#!/usr/bin/env python3
"""Storage-state regression, using portable Opus/NOR; no MCU/timing claims.

Optionally reproduce the old lock with --control-source <frozen old source>.
Each invocation needs a fresh output label; failed attempts are preserved.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from test_wba_recording_product import NAMES
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    parser.add_argument('--control-source', type=Path)
    parser.add_argument('--full-only', action='store_true', help='Run only the affected empty-full control and storage case')
    args = parser.parse_args()
    if Path(args.label).name != args.label or args.label in ('', '.', '..'):
        parser.error('label must be one fresh directory name')
    output = ROOT / '.cache/recording-empty-full' / args.label
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    if args.control_source:
        cases.append(('control', args.control_source.resolve(), 0))
    cases += [('candidate', ROOT, 1)]
    if not args.full_only:
        cases += [('stoppedFaultRecovery', ROOT, 1)]
    library = ROOT / '.cache/opus-host-fixed/opus.lib'
    if not library.is_file():
        # Frozen source trees deliberately do not vendor generated libraries.
        parser.error('portable native Opus library missing: ' + str(library))
    results = []
    report = dict(result='RUNNING', hardwareOperations=0, installed=False,
                  realAudio=False, timingQualified=False, codecParityQualified=False,
                  ceMemoryLayoutQualified=False,
                  hostProfile='portable lowdelay Opus; roomy native arena; storage ownership only',
                  opusLibrarySha256=hashlib.sha256(library.read_bytes()).hexdigest())
    for label, source, fixed in cases:
        target = output / label
        target.mkdir()
        sdk = target / 'sdk'
        sdk.mkdir()
        (sdk / 'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n')
        (sdk / 'stm32_wpan_common.h').write_text('/* native public-type model */\n')
        app = source / 'app/companion_pendant'
        rec = app / 'recording'
        test = rec / 'tests/test_wba_runtime_recovery.c' if label == 'stoppedFaultRecovery' else ROOT / 'app/companion_pendant/recording/tests/test_wba_empty_full_recovery.c'
        sources = [test, app / 'runtime/companion_link.c',
                   *[rec / (name + '.c') for name in NAMES], app / 'storage/spi_nor_stm32wba.c']
        includes = [sdk, rec, rec / 'tests', *[app / name for name in
                    ('runtime', 'storage', 'gatt', 'v1_features', 'playback', 'touch', 'epaper', 'imu', 'power')],
                    source / 'third_party/denzic-platform/audio/embedded/c/include',
                    source / 'third_party/opus/include']
        command = ['cl.exe', '/nologo', '/W4', '/WX', '/wd5287', '/std:c11', '/TC', '/O2', '/MD',
                   '/DCOMP_WBA_INTERNAL_FLASH_KIB=0', '/DCOMPANION_RECORDING_SEGMENTED_ONLY=1',
                   '/DCOMPANION_OPUS16_WBA_LOWDELAY=1', '/DCOMPANION_OPUS16_ENCODER_BYTES=65536',
                   '/DCOMP_NOR_FIXTURE_BYTES=1048576', f'/DTEST_FIXED={fixed}',
                   *['/I' + str(p) for p in includes], *map(str, sources),
                   '/Fe:' + str(target / 'test.exe'), '/link', str(library)]
        (target / 'inputs.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sources}, indent=2) + '\n')
        script = target / 'build.cmd'
        script.write_text('@echo off\ncall "' + str(find_vsdevcmd()) +
                '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n' +
                subprocess.list2cmdline(command) + '\n')
        for stage, cmd in [('compile', ['cmd.exe', '/d', '/c', str(script)]),
                           ('run', [str(target / 'test.exe')])]:
            with (target / (stage + '.log')).open('xb') as log:
                process = subprocess.Popen(cmd, cwd=target, stdout=log, stderr=subprocess.STDOUT,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    code = process.wait(timeout=45 if stage == 'run' else 120)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    code = 124
            if code:
                report.update(result='FAILED_PRESERVED', case=label, stage=stage, exitCode=code)
                (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
                raise RuntimeError(f'{label}/{stage}: {code}\n' + (target / (stage + '.log')).read_text(errors='replace')[-1800:])
        results.append(dict(case=label, output=(target / 'run.log').read_text(errors='replace')))
    report.update(result='PASS_STORAGE_OWNERSHIP_ONLY', cases=results)
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
