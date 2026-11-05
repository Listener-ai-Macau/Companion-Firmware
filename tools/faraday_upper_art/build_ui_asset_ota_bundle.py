#!/usr/bin/env python3
"""Wrap a UI generation blob in the Companion resource-OTA envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

HEADER_BYTES = 96
FORMAT_VERSION = 1
TARGET_UI_GENERATION = 1
CEMP_HEADER_BYTES = 80


def fail(message: str) -> None:
    raise SystemExit(f"BUILD_UI_ASSET_OTA_FAILED: {message}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def load_base_identity(path: Path) -> dict[str, int | str]:
    data = path.read_bytes()
    if len(data) < CEMP_HEADER_BYTES or data[:4] != b"CEMP":
        fail("base pack is not CEMP")
    version, header_bytes = struct.unpack_from("<HH", data, 4)
    total_bytes = struct.unpack_from("<I", data, 8)[0]
    if version != 1 or header_bytes != CEMP_HEADER_BYTES:
        fail("unsupported CEMP header")
    if total_bytes != len(data):
        fail("CEMP declared size does not match file size")
    return {
        "path": str(path),
        "bytes": total_bytes,
        "payload_crc32": struct.unpack_from("<I", data, 56)[0],
        "index_crc32": struct.unpack_from("<I", data, 60)[0],
        "sha256": sha256(data),
    }


def build(args: argparse.Namespace) -> dict[str, object]:
    metadata = json.loads(args.generation.read_text(encoding="utf-8"))
    blob = args.blob.read_bytes()
    base = load_base_identity(args.base_cemp)
    resource_hex = metadata.get("resource_id", "")
    try:
        resource_id = bytes.fromhex(resource_hex)
    except ValueError:
        fail("generation resource_id is not hexadecimal")
    if len(resource_id) != 32 or resource_id == bytes(32):
        fail("generation resource_id must be a nonzero 32-byte value")
    if metadata.get("blob_bytes") != len(blob):
        fail("generation blob size mismatch")
    if metadata.get("blob_crc32") != crc32(blob):
        fail("generation blob CRC mismatch")
    manifest_offset = int(metadata.get("manifest_offset", 0))
    manifest_bytes = int(metadata.get("manifest_bytes", 0))
    if (
        manifest_offset < 0
        or manifest_bytes < 32
        or manifest_offset > len(blob)
        or manifest_bytes > len(blob) - manifest_offset
    ):
        fail("generation manifest range is invalid")
    manifest = blob[manifest_offset : manifest_offset + manifest_bytes]
    if metadata.get("manifest_crc32") != crc32(manifest):
        fail("generation manifest CRC mismatch")
    planned_blob_offset = (
        args.planned_blob_offset
        if args.planned_blob_offset is not None
        else int(metadata.get("planned_blob_offset", -1))
    )
    if not 0 <= planned_blob_offset < 0x001DC000:
        fail("generation planned blob offset is invalid")

    bundle_bytes = HEADER_BYTES + len(blob)
    header = bytearray(HEADER_BYTES)
    header[:4] = b"CUOT"
    struct.pack_into(
        "<HHIIIIIIIIIII",
        header,
        4,
        FORMAT_VERSION,
        HEADER_BYTES,
        TARGET_UI_GENERATION,
        bundle_bytes,
        int(base["bytes"]),
        int(base["payload_crc32"]),
        int(base["index_crc32"]),
        args.expected_active_generation,
        len(blob),
        crc32(blob),
        manifest_offset,
        manifest_bytes,
        crc32(manifest),
    )
    header[52:84] = resource_id
    struct.pack_into("<I", header, 84, planned_blob_offset)
    struct.pack_into("<I", header, 92, crc32(header[:92]))
    bundle = bytes(header) + blob
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(bundle)

    receipt = {
        "schema": "companion.ui_asset_ota_bundle.v1",
        "status": "MACHINE_READY",
        "format": {
            "magic": "CUOT",
            "version": FORMAT_VERSION,
            "header_bytes": HEADER_BYTES,
            "target": "ui_generation",
        },
        "bundle": {
            "path": str(args.output),
            "bytes": len(bundle),
            "crc32": crc32(bundle),
            "sha256": sha256(bundle),
        },
        "base_cemp": base,
        "generation": {
            "expected_active_generation": args.expected_active_generation,
            "resource_id": resource_hex.upper(),
            "blob_bytes": len(blob),
            "blob_crc32": crc32(blob),
            "manifest_offset": manifest_offset,
            "manifest_bytes": manifest_bytes,
            "manifest_crc32": crc32(manifest),
            "planned_blob_offset": planned_blob_offset,
        },
        "activation": {
            "commit": "inactive_root_last",
            "abort_preserves_active_generation": True,
            "partition_bytes": 0x00200000,
        },
        "hardware_contact": 0,
    }
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blob", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--base-cemp", type=Path, required=True)
    parser.add_argument(
        "--expected-active-generation", type=int, required=True
    )
    parser.add_argument("--planned-blob-offset", type=lambda value: int(value, 0))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if not 0 <= args.expected_active_generation <= 0xFFFFFFFE:
        fail("expected generation is outside uint32 range")
    print(json.dumps(build(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
