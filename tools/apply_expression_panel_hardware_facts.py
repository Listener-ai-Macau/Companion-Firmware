#!/usr/bin/env python3
"""Apply READY_FOR_DRIVER_FACTS into a draft real-panel evidence record."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import init_expression_panel_evidence_record as init_record  # noqa: E402
import verify_expression_panel_evidence_record as evidence_validator  # noqa: E402
import verify_expression_panel_hardware_facts as facts_intake  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-hardware-facts-bridge.json")
SCHEMA_ID = "companion.pendant.screen_panel_hardware_facts_bridge.v1"
RECORD_SCHEMA_ID = init_record.RECORD_SCHEMA_ID
FACTS_SCHEMA_ID = facts_intake.FACTS_SCHEMA_ID

ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
PANEL_GATE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
FACTS_INTAKE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-facts-intake.json"
PANEL_EVIDENCE_VALIDATOR = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-record-validator.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs/bringup_steps.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_facts_to_record(record: dict[str, Any], facts: dict[str, Any]) -> list[str]:
    errors = facts_intake.validate_facts(facts)
    if errors:
        return [f"hardware facts invalid: {error}" for error in errors]
    require(facts.get("status") == "READY_FOR_DRIVER_FACTS", "hardware facts must be READY_FOR_DRIVER_FACTS before applying to evidence record", errors)
    require(record.get("schema_id") == RECORD_SCHEMA_ID, f"record schema_id must be {RECORD_SCHEMA_ID}", errors)
    require(record.get("status") == "DRAFT_UNFILLED", "record must stay DRAFT_UNFILLED while importing hardware facts", errors)
    require(record.get("claim_scope") == "real_panel_refresh", "record claim_scope must be real_panel_refresh", errors)

    target = facts.get("target")
    record_target = record.get("target_pin_map", {}).get("target_family")
    require(target == record_target, f"facts target {target} must match record target {record_target}", errors)
    if errors:
        return errors

    identity = record.setdefault("panel_identity", {})
    facts_identity = facts.get("panel_identity", {})
    for key in [
        "controller_model",
        "panel_module_or_label",
        "panel_variant",
        "resolution_px",
        "datasheet_revision",
        "waveform_lut_source",
    ]:
        if key in facts_identity:
            identity[key] = facts_identity[key]

    pin_map = record.setdefault("target_pin_map", {})
    facts_pin_map = facts.get("target_pin_map", {})
    for key, value in facts_pin_map.items():
        pin_map[key] = value

    timing = record.setdefault("driver_timing", {})
    facts_timing = facts.get("driver_timing", {})
    for key in [
        "reset_low_ms",
        "reset_high_ms",
        "busy_timeout_ms",
        "full_refresh_sequence",
        "partial_refresh_policy",
        "sleep_or_powerdown_sequence",
    ]:
        if key in facts_timing:
            timing[key] = facts_timing[key]

    instructions = record.setdefault("_instructions", [])
    note = (
        "Hardware facts imported from READY_FOR_DRIVER_FACTS; this record must remain "
        "DRAFT_UNFILLED until BLE, diagnostics, visual, and portability evidence are filled."
    )
    if isinstance(instructions, list) and note not in instructions:
        instructions.append(note)
    record["status"] = "DRAFT_UNFILLED"
    return []


def validate_applied_record(record: dict[str, Any], record_path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    require(record.get("status") == "DRAFT_UNFILLED", "applied record must remain DRAFT_UNFILLED", errors)
    for section in ["panel_identity", "target_pin_map", "driver_timing"]:
        value = record.get(section, {})
        require(isinstance(value, dict), f"{section} must be an object", errors)
        if isinstance(value, dict):
            for field_value in value.values():
                require(evidence_validator.non_placeholder(field_value), f"{section} still contains placeholder after facts import", errors)
    final_errors = evidence_validator.validate_record(record, record_path)
    require(final_errors, "applied hardware-facts record unexpectedly passed final real-panel validator", errors)
    require(
        any("status must be PASS" in error for error in final_errors),
        "final validator must still reject the draft status after facts import",
        errors,
    )
    for forbidden in [
        "evidence record has placeholder panel_identity.",
        "evidence record has placeholder target_pin_map.",
        "evidence record has placeholder driver_timing.",
    ]:
        require(
            not any(error.startswith(forbidden) for error in final_errors),
            f"final validator still reports imported hardware fact placeholder: {forbidden}",
            errors,
        )
    return errors


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Bridges READY_FOR_DRIVER_FACTS into a draft panel evidence record so "
            "controller/pin/timing facts are synchronized before implementing the target driver, "
            "without claiming real refresh."
        ),
        "sources": {
            "bridge_tool": "tools/apply_expression_panel_hardware_facts.py",
            "facts_intake_tool": "tools/verify_expression_panel_hardware_facts.py",
            "facts_intake_fixture": rel(FACTS_INTAKE),
            "evidence_validator": "tools/verify_expression_panel_evidence_record.py",
            "evidence_validator_fixture": rel(PANEL_EVIDENCE_VALIDATOR),
            "panel_hardware_gate": rel(PANEL_GATE),
            "screen_doc": rel(SCREEN_DOC),
            "bringup_doc": rel(BRINGUP_DOC),
            "epaper_readme": rel(EPAPER_README),
        },
        "input_schema": FACTS_SCHEMA_ID,
        "output_schema": RECORD_SCHEMA_ID,
        "accepted_input_status": "READY_FOR_DRIVER_FACTS",
        "output_status_after_apply": "DRAFT_UNFILLED",
        "imported_sections": [
            "panel_identity",
            "target_pin_map",
            "driver_timing",
        ],
        "left_unfilled_until_real_bench": [
            "host_observability",
            "visual_evidence",
            "portability_notes",
        ],
        "real_refresh_guard": {
            "does_not_claim_real_refresh": True,
            "final_validator_must_still_fail": True,
            "panel_gate_must_remain": "DEFERRED_HARDWARE",
        },
        "self_test_cases": [
            "ready_facts_apply_to_draft_record",
            "draft_facts_are_rejected",
            "target_mismatch_is_rejected",
            "applied_record_still_fails_final_validator",
            "imported_sections_have_no_placeholders",
        ],
        "validation_commands": [
            "python .\\tools\\apply_expression_panel_hardware_facts.py --self-test",
            "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
            "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
            "python .\\tools\\verify_expression_panel_gate.py",
        ],
    }


def build_session_record(root: pathlib.Path, target: str = "WB55") -> pathlib.Path:
    record = init_record.build_record(target, "idle", "2.13in")
    init_record.apply_session_paths(record)
    record_path = root / init_record.SESSION_RECORD_FILENAME
    init_record.write_session_scaffold(root, record_path, record, target, "idle", "2.13in")
    return record_path


def run_self_test() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        record_path = build_session_record(root / "ready")
        record = load_json(record_path)
        facts = facts_intake.build_ready_self_test_facts("WB55")
        errors.extend(apply_facts_to_record(record, facts))
        errors.extend(validate_applied_record(record, record_path))
        require(record["panel_identity"]["controller_model"] == "UC8151D", "ready facts did not import controller model", errors)
        require(record["target_pin_map"]["dc_pin"] == "PB0", "ready facts did not import DC pin", errors)
        require(record["driver_timing"]["busy_timeout_ms"] == 5000, "ready facts did not import busy timeout", errors)

        out_path = root / "ready-applied.json"
        write_json(out_path, record)
        require(load_json(out_path) == record, "applied record write/read drifted", errors)

        draft_record_path = build_session_record(root / "draft")
        draft_record = load_json(draft_record_path)
        draft_errors = apply_facts_to_record(draft_record, facts_intake.build_draft_facts("WB55"))
        require(draft_errors, "draft facts self-test did not fail bridge apply", errors)

        mismatch_record_path = build_session_record(root / "mismatch")
        mismatch_record = load_json(mismatch_record_path)
        mismatch_facts = facts_intake.build_ready_self_test_facts("WB55")
        mismatch_facts["target"] = "WBA55"
        mismatch_facts["target_pin_map"]["target_family"] = "WBA55"
        mismatch_errors = apply_facts_to_record(mismatch_record, mismatch_facts)
        require(mismatch_errors, "target mismatch self-test did not fail bridge apply", errors)
    return errors


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected hardware facts bridge schema", errors)
    require(data.get("status") == "PASS", "hardware facts bridge fixture must be PASS", errors)
    sources = data.get("sources", {})
    for key in ["bridge_tool", "facts_intake_tool", "facts_intake_fixture", "evidence_validator", "evidence_validator_fixture", "panel_hardware_gate"]:
        source = sources.get(key)
        require(isinstance(source, str) and (REPO_ROOT / source).exists(), f"fixture source missing {key}", errors)
    require(data.get("input_schema") == FACTS_SCHEMA_ID, "fixture input schema drifted", errors)
    require(data.get("output_schema") == RECORD_SCHEMA_ID, "fixture output schema drifted", errors)
    require(data.get("accepted_input_status") == "READY_FOR_DRIVER_FACTS", "bridge must require READY_FOR_DRIVER_FACTS", errors)
    require(data.get("output_status_after_apply") == "DRAFT_UNFILLED", "bridge output status must stay DRAFT_UNFILLED", errors)
    for section in ["panel_identity", "target_pin_map", "driver_timing"]:
        require(section in data.get("imported_sections", []), f"fixture missing imported section {section}", errors)
    guard = data.get("real_refresh_guard", {})
    require(guard.get("does_not_claim_real_refresh") is True, "bridge must not claim real refresh", errors)
    require(guard.get("final_validator_must_still_fail") is True, "bridge must require final validator rejection", errors)
    require(guard.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "bridge must preserve deferred gate", errors)
    for case in [
        "ready_facts_apply_to_draft_record",
        "draft_facts_are_rejected",
        "target_mismatch_is_rejected",
        "applied_record_still_fails_final_validator",
        "imported_sections_have_no_placeholders",
    ]:
        require(case in data.get("self_test_cases", []), f"fixture missing self-test case {case}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (BRINGUP_DOC, "bringup doc"), (EPAPER_README, "epaper README")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "panel_hardware_facts_bridge",
            "apply_expression_panel_hardware_facts.py",
            "READY_FOR_DRIVER_FACTS",
            "DRAFT_UNFILLED",
            "does not claim real refresh",
        ]:
            require(token in text, f"{name} missing hardware facts bridge anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_hardware_facts_bridge"]
        require(len(items) == 1, "acceptance index must contain one panel_hardware_facts_bridge item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_hardware_facts_bridge item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel_hardware_facts_bridge item must link fixture", errors)
            require(
                "python .\\tools\\apply_expression_panel_hardware_facts.py --self-test" in item.get("validation_commands", []),
                "panel_hardware_facts_bridge item must run self-test",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing hardware facts bridge fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic bridge fixture.")
    parser.add_argument("--self-test", action="store_true", help="Run bridge positive and negative checks.")
    parser.add_argument("--facts", type=pathlib.Path, default=None, help="READY_FOR_DRIVER_FACTS JSON.")
    parser.add_argument("--record", type=pathlib.Path, default=None, help="Draft panel-evidence-record JSON.")
    parser.add_argument("--output", type=pathlib.Path, default=None, help="Output record path; defaults to --record when --write is used.")
    parser.add_argument("--write", action="store_true", help="Write the applied draft evidence record.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    if args.self_test:
        errors.extend(run_self_test())

    applied_path: pathlib.Path | None = None
    if args.facts is not None or args.record is not None:
        require(args.facts is not None and args.record is not None, "--facts and --record must be provided together", errors)
        if args.facts is not None and args.record is not None:
            facts_path = args.facts if args.facts.is_absolute() else REPO_ROOT / args.facts
            record_path = args.record if args.record.is_absolute() else REPO_ROOT / args.record
            require(facts_path.exists(), f"missing facts file: {rel(facts_path)}", errors)
            require(record_path.exists(), f"missing evidence record: {rel(record_path)}", errors)
            if facts_path.exists() and record_path.exists():
                record = load_json(record_path)
                errors.extend(apply_facts_to_record(record, load_json(facts_path)))
                errors.extend(validate_applied_record(record, record_path))
                if args.write and not errors:
                    applied_path = args.output if args.output is not None else record_path
                    applied_path = applied_path if applied_path.is_absolute() else REPO_ROOT / applied_path
                    write_json(applied_path, record)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel hardware facts bridge checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    if applied_path is not None:
        print(f"PASS: Companion panel hardware facts bridge wrote -> {rel(applied_path)}")
    else:
        print(f"PASS: Companion panel hardware facts bridge verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
