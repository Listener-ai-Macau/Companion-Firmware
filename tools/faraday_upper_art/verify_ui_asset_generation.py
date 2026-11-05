#!/usr/bin/env python3
"""Verify every UI-generation state against the canonical 200x200 source."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

from build_ui_asset_generation import (
    FLAG_OVERRIDE_PACKBITS,
    FLAG_XOR_PATCH,
    FRAME_BYTES,
    MANIFEST_ENTRY_BYTES,
    MANIFEST_HEADER_BYTES,
    fnv1a32,
    read_pbm_display_bytes,
    state_duration_ms,
)


def decode_packbits(data: bytes) -> bytes:
    output = bytearray()
    index = 0
    while index < len(data):
        control = data[index]
        index += 1
        if control <= 127:
            count = control + 1
            if index + count > len(data):
                raise ValueError("PackBits literal exceeds payload")
            output.extend(data[index:index + count])
            index += count
        elif control >= 129:
            count = 257 - control
            if index >= len(data):
                raise ValueError("PackBits run misses its byte")
            output.extend(bytes((data[index],)) * count)
            index += 1
        else:
            raise ValueError("PackBits 0x80 is forbidden")
    if len(output) != FRAME_BYTES:
        raise ValueError(f"decoded frame is {len(output)} bytes")
    return bytes(output)


def apply_xor_patch(base: bytes, encoded: bytes) -> bytes:
    output = bytearray(base)
    cursor = 0
    previous_end = 0
    while cursor < len(encoded):
        if len(encoded) - cursor < 3:
            raise ValueError("XOR patch has a truncated run header")
        offset, count = struct.unpack_from("<HB", encoded, cursor)
        cursor += 3
        if (count == 0 or offset < previous_end or
                offset + count > FRAME_BYTES or
                cursor + count > len(encoded)):
            raise ValueError("XOR patch run is malformed")
        for index, value in enumerate(encoded[cursor:cursor + count]):
            output[offset + index] ^= value
        cursor += count
        previous_end = offset + count
    return bytes(output)


def parse_cemp(path: Path) -> list[bytes]:
    data = path.read_bytes()
    if len(data) < 80 or data[:4] != b"CEMP":
        raise ValueError("base CEMP is invalid")
    version, header_size = struct.unpack_from("<HH", data, 4)
    total_size = struct.unpack_from("<I", data, 8)[0]
    width, height, stride = struct.unpack_from("<HHH", data, 20)
    pixel_format, encoding, _, frame_count = struct.unpack_from("<BBHH", data, 26)
    frame_offset = struct.unpack_from("<I", data, 36)[0]
    payload_offset, payload_size, payload_crc = struct.unpack_from("<III", data, 48)
    if (version, header_size, total_size) != (1, 80, len(data)):
        raise ValueError("base CEMP header is inconsistent")
    if (width, height, stride, pixel_format, encoding) != (200, 200, 25, 1, 2):
        raise ValueError("base CEMP profile is not 200x200 PackBits 1bpp")
    if zlib.crc32(data[payload_offset:payload_offset + payload_size]) != payload_crc:
        raise ValueError("base CEMP payload CRC mismatch")
    frames: list[bytes] = []
    for index in range(frame_count):
        entry = frame_offset + index * 20
        data_offset, data_size = struct.unpack_from("<II", data, entry)
        encoded = data[
            payload_offset + data_offset:
            payload_offset + data_offset + data_size
        ]
        frames.append(decode_packbits(encoded))
    return frames


def parse_blob_map(values: list[str]) -> dict[int, bytes]:
    result: dict[int, bytes] = {}
    for value in values:
        offset_text, path_text = value.split("=", 1)
        offset = int(offset_text, 0)
        result[offset] = Path(path_text).read_bytes()
    return result


def read_absolute(blob_map: dict[int, bytes], offset: int, size: int) -> bytes:
    for base, blob in blob_map.items():
        if base <= offset and size <= len(blob) - (offset - base):
            relative = offset - base
            return blob[relative:relative + size]
    raise ValueError(f"payload 0x{offset:X}+{size} is absent from blob map")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--generation", required=True, type=Path)
    parser.add_argument("--base-cemp", required=True, type=Path)
    parser.add_argument("--blob", action="append", default=[],
                        help="absolute_offset=path")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.source_pack_manifest.read_text(encoding="utf-8"))
    generation = json.loads(args.generation.read_text(encoding="utf-8"))
    source_root = args.source_pack_manifest.resolve().parent
    base_frames = parse_cemp(args.base_cemp)
    blob_map = parse_blob_map(args.blob)
    entries = generation["entries_by_id"]
    states = source["states"]
    if set(entries) != {state["id"] for state in states}:
        raise ValueError("generation does not enumerate the complete source")

    checked = 0
    override_count = 0
    patch_count = 0
    hashes: set[int] = set()
    for state in states:
        state_id = state["id"]
        expected = read_pbm_display_bytes(source_root / state["pbm_file"])
        entry = entries[state_id]
        if int(entry["duration_ms"]) != state_duration_ms(state):
            raise ValueError(f"duration differs: {state_id}")
        state_hash = fnv1a32(state_id)
        if state_hash in hashes or entry["state_hash"] != state_hash:
            raise ValueError(f"state hash mismatch/collision: {state_id}")
        hashes.add(state_hash)
        if entry["flags"] == 0:
            frame_index = int(entry["base_frame_index"])
            if frame_index >= len(base_frames):
                raise ValueError(f"base frame out of range: {state_id}")
            actual = base_frames[frame_index]
        elif entry["flags"] == FLAG_OVERRIDE_PACKBITS:
            encoded = read_absolute(
                blob_map,
                int(entry["payload_offset"]),
                int(entry["payload_size"]),
            )
            if zlib.crc32(encoded) != int(entry["payload_crc32"]):
                raise ValueError(f"override payload CRC mismatch: {state_id}")
            actual = decode_packbits(encoded)
            override_count += 1
        elif entry["flags"] == FLAG_XOR_PATCH:
            frame_index = int(entry["base_frame_index"])
            if frame_index >= len(base_frames):
                raise ValueError(f"patch base frame out of range: {state_id}")
            encoded = read_absolute(
                blob_map,
                int(entry["payload_offset"]),
                int(entry["payload_size"]),
            )
            if zlib.crc32(encoded) != int(entry["payload_crc32"]):
                raise ValueError(f"patch payload CRC mismatch: {state_id}")
            actual = apply_xor_patch(base_frames[frame_index], encoded)
            patch_count += 1
        else:
            raise ValueError(f"unsupported entry flags: {state_id}")
        if actual != expected:
            raise ValueError(f"frame bytes differ: {state_id}")
        if zlib.crc32(actual) != int(entry["frame_crc32"]):
            raise ValueError(f"frame CRC mismatch: {state_id}")
        if hashlib.sha256(actual).hexdigest().upper() != entry["display_sha256"]:
            raise ValueError(f"frame SHA mismatch: {state_id}")
        checked += 1

    receipt = {
        "status": "PASS_UI_ASSET_GENERATION_EQUIVALENT",
        "resource_id": generation["resource_id"],
        "page_sha256": generation["page_sha256"],
        "states_checked": checked,
        "override_states": override_count,
        "xor_patch_states": patch_count,
        "frame_bytes": FRAME_BYTES,
        "strict_1bpp": True,
        "base_cemp_sha256":
            hashlib.sha256(args.base_cemp.read_bytes()).hexdigest().upper(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, ensure_ascii=True, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(json.dumps(receipt, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
