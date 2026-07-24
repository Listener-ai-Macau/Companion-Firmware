#!/usr/bin/env python3
"""Audit the WB55 official SSD1681 full-refresh path against recorded vendor evidence.

This is intentionally a source/trace audit.  A PASS means no software-reference
mismatch was found; it never upgrades the physical panel from its rail NO_GO.
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
RESEARCH = ROOT / "docs/validation/companion-screen-ssd1681-grain-recovery-research-20260714.md"
WHITE_FAILURE = ROOT / "docs/validation/companion-screen-wb55-white-recovery-failure-20260719.json"
RAIL_MEASUREMENT = ROOT / "docs/validation/companion-screen-ssd1681-voltage-rails-operator-20260714.json"
SCHEMA_ID = "companion.wb55.ssd1681_driver_audit.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ordered(text: str, snippets: list[str]) -> bool:
    cursor = 0
    for snippet in snippets:
        cursor = text.find(snippet, cursor)
        if cursor < 0:
            return False
        cursor += len(snippet)
    return True


def evaluate(source_text: str, failure: dict[str, Any], rail: dict[str, Any]) -> dict[str, Any]:
    window_start = source_text.find("static bool ssd1681_set_window")
    refresh_start = source_text.find("static bool ssd1681_refresh_display")
    refresh_end = source_text.find("static comp_epaper_panel_result_t ssd1681_refresh", refresh_start)
    refresh_body = source_text[refresh_start:refresh_end]
    reset_start = source_text.find("static void ssd1681_reset")
    reset_end = source_text.find("static bool ssd1681_prepare_vendor_fast_profile", reset_start)
    reset_body = source_text[reset_start:reset_end]
    official_start = source_text.find("if (official_full_diagnostic)")
    official_end = source_text.find("} else {", official_start)
    official_body = source_text[official_start:official_end]
    measurement = rail.get("measurement", {})
    machine = failure.get("machine_result", {})

    checks = {
        "full_init_values_match_recorded_good_display_reference": all(
            token in source_text
            for token in (
                "static const uint8_t driver_output[] = {0xC7u, 0x00u, 0x00u};",
                "static const uint8_t data_entry[] = {0x01u};",
                "static const uint8_t normal_border[] = {0x05u};",
                "static const uint8_t temperature[] = {0x80u};",
            )
        ),
        "full_init_command_order_matches_recorded_good_display_reference": ordered(
            source_text[window_start:refresh_start],
            (
                "ssd1681_command_data(0x01u",
                "ssd1681_command_data(0x11u",
                "ssd1681_command_data(0x44u",
                "ssd1681_command_data(0x45u",
                "ssd1681_command_data(0x3Cu",
                "ssd1681_command_data(0x18u",
                "ssd1681_command_data(0x4Eu",
                "ssd1681_command_data(0x4Fu",
            ),
        ),
        "reset_low_high_10ms_matches_recorded_good_display_reference": reset_body.count("HAL_Delay(10u)") == 2,
        "full_refresh_uses_f7_then_master_activation": ordered(
            refresh_body,
            (": 0xF7u;", "ssd1681_command_data(0x22u", "ssd1681_command(0x20u)"),
        ),
        "official_diagnostic_writes_current_0x24_plane_only": "ssd1681_write_plane_region(0x24u, s_frame, &window)" in official_body,
        "current_white_trace_was_official_one_plane_full_refresh": machine.get("official_one_plane_0x24_only") is True
        and machine.get("refresh_mode") == "full"
        and machine.get("bytes") == 5000
        and machine.get("data_planes") == 1
        and machine.get("busy_asserted_and_completed") is True
        and machine.get("parser_status") == "PASS_MACHINE_DIGITAL_ONLY",
        "current_white_visible_result_remains_fail": failure.get("status") == "FAIL_VISIBLE_OFFICIAL_WHITE_FULL_REFRESH"
        and failure.get("operator_review", {}).get("selected") == "失败",
        "historical_rails_require_hardware_not_driver_triage": measurement.get("prevgl1_min_v") == 0.0042
        and measurement.get("prevgh1_max_v") == 3.3
        and rail.get("decision", {}).get("result") == "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED",
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {"checks": checks, "failures": failures}


def build_report(result: dict[str, Any]) -> dict[str, Any]:
    status = (
        "PASS_MACHINE_AUDIT_NO_DRIVER_MISMATCH_PHYSICAL_NO_GO"
        if not result["failures"]
        else "NO_GO_DRIVER_AUDIT_INCOMPLETE"
    )
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": "source_and_recorded_trace_audit_only_no_panel_or_waveform_acceptance",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "reference": {
            "vendor_package": "S-GDEY0154D67-FP-Touch.rar",
            "vendor_package_sha256": "202ADAB27515FDBA790565F643C3C83C52C11FF36844E8C387F66676C3D82CD4",
            "recorded_reference_sequence": "reset; 01 C7 00 00; 11 01; full 44/45; 3C 05; 18 80; full 4E/4F; 24 current plane; 22 F7; 20; BUSY",
        },
        "checks": result["checks"],
        "failures": result["failures"],
        "conclusion": (
            "No software-reference mismatch was found in the current official White diagnostic. "
            "The visible failure is not evidence for an extra/shorter full refresh or a LUT change."
            if not result["failures"]
            else "The source/trace audit is incomplete; do not alter the driver until the listed failure is resolved."
        ),
        "physical_status": "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED",
        "next_permitted_action": "Record replacement or cross-swapped ESP32-FTS02 identity and wiring/flex seating, then measure PREVGH1/PREVGL1 during the same verified official White refresh.",
        "prohibited_shortcuts": [
            "Do not rerun the identical White diagnostic as a driver fix.",
            "Do not introduce a generic, nearby-panel, online, guessed, or custom LUT.",
            "Do not run Black, normal expression, V22, partial/residue, or art/choreography acceptance while White remains failed.",
        ],
        "sources": {
            "panel_source": {"path": rel(PANEL_SOURCE), "sha256": sha256(PANEL_SOURCE)},
            "recorded_vendor_comparison": rel(RESEARCH),
            "current_white_failure": rel(WHITE_FAILURE),
            "historical_rail_measurement": rel(RAIL_MEASUREMENT),
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    result = evaluate(
        PANEL_SOURCE.read_text(encoding="utf-8"),
        load_json(WHITE_FAILURE),
        load_json(RAIL_MEASUREMENT),
    )
    report = build_report(result)
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if result["failures"]:
        print(f"NO_GO: SSD1681 driver audit incomplete -> {rel(destination)}", file=sys.stderr)
        return 1
    print(f"PASS: SSD1681 driver audit found no reference mismatch -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
