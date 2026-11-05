"""Check the production OTA receipt cache and its real DOV1 durability barrier."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--real-encoder-arena',action='store_true');a=p.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 ble=ROOT/'platform/stm32wba55_companion_v11/ble';ota=ROOT/'third_party/denzic-platform/ota/embedded/c'
 sources=[ble/'wba_ota_gatt.c',ble/'tests/test_ota_status_barrier.c',ota/'src/denzic_ota_v1.c']
 includes=[ble/'tests/ota_fakes',ble,ROOT/'app/companion_pendant/update',ota/'include']
 flags=[]
 if a.real_encoder_arena:
  sources.append(ROOT/'app/companion_pendant/recording/companion_opus16_rt.c')
  includes += [ROOT/'app/companion_pendant/recording',ROOT/'third_party/opus/include']
  flags=['/O2','/Gy','/MD','/DCOMPANION_WBA_CE_SHARED_CAPTURE=1','/DCOMPANION_OPUS16_ENCODER_BYTES=8744u']
 exe=out/'receipt-cache.exe'
 # C4295 is the pre-existing fixed four-byte wire magic, not this change.
 cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4295','/DCOMP_WBA_INTERNAL_FLASH_KIB=512u',*flags,*(f'/I{x}' for x in includes),*(str(x) for x in sources),f'/Fe:{exe}']
 if a.real_encoder_arena:cmd += ['/link','/OPT:REF',str(ROOT/'.cache/opus-host-fixed/opus.lib')]
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 log=out/'build.log';run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe)],out,log)
 (out/'result.json').write_text(json.dumps(dict(result='PASS_PRODUCTION_OTA_CACHE_DURABLE_BARRIER',output=result,hardware=False,newSpeedMeasurements=0,sourceSha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*sources,ble/'wba_ota_gatt.h',Path(__file__)]}),indent=2)+'\n')
 print(result,end='')
if __name__=='__main__':main()
