#!/usr/bin/env python3
"""Verify the STM32WBA screen GATT scaffold preserves host-visible screen contracts."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-gatt-stm32wba.json")
SCHEMA_ID = "companion.pendant.screen_gatt_stm32wba.v1"

GATT_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_gatt_stm32wba.h"
GATT_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_gatt_stm32wba.c"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
REAL_BLE_BENCH = REPO_ROOT / "docs" / "validation" / "companion-screen-real-ble-bench.json"
HOST_STATUS_SEQUENCE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-host-status-sequence.json"
WB55_APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
WB55_MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA55_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read_text(path, errors)
    if not text:
        return {}
    return json.loads(text)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Target-named STM32WBA screen GATT scaffold that preserves the "
            "CardWriteV1/CardStatusV1/SettingsV1 screen contract without using "
            "the WB55 STM32_WPAN GATT implementation."
        ),
        "sources": {
            "wba_screen_gatt_header": rel(GATT_HEADER),
            "wba_screen_gatt_source": rel(GATT_SOURCE),
            "ble_gatt_contract": rel(BLE_CONTRACT),
            "real_ble_screen_bench": rel(REAL_BLE_BENCH),
            "host_status_sequence": rel(HOST_STATUS_SEQUENCE),
            "wba_port_contract": rel(WBA_CONTRACT),
            "wba55_port_scaffold": rel(WBA55_SCAFFOLD),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "contract": {
            "max_payload_bytes": 248,
            "card_write_payload": "companion_epaper_stm32wba_card_write_v1_t",
            "card_status_payload": "companion_epaper_stm32wba_card_status_v1_t",
            "settings_payload": "companion_epaper_stm32wba_settings_v1_t",
            "expression_card_slot": 1,
            "expression_request_id_base": "0xe0000000",
            "accepted_status_render_state": "COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED",
            "rendered_status_render_state": "COMPANION_EPAPER_STM32WBA_RENDER_STATE_RENDERED",
            "failed_status_render_state": "COMPANION_EPAPER_STM32WBA_RENDER_STATE_FAILED",
            "busy_status_render_state": "COMPANION_EPAPER_STM32WBA_RENDER_STATE_BUSY",
            "settings_sleepy_trigger": "display_brightness=0 or quiet-hours flag bit 0",
            "settings_clear_recovery": (
                "every valid SettingsV1 write reaches the expression-hint callback "
                "and schedules display work, including brightness and quiet-hours clears"
            ),
            "not_in_wb55_build": True,
            "real_ble_operations": [
                "card_write",
                "settings_sleepy_screen_status",
                "screen_expression_status",
            ],
        },
        "forbidden_before_wba_ble_project": [
            "companion_gatt_stm32wb",
            "STM32_WPAN",
            "aci_gatt",
            "SVCCTL",
            "GATT_NOTIFY_ATTRIBUTE_WRITE",
            "UTIL_SEQ",
            "CPU2",
            "FUS",
            "IPCC",
            "HSEM",
        ],
        "required_future_evidence": [
            "CubeWBA BLE service registration chosen",
            "WBA CardWriteV1 parser preserves request_id/card_slot/display_flags/content_crc32",
            "WBA CardStatusV1 notify preserves accepted/final refresh_count sequence",
            "WBA SettingsV1 write with display_brightness=0 triggers settings_sleepy_screen_status",
            "WBA SettingsV1 clear write restores the policy-selected non-sleepy expression",
            "WBA real BLE artifact carries screen_expression_status six-face baseline",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_screen_gatt_stm32wba.py",
            "python .\\tools\\verify_companion_gatt_static.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WBA screen GATT scaffold schema", errors)
    require(data.get("status") == "PASS", "WBA screen GATT scaffold fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("max_payload_bytes") == 248, "WBA screen GATT max payload drifted", errors)
    require(contract.get("expression_card_slot") == 1, "WBA screen GATT expression card slot drifted", errors)
    require(contract.get("expression_request_id_base") == "0xe0000000", "WBA screen GATT expression request id base drifted", errors)
    require(contract.get("not_in_wb55_build") is True, "WBA screen GATT scaffold must stay out of WB55 build", errors)
    require(
        "every valid SettingsV1 write" in str(contract.get("settings_clear_recovery", "")),
        "WBA screen GATT fixture must preserve settings clear recovery",
        errors,
    )
    require(
        set(contract.get("real_ble_operations", [])) == {"card_write", "settings_sleepy_screen_status", "screen_expression_status"},
        "WBA screen GATT scaffold must cover screen real BLE operations",
        errors,
    )


def check_gatt_code(errors: list[str]) -> None:
    header = read_text(GATT_HEADER, errors)
    source = read_text(GATT_SOURCE, errors)
    combined = header + "\n" + source
    for token in [
        "COMPANION_EPAPER_STM32WBA_GATT_MAX_PAYLOAD_BYTES 248u",
        "COMPANION_EPAPER_STM32WBA_EXPRESSION_CARD_SLOT 1u",
        "COMPANION_EPAPER_STM32WBA_EXPRESSION_REQUEST_ID_BASE 0xe0000000u",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED = 1",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_RENDERED = 2",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_FAILED = 3",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_BUSY = 4",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK = 0",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_DEFERRED_NO_PANEL = 4",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_DEFERRED_CONTROLLER_UNKNOWN = 5",
        "companion_epaper_stm32wba_card_write_v1_t",
        "companion_epaper_stm32wba_card_status_v1_t",
        "companion_epaper_stm32wba_settings_v1_t",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "companion_epaper_stm32wba_screen_gatt_publish_card_status",
        "companion_epaper_stm32wba_screen_gatt_handle_settings",
        "companion_epaper_stm32wba_settings_wants_sleepy",
        "companion_epaper_stm32wba_is_expression_request_id",
    ]:
        require(token in header, f"screen_gatt_stm32wba.h missing {token}", errors)
    for token in [
        '#include "screen_gatt_stm32wba.h"',
        "gatt->config.handle_card_write != NULL",
        "gatt->config.publish_card_status != NULL",
        "gatt->config.apply_settings_expression_hint != NULL",
        "gatt->config.schedule_display_task != NULL",
        "settings->display_brightness == 0u",
        "COMPANION_EPAPER_STM32WBA_QUIET_HOURS_SLEEPY_FLAG",
        "request_id & 0xf0000000u",
        "COMPANION_EPAPER_STM32WBA_EXPRESSION_REQUEST_ID_BASE",
        ".refresh_count = ++gatt->refresh_count",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK",
        "gatt->config.schedule_display_task(gatt->config.context);",
        "gatt->config.apply_settings_expression_hint(gatt->config.context",
    ]:
        require(token in source, f"screen_gatt_stm32wba.c missing {token}", errors)
    for token in [
        "companion_gatt_stm32wb",
        "STM32_WPAN",
        "aci_gatt",
        "SVCCTL",
        "GATT_NOTIFY_ATTRIBUTE_WRITE",
        "UTIL_SEQ",
        "CPU2",
        "FUS",
        "IPCC",
        "HSEM",
    ]:
        require(token not in combined, f"WBA screen GATT scaffold leaked WB55/platform token {token}", errors)

    settings_region = source.split(
        "void companion_epaper_stm32wba_screen_gatt_handle_settings", 1
    )[-1]
    require(
        "if (companion_epaper_stm32wba_settings_wants_sleepy" not in settings_region,
        "SettingsV1 callback must run for clear writes as well as sleepy writes",
        errors,
    )
    require(
        settings_region.find("apply_settings_expression_hint") < settings_region.find("schedule_display_task"),
        "SettingsV1 must apply its expression hint before scheduling display work",
        errors,
    )


def check_wb55_isolation(errors: list[str]) -> None:
    app_ble = read_text(WB55_APP_BLE, errors)
    makefile = read_text(WB55_MAKEFILE, errors)
    for text, name in [(app_ble, "WB55 app_ble.c"), (makefile, "WB55 Makefile")]:
        require("screen_gatt_stm32wba" not in text, f"{name} must not include WBA screen GATT scaffold", errors)
        require("companion_epaper_stm32wba_screen_gatt" not in text, f"{name} must not use WBA screen GATT scaffold", errors)
    require("companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS" in app_ble, "WB55 CardStatus publish anchor missing", errors)
    require("companion_gatt_parse_card_write_v1" in app_ble, "WB55 CardWrite parse anchor missing", errors)
    require("Companion_Display_ApplySettingsExpressionHint" in app_ble, "WB55 settings expression hint anchor missing", errors)


def check_related_contracts(errors: list[str]) -> None:
    ble_contract = read_text(BLE_CONTRACT, errors)
    real_ble = read_json(REAL_BLE_BENCH, errors)
    host_sequence = read_json(HOST_STATUS_SEQUENCE, errors)
    for token in [
        "CardWriteV1",
        "CardStatusV1",
        "SettingsV1",
        "settings_sleepy_screen_status",
        "screen_expression_status",
        "final_card_status",
        "0xe0000000",
    ]:
        require(token in ble_contract, f"BLE contract missing screen GATT anchor {token}", errors)
    serialized_real_ble = json.dumps(real_ble, sort_keys=True)
    for token in ["card_write", "settings_sleepy_screen_status", "screen_expression_status", "final_card_status"]:
        require(token in serialized_real_ble, f"real BLE bench fixture missing {token}", errors)
    require(host_sequence.get("operation") == "screen_expression_status", "host status sequence fixture operation drifted", errors)


def check_project_links(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    readme = read_text(README, errors)
    contract = read_json(WBA_CONTRACT, errors)
    scaffold = read_json(WBA55_SCAFFOLD, errors)
    for text, name in [(screen_doc, "screen doc"), (wba_rules, "WBA rules"), (readme, "epaper README")]:
        for token in [
            "wba_screen_gatt_scaffold",
            "WBA screen GATT scaffold",
            "screen_gatt_stm32wba",
            "companion_epaper_stm32wba_screen_gatt_accept_card_write",
            "companion-screen-gatt-stm32wba.json",
            "verify_expression_screen_gatt_stm32wba.py",
            "settings_sleepy_screen_status",
            "screen_expression_status",
        ]:
            require(token in text, f"{name} missing WBA screen GATT anchor {token}", errors)
    serialized_contract = json.dumps(contract, sort_keys=True)
    for token in ["screen_gatt_stm32wba", "verify_expression_screen_gatt_stm32wba.py", "WBA screen GATT scaffold"]:
        require(token in serialized_contract, f"WBA portability contract missing {token}", errors)
    serialized_scaffold = json.dumps(scaffold, sort_keys=True)
    for token in ["screen_gatt_stm32wba", "companion_epaper_stm32wba_screen_gatt_accept_card_write", "DRAFT_PRE_PORT"]:
        require(token in serialized_scaffold, f"WBA55 port scaffold missing {token}", errors)

    if allow_stale_index:
        return
    index = read_json(ACCEPTANCE_INDEX, errors)
    matches = [
        item
        for item in index.get("items", [])
        if isinstance(item, dict) and item.get("id") == "wba_screen_gatt_scaffold"
    ]
    require(len(matches) == 1, "acceptance index must contain one wba_screen_gatt_scaffold item", errors)
    if matches:
        item = matches[0]
        require(item.get("status") == "PASS", "wba_screen_gatt_scaffold item must be PASS", errors)
        require(
            "docs/validation/companion-screen-gatt-stm32wba.json" in item.get("evidence_paths", []),
            "wba_screen_gatt_scaffold item must link its fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_screen_gatt_stm32wba.py" in item.get("validation_commands", []),
            "wba_screen_gatt_scaffold item must run its verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WBA screen GATT scaffold fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WBA screen GATT scaffold fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_gatt_code(errors)
    check_wb55_isolation(errors)
    check_related_contracts(errors)
    check_project_links(errors, allow_stale_index=bool(args.write_fixture))

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion WBA screen GATT scaffold checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WBA screen GATT scaffold verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
