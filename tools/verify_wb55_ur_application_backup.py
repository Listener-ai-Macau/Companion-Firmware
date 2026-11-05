#!/usr/bin/env python3
"""Validate two read-only under-reset WB55 application uploads."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

APPLICATION_BYTES = 0x80000
SRAM_MIN = 0x20000000
SRAM_MAX = 0x2003FFFF
FLASH_MIN = 0x08000000
FLASH_MAX = 0x0807FFFF
MIN_PROGRAMMED_SPAN = 0x1000
MIN_NON_FF_BYTES = 1024


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

    non_ff_offsets = [index for index, value in enumerate(data) if value != 0xFF]
    first_non_ff = non_ff_offsets[0]
    last_non_ff = non_ff_offsets[-1]
    programmed_span = last_non_ff - first_non_ff + 1
    if first_non_ff > 7:
        raise BackupError(f"{label}: first non-FF byte is outside vector words at {first_non_ff}")
    if programmed_span < MIN_PROGRAMMED_SPAN:
        raise BackupError(f"{label}: programmed span {programmed_span} is below {MIN_PROGRAMMED_SPAN}")
    if len(non_ff_offsets) < MIN_NON_FF_BYTES:
        raise BackupError(f"{label}: only {len(non_ff_offsets)} non-FF bytes")

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
        "programmed_content": {
            "first_non_ff_offset": first_non_ff,
            "last_non_ff_offset": last_non_ff,
            "span_bytes": programmed_span,
            "non_ff_bytes": len(non_ff_offsets),
            "minimum_span_bytes": MIN_PROGRAMMED_SPAN,
            "minimum_non_ff_bytes": MIN_NON_FF_BYTES,
        },
    }


def validate_pair(backup_a: bytes, backup_b: bytes) -> dict:
    a = validate_image(backup_a, "backup-a")
    b = validate_image(backup_b, "backup-b")
    if backup_a != backup_b:
        raise BackupError("backup-a and backup-b differ")
    return {
        "schema_id": "companion.wb55.ur_application_backup.v1",
        "status": "PASS_DUAL_UR_APPLICATION_BACKUP",
        "address_hex": "0x08000000",
        "length_hex": "0x80000",
        "length_bytes": APPLICATION_BYTES,
        "backup_a": a,
        "backup_b": b,
        "byte_identical": True,
        "shared_sha256": a["sha256"],
        "identity_claim": "CAPTURED_PRE_RUN_APPLICATION_BYTES_NOT_E199_HEX_REPRODUCTION",
    }


def valid_fixture() -> bytes:
    data = bytearray([0xFF]) * APPLICATION_BYTES
    struct.pack_into("<II", data, 0, 0x20030000, 0x08000101)
    for index in range(0x100, 0x2100):
        data[index] = index & 0xFE
    return bytes(data)


def expect_failure(name: str, a: bytes, b: bytes) -> None:
    try:
        validate_pair(a, b)
    except BackupError:
        return
    raise AssertionError(f"negative fixture unexpectedly passed: {name}")


def self_test() -> None:
    valid = valid_fixture()
    assert validate_pair(valid, valid)["status"] == "PASS_DUAL_UR_APPLICATION_BACKUP"
    cases = {
        "short": (valid[:-1], valid),
        "long": (valid + b"\xFF", valid),
        "mismatch": (valid, valid[:-1] + b"\x00"),
        "bad_msp_range": (struct.pack("<I", 0x10000000) + valid[4:], valid),
        "bad_msp_alignment": (struct.pack("<I", 0x20030004) + valid[4:], valid),
        "bad_reset_thumb": (valid[:4] + struct.pack("<I", 0x08000100) + valid[8:], valid),
        "bad_reset_range": (valid[:4] + struct.pack("<I", 0x08080001) + valid[8:], valid),
        "all00": (bytes(APPLICATION_BYTES), bytes(APPLICATION_BYTES)),
        "allff": (bytes([0xFF]) * APPLICATION_BYTES, bytes([0xFF]) * APPLICATION_BYTES),
    }
    for name, inputs in cases.items():
        expect_failure(name, *inputs)

    sparse_span = bytearray([0xFF]) * APPLICATION_BYTES
    struct.pack_into("<II", sparse_span, 0, 0x20030000, 0x08000101)
    sparse_span[0x100:0x108] = b"COMPTEST"
    expect_failure("sparse_span", bytes(sparse_span), bytes(sparse_span))

    sparse_count = bytearray([0xFF]) * APPLICATION_BYTES
    struct.pack_into("<II", sparse_count, 0, 0x20030000, 0x08000101)
    sparse_count[0x2000] = 0x00
    expect_failure("sparse_count", bytes(sparse_count), bytes(sparse_count))
    print("PASS: WB55 UR application backup positive/negative self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-a", type=Path)
    parser.add_argument("--backup-b", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.backup_a is None or args.backup_b is None or args.out is None:
        parser.error("--backup-a, --backup-b and --out are required unless --self-test is used")
    try:
        result = validate_pair(args.backup_a.read_bytes(), args.backup_b.read_bytes())
    except (BackupError, OSError) as exc:
        print(f"NO_GO: {exc}")
        return 1
    result["private_files"] = {
        "backup_a": str(args.backup_a),
        "backup_b": str(args.backup_b),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
