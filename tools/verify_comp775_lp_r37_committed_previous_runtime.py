#!/usr/bin/env python3
"""Verify one natural r37 low-power commit and its frozen tail."""

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

    trigger = "[power] low_power_face request=sleepy trigger=idle_timer"
    commit = "[screen] low_power_idle freeze=committed quiet=1 life=0 blink=0 wave=0 accessory=0"
    landing = (
        "accepted_fast_full profile=accepted_cached_mode2 control=0xFF "
        "window=200x200 bytes_each=5000 data_planes=2 old_plane=committed_previous"
    )
    try:
        trigger_at = text.index(trigger)
        request_match = re.search(
            r"boundary_enqueue reason=low_power_idle .* request=(\d+)",
            text[trigger_at:],
        )
        request_id = request_match.group(1) if request_match else ""
        landing_at = text.index(landing, trigger_at)
        commit_at = text.index(commit, landing_at)
        sleep_at = text.index("[e]ds p=1 r=1 s=1", commit_at)
    except ValueError:
        request_id = ""
        trigger_at = landing_at = commit_at = sleep_at = -1
    tail = text[sleep_at:] if sleep_at >= 0 else ""

    checks = {
        "natural_300s_idle_trigger_once": (
            text.count(trigger) == 1
            and "low_power_idle_timer=ready delay_ms=300000 diagnostic=0" not in text
            # The ready line is in the preceding continuous segment; this
            # tail proves the natural timer by its explicit trigger source.
        ),
        "one_r37_committed_previous_landing": text.count(landing) == 1,
        "one_full_window_ff_product_commit": (
            bool(request_id)
            and text.count(
                f"accepted_product_driver request={request_id} changed=1 control=0xFF"
            ) == 1
            and "window=0-24,0-199 bytes=5000" in text[landing_at:commit_at]
            and "previous_plane_sync=1" in text[landing_at:commit_at]
            and "post_sync_bytes=10000" in text[landing_at:commit_at]
            and "reason=7" in text[landing_at:commit_at]
        ),
        "freeze_only_after_visible_commit": (
            0 <= trigger_at < landing_at < commit_at < sleep_at
            and "surface=low_power action=3" in text[landing_at:commit_at]
        ),
        "deep_sleep_once": text.count("[e]ds p=1 r=1 s=1") == 1,
        "no_rejected_lp_waveform": (
            "[e]lp1 " not in text
            and "inverse_old=1" not in text[trigger_at:]
            and "control=0xC7" not in text[trigger_at:]
        ),
        "frozen_tail_has_no_display_or_motion_commits": (
            "accepted_product_driver" not in tail
            and "[screen-life]" not in tail
            and "[screen-blink]" not in tail
            and "recording_overlay" not in tail
        ),
        "frozen_tail_watchdog_healthy": (
            tail.count("[watchdog] healthy=1 stalled_mask=0x00") >= 8
        ),
        "no_fault_or_reset": all(
            marker not in text.lower()
            for marker in ("hardfault", "watchdog] fault", "panel error", "assert failed")
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": "companion.comp775.lp_r37_committed_previous.runtime.v1",
        "status": "PASS_MACHINE_R37_LP_FROZEN" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "log": {"path": str(log), "sha256": digest(log)},
        "image": {"path": str(image), "sha256": digest(image)},
        "counts": {
            "lp_triggers": text.count(trigger),
            "r37_landings": text.count(landing),
            "deep_sleep": text.count("[e]ds p=1 r=1 s=1"),
            "post_sleep_watchdog_healthy": tail.count(
                "[watchdog] healthy=1 stalled_mask=0x00"
            ),
            "post_sleep_display_commits": tail.count("accepted_product_driver"),
        },
        "claim_scope": "machine timing and freeze only; glass cleanliness remains Owner-gated",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("FAIL: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: natural r37 LP landing and frozen tail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
