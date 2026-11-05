#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zlib


SECTOR_SIZE = 4096


def format_header(
    chunk: bytes,
    *,
    chunk_offset: int,
    total_size: int,
    total_crc32: int,
) -> str:
    chunk_crc32 = zlib.crc32(chunk)
    finalizes_pack = chunk_offset == 0
    lines = [
        "#ifndef COMPANION_SCREEN_ASSET_PROVISION_BLOB_H",
        "#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE {len(chunk)}u",
        (
            "#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_CRC32 "
            f"0x{chunk_crc32:08X}u"
        ),
        f"#define COMPANION_SCREEN_ASSET_PROVISION_CHUNK_OFFSET {chunk_offset}u",
        f"#define COMPANION_SCREEN_ASSET_PROVISION_TOTAL_SIZE {total_size}u",
        (
            "#define COMPANION_SCREEN_ASSET_PROVISION_TOTAL_CRC32 "
            f"0x{total_crc32:08X}u"
        ),
        (
            "#define COMPANION_SCREEN_ASSET_PROVISION_FINALIZES_PACK "
            f"{1 if finalizes_pack else 0}u"
        ),
        f"#define COMPANION_SCREEN_ASSET_PROVISION_HEADER_COMMIT_BYTES {SECTOR_SIZE}u",
        "",
        "static const uint8_t companion_screen_asset_provision_blob[]",
        "    __attribute__((aligned(4))) = {",
    ]
    for start in range(0, len(chunk), 16):
        values = ", ".join(
            f"0x{byte:02X}u" for byte in chunk[start : start + 16]
        )
        lines.append(f"    {values},")
    lines.extend(
        ["};", "", "#endif /* COMPANION_SCREEN_ASSET_PROVISION_BLOB_H */", ""]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--offset", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--length", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--output-header", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args()

    pack = args.input.resolve().read_bytes()
    if args.offset < 0 or args.length <= 0:
        raise SystemExit("chunk offset/length must be non-negative and non-zero")
    if args.offset % SECTOR_SIZE:
        raise SystemExit("chunk offset must be 4 KiB aligned")
    if args.offset + args.length > len(pack):
        raise SystemExit("chunk extends beyond the input pack")
    if args.offset + args.length < len(pack) and args.length % SECTOR_SIZE:
        raise SystemExit("non-terminal chunk length must be 4 KiB aligned")

    chunk = pack[args.offset : args.offset + args.length]
    total_crc32 = zlib.crc32(pack)
    args.output_header.parent.mkdir(parents=True, exist_ok=True)
    args.output_header.write_text(
        format_header(
            chunk,
            chunk_offset=args.offset,
            total_size=len(pack),
            total_crc32=total_crc32,
        ),
        encoding="ascii",
        newline="\n",
    )

    receipt = {
        "schema": "companion.screen_asset_provision_chunk.v1",
        "input": str(args.input),
        "input_bytes": len(pack),
        "input_sha256": hashlib.sha256(pack).hexdigest().upper(),
        "input_crc32": f"0x{total_crc32:08X}",
        "chunk_offset": args.offset,
        "chunk_bytes": len(chunk),
        "chunk_sha256": hashlib.sha256(chunk).hexdigest().upper(),
        "chunk_crc32": f"0x{zlib.crc32(chunk):08X}",
        "sector_size": SECTOR_SIZE,
        "finalizes_pack": args.offset == 0,
        "header_commit_bytes": SECTOR_SIZE if args.offset == 0 else 0,
    }
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="ascii"
        )
    print(
        "SCREEN_ASSET_CHUNK "
        f"offset={args.offset} bytes={len(chunk)} total={len(pack)} "
        f"final={int(args.offset == 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
