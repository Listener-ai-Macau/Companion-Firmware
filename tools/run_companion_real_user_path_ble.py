#!/usr/bin/env python3
"""Real-radio Companion user-path probe (not host simulation).

Connects to a physical companion, reads status, battery, recording list,
settings and OTA readiness, and optionally exercises a short recording control
start/stop when the board accepts it. Writes a durable JSON artifact.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakClient, BleakScanner

DEVICE_STATUS = "8f7a1001-7b7d-4f3d-9d6f-6c2d1b7c0000"
BATTERY = "8f7a1002-7b7d-4f3d-9d6f-6c2d1b7c0000"
REC_CTRL = "8f7a3001-7b7d-4f3d-9d6f-6c2d1b7c0000"
REC_LIST = "8f7a3002-7b7d-4f3d-9d6f-6c2d1b7c0000"
SETTINGS = "8f7a4001-7b7d-4f3d-9d6f-6c2d1b7c0000"
OTA_READY = "8f7a7001-7b7d-4f3d-9d6f-6c2d1b7c0000"


async def find_device(name: str, address: str | None, timeout: float):
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    for addr, (dev, adv) in found.items():
        local = (dev.name or adv.local_name or "")
        if address and addr.upper() != address.upper():
            continue
        if name.lower() in local.lower() or (address and addr.upper() == address.upper()):
            return addr, local, getattr(adv, "rssi", None)
    raise RuntimeError(f"device not found name={name!r} address={address!r}")


async def run(args: argparse.Namespace) -> dict:
    ops: list[dict] = []
    addr, local_name, rssi = await find_device(args.name, args.address, args.timeout)
    ops.append(
        {
            "operation": "scan",
            "status": "PASS",
            "address": addr,
            "name": local_name,
            "rssi": rssi,
        }
    )

    last_err = None
    for attempt in range(1, args.connect_retries + 1):
        try:
            # Re-scan each attempt: Windows often drops the advertiser after a bad disconnect.
            addr, local_name, rssi = await find_device(args.name, args.address, min(args.timeout, 8.0))
            # Windows WinRT: cached GATT + unpaired links often cancel first reads.
            client_kwargs = {"timeout": args.timeout}
            try:
                client_kwargs["winrt"] = {"use_cached_services": False}
            except Exception:
                pass
            async with BleakClient(addr, **client_kwargs) as client:
                ops.append(
                    {
                        "operation": "connect",
                        "status": "PASS",
                        "attempt": attempt,
                        "connected": bool(client.is_connected),
                        "address": addr,
                    }
                )
                if hasattr(client, "pair"):
                    try:
                        await client.pair()
                        ops.append({"operation": "pair", "status": "PASS"})
                    except Exception as pair_exc:  # noqa: BLE001
                        ops.append(
                            {
                                "operation": "pair",
                                "status": "SKIP",
                                "error": str(pair_exc),
                            }
                        )

                async def read_one(label: str, uuid: str) -> bytes:
                    data = bytes(await client.read_gatt_char(uuid))
                    ops.append(
                        {
                            "operation": f"read_{label}",
                            "status": "PASS",
                            "uuid": uuid,
                            "bytes": len(data),
                            "hex_prefix": data[:24].hex(),
                        }
                    )
                    return data

                status = await read_one("device_status", DEVICE_STATUS)
                battery = await read_one("battery", BATTERY)
                rec_list = await read_one("recording_list", REC_LIST)
                settings = await read_one("settings", SETTINGS)
                utc_now = datetime.now(timezone.utc)
                await client.write_gatt_char(
                    SETTINGS,
                    settings[:10]
                    + bytes((utc_now.hour, utc_now.minute, utc_now.second)),
                    response=True,
                )
                ops.append(
                    {
                        "operation": "sync_utc_clock",
                        "status": "PASS",
                        "utc_hms": utc_now.strftime("%H:%M:%S"),
                        "settings_prefix_preserved": len(settings) >= 10,
                    }
                )
                ota = await read_one("ota_readiness", OTA_READY)

                firmware_version = None
                if len(status) >= 12:
                    firmware_version = struct.unpack_from("<I", status, 4)[0]

                # recording_list v1 starts with <schema, count, entry_size,
                # reserved>; byte 0 is not the catalog count.
                recording_count = rec_list[1] if len(rec_list) >= 2 else None

                if args.exercise_recording_control:
                    # recording_control v1 is <schema, command, profile,
                    # reserved, request_id, max_seconds>.  The former 8-byte
                    # payload was a stale pre-profile contract: Windows could
                    # report a successful GATT write while the board correctly
                    # ignored it and remained idle.
                    request_id = int(time.time()) & 0xFFFFFFFF
                    start = struct.pack(
                        "<BBBBIH", 1, 1, 2, 0, request_id,
                        max(1, int(args.record_seconds) + 1))
                    stop = struct.pack(
                        "<BBBBIH", 1, 2, 2, 0,
                        (request_id + 1) & 0xFFFFFFFF, 0)
                    await client.write_gatt_char(REC_CTRL, start, response=True)
                    ops.append({"operation": "recording_control_start_write", "status": "PASS"})
                    await asyncio.sleep(args.record_seconds)
                    await client.write_gatt_char(REC_CTRL, stop, response=True)
                    ops.append({"operation": "recording_control_stop_write", "status": "PASS"})
                    await asyncio.sleep(0.5)
                    rec_list2 = await read_one("recording_list_after_control", REC_LIST)
                    recording_count = (
                        rec_list2[1] if len(rec_list2) >= 2 else recording_count
                    )

                ops.append({"operation": "disconnect", "status": "PASS"})

            return {
                "schema": "companion.real_user_path_ble.v1",
                "status": "PASS_REAL_RADIO",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "target": {"address": addr, "name": local_name, "rssi": rssi},
                "firmware_version_u32": firmware_version,
                "recording_list_count": recording_count,
                "payload_sizes": {
                    "device_status": len(status),
                    "battery": len(battery),
                    "recording_list": len(rec_list),
                    "settings": len(settings),
                    "ota_readiness": len(ota),
                },
                "operations": ops,
                "note": "Real BLE radio path. Does not claim OTA apply, mic soak, or human visual panel acceptance.",
            }
        except Exception as exc:  # noqa: BLE001 - record and retry real radio flakiness
            last_err = exc
            ops.append(
                {
                    "operation": "connect_or_path_attempt",
                    "status": "FAIL",
                    "attempt": attempt,
                    "error": str(exc),
                }
            )
            await asyncio.sleep(2.0)

    return {
        "schema": "companion.real_user_path_ble.v1",
        "status": "FAIL_REAL_RADIO",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "error": str(last_err),
        "operations": ops,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="companion")
    parser.add_argument("--address", default="")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--connect-retries", type=int, default=3)
    parser.add_argument("--exercise-recording-control", action="store_true")
    parser.add_argument("--record-seconds", type=float, default=1.5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    args.address = args.address or None
    result = asyncio.run(run(args))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "PASS_REAL_RADIO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
