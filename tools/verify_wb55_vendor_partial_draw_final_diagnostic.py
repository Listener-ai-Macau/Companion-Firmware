#!/usr/bin/env python3
"""Statically admit the source-command-bound draw/final local diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
RECOVERY = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate-r2-20260720.json"
P0_CLOSURE = ROOT / "docs/validation/companion-gdey0154d67-t03-p0-closure-r2-20260720.json"
SUPPLIER = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-draw-final-static-20260720.json"
SUPPLIER_SHA256 = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_draw_final_static.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative(path)} is not a JSON object")
    return value


def evaluate() -> tuple[dict[str, Any], bool]:
    inputs = (DRIVER, MAKEFILE, BUILD, REQUIREMENTS, RECOVERY, P0_CLOSURE, SUPPLIER)
    missing = [relative(path) for path in inputs if not path.is_file()]
    if missing:
        return ({"schema_id": SCHEMA_ID, "status": "NO_GO_INPUT_MISSING", "failures": missing}, False)

    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
    requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    recovery = load_json(RECOVERY)
    closure = load_json(P0_CLOSURE)
    branch_start = driver.find("if (vendor_partial_draw_final) {")
    branch_end = driver.find("#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC", branch_start)
    branch = driver[branch_start:branch_end] if branch_start >= 0 else ""
    checks = {
        "owner_authorizes_only_draw_then_final_comparison": "COMP-REQ-232" in requirements
        and "first draw a local transitional union containing both the previous and current black pixels" in requirements,
        "supplier_source_is_frozen": digest(SUPPLIER) == SUPPLIER_SHA256
        and SUPPLIER_SHA256 in driver,
        "candidate_is_compile_time_disabled_and_source_partial_only": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DRAW_FINAL_DIAGNOSTIC 0",
                "draw/final diagnostic requires the source partial operator loop",
                "#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DRAW_FINAL_DIAGNOSTIC",
            )
        ),
        "first_pass_uses_only_the_local_old_or_new_black_union": all(
            token in driver
            for token in (
                "static bool ssd1681_write_previous_current_union_region",
                "s_previous_frame[index] & s_frame[index]",
                "!ssd1681_command(0x24u)",
            )
        ),
        "two_source_0xff_busy_passes_settle_to_current_frame": all(
            token in branch
            for token in (
                "ssd1681_write_previous_current_union_region(&window)",
                "ssd1681_refresh_display(",
                "ssd1681_reset();",
                "ssd1681_set_window_vendor_partial_source(&window, true)",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                "draw_control=0xFF",
                "final_control=0xFF",
                "no_full_write=1 no_c7=1",
            )
        ),
        "generic_third_activation_is_suppressed": "if (!vendor_partial_cleanup_draw && !vendor_partial_draw_final)"
        in driver,
        "fixed_machine_and_operator_builds_are_isolated": all(
            token in build
            for token in (
                "[switch]$EpaperSsd1681VendorPartialDrawFinalDiagnostic",
                "[switch]$EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic",
                "EPAPER_SSD1681_VENDOR_PARTIAL_DRAW_FINAL_DIAGNOSTIC=1",
                "$drawFinalRepeats = if ($EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic) { 360 } else { 49 }",
                "build_vendor_partial_draw_final_diagnostic",
                "build_vendor_partial_draw_final_operator_loop_diagnostic",
            )
        ) and "EPAPER_SSD1681_VENDOR_PARTIAL_DRAW_FINAL_DIAGNOSTIC" in makefile,
        "hardware_recovery_gate_is_current": recovery.get("status")
        == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST"
        and closure.get("status") == "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO",
    }
    failures = [name for name, passed in checks.items() if not passed]
    passed = not failures
    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_STATIC_PRODUCTION_OFF_VENDOR_PARTIAL_DRAW_FINAL" if passed else "NO_GO_STATIC_VENDOR_PARTIAL_DRAW_FINAL",
        "machine_status": "PASS_STATIC_HARDWARE_ADMITTED" if passed else "FAIL_STATIC",
        "claim_scope": "default-disabled local draw/final transport only; no optical, production, LUT, temperature or panel-identity claim",
        "checks": checks,
        "failures": failures,
        "source": {
            "supplier_epaper_c": {"path": relative(SUPPLIER), "sha256": digest(SUPPLIER)},
            "driver": {"path": relative(DRIVER), "sha256": digest(DRIVER)},
        },
        "controlled_behavior": {
            "pass_1": "source reset/border/local 0x24 old-or-new-black union, 0xFF, 0x20, BUSY",
            "pass_2": "source reset/border/same local 0x24 final current frame, 0xFF, 0x20, BUSY",
            "forbidden": ["0xC7", "full local-motion write", "LUT or waveform-byte change", "production promotion"],
        },
    }
    return report, passed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report, passed = evaluate()
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: draw/final static gate -> {relative(args.out)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
