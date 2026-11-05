"""First installation of Companion V1.1 WBA55. Default: offline validation only.

Execution requires an explicit board and ST-LINK serial. Never changes option
bytes, mass-erases, or uses the old WB55 flash layout. Nonblank product data is
refused, not reformatted. Resume is bound to the original UID and blank backups.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from wba_flash_geometry import FlashGeometry, for_mcu, from_receipt
from wba_resource_geometry import geometry as resource_geometry

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_GEOMETRY = for_mcu()
INTERNAL_BASE, INTERNAL_BYTES, NVM_OFFSET = _DEFAULT_GEOMETRY.flash_base, _DEFAULT_GEOMETRY.flash_bytes, _DEFAULT_GEOMETRY.nvm_offset
NOR_BASE, NOR_BYTES, UI_BYTES = 0x90000000, 0x1000000, 0x200000
BOARD = 'companion-v1.1-wba55'
SWD_FREQUENCIES = (50, 1000, 4000, 8000)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, value: dict):
    # Atomic checkpoint replacement: never truncate a usable resume record.
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
        handle.flush(); os.fsync(handle.fileno())
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        move = kernel.MoveFileExW
        move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        move.restype = ctypes.c_int
        # Same-volume atomic rename with Windows' write-through completion.
        if not move(str(temporary.resolve()), str(path.resolve()), 0x1 | 0x8):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)

def sync_backup(path: Path, expected: bytes):
    with path.open('r+b') as handle:
        if handle.read() != expected:
            raise RuntimeError('Backup differs from preflight readback: ' + str(path))
        handle.flush(); os.fsync(handle.fileno())

def member(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or Path(name).is_absolute():
        raise ValueError('Package path escapes directory')
    return target

class Package:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        manifest_bytes = (self.directory / 'manifest.json').read_bytes()
        self.manifest_sha256 = sha(manifest_bytes)
        self.manifest = m = json.loads(manifest_bytes)
        self.geometry = from_receipt(m, allow_legacy_cg=True)
        if (m.get('schema') != 'companion.wba.v11.prehardware.delivery.v1' or
            m.get('board') != 'Companion V1.1 2026-09-19' or
            m.get('initial_combined_load_address') != '0x08000000' or m.get('load_address') != f'0x{self.geometry.app_address:08X}'):
            raise ValueError('Not a Companion V1.1 WBA55 package/layout')
        self.internal_path = member(self.directory, 'companion-v11-initial-boot-and-app.bin')
        self.ui_path = member(self.directory, 'resource-ota/ui-partition.bin')
        self.internal, self.ui = self.internal_path.read_bytes(), self.ui_path.read_bytes()
        for name, data in [('companion-v11-initial-boot-and-app.bin', self.internal), ('resource-ota/ui-partition.bin', self.ui)]:
            if m.get('files', {}).get(name) != sha(data):
                raise ValueError('Package hash mismatch: ' + name)
        if sha(self.internal) != m.get('initial_combined_sha256') or sha(self.internal[self.geometry.boot_bytes:]) != m.get('bin_sha256'):
            raise ValueError('Boot/app identity mismatch')
        profile = m.get('ui_resource_profile', {})
        self.flash_geometry = m.get('flash_geometry')
        if self.flash_geometry is not None:
            if self.flash_geometry != resource_geometry(len(self.ui)):
                raise ValueError('Static/dynamic geometry differs from resource bank')
        elif len(self.ui) != UI_BYTES:
            raise ValueError('Variable resource bank requires matched layout geometry')
        if len(self.internal) <= self.geometry.boot_bytes+8 or len(self.internal) > self.geometry.nvm_offset:
            raise ValueError('Image extent exceeds target partition')
        if profile.get('uiPartitionBytes') != len(self.ui) or str(profile.get('uiPartitionSha256', '')).lower() != sha(self.ui):
            raise ValueError('UI profile mismatch')
        for offset, end in [(0, self.geometry.boot_bytes), (self.geometry.boot_bytes, len(self.internal))]:
            stack, reset = struct.unpack_from('<II', self.internal, offset)
            if not (self.geometry.valid_stack_pointer(stack) and reset & 1 and
                    INTERNAL_BASE + offset <= (reset & ~1) < INTERNAL_BASE + end):
                raise ValueError('Invalid boot/app vector table')

def validate_loader(directory: Path, geometry: FlashGeometry | None = None) -> Path:
    geometry = geometry or for_mcu()
    report = json.loads((directory / 'result.json').read_text(encoding='utf-8'))
    if report.get('schema') != 'companion.wba.factory-loader.v1' or report.get('result') != 'PASS_BUILD_ONLY':
        raise ValueError('Missing factory loader build identity')
    # Old loaders explicitly checked 1024KiB. They are never CE-compatible,
    # even though their external NOR geometry is identical.
    if report.get('mcu') is None:
        if geometry.flash_kib != 1024:
            raise ValueError('Legacy factory loader requires CG capacity; CE loader required')
    elif from_receipt(report) != geometry:
        raise ValueError('Factory loader MCU capacity differs from package')
    loader = member(directory, report['loader'])
    if sha(loader.read_bytes()) != report['loader_sha256']:
        raise ValueError('Factory loader hash mismatch')
    if (report.get('read_base') != NOR_BASE or report.get('read_bytes') != NOR_BYTES or
        report.get('write_bytes') != UI_BYTES or report.get('mass_erase') != 'REFUSED'):
        raise ValueError('Unsafe loader partition contract')
    parsed = json.loads((directory / 'st-parse-result.json').read_text(encoding='utf-8'))
    if (parsed.get('result') != 'PASS_ST_OFFLINE_LOADER_PARSE_ONLY' or
        parsed.get('loader_sha256') != report['loader_sha256']):
        raise ValueError('Missing/mismatched ST loader parse evidence')
    return loader

def validate_identity(device_id: bytes, flash_size: bytes, options: bytes, uid: bytes,
                      geometry: FlashGeometry | None = None) -> str:
    geometry = geometry or for_mcu()
    if len(device_id) != 4 or len(flash_size) != 2 or len(options) != 4 or len(uid) != 12:
        raise ValueError('Incomplete device identity read')
    if struct.unpack('<I', device_id)[0] & 0xfff != 0x492 or struct.unpack('<H', flash_size)[0] != geometry.flash_kib:
        raise ValueError('Wrong MCU family/capacity; refuse old WB55 or another target')
    optr = struct.unpack('<I', options)[0]
    if optr & 0x80000000 or optr & 0xff != 0xaa or not optr & 0x10000:
        raise ValueError('Requires TZEN=0, RDP=0xAA, software IWDG; option bytes will NOT be changed')
    if uid == bytes(12) or uid == bytes([255]) * 12:
        raise ValueError('Invalid MCU UID')
    return uid.hex()

class Programmer:
    """Official CLI wrapper; opt into HOTPLUG for reads that must not reset.

    HOTPLUG does not itself halt the CPU. Callers that need a coherent halted
    snapshot must explicitly arrange the halt, watchdog freeze and cleanup.
    Existing factory callers retain their original connection policy.
    """
    def __init__(self, executable: Path, serial: str, loader: Path, output: Path,
                 nrst_connected: bool = False, frequency_khz: int = 1000,
                 hotplug: bool = False):
        if frequency_khz not in SWD_FREQUENCIES:
            raise ValueError('Unsupported requested SWD frequency')
        self.executable, self.serial, self.loader, self.output = executable, serial, loader, output
        self.nrst_connected = nrst_connected
        self.frequency_khz = frequency_khz
        self.hotplug = hotplug
        self.index = 0

    def connection_identity(self):
        return {'transport': 'SWD', 'nrst_connected': self.nrst_connected,
                'mode': 'HOTPLUG' if self.hotplug else ('UR' if self.nrst_connected else 'NORMAL'),
                'reset': None if self.hotplug else ('HWrst' if self.nrst_connected else 'SWrst'),
                'frequency_khz': self.frequency_khz}

    def call(self, args: list[str], external=False):
        self.index += 1
        connection = self.connection_identity()
        command = [str(self.executable), '-c', 'port=SWD', 'mode=' + connection['mode']]
        if connection['reset'] is not None:
            command += ['reset=' + connection['reset']]
        command += ['freq=' + str(connection['frequency_khz']), 'sn=' + self.serial]
        if external:
            command += ['-el', str(self.loader)]
        command += args
        log = self.output / f'{self.index:03d}-programmer.log'
        print(f'[{self.index}] {"SPI3 NOR" if external else "MCU"}: {args[0]}', flush=True)
        try:
            # A full 16MiB read over a real SWD probe can exceed three minutes.
            # Keep a finite external-loader deadline rather than killing a
            # healthy large transfer at the internal-Flash command deadline.
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900 if external else 180)
        except subprocess.TimeoutExpired as exc:
            partial = ''.join(part.decode('utf-8', errors='replace') if isinstance(part, bytes) else str(part)
                              for part in (exc.stdout or b'', exc.stderr or b''))
            log.write_text('TIMEOUT\n' + str(exc) + '\n' + partial, encoding='utf-8')
            raise RuntimeError('Programmer timed out; target is not reset to run') from exc
        log.write_text(subprocess.list2cmdline(command) + '\n' + result.stdout + result.stderr, encoding='utf-8')
        if result.returncode or re.search(r'(?im)^\s*Error\s*:', result.stdout + result.stderr):
            hint = ('; HOTPLUG preserved the target reset state; no automatic reset fallback was attempted'
                    if self.hotplug else
                    '; six-pin SWD uses NORMAL/SWrst without NRST; a target that disables SWD or remains in deep sleep may require separately wired NRST'
                    if not self.nrst_connected else '')
            raise RuntimeError('Programmer failed; see ' + str(log) + hint)

    def read(self, address: int, size: int, name: str, external=False) -> bytes:
        path = self.output / name
        if path.exists():
            raise RuntimeError('Readback file already exists: ' + str(path))
        self.call(['-u', hex(address), str(size), str(path)], external)
        data = path.read_bytes()
        if len(data) != size:
            raise RuntimeError('Truncated readback ' + name)
        return data

    def write(self, path: Path, address: int, external=False):
        # SPI NOR verification uses the explicit full Read callback/readback
        # below, avoiding CubeProgrammer's optional Verify/CheckSum ABI.
        self.call(['-d', str(path), hex(address)] + ([] if external else ['-v']), external)

    def halt(self):
        # Live inspection must opt into HOTPLUG; otherwise the connection
        # itself resets the MCU before this explicit halt reaches it.
        if not self.hotplug:
            raise RuntimeError('Explicit no-reset halt requires HOTPLUG')
        self.call(['-halt'])

    def run(self):
        if not self.hotplug:
            raise RuntimeError('Explicit no-reset resume requires HOTPLUG')
        self.call(['-run'])

    def reset(self):
        # A six-pin V/C/G/D/RX/TX header has no NRST. Software system reset
        # through the debug port is distinct from UART reset/ROM programming.
        self.call(['-hardRst' if self.nrst_connected else '-rst', '-run'])

def blank(data: bytes) -> bool:
    return data.count(255) == len(data)

def exact_internal(actual: bytes, desired: bytes, geometry: FlashGeometry | None = None) -> bool:
    geometry = geometry or for_mcu()
    return len(actual) == geometry.flash_bytes and len(desired) <= geometry.nvm_offset and \
        actual[:len(desired)] == desired and blank(actual[len(desired):geometry.nvm_offset])

def interrupted_program(actual: bytes, desired: bytes) -> bool:
    # Erased 0xff -> requested bits, possibly interrupted partway through a
    # page/word. Extra cleared bits cannot come from writing this image.
    return len(actual) == len(desired) and all((a & d) == d for a, d in zip(actual, desired))

def install(package: Package, programmer, output: Path, resume: Path | None = None) -> dict:
    """Actual readbacks, never process exit code alone, establish install success."""
    if getattr(package, 'flash_geometry', None) is not None:
        # This legacy blank-board installer never writes CFL3 roots or relocates
        # dynamic settings. Refuse before board access rather than install a
        # bank whose matching app cannot mount its dynamic storage.
        raise ValueError('Layout3 requires a matched boot/app/resource and CFL3 formatter; legacy initial installer cannot initialize this geometry')
    geometry = package.geometry
    internal_bytes, nvm_offset = geometry.flash_bytes, geometry.nvm_offset
    uid = validate_identity(
        programmer.read(0xE0044000, 4, 'device-id.bin'), programmer.read(0x0BF907A0, 2, 'flash-size.bin'),
        programmer.read(0x40022040, 4, 'option-bytes.bin'), programmer.read(0x0BF90700, 12, 'uid.bin'), geometry)
    internal = programmer.read(INTERNAL_BASE, internal_bytes, 'before-internal.bin')
    nor = programmer.read(NOR_BASE, NOR_BYTES, 'before-nor.bin', True)
    report = {'schema': 'companion.wba.factory-install.v1', 'result': 'IN_PROGRESS', 'uid': uid,
        'mcu': geometry.mcu, 'internal_flash_geometry': geometry.receipt(),
        'package_manifest_sha256': package.manifest_sha256, 'fullChainAcceptance': 'NOT_RUN',
        'hardwareAcceptance': 'NOT_RUN', 'writes_started': False, 'reset_to_app': False,
        'before_internal_sha256': sha(internal), 'before_nor_sha256': sha(nor)}
    if hasattr(programmer, 'connection_identity'):
        report['debug_connection'] = programmer.connection_identity()
    if exact_internal(internal, package.internal, geometry) and nor[:UI_BYTES] == package.ui:
        report['result'] = 'ALREADY_INSTALLED_READBACK_VERIFIED'
        # Reads leave the core halted; resume the verified existing product too.
        programmer.reset()
        report['reset_to_app'] = True
        write_json(output / 'result.json', report)
        return report
    if resume is None:
        if not blank(internal) or not blank(nor):
            raise RuntimeError('Initial install requires blank MCU and NOR; existing data preserved. Use OTA for an installed product.')
        origin = output
        checkpoint = dict(report, phase='prepared')
    else:
        origin = resume.resolve()
        previous = json.loads((origin / 'checkpoint.json').read_text(encoding='utf-8'))
        checkpoint = previous
        first_internal, first_nor = (origin / 'before-internal.bin').read_bytes(), (origin / 'before-nor.bin').read_bytes()
        if (previous.get('uid') != uid or previous.get('package_manifest_sha256') != package.manifest_sha256 or
            len(first_internal) != internal_bytes or len(first_nor) != NOR_BYTES or
            sha(first_internal) != previous.get('before_internal_sha256') or sha(first_nor) != previous.get('before_nor_sha256') or
            not blank(first_internal) or not blank(first_nor)):
            raise RuntimeError('Resume does not match the original blank board/package')
        if not blank(internal[nvm_offset:]) or not blank(nor[UI_BYTES:]) or not blank(internal[len(package.internal):nvm_offset]):
            raise RuntimeError('Board contains new data since initial attempt; resume refused')
        phase = previous.get('phase')
        if phase not in ('prepared', 'ui_write_pending', 'firmware_write_pending'):
            raise RuntimeError('Unknown resume phase')
        if phase == 'prepared' and (not blank(internal) or not blank(nor)):
            raise RuntimeError('Board changed before authorized write phase')
        if phase == 'ui_write_pending' and not blank(internal):
            raise RuntimeError('Internal image changed during UI-only phase')
        if phase == 'firmware_write_pending' and nor[:UI_BYTES] != package.ui:
            raise RuntimeError('Previously verified UI changed; resume refused')
        if (not interrupted_program(internal[:len(package.internal)], package.internal) or
            not interrupted_program(nor[:UI_BYTES], package.ui)):
            raise RuntimeError('Writable region contains incompatible data, not an interrupted package write')
    # A recoverable, UID-bound blank backup exists BEFORE the first destructive action.
    if resume is None:
        sync_backup(output / 'before-internal.bin', internal)
        sync_backup(output / 'before-nor.bin', nor)
        write_json(output / 'checkpoint.json', checkpoint)
    report['original_blank_backup'] = str(origin)
    # Program the already validated bytes, not mutable source paths that another
    # build/copy could replace after preflight.
    images = output / 'install-images'
    images.mkdir()
    internal_image, ui_image = images / 'boot-and-app.bin', images / 'ui.bin'
    internal_image.write_bytes(package.internal)
    ui_image.write_bytes(package.ui)
    report['writes_started'] = True
    write_json(output / 'result.json', report)
    try:
        # Populate assets first; only install boot/app after exact resource readback.
        if nor[:UI_BYTES] != package.ui:
            checkpoint['phase'] = 'ui_write_pending'
            write_json(origin / 'checkpoint.json', checkpoint)
            programmer.write(ui_image, NOR_BASE, True)
        ui_after = programmer.read(NOR_BASE, UI_BYTES, 'verified-ui.bin', True)
        if ui_after != package.ui:
            raise RuntimeError('UI readback differs; firmware will not be written')
        if not exact_internal(internal, package.internal, geometry):
            checkpoint['phase'] = 'firmware_write_pending'
            write_json(origin / 'checkpoint.json', checkpoint)
            programmer.write(internal_image, INTERNAL_BASE)
        after_internal = programmer.read(INTERNAL_BASE, internal_bytes, 'after-internal.bin')
        after_nor = programmer.read(NOR_BASE, NOR_BYTES, 'after-nor.bin', True)
        if (not exact_internal(after_internal, package.internal, geometry) or after_nor[:UI_BYTES] != package.ui or
            after_internal[nvm_offset:] != internal[nvm_offset:] or after_nor[UI_BYTES:] != nor[UI_BYTES:]):
            raise RuntimeError('Readback mismatch or protected region changed; target not started')
        report.update(after_internal_sha256=sha(after_internal), after_nor_sha256=sha(after_nor),
                      protected_regions_unchanged=True, result='PASS_INSTALL_READBACK_ONLY')
        programmer.reset()
        report['reset_to_app'] = True
    except Exception as exc:
        report.update(result='FAIL_INSTALL', error=str(exc))
        raise
    finally:
        write_json(output / 'result.json', report)
    return report

@contextmanager
def probe_lock(serial: str):
    # Process-lifetime OS lock, not a stale PID file. No deletion of user files.
    import msvcrt
    path = Path(tempfile.gettempdir()) / ('companion-wba-swd-' + sha(serial.encode())[:16] + '.lock')
    with path.open('a+b') as handle:
        if path.stat().st_size == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path, help='Extracted WBA package directory')
    parser.add_argument('--loader-dir', type=Path, help='Capacity-matched loader; default selects CE or legacy CG directory from package identity')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--board', choices=[BOARD])
    parser.add_argument('--probe-serial')
    parser.add_argument('--nrst-connected', action='store_true',
                        help='Explicitly select under-reset/HWrst only when NRST is separately wired; six-pin default is NORMAL/SWrst')
    parser.add_argument('--swd-frequency', type=int, choices=SWD_FREQUENCIES, default=1000,
                        help='Requested official SWD frequency in kHz; use a faster value only after successful reads')
    parser.add_argument('--programmer', type=Path, default=Path('C:/ST/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', type=Path, help='Original failed initial-install directory with blank backups')
    args = parser.parse_args()
    out = args.output or ROOT / '.cache/wba-factory/runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Output directory must be empty; --resume names the previous attempt separately')
    out.mkdir(parents=True, exist_ok=True)
    try:
        package = Package(args.package)
        loader_directory = args.loader_dir or ROOT / ('.cache/wba-factory/loader-ce' if package.geometry.flash_kib == 512 else '.cache/wba-factory/loader')
        loader = validate_loader(loader_directory.resolve(), package.geometry)
        plan = {'schema': 'companion.wba.factory-plan.v1', 'result': 'PASS_OFFLINE_PREFLIGHT_ONLY',
            'mcu': package.geometry.mcu, 'internal_flash_geometry': package.geometry.receipt(),
            'board': BOARD, 'package_manifest_sha256': package.manifest_sha256,
            'internal_image_sha256': sha(package.internal), 'ui_image_sha256': sha(package.ui),
            'loader_sha256': sha(loader.read_bytes()), 'internal_address': hex(INTERNAL_BASE), 'ui_virtual_address': hex(NOR_BASE),
            'blank_board_required': True, 'option_byte_writes': False, 'mass_erase': False,
            'debug_connection': {'transport': 'SWD', 'nrst_connected': args.nrst_connected,
                                 'mode': 'UR' if args.nrst_connected else 'NORMAL',
                                 'reset': 'HWrst' if args.nrst_connected else 'SWrst',
                                 'frequency_khz': args.swd_frequency},
            'hardwareAcceptance': 'NOT_RUN', 'fullChainAcceptance': 'NOT_RUN', 'flashed': False}
        write_json(out / 'plan.json', plan)
        if not args.execute:
            print(json.dumps(plan, indent=2)); print(out / 'plan.json'); return 0
        if args.board != BOARD or not args.probe_serial or not re.fullmatch(r'[A-Za-z0-9_-]{4,80}', args.probe_serial):
            raise ValueError('--execute requires --board companion-v1.1-wba55 and the explicit --probe-serial')
        if not args.programmer.is_file():
            raise ValueError('STM32CubeProgrammer executable missing')
        with probe_lock(args.probe_serial):
            result = install(package, Programmer(args.programmer.resolve(), args.probe_serial, loader, out,
                                                nrst_connected=args.nrst_connected, frequency_khz=args.swd_frequency), out, args.resume)
        print(json.dumps(result, indent=2)); return 0
    except Exception as exc:
        # Preserve richer progress/failure records produced by install().
        if not (out / 'result.json').exists():
            write_json(out / 'result.json', {'result': 'FAIL_PRECHECK', 'error': str(exc), 'hardwareAcceptance': 'NOT_RUN'})
        print('REFUSED/FAILED: ' + str(exc)); return 1

if __name__ == '__main__':
    raise SystemExit(main())
