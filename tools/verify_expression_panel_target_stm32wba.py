#!/usr/bin/env python3
"""Verify the STM32WBA panel adapter stays callback-bound and target isolated."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-target-stm32wba.json")
SCHEMA_ID = "companion.pendant.screen_panel_target_stm32wba.v1"

PANEL_TARGET_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wba.h"
PANEL_TARGET_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wba.c"
PANEL_ADAPTER_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_ADAPTER_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
WB55_APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
WB55_MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA55_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"


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
            "Target-named STM32WBA panel adapter scaffold for WBA55/WBA65 ports. "
            "It defaults to dry-run but can bind a target refresh callback without "
            "leaking CubeWBA HAL or pin facts into the portable panel adapter."
        ),
        "sources": {
            "wba_target_header": rel(PANEL_TARGET_HEADER),
            "wba_target_source": rel(PANEL_TARGET_SOURCE),
            "portable_panel_header": rel(PANEL_ADAPTER_HEADER),
            "portable_panel_source": rel(PANEL_ADAPTER_SOURCE),
            "wba_port_contract": rel(WBA_CONTRACT),
            "wba55_port_scaffold": rel(WBA55_SCAFFOLD),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
            "panel_gate": rel(PANEL_GATE),
        },
        "contract": {
            "initializer": "companion_epaper_panel_stm32wba_init",
            "target_name_api": "companion_epaper_panel_stm32wba_target_name",
            "targets": ["WBA55", "WBA65"],
            "target_enum": [
                "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55",
                "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65",
            ],
            "current_transport": "callback_bindable_dry_run_default",
            "dry_run_delegate": "comp_epaper_panel_adapter_init_dry_run",
            "bind_api": "companion_epaper_panel_stm32wba_bind",
            "bind_config": "companion_epaper_panel_stm32wba_config_t",
            "portable_bind_delegate": "comp_epaper_panel_adapter_init",
            "real_refresh_claimed": False,
            "refresh_intent_source": "comp_epaper_display_request_t.refresh_mode",
            "dirty_rect_source": "comp_epaper_display_request_t.dirty_x/dirty_y/dirty_width/dirty_height",
            "interactive_refresh_intents": [
                "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE",
                "COMP_EPAPER_REFRESH_MAINTENANCE",
                "COMP_EPAPER_REFRESH_FULL",
            ],
            "wba_waveform_mapping_owner": "panel_target_stm32wba.*",
            "target_file_pattern": "panel_target_stm32wba.*",
            "not_in_wb55_build": True,
            "wba55_is_baseline": True,
            "wba65_requires_capability_flags": True,
        },
        "forbidden_before_wba_hardware_evidence": [
            "HAL_SPI",
            "HAL_QSPI",
            "HAL_GPIO",
            "GPIO_PIN_",
            "SPI2",
            "PA9",
            "PC1",
            "PC2",
            "PA6",
            "SPI2_CS",
            "STM32_WPAN",
            "CPU2",
            "FUS",
            "IPCC",
            "HSEM",
            "COMP_EPAPER_PANEL_RESULT_OK",
        ],
        "required_future_evidence": [
            "separate CubeWBA project and build wrapper",
            "target SPI/DC/RST/BUSY/power pins",
            "panel controller model and datasheet revision",
            "reset timing, BUSY timeout, full refresh sequence, partial refresh policy",
            "real BLE artifact with --expect-real-panel and screen_expression_status",
            "filled WBA panel evidence record passing verify_expression_panel_evidence_record.py --record",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_target_stm32wba.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            "python .\\tools\\verify_expression_panel_gate.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WBA panel target schema", errors)
    require(data.get("status") == "PASS", "WBA panel target fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("initializer") == "companion_epaper_panel_stm32wba_init", "fixture missing WBA initializer", errors)
    require(
        contract.get("current_transport") == "callback_bindable_dry_run_default",
        "WBA panel target must remain callback-bindable with a dry-run default",
        errors,
    )
    require(contract.get("dry_run_delegate") == "comp_epaper_panel_adapter_init_dry_run", "fixture missing dry-run delegate", errors)
    require(contract.get("bind_api") == "companion_epaper_panel_stm32wba_bind", "fixture missing WBA bind API", errors)
    require(contract.get("bind_config") == "companion_epaper_panel_stm32wba_config_t", "fixture missing WBA bind config", errors)
    require(contract.get("portable_bind_delegate") == "comp_epaper_panel_adapter_init", "fixture missing portable bind delegate", errors)
    require(contract.get("real_refresh_claimed") is False, "WBA panel target must not claim real refresh", errors)
    require(
        contract.get("refresh_intent_source") == "comp_epaper_display_request_t.refresh_mode",
        "WBA panel target fixture must preserve portable refresh intent source",
        errors,
    )
    require(
        contract.get("dirty_rect_source") == "comp_epaper_display_request_t.dirty_x/dirty_y/dirty_width/dirty_height",
        "WBA panel target fixture must preserve dirty-rect source",
        errors,
    )
    for intent in [
        "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE",
        "COMP_EPAPER_REFRESH_MAINTENANCE",
        "COMP_EPAPER_REFRESH_FULL",
    ]:
        require(intent in contract.get("interactive_refresh_intents", []), f"WBA panel target missing refresh intent {intent}", errors)
    require(
        contract.get("wba_waveform_mapping_owner") == "panel_target_stm32wba.*",
        "WBA waveform mapping must stay in the WBA target adapter",
        errors,
    )
    require(contract.get("not_in_wb55_build") is True, "WBA panel target must stay out of WB55 build", errors)
    require(set(contract.get("targets", [])) == {"WBA55", "WBA65"}, "WBA panel target must cover WBA55 and WBA65", errors)


def check_target_code(errors: list[str]) -> None:
    header = read_text(PANEL_TARGET_HEADER, errors)
    source = read_text(PANEL_TARGET_SOURCE, errors)
    combined = header + "\n" + source
    adapter_header = read_text(PANEL_ADAPTER_HEADER, errors)
    queue_header = read_text(REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h", errors)
    for token in [
        '#include "panel_adapter.h"',
        "companion_epaper_panel_stm32wba_target_t",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65",
        "companion_epaper_panel_stm32wba_config_t",
        "companion_epaper_panel_stm32wba_target_name",
        "companion_epaper_panel_stm32wba_init",
        "companion_epaper_panel_stm32wba_bind",
    ]:
        require(token in header, f"panel_target_stm32wba.h missing {token}", errors)
    for token in [
        '#include "panel_target_stm32wba.h"',
        'return "WBA55";',
        'return "WBA65";',
        "(void)target;",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
        "comp_epaper_panel_adapter_init(adapter, &panel_config)",
        "config->refresh",
    ]:
        require(token in source, f"panel_target_stm32wba.c missing {token}", errors)
    for token in [
        "comp_epaper_panel_refresh_fn_t",
        "const comp_epaper_display_request_t *request",
    ]:
        require(token in adapter_header, f"portable panel adapter missing refresh request contract {token}", errors)
    for token in [
        "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE",
        "COMP_EPAPER_REFRESH_MAINTENANCE",
        "uint16_t dirty_x",
        "uint16_t dirty_y",
        "uint16_t dirty_width",
        "uint16_t dirty_height",
    ]:
        require(token in queue_header, f"display queue missing portable refresh intent/dirty rect token {token}", errors)
    for token in [
        "HAL_SPI",
        "HAL_QSPI",
        "HAL_GPIO",
        "GPIO_PIN_",
        "SPI2",
        "PA9",
        "PC1",
        "PC2",
        "PA6",
        "SPI2_CS",
        "STM32_WPAN",
        "CPU2",
        "FUS",
        "IPCC",
        "HSEM",
        "COMP_EPAPER_PANEL_RESULT_OK",
    ]:
        require(token not in combined, f"WBA panel target must not contain target hardware fact before evidence: {token}", errors)


def check_wb55_isolation(errors: list[str]) -> None:
    app_ble = read_text(WB55_APP_BLE, errors)
    makefile = read_text(WB55_MAKEFILE, errors)
    for text, name in [(app_ble, "WB55 app_ble.c"), (makefile, "WB55 Makefile")]:
        require("panel_target_stm32wba" not in text, f"{name} must not include the WBA panel target scaffold", errors)
        require("companion_epaper_panel_stm32wba_init" not in text, f"{name} must not call the WBA panel initializer", errors)
    require(
        "panel_target_stm32wb.c" in makefile,
        "WB55 Makefile must keep compiling only the WB55 target adapter",
        errors,
    )


def check_project_links(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    readme = read_text(README, errors)
    contract = read_json(WBA_CONTRACT, errors)
    scaffold = read_json(WBA55_SCAFFOLD, errors)
    gate = read_json(PANEL_GATE, errors)
    for text, name in [(screen_doc, "screen doc"), (wba_rules, "WBA rules"), (readme, "epaper README")]:
        for token in [
            "wba_panel_target_adapter_scaffold",
            "WBA panel target adapter scaffold",
            "panel_target_stm32wba",
            "companion_epaper_panel_stm32wba_init",
            "companion-screen-panel-target-stm32wba.json",
            "verify_expression_panel_target_stm32wba.py",
            "WBA55",
            "WBA65",
        ]:
            require(token in text, f"{name} missing WBA panel target anchor {token}", errors)
    if not allow_stale_index:
        serialized_contract = json.dumps(contract, sort_keys=True)
        for token in ["panel_target_stm32wba", "verify_expression_panel_target_stm32wba.py", "WBA panel target adapter scaffold"]:
            require(token in serialized_contract, f"WBA portability contract missing {token}", errors)
        serialized_scaffold = json.dumps(scaffold, sort_keys=True)
        for token in ["panel_target_stm32wba", "companion_epaper_panel_stm32wba_init", "DRAFT_PRE_PORT"]:
            require(token in serialized_scaffold, f"WBA55 port scaffold missing {token}", errors)
    require(gate.get("status") == "PASS", "WB55 real-panel gate must remain PASS", errors)
    require(gate.get("gate_id") == "wb55_real_panel_refresh", "panel gate must stay scoped to WB55", errors)
    require(
        "only target panel" in str(gate.get("wba_impact", "")),
        "WB55 panel evidence must describe the WBA target-backend boundary",
        errors,
    )

    if allow_stale_index:
        return
    index = read_json(ACCEPTANCE_INDEX, errors)
    matches = [
        item
        for item in index.get("items", [])
        if isinstance(item, dict) and item.get("id") == "wba_panel_target_adapter_scaffold"
    ]
    require(len(matches) == 1, "acceptance index must contain one wba_panel_target_adapter_scaffold item", errors)
    if matches:
        item = matches[0]
        require(item.get("status") == "PASS", "wba_panel_target_adapter_scaffold item must be PASS", errors)
        require(
            "docs/validation/companion-screen-panel-target-stm32wba.json" in item.get("evidence_paths", []),
            "wba_panel_target_adapter_scaffold item must link its fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_panel_target_stm32wba.py" in item.get("validation_commands", []),
            "wba_panel_target_adapter_scaffold item must run its verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WBA panel target fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WBA panel target fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_target_code(errors)
    check_wb55_isolation(errors)
    check_project_links(errors, allow_stale_index=bool(args.write_fixture))

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion WBA panel target adapter checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WBA panel target adapter verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
