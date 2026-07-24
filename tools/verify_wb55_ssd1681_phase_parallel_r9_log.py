#!/usr/bin/env python3
"""Fail-closed parser for the bounded SSD1681 phase-parallel R9 trace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
WORKBENCH_SHA = "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF"
SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
PREFIX = "[epaper] phase_parallel_r9"
STEP_RE = re.compile(
    r"\[epaper\] phase_parallel_r9 step=(\d+) previous=([WAB]) current=([WAB]) "
    r"ww=(\d+) wb=(\d+) bw=(\d+) bb=(\d+) old_command=0x26 old_selector=1 "
    r"old_bytes=128 new_command=0x24 new_selector=0 new_bytes=128 control=0xCF "
    r"refresh=0x20 busy_complete=([01]) busy_elapsed_ms=(\d+) post_sync_command=0x24 "
    r"post_sync_bytes=(\d+) post_sync_refresh=0 lut_sha256=([0-9A-F]{64}) step_ok=([01])"
)
EXPECTED = [
    (1, "W", "A", 512, 512, 0, 0),
    *[
        (
            index,
            "A" if index % 2 == 0 else "B",
            "B" if index % 2 == 0 else "A",
            256,
            256,
            256,
            256,
        )
        for index in range(2, 16)
    ],
    (16, "A", "W", 512, 0, 512, 0),
]


def evaluate(text: str, *, hardware_contact: int = 1) -> dict[str, object]:
    errors: list[str] = []
    armed = f"{PREFIX} armed countdown=0 dwell_ms=0 screen_commands=0 screen_refreshes=0"
    start = (
        f"{PREFIX} start candidate=source_field_reorder_phase_parallel_r9 "
        f"lut_sha256={LUT_SHA} workbench_sha256={WORKBENCH_SHA} source_sha256={SOURCE_SHA} "
        "activations=16 predicted_busy_max_ms=599 window_x_bytes=1-4 window_y=8-39 "
        "window_bytes=128 old_command=0x26 old_selector=1 new_command=0x24 new_selector=0 "
        "post_sync_command=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 countdown=0 "
        "dwell_ms=0 verbose_during_observation=0 full_frame_writes=0 full_refreshes=0 "
        "controls_ff=0 controls_f7=0 controls_c7=0 voltage_tail=221741A83258 retries=0 "
        "motion_120_frame=0"
    )
    load = (
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 "
        f"tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1"
    )
    for name, marker in (("armed", armed), ("start", start), ("lut_load", load)):
        if text.count(marker) != 1:
            errors.append(f"single exact {name} marker missing")

    complete = re.search(
        rf"{re.escape(PREFIX)} observation_complete activations_completed=(\d+) "
        r"elapsed_ms=(\d+) verbose_records_follow=1",
        text,
    )
    completed = int(complete.group(1)) if complete else 0
    elapsed_ms = int(complete.group(2)) if complete else 0
    if complete is None or completed != 16:
        errors.append("observation_complete is not exactly 16")

    matches = list(STEP_RE.finditer(text))
    if text.count(f"{PREFIX} step=") != 16 or len(matches) != 16:
        errors.append("trace does not contain exactly 16 complete step records")
    if complete and matches and matches[0].start() < complete.end():
        errors.append("step UART was emitted before observation completion")

    steps: list[dict[str, object]] = []
    for match in matches:
        values = match.groups()
        steps.append(
            {
                "step": int(values[0]),
                "previous": values[1],
                "current": values[2],
                "ww": int(values[3]),
                "wb": int(values[4]),
                "bw": int(values[5]),
                "bb": int(values[6]),
                "busy_complete": int(values[7]),
                "busy_ms": int(values[8]),
                "post_sync_bytes": int(values[9]),
                "lut_sha256": values[10],
                "step_ok": int(values[11]),
            }
        )
    for index, step in enumerate(steps[:16]):
        expected = EXPECTED[index]
        observed = tuple(
            step[key] for key in ("step", "previous", "current", "ww", "wb", "bw", "bb")
        )
        if observed != expected:
            errors.append(f"step {index + 1} transition oracle differs")
        if sum(int(step[key]) for key in ("ww", "wb", "bw", "bb")) != 1024:
            errors.append(f"step {index + 1} does not cover one complete 32x32 window")
        if step["busy_complete"] != 1 or not 1 <= int(step["busy_ms"]) <= 600:
            errors.append(f"step {index + 1} BUSY is not a <=600 ms completion")
        if step["post_sync_bytes"] != 128:
            errors.append(f"step {index + 1} post-activation selector0 synchronization differs")
        if step["lut_sha256"] != LUT_SHA or step["step_ok"] != 1:
            errors.append(f"step {index + 1} candidate identity or transport differs")

    busy_sum = sum(int(step["busy_ms"]) for step in steps)
    if steps and (elapsed_ms < busy_sum or elapsed_ms > 16000):
        errors.append("bounded observation elapsed time is inconsistent with step BUSY values")
    coverage = {
        transition: sum(int(step[transition.lower()]) for step in steps)
        for transition in ("WW", "WB", "BW", "BB")
    }
    if steps and any(value <= 0 for value in coverage.values()):
        errors.append("WW/WB/BW/BB runtime pixel coverage is incomplete")

    result = (
        f"{PREFIX} result=ok activations_completed=16 controls_cf=16 refresh_20=16 "
        "busy_completions=16 writes_26=16 stage_writes_24=16 post_sync_24=16 "
        "post_sync_refresh=0 local_bytes_each=128 final_local_state=white countdown=0 dwell_ms=0 "
        "verbose_during_observation=0 full_frame_writes=0 full_refreshes=0 controls_ff=0 "
        "controls_f7=0 controls_c7=0 lut_loads=1 voltage_tail_changes=0 retries=0 "
        f"motion_120_frame=0 observation_elapsed_ms={elapsed_ms} gpio_restore=1 sda=0 sck=0 cs=1"
    )
    if text.count(result) != 1:
        errors.append("final count/window/control/no-extra/GPIO marker missing")

    return {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_trace.v1",
        "status": "PASS_MACHINE_PHASE_PARALLEL_R9" if not errors else "NO_GO_PHASE_PARALLEL_R9",
        "errors": errors,
        "hardware_contact": hardware_contact,
        "candidate": {
            "lut_sha256": LUT_SHA,
            "workbench_sha256": WORKBENCH_SHA,
            "supplier_source_sha256": SOURCE_SHA,
            "voltage_tail_hex": "221741A83258",
        },
        "contract": {
            "activations": 16,
            "window": {"x_bytes": [1, 4], "y": [8, 39], "bytes_per_plane": 128},
            "previous_command": "0x26",
            "previous_selector": 1,
            "current_command": "0x24",
            "current_selector": 0,
            "post_sync_command": "0x24",
            "control": "0xCF",
            "refresh": "0x20",
            "busy_limit_ms": 600,
            "full_frame_writes": 0,
            "forbidden_controls": {"0xF7": 0, "0xC7": 0, "0xFF": 0},
            "automatic_retries": 0,
            "motion_120_frame": False,
        },
        "observed": {
            "records": len(steps),
            "observation_elapsed_ms": elapsed_ms,
            "busy_sum_ms": busy_sum,
            "busy_max_ms": max((int(step["busy_ms"]) for step in steps), default=None),
            "pixel_class_coverage": coverage,
            "steps": steps,
        },
        "production_allowed": False,
    }


def fixture() -> str:
    elapsed = 9584
    lines = [
        f"{PREFIX} armed countdown=0 dwell_ms=0 screen_commands=0 screen_refreshes=0",
        f"{PREFIX} start candidate=source_field_reorder_phase_parallel_r9 lut_sha256={LUT_SHA} "
        f"workbench_sha256={WORKBENCH_SHA} source_sha256={SOURCE_SHA} activations=16 "
        "predicted_busy_max_ms=599 window_x_bytes=1-4 window_y=8-39 window_bytes=128 "
        "old_command=0x26 old_selector=1 new_command=0x24 new_selector=0 post_sync_command=0x24 "
        "control=0xCF refresh=0x20 busy_limit_ms=600 countdown=0 dwell_ms=0 "
        "verbose_during_observation=0 full_frame_writes=0 full_refreshes=0 controls_ff=0 "
        "controls_f7=0 controls_c7=0 voltage_tail=221741A83258 retries=0 motion_120_frame=0",
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 "
        f"tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1",
        f"{PREFIX} observation_complete activations_completed=16 elapsed_ms={elapsed} verbose_records_follow=1",
    ]
    for step, previous, current, ww, wb, bw, bb in EXPECTED:
        lines.append(
            f"{PREFIX} step={step} previous={previous} current={current} ww={ww} wb={wb} bw={bw} bb={bb} "
            "old_command=0x26 old_selector=1 old_bytes=128 new_command=0x24 new_selector=0 "
            "new_bytes=128 control=0xCF refresh=0x20 busy_complete=1 busy_elapsed_ms=599 "
            f"post_sync_command=0x24 post_sync_bytes=128 post_sync_refresh=0 lut_sha256={LUT_SHA} step_ok=1"
        )
    lines.append(
        f"{PREFIX} result=ok activations_completed=16 controls_cf=16 refresh_20=16 "
        "busy_completions=16 writes_26=16 stage_writes_24=16 post_sync_24=16 post_sync_refresh=0 "
        "local_bytes_each=128 final_local_state=white countdown=0 dwell_ms=0 "
        "verbose_during_observation=0 full_frame_writes=0 full_refreshes=0 controls_ff=0 "
        "controls_f7=0 controls_c7=0 lut_loads=1 voltage_tail_changes=0 retries=0 "
        f"motion_120_frame=0 observation_elapsed_ms={elapsed} gpio_restore=1 sda=0 sck=0 cs=1"
    )
    return "\n".join(lines)


def self_test() -> int:
    good = fixture()
    step_one = good.index(f"{PREFIX} step=1")
    step_one_end = good.index("\n", step_one) + 1
    complete = good.index(f"{PREFIX} observation_complete")
    early = good[:complete] + good[step_one:step_one_end] + good[complete:step_one] + good[step_one_end:]
    cases = {
        "missing_step": good.replace(f"{PREFIX} step=16", f"{PREFIX} omitted=16", 1),
        "extra_activation": good.replace("activations_completed=16", "activations_completed=17", 1),
        "wrong_fixed_bank": good.replace("old_selector=1", "old_selector=0", 1),
        "class_oracle": good.replace("wb=256", "wb=255", 1),
        "busy_over_limit": good.replace("busy_elapsed_ms=599", "busy_elapsed_ms=601", 1),
        "missing_post_sync": good.replace("post_sync_bytes=128", "post_sync_bytes=0", 1),
        "early_uart": early,
        "full_frame": good.replace("full_frame_writes=0", "full_frame_writes=1", 1),
        "f7": good.replace("controls_f7=0", "controls_f7=1", 1),
        "c7": good.replace("controls_c7=0", "controls_c7=1", 1),
        "ff": good.replace("controls_ff=0", "controls_ff=1", 1),
        "retry": good.replace("retries=0", "retries=1", 1),
        "motion": good.replace("motion_120_frame=0", "motion_120_frame=1", 1),
        "tail": good.replace("tails=3F:22", "tails=3F:23", 1),
    }
    passed = evaluate(good, hardware_contact=0)["status"] == "PASS_MACHINE_PHASE_PARALLEL_R9"
    rejected = {
        name: evaluate(value, hardware_contact=0)["status"] == "NO_GO_PHASE_PARALLEL_R9"
        for name, value in cases.items()
    }
    ok = passed and all(rejected.values())
    print(
        "PASS: R9 trace parser positive and bounded negative fixtures"
        if ok
        else f"FAIL: passed={passed} rejected={rejected}"
    )
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
    return 0 if result["status"] == "PASS_MACHINE_PHASE_PARALLEL_R9" else 1


if __name__ == "__main__":
    sys.exit(main())
