#!/usr/bin/env python3
"""Real-hardware observability probe.

Pulls the diagnostics/log buffer from the physical STM32WB55 Companion device
over BLE. READ-ONLY: it issues ONE diag-log pull request on the
diagnostics_log_pull characteristic (8f7a5001-...) and decodes the notify
response. It writes no device state (no card / settings / recording / wake /
delete / ota writes), so it is safe to run alongside other holders.

Wire contract is reused verbatim from companion_ble_real_bench
(parse_diag_log_pull + notify_write_wait) so the on-the-wire bytes match the
validated GATT bench.

Yield gate: if the device is not seen in scan, the probe aborts without
attempting a connection (another holder — e.g. codex — may own the link).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import pathlib
import struct
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import companion_ble_real_bench as bench  # noqa: E402
from bleak import BleakClient, BleakScanner  # noqa: E402

MAC = "00:80:E1:27:B8:EA"
DIAG_UUID = "8f7a5001-7b7d-4f3d-9d6f-6c2d1b7c0000"
EVIDENCE = HERE.parent / "docs" / "validation" / "companion-realhw-diag-log-pull.json"

# Best-effort source-name map; order follows diag_log_events.h SOURCE_LIST.
SOURCE_NAMES = {
    1: "BOOT", 2: "BLE", 3: "GATT", 4: "EPAPER", 5: "RECORDING_FSM",
    6: "MICROPHONE", 7: "SPI_FLASH_CACHE", 8: "OTA", 9: "BATTERY_CHARGING",
    10: "POWER_LPM", 11: "WARNINGS", 12: "ERRORS", 13: "MEETING", 14: "IMU",
    15: "SPEAKER", 16: "WAKE_WORD", 17: "DEVICE_SETTINGS",
}
SEV_NAMES = {0: "INFO", 1: "WARN", 2: "ERROR"}


def decode_event(ev: dict) -> dict:
    return {
        "sequence": ev["sequence"],
        "t_ms": ev["t_ms"],
        "source": SOURCE_NAMES.get(ev["source"], f"SRC{ev['source']}"),
        "source_id": ev["source"],
        "event_id": ev["event_id"],
        "severity": SEV_NAMES.get(ev["severity"], f"SEV{ev['severity']}"),
        "event_flags": ev["event_flags"],
        "args": [ev["arg0"], ev["arg1"], ev["arg2"], ev["arg3"]],
    }


async def pull(client, cursor: int, max_events: int, max_bytes: int, source_mask: int = 0xFF) -> dict:
    # schema=1, source_mask=0xFF (bits 0-7 select sources 1-8: BOOT/BLE/GATT/EPAPER/
    # RECORDING_FSM/MICROPHONE/SPI_FLASH_CACHE/OTA), severity=0xFFFF (all), cursor,
    # max_events, max_bytes. Little-endian, 12 bytes.
    # NOTE: source_mask=0 (as companion_ble_real_bench uses) matches NO source, so the
    # device records zero matching events and stays SILENT (no notify) — see app_ble.c
    # Companion_Gatt_PublishDiagLogResponse: packet_bytes==0 -> return without notify.
    payload = struct.pack("<BBHIHH", 1, source_mask, 0xFFFF, cursor, max_events, max_bytes)
    return await bench.notify_write_wait(
        client, DIAG_UUID, DIAG_UUID, payload,
        bench.parse_diag_log_pull,
        lambda p: p["request_cursor"] == cursor,
        10.0,
    )


async def main() -> int:
    print(f"[probe] scanning 15s for {MAC} (yield gate) ...")
    device = await BleakScanner.find_device_by_address(MAC, timeout=15.0)
    if device is None:
        print("[probe] YIELD: device not seen in scan (codex may hold BLE or "
              "device is off). Aborting without connecting.")
        return 2
    print(f"[probe] found name={device.name!r} rssi={getattr(device, 'rssi', '?')} — connecting")

    evidence: dict = {
        "mac": MAC,
        "captured_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "probe": pathlib.Path(__file__).name,
        "capability": "observability.diagnostics_log_pull",
        "uuid": DIAG_UUID,
    }

    async with BleakClient(device, timeout=20.0) as client:
        evidence["mtu"] = getattr(client, "mtu_size", None)
        first = await pull(client, 0, 8, 240)
        decoded = [decode_event(e) for e in first["events"]]
        evidence["pull_1"] = {
            "request": {
                "schema_version": 1, "source_mask": "0xFF", "severity_mask": "0xFFFF",
                "cursor": 0, "max_events": 8, "max_bytes": 240,
            },
            "event_count": first["event_count"],
            "total_available": first["total_available"],
            "next_cursor": first["next_cursor"],
            "packet_bytes": first["packet_bytes"],
            "payload_crc32": first["payload_crc32"],
            "crc_valid": first["crc_valid"],
            "events": decoded,
        }
        print(f"[probe] pull#1: {first['event_count']} events, "
              f"total_available={first['total_available']}, "
              f"crc_valid={first['crc_valid']}, next_cursor={first['next_cursor']}")
        for e in decoded:
            print(f"         #{e['sequence']:>3} t={e['t_ms']:>8}ms "
                  f"{e['source']:<16} evt=0x{e['event_id']:02x} "
                  f"{e['severity']:<5} args={e['args']}")

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"[probe] evidence -> {EVIDENCE}")
    ok = first["event_count"] >= 1 and first["crc_valid"]
    print(f"[probe] RESULT: "
          f"{'PASS — observability.diag-log real-hw CLOSED' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
