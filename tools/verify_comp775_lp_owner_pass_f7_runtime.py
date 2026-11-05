#!/usr/bin/env python3
"""Verify a natural run lands on the sealed Owner-PASS two-F7 LP path."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=pathlib.Path)
    parser.add_argument("--image", required=True, type=pathlib.Path)
    parser.add_argument("--write", required=True, type=pathlib.Path)
    args = parser.parse_args()
    log = args.log if args.log.is_absolute() else ROOT / args.log
    image = args.image if args.image.is_absolute() else ROOT / args.image
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    text = log.read_text(encoding="utf-8", errors="replace")

    timer = "[power] low_power_idle_timer=ready delay_ms=300000 diagnostic=0"
    trigger = "[power] low_power_face request=sleepy trigger=idle_timer"
    white = (
        "lp_enter_step=white_basemap control=0xF7 "
        "planes=0x24+0x26=white result=1"
    )
    paint = (
        "lp_enter_step=paint_sleepy control=0xF7 "
        "old_plane=white result=1"
    )
    landing = (
        "lp_enter_freeze_clean path=f7_white_basemap_then_target "
        "control=0xF7 white_ok=1 paint_ok=1 rebaseline_ok=1"
    )
    product = "accepted_product_driver"
    freeze = "[screen] low_power_idle freeze=committed"
    hold = (
        "deep_sleep skipped=owner_pass_f7_white_basemap "
        "after_idle_visible_commit=1 reason=clean_hold"
    )

    trigger_at = text.find(trigger)
    white_at = text.find(white, max(trigger_at, 0))
    paint_at = text.find(paint, max(white_at, 0))
    landing_at = text.find(landing, max(paint_at, 0))
    freeze_at = text.find(freeze, max(landing_at, 0))
    hold_at = text.find(hold, max(freeze_at, 0))
    tail = text[hold_at:] if hold_at >= 0 else ""

    partial_before = [
        int(value)
        for value in re.findall(
            r"accepted_product_driver .*?control=0xCF .*?partial_before=(\d+)", text
        )
    ]
    f7_products = re.findall(
        r"accepted_product_driver .*?control=0xF7 .*?reason=(\d+)", text
    )
    checks = {
        "natural_300s_trigger_once": (
            text.count(timer) == 1 and text.count(trigger) == 1
        ),
        "ordinary_cf_crosses_64_without_auto_full": (
            len(partial_before) >= 65
            and max(partial_before, default=-1) >= 64
            and "automatic_life=1" not in text
        ),
        "two_f7_steps_and_landing_once": (
            text.count(white) == 1
            and text.count(paint) == 1
            and text.count(landing) == 1
            and f7_products == ["7"]
        ),
        "lp_order_trigger_white_paint_landing_freeze_hold": (
            0 <= trigger_at < white_at < paint_at < landing_at < freeze_at < hold_at
        ),
        "controller_awake_matches_owner_pass": (
            text.count(hold) == 1 and "[e]ds p=1 r=1 s=1" not in text
        ),
        "frozen_tail_has_no_display_or_motion_commits": (
            product not in tail
            and "[screen-life]" not in tail
            and "[screen-blink]" not in tail
            and "recording_overlay" not in tail
        ),
        "frozen_tail_watchdog_healthy": (
            tail.count("[watchdog] healthy=1 stalled_mask=0x00") >= 7
        ),
        "no_fault_or_reset": all(
            marker not in text.lower()
            for marker in (
                "hardfault",
                "watchdog] fault",
                "panel error",
                "assert failed",
                "fatal_error",
            )
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": "companion.comp775.lp_owner_pass_f7.runtime.v1",
        "status": "PASS_MACHINE_OWNER_F7_LP_HOLD" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "log": {"path": str(log), "sha256": digest(log)},
        "image": {"path": str(image), "sha256": digest(image)},
        "counts": {
            "cf_product_commits": len(partial_before),
            "max_partial_before": max(partial_before, default=-1),
            "white_f7": text.count(white),
            "paint_f7": text.count(paint),
            "lp_landings": text.count(landing),
            "deep_sleep_commands": text.count("[e]ds p=1 r=1 s=1"),
            "post_hold_watchdog_healthy": tail.count(
                "[watchdog] healthy=1 stalled_mask=0x00"
            ),
            "post_hold_display_commits": tail.count(product),
        },
        "claim_scope": "machine topology and frozen hold; glass cleanliness remains Owner-gated",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("FAIL: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: natural sealed Owner-PASS two-F7 LP hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
