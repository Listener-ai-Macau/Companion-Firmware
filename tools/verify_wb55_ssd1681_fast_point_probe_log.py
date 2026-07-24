#!/usr/bin/env python3
"""Machine oracle for the 120-frame SSD1681 fast point probe."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


POSITIONS = (52, 60, 68, 76, 84, 76, 68, 60)
FRAME_RE = re.compile(
    r"\[epaper\] fast_probe frame=(\d+) x=(\d+) y=(\d+) size=(\d+) "
    r"window_x_bytes=(\d+)-(\d+) window_y=(\d+)-(\d+) changed_bytes=(\d+) "
    r"oracle_bytes=(\d+) stage_command=0x24 stage_bytes=(\d+) control=0xFF "
    r"refresh=0x20 busy_complete=([01]) busy_elapsed_ms=(\d+) interval_ms=(\d+) "
    r"post_sync_command=0x24 post_sync_bytes=(\d+) post_sync_refresh=0 frame_ok=([01])"
)


def draw(x_start: int) -> bytes:
    frame = bytearray([0xFF] * 5000)
    for y in range(94, 106):
        for x in range(x_start, x_start + 12):
            frame[y * 25 + x // 8] &= ~(0x80 >> (x & 7)) & 0xFF
    return bytes(frame)


def expected_frames() -> list[dict]:
    previous = bytes([0xFF]) * 5000
    expected = []
    for index in range(120):
        x = POSITIONS[index % len(POSITIONS)]
        current = draw(x)
        changed = [i for i, pair in enumerate(zip(previous, current)) if pair[0] != pair[1]]
        xs = [i % 25 for i in changed]
        ys = [i // 25 for i in changed]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        expected.append({
            "frame": index + 1,
            "x": x,
            "y": 94,
            "size": 12,
            "x0": x0,
            "x1": x1,
            "y0": y0,
            "y1": y1,
            "changed": len(changed),
            "oracle": (x1 - x0 + 1) * (y1 - y0 + 1),
        })
        previous = current
    return expected


def percentile95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1] if ordered else 0


def evaluate(text: str) -> dict:
    errors: list[str] = []
    frames = []
    for match in FRAME_RE.finditer(text):
        values = [int(value) for value in match.groups()]
        frames.append(dict(zip((
            "frame", "x", "y", "size", "x0", "x1", "y0", "y1", "changed",
            "oracle", "stage", "busy_complete", "busy_ms", "interval_ms",
            "sync", "frame_ok",
        ), values)))

    expected = expected_frames()
    if len(frames) != 120:
        errors.append(f"expected 120 frame records, got {len(frames)}")
    if [frame["frame"] for frame in frames] != list(range(1, 121)):
        errors.append("frame sequence is not exactly 1..120")
    for index, frame in enumerate(frames[:120]):
        oracle = expected[index]
        for key in ("frame", "x", "y", "size", "x0", "x1", "y0", "y1", "changed", "oracle"):
            if frame[key] != oracle[key]:
                errors.append(f"frame {index + 1} {key}={frame[key]} expected={oracle[key]}")
        if not (0 <= frame["x0"] <= frame["x1"] < 25 and
                0 <= frame["y0"] <= frame["y1"] < 200):
            errors.append(f"frame {index + 1} window outside 200x200")
        if frame["stage"] != frame["oracle"] or frame["sync"] != frame["oracle"]:
            errors.append(f"frame {index + 1} transfer bytes differ from oracle")
        if frame["busy_complete"] != 1 or frame["frame_ok"] != 1:
            errors.append(f"frame {index + 1} transport or BUSY failed")
        if frame["busy_ms"] > 1000:
            errors.append(f"frame {index + 1} BUSY exceeds 1000 ms")
        if index == 0:
            if frame["interval_ms"] != 0:
                errors.append("first frame interval must be zero sentinel")
        elif not (475 <= frame["interval_ms"] <= 550):
            errors.append(f"frame {index + 1} interval outside 475..550 ms")

    intervals = [frame["interval_ms"] for frame in frames[1:]]
    p95_ms = percentile95(intervals)
    if intervals and p95_ms > 600:
        errors.append(f"frame interval p95 {p95_ms} exceeds 600 ms")
    countdowns = [int(value) for value in re.findall(
        r"fast_probe countdown=(\d+) screen_commands=0 screen_refreshes=0", text
    )]
    if countdowns != [3, 2, 1]:
        errors.append(f"non-screen countdown must be exactly 3,2,1; got {countdowns}")
    if text.count("fast_probe start_signal=1 screen_commands=0 screen_refreshes=0") != 1:
        errors.append("single non-screen start signal missing")
    start_ok = re.search(
        r"fast_probe start frames=120 point=12x12 geometry_role=diagnostic_only "
        r"diff=generic_previous_current stage_bank=0x24 post_sync_bank=0x24 "
        r"motion_0x26_writes=0 control=0xFF refresh=0x20 target_spacing_ms=500 "
        r"step_px=8 excursion_px=32 full_refreshes=0 f7=0 c7=0 lut_writes=0 retries=0",
        text,
    ) is not None
    seed_ok = "fast_probe seed banks=0x24,0x26 bytes_each=5000 activation=0 ok=1" in text
    result_match = re.search(
        r"fast_probe result=ok frames=120 controls_ff=120 refresh_20=120 "
        r"busy_completions=120 motion_0x26_writes=0 post_sync_24=120 "
        r"post_sync_refresh=0 full_refreshes=0 controls_f7=0 controls_c7=0 "
        r"lut_writes=0 retries=0 motion_elapsed_ms=(\d+) gpio_restore=1 sda=0 sck=0 cs=1",
        text,
    )
    motion_elapsed_ms = int(result_match.group(1)) if result_match else 0
    if not start_ok:
        errors.append("start contract marker missing")
    if not seed_ok:
        errors.append("non-activating initial RAM seed marker missing")
    if result_match is None:
        errors.append("result/count/GPIO marker missing")
    elif not (57000 <= motion_elapsed_ms <= 70000):
        errors.append(f"motion elapsed {motion_elapsed_ms} outside 57000..70000 ms")
    xs = [frame["x"] for frame in frames]
    if xs and (min(xs) != 52 or max(xs) != 84 or max(xs) - min(xs) < 32):
        errors.append("trajectory does not prove at least 32 px excursion")
    if len(xs) > 1 and any(abs(current - previous) != 8 for previous, current in zip(xs, xs[1:])):
        errors.append("trajectory contains a step other than 8 px")

    return {
        "schema_id": "companion.ssd1681.fast_point_probe.v1",
        "status": "PASS_MACHINE_SSD1681_FAST_POINT_PROBE" if not errors else "NO_GO_SSD1681_FAST_POINT_PROBE",
        "errors": errors,
        "contract": {
            "frames": 120,
            "trajectory_px": list(POSITIONS),
            "step_px": 8,
            "excursion_px": 32,
            "motion_0x26_writes": 0,
            "controls_ff": 120,
            "refresh_0x20": 120,
            "busy_completions": 120,
            "post_activation_0x24_sync_without_refresh": 120,
            "full_refreshes": 0,
            "frame_interval_ms": [475, 550],
            "frame_interval_p95_max_ms": 600,
            "motion_elapsed_ms": [57000, 70000],
        },
        "observed": {
            "frame_records": len(frames),
            "busy_ms": [frame["busy_ms"] for frame in frames],
            "interval_ms": [frame["interval_ms"] for frame in frames],
            "interval_p95_ms": p95_ms,
            "motion_elapsed_ms": motion_elapsed_ms,
            "stage_bytes": [frame["stage"] for frame in frames],
            "post_sync_bytes": [frame["sync"] for frame in frames],
        },
        "mapping_basis": "Phase A proved post-activation selector0/0x24 no-refresh current sync restores both RAM banks current.",
        "claims_not_made": ["no visual acceptance", "no production admission", "no custom LUT/waveform/temperature/Rig/CRIG/touch/BLE claim"],
    }


def fixture() -> str:
    lines = [
        "[epaper] fast_probe countdown=3 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe countdown=2 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe countdown=1 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe start_signal=1 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe start frames=120 point=12x12 geometry_role=diagnostic_only diff=generic_previous_current stage_bank=0x24 post_sync_bank=0x24 motion_0x26_writes=0 control=0xFF refresh=0x20 target_spacing_ms=500 step_px=8 excursion_px=32 full_refreshes=0 f7=0 c7=0 lut_writes=0 retries=0",
        "[epaper] fast_probe seed banks=0x24,0x26 bytes_each=5000 activation=0 ok=1",
    ]
    for item in expected_frames():
        interval = 0 if item["frame"] == 1 else 522
        lines.append(
            f"[epaper] fast_probe frame={item['frame']} x={item['x']} y=94 size=12 "
            f"window_x_bytes={item['x0']}-{item['x1']} window_y={item['y0']}-{item['y1']} "
            f"changed_bytes={item['changed']} oracle_bytes={item['oracle']} "
            f"stage_command=0x24 stage_bytes={item['oracle']} control=0xFF refresh=0x20 "
            f"busy_complete=1 busy_elapsed_ms=447 interval_ms={interval} "
            f"post_sync_command=0x24 post_sync_bytes={item['oracle']} post_sync_refresh=0 frame_ok=1"
        )
    lines.append("[epaper] fast_probe result=ok frames=120 controls_ff=120 refresh_20=120 busy_completions=120 motion_0x26_writes=0 post_sync_24=120 post_sync_refresh=0 full_refreshes=0 controls_f7=0 controls_c7=0 lut_writes=0 retries=0 motion_elapsed_ms=62118 gpio_restore=1 sda=0 sck=0 cs=1")
    return "\n".join(lines)


def self_test() -> int:
    good = evaluate(fixture())
    missing = evaluate(fixture().replace("[epaper] fast_probe frame=120", "[other] frame=120"))
    timing = evaluate(fixture().replace("interval_ms=522", "interval_ms=551", 1))
    transfer = evaluate(fixture().replace("stage_bytes=24", "stage_bytes=23", 1))
    motion_26 = evaluate(fixture().replace("motion_0x26_writes=0", "motion_0x26_writes=1", 1))
    countdown = evaluate(fixture().replace("countdown=2", "countdown=3", 1))
    ok = (good["status"] == "PASS_MACHINE_SSD1681_FAST_POINT_PROBE" and
          all(item["status"] == "NO_GO_SSD1681_FAST_POINT_PROBE"
              for item in (missing, timing, transfer, motion_26, countdown)))
    print("PASS: fast-point parser positive/missing/timing/transfer/0x26/countdown fixtures" if ok
          else "FAIL: fast-point parser self-test")
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
    return 0 if result["status"] == "PASS_MACHINE_SSD1681_FAST_POINT_PROBE" else 1


if __name__ == "__main__":
    sys.exit(main())
