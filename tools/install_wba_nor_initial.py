"""Matched compact24-nor initial migration, offline inspection by default.

--execute is a deliberate WIRED INITIAL MIGRATION, never ordinary App OTA.
The executing operator must have current hardware authorization. One normal
idle bridge application reply is mandatory; there is no missing-UART recovery
switch, alternate reset strategy, automatic retry, or old-image rollback.
Original reads contain pairing secrets: execution output must remain in the
project's ignored .cache. No private bytes may be added to public checkpoints.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import threading
import time

from wba_nor_initial import (SYSTEM_BYTES, TARGET, exact, inspect_pairing,
                             inspect_target, load, make_plan, require, sha,
                             verify_build_inputs)

PROBE = '004400403532510B31333430'


def stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


class BoardLease:
    def __init__(self, path: Path, output: Path, purpose: str | None = None):
        self.path, self.output, self.held = path, output, False
        purpose = purpose or 'compact24-nor有线初始迁移；一次正常空闲UART/当次COMMITTED外部配对核验，Boot最后'
        self.line = ('- **占用中**：Companion ' + purpose + '（' + stamp() +
                     '，固定V3）。依据' + str(output / 'result.json'))

    def raw(self):
        raw = self.path.read_bytes()
        require('## 当前占用'.encode() in raw and '## 交接方式'.encode() in raw,
                'Shared board record is incomplete')
        return raw

    @staticmethod
    def owners(raw):
        begin = raw.index('## 当前占用'.encode())
        end = raw.index('## 交接方式'.encode(), begin)
        return [row.decode() for row in raw[begin:end].splitlines() if '**占用中**'.encode() in row]

    def replace(self, before, after):
        import os
        import tempfile
        for _ in range(6):
            raw = self.raw()
            old, new = before.encode(), after.encode()
            require(raw.count(old) == 1, 'Exact shared lease row is absent or ambiguous')
            if raw != self.path.read_bytes():
                time.sleep(.1)
                continue
            fd, temp = tempfile.mkstemp(prefix=self.path.name + '.', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(raw.replace(old, new, 1)); f.flush(); os.fsync(f.fileno())
                os.replace(temp, self.path)
            finally:
                if os.path.exists(temp): os.unlink(temp)
            return
        raise RuntimeError('Shared board changed; no operation')

    def acquire(self):
        require(not self.owners(self.raw()), 'Another chat owns the board')
        self.replace('## 当前占用', '## 当前占用\n\n' + self.line)
        self.held = True
        self.check()

    def check(self):
        require(self.held and self.owners(self.raw()) == [self.line], 'Exclusive shared lease changed')

    def release(self, result):
        if self.held:
            self.replace(self.line, self.line.replace('**占用中**', '**已释放**') +
                         '；' + stamp() + ' ' + result + '；本次实际句柄已关闭。')
            self.held = False


def fields(raw: bytes, label: str):
    rows = [dict(re.findall(r'(\w+)=([^\s]+)', row))
            for row in raw.decode(errors='replace').splitlines() if row.startswith(label + ' ')]
    require(bool(rows), 'Missing current ' + label + ' snapshot')
    return rows[-1]


def execute(args, images, factory, factory_binding):
    # Imports below do not occur for offline inspection. Importing them does
    # not connect; the explicit Session/Serial scopes own every actual handle.
    import ctypes as c
    import os
    import serial
    from serial.tools import list_ports
    from cube_programmer_api_session import Session
    from diagnose_wba_uart import collect, parse_frames
    from migrate_wba_static_ui import external_read, remove_loader
    from provision_wba_v11 import probe_lock, validate_identity, write_json
    from wba_nor_journal import JournalLock, persist_acquisition, mark_start

    out = args.output.resolve()
    project = args.project_root.resolve()
    require(out.is_relative_to(project / '.cache'), 'Private acquisition output must stay in project .cache')
    require(args.bridge_firmware is not None, 'Exact installed signed migration-bridge firmware required')
    require(not out.exists(), 'Refuse to overwrite a private migration journal')
    out.mkdir(parents=True)
    state = dict(schema='companion.wba.nor-initial-execution.v2', result='NOT_STARTED',
                 startedAt=stamp(), requiredUid=args.uid.lower(), probeSerial=PROBE,
                 target=images.report, factorySourceBinding=factory_binding,
                 wirelessOta=False, writesStarted=False, normalAfter=False,
                 verifiedInternalPages=[], verifiedNorSectors=[], ownedHandlesClosed=False)
    lease = BoardLease(project / 'docs/board_operations.md', out)
    journal_lock = JournalLock(out)
    stop, opened = threading.Event(), threading.Event()
    after_errors, monitor = [], None

    def save():
        write_json(out / 'result.json', state)

    def port_name():
        rows = [p.device for p in list_ports.comports() if p.serial_number == PROBE]
        require(len(rows) == 1, 'Fixed V3 UART absent or ambiguous')
        return rows[0]

    def start_monitor():
        # Passive startup only. No second availability query or reconnect.
        try:
            port = serial.Serial(port=None, baudrate=115200, timeout=.1)
            port.dtr = False; port.rts = False; port.port = port_name()
            with port, (out / 'after-uart.log').open('wb') as f:
                opened.set()
                while not stop.is_set():
                    data = port.read(min(max(port.in_waiting, 1), 4096))
                    if data: f.write(data); f.flush()
        except BaseException as exc:
            after_errors.append(type(exc).__name__ + ': ' + str(exc)); opened.set()

    def open_loader(probe):
        from wba_factory_writer import open_bound_loader
        return open_bound_loader(probe, out, args.loader, factory)

    def durable(path):
        with path.open('rb+') as f: f.flush(); os.fsync(f.fileno())

    save()
    try:
        journal_lock.acquire()
        lease.acquire()
        state['sharedLeaseLine'] = lease.line
        with (out / 'before-uart.log').open('wb') as f:
            collect(port_name(), 12, False, lambda data: (f.write(data), f.flush()), tail_seconds=.6)
        raw = (out / 'before-uart.log').read_bytes()
        frames, bad = parse_frames(raw)
        matches = [frame for frame in frames if frame['reason'] == 'query']
        require(bool(matches) and not bad, 'No complete normal UART query; stop without SWD')
        before = matches[-1]; s = before['sections']
        require(s['ID']['uid'] == args.uid.lower() and s['ID']['fw'] == f'{args.bridge_firmware:08x}' and
                s['ID']['ui'] == images.report['ui'], 'Normal bridge identity differs')
        require(s['AUDIO']['mic_run'] == 0 and s['BLE']['linked'] == 0 and
                s['STORAGE']['recording_ready'] == 1 and s['STORAGE']['rec_state'] in (1, 6) and
                s['STORAGE']['rec_fault'] == 0, 'Recording/radio/storage is not idle')
        require(int(s['POWER']['sleep_block'], 16) & sum(1 << bit for bit in (0, 1, 8, 11, 12, 13, 14)) == 0,
                'Protected operation is active')
        ui_state, bond = fields(raw, 'UI1'), fields(raw, 'BOND1')
        # Revision equality is a display-completion fact, not an input-idle
        # predicate. The known panel failure can leave visible_revision and visible_surface stale
        # forever while pet/standby is idle. Keep the physical/menu/touch and
        # outstanding-operation guards; never fabricate a visible completion.
        require(ui_state['surface'] in ('0', '2') and
                ui_state['touch_contact'] == ui_state['outstanding'] == '0', 'Pet/menu/touch is active')
        state['screenAtAdmission'] = ui_state
        require(bond['pending'] == bond['busy'] == '0', 'Current bond persistence is not durable/idle')
        state['normalBefore'] = before; save()
        with probe_lock(PROBE), Session(PROBE, out, lease.check, access_port=1) as probe:
            uid = probe.read(0x0BF90700, 12, 'uid.bin')
            require(validate_identity(probe.read(0xE0044000, 4, 'device-id.bin'),
                                      probe.read(0x0BF907A0, 2, 'flash-size.bin'),
                                      probe.read(0x40022040, 4, 'options.bin'), uid, TARGET) == args.uid.lower(),
                    'Actual MCU/UID differs')
            freeze = int.from_bytes(probe.read(0xE0044008, 4, 'freeze-before.bin'), 'little')
            loader_name, complete = None, False
            try:
                probe.word(0xE0044008, freeze | (1 << 12))
                original = probe.read(TARGET.flash_base, TARGET.flash_bytes, 'private-internal-before.bin')
                loader_name = open_loader(probe)
                ui = external_read(probe, 0x90000000, len(images.ui), 'before-ui.bin')
                system = external_read(probe, 0x90000000 + len(ui), SYSTEM_BYTES, 'private-metadata-before.bin')
                plan = make_plan(images, original, ui, system, uid, args.public_key.read_bytes(),
                                 factory, args.loader.read_bytes())
                require(plan['previous']['firmware'] == args.bridge_firmware, 'Live signed bridge version differs from UART')
                state['plan'] = plan
                state['livePairingPreflight'] = plan['pairing']
                # Persist exact private authority before any erase, independently
                # of the mutable public package/source paths.
                (out / 'target-internal.bin').write_bytes(images.internal)
                (out / 'current-sector.bin').write_bytes(images.current_sector)
                (out / 'retained-new-package.cup').write_bytes(images.cup)
                save()
                for name in ('uid.bin', 'device-id.bin', 'flash-size.bin', 'options.bin',
                             'freeze-before.bin', 'private-internal-before.bin', 'before-ui.bin',
                             'private-metadata-before.bin', 'target-internal.bin',
                             'current-sector.bin', 'retained-new-package.cup', 'result.json'):
                    durable(out / name)
                state['durablePrewriteAuthority'] = persist_acquisition(out, state)
                save()
                remove_loader(probe, loader_name); loader_name = None
                from wba_nor_writer import apply_plan
                apply_plan(probe, out, images, plan, original, ui, system, uid,
                           lease, state, save, open_loader)
                monitor = threading.Thread(target=start_monitor)
                monitor.start()
                require(opened.wait(5) and not after_errors, 'Passive startup UART could not open')
                complete = True
            finally:
                if loader_name: remove_loader(probe, loader_name)
                if complete or not state['writesStarted']:
                    # Releasing the watchdog freeze or issuing reset can let
                    # an App run. Publish this boundary before either action;
                    # a later missing/torn result is never erase permission.
                    mark_start(out, 'start-authorized.json', uid.hex(),
                               images.report['packageSha256'], state.get('durablePrewriteAuthority'))
                    state['startupAuthorizationPersisted'] = True; save()
                    probe.word(0xE0044008, freeze)
                    probe.reset(); state['softwareResetIssued'] = True
                else:
                    state['partialInitialInstallRetainedStopped'] = True
                    state['recovery'] = 'Preserve journal and current wiring. Explicit Owner recovery authorization required; never bypass missing normal UART automatically.'
                save()
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline and not after_errors:
            lease.check()
            raw = (out / 'after-uart.log').read_bytes()
            frames, bad = parse_frames(raw)
            if frames and not bad:
                s = frames[-1]['sections']
                if (s['ID']['uid'] == args.uid.lower() and s['ID']['fw'] == f'{images.report["firmware"]:08x}' and
                    s['ID']['ui'] == images.report['ui'] and s['STORAGE']['recording_ready'] == 1 and
                    s['STORAGE']['rec_fault'] == 0 and s['BLE']['init'] == 1 and
                    not s['CORE']['stack_guard'] and not s['CORE']['stack_low']):
                    state.update(result='WIRED_NOR_INITIAL_READBACK_AND_NORMAL_STARTUP_VERIFIED',
                                 normalAfter=True, afterSnapshot=frames[-1]); break
            time.sleep(.1)
        require(state['normalAfter'], 'No verified passive normal startup; no extra query/reset/retry')
    except BaseException as exc:
        state.update(result='WIRED_NOR_INITIAL_NOT_COMPLETED', error=type(exc).__name__ + ': ' + str(exc))
    finally:
        stop.set()
        if monitor:
            monitor.join(3)
            require(not monitor.is_alive(), 'Actual UART handle still open; keep shared lease')
        state.update(ownedHandlesClosed=True, finishedAt=stamp())
        save()
        try: lease.release(state['result'])
        finally: journal_lock.close()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'app', 'boot', 'public-key', 'source-root', 'source-repo',
                 'resource-directory', 'factory-result', 'loader', 'project-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--uid', required=True)
    parser.add_argument('--bridge-firmware', type=lambda s: int(s, 0),
                        help='Exact firmware integer of the normally running signed migration bridge')
    parser.add_argument('--execute', action='store_true', help='Explicit normal-UART-gated initial WIRED migration')
    args = parser.parse_args()
    require(len(args.uid) == 24 and all(c in '0123456789abcdefABCDEF' for c in args.uid), 'Exact explicit UID required')
    require(not args.output.exists(), 'Output must be a new private directory')
    images = inspect_target(args.package, args.app, args.boot, args.public_key.read_bytes(),
                            args.source_root, args.source_repo, args.source_commit, args.resource_directory)
    factory = load(args.factory_result)
    factory_binding = verify_build_inputs({'source_sha256': {}}, factory, args.source_root,
                                          args.source_repo, args.source_commit, args.resource_directory)
    if not args.execute:
        args.output.mkdir(parents=True)
        result = dict(result='TARGET_INSPECTED_OFFLINE_NO_DEVICE_OPENED', target=images.report,
                      factorySourceBinding=factory_binding, hardwareOperations=0, installed=False,
                      actualPairingPreflight=False, liveMigrationQualified=False)
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    else:
        result = execute(args, images, factory, factory_binding)
    print(json.dumps({key: result.get(key) for key in ('result', 'normalAfter', 'writesStarted', 'ownedHandlesClosed')}))
    raise SystemExit(0 if not args.execute or result.get('normalAfter') else 2)


if __name__ == '__main__':
    main()
