#!/usr/bin/env python3
"""Verify all product input sources are covered by ExpressionV1 fixtures."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-input-source-matrix.json")
SCHEMA_ID = "companion.pendant.expression_input_source_matrix.v1"

EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

SIGNAL_ENUM_RE = re.compile(r"COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+)\s*=\s*(\d+),")

FOCUSED_FIXTURES = {
    "firmware_state": pathlib.Path("docs/validation/companion-screen-firmware-expression-state.json"),
    "event_bridge": pathlib.Path("docs/validation/companion-screen-expression-event-bridge.json"),
    "settings_policy": pathlib.Path("docs/validation/companion-screen-settings-policy.json"),
    "device_status": pathlib.Path("docs/validation/companion-screen-device-status-expression-hook.json"),
    "battery": pathlib.Path("docs/validation/companion-screen-battery-expression-hook.json"),
    "recording_state": pathlib.Path("docs/validation/companion-screen-recording-state-expression-hook.json"),
    "interaction_status": pathlib.Path("docs/validation/companion-screen-interaction-status-expression-hook.json"),
    "ota": pathlib.Path("docs/validation/companion-screen-ota-expression-hook.json"),
}

INPUT_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "id": "boot_default_idle",
        "title": "Boot/default idle",
        "category": "startup",
        "portable_path": "direct ExpressionV1 signal",
        "focused_fixture": "firmware_state",
        "focused_verifier": "tools/verify_expression_firmware_state.py",
        "signals": ["BOOT_IDLE"],
        "required_tokens": {
            "app_ble": ["Companion_Display_EnqueueExpressionSignal(COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,"],
            "event_header": [],
            "event_source": [],
        },
        "fixture_acceptance": ["first_boot_idle_enqueues"],
        "wba_adapter_rule": "WBA startup enqueues BOOT_IDLE through its display scheduler after the display task exists.",
    },
    {
        "id": "diagnostic_events",
        "title": "Diagnostic event bridge",
        "category": "diagnostics",
        "portable_path": "comp_epaper_expression_signal_from_diag_event",
        "focused_fixture": "event_bridge",
        "focused_verifier": "tools/verify_expression_event_bridge.py",
        "signals": [
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
            "BATTERY_RECOVERED",
            "RECOVERY",
            "ERROR",
        ],
        "required_tokens": {
            "app_ble": ["comp_epaper_expression_signal_from_diag_event"],
            "event_header": ["comp_epaper_expression_signal_from_diag_event"],
            "event_source": [
                "k_event_signal_defs",
                "COMP_DIAG_EVENT_SOURCE(event_code) == (uint8_t)COMP_DIAG_SRC_EPAPER",
                "severity >= COMP_DIAG_SEV_ERROR",
            ],
        },
        "fixture_acceptance": [],
        "wba_adapter_rule": "WBA diagnostic logging can feed the same event bridge and must keep e_paper self-loop rejection.",
    },
    {
        "id": "settings_v1",
        "title": "SettingsV1 screen hints",
        "category": "gatt_status",
        "portable_path": "direct settings sleepy/recovery signals",
        "focused_fixture": "settings_policy",
        "focused_verifier": "tools/verify_expression_settings_policy.py",
        "signals": ["SETTINGS_SLEEPY", "RECOVERY"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplySettingsExpressionHint",
                "Companion_Settings_WantsSleepy",
                "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
                "COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY",
            ],
            "event_header": [],
            "event_source": [],
        },
        "fixture_acceptance": [
            "quiet_hours_maps_to_sleepy",
            "display_off_maps_to_sleepy",
            "recording_overrides_sleepy",
        ],
        "wba_adapter_rule": "WBA SettingsV1 adapter preserves quiet-hours/display-off as low-priority sleepy hints.",
    },
    {
        "id": "device_status_v1",
        "title": "DeviceStatusV1",
        "category": "gatt_status",
        "portable_path": "comp_epaper_expression_signal_from_device_status",
        "focused_fixture": "device_status",
        "focused_verifier": "tools/verify_expression_device_status_hook.py",
        "signals": ["SETTINGS_SLEEPY", "RECORDING_START", "ERROR"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplyDeviceStatusExpressionHint",
                "comp_epaper_expression_signal_from_device_status",
                "Companion_Gatt_PublishDeviceStatus(false);",
                "Companion_Gatt_PublishDeviceStatus(true);",
            ],
            "event_header": ["comp_epaper_expression_signal_from_device_status"],
            "event_source": [
                "fault_bitmap != 0u",
                "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO",
                "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED",
            ],
        },
        "fixture_acceptance": [
            "device_status_publish_feeds_expression_bridge",
            "initial_state_publish_does_not_schedule_expression",
        ],
        "wba_adapter_rule": "WBA DeviceStatusV1 adapter calls the same mapper after startup publication is scheduler-safe.",
    },
    {
        "id": "battery_charge_v1",
        "title": "BatteryChargeV1",
        "category": "gatt_status",
        "portable_path": "battery_charging.sample diagnostic bridge",
        "focused_fixture": "battery",
        "focused_verifier": "tools/verify_expression_battery_hook.py",
        "signals": ["LOW_BATTERY", "BATTERY_RECOVERED"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplyBatteryExpressionHint",
                "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
                "Companion_Gatt_PublishBatteryCharge(false);",
                "Companion_Gatt_PublishBatteryCharge(true);",
            ],
            "event_header": [
                "COMP_EPAPER_EXPRESSION_LOW_BATTERY_PERCENT",
                "COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_PERCENT",
            ],
            "event_source": [
                "low_battery_sample(arg0, arg1, arg2)",
                "battery_recovered_sample(arg0, arg1, arg2)",
            ],
        },
        "fixture_acceptance": [
            "battery_charge_publish_feeds_expression_bridge",
            "battery_recovery_only_clears_low_battery",
        ],
        "wba_adapter_rule": "WBA BatteryChargeV1 adapter preserves low/recovered thresholds and recovery guard.",
    },
    {
        "id": "recording_fsm_state",
        "title": "Recording FSM state",
        "category": "portable_state",
        "portable_path": "comp_epaper_expression_signal_from_recording_state",
        "focused_fixture": "recording_state",
        "focused_verifier": "tools/verify_expression_recording_state_hook.py",
        "signals": ["RECORDING_START", "RECORDING_STOP", "RECORDING_CANCEL", "RECORDING_FINISHED", "ERROR"],
        "required_tokens": {
            "app_ble": [],
            "event_header": ["comp_epaper_expression_signal_from_recording_state"],
            "event_source": [
                "COMP_EPAPER_EXPRESSION_RECORDING_STATE_RECORDING",
                "COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_READY",
                "COMP_EPAPER_EXPRESSION_RECORDING_STATE_ERROR_RECOVERY",
            ],
        },
        "fixture_acceptance": [
            "recording_state_active_maps_to_recording",
            "recording_state_transfer_maps_to_sync_complete",
        ],
        "wba_adapter_rule": "WBA recording adapter reuses numeric Recording FSM state mapping before adding platform glue.",
    },
    {
        "id": "meeting_status_v1",
        "title": "MeetingStatusV1",
        "category": "gatt_status",
        "portable_path": "comp_epaper_expression_signal_from_meeting_status",
        "focused_fixture": "interaction_status",
        "focused_verifier": "tools/verify_expression_interaction_status_hook.py",
        "signals": ["MEETING_START", "MEETING_STOP", "MEETING_FINALIZE", "ERROR"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplyMeetingStatusExpressionHint",
                "comp_epaper_expression_signal_from_meeting_status",
                "Companion_Gatt_PublishMeetingStatus(false);",
                "Companion_Gatt_PublishMeetingStatus(true);",
            ],
            "event_header": ["comp_epaper_expression_signal_from_meeting_status"],
            "event_source": [
                "COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING",
                "COMP_EPAPER_EXPRESSION_MEETING_SUMMARY_PENDING",
                "COMP_EPAPER_EXPRESSION_MEETING_SYNC_COMPLETE",
            ],
        },
        "fixture_acceptance": ["meeting_status_maps_to_recording_thinking_sync_error"],
        "wba_adapter_rule": "WBA MeetingStatusV1 adapter preserves recording/thinking/sync/error expression mapping.",
    },
    {
        "id": "speaker_status_v1",
        "title": "SpeakerStatusV1",
        "category": "gatt_status",
        "portable_path": "comp_epaper_expression_signal_from_speaker_status",
        "focused_fixture": "interaction_status",
        "focused_verifier": "tools/verify_expression_interaction_status_hook.py",
        "signals": ["SPEAKER_PROMPT", "ERROR"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplySpeakerStatusExpressionHint",
                "comp_epaper_expression_signal_from_speaker_status",
                "Companion_Gatt_PublishSpeakerStatus(false);",
                "Companion_Gatt_PublishSpeakerStatus(true);",
            ],
            "event_header": ["comp_epaper_expression_signal_from_speaker_status"],
            "event_source": ["COMP_EPAPER_EXPRESSION_SPEAKER_STATE_PROMPT_ACCEPTED"],
        },
        "fixture_acceptance": ["speaker_status_maps_to_speaking_error"],
        "wba_adapter_rule": "WBA SpeakerStatusV1 adapter preserves speaking/error expression mapping.",
    },
    {
        "id": "wake_word_status_v1",
        "title": "WakeWordStatusV1",
        "category": "gatt_status",
        "portable_path": "comp_epaper_expression_signal_from_wake_word_status",
        "focused_fixture": "interaction_status",
        "focused_verifier": "tools/verify_expression_interaction_status_hook.py",
        "signals": ["WAKE_ARMED", "WAKE_DETECTED", "ERROR"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplyWakeWordStatusExpressionHint",
                "comp_epaper_expression_signal_from_wake_word_status",
                "Companion_Gatt_PublishWakeWordStatus(false);",
                "Companion_Gatt_PublishWakeWordStatus(true);",
            ],
            "event_header": ["comp_epaper_expression_signal_from_wake_word_status"],
            "event_source": [
                "COMP_EPAPER_EXPRESSION_WAKE_ENGINE_ARMED",
                "COMP_EPAPER_EXPRESSION_WAKE_EVENT_DETECTED",
            ],
        },
        "fixture_acceptance": ["wake_word_status_maps_to_idle_listening_error"],
        "wba_adapter_rule": "WBA WakeWordStatusV1 adapter preserves armed/listening/error expression mapping.",
    },
    {
        "id": "ota_readiness_v1",
        "title": "OtaReadinessV1",
        "category": "gatt_status",
        "portable_path": "comp_epaper_expression_signal_from_ota_readiness",
        "focused_fixture": "ota",
        "focused_verifier": "tools/verify_expression_ota_hook.py",
        "signals": ["LOW_BATTERY", "ERROR"],
        "required_tokens": {
            "app_ble": [
                "Companion_Display_ApplyOtaExpressionHint",
                "comp_epaper_expression_signal_from_ota_readiness",
                "Companion_Gatt_PublishOtaReadiness(false);",
                "Companion_Gatt_PublishOtaReadiness(true);",
            ],
            "event_header": ["comp_epaper_expression_signal_from_ota_readiness"],
            "event_source": [
                "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER",
                "blocker_bitmap != 0u",
            ],
        },
        "fixture_acceptance": [
            "ota_readiness_publish_feeds_expression_bridge",
            "low_battery_blocker_takes_precedence",
        ],
        "wba_adapter_rule": "WBA OtaReadinessV1 adapter preserves low-battery blocker precedence over generic OTA errors.",
    },
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


def parse_signal_ids(header: str) -> dict[str, int]:
    return {
        symbol: int(value)
        for symbol, value in SIGNAL_ENUM_RE.findall(header)
        if symbol != "COUNT"
    }


def load_fixture(key: str, errors: list[str]) -> dict[str, Any]:
    path = REPO_ROOT / FOCUSED_FIXTURES[key]
    require(path.exists(), f"missing focused fixture {rel(path)}", errors)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_fixture() -> dict[str, Any]:
    signal_ids = parse_signal_ids(EXPRESSION_HEADER.read_text(encoding="utf-8"))
    sources: list[dict[str, Any]] = []
    for item in INPUT_SOURCES:
        sources.append(
            {
                "id": item["id"],
                "title": item["title"],
                "category": item["category"],
                "portable_path": item["portable_path"],
                "signals": [
                    {
                        "symbol": signal,
                        "id": signal_ids[signal],
                    }
                    for signal in item["signals"]
                ],
                "focused_fixture": rel(REPO_ROOT / FOCUSED_FIXTURES[str(item["focused_fixture"])]),
                "focused_verifier": item["focused_verifier"],
                "wba_adapter_rule": item["wba_adapter_rule"],
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "WB55/WBA ExpressionV1 input-source coverage matrix.",
        "sources": {
            "firmware_header": rel(EXPRESSION_HEADER),
            "event_bridge_header": rel(EVENTS_HEADER),
            "event_bridge_source": rel(EVENTS_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "input_source_count": len(sources),
        "input_sources": sources,
        "acceptance": {
            "boot_default_idle_covered": True,
            "diagnostic_event_bridge_covered": True,
            "settings_v1_covered": True,
            "device_status_v1_covered": True,
            "battery_charge_v1_covered": True,
            "recording_fsm_state_covered": True,
            "meeting_status_v1_covered": True,
            "speaker_status_v1_covered": True,
            "wake_word_status_v1_covered": True,
            "ota_readiness_v1_covered": True,
            "focused_fixtures_linked": True,
            "wba_adapter_checklist_complete": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_input_source_matrix.py",
            "python .\\tools\\verify_expression_event_bridge.py",
            "python .\\tools\\verify_expression_settings_policy.py",
            "python .\\tools\\verify_expression_device_status_hook.py",
            "python .\\tools\\verify_expression_battery_hook.py",
            "python .\\tools\\verify_expression_recording_state_hook.py",
            "python .\\tools\\verify_expression_interaction_status_hook.py",
            "python .\\tools\\verify_expression_ota_hook.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_sources(expected: dict[str, Any], errors: list[str]) -> None:
    signal_ids = parse_signal_ids(read(EXPRESSION_HEADER, errors))
    app_ble = read(APP_BLE, errors)
    event_header = read(EVENTS_HEADER, errors)
    event_source = read(EVENTS_SOURCE, errors)

    require(len(INPUT_SOURCES) == 10, "input source matrix count drifted", errors)
    seen_ids: set[str] = set()
    for item in INPUT_SOURCES:
        source_id = str(item["id"])
        require(source_id not in seen_ids, f"duplicate input source id {source_id}", errors)
        seen_ids.add(source_id)
        for signal in item["signals"]:
            require(str(signal) in signal_ids, f"{source_id} references unknown signal {signal}", errors)
        tokens = item["required_tokens"]
        for token in tokens.get("app_ble", []):
            require(token in app_ble, f"{source_id} missing WB55 app_ble token {token}", errors)
        for token in tokens.get("event_header", []):
            require(token in event_header, f"{source_id} missing expression_events.h token {token}", errors)
        for token in tokens.get("event_source", []):
            require(token in event_source, f"{source_id} missing expression_events.c token {token}", errors)

    require(expected.get("input_source_count") == 10, "fixture input source count drifted", errors)
    fixture_ids = [entry.get("id") for entry in expected.get("input_sources", [])]
    require(fixture_ids == [item["id"] for item in INPUT_SOURCES], "fixture input source order drifted", errors)


def check_focused_fixtures(errors: list[str]) -> None:
    for key, path in FOCUSED_FIXTURES.items():
        fixture = load_fixture(key, errors)
        if not fixture:
            continue
        require(fixture.get("schema_id"), f"{rel(REPO_ROOT / path)} missing schema_id", errors)
        if key not in {"event_bridge", "firmware_state"}:
            require(fixture.get("status") == "PASS", f"{rel(REPO_ROOT / path)} must be PASS", errors)

    for item in INPUT_SOURCES:
        fixture = load_fixture(str(item["focused_fixture"]), errors)
        acceptance = fixture.get("acceptance", {})
        state_machine = fixture.get("state_machine", {})
        for flag in item.get("fixture_acceptance", []):
            require(
                acceptance.get(flag) is True or state_machine.get(flag) is True,
                f"{item['id']} focused fixture missing acceptance flag {flag}",
                errors,
            )

    event_bridge = load_fixture("event_bridge", errors)
    require(len(event_bridge.get("event_mappings", [])) >= 21, "event bridge fixture missing diagnostic event mappings", errors)
    special_cases = event_bridge.get("special_cases", {})
    for key in [
        "device_status.active_mode_fault_bitmap",
        "battery_charging.sample",
        "recording_fsm.state",
        "ota_readiness.blocker_bitmap",
        "e_paper.*",
        "severity_error_fallback",
    ]:
        require(key in special_cases, f"event bridge fixture missing special case {key}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(SCREEN_DOC, errors).split()).lower()
    wba_rules = " ".join(read(WBA_RULES, errors).split()).lower()
    readme = " ".join(read(README, errors).split()).lower()
    for token in [
        "expression input source matrix",
        "expression_input_source_matrix",
        "companion-screen-expression-input-source-matrix.json",
        "verify_expression_input_source_matrix.py",
        "settingsv1",
        "devicestatusv1",
        "batterychargev1",
        "otareadinessv1",
    ]:
        require(token.lower() in screen_doc, f"screen doc missing input source matrix anchor {token}", errors)
    for token in [
        "expression input source matrix",
        "verify_expression_input_source_matrix.py",
        "wba adapter checklist",
        "settingsv1",
        "devicestatusv1",
        "batterychargev1",
        "meetingstatusv1",
        "speakerstatusv1",
        "wakewordstatusv1",
        "otareadinessv1",
    ]:
        require(token.lower() in wba_rules, f"WBA rules missing input source matrix anchor {token}", errors)
    for token in [
        "expression input source matrix",
        "verify_expression_input_source_matrix.py",
        "wba port must preserve",
    ]:
        require(token.lower() in readme, f"e-paper README missing input source matrix anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression input source matrix fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic input source matrix fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_sources(expected, errors)
    check_focused_fixtures(errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: ExpressionV1 input source matrix checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: ExpressionV1 input source matrix verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
