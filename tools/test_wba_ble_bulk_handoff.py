"""Exercise the production bulk function at mocked official ACI boundaries."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 source=ROOT/'platform/stm32wba55_companion_v11/ble/app_ble.c'
 fixture=source.parent/'tests/test_ble_bulk_handoff.c'
 text=source.read_text();start=text.index('void comp_v11_ble_bulk_profile(')
 # Stop at this function's unindented closing brace, not a later diagnostic
 # symbol: the installed source contains a trace dumper between the two.
 end=text.index('\n}',text.index('{',start))+2;body=text[start:end]+'\n'
 assert body.count('{')==body.count('}'), 'Unbalanced production function extraction'
 (out/'production_bulk_profile.inc').write_text(body,encoding='utf-8')
 exe=out/'bulk-handoff.exe';cmd=['cl.exe','/nologo','/TC','/std:c11','/Zc:preprocessor','/O2','/W4','/WX',f'/I{out}',str(fixture),f'/Fe:{exe}']
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n',encoding='utf-8')
 log=out/'build.log';run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe)],out,log)
 (out/'result.json').write_text(json.dumps(dict(result='PASS_PRODUCTION_BULK_HANDOFF_SOFTWARE_ONLY',output=result,physicalBoard=False,installed=False,
  sourceSha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,fixture,Path(__file__)]}),indent=2)+'\n',encoding='utf-8')
 print(result,end='')
if __name__=='__main__':main()
