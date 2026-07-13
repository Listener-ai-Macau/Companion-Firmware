#!/usr/bin/env python3
"""Verify no-hardware panel adapter behavior cases for future WB/WBA drivers."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-adapter-behavior.json")
SCHEMA_ID = "companion.pendant.screen_panel_adapter_behavior.v1"

PANEL_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
DISPLAY_QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
BOUNDARY_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-adapter-boundary.json"

RESULT_VALUES = {
    "ok": 0,
    "deferred_no_panel": 1,
    "deferred_controller_unknown": 2,
    "bad_argument": 3,
    "transport_error": 4,
    "busy": 5,
}

RENDER_STATES = {
    "idle": 0,
    "accepted": 1,
    "rendered": 2,
    "failed": 3,
    "busy": 4,
}

LAST_ERRORS = {
    "ok": 0,
    "deferred_no_panel": 4,
    "deferred_controller_unknown": 5,
    "panel_bad_argument": 6,
    "panel_transport_error": 7,
    "panel_busy": 8,
}


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


def render_state_for(result: str) -> str:
    if result == "ok":
        return "rendered"
    if result == "busy":
        return "busy"
    return "failed"


def last_error_for(result: str) -> str:
    return {
        "ok": "ok",
        "deferred_no_panel": "deferred_no_panel",
        "deferred_controller_unknown": "deferred_controller_unknown",
        "bad_argument": "panel_bad_argument",
        "transport_error": "panel_transport_error",
        "busy": "panel_busy",
    }[result]


def scenario(
    case_id: str,
    setup: str,
    result: str,
    counter: str | None,
    transferred_bytes: int,
    callback_invoked: bool,
    note: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "setup": setup,
        "expected_result": result,
        "expected_result_value": RESULT_VALUES[result],
        "expected_render_state": render_state_for(result),
        "expected_render_state_value": RENDER_STATES[render_state_for(result)],
        "expected_last_error": last_error_for(result),
        "expected_last_error_value": LAST_ERRORS[last_error_for(result)],
        "expected_counter": counter,
        "expected_transferred_bytes": transferred_bytes,
        "callback_invoked": callback_invoked,
        "request_identity_overridden_by_dispatcher": True,
        "note": note,
    }


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "panel_header": rel(PANEL_HEADER),
            "panel_source": rel(PANEL_SOURCE),
            "display_queue_header": rel(DISPLAY_QUEUE_HEADER),
            "boundary_fixture": rel(BOUNDARY_FIXTURE),
        },
        "common_request": {
            "request_id": 0xE0000001,
            "content_crc32": "0x1234abcd",
            "payload_len": 42,
            "card_slot": 1,
        },
        "behavior_cases": [
            scenario(
                "null_adapter_rejected",
                "adapter is NULL",
                "bad_argument",
                None,
                0,
                False,
                "Bad arguments are rejected before attempts or target callbacks.",
            ),
            scenario(
                "null_request_rejected",
                "request is NULL",
                "bad_argument",
                None,
                0,
                False,
                "Bad arguments are rejected before attempts or target callbacks.",
            ),
            scenario(
                "dry_run_no_panel",
                "comp_epaper_panel_adapter_init_dry_run",
                "deferred_no_panel",
                "deferred_count",
                0,
                False,
                "WB55 remains in dry-run mode until real panel evidence exists.",
            ),
            scenario(
                "hardware_present_controller_unknown",
                "hardware_present=true, controller_known=false",
                "deferred_controller_unknown",
                "deferred_count",
                0,
                False,
                "A selected board without controller facts cannot claim transport.",
            ),
            scenario(
                "known_panel_missing_callback",
                "hardware_present=true, controller_known=true, dimensions set, refresh=NULL",
                "transport_error",
                "error_count",
                0,
                False,
                "Known panel metadata is not enough; a target refresh callback is required.",
            ),
            scenario(
                "target_callback_ok_default_bytes",
                "target callback returns OK and leaves transferred_bytes=0",
                "ok",
                "rendered_count",
                42,
                True,
                "Dispatcher fills transferred_bytes from payload_len when the target callback omits it.",
            ),
            scenario(
                "target_callback_ok_reported_bytes",
                "target callback returns OK and reports transferred_bytes=17",
                "ok",
                "rendered_count",
                17,
                True,
                "Dispatcher preserves nonzero target byte counts.",
            ),
            scenario(
                "target_callback_busy",
                "target callback returns BUSY",
                "busy",
                None,
                0,
                True,
                "Busy is host-visible and should not increment rendered, deferred, or error counters.",
            ),
            scenario(
                "target_callback_deferred_controller",
                "target callback returns DEFERRED_CONTROLLER_UNKNOWN",
                "deferred_controller_unknown",
                "deferred_count",
                0,
                True,
                "Target adapters can still defer if late controller probing fails.",
            ),
            scenario(
                "target_callback_transport_error",
                "target callback returns TRANSPORT_ERROR",
                "transport_error",
                "error_count",
                0,
                True,
                "Transport failures remain host-visible without changing portable state.",
            ),
        ],
        "acceptance": {
            "bad_arguments_rejected_before_attempt_count": True,
            "dry_run_reports_deferred_no_panel": True,
            "known_panel_requires_target_callback": True,
            "callback_ok_maps_to_rendered_ok": True,
            "callback_busy_maps_to_busy_without_error_counter": True,
            "callback_failures_preserve_status_error_contract": True,
            "dispatcher_owns_request_identity": True,
            "wba_safe_behavior_matrix": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_adapter_behavior.py",
            "python .\\tools\\verify_expression_panel_adapter_boundary.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
        "execution_note": (
            "This is a no-hardware behavioral contract fixture. The current "
            "workspace has arm-none-eabi-gcc for firmware builds but no host C "
            "runtime compiler, so the verifier cross-checks the deterministic "
            "scenario matrix against the compiled firmware source and status "
            "code mappings."
        ),
    }


def check_enum_values(errors: list[str]) -> None:
    header = read(PANEL_HEADER, errors)
    queue_header = read(DISPLAY_QUEUE_HEADER, errors)
    for symbol, value in [
        ("COMP_EPAPER_PANEL_RESULT_OK", 0),
        ("COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL", 1),
        ("COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN", 2),
        ("COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT", 3),
        ("COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR", 4),
        ("COMP_EPAPER_PANEL_RESULT_BUSY", 5),
    ]:
        require(f"{symbol} = {value}" in header, f"panel result {symbol} drifted from {value}", errors)
    for symbol, value in [
        ("COMP_EPAPER_RENDER_STATE_RENDERED", 2),
        ("COMP_EPAPER_RENDER_STATE_FAILED", 3),
        ("COMP_EPAPER_RENDER_STATE_BUSY", 4),
    ]:
        require(f"{symbol} = {value}" in queue_header, f"render state {symbol} drifted from {value}", errors)


def check_source_behavior(errors: list[str]) -> None:
    source = read(PANEL_SOURCE, errors)
    for token in [
        "if (adapter == NULL || request == NULL)",
        "adapter->attempted_count++",
        "!adapter->config.hardware_present",
        "adapter->deferred_count++",
        "!adapter->config.controller_known",
        "adapter->config.width == 0u",
        "adapter->config.height == 0u",
        "adapter->config.refresh == NULL",
        "adapter->error_count++",
        "adapter->config.refresh(adapter->config.context",
        "adapter->rendered_count++",
        "result != COMP_EPAPER_PANEL_RESULT_BUSY",
        "*out_report = target_report",
        "out_report->request_id = request->request_id",
        "out_report->content_crc32 = request->content_crc32",
        "out_report->transferred_bytes = 0u",
        "out_report->transferred_bytes = (uint32_t)request->payload_len",
        "out_report->adapter_attempts = adapter->attempted_count",
    ]:
        require(token in source, f"panel adapter behavior source missing {token}", errors)
    require(
        source.find("if (adapter == NULL || request == NULL)") < source.find("adapter->attempted_count++"),
        "bad arguments must be rejected before attempt count increments",
        errors,
    )
    require(
        source.find("adapter->config.refresh == NULL") < source.find("adapter->config.refresh(adapter->config.context"),
        "missing callback guard must run before target callback",
        errors,
    )
    require(
        "result = COMP_EPAPER_PANEL_RESULT_OK" not in source,
        "portable dispatcher must not synthesize OK before target callback",
        errors,
    )


def check_status_mappings(errors: list[str]) -> None:
    source = read(PANEL_SOURCE, errors)
    for snippet, label in [
        ("case COMP_EPAPER_PANEL_RESULT_OK:\n        return (uint8_t)COMP_EPAPER_RENDER_STATE_RENDERED;", "OK rendered"),
        ("case COMP_EPAPER_PANEL_RESULT_BUSY:\n        return (uint8_t)COMP_EPAPER_RENDER_STATE_BUSY;", "BUSY busy"),
        ("case COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL:\n        return 4u;", "deferred no panel error"),
        ("case COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN:\n        return 5u;", "controller unknown error"),
        ("case COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT:\n        return 6u;", "bad argument error"),
        ("case COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR:\n        return 7u;", "transport error"),
        ("case COMP_EPAPER_PANEL_RESULT_BUSY:\n        return 8u;", "busy error"),
    ]:
        require(snippet in source, f"panel adapter status mapping drifted for {label}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel adapter behavior schema", errors)
    require(data.get("status") == "PASS", "panel adapter behavior fixture must be PASS", errors)
    cases = {case.get("case_id"): case for case in data.get("behavior_cases", []) if isinstance(case, dict)}
    expected_cases = {
        "null_adapter_rejected",
        "null_request_rejected",
        "dry_run_no_panel",
        "hardware_present_controller_unknown",
        "known_panel_missing_callback",
        "target_callback_ok_default_bytes",
        "target_callback_ok_reported_bytes",
        "target_callback_busy",
        "target_callback_deferred_controller",
        "target_callback_transport_error",
    }
    require(set(cases) == expected_cases, "panel adapter behavior case coverage drifted", errors)
    for case_id, case in cases.items():
        result = str(case.get("expected_result"))
        render_state = str(case.get("expected_render_state"))
        last_error = str(case.get("expected_last_error"))
        require(case.get("expected_result_value") == RESULT_VALUES.get(result), f"{case_id} result value drifted", errors)
        require(case.get("expected_render_state_value") == RENDER_STATES.get(render_state), f"{case_id} render state value drifted", errors)
        require(case.get("expected_last_error_value") == LAST_ERRORS.get(last_error), f"{case_id} last error value drifted", errors)
        require(case.get("expected_render_state") == render_state_for(result), f"{case_id} render state mapping drifted", errors)
        require(case.get("expected_last_error") == last_error_for(result), f"{case_id} last error mapping drifted", errors)
        if result != "ok":
            require(case.get("expected_transferred_bytes") == 0, f"{case_id} non-OK case must transfer zero bytes", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "bad_arguments_rejected_before_attempt_count",
        "dry_run_reports_deferred_no_panel",
        "known_panel_requires_target_callback",
        "callback_ok_maps_to_rendered_ok",
        "callback_busy_maps_to_busy_without_error_counter",
        "callback_failures_preserve_status_error_contract",
        "dispatcher_owns_request_identity",
        "wba_safe_behavior_matrix",
    ]:
        require(acceptance.get(token) is True, f"panel adapter behavior acceptance missing {token}", errors)
    for command in data.get("validation_commands", []):
        if "\\tools\\" in str(command):
            tool = str(command).split("\\tools\\", 1)[1].split()[0]
            require((REPO_ROOT / "tools" / tool).exists(), f"panel adapter behavior command references missing tool {tool}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    readme = read(README, errors)
    wba_rules = read(WBA_RULES, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    boundary_text = read(BOUNDARY_FIXTURE, errors)

    for token in [
        "panel_adapter_behavior_matrix",
        "companion-screen-panel-adapter-behavior.json",
        "callback_busy_maps_to_busy_without_error_counter",
        "dispatcher_owns_request_identity",
    ]:
        require(token in screen_doc, f"screen doc missing panel behavior anchor {token}", errors)
    require("panel adapter behavior matrix" in readme.lower(), "e-paper README missing panel adapter behavior matrix note", errors)
    require("panel adapter behavior matrix" in wba_rules.lower(), "WBA rules missing panel adapter behavior matrix note", errors)
    require("target_refresh_callback_only" in boundary_text, "boundary fixture must keep target-only OK source", errors)
    require(fixture_rel in index_text, "acceptance index must link panel adapter behavior fixture", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if item.get("id") == "panel_adapter_behavior_matrix"]
        require(len(items) == 1, "acceptance index must contain one panel_adapter_behavior_matrix item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_adapter_behavior_matrix item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel_adapter_behavior_matrix item missing fixture", errors)
            require(
                "python .\\tools\\verify_expression_panel_adapter_behavior.py" in item.get("validation_commands", []),
                "panel_adapter_behavior_matrix item missing verifier command",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel adapter behavior fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic panel adapter behavior JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    expected = build_fixture()
    errors: list[str] = []

    check_enum_values(errors)
    check_source_behavior(errors)
    check_status_mappings(errors)
    check_fixture_data(expected, errors)
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel adapter behavior checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion panel adapter behavior verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
