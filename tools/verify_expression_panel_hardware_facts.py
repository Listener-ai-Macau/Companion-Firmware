#!/usr/bin/env python3
"""Create and verify real-panel hardware fact intake files."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import init_expression_panel_evidence_record as init_record  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-hardware-facts-intake.json")
FACTS_FILENAME = "panel-hardware-facts.todo.json"
SCHEMA_ID = "companion.pendant.screen_panel_hardware_facts_intake.v1"
FACTS_SCHEMA_ID = "companion.pendant.screen_panel_hardware_facts.v1"
TARGETS = ("WB55", "WBA55", "WBA65")

PANEL_GATE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
PANEL_EVIDENCE_TEMPLATE = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-template.json"
PANEL_SESSION_PREFLIGHT = REPO_ROOT / "docs/validation/companion-screen-panel-session-directory-preflight.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs/bringup_steps.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"

PIN_RE = re.compile(r"^P[A-K][0-9]{1,2}$")
PLACEHOLDER_RE = re.compile(r"(?:^|[^a-z0-9])(?:todo|tbd|unknown|null)(?:[^a-z0-9]|$)", re.IGNORECASE)


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


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip()
        return text == "" or PLACEHOLDER_RE.search(text) is not None
    if isinstance(value, (list, tuple)):
        return not value or any(is_placeholder(item) for item in value)
    if isinstance(value, dict):
        return not value or any(is_placeholder(item) for item in value.values())
    return False


def valid_pin_or_not_present(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return text == "not_present" or PIN_RE.match(text) is not None


def build_draft_facts(target: str, expression: str = "idle", variant: str = "2.13in") -> dict[str, Any]:
    return init_record.build_hardware_facts_draft(target, expression, variant)


def build_ready_self_test_facts(target: str = "WB55") -> dict[str, Any]:
    data = build_draft_facts(target)
    data["status"] = "READY_FOR_DRIVER_FACTS"
    data["panel_identity"].update(
        {
            "controller_model": "UC8151D",
            "panel_module_or_label": "self-test-2.13in-module",
            "datasheet_revision": "rev-a",
            "waveform_lut_source": "controller OTP",
        }
    )
    data["target_pin_map"].update(
        {
            "dc_pin": "PB0",
            "rst_pin": "PB1",
            "busy_pin": "PB2",
            "power_enable_pin": "not_present",
            "logic_voltage": "3.3V",
        }
    )
    data["driver_timing"].update(
        {
            "reset_low_ms": 10,
            "reset_high_ms": 10,
            "busy_timeout_ms": 5000,
            "full_refresh_sequence": ["reset", "power_on", "write_ram", "display_refresh", "wait_busy"],
            "partial_refresh_policy": "disabled until controller partial LUT is validated",
            "sleep_or_powerdown_sequence": ["deep_sleep"],
        }
    )
    return data


def validate_facts(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(data.get("schema_id") == FACTS_SCHEMA_ID, f"facts schema_id must be {FACTS_SCHEMA_ID}", errors)
    status = str(data.get("status", ""))
    require(status in {"DRAFT_UNFILLED", "READY_FOR_DRIVER_FACTS"}, "facts status must be DRAFT_UNFILLED or READY_FOR_DRIVER_FACTS", errors)
    target = str(data.get("target", ""))
    require(target in TARGETS, f"facts target must be one of {TARGETS}", errors)
    require(data.get("claim_scope") == "hardware_facts_only_no_real_refresh", "facts claim_scope must not claim real refresh", errors)

    identity = data.get("panel_identity", {})
    pin_map = data.get("target_pin_map", {})
    timing = data.get("driver_timing", {})
    guard = data.get("acceptance_guard", {})
    require(isinstance(identity, dict), "panel_identity must be an object", errors)
    require(isinstance(pin_map, dict), "target_pin_map must be an object", errors)
    require(isinstance(timing, dict), "driver_timing must be an object", errors)
    require(guard.get("does_not_claim_real_refresh") is True, "facts must not claim real refresh", errors)
    require(guard.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "facts must preserve deferred panel gate", errors)

    if isinstance(identity, dict):
        resolution = identity.get("resolution_px")
        require(
            isinstance(resolution, list) and len(resolution) == 2 and all(isinstance(value, int) and value > 0 for value in resolution),
            "panel_identity.resolution_px must be [width, height] positive integers",
            errors,
        )
    if isinstance(pin_map, dict):
        require(pin_map.get("target_family") == target, "target_pin_map.target_family must match facts target", errors)
        if target == "WB55":
            for key, expected in {
                "spi_instance_or_bus": "SPI2",
                "sck_pin": "PA9",
                "mosi_pin": "PC1",
                "miso_pin": "PC2",
                "cs_pin": "PA6",
                "cs_label": "SPI2_CS",
            }.items():
                require(pin_map.get(key) == expected, f"WB55 facts {key} expected {expected}", errors)
        else:
            serialized = json.dumps(pin_map)
            for wb55_fact in ["PA9", "PC1", "PC2", "PA6", "SPI2_CS"]:
                require(wb55_fact not in serialized, f"{target} facts leaked WB55 pin fact {wb55_fact}", errors)

    if status == "DRAFT_UNFILLED":
        for dotted in [
            "panel_identity.controller_model",
            "target_pin_map.dc_pin",
            "target_pin_map.rst_pin",
            "target_pin_map.busy_pin",
            "driver_timing.reset_low_ms",
        ]:
            section, field = dotted.split(".", 1)
            require(is_placeholder(data.get(section, {}).get(field)), f"draft facts should keep {dotted} as a TODO", errors)
        return errors

    for section, fields in {
        "panel_identity": [
            "controller_model",
            "panel_module_or_label",
            "panel_variant",
            "resolution_px",
            "datasheet_revision",
            "waveform_lut_source",
        ],
        "target_pin_map": [
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
    }.items():
        value = data.get(section, {})
        require(isinstance(value, dict), f"{section} must be an object", errors)
        if not isinstance(value, dict):
            continue
        for field in fields:
            require(field in value, f"{section}.{field} missing", errors)
            require(not is_placeholder(value.get(field)), f"{section}.{field} must be filled before READY_FOR_DRIVER_FACTS", errors)

    if isinstance(pin_map, dict):
        for field in ["sck_pin", "mosi_pin", "cs_pin", "dc_pin", "rst_pin", "busy_pin", "power_enable_pin"]:
            require(valid_pin_or_not_present(pin_map.get(field)), f"target_pin_map.{field} must be an STM32 pin or not_present", errors)
        require(str(pin_map.get("logic_voltage", "")).strip() in {"1.8V", "3.0V", "3.3V"}, "logic_voltage must be 1.8V, 3.0V, or 3.3V", errors)
    if isinstance(timing, dict):
        for field in ["reset_low_ms", "reset_high_ms", "busy_timeout_ms"]:
            require(isinstance(timing.get(field), int) and timing.get(field) > 0, f"driver_timing.{field} must be a positive integer", errors)
        for field in ["full_refresh_sequence", "sleep_or_powerdown_sequence"]:
            require(isinstance(timing.get(field), list) and timing.get(field), f"driver_timing.{field} must be a non-empty list", errors)
    return errors


def write_json(path: pathlib.Path, data: dict[str, Any], force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Defines the hardware-fact intake file that can be filled before a real WB55/WBA "
            "panel driver is implemented, without claiming a real refresh."
        ),
        "sources": {
            "facts_tool": "tools/verify_expression_panel_hardware_facts.py",
            "session_init_tool": "tools/init_expression_panel_evidence_record.py",
            "panel_evidence_template": rel(PANEL_EVIDENCE_TEMPLATE),
            "panel_hardware_gate": rel(PANEL_GATE),
            "panel_session_directory_preflight": rel(PANEL_SESSION_PREFLIGHT),
            "screen_doc": rel(SCREEN_DOC),
            "bringup_doc": rel(BRINGUP_DOC),
            "epaper_readme": rel(EPAPER_README),
        },
        "facts_schema_id": FACTS_SCHEMA_ID,
        "draft_filename": FACTS_FILENAME,
        "target_coverage": list(TARGETS),
        "accepted_fact_statuses": ["DRAFT_UNFILLED", "READY_FOR_DRIVER_FACTS"],
        "ready_for_driver_required_sections": {
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
        },
        "wb55_prefilled_transport": {
            "spi_instance_or_bus": "SPI2",
            "sck_pin": "PA9",
            "mosi_pin": "PC1",
            "miso_pin": "PC2",
            "cs_pin": "PA6",
            "cs_label": "SPI2_CS",
        },
        "real_refresh_guard": {
            "does_not_claim_real_refresh": True,
            "panel_gate_must_remain": "DEFERRED_HARDWARE",
            "still_requires_ble_diagnostics_visual_evidence": True,
        },
        "self_test_cases": [
            "draft_wb55_facts_pass_intake",
            "ready_wb55_facts_pass_intake",
            "ready_facts_with_placeholder_fail",
            "wba_facts_must_not_copy_wb55_pins",
            "invalid_pin_fails",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_hardware_facts.py",
            "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
            "python .\\tools\\verify_expression_panel_gate.py",
        ],
    }


def run_self_test() -> list[str]:
    errors: list[str] = []
    draft = build_draft_facts("WB55")
    draft_errors = validate_facts(draft)
    require(not draft_errors, f"draft WB55 facts failed: {draft_errors}", errors)

    ready = build_ready_self_test_facts("WB55")
    ready_errors = validate_facts(ready)
    require(not ready_errors, f"ready WB55 facts failed: {ready_errors}", errors)

    placeholder = json.loads(json.dumps(ready))
    placeholder["panel_identity"]["controller_model"] = "TODO_CONTROLLER_MODEL"
    require(validate_facts(placeholder), "ready facts with placeholder did not fail", errors)

    wba = build_draft_facts("WBA55")
    wba["target_pin_map"]["sck_pin"] = "PA9"
    require(validate_facts(wba), "WBA facts with WB55 pin did not fail", errors)

    invalid_pin = json.loads(json.dumps(ready))
    invalid_pin["target_pin_map"]["dc_pin"] = "D0"
    require(validate_facts(invalid_pin), "invalid pin self-test did not fail", errors)

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        path = root / FACTS_FILENAME
        write_json(path, draft)
        require(load_json(path) == draft, "facts draft write/read self-test drifted", errors)
    return errors


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected hardware facts intake schema", errors)
    require(data.get("status") == "PASS", "hardware facts intake fixture must be PASS", errors)
    sources = data.get("sources", {})
    for key in ["facts_tool", "session_init_tool", "panel_evidence_template", "panel_hardware_gate"]:
        source = sources.get(key)
        require(isinstance(source, str) and (REPO_ROOT / source).exists(), f"fixture source missing {key}", errors)
    require(data.get("facts_schema_id") == FACTS_SCHEMA_ID, "fixture facts schema id drifted", errors)
    require(data.get("draft_filename") == FACTS_FILENAME, "fixture draft filename drifted", errors)
    require(data.get("target_coverage") == list(TARGETS), "fixture target coverage drifted", errors)
    require(data.get("accepted_fact_statuses") == ["DRAFT_UNFILLED", "READY_FOR_DRIVER_FACTS"], "fixture fact statuses drifted", errors)
    guard = data.get("real_refresh_guard", {})
    require(guard.get("does_not_claim_real_refresh") is True, "fixture must not claim real refresh", errors)
    require(guard.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "fixture must preserve deferred gate", errors)
    for case in [
        "draft_wb55_facts_pass_intake",
        "ready_wb55_facts_pass_intake",
        "ready_facts_with_placeholder_fail",
        "wba_facts_must_not_copy_wb55_pins",
        "invalid_pin_fails",
    ]:
        require(case in data.get("self_test_cases", []), f"fixture missing self-test case {case}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (BRINGUP_DOC, "bringup doc"), (EPAPER_README, "epaper README")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "panel_hardware_facts_intake",
            "verify_expression_panel_hardware_facts.py",
            FACTS_FILENAME,
            "READY_FOR_DRIVER_FACTS",
            "does not claim real refresh",
        ]:
            require(token in text, f"{name} missing hardware facts intake anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_hardware_facts_intake"]
        require(len(items) == 1, "acceptance index must contain one panel_hardware_facts_intake item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_hardware_facts_intake item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel_hardware_facts_intake item must link fixture", errors)
            require(
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test" in item.get("validation_commands", []),
                "panel_hardware_facts_intake item must run self-test",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing hardware facts intake fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic hardware-facts fixture.")
    parser.add_argument("--self-test", action="store_true", help="Run draft/ready/invalid fact checks.")
    parser.add_argument("--facts", type=pathlib.Path, default=None, help="Hardware fact JSON to validate.")
    parser.add_argument("--target", choices=TARGETS, default="WB55")
    parser.add_argument("--session-root", type=pathlib.Path, default=None)
    parser.add_argument("--output", type=pathlib.Path, default=None)
    parser.add_argument("--write-draft", action="store_true", help="Write a DRAFT_UNFILLED hardware-facts intake JSON.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft facts file.")
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
    facts_path: pathlib.Path | None = None
    if args.write_draft:
        if args.session_root is None and args.output is None:
            errors.append("--write-draft requires --session-root or --output")
        else:
            if args.output is not None:
                facts_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output
            else:
                root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root
                facts_path = root / FACTS_FILENAME
            if facts_path is not None and not errors:
                try:
                    write_json(facts_path, build_draft_facts(args.target), force=bool(args.force))
                except FileExistsError:
                    errors.append(f"hardware facts draft already exists: {rel(facts_path)}; use --force to overwrite")
    if args.facts is not None:
        facts_path = args.facts if args.facts.is_absolute() else REPO_ROOT / args.facts
    if facts_path is not None and facts_path.exists():
        errors.extend(validate_facts(load_json(facts_path)))

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel hardware facts intake checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    if facts_path is not None:
        print(f"PASS: Companion panel hardware facts intake verified -> {rel(facts_path)}")
    else:
        print(f"PASS: Companion panel hardware facts intake verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
