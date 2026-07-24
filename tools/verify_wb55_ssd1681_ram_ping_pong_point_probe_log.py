#!/usr/bin/env python3
"""Machine oracle for the 24-frame SSD1681 ping-pong point probe."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FRAME_RE = re.compile(
    r"\[epaper\] ping_pong_probe frame=(\d+) x=(\d+) y=(\d+) size=(\d+) "
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
    for index in range(24):
        x = 60 + index * 2 if index < 12 else 60 + (22 - index) * 2
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


def evaluate(text: str) -> dict:
    errors: list[str] = []
    matches = list(FRAME_RE.finditer(text))
    expected = expected_frames()
    frames = []
    for match in matches:
        values = [int(value) for value in match.groups()]
        frame = dict(zip((
            "frame", "x", "y", "size", "x0", "x1", "y0", "y1", "changed",
            "oracle", "stage", "busy_complete", "busy_ms", "interval_ms",
            "sync", "frame_ok",
        ), values))
        frames.append(frame)

    if len(frames) != 24:
        errors.append(f"expected 24 frame records, got {len(frames)}")
    if [frame["frame"] for frame in frames] != list(range(1, 25)):
        errors.append("frame sequence is not exactly 1..24")
    for index, frame in enumerate(frames[:24]):
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
        elif not (600 <= frame["interval_ms"] <= 1000):
            errors.append(f"frame {index + 1} interval outside 600..1000 ms")

    start_ok = re.search(
        r"ping_pong_probe start frames=24 point=12x12 geometry_role=diagnostic_only "
        r"diff=generic_previous_current stage_bank=0x24 post_sync_bank=0x24 "
        r"motion_0x26_writes=0 control=0xFF refresh=0x20 target_spacing_ms=800 "
        r"full_refreshes=0 f7=0 c7=0 lut_writes=0 retries=0",
        text,
    ) is not None
    seed_ok = "ping_pong_probe seed banks=0x24,0x26 bytes_each=5000 activation=0 ok=1" in text
    result_ok = re.search(
        r"ping_pong_probe result=ok frames=24 controls_ff=24 refresh_20=24 "
        r"busy_completions=24 motion_0x26_writes=0 post_sync_24=24 "
        r"post_sync_refresh=0 full_refreshes=0 controls_f7=0 controls_c7=0 "
        r"lut_writes=0 retries=0 gpio_restore=1 sda=0 sck=0 cs=1",
        text,
    ) is not None
    if not start_ok:
        errors.append("start contract marker missing")
    if not seed_ok:
        errors.append("non-activating initial RAM seed marker missing")
    if not result_ok:
        errors.append("result/count/GPIO marker missing")

    return {
        "schema_id": "companion.ssd1681.ram_ping_pong_point_probe.v1",
        "status": "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE" if not errors else "NO_GO_RAM_PING_PONG_POINT_PROBE",
        "errors": errors,
        "contract": {
            "frames": 24,
            "motion_0x26_writes": 0,
            "controls_ff": 24,
            "refresh_0x20": 24,
            "busy_completions": 24,
            "post_activation_0x24_sync_without_refresh": 24,
            "full_refreshes": 0,
            "controls_f7": 0,
            "controls_c7": 0,
            "lut_writes": 0,
            "automatic_retries": 0,
            "frame_spacing_ms": [600, 1000],
            "busy_max_ms": 1000,
        },
        "observed": {
            "frame_records": len(frames),
            "busy_ms": [frame["busy_ms"] for frame in frames],
            "interval_ms": [frame["interval_ms"] for frame in frames],
            "stage_bytes": [frame["stage"] for frame in frames],
            "post_sync_bytes": [frame["sync"] for frame in frames],
        },
        "mapping_basis": "Phase A uniquely proved activation swaps staged selector0/0x24 current into selector1 while selector0 becomes previous; post-activation 0x24 current sync restores both banks without another activation.",
        "claims_not_made": ["no visual acceptance", "no production admission", "no LUT/waveform/temperature/voltage/Rig/CRIG/touch/BLE claim"],
    }


def fixture() -> str:
    lines = [
        "[epaper] ping_pong_probe start frames=24 point=12x12 geometry_role=diagnostic_only diff=generic_previous_current stage_bank=0x24 post_sync_bank=0x24 motion_0x26_writes=0 control=0xFF refresh=0x20 target_spacing_ms=800 full_refreshes=0 f7=0 c7=0 lut_writes=0 retries=0",
        "[epaper] ping_pong_probe seed banks=0x24,0x26 bytes_each=5000 activation=0 ok=1",
    ]
    for item in expected_frames():
        interval = 0 if item["frame"] == 1 else 820
        lines.append(
            f"[epaper] ping_pong_probe frame={item['frame']} x={item['x']} y=94 size=12 "
            f"window_x_bytes={item['x0']}-{item['x1']} window_y={item['y0']}-{item['y1']} "
            f"changed_bytes={item['changed']} oracle_bytes={item['oracle']} "
            f"stage_command=0x24 stage_bytes={item['oracle']} control=0xFF refresh=0x20 "
            f"busy_complete=1 busy_elapsed_ms=447 interval_ms={interval} "
            f"post_sync_command=0x24 post_sync_bytes={item['oracle']} post_sync_refresh=0 frame_ok=1"
        )
    lines.append("[epaper] ping_pong_probe result=ok frames=24 controls_ff=24 refresh_20=24 busy_completions=24 motion_0x26_writes=0 post_sync_24=24 post_sync_refresh=0 full_refreshes=0 controls_f7=0 controls_c7=0 lut_writes=0 retries=0 gpio_restore=1 sda=0 sck=0 cs=1")
    return "\n".join(lines)


def self_test() -> int:
    good = evaluate(fixture())
    missing = evaluate(fixture().replace("[epaper] ping_pong_probe frame=24", "[other] frame=24"))
    timing = evaluate(fixture().replace("interval_ms=820", "interval_ms=1001", 1))
    transfer = evaluate(fixture().replace("stage_bytes=36", "stage_bytes=35", 1))
    motion_26 = evaluate(fixture().replace("motion_0x26_writes=0", "motion_0x26_writes=1", 1))
    ok = (good["status"] == "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE" and
          all(item["status"] == "NO_GO_RAM_PING_PONG_POINT_PROBE"
              for item in (missing, timing, transfer, motion_26)))
    print("PASS: point-probe parser positive/missing/timing/transfer/0x26 fixtures" if ok
          else "FAIL: point-probe parser self-test")
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
    return 0 if result["status"] == "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE" else 1


if __name__ == "__main__":
    sys.exit(main())
