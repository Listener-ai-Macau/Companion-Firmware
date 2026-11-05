#!/usr/bin/env python3
"""Diagnose Companion BLE connect/service discovery while capturing serial logs."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import pathlib
import queue
import subprocess
import sys
import threading
import time
import traceback
from typing import Any

import serial
from serial.tools import list_ports


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
UUID_TABLE_PATH = REPO_ROOT / "docs" / "ble_uuid_table.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_address(value: str | None) -> str:
    return "" if value is None else value.replace(":", "").replace("-", "").lower()


def resolve_artifact_dir(path: pathlib.Path | None) -> pathlib.Path:
    if path is not None:
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = REPO_ROOT / ".cache" / "validation" / f"companion-ble-connect-serial-{stamp}"
    output.mkdir(parents=True, exist_ok=True)
    return output


def resolve_serial_port(requested: str | None) -> tuple[str, list[dict[str, Any]]]:
    ports: list[dict[str, Any]] = []
    for port in list_ports.comports():
        item = {
            "device": port.device,
            "description": port.description,
            "manufacturer": port.manufacturer,
            "hwid": port.hwid,
            "vid": port.vid,
            "pid": port.pid,
        }
        ports.append(item)
        if requested and port.device.upper() == requested.upper():
            return port.device, ports

    if requested:
        raise RuntimeError(f"requested serial port is not present: {requested}; present={ports}")

    candidates = [
        item
        for item in ports
        if item.get("vid") == 0x0483
        or "ST-LINK" in str(item.get("description", "")).upper()
        or "STMICROELECTRONICS" in str(item.get("manufacturer", "")).upper()
        or "VID:PID=0483" in str(item.get("hwid", "")).upper()
    ]
    if len(candidates) == 1:
        return str(candidates[0]["device"]), ports
    if not candidates:
        raise RuntimeError(f"no ST-LINK/STM32 serial port found; present={ports}")
    raise RuntimeError(f"multiple ST-LINK/STM32 serial ports found; pass --serial-port. candidates={candidates}")


class SerialMonitor:
    def __init__(self, port: str, baud: int, raw_log_path: pathlib.Path) -> None:
        self.port = port
        self.baud = baud
        self.raw_log_path = raw_log_path
        self.lines: list[str] = []
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._serial: serial.Serial | None = None
        self._buffer = bytearray()

    def start(self) -> None:
        self.raw_log_path.write_text("", encoding="utf-8")
        ser = serial.Serial()
        ser.port = self.port
        ser.baudrate = self.baud
        ser.timeout = 0.05
        ser.dsrdtr = False
        ser.rtscts = False
        ser.dtr = False
        ser.rts = False
        ser.open()
        ser.setDTR(False)
        ser.setRTS(False)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        self._serial = ser
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    def _reader(self) -> None:
        assert self._serial is not None
        while not self._stop.is_set():
            try:
                data = self._serial.read(256)
            except Exception as exc:  # noqa: BLE001
                self._queue.put(f"__SERIAL_ERROR__ {type(exc).__name__}: {exc}")
                return
            if not data:
                continue
            with self.raw_log_path.open("ab") as raw:
                raw.write(data)
            self._buffer.extend(data)
            while b"\n" in self._buffer:
                raw_line, _, self._buffer = self._buffer.partition(b"\n")
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line:
                    self.lines.append(line)
                    self._queue.put(line)


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def load_required_services() -> list[str]:
    table = json.loads(UUID_TABLE_PATH.read_text(encoding="utf-8"))
    return [str(service["uuid"]).lower() for service in table.get("services", [])]


def advertisement_services(adv: Any, device: Any) -> list[str]:
    service_uuids = getattr(adv, "service_uuids", None)
    if service_uuids is None:
        metadata = getattr(device, "metadata", {}) or {}
        service_uuids = metadata.get("uuids", [])
    return sorted({str(uuid).lower() for uuid in service_uuids or []})


def adv_props(device: Any, adv: Any | None) -> dict[str, Any]:
    raw_adv = getattr(device, "details", None)
    winrt_adv = getattr(raw_adv, "adv", None)
    props: dict[str, Any] = {}
    if winrt_adv is not None:
        for key in ("advertisement_type", "bluetooth_address", "bluetooth_address_type", "is_connectable"):
            try:
                props[key] = str(getattr(winrt_adv, key))
            except Exception as exc:  # noqa: BLE001
                props[key] = f"{type(exc).__name__}: {exc}"
    return {
        "name": getattr(device, "name", None) or (getattr(adv, "local_name", None) if adv is not None else None),
        "address": getattr(device, "address", None),
        "details": repr(getattr(device, "details", None)),
        "rssi": getattr(adv, "rssi", None) if adv is not None else getattr(device, "rssi", None),
        "local_name": getattr(adv, "local_name", None) if adv is not None else None,
        "service_uuids": advertisement_services(adv, device) if adv is not None else [],
        "manufacturer_data": {
            str(key): bytes(value).hex()
            for key, value in (getattr(adv, "manufacturer_data", {}) or {}).items()
        }
        if adv is not None
        else {},
        "winrt": props,
    }


async def scan_target(args: argparse.Namespace) -> tuple[Any | None, list[dict[str, Any]]]:
    from bleak import BleakScanner

    discovered: list[dict[str, Any]] = []
    selected: Any | None = None
    target_address = normalize_address(args.address)
    raw = await BleakScanner.discover(timeout=args.scan_timeout, return_adv=True)
    for value in raw.values():
        device, adv = value if isinstance(value, tuple) else (value, None)
        record = adv_props(device, adv)
        name = str(record.get("name") or "")
        address = str(record.get("address") or "")
        match = (
            bool(target_address and normalize_address(address) == target_address)
            or args.name.lower() in name.lower()
        )
        if match:
            discovered.append(record)
            if selected is None or normalize_address(address) == target_address:
                selected = device
    return selected, discovered


async def connect_attempt(label: str, target: Any, kwargs: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    from bleak import BleakClient

    started = time.monotonic()
    result: dict[str, Any] = {
        "label": label,
        "kwargs": kwargs,
        "started_at": utc_now(),
    }

    async def inner() -> dict[str, Any]:
        client = BleakClient(target, timeout=args.connect_timeout, **kwargs)
        await client.connect()
        try:
            services = list(client.services)
            return {
                "connected": bool(client.is_connected),
                "service_count": len(services),
                "services": [
                    {
                        "uuid": str(service.uuid).lower(),
                        "characteristics": [str(char.uuid).lower() for char in service.characteristics],
                    }
                    for service in services
                ],
            }
        finally:
            if client.is_connected:
                await client.disconnect()

    try:
        payload = await asyncio.wait_for(inner(), timeout=args.outer_timeout)
        result.update({"status": "PASS", **payload})
    except Exception as exc:  # noqa: BLE001
        result.update(
            {
                "status": "FAIL",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "error_repr": repr(exc),
                "traceback_tail": traceback.format_exc().splitlines()[-16:],
            }
        )
    result["duration_s"] = round(time.monotonic() - started, 3)
    result["ended_at"] = utc_now()
    return result


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import bleak

    artifact_dir = resolve_artifact_dir(args.artifact_dir)
    raw_serial = artifact_dir / "ble-connect-serial.log"
    port, ports = resolve_serial_port(args.serial_port)
    monitor = SerialMonitor(port, args.baud, raw_serial)
    required_services = load_required_services()
    operations: list[dict[str, Any]] = []

    started = utc_now()
    monitor.start()
    try:
        await asyncio.sleep(args.serial_lead_s)
        selected, candidates = await scan_target(args)
        operations.append(
            {
                "operation": "scan",
                "status": "PASS" if selected is not None else "FAIL",
                "candidates": candidates,
                "candidate_count": len(candidates),
            }
        )
        if selected is not None:
            if args.attempt in ("device", "both"):
                operations.append(await connect_attempt("device_default", selected, {}, args))
                if args.try_service_filter:
                    operations.append(
                        await connect_attempt(
                            "device_required_services",
                            selected,
                            {"services": required_services},
                            args,
                        )
                    )
            if args.attempt in ("address", "both"):
                operations.append(await connect_attempt("address_default", args.address, {}, args))
                if args.try_service_filter:
                    operations.append(
                        await connect_attempt(
                            "address_required_services",
                            args.address,
                            {"services": required_services},
                            args,
                        )
                    )
        await asyncio.sleep(args.serial_trail_s)
    finally:
        monitor.stop()

    passed = any(op.get("operation") != "scan" and op.get("status") == "PASS" for op in operations)
    return {
        "schema_version": 1,
        "tool": "tools/companion_ble_connect_with_serial.py",
        "status": "PASS" if passed else "FAIL",
        "started_at": started,
        "finished_at": utc_now(),
        "firmware_commit": git_commit(),
        "bleak_version": getattr(bleak, "__version__", "unknown"),
        "target": {"name": args.name, "address": args.address},
        "serial": {
            "port": port,
            "baud": args.baud,
            "raw_log": str(raw_serial),
            "line_count": len(monitor.lines),
            "lines": monitor.lines[-80:],
            "present_ports": ports,
        },
        "required_services": required_services,
        "operations": operations,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="companion")
    parser.add_argument("--address", default="00:80:E1:27:B8:EA")
    parser.add_argument("--serial-port", default="")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--scan-timeout", type=float, default=8.0)
    parser.add_argument("--connect-timeout", type=float, default=12.0)
    parser.add_argument("--outer-timeout", type=float, default=18.0)
    parser.add_argument("--serial-lead-s", type=float, default=0.5)
    parser.add_argument("--serial-trail-s", type=float, default=1.5)
    parser.add_argument("--attempt", choices=("device", "address", "both"), default="both")
    parser.add_argument("--try-service-filter", action="store_true")
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    args.serial_port = args.serial_port.strip()
    args.artifact_dir = resolve_artifact_dir(args.artifact_dir)
    result = asyncio.run(run(args))
    output = args.artifact_dir / "companion-ble-connect-with-serial.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    print(f"{result['status']}: Companion BLE connect diagnostic artifact={output}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
