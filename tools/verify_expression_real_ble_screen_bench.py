#!/usr/bin/env python3
"""Verify the real BLE bench captures final screen status for panel acceptance."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-real-ble-bench.json")
SCHEMA_ID = "companion.pendant.screen_real_ble_bench.v1"

REAL_BENCH = REPO_ROOT / "tools" / "companion_ble_real_bench.py"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"
PANEL_EVIDENCE_TEMPLATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-template.json"
HOST_STATUS_SEQUENCE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-host-status-sequence.json"
DEMO_HOST_STATUS_SEQUENCE = (
    REPO_ROOT / "docs" / "validation" / "companion-screen-expression-demo-host-status-sequence.json"
)

EXPECTED_STATUS_EVENTS = [
    "boot_idle",
    "settings.display_off",
    "recording_fsm.start_request",
    "battery_charging.sample.low",
    "recording_fsm.session_finished",
    "errors.fault",
]
EXPECTED_STATUS_FACES = [
    "idle",
    "sleepy",
    "recording",
    "low_battery",
    "sync_complete",
    "error",
]


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "real_ble_bench": rel(REAL_BENCH),
            "ble_contract": rel(BLE_CONTRACT),
            "bringup_steps": rel(BRINGUP_STEPS),
            "screen_acceptance": rel(SCREEN_DOC),
            "panel_gate": rel(PANEL_GATE),
            "panel_evidence_template": rel(PANEL_EVIDENCE_TEMPLATE),
            "host_expression_status_sequence": rel(HOST_STATUS_SEQUENCE),
            "demo_host_expression_status_sequence": rel(DEMO_HOST_STATUS_SEQUENCE),
        },
        "bench_operation": {
            "operation": "card_write",
            "accepted_status_field": "card_status",
            "final_status_field": "final_card_status",
            "status_sequence_field": "status_sequence",
            "real_panel_flag": "--expect-real-panel",
            "final_timeout_flag": "--screen-final-timeout",
            "default_no_panel_ok": True,
            "real_panel_required_final": {
                "render_state": "rendered",
                "render_state_value": 2,
                "last_error": "ok",
                "last_error_value": 0,
            },
            "no_panel_allowed_final": {
                "render_state": "failed",
                "last_error_values": [4, 5],
                "last_errors": ["deferred_no_panel", "deferred_controller_unknown"],
            },
        },
        "expression_bench_operation": {
            "operation": "settings_sleepy_screen_status",
            "trigger": "SettingsV1 display_brightness=0",
            "restore_operation": "settings_restore_after_sleepy",
            "accepted_status_field": "card_status",
            "final_status_field": "final_card_status",
            "status_sequence_field": "status_sequence",
            "expression_request_id_base": "0xe0000000",
            "expression_card_slot": 1,
            "real_panel_flag": "--expect-real-panel",
            "final_timeout_flag": "--screen-final-timeout",
            "default_no_panel_ok": True,
            "real_panel_required_final": {
                "render_state": "rendered",
                "render_state_value": 2,
                "last_error": "ok",
                "last_error_value": 0,
            },
            "no_panel_allowed_final": {
                "render_state": "failed",
                "last_error_values": [4, 5],
                "last_errors": ["deferred_no_panel", "deferred_controller_unknown"],
            },
        },
        "expression_status_sequence_operation": {
            "operation": "screen_expression_status",
            "contract_only": True,
            "hardware_collected": False,
            "host_sequence_fixture": rel(HOST_STATUS_SEQUENCE),
            "expected_events": EXPECTED_STATUS_EVENTS,
            "required_faces": EXPECTED_STATUS_FACES,
            "required_fields": [
                "request_id",
                "content_crc32",
                "diagnostic_arg3",
                "accepted_refresh_count",
                "final_refresh_count",
            ],
            "content_crc32_model": "comp_epaper_expression_decision_crc32",
            "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
            "real_panel_parity_dependency": "card_write and settings_sleepy_screen_status must still pass with --expect-real-panel before rendered/ok parity is claimed.",
        },
        "expression_demo_status_sequence_operation": {
            "operation": "screen_expression_demo_status",
            "contract_only": True,
            "hardware_collected": False,
            "host_sequence_fixture": rel(DEMO_HOST_STATUS_SEQUENCE),
            "required_faces": [
                "error",
                "happy",
                "idle",
                "listening",
                "low_battery",
                "recording",
                "sleepy",
                "speaking",
                "sync_complete",
                "thinking",
            ],
            "accepted_status_pair_count": 29,
            "held_no_status_count": 8,
            "required_fields": [
                "request_id",
                "content_crc32",
                "diagnostic_arg3",
                "card_status",
                "dry_run_final_status",
            ],
            "content_crc32_model": "comp_epaper_expression_decision_crc32",
            "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
            "held_steps_contract": "held_steps_emit_no_host_status",
            "real_panel_parity_dependency": "card_write and settings_sleepy_screen_status still provide the hardware-collected rendered/ok evidence.",
        },
        "artifact_contract": {
            "real_panel_refresh_claimed": "true only when final_card_status is rendered/ok",
            "screen_panel_result": ["rendered_ok", "deferred_no_panel_or_controller_unknown"],
            "request_identity": "accepted and final CardStatusV1 request_id/content_crc32 must match",
            "expression_request_identity": "settings_sleepy_screen_status must use expression card_slot=1 and 0xe0000000 request_id base",
            "host_expression_status_sequence": "artifact carries screen_expression_status baseline from companion-screen-expression-host-status-sequence.json so WBA/WB55 real bench parity compares the same six-face host contract",
            "demo_host_expression_status_sequence": "artifact carries screen_expression_demo_status baseline from companion-screen-expression-demo-host-status-sequence.json so WBA/WB55 benches keep all demo faces host-observable",
            "partial_failure_evidence": "failed live artifacts must keep operations and partial_operation_count so hardware loss is distinguishable from screen contract drift",
            "evidence_for_hardware_gate": [
                "card_status",
                "final_card_status",
                "status_sequence",
                "screen_expression_status",
                "screen_expression_demo_status",
                "real_panel_refresh_claimed",
                "screen_panel_result",
                "partial_operation_count",
            ],
        },
        "acceptance": {
            "real_bench_waits_for_final_card_status": True,
            "expect_real_panel_requires_rendered_ok": True,
            "default_bench_allows_no_panel_deferred_status": True,
            "accepted_final_identity_is_checked": True,
            "real_bench_collects_expression_final_status": True,
            "settings_sleepy_trigger_has_final_card_status": True,
            "real_bench_carries_host_expression_status_sequence": True,
            "six_face_sequence_baseline_is_linked": True,
            "real_bench_carries_demo_expression_status_sequence": True,
            "demo_sequence_baseline_covers_all_faces": True,
            "demo_sequence_held_steps_emit_no_status": True,
            "expression_request_identity_is_checked": True,
            "hardware_gate_can_reference_real_ble_artifact": True,
            "wba_real_ble_bench_can_reuse_contract": True,
            "wba_real_ble_bench_requires_screen_expression_status": True,
            "failed_bench_preserves_partial_operations": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python -m py_compile .\\tools\\companion_ble_real_bench.py",
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\verify_expression_demo_host_status_sequence.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_real_bench_code(errors: list[str]) -> None:
    text = read(REAL_BENCH, errors)
    for token in [
        "CARD_RENDER_STATE_ACCEPTED = 1",
        "CARD_RENDER_STATE_RENDERED = 2",
        "CARD_RENDER_STATE_FAILED = 3",
        "CARD_RENDER_STATE_BUSY = 4",
        "CARD_LAST_ERROR_OK = 0",
        "CARD_LAST_ERROR_DEFERRED_NO_PANEL = 4",
        "CARD_LAST_ERROR_DEFERRED_CONTROLLER_UNKNOWN = 5",
        "EXPRESSION_CARD_SLOT = 1",
        "EXPRESSION_REQUEST_ID_BASE = 0xE0000000",
        "EXPRESSION_REQUEST_ID_MASK = 0xF0000000",
        "async def write_card_and_collect_status",
        "def is_expression_card_status",
        "async def write_settings_and_collect_expression_status",
        "class BenchPartialError",
        "self.result = result",
        "partial_operation_count",
        "await client.start_notify(uuids[\"e_paper_card_status\"], callback)",
        "await client.write_gatt_char(uuids[\"e_paper_card_write\"], payload, response=True)",
        "await client.write_gatt_char(uuids[\"settings\"], payload, response=True)",
        "int(parsed[\"request_id\"]) != request_id",
        "int(parsed[\"card_slot\"]) == EXPRESSION_CARD_SLOT",
        "CARD_RENDER_STATE_ACCEPTED",
        "CARD_RENDER_STATE_RENDERED",
        "CARD_RENDER_STATE_FAILED",
        "CARD_RENDER_STATE_BUSY",
        "card write did not publish final status",
        "card write accepted/final identity drifted",
        "settings sleepy did not publish expression final status",
        "settings sleepy accepted/final identity drifted",
        "HOST_STATUS_SEQUENCE_PATH",
        "DEMO_HOST_STATUS_SEQUENCE_PATH",
        "EXPRESSION_STATUS_REQUIRED_EVENTS",
        "EXPRESSION_STATUS_REQUIRED_FACES",
        "EXPRESSION_DEMO_STATUS_REQUIRED_FACES",
        "def expression_status_sequence_contract",
        "def expression_demo_status_sequence_contract",
        "\"operation\": \"screen_expression_status\"",
        "\"operation\": \"screen_expression_demo_status\"",
        "\"contract_only\": True",
        "\"hardware_collected\": False",
        "\"host_sequence_fixture\"",
        "\"expected_events\"",
        "\"required_faces\"",
        "\"accepted_refresh_count\"",
        "\"final_refresh_count\"",
        "comp_epaper_expression_decision_crc32",
        "(expression_id << 16) | signal_id",
        "operations.append(expression_status_sequence_contract())",
        "operations.append(expression_demo_status_sequence_contract())",
        "raise BenchPartialError(",
        "\"operations\": operations",
        "if isinstance(exc, BenchPartialError):",
        "rendered_ok",
        "deferred_no_panel_or_controller_unknown",
        "real_panel_refresh_claimed",
        "settings_sleepy_screen_status",
        "settings_restore_after_sleepy",
        "screen_expression_status",
        "screen_expression_demo_status",
        "held_steps_emit_no_host_status",
        "expression_request_id_base",
        "final_card_status",
        "status_sequence",
        "--expect-real-panel",
        "--screen-final-timeout",
    ]:
        require(token in text, f"real BLE bench missing screen final status anchor {token}", errors)
    require(
        "args.expect_real_panel and not rendered_ok" in text,
        "real BLE bench must enforce rendered/ok when --expect-real-panel is set",
        errors,
    )
    require(
        "not args.expect_real_panel and not (rendered_ok or deferred_no_panel)" in text,
        "real BLE bench default mode must allow rendered/ok or deferred no-panel/controller",
        errors,
    )
    require(
        "operations.append(await write_card_and_collect_status" in text,
        "card_write operation must use final status collector",
        errors,
    )
    settings_index = text.find('"operation": "settings_sleepy_screen_status"')
    recording_index = text.find('"operation": "recording_control_and_list"')
    require(settings_index >= 0, "real BLE bench missing settings_sleepy_screen_status operation", errors)
    require(recording_index >= 0, "real BLE bench missing recording_control_and_list operation", errors)
    if settings_index >= 0 and recording_index >= 0:
        require(
            settings_index < recording_index,
            "settings sleepy screen status must be collected before recording control changes expression priority",
            errors,
        )
    partial_count_index = text.find('"partial_operation_count": len(operations)')
    partial_handler_index = text.find("if isinstance(exc, BenchPartialError):")
    require(partial_count_index >= 0, "real BLE bench missing partial_operation_count result field", errors)
    require(partial_handler_index >= 0, "real BLE bench missing BenchPartialError handler", errors)
    if partial_count_index >= 0 and partial_handler_index >= 0:
        require(
            partial_count_index < partial_handler_index,
            "partial operations must be attached before BenchPartialError is handled in main",
            errors,
        )


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected real BLE screen bench schema", errors)
    require(data.get("status") == "PASS", "real BLE screen bench fixture must be PASS", errors)
    bench = data.get("bench_operation", {})
    require(bench.get("final_status_field") == "final_card_status", "fixture missing final_card_status field", errors)
    require(bench.get("real_panel_flag") == "--expect-real-panel", "fixture missing --expect-real-panel flag", errors)
    require(bench.get("final_timeout_flag") == "--screen-final-timeout", "fixture missing --screen-final-timeout flag", errors)
    require(
        bench.get("real_panel_required_final", {}).get("render_state_value") == 2,
        "real panel final render_state must be rendered",
        errors,
    )
    require(
        bench.get("real_panel_required_final", {}).get("last_error_value") == 0,
        "real panel final last_error must be ok",
        errors,
    )
    expression = data.get("expression_bench_operation", {})
    require(
        expression.get("operation") == "settings_sleepy_screen_status",
        "fixture missing settings sleepy expression operation",
        errors,
    )
    require(
        expression.get("restore_operation") == "settings_restore_after_sleepy",
        "fixture missing settings restore operation",
        errors,
    )
    require(
        expression.get("expression_request_id_base") == "0xe0000000",
        "fixture missing expression request id base",
        errors,
    )
    require(expression.get("expression_card_slot") == 1, "fixture missing expression card slot", errors)
    require(
        expression.get("final_status_field") == "final_card_status",
        "fixture expression operation missing final_card_status field",
        errors,
    )
    sequence = data.get("expression_status_sequence_operation", {})
    require(sequence.get("operation") == "screen_expression_status", "fixture missing screen_expression_status operation", errors)
    require(sequence.get("contract_only") is True, "screen_expression_status operation must be contract-only", errors)
    require(sequence.get("hardware_collected") is False, "screen_expression_status baseline must not claim hardware collection", errors)
    require(
        sequence.get("host_sequence_fixture") == rel(HOST_STATUS_SEQUENCE),
        "screen_expression_status operation must link host sequence fixture",
        errors,
    )
    require(
        sequence.get("expected_events") == EXPECTED_STATUS_EVENTS,
        "screen_expression_status operation event list drifted",
        errors,
    )
    require(
        sequence.get("required_faces") == EXPECTED_STATUS_FACES,
        "screen_expression_status operation face list drifted",
        errors,
    )
    for field in ["request_id", "content_crc32", "diagnostic_arg3", "accepted_refresh_count", "final_refresh_count"]:
        require(
            field in sequence.get("required_fields", []),
            f"screen_expression_status operation missing required field {field}",
            errors,
        )
    require(
        sequence.get("content_crc32_model") == "comp_epaper_expression_decision_crc32",
        "screen_expression_status operation missing CRC model",
        errors,
    )
    require(
        sequence.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "screen_expression_status operation missing diagnostic arg3 model",
        errors,
    )
    demo_sequence = data.get("expression_demo_status_sequence_operation", {})
    require(
        demo_sequence.get("operation") == "screen_expression_demo_status",
        "fixture missing screen_expression_demo_status operation",
        errors,
    )
    require(
        demo_sequence.get("contract_only") is True,
        "screen_expression_demo_status operation must be contract-only",
        errors,
    )
    require(
        demo_sequence.get("hardware_collected") is False,
        "screen_expression_demo_status baseline must not claim hardware collection",
        errors,
    )
    require(
        demo_sequence.get("host_sequence_fixture") == rel(DEMO_HOST_STATUS_SEQUENCE),
        "screen_expression_demo_status operation must link demo host sequence fixture",
        errors,
    )
    require(
        demo_sequence.get("required_faces") == [
            "error",
            "happy",
            "idle",
            "listening",
            "low_battery",
            "recording",
            "sleepy",
            "speaking",
            "sync_complete",
            "thinking",
        ],
        "screen_expression_demo_status operation face list drifted",
        errors,
    )
    require(
        demo_sequence.get("accepted_status_pair_count") == 29,
        "screen_expression_demo_status operation accepted pair count drifted",
        errors,
    )
    require(
        demo_sequence.get("held_no_status_count") == 8,
        "screen_expression_demo_status operation held count drifted",
        errors,
    )
    require(
        demo_sequence.get("held_steps_contract") == "held_steps_emit_no_host_status",
        "screen_expression_demo_status operation missing held step contract",
        errors,
    )
    for field in ["request_id", "content_crc32", "diagnostic_arg3", "card_status", "dry_run_final_status"]:
        require(
            field in demo_sequence.get("required_fields", []),
            f"screen_expression_demo_status operation missing required field {field}",
            errors,
        )
    artifact_contract = data.get("artifact_contract", {})
    require(
        "partial_operation_count" in artifact_contract.get("evidence_for_hardware_gate", []),
        "artifact contract must include partial_operation_count in hardware-gate evidence fields",
        errors,
    )
    require(
        "partial_operation_count" in artifact_contract.get("partial_failure_evidence", ""),
        "artifact contract must explain partial failure evidence",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "real_bench_waits_for_final_card_status",
        "expect_real_panel_requires_rendered_ok",
        "default_bench_allows_no_panel_deferred_status",
        "accepted_final_identity_is_checked",
        "real_bench_collects_expression_final_status",
        "settings_sleepy_trigger_has_final_card_status",
        "real_bench_carries_host_expression_status_sequence",
        "six_face_sequence_baseline_is_linked",
        "real_bench_carries_demo_expression_status_sequence",
        "demo_sequence_baseline_covers_all_faces",
        "demo_sequence_held_steps_emit_no_status",
        "expression_request_identity_is_checked",
        "hardware_gate_can_reference_real_ble_artifact",
        "wba_real_ble_bench_can_reuse_contract",
        "wba_real_ble_bench_requires_screen_expression_status",
        "failed_bench_preserves_partial_operations",
    ]:
        require(acceptance.get(token) is True, f"real BLE screen bench acceptance missing {token}", errors)
    for command in data.get("validation_commands", []):
        if "\\tools\\" in str(command):
            tool = str(command).split("\\tools\\", 1)[1].split()[0]
            require((REPO_ROOT / "tools" / tool).exists(), f"real BLE screen bench command references missing tool {tool}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    contract = read(BLE_CONTRACT, errors)
    bringup = read(BRINGUP_STEPS, errors)
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    gate = read(PANEL_GATE, errors)
    evidence = read(PANEL_EVIDENCE_TEMPLATE, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)

    for token in [
        "--expect-real-panel",
        "--screen-final-timeout",
        "final_card_status",
        "real_panel_refresh_claimed",
        "settings_sleepy_screen_status",
        "partial_operation_count",
        "operations",
        "screen_expression_status",
        "companion-screen-expression-host-status-sequence.json",
        "screen_expression_demo_status",
        "companion-screen-expression-demo-host-status-sequence.json",
        "held_steps_emit_no_host_status",
    ]:
        require(token in contract, f"BLE contract missing real screen bench anchor {token}", errors)
    for token in [
        "--expect-real-panel",
        "companion-screen-real-ble-bench.json",
        "final_card_status",
        "settings_sleepy_screen_status",
        "partial_operation_count",
        "operations",
        "screen_expression_status",
        "companion-screen-expression-host-status-sequence.json",
        "screen_expression_demo_status",
        "companion-screen-expression-demo-host-status-sequence.json",
    ]:
        require(token in bringup, f"bringup steps missing real screen bench anchor {token}", errors)
    for token in [
        "real_ble_screen_final_status_bench",
        "real_ble_expression_status_sequence_contract",
        "companion-screen-real-ble-bench.json",
        "companion-screen-expression-host-status-sequence.json",
        "verify_expression_real_ble_screen_bench.py",
        "final_card_status",
        "settings_sleepy_screen_status",
        "partial_operation_count",
        "operations",
        "screen_expression_status",
        "screen_expression_demo_status",
        "companion-screen-expression-demo-host-status-sequence.json",
    ]:
        require(token in screen_doc, f"screen doc missing real BLE screen bench anchor {token}", errors)
    require("real BLE screen bench" in wba_rules, "WBA rules missing real BLE screen bench note", errors)
    require("settings_sleepy_screen_status" in wba_rules, "WBA rules missing settings sleepy bench note", errors)
    require("screen_expression_status" in wba_rules, "WBA rules missing screen expression status bench note", errors)
    require("screen_expression_demo_status" in wba_rules, "WBA rules missing screen expression demo status bench note", errors)
    require("partial_operation_count" in wba_rules, "WBA rules missing partial operation evidence note", errors)
    require("six-face" in wba_rules, "WBA rules missing six-face real bench note", errors)
    require(fixture_rel in gate, "panel hardware gate must link real BLE screen bench fixture", errors)
    require(fixture_rel in evidence, "panel evidence template must link real BLE screen bench fixture", errors)
    require(fixture_rel in index_text, "acceptance index must link real BLE screen bench fixture", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if item.get("id") == "real_ble_screen_final_status_bench"]
        require(len(items) == 1, "acceptance index must contain one real_ble_screen_final_status_bench item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "real_ble_screen_final_status_bench item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "real BLE screen bench item missing fixture", errors)
            require(
                "python .\\tools\\verify_expression_real_ble_screen_bench.py" in item.get("validation_commands", []),
                "real BLE screen bench item missing verifier command",
                errors,
            )
        sequence_items = [
            item for item in index.get("items", []) if item.get("id") == "real_ble_expression_status_sequence_contract"
        ]
        require(
            len(sequence_items) == 1,
            "acceptance index must contain one real_ble_expression_status_sequence_contract item",
            errors,
        )
        if sequence_items:
            item = sequence_items[0]
            require(item.get("status") == "PASS", "real BLE expression status sequence item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "real BLE expression sequence item missing fixture", errors)
            require(
                rel(HOST_STATUS_SEQUENCE) in item.get("evidence_paths", []),
                "real BLE expression sequence item missing host sequence fixture",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing real BLE screen bench fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic real BLE screen bench JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    expected = build_fixture()
    errors: list[str] = []

    check_real_bench_code(errors)
    check_fixture_data(expected, errors)
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion real BLE screen bench checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion real BLE screen bench verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
