#!/usr/bin/env python3
"""Verify the single Denzic OTA v1 contract across host and embedded products."""

from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
TYPE_ROOT = REPO_ROOT.parent / "Companion-Type"
PLATFORM_OTA = REPO_ROOT / "third_party" / "denzic-platform" / "ota"


def read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def require_tokens(text: str, tokens: list[str], label: str, errors: list[str]) -> None:
    for token in tokens:
        require(token in text, f"{label} missing token: {token}", errors)


def forbid_tokens(text: str, tokens: list[str], label: str, errors: list[str]) -> None:
    for token in tokens:
        require(token not in text, f"{label} contains obsolete token: {token}", errors)


def check_shared_core(errors: list[str]) -> None:
    protocol_path = PLATFORM_OTA / "protocol" / "ota_v1.json"
    host_rust = PLATFORM_OTA / "host" / "rust" / "src" / "lib.rs"
    host_typescript = PLATFORM_OTA / "host" / "typescript" / "src" / "index.ts"
    embedded_header = PLATFORM_OTA / "embedded" / "c" / "include" / "denzic_ota_v1.h"
    embedded_source = PLATFORM_OTA / "embedded" / "c" / "src" / "denzic_ota_v1.c"
    for path in [protocol_path, host_rust, host_typescript, embedded_header, embedded_source]:
        require(path.is_file(), f"Denzic-Platform OTA layer missing: {path}", errors)
    if not protocol_path.is_file():
        return
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    require(protocol.get("name") == "denzic_ota_v1", "shared protocol name drifted", errors)
    require(protocol.get("version") == 1, "shared protocol version drifted", errors)
    require(protocol.get("magic_ascii") == "DOV1", "shared protocol magic drifted", errors)
    require(protocol.get("control_bytes") == 16, "shared control size drifted", errors)
    require(protocol.get("data_header_bytes") == 4, "shared data header size drifted", errors)
    require(protocol.get("status_bytes") == 24, "shared status size drifted", errors)


def check_embedded_product(errors: list[str]) -> None:
    makefile = read(REPO_ROOT / "cubeide" / "Companion_BLE_Ota_Loader" / "Makefile", errors)
    adapter = read(
        REPO_ROOT
        / "cubeide"
        / "Companion_BLE_Ota_Loader"
        / "Src"
        / "companion_ota_v1.c",
        errors,
    )
    app_ble = read(
        REPO_ROOT / "cubeide" / "Companion_BLE_Ota_Loader" / "Src" / "app_ble.c",
        errors,
    )
    package_tool = read(REPO_ROOT / "tools" / "package_ota_firmware.ps1", errors)
    require_tokens(
        makefile,
        [
            "Src/companion_ota_v1.c",
            "$(DENZIC_OTA)/src/denzic_ota_v1.c",
            "$(DENZIC_OTA)/include",
        ],
        "embedded Makefile",
        errors,
    )
    require_tokens(
        adapter,
        [
            "void SVCCTL_SvcInit(void)",
            "denzic_ota_v1_init",
            "denzic_ota_v1_handle_control",
            "denzic_ota_v1_handle_data",
            "denzic_ota_v1_encode_status",
            "COMPANION_OTA_V1_REBOOT_GRACE_MS",
        ],
        "Companion embedded adapter",
        errors,
    )
    require_tokens(
        package_tool,
        [
            'name = "denzic_ota_v1"',
            "version = 1",
            'firmware_capability = "denzic_ota_v1"',
            'gatt_contract = "denzic_ota_v1"',
            'kind = "denzic_ota_v1_stm32wb_loader"',
        ],
        "Companion package tool",
        errors,
    )
    obsolete_files = ["otas_app.c", "otas_stm.c", "companion_ota_v2.c", "companion_ota_v2.h"]
    source_dir = REPO_ROOT / "cubeide" / "Companion_BLE_Ota_Loader" / "Src"
    for name in obsolete_files:
        require(not (source_dir / name).exists(), f"obsolete OTA runtime still exists: {name}", errors)
        require(name not in makefile, f"embedded Makefile still compiles obsolete OTA runtime: {name}", errors)
    forbid_tokens(
        adapter + app_ble + makefile + package_tool,
        ["companion_ota_v2", "companion_ble_ota_v2", "stm32wb_st_ble_ota", "STM32WB_ST_OTA"],
        "Companion embedded OTA runtime",
        errors,
    )


def check_host_product(errors: list[str]) -> None:
    cargo = read(TYPE_ROOT / "apps" / "windows" / "src-tauri" / "Cargo.toml", errors)
    adapter = read(
        TYPE_ROOT
        / "apps"
        / "windows"
        / "src-tauri"
        / "src"
        / "backend"
        / "firmware_ota.rs",
        errors,
    )
    bridge = read(
        TYPE_ROOT
        / "apps"
        / "windows"
        / "src-tauri"
        / "src"
        / "backend"
        / "ble_bridge.rs",
        errors,
    )
    commands = read(
        TYPE_ROOT / "apps" / "windows" / "src-tauri" / "src" / "commands.rs",
        errors,
    )
    lib = read(TYPE_ROOT / "apps" / "windows" / "src-tauri" / "src" / "lib.rs", errors)
    require_tokens(
        cargo,
        ['denzic-ota-core = { path = "../../../third_party/denzic-platform/ota/host/rust" }'],
        "Companion-Type Cargo",
        errors,
    )
    require_tokens(
        adapter,
        [
            'const PACKAGE_TYPE: &str = "companion-firmware-ota";',
            "denzic_ota_core::PROTOCOL_NAME",
            "denzic_ota_core::PROTOCOL_VERSION",
            "file.sha256",
            "validate_package",
            "8f7a8007-7b7d-4f3d-9d6f-6c2d1b7c0000",
            "8f7a8002-7b7d-4f3d-9d6f-6c2d1b7c0000",
            "8f7a8004-7b7d-4f3d-9d6f-6c2d1b7c0000",
            "8f7a8005-7b7d-4f3d-9d6f-6c2d1b7c0000",
        ],
        "Companion-Type product adapter",
        errors,
    )
    require_tokens(
        bridge,
        [
            "impl denzic_ota_core::OtaV1Transport for CompanionOtaV1Transport",
            "denzic_ota_core::transfer(",
            "WriteType::WithoutResponse",
            "read_status",
            "write_finish",
        ],
        "Companion-Type BLE transport",
        errors,
    )
    require("transfer_companion_firmware_ota" in commands, "host command is not exposed", errors)
    require(
        "commands::transfer_companion_firmware_ota" in lib,
        "host command is not registered with Tauri",
        errors,
    )
    require("--firmware-ota-transfer" in lib, "host OTA CLI is not exposed", errors)
    require("firmware_ota_result_json=" in lib, "host OTA CLI lacks machine evidence", errors)
    forbid_tokens(
        adapter + bridge + commands + lib,
        ["companion_ota_v2", "companion_ble_ota_v2", "stm32wb_st_ble_ota", "STM32WB_ST_OTA"],
        "Companion-Type OTA runtime",
        errors,
    )


def check_cross_product_gate(errors: list[str]) -> None:
    gate = read(REPO_ROOT / "tools" / "verify_type_companion_package_static.ps1", errors)
    hardware_gate = read(REPO_ROOT / "tools" / "verify_companion_ble_ota.ps1", errors)
    require_tokens(
        gate,
        [
            "..\\..\\Companion-Type",
            "Assert-HostAdapter",
            "Assert-EmbeddedAdapter",
            "COMPANION_TYPE_OTA_TEST_MANIFEST",
            "validates_external_package_when_requested",
            "PASS: Companion OTA v1 package is implemented and validated on both host and embedded sides.",
        ],
        "cross-product OTA gate",
        errors,
    )
    require_tokens(
        hardware_gate,
        [
            "C:\\Program Files\\Companion Type\\companion-type.exe",
            "Real Companion OTA acceptance must run the MSI-installed Companion Type",
            '"--firmware-ota-transfer"',
        ],
        "Companion installed-host OTA gate",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    check_shared_core(errors)
    check_embedded_product(errors)
    check_host_product(errors)
    check_cross_product_gate(errors)
    if errors:
        print("FAIL: Companion Denzic OTA v1 contract checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: one Denzic OTA v1 contract is wired through shared host and embedded cores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
