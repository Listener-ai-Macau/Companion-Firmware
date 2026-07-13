#!/usr/bin/env python3
"""Verify the WB55 target-named panel adapter scaffold stays dry-run and WBA-ready."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-target-stm32wb.json")
SCHEMA_ID = "companion.pendant.screen_panel_target_stm32wb.v1"

PANEL_TARGET_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb.h"
PANEL_TARGET_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb.c"
SSD1681_TARGET_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb_ssd1681.c"
PANEL_ADAPTER_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_ADAPTER_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"


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


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "WB55 target-named adapter with a proven SSD1681 production backend and a dry-run fallback, preserving the WBA target-adapter split.",
        "sources": {
            "wb55_target_header": rel(PANEL_TARGET_HEADER),
            "wb55_target_source": rel(PANEL_TARGET_SOURCE),
            "wb55_ssd1681_diagnostic_driver": rel(SSD1681_TARGET_SOURCE),
            "portable_panel_header": rel(PANEL_ADAPTER_HEADER),
            "portable_panel_source": rel(PANEL_ADAPTER_SOURCE),
            "wb55_integration": rel(APP_BLE),
            "wb55_build": rel(MAKEFILE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
            "panel_gate": rel(PANEL_GATE),
        },
        "contract": {
            "wb55_initializer": "companion_epaper_panel_stm32wb_init",
            "current_transport": "ssd1681_real_when_bringup_enabled",
            "dry_run_delegate": "comp_epaper_panel_adapter_init_dry_run_fallback",
            "real_refresh_claimed": True,
            "target_file_pattern": "panel_target_stm32wb.*",
            "future_wba_pattern": "*_stm32wba.*",
            "ssd1681_diagnostic_driver": {
                "build_flag": "COMPANION_EPAPER_PANEL_SSD1681_BRINGUP",
                "controller": "SSD1681",
                "full_refresh_sequence": "GDEY0154D67_vendor_reference",
                "real_refresh_claimed": True,
            },
        },
        "forbidden_until_hardware_evidence": [
            "HAL_SPI",
            "HAL_QSPI",
            "GPIO_PIN_",
            "BSP_",
            "EPD_",
            "COMP_EPAPER_PANEL_RESULT_OK",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_target_stm32wb.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_panel_adapter_boundary.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WB55 panel target schema", errors)
    require(data.get("status") == "PASS", "WB55 panel target fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("wb55_initializer") == "companion_epaper_panel_stm32wb_init", "fixture missing WB55 initializer", errors)
    require(contract.get("current_transport") == "ssd1681_real_when_bringup_enabled", "fixture must record the real SSD1681 transport", errors)
    require(contract.get("dry_run_delegate") == "comp_epaper_panel_adapter_init_dry_run_fallback", "fixture missing dry-run fallback", errors)
    require(contract.get("real_refresh_claimed") is True, "fixture must record the real refresh evidence", errors)
    require(contract.get("future_wba_pattern") == "*_stm32wba.*", "fixture missing future WBA adapter pattern", errors)
    diagnostic_driver = contract.get("ssd1681_diagnostic_driver", {})
    require(
        diagnostic_driver.get("build_flag") == "COMPANION_EPAPER_PANEL_SSD1681_BRINGUP",
        "fixture missing SSD1681 diagnostic build flag",
        errors,
    )
    require(diagnostic_driver.get("controller") == "SSD1681", "fixture missing SSD1681 controller", errors)
    require(
        diagnostic_driver.get("full_refresh_sequence") == "GDEY0154D67_vendor_reference",
        "fixture missing GDEY0154D67 vendor refresh sequence",
        errors,
    )
    require(diagnostic_driver.get("real_refresh_claimed") is True, "fixture must claim the proven SSD1681 panel refresh", errors)


def check_target_code(errors: list[str]) -> None:
    header = read(PANEL_TARGET_HEADER, errors)
    source = read(PANEL_TARGET_SOURCE, errors)
    for token in [
        '#include "panel_adapter.h"',
        "companion_epaper_panel_stm32wb_init",
    ]:
        require(token in header, f"panel_target_stm32wb.h missing {token}", errors)
    for token in [
        '#include "panel_target_stm32wb.h"',
        "void companion_epaper_panel_stm32wb_init(",
        "comp_epaper_expression_asset_source_t *expression_assets",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
    ]:
        require(token in source, f"panel_target_stm32wb.c missing {token}", errors)
    for token in ["HAL_SPI", "HAL_QSPI", "GPIO_PIN_", "BSP_", "EPD_", "COMP_EPAPER_PANEL_RESULT_OK"]:
        require(token not in source, f"WB55 panel target must not contain real transport before evidence: {token}", errors)


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    makefile = read(MAKEFILE, errors)
    for token in [
        '#include "panel_target_stm32wb.h"',
        "companion_epaper_panel_stm32wb_init(",
        "s_companion_expression_asset_source",
    ]:
        require(token in app_ble, f"WB55 app_ble.c missing panel target token {token}", errors)
    require(
        "comp_epaper_panel_adapter_init_dry_run(&s_companion_panel_adapter)" not in app_ble,
        "WB55 app_ble.c should initialize through the target-named panel adapter",
        errors,
    )
    require(
        "$(ROOT)/app/companion_pendant/epaper/panel_target_stm32wb.c" in makefile,
        "WB55 Makefile missing panel_target_stm32wb.c",
        errors,
    )
    require(
        "ifeq ($(EPAPER_SSD1681_BRINGUP),1)" in makefile and
        "panel_target_stm32wb_ssd1681.c" in makefile,
        "WB55 Makefile must compile the SSD1681 driver only for the explicit bring-up build",
        errors,
    )


def check_ssd1681_diagnostic_driver(errors: list[str]) -> None:
    source = read(SSD1681_TARGET_SOURCE, errors)
    for token in [
        "#define SSD1681_WIDTH 200u",
        "#define SSD1681_HEIGHT 200u",
        "Good Display's matching STM32 example waits while BUSY is high and proceeds low.",
        "#define SSD1681_BUSY_READY_LEVEL GPIO_PIN_RESET",
        "GPIO_InitStruct.Pull = GPIO_NOPULL;",
        "#define SSD1681_REFRESH_START_TIMEOUT_MS 100u",
        "while (HAL_GPIO_ReadPin",
        "!= SSD1681_BUSY_READY_LEVEL)",
        "static bool ssd1681_wait_refresh_complete",
        "bool observed_busy = false;",
        "SSD1681_REFRESH_START_TIMEOUT_MS",
        "static const uint8_t driver_output[] = {0xC7u, 0x00u, 0x00u};",
        "static const uint8_t data_entry[] = {0x01u};",
        "static ssd1681_window_t ssd1681_window_from_difference(void)",
        "static bool ssd1681_set_window(const ssd1681_window_t *window)",
        "static bool ssd1681_write_plane_region",
        "s_previous_frame",
        "ssd1681_command(0x12u)",
        "ssd1681_write_plane_region(0x24u, s_frame, &window)",
        "ssd1681_write_plane_region(0x26u, s_previous_frame, &window)",
        "? 0xFCu",
        "? 0xCFu",
        ": 0xF7u",
        "ssd1681_command(0x20u)",
        "GDEY0154D67 reference's descending Y address",
        "Differential mode needs the old and new pixels",
        "comp_epaper_refresh_policy_select",
        "comp_epaper_refresh_policy_commit",
        "busy_active_ms",
        "#define COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI 1",
        '"software_vendor_edges"',
        "HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);",
        "HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);",
        "#define COMPANION_EPAPER_SSD1681_ROTATION_DEGREES 0u",
        "static uint8_t frame_reverse_bits(uint8_t value)",
        "static void frame_apply_target_rotation(void)",
        "frame_apply_target_rotation();",
        "static void frame_apply_horizontal_mirror(void)",
        "frame_apply_horizontal_mirror();",
        '"[epaper] frame rotation=%u mirror_x=%u width=%u height=%u',
    ]:
        require(token in source, f"SSD1681 diagnostic driver missing vendor sequence token {token}", errors)
    require(
        source.count("HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);") >= 1 and
        "value <<= 1u;" in source,
        "SSD1681 software SPI must preserve the vendor's MSB-first rising-edge clocking",
        errors,
    )
    bringup_main = read(REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c", errors)
    require(
        "#define BOARD_EPAPER_SPI_BAUDRATE_PRESCALER SPI_BAUDRATEPRESCALER_16" in bringup_main and
        "#define BOARD_EPAPER_SPI_HZ 2000000u" in bringup_main,
        "WB55 e-paper SPI must keep the vendor-equivalent conservative 2 MHz bring-up rate",
        errors,
    )
    require(
        "COMPANION_EPAPER_PANEL_SSD1681_BRINGUP" in read(PANEL_TARGET_SOURCE, errors),
        "WB55 target adapter must select the SSD1681 driver only through the bring-up flag",
        errors,
    )
    makefile = read(MAKEFILE, errors)
    for token in [
        "COMPANION_EPAPER_SSD1681_ROTATION_DEGREES=$(EPAPER_SSD1681_ROTATION)u",
        "COMPANION_SCREEN_ROTATION_DEGREES=$(EPAPER_SSD1681_ROTATION)u",
    ]:
        require(token in makefile, f"WB55 Makefile missing orientation contract {token}", errors)
    bringup_wrapper = read(REPO_ROOT / "tools" / "build_nucleo_bringup.ps1", errors)
    for token in [
        "[ValidateSet(0, 180)]",
        "[int]$EpaperSsd1681Rotation = 180",
        '"EPAPER_SSD1681_ROTATION=$EpaperSsd1681Rotation"',
        "[int]$EpaperSsd1681MirrorX = 1",
        '"EPAPER_SSD1681_MIRROR_X=$EpaperSsd1681MirrorX"',
    ]:
        require(token in bringup_wrapper, f"WB55 build wrapper missing orientation contract {token}", errors)
    for token in [
        "#define COMPANION_SCREEN_ROTATION_DEGREES 0u",
        "logical_x = sample->x < 200u ? sample->x : 199u;",
        "logical_y = sample->y < 200u ? sample->y : 199u;",
        "logical_x = (uint16_t)(199u - logical_x);",
        "logical_y = (uint16_t)(199u - logical_y);",
        "raw_x=%u raw_y=%u x=%u y=%u mirror_x=%u mirror_y=%u",
    ]:
        require(token in bringup_main, f"WB55 touch path missing orientation contract {token}", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    gate = read(PANEL_GATE, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "wb55_panel_target_adapter_scaffold",
        "WB55 panel target adapter scaffold",
        "panel_target_stm32wb",
        "companion-screen-panel-target-stm32wb.json",
        "verify_expression_panel_target_stm32wb.py",
        "companion_epaper_panel_stm32wb_init",
    ]:
        require(token in screen_doc, f"screen expression doc missing WB55 panel target anchor {token}", errors)
    for token in ["panel_target_stm32wb", "companion_epaper_panel_stm32wb_init", "*_stm32wba.*"]:
        require(token in wba_rules, f"WBA rules missing WB55 panel target anchor {token}", errors)
    for token in ["panel_target_stm32wb", "companion_epaper_panel_stm32wb_init"]:
        require(token in readme, f"e-paper README missing WB55 panel target anchor {token}", errors)
    for token in ["panel_target_stm32wb", "companion_epaper_panel_stm32wb_init", '"status": "PASS"', "0xC7"]:
        require(token in gate, f"panel hardware gate missing WB55 panel target anchor {token}", errors)
    if index_text:
        index = json.loads(index_text)
        matches = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "wb55_panel_target_adapter_scaffold"]
        require(len(matches) == 1, "acceptance index must contain one wb55_panel_target_adapter_scaffold item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "wb55_panel_target_adapter_scaffold item must be PASS", errors)
            require(
                "docs/validation/companion-screen-panel-target-stm32wb.json" in item.get("evidence_paths", []),
                "wb55_panel_target_adapter_scaffold item must link fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_panel_target_stm32wb.py" in item.get("validation_commands", []),
                "wb55_panel_target_adapter_scaffold item must run verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WB55 panel target fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WB55 panel target fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_target_code(errors)
    check_wb55_integration(errors)
    check_ssd1681_diagnostic_driver(errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion WB55 panel target adapter checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 panel target adapter verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
