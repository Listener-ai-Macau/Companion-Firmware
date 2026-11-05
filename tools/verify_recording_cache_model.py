#!/usr/bin/env python3
"""Verify the Companion recording cache model and fixture."""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import zlib
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.recording_cache.cache_model import (  # noqa: E402
    FileBackedRecordingCache,
    SampleFormat,
    synthetic_pcm16,
)


MODEL = REPO_ROOT / "app/companion_pendant/recording_cache/cache_model.py"
README = REPO_ROOT / "app/companion_pendant/recording_cache/README.md"
DIAG_EVENTS = REPO_ROOT / "app/companion_pendant/diag_log/diag_log_events.h"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
FIXTURE = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.7-recording-cache-fixture.json"
WORKDIR = REPO_ROOT / "docs/validation/.recording-cache-workdir"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"FAIL: missing required file: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def check_static_surface(errors: list[str]) -> None:
    model_text = read(MODEL)
    readme_text = read(README)
    diag_text = read(DIAG_EVENTS)
    contract_text = read(BLE_CONTRACT)
    joined = "\n".join([model_text, readme_text, diag_text, contract_text])

    for token in [
        "FileBackedRecordingCache",
        "backend_kind = \"file_backed_simulator\"",
        "later_backend_kind = \"external_spi_nor\"",
        "SPH0655-compatible PDM digital MEMS",
        "software_fixture_for_HAL_LL_SAI_PDM_to_PCM_boundary",
        "RecordingMetadata",
        "created_unix_s",
        "created_tick_ms",
        "total_length",
        "sample_format",
        "crc32",
        "sha256",
        "sync_state",
        "delete_state",
        "read_from_packet_sequence",
        "request_delete_after_sync",
        "privacy_erase",
    ]:
        require(token in joined, f"recording cache surface missing {token}", errors)

    for token in [
        "spi_flash_cache.write",
        "spi_flash_cache.read",
        "spi_flash_cache.delete",
        "spi_flash_cache.low_storage",
        "spi_flash_cache.interrupted_write",
        "spi_flash_cache.interrupted_read",
        "spi_flash_cache.privacy_erase",
    ]:
        require(token in joined, f"diag event coverage missing {token}", errors)

    for token in ["recording_list", "recording chunk pull", "delete-after-sync", "CRC", "SHA-256"]:
        require(token in contract_text, f"BLE contract missing {token}", errors)

    for forbidden in ["esp_partition", "nvs_flash", "ESP_LOG", "smart base", "Wi-Fi", "wireless charging"]:
        require(forbidden not in model_text, f"cache model introduced forbidden token {forbidden}", errors)


def assert_packets(packets: list[dict[str, Any]], total_length: int, start_sequence: int, start_offset: int) -> None:
    offset = start_offset
    sequence = start_sequence
    for packet in packets:
        if packet["packet_sequence"] != sequence:
            raise AssertionError(f"packet sequence mismatch: {packet}")
        if packet["byte_offset"] != offset:
            raise AssertionError(f"packet byte offset mismatch: {packet}")
        if packet["total_length"] != total_length:
            raise AssertionError(f"total length drift: {packet}")
        if not str(packet["packet_crc32"]).startswith("0x"):
            raise AssertionError(f"missing packet crc: {packet}")
        offset += packet["payload_length"]
        sequence += 1


def build_fixture(errors: list[str]) -> dict[str, Any]:
    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(parents=True)
    try:
        sample = synthetic_pcm16(duration_ms=5000)
        sample_format = SampleFormat()
        cache = FileBackedRecordingCache(WORKDIR / "cache", capacity_bytes=512 * 1024)
        write_result = cache.write_recording(
            1,
            sample,
            sample_format,
            created_unix_s=1_800_000_000,
            created_tick_ms=42_000,
            duration_ms=5000,
        )
        metadata = cache.metadata(1)
        recording_list = cache.recording_list()
        pull = cache.read_chunks(1, byte_offset=0, requested_length=len(sample), max_payload=4096)
        packets = pull["packets"]
        resume_by_offset = cache.read_chunks(1, byte_offset=8192, requested_length=8192, max_payload=4096)
        resume_by_sequence = cache.read_from_packet_sequence(1, packet_sequence=2, requested_length=8192, max_payload=4096)
        refused_delete = cache.request_delete_after_sync(
            1,
            validated_total_length=metadata.total_length,
            validated_sha256=metadata.sha256,
            host_verified=False,
        )
        accepted_delete = cache.request_delete_after_sync(
            1,
            validated_total_length=metadata.total_length,
            validated_sha256=metadata.sha256,
            host_verified=True,
        )
        duplicate_delete = cache.request_delete_after_sync(
            1,
            validated_total_length=metadata.total_length,
            validated_sha256=metadata.sha256,
            host_verified=True,
        )

        low_storage_cache = FileBackedRecordingCache(WORKDIR / "low-storage", capacity_bytes=1024)
        low_storage = low_storage_cache.write_recording(
            2,
            sample,
            sample_format,
            created_unix_s=1_800_000_001,
            created_tick_ms=43_000,
            duration_ms=5000,
        )

        interrupted_write_cache = FileBackedRecordingCache(WORKDIR / "interrupted-write", capacity_bytes=512 * 1024)
        interrupted_write = interrupted_write_cache.write_recording(
            3,
            sample,
            sample_format,
            created_unix_s=1_800_000_002,
            created_tick_ms=44_000,
            duration_ms=5000,
            interrupt_after_bytes=4096,
        )

        interrupted_read_cache = FileBackedRecordingCache(WORKDIR / "interrupted-read", capacity_bytes=512 * 1024)
        interrupted_read_cache.write_recording(
            4,
            sample,
            sample_format,
            created_unix_s=1_800_000_003,
            created_tick_ms=45_000,
            duration_ms=5000,
        )
        interrupted_read = interrupted_read_cache.read_chunks(
            4,
            byte_offset=0,
            requested_length=len(sample),
            max_payload=4096,
            interrupt_after_packets=2,
        )
        privacy_cache = FileBackedRecordingCache(WORKDIR / "privacy", capacity_bytes=512 * 1024)
        privacy_cache.write_recording(
            5,
            sample,
            sample_format,
            created_unix_s=1_800_000_004,
            created_tick_ms=46_000,
            duration_ms=5000,
        )
        privacy_erase = privacy_cache.privacy_erase()

        assert_packets(packets, len(sample), 0, 0)
        assert_packets(resume_by_offset["packets"], len(sample), 0, 8192)
        assert_packets(resume_by_sequence["packets"], len(sample), 2, 8192)
        require(write_result["status"] == "stored", "write did not store recording", errors)
        require(pull["status"] == "ok", "chunk pull failed", errors)
        require(sum(packet["payload_length"] for packet in packets) == len(sample), "chunk byte count mismatch", errors)
        require(packets[-1]["final_sha256"] == metadata.sha256, "final packet missing full SHA-256", errors)
        require(refused_delete["status"] == "refused_before_host_verification", "delete-after-sync was not refused before verification", errors)
        require(accepted_delete["status"] == "deleted", "delete-after-sync did not delete after verification", errors)
        require(duplicate_delete["status"] == "duplicate_delete", "duplicate delete behavior missing", errors)
        require(low_storage["status"] == "low_storage", "low storage behavior missing", errors)
        require(interrupted_write["status"] == "interrupted_write", "interrupted write behavior missing", errors)
        require(interrupted_read["status"] == "interrupted_read", "interrupted read behavior missing", errors)
        require(privacy_erase["status"] == "privacy_erased", "privacy erase behavior missing", errors)

        fixture = {
            "schema_version": 1,
            "mode": "synthetic-no-hardware-recording-cache-fixture",
            "backend": {
                "current": cache.backend_kind,
                "later": cache.later_backend_kind,
                "real_spi_nor_driver_timing_power": "deferred_to_hardware_gate",
            },
            "synthetic_audio": {
                "duration_ms": 5000,
                "byte_count": len(sample),
                "crc32": f"0x{zlib.crc32(sample) & 0xFFFFFFFF:08x}",
                "sha256": metadata.sha256,
                "sample_format": sample_format.to_dict(),
            },
            "recording_list": recording_list,
            "recording_metadata": metadata.to_dict(),
            "chunk_pull": {
                "request": {
                    "recording_id": 1,
                    "byte_offset": 0,
                    "requested_length": len(sample),
                    "max_payload": 4096,
                },
                "status": pull["status"],
                "packet_count": len(packets),
                "packets": packets,
                "byte_count_verified": sum(packet["payload_length"] for packet in packets),
                "final_sha256_verified": packets[-1]["final_sha256"] == metadata.sha256,
            },
            "resume": {
                "by_byte_offset": {
                    "byte_offset": 8192,
                    "first_packet": resume_by_offset["packets"][0],
                },
                "by_packet_sequence": {
                    "packet_sequence": 2,
                    "first_packet": resume_by_sequence["packets"][0],
                },
            },
            "delete_after_sync": {
                "refused_before_host_verification": refused_delete,
                "accepted_after_length_and_sha256": accepted_delete,
                "duplicate_delete": duplicate_delete,
            },
            "negative_cases": {
                "low_storage": low_storage,
                "interrupted_write": interrupted_write,
                "interrupted_read": interrupted_read,
                "privacy_erase": privacy_erase,
            },
            "diag_events": [event.to_dict() for event in (
                cache.events
                + low_storage_cache.events
                + interrupted_write_cache.events
                + interrupted_read_cache.events
                + privacy_cache.events
            )],
            "quality_claim": "cache and BLE pull metadata only; real SPI NOR timing and power remain a later hardware gate",
        }
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(fixture, indent=2, sort_keys=True) + "\n"
        if not FIXTURE.exists() or FIXTURE.read_text(encoding="utf-8") != text:
            FIXTURE.write_text(text, encoding="utf-8")
        return fixture
    finally:
        if WORKDIR.exists():
            shutil.rmtree(WORKDIR)


def check_fixture(fixture: dict[str, Any], errors: list[str]) -> None:
    require(fixture["synthetic_audio"]["duration_ms"] >= 5000, "fixture shorter than 5 seconds", errors)
    require(fixture["synthetic_audio"]["duration_ms"] <= 10000, "fixture longer than 10 seconds", errors)
    require(fixture["synthetic_audio"]["byte_count"] == 160000, "fixture byte count mismatch", errors)
    require(fixture["chunk_pull"]["byte_count_verified"] == 160000, "chunk pull byte count mismatch", errors)
    require(fixture["chunk_pull"]["final_sha256_verified"], "final SHA-256 was not verified", errors)
    require(fixture["delete_after_sync"]["accepted_after_length_and_sha256"]["status"] == "deleted", "delete-after-sync did not delete", errors)
    require(fixture["backend"]["real_spi_nor_driver_timing_power"] == "deferred_to_hardware_gate", "hardware gate deferral missing", errors)
    sample_format = fixture["synthetic_audio"]["sample_format"]
    require(sample_format["source_family"] == "SPH0655-compatible PDM digital MEMS", "fixture source family drifted from WB55 PDM default", errors)
    require(
        sample_format["stm32_ingress"] == "software_fixture_for_HAL_LL_SAI_PDM_to_PCM_boundary",
        "fixture ingress drifted from PDM-to-PCM boundary",
        errors,
    )
    diag_names = {event["diag_name"] for event in fixture["diag_events"]}
    for name in [
        "spi_flash_cache.write",
        "spi_flash_cache.read",
        "spi_flash_cache.delete",
        "spi_flash_cache.low_storage",
        "spi_flash_cache.interrupted_write",
        "spi_flash_cache.interrupted_read",
        "spi_flash_cache.privacy_erase",
    ]:
        require(name in diag_names, f"fixture missing diag event {name}", errors)


def main() -> int:
    errors: list[str] = []
    check_static_surface(errors)
    fixture = build_fixture(errors)
    check_fixture(fixture, errors)
    if errors:
        print("FAIL: Companion recording cache model checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(
        "PASS: Companion recording cache model verified; fixture written to "
        f"{FIXTURE.relative_to(REPO_ROOT)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
