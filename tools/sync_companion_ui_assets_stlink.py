#!/usr/bin/env python3
"""Fast development sync for Companion UI assets through ST-LINK."""

from __future__ import annotations

import argparse
import atexit
import ctypes
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

ALIAS_BASE = 0x90000000
PARTITION_BYTES = 0x00200000
SECTOR_BYTES = 4096
ROOT_BYTES = 128
ROOT_A = 0x001FE000
ROOT_B = 0x001FF000
ARENA_END = 0x001DC000
STATIC_RESOURCE_BASE = 0x001DC000
STATIC_RESOURCE_LIMIT = 0x001FD000
STATIC_RESOURCE_CAPACITY = STATIC_RESOURCE_LIMIT - STATIC_RESOURCE_BASE
CUOT_HEADER_BYTES = 96
SWD_MUTEX_NAME = "Local\\Companion-WB55-SWD-COM-Exclusive-v1"


def fail(message: str) -> None:
    raise SystemExit(f"SYNC_UI_STLINK_FAILED: {message}")


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def align_sector(value: int) -> int:
    return (value + SECTOR_BYTES - 1) & ~(SECTOR_BYTES - 1)


def parse_root(image: bytes, offset: int) -> dict[str, object] | None:
    root = image[offset : offset + ROOT_BYTES]
    if (
        len(root) != ROOT_BYTES
        or root[:4] != b"CUIR"
        or struct.unpack_from("<H", root, 4)[0] != 1
        or struct.unpack_from("<H", root, 6)[0] != ROOT_BYTES
        or crc32(root[:124]) != struct.unpack_from("<I", root, 124)[0]
    ):
        return None
    values = struct.unpack_from("<IIIIIIIII", root, 8)
    (
        generation,
        base_pack_size,
        blob_offset,
        blob_size,
        blob_crc32,
        manifest_offset,
        manifest_size,
        manifest_crc32,
        arena_next,
    ) = values
    if (
        generation == 0
        or not base_pack_size <= blob_offset < ARENA_END
        or blob_size == 0
        or blob_offset + blob_size > ARENA_END
        or manifest_size < 32
        or manifest_offset + manifest_size > blob_size
        or arena_next != align_sector(blob_offset + blob_size)
        or crc32(image[blob_offset : blob_offset + blob_size]) != blob_crc32
        or crc32(
            image[
                blob_offset + manifest_offset :
                blob_offset + manifest_offset + manifest_size
            ]
        )
        != manifest_crc32
    ):
        return None
    return {
        "generation": generation,
        "root_offset": offset,
        "base_pack_size": base_pack_size,
        "blob_offset": blob_offset,
        "blob_size": blob_size,
        "blob_crc32": blob_crc32,
        "manifest_offset": manifest_offset,
        "manifest_size": manifest_size,
        "manifest_crc32": manifest_crc32,
        "arena_next": arena_next,
        "resource_id": root[44:76],
    }


def active_root(image: bytes) -> dict[str, object] | None:
    roots = [
        root for root in (parse_root(image, ROOT_A), parse_root(image, ROOT_B))
        if root is not None
    ]
    return max(roots, key=lambda root: int(root["generation"])) if roots else None


def parse_cuot(path: Path) -> dict[str, object]:
    bundle = path.read_bytes()
    if len(bundle) <= CUOT_HEADER_BYTES:
        fail("CUOT bundle is too small")
    header = bundle[:CUOT_HEADER_BYTES]
    if (
        header[:4] != b"CUOT"
        or struct.unpack_from("<H", header, 4)[0] != 1
        or struct.unpack_from("<H", header, 6)[0] != CUOT_HEADER_BYTES
        or struct.unpack_from("<I", header, 8)[0] != 1
        or struct.unpack_from("<I", header, 12)[0] != len(bundle)
        or struct.unpack_from("<I", header, 88)[0] != 0
        or crc32(header[:92]) != struct.unpack_from("<I", header, 92)[0]
    ):
        fail("CUOT header contract is invalid")
    blob = bundle[CUOT_HEADER_BYTES:]
    blob_size = struct.unpack_from("<I", header, 32)[0]
    manifest_offset = struct.unpack_from("<I", header, 40)[0]
    manifest_size = struct.unpack_from("<I", header, 44)[0]
    if (
        blob_size != len(blob)
        or crc32(blob) != struct.unpack_from("<I", header, 36)[0]
        or manifest_size < 32
        or manifest_offset + manifest_size > blob_size
        or crc32(blob[manifest_offset : manifest_offset + manifest_size])
        != struct.unpack_from("<I", header, 48)[0]
        or header[52:84] == bytes(32)
    ):
        fail("CUOT blob or manifest contract is invalid")
    return {
        "bundle": bundle,
        "blob": blob,
        "base_pack_size": struct.unpack_from("<I", header, 16)[0],
        "base_payload_crc32": struct.unpack_from("<I", header, 20)[0],
        "base_index_crc32": struct.unpack_from("<I", header, 24)[0],
        "expected_generation": struct.unpack_from("<I", header, 28)[0],
        "blob_crc32": struct.unpack_from("<I", header, 36)[0],
        "manifest_offset": manifest_offset,
        "manifest_size": manifest_size,
        "manifest_crc32": struct.unpack_from("<I", header, 48)[0],
        "resource_id": header[52:84],
        "planned_blob_offset": struct.unpack_from("<I", header, 84)[0],
    }


def parse_static_resource_pack(path: Path) -> dict[str, object]:
    pack = path.read_bytes()
    if (
        len(pack) < 64
        or len(pack) > STATIC_RESOURCE_CAPACITY
        or pack[:4] != b"CRRP"
        or struct.unpack_from("<H", pack, 4)[0] != 1
        or struct.unpack_from("<H", pack, 6)[0] != 64
        or struct.unpack_from("<I", pack, 8)[0] != len(pack)
        or struct.unpack_from("<I", pack, 12)[0] != 2
    ):
        fail("recording resource pack header is invalid")
    entries_offset = struct.unpack_from("<I", pack, 16)[0]
    entries_bytes = struct.unpack_from("<I", pack, 20)[0]
    payload_offset = struct.unpack_from("<I", pack, 24)[0]
    payload_bytes = struct.unpack_from("<I", pack, 28)[0]
    if (
        entries_offset != 64
        or entries_bytes != 64
        or payload_offset != entries_offset + entries_bytes
        or payload_offset + payload_bytes != len(pack)
        or crc32(pack[:40]) != struct.unpack_from("<I", pack, 40)[0]
        or crc32(pack[entries_offset:payload_offset])
        != struct.unpack_from("<I", pack, 36)[0]
        or crc32(pack[payload_offset:])
        != struct.unpack_from("<I", pack, 32)[0]
    ):
        fail("recording resource pack CRC or layout is invalid")
    return {
        "path": str(path),
        "data": pack,
        "bytes": len(pack),
        "crc32": crc32(pack),
        "sha256": sha256(pack),
    }


def overlay_static_resource(
    transaction: dict[str, object],
    static_resource: dict[str, object],
) -> dict[str, object]:
    current = bytes(transaction["current"])
    desired = bytearray(bytes(transaction["desired"]))
    pack = bytes(static_resource["data"])
    region = pack + b"\xFF" * (STATIC_RESOURCE_CAPACITY - len(pack))
    desired[STATIC_RESOURCE_BASE:STATIC_RESOURCE_LIMIT] = region
    changed_static = [
        offset
        for offset in range(
            STATIC_RESOURCE_BASE,
            STATIC_RESOURCE_LIMIT,
            SECTOR_BYTES,
        )
        if current[offset : offset + SECTOR_BYTES]
        != desired[offset : offset + SECTOR_BYTES]
    ]
    changed_data = sorted(
        set(transaction["changed_data_sectors"]) | set(changed_static)
    )
    result = dict(transaction)
    result.update(
        {
            "noop": bool(transaction["noop"]) and not changed_static,
            "desired": bytes(desired),
            "changed_data_sectors": changed_data,
            "static_resource_changed_sectors": changed_static,
            "static_resource_current_match": (
                current[STATIC_RESOURCE_BASE:STATIC_RESOURCE_LIMIT]
                == region
            ),
        }
    )
    return result


def base_identity(image: bytes) -> dict[str, int]:
    if (
        image[:4] != b"CEMP"
        or struct.unpack_from("<H", image, 4)[0] != 1
        or struct.unpack_from("<H", image, 6)[0] != 80
    ):
        fail("current UI partition has no supported CEMP base")
    return {
        "bytes": struct.unpack_from("<I", image, 8)[0],
        "payload_crc32": struct.unpack_from("<I", image, 56)[0],
        "index_crc32": struct.unpack_from("<I", image, 60)[0],
    }


def optional_base_identity(image: bytes) -> dict[str, int] | None:
    if (
        len(image) < 80
        or image[:4] != b"CEMP"
        or struct.unpack_from("<H", image, 4)[0] != 1
        or struct.unpack_from("<H", image, 6)[0] != 80
    ):
        return None
    return base_identity(image)


def encode_root(cuot: dict[str, object], root_offset: int) -> bytes:
    root = bytearray(ROOT_BYTES)
    root[:4] = b"CUIR"
    struct.pack_into("<HH", root, 4, 1, ROOT_BYTES)
    blob_offset = int(cuot["planned_blob_offset"])
    blob = bytes(cuot["blob"])
    struct.pack_into(
        "<IIIIIIIII",
        root,
        8,
        int(cuot["expected_generation"]) + 1,
        int(cuot["base_pack_size"]),
        blob_offset,
        len(blob),
        int(cuot["blob_crc32"]),
        int(cuot["manifest_offset"]),
        int(cuot["manifest_size"]),
        int(cuot["manifest_crc32"]),
        align_sector(blob_offset + len(blob)),
    )
    root[44:76] = bytes(cuot["resource_id"])
    struct.pack_into("<I", root, 124, crc32(root[:124]))
    return bytes(root)


def contiguous_runs(sectors: list[int]) -> list[tuple[int, int]]:
    if not sectors:
        return []
    runs: list[tuple[int, int]] = []
    start = previous = sectors[0]
    for sector in sectors[1:]:
        if sector != previous + SECTOR_BYTES:
            runs.append((start, previous + SECTOR_BYTES))
            start = sector
        previous = sector
    runs.append((start, previous + SECTOR_BYTES))
    return runs


def generation_blob_is_self_contained(cuot: dict[str, object]) -> bool:
    blob = bytes(cuot["blob"])
    manifest_offset = int(cuot["manifest_offset"])
    manifest_size = int(cuot["manifest_size"])
    manifest = blob[manifest_offset : manifest_offset + manifest_size]
    if len(manifest) < 32 or manifest[:4] != b"CUIM":
        return False
    version, header_bytes, entry_count, entry_bytes = struct.unpack_from(
        "<HHHH", manifest, 4
    )
    declared_size = struct.unpack_from("<I", manifest, 12)[0]
    if (
        version != 1
        or header_bytes != 32
        or entry_bytes != 24
        or declared_size != manifest_size
        or header_bytes + entry_count * entry_bytes != manifest_size
    ):
        return False
    payload_start = int(cuot["planned_blob_offset"]) + manifest_size
    payload_end = int(cuot["planned_blob_offset"]) + len(blob)
    for index in range(entry_count):
        entry = struct.unpack_from(
            "<IHHIIHHI", manifest, header_bytes + index * entry_bytes
        )
        flags = entry[2]
        payload_offset = entry[4]
        payload_size = entry[5]
        if flags == 0:
            if payload_offset != 0 or payload_size != 0:
                return False
        elif (
            payload_size == 0
            or payload_offset < payload_start
            or payload_offset + payload_size > payload_end
        ):
            return False
    return True


def plan(
    current: bytes,
    cuot: dict[str, object],
    allow_generation_compaction: bool = False,
) -> dict[str, object]:
    if len(current) != PARTITION_BYTES:
        fail("current partition image must be exactly 2 MiB")
    base = base_identity(current)
    if (
        base["bytes"] != cuot["base_pack_size"]
        or base["payload_crc32"] != cuot["base_payload_crc32"]
        or base["index_crc32"] != cuot["base_index_crc32"]
    ):
        fail("CUOT base identity does not match current CEMP")
    active = active_root(current)
    generation = int(active["generation"]) if active else 0
    if generation != cuot["expected_generation"]:
        fail("CUOT expected generation is stale")
    blob = bytes(cuot["blob"])
    same_active_blob = bool(
        active
        and active["resource_id"] == cuot["resource_id"]
        and int(active["base_pack_size"]) == int(cuot["base_pack_size"])
        and int(active["blob_size"]) == len(blob)
        and int(active["blob_crc32"]) == int(cuot["blob_crc32"])
        and int(active["manifest_offset"]) == int(cuot["manifest_offset"])
        and int(active["manifest_size"]) == int(cuot["manifest_size"])
        and int(active["manifest_crc32"]) == int(cuot["manifest_crc32"])
        and current[
            int(active["blob_offset"]) :
            int(active["blob_offset"]) + int(active["blob_size"])
        ] == blob
    )
    if same_active_blob:
        return {
            "noop": True,
            "current": current,
            "desired": current,
            "active": active,
            "inactive_root": ROOT_B
            if active["root_offset"] == ROOT_A else ROOT_A,
            "changed_data_sectors": [],
            "root_sector": None,
        }

    expected_blob_offset = (
        int(active["arena_next"])
        if active else align_sector(int(cuot["base_pack_size"]))
    )
    blob_offset = int(cuot["planned_blob_offset"])
    compacting = bool(
        allow_generation_compaction
        and active
        and blob_offset == align_sector(int(cuot["base_pack_size"]))
        and blob_offset < expected_blob_offset
        and blob_offset % SECTOR_BYTES == 0
        and blob_offset + len(blob) <= ARENA_END
        and generation_blob_is_self_contained(cuot)
    )
    if not compacting and (
        blob_offset != expected_blob_offset
        or blob_offset % SECTOR_BYTES != 0
        or blob_offset + len(blob) > ARENA_END
    ):
        fail("CUOT planned blob offset does not match current arena")
    inactive_root = (
        ROOT_B if active and active["root_offset"] == ROOT_A else ROOT_A
    )
    desired = bytearray(current)
    blob_end = align_sector(blob_offset + len(blob))
    if compacting:
        desired[blob_offset:ARENA_END] = b"\xFF" * (
            ARENA_END - blob_offset
        )
    desired[blob_offset:blob_end] = b"\xFF" * (blob_end - blob_offset)
    desired[blob_offset : blob_offset + len(blob)] = blob
    desired[inactive_root : inactive_root + SECTOR_BYTES] = (
        b"\xFF" * SECTOR_BYTES
    )
    desired[inactive_root : inactive_root + ROOT_BYTES] = encode_root(
        cuot, inactive_root
    )
    active_root_offset = int(active["root_offset"]) if active else None
    changed = [
        offset
        for offset in range(0, PARTITION_BYTES, SECTOR_BYTES)
        if current[offset : offset + SECTOR_BYTES]
        != desired[offset : offset + SECTOR_BYTES]
    ]
    allowed_data = set(
        range(
            blob_offset,
            ARENA_END if compacting else blob_end,
            SECTOR_BYTES,
        )
    )
    if (
        inactive_root not in changed
        or any(
            offset not in allowed_data and offset != inactive_root
            for offset in changed
        )
        or active_root_offset in changed
    ):
        fail("sector plan escaped blob plus inactive-root contract")
    return {
        "noop": False,
        "current": current,
        "desired": bytes(desired),
        "active": active,
        "inactive_root": inactive_root,
        "changed_data_sectors": [
            offset for offset in changed if offset != inactive_root
        ],
        "root_sector": inactive_root,
        "generation_compaction": compacting,
        "abort_preserves_active_generation": not compacting,
    }


def bootstrap_plan(
    current: bytes,
    bootstrap: bytes,
    allow_base_migration: bool = False,
    allow_generation_root_recovery: bool = False,
    allow_base_repair: bool = False,
) -> dict[str, object]:
    if len(current) != PARTITION_BYTES or len(bootstrap) != PARTITION_BYTES:
        fail("bootstrap images must be exactly 2 MiB")
    active = active_root(current)
    if active is not None and not (allow_base_migration or allow_base_repair):
        fail("bootstrap is forbidden when an active generation exists")
    if allow_base_migration and allow_base_repair:
        fail("base migration and same-identity base repair are exclusive")
    if active is not None and allow_generation_root_recovery:
        fail("generation root recovery requires no active generation")
    roots = [
        root
        for root in (
            parse_root(bootstrap, ROOT_A),
            parse_root(bootstrap, ROOT_B),
        )
        if root is not None
    ]
    if len(roots) != 1:
        fail("bootstrap must contain exactly one valid generation root")
    root = roots[0]
    generation = int(root["generation"])
    root_offset = int(root["root_offset"])
    recovering_root = bool(active is None and allow_generation_root_recovery)
    if active is None:
        if not recovering_root and generation != 1:
            fail("bootstrap without an active generation must target generation 1")
    else:
        expected_generation = int(active["generation"]) + 1
        expected_root = (
            ROOT_B if int(active["root_offset"]) == ROOT_A else ROOT_A
        )
        if generation != expected_generation:
            fail("base migration must target exactly the next generation")
        if root_offset != expected_root:
            fail("base migration must commit through the inactive root")
    base = base_identity(bootstrap)
    if int(root["base_pack_size"]) != base["bytes"]:
        fail("bootstrap root and base CEMP size differ")
    if recovering_root and base_identity(current) != base:
        fail("generation root recovery requires the exact current CEMP base")
    if active is not None:
        current_base = base_identity(current)
        if current_base == base and not allow_base_repair:
            fail("base migration requires a different CEMP base identity")
        if current_base != base and allow_base_repair:
            fail("same-identity base repair requires the current CEMP identity")
        if allow_base_repair and current[: int(base["bytes"])] == \
                bootstrap[: int(base["bytes"])]:
            fail("same-identity base repair requires differing CEMP bytes")

    data_sectors = set()
    if not recovering_root:
        data_sectors.update(
            range(0, align_sector(base["bytes"]), SECTOR_BYTES)
        )
    data_sectors.update(
        range(
            int(root["blob_offset"]),
            int(root["arena_next"]),
            SECTOR_BYTES,
        )
    )
    if active is not None:
        active_blob_sectors = set(
            range(
                int(active["blob_offset"]),
                int(active["arena_next"]),
                SECTOR_BYTES,
            )
        )
        preserved_active_blob_sectors = data_sectors & active_blob_sectors
        for offset in preserved_active_blob_sectors:
            if (
                current[offset : offset + SECTOR_BYTES]
                != bootstrap[offset : offset + SECTOR_BYTES]
            ):
                fail("base migration data differs inside the active generation blob")
        # The bootstrap may intentionally reference the already-committed
        # active blob while replacing only the CEMP base. Identical sectors
        # are preserved in place and must never become write operations.
        data_sectors -= preserved_active_blob_sectors
        if int(active["root_offset"]) in data_sectors:
            fail("base migration data overlaps the active generation root")
    else:
        preserved_active_blob_sectors = set()
    desired = bytearray(current)
    changed_data: list[int] = []
    for offset in sorted(data_sectors):
        desired[offset : offset + SECTOR_BYTES] = bootstrap[
            offset : offset + SECTOR_BYTES
        ]
        if current[offset : offset + SECTOR_BYTES] != desired[
            offset : offset + SECTOR_BYTES
        ]:
            changed_data.append(offset)
    desired[root_offset : root_offset + SECTOR_BYTES] = bootstrap[
        root_offset : root_offset + SECTOR_BYTES
    ]
    if current[root_offset : root_offset + SECTOR_BYTES] == desired[
        root_offset : root_offset + SECTOR_BYTES
    ]:
        fail("bootstrap root unexpectedly already exists")
    return {
        "noop": False,
        "current": current,
        "desired": bytes(desired),
        "active": active,
        "inactive_root": root_offset,
        "changed_data_sectors": changed_data,
        "root_sector": root_offset,
        "generation_after": generation,
        "resource_id": bytes(root["resource_id"]),
        "base_migration": active is not None,
        "base_repair": active is not None and allow_base_repair,
        "generation_root_recovery": recovering_root,
        "preserved_active_blob_sectors": sorted(
            preserved_active_blob_sectors
        ),
    }


def connection_args(serial: str | None) -> list[str]:
    args = ["-c", "port=SWD"]
    if serial:
        args.append(f"sn={serial}")
    args.extend(["mode=UR", "reset=HWrst", "freq=4000"])
    return args


def acquire_swd_mutex() -> int:
    if sys.platform != "win32":
        fail("real SWD access requires Windows named-mutex support")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    ]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.CreateMutexW(None, False, SWD_MUTEX_NAME)
    if not handle:
        fail("cannot create the Companion WB55 SWD/COM mutex")
    result = kernel32.WaitForSingleObject(handle, 0)
    if result not in (0x00000000, 0x00000080):
        kernel32.CloseHandle(handle)
        fail("Companion WB55 SWD/COM lock is held; zero hardware contact")

    def release() -> None:
        kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)

    atexit.register(release)
    return int(handle)


def validate_inherited_lock() -> None:
    run_id = os.environ.get("COMPANION_WB55_LOCK_RUN_ID", "")
    evidence_path = os.environ.get(
        "COMPANION_WB55_LOCK_EVIDENCE_PATH", ""
    )
    if not run_id or not evidence_path:
        fail("workflow lock acknowledgement has no inherited lock evidence")
    path = Path(evidence_path)
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("workflow lock evidence is missing or malformed")
    if (
        evidence.get("status") != "HELD"
        or evidence.get("resource") != "Companion-WB55"
        or evidence.get("run_id") != run_id
    ):
        fail("workflow lock evidence is not an active Companion-WB55 grant")


def run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        fail(
            f"CubeProgrammer command failed ({completed.returncode}): "
            + " ".join(command)
        )
    return completed.stdout + completed.stderr


def main() -> None:
    started = time.perf_counter()
    stage_ms: dict[str, int] = {
        "live_partition_read": 0,
        "plan": 0,
        "data_write": 0,
        "root_commit": 0,
        "readback": 0,
        "ordinary_reset": 0,
    }
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle", type=Path)
    source.add_argument("--bootstrap-image", type=Path)
    parser.add_argument("--current-image", type=Path)
    parser.add_argument("--trusted-current-image", type=Path)
    parser.add_argument(
        "--recording-resource-pack",
        type=Path,
        default=repo / ".cache/validation/"
        "comp-req-775-recording-resources/"
        "companion_recording_resources.crrp",
    )
    parser.add_argument(
        "--loader",
        type=Path,
        default=repo / "tools/external_loader/wb55_spi1_nor/build/"
        "Companion_WB55_SPI1_NOR_UI_2MiB.stldr",
    )
    parser.add_argument(
        "--cubeprogrammer",
        type=Path,
        default=Path(
            "C:/ST/STM32CubeProgrammer/bin/STM32_Programmer_CLI.exe"
        ),
    )
    parser.add_argument("--probe-serial")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=repo / ".cache/validation/comp-req-775-incremental-sync/"
        "stlink-sync",
    )
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-hardware", action="store_true")
    parser.add_argument("--allow-base-migration", action="store_true")
    parser.add_argument("--allow-base-repair", action="store_true")
    parser.add_argument(
        "--allow-generation-root-recovery", action="store_true"
    )
    parser.add_argument(
        "--allow-generation-compaction", action="store_true"
    )
    parser.add_argument("--workflow-lock-held", action="store_true")
    parser.add_argument("--swd-mutex-held", action="store_true")
    args = parser.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=True)
    if not args.recording_resource_pack.exists():
        fail("recording resource pack is missing")
    static_resource = parse_static_resource_pack(
        args.recording_resource_pack
    )
    if not args.loader.exists():
        fail("external loader is missing; run its make verify target")
    if not args.dry_run and not args.allow_hardware:
        fail("real SWD access requires --allow-hardware")
    if not args.dry_run and not args.workflow_lock_held:
        fail("real SWD access must run inside the Companion-WB55 workflow lock")
    if not args.dry_run and args.current_image is not None:
        fail("hardware mode always reads the live partition; omit --current-image")
    if not args.dry_run:
        validate_inherited_lock()
        if args.swd_mutex_held:
            if os.environ.get("COMPANION_WB55_SWD_MUTEX_HELD") != "1":
                fail("inherited SWD mutex acknowledgement is not active")
        else:
            acquire_swd_mutex()

    current_path = args.current_image or args.workspace / "current.bin"
    trusted_path = (
        args.trusted_current_image
        or args.workspace / "trusted-current.bin"
    )
    commands: list[list[str]] = []
    hardware_contact = 0
    live_read_bytes = 0
    readback_bytes = 0
    read_strategy = "provided_image"
    if args.current_image is None:
        if args.dry_run:
            fail("--dry-run requires --current-image")
        stage_started = time.perf_counter()
        if trusted_path.exists():
            trusted = trusted_path.read_bytes()
            if len(trusted) != PARTITION_BYTES:
                fail("trusted current image is not exactly 2 MiB")
            prefix_path = args.workspace / "live-prefix.bin"
            roots_path = args.workspace / "live-roots.bin"
            static_path = args.workspace / "live-recording-resources.bin"
            prefix_path.unlink(missing_ok=True)
            roots_path.unlink(missing_ok=True)
            static_path.unlink(missing_ok=True)
            for address, size, output in (
                (0, SECTOR_BYTES, prefix_path),
                (
                    STATIC_RESOURCE_BASE,
                    STATIC_RESOURCE_CAPACITY,
                    static_path,
                ),
                (ROOT_A, SECTOR_BYTES * 2, roots_path),
            ):
                command = [
                    str(args.cubeprogrammer),
                    *connection_args(args.probe_serial),
                    "-el",
                    str(args.loader.resolve()),
                    "-u",
                    f"0x{ALIAS_BASE + address:08X}",
                    f"0x{size:X}",
                    str(output.resolve()),
                ]
                commands.append(command)
                run(command, args.workspace)
                hardware_contact = 1
                live_read_bytes += size
            if (
                prefix_path.read_bytes() != trusted[:SECTOR_BYTES]
                or static_path.read_bytes()
                != trusted[STATIC_RESOURCE_BASE:STATIC_RESOURCE_LIMIT]
                or roots_path.read_bytes()
                != trusted[ROOT_A : ROOT_B + SECTOR_BYTES]
            ):
                fail(
                    "trusted image does not match live CEMP, static resources, "
                    "and roots"
                )
            current_path.write_bytes(trusted)
            read_strategy = (
                "trusted_cache_with_live_header_static_resources_and_roots"
            )
        else:
            current_path.unlink(missing_ok=True)
            command = [
                str(args.cubeprogrammer),
                *connection_args(args.probe_serial),
                "-el",
                str(args.loader.resolve()),
                "-u",
                f"0x{ALIAS_BASE:08X}",
                f"0x{PARTITION_BYTES:X}",
                str(current_path.resolve()),
            ]
            commands.append(command)
            run(command, args.workspace)
            hardware_contact = 1
            live_read_bytes = PARTITION_BYTES
            read_strategy = "full_live_partition"
        stage_ms["live_partition_read"] = round(
            (time.perf_counter() - stage_started) * 1000
        )

    current = current_path.read_bytes()
    current_base = optional_base_identity(current)
    stage_started = time.perf_counter()
    if args.bundle is not None:
        cuot = parse_cuot(args.bundle)
        sync_plan = plan(
            current,
            cuot,
            allow_generation_compaction=args.allow_generation_compaction,
        )
        source_receipt = {
            "kind": "cuot",
            "path": str(args.bundle),
            "bytes": len(bytes(cuot["bundle"])),
            "sha256": sha256(bytes(cuot["bundle"])),
        }
        generation_after = (
            int(cuot["expected_generation"])
            if sync_plan["noop"]
            else int(cuot["expected_generation"]) + 1
        )
    else:
        bootstrap = args.bootstrap_image.read_bytes()
        sync_plan = bootstrap_plan(
            current,
            bootstrap,
            allow_base_migration=args.allow_base_migration,
            allow_generation_root_recovery=(
                args.allow_generation_root_recovery
            ),
            allow_base_repair=args.allow_base_repair,
        )
        source_receipt = {
            "kind": "bootstrap_partition",
            "path": str(args.bootstrap_image),
            "bytes": len(bootstrap),
            "sha256": sha256(bootstrap),
            "base_migration_allowed": bool(args.allow_base_migration),
            "base_repair_allowed": bool(args.allow_base_repair),
            "generation_root_recovery_allowed": bool(
                args.allow_generation_root_recovery
            ),
        }
        generation_after = int(sync_plan["generation_after"])
    sync_plan = overlay_static_resource(sync_plan, static_resource)
    stage_ms["plan"] = round(
        (time.perf_counter() - stage_started) * 1000
    )
    desired = bytes(sync_plan["desired"])
    desired_base = base_identity(desired)
    desired_root = active_root(desired)
    if desired_root is None or int(desired_root["generation"]) != generation_after:
        fail("planned partition has no valid target generation")
    write_bytes = 0
    write_calls = 0
    readback_verified = False
    ordinary_reset_performed = False

    if not sync_plan["noop"]:
        data_write_started = time.perf_counter()
        for index, (start, end) in enumerate(
            contiguous_runs(sync_plan["changed_data_sectors"])
        ):
            data = desired[start:end]
            path = args.workspace / f"data-run-{index:02d}.bin"
            path.write_bytes(data)
            command = [
                str(args.cubeprogrammer),
                *connection_args(args.probe_serial),
                "-el",
                str(args.loader.resolve()),
                "-d",
                str(path.resolve()),
                f"0x{ALIAS_BASE + start:08X}",
                "-v",
            ]
            commands.append(command)
            write_bytes += len(data)
            write_calls += 1
            if not args.dry_run:
                run(command, args.workspace)
                hardware_contact = 1
        stage_ms["data_write"] = round(
            (time.perf_counter() - data_write_started) * 1000
        )

        if sync_plan["root_sector"] is not None:
            root_offset = int(sync_plan["root_sector"])
            root_path = args.workspace / "inactive-root-last.bin"
            root_path.write_bytes(
                desired[root_offset : root_offset + SECTOR_BYTES]
            )
            root_command = [
                str(args.cubeprogrammer),
                *connection_args(args.probe_serial),
                "-el",
                str(args.loader.resolve()),
                "-d",
                str(root_path.resolve()),
                f"0x{ALIAS_BASE + root_offset:08X}",
                "-v",
            ]
            commands.append(root_command)
            write_bytes += SECTOR_BYTES
            write_calls += 1
            if not args.dry_run:
                root_started = time.perf_counter()
                run(root_command, args.workspace)
                stage_ms["root_commit"] = round(
                    (time.perf_counter() - root_started) * 1000
                )
                hardware_contact = 1

        if not args.dry_run:
            readback_started = time.perf_counter()
            readback_ranges = contiguous_runs(
                sync_plan["changed_data_sectors"]
            )
            if sync_plan["root_sector"] is not None:
                readback_ranges.append((
                    int(sync_plan["root_sector"]),
                    int(sync_plan["root_sector"]) + SECTOR_BYTES,
                ))
            for index, (start, end) in enumerate(readback_ranges):
                readback_path = (
                    args.workspace / f"readback-run-{index:02d}.bin"
                )
                readback_path.unlink(missing_ok=True)
                readback_command = [
                    str(args.cubeprogrammer),
                    *connection_args(args.probe_serial),
                    "-el",
                    str(args.loader.resolve()),
                    "-u",
                    f"0x{ALIAS_BASE + start:08X}",
                    f"0x{end - start:X}",
                    str(readback_path.resolve()),
                ]
                commands.append(readback_command)
                run(readback_command, args.workspace)
                observed = readback_path.read_bytes()
                if observed != desired[start:end]:
                    fail(
                        "selective readback differs from the planned partition"
                    )
                readback_bytes += end - start
            trusted_path.write_bytes(desired)
            stage_ms["readback"] = round(
                (time.perf_counter() - readback_started) * 1000
            )
            readback_verified = True

    if not args.dry_run:
        if sync_plan["noop"]:
            readback_verified = current == desired
            trusted_path.write_bytes(desired)
        reset_command = [
            str(args.cubeprogrammer),
            *connection_args(args.probe_serial),
            "-rst",
        ]
        commands.append(reset_command)
        reset_started = time.perf_counter()
        run(reset_command, args.workspace)
        stage_ms["ordinary_reset"] = round(
            (time.perf_counter() - reset_started) * 1000
        )
        ordinary_reset_performed = True

    elapsed_ms = round((time.perf_counter() - started) * 1000)

    receipt = {
        "schema": "companion.ui_asset_stlink_sync.v1",
        "status": "MACHINE_READY" if args.dry_run else "COMPLETE",
        "mode": "dry_run" if args.dry_run else "hardware",
        "source": source_receipt,
        "bundle": source_receipt if args.bundle is not None else None,
        "current_partition_sha256": sha256(current),
        "desired_partition_sha256": sha256(desired),
        "readback_partition_sha256": (
            sha256(desired) if readback_verified else None
        ),
        "partition_readback_verified": readback_verified,
        "read_strategy": read_strategy,
        "live_read_bytes": live_read_bytes,
        "selective_readback_bytes": readback_bytes,
        "trusted_current_image": str(trusted_path),
        "active_generation_before": int(sync_plan["active"]["generation"])
        if sync_plan["active"] else 0,
        "active_generation_after": generation_after,
        "cemp": {
            "base_migration_allowed": bool(args.allow_base_migration),
            "base_migrated": bool(
                args.bootstrap_image is not None
                and sync_plan.get("base_migration", False)
            ),
            "generation_root_recovered": bool(
                args.bootstrap_image is not None
                and sync_plan.get("generation_root_recovery", False)
            ),
            "current": (
                {
                    **current_base,
                    "sha256": sha256(
                        current[: int(current_base["bytes"])]
                    ),
                }
                if current_base is not None
                else None
            ),
            "target": {
                **desired_base,
                "sha256": sha256(
                    desired[: int(desired_base["bytes"])]
                ),
            },
        },
        "target_root": {
            "generation": int(desired_root["generation"]),
            "offset": f"0x{int(desired_root['root_offset']):06X}",
            "blob_offset": f"0x{int(desired_root['blob_offset']):06X}",
            "blob_bytes": int(desired_root["blob_size"]),
            "blob_crc32": int(desired_root["blob_crc32"]),
            "manifest_offset": int(desired_root["manifest_offset"]),
            "manifest_bytes": int(desired_root["manifest_size"]),
            "manifest_crc32": int(desired_root["manifest_crc32"]),
            "resource_id": bytes(desired_root["resource_id"]).hex().upper(),
        },
        "recording_resource_pack": {
            "offset": f"0x{STATIC_RESOURCE_BASE:06X}",
            "limit": f"0x{STATIC_RESOURCE_LIMIT:06X}",
            "capacity_bytes": STATIC_RESOURCE_CAPACITY,
            "pack_bytes": int(static_resource["bytes"]),
            "pack_crc32": int(static_resource["crc32"]),
            "pack_sha256": str(static_resource["sha256"]),
            "current_match": bool(
                sync_plan["static_resource_current_match"]
            ),
            "changed_sector_count": len(
                sync_plan["static_resource_changed_sectors"]
            ),
            "readback_verified": bool(readback_verified),
        },
        "noop": bool(sync_plan["noop"]),
        "generation_compaction": bool(
            sync_plan.get("generation_compaction", False)
        ),
        "abort_preserves_active_generation": bool(
            sync_plan.get("abort_preserves_active_generation", True)
        ),
        "changed_data_sectors": [
            f"0x{offset:06X}"
            for offset in sync_plan["changed_data_sectors"]
        ],
        "inactive_root_last": None
        if sync_plan["root_sector"] is None
        else f"0x{int(sync_plan['root_sector']):06X}",
        "external_flash_write_bytes": write_bytes,
        "external_flash_write_calls": write_calls,
        "internal_flash_write_bytes": 0,
        "loader_partition_bytes": PARTITION_BYTES,
        "recording_partition_write_bytes": 0,
        "protected_partitions": {
            "ui_alias_start": f"0x{ALIAS_BASE:08X}",
            "ui_alias_end_exclusive": (
                f"0x{ALIAS_BASE + PARTITION_BYTES:08X}"
            ),
            "loader_internal_flash_write_bytes": 0,
            "ota_app_internal_flash_write_bytes": 0,
            "other_internal_flash_write_bytes": 0,
            "recording_partition_write_bytes": 0,
            "fus_write_bytes": 0,
            "otp_write_bytes": 0,
            "option_byte_write_bytes": 0,
            "mass_erase_calls": 0,
        },
        "commands": commands,
        "timing_ms": {
            **stage_ms,
            "total": elapsed_ms,
        },
        "performance_contract": {
            "evaluated_on_hardware": not args.dry_run,
            "same_resource_under_10s": (
                elapsed_ms <= 10000
                if not args.dry_run and sync_plan["noop"]
                else None
            ),
            "changed_resource_under_30s": (
                elapsed_ms <= 30000
                if not args.dry_run and not sync_plan["noop"]
                else None
            ),
        },
        "ordinary_reset_performed": ordinary_reset_performed,
        "workflow_lock_acknowledged": (
            args.workflow_lock_held if not args.dry_run else False
        ),
        "swd_mutex": SWD_MUTEX_NAME if not args.dry_run else None,
        "swd_mutex_inherited": (
            args.swd_mutex_held if not args.dry_run else False
        ),
        "hardware_contact": hardware_contact,
    }
    receipt_path = args.receipt or args.workspace / "sync-receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
