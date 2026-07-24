#!/usr/bin/env python3
"""Statically admit the source-bound no-black-flash cleanup/draw diagnostic only."""

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
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate-r2-20260720.json"
P0_CLOSURE = ROOT / "docs/validation/companion-gdey0154d67-t03-p0-closure-r2-20260720.json"
SUPPLIER = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
PUBLIC_REFERENCE = ROOT / (
    ".cache/reference/good-display-gdeh0154d67/extracted/"
    "S-GDEH0154D67-20221011/HARDWARE/EPD/Display_EPD_W21.c"
)
DEFAULT_OUT = ROOT / (
    "docs/validation/companion-gdey0154d67-t03-vendor-partial-cleanup-draw-static-20260720.json"
)
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_cleanup_draw_static.v1"
SUPPLIER_SHA256 = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"


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
    inputs = (DRIVER, MAKEFILE, BUILD, REQUIREMENTS, RECOVERY_GATE, P0_CLOSURE, SUPPLIER, PUBLIC_REFERENCE)
    missing = [relative(path) for path in inputs if not path.is_file()]
    if missing:
        return ({"schema_id": SCHEMA_ID, "status": "FAIL_INPUT_MISSING", "failures": missing}, False)

    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
    requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    supplier = SUPPLIER.read_text(encoding="utf-8", errors="replace")
    public_reference = PUBLIC_REFERENCE.read_text(encoding="utf-8", errors="replace")
    recovery = load_json(RECOVERY_GATE)
    p0_closure = load_json(P0_CLOSURE)

    cleanup_block_start = driver.find("if (vendor_partial_cleanup_draw) {")
    cleanup_block_end = driver.find("#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC", cleanup_block_start)
    cleanup_block = driver[cleanup_block_start:cleanup_block_end] if cleanup_block_start >= 0 else ""
    checks = {
        "owner_explicitly_authorized_only_production_off_cleanup_draw": "COMP-REQ-228" in requirements
        and "不要黑闪" in requirements
        and "0x24" in requirements
        and "0x22=0xFF" in requirements,
        "supplier_source_hash_is_the_frozen_input": digest(SUPPLIER) == SUPPLIER_SHA256
        and "#define SSD1681_VENDOR_PARTIAL_SOURCE_SHA256" in driver
        and SUPPLIER_SHA256 in driver,
        "supplier_partial_route_is_not_the_159_byte_c7_route": all(
            token in supplier
            for token in (
                "void EPD_Dis_Part(",
                "Epaper_Write_Data(0xFF)",
                "void EPD_Update_LUT",
                "Epaper_Write_Data(0xC7)",
                "Epaper_Write_Command(0x3C)",
                "Epaper_Write_Data(0x80)",
            )
        ),
        "public_gdeh_reference_correlates_local_0xff_sequence": all(
            token in public_reference
            for token in (
                "void EPD_SetRAMValue_BaseMap",
                "Epaper_Write_Command(0x26)",
                "void EPD_Dis_Part(",
                "Epaper_Write_Data(0xFF)",
                "Epaper_Write_Command(0x20)",
            )
        ),
        "diagnostic_is_default_off_and_requires_source_partial_loop": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC 0",
                "cleanup/draw diagnostic requires the source partial operator loop",
                "#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC",
            )
        ),
        "each_partial_motion_has_two_source_equivalent_local_passes": all(
            token in cleanup_block
            for token in (
                "ssd1681_write_white_region(&window)",
                "ssd1681_refresh_display(",
                "ssd1681_reset();",
                "ssd1681_set_window_vendor_partial_source(&window, true)",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                "cleanup_control=0xFF",
                "draw_control=0xFF",
                "no_full_write=1 no_c7=1",
            )
        ),
        "cleanup_draw_suppresses_the_generic_third_partial_activation": "if (!vendor_partial_cleanup_draw) {"
        in driver,
        "cleanup_payload_is_local_and_byte_aligned": all(
            token in driver
            for token in (
                "static bool ssd1681_write_white_region(const ssd1681_window_t *window)",
                "window->x_end_byte >= SSD1681_BYTES_PER_ROW",
                "uint8_t white_row[SSD1681_BYTES_PER_ROW]",
                "for (uint16_t y = window->y_start; y <= window->y_end; ++y)",
            )
        ),
        "build_profile_is_fixed_isolated_and_traceable": all(
            token in build
            for token in (
                "[switch]$EpaperSsd1681VendorPartialCleanupDrawDiagnostic",
                "[switch]$EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic",
                "EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC=1",
                "$cleanupDrawRepeats = if ($EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic) { 360 } else { 49 }",
                "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$cleanupDrawRepeats",
                "$cleanupDrawBuildDir",
                "$cleanupDrawTarget",
                "build_vendor_partial_cleanup_draw_diagnostic",
                "Companion_Nucleo_WB55RG_VendorPartialCleanupDrawDiagnostic",
                "build_vendor_partial_cleanup_draw_operator_loop_diagnostic",
                "Companion_Nucleo_WB55RG_VendorPartialCleanupDrawOperatorLoopDiagnostic",
            )
        ) and all(
            token in makefile
            for token in (
                "EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC=1",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC=1",
        )
        ),
        "r2_recovery_evidence_is_current_fpc_and_official_full_only": recovery.get("status")
        == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST"
        and p0_closure.get("status") == "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO"
        and recovery.get("source_binding", {}).get("current_ssd1681_target_sha256")
        == "66A5A2E7DC1F85BC7A02F0BCDA9F009BEA6B96E2995941E90E218D141FF2EE3F",
    }
    failures = [name for name, passed in checks.items() if not passed]
    static_passed = not failures
    recovery_status = recovery.get("status")
    p0_closure_status = p0_closure.get("status")
    hardware_admitted = (
        static_passed
        and recovery_status == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST"
        and p0_closure_status == "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO"
    )
    status = (
        "PASS_STATIC_PRODUCTION_OFF_VENDOR_PARTIAL_CLEANUP_DRAW"
        if static_passed
        else "FAIL_STATIC_VENDOR_PARTIAL_CLEANUP_DRAW"
    )
    report = {
        "schema_id": SCHEMA_ID,
        "status": status,
        "machine_status": "PASS_STATIC_HARDWARE_FAIL_CLOSED"
        if static_passed and not hardware_admitted
        else "PASS_STATIC_HARDWARE_ADMITTED"
        if hardware_admitted
        else "FAIL_STATIC",
        "claim_scope": "compile-time-disabled source-bound local cleanup/draw diagnostic; no optical or production claim",
        "checks": checks,
        "failures": failures,
        "source_manifest": {
            "supplier_epaper_c": {"path": relative(SUPPLIER), "sha256": digest(SUPPLIER)},
            "public_gdeh_reference_c": {"path": relative(PUBLIC_REFERENCE), "sha256": digest(PUBLIC_REFERENCE)},
            "driver": {"path": relative(DRIVER), "sha256": digest(DRIVER)},
        },
        "controlled_behavior": {
            "production_default": "disabled",
            "baseline": "supplier base-map 0x24 then 0x26, full 0xF7",
            "motion_pass_1": "source-style reset/border/local 0x24 white then 0xFF, 0x20, BUSY",
            "motion_pass_2": "source-style reset/border/same local 0x24 final pixels then 0xFF, 0x20, BUSY",
            "forbidden": ["0xC7", "full-frame local-motion write", "LUT byte change", "production promotion"],
        },
        "hardware_admission": {
            "allowed": hardware_admitted,
            "recovery_gate_status": recovery_status,
            "p0_closure_status": p0_closure_status,
            "reason": "The isolated candidate may flash only because r2 binds the replacement FPC, official White/Black, and +20/-20 V rails. This is not a promotion of the candidate source, its local optical result, or the 159-byte LUT.",
        },
    }
    return report, static_passed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report, static_passed = evaluate()
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: cleanup/draw static gate -> {relative(args.out)}")
    return 0 if static_passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
