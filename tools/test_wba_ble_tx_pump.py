#!/usr/bin/env python3
"""Check the sealed-send task against the actual ST sequencer, without a board."""
from pathlib import Path
import argparse
from datetime import datetime
import hashlib
import json
import re
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
BLE = ROOT / 'platform/stm32wba55_companion_v11/ble'
REC = ROOT / 'app/companion_pendant/recording'
SDK = ROOT / '.cache/deps/STM32CubeWBA/Utilities/sequencer'
OUT = None


def run(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
        default=ROOT / '.cache' / ('tx-pump-' + datetime.now().strftime('%Y%m%d-%H%M%S')))
    OUT = parser.parse_args().output.resolve()
    OUT.mkdir(parents=True, exist_ok=False)
    vs = find_vsdevcmd()
    if not vs:
        raise RuntimeError('MSVC compiler required')
    # MSVC has no weak function override. Remove only the two empty default
    # hooks in a cache copy; scheduler and nested-event logic remain verbatim.
    # Never mutate the SDK used to build production firmware.
    original = (SDK / 'stm32_seq.c').read_text(encoding='utf-8')
    native = original
    for hook in ('PreTask', 'PostTask'):
        native, count = re.subn(
            rf'__WEAK void UTIL_SEQ_{hook}\( uint32_t TaskId \)\s*'
            r'\{\s*\(void\)TaskId;\s*return;\s*\}', '', native)
        assert count == 1, hook
    (OUT / 'stm32_seq_native.c').write_text(native, encoding='utf-8')
    (OUT / 'utilities_conf.h').write_text(
        '#include <string.h>\n#define __WEAK\n#define __CORTEX_M 0\n'
        '#define UTIL_SEQ_INIT_CRITICAL_SECTION()\n'
        '#define UTIL_SEQ_ENTER_CRITICAL_SECTION()\n'
        '#define UTIL_SEQ_EXIT_CRITICAL_SECTION()\n'
        '#define UTILS_MEMSET8(dest,value,size) memset(dest,value,size)\n', encoding='utf-8')
    source = BLE / 'tests/test_ble_tx_pump.c'
    executable = OUT / 'test-ble-tx-pump.exe'
    command = ['cl.exe', '/nologo', '/TC', '/std:c11', '/O2', '/W4', '/WX',
               f'/I{BLE}', f'/I{REC}', f'/I{SDK}', f'/I{OUT}',
               str(source), str(OUT / 'stm32_seq_native.c'),
               f'/Fo:{OUT}\\', f'/Fe:{executable}']
    script = OUT / 'compile.cmd'
    script.write_text(f'@call "{vs}" -arch=amd64 -host_arch=amd64 >nul\n'
                      '@if errorlevel 1 exit /b %errorlevel%\n'
                      + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
    output = run(['cmd.exe', '/d', '/c', str(script)]) + run([str(executable)])
    (OUT / 'test.log').write_text(output, encoding='utf-8')
    (OUT / 'result.json').write_text(json.dumps({
        'result': 'PASS_NATIVE_SCHEDULER_ONLY', 'hardwareTested': False,
        'sdkSourceSha256': hashlib.sha256((SDK / 'stm32_seq.c').read_bytes()).hexdigest(),
        'nativeAdaptation': 'Remove only empty weak PreTask/PostTask definitions for MSVC linking; fixture supplies the product owner hooks.',
        'checks': 6, 'scope': 'Queue scheduling, backpressure/event ordering, nested waits, foreground yielding and exclusions; no air throughput claim.',
    }, indent=2) + '\n', encoding='utf-8')
    print(output.strip())


if __name__ == '__main__':
    main()
