"""Reproduce capture starvation with the production poll and bounded dispatch."""
from pathlib import Path
import argparse,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];platform=root/'platform/stm32wba55_companion_v11';out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
raw=(platform/'microphone_hal.c').read_text();begin=raw.index('static comp_v11_microphone_poll_result_t microphone_hal_poll_body(');end=raw.index('\ncomp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(',begin)
poll=raw[begin:end];old='static bool conversion_window_open(' in raw
if old:poll=raw[raw.index('static bool conversion_window_open('):begin]+poll
template=(platform/'tests/test_microphone_capture_priority.c').read_text()
source=out/'model.c';source.write_text(('#define OLD_RADIO_CONVERT_GATE 1\n' if old else '')+template.replace('/* @PRODUCTION_POLL@ */',poll))
args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(platform/'tests/fakes'),'/I'+str(platform),'/I'+str(root/'app/companion_pendant/recording'),str(source),'/Fe:'+str(out/'test.exe')]
batch=out/'compile.cmd';batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
for stage,cmd in [('compile',['cmd.exe','/d','/c',str(batch)]),('run',[str(out/'test.exe')])]:
 r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/(stage+'.log')).write_text(r.stdout+r.stderr);print(stage,r.returncode,r.stdout+r.stderr,flush=True)
 (out/'result.json').write_text(json.dumps({'stage':stage,'exitCode':r.returncode,'oldConversionGate':old,'hardwareQualified':False},indent=2)+'\n')
 r.check_returncode()
