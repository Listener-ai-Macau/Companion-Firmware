#!/usr/bin/env python3
"""Verify one direction of the WB55 pet-stroke hardware probe."""

from __future__ import annotations

import argparse
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_LOG = pathlib.Path(
    ".cache/validation/screen-revision31-directional-stroke-probe/nucleo-serial-raw.log"
)
PROBES = {
    "left": {
        "start": "180,100",
        "end": "20,100",
        "pose": ("gaze=-32,0", "brow=2 lift=12 asym=-9 mouth=5 mouth_scale=78 cheek=3"),
    },
    "right": {
        "start": "20,100",
        "end": "180,100",
        "pose": ("gaze=32,0", "brow=2 lift=12 asym=9 mouth=5 mouth_scale=78 cheek=3"),
    },
    "up": {
        "start": "100,180",
        "end": "100,20",
        "pose": ("gaze=0,-32", "brow=2 lift=20 asym=0 mouth=5 mouth_scale=86 cheek=3 mark=4"),
    },
    "down": {
        "start": "100,20",
        "end": "100,180",
        "pose": ("gaze=0,30", "brow=3 lift=6 asym=0 mouth=1 mouth_scale=112 cheek=3"),
    },
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path, default=DEFAULT_LOG)
    parser.add_argument("--direction", choices=tuple(PROBES), default="down")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    path = ROOT / args.log
    if not path.is_file():
        print(f"pet stroke runtime: FAIL\n  - missing log: {path}")
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    probe = PROBES[args.direction]
    start = probe["start"]
    end = probe["end"]
    daily_demo_marker = (
        f"[screen] daily_stroke_demo direction={args.direction} start={start} end={end} duration_ms=600"
    )
    # Revision 31's first down-stroke capture predates the explicit direction
    # field. Keep that board evidence valid while requiring it in new probes.
    if args.direction == "down" and daily_demo_marker not in text:
        daily_demo_marker = "[screen] daily_stroke_demo start=100,20 end=100,180 duration_ms=600"
    for marker in (
        "[screen] pet_behavior_selftest=pass",
        "memory=pass strokes=pass",
        daily_demo_marker,
        f"[pet-stroke] direction={args.direction} start={start} end={end} duration_ms=600",
        f"[epaper] scene=pet state=happy {probe['pose'][0]}",
        probe["pose"][1],
        "[touch-health] detected=1",
        "errors=0",
        "wait_buffer_selftest=1",
    ):
        if marker not in text:
            errors.append(f"missing marker: {marker}")
    if text.count("refresh mode=full control=0xF7") != 1:
        errors.append("probe must establish exactly one full refresh baseline")
    differential_count = text.count("refresh mode=differential control=0xFC")
    if differential_count < 3:
        errors.append(f"directional response used only {differential_count} differential refreshes")
    if errors:
        print("pet stroke runtime: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("pet stroke runtime: PASS")
    print(
        f"  {args.direction}-stroke full-face response reached the real SSD1681 via {differential_count} differential refreshes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
