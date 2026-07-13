#!/usr/bin/env python3
"""Verify panel adapter telemetry stays portable and WBA-safe."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-adapter-telemetry.json")
SCHEMA_ID = "companion.pendant.screen_panel_adapter_telemetry.v1"

PANEL_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
SCREEN_RUNTIME_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.h"
SCREEN_RUNTIME_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
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
        "purpose": "Portable panel adapter telemetry for WB55 dry-run status and future WBA real-panel driver pressure checks.",
        "sources": {
            "panel_header": rel(PANEL_HEADER),
            "panel_source": rel(PANEL_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "telemetry_fields": {
            "hardware_present": "current target configuration says panel hardware is present",
            "controller_known": "current target configuration has controller identity and dimensions",
            "refresh_configured": "target refresh callback is configured",
            "last_result_valid": "at least one adapter result has been observed",
            "last_result": "last comp_epaper_panel_result_t value observed by the dispatcher",
            "width_height": "panel dimensions from target configuration",
            "attempted_count": "display requests accepted by the adapter dispatcher",
            "rendered_count": "target callbacks that returned OK",
            "deferred_count": "dry-run/no-panel/controller-unknown deferrals",
            "error_count": "bad transport or target callback failures except BUSY",
        },
        "contract": {
            "snapshot_api": "comp_epaper_panel_adapter_snapshot",
            "snapshot_null_safe": True,
            "bad_argument_records_last_result_when_adapter_exists": True,
            "busy_does_not_increment_error_count": True,
            "dry_run_remains_deferred_no_panel": True,
            "platform_free": True,
            "host_status_unchanged": "CardStatusV1 and existing e_paper.update_result argument meanings are preserved.",
        },
        "wb55_observability": {
            "update_result_arg3": "runtime_stats.panel.attempted_count",
            "update_result_arg4": "panel_result",
            "stats_snapshot_api": "comp_epaper_screen_runtime_snapshot",
            "panel_snapshot_source": "comp_epaper_panel_adapter_snapshot",
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_adapter_telemetry.py",
            "python .\\tools\\verify_expression_panel_adapter_behavior.py",
            "python .\\tools\\verify_expression_panel_adapter_boundary.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel adapter telemetry schema", errors)
    require(data.get("status") == "PASS", "panel adapter telemetry fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(
        contract.get("snapshot_api") == "comp_epaper_panel_adapter_snapshot",
        "panel telemetry contract missing snapshot API",
        errors,
    )
    require(contract.get("snapshot_null_safe") is True, "panel telemetry snapshot must stay null-safe", errors)
    require(
        contract.get("bad_argument_records_last_result_when_adapter_exists") is True,
        "panel telemetry must record BAD_ARGUMENT when an adapter exists",
        errors,
    )
    require(contract.get("busy_does_not_increment_error_count") is True, "BUSY must not count as panel error", errors)
    wb55 = data.get("wb55_observability", {})
    require(wb55.get("update_result_arg3") == "runtime_stats.panel.attempted_count", "WB55 fixture must keep update_result arg3 as attempts", errors)
    require(wb55.get("update_result_arg4") == "panel_result", "WB55 fixture must keep update_result arg4 as panel result", errors)
    require(
        wb55.get("stats_snapshot_api") == "comp_epaper_screen_runtime_snapshot",
        "WB55 fixture must collect panel telemetry through the screen runtime snapshot",
        errors,
    )
    require(
        wb55.get("panel_snapshot_source") == "comp_epaper_panel_adapter_snapshot",
        "WB55 fixture must keep panel snapshot as the panel telemetry source",
        errors,
    )


def check_panel_code(errors: list[str]) -> None:
    header = read(PANEL_HEADER, errors)
    source = read(PANEL_SOURCE, errors)
    combined = header + "\n" + source
    for token in [
        "comp_epaper_panel_adapter_snapshot_t",
        "bool refresh_configured;",
        "bool last_result_valid;",
        "uint32_t attempted_count;",
        "uint32_t rendered_count;",
        "uint32_t deferred_count;",
        "uint32_t error_count;",
        "comp_epaper_panel_result_t last_result;",
        "comp_epaper_panel_adapter_snapshot",
    ]:
        require(token in header, f"panel_adapter.h missing telemetry token {token}", errors)
    for token in [
        "adapter->last_result = COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL;",
        "adapter->last_result = result;",
        "adapter->last_result_valid = true;",
        "void comp_epaper_panel_adapter_snapshot",
        "memset(out_snapshot, 0, sizeof(*out_snapshot));",
        "out_snapshot->hardware_present = adapter->config.hardware_present;",
        "out_snapshot->controller_known = adapter->config.controller_known;",
        "out_snapshot->refresh_configured = adapter->config.refresh != NULL;",
        "out_snapshot->last_result_valid = adapter->last_result_valid;",
        "out_snapshot->attempted_count = adapter->attempted_count;",
        "out_snapshot->rendered_count = adapter->rendered_count;",
        "out_snapshot->deferred_count = adapter->deferred_count;",
        "out_snapshot->error_count = adapter->error_count;",
        "out_snapshot->last_result = adapter->last_result;",
    ]:
        require(token in source, f"panel_adapter.c missing telemetry token {token}", errors)
    require(
        "result != COMP_EPAPER_PANEL_RESULT_BUSY" in source,
        "BUSY must remain excluded from panel error_count",
        errors,
    )
    require(
        source.find("adapter->last_result = result;") < source.find("if (out_report != NULL) {\n        *out_report = target_report;"),
        "panel telemetry must record last_result before publishing report",
        errors,
    )
    for label, pattern in FORBIDDEN_PORTABLE_PATTERNS.items():
        match = pattern.search(combined)
        require(match is None, f"panel telemetry must stay platform-free: {label}: {match.group(0) if match else ''}", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    display_start = app_ble.find("static void Companion_Display_Task(void)")
    display_end = app_ble.find("static uint32_t Companion_Display_NextExpressionRequestId", display_start)
    display_task = app_ble[display_start:display_end] if display_start >= 0 and display_end > display_start else ""
    require(display_task, "could not isolate Companion_Display_Task", errors)
    require('#include "screen_runtime.h"' in app_ble, "WB55 app_ble.c missing screen runtime include", errors)
    for token in [
        "comp_epaper_screen_runtime_snapshot_t runtime_stats",
        "comp_epaper_screen_runtime_snapshot(&s_companion_expression_state",
        "&s_companion_panel_adapter",
        "runtime_stats.panel.attempted_count",
        "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
        "(uint32_t)panel_result",
    ]:
        require(token in display_task, f"WB55 display task missing panel telemetry token {token}", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "panel_adapter_telemetry_snapshot",
        "Panel adapter telemetry snapshot",
        "companion-screen-panel-adapter-telemetry.json",
        "verify_expression_panel_adapter_telemetry.py",
        "stats snapshot",
        "comp_epaper_panel_adapter_snapshot",
    ]:
        require(token in screen_doc, f"screen expression doc missing panel telemetry anchor {token}", errors)
    for token in ["panel adapter telemetry", "stats snapshot", "WBA", "comp_epaper_panel_adapter_snapshot"]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing panel telemetry anchor {token}", errors)
    for token in ["panel adapter telemetry", "stats snapshot", "verify_expression_panel_adapter_telemetry.py"]:
        require(token.lower() in readme.lower(), f"e-paper README missing panel telemetry anchor {token}", errors)

    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if isinstance(item, dict)]
        matches = [item for item in items if item.get("id") == "panel_adapter_telemetry_snapshot"]
        require(len(matches) == 1, "acceptance index must contain one panel_adapter_telemetry_snapshot item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "panel_adapter_telemetry_snapshot item must be PASS", errors)
            require(
                "docs/validation/companion-screen-panel-adapter-telemetry.json" in item.get("evidence_paths", []),
                "panel_adapter_telemetry_snapshot item must link telemetry fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_panel_adapter_telemetry.py" in item.get("validation_commands", []),
                "panel_adapter_telemetry_snapshot item must run telemetry verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel adapter telemetry fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic panel adapter telemetry fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_panel_code(errors)
    check_wb55_integration(errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion panel adapter telemetry checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion panel adapter telemetry verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
