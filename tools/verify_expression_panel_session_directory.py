#!/usr/bin/env python3
"""Verify a concrete real-panel session directory before hardware evidence is filled."""

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
import render_expression_panel_bringup_packet as operator_packet  # noqa: E402
import verify_expression_panel_evidence_record as final_validator  # noqa: E402
import verify_expression_panel_hardware_facts as hardware_facts  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-session-directory-preflight.json")
SCHEMA_ID = "companion.pendant.screen_panel_session_directory_preflight.v1"
RECORD_SCHEMA_ID = "companion.pendant.screen_panel_evidence_record.v1"
PANEL_GATE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
PANEL_SESSION = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-session.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs/bringup_steps.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"

TARGETS = {"WB55", "WBA55", "WBA65"}
SESSION_RECORD = init_record.SESSION_RECORD_FILENAME
SESSION_FACTS = init_record.SESSION_FACTS_FILENAME
SESSION_OPERATOR_PACKET_JSON = "panel-bringup-operator-packet.json"
SESSION_OPERATOR_PACKET_MARKDOWN = "panel-bringup-operator-packet.md"
SESSION_RELATIVE_ARTIFACTS = {
    "host_observability.real_ble_bench_artifact": "companion-ble-real-bench.json",
    "host_observability.diagnostics_bundle_artifact": "diagnostics/summary.json",
    "visual_evidence.before_photo": "visual/before_photo.jpg",
    "visual_evidence.during_refresh_photo_or_video": "visual/during_refresh_photo_or_video",
    "visual_evidence.after_photo": "visual/after_photo.jpg",
}


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


def nested_get(data: dict[str, Any], dotted_key: str) -> Any:
    value: Any = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def is_todo(value: Any) -> bool:
    return isinstance(value, str) and "TODO" in value


def session_root_for_args(root: pathlib.Path) -> pathlib.Path:
    try:
        return pathlib.Path(root.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return root


def expected_operator_packet(root: pathlib.Path, target: str) -> tuple[dict[str, Any], str]:
    args = operator_packet.parse_args([
        "--session-root",
        str(session_root_for_args(root)),
        "--target",
        target,
    ])
    packet = operator_packet.build_packet(args)
    return packet, operator_packet.render_markdown(packet)


def write_operator_packet(root: pathlib.Path, target: str) -> None:
    packet, markdown = expected_operator_packet(root, target)
    operator_packet.write_outputs(
        root / SESSION_OPERATOR_PACKET_JSON,
        root / SESSION_OPERATOR_PACKET_MARKDOWN,
        packet,
        markdown,
    )


def validate_operator_packet_files(root: pathlib.Path, target: str) -> list[str]:
    errors: list[str] = []
    json_path = root / SESSION_OPERATOR_PACKET_JSON
    markdown_path = root / SESSION_OPERATOR_PACKET_MARKDOWN
    if not json_path.exists() and not markdown_path.exists():
        return errors

    require(json_path.exists(), f"session operator packet JSON missing: {rel(json_path)}", errors)
    require(markdown_path.exists(), f"session operator packet Markdown missing: {rel(markdown_path)}", errors)
    if not json_path.exists() or not markdown_path.exists():
        return errors

    try:
        actual = load_json(json_path)
    except json.JSONDecodeError as exc:
        return [f"session operator packet JSON is invalid: {rel(json_path)}: {exc}"]

    expected, expected_markdown = expected_operator_packet(root, target)
    packet_errors: list[str] = []
    operator_packet.validate_packet(actual, packet_errors, deterministic=False)
    errors.extend(f"session operator packet {error}" for error in packet_errors)
    require(actual == expected, f"{rel(json_path)} is stale; rerun render_expression_panel_bringup_packet.py --write", errors)

    markdown = markdown_path.read_text(encoding="utf-8")
    require(
        markdown == expected_markdown,
        f"{rel(markdown_path)} is stale; rerun render_expression_panel_bringup_packet.py --write",
        errors,
    )
    serialized = json.dumps(actual, sort_keys=True)
    require(
        f"-Resource {operator_packet.target_resource_arg(target)}" in serialized,
        "session operator packet must quote hardware lock resources",
        errors,
    )
    require("partial_operation_count" in serialized, "session operator packet missing partial failure evidence", errors)
    require(
        "failed runs must preserve operations and partial_operation_count" in markdown,
        "session operator packet Markdown missing partial failure evidence note",
        errors,
    )
    return errors


def validate_session_directory(root: pathlib.Path, target: str) -> list[str]:
    errors: list[str] = []
    require(target in TARGETS, f"target must be one of {sorted(TARGETS)}", errors)
    require(root.exists(), f"session root missing: {rel(root)}", errors)
    require(root.is_dir(), f"session root is not a directory: {rel(root)}", errors)
    if not root.exists() or not root.is_dir():
        return errors

    for directory in ["visual", "diagnostics"]:
        require((root / directory).is_dir(), f"session directory missing {directory}/", errors)
    notes = root / "operator-notes.md"
    require(notes.exists(), f"session operator notes missing: {rel(notes)}", errors)
    if notes.exists():
        text = notes.read_text(encoding="utf-8")
        for token in [
            "controller_model",
            "dc_pin",
            "rst_pin",
            "busy_pin",
            SESSION_FACTS,
            "companion_ble_real_bench.py --expect-real-panel",
            "verify_expression_panel_evidence_record.py --record",
        ]:
            require(token in text, f"operator notes missing {token}", errors)

    facts_path = root / SESSION_FACTS
    require(facts_path.exists(), f"session hardware facts draft missing: {rel(facts_path)}", errors)
    if facts_path.exists():
        facts = load_json(facts_path)
        facts_errors = hardware_facts.validate_facts(facts)
        require(not facts_errors, f"session hardware facts draft failed intake: {facts_errors}", errors)
        require(facts.get("status") == "DRAFT_UNFILLED", "session hardware facts must start as DRAFT_UNFILLED", errors)
        require(facts.get("target") == target, f"session hardware facts target must be {target}", errors)
        require(facts.get("session_record") == SESSION_RECORD, "session hardware facts must point at panel-evidence-record.json", errors)
    errors.extend(validate_operator_packet_files(root, target))

    record_path = root / SESSION_RECORD
    require(record_path.exists(), f"session evidence record missing: {rel(record_path)}", errors)
    if not record_path.exists():
        return errors
    record = load_json(record_path)
    require(record.get("schema_id") == RECORD_SCHEMA_ID, "session record schema drifted", errors)
    require(record.get("status") == "DRAFT_UNFILLED", "session preflight expects a DRAFT_UNFILLED record", errors)
    require(record.get("claim_scope") == "real_panel_refresh", "session record claim_scope must be real_panel_refresh", errors)

    for dotted_key, expected in SESSION_RELATIVE_ARTIFACTS.items():
        require(nested_get(record, dotted_key) == expected, f"session record {dotted_key} must be {expected}", errors)

    pin_map = record.get("target_pin_map", {})
    require(isinstance(pin_map, dict), "session record target_pin_map must be an object", errors)
    if isinstance(pin_map, dict):
        require(pin_map.get("target_family") == target, f"session record target_family must be {target}", errors)
        if target == "WB55":
            expected_wb55 = {
                "spi_instance_or_bus": "SPI2",
                "sck_pin": "PA9",
                "mosi_pin": "PC1",
                "miso_pin": "PC2",
                "cs_pin": "PA6",
                "cs_label": "SPI2_CS",
            }
            for key, expected in expected_wb55.items():
                require(pin_map.get(key) == expected, f"WB55 session {key} expected {expected}", errors)
        else:
            for wb55_fact in ["PA9", "PC1", "PC2", "PA6", "SPI2_CS"]:
                require(wb55_fact not in json.dumps(pin_map), f"{target} session leaked WB55 pin fact {wb55_fact}", errors)
        for key in ["dc_pin", "rst_pin", "busy_pin", "logic_voltage"]:
            require(is_todo(pin_map.get(key)), f"session preflight expects {key} to remain TODO until hardware review", errors)

    final_errors = final_validator.validate_record(record, record_path)
    require(final_errors, "DRAFT_UNFILLED session record unexpectedly passed final real-panel validator", errors)
    require(
        any("status must be PASS" in error for error in final_errors),
        "final validator must reject the draft session status",
        errors,
    )
    return errors


def create_session(root: pathlib.Path, target: str) -> None:
    record = init_record.build_record(target, "idle", "2.13in")
    init_record.apply_session_paths(record)
    init_record.write_session_scaffold(root, root / SESSION_RECORD, record, target, "idle", "2.13in")


def run_self_test() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "companion-real-panel-wb55-self-test"
        create_session(root, "WB55")
        valid_errors = validate_session_directory(root, "WB55")
        require(not valid_errors, f"valid generated WB55 session failed preflight: {valid_errors}", errors)

        missing_notes = pathlib.Path(tmp) / "missing-notes"
        create_session(missing_notes, "WB55")
        (missing_notes / "operator-notes.md").unlink()
        require(validate_session_directory(missing_notes, "WB55"), "missing operator notes self-test did not fail", errors)

        wrong_status = pathlib.Path(tmp) / "wrong-status"
        create_session(wrong_status, "WB55")
        record_path = wrong_status / SESSION_RECORD
        record = load_json(record_path)
        record["status"] = "PASS"
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        require(validate_session_directory(wrong_status, "WB55"), "filled-status self-test did not fail preflight", errors)

        missing_visual = pathlib.Path(tmp) / "missing-visual"
        create_session(missing_visual, "WB55")
        (missing_visual / "visual").rmdir()
        require(validate_session_directory(missing_visual, "WB55"), "missing visual directory self-test did not fail", errors)

        current_packet = pathlib.Path(tmp) / "current-packet"
        create_session(current_packet, "WB55")
        write_operator_packet(current_packet, "WB55")
        current_packet_errors = validate_session_directory(current_packet, "WB55")
        require(not current_packet_errors, f"current operator packet self-test failed: {current_packet_errors}", errors)

        stale_packet = pathlib.Path(tmp) / "stale-packet"
        create_session(stale_packet, "WB55")
        write_operator_packet(stale_packet, "WB55")
        for packet_path in [
            stale_packet / SESSION_OPERATOR_PACKET_JSON,
            stale_packet / SESSION_OPERATOR_PACKET_MARKDOWN,
        ]:
            text = packet_path.read_text(encoding="utf-8")
            text = text.replace("-Resource 'Companion-WB55,BLE-Companion'", "-Resource Companion-WB55,BLE-Companion")
            text = text.replace("partial_operation_count", "partial_count_legacy")
            packet_path.write_text(text, encoding="utf-8")
        require(validate_session_directory(stale_packet, "WB55"), "stale operator packet self-test did not fail", errors)
    return errors


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "No-hardware preflight for concrete real-panel session directories: "
            "the generated directory is ready for operator evidence, but its draft "
            "record is still rejected by the final hardware validator."
        ),
        "sources": {
            "session_init_tool": "tools/init_expression_panel_evidence_record.py",
            "session_directory_preflight": "tools/verify_expression_panel_session_directory.py",
            "operator_packet_tool": "tools/render_expression_panel_bringup_packet.py",
            "final_record_validator": "tools/verify_expression_panel_evidence_record.py",
            "panel_hardware_session": rel(PANEL_SESSION),
            "panel_hardware_gate": rel(PANEL_GATE),
            "screen_doc": rel(SCREEN_DOC),
            "bringup_doc": rel(BRINGUP_DOC),
            "epaper_readme": rel(EPAPER_README),
        },
        "target_coverage": sorted(TARGETS),
        "validated_session_layout": [
            SESSION_RECORD,
            SESSION_FACTS,
            "operator-notes.md",
            "visual/",
            "diagnostics/",
        ],
        "optional_operator_packet_guard": {
            "json": SESSION_OPERATOR_PACKET_JSON,
            "markdown": SESSION_OPERATOR_PACKET_MARKDOWN,
            "must_match_current_renderer": True,
            "requires_quoted_hardware_lock_resource": True,
            "requires_partial_failure_evidence": ["operations", "partial_operation_count"],
        },
        "hardware_facts_draft": {
            "filename": SESSION_FACTS,
            "required_status_before_driver": "DRAFT_UNFILLED",
            "validated_by": f"python .\\tools\\verify_expression_panel_hardware_facts.py --facts <session>\\{SESSION_FACTS}",
        },
        "session_relative_artifact_paths": SESSION_RELATIVE_ARTIFACTS,
        "wb55_prefilled_transport": {
            "spi_instance_or_bus": "SPI2",
            "sck_pin": "PA9",
            "mosi_pin": "PC1",
            "miso_pin": "PC2",
            "cs_pin": "PA6",
            "cs_label": "SPI2_CS",
        },
        "draft_record_guard": {
            "required_status_before_hardware": "DRAFT_UNFILLED",
            "must_fail_final_validator": True,
            "final_validator": "python .\\tools\\verify_expression_panel_evidence_record.py --record <session>/panel-evidence-record.json",
        },
        "self_test_cases": [
            "generated_wb55_session_passes_preflight",
            "missing_operator_notes_fails",
            "pass_status_before_hardware_fails",
            "missing_visual_directory_fails",
            "draft_record_is_rejected_by_final_validator",
            "current_operator_packet_passes",
            "stale_operator_packet_fails",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_session_directory.py --self-test",
            "python .\\tools\\init_expression_panel_evidence_record.py --target WB55 --session-root .\\.cache\\validation\\companion-real-panel-wb55-<timestamp> --write-session",
            "python .\\tools\\verify_expression_panel_session_directory.py --session-root .\\.cache\\validation\\companion-real-panel-wb55-<timestamp> --target WB55",
            "python .\\tools\\verify_expression_panel_hardware_facts.py --facts .\\.cache\\validation\\companion-real-panel-wb55-<timestamp>\\panel-hardware-facts.todo.json",
            "python .\\tools\\render_expression_panel_bringup_packet.py --session-root .\\.cache\\validation\\companion-real-panel-wb55-<timestamp> --write --json .\\.cache\\validation\\companion-real-panel-wb55-<timestamp>\\panel-bringup-operator-packet.json --markdown .\\.cache\\validation\\companion-real-panel-wb55-<timestamp>\\panel-bringup-operator-packet.md",
            "python .\\tools\\verify_expression_panel_evidence_record.py --record .\\.cache\\validation\\companion-real-panel-wb55-<timestamp>\\panel-evidence-record.json",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel session directory preflight schema", errors)
    require(data.get("status") == "PASS", "panel session directory preflight fixture must be PASS", errors)
    sources = data.get("sources", {})
    for key in ["session_init_tool", "session_directory_preflight", "operator_packet_tool", "final_record_validator", "panel_hardware_session", "panel_hardware_gate"]:
        source = sources.get(key)
        require(isinstance(source, str) and (REPO_ROOT / source).exists(), f"fixture source missing {key}", errors)
    require(data.get("target_coverage") == sorted(TARGETS), "fixture target coverage drifted", errors)
    layout = data.get("validated_session_layout", [])
    for token in [SESSION_RECORD, SESSION_FACTS, "operator-notes.md", "visual/", "diagnostics/"]:
        require(token in layout, f"fixture missing layout token {token}", errors)
    facts = data.get("hardware_facts_draft", {})
    require(facts.get("filename") == SESSION_FACTS, "fixture hardware facts draft filename drifted", errors)
    require(
        facts.get("required_status_before_driver") == "DRAFT_UNFILLED",
        "fixture hardware facts draft status drifted",
        errors,
    )
    require(data.get("session_relative_artifact_paths") == SESSION_RELATIVE_ARTIFACTS, "fixture session relative paths drifted", errors)
    packet_guard = data.get("optional_operator_packet_guard", {})
    require(packet_guard.get("json") == SESSION_OPERATOR_PACKET_JSON, "fixture operator packet JSON filename drifted", errors)
    require(packet_guard.get("markdown") == SESSION_OPERATOR_PACKET_MARKDOWN, "fixture operator packet Markdown filename drifted", errors)
    require(packet_guard.get("must_match_current_renderer") is True, "fixture must require current operator packet renderer", errors)
    require(packet_guard.get("requires_quoted_hardware_lock_resource") is True, "fixture must require quoted hardware lock resources", errors)
    require(
        packet_guard.get("requires_partial_failure_evidence") == ["operations", "partial_operation_count"],
        "fixture partial failure evidence guard drifted",
        errors,
    )
    wb55 = data.get("wb55_prefilled_transport", {})
    for key, expected in {
        "spi_instance_or_bus": "SPI2",
        "sck_pin": "PA9",
        "mosi_pin": "PC1",
        "miso_pin": "PC2",
        "cs_pin": "PA6",
        "cs_label": "SPI2_CS",
    }.items():
        require(wb55.get(key) == expected, f"fixture WB55 {key} drifted", errors)
    guard = data.get("draft_record_guard", {})
    require(guard.get("required_status_before_hardware") == "DRAFT_UNFILLED", "fixture draft guard status drifted", errors)
    require(guard.get("must_fail_final_validator") is True, "fixture must require final validator rejection", errors)
    for case in [
        "generated_wb55_session_passes_preflight",
        "missing_operator_notes_fails",
        "pass_status_before_hardware_fails",
        "missing_visual_directory_fails",
        "draft_record_is_rejected_by_final_validator",
        "current_operator_packet_passes",
        "stale_operator_packet_fails",
    ]:
        require(case in data.get("self_test_cases", []), f"fixture missing self-test case {case}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (BRINGUP_DOC, "bringup doc"), (EPAPER_README, "epaper README")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "panel_session_directory_preflight",
            "verify_expression_panel_session_directory.py",
            "--write-session",
            "DRAFT_UNFILLED",
            "operator-notes.md",
            "panel-bringup-operator-packet",
            "partial_operation_count",
        ]:
            require(token in text, f"{name} missing panel session directory preflight anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_session_directory_preflight"]
        require(len(items) == 1, "acceptance index must contain one panel_session_directory_preflight item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_session_directory_preflight item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel_session_directory_preflight item must link fixture", errors)
            require(
                "python .\\tools\\verify_expression_panel_session_directory.py --self-test" in item.get("validation_commands", []),
                "panel_session_directory_preflight item must run self-test",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel session directory preflight fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic preflight fixture.")
    parser.add_argument("--self-test", action="store_true", help="Run generated-session positive and negative checks.")
    parser.add_argument("--session-root", type=pathlib.Path, default=None, help="Concrete session directory to validate.")
    parser.add_argument("--target", choices=sorted(TARGETS), default="WB55")
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
    if args.session_root is not None:
        root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root
        errors.extend(validate_session_directory(root, args.target))
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel session directory preflight checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    if args.session_root is not None:
        print(f"PASS: Companion panel session directory preflight verified -> {rel(root)}")
    else:
        print(f"PASS: Companion panel session directory preflight verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
