#!/usr/bin/env python3
"""Affected MTU negotiation and original-byte transfer; no physical speed claim."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
REC = 'app/companion_pendant/recording/'
BLE = 'platform/stm32wba55_companion_v11/ble/'

def main():
    out=ROOT/'.cache/recording-core-20261011'/sys.argv[1];out.mkdir(exist_ok=False)
    source=out/'source'
    files=[REC+'tests/test_wba_recording_packet_capacity.c',REC+'tests/test_wba_recording_transfer.c',
           REC+'wba_recording_transfer.c',REC+'companion_recording_journal.c',
           BLE+'ble_packet_capacity.h',BLE+'ble_mtu.h',str(Path(__file__).relative_to(ROOT))]
    files += [str(p.relative_to(ROOT)) for p in (ROOT/REC).glob('*.h')]
    for name in files:
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    (out/'source.json').write_text(json.dumps({n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in files},indent=2)+'\n')
    def run(args,name):
        p=subprocess.run(args,cwd=out,text=True,capture_output=True)
        (out/name).write_text(p.stdout+p.stderr,encoding='utf-8')
        if p.returncode:raise RuntimeError(f'{name}: {p.returncode}\n{p.stdout}\n{p.stderr}')
        return p.stdout
    try:
        sources=[source/(REC+n) for n in ['tests/test_wba_recording_packet_capacity.c','wba_recording_transfer.c','companion_recording_journal.c']]
        args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX',f'/I{source/REC}',f'/I{source/BLE}',
              *map(str,sources),f'/Fe:{out/"mtu.exe"}']
        cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
        run(['cmd.exe','/d','/c',str(cmd)],'compile.txt');result=run([str(out/'mtu.exe')],'result.txt')
        cc=shutil.which('arm-none-eabi-gcc');assert cc
        for src in sources:
            run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror',
                 '-Wconversion','-Wshadow','-pedantic',f'-I{source/REC}',f'-I{source/BLE}',
                 '-c',str(src),'-o',str(out/(src.stem+'.o'))],src.stem+'-m33.txt')
        report=dict(result='PASS_MTU_NEGOTIATION_AND_ORIGINAL_BYTES_SOFTWARE_ONLY',output=result,
                    physicalBoard=False,installed=False,throughputMeasured=False)
    except Exception as e:
        report=dict(result='FAILED_MTU_SOFTWARE',error=str(e));(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');raise
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
