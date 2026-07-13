#!/usr/bin/env python3
"""Verify the WB55 SSD1681 fast-maintenance hardware log."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = (
    ROOT
    / ".cache/validation/screen-ssd1681-fast-maintenance/nucleo-serial-raw.log"
)
DEFAULT_PRODUCTION_LOG = (
    ROOT
    / ".cache/validation/screen-revision11-fast-maintenance-normal/nucleo-serial-raw.log"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument(
        "--production-log", type=Path, default=DEFAULT_PRODUCTION_LOG
    )
    args = parser.parse_args()

    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    if not log_path.is_file():
        print(f"epaper fast maintenance runtime: FAIL\n  - missing log: {log_path}")
        return 1

    text = log_path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    required = {
        "hard-limit decision": (
            "selected=fast reason=6 partial_count=5 soft=5 hard=5 baseline=1"
        ),
        "vendor fast initialization": (
            "fast_init temperature=0x0064 load=0xB1 apply=0x91"
        ),
        "single-flash fast waveform command": "refresh mode=fast control=0xC7",
        "successful fast completion": "activate=1 complete=1 elapsed_ms=1740",
        "policy reset after maintenance": (
            "policy_commit mode=fast ok=1 partial_count=0 baseline=1"
        ),
    }
    for label, marker in required.items():
        if marker not in text:
            errors.append(f"missing {label}: {marker}")

    fast_commit = text.find(
        "policy_commit mode=fast ok=1 partial_count=0 baseline=1"
    )
    post_fast_partial = text.find(
        "policy_commit mode=partial ok=1 partial_count=1 baseline=1",
        max(fast_commit, 0),
    )
    if fast_commit < 0 or post_fast_partial < 0:
        errors.append("missing successful partial refresh after fast maintenance")

    failure_markers = re.findall(
        r"(?im)^.*(?:complete=0|ready=0|timeout|failed|\bfail\b|\berror\b).*$",
        text,
    )
    if failure_markers:
        errors.append("failure marker(s): " + " | ".join(failure_markers[:3]))

    production_path = (
        args.production_log
        if args.production_log.is_absolute()
        else ROOT / args.production_log
    )
    if not production_path.is_file():
        errors.append(f"missing production log: {production_path}")
        production_text = ""
    else:
        production_text = production_path.read_text(
            encoding="utf-8", errors="replace"
        )
        production_markers = {
            "production thresholds": "soft=5 hard=60 baseline=0",
            "unknown-baseline full refresh": (
                "refresh mode=full control=0xF7 busy=0 update=1 activate=1 complete=1"
            ),
            "production partial refresh": (
                "refresh mode=partial control=0xFF busy=0 update=1 activate=1 complete=1"
            ),
        }
        for label, marker in production_markers.items():
            if marker not in production_text:
                errors.append(f"missing {label}: {marker}")
        if "daily_tap_demo start" in production_text:
            errors.append("production log still contains the daily-tap test demo")
        if "soft=5 hard=5" in production_text:
            errors.append("production log still contains the test hard limit")

    if errors:
        print("epaper fast maintenance runtime: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    partial_before = text[:fast_commit].count("policy_commit mode=partial ok=1")
    print("epaper fast maintenance runtime: PASS")
    print(f"  evidence: {log_path}")
    print(f"  partial commits before maintenance: {partial_before}")
    print("  maintenance: control=0xC7 complete=1 elapsed_ms=1740")
    print("  post-maintenance partial baseline: PASS")
    print(f"  production evidence: {production_path}")
    print("  production thresholds: soft=5 hard=60")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
