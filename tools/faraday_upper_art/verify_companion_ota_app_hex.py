#!/usr/bin/env python3
"""Fail closed unless an Intel HEX is a valid Companion OTA App image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


APP_BASE = 0x08007000
APP_END = 0x08080000
MAGIC_POINTER_ADDRESS = APP_BASE + 0x140
OTA_MAGIC = 0x94448A29


def load_hex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    eof_seen = False
    for line_number, raw_line in enumerate(
        path.read_text(encoding="ascii").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line.startswith(":"):
            raise ValueError(f"{path}:{line_number}: invalid Intel HEX")
        record = bytes.fromhex(line[1:])
        if len(record) < 5 or (sum(record) & 0xFF) != 0:
            raise ValueError(f"{path}:{line_number}: bad Intel HEX checksum")
        count = record[0]
        address = int.from_bytes(record[1:3], "big")
        kind = record[3]
        payload = record[4 : 4 + count]
        if len(payload) != count or len(record) != count + 5:
            raise ValueError(f"{path}:{line_number}: malformed Intel HEX")
        if kind == 0:
            absolute = upper + address
            for offset, value in enumerate(payload):
                target = absolute + offset
                previous = memory.get(target)
                if previous is not None and previous != value:
                    raise ValueError(
                        f"{path}:{line_number}: conflicting byte "
                        f"at 0x{target:08X}"
                    )
                memory[target] = value
        elif kind == 1:
            eof_seen = True
            break
        elif kind == 4:
            if count != 2:
                raise ValueError(
                    f"{path}:{line_number}: bad extended address"
                )
            upper = int.from_bytes(payload, "big") << 16
        elif kind not in (2, 3, 5):
            raise ValueError(
                f"{path}:{line_number}: unsupported record type {kind}"
            )
    if not memory or not eof_seen:
        raise ValueError(f"{path}: incomplete Intel HEX")
    return memory


def u32(memory: dict[int, int], address: int) -> int | None:
    values = [memory.get(address + offset) for offset in range(4)]
    if any(value is None for value in values):
        return None
    return int.from_bytes(bytes(values), "little")


def verify(path: Path) -> dict:
    memory = load_hex(path)
    minimum = min(memory)
    maximum = max(memory) + 1
    msp = u32(memory, APP_BASE)
    reset_handler = u32(memory, APP_BASE + 4)
    magic_pointer = u32(memory, MAGIC_POINTER_ADDRESS)
    magic_value = (
        u32(memory, magic_pointer)
        if magic_pointer is not None
        and APP_BASE <= magic_pointer <= APP_END - 4
        else None
    )
    checks = {
        "defined_bytes_only_in_ota_app": (
            minimum >= APP_BASE and maximum <= APP_END
        ),
        "vector_present_at_0x08007000": (
            msp is not None and reset_handler is not None
        ),
        "msp_in_sram": (
            msp is not None and 0x20000000 <= msp < 0x20040000
        ),
        "reset_handler_thumb_in_ota_app": (
            reset_handler is not None
            and (reset_handler & 1) == 1
            and APP_BASE <= (reset_handler & ~1) < APP_END
        ),
        "ota_magic_pointer_in_app": (
            magic_pointer is not None
            and APP_BASE <= magic_pointer <= APP_END - 4
        ),
        "ota_magic_value_exact": magic_value == OTA_MAGIC,
    }
    return {
        "schema": "companion.ota_app_hex_layout.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "image": str(path.resolve()),
        "defined_bytes": len(memory),
        "minimum_address": f"0x{minimum:08X}",
        "maximum_address_exclusive": f"0x{maximum:08X}",
        "vector": {
            "msp": None if msp is None else f"0x{msp:08X}",
            "reset_handler": (
                None
                if reset_handler is None
                else f"0x{reset_handler:08X}"
            ),
        },
        "ota_magic": {
            "pointer": (
                None
                if magic_pointer is None
                else f"0x{magic_pointer:08X}"
            ),
            "value": (
                None if magic_value is None else f"0x{magic_value:08X}"
            ),
        },
        "checks": checks,
        "hardware_contact": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hex", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.hex)
    except (OSError, ValueError) as exc:
        result = {
            "schema": "companion.ota_app_hex_layout.v1",
            "status": "FAILED",
            "error": str(exc),
            "hardware_contact": 0,
        }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
