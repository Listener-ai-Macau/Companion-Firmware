#!/usr/bin/env python3
"""Verify WB55 OtaReadinessV1 feeds the portable ExpressionV1 blocker hook."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.expression_policy import expression_from_status  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-ota-expression-hook.json")
SCHEMA_ID = "companion.pendant.screen_ota_expression_hook.v1"

APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
GATT_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"


OTA_LOW_BATTERY_BLOCKER = 1 << 3
OTA_WRONG_BOARD_BLOCKER = 1 << 4

OTA_CASES = [
    {
        "case_id": "ready_no_blockers_no_expression",
        "blocker_bitmap": 0,
        "expected_expression": "idle",
        "expected_signal": None,
    },
    {
        "case_id": "low_battery_blocker_maps_to_low_battery",
        "blocker_bitmap": OTA_LOW_BATTERY_BLOCKER,
        "expected_expression": "low_battery",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY",
    },
    {
        "case_id": "wrong_board_blocker_maps_to_error",
        "blocker_bitmap": OTA_WRONG_BOARD_BLOCKER,
        "expected_expression": "error",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
    },
    {
        "case_id": "low_battery_takes_precedence_over_other_blockers",
        "blocker_bitmap": OTA_LOW_BATTERY_BLOCKER | OTA_WRONG_BOARD_BLOCKER,
        "expected_expression": "low_battery",
        "expected_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY",
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
    for case in OTA_CASES:
        payload = {"blocker_bitmap": case["blocker_bitmap"]}
        decision = expression_from_status({"ota_readiness": payload})
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
            "status_source": "OtaReadinessV1",
            "publish_api": "Companion_Gatt_PublishOtaReadiness(bool apply_expression_hint)",
            "initial_state_guard": "Companion_Gatt_PublishOtaReadiness(false)",
            "notify_read_hook": "Companion_Gatt_PublishOtaReadiness(true)",
            "portable_mapper": "comp_epaper_expression_signal_from_ota_readiness",
            "blocker_bitmap_source": "readiness->blocker_bitmap",
        },
        "blocker_bits": {
            "low_battery": 3,
            "wrong_board_target": 4,
        },
        "cases": cases,
        "acceptance": {
            "ota_readiness_publish_feeds_expression_bridge": True,
            "initial_state_publish_does_not_schedule_expression": True,
            "low_battery_blocker_maps_to_low_battery": True,
            "nonzero_ota_blocker_maps_to_error": True,
            "low_battery_blocker_takes_precedence": True,
            "wba_safe_ota_hook": True,
        },
    }


def check_wb55_hook(errors: list[str]) -> None:
    app_ble = APP_BLE.read_text(encoding="utf-8")
    for token in [
        "static void Companion_Gatt_PublishOtaReadiness(bool apply_expression_hint);",
        "Companion_Gatt_PublishOtaReadiness(false);",
        "Companion_Gatt_PublishOtaReadiness(true);",
        "static void Companion_Display_ApplyOtaExpressionHint(",
        "const companion_gatt_ota_readiness_v1_t *readiness",
        "comp_epaper_expression_signal_from_ota_readiness",
        "readiness->blocker_bitmap",
        "if (apply_expression_hint)",
        "Companion_Display_ApplyOtaExpressionHint(&readiness);",
    ]:
        require(token in app_ble, f"app_ble.c missing OTA expression hook token {token}", errors)


def check_event_bridge(errors: list[str]) -> None:
    header = EVENTS_HEADER.read_text(encoding="utf-8")
    source = EVENTS_SOURCE.read_text(encoding="utf-8")
    for token in [
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER_BIT 3u",
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER",
        "comp_epaper_expression_signal_from_ota_readiness",
    ]:
        require(token in header, f"expression_events.h missing OTA bridge token {token}", errors)
    for token in [
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER",
        "COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_ERROR",
        "blocker_bitmap != 0u",
    ]:
        require(token in source, f"expression_events.c missing OTA bridge token {token}", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = PLAN_DOC.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    wba_rules = WBA_RULES.read_text(encoding="utf-8")
    gatt_contract = GATT_CONTRACT.read_text(encoding="utf-8")
    for token in [
        "WB55 OTA readiness expression hint",
        "wb55_ota_readiness_expression_hint",
        "companion-screen-ota-expression-hook.json",
        "ota_readiness_publish_feeds_expression_bridge",
    ]:
        require(token in screen_doc, f"screen expression doc missing OTA hook anchor {token}", errors)
    for token in [
        "WB55 OtaReadinessV1 publishing can feed",
        "portable OTA blocker mapper",
    ]:
        require(token in readme, f"e-paper README missing OTA hook anchor {token}", errors)
    for token in [
        "otareadinessv1",
        "ota blocker",
        "wba ota adapter",
    ]:
        require(token in wba_rules.lower(), f"WBA rules missing OTA hook anchor {token}", errors)
    for token in [
        "OtaReadinessV1 is also a screen-expression input",
        "low-battery blocker",
    ]:
        require(token in gatt_contract, f"GATT contract missing OTA expression anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing OTA expression fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic OTA expression fixture.")
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
        print("FAIL: Companion WB55 OTA expression hook checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 OTA expression hook verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
