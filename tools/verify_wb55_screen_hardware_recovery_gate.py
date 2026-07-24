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
RECOVERY_RUNNER = (
    ROOT
    / "docs/validation/companion-screen-wb55-hardware-recovery-runner.json"
)
VENDOR_AUDIT = (
    ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
)
FPC_REPLACEMENT_EVIDENCE = (
    ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
)
CURRENT_RUN_ROOT = ROOT / ".cache/validation/wb55-screen-recovery-current-source-20260720"
WHITE_STAGE = CURRENT_RUN_ROOT / "white/stage-run.json"
BLACK_STAGE = CURRENT_RUN_ROOT / "black/stage-run.json"
WHITE_DIGITAL = CURRENT_RUN_ROOT / "white/official-full-result.json"
BLACK_DIGITAL = CURRENT_RUN_ROOT / "black/official-full-result.json"
WHITE_RAIL = ROOT / "docs/validation/companion-screen-wb55-white-rail-measurement-current-source-20260720.json"
SCHEMA_ID = "companion.screen.wb55_hardware_recovery_gate.v3"


def resolve_repo_path(path: pathlib.Path) -> pathlib.Path:
    return path if path.is_absolute() else ROOT / path


def configure_current_evidence(current_run_root: pathlib.Path, white_rail: pathlib.Path) -> None:
    """Select a versioned physical-evidence set without replacing older raw runs."""
    global CURRENT_RUN_ROOT, WHITE_STAGE, BLACK_STAGE, WHITE_DIGITAL, BLACK_DIGITAL, WHITE_RAIL
    CURRENT_RUN_ROOT = resolve_repo_path(current_run_root)
    WHITE_STAGE = CURRENT_RUN_ROOT / "white/stage-run.json"
    BLACK_STAGE = CURRENT_RUN_ROOT / "black/stage-run.json"
    WHITE_DIGITAL = CURRENT_RUN_ROOT / "white/official-full-result.json"
    BLACK_DIGITAL = CURRENT_RUN_ROOT / "black/official-full-result.json"
    WHITE_RAIL = resolve_repo_path(white_rail)


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
        RECOVERY_RUNNER,
        VENDOR_AUDIT,
        FPC_REPLACEMENT_EVIDENCE,
        WHITE_STAGE,
        BLACK_STAGE,
        WHITE_DIGITAL,
        BLACK_DIGITAL,
        WHITE_RAIL,
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
    recovery_runner = load_json(RECOVERY_RUNNER)
    vendor_audit = load_json(VENDOR_AUDIT)
    replacement_fpc = load_json(FPC_REPLACEMENT_EVIDENCE)
    white_stage = load_json(WHITE_STAGE)
    black_stage = load_json(BLACK_STAGE)
    white_digital = load_json(WHITE_DIGITAL)
    black_digital = load_json(BLACK_DIGITAL)
    white_rail = load_json(WHITE_RAIL)

    critical_sources = vendor_audit.get("source_manifest", {}).get("critical_sources", {})
    expected_target_sha256 = critical_sources.get("current_ssd1681_target", {}).get("sha256")
    expected_vendor_epaper_c_sha256 = critical_sources.get("epaper_c", {}).get("sha256")
    require(vendor_audit.get("machine_status") == "PASS_AUDIT_COMPLETE", "vendor source audit did not pass", errors)
    require(vendor_audit.get("promotion_status") == "NO_GO_PANEL_IDENTITY_UNPROVEN", "vendor LUT identity must remain NO_GO", errors)
    require(vendor_audit.get("command_evidence", {}).get("production_lut_reference_absent") is True, "vendor LUT must remain absent from production", errors)
    require(isinstance(expected_target_sha256, str) and bool(expected_target_sha256), "vendor audit current SSD1681 source hash missing", errors)
    require(isinstance(expected_vendor_epaper_c_sha256, str) and bool(expected_vendor_epaper_c_sha256), "vendor audit EPAPER.c source hash missing", errors)

    for token in (
        "COMP-REQ-157",
        "COMP-REQ-163",
        "COMP-REQ-164",
        "NO_GO_CURRENT_WHITE_BLACK_UNRETESTED_AFTER_FPC_REPLACEMENT",
        "replacement-display-FPC evidence artifact",
        "0xC7",
    ):
        require(token in product_text, f"replacement-FPC steering missing token: {token}", errors)
    for token in (
        "FTS02 analog repair map",
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
        "historical voltage probe must remain immutable",
        errors,
    )
    require(
        measurement.get("prevgl1_min_v") == 0.0042,
        "historical PREVGL1 minimum must remain 4.2 mV",
        errors,
    )
    require(
        measurement.get("prevgh1_max_v") == 3.3,
        "historical PREVGH1 maximum must remain 3.3 V",
        errors,
    )
    require(
        operator.get("selected") == "FAIL",
        "historical voltage operator result must remain FAIL",
        errors,
    )
    require(
        operator.get("decision", {}).get("result")
        == "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED",
        "historical operator decision must retain the refresh-voltage NO_GO",
        errors,
    )
    require(
        normal.get("status") == "NO_GO_NORMAL_EXPRESSION_NOT_VISIBLE",
        "historical normal expression recovery must remain NO_GO",
        errors,
    )
    require(
        recovery_runner.get("status") == "PASS_MACHINE_PREFLIGHT",
        "staged replacement-display-FPC recovery runner preflight must pass",
        errors,
    )
    require(
        recovery_runner.get("claim_scope")
        == "static_and_stubbed_recovery_no_hardware_claim",
        "staged recovery runner must not claim current hardware recovery",
        errors,
    )
    require(
        replacement_fpc.get("schema_id")
        == "companion.wb55.display_fpc_replacement_evidence.v1",
        "replacement display-FPC evidence schema drifted",
        errors,
    )
    require(
        replacement_fpc.get("status")
        == "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE",
        "replacement display-FPC evidence must retain the owner-observed current panel status",
        errors,
    )
    observation = replacement_fpc.get("owner_observation", {})
    for field in (
        "replacement_display_fpc_installed",
        "current_dynamic_expressions_visible",
        "photo_observed_in_conversation",
    ):
        require(observation.get(field) is True, f"replacement display-FPC evidence missing {field}", errors)
    authorization = replacement_fpc.get("authorization", {})
    require(authorization.get("allowed_stage") == "White", "replacement FPC evidence must authorize White only", errors)
    require(authorization.get("black_requires") == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE", "Black must remain rail-gated", errors)
    for name, expected_stage, stage in (
        ("White", "White", white_stage),
        ("Black", "Black", black_stage),
    ):
        require(stage.get("stage") == expected_stage, f"current {name} stage identity drifted", errors)
        require(
            stage.get("status") == "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS",
            f"current {name} stage must retain source-bound machine plus operator PASS",
            errors,
        )
        require(stage.get("normal_firmware_restored") is True, f"current {name} stage did not restore normal firmware", errors)
        require(stage.get("diagnostic_left_installed") is False, f"current {name} stage left a diagnostic installed", errors)
        require(stage.get("operator_review", {}).get("selected") == "通过", f"current {name} operator result must pass", errors)
        require(
            isinstance(stage.get("operator_review", {}).get("note"), str)
            and bool(stage["operator_review"]["note"].strip()),
            f"current {name} operator observation note must be nonempty",
            errors,
        )
        require(
            len(stage.get("results", [])) >= 4
            and all(result.get("status") == "PASS" for result in stage.get("results", [])),
            f"current {name} stage has a non-PASS machine step",
            errors,
        )
    white_prerequisites = white_stage.get("prerequisites", {})
    require(white_prerequisites.get("replacement_display_fpc_validated") is True, "White stage did not validate replacement FPC evidence", errors)
    require(white_prerequisites.get("vendor_source_audit_validated") is True, "White stage did not validate source audit", errors)
    black_prerequisites = black_stage.get("prerequisites", {})
    require(black_prerequisites.get("post_white_rail_validated") is True, "Black stage did not validate White rail artifact", errors)
    require(black_prerequisites.get("vendor_source_audit_validated") is True, "Black stage did not validate source audit", errors)
    require(black_prerequisites.get("post_white_rail_path") == rel(WHITE_RAIL), "Black stage consumed an unexpected White rail artifact", errors)
    for name, expected_pattern, digital in (
        ("White", "white", white_digital),
        ("Black", "black", black_digital),
    ):
        require(digital.get("status") == "PASS_MACHINE_DIGITAL_ONLY", f"current {name} digital parser must pass", errors)
        require(digital.get("pattern") == expected_pattern, f"current {name} digital pattern drifted", errors)
        for key in (
            "full_window_5000_bytes",
            "official_current_plane_only",
            "activation_0x20_sent",
            "soft_reset_busy_asserted",
            "busy_returned_ready",
            "refresh_completed",
            "source_audit_bound",
        ):
            require(digital.get("checks", {}).get(key) is True, f"current {name} digital check missing: {key}", errors)
        digital_source_audit = digital.get("source_audit", {})
        require(
            digital_source_audit.get("current_ssd1681_target_sha256") == expected_target_sha256,
            f"current {name} digital trace is bound to a stale SSD1681 target source hash",
            errors,
        )
        require(
            digital_source_audit.get("vendor_epaper_c_sha256") == expected_vendor_epaper_c_sha256,
            f"current {name} digital trace vendor EPAPER.c source hash drifted",
            errors,
        )
    require(white_rail.get("status") == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE", "White rail artifact must pass before Black", errors)
    require(
        white_rail.get("minimum_cycles") == 30
        and white_rail.get("accepted_reset_bounded_cycles") == list(range(1, 31)),
        "White rail artifact must bind the reset-bounded complete 30-cycle run",
        errors,
    )
    for key in (
        "activation_0x20_sent",
        "every_observed_cycle_has_completed_f7_refresh",
        "every_observed_cycle_transfers_one_5000_byte_plane",
        "positive_and_negative_refresh_rails_established",
        "operator_selected_pass",
        "screen_observation_declares_uniform_white",
        "source_audit_bound",
    ):
        require(white_rail.get("checks", {}).get(key) is True, f"White rail check missing: {key}", errors)
    rail_measurement = white_rail.get("measurement", {})
    require(rail_measurement.get("prevgh1_max_v", 0) > 3.3, "White rail PREVGH1 is not positive", errors)
    require(rail_measurement.get("prevgl1_min_v", 0) < 0, "White rail PREVGL1 is not negative", errors)
    rail_source_audit = white_rail.get("source_audit", {})
    require(
        rail_source_audit.get("current_ssd1681_target_sha256") == expected_target_sha256,
        "White rail artifact is bound to a stale SSD1681 target source hash",
        errors,
    )
    require(
        rail_source_audit.get("vendor_epaper_c_sha256") == expected_vendor_epaper_c_sha256,
        "White rail artifact vendor EPAPER.c source hash drifted",
        errors,
    )
    return {
        "official": official,
        "voltage": voltage,
        "operator": operator,
        "normal": normal,
        "recovery_runner": recovery_runner,
        "vendor_audit": vendor_audit,
        "replacement_fpc": replacement_fpc,
        "white_stage": white_stage,
        "black_stage": black_stage,
        "white_digital": white_digital,
        "black_digital": black_digital,
        "white_rail": white_rail,
    }


def build_contract(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    official = sources.get("official", {})
    voltage = sources.get("voltage", {})
    measurement = voltage.get("measurement_result", {})
    normal = sources.get("normal", {})
    recovery_runner = sources.get("recovery_runner", {})
    vendor_audit = sources.get("vendor_audit", {})
    replacement_fpc = sources.get("replacement_fpc", {})
    white_stage = sources.get("white_stage", {})
    black_stage = sources.get("black_stage", {})
    white_digital = sources.get("white_digital", {})
    black_digital = sources.get("black_digital", {})
    white_rail = sources.get("white_rail", {})
    return {
        "schema_id": SCHEMA_ID,
        "gate_id": "wb55_real_panel_refresh",
        "status": "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
        "claim_scope": "source_bound_official_white_black_and_rail_retest_not_fast_lut_or_dynamic_expression_acceptance",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + replacement display FPC + GDEY0154D67-T03",
        "source_binding": {
            "vendor_source_audit": rel(VENDOR_AUDIT),
            "current_ssd1681_target_sha256": vendor_audit.get("source_manifest", {}).get("critical_sources", {}).get("current_ssd1681_target", {}).get("sha256"),
            "vendor_epaper_c_sha256": vendor_audit.get("source_manifest", {}).get("critical_sources", {}).get("epaper_c", {}).get("sha256"),
        },
        "current_fault": {
            "classification": "CURRENT_OFFICIAL_WHITE_BLACK_RETEST_PASSED_ON_REPLACEMENT_FPC",
            "owner_observed_dynamic_expressions_visible": replacement_fpc.get("owner_observation", {}).get("current_dynamic_expressions_visible"),
            "current_white_black_machine_or_operator_acceptance": True,
            "historical_old_fpc_measurement": {
                "positive_rail_max_v": measurement.get("prevgh1_max_v"),
                "negative_rail_min_v": measurement.get("prevgl1_min_v"),
                "operator_result": sources.get("operator", {}).get("selected"),
                "normal_expression_status": normal.get("status"),
            },
        },
        "historical_evidence_policy": {
            "previous_visible_refresh_records_retained": True,
            "previous_visible_refresh_is_current_acceptance": False,
            "reason": (
                "The old White failure and rail record were captured with a broken display FPC. "
                "They remain immutable history, not a diagnosis or acceptance result for the replacement FPC."
            ),
        },
        "recovery_order": [
            "Validate the versioned owner-reported replacement display-FPC evidence; the existing logic input remains 3.3 V only.",
            "Under the Companion-WB55 workflow lock, run the existing source-bound official White diagnostic and record one focused visible result.",
            "Capture a new labelled PREVGH1/PREVGL1 artifact during that verified White refresh; only a PASS machine-and-rails artifact can unlock Black.",
            "Run Black only after the new White rail artifact passes, then record one focused visible result.",
            "After solid white and black pass, run RestoreNormal, then prove the current expression, one partial transition, touch, and one maintenance boundary.",
        ],
        "recovery_runner": {
            "status": recovery_runner.get("status"),
            "claim_scope": recovery_runner.get("claim_scope"),
            "runner": recovery_runner.get("runner"),
            "parser": recovery_runner.get("parser"),
            "stage_order": ["white", "black", "restorenormal"],
            "operator_sequence": recovery_runner.get("operator_sequence", []),
            "machine_pass_is_panel_acceptance": False,
        },
        "acceptance_criteria": {
            "official_white_solid_and_deterministic": True,
            "official_black_solid_and_deterministic": True,
            "current_source_bound_white_machine_trace": True,
            "current_source_bound_black_machine_trace": True,
            "positive_and_negative_refresh_rails_established": True,
            "normal_current_expression_visible": False,
            "partial_expression_transition_visible": False,
            "touch_and_maintenance_visual_recheck_passed": False,
        },
        "remaining_non_go_facts": [
            "Exact GDEY0154D67-T03 temperature applicability and panel/FPC/controller identity evidence for the supplier one-second LUT.",
            "A separately authorized sparse expression sequence with six distinct frames and focused residue review; no such fast-LUT experiment has run.",
        ],
        "prohibited_shortcuts": [
            "Do not change expression, menu, recording, CEMP, or normal refresh policy during the official White/Black retest.",
            "Do not use TP_INT/PC6 or optional TP_RST/PC10 as e-paper recovery wiring.",
            "Do not promote historical visible-refresh evidence as current acceptance.",
            "Do not load the unaffiliated 0xC7/one-second LUT or invent a waveform from the replacement-FPC observation.",
        ],
        "sources": {
            "product_requirements": rel(PRODUCT_REQUIREMENTS),
            "grain_recovery_research": rel(GRAIN_RESEARCH),
            "official_white_black_recovery": rel(OFFICIAL_RECOVERY),
            "voltage_probe": rel(VOLTAGE_PROBE),
            "voltage_operator_review": rel(VOLTAGE_OPERATOR),
            "normal_restore": rel(NORMAL_RESTORE),
            "staged_recovery_runner": rel(RECOVERY_RUNNER),
            "vendor_source_audit": rel(VENDOR_AUDIT),
            "replacement_display_fpc_evidence": rel(FPC_REPLACEMENT_EVIDENCE),
            "current_white_stage": rel(WHITE_STAGE),
            "current_black_stage": rel(BLACK_STAGE),
            "current_white_digital": rel(WHITE_DIGITAL),
            "current_black_digital": rel(BLACK_DIGITAL),
            "current_white_rail": rel(WHITE_RAIL),
        },
        "wba_impact": (
            "Keep this failure target-local. WBA55/WBA65 reuse portable screen, "
            "expression, touch, and refresh-intent contracts but require their own "
            "panel power/rail implementation and real hardware evidence."
        ),
        "validation_commands": [
            "python .\\tools\\verify_wb55_screen_hardware_recovery_gate.py",
            "python .\\tools\\verify_wb55_screen_hardware_recovery_runner.py",
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
        contract.get("status") == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
        "hardware recovery gate must bind the current official White/Black retest",
        errors,
    )
    require(
        contract.get("claim_scope")
        == "source_bound_official_white_black_and_rail_retest_not_fast_lut_or_dynamic_expression_acceptance",
        "hardware gate claim scope drifted",
        errors,
    )
    criteria = contract.get("acceptance_criteria", {})
    for key in (
        "normal_current_expression_visible",
        "partial_expression_transition_visible",
        "touch_and_maintenance_visual_recheck_passed",
    ):
        require(criteria.get(key) is False, f"{key} must remain false", errors)
    for key in (
        "official_white_solid_and_deterministic",
        "official_black_solid_and_deterministic",
        "current_source_bound_white_machine_trace",
        "current_source_bound_black_machine_trace",
        "positive_and_negative_refresh_rails_established",
    ):
        require(criteria.get(key) is True, f"{key} must be true", errors)
    require(
        len(contract.get("remaining_non_go_facts", [])) == 2,
        "hardware gate must retain two explicit fast-LUT/dynamic non-go facts",
        errors,
    )
    require(
        contract.get("current_fault", {}).get("current_white_black_machine_or_operator_acceptance") is True,
        "current White/Black acceptance linkage missing",
        errors,
    )
    runner = contract.get("recovery_runner", {})
    require(
        runner.get("status") == "PASS_MACHINE_PREFLIGHT",
        "hardware gate must link the staged recovery runner",
        errors,
    )
    require(
        runner.get("stage_order") == ["white", "black", "restorenormal"],
        "hardware recovery stage order drifted",
        errors,
    )
    require(
        runner.get("machine_pass_is_panel_acceptance") is False,
        "machine recovery preflight must not claim panel acceptance",
        errors,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--current-run-root", type=pathlib.Path, default=CURRENT_RUN_ROOT,
                        help="Versioned White/Black stage root; defaults to the retained current-source run.")
    parser.add_argument("--white-rail", type=pathlib.Path, default=WHITE_RAIL,
                        help="Versioned official White rail artifact paired with this run.")
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args(argv)

    configure_current_evidence(args.current_run_root, args.white_rail)
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
    print(f"PASS: WB55 current replacement-FPC official White/Black retest verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
