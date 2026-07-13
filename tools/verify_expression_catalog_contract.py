#!/usr/bin/env python3
"""Verify the public ExpressionV1 catalog stays stable across firmware and host tools."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import EXPRESSION_COPY, EXPRESSION_KINDS  # noqa: E402
from app.companion_pendant.epaper.expression_policy import EXPRESSION_PRIORITIES  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-catalog.json")
SCHEMA_ID = "companion.pendant.screen_expression_catalog.v1"

EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EXPRESSION_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
RENDERER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "card_renderer.py"
POLICY = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_policy.py"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
FIRMWARE_STATE_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-firmware-expression-state.json"
BLE_MATRIX = REPO_ROOT / "docs" / "validation" / "companion_ble_matrix.json"

EXPECTED_EXPRESSIONS = [
    "idle",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "sleepy",
    "recording",
    "sync_complete",
    "low_battery",
    "error",
]

EXPECTED_SIGNALS = [
    "BOOT_IDLE",
    "WAKE_ARMED",
    "WAKE_DISABLED",
    "WAKE_DETECTED",
    "SPEAKER_PROMPT",
    "SPEAKER_RESULT",
    "MEETING_START",
    "MEETING_STOP",
    "MEETING_FINALIZE",
    "RECORDING_START",
    "RECORDING_STOP",
    "RECORDING_CANCEL",
    "RECORDING_FINISHED",
    "LOW_BATTERY",
    "RECOVERY",
    "ERROR",
    "SETTINGS_SLEEPY",
    "BATTERY_RECOVERED",
]

STABLE_EXPRESSIONS = {"idle", "sleepy", "recording", "low_battery", "error"}
AUTO_RECOVERY_MS = {
    "listening": 10000,
    "thinking": 12000,
    "speaking": 10000,
    "happy": 6000,
    "sync_complete": 8000,
}
SIGNAL_TO_EXPRESSION = {
    "BOOT_IDLE": "idle",
    "WAKE_ARMED": "idle",
    "WAKE_DISABLED": "sleepy",
    "WAKE_DETECTED": "listening",
    "SPEAKER_PROMPT": "speaking",
    "SPEAKER_RESULT": "happy",
    "MEETING_START": "recording",
    "MEETING_STOP": "thinking",
    "MEETING_FINALIZE": "sync_complete",
    "RECORDING_START": "recording",
    "RECORDING_STOP": "thinking",
    "RECORDING_CANCEL": "idle",
    "RECORDING_FINISHED": "sync_complete",
    "LOW_BATTERY": "low_battery",
    "RECOVERY": "idle",
    "ERROR": "error",
    "SETTINGS_SLEEPY": "sleepy",
    "BATTERY_RECOVERED": "idle",
}

EXPRESSION_ENUM_RE = re.compile(r"COMP_EPAPER_EXPRESSION_([A-Z_]+)\s*=\s*(\d+),")
SIGNAL_ENUM_RE = re.compile(r"COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+)\s*=\s*(\d+),")
EXPRESSION_DEF_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(\d+)u,\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\}'
)
SIGNAL_DEF_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(true|false),\s*"([^"]+)"\}'
)


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


def symbol_to_name(symbol: str) -> str:
    return symbol.lower()


def parse_enum_values(header: str, pattern: re.Pattern[str], prefix: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for symbol, value in pattern.findall(header):
        if symbol == "COUNT":
            values[f"{prefix}_COUNT"] = int(value)
        else:
            values[symbol_to_name(symbol) if prefix == "expression" else symbol] = int(value)
    return values


def parse_expression_defs(source: str) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for symbol, priority, name, title, body, footer in EXPRESSION_DEF_RE.findall(source):
        parsed[name] = {
            "symbol": symbol,
            "priority": int(priority),
            "title": title,
            "body": body,
            "footer": footer,
        }
    return parsed


def parse_signal_defs(source: str) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for signal, expression_symbol, may_lower, reason in SIGNAL_DEF_RE.findall(source):
        parsed[signal] = {
            "expression": symbol_to_name(expression_symbol),
            "may_lower_priority": may_lower == "true",
            "reason": reason,
        }
    return parsed


def build_catalog() -> dict[str, Any]:
    header = EXPRESSION_HEADER.read_text(encoding="utf-8")
    source = EXPRESSION_SOURCE.read_text(encoding="utf-8")
    expression_ids = parse_enum_values(header, EXPRESSION_ENUM_RE, "expression")
    signal_ids = parse_enum_values(header, SIGNAL_ENUM_RE, "signal")
    expression_defs = parse_expression_defs(source)
    signal_defs = parse_signal_defs(source)

    expressions = []
    for name in EXPECTED_EXPRESSIONS:
        title, body, footer = EXPRESSION_COPY[name]
        expressions.append(
            {
                "id": expression_ids[name],
                "name": name,
                "symbol": expression_defs[name]["symbol"],
                "priority": expression_defs[name]["priority"],
                "title": title,
                "body": body,
                "footer": footer,
                "stability": "stable" if name in STABLE_EXPRESSIONS else "transient",
                "auto_recover_ms": AUTO_RECOVERY_MS.get(name, 0),
            }
        )

    signals = []
    for signal in EXPECTED_SIGNALS:
        mapped = signal_defs[signal]["expression"]
        signals.append(
            {
                "id": signal_ids[signal],
                "signal": signal,
                "expression": mapped,
                "expression_id": expression_ids[mapped],
                "may_lower_priority": signal_defs[signal]["may_lower_priority"],
                "reason": signal_defs[signal]["reason"],
            }
        )

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Host-visible ExpressionV1 catalog tying stable numeric IDs to copy, priority, recovery, and BLE diagnostic payloads.",
        "sources": {
            "firmware_header": rel(EXPRESSION_HEADER),
            "firmware_source": rel(EXPRESSION_SOURCE),
            "renderer": rel(RENDERER),
            "policy": rel(POLICY),
            "wb55_integration": rel(APP_BLE),
            "ble_contract": rel(BLE_CONTRACT),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "firmware_state_fixture": rel(FIRMWARE_STATE_FIXTURE),
            "ble_matrix": rel(BLE_MATRIX),
        },
        "public_invariants": {
            "expression_count": len(EXPECTED_EXPRESSIONS),
            "signal_count": len(EXPECTED_SIGNALS),
            "expression_card_slot": 1,
            "expression_request_id_base": "0xe0000000",
            "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
            "copy_locale": "en",
            "stable_id_policy": "Do not renumber existing ExpressionV1 or signal IDs; append new IDs before COUNT only.",
        },
        "expressions": expressions,
        "signals": signals,
        "validation_commands": [
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_firmware_state.py",
            "python .\\tools\\verify_epaper_assets.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_catalog_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected expression catalog schema", errors)
    require(data.get("status") == "PASS", "expression catalog fixture must be PASS", errors)
    invariants = data.get("public_invariants", {})
    require(invariants.get("expression_count") == 10, "expression count drifted", errors)
    require(invariants.get("signal_count") == 18, "signal count drifted", errors)
    require(invariants.get("expression_card_slot") == 1, "expression card slot drifted", errors)
    require(invariants.get("expression_request_id_base") == "0xe0000000", "expression request ID base drifted", errors)
    require(
        invariants.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "expression diagnostic arg3 model drifted",
        errors,
    )

    expressions = data.get("expressions", [])
    require([entry.get("name") for entry in expressions] == EXPECTED_EXPRESSIONS, "expression order/name list drifted", errors)
    for expected_id, entry in enumerate(expressions):
        name = entry.get("name")
        require(entry.get("id") == expected_id, f"{name} expression id drifted", errors)
        require(entry.get("priority") == EXPRESSION_PRIORITIES.get(str(name)), f"{name} priority drifted", errors)
        title, body, footer = EXPRESSION_COPY.get(str(name), ("", "", ""))
        require(entry.get("title") == title, f"{name} title drifted", errors)
        require(entry.get("body") == body, f"{name} body drifted", errors)
        require(entry.get("footer") == footer, f"{name} footer drifted", errors)
        expected_stability = "stable" if name in STABLE_EXPRESSIONS else "transient"
        require(entry.get("stability") == expected_stability, f"{name} stability drifted", errors)
        require(entry.get("auto_recover_ms") == AUTO_RECOVERY_MS.get(str(name), 0), f"{name} auto recovery drifted", errors)

    signals = data.get("signals", [])
    require([entry.get("signal") for entry in signals] == EXPECTED_SIGNALS, "signal order/list drifted", errors)
    expression_ids = {entry.get("name"): entry.get("id") for entry in expressions}
    for expected_id, entry in enumerate(signals):
        signal = str(entry.get("signal"))
        expected_expression = SIGNAL_TO_EXPRESSION.get(signal)
        require(entry.get("id") == expected_id, f"{signal} signal id drifted", errors)
        require(entry.get("expression") == expected_expression, f"{signal} expression mapping drifted", errors)
        require(entry.get("expression_id") == expression_ids.get(expected_expression), f"{signal} expression id mapping drifted", errors)
        require(bool(entry.get("reason")), f"{signal} missing reason", errors)

    for evidence in data.get("sources", {}).values():
        require((REPO_ROOT / str(evidence)).exists(), f"catalog source path missing: {evidence}", errors)


def check_firmware_and_renderer(errors: list[str]) -> None:
    header = read(EXPRESSION_HEADER, errors)
    source = read(EXPRESSION_SOURCE, errors)
    expression_ids = parse_enum_values(header, EXPRESSION_ENUM_RE, "expression")
    signal_ids = parse_enum_values(header, SIGNAL_ENUM_RE, "signal")
    expression_defs = parse_expression_defs(source)
    signal_defs = parse_signal_defs(source)

    require(set(EXPRESSION_KINDS) == set(EXPECTED_EXPRESSIONS), "renderer ExpressionV1 kind set drifted", errors)
    require([expression_ids.get(name) for name in EXPECTED_EXPRESSIONS] == list(range(10)), "firmware expression enum IDs drifted", errors)
    require(expression_ids.get("expression_COUNT") == 10, "firmware expression COUNT drifted", errors)
    require([signal_ids.get(signal) for signal in EXPECTED_SIGNALS] == list(range(18)), "firmware signal enum IDs drifted", errors)
    require(signal_ids.get("signal_COUNT") == 18, "firmware signal COUNT drifted", errors)
    require(set(expression_defs) == set(EXPECTED_EXPRESSIONS), "firmware expression definition table drifted", errors)
    require(set(signal_defs) == set(EXPECTED_SIGNALS), "firmware signal definition table drifted", errors)

    for name in EXPECTED_EXPRESSIONS:
        title, body, footer = EXPRESSION_COPY[name]
        require(expression_defs[name]["title"] == title, f"{name} firmware/renderer title mismatch", errors)
        require(expression_defs[name]["body"] == body, f"{name} firmware/renderer body mismatch", errors)
        require(expression_defs[name]["footer"] == footer, f"{name} firmware/renderer footer mismatch", errors)
        require(expression_defs[name]["priority"] == EXPRESSION_PRIORITIES[name], f"{name} firmware/policy priority mismatch", errors)

    for signal, expression in SIGNAL_TO_EXPRESSION.items():
        require(signal_defs[signal]["expression"] == expression, f"{signal} firmware signal mapping drifted", errors)

    for token in [
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_LISTENING_MS 10000u",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_THINKING_MS 12000u",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SPEAKING_MS 10000u",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_HAPPY_MS 6000u",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SYNC_COMPLETE_MS 8000u",
    ]:
        require(token in header, f"firmware header missing recovery constant {token}", errors)


def check_host_visible_anchors(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    ble_contract = read(BLE_CONTRACT, errors)
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    index = json.loads(read(ACCEPTANCE_INDEX, errors) or "{}")
    firmware_state = json.loads(read(FIRMWARE_STATE_FIXTURE, errors) or "{}")
    ble_matrix = json.loads(read(BLE_MATRIX, errors) or "{}")

    for token in [
        "COMPANION_EPAPER_EXPRESSION_CARD_SLOT",
        "COMPANION_EPAPER_EXPRESSION_REQUEST_BASE",
        "((uint32_t)decision->expression << 16) |",
        "(uint32_t)decision->signal",
    ]:
        require(token in app_ble, f"WB55 app missing catalog-visible token {token}", errors)
    for token in [
        "(expression_id << 16) | signal_id",
        "CardStatusV1 Observability",
        "screen_expression_status",
    ]:
        require(token in ble_contract, f"BLE contract missing catalog token {token}", errors)
    for token in [
        "expression_catalog_contract",
        "companion-screen-expression-catalog.json",
        "verify_expression_catalog_contract.py",
        "ExpressionV1 catalog contract",
    ]:
        require(token in screen_doc, f"screen doc missing catalog anchor {token}", errors)
    for token in [
        "ExpressionV1 catalog",
        "companion-screen-expression-catalog.json",
        "verify_expression_catalog_contract.py",
        "stable numeric IDs",
    ]:
        require(token in wba_rules, f"WBA rules missing catalog anchor {token}", errors)

    expression_names = {entry.get("name") for entry in firmware_state.get("expressions", [])}
    signal_names = {entry.get("signal") for entry in firmware_state.get("signals", [])}
    require(expression_names == set(EXPECTED_EXPRESSIONS), "firmware state fixture expression set drifted from catalog", errors)
    require(signal_names == set(EXPECTED_SIGNALS), "firmware state fixture signal set drifted from catalog", errors)
    require(
        ble_matrix.get("operation_coverage", {})
        .get("screen_expression_status", {})
        .get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "BLE matrix fixture missing catalog diagnostic arg3 model",
        errors,
    )

    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    catalog_items = [item for item in items if item.get("id") == "expression_catalog_contract"]
    require(len(catalog_items) == 1, "acceptance index must contain one expression_catalog_contract item", errors)
    if catalog_items:
        item = catalog_items[0]
        require(item.get("status") == "PASS", "expression_catalog_contract index item must be PASS", errors)
        require(
            "docs/validation/companion-screen-expression-catalog.json" in item.get("evidence_paths", []),
            "expression_catalog_contract item must link catalog fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_catalog_contract.py" in item.get("validation_commands", []),
            "expression_catalog_contract item must run catalog verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression catalog fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_catalog_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic ExpressionV1 catalog JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_catalog()
    errors: list[str] = []

    check_catalog_data(expected, errors)
    check_firmware_and_renderer(errors)
    if args.write_fixture:
        # First-time generation happens before the acceptance index points at this fixture.
        for path in [BLE_CONTRACT, SCREEN_DOC, WBA_RULES, FIRMWARE_STATE_FIXTURE, BLE_MATRIX]:
            require(path.exists(), f"missing required path {rel(path)}", errors)
    else:
        check_host_visible_anchors(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion ExpressionV1 catalog checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 catalog verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
