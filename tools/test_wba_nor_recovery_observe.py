#!/usr/bin/env python3
"""Read-only NOR recovery preflight, real driver with command-level model."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
from verify_wba_spi_nor_adapter import find_vsdevcmd

root=Path(__file__).resolve().parents[1]
out=root/'.cache/recording-core-20261011'/sys.argv[1]
out.mkdir(parents=True,exist_ok=False)
storage=root/'app/companion_pendant/storage'
recording=root/'app/companion_pendant/recording'
fixture=root/'tools/fixtures/wba_nor_recovery_observe_test.c'
inputs=[fixture,root/'tools/fixtures/wba_nor_suspend_test.c',storage/'spi_nor_stm32wba.c',storage/'spi_nor_stm32wba.h',recording/'companion_cpu_stage.h',Path(__file__).resolve()]
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
(out/'source.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD','/I'+str(storage),'/I'+str(recording),str(fixture),str(storage/'spi_nor_stm32wba.c'),'/Fe:'+str(out/'observe.exe')]
cmd=out/'compile.cmd'
cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
def run(name,command):
    p=subprocess.run(command,cwd=out,capture_output=True,text=True)
    (out/name).write_text(p.stdout+p.stderr,encoding='utf-8')
    if p.returncode: raise RuntimeError(name+': '+str(p.returncode)+'\n'+p.stdout+p.stderr)
run('compile.txt',['cmd.exe','/d','/c',str(cmd)])
run('result.txt',[str(out/'observe.exe')])
cc=shutil.which('arm-none-eabi-gcc')
if not cc: raise RuntimeError('ARM compiler not found')
run('arm.txt',[cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic','-I'+str(storage),'-I'+str(recording),'-c',str(storage/'spi_nor_stm32wba.c'),'-o',str(out/'nor.o')])
print((out/'result.txt').read_text(encoding='utf-8'))
