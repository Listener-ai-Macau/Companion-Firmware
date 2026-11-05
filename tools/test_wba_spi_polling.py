"""Test the actual HAL binding with a SPI3 length-limited fake peripheral."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
PLATFORM=ROOT/'platform/stm32wba55_companion_v11'
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
    sources=[PLATFORM/'spi_polling.h',PLATFORM/'tests/test_spi_polling.c',
             PLATFORM/'tests/spi_fakes/stm32wbaxx_hal.h',Path(__file__)]
    fake=PLATFORM/'tests/spi_fakes';source=sources[1];exe=out/'test.exe'
    command=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{fake}',f'/I{PLATFORM}',str(source),f'/Fe:{exe}']
    build=out/'build.cmd';build.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n')
    logs=[]
    for command in (['cmd.exe','/d','/c',str(build)],[str(exe)],
                    [shutil.which('arm-none-eabi-gcc'),'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror',f'-I{fake}',f'-I{PLATFORM}','-c',str(source),'-o',str(out/'test.o')]):
        result=subprocess.run(command,cwd=out,capture_output=True,text=True);logs.append(result.stdout+result.stderr)
        (out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
        if result.returncode:raise RuntimeError('SPI binding test failed; see '+str(out/'test.log'))
    receipt={'result':'PASS_SPI_POLLING_SOFTWARE_ONLY','hardwareAcceptance':'NOT_RUN',
             'output':logs[1].strip(),'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['output'])
if __name__=='__main__':main()
