"""Check actual durable-notification protocol without accessing radio/board."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--opus-lib',type=Path,help='Explicit existing host Opus library for an immutable source tree')
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 ble=ROOT/'platform/stm32wba55_companion_v11/ble';ota=ROOT/'third_party/denzic-platform/ota/embedded/c'
 sources=[ble/'wba_ota_gatt.c',ble/'tests/test_ota_durable_notifications.c',ota/'src/denzic_ota_v1.c',ROOT/'app/companion_pendant/recording/companion_opus16_rt.c']
 includes=[ble/'tests/ota_fakes',ble,ROOT/'app/companion_pendant/update',ota/'include',ROOT/'app/companion_pendant/recording',ROOT/'third_party/opus/include']
 opus=(a.opus_lib or ROOT/'.cache/opus-host-fixed/opus.lib').resolve();assert opus.is_file()
 exe=out/'durable-notifications.exe';cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4295','/O2','/Gy','/MD','/DCOMP_WBA_INTERNAL_FLASH_KIB=512u','/DTEST_PUBLISH_OBSERVER=1','/DCOMPANION_WBA_CE_SHARED_CAPTURE=1','/DCOMPANION_OPUS16_ENCODER_BYTES=8744u',*(f'/I{x}' for x in includes),*(str(x) for x in sources),f'/Fe:{exe}','/link','/OPT:REF',str(opus)]
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 transcript=out/'notification-status.bin'
 log=out/'build.log';run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe),str(transcript)],out,log)
 assert 'SVCCTL_EvtAckFlowDisable' not in sources[0].read_text() and 'SVCCTL_ResumeUserEventFlow' not in sources[0].read_text()
 raw=transcript.read_bytes();assert raw and len(raw)%64==0
 (out/'result.json').write_text(json.dumps(dict(result='PASS_PRODUCTION_DURABLE_NOTIFICATION_CREDITS',output=result,hardware=False,newSpeedMeasurements=0,
  wireTranscript=dict(path=str(transcript),bytes=len(raw),frameSize=64,frames=len(raw)//64,sha256=hashlib.sha256(raw).hexdigest()),
  sourceSha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*sources,ble/'wba_ota_gatt.h',Path(__file__)]}),indent=2)+'\n');print(result,end='')
if __name__=='__main__':main()
