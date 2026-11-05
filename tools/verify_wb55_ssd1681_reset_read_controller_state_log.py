#!/usr/bin/env python3
"""Fail-closed parser for the one-reset SSD1681 controller-state capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

START = "[epaper] reset_read_state start groups=3 writes=0 refresh_commands=0 hard_resets=1 busy_waits=1 reset_low_ms=100 reset_high_ms=100"
PREREQUISITE_RE = re.compile(
    r"\[epaper\] reset_read_state prerequisite hard_resets=1 busy_waits=1 "
    r"busy_initial=(?P<initial>[01]) busy_final=(?P<final>[01]) "
    r"ready=(?P<ready>[01]) ready_elapsed_ms=(?P<elapsed>\d+) timeout_ms=5000"
)
GROUP_RE = re.compile(
    r"\[epaper\] reset_read_state group=(?P<group>\d+) "
    r"chip_cmd=0x2F chip_len=(?P<chip_len>\d+) chip=(?P<chip>[0-9A-F]{2}) "
    r"display_cmd=0x2D display_len=(?P<display_len>\d+) "
    r"display=(?P<display>[0-9A-F]+) gpio_restore=(?P<restore>[01]) "
    r"sda=(?P<sda>[01]) sck=(?P<sck>[01]) cs=(?P<cs>[01])"
)
OK_RE = re.compile(
    r"\[epaper\] reset_read_state result=ok chip=(?P<chip>[0-9A-F]{2}) "
    r"vcom_otp=(?P<vcom_otp>[0-9A-F]{2}) vcom_reg=(?P<vcom_reg>[0-9A-F]{2}) "
    r"display_option=(?P<option>[0-9A-F]{10}) ping_pong=(?P<ping>[01]) "
    r"waveform_version=(?P<waveform>[0-9A-F]{8}) groups=3 writes=0 "
    r"refresh_commands=0 hard_resets=1 busy_waits=1"
)
FORBIDDEN_COMMANDS = (0x20, 0x22, 0x24, 0x26, 0x27, 0x32, 0x37, 0x41)


class GateError(ValueError):
    pass


def analyze(text: str) -> tuple[dict, bool]:
    failures: list[str] = []
    report: dict = {
        "schema_id": "companion.wb55.ssd1681.reset_read_controller_state.v1",
        "status": "NO_GO_RESET_READ_CONTROLLER_STATE",
        "claim_scope": "one hard reset, one bounded BUSY-ready wait, and three read-only 0x2F/0x2D groups; no refresh, panel write, waveform, temperature, visual, or production claim",
        "raw_groups": [],
        "failures": failures,
        "safety": {
            "hard_resets": 1,
            "busy_waits": 1,
            "panel_writes": 0,
            "refresh_commands": 0,
            "automatic_retries": 0,
        },
    }

    for command in FORBIDDEN_COMMANDS:
        if f"command=0x{command:02X}" in text or f"cmd=0x{command:02X}" in text:
            failures.append(f"forbidden command trace: 0x{command:02X}")
    if text.count(START) != 1:
        failures.append("missing or repeated exact start marker")

    prerequisites = list(PREREQUISITE_RE.finditer(text))
    if len(prerequisites) != 1:
        failures.append("missing or repeated reset/BUSY prerequisite marker")
        ready = False
    else:
        fields = prerequisites[0].groupdict()
        elapsed = int(fields["elapsed"])
        ready = fields["ready"] == "1"
        report["prerequisite"] = {
            "reset_low_ms": 100,
            "reset_high_ms": 100,
            "busy_initial": int(fields["initial"]),
            "busy_final": int(fields["final"]),
            "ready": ready,
            "ready_elapsed_ms": elapsed,
            "timeout_ms": 5000,
        }
        if not ready:
            failures.append("BUSY did not become ready")
        if fields["final"] != "0":
            failures.append("BUSY final level is not ready-low")
        if elapsed > 5000:
            failures.append("BUSY readiness exceeded the bounded timeout")

    matches = list(GROUP_RE.finditer(text))
    if len(matches) != 3:
        failures.append(f"expected exactly 3 groups after readiness, found {len(matches)}")
    chips: list[int] = []
    payloads: list[bytes] = []
    for expected_group, match in enumerate(matches, 1):
        fields = match.groupdict()
        group_failures: list[str] = []
        if int(fields["group"]) != expected_group:
            group_failures.append("group order")
        if int(fields["chip_len"]) != 1:
            group_failures.append("0x2F length")
        if int(fields["display_len"]) != 11 or len(fields["display"]) != 22:
            group_failures.append("0x2D length")
        if fields["restore"] != "1" or fields["sda"] != "0" or fields["sck"] != "0" or fields["cs"] != "1":
            group_failures.append("GPIO restore")
        if group_failures:
            failures.append(f"group {expected_group}: {', '.join(group_failures)}")
            continue
        chip = int(fields["chip"], 16)
        payload = bytes.fromhex(fields["display"])
        chips.append(chip)
        payloads.append(payload)
        report["raw_groups"].append({
            "group": expected_group,
            "chip_status_hex": f"{chip:02X}",
            "display_option_hex": payload.hex().upper(),
            "gpio_restore": True,
            "sda_output_low": True,
            "scl_low": True,
            "cs_high": True,
        })

    if len(chips) == 3 and len(set(chips)) != 1:
        failures.append("0x2F responses are inconsistent")
    if len(payloads) == 3 and len(set(payloads)) != 1:
        failures.append("0x2D responses are inconsistent")
    if len(chips) == 3:
        chip = chips[0]
        if chip & 0x03 != 0x01:
            failures.append("chip ID bits[1:0] are not 01")
        if chip & 0x04:
            failures.append("0x2F reports BUSY")
    else:
        chip = 0
    if len(payloads) == 3:
        payload = payloads[0]
        if payload == bytes(11):
            failures.append("0x2D response is all 00")
        if payload == bytes([0xFF]) * 11:
            failures.append("0x2D response is all FF")
        report["payload_sha256"] = hashlib.sha256(payload).hexdigest().upper()
        report["decoded"] = {
            "chip_status_hex": f"{chip:02X}",
            "chip_id_bits_1_0": chip & 0x03,
            "busy_bit_2": (chip >> 2) & 1,
            "vcom_otp_selection_hex": f"{payload[0]:02X}",
            "vcom_register_hex": f"{payload[1]:02X}",
            "display_option_0x37_b_through_f_hex": payload[2:7].hex().upper(),
            "f6_mode2_ram_ping_pong_enabled": bool(payload[6] & 0x40),
            "waveform_version_hex": payload[7:11].hex().upper(),
        }

    summaries = list(OK_RE.finditer(text))
    if not failures:
        if len(summaries) != 1:
            failures.append("missing or repeated successful firmware summary")
        else:
            summary = summaries[0].groupdict()
            payload = payloads[0]
            if int(summary["chip"], 16) != chips[0]:
                failures.append("summary chip differs from raw groups")
            if int(summary["vcom_otp"], 16) != payload[0] or int(summary["vcom_reg"], 16) != payload[1]:
                failures.append("summary VCOM differs from raw payload")
            if summary["option"] != payload[2:7].hex().upper():
                failures.append("summary display option differs from raw payload")
            if int(summary["ping"]) != int(bool(payload[6] & 0x40)):
                failures.append("summary ping-pong differs from raw payload")
            if summary["waveform"] != payload[7:11].hex().upper():
                failures.append("summary waveform version differs from raw payload")

    valid = not failures and ready
    if valid:
        report["status"] = "PASS_MACHINE_RESET_READ_CONTROLLER_STATE"
    return report, valid


def fixture(payload: bytes | None = None, chip: int = 0x01, ready: int = 1) -> str:
    payload = bytes.fromhex("1234010203044556575859") if payload is None else payload
    rows = [START,
            f"[epaper] reset_read_state prerequisite hard_resets=1 busy_waits=1 busy_initial=1 busy_final={0 if ready else 1} ready={ready} ready_elapsed_ms=12 timeout_ms=5000"]
    if ready:
        for group in range(1, 4):
            rows.append(
                f"[epaper] reset_read_state group={group} chip_cmd=0x2F chip_len=1 chip={chip:02X} "
                f"display_cmd=0x2D display_len=11 display={payload.hex().upper()} "
                "gpio_restore=1 sda=0 sck=0 cs=1"
            )
        rows.append(
            f"[epaper] reset_read_state result=ok chip={chip:02X} vcom_otp={payload[0]:02X} "
            f"vcom_reg={payload[1]:02X} display_option={payload[2:7].hex().upper()} "
            f"ping_pong={int(bool(payload[6] & 0x40))} waveform_version={payload[7:11].hex().upper()} "
            "groups=3 writes=0 refresh_commands=0 hard_resets=1 busy_waits=1"
        )
    return "\n".join(rows)


def self_test() -> None:
    report, valid = analyze(fixture())
    assert valid and report["status"] == "PASS_MACHINE_RESET_READ_CONTROLLER_STATE"
    cases = {
        "not_ready": fixture(ready=0),
        "bad_id": fixture(chip=0x02),
        "busy_status": fixture(chip=0x05),
        "all_zero": fixture(bytes(11)),
        "all_ff": fixture(bytes([0xFF]) * 11),
        "missing_group": fixture().replace("[epaper] reset_read_state group=3", "[epaper] ignored group=3", 1),
        "gpio": fixture().replace("gpio_restore=1", "gpio_restore=0", 1),
        "extra_reset": fixture() + "\n" + START,
        "timeout": fixture().replace("ready_elapsed_ms=12", "ready_elapsed_ms=5001", 1),
        "forbidden": fixture() + "\n[epaper] command=0x20",
    }
    for name, text in cases.items():
        _, valid = analyze(text)
        if valid:
            raise AssertionError(f"negative fixture unexpectedly passed: {name}")
    print("PASS: SSD1681 reset-read parser positive/negative self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.log is None or args.out is None:
        parser.error("--log and --out are required unless --self-test is used")
    text = args.log.read_text(encoding="utf-8", errors="replace")
    report, valid = analyze(text)
    report["source_log"] = str(args.log)
    report["source_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest().upper()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
