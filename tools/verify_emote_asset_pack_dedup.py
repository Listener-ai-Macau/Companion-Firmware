#!/usr/bin/env python3
"""Verify CEMP keeps duplicate raster payloads shared and independently seekable."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

from build_emote_asset_pack import build_pack


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app/companion_pendant/epaper/assets/emote_matrix_white_200x200.json"
REPORT = ROOT / "docs/validation/companion-screen-emote-pack-dedup.json"
HEADER_FRAME_COUNT = 30
HEADER_FRAME_OFFSET = 36
HEADER_PAYLOAD_OFFSET = 48
HEADER_PAYLOAD_SIZE = 52
FRAME_ENTRY_BYTES = 20


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    pack, metadata = build_pack(MANIFEST)
    frame_count = struct.unpack_from("<H", pack, HEADER_FRAME_COUNT)[0]
    frame_offset = struct.unpack_from("<I", pack, HEADER_FRAME_OFFSET)[0]
    payload_offset = struct.unpack_from("<I", pack, HEADER_PAYLOAD_OFFSET)[0]
    payload_size = struct.unpack_from("<I", pack, HEADER_PAYLOAD_SIZE)[0]
    ranges: list[tuple[int, int]] = []
    errors: list[str] = []

    if frame_count != metadata["frame_count"]:
        errors.append("CEMP header frame count does not match pack metadata")
    if payload_offset + payload_size != len(pack):
        errors.append("CEMP payload boundary does not end at pack size")
    for index in range(frame_count):
        data_offset, data_size = struct.unpack_from(
            "<II", pack, frame_offset + index * FRAME_ENTRY_BYTES
        )
        if data_size == 0 or data_offset + data_size > payload_size:
            errors.append(f"frame {index} points outside the CEMP payload")
        ranges.append((data_offset, data_size))

    unique_ranges = len(set(ranges))
    if unique_ranges != metadata["unique_payload_frame_count"]:
        errors.append("unique CEMP ranges do not match deduplication metadata")
    if metadata["deduplicated_frame_count"] != frame_count - unique_ranges:
        errors.append("deduplicated frame count does not match CEMP frame ranges")
    if metadata["deduplicated_frame_count"] <= 0:
        errors.append("CEMP must retain at least one shared payload frame")
    if metadata["payload_bytes"] >= metadata["payload_bytes_without_deduplication"]:
        errors.append("CEMP deduplication did not reduce payload bytes")

    report = {
        "schema": "companion.screen.emote_pack_dedup.v1",
        "status": "PASS" if not errors else "FAIL",
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "revision": metadata["revision"],
        "clip_count": metadata["clip_count"],
        "frame_count": frame_count,
        "unique_payload_frame_count": unique_ranges,
        "deduplicated_frame_count": metadata["deduplicated_frame_count"],
        "payload_bytes_without_deduplication": metadata["payload_bytes_without_deduplication"],
        "payload_bytes": metadata["payload_bytes"],
        "total_bytes": metadata["total_bytes"],
        "pack_crc32": f"0x{metadata['pack_crc32']:08X}",
        "errors": errors,
    }
    if args.write:
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "PASS: CEMP shared-payload frame ranges remain independently seekable "
        f"({frame_count} frame records, {unique_ranges} payload records)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
