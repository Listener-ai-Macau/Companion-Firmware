#!/usr/bin/env python3
"""Exercise TX-pool wake ordering and fallback deadlines; no hardware access."""
from pathlib import Path
import shutil
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
BLE = ROOT / 'platform/stm32wba55_companion_v11/ble'
OUT = ROOT / '.cache/stopped-upload-20261008/tx-gate'


def run(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    vs = find_vsdevcmd()
    cc = shutil.which('arm-none-eabi-gcc')
    if not vs or not cc:
        raise RuntimeError('MSVC and ARM GNU compilers required')
    source = BLE / 'tests/test_ble_tx_gate.c'
    executable = OUT / 'test-ble-tx-gate.exe'
    command = ['cl.exe', '/nologo', '/TC', '/std:c11', '/O2', '/W4', '/WX',
               f'/I{BLE}', str(source), f'/Fo:{OUT / "test.obj"}', f'/Fe:{executable}']
    script = OUT / 'compile.cmd'
    script.write_text(f'@call "{vs}" -arch=amd64 -host_arch=amd64 >nul\n'
                      '@if errorlevel 1 exit /b %errorlevel%\n'
                      + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
    output = run(['cmd.exe', '/d', '/c', str(script)]) + run([str(executable)])
    run([cc, '-std=c11', '-mcpu=cortex-m33', '-mthumb', '-Os', '-Wall', '-Wextra',
         '-Werror', '-Wconversion', '-Wshadow', f'-I{BLE}', '-c', str(source),
         '-o', str(OUT / 'test-m33.o')])
    (OUT / 'test.log').write_text(output, encoding='utf-8')
    print(output.strip())


if __name__ == '__main__':
    main()
