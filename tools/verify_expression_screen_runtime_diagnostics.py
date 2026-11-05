#!/usr/bin/env python3
"""Verify screen runtime diagnostics for WB55 and future WBA ports."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-runtime-diagnostics.json")
SCHEMA_ID = "companion.pendant.screen_runtime_diagnostics.v1"

DIAG_EVENTS = REPO_ROOT / "app" / "companion_pendant" / "diag_log" / "diag_log_events.h"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
SCREEN_RUNTIME_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.h"
SCREEN_RUNTIME_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.c"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
DECODE_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_runtime_diagnostic_decode.py"
DECODE_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-runtime-diagnostic-decode.json"

RUNTIME_EVENT_TOKEN = 'X(EPAPER, RUNTIME_SNAPSHOT, 0x03u, COMP_DIAG_SEV_INFO, "e_paper.runtime_snapshot")'


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
        "purpose": "Diagnostic event contract for publishing aggregate screen runtime stats without changing CardStatusV1.",
        "sources": {
            "diag_events": rel(DIAG_EVENTS),
            "wb55_integration": rel(APP_BLE),
            "screen_runtime_header": rel(SCREEN_RUNTIME_HEADER),
            "screen_runtime_source": rel(SCREEN_RUNTIME_SOURCE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
            "ble_contract": rel(BLE_CONTRACT),
        },
        "runtime_event": "e_paper.runtime_snapshot",
        "event_code": "COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT",
        "event_id": "0x03",
        "payload": {
            "arg0": "(expression.current << 16) | expression.last_signal",
            "arg1": "(display_queue.pending_count << 16) | display_queue.high_water_count",
            "arg2": "display_queue.dropped_count",
            "arg3": "(panel.deferred_count << 16) | panel.error_count",
        },
        "severity": "warn when panel.error_count != 0, otherwise info",
        "wb55_recording": {
            "source_snapshot": "comp_epaper_screen_runtime_snapshot",
            "record_function": "Companion_Display_RecordRuntimeSnapshot",
            "record_after_update_result": True,
        },
        "host_decoding": {
            "decoded_args": True,
            "decode_fixture": rel(DECODE_FIXTURE),
            "decode_verifier": rel(DECODE_VERIFIER),
        },
        "wba_contract": "WBA display tasks must preserve the same event name, event id, payload packing, and warning rule while replacing only target scheduler/BLE/panel glue.",
        "validation_commands": [
            "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
            "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected screen runtime diagnostics schema", errors)
    require(data.get("status") == "PASS", "runtime diagnostics fixture must be PASS", errors)
    require(data.get("runtime_event") == "e_paper.runtime_snapshot", "fixture missing runtime event name", errors)
    require(data.get("event_code") == "COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT", "fixture missing runtime event code", errors)
    require(data.get("event_id") == "0x03", "fixture missing runtime event id", errors)
    payload = data.get("payload", {})
    for key, value in {
        "arg0": "(expression.current << 16) | expression.last_signal",
        "arg1": "(display_queue.pending_count << 16) | display_queue.high_water_count",
        "arg2": "display_queue.dropped_count",
        "arg3": "(panel.deferred_count << 16) | panel.error_count",
    }.items():
        require(payload.get(key) == value, f"fixture payload {key} drifted", errors)
    require(
        data.get("severity") == "warn when panel.error_count != 0, otherwise info",
        "fixture missing runtime severity rule",
        errors,
    )
    wb55 = data.get("wb55_recording", {})
    require(wb55.get("source_snapshot") == "comp_epaper_screen_runtime_snapshot", "fixture missing source snapshot", errors)
    require(wb55.get("record_function") == "Companion_Display_RecordRuntimeSnapshot", "fixture missing record function", errors)
    require(wb55.get("record_after_update_result") is True, "fixture must record runtime after update_result", errors)
    host_decoding = data.get("host_decoding", {})
    require(host_decoding.get("decoded_args") is True, "fixture missing host decoded_args contract", errors)
    require(
        host_decoding.get("decode_verifier") == "tools/verify_expression_screen_runtime_diagnostic_decode.py",
        "fixture missing runtime diagnostic decode verifier",
        errors,
    )


def check_diag_event(errors: list[str]) -> None:
    diag_events = read(DIAG_EVENTS, errors)
    require(RUNTIME_EVENT_TOKEN in diag_events, f"diagnostic event contract missing {RUNTIME_EVENT_TOKEN}", errors)


def check_wb55_recording(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    for token in [
        "static uint32_t Companion_Display_PackRuntimePair(uint32_t high, uint32_t low)",
        "((high & 0xFFFFu) << 16) | (low & 0xFFFFu)",
        "static void Companion_Display_RecordRuntimeSnapshot",
        "COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT",
        "runtime_stats->panel.error_count != 0u ? COMP_DIAG_SEV_WARN",
        "runtime_stats->expression.current",
        "runtime_stats->expression.last_signal",
        "runtime_stats->display_queue.pending_count",
        "runtime_stats->display_queue.high_water_count",
        "runtime_stats->display_queue.dropped_count",
        "runtime_stats->panel.deferred_count",
        "runtime_stats->panel.error_count",
        "Companion_Display_RecordRuntimeSnapshot(&runtime_stats);",
    ]:
        require(token in app_ble, f"WB55 app_ble.c missing runtime diagnostic token {token}", errors)

    display_start = app_ble.find("static void Companion_Display_Task(void)\n{")
    display_end = app_ble.find("static uint32_t Companion_Display_NextExpressionRequestId", display_start)
    display_task = app_ble[display_start:display_end] if display_start >= 0 and display_end > display_start else ""
    require(display_task, "could not isolate Companion_Display_Task", errors)
    if display_task:
        snapshot_idx = display_task.find("comp_epaper_screen_runtime_snapshot(&s_companion_expression_state")
        update_idx = display_task.find("COMP_DIAG_EVT_EPAPER_UPDATE_RESULT")
        runtime_idx = display_task.find("Companion_Display_RecordRuntimeSnapshot(&runtime_stats);")
        status_idx = display_task.find("Companion_Gatt_PublishCardStatus")
        require(snapshot_idx >= 0, "display task must collect runtime snapshot", errors)
        require(update_idx >= 0, "display task must record update_result", errors)
        require(runtime_idx > update_idx, "runtime snapshot diagnostic must be recorded after update_result", errors)
        require(status_idx > runtime_idx, "runtime snapshot diagnostic must be recorded before final CardStatus publish", errors)


def check_runtime_sources(errors: list[str]) -> None:
    header = read(SCREEN_RUNTIME_HEADER, errors)
    source = read(SCREEN_RUNTIME_SOURCE, errors)
    for token in [
        "comp_epaper_screen_runtime_snapshot_t",
        "comp_epaper_expression_state_snapshot_t expression;",
        "comp_epaper_display_queue_snapshot_t display_queue;",
        "comp_epaper_panel_adapter_snapshot_t panel;",
    ]:
        require(token in header, f"screen_runtime.h missing diagnostics source token {token}", errors)
    for token in [
        "comp_epaper_expression_state_snapshot(expression_state",
        "comp_epaper_display_queue_snapshot(display_queue",
        "comp_epaper_panel_adapter_snapshot(panel_adapter",
    ]:
        require(token in source, f"screen_runtime.c missing diagnostics source token {token}", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    ble_contract = read(BLE_CONTRACT, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "screen_runtime_diagnostics",
        "Screen runtime diagnostics",
        "companion-screen-runtime-diagnostics.json",
        "verify_expression_screen_runtime_diagnostics.py",
        "verify_expression_screen_runtime_diagnostic_decode.py",
        "e_paper.runtime_snapshot",
    ]:
        require(token in screen_doc, f"screen expression doc missing runtime diagnostics anchor {token}", errors)
    for token in [
        "runtime snapshot diagnostic",
        "e_paper.runtime_snapshot",
        "(display_queue.pending_count << 16) | display_queue.high_water_count",
    ]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing runtime diagnostics anchor {token}", errors)
    for token in ["runtime diagnostics", "e_paper.runtime_snapshot", "verify_expression_screen_runtime_diagnostics.py"]:
        require(token.lower() in readme.lower(), f"e-paper README missing runtime diagnostics anchor {token}", errors)
    for token in ["e_paper.runtime_snapshot", "display_queue.pending_count", "panel.error_count"]:
        require(token in ble_contract, f"BLE contract missing runtime diagnostics anchor {token}", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if isinstance(item, dict)]
        matches = [item for item in items if item.get("id") == "screen_runtime_diagnostics"]
        require(len(matches) == 1, "acceptance index must contain one screen_runtime_diagnostics item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "screen_runtime_diagnostics item must be PASS", errors)
            require(
                "docs/validation/companion-screen-runtime-diagnostics.json" in item.get("evidence_paths", []),
                "screen_runtime_diagnostics item must link diagnostics fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py" in item.get("validation_commands", []),
                "screen_runtime_diagnostics item must run diagnostics verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing screen runtime diagnostics fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic runtime diagnostics fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_diag_event(errors)
    check_wb55_recording(errors)
    check_runtime_sources(errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion screen runtime diagnostics checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen runtime diagnostics verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
