#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.cache/wba-update-metadata-host'

def main()->int:
    OUT.mkdir(parents=True,exist_ok=True)
    vcvars=Path(r'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat')
    if not vcvars.exists(): raise RuntimeError('Visual Studio Build Tools vcvars64.bat missing')
    exe=OUT/'test_wba_update_metadata.exe'
    test=ROOT/'app/companion_pendant/update/tests/test_wba_update_metadata.c'
    source=ROOT/'app/companion_pendant/update/wba_update_metadata.c'
    include=ROOT/'app/companion_pendant/update'
    ota_include=ROOT/'third_party/denzic-platform/ota/embedded/c/include'
    cmd=OUT/'build.cmd'
    cmd.write_text('@echo off\ncall "'+str(vcvars)+'" amd64 >nul\n'
        f'cl.exe /nologo /std:c11 /W4 /WX /utf-8 /I"{include}" /I"{ota_include}" "{test}" "{source}" /Fe:"{exe}"\n',encoding='utf-8')
    built=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=OUT,text=True,capture_output=True)
    if built.returncode: raise RuntimeError(built.stdout+built.stderr)
    ran=subprocess.run([str(exe)],cwd=OUT,text=True,capture_output=True)
    if ran.returncode or not ran.stdout.startswith('PASS_WBA_UPDATE_METADATA'):
        raise RuntimeError(ran.stdout+ran.stderr)
    tracked=[test,source,Path(__file__)]
    result={'schema':'companion.wba.update-metadata.host.v1','result':'PASS',
            'blank_only_empty':True,'invalid_fail_closed':True,
            'read_failure_fail_closed':True,'commit_ram_rollback':True,
            'output':ran.stdout.strip(),'sources':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(ran.stdout.strip());print(OUT/'result.json');return 0

if __name__=='__main__': raise SystemExit(main())
