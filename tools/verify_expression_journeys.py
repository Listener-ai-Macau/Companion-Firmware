#!/usr/bin/env python3
"""Verify ExpressionV1 user journeys across consecutive events."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import (  # noqa: E402
    DISPLAY_VARIANTS,
    EXPRESSION_COPY,
    EXPRESSION_KINDS,
    CardModel,
    render_card,
    sha256_hex,
)


EXPRESSION_STATE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
EXPRESSION_EVENTS = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-journeys.json")
SCHEMA_ID = "companion.pendant.expression_journeys.v1"


EXPRESSION_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(\d+)u,\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\}'
)
SIGNAL_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(true|false),\s*"([^"]+)"\}'
)
EVENT_RE = re.compile(
    r"\{COMP_DIAG_EVT_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+)\}"
)


EVENT_NAMES = {
    "COMP_DIAG_EVT_WAKE_WORD_ARMED": "wake_word.armed",
    "COMP_DIAG_EVT_WAKE_WORD_DISABLED": "wake_word.disabled",
    "COMP_DIAG_EVT_WAKE_WORD_DETECTED": "wake_word.detected",
    "COMP_DIAG_EVT_WAKE_WORD_REJECTED": "wake_word.rejected",
    "COMP_DIAG_EVT_SPEAKER_PROMPT": "speaker.prompt",
    "COMP_DIAG_EVT_SPEAKER_RESULT": "speaker.result",
    "COMP_DIAG_EVT_SPEAKER_REJECTED": "speaker.rejected",
    "COMP_DIAG_EVT_MEETING_START": "meeting.start",
    "COMP_DIAG_EVT_MEETING_STOP": "meeting.stop",
    "COMP_DIAG_EVT_MEETING_FINALIZE": "meeting.finalize",
    "COMP_DIAG_EVT_MEETING_REJECTED": "meeting.rejected",
    "COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST": "recording_fsm.start_request",
    "COMP_DIAG_EVT_RECORDING_FSM_STOP_REQUEST": "recording_fsm.stop_request",
    "COMP_DIAG_EVT_RECORDING_FSM_CANCEL_REQUEST": "recording_fsm.cancel_request",
    "COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED": "recording_fsm.session_finished",
    "COMP_DIAG_EVT_RECORDING_FSM_REJECTED": "recording_fsm.rejected",
    "COMP_DIAG_EVT_RECORDING_FSM_ERROR": "recording_fsm.error",
    "COMP_DIAG_EVT_RECORDING_FSM_RECOVERY": "recording_fsm.recovery",
    "COMP_DIAG_EVT_WARNINGS_RECOVERED": "warnings.recovered",
    "COMP_DIAG_EVT_ERRORS_ASSERT": "errors.assert",
    "COMP_DIAG_EVT_ERRORS_FAULT": "errors.fault",
}


AUTO_RECOVERY_MS = {
    "happy": 6000,
    "listening": 10000,
    "speaking": 10000,
    "sync_complete": 8000,
    "thinking": 12000,
}


JOURNEYS = [
    {
        "journey_id": "wake_to_recording_sync",
        "steps": [
            {"event": "wake_word.armed", "expected_expression": "idle", "expected_accepted": True},
            {"event": "wake_word.detected", "expected_expression": "listening", "expected_accepted": True},
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {"event": "recording_fsm.stop_request", "expected_expression": "thinking", "expected_accepted": True},
            {"event": "recording_fsm.session_finished", "expected_expression": "sync_complete", "expected_accepted": True},
        ],
    },
    {
        "journey_id": "duplicate_expression_suppressed",
        "steps": [
            {"event": "wake_word.armed", "expected_expression": "idle", "expected_accepted": True},
            {"event": "wake_word.armed", "expected_expression": "idle", "expected_accepted": False},
            {"event": "wake_word.detected", "expected_expression": "listening", "expected_accepted": True},
            {"event": "wake_word.detected", "expected_expression": "listening", "expected_accepted": False},
        ],
    },
    {
        "journey_id": "status_notify_duplicate_suppression",
        "steps": [
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {
                "event": "status.device",
                "payload": {"active_mode": 1, "fault_bitmap": 0},
                "expected_expression": "recording",
                "expected_accepted": False,
            },
            {"event": "meeting.finalize", "expected_expression": "sync_complete", "expected_accepted": True},
            {
                "event": "status.meeting",
                "payload": {"state": 2, "summary_state": 1, "sync_state": 1, "last_error": 0},
                "expected_expression": "sync_complete",
                "expected_accepted": False,
            },
            {"event": "speaker.prompt", "expected_expression": "speaking", "expected_accepted": True},
            {
                "event": "status.speaker",
                "payload": {"state": 2, "last_error": 0},
                "expected_expression": "speaking",
                "expected_accepted": False,
            },
            {"event": "warnings.recovered", "expected_expression": "idle", "expected_accepted": True},
            {"event": "wake_word.detected", "expected_expression": "listening", "expected_accepted": True},
            {
                "event": "status.wake_word",
                "payload": {"armed": 1, "engine_state": 1, "last_event": 2, "last_error": 0},
                "expected_expression": "listening",
                "expected_accepted": False,
            },
        ],
    },
    {
        "journey_id": "recording_low_battery_priority",
        "steps": [
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 12, "millivolts": 3520, "charger_present": 0},
                "expected_expression": "recording",
                "expected_accepted": False,
            },
            {"event": "recording_fsm.stop_request", "expected_expression": "thinking", "expected_accepted": True},
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 12, "millivolts": 3520, "charger_present": 0},
                "expected_expression": "low_battery",
                "expected_accepted": True,
            },
        ],
    },
    {
        "journey_id": "battery_recovery_only_clears_low_battery",
        "steps": [
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 8, "millivolts": 3450, "charger_present": 0},
                "expected_expression": "low_battery",
                "expected_accepted": True,
            },
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 22, "millivolts": 3650, "charger_present": 0},
                "expected_expression": "low_battery",
                "expected_accepted": False,
            },
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 27, "millivolts": 3650, "charger_present": 0},
                "expected_expression": "idle",
                "expected_accepted": True,
            },
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 100, "millivolts": 5000, "charger_present": 1},
                "expected_expression": "recording",
                "expected_accepted": False,
            },
            {"event": "errors.fault", "severity": "error", "expected_expression": "error", "expected_accepted": True},
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 100, "millivolts": 5000, "charger_present": 1},
                "expected_expression": "error",
                "expected_accepted": False,
            },
            {"event": "warnings.recovered", "expected_expression": "idle", "expected_accepted": True},
        ],
    },
    {
        "journey_id": "speaker_prompt_result",
        "steps": [
            {"event": "speaker.prompt", "expected_expression": "speaking", "expected_accepted": True},
            {"event": "speaker.result", "expected_expression": "happy", "expected_accepted": True},
        ],
    },
    {
        "journey_id": "transient_expression_auto_recovery",
        "steps": [
            {"event": "speaker.result", "expected_expression": "happy", "expected_accepted": True},
            {
                "event": "time.elapsed",
                "payload": {"elapsed_ms": 5000},
                "expected_expression": "happy",
                "expected_accepted": False,
            },
            {
                "event": "time.elapsed",
                "payload": {"elapsed_ms": 1000},
                "expected_expression": "idle",
                "expected_accepted": True,
            },
            {"event": "meeting.finalize", "expected_expression": "sync_complete", "expected_accepted": True},
            {
                "event": "time.elapsed",
                "payload": {"elapsed_ms": 8000},
                "expected_expression": "idle",
                "expected_accepted": True,
            },
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {
                "event": "time.elapsed",
                "payload": {"elapsed_ms": 60000},
                "expected_expression": "recording",
                "expected_accepted": False,
            },
        ],
    },
    {
        "journey_id": "wake_reject_recovery",
        "steps": [
            {"event": "wake_word.rejected", "expected_expression": "error", "expected_accepted": True},
            {"event": "warnings.recovered", "expected_expression": "idle", "expected_accepted": True},
            {"event": "wake_word.disabled", "expected_expression": "idle", "expected_accepted": False},
        ],
    },
    {
        "journey_id": "wake_disabled_sleepy",
        "steps": [
            {"event": "wake_word.disabled", "expected_expression": "sleepy", "expected_accepted": True},
        ],
    },
    {
        "journey_id": "settings_sleepy_hint",
        "steps": [
            {"event": "wake_word.armed", "expected_expression": "idle", "expected_accepted": True},
            {"event": "settings.display_off", "expected_expression": "sleepy", "expected_accepted": True},
            {"event": "settings.display_on", "expected_expression": "idle", "expected_accepted": True},
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {"event": "settings.display_off", "expected_expression": "recording", "expected_accepted": False},
            {"event": "recording_fsm.cancel_request", "expected_expression": "idle", "expected_accepted": True},
            {"event": "settings.quiet_hours", "expected_expression": "sleepy", "expected_accepted": True},
        ],
    },
    {
        "journey_id": "display_update_no_self_loop",
        "steps": [
            {"event": "recording_fsm.start_request", "expected_expression": "recording", "expected_accepted": True},
            {
                "event": "e_paper.update_result",
                "payload": {"last_error": 4},
                "severity": "warn",
                "expected_expression": "recording",
                "expected_accepted": False,
            },
        ],
    },
    {
        "journey_id": "error_overrides_and_recovers",
        "steps": [
            {
                "event": "battery_charging.sample",
                "payload": {"percent": 8, "millivolts": 3450, "charger_present": 0},
                "expected_expression": "low_battery",
                "expected_accepted": True,
            },
            {"event": "errors.fault", "severity": "error", "expected_expression": "error", "expected_accepted": True},
            {"event": "speaker.prompt", "expected_expression": "error", "expected_accepted": False},
            {"event": "warnings.recovered", "expected_expression": "idle", "expected_accepted": True},
        ],
    },
    {
        "journey_id": "meeting_capture_finalize",
        "steps": [
            {"event": "meeting.start", "expected_expression": "recording", "expected_accepted": True},
            {"event": "meeting.stop", "expected_expression": "thinking", "expected_accepted": True},
            {"event": "meeting.finalize", "expected_expression": "sync_complete", "expected_accepted": True},
        ],
    },
]


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def symbol_to_expression(symbol: str) -> str:
    return symbol.lower()


def parse_expression_table() -> dict[str, dict[str, Any]]:
    source = EXPRESSION_STATE.read_text(encoding="utf-8")
    parsed: dict[str, dict[str, Any]] = {}
    for symbol, priority, name, title, body, footer in EXPRESSION_RE.findall(source):
        parsed[name] = {
            "symbol": symbol,
            "priority": int(priority),
            "title": title,
            "body": body,
            "footer": footer,
        }
    return parsed


def parse_signal_table() -> dict[str, dict[str, Any]]:
    source = EXPRESSION_STATE.read_text(encoding="utf-8")
    parsed: dict[str, dict[str, Any]] = {}
    for signal, expression_symbol, may_lower, reason in SIGNAL_RE.findall(source):
        parsed[signal] = {
            "expression": symbol_to_expression(expression_symbol),
            "may_lower_priority": may_lower == "true",
            "reason": reason,
        }
    return parsed


def parse_event_table() -> dict[str, str]:
    source = EXPRESSION_EVENTS.read_text(encoding="utf-8")
    by_symbol = {
        f"COMP_DIAG_EVT_{event_symbol}": signal
        for event_symbol, signal in EVENT_RE.findall(source)
    }
    return {
        event_name: by_symbol[event_code]
        for event_code, event_name in EVENT_NAMES.items()
        if event_code in by_symbol
    }


def severity_value(name: str) -> int:
    return {"info": 0, "warn": 1, "error": 2}.get(name, 0)


def low_battery(payload: dict[str, Any]) -> bool:
    percent = int(payload.get("percent", 101))
    millivolts = int(payload.get("millivolts", 5000))
    charger_present = int(payload.get("charger_present", 0)) != 0
    return percent <= 20 or (millivolts < 3600 and not charger_present)


def battery_recovered(payload: dict[str, Any]) -> bool:
    percent = int(payload.get("percent", -1))
    millivolts = int(payload.get("millivolts", 0))
    charger_present = int(payload.get("charger_present", 0)) != 0
    return percent >= 25 or (charger_present and millivolts >= 3600)


def signal_from_status_step(event: str, payload: dict[str, Any]) -> str | None:
    if event == "status.device":
        if int(payload.get("fault_bitmap", 0)) != 0:
            return "ERROR"
        active_mode = int(payload.get("active_mode", 2))
        if active_mode == 1:
            return "RECORDING_START"
        if active_mode == 0:
            return "SETTINGS_SLEEPY"
        return None
    if event == "status.meeting":
        if int(payload.get("last_error", 0)) != 0:
            return "ERROR"
        state = int(payload.get("state", 0))
        if state == 1:
            return "MEETING_START"
        if state == 2 or int(payload.get("sync_state", 0)) == 1:
            return "MEETING_FINALIZE"
        if int(payload.get("summary_state", 0)) == 1:
            return "MEETING_STOP"
        return None
    if event == "status.speaker":
        if int(payload.get("last_error", 0)) != 0:
            return "ERROR"
        if int(payload.get("state", 0)) == 2:
            return "SPEAKER_PROMPT"
        return None
    if event == "status.wake_word":
        if int(payload.get("last_error", 0)) != 0:
            return "ERROR"
        if int(payload.get("last_event", 0)) == 2:
            return "WAKE_DETECTED"
        if int(payload.get("armed", 0)) != 0 or int(payload.get("engine_state", 0)) == 1:
            return "WAKE_ARMED"
        return None
    return None


def signal_from_step(step: dict[str, Any], event_table: dict[str, str]) -> str | None:
    event = str(step["event"])
    payload = dict(step.get("payload", {}))
    if event.startswith("status."):
        return signal_from_status_step(event, payload)
    if event.startswith("e_paper."):
        return None
    if event in {"settings.display_off", "settings.quiet_hours"}:
        return "SETTINGS_SLEEPY"
    if event == "settings.display_on":
        return "RECOVERY"
    if event == "battery_charging.sample":
        if low_battery(payload):
            return "LOW_BATTERY"
        if battery_recovered(payload):
            return "BATTERY_RECOVERED"
        return None
    if event in event_table:
        return event_table[event]
    if severity_value(str(step.get("severity", "info"))) >= 2:
        return "ERROR"
    return None


def render_hashes(expression: str, card_id: str) -> dict[str, str]:
    title, body, footer = EXPRESSION_COPY[expression]
    card = CardModel(
        card_id=card_id,
        card_type="expression",
        state=expression,
        title=title,
        body=body,
        footer=footer,
    )
    return {
        key: sha256_hex(render_card(card, variant))
        for key, variant in DISPLAY_VARIANTS.items()
    }


def simulate_journey(
    journey: dict[str, Any],
    expressions: dict[str, dict[str, Any]],
    signals: dict[str, dict[str, Any]],
    event_table: dict[str, str],
    errors: list[str],
) -> dict[str, Any]:
    current = "idle"
    current_priority = expressions[current]["priority"]
    visible_age_ms = 0
    initialized = False
    steps = []

    for index, step in enumerate(journey["steps"]):
        event = str(step["event"])
        signal: str | None = None
        accepted = False
        auto_recovered = False
        reason = "event has no expression signal"
        if event == "time.elapsed":
            elapsed_ms = int(dict(step.get("payload", {})).get("elapsed_ms", 0))
            visible_age_ms = min(0xFFFFFFFF, visible_age_ms + elapsed_ms)
            recover_ms = AUTO_RECOVERY_MS.get(current, 0)
            reason = f"elapsed {elapsed_ms} ms while {current} is visible"
            if initialized and recover_ms and visible_age_ms >= recover_ms:
                previous_expression = current
                signal = "RECOVERY"
                current = "idle"
                current_priority = expressions[current]["priority"]
                visible_age_ms = 0
                accepted = True
                auto_recovered = True
                reason = f"auto-recovered {previous_expression} to idle after {elapsed_ms} ms"
        else:
            signal = signal_from_step(step, event_table)
        if signal is not None and not auto_recovered:
            require(signal in signals, f"{journey['journey_id']} step {index} unknown signal {signal}", errors)
            if signal in signals:
                signal_def = signals[signal]
                candidate = signal_def["expression"]
                candidate_priority = expressions[candidate]["priority"]
                reason = signal_def["reason"]
                if signal == "BATTERY_RECOVERED" and (not initialized or current != "low_battery"):
                    reason = "battery recovery ignored because low_battery is not visible"
                elif signal == "BATTERY_RECOVERED" and current == "low_battery":
                    current = candidate
                    current_priority = candidate_priority
                    visible_age_ms = 0
                    initialized = True
                    accepted = True
                elif initialized and candidate == current:
                    visible_age_ms = 0
                    reason = f"duplicate visible expression {candidate} suppressed"
                elif signal == "SETTINGS_SLEEPY" and current == "idle":
                    current = candidate
                    current_priority = candidate_priority
                    visible_age_ms = 0
                    initialized = True
                    accepted = True
                elif (not initialized or
                      candidate_priority >= current_priority or
                      signal_def["may_lower_priority"]):
                    current = candidate
                    current_priority = candidate_priority
                    visible_age_ms = 0
                    initialized = True
                    accepted = True
                else:
                    reason = f"ignored lower-priority {candidate} while {current} is visible"

        require(
            current == step["expected_expression"],
            f"{journey['journey_id']} step {index} {event}: visible {current}, expected {step['expected_expression']}",
            errors,
        )
        require(
            accepted == bool(step["expected_accepted"]),
            f"{journey['journey_id']} step {index} {event}: accepted {accepted}, expected {step['expected_accepted']}",
            errors,
        )
        steps.append(
            {
                "index": index,
                "event": event,
                "payload": dict(step.get("payload", {})),
                "severity": str(step.get("severity", "info")),
                "expression_signal": signal,
                "accepted": accepted,
                "visible_expression": current,
                "priority": current_priority,
                "visible_age_ms": visible_age_ms,
                "reason": reason,
                "render_hashes": render_hashes(current, f"{journey['journey_id']}_{index}"),
            }
        )

    return {
        "journey_id": journey["journey_id"],
        "steps": steps,
        "final_expression": current,
    }


def build_fixture(errors: list[str]) -> dict[str, Any]:
    expressions = parse_expression_table()
    signals = parse_signal_table()
    event_table = parse_event_table()
    rendered = [
        simulate_journey(journey, expressions, signals, event_table, errors)
        for journey in JOURNEYS
    ]
    coverage = sorted({step["visible_expression"] for item in rendered for step in item["steps"]})
    return {
        "schema_id": SCHEMA_ID,
        "sources": {
            "expression_state": rel(EXPRESSION_STATE),
            "expression_events": rel(EXPRESSION_EVENTS),
            "renderer": "app/companion_pendant/epaper/card_renderer.py",
            "screen_acceptance": rel(PLAN_DOC),
        },
        "journeys": rendered,
        "coverage": coverage,
        "acceptance": {
            "all_expression_states_covered": set(coverage) == EXPRESSION_KINDS,
            "recording_not_hidden_by_low_battery": True,
            "display_update_no_self_loop": True,
            "error_overrides_lower_priority": True,
            "duplicate_same_expression_suppressed": True,
            "transient_auto_recovery_to_idle": True,
            "stable_recording_does_not_timeout": True,
            "settings_sleepy_hint_does_not_hide_recording": True,
            "status_notify_duplicate_suppression": True,
            "battery_recovery_only_clears_low_battery": True,
        },
    }


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression journeys fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def check_docs(errors: list[str]) -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    for token in [
        "User journey expression acceptance",
        "verify_expression_journeys.py",
        "recording_not_hidden_by_low_battery",
        "display_update_no_self_loop",
        "duplicate_same_expression_suppressed",
        "transient_auto_recovery_to_idle",
        "stable_recording_does_not_timeout",
        "settings_sleepy_hint_does_not_hide_recording",
        "status_notify_duplicate_suppression",
        "battery_recovery_only_clears_low_battery",
        "expression-storyboard.svg",
        "render_expression_storyboard.py",
    ]:
        require(token in text, f"screen expression doc missing journey anchor: {token}", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic journey fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [EXPRESSION_STATE, EXPRESSION_EVENTS, PLAN_DOC]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture(errors) if not errors else {"schema_id": SCHEMA_ID, "errors": errors}
    if expected.get("acceptance", {}).get("all_expression_states_covered") is not True:
        errors.append("journeys do not cover every ExpressionV1 state")

    check_docs(errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion ExpressionV1 journey checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 journeys verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
