#!/usr/bin/env python3
"""Verify the owner-authorized, production-off Good Display one-second LUT image."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR_EPAPER = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_vendor_1s_lut_diagnostic.ps1"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
PANEL_CORRELATION = ROOT / "docs/validation/companion-gdey0154d67-t03-panel-marking-correlation-20260720.json"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
P0_CLOSURE = ROOT / "docs/validation/companion-gdey0154d67-t03-p0-closure-20260720.json"
WHITE_RAIL = ROOT / "docs/validation/companion-screen-wb55-white-rail-measurement-current-source-20260720.json"
REPLACEMENT_FPC = ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
DIAGNOSTIC_IMAGE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_vendor_1s_lut_diagnostic/Companion_Nucleo_WB55RG_Vendor1sLutDiagnostic.hex"
OPERATOR_LOOP_IMAGE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_vendor_1s_lut_operator_loop_diagnostic/Companion_Nucleo_WB55RG_Vendor1sLutOperatorLoopDiagnostic.hex"
DEFAULT_OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-diagnostic-static-20260720.json"
EXPECTED_LUT_SHA256 = "F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15"
EXPECTED_DIAGNOSTIC_IMAGE_SHA256 = "FCB793FF1F204643CA7EA7CE972A6A4B87708044633792197F96A08F5E50E180"
EXPECTED_OPERATOR_LOOP_IMAGE_SHA256 = "E84D361450927E01F7F2C2F6CDFF35B68138820FAA10E4D930D2FC95365F39D5"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_1s_lut_diagnostic_static.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} must be a JSON object")
    return value


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def extract_array(text: str, name: str) -> list[int]:
    match = re.search(
        rf"\b(?:const\s+unsigned\s+char|static\s+const\s+uint8_t)\s+{re.escape(name)}\s*"
        rf"\[\s*159\s*\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        strip_comments(text),
        flags=re.DOTALL,
    )
    if match is None:
        return []
    return [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})", match.group("body"))]


def require(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def audit_hash_matches_current(audit: dict[str, Any], key: str, path: pathlib.Path) -> bool:
    source = audit.get("source_manifest", {}).get("critical_sources", {}).get(key, {})
    return isinstance(source, dict) and source.get("sha256") == digest(path)


def evaluate() -> dict[str, Any]:
    required = [
        VENDOR_EPAPER,
        DRIVER,
        MAKEFILE,
        BUILD,
        RUNNER,
        REQUIREMENTS,
        PANEL_CORRELATION,
        SOURCE_AUDIT,
        RECOVERY_GATE,
        P0_CLOSURE,
        WHITE_RAIL,
        REPLACEMENT_FPC,
        DIAGNOSTIC_IMAGE,
        OPERATOR_LOOP_IMAGE,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "NO_GO_INPUT_MISSING", "failures": missing, "checks": {}}

    vendor_text = VENDOR_EPAPER.read_text(encoding="utf-8", errors="replace")
    driver_text = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    makefile_text = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    build_text = BUILD.read_text(encoding="utf-8-sig", errors="replace")
    runner_text = RUNNER.read_text(encoding="utf-8-sig", errors="replace")
    requirements_text = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    panel = load_json(PANEL_CORRELATION)
    audit = load_json(SOURCE_AUDIT)
    recovery = load_json(RECOVERY_GATE)
    p0_closure = load_json(P0_CLOSURE)
    white_rail = load_json(WHITE_RAIL)
    replacement_fpc = load_json(REPLACEMENT_FPC)
    vendor_lut = extract_array(vendor_text, "LUT_DATA")
    target_lut = extract_array(driver_text, "ssd1681_vendor_1s_lut")
    vendor_sha = hashlib.sha256(bytes(vendor_lut)).hexdigest().upper() if vendor_lut else ""
    target_sha = hashlib.sha256(bytes(target_lut)).hexdigest().upper() if target_lut else ""
    failures: list[str] = []
    checks = {
        "owner_authorized_supplier_provenance_and_diagnostic_use": "COMP-REQ-168" in requirements_text
        and "explicitly authorized use of its one-second LUT" in requirements_text
        and "COMP-REQ-169" in requirements_text
        and "COMP-REQ-171" in requirements_text
        and "fixed maximum of 360 full frames" in requirements_text,
        "panel_marking_correlates_to_t03_ssd1681": panel.get("status")
        == "PASS_OWNER_PHOTO_LABEL_OBSERVED_UNARCHIVED"
        and panel.get("target") == "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "historical_recovery_gate_fixture_passed": recovery.get("status")
        == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
        "replacement_fpc_evidence_passed": replacement_fpc.get("status")
        == "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE"
        and replacement_fpc.get("checks", {}).get("display_fpc_replaced") is True
        and replacement_fpc.get("checks", {}).get("logic_input_is_3v3_only") is True,
        "white_rail_measurement_passed": white_rail.get("status")
        == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE"
        and white_rail.get("checks", {}).get("positive_and_negative_refresh_rails_established") is True
        and white_rail.get("measurement", {}).get("available") is True
        and white_rail.get("measurement", {}).get("prevgh1_max_v") == 20.0
        and white_rail.get("measurement", {}).get("prevgl1_min_v") == -20.0,
        "current_p0_official_white_black_closure_passed": p0_closure.get("status")
        == "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO",
        "source_audit_preserves_non_promotion_boundary": audit.get("machine_status")
        == "PASS_AUDIT_COMPLETE"
        and audit.get("promotion_status") == "NO_GO_PANEL_IDENTITY_UNPROVEN"
        and audit.get("production_off_diagnostic", {}).get("allowed") is False
        and audit.get("command_evidence", {}).get("production_lut_reference_absent") is True,
        "supplier_lut_has_159_bytes": len(vendor_lut) == 159,
        "supplier_lut_sha256_matches_manifest": vendor_sha == EXPECTED_LUT_SHA256,
        "diagnostic_lut_has_159_bytes": len(target_lut) == 159,
        "diagnostic_lut_is_verbatim_supplier_data": target_lut == vendor_lut
        and target_sha == EXPECTED_LUT_SHA256,
        "diagnostic_image_sha256_is_source_bound": digest(DIAGNOSTIC_IMAGE)
        == EXPECTED_DIAGNOSTIC_IMAGE_SHA256,
        "operator_loop_image_sha256_is_source_bound": digest(OPERATOR_LOOP_IMAGE)
        == EXPECTED_OPERATOR_LOOP_IMAGE_SHA256,
        "diagnostic_is_default_off": "#define COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC 0" in driver_text,
        "operator_loop_is_default_off_and_requires_source_bound_diagnostic": all(
            token in driver_text
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_OPERATOR_LOOP_DIAGNOSTIC 0",
                "SSD1681 vendor one-second LUT operator loop requires the source-bound LUT diagnostic",
            )
        ),
        "diagnostic_lut_is_compile_guarded": "#if COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC\n/* Literal, source-bound copy" in driver_text,
        "vendor_reset_is_100ms_low_then_high": "vendor_1s_lut reset low_ms=100 high_ms=100" in driver_text
        and "HAL_Delay(100u);" in driver_text,
        "operator_replay_waits_for_visible_prompt_window": "#define SSD1681_VENDOR_1S_LUT_REVIEW_START_DELAY_MS 5000u" in driver_text
        and "vendor_1s_lut review_start_delay_ms=%lu" in driver_text,
        "vendor_init_loads_exact_tail_registers": all(
            token in driver_text
            for token in (
                "ssd1681_command_data(0x3Fu, &ssd1681_vendor_1s_lut[153], 1u)",
                "ssd1681_command_data(0x03u, &ssd1681_vendor_1s_lut[154], 1u)",
                "ssd1681_command_data(0x04u, &ssd1681_vendor_1s_lut[155], 3u)",
                "ssd1681_command_data(0x2Cu, &ssd1681_vendor_1s_lut[158], 1u)",
            )
        ),
        "vendor_init_loads_153_bytes_to_0x32": "ssd1681_command_data(0x32u, ssd1681_vendor_1s_lut, 153u)" in driver_text,
        "vendor_refresh_is_full_5000_byte_0x24_then_c7_20_busy": all(
            token in driver_text
            for token in (
                "good_display_vendor_1s_lut_0x24_only",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                "? 0xC7u",
                "ssd1681_command(0x20u)",
                "ssd1681_wait_refresh_complete",
            )
        ),
        "diagnostic_uses_six_isolated_full_frames": all(
            token in build_text
            for token in (
                "[switch]$EpaperSsd1681Vendor1sLutDiagnostic",
                "EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC=1",
                "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
                "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=6",
                "BUILD_DIR=build_vendor_1s_lut_diagnostic",
            )
        ),
        "operator_loop_is_a_separate_bounded_build": all(
            token in build_text
            for token in (
                "[switch]$EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic",
                "EPAPER_SSD1681_VENDOR_1S_LUT_OPERATOR_LOOP_DIAGNOSTIC=1",
                "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
                "BUILD_DIR=build_vendor_1s_lut_operator_loop_diagnostic",
                "TARGET=Companion_Nucleo_WB55RG_Vendor1sLutOperatorLoopDiagnostic",
            )
        ),
        "operator_loop_repeats_the_same_six_marker_positions": "(uint8_t)((cycle - 1u) % 6u)" in driver_text,
        "makefile_exposes_only_explicit_diagnostic_macros": all(
            token in makefile_text
            for token in (
                "EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC",
                "EPAPER_SSD1681_VENDOR_1S_LUT_OPERATOR_LOOP_DIAGNOSTIC",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC=1",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_OPERATOR_LOOP_DIAGNOSTIC=1",
            )
        ),
        "runner_flashes_bounded_operator_loop_after_machine_pass": all(
            token in runner_text
            for token in (
                "flash_vendor_1s_lut_operator_loop",
                "foreach ($step in $steps[0..2])",
                "$operatorLoop = $steps[3]",
                "$restore = $steps[4]",
                "machine_six_frame_pass_then_bounded_360_frame_operator_loop",
                "maximum_full_frames = 360",
            )
        ),
        "runner_directly_requires_current_replacement_fpc_and_white_rail": all(
            token in runner_text
            for token in (
                "$WhiteRailPath",
                "$ReplacementFpcPath",
                "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE",
                "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE",
                "prevgh1_max_v -ne 20.0",
                "prevgl1_min_v -ne -20.0",
                "$static.images.diagnostic.sha256",
                "$static.images.operator_loop.sha256",
                "diagnostic image hash does not match the source-bound static contract",
            )
        ),
        "source_audit_still_matches_supplier_and_driver": audit.get("machine_status") == "PASS_AUDIT_COMPLETE"
        and audit_hash_matches_current(audit, "epaper_c", VENDOR_EPAPER)
        and audit_hash_matches_current(audit, "current_ssd1681_target", DRIVER),
    }
    for name, passed in checks.items():
        require(passed, name, failures)
    hardware_execution_authorized = not failures
    return {
        "status": "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_1S_LUT" if hardware_execution_authorized else "NO_GO_VENDOR_1S_LUT_DIAGNOSTIC_NOT_AUTHORIZED",
        "failures": failures,
        "checks": checks,
        "source": {
            "vendor_epaper_c": {"path": str(VENDOR_EPAPER), "sha256": digest(VENDOR_EPAPER)},
            "supplier_lut_sha256": vendor_sha,
            "target_driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
            "target_lut_sha256": target_sha,
        },
        "images": {
            "diagnostic": {
                "path": rel(DIAGNOSTIC_IMAGE),
                "sha256": digest(DIAGNOSTIC_IMAGE),
            },
            "operator_loop": {
                "path": rel(OPERATOR_LOOP_IMAGE),
                "sha256": digest(OPERATOR_LOOP_IMAGE),
                "maximum_full_frames": 360,
            },
        },
        "authorization": {
            "hardware_execution_authorized": hardware_execution_authorized,
            "source_audit": {
                "path": rel(SOURCE_AUDIT),
                "sha256": digest(SOURCE_AUDIT),
                "promotion_status": audit.get("promotion_status"),
                "production_off_diagnostic_allowed_by_source_audit": audit.get(
                    "production_off_diagnostic", {}
                ).get("allowed"),
                "current_room_diagnostic_authorization": "COMP-REQ-168/169/171",
            },
            "current_p0_closure": {
                "path": rel(P0_CLOSURE),
                "sha256": digest(P0_CLOSURE),
                "status": p0_closure.get("status"),
            },
            "white_rail": {
                "path": rel(WHITE_RAIL),
                "sha256": digest(WHITE_RAIL),
                "status": white_rail.get("status"),
                "prevgh1_max_v": white_rail.get("measurement", {}).get("prevgh1_max_v"),
                "prevgl1_min_v": white_rail.get("measurement", {}).get("prevgl1_min_v"),
            },
            "replacement_fpc": {
                "path": rel(REPLACEMENT_FPC),
                "sha256": digest(REPLACEMENT_FPC),
                "status": replacement_fpc.get("status"),
            },
        },
        "controlled_behavior": {
            "production_default": "disabled",
            "diagnostic_build": "machine six-frame pass then one source-identical bounded 360-frame operator loop",
            "operator_loop_marker_positions": 6,
            "operator_loop_maximum_full_frames": 360,
            "refresh": "0x24, 0x22=0xC7, 0x20, BUSY high-active/low-ready",
            "source_temperature_table": "not supplied",
            "temperature_claim": "none",
            "production_promotion": "not authorized",
            "hardware_execution_authorized": hardware_execution_authorized,
            "normal_firmware_restore_required": True,
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    try:
        result = evaluate()
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: cannot verify vendor one-second diagnostic: {error}", file=sys.stderr)
        return 1
    report = {
        "schema_id": SCHEMA_ID,
        "claim_scope": "owner-authorized source-bound production-off diagnostic static contract only",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        **result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: vendor one-second LUT diagnostic static check -> {rel(output)}")
    return 0 if report["status"] == "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_1S_LUT" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
