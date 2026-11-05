#!/usr/bin/env python3
"""HOST_ONLY contract test for the portable WBA update service."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import argparse
from wba_flash_geometry import for_mcu, SOURCE as GEOMETRY_SOURCE, HEADER as GEOMETRY_HEADER

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "wba-update-service-host"
SRC = [
    ROOT / "app/companion_pendant/update/tests/test_wba_update_service.c",
    ROOT / "app/companion_pendant/update/wba_update_service.c",
    ROOT / "third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c",
]


def main() -> int:
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mcu',choices=['STM32WBA55CGU6','STM32WBA55CEU6'],default='STM32WBA55CEU6')
    parser.add_argument('--output',type=pathlib.Path)
    args=parser.parse_args();geometry=for_mcu(args.mcu)
    OUT=args.output.resolve() if args.output else OUT
    OUT.mkdir(parents=True, exist_ok=True)
    cc = shutil.which("clang") or shutil.which("gcc")
    exe = OUT / ("test_wba_update_service.exe" if os.name == "nt" else "test_wba_update_service")
    includes = [ROOT / "app/companion_pendant/update",
                ROOT / "third_party/denzic-platform/ota/embedded/c/include"]
    if cc:
        cmd = [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", f'-DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u',
               *sum((["-I", str(p)] for p in includes), []),
               *map(str, SRC), "-o", str(exe)]
        compile_run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    else:
        vcvars = pathlib.Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat")
        if os.name != "nt" or not vcvars.exists():
            raise SystemExit("clang/gcc/MSVC unavailable")
        cl = f"cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX /wd4295 /DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u "
        cl += " ".join(f'/I"{p}"' for p in includes)
        cl += " " + " ".join(f'"{p}"' for p in SRC)
        cl += f' /Fe:"{exe}" /link /OPT:REF /INCREMENTAL:NO'
        build_cmd = OUT / "build.cmd"
        build_cmd.write_text(f'@call "{vcvars}" >nul\n{cl}\n', encoding="ascii")
        cmd = [os.environ.get("ComSpec", "cmd.exe"), "/d", "/c", str(build_cmd)]
        compile_run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    run = subprocess.run([str(exe)], cwd=ROOT, text=True, capture_output=True) if compile_run.returncode == 0 else None
    status = "PASS" if run and run.returncode == 0 else "NO_GO"
    result = {
        "schema": "companion.wba_update_service.host.v1",
        "status": status,
        "host_only": True,
        "hardware_contact": False,
        "compile_exit": compile_run.returncode,
        "run_exit": None if run is None else run.returncode,
        "stdout": "" if run is None else run.stdout,
        "stderr": compile_run.stdout + compile_run.stderr + ("" if run is None else run.stderr),
        "sources": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in [*SRC, pathlib.Path(__file__)]},
    }
    result['mcu']=geometry.mcu;result['internal_flash_geometry']=geometry.receipt()
    for path in [GEOMETRY_SOURCE,GEOMETRY_HEADER,ROOT/'app/companion_pendant/update/wba_update_service.h']:
        result['sources'][path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if status != "PASS":
        print(result["stderr"], end="")
        return 1
    print(run.stdout.strip())
    print(OUT / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
