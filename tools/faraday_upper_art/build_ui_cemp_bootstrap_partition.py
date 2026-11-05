#!/usr/bin/env python3
"""Build a verified 2 MiB UI NOR image from one CEMP and generation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


PARTITION_BYTES = 0x200000
SECTOR_BYTES = 0x1000
ARENA_END = 0x1DC000
STATIC_RESOURCE_OFFSET = 0x1DC000
STATIC_RESOURCE_LIMIT = 0x1FD000
ROOT_A_OFFSET = 0x1FE000
ROOT_B_OFFSET = 0x1FF000
ROOT_BYTES = 128


def align_sector(value: int) -> int:
    return (value + SECTOR_BYTES - 1) & ~(SECTOR_BYTES - 1)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cemp", required=True, type=Path)
    parser.add_argument("--generation-blob", required=True, type=Path)
    parser.add_argument("--generation", required=True, type=Path)
    parser.add_argument("--static-resource", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--root-generation", type=int)
    parser.add_argument(
        "--root-offset",
        type=lambda value: int(value, 0),
        choices=(ROOT_A_OFFSET, ROOT_B_OFFSET),
        default=ROOT_A_OFFSET,
    )
    args = parser.parse_args()

    cemp = args.cemp.read_bytes()
    blob = args.generation_blob.read_bytes()
    generation = json.loads(args.generation.read_text(encoding="ascii"))
    static_resource = args.static_resource.read_bytes()
    if len(cemp) < 80 or cemp[:4] != b"CEMP":
        raise ValueError("input CEMP is invalid")
    if struct.unpack_from("<I", cemp, 8)[0] != len(cemp):
        raise ValueError("CEMP declared size differs")
    blob_offset = int(generation["planned_blob_offset"])
    if (
        blob_offset < align_sector(len(cemp))
        or blob_offset % SECTOR_BYTES != 0
    ):
        raise ValueError(
            "generation blob must use a sector-aligned address after CEMP"
        )
    if len(blob) != int(generation["blob_bytes"]):
        raise ValueError("generation blob size differs")
    if zlib.crc32(blob) != int(generation["blob_crc32"]):
        raise ValueError("generation blob CRC differs")
    manifest_size = int(generation["manifest_bytes"])
    if manifest_size > len(blob):
        raise ValueError("generation manifest exceeds blob")
    if zlib.crc32(blob[:manifest_size]) != int(
        generation["manifest_crc32"]
    ):
        raise ValueError("generation manifest CRC differs")
    arena_next = align_sector(blob_offset + len(blob))
    if arena_next > ARENA_END:
        raise ValueError("CEMP plus generation exceeds UI arena")
    if len(static_resource) > STATIC_RESOURCE_LIMIT - STATIC_RESOURCE_OFFSET:
        raise ValueError("static resource exceeds its partition")

    root = bytearray(b"\xFF" * ROOT_BYTES)
    struct.pack_into("<4sHH", root, 0, b"CUIR", 1, ROOT_BYTES)
    root_generation = (
        args.root_generation
        if args.root_generation is not None
        else int(generation["generation"])
    )
    if root_generation <= 0:
        raise ValueError("root generation must be positive")
    struct.pack_into(
        "<IIIIIIIII",
        root,
        8,
        root_generation,
        len(cemp),
        blob_offset,
        len(blob),
        zlib.crc32(blob),
        0,
        manifest_size,
        zlib.crc32(blob[:manifest_size]),
        arena_next,
    )
    resource_id = bytes.fromhex(generation["resource_id"])
    if len(resource_id) != 32:
        raise ValueError("resource id must be SHA-256 sized")
    root[44:76] = resource_id
    struct.pack_into("<I", root, 124, zlib.crc32(root[:124]))

    partition = bytearray(b"\xFF" * PARTITION_BYTES)
    partition[: len(cemp)] = cemp
    partition[blob_offset : blob_offset + len(blob)] = blob
    partition[
        STATIC_RESOURCE_OFFSET :
        STATIC_RESOURCE_OFFSET + len(static_resource)
    ] = static_resource
    partition[args.root_offset : args.root_offset + ROOT_BYTES] = root

    checks = {
        "cemp_at_zero": partition[:4] == b"CEMP",
        "generation_blob_after_cemp": blob_offset >= len(cemp),
        "generation_within_ui_arena": arena_next <= ARENA_END,
        "recording_resource_preserved": (
            partition[
                STATIC_RESOURCE_OFFSET :
                STATIC_RESOURCE_OFFSET + 4
            ]
            == b"CRRP"
        ),
        "selected_root_commits_generation": (
            partition[args.root_offset : args.root_offset + 4] == b"CUIR"
        ),
        "other_root_inactive": (
            partition[
                (
                    ROOT_B_OFFSET
                    if args.root_offset == ROOT_A_OFFSET
                    else ROOT_A_OFFSET
                ) :
                (
                    ROOT_B_OFFSET
                    if args.root_offset == ROOT_A_OFFSET
                    else ROOT_A_OFFSET
                )
                + SECTOR_BYTES
            ]
            == b"\xFF" * SECTOR_BYTES
        ),
    }
    if not all(checks.values()):
        raise ValueError(f"bootstrap partition checks failed: {checks}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(partition)
    receipt = {
        "schema": "companion.ui_cemp_bootstrap_partition.v1",
        "status": "MACHINE_READY",
        "checks": checks,
        "partition": {
            "bytes": len(partition),
            "sha256": sha256(partition),
        },
        "cemp": {
            "bytes": len(cemp),
            "sha256": sha256(cemp),
        },
        "generation": {
            "number": root_generation,
            "resource_id": generation["resource_id"],
            "blob_offset": blob_offset,
            "blob_bytes": len(blob),
            "blob_sha256": sha256(blob),
            "arena_next": arena_next,
            "root_offset": args.root_offset,
        },
        "static_resource": {
            "offset": STATIC_RESOURCE_OFFSET,
            "bytes": len(static_resource),
            "sha256": sha256(static_resource),
        },
        "hardware_contact": 0,
    }
    args.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
