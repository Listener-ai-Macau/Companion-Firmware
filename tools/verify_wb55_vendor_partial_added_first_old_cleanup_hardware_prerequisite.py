#!/usr/bin/env python3
"""Fail-closed prerequisite gate for the added-first old-cleanup diagnostic.

The r2 White/Black/rail set is immutable physical evidence for the replacement
FPC and FTS02 rail path.  It deliberately retains its historical source hash.
This verifier never recasts that run as a trace of the current diagnostic: it
instead binds the retained r2 facts to a separate current-source assertion that
the new diagnostic remains default-disabled in the ordinary firmware.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
FPC = ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
R2_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate-r2-20260720.json"
R2_CLOSURE = ROOT / "docs/validation/companion-gdey0154d67-t03-p0-closure-r2-20260720.json"
R2_RAIL = ROOT / "docs/validation/companion-screen-wb55-white-rail-measurement-current-source-r2-20260720.json"
R2_ROOT = ROOT / ".cache/validation/wb55-screen-recovery-current-source-r2-20260720"
R2_WHITE_STAGE = R2_ROOT / "white/stage-run.json"
R2_BLACK_STAGE = R2_ROOT / "black/stage-run.json"
R2_WHITE_DIGITAL = R2_ROOT / "white/official-full-result.json"
R2_BLACK_DIGITAL = R2_ROOT / "black/official-full-result.json"
SUPPLIER = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-r2-hardware-prerequisite-20260721.json"
SCHEMA = "companion.wb55.gdey0154d67_t03.vendor_partial_added_first_old_cleanup_r2_hardware_prerequisite.v1"
VENDOR_SHA256 = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
R2_DRIVER_SHA256 = "66A5A2E7DC1F85BC7A02F0BCDA9F009BEA6B96E2995941E90E218D141FF2EE3F"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def require(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)


def source_ref(value: dict[str, Any]) -> str | None:
    return value.get("source_audit", {}).get("current_ssd1681_target_sha256")


def evaluate() -> tuple[dict[str, Any], bool]:
    inputs = (
        DRIVER,
        REQUIREMENTS,
        FPC,
        R2_GATE,
        R2_CLOSURE,
        R2_RAIL,
        R2_WHITE_STAGE,
        R2_BLACK_STAGE,
        R2_WHITE_DIGITAL,
        R2_BLACK_DIGITAL,
        SUPPLIER,
    )
    missing = [rel(path) for path in inputs if not path.is_file()]
    if missing:
        return ({"schema_id": SCHEMA, "status": "FAIL_INPUT_MISSING", "failures": missing}, False)

    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    fpc = load(FPC)
    r2_gate = load(R2_GATE)
    r2_closure = load(R2_CLOSURE)
    rail = load(R2_RAIL)
    white_stage = load(R2_WHITE_STAGE)
    black_stage = load(R2_BLACK_STAGE)
    white_digital = load(R2_WHITE_DIGITAL)
    black_digital = load(R2_BLACK_DIGITAL)
    checks: dict[str, bool] = {}

    require(
        checks,
        "owner_authorized_versioned_r2_prerequisite_only",
        "COMP-REQ-255" in requirements
        and "vendor_partial_added_first_old_cleanup" in requirements,
    )
    require(checks, "supplier_input_hash_is_immutable", digest(SUPPLIER) == VENDOR_SHA256)
    require(
        checks,
        "replacement_fpc_evidence_passes",
        fpc.get("status") == "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE"
        and fpc.get("owner_observation", {}).get("replacement_display_fpc_installed") is True
        and fpc.get("owner_observation", {}).get("current_dynamic_expressions_visible") is True,
    )
    require(
        checks,
        "r2_gate_retains_official_white_black_rail_pass",
        r2_gate.get("status") == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST"
        and r2_gate.get("source_binding", {}).get("current_ssd1681_target_sha256") == R2_DRIVER_SHA256
        and r2_gate.get("source_binding", {}).get("vendor_epaper_c_sha256") == VENDOR_SHA256,
    )
    require(
        checks,
        "r2_closure_retains_lut_and_dynamic_no_go",
        r2_closure.get("status") == "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO"
        and r2_closure.get("enforced_invariants", {}).get("official_white_black_are_0x24_one_5000_byte_plane_f7_0x20_busy") is True
        and r2_closure.get("vendor_lut_disposition", {}).get("promotion_status") == "NO_GO_PANEL_IDENTITY_UNPROVEN",
    )
    for color, stage, digital in (
        ("white", white_stage, white_digital),
        ("black", black_stage, black_digital),
    ):
        require(
            checks,
            f"r2_{color}_stage_machine_operator_restore_passes",
            stage.get("stage", "").lower() == color
            and stage.get("status") == "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS"
            and stage.get("normal_firmware_restored") is True
            and stage.get("diagnostic_left_installed") is False
            and stage.get("operator_review", {}).get("selected") == "通过"
            and bool(str(stage.get("operator_review", {}).get("note", "")).strip()),
        )
        require(
            checks,
            f"r2_{color}_digital_is_one_plane_f7_busy_and_historically_bound",
            digital.get("status") == "PASS_MACHINE_DIGITAL_ONLY"
            and all(
                digital.get("checks", {}).get(key) is True
                for key in (
                    "full_window_5000_bytes",
                    "official_current_plane_only",
                    "activation_0x20_sent",
                    "soft_reset_busy_asserted",
                    "busy_returned_ready",
                    "refresh_completed",
                    "source_audit_bound",
                )
            )
            and source_ref(digital) == R2_DRIVER_SHA256
            and digital.get("source_audit", {}).get("vendor_epaper_c_sha256") == VENDOR_SHA256,
        )
    require(
        checks,
        "r2_white_rail_is_30_cycle_positive_negative_and_historically_bound",
        rail.get("status") == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE"
        and rail.get("minimum_cycles") == 30
        and rail.get("accepted_reset_bounded_cycles") == list(range(1, 31))
        and rail.get("measurement", {}).get("prevgh1_max_v", 0) > 3.3
        and rail.get("measurement", {}).get("prevgl1_min_v", 0) < 0
        and rail.get("measurement", {}).get("operator_selected") == "通过"
        and rail.get("measurement", {}).get("screen_observation") == "uniform_white"
        and source_ref(rail) == R2_DRIVER_SHA256
        and rail.get("source_audit", {}).get("vendor_epaper_c_sha256") == VENDOR_SHA256,
    )
    require(
        checks,
        "current_driver_keeps_candidate_default_off",
        "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_DIAGNOSTIC 0" in driver
        and "#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_DIAGNOSTIC" in driver,
    )
    require(
        checks,
        "current_driver_keeps_official_full_white_black_transport",
        "ssd1681_write_plane_region(0x24u, s_frame, &window)" in driver
        and "update_control = vendor_1s_lut_diagnostic" in driver
        and ": 0xF7u;" in driver
        and "ssd1681_command(0x20u)" in driver
        and "ssd1681_wait_refresh_complete" in driver,
    )

    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": SCHEMA,
        "status": "PASS_R2_HARDWARE_PREREQUISITE_ADDED_FIRST_OLD_CLEANUP_UNPROVEN"
        if not failures
        else "FAIL_R2_HARDWARE_PREREQUISITE",
        "machine_status": "PASS_STATIC_HARDWARE_PREREQUISITE_ONLY" if not failures else "FAIL_STATIC",
        "claim_scope": (
            "r2 replacement-FPC/White/Black/rail prerequisite plus current default-off source guard; "
            "not a claim that r2 executed the current diagnostic or that the candidate is residue-free"
        ),
        "checks": checks,
        "failures": failures,
        "historical_source_binding": {
            "r2_ssd1681_target_sha256": R2_DRIVER_SHA256,
            "vendor_epaper_c_sha256": VENDOR_SHA256,
            "preserved_not_rebound_to_current_source": True,
        },
        "current_source_guard": {
            "driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
            "product_requirements": {"path": rel(REQUIREMENTS), "sha256": digest(REQUIREMENTS)},
            "candidate_default": "disabled",
            "official_full_path_asserted": "0x24 current plane, 0xF7, 0x20, BUSY",
        },
        "physical_evidence": {
            "replacement_fpc": {"path": rel(FPC), "sha256": digest(FPC)},
            "r2_gate": {"path": rel(R2_GATE), "sha256": digest(R2_GATE)},
            "r2_closure": {"path": rel(R2_CLOSURE), "sha256": digest(R2_CLOSURE)},
            "white_stage": {"path": rel(R2_WHITE_STAGE), "sha256": digest(R2_WHITE_STAGE)},
            "black_stage": {"path": rel(R2_BLACK_STAGE), "sha256": digest(R2_BLACK_STAGE)},
            "white_digital": {"path": rel(R2_WHITE_DIGITAL), "sha256": digest(R2_WHITE_DIGITAL)},
            "black_digital": {"path": rel(R2_BLACK_DIGITAL), "sha256": digest(R2_BLACK_DIGITAL)},
            "white_rail": {"path": rel(R2_RAIL), "sha256": digest(R2_RAIL)},
        },
        "forbidden_claims": [
            "No current-diagnostic physical pass before its own new machine trace and canonical operator review.",
            "No production promotion, temperature claim, LUT import, waveform mutation, or dynamic-expression binding.",
            "No rewrite or source-hash rebinding of the r2 physical artifacts.",
        ],
    }
    return report, not failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report, passed = evaluate()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    rendered = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="ascii")
    elif not out.exists():
        print(f"FAIL: missing prerequisite artifact {rel(out)}", file=sys.stderr)
        return 1
    elif out.read_text(encoding="ascii") != rendered:
        print(f"FAIL: stale prerequisite artifact {rel(out)}; rerun with --write", file=sys.stderr)
        return 1
    print(f"{'PASS' if passed else 'FAIL'}: r2 hardware prerequisite -> {rel(out)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
