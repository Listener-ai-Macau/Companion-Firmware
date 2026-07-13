#!/usr/bin/env python3
"""Verify the portable screen runtime snapshot used by WB55 and future WBA ports."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-runtime-snapshot.json")
SCHEMA_ID = "companion.pendant.screen_runtime_snapshot.v1"

SCREEN_RUNTIME_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.h"
SCREEN_RUNTIME_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"

FORBIDDEN_PORTABLE_PATTERNS = {
    "STM32 family token": re.compile(r"\bstm32\w*\b", re.IGNORECASE),
    "HAL call": re.compile(r"\bHAL_[A-Za-z0-9_]+"),
    "STM32_WPAN": re.compile(r"\bSTM32_?WPAN\b", re.IGNORECASE),
    "Cube generated app header": re.compile(r'#\s*include\s+"(?:main|app_conf|app_ble)\.h"'),
    "GPIO pin macro": re.compile(r"\bGPIO(?:[A-Z]|\b)|\bGPIO_PIN_\w+"),
    "WB wireless split": re.compile(r"\b(?:CPU2|FUS|IPCC|HSEM|BLE_p2pServer)\b"),
    "board peripheral instance": re.compile(r"\b(?:QSPI|I2C[0-9]?|SAI[0-9]?|UART[0-9]?|USART[0-9]?|SPI[0-9]?)\b"),
    "sequencer": re.compile(r"\bUTIL_SEQ\b"),
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
        "purpose": "Portable aggregate runtime snapshot for screen expression state, display queue pressure, and panel adapter telemetry.",
        "sources": {
            "screen_runtime_header": rel(SCREEN_RUNTIME_HEADER),
            "screen_runtime_source": rel(SCREEN_RUNTIME_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "wb55_build": rel(MAKEFILE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "snapshot_fields": {
            "expression": "comp_epaper_expression_state_snapshot_t",
            "display_queue": "comp_epaper_display_queue_snapshot_t",
            "panel": "comp_epaper_panel_adapter_snapshot_t",
        },
        "contract": {
            "snapshot_api": "comp_epaper_screen_runtime_snapshot",
            "null_output_is_noop": True,
            "zeros_output_before_subsnapshots": True,
            "platform_free": True,
            "subsnapshots": [
                "comp_epaper_expression_state_snapshot",
                "comp_epaper_display_queue_snapshot",
                "comp_epaper_panel_adapter_snapshot",
            ],
        },
        "wb55_observability": {
            "display_task_snapshot": "comp_epaper_screen_runtime_snapshot",
            "update_result_arg3": "runtime_stats.panel.attempted_count",
            "reschedule_condition": "runtime_stats.display_queue.pending_count != 0u",
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
            "python .\\tools\\verify_expression_state_telemetry.py",
            "python .\\tools\\verify_display_queue_telemetry.py",
            "python .\\tools\\verify_expression_panel_adapter_telemetry.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected screen runtime snapshot schema", errors)
    require(data.get("status") == "PASS", "screen runtime fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("snapshot_api") == "comp_epaper_screen_runtime_snapshot", "screen runtime fixture missing snapshot API", errors)
    require(contract.get("null_output_is_noop") is True, "screen runtime snapshot must keep null output as no-op", errors)
    require(contract.get("zeros_output_before_subsnapshots") is True, "screen runtime snapshot must zero output first", errors)
    for token in [
        "comp_epaper_expression_state_snapshot",
        "comp_epaper_display_queue_snapshot",
        "comp_epaper_panel_adapter_snapshot",
    ]:
        require(token in contract.get("subsnapshots", []), f"screen runtime fixture missing subsnapshot {token}", errors)
    wb55 = data.get("wb55_observability", {})
    require(wb55.get("update_result_arg3") == "runtime_stats.panel.attempted_count", "WB55 must log panel attempts from runtime snapshot", errors)
    require(
        wb55.get("reschedule_condition") == "runtime_stats.display_queue.pending_count != 0u",
        "WB55 must reschedule from runtime queue snapshot",
        errors,
    )


def check_runtime_code(errors: list[str]) -> None:
    header = read(SCREEN_RUNTIME_HEADER, errors)
    source = read(SCREEN_RUNTIME_SOURCE, errors)
    combined = header + "\n" + source
    for token in [
        '#include "display_queue.h"',
        '#include "expression_state.h"',
        '#include "panel_adapter.h"',
        "comp_epaper_screen_runtime_snapshot_t",
        "comp_epaper_expression_state_snapshot_t expression;",
        "comp_epaper_display_queue_snapshot_t display_queue;",
        "comp_epaper_panel_adapter_snapshot_t panel;",
        "comp_epaper_screen_runtime_snapshot",
    ]:
        require(token in header, f"screen_runtime.h missing token {token}", errors)
    for token in [
        "void comp_epaper_screen_runtime_snapshot",
        "if (out_snapshot == NULL)",
        "memset(out_snapshot, 0, sizeof(*out_snapshot));",
        "comp_epaper_expression_state_snapshot(expression_state",
        "comp_epaper_display_queue_snapshot(display_queue",
        "comp_epaper_panel_adapter_snapshot(panel_adapter",
    ]:
        require(token in source, f"screen_runtime.c missing token {token}", errors)
    for label, pattern in FORBIDDEN_PORTABLE_PATTERNS.items():
        match = pattern.search(combined)
        require(match is None, f"screen runtime must stay platform-free: {label}: {match.group(0) if match else ''}", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    makefile = read(MAKEFILE, errors)
    display_start = app_ble.find("static void Companion_Display_Task(void)")
    display_end = app_ble.find("static uint32_t Companion_Display_NextExpressionRequestId", display_start)
    display_task = app_ble[display_start:display_end] if display_start >= 0 and display_end > display_start else ""
    require(display_task, "could not isolate Companion_Display_Task", errors)
    for token in [
        '#include "screen_runtime.h"',
        "comp_epaper_screen_runtime_snapshot_t runtime_stats",
        "comp_epaper_screen_runtime_snapshot(&s_companion_expression_state",
        "&s_companion_display_queue",
        "&s_companion_panel_adapter",
        "runtime_stats.panel.attempted_count",
        "runtime_stats.display_queue.pending_count",
        "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
    ]:
        require(token in app_ble, f"WB55 app_ble.c missing runtime snapshot token {token}", errors)
    require(
        "$(ROOT)/app/companion_pendant/epaper/screen_runtime.c" in makefile,
        "WB55 Makefile missing screen_runtime.c",
        errors,
    )
    if display_task:
        require("comp_epaper_panel_adapter_snapshot_t panel_stats" not in display_task, "WB55 display task should not keep a separate panel_stats snapshot", errors)
        require("comp_epaper_display_queue_snapshot_t queue_stats" not in display_task, "WB55 display task should not keep a separate queue_stats snapshot", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "screen_runtime_snapshot",
        "Screen runtime snapshot",
        "companion-screen-runtime-snapshot.json",
        "verify_expression_screen_runtime_snapshot.py",
        "comp_epaper_screen_runtime_snapshot",
    ]:
        require(token in screen_doc, f"screen expression doc missing runtime snapshot anchor {token}", errors)
    for token in ["screen runtime snapshot", "comp_epaper_screen_runtime_snapshot", "WBA"]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing runtime snapshot anchor {token}", errors)
    for token in ["screen runtime", "comp_epaper_screen_runtime_snapshot", "verify_expression_screen_runtime_snapshot.py"]:
        require(token.lower() in readme.lower(), f"e-paper README missing runtime snapshot anchor {token}", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if isinstance(item, dict)]
        matches = [item for item in items if item.get("id") == "screen_runtime_snapshot"]
        require(len(matches) == 1, "acceptance index must contain one screen_runtime_snapshot item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "screen_runtime_snapshot item must be PASS", errors)
            require(
                "docs/validation/companion-screen-runtime-snapshot.json" in item.get("evidence_paths", []),
                "screen_runtime_snapshot item must link runtime fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_screen_runtime_snapshot.py" in item.get("validation_commands", []),
                "screen_runtime_snapshot item must run runtime verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing screen runtime fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic screen runtime fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_runtime_code(errors)
    check_wb55_integration(errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion screen runtime snapshot checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen runtime snapshot verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
