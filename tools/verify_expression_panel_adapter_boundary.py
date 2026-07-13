#!/usr/bin/env python3
"""Verify the portable panel adapter owns dispatch while target code owns refresh transport."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-adapter-boundary.json")
SCHEMA_ID = "companion.pendant.screen_panel_adapter_boundary.v1"

PANEL_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
PANEL_TARGET_STM32WB_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb.h"
PANEL_TARGET_STM32WB_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb.c"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
PANEL_BEHAVIOR_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-adapter-behavior.json"
PANEL_EVIDENCE_TEMPLATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-template.json"

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
        "sources": {
            "panel_header": rel(PANEL_HEADER),
            "panel_source": rel(PANEL_SOURCE),
            "wb55_target_header": rel(PANEL_TARGET_STM32WB_HEADER),
            "wb55_target_source": rel(PANEL_TARGET_STM32WB_SOURCE),
            "screen_doc": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "panel_behavior_fixture": rel(PANEL_BEHAVIOR_FIXTURE),
            "panel_evidence_template": rel(PANEL_EVIDENCE_TEMPLATE),
        },
        "adapter_contract": {
            "portable_dispatcher": "comp_epaper_panel_adapter_refresh_card",
            "target_refresh_callback_type": "comp_epaper_panel_refresh_fn_t",
            "target_context_field": "context",
            "target_callback_field": "refresh",
            "dry_run_initializer": "comp_epaper_panel_adapter_init_dry_run",
            "missing_callback_result": "COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR",
            "dry_run_result": "COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL",
            "controller_unknown_result": "COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN",
            "real_ok_source": "target_refresh_callback_only",
        },
        "guard_order": [
            "hardware_present",
            "controller_known_width_height",
            "refresh_callback_present",
            "target_refresh_callback",
        ],
        "target_adapter_expectations": {
            "wb55_file_pattern": "*_stm32wb.*",
            "wb55_current_file": rel(PANEL_TARGET_STM32WB_SOURCE),
            "wb55_current_initializer": "companion_epaper_panel_stm32wb_init",
            "wba_file_pattern": "*_stm32wba.*",
            "portable_files_unchanged": [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/display_queue.c",
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
            ],
        },
        "acceptance": {
            "dry_run_still_deferred_no_panel": True,
            "known_panel_without_target_callback_is_transport_error": True,
            "real_refresh_ok_can_only_come_from_target_callback": True,
            "portable_adapter_has_no_board_dependencies": True,
            "wba_safe_target_ops_boundary": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_adapter_behavior.py",
            "python .\\tools\\verify_expression_panel_adapter_boundary.py",
            "python .\\tools\\verify_expression_panel_target_stm32wb.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_panel_adapter_code(errors: list[str]) -> None:
    header = read(PANEL_HEADER, errors)
    source = read(PANEL_SOURCE, errors)
    target_header = read(PANEL_TARGET_STM32WB_HEADER, errors)
    target_source = read(PANEL_TARGET_STM32WB_SOURCE, errors)
    combined = header + "\n" + source

    for token in [
        "comp_epaper_panel_refresh_fn_t",
        "void *context",
        "comp_epaper_panel_refresh_fn_t refresh",
        ".refresh = NULL",
        ".context = NULL",
        "adapter->config.refresh == NULL",
        "COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR",
        "adapter->config.refresh(adapter->config.context",
        "target_report",
        "adapter->rendered_count++",
    ]:
        require(token in combined, f"panel adapter target boundary missing {token}", errors)

    order_tokens = [
        "!adapter->config.hardware_present",
        "!adapter->config.controller_known",
        "adapter->config.refresh == NULL",
        "adapter->config.refresh(adapter->config.context",
    ]
    positions = [source.find(token) for token in order_tokens]
    require(all(position >= 0 for position in positions), "panel adapter guard order tokens missing", errors)
    require(positions == sorted(positions), "panel adapter must check hardware/controller/callback before target refresh", errors)

    require(
        "result = COMP_EPAPER_PANEL_RESULT_OK" not in source,
        "portable panel adapter must not directly claim OK",
        errors,
    )
    for label, pattern in FORBIDDEN_PORTABLE_PATTERNS.items():
        match = pattern.search(combined)
        require(
            match is None,
            f"panel adapter contains non-portable {label}: {match.group(0) if match else ''}",
            errors,
        )
    for token in [
        "companion_epaper_panel_stm32wb_init",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
    ]:
        require(token in target_header + target_source, f"WB55 target panel adapter missing {token}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel adapter boundary schema", errors)
    require(data.get("status") == "PASS", "panel adapter boundary fixture must be PASS", errors)
    contract = data.get("adapter_contract", {})
    require(contract.get("target_refresh_callback_type") == "comp_epaper_panel_refresh_fn_t", "fixture missing callback type", errors)
    require(contract.get("missing_callback_result") == "COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR", "fixture missing missing-callback result", errors)
    require(contract.get("real_ok_source") == "target_refresh_callback_only", "fixture must keep OK target-owned", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "dry_run_still_deferred_no_panel",
        "known_panel_without_target_callback_is_transport_error",
        "real_refresh_ok_can_only_come_from_target_callback",
        "portable_adapter_has_no_board_dependencies",
        "wba_safe_target_ops_boundary",
    ]:
        require(acceptance.get(token) is True, f"panel adapter boundary acceptance missing {token}", errors)
    for command in data.get("validation_commands", []):
        if "\\tools\\" in str(command):
            tool = str(command).split("\\tools\\", 1)[1].split()[0]
            require((REPO_ROOT / "tools" / tool).exists(), f"panel adapter boundary command references missing tool {tool}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    evidence_template = read(PANEL_EVIDENCE_TEMPLATE, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)

    for token in [
        "panel_target_ops_boundary",
        "companion-screen-panel-adapter-boundary.json",
        "comp_epaper_panel_refresh_fn_t",
        "panel_adapter_behavior_matrix",
        "wb55_panel_target_adapter_scaffold",
        "companion-screen-panel-adapter-behavior.json",
        "companion-screen-panel-target-stm32wb.json",
        "target-owned refresh callback",
    ]:
        require(token in screen_doc, f"screen doc missing panel adapter boundary anchor {token}", errors)
    for token in [
        "target-owned refresh callback",
        "comp_epaper_panel_refresh_fn_t",
        "panel adapter boundary",
    ]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing panel adapter boundary anchor {token}", errors)
    require("target-owned refresh callback" in readme.lower(), "e-paper README missing target-owned refresh callback note", errors)
    require(PANEL_BEHAVIOR_FIXTURE.exists(), "missing panel adapter behavior fixture", errors)
    require("target_adapter_file" in evidence_template, "panel evidence template must require target_adapter_file", errors)
    require(fixture_rel in index_text, "acceptance index must link panel adapter boundary fixture", errors)

    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if item.get("id") == "panel_target_ops_boundary"]
        require(len(items) == 1, "acceptance index must contain one panel_target_ops_boundary item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_target_ops_boundary item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel_target_ops_boundary item missing fixture evidence", errors)
            require(
                "python .\\tools\\verify_expression_panel_adapter_boundary.py" in item.get("validation_commands", []),
                "panel_target_ops_boundary item missing verifier command",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel adapter boundary fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic panel adapter boundary JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    expected = build_fixture()
    errors: list[str] = []

    check_panel_adapter_code(errors)
    check_fixture_data(expected, errors)
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel adapter boundary checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion panel adapter boundary verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
