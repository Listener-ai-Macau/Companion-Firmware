#!/usr/bin/env python3
"""Verify ExpressionV1 state telemetry stays portable and WBA-safe."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-state-telemetry.json")
SCHEMA_ID = "companion.pendant.screen_expression_state_telemetry.v1"

EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EXPRESSION_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
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
        "purpose": "Portable ExpressionV1 state telemetry for WB55 transient scheduling and future WBA scheduler hooks.",
        "sources": {
            "expression_header": rel(EXPRESSION_HEADER),
            "expression_source": rel(EXPRESSION_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "telemetry_fields": {
            "initialized": "whether a visible expression has been accepted",
            "current": "current ExpressionV1 face enum",
            "last_signal": "last ExpressionV1 signal applied or suppressed",
            "priority": "priority of the current face",
            "revision": "visible-expression change counter",
            "visible_age_ms": "elapsed time since the current visible face was accepted",
            "auto_recover_ms": "portable recovery dwell time for transient faces",
            "suppressed_duplicate_count": "same-face signal suppressions that avoided e-paper refresh",
        },
        "contract": {
            "snapshot_api": "comp_epaper_expression_state_snapshot",
            "snapshot_null_safe": True,
            "auto_recover_derived_from_current": True,
            "wb55_scheduler_uses_snapshot": True,
            "duplicate_suppression_observable": True,
            "host_status_unchanged": "CardStatusV1 and expression diagnostic payloads stay unchanged.",
            "platform_free": True,
        },
        "wb55_observability": {
            "scheduler_reads": [
                "snapshot.initialized",
                "snapshot.auto_recover_ms",
                "snapshot.visible_age_ms",
            ],
            "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_state_telemetry.py",
            "python .\\tools\\verify_expression_firmware_state.py",
            "python .\\tools\\verify_expression_journeys.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected expression state telemetry schema", errors)
    require(data.get("status") == "PASS", "expression state telemetry fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(
        contract.get("snapshot_api") == "comp_epaper_expression_state_snapshot",
        "expression telemetry contract missing snapshot API",
        errors,
    )
    require(contract.get("snapshot_null_safe") is True, "expression telemetry snapshot must stay null-safe", errors)
    require(contract.get("auto_recover_derived_from_current") is True, "auto recovery must be derived from current face", errors)
    require(contract.get("wb55_scheduler_uses_snapshot") is True, "WB55 scheduler must use expression snapshot", errors)
    require(contract.get("duplicate_suppression_observable") is True, "duplicate suppression counter must stay observable", errors)


def check_expression_code(errors: list[str]) -> None:
    header = read(EXPRESSION_HEADER, errors)
    source = read(EXPRESSION_SOURCE, errors)
    combined = header + "\n" + source
    for token in [
        "comp_epaper_expression_state_snapshot_t",
        "bool initialized;",
        "comp_epaper_expression_t current;",
        "comp_epaper_expression_signal_t last_signal;",
        "uint32_t revision;",
        "uint32_t visible_age_ms;",
        "uint32_t auto_recover_ms;",
        "uint32_t suppressed_duplicate_count;",
        "comp_epaper_expression_state_snapshot",
    ]:
        require(token in header, f"expression_state.h missing telemetry token {token}", errors)
    for token in [
        "#include <string.h>",
        "void comp_epaper_expression_state_snapshot",
        "memset(out_snapshot, 0, sizeof(*out_snapshot));",
        "out_snapshot->initialized = state->initialized;",
        "out_snapshot->current = state->current;",
        "out_snapshot->last_signal = state->last_signal;",
        "out_snapshot->priority = state->priority;",
        "out_snapshot->revision = state->revision;",
        "out_snapshot->visible_age_ms = state->visible_age_ms;",
        "out_snapshot->auto_recover_ms = comp_epaper_expression_auto_recover_ms(state->current);",
        "out_snapshot->suppressed_duplicate_count = state->suppressed_duplicate_count;",
    ]:
        require(token in source, f"expression_state.c missing telemetry token {token}", errors)
    for label, pattern in FORBIDDEN_PORTABLE_PATTERNS.items():
        match = pattern.search(combined)
        require(match is None, f"expression telemetry must stay platform-free: {label}: {match.group(0) if match else ''}", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    start = app_ble.find("static void Companion_Display_ScheduleExpressionTick(uint32_t now_ms)\n{")
    end = app_ble.find("static void Companion_Display_ProcessExpressionTick(void)\n{", start)
    scheduler = app_ble[start:end] if start >= 0 and end > start else ""
    require(scheduler, "could not isolate Companion_Display_ScheduleExpressionTick", errors)
    for token in [
        "comp_epaper_expression_state_snapshot_t expression_stats",
        "comp_epaper_expression_state_snapshot(&s_companion_expression_state",
        "recover_ms = expression_stats.auto_recover_ms;",
        "expression_stats.initialized &&",
        "expression_stats.visible_age_ms >= recover_ms",
        "recover_ms - expression_stats.visible_age_ms",
        "HW_TS_Start(s_companion_expression_tick_timer_id",
    ]:
        require(token in scheduler, f"WB55 expression scheduler missing telemetry token {token}", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "expression_state_telemetry_snapshot",
        "Expression state telemetry snapshot",
        "companion-screen-expression-state-telemetry.json",
        "verify_expression_state_telemetry.py",
        "comp_epaper_expression_state_snapshot",
        "suppressed duplicate",
    ]:
        require(token in screen_doc, f"screen expression doc missing expression telemetry anchor {token}", errors)
    for token in ["expression state telemetry", "stats snapshot", "WBA", "comp_epaper_expression_state_snapshot"]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing expression telemetry anchor {token}", errors)
    for token in ["expression state telemetry", "stats snapshot", "verify_expression_state_telemetry.py"]:
        require(token.lower() in readme.lower(), f"e-paper README missing expression telemetry anchor {token}", errors)

    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if isinstance(item, dict)]
        matches = [item for item in items if item.get("id") == "expression_state_telemetry_snapshot"]
        require(len(matches) == 1, "acceptance index must contain one expression_state_telemetry_snapshot item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "expression_state_telemetry_snapshot item must be PASS", errors)
            require(
                "docs/validation/companion-screen-expression-state-telemetry.json" in item.get("evidence_paths", []),
                "expression_state_telemetry_snapshot item must link telemetry fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_state_telemetry.py" in item.get("validation_commands", []),
                "expression_state_telemetry_snapshot item must run telemetry verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression state telemetry fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic expression state telemetry fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_expression_code(errors)
    check_wb55_integration(errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion expression state telemetry checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion expression state telemetry verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
