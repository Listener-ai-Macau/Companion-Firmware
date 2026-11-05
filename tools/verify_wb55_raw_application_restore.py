#!/usr/bin/env python3
"""Verify a post-restore upload equals the captured WB55 raw baseline."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from verify_wb55_ur_application_backup import (
    APPLICATION_BYTES,
    BackupError,
    validate_image,
    validate_pair,
    valid_fixture,
)


def validate_restore(backup_a: bytes, backup_b: bytes, restored: bytes) -> dict:
    baseline = validate_pair(backup_a, backup_b)
    restored_result = validate_image(restored, "restore-verify")
    if restored != backup_a:
        raise BackupError("restore-verify differs byte-for-byte from backup-a")
    return {
        "schema_id": "companion.wb55.raw_application_restore.v1",
        "status": "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES",
        "address_hex": "0x08000000",
        "length_hex": "0x80000",
        "length_bytes": APPLICATION_BYTES,
        "baseline_sha256": baseline["shared_sha256"],
        "restore_sha256": restored_result["sha256"],
        "byte_identical": True,
        "restore_vector": restored_result["vector"],
        "restore_programmed_content": restored_result["programmed_content"],
        "restore_identity": "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES",
        "e199_hex_reproduction": False,
    }


def expect_failure(name: str, a: bytes, b: bytes, restored: bytes) -> None:
    try:
        validate_restore(a, b, restored)
    except BackupError:
        return
    raise AssertionError(f"negative restore fixture unexpectedly passed: {name}")


def self_test() -> None:
    valid = valid_fixture()
    assert validate_restore(valid, valid, valid)["status"] == \
        "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES"
    cases = {
        "baseline_mismatch": (valid, valid[:-1] + b"\x00", valid),
        "restore_short": (valid, valid, valid[:-1]),
        "restore_long": (valid, valid, valid + b"\xFF"),
        "restore_mismatch": (valid, valid, valid[:-1] + b"\x00"),
        "restore_all00": (valid, valid, bytes(APPLICATION_BYTES)),
        "restore_allff": (valid, valid, bytes([0xFF]) * APPLICATION_BYTES),
        "restore_bad_msp": (valid, valid, struct.pack("<I", 0x10000000) + valid[4:]),
        "restore_bad_vector": (valid, valid, valid[:4] + struct.pack("<I", 0x08000100) + valid[8:]),
    }
    for name, inputs in cases.items():
        expect_failure(name, *inputs)
    print("PASS: WB55 raw application restore positive/negative self-test")


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
    if any(value is None for value in (args.backup_a, args.backup_b, args.restore_verify, args.out)):
        parser.error("--backup-a, --backup-b, --restore-verify and --out are required")
    try:
        result = validate_restore(
            args.backup_a.read_bytes(),
            args.backup_b.read_bytes(),
            args.restore_verify.read_bytes(),
        )
    except (BackupError, OSError) as exc:
        print(f"NO_GO: {exc}")
        return 1
    result["private_files"] = {
        "backup_a": str(args.backup_a),
        "backup_b": str(args.backup_b),
        "restore_verify": str(args.restore_verify),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
