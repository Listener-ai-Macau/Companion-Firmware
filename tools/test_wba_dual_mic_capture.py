#!/usr/bin/env python3
"""Affected target-controller test using software NOR/mic/clock ports.

Compiles the actual target C and the actual BLE storage-blocker expression,
then checks independent output and its UART dump through the production file
decoders. Does not open hardware, generate a board receipt or qualify audio.
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    source=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    platform=source/'platform/stm32wba55_companion_v11';test=platform/'tests/test_dual_mic_capture.c'
    includes=[out,platform/'tests',platform,*sorted({p.parent for p in(source/'app/companion_pendant').rglob('*.h')})]
    ble=platform/'ble/ble_product.c';actual=re.search(r'comp_power_policy_set_blocker\(&product->board->power,COMP_POWER_BLOCKER_STORAGE,[\s\S]*?;',ble.read_text())
    assert actual,'Actual BLE storage-blocker calculation not found'
    (out/'pair_storage_guard_expression.inc').write_text('#define COMPANION_WBA_DUAL_PAIR_CAPTURE 1\nstatic void refresh_storage_blocker(void){\n'+actual.group()+'\n}\n')
    lowpower=platform/'low_power_target.c'
    foreground=re.search(r'if\(comp_v11_dual_pair_foreground_pending\(app\)\) return true;',lowpower.read_text())
    expression=foreground.group().replace('(app)','(&app)')if foreground else''
    (out/'pair_foreground_guard_expression.inc').write_text('static bool pair_service_foreground_pending(void){\n'+expression+'\nreturn false;\n}\n')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inputs={str(p):sha(p)for p in [platform/'dual_mic_capture.c',platform/'dual_mic_capture.h',test,
        platform/'tests/dual_mic_capture_test_platform.h',ble,lowpower,source/'app/companion_pendant/recording/wba_dual_mic_pair_stream.h',
        source/'tools/capture_wba_dual_mic_pair.py',source/'tools/decode_wba_dual_mic_stream.py']}
    flags=' '.join('/I"'+str(p)+'"'for p in includes)
    build=['@echo off','call "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/Common7/Tools/VsDevCmd.bat" -arch=amd64 -host_arch=amd64 >nul',
        'if errorlevel 1 exit /b %errorlevel%',f'cl.exe /nologo /std:c11 /W4 /WX /O2 {flags} "{test}" /Fe:"{out/"board-port.exe"}" /Fo:"{out}/" /link /INCREMENTAL:NO','exit /b %errorlevel%']
    (out/'build.cmd').write_text('\n'.join(build)+'\n');at=datetime.now().astimezone().isoformat(timespec='seconds')
    with(out/'build.log').open('xb')as log:
        code=subprocess.run(['cmd.exe','/d','/c',str(out/'build.cmd')],cwd=out,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW).returncode
    if not code:
        with(out/'checks.log').open('xb')as log:
            code=subprocess.run([str(out/'board-port.exe'),str(out/'software-source.dmp'),str(out/'dump.log')],cwd=out,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW).returncode
    if not code:
        sys.path.insert(0,str(source/'tools'));import capture_wba_dual_mic_pair as capture;import decode_wba_dual_mic_stream as decoder
        raw=(out/'software-source.dmp').read_bytes();log=(out/'dump.log').read_bytes();pcm,identity=decoder.decode(raw)
        assert identity['sampleCount']==32000 and identity['sourceSampleOffset']==640
        for i in range(32000):assert struct.unpack_from('<hh',pcm,i*4)==(i%2000,-(i%2000)-1)
        rows=capture.PairRows();rows.dump_started=True
        for i in range(0,len(log),511):rows.feed(log[i:i+511])
        assert bytes(rows.stream)==raw and rows.end=={'bytes':'132928','error':'0'}
        first=log.splitlines()[0]+b'\n'
        for bad in [first+first,first.replace(b'offset=0 ',b'offset=32 '),b'DPAIR DATA offset=0 hex=0\n',b'DPAIR END bytes=2 error=0\n']:
            rows=capture.PairRows();rows.dump_started=True
            try:rows.feed(bad)
            except ValueError:pass
            else:raise AssertionError('Invalid dump accepted')
    assert all(sha(Path(p))==digest for p,digest in inputs.items()),'Input changed'
    result=dict(result='PASS_TARGET_CONTROLLER_AND_ACTUAL_STORAGE_GUARD_SOFTWARE_PORTS_ONLY'if not code else'FAIL_PRESERVED',exitCode=code,
        startedAtLocal=at,finishedAtLocal=datetime.now().astimezone().isoformat(timespec='seconds'),inputs=inputs,
        exactTargetCodeAndBleExpression=True,sourceAndDumpSampleExact=not bool(code),hardwareAccess=False,newRecording=False,
        physicalNoiseReductionQualified=False,externalBoardCaptureReceiptGenerated=False,
        testOrigin='Software NOR/mic/clock doubles; target code DMP header alone does not authenticate a physical source')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['result','exitCode','finishedAtLocal']}));return code


if __name__=='__main__':raise SystemExit(main())
