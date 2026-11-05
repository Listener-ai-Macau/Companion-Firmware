"""Operate an already-loaded SRAM peripheral diagnostic and save raw evidence.

Does not install firmware or connect SWD/BLE. HELLO is an inert unknown command
to the product console; no peripheral command is sent before a matching SRAM
diagnostic UID is returned. A lease is required even when only using UART.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import time
import wave

import serial
from serial.tools import list_ports
from diagnose_wba_uart import parse_frames
from peripheral_diag_uart import send_line

ROOT = Path(__file__).resolve().parents[1]
SN = "004400403532510B31333430"
UID = "180010000d50335754363720"
DIAG = "COMP_PERIPH_RAM_V1"
COMMANDS = ("IO", "KEY", "KEY_ARM", "KEY_STATUS", "KEY_STOP", "IMU", "TOUCH50", "TOUCH100", "TOUCH25", "TOUCH10", "TOUCH50_RESET",
            "TOUCH100_STOP", "TOUCH50_STOP", "TOUCH25_STOP", "TOUCH10_STOP", "TOUCH_MATRIX", "TOUCH_MATRIX_RESET", "NOR",
            "NOR_RW_LAST_DEV_SECTOR", "EPD", "SPEAKER", "SPEAKER_SPEECH", "SPEAKER_SPEECH_G64", "SPEAKER_SPEECH_G128",
            "SPEAKER_SPEECH_G256", "SPEAKER_SPEECH_G512", "MIC", "IMU_SELF_TEST", "IMU_INTERRUPT_PATH", "TOUCH_RESET_PATH", "CLOCKS", "RESET")
ELECTRICAL_COMMANDS = ("TCA_RESET_PATH", "INTERNAL_REFERENCE", "RELATIVE_CLOCKS", "RTC_STOP_WAKE", "IMU_STOP_WAKE")
COMMANDS += ELECTRICAL_COMMANDS


def values(line: str) -> dict[str, str]:
    return dict(token.split("=", 1) for token in line.split()[1:] if "=" in token)


def analyze(raw: bytes, command: str, out: Path) -> dict:
    lines = raw.decode("ascii", errors="replace").splitlines()
    result = {"command": command, "physicalQualification": "UNCONFIRMED"}
    result["deviceEnd"] = [values(s) for s in lines if s.startswith("END ")]
    if command in ("IMU_SELF_TEST", "IMU_INTERRUPT_PATH", "TOUCH_RESET_PATH", "CLOCKS", *ELECTRICAL_COMMANDS):
        result["records"] = [values(s) for s in lines if s.startswith(("IMU_ST_", "IMU_MODE ", "IMU_IRQ_", "TOUCH_RESET_", "CLOCK_", "VREF_", "TCA_RESET_", "STOP_WAKE"))]
        result["qualificationNote"] = "Focused hardware observations; not mounting calibration, product gesture/display delivery, precision clock or power/current certification."
    elif command.startswith("KEY"):
        result["keyStatus"] = [values(s) for s in lines if s.startswith("KEY_STATUS ")]
        result["keyEvents"] = [values(s) for s in lines if s.startswith("KEY_EVENT ")]
        result["qualificationNote"] = "ARM establishes an observation window without an operator deadline; STATUS retains events until a new ARM. Confirm the operator actually pressed and released before interpreting counts."
    elif command == "MIC":
        blocks: dict[tuple[int, int, int], bytes] = {}
        for s in lines:
            if not s.startswith("PCM "):
                continue
            v = values(s)
            key = int(v["channel"]), int(v["frame"]), int(v["sample"])
            data = bytes.fromhex(v["hex"])
            if key[0] not in (0, 1) or key[2] not in (0, 32, 64, 96, 128) or len(data) != 64 or key in blocks:
                raise ValueError("Invalid or duplicate PCM frame segment")
            blocks[key] = data
        expected = {(c, f, s) for c in range(2) for f in range(7) for s in range(0, 160, 32)}
        result["pcmComplete"] = set(blocks) == expected
        if result["pcmComplete"]:
            channels = [b"".join(blocks[(c, f, s)] for f in range(7) for s in range(0, 160, 32)) for c in range(2)]
            decoded = [struct.unpack("<1120h", b) for b in channels]
            channel_stats = []
            for c, pcm in enumerate(decoded):
                mean = sum(pcm) / len(pcm)
                rms = math.sqrt(sum((x - mean) ** 2 for x in pcm) / len(pcm))
                path = out / f"microphone-{c}.wav"
                with wave.open(str(path), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(channels[c])
                channel_stats.append({"channel": c, "samples": len(pcm), "durationMs": 70,
                                      "rmsWithoutDc": rms, "peak": max(abs(x) for x in pcm),
                                      "clippedSamples": sum(x in (-32768, 32767) for x in pcm),
                                      "sha256": hashlib.sha256(channels[c]).hexdigest(), "wav": path.name})
            result["microphones"] = channel_stats
            result["channelsByteIdentical"] = channels[0] == channels[1]
            result["qualificationNote"] = "Compare separate quiet and real acoustic stimuli; noise or DMA completion alone cannot qualify either microphone. A 70ms diagnostic is not a product recording or quality gate."
    elif command == "IMU":
        samples = [values(s) for s in lines if s.startswith("IMU ms=")]
        axes = {axis: [int(s[axis]) for s in samples] for axis in ("ax", "ay", "az", "gx", "gy", "gz")}
        result["sampleCount"] = len(samples)
        result["axisRanges"] = {a: {"min": min(v), "max": max(v)} for a, v in axes.items() if v}
        # Diagnostic observations only. A single outlier is not a six-face pass.
        faces: dict[str, list[int]] = {}
        for s in samples:
            acceleration = [int(s[k]) for k in ("ax", "ay", "az")]
            norm = math.sqrt(sum(a * a for a in acceleration))
            major = max(range(3), key=lambda k: abs(acceleration[k]))
            stationary = max(abs(int(s[k])) for k in ("gx", "gy", "gz")) < 8000
            if 850 <= norm <= 1150 and stationary and all(abs(a) < 300 for k, a in enumerate(acceleration) if k != major):
                face = "xyz"[major] + ("+" if acceleration[major] > 0 else "-")
                faces.setdefault(face, []).append(int(s["ms"]))
        holds = {}
        for face, stamps in faces.items():
            longest = current = 0
            for prev, stamp in zip(stamps, stamps[1:]):
                current = current + stamp - prev if 0 < stamp - prev < 80 else 0
                longest = max(longest, current)
            holds[face] = longest
        result["gravityFaceLongestHoldMs"] = holds
        result["sixGravityFacesObserved"] = len(holds) == 6 and all(n >= 500 for n in holds.values())
        result["gyroMotionObservedEachAxis"] = all(any(abs(x) >= 20000 for x in axes[k]) for k in ("gx", "gy", "gz"))
        result["qualificationNote"] = "Gravity holds and gyro movement are diagnostic coverage, not calibrated accuracy or MEMS self-test. Inspect timing, IO errors, and all physical axes before qualification."
    elif command.startswith("SPEAKER"):
        result["speakerRecords"] = [values(s) for s in lines if s.startswith("SPEAKER ")]
        result["qualificationNote"] = "DMA completion and MCU GPIO edges require actual hearing feedback; GPIO sampling is not oscilloscope timing or electrical level qualification."
    elif command.startswith("TOUCH"):
        result["busMatrix"] = [values(s) for s in lines if s.startswith("TOUCH_MATRIX ")]
        result["ioErrors"] = [values(s) for s in lines if s.startswith("TOUCH_IO ")]
        samples = [values(s) for s in lines if s.startswith("TOUCH ms=")]
        contact = [s for s in samples if int(s["count"]) > 0]
        result["reportedContacts"] = len(contact)
        if contact:
            result["coordinateRange"] = {a: [min(int(s[a]) for s in contact), max(int(s[a]) for s in contact)] for a in ("x", "y")}
        result["releaseObserved"] = any(int(s["count"]) == 0 for s in samples)
        result["qualificationNote"] = "Compare four corners and centre with known physical positions; identity/ACK/one touch does not qualify coordinate mapping or interrupt wiring."
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", choices=COMMANDS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner", default="01a11ba8-9629-7350-976b-fd50a1045a76")
    parser.add_argument("--lead-in-seconds", type=int, default=15)
    args = parser.parse_args()
    if not 0 <= args.lead_in_seconds <= 30:
        parser.error("Lead-in must be between 0 and 30 seconds")
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    report = {"result": "STARTING", "startedAtLocal": datetime.now().isoformat(), "command": args.command,
              "probeSerial": SN, "uid": UID, "uartClosed": True, "peripheralCommandsIssued": 0,
              "diagnosticLoadedByThisTool": False, "physicalQualification": "UNCONFIRMED"}
    raw = bytearray(); link = None

    def lease() -> None:
        s = (ROOT.parent / "docs/board_operations.md").read_text(encoding="utf-8-sig")
        section = s.split("## 当前占用", 1)[1].split("## 交接方式", 1)[0]
        active = [line for line in section.splitlines() if "**占用中**" in line]
        if len(active) != 1 or args.owner not in active[0] or "peripheral-ram-diag" not in active[0]:
            raise RuntimeError("Unique peripheral-ram-diag lease is absent or changed")
        if args.command == "NOR_RW_LAST_DEV_SECTOR" and "ota-idle-confirmed" not in active[0]:
            raise RuntimeError("Scratch write requires a live, independent confirmation that no OTA/rollback reservation is active")

    def save() -> None:
        (out / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read_line() -> str:
        assert link is not None
        line = link.readline(512)
        raw.extend(line)
        (out / "uart.log").write_bytes(raw)
        if len(raw) > 2 * 1024 * 1024:
            raise RuntimeError("Diagnostic capture exceeded its bound")
        return line.decode("ascii", errors="replace").strip()

    try:
        lease(); save()
        ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
        if len(ports) != 1:
            raise RuntimeError("Fixed V3 UART mapping is not unique")
        link = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1,
                             rtscts=False, dsrdtr=False, xonxoff=False)
        link.dtr = link.rts = False; link.port = ports[0]
        with link:
            report["uartClosed"] = False
            lease(); send_line(link, ""); send_line(link, "HELLO")
            until = time.monotonic() + 3
            identified = False
            while time.monotonic() < until:
                line = read_line()
                if line.startswith("HELLO "):
                    v = values(line)
                    if (v.get("id") != DIAG or v.get("uid") != UID or v.get("device") != "492"
                            or v.get("flash_kib") != "512" or v.get("target_ok") != "1"):
                        raise RuntimeError("Unexpected diagnostic or target identity")
                    report["hello"] = v; identified = True; break
            if not identified:
                raise RuntimeError("Matching SRAM diagnostic is not running; no peripheral command sent")
            print(f"DIAGNOSTIC_READY command={args.command} lead_in_seconds={args.lead_in_seconds}", flush=True)
            deadline = time.monotonic() + args.lead_in_seconds
            while time.monotonic() < deadline:
                lease(); time.sleep(min(.25, max(0, deadline - time.monotonic())))
            lease()
            report["commandIssuedAtLocal"] = datetime.now().isoformat()
            send_line(link, args.command)
            if args.command == "RESET":
                report["productResetCommandsIssued"] = 1
            else:
                report["peripheralCommandsIssued"] = 1
            save()
            until = time.monotonic() + (8 if args.command == "RESET" else 65)
            expected = (args.command if args.command in ("IMU_SELF_TEST", "IMU_INTERRUPT_PATH", "TOUCH_RESET_PATH", "CLOCKS", *ELECTRICAL_COMMANDS) else
                        "TOUCH" if args.command.startswith("TOUCH") else
                        "SPEAKER" if args.command.startswith("SPEAKER") else
                        "NOR_RW" if args.command.startswith("NOR_RW") else args.command)
            ended = False
            while time.monotonic() < until:
                line = read_line()
                if args.command == "RESET":
                    frames, _ = parse_frames(bytes(raw))
                    if frames:
                        restored = frames[-1]["sections"]
                        if restored["ID"]["uid"] != UID or restored["ID"]["ui"] != 67:
                            raise RuntimeError("Unexpected product identity after reset")
                        report["productRestoredSnapshot"] = frames[-1]
                        ended = True; break
                if line.startswith("END ") and values(line).get("test") == expected:
                    report["deviceEnd"] = values(line); ended = True; break
            if not ended:
                raise RuntimeError("Command did not report completion before the capture limit")
            if args.command == "RESET":
                report["result"] = "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED"
                return
            report["analysis"] = analyze(bytes(raw), args.command, out)
            accepted = {
                "IO": {"REGISTERS_READ_PHYSICAL_IO_PENDING"},
                "KEY": {"PRESS_RELEASE_OBSERVED"},
                "KEY_ARM": {"ARMED_AWAITING_OPERATOR"},
                "KEY_STATUS": {"THREE_PRESS_RELEASE_OBSERVED", "AWAITING_OPERATOR"},
                "KEY_STOP": {"DISARMED"},
                "IMU": {"DATA_CAPTURED_STIMULUS_REVIEW_REQUIRED"},
                "TOUCH": {"CONTACTS_CAPTURED_COVERAGE_REVIEW_REQUIRED", "BUS_MATRIX_CAPTURED"},
                "NOR": {"READS_CAPTURED_WRITE_UNTESTED"},
                "NOR_RW": {"TWO_PATTERNS_VERIFIED_RESTORED"},
                "EPD": {"TWO_ACTIVATIONS_COMPLETED_VISUAL_REVIEW_REQUIRED"},
                "SPEAKER": {"DMA_COMPLETED_HEARING_UNCONFIRMED"},
                "MIC": {"TWO_CHANNEL_PCM_EXPORTED_STIMULUS_REVIEW_REQUIRED"},
                "IMU_SELF_TEST": {"SIX_AXES_SELF_TEST_AND_MODES_PASSED"},
                "IMU_INTERRUPT_PATH": {"IMU_P3_EXPANDER_PC13_INTERRUPT_PATH_PASSED"},
                "TOUCH_RESET_PATH": {"RESET_CONTROL_REACHED_TOUCH_AND_RECOVERED"},
                "CLOCKS": {"LSE_RTC_BINARY_ADVANCE_OBSERVED"},
                "TCA_RESET_PATH": {"HARDWARE_RESET_DEFAULTS_AND_RESTORE_PASSED"},
                "INTERNAL_REFERENCE": {"INTERNAL_REFERENCE_OBSERVED_EXTERNAL_ADC_UNTESTED"},
                "RELATIVE_CLOCKS": {"RELATIVE_COUNTS_CAPTURED_ABSOLUTE_PRECISION_UNTESTED"},
                "RTC_STOP_WAKE": {"STOP1_SOURCE_AND_CLOCK_RECOVERY_OBSERVED_CURRENT_UNMEASURED"},
                "IMU_STOP_WAKE": {"STOP1_SOURCE_AND_CLOCK_RECOVERY_OBSERVED_CURRENT_UNMEASURED"},
            }
            if report["deviceEnd"].get("result") not in accepted[expected]:
                report["result"] = "DEVICE_DIAGNOSTIC_INCOMPLETE_OR_FAILED"
            elif args.command == "MIC" and not report["analysis"].get("pcmComplete"):
                report["result"] = "DIAGNOSTIC_PCM_DATA_INCOMPLETE"
            else:
                report["result"] = "DIAGNOSTIC_RESPONSE_CAPTURED_PHYSICAL_QUALIFICATION_PENDING"
    except Exception as e:
        report.update(result="DIAGNOSTIC_CAPTURE_FAILED", error=repr(e))
    finally:
        if link is not None and link.is_open:
            link.close()
        report.update(uartClosed=True, uartBytes=len(raw), finishedAtLocal=datetime.now().isoformat())
        (out / "uart.log").write_bytes(raw); save()
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    raise SystemExit(0 if report["result"] in (
        "DIAGNOSTIC_RESPONSE_CAPTURED_PHYSICAL_QUALIFICATION_PENDING",
        "PRODUCT_UART_IDENTITY_RESTORED_PERIPHERAL_QUALIFICATION_UNCHANGED") else 1)


if __name__ == "__main__":
    main()
