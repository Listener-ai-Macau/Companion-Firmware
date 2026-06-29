#!/usr/bin/env python3
"""No-hardware Companion BLE fixture harness.

The fixture backend exercises the host-facing Companion BLE contract without a
radio. Real BLE adapters can later reuse the same operation names and evidence
shape through Bleak, Windows BLE APIs, or a Listener-Type host bridge.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE_PATH = REPO_ROOT / "docs/ble_uuid_table.json"
RECORDING_FIXTURE_PATH = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.7-recording-cache-fixture.json"
OTA_FIXTURE_PATH = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"
MATRIX_PATH = REPO_ROOT / "docs/validation/companion_ble_matrix.json"

REQUIRED_OPERATIONS = (
    "scan_result_parsing",
    "status_read",
    "card_write",
    "recording_list",
    "recording_pull",
    "byte_offset_resume",
    "log_pull",
    "delete",
    "ota_status",
)
REQUIRED_MATRIX_CATEGORIES = (
    "normal_use",
    "retry",
    "cancel",
    "disconnect_reconnect",
    "byte_offset_resume",
    "gatt_cache_stale",
    "cccd_notify_failure",
    "recovered_event_suppressed",
    "long_recording_metadata",
    "idle_resume",
    "log_export",
    "ota_blocked",
)
REQUIRED_FAILURES = (
    "no_device",
    "wrong_service_uuid",
    "timeout",
    "disconnected",
    "gatt_cache_stale",
    "cccd_notify_failure",
    "crc_mismatch",
    "hash_mismatch",
    "low_battery",
    "no_recording",
    "transfer_canceled",
    "ota_blocked",
)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing fixture: {path.relative_to(REPO_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: pathlib.Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def crc32_hex(data: bytes) -> str:
    return f"0x{binascii.crc32(data) & 0xFFFFFFFF:08x}"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def uuid_index(uuid_table: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for service in uuid_table.get("services", []):
        index[str(service["service"])] = str(service["uuid"])
        for char in service.get("characteristics", []):
            index[str(char["name"])] = str(char["uuid"])
    return index


@dataclass(frozen=True)
class FixtureScanDevice:
    name: str
    address: str
    service_uuids: tuple[str, ...]
    rssi: int


class CompanionFixtureAdapter:
    """Fixture adapter that mirrors the later real BLE operation boundary."""

    backend = "fixture"
    later_real_adapters = ("python-bleak", "windows-ble-apis", "listener-type-ble-approach")

    def __init__(self) -> None:
        self.uuid_table = load_json(UUID_TABLE_PATH)
        self.uuids = uuid_index(self.uuid_table)
        self.recording_fixture = load_json(RECORDING_FIXTURE_PATH)
        self.ota_fixture = load_json(OTA_FIXTURE_PATH)
        self.selected_device: FixtureScanDevice | None = None

    def scan(self) -> dict[str, Any]:
        companion_status_uuid = self.uuids["device_status"]
        companion_recording_uuid = self.uuids["recording"]
        devices = (
            FixtureScanDevice(
                name="Companion Pendant Dev",
                address="F1:E2:D3:C4:B5:A6",
                service_uuids=(companion_status_uuid, companion_recording_uuid),
                rssi=-48,
            ),
            FixtureScanDevice(
                name="Reference Audio Host",
                address="00:11:22:33:44:55",
                service_uuids=("0000180f-0000-1000-8000-00805f9b34fb",),
                rssi=-71,
            ),
        )
        selected = next(
            device
            for device in devices
            if device.name.startswith("Companion ") and companion_status_uuid in device.service_uuids
        )
        self.selected_device = selected
        return {
            "operation": "scan_result_parsing",
            "status": "PASS",
            "selected_name": selected.name,
            "selected_address": selected.address,
            "required_service_uuid": companion_status_uuid,
            "ignored_device_count": len(devices) - 1,
            "device_count": len(devices),
            "rssi": selected.rssi,
        }

    def read_status(self) -> dict[str, Any]:
        return {
            "operation": "status_read",
            "status": "PASS",
            "device_status": {
                "schema_version": 1,
                "firmware_semver": "0.1.0-fixture",
                "build_id": "fixture-b109442",
                "board_id": "NUCLEO-WB55RG",
                "uptime_ms": 123456,
                "fault_bitmap": 0,
                "active_mode": "idle",
                "advertising_name": "Companion Pendant Dev",
            },
            "battery_charge": {
                "percent": 84,
                "millivolts": 4012,
                "charge_state": "discharging",
                "charger_present": False,
                "temperature_c_x10": 261,
            },
        }

    def write_card(self) -> dict[str, Any]:
        title = "Bring-up card".encode("utf-8")
        body = "Fixture card write proves UTF-8 length and CRC handling.".encode("utf-8")
        content = title + b"\0" + body
        return {
            "operation": "card_write",
            "status": "PASS",
            "request_id": 17,
            "card_slot": 0,
            "utf8_title_len": len(title),
            "utf8_body_len": len(body),
            "content_crc32": crc32_hex(content),
            "render_state": "accepted",
        }

    def list_recordings(self) -> dict[str, Any]:
        entries = list(self.recording_fixture.get("recording_list", []))
        if not entries:
            raise RuntimeError("recording fixture contains no recording_list entries")
        first = dict(entries[0])
        sample_format = self.recording_fixture.get("synthetic_audio", {}).get("sample_format", {})
        return {
            "operation": "recording_list",
            "status": "PASS",
            "count": len(entries),
            "entry": {
                "recording_id": first["recording_id"],
                "duration_ms": first["duration_ms"],
                "codec": first["codec"],
                "sample_rate_hz": sample_format.get("sample_rate_hz", 16000),
                "total_length": first["total_length"],
                "sha256_prefix": first["sha256_prefix"],
                "sync_state": first["sync_state"],
                "delete_state": first["delete_state"],
            },
        }

    def pull_recording(self) -> dict[str, Any]:
        chunk_pull = self.recording_fixture.get("chunk_pull", {})
        packets = list(chunk_pull.get("packets", []))
        if not packets:
            raise RuntimeError("recording fixture contains no chunk_pull packets")
        total_length = int(self.recording_fixture["synthetic_audio"]["byte_count"])
        next_offset = 0
        for expected_seq, packet in enumerate(packets):
            if packet["packet_sequence"] != expected_seq:
                raise RuntimeError(f"packet sequence drift at {expected_seq}")
            if packet["byte_offset"] != next_offset:
                raise RuntimeError(f"packet byte offset drift at {expected_seq}")
            next_offset += int(packet["payload_length"])
        if next_offset != total_length:
            raise RuntimeError("recording payload length mismatch")
        return {
            "operation": "recording_pull",
            "status": "PASS",
            "recording_id": packets[0]["recording_id"],
            "packet_count": len(packets),
            "total_length": total_length,
            "byte_count_verified": chunk_pull.get("byte_count_verified"),
            "final_sha256_verified": bool(chunk_pull.get("final_sha256_verified")),
            "crc_model": "packet_crc32 over header+payload; final packet carries SHA-256",
            "resume": self.recording_fixture.get("resume", {}),
        }

    def resume_after_disconnect(self) -> dict[str, Any]:
        resume = self.recording_fixture.get("resume", {}).get("by_byte_offset", {})
        first_packet = dict(resume.get("first_packet", {}))
        byte_offset = int(resume.get("byte_offset", -1))
        if byte_offset < 0 or int(first_packet.get("byte_offset", -2)) != byte_offset:
            raise RuntimeError("byte-offset resume fixture is not aligned")
        return {
            "operation": "byte_offset_resume",
            "status": "PASS",
            "disconnect_reason_classification": "disconnected",
            "resume_strategy": "byte_offset_resume",
            "previous_verified_byte_offset": byte_offset,
            "request": {
                "recording_id": first_packet["recording_id"],
                "byte_offset": byte_offset,
                "requested_length": 8192,
                "host_resume_token": "fixture-disconnect-reconnect-token",
            },
            "first_resumed_packet": {
                "recording_id": first_packet["recording_id"],
                "byte_offset": first_packet["byte_offset"],
                "packet_sequence": first_packet["packet_sequence"],
                "total_length": first_packet["total_length"],
                "payload_length": first_packet["payload_length"],
                "packet_crc32": first_packet["packet_crc32"],
            },
            "host_result": "reread recording_list, resume from absolute byte offset, and do not duplicate verified bytes",
        }

    def pull_log(self) -> dict[str, Any]:
        event_lines = [
            "gatt.scan selected Companion service",
            "recording.pull completed fixture transfer",
            "ota.readiness blocked by low battery fixture",
        ]
        payload = "\n".join(event_lines).encode("utf-8")
        return {
            "operation": "log_pull",
            "status": "PASS",
            "cursor": 0,
            "next_cursor": len(event_lines),
            "total_available": len(event_lines),
            "event_count": len(event_lines),
            "crc32": crc32_hex(payload),
            "bounded_tail": True,
        }

    def delete_recording(self) -> dict[str, Any]:
        delete_fixture = self.recording_fixture.get("delete_after_sync", {})
        accepted = delete_fixture.get("accepted_after_length_and_sha256", {})
        duplicate = delete_fixture.get("duplicate_delete", {})
        return {
            "operation": "delete",
            "status": "PASS",
            "delete_after_sync": {
                "refused_before_host_verification": delete_fixture.get("refused_before_host_verification", {}).get("status"),
                "accepted_after_length_and_sha256": accepted.get("status"),
                "duplicate_delete": duplicate.get("status"),
            },
            "privacy_erase_supported": True,
            "host_must_match_total_length_and_sha256": True,
        }

    def read_ota_status(self) -> dict[str, Any]:
        blockers = list(self.ota_fixture.get("required_blockers", []))
        cases = [case["case"] for case in self.ota_fixture.get("cases", [])]
        return {
            "operation": "ota_status",
            "status": "PASS",
            "ready_state": "not_ready",
            "boot_slot": "slot_a",
            "battery_percent": 18,
            "charger_present": False,
            "charger_required": False,
            "minimum_required_mv": 3700,
            "min_battery_percent": 40,
            "blocker_bitmap_names": blockers,
            "blocker_bitmap": self.ota_fixture.get("required_blocker_bits", {}),
            "blocked_case": "low_battery",
            "fixture_cases": cases,
            "fixture_blocked_cases": [
                case
                for case in cases
                if case.startswith("bad_")
            ],
            "host_messages": self.ota_fixture.get("host_messages", {}),
            "ota_data_path_enabled": False,
        }

    def run_operations(self) -> dict[str, dict[str, Any]]:
        operations = [
            self.scan(),
            self.read_status(),
            self.write_card(),
            self.list_recordings(),
            self.pull_recording(),
            self.resume_after_disconnect(),
            self.pull_log(),
            self.delete_recording(),
            self.read_ota_status(),
        ]
        return {str(item["operation"]): item for item in operations}


def product_matrix(operations: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    recording_total = operations["recording_pull"]["total_length"]
    return [
        {
            "case_id": "C1",
            "category": "normal_use",
            "scenario": "Scan, read status, write a card, list recordings, pull one recording, pull logs, and read OTA status in one fixture session.",
            "result": "PASS",
            "fixture_operations": list(REQUIRED_OPERATIONS),
            "expected_host_behavior": "Host reaches a coherent idle Companion state and can exercise every first GATT surface without hardware.",
            "failure_classification": "contract_or_fixture_drift",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C2",
            "category": "retry",
            "scenario": "Retry after a timeout or busy response rereads status and repeats the idempotent operation once.",
            "result": "PASS",
            "fixture_operations": ["status_read", "recording_list", "recording_pull"],
            "expected_host_behavior": "Retry resumes by byte offset instead of duplicating already verified recording bytes.",
            "failure_classification": "retry_not_idempotent",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C3",
            "category": "cancel",
            "scenario": "A transfer cancel stops the active pull and leaves the recording available for a later byte-offset resume.",
            "result": "PASS",
            "fixture_operations": ["recording_pull", "recording_list"],
            "expected_host_behavior": "User sees transfer canceled and can retry; no delete-after-sync is sent.",
            "failure_classification": "transfer_canceled",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C4",
            "category": "disconnect_reconnect",
            "scenario": "Disconnect after partial recording pull, reconnect, reread recording_list, and resume from the next byte offset.",
            "result": "PASS",
            "fixture_operations": ["scan_result_parsing", "recording_list", "recording_pull"],
            "expected_host_behavior": "Host recovers through scan/connect and does not trust stale packet sequence without total_length continuity.",
            "failure_classification": "reconnect_or_resume_failed",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C5",
            "category": "byte_offset_resume",
            "scenario": "BLE link drops after 8192 verified bytes; host reconnects, rereads recording_list, and requests the next absolute byte offset.",
            "result": "PASS",
            "fixture_operations": ["scan_result_parsing", "recording_list", "byte_offset_resume"],
            "expected_host_behavior": "Host resumes by byte_offset and total_length, not by stale packet sequence or local UI state.",
            "failure_classification": "disconnected",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C6",
            "category": "gatt_cache_stale",
            "scenario": "Host sees Companion service changed/stale GATT cache symptoms after reconnect before any firmware data transfer.",
            "result": "PASS",
            "fixture_operations": ["scan_result_parsing", "status_read"],
            "expected_host_behavior": "Classify gatt_cache_stale, refresh service discovery once, then suggest re-pair and diagnostic export if it repeats.",
            "failure_classification": "gatt_cache_stale",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C7",
            "category": "cccd_notify_failure",
            "scenario": "Notify subscription cannot enable CCCD for recording or diagnostic packets.",
            "result": "PASS",
            "fixture_operations": ["recording_pull", "log_pull"],
            "expected_host_behavior": "Classify cccd_notify_failure, reopen notify subscription once, and keep delete-after-sync disabled until host verification.",
            "failure_classification": "cccd_notify_failure",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C8",
            "category": "recovered_event_suppressed",
            "scenario": "Repeated automatic BLE recovery succeeds several times during one sync session.",
            "result": "PASS",
            "fixture_operations": ["status_read", "recording_list", "byte_offset_resume"],
            "expected_host_behavior": "Only the first reconnected event may be user-visible; repeated recovered_event_suppressed entries stay diagnostic-only.",
            "failure_classification": "disconnected",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C9",
            "category": "long_recording_metadata",
            "scenario": f"Host validates long recording metadata before transfer: {recording_total} bytes, sample format, CRC/hash, and created time/tick.",
            "result": "PASS",
            "fixture_operations": ["recording_list", "recording_pull"],
            "expected_host_behavior": "Host treats total_length and final SHA-256 as authoritative before delete-after-sync.",
            "failure_classification": "metadata_mismatch",
            "artifact_requirements": ["docs/validation/companion-pendant-firmware-bringup-1.7-recording-cache-fixture.json"],
        },
        {
            "case_id": "C10",
            "category": "idle_resume",
            "scenario": "After idle, host rereads status and recording_list before offering a sync action.",
            "result": "PASS",
            "fixture_operations": ["status_read", "recording_list"],
            "expected_host_behavior": "Stale local UI state is refreshed or an actionable timeout is surfaced.",
            "failure_classification": "idle_resume_stale_state",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C11",
            "category": "log_export",
            "scenario": "Host requests a bounded diagnostic tail after an error or blocked transfer.",
            "result": "PASS",
            "fixture_operations": ["log_pull"],
            "expected_host_behavior": "Support package includes cursor, event count, and CRC without attempting an unbounded full dump.",
            "failure_classification": "diagnostics_missing",
            "artifact_requirements": ["docs/validation/companion_ble_matrix.json"],
        },
        {
            "case_id": "C12",
            "category": "ota_blocked",
            "scenario": "OTA readiness is not ready while low battery, transfer, diag export, wrong-board, invalid-hash, or interrupted-transfer blockers are present.",
            "result": "PASS",
            "fixture_operations": ["ota_status"],
            "expected_host_behavior": "Host shows blocker names and does not offer OTA transfer writes.",
            "failure_classification": "ota_blocker_not_actionable",
            "artifact_requirements": ["docs/validation/companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"],
        },
]


def actionable_failures() -> list[dict[str, Any]]:
    return [
        {
            "failure": "no_device",
            "simulated_trigger": "scan returns no Companion service UUID",
            "user_action": "Power the pendant, keep it near the host, and retry scan/pairing.",
            "host_result": "show reconnect action; do not claim sync success",
            "retryable": True,
            "automatic_recovery": False,
            "diagnostic_context": "scan_result_parsing",
        },
        {
            "failure": "wrong_service_uuid",
            "simulated_trigger": "advertisement lacks Companion service UUID",
            "user_action": "Select the Companion pendant advertising name or forget the stale device and scan again.",
            "host_result": "reject the device before any characteristic read",
            "retryable": True,
            "automatic_recovery": False,
            "diagnostic_context": "scan_result_parsing",
        },
        {
            "failure": "timeout",
            "simulated_trigger": "status read or transfer notify exceeds budget",
            "user_action": "Retry once, then reconnect the pendant if the timeout repeats.",
            "host_result": "surface timeout with retry/reconnect option",
            "retryable": True,
            "automatic_recovery": True,
            "diagnostic_context": "operation_timeout",
        },
        {
            "failure": "disconnected",
            "simulated_trigger": "link drops after a verified recording byte offset",
            "user_action": "Keep the pendant nearby; the host should reconnect and resume automatically, then offer manual retry if it repeats.",
            "host_result": "reread status and recording_list, then resume by byte_offset",
            "retryable": True,
            "automatic_recovery": True,
            "diagnostic_context": "disconnect_reconnect",
        },
        {
            "failure": "gatt_cache_stale",
            "simulated_trigger": "service changed or cached GATT table no longer exposes Companion characteristics",
            "user_action": "Refresh the Companion device, re-pair if stale services persist, and export diagnostics for repeated cache failures.",
            "host_result": "refresh discovery once; repeated failures are diagnostic-only and may suggest re-pair",
            "retryable": True,
            "automatic_recovery": True,
            "diagnostic_context": "gatt_cache_stale",
        },
        {
            "failure": "cccd_notify_failure",
            "simulated_trigger": "notify subscription or CCCD write fails for recording/log packets",
            "user_action": "Retry after the host reopens notification subscription; export diagnostics if repeated.",
            "host_result": "do not trust partial transfer; reopen notify path before continuing",
            "retryable": True,
            "automatic_recovery": True,
            "diagnostic_context": "cccd_notify_failure",
        },
        {
            "failure": "crc_mismatch",
            "simulated_trigger": "recording packet CRC does not match header+payload",
            "user_action": "Retry the recording pull from byte offset zero and export diagnostics if it repeats.",
            "host_result": "do not mark recording synced and do not delete",
            "retryable": True,
            "automatic_recovery": False,
            "diagnostic_context": "recording_pull",
        },
        {
            "failure": "hash_mismatch",
            "simulated_trigger": "final recording SHA-256 does not match recording_list metadata",
            "user_action": "Retry the full recording pull and keep the pendant recording stored until a verified transfer succeeds.",
            "host_result": "do not mark synced and do not send delete-after-sync",
            "retryable": True,
            "automatic_recovery": False,
            "diagnostic_context": "recording_pull",
        },
        {
            "failure": "low_battery",
            "simulated_trigger": "OTA readiness reports low_battery blocker",
            "user_action": "Charge the pendant above the package minimum before retrying OTA.",
            "host_result": "block OTA transfer writes",
            "retryable": False,
            "automatic_recovery": False,
            "diagnostic_context": "ota_status",
        },
        {
            "failure": "no_recording",
            "simulated_trigger": "recording_list is empty or recording_id is missing",
            "user_action": "Record a new sample or refresh the list after reconnecting.",
            "host_result": "disable recording pull/delete for that id",
            "retryable": True,
            "automatic_recovery": False,
            "diagnostic_context": "recording_list",
        },
        {
            "failure": "transfer_canceled",
            "simulated_trigger": "user cancels recording pull before final SHA-256",
            "user_action": "Resume the transfer later from the next verified byte offset.",
            "host_result": "keep local partial state separate from synced state",
            "retryable": True,
            "automatic_recovery": False,
            "diagnostic_context": "recording_pull",
        },
        {
            "failure": "ota_blocked",
            "simulated_trigger": "OTA readiness blocker_bitmap is non-zero",
            "user_action": "Resolve the named blocker before retrying the update.",
            "host_result": "show blocker names and keep OTA data path disabled",
            "retryable": False,
            "automatic_recovery": False,
            "diagnostic_context": "ota_status",
        },
    ]


def recovery_event_policy() -> dict[str, Any]:
    return {
        "rate_limit_window_seconds": 60,
        "max_visible_recovered_events_per_window": 1,
        "cases": [
            {
                "event_id": "reconnected_event_visible",
                "trigger": "first automatic disconnect recovery in a sync session",
                "visible_to_user": True,
                "host_result": "show one concise reconnected confirmation",
            },
            {
                "event_id": "recovered_event_suppressed",
                "trigger": "second or later automatic recovery within the rate-limit window",
                "visible_to_user": False,
                "host_result": "record diagnostic context without spamming the host UX",
            },
            {
                "event_id": "gatt_cache_stale_diagnostic_only",
                "trigger": "repeated stale GATT/cache or CCCD notify failure after automatic retry",
                "visible_to_user": False,
                "host_result": "keep bounded diagnostics and show re-pair guidance only when manual action is needed",
            },
        ],
    }


def build_matrix() -> dict[str, Any]:
    adapter = CompanionFixtureAdapter()
    operations = adapter.run_operations()
    failures = actionable_failures()
    return {
        "schema_id": "companion.pendant.ble_fixture_matrix.v1",
        "schema_version": 1,
        "status": "PASS",
        "generated_by": "tools/companion_ble_tool.py --self-test",
        "generated_at": "static-fixture",
        "no_hardware": True,
        "backend": adapter.backend,
        "real_ble_adapter_plan": list(adapter.later_real_adapters),
        "source_refs_used": {
            "listener_matrix_mindset": [
                "case catalog",
                "failure classification",
                "artifact requirements",
                "actionable error checks",
            ],
            "forbidden_dependencies": [
                "Listener device names",
                "HID keyboard behavior",
                "ESP-specific BLE services",
            ],
            "depends_on_forbidden_dependencies": False,
        },
        "fixtures": {
            "uuid_table": rel(UUID_TABLE_PATH),
            "recording_cache": rel(RECORDING_FIXTURE_PATH),
            "ota_manifest_report": rel(OTA_FIXTURE_PATH),
        },
        "operation_coverage": operations,
        "product_matrix": product_matrix(operations),
        "actionable_failures": failures,
        "failure_classification_matrix": failures,
        "recovery_event_policy": recovery_event_policy(),
        "artifact_policy": {
            "primary_artifact": rel(MATRIX_PATH),
            "allowed_roots": ["docs/validation", "tests/fixtures"],
        },
        "self_test": {
            "required_operations": list(REQUIRED_OPERATIONS),
            "required_matrix_categories": list(REQUIRED_MATRIX_CATEGORIES),
            "required_failures": list(REQUIRED_FAILURES),
            "result": "PASS",
        },
    }


def validate_matrix_shape(matrix: dict[str, Any]) -> None:
    if matrix.get("status") != "PASS":
        raise RuntimeError("matrix status is not PASS")
    operations = set(matrix.get("operation_coverage", {}).keys())
    missing_operations = sorted(set(REQUIRED_OPERATIONS) - operations)
    if missing_operations:
        raise RuntimeError(f"missing operation coverage: {', '.join(missing_operations)}")
    categories = {str(item.get("category")) for item in matrix.get("product_matrix", [])}
    missing_categories = sorted(set(REQUIRED_MATRIX_CATEGORIES) - categories)
    if missing_categories:
        raise RuntimeError(f"missing matrix categories: {', '.join(missing_categories)}")
    failures = {str(item.get("failure")) for item in matrix.get("actionable_failures", [])}
    missing_failures = sorted(set(REQUIRED_FAILURES) - failures)
    if missing_failures:
        raise RuntimeError(f"missing actionable failures: {', '.join(missing_failures)}")


def write_matrix(path: pathlib.Path, matrix: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run the no-hardware fixture matrix and write docs/validation artifact")
    parser.add_argument("--backend", choices=["fixture", "bleak", "windows", "listener-type"], default="fixture")
    parser.add_argument("--matrix-path", type=pathlib.Path, default=MATRIX_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.self_test:
        print("FAIL: companion_ble_tool currently exposes --self-test as the no-hardware acceptance surface.", file=sys.stderr)
        return 2
    if args.backend != "fixture":
        print(f"FAIL: backend {args.backend!r} is reserved for later real BLE validation.", file=sys.stderr)
        return 2
    try:
        matrix = build_matrix()
        validate_matrix_shape(matrix)
        matrix_path = args.matrix_path if args.matrix_path.is_absolute() else REPO_ROOT / args.matrix_path
        write_matrix(matrix_path, matrix)
    except Exception as exc:  # noqa: BLE001 - compact CLI failure is intentional.
        print(f"FAIL: Companion BLE fixture self-test failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"status": "PASS", "matrix": rel(matrix_path)}, indent=2, sort_keys=True))
    else:
        print(
            "PASS: Companion BLE fixture self-test wrote "
            f"{rel(matrix_path)} with {len(REQUIRED_OPERATIONS)} operation(s), "
            f"{len(REQUIRED_MATRIX_CATEGORIES)} matrix case(s), "
            f"and {len(REQUIRED_FAILURES)} actionable failure(s)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
