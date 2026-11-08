"""Exercise production radio admission and the actual HAL queue-retention helper."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];platform=root/'platform/stm32wba55_companion_v11';rec=root/'app/companion_pendant/recording'
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
raw=(platform/'microphone_hal.c').read_text();start=raw.index('static bool conversion_window_open(');end=raw.index('static comp_v11_microphone_poll_result_t microphone_hal_poll_body(',start);helper=raw[start:end]
poll=raw[end:];assert poll.index('if (!conversion_window_open(microphone))')<poll.index('if (!pop_event(microphone, &event))')
template=(platform/'tests/test_microphone_conversion_window.c').read_text();assert template.count('/* @PRODUCTION_CONVERSION_WINDOW@ */')==1
source=out/'hal.c';source.write_text(template.replace('/* @PRODUCTION_CONVERSION_WINDOW@ */',helper),encoding='utf-8')
for name,test in [('policy',platform/'tests/test_capture_radio_window.c'),('hal',source)]:
 args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(platform/'tests/fakes'),'/I'+str(platform),'/I'+str(rec),str(test),'/Fe:'+str(out/(name+'.exe'))]
 batch=out/(name+'.cmd');batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
 for stage,cmd in [('compile',['cmd.exe','/d','/c',str(batch)]),('run',[str(out/(name+'.exe'))])]:
  p=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/(name+'-'+stage+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(name,stage,p.returncode,(p.stdout+p.stderr)[-1800:],flush=True);p.check_returncode()
(out/'result.json').write_text(json.dumps({'state':'PASS_POLICY_AND_PRODUCTION_HAL_QUEUE_RETENTION_SOFTWARE_ONLY','helperSha256':hashlib.sha256(helper.encode()).hexdigest(),'queueNotPoppedBeforeAdmission':True,'hardwareTimingQualified':False},indent=2)+'\n')
