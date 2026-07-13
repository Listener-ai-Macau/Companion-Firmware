#!/usr/bin/env python3
"""Verify real WB55 horizontal gestures reach a completed e-paper refresh."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


def count_ordered(lines: list[str], markers: tuple[str, ...]) -> int:
    marker_index = 0
    completed = 0
    for line in lines:
        if markers[marker_index] not in line:
            continue
        marker_index += 1
        if marker_index == len(markers):
            completed += 1
            marker_index = 0
    return completed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=pathlib.Path)
    parser.add_argument("--min-enter", type=int, default=1)
    parser.add_argument("--min-exit", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.log.exists():
        print(f"FAIL: missing serial log {args.log}", file=sys.stderr)
        return 1

    text = args.log.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    enter_count = count_ordered(lines, (
        "[touch-ui] daily_to_menu gesture=",
        "[screen] menu enqueue",
        "[epaper] scene=menu asset=menu.home.",
        "[epaper] refresh mode=partial control=0xFF busy=0 update=1 activate=1 complete=1",
    ))
    exit_count = count_ordered(lines, (
        "[touch-ui] menu_to_daily",
        "[epaper] scene=expression name=idle",
        "[epaper] refresh mode=partial control=0xFF busy=0 update=1 activate=1 complete=1",
    ))
    left_count = text.count("[touch-ui] gesture=swipe_left")
    right_count = text.count("[touch-ui] gesture=swipe_right")
    incomplete_refreshes = len(re.findall(r"\[epaper\] refresh mode=.*\bcomplete=0\b", text))
    touch_errors = [int(value) for value in re.findall(
        r"\[touch-health\][^\r\n]*\berrors=(\d+)", text
    )]

    errors: list[str] = []
    if enter_count < args.min_enter:
        errors.append(f"menu-entry cycles {enter_count} < required {args.min_enter}")
    if exit_count < args.min_exit:
        errors.append(f"menu-exit cycles {exit_count} < required {args.min_exit}")
    if left_count < args.min_enter:
        errors.append(f"left-swipe events {left_count} < required {args.min_enter}")
    if right_count < args.min_exit:
        errors.append(f"right-swipe events {right_count} < required {args.min_exit}")
    if incomplete_refreshes != 0:
        errors.append(f"found {incomplete_refreshes} incomplete e-paper refreshes")
    if not touch_errors:
        errors.append("missing touch-health error telemetry")
    elif max(touch_errors) != 0:
        errors.append(f"touch-health reported {max(touch_errors)} I2C errors")

    if errors:
        print("FAIL: horizontal gesture runtime evidence rejected:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print(
        "PASS: real horizontal gesture cycles verified "
        f"(left={left_count}, right={right_count}, enter={enter_count}, "
        f"exit={exit_count}, touch_errors={max(touch_errors)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
