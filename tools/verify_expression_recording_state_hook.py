#!/usr/bin/env python3
"""Verify Recording FSM state snapshots map to portable ExpressionV1 signals."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.expression_policy import expression_from_status  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-recording-state-expression-hook.json")
SCHEMA_ID = "companion.pendant.screen_recording_state_expression_hook.v1"

EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
POLICY = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_policy.py"
RECORDING_FSM = REPO_ROOT / "app" / "companion_pendant" / "recording" / "recording_fsm.h"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
GATT_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"

FSM_ENUM_RE = re.compile(r"COMP_RECORDING_STATE_([A-Z_]+)(?:\s*=\s*(\d+))?,")
EVENT_CONST_RE = re.compile(r"#define COMP_EPAPER_EXPRESSION_RECORDING_STATE_([A-Z_]+)\s+(\d+)u")

EXPECTED_STATES = [
    ("IDLE", 0, None, "idle"),
    ("PENDING_START", 1, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START", "recording"),
    ("RECORDING", 2, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START", "recording"),
    ("STOPPING", 3, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP", "thinking"),
    ("CANCELED", 4, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL", "idle"),
    ("TRANSFER_READY", 5, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED", "sync_complete"),
    ("TRANSFER_ACTIVE", 6, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED", "sync_complete"),
    ("TRANSFERRED", 7, "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED", "sync_complete"),
    ("ERROR_RECOVERY", 8, "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR", "error"),
]


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


def parse_recording_fsm_states(text: str) -> dict[str, int]:
    states: dict[str, int] = {}
    next_value = 0
    for symbol, explicit in FSM_ENUM_RE.findall(text):
        value = int(explicit) if explicit else next_value
        states[symbol] = value
        next_value = value + 1
    return states


def parse_event_state_constants(text: str) -> dict[str, int]:
    return {symbol: int(value) for symbol, value in EVENT_CONST_RE.findall(text)}


def build_fixture() -> dict[str, Any]:
    cases = []
    for symbol, value, signal, expression in EXPECTED_STATES:
        decision = expression_from_status(
            {
                "device_status": {"active_mode": 2},
                "recording_status": {"state": value},
            }
        )
        cases.append(
            {
                "state": symbol.lower(),
                "state_value": value,
                "expected_signal": signal,
                "expected_expression": expression,
                "policy_expression": decision.expression,
                "policy_reason": decision.reason,
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Recording FSM state snapshots can feed ExpressionV1 without depending on WB55 or WBA platform glue.",
        "sources": {
            "event_bridge_header": rel(EVENTS_HEADER),
            "event_bridge_source": rel(EVENTS_SOURCE),
            "policy": rel(POLICY),
            "recording_fsm": rel(RECORDING_FSM),
            "screen_acceptance": rel(PLAN_DOC),
            "epaper_readme": rel(README),
            "wba_rules": rel(WBA_RULES),
            "gatt_contract": rel(GATT_CONTRACT),
        },
        "portable_mapper": "comp_epaper_expression_signal_from_recording_state",
        "cases": cases,
        "acceptance": {
            "recording_fsm_enum_values_locked": True,
            "recording_state_idle_has_no_expression_override": True,
            "recording_state_active_maps_to_recording": True,
            "recording_state_stopping_maps_to_thinking": True,
            "recording_state_transfer_maps_to_sync_complete": True,
            "recording_state_error_recovery_maps_to_error": True,
            "unknown_recording_state_is_ignored": True,
            "wba_safe_recording_state_mapper": True,
        },
    }


def check_state_values(errors: list[str]) -> None:
    fsm_states = parse_recording_fsm_states(read(RECORDING_FSM, errors))
    event_states = parse_event_state_constants(read(EVENTS_HEADER, errors))
    for symbol, value, _signal, _expression in EXPECTED_STATES:
        require(
            fsm_states.get(symbol) == value,
            f"recording_fsm.h state {symbol} value drifted from {value}",
            errors,
        )
        require(
            event_states.get(symbol) == value,
            f"expression_events.h recording state {symbol} value drifted from {value}",
            errors,
        )


def check_mapper(errors: list[str]) -> None:
    header = read(EVENTS_HEADER, errors)
    source = read(EVENTS_SOURCE, errors)
    policy = read(POLICY, errors)
    require(
        "bool comp_epaper_expression_signal_from_recording_state(" in header,
        "expression_events.h missing recording state mapper declaration",
        errors,
    )
    require(
        "bool comp_epaper_expression_signal_from_recording_state(" in source,
        "expression_events.c missing recording state mapper implementation",
        errors,
    )
    for symbol, _value, signal, _expression in EXPECTED_STATES:
        token = f"COMP_EPAPER_EXPRESSION_RECORDING_STATE_{symbol}"
        require(token in header, f"expression_events.h missing recording state constant {token}", errors)
        if signal is not None:
            require(token in source, f"expression_events.c missing mapper branch for {token}", errors)
            require(signal in source, f"expression_events.c missing mapper signal {signal}", errors)
    for token in [
        "default:",
        "return false;",
        "recording_status",
        "RECORDING_STATE_TRANSFER_READY",
        "RECORDING_STATE_ERROR_RECOVERY",
    ]:
        require(token in source + policy, f"recording state mapper missing token {token}", errors)


def check_policy(errors: list[str]) -> None:
    for symbol, value, _signal, expression in EXPECTED_STATES:
        decision = expression_from_status(
            {
                "device_status": {"active_mode": 2},
                "recording_status": {"state": value},
            }
        )
        require(
            decision.expression == expression,
            f"policy maps recording state {symbol} to {decision.expression}, expected {expression}",
            errors,
        )
    decision = expression_from_status(
        {
            "device_status": {"active_mode": 2},
            "recording_status": {"state": 255},
        }
    )
    require(decision.expression == "idle", "unknown recording states must not override idle status", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(PLAN_DOC, errors).split()).lower()
    readme = " ".join(read(README, errors).split()).lower()
    wba_rules = " ".join(read(WBA_RULES, errors).split()).lower()
    gatt_contract = " ".join(read(GATT_CONTRACT, errors).split()).lower()
    for token in [
        "recording fsm state expression hook",
        "recording_state_expression_hook",
        "companion-screen-recording-state-expression-hook.json",
        "comp_epaper_expression_signal_from_recording_state",
    ]:
        require(token in screen_doc, f"screen expression doc missing recording state hook anchor {token}", errors)
    for token in [
        "recording fsm state snapshots",
        "comp_epaper_expression_signal_from_recording_state",
    ]:
        require(token in readme, f"e-paper README missing recording state hook anchor {token}", errors)
    for token in [
        "recording fsm state",
        "wba recording adapter",
        "comp_epaper_expression_signal_from_recording_state",
    ]:
        require(token in wba_rules, f"WBA rules missing recording state hook anchor {token}", errors)
    for token in [
        "recordingcontrolv1",
        "idle, recording, stopping, stored, or failed",
    ]:
        require(token in gatt_contract, f"GATT contract missing recording state hook anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing recording state expression fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic recording state expression fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_fixture()

    check_state_values(errors)
    check_mapper(errors)
    check_policy(errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion Recording FSM state expression hook checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion Recording FSM state expression hook verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
