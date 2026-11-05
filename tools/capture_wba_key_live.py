"""Retain an actual WBA key observation on the host until the operator finishes.

Uses an already-loaded SRAM diagnostic. Keeps UART open, saves new key events
as they arrive, and observes KEY_STATUS every two seconds. Reuses an existing
ARM without clearing its events. A missing reply ends the capture; there is no
reconnect, reset, firmware installation, or operator countdown.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time

import serial
from serial.tools import list_ports

from capture_wba_peripheral_diag import DIAG, ROOT, SN, UID, values
from peripheral_diag_uart import send_line


class DiagnosticResponseTimeout(RuntimeError):
    pass


def now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner", default="01a11ba8-9629-7350-976b-fd50a1045a76")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    stop_file = out / "stop.request"
    report = {
        "result": "STARTING", "startedAtLocal": now(), "probeSerial": SN, "uid": UID,
        "physicalQualification": "UNCONFIRMED", "uartClosed": True,
        "peripheralCommandsIssued": 0, "resetIssued": False,
        "operatorDeadline": None, "stopRequestPath": str(stop_file),
        "events": [], "currentKeyState": "UNCONFIRMED",
        "leaseToken": out.name,
    }
    link = None
    pending = bytearray()
    seen_events: set[tuple[int, int, int]] = set()
    status_revision = 0
    raw_bytes = 0

    def save() -> None:
        temporary = out / "result.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(out / "result.json")

    def lease() -> None:
        text = (ROOT.parent / "docs/board_operations.md").read_text(encoding="utf-8-sig")
        section = text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]
        active = [line for line in section.splitlines() if "**占用中**" in line]
        if (len(active) != 1 or args.owner not in active[0]
                or "peripheral-ram-diag" not in active[0] or out.name not in active[0]):
            raise RuntimeError("Unique peripheral-ram-diag lease is absent or changed")

    def release_failed_capture() -> None:
        # A background capture can lose the target while waiting for the human.
        # Release its own exact stage after closing UART; never edit another one.
        board = ROOT.parent / "docs/board_operations.md"
        try:
            text = board.read_text(encoding="utf-8-sig")
            section = text.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]
            active = [line for line in section.splitlines() if "**占用中**" in line]
            if (len(active) != 1 or args.owner not in active[0]
                    or "peripheral-ram-diag" not in active[0] or out.name not in active[0]):
                report["leaseRelease"] = "OWN_STAGE_NOT_ACTIVE_NO_EDIT"
                return
            replacement = active[0].replace("**占用中**", "**已释放**", 1)
            replacement += ("；" + now() + " 持续按键采集已退出且UART实际关闭，无SWD/BLE句柄，"
                            "明确释放。当前板端采集状态未知，按键实物未判通过；原始证据 "
                            + out.relative_to(ROOT.parent).as_posix() + "/result.json。")
            if board.read_text(encoding="utf-8-sig") != text:
                report["leaseRelease"] = "RECORD_CHANGED_NO_EDIT"
                return
            board.write_text(text.replace(active[0], replacement, 1), encoding="utf-8-sig")
            report["leaseRelease"] = "FAILED_CAPTURE_HANDLES_CLOSED_STAGE_RELEASED"
        except Exception as error:
            report["leaseReleaseError"] = repr(error)

    with (out / "uart.log").open("wb") as raw_log, (out / "key-events.jsonl").open("w", encoding="utf-8") as journal:
        def observe(line: str) -> None:
            nonlocal status_revision
            if line.startswith("KEY_STATUS "):
                status_revision += 1
                report["lastKeyStatus"] = values(line)
                report["lastResponsiveAtLocal"] = now()
            elif line.startswith("KEY_EVENT "):
                event = values(line)
                identity = int(event["index"]), int(event["ms"]), int(event["pressed"])
                if identity[2] not in (0, 1):
                    raise ValueError("Invalid key event state")
                if identity not in seen_events:
                    if len(seen_events) >= 4096:
                        raise RuntimeError("Key event storage bound exceeded; preserve evidence")
                    seen_events.add(identity)
                    item = {"hostReceivedAtLocal": now(), **event}
                    report["events"].append(item)
                    journal.write(json.dumps(item, ensure_ascii=False) + "\n")
                    journal.flush()
                    os.fsync(journal.fileno())
                    raw_log.flush()
                    os.fsync(raw_log.fileno())
                    save()
                    print(line, flush=True)

        def read_lines() -> list[str]:
            nonlocal raw_bytes
            assert link is not None
            chunk = link.read(min(max(link.in_waiting, 1), 4096))
            raw_bytes += len(chunk)
            if raw_bytes > 128 * 1024 * 1024:
                raise RuntimeError("UART evidence bound exceeded")
            raw_log.write(chunk)
            raw_log.flush()
            pending.extend(chunk)
            if len(pending) > 8192 and b"\n" not in pending:
                raise RuntimeError("Diagnostic line exceeds its bound")
            lines = []
            while b"\n" in pending:
                line, _, remainder = pending.partition(b"\n")
                pending[:] = remainder
                decoded = line.decode("ascii", errors="replace").strip()
                observe(decoded)
                lines.append(decoded)
            return lines

        def command(name: str) -> dict[str, str]:
            assert link is not None
            lease()
            revision_before = status_revision
            send_line(link, name)
            report["peripheralCommandsIssued"] += 1
            report["lastCommand"] = name
            report["lastCommandIssuedAtLocal"] = now()
            save()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                for line in read_lines():
                    if line.startswith("END "):
                        end = values(line)
                        if end.get("test") != name:
                            continue
                        allowed = {
                            "KEY_ARM": {"ARMED_AWAITING_OPERATOR"},
                            "KEY_STATUS": {"AWAITING_OPERATOR", "THREE_PRESS_RELEASE_OBSERVED"},
                            "KEY_STOP": {"DISARMED"},
                        }
                        if end.get("result") not in allowed[name]:
                            raise RuntimeError("Unexpected key command result: " + line)
                        if name != "KEY_STOP" and status_revision == revision_before:
                            raise RuntimeError("Key command omitted its live status")
                        report["lastDeviceEnd"] = end
                        report["lastResponsiveAtLocal"] = now()
                        save()
                        return report.get("lastKeyStatus", {})
            raise DiagnosticResponseTimeout("Key status reply timed out; retained events do not imply a physical disconnect")

        try:
            lease()
            save()
            ports = [port.device for port in list_ports.comports() if port.serial_number == SN]
            if len(ports) != 1:
                raise RuntimeError("Fixed V3 UART mapping is not unique")
            link = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1,
                                 rtscts=False, dsrdtr=False, xonxoff=False)
            link.dtr = link.rts = False
            link.port = ports[0]
            link.open()
            report.update(uartClosed=False, port=ports[0])
            lease()
            send_line(link, "")
            send_line(link, "HELLO")
            hello = None
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and hello is None:
                for line in read_lines():
                    marker = "HELLO id=" + DIAG + " "
                    if marker not in line:
                        continue
                    candidate = values(line[line.index(marker):])
                    if (candidate.get("uid") != UID or candidate.get("device") != "492"
                            or candidate.get("flash_kib") != "512" or candidate.get("target_ok") != "1"):
                        raise RuntimeError("Unexpected diagnostic target identity")
                    hello = candidate
            if hello is None:
                raise RuntimeError("Matching SRAM diagnostic is unavailable; no key command sent")
            report["hello"] = hello
            status = command("KEY_STATUS")
            if status.get("armed") == "1":
                report["reusedExistingArm"] = True
            elif status.get("armed") == "0":
                report["reusedExistingArm"] = False
                status = command("KEY_ARM")
            else:
                raise RuntimeError("Unknown key armed state")
            if status.get("armed") != "1" or status.get("no_operator_deadline") != "1":
                raise RuntimeError("Persistent key observation did not arm")
            report["baselineKeyStatus"] = dict(status)
            report.update(result="KEY_LIVE_CAPTURE_ARMED_AWAITING_OPERATOR", armedAtLocal=now(),
                          currentKeyState="LAST_CONFIRMED_ARMED")
            save()
            (out / "armed.ok.json").write_text(json.dumps({
                "armedAtLocal": report["armedAtLocal"], "uid": UID,
                "operatorDeadline": None, "currentProcessMustStillBeRunning": True,
                "reusedExistingArm": report["reusedExistingArm"],
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("KEY_LIVE_CAPTURE_READY output=" + str(out), flush=True)
            next_poll = time.monotonic() + 2
            previous = status
            while not stop_file.exists():
                lease()
                read_lines()
                if time.monotonic() >= next_poll:
                    status = command("KEY_STATUS")
                    if (status.get("armed") != "1"
                            or int(status["elapsed_ms"]) < int(previous["elapsed_ms"])
                            or int(status["presses"]) < int(previous["presses"])
                            or int(status["releases"]) < int(previous["releases"])):
                        raise RuntimeError("Key observation reset or changed; preserve prior events")
                    previous = status
                    next_poll = time.monotonic() + 2
            command("KEY_STATUS")
            command("KEY_STOP")
            report.update(result="KEY_LIVE_CAPTURE_STOPPED_OWNER_ACTION_REVIEW_REQUIRED",
                          currentKeyState="DISARMED_DIAGNOSTIC_STILL_RUNNING")
        except KeyboardInterrupt:
            report.update(result="KEY_LIVE_CAPTURE_INTERRUPTED", currentKeyState="UNCONFIRMED")
        except DiagnosticResponseTimeout as error:
            report.update(result="KEY_LIVE_CAPTURE_FAILED", failureKind="RESPONSE_TIMEOUT",
                          error=repr(error), currentKeyState="LAST_OBSERVATION_PRESERVED_CURRENT_STATE_UNKNOWN")
        except Exception as error:
            report.update(result="KEY_LIVE_CAPTURE_FAILED", error=repr(error), currentKeyState="UNCONFIRMED")
        finally:
            if link is not None and link.is_open:
                link.close()
            report.update(uartClosed=True, uartBytes=raw_bytes, finishedAtLocal=now())
            raw_log.flush()
            os.fsync(raw_log.fileno())
            if report["result"] in ("KEY_LIVE_CAPTURE_FAILED", "KEY_LIVE_CAPTURE_INTERRUPTED"):
                release_failed_capture()
            save()
            print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    raise SystemExit(0 if report["result"] == "KEY_LIVE_CAPTURE_STOPPED_OWNER_ACTION_REVIEW_REQUIRED" else 1)


if __name__ == "__main__":
    main()
