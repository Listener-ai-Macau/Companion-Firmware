#!/usr/bin/env python3
"""Verify the current WB55 e-paper hardware recovery gate."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = (
    ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
)
PRODUCT_REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
GRAIN_RESEARCH = (
    ROOT
    / "docs/validation/companion-screen-ssd1681-grain-recovery-research-20260714.md"
)
OFFICIAL_RECOVERY = (
    ROOT
    / "docs/validation/companion-screen-ssd1681-official-full-recovery-20260714.json"
)
VOLTAGE_PROBE = (
    ROOT
    / "docs/validation/companion-screen-ssd1681-voltage-probe-image-20260714.json"
)
VOLTAGE_OPERATOR = (
    ROOT
    / "docs/validation/companion-screen-ssd1681-voltage-rails-operator-20260714.json"
)
NORMAL_RESTORE = (
    ROOT
    / "docs/validation/companion-screen-normal-restore-after-black-20260714.json"
)
SCHEMA_ID = "companion.screen.wb55_hardware_recovery_gate.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_sources(errors: list[str]) -> dict[str, dict[str, Any]]:
    for path in (
        PRODUCT_REQUIREMENTS,
        GRAIN_RESEARCH,
        OFFICIAL_RECOVERY,
        VOLTAGE_PROBE,
        VOLTAGE_OPERATOR,
        NORMAL_RESTORE,
    ):
        require(path.exists(), f"missing source {rel(path)}", errors)
    if errors:
        return {}

    product_text = PRODUCT_REQUIREMENTS.read_text(encoding="utf-8")
    research_text = GRAIN_RESEARCH.read_text(encoding="utf-8")
    official = load_json(OFFICIAL_RECOVERY)
    voltage = load_json(VOLTAGE_PROBE)
    operator = load_json(VOLTAGE_OPERATOR)
    normal = load_json(NORMAL_RESTORE)

    for token in (
        "COMP-REQ-034",
        "active P0; refresh-voltage failure measured",
        "replace or cross-swap FTS02 before replacing the panel module",
        "Do not modify expression, menu, recording, or normal refresh policy",
        "deterministic solid black and solid white frames, then the normal expression",
    ):
        require(token in product_text, f"COMP-REQ-034 missing token: {token}", errors)
    for token in (
        "FTS02 analog repair map",
        "Q1",
        "Si1308EDL",
        "P3=2.2",
        "measure PREVGH/PREVGL",
    ):
        require(token in research_text, f"grain recovery research missing token: {token}", errors)

    require(
        official.get("status") == "NO_GO_DIGITAL_CONTROL_PASS_ANALOG_PANEL_FAIL",
        "official white/black recovery must remain NO_GO",
        errors,
    )
    for color in ("white_result", "black_result"):
        result = official.get(color, {})
        require(result.get("data_planes") == 1, f"{color} must use one plane", errors)
        require(result.get("refresh_complete") is True, f"{color} must complete", errors)
        require(
            result.get("soft_reset_busy_asserted") is True,
            f"{color} must retain BUSY evidence",
            errors,
        )
        require(
            result.get("operator_selection") == "失败",
            f"{color} must retain operator FAIL",
            errors,
        )

    measurement = voltage.get("measurement_result", {})
    require(
        measurement.get("decision") == "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED",
        "voltage probe must keep the refresh-voltage NO_GO",
        errors,
    )
    require(
        measurement.get("prevgl1_min_v") == 0.0042,
        "PREVGL1 minimum must remain 4.2 mV",
        errors,
    )
    require(
        measurement.get("prevgh1_max_v") == 3.3,
        "PREVGH1 maximum must remain 3.3 V",
        errors,
    )
    require(
        operator.get("selected") == "FAIL",
        "voltage operator result must remain FAIL",
        errors,
    )
    require(
        operator.get("decision", {}).get("result")
        == "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED",
        "operator decision must retain the refresh-voltage NO_GO",
        errors,
    )
    require(
        normal.get("status") == "NO_GO_NORMAL_EXPRESSION_NOT_VISIBLE",
        "normal expression recovery must remain NO_GO",
        errors,
    )
    return {
        "official": official,
        "voltage": voltage,
        "operator": operator,
        "normal": normal,
    }


def build_contract(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    official = sources.get("official", {})
    voltage = sources.get("voltage", {})
    measurement = voltage.get("measurement_result", {})
    normal = sources.get("normal", {})
    return {
        "schema_id": SCHEMA_ID,
        "gate_id": "wb55_real_panel_refresh",
        "status": "DEFERRED_HARDWARE_FTS02_BOOST",
        "claim_scope": "current_hardware_recovery_gate_no_panel_acceptance",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "current_fault": {
            "classification": "REFRESH_VOLTAGE_NOT_ESTABLISHED",
            "visible_result": "black-white grain/noise, not a valid framebuffer",
            "digital_command_path": "PASS_OFFICIAL_0X24_BUSY_ASSERT_RETURN",
            "positive_rail_max_v": measurement.get("prevgh1_max_v"),
            "negative_rail_min_v": measurement.get("prevgl1_min_v"),
            "operator_result": sources.get("operator", {}).get("selected"),
            "normal_expression_visible": normal.get("status")
            != "NO_GO_NORMAL_EXPRESSION_NOT_VISIBLE",
        },
        "historical_evidence_policy": {
            "previous_visible_refresh_records_retained": True,
            "previous_visible_refresh_is_current_acceptance": False,
            "reason": (
                "Later official white/black diagnostics and measured PREVGH/PREVGL "
                "contradict current panel health, so historical refresh evidence is "
                "context only until the analog path is restored and reaccepted."
            ),
        },
        "recovery_order": [
            "Replace or cross-swap ESP32-FTS02 before replacing the panel module.",
            "Keep P3 at 2.2, fully latch the 24-pin e-paper FPC in P5, and verify 3.3 V logic power and common ground.",
            "Under the Companion-WB55 workflow lock, rerun the official one-plane white diagnostic and then the black diagnostic while capturing BUSY.",
            "If either frame fails, measure PREVGH1 and PREVGL1 during the verified refresh window and stop before expression/menu changes.",
            "After solid white and black pass, restore normal firmware and prove the current expression, one partial transition, touch, and one maintenance boundary.",
        ],
        "acceptance_criteria": {
            "official_white_solid_and_deterministic": False,
            "official_black_solid_and_deterministic": False,
            "busy_assert_and_return": bool(
                official.get("white_result", {}).get("soft_reset_busy_asserted")
                and official.get("black_result", {}).get("soft_reset_busy_asserted")
            ),
            "positive_and_negative_refresh_rails_established": False,
            "normal_current_expression_visible": False,
            "partial_expression_transition_visible": False,
            "touch_and_maintenance_visual_recheck_passed": False,
        },
        "missing_hardware_facts": [
            "Replacement or cross-swapped FTS02 board identity and wiring check.",
            "Deterministic solid-white and solid-black official one-plane frames with BUSY evidence after replacement.",
            "Established positive PREVGH1 and negative PREVGL1 refresh rails, or equivalent vendor-specified rail evidence.",
            "Visible current normal expression, partial expression transition, touch response, and maintenance boundary on the recovered panel.",
        ],
        "prohibited_shortcuts": [
            "Do not change expression, menu, recording, CEMP, or normal refresh policy to compensate for the analog fault.",
            "Do not use TP_INT/PC6 or optional TP_RST/PC10 as e-paper recovery wiring.",
            "Do not promote historical visible-refresh evidence as current acceptance.",
            "Do not replace the panel module before FTS02 replacement/cross-swap unless new rail evidence contradicts the current diagnosis.",
        ],
        "sources": {
            "product_requirements": rel(PRODUCT_REQUIREMENTS),
            "grain_recovery_research": rel(GRAIN_RESEARCH),
            "official_white_black_recovery": rel(OFFICIAL_RECOVERY),
            "voltage_probe": rel(VOLTAGE_PROBE),
            "voltage_operator_review": rel(VOLTAGE_OPERATOR),
            "normal_restore": rel(NORMAL_RESTORE),
        },
        "wba_impact": (
            "Keep this failure target-local. WBA55/WBA65 reuse portable screen, "
            "expression, touch, and refresh-intent contracts but require their own "
            "panel power/rail implementation and real hardware evidence."
        ),
        "validation_commands": [
            "python .\\tools\\verify_wb55_screen_hardware_recovery_gate.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\verify_companion_screen_goal_audit.py",
        ],
    }


def check_contract(contract: dict[str, Any], errors: list[str]) -> None:
    require(contract.get("schema_id") == SCHEMA_ID, "unexpected schema_id", errors)
    require(
        contract.get("gate_id") == "wb55_real_panel_refresh",
        "hardware recovery gate id drifted",
        errors,
    )
    require(
        contract.get("status") == "DEFERRED_HARDWARE_FTS02_BOOST",
        "hardware recovery gate must remain deferred",
        errors,
    )
    require(
        contract.get("claim_scope")
        == "current_hardware_recovery_gate_no_panel_acceptance",
        "hardware gate must not claim panel acceptance",
        errors,
    )
    criteria = contract.get("acceptance_criteria", {})
    require(criteria.get("busy_assert_and_return") is True, "BUSY proof missing", errors)
    for key in (
        "official_white_solid_and_deterministic",
        "official_black_solid_and_deterministic",
        "positive_and_negative_refresh_rails_established",
        "normal_current_expression_visible",
        "partial_expression_transition_visible",
        "touch_and_maintenance_visual_recheck_passed",
    ):
        require(criteria.get(key) is False, f"{key} must remain false", errors)
    require(
        len(contract.get("missing_hardware_facts", [])) == 4,
        "hardware gate must list four concrete missing facts",
        errors,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args(argv)

    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    errors: list[str] = []
    sources = validate_sources(errors)
    contract = build_contract(sources)
    check_contract(contract, errors)
    rendered = json.dumps(contract, indent=2, sort_keys=True) + "\n"
    if args.write_fixture and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(rendered, encoding="utf-8")
    elif not fixture.exists():
        errors.append(f"missing fixture {rel(fixture)}")
    elif fixture.read_text(encoding="utf-8") != rendered:
        errors.append(f"stale fixture {rel(fixture)}; rerun with --write-fixture")

    if errors:
        print("FAIL: WB55 screen hardware recovery gate failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 current screen recovery remains hardware-deferred -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
