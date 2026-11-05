from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
O=a.output.resolve();O.mkdir(exist_ok=False)
fixture=R/'platform/stm32wba55_companion_v11/ble/tests/test_ble_radio_activity_profile.c'
header=fixture.parent.parent/'ble_radio_activity_profile.h';exe=O/'radio-activity.exe'
cmd=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX',str(fixture),'/Fe:'+str(exe)]
script=O/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
run(['cmd.exe','/d','/c',str(script)],O,O/'build.log')
q=subprocess.run([str(exe)],cwd=O,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'run.log').write_bytes(q.stdout)
s=dict(result='PASS' if q.returncode==0 else 'FAIL',exitCode=q.returncode,physicalBoard=False,
 scope='Exact production inline counter; timestamps supplied, not physical callback latency or calibrated RF time.',
 sourceSha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [fixture,header,Path(__file__)]})
(O/'result.json').write_text(json.dumps(s,indent=2)+'\n');print(q.stdout.decode(errors='replace'));raise SystemExit(q.returncode)
