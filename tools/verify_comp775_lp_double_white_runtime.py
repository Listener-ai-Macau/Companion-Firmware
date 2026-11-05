#!/usr/bin/env python3
"""Verify the owner-authorized COMP-REQ-775 double-white LP boundary."""

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
    args = parser.parse_args()

    main_lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail_lines = args.tail.read_text(encoding="utf-8", errors="replace").splitlines()
    lp3_rows = [fields(line) for line in main_lines if "[e] lp3 " in line]
    driver_rows = [fields(line) for line in main_lines
                   if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in driver_rows
                  if row.get("control") == "0xCF" and row.get("changed") == "1"]
    maintenance = [row for row in driver_rows
                   if row.get("reason") == "4" and row.get("control") == "0xC7"]
    lp_driver = [row for row in driver_rows if row.get("reason") == "7"]
    freeze_indexes = [index for index, line in enumerate(main_lines)
                      if "[screen] low_power_idle freeze=committed" in line]
    freeze_index = freeze_indexes[-1] if freeze_indexes else None
    post_freeze_main = main_lines[freeze_index + 1:] if freeze_index is not None else []
    post_freeze = post_freeze_main + tail_lines
    post_driver = [line for line in post_freeze
                   if "[epaper] accepted_product_driver" in line]
    post_watchdog = [fields(line) for line in post_freeze if "[watchdog]" in line]
    deep_sleep = [line for line in post_freeze_main
                  if "[epaper] panel_sleep" in line and "deep_sleep=1" in line]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in main_lines + tail_lines)})

    lp3 = lp3_rows[0] if len(lp3_rows) == 1 else {}
    lp = lp_driver[0] if len(lp_driver) == 1 else {}
    try:
        busy_ms = int(lp3.get("b", "0"))
        transaction_ms = int(lp.get("transaction_ms", "0"))
    except ValueError:
        busy_ms = 0
        transaction_ms = 0

    checks = {
        "long_changed_cf_history": len(changed_cf) >= args.min_changed_cf,
        "exactly_one_double_white_receipt": len(lp3_rows) == 1,
        "receipt_declares_three_activations": lp3.get("c") == "FFC" and lp3.get("a") == "3",
        "both_white_and_target_stages_complete": (
            lp3.get("w") == "1/1" and lp3.get("t") == "1/1" and lp3.get("m") == "1"),
        "three_busy_intervals_are_bounded": 3600 <= busy_ms <= 5200,
        "exactly_one_successful_lp_driver_commit": (
            len(lp_driver) == 1 and lp.get("control") == "0xC7"
            and lp.get("changed") == "1" and lp.get("bytes") == "5000"
            and lp.get("result") == "1" and transaction_ms <= 10000),
        "freeze_committed_once": len(freeze_indexes) == 1,
        "deep_sleep_mode_1_sent_after_freeze": len(deep_sleep) == 1,
        "no_display_commit_after_freeze": not post_driver,
        "watchdog_healthy_after_freeze": (
            len(post_watchdog) >= 3
            and all(row.get("healthy") == "1" and row.get("stalled_mask") == "0x00"
                    for row in post_watchdog)),
        "no_fault_markers": not faults,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_double_white_runtime.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "hardware_contact": 1,
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "maintenance_c7_requests": len(maintenance),
            "total_driver_requests": len(driver_rows),
            "visible_activation_count": 3,
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "watchdog_healthy_after_freeze": len(post_watchdog),
            "display_commits_after_freeze": len(post_driver),
        },
        "identity": {
            "log": str(args.log.resolve()),
            "log_sha256": digest(args.log),
            "tail": str(args.tail.resolve()),
            "tail_sha256": digest(args.tail),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
