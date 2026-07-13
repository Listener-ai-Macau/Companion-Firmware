#!/usr/bin/env python3
"""Static checks for the Companion Listener-compatible VKA1 audio bridge."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DENZIC_ROOT = REPO_ROOT.parents[1]
LISTENER_TYPE_ROOT = DENZIC_ROOT / "Listener/Listener-Type"
LISTENER_FIRMWARE_ROOT = DENZIC_ROOT / "Listener/Listener-Firmware"

AUDIO_DIR = REPO_ROOT / "app/companion_pendant/audio_stream"
HEADER = AUDIO_DIR / "audio_stream.h"
SOURCE = AUDIO_DIR / "audio_stream.c"
STM32WB_HEADER = AUDIO_DIR / "audio_stream_stm32wb.h"
STM32WB_SOURCE = AUDIO_DIR / "audio_stream_stm32wb.c"
BRINGUP_APP_CONF = REPO_ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/app_conf.h"
BRINGUP_APP_BLE = REPO_ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
BRINGUP_MAIN = REPO_ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
BRINGUP_MAKEFILE = REPO_ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
FLASH_TOOL = REPO_ROOT / "tools/flash.ps1"
A1_A2_TOOL = REPO_ROOT / "tools/verify_companion_type_a1_a2.ps1"
UUID_TABLE = REPO_ROOT / "docs/ble_uuid_table.json"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
TYPE_AUDIO_GENERATED = LISTENER_TYPE_ROOT / "third_party/denzic-platform/audio/host/rust/src/generated.rs"
TYPE_LIB = LISTENER_TYPE_ROOT / "src-tauri/src/lib.rs"
TYPE_BLE = LISTENER_TYPE_ROOT / "src-tauri/src/embedded_ble.rs"
TYPE_IPC = LISTENER_TYPE_ROOT / "src/lib/ipc.ts"
TYPE_COMMANDS = LISTENER_TYPE_ROOT / "src-tauri/src/commands.rs"
TYPE_DICTATION = LISTENER_TYPE_ROOT / "src-tauri/src/coordinator/dictation.rs"
TYPE_DEVICE_SECTION = LISTENER_TYPE_ROOT / "src/pages/settings/DeviceSection.tsx"
TYPE_SETTINGS_PAGE = LISTENER_TYPE_ROOT / "src/pages/Settings.tsx"
LISTENER_PROTO = LISTENER_FIRMWARE_ROOT / "protocols/listener_proto/include/listener_audio_proto.h"
LISTENER_PLATFORM_AUDIO = LISTENER_FIRMWARE_ROOT / "third_party/denzic-platform/audio/embedded/c/include/denzic_audio_v1_generated.h"

SERVICE_UUID = "710af845-6d9f-6583-0c4d-9e5b3bc3091a"
NOTIFY_UUID = "710af845-6d9f-6583-0c4d-9e5b3bc3091b"
READINESS_UUID = "710af845-6d9f-6583-0c4d-9e5b3bc3091c"
CAPABILITIES_UUID = "710af845-6d9f-6583-0c4d-9e5b3bc3091d"
CONTROL_UUID = "710af845-6d9f-6583-0c4d-9e5b3bc3091e"

PACKET_TYPES = {
    "SESSION_START": 1,
    "AUDIO_DATA": 2,
    "SESSION_STOP": 3,
    "SESSION_CANCEL": 4,
    "SESSION_ERROR": 5,
}
CONTROL_COMMANDS = (
    "TYPE:READY",
    "TYPE:READY:A1",
    "TYPE:READY:A2",
    "TYPE:HB",
    "TYPE:STOP",
    "TYPE:BYE",
    "VREC:TOGGLE",
    "VREC:STOP",
    "VREC:CANCEL",
    "VREC:PROCESSING:START",
    "VREC:PROCESSING:STOP",
    "VREC:PROCESSING:DONE",
    "VREC:PROCESSING:WARN",
)


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def macro_int(text: str, name: str) -> int | None:
    match = re.search(rf"#define\s+{re.escape(name)}\s+([0-9]+)u?", text)
    if not match:
        return None
    return int(match.group(1))


def rust_guid_literal(uuid: str) -> str:
    parts = uuid.split("-")
    if len(parts) != 5:
        raise ValueError(f"invalid UUID: {uuid}")
    return f"0x{parts[0]}_{parts[1]}_{parts[2]}_{parts[3]}_{parts[4]}"


def type_ble_contains_uuid(type_ble: str, uuid: str) -> bool:
    return uuid in type_ble or rust_guid_literal(uuid) in type_ble


def uuid_to_stm32_le(uuid: str) -> list[int]:
    compact = uuid.replace("-", "")
    raw = bytes.fromhex(compact)
    return list(reversed(raw))


def c_uint8_array(text: str, name: str) -> list[int] | None:
    match = re.search(
        rf"static\s+const\s+uint8_t\s+{re.escape(name)}\s*\[16\]\s*=\s*\{{(?P<body>.*?)\}};",
        text,
        re.DOTALL,
    )
    if not match:
        return None
    return [int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]{2})", match.group("body"))]


def check_companion_surface(header: str, source: str, errors: list[str]) -> None:
    for uuid in (SERVICE_UUID, NOTIFY_UUID, READINESS_UUID, CAPABILITIES_UUID, CONTROL_UUID):
        require(uuid in header, f"Companion audio_stream.h missing UUID {uuid}", errors)

    for token in (
        "COMP_AUDIO_STREAM_VKA1_MAGIC \"VKA1\"",
        "COMP_AUDIO_STREAM_VKA1_HEADER_BYTES 20u",
        "COMP_AUDIO_STREAM_PCM_SAMPLE_RATE_HZ 16000u",
        "COMP_AUDIO_STREAM_PCM_CHANNELS 1u",
        "COMP_AUDIO_STREAM_PCM_SAMPLE_WIDTH_BITS 16u",
        "COMP_AUDIO_STREAM_MAX_GATT_VALUE_BYTES 500u",
        "comp_audio_stream_build_vka1_packet",
        "comp_audio_stream_handle_control_write",
    ):
        require(token in header or token in source, f"Companion VKA1 bridge missing {token}", errors)

    for name, value in PACKET_TYPES.items():
        require(
            f"COMP_AUDIO_PACKET_{name} = {value}" in header,
            f"Companion packet type {name} does not match {value}",
            errors,
        )

    for command in CONTROL_COMMANDS:
        require(command in source, f"Companion control parser missing {command}", errors)

    forbidden = (
        "NimBLE",
        "BLEDevice",
        "esp_err_t",
        "aci_gatt_update_char_value",
        "HAL_",
    )
    for token in forbidden:
        require(token not in header and token not in source, f"portable audio_stream uses forbidden dependency {token}", errors)


def check_stm32wb_adapter(header: str, source: str, errors: list[str]) -> None:
    required_header_tokens = (
        "COMP_AUDIO_STREAM_STM32WB_GATT_VALUE_BYTES 248u",
        "COMP_AUDIO_STREAM_STM32WB_CONTROL_VALUE_BYTES 64u",
        "COMP_AUDIO_STREAM_STM32WB_READINESS_VALUE_BYTES 96u",
        "COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_VALUE_BYTES 96u",
        "comp_audio_stream_stm32wb_default_config",
        "comp_audio_stream_stm32wb_init",
        "comp_audio_stream_stm32wb_notify",
        "comp_audio_stream_stm32wb_update_readiness",
        "comp_audio_stream_stm32wb_update_capabilities",
        "comp_audio_stream_stm32wb_app_notification",
    )
    for token in required_header_tokens:
        require(token in header, f"STM32WB adapter header missing {token}", errors)

    required_source_tokens = (
        "common_blesvc.h",
        "PLACE_IN_SECTION(\"BLE_DRIVER_CONTEXT\")",
        "COMP_AUDIO_STREAM_STM32WB_NOTIFY_CCCD_OFFSET 2u",
        "COMP_AUDIO_STREAM_STM32WB_VALUE_HANDLE_OFFSET 1u",
        "COMP_AUDIO_STREAM_STM32WB_SERVICE_ATTRIBUTE_RECORDS (1u + 3u + 2u + 2u + 2u)",
        "SVCCTL_RegisterSvcHandler",
        "ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE",
        "COMSVC_Notification",
        "comp_audio_stream_set_notify_enabled",
        "comp_audio_stream_handle_control_write",
        "aci_gatt_add_service",
        "aci_gatt_add_char",
        "aci_gatt_update_char_value",
        "GATT_NOTIFY_ATTRIBUTE_WRITE",
        "GATT_DONT_NOTIFY_EVENTS",
        "CHAR_PROP_NOTIFY",
        "CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP",
        "CHAR_PROP_READ",
        "COMP_AUDIO_STREAM_STM32WB_GATT_VALUE_BYTES",
        "gatt_value=248",
        "sample_rate=16000",
    )
    for token in required_source_tokens:
        require(token in source, f"STM32WB adapter source missing {token}", errors)

    forbidden_source_tokens = (
        "COMP_AUDIO_STREAM_MAX_GATT_VALUE_BYTES",
        "ACI_GATT_WRITE_PERMIT_REQ_VSEVT_CODE",
        "aci_gatt_write_resp",
        "NimBLE",
        "BLEDevice",
        "esp_err_t",
    )
    for token in forbidden_source_tokens:
        require(token not in source, f"STM32WB adapter should not contain {token}", errors)

    arrays = {
        "COMP_AUDIO_STREAM_STM32WB_SERVICE_UUID": SERVICE_UUID,
        "COMP_AUDIO_STREAM_STM32WB_NOTIFY_UUID": NOTIFY_UUID,
        "COMP_AUDIO_STREAM_STM32WB_READINESS_UUID": READINESS_UUID,
        "COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_UUID": CAPABILITIES_UUID,
        "COMP_AUDIO_STREAM_STM32WB_CONTROL_UUID": CONTROL_UUID,
    }
    for name, uuid in arrays.items():
        actual = c_uint8_array(source, name)
        require(actual is not None, f"STM32WB adapter missing UUID array {name}", errors)
        if actual is not None:
            require(actual == uuid_to_stm32_le(uuid), f"STM32WB adapter UUID array {name} is not ST little-endian {uuid}", errors)


def check_type_contract(type_audio_generated: str, type_lib: str, type_ble: str, errors: list[str]) -> None:
    require("denzic_audio_v1_core as embedded_audio" in type_lib, "Type must re-export the Denzic audio v1 core", errors)
    require('pub const MAGIC: &[u8; 4] = b"VKA1";' in type_audio_generated, "Type MAGIC is not VKA1", errors)
    require("pub const HEADER_LEN: usize = 20;" in type_audio_generated, "Type HEADER_LEN is not 20", errors)
    require("pub const PCM_SAMPLE_RATE_HZ: u32 = 16000;" in type_audio_generated, "Type sample rate is not 16 kHz", errors)
    require("pub const PCM_CHANNELS: u16 = 1;" in type_audio_generated, "Type channel count is not mono", errors)
    require("pub const PCM_SAMPLE_WIDTH_BITS: u16 = 16;" in type_audio_generated, "Type PCM width is not 16 bit", errors)

    for packet_name, value in PACKET_TYPES.items():
        rust_name = f"PACKET_TYPE_{packet_name}"
        require(
            re.search(rf"pub const {rust_name}: u8 = {value};", type_audio_generated) is not None,
            f"Type packet {rust_name} does not map to {value}",
            errors,
        )

    for uuid in (SERVICE_UUID, NOTIFY_UUID, CONTROL_UUID, READINESS_UUID, CAPABILITIES_UUID):
        require(type_ble_contains_uuid(type_ble, uuid), f"Type BLE constants missing UUID {uuid}", errors)

    for command in ("TYPE:READY", "TYPE:HB", "VREC:TOGGLE", "VREC:STOP", "VREC:CANCEL"):
        require(command in type_ble, f"Type BLE code missing control command {command}", errors)
    require(
        "LISTENER_TYPE_EMBEDDED_BLE_READY_COMMAND" in type_ble,
        "Type BLE code missing configurable ready-command hook for TYPE:READY:A1/A2",
        errors,
    )


def check_type_host_runtime_contract(
    type_ipc: str,
    type_commands: str,
    type_dictation: str,
    type_device_section: str,
    settings_page: str,
    errors: list[str],
) -> None:
    for token in (
        "probeEmbeddedAudioBleSubscription",
        "'probe_embedded_audio_ble_subscription'",
        "submitEmbeddedAudioBleOnce",
        "'submit_embedded_audio_ble_once'",
    ):
        require(token in type_ipc, f"Type IPC missing embedded BLE audio token {token}", errors)

    for token in (
        "pub async fn probe_embedded_audio_ble_subscription",
        ".probe_embedded_audio_ble_subscription(timeout_ms)",
        "pub async fn submit_embedded_audio_ble_stream",
        "coord.submit_embedded_audio_ble_stream(timeout_ms).await",
    ):
        require(token in type_commands, f"Type command surface missing {token}", errors)

    for token in (
        "pub(super) async fn submit_embedded_audio_ble_stream",
        "submit_embedded_audio_ble_stream_impl",
        "capture_notification_events_until_cancelled",
        "EmbeddedBleStreamSignal::Ready",
        "EmbeddedBleStreamSignal::Notification",
        "terminal_received",
        "missing_packet_count",
        "reconstructed_pcm_bytes",
    ):
        require(token in type_dictation, f"Type streaming implementation missing {token}", errors)

    require(
        type_commands.find("pub async fn submit_embedded_audio_ble_stream") >
        type_commands.find("pub async fn submit_embedded_audio_ble_once"),
        "Type command surface should expose the stream command in addition to the legacy one-shot BLE audio command",
        errors,
    )

    for token in (
        "getEmbeddedBleRuntimeStatus",
        "FirmwareOtaPanel",
        "settings.device",
        "DeviceSection",
    ):
        require(token in type_device_section, f"Type device settings page missing {token}", errors)

    require(
        "section === 'device' && <DeviceSection />" in settings_page,
        "Type Settings page no longer renders DeviceSection for the hardware section",
        errors,
    )


def check_listener_firmware_contract(listener_proto: str, platform_audio: str, errors: list[str]) -> None:
    require('#include "denzic_audio_v1_generated.h"' in listener_proto, "Listener firmware must include Denzic audio v1 generated protocol", errors)
    require("#define LISTENER_AUDIO_PROTO_MAGIC DENZIC_AUDIO_V1_MAGIC" in listener_proto, "Listener firmware magic alias drifted", errors)
    require("#define LISTENER_AUDIO_PROTO_HEADER_BYTES DENZIC_AUDIO_V1_HEADER_BYTES" in listener_proto, "Listener firmware header-length alias drifted", errors)
    require('#define DENZIC_AUDIO_V1_MAGIC "VKA1"' in platform_audio, "Listener firmware magic is not VKA1", errors)
    require("#define DENZIC_AUDIO_V1_HEADER_BYTES (20u)" in platform_audio, "Listener firmware header length is not 20", errors)
    for name, value in PACKET_TYPES.items():
        listener_name = f"LISTENER_AUDIO_PACKET_TYPE_{name}"
        platform_name = f"DENZIC_AUDIO_V1_PACKET_TYPE_{name}"
        require(
            f"#define {listener_name} {platform_name}" in listener_proto,
            f"Listener firmware packet alias {listener_name} drifted",
            errors,
        )
        require(
            re.search(rf"{platform_name}\s*=\s*{value}\b", platform_audio) is not None,
            f"Listener firmware packet {platform_name} does not match {value}",
            errors,
        )


def check_uuid_table(errors: list[str]) -> None:
    data: dict[str, Any] = json.loads(read(UUID_TABLE))
    compat_services = data.get("compatibility_services", [])
    require(isinstance(compat_services, list), "ble_uuid_table.json missing compatibility_services list", errors)
    if not isinstance(compat_services, list):
        return
    service = next((item for item in compat_services if item.get("service") == "listener_vka1_audio_stream"), None)
    require(isinstance(service, dict), "UUID table missing listener_vka1_audio_stream compatibility service", errors)
    if not isinstance(service, dict):
        return
    require(service.get("uuid") == SERVICE_UUID, "compatibility service UUID mismatch", errors)
    chars = {item.get("name"): item.get("uuid") for item in service.get("characteristics", []) if isinstance(item, dict)}
    expected = {
        "listener_vka1_audio_notify": NOTIFY_UUID,
        "listener_vka1_audio_readiness": READINESS_UUID,
        "listener_vka1_audio_capabilities": CAPABILITIES_UUID,
        "listener_vka1_audio_control": CONTROL_UUID,
    }
    for name, uuid in expected.items():
        require(chars.get(name) == uuid, f"compatibility char {name} UUID mismatch", errors)


def check_docs(errors: list[str]) -> None:
    contract = read(BLE_CONTRACT)
    bringup = read(REPO_ROOT / "docs/bringup_steps.md")
    for token in (
        "Listener-Compatible Live Audio",
        "VKA1",
        "audio_stream_stm32wb.c",
        "248-byte notify value",
        SERVICE_UUID,
        NOTIFY_UUID,
        CONTROL_UUID,
        "TYPE:READY",
        "TYPE:READY:A1",
        "TYPE:READY:A2",
        "VREC:TOGGLE",
    ):
        require(token in contract, f"BLE contract missing Listener-compatible audio token {token}", errors)
    for token in (
        "tools\\verify_companion_type_a1_a2.ps1",
        "A1 as six short",
        "--submit-embedded-audio-ble-stream 45000",
        "--submit-embedded-audio-ble-stream 120000",
        "16 kHz mono Chinese TTS WAV fixtures",
        "TYPE:READY:A1",
    ):
        require(token in bringup, f"bringup steps missing A1/A2 validation token {token}", errors)


def check_type_a1_a2_validation_tool(errors: list[str]) -> None:
    tool = read(A1_A2_TOOL)
    for token in (
        "[int] $ProbeTimeoutMs = 30000",
        "[int] $A1TimeoutMs = 45000",
        "[int] $A1Rounds = 6",
        "[int] $A2TimeoutMs = 120000",
        "[switch] $WorkflowLockHeld",
        "Show-OperatorPrompt",
        "[System.Media.SystemSounds]::Exclamation.Play()",
        "[Console]::Beep(880, 220)",
        "Companion A1/A2 验证即将开始",
        "New-TtsWav",
        "Start-WavPlaybackOnce",
        "$player.PlaySync()",
        '[ValidateSet("wav", "speech")]',
        "Invoke-TtsPlaybackSync",
        "TYPE:READY:A1",
        "--probe-embedded-audio-ble-subscription",
        "--submit-embedded-audio-ble-stream",
        "Companion-WB55,BLE-Companion",
        "companion.type_a1_a2.validation.v1",
        "expected_text",
        "Refusing to run Companion A1/A2 hardware validation without -WorkflowLockHeld.",
    ):
        require(token in tool, f"verify_companion_type_a1_a2.ps1 missing {token}", errors)


def check_stm32wb_unified_bringup_app(errors: list[str]) -> None:
    app_conf = read(BRINGUP_APP_CONF)
    app_ble = read(BRINGUP_APP_BLE)
    main_c = read(BRINGUP_MAIN)
    makefile = read(BRINGUP_MAKEFILE)
    flash_tool = read(FLASH_TOOL)
    for token in (
        "#include_next \"app_conf.h\"",
        "#define CFG_BLE_MAX_ATT_MTU (251)",
    ):
        require(token in app_conf, f"NUCLEO bringup app_conf.h missing {token}", errors)

    for token in (
        "Companion_Nucleo_WB55RG_Bringup",
        "Core/Src/app_ble.c",
        "$(P2P)/Core/Src/app_entry.c",
        "$(ROOT)/app/companion_pendant/audio_stream",
        "$(ROOT)/app/companion_pendant/audio_stream/audio_stream.c",
        "$(ROOT)/app/companion_pendant/audio_stream/audio_stream_stm32wb.c",
        "SYSTEM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/Core/Src/system_stm32wbxx.c",
        "$(BUILD_DIR)/system_stm32wbxx.o: $(SYSTEM_SOURCE) | $(BUILD_DIR)",
    ):
        require(token in makefile, f"NUCLEO bringup Makefile missing {token}", errors)

    for token in (
        '#define COMPANION_BLE_PRODUCT_NAME "companion"',
        "#define COMPANION_BLE_IO_CAPABILITY CFG_IO_CAPABILITY_NO_INPUT_NO_OUTPUT",
        "#define COMPANION_BLE_BONDING_MODE 0",
        "#define COMPANION_BLE_MITM_PROTECTION 0",
        "#define COMPANION_BLE_ADDRESS_OFFSET 0u",
        "0x01 /* Companion app */",
        "source=mic",
        "ready:listener_vka1 app=companion",
        "Companion_App_HandleBleControl",
        "comp_audio_stream_stm32wb_default_config",
        "comp_audio_stream_stm32wb_init",
        "comp_audio_stream_send_session_start",
        "comp_audio_stream_send_session_audio",
        "comp_audio_stream_send_session_stop",
        "COMP_AUDIO_CONTROL_RECORDING_TOGGLE",
        "APP_BLE_Key_Button1_Action",
        "Companion_BleAudio_SendSessionStart",
        "Companion_BleAudio_SendPcmBytes",
        "Companion_BleAudio_RequestActiveLink",
        "Companion_BleAudio_RequestIdleLink",
        "aci_l2cap_connection_parameter_update_req",
        "hci_le_set_phy",
        "COMPANION_BLE_LINK_ACTIVE_INTERVAL_MIN 0x0006u",
        "COMPANION_BLE_LINK_IDLE_INTERVAL_MIN 0x0050u",
        "audio high-speed link deferred until active recording",
        "comp_audio_stream_set_notify_enabled(&s_companion_audio_stream, false)",
    ):
        require(token in app_ble, f"NUCLEO bringup app_ble missing {token}", errors)

    for token in (
        "Companion_App_HandleBleControl",
        "COMPANION_TYPE_READY_A2_AUTOSTREAM_PCM_BYTES 320u",
        "COMP_AUDIO_CONTROL_TYPE_READY",
        "start_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL",
        "Companion_BleAudio_SendPcmBytes",
        "Companion_BleAudio_RequestActiveLink(reason)",
        "Companion_BleAudio_RequestIdleLink(reason)",
        'Companion_BleAudio_RequestIdleLink("mic_capture_failed")',
        "capture_microphone_block",
        "MX_APPE_Init",
        "MX_APPE_Process",
        "ble=companion_vka1",
    ):
        require(token in main_c, f"NUCLEO bringup main.c missing {token}", errors)

    for forbidden in (
        "Audio_Fixture_Init",
        "Audio_Fixture_StartOrDeferSyntheticSession",
        "COMPANION_AUDIO_FIXTURE_AUTOSTART_ON_TYPE_READY",
        "COMPANION_AUDIO_FIXTURE_PACKET_COUNT",
        "Delete_Sectors",
        "FD_EraseSectors",
        "OTAS_STM_Init",
        "otas_stm.h",
    ):
        require(forbidden not in app_ble and forbidden not in main_c and forbidden not in makefile, f"NUCLEO bringup app must not contain {forbidden}", errors)

    for token in (
        "[switch] $FlashNucleoBringup",
        "Companion_Nucleo_WB55RG_Bringup.hex",
        "flash Companion NUCLEO bring-up",
        "Companion NUCLEO bring-up image",
        "Show-OperatorPrompt",
    ):
        require(token in flash_tool, f"flash.ps1 missing NUCLEO bringup flash token {token}", errors)


def build_fixture_packets(payload_size: int = 133, packet_count: int = 12) -> list[bytes]:
    pcm = bytes((index * 17) & 0xFF for index in range(payload_size * packet_count))
    packets: list[bytes] = []

    def packet(packet_type: int, session_id: int, sequence_or_count: int, payload: bytes, pcm_bytes: int) -> bytes:
        header = bytearray()
        header += b"VKA1"
        header += bytes([packet_type, 0])
        header += (20).to_bytes(2, "little")
        header += session_id.to_bytes(4, "little")
        header += sequence_or_count.to_bytes(2, "little")
        header += bytes([0, 1])
        header += len(payload).to_bytes(2, "little")
        header += pcm_bytes.to_bytes(2, "little")
        return bytes(header + payload)

    packets.append(packet(PACKET_TYPES["SESSION_START"], 7, 0, b"", 0))
    for seq, offset in enumerate(range(0, len(pcm), payload_size)):
        chunk = pcm[offset : offset + payload_size]
        packets.append(packet(PACKET_TYPES["AUDIO_DATA"], 7, seq, chunk, len(chunk)))
    packets.append(packet(PACKET_TYPES["SESSION_STOP"], 7, len(packets) - 1, b"", 0))
    return packets


def check_fixture_model(errors: list[str]) -> None:
    packets = build_fixture_packets()
    require(len(packets) == 14, "fixture should produce start + 12 audio + stop packets", errors)
    require(packets[0][:20].hex() == "564b413101001400070000000000000100000000", "fixture session_start header drifted", errors)
    require(packets[1][4] == PACKET_TYPES["AUDIO_DATA"], "fixture first audio packet type drifted", errors)
    require(int.from_bytes(packets[1][12:14], "little") == 0, "fixture first audio sequence drifted", errors)
    require(int.from_bytes(packets[-1][12:14], "little") == 12, "fixture stop expected_packet_count drifted", errors)


def main() -> int:
    errors: list[str] = []
    try:
        header = read(HEADER)
        source = read(SOURCE)
        check_companion_surface(header, source, errors)
        check_stm32wb_adapter(read(STM32WB_HEADER), read(STM32WB_SOURCE), errors)
        check_type_contract(read(TYPE_AUDIO_GENERATED), read(TYPE_LIB), read(TYPE_BLE), errors)
        check_type_host_runtime_contract(
            read(TYPE_IPC),
            read(TYPE_COMMANDS),
            read(TYPE_DICTATION),
            read(TYPE_DEVICE_SECTION),
            read(TYPE_SETTINGS_PAGE),
            errors,
        )
        check_listener_firmware_contract(read(LISTENER_PROTO), read(LISTENER_PLATFORM_AUDIO), errors)
        check_uuid_table(errors)
        check_docs(errors)
        check_type_a1_a2_validation_tool(errors)
        check_stm32wb_unified_bringup_app(errors)
        check_fixture_model(errors)
    except Exception as exc:  # noqa: BLE001 - compact verifier output.
        print(f"FAIL: Companion Listener VKA1 static check crashed: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("FAIL: Companion Listener VKA1 static check failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print("PASS: Companion Listener-compatible VKA1 audio bridge matches Type and Listener firmware contracts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
