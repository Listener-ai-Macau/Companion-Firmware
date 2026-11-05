#!/usr/bin/env python3
"""Machine oracle for the bounded custom Mode2 four-transition safety run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


LUT_SHA = "75D7647188ACF1C79BC37313DC40105AF4445B9B6F422AD4FDAF0A465413984D"
SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
STEP_RE = re.compile(
    r"\[epaper\] custom_mode2_safety step=(\d+) previous=([WAB]) current=([WAB]) "
    r"ww=(\d+) wb=(\d+) bw=(\d+) bb=(\d+) old_command=0x26 old_bytes=128 "
    r"new_command=0x24 new_bytes=128 control=0xCF refresh=0x20 busy_complete=([01]) "
    r"busy_elapsed_ms=(\d+) lut_sha256=([0-9A-F]{64}) step_ok=([01])"
)
EXPECTED = [
    (1, "W", "A", 512, 512, 0, 0),
    (2, "A", "B", 256, 256, 256, 256),
    (3, "B", "A", 256, 256, 256, 256),
    (4, "A", "B", 256, 256, 256, 256),
    (5, "B", "A", 256, 256, 256, 256),
    (6, "A", "B", 256, 256, 256, 256),
    (7, "B", "A", 256, 256, 256, 256),
    (8, "A", "B", 256, 256, 256, 256),
    (9, "B", "W", 512, 0, 512, 0),
]


def evaluate(text: str) -> dict[str, object]:
    errors: list[str] = []
    countdowns = [int(value) for value in re.findall(
        r"custom_mode2_safety countdown=(\d+) screen_commands=0 screen_refreshes=0", text
    )]
    if countdowns != [3, 2, 1]:
        errors.append(f"countdown differs: {countdowns}")
    start = (
        "custom_mode2_safety start candidate=stationary_suppression_uniform_tp16_r4 "
        f"lut_sha256={LUT_SHA} source_sha256={SOURCE_SHA} activations=9 "
        "window_x_bytes=1-4 window_y=8-39 window_bytes=128 old_bank=0x26 "
        "new_bank=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 full_refreshes=0 controls_ff=0 "
        "controls_f7=0 controls_c7=0 voltage_tail=221741A83258 hard_resets_after_lut=0 retries=0"
    )
    if text.count(start) != 1:
        errors.append("single start contract marker missing")
    load = (
        "custom_mode2_safety lut_load command=0x32 payload_bytes=153 "
        f"tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1"
    )
    if text.count(load) != 1:
        errors.append("single exact LUT/tail load marker missing")

    steps = []
    for match in STEP_RE.finditer(text):
        values = match.groups()
        steps.append({
            "step": int(values[0]),
            "previous": values[1],
            "current": values[2],
            "ww": int(values[3]),
            "wb": int(values[4]),
            "bw": int(values[5]),
            "bb": int(values[6]),
            "busy": int(values[7]),
            "busy_ms": int(values[8]),
            "lut_sha": values[9],
            "ok": int(values[10]),
        })
    if len(steps) != 9:
        errors.append(f"expected 9 transition records, got {len(steps)}")
    for index, step in enumerate(steps[:9]):
        expected = EXPECTED[index]
        observed = (
            step["step"], step["previous"], step["current"], step["ww"],
            step["wb"], step["bw"], step["bb"],
        )
        if observed != expected:
            errors.append(f"step {index + 1} oracle differs: {observed} != {expected}")
        if sum(int(step[key]) for key in ("ww", "wb", "bw", "bb")) != 1024:
            errors.append(f"step {index + 1} does not cover 1024 local pixels")
        if step["busy"] != 1 or step["ok"] != 1:
            errors.append(f"step {index + 1} transport/BUSY failed")
        if step["busy_ms"] > 600:
            errors.append(f"step {index + 1} BUSY exceeds 600 ms")
        if step["lut_sha"] != LUT_SHA:
            errors.append(f"step {index + 1} LUT hash differs")

    result = (
        "custom_mode2_safety result=ok activations_completed=9 controls_cf=9 "
        "refresh_20=9 busy_completions=9 writes_26=9 writes_24=9 local_bytes_each=128 "
        "final_local_state=white full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 "
        "lut_loads=1 voltage_tail_changes=0 hard_resets_after_lut=0 retries=0 "
        "gpio_restore=1 sda=0 sck=0 cs=1"
    )
    if text.count(result) != 1:
        errors.append("final count/white/GPIO marker missing")
    if steps and not all(any(int(step[key]) > 0 for step in steps) for key in ("ww", "wb", "bw", "bb")):
        errors.append("run does not cover all WW/WB/BW/BB classes")

    return {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_transition_safety_trace.v1",
        "status": "PASS_MACHINE_CUSTOM_MODE2_TRANSITION_SAFETY" if not errors else "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY",
        "errors": errors,
        "contract": {
            "activations": 9,
            "maximum_activations": 16,
            "window": {"x_bytes": [1, 4], "y": [8, 39], "bytes_per_plane": 128},
            "transition_classes": ["WW", "WB", "BW", "BB"],
            "old_bank": "0x26",
            "new_bank": "0x24",
            "control": "0xCF",
            "refresh": "0x20",
            "candidate_lut_sha256": LUT_SHA,
            "protected_tail_hex": "221741A83258",
            "full_frame_refreshes": 0,
            "final_local_state": "white",
        },
        "observed": {"records": len(steps), "steps": steps},
        "hardware_contact": 1,
        "production_allowed": False,
    }


def fixture() -> str:
    lines = [
        f"[epaper] custom_mode2_safety countdown={value} screen_commands=0 screen_refreshes=0"
        for value in (3, 2, 1)
    ]
    lines.append(
        f"[epaper] custom_mode2_safety start candidate=stationary_suppression_uniform_tp16_r4 lut_sha256={LUT_SHA} source_sha256={SOURCE_SHA} activations=9 window_x_bytes=1-4 window_y=8-39 window_bytes=128 old_bank=0x26 new_bank=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 voltage_tail=221741A83258 hard_resets_after_lut=0 retries=0"
    )
    lines.append(
        f"[epaper] custom_mode2_safety lut_load command=0x32 payload_bytes=153 tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1"
    )
    for step, previous, current, ww, wb, bw, bb in EXPECTED:
        lines.append(
            f"[epaper] custom_mode2_safety step={step} previous={previous} current={current} "
            f"ww={ww} wb={wb} bw={bw} bb={bb} old_command=0x26 old_bytes=128 "
            f"new_command=0x24 new_bytes=128 control=0xCF refresh=0x20 busy_complete=1 "
            f"busy_elapsed_ms=447 lut_sha256={LUT_SHA} step_ok=1"
        )
    lines.append(
        "[epaper] custom_mode2_safety result=ok activations_completed=9 controls_cf=9 refresh_20=9 busy_completions=9 writes_26=9 writes_24=9 local_bytes_each=128 final_local_state=white full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 lut_loads=1 voltage_tail_changes=0 hard_resets_after_lut=0 retries=0 gpio_restore=1 sda=0 sck=0 cs=1"
    )
    return "\n".join(lines)


def self_test() -> int:
    good = evaluate(fixture())
    cases = [
        fixture().replace("step=9", "other=9", 1),
        fixture().replace("wb=256", "wb=255", 1),
        fixture().replace("busy_elapsed_ms=447", "busy_elapsed_ms=601", 1),
        fixture().replace("control=0xCF", "control=0xFF", 1),
        fixture().replace("final_local_state=white", "final_local_state=unknown", 1),
    ]
    ok = good["status"] == "PASS_MACHINE_CUSTOM_MODE2_TRANSITION_SAFETY" and all(
        evaluate(case)["status"] == "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY" for case in cases
    )
    print("PASS: custom Mode2 parser positive/missing/class/timing/control/final fixtures" if ok else "FAIL: custom Mode2 parser self-test")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.log is None or args.out is None:
        parser.error("--log and --out are required unless --self-test is used")
    result = evaluate(args.log.read_text(encoding="utf-8", errors="ignore"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "PASS_MACHINE_CUSTOM_MODE2_TRANSITION_SAFETY" else 1


if __name__ == "__main__":
    sys.exit(main())
