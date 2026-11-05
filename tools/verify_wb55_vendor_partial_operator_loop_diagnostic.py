#!/usr/bin/env python3
"""Verify the source-bound Good Display partial-refresh operator-loop contract."""

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
RUNNER = ROOT / "tools/run_wb55_vendor_partial_operator_loop_diagnostic.ps1"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
DEFAULT_OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-operator-loop-static-20260720.json"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_operator_loop_static.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: pathlib.Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(decoded, dict):
        raise ValueError(f"{path} is not a JSON object")
    return decoded


def audit_hash_matches_current(audit: dict[str, Any], key: str, path: pathlib.Path) -> bool:
    source = audit.get("source_manifest", {}).get("critical_sources", {}).get(key, {})
    return source.get("sha256") == digest(path)


def evaluate() -> dict[str, Any]:
    required = (DRIVER, MAKEFILE, BUILD, RUNNER, REQUIREMENTS, SOURCE_AUDIT, RECOVERY_GATE)
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "NO_GO_INPUT_MISSING", "failures": missing, "checks": {}}

    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
    runner = RUNNER.read_text(encoding="utf-8-sig", errors="replace")
    requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    audit = load_json(SOURCE_AUDIT)
    recovery = load_json(RECOVERY_GATE)
    checks = {
        "owner_authorized_source_partial_comparator": "COMP-REQ-172" in requirements
        and "0x3C=0x80" in requirements
        and "0x22=0xFF" in requirements
        and "COMP-REQ-173" in requirements
        and "UINT8_MAX" in requirements,
        "current_fpc_white_black_recovery_gate_passed": recovery.get("status")
        == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
        "source_audit_passes_and_binds_current_driver": audit.get("machine_status") == "PASS_AUDIT_COMPLETE"
        and audit_hash_matches_current(audit, "current_ssd1681_target", DRIVER),
        "source_audit_proves_vendor_partial_sequence": all(
            audit.get("vendor_checks", {}).get(name) is True
            for name in (
                "partial_path_resets_and_locks_border_0x80",
                "partial_path_uses_10ms_reset_region_0x24_and_0xff_0x20",
                "partial_basemap_writes_0x24_then_0x26_before_normal_f7",
            )
        ),
        "operator_loop_is_default_off_and_source_partial_only": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC 0",
                "SSD1681 vendor partial operator loop requires the vendor partial diagnostic path",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC != 0u",
            )
        ),
        "target_basemap_order_and_region_path_are_source_bound": all(
            token in driver
            for token in (
                "vendor_partial_source basemap_reset low_ms=100 high_ms=100",
                "vendor_partial_source region_reset low_ms=10 high_ms=10",
                "ssd1681_set_window_vendor_partial_source",
                "static const uint8_t border_lock[] = {0x80u};",
                "good_display_vendor_partial_basemap_0x24_then_0x26",
                "good_display_vendor_partial_source",
                "? (partial ? 1u : 2u)",
                "comp_epaper_refresh_policy_init(&s_target_context.refresh_policy, UINT8_MAX);",
            )
        ),
        "build_is_separate_bounded_and_default_off": all(
            token in build
            for token in (
                "[switch]$EpaperSsd1681VendorPartialOperatorLoopDiagnostic",
                "EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC=1",
                "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
                "BUILD_DIR=build_vendor_partial_operator_loop_diagnostic",
                "TARGET=Companion_Nucleo_WB55RG_VendorPartialOperatorLoopDiagnostic",
            )
        ),
        "makefile_requires_explicit_partial_operator_macro": all(
            token in makefile
            for token in (
                "EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC=1",
            )
        ),
        "runner_requires_machine_trace_before_operator_loop": all(
            token in runner
            for token in (
                "flash_vendor_partial_operator_loop",
                "parse_vendor_partial_operator_loop",
                "machine_pass_then_bounded_360_frame_source_partial_operator_loop",
                "flash_normal_restore",
            )
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_OPERATOR_LOOP"
        if not failures
        else "NO_GO_STATIC_VENDOR_PARTIAL_OPERATOR_LOOP_CONTRACT_INCOMPLETE",
        "failures": failures,
        "checks": checks,
        "source": {
            "target_driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
            "source_audit": {"path": rel(SOURCE_AUDIT), "sha256": digest(SOURCE_AUDIT)},
        },
        "controlled_behavior": {
            "production_default": "disabled",
            "baseline": "source 0x24 then 0x26, 5000 bytes each, 0xF7, 0x20, BUSY",
            "region_refresh": "source 10 ms reset, border 0x80, one changed-region 0x24, 0xFF, 0x20, BUSY",
            "operator_loop_maximum_frames": 360,
            "operator_loop_maintenance_full_refresh": "disabled with UINT8_MAX only in this diagnostic image",
            "temperature_claim": "none",
            "production_promotion": "not authorized",
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
        print(f"NO_GO: cannot verify vendor partial operator loop: {error}", file=sys.stderr)
        return 1
    report = {
        "schema_id": SCHEMA_ID,
        "claim_scope": "owner-authorized source-bound production-off partial comparator only",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        **result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: vendor partial operator-loop static check -> {rel(output)}")
    return 0 if report["status"] == "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_OPERATOR_LOOP" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
