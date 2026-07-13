#!/usr/bin/env python3
"""Verify host-observable screen status and diagnostic contracts."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-status-observability.json")
SCHEMA_ID = "companion.pendant.screen_status_observability.v1"

GATT_HEADER = REPO_ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.h"
DISPLAY_QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
DISPLAY_QUEUE_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.c"
PANEL_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
DIAG_EVENTS = REPO_ROOT / "app" / "companion_pendant" / "diag_log" / "diag_log_events.h"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
BLE_MATRIX = REPO_ROOT / "docs" / "validation" / "companion_ble_matrix.json"

RENDER_STATES = {
    "idle": 0,
    "accepted": 1,
    "rendered": 2,
    "failed": 3,
    "busy": 4,
}

LAST_ERRORS = {
    "ok": 0,
    "queue_full": 1,
    "payload_too_long": 2,
    "bad_argument": 3,
    "deferred_no_panel": 4,
    "deferred_controller_unknown": 5,
    "panel_bad_argument": 6,
    "panel_transport_error": 7,
    "panel_busy": 8,
    "unsupported_expression": 9,
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


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "gatt_header": rel(GATT_HEADER),
            "display_queue_header": rel(DISPLAY_QUEUE_HEADER),
            "display_queue_source": rel(DISPLAY_QUEUE_SOURCE),
            "panel_adapter": rel(PANEL_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "diag_events": rel(DIAG_EVENTS),
            "ble_contract": rel(BLE_CONTRACT),
            "screen_acceptance": rel(SCREEN_DOC),
            "ble_matrix": rel(BLE_MATRIX),
        },
        "card_status_v1": {
            "fields": [
                "schema_version",
                "card_slot",
                "render_state",
                "last_error",
                "request_id",
                "content_crc32",
                "refresh_count",
            ],
            "render_states": RENDER_STATES,
            "last_errors": LAST_ERRORS,
        },
        "observable_sequences": [
            {
                "name": "initial_status_read",
                "steps": [
                    {
                        "card_slot": 0,
                        "render_state": "idle",
                        "last_error": "ok",
                        "request_id": 0,
                        "meaning": "published by Companion_Gatt_PublishInitialState before any display request",
                    }
                ],
            },
            {
                "name": "boot_idle_dry_run",
                "steps": [
                    {
                        "card_slot": 1,
                        "request_id_prefix": "0xE",
                        "render_state": "accepted",
                        "last_error": "ok",
                        "diag_event": "e_paper.render_request",
                    },
                    {
                        "card_slot": 1,
                        "request_id": "same_as_accepted",
                        "content_crc32": "same_as_accepted",
                        "render_state": "failed",
                        "last_error": "deferred_no_panel",
                        "diag_event": "e_paper.update_result",
                        "runtime_diag_event": "e_paper.runtime_snapshot",
                    },
                ],
            },
            {
                "name": "host_card_write_dry_run",
                "steps": [
                    {
                        "card_slot": "CardWriteV1.card_slot",
                        "request_id": "CardWriteV1.request_id",
                        "render_state": "accepted",
                        "last_error": "ok",
                        "diag_event": "e_paper.render_request",
                    },
                    {
                        "card_slot": "same_as_write",
                        "request_id": "same_as_write",
                        "content_crc32": "same_as_write",
                        "render_state": "failed",
                        "last_error": "deferred_no_panel",
                        "diag_event": "e_paper.update_result",
                        "runtime_diag_event": "e_paper.runtime_snapshot",
                    },
                ],
            },
            {
                "name": "host_expression_status_fixture",
                "steps": [
                    {
                        "card_slot": 1,
                        "events": [
                            "boot_idle",
                            "settings.display_off",
                            "recording_fsm.start_request",
                            "battery_charging.sample.low",
                            "recording_fsm.session_finished",
                            "errors.fault",
                        ],
                        "render_state": "accepted_then_failed",
                        "last_error": "ok_then_deferred_no_panel",
                        "content_crc32": "comp_epaper_expression_decision_crc32",
                        "diag_arg3": "(expression_id << 16) | signal_id",
                    },
                ],
            },
        ],
        "acceptance": {
            "card_status_read_returns_latest_status": True,
            "accepted_and_final_status_preserve_request_identity": True,
            "dry_run_no_panel_is_observable": True,
            "diagnostic_events_pair_with_card_status": True,
            "runtime_snapshot_diagnostic_preserves_card_status": True,
            "refresh_count_is_monotonic": True,
            "expression_status_fixture_correlates_diag_payload": True,
            "expression_status_fixture_covers_extended_faces": True,
        },
    }


def check_gatt_status_struct(errors: list[str]) -> None:
    header = read(GATT_HEADER, errors)
    for token in [
        "typedef struct {",
        "companion_gatt_card_status_v1_t",
        "uint8_t schema_version;",
        "uint8_t card_slot;",
        "uint8_t render_state;",
        "uint8_t last_error;",
        "uint32_t request_id;",
        "uint32_t content_crc32;",
        "uint32_t refresh_count;",
        "companion_gatt_parse_card_status_v1",
    ]:
        require(token in header, f"GATT CardStatusV1 contract missing {token}", errors)


def check_render_and_error_codes(errors: list[str]) -> None:
    queue_header = read(DISPLAY_QUEUE_HEADER, errors)
    queue_source = read(DISPLAY_QUEUE_SOURCE, errors)
    panel_source = read(PANEL_SOURCE, errors)

    for symbol, value in [
        ("COMP_EPAPER_RENDER_STATE_IDLE", 0),
        ("COMP_EPAPER_RENDER_STATE_ACCEPTED", 1),
        ("COMP_EPAPER_RENDER_STATE_RENDERED", 2),
        ("COMP_EPAPER_RENDER_STATE_FAILED", 3),
        ("COMP_EPAPER_RENDER_STATE_BUSY", 4),
    ]:
        require(f"{symbol} = {value}" in queue_header, f"render state {symbol} drifted from {value}", errors)

    for snippet, name in [
        ("case COMP_EPAPER_DISPLAY_QUEUE_FULL:\n        return 1u;", "queue_full"),
        ("case COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG:\n        return 2u;", "payload_too_long"),
        ("case COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT:\n        return 3u;", "bad_argument"),
        ("case COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION:\n        return 9u;", "unsupported_expression"),
    ]:
        require(snippet in queue_source, f"display queue last_error mapping drifted for {name}", errors)

    for snippet, name in [
        ("case COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL:\n        return 4u;", "deferred_no_panel"),
        ("case COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN:\n        return 5u;", "deferred_controller_unknown"),
        ("case COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT:\n        return 6u;", "panel_bad_argument"),
        ("case COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR:\n        return 7u;", "panel_transport_error"),
        ("case COMP_EPAPER_PANEL_RESULT_BUSY:\n        return 8u;", "panel_busy"),
    ]:
        require(snippet in panel_source, f"panel adapter last_error mapping drifted for {name}", errors)


def check_wb55_observability(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    diag_events = read(DIAG_EVENTS, errors)
    for token in [
        "static companion_gatt_card_status_v1_t s_companion_gatt_card_status",
        "static uint32_t s_companion_gatt_card_refresh_count",
        "Companion_Gatt_PublishCardStatus(0u, 0u, 0u, 0u, 0u)",
        "case COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS:",
        "(const uint8_t *)&s_companion_gatt_card_status",
        "s_companion_gatt_card_status.card_slot = card_slot;",
        "s_companion_gatt_card_status.render_state = render_state;",
        "s_companion_gatt_card_status.last_error = last_error;",
        "s_companion_gatt_card_status.request_id = request_id;",
        "s_companion_gatt_card_status.content_crc32 = content_crc32;",
        "s_companion_gatt_card_status.refresh_count = ++s_companion_gatt_card_refresh_count;",
        "Companion_Display_EnqueueExpressionSignal(COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE",
        "COMP_DIAG_EVT_EPAPER_RENDER_REQUEST",
        "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
        "COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT",
        "Companion_Display_RecordRuntimeSnapshot",
        "((uint32_t)decision->expression << 16) |",
    ]:
        require(token in app_ble, f"WB55 screen observability missing {token}", errors)

    card_write_start = app_ble.find("case COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE:")
    recording_start = app_ble.find("case COMPANION_GATT_CHAR_RECORDING_CONTROL:", card_write_start)
    card_write = app_ble[card_write_start:recording_start] if card_write_start >= 0 and recording_start > card_write_start else ""
    require(card_write, "could not isolate CardWrite handler", errors)
    if card_write:
        for token in [
            "Companion_Gatt_PublishCardStatus(",
            "request.card_slot",
            "request.request_id",
            "(uint8_t)COMP_EPAPER_RENDER_STATE_ACCEPTED",
            "content_crc32",
            "UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID",
        ]:
            require(token in card_write, f"CardWrite accepted status missing {token}", errors)

    display_start = app_ble.find("static void Companion_Display_Task(void)\n{")
    helper_start = app_ble.find("static uint32_t Companion_Display_NextExpressionRequestId", display_start)
    display_task = app_ble[display_start:helper_start] if display_start >= 0 and helper_start > display_start else ""
    require(display_task, "could not isolate Companion_Display_Task", errors)
    if display_task:
        for token in [
            "comp_epaper_panel_adapter_refresh_card",
            "comp_epaper_panel_adapter_render_state",
            "comp_epaper_panel_adapter_status_error",
            "request.card_slot",
            "request.request_id",
            "request.content_crc32",
            "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
            "Companion_Display_RecordRuntimeSnapshot(&runtime_stats)",
        ]:
            require(token in display_task, f"display task final status missing {token}", errors)

    for token in [
        'X(EPAPER, RENDER_REQUEST, 0x01u, COMP_DIAG_SEV_INFO, "e_paper.render_request")',
        'X(EPAPER, UPDATE_RESULT, 0x02u, COMP_DIAG_SEV_INFO, "e_paper.update_result")',
        'X(EPAPER, RUNTIME_SNAPSHOT, 0x03u, COMP_DIAG_SEV_INFO, "e_paper.runtime_snapshot")',
    ]:
        require(token in diag_events, f"diagnostic event contract missing {token}", errors)


def check_docs_and_host_fixture(errors: list[str]) -> None:
    contract = read(BLE_CONTRACT, errors)
    screen_doc = read(SCREEN_DOC, errors)
    matrix_text = read(BLE_MATRIX, errors)
    for token in [
        "CardStatusV1 Observability",
        "render_state",
        "last_error",
        "deferred_no_panel",
        "e_paper.render_request",
        "e_paper.update_result",
        "e_paper.runtime_snapshot",
        "display_queue.pending_count",
        "(expression_id << 16) | signal_id",
        "low-battery",
        "sync-complete",
        "error expressions",
    ]:
        require(token in contract, f"BLE contract missing screen status anchor {token}", errors)
    for token in [
        "Screen status observability",
        "Host BLE ExpressionV1 status fixture",
        "Host BLE ExpressionV1 extended status coverage",
        "host_ble_expression_extended_status_fixture",
        "screen_expression_status",
        "host_expression_status_extended_faces",
        "companion-screen-status-observability.json",
        "verify_expression_status_observability.py",
        "Screen runtime diagnostics",
        "e_paper.runtime_snapshot",
    ]:
        require(token in screen_doc, f"screen expression doc missing observability anchor {token}", errors)
    if matrix_text:
        matrix = json.loads(matrix_text)
        card = matrix.get("operation_coverage", {}).get("card_write", {})
        require(card.get("card_status", {}).get("render_state_name") == "accepted", "BLE fixture missing accepted card_status", errors)
        require(
            card.get("dry_run_final_status", {}).get("last_error_name") == "deferred_no_panel",
            "BLE fixture missing dry-run no-panel final status",
            errors,
        )
        expression = matrix.get("operation_coverage", {}).get("screen_expression_status", {})
        require(expression.get("status") == "PASS", "BLE fixture missing screen expression status operation", errors)
        require(
            expression.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
            "BLE fixture missing expression diagnostic arg3 model",
            errors,
        )
        steps = expression.get("steps", [])
        step_events = {str(step.get("event")) for step in steps if isinstance(step, dict)}
        require(
            {
                "boot_idle",
                "settings.display_off",
                "recording_fsm.start_request",
                "battery_charging.sample.low",
                "recording_fsm.session_finished",
                "errors.fault",
            } <= step_events,
            "BLE fixture missing extended expression status coverage",
            errors,
        )
        step_expressions = {str(step.get("expression")) for step in steps if isinstance(step, dict)}
        require(
            {"idle", "sleepy", "recording", "low_battery", "sync_complete", "error"} <= step_expressions,
            "BLE fixture missing extended ExpressionV1 face coverage",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing screen status fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic status observability fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_gatt_status_struct(errors)
    check_render_and_error_codes(errors)
    check_wb55_observability(errors)
    check_docs_and_host_fixture(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen status observability checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen status observability verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
