"""Verify WBA UART status framing and exact wired-pair request parsing, without hardware."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
PLATFORM=ROOT/'platform/stm32wba55_companion_v11'
DEFAULT_OUT=ROOT/'.cache/host-tests/wba-diagnostic-console'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUT)
    args=parser.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    receipt=out/'result.json';receipt.unlink(missing_ok=True)
    log=out/'build.log';log.write_text('',encoding='utf-8')
    sources=[PLATFORM/'diagnostic_console.c',PLATFORM/'tests/test_diagnostic_console.c']
    vc=find_vsdevcmd();arm=shutil.which('arm-none-eabi-gcc')
    if not vc or not arm: raise RuntimeError('MSVC / Cortex-M33 compiler unavailable')
    exe=out/'test.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8',f'/I{PLATFORM}',
          *(str(p) for p in sources),f'/Fe:{exe}']
    script=out/'build.cmd'
    script.write_text(f'@echo off\ncall "{vc}" -arch=amd64 -host_arch=amd64 >nul\n'
        'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
    run(['cmd.exe','/d','/c',str(script)],out,log)
    result=run([str(exe)],out,log)
    run([arm,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror',
         f'-I{PLATFORM}','-c',str(sources[0]),'-o',str(out/'diagnostic_console.o')],out,log)
    paths=[*sources,PLATFORM/'diagnostic_console.h',Path(__file__)]
    paths.append(PLATFORM/'main.c')
    receipt.write_text(json.dumps({'result':'PASS_PREHARDWARE_SOFTWARE_ONLY',
        'scope':'UART_status_framing_and_wired_PAIR_request_parser_no_hardware',
        'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN',
        'tests':result.splitlines(),
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n',encoding='utf-8')
    print(result,end='');print(receipt)
    return 0

if __name__=='__main__':raise SystemExit(main())
