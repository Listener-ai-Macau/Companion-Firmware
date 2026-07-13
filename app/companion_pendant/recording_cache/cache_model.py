#!/usr/bin/env python3
"""File-backed Companion recording cache model.

This is a no-hardware model for the storage and BLE pull semantics that will
later sit above an STM32 SPI NOR driver. It deliberately keeps the backend
boundary explicit so validation can exercise recording metadata, chunk pull,
delete, and privacy behavior without touching a real flash part.
"""

from __future__ import annotations

import hashlib
import pathlib
import struct
import zlib
from dataclasses import asdict, dataclass
from typing import Any


SYNC_UNSYNCED = "unsynced"
SYNC_TRANSFER_ACTIVE = "transfer_active"
SYNC_TRANSFERRED = "transferred"
SYNC_DELETED = "deleted"
DELETE_STORED = "stored"
DELETE_AFTER_SYNC_REQUESTED = "delete_after_sync_requested"
DELETE_DELETED = "deleted"
DELETE_PRIVACY_ERASED = "privacy_erased"
DELETE_INTERRUPTED_WRITE = "interrupted_write"


@dataclass(frozen=True)
class SampleFormat:
    codec: str = "pcm16"
    sample_rate_hz: int = 16000
    bits_per_sample: int = 16
    channels: int = 1
    frame_samples: int = 160
    source_family: str = "SPH0655-compatible PDM digital MEMS"
    stm32_ingress: str = "software_fixture_for_HAL_LL_SAI_PDM_to_PCM_boundary"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecordingMetadata:
    recording_id: int
    created_unix_s: int
    created_tick_ms: int
    duration_ms: int
    total_length: int
    sample_format: SampleFormat
    crc32: str
    sha256: str
    sha256_prefix: str
    sync_state: str = SYNC_UNSYNCED
    delete_state: str = DELETE_STORED
    packet_sequence_next: int = 0
    byte_offset_ready: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sample_format"] = self.sample_format.to_dict()
        return data

    def to_ble_list_entry(self) -> dict[str, Any]:
        return {
            "recording_id": self.recording_id,
            "started_unix_s": self.created_unix_s,
            "duration_ms": self.duration_ms,
            "codec": self.sample_format.codec,
            "total_length": self.total_length,
            "sha256_prefix": self.sha256_prefix,
            "sync_state": self.sync_state,
            "delete_state": self.delete_state,
        }


@dataclass(frozen=True)
class CacheEvent:
    diag_name: str
    severity: str
    recording_id: int
    arg0: int
    arg1: int
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkPacket:
    recording_id: int
    packet_sequence: int
    byte_offset: int
    total_length: int
    payload_length: int
    payload_crc32: str
    packet_crc32: str
    payload_sha256: str
    final_sha256: str | None
    flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FileBackedRecordingCache:
    """Recording cache simulator with the same boundaries as a later SPI NOR backend."""

    backend_kind = "file_backed_simulator"
    later_backend_kind = "external_spi_nor"

    def __init__(self, root: pathlib.Path, capacity_bytes: int = 2 * 1024 * 1024) -> None:
        self.root = pathlib.Path(root)
        self.capacity_bytes = capacity_bytes
        self.root.mkdir(parents=True, exist_ok=True)
        self._metadata: dict[int, RecordingMetadata] = {}
        self.events: list[CacheEvent] = []

    def _path_for(self, recording_id: int) -> pathlib.Path:
        return self.root / f"recording_{recording_id:08x}.pcm"

    def _event(self,
               diag_name: str,
               severity: str,
               recording_id: int,
               arg0: int,
               arg1: int,
               detail: str) -> None:
        self.events.append(CacheEvent(diag_name, severity, recording_id, arg0, arg1, detail))

    def used_bytes(self) -> int:
        total = 0
        for metadata in self._metadata.values():
            if metadata.delete_state in {DELETE_STORED, DELETE_AFTER_SYNC_REQUESTED}:
                total += metadata.total_length
        return total

    def write_recording(self,
                        recording_id: int,
                        data: bytes,
                        sample_format: SampleFormat,
                        created_unix_s: int,
                        created_tick_ms: int,
                        duration_ms: int,
                        interrupt_after_bytes: int | None = None) -> dict[str, Any]:
        available = self.capacity_bytes - self.used_bytes()
        if len(data) > available:
            self._event("spi_flash_cache.low_storage", "warn", recording_id, len(data), available, "low_storage")
            return {"status": "low_storage", "requested_bytes": len(data), "available_bytes": available}

        if interrupt_after_bytes is not None and 0 <= interrupt_after_bytes < len(data):
            partial = data[:interrupt_after_bytes]
            self._path_for(recording_id).write_bytes(partial)
            metadata = self._build_metadata(
                recording_id,
                partial,
                sample_format,
                created_unix_s,
                created_tick_ms,
                duration_ms=0,
                delete_state=DELETE_INTERRUPTED_WRITE,
            )
            self._metadata[recording_id] = metadata
            self._event(
                "spi_flash_cache.interrupted_write",
                "warn",
                recording_id,
                interrupt_after_bytes,
                len(data),
                "interrupted_write",
            )
            return {"status": "interrupted_write", "metadata": metadata.to_dict()}

        self._path_for(recording_id).write_bytes(data)
        metadata = self._build_metadata(
            recording_id,
            data,
            sample_format,
            created_unix_s,
            created_tick_ms,
            duration_ms,
            DELETE_STORED,
        )
        metadata.byte_offset_ready = metadata.total_length
        self._metadata[recording_id] = metadata
        self._event("spi_flash_cache.write", "info", recording_id, len(data), metadata.duration_ms, "write")
        return {"status": "stored", "metadata": metadata.to_dict()}

    def _build_metadata(self,
                        recording_id: int,
                        data: bytes,
                        sample_format: SampleFormat,
                        created_unix_s: int,
                        created_tick_ms: int,
                        duration_ms: int,
                        delete_state: str) -> RecordingMetadata:
        sha = hashlib.sha256(data).hexdigest()
        return RecordingMetadata(
            recording_id=recording_id,
            created_unix_s=created_unix_s,
            created_tick_ms=created_tick_ms,
            duration_ms=duration_ms,
            total_length=len(data),
            sample_format=sample_format,
            crc32=f"0x{zlib.crc32(data) & 0xFFFFFFFF:08x}",
            sha256=sha,
            sha256_prefix=sha[:16],
            sync_state=SYNC_UNSYNCED,
            delete_state=delete_state,
            byte_offset_ready=len(data),
        )

    def metadata(self, recording_id: int) -> RecordingMetadata:
        return self._metadata[recording_id]

    def recording_list(self) -> list[dict[str, Any]]:
        active = [
            metadata.to_ble_list_entry()
            for metadata in self._metadata.values()
            if metadata.delete_state in {DELETE_STORED, DELETE_AFTER_SYNC_REQUESTED}
        ]
        return sorted(active, key=lambda item: int(item["recording_id"]))

    def read_chunks(self,
                    recording_id: int,
                    byte_offset: int,
                    requested_length: int,
                    max_payload: int,
                    packet_sequence_start: int = 0,
                    interrupt_after_packets: int | None = None) -> dict[str, Any]:
        metadata = self._metadata[recording_id]
        if metadata.delete_state not in {DELETE_STORED, DELETE_AFTER_SYNC_REQUESTED}:
            return {"status": "record_missing", "packets": []}
        if byte_offset > metadata.total_length:
            return {"status": "offset_out_of_range", "total_length": metadata.total_length, "packets": []}

        data = self._path_for(recording_id).read_bytes()
        end = min(metadata.total_length, byte_offset + requested_length)
        packets: list[ChunkPacket] = []
        offset = byte_offset
        sequence = packet_sequence_start
        while offset < end:
            if interrupt_after_packets is not None and len(packets) >= interrupt_after_packets:
                self._event(
                    "spi_flash_cache.interrupted_read",
                    "warn",
                    recording_id,
                    offset,
                    end,
                    "interrupted_read",
                )
                metadata.sync_state = SYNC_TRANSFER_ACTIVE
                return {"status": "interrupted_read", "packets": [packet.to_dict() for packet in packets]}
            payload = data[offset:min(end, offset + max_payload)]
            final = offset + len(payload) >= metadata.total_length
            packets.append(self._make_packet(metadata, sequence, offset, payload, final))
            offset += len(payload)
            sequence += 1

        metadata.packet_sequence_next = sequence
        metadata.sync_state = SYNC_TRANSFERRED if end == metadata.total_length else SYNC_TRANSFER_ACTIVE
        self._event("spi_flash_cache.read", "info", recording_id, byte_offset, end - byte_offset, "read")
        return {"status": "ok", "packets": [packet.to_dict() for packet in packets]}

    def read_from_packet_sequence(self,
                                  recording_id: int,
                                  packet_sequence: int,
                                  requested_length: int,
                                  max_payload: int) -> dict[str, Any]:
        offset = packet_sequence * max_payload
        return self.read_chunks(recording_id, offset, requested_length, max_payload, packet_sequence)

    def _make_packet(self,
                     metadata: RecordingMetadata,
                     packet_sequence: int,
                     byte_offset: int,
                     payload: bytes,
                     final: bool) -> ChunkPacket:
        header = struct.pack(
            "<IIII",
            metadata.recording_id,
            packet_sequence,
            byte_offset,
            metadata.total_length,
        )
        packet_crc = zlib.crc32(header + payload) & 0xFFFFFFFF
        payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
        flags = ["final"] if final else []
        return ChunkPacket(
            recording_id=metadata.recording_id,
            packet_sequence=packet_sequence,
            byte_offset=byte_offset,
            total_length=metadata.total_length,
            payload_length=len(payload),
            payload_crc32=f"0x{payload_crc:08x}",
            packet_crc32=f"0x{packet_crc:08x}",
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            final_sha256=metadata.sha256 if final else None,
            flags=flags,
        )

    def request_delete_after_sync(self,
                                  recording_id: int,
                                  validated_total_length: int,
                                  validated_sha256: str,
                                  host_verified: bool) -> dict[str, Any]:
        metadata = self._metadata.get(recording_id)
        if metadata is None or metadata.delete_state in {DELETE_DELETED, DELETE_PRIVACY_ERASED}:
            self._event("spi_flash_cache.delete", "warn", recording_id, 0, 0, "duplicate_delete")
            return {"status": "duplicate_delete"}

        metadata.delete_state = DELETE_AFTER_SYNC_REQUESTED
        if not host_verified:
            return {"status": "refused_before_host_verification", "delete_state": metadata.delete_state}
        if validated_total_length != metadata.total_length or validated_sha256 != metadata.sha256:
            return {"status": "metadata_mismatch", "delete_state": metadata.delete_state}

        self._path_for(recording_id).unlink(missing_ok=True)
        metadata.delete_state = DELETE_DELETED
        metadata.sync_state = SYNC_DELETED
        self._event("spi_flash_cache.delete", "info", recording_id, validated_total_length, 0, "delete_after_sync")
        return {"status": "deleted", "metadata": metadata.to_dict()}

    def privacy_erase(self) -> dict[str, Any]:
        erased = 0
        for recording_id, metadata in list(self._metadata.items()):
            if metadata.delete_state != DELETE_PRIVACY_ERASED:
                self._path_for(recording_id).unlink(missing_ok=True)
                metadata.delete_state = DELETE_PRIVACY_ERASED
                metadata.sync_state = SYNC_DELETED
                erased += 1
        self._event("spi_flash_cache.privacy_erase", "warn", 0, erased, 0, "privacy_erase")
        return {"status": "privacy_erased", "erased_count": erased}


def synthetic_pcm16(duration_ms: int = 5000, sample_rate_hz: int = 16000) -> bytes:
    sample_count = sample_rate_hz * duration_ms // 1000
    out = bytearray()
    for index in range(sample_count):
        value = ((index * 73) % 2048) - 1024
        if (index // 1600) % 2:
            value = -value
        out.extend(int(value).to_bytes(2, byteorder="little", signed=True))
    return bytes(out)
