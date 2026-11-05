"""Run native power/button fault journeys and compile their Cortex-M33 code."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
from wba_power_profile import DEFAULT, validate, write_header

def qualification_tests():
    import copy
    if validate(DEFAULT) is not False: raise RuntimeError('Stock unsafe divider was accepted')
    for change in ({'dividerVerified':True,'qualificationEvidence':'host fixture'},
                   {'chargerPullupsVerified':True}, {'referenceMv':True},
                   {'socCurveVerified':True}, {'chargerPullupsVerified':'false'}):
        candidate=copy.deepcopy(DEFAULT); candidate.update(change)
        try: validate(candidate)
        except ValueError: pass
        else: raise RuntimeError(f'Unsafe/ambiguous qualification accepted: {change}')
    value=copy.deepcopy(DEFAULT)
    value.update(topOhm=150000,dividerVerified=True,referenceVerified=True,
        qualificationEvidence='HOST_ONLY_SYNTHETIC_REWORK_NOT_BOARD_APPROVAL')
    if not validate(value): raise RuntimeError('Qualified safe fixture refused')
    source=OUT/'host-only-profile.json'; source.write_text(json.dumps(value))
    report=write_header(OUT,source)
    if not report['sampling_qualified']: raise RuntimeError('Qualified profile not bound')
    print('PASS build qualification: stock divider disabled; unsafe, unmeasured, malformed and empty-curve profiles rejected; evidence-bound safe fixture compiled')

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app/companion_pendant'
OUT = ROOT / '.cache/host-tests/wba-power-monitor'
INCLUDES = [OUT, APP / 'power', APP / 'board']
SOURCES = [APP / p for p in ('power/wba_power_monitor.c', 'power/wba_button.c',
    'power/power_policy.c', 'board/companion_v11_board.c', 'board/tca6408.c')]
TEST = APP / 'power/tests/test_wba_power_monitor.c'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-only',action='store_true',help='Only the affected raw observation path; no charger/button regressions')
    options=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    receipt=OUT/'result.json'
    receipt.unlink(missing_ok=True)
    log=OUT/'build.log'; log.write_text('')
    if options.raw_only: write_header(OUT)
    else: qualification_tests()
    vc=find_vsdevcmd()
    if not vc: raise RuntimeError('MSVC unavailable')
    exe=OUT/'test.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX',*(f'/I{p}' for p in INCLUDES),
          *(str(p) for p in [*SOURCES,TEST]),f'/Fe:{exe}']
    script=OUT/'build.cmd'
    script.write_text(f'@echo off\ncall "{vc}" -arch=amd64 -host_arch=amd64 >nul\n'
        'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],OUT,log)
    result=run([str(exe),*(['--raw-only'] if options.raw_only else [])],OUT,log)
    cc=shutil.which('arm-none-eabi-gcc')
    if not cc: raise RuntimeError('Cortex-M33 compiler missing')
    for p in SOURCES:
        run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror',
             *(f'-I{d}' for d in INCLUDES),'-c',str(p),'-o',str(OUT/f'{p.stem}.o')],OUT,log)
    paths=[*SOURCES,TEST,Path(__file__),*(APP/'power').glob('wba_*.h'),
           APP/'power/power_policy.h',APP/'board/companion_v11_board.h',ROOT/'tools/wba_power_profile.py',
           OUT/'wba_board_power_profile.h',*([] if options.raw_only else [OUT/'host-only-profile.json'])]
    receipt.write_text(json.dumps({'result':'PASS_PREHARDWARE_SOFTWARE_ONLY',
        'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN','tests':result.splitlines(),
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    print(result,end='')
    print(receipt)
    return 0
if __name__=='__main__': raise SystemExit(main())
