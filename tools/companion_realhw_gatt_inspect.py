#!/usr/bin/env python3
"""Real-hw GATT inspection: enumerate the on-device Companion service/characteristic
table and read device_status, to distinguish (a) stale hex with no diag service,
(b) handler present but ring empty/silent, (c) CCCD/notify not enabled.
Read-only: enumerate + one read on device_status. Writes nothing.
"""
from __future__ import annotations
import asyncio
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bleak import BleakClient, BleakScanner  # noqa: E402

MAC = "00:80:E1:27:B8:EA"
DIAG = "8f7a5001-7b7d-4f3d-9d6f-6c2d1b7c0000"
DEV_STATUS = "8f7a1001-7b7d-4f3d-9d6f-6c2d1b7c0000"


async def main() -> int:
    dev = await BleakScanner.find_device_by_address(MAC, timeout=15.0)
    if dev is None:
        print("YIELD: device not seen")
        return 2
    print(f"found {dev.name!r}")
    async with BleakClient(dev, timeout=20.0) as c:
        print(f"connected; enumerating companion characteristics:")
        found_diag = False
        for s in c.services:
            for ch in s.characteristics:
                u = str(ch.uuid)
                if "8f7a" in u or "710af845" in u:
                    flag = "  <-- DIAG" if "8f7a5001" in u else ""
                    print(f"  {u}  props={list(ch.properties)}  handle={ch.handle}{flag}")
                    if "8f7a5001" in u:
                        found_diag = True
                        diag_props = list(ch.properties)
        print(f"\ndiagnostics_log_pull (8f7a5001) present: {found_diag}")
        if found_diag:
            print(f"  properties: {diag_props}")
            print(f"  has notify: {'notify' in diag_props}")
            print(f"  has write:  {'write' in diag_props or 'write-without-response' in diag_props}")
        # read device_status for firmware_version + build_id
        try:
            data = bytes(await c.read_gatt_char(DEV_STATUS))
            print(f"\ndevice_status raw ({len(data)}B): {data.hex()}")
            # DeviceStatusV1 fields from app_ble.c (u8 schema, u8 active_mode, u8 fault,
            # then u32 firmware_version / build_id / board_id / uptime_ms — natural align
            # pads fault->u32 boundary at offset 4).
            if len(data) >= 8:
                import struct
                schema = data[0]
                active = data[1]
                fault = data[2]
                fw = struct.unpack_from("<I", data, 4)[0] if len(data) >= 8 else None
                build = struct.unpack_from("<I", data, 8)[0] if len(data) >= 12 else None
                board = struct.unpack_from("<I", data, 12)[0] if len(data) >= 16 else None
                uptime = struct.unpack_from("<I", data, 16)[0] if len(data) >= 20 else None
                print(f"  schema={schema} active_mode={active} fault=0x{fault:02x}")
                print(f"  firmware_version=0x{fw:08x}" if fw is not None else "  fw=?")
                print(f"  build_id=0x{build:08x}" if build is not None else "  build=?")
                print(f"  board_id=0x{board:08x}" if board is not None else "  board=?")
                print(f"  uptime_ms={uptime}" if uptime is not None else "  uptime=?")
        except Exception as e:  # noqa: BLE001
            print(f"read device_status failed: {e!r}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
