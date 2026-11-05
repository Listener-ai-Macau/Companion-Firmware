"""Compile and run malformed product-GATT event tests without hardware."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
BLE=ROOT/'platform/stm32wba55_companion_v11/ble'
GATT=ROOT/'app/companion_pendant/gatt'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--capability-only',action='store_true')
    parser.add_argument('--completion-only',action='store_true')
    options=parser.parse_args()
    out=options.output.resolve() if options.output else ROOT/'.cache/wba-product-gatt-faults-host'
    out.mkdir(parents=True,exist_ok=not bool(options.output))
    log=out/'build.log';log.write_text('',encoding='utf-8')
    sources=[GATT/'companion_gatt_stm32wb.c',BLE/'tests/test_product_gatt_faults.c']
    includes=[BLE/'tests/ota_fakes',GATT,ROOT/'app/companion_pendant/v1_features',
        ROOT/'app/companion_pendant/diag_log']
    exe=out/'test.exe';args=['cl.exe','/nologo','/std:c11','/W4','/WX','/DCOMPANION_GATT_WBA_HOST',
        *(f'/I{p}' for p in includes),*(str(p) for p in sources),f'/Fe:{exe}']
    script=out/'build.cmd';script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
    assert not (options.capability_only and options.completion_only)
    run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe),*(['completion'] if options.completion_only else ['capability'] if options.capability_only else [])],out,log);print(result,end='')
    paths=[*sources,GATT/'companion_gatt_stm32wb.h',
        ROOT/'app/companion_pendant/v1_features/companion_wire_v1.h',
        ROOT/'app/companion_pendant/diag_log/diag_log.h',
        ROOT/'app/companion_pendant/diag_log/diag_log_events.h',
        *list((BLE/'tests/ota_fakes').glob('*.h')),Path(__file__)]
    receipt={'result':'PASS_HOST_ONLY','hardwareAcceptance':'NOT_RUN','tests':result,
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(out/'result.json')
if __name__=='__main__':main()
