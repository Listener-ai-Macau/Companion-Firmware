#!/usr/bin/env python3
"""Verify screen settings influence ExpressionV1 without hiding priority states."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import DISPLAY_VARIANTS, render_card, sha256_hex  # noqa: E402
from app.companion_pendant.epaper.expression_policy import (  # noqa: E402
    SCREEN_SETTINGS_QUIET_HOURS_FLAG,
    expression_from_status,
    is_quiet_hours_active,
    screen_settings_wants_sleepy,
)


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-settings-policy.json")
SCHEMA_ID = "companion.pendant.screen_settings_policy.v1"
POLICY_MODULE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_policy.py"
GATT_HEADER = REPO_ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.h"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"


CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "quiet_hours_explicit_sleepy",
        "input": {"device_status": {"active_mode": 2}, "settings": {"quiet_hours_active": True}},
        "expected_expression": "sleepy",
        "expected_quiet_active": True,
        "expected_sleepy_setting": True,
    },
    {
        "case_id": "quiet_hours_wraps_midnight_sleepy",
        "input": {
            "device_status": {"active_mode": 2},
            "settings": {"quiet_hours_start_min": 1320, "quiet_hours_end_min": 420, "local_minute": 30},
        },
        "expected_expression": "sleepy",
        "expected_quiet_active": True,
        "expected_sleepy_setting": True,
    },
    {
        "case_id": "quiet_hours_daytime_idle",
        "input": {
            "device_status": {"active_mode": 2},
            "settings": {"quiet_hours_start_min": 1320, "quiet_hours_end_min": 420, "local_minute": 720},
        },
        "expected_expression": "idle",
        "expected_quiet_active": False,
        "expected_sleepy_setting": False,
    },
    {
        "case_id": "display_off_sleepy",
        "input": {"device_status": {"active_mode": 2}, "settings": {"display_brightness": 0}},
        "expected_expression": "sleepy",
        "expected_quiet_active": False,
        "expected_sleepy_setting": True,
    },
    {
        "case_id": "settings_flag_sleepy",
        "input": {"device_status": {"active_mode": 2}, "settings": {"flags": SCREEN_SETTINGS_QUIET_HOURS_FLAG}},
        "expected_expression": "sleepy",
        "expected_quiet_active": True,
        "expected_sleepy_setting": True,
    },
    {
        "case_id": "quiet_hours_recording_visible",
        "input": {
            "device_status": {"active_mode": 2},
            "settings": {"quiet_hours_active": True, "display_brightness": 0},
            "recording_control": {"command": 1, "privacy_flags": 0},
        },
        "expected_expression": "recording",
        "expected_quiet_active": True,
        "expected_sleepy_setting": True,
    },
    {
        "case_id": "quiet_hours_low_battery_visible",
        "input": {
            "device_status": {"active_mode": 2},
            "settings": {"quiet_hours_active": True},
            "battery_charge": {"percent": 9, "millivolts": 3500, "charger_present": 0},
        },
        "expected_expression": "low_battery",
        "expected_quiet_active": True,
        "expected_sleepy_setting": True,
    },
    {
        "case_id": "quiet_hours_error_visible",
        "input": {
            "device_status": {"active_mode": 2, "fault_bitmap": 1},
            "settings": {"quiet_hours_active": True},
        },
        "expected_expression": "error",
        "expected_quiet_active": True,
        "expected_sleepy_setting": True,
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


def build_fixture() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case in CASES:
        decision = expression_from_status(dict(case["input"]))
        card = decision.as_card(card_id=str(case["case_id"]))
        cases.append(
            {
                "case_id": case["case_id"],
                "input": case["input"],
                "expected_expression": case["expected_expression"],
                "decision": decision.as_manifest(),
                "quiet_hours_active": is_quiet_hours_active(dict(case["input"].get("settings", {}))),
                "screen_settings_wants_sleepy": screen_settings_wants_sleepy(dict(case["input"].get("settings", {}))),
                "render_hashes": {
                    key: sha256_hex(render_card(card, variant))
                    for key, variant in DISPLAY_VARIANTS.items()
                },
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "policy": rel(POLICY_MODULE),
            "gatt_header": rel(GATT_HEADER),
            "ble_contract": rel(BLE_CONTRACT),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
        },
        "settings_contract": {
            "quiet_hours_flag": SCREEN_SETTINGS_QUIET_HOURS_FLAG,
            "supports_explicit_quiet_hours_active": True,
            "supports_wrapping_midnight_windows": True,
            "display_brightness_zero_maps_to_sleepy": True,
        },
        "cases": cases,
        "acceptance": {
            "quiet_hours_maps_to_sleepy": True,
            "display_off_maps_to_sleepy": True,
            "recording_overrides_sleepy": True,
            "low_battery_overrides_sleepy": True,
            "error_overrides_sleepy": True,
            "wba_safe_policy_only": True,
        },
    }


def check_logic(errors: list[str]) -> None:
    for case in CASES:
        settings = dict(case["input"].get("settings", {}))
        decision = expression_from_status(dict(case["input"]))
        require(
            decision.expression == case["expected_expression"],
            f"{case['case_id']} mapped to {decision.expression}, expected {case['expected_expression']}",
            errors,
        )
        require(
            is_quiet_hours_active(settings) is case["expected_quiet_active"],
            f"{case['case_id']} quiet-hour active result drifted",
            errors,
        )
        require(
            screen_settings_wants_sleepy(settings) is case["expected_sleepy_setting"],
            f"{case['case_id']} sleepy setting result drifted",
            errors,
        )
        for variant in DISPLAY_VARIANTS.values():
            rendered = render_card(decision.as_card(card_id=str(case["case_id"])), variant)
            require(rendered.startswith(b"P4\n"), f"{case['case_id']}/{variant.key} did not render PBM", errors)


def check_sources(errors: list[str]) -> None:
    policy = POLICY_MODULE.read_text(encoding="utf-8")
    gatt = GATT_HEADER.read_text(encoding="utf-8")
    contract = BLE_CONTRACT.read_text(encoding="utf-8")
    screen_doc = SCREEN_DOC.read_text(encoding="utf-8")
    wba_rules = WBA_RULES.read_text(encoding="utf-8")
    for token in [
        "SCREEN_SETTINGS_QUIET_HOURS_FLAG",
        "is_quiet_hours_active",
        "screen_settings_wants_sleepy",
        "quiet_hours_start_min",
        "display_brightness",
    ]:
        require(token in policy, f"expression policy missing settings anchor {token}", errors)
    for token in ["quiet_hours_start_min", "quiet_hours_end_min", "display_brightness", "flags"]:
        require(token in gatt, f"SettingsV1 struct missing {token}", errors)
    for token in [
        "Screen Settings Expression Policy",
        "quiet_hours_active",
        "display_brightness=0",
        "sleepy",
    ]:
        require(token in contract, f"BLE contract missing screen settings policy anchor {token}", errors)
    for token in [
        "Screen settings expression policy",
        "companion-screen-settings-policy.json",
        "verify_expression_settings_policy.py",
    ]:
        require(token in screen_doc, f"screen expression doc missing settings policy anchor {token}", errors)
    require("quiet hours" in wba_rules.lower(), "WBA rules missing quiet-hours portability note", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing screen settings policy fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update deterministic screen settings policy evidence.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []
    check_logic(errors)
    check_sources(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen settings policy checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen settings policy verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
