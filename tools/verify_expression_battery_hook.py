#!/usr/bin/env python3
"""Verify WB55 BatteryChargeV1 feeds the portable ExpressionV1 low-battery hook."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.expression_policy import expression_from_event  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-battery-expression-hook.json")
SCHEMA_ID = "companion.pendant.screen_battery_expression_hook.v1"

APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"


BATTERY_CASES = [
    {
        "case_id": "default_devboard_charging_maps_to_guarded_recovery",
        "payload": {"percent": 100, "millivolts": 5000, "charger_present": 1, "charge_state": 1},
        "expected_expression": "idle",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
    },
    {
        "case_id": "low_percent_maps_to_low_battery",
        "payload": {"percent": 12, "millivolts": 3800, "charger_present": 0, "charge_state": 1},
        "expected_expression": "low_battery",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY",
    },
    {
        "case_id": "low_voltage_not_charging_maps_to_low_battery",
        "payload": {"percent": 55, "millivolts": 3500, "charger_present": 0, "charge_state": 1},
        "expected_expression": "low_battery",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY",
    },
    {
        "case_id": "low_voltage_charging_does_not_force_low_battery",
        "payload": {"percent": 55, "millivolts": 3500, "charger_present": 1, "charge_state": 2},
        "expected_expression": "idle",
        "expected_signal": None,
    },
    {
        "case_id": "near_threshold_does_not_recover_low_battery",
        "payload": {"percent": 22, "millivolts": 3650, "charger_present": 0, "charge_state": 1},
        "expected_expression": "idle",
        "expected_signal": None,
    },
    {
        "case_id": "recovered_percent_maps_to_battery_recovered",
        "payload": {"percent": 27, "millivolts": 3650, "charger_present": 0, "charge_state": 1},
        "expected_expression": "idle",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
    },
    {
        "case_id": "charging_voltage_maps_to_battery_recovered",
        "payload": {"percent": 22, "millivolts": 3650, "charger_present": 1, "charge_state": 2},
        "expected_expression": "idle",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
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
    for case in BATTERY_CASES:
        decision = expression_from_event("battery_charging.sample", dict(case["payload"]))
        require(
            decision.expression == case["expected_expression"],
            f"{case['case_id']} policy mapped to {decision.expression}",
            errors,
        )
        cases.append(
            {
                "case_id": case["case_id"],
                "payload": case["payload"],
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
            "wba_rules": rel(WBA_RULES),
        },
        "wb55_hook": {
            "status_source": "BatteryChargeV1",
            "publish_api": "Companion_Gatt_PublishBatteryCharge(bool apply_expression_hint)",
            "initial_state_guard": "Companion_Gatt_PublishBatteryCharge(false)",
            "notify_read_hook": "Companion_Gatt_PublishBatteryCharge(true)",
            "event_code": "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
            "arg0": "percent",
            "arg1": "millivolts",
            "arg2": "charger_present",
            "arg3": "charge_state",
        },
        "thresholds": {
            "low_battery_percent": 20,
            "low_battery_millivolts": 3600,
            "battery_recovered_percent": 25,
            "battery_recovered_millivolts": 3600,
            "charging_suppresses_voltage_only_low_battery": True,
            "near_threshold_samples_do_not_recover_low_battery": True,
        },
        "cases": cases,
        "acceptance": {
            "battery_charge_publish_feeds_expression_bridge": True,
            "initial_state_publish_does_not_schedule_expression": True,
            "low_percent_maps_to_low_battery": True,
            "low_voltage_while_not_charging_maps_to_low_battery": True,
            "charging_voltage_sample_does_not_force_low_battery": True,
            "recovered_percent_maps_to_battery_recovered": True,
            "charging_voltage_maps_to_battery_recovered": True,
            "battery_recovery_only_clears_low_battery": True,
            "wba_safe_battery_hook": True,
        },
    }


def check_wb55_hook(errors: list[str]) -> None:
    app_ble = APP_BLE.read_text(encoding="utf-8")
    for token in [
        "static void Companion_Gatt_PublishBatteryCharge(bool apply_expression_hint);",
        "Companion_Gatt_PublishBatteryCharge(false);",
        "Companion_Gatt_PublishBatteryCharge(true);",
        "static void Companion_Display_ApplyBatteryExpressionHint(",
        "const companion_gatt_battery_charge_v1_t *status",
        "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
        "COMP_DIAG_SEV_INFO",
        "(uint32_t)status->percent",
        "(uint32_t)status->millivolts",
        "(uint32_t)status->charger_present",
        "(uint32_t)status->charge_state",
        "if (apply_expression_hint)",
        "Companion_Display_ApplyBatteryExpressionHint(&status);",
    ]:
        require(token in app_ble, f"app_ble.c missing battery expression hook token {token}", errors)


def check_event_bridge(errors: list[str]) -> None:
    header = EVENTS_HEADER.read_text(encoding="utf-8")
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    for token in [
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY_PERCENT 20u",
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY_MV 3600u",
        "COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_PERCENT 25u",
        "COMP_EPAPER_EXPRESSION_BATTERY_RECOVERED_MV 3600u",
    ]:
        require(token in header, f"expression_events.h missing battery threshold {token}", errors)
    for token in [
        "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
        "low_battery_sample(arg0, arg1, arg2)",
        "battery_recovered_sample(arg0, arg1, arg2)",
        "COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
        "charger_present == 0u",
    ]:
        require(token in source, f"expression_events.c missing battery bridge token {token}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = PLAN_DOC.read_text(encoding="utf-8")
    wba_rules = WBA_RULES.read_text(encoding="utf-8")
    for token in [
        "WB55 battery expression hint",
        "Battery recovery expression guard",
        "wb55_battery_expression_hint",
        "battery_recovery_expression_guard",
        "companion-screen-battery-expression-hook.json",
        "battery_charge_publish_feeds_expression_bridge",
        "battery_recovery_only_clears_low_battery",
    ]:
        require(token in screen_doc, f"screen expression doc missing battery hook anchor {token}", errors)
    for token in [
        "batterychargev1",
        "low-battery expression",
        "wba battery adapter",
    ]:
        require(token in wba_rules.lower(), f"WBA rules missing battery hook anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing battery expression fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic battery expression fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [APP_BLE, EVENTS_HEADER, EVENTS_SOURCE, PLAN_DOC, WBA_RULES]:
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
        print("FAIL: Companion WB55 battery expression hook checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 battery expression hook verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
