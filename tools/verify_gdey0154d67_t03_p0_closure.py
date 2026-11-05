#!/usr/bin/env python3
"""Close the source-bound GDEY0154D67-T03 official full-refresh P0 evidence."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-p0-closure-20260720.json"
VENDOR_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
PANEL_CORRELATION = ROOT / "docs/validation/companion-gdey0154d67-t03-panel-marking-correlation-20260720.json"
FPC_EVIDENCE = ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
WHITE_RAIL = ROOT / "docs/validation/companion-screen-wb55-white-rail-measurement-current-source-20260720.json"
RUNNER = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-runner.json"
GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
CURRENT_RUN_ROOT = ROOT / ".cache/validation/wb55-screen-recovery-current-source-20260720"
WHITE_STAGE = CURRENT_RUN_ROOT / "white/stage-run.json"
BLACK_STAGE = CURRENT_RUN_ROOT / "black/stage-run.json"
WHITE_DIGITAL = CURRENT_RUN_ROOT / "white/official-full-result.json"
BLACK_DIGITAL = CURRENT_RUN_ROOT / "black/official-full-result.json"
SCHEMA_ID = "companion.gdey0154d67_t03.p0_closure.v1"


def resolve_repo_path(path: pathlib.Path) -> pathlib.Path:
    return path if path.is_absolute() else ROOT / path


def configure_current_evidence(current_run_root: pathlib.Path, white_rail: pathlib.Path,
                               recovery_gate: pathlib.Path) -> None:
    """Select one immutable current-source physical run for this closure report."""
    global CURRENT_RUN_ROOT, WHITE_STAGE, BLACK_STAGE, WHITE_DIGITAL, BLACK_DIGITAL, WHITE_RAIL, GATE
    CURRENT_RUN_ROOT = resolve_repo_path(current_run_root)
    WHITE_STAGE = CURRENT_RUN_ROOT / "white/stage-run.json"
    BLACK_STAGE = CURRENT_RUN_ROOT / "black/stage-run.json"
    WHITE_DIGITAL = CURRENT_RUN_ROOT / "white/official-full-result.json"
    BLACK_DIGITAL = CURRENT_RUN_ROOT / "black/official-full-result.json"
    WHITE_RAIL = resolve_repo_path(white_rail)
    GATE = resolve_repo_path(recovery_gate)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_stage(
    label: str,
    stage: dict[str, Any],
    digital: dict[str, Any],
    expected_pattern: str,
    expected_target_sha256: str,
    expected_vendor_epaper_c_sha256: str,
    errors: list[str],
) -> None:
    require(stage.get("stage") == label, f"{label} stage identity drifted", errors)
    require(
        stage.get("status") == "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS",
        f"{label} stage status is not source-bound visual PASS with normal restore",
        errors,
    )
    require(stage.get("normal_firmware_restored") is True, f"{label} did not restore normal firmware", errors)
    review = stage.get("operator_review", {})
    require(review.get("selected") == "通过", f"{label} operator review did not pass", errors)
    require(isinstance(review.get("note"), str) and bool(review["note"].strip()), f"{label} operator note is empty", errors)
    require(
        isinstance(review.get("note"), str) and "残留" in review["note"],
        f"{label} operator note does not record the required residue observation",
        errors,
    )
    results = stage.get("results", [])
    require(len(results) >= 4 and all(result.get("status") == "PASS" for result in results), f"{label} stage has a non-PASS machine step", errors)
    require(digital.get("status") == "PASS_MACHINE_DIGITAL_ONLY", f"{label} digital parser did not pass", errors)
    require(digital.get("pattern") == expected_pattern, f"{label} digital pattern drifted", errors)
    for key in (
        "full_window_5000_bytes",
        "official_current_plane_only",
        "activation_0x20_sent",
        "soft_reset_busy_asserted",
        "busy_returned_ready",
        "refresh_completed",
        "refresh_elapsed_recorded_within_5000_ms",
        "source_audit_bound",
    ):
        require(digital.get("checks", {}).get(key) is True, f"{label} digital check missing: {key}", errors)
    source_audit = digital.get("source_audit", {})
    require(
        source_audit.get("current_ssd1681_target_sha256") == expected_target_sha256,
        f"{label} digital trace is bound to a stale SSD1681 target source hash",
        errors,
    )
    require(
        source_audit.get("vendor_epaper_c_sha256") == expected_vendor_epaper_c_sha256,
        f"{label} digital trace vendor EPAPER.c source hash drifted",
        errors,
    )


def build_report() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    paths = (
        VENDOR_AUDIT,
        PANEL_CORRELATION,
        FPC_EVIDENCE,
        WHITE_RAIL,
        RUNNER,
        GATE,
        WHITE_STAGE,
        BLACK_STAGE,
        WHITE_DIGITAL,
        BLACK_DIGITAL,
    )
    for path in paths:
        require(path.is_file(), f"missing source {rel(path)}", errors)
    if WHITE_STAGE.is_file():
        try:
            white_stage_probe = load(WHITE_STAGE)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(f"current White stage report is unreadable: {error}")
        else:
            require(
                white_stage_probe.get("status")
                == "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS",
                "current White stage is not a completed source-bound visual record; rerun White rather than treating a DRY-RUN as physical evidence",
                errors,
            )
    if errors:
        return {"schema_id": SCHEMA_ID, "status": "FAIL", "failures": errors}, errors

    vendor = load(VENDOR_AUDIT)
    correlation = load(PANEL_CORRELATION)
    fpc = load(FPC_EVIDENCE)
    rail = load(WHITE_RAIL)
    runner = load(RUNNER)
    gate = load(GATE)
    white_stage = load(WHITE_STAGE)
    black_stage = load(BLACK_STAGE)
    white_digital = load(WHITE_DIGITAL)
    black_digital = load(BLACK_DIGITAL)

    manifest = vendor.get("source_manifest", {})
    critical_sources = manifest.get("critical_sources", {})
    current_target = critical_sources.get("current_ssd1681_target", {})
    vendor_epaper_c = critical_sources.get("epaper_c", {})
    expected_target_sha256 = current_target.get("sha256")
    expected_vendor_epaper_c_sha256 = vendor_epaper_c.get("sha256")
    lut = manifest.get("lut_data", {})
    require(vendor.get("machine_status") == "PASS_AUDIT_COMPLETE", "vendor source audit did not pass", errors)
    require(vendor.get("promotion_status") == "NO_GO_PANEL_IDENTITY_UNPROVEN", "vendor LUT must remain identity NO_GO", errors)
    require(vendor.get("supplier_input_is_read_only") is True, "vendor input is not marked read-only", errors)
    require(isinstance(expected_target_sha256, str) and bool(expected_target_sha256), "current SSD1681 target source hash is missing", errors)
    require(isinstance(expected_vendor_epaper_c_sha256, str) and bool(expected_vendor_epaper_c_sha256), "vendor EPAPER.c source hash is missing", errors)
    require(manifest.get("file_count") == 124, "vendor manifest file count drifted", errors)
    require(lut.get("declared_bytes") == 159 and lut.get("literal_count") == 159, "vendor LUT must contain exactly 159 bytes", errors)
    require(lut.get("load_command") == "0x32" and lut.get("load_payload_bytes") == 153, "vendor LUT load must be 0x32 with 153 bytes", errors)
    require(
        lut.get("tail_bindings") == {"0x03": ["0x17"], "0x04": ["0x41", "0xA8", "0x32"], "0x2C": ["0x58"], "0x3F": ["0x22"]},
        "vendor LUT tail binding drifted",
        errors,
    )
    command = vendor.get("command_evidence", {})
    require(command.get("full_plane_command") == "0x24" and command.get("full_plane_bytes") == 5000, "vendor full plane contract drifted", errors)
    require(command.get("full_update_control") == "0xF7" and command.get("lut_fast_update_control") == "0xC7", "vendor control words drifted", errors)
    require(command.get("master_activation") == "0x20", "vendor activation command drifted", errors)
    require(command.get("production_lut_reference_absent") is True, "production must not reference the vendor LUT", errors)
    require(vendor.get("production_off_diagnostic", {}).get("allowed") is False, "production-off LUT diagnostic must stay forbidden", errors)

    require(correlation.get("status") == "PASS_OWNER_PHOTO_LABEL_OBSERVED_UNARCHIVED", "panel marking correlation status drifted", errors)
    require(correlation.get("promotion_status") == "NO_GO_PANEL_IDENTITY_UNPROVEN", "panel correlation must not promote the LUT", errors)
    require(
        any("replacement-display-FPC" in item for item in correlation.get("remaining_required_evidence", [])),
        "panel correlation must retain the current replacement-FPC physical prerequisite wording",
        errors,
    )
    require(fpc.get("status") == "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE", "replacement FPC evidence did not pass", errors)
    require(fpc.get("authorization", {}).get("allowed_stage") == "White", "replacement FPC evidence must authorize White only", errors)

    require(rail.get("status") == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE", "White rail artifact did not pass", errors)
    require(
        rail.get("minimum_cycles") == 30
        and rail.get("accepted_reset_bounded_cycles") == list(range(1, 31)),
        "White rail artifact does not bind the reset-bounded 30 complete cycles",
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
        require(rail.get("checks", {}).get(key) is True, f"White rail check missing: {key}", errors)
    measure = rail.get("measurement", {})
    require(measure.get("prevgh1_max_v", 0) > 3.3 and measure.get("prevgl1_min_v", 0) < 0, "White rail polarity is not established", errors)
    rail_source_audit = rail.get("source_audit", {})
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

    require(runner.get("status") == "PASS_MACHINE_PREFLIGHT", "recovery runner preflight did not pass", errors)
    guards = runner.get("prerequisite_guard_contract", {})
    for key in (
        "replacement_display_fpc_schema_guard_present",
        "white_execute_requires_replacement_display_fpc",
        "black_execute_requires_white_rail",
        "white_rail_schema_guard_present",
        "vendor_source_audit_guard_present",
        "checkonly_preserves_completed_evidence",
    ):
        require(guards.get(key) is True, f"runner guard missing: {key}", errors)
    hardware_lock = runner.get("hardware_lock_contract", {})
    for key in (
        "helper_exists",
        "runner_imports_helper",
        "runner_acquires_before_steps",
        "child_grant_is_recorded",
        "legacy_boolean_is_not_authority",
        "flash_child_imports_and_uses_helper",
        "serial_child_imports_and_uses_helper",
        "runner_does_not_forward_legacy_boolean_to_serial_child",
        "mutex_spans_step_sequence_and_restore",
        "host_mutex_test_passed",
    ):
        require(hardware_lock.get(key) is True, f"runner hardware lock contract missing: {key}", errors)
    require(runner.get("execute_missing_replacement_display_fpc_negative", {}).get("refused_before_hardware") is True, "runner must fail closed before hardware when replacement display-FPC evidence is absent", errors)
    require(runner.get("execute_with_lock_missing_replacement_display_fpc_negative", {}).get("refused_before_hardware") is True, "White must fail closed without replacement FPC evidence", errors)
    require(runner.get("black_without_white_rail_negative", {}).get("refused_before_hardware") is True, "Black must fail closed without White rail evidence", errors)

    validate_stage(
        "White",
        white_stage,
        white_digital,
        "white",
        expected_target_sha256,
        expected_vendor_epaper_c_sha256,
        errors,
    )
    validate_stage(
        "Black",
        black_stage,
        black_digital,
        "black",
        expected_target_sha256,
        expected_vendor_epaper_c_sha256,
        errors,
    )
    require(gate.get("status") == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST", "final current-FPC recovery gate did not pass", errors)
    require(
        gate.get("claim_scope") == "source_bound_official_white_black_and_rail_retest_not_fast_lut_or_dynamic_expression_acceptance",
        "final gate claim scope drifted",
        errors,
    )

    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO" if not errors else "FAIL",
        "claim_scope": "official_full_refresh_p0_closed_without_vendor_lut_promotion_or_dynamic_expression_claim",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + replacement display FPC + GDEY0154D67-T03",
        "official_full_retest": {
            "white": {"stage": rel(WHITE_STAGE), "digital": rel(WHITE_DIGITAL), "operator_note": white_stage.get("operator_review", {}).get("note")},
            "black": {"stage": rel(BLACK_STAGE), "digital": rel(BLACK_DIGITAL), "operator_note": black_stage.get("operator_review", {}).get("note")},
            "white_rail": rel(WHITE_RAIL),
            "final_gate": rel(GATE),
        },
        "human_observations": {
            "white": white_stage.get("operator_review", {}).get("note"),
            "black": black_stage.get("operator_review", {}).get("note"),
            "residue_observation": {
                "white_note_mentions_residue": "残留" in white_stage.get("operator_review", {}).get("note", ""),
                "black_note_mentions_residue": "残留" in black_stage.get("operator_review", {}).get("note", ""),
                "conclusion": "Both canonical White and Black reviews explicitly report no old-image residue.",
            },
        },
        "vendor_lut_disposition": {
            "source_audit": rel(VENDOR_AUDIT),
            "panel_correlation": rel(PANEL_CORRELATION),
            "promotion_status": vendor.get("promotion_status"),
            "production_off_diagnostic_allowed": vendor.get("production_off_diagnostic", {}).get("allowed"),
            "remaining_evidence": correlation.get("remaining_required_evidence", []),
        },
        "enforced_invariants": {
            "official_white_black_are_0x24_one_5000_byte_plane_f7_0x20_busy": not errors,
            "white_requires_replacement_display_fpc_evidence": guards.get("white_execute_requires_replacement_display_fpc"),
            "black_requires_pass_white_rail": guards.get("black_execute_requires_white_rail"),
            "vendor_lut_absent_from_production": command.get("production_lut_reference_absent"),
            "vendor_lut_is_not_cwf1": vendor.get("identity_evidence", {}).get("temperature_banded_cwf1_table_is_documented") is False,
        },
        "remaining_no_go": [
            "No exact Good Display T03 identity binding from the supplied one-second source tree.",
            "No Good Display temperature applicability table for the one-second LUT.",
            "No production-off fast-LUT diagnostic or production refresh-policy change was authorized or run.",
        ],
        "failures": errors,
    }
    return report, errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    parser.add_argument("--current-run-root", type=pathlib.Path, default=CURRENT_RUN_ROOT,
                        help="Versioned White/Black stage root; defaults to the retained current-source run.")
    parser.add_argument("--white-rail", type=pathlib.Path, default=WHITE_RAIL,
                        help="Versioned official White rail artifact paired with this run.")
    parser.add_argument("--recovery-gate", type=pathlib.Path, default=GATE,
                        help="Versioned recovery-gate artifact paired with this run.")
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    configure_current_evidence(args.current_run_root, args.white_rail, args.recovery_gate)
    report, errors = build_report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        print(f"FAIL: GDEY0154D67-T03 P0 closure -> {rel(output)}", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: GDEY0154D67-T03 P0 closure -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
