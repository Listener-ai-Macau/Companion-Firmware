#!/usr/bin/env python3
"""Verify whether panel hardware facts are ready for target driver work."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import init_expression_panel_evidence_record as init_record  # noqa: E402
import verify_expression_panel_hardware_facts as hardware_facts  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-driver-readiness.json")
SCHEMA_ID = "companion.pendant.screen_panel_driver_readiness.v1"
TARGETS = ("WB55", "WBA55", "WBA65")
READY_STATUS = "READY_FOR_DRIVER_IMPLEMENTATION"
BLOCKED_STATUS = "BLOCKED_ON_HARDWARE_FACTS"
INVALID_STATUS = "INVALID_FACTS"

REQUIRED_READY_FIELDS = {
    "panel_identity": [
        "controller_model",
        "panel_module_or_label",
        "panel_variant",
        "resolution_px",
        "datasheet_revision",
        "waveform_lut_source",
    ],
    "target_pin_map": [
        "target_family",
        "spi_instance_or_bus",
        "sck_pin",
        "mosi_pin",
        "cs_pin",
        "dc_pin",
        "rst_pin",
        "busy_pin",
        "power_enable_pin",
        "logic_voltage",
    ],
    "driver_timing": [
        "reset_low_ms",
        "reset_high_ms",
        "busy_timeout_ms",
        "full_refresh_sequence",
        "partial_refresh_policy",
        "sleep_or_powerdown_sequence",
    ],
}

PANEL_GATE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
FACTS_INTAKE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-facts-intake.json"
SESSION_PREFLIGHT = REPO_ROOT / "docs/validation/companion-screen-panel-session-directory-preflight.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs/bringup_steps.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
WBA_RULES = REPO_ROOT / "docs/stm32wba_migration_rules.md"


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


def facts_path_from_session(session_root: pathlib.Path) -> pathlib.Path:
    return session_root / init_record.SESSION_FACTS_FILENAME


def missing_ready_fields(data: dict[str, Any]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for section, fields in REQUIRED_READY_FIELDS.items():
        section_value = data.get(section, {})
        if not isinstance(section_value, dict):
            missing.append({"section": section, "field": "*", "reason": "section_missing_or_not_object"})
            continue
        for field in fields:
            value = section_value.get(field)
            if field not in section_value:
                missing.append({"section": section, "field": field, "reason": "missing"})
            elif hardware_facts.is_placeholder(value):
                missing.append({"section": section, "field": field, "reason": "placeholder"})
    return missing


def known_transport(data: dict[str, Any]) -> dict[str, Any]:
    pin_map = data.get("target_pin_map", {})
    if not isinstance(pin_map, dict):
        return {}
    return {
        "target_family": pin_map.get("target_family"),
        "spi_instance_or_bus": pin_map.get("spi_instance_or_bus"),
        "sck_pin": pin_map.get("sck_pin"),
        "mosi_pin": pin_map.get("mosi_pin"),
        "miso_pin": pin_map.get("miso_pin"),
        "cs_pin": pin_map.get("cs_pin"),
        "cs_label": pin_map.get("cs_label"),
    }


def build_readiness_report(data: dict[str, Any], facts_path: pathlib.Path | None = None) -> dict[str, Any]:
    validation_errors = hardware_facts.validate_facts(data)
    missing_fields = missing_ready_fields(data)
    facts_status = str(data.get("status", ""))
    if validation_errors:
        readiness_status = INVALID_STATUS
    elif facts_status == "READY_FOR_DRIVER_FACTS" and not missing_fields:
        readiness_status = READY_STATUS
    else:
        readiness_status = BLOCKED_STATUS

    target = str(data.get("target", ""))
    return {
        "readiness_status": readiness_status,
        "facts_status": facts_status,
        "target": target,
        "facts_path": rel(facts_path) if facts_path is not None else None,
        "known_transport": known_transport(data),
        "missing_ready_fields": missing_fields,
        "missing_ready_field_count": len(missing_fields),
        "validation_errors": validation_errors,
        "driver_entrypoint": "app/companion_pendant/epaper/panel_target_stm32wb.c"
        if target == "WB55"
        else "app/companion_pendant/epaper/panel_target_stm32wba.c",
        "next_action": (
            "Implement target panel refresh callback and collect real BLE, diagnostics, and visual evidence."
            if readiness_status == READY_STATUS
            else "Fill panel controller, DC/RST/BUSY, power, voltage, reset/BUSY timing, and refresh sequence facts."
        ),
        "real_refresh_claimed": False,
        "panel_gate_must_remain": "DEFERRED_HARDWARE",
    }


def build_fixture() -> dict[str, Any]:
    draft = init_record.build_hardware_facts_draft("WB55")
    ready = hardware_facts.build_ready_self_test_facts("WB55")
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Reports whether a target panel facts file is ready for driver implementation "
            "without claiming a real e-paper refresh."
        ),
        "sources": {
            "readiness_tool": "tools/verify_expression_panel_driver_readiness.py",
            "facts_intake_tool": "tools/verify_expression_panel_hardware_facts.py",
            "facts_intake_fixture": rel(FACTS_INTAKE),
            "panel_hardware_gate": rel(PANEL_GATE),
            "panel_session_directory_preflight": rel(SESSION_PREFLIGHT),
            "screen_doc": rel(SCREEN_DOC),
            "bringup_doc": rel(BRINGUP_DOC),
            "epaper_readme": rel(EPAPER_README),
            "wba_rules": rel(WBA_RULES),
        },
        "target_coverage": list(TARGETS),
        "current_wb55_draft_readiness": build_readiness_report(draft),
        "ready_self_test_readiness": build_readiness_report(ready),
        "real_refresh_guard": {
            "does_not_claim_real_refresh": True,
            "panel_gate_must_remain": "DEFERRED_HARDWARE",
            "requires_final_panel_evidence_record": True,
        },
        "self_test_cases": [
            "draft_facts_report_blocked_with_missing_fields",
            "ready_facts_report_ready_without_missing_fields",
            "invalid_ready_facts_report_invalid",
            "session_facts_path_report_supported",
            "require_ready_requires_target_facts_source",
            "require_ready_fails_for_draft",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_driver_readiness.py",
            "python .\\tools\\verify_expression_panel_driver_readiness.py --self-test",
            "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
            "python .\\tools\\verify_expression_panel_gate.py",
        ],
    }


def validate_report(report: dict[str, Any], errors: list[str]) -> None:
    require(report.get("readiness_status") in {READY_STATUS, BLOCKED_STATUS, INVALID_STATUS}, "invalid readiness status", errors)
    require(report.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "readiness must preserve deferred panel gate", errors)
    require(report.get("real_refresh_claimed") is False, "readiness must not claim real refresh", errors)
    if report.get("readiness_status") == READY_STATUS:
        require(report.get("missing_ready_field_count") == 0, "ready report must have no missing fields", errors)
        require(not report.get("validation_errors"), "ready report must have no validation errors", errors)
    if report.get("readiness_status") == BLOCKED_STATUS:
        require(report.get("missing_ready_field_count", 0) > 0, "blocked report must list missing fields", errors)
    if report.get("readiness_status") == INVALID_STATUS:
        require(report.get("validation_errors"), "invalid report must include validation errors", errors)


def run_self_test() -> list[str]:
    errors: list[str] = []
    draft = init_record.build_hardware_facts_draft("WB55")
    draft_report = build_readiness_report(draft)
    validate_report(draft_report, errors)
    require(draft_report.get("readiness_status") == BLOCKED_STATUS, "draft facts should be blocked", errors)
    missing = {(item.get("section"), item.get("field")) for item in draft_report.get("missing_ready_fields", [])}
    for field in [
        ("panel_identity", "controller_model"),
        ("target_pin_map", "dc_pin"),
        ("target_pin_map", "rst_pin"),
        ("target_pin_map", "busy_pin"),
        ("driver_timing", "reset_low_ms"),
    ]:
        require(field in missing, f"draft readiness missing expected blocker {field}", errors)
    transport = draft_report.get("known_transport", {})
    require(transport.get("spi_instance_or_bus") == "SPI2", "draft readiness lost WB55 SPI2 transport", errors)
    require(transport.get("sck_pin") == "PA9", "draft readiness lost WB55 SCK pin", errors)

    ready = hardware_facts.build_ready_self_test_facts("WB55")
    ready_report = build_readiness_report(ready)
    validate_report(ready_report, errors)
    require(ready_report.get("readiness_status") == READY_STATUS, "ready facts should be ready", errors)

    invalid = json.loads(json.dumps(ready))
    invalid["panel_identity"]["controller_model"] = "TODO_CONTROLLER_MODEL"
    invalid_report = build_readiness_report(invalid)
    validate_report(invalid_report, errors)
    require(invalid_report.get("readiness_status") == INVALID_STATUS, "invalid ready facts should be invalid", errors)
    return errors


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, f"fixture schema_id must be {SCHEMA_ID}", errors)
    require(data.get("status") == "PASS", "driver readiness fixture must be PASS", errors)
    for source in data.get("sources", {}).values():
        if isinstance(source, str):
            require((REPO_ROOT / source).exists(), f"readiness source missing {source}", errors)
    require(data.get("target_coverage") == list(TARGETS), "driver readiness target coverage drifted", errors)
    draft = data.get("current_wb55_draft_readiness", {})
    ready = data.get("ready_self_test_readiness", {})
    validate_report(draft, errors)
    validate_report(ready, errors)
    require(draft.get("readiness_status") == BLOCKED_STATUS, "fixture draft readiness must be blocked", errors)
    require(ready.get("readiness_status") == READY_STATUS, "fixture ready self-test must be ready", errors)
    guard = data.get("real_refresh_guard", {})
    require(guard.get("does_not_claim_real_refresh") is True, "fixture must not claim real refresh", errors)
    require(guard.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "fixture must preserve deferred gate", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (BRINGUP_DOC, "bringup doc"), (EPAPER_README, "epaper README"), (WBA_RULES, "WBA rules")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "panel_driver_readiness_report",
            "companion-screen-panel-driver-readiness.json",
            "verify_expression_panel_driver_readiness.py",
            BLOCKED_STATUS,
            READY_STATUS,
        ]:
            require(token in text, f"{name} missing panel driver readiness anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_driver_readiness_report"]
        require(len(items) == 1, "acceptance index must contain one panel_driver_readiness_report item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_driver_readiness_report item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel_driver_readiness_report item must link fixture", errors)
            require(
                "python .\\tools\\verify_expression_panel_driver_readiness.py --self-test" in item.get("validation_commands", []),
                "panel_driver_readiness_report item must run self-test",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel driver readiness fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def write_report(path: pathlib.Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic driver-readiness fixture.")
    parser.add_argument("--self-test", action="store_true", help="Run draft/ready/invalid readiness checks.")
    parser.add_argument("--facts", type=pathlib.Path, default=None, help="Panel hardware facts JSON to inspect.")
    parser.add_argument("--session-root", type=pathlib.Path, default=None, help="Session root containing panel-hardware-facts.todo.json.")
    parser.add_argument("--output", type=pathlib.Path, default=None, help="Write a readiness report for --facts/--session-root.")
    parser.add_argument("--require-ready", action="store_true", help="Fail unless facts are READY_FOR_DRIVER_IMPLEMENTATION.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    if args.self_test:
        errors.extend(run_self_test())

    facts_path: pathlib.Path | None = None
    if args.session_root is not None:
        root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root
        facts_path = facts_path_from_session(root)
    if args.facts is not None:
        facts_path = args.facts if args.facts.is_absolute() else REPO_ROOT / args.facts

    report: dict[str, Any] | None = None
    if args.require_ready and facts_path is None:
        errors.append("--require-ready requires --facts or --session-root so a concrete panel facts file is checked")
    if facts_path is not None:
        if not facts_path.exists():
            errors.append(f"facts file missing: {rel(facts_path)}")
        else:
            report = build_readiness_report(load_json(facts_path), facts_path)
            validate_report(report, errors)
            if args.output is not None and not errors:
                output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output
                write_report(output_path, report)
            if report.get("readiness_status") == INVALID_STATUS:
                errors.extend(str(error) for error in report.get("validation_errors", []))
            if args.require_ready and report.get("readiness_status") != READY_STATUS:
                errors.append(
                    f"driver readiness is {report.get('readiness_status')}; fill hardware facts before implementing the panel driver"
                )

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_project_links(rel(fixture_path), errors)
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel driver readiness checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    if report is not None:
        print(
            "PASS: Companion panel driver readiness "
            f"{report['readiness_status']} missing={report['missing_ready_field_count']} -> {rel(facts_path)}"
        )
    else:
        print(f"PASS: Companion panel driver readiness verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
