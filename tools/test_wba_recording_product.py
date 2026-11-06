#!/usr/bin/env python3
"""Affected radio/runtime scenario over real Opus and the production NOR model.

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
         'companion_segment_audio', 'companion_segment_catalog', 'companion_segment_reserve',
         'companion_opus16_rt', 'wba_recording_product', 'wba_segment_discard_preview',
         'wba_segment_discard_worker', 'wba_segment_discard_control', 'wba_segment_discard_wire']


def run(command, out, name):
    result = subprocess.run(command, cwd=out, capture_output=True, text=True)
    (out / name).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{name}: exit {result.returncode}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def main():
    out = ROOT / '.cache/recording-core-20261011' / sys.argv[1]
    out.mkdir(exist_ok=False)
    frozen = out / 'source'
    capacity_only='--pause-capacity' in sys.argv[2:]
    selected_only='--selected-discard' in sys.argv[2:]
    bookmarks_only='--bookmarks' in sys.argv[2:]
    sources = [REC / ('tests/test_wba_recording_bookmarks.c' if bookmarks_only else 'tests/test_wba_recording_pause_capacity.c' if capacity_only else 'tests/test_wba_recording_product.c'), APP / 'runtime/companion_link.c',
               *[REC / (n + '.c') for n in NAMES], APP / 'storage/spi_nor_stm32wba.c']
    files = set(sources) | set(APP.rglob('*.h'))
    files |= {REC / 'tests/test_wba_recording_product.c', REC / 'tests/test_wba_recording_radio.c', REC / 'tests/test_wba_recording_recovery.c', REC / 'tests/test_wba_recording_pipeline.c',
              REC / 'tests/test_wba_recording_pause_capacity.c',
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
    # New MSVC warns C5287 for an existing cross-enum static assertion even
    # with explicit integer casts. The assertion itself remains evaluated.
    args = ['cl.exe', '/nologo', '/W4', '/WX', '/wd5287', '/std:c11', '/TC', '/O2', '/MD',
            '/DCOMPANION_OPUS16_WBA_LOWDELAY=1', '/DCOMPANION_OPUS16_ENCODER_BYTES=65536',
            *(['/DCOMP_NOR_FIXTURE_BYTES=1048576'] if capacity_only or bookmarks_only else []),
            *(['/DCOMPANION_RECORDING_SEGMENTED_ONLY=1'] if selected_only or capacity_only or bookmarks_only or any(a in sys.argv[2:] for a in ['--local-control','--logical-control','--pause-control','--initial-status','--workspace-restart','--terminal-cause']) else []),
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
        logical_only = '--logical-control' in sys.argv[2:]
        local_only='--local-control' in sys.argv[2:]
        pause_only='--pause-control' in sys.argv[2:]
        initial_only='--initial-status' in sys.argv[2:]
        workspace_only='--workspace-restart' in sys.argv[2:]
        terminal_only='--terminal-cause' in sys.argv[2:]
        wide_only='--wide-index' in sys.argv[2:]
        result = run([str(out / 'radio.exe')]+(['selected-discard'] if selected_only else ['wide-index'] if wide_only else ['terminal-cause','terminal-cause.cms3'] if terminal_only else ['engine-bookmarks.cmb3'] if bookmarks_only else ['local-control','local-control.cms3'] if local_only else ['workspace-restart'] if workspace_only else ['initial-status'] if initial_only else ['pause-control','pause-control.cpc3'] if pause_only else
            ['logical-control'] if logical_only else []), out, 'result.txt')
        cc = shutil.which('arm-none-eabi-gcc'); assert cc
        for relative in ['runtime/companion_link.c', 'recording/wba_recording_radio.c',
                         'recording/wba_recording_pipeline.c', 'recording/wba_segment_pull.c',
                         'recording/wba_recording_transfer.c', 'recording/wba_recording_product.c',
                         *(['recording/wba_segment_discard_preview.c','recording/wba_segment_discard_control.c','recording/wba_segment_discard_wire.c'] if selected_only else []),
                         *(['recording/companion_continuous_recording.c','recording/companion_segment_audio.c'] if capacity_only or bookmarks_only else [])]:
            if capacity_only and relative not in ['recording/companion_continuous_recording.c','recording/wba_recording_pipeline.c']:continue
            if local_only and relative not in ['runtime/companion_link.c','recording/wba_recording_product.c']:continue
            if initial_only and relative!='runtime/companion_link.c':continue
            if workspace_only and relative!='recording/wba_recording_product.c':continue
            if logical_only and relative not in ['runtime/companion_link.c','recording/wba_recording_product.c']:continue
            path = frozen / 'app/companion_pendant' / relative
            command = [cc, '-std=c11', '-mcpu=cortex-m33', '-mthumb', '-Os', '-Wall', '-Wextra',
                       '-Werror', '-Wconversion', '-Wshadow', '-pedantic', '-fstack-usage',
                       *['-I' + str(p) for p in includes], '-c', str(path), '-o', str(out / (path.stem + '.o'))]
            commands.append(command); run(command, out, path.stem + '-m33.txt')
            if relative in ['runtime/companion_link.c','recording/wba_recording_transfer.c']:
                production=command[:-2]+['-DCOMPANION_RECORDING_SEGMENTED_ONLY=1','-o',str(out/(path.stem+'-product.o'))]
                commands.append(production);run(production,out,path.stem+'-product-m33.txt')
        report = dict(result='PASS_PRODUCT_PORTS_SOFTWARE_ONLY', softwareOutput=result,
                      physicalBoard=False, realBle=False, typeDurability=False, timingQualification=False,
                      productionAppBound=True, installed=False,
                      opusHostLibrarySha256=hashlib.sha256(lib.read_bytes()).hexdigest())
    except Exception as error:
        report = dict(result='FAILED_RADIO_RUNTIME_SOFTWARE', error=str(error), installed=False)
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report)); raise
    (out / 'm33-commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
