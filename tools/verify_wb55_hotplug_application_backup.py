#!/usr/bin/env python3
"""Validate two WB55 application uploads and an optional post-restore upload."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

APPLICATION_BYTES = 0x80000
SRAM_MIN = 0x20000000
SRAM_MAX = 0x2003FFFF
FLASH_MIN = 0x08000000
FLASH_MAX = 0x0807FFFF


class BackupError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def validate_image(data: bytes, label: str) -> dict:
    if len(data) != APPLICATION_BYTES:
        raise BackupError(f"{label}: expected {APPLICATION_BYTES} bytes, got {len(data)}")
    if data == bytes(APPLICATION_BYTES):
        raise BackupError(f"{label}: all-zero image")
    if data == bytes([0xFF]) * APPLICATION_BYTES:
        raise BackupError(f"{label}: all-FF image")
    msp, reset_vector = struct.unpack_from("<II", data, 0)
    if not SRAM_MIN <= msp <= SRAM_MAX or msp % 8 != 0:
        raise BackupError(f"{label}: invalid MSP 0x{msp:08X}")
    if reset_vector & 1 != 1:
        raise BackupError(f"{label}: reset vector is not Thumb 0x{reset_vector:08X}")
    reset_address = reset_vector & ~1
    if not FLASH_MIN <= reset_address <= FLASH_MAX:
        raise BackupError(f"{label}: reset vector outside application flash 0x{reset_vector:08X}")
    return {
        "bytes": len(data),
        "sha256": sha256(data),
        "vector": {
            "msp_hex": f"0x{msp:08X}",
            "msp_8_byte_aligned": True,
            "reset_vector_hex": f"0x{reset_vector:08X}",
            "reset_vector_thumb": True,
            "reset_address_hex": f"0x{reset_address:08X}",
        },
    }


def validate_pair(backup_a: bytes, backup_b: bytes, restore_verify: bytes | None = None) -> dict:
    a = validate_image(backup_a, "backup-a")
    b = validate_image(backup_b, "backup-b")
    if backup_a != backup_b:
        raise BackupError("backup-a and backup-b differ")
    result = {
        "schema_id": "companion.wb55.hotplug_application_backup.v1",
        "status": "PASS_DUAL_HOTPLUG_APPLICATION_BACKUP",
        "address_hex": "0x08000000",
        "length_hex": "0x80000",
        "length_bytes": APPLICATION_BYTES,
        "backup_a": a,
        "backup_b": b,
        "byte_identical": True,
        "shared_sha256": a["sha256"],
        "identity_claim": "CAPTURED_PRE_RUN_APPLICATION_BYTES",
        "e199_hex_file_hash_claim": False,
    }
    if restore_verify is not None:
        restored = validate_image(restore_verify, "restore-verify")
        if restore_verify != backup_a:
            raise BackupError("restore-verify differs from backup-a")
        result["status"] = "PASS_DUAL_BACKUP_AND_POST_RESTORE_COMPARE"
        result["restore_verify"] = restored
        result["restored_byte_identical"] = True
        result["restore_identity"] = "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES"
    return result


def valid_fixture() -> bytes:
    data = bytearray([0xFF]) * APPLICATION_BYTES
    struct.pack_into("<II", data, 0, 0x20030000, 0x08000101)
    data[0x100:0x108] = b"COMPTEST"
    return bytes(data)


def self_test() -> None:
    valid = valid_fixture()
    assert validate_pair(valid, valid)["status"] == "PASS_DUAL_HOTPLUG_APPLICATION_BACKUP"
    assert validate_pair(valid, valid, valid)["status"] == "PASS_DUAL_BACKUP_AND_POST_RESTORE_COMPARE"
    cases: dict[str, tuple[bytes, bytes, bytes | None]] = {
        "short": (valid[:-1], valid, None),
        "long": (valid + b"\xFF", valid, None),
        "mismatch": (valid, valid[:-1] + b"\x00", None),
        "bad_msp_range": (struct.pack("<I", 0x10000000) + valid[4:], valid, None),
        "bad_msp_alignment": (struct.pack("<I", 0x20030004) + valid[4:], valid, None),
        "bad_reset_thumb": (valid[:4] + struct.pack("<I", 0x08000100) + valid[8:], valid, None),
        "bad_reset_range": (valid[:4] + struct.pack("<I", 0x08080001) + valid[8:], valid, None),
        "all00": (bytes(APPLICATION_BYTES), bytes(APPLICATION_BYTES), None),
        "allff": (bytes([0xFF]) * APPLICATION_BYTES, bytes([0xFF]) * APPLICATION_BYTES, None),
        "restore_mismatch": (valid, valid, valid[:-1] + b"\x00"),
    }
    for name, inputs in cases.items():
        try:
            validate_pair(*inputs)
        except BackupError:
            continue
        raise AssertionError(f"negative fixture unexpectedly passed: {name}")
    print("PASS: WB55 HOTPLUG application backup positive/negative self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-a", type=Path)
    parser.add_argument("--backup-b", type=Path)
    parser.add_argument("--restore-verify", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.backup_a is None or args.backup_b is None or args.out is None:
        parser.error("--backup-a, --backup-b and --out are required unless --self-test is used")
    try:
        result = validate_pair(
            args.backup_a.read_bytes(),
            args.backup_b.read_bytes(),
            args.restore_verify.read_bytes() if args.restore_verify else None,
        )
    except (BackupError, OSError) as exc:
        print(f"NO_GO: {exc}", file=sys.stderr)
        return 1
    result["private_files"] = {
        "backup_a": str(args.backup_a),
        "backup_b": str(args.backup_b),
        "restore_verify": str(args.restore_verify) if args.restore_verify else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
