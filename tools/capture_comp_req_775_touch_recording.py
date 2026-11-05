#!/usr/bin/env python3
"""Capture a real COMP-REQ-775 touch recording with event-driven prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
from typing import Any

try:
    from verify_companion_button_input import (
        ButtonInputError,
        SerialMonitor,
        resolve_serial_port,
        wait_for_button_with_popup,
    )
except ModuleNotFoundError:  # imported as tools.* by unit tests
    from tools.verify_companion_button_input import (
        ButtonInputError,
        SerialMonitor,
        resolve_serial_port,
        wait_for_button_with_popup,
    )


sys.dont_write_bytecode = True
START_PATTERN = re.compile(
    r"\[record\]\s+touch_double_tap\s+action=start\s+source=2\s+"
    r"result=0\s+state=recording\b")
STOP_PATTERN = re.compile(
    r"\[record\]\s+touch_double_tap\s+action=stop\s+source=2\s+"
    r"stop_result=0\b")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def prompt_args(args: argparse.Namespace, title: str, message: str) -> argparse.Namespace:
    return argparse.Namespace(
        button="TOUCH",
        button_alias="FT6336 double tap",
        pin="I2C3",
        press_count=2,
        timeout=args.action_timeout,
        no_gui=args.no_gui,
        prompt_title=title,
        prompt_message=message,
    )


def wait_for_event(
    monitor: SerialMonitor,
    args: argparse.Namespace,
    index: int,
    pattern: re.Pattern[str],
    title: str,
    message: str,
) -> dict[str, Any]:
    result = wait_for_button_with_popup(
        monitor, prompt_args(args, title, message), index, pattern)
    return {
        "event_index": index,
        "status": "PASS",
        "detected_after_s": result["detected_after_s"],
        "line": result["line"],
    }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_log = out_dir / "touch-recording-serial.log"
    receipt_path = out_dir / "touch-recording-capture.json"
    port, present_ports = resolve_serial_port(args.port)
    monitor = SerialMonitor(port, args.baud, raw_log)
    operations: list[dict[str, Any]] = []
    started = time.monotonic()
    status = "FAIL"
    error = ""
    try:
        monitor.start()
        operations.append({
            "operation": "serial_open",
            "status": "PASS",
            "port": port,
            "baud": args.baud,
            "present_ports": present_ports,
        })
        time.sleep(1.0)
        operations.append(wait_for_event(
            monitor,
            args,
            1,
            START_PATTERN,
            "COMP-REQ-775：双击开始录音",
            "串口已经打开，之后不会复位。\n\n"
            "如果屏幕在睡眠：先单击唤醒，等普通脸稳定后再操作。\n"
            "现在在屏幕非菜单区域双击一次。\n\n"
            "只有固件实际进入 recording 后窗口才会自动关闭；"
            "请不要点关闭，也不要按 RESET。",
        ))
        dwell_started = time.monotonic()
        time.sleep(args.record_seconds)
        operations.append({
            "operation": "recording_dwell",
            "status": "PASS",
            "seconds": round(time.monotonic() - dwell_started, 3),
        })
        operations.append(wait_for_event(
            monitor,
            args,
            2,
            STOP_PATTERN,
            "COMP-REQ-775：双击停止录音",
            f"已保持真实 recording 超过 {args.record_seconds:.0f} 秒。\n\n"
            "现在在屏幕非菜单区域再双击一次停止。\n\n"
            "只有固件实际 stop 成功后窗口才会自动关闭；"
            "请不要点关闭，也不要按 RESET。",
        ))
        time.sleep(args.trailing_seconds)
        status = "PASS"
    except (ButtonInputError, Exception) as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        monitor.stop()

    raw_text = raw_log.read_text(encoding="utf-8", errors="replace")
    start_lines = [line for line in raw_text.splitlines()
                   if START_PATTERN.search(line)]
    stop_lines = [line for line in raw_text.splitlines()
                  if STOP_PATTERN.search(line)]
    result = {
        "schema": "companion.comp_req_775.touch_recording_capture.v1",
        "status": status,
        "error": error or None,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "required_record_seconds": args.record_seconds,
        "trailing_seconds": args.trailing_seconds,
        "port": port,
        "baud": args.baud,
        "raw_log": str(raw_log),
        "raw_log_sha256": sha256(raw_log),
        "real_start_count": len(start_lines),
        "real_stop_count": len(stop_lines),
        "operations": operations,
    }
    receipt_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="", help="ST-LINK VCP, auto if empty")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--record-seconds", type=float, default=15.0)
    parser.add_argument("--trailing-seconds", type=float, default=20.0)
    parser.add_argument("--action-timeout", type=float, default=180.0)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--no-gui", action="store_true")
    args = parser.parse_args()
    if args.record_seconds < 10.0:
        parser.error("--record-seconds must be at least 10")
    result = capture(args)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
