#!/usr/bin/env python3
"""Verify the WB55 display task drains queued screen work safely."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-display-drain-contract.json")
SCHEMA_ID = "companion.pendant.screen_display_drain_contract.v1"

DISPLAY_QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
DISPLAY_QUEUE_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.c"
PANEL_ADAPTER_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
SCREEN_RUNTIME_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.h"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"


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


def isolate_function(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return ""


def require_order(text: str, tokens: list[str], label: str, errors: list[str]) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, f"{label} missing ordered token {token}", errors)
        if position < 0:
            return
        require(position > cursor, f"{label} token out of order: {token}", errors)
        cursor = position


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Display task drain/reschedule contract for WB55 and future WBA panel adapters.",
        "sources": {
            "display_queue_header": rel(DISPLAY_QUEUE_HEADER),
            "display_queue_source": rel(DISPLAY_QUEUE_SOURCE),
            "panel_adapter_header": rel(PANEL_ADAPTER_HEADER),
            "screen_runtime_header": rel(SCREEN_RUNTIME_HEADER),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "queue_contract": {
            "depth": 4,
            "payload_max_bytes": 236,
            "sequence_starts_at": 1,
            "fifo_indices": ["read_index", "write_index", "count"],
            "drop_counter": "dropped_count",
            "high_water_counter": "high_water_count",
            "resource_generation": "active_resource_revision",
            "generation_switch_counter": "generation_switch_count",
            "last_generation_discard_counter": "last_stale_generation_discarded",
            "stale_generation_counter": "stale_generation_discard_count",
        },
        "display_task_contract": {
            "task": "Companion_Display_Task",
            "pre_drain_tick": "Companion_Display_ProcessExpressionTick",
            "dequeue_api": "comp_epaper_display_queue_dequeue",
            "target_refresh_api": "comp_epaper_panel_adapter_refresh_card",
            "render_state_map": "comp_epaper_panel_adapter_render_state",
            "last_error_map": "comp_epaper_panel_adapter_status_error",
            "runtime_snapshot_api": "comp_epaper_screen_runtime_snapshot",
            "update_result_event": "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
            "runtime_snapshot_event": "COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT",
            "final_status_api": "Companion_Gatt_PublishCardStatus",
            "reschedule_condition": "runtime_stats.display_queue.pending_count != 0u",
        },
        "acceptance": {
            "fifo_sequence_identity_preserved": True,
            "dequeue_happens_once_before_panel_refresh": True,
            "panel_result_maps_to_final_card_status": True,
            "runtime_snapshot_recorded_before_final_card_status": True,
            "pending_work_reschedules_display_task": True,
            "request_carries_resource_revision": True,
            "generation_change_discards_stale_pending_work": True,
            "display_result_marks_coherent_generation": True,
            "empty_queue_returns_without_panel_refresh": True,
            "wba_display_task_can_reuse_contract": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_display_drain.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_display_queue_telemetry.py",
            "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_queue_source(errors: list[str]) -> None:
    header = read(DISPLAY_QUEUE_HEADER, errors)
    source = read(DISPLAY_QUEUE_SOURCE, errors)
    for token in [
        "COMP_EPAPER_DISPLAY_QUEUE_DEPTH 4u",
        "COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES 236u",
        "size_t read_index;",
        "size_t write_index;",
        "size_t count;",
        "uint32_t next_sequence;",
        "uint32_t dropped_count;",
        "uint32_t resource_revision;",
        "uint32_t active_resource_revision;",
        "uint32_t generation_switch_count;",
        "uint32_t last_stale_generation_discarded;",
        "uint32_t stale_generation_discard_count;",
        "comp_epaper_display_queue_set_resource_revision",
        "bool comp_epaper_display_queue_dequeue",
    ]:
        require(token in header, f"display_queue.h missing drain contract token {token}", errors)
    require_order(
        source,
        [
            "queue->next_sequence = 1u;",
            "comp_epaper_display_queue_enqueue_card_write",
        ],
        "display_queue init/enqueue",
        errors,
    )
    require_order(
        source,
        [
            "(*out_request)->sequence = queue->next_sequence++;",
            "comp_epaper_queue_commit(queue);",
        ],
        "display queue reserve/commit",
        errors,
    )
    require_order(
        source,
        [
            "*out_request = queue->items[queue->read_index];",
            "memset(&queue->items[queue->read_index], 0, sizeof(queue->items[queue->read_index]));",
            "queue->read_index = comp_epaper_queue_advance(queue->read_index);",
            "queue->count--;",
            "return true;",
        ],
        "display queue dequeue",
        errors,
    )
    for token in [
        "queue->dropped_count++;",
        "queue->high_water_count = queue->count;",
        "out_snapshot->pending_count = queue->count;",
        "out_snapshot->next_sequence = queue->next_sequence;",
        "out_snapshot->active_resource_revision = queue->active_resource_revision;",
        "out_snapshot->generation_switch_count = queue->generation_switch_count;",
        "out_snapshot->last_stale_generation_discarded",
        "out_snapshot->stale_generation_discard_count",
        "(*out_request)->resource_revision = queue->active_resource_revision;",
        "queue->last_stale_generation_discarded = (uint32_t)discarded;",
        "queue->generation_switch_count++;",
        "queue->stale_generation_discard_count += (uint32_t)discarded;",
        "request->resource_revision = queue->active_resource_revision;",
    ]:
        require(token in source, f"display_queue.c missing drain telemetry token {token}", errors)


def check_display_task(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    display_task = isolate_function(app_ble, "static void Companion_Display_Task(void)\n{")
    require(display_task, "could not isolate Companion_Display_Task", errors)
    if not display_task:
        return
    require_order(
        display_task,
        [
            "Companion_Display_ProcessExpressionTick();",
            "if (!comp_epaper_display_queue_dequeue(&s_companion_display_queue, &request))",
            "return;",
            "panel_result = comp_epaper_panel_adapter_refresh_card(&s_companion_panel_adapter",
            "render_state = comp_epaper_panel_adapter_render_state(panel_result);",
            "status_error = comp_epaper_panel_adapter_status_error(panel_result);",
            "comp_epaper_screen_runtime_snapshot(&s_companion_expression_state",
            "comp_diag_log_record_code(COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
            "display_result id=%lu kind=%u resource_revision=%lu active_revision=%lu coherent_generation=%u",
            "Companion_Display_RecordRuntimeSnapshot(&runtime_stats);",
            "Companion_Gatt_PublishCardStatus(request.card_slot",
            "if (runtime_stats.display_queue.pending_count != 0u)",
            "UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);",
        ],
        "Companion_Display_Task",
        errors,
    )
    require(
        display_task.count("comp_epaper_display_queue_dequeue") == 1,
        "display task must dequeue at most one request per scheduler pass",
        errors,
    )
    for token in [
        "request.request_id",
        "request.content_crc32",
        "request.card_slot",
        "request.resource_revision",
        "request.resource_revision == runtime_stats.display_queue.active_resource_revision ? 1u : 0u",
        "runtime_stats.panel.attempted_count",
        "runtime_stats.display_queue.active_resource_revision",
        "runtime_stats.display_queue.generation_switch_count",
        "runtime_stats.display_queue.last_stale_generation_discarded",
        "runtime_stats.display_queue.stale_generation_discard_count",
        "(uint32_t)panel_result",
        "render_state",
        "status_error",
    ]:
        require(token in display_task, f"display task missing CardStatus/diagnostic identity token {token}", errors)


def check_related_contracts(errors: list[str]) -> None:
    panel_header = read(PANEL_ADAPTER_HEADER, errors)
    runtime_header = read(SCREEN_RUNTIME_HEADER, errors)
    for token in [
        "comp_epaper_panel_adapter_refresh_card",
        "comp_epaper_panel_adapter_render_state",
        "comp_epaper_panel_adapter_status_error",
        "COMP_EPAPER_PANEL_RESULT_BUSY",
    ]:
        require(token in panel_header, f"panel adapter header missing drain dependency {token}", errors)
    for token in [
        "comp_epaper_screen_runtime_snapshot_t",
        "comp_epaper_display_queue_snapshot_t display_queue;",
        "comp_epaper_panel_adapter_snapshot_t panel;",
    ]:
        require(token in runtime_header, f"screen runtime header missing drain dependency {token}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(SCREEN_DOC, errors).split()).lower()
    wba_rules = " ".join(read(WBA_RULES, errors).split()).lower()
    readme = " ".join(read(README, errors).split()).lower()
    for token in [
        "screen display drain contract",
        "screen_display_drain_contract",
        "companion-screen-display-drain-contract.json",
        "verify_expression_display_drain.py",
        "companion_display_task",
    ]:
        require(token.lower() in screen_doc, f"screen doc missing display drain anchor {token}", errors)
    for token in [
        "display drain contract",
        "verify_expression_display_drain.py",
        "pending work reschedules",
    ]:
        require(token.lower() in wba_rules, f"WBA rules missing display drain anchor {token}", errors)
    for token in [
        "display drain contract",
        "verify_expression_display_drain.py",
    ]:
        require(token.lower() in readme, f"e-paper README missing display drain anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing display drain fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update deterministic display drain fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_queue_source(errors)
    check_display_task(errors)
    check_related_contracts(errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion display drain contract checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion display drain contract verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
