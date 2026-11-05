"""Reproduce single-tail loss of access, then exercise the real reader/consume.

Portable NOR/Opus model only; never modifies a physical device or original.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
from test_wba_recording_product import NAMES
from verify_wba_spi_nor_adapter import find_vsdevcmd

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--opus-lib',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--case',choices=['baseline','candidate','runtime'],required=True);a=ap.parse_args()
 root=Path(__file__).resolve().parents[1];src=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 app=src/'app/companion_pendant';rec=app/'recording';sdk=out/'sdk';sdk.mkdir()
 (sdk/'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n');(sdk/'stm32_wpan_common.h').write_text('/* public-type model */\n')
 test=rec/'tests/test_wba_runtime_recovery.c'if a.case=='runtime'else root/'app/companion_pendant/recording/tests/test_wba_salvage_isolation.c'
 sources=[test,app/'runtime/companion_link.c',*[rec/(n+'.c')for n in NAMES],app/'storage/spi_nor_stm32wba.c']
 includes=[sdk,rec,rec/'tests',*[app/n for n in ['runtime','storage','gatt','v1_features','playback','touch','epaper','imu','power']],src/'third_party/denzic-platform/audio/embedded/c/include',src/'third_party/opus/include']
 cmd=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD','/utf-8','/DCOMP_WBA_INTERNAL_FLASH_KIB=0','/DCOMPANION_RECORDING_SEGMENTED_ONLY=1','/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536','/DCOMP_NOR_FIXTURE_BYTES=1048576',f'/DTEST_FIXED={0 if a.case=="baseline"else 1}',*['/I'+str(p)for p in includes],*map(str,sources),'/Fe:'+str(out/'test.exe'),'/link',str(a.opus_lib.resolve())]
 (out/'inputs.json').write_text(json.dumps(dict(source=str(src),case=a.case,inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},opusLibSha256=hashlib.sha256(a.opus_lib.read_bytes()).hexdigest()),indent=2)+'\n')
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 result=dict(result='RUNNING',case=a.case,hardwareOperations=0,physicalNorCorruption=False,audioQualityOrTimingQualified=False)
 for stage,command in [('build',[os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)]),('run',[str(out/'test.exe')])]:
  with(out/(stage+'.log')).open('xb')as log:
   p=subprocess.Popen(command,cwd=out,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:code=p.wait(timeout=120 if stage=='build'else 45)
   except subprocess.TimeoutExpired:p.kill();p.wait();code=124
  result[stage+'ExitCode']=code
  if code:
   result['result']='FAILED_PRESERVED';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print((out/(stage+'.log')).read_text(errors='replace')[-1700:]);raise SystemExit(code)
 result.update(result='REPRODUCED745_LOSS_OF_INTACT_ORIGINAL_ACCESS'if a.case=='baseline'else 'PASS_SALVAGE_ISOLATION_SOFTWARE_ONLY',output=(out/'run.log').read_text(errors='replace'))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
