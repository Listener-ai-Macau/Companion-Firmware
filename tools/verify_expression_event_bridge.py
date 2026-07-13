#!/usr/bin/env python3
"""Verify the firmware diagnostic-event to ExpressionV1 bridge."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.expression_policy import expression_from_event  # noqa: E402


EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-event-bridge.json")
SCHEMA_ID = "companion.pendant.expression_event_bridge.v1"


EVENT_RE = re.compile(
    r"\{COMP_DIAG_EVT_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+)\}"
)

SIGNAL_EXPRESSION = {
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
    "BATTERY_RECOVERED": "idle",
}

EXPECTED_EVENT_NAMES = {
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


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_event_table(source: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for event_symbol, signal in EVENT_RE.findall(source):
        parsed[f"COMP_DIAG_EVT_{event_symbol}"] = signal
    return parsed


def build_fixture() -> dict[str, Any]:
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    event_table = parse_event_table(source)
    mappings = []
    for event_code in sorted(event_table):
        signal = event_table[event_code]
        mappings.append(
            {
                "event_code": event_code,
                "event_name": EXPECTED_EVENT_NAMES.get(event_code, "unknown"),
                "expression_signal": signal,
                "expression": SIGNAL_EXPRESSION[signal],
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "sources": {
            "event_bridge_header": rel(EVENTS_HEADER),
            "event_bridge_source": rel(EVENTS_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(PLAN_DOC),
        },
        "event_mappings": mappings,
        "special_cases": {
            "device_status.active_mode_fault_bitmap": {
                "expression": "sleepy_or_recording_or_error",
                "condition": "faults map to error, active audio maps to recording, disconnected maps to low-priority sleepy",
            },
            "interaction_status.meeting_speaker_wake": {
                "expression": "recording_thinking_sync_speaking_listening_idle_or_error",
                "condition": "MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 mirror control diagnostic semantics",
            },
            "battery_charging.sample": {
                "expression": "low_battery_or_battery_recovered",
                "condition": "percent <= 20 or millivolts < 3600 while not charging maps low; percent >= 25 or charging at >= 3600 mV maps recovered",
            },
            "recording_fsm.state": {
                "expression": "recording_thinking_sync_complete_idle_or_error",
                "condition": "recording FSM state snapshots map through comp_epaper_expression_signal_from_recording_state without platform dependencies",
            },
            "wb55_batterychargev1_hook": {
                "expression": "low_battery",
                "condition": "post-startup BatteryChargeV1 publishes feed battery_charging.sample",
            },
            "ota_readiness.blocker_bitmap": {
                "expression": "low_battery_or_error",
                "condition": "low-battery blocker maps to low_battery; other nonzero blockers map to error",
            },
            "e_paper.*": {
                "expression": None,
                "condition": "ignored by firmware bridge to prevent display-update self loops",
            },
            "severity_error_fallback": {
                "expression": "error",
                "condition": "non-e-paper events with severity >= error",
            },
        },
    }


def check_event_table(errors: list[str]) -> None:
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    parsed = parse_event_table(source)
    require(set(parsed) == set(EXPECTED_EVENT_NAMES), f"event bridge table mismatch: {sorted(set(parsed) ^ set(EXPECTED_EVENT_NAMES))}", errors)
    for event_code, event_name in EXPECTED_EVENT_NAMES.items():
        if event_code not in parsed:
            continue
        signal = parsed[event_code]
        expression = SIGNAL_EXPRESSION.get(signal)
        require(expression is not None, f"{event_code} uses unknown signal {signal}", errors)
        if event_name.endswith(".rejected") or event_name.endswith(".error") or event_name.startswith("errors."):
            require(expression == "error", f"{event_name} should map to error", errors)
        elif event_name in {
            "battery_charging.sample",
            "e_paper.update_result",
            "e_paper.render_request",
        }:
            continue
        else:
            policy_expression = expression_from_event(event_name).expression
            require(
                policy_expression == expression,
                f"{event_name} C bridge maps to {expression}, Python policy maps to {policy_expression}",
                errors,
            )


def check_special_cases(errors: list[str]) -> None:
    header = EVENTS_HEADER.read_text(encoding="utf-8")
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    for token in [
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY_PERCENT 20u",
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY_MV 3600u",
        "COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_PERCENT 25u",
        "COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_MV 3600u",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED 0u",
        "comp_epaper_expression_signal_from_device_status",
        "COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING 1u",
        "COMP_EPAPER_EXPRESSION_RECORDING_STATE_RECORDING 2u",
        "COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_READY 5u",
        "COMP_EPAPER_EXPRESSION_RECORDING_STATE_ERROR_RECOVERY 8u",
        "comp_epaper_expression_signal_from_recording_state",
        "COMP_EPAPER_EXPRESSION_SPEAKER_STATE_PROMPT_ACCEPTED 2u",
        "COMP_EPAPER_EXPRESSION_WAKE_EVENT_DETECTED 2u",
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER_BIT 3u",
        "comp_epaper_expression_signal_from_ota_readiness",
    ]:
        require(token in header, f"event bridge header missing threshold {token}", errors)
    for token in [
        "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
        "low_battery_sample(arg0, arg1, arg2)",
        "battery_recovered_sample(arg0, arg1, arg2)",
        "COMP_DIAG_EVENT_SOURCE(event_code) == (uint8_t)COMP_DIAG_SRC_EPAPER",
        "severity >= COMP_DIAG_SEV_ERROR",
        "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT",
        "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED",
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER",
        "blocker_bitmap != 0u",
    ]:
        require(token in source, f"event bridge source missing special case {token}", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = APP_BLE.read_text(encoding="utf-8")
    for token in [
        '#include "expression_events.h"',
        "Companion_Display_EnqueueExpressionEvent",
        "Companion_Diag_RecordAndEnqueueExpression",
        "comp_epaper_expression_signal_from_diag_event",
        "COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST",
        "COMP_DIAG_EVT_MEETING_FINALIZE",
        "COMP_DIAG_EVT_SPEAKER_PROMPT",
        "COMP_DIAG_EVT_WAKE_WORD_DETECTED",
        "Companion_Display_ApplyBatteryExpressionHint",
        "Companion_Display_ApplyDeviceStatusExpressionHint",
        "Companion_Display_ApplyMeetingStatusExpressionHint",
        "Companion_Display_ApplySpeakerStatusExpressionHint",
        "Companion_Display_ApplyWakeWordStatusExpressionHint",
        "Companion_Display_ApplyOtaExpressionHint",
        "Companion_Gatt_PublishDeviceStatus(false)",
        "Companion_Gatt_PublishDeviceStatus(true)",
        "Companion_Gatt_PublishBatteryCharge(false)",
        "Companion_Gatt_PublishBatteryCharge(true)",
        "Companion_Gatt_PublishMeetingStatus(false)",
        "Companion_Gatt_PublishMeetingStatus(true)",
        "Companion_Gatt_PublishSpeakerStatus(false)",
        "Companion_Gatt_PublishSpeakerStatus(true)",
        "Companion_Gatt_PublishWakeWordStatus(false)",
        "Companion_Gatt_PublishWakeWordStatus(true)",
        "Companion_Gatt_PublishOtaReadiness(false)",
        "Companion_Gatt_PublishOtaReadiness(true)",
        "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
        "comp_epaper_expression_signal_from_device_status",
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
        "comp_epaper_expression_signal_from_ota_readiness",
    ]:
        require(token in app_ble, f"WB55 app_ble.c missing event bridge token {token}", errors)


def check_docs(errors: list[str]) -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    for token in [
        "Diagnostic-event expression bridge",
        "WB55 device status expression hint",
        "WB55 interaction status expression hint",
        "WB55 battery expression hint",
        "WB55 OTA readiness expression hint",
        "expression_events.h/.c",
        "e_paper.*",
        "verify_expression_event_bridge.py",
    ]:
        require(token in text, f"screen expression doc missing event bridge anchor: {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing event bridge fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic event bridge fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [EVENTS_HEADER, EVENTS_SOURCE, APP_BLE, PLAN_DOC]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture() if not errors else {"schema_id": SCHEMA_ID, "errors": errors}

    if not errors:
        check_event_table(errors)
        check_special_cases(errors)
        check_wb55_integration(errors)
        check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion ExpressionV1 event bridge checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 event bridge verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
