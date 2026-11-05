#!/usr/bin/env python3
"""HOST_ONLY power-loss/rollback test for the WBA resident boot engine."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, shutil, subprocess
from wba_flash_geometry import for_mcu, SOURCE as GEOMETRY_SOURCE, HEADER as GEOMETRY_HEADER

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/".cache/wba-boot-installer-host"
SRC=[ROOT/"app/companion_pendant/update/tests/test_wba_boot_installer.c",
     ROOT/"app/companion_pendant/update/wba_boot_installer.c",
     ROOT/"app/companion_pendant/update/wba_update_service.c",
     ROOT/"third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c"]
INC=[ROOT/"app/companion_pendant/update",ROOT/"third_party/denzic-platform/ota/embedded/c/include"]

def main()->int:
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mcu',choices=['STM32WBA55CGU6','STM32WBA55CEU6'],default='STM32WBA55CEU6')
    parser.add_argument('--output',type=pathlib.Path)
    args=parser.parse_args();geometry=for_mcu(args.mcu)
    OUT=args.output.resolve() if args.output else OUT
    OUT.mkdir(parents=True,exist_ok=True);exe=OUT/("test_wba_boot_installer.exe" if os.name=="nt" else "test_wba_boot_installer")
    cc=shutil.which("clang") or shutil.which("gcc")
    if cc:
        cmd=[cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",f'-DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u',*sum((["-I",str(x)] for x in INC),[]),*map(str,SRC),"-o",str(exe)]
    else:
        vc=pathlib.Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat")
        if os.name!="nt" or not vc.exists():raise SystemExit("C compiler unavailable")
        cl=f"cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX /wd4295 /DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u "+" ".join(f'/I"{x}"' for x in INC)+" "+" ".join(f'"{x}"' for x in SRC)+f' /Fe:"{exe}" /link /OPT:REF /INCREMENTAL:NO'
        script=OUT/"build.cmd";script.write_text(f'@call "{vc}" >nul\n{cl}\n',encoding="ascii")
        cmd=[os.environ.get("ComSpec","cmd.exe"),"/d","/c",str(script)]
    build=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    run=subprocess.run([str(exe)],cwd=ROOT,text=True,capture_output=True) if build.returncode==0 else None
    result={"schema":"companion.wba_boot_installer.host.v1","status":"PASS" if run and run.returncode==0 else "NO_GO","host_only":True,"hardware_contact":False,"compile_exit":build.returncode,"run_exit":None if run is None else run.returncode,"stdout":"" if run is None else run.stdout,"stderr":build.stdout+build.stderr+("" if run is None else run.stderr),"sources":{str(x.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(x.read_bytes()).hexdigest() for x in [*SRC,pathlib.Path(__file__)]}}
    result['mcu']=geometry.mcu;result['internal_flash_geometry']=geometry.receipt()
    for path in [GEOMETRY_SOURCE,GEOMETRY_HEADER,ROOT/'app/companion_pendant/update/wba_boot_installer.h',ROOT/'app/companion_pendant/update/wba_update_service.h']:
        result['sources'][path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    if result["status"]!="PASS":print(result["stderr"],end="");return 1
    print(run.stdout.strip());print(OUT/"result.json");return 0
if __name__=="__main__":raise SystemExit(main())
