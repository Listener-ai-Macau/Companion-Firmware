#!/usr/bin/env python3
"""Verify COMP-REQ-781 WB55 power-setting persistence and partition safety."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
MENU = ROOT / "app" / "companion_pendant" / "epaper" / "screen_menu.c"
MAKEFILE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
STORE_C = ROOT / "app" / "companion_pendant" / "power" / "power_settings_store.c"
STORE_H = ROOT / "app" / "companion_pendant" / "power" / "power_settings_store.h"
PRODUCT_REQ = ROOT / "docs" / "companion_product_requirements.md"
LOW_POWER_REQ = ROOT / "docs" / "companion_low_power_requirements.md"
HOST_TEST = ROOT / "tools" / "test_power_policy_host.ps1"
DEFAULT_OUT = (
    ROOT / ".cache" / "validation" / "comp-req-781-power-settings-20260815"
    / "MACHINE_READY.json"
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--skip-host-test", action="store_true")
    args = parser.parse_args()

    main_source = MAIN.read_text(encoding="utf-8")
    menu_source = MENU.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    store_c = STORE_C.read_text(encoding="utf-8")
    store_h = STORE_H.read_text(encoding="utf-8")
    product_req = PRODUCT_REQ.read_text(encoding="utf-8")
    low_power_req = LOW_POWER_REQ.read_text(encoding="utf-8")
    errors: list[str] = []

    require("#define FLASH_POWER_SETTINGS_ADDRESS 0x001FD000u" in main_source,
            "settings sector is not fixed at 0x001FD000", errors)
    require("COMP_RECORDING_RESOURCE_EXTERNAL_LIMIT == FLASH_POWER_SETTINGS_ADDRESS" in main_source,
            "settings sector no longer follows read-only diagnostic resources", errors)
    require("FLASH_POWER_SETTINGS_ADDRESS + COMP_POWER_SETTINGS_SECTOR_BYTES ==" in main_source and
            "COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET" in main_source,
            "settings sector no longer ends exactly at UI root A", errors)
    require("FLASH_TEST_ADDRESS" not in main_source and
            "run_flash_write_read_smoke" not in main_source,
            "destructive flash smoke can still overwrite persisted settings", errors)
    require("power_settings_store.c" in makefile,
            "power settings store is absent from the WB55 build", errors)

    load_at = main_source.find("    load_power_settings();")
    timer_at = main_source.find("    init_low_power_idle_timer();")
    require(0 <= load_at < timer_at,
            "persisted setting is not loaded before RTC timer initialization", errors)
    require(main_source.count("save_power_settings(") >= 3,
            "menu and restore-default save hooks are incomplete", errors)
    require("COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE" in main_source and
            "COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP" in menu_source and
            "s_browser_menu_tap_kind == COMPANION_BROWSER_MENU_KIND_ACTION" in main_source and
            "    (void)save_power_settings();" in main_source,
            "auto-sleep or restore-default event is not wired to persistence", errors)

    for anchor in [
        "COMP_POWER_SETTINGS_SECTOR_BYTES 4096u",
        "COMP_POWER_SETTINGS_RECORD_BYTES 16u",
        "COMP_POWER_SETTINGS_SLOT_COUNT",
    ]:
        require(anchor in store_h, f"store layout missing: {anchor}", errors)
    for anchor in [
        "COMP_POWER_SETTINGS_MAGIC",
        "COMP_POWER_SETTINGS_VERSION",
        "record_crc32",
        "supported_minutes",
        "store->port.erase",
        "memcmp(record, verify",
        "COMP_POWER_SETTINGS_DEFAULT_MINUTES 3u",
    ]:
        require(anchor in store_c, f"store safety behavior missing: {anchor}", errors)
    require("minutes == 0u || minutes == 1u || minutes == 3u || minutes == 5u" in store_c,
            "store accepts values outside 0/1/3/5", errors)

    for anchor in [
        "COMP-REQ-781",
        "0x001FD000..0x001FE000",
        "断写或 CRC 错误记录",
        "硬复位",
    ]:
        require(anchor in product_req, f"product requirement missing: {anchor}", errors)
    for anchor in ["跨复位和断电保持", "CRC32 设置日志", "空白或仅损坏"]:
        require(anchor in low_power_req, f"low-power requirement missing: {anchor}", errors)

    host_test = {"status": "SKIPPED", "stdout": "", "stderr": ""}
    if not args.skip_host_test:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HOST_TEST)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        host_test = {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        require(completed.returncode == 0 and
                "PASS: power idle" in completed.stdout and
                "settings all-field/boundary/v1-migration/CRC/torn/"
                "write-amplification and behavior matrix pass"
                in completed.stdout,
                "host NOR fault-injection test failed", errors)

    result = {
        "schema": "companion.comp_req_781.power_settings.v1",
        "status": "MACHINE_READY" if not errors else "FAILED",
        "partition": {
            "start": "0x001FD000",
            "end_exclusive": "0x001FE000",
            "bytes": 4096,
            "recording_start": "0x00200000",
        },
        "record": "16-byte append-only magic/version/generation/value/CRC32 with readback",
        "supported_minutes": [0, 1, 3, 5],
        "fault_policy": "torn/corrupt ignored; prior valid wins; blank/corrupt-only defaults to 3",
        "host_test": host_test,
        "errors": errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
