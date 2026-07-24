#!/usr/bin/env python3
"""Audit the official White and observed external-CEMP full-refresh paths.

This is deliberately a source-and-artifact differential audit.  It records the
real plane-write difference without treating a clean expression as proof that
the failed official White path may be changed, or that the FTS02 voltage gate
has recovered.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PANEL_SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
WHITE_FAILURE = ROOT / "docs/validation/companion-screen-wb55-white-recovery-failure-20260719.json"
CLEAN_EXPRESSION = ROOT / "docs/validation/companion-screen-v9-clean-expression-observation-20260719.json"
RAIL_FAILURE = ROOT / "docs/validation/companion-screen-ssd1681-voltage-rails-operator-20260714.json"
SCHEMA_ID = "companion.wb55.white_expression_path_differential.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    source = PANEL_SOURCE.read_text(encoding="utf-8")
    white = load_json(WHITE_FAILURE)
    expression = load_json(CLEAN_EXPRESSION)
    rails = load_json(RAIL_FAILURE)
    white_machine = white.get("machine_result", {})
    expression_frame = expression.get("machine_correlated_frame", {})
    rail_measurement = rails.get("measurement", {})

    checks = {
        "failed_white_is_recorded_official_single_plane": (
            white.get("status") == "FAIL_VISIBLE_OFFICIAL_WHITE_FULL_REFRESH"
            and white_machine.get("official_one_plane_0x24_only") is True
            and white_machine.get("data_planes") == 1
            and white_machine.get("bytes") == 5000
            and white_machine.get("refresh_mode") == "full"
            and white_machine.get("busy_asserted_and_completed") is True
            and white_machine.get("refresh_elapsed_ms", 5001) <= 5000
        ),
        "accepted_expression_is_two_plane_full_refresh": (
            expression.get("status")
            == "PASS_OWNER_ACCEPTED_LIMITED_CLEAN_EXTERNAL_CEMP_BASELINE"
            and expression_frame.get("source") == "locked_v9_external_cemp"
            and expression_frame.get("refresh_mode") == "full"
            and expression_frame.get("data_planes") == 2
            and expression_frame.get("frame_bytes_per_plane") == 5000
            and expression_frame.get("update_control") == "0xF7"
            and expression_frame.get("refresh_complete") is True
            and expression_frame.get("elapsed_ms", 5001) <= 5000
        ),
        "official_source_uses_current_plane_only": (
            "COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC" in source
            and "normal full path, which writes 0x24 only before 0xF7" in source
            and "ssd1681_write_plane_region(0x24u, s_frame, &window);" in source
            and "full_write_profile=good_display_official_0x24_only" in source
        ),
        "product_full_path_is_explicit_two_plane_baseline": (
            "Product full and maintenance paths keep their accepted" in source
            and "ssd1681_write_plane_region(0x26u, s_frame, &window)" in source
            and "ssd1681_write_plane_region(0x24u, s_frame, &window)" in source
        ),
        "both_paths_share_full_window_and_activation": (
            "ssd1681_set_window(&window, vendor_sample_partial)" in source
            and "ssd1681_refresh_display(selection.decision)" in source
            and "static const uint8_t normal_border[] = {0x05u};" in source
        ),
        "rail_failure_remains_a_hardware_no_go": (
            rails.get("decision", {}).get("result")
            == "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED"
            and rail_measurement.get("prevgl1_min_v", 1.0) >= 0.0
            and rail_measurement.get("prevgh1_max_v", 99.0) <= 3.3
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_DIFFERENTIAL_NO_DRIVER_CHANGE_AUTHORIZED"
        if not failures
        else "NO_GO_WHITE_EXPRESSION_PATH_DIFFERENTIAL_INCOMPLETE",
        "claim_scope": "source_and_recorded_physical_artifact_differential_not_white_recovery_or_hardware_root_cause_proof",
        "checks": checks,
        "failures": failures,
        "observed_difference": {
            "official_white": "Good Display official full diagnostic writes current 5000-byte frame to 0x24 only before 0x22=0xF7 and 0x20.",
            "accepted_expression": "The observed locked V9 external-CEMP expression full refresh wrote two 5000-byte planes: 0x26 baseline then 0x24 current.",
            "common_path": "Both route through the same full-window setup, normal border 0x3C=0x05, full activation selection, and BUSY-completion wait."
        },
        "conclusion": "The clean expression establishes a real display-path difference, but it does not identify a mismatch with the recorded Good Display official White reference. The existing PREVGH/PREVGL failure remains controlling; no White driver, LUT, or expression policy change is authorized.",
        "next_permitted_action": "Record replacement or cross-swapped ESP32-FTS02 identity and wiring/flex seating, then repeat the official White diagnostic while measuring PREVGH1 and PREVGL1 in the verified refresh window.",
        "sources": {
            "panel_source": {"path": rel(PANEL_SOURCE), "sha256": digest(PANEL_SOURCE)},
            "white_failure": {"path": rel(WHITE_FAILURE), "sha256": digest(WHITE_FAILURE)},
            "clean_expression": {"path": rel(CLEAN_EXPRESSION), "sha256": digest(CLEAN_EXPRESSION)},
            "rail_failure": {"path": rel(RAIL_FAILURE), "sha256": digest(RAIL_FAILURE)},
        },
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        print(f"NO_GO: White/expression differential -> {rel(destination)}", file=sys.stderr)
        return 1
    print(f"PASS: White/expression differential -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
