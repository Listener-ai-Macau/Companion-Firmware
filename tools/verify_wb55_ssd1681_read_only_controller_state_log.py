#!/usr/bin/env python3
"""Fail-closed parser for the SSD1681 read-only controller-state capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

GROUP_RE = re.compile(
    r"\[epaper\] readonly_state group=(?P<group>\d+) "
    r"chip_cmd=0x2F chip_len=(?P<chip_len>\d+) chip=(?P<chip>[0-9A-F]{2}) "
    r"display_cmd=0x2D display_len=(?P<display_len>\d+) "
    r"display=(?P<display>[0-9A-F]+) gpio_restore=(?P<restore>[01]) "
    r"sda=(?P<sda>[01]) sck=(?P<sck>[01]) cs=(?P<cs>[01])"
)
OK_RE = re.compile(
    r"\[epaper\] readonly_state result=ok chip=(?P<chip>[0-9A-F]{2}) "
    r"vcom_otp=(?P<vcom_otp>[0-9A-F]{2}) vcom_reg=(?P<vcom_reg>[0-9A-F]{2}) "
    r"display_option=(?P<option>[0-9A-F]{10}) ping_pong=(?P<ping>[01]) "
    r"waveform_version=(?P<waveform>[0-9A-F]{8}) groups=3 writes=0 "
    r"refresh_commands=0 hard_resets=0"
)
FORBIDDEN_COMMANDS = (0x20, 0x22, 0x24, 0x26, 0x30, 0x31, 0x32, 0x36, 0x37, 0x39)


class GateError(ValueError):
    pass


def parse_capture(text: str) -> dict:
    for command in FORBIDDEN_COMMANDS:
        token = f"command=0x{command:02X}"
        if token in text or f"cmd=0x{command:02X}" in text:
            raise GateError(f"forbidden command trace: 0x{command:02X}")
    if text.count("[epaper] readonly_state start groups=3 writes=0 refresh_commands=0 hard_resets=0") != 1:
        raise GateError("missing or repeated start marker")

    matches = list(GROUP_RE.finditer(text))
    if len(matches) != 3:
        raise GateError(f"expected exactly 3 groups, found {len(matches)}")
    chips: list[int] = []
    payloads: list[bytes] = []
    raw_groups: list[dict] = []
    for expected_group, match in enumerate(matches, 1):
        fields = match.groupdict()
        if int(fields["group"]) != expected_group:
            raise GateError("group order is not exactly 1,2,3")
        if int(fields["chip_len"]) != 1:
            raise GateError("0x2F response length is not one byte")
        if int(fields["display_len"]) != 11:
            raise GateError("0x2D declared response length is not eleven bytes")
        display_hex = fields["display"]
        if len(display_hex) != 22:
            raise GateError("0x2D raw payload length is not eleven bytes")
        if fields["restore"] != "1" or fields["sda"] != "0" or fields["sck"] != "0" or fields["cs"] != "1":
            raise GateError("GPIO restore contract failed")
        chip = int(fields["chip"], 16)
        payload = bytes.fromhex(display_hex)
        chips.append(chip)
        payloads.append(payload)
        raw_groups.append({
            "group": expected_group,
            "chip_status_hex": f"{chip:02X}",
            "display_option_hex": payload.hex().upper(),
            "gpio_restore": True,
            "sda_output_low": True,
            "scl_low": True,
            "cs_high": True,
        })

    if len(set(chips)) != 1:
        raise GateError("0x2F responses are inconsistent")
    if len(set(payloads)) != 1:
        raise GateError("0x2D responses are inconsistent")
    chip = chips[0]
    payload = payloads[0]
    if chip & 0x03 != 0x01:
        raise GateError("chip ID bits[1:0] are not 01")
    if chip & 0x04:
        raise GateError("controller reports BUSY")
    if payload == bytes(11):
        raise GateError("0x2D response is all 00")
    if payload == bytes([0xFF]) * 11:
        raise GateError("0x2D response is all FF")

    summaries = list(OK_RE.finditer(text))
    if len(summaries) != 1:
        raise GateError("missing or repeated successful firmware summary")
    summary = summaries[0].groupdict()
    if int(summary["chip"], 16) != chip:
        raise GateError("summary chip status differs from raw groups")
    if int(summary["vcom_otp"], 16) != payload[0] or int(summary["vcom_reg"], 16) != payload[1]:
        raise GateError("summary VCOM differs from raw payload")
    if summary["option"] != payload[2:7].hex().upper():
        raise GateError("summary display option differs from raw payload")
    if int(summary["ping"]) != int(bool(payload[6] & 0x40)):
        raise GateError("summary ping-pong bit differs from raw payload")
    if summary["waveform"] != payload[7:11].hex().upper():
        raise GateError("summary waveform version differs from raw payload")

    return {
        "schema_id": "companion.wb55.ssd1681.read_only_controller_state.v1",
        "status": "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE",
        "claim_scope": "three stable read-only 0x2F/0x2D groups only; no refresh, write, waveform, temperature, visual, or production claim",
        "commands": {"chip_status": "0x2F", "display_option": "0x2D", "groups": 3},
        "raw_groups": raw_groups,
        "payload_sha256": hashlib.sha256(payload).hexdigest().upper(),
        "decoded": {
            "chip_status_hex": f"{chip:02X}",
            "chip_id_bits_1_0": chip & 0x03,
            "busy_bit_2": (chip >> 2) & 1,
            "vcom_otp_selection_hex": f"{payload[0]:02X}",
            "vcom_register_hex": f"{payload[1]:02X}",
            "display_option_0x37_b_through_f_hex": payload[2:7].hex().upper(),
            "f6_mode2_ram_ping_pong_enabled": bool(payload[6] & 0x40),
            "waveform_version_hex": payload[7:11].hex().upper(),
        },
        "safety": {
            "writes": 0,
            "refresh_commands": 0,
            "hard_resets": 0,
            "high_voltage_activation": False,
            "normal_panel_init_entered": False,
            "automatic_retry": False,
        },
    }


def valid_fixture(payload: bytes | None = None, chip: int = 0x01) -> str:
    payload = bytes.fromhex("1234010203044556575859") if payload is None else payload
    rows = ["[epaper] readonly_state start groups=3 writes=0 refresh_commands=0 hard_resets=0"]
    for group in range(1, 4):
        rows.append(
            f"[epaper] readonly_state group={group} chip_cmd=0x2F chip_len=1 chip={chip:02X} "
            f"display_cmd=0x2D display_len=11 display={payload.hex().upper()} "
            "gpio_restore=1 sda=0 sck=0 cs=1"
        )
    rows.append(
        f"[epaper] readonly_state result=ok chip={chip:02X} vcom_otp={payload[0]:02X} "
        f"vcom_reg={payload[1]:02X} display_option={payload[2:7].hex().upper()} "
        f"ping_pong={int(bool(payload[6] & 0x40))} waveform_version={payload[7:11].hex().upper()} "
        "groups=3 writes=0 refresh_commands=0 hard_resets=0"
    )
    return "\n".join(rows)


def self_test() -> None:
    result = parse_capture(valid_fixture())
    assert result["status"] == "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE"
    cases = {
        "short": valid_fixture().replace("display_len=11 display=1234010203044556575859", "display_len=10 display=12340102030445565758", 1),
        "long": valid_fixture().replace("display_len=11 display=1234010203044556575859", "display_len=12 display=123401020304455657585900", 1),
        "inconsistent": valid_fixture().replace("display=1234010203044556575859", "display=1334010203044556575859", 1),
        "bad_id": valid_fixture(chip=0x02),
        "busy": valid_fixture(chip=0x05),
        "all00": valid_fixture(bytes(11)),
        "allff": valid_fixture(bytes([0xFF]) * 11),
        "gpio": valid_fixture().replace("gpio_restore=1", "gpio_restore=0", 1),
        "missing": valid_fixture().replace("[epaper] readonly_state group=3", "[epaper] ignored group=3", 1),
        "extra": valid_fixture() + "\n" + GROUP_RE.search(valid_fixture()).group(0),
        "forbidden": valid_fixture() + "\n[epaper] command=0x20",
    }
    for name, fixture in cases.items():
        try:
            parse_capture(fixture)
        except GateError:
            continue
        raise AssertionError(f"negative fixture unexpectedly passed: {name}")
    print("PASS: SSD1681 read-only parser positive/negative self-test")


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
    try:
        result = parse_capture(args.log.read_text(encoding="utf-8", errors="replace"))
    except GateError as exc:
        print(f"NO_GO: {exc}", file=sys.stderr)
        return 1
    result["source_log"] = str(args.log)
    result["source_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest().upper()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
