"""Compare the real GATT registration to its retained pre-change source."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
BLE = ROOT / 'platform/stm32wba55_companion_v11/ble'
GATT = ROOT / 'app/companion_pendant/gatt'
UPDATE = ROOT / 'app/companion_pendant/update'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-gatt', type=Path, required=True)
    parser.add_argument('--baseline-schema', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=False)
    before = args.baseline_gatt.resolve()
    old = out / 'reference.c'
    content = before.read_text(encoding='utf-8')
    names = sorted(set(re.findall(r'\b(companion_gatt_\w+)\s*\(', content)))
    prefix = ''.join(f'#define {name} reference_{name}\n' for name in names)
    baseline_schema = args.baseline_schema.resolve()
    (out/'reference-schema.h').write_bytes(baseline_schema.read_bytes())
    content = content.replace('#include "companion_gatt_schema.h"', '#include "reference-schema.h"')
    old.write_text(prefix + content, encoding='utf-8')
    official = args.sdk.resolve() / 'Middlewares/ST/STM32_WPAN/ble/stack/include'
    sources = [GATT/'companion_gatt_stm32wb.c', BLE/'wba_ota_gatt.c',
        UPDATE/'wba_update_manifest_wire.c', BLE/'tests/test_ble_memory_budget.c', old]
    includes = [BLE/'tests/ota_fakes', GATT, BLE, UPDATE, official,
        ROOT/'third_party/denzic-platform/ota/embedded/c/include',
        ROOT/'app/companion_pendant/v1_features', ROOT/'app/companion_pendant/diag_log']
    exe = out/'budget.exe'
    command = ['cl.exe','/nologo','/TC','/std:c11','/Zc:preprocessor','/O2','/W4','/WX',
        '/DCOMPANION_GATT_WBA_HOST', '/DCOMP_WBA_INTERNAL_FLASH_KIB=512u',
        '/DCOMP_WBA_INTERNAL_NVM_KIB=0u',
        '/DCOMP_WBA_BOOT_FLASH_KIB=24u',
        *(f'/I{p}' for p in includes), *(str(p) for p in sources), f'/Fe:{exe}']
    script = out/'build.cmd'
    script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n', encoding='utf-8')
    log = out/'build.log';log.write_text('', encoding='utf-8')
    run(['cmd.exe','/d','/c',str(script)], out, log)
    result = run([str(exe)], out, log)
    relevant = [*sources, before, baseline_schema, GATT/'companion_gatt_schema.h', BLE/'ble_memory_budget.h',
        BLE/'app_conf.h', BLE/'ble_conf.h', BLE/'ble_mtu.h', official/'ble_bufsize.h', Path(__file__)]
    receipt = dict(result='PASS_CE_BLE_BUDGET_SOFTWARE_ONLY', output=result,
        configuredMtu=512, recordingValueCap=509, otaFileCap=505, physicalBoard=False, installed=False,
        gattBufferBytes=7860, previousGattBufferBytes=8076, savedBytes=216, hostBufferBytes=3880,
        officialP2pPools=dict(hostBytes=7784,gattBytes=4448,links=8,mtu=251,
            scope='Calculated using pinned SDK macros and official app_conf.h, not a full example build'),
        coldRegistrationQualification='REQUIRES_ACTUAL_STACK; host fake does not emulate allocator',
        sourceSha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in relevant})
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n', encoding='utf-8')
    print(result, end='')

if __name__=='__main__':main()
