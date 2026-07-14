#!/usr/bin/env python3
"""Verify the callback-only WBA external screen-assets adapter."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EPAPER_ROOT = REPO_ROOT / "app" / "companion_pendant" / "epaper"
STORAGE_ROOT = REPO_ROOT / "app" / "companion_pendant" / "storage"
HEADER = EPAPER_ROOT / "screen_assets_stm32wba.h"
SOURCE = EPAPER_ROOT / "screen_assets_stm32wba.c"
ASSET_STORE_HEADER = EPAPER_ROOT / "asset_store.h"
SPI_NOR_HEADER = STORAGE_ROOT / "spi_nor_stm32wba.h"
SPI_NOR_SOURCE = STORAGE_ROOT / "spi_nor_stm32wba.c"
SPI_NOR_VERIFIER = REPO_ROOT / "tools" / "verify_wba_spi_nor_adapter.py"
SPI_NOR_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-wba-spi-nor-adapter.json"
WB55_APP = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
WB55_MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
DEFAULT_FIXTURE = pathlib.Path(
    "docs/validation/companion-screen-assets-stm32wba.json"
)
SCHEMA_ID = "companion.pendant.screen_assets_stm32wba.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Callback-only external ui_assets reader for WBA55/WBA65. "
            "Target storage owns physical Flash details; the screen layer owns logical offsets."
        ),
        "sources": {
            "adapter_header": rel(HEADER),
            "adapter_source": rel(SOURCE),
            "portable_asset_store": rel(ASSET_STORE_HEADER),
            "selected_wba_storage_adapter": rel(SPI_NOR_SOURCE),
            "selected_wba_storage_contract": rel(SPI_NOR_FIXTURE),
        },
        "contract": {
            "targets": ["WBA55", "WBA65"],
            "storage_class": "external_nor",
            "selected_pre_port_transport": "spi_nor_1_1_1",
            "address_model": "logical_partition_relative_offset",
            "required_callback": "read(context, partition_offset, destination, length)",
            "selected_partition_callback": "companion_spi_nor_stm32wba_partition_read",
            "bounds_policy": "adapter rejects reads outside configured partition_size",
            "hardware_parity_claimed": False,
        },
        "required_future_evidence": [
            "CubeWBA storage peripheral and pin facts for the selected board",
            "external NOR capacity, erase geometry, and ui_assets partition layout",
            "CEMP mount, CRC, profile check, and frame read from real WBA storage",
            "resource OTA staging and atomic active-metadata activation",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_screen_assets_stm32wba.py",
            "python .\\tools\\verify_wba_spi_nor_adapter.py --self-test",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_code(errors: list[str]) -> None:
    for path in (
        HEADER,
        SOURCE,
        ASSET_STORE_HEADER,
        SPI_NOR_HEADER,
        SPI_NOR_SOURCE,
        SPI_NOR_VERIFIER,
        SPI_NOR_FIXTURE,
    ):
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if errors:
        return
    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    combined = header + "\n" + source
    spi_nor = (
        SPI_NOR_HEADER.read_text(encoding="utf-8")
        + "\n"
        + SPI_NOR_SOURCE.read_text(encoding="utf-8")
    )

    for token in (
        '#include "asset_store.h"',
        '#include "panel_target_stm32wba.h"',
        "companion_screen_assets_stm32wba_read_fn_t",
        "partition_size",
        "companion_screen_assets_stm32wba_init",
        "companion_screen_assets_stm32wba_ready",
        "companion_screen_assets_stm32wba_bind",
    ):
        require(token in header, f"WBA assets header missing {token}", errors)
    for token in (
        "read_partition",
        "partition_offset > adapter->config.partition_size",
        "length > adapter->config.partition_size - partition_offset",
        "COMP_ASSET_STORAGE_EXTERNAL_NOR",
        "comp_asset_store_init_reader",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65",
    ):
        require(token in source, f"WBA assets source missing {token}", errors)
    for token in (
        "HAL_",
        "GPIO",
        "QSPI",
        "OSPI",
        "I2C",
        "SPI",
        "STM32_WPAN",
        "UTIL_SEQ",
        "0x00200000",
        "PC0",
        "PB11",
    ):
        require(token not in combined, f"WBA assets adapter leaked target fact {token}", errors)

    for token in (
        "companion_spi_nor_stm32wba_partition_read",
        "companion_spi_nor_stm32wba_partition_init",
        "NOR_CMD_READ_DATA 0x03u",
    ):
        require(token in spi_nor, f"selected WBA SPI NOR adapter missing {token}", errors)

    wb55 = WB55_APP.read_text(encoding="utf-8") + "\n" + WB55_MAKEFILE.read_text(encoding="utf-8")
    require("screen_assets_stm32wba" not in wb55,
            "WB55 build must not include WBA assets adapter", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []
    check_code(errors)
    if args.write_fixture and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.write_fixture:
        require(fixture.exists(), f"missing WBA assets fixture {rel(fixture)}", errors)
        if fixture.exists():
            actual = json.loads(fixture.read_text(encoding="utf-8"))
            require(actual == expected, f"{rel(fixture)} is stale; rerun with --write-fixture", errors)
    if errors:
        print("FAIL: Companion STM32WBA screen-assets checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion STM32WBA screen-assets adapter verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
