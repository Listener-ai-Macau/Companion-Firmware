#!/usr/bin/env python3
"""Companion-owned BLE OTA v2 transfer tool.

This is the independent host path for the STM32WB Companion OTA loader. It
reads the Companion OTA manifest, sends the COV2 BEGIN/DATA/FINISH protocol over
BLE with Bleak, and writes a structured artifact compatible with the manual gate
evidence checker.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import pathlib
import struct
import sys
import time
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

MAGIC = b"COV2"
PROTOCOL_VERSION = 1
OP_BEGIN = 1
OP_SYNC = 2
OP_FINISH = 3
OP_ABORT = 4
STATE_RECEIVING = 2
STATE_COMPLETE = 3
STATE_ERROR = 4
STATUS_SIZE = 24


class OtaError(RuntimeError):
    """Compact validation failure used in JSON artifacts."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_address(address: str | None) -> str:
    return "" if address is None else address.replace(":", "").replace("-", "").lower()


def parse_status(raw: bytes) -> dict[str, Any]:
    data = bytes(raw)
    if len(data) < STATUS_SIZE:
        raise OtaError(f"status payload too short: {len(data)}")
    if data[:4] != MAGIC:
        raise OtaError(f"status magic mismatch: {data[:4]!r}")
    version, state, last_error = struct.unpack_from("<BBB", data, 4)
    bytes_written, expected_size, chunk_bytes, window_chunks, data_write_count = struct.unpack_from(
        "<IIHHI", data, 8
    )
    return {
        "magic": "COV2",
        "version": version,
        "state": state,
        "last_error": last_error,
        "bytes_written": bytes_written,
        "expected_size": expected_size,
        "chunk_bytes": chunk_bytes,
        "window_chunks": window_chunks,
        "data_write_count": data_write_count,
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise OtaError(message)


def advertisement_services(adv: Any, device: Any) -> list[str]:
    service_uuids = getattr(adv, "service_uuids", None)
    if service_uuids is None:
        service_uuids = (getattr(device, "metadata", {}) or {}).get("uuids", [])
    return sorted({str(uuid).lower() for uuid in service_uuids or []})


async def scan_for_target(args: argparse.Namespace, service_uuid: str) -> tuple[Any, dict[str, Any]]:
    try:
        from bleak import BleakScanner
    except Exception as exc:  # noqa: BLE001
        raise OtaError(f"bleak import failed: {exc}") from exc

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
        name_match = target_name and target_name in name.lower()
        service_match = service_uuid.lower() in adv_uuids
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
        raise OtaError(f"no Companion OTA candidate found; seen={seen}")

    def score(candidate: tuple[Any, Any | None, list[str], int | None, str]) -> tuple[int, int]:
        device, _adv, adv_uuids, rssi, name = candidate
        address = str(getattr(device, "address", ""))
        value = 0
        if target_address and normalize_address(address) == target_address:
            value += 100
        if target_name and target_name in name.lower():
            value += 20
        if service_uuid.lower() in adv_uuids:
            value += 40
        return value, int(rssi if rssi is not None else -999)

    selected = max(candidates, key=score)
    device, _adv, adv_uuids, rssi, name = selected
    return device, {
        "operation": "scan",
        "status": "PASS",
        "selected_name": name,
        "selected_address": str(getattr(device, "address", "")),
        "rssi": rssi,
        "advertised_service_uuids": adv_uuids,
        "target_service_uuid": service_uuid.lower(),
        "target_service_advertised": service_uuid.lower() in adv_uuids,
        "candidate_count": len(candidates),
        "seen_count": len(discovered),
    }


async def get_services(client: Any) -> Any:
    services = getattr(client, "services", None)
    if services is None and hasattr(client, "get_services"):
        services = await client.get_services()
    if services is None:
        raise OtaError("Bleak client did not expose services after connect")
    return services


async def read_status(client: Any, status_uuid: str) -> dict[str, Any]:
    return parse_status(bytes(await client.read_gatt_char(status_uuid)))


async def wait_for_receiving(client: Any, status_uuid: str, timeout_s: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last = await read_status(client, status_uuid)
        if last["state"] == STATE_RECEIVING:
            return last
        if last["state"] == STATE_ERROR:
            raise OtaError(f"loader entered error state after BEGIN: {last}")
        await asyncio.sleep(0.25)
    raise OtaError(f"timeout waiting for receiving state; last={last}")


async def run_transfer(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from bleak import BleakClient
    except Exception as exc:  # noqa: BLE001
        raise OtaError(f"bleak import failed: {exc}") from exc

    started = utc_now()
    monotonic_start = time.monotonic()
    manifest = load_manifest(args.manifest)
    protocol = manifest.get("protocol", {})
    gatt = protocol.get("gatt", {})
    protocol_name = str(protocol.get("name", ""))
    require(protocol_name == "companion_ota_v2", f"unsupported manifest protocol {protocol_name!r}")

    service_uuid = str(gatt.get("service_uuid", "")).lower()
    control_uuid = str(gatt.get("control_uuid", "")).lower()
    data_uuid = str(gatt.get("data_uuid", "")).lower()
    status_uuid = str(gatt.get("status_uuid", "")).lower()
    chunk_bytes = int(gatt.get("chunk_bytes", 240))
    window_chunks = int(args.window_chunks or 8)
    require(service_uuid and control_uuid and data_uuid and status_uuid, "manifest missing OTA v2 GATT UUIDs")
    require(1 <= chunk_bytes <= 244, f"unsupported chunk_bytes={chunk_bytes}")

    firmware = args.firmware
    firmware_size = firmware.stat().st_size
    firmware_hash = file_sha256(firmware)
    manifest_hash = str((manifest.get("file", {}) or {}).get("sha256", "")).lower()
    manifest_size = int((manifest.get("file", {}) or {}).get("size_bytes", 0))
    require(firmware_size == manifest_size, f"firmware size {firmware_size} != manifest {manifest_size}")
    require(firmware_hash == manifest_hash, "firmware SHA-256 does not match manifest")

    operations: list[dict[str, Any]] = []
    device, scan_operation = await scan_for_target(args, service_uuid)
    operations.append(scan_operation)

    disconnect_observed = False

    def on_disconnect(_client: Any) -> None:
        nonlocal disconnect_observed
        disconnect_observed = True

    async with BleakClient(device, timeout=args.timeout, disconnected_callback=on_disconnect) as client:
        services = await get_services(client)
        found_services = {str(service.uuid).lower() for service in services}
        found_chars = {
            str(char.uuid).lower()
            for service in services
            for char in service.characteristics
        }
        missing = sorted({service_uuid, control_uuid, data_uuid, status_uuid} - (found_services | found_chars))
        require(not missing, f"missing OTA service/characteristics after connect: {missing}")
        operations.append(
            {
                "operation": "service_discovery",
                "status": "PASS",
                "service_uuid": service_uuid,
                "control_uuid": control_uuid,
                "data_uuid": data_uuid,
                "status_uuid": status_uuid,
            }
        )

        initial_status = await read_status(client, status_uuid)
        operations.append({"operation": "initial_status", "status": "PASS", "ota_status": initial_status})

        begin = bytearray(16)
        begin[0:4] = MAGIC
        begin[4] = OP_BEGIN
        begin[5] = PROTOCOL_VERSION
        struct.pack_into("<IHH", begin, 8, firmware_size, chunk_bytes, window_chunks)
        await client.write_gatt_char(control_uuid, bytes(begin), response=True)
        begin_status = await wait_for_receiving(client, status_uuid, args.begin_timeout)
        operations.append({"operation": "begin", "status": "PASS", "ota_status": begin_status})

        bytes_sent = 0
        writes = 0
        with firmware.open("rb") as f:
            while True:
                payload = f.read(chunk_bytes)
                if not payload:
                    break
                packet = struct.pack("<I", bytes_sent) + payload
                await client.write_gatt_char(data_uuid, packet, response=args.write_response)
                bytes_sent += len(payload)
                writes += 1
                if writes % max(1, window_chunks) == 0:
                    status = await read_status(client, status_uuid)
                    if status["state"] == STATE_ERROR:
                        raise OtaError(f"loader entered error state during data transfer: {status}")
                    if status["bytes_written"] > bytes_sent:
                        raise OtaError(f"loader bytes_written advanced past host offset: {status}")
        final_data_status = await read_status(client, status_uuid)
        require(
            int(final_data_status["bytes_written"]) == firmware_size,
            f"loader bytes_written={final_data_status['bytes_written']} expected={firmware_size}",
        )
        operations.append({"operation": "data", "status": "PASS", "ota_status": final_data_status})

        finish = bytearray(16)
        finish[0:4] = MAGIC
        finish[4] = OP_FINISH
        finish[5] = PROTOCOL_VERSION
        await client.write_gatt_char(control_uuid, bytes(finish), response=True)
        finish_status: dict[str, Any] | None = None
        deadline = time.monotonic() + args.finish_timeout
        while time.monotonic() < deadline and not disconnect_observed:
            try:
                finish_status = await read_status(client, status_uuid)
                if finish_status["state"] == STATE_COMPLETE:
                    break
                if finish_status["state"] == STATE_ERROR:
                    raise OtaError(f"loader entered error state after FINISH: {finish_status}")
            except Exception:
                disconnect_observed = True
                break
            await asyncio.sleep(0.2)

    version_confirmed = bytes_sent == firmware_size and (disconnect_observed or finish_status is not None)
    operations.append(
        {
            "operation": "finish",
            "status": "PASS" if version_confirmed else "FAIL",
            "ota_status": finish_status,
            "disconnect_observed": disconnect_observed,
        }
    )
    require(version_confirmed, "finish did not produce completion status or reset/disconnect evidence")

    return {
        "schema_version": 1,
        "tool": "tools/companion_ble_ota_v2.py",
        "backend": "python-bleak",
        "status": "PASS",
        "started_at": started,
        "ended_at": utc_now(),
        "duration_s": round(time.monotonic() - monotonic_start, 3),
        "manifest": {
            "path": str(args.manifest),
            "version": str(manifest.get("version", "")),
            "protocolName": protocol_name,
            "protocol_name": protocol_name,
            "service_uuid": service_uuid,
        },
        "firmwareSha256": firmware_hash,
        "firmware_sha256": firmware_hash,
        "transfer": {
            "transport": "companion_ota_v2",
            "bytesTransferred": bytes_sent,
            "bytes_transferred": bytes_sent,
            "dataWriteCount": writes,
            "data_write_count": writes,
            "chunkBytes": chunk_bytes,
            "chunk_bytes": chunk_bytes,
            "windowChunks": window_chunks,
            "window_chunks": window_chunks,
            "versionConfirmed": True,
            "version_confirmed": True,
            "disconnectObserved": disconnect_observed,
            "disconnect_observed": disconnect_observed,
        },
        "target": {
            "name_filter": args.name,
            "address_filter": args.address,
        },
        "operations": operations,
    }


def write_output(path: pathlib.Path, result: dict[str, Any]) -> None:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--firmware", type=pathlib.Path, required=True)
    parser.add_argument("--name", default="companion")
    parser.add_argument("--address", default=None)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--begin-timeout", type=float, default=20.0)
    parser.add_argument("--finish-timeout", type=float, default=8.0)
    parser.add_argument("--window-chunks", type=int, default=0)
    parser.add_argument("--write-without-response", dest="write_response", action="store_false")
    parser.set_defaults(write_response=True)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = asyncio.run(run_transfer(args))
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema_version": 1,
            "tool": "tools/companion_ble_ota_v2.py",
            "backend": "python-bleak",
            "status": "FAIL",
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
        print(f"FAIL: Companion BLE OTA v2 transfer failed: {exc}", file=sys.stderr)
        return 1

    if args.output is not None:
        write_output(args.output, result)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        transfer = result["transfer"]
        print(
            "PASS: Companion BLE OTA v2 transfer completed; "
            f"{transfer['bytesTransferred']} bytes in {transfer['dataWriteCount']} write(s)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
