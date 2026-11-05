#!/usr/bin/env python3
"""Verify long-history COMP-REQ-775 normal-full white F7 -> fast target C7."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAULT_TOKENS = ("HardFault", "panic", "assert failed", "stalled_mask=0x01",
                "stalled_mask=0x02", "stalled_mask=0x04",
                "stalled_mask=0x08", "stalled_mask=0x10")


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--tail", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-changed-cf", type=int, default=140)
    parser.add_argument("--expect-normal-standby", action="store_true")
    parser.add_argument("--expect-frozen-no-rearm", action="store_true")
    parser.add_argument("--expect-inverse-precondition", action="store_true")
    args = parser.parse_args()
    main_lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail_lines = args.tail.read_text(encoding="utf-8", errors="replace").splitlines()
    lp_rows = [fields(line) for line in main_lines
               if "[e] lp2 " in line and " c=" in line]
    drivers = [fields(line) for line in main_lines
               if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in drivers
                  if row.get("control") == "0xCF" and row.get("changed") == "1"]
    maintenance = [row for row in drivers
                   if row.get("reason") == "4" and row.get("control") == "0xC7"]
    lp_driver = [row for row in drivers if row.get("reason") == "7"]
    freeze_indexes = [index for index, line in enumerate(main_lines)
                      if "[screen] low_power_idle freeze=committed" in line]
    freeze_index = freeze_indexes[-1] if freeze_indexes else None
    post_freeze = ((main_lines[freeze_index + 1:] if freeze_index is not None else [])
                   + tail_lines)
    post_driver = [line for line in post_freeze
                   if "[epaper] accepted_product_driver" in line]
    post_watchdog = [fields(line) for line in post_freeze if "[watchdog]" in line]
    deep_sleep = [line for line in post_freeze
                  if "[epaper] panel_sleep" in line and "deep_sleep=1" in line]
    normal_standby = [line for line in post_freeze
                      if "deep_sleep skipped=normal_standby" in line
                      and "reason=r69_clean_lock" in line]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in main_lines + tail_lines)})
    lp = lp_rows[0] if len(lp_rows) == 1 else {}
    driver = lp_driver[0] if len(lp_driver) == 1 else {}
    try:
        busy_ms = int(lp.get("b", "0"))
        transaction_ms = int(driver.get("transaction_ms", "0"))
    except ValueError:
        busy_ms = transaction_ms = 0
    checks = {
        "long_changed_cf_history": len(changed_cf) >= args.min_changed_cf,
        "exactly_one_official_white_receipt": len(lp_rows) == 1,
        "normal_white_and_target_complete": (
            lp.get("w") == "1" and lp.get("ws") == "1"
            and lp.get("t") == "1" and lp.get("ts") == "1"
            and lp.get("c") == ("F7F7C7" if args.expect_inverse_precondition
                                 else "F7C7")
            and (lp.get("i") == "1" and lp.get("ir") == "1"
                 if args.expect_inverse_precondition else True)
            and (lp.get("m2") == "0" and lp.get("frozen") == "1"
                 if args.expect_frozen_no_rearm else lp.get("m2") == "1")),
        "visible_busy_intervals_are_bounded": (
            3900 <= busy_ms <= 5300 if args.expect_inverse_precondition
            else 2600 <= busy_ms <= 3800),
        "exactly_one_successful_lp_driver_commit": (
            len(lp_driver) == 1 and driver.get("control") == "0xC7"
            and driver.get("changed") == "1" and driver.get("bytes") == "5000"
            and driver.get("result") == "1" and driver.get("previous_plane_sync") == "1"
            and transaction_ms <= 8000),
        "freeze_committed_once": len(freeze_indexes) == 1,
        "requested_post_commit_power_state_exact": (
            len(normal_standby) == 1 and not deep_sleep
            if args.expect_normal_standby
            else len(deep_sleep) == 1 and not normal_standby),
        "no_display_commit_after_freeze": not post_driver,
        "watchdog_healthy_after_freeze": (
            len(post_watchdog) >= 3
            and all(row.get("healthy") == "1" and row.get("stalled_mask") == "0x00"
                    for row in post_watchdog)),
        "no_fault_markers": not faults,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_official_white_runtime.v2",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "maintenance_c7_requests": len(maintenance),
            "total_driver_requests": len(drivers),
            "visible_activation_count": 3 if args.expect_inverse_precondition else 2,
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "watchdog_healthy_after_freeze": len(post_watchdog),
            "display_commits_after_freeze": len(post_driver),
            "post_commit_power_state": (
                "normal_standby" if args.expect_normal_standby else "deep_sleep_1"),
        },
        "identity": {
            "log": str(args.log.resolve()), "log_sha256": digest(args.log),
            "tail": str(args.tail.resolve()), "tail_sha256": digest(args.tail),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
