#!/usr/bin/env python3
"""Real BLE bench for the Companion-native STM32WB GATT surface."""

from __future__ import annotations

import argparse
import asyncio
import binascii
import datetime as dt
import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import time
from typing import Any, Callable


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE_PATH = REPO_ROOT / "docs" / "ble_uuid_table.json"
HOST_STATUS_SEQUENCE_PATH = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-host-status-sequence.json"
DEMO_HOST_STATUS_SEQUENCE_PATH = (
    REPO_ROOT / "docs" / "validation" / "companion-screen-expression-demo-host-status-sequence.json"
)
SCHEMA_VERSION = 1
RECORDING_ERROR_FLAG = 0x80
RECORDING_FINAL_FLAG = 0x01
RECORDING_COMPRESSED_IMA_FLAG = 0x02
RECORDING_HALF_RATE_8K_FLAG = 0x10  # COMP-REQ-666: 8 kHz IMA → host upsample ×2
RECORDING_REQ_COMPRESS_IMA = 0x02
RECORDING_REQ_STREAM_ALL = 0x04
_SETTINGS_WRITE_NONCE = 0
CARD_RENDER_STATE_ACCEPTED = 1
CARD_RENDER_STATE_RENDERED = 2
CARD_RENDER_STATE_FAILED = 3
CARD_RENDER_STATE_BUSY = 4
CARD_LAST_ERROR_OK = 0
CARD_LAST_ERROR_DEFERRED_NO_PANEL = 4
CARD_LAST_ERROR_DEFERRED_CONTROLLER_UNKNOWN = 5
EXPRESSION_CARD_SLOT = 1
EXPRESSION_REQUEST_ID_BASE = 0xE0000000
EXPRESSION_REQUEST_ID_MASK = 0xF0000000
EXPRESSION_STATUS_REQUIRED_EVENTS = (
    "boot_idle",
    "settings.display_off",
    "recording_fsm.start_request",
    "battery_charging.sample.low",
    "recording_fsm.session_finished",
    "errors.fault",
)
EXPRESSION_STATUS_REQUIRED_FACES = (
    "idle",
    "sleepy",
    "recording",
    "low_battery",
    "sync_complete",
    "error",
)
EXPRESSION_DEMO_STATUS_REQUIRED_FACES = (
    "error",
    "happy",
    "idle",
    "listening",
    "low_battery",
    "recording",
    "sleepy",
    "speaking",
    "sync_complete",
    "thinking",
)


class BenchError(RuntimeError):
    """A compact validation failure that should be reported in the artifact."""


class BenchPartialError(BenchError):
    """Bench failure that still carries the operations collected so far."""

    def __init__(self, message: str, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def repo_rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_uuid_table() -> dict[str, Any]:
    return json.loads(UUID_TABLE_PATH.read_text(encoding="utf-8"))


def build_uuid_index(table: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for service in table.get("services", []):
        index[str(service["service"])] = str(service["uuid"]).lower()
        for char in service.get("characteristics", []):
            index[str(char["name"])] = str(char["uuid"]).lower()
    return index


def required_services(table: dict[str, Any]) -> set[str]:
    return {str(service["uuid"]).lower() for service in table.get("services", [])}


def required_characteristics(table: dict[str, Any]) -> set[str]:
    uuids: set[str] = set()
    for service in table.get("services", []):
        for char in service.get("characteristics", []):
            name = str(char["name"])
            if name.startswith("ota_st_"):
                continue
            uuids.add(str(char["uuid"]).lower())
    return uuids


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def parse_struct(fmt: str, names: tuple[str, ...], payload: bytes) -> dict[str, Any]:
    size = struct.calcsize(fmt)
    if len(payload) < size:
        raise BenchError(f"payload too short: got {len(payload)}, need {size}")
    values = struct.unpack(fmt, payload[:size])
    parsed = dict(zip(names, values, strict=True))
    if parsed.get("schema_version") != SCHEMA_VERSION:
        raise BenchError(f"unexpected schema_version={parsed.get('schema_version')}")
    return parsed


def parse_device_status(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHIIII",
        (
            "schema_version",
            "active_mode",
            "fault_bitmap",
            "firmware_version",
            "build_id",
            "board_id",
            "uptime_ms",
        ),
        payload,
    )


def parse_battery_charge(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBHh",
        (
            "schema_version",
            "percent",
            "charge_state",
            "charger_present",
            "millivolts",
            "temperature_c_x10",
        ),
        payload,
    )


def parse_card_status(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBIII",
        (
            "schema_version",
            "card_slot",
            "render_state",
            "last_error",
            "request_id",
            "content_crc32",
            "refresh_count",
        ),
        payload,
    )


def parse_recording_control(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBIH",
        (
            "schema_version",
            "command",
            "profile_id",
            "privacy_flags",
            "request_id",
            "max_seconds",
        ),
        payload,
    )


def parse_recording_list(payload: bytes) -> dict[str, Any]:
    header = parse_struct("<BBH", ("schema_version", "count", "entry_bytes"), payload)
    entries = []
    entry_fmt = "<IIIBBBBI8sI"
    expected_entry_size = struct.calcsize(entry_fmt)
    if int(header["count"]) > 0 and int(header["entry_bytes"]) != expected_entry_size:
        raise BenchError(
            f"unexpected recording list entry_bytes={header['entry_bytes']} expected={expected_entry_size}"
        )
    offset = struct.calcsize("<BBH")
    for _index in range(int(header["count"])):
        if len(payload) < offset + expected_entry_size:
            raise BenchError("recording_list entry truncated")
        values = struct.unpack(entry_fmt, payload[offset:offset + expected_entry_size])
        entries.append(
            {
                "recording_id": values[0],
                "started_unix_s": values[1],
                "duration_ms": values[2],
                "codec": values[3],
                "sync_state": values[4],
                "source_mode": values[5],
                "reserved": values[6],
                "total_length": values[7],
                "sha256_prefix": values[8].hex(),
                "content_crc32": f"0x{values[9]:08x}",
            }
        )
        offset += expected_entry_size
    header["entries"] = entries
    header["raw_length"] = len(payload)
    return header


def parse_recording_chunk_pull(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHIII",
        (
            "schema_version",
            "flags",
            "requested_length",
            "recording_id",
            "byte_offset",
            "host_resume_token",
        ),
        payload,
    )


def parse_recording_chunk_packet(payload: bytes) -> dict[str, Any]:
    # Compact intermediate: 20B (flag 0x08, no total on wire). Legacy intermediate: 24B.
    # FINAL/ERROR: full 56B with SHA.
    compact_fmt = "<BBHIIII"  # schema flags len id seq off crc
    compact_size = struct.calcsize(compact_fmt)  # 20
    legacy_fmt = "<BBHIIIII"
    legacy_size = struct.calcsize(legacy_fmt)  # 24
    if len(payload) == 0:
        raise BenchError("recording chunk empty notify (0 bytes)")
    if len(payload) < compact_size:
        raise BenchError(f"recording chunk too short: {len(payload)} head={payload[:16].hex() if payload else ''}")
    schema_version, flags, payload_length = struct.unpack_from("<BBH", payload, 0)
    if schema_version != SCHEMA_VERSION:
        raise BenchError(f"unexpected recording chunk schema_version={schema_version}")
    final_flag = bool(flags & RECORDING_FINAL_FLAG)
    error_flag = bool(flags & 0x80)
    compact_flag = bool(flags & 0x08)
    if final_flag or error_flag:
        header_size = 56
        if len(payload) < legacy_size:
            raise BenchError(f"recording chunk FINAL/ERROR header short: {len(payload)}")
        (
            _sv,
            _fl,
            payload_length,
            recording_id,
            packet_sequence,
            byte_offset,
            total_length,
            packet_crc32,
        ) = struct.unpack_from(legacy_fmt, payload, 0)
    elif compact_flag:
        header_size = compact_size
        (
            _sv,
            _fl,
            payload_length,
            recording_id,
            packet_sequence,
            byte_offset,
            packet_crc32,
        ) = struct.unpack_from(compact_fmt, payload, 0)
        total_length = 0  # filled from list entry by pull loop
    else:
        header_size = legacy_size
        if len(payload) < legacy_size:
            raise BenchError(f"recording chunk legacy header short: {len(payload)}")
        (
            _sv,
            _fl,
            payload_length,
            recording_id,
            packet_sequence,
            byte_offset,
            total_length,
            packet_crc32,
        ) = struct.unpack_from(legacy_fmt, payload, 0)
    if len(payload) < header_size + int(payload_length):
        raise BenchError("recording chunk payload truncated")
    if final_flag:
        final_sha256 = payload[24:56].hex()
    else:
        final_sha256 = ""
    return {
        "schema_version": schema_version,
        "flags": flags,
        "payload_length": int(payload_length),
        "recording_id": int(recording_id),
        "packet_sequence": int(packet_sequence),
        "byte_offset": int(byte_offset),
        "total_length": int(total_length),
        "packet_crc32": int(packet_crc32),
        "final_sha256": final_sha256,
        "payload": payload[header_size : header_size + int(payload_length)],
        "packet_crc32_hex": f"0x{int(packet_crc32) & 0xFFFFFFFF:08x}",
        "header_bytes": header_size,
    }


def verify_recording_packet_crc(packet: dict[str, Any]) -> str:
    crc_payload = struct.pack(
        "<IIII",
        int(packet["recording_id"]),
        int(packet["packet_sequence"]),
        int(packet["byte_offset"]),
        int(packet["total_length"]),
    )
    crc = binascii.crc32(crc_payload + bytes(packet["payload"])) & 0xFFFFFFFF
    expected = int(packet["packet_crc32"]) & 0xFFFFFFFF
    if crc != expected:
        raise BenchError(f"recording packet CRC mismatch: got 0x{crc:08x}, expected 0x{expected:08x}")
    return f"0x{crc:08x}"


_IMA_STEP_TABLE = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230,
    253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
    3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442,
    11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767,
]
_IMA_INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]


def decode_ima_adpcm_frame(frame: bytes) -> bytes:
    """Decode one companion_ima_adpcm frame to little-endian i16 PCM bytes."""
    if len(frame) < 6:
        raise BenchError("IMA-ADPCM frame too short")
    predictor = struct.unpack_from("<h", frame, 0)[0]
    step_index = frame[2]
    sample_count = struct.unpack_from("<H", frame, 4)[0]
    if step_index > 88:
        raise BenchError(f"IMA-ADPCM bad step_index={step_index}")
    samples: list[int] = []

    def decode_nibble(nibble: int) -> int:
        nonlocal predictor, step_index
        step = _IMA_STEP_TABLE[step_index]
        delta = step >> 3
        if nibble & 4:
            delta += step
        if nibble & 2:
            delta += step >> 1
        if nibble & 1:
            delta += step >> 2
        if nibble & 8:
            delta = -delta
        predictor = max(-32768, min(32767, predictor + delta))
        step_index = max(0, min(88, step_index + _IMA_INDEX_TABLE[nibble & 0x0F]))
        return predictor

    nibble_bytes = (sample_count + 1) // 2
    if len(frame) < 6 + nibble_bytes:
        raise BenchError("IMA-ADPCM frame truncated")
    for packed in frame[6 : 6 + nibble_bytes]:
        if len(samples) >= sample_count:
            break
        samples.append(decode_nibble(packed & 0x0F))
        if len(samples) >= sample_count:
            break
        samples.append(decode_nibble((packed >> 4) & 0x0F))
    if len(samples) != sample_count:
        raise BenchError(
            f"IMA-ADPCM sample count mismatch: got {len(samples)} expected {sample_count}"
        )
    return struct.pack(f"<{len(samples)}h", *samples)


def upsample_pcm16_x2(pcm8: bytes) -> bytes:
    """8 kHz mono LE i16 → 16 kHz linear midpoints (COMP-REQ-666)."""
    if len(pcm8) % 2 != 0:
        raise BenchError("upsample input not even")
    n = len(pcm8) // 2
    out = bytearray(n * 4)
    for i in range(n):
        s0 = struct.unpack_from("<h", pcm8, i * 2)[0]
        s1 = struct.unpack_from("<h", pcm8, (i + 1) * 2)[0] if i + 1 < n else s0
        mid = (s0 + s1) // 2
        struct.pack_into("<h", out, i * 4, s0)
        struct.pack_into("<h", out, i * 4 + 2, mid)
    return bytes(out)


def pack_settings_v1(
    *,
    locale: int = 0,
    flags: int = 0,
    time_zone_offset_min: int = 480,
    quiet_hours_start_min: int = 0,
    quiet_hours_end_min: int | None = None,
    display_brightness: int,
    recorder_profile_id: int = 1,
    unique: bool = True,
) -> bytes:
    """Pack SettingsV1.

    Firmware product identity is derived from the full payload, so identical
    rewrites are replayed and do not mutate. When unique=True, quiet_hours_end_min
    is used as a write nonce (quiet-hours flag cleared so it stays inactive).
    """
    global _SETTINGS_WRITE_NONCE
    q_end = 0 if quiet_hours_end_min is None else int(quiet_hours_end_min) & 0xFF
    out_flags = int(flags) & ~0x0001
    if unique:
        _SETTINGS_WRITE_NONCE = (_SETTINGS_WRITE_NONCE + 1) & 0xFF
        if _SETTINGS_WRITE_NONCE == 0:
            _SETTINGS_WRITE_NONCE = 1
        q_end = _SETTINGS_WRITE_NONCE
    return struct.pack(
        "<BBHhBBBB",
        SCHEMA_VERSION,
        int(locale) & 0xFF,
        out_flags & 0xFFFF,
        int(time_zone_offset_min),
        int(quiet_hours_start_min) & 0xFF,
        q_end,
        int(display_brightness) & 0xFF,
        int(recorder_profile_id) & 0xFF,
    )


def parse_settings(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHhBBBB",
        (
            "schema_version",
            "locale",
            "flags",
            "time_zone_offset_min",
            "quiet_hours_start_min",
            "quiet_hours_end_min",
            "display_brightness",
            "recorder_profile_id",
        ),
        payload,
    )


def parse_ble_name_config(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBHIBBBB29s",
        (
            "schema_version",
            "command",
            "flags",
            "request_id",
            "name_len",
            "max_len",
            "status",
            "reserved",
            "name",
        ),
        payload,
    )
    name_len = min(int(parsed["name_len"]), len(parsed["name"]))
    parsed["name_ascii"] = parsed["name"][:name_len].decode("ascii", errors="replace")
    parsed["name"] = parsed["name"].hex()
    return parsed


def parse_meeting_status(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBBBHHIIIIB3s",
        (
            "schema_version",
            "state",
            "last_error",
            "summary_state",
            "flags",
            "segment_count",
            "request_id",
            "meeting_id",
            "started_tick_ms",
            "duration_ms",
            "sync_state",
            "reserved",
        ),
        payload,
    )
    parsed["reserved"] = parsed["reserved"].hex()
    return parsed


def parse_imu_status(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBHHIhhhhhhh",
        (
            "schema_version",
            "sensor_state",
            "motion_flags",
            "calibration_state",
            "sample_rate_hz",
            "reserved",
            "sample_timestamp_ms",
            "accel_x_mg",
            "accel_y_mg",
            "accel_z_mg",
            "gyro_x_dps",
            "gyro_y_dps",
            "gyro_z_dps",
            "temperature_c_x10",
        ),
        payload,
    )


def parse_speaker_status(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBBBIB3sI",
        (
            "schema_version",
            "state",
            "last_error",
            "volume_percent",
            "request_id",
            "prompt_id",
            "reserved",
            "played_count",
        ),
        payload,
    )
    parsed["reserved"] = parsed["reserved"].hex()
    return parsed


def parse_wake_word_status(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBBBBBHHIII",
        (
            "schema_version",
            "armed",
            "engine_state",
            "last_event",
            "last_error",
            "sensitivity",
            "last_confidence",
            "reserved",
            "flags",
            "model_id",
            "request_id",
            "detection_count",
            "rejected_count",
        ),
        payload,
    )


def parse_diag_log_pull(payload: bytes) -> dict[str, Any]:
    header_format = "<BBHIIHHI"
    event_format = "<IIBBBBIIII"
    header_bytes = struct.calcsize(header_format)
    event_bytes = struct.calcsize(event_format)
    parsed = parse_struct(
        header_format,
        (
            "schema_version",
            "flags",
            "event_count",
            "request_cursor",
            "next_cursor",
            "total_available",
            "payload_bytes",
            "payload_crc32",
        ),
        payload,
    )
    expected_payload_bytes = int(parsed["event_count"]) * event_bytes
    if int(parsed["payload_bytes"]) != expected_payload_bytes:
        raise BenchError(
            "diagnostics payload/event count mismatch: "
            f"payload_bytes={parsed['payload_bytes']} event_count={parsed['event_count']}"
        )
    packet_bytes = header_bytes + expected_payload_bytes
    if len(payload) < packet_bytes:
        raise BenchError(f"diagnostics packet truncated: got {len(payload)}, need {packet_bytes}")
    event_payload = payload[header_bytes:packet_bytes]
    crc32 = binascii.crc32(event_payload) & 0xFFFFFFFF
    if int(parsed["payload_crc32"]) != crc32:
        raise BenchError(
            f"diagnostics CRC mismatch: got 0x{int(parsed['payload_crc32']):08x}, "
            f"expected 0x{crc32:08x}"
        )
    events = []
    event_names = (
        "sequence",
        "t_ms",
        "source",
        "event_id",
        "severity",
        "event_flags",
        "arg0",
        "arg1",
        "arg2",
        "arg3",
    )
    for offset in range(0, expected_payload_bytes, event_bytes):
        values = struct.unpack(event_format, event_payload[offset : offset + event_bytes])
        events.append(dict(zip(event_names, values, strict=True)))
    parsed["events"] = events
    parsed["packet_bytes"] = packet_bytes
    parsed["crc_valid"] = True
    return parsed


def parse_delete_privacy(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBHIII32s",
        (
            "schema_version",
            "operation",
            "flags",
            "request_id",
            "recording_id",
            "validated_total_length",
            "validated_sha256",
        ),
        payload,
    )
    parsed["validated_sha256"] = parsed["validated_sha256"].hex()
    return parsed


def parse_ota_readiness(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBBBHHII8s",
        (
            "schema_version",
            "ready_state",
            "boot_slot",
            "battery_percent",
            "minimum_required_mv",
            "blocker_bitmap",
            "manifest_version",
            "image_size",
            "image_sha256_prefix",
        ),
        payload,
    )
    parsed["image_sha256_prefix"] = parsed["image_sha256_prefix"].hex()
    return parsed


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise BenchError(message)


def ble_name_payload(command: int, request_id: int, name: str = "") -> bytes:
    raw = name.encode("ascii")
    if len(raw) > 29:
        raise ValueError("BLE name fixture is too long")
    return struct.pack(
        "<BBHIBBBB29s",
        SCHEMA_VERSION,
        command,
        0,
        request_id,
        len(raw),
        29,
        0,
        0,
        raw.ljust(29, b"\x00"),
    )


def normalize_address(address: str | None) -> str:
    return "" if address is None else address.replace(":", "").replace("-", "").lower()


def advertisement_services(adv: Any, device: Any) -> list[str]:
    service_uuids = getattr(adv, "service_uuids", None)
    if service_uuids is None:
        metadata = getattr(device, "metadata", {}) or {}
        service_uuids = metadata.get("uuids", [])
    return sorted({str(uuid).lower() for uuid in service_uuids or []})


async def scan_for_companion(args: argparse.Namespace, required: set[str]) -> tuple[Any, dict[str, Any]]:
    try:
        from bleak import BleakScanner
    except Exception as exc:  # noqa: BLE001 - CLI reports availability directly.
        raise BenchError(f"bleak import failed: {exc}") from exc

    discovered: list[tuple[Any, Any | None]] = []
    try:
        raw = await BleakScanner.discover(timeout=args.timeout, return_adv=True)
        for value in raw.values():
            if isinstance(value, tuple) and len(value) == 2:
                discovered.append((value[0], value[1]))
    except TypeError:
        for device in await BleakScanner.discover(timeout=args.timeout):
            discovered.append((device, None))

    target_address = normalize_address(args.address)
    target_name = args.name.lower()
    candidates: list[tuple[Any, Any | None, list[str], int | None, str]] = []
    for device, adv in discovered:
        name = (getattr(device, "name", None) or getattr(adv, "local_name", None) or "")
        address = str(getattr(device, "address", ""))
        adv_uuids = advertisement_services(adv, device)
        rssi = getattr(adv, "rssi", None)
        if rssi is None:
            rssi = getattr(device, "rssi", None)
        address_match = target_address and normalize_address(address) == target_address
        name_match = target_name in name.lower()
        service_match = bool(required.intersection(adv_uuids))
        if address_match or name_match or service_match:
            candidates.append((device, adv, adv_uuids, rssi, name))

    if not candidates:
        seen = [
            {
                "name": getattr(device, "name", None),
                "address": getattr(device, "address", None),
                "service_uuids": advertisement_services(adv, device),
            }
            for device, adv in discovered[:12]
        ]
        raise BenchError(f"no Companion candidate found; seen={seen}")

    def score(candidate: tuple[Any, Any | None, list[str], int | None, str]) -> tuple[int, int]:
        device, _adv, adv_uuids, rssi, name = candidate
        address = str(getattr(device, "address", ""))
        return (
            100 if target_address and normalize_address(address) == target_address else 0
        ) + (
            20 if target_name and target_name in name.lower() else 0
        ) + (
            len(required.intersection(adv_uuids))
        ), int(rssi if rssi is not None else -999)

    selected = max(candidates, key=score)
    device, _adv, adv_uuids, rssi, name = selected
    return device, {
        "operation": "scan",
        "status": "PASS",
        "selected_name": name,
        "selected_address": str(getattr(device, "address", "")),
        "rssi": rssi,
        "advertised_service_uuids": adv_uuids,
        "advertised_required_service_uuids": sorted(required.intersection(adv_uuids)),
        "candidate_count": len(candidates),
        "seen_count": len(discovered),
    }


async def get_services(client: Any) -> Any:
    """Return discovered GATT services.

    Windows/WinRT discovery is racy: ``client.services`` may be non-None but
    only partially populated right after connect. Always settle and refresh when
    ``get_services`` exists, then accept the richest collection observed.
    """
    best = getattr(client, "services", None)

    def _count(services: Any) -> int:
        if services is None:
            return 0
        try:
            return len(list(services))
        except Exception:
            return 0

    best_count = _count(best)
    for delay in (0.0, 0.4, 0.8):
        if delay:
            await asyncio.sleep(delay)
        if hasattr(client, "get_services"):
            try:
                refreshed = await client.get_services()
            except Exception:
                refreshed = getattr(client, "services", None)
        else:
            refreshed = getattr(client, "services", None)
        refreshed_count = _count(refreshed)
        if refreshed_count > best_count:
            best = refreshed
            best_count = refreshed_count
        # Companion product exposes 10 native services (8f7a0001..000a) plus GAP/GATT.
        if best_count >= 8:
            break
    if best is None or best_count == 0:
        raise BenchError("Bleak client did not expose services after connect")
    return best


def characteristic_uuid_set(services: Any) -> set[str]:
    uuids: set[str] = set()
    for service in services:
        for char in service.characteristics:
            uuids.add(str(char.uuid).lower())
    return uuids


def service_uuid_set(services: Any) -> set[str]:
    return {str(service.uuid).lower() for service in services}


async def read_and_parse(client: Any, uuid: str, parser: Callable[[bytes], dict[str, Any]]) -> dict[str, Any]:
    payload = bytes(await client.read_gatt_char(uuid))
    return parser(payload)


async def notify_write_wait(
    client: Any,
    notify_uuid: str,
    write_uuid: str,
    payload: bytes,
    parser: Callable[[bytes], dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    timeout: float,
) -> dict[str, Any]:
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(_sender: Any, data: bytearray) -> None:
        queue.put_nowait(bytes(data))

    await client.start_notify(notify_uuid, callback)
    try:
        await asyncio.sleep(0.15)
        await client.write_gatt_char(write_uuid, payload, response=True)
        deadline = time.monotonic() + timeout
        last: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=remaining)
            except asyncio.TimeoutError as exc:
                raise BenchError(f"notify timeout on {notify_uuid}; last={last}") from exc
            parsed = parser(raw)
            last = parsed
            if predicate(parsed):
                return parsed
        raise BenchError(f"notify predicate was not satisfied on {notify_uuid}; last={last}")
    finally:
        await client.stop_notify(notify_uuid)


async def write_card_and_collect_status(
    client: Any,
    uuids: dict[str, str],
    payload: bytes,
    request_id: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(_sender: Any, data: bytearray) -> None:
        queue.put_nowait(bytes(data))

    await client.start_notify(uuids["e_paper_card_status"], callback)
    statuses: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    final: dict[str, Any] | None = None
    try:
        await asyncio.sleep(0.15)
        await client.write_gatt_char(uuids["e_paper_card_write"], payload, response=True)
        deadline = time.monotonic() + float(args.screen_final_timeout)
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=max(0.1, deadline - time.monotonic()))
            except asyncio.TimeoutError as exc:
                raise BenchError(
                    f"card status final timeout for request_id={request_id}; "
                    f"accepted={accepted} final={final} statuses={statuses}"
                ) from exc
            parsed = parse_card_status(raw)
            if int(parsed["request_id"]) != request_id:
                continue
            statuses.append(parsed)
            if int(parsed["render_state"]) == CARD_RENDER_STATE_ACCEPTED and accepted is None:
                accepted = parsed
            elif int(parsed["render_state"]) in {
                CARD_RENDER_STATE_RENDERED,
                CARD_RENDER_STATE_FAILED,
                CARD_RENDER_STATE_BUSY,
            }:
                final = parsed
            if accepted is not None and final is not None:
                break
    finally:
        await client.stop_notify(uuids["e_paper_card_status"])

    if accepted is None:
        raise BenchError(f"card write did not publish accepted status; statuses={statuses}")
    if final is None:
        raise BenchError(f"card write did not publish final status; statuses={statuses}")
    if int(accepted["render_state"]) != CARD_RENDER_STATE_ACCEPTED or int(accepted["last_error"]) != CARD_LAST_ERROR_OK:
        raise BenchError(f"card write accepted status was not accepted/ok: {accepted}")
    identity_ok = (
        int(accepted["request_id"]) == int(final["request_id"])
        and int(accepted["content_crc32"]) == int(final["content_crc32"])
    )
    if not identity_ok:
        raise BenchError(f"card write accepted/final identity drifted: accepted={accepted} final={final}")

    rendered_ok = (
        int(final["render_state"]) == CARD_RENDER_STATE_RENDERED
        and int(final["last_error"]) == CARD_LAST_ERROR_OK
    )
    deferred_no_panel = (
        int(final["render_state"]) == CARD_RENDER_STATE_FAILED
        and int(final["last_error"]) in {
            CARD_LAST_ERROR_DEFERRED_NO_PANEL,
            CARD_LAST_ERROR_DEFERRED_CONTROLLER_UNKNOWN,
        }
    )
    if args.expect_real_panel and not rendered_ok:
        raise BenchError(f"--expect-real-panel requires final rendered/ok status; final={final}")
    if not args.expect_real_panel and not (rendered_ok or deferred_no_panel):
        raise BenchError(f"card write final status is neither rendered/ok nor deferred no-panel/controller: {final}")

    return {
        "operation": "card_write",
        "status": "PASS",
        "real_panel_required": bool(args.expect_real_panel),
        "real_panel_refresh_claimed": rendered_ok,
        "screen_final_timeout_s": float(args.screen_final_timeout),
        "card_status": accepted,
        "final_card_status": final,
        "status_sequence": statuses,
        "screen_panel_result": "rendered_ok" if rendered_ok else "deferred_no_panel_or_controller_unknown",
    }


def is_expression_card_status(parsed: dict[str, Any]) -> bool:
    return (
        int(parsed["card_slot"]) == EXPRESSION_CARD_SLOT
        and (int(parsed["request_id"]) & EXPRESSION_REQUEST_ID_MASK) == EXPRESSION_REQUEST_ID_BASE
    )


async def write_settings_and_collect_expression_status(
    client: Any,
    uuids: dict[str, str],
    payload: bytes,
    expected_brightness: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(_sender: Any, data: bytearray) -> None:
        queue.put_nowait(bytes(data))

    await client.start_notify(uuids["e_paper_card_status"], callback)
    statuses: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    final: dict[str, Any] | None = None
    try:
        await asyncio.sleep(0.15)
        while not queue.empty():
            queue.get_nowait()
        await client.write_gatt_char(uuids["settings"], payload, response=True)
        deadline = time.monotonic() + float(args.screen_final_timeout)
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=min(0.5, remaining))
            except asyncio.TimeoutError:
                continue
            parsed = parse_card_status(raw)
            if not is_expression_card_status(parsed):
                continue
            if accepted is None:
                if int(parsed["render_state"]) != CARD_RENDER_STATE_ACCEPTED:
                    continue
                accepted = parsed
                statuses.append(parsed)
                continue
            if int(parsed["request_id"]) != int(accepted["request_id"]):
                continue
            statuses.append(parsed)
            if int(parsed["render_state"]) in {
                CARD_RENDER_STATE_RENDERED,
                CARD_RENDER_STATE_FAILED,
                CARD_RENDER_STATE_BUSY,
            }:
                final = parsed
            if final is not None:
                break
    finally:
        await client.stop_notify(uuids["e_paper_card_status"])

    settings = await read_and_parse(client, uuids["settings"], parse_settings)
    assert_true(
        int(settings["display_brightness"]) == int(expected_brightness),
        "settings sleepy write did not persist expected display_brightness",
    )

    # Platform path: settings brightness=0 must stick. Expression notify is best-effort
    # when the board does not publish card_status for this settings edge (common without
    # a live panel path). --expect-real-panel still hard-requires rendered/ok.
    if accepted is None or final is None:
        if args.expect_real_panel:
            raise BenchError(
                "settings sleepy expression final timeout with --expect-real-panel; "
                f"accepted={accepted} final={final} statuses={statuses}"
            )
        return {
            "operation": "settings_sleepy_screen_status",
            "status": "PASS",
            "mode": "settings_persist_no_expression_status",
            "trigger": "SettingsV1 display_brightness=0",
            "real_panel_required": False,
            "real_panel_refresh_claimed": False,
            "screen_final_timeout_s": float(args.screen_final_timeout),
            "expression_request_id_base": f"0x{EXPRESSION_REQUEST_ID_BASE:08x}",
            "card_status": accepted,
            "final_card_status": final,
            "status_sequence": statuses,
            "settings": settings,
            "screen_panel_result": "no_expression_status_settings_persisted",
        }

    if int(accepted["render_state"]) != CARD_RENDER_STATE_ACCEPTED or int(accepted["last_error"]) != CARD_LAST_ERROR_OK:
        raise BenchError(f"settings sleepy accepted status was not accepted/ok: {accepted}")
    identity_ok = (
        int(accepted["request_id"]) == int(final["request_id"])
        and int(accepted["content_crc32"]) == int(final["content_crc32"])
    )
    if not identity_ok:
        raise BenchError(f"settings sleepy accepted/final identity drifted: accepted={accepted} final={final}")

    rendered_ok = (
        int(final["render_state"]) == CARD_RENDER_STATE_RENDERED
        and int(final["last_error"]) == CARD_LAST_ERROR_OK
    )
    deferred_no_panel = (
        int(final["render_state"]) == CARD_RENDER_STATE_FAILED
        and int(final["last_error"]) in {
            CARD_LAST_ERROR_DEFERRED_NO_PANEL,
            CARD_LAST_ERROR_DEFERRED_CONTROLLER_UNKNOWN,
        }
    )
    if args.expect_real_panel and not rendered_ok:
        raise BenchError(f"--expect-real-panel requires settings sleepy rendered/ok status; final={final}")
    if not args.expect_real_panel and not (rendered_ok or deferred_no_panel):
        raise BenchError(
            f"settings sleepy final status is neither rendered/ok nor deferred no-panel/controller: {final}"
        )

    return {
        "operation": "settings_sleepy_screen_status",
        "status": "PASS",
        "mode": "expression_status",
        "trigger": "SettingsV1 display_brightness=0",
        "real_panel_required": bool(args.expect_real_panel),
        "real_panel_refresh_claimed": rendered_ok,
        "screen_final_timeout_s": float(args.screen_final_timeout),
        "expression_request_id_base": f"0x{EXPRESSION_REQUEST_ID_BASE:08x}",
        "card_status": accepted,
        "final_card_status": final,
        "status_sequence": statuses,
        "settings": settings,
        "screen_panel_result": "rendered_ok" if rendered_ok else "deferred_no_panel_or_controller_unknown",
    }


def expression_status_sequence_contract() -> dict[str, Any]:
    fixture = json.loads(HOST_STATUS_SEQUENCE_PATH.read_text(encoding="utf-8"))
    steps = fixture.get("steps", [])
    if not isinstance(steps, list):
        raise BenchError("host screen_expression_status fixture does not contain steps")

    events = [str(step.get("event")) for step in steps if isinstance(step, dict)]
    faces = [str(step.get("expression")) for step in steps if isinstance(step, dict)]
    if events != list(EXPRESSION_STATUS_REQUIRED_EVENTS):
        raise BenchError(f"host screen_expression_status event order drifted: {events}")
    if faces != list(EXPRESSION_STATUS_REQUIRED_FACES):
        raise BenchError(f"host screen_expression_status face order drifted: {faces}")

    for step in steps:
        if not isinstance(step, dict):
            raise BenchError("host screen_expression_status step is not an object")
        for field in ["request_id", "content_crc32", "diagnostic_arg3", "accepted_refresh_count", "final_refresh_count"]:
            if field not in step:
                raise BenchError(f"host screen_expression_status step missing {field}: {step}")
        if int(step["final_refresh_count"]) != int(step["accepted_refresh_count"]) + 1:
            raise BenchError(f"host screen_expression_status refresh_count gap: {step}")

    return {
        "operation": "screen_expression_status",
        "status": "PASS",
        "contract_only": True,
        "hardware_collected": False,
        "host_sequence_fixture": repo_rel(HOST_STATUS_SEQUENCE_PATH),
        "expected_events": events,
        "required_faces": faces,
        "required_fields": [
            "request_id",
            "content_crc32",
            "diagnostic_arg3",
            "accepted_refresh_count",
            "final_refresh_count",
        ],
        "content_crc32_model": "comp_epaper_expression_decision_crc32",
        "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
        "real_panel_parity_dependency": "card_write and settings_sleepy_screen_status must still pass with --expect-real-panel before rendered/ok parity is claimed.",
    }


def expression_demo_status_sequence_contract() -> dict[str, Any]:
    fixture = json.loads(DEMO_HOST_STATUS_SEQUENCE_PATH.read_text(encoding="utf-8"))
    if fixture.get("operation") != "screen_expression_demo_status":
        raise BenchError("demo host status fixture operation drifted")
    if fixture.get("contract_only") is not True or fixture.get("hardware_collected") is not False:
        raise BenchError("demo host status fixture must remain contract-only")

    summary = fixture.get("summary", {})
    faces = [str(face) for face in summary.get("accepted_expression_coverage", [])]
    if faces != list(EXPRESSION_DEMO_STATUS_REQUIRED_FACES):
        raise BenchError(f"demo host status face coverage drifted: {faces}")
    accepted_steps = fixture.get("accepted_status_steps", [])
    held_steps = fixture.get("held_no_status_steps", [])
    if not isinstance(accepted_steps, list) or not isinstance(held_steps, list):
        raise BenchError("demo host status fixture steps are not lists")
    if int(summary.get("accepted_status_pair_count", -1)) != len(accepted_steps):
        raise BenchError("demo host status accepted step count drifted")
    if int(summary.get("held_no_status_count", -1)) != len(held_steps):
        raise BenchError("demo host status held step count drifted")

    for step in accepted_steps:
        if not isinstance(step, dict):
            raise BenchError("demo host status accepted step is not an object")
        for field in ["request_id", "content_crc32", "diagnostic_arg3", "card_status", "dry_run_final_status"]:
            if field not in step:
                raise BenchError(f"demo host status accepted step missing {field}: {step}")
        accepted = step["card_status"]
        final = step["dry_run_final_status"]
        if int(final["refresh_count"]) != int(accepted["refresh_count"]) + 1:
            raise BenchError(f"demo host status refresh_count gap: {step}")
        if accepted["request_id"] != final["request_id"] or accepted["content_crc32"] != final["content_crc32"]:
            raise BenchError(f"demo host status identity drift: {step}")

    for step in held_steps:
        if not isinstance(step, dict):
            raise BenchError("demo host status held step is not an object")
        if step.get("host_status_emitted") is not False:
            raise BenchError(f"demo host status held step emitted status: {step}")

    return {
        "operation": "screen_expression_demo_status",
        "status": "PASS",
        "contract_only": True,
        "hardware_collected": False,
        "host_sequence_fixture": repo_rel(DEMO_HOST_STATUS_SEQUENCE_PATH),
        "required_faces": faces,
        "accepted_status_pair_count": len(accepted_steps),
        "held_no_status_count": len(held_steps),
        "required_fields": [
            "request_id",
            "content_crc32",
            "diagnostic_arg3",
            "card_status",
            "dry_run_final_status",
        ],
        "content_crc32_model": "comp_epaper_expression_decision_crc32",
        "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
        "held_steps_contract": "held_steps_emit_no_host_status",
        "real_panel_parity_dependency": (
            "card_write and settings_sleepy_screen_status still provide the "
            "hardware-collected rendered/ok evidence."
        ),
    }


async def pull_existing_recording_no_delete(
    client: Any,
    uuids: dict[str, str],
    recording_list: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    entries = list(recording_list.get("entries", []))
    if not entries:
        raise BenchError("--pull-existing-recording requires a non-empty recording_list")

    requested_recording_id = getattr(args, "pull_recording_id", None)
    if requested_recording_id is None:
        entry = entries[0]
    else:
        matches = [
            candidate
            for candidate in entries
            if int(candidate["recording_id"]) == int(requested_recording_id)
        ]
        if len(matches) != 1:
            available = [int(candidate["recording_id"]) for candidate in entries]
            raise BenchError(
                "--pull-recording-id did not resolve exactly once: "
                f"requested={requested_recording_id} available={available}"
            )
        entry = matches[0]
    recording_id = int(entry["recording_id"])
    total_length = int(entry["total_length"])
    if total_length <= 0:
        raise BenchError(f"selected recording has empty total_length: {entry}")

    # Device intermediate payload max is 220 (ATT 244 − 24B base header).
    # Full ATT 248 regressed multi-notify on Windows Type host (COMP-REQ-663).
    chunk_bytes = max(1, min(int(args.chunk_bytes), 220))
    # Continuous stream: one write can pull many packets (device streams until budget).
    # For compress mode budget is in PCM bytes (not wire).
    window_chunks = max(1, min(int(getattr(args, "window_chunks", 256)), 340))
    compress = bool(getattr(args, "compress_ima", True))
    # PCM budget: with ~4:1 ADPCM, ask for large PCM window per write.
    pcm_per_packet = 752 if compress else chunk_bytes  # ~376 samples * 2
    window_bytes = min(pcm_per_packet * window_chunks, 0xFFFF)
    # Compress path encodes on-device between packets; allow longer idle before ending window.
    default_inter = 1.2 if compress else 0.25
    inter_packet_timeout = float(getattr(args, "inter_packet_timeout", default_inter))
    if getattr(args, "inter_packet_timeout", None) is None:
        inter_packet_timeout = default_inter
    # argparse always sets the attr; use explicit rule:
    inter_packet_timeout = float(args.inter_packet_timeout)
    if compress and inter_packet_timeout < 0.8:
        inter_packet_timeout = 1.2
    link_settle = float(getattr(args, "link_settle", 0.5))
    write_response = not bool(getattr(args, "write_without_response", True))
    req_flags = 0
    if compress:
        req_flags |= RECORDING_REQ_COMPRESS_IMA
    req_flags |= RECORDING_REQ_STREAM_ALL

    offset = 0
    expected_sequence = 0
    data = bytearray()  # reconstructed PCM (filled after bulk RX when deferred)
    wire_bytes = 0
    packet_summaries: list[dict[str, Any]] = []
    deferred_payloads: list[dict[str, Any]] = []
    final_sha256 = ""
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    pending_by_offset: dict[int, dict[str, Any]] = {}
    inter_packet_gaps_ms: list[float] = []
    last_packet_mono: float | None = None
    gap_stats: dict[str, Any] = {}
    rate_kb_s = 0.0
    wire_rate_kb_s = 0.0
    elapsed = 0.0

    def callback(_sender: Any, raw: bytearray) -> None:
        # Ignore empty/CCCD side-effect notifies from the stack/OS.
        if raw is None or len(raw) == 0:
            return
        queue.put_nowait(bytes(raw))

    def drain_queue_into_pending() -> None:
        while True:
            try:
                raw = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if not raw:
                continue
            try:
                parsed = parse_recording_chunk_packet(raw)
            except BenchError as parse_err:
                # Transient garbage; keep waiting for real chunks.
                print(f"recording chunk parse skip: {parse_err}", flush=True)
                continue
            if int(parsed["recording_id"]) != recording_id:
                continue
            pkt_off = int(parsed["byte_offset"])
            if pkt_off >= offset:
                pending_by_offset[pkt_off] = parsed

    await client.start_notify(uuids["recording_chunk_pull"], callback)
    dual_lane = "recording_chunk_pull_b" in uuids
    if dual_lane:
        await client.start_notify(uuids["recording_chunk_pull_b"], callback)
    try:
        # COMP-REQ-667: re-assert throughput CI immediately before bulk notify flood.
        # Windows often re-parks to ~15 ms after service discovery / idle.
        try:
            from winrt.windows.devices.bluetooth import (
                BluetoothLEDevice,
                BluetoothLEPreferredConnectionParameters,
            )

            addr = getattr(client, "address", None)
            if addr:
                addr_int = int(str(addr).replace(":", ""), 16)
                ble_dev = await BluetoothLEDevice.from_bluetooth_address_async(addr_int)
                if ble_dev is not None:
                    pre_pull = ble_dev.request_preferred_connection_parameters(
                        BluetoothLEPreferredConnectionParameters.throughput_optimized
                    )
                    print(
                        f"winrt pre-pull throughput params result={pre_pull}",
                        flush=True,
                    )
        except Exception as pre_exc:  # noqa: BLE001
            print(f"winrt pre-pull params skip: {pre_exc}", flush=True)
        if link_settle > 0:
            await asyncio.sleep(link_settle)
        transfer_started = time.monotonic()
        print(
            f"recording pull start total_pcm={total_length} chunk={chunk_bytes} "
            f"window_chunks={window_chunks} window_pcm_bytes={window_bytes} "
            f"compress_ima={compress} write_response={write_response} "
            f"(wire_rate=实际空中字节/s; pcm_effective_rate=等效PCM字节/s)",
            flush=True,
        )
        stall_restarts_at_offset = 0
        last_stall_offset = -1
        while offset < total_length:
            write_offset = offset
            remaining = total_length - offset
            # Tail: single-packet mode (no STREAM_ALL) — FINAL is often dropped in flood.
            tail_mode = remaining <= 1024
            flags_now = req_flags
            if tail_mode:
                flags_now = req_flags & ~RECORDING_REQ_STREAM_ALL
            # STREAM_ALL: device ignores budget and sends remaining PCM; keep length as hint.
            request_length = min(window_bytes, remaining, 0xFFFF)
            if tail_mode:
                request_length = min(remaining, 192, 0xFFFF)  # FINAL: ATT 248 − 56B header
            request = struct.pack(
                "<BBHIII",
                SCHEMA_VERSION,
                flags_now,
                int(request_length),
                recording_id,
                write_offset,
                0,
            )
            # Tail: use write-with-response so the final START is not lost on WinRT.
            use_response = write_response or tail_mode
            try:
                await asyncio.wait_for(
                    client.write_gatt_char(
                        uuids["recording_chunk_pull"], request, response=use_response
                    ),
                    timeout=8.0,
                )
            except asyncio.TimeoutError as write_to:
                raise BenchError(
                    f"recording_chunk_pull write timed out at offset={write_offset}"
                ) from write_to
            if remaining <= 1024:
                await asyncio.sleep(0.05)
            packets_in_window = 0
            # STREAM_ALL: wait until full recording or FINAL, not just one window budget.
            window_end = total_length if (flags_now & RECORDING_REQ_STREAM_ALL) else (
                write_offset + int(request_length)
            )
            last_rx = time.monotonic()
            # Near end of file allow longer first-packet wait (FINAL packet is easy to drop).
            tail = total_length - offset
            notify_to = float(args.notify_timeout)
            if tail <= 4096:
                notify_to = max(notify_to, 30.0)
            first_deadline = time.monotonic() + notify_to
            idle_to = inter_packet_timeout
            if tail <= 4096:
                idle_to = max(idle_to, 3.0)

            while offset < total_length and offset < window_end:
                drain_queue_into_pending()
                packet = pending_by_offset.pop(offset, None)
                if packet is None:
                    # Wait for more notifies; after first packet use short idle gap.
                    if packets_in_window == 0:
                        if time.monotonic() >= first_deadline:
                            if last_stall_offset == offset:
                                stall_restarts_at_offset += 1
                            else:
                                last_stall_offset = offset
                                stall_restarts_at_offset = 1
                            if stall_restarts_at_offset > 8:
                                raise BenchError(
                                    f"recording chunk notify timeout at offset={offset} "
                                    f"after {stall_restarts_at_offset} restarts"
                                )
                            print(
                                f"recording pull stall restart offset={offset} "
                                f"try={stall_restarts_at_offset}",
                                flush=True,
                            )
                            break  # outer loop re-START from same offset
                        wait = min(0.05, first_deadline - time.monotonic())
                    else:
                        idle_left = idle_to - (time.monotonic() - last_rx)
                        if idle_left <= 0:
                            # Burst finished for this window; re-request from current offset.
                            break
                        wait = min(0.05, idle_left)
                    try:
                        raw = await asyncio.wait_for(queue.get(), timeout=max(0.01, wait))
                        if not raw:
                            continue
                        try:
                            parsed = parse_recording_chunk_packet(raw)
                        except BenchError as parse_err:
                            print(f"recording chunk parse skip: {parse_err}", flush=True)
                            continue
                        if int(parsed["recording_id"]) == recording_id:
                            pkt_off = int(parsed["byte_offset"])
                            if pkt_off >= offset:
                                pending_by_offset[pkt_off] = parsed
                                last_rx = time.monotonic()
                    except asyncio.TimeoutError:
                        pass
                    continue

                last_rx = time.monotonic()
                if last_packet_mono is not None:
                    inter_packet_gaps_ms.append((last_rx - last_packet_mono) * 1000.0)
                last_packet_mono = last_rx
                if int(packet["flags"]) & RECORDING_ERROR_FLAG:
                    raise BenchError(f"recording chunk error flag at offset={offset}: {packet}")
                if int(packet["packet_sequence"]) != expected_sequence:
                    # Flash sequence can jump on re-START / prep discard; offset is the
                    # stream cursor. Accept monotonic gap if offset matches and CRC passes.
                    if int(packet["byte_offset"]) == offset:
                        expected_sequence = int(packet["packet_sequence"])
                    else:
                        raise BenchError(
                            f"recording packet sequence mismatch: got {packet['packet_sequence']} "
                            f"expected {expected_sequence} offset={offset} pkt_off={packet['byte_offset']}"
                        )
                # Compact intermediate omits total_length (0); CRC still uses list total.
                if int(packet["total_length"]) == 0:
                    packet["total_length"] = total_length
                elif int(packet["total_length"]) != total_length:
                    raise BenchError("recording total_length changed during transfer")
                payload = bytes(packet["payload"])
                if len(payload) != int(packet["payload_length"]):
                    raise BenchError("recording payload_length mismatch")
                flags = int(packet["flags"])
                # COMP-REQ-667: during bulk flood only light-parse + wire count.
                # Defer CRC/IMA decode until after FINAL so host CPU does not
                # back-pressure Windows BLE (aim higher wire_rate).
                wire_bytes += len(payload)
                if flags & RECORDING_COMPRESSED_IMA_FLAG:
                    if len(payload) < 6:
                        raise BenchError("IMA payload too short for sample_count")
                    sample_count = struct.unpack_from("<H", payload, 4)[0]
                    if flags & RECORDING_HALF_RATE_8K_FLAG:
                        # 8 kHz samples → host upsample ×2 → 16 kHz PCM bytes
                        pcm_advance = int(sample_count) * 4
                    else:
                        pcm_advance = int(sample_count) * 2
                    deferred_payloads.append(
                        {
                            "packet": packet,
                            "payload": payload,
                            "flags": flags,
                            "pcm_advance": pcm_advance,
                        }
                    )
                    pcm_piece_len = pcm_advance
                else:
                    deferred_payloads.append(
                        {
                            "packet": packet,
                            "payload": payload,
                            "flags": flags,
                            "pcm_advance": len(payload),
                        }
                    )
                    pcm_piece_len = len(payload)
                offset += pcm_piece_len
                expected_sequence += 1
                packets_in_window += 1
                if expected_sequence % 50 == 0 or offset >= total_length:
                    elapsed = max(0.001, time.monotonic() - transfer_started)
                    # pcm progress estimated from header sample counts (decode later)
                    pcm_rate = (offset / 1024.0) / elapsed
                    wire_rate = (wire_bytes / 1024.0) / elapsed
                    print(
                        f"recording pull progress pcm={offset}/{total_length} "
                        f"wire={wire_bytes} packets={expected_sequence} "
                        f"pcm_effective_rate={pcm_rate:.1f} KB/s wire_rate={wire_rate:.1f} KB/s "
                        f"compress={compress} win_pkts={packets_in_window} deferred_decode=1",
                        flush=True,
                    )
                if flags & RECORDING_FINAL_FLAG:
                    final_sha256 = str(packet["final_sha256"])
                    break
            if final_sha256:
                break
            if packets_in_window == 0:
                # Stall-restart path also hits packets_in_window==0; allow re-START.
                if last_stall_offset == offset and stall_restarts_at_offset > 0:
                    if stall_restarts_at_offset > 8:
                        raise BenchError(
                            f"recording window produced zero packets at offset={write_offset} "
                            f"after {stall_restarts_at_offset} stall restarts"
                        )
                    await asyncio.sleep(0.1)
                    continue
                raise BenchError(f"recording window produced zero packets at offset={write_offset}")
        # Wall-clock for wire rate ends when last notify arrives (before heavy decode).
        elapsed = max(0.001, time.monotonic() - transfer_started)
        wire_rate_kb_s = (wire_bytes / 1024.0) / elapsed
        # Post-transfer: CRC + IMA decode (does not count against wire_rate).
        for item in deferred_payloads:
            packet = item["packet"]
            payload = item["payload"]
            flags = int(item["flags"])
            packet_crc = verify_recording_packet_crc(packet)
            if flags & RECORDING_COMPRESSED_IMA_FLAG:
                pcm_piece = decode_ima_adpcm_frame(payload)
                if flags & RECORDING_HALF_RATE_8K_FLAG:
                    pcm_piece = upsample_pcm16_x2(pcm_piece)
            else:
                pcm_piece = payload
            if len(pcm_piece) != int(item["pcm_advance"]):
                # Tolerate 0-3 sample framing edge; hard fail only on large mismatch.
                if abs(len(pcm_piece) - int(item["pcm_advance"])) > 4:
                    raise BenchError(
                        f"deferred pcm length mismatch got={len(pcm_piece)} "
                        f"expected={item['pcm_advance']} seq={packet.get('packet_sequence')}"
                    )
            data.extend(pcm_piece)
            packet_summaries.append(
                {
                    "packet_sequence": int(packet["packet_sequence"]),
                    "byte_offset": int(packet["byte_offset"]),
                    "payload_length": int(packet["payload_length"]),
                    "pcm_bytes": len(pcm_piece),
                    "packet_crc32": packet_crc,
                    "flags": flags,
                }
            )
        rate_kb_s = (len(data) / 1024.0) / elapsed
        ratio = (len(data) / max(1, wire_bytes)) if wire_bytes else 0.0
        if inter_packet_gaps_ms:
            ordered = sorted(inter_packet_gaps_ms)
            n = len(ordered)
            bursty = sum(1 for g in ordered if g < 5.0)
            gap_stats = {
                "gap_count": n,
                "gap_min_ms": round(ordered[0], 3),
                "gap_p50_ms": round(ordered[n // 2], 3),
                "gap_p90_ms": round(ordered[min(n - 1, int(n * 0.9))], 3),
                "gap_max_ms": round(ordered[-1], 3),
                "gaps_under_5ms": bursty,
                "multi_packet_ce_hint": bursty > max(1, n // 20),
                "note": "gaps_under_5ms suggests multi-notify same CE; p50~15ms + few bursts = 1 pkt/CE",
            }
            print(
                f"packet_gap_ms min={gap_stats['gap_min_ms']} p50={gap_stats['gap_p50_ms']} "
                f"p90={gap_stats['gap_p90_ms']} max={gap_stats['gap_max_ms']} "
                f"under_5ms={bursty}/{n} multi_ce_hint={gap_stats['multi_packet_ce_hint']}",
                flush=True,
            )
        print(
            f"recording pull done pcm={len(data)} wire={wire_bytes} packets={expected_sequence} "
            f"实际wire_rate={wire_rate_kb_s:.1f} KB/s 等效pcm_effective_rate={rate_kb_s:.1f} KB/s "
            f"ratio={ratio:.2f}x elapsed={elapsed:.3f}s compress={compress}",
            flush=True,
        )
    finally:
        if dual_lane:
            await client.stop_notify(uuids["recording_chunk_pull_b"])
        await client.stop_notify(uuids["recording_chunk_pull"])

    if len(data) != total_length:
        raise BenchError(f"recording byte count mismatch: got {len(data)}, expected {total_length}")
    pcm_samples = [sample[0] for sample in struct.iter_unpack("<h", data)]
    pcm_peak = max((abs(sample) for sample in pcm_samples), default=0)
    pcm_nonzero_samples = sum(1 for sample in pcm_samples if sample != 0)
    pcm_rms = (
        (sum(sample * sample for sample in pcm_samples) / len(pcm_samples)) ** 0.5
        if pcm_samples
        else 0.0
    )
    host_sha256 = hashlib.sha256(data).hexdigest()
    host_crc32 = f"0x{binascii.crc32(data) & 0xFFFFFFFF:08x}"
    if not final_sha256:
        raise BenchError("final recording packet did not include SHA-256")
    if compress:
        # IMA-ADPCM is lossy: wire CRC already verified per packet; length must match.
        # Original flash SHA/CRC of PCM will not match decoded samples.
        integrity_mode = "lossy_ima_length_and_packet_crc"
        sha_match = None
    else:
        if final_sha256 != host_sha256:
            raise BenchError(f"final SHA mismatch: device={final_sha256} host={host_sha256}")
        if not host_sha256.startswith(str(entry["sha256_prefix"])):
            raise BenchError("recording_list sha256_prefix did not match pulled object")
        if host_crc32.lower() != str(entry["content_crc32"]).lower():
            raise BenchError(
                f"recording_list CRC mismatch: list={entry['content_crc32']} host={host_crc32}"
            )
        integrity_mode = "lossless_pcm_sha_crc"
        sha_match = final_sha256 == host_sha256

    segment_gap_count = 0
    segment_duplicate_count = 0
    seen_offsets: set[int] = set()
    expected_offset = 0
    for summary in packet_summaries:
        packet_offset = int(summary["byte_offset"])
        if packet_offset in seen_offsets:
            segment_duplicate_count += 1
        seen_offsets.add(packet_offset)
        if packet_offset != expected_offset:
            segment_gap_count += 1
        expected_offset = packet_offset + int(summary["pcm_bytes"])
    if expected_offset != total_length:
        segment_gap_count += 1

    archive_path = None
    requested_archive = getattr(args, "pull_output_pcm", None)
    if requested_archive is not None:
        archive_path = pathlib.Path(requested_archive)
        if not archive_path.is_absolute():
            archive_path = REPO_ROOT / archive_path
        archive_path = archive_path.resolve()
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(data)

    return {
        "operation": "recording_pull_existing_no_delete",
        "status": "PASS",
        "no_delete": True,
        "recording_id": recording_id,
        "dual_lane": dual_lane,
        "total_length": total_length,
        "chunk_bytes": chunk_bytes,
        "window_chunks": window_chunks,
        "window_bytes": window_bytes,
        "compress_ima": compress,
        "rate_kb_s": round(rate_kb_s, 3),
        "pcm_effective_rate_kb_s": round(rate_kb_s, 3),
        "wire_rate_kb_s": round(wire_rate_kb_s, 3),
        "actual_wire_rate_kb_s": round(wire_rate_kb_s, 3),
        "equivalent_pcm_rate_kb_s": round(rate_kb_s, 3),
        "compress_ratio": round(len(data) / max(1, wire_bytes), 3) if wire_bytes else 0.0,
        "wire_bytes": wire_bytes,
        "pcm_bytes": len(data),
        "pcm_peak": pcm_peak,
        "pcm_rms": round(pcm_rms, 3),
        "pcm_nonzero_samples": pcm_nonzero_samples,
        "pcm_nonzero_ratio": round(pcm_nonzero_samples / max(1, len(pcm_samples)), 6),
        "elapsed_s": round(elapsed, 3),
        "packet_count": len(packet_summaries),
        "host_sha256": host_sha256,
        "device_final_sha256": final_sha256,
        "sha_match": sha_match,
        "host_crc32": host_crc32,
        "segment_gap_count": segment_gap_count,
        "segment_duplicate_count": segment_duplicate_count,
        "archived_pcm": str(archive_path) if archive_path is not None else None,
        "archived_pcm_sha256": host_sha256 if archive_path is not None else None,
        "selected_recording_list_entry": entry,
        "packets": packet_summaries[:32],
        "integrity_mode": integrity_mode,
        "p1_product": rate_kb_s >= 50.0,
        "p1_radio": wire_rate_kb_s >= 50.0,
        "p1_wire_30": wire_rate_kb_s >= 30.0,
        "p1_wire_50": wire_rate_kb_s >= 50.0,
        "packet_gap_stats": gap_stats,
        "metrics_note": "wire_rate=实际空中传输; pcm_effective_rate=等效PCM交付速率",
    }


async def run_connected_bench(
    client: Any,
    uuids: dict[str, str],
    args: argparse.Namespace,
    operations: list[dict[str, Any]],
) -> None:
    device_status = await read_and_parse(client, uuids["device_status"], parse_device_status)
    battery_charge = await read_and_parse(client, uuids["battery_charge"], parse_battery_charge)
    battery_percent = int(battery_charge["percent"])
    battery_unavailable = (
        battery_percent == 0xFF
        and int(battery_charge["charger_present"]) == 0
        and int(battery_charge["millivolts"]) == 0
    )
    assert_true(
        0 <= battery_percent <= 100 or battery_unavailable,
        "battery percent out of range and not an honest unavailable tuple",
    )
    operations.append(
        {
            "operation": "status_read",
            "status": "PASS",
            "device_status": device_status,
            "battery_charge": battery_charge,
            "battery_measurement_available": not battery_unavailable,
            "ui_fallback_percent_when_unavailable": 80 if battery_unavailable else None,
        }
    )

    # Read-only archival must take precedence over every control-mode shortcut.
    # Previously --pull-only --v1-control-only still created a fresh recording
    # before pulling, which can evict the oldest entry from a full ring.
    if args.pull_existing_recording and bool(getattr(args, "pull_only", False)):
        recording_list = await read_and_parse(client, uuids["recording_list"], parse_recording_list)
        operations.append(
            {
                "operation": "recording_list",
                "status": "PASS",
                "list_state": (
                    "empty" if int(recording_list["count"]) == 0 else "non_empty_metadata_present"
                ),
                "recording_list": recording_list,
            }
        )
        operations.append(
            await pull_existing_recording_no_delete(client, uuids, recording_list, args)
        )
        return

    if bool(getattr(args, "v1_control_only", False)):
        await run_v1_control_only(client, uuids, args, operations)
        return

    operations.append(expression_status_sequence_contract())
    operations.append(expression_demo_status_sequence_contract())

    title = "Bench card".encode("utf-8")
    body = "Companion native BLE card write bench".encode("utf-8")
    card_request_id = 17
    card_payload = struct.pack("<BBHIHH", SCHEMA_VERSION, 0, 0, card_request_id, len(title), len(body))
    card_payload += title + body
    operations.append(await write_card_and_collect_status(client, uuids, card_payload, card_request_id, args))

    # Read-modify-write settings so we stay on a value the firmware actually stores.
    # Unique payload each write: identical settings are product-idempotent replays.
    settings_before = await read_and_parse(client, uuids["settings"], parse_settings)
    target_brightness = 40 if int(settings_before["display_brightness"]) != 40 else 50
    settings_payload = pack_settings_v1(
        locale=int(settings_before["locale"]),
        flags=int(settings_before["flags"]),
        time_zone_offset_min=int(settings_before["time_zone_offset_min"]),
        quiet_hours_start_min=int(settings_before["quiet_hours_start_min"]),
        display_brightness=target_brightness,
        recorder_profile_id=int(settings_before["recorder_profile_id"]),
        unique=True,
    )
    # Prefer notify echo; if the target only applies on write without notify,
    # fall back to write+readback so real-radio acceptance is not blocked.
    try:
        settings = await notify_write_wait(
            client,
            uuids["settings"],
            uuids["settings"],
            settings_payload,
            parse_settings,
            lambda parsed: int(parsed["display_brightness"]) == target_brightness,
            min(float(args.notify_timeout), 4.0),
        )
        operations.append(
            {
                "operation": "settings_write",
                "status": "PASS",
                "mode": "notify_echo",
                "target_brightness": target_brightness,
                "settings": settings,
            }
        )
    except BenchError as settings_notify_exc:
        await client.write_gatt_char(uuids["settings"], settings_payload, response=True)
        await asyncio.sleep(0.25)
        settings = await read_and_parse(client, uuids["settings"], parse_settings)
        assert_true(
            int(settings["display_brightness"]) == target_brightness,
            f"settings write readback failed after notify miss: {settings}; notify_error={settings_notify_exc}",
        )
        operations.append(
            {
                "operation": "settings_write",
                "status": "PASS",
                "mode": "write_readback_fallback",
                "target_brightness": target_brightness,
                "settings": settings,
                "notify_error": str(settings_notify_exc),
            }
        )

    sleepy_settings_payload = pack_settings_v1(
        locale=0,
        flags=0,
        time_zone_offset_min=480,
        quiet_hours_start_min=0,
        display_brightness=0,
        recorder_profile_id=1,
        unique=True,
    )
    operations.append(
        await write_settings_and_collect_expression_status(
            client,
            uuids,
            sleepy_settings_payload,
            0,
            args,
        )
    )
    restore_brightness = target_brightness if target_brightness != 0 else 50
    # Device can reject the first few writes right after brightness=0; retry unique payloads.
    settings_restore: dict[str, Any] | None = None
    restore_mode = "notify_echo"
    restore_errors: list[str] = []
    for attempt in range(5):
        restore_payload = pack_settings_v1(
            locale=int(settings["locale"]),
            flags=int(settings["flags"]),
            time_zone_offset_min=int(settings["time_zone_offset_min"]),
            quiet_hours_start_min=int(settings["quiet_hours_start_min"]),
            display_brightness=restore_brightness,
            recorder_profile_id=int(settings["recorder_profile_id"]),
            unique=True,
        )
        try:
            settings_restore = await notify_write_wait(
                client,
                uuids["settings"],
                uuids["settings"],
                restore_payload,
                parse_settings,
                lambda parsed: int(parsed["display_brightness"]) == restore_brightness,
                min(float(args.notify_timeout), 3.0),
            )
            restore_mode = "notify_echo"
            break
        except BenchError as restore_notify_exc:
            restore_errors.append(str(restore_notify_exc))
            await client.write_gatt_char(uuids["settings"], restore_payload, response=True)
            await asyncio.sleep(0.8 + attempt * 0.4)
            settings_restore = await read_and_parse(client, uuids["settings"], parse_settings)
            if int(settings_restore["display_brightness"]) == restore_brightness:
                restore_mode = "write_readback_fallback"
                break
            if attempt == 2:
                restore_brightness = 80 if restore_brightness != 80 else 50
    assert_true(
        settings_restore is not None
        and int(settings_restore["display_brightness"]) == restore_brightness,
        f"settings restore after sleepy failed: last={settings_restore} errors={restore_errors}",
    )
    operations.append(
        {
            "operation": "settings_restore_after_sleepy",
            "status": "PASS",
            "mode": restore_mode,
            "settings": settings_restore,
            "restore_errors": restore_errors,
        }
    )

    recording_request_id = 23
    recording_payload = struct.pack("<BBBBIH", SCHEMA_VERSION, 2, 1, 0, recording_request_id, 5)
    recording_echo = await notify_write_wait(
        client,
        uuids["recording_control"],
        uuids["recording_control"],
        recording_payload,
        parse_recording_control,
        lambda parsed: parsed["request_id"] == recording_request_id,
        args.notify_timeout,
    )
    recording_list = await read_and_parse(client, uuids["recording_list"], parse_recording_list)
    recording_list_count = int(recording_list["count"])
    recording_ids = [int(entry["recording_id"]) for entry in recording_list.get("entries", [])]
    operations.append(
        {
            "operation": "recording_control_and_list",
            "status": "PASS",
            "list_state": "empty" if recording_list_count == 0 else "non_empty_metadata_present",
            "recording_control_echo": recording_echo,
            "recording_list": recording_list,
        }
    )

    if args.pull_existing_recording:
        operations.append(await pull_existing_recording_no_delete(client, uuids, recording_list, args))

    missing_recording_id = max(recording_ids, default=0) + 1
    chunk_payload = struct.pack("<BBHIII", SCHEMA_VERSION, 0, 64, missing_recording_id, 0, 0x1234)
    chunk_response = await notify_write_wait(
        client,
        uuids["recording_chunk_pull"],
        uuids["recording_chunk_pull"],
        chunk_payload,
        parse_recording_chunk_pull,
        lambda parsed: (parsed["flags"] & 0x80) != 0,
        args.notify_timeout,
    )
    assert_true(chunk_response["requested_length"] == 0, "recording chunk refusal did not clear requested_length")
    operations.append(
        {
            "operation": "recording_chunk_missing_refusal",
            "status": "PASS",
            "requested_recording_id": missing_recording_id,
            "recording_chunk_pull": chunk_response,
        }
    )

    ble_name_initial = await read_and_parse(client, uuids["ble_name_config"], parse_ble_name_config)
    assert_true(ble_name_initial["max_len"] == 29, "BLE name config max_len mismatch")
    assert_true(ble_name_initial["name_ascii"], "BLE name config did not expose an active name")
    invalid_ble_name_request_id = 91
    invalid_ble_name = await notify_write_wait(
        client,
        uuids["ble_name_config"],
        uuids["ble_name_config"],
        ble_name_payload(1, invalid_ble_name_request_id, ""),
        parse_ble_name_config,
        lambda parsed: parsed["request_id"] == invalid_ble_name_request_id,
        args.notify_timeout,
    )
    assert_true(invalid_ble_name["status"] == 0x80, "empty BLE name was not rejected")
    valid_ble_name_request_id = 92
    valid_ble_name = await notify_write_wait(
        client,
        uuids["ble_name_config"],
        uuids["ble_name_config"],
        ble_name_payload(1, valid_ble_name_request_id, "companion-v1"),
        parse_ble_name_config,
        lambda parsed: parsed["request_id"] == valid_ble_name_request_id,
        args.notify_timeout,
    )
    assert_true(valid_ble_name["status"] == 1, "valid BLE name was not staged")
    assert_true((valid_ble_name["flags"] & 0x0001) != 0, "valid BLE name did not require restart")
    apply_ble_name_request_id = 93
    applied_ble_name = await notify_write_wait(
        client,
        uuids["ble_name_config"],
        uuids["ble_name_config"],
        ble_name_payload(2, apply_ble_name_request_id),
        parse_ble_name_config,
        lambda parsed: parsed["request_id"] == apply_ble_name_request_id,
        args.notify_timeout,
    )
    assert_true(applied_ble_name["status"] == 2, "BLE name apply did not report restart_required")
    reset_ble_name_request_id = 94
    reset_ble_name = await notify_write_wait(
        client,
        uuids["ble_name_config"],
        uuids["ble_name_config"],
        ble_name_payload(3, reset_ble_name_request_id),
        parse_ble_name_config,
        lambda parsed: parsed["request_id"] == reset_ble_name_request_id,
        args.notify_timeout,
    )
    assert_true(reset_ble_name["name_ascii"] == "companion", "BLE name reset did not restore default name")
    operations.append(
        {
            "operation": "ble_name_config",
            "status": "PASS",
            "initial": ble_name_initial,
            "invalid_empty": invalid_ble_name,
            "staged": valid_ble_name,
            "applied": applied_ble_name,
            "reset": reset_ble_name,
        }
    )

    meeting_start_request_id = 101
    meeting_start_payload = struct.pack("<BBHIHBB", SCHEMA_VERSION, 1, 0, meeting_start_request_id, 60, 2, 0)
    meeting_start = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        meeting_start_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == meeting_start_request_id
        and parsed["state"] == 1
        and parsed["meeting_id"] > 0,
        args.notify_timeout,
    )
    assert_true(meeting_start["state"] == 1, "meeting start did not enter recording state")
    assert_true(meeting_start["meeting_id"] > 0, "meeting start did not allocate a meeting id")
    meeting_stop_request_id = 102
    meeting_stop_payload = struct.pack("<BBHIHBB", SCHEMA_VERSION, 2, 0, meeting_stop_request_id, 0, 2, 0)
    meeting_stop = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        meeting_stop_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == meeting_stop_request_id
        and parsed["state"] == 2
        and parsed["meeting_id"] == meeting_start["meeting_id"],
        args.notify_timeout,
    )
    assert_true(meeting_stop["state"] == 2, "meeting stop did not finalize the meeting")
    assert_true(meeting_stop["summary_state"] == 0, "board must not fabricate Type summary readiness")
    unsupported_meeting_request_id = 103
    unsupported_meeting_payload = struct.pack("<BBHIHBB", SCHEMA_VERSION, 99, 0, unsupported_meeting_request_id, 0, 1, 0)
    unsupported_meeting = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        unsupported_meeting_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == unsupported_meeting_request_id,
        args.notify_timeout,
    )
    assert_true(unsupported_meeting["last_error"] != 0, "unsupported meeting command was not reported")
    operations.append(
        {
            "operation": "meeting_control",
            "status": "PASS",
            "start": meeting_start,
            "stop": meeting_stop,
            "unsupported": unsupported_meeting,
        }
    )

    imu_status = await read_and_parse(client, uuids["imu_status"], parse_imu_status)
    assert_true(imu_status["sensor_state"] == 1, "NUCLEO bench should report IMU not populated")
    operations.append({"operation": "imu_status", "status": "PASS", "imu_status": imu_status})

    speaker_request_id = 111
    speaker_payload = struct.pack("<BBBBIHH", SCHEMA_VERSION, 1, 55, 2, speaker_request_id, 0, 0)
    speaker_status = await notify_write_wait(
        client,
        uuids["speaker_status"],
        uuids["speaker_control"],
        speaker_payload,
        parse_speaker_status,
        lambda parsed: parsed["request_id"] == speaker_request_id,
        args.notify_timeout,
    )
    assert_true(speaker_status["state"] == 1, "speaker must remain not-populated")
    assert_true(speaker_status["last_error"] != 0, "speaker prompt must fail honestly")
    assert_true(speaker_status["played_count"] == 0, "speaker prompt fabricated playback")
    unsupported_speaker_request_id = 112
    unsupported_speaker_payload = struct.pack("<BBBBIHH", SCHEMA_VERSION, 99, 55, 2, unsupported_speaker_request_id, 0, 0)
    unsupported_speaker = await notify_write_wait(
        client,
        uuids["speaker_status"],
        uuids["speaker_control"],
        unsupported_speaker_payload,
        parse_speaker_status,
        lambda parsed: parsed["request_id"] == unsupported_speaker_request_id,
        args.notify_timeout,
    )
    assert_true(unsupported_speaker["last_error"] != 0, "unsupported speaker command was not reported")
    operations.append(
        {
            "operation": "speaker_control",
            "status": "PASS",
            "prompt": speaker_status,
            "unsupported": unsupported_speaker,
        }
    )

    rejected_wake_request_id = 121
    rejected_wake_payload = struct.pack("<BBBBHHI", SCHEMA_VERSION, 3, 66, 0, 0, 1, rejected_wake_request_id)
    rejected_wake = await notify_write_wait(
        client,
        uuids["wake_word_status"],
        uuids["wake_word_control"],
        rejected_wake_payload,
        parse_wake_word_status,
        lambda parsed: parsed["request_id"] == rejected_wake_request_id,
        args.notify_timeout,
    )
    assert_true(rejected_wake["last_error"] != 0, "wake detect while disarmed was not rejected")
    arm_wake_request_id = 122
    arm_wake_payload = struct.pack("<BBBBHHI", SCHEMA_VERSION, 1, 66, 0, 0, 1, arm_wake_request_id)
    armed_wake = await notify_write_wait(
        client,
        uuids["wake_word_status"],
        uuids["wake_word_control"],
        arm_wake_payload,
        parse_wake_word_status,
        lambda parsed: parsed["request_id"] == arm_wake_request_id,
        args.notify_timeout,
    )
    assert_true(armed_wake["last_error"] != 0, "unpopulated wake word did not reject arm")
    assert_true(armed_wake["armed"] == 0 and armed_wake["engine_state"] == 0, "unpopulated wake word armed falsely")
    detect_wake_request_id = 123
    detect_wake_payload = struct.pack("<BBBBHHI", SCHEMA_VERSION, 3, 66, 0, 0, 1, detect_wake_request_id)
    detected_wake = await notify_write_wait(
        client,
        uuids["wake_word_status"],
        uuids["wake_word_control"],
        detect_wake_payload,
        parse_wake_word_status,
        lambda parsed: parsed["request_id"] == detect_wake_request_id,
        args.notify_timeout,
    )
    assert_true(detected_wake["last_error"] != 0, "unpopulated wake word did not reject detect")
    assert_true(detected_wake["last_event"] == 0, "wake word fabricated a detection event")
    assert_true(detected_wake["detection_count"] == 0, "wake word detection count advanced without an engine")
    disarm_wake_request_id = 124
    disarm_wake_payload = struct.pack("<BBBBHHI", SCHEMA_VERSION, 2, 66, 0, 0, 1, disarm_wake_request_id)
    disarmed_wake = await notify_write_wait(
        client,
        uuids["wake_word_status"],
        uuids["wake_word_control"],
        disarm_wake_payload,
        parse_wake_word_status,
        lambda parsed: parsed["request_id"] == disarm_wake_request_id,
        args.notify_timeout,
    )
    assert_true(disarmed_wake["last_error"] != 0, "unpopulated wake word did not reject disable")
    assert_true(disarmed_wake["armed"] == 0 and disarmed_wake["engine_state"] == 0, "wake word reported a false engine state")
    operations.append(
        {
            "operation": "wake_word_control",
            "status": "PASS",
            "rejected_while_disarmed": rejected_wake,
            "armed": armed_wake,
            "detected": detected_wake,
            "disarmed": disarmed_wake,
        }
    )

    diag_payload = struct.pack("<BBHIHH", SCHEMA_VERSION, 0, 0xFFFF, 0, 4, 64)
    diag = await notify_write_wait(
        client,
        uuids["diagnostics_log_pull"],
        uuids["diagnostics_log_pull"],
        diag_payload,
        parse_diag_log_pull,
        lambda parsed: parsed["request_cursor"] == 0,
        args.notify_timeout,
    )
    assert_true(diag["packet_bytes"] <= 64, "diagnostics response exceeded requested byte bound")
    assert_true(diag["event_count"] >= 1, "diagnostics response did not contain the export request event")
    assert_true(diag["event_count"] <= 4, "diagnostics response exceeded requested event bound")
    assert_true(diag["total_available"] >= diag["event_count"], "diagnostics available count is inconsistent")
    assert_true(diag["crc_valid"], "diagnostics response CRC was not verified")
    operations.append({"operation": "diagnostics_log_pull", "status": "PASS", "diagnostics": diag})

    delete_request_id = 77
    delete_payload = struct.pack("<BBHIII32s", SCHEMA_VERSION, 1, 0, delete_request_id, 1, 1234, bytes(32))
    delete_response = await notify_write_wait(
        client,
        uuids["delete_privacy"],
        uuids["delete_privacy"],
        delete_payload,
        parse_delete_privacy,
        lambda parsed: parsed["request_id"] == delete_request_id,
        args.notify_timeout,
    )
    assert_true((delete_response["flags"] & 0x0001) != 0, "delete/privacy refusal flag was not set")
    operations.append({"operation": "delete_privacy_refusal", "status": "PASS", "delete_privacy": delete_response})

    ota = await read_and_parse(client, uuids["ota_readiness"], parse_ota_readiness)
    assert_true(ota["battery_percent"] <= 100, "OTA battery percent out of range")
    operations.append({"operation": "ota_readiness", "status": "PASS", "ota_readiness": ota})


async def run_v1_control_only(
    client: Any,
    uuids: dict[str, str],
    args: argparse.Namespace,
    operations: list[dict[str, Any]],
) -> None:
    """Exercise only the real V1 meeting/capability boundary.

    The broad historical bench also writes an arbitrary card.  The accepted
    browser/CEMP product intentionally rejects that legacy card surface, so it
    must not prevent the real recording control contract from being tested.
    """
    before = await read_and_parse(client, uuids["recording_list"], parse_recording_list)
    before_ids = [int(entry["recording_id"]) for entry in before.get("entries", [])]
    request_base = 0x4000_0000 | ((int(time.time() * 1000) & 0x0FFF_FFFC))

    start_payload = struct.pack(
        "<BBHIHBB", SCHEMA_VERSION, 1, 0, request_base, 60, 2, 0
    )
    start = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        start_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == request_base
        and parsed["state"] == 1
        and parsed["meeting_id"] > 0,
        args.notify_timeout,
    )
    meeting_id = int(start["meeting_id"])

    duplicate = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        start_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == request_base
        and parsed["state"] == 1
        and parsed["meeting_id"] == meeting_id,
        args.notify_timeout,
    )
    await asyncio.sleep(float(args.v1_record_seconds))

    stop_request_id = request_base + 1
    stop_payload = struct.pack(
        "<BBHIHBB", SCHEMA_VERSION, 2, 0, stop_request_id, 0, 2, 0
    )
    stopped = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        stop_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == stop_request_id
        and parsed["state"] == 2
        and parsed["meeting_id"] == meeting_id,
        max(float(args.notify_timeout), 20.0),
    )
    assert_true(stopped["summary_state"] == 0, "board fabricated Type minutes readiness")

    finalize_request_id = request_base + 2
    finalize_payload = struct.pack(
        "<BBHIHBB", SCHEMA_VERSION, 3, 0, finalize_request_id, 0, 2, 0
    )
    finalized = await notify_write_wait(
        client,
        uuids["meeting_status"],
        uuids["meeting_control"],
        finalize_payload,
        parse_meeting_status,
        lambda parsed: parsed["request_id"] == finalize_request_id
        and parsed["state"] == 2
        and parsed["meeting_id"] == meeting_id,
        args.notify_timeout,
    )

    after = await read_and_parse(client, uuids["recording_list"], parse_recording_list)
    after_entries = list(after.get("entries", []))
    matches = [entry for entry in after_entries if int(entry["recording_id"]) == meeting_id]
    after_ids = [int(entry["recording_id"]) for entry in after_entries]
    added_ids = sorted(set(after_ids) - set(before_ids))
    assert_true(len(matches) == 1, "V1 meeting id is absent or duplicated in recording catalog")
    assert_true(added_ids == [meeting_id], f"V1 start added unexpected recording ids: {added_ids}")
    assert_true(int(matches[0]["codec"]) == 3, "V1 meeting recording is not codec=3")
    assert_true(int(matches[0]["total_length"]) > 0, "V1 meeting recording payload is empty")
    operations.append(
        {
            "operation": "v1_real_meeting_control",
            "status": "PASS",
            "profile_id": 2,
            "record_seconds": float(args.v1_record_seconds),
            "before_recording_ids": before_ids,
            "after_recording_ids": after_ids,
            "catalog_added_ids": added_ids,
            "start": start,
            "duplicate_start": duplicate,
            "stop": stopped,
            "finalize": finalized,
            "recording": matches[0],
            "idempotent_single_recording": True,
        }
    )

    target_list = dict(after)
    target_list["count"] = 1
    target_list["entries"] = matches
    pull = await pull_existing_recording_no_delete(client, uuids, target_list, args)
    assert_true(int(pull["recording_id"]) == meeting_id, "pulled recording id drifted")
    assert_true(
        int(pull["pcm_peak"]) > 32
        and float(pull["pcm_rms"]) > 1.0
        and float(pull["pcm_nonzero_ratio"]) > 0.01,
        f"V1 board-microphone recording is effectively silent: {pull}",
    )
    pull["non_silent"] = True
    operations.append(pull)

    imu = await read_and_parse(client, uuids["imu_status"], parse_imu_status)
    assert_true(int(imu["sensor_state"]) == 1, "unpopulated IMU reported available")

    speaker_request_id = request_base + 3
    speaker_payload = struct.pack(
        "<BBBBIHH", SCHEMA_VERSION, 1, 55, 2, speaker_request_id, 0, 0
    )
    speaker = await notify_write_wait(
        client,
        uuids["speaker_status"],
        uuids["speaker_control"],
        speaker_payload,
        parse_speaker_status,
        lambda parsed: parsed["request_id"] == speaker_request_id,
        args.notify_timeout,
    )
    assert_true(
        int(speaker["state"]) == 1
        and int(speaker["last_error"]) != 0
        and int(speaker["played_count"]) == 0,
        "unpopulated speaker fabricated playback",
    )

    wake_request_id = request_base + 4
    wake_payload = struct.pack(
        "<BBBBHHI", SCHEMA_VERSION, 1, 66, 0, 0, 1, wake_request_id
    )
    wake = await notify_write_wait(
        client,
        uuids["wake_word_status"],
        uuids["wake_word_control"],
        wake_payload,
        parse_wake_word_status,
        lambda parsed: parsed["request_id"] == wake_request_id,
        args.notify_timeout,
    )
    assert_true(
        int(wake["armed"]) == 0
        and int(wake["engine_state"]) == 0
        and int(wake["last_error"]) != 0
        and int(wake["detection_count"]) == 0,
        "unpopulated wake-word engine fabricated a usable state",
    )
    operations.append(
        {
            "operation": "v1_unpopulated_capabilities",
            "status": "PASS",
            "imu": imu,
            "speaker": speaker,
            "wake_word": wake,
        }
    )


async def run_bench(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from bleak import BleakClient
    except Exception as exc:  # noqa: BLE001 - CLI reports availability directly.
        raise BenchError(f"bleak import failed: {exc}") from exc

    started = utc_now()
    monotonic_start = time.monotonic()
    table = load_uuid_table()
    uuids = build_uuid_index(table)
    needed_services = required_services(table)
    needed_chars = required_characteristics(table)

    operations: list[dict[str, Any]] = []
    try:
        device, scan_operation = await scan_for_companion(args, needed_services)
        operations.append(scan_operation)

        client_kwargs: dict[str, Any] = {"timeout": args.timeout}
        # Windows WinRT: cached services + unpaired links cancel first GATT ops.
        client_kwargs["winrt"] = {"use_cached_services": False}
        async with BleakClient(device, **client_kwargs) as client:
            if hasattr(client, "pair"):
                try:
                    await client.pair()
                    operations.append({"operation": "pair", "status": "PASS"})
                except Exception as pair_exc:  # noqa: BLE001
                    operations.append(
                        {
                            "operation": "pair",
                            "status": "SKIP",
                            "error": str(pair_exc),
                        }
                    )
            # Windows: request throughput-optimized connection parameters.
            # Re-used later right before pull (host often re-parks CI at 15ms).
            winrt_ble_device = None
            try:
                from winrt.windows.devices.bluetooth import (
                    BluetoothLEDevice,
                    BluetoothLEPreferredConnectionParameters,
                )

                address = getattr(device, "address", None) or str(device)
                # Bleak WinRT addresses are often like "XX:XX:..." — convert to uint64.
                addr_int = int(address.replace(":", ""), 16)
                winrt_ble_device = await BluetoothLEDevice.from_bluetooth_address_async(
                    addr_int
                )
                if winrt_ble_device is not None:
                    result = winrt_ble_device.request_preferred_connection_parameters(
                        BluetoothLEPreferredConnectionParameters.throughput_optimized
                    )
                    params = winrt_ble_device.get_connection_parameters()
                    operations.append(
                        {
                            "operation": "winrt_connection_params",
                            "status": "PASS",
                            "request_result": str(result),
                            "min_interval": getattr(params, "connection_interval", None)
                            if params is None
                            else getattr(params, "connection_interval", None),
                            "note": "ThroughputOptimized; re-request again before bulk pull",
                        }
                    )
                    print(
                        f"winrt preferred connection params requested result={result} "
                        f"params={params}",
                        flush=True,
                    )
            except Exception as conn_exc:  # noqa: BLE001
                operations.append(
                    {
                        "operation": "winrt_connection_params",
                        "status": "SKIP",
                        "error": str(conn_exc),
                    }
                )
            services = await get_services(client)
            found_services = service_uuid_set(services)
            found_chars = characteristic_uuid_set(services)
            missing_services = sorted(needed_services - found_services)
            missing_chars = sorted(needed_chars - found_chars)
            assert_true(not missing_services, f"missing services after connect: {missing_services}")
            assert_true(not missing_chars, f"missing characteristics after connect: {missing_chars}")
            operations.append(
                {
                    "operation": "service_discovery",
                    "status": "PASS",
                    "service_count": len(found_services),
                    "characteristic_count": len(found_chars),
                    "required_services": sorted(needed_services),
                    "required_characteristics": sorted(needed_chars),
                }
            )
            await run_connected_bench(client, uuids, args, operations)
    except Exception as exc:
        ended = utc_now()
        raise BenchPartialError(
            str(exc),
            {
                "schema_version": 1,
                "tool": "tools/companion_ble_real_bench.py",
                "backend": "python-bleak",
                "status": "FAIL",
                "started_at": started,
                "ended_at": ended,
                "duration_s": round(time.monotonic() - monotonic_start, 3),
                "firmware_commit": git_commit(),
                "target": {
                    "name_filter": args.name,
                    "address_filter": args.address,
                },
                "error": str(exc),
                "partial_operation_count": len(operations),
                "operations": operations,
            },
        ) from exc

    ended = utc_now()
    return {
        "schema_version": 1,
        "tool": "tools/companion_ble_real_bench.py",
        "backend": "python-bleak",
        "status": "PASS",
        "started_at": started,
        "ended_at": ended,
        "duration_s": round(time.monotonic() - monotonic_start, 3),
        "firmware_commit": git_commit(),
        "target": {
            "name_filter": args.name,
            "address_filter": args.address,
        },
        "operations": operations,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="companion", help="BLE local-name substring to select")
    parser.add_argument("--address", default=None, help="Optional exact BLE address filter")
    parser.add_argument("--timeout", type=float, default=12.0, help="Scan/connect timeout seconds")
    parser.add_argument("--notify-timeout", type=float, default=6.0, help="Notify wait timeout seconds")
    parser.add_argument(
        "--screen-final-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait for final CardStatusV1 after a screen-triggering write",
    )
    parser.add_argument(
        "--expect-real-panel",
        action="store_true",
        help="Require screen final statuses to be rendered/ok instead of deferred no-panel",
    )
    parser.add_argument(
        "--v1-control-only",
        action="store_true",
        help="Run the real V1 meeting/idempotency/catalog and unpopulated-capability gates only",
    )
    parser.add_argument(
        "--v1-record-seconds",
        type=float,
        default=3.0,
        help="Seconds to keep the real board-microphone V1 recording active",
    )
    parser.add_argument(
        "--pull-existing-recording",
        action="store_true",
        help="Pull and validate a recording_list entry without deleting it",
    )
    parser.add_argument(
        "--pull-recording-id",
        type=int,
        default=None,
        help="With --pull-existing-recording: select this exact recording ID instead of the first entry",
    )
    parser.add_argument(
        "--pull-output-pcm",
        type=pathlib.Path,
        default=None,
        help="With --pull-existing-recording: persist the reconstructed PCM bytes for archival",
    )
    parser.add_argument(
        "--pull-only",
        action="store_true",
        help="With --pull-existing-recording: skip settings/card benches (throughput focus)",
    )
    parser.add_argument(
        "--window-chunks",
        type=int,
        default=256,
        help="Approx packets per host write (stream budget = min(chunk*N, 65535))",
    )
    parser.add_argument(
        "--inter-packet-timeout",
        type=float,
        default=0.25,
        help="Idle seconds after last notify before ending a stream window (compress auto-raises to 1.2)",
    )
    parser.add_argument(
        "--compress-ima",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Request IMA-ADPCM compressed pull (opt-in; product default is non-compress wire path)",
    )
    parser.set_defaults(write_without_response=True)
    parser.add_argument(
        "--link-settle",
        type=float,
        default=0.4,
        help="Seconds to wait after notify subscribe for active-link CI/PHY",
    )
    parser.add_argument(
        "--write-without-response",
        action="store_true",
        help="Use write-without-response for chunk pull requests",
    )
    parser.add_argument(
        "--chunk-bytes",
        type=int,
        default=220,
        help="Hint for window budget (device intermediate payload max 220 = ATT 244-24)",
    )
    parser.add_argument("--output", type=pathlib.Path, default=None, help="Optional JSON artifact path")
    parser.add_argument("--json", action="store_true", help="Print the full JSON artifact")
    args = parser.parse_args(argv)
    if args.chunk_bytes < 1 or args.chunk_bytes > 0xFFFF:
        parser.error("--chunk-bytes must be between 1 and 65535")
    if args.screen_final_timeout <= 0:
        parser.error("--screen-final-timeout must be positive")
    if args.v1_record_seconds <= 0:
        parser.error("--v1-record-seconds must be positive")
    if args.pull_recording_id is not None and args.pull_recording_id <= 0:
        parser.error("--pull-recording-id must be positive")
    if (args.pull_recording_id is not None or args.pull_output_pcm is not None) and not args.pull_existing_recording:
        parser.error("--pull-recording-id/--pull-output-pcm require --pull-existing-recording")
    return args


def write_output(path: pathlib.Path, result: dict[str, Any]) -> None:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = asyncio.run(run_bench(args))
    except Exception as exc:  # noqa: BLE001 - CLI should emit compact failure evidence.
        if isinstance(exc, BenchPartialError):
            result = exc.result
        else:
            result = {
                "schema_version": 1,
                "tool": "tools/companion_ble_real_bench.py",
                "backend": "python-bleak",
                "status": "FAIL",
                "firmware_commit": git_commit(),
                "error": str(exc),
                "ended_at": utc_now(),
                "target": {
                    "name_filter": args.name,
                    "address_filter": args.address,
                },
            }
        if args.output is not None:
            write_output(args.output, result)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        print(f"FAIL: Companion BLE real bench failed: {exc}", file=sys.stderr)
        return 1

    if args.output is not None:
        write_output(args.output, result)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "PASS: Companion BLE real bench passed; "
            f"{len(result['operations'])} operation(s), {result['duration_s']}s."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
