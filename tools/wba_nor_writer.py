"""Shared bounded writer for one already qualified wired migration plan.

No admission, connection or permission inference. Caller owns the physical
identity, retained original authority, exact live plan and exclusive session.
"""
import ctypes as c
from migrate_wba_static_ui import external_read, remove_loader
from wba_nor_initial import SYSTEM_BYTES, TARGET, inspect_pairing, require


def apply_plan(probe, out, images, plan, original, ui, system, uid,
               lease, state, save, open_loader):
    loader_name = None
    try:
        probe.api.sectorErase.argtypes = [c.POINTER(c.c_uint), c.c_uint, c.c_char_p]
        probe.api.sectorErase.restype = c.c_int

        def internal_pages(offsets):
            for at in offsets:
                lease.check()
                require(at % 8192 == 0 and 0 <= at <= TARGET.flash_bytes - 8192, 'Unbounded internal page')
                path = out / f'internal-target-{at:x}.bin'
                path.write_bytes(images.internal[at:at + 8192])
                state['writesStarted'] = True; state['nextInternalPage'] = at; save()
                indices = (c.c_uint * 1)(at // 8192)
                probe.checked(probe.api.sectorErase(indices, 1, None), 'bounded migration internal page erase')
                probe.checked(probe.api.downloadFile(str(path), TARGET.flash_base + at, 1, 1, None),
                              'bounded migration internal page program/readback')
                require(probe.read(TARGET.flash_base + at, 8192, f'internal-readback-{at:x}.bin') ==
                        images.internal[at:at + 8192], 'Internal page readback differs')
                state['verifiedInternalPages'].append(at); save()

        operations = plan['orderedOperations']
        internal_pages(operations[0]['pageOffsets'])
        loader_name = open_loader(probe)
        current_system = external_read(probe, 0x90000000 + len(ui), SYSTEM_BYTES, 'private-before-reclaim-system.bin')
        require(current_system == system, 'External metadata changed before internal NVM reclaim')
        inspect_pairing(original, current_system, uid)
        remove_loader(probe, loader_name); loader_name = None
        internal_pages(operations[1]['pageOffsets'])
        require(probe.read(TARGET.app_address, len(images.internal) - TARGET.boot_bytes,
                           'app-and-tail-before-publication.bin') == images.internal[TARGET.boot_bytes:],
                'Complete App/tail is not verified before publication')
        loader_name = open_loader(probe)
        require(external_read(probe, 0x90000000, len(ui), 'ui-before-publication.bin') == ui,
                'Resource changed before publication')
        require(external_read(probe, 0x90000000 + len(ui), SYSTEM_BYTES, 'private-system-before-publication.bin') == system,
                'Metadata/bonds changed before publication')
        expected_system = bytearray(system)
        for at in plan['allowedNorSectorOffsets']:
            lease.check()
            require(at - len(ui) in (0x2000, 0x3000), 'Unexpected metadata mutation')
            path = out / f'current-target-{at:x}.bin'; path.write_bytes(images.current_sector)
            state['writesStarted'] = True; state['nextNorSector'] = at; save()
            probe.checked(probe.api.downloadFile(str(path), 0x90000000 + at, 0, 1, None),
                          'bounded signed-current metadata sector')
            require(external_read(probe, 0x90000000 + at, 4096, f'current-readback-{at:x}.bin') == images.current_sector,
                    'Signed current publication readback differs')
            expected_system[at - len(ui):at - len(ui) + 4096] = images.current_sector
            state['verifiedNorSectors'].append(at); save()
        require(external_read(probe, 0x90000000 + len(ui), SYSTEM_BYTES, 'private-system-after-publication.bin') ==
                bytes(expected_system), 'Unrelated metadata or protected pairing changed')
        remove_loader(probe, loader_name); loader_name = None
        internal_pages(operations[4]['pageOffsets'])
        require(probe.read(TARGET.flash_base, TARGET.flash_bytes, 'internal-after.bin') == images.internal,
                'Full new internal image differs')
        loader_name = open_loader(probe)
        require(external_read(probe, 0x90000000, len(ui), 'ui-after.bin') == ui and
                external_read(probe, 0x90000000 + len(ui), SYSTEM_BYTES, 'private-metadata-after.bin') == bytes(expected_system),
                'Final UI/system/protected pairing readback differs')
        remove_loader(probe, loader_name); loader_name = None
        state.update(fullInternalReadback=True, currentMetadataReadback=True, uiReadback=True,
                     pairingExternalBytesPreserved=True, settingsAndRecordingMetadataPreserved=True,
                     internalNvmReclaimed=True)
        save()
    finally:
        if loader_name:
            remove_loader(probe, loader_name)
