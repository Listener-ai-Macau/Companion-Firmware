#!/usr/bin/env python3
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
from test_wba_runtime import ROOT, APP, INCLUDES

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--battery-only',action='store_true')
    options=parser.parse_args()
    out=ROOT / ('.cache/wba-battery-renderer' if options.battery_only else '.cache/wba-product-renderer')
    out.mkdir(parents=True,exist_ok=True)
    log=out / 'build.log'; log.write_text('')
    report={'result':'FAIL','hardwareAcceptance':'NOT_RUN','artFixture':'synthetic masks; pixel ownership only'}
    try:
        sources=[APP / n for n in ('runtime/companion_renderer.c','runtime/tests/test_companion_renderer.c',
            'epaper/screen_menu.c','epaper/screen_framebuffer.c','epaper/motion_coordinator.c','touch/browser_interaction_runtime.c')]
        exe=out/'test_renderer.exe'
        args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1','/DCOMPANION_WBA_RESOURCE_PROFILE=1',
              *(f'/I{p}' for p in INCLUDES),*(str(p) for p in sources),f'/Fe:{exe}']
        script=out/'build.cmd'
        script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\n'
                          'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
        run(['cmd.exe','/d','/c',str(script)],out,log)
        result=run([str(exe),*(['--battery-only'] if options.battery_only else [])],out,log); print(result,end='')
        if ('PASS_BATTERY_RENDERER' if options.battery_only else 'PASS_PREHARDWARE_RENDERER') not in result: raise RuntimeError('Completion absent')
        report.update(result='PASS_PREHARDWARE_SOFTWARE_ONLY',tests=result.strip(),
            source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [*sources, Path(__file__), *(p for d in INCLUDES for p in d.glob('*.h'))]})
    except (OSError,RuntimeError) as e: report['error']=str(e); print(e)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return int(report['result']=='FAIL')
if __name__=='__main__': raise SystemExit(main())
