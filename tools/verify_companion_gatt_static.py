#!/usr/bin/env python3
"""Static checks for the Companion STM32WB GATT skeleton."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE = REPO_ROOT / "docs" / "ble_uuid_table.json"
CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"
GATT_HEADER = REPO_ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.h"
GATT_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
APP_CONF = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "app_conf.h"
BLE_CONF = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "ble_conf.h"
MAIN_SOURCE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def check_uuid_table(source: str, errors: list[str]) -> None:
    table = json.loads(UUID_TABLE.read_text(encoding="utf-8"))
    required_payloads = {
        "DeviceStatusV1": "companion_gatt_device_status_v1_t",
        "BatteryChargeV1": "companion_gatt_battery_charge_v1_t",
        "CardWriteV1": "companion_gatt_card_write_v1_t",
        "CardStatusV1": "companion_gatt_card_status_v1_t",
        "RecordingControlV1": "companion_gatt_recording_control_v1_t",
        "RecordingListV1": "companion_gatt_recording_list_v1_t",
        "RecordingChunkPullV1": "companion_gatt_recording_chunk_pull_v1_t",
        "SettingsV1": "companion_gatt_settings_v1_t",
        "DiagLogPullV1": "companion_gatt_diag_log_pull_v1_t",
        "DeletePrivacyV1": "companion_gatt_delete_privacy_v1_t",
        "OtaReadinessV1": "companion_gatt_ota_readiness_v1_t",
    }
    header = read(GATT_HEADER)
    for payload, struct_name in required_payloads.items():
        require(struct_name in header, f"missing payload struct for {payload}", errors)
        parser = "companion_gatt_parse_" + re.sub(r"(?<!^)([A-Z])", r"_\1", payload).lower()
        require(parser in header and parser in source, f"missing parser for {payload}", errors)

    expected_names = []
    expected_prefixes = []
    for service in table["services"]:
        service_uuid = service["uuid"].split("-")[0]
        expected_prefixes.append(int(service_uuid[-4:], 16))
        for characteristic in service["characteristics"]:
            name = characteristic["name"]
            if name.startswith("ota_st_"):
                continue
            expected_names.append(name)
            char_uuid = characteristic["uuid"].split("-")[0]
            expected_prefixes.append(int(char_uuid[-4:], 16))

    for name in expected_names:
        enum_name = "COMPANION_GATT_CHAR_" + name.upper()
        require(enum_name in header, f"missing enum for UUID-table characteristic {name}", errors)
        require(f'"{name}"' in source, f"missing runtime name for characteristic {name}", errors)

    for prefix in expected_prefixes:
        require(f"0x{prefix:04x}u" in source.lower(), f"missing UUID prefix 0x{prefix:04x}", errors)


def check_stm32_surface(source: str, app_ble: str, errors: list[str]) -> None:
    for anchor in [
        "aci_gatt_add_service",
        "aci_gatt_add_char",
        "aci_gatt_update_char_value",
        "SVCCTL_RegisterSvcHandler",
        "SVCCTL_App_Notification",
        "ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE",
        "GATT_NOTIFY_ATTRIBUTE_WRITE",
        "COMPANION_GATT_QUEUE_DEPTH",
        "companion_gatt_stm32wb_drain",
    ]:
        require(anchor in source or anchor in app_ble, f"missing STM32 GATT anchor {anchor}", errors)

    start = source.find("static SVCCTL_EvtAckStatus_t companion_gatt_stm32wb_event_handler")
    end = source.find("static companion_gatt_parse_result_t companion_gatt_copy_fixed")
    require(start >= 0 and end > start, "missing GATT event handler body", errors)
    if start >= 0 and end > start:
        body = source[start:end]
        forbidden_patterns = {
            "display": r"\bdisplay\b|epaper_render|card_render",
            "flash": r"\bflash\b|qspi|spi_flash",
            "microphone": r"\bmicrophone\b|mic_",
            "ota work": r"\bcompanion_ota\b|ota_",
            "recording FSM": r"recording_fsm_dispatch",
        }
        for label, pattern in forbidden_patterns.items():
            require(re.search(pattern, body.lower()) is None, f"GATT callback must not block on {label}", errors)
        require("companion_gatt_enqueue" in body, "GATT callback must enqueue parsed/copy payloads", errors)

    require("UTIL_SEQ_SetTask" in app_ble, "app must schedule queued GATT work through STM32 sequencer", errors)
    require("CFG_TASK_COMPANION_GATT_ID" in read(APP_CONF), "app_conf must define Companion GATT task id", errors)


def app_conf_define(text: str, name: str) -> int | None:
    match = re.search(rf"#define\s+{re.escape(name)}\s+\(?\s*(\d+)\s*\)?", text)
    if match is None:
        return None
    return int(match.group(1))


def check_nucleo_ble_capacity(errors: list[str]) -> None:
    app_conf = read(APP_CONF)
    ble_conf = read(BLE_CONF)
    uuid_table = json.loads(UUID_TABLE.read_text(encoding="utf-8"))
    required_services = 2 + 1 + len(uuid_table["services"])

    service_count = app_conf_define(app_conf, "CFG_BLE_NUM_GATT_SERVICES")
    attr_count = app_conf_define(app_conf, "CFG_BLE_NUM_GATT_ATTRIBUTES")
    value_array_size = app_conf_define(app_conf, "CFG_BLE_ATT_VALUE_ARRAY_SIZE")
    service_callback_count = app_conf_define(ble_conf, "BLE_CFG_SVC_MAX_NBR_CB")

    require(
        service_count is not None and service_count >= required_services,
        f"CFG_BLE_NUM_GATT_SERVICES must cover GAP/GATT, VKA1, and Companion services; need >= {required_services}",
        errors,
    )
    require(
        attr_count is not None and attr_count >= 96,
        "CFG_BLE_NUM_GATT_ATTRIBUTES must be sized for VKA1 plus Companion-native services",
        errors,
    )
    require(
        value_array_size is not None and value_array_size >= 4096,
        "CFG_BLE_ATT_VALUE_ARRAY_SIZE must be sized for 248-byte notify/read values",
        errors,
    )
    require(
        service_callback_count is not None and service_callback_count >= 2,
        "BLE_CFG_SVC_MAX_NBR_CB must cover both VKA1 audio and Companion-native GATT service handlers",
        errors,
    )


def check_nucleo_boot_path(errors: list[str]) -> None:
    main_source = read(MAIN_SOURCE)
    boot_selftests = app_conf_define(main_source, "COMPANION_RUN_BOOT_SELFTESTS")

    require(
        boot_selftests == 0,
        "COMPANION_RUN_BOOT_SELFTESTS must default to 0 so BLE acceptance reaches the main loop",
        errors,
    )
    require(
        "#if COMPANION_RUN_BOOT_SELFTESTS" in main_source and "boot_selftests=skipped" in main_source,
        "main.c must gate boot selftests behind COMPANION_RUN_BOOT_SELFTESTS",
        errors,
    )


def check_build_integration(errors: list[str]) -> None:
    makefile = read(MAKEFILE)
    for token in [
        "$(ROOT)/app/companion_pendant/gatt",
        "$(ROOT)/app/companion_pendant/gatt/companion_gatt_stm32wb.c",
    ]:
        require(token in makefile, f"Makefile missing {token}", errors)

    app_ble = read(APP_BLE)
    for token in [
        '#include "companion_gatt_stm32wb.h"',
        "Companion_Gatt_Init",
        "Companion_Gatt_Task",
        "companion_gatt_stm32wb_init",
    ]:
        require(token in app_ble, f"app_ble.c missing {token}", errors)


def check_forbidden_apis(errors: list[str]) -> None:
    text = "\n".join(read(path) for path in [GATT_HEADER, GATT_SOURCE, APP_BLE, MAKEFILE])
    for token in ["NimBLE", "BLEDevice", "idf.py"]:
        require(token not in text, f"forbidden non-STM32 BLE/API token found: {token}", errors)

    changed_third_party = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB").strip()
    require(not changed_third_party, f"third_party/STM32CubeWB modified: {changed_third_party}", errors)


def main() -> int:
    errors: list[str] = []
    source = read(GATT_SOURCE)
    app_ble = read(APP_BLE)
    check_uuid_table(source, errors)
    check_stm32_surface(source, app_ble, errors)
    check_nucleo_ble_capacity(errors)
    check_nucleo_boot_path(errors)
    check_build_integration(errors)
    check_forbidden_apis(errors)

    contract = read(CONTRACT)
    require(
        "parse-and-enqueue" in contract or "parse and enqueue" in contract,
        "BLE contract missing parse-and-enqueue boundary",
        errors,
    )
    for token in ["diagnostics/log pull", "OTA readiness"]:
        require(token in contract, f"BLE contract missing {token}", errors)

    if errors:
        print("FAIL: Companion GATT static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print("PASS: Companion STM32WB GATT skeleton static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
