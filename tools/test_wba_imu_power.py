#!/usr/bin/env python3
"""Build and run the HAL-free LSM6DSO run/idle transition test."""

from __future__ import annotations

import os
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
IMU = ROOT / "app" / "companion_pendant" / "imu"
TAPS = sys.argv[1:] == ["--taps"]
PORT = sys.argv[1:] == ["--recording-port"]
SOURCE = IMU / "tests" / ("test_lsm6dso_recording_port.c" if PORT else "test_lsm6dso_taps.c" if TAPS else "test_lsm6dso_power.c")
DRIVER = IMU / "lsm6dso.c"
OUT = ROOT / ".cache" / "host-tests" / ("wba-imu-recording-port" if PORT else "wba-imu-taps" if TAPS else "wba-imu-power")
RESULT = OUT / "result.json"
SOURCES = [
    IMU / "lsm6dso.h",
    DRIVER,
    SOURCE,
    pathlib.Path(__file__).resolve(),
]


def write_result(stdout: str) -> None:
    source_sha256 = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCES
    }
    payload = {
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "source_sha256": source_sha256,
        "stdout": stdout,
    }
    temporary = RESULT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(RESULT)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT.unlink(missing_ok=True)
    if PORT:
        board=ROOT/'platform/stm32wba55_companion_v11/board_hal.c'
        text=board.read_text();begin=text.index('bool comp_v11_hal_microphone_enable(')
        brace=text.index('{',begin);depth=1;end=brace+1
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        (OUT/'imu_microphone_port.inc').write_text(text[begin:end]+'\n')
        SOURCES.extend([board,IMU/'tests/test_lsm6dso_taps.c'])
    exe = OUT / ("test_lsm6dso_power.exe" if sys.platform == "win32" else "test_lsm6dso_power")
    compiler = shutil.which("clang") or shutil.which("gcc")
    if compiler is not None:
        command = [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                   f"-I{IMU}",f"-I{OUT}", str(SOURCE), str(DRIVER), "-o", str(exe)]
        built = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    else:
        vcvars = pathlib.Path(
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
            r"\VC\Auxiliary\Build\vcvars64.bat"
        )
        if not vcvars.exists():
            print("FAIL: clang/gcc or Visual Studio Build Tools is required", file=sys.stderr)
            return 2
        script = OUT / "build_lsm6dso_power.cmd"
        script.write_text(
            "@echo off\n"
            f'call "{vcvars}" >nul\n'
            "if errorlevel 1 exit /b %errorlevel%\n"
            f'cl.exe /nologo /W4 /WX /std:c11 /I"{IMU}" /I"{OUT}" "{SOURCE}" '
            f'"{DRIVER}" /Fe:"{exe}"\n',
            encoding="utf-8",
        )
        built = subprocess.run(
            [os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"),
             "/d", "/c", str(script)],
            cwd=OUT, text=True, capture_output=True)
    if built.returncode != 0:
        print(built.stdout, end="")
        print(built.stderr, end="", file=sys.stderr)
        return built.returncode
    tested = subprocess.run([str(exe)], cwd=ROOT, text=True, capture_output=True)
    print(tested.stdout, end="")
    print(tested.stderr, end="", file=sys.stderr)
    if tested.returncode == 0:
        write_result(tested.stdout)
    return tested.returncode


if __name__ == "__main__":
    raise SystemExit(main())
