from pathlib import Path
import argparse
import hashlib,json,shutil,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app/companion_pendant'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screen-disabled',action='store_true')
    parser.add_argument('--product',choices=('companion','capture'),default='companion')
    parser.add_argument('--output',type=Path);options=parser.parse_args()
    screen=not options.screen_disabled and options.product=='companion'
    expected='Capture' if options.product=='capture' else 'Companion'
    flags=[f'-DCOMPANION_WBA_SCREEN_ENABLED={int(screen)}',
           f'-DCOMPANION_PRODUCT_CAPTURE={int(options.product=="capture")}']
    out=options.output or ROOT/('.cache/wba-preferences-'+options.product+('-screen' if screen else '-no-screen')+'-host');out.mkdir(parents=True,exist_ok=True)
    log=out/'build.log';log.write_text('')
    sources=[APP/'runtime/companion_preferences.c',APP/'power/power_settings_store.c',APP/'runtime/tests/test_companion_preferences.c',APP/'recording/wba_silence_stop.c']
    includes=[APP/'runtime',APP/'power',APP/'recording',APP/'imu'];exe=out/'test_preferences.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX',*(f'/I{p}' for p in includes),*(str(p) for p in sources),f'/Fe:{exe}']
    args[1:1]=[flag.replace('-D','/D',1) for flag in flags]
    script=out/'build.cmd';script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],out,log);result=run([str(exe),expected],out,log);print(result,end='')
    for source in [*sources[:2],sources[3]]:
        run([shutil.which('arm-none-eabi-gcc'),'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror',*flags,*(f'-I{p}' for p in includes),'-c',str(source),'-o',str(out/(source.stem+'.o'))],out,log)
    report={'result':'PASS_HOST_ONLY','hardwareAcceptance':'NOT_RUN','tests':result,
      'product':options.product,'screenEnabled':screen,'expectedDefaultName':expected,
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,APP/'runtime/companion_preferences.h',Path(__file__)]}}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
