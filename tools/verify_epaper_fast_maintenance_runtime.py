#!/usr/bin/env python3
"""Verify the WB55 SSD1681 fast-maintenance hardware log."""

from __future__ import annotations

import argparse
import json
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
HISTORICAL_SUMMARY = (
    ROOT / "docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json"
)
CURRENT_RECOVERY_GATE = (
    ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
)


def verify_historical_summary(errors: list[str]) -> None:
    if not HISTORICAL_SUMMARY.is_file():
        errors.append(f"missing historical summary: {HISTORICAL_SUMMARY}")
        return
    data = json.loads(HISTORICAL_SUMMARY.read_text(encoding="utf-8"))
    fast = data.get("fast_maintenance_runtime", {})
    production = data.get("production_runtime", {})
    expected = {
        "decision": "fast",
        "reason": "interactive_hard_limit",
        "control": "0xC7",
        "elapsed_ms": 1740,
        "complete": True,
        "policy_count_after_commit": 0,
        "post_fast_partial_refresh": True,
        "machine_result": "PASS",
    }
    for key, value in expected.items():
        if fast.get(key) != value:
            errors.append(f"historical fast summary {key} drifted: {fast.get(key)!r}")
    if production.get("interactive_soft_limit") != 5:
        errors.append("historical production soft limit drifted")
    if production.get("interactive_hard_limit") != 60:
        errors.append("historical production hard limit drifted")
    if production.get("daily_tap_demo") is not False:
        errors.append("historical production summary still enables daily-tap demo")
    if production.get("flash_verified") is not True:
        errors.append("historical production summary lost flash verification")


def verify_current_recovery_scope(errors: list[str]) -> None:
    if not CURRENT_RECOVERY_GATE.is_file():
        errors.append(f"missing current recovery gate: {CURRENT_RECOVERY_GATE}")
        return
    recovery = json.loads(CURRENT_RECOVERY_GATE.read_text(encoding="utf-8"))
    if recovery.get("status") != "DEFERRED_HARDWARE_FTS02_BOOST":
        errors.append("current panel recovery must remain FTS02-deferred")
    if recovery.get("acceptance_criteria", {}).get("touch_and_maintenance_visual_recheck_passed") is not False:
        errors.append("historical fast evidence must not imply current visual acceptance")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument(
        "--production-log", type=Path, default=DEFAULT_PRODUCTION_LOG
    )
    parser.add_argument(
        "--require-raw",
        action="store_true",
        help="Fail instead of using the tracked historical summary when raw logs are absent.",
    )
    args = parser.parse_args()

    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    errors: list[str] = []
    production_path = (
        args.production_log
        if args.production_log.is_absolute()
        else ROOT / args.production_log
    )
    raw_mode = log_path.is_file() and production_path.is_file()
    if not raw_mode:
        if args.require_raw:
            if not log_path.is_file():
                errors.append(f"missing log: {log_path}")
            if not production_path.is_file():
                errors.append(f"missing production log: {production_path}")
        else:
            verify_historical_summary(errors)
        verify_current_recovery_scope(errors)
        if errors:
            print("epaper fast maintenance runtime: FAIL")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("epaper fast maintenance runtime: PASS_HISTORICAL_SUMMARY")
        print(f"  durable evidence: {HISTORICAL_SUMMARY}")
        print("  current panel acceptance: DEFERRED_HARDWARE_FTS02_BOOST")
        return 0

    text = log_path.read_text(encoding="utf-8", errors="replace")
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
    verify_current_recovery_scope(errors)

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
