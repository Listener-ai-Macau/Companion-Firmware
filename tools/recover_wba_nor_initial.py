"""Inspect a retained failed wired migration; explicit recovery is separate.

Default operation is offline. --recover-interrupted-migration is ONLY for a
concrete interrupted install retained by this installer, with separate
current Owner authorization. It is never selected by a failed UART query and
is never an alternative reset mode or a blank-device/old-image recovery.

V2 installers retain independent pre-write acquisition/phase evidence and a
process-lifetime journal lock. A missing/torn diagnostic result alone is never
authority. Legacy V1 still requires its finalized retained-stopped failure.
Any marker allowing the App to start forbids another erase, even without UART.
Host-loss recovery implementation still requires physical qualification.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import threading
import time

from install_wba_nor_initial import BoardLease, PROBE
from wba_nor_initial import (SYSTEM_BYTES, TARGET, TargetImages, exact, inspect_target,
                             load, make_plan, make_resume_plan, require, sha,
                             verify_build_inputs)
from wba_nor_journal import (AUTHORITY, JournalLock, read_acquisition, require_unstarted,
                             mark_start)


def stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


@dataclass(repr=False)
class Authority:
    state: dict
    uid: bytes
    internal: bytes
    ui: bytes
    system: bytes
    plan: dict
    report: dict


def retained_authority(original: Path, project: Path, images: TargetImages,
                       public_xy: bytes, factory: dict, loader: bytes) -> Authority:
    original, project = original.resolve(), project.resolve()
    require(original.is_relative_to(project / '.cache'), 'Private original journal must stay in project .cache')
    require_unstarted(original)
    durable = None
    if (original / AUTHORITY).exists():
        # This acquisition was published before the first erase. The mutable
        # result can be absent/torn following host loss; it is not reconstructed
        # into a made-up finalized failure or used as authority.
        state, durable = read_acquisition(original)
        try: diagnostic = load(original / 'result.json')
        except (ValueError, FileNotFoundError): diagnostic = {}
        require(diagnostic.get('normalAfter') is not True and diagnostic.get('softwareResetIssued') is not True,
                'Original install completed or may already have started; do not recover a working product')
        journal_mode = 'durable-prewrite-v2'
    else:
        state = load(original / 'result.json')
        require(state.get('schema') == 'companion.wba.nor-initial-execution.v1', 'Not an original wired migration journal')
        require(state.get('normalAfter') is False and state.get('result') == 'WIRED_NOR_INITIAL_NOT_COMPLETED',
                'Original install completed or has no finalized failure; do not recover a working product')
        require(state.get('writesStarted') is True and state.get('partialInitialInstallRetainedStopped') is True and
                state.get('softwareResetIssued') is not True and state.get('ownedHandlesClosed') is True,
                'No finalized retained-stopped V1 authority; host loss needs a V2 acquisition')
        journal_mode = 'legacy-finalized-stopped-v1'
    uid = exact(original, 'uid.bin', 12)
    require(uid.hex() == state.get('requiredUid') and state.get('probeSerial') == PROBE,
            'Original fixed probe/UID differs')
    target = state.get('target', {})
    for key in ('packageSha256', 'internalTargetSha256', 'appSha256', 'bootSha256',
                'uiSha256', 'firmware', 'ui', 'layout'):
        require(target.get(key) == images.report.get(key), 'Retained target differs: ' + key)
    require(exact(original, 'retained-new-package.cup') == images.cup and
            exact(original, 'target-internal.bin', TARGET.flash_bytes) == images.internal and
            exact(original, 'current-sector.bin', 4096) == images.current_sector,
            'Original retained signed target is incomplete or changed')
    internal = exact(original, 'private-internal-before.bin', TARGET.flash_bytes)
    ui = exact(original, 'before-ui.bin')
    system = exact(original, 'private-metadata-before.bin', SYSTEM_BYTES)
    plan = make_plan(images, internal, ui, system, uid, public_xy, factory, loader)
    recorded = state.get('plan', {})
    for key in ('uid', 'beforeInternalSha256', 'beforeSystemSha256', 'beforeUiSha256',
                'loaderSha256', 'protectedBondRange', 'orderedOperations', 'allowedNorSectorOffsets'):
        require(recorded.get(key) == plan.get(key), 'Original mutation authority differs: ' + key)
    before = state.get('normalBefore', {}).get('sections', {})
    require(before.get('ID', {}).get('uid') == uid.hex() and
            before['ID'].get('fw') == f'{plan["previous"]["firmware"]:08x}' and
            before['ID'].get('ui') == images.report['ui'], 'Original normal bridge identity is absent')
    require(before.get('AUDIO', {}).get('mic_run') == 0 and before.get('BLE', {}).get('linked') == 0 and
            before.get('STORAGE', {}).get('recording_ready') == 1 and
            before['STORAGE'].get('rec_fault') == 0, 'Original normal idle admission is absent')
    report = dict(result='RETAINED_FAILED_MIGRATION_AUTHORITY_QUALIFIED_OFFLINE',
                  uid=uid.hex(), originalDirectory=str(original),
                  packageSha256=images.report['packageSha256'], internalTargetSha256=sha(images.internal),
                  originalReceiptSha256=(sha(exact(original, 'result.json')) if (original / 'result.json').exists() else None),
                  journalMode=journal_mode, durableAuthority=durable,
                  mutableDiagnosticUsedAsAuthority=(durable is None),
                  originalInternalSha256=sha(internal), originalSystemSha256=sha(system), originalUiSha256=sha(ui),
                  privatePayloadExported=False, ownerPermissionInferred=False,
                  actualAcquisitionOrRecoveryProven=False)
    return Authority(state, uid, internal, ui, system, plan, report)


def execute(args, images: TargetImages, factory: dict, authority: Authority) -> dict:
    # Explicit, separately authorized failed-install work only. No admission
    # query, automatic fallback or repeated attach is implemented here.
    import serial
    from serial.tools.list_ports import comports
    from cube_programmer_api_session import Session
    from diagnose_wba_uart import parse_frames
    from migrate_wba_static_ui import external_read, remove_loader
    from provision_wba_v11 import probe_lock, validate_identity, write_json
    from wba_factory_writer import open_bound_loader
    from wba_nor_writer import apply_plan

    out, project = args.output.resolve(), args.project_root.resolve()
    require(out.is_relative_to(project / '.cache') and not out.exists(), 'New private recovery output required')
    require(out != args.original.resolve(), 'Never overwrite original failure evidence')
    out.mkdir(parents=True)
    lease = BoardLease(project / 'docs/board_operations.md', out,
                       '显式原始失败迁移续装；非普通UART失联兜底，原配对保护，Boot最后')
    journal_lock = JournalLock(args.original.resolve())
    state = dict(schema='companion.wba.nor-initial-recovery.v1', result='NOT_STARTED', startedAt=stamp(),
                 authority=authority.report, writesStarted=False, normalAfter=False,
                 verifiedInternalPages=[], verifiedNorSectors=[], ownedHandlesClosed=False,
                 uartQueryCommands=0, blankDevice=False, oldImageRollback=False)
    stop, opened = threading.Event(), threading.Event()
    errors, monitor = [], None

    def save(): write_json(out / 'result.json', state)

    def original_unchanged():
        require_unstarted(args.original)
        if authority.report['journalMode'] == 'durable-prewrite-v2':
            _, current = read_acquisition(args.original)
            require(current == authority.report['durableAuthority'], 'Immutable original authority changed')
        else:
            require(sha(exact(args.original, 'result.json')) == authority.report['originalReceiptSha256'],
                    'Original finalized V1 authority changed')

    def marker(name):
        # Immutable original publication boundary: a later missing result does
        # not turn a possibly running product into another erase candidate.
        mark_start(args.original, name, authority.uid.hex(), images.report['packageSha256'],
                   authority.report.get('durableAuthority') or
                   {'originalReceiptSha256': authority.report['originalReceiptSha256']}, out)

    def listen():
        try:
            ports = [p.device for p in comports() if p.serial_number == PROBE]
            require(len(ports) == 1, 'Fixed V3 passive UART absent/ambiguous')
            port = serial.Serial(port=None, baudrate=115200, timeout=.1)
            port.dtr = port.rts = False; port.port = ports[0]
            with port, (out / 'after-uart.log').open('wb') as log:
                opened.set()
                while not stop.is_set():
                    data = port.read(min(max(port.in_waiting, 1), 4096))
                    if data: log.write(data); log.flush()
        except BaseException as e: errors.append(repr(e)); opened.set()

    def loader(probe): return open_bound_loader(probe, out, args.loader, factory)

    save()
    try:
        # A live installer/recovery holds this OS lock even after it drops the
        # SWD lock to wait for UART. A PID or stale shared row is insufficient.
        journal_lock.acquire()
        original_unchanged()
        if authority.report['journalMode'] == 'durable-prewrite-v2':
            # Only the exact original lease can be retired, after proving the
            # original operation no longer holds its lifetime OS lock. Other
            # chats/rows are never removed, regardless of their timestamp.
            original_line = authority.state['sharedLeaseLine']
            owners = lease.owners(lease.raw())
            if owners == [original_line]:
                lease.replace(original_line, original_line.replace('**占用中**', '**已释放**') +
                    '；' + stamp() + ' 显式原迁移恢复已取得原作业OS锁，旧主机作业不再持锁；交由新独占重新核实现场。')
                state['originalLeaseRetiredAfterLifetimeLockAcquired'] = True; save()
        lease.acquire()
        with probe_lock(PROBE), Session(PROBE, out, lease.check, access_port=1) as probe:
            uid = probe.read(0x0BF90700, 12, 'uid.bin')
            require(validate_identity(probe.read(0xE0044000, 4, 'device-id.bin'),
                                      probe.read(0x0BF907A0, 2, 'flash-size.bin'),
                                      probe.read(0x40022040, 4, 'options.bin'), uid, TARGET) == authority.uid.hex(),
                    'Physical failed target identity differs')
            require((out / 'options.bin').read_bytes() == exact(args.original, 'options.bin', 4),
                    'Original debug/security/watchdog options changed')
            freeze = int.from_bytes(probe.read(0xE0044008, 4, 'freeze-before.bin'), 'little')
            registered, complete = None, False
            try:
                probe.word(0xE0044008, freeze | (1 << 12))
                internal = probe.read(TARGET.flash_base, TARGET.flash_bytes, 'private-interrupted-internal.bin')
                registered = loader(probe)
                ui = external_read(probe, 0x90000000, len(images.ui), 'ui-before.bin')
                system = external_read(probe, 0x90000000 + len(ui), SYSTEM_BYTES, 'private-system-before.bin')
                require(ui == authority.ui, 'Resource changed; this recovery does not move UI')
                plan = make_resume_plan(images, authority.internal, authority.ui, authority.system,
                                        internal, system, uid, args.public_key.read_bytes(), factory,
                                        args.loader.read_bytes())
                original_unchanged()
                state['liveResumePlan'] = plan
                state['liveReadbackQualifiedBeforeMutation'] = True; save()
                remove_loader(probe, registered); registered = None
                # The helper consumes only the remaining bounded ranges. It
                # never reconstructs or overwrites a newer external pairing.
                apply_plan(probe, out, images, plan, authority.internal, ui, system, uid,
                           lease, state, save, loader)
                monitor = threading.Thread(target=listen); monitor.start()
                require(opened.wait(5) and not errors, 'Passive startup UART unavailable; no retry')
                marker('recovery-start-authorized.json')
                complete = True
            finally:
                if registered: remove_loader(probe, registered)
                if complete:
                    # Restore the original pre-install freeze value, not the
                    # interrupted session's temporary IWDG freeze.
                    original_freeze = int.from_bytes(exact(args.original, 'freeze-before.bin', 4), 'little')
                    probe.word(0xE0044008, original_freeze)
                    probe.reset(); state['softwareResetIssued'] = True
                else:
                    # Keep IWDG frozen and the target halted on an incomplete
                    # explicit recovery. Unfreezing can cause a later reset.
                    state['retainedStoppedWithoutAdditionalReset'] = True
                save()
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline and not errors:
            lease.check()
            frames, bad = parse_frames((out / 'after-uart.log').read_bytes())
            if frames and not bad:
                s = frames[-1]['sections']
                if (s['ID']['uid'] == authority.uid.hex() and s['ID']['fw'] == f'{images.report["firmware"]:08x}' and
                    s['ID']['ui'] == images.report['ui'] and s['BLE']['init'] == 1 and
                    s['STORAGE']['recording_ready'] == 1 and not s['STORAGE']['rec_fault'] and
                    not s['CORE']['stack_low'] and not s['CORE']['stack_guard']):
                    state.update(result='EXPLICIT_INTERRUPTED_MIGRATION_READBACK_AND_STARTUP_VERIFIED',
                                 normalAfter=True, afterSnapshot=frames[-1]); break
            time.sleep(.1)
        require(state['normalAfter'], 'No qualified passive startup; preserve both journals and do not retry')
        marker('recovery-completed.json')
    except BaseException as e:
        state.update(result='EXPLICIT_INTERRUPTED_MIGRATION_NOT_COMPLETED', error=repr(e))
    finally:
        stop.set()
        if monitor:
            monitor.join(3); require(not monitor.is_alive(), 'UART still open; retain shared lease')
        state.update(ownedHandlesClosed=True, uartErrors=errors, finishedAt=stamp()); save()
        try: lease.release(state['result'])
        finally: journal_lock.close()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'app', 'boot', 'public-key', 'source-root', 'source-repo',
                 'resource-directory', 'factory-result', 'loader', 'project-root', 'original', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--recover-interrupted-migration', action='store_true',
                        help='Only after current Owner authorization for this concrete retained failed install; never inferred from UART loss')
    args = parser.parse_args()
    try:
        images = inspect_target(args.package, args.app, args.boot, args.public_key.read_bytes(),
                                args.source_root, args.source_repo, args.source_commit, args.resource_directory)
        factory = load(args.factory_result)
        binding = verify_build_inputs({'source_sha256': {}}, factory, args.source_root,
                                      args.source_repo, args.source_commit, args.resource_directory)
        authority = retained_authority(args.original, args.project_root, images,
                                       args.public_key.read_bytes(), factory, args.loader.read_bytes())
    except (ValueError, FileNotFoundError) as exc:
        # Only this pre-device branch may report zero device operations. A
        # later output/cleanup exception must never be relabelled as admission.
        print(json.dumps(dict(result='REFUSED_BEFORE_DEVICE_ACCESS',error=str(exc),deviceOperations=0),ensure_ascii=False))
        return 2
    if args.recover_interrupted_migration:
        result = execute(args, images, factory, authority)
    else:
        require(not args.output.exists(), 'Offline report output must be new')
        args.output.mkdir(parents=True)
        result = dict(result=authority.report['result'], authority=authority.report,
                      factorySourceBinding=binding, deviceOperations=0, recovered=False,
                      separatelyAuthorizedRecoveryRequired=True)
        (args.output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result.get(k) for k in ('result','normalAfter','writesStarted','deviceOperations')},ensure_ascii=False))
    return 0 if not args.recover_interrupted_migration or result.get('normalAfter') else 2


if __name__ == '__main__':
    raise SystemExit(main())
