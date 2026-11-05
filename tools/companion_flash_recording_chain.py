#!/usr/bin/env python3
"""Exercise the real Companion recording -> QSPI flash -> BLE pull chain."""

from __future__ import annotations

import argparse
import asyncio
import binascii
import datetime as dt
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys
import threading
import time
import traceback
import wave
from typing import Any, Callable

from companion_ble_connect_with_serial import SerialMonitor, resolve_serial_port


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE_PATH = REPO_ROOT / "docs" / "ble_uuid_table.json"
SCHEMA_VERSION = 1
RECORDING_ERROR_FLAG = 0x80
RECORDING_FINAL_FLAG = 0x01
RECORDING_SOURCE_MIC_SAI = 1
PCM_SAMPLE_RATE = 16000
PCM_CHANNELS = 1
PCM_WIDTH_BYTES = 2


class ChainError(RuntimeError):
    """A validation failure with enough context for the artifact."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def write_wav(path: pathlib.Path, pcm_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_WIDTH_BYTES)
        wav_file.setframerate(PCM_SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)


def analyze_pcm16(pcm_bytes: bytes, args: argparse.Namespace) -> dict[str, Any]:
    if len(pcm_bytes) % PCM_WIDTH_BYTES != 0:
        raise ChainError(f"PCM16 payload length is not even: {len(pcm_bytes)}")

    sample_count = len(pcm_bytes) // PCM_WIDTH_BYTES
    if sample_count == 0:
        raise ChainError("PCM16 payload is empty")

    samples = struct.unpack("<" + "h" * sample_count, pcm_bytes)
    abs_samples = [abs(value) for value in samples]
    rms = math.sqrt(sum(float(value) * float(value) for value in samples) / sample_count)
    clipping_count = sum(1 for value in samples if abs(value) >= 32760)
    zero_count = sum(1 for value in samples if value == 0)
    duration_s = sample_count / float(PCM_SAMPLE_RATE)
    clipping_ratio = clipping_count / float(sample_count)
    zero_ratio = zero_count / float(sample_count)
    sorted_abs = sorted(abs_samples)
    p95 = sorted_abs[int((sample_count - 1) * 0.95)]
    p99 = sorted_abs[int((sample_count - 1) * 0.99)]
    warnings = []
    if duration_s < float(args.min_duration_s):
        warnings.append("duration_below_min")
    if rms < float(args.min_rms):
        warnings.append("rms_below_min")
    if rms > float(args.max_rms):
        warnings.append("rms_above_max")
    if clipping_ratio > float(args.max_clipping_ratio):
        warnings.append("clipping_above_max")

    return {
        "operation": "audio_quality",
        "status": "WARNING" if warnings else "PASS",
        "sample_rate_hz": PCM_SAMPLE_RATE,
        "channels": PCM_CHANNELS,
        "sample_width_bytes": PCM_WIDTH_BYTES,
        "sample_count": sample_count,
        "duration_s": round(duration_s, 4),
        "peak": max(abs_samples),
        "rms": round(rms, 2),
        "p95_abs": p95,
        "p99_abs": p99,
        "zero_ratio": round(zero_ratio, 6),
        "clipping_ratio": round(clipping_ratio, 6),
        "warning_thresholds": {
            "min_duration_s": float(args.min_duration_s),
            "min_rms": float(args.min_rms),
            "max_rms": float(args.max_rms),
            "max_clipping_ratio": float(args.max_clipping_ratio),
        },
        "warnings": warnings,
    }


def start_playback_fixture(args: argparse.Namespace) -> tuple[threading.Thread | None, dict[str, Any] | None]:
    if args.play_audio_path is None:
        return None, None

    path = args.play_audio_path
    result: dict[str, Any] = {
        "operation": "playback_fixture",
        "status": "STARTED",
        "path": str(path),
        "delay_s": float(args.play_delay_s),
    }
    if not path.exists():
        result["status"] = "FAIL"
        result["error"] = f"playback WAV not found: {path}"
        return None, result

    def worker() -> None:
        try:
            time.sleep(max(0.0, float(args.play_delay_s)))
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
            result["status"] = "PASS"
            result["finished_at"] = utc_now()
        except Exception as exc:  # noqa: BLE001
            result["status"] = "FAIL"
            result["error"] = str(exc)

    thread = threading.Thread(target=worker, name="companion-recording-playback-fixture", daemon=True)
    thread.start()
    return thread, result


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


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
    except Exception as exc:  # noqa: BLE001
        raise ChainError(f"bleak import failed: {exc}") from exc

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
        raise ChainError(f"no Companion candidate found; seen={seen}")

    def score(candidate: tuple[Any, Any | None, list[str], int | None, str]) -> tuple[int, int]:
        device, _adv, adv_uuids, rssi, name = candidate
        address = str(getattr(device, "address", ""))
        return (
            100 if target_address and normalize_address(address) == target_address else 0
        ) + (
            20 if target_name and target_name in name.lower() else 0
        ) + len(required.intersection(adv_uuids)), int(rssi if rssi is not None else -999)

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


def parse_struct(fmt: str, names: tuple[str, ...], payload: bytes) -> dict[str, Any]:
    size = struct.calcsize(fmt)
    if len(payload) < size:
        raise ChainError(f"payload too short: got {len(payload)}, need {size}")
    values = struct.unpack(fmt, payload[:size])
    parsed = dict(zip(names, values, strict=True))
    if parsed.get("schema_version") != SCHEMA_VERSION:
        raise ChainError(f"unexpected schema_version={parsed.get('schema_version')}")
    return parsed


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
        raise ChainError(
            f"unexpected recording list entry_bytes={header['entry_bytes']} expected={expected_entry_size}"
        )
    offset = struct.calcsize("<BBH")
    for _index in range(int(header["count"])):
        if len(payload) < offset + expected_entry_size:
            raise ChainError("recording_list entry truncated")
        values = struct.unpack(entry_fmt, payload[offset:offset + expected_entry_size])
        entry = {
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
        entries.append(entry)
        offset += expected_entry_size
    header["entries"] = entries
    header["raw_length"] = len(payload)
    return header


def parse_recording_chunk(payload: bytes) -> dict[str, Any]:
    header_fmt = "<BBHIIIII32s"
    header_size = struct.calcsize(header_fmt)
    parsed = parse_struct(
        header_fmt,
        (
            "schema_version",
            "flags",
            "payload_length",
            "recording_id",
            "packet_sequence",
            "byte_offset",
            "total_length",
            "packet_crc32",
            "final_sha256",
        ),
        payload,
    )
    payload_length = int(parsed["payload_length"])
    if len(payload) < header_size + payload_length:
        raise ChainError("recording chunk payload truncated")
    parsed["payload"] = payload[header_size:header_size + payload_length]
    parsed["final_sha256"] = bytes(parsed["final_sha256"]).hex()
    parsed["packet_crc32_hex"] = f"0x{int(parsed['packet_crc32']) & 0xFFFFFFFF:08x}"
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
    parsed["validated_sha256"] = bytes(parsed["validated_sha256"]).hex()
    return parsed


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
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=max(0.1, deadline - time.monotonic()))
            except asyncio.TimeoutError as exc:
                raise ChainError(f"notify timeout on {notify_uuid}; last={last}") from exc
            parsed = parser(raw)
            last = parsed
            if predicate(parsed):
                return parsed
        raise ChainError(f"notify predicate not satisfied on {notify_uuid}; last={last}")
    finally:
        await client.stop_notify(notify_uuid)


async def read_recording_list(client: Any, uuid: str) -> dict[str, Any]:
    return parse_recording_list(bytes(await client.read_gatt_char(uuid)))


def control_payload(command: int, request_id: int, max_seconds: int, profile_id: int = 2) -> bytes:
    # profile_id=2 -> live board-mic air path (real speaker->mic capture);
    # profile_id=1 -> synthetic auto_fill (stored speech source, wire/storage test only).
    return struct.pack("<BBBBIH", SCHEMA_VERSION, command, profile_id, 0, request_id, max_seconds)


def verify_packet_crc(packet: dict[str, Any]) -> str:
    header = struct.pack(
        "<IIII",
        int(packet["recording_id"]),
        int(packet["packet_sequence"]),
        int(packet["byte_offset"]),
        int(packet["total_length"]),
    )
    crc = binascii.crc32(header + bytes(packet["payload"])) & 0xFFFFFFFF
    expected = int(packet["packet_crc32"]) & 0xFFFFFFFF
    if crc != expected:
        raise ChainError(f"packet CRC mismatch: got 0x{crc:08x}, expected 0x{expected:08x}")
    return f"0x{crc:08x}"


async def pull_recording(
    client: Any,
    uuids: dict[str, str],
    entry: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[dict[str, Any], bytes]:
    offset = 0
    expected_sequence = 0
    total_length = int(entry["total_length"])
    recording_id = int(entry["recording_id"])
    data = bytearray()
    packets: list[dict[str, Any]] = []
    final_sha256 = ""

    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(_sender: Any, raw: bytearray) -> None:
        queue.put_nowait(bytes(raw))

    await client.start_notify(uuids["recording_chunk_pull"], callback)
    try:
        await asyncio.sleep(0.15)
        while offset < total_length:
            request_length = min(args.chunk_bytes, total_length - offset)
            request = struct.pack("<BBHIII", SCHEMA_VERSION, 0, request_length, recording_id, offset, 0)
            await client.write_gatt_char(uuids["recording_chunk_pull"], request, response=True)
            deadline = time.monotonic() + float(args.notify_timeout)
            packet: dict[str, Any] | None = None
            last: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(queue.get(), timeout=max(0.1, deadline - time.monotonic()))
                except asyncio.TimeoutError as exc:
                    raise ChainError(f"recording chunk notify timeout at offset={offset}; last={last}") from exc
                parsed = parse_recording_chunk(raw)
                last = parsed
                if int(parsed["byte_offset"]) == offset:
                    packet = parsed
                    break
            if packet is None:
                raise ChainError(f"recording chunk notify predicate not satisfied at offset={offset}; last={last}")
            if int(packet["flags"]) & RECORDING_ERROR_FLAG:
                raise ChainError(f"recording chunk error flag at offset={offset}: {packet}")
            if int(packet["packet_sequence"]) != expected_sequence:
                raise ChainError(
                    f"packet sequence mismatch: got {packet['packet_sequence']} expected {expected_sequence}"
                )
            if int(packet["total_length"]) != total_length:
                raise ChainError("recording total_length changed during transfer")
            payload = bytes(packet["payload"])
            if len(payload) != int(packet["payload_length"]):
                raise ChainError("recording payload_length mismatch")
            packet_crc = verify_packet_crc(packet)
            data.extend(payload)
            packet_summary = {
                "packet_sequence": int(packet["packet_sequence"]),
                "byte_offset": int(packet["byte_offset"]),
                "payload_length": int(packet["payload_length"]),
                "packet_crc32": packet_crc,
                "flags": int(packet["flags"]),
            }
            packets.append(packet_summary)
            offset += len(payload)
            expected_sequence += 1
            if int(packet["flags"]) & RECORDING_FINAL_FLAG:
                final_sha256 = str(packet["final_sha256"])
                break
    finally:
        await client.stop_notify(uuids["recording_chunk_pull"])

    if len(data) != total_length:
        raise ChainError(f"recording byte count mismatch: got {len(data)}, expected {total_length}")
    computed_sha256 = hashlib.sha256(data).hexdigest()
    if not final_sha256:
        raise ChainError("final recording packet did not include SHA-256")
    if final_sha256 != computed_sha256:
        raise ChainError(f"final SHA mismatch: device={final_sha256} host={computed_sha256}")
    if not computed_sha256.startswith(str(entry["sha256_prefix"])):
        raise ChainError("recording_list sha256_prefix did not match pulled object")
    host_crc32 = f"0x{binascii.crc32(data) & 0xFFFFFFFF:08x}"
    if host_crc32.lower() != str(entry["content_crc32"]).lower():
        raise ChainError(f"recording_list CRC mismatch: list={entry['content_crc32']} host={host_crc32}")

    return (
        {
            "operation": "recording_pull",
            "status": "PASS",
            "recording_id": recording_id,
            "total_length": total_length,
            "packet_count": len(packets),
            "packets": packets,
            "host_sha256": computed_sha256,
            "device_final_sha256": final_sha256,
            "host_crc32": host_crc32,
        },
        bytes(data),
    )


async def run_chain(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from bleak import BleakClient
    except Exception as exc:  # noqa: BLE001
        raise ChainError(f"bleak import failed: {exc}") from exc

    started = utc_now()
    monotonic_start = time.monotonic()
    artifact_dir = resolve_artifact_dir(args.artifact_dir)
    table = load_uuid_table()
    uuids = build_uuid_index(table)
    operations: list[dict[str, Any]] = []
    monitor: SerialMonitor | None = None
    serial_raw_log = artifact_dir / "flash-recording-serial.log"
    pcm_path = artifact_dir / "ble-recording.pcm"
    wav_path = artifact_dir / "ble-recording-16k-mono.wav"

    try:
        if not args.no_serial_monitor:
            try:
                port, present_ports = resolve_serial_port(args.serial_port)
                monitor = SerialMonitor(port, int(args.baud), serial_raw_log)
                monitor.start()
                operations.append(
                    {
                        "operation": "serial_monitor_start",
                        "status": "PASS",
                        "port": port,
                        "baud": int(args.baud),
                        "raw_log": str(serial_raw_log),
                        "present_ports": present_ports,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                operations.append(
                    {
                        "operation": "serial_monitor_start",
                        "status": "WARNING",
                        "error": str(exc),
                        "raw_log": str(serial_raw_log),
                    }
                )

        device, scan = await scan_for_companion(args, required_services(table))
        operations.append(scan)

        async with BleakClient(device, timeout=args.timeout) as client:
            start_request_id = 501
            start_echo = await notify_write_wait(
                client,
                uuids["recording_control"],
                uuids["recording_control"],
                control_payload(1, start_request_id, max(1, int(args.record_seconds) + 1), profile_id=args.profile),
                parse_recording_control,
                lambda parsed: parsed["request_id"] == start_request_id,
                args.notify_timeout,
            )
            if int(start_echo["privacy_flags"]) & RECORDING_ERROR_FLAG:
                raise ChainError(f"recording start was rejected: {start_echo}")
            operations.append({"operation": "recording_start", "status": "PASS", "echo": start_echo})
            playback_thread, playback_result = start_playback_fixture(args)
            if playback_result is not None and playback_result.get("status") == "FAIL":
                operations.append(playback_result)
                raise ChainError(str(playback_result.get("error", "playback fixture failed")))

            await asyncio.sleep(args.record_seconds)
            if playback_thread is not None:
                playback_thread.join(timeout=2.0)
            if playback_result is not None:
                if playback_result.get("status") == "STARTED":
                    playback_result["status"] = "WARNING"
                    playback_result["warning"] = "playback fixture was still running when recording dwell ended"
                operations.append(playback_result)
                if playback_result.get("status") == "FAIL":
                    raise ChainError(str(playback_result.get("error", "playback fixture failed")))

            stop_request_id = 502
            stop_echo = await notify_write_wait(
                client,
                uuids["recording_control"],
                uuids["recording_control"],
                control_payload(2, stop_request_id, 0),
                parse_recording_control,
                lambda parsed: parsed["request_id"] == stop_request_id,
                args.notify_timeout,
            )
            if int(stop_echo["privacy_flags"]) & RECORDING_ERROR_FLAG:
                raise ChainError(f"recording stop/store was rejected: {stop_echo}")
            operations.append({"operation": "recording_stop_store", "status": "PASS", "echo": stop_echo})

            recording_list = await read_recording_list(client, uuids["recording_list"])
            if int(recording_list["count"]) != 1:
                raise ChainError(f"expected one recording after stop, got {recording_list}")
            entry = recording_list["entries"][0]
            if int(entry["source_mode"]) != RECORDING_SOURCE_MIC_SAI:
                raise ChainError(f"recording was not sourced from SAI microphone path: {entry}")
            if int(entry["total_length"]) <= 0:
                raise ChainError(f"recording total_length was empty: {entry}")
            operations.append({"operation": "recording_list_after_stop", "status": "PASS", "recording_list": recording_list})

            pull, pcm_bytes = await pull_recording(client, uuids, entry, args)
            operations.append(pull)
            pcm_path.write_bytes(pcm_bytes)
            write_wav(wav_path, pcm_bytes)
            quality = analyze_pcm16(pcm_bytes, args)
            quality["pcm_path"] = str(pcm_path)
            quality["wav_path"] = str(wav_path)
            operations.append(
                {
                    "operation": "audio_export",
                    "status": "PASS",
                    "pcm_path": str(pcm_path),
                    "wav_path": str(wav_path),
                    "sample_rate_hz": PCM_SAMPLE_RATE,
                    "channels": PCM_CHANNELS,
                    "sample_width_bytes": PCM_WIDTH_BYTES,
                    "byte_count": len(pcm_bytes),
                }
            )
            operations.append(quality)

            delete_request_id = 503
            delete_payload = struct.pack(
                "<BBHIII32s",
                SCHEMA_VERSION,
                1,
                0,
                delete_request_id,
                int(entry["recording_id"]),
                int(entry["total_length"]),
                bytes.fromhex(str(pull["host_sha256"])),
            )
            delete_response = await notify_write_wait(
                client,
                uuids["delete_privacy"],
                uuids["delete_privacy"],
                delete_payload,
                parse_delete_privacy,
                lambda parsed: parsed["request_id"] == delete_request_id,
                args.notify_timeout,
            )
            if int(delete_response["flags"]) & 0x0001:
                raise ChainError(f"delete-after-sync was refused: {delete_response}")
            operations.append({"operation": "delete_after_sync", "status": "PASS", "delete_privacy": delete_response})

            list_after_delete = await read_recording_list(client, uuids["recording_list"])
            if int(list_after_delete["count"]) != 0:
                raise ChainError(f"recording_list not empty after delete: {list_after_delete}")
            operations.append({"operation": "recording_list_after_delete", "status": "PASS", "recording_list": list_after_delete})

        return {
            "schema_version": 1,
            "status": "PASS",
            "started_at": started,
            "finished_at": utc_now(),
            "duration_s": round(time.monotonic() - monotonic_start, 3),
            "git_commit": git_commit(),
            "mode": "real_ble_recording_to_qspi_flash_chain",
            "artifacts": {
                "artifact_dir": str(artifact_dir),
                "pcm_path": str(pcm_path),
                "wav_path": str(wav_path),
                "serial_log": str(serial_raw_log),
            },
            "operations": operations,
        }
    finally:
        if monitor is not None:
            monitor.stop()
            operations.append(
                {
                    "operation": "serial_monitor_stop",
                    "status": "PASS",
                    "line_count": len(monitor.lines),
                    "tail": monitor.lines[-80:],
                    "raw_log": str(serial_raw_log),
                }
            )


def resolve_artifact_dir(artifact_dir: pathlib.Path | None) -> pathlib.Path:
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = REPO_ROOT / ".cache" / "validation" / f"companion-flash-recording-chain-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_artifact(result: dict[str, Any], artifact_dir: pathlib.Path | None) -> pathlib.Path:
    artifact_dir = resolve_artifact_dir(artifact_dir)
    path = artifact_dir / "companion-flash-recording-chain.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="companion", help="BLE local name substring")
    parser.add_argument("--address", default="", help="Optional BLE address")
    parser.add_argument("--timeout", type=float, default=8.0, help="BLE scan/connect timeout")
    parser.add_argument("--notify-timeout", type=float, default=15.0, help="GATT notify timeout")
    parser.add_argument("--record-seconds", type=float, default=1.0, help="User recording dwell time before stop")
    parser.add_argument("--profile", type=int, default=2, help="Recording profile: 2=live board-mic air (default, real speaker->mic), 1=synthetic auto_fill")
    parser.add_argument("--chunk-bytes", type=int, default=160, help="Requested recording bytes per BLE pull")
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=None, help="Directory for JSON evidence")
    parser.add_argument("--play-audio-path", type=pathlib.Path, default=None, help="Optional WAV to play after recording starts")
    parser.add_argument("--play-delay-s", type=float, default=0.6, help="Delay before optional playback fixture starts")
    parser.add_argument("--serial-port", default="", help="Optional ST-LINK VCP serial port")
    parser.add_argument("--baud", type=int, default=115200, help="ST-LINK VCP baud rate")
    parser.add_argument("--no-serial-monitor", action="store_true", help="Do not capture ST-LINK VCP logs during recording")
    parser.add_argument("--min-duration-s", type=float, default=0.5, help="Audio quality warning threshold for short captures")
    parser.add_argument("--min-rms", type=float, default=8.0, help="Audio quality warning threshold for near-silence")
    parser.add_argument("--max-rms", type=float, default=12000.0, help="Audio quality warning threshold for overly hot captures")
    parser.add_argument("--max-clipping-ratio", type=float, default=0.02, help="Audio quality warning threshold for clipped samples")
    return parser


async def async_main(args: argparse.Namespace) -> int:
    args.artifact_dir = resolve_artifact_dir(args.artifact_dir)
    result: dict[str, Any]
    try:
        result = await run_chain(args)
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "finished_at": utc_now(),
            "git_commit": git_commit(),
            "error": str(exc),
            "error_repr": repr(exc),
            "traceback": traceback.format_exc(),
        }
        path = write_artifact(result, args.artifact_dir)
        print(f"FAIL: Companion flash recording chain failed; artifact={path}")
        print(str(exc))
        return 1

    path = write_artifact(result, args.artifact_dir)
    print(f"PASS: Companion flash recording chain passed; artifact={path}")
    return 0


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
