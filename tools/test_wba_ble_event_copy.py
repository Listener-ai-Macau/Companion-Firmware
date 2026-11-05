#!/usr/bin/env python3
"""Test the pure WBA BLE split-event validator/copy helper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from verify_wba_spi_nor_adapter import find_vsdevcmd


ROOT = Path(__file__).resolve().parents[1]
BLE = ROOT / "platform" / "stm32wba55_companion_v11" / "ble"
OUT = ROOT / ".cache" / "wba-ble-event-copy-host"
SOURCE = BLE / "ble_event_copy.c"
HEADER = BLE / "ble_event_copy.h"
TEST = BLE / "tests" / "test_ble_event_copy.c"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                            check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    vsdevcmd = find_vsdevcmd()
    if vsdevcmd is None:
        raise RuntimeError("MSVC environment unavailable")
    executable = OUT / "test-ble-event-copy.exe"
    args = ["cl.exe", "/nologo", "/TC", "/std:c11", "/O2", "/W4", "/WX",
            f"/I{BLE}", str(SOURCE), str(TEST), f"/Fe:{executable}"]
    script = OUT / "compile.cmd"
    script.write_text(
        f'@call "{vsdevcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
        '@if errorlevel 1 exit /b %errorlevel%\n'
        + subprocess.list2cmdline(args) + "\n", encoding="utf-8")
    native_compile = run(["cmd.exe", "/d", "/c", str(script)])
    host = run([str(executable)])
    if not host.stdout.startswith("PASS_WBA_BLE_EVENT_COPY_HOST_ONLY"):
        raise RuntimeError(f"unexpected host output: {host.stdout}")

    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        raise RuntimeError("arm-none-eabi-gcc unavailable")
    obj = OUT / "ble_event_copy.o"
    run([compiler,"-std=c11","-mcpu=cortex-m33","-mthumb","-Os",
         "-Wall","-Wextra","-Werror","-Wconversion","-Wshadow",
         "-Wformat=2","-pedantic",f"-I{BLE}","-c",str(SOURCE),"-o",str(obj)])
    result = {
        "schema": "companion.wba_ble_event_copy.prehardware.v1",
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "cases": ["contiguous", "split", "maximum_258_bytes", "null",
                  "short_header", "missing_extension", "wrong_type",
                  "truncated_plen", "extra_bytes", "length_overflow",
                  "small_output"],
        "test_stdout": host.stdout.strip(),
        "compile_log": (native_compile.stdout + native_compile.stderr).strip(),
        "m33_object_sha256": sha256(obj),
        "source_sha256": {str(path.relative_to(ROOT)): sha256(path)
                          for path in (SOURCE,HEADER,TEST,Path(__file__))},
    }
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PASS_WBA_BLE_EVENT_COPY_PREHARDWARE")
    print(result_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NO_GO_WBA_BLE_EVENT_COPY: {exc}",file=sys.stderr)
        raise SystemExit(2)
