#!/usr/bin/env python3
"""Verify an external-pack expression animation and clean menu restore."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=pathlib.Path)
    parser.add_argument("--revision", required=True, type=int)
    parser.add_argument("--pack-frames", required=True, type=int)
    parser.add_argument("--expression", required=True)
    parser.add_argument("--frame-indices", required=True, type=int, nargs="+")
    parser.add_argument("--dirty", required=True, type=int, nargs=4)
    parser.add_argument("--require-marker", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.log.is_file():
        print(f"ERROR: runtime log does not exist: {args.log}")
        return 1
    if len(args.frame_indices) < 2:
        print("ERROR: provide the intro and at least one loop frame")
        return 1

    content = args.log.read_text(encoding="utf-8", errors="replace")
    boot_marker = (
        "pack=emote-matrix-white-200x200-v1 "
        f"revision={args.revision} clips=30 frames={args.pack_frames}"
    )
    boot_offset = content.rfind(boot_marker)
    if boot_offset < 0:
        print(f"ERROR: missing {boot_marker}")
        return 1
    runtime = content[boot_offset:]

    errors: list[str] = []
    dirty_marker = ",".join(str(value) for value in args.dirty)
    required = [
        f"scene=expression name={args.expression} frame_index={args.frame_indices[0]}",
        f"dirty={dirty_marker} source=external_flash",
        "refresh mode=full control=0xF7",
        "refresh mode=partial control=0xFF",
        "selected=full reason=4 partial_count=5/5 baseline=1",
        "presentation=restore_menu view=0 page=0 language=1",
        "scene=menu asset=menu.home.zh source=external_flash",
    ]
    for in_clip, frame_index in enumerate(args.frame_indices):
        phase = 1 if in_clip == 0 else 2
        required.append(
            f"clip={args.expression} frame={frame_index} "
            f"in_clip={in_clip} phase={phase}"
        )
    required.extend(args.require_marker)
    for marker in required:
        if marker not in runtime:
            errors.append(f"missing runtime marker: {marker}")

    restore = runtime.find("presentation=restore_menu")
    menu = runtime.find("scene=menu asset=menu.home.zh", restore)
    if restore < 0 or menu < 0:
        errors.append("could not locate the restore-menu interval")
    elif "scene=expression" in runtime[restore:menu]:
        errors.append("stale expression frame was queued between restore_menu and menu")

    failure_patterns = {
        "nonzero queue result": r"queue=(?!0\b)\d+",
        "incomplete refresh": r"complete=0",
        "panel ready timeout": r"ready_wait[^\r\n]*ready=0",
    }
    for label, pattern in failure_patterns.items():
        if re.search(pattern, runtime):
            errors.append(f"runtime contains {label}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        f"PASS: revision {args.revision} {args.expression} animation, "
        "refresh policy, and clean menu restore verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
