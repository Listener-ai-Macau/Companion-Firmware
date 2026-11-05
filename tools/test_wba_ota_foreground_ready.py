"""Reproduce queued OTA work missing from the production idle predicate.

Compiles the actual GATT adapter and exact production predicate, with only
hardware/ACI and unrelated display/sequencer readiness represented by fakes.
No radio, timing/rate claim, board operation or firmware installation.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
from test_wba_ota_stream_backpressure import function
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rows=[];fixture=ROOT/'platform/stm32wba55_companion_v11/ble/tests/test_ota_foreground_ready.c'
    for label,source,expected in [('baseline',a.baseline_source.resolve(),0),('fixed',ROOT,1)]:
        dest=out/label;dest.mkdir();ble=source/'platform/stm32wba55_companion_v11/ble'
        idle=source/'platform/stm32wba55_companion_v11/low_power_target.c'
        predicate=function(idle.read_text(),'static bool foreground_pending')
        (dest/'production_foreground_pending.inc').write_text(predicate+'\n')
        sources=[ble/'wba_ota_gatt.c',fixture]
        includes=[dest,ble/'tests/ota_fakes',ble,source/'app/companion_pendant/update',source/'third_party/denzic-platform/ota/embedded/c/include']
        exe=dest/'ota-foreground-ready.exe'
        cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4295','/DCOMP_WBA_INTERNAL_FLASH_KIB=512u',f'/DEXPECT_OTA_READY={expected}',*(f'/I{x}' for x in includes),*(str(x) for x in sources),f'/Fe:{exe}']
        script=dest/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
        log=dest/'build.log';run(['cmd.exe','/d','/c',str(script)],dest,log);result=run([str(exe)],dest,log)
        rows.append(dict(label=label,expectedOtaReady=expected,output=result,sourceSha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*sources,idle,ble/'wba_ota_gatt.h',Path(__file__)]}))
    report=dict(result='BASELINE_QUEUED_OTA_IDLE_OMISSION_REPRODUCED_AND_FIXED',rows=rows,
        hardwareOperations=0,newSpeedMeasurements=0,firmwareInstalled=False,
        scope='Idle predicate sees complete commands and deferred fault cleanup, not partial assembly, in-progress callbacks or ACI retry-only work; queue, command budget and durable status behavior unchanged.')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
