"""Prepare a UID-bound blank-device simple-CUP initial package, offline by default.

This is a separate NEW BLANK DEVICE path, never a missing-UART fallback for an
installed product. Explicit execution must read the entire MCU and entire NOR
as erased, or match a retained pre-start blank-device journal for this UID and
this exact signed target. Device operations happen only inside execute().
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import struct
import threading
import time
import zlib

from package_wba_paired_initial import workspace_sector
from wba_factory_writer import open_bound_loader, validate_writer
from wba_nor_initial import (TARGET, TargetImages, exact, inspect_target, load, require,
                             sha, verify_build_inputs)
from install_wba_nor_initial import BoardLease

NOR_BYTES = 16777216
PUBLICATION_BYTES = 16
PROBE = '004400403532510B31333430'
# Pinned STM32WBA55 CMSIS: SYSTEM_FLASH_BASE_NS=0x0BF88000;
# FLASH_OTP_BASE=SYSTEM_FLASH_BASE_NS+0x8000. Permit the known ROM alternate
# entry, never an unchecked secure-flash alias, SRAM or direct App entry.
SYSTEM_ROM_NS_BEGIN, SYSTEM_ROM_NS_END = 0x0BF88000, 0x0BF90000


def stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def is_blank(data: bytes) -> bool:
    return data.count(255) == len(data)


def valid_uid(uid: bytes):
    require(len(uid) == 12 and uid not in (bytes(12), b'\xff' * 12), 'Exact nonblank device UID required')


def cfl3_sector(geometry: dict, uid: bytes) -> bytes:
    valid_uid(uid)
    # Reuse the existing product root encoder, then bind its reserved device
    # identity and recompute the same CRC. This is not a second root format.
    root = bytearray(workspace_sector(geometry))
    root[32:44] = uid
    struct.pack_into('<I', root, 60, zlib.crc32(root[:60]))
    return bytes(root)


@dataclass(repr=False)
class BlankImages:
    target: TargetImages
    uid: bytes
    nor_geometry: dict
    root: bytes
    preactivation: bytes

    @property
    def vectors(self):
        return (0, TARGET.boot_bytes)

    def nor_target(self) -> bytes:
        result = bytearray(b'\xff' * NOR_BYTES)
        result[:len(self.target.ui)] = self.target.ui
        static = len(self.target.ui)
        for at in (0x2000, 0x3000): result[static + at:static + at + 4096] = self.target.current_sector
        for at in (0x8000, 0x9000): result[static + at:static + at + 4096] = self.root
        return bytes(result)

    def report(self):
        static = len(self.target.ui)
        return dict(schema='companion.wba.blank-simple-initial.v1', uid=self.uid.hex(),
                    result='OFFLINE_UID_BOUND_INITIAL_IMAGES_NOT_INSTALLED',
                    target=self.target.report, flashGeometry=self.nor_geometry,
                    preactivationSha256=sha(self.preactivation), finalInternalSha256=sha(self.target.internal),
                    fullExpectedNorSha256=sha(self.nor_target()), rootSha256=sha(self.root),
                    currentSectorSha256=sha(self.target.current_sector),
                    norWriteRanges=[dict(offset=0, bytes=static)] +
                        [dict(offset=static + at, bytes=4096) for at in (0x2000, 0x3000, 0x8000, 0x9000)],
                    protectedPairingAndSealRange=[static + 0xC000, static + 0xF000],
                    vectorPublication=[dict(offset=at, bytes=PUBLICATION_BYTES,
                                            sha256=sha(self.target.internal[at:at + PUBLICATION_BYTES])) for at in self.vectors],
                    fullBlankBeforeFirstWriteRequired=True, wholeNorAndMcuRequired=True,
                    vectorPublicationFollowsDurableStartAuthorization=True,
                    source='Existing simple CUP/SCU3 + existing UID-bound CFL3 root encoder',
                    acquisitionProven=False, installed=False, hardwareOperations=0,
                    atRestSecurityQualified=False, physicalQualified=False)


def make_images(target: TargetImages, uid: bytes, nor_geometry: dict) -> BlankImages:
    valid_uid(uid)
    static = len(target.ui)
    require(nor_geometry['norBytes'] == NOR_BYTES and nor_geometry['staticBytes'] == static and
            nor_geometry['dynamicBase'] == static and nor_geometry['systemBytes'] == 131072 and
            nor_geometry['recordingCatalog'] == static + 0x10000 and
            nor_geometry['payloadBase'] == static + 0x20000, 'Exact current NOR geometry required')
    preactivation = bytearray(target.internal)
    for at in (0, TARGET.boot_bytes): preactivation[at:at + PUBLICATION_BYTES] = b'\xff' * PUBLICATION_BYTES
    return BlankImages(target, uid, nor_geometry, cfl3_sector(nor_geometry, uid), bytes(preactivation))


def original_blank_authority(images: BlankImages, original: dict,
                             original_internal: bytes, original_nor: bytes) -> None:
    """Reject an already-start-authorized journal BEFORE any device access."""
    report = images.report()
    require(original.get('schema') == 'companion.wba.blank-initial-journal.v1' and
            original.get('uid') == images.uid.hex() and
            original.get('packageSha256') == images.target.report['packageSha256'] and
            original.get('preactivationSha256') == report['preactivationSha256'] and
            original.get('fullExpectedNorSha256') == report['fullExpectedNorSha256'],
            'Original blank journal belongs to another UID/package/target')
    require(original.get('startAuthorized') is False and original.get('phase') in
            ('ORIGINAL_BLANK_SAVED', 'NOR_PENDING', 'INTERNAL_PENDING', 'PREACTIVATION_VERIFIED'),
            'Application may already have started; do not resume as a blank device')
    require(original_internal is not None and len(original_internal) == TARGET.flash_bytes and
            is_blank(original_internal) and original.get('originalInternalSha256') == sha(original_internal),
            'Original full internal blank backup is absent or inconsistent')
    require(original_nor is not None and len(original_nor) == NOR_BYTES and is_blank(original_nor) and
            original.get('originalNorSha256') == sha(original_nor), 'Original full NOR blank backup is absent or inconsistent')


def qualify_before_start(images: BlankImages, internal: bytes, nor: bytes, original: dict | None = None,
                         original_internal: bytes | None = None, original_nor: bytes | None = None) -> dict:
    require(len(internal) == TARGET.flash_bytes and len(nor) == NOR_BYTES, 'Whole-chip readbacks required')
    if original is None:
        require(is_blank(internal) and is_blank(nor), 'Device is not fully blank; preserve it and use its installed-product path')
        return dict(result='LIVE_BYTES_BLANK_INITIAL_ELIGIBLE', originalInternalSha256=sha(internal),
                    originalNorSha256=sha(nor), resume=False, acquisitionProven=False)
    require(original_internal is not None and original_nor is not None, 'Original blank backups required')
    original_blank_authority(images, original, original_internal, original_nor)
    for at in images.vectors:
        require(is_blank(internal[at:at + PUBLICATION_BYTES]), 'A publication vector is no longer erased')
    require(all((a & b) == b for a, b in zip(internal, images.preactivation)),
            'Internal data is not an interrupted write of this exact preactivation image')
    desired_nor = images.nor_target()
    require(all((a & b) == b for a, b in zip(nor, desired_nor)),
            'NOR contains unrelated settings, recording, pairing, or another target')
    static = len(images.target.ui)
    require(is_blank(nor[static + 0xC000:static + 0xF000]), 'A pairing/provisioning page is no longer blank')
    return dict(result='LIVE_BYTES_MATCH_RETAINED_PRESTART_BLANK_AUTHORITY', resume=True,
                originalInternalSha256=sha(original_internal), originalNorSha256=sha(original_nor),
                currentInternalSha256=sha(internal), currentNorSha256=sha(nor), acquisitionProven=False)


def prepare_directory(images: BlankImages, output: Path, source: dict, factory_binding: dict):
    require(not output.exists(), 'Prepared output already exists')
    output.mkdir(parents=True)
    payloads = {'preactivation-internal.bin': images.preactivation,
                'ui-partition.bin': images.target.ui, 'current-sector.bin': images.target.current_sector,
                'cfl3-sector.bin': images.root, 'companion-update.cup': images.target.cup,
                'boot-vector.bin': images.target.internal[:PUBLICATION_BYTES],
                'app-vector.bin': images.target.internal[TARGET.boot_bytes:TARGET.boot_bytes + PUBLICATION_BYTES]}
    for name, data in payloads.items(): (output / name).write_bytes(data)
    report = images.report()
    report.update(source=source, factorySourceBinding=factory_binding,
                  files={name: dict(bytes=len(data), sha256=sha(data)) for name, data in payloads.items()},
                  vectorFilesAreFinalPublicationOnly=True,
                  preactivationFileMustSkipBothVectorUnitsDuringProgramming=True,
                  directWholeImageProgrammingNotTheGuardedProcedure=True,
                  executionCommandHasNotRun=True)
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def execute(args, images: BlankImages, factory: dict):
    import ctypes as c
    import os
    import serial
    from serial.tools.list_ports import comports
    from cube_programmer_api_session import Session
    from diagnose_wba_uart import parse_frames
    from migrate_wba_static_ui import external_read, remove_loader
    from provision_wba_v11 import probe_lock, sync_backup, validate_identity, write_json

    require(args.new_blank_device, 'Execution requires explicit NEW BLANK DEVICE intent; never a UART fallback')
    out, project = args.output.resolve(), args.project_root.resolve()
    require(out.is_relative_to(project / '.cache') and not out.exists(), 'New private .cache acquisition output required')
    origin = args.resume.resolve() if args.resume else out
    require(origin.is_relative_to(project / '.cache'), 'Original private journal must stay inside project .cache')
    original_checkpoint, original_internal, original_nor = None, None, None
    if args.resume:
        original_checkpoint = load(origin / 'checkpoint.json')
        original_internal = exact(origin, 'before-internal.bin', TARGET.flash_bytes)
        original_nor = exact(origin, 'before-nor.bin', NOR_BYTES)
        original_blank_authority(images, original_checkpoint, original_internal, original_nor)
    out.mkdir(parents=True)
    lease = BoardLease(project / 'docs/board_operations.md', out,
                       '新空白板simple-CUP初装；全MCU/NOR空白或原始空白日志续装，无掉线恢复，向量最后发布')
    state = dict(schema='companion.wba.blank-initial-attempt.v1', startedAt=stamp(), uid=images.uid.hex(),
                 result='NOT_STARTED', writesStarted=False, normalAfter=False, startAuthorized=False,
                 hardwareStage='NEW_BLANK_DEVICE', wirelessOta=False, ownedHandlesClosed=False,
                 verifiedInternalPages=[], verifiedNorRanges=[])
    checkpoint = None
    stop, opened = threading.Event(), threading.Event()
    monitor, errors = None, []
    def save(): write_json(out / 'result.json', state)
    def durable(path):
        with path.open('rb+') as f: f.flush(); os.fsync(f.fileno())
    def save_checkpoint():
        write_json(origin / 'checkpoint.json', checkpoint); durable(origin / 'checkpoint.json')
    def listen():
        try:
            ports = [p.device for p in comports() if p.serial_number == PROBE]
            require(len(ports) == 1, 'Fixed V3 passive UART absent/ambiguous')
            port = serial.Serial(port=None, baudrate=115200, timeout=.1)
            port.dtr = False; port.rts = False; port.port = ports[0]
            with port, (out / 'after-uart.log').open('wb') as f:
                opened.set()
                while not stop.is_set():
                    data = port.read(min(max(port.in_waiting, 1), 4096))
                    if data: f.write(data); f.flush()
        except BaseException as e: errors.append(type(e).__name__ + ': ' + str(e)); opened.set()
    save()
    try:
        lease.acquire()
        with probe_lock(PROBE), Session(PROBE, out, lease.check, access_port=1) as probe:
            uid = probe.read(0x0BF90700, 12, 'uid.bin')
            require(validate_identity(probe.read(0xE0044000, 4, 'device-id.bin'),
                                      probe.read(0x0BF907A0, 2, 'flash-size.bin'),
                                      probe.read(0x40022040, 4, 'options.bin'), uid, TARGET) == images.uid.hex(),
                    'Actual physical MCU/UID differs')
            boot_options = probe.read(0x40022044, 8, 'boot-addresses.bin')
            boot0, boot1 = (value & 0xFFFFFF80 for value in struct.unpack('<2I', boot_options))
            require(boot0 == TARGET.flash_base and (boot1 == TARGET.flash_base or
                    SYSTEM_ROM_NS_BEGIN <= boot1 < SYSTEM_ROM_NS_END),
                    'Nondefault internal boot entry; option bytes will not be changed')
            freeze = int.from_bytes(probe.read(0xE0044008, 4, 'freeze-before.bin'), 'little')
            registered, complete = None, False
            try:
                probe.word(0xE0044008, freeze | (1 << 12))
                internal = probe.read(TARGET.flash_base, TARGET.flash_bytes, 'before-internal.bin')
                registered = open_bound_loader(probe, out, args.loader, factory)
                nor = external_read(probe, 0x90000000, NOR_BYTES, 'before-nor.bin')
                if args.resume:
                    require(load(origin / 'checkpoint.json') == original_checkpoint, 'Original journal changed before admission')
                    checkpoint = original_checkpoint
                    require(exact(origin, 'uid.bin', 12) == uid and exact(origin, 'boot-addresses.bin', 8) == boot_options and
                            exact(origin, 'options.bin', 4) == exact(out, 'options.bin', 4),
                            'Original physical identity or boot configuration differs')
                    admission = qualify_before_start(images, internal, nor, checkpoint,
                                                     original_internal, original_nor)
                else:
                    admission = qualify_before_start(images, internal, nor)
                    sync_backup(out / 'before-internal.bin', internal); sync_backup(out / 'before-nor.bin', nor)
                    checkpoint = dict(schema='companion.wba.blank-initial-journal.v1', uid=uid.hex(),
                                      packageSha256=images.target.report['packageSha256'],
                                      preactivationSha256=sha(images.preactivation), fullExpectedNorSha256=sha(images.nor_target()),
                                      originalInternalSha256=sha(internal), originalNorSha256=sha(nor),
                                      startAuthorized=False, phase='ORIGINAL_BLANK_SAVED')
                    for name in ('uid.bin', 'options.bin', 'boot-addresses.bin'): durable(out / name)
                state['admission'] = admission; state['originalBlankDirectory'] = str(origin)
                save_checkpoint(); save()
                desired_nor = images.nor_target(); static = len(images.target.ui)
                ranges = [(0, images.target.ui)] + [(static + at, images.target.current_sector) for at in (0x2000, 0x3000)] + \
                         [(static + at, images.root) for at in (0x8000, 0x9000)]
                for at, data in ranges:
                    if nor[at:at + len(data)] == data: continue
                    lease.check(); checkpoint['phase'] = 'NOR_PENDING'; save_checkpoint()
                    path = out / f'nor-target-{at:x}.bin'; path.write_bytes(data)
                    state['writesStarted'] = True; state['nextNorRange'] = [at, len(data)]; save()
                    probe.checked(probe.api.downloadFile(str(path), 0x90000000 + at, 0, 1, None), 'bounded blank-device NOR range')
                    require(external_read(probe, 0x90000000 + at, len(data), f'nor-verified-{at:x}.bin') == data,
                            'Blank-device NOR readback differs')
                    state['verifiedNorRanges'].append([at, len(data)]); save()
                require(external_read(probe, 0x90000000, NOR_BYTES, 'nor-preactivation.bin') == desired_nor,
                        'Full NOR differs or unrelated fresh storage is no longer blank')
                remove_loader(probe, registered); registered = None
                probe.api.sectorErase.argtypes = [c.POINTER(c.c_uint), c.c_uint, c.c_char_p]
                probe.api.sectorErase.restype = c.c_int
                pages = [at for at in range(0, TARGET.flash_bytes, 8192)
                         if internal[at:at + 8192] != images.preactivation[at:at + 8192] or at in images.vectors]
                pages = [at for at in pages if at >= TARGET.boot_bytes] + sorted(
                    [at for at in pages if at < TARGET.boot_bytes], reverse=True)
                for at in pages:
                    lease.check(); checkpoint['phase'] = 'INTERNAL_PENDING'; save_checkpoint()
                    state['writesStarted'] = True; state['nextInternalPage'] = at; save()
                    indices = (c.c_uint * 1)(at // 8192)
                    probe.checked(probe.api.sectorErase(indices, 1, None), 'bounded blank-device internal page erase')
                    skip = PUBLICATION_BYTES if at in images.vectors else 0
                    # Never program all-FF into the reserved vector units:
                    # ECC programming is not inferred from read-as-FF data.
                    path = out / f'internal-body-{at:x}.bin'
                    path.write_bytes(images.preactivation[at + skip:at + 8192])
                    probe.checked(probe.api.downloadFile(str(path), TARGET.flash_base + at + skip, 1, 1, None),
                                  'initial page body with vector unit excluded')
                    require(probe.read(TARGET.flash_base + at, 8192, f'internal-body-verified-{at:x}.bin') ==
                            images.preactivation[at:at + 8192], 'Preactivation internal page differs')
                    state['verifiedInternalPages'].append(at); save()
                require(probe.read(TARGET.flash_base, TARGET.flash_bytes, 'internal-preactivation.bin') == images.preactivation,
                        'Full preactivation image differs')
                checkpoint['phase'] = 'PREACTIVATION_VERIFIED'; save_checkpoint()
                registered = open_bound_loader(probe, out, args.loader, factory)
                require(external_read(probe, 0x90000000, NOR_BYTES, 'nor-before-publication.bin') == desired_nor,
                        'NOR changed before start authorization')
                remove_loader(probe, registered); registered = None
                # Write-ahead boundary: after this durable record a reset could
                # start the new application and generate keys. A missing log is
                # never permission to reclassify it as blank and erase again.
                checkpoint.update(phase='START_AUTHORIZED', startAuthorized=True, authorizedAt=stamp())
                save_checkpoint(); state['startAuthorized'] = True; save()
                for at in (TARGET.boot_bytes, 0):
                    lease.check()
                    data = images.target.internal[at:at + PUBLICATION_BYTES]
                    path = out / f'vector-publication-{at:x}.bin'; path.write_bytes(data)
                    probe.checked(probe.api.downloadFile(str(path), TARGET.flash_base + at, 1, 1, None),
                                  'final aligned vector publication without erase')
                    require(probe.read(TARGET.flash_base + at, PUBLICATION_BYTES, f'vector-verified-{at:x}.bin') == data,
                            'Vector publication readback differs')
                require(probe.read(TARGET.flash_base, TARGET.flash_bytes, 'internal-final.bin') == images.target.internal,
                        'Full final Boot/App readback differs')
                state.update(fullInternalReadback=True, fullNorReadbackBeforeStart=True, cfl3UidBound=True,
                             signedCurrentPublished=True, pairingAndSealBlankBeforeFirstStart=True)
                checkpoint['phase'] = 'COMPLETE_READBACK_BEFORE_START'; save_checkpoint(); save()
                monitor = threading.Thread(target=listen); monitor.start()
                require(opened.wait(5) and not errors, 'Passive first-start UART unavailable; no automatic retry')
                complete = True
            finally:
                if registered: remove_loader(probe, registered)
                if complete:
                    probe.word(0xE0044008, freeze); probe.reset(); state['softwareResetIssued'] = True
                else:
                    # Do not start a rejected/nonblank target or an incomplete
                    # new image. Retain the explicit initial-install context.
                    probe.word(0xE0044008, freeze)
                    state['leftStoppedWithoutAdditionalReset'] = True
                save()
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline and not errors:
            lease.check()
            raw = (out / 'after-uart.log').read_bytes()
            frames, bad = parse_frames(raw)
            if frames and not bad:
                s = frames[-1]['sections']
                if (s['ID']['uid'] == images.uid.hex() and s['ID']['fw'] == f'{images.target.report["firmware"]:08x}' and
                    s['ID']['ui'] == images.target.report['ui'] and s['BLE']['init'] == 1 and
                    s['STORAGE']['recording_ready'] == 1 and not s['STORAGE']['rec_fault'] and
                    not s['CORE']['stack_guard'] and not s['CORE']['stack_low']):
                    state.update(result='BLANK_INITIAL_READBACK_AND_NORMAL_FIRST_START_VERIFIED', normalAfter=True,
                                 afterSnapshot=frames[-1], ownerAcceptancePending=True); break
            time.sleep(.1)
        require(state['normalAfter'], 'No qualified passive first-start reply; preserve data and do not repeat initial installation')
    except BaseException as e:
        state.update(result='BLANK_INITIAL_NOT_COMPLETED', error=type(e).__name__ + ': ' + str(e))
    finally:
        stop.set()
        if monitor:
            monitor.join(3); require(not monitor.is_alive(), 'Actual UART handle still open; keep lease')
        state.update(ownedHandlesClosed=True, finishedAt=stamp()); save(); lease.release(state['result'])
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'app', 'boot', 'public-key', 'source-root', 'source-repo',
                 'resource-directory', 'factory-result', 'loader', 'project-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--uid', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--new-blank-device', action='store_true', help='Explicit new-device intent, never inferred from missing UART')
    parser.add_argument('--resume', type=Path, help='Retained pre-start blank-device original journal; refuses any start-authorized attempt')
    args = parser.parse_args()
    require(len(args.uid) == 24 and all(c in '0123456789abcdefABCDEF' for c in args.uid), 'Exact UID required')
    uid = bytes.fromhex(args.uid); valid_uid(uid)
    require(args.execute or args.resume is None, 'Resume is an explicit hardware action, unavailable during offline preparation')
    target = inspect_target(args.package, args.app, args.boot, args.public_key.read_bytes(), args.source_root,
                            args.source_repo, args.source_commit, args.resource_directory)
    app = load(args.app / 'result.json')
    require(app['ble_bond_persistence']['new_board_provisioning'] is True, 'Explicit DEV first-board-capable App required')
    factory = load(args.factory_result)
    validate_writer(factory, args.loader.read_bytes(), len(target.ui))
    binding = verify_build_inputs({'source_sha256': {}}, factory, args.source_root,
                                  args.source_repo, args.source_commit, args.resource_directory)
    images = make_images(target, uid, app['flash_geometry'])
    if args.execute:
        result = execute(args, images, factory)
    else:
        result = prepare_directory(images, args.output,
                                   dict(commit=args.source_commit, root=str(args.source_root)), binding)
    print(json.dumps({key: result.get(key) for key in ('result', 'uid', 'installed', 'normalAfter', 'writesStarted')}))
    raise SystemExit(0 if not args.execute or result.get('normalAfter') else 2)


if __name__ == '__main__': main()
