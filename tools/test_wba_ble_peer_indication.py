"""Exercise the production indication scheduler with the captured R85 metadata."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    folder=ROOT/'platform/stm32wba55_companion_v11/ble'
    source=folder/'tests/test_ble_peer_indication.c';exe=out/'peer-indication.exe'
    cmd=['cl.exe','/nologo','/TC','/std:c11','/Zc:preprocessor','/O2','/W4','/WX',str(source),f'/Fe:{exe}']
    script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n',encoding='utf8')
    run(['cmd.exe','/d','/c',str(script)],out,out/'build.log');result=run([str(exe)],out,out/'build.log')
    (out/'result.json').write_text(json.dumps(dict(result=result,hardwareQualified=False,files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [source,folder/'ble_peer_indication.h',Path(__file__)]}),indent=2)+'\n')
    print(result,end='')
if __name__=='__main__':main()
