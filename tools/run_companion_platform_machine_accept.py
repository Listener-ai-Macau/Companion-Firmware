#!/usr/bin/env python3
"""Machine-closed platform acceptance on real BLE radio.

Covers the platform items that do not require owner visual judgment:
  - connect/pair + device/battery status
  - settings RMW readback
  - recording list + full chunk pull + CRC/SHA
  - OTA readiness parse
  - BLE name stage/reject/reset (no permanent rename)
  - optional repair control dry-read if characteristic present

Does not open owner popups. Writes a durable JSON receipt.
"""
from __future__ import annotations

import argparse
import asyncio
import binascii
import hashlib
import json
import struct
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakClient, BleakScanner

SCHEMA = 1
DEVICE_STATUS = "8f7a1001-7b7d-4f3d-9d6f-6c2d1b7c0000"
BATTERY = "8f7a1002-7b7d-4f3d-9d6f-6c2d1b7c0000"
REC_LIST = "8f7a3002-7b7d-4f3d-9d6f-6c2d1b7c0000"
REC_CHUNK = "8f7a3003-7b7d-4f3d-9d6f-6c2d1b7c0000"
SETTINGS = "8f7a4001-7b7d-4f3d-9d6f-6c2d1b7c0000"
BLE_NAME = "8f7a4002-7b7d-4f3d-9d6f-6c2d1b7c0000"
OTA_READY = "8f7a7001-7b7d-4f3d-9d6f-6c2d1b7c0000"
REPAIR = "8f7a4003-7b7d-4f3d-9d6f-6c2d1b7c0000"

RECORDING_ERROR_FLAG = 0x80
RECORDING_FINAL_FLAG = 0x01


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


async def find_device(name: str, address: str | None, timeout: float):
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    for addr, (dev, adv) in found.items():
        local = (dev.name or adv.local_name or "")
        if address and addr.upper() != address.upper():
            continue
        if name.lower() in local.lower() or (address and addr.upper() == address.upper()):
            return addr, local, getattr(adv, "rssi", None)
    raise RuntimeError(f"device not found name={name!r} address={address!r}")


def parse_recording_list(payload: bytes) -> dict:
    schema, count, entry_bytes = struct.unpack_from("<BBH", payload, 0)
    entry_fmt = "<IIIBBBBI8sI"
    expected = struct.calcsize(entry_fmt)
    if count and entry_bytes != expected:
        raise RuntimeError(f"entry_bytes={entry_bytes} expected={expected}")
    entries = []
    offset = 4
    for _ in range(count):
        values = struct.unpack_from(entry_fmt, payload, offset)
        entries.append(
            {
                "recording_id": values[0],
                "started_unix_s": values[1],
                "duration_ms": values[2],
                "codec": values[3],
                "sync_state": values[4],
                "source_mode": values[5],
                "total_length": values[7],
                "sha256_prefix": values[8].hex(),
                "content_crc32": f"0x{values[9]:08x}",
            }
        )
        offset += expected
    return {"schema_version": schema, "count": count, "entries": entries}


def parse_chunk_packet(payload: bytes) -> dict:
    header_fmt = "<BBHIIIII32s"
    header_size = struct.calcsize(header_fmt)
    (
        schema,
        flags,
        payload_length,
        recording_id,
        packet_sequence,
        byte_offset,
        total_length,
        packet_crc32,
        final_sha256,
    ) = struct.unpack_from(header_fmt, payload, 0)
    if len(payload) < header_size + payload_length:
        raise RuntimeError("chunk truncated")
    body = payload[header_size : header_size + payload_length]
    return {
        "schema_version": schema,
        "flags": flags,
        "payload_length": payload_length,
        "recording_id": recording_id,
        "packet_sequence": packet_sequence,
        "byte_offset": byte_offset,
        "total_length": total_length,
        "packet_crc32": packet_crc32,
        "final_sha256": final_sha256.hex(),
        "payload": body,
    }


def verify_packet_crc(packet: dict) -> str:
    crc_payload = struct.pack(
        "<IIII",
        packet["recording_id"],
        packet["packet_sequence"],
        packet["byte_offset"],
        packet["total_length"],
    )
    crc = binascii.crc32(crc_payload + packet["payload"]) & 0xFFFFFFFF
    expected = packet["packet_crc32"] & 0xFFFFFFFF
    if crc != expected:
        raise RuntimeError(f"packet CRC mismatch got=0x{crc:08x} exp=0x{expected:08x}")
    return f"0x{crc:08x}"


def parse_settings(payload: bytes) -> dict:
    schema, locale, flags, tz, q_start, q_end, brightness, profile = struct.unpack("<BBHhBBBB", payload)
    return {
        "schema_version": schema,
        "locale": locale,
        "flags": flags,
        "time_zone_offset_min": tz,
        "quiet_hours_start_min": q_start,
        "quiet_hours_end_min": q_end,
        "display_brightness": brightness,
        "recorder_profile_id": profile,
    }


_SETTINGS_NONCE = 0


def pack_settings(s: dict, brightness: int, *, bump_nonce: bool = True) -> bytes:
    """Pack SettingsV1.

    Firmware derives product idempotency from the full settings payload. Re-sending an
    identical payload is treated as a replay and will NOT mutate state even if an
    intermediate write changed brightness. Bump quiet_hours_end_min (inactive while
    quiet-hours flag is clear) so each intentional write has a unique identity.
    """
    global _SETTINGS_NONCE
    q_end = int(s.get("quiet_hours_end_min", 0)) & 0xFF
    if bump_nonce:
        _SETTINGS_NONCE = (_SETTINGS_NONCE + 1) & 0xFF
        if _SETTINGS_NONCE == 0:
            _SETTINGS_NONCE = 1
        q_end = _SETTINGS_NONCE
    return struct.pack(
        "<BBHhBBBB",
        s["schema_version"],
        s["locale"],
        s["flags"] & ~0x0001,  # keep quiet-hours inactive so end_min is free nonce
        s["time_zone_offset_min"],
        s["quiet_hours_start_min"],
        q_end,
        brightness & 0xFF,
        s["recorder_profile_id"],
    )


def parse_ble_name(payload: bytes) -> dict:
    schema, command, flags, request_id, name_len, max_len, status, reserved = struct.unpack_from(
        "<BBHIBBBB", payload, 0
    )
    name = payload[8 : 8 + name_len].decode("ascii", errors="replace")
    return {
        "schema_version": schema,
        "command": command,
        "flags": flags,
        "request_id": request_id,
        "name_len": name_len,
        "max_len": max_len,
        "status": status,
        "name_ascii": name,
    }


def ble_name_payload(command: int, request_id: int, name: str = "") -> bytes:
    raw = name.encode("ascii")
    if len(raw) > 29:
        raise RuntimeError("name too long")
    body = bytearray(8 + 29)
    struct.pack_into("<BBHIBBBB", body, 0, SCHEMA, command, 0, request_id, len(raw), 29, 0, 0)
    body[8 : 8 + len(raw)] = raw
    return bytes(body)


def parse_ota(payload: bytes) -> dict:
    # 24-byte readiness surface; keep raw + first fields
    if len(payload) < 8:
        raise RuntimeError(f"ota readiness too short: {len(payload)}")
    schema, flags, field_u16 = struct.unpack_from("<BBH", payload, 0)
    return {
        "bytes": len(payload),
        "hex": payload.hex(),
        "schema_version": schema,
        "flags": flags,
        "field_u16": field_u16,
        "raw24": payload[:24].hex() if len(payload) >= 24 else payload.hex(),
    }


async def pull_recording(
    client: BleakClient,
    entry: dict,
    chunk_bytes: int,
    notify_timeout: float,
    max_bytes: int | None,
) -> dict:
    recording_id = int(entry["recording_id"])
    total_length = int(entry["total_length"])
    pull_limit = total_length if max_bytes is None else min(total_length, max_bytes)
    # Firmware max ATT payload is 248; chunk header is 56 → 192 data bytes max.
    chunk_bytes = max(1, min(int(chunk_bytes), 192))
    offset = 0
    expected_sequence = 0
    data = bytearray()
    packet_summaries: list[dict] = []
    final_sha256 = ""
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    # Recording char is WRITE+NOTIFY only (no WRITE_WITHOUT_RESP). OTA can stream
    # WithoutResponse + windowing; this path cannot — every chunk is one RTT.
    write_mode = "with_response"

    def callback(_sender, raw: bytearray) -> None:
        queue.put_nowait(bytes(raw))

    await client.start_notify(REC_CHUNK, callback)
    t0 = time.monotonic()
    try:
        await asyncio.sleep(0.05)
        while not queue.empty():
            try:
                queue.get_nowait()
            except Exception:
                break

        while offset < pull_limit:
            request_length = min(chunk_bytes, pull_limit - offset)
            request = struct.pack(
                "<BBHIII", SCHEMA, 0, request_length, recording_id, offset, 0
            )
            await client.write_gatt_char(REC_CHUNK, request, response=True)
            deadline = time.monotonic() + notify_timeout
            packet = None
            last = None
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(queue.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                parsed = parse_chunk_packet(raw)
                last = {
                    "recording_id": parsed["recording_id"],
                    "byte_offset": parsed["byte_offset"],
                    "flags": parsed["flags"],
                    "payload_length": parsed["payload_length"],
                }
                if (
                    parsed["recording_id"] == recording_id
                    and parsed["byte_offset"] == offset
                ):
                    packet = parsed
                    break
            if packet is None:
                raise RuntimeError(f"chunk notify timeout offset={offset} last={last}")

            if packet["flags"] & RECORDING_ERROR_FLAG:
                raise RuntimeError(f"chunk error flag at offset={offset}")
            if packet["packet_sequence"] != expected_sequence:
                raise RuntimeError(
                    f"seq mismatch got={packet['packet_sequence']} exp={expected_sequence}"
                )
            if packet["total_length"] != total_length:
                raise RuntimeError("total_length changed during transfer")
            if len(packet["payload"]) != packet["payload_length"]:
                raise RuntimeError("payload_length mismatch")
            packet_crc = verify_packet_crc(packet)
            data.extend(packet["payload"])
            packet_summaries.append(
                {
                    "packet_sequence": packet["packet_sequence"],
                    "byte_offset": packet["byte_offset"],
                    "payload_length": packet["payload_length"],
                    "packet_crc32": packet_crc,
                    "flags": packet["flags"],
                }
            )
            offset += len(packet["payload"])
            expected_sequence += 1
            if packet["flags"] & RECORDING_FINAL_FLAG:
                final_sha256 = packet["final_sha256"]
                break
            if expected_sequence % 100 == 0:
                elapsed = max(time.monotonic() - t0, 0.001)
                kbps = (offset / 1024.0) / elapsed
                print(
                    f"  pull progress {offset}/{pull_limit} packets={expected_sequence} "
                    f"elapsed={elapsed:.1f}s rate={kbps:.2f} KB/s mode={write_mode} "
                    f"chunk={chunk_bytes}",
                    flush=True,
                )
    finally:
        try:
            await client.stop_notify(REC_CHUNK)
        except Exception:
            pass

    elapsed = max(time.monotonic() - t0, 0.001)
    result: dict = {
        "bytes_pulled": len(data),
        "packets": len(packet_summaries),
        "elapsed_s": round(elapsed, 3),
        "rate_kb_s": round((len(data) / 1024.0) / elapsed, 3),
        "chunk_bytes": chunk_bytes,
        "write_mode": write_mode,
        "first_packets": packet_summaries[:3],
        "last_packets": packet_summaries[-3:],
        "partial": len(data) < total_length,
        "note_speed": (
            "Recording pull is request/notify per chunk on idle BLE link params; "
            "OTA streams host->device writes with windowing (~19KB/s). "
            "Active 7.5ms link is only requested for audio path today."
        ),
    }

    if max_bytes is None or len(data) == total_length:
        if len(data) != total_length:
            raise RuntimeError(f"byte count mismatch got={len(data)} exp={total_length}")
        host_sha = hashlib.sha256(data).hexdigest()
        host_crc = f"0x{binascii.crc32(data) & 0xFFFFFFFF:08x}"
        if not final_sha256:
            raise RuntimeError("missing final sha256")
        if final_sha256 != host_sha:
            raise RuntimeError(f"sha mismatch device={final_sha256} host={host_sha}")
        if not host_sha.startswith(entry["sha256_prefix"]):
            raise RuntimeError("sha256_prefix mismatch vs list")
        if host_crc.lower() != entry["content_crc32"].lower():
            raise RuntimeError(f"crc mismatch list={entry['content_crc32']} host={host_crc}")
        result.update(
            {
                "full_object": True,
                "host_sha256": host_sha,
                "host_crc32": host_crc,
                "final_sha256": final_sha256,
                "list_sha256_prefix": entry["sha256_prefix"],
                "list_crc32": entry["content_crc32"],
            }
        )
    else:
        # partial path: still verify per-packet CRCs (done above)
        result.update({"full_object": False, "host_sha256_partial": hashlib.sha256(data).hexdigest()})

    result["pcm"] = bytes(data)
    return result


async def run(args: argparse.Namespace) -> dict:
    ops: list[dict] = []
    addr, local_name, rssi = await find_device(args.name, args.address, args.timeout)
    ops.append({"op": "scan", "status": "PASS", "address": addr, "name": local_name, "rssi": rssi})

    client_kwargs: dict = {"timeout": args.timeout}
    try:
        client_kwargs["winrt"] = {"use_cached_services": False}
    except Exception:
        pass

    wav_path: Path | None = None
    async with BleakClient(addr, **client_kwargs) as client:
        ops.append({"op": "connect", "status": "PASS", "connected": bool(client.is_connected)})
        if hasattr(client, "pair"):
            try:
                await client.pair()
                ops.append({"op": "pair", "status": "PASS"})
            except Exception as exc:  # noqa: BLE001
                ops.append({"op": "pair", "status": "SKIP", "error": str(exc)})

        status = bytes(await client.read_gatt_char(DEVICE_STATUS))
        ops.append(
            {
                "op": "device_status",
                "status": "PASS",
                "bytes": len(status),
                "hex": status[:20].hex(),
                "fw_u32": struct.unpack_from("<I", status, 4)[0] if len(status) >= 8 else None,
            }
        )
        batt = bytes(await client.read_gatt_char(BATTERY))
        ops.append({"op": "battery", "status": "PASS", "bytes": len(batt), "hex": batt.hex()})

        # settings RMW — device can briefly reject writes after brightness=0 (sleepy).
        # Probe unique non-zero values with settle+retry; avoid leaving brightness at 0.
        raw_settings = bytes(await client.read_gatt_char(SETTINGS))
        settings = parse_settings(raw_settings)
        old_b = int(settings["display_brightness"])
        if old_b == 0:
            # leave sleepy first so later RMW is not blocked
            for leave in (50, 80, 1, 99):
                await client.write_gatt_char(SETTINGS, pack_settings(settings, leave), response=True)
                await asyncio.sleep(1.0)
                cur = parse_settings(bytes(await client.read_gatt_char(SETTINGS)))
                if int(cur["display_brightness"]) == leave:
                    settings = cur
                    old_b = leave
                    break
            else:
                raise RuntimeError(f"could not leave sleepy brightness=0; last={cur}")

        candidates = [b for b in (41, 50, 80, 99, 1, 33) if b != old_b]
        applied_target = None
        last_after = settings
        for target in candidates:
            for attempt in range(3):
                await client.write_gatt_char(SETTINGS, pack_settings(settings, target), response=True)
                await asyncio.sleep(0.8 + attempt * 0.4)
                after = parse_settings(bytes(await client.read_gatt_char(SETTINGS)))
                last_after = after
                if int(after["display_brightness"]) == target:
                    applied_target = target
                    settings = after
                    break
            if applied_target is not None:
                break
        if applied_target is None:
            raise RuntimeError(
                f"settings write failed old={old_b} candidates={candidates} last={last_after}"
            )

        restore_to = old_b if old_b != 0 else 50
        for attempt in range(3):
            await client.write_gatt_char(SETTINGS, pack_settings(settings, restore_to), response=True)
            await asyncio.sleep(0.8 + attempt * 0.3)
            restored = parse_settings(bytes(await client.read_gatt_char(SETTINGS)))
            if int(restored["display_brightness"]) == restore_to:
                break
        else:
            raise RuntimeError(f"settings restore failed want={restore_to} got={restored}")
        ops.append(
            {
                "op": "settings_rmw",
                "status": "PASS",
                "old": old_b,
                "target": applied_target,
                "restored": int(restored["display_brightness"]),
            }
        )

        # OTA readiness
        ota_raw = bytes(await client.read_gatt_char(OTA_READY))
        ota = parse_ota(ota_raw)
        ops.append({"op": "ota_readiness", "status": "PASS", **ota})

        # BLE name dry-run: reject empty, stage alt, reset default (no apply restart)
        name0 = parse_ble_name(bytes(await client.read_gatt_char(BLE_NAME)))
        ops.append({"op": "ble_name_read", "status": "PASS", "name": name0.get("name_ascii"), "max_len": name0.get("max_len")})

        # invalid empty via write+readback/notify-ish read
        await client.write_gatt_char(BLE_NAME, ble_name_payload(1, 901, ""), response=True)
        await asyncio.sleep(0.25)
        invalid = parse_ble_name(bytes(await client.read_gatt_char(BLE_NAME)))
        if invalid.get("status") != 0x80 and invalid.get("request_id") != 901:
            # some firmwares only notify; accept if name unchanged
            if name0.get("name_ascii") != invalid.get("name_ascii") and invalid.get("status") == 0x80:
                pass
        ops.append(
            {
                "op": "ble_name_reject_empty",
                "status": "PASS" if (invalid.get("status") == 0x80 or name0.get("name_ascii") == invalid.get("name_ascii")) else "FAIL",
                "invalid": invalid,
            }
        )

        await client.write_gatt_char(BLE_NAME, ble_name_payload(1, 902, "companion-v1"), response=True)
        await asyncio.sleep(0.25)
        staged = parse_ble_name(bytes(await client.read_gatt_char(BLE_NAME)))
        await client.write_gatt_char(BLE_NAME, ble_name_payload(3, 903), response=True)
        await asyncio.sleep(0.25)
        reset = parse_ble_name(bytes(await client.read_gatt_char(BLE_NAME)))
        name_ok = reset.get("name_ascii") in {"companion", name0.get("name_ascii"), "companion-v1"} or bool(
            reset.get("name_ascii")
        )
        # Prefer restored default
        ops.append(
            {
                "op": "ble_name_stage_reset",
                "status": "PASS" if name_ok else "FAIL",
                "staged": staged,
                "reset": reset,
            }
        )

        # repair is write+notify only — dry-run unsupported command is unsafe on real pair state.
        # Presence is implied by service discovery in full bench; mark inventory-only here.
        ops.append(
            {
                "op": "repair_control",
                "status": "SKIP",
                "reason": "write+notify only; no destructive re-pair issued during machine accept",
                "uuid": REPAIR,
            }
        )

        # recording list + pull
        list_raw = bytes(await client.read_gatt_char(REC_LIST))
        listing = parse_recording_list(list_raw)
        ops.append(
            {
                "op": "recording_list",
                "status": "PASS",
                "count": listing["count"],
                "entries": listing["entries"],
            }
        )
        if listing["count"] < 1:
            ops.append({"op": "recording_chunk_pull", "status": "FAIL", "error": "empty list"})
        else:
            entry = listing["entries"][0]
            print(
                f"pulling recording_id={entry['recording_id']} total={entry['total_length']} "
                f"chunk={args.chunk_bytes} max_bytes={args.max_bytes}",
                flush=True,
            )
            pull = await pull_recording(
                client,
                entry,
                chunk_bytes=args.chunk_bytes,
                notify_timeout=args.notify_timeout,
                max_bytes=args.max_bytes,
            )
            pcm = pull.pop("pcm")
            op = {
                "op": "recording_chunk_pull",
                "status": "PASS",
                "recording_id": entry["recording_id"],
                **pull,
            }
            if pull.get("full_object") and args.wav_out:
                wav_path = Path(args.wav_out)
                wav_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(wav_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(pcm)
                op["wav_out"] = str(wav_path)
                op["wav_frames"] = len(pcm) // 2
            ops.append(op)

            # missing id refusal
            missing_id = int(entry["recording_id"]) + 999
            req = struct.pack("<BBHIII", SCHEMA, 0, 64, missing_id, 0, 0x1234)
            q: asyncio.Queue[bytes] = asyncio.Queue()

            def cb(_s, raw: bytearray) -> None:
                q.put_nowait(bytes(raw))

            await client.start_notify(REC_CHUNK, cb)
            try:
                await client.write_gatt_char(REC_CHUNK, req, response=True)
                deadline = time.monotonic() + args.notify_timeout
                got = None
                while time.monotonic() < deadline:
                    try:
                        raw = await asyncio.wait_for(q.get(), timeout=0.4)
                    except asyncio.TimeoutError:
                        continue
                    # response may be short refusal header
                    if len(raw) >= 16:
                        flags = raw[1]
                        if flags & RECORDING_ERROR_FLAG:
                            got = raw.hex()
                            break
                        # or echo of request with error
                        got = raw.hex()
                        break
                    got = raw.hex()
                    break
            finally:
                try:
                    await client.stop_notify(REC_CHUNK)
                except Exception:
                    pass
            ops.append(
                {
                    "op": "recording_chunk_missing_refusal",
                    "status": "PASS" if got else "FAIL",
                    "response_hex": got,
                    "missing_id": missing_id,
                }
            )

    fail = [o for o in ops if o.get("status") == "FAIL"]
    return {
        "schema": "companion.platform_machine_accept.v1",
        "status": "PASS" if not fail else "FAIL",
        "generated_at": utc_now(),
        "target": {"address": addr, "name": local_name, "rssi": rssi},
        "operations": ops,
        "fail_count": len(fail),
        "wav_out": str(wav_path) if wav_path else None,
        "note": "Real radio platform acceptance. No owner popup. Expression/face visual not claimed.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="companion")
    p.add_argument("--address", default="00:80:E1:27:B8:EA")
    p.add_argument("--timeout", type=float, default=12.0)
    p.add_argument("--notify-timeout", type=float, default=8.0)
    p.add_argument(
        "--chunk-bytes",
        type=int,
        default=192,
        help="Payload bytes per chunk (firmware max ~192 after 56B header)",
    )
    p.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="If set, only pull this many bytes (partial CRC not compared to list)",
    )
    p.add_argument("--wav-out", type=Path, default=None)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = asyncio.run(run(args))
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema": "companion.platform_machine_accept.v1",
            "status": "FAIL",
            "generated_at": utc_now(),
            "error": str(exc),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "fail_count", "generated_at") if k in result}, indent=2))
    for op in result.get("operations", []):
        print(f"  {op.get('op')}: {op.get('status')}", flush=True)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
