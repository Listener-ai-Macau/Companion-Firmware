#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify NUCLEO button input by auto-closing prompts on serial button logs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import queue
import re
import sys
import threading
import time
from typing import Any

import serial
from serial.tools import list_ports


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class ButtonInputError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def resolve_artifact_dir(path: pathlib.Path | None) -> pathlib.Path:
    if path is not None:
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = REPO_ROOT / ".cache" / "validation" / f"companion-button-input-{stamp}"
    output.mkdir(parents=True, exist_ok=True)
    return output


def resolve_serial_port(requested: str | None) -> tuple[str, list[dict[str, Any]]]:
    ports = []
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
        raise ButtonInputError(f"requested serial port is not present: {requested}; present={ports}")

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
        raise ButtonInputError(f"no ST-LINK/STM32 serial port found; present={ports}")
    raise ButtonInputError(f"multiple ST-LINK/STM32 serial ports found; pass --port. candidates={candidates}")


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

    def next_line(self, timeout: float) -> str | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


def message_beep() -> None:
    try:
        import winsound

        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass


def wait_for_button_with_popup(
    monitor: SerialMonitor,
    args: argparse.Namespace,
    press_index: int,
    pattern: re.Pattern[str],
) -> dict[str, Any]:
    started = time.monotonic()
    title = getattr(args, "prompt_title", "") or f"Companion {args.button} 按钮检测 {press_index}/{args.press_count}"
    custom_message = getattr(args, "prompt_message", "")
    if custom_message:
        message = custom_message
    else:
        target_text = (
            "任意 SW1/SW2/SW3 用户按钮"
            if args.button.upper() == "ANY"
            else f"{args.button}/{args.button_alias} 用户按钮（{args.pin}）"
        )
        message = (
            f"现在按住 NUCLEO-WB55RG 开发板上的 {target_text}，一直按到这个窗口自动关闭。\n\n"
            "检测到固件串口日志后，这个窗口会自动关闭并进入下一步。\n"
            "不要按 B4/RESET，也不要点关闭；如果按错按钮，脚本会继续等目标按钮。"
        )

    if args.no_gui:
        print(title)
        print(message)
        while time.monotonic() - started < args.timeout:
            line = monitor.next_line(0.1)
            if line is None:
                continue
            print(line)
            match = pattern.search(line)
            if match:
                return {
                    "press_index": press_index,
                    "status": "PASS",
                    "detected_after_s": round(time.monotonic() - started, 3),
                    "detected_button": match.group("button") if "button" in match.groupdict() else args.button,
                    "line": line,
                }
        raise ButtonInputError(f"timed out waiting for {args.button} press {press_index}")

    import tkinter as tk
    from tkinter import ttk

    result: dict[str, Any] = {}
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0, sticky="nsew")
    label = ttk.Label(frame, text=message, justify="left", wraplength=520)
    label.grid(row=0, column=0, sticky="w")
    status_var = tk.StringVar(value=f"等待 {args.button} 按下，剩余 {int(args.timeout)} 秒")
    status = ttk.Label(frame, textvariable=status_var)
    status.grid(row=1, column=0, sticky="w", pady=(16, 0))
    progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate", length=520)
    progress.grid(row=2, column=0, pady=(12, 0))
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 3
    root.geometry(f"+{x}+{y}")
    message_beep()

    def poll() -> None:
        elapsed = time.monotonic() - started
        remaining = max(0.0, float(args.timeout) - elapsed)
        progress["value"] = min(100.0, (elapsed / float(args.timeout)) * 100.0)
        status_var.set(f"等待 {args.button} 按下，剩余 {remaining:.1f} 秒")
        while True:
            line = monitor.next_line(0.0)
            if line is None:
                break
            if line.startswith("__SERIAL_ERROR__"):
                result["error"] = line
                root.destroy()
                return
            match = pattern.search(line)
            if match:
                result.update(
                    {
                        "press_index": press_index,
                        "status": "PASS",
                        "detected_after_s": round(time.monotonic() - started, 3),
                        "detected_button": match.group("button") if "button" in match.groupdict() else args.button,
                        "line": line,
                    }
                )
                status_var.set(f"已检测到按钮: {line}")
                root.after(250, root.destroy)
                return
        if elapsed >= float(args.timeout):
            result["error"] = f"timed out waiting for {args.button} press {press_index}"
            root.destroy()
            return
        root.after(50, poll)

    root.after(50, poll)
    root.mainloop()
    if "error" in result:
        raise ButtonInputError(str(result["error"]))
    if not result:
        raise ButtonInputError(f"button popup closed before detecting {args.button}")
    return result


def drain_until_release(monitor: SerialMonitor, button: str, timeout: float = 5.0) -> dict[str, Any]:
    started = time.monotonic()
    release = re.compile(
        rf"\[button-raw\]\s+{re.escape(button)}\s+active_low=0\b",
        re.IGNORECASE,
    )
    drained: list[str] = []
    while time.monotonic() - started < timeout:
        line = monitor.next_line(0.15)
        if line is None:
            if drained:
                break
            continue
        drained.append(line)
        if release.search(line):
            return {
                "status": "PASS",
                "released_after_s": round(time.monotonic() - started, 3),
                "line": line,
                "drained_count": len(drained),
            }
    return {
        "status": "UNKNOWN",
        "released_after_s": round(time.monotonic() - started, 3),
        "line": "",
        "drained_count": len(drained),
    }


def show_completion_popup(args: argparse.Namespace, detections: list[dict[str, Any]]) -> None:
    if args.no_gui:
        return
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title(f"Companion {args.button} 检测通过")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        lines = "\n".join(f"{d['press_index']}. {d['line']}" for d in detections)
        text = f"已连续检测到 {len(detections)} 次 {args.button} 按下。\n\n{lines}\n\n窗口 2 秒后自动关闭。"
        frame = ttk.Frame(root, padding=20)
        frame.grid(row=0, column=0)
        ttk.Label(frame, text=text, justify="left", wraplength=560).grid(row=0, column=0)
        root.update_idletasks()
        root.geometry(
            f"+{(root.winfo_screenwidth() - root.winfo_width()) // 2}"
            f"+{(root.winfo_screenheight() - root.winfo_height()) // 3}"
        )
        message_beep()
        root.after(2000, root.destroy)
        root.mainloop()
    except Exception:
        pass


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    artifact_dir = resolve_artifact_dir(args.artifact_dir)
    raw_log = artifact_dir / "button-input-serial.log"
    port, present_ports = resolve_serial_port(args.port)
    monitor = SerialMonitor(port, args.baud, raw_log)
    if args.button.upper() == "ANY":
        target = re.compile(
            r"\[(?:button|button-raw)\]\s+(?P<button>SW[123])\s+"
            r"(?:pressed\b|active_low=1\b)",
            re.IGNORECASE,
        )
    else:
        target = re.compile(
            rf"\[(?:button|button-raw)\]\s+(?P<button>{re.escape(args.button)})\s+"
            r"(?:pressed\b|active_low=1\b)",
            re.IGNORECASE,
        )
    detections: list[dict[str, Any]] = []
    monitor.start()
    try:
        for index in range(1, int(args.press_count) + 1):
            detection = wait_for_button_with_popup(monitor, args, index, target)
            detected_button = str(detection.get("detected_button") or args.button)
            if detected_button.upper() != "ANY":
                detection["release"] = drain_until_release(monitor, detected_button)
            detections.append(detection)
            if index < int(args.press_count):
                time.sleep(float(args.between_prompts_s))
        show_completion_popup(args, detections)
    finally:
        monitor.stop()

    return {
        "schema_version": 1,
        "status": "PASS",
        "started_at": started,
        "finished_at": utc_now(),
        "mode": "companion_nucleo_button_input_serial_popup",
        "button": args.button,
        "button_alias": args.button_alias,
        "pin": args.pin,
        "port": port,
        "baud": args.baud,
        "press_count": args.press_count,
        "detections": detections,
        "raw_log": str(raw_log),
        "present_ports": present_ports,
    }


def write_artifact(result: dict[str, Any], artifact_dir: pathlib.Path | None) -> pathlib.Path:
    output = resolve_artifact_dir(artifact_dir)
    path = output / "companion-button-input.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="", help="ST-LINK VCP port, e.g. COM13")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--button", default="SW3")
    parser.add_argument("--button-alias", default="B3")
    parser.add_argument("--pin", default="PD1")
    parser.add_argument("--press-count", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--between-prompts-s", type=float, default=0.4)
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=None)
    parser.add_argument("--no-gui", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    args.port = args.port.strip()
    args.artifact_dir = resolve_artifact_dir(args.artifact_dir)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "finished_at": utc_now(),
            "mode": "companion_nucleo_button_input_serial_popup",
            "button": args.button,
            "button_alias": args.button_alias,
            "pin": args.pin,
            "error": str(exc),
        }
        path = write_artifact(result, args.artifact_dir)
        print(f"FAIL: Companion {args.button} button input check failed; artifact={path}")
        print(str(exc))
        return 1

    path = write_artifact(result, args.artifact_dir)
    print(f"PASS: Companion {args.button} button input check passed; artifact={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
