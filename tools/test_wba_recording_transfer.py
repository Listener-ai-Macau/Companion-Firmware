#!/usr/bin/env python3
"""Host-only recording transfer and Cortex-M33 compile checks."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
REC = ROOT / "app" / "companion_pendant" / "recording"
OUT = ROOT / ".cache" / "wba-recording-transfer-host"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                            check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def run_vc(command: str) -> subprocess.CompletedProcess[str]:
    vcvars = pathlib.Path(os.environ.get("ProgramFiles(x86)", "")) / (
        "Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
    )
    if not vcvars.exists():
        raise RuntimeError(f"MSVC environment not found: {vcvars}")
    script = OUT / "vc-command.cmd"
    script.write_text(
        f'@call "{vcvars}" >nul\n@if errorlevel 1 exit /b %errorlevel%\n'
        f'@cd /d "{OUT}"\n@if errorlevel 1 exit /b %errorlevel%\n'
        f'@{command}\n', encoding="utf-8"
    )
    return run(["cmd", "/d", "/c", str(script)])


def quote(path: pathlib.Path) -> str:
    return f'"{path}"'


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = [
        REC / "tests" / "test_wba_recording_transfer.c",
        REC / "wba_recording_transfer.c",
        REC / "companion_recording_journal.c",
    ]
    headers = [
        REC / "wba_recording_transfer.h",
        REC / "wba_recording_crc.h",
        REC / "companion_recording_wire.h",
        REC / "companion_recording_gatt_adapter.h",
        REC / "companion_recording_journal.h",
    ]
    executable = OUT / "wba-recording-transfer-test.exe"
    compile_result = run_vc(
        f'cl /nologo /TC /std:c11 /O2 /W4 /WX /I{quote(REC)} '
        + " ".join(quote(path) for path in sources)
        + f' /Fe:{quote(executable)}'
    )
    test_result = run([str(executable)])
    if not test_result.stdout.startswith("PASS_WBA_RECORDING_TRANSFER_HOST_ONLY"):
        raise RuntimeError(f"unexpected test output: {test_result.stdout}")

    arm_gcc = shutil.which("arm-none-eabi-gcc")
    if not arm_gcc:
        raise RuntimeError("arm-none-eabi-gcc unavailable")
    arm_objects: dict[str, str] = {}
    for source in sources[1:]:
        output = OUT / f"{source.stem}.o"
        run([
            arm_gcc, "-std=c11", "-mcpu=cortex-m33", "-mthumb",
            "-Wall", "-Wextra", "-Werror", "-Wconversion", "-Wshadow",
            "-Wformat=2", "-pedantic", f"-I{REC}", "-c", str(source),
            "-o", str(output),
        ])
        arm_objects[output.name] = sha256(output)

    result = {
        "schema": "companion.wba_recording_transfer.prehardware.v1",
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "wire": {
            "request_bytes": 16,
            "response_header_bytes": 56,
            "max_att_value_bytes": 509,
            "max_payload_bytes": 453,
            "legacy_test_compact_payload_bytes": 224,
            "lanes": 1,
            "resume_authority": "host_verified_byte_offset",
            "resume_token_semantics": "correlation_only",
        },
        "test_stdout": test_result.stdout.strip(),
        "compile_log": (compile_result.stdout + compile_result.stderr).strip(),
        "m33_objects": arm_objects,
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [*sources, *headers]
        },
    }
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS_WBA_RECORDING_TRANSFER_PREHARDWARE")
    print(result_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NO_GO_WBA_RECORDING_TRANSFER: {exc}", file=sys.stderr)
        raise SystemExit(2)
