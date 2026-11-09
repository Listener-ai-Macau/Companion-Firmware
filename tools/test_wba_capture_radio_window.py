"""Exercise production codec radio admission; DMA capture always precedes it."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];platform=root/'platform/stm32wba55_companion_v11';rec=root/'app/companion_pendant/recording'
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
for name,test in [('policy',platform/'tests/test_capture_radio_window.c')]:
 args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(platform/'tests/fakes'),'/I'+str(platform),'/I'+str(rec),str(test),'/Fe:'+str(out/(name+'.exe'))]
 batch=out/(name+'.cmd');batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
 for stage,cmd in [('compile',['cmd.exe','/d','/c',str(batch)]),('run',[str(out/(name+'.exe'))])]:
  p=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/(name+'-'+stage+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(name,stage,p.returncode,(p.stdout+p.stderr)[-1800:],flush=True);p.check_returncode()
(out/'result.json').write_text(json.dumps({'state':'PASS_CODEC_RADIO_ADMISSION_SOFTWARE_ONLY','hardwareTimingQualified':False},indent=2)+'\n')
