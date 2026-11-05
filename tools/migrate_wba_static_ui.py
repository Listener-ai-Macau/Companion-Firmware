"""Explicit development media migration for a matched WBA static UI package.

Caller must hold the shared board lease, verify the normal idle application and
the exact internal preimage/NVM, and keep the same official API session. This
does not run a loader, open a probe or format anything merely on import. Raw
settings/preimages stay local; only hashes belong in delivery checkpoints.
"""
from pathlib import Path
import ctypes as c
import hashlib
import shutil
import struct
import zlib
from provision_wba_v11 import write_json
from verify_wba_factory_loader import Loader
from wba_resource_geometry import geometry

NOR = 0x90000000
SECTOR = 4096
SYSTEM = 131072
sha = lambda data: hashlib.sha256(data).hexdigest()

def external_read(probe, address, size, name):
    """Bound Cube's callable-loader receive buffer to physical CE SRAM1.

    The current loader ends near0x200021a0. A32KiB receive buffer would cross
    the documented0x20008000 bank boundary even if an old probe read happened
    to compare correctly.16KiB calls keep the loader's staging buffer in its
    first bank; this does not claim the NOR's virtual0x90000000 is mapped RAM.
    """
    if address < NOR or size <= 0 or address-NOR > 16777216-size:
        raise ValueError('External read outside the16MiB NOR')
    if size <= 16384:
        return probe.read(address,size,name)
    result=bytearray()
    for at in range(0,size,16384):
        result.extend(probe.read(address+at,min(16384,size-at),name+f'.part-{at:x}'))
    destination=probe.output/name
    if destination.exists():
        raise RuntimeError('Refuse to overwrite assembled external read '+name)
    destination.write_bytes(result)
    return bytes(result)


def plan(old_bank, new_bank, metadata, payload_prefix):
    """Make a bounded paired migration, preserving every non-recording byte."""
    old, new = geometry(len(old_bank)), geometry(len(new_bank))
    assert len(metadata) == SYSTEM
    assert new['staticBytes'] > old['staticBytes']
    assert len(payload_prefix) == new['staticBytes'] - old['staticBytes']
    roots = [metadata[at:at+64] for at in (0x8000, 0x9000)]
    valid = [p for p in roots if p[:4] == b'CFL3' and
             struct.unpack_from('<II', p, 4) == (3, 64) and
             struct.unpack_from('<5I', p, 12) ==
             (old['staticBytes'], old['dynamicBase'], old['recordingCatalog'],
              old['payloadBase'], old['payloadBytes']) and
             struct.unpack_from('<I', p, 60)[0] == zlib.crc32(p[:60])]
    assert valid and all(p == valid[0] for p in valid), 'Unknown or divergent CFL3 layout'
    assert metadata[0x2000:0x4000] == b'\xff'*8192, 'Pending OTA state; refuse media migration'
    root = bytearray(valid[0])
    struct.pack_into('<5I', root, 12, new['staticBytes'], new['dynamicBase'],
                     new['recordingCatalog'], new['payloadBase'], new['payloadBytes'])
    struct.pack_into('<I', root, 60, zlib.crc32(root[:60]))
    moved = bytearray(metadata)
    # Owner explicitly permits clearing DEVELOPMENT recordings. A blank CSI1
    # is provisioned by the existing product entropy allocator on the next boot,
    # giving a fresh namespace; no old session IDs or synthetic sample are reused.
    cleared = [(0x6000, 0x2000), (0x10000, 0x2000), (0x14000, 0xC000)]
    for at, count in cleared:
        moved[at:at+count] = b'\xff'*count
    for at in (0x8000, 0x9000):
        moved[at:at+SECTOR] = bytes(root).ljust(SECTOR, b'\xff')
    protected = [i for i in range(SYSTEM//SECTOR) if not any(
        at <= i*SECTOR < at+n for at, n in cleared+[(0x8000, 8192)])]
    for i in protected:
        assert moved[i*SECTOR:(i+1)*SECTOR] == metadata[i*SECTOR:(i+1)*SECTOR]
    before = old_bank+metadata+payload_prefix
    after = new_bank+bytes(moved)
    assert len(before) == len(after) == new['dynamicBase']+SYSTEM
    pages = [at for at in range(0, len(after), SECTOR)
             if before[at:at+SECTOR] != after[at:at+SECTOR]]
    preserved_prefix = old['rootA']-SECTOR
    assert new_bank[:preserved_prefix] == old_bank[:preserved_prefix]
    assert pages and min(pages) >= preserved_prefix
    assert max(pages)+SECTOR <= new['dynamicBase']+SYSTEM
    return before, after, pages, protected, old, new


def open_loader(probe, out, loader_path):
    """Use the same CE development formatter already installed in this project."""
    loader_path = Path(loader_path)
    assert sha(loader_path.read_bytes()) == 'bf8a6b7014844a5ed036b6ea1b7b2bd9c96564adc1e58a58a2e660a74a23b641'
    root = out/'loaders'
    (root/'ExternalLoader').mkdir(parents=True, exist_ok=False)
    shutil.copyfile(loader_path, root/'ExternalLoader'/loader_path.name)
    # setLoadersPath changes internal-loader discovery as well. Keep the official
    # installed internal loaders available throughout the paired transaction.
    shutil.copytree(Path('C:/ST/STM32CubeProgrammer/bin/FlashLoader'), root/'FlashLoader')
    probe.api.setLoadersPath(str(root.resolve()).encode())
    probe.api.setExternalLoaderPath.argtypes = [c.c_char_p, c.POINTER(c.POINTER(Loader))]
    probe.api.setExternalLoaderPath.restype = None
    probe.api.removeExternalLoader.argtypes = [c.c_char_p]
    probe.api.removeExternalLoader.restype = None
    loaded = c.POINTER(Loader)()
    try:
        probe.api.setExternalLoaderPath(loader_path.name.encode(), c.byref(loaded))
        assert loaded and loaded.contents.sectors, 'CE formatter registration unavailable'
        info = loaded.contents
        assert (info.start, info.size, info.page, info.sector_types,
                info.sectors[0].count, info.sectors[0].size) == (NOR, 16777216, 256, 1, 4096, SECTOR)
        assert info.name.decode() == 'Companion_V11_WBA55_SPI3_DEV_FORMAT_v3'
    except BaseException:
        remove_loader(probe, loader_path.name)
        raise
    return loader_path.name


def remove_loader(probe, name):
    probe.api.removeExternalLoader(name.encode())
    probe.api.setLoadersPath(b'C:/ST/STM32CubeProgrammer/bin')


def migrate(probe, out, lease, old_bank, new_bank, state, loader_path):
    """Read exact media, then replace only changed sectors; rollback once on failure."""
    name = open_loader(probe, out, loader_path)
    state['externalLoaderEntered'] = True
    touched = []
    before = None
    try:
        actual = bytearray()
        for at in range(0, len(old_bank), 65536):
            n = min(65536, len(old_bank)-at)
            actual.extend(external_read(probe,NOR+at, n, f'before-ui-{at:x}.bin'))
        assert bytes(actual) == old_bank, 'Actual UI67 bank differs from the preserved package'
        metadata = external_read(probe,NOR+len(old_bank), SYSTEM, 'private-metadata-before.bin')
        tail = external_read(probe,NOR+len(old_bank)+SYSTEM, len(new_bank)-len(old_bank),
                          'development-payload-prefix-before.bin')
        before, after, pages, protected, old, new = plan(old_bank, new_bank, metadata, tail)
        state.update(mediaPreimageVerified=True, oldGeometry=old, newGeometry=new,
                     norChangedSectorOffsets=pages, protectedMetadataSectorIndices=protected,
                     developerRecordingNamespaceClearPlanned=True)
        write_json(out/'result.json', state)
        readback = bytearray(before)
        for at in pages:
            lease()
            page = out/f'private-media-target-{at:x}.bin'
            page.write_bytes(after[at:at+SECTOR])
            state['norWritesStarted'] = True
            touched.append(at)
            write_json(out/'result.json', state)
            probe.checked(probe.api.downloadFile(str(page), NOR+at, 0, 1, None),
                          'bounded changed NOR sector erase/write/verify')
            got = probe.read(NOR+at, SECTOR, f'private-media-after-{at:x}.bin')
            assert got == after[at:at+SECTOR], ('NOR sector differs', at)
            readback[at:at+SECTOR] = got
            print(f'NOR verified sector {at//SECTOR}', flush=True)
        assert bytes(readback) == after
        for i in protected:
            at = new['dynamicBase']+i*SECTOR
            assert readback[at:at+SECTOR] == metadata[i*SECTOR:(i+1)*SECTOR]
        state.update(staticResourceReadback=True, staticResourceSha256=sha(readback[:len(new_bank)]),
                     developerRecordingNamespaceCleared=True,
                     protectedDynamicMetadataPreserved=True, newLayoutReadback=True,
                     originalUi67PreimageSha256=sha(actual),
                     oldMetadataSha256=sha(metadata), newMetadataSha256=sha(readback[len(new_bank):]),
                     norReadbackMethod='Same-operation full original bank and changed-sector exact readback; unchanged sectors never erased')
        write_json(out/'result.json', state)
        # Retained only in local private preimages for a paired INTERNAL failure;
        # the caller must not commit settings, NVM, or raw recording bytes.
        return before, pages
    except BaseException:
        if touched and before is not None:
            try:
                for at in touched:
                    lease()
                    p = out/f'private-media-rollback-{at:x}.bin'
                    p.write_bytes(before[at:at+SECTOR])
                    probe.checked(probe.api.downloadFile(str(p), NOR+at, 0, 1, None),
                                  'restore exact media sector changed by failed migration')
                    assert probe.read(NOR+at, SECTOR, f'private-media-restored-{at:x}.bin') == before[at:at+SECTOR]
                state['failedMediaMigrationRestored'] = True
            except BaseException as exc:
                state['failedMediaRestoreError'] = repr(exc)
        raise
    finally:
        remove_loader(probe, name)


def restore_paired_media(probe, out, lease, before, pages, state, loader_path):
    """Restore exactly this migration after a paired internal installation fails.

    This is a single bounded restoration of our own writes. The caller restores
    and verifies the original internal pages first and retains the same session.
    It does not retry installing or switch the probe connection/reset mode.
    """
    holder=out/'paired-media-restore'
    holder.mkdir(exist_ok=False)
    name=open_loader(probe, holder, loader_path)
    try:
        for at in pages:
            lease()
            p=holder/f'private-original-{at:x}.bin'
            p.write_bytes(before[at:at+SECTOR])
            probe.checked(probe.api.downloadFile(str(p),NOR+at,0,1,None),
                          'restore exact media sector after paired internal failure')
            assert probe.read(NOR+at,SECTOR,f'private-paired-restored-{at:x}.bin')==before[at:at+SECTOR]
        state['pairedOriginalMediaRestored']=True
        state['developerRecordingNamespaceCleared']=False
        write_json(out/'result.json',state)
    finally:
        remove_loader(probe,name)
