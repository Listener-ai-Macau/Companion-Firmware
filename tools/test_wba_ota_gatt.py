from pathlib import Path
import argparse,hashlib,json,subprocess
from wba_flash_geometry import MCUS,for_mcu,SOURCE as GEOMETRY_SOURCE,HEADER as GEOMETRY_HEADER
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
BLE=ROOT/'platform/stm32wba55_companion_v11/ble'
UPDATE=ROOT/'app/companion_pendant/update'
def main():
    parser=argparse.ArgumentParser(description='Host-only signed OTA GATT contract for CE/CG')
    parser.add_argument('--mcu',choices=MCUS,default='STM32WBA55CEU6')
    parser.add_argument('--output',type=Path)
    options=parser.parse_args();geometry=for_mcu(options.mcu)
    out=options.output.resolve() if options.output else ROOT/'.cache/wba-ota-gatt-host';out.mkdir(parents=True,exist_ok=True)
    log=out/'build.log';log.write_text('')
    sources=[BLE/'wba_ota_gatt.c',BLE/'tests/test_ota_gatt.c',UPDATE/'wba_update_manifest_wire.c']
    includes=[BLE/'tests/ota_fakes',BLE,UPDATE,ROOT/'third_party/denzic-platform/ota/embedded/c/include']
    exe=out/'test_ota_gatt.exe';args=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u',*(f'/I{p}' for p in includes),*(str(p) for p in sources),f'/Fe:{exe}']
    script=out/'build.cmd';script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe)],out,log);print(result,end='')
    report={'result':'PASS_HOST_ONLY','mcu':geometry.mcu,'internal_flash_geometry':geometry.receipt(),'hardwareAcceptance':'NOT_RUN','tests':result,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,BLE/'wba_ota_gatt.h',UPDATE/'wba_update_service.h',GEOMETRY_SOURCE,GEOMETRY_HEADER,*list((BLE/'tests/ota_fakes').glob('*.h')),Path(__file__)]}}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
