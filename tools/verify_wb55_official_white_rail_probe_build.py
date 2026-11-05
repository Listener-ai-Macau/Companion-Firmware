#!/usr/bin/env python3
"""Bind the official White rail-probe image to its isolated build contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD_WRAPPER = ROOT / "tools/build_nucleo_bringup.ps1"
PANEL_TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
SCHEMA_ID = "companion.wb55.official_white_rail_probe_build.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def probe_block(build_wrapper: str) -> str:
    start = build_wrapper.find("if ($EpaperSsd1681OfficialWhiteRailProbe) {")
    end = build_wrapper.find("if ($EpaperSsd1681VendorPartialDiagnostic)", start)
    return build_wrapper[start:end] if start >= 0 and end > start else ""


def evaluate(build_wrapper: str, panel_target: str) -> dict[str, bool]:
    block = probe_block(build_wrapper)
    required_defines = (
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=1",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=30",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=5000",
        "BUILD_DIR=build_official_full_rail_probe_white",
        "TARGET=Companion_Nucleo_WB55RG_OfficialFullRailProbeWhite",
    )
    return {
        "probe_switch_is_declared": "[switch]$EpaperSsd1681OfficialWhiteRailProbe," in build_wrapper,
        "probe_rejects_runtime_overrides": all(
            token in block
            for token in (
                "$EpaperSsd1681OfficialFullDiagnostic",
                "$EpaperSsd1681DiagnosticPattern -ne ''",
                "$EpaperSsd1681DiagnosticPartial",
                "$EpaperSsd1681DiagnosticRepeats -ne 1",
                "$EpaperSsd1681DiagnosticIntervalMs -ne 0",
                "fixed isolated profile",
            )
        ),
        "probe_has_exact_white_rail_defines": all(token in block for token in required_defines),
        "probe_does_not_select_a_lut_or_partial_mode": "LUT" not in block and "VENDOR_PARTIAL" not in block,
        "build_wrapper_does_not_flash": "flash_nucleo_bringup" not in build_wrapper,
        "target_uses_official_one_plane_current_write": all(
            token in panel_target
            for token in (
                "COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC",
                "vendor_sample_partial || official_full_diagnostic ||",
                "? 1u\n                                                   : 2u;",
                "} else if (official_full_diagnostic || vendor_1s_lut_diagnostic) {",
                "ssd1681_write_plane_region(0x24u, s_frame, &window);",
                "\"good_display_official_0x24_only\"",
            )
        ),
        "target_trace_has_cycle_and_busy_markers": "[epaper] boot_diag pattern=%u official=%u cycle=%u result=%u bytes=%lu busy=%d" in panel_target,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=pathlib.Path, required=True)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    image = args.image if args.image.is_absolute() else ROOT / args.image
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    if not image.is_file():
        parser.error(f"missing rail-probe image: {rel(image)}")

    build_wrapper = BUILD_WRAPPER.read_text(encoding="utf-8-sig")
    panel_target = PANEL_TARGET.read_text(encoding="utf-8-sig")
    checks = evaluate(build_wrapper, panel_target)
    failures = [name for name, passed in checks.items() if not passed]
    report: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "status": (
            "PASS_BUILD_ONLY_OFFICIAL_WHITE_RAIL_PROBE_NOT_FLASHED"
            if not failures
            else "FAIL_OFFICIAL_WHITE_RAIL_PROBE_BUILD_CONTRACT"
        ),
        "claim_scope": "compile_time_and_image_identity_only_not_flash_or_panel_acceptance",
        "checks": checks,
        "failures": failures,
        "image": {"path": rel(image), "sha256": digest(image)},
        "build_contract": {
            "pattern": "white",
            "official_full_current_plane": "0x24_only",
            "data_planes": 1,
            "bytes_per_plane": 5000,
            "refresh_control": "0xF7",
            "repeats": 30,
            "interval_ms": 5000,
            "target": "Companion_Nucleo_WB55RG_OfficialFullRailProbeWhite",
        },
        "next_physical_gate": "After the versioned replacement-display-FPC evidence and flex/wiring verification, flash this exact SHA under the bounded hardware session, collect a reset-bounded log and PREVGH1/PREVGL1 measurements, then run verify_wb55_official_full_rail_measurement.py. This build artifact does not authorize a White PASS, Black stage, normal-runtime claim, or any LUT change.",
        "sources": {
            "build_wrapper": {"path": rel(BUILD_WRAPPER), "sha256": digest(BUILD_WRAPPER)},
            "panel_target": {"path": rel(PANEL_TARGET), "sha256": digest(PANEL_TARGET)},
        },
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        print(f"FAIL: official White rail-probe build contract -> {rel(destination)}", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: official White rail-probe build contract -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
