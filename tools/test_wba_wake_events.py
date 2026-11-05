#!/usr/bin/env python3
"""Compile and run the HAL-free Companion V1.1 wake-event latch test."""

from __future__ import annotations

import pathlib
import hashlib
import json
import os
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform" / "stm32wba55_companion_v11"
SOURCE = PLATFORM / "tests" / "test_wake_events.c"
OUT = ROOT / ".cache" / "host-tests" / "wba-wake-events"
RESULT = OUT / "result.json"
SOURCES = [
    PLATFORM / "wake_events.h",
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
    exe = OUT / ("test_wake_events.exe" if sys.platform == "win32" else "test_wake_events")
    compiler = shutil.which("clang") or shutil.which("gcc")
    if compiler is not None:
        command = [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{PLATFORM}",
            str(SOURCE),
            "-o",
            str(exe),
        ]
        built = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    else:
        vcvars = pathlib.Path(
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
            r"\VC\Auxiliary\Build\vcvars64.bat"
        )
        if not vcvars.exists():
            print("FAIL: clang/gcc or Visual Studio Build Tools is required", file=sys.stderr)
            return 2
        command_file = OUT / "build_wake_events.cmd"
        command_file.write_text(
            "@echo off\n"
            f'call "{vcvars}" >nul\n'
            "if errorlevel 1 exit /b %errorlevel%\n"
            f'cl.exe /nologo /W4 /WX /std:c11 /I"{PLATFORM}" '
            f'"{SOURCE}" /Fe:"{exe}"\n',
            encoding="utf-8",
        )
        built = subprocess.run(
            [os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"),
             "/d", "/c", str(command_file)],
            cwd=OUT,
            text=True,
            capture_output=True,
        )
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
