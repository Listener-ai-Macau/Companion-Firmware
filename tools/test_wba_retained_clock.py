"""Exercise the actual retained RTC UTC anchor with declared mock target ports."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
POWER=ROOT/'app/companion_pendant/power'
OUT=ROOT/'.cache/host-tests/wba-retained-clock'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    receipt=OUT/'result.json';receipt.unlink(missing_ok=True)
    log=OUT/'build.log';log.write_text('')
    sources=[POWER/'wba_retained_clock.c',POWER/'tests/test_wba_retained_clock.c']
    vc=find_vsdevcmd();cc=shutil.which('arm-none-eabi-gcc')
    if not vc or not cc: raise RuntimeError('MSVC / Cortex-M33 compiler unavailable')
    exe=OUT/'test.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{POWER}',*(str(p) for p in sources),f'/Fe:{exe}']
    script=OUT/'build.cmd'
    script.write_text(f'@echo off\ncall "{vc}" -arch=amd64 -host_arch=amd64 >nul\n'
        'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],OUT,log)
    result=run([str(exe)],OUT,log)
    run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror',
         f'-I{POWER}','-c',str(sources[0]),'-o',str(OUT/'wba_retained_clock.o')],OUT,log)
    platform=ROOT/'platform/stm32wba55_companion_v11'
    runtime=ROOT/'app/companion_pendant/runtime'
    target_sources=[platform/'clock_target.c',platform/'tests/test_clock_target.c',
                    POWER/'wba_retained_clock.c',runtime/'companion_preferences.c',POWER/'power_settings_store.c']
    includes=[platform/'tests/clock_fakes',platform,POWER,runtime,ROOT/'app/companion_pendant/imu']
    target_exe=OUT/'target_test.exe'
    target_args=['cl.exe','/nologo','/std:c11','/W4','/WX','/DCOMPANION_WBA_BLE_LINKED',
        *(f'/I{p}' for p in includes),*(str(p) for p in target_sources),f'/Fe:{target_exe}']
    script.write_text(f'@echo off\ncall "{vc}" -arch=amd64 -host_arch=amd64 >nul\n'
        'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(target_args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],OUT,log)
    result+=run([str(target_exe)],OUT,log)
    paths=[*sources,*target_sources,POWER/'wba_retained_clock.h',platform/'clock_target.h',
           platform/'tests/clock_fakes/stm32wbaxx_hal.h',runtime/'companion_preferences.h',Path(__file__)]
    receipt.write_text(json.dumps({'result':'PASS_PREHARDWARE_SOFTWARE_ONLY',
        'scope':'actual_dual_bank_codec_fake_backup_registers_not_physical_RTC',
        'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN',
        'tests':result.splitlines(),
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    print(result,end='');print(receipt)
    return 0
if __name__=='__main__':raise SystemExit(main())
