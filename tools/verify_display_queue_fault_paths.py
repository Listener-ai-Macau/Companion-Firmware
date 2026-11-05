#!/usr/bin/env python3
"""Verify no-hardware display queue fault paths and host-visible status."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-display-queue-faults.json")
SCHEMA_ID = "companion.pendant.screen_display_queue_faults.v1"

QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
QUEUE_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "display_queue_header": rel(QUEUE_HEADER),
            "display_queue_source": rel(QUEUE_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
        },
        "queue_contract": {
            "depth": 4,
            "payload_max_bytes": 236,
            "result_codes": {
                "ok": 0,
                "queue_full": 1,
                "payload_too_long": 2,
                "bad_argument": 3,
                "unsupported_expression": 4,
            },
            "card_status_last_errors": {
                "ok": 0,
                "queue_full": 1,
                "payload_too_long": 2,
                "bad_argument": 3,
                "unsupported_expression": 9,
            },
            "render_states": {
                "accepted": 1,
                "failed": 3,
                "busy": 4,
            },
        },
        "fault_scenarios": [
            {
                "scenario": "card_write_queue_full",
                "precondition": "pending queue count equals depth",
                "queue_result": "queue_full",
                "render_state": "busy",
                "last_error": "queue_full",
                "dropped_count_delta": 1,
                "accepted_status_published": False,
                "final_status_published": True,
                "diagnostic_event": "e_paper.update_result",
            },
            {
                "scenario": "card_write_payload_too_long",
                "precondition": "CardWriteV1 content length is 237 bytes",
                "queue_result": "payload_too_long",
                "render_state": "failed",
                "last_error": "payload_too_long",
                "dropped_count_delta": 1,
                "accepted_status_published": False,
                "final_status_published": True,
                "diagnostic_event": "e_paper.update_result",
            },
            {
                "scenario": "expression_queue_full_rollback",
                "precondition": "recording-start signal is accepted by state model but display queue is full",
                "queue_result": "queue_full",
                "render_state": "busy",
                "last_error": "queue_full",
                "state_rollback_required": True,
                "previous_expression": "idle",
                "attempted_expression": "recording",
                "visible_expression_after_failure": "idle",
                "diagnostic_event": "e_paper.update_result",
            },
            {
                "scenario": "expression_unsupported_rejected",
                "precondition": "display queue receives a decision whose expression enum is unsupported",
                "queue_result": "unsupported_expression",
                "render_state": "failed",
                "last_error": "unsupported_expression",
                "dropped_count_delta": 1,
                "accepted_status_published": False,
                "api_boundary": "comp_epaper_display_queue_enqueue_expression",
            },
        ],
        "acceptance": {
            "queue_full_reports_busy": True,
            "payload_too_long_reports_failed": True,
            "unsupported_expression_reports_failed": True,
            "expression_state_rolls_back_on_enqueue_failure": True,
            "fault_paths_emit_update_result_diagnostics": True,
            "wba_safe_fault_contract": True,
        },
    }


def check_queue_contract(errors: list[str]) -> None:
    header = read(QUEUE_HEADER)
    source = read(QUEUE_SOURCE)
    for token in [
        "#define COMP_EPAPER_DISPLAY_QUEUE_DEPTH 4u",
        "#define COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES 236u",
        "COMP_EPAPER_DISPLAY_QUEUE_FULL = 1",
        "COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG = 2",
        "COMP_EPAPER_DISPLAY_QUEUE_BAD_ARGUMENT = 3",
        "COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION = 4",
        "COMP_EPAPER_RENDER_STATE_FAILED = 3",
        "COMP_EPAPER_RENDER_STATE_BUSY = 4",
    ]:
        require(token in header, f"display_queue.h missing queue fault contract token {token}", errors)
    for token in [
        "queue->count >= COMP_EPAPER_DISPLAY_QUEUE_DEPTH",
        "queue->dropped_count++",
        "return COMP_EPAPER_DISPLAY_QUEUE_FULL",
        "payload_len > COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES",
        "return COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG",
        "!comp_epaper_expression_is_supported(decision->expression)",
        "return COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION",
        "case COMP_EPAPER_DISPLAY_QUEUE_FULL:",
        "return 1u;",
        "case COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG:",
        "return 2u;",
        "case COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION:",
        "return 9u;",
    ]:
        require(token in source, f"display_queue.c missing queue fault token {token}", errors)


def check_wb55_fault_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE)
    for token in [
        "comp_epaper_display_queue_status_error(queue_result)",
        "queue_result == COMP_EPAPER_DISPLAY_QUEUE_FULL",
        "(uint8_t)COMP_EPAPER_RENDER_STATE_BUSY",
        "(uint8_t)COMP_EPAPER_RENDER_STATE_FAILED",
        "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
        "comp_epaper_display_queue_snapshot(&s_companion_display_queue",
        "queue_stats.dropped_count",
        "Companion_Gatt_PublishCardStatus(request.card_slot",
        "s_companion_expression_state = *previous_state",
        "Companion_Gatt_PublishCardStatus(COMPANION_EPAPER_EXPRESSION_CARD_SLOT",
    ]:
        require(token in app_ble, f"app_ble.c missing queue fault integration token {token}", errors)

    card_write_start = app_ble.find("case COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE:")
    recording_start = app_ble.find("case COMPANION_GATT_CHAR_RECORDING_CONTROL:", card_write_start)
    card_write = app_ble[card_write_start:recording_start] if card_write_start >= 0 and recording_start > card_write_start else ""
    require(card_write, "could not isolate CardWrite handler", errors)
    if card_write:
        for token in [
            "comp_epaper_display_queue_enqueue_card_write",
            "queue_result == COMP_EPAPER_DISPLAY_QUEUE_OK",
            "comp_epaper_display_queue_status_error(queue_result)",
            "COMP_EPAPER_DISPLAY_QUEUE_FULL",
            "COMP_EPAPER_RENDER_STATE_BUSY",
            "COMP_EPAPER_RENDER_STATE_FAILED",
            "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
        ]:
            require(token in card_write, f"CardWrite fault path missing {token}", errors)

    helper_region_start = app_ble.find("static void Companion_Display_ProcessExpressionTick(void)\n{")
    expression_start = app_ble.find(
        "static void Companion_Display_EnqueueExpressionDecision",
        helper_region_start,
    )
    expression_end = app_ble.find("static void Companion_Display_EnqueueExpressionSignal", expression_start)
    expression_path = app_ble[expression_start:expression_end] if expression_start >= 0 and expression_end > expression_start else ""
    require(expression_path, "could not isolate expression enqueue helper", errors)
    if expression_path:
        for token in [
            "comp_epaper_display_queue_enqueue_expression",
            "s_companion_expression_state = *previous_state",
            "COMP_EPAPER_DISPLAY_QUEUE_FULL",
            "COMP_EPAPER_RENDER_STATE_BUSY",
            "COMP_EPAPER_RENDER_STATE_FAILED",
            "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
        ]:
            require(token in expression_path, f"expression fault path missing {token}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC)
    wba_rules = read(WBA_RULES)
    for token in [
        "Display queue fault paths",
        "display_queue_fault_paths",
        "companion-screen-display-queue-faults.json",
        "expression_state_rolls_back_on_enqueue_failure",
    ]:
        require(token in screen_doc, f"screen expression doc missing fault-path anchor {token}", errors)
    for token in [
        "display queue fault paths",
        "queue_full",
        "payload_too_long",
        "unsupported_expression",
    ]:
        require(token in wba_rules.lower(), f"WBA rules missing fault-path anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing display queue fault fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic display queue fault fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [QUEUE_HEADER, QUEUE_SOURCE, APP_BLE, SCREEN_DOC, WBA_RULES]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture()
    if not errors:
        check_queue_contract(errors)
        check_wb55_fault_integration(errors)
        check_docs(errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)
    if errors:
        print("FAIL: Companion display queue fault checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion display queue fault paths verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
