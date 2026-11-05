#!/usr/bin/env python3
"""Verify the STM32WBA screen scheduler/timer scaffold stays target-isolated."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-scheduler-stm32wba.json")
SCHEMA_ID = "companion.pendant.screen_scheduler_stm32wba.v1"

SCHEDULER_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_scheduler_stm32wba.h"
SCHEDULER_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_scheduler_stm32wba.c"
DISPLAY_DRAIN_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-display-drain-contract.json"
EXPRESSION_STATE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
WB55_APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
WB55_MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA55_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read_text(path, errors)
    if not text:
        return {}
    return json.loads(text)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Target-named STM32WBA display scheduler/timer scaffold that keeps "
            "display-task wakeups and ExpressionV1 tick timing behind callbacks "
            "until the CubeWBA scheduler is selected."
        ),
        "sources": {
            "wba_scheduler_header": rel(SCHEDULER_HEADER),
            "wba_scheduler_source": rel(SCHEDULER_SOURCE),
            "display_drain_contract": rel(DISPLAY_DRAIN_CONTRACT),
            "expression_state_header": rel(EXPRESSION_STATE_HEADER),
            "wba_port_contract": rel(WBA_CONTRACT),
            "wba55_port_scaffold": rel(WBA55_SCAFFOLD),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "contract": {
            "scheduler_type": "companion_epaper_stm32wba_scheduler_t",
            "schedule_display_callback": "companion_epaper_stm32wba_schedule_fn_t",
            "start_tick_timer_callback": "companion_epaper_stm32wba_timer_fn_t",
            "stop_tick_timer_callback": "companion_epaper_stm32wba_schedule_fn_t",
            "now_ms_callback": "companion_epaper_stm32wba_now_ms_fn_t",
            "schedule_display_api": "companion_epaper_stm32wba_schedule_display_task",
            "schedule_tick_api": "companion_epaper_stm32wba_schedule_expression_tick",
            "ready_api": "companion_epaper_stm32wba_scheduler_ready",
            "not_in_wb55_build": True,
            "preserves_display_drain_contract": True,
            "preserves_expression_tick_contract": True,
        },
        "forbidden_before_wba_project": [
            "UTIL_SEQ",
            "HW_TS",
            "CFG_TASK_COMPANION_DISPLAY_ID",
            "CFG_SCH_PRIO_0",
            "HAL_GetTick",
            "HAL_TIM",
            "STM32_WPAN",
            "CPU2",
            "FUS",
            "IPCC",
            "HSEM",
        ],
        "required_future_evidence": [
            "CubeWBA scheduler API chosen",
            "WBA display task registration calls the same one-request-per-pass display drain path",
            "WBA tick timer wakes display work for comp_epaper_expression_state_tick",
            "WBA now_ms source is monotonic for transient expression recovery",
            "WBA build wrapper compiles the scheduler hook for the selected target",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_screen_scheduler_stm32wba.py",
            "python .\\tools\\verify_expression_display_drain.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WBA scheduler scaffold schema", errors)
    require(data.get("status") == "PASS", "WBA scheduler scaffold fixture must be PASS", errors)
    contract = data.get("contract", {})
    for token in [
        "scheduler_type",
        "schedule_display_callback",
        "start_tick_timer_callback",
        "stop_tick_timer_callback",
        "now_ms_callback",
        "schedule_display_api",
        "schedule_tick_api",
        "ready_api",
    ]:
        require(contract.get(token), f"WBA scheduler scaffold contract missing {token}", errors)
    require(contract.get("not_in_wb55_build") is True, "WBA scheduler scaffold must stay out of WB55 build", errors)
    require(contract.get("preserves_display_drain_contract") is True, "WBA scheduler scaffold must preserve display drain contract", errors)
    require(contract.get("preserves_expression_tick_contract") is True, "WBA scheduler scaffold must preserve expression tick contract", errors)


def check_scheduler_code(errors: list[str]) -> None:
    header = read_text(SCHEDULER_HEADER, errors)
    source = read_text(SCHEDULER_SOURCE, errors)
    combined = header + "\n" + source
    for token in [
        "companion_epaper_stm32wba_schedule_fn_t",
        "companion_epaper_stm32wba_timer_fn_t",
        "companion_epaper_stm32wba_now_ms_fn_t",
        "companion_epaper_stm32wba_scheduler_config_t",
        "companion_epaper_stm32wba_scheduler_t",
        "companion_epaper_stm32wba_scheduler_init",
        "companion_epaper_stm32wba_scheduler_ready",
        "companion_epaper_stm32wba_now_ms",
        "companion_epaper_stm32wba_schedule_display_task",
        "companion_epaper_stm32wba_schedule_expression_tick",
    ]:
        require(token in header, f"screen_scheduler_stm32wba.h missing {token}", errors)
    for token in [
        '#include "screen_scheduler_stm32wba.h"',
        "memset(scheduler, 0, sizeof(*scheduler));",
        "scheduler->config = *config;",
        "scheduler->config.schedule_display_task != NULL",
        "scheduler->config.start_expression_tick_timer != NULL",
        "scheduler->config.stop_expression_tick_timer != NULL",
        "scheduler->config.now_ms != NULL",
        "return scheduler->config.now_ms(scheduler->config.context);",
        "scheduler->config.schedule_display_task(scheduler->config.context);",
        "scheduler->config.stop_expression_tick_timer(scheduler->config.context);",
        "companion_epaper_stm32wba_schedule_display_task(scheduler);",
        "scheduler->config.start_expression_tick_timer(scheduler->config.context",
    ]:
        require(token in source, f"screen_scheduler_stm32wba.c missing {token}", errors)
    for token in [
        "UTIL_SEQ",
        "HW_TS",
        "CFG_TASK_COMPANION_DISPLAY_ID",
        "CFG_SCH_PRIO_0",
        "HAL_GetTick",
        "HAL_TIM",
        "STM32_WPAN",
        "CPU2",
        "FUS",
        "IPCC",
        "HSEM",
    ]:
        require(token not in combined, f"WBA scheduler scaffold leaked WB55/platform token {token}", errors)


def check_wb55_isolation(errors: list[str]) -> None:
    app_ble = read_text(WB55_APP_BLE, errors)
    makefile = read_text(WB55_MAKEFILE, errors)
    for text, name in [(app_ble, "WB55 app_ble.c"), (makefile, "WB55 Makefile")]:
        require("screen_scheduler_stm32wba" not in text, f"{name} must not include WBA scheduler scaffold", errors)
        require("companion_epaper_stm32wba_scheduler" not in text, f"{name} must not use WBA scheduler scaffold", errors)
    require("UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID" in app_ble, "WB55 display task scheduling anchor missing", errors)
    require("HW_TS_Start(s_companion_expression_tick_timer_id" in app_ble, "WB55 expression tick timer anchor missing", errors)


def check_related_contracts(errors: list[str]) -> None:
    display_drain = read_json(DISPLAY_DRAIN_CONTRACT, errors)
    expression_header = read_text(EXPRESSION_STATE_HEADER, errors)
    require(
        display_drain.get("display_task_contract", {}).get("reschedule_condition") == "runtime_stats.display_queue.pending_count != 0u",
        "display drain contract must keep pending-work reschedule condition",
        errors,
    )
    for token in [
        "comp_epaper_expression_state_tick",
        "comp_epaper_expression_auto_recover_ms",
        "visible_age_ms",
    ]:
        require(token in expression_header, f"expression state header missing tick dependency {token}", errors)


def check_project_links(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    readme = read_text(README, errors)
    contract = read_json(WBA_CONTRACT, errors)
    scaffold = read_json(WBA55_SCAFFOLD, errors)
    for text, name in [(screen_doc, "screen doc"), (wba_rules, "WBA rules"), (readme, "epaper README")]:
        for token in [
            "wba_display_scheduler_scaffold",
            "WBA display scheduler scaffold",
            "screen_scheduler_stm32wba",
            "companion_epaper_stm32wba_schedule_expression_tick",
            "companion-screen-scheduler-stm32wba.json",
            "verify_expression_screen_scheduler_stm32wba.py",
            "display drain contract",
        ]:
            require(token in text, f"{name} missing WBA scheduler anchor {token}", errors)
    if not allow_stale_index:
        serialized_contract = json.dumps(contract, sort_keys=True)
        for token in ["screen_scheduler_stm32wba", "verify_expression_screen_scheduler_stm32wba.py", "WBA display scheduler scaffold"]:
            require(token in serialized_contract, f"WBA portability contract missing {token}", errors)
        serialized_scaffold = json.dumps(scaffold, sort_keys=True)
        for token in ["screen_scheduler_stm32wba", "companion_epaper_stm32wba_schedule_expression_tick", "DRAFT_PRE_PORT"]:
            require(token in serialized_scaffold, f"WBA55 port scaffold missing {token}", errors)

    if allow_stale_index:
        return
    index = read_json(ACCEPTANCE_INDEX, errors)
    matches = [
        item
        for item in index.get("items", [])
        if isinstance(item, dict) and item.get("id") == "wba_display_scheduler_scaffold"
    ]
    require(len(matches) == 1, "acceptance index must contain one wba_display_scheduler_scaffold item", errors)
    if matches:
        item = matches[0]
        require(item.get("status") == "PASS", "wba_display_scheduler_scaffold item must be PASS", errors)
        require(
            "docs/validation/companion-screen-scheduler-stm32wba.json" in item.get("evidence_paths", []),
            "wba_display_scheduler_scaffold item must link its fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_screen_scheduler_stm32wba.py" in item.get("validation_commands", []),
            "wba_display_scheduler_scaffold item must run its verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WBA scheduler scaffold fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WBA scheduler scaffold fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_scheduler_code(errors)
    check_wb55_isolation(errors)
    check_related_contracts(errors)
    check_project_links(errors, allow_stale_index=bool(args.write_fixture))

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion WBA screen scheduler scaffold checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WBA screen scheduler scaffold verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
