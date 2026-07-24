#!/usr/bin/env python3
"""Focused offline R6 target-unipolar LUT and schema-v5 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import verify_wb55_ssd1681_r10_ball_log as log_parser

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-r6-target-unipolar-focused-20260722.json"
R9_NAME = "ssd1681_phase_parallel_r9_lut"
R5_NAME = "ssd1681_r10_r5_lut"
R6_NAME = "ssd1681_r10_r6_lut"
R9_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
R5_SHA = "447FB169543F3E33EA6080607B685E2ADB8F38066952FCDF020882359BA94E89"
R6_SHA = "8525533D1971CE99F46A1AD6580741920B7FA152D2A99632206BE0E17696A5E8"


class Failure(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise Failure(message)


def values(source: str, name: str) -> list[int]:
    match = re.search(rf"static const uint8_t {name}\[159\] = \{{(.*?)\n\}};", source, re.S)
    require(match is not None, f"missing {name}")
    result = [int(token, 16) for token in re.findall(r"0x([0-9A-Fa-f]{2})u?", match.group(1))]
    require(len(result) == 159, f"{name} length is not 159")
    return result


def waveform(source: str) -> dict[str, object]:
    r9, r5, r6 = values(source, R9_NAME), values(source, R5_NAME), values(source, R6_NAME)
    require(sha(bytes(r9)) == R9_SHA and sha(bytes(r5)) == R5_SHA and sha(bytes(r6)) == R6_SHA, "R9/R5/R6 LUT hash drift")
    diff_r9 = [i for i, (a, b) in enumerate(zip(r9, r6)) if a != b]
    diff_r5 = [i for i, (a, b) in enumerate(zip(r5, r6)) if a != b]
    require(diff_r9 == [12, 13, 24, 25], "R6 differs from R9 outside the two polarity lead bytes")
    require(diff_r5 == [14, 15, 26, 27], "R6 differs from R5 outside the two polarity lead bytes")
    require(r6[12:16] == [0x80] * 4 and r6[24:28] == [0x40] * 4, "R6 is not target-unipolar")
    require(r6[60:] == r9[60:] and r6[-6:] == [0x22, 0x17, 0x41, 0xA8, 0x32, 0x58], "R6 timing/tail bytes changed")
    start = source.index("static void ssd1681_phase_parallel_r10_ball_diagnostic")
    end = source.index("#endif", start)
    r10 = source[start:end]
    for token in (
        "schema=v5", "SSD1681_R10_R6_LUT_SHA256", R6_NAME,
        "ssd1681_command_data(0x32u, ssd1681_r10_r6_lut, 153u)",
        "ssd1681_command_data(0x3Fu, &ssd1681_r10_r6_lut[153], 1u)",
        "ssd1681_command_data(0x03u, &ssd1681_r10_r6_lut[154], 1u)",
        "ssd1681_command_data(0x04u, &ssd1681_r10_r6_lut[155], 3u)",
        "ssd1681_command_data(0x2Cu, &ssd1681_r10_r6_lut[158], 1u)",
    ):
        require(token in r10, f"R6 source missing {token}")
    require(R5_NAME not in r10, "R6 diagnostic still loads R5 LUT")
    return {
        "r9_lut_sha256": R9_SHA, "r5_lut_sha256": R5_SHA, "r6_lut_sha256": R6_SHA,
        "r6_vs_r9_changed_offsets": diff_r9, "r6_vs_r5_changed_offsets": diff_r5,
        "bw_net": -16, "wb_net": 16, "ww_net": 0, "bb_net": 0,
        "shared_tp_frames": 16, "timing_bytes_60_143_preserved": True,
        "tail_hex": "221741A83258", "non_lut_contract_unchanged": True,
    }


def reject(name: str, callback) -> dict[str, str]:
    try:
        callback()
    except (Failure, log_parser.LogFailure, log_parser.oracle.OracleFailure) as error:
        return {"name": name, "result": "rejected", "reason": str(error)}
    raise Failure(f"negative fixture accepted: {name}")


def parser_evidence() -> dict[str, object]:
    positive = log_parser.r6_positive_log(2).replace("busy_elapsed_ms=500", "busy_elapsed_ms=599")
    parsed = log_parser.parse_log(positive, 2)
    loop = log_parser.parse_loop_log(positive, 2)
    require(parsed["busy_max_ms"] == 599 and loop["busy_max_ms"] == 599, "v5 positive BUSY is not 599")
    negatives = [
        reject("r5_lut", lambda: log_parser.parse_log(positive.replace(log_parser.R6_LUT_SHA256, log_parser.R5_LUT_SHA256), 2)),
        reject("old_lut", lambda: log_parser.parse_log(positive.replace(log_parser.R6_LUT_SHA256, log_parser.oracle.LUT_SHA256), 2)),
        reject("wrong_payload", lambda: log_parser.parse_log(re.sub(r"previous_payload_sha256=[0-9A-F]{64}", "previous_payload_sha256=" + "0" * 64, positive, count=1), 2)),
    ]
    return {"positive_schema_v5": {"status": parsed["status"], "loop_status": loop["status"], "busy_max_ms": 599}, "negative_fixtures": negatives}


def wrong_direction(source: str) -> dict[str, str]:
    start = source.index(f"static const uint8_t {R6_NAME}[159]")
    end = source.index("};", start)
    block = source[start:end]
    mutated = block.replace("0x80u, 0x80u, 0x80u, 0x80u", "0x40u, 0x40u, 0x40u, 0x40u", 1)
    try:
        waveform(source[:start] + mutated + source[end:])
    except Failure as error:
        return {"name": "wrong_direction", "result": "rejected", "reason": str(error)}
    raise Failure("negative fixture accepted: wrong_direction")


def build() -> dict[str, object]:
    source = DRIVER.read_text(encoding="utf-8")
    return {
        "schema_id": "companion.wb55.ssd1681.r10_r6_target_unipolar_focused.v1",
        "status": "PASS_R10_R6_TARGET_UNIPOLAR_FOCUSED",
        "authority": "COMP-REQ-345",
        "hardware_contact": 0,
        "execute_authorized": False,
        "driver_sha256": sha(source.encode("utf-8")),
        "waveform": waveform(source),
        "parser": parser_evidence(),
        "direction_negative": wrong_direction(source),
    }


def main() -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--write", action="store_true")
    args.add_argument("--artifact", type=Path, default=ARTIFACT)
    options = args.parse_args()
    try:
        value = build()
    except (OSError, Failure, log_parser.LogFailure, log_parser.oracle.OracleFailure) as error:
        print(f"FAIL: R10 R6 focused: {error}")
        return 1
    rendered = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if options.write:
        options.artifact.parent.mkdir(parents=True, exist_ok=True)
        temp = options.artifact.with_name(options.artifact.name + ".tmp")
        temp.write_bytes(rendered)
        temp.replace(options.artifact)
    elif not options.artifact.exists() or options.artifact.read_bytes() != rendered:
        print(f"FAIL: stale R6 focused artifact: {options.artifact}")
        return 1
    print(f"PASS: R10 R6 target-unipolar focused negatives=4 sha256={sha(rendered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
