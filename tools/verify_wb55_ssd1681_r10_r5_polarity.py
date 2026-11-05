#!/usr/bin/env python3
"""Focused, offline R5 LUT direction and schema-v4 regression."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import verify_wb55_ssd1681_r10_ball_log as log_parser


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-r5-polarity-focused-20260722.json"
R9_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
R5_SHA = "447FB169543F3E33EA6080607B685E2ADB8F38066952FCDF020882359BA94E89"
R9_NAME = "ssd1681_phase_parallel_r9_lut"
R5_NAME = "ssd1681_r10_r5_lut"
TAIL = [0x22, 0x17, 0x41, 0xA8, 0x32, 0x58]


class Failure(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def array_values(source: str, name: str) -> list[int]:
    match = re.search(rf"static const uint8_t {name}\[159\] = \{{(.*?)\n\}};", source, re.S)
    require(match is not None, f"missing 159-byte array {name}")
    values = [int(token, 16) for token in re.findall(r"0x([0-9A-Fa-f]{2})u?", match.group(1))]
    require(len(values) == 159, f"{name} has {len(values)} bytes, expected 159")
    return values


def waveform_evidence(source: str) -> dict[str, object]:
    old = array_values(source, R9_NAME)
    new = array_values(source, R5_NAME)
    changed = [index for index, (before, after) in enumerate(zip(old, new)) if before != after]
    require(sha256(bytes(old)) == R9_SHA, "historical R9 LUT hash drifted")
    require(sha256(bytes(new)) == R5_SHA, "R5 LUT hash does not match the sealed candidate")
    require(changed == list(range(12, 16)) + list(range(24, 28)), "R5 changed offsets are not exactly the two 4-byte polarity groups")
    require(new[12:16] == [0x80, 0x80, 0x40, 0x40], "R5 BW direction was not reversed")
    require(new[24:28] == [0x40, 0x40, 0x80, 0x80], "R5 WB direction was not reversed")
    require(old[12:16] == [0x40, 0x40, 0x80, 0x80] and old[24:28] == [0x80, 0x80, 0x40, 0x40], "R9 source polarity groups drifted")
    require(new[60:] == old[60:] and new[-6:] == TAIL, "R5 timing/tail bytes changed")

    start = source.index("static void ssd1681_phase_parallel_r10_ball_diagnostic")
    end = source.index("#endif", start)
    r10 = source[start:end]
    for token in (
        "schema=v4", "SSD1681_R10_R5_LUT_SHA256", "ssd1681_r10_r5_lut",
        "ssd1681_command_data(0x32u, ssd1681_r10_r5_lut, 153u)",
        "ssd1681_command_data(0x3Fu, &ssd1681_r10_r5_lut[153], 1u)",
        "ssd1681_command_data(0x03u, &ssd1681_r10_r5_lut[154], 1u)",
        "ssd1681_command_data(0x04u, &ssd1681_r10_r5_lut[155], 3u)",
        "ssd1681_command_data(0x2Cu, &ssd1681_r10_r5_lut[158], 1u)",
    ):
        require(token in r10, f"R5 R10 path is missing {token}")
    require(R9_NAME not in r10, "R10 path still references the historical R9 LUT")

    frame_start = source.index("#define SSD1681_R10_WHITE_POSITION")
    frame_end = source.index("static void ssd1681_r10_print_frame", frame_start)
    frame = source[frame_start:frame_end]
    for token in (
        "SSD1681_R10_CORRIDOR_X_START_BYTE 4u", "SSD1681_R10_CORRIDOR_X_END_BYTE 9u",
        "SSD1681_R10_CORRIDOR_Y_START 80u", "SSD1681_R10_CORRIDOR_Y_END 91u",
        "SSD1681_R10_CORRIDOR_BYTES 72u", "ssd1681_r10_corridor_from_difference",
        "ssd1681_write_plane_region(0x26u", "ssd1681_write_plane_region(0x24u",
        "ssd1681_command_data(0x22u", "ssd1681_command(0x20u)",
        "HAL_Delay(SSD1681_R10_STABLE_HOLD_TARGET_MS)",
    ):
        require(token in frame, f"non-LUT R10 frame contract is missing {token}")
    require("0xF7u" not in frame and "0xC7u" not in frame and "0x37u" not in frame, "forbidden refresh/control entered R5 frame path")
    return {
        "r9_lut_sha256": R9_SHA,
        "r5_lut_sha256": R5_SHA,
        "changed_offsets": changed,
        "changed_byte_count": len(changed),
        "direction": "BW_VSH1_to_VSL_and_WB_VSL_to_VSH1",
        "shared_bytes_preserved": 151,
        "tail_hex": "221741A83258",
        "non_lut_contract_unchanged": True,
    }


def rejected(name: str, callback) -> dict[str, str]:
    try:
        callback()
    except (log_parser.LogFailure, log_parser.oracle.OracleFailure, Failure) as error:
        return {"name": name, "result": "rejected", "reason": str(error)}
    raise Failure(f"negative fixture was accepted: {name}")


def parser_evidence() -> dict[str, object]:
    positive = log_parser.r5_positive_log(2).replace("busy_elapsed_ms=500", "busy_elapsed_ms=599")
    parsed = log_parser.parse_log(positive, minimum_loop_iterations=2)
    loop = log_parser.parse_loop_log(positive, minimum_loop_iterations=2)
    require(parsed["busy_max_ms"] == 599 and loop["busy_max_ms"] == 599, "R5 positive BUSY=599 was not retained")
    negatives = [
        rejected("old_lut_sha", lambda: log_parser.parse_log(positive.replace(log_parser.R5_LUT_SHA256, log_parser.oracle.LUT_SHA256), 2)),
        rejected("wrong_payload_hash", lambda: log_parser.parse_log(re.sub(r"previous_payload_sha256=[0-9A-F]{64}", "previous_payload_sha256=" + "0" * 64, positive, count=1), 2)),
    ]
    return {
        "positive_schema_v4": {"status": parsed["status"], "loop_status": loop["status"], "busy_max_ms": 599},
        "negative_fixtures": negatives,
    }


def direction_negative(source: str) -> dict[str, str]:
    block_start = source.index(f"static const uint8_t {R5_NAME}[159]")
    block_end = source.index("};", block_start)
    block = source[block_start:block_end]
    mutated = block.replace("0x80u, 0x80u, 0x40u, 0x40u", "0x40u, 0x40u, 0x80u, 0x80u", 1)
    try:
        waveform_evidence(source[:block_start] + mutated + source[block_end:])
    except Failure as error:
        return {"name": "wrong_direction", "result": "rejected", "reason": str(error)}
    raise Failure("negative fixture was accepted: wrong_direction")


def build_artifact() -> dict[str, object]:
    source = DRIVER.read_text(encoding="utf-8")
    evidence = waveform_evidence(source)
    parser = parser_evidence()
    return {
        "schema_id": "companion.wb55.ssd1681.r10_r5_polarity_focused.v1",
        "status": "PASS_R10_R5_POLARITY_FOCUSED",
        "authority": "COMP-REQ-341",
        "hardware_contact": 0,
        "execute_authorized": False,
        "waveform": evidence,
        "parser": parser,
        "direction_negative": direction_negative(source),
        "driver_sha256": sha256(source.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    args = parser.parse_args()
    try:
        value = build_artifact()
    except (OSError, Failure, log_parser.LogFailure, log_parser.oracle.OracleFailure) as error:
        print(f"FAIL: R10 R5 polarity focused: {error}")
        return 1
    rendered = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.write:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.artifact.with_name(args.artifact.name + ".tmp")
        temporary.write_bytes(rendered)
        temporary.replace(args.artifact)
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered:
        print(f"FAIL: stale R5 focused artifact: {args.artifact}")
        return 1
    print(f"PASS: R10 R5 polarity focused positive_schema_v4=PASS negatives=3")
    print(f"artifact={args.artifact.relative_to(ROOT).as_posix()} sha256={sha256(rendered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
