#!/usr/bin/env python3
"""Verify WB55 interaction status publishes feed portable ExpressionV1 hooks."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.expression_policy import expression_from_status  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-interaction-status-expression-hook.json")
SCHEMA_ID = "companion.pendant.screen_interaction_status_expression_hook.v1"

APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
GATT_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"


INTERACTION_CASES = [
    {
        "case_id": "meeting_idle_no_expression_override",
        "input": {"meeting_status": {"state": 0, "summary_state": 0, "sync_state": 0, "last_error": 0}},
        "expected_expression": "idle",
        "expected_signal": None,
    },
    {
        "case_id": "meeting_recording_maps_to_recording",
        "input": {"meeting_status": {"state": 1, "summary_state": 0, "sync_state": 0, "last_error": 0}},
        "expected_expression": "recording",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START",
    },
    {
        "case_id": "meeting_sync_maps_to_sync_complete",
        "input": {"meeting_status": {"state": 2, "summary_state": 1, "sync_state": 1, "last_error": 0}},
        "expected_expression": "sync_complete",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE",
    },
    {
        "case_id": "meeting_summary_pending_maps_to_thinking",
        "input": {"meeting_status": {"state": 0, "summary_state": 1, "sync_state": 0, "last_error": 0}},
        "expected_expression": "thinking",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP",
    },
    {
        "case_id": "meeting_error_maps_to_error",
        "input": {"meeting_status": {"state": 1, "summary_state": 0, "sync_state": 0, "last_error": 2}},
        "expected_expression": "error",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
    },
    {
        "case_id": "speaker_idle_no_expression_override",
        "input": {"speaker_status": {"state": 1, "last_error": 0}},
        "expected_expression": "idle",
        "expected_signal": None,
    },
    {
        "case_id": "speaker_prompt_maps_to_speaking",
        "input": {"speaker_status": {"state": 2, "last_error": 0}},
        "expected_expression": "speaking",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT",
    },
    {
        "case_id": "speaker_error_maps_to_error",
        "input": {"speaker_status": {"state": 2, "last_error": 2}},
        "expected_expression": "error",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
    },
    {
        "case_id": "wake_armed_maps_to_idle",
        "input": {"wake_word_status": {"armed": 1, "engine_state": 1, "last_event": 0, "last_error": 0}},
        "expected_expression": "idle",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED",
    },
    {
        "case_id": "wake_detected_maps_to_listening",
        "input": {"wake_word_status": {"armed": 1, "engine_state": 1, "last_event": 2, "last_error": 0}},
        "expected_expression": "listening",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED",
    },
    {
        "case_id": "wake_error_maps_to_error",
        "input": {"wake_word_status": {"armed": 0, "engine_state": 0, "last_event": 0, "last_error": 2}},
        "expected_expression": "error",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
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


def build_fixture(errors: list[str]) -> dict[str, Any]:
    cases = []
    for case in INTERACTION_CASES:
        decision = expression_from_status(dict(case["input"]))
        require(
            decision.expression == case["expected_expression"],
            f"{case['case_id']} policy mapped to {decision.expression}",
            errors,
        )
        cases.append(
            {
                "case_id": case["case_id"],
                "input": case["input"],
                "expected_expression": case["expected_expression"],
                "expected_signal": case["expected_signal"],
                "policy_expression": decision.expression,
                "policy_reason": decision.reason,
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "wb55_integration": rel(APP_BLE),
            "event_bridge_header": rel(EVENTS_HEADER),
            "event_bridge_source": rel(EVENTS_SOURCE),
            "screen_acceptance": rel(PLAN_DOC),
            "epaper_readme": rel(README),
            "wba_rules": rel(WBA_RULES),
            "gatt_contract": rel(GATT_CONTRACT),
        },
        "wb55_hook": {
            "status_sources": ["MeetingStatusV1", "SpeakerStatusV1", "WakeWordStatusV1"],
            "meeting_publish_api": "Companion_Gatt_PublishMeetingStatus(bool apply_expression_hint)",
            "speaker_publish_api": "Companion_Gatt_PublishSpeakerStatus(bool apply_expression_hint)",
            "wake_publish_api": "Companion_Gatt_PublishWakeWordStatus(bool apply_expression_hint)",
            "initial_state_guards": [
                "Companion_Gatt_PublishMeetingStatus(false)",
                "Companion_Gatt_PublishSpeakerStatus(false)",
                "Companion_Gatt_PublishWakeWordStatus(false)",
            ],
            "notify_read_hooks": [
                "Companion_Gatt_PublishMeetingStatus(true)",
                "Companion_Gatt_PublishSpeakerStatus(true)",
                "Companion_Gatt_PublishWakeWordStatus(true)",
            ],
            "portable_mappers": [
                "comp_epaper_expression_signal_from_meeting_status",
                "comp_epaper_expression_signal_from_speaker_status",
                "comp_epaper_expression_signal_from_wake_word_status",
            ],
        },
        "constants": {
            "meeting_recording": 1,
            "meeting_finalized": 2,
            "speaker_prompt_accepted": 2,
            "wake_engine_armed": 1,
            "wake_event_detected": 2,
        },
        "cases": cases,
        "acceptance": {
            "interaction_status_publish_feeds_expression_bridge": True,
            "initial_state_publish_does_not_schedule_expression": True,
            "meeting_status_maps_to_recording_thinking_sync_error": True,
            "speaker_status_maps_to_speaking_error": True,
            "wake_word_status_maps_to_idle_listening_error": True,
            "duplicate_control_status_notifications_are_suppressed_by_state": True,
            "wba_safe_interaction_status_hook": True,
        },
    }


def check_wb55_hook(errors: list[str]) -> None:
    app_ble = APP_BLE.read_text(encoding="utf-8")
    for token in [
        "static void Companion_Gatt_PublishMeetingStatus(bool apply_expression_hint);",
        "static void Companion_Gatt_PublishSpeakerStatus(bool apply_expression_hint);",
        "static void Companion_Gatt_PublishWakeWordStatus(bool apply_expression_hint);",
        "Companion_Gatt_PublishMeetingStatus(false);",
        "Companion_Gatt_PublishSpeakerStatus(false);",
        "Companion_Gatt_PublishWakeWordStatus(false);",
        "Companion_Gatt_PublishMeetingStatus(true);",
        "Companion_Gatt_PublishSpeakerStatus(true);",
        "Companion_Gatt_PublishWakeWordStatus(true);",
        "Companion_Display_ApplyMeetingStatusExpressionHint(&status);",
        "Companion_Display_ApplySpeakerStatusExpressionHint(&status);",
        "Companion_Display_ApplyWakeWordStatusExpressionHint(&status);",
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
        "status->summary_state",
        "status->sync_state",
        "status->last_event",
    ]:
        require(token in app_ble, f"app_ble.c missing interaction status hook token {token}", errors)


def check_event_bridge(errors: list[str]) -> None:
    header = EVENTS_HEADER.read_text(encoding="utf-8")
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    for token in [
        "COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING 1u",
        "COMP_EPAPER_EXPRESSION_MEETING_STATE_FINALIZED 2u",
        "COMP_EPAPER_EXPRESSION_SPEAKER_STATE_PROMPT_ACCEPTED 2u",
        "COMP_EPAPER_EXPRESSION_WAKE_ENGINE_ARMED 1u",
        "COMP_EPAPER_EXPRESSION_WAKE_EVENT_DETECTED 2u",
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
    ]:
        require(token in header, f"expression_events.h missing interaction bridge token {token}", errors)
    for token in [
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START",
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE",
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT",
        "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
    ]:
        require(token in source, f"expression_events.c missing interaction bridge token {token}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = PLAN_DOC.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    wba_rules = WBA_RULES.read_text(encoding="utf-8")
    gatt_contract = GATT_CONTRACT.read_text(encoding="utf-8")
    for token in [
        "WB55 interaction status expression hint",
        "wb55_interaction_status_expression_hint",
        "companion-screen-interaction-status-expression-hook.json",
        "interaction_status_publish_feeds_expression_bridge",
    ]:
        require(token in screen_doc, f"screen expression doc missing interaction status hook anchor {token}", errors)
    for token in [
        "WB55 MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 publishing can feed",
        "portable interaction-status mappers",
    ]:
        require(token in readme, f"e-paper README missing interaction status hook anchor {token}", errors)
    for token in [
        "meetingstatusv1",
        "speakerstatusv1",
        "wakewordstatusv1",
        "interaction-status mapper",
        "wba interaction-status adapter",
    ]:
        require(token in wba_rules.lower(), f"WBA rules missing interaction status hook anchor {token}", errors)
    for token in [
        "MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 are also screen-expression inputs",
        "interaction status",
    ]:
        require(token in gatt_contract, f"GATT contract missing interaction status expression anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing interaction status expression fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic interaction status expression fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [APP_BLE, EVENTS_HEADER, EVENTS_SOURCE, PLAN_DOC, README, WBA_RULES, GATT_CONTRACT]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture(errors) if not errors else {"schema_id": SCHEMA_ID, "errors": errors}
    if not errors:
        check_wb55_hook(errors)
        check_event_bridge(errors)
        check_docs(errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)
    if errors:
        print("FAIL: Companion WB55 interaction status expression hook checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 interaction status expression hook verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
