#!/usr/bin/env python3
"""Stress STOP/finalize against an immediate new GATT START on real WB55."""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

from bleak import BleakClient, BleakScanner

from companion_ble_auto_record import load_uuids, notify_write, pack_ctrl, parse_list


async def main() -> int:
    repo = pathlib.Path(__file__).resolve().parents[1]
    uuids = load_uuids(repo)
    client = None
    for attempt in range(1, 4):
        found = await BleakScanner.discover(timeout=12.0)
        device = next(
            (item for item in found if item.name and "companion" in item.name.lower()),
            None,
        )
        if device is None:
            print(f"NO_DEVICE attempt={attempt}")
            await asyncio.sleep(2.0)
            continue
        # Windows may retain a stale GATT handle table across App-only flashes.
        # Product regressions must rediscover services just like the Type path;
        # otherwise the first recording-list read can close a healthy object.
        candidate = BleakClient(
            device,
            timeout=20.0,
            winrt={"use_cached_services": False},
        )
        try:
            await candidate.connect()
            if hasattr(candidate, "pair"):
                try:
                    await candidate.pair()
                except Exception as exc:
                    print(f"PAIR_SKIP attempt={attempt} error={type(exc).__name__}")
            client = candidate
            break
        except Exception as exc:
            print(f"CONNECT_RETRY attempt={attempt} error={type(exc).__name__}")
            try:
                await candidate.disconnect()
            except Exception:
                pass
            await asyncio.sleep(2.0)
    if client is None:
        return 2

    try:
        await asyncio.sleep(1.0)
        before = parse_list(bytes(await client.read_gatt_char(uuids["recording_list"])))
        print("LIST0", json.dumps(before))

        # First real capture, then intentionally race a new START against its
        # storage finalize boundary.  The firmware must reject, never crash.
        await notify_write(client, uuids["recording_control"], pack_ctrl(1, 6101, 20, 2))
        # max_s=20 pre-erases the complete ~323 KiB short-recording extent.
        # Allow that prepare to finish and capture to become RECORDING before
        # issuing STOP; otherwise this probes pending-start cancellation only.
        await asyncio.sleep(8.0)
        await notify_write(client, uuids["recording_control"], pack_ctrl(2, 6102, 0, 2))
        await asyncio.sleep(0.05)
        await notify_write(client, uuids["recording_control"], pack_ctrl(1, 6103, 20, 2))

        # Once finalize is certainly done, a fresh START must work normally.
        await asyncio.sleep(1.5)
        await notify_write(client, uuids["recording_control"], pack_ctrl(1, 6104, 20, 2))
        await asyncio.sleep(8.0)
        await notify_write(client, uuids["recording_control"], pack_ctrl(2, 6105, 0, 2))
        await asyncio.sleep(2.0)

        after = parse_list(bytes(await client.read_gatt_char(uuids["recording_list"])))
        print("LIST1", json.dumps(after))
        old_ids = {entry["id"] for entry in before["entries"]}
        new_entries = [entry for entry in after["entries"] if entry["id"] not in old_ids]
        valid = [
            entry
            for entry in new_entries
            if entry.get("codec") == 3
            and entry.get("dur_ms", 0) > 0
            and entry.get("len", 0) > 0
        ]
        print("REENTRY_PROBE", json.dumps({"new": new_entries, "valid": valid}))
        return 0 if len(valid) >= 2 else 3
    finally:
        await client.disconnect()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
