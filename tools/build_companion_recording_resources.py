#!/usr/bin/env python3
"""Build the external CRRP recording-diagnostic resource pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G7_SOURCE = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/"
    "companion_g7_speech_pcm.h"
)
OPUS_SOURCE = (
    ROOT
    / "app/companion_pendant/recording/companion_opus16_fixture_blob.h"
)
DEFAULT_OUT = (
    ROOT
    / ".cache/validation/comp-req-775-recording-resources/"
    "companion_recording_resources.crrp"
)

MAGIC = b"CRRP"
VERSION = 1
HEADER_BYTES = 64
ENTRY_BYTES = 32
ENTRY_COUNT = 2
PACK_BASE = 0x001DC000
PACK_CAPACITY = 0x00021000
PACK_LIMIT = 0x001FD000
FLASH_TEST_SCRATCH_BASE = 0x001FD000
FLASH_TEST_SCRATCH_BYTES = 0x00001000
UI_GENERATION_ROOT_A = 0x001FE000
RECORDING_BASE = 0x00200000
RECORDING_LIMIT = 0x01000000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def extract_array(path: Path, symbol: str, expected_bytes: int) -> bytes:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"\b{re.escape(symbol)}\s*\[[^\]]+\]\s*=\s*\{{(.*?)\}}\s*;",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"array {symbol} not found in {path}")
    data = bytes(int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]{1,2})", match.group(1)))
    if len(data) != expected_bytes:
        raise ValueError(
            f"{symbol} bytes={len(data)} expected={expected_bytes}"
        )
    return data


def build_pack() -> tuple[bytes, dict[str, object]]:
    if PACK_BASE + PACK_CAPACITY != PACK_LIMIT:
        raise AssertionError("recording resource capacity does not reach pack limit")
    if (
        FLASH_TEST_SCRATCH_BASE != PACK_LIMIT
        or FLASH_TEST_SCRATCH_BASE + FLASH_TEST_SCRATCH_BYTES
        != UI_GENERATION_ROOT_A
    ):
        raise AssertionError("flash-test scratch does not fill the pre-root sector")

    g7 = extract_array(G7_SOURCE, "COMPANION_G7_SPEECH_PCM", 112000)
    opus = extract_array(
        OPUS_SOURCE, "COMPANION_OPUS16_FIXTURE_BLOB", 21723
    )
    payload_offset = HEADER_BYTES + ENTRY_BYTES * ENTRY_COUNT
    resources = [
        (1, "g7_speech_pcm", g7, 640, 175),
        (2, "opus16_fixture", opus, 12000, 0),
    ]

    entries = bytearray()
    payload = bytearray()
    manifest_entries: list[dict[str, object]] = []
    for resource_id, name, data, aux0, aux1 in resources:
        data_offset = payload_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        entries += struct.pack(
            "<8I",
            resource_id,
            data_offset,
            len(data),
            crc,
            aux0,
            aux1,
            0,
            0,
        )
        payload += data
        manifest_entries.append(
            {
                "id": resource_id,
                "name": name,
                "offset": data_offset,
                "bytes": len(data),
                "crc32": f"{crc:08X}",
                "sha256": sha256(data),
                "aux0": aux0,
                "aux1": aux1,
            }
        )

    total_bytes = payload_offset + len(payload)
    if total_bytes > PACK_CAPACITY:
        raise ValueError(
            f"pack bytes={total_bytes} exceeds capacity={PACK_CAPACITY}"
        )
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF
    payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
    header_prefix = struct.pack(
        "<4sHH8I",
        MAGIC,
        VERSION,
        HEADER_BYTES,
        total_bytes,
        ENTRY_COUNT,
        HEADER_BYTES,
        len(entries),
        payload_offset,
        len(payload),
        payload_crc,
        entries_crc,
    )
    if len(header_prefix) != 40:
        raise AssertionError(len(header_prefix))
    header_crc = zlib.crc32(header_prefix) & 0xFFFFFFFF
    header = header_prefix + struct.pack("<I", header_crc) + bytes(20)
    pack = header + bytes(entries) + bytes(payload)
    if len(pack) != total_bytes:
        raise AssertionError((len(pack), total_bytes))

    manifest: dict[str, object] = {
        "schema_id": "companion-recording-resource-pack-v1",
        "status": "MACHINE_READY_OFFLINE",
        "format": {
            "magic": MAGIC.decode("ascii"),
            "version": VERSION,
            "header_bytes": HEADER_BYTES,
            "entry_bytes": ENTRY_BYTES,
            "entry_count": ENTRY_COUNT,
        },
        "placement": {
            "ui_assets": {
                "base": "0x00000000",
                "limit": "0x00200000",
                "generation_arena_limit": f"0x{PACK_BASE:08X}",
            },
            "recording": {
                "base": f"0x{RECORDING_BASE:08X}",
                "limit": f"0x{RECORDING_LIMIT:08X}",
            },
            "recording_resources": {
                "base": f"0x{PACK_BASE:08X}",
                "capacity_bytes": PACK_CAPACITY,
                "used_bytes": total_bytes,
                "limit": f"0x{PACK_LIMIT:08X}",
            },
            "flash_test_scratch": {
                "base": f"0x{FLASH_TEST_SCRATCH_BASE:08X}",
                "bytes": FLASH_TEST_SCRATCH_BYTES,
                "limit": f"0x{UI_GENERATION_ROOT_A:08X}",
            },
        },
        "pack": {
            "bytes": total_bytes,
            "crc32": f"{zlib.crc32(pack) & 0xFFFFFFFF:08X}",
            "sha256": sha256(pack),
            "payload_bytes": len(payload),
            "payload_crc32": f"{payload_crc:08X}",
            "entries_crc32": f"{entries_crc:08X}",
            "header_crc32": f"{header_crc:08X}",
        },
        "resources": manifest_entries,
        "sources": [
            {
                "path": G7_SOURCE.relative_to(ROOT).as_posix(),
                "sha256": sha256(G7_SOURCE.read_bytes()),
            },
            {
                "path": OPUS_SOURCE.relative_to(ROOT).as_posix(),
                "sha256": sha256(OPUS_SOURCE.read_bytes()),
            },
        ],
        "hardware_contact": 0,
    }
    return pack, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    manifest_path = output.with_suffix(".json")
    pack, manifest = build_pack()
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not output.exists() or output.read_bytes() != pack:
            raise SystemExit(f"stale or missing pack: {output}")
        if not manifest_path.exists() or manifest_path.read_text(
            encoding="utf-8"
        ) != manifest_text:
            raise SystemExit(f"stale or missing manifest: {manifest_path}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(pack)
        manifest_path.write_text(manifest_text, encoding="utf-8")
    print(
        "PASS_RECORDING_RESOURCE_BUILD "
        f"bytes={len(pack)} sha256={manifest['pack']['sha256']} "
        "hardware_contact=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
