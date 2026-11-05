#!/usr/bin/env python3
"""Verify the source-bound, production-off slow-motion partial diagnostic."""

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
RUNNER = ROOT / "tools/run_wb55_vendor_partial_slow_motion_diagnostic.ps1"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
RESIDUE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-residue-recovery-audit-20260720.json"
ACCEPTED_STAGE = ROOT / ".cache/validation/wb55-vendor-partial-operator-loop-retry-2-20260720/stage-run.json"
ACCEPTED_TRACE = ROOT / ".cache/validation/wb55-vendor-partial-operator-loop-retry-2-20260720/vendor-partial-trace.json"
DEFAULT_OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-slow-motion-static-20260720.json"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_slow_motion_static.v1"


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
    required = (
        DRIVER,
        MAKEFILE,
        BUILD,
        RUNNER,
        REQUIREMENTS,
        SOURCE_AUDIT,
        RECOVERY_GATE,
        RESIDUE_AUDIT,
        ACCEPTED_STAGE,
        ACCEPTED_TRACE,
    )
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
    residue = load_json(RESIDUE_AUDIT)
    accepted_stage = load_json(ACCEPTED_STAGE)
    accepted_trace = load_json(ACCEPTED_TRACE)
    accepted_bytes = accepted_trace.get("region_transfer_bytes", [])
    accepted_maximum = max(accepted_bytes) if accepted_bytes else 0

    checks = {
        "owner_authorizes_only_source_bound_slow_transport": all(
            token in requirements
            for token in (
                "COMP-REQ-174",
                "COMP-REQ-175",
                "COMP-REQ-200",
                "EPD_Dis_Part_myself",
                "at most two disjoint changed rectangles",
            )
        ),
        "current_fpc_white_black_recovery_gate_passed": recovery.get("status")
        == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
        "accepted_single_region_partial_review_is_preserved": accepted_stage.get("status")
        == "PASS_MACHINE_AND_OPERATOR_VENDOR_PARTIAL_OPERATOR_LOOP_NORMAL_RESTORED"
        and accepted_stage.get("operator_review", {}).get("selected") == "通过"
        and accepted_stage.get("normal_firmware_restored") is True
        and accepted_trace.get("status") == "PASS_MACHINE_VENDOR_PARTIAL_BASELINE_AND_REGION_TRACE"
        and accepted_maximum == 567,
        "source_audit_passes_binds_current_driver_and_proves_multi_region_supplier_sequence": audit.get(
            "machine_status"
        )
        == "PASS_AUDIT_COMPLETE"
        and audit_hash_matches_current(audit, "current_ssd1681_target", DRIVER)
        and audit.get("vendor_checks", {}).get(
            "partial_multi_region_path_uses_one_reset_border_five_0x24_then_one_ff_0x20"
        )
        is True,
        "slow_motion_is_default_off_and_requires_source_partial_multi_region_path": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC 0",
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_SLOW_MOTION_DIAGNOSTIC 0",
                "SSD1681 vendor partial slow motion requires the source multi-region operator loop",
            )
        ),
        "driver_emits_48_ordered_intermediate_positions_without_product_expression_binding": all(
            token in driver
            for token in (
                "#define SSD1681_VENDOR_PARTIAL_SLOW_STEPS_PER_SEGMENT 8u",
                "#define SSD1681_VENDOR_PARTIAL_SLOW_POSITION_COUNT (6u * SSD1681_VENDOR_PARTIAL_SLOW_STEPS_PER_SEGMENT)",
                "static void frame_ball_motion_slow(uint8_t phase)",
                "frame_ball_motion_slow(step);",
                "% SSD1681_VENDOR_PARTIAL_SLOW_POSITION_COUNT",
            )
        ),
        "driver_uses_at_most_two_old_new_regions_then_one_source_refresh": all(
            token in driver
            for token in (
                "static uint8_t ssd1681_source_partial_dot_regions(ssd1681_window_t regions[2])",
                "ssd1681_windows_overlap",
                "ssd1681_set_window_vendor_partial_source(&source_regions[index],",
                "ssd1681_write_plane_region(0x24u, s_frame, &source_regions[index])",
                "index == 0u",
                "\"good_display_vendor_partial_source\"",
                "? 0xFFu",
                "comp_epaper_refresh_policy_init(&s_target_context.refresh_policy, UINT8_MAX);",
            )
        ),
        "build_is_separate_bounded_and_default_off": all(
            token in build
            for token in (
                "[switch]$EpaperSsd1681VendorPartialSlowMotionDiagnostic",
                "EPAPER_SSD1681_VENDOR_PARTIAL_SLOW_MOTION_DIAGNOSTIC=1",
                "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
                "BUILD_DIR=build_vendor_partial_slow_motion_diagnostic",
                "TARGET=Companion_Nucleo_WB55RG_VendorPartialSlowMotionDiagnostic",
            )
        )
        and "EPAPER_SSD1681_VENDOR_PARTIAL_SLOW_MOTION_DIAGNOSTIC" in makefile,
        "runner_requires_machine_trace_below_accepted_limit_before_operator_review": all(
            token in runner
            for token in (
                "flash_vendor_partial_slow_motion",
                "parse_vendor_partial_slow_motion",
                "maximum_accepted_region_bytes_per_plane = 567",
                "flash_normal_restore",
                "aiw_operator_prompt_v1",
                "残影不是自动忽略项",
                "residue_observed",
            )
        ),
        "prior_residue_failure_is_retained_and_new_observation_is_explicitly_non_promotional": residue.get("status")
        == "NO_GO_PHYSICAL_RESIDUE_OBSERVED_NO_SOURCE_BOUND_CONTINUOUS_RECOVERY"
        and all(
            token in requirements
            for token in (
                "visible residue is a recorded current-room diagnostic observation",
                "physical continuous-motion observation authorized with residue recorded as diagnostic evidence",
                "No new/custom/general LUT, temperature compensation, production refresh-policy change",
            )
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_SLOW_MOTION"
        if not failures
        else "NO_GO_STATIC_VENDOR_PARTIAL_SLOW_MOTION_CONTRACT_INCOMPLETE",
        "failures": failures,
        "checks": checks,
        "source": {
            "target_driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
            "source_audit": {"path": rel(SOURCE_AUDIT), "sha256": digest(SOURCE_AUDIT)},
            "accepted_stage": {"path": rel(ACCEPTED_STAGE), "sha256": digest(ACCEPTED_STAGE)},
            "accepted_trace": {"path": rel(ACCEPTED_TRACE), "sha256": digest(ACCEPTED_TRACE)},
            "residue_audit": {"path": rel(RESIDUE_AUDIT), "sha256": digest(RESIDUE_AUDIT)},
        },
        "accepted_single_region_comparator": {
            "operator_note": accepted_stage.get("operator_review", {}).get("note"),
            "region_transfer_bytes": accepted_bytes,
            "maximum_accepted_region_bytes": accepted_maximum,
        },
        "prior_residue_observation": {
            "path": rel(RESIDUE_AUDIT),
            "status": residue.get("status"),
            "disposition": residue.get("required_disposition", {}),
        },
        "controlled_behavior": {
            "production_default": "disabled",
            "initial_basemap": "source 0x24 then 0x26, 5000 bytes each, 0xF7, 0x20, BUSY",
            "intermediate_positions": 48,
            "partial_refresh": "one source 10 ms reset, one 0x3C=0x80 lock, one or two 0x24 regions, one 0xFF, 0x20, BUSY",
            "partial_transfer_limit": f"at most {accepted_maximum} bytes, the accepted single-region maximum",
            "operator_loop_maximum_frames": 360,
            "operator_loop_maintenance_full_refresh": "disabled with UINT8_MAX only in this diagnostic image",
            "temperature_claim": "none",
            "production_promotion": "not authorized",
            "current_room_residue": "recorded in the canonical review; never treated as a no-ghosting success",
            "upper_layer_art_rig_crig_browser_binding": "not modified by this diagnostic",
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
        print(f"NO_GO: cannot verify vendor partial slow-motion diagnostic: {error}", file=sys.stderr)
        return 1
    report = {
        "schema_id": SCHEMA_ID,
        "claim_scope": "owner-authorized source-bound production-off slow-position transport only",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        **result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: vendor partial slow-motion static check -> {rel(output)}")
    return 0 if report["status"] == "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_SLOW_MOTION" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
