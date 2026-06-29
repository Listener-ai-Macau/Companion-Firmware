#!/usr/bin/env python3
"""Real BLE bench for the Companion-native STM32WB GATT surface."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import pathlib
import struct
import subprocess
import sys
import time
from typing import Any, Callable


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE_PATH = REPO_ROOT / "docs" / "ble_uuid_table.json"
SCHEMA_VERSION = 1


class BenchError(RuntimeError):
    """A compact validation failure that should be reported in the artifact."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_uuid_table() -> dict[str, Any]:
    return json.loads(UUID_TABLE_PATH.read_text(encoding="utf-8"))


def build_uuid_index(table: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for service in table.get("services", []):
        index[str(service["service"])] = str(service["uuid"]).lower()
        for char in service.get("characteristics", []):
            index[str(char["name"])] = str(char["uuid"]).lower()
    return index


def required_services(table: dict[str, Any]) -> set[str]:
    return {str(service["uuid"]).lower() for service in table.get("services", [])}


def required_characteristics(table: dict[str, Any]) -> set[str]:
    uuids: set[str] = set()
    for service in table.get("services", []):
        for char in service.get("characteristics", []):
            name = str(char["name"])
            if name.startswith("ota_st_"):
                continue
            uuids.add(str(char["uuid"]).lower())
    return uuids


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def parse_struct(fmt: str, names: tuple[str, ...], payload: bytes) -> dict[str, Any]:
    size = struct.calcsize(fmt)
    if len(payload) < size:
        raise BenchError(f"payload too short: got {len(payload)}, need {size}")
    values = struct.unpack(fmt, payload[:size])
    parsed = dict(zip(names, values, strict=True))
    if parsed.get("schema_version") != SCHEMA_VERSION:
        raise BenchError(f"unexpected schema_version={parsed.get('schema_version')}")
    return parsed


def parse_device_status(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHIIII",
        (
            "schema_version",
            "active_mode",
            "fault_bitmap",
            "firmware_version",
            "build_id",
            "board_id",
            "uptime_ms",
        ),
        payload,
    )


def parse_battery_charge(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBHh",
        (
            "schema_version",
            "percent",
            "charge_state",
            "charger_present",
            "millivolts",
            "temperature_c_x10",
        ),
        payload,
    )


def parse_card_status(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBIII",
        (
            "schema_version",
            "card_slot",
            "render_state",
            "last_error",
            "request_id",
            "content_crc32",
            "refresh_count",
        ),
        payload,
    )


def parse_recording_control(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBBBIH",
        (
            "schema_version",
            "command",
            "profile_id",
            "privacy_flags",
            "request_id",
            "max_seconds",
        ),
        payload,
    )


def parse_recording_list(payload: bytes) -> dict[str, Any]:
    return parse_struct("<BBH", ("schema_version", "count", "entry_bytes"), payload)


def parse_recording_chunk_pull(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHIII",
        (
            "schema_version",
            "flags",
            "requested_length",
            "recording_id",
            "byte_offset",
            "host_resume_token",
        ),
        payload,
    )


def parse_settings(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHhBBBB",
        (
            "schema_version",
            "locale",
            "flags",
            "time_zone_offset_min",
            "quiet_hours_start_min",
            "quiet_hours_end_min",
            "display_brightness",
            "recorder_profile_id",
        ),
        payload,
    )


def parse_diag_log_pull(payload: bytes) -> dict[str, Any]:
    return parse_struct(
        "<BBHIHH",
        (
            "schema_version",
            "source_mask",
            "severity_mask",
            "cursor",
            "max_events",
            "max_bytes",
        ),
        payload,
    )


def parse_delete_privacy(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBHIII32s",
        (
            "schema_version",
            "operation",
            "flags",
            "request_id",
            "recording_id",
            "validated_total_length",
            "validated_sha256",
        ),
        payload,
    )
    parsed["validated_sha256"] = parsed["validated_sha256"].hex()
    return parsed


def parse_ota_readiness(payload: bytes) -> dict[str, Any]:
    parsed = parse_struct(
        "<BBBBHHII8s",
        (
            "schema_version",
            "ready_state",
            "boot_slot",
            "battery_percent",
            "minimum_required_mv",
            "blocker_bitmap",
            "manifest_version",
            "image_size",
            "image_sha256_prefix",
        ),
        payload,
    )
    parsed["image_sha256_prefix"] = parsed["image_sha256_prefix"].hex()
    return parsed


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise BenchError(message)


def normalize_address(address: str | None) -> str:
    return "" if address is None else address.replace(":", "").replace("-", "").lower()


def advertisement_services(adv: Any, device: Any) -> list[str]:
    service_uuids = getattr(adv, "service_uuids", None)
    if service_uuids is None:
        metadata = getattr(device, "metadata", {}) or {}
        service_uuids = metadata.get("uuids", [])
    return sorted({str(uuid).lower() for uuid in service_uuids or []})


async def scan_for_companion(args: argparse.Namespace, required: set[str]) -> tuple[Any, dict[str, Any]]:
    try:
        from bleak import BleakScanner
    except Exception as exc:  # noqa: BLE001 - CLI reports availability directly.
        raise BenchError(f"bleak import failed: {exc}") from exc

    discovered: list[tuple[Any, Any | None]] = []
    try:
        raw = await BleakScanner.discover(timeout=args.timeout, return_adv=True)
        for value in raw.values():
            if isinstance(value, tuple) and len(value) == 2:
                discovered.append((value[0], value[1]))
    except TypeError:
        for device in await BleakScanner.discover(timeout=args.timeout):
            discovered.append((device, None))

    target_address = normalize_address(args.address)
    target_name = args.name.lower()
    candidates: list[tuple[Any, Any | None, list[str], int | None, str]] = []
    for device, adv in discovered:
        name = (getattr(device, "name", None) or getattr(adv, "local_name", None) or "")
        address = str(getattr(device, "address", ""))
        adv_uuids = advertisement_services(adv, device)
        rssi = getattr(adv, "rssi", None)
        if rssi is None:
            rssi = getattr(device, "rssi", None)
        address_match = target_address and normalize_address(address) == target_address
        name_match = target_name in name.lower()
        service_match = bool(required.intersection(adv_uuids))
        if address_match or name_match or service_match:
            candidates.append((device, adv, adv_uuids, rssi, name))

    if not candidates:
        seen = [
            {
                "name": getattr(device, "name", None),
                "address": getattr(device, "address", None),
                "service_uuids": advertisement_services(adv, device),
            }
            for device, adv in discovered[:12]
        ]
        raise BenchError(f"no Companion candidate found; seen={seen}")

    def score(candidate: tuple[Any, Any | None, list[str], int | None, str]) -> tuple[int, int]:
        device, _adv, adv_uuids, rssi, name = candidate
        address = str(getattr(device, "address", ""))
        return (
            100 if target_address and normalize_address(address) == target_address else 0
        ) + (
            20 if target_name and target_name in name.lower() else 0
        ) + (
            len(required.intersection(adv_uuids))
        ), int(rssi if rssi is not None else -999)

    selected = max(candidates, key=score)
    device, _adv, adv_uuids, rssi, name = selected
    return device, {
        "operation": "scan",
        "status": "PASS",
        "selected_name": name,
        "selected_address": str(getattr(device, "address", "")),
        "rssi": rssi,
        "advertised_service_uuids": adv_uuids,
        "advertised_required_service_uuids": sorted(required.intersection(adv_uuids)),
        "candidate_count": len(candidates),
        "seen_count": len(discovered),
    }


async def get_services(client: Any) -> Any:
    services = getattr(client, "services", None)
    if services is None and hasattr(client, "get_services"):
        services = await client.get_services()
    if services is None:
        raise BenchError("Bleak client did not expose services after connect")
    return services


def characteristic_uuid_set(services: Any) -> set[str]:
    uuids: set[str] = set()
    for service in services:
        for char in service.characteristics:
            uuids.add(str(char.uuid).lower())
    return uuids


def service_uuid_set(services: Any) -> set[str]:
    return {str(service.uuid).lower() for service in services}


async def read_and_parse(client: Any, uuid: str, parser: Callable[[bytes], dict[str, Any]]) -> dict[str, Any]:
    payload = bytes(await client.read_gatt_char(uuid))
    return parser(payload)


async def notify_write_wait(
    client: Any,
    notify_uuid: str,
    write_uuid: str,
    payload: bytes,
    parser: Callable[[bytes], dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    timeout: float,
) -> dict[str, Any]:
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(_sender: Any, data: bytearray) -> None:
        queue.put_nowait(bytes(data))

    await client.start_notify(notify_uuid, callback)
    try:
        await asyncio.sleep(0.15)
        await client.write_gatt_char(write_uuid, payload, response=True)
        deadline = time.monotonic() + timeout
        last: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=remaining)
            except asyncio.TimeoutError as exc:
                raise BenchError(f"notify timeout on {notify_uuid}; last={last}") from exc
            parsed = parser(raw)
            last = parsed
            if predicate(parsed):
                return parsed
        raise BenchError(f"notify predicate was not satisfied on {notify_uuid}; last={last}")
    finally:
        await client.stop_notify(notify_uuid)


async def run_connected_bench(client: Any, uuids: dict[str, str], args: argparse.Namespace) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []

    device_status = await read_and_parse(client, uuids["device_status"], parse_device_status)
    battery_charge = await read_and_parse(client, uuids["battery_charge"], parse_battery_charge)
    assert_true(0 <= int(battery_charge["percent"]) <= 100, "battery percent out of range")
    operations.append(
        {
            "operation": "status_read",
            "status": "PASS",
            "device_status": device_status,
            "battery_charge": battery_charge,
        }
    )

    title = "Bench card".encode("utf-8")
    body = "Companion native BLE card write bench".encode("utf-8")
    card_request_id = 17
    card_payload = struct.pack("<BBHIHH", SCHEMA_VERSION, 0, 0, card_request_id, len(title), len(body))
    card_payload += title + body
    card_status = await notify_write_wait(
        client,
        uuids["e_paper_card_status"],
        uuids["e_paper_card_write"],
        card_payload,
        parse_card_status,
        lambda parsed: parsed["request_id"] == card_request_id,
        args.notify_timeout,
    )
    assert_true(card_status["render_state"] == 1, "card write was not accepted by bench status")
    operations.append({"operation": "card_write", "status": "PASS", "card_status": card_status})

    recording_request_id = 23
    recording_payload = struct.pack("<BBBBIH", SCHEMA_VERSION, 2, 1, 0, recording_request_id, 5)
    recording_echo = await notify_write_wait(
        client,
        uuids["recording_control"],
        uuids["recording_control"],
        recording_payload,
        parse_recording_control,
        lambda parsed: parsed["request_id"] == recording_request_id,
        args.notify_timeout,
    )
    recording_list = await read_and_parse(client, uuids["recording_list"], parse_recording_list)
    assert_true(recording_list["count"] == 0, "NUCLEO bench should expose an empty recording list")
    operations.append(
        {
            "operation": "recording_control_and_list",
            "status": "PASS",
            "recording_control_echo": recording_echo,
            "recording_list": recording_list,
        }
    )

    chunk_payload = struct.pack("<BBHIII", SCHEMA_VERSION, 0, 64, 1, 0, 0x1234)
    chunk_response = await notify_write_wait(
        client,
        uuids["recording_chunk_pull"],
        uuids["recording_chunk_pull"],
        chunk_payload,
        parse_recording_chunk_pull,
        lambda parsed: (parsed["flags"] & 0x80) != 0,
        args.notify_timeout,
    )
    assert_true(chunk_response["requested_length"] == 0, "recording chunk refusal did not clear requested_length")
    operations.append(
        {
            "operation": "recording_chunk_refusal",
            "status": "PASS",
            "recording_chunk_pull": chunk_response,
        }
    )

    settings_payload = struct.pack("<BBHhBBBB", SCHEMA_VERSION, 0, 0, 480, 0, 0, 81, 1)
    settings = await notify_write_wait(
        client,
        uuids["settings"],
        uuids["settings"],
        settings_payload,
        parse_settings,
        lambda parsed: parsed["display_brightness"] == 81,
        args.notify_timeout,
    )
    operations.append({"operation": "settings_write", "status": "PASS", "settings": settings})

    diag_payload = struct.pack("<BBHIHH", SCHEMA_VERSION, 1, 0xFFFF, 0, 4, 64)
    diag = await notify_write_wait(
        client,
        uuids["diagnostics_log_pull"],
        uuids["diagnostics_log_pull"],
        diag_payload,
        parse_diag_log_pull,
        lambda parsed: parsed["cursor"] == 1,
        args.notify_timeout,
    )
    assert_true(diag["max_bytes"] <= 64, "diagnostics response exceeded requested byte bound")
    operations.append({"operation": "diagnostics_log_pull", "status": "PASS", "diagnostics": diag})

    delete_request_id = 77
    delete_payload = struct.pack("<BBHIII32s", SCHEMA_VERSION, 1, 0, delete_request_id, 1, 1234, bytes(32))
    delete_response = await notify_write_wait(
        client,
        uuids["delete_privacy"],
        uuids["delete_privacy"],
        delete_payload,
        parse_delete_privacy,
        lambda parsed: parsed["request_id"] == delete_request_id,
        args.notify_timeout,
    )
    assert_true((delete_response["flags"] & 0x0001) != 0, "delete/privacy refusal flag was not set")
    operations.append({"operation": "delete_privacy_refusal", "status": "PASS", "delete_privacy": delete_response})

    ota = await read_and_parse(client, uuids["ota_readiness"], parse_ota_readiness)
    assert_true(ota["battery_percent"] <= 100, "OTA battery percent out of range")
    operations.append({"operation": "ota_readiness", "status": "PASS", "ota_readiness": ota})

    return operations


async def run_bench(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from bleak import BleakClient
    except Exception as exc:  # noqa: BLE001 - CLI reports availability directly.
        raise BenchError(f"bleak import failed: {exc}") from exc

    started = utc_now()
    monotonic_start = time.monotonic()
    table = load_uuid_table()
    uuids = build_uuid_index(table)
    needed_services = required_services(table)
    needed_chars = required_characteristics(table)

    device, scan_operation = await scan_for_companion(args, needed_services)
    operations: list[dict[str, Any]] = [scan_operation]

    async with BleakClient(device, timeout=args.timeout) as client:
        services = await get_services(client)
        found_services = service_uuid_set(services)
        found_chars = characteristic_uuid_set(services)
        missing_services = sorted(needed_services - found_services)
        missing_chars = sorted(needed_chars - found_chars)
        assert_true(not missing_services, f"missing services after connect: {missing_services}")
        assert_true(not missing_chars, f"missing characteristics after connect: {missing_chars}")
        operations.append(
            {
                "operation": "service_discovery",
                "status": "PASS",
                "service_count": len(found_services),
                "characteristic_count": len(found_chars),
                "required_services": sorted(needed_services),
                "required_characteristics": sorted(needed_chars),
            }
        )
        operations.extend(await run_connected_bench(client, uuids, args))

    ended = utc_now()
    return {
        "schema_version": 1,
        "tool": "tools/companion_ble_real_bench.py",
        "backend": "python-bleak",
        "status": "PASS",
        "started_at": started,
        "ended_at": ended,
        "duration_s": round(time.monotonic() - monotonic_start, 3),
        "firmware_commit": git_commit(),
        "target": {
            "name_filter": args.name,
            "address_filter": args.address,
        },
        "operations": operations,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="companion", help="BLE local-name substring to select")
    parser.add_argument("--address", default=None, help="Optional exact BLE address filter")
    parser.add_argument("--timeout", type=float, default=12.0, help="Scan/connect timeout seconds")
    parser.add_argument("--notify-timeout", type=float, default=6.0, help="Notify wait timeout seconds")
    parser.add_argument("--output", type=pathlib.Path, default=None, help="Optional JSON artifact path")
    parser.add_argument("--json", action="store_true", help="Print the full JSON artifact")
    return parser.parse_args(argv)


def write_output(path: pathlib.Path, result: dict[str, Any]) -> None:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = asyncio.run(run_bench(args))
    except Exception as exc:  # noqa: BLE001 - CLI should emit compact failure evidence.
        result = {
            "schema_version": 1,
            "tool": "tools/companion_ble_real_bench.py",
            "backend": "python-bleak",
            "status": "FAIL",
            "firmware_commit": git_commit(),
            "error": str(exc),
            "ended_at": utc_now(),
            "target": {
                "name_filter": args.name,
                "address_filter": args.address,
            },
        }
        if args.output is not None:
            write_output(args.output, result)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        print(f"FAIL: Companion BLE real bench failed: {exc}", file=sys.stderr)
        return 1

    if args.output is not None:
        write_output(args.output, result)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "PASS: Companion BLE real bench passed; "
            f"{len(result['operations'])} operation(s), {result['duration_s']}s."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
