#!/usr/bin/env python3
"""Machine oracle for the inverse-seeded 120-frame fast point probe."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from verify_wb55_ssd1681_fast_point_probe_log import FRAME_RE, POSITIONS, draw, percentile95


def initial_previous() -> bytes:
    desired = draw(POSITIONS[0])
    previous = bytearray([0xFF] * 5000)
    for y in range(94, 106):
        for x in range(POSITIONS[0], POSITIONS[4] + 12):
            index = y * 25 + x // 8
            mask = 0x80 >> (x & 7)
            if desired[index] & mask:
                previous[index] &= ~mask & 0xFF
    return bytes(previous)


def expected_frames() -> list[dict]:
    previous = initial_previous()
    expected = []
    for index in range(120):
        x = POSITIONS[index % len(POSITIONS)]
        current = draw(x)
        changed = [i for i, pair in enumerate(zip(previous, current)) if pair[0] != pair[1]]
        xs = [i % 25 for i in changed]
        ys = [i // 25 for i in changed]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        white_to_black = sum((old & ~new & 0xFF).bit_count() for old, new in zip(previous, current))
        black_to_white = sum((~old & new & 0xFF).bit_count() for old, new in zip(previous, current))
        expected.append({
            "frame": index + 1, "x": x, "y": 94, "size": 12,
            "x0": x0, "x1": x1, "y0": y0, "y1": y1,
            "changed": len(changed), "oracle": (x1 - x0 + 1) * (y1 - y0 + 1),
            "white_to_black": white_to_black, "black_to_white": black_to_white,
        })
        previous = current
    return expected


def evaluate(text: str) -> dict:
    errors: list[str] = []
    frames = []
    keys = ("frame", "x", "y", "size", "x0", "x1", "y0", "y1", "changed",
            "oracle", "stage", "busy_complete", "busy_ms", "interval_ms", "sync", "frame_ok")
    for match in FRAME_RE.finditer(text):
        frames.append(dict(zip(keys, (int(value) for value in match.groups()))))
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
        if frame["stage"] != frame["oracle"] or frame["sync"] != frame["oracle"]:
            errors.append(f"frame {index + 1} transfer bytes differ from oracle")
        if frame["busy_complete"] != 1 or frame["frame_ok"] != 1 or frame["busy_ms"] > 1000:
            errors.append(f"frame {index + 1} transport/BUSY failed")
        if index == 0 and frame["interval_ms"] != 0:
            errors.append("first frame interval must be zero sentinel")
        if index > 0 and not (475 <= frame["interval_ms"] <= 550):
            errors.append(f"frame {index + 1} interval outside 475..550 ms")
    if expected[0]["changed"] != 72 or expected[0]["oracle"] != 72 or expected[0]["white_to_black"] != 144 or expected[0]["black_to_white"] != 384:
        errors.append("inverse-seed frame-1 transition contract differs")
    if any(item["changed"] != 36 or item["white_to_black"] != 96 or item["black_to_white"] != 96 for item in expected[1:]):
        errors.append("frames 2..120 transition contract differs")
    intervals = [frame["interval_ms"] for frame in frames[1:]]
    p95_ms = percentile95(intervals)
    if intervals and p95_ms > 600:
        errors.append(f"frame interval p95 {p95_ms} exceeds 600 ms")
    countdowns = [int(value) for value in re.findall(r"fast_probe countdown=(\d+) screen_commands=0 screen_refreshes=0", text)]
    if countdowns != [3, 2, 1] or text.count("fast_probe start_signal=1 screen_commands=0 screen_refreshes=0") != 1:
        errors.append("non-screen countdown/start signal differs")
    start_ok = re.search(
        r"fast_probe start frames=120 point=12x12 geometry_role=diagnostic_only "
        r"diff=generic_previous_current stage_bank=0x24 post_sync_bank=0x24 "
        r"first_previous_plane_seed=local_inverse_corridor motion_0x26_writes=0 "
        r"control=0xFF refresh=0x20 target_spacing_ms=500 step_px=8 excursion_px=32 "
        r"full_refreshes=0 f7=0 c7=0 lut_writes=0 retries=0", text) is not None
    seed_ok = "fast_probe seed current_0x24=frame1 previous_0x26=local_inverse_corridor bytes_each=5000 activation=0 ok=1" in text
    result_match = re.search(
        r"fast_probe result=ok frames=120 controls_ff=120 refresh_20=120 busy_completions=120 "
        r"motion_0x26_writes=0 post_sync_24=120 post_sync_refresh=0 full_refreshes=0 "
        r"controls_f7=0 controls_c7=0 lut_writes=0 retries=0 motion_elapsed_ms=(\d+) "
        r"gpio_restore=1 sda=0 sck=0 cs=1", text)
    motion_elapsed_ms = int(result_match.group(1)) if result_match else 0
    if not start_ok:
        errors.append("inverse-seed start marker missing")
    if not seed_ok:
        errors.append("inverse-seed RAM marker missing")
    if result_match is None or not (57000 <= motion_elapsed_ms <= 70000):
        errors.append("result/count/elapsed/GPIO marker differs")
    return {
        "schema_id": "companion.ssd1681.fast_point_probe_inverse_seed.v1",
        "status": "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_INVERSE_SEED" if not errors else "NO_GO_SSD1681_FAST_POINT_PROBE_INVERSE_SEED",
        "errors": errors,
        "single_variable": "first_frame_previous_plane_seed=local_inverse_corridor",
        "contract": {"frames": 120, "frame_1_dirty_bytes": 72, "frame_1_white_to_black": 144, "frame_1_black_to_white": 384, "later_dirty_bytes": 36, "controls_ff": 120, "refresh_0x20": 120, "post_sync_0x24": 120, "motion_0x26": 0, "full_refreshes": 0, "lut_writes": 0},
        "observed": {"frames": len(frames), "interval_p95_ms": p95_ms, "motion_elapsed_ms": motion_elapsed_ms, "busy_ms": [frame["busy_ms"] for frame in frames], "interval_ms": [frame["interval_ms"] for frame in frames]},
    }


def fixture() -> str:
    lines = [
        "[epaper] fast_probe countdown=3 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe countdown=2 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe countdown=1 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe start_signal=1 screen_commands=0 screen_refreshes=0",
        "[epaper] fast_probe start frames=120 point=12x12 geometry_role=diagnostic_only diff=generic_previous_current stage_bank=0x24 post_sync_bank=0x24 first_previous_plane_seed=local_inverse_corridor motion_0x26_writes=0 control=0xFF refresh=0x20 target_spacing_ms=500 step_px=8 excursion_px=32 full_refreshes=0 f7=0 c7=0 lut_writes=0 retries=0",
        "[epaper] fast_probe seed current_0x24=frame1 previous_0x26=local_inverse_corridor bytes_each=5000 activation=0 ok=1",
    ]
    for item in expected_frames():
        interval = 0 if item["frame"] == 1 else 523
        lines.append(f"[epaper] fast_probe frame={item['frame']} x={item['x']} y=94 size=12 window_x_bytes={item['x0']}-{item['x1']} window_y={item['y0']}-{item['y1']} changed_bytes={item['changed']} oracle_bytes={item['oracle']} stage_command=0x24 stage_bytes={item['oracle']} control=0xFF refresh=0x20 busy_complete=1 busy_elapsed_ms=447 interval_ms={interval} post_sync_command=0x24 post_sync_bytes={item['oracle']} post_sync_refresh=0 frame_ok=1")
    lines.append("[epaper] fast_probe result=ok frames=120 controls_ff=120 refresh_20=120 busy_completions=120 motion_0x26_writes=0 post_sync_24=120 post_sync_refresh=0 full_refreshes=0 controls_f7=0 controls_c7=0 lut_writes=0 retries=0 motion_elapsed_ms=62237 gpio_restore=1 sda=0 sck=0 cs=1")
    return "\n".join(lines)


def self_test() -> int:
    good = evaluate(fixture())
    bad_seed = evaluate(fixture().replace("local_inverse_corridor", "all_white", 1))
    bad_frame = evaluate(fixture().replace("stage_bytes=72", "stage_bytes=71", 1))
    bad_time = evaluate(fixture().replace("interval_ms=523", "interval_ms=551", 1))
    ok = good["status"].startswith("PASS_") and all(item["status"].startswith("NO_GO_") for item in (bad_seed, bad_frame, bad_time))
    print("PASS: inverse-seed parser positive/seed/frame/timing fixtures" if ok else "FAIL: inverse-seed parser self-test")
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
        parser.error("--log and --out required unless --self-test")
    result = evaluate(args.log.read_text(encoding="utf-8", errors="ignore"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    sys.exit(main())
