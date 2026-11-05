#!/usr/bin/env python3
"""Verify bounded idle cleanup and recording-safe deferral on WB55 logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re


def read(path: pathlib.Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = text.rfind("[stage] uart ok")
    if marker >= 0:
        text = text[marker:]
    return text, text.splitlines()


def index(lines: list[str], token: str, start: int = 0) -> int:
    return next((i for i in range(start, len(lines)) if token in lines[i]), -1)


def safe_atomic_blink_deferral(lines: list[str], receipt_at: int,
                               partial_before: int) -> bool:
    """Allow 66 only when one closed/open pair atomically crossed the limit."""
    if 64 <= partial_before <= 65:
        return True
    if partial_before != 66:
        return False
    prior_driver = next(
        (i for i in range(receipt_at - 1, max(-1, receipt_at - 40), -1)
         if "[epaper] accepted_product_driver" in lines[i]), -1)
    if prior_driver < 0:
        return False
    before_match = re.search(r"partial_before=(\d+)", lines[prior_driver])
    pair_at = next(
        (i for i in range(prior_driver + 1, receipt_at)
         if "[screen-blink] pair " in lines[i]
         and "committed=1" in lines[i]
         and "closed_control=0xCF" in lines[i]
         and "open_control=0xCF" in lines[i]), -1)
    return (before_match is not None
            and int(before_match.group(1)) == 63
            and pair_at > prior_driver
            and not any("[epaper] accepted_product_driver" in lines[i]
                        for i in range(prior_driver + 1, receipt_at)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-log", type=pathlib.Path, required=True)
    parser.add_argument("--recording-log", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--expected-control", choices=("C7", "FF"),
                        default="C7")
    args = parser.parse_args()

    idle_text, idle = read(args.idle_log)
    rec_text, rec = read(args.recording_log)
    idle_maint = [i for i, line in enumerate(idle) if
                  "maintenance_single_full" in line and "automatic_life=1" in line]
    idle_reason4_receipts = [i for i, line in enumerate(idle) if
                             "[epaper] accepted_product_driver" in line and
                             "maintenance=1" in line and "reason=4" in line]
    idle_receipts: list[int] = []
    idle_next_receipts: list[int] = []
    search_at = 0
    for maintenance_at in idle_maint:
        receipt_at = index(idle, "accepted_product_driver", maintenance_at)
        if receipt_at < 0 or receipt_at < search_at:
            continue
        idle_receipts.append(receipt_at)
        idle_next_receipts.append(index(idle, "accepted_product_driver", receipt_at + 1))
        search_at = receipt_at + 1
    rec_start = index(rec, "action=overlay_start result=1")
    rec_stop = index(rec, "action=stop_commit", max(rec_start, 0))
    rec_interval = rec[rec_start:rec_stop] if rec_start >= 0 and rec_stop > rec_start else []
    post_maint = index(rec, "maintenance=1", rec_stop + 1)

    idle_partials = []
    for receipt_at in idle_receipts:
        partial_match = re.search(r"partial_before=(\d+)", idle[receipt_at])
        idle_partials.append(int(partial_match.group(1)) if partial_match else -1)
    post_match = re.search(r"partial_before=(\d+)",
                           rec[post_maint] if post_maint >= 0 else "")
    post_partial = int(post_match.group(1)) if post_match else -1
    post_context = rec[max(0, post_maint - 3):post_maint + 1]
    checks = {
        "idle_each_64_boundary_has_one_safe_automatic_cleanup": (
            bool(idle_maint) and len(idle_maint) == len(idle_receipts)
            and len(idle_maint) == len(idle_reason4_receipts)
            # A closed/open natural-blink pair is atomic. If a life commit has
            # just made count 64, the queued pair occupies counts 65/66 and the
            # next authored-life carrier is the first safe cleanup slot. 66 is
            # accepted only with that exact committed-pair evidence.
            and all(safe_atomic_blink_deferral(idle, receipt_at, value)
                    for receipt_at, value in zip(idle_receipts, idle_partials))
        ),
        "idle_each_cleanup_is_single_expected_full": bool(idle_receipts) and all(
            f"control=0x{args.expected_control}" in idle[receipt_at]
            and "regions=1" in idle[receipt_at]
            for receipt_at in idle_receipts
        ),
        "idle_cleanup_before_owner_pollution": bool(idle_partials) and all(
            64 <= value < 120 for value in idle_partials
        ),
        "idle_counter_restarts_after_each_cleanup": (
            len(idle_next_receipts) == len(idle_receipts)
            and all(next_at >= 0
                    and "control=0xCF" in idle[next_at]
                    and (match := re.search(r"partial_before=(\d+)",
                                           idle[next_at])) is not None
                    # The first public driver receipt may follow an atomic
                    # blink pair whose deferred trace accounts for counts 0/1.
                    and int(match.group(1)) <= 2
                    for next_at in idle_next_receipts)
        ),
        "recording_interval_present": rec_start >= 0 and rec_stop > rec_start,
        "recording_defers_all_full_refreshes": bool(rec_interval) and not any(
            token in line for line in rec_interval
            for token in ("control=0xC7", "control=0xF7", "control=0xFF",
                          "maintenance_single_full")),
        "recording_keeps_pure_wave_lane": sum("mic_local_partial only=1" in line
                                                for line in rec_interval) >= 20,
        "recording_cleanup_runs_after_stop": post_maint > rec_stop and
            any(f"control=0x{args.expected_control}" in line
                for line in post_context) and
            post_partial >= 64,
        "watchdog_healthy": "[watchdog] healthy=1 stalled_mask=0x00" in idle_text and
            "[watchdog] healthy=1 stalled_mask=0x00" in rec_text,
        "no_storage_full_or_audio_drop": "storage_full" not in rec_text and
            re.search(r"codec=3 frames=\d+ drops=0", rec_text) is not None,
    }
    result = {
        "schema": "companion.comp_req_775.life_maintenance.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "measurements": {
            "idle_cleanup_count": len(idle_maint),
            "idle_cleanup_partial_before": idle_partials,
            "recording_cleanup_partial_before": post_partial,
            "recording_interval_lines": len(rec_interval),
            "expected_cleanup_control": f"0x{args.expected_control}",
        },
        "evidence": {
            "idle_log": str(args.idle_log.resolve()),
            "idle_log_sha256": hashlib.sha256(args.idle_log.read_bytes()).hexdigest().upper(),
            "recording_log": str(args.recording_log.resolve()),
            "recording_log_sha256": hashlib.sha256(args.recording_log.read_bytes()).hexdigest().upper(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
