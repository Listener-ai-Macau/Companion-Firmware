"""Check validity boundaries of the production bounded dispatch observer."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 ble=ROOT/'platform/stm32wba55_companion_v11/ble';source=ble/'tests/test_dispatch_profile.c';exe=out/'dispatch.exe'
 cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{ble}',str(source),f'/Fe:{exe}']
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 log=out/'build.log';run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe)],out,log)
 (out/'result.json').write_text(json.dumps(dict(result='PASS_PRODUCTION_DISPATCH_VALIDITY_BOUNDARIES',output=result,hardware=False,newSpeedMeasurements=0,sourceSha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [source,ble/'ble_dispatch_profile.h',Path(__file__)]}),indent=2)+'\n')
 print(result,end='')
if __name__=='__main__':main()
