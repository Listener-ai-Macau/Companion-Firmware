#!/usr/bin/env python3
"""Verify one continuous boot-to-low-power run uses the accepted r37 history."""

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
    raw = log.read_text(encoding="utf-8", errors="replace")

    # capture_nucleo_serial opens the UART before resetting the MCU, so a few
    # pre-reset lines may be present.  Bind all checks to the last complete boot.
    boot_marker = "[stage] uart ok"
    boot_at = raw.rfind(boot_marker)
    text = raw[boot_at:] if boot_at >= 0 else raw

    timer_ready = "[power] low_power_idle_timer=ready delay_ms=300000 diagnostic=0"
    timer_armed = "[power] low_power_idle_timer=armed delay_ms=300000 source=rtc_ts"
    trigger = "[power] low_power_face request=sleepy trigger=idle_timer"
    freeze = "[screen] low_power_idle freeze=committed quiet=1 life=0 blink=0 wave=0 accessory=0"
    landing = (
        "accepted_fast_full profile=accepted_cached_mode2 control=0xFF "
        "window=200x200 bytes_each=5000 data_planes=2 old_plane=committed_previous"
    )
    boot_landing = (
        "accepted_fast_full profile=accepted_cached_mode2 control=0xFF "
        "window=200x200 bytes_each=5000 data_planes=2 old_plane=inverse_target"
    )
    deep_sleep = "[e]ds p=1 r=1 s=1"

    trigger_at = text.find(trigger)
    landing_at = text.find(landing, max(trigger_at, 0))
    freeze_at = text.find(freeze, max(landing_at, 0))
    sleep_at = text.find(deep_sleep, max(freeze_at, 0))
    tail = text[sleep_at:] if sleep_at >= 0 else ""

    partial_before = [
        int(value)
        for value in re.findall(
            r"accepted_product_driver .*?control=0xCF .*?partial_before=(\d+)", text
        )
    ]
    max_partial_before = max(partial_before, default=-1)
    ff_commits = re.findall(
        r"accepted_product_driver .*?control=0xFF .*?reason=(\d+)", text
    )

    fault_markers = (
        "hardfault",
        "watchdog] fault",
        "panel error",
        "assert failed",
        "fatal_error",
    )
    checks = {
        "continuous_reset_boot_present": boot_at >= 0,
        "boot_uses_one_unified_r37_ff": (
            text.count(boot_landing) == 1
            and text.count("lifecycle_boundary control=0xFF unified_r37=1") >= 1
        ),
        "no_c7_anywhere_after_boot": "control=0xC7" not in text,
        "ordinary_cf_crosses_old_maintenance_limit": (
            len(partial_before) >= 65 and max_partial_before >= 64
        ),
        "no_automatic_maintenance_full_refresh": (
            "maintenance_single_full" not in text
            and "automatic_life_maintenance=1" not in text
        ),
        "natural_300s_timer_armed_and_triggered_once": (
            text.count(timer_ready) == 1
            # The policy immediately rearms once while handing the accepted
            # sleep intent to the display owner; one trigger and one landing
            # below prove that the duplicate arm log is not a second entry.
            and text.count(timer_armed) >= 1
            and text.count(trigger) == 1
        ),
        "one_committed_previous_r37_lp_landing": text.count(landing) == 1,
        "lp_order_is_trigger_landing_freeze_sleep": (
            0 <= trigger_at < landing_at < freeze_at < sleep_at
        ),
        "only_boot_and_lp_are_ff_product_commits": (
            len(ff_commits) == 2 and sorted(ff_commits) == ["3", "7"]
        ),
        "deep_sleep_once": text.count(deep_sleep) == 1,
        "frozen_tail_has_no_display_or_motion_commits": (
            "accepted_product_driver" not in tail
            and "[screen-life]" not in tail
            and "[screen-blink]" not in tail
            and "recording_overlay" not in tail
        ),
        "frozen_tail_watchdog_healthy": (
            # The 390 s capture leaves roughly 70 s after the display BUSY
            # handoff; seven 10 s health reports cover that entire frozen tail.
            tail.count("[watchdog] healthy=1 stalled_mask=0x00") >= 7
        ),
        "no_fault_or_reset": all(marker not in text.lower() for marker in fault_markers),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": "companion.comp775.r37_unified_history.runtime.v1",
        "status": "PASS_MACHINE_R37_UNIFIED_HISTORY" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "log": {"path": str(log), "sha256": digest(log)},
        "image": {"path": str(image), "sha256": digest(image)},
        "counts": {
            "cf_product_commits": len(partial_before),
            "max_partial_before": max_partial_before,
            "ff_product_commit_reasons": ff_commits,
            "lp_triggers": text.count(trigger),
            "r37_lp_landings": text.count(landing),
            "deep_sleep": text.count(deep_sleep),
            "post_sleep_watchdog_healthy": tail.count(
                "[watchdog] healthy=1 stalled_mask=0x00"
            ),
            "post_sleep_display_commits": tail.count("accepted_product_driver"),
        },
        "claim_scope": (
            "continuous refresh history, natural LP timing, and frozen tail; "
            "glass cleanliness remains Owner-gated"
        ),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("FAIL: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: continuous accepted-r37 refresh history and frozen LP tail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
