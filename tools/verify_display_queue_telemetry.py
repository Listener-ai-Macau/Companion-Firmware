#!/usr/bin/env python3
"""Verify display queue telemetry stays portable and WBA-safe."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-display-queue-telemetry.json")
SCHEMA_ID = "companion.pendant.screen_display_queue_telemetry.v1"

QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
QUEUE_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"


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
        "purpose": "Portable display queue telemetry for WB55 bring-up and future WBA panel scheduler pressure checks.",
        "sources": {
            "display_queue_header": rel(QUEUE_HEADER),
            "display_queue_source": rel(QUEUE_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "telemetry_fields": {
            "pending_count": "current queued display requests",
            "high_water_count": "largest pending count since queue init",
            "queue_depth": "portable compile-time queue capacity mirrored into the stats snapshot",
            "payload_max_bytes": "portable CardWriteV1 payload bound mirrored into the stats snapshot",
            "dropped_count": "requests rejected by full queue, oversized payload, or unsupported expression",
            "next_sequence": "monotonic in-memory request ordering counter",
        },
        "contract": {
            "depth": 4,
            "payload_max_bytes": 236,
            "snapshot_api": "comp_epaper_display_queue_snapshot",
            "high_water_initial": 0,
            "high_water_updates_after_commit": True,
            "high_water_never_exceeds_depth": True,
            "dequeue_does_not_reduce_high_water": True,
            "null_queue_returns_zero": True,
            "snapshot_null_safe": True,
            "platform_free": True,
            "host_status_unchanged": "CardStatusV1 remains the host-facing latest request status; telemetry does not add a GATT surface yet.",
        },
        "wb55_observability": {
            "render_request_arg2": "snapshot.pending_count",
            "update_result_arg2": "snapshot.dropped_count",
            "stats_snapshot_api": "comp_epaper_display_queue_snapshot",
            "high_water_api": "comp_epaper_display_queue_high_water_count",
        },
        "validation_commands": [
            "python .\\tools\\verify_display_queue_telemetry.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_display_queue_fault_paths.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected display queue telemetry schema", errors)
    require(data.get("status") == "PASS", "display queue telemetry fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("depth") == 4, "telemetry contract queue depth drifted", errors)
    require(contract.get("payload_max_bytes") == 236, "telemetry contract payload bound drifted", errors)
    require(
        contract.get("snapshot_api") == "comp_epaper_display_queue_snapshot",
        "telemetry contract missing queue snapshot API",
        errors,
    )
    require(contract.get("high_water_initial") == 0, "telemetry contract initial high-water drifted", errors)
    require(contract.get("high_water_updates_after_commit") is True, "telemetry contract must update high-water after commit", errors)
    require(contract.get("dequeue_does_not_reduce_high_water") is True, "telemetry contract must preserve high-water after dequeue", errors)
    require(contract.get("null_queue_returns_zero") is True, "telemetry contract must keep null queue reads safe", errors)
    require(contract.get("snapshot_null_safe") is True, "telemetry contract must keep snapshot null-safe", errors)
    require(
        data.get("wb55_observability", {}).get("stats_snapshot_api") == "comp_epaper_display_queue_snapshot",
        "telemetry fixture missing snapshot API",
        errors,
    )
    require(
        data.get("wb55_observability", {}).get("high_water_api") == "comp_epaper_display_queue_high_water_count",
        "telemetry fixture missing high-water API",
        errors,
    )


def check_queue_code(errors: list[str]) -> None:
    header = read(QUEUE_HEADER, errors)
    source = read(QUEUE_SOURCE, errors)
    for token in [
        "size_t high_water_count;",
        "comp_epaper_display_queue_snapshot_t",
        "size_t queue_depth;",
        "size_t payload_max_bytes;",
        "comp_epaper_display_queue_snapshot",
        "comp_epaper_display_queue_high_water_count",
        "comp_epaper_display_queue_pending",
        "comp_epaper_display_queue_dropped_count",
    ]:
        require(token in header, f"display_queue.h missing telemetry token {token}", errors)
    for token in [
        "queue->count++;",
        "if (queue->count > queue->high_water_count)",
        "queue->high_water_count = queue->count;",
        "void comp_epaper_display_queue_snapshot",
        "memset(out_snapshot, 0, sizeof(*out_snapshot));",
        "out_snapshot->pending_count = queue->count;",
        "out_snapshot->high_water_count = queue->high_water_count;",
        "out_snapshot->queue_depth = COMP_EPAPER_DISPLAY_QUEUE_DEPTH;",
        "out_snapshot->payload_max_bytes = COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES;",
        "out_snapshot->next_sequence = queue->next_sequence;",
        "out_snapshot->dropped_count = queue->dropped_count;",
        "return queue == NULL ? 0u : queue->count;",
        "return queue == NULL ? 0u : queue->high_water_count;",
        "return queue == NULL ? 0u : queue->dropped_count;",
    ]:
        require(token in source, f"display_queue.c missing telemetry token {token}", errors)
    dequeue_start = source.find("bool comp_epaper_display_queue_dequeue")
    snapshot_start = source.find("void comp_epaper_display_queue_snapshot", dequeue_start)
    dequeue_body = source[dequeue_start:snapshot_start] if dequeue_start >= 0 and snapshot_start > dequeue_start else ""
    require(dequeue_body, "could not isolate display queue dequeue body", errors)
    require("high_water_count" not in dequeue_body, "dequeue must not reduce high-water telemetry", errors)
    for forbidden in ["HAL_", "GPIO", "SPI", "QSPI", "stm32", "STMWPAN", "UTIL_SEQ"]:
        require(forbidden.lower() not in (header + source).lower(), f"display queue telemetry must stay platform-free: {forbidden}", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    for token in [
        "comp_epaper_display_queue_snapshot_t queue_stats",
        "comp_epaper_display_queue_snapshot(&s_companion_display_queue, &queue_stats)",
        "queue_stats.pending_count",
        "queue_stats.dropped_count",
        "s_companion_display_queue",
        "COMP_DIAG_EVT_EPAPER_RENDER_REQUEST",
        "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
    ]:
        require(token in app_ble, f"WB55 app missing queue telemetry integration token {token}", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "display_queue_telemetry",
        "Display queue telemetry",
        "companion-screen-display-queue-telemetry.json",
        "verify_display_queue_telemetry.py",
        "high-water",
    ]:
        require(token in screen_doc, f"screen expression doc missing telemetry anchor {token}", errors)
    for token in ["display queue telemetry", "high-water", "stats snapshot", "WBA", "comp_epaper_display_queue_snapshot", "comp_epaper_display_queue_high_water_count"]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing telemetry anchor {token}", errors)
    for token in ["display queue telemetry", "high-water", "stats snapshot", "verify_display_queue_telemetry.py"]:
        require(token.lower() in readme.lower(), f"e-paper README missing telemetry anchor {token}", errors)

    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if isinstance(item, dict)]
        matches = [item for item in items if item.get("id") == "display_queue_telemetry"]
        require(len(matches) == 1, "acceptance index must contain one display_queue_telemetry item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "display_queue_telemetry index item must be PASS", errors)
            require(
                "docs/validation/companion-screen-display-queue-telemetry.json" in item.get("evidence_paths", []),
                "display_queue_telemetry item must link telemetry fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_display_queue_telemetry.py" in item.get("validation_commands", []),
                "display_queue_telemetry item must run telemetry verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing display queue telemetry fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic display queue telemetry fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_queue_code(errors)
    check_wb55_integration(errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion display queue telemetry checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion display queue telemetry verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
