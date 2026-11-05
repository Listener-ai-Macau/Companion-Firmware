#!/usr/bin/env python3
"""Verify WB55 DeviceStatusV1 feeds the portable ExpressionV1 status hook."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.expression_policy import expression_from_status  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-device-status-expression-hook.json")
SCHEMA_ID = "companion.pendant.screen_device_status_expression_hook.v1"

APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
GATT_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"


DEVICE_CASES = [
    {
        "case_id": "idle_link_no_expression_override",
        "payload": {"active_mode": 2, "fault_bitmap": 0},
        "expected_expression": "idle",
        "expected_signal": None,
    },
    {
        "case_id": "disconnected_maps_to_sleepy",
        "payload": {"active_mode": 0, "fault_bitmap": 0},
        "expected_expression": "sleepy",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
    },
    {
        "case_id": "active_audio_maps_to_recording",
        "payload": {"active_mode": 1, "fault_bitmap": 0},
        "expected_expression": "recording",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
    },
    {
        "case_id": "fault_bitmap_maps_to_error",
        "payload": {"active_mode": 1, "fault_bitmap": 1},
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
    for case in DEVICE_CASES:
        payload = dict(case["payload"])
        decision = expression_from_status({"device_status": payload})
        require(
            decision.expression == case["expected_expression"],
            f"{case['case_id']} policy mapped to {decision.expression}",
            errors,
        )
        cases.append(
            {
                "case_id": case["case_id"],
                "payload": payload,
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
            "status_source": "DeviceStatusV1",
            "publish_api": "Companion_Gatt_PublishDeviceStatus(bool apply_expression_hint)",
            "initial_state_guard": "Companion_Gatt_PublishDeviceStatus(false)",
            "notify_read_hook": "Companion_Gatt_PublishDeviceStatus(true)",
            "portable_mapper": "comp_epaper_expression_signal_from_device_status",
            "active_mode_source": "status->active_mode",
            "fault_bitmap_source": "status->fault_bitmap",
        },
        "active_modes": {
            "disconnected": 0,
            "active_audio": 1,
            "idle_link": 2,
        },
        "cases": cases,
        "acceptance": {
            "device_status_publish_feeds_expression_bridge": True,
            "initial_state_publish_does_not_schedule_expression": True,
            "disconnected_maps_to_low_priority_sleepy": True,
            "active_audio_maps_to_recording": True,
            "fault_bitmap_maps_to_error": True,
            "fault_bitmap_takes_precedence": True,
            "wba_safe_device_status_hook": True,
        },
    }


def check_wb55_hook(errors: list[str]) -> None:
    app_ble = APP_BLE.read_text(encoding="utf-8")
    for token in [
        "static void Companion_Gatt_PublishDeviceStatus(bool apply_expression_hint);",
        "Companion_Gatt_PublishDeviceStatus(false);",
        "Companion_Gatt_PublishDeviceStatus(true);",
        "static void Companion_Display_ApplyDeviceStatusExpressionHint(",
        "const companion_gatt_device_status_v1_t *status",
        "comp_epaper_expression_signal_from_device_status",
        "status->active_mode",
        "status->fault_bitmap",
        "if (apply_expression_hint)",
        "Companion_Display_ApplyDeviceStatusExpressionHint(&status);",
    ]:
        require(token in app_ble, f"app_ble.c missing DeviceStatus expression hook token {token}", errors)


def check_event_bridge(errors: list[str]) -> None:
    header = EVENTS_HEADER.read_text(encoding="utf-8")
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    for token in [
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED 0u",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO 1u",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_IDLE_LINK 2u",
        "comp_epaper_expression_signal_from_device_status",
    ]:
        require(token in header, f"expression_events.h missing DeviceStatus bridge token {token}", errors)
    for token in [
        "fault_bitmap != 0u",
        "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
    ]:
        require(token in source, f"expression_events.c missing DeviceStatus bridge token {token}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = PLAN_DOC.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    wba_rules = WBA_RULES.read_text(encoding="utf-8")
    gatt_contract = GATT_CONTRACT.read_text(encoding="utf-8")
    for token in [
        "WB55 device status expression hint",
        "wb55_device_status_expression_hint",
        "companion-screen-device-status-expression-hook.json",
        "device_status_publish_feeds_expression_bridge",
    ]:
        require(token in screen_doc, f"screen expression doc missing DeviceStatus hook anchor {token}", errors)
    for token in [
        "WB55 DeviceStatusV1 publishing can feed",
        "portable device-status mapper",
    ]:
        require(token in readme, f"e-paper README missing DeviceStatus hook anchor {token}", errors)
    for token in [
        "devicestatusv1",
        "device-status mapper",
        "wba device-status adapter",
    ]:
        require(token in wba_rules.lower(), f"WBA rules missing DeviceStatus hook anchor {token}", errors)
    for token in [
        "DeviceStatusV1 is also a screen-expression input",
        "fault_bitmap",
    ]:
        require(token in gatt_contract, f"GATT contract missing DeviceStatus expression anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing DeviceStatus expression fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic DeviceStatus expression fixture.")
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
        print("FAIL: Companion WB55 DeviceStatus expression hook checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 DeviceStatus expression hook verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
