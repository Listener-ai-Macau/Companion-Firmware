#!/usr/bin/env python3
"""Verify the current browser frame map through the existing CEMP decoder format."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_emote_asset_pack import decode_packbits


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_p4(path: Path) -> bytes:
    data = path.read_bytes()
    marker = b"P4\n200 200\n"
    if not data.startswith(marker):
        raise ValueError(f"invalid PBM header: {path}")
    return bytes(value ^ 0xFF for value in data[len(marker):len(marker) + 5000])


def read_c_string(table: bytes, offset: int) -> str:
    if offset >= len(table):
        raise ValueError("string offset out of bounds")
    end = table.find(b"\0", offset)
    if end < 0:
        raise ValueError("unterminated string")
    return table[offset:end].decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    pack_path = args.pack.resolve()
    source_path = args.source_pack_manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = json.loads(source_path.read_text(encoding="utf-8"))
    pack = pack_path.read_bytes()
    checks: dict[str, bool] = {}
    failures: list[str] = []

    def require(name: str, value: bool) -> None:
        checks[name] = bool(value)
        if not value:
            failures.append(name)

    require("manifest_schema", manifest.get("schema") == "companion.emote_asset_pack_manifest.v1")
    require("source_page_identity", manifest.get("source", {}).get("browser_page_sha256") == source["source"]["page_sha256"])
    require("source_pack_identity", manifest.get("source", {}).get("source_pack_manifest_sha256") == sha256(source_path.read_bytes()))
    require("pack_size_header", len(pack) >= 80)
    if len(pack) < 80:
        header = b""
    else:
        header = pack[:80]
    magic, version, header_size = header[:4], *struct.unpack_from("<HH", header, 4)
    require("header", magic == b"CEMP" and version == 1 and header_size == 80)

    if len(header) == 80:
        total_size, revision, priority, flags = struct.unpack_from("<IIHH", header, 8)
        width, height, stride, pixel_format, encoding, clip_count, frame_count = struct.unpack_from("<HHHBBHH", header, 20)
        clip_offset, frame_offset, string_offset, string_size, payload_offset, payload_size, payload_crc, index_crc = struct.unpack_from("<IIIIIIII", header, 32)
    else:
        total_size = revision = priority = flags = width = height = stride = pixel_format = encoding = clip_count = frame_count = 0
        clip_offset = frame_offset = string_offset = string_size = payload_offset = payload_size = payload_crc = index_crc = 0

    require("profile", (width, height, stride, pixel_format, encoding) == (200, 200, 25, 1, 2))
    expected_clip_count = int(manifest.get("source", {}).get("clip_count", len(source["states"])))
    expected_frame_count = int(manifest.get("source", {}).get("frame_count", len(source["states"])))
    manifest_frame_count = sum(len(clip.get("frames", [])) for clip in manifest.get("clips", []))
    require("catalog_counts", clip_count == expected_clip_count and frame_count == expected_frame_count
            and len(manifest.get("clips", [])) == expected_clip_count
            and manifest_frame_count == expected_frame_count)
    require("total_size", total_size == len(pack) and payload_offset + payload_size == len(pack))
    index_end = string_offset + string_size
    require("index_bounds", clip_offset == 80 and clip_offset <= frame_offset <= string_offset <= index_end <= len(pack))
    index_bytes = pack[clip_offset:index_end]
    require("index_crc", (zlib.crc32(index_bytes) & 0xFFFFFFFF) == index_crc)
    require("payload_crc", (zlib.crc32(pack[payload_offset:payload_offset + payload_size]) & 0xFFFFFFFF) == payload_crc)

    strings = pack[string_offset:index_end]
    states = source["states"]
    clips_by_name: dict[str, tuple] = {}
    for index in range(clip_count):
        clip_at = clip_offset + index * 16
        name_offset, first_frame, count, loop_start, loop_end, _ = struct.unpack_from(
            "<IHHHHI", pack, clip_at
        )
        clips_by_name[read_c_string(strings, name_offset)] = (
            first_frame, count, loop_start, loop_end
        )
    state_checks = []
    state_map = manifest.get("source", {}).get("state_to_canonical_frame", {})
    for state in states:
        unique_index = state_map.get(state["id"])
        clip = clips_by_name.get(f"frame_{int(unique_index):04d}") if unique_index is not None else None
        if clip is None:
            state_checks.append(False)
            continue
        first_frame, count, loop_start, loop_end = clip
        frame_at = frame_offset + first_frame * 20
        if frame_at + 20 > len(pack):
            state_checks.append(False)
            continue
        data_offset, data_size, duration_ms, dirty_x, dirty_y, dirty_w, dirty_h, _ = struct.unpack_from("<IIHHHHHH", pack, frame_at)
        try:
            expected = read_p4(source_path.parent / state["pbm_file"])
            encoded = pack[payload_offset + data_offset:payload_offset + data_offset + data_size]
            decoded = decode_packbits(encoded, 5000)
            valid = (count == 1 and loop_start == 0 and loop_end == 1 and duration_ms == 480
                     and dirty_x == dirty_y == dirty_w == dirty_h == 0
                     and decoded == expected)
        except (ValueError, IndexError):
            valid = False
        state_checks.append(valid)
    require("state_frame_roundtrip", len(state_checks) == len(states) and all(state_checks))
    require("external_payload_size", payload_size < len(source["states"]) * 5000)

    result = {
        "schema": "companion.comp_req_638.cemp_verification.v1",
        "status": "PASS_CEMP_EXTERNAL_SOURCE_BOUND" if not failures else "NO_GO_CEMP",
        "manifest_sha256": sha256(manifest_path.read_bytes()),
        "pack_sha256": sha256(pack),
        "pack_bytes": len(pack),
        "payload_bytes": payload_size,
        "checks": checks,
        "failures": failures,
        "clip_count": clip_count,
        "frame_count": frame_count,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
