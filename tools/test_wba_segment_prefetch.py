#!/usr/bin/env python3
"""Bounded sealed read-ahead over real Opus and the production NOR model.

Software evidence only: no BLE/MCU/Type filesystem or timing qualification.
Freeze each attempt; a failed attempt is never overwritten by a repair.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app/companion_pendant'
REC = APP / 'recording'
NAMES = ['wba_recording_radio', 'wba_segment_pull', 'wba_segment_directory',
         'wba_recording_transfer', 'companion_recording_journal', 'wba_recording_recovery',
         'wba_recording_pipeline', 'wba_segment_storage', 'companion_continuous_recording',
         'companion_segment_audio', 'companion_range_receipt','companion_range_reclaim','companion_segment_catalog', 'companion_segment_reserve',
         'companion_opus16_rt', 'wba_segment_discard_preview', 'wba_segment_discard_worker', 'wba_segment_discard_control', 'wba_segment_discard_wire']


def run(command, out, name):
    result = subprocess.run(command, cwd=out, capture_output=True, text=True)
    (out / name).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{name}: exit {result.returncode}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def main():
    out = ROOT / '.cache/recording-core-20261011' / sys.argv[1]
    out.mkdir(parents=True, exist_ok=False)
    frozen = out / 'source'
    sources = [REC / 'tests/test_wba_segment_pull.c',
               *[REC / (n + '.c') for n in NAMES], APP / 'storage/spi_nor_stm32wba.c']
    files = set(sources) | set(APP.rglob('*.h'))
    files |= {REC / 'tests/test_wba_recording_recovery.c', REC / 'tests/test_wba_recording_pipeline.c',
              APP / 'runtime/tests/test_companion_link.c', ROOT / 'tools/fixtures/wba_nor_suspend_test.c',
              Path(__file__).resolve()}
    files |= set((ROOT / 'third_party/denzic-platform/audio/embedded/c/include').rglob('*.h'))
    hashes = {}
    for path in sorted(files):
        relative = path.relative_to(ROOT); target = frozen / relative
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
        hashes[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    (out / 'source.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    sdk = out / 'host-sdk'; sdk.mkdir()
    (sdk / 'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n')
    (sdk / 'stm32_wpan_common.h').write_text('/* Portable GATT type model only. */\n')
    includes = [sdk, *[frozen / 'app/companion_pendant' / n for n in
                      ['runtime', 'recording', 'storage', 'gatt', 'v1_features', 'playback',
                       'touch', 'epaper', 'imu', 'power']],
                frozen / 'third_party/denzic-platform/audio/embedded/c/include']
    lib = ROOT / '.cache/opus-host-fixed/opus.lib'
    args = ['cl.exe', '/nologo', '/W4', '/WX', '/std:c11', '/TC', '/O2', '/MD',
            '/DCOMPANION_OPUS16_WBA_LOWDELAY=1', '/DCOMPANION_OPUS16_ENCODER_BYTES=65536',
            *['/I' + str(p) for p in includes], '/I' + str(ROOT / 'third_party/opus/include'),
            *[str(frozen / p.relative_to(ROOT)) for p in sources],
            '/Fe:' + str(out / 'radio.exe'), '/link', str(lib)]
    cmd = out / 'compile.cmd'
    cmd.write_text('@echo off\ncall "' + str(find_vsdevcmd()) +
                   '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n' +
                   subprocess.list2cmdline(args) + '\n', encoding='ascii')
    commands = []
    try:
        run(['cmd.exe', '/d', '/c', str(cmd)], out, 'compile.txt')
        result = run([str(out / 'radio.exe'), *sys.argv[2:]], out, 'result.txt')
        cc = shutil.which('arm-none-eabi-gcc'); assert cc
        for relative in ['recording/wba_recording_pipeline.c', 'recording/wba_segment_pull.c',
                         'recording/wba_recording_transfer.c']:
            path = frozen / 'app/companion_pendant' / relative
            command = [cc, '-std=c11', '-mcpu=cortex-m33', '-mthumb', '-Os', '-Wall', '-Wextra',
                       '-Werror', '-Wconversion', '-Wshadow', '-pedantic', '-fstack-usage',
                       *['-I' + str(p) for p in includes], '-c', str(path), '-o', str(out / (path.stem + '.o'))]
            commands.append(command); run(command, out, path.stem + '-m33.txt')
        report = dict(result='PASS_PULL_PREFETCH_SOFTWARE_ONLY', softwareOutput=result,
                      physicalBoard=False, realBle=False, typeDurability=False, timingQualification=False,
                      productionAppBound=False, installed=False,
                      opusHostLibrarySha256=hashlib.sha256(lib.read_bytes()).hexdigest())
    except Exception as error:
        report = dict(result='FAILED_PULL_PREFETCH_SOFTWARE', error=str(error), installed=False)
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report)); raise
    (out / 'm33-commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
