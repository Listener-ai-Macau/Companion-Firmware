#!/usr/bin/env python3
"""Verify a reset-bounded V9 screen-tap manual-step diagnostic serial trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_ID = "companion.wb55.v9_manual_step_diagnostic_trace.v1"
EXPECTED_STEPS = (1, 2, 3, 0)
STEP_RE = re.compile(
    r"\[v9-manual-step\] result=queued step=(?P<step>[0-3]) "
    r"clip=(?P<clip>idle|touch|swipe_left|swipe_right) frame=2 refresh=full "
    r"player=stopped source=locked_v9_cemp"
)
TAP_RE = re.compile(
    r"\[touch-ui\] v9_manual_step result=(?P<result>queued|rejected) "
    r"source=screen_tap x=(?P<x>\d+) y=(?P<y>\d+)"
)
REFRESH_RE = re.compile(
    r"\[epaper\] refresh mode=full profile=(?P<profile>\S+) control=0x(?P<control>[0-9A-Fa-f]{2}) "
    r"expected_visible_flicker=(?P<flicker>\S+) activation_count=(?P<count>\d+) "
    r"busy=(?P<busy>-?\d+) update=(?P<update>\d+) activate=(?P<activate>\d+) "
    r"complete=(?P<complete>\d+) elapsed_ms=(?P<elapsed>\d+)"
)
TIMING_RE = re.compile(
    r"\[epaper\] timing mode=full .* bytes=(?P<bytes>\d+) data_planes=(?P<planes>\d+)"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def evaluate(text: str) -> dict[str, Any]:
    steps = [
        {"step": int(match["step"]), "clip": match["clip"]}
        for match in STEP_RE.finditer(text)
    ]
    taps = [match.groupdict() for match in TAP_RE.finditer(text)]
    refreshes = [
        {
            "profile": match["profile"],
            "control": f"0x{match['control'].upper()}",
            "complete": int(match["complete"]),
            "elapsed_ms": int(match["elapsed"]),
            "update": int(match["update"]),
            "activate": int(match["activate"]),
        }
        for match in REFRESH_RE.finditer(text)
    ]
    timings = [
        {"bytes": int(match["bytes"]), "data_planes": int(match["planes"])}
        for match in TIMING_RE.finditer(text)
    ]
    checks = {
        "exactly_four_accepted_screen_taps": len(taps) == 4
        and all(tap["result"] == "queued" for tap in taps),
        "exactly_four_deterministic_step_clips": len(steps) == 5
        and [entry["step"] for entry in steps] == [0, *EXPECTED_STEPS]
        and [entry["clip"] for entry in steps]
        == ["idle", "touch", "swipe_left", "swipe_right", "idle"],
        "no_rejected_or_blocked_step": "[v9-manual-step] result=blocked" not in text
        and "[touch-ui] v9_manual_step result=rejected" not in text,
        "five_completed_full_refreshes": len(refreshes) >= 5
        and all(
            refresh["control"] == "0xF7"
            and refresh["complete"] == 1
            and refresh["update"] == 1
            and refresh["activate"] == 1
            and refresh["elapsed_ms"] <= 5000
            for refresh in refreshes
        ),
        "two_plane_full_frame_transfer": len(timings) >= 5
        and all(timing["bytes"] == 5000 and timing["data_planes"] == 2 for timing in timings),
        "no_panel_failure_marker": "[epaper] fail " not in text,
        "no_board_button_advance": "[v9-manual-step] action=ignored source=board_button" not in text,
    }
    return {
        "checks": checks,
        "steps": steps,
        "screen_taps": taps,
        "refreshes": refreshes,
        "timings": timings,
        "failures": [name for name, passed in checks.items() if not passed],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    if not log_path.is_file():
        print(f"NO_GO: serial log missing: {log_path}", file=sys.stderr)
        return 1
    result = evaluate(load_text(log_path))
    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_SCREEN_TAP_TO_FULL_REFRESH_TRACE_NOT_VISUAL_ACCEPTANCE"
        if not result["failures"]
        else "NO_GO_MANUAL_STEP_TRACE_INCOMPLETE",
        "claim_scope": "controlled_locked_v9_static_panel_comparator_not_product_animation_or_panel_recovery",
        "expected_short_taps": 4,
        "expected_sequence_after_boot": ["touch", "swipe_left", "swipe_right", "idle"],
        "log": {"path": rel(log_path), "sha256": sha256(log_path)},
        **result,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["failures"]:
        print(f"NO_GO: V9 manual-step serial trace -> {rel(destination)}", file=sys.stderr)
        return 1
    print(f"PASS: V9 manual-step serial trace -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
