#!/usr/bin/env python3
"""Static checks for Companion OTA readiness and manifest discipline."""

from __future__ import annotations

import json
import pathlib
import re
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OTA_DOC = REPO_ROOT / "docs/ota_readiness.md"
FLASH_DOC = REPO_ROOT / "docs/bootloader_flash_layout.md"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
REUSE_MAP = REPO_ROOT / "docs/listener_reuse_map.md"
DIAG_EVENTS = REPO_ROOT / "app/companion_pendant/diag_log/diag_log_events.h"
FIXTURE_REPORT = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"
OTA_LOADER_APP_BLE = REPO_ROOT / "cubeide/Companion_BLE_Ota_Loader/Src/app_ble.c"
OTA_LOADER_OTAS_APP = REPO_ROOT / "cubeide/Companion_BLE_Ota_Loader/Src/otas_app.c"
OTA_LOADER_OTAS_STM = REPO_ROOT / "cubeide/Companion_BLE_Ota_Loader/Src/otas_stm.c"
OTA_LOADER_MAKEFILE = REPO_ROOT / "cubeide/Companion_BLE_Ota_Loader/Makefile"
FLASH_TOOL = REPO_ROOT / "tools/flash.ps1"
WIRELESS_STACK_TOOL = REPO_ROOT / "tools/provision_companion_wireless_stack.ps1"
PACKAGE_TOOL = REPO_ROOT / "tools/package_ota_firmware.ps1"
TYPE_PACKAGE_TOOL = REPO_ROOT / "tools/verify_type_companion_package_static.ps1"
BRINGUP_READINESS_TOOL = REPO_ROOT / "tools/verify_companion_bringup_readiness.ps1"
MANUAL_GATE_TOOL = REPO_ROOT / "tools/verify_companion_manual_gate_evidence.ps1"
BLE_OTA_TOOL = REPO_ROOT / "tools/verify_companion_ble_ota.ps1"
WIRED_FLASH_TOOL = REPO_ROOT / "tools/verify_companion_wired_flash.ps1"
TYPE_VISUAL_TOOL = REPO_ROOT / "tools/capture_type_companion_visual.ps1"
TYPE_UI_MANUAL_TOOL = REPO_ROOT / "tools/verify_companion_type_ui_manual.ps1"
HARDWARE_ACCEPTANCE_TOOL = REPO_ROOT / "tools/verify_companion_hardware_acceptance.ps1"

REQUIRED_BLOCKERS = {
    "recording_active",
    "transfer_active",
    "diag_export_active",
    "low_battery",
    "wrong_board_target",
    "invalid_hash",
    "interrupted_transfer",
}
REQUIRED_DIAG_EVENTS = {
    "ota.manifest",
    "ota.readiness",
    "ota.blocker",
    "ota.interrupted_transfer",
    "ota.post_update_self_check",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing {path.relative_to(REPO_ROOT)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def check_ota_doc(errors: list[str]) -> None:
    text = read_text(OTA_DOC, errors)
    for anchor in [
        "BLE_Ota",
        "BLE_p2pServer_ota",
        "COMPANION-PENDANT-CE",
        "STM32WB55CEUx",
        "ota_staging",
        "recording_cache",
        "low-battery",
        "rollback",
        "manifest",
        "Listener",
        "STM32_WPAN",
        "STM32CubeProgrammer",
        "Shared Wireless And Wired Package",
        "tools/flash.ps1 -FlashPackage -PackagePath",
        "Companion_BLE_Ota_Loader.hex",
        "first, then the",
        "must not be copied",
    ]:
        require(anchor in text, f"ota_readiness missing anchor: {anchor}", errors)
    for blocker in REQUIRED_BLOCKERS:
        require(blocker in text, f"ota_readiness missing blocker: {blocker}", errors)
    require("not a firmware swap implementation" in text, "ota_readiness must defer real firmware swap", errors)


def check_flash_doc(errors: list[str]) -> None:
    text = read_text(FLASH_DOC, errors)
    for anchor in [
        "COMPANION-PENDANT-CE",
        "STM32WB55CEUx",
        "ROM bootloader",
        "STM32CubeProgrammer",
        "external-QSPI",
        "ota_staging",
        "recording_cache",
        "diag_log_mirror",
        "single runnable CPU1 app",
        "must not be copied",
    ]:
        require(anchor in text, f"bootloader_flash_layout missing anchor: {anchor}", errors)
    require(
        re.search(r"dual\s+external OTA partitions", text, re.IGNORECASE) is not None,
        "flash layout must state dual external OTA partition policy",
        errors,
    )
    require(
        re.search(r"must not require two complete internal app\s+slots", text, re.IGNORECASE) is not None,
        "flash layout must forbid two internal app slots",
        errors,
    )


def check_ble_contract(errors: list[str]) -> None:
    text = read_text(BLE_CONTRACT, errors)
    for anchor in [
        "OTA readiness",
        "OtaReadinessV1",
        "blocker_bitmap",
        "board_target",
        "mcu",
        "manifest_version",
        "image_sha256_prefix",
        "interrupted_transfer_resume_token",
        "must not accept\nOTA data writes",
    ]:
        require(anchor in text, f"BLE contract missing OTA anchor: {anchor}", errors)
    for blocker in REQUIRED_BLOCKERS:
        require(blocker in text, f"BLE contract missing blocker: {blocker}", errors)


def check_diag_events(errors: list[str]) -> None:
    text = read_text(DIAG_EVENTS, errors)
    require('"ota"' in text, "diag events missing ota source", errors)
    for event in REQUIRED_DIAG_EVENTS:
        require(f'"{event}"' in text, f"diag events missing {event}", errors)

    pairs = re.findall(r"X\(OTA,\s*([A-Z0-9_]+),\s*(0x[0-9A-Fa-f]+|\d+)u?", text)
    ids = [int(value, 0) for _, value in pairs]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    require(not duplicate_ids, f"duplicate OTA diag event ids: {duplicate_ids}", errors)


def check_fixture_report(errors: list[str]) -> None:
    require(FIXTURE_REPORT.exists(), f"missing fixture report: {FIXTURE_REPORT.relative_to(REPO_ROOT)}", errors)
    if not FIXTURE_REPORT.exists():
        return
    data = json.loads(FIXTURE_REPORT.read_text(encoding="utf-8"))
    require(data.get("status") == "PASS", "OTA manifest fixture report did not PASS", errors)
    cases = {case.get("case"): case for case in data.get("cases", [])}
    for case_name in ["good", "good_nucleo_bringup", "bad_invalid_hash", "bad_wrong_board", "bad_missing_blockers"]:
        require(case_name in cases, f"missing fixture case: {case_name}", errors)
        if case_name in cases:
            require(cases[case_name].get("status") == "PASS", f"fixture case did not PASS: {case_name}", errors)
    require(REQUIRED_BLOCKERS <= set(data.get("required_blockers", [])), "fixture report missing required blockers", errors)
    good = cases.get("good", {})
    require(good.get("actual_valid") is True, "good CE manifest fixture must validate", errors)
    good_nucleo = cases.get("good_nucleo_bringup", {})
    require(good_nucleo.get("actual_valid") is True, "good NUCLEO manifest fixture must validate", errors)


def check_reuse_boundary(errors: list[str]) -> None:
    text = read_text(REUSE_MAP, errors)
    for anchor in [
        "components/firmware_ota",
        "ports/esp32/ble_firmware_ota",
        "manifest discipline",
        "ESP-IDF OTA slots",
        "NimBLE service code",
        "no reuse",
    ]:
        require(anchor in text, f"reuse map missing OTA boundary: {anchor}", errors)


def check_local_ota_loader(errors: list[str]) -> None:
    text = read_text(OTA_LOADER_APP_BLE, errors)
    otas_app = read_text(OTA_LOADER_OTAS_APP, errors)
    otas_stm = read_text(OTA_LOADER_OTAS_STM, errors)
    makefile = read_text(OTA_LOADER_MAKEFILE, errors)
    for anchor in [
        '#define COMPANION_BLE_PRODUCT_NAME "companion"',
        "#define COMPANION_BLE_IO_CAPABILITY CFG_IO_CAPABILITY_NO_INPUT_NO_OUTPUT",
        "#define COMPANION_BLE_BONDING_MODE 0",
        "#define COMPANION_BLE_MITM_PROTECTION 0",
        '#include "otas_stm.h"',
        "SVCCTL_Init();",
        "OTAS_STM_Init();",
        "aci_gatt_update_char_value(gap_service_handle, gap_dev_name_char_handle",
    ]:
        require(anchor in text, f"local OTA loader missing anchor: {anchor}", errors)
    require(
        text.find("SVCCTL_Init();") < text.find("OTAS_STM_Init();") < text.find("Adv_Request();"),
        "local OTA loader must register OTAS_STM service after SVCCTL_Init and before advertising",
        errors,
    )
    for anchor in [
        "OTA := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota",
        "$(OTA)/Core/Src/app_entry.c",
        "$(OTA)/Core/Src/flash_driver.c",
        "$(CUBE)/Middlewares/ST/STM32_WPAN/ble/svc/Src/svc_ctl.c",
        "$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto/ble_gatt_aci.c",
    ]:
        require(anchor in makefile, f"local OTA loader Makefile must keep ST BLE_Ota source anchor: {anchor}", errors)
    for anchor in [
        "8f7a0007-7b7d-4f3d-9d6f-6c2d1b7c0000",
        "8f7a7002-7b7d-4f3d-9d6f-6c2d1b7c0000",
        "8f7a7003-7b7d-4f3d-9d6f-6c2d1b7c0000",
        "8f7a7004-7b7d-4f3d-9d6f-6c2d1b7c0000",
        "GATT_NOTIFY_WRITE_REQ_AND_WAIT_FOR_APPL_RESP",
        "OTAS_STM_Is_Value_Handle",
    ]:
        require(anchor in otas_stm, f"local OTAS_STM adapter missing anchor: {anchor}", errors)
    finish = re.search(r"case\s+OTAS_STM_UPLOAD_FINISHED:(?P<body>.*?)case\s+OTAS_STM_CANCEL_UPLOAD:", otas_app, re.S)
    require(finish is not None, "local OTA app missing OTAS_STM_UPLOAD_FINISHED block", errors)
    if finish is not None:
        body = finish.group("body")
        require("OTAS_STM_UpdateChar(OTAS_STM_CONF_ID" in body, "OTA finish must send ST reboot confirmation indication", errors)
        require(
            "OTAS_APP_FinalizeUpload();" not in body,
            "OTA finish must wait for ACI_GATT_SERVER_CONFIRMATION before finalizing/rebooting",
            errors,
        )
    confirm = re.search(r"case\s+OTAS_STM_CONF_EVENT_ID:(?P<body>.*?)break;", otas_app, re.S)
    require(confirm is not None, "local OTA app missing OTAS_STM_CONF_EVENT_ID block", errors)
    if confirm is not None:
        require(
            "OTAS_APP_FinalizeUpload();" in confirm.group("body"),
            "OTA app must finalize/reboot only from the ST confirmation event",
            errors,
        )


def check_wired_package_tooling(errors: list[str]) -> None:
    flash = read_text(FLASH_TOOL, errors)
    wireless_stack = read_text(WIRELESS_STACK_TOOL, errors)
    package = read_text(PACKAGE_TOOL, errors)
    type_package = read_text(TYPE_PACKAGE_TOOL, errors)
    readiness = read_text(BRINGUP_READINESS_TOOL, errors)
    manual_gate = read_text(MANUAL_GATE_TOOL, errors)
    ble_ota = read_text(BLE_OTA_TOOL, errors)
    wired_flash = read_text(WIRED_FLASH_TOOL, errors)
    type_visual = read_text(TYPE_VISUAL_TOOL, errors)
    type_ui_manual = read_text(TYPE_UI_MANUAL_TOOL, errors)
    hardware_acceptance = read_text(HARDWARE_ACCEPTANCE_TOOL, errors)

    for anchor in [
        "[switch] $FlashPackage",
        "[string] $PackagePath",
        "function Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "System.Windows.Forms.MessageBox",
        "Resolve-FactoryManifest",
        "Get-WiredFactoryArtifacts",
        "package_type must be companion-wired-factory",
        "ota_loader",
        "Factory artifact hash mismatch",
        "Invoke-ProgrammerWrite",
        "factory artifact $($artifact.Role)",
        "PASS: $targetLabel flashed.",
        "tools\\provision_companion_wireless_stack.ps1 -CheckOnly",
    ]:
        require(anchor in flash, f"flash.ps1 missing wired package anchor: {anchor}", errors)

    for anchor in [
        "companion.wb55_wireless_stack.provisioning.v1",
        "[switch] $ReadFusInfo",
        "[switch] $InstallBleStack",
        "[switch] $WorkflowLockHeld",
        "function Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "[int] $PromptTimeoutSeconds = 90",
        "WScript.Shell",
        "$popup.Popup",
        "stm32wb5x_BLE_Stack_full_fw.bin",
        "$installAddress = \"0x080D0000\"",
        "Wireless Coprocessor Binary Table, STM32WB5xxG(1M), V1.24.0",
        "FUS_v2 only",
        "STM32_Programmer_CLI.exe -c port=$Port -startfus",
        "$fusInfoAddress = \"0x20030030\"",
        "$fusFallbackAddress = \"0x20010010\"",
        "02020[0-9A-F]00",
        "fus_v2_2_ready_for_wireless_stack",
        "-fwupgrade",
        "firstinstall=0",
        "nSWboot0=1",
        "Companion WB55 无线栈操作确认",
        "Refusing to touch Companion WB55 hardware without workflow lock acknowledgement",
        "This script will not auto-upgrade FUS",
        "companion_wireless_stack_result_json=",
        "companion-wireless-stack-summary.json",
    ]:
        require(anchor in wireless_stack, f"provision_companion_wireless_stack.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "-FlashPackage -PackagePath",
        "factory\\$factoryPackageName\\manifest.json",
        "restore both the ST BLE_Ota loader and Companion app over SWD",
        "Use STM32CubeProgrammer or tools/flash.ps1 -FlashPackage",
    ]:
        require(anchor in package, f"package_ota_firmware.ps1 missing wired package anchor: {anchor}", errors)

    require(
        "-FlashNucleoBringup -ImagePath <package>\\factory" not in package,
        "package script must not document the old app-only wired flash command",
        errors,
    )

    for anchor in [
        "STM32WB_ST_OTA_TRANSPORT_BOUNDARY",
        "gattConfirmUuid",
        "stm32wb_st_manifest_requires_confirm_gatt_boundary",
        "FirmwareOtaBleTransferTransport",
        "request.manifest.protocolName === STM32WB_ST_OTA_TRANSPORT_BOUNDARY.protocolName",
        "evaluateFirmwareOtaPreflight",
        "--wired-firmware-check",
        "companion-wired-factory",
        "ota_loader",
        "Invoke-TypeUiSamePackageCheck",
        "Type Companion temporary debug page same-package check",
        "tools\\\\verify_companion_bringup_readiness.ps1",
        "Invoke-TypeStm32OtaConfirmCheck",
        "selectedPackage?.path ?? null",
        "import { FirmwareOtaPanel } from './FirmwareOtaPanel';",
        "COMPANION_FIRMWARE_PANEL_BLE_STATUS",
        "bleStatus={COMPANION_FIRMWARE_PANEL_BLE_STATUS}",
        'params.get("visual") === "settings-companion"',
        'isSettingsCompanionVisual ? `"companion`" : `"device`"',
        "tools\\\\verify_companion_wired_flash.ps1",
        "Companion wired factory flash validation",
        "isStm32WbSwdTarget(selectedPayload?.target)",
        "const activeWiredPort = stm32WbSwd ? 'SWD' : port",
        "settings.recording.wiredFirmwareStm32Desc",
        "settings.recording.wiredFirmwareProgressConnectingSwd",
        "function isStm32WbSwdTarget",
        "stm32wb55ceux",
        "STM32WB ST OTA confirmation indication is required",
        "PASS: Companion package is accepted by Type Companion OTA/wired static integration checks.",
    ]:
        require(anchor in type_package, f"verify_type_companion_package_static.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "[switch] $Full",
        "verify_listener_vka1_static.py",
        "verify_ota_contract_static.py",
        "verify_type_companion_package_static.ps1",
        "verify_companion_manual_gate_evidence.ps1",
        "verify_companion_ble_ota.ps1",
        "verify_companion_wired_flash.ps1",
        "verify_companion_type_a1_a2.ps1",
        "verify_companion_type_ui_manual.ps1",
        "verify_companion_hardware_acceptance.ps1",
        "capture_type_companion_visual.ps1",
        "-SkipTypeRust",
        "-SkipTypeCompanionVisual",
        "npm.cmd",
        "PASS_STATIC_MANUAL_GATES_REMAIN",
        "ConvertTo-ReadinessMarkdown",
        "Companion Bring-Up Readiness Report",
        "Manual Gates Remaining",
        "summary.md",
        "summary_markdown",
        "Companion Type A1/A2 validation",
        "real Companion BLE OTA through Type",
        "Companion BLE OTA validation",
        "Companion BLE OTA dry run",
        "Companion wired factory flash validation",
        "Companion wired flash dry run",
        "Companion Type UI validation",
        "Companion Type UI manual dry run",
        "Companion hardware acceptance dry run",
        "Type temporary Companion visual smoke",
        "type-companion-visual",
        "type-companion-visual-summary.json",
        "Type temporary Companion debug page",
        "manual_evidence_verifier",
        "hardware_acceptance_runner",
        "hardware_acceptance_dry_run",
        "Companion manual gate evidence checklist",
        "hardware-acceptance-dry-run",
        "type-ui-manual-dry-run",
        "companion-type-ui-manual-summary.json",
        "companion-hardware-acceptance-summary.json",
        "-TypeUiEvidencePath",
    ]:
        require(anchor in readiness, f"verify_companion_bringup_readiness.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "companion.type_visual.v1",
        "settings-companion",
        "--headless=new",
        "--screenshot=",
        "--dump-dom",
        "Companion Pendant bring-up",
        "A1 smoke",
        "A2 smoke",
        "蓝牙 OTA",
        "总体验收",
        "ST-LINK / SWD",
        "type_companion_visual_result_json=",
        "Stop-ProcessTree -RootProcessId",
        "--strictPort",
        "AllowTimeoutWithArtifact",
        "type-companion-visual-summary.json",
    ]:
        require(anchor in type_visual, f"capture_type_companion_visual.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "companion.manual_gate_evidence.v1",
        "[switch] $ChecklistOnly",
        "CHECKLIST_PENDING",
        "firmware_ota_result_json=",
        "companion_ble_ota_result_json=",
        "companion_wired_flash_result_json=",
        "companion_type_ui_manual_result_json=",
        "type_report_json",
        "verify_companion_ble_ota.ps1",
        "verify_companion_wired_flash.ps1",
        "wired_firmware_result_json=",
        "extra",
        "result",
        "stm32wb_st_ble_ota",
        "STM32WB wired factory flash completed and verified by STM32CubeProgrammer",
        "real Companion Type A1/A2",
        "real Companion BLE OTA through Type",
        "real Companion wired flash from same package",
        "Type temporary Companion debug page",
        "companion.type_ui_manual.validation.v1",
        "operator_confirmed",
        "Type UI required actions include the aggregate hardware acceptance command",
        "总体验收 / Companion hardware acceptance",
        "including 总体验收 command visibility",
        "Companion Manual Gate Evidence",
    ]:
        require(anchor in manual_gate, f"verify_companion_manual_gate_evidence.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "companion.type_ui_manual.validation.v1",
        "[switch] $Execute",
        "[switch] $WorkflowLockHeld",
        "Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "Companion Type 页面真机验证",
        "确认 Companion Type 页面结果",
        "BLE 订阅 PASS",
        "A1 smoke PASS",
        "A2 smoke PASS",
        "ST-LINK / SWD",
        "with-lock -Resource Companion-WB55,BLE-Companion",
        "companion_type_ui_manual_result_json=",
        "DRY-RUN: Companion Type UI manual validation is ready.",
        "Refusing to run Companion Type UI manual validation without -WorkflowLockHeld.",
        "companion-type-ui-manual-summary.json",
        "总体验收",
        "Companion hardware acceptance 命令",
        "aggregate acceptance command",
    ]:
        require(anchor in type_ui_manual, f"verify_companion_type_ui_manual.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "companion.hardware_acceptance.validation.v1",
        "[switch] $Execute",
        "[switch] $WorkflowLockHeld",
        "[switch] $SkipWirelessStackProvisioning",
        "Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "Companion 总体验收即将开始",
        "with-lock -Resource Companion-WB55,BLE-Companion",
        "provision_companion_wireless_stack.ps1",
        "-InstallBleStack",
        "verify_companion_type_a1_a2.ps1",
        "verify_companion_ble_ota.ps1",
        "verify_companion_wired_flash.ps1",
        "verify_companion_type_ui_manual.ps1",
        "verify_companion_manual_gate_evidence.ps1",
        ".\\tools\\flash.ps1",
        "-FlashAudioFixture",
        "ensure CPU2 BLE wireless stack",
        "prep flash Companion BLE audio fixture",
        "-A1A2SummaryPath",
        "-BleOtaEvidencePath",
        "-WiredFlashEvidencePath",
        "-TypeUiEvidencePath",
        "- Wireless stack: ``$($Report[\"evidence\"][\"wireless_stack\"])``",
        "manual gate evidence verifier",
        "companion_hardware_acceptance_result_json=",
        "DRY-RUN: Companion hardware acceptance runner is ready.",
        "Refusing to run Companion hardware acceptance without -WorkflowLockHeld.",
        "CPU2 BLE wireless stack 预检/安装",
        "runs while the VKA1 audio fixture is still flashed",
        "prepares the board for Listener-compatible A1/A2 and Type UI smoke",
        "restores the package OTA loader before BLE OTA",
        "Type 页面验收必须在包刷写前完成",
        "BLE OTA 必须在有线同包刷机之后执行",
    ]:
        require(anchor in hardware_acceptance, f"verify_companion_hardware_acceptance.ps1 missing anchor: {anchor}", errors)
    type_ui_call = 'Invoke-AcceptanceStep -Name "Type temporary Companion debug page"'
    wireless_call = 'Invoke-AcceptanceStep -Name "ensure CPU2 BLE wireless stack"'
    fixture_call = 'Invoke-AcceptanceStep -Name "prep flash Companion BLE audio fixture"'
    a1_a2_call = 'Invoke-AcceptanceStep -Name "real Companion Type A1/A2"'
    wired_call = 'Invoke-AcceptanceStep -Name "real Companion wired flash from same package"'
    ble_ota_call = 'Invoke-AcceptanceStep -Name "real Companion BLE OTA through Type"'
    require(
        0 <= hardware_acceptance.find(wireless_call) < hardware_acceptance.find(fixture_call),
        "hardware acceptance runner must provision/read the CPU2 BLE wireless stack before flashing CPU1 BLE fixtures",
        errors,
    )
    require(
        0 <= hardware_acceptance.find(fixture_call) < hardware_acceptance.find(a1_a2_call),
        "hardware acceptance runner must flash the BLE audio fixture before A1/A2",
        errors,
    )
    require(
        0 <= hardware_acceptance.find(type_ui_call) < hardware_acceptance.find(ble_ota_call),
        "hardware acceptance runner must execute Type UI while the VKA1 fixture is still flashed, before BLE OTA",
        errors,
    )
    require(
        0 <= hardware_acceptance.find(wired_call) < hardware_acceptance.find(ble_ota_call),
        "hardware acceptance runner must restore the package OTA loader through wired flash before BLE OTA",
        errors,
    )

    for anchor in [
        "companion.ble_ota.validation.v1",
        "[switch] $Execute",
        "[switch] $WorkflowLockHeld",
        "Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "Companion BLE OTA 验证即将开始",
        "--firmware-ota-transfer",
        "firmware_ota_result_json=",
        "companion_ble_ota_result_json=",
        "stm32wb_st_ble_ota",
        "versionConfirmed",
        "DRY-RUN: Companion BLE OTA validation is ready.",
        "Refusing to run Companion BLE OTA validation without -WorkflowLockHeld.",
    ]:
        require(anchor in ble_ota, f"verify_companion_ble_ota.ps1 missing anchor: {anchor}", errors)

    for anchor in [
        "companion.wired_flash.validation.v1",
        "[switch] $Execute",
        "[switch] $WorkflowLockHeld",
        "Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "Companion 有线刷机验证即将开始",
        "--wired-firmware-check",
        "--wired-firmware-flash",
        "wired_firmware_result_json=",
        "companion_wired_flash_result_json=",
        "Companion wired factory flash validation",
        "STM32WB wired factory flash completed and verified by STM32CubeProgrammer",
        "DRY-RUN",
        "Refusing to run Companion wired flash validation without -WorkflowLockHeld.",
    ]:
        require(anchor in wired_flash, f"verify_companion_wired_flash.ps1 missing anchor: {anchor}", errors)


def main() -> int:
    errors: list[str] = []
    check_ota_doc(errors)
    check_flash_doc(errors)
    check_ble_contract(errors)
    check_diag_events(errors)
    check_fixture_report(errors)
    check_reuse_boundary(errors)
    check_local_ota_loader(errors)
    check_wired_package_tooling(errors)

    if errors:
        print("FAIL: Companion OTA static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion OTA readiness contract static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
