"""Compile production GATT+DOV1 and exact app_ble dispatch bodies with host AMM."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def function(text,name):
 matches=list(re.finditer(r'\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text));assert len(matches)==1,name
 start=matches[0].start()
 brace=text.index('{',start);end=brace;depth=0
 for end in range(brace,len(text)):
  if text[end]=='{':depth+=1
  if text[end]=='}':
   depth-=1
   if depth==0:return text[start:end+1]
 raise AssertionError(name)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--dispatch-source',type=Path);a=p.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 ble=ROOT/'platform/stm32wba55_companion_v11/ble';ota=ROOT/'third_party/denzic-platform/ota/embedded/c'
 app=a.dispatch_source.resolve() if a.dispatch_source else ble/'app_ble.c'
 raw=app.read_text();bodies='\n\n'.join(function(raw,'void '+name) for name in ['Ble_UserEvtRx','SVCCTL_ResumeUserEventFlow'])
 (out/'production_user_event_dispatch.inc').write_text(bodies)
 assert 'if(!user_event_flow_paused)\n          UTIL_SEQ_SetTask' in raw
 sources=[ble/'wba_ota_gatt.c',ble/'tests/test_ota_stream_backpressure.c',ota/'src/denzic_ota_v1.c',ROOT/'app/companion_pendant/recording/companion_opus16_rt.c']
 includes=[out,ble/'tests/ota_fakes',ble,ROOT/'app/companion_pendant/update',ota/'include',ROOT/'app/companion_pendant/recording',ROOT/'third_party/opus/include']
 exe=out/'stream-backpressure.exe'
 cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4295','/O2','/Gy','/MD','/DCOMP_WBA_INTERNAL_FLASH_KIB=512u','/DCOMPANION_WBA_CE_SHARED_CAPTURE=1','/DCOMPANION_OPUS16_ENCODER_BYTES=8744u',*(f'/I{x}' for x in includes),*(str(x) for x in sources),f'/Fe:{exe}','/link','/OPT:REF',str(ROOT/'.cache/opus-host-fixed/opus.lib')]
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 log=out/'build.log';run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe)],out,log)
 (out/'result.json').write_text(json.dumps(dict(result='PASS_PRODUCTION_BOUNDED_STREAM_GATE',output=result,hardware=False,newSpeedMeasurements=0,dispatchSource=str(app),sourceSha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*sources,app,ble/'wba_ota_gatt.h',Path(__file__)]}),indent=2)+'\n');print(result,end='')
if __name__=='__main__':main()
