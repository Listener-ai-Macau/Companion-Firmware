#!/usr/bin/env python3
"""Offline contract verifier for the Companion STM32 external loader."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

ALIAS_BASE = 0x90000000
PARTITION_BYTES = 0x00200000
RAM_BASE = 0x20000004
REQUIRED_SYMBOLS = {
    "StorageInfo",
    "Init",
    "Read",
    "Write",
    "SectorErase",
    "MassErase",
    "Verify",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"VERIFY_EXTERNAL_LOADER_FAILED: {message}")


def c_string(data: bytes, offset: int) -> str:
    end = data.find(b"\0", offset)
    require(end >= 0, "unterminated ELF string")
    return data[offset:end].decode("ascii")


def range_valid(address: int, size: int) -> bool:
    if address < ALIAS_BASE or size < 0:
        return False
    offset = address - ALIAS_BASE
    return offset <= PARTITION_BYTES and size <= PARTITION_BYTES - offset


def parse_elf(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    require(data[:4] == b"\x7fELF", "not an ELF file")
    require(data[4] == 1 and data[5] == 1, "expected ELF32 little-endian")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data, 0)
    machine = header[2]
    section_offset = header[6]
    section_entry_bytes = header[11]
    section_count = header[12]
    section_names_index = header[13]
    require(machine == 40, "expected ARM machine type")
    require(section_entry_bytes == 40, "unexpected section header size")

    sections: list[dict[str, int | str]] = []
    raw_sections: list[tuple[int, ...]] = []
    for index in range(section_count):
        raw = struct.unpack_from(
            "<IIIIIIIIII", data, section_offset + index * section_entry_bytes
        )
        raw_sections.append(raw)
    require(section_names_index < section_count, "bad section name table")
    names_raw = raw_sections[section_names_index]
    names = data[names_raw[4] : names_raw[4] + names_raw[5]]
    for raw in raw_sections:
        sections.append(
            {
                "name": c_string(names, raw[0]),
                "type": raw[1],
                "flags": raw[2],
                "address": raw[3],
                "offset": raw[4],
                "size": raw[5],
                "link": raw[6],
                "entry_bytes": raw[9],
            }
        )

    by_name = {str(section["name"]): section for section in sections}
    require(".DevInfo" in by_name and ".loader" in by_name, "missing loader sections")
    dev_info = by_name[".DevInfo"]
    loader = by_name[".loader"]
    require(dev_info["address"] == 0 and dev_info["size"] == 200,
            ".DevInfo must be 200 bytes at address zero")
    require(loader["address"] == RAM_BASE and loader["size"] > 0,
            "loader code must begin at SRAM 0x20000004")
    alloc_sections = [
        section for section in sections
        if int(section["flags"]) & 0x2 and int(section["size"]) > 0
    ]
    require(
        {str(section["name"]) for section in alloc_sections}
        <= {".DevInfo", ".loader", ".bss"},
        "unexpected allocated section",
    )

    dev = data[
        int(dev_info["offset"]) : int(dev_info["offset"]) + int(dev_info["size"])
    ]
    name = dev[:100].split(b"\0", 1)[0].decode("ascii")
    device_type = struct.unpack_from("<H", dev, 100)[0]
    start_address, device_size, page_size = struct.unpack_from("<III", dev, 104)
    erased_value = dev[116]
    first_sector_count, first_sector_size = struct.unpack_from("<II", dev, 120)
    require(device_type == 3, "device type must be NOR_FLASH")
    require(start_address == ALIAS_BASE, "wrong external alias base")
    require(device_size == PARTITION_BYTES, "loader exposes more than 2 MiB")
    require(page_size == 256 and erased_value == 0xFF, "wrong NOR page contract")
    require(
        first_sector_count == PARTITION_BYTES // 4096
        and first_sector_size == 4096,
        "wrong 4 KiB sector map",
    )
    require(dev[128:] == bytes(72), "unexpected additional sector regions")

    symbols: set[str] = set()
    for section in sections:
        if int(section["type"]) != 2:
            continue
        link = int(section["link"])
        require(link < len(sections), "bad symbol string table")
        strings_section = sections[link]
        strings = data[
            int(strings_section["offset"]) :
            int(strings_section["offset"]) + int(strings_section["size"])
        ]
        entry_bytes = int(section["entry_bytes"])
        require(entry_bytes == 16, "unexpected ELF32 symbol size")
        for offset in range(
            int(section["offset"]),
            int(section["offset"]) + int(section["size"]),
            entry_bytes,
        ):
            name_offset, _value, _size, info, _other, section_index = (
                struct.unpack_from("<IIIBBH", data, offset)
            )
            if (info >> 4) == 1 and section_index != 0 and name_offset != 0:
                symbols.add(c_string(strings, name_offset))
    require(REQUIRED_SYMBOLS <= symbols, "missing standard external-loader exports")

    boundary_cases = {
        "first_byte": range_valid(ALIAS_BASE, 1),
        "full_partition": range_valid(ALIAS_BASE, PARTITION_BYTES),
        "last_byte": range_valid(ALIAS_BASE + PARTITION_BYTES - 1, 1),
        "zero_at_end": range_valid(ALIAS_BASE + PARTITION_BYTES, 0),
        "below_base_rejected": not range_valid(ALIAS_BASE - 1, 1),
        "past_end_rejected": not range_valid(ALIAS_BASE + PARTITION_BYTES, 1),
        "cross_end_rejected": not range_valid(
            ALIAS_BASE + PARTITION_BYTES - 1, 2
        ),
        "u32_wrap_style_rejected": not range_valid(0xFFFFFFFF, 2),
    }
    require(all(boundary_cases.values()), "range guard negative case failed")
    return {
        "artifact": str(path),
        "bytes": len(data),
        "device_name": name,
        "alias_base": f"0x{start_address:08X}",
        "partition_bytes": device_size,
        "page_bytes": page_size,
        "sector_bytes": first_sector_size,
        "sector_count": first_sector_count,
        "loader_ram_base": f"0x{int(loader['address']):08X}",
        "loader_code_bytes": int(loader["size"]),
        "exports": sorted(REQUIRED_SYMBOLS),
        "boundary_cases": boundary_cases,
        "hardware_contact": 0,
        "result": "MACHINE_READY",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("loader", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = parse_elf(args.loader)
    encoded = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
