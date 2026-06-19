#!/usr/bin/env python3
"""Companion BLE fixture probe helpers."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CACHE_FIXTURE = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.7-recording-cache-fixture.json"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing fixture: {path.relative_to(REPO_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_recording_pull_fixture(path: pathlib.Path) -> dict[str, Any]:
    errors: list[str] = []
    fixture = load_json(path)
    require(fixture.get("schema_version") == 1, "unexpected fixture schema_version", errors)
    require(fixture.get("backend", {}).get("current") == "file_backed_simulator", "fixture is not cache backed", errors)
    entries = fixture.get("recording_list", [])
    require(len(entries) == 1, "recording_list must expose one stored fixture recording", errors)
    if entries:
        require(entries[0].get("recording_id") == 1, "recording_list recording_id mismatch", errors)
        require(entries[0].get("total_length") == fixture.get("synthetic_audio", {}).get("byte_count"), "recording_list total_length mismatch", errors)

    chunk_pull = fixture.get("chunk_pull", {})
    packets = chunk_pull.get("packets", [])
    require(chunk_pull.get("status") == "ok", "chunk pull fixture did not complete", errors)
    require(len(packets) >= 2, "chunk pull fixture must include multiple packets", errors)
    total_length = fixture.get("synthetic_audio", {}).get("byte_count")
    next_offset = 0
    for expected_sequence, packet in enumerate(packets):
        require(packet.get("packet_sequence") == expected_sequence, f"packet sequence mismatch at {expected_sequence}", errors)
        require(packet.get("byte_offset") == next_offset, f"byte offset mismatch at packet {expected_sequence}", errors)
        require(packet.get("total_length") == total_length, f"total length drift at packet {expected_sequence}", errors)
        require(str(packet.get("packet_crc32", "")).startswith("0x"), f"missing packet CRC at {expected_sequence}", errors)
        next_offset += int(packet.get("payload_length", 0))
    require(next_offset == total_length, "packet payload lengths do not add up to total length", errors)
    require(packets[-1].get("final_sha256") == fixture.get("synthetic_audio", {}).get("sha256"), "final packet SHA-256 mismatch", errors)

    resume = fixture.get("resume", {})
    require(resume.get("by_byte_offset", {}).get("first_packet", {}).get("byte_offset") == 8192, "byte-offset resume evidence missing", errors)
    require(resume.get("by_packet_sequence", {}).get("first_packet", {}).get("packet_sequence") == 2, "packet-sequence resume evidence missing", errors)

    delete = fixture.get("delete_after_sync", {})
    require(
        delete.get("refused_before_host_verification", {}).get("status") == "refused_before_host_verification",
        "delete-after-sync was not refused before host verification",
        errors,
    )
    require(
        delete.get("accepted_after_length_and_sha256", {}).get("status") == "deleted",
        "delete-after-sync did not delete after host verification",
        errors,
    )
    require(delete.get("duplicate_delete", {}).get("status") == "duplicate_delete", "duplicate delete evidence missing", errors)

    if errors:
        raise AssertionError("; ".join(errors))
    return {
        "probe": "companion_ble_probe",
        "mode": "recording-pull-fixture",
        "status": "PASS",
        "fixture": path.relative_to(REPO_ROOT).as_posix(),
        "recording_id": 1,
        "total_length": total_length,
        "packet_count": len(packets),
        "resume": {
            "byte_offset": 8192,
            "packet_sequence": 2,
        },
        "delete_after_sync": {
            "refused_before_host_verification": True,
            "accepted_after_length_and_sha256": True,
            "duplicate_delete": True,
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=["recording-pull"], required=True)
    parser.add_argument("--fixture-path", type=pathlib.Path, default=DEFAULT_CACHE_FIXTURE)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        fixture_path = args.fixture_path if args.fixture_path.is_absolute() else REPO_ROOT / args.fixture_path
        result = check_recording_pull_fixture(fixture_path)
    except Exception as exc:  # noqa: BLE001 - CLI should return a compact failure.
        print(f"FAIL: Companion BLE fixture probe failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "PASS: Companion BLE recording-pull fixture probe passed; "
            f"{result['packet_count']} packet(s), {result['total_length']} byte(s)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
