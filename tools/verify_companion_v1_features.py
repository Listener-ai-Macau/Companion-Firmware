#!/usr/bin/env python3
"""Static checks for Companion V1 feature contracts."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE = REPO_ROOT / "docs" / "ble_uuid_table.json"
GATT_HEADER = REPO_ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.h"
GATT_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.c"
V1_HEADER = REPO_ROOT / "app" / "companion_pendant" / "v1_features" / "companion_v1_features.h"
V1_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "v1_features" / "companion_v1_features.c"
DIAG_EVENTS = REPO_ROOT / "app" / "companion_pendant" / "diag_log" / "diag_log_events.h"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
APP_CONF = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "app_conf.h"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
FIXTURE = REPO_ROOT / "tools" / "companion_v1_feature_fixture.py"
REAL_BENCH = REPO_ROOT / "tools" / "companion_ble_real_bench.py"

REQUIRED_CHARS = {
    "ble_name_config": "BleNameConfigV1",
    "meeting_control": "MeetingControlV1",
    "meeting_status": "MeetingStatusV1",
    "imu_status": "ImuStatusV1",
    "speaker_control": "SpeakerControlV1",
    "speaker_status": "SpeakerStatusV1",
    "wake_word_control": "WakeWordControlV1",
    "wake_word_status": "WakeWordStatusV1",
}

REQUIRED_DIAG_ANCHORS = {
    "meeting.start",
    "meeting.stop",
    "meeting.finalize",
    "meeting.rejected",
    "imu.sample",
    "imu.motion",
    "imu.unavailable",
    "speaker.prompt",
    "speaker.result",
    "speaker.rejected",
    "wake_word.armed",
    "wake_word.detected",
    "wake_word.disabled",
    "wake_word.rejected",
    "device_settings.ble_name.accepted",
    "device_settings.ble_name.rejected",
    "device_settings.ble_name.applied",
}


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


def parser_name(payload: str) -> str:
    table = {
        "BleNameConfigV1": "companion_gatt_parse_ble_name_config_v1",
        "MeetingControlV1": "companion_gatt_parse_meeting_control_v1",
        "MeetingStatusV1": "companion_gatt_parse_meeting_status_v1",
        "ImuStatusV1": "companion_gatt_parse_imu_status_v1",
        "SpeakerControlV1": "companion_gatt_parse_speaker_control_v1",
        "SpeakerStatusV1": "companion_gatt_parse_speaker_status_v1",
        "WakeWordControlV1": "companion_gatt_parse_wake_word_control_v1",
        "WakeWordStatusV1": "companion_gatt_parse_wake_word_status_v1",
    }
    return table[payload]


def struct_name(payload: str) -> str:
    table = {
        "BleNameConfigV1": "companion_gatt_ble_name_config_v1_t",
        "MeetingControlV1": "companion_gatt_meeting_control_v1_t",
        "MeetingStatusV1": "companion_gatt_meeting_status_v1_t",
        "ImuStatusV1": "companion_gatt_imu_status_v1_t",
        "SpeakerControlV1": "companion_gatt_speaker_control_v1_t",
        "SpeakerStatusV1": "companion_gatt_speaker_status_v1_t",
        "WakeWordControlV1": "companion_gatt_wake_word_control_v1_t",
        "WakeWordStatusV1": "companion_gatt_wake_word_status_v1_t",
    }
    return table[payload]


def check_uuid_and_gatt(errors: list[str]) -> None:
    table = json.loads(read(UUID_TABLE))
    chars: dict[str, dict[str, Any]] = {}
    services = {str(service["service"]) for service in table["services"]}
    for service in table["services"]:
        for characteristic in service["characteristics"]:
            chars[str(characteristic["name"])] = characteristic
    for service in {"meeting", "sensors", "audio_output", "settings"}:
        require(service in services, f"missing service {service}", errors)

    header = read(GATT_HEADER)
    source = read(GATT_SOURCE)
    for name, payload in REQUIRED_CHARS.items():
        require(name in chars, f"missing UUID-table characteristic {name}", errors)
        require(chars.get(name, {}).get("payload") == payload, f"{name} payload mismatch", errors)
        require("COMPANION_GATT_CHAR_" + name.upper() in header, f"missing enum for {name}", errors)
        require(struct_name(payload) in header, f"missing struct for {payload}", errors)
        require(parser_name(payload) in header and parser_name(payload) in source, f"missing parser for {payload}", errors)
        require(f'"{name}"' in source, f"missing runtime char name {name}", errors)

    for prefix in ["0x4002u", "0x8001u", "0x8002u", "0x9001u", "0xa001u", "0xa004u"]:
        require(prefix in source.lower(), f"missing GATT UUID prefix {prefix}", errors)


def check_v1_module(errors: list[str]) -> None:
    header = read(V1_HEADER)
    source = read(V1_SOURCE)
    makefile = read(MAKEFILE)
    for token in [
        "COMPANION_V1_DEFAULT_BLE_NAME",
        "companion_v1_features_init",
        "companion_v1_apply_meeting_control",
        "companion_v1_apply_speaker_control",
        "companion_v1_apply_wake_word_control",
        "companion_v1_apply_ble_name_config",
        "companion_v1_ble_name_is_valid",
    ]:
        require(token in header and token in source, f"missing V1 module token {token}", errors)
    for token in ['ch == \'"\'', "ch == '\\''", "ch == ';'", "ch == '='", "ch == '\\\\'"]:
        require(token in source, f"BLE name policy missing check {token}", errors)
    require("COMPANION_V1_DEFAULT_BLE_NAME \"companion\"" in header, "default Companion BLE name missing", errors)
    require("$(ROOT)/app/companion_pendant/v1_features" in makefile, "Makefile missing V1 include path", errors)
    require(
        "$(ROOT)/app/companion_pendant/v1_features/companion_v1_features.c" in makefile,
        "Makefile missing V1 source",
        errors,
    )


def check_app_ble(errors: list[str]) -> None:
    app_ble = read(APP_BLE)
    for token in [
        '#include "companion_v1_features.h"',
        "companion_v1_features_init",
        "companion_gatt_parse_ble_name_config_v1",
        "companion_gatt_parse_meeting_control_v1",
        "companion_gatt_parse_speaker_control_v1",
        "companion_gatt_parse_wake_word_control_v1",
        "Companion_Gatt_PublishBleNameConfig",
        "Companion_Gatt_PublishMeetingStatus",
        "Companion_Gatt_PublishImuStatus",
        "Companion_Gatt_PublishSpeakerStatus",
        "Companion_Gatt_PublishWakeWordStatus",
    ]:
        require(token in app_ble, f"app_ble.c missing {token}", errors)

    handler_start = app_ble.find("static void Companion_Gatt_HandleEvent")
    handler_end = app_ble.find("static void Companion_Gatt_PublishInitialState")
    require(handler_start >= 0 and handler_end > handler_start, "missing Companion GATT handler body", errors)
    if handler_start >= 0 and handler_end > handler_start:
        body = app_ble[handler_start:handler_end]
        for forbidden in ["HAL_QSPI", "BSP_AUDIO", "microphone_start", "imu_read", "speaker_play"]:
            require(forbidden not in body, f"GATT handler must not block on hardware IO: {forbidden}", errors)


def check_diag_and_capacity(errors: list[str]) -> None:
    diag = read(DIAG_EVENTS)
    for anchor in REQUIRED_DIAG_ANCHORS:
        require(anchor in diag, f"missing diag anchor {anchor}", errors)
    app_conf = read(APP_CONF)
    require("#define CFG_BLE_NUM_GATT_SERVICES 16" in app_conf, "GATT service count not raised for V1 services", errors)
    require("#define CFG_BLE_NUM_GATT_ATTRIBUTES 96" in app_conf, "GATT attr count not raised for V1 services", errors)
    require("CFG_BLE_ATT_VALUE_ARRAY_SIZE (4096)" in app_conf, "ATT value array not raised for V1 services", errors)


def check_fixture(errors: list[str]) -> None:
    spec = importlib.util.spec_from_file_location("companion_v1_feature_fixture", FIXTURE)
    require(spec is not None and spec.loader is not None, "cannot load V1 fixture module", errors)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    matrix = module.build_matrix()
    module.validate_matrix(matrix)
    features = {item["feature"] for item in matrix["features"]}
    require(features == {"meeting_recording", "imu", "speaker", "voice_wake", "ble_name_config"}, "fixture feature set mismatch", errors)
    require(matrix["ble_name_policy"]["valid_example_passed"] is True, "fixture valid BLE name failed", errors)
    require(
        all(not item["accepted"] for item in matrix["ble_name_policy"]["invalid_examples"]),
        "fixture accepted an invalid BLE name",
        errors,
    )


def check_real_bench(errors: list[str]) -> None:
    bench = read(REAL_BENCH)
    for token in [
        "parse_ble_name_config",
        "parse_meeting_status",
        "parse_imu_status",
        "parse_speaker_status",
        "parse_wake_word_status",
        '"operation": "ble_name_config"',
        '"operation": "meeting_control"',
        '"operation": "imu_status"',
        '"operation": "speaker_control"',
        '"operation": "wake_word_control"',
        "wake detect while disarmed",
        "BLE name reset did not restore default name",
    ]:
        require(token in bench, f"real BLE bench missing V1 coverage token {token}", errors)


def check_forbidden_diff(errors: list[str]) -> None:
    changed_third_party = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB").strip()
    require(not changed_third_party, f"third_party/STM32CubeWB modified: {changed_third_party}", errors)


def main() -> int:
    errors: list[str] = []
    for path in [UUID_TABLE, GATT_HEADER, GATT_SOURCE, V1_HEADER, V1_SOURCE, DIAG_EVENTS, APP_BLE, APP_CONF, MAKEFILE, FIXTURE, REAL_BENCH]:
        require(path.exists(), f"missing required path {path.relative_to(REPO_ROOT)}", errors)
    if not errors:
        check_uuid_and_gatt(errors)
        check_v1_module(errors)
        check_app_ble(errors)
        check_diag_and_capacity(errors)
        check_fixture(errors)
        check_real_bench(errors)
        check_forbidden_diff(errors)
    if errors:
        print("FAIL: Companion V1 feature static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion V1 feature contracts, state models, diagnostics, and fixture checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
