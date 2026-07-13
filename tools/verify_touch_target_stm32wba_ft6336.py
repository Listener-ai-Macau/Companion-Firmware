#!/usr/bin/env python3
"""Verify the callback-only FT6336 target adapter prepared for STM32WBA."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-touch-ft6336-stm32wba.json")
SCHEMA_ID = "companion.pendant.screen_touch_ft6336_stm32wba.v1"
TOUCH_ROOT = REPO_ROOT / "app" / "companion_pendant" / "touch"
HEADER = TOUCH_ROOT / "touch_target_stm32wba_ft6336.h"
SOURCE = TOUCH_ROOT / "touch_target_stm32wba_ft6336.c"
PORTABLE_HEADER = TOUCH_ROOT / "ft6336.h"
PORTABLE_SOURCE = TOUCH_ROOT / "ft6336.c"
WB55_APP = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
WB55_MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Callback-only FT6336 target adapter prepared for WBA55/WBA65. "
            "CubeWBA owns I2C and pins; the portable layer owns register and report contracts."
        ),
        "sources": {
            "target_header": rel(HEADER),
            "target_source": rel(SOURCE),
            "portable_decoder_header": rel(PORTABLE_HEADER),
            "portable_decoder_source": rel(PORTABLE_SOURCE),
        },
        "contract": {
            "targets": ["WBA55", "WBA65"],
            "address_format": "7_bit",
            "default_address": "0x38",
            "transport": "probe_and_register_read_write_callbacks",
            "portable_decoder": "comp_ft6336_decode_touch_report",
            "identity_register": "COMP_FT6336_IDENTITY_REGISTER",
            "interrupt_mode_register": "COMP_FT6336_G_MODE_REGISTER",
            "interrupt_mode": "trigger_with_poll_fallback",
            "runtime_tuning": "shared_threshold_and_active_monitor_periods",
            "reconnect_after_read_error": True,
            "not_in_wb55_build": True,
            "hardware_parity_claimed": False,
        },
        "required_future_evidence": [
            "CubeWBA IOC I2C instance and SDA/SCL pin facts",
            "detected 7-bit address and FT6336 identity bytes",
            "four-corner coordinate orientation capture",
            "tap and left/right/up/down gesture acceptance",
        ],
        "validation_commands": [
            "python .\\tools\\verify_touch_target_stm32wba_ft6336.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_code(errors: list[str]) -> None:
    header = read_text(HEADER, errors)
    source = read_text(SOURCE, errors)
    combined = header + "\n" + source
    for token in [
        '#include "ft6336.h"',
        "COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55",
        "COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA65",
        "companion_touch_ft6336_stm32wba_probe_fn_t",
        "companion_touch_ft6336_stm32wba_read_fn_t",
        "companion_touch_ft6336_stm32wba_write_fn_t",
        "companion_touch_ft6336_stm32wba_config_t",
        "companion_touch_ft6336_stm32wba_init",
        "companion_touch_ft6336_stm32wba_probe",
        "companion_touch_ft6336_stm32wba_read_identity",
        "companion_touch_ft6336_stm32wba_configure_interrupt",
        "companion_touch_ft6336_stm32wba_configure_runtime_tuning",
        "companion_touch_ft6336_stm32wba_poll",
    ]:
        require(token in header, f"WBA touch header missing {token}", errors)
    for token in [
        "COMP_FT6336_I2C_ADDRESS_7BIT",
        "COMP_FT6336_IDENTITY_REGISTER",
        "COMP_FT6336_TOUCH_REPORT_REGISTER",
        "COMP_FT6336_G_MODE_REGISTER",
        "COMP_FT6336_G_MODE_TRIGGER",
        "COMP_FT6336_TOUCH_THRESHOLD_REGISTER",
        "COMP_FT6336_PERIOD_ACTIVE_REGISTER",
        "COMP_FT6336_PERIOD_MONITOR_REGISTER",
        "comp_ft6336_decode_touch_report",
        "touch->detected = false",
        "touch->identity_attempted = false",
        "touch->probe_count++",
        "touch->read_count++",
        "touch->error_count++",
        "touch->config.write",
        "interrupt_mode_valid",
        "runtime_tuning_valid",
    ]:
        require(token in source, f"WBA touch source missing {token}", errors)
    for token in [
        "HAL_I2C",
        "HAL_GPIO",
        "GPIO_PIN_",
        "I2C1",
        "I2C3",
        "PC0",
        "PB11",
        "CN7",
        "STM32_WPAN",
        "UTIL_SEQ",
    ]:
        require(token not in combined, f"WBA touch adapter leaked platform fact {token}", errors)

    wb55 = read_text(WB55_APP, errors) + "\n" + read_text(WB55_MAKEFILE, errors)
    require("touch_target_stm32wba_ft6336" not in wb55, "WB55 build must not include WBA touch adapter", errors)


def check_fixture(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WBA touch schema", errors)
    require(data.get("status") == "PASS", "WBA touch fixture must be PASS", errors)
    contract = data.get("contract", {})
    require(set(contract.get("targets", [])) == {"WBA55", "WBA65"}, "WBA touch targets drifted", errors)
    require(contract.get("address_format") == "7_bit", "WBA touch callbacks must use a 7-bit address", errors)
    require(contract.get("portable_decoder") == "comp_ft6336_decode_touch_report", "portable decoder reuse missing", errors)
    require(contract.get("interrupt_mode") == "trigger_with_poll_fallback", "touch interrupt/fallback contract missing", errors)
    require(contract.get("runtime_tuning") == "shared_threshold_and_active_monitor_periods", "shared touch tuning contract missing", errors)
    require(contract.get("reconnect_after_read_error") is True, "touch reconnect behavior missing", errors)
    require(contract.get("hardware_parity_claimed") is False, "WBA touch must not claim hardware parity yet", errors)


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
    check_fixture(expected, errors)
    check_code(errors)
    if args.write_fixture and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.write_fixture:
        require(fixture.exists(), f"missing WBA touch fixture {rel(fixture)}", errors)
        if fixture.exists():
            actual = json.loads(fixture.read_text(encoding="utf-8"))
            require(actual == expected, f"{rel(fixture)} is stale; rerun with --write-fixture", errors)
            check_fixture(actual, errors)
    if errors:
        print("FAIL: Companion STM32WBA FT6336 checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion STM32WBA FT6336 adapter verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
