#!/usr/bin/env python3
"""Embed one audited CRIG component pack for the dedicated screen demo."""

from __future__ import annotations

import argparse
import pathlib
import struct
import zlib


def require_crig(data: bytes, source: pathlib.Path) -> None:
    if len(data) < 80 or data[:4] != b"CRIG":
        raise ValueError(f"{source}: expected a CRIG component pack")
    total_size = struct.unpack_from("<I", data, 8)[0]
    if total_size != len(data):
        raise ValueError(f"{source}: header size {total_size} does not match {len(data)} bytes")


def format_header(data: bytes) -> str:
    crc32 = zlib.crc32(data)
    lines = [
        "#ifndef COMPANION_SCREEN_ASSET_PROVISION_BLOB_H",
        "#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE {len(data)}u",
        f"#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_CRC32 0x{crc32:08X}u",
        "",
        "static const uint8_t companion_screen_asset_provision_blob[]",
        "    __attribute__((aligned(4))) = {",
    ]
    for start in range(0, len(data), 16):
        values = ", ".join(f"0x{byte:02X}u" for byte in data[start:start + 16])
        lines.append(f"    {values},")
    lines.extend(["};", "", "#endif /* COMPANION_SCREEN_ASSET_PROVISION_BLOB_H */", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--c-header", type=pathlib.Path, required=True)
    args = parser.parse_args()

    data = args.input.resolve().read_bytes()
    require_crig(data, args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    args.c_header.parent.mkdir(parents=True, exist_ok=True)
    args.c_header.write_text(format_header(data), encoding="ascii", newline="\n")
    print(f"CRIG bytes={len(data)} crc32=0x{zlib.crc32(data):08X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
