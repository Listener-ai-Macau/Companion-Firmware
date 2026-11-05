#!/usr/bin/env python3
"""Exercise the product coordinator with real portable modules and fake I/O."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app/companion_pendant'
INCLUDES = [APP / d for d in ('runtime', 'runtime/generated', 'playback', 'touch', 'epaper', 'imu', 'power')]
INCLUDES += [ROOT / 'third_party/denzic-platform/audio/embedded/c/include']
SOURCES = [APP / p for p in ('runtime/companion_runtime.c', 'runtime/companion_pet_chat.c', 'playback/audio_feedback.c',
    'playback/speaker_playback.c', 'touch/touch_gesture.c', 'touch/touch_tap_arbiter.c',
    'touch/browser_interaction_runtime.c', 'epaper/screen_menu.c', 'epaper/screen_framebuffer.c',
    'epaper/motion_coordinator.c', 'power/power_settings_store.c')]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--battery-only',action='store_true')
    parser.add_argument('--recording-pause-only',action='store_true')
    parser.add_argument('--recording-start-only',action='store_true')
    parser.add_argument('--attempt',default='20261012')
    args=parser.parse_args()
    narrow_recording=args.recording_pause_only or args.recording_start_only
    out = ROOT / ('.cache/wba-recording-start-runtime-'+args.attempt if args.recording_start_only else
                  '.cache/wba-recording-pause-runtime-'+args.attempt if args.recording_pause_only else
                  '.cache/wba-battery-runtime' if args.battery_only else '.cache/wba-product-runtime')
    out.mkdir(parents=True, exist_ok=not narrow_recording)
    log = out / 'build.log'
    log.write_text('', encoding='utf-8')
    report = {'result': 'FAIL', 'hardwareAcceptance': 'NOT_RUN', 'fullChainAcceptance': 'NOT_RUN'}
    try:
        devcmd = find_vsdevcmd()
        if not devcmd: raise RuntimeError('MSVC unavailable')
        exe = out / 'test_runtime.exe'
        test = APP / 'runtime/tests/test_companion_runtime.c'
        sources=SOURCES;includes=INCLUDES;frozen_hashes={}
        if narrow_recording:
            frozen=out/'source'
            files={*SOURCES,test,Path(__file__)}
            for folder in INCLUDES:files.update(folder.rglob('*.h'))
            for path in files:
                target=frozen/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(path.read_bytes());frozen_hashes[str(path.relative_to(ROOT))]=hashlib.sha256(target.read_bytes()).hexdigest()
            sources=[frozen/p.relative_to(ROOT) for p in SOURCES]
            test=frozen/test.relative_to(ROOT);includes=[frozen/p.relative_to(ROOT) for p in INCLUDES]
            (out/'source.json').write_text(json.dumps(frozen_hashes,indent=2)+'\n')
        cc_args = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', '/utf-8',
                '/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
                *(f'/I{p}' for p in includes), *(str(p) for p in [*sources, test]), f'/Fe:{exe}']
        # Existing compile-time pet-motion branches intentionally contain a
        # constant operand; the battery-only fixture does not exercise them.
        if args.battery_only or narrow_recording:cc_args.extend(['/wd4127','/wd4100'])
        if narrow_recording:cc_args.extend(['/DCOMPANION_WBA_RESOURCE_PROFILE=0','/DCOMPANION_RECORDING_SEGMENTED_ONLY=1'])
        script = out / 'build.cmd'
        script.write_text(f'@echo off\ncall "{devcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
                          'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(cc_args) + '\n')
        run(['cmd.exe', '/d', '/c', str(script)], out, log)
        result = run([str(exe),*(['--recording-start-only'] if args.recording_start_only else
                               ['--recording-pause-only'] if args.recording_pause_only else
                               ['--battery-only'] if args.battery_only else [])], out, log)
        print(result, end='')
        if ('PASS_RECORDING_START_CLOCK' if args.recording_start_only else 'PASS_CAPTURE_PAUSE_RUNTIME' if args.recording_pause_only else 'PASS_BATTERY_RUNTIME' if args.battery_only else 'PASS_PREHARDWARE_RUNTIME') not in result: raise RuntimeError('Test completion missing')
        cc = shutil.which('arm-none-eabi-gcc')
        if not cc: raise RuntimeError('Cortex M33 compiler missing')
        for i, source in enumerate(sources):
            if (args.battery_only or narrow_recording) and source.name!='companion_runtime.c':continue
            run([cc, '-std=c11', '-mcpu=cortex-m33', '-mthumb', '-Os', '-Wall', '-Wextra', '-Werror',
                 *(['-DCOMPANION_WBA_RESOURCE_PROFILE=0', '-DCOMPANION_RECORDING_SEGMENTED_ONLY=1', '-Wno-unused-function'] if narrow_recording else []),
                 '-DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1', *(f'-I{p}' for p in includes),
                 '-c', str(source), '-o', str(out / f'{i}-{source.stem}.o')], out, log)
        report.update(result='PASS_PREHARDWARE_SOFTWARE_ONLY', tests=result.splitlines(),
            source_sha256=frozen_hashes or {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [*SOURCES, test, Path(__file__), *INCLUDES[0].glob('*.h'), *INCLUDES[1].glob('*.h')]})
    except (OSError, RuntimeError) as e:
        report['error'] = str(e)
        print(e)
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return int(report['result'] == 'FAIL')

if __name__ == '__main__': raise SystemExit(main())
