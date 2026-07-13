#!/usr/bin/env python3
"""Keep the Companion USB development plan target-aware."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "docs" / "companion_usb_development_requirements.md"
PLAN = ROOT / "docs" / "companion_screen_project_plan.md"
IOC = ROOT / "docs" / "companion_pendant_ioc.md"
BOOT_LAYOUT = ROOT / "docs" / "bootloader_flash_layout.md"
FIXTURE = ROOT / "docs" / "validation" / "companion-usb-development-requirements.json"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()

    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    ioc = IOC.read_text(encoding="utf-8")
    boot_layout = BOOT_LAYOUT.read_text(encoding="utf-8")
    errors: list[str] = []

    for anchor in (
        "WBA55 无原生 USB/ROM USB DFU",
        "USB-UART bridge",
        "ROM USART bootloader",
        "WBA65 有原生 USB OTG",
        "ROM USB DFU",
        "HSE32",
        "SWDIO",
        "SWCLK",
        "NRST",
        "Denzic BLE OTA",
        "不能机械照搬",
    ):
        require(anchor in requirements, f"USB development requirement missing: {anchor}", errors)

    require("SCR-19" in plan, "project plan does not register SCR-19", errors)
    require("USB CDC 串口 + DFU 升级" in ioc, "WB55 product USB baseline drifted", errors)
    require("resident CPU1 bootloader" in boot_layout, "resident bootloader boundary drifted", errors)
    require("ROM bootloader" in boot_layout, "ROM recovery boundary drifted", errors)

    result = {
        "schema_id": "companion.usb_development.requirements.v1",
        "status": "PASS" if not errors else "FAIL",
        "current_devboard": "ST-LINK VCP + SWD only",
        "wba55": "external USB-UART VCP + ROM USART bootloader + SWD pads",
        "wba65": "native USB CDC + ROM USB DFU + SWD pads",
        "shared_rule": "USB development transport does not replace ROM recovery, SWD rescue, or signed Denzic OTA",
        "errors": errors,
    }
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
