#!/usr/bin/env python3
"""Behavior and integration checks for Companion's bounded diagnostic export."""

from __future__ import annotations

import binascii
import importlib.util
import pathlib
import shutil
import struct
import subprocess
import sys
from types import ModuleType
from typing import Any, Callable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DIAG_ROOT = REPO_ROOT / "app" / "companion_pendant" / "diag_log"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
REAL_BENCH = REPO_ROOT / "tools" / "companion_ble_real_bench.py"
BUTTON_CHAIN = REPO_ROOT / "tools" / "companion_button_recording_chain.py"

HEADER_FORMAT = "<BBHIIHHI"
EVENT_FORMAT = "<IIBBBBIIII"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def packet_fixture(*, corrupt_crc: bool = False, truncate: bool = False) -> bytes:
    events = b"".join(
        (
            struct.pack(EVENT_FORMAT, 41, 900, 3, 2, 0, 0, 0, 4, 64, 0xFFFF),
            struct.pack(EVENT_FORMAT, 42, 905, 4, 3, 1, 0, 2, 4, 1, 0),
        )
    )
    crc32 = binascii.crc32(events) & 0xFFFFFFFF
    if corrupt_crc:
        crc32 ^= 1
    packet = struct.pack(
        HEADER_FORMAT,
        1,
        0x02,
        2,
        0,
        42,
        7,
        len(events),
        crc32,
    ) + events
    return packet[:-1] if truncate else packet


def check_parser(
    parser: Callable[[bytes], dict[str, Any]],
    error_type: type[BaseException],
    label: str,
    errors: list[str],
) -> None:
    parsed = parser(packet_fixture())
    require(parsed.get("request_cursor") == 0, f"{label} request cursor mismatch", errors)
    require(parsed.get("next_cursor") == 42, f"{label} next cursor mismatch", errors)
    require(parsed.get("total_available") == 7, f"{label} total count mismatch", errors)
    require(parsed.get("event_count") == 2, f"{label} event count mismatch", errors)
    require(parsed.get("packet_bytes") == 76, f"{label} packet byte count mismatch", errors)
    require(parsed.get("crc_valid") is True, f"{label} CRC was not marked valid", errors)
    require(
        [event.get("sequence") for event in parsed.get("events", [])] == [41, 42],
        f"{label} event sequence decode mismatch",
        errors,
    )
    for bad_name, payload in (
        ("bad CRC", packet_fixture(corrupt_crc=True)),
        ("truncated packet", packet_fixture(truncate=True)),
    ):
        try:
            parser(payload)
        except error_type:
            pass
        else:
            errors.append(f"{label} accepted {bad_name}")


def check_sources(errors: list[str]) -> None:
    export_h = (DIAG_ROOT / "diag_log_export.h").read_text(encoding="utf-8")
    export_c = (DIAG_ROOT / "diag_log_export.c").read_text(encoding="utf-8")
    log_c = (DIAG_ROOT / "diag_log.c").read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    diag_start = app_ble.rfind("static void Companion_Gatt_PublishDiagLogResponse")
    diag_end = app_ble.find("\nstatic void ", diag_start + 1)
    diag_body = app_ble[diag_start:diag_end]

    for token in (
        "COMP_DIAG_LOG_EXPORT_HEADER_BYTES 20u",
        "COMP_DIAG_LOG_EXPORT_MAX_EVENTS 8u",
        "comp_diag_log_export_packet_t",
        "comp_diag_log_export_build",
        "comp_diag_log_export_crc32",
    ):
        require(token in export_h or token in export_c, f"missing export anchor {token}", errors)
    for token in (
        "comp_diag_log_read_page",
        "cursor == 0u && available > max_events",
        "comp_diag_log_source_matches",
        "comp_diag_log_severity_matches",
    ):
        require(token in log_c, f"missing ring paging anchor {token}", errors)
    for token in (
        '#include "diag_log_export.h"',
        "COMP_DIAG_EVT_GATT_LOG_EXPORT_REQUEST",
        "comp_diag_log_export_build(&export_request",
        "response_bytes > COMPANION_GATT_MAX_PAYLOAD_BYTES",
    ):
        require(token in app_ble, f"WB55 GATT adapter missing {token}", errors)
    require(diag_start >= 0 and diag_end > diag_start, "cannot isolate WB55 diagnostics response", errors)
    require("response = *request" not in diag_body, "placeholder diagnostics echo remains", errors)
    require("request->cursor + 1u" not in diag_body, "synthetic diagnostics cursor remains", errors)
    require("diag_log/diag_log_export.c" in makefile, "WB55 build omits portable exporter", errors)


def check_cortex_m33_compile(errors: list[str]) -> None:
    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        errors.append("arm-none-eabi-gcc is required for the WBA Cortex-M33 portability check")
        return
    command = [
        compiler,
        "-mcpu=cortex-m33",
        "-mthumb",
        "-std=c11",
        "-ffreestanding",
        "-Wall",
        "-Wextra",
        "-Werror",
        f"-I{DIAG_ROOT}",
        "-fsyntax-only",
        str(DIAG_ROOT / "diag_log.c"),
        str(DIAG_ROOT / "diag_log_export.c"),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        "portable diagnostics core failed Cortex-M33 compile: "
        + (completed.stderr.strip() or completed.stdout.strip()),
        errors,
    )


def check_native_replay(errors: list[str]) -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        errors.append("pwsh is required for the native diagnostics replay")
        return
    completed = subprocess.run(
        [pwsh, "-NoProfile", "-File", str(REPO_ROOT / "tools" / "test_diag_log_export_host.ps1")],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0 and
        "PASS: portable bounded diagnostics export host replay passed." in completed.stdout,
        "native diagnostics replay failed: "
        + (completed.stderr.strip() or completed.stdout.strip()),
        errors,
    )


def main() -> int:
    errors: list[str] = []
    check_sources(errors)
    check_cortex_m33_compile(errors)
    check_native_replay(errors)

    real_bench = load_module(REAL_BENCH, "companion_ble_real_bench_diag_test")
    button_chain = load_module(BUTTON_CHAIN, "companion_button_recording_chain_diag_test")
    check_parser(real_bench.parse_diag_log_pull, real_bench.BenchError, "real bench", errors)
    check_parser(button_chain.parse_diag_log_pull, button_chain.ChainError, "button chain", errors)

    if errors:
        print("FAIL: bounded diagnostics export checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: bounded diagnostics export C/GATT/host contract checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
