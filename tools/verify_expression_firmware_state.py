#!/usr/bin/env python3
"""Verify firmware-side ExpressionV1 state matches the renderer and policy."""

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


EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EXPRESSION_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
EXPRESSION_EVENTS = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
DISPLAY_QUEUE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-firmware-expression-state.json")
SCHEMA_ID = "companion.pendant.firmware_expression_state.v1"


EXPRESSION_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(\d+)u,\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\}'
)
SIGNAL_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(true|false),\s*"([^"]+)"\}'
)

EXPECTED_SIGNAL_MAP = {
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

AUTO_RECOVERY_MS = {
    "happy": 6000,
    "listening": 10000,
    "speaking": 10000,
    "sync_complete": 8000,
    "thinking": 12000,
}

STABLE_EXPRESSIONS = [
    "error",
    "idle",
    "low_battery",
    "recording",
    "sleepy",
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


def parse_expression_table(source: str) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for match in EXPRESSION_RE.finditer(source):
        symbol, priority, name, title, body, footer = match.groups()
        parsed[name] = {
            "symbol": symbol,
            "name": name,
            "priority": int(priority),
            "title": title,
            "body": body,
            "footer": footer,
        }
    return parsed


def parse_signal_table(source: str) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for match in SIGNAL_RE.finditer(source):
        signal, expression_symbol, may_lower, reason = match.groups()
        parsed[signal] = {
            "signal": signal,
            "expression": symbol_to_expression(expression_symbol),
            "may_lower_priority": may_lower == "true",
            "reason": reason,
        }
    return parsed


def build_fixture() -> dict[str, Any]:
    source = EXPRESSION_SOURCE.read_text(encoding="utf-8")
    expressions = parse_expression_table(source)
    signals = parse_signal_table(source)
    return {
        "schema_id": SCHEMA_ID,
        "sources": {
            "firmware_header": rel(EXPRESSION_HEADER),
            "firmware_source": rel(EXPRESSION_SOURCE),
            "firmware_event_bridge": rel(EXPRESSION_EVENTS),
            "display_queue": rel(DISPLAY_QUEUE),
            "wb55_integration": rel(APP_BLE),
            "renderer": "app/companion_pendant/epaper/card_renderer.py",
            "policy": "app/companion_pendant/epaper/expression_policy.py",
        },
        "expressions": [expressions[name] for name in sorted(expressions)],
        "signals": [signals[name] for name in sorted(signals)],
        "state_machine": {
            "first_boot_idle_enqueues": True,
            "visible_age_counter": "visible_age_ms",
            "duplicate_visible_expression_suppressed": True,
            "duplicate_suppression_counter": "suppressed_duplicate_count",
            "last_signal_tracked": True,
            "state_snapshot_api": "comp_epaper_expression_state_snapshot",
            "signal_preflight_api": "comp_epaper_expression_signal_is_supported",
            "auto_recovery_api": "comp_epaper_expression_state_tick",
            "auto_recovery_ms": AUTO_RECOVERY_MS,
            "stable_expressions": STABLE_EXPRESSIONS,
            "auto_recovery_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY",
            "battery_recovery_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
            "battery_recovery_guard": "only low_battery can be lowered to idle by a recovered battery sample",
        },
        "wb55_tick_hook": {
            "timer_server": "HW_TS",
            "timer_mode": "hw_ts_SingleShot",
            "timer_callback": "Companion_Display_TickTimerElapsed",
            "task": "Companion_Display_Task",
            "elapsed_time_source": "HAL_GetTick",
            "tick_api": "comp_epaper_expression_state_tick",
            "recovery_enqueue_path": "Companion_Display_EnqueueExpressionDecision",
        },
        "wb55_settings_hook": {
            "settings_source": "SettingsV1",
            "quiet_hours_flag": "COMPANION_SETTINGS_FLAG_QUIET_HOURS_ACTIVE",
            "display_off_field": "display_brightness",
            "sleepy_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
            "stable_state_guard": "portable expression priority/state gate",
            "settings_recovery_guard": "last_signal == COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        },
        "acceptance": {
            "portable_c_state": True,
            "matches_renderer_copy": True,
            "matches_policy_priority": True,
            "wb55_event_path_enqueues_expression": True,
            "wb55_boot_idle_enqueued": True,
            "duplicate_expression_suppressed": True,
            "expression_state_snapshot": True,
            "transient_auto_recovery_to_idle": True,
            "stable_expressions_do_not_auto_recover": True,
            "wb55_expression_tick_scheduler": True,
            "wb55_settings_expression_hint": True,
            "battery_recovery_only_clears_low_battery": True,
            "unknown_signal_guard": True,
            "wba_safe_adapter_boundary": True,
        },
    }


def check_expression_table(expressions: dict[str, dict[str, Any]], errors: list[str]) -> None:
    require(set(expressions) == EXPRESSION_KINDS, f"C expression set mismatch: {sorted(set(expressions) ^ EXPRESSION_KINDS)}", errors)
    for name in sorted(EXPRESSION_KINDS):
        if name not in expressions:
            continue
        entry = expressions[name]
        title, body, footer = EXPRESSION_COPY[name]
        require(entry["priority"] == EXPRESSION_PRIORITIES[name], f"{name} priority mismatch", errors)
        require(entry["title"] == title, f"{name} title mismatch", errors)
        require(entry["body"] == body, f"{name} body mismatch", errors)
        require(entry["footer"] == footer, f"{name} footer mismatch", errors)


def check_signal_table(signals: dict[str, dict[str, Any]], errors: list[str]) -> None:
    require(set(signals) == set(EXPECTED_SIGNAL_MAP), f"C signal set mismatch: {sorted(set(signals) ^ set(EXPECTED_SIGNAL_MAP))}", errors)
    for signal, expected_expression in EXPECTED_SIGNAL_MAP.items():
        if signal not in signals:
            continue
        require(
            signals[signal]["expression"] == expected_expression,
            f"{signal} maps to {signals[signal]['expression']}, expected {expected_expression}",
            errors,
        )
        require(signals[signal]["reason"], f"{signal} is missing human-readable reason", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = APP_BLE.read_text(encoding="utf-8")
    queue = DISPLAY_QUEUE.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")
    expression_header = EXPRESSION_HEADER.read_text(encoding="utf-8")
    expression_source = EXPRESSION_SOURCE.read_text(encoding="utf-8")
    for token in [
        "comp_epaper_expression_state_snapshot_t",
        "comp_epaper_expression_signal_t last_signal;",
        "uint32_t visible_age_ms;",
        "uint32_t suppressed_duplicate_count;",
        "comp_epaper_expression_auto_recover_ms",
        "comp_epaper_expression_signal_is_supported",
        "comp_epaper_expression_state_tick",
        "comp_epaper_expression_state_snapshot",
    ]:
        require(token in expression_header, f"expression_state.h missing duplicate-suppression field {token}", errors)
    for token in [
        "state->last_signal = COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE;",
        "state->visible_age_ms = 0u;",
        "state->suppressed_duplicate_count = 0u;",
        "decision.expression == state->current",
        "state->suppressed_duplicate_count++",
        "state->visible_age_ms += elapsed_ms;",
        "out_snapshot->current = state->current;",
        "out_snapshot->auto_recover_ms = comp_epaper_expression_auto_recover_ms(state->current);",
        "out_snapshot->suppressed_duplicate_count = state->suppressed_duplicate_count;",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_LISTENING_MS",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_THINKING_MS",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SPEAKING_MS",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_HAPPY_MS",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SYNC_COMPLETE_MS",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
        "state->current == COMP_EPAPER_EXPRESSION_IDLE",
        "state->current != COMP_EPAPER_EXPRESSION_LOW_BATTERY",
        "return find_signal(signal) != NULL;",
        "return false;",
    ]:
        require(token in expression_source, f"expression_state.c missing duplicate-suppression token {token}", errors)
    for token in [
        "comp_epaper_expression_state_apply_signal",
        "comp_epaper_display_queue_enqueue_expression",
        "comp_epaper_expression_signal_from_diag_event",
        "COMPANION_EPAPER_EXPRESSION_CARD_SLOT",
        "COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE",
        "Companion_Display_CreateExpressionTickTimer();",
        "HW_TS_Create(CFG_TIM_PROC_ID_ISR",
        "hw_ts_SingleShot",
        "Companion_Display_TickTimerElapsed",
        "Companion_Display_ProcessExpressionTick();",
        "comp_epaper_expression_state_snapshot(&s_companion_expression_state",
        "comp_epaper_expression_state_tick",
        "Companion_Display_EnqueueExpressionDecision",
        "Companion_Display_ScheduleExpressionTick",
        "COMPANION_SETTINGS_FLAG_QUIET_HOURS_ACTIVE",
        "Companion_Settings_WantsSleepy",
        "Companion_Display_ApplySettingsExpressionHint",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "s_companion_expression_state.last_signal ==",
        "CFG_TS_TICK_VAL",
        "s_companion_expression_state = *previous_state",
        "COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST",
        "COMP_DIAG_EVT_MEETING_FINALIZE",
        "COMP_DIAG_EVT_WAKE_WORD_DETECTED",
    ]:
        require(token in app_ble, f"WB55 app_ble.c missing expression integration token {token}", errors)
    display_registration = "UTIL_SEQ_RegTask(1 << CFG_TASK_COMPANION_DISPLAY_ID"
    boot_idle_call = "Companion_Display_EnqueueExpressionSignal(COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE"
    require(display_registration in app_ble, "WB55 app_ble.c missing display task registration", errors)
    require(boot_idle_call in app_ble, "WB55 app_ble.c does not enqueue boot idle expression", errors)
    if display_registration in app_ble and boot_idle_call in app_ble:
        require(
            app_ble.index(display_registration) < app_ble.index(boot_idle_call),
            "boot idle expression must be enqueued after display task registration",
            errors,
        )
    require("COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION" in queue, "display queue does not store expression request kind", errors)
    require("expression_state.c" in makefile, "WB55 build does not compile expression_state.c", errors)
    require("Firmware ExpressionV1 state path" in plan, "screen expression doc missing firmware state acceptance item", errors)
    require("Expression transient auto recovery" in plan, "screen expression doc missing transient auto recovery acceptance item", errors)
    require("WB55 expression tick scheduler" in plan, "screen expression doc missing WB55 expression tick scheduler acceptance item", errors)
    require("WB55 settings expression hint" in plan, "screen expression doc missing WB55 settings expression hint acceptance item", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing firmware expression fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic firmware state fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [EXPRESSION_HEADER, EXPRESSION_SOURCE, EXPRESSION_EVENTS, DISPLAY_QUEUE, APP_BLE, MAKEFILE, PLAN_DOC]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if errors:
        expected = {"schema_id": SCHEMA_ID, "errors": errors}
    else:
        source = EXPRESSION_SOURCE.read_text(encoding="utf-8")
        expressions = parse_expression_table(source)
        signals = parse_signal_table(source)
        check_expression_table(expressions, errors)
        check_signal_table(signals, errors)
        check_wb55_integration(errors)
        expected = build_fixture()

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion firmware ExpressionV1 state checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion firmware ExpressionV1 state verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
