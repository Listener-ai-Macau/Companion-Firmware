#!/usr/bin/env python3
"""Verify the ExpressionV1 priority, lowering, duplicate, and recovery matrix."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-priority-matrix.json")
SCHEMA_ID = "companion.pendant.expression_priority_matrix.v1"

EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EXPRESSION_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
CATALOG_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-catalog.json"
FIRMWARE_STATE_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-firmware-expression-state.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

EXPRESSION_ENUM_RE = re.compile(r"COMP_EPAPER_EXPRESSION_([A-Z_]+)\s*=\s*(\d+),")
SIGNAL_ENUM_RE = re.compile(r"COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+)\s*=\s*(\d+),")
EXPRESSION_DEF_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(\d+)u,\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\}'
)
SIGNAL_DEF_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(true|false),\s*"([^"]+)"\}'
)
AUTO_RECOVER_DEFINE_RE = re.compile(r"#define\s+COMP_EPAPER_EXPRESSION_AUTO_RECOVER_([A-Z_]+)_MS\s+(\d+)u")

EXPECTED_PRIORITIES = {
    "sleepy": 10,
    "idle": 20,
    "happy": 30,
    "sync_complete": 40,
    "thinking": 50,
    "listening": 60,
    "speaking": 70,
    "low_battery": 80,
    "recording": 90,
    "error": 100,
}

STABLE_EXPRESSIONS = {"idle", "sleepy", "recording", "low_battery", "error"}


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


def parse_expression_ids(header: str) -> dict[str, int]:
    return {
        symbol: int(value)
        for symbol, value in EXPRESSION_ENUM_RE.findall(header)
        if symbol != "COUNT"
    }


def parse_signal_ids(header: str) -> dict[str, int]:
    return {
        symbol: int(value)
        for symbol, value in SIGNAL_ENUM_RE.findall(header)
        if symbol != "COUNT"
    }


def parse_expressions(source: str, header: str) -> dict[str, dict[str, Any]]:
    ids = parse_expression_ids(header)
    parsed: dict[str, dict[str, Any]] = {}
    for symbol, priority, name, title, body, footer in EXPRESSION_DEF_RE.findall(source):
        parsed[name] = {
            "id": ids.get(symbol),
            "symbol": symbol,
            "name": name,
            "priority": int(priority),
            "title": title,
            "body": body,
            "footer": footer,
            "stability": "stable" if name in STABLE_EXPRESSIONS else "transient",
        }
    return parsed


def parse_signals(source: str, header: str) -> dict[str, dict[str, Any]]:
    ids = parse_signal_ids(header)
    parsed: dict[str, dict[str, Any]] = {}
    for signal, expression_symbol, may_lower, reason in SIGNAL_DEF_RE.findall(source):
        expression = expression_symbol.lower()
        parsed[signal] = {
            "id": ids.get(signal),
            "signal": signal,
            "expression": expression,
            "may_lower_priority": may_lower == "true",
            "reason": reason,
        }
    return parsed


def parse_auto_recovery(header: str) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for symbol, value in AUTO_RECOVER_DEFINE_RE.findall(header):
        name = symbol.lower()
        if name == "disabled":
            continue
        parsed[name] = int(value)
    return parsed


def ordered_expressions(expressions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [expressions[name] for name in sorted(expressions, key=lambda item: int(expressions[item]["id"]))]


def ordered_signals(signals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [signals[name] for name in sorted(signals, key=lambda item: int(signals[item]["id"]))]


def can_apply_lower_priority_signal(current: str, signal: dict[str, Any]) -> bool:
    if signal["signal"] == "SETTINGS_SLEEPY" and current == "idle":
        return True
    if signal["signal"] == "BATTERY_RECOVERED" and current == "low_battery":
        return True
    return bool(signal["may_lower_priority"])


def simulate_case(current: str, signal: dict[str, Any], expressions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    target = str(signal["expression"])
    current_priority = int(expressions[current]["priority"])
    target_priority = int(expressions[target]["priority"])
    priority_delta = target_priority - current_priority

    if signal["signal"] == "BATTERY_RECOVERED" and current != "low_battery":
        outcome = "guarded_battery_recovered"
        applied = False
        next_expression = current
    elif target == current:
        outcome = "suppressed_duplicate"
        applied = False
        next_expression = current
    elif target_priority < current_priority and not can_apply_lower_priority_signal(current, signal):
        outcome = "blocked_lower_priority"
        applied = False
        next_expression = current
    else:
        outcome = "applied"
        applied = True
        next_expression = target

    return {
        "current": current,
        "signal": signal["signal"].lower(),
        "target": target,
        "current_priority": current_priority,
        "target_priority": target_priority,
        "priority_delta": priority_delta,
        "may_lower_priority": bool(signal["may_lower_priority"]),
        "applied": applied,
        "outcome": outcome,
        "next_expression": next_expression,
    }


def build_pairwise_matrix(
    expressions: dict[str, dict[str, Any]],
    signals: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for expression in ordered_expressions(expressions):
        current = str(expression["name"])
        for signal in ordered_signals(signals):
            matrix.append(simulate_case(current, signal, expressions))
    return matrix


def build_auto_recovery_matrix(
    expressions: dict[str, dict[str, Any]],
    auto_recovery: dict[str, int],
) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for expression in ordered_expressions(expressions):
        name = str(expression["name"])
        recover_ms = int(auto_recovery.get(name, 0))
        matrix.append(
            {
                "expression": name,
                "stability": expression["stability"],
                "auto_recover_ms": recover_ms,
                "recovers_to": "idle" if recover_ms else None,
            }
        )
    return matrix


def fixture_from_sources(header: str, source: str) -> dict[str, Any]:
    expressions = parse_expressions(source, header)
    signals = parse_signals(source, header)
    auto_recovery = parse_auto_recovery(header)
    pairwise = build_pairwise_matrix(expressions, signals)
    outcomes = Counter(str(case["outcome"]) for case in pairwise)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Exhaustive ExpressionV1 state/signal priority matrix for WB55 and future WBA scheduler adapters.",
        "sources": {
            "firmware_header": rel(EXPRESSION_HEADER),
            "firmware_source": rel(EXPRESSION_SOURCE),
            "catalog_fixture": rel(CATALOG_FIXTURE),
            "firmware_state_fixture": rel(FIRMWARE_STATE_FIXTURE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "readme": rel(README),
        },
        "expressions": ordered_expressions(expressions),
        "signals": ordered_signals(signals),
        "acceptance": {
            "expression_count": len(expressions),
            "signal_count": len(signals),
            "pairwise_case_count": len(pairwise),
            "higher_priority_signals_apply": True,
            "duplicate_same_expression_suppressed": True,
            "lower_priority_without_permission_blocked": True,
            "may_lower_priority_signals_can_lower": True,
            "settings_sleepy_only_lowers_idle": True,
            "battery_recovered_only_clears_low_battery": True,
            "transient_faces_auto_recover_to_idle": True,
            "stable_faces_do_not_auto_recover": True,
        },
        "priority_order_low_to_high": [
            entry["name"]
            for entry in sorted(ordered_expressions(expressions), key=lambda item: int(item["priority"]))
        ],
        "pairwise_outcome_counts": dict(sorted(outcomes.items())),
        "pairwise_matrix": pairwise,
        "auto_recovery_matrix": build_auto_recovery_matrix(expressions, auto_recovery),
        "validation_commands": [
            "python .\\tools\\verify_expression_priority_matrix.py",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_firmware_state.py",
            "python .\\tools\\verify_expression_journeys.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def build_fixture() -> dict[str, Any]:
    return fixture_from_sources(
        EXPRESSION_HEADER.read_text(encoding="utf-8"),
        EXPRESSION_SOURCE.read_text(encoding="utf-8"),
    )


def check_matrix(data: dict[str, Any], errors: list[str]) -> None:
    expressions = {str(entry["name"]): entry for entry in data.get("expressions", [])}
    signals = {str(entry["signal"]).upper(): entry for entry in data.get("signals", [])}
    pairwise = data.get("pairwise_matrix", [])
    recoveries = {str(entry["expression"]): entry for entry in data.get("auto_recovery_matrix", [])}
    acceptance = data.get("acceptance", {})

    require(data.get("schema_id") == SCHEMA_ID, "unexpected expression priority matrix schema", errors)
    require(data.get("status") == "PASS", "priority matrix fixture must be PASS", errors)
    require(set(expressions) == set(EXPECTED_PRIORITIES), "expression priority matrix expression set drifted", errors)
    for name, expected_priority in EXPECTED_PRIORITIES.items():
        if name in expressions:
            require(expressions[name].get("priority") == expected_priority, f"{name} priority drifted", errors)
    require(
        data.get("priority_order_low_to_high") == [name for name, _ in sorted(EXPECTED_PRIORITIES.items(), key=lambda item: item[1])],
        "expression priority ordering drifted",
        errors,
    )
    require(acceptance.get("expression_count") == 10, "priority matrix expression count drifted", errors)
    require(acceptance.get("signal_count") == 18, "priority matrix signal count drifted", errors)
    require(acceptance.get("pairwise_case_count") == 180, "priority matrix pairwise case count drifted", errors)
    require(len(pairwise) == 180, "priority matrix must cover every expression/signal pair", errors)

    cases_by_key = {
        (str(case.get("current")), str(case.get("signal")).upper()): case
        for case in pairwise
        if isinstance(case, dict)
    }
    require(len(cases_by_key) == 180, "priority matrix has duplicate or missing expression/signal keys", errors)
    for current in expressions:
        for signal in signals:
            case = cases_by_key.get((current, signal))
            require(case is not None, f"priority matrix missing case {current}/{signal}", errors)
            if case is None:
                continue
            target = str(case.get("target"))
            target_priority = int(case.get("target_priority", -1))
            current_priority = int(case.get("current_priority", -1))
            if signal == "BATTERY_RECOVERED" and current != "low_battery":
                require(case.get("outcome") == "guarded_battery_recovered", f"{current}/{signal} must be guarded", errors)
                require(case.get("applied") is False, f"{current}/{signal} must not apply", errors)
            elif target == current:
                require(case.get("outcome") == "suppressed_duplicate", f"{current}/{signal} must suppress duplicate", errors)
                require(case.get("applied") is False, f"{current}/{signal} duplicate must not refresh", errors)
            elif target_priority > current_priority:
                require(case.get("outcome") == "applied", f"{current}/{signal} higher-priority signal must apply", errors)
            elif target_priority < current_priority and can_apply_lower_priority_signal(current, signals[signal]):
                require(case.get("outcome") == "applied", f"{current}/{signal} permitted lower-priority signal must apply", errors)
            elif target_priority < current_priority and not can_apply_lower_priority_signal(current, signals[signal]):
                require(case.get("outcome") == "blocked_lower_priority", f"{current}/{signal} lower-priority signal must be blocked", errors)

    for current in expressions:
        case = cases_by_key.get((current, "SETTINGS_SLEEPY"))
        if case is None:
            continue
        if current == "idle":
            require(case.get("outcome") == "applied", "settings sleepy must lower idle to sleepy", errors)
        elif current != "sleepy":
            require(case.get("outcome") == "blocked_lower_priority", f"settings sleepy must not hide {current}", errors)
    for current in expressions:
        case = cases_by_key.get((current, "BATTERY_RECOVERED"))
        if case is None:
            continue
        expected = "applied" if current == "low_battery" else "guarded_battery_recovered"
        require(case.get("outcome") == expected, f"battery recovered guard drifted for {current}", errors)

    for name in STABLE_EXPRESSIONS:
        require(recoveries.get(name, {}).get("auto_recover_ms") == 0, f"stable face {name} must not auto-recover", errors)
        require(recoveries.get(name, {}).get("recovers_to") is None, f"stable face {name} must not recover to another face", errors)
    for name in set(EXPECTED_PRIORITIES) - STABLE_EXPRESSIONS:
        require(recoveries.get(name, {}).get("auto_recover_ms", 0) > 0, f"transient face {name} must have recovery dwell", errors)
        require(recoveries.get(name, {}).get("recovers_to") == "idle", f"transient face {name} must recover to idle", errors)

    for key in [
        "higher_priority_signals_apply",
        "duplicate_same_expression_suppressed",
        "lower_priority_without_permission_blocked",
        "may_lower_priority_signals_can_lower",
        "settings_sleepy_only_lowers_idle",
        "battery_recovered_only_clears_low_battery",
        "transient_faces_auto_recover_to_idle",
        "stable_faces_do_not_auto_recover",
    ]:
        require(acceptance.get(key) is True, f"priority matrix acceptance flag missing {key}", errors)


def check_firmware_tokens(errors: list[str]) -> None:
    source = read(EXPRESSION_SOURCE, errors)
    for token in [
        "can_apply_lower_priority_signal",
        "decision.expression == state->current",
        "state->suppressed_duplicate_count++",
        "decision.priority < state->priority",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "state->current == COMP_EPAPER_EXPRESSION_IDLE",
        "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
        "state->current != COMP_EPAPER_EXPRESSION_LOW_BATTERY",
        "comp_epaper_expression_state_tick",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY",
    ]:
        require(token in source, f"expression_state.c missing priority matrix token {token}", errors)


def check_cross_fixtures(data: dict[str, Any], errors: list[str]) -> None:
    catalog = json.loads(read(CATALOG_FIXTURE, errors) or "{}")
    firmware = json.loads(read(FIRMWARE_STATE_FIXTURE, errors) or "{}")
    catalog_priorities = {str(entry.get("name")): entry.get("priority") for entry in catalog.get("expressions", [])}
    matrix_priorities = {str(entry.get("name")): entry.get("priority") for entry in data.get("expressions", [])}
    require(catalog_priorities == matrix_priorities, "priority matrix drifted from expression catalog priorities", errors)
    require(
        firmware.get("state_machine", {}).get("battery_recovery_guard")
        == "only low_battery can be lowered to idle by a recovered battery sample",
        "firmware state fixture missing battery recovery guard",
        errors,
    )
    require(
        firmware.get("acceptance", {}).get("stable_expressions_do_not_auto_recover") is True,
        "firmware state fixture missing stable auto-recovery guard",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(SCREEN_DOC, errors).split()).lower()
    wba_rules = " ".join(read(WBA_RULES, errors).split()).lower()
    readme = " ".join(read(README, errors).split()).lower()
    for token in [
        "expression priority matrix",
        "expression_priority_matrix",
        "companion-screen-expression-priority-matrix.json",
        "verify_expression_priority_matrix.py",
        "settings sleepy",
        "battery recovered",
    ]:
        require(token.lower() in screen_doc, f"screen doc missing priority matrix anchor {token}", errors)
    for token in [
        "expression priority matrix",
        "verify_expression_priority_matrix.py",
        "settings sleepy",
        "battery recovered",
    ]:
        require(token.lower() in wba_rules, f"WBA rules missing priority matrix anchor {token}", errors)
    for token in [
        "expression priority matrix",
        "verify_expression_priority_matrix.py",
    ]:
        require(token.lower() in readme, f"e-paper README missing priority matrix anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression priority matrix fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_matrix(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic priority matrix fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_matrix(expected, errors)
    check_firmware_tokens(errors)
    check_cross_fixtures(expected, errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: ExpressionV1 priority matrix checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: ExpressionV1 priority matrix verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
