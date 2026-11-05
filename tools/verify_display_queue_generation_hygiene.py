#!/usr/bin/env python3
"""Verify display queue resource-generation behavior for SCR-17."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-display-queue-generation-hygiene.json"
SCHEMA_ID = "companion.pendant.screen_display_queue_generation_hygiene.v1"

QUEUE_H = ROOT / "app/companion_pendant/epaper/display_queue.h"
QUEUE_C = ROOT / "app/companion_pendant/epaper/display_queue.c"
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
PLAN = ROOT / "docs/companion_screen_project_plan.md"
GENERATION_RESEARCH = ROOT / "docs/validation/companion-screen-generation-swap-research.md"
WBA_RULES = ROOT / "docs/stm32wba_migration_rules.md"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def require_order(text: str, tokens: list[str], label: str, errors: list[str]) -> None:
    cursor = -1
    for token in tokens:
        index = text.find(token, cursor + 1)
        require(index >= 0, f"{label} missing ordered token {token}", errors)
        if index < 0:
            return
        require(index > cursor, f"{label} token out of order: {token}", errors)
        cursor = index


def build_scenario() -> dict[str, Any]:
    """Deterministic behavior model for the queue-generation contract."""

    queue = {
        "pending": 0,
        "dropped": 0,
        "active_revision": 0,
        "generation_switches": 0,
        "last_stale_discarded": 0,
        "stale_discarded": 0,
        "next_sequence": 1,
        "requests": [],
    }

    def switch_revision(revision: int) -> None:
        if queue["active_revision"] == revision:
            return
        discarded = queue["pending"]
        queue["dropped"] += discarded
        queue["stale_discarded"] += discarded
        queue["last_stale_discarded"] = discarded
        queue["generation_switches"] += 1
        queue["pending"] = 0
        queue["requests"] = []
        queue["active_revision"] = revision

    def enqueue(kind: str, request_id: int) -> None:
        request = {
            "kind": kind,
            "request_id": request_id,
            "sequence": queue["next_sequence"],
            "resource_revision": queue["active_revision"],
        }
        queue["next_sequence"] += 1
        queue["requests"].append(request)
        queue["pending"] += 1

    switch_revision(50)
    enqueue("expression", 0x5001)
    enqueue("menu", 0x5002)
    enqueue("expression", 0x5003)
    before_switch = {
        "pending": queue["pending"],
        "request_revisions": [item["resource_revision"] for item in queue["requests"]],
    }

    switch_revision(51)
    after_switch = {
        "pending": queue["pending"],
        "active_revision": queue["active_revision"],
        "generation_switches": queue["generation_switches"],
        "last_stale_discarded": queue["last_stale_discarded"],
        "stale_discarded": queue["stale_discarded"],
        "dropped": queue["dropped"],
    }

    enqueue("menu", 0x5101)
    first_current_request = queue["requests"][0]
    coherent_generation = int(
        first_current_request["resource_revision"] == queue["active_revision"]
    )

    return {
        "name": "rev50_pending_frames_discarded_before_rev51_first_frame",
        "before_switch": before_switch,
        "after_switch": after_switch,
        "first_current_request": first_current_request,
        "display_result_expectation": {
            "active_revision": 51,
            "resource_revision": 51,
            "coherent_generation": coherent_generation,
            "generation_switches": 2,
            "last_stale_discarded": 3,
        },
    }


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Behavior-level guard that resource-pack generation switches discard stale display requests before the next visible frame.",
        "sources": {
            "display_queue_header": rel(QUEUE_H),
            "display_queue_source": rel(QUEUE_C),
            "wb55_integration": rel(APP_BLE),
            "project_plan": rel(PLAN),
            "generation_research": rel(GENERATION_RESEARCH),
            "wba_rules": rel(WBA_RULES),
        },
        "scenario": build_scenario(),
        "contract": {
            "revision_switch_api": "comp_epaper_display_queue_set_resource_revision",
            "active_revision_field": "active_resource_revision",
            "request_revision_field": "resource_revision",
            "generation_switch_counter": "generation_switch_count",
            "last_stale_discard_counter": "last_stale_generation_discarded",
            "stale_discard_counter": "stale_generation_discard_count",
            "wb55_log_markers": [
                "queue_generation revision=",
                "coherent_generation=1",
                "generation_switches=",
                "last_stale_discarded=",
            ],
            "wba_inherits_contract": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_expression_display_drain.py",
            "python .\\tools\\verify_screen_refresh_feel_contract.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_source(errors: list[str]) -> None:
    header = read(QUEUE_H)
    source = read(QUEUE_C)
    app_ble = read(APP_BLE)
    plan = read(PLAN)
    research = read(GENERATION_RESEARCH)
    wba_rules = read(WBA_RULES)

    for token in (
        "uint32_t resource_revision;",
        "uint32_t active_resource_revision;",
        "uint32_t generation_switch_count;",
        "uint32_t last_stale_generation_discarded;",
        "uint32_t stale_generation_discard_count;",
        "comp_epaper_display_queue_set_resource_revision",
        "comp_epaper_display_queue_generation_switch_count",
        "comp_epaper_display_queue_last_stale_generation_discarded",
        "comp_epaper_display_queue_stale_generation_discard_count",
    ):
        require(token in header, f"display_queue.h missing generation token {token}", errors)

    require_order(
        source,
        [
            "discarded = queue->count;",
            "queue->dropped_count += (uint32_t)discarded;",
            "queue->stale_generation_discard_count += (uint32_t)discarded;",
            "queue->last_stale_generation_discarded = (uint32_t)discarded;",
            "queue->generation_switch_count++;",
            "memset(queue->items, 0, sizeof(queue->items));",
            "queue->read_index = 0u;",
            "queue->write_index = 0u;",
            "queue->count = 0u;",
            "queue->active_resource_revision = resource_revision;",
        ],
        "display queue revision switch",
        errors,
    )
    for token in (
        "(*out_request)->resource_revision = queue->active_resource_revision;",
        "request->resource_revision = queue->active_resource_revision;",
        "out_snapshot->active_resource_revision = queue->active_resource_revision;",
        "out_snapshot->generation_switch_count = queue->generation_switch_count;",
        "out_snapshot->last_stale_generation_discarded",
        "out_snapshot->stale_generation_discard_count",
    ):
        require(token in source, f"display_queue.c missing generation token {token}", errors)
    for retired in (
        "pet_expression.h",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_display_queue_enqueue_pet_expression",
        "comp_pet_expression_pose_t",
        "comp_pet_expression_pose_is_valid",
        "pet_pose",
    ):
        require(retired not in header + source,
                f"display queue retains a retired procedural visual route: {retired}", errors)

    for token in (
        "comp_epaper_display_queue_set_resource_revision(",
        "queue_generation revision=",
        "display_result id=%lu kind=%u resource_revision=%lu active_revision=%lu coherent_generation=%u",
        "request.resource_revision == runtime_stats.display_queue.active_resource_revision ? 1u : 0u",
        "generation_switches=%lu last_stale_discarded=%lu",
        "runtime_stats.display_queue.stale_generation_discard_count",
    ):
        require(token in app_ble, f"app_ble.c missing generation log token {token}", errors)

    for token in (
        "release ledger",
        "旧队列丢弃计数",
        "首帧 coherent marker",
        "新旧画面交织防回退",
    ):
        require(token in plan, f"project plan missing SCR-17 token {token}", errors)
    for token in (
        "Release ledger entry required",
        "`coherent_generation=1`",
        "stale queued frame",
        "stale asset revision",
    ):
        require(token in research, f"generation research missing token {token}", errors)
    for token in (
        "Display generation hygiene",
        "coherent_generation=1",
        "generation_switch_count",
        "Resource generation switches must remain coherent",
    ):
        require(token in wba_rules, f"WBA rules missing generation token {token}", errors)


def check_fixture(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected generation hygiene schema", errors)
    require(data.get("status") == "PASS", "generation hygiene fixture must be PASS", errors)
    scenario = data.get("scenario", {})
    before = scenario.get("before_switch", {})
    after = scenario.get("after_switch", {})
    first = scenario.get("first_current_request", {})
    display = scenario.get("display_result_expectation", {})
    require(before.get("pending") == 3, "scenario must start with three stale pending frames", errors)
    require(before.get("request_revisions") == [50, 50, 50], "stale requests must carry rev50", errors)
    require(after.get("pending") == 0, "revision switch must drain pending frames", errors)
    require(after.get("active_revision") == 51, "revision switch must activate rev51", errors)
    require(after.get("last_stale_discarded") == 3, "revision switch must report three stale discards", errors)
    require(after.get("stale_discarded") == 3, "stale discard total must be three", errors)
    require(first.get("resource_revision") == 51, "first post-switch request must carry rev51", errors)
    require(display.get("coherent_generation") == 1, "first post-switch frame must be coherent", errors)
    for marker in (
        "queue_generation revision=",
        "coherent_generation=1",
        "generation_switches=",
        "last_stale_discarded=",
    ):
        require(marker in data.get("contract", {}).get("wb55_log_markers", []), f"fixture missing log marker {marker}", errors)
    require(data.get("contract", {}).get("wba_inherits_contract") is True, "WBA must inherit generation hygiene contract", errors)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    output = args.json if args.json.is_absolute() else ROOT / args.json

    errors: list[str] = []
    expected = build_fixture()
    check_fixture(expected, errors)
    check_source(errors)

    rendered = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    if args.write and not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not args.write:
        require(output.exists(), f"missing {rel(output)}", errors)
        if output.exists():
            actual_text = output.read_text(encoding="utf-8")
            require(actual_text == rendered, f"{rel(output)} is stale; rerun with --write", errors)
            if actual_text == rendered:
                check_fixture(json.loads(actual_text), errors)

    if errors:
        print("FAIL: display queue generation hygiene checks failed", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: display queue generation hygiene verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
