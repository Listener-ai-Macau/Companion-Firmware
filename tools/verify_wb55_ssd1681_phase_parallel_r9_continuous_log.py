#!/usr/bin/env python3
"""Fail-closed parser for the R9 continuous-observation UART ring."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
WORKBENCH_SHA = "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF"
SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
PREFIX = "[epaper] phase_parallel_r9_continuous"
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
QUALIFICATION_STEP_RE = re.compile(
    rf"{re.escape(PREFIX)} qualification_step=(\d+) previous=([WAB]) current=([WAB]) "
    r"ww=(\d+) wb=(\d+) bw=(\d+) bb=(\d+) old_command=0x26 old_selector=1 "
    r"old_bytes=128 new_command=0x24 new_selector=0 new_bytes=128 control=0xCF "
    r"refresh=0x20 busy_complete=([01]) busy_elapsed_ms=(\d+) post_sync_command=0x24 "
    r"post_sync_bytes=(\d+) post_sync_refresh=0 lut_sha256=([0-9A-F]{64}) step_ok=([01])"
)
LOOP_RE = re.compile(
    rf"{re.escape(PREFIX)} loop_iteration=(\d+) previous=([WAB]) current=([AB]) "
    r"ww=(\d+) wb=(\d+) bw=(\d+) bb=(\d+) old_command=0x26 old_selector=1 "
    r"old_bytes=128 new_command=0x24 new_selector=0 new_bytes=128 control=0xCF "
    r"refresh=0x20 busy_complete=([01]) busy_elapsed_ms=(\d+) post_sync_command=0x24 "
    r"post_sync_bytes=(\d+) post_sync_refresh=0 lut_sha256=([0-9A-F]{64}) "
    r"full_frame_writes=0 controls_ff=0 controls_f7=0 controls_c7=0 retries=0 "
    r"motion_120_frame=0 step_ok=([01])"
)


def _record(match: re.Match[str], *, qualification: bool) -> dict[str, object]:
    values = match.groups()
    return {
        "index": int(values[0]),
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
        "kind": "qualification" if qualification else "loop",
    }


def evaluate(text: str, *, hardware_contact: int = 1) -> dict[str, object]:
    errors: list[str] = []
    armed = (
        f"{PREFIX} armed qualification_activations=16 loop_limit=none popup_commands=0 "
        "telemetry_storage=host_ring_65536"
    )
    start = (
        f"{PREFIX} start candidate=source_field_reorder_phase_parallel_r9 "
        f"lut_sha256={LUT_SHA} workbench_sha256={WORKBENCH_SHA} source_sha256={SOURCE_SHA} "
        "window_x_bytes=1-4 window_y=8-39 window_bytes=128 old_command=0x26 old_selector=1 "
        "new_command=0x24 new_selector=0 post_sync_command=0x24 control=0xCF refresh=0x20 "
        "busy_limit_ms=600 full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 "
        "controls_c7=0 voltage_tail=221741A83258 retries=0 motion_120_frame=0 production_enabled=0"
    )
    load = (
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 tails=3F:22,03:17,04:41A832,2C:58 "
        f"candidate_sha256={LUT_SHA} loaded=1"
    )
    for name, marker in (("armed", armed), ("start", start), ("lut_load", load)):
        if text.count(marker) != 1:
            errors.append(f"single exact {name} marker missing")

    complete = re.search(
        rf"{re.escape(PREFIX)} qualification_complete activations_completed=(\d+) "
        r"elapsed_ms=(\d+) verbose_records_follow=1",
        text,
    )
    completed = int(complete.group(1)) if complete else 0
    elapsed_ms = int(complete.group(2)) if complete else 0
    if complete is None or completed != 16:
        errors.append("qualification is not exactly 16 completed activations")

    qualification = [
        _record(match, qualification=True)
        for match in QUALIFICATION_STEP_RE.finditer(text)
    ]
    if text.count(f"{PREFIX} qualification_step=") != 16 or len(qualification) != 16:
        errors.append("qualification trace does not contain exactly 16 records")
    if complete and qualification and qualification[0]["index"] == 1:
        first_match = QUALIFICATION_STEP_RE.search(text)
        if first_match and first_match.start() < complete.end():
            errors.append("qualification detail appeared before qualification_complete")

    for offset, record in enumerate(qualification[:16]):
        observed = tuple(
            record[key]
            for key in ("index", "previous", "current", "ww", "wb", "bw", "bb")
        )
        if observed != EXPECTED[offset]:
            errors.append(f"qualification step {offset + 1} transition oracle differs")
        if sum(int(record[key]) for key in ("ww", "wb", "bw", "bb")) != 1024:
            errors.append(f"qualification step {offset + 1} does not cover 32x32")
        if record["busy_complete"] != 1 or not 1 <= int(record["busy_ms"]) <= 600:
            errors.append(f"qualification step {offset + 1} BUSY exceeds 600 ms")
        if record["post_sync_bytes"] != 128:
            errors.append(f"qualification step {offset + 1} post-sync differs")
        if record["lut_sha256"] != LUT_SHA or record["step_ok"] != 1:
            errors.append(f"qualification step {offset + 1} identity/transport differs")

    result_re = re.compile(
        rf"{re.escape(PREFIX)} qualification_result=ok activations_completed=16 controls_cf=16 "
        r"refresh_20=16 busy_completions=16 writes_26=16 stage_writes_24=16 post_sync_24=16 "
        r"post_sync_refresh=0 local_bytes_each=128 final_local_state=white full_frame_writes=0 "
        r"full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 lut_loads=1 "
        r"voltage_tail_changes=0 retries=0 motion_120_frame=0 qualification_elapsed_ms=(\d+) "
        r"bus_retained_for_loop=1"
    )
    result = result_re.search(text)
    if result is None or int(result.group(1)) != elapsed_ms:
        errors.append("exact qualification result/count marker missing")

    ready = (
        f"{PREFIX} observation_ready loop_limit=none next_previous=W next_current=A "
        "telemetry_storage=host_ring_65536"
    )
    if text.count(ready) != 1:
        errors.append("single observation_ready marker missing")
    elif result and text.index(ready) < result.end():
        errors.append("observation_ready preceded qualification PASS")

    if f"{PREFIX} qualification_result=no_go" in text:
        errors.append("qualification emitted no_go")
    if f"{PREFIX} loop_fault" in text:
        errors.append("continuous loop emitted a fault")

    loop = [_record(match, qualification=False) for match in LOOP_RE.finditer(text)]
    if text.count(f"{PREFIX} loop_iteration=") != len(loop):
        errors.append("one or more loop records are malformed")
    previous_index: int | None = None
    for offset, record in enumerate(loop):
        index = int(record["index"])
        expected_previous = "W" if index == 1 else ("A" if index % 2 == 0 else "B")
        expected_current = "B" if index % 2 == 0 else "A"
        expected_classes = (512, 512, 0, 0) if index == 1 else (256, 256, 256, 256)
        if (record["previous"], record["current"]) != (expected_previous, expected_current):
            errors.append(f"loop record {offset + 1} pattern sequence differs")
        if tuple(record[key] for key in ("ww", "wb", "bw", "bb")) != expected_classes:
            errors.append(f"loop record {offset + 1} transition classes differ")
        if previous_index is not None and index != previous_index + 1:
            errors.append(f"loop record {offset + 1} iteration is not contiguous")
        previous_index = index
        if record["busy_complete"] != 1 or not 1 <= int(record["busy_ms"]) <= 600:
            errors.append(f"loop record {offset + 1} BUSY exceeds 600 ms")
        if record["post_sync_bytes"] != 128:
            errors.append(f"loop record {offset + 1} post-sync differs")
        if record["lut_sha256"] != LUT_SHA or record["step_ok"] != 1:
            errors.append(f"loop record {offset + 1} identity/transport differs")

    qualification_busy = [int(item["busy_ms"]) for item in qualification]
    loop_busy = [int(item["busy_ms"]) for item in loop]
    return {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous_trace.v1",
        "status": "PASS_MACHINE_R9_CONTINUOUS_TRACE" if not errors else "NO_GO_R9_CONTINUOUS_TRACE",
        "errors": errors,
        "hardware_contact": hardware_contact,
        "qualification": {
            "historical_r9_result_changed": False,
            "activations": len(qualification),
            "elapsed_ms": elapsed_ms,
            "busy_max_ms": max(qualification_busy, default=None),
            "passed_before_loop": result is not None and text.count(ready) == 1,
        },
        "loop": {
            "preset_iteration_limit": None,
            "records_in_ring": len(loop),
            "first_iteration": loop[0]["index"] if loop else None,
            "last_iteration": loop[-1]["index"] if loop else None,
            "busy_max_ms": max(loop_busy, default=None),
            "fixed_bank": {"old_command": "0x26", "old_selector": 1, "new_command": "0x24", "new_selector": 0},
            "control": "0xCF",
            "refresh": "0x20",
            "post_sync": "0x24",
        },
        "candidate": {"lut_sha256": LUT_SHA, "workbench_sha256": WORKBENCH_SHA},
        "forbidden": {"full_frame": 0, "0xF7": 0, "0xC7": 0, "0xFF": 0, "retry": 0, "motion_120_frame": 0},
        "production_allowed": False,
    }


def fixture(loop_records: int = 3) -> str:
    elapsed = 9584
    lines = [
        f"{PREFIX} armed qualification_activations=16 loop_limit=none popup_commands=0 telemetry_storage=host_ring_65536",
        f"{PREFIX} start candidate=source_field_reorder_phase_parallel_r9 lut_sha256={LUT_SHA} "
        f"workbench_sha256={WORKBENCH_SHA} source_sha256={SOURCE_SHA} window_x_bytes=1-4 "
        "window_y=8-39 window_bytes=128 old_command=0x26 old_selector=1 new_command=0x24 "
        "new_selector=0 post_sync_command=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 "
        "full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 "
        "voltage_tail=221741A83258 retries=0 motion_120_frame=0 production_enabled=0",
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={LUT_SHA} loaded=1",
        f"{PREFIX} qualification_complete activations_completed=16 elapsed_ms={elapsed} verbose_records_follow=1",
    ]
    for step, previous, current, ww, wb, bw, bb in EXPECTED:
        lines.append(
            f"{PREFIX} qualification_step={step} previous={previous} current={current} ww={ww} wb={wb} bw={bw} bb={bb} "
            "old_command=0x26 old_selector=1 old_bytes=128 new_command=0x24 new_selector=0 new_bytes=128 "
            "control=0xCF refresh=0x20 busy_complete=1 busy_elapsed_ms=599 post_sync_command=0x24 "
            f"post_sync_bytes=128 post_sync_refresh=0 lut_sha256={LUT_SHA} step_ok=1"
        )
    lines.extend(
        [
            f"{PREFIX} qualification_result=ok activations_completed=16 controls_cf=16 refresh_20=16 "
            "busy_completions=16 writes_26=16 stage_writes_24=16 post_sync_24=16 post_sync_refresh=0 "
            "local_bytes_each=128 final_local_state=white full_frame_writes=0 full_refreshes=0 controls_ff=0 "
            "controls_f7=0 controls_c7=0 lut_loads=1 voltage_tail_changes=0 retries=0 motion_120_frame=0 "
            f"qualification_elapsed_ms={elapsed} bus_retained_for_loop=1",
            f"{PREFIX} observation_ready loop_limit=none next_previous=W next_current=A telemetry_storage=host_ring_65536",
        ]
    )
    for iteration in range(1, loop_records + 1):
        previous = "W" if iteration == 1 else ("A" if iteration % 2 == 0 else "B")
        current = "B" if iteration % 2 == 0 else "A"
        classes = (512, 512, 0, 0) if iteration == 1 else (256, 256, 256, 256)
        lines.append(
            f"{PREFIX} loop_iteration={iteration} previous={previous} current={current} ww={classes[0]} wb={classes[1]} "
            f"bw={classes[2]} bb={classes[3]} old_command=0x26 old_selector=1 old_bytes=128 new_command=0x24 "
            "new_selector=0 new_bytes=128 control=0xCF refresh=0x20 busy_complete=1 busy_elapsed_ms=599 "
            f"post_sync_command=0x24 post_sync_bytes=128 post_sync_refresh=0 lut_sha256={LUT_SHA} "
            "full_frame_writes=0 controls_ff=0 controls_f7=0 controls_c7=0 retries=0 motion_120_frame=0 step_ok=1"
        )
    return "\n".join(lines)


def self_test() -> dict[str, object]:
    good = fixture()
    cases = {
        "missing_qualification_step": good.replace(f"{PREFIX} qualification_step=16", f"{PREFIX} omitted=16", 1),
        "qualification_busy_over_limit": good.replace("busy_elapsed_ms=599", "busy_elapsed_ms=601", 1),
        "loop_busy_over_limit": good.rsplit("busy_elapsed_ms=599", 1)[0] + "busy_elapsed_ms=601" + good.rsplit("busy_elapsed_ms=599", 1)[1],
        "missing_post_sync": good.replace("post_sync_bytes=128", "post_sync_bytes=0", 1),
        "wrong_lut": good.replace(LUT_SHA, "0" * 64, 1),
        "fault_marker": good + f"\n{PREFIX} loop_fault iteration=4 busy_elapsed_ms=601 reason=transport_or_busy_timeout loop_stopped=1 gpio_restore=1",
        "malformed_loop": good.replace("old_selector=1", "old_selector=0", 1),
        "noncontiguous_loop": good.replace("loop_iteration=3", "loop_iteration=4", 1),
    }
    good_result = evaluate(good, hardware_contact=0)
    rejected = {name: bool(evaluate(value, hardware_contact=0)["errors"]) for name, value in cases.items()}
    passed = good_result["status"] == "PASS_MACHINE_R9_CONTINUOUS_TRACE" and all(rejected.values())
    return {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous_parser_selftest.v1",
        "status": "PASS" if passed else "FAIL",
        "hardware_contact": 0,
        "positive_fixture": good_result["status"],
        "negative_cases_rejected": rejected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--hardware-contact", type=int, choices=(0, 1), default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    else:
        if args.log is None:
            parser.error("--log is required unless --self-test is used")
        result = evaluate(args.log.read_text(encoding="utf-8", errors="replace"), hardware_contact=args.hardware_contact)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
