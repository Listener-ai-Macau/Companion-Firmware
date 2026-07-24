#!/usr/bin/env python3
"""Fail-closed oracle for the R6 contiguous 16-activation Mode2 trace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


LUT_SHA = "75D7647188ACF1C79BC37313DC40105AF4445B9B6F422AD4FDAF0A465413984D"
SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
R5_HEX_SHA = "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564"
PREFIX = "[epaper] custom_mode2_observable_r6"
STEP_RE = re.compile(
    r"\[epaper\] custom_mode2_observable_r6 step=(\d+) previous=([WAB]) current=([WAB]) "
    r"ww=(\d+) wb=(\d+) bw=(\d+) bb=(\d+) old_command=0x26 old_bytes=128 "
    r"new_command=0x24 new_bytes=128 control=0xCF refresh=0x20 busy_complete=([01]) "
    r"busy_elapsed_ms=(\d+) lut_sha256=([0-9A-F]{64}) step_ok=([01])"
)
EXPECTED = [
    (1, "W", "A", 512, 512, 0, 0),
    *[(index, "A" if index % 2 == 0 else "B", "B" if index % 2 == 0 else "A", 256, 256, 256, 256)
      for index in range(2, 16)],
    (16, "A", "W", 512, 0, 512, 0),
]


def evaluate(text: str) -> dict[str, object]:
    errors: list[str] = []
    armed = (
        f"{PREFIX} armed immediate_after_authorization=1 countdown=0 dwell_ms=0 "
        "screen_commands=0 screen_refreshes=0"
    )
    start = (
        f"{PREFIX} start candidate=stationary_suppression_uniform_tp16_observable_r6 "
        f"lut_sha256={LUT_SHA} source_sha256={SOURCE_SHA} r5_hex_lineage={R5_HEX_SHA} "
        "activations=16 predicted_observation_ms=9583 window_x_bytes=1-4 window_y=8-39 "
        "window_bytes=128 old_bank=0x26 new_bank=0x24 control=0xCF refresh=0x20 "
        "busy_limit_ms=600 countdown=0 dwell_ms=0 verbose_during_observation=0 "
        "full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 "
        "voltage_tail=221741A83258 hard_resets_after_lut=0 retries=0 motion_120_frame=0"
    )
    load = (
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 "
        f"tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1"
    )
    for name, marker in (("armed", armed), ("start", start), ("lut_load", load)):
        if text.count(marker) != 1:
            errors.append(f"single exact {name} marker missing")

    complete_match = re.search(
        rf"{re.escape(PREFIX)} observation_complete activations_completed=(\d+) "
        r"elapsed_ms=(\d+) verbose_records_follow=1",
        text,
    )
    if complete_match is None:
        errors.append("observation_complete marker missing")
        complete_count = 0
        elapsed_ms = 0
    else:
        complete_count = int(complete_match.group(1))
        elapsed_ms = int(complete_match.group(2))
        if complete_count != 16:
            errors.append(f"observation_complete count differs: {complete_count}")
        if not 9000 <= elapsed_ms <= 11000:
            errors.append(f"contiguous observation elapsed outside 9000..11000 ms: {elapsed_ms}")

    steps: list[dict[str, object]] = []
    matches = list(STEP_RE.finditer(text))
    raw_step_prefixes = text.count(f"{PREFIX} step=")
    if raw_step_prefixes != 16 or len(matches) != 16:
        errors.append(f"expected exactly 16 complete records, got prefixes={raw_step_prefixes} parsed={len(matches)}")
    if complete_match is not None and matches and matches[0].start() < complete_match.end():
        errors.append("verbose step record occurred before observation_complete")
    for match in matches:
        values = match.groups()
        steps.append({
            "step": int(values[0]), "previous": values[1], "current": values[2],
            "ww": int(values[3]), "wb": int(values[4]), "bw": int(values[5]), "bb": int(values[6]),
            "busy": int(values[7]), "busy_ms": int(values[8]), "lut_sha": values[9], "ok": int(values[10]),
        })
    for index, step in enumerate(steps[:16]):
        expected = EXPECTED[index]
        observed = tuple(step[key] for key in ("step", "previous", "current", "ww", "wb", "bw", "bb"))
        if observed != expected:
            errors.append(f"step {index + 1} oracle differs: {observed} != {expected}")
        if sum(int(step[key]) for key in ("ww", "wb", "bw", "bb")) != 1024:
            errors.append(f"step {index + 1} does not cover the complete 32x32 window")
        if step["busy"] != 1 or step["ok"] != 1 or not 1 <= int(step["busy_ms"]) <= 600:
            errors.append(f"step {index + 1} transport/BUSY failed")
        if step["lut_sha"] != LUT_SHA:
            errors.append(f"step {index + 1} LUT hash differs")

    result = (
        f"{PREFIX} result=ok activations_completed=16 controls_cf=16 refresh_20=16 "
        "busy_completions=16 writes_26=16 writes_24=16 local_bytes_each=128 "
        "final_local_state=white countdown=0 dwell_ms=0 compensation_activations=0 "
        "verbose_during_observation=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 "
        "lut_loads=1 voltage_tail_changes=0 hard_resets_after_lut=0 retries=0 motion_120_frame=0 "
        f"observation_elapsed_ms={elapsed_ms} gpio_restore=1 sda=0 sck=0 cs=1"
    )
    if text.count(result) != 1:
        errors.append("final 16-count/white/no-extra/GPIO marker missing")

    return {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_observable_r6_trace.v1",
        "status": "PASS_MACHINE_CUSTOM_MODE2_OBSERVABLE_R6" if not errors else "NO_GO_CUSTOM_MODE2_OBSERVABLE_R6",
        "errors": errors,
        "contract": {
            "activations": 16, "contiguous": True, "predicted_busy_sum_ms": 9583,
            "elapsed_range_ms": [9000, 11000], "window": {"x_bytes": [1, 4], "y": [8, 39], "bytes_per_plane": 128},
            "old_bank": "0x26", "new_bank": "0x24", "control": "0xCF", "refresh": "0x20",
            "candidate_lut_sha256": LUT_SHA, "r5_hex_lineage_sha256": R5_HEX_SHA,
            "countdown": 0, "dwell_ms": 0, "full_frame_refreshes": 0,
            "compensation_activations": 0, "retries": 0, "motion_120_frame": False,
        },
        "observed": {"records": len(steps), "observation_elapsed_ms": elapsed_ms, "steps": steps},
        "hardware_contact": 1,
        "production_allowed": False,
    }


def fixture() -> str:
    lines = [
        f"{PREFIX} armed immediate_after_authorization=1 countdown=0 dwell_ms=0 screen_commands=0 screen_refreshes=0",
        f"{PREFIX} start candidate=stationary_suppression_uniform_tp16_observable_r6 lut_sha256={LUT_SHA} source_sha256={SOURCE_SHA} r5_hex_lineage={R5_HEX_SHA} activations=16 predicted_observation_ms=9583 window_x_bytes=1-4 window_y=8-39 window_bytes=128 old_bank=0x26 new_bank=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 countdown=0 dwell_ms=0 verbose_during_observation=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 voltage_tail=221741A83258 hard_resets_after_lut=0 retries=0 motion_120_frame=0",
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1",
        f"{PREFIX} observation_complete activations_completed=16 elapsed_ms=9583 verbose_records_follow=1",
    ]
    for step, previous, current, ww, wb, bw, bb in EXPECTED:
        lines.append(
            f"{PREFIX} step={step} previous={previous} current={current} ww={ww} wb={wb} bw={bw} bb={bb} "
            f"old_command=0x26 old_bytes=128 new_command=0x24 new_bytes=128 control=0xCF refresh=0x20 "
            f"busy_complete=1 busy_elapsed_ms={598 if step == 1 else 599} lut_sha256={LUT_SHA} step_ok=1"
        )
    lines.append(
        f"{PREFIX} result=ok activations_completed=16 controls_cf=16 refresh_20=16 busy_completions=16 "
        "writes_26=16 writes_24=16 local_bytes_each=128 final_local_state=white countdown=0 dwell_ms=0 "
        "compensation_activations=0 verbose_during_observation=0 full_refreshes=0 controls_ff=0 controls_f7=0 "
        "controls_c7=0 lut_loads=1 voltage_tail_changes=0 hard_resets_after_lut=0 retries=0 motion_120_frame=0 "
        "observation_elapsed_ms=9583 gpio_restore=1 sda=0 sck=0 cs=1"
    )
    return "\n".join(lines)


def self_test() -> int:
    good = fixture()
    first_step = good.index(f"{PREFIX} step=1")
    complete_start = good.index(f"{PREFIX} observation_complete")
    complete_end = good.index("\n", complete_start) + 1
    early = good[:complete_start] + good[first_step:good.index("\n", first_step) + 1] + good[complete_start:first_step] + good[good.index("\n", first_step) + 1:]
    cases = {
        "missing": good.replace(f"{PREFIX} step=16", f"{PREFIX} omitted=16", 1),
        "extra": good.replace(f"{PREFIX} result=", good[good.index(f"{PREFIX} step=15"):good.index("\n", good.index(f"{PREFIX} step=15")) + 1] + f"{PREFIX} result=", 1),
        "class": good.replace("wb=256", "wb=255", 1),
        "busy": good.replace("busy_elapsed_ms=598", "busy_elapsed_ms=601", 1),
        "dwell": good.replace("dwell_ms=0", "dwell_ms=800", 1),
        "countdown": good.replace("countdown=0", "countdown=3", 1),
        "early_uart": early,
        "forbidden_control": good.replace("controls_f7=0", "controls_f7=1", 1),
        "retry": good.replace("retries=0", "retries=1", 1),
        "motion": good.replace("motion_120_frame=0", "motion_120_frame=1", 1),
    }
    passed = evaluate(good)["status"] == "PASS_MACHINE_CUSTOM_MODE2_OBSERVABLE_R6"
    rejected = {name: evaluate(value)["status"] == "NO_GO_CUSTOM_MODE2_OBSERVABLE_R6" for name, value in cases.items()}
    ok = passed and all(rejected.values())
    print("PASS: R6 parser positive and missing/extra/class/BUSY/dwell/countdown/early-UART/forbidden/retry/motion negatives" if ok else f"FAIL: {rejected}")
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
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    sys.exit(main())
