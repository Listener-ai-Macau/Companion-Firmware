#!/usr/bin/env python3
"""Verify one inverse-old cold C7 LP commit and a quiescent handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAULT_TOKENS = (
    "HardFault", "panic", "assert failed", "stalled_mask=0x01",
    "stalled_mask=0x02", "stalled_mask=0x04", "stalled_mask=0x08",
    "stalled_mask=0x10",
)


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--tail", type=Path,
                        help="Optional continuation captured without resetting the MCU")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-changed-cf", type=int, default=140)
    args = parser.parse_args()

    main_lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail_lines = (args.tail.read_text(encoding="utf-8", errors="replace").splitlines()
                  if args.tail else [])
    drivers = [fields(line) for line in main_lines
               if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in drivers
                  if row.get("control") == "0xCF" and row.get("changed") == "1"]
    maintenance = [row for row in drivers
                   if row.get("reason") == "4" and row.get("control") == "0xC7"]
    lp_driver = [row for row in drivers if row.get("reason") == "7"]
    forbidden_two_stage = [line for line in main_lines
                           if "[e]lpw=" in line or "[e]lpwrb=" in line
                           or "[e]lpf7=" in line
                           or "[epaper] lp_r61_white_dwell_wake" in line]
    freeze_indexes = [index for index, line in enumerate(main_lines)
                      if "[screen] low_power_idle freeze=committed" in line]
    freeze_index = freeze_indexes[-1] if freeze_indexes else None
    boundary_indexes = [index for index, line in enumerate(main_lines)
                        if "[screen] boundary_enqueue reason=low_power_idle" in line]
    boundary_index = boundary_indexes[-1] if boundary_indexes else None
    lp_window = (main_lines[boundary_index:freeze_index + 1]
                 if boundary_index is not None and freeze_index is not None
                 and boundary_index < freeze_index else [])
    settle_receipts = [fields(line) for line in lp_window
                       if "[epaper] lp_settle_ff" in line
                       or "[epaper] mode2_settle_after_gc" in line]
    entry_receipts = [fields(line) for line in lp_window
                      if "[epaper] lp_enter_inverse_old_c7" in line]
    rearm_skip_receipts = [fields(line) for line in lp_window
                           if "[epaper] lp_skip_mode2_rearm" in line]
    hidden_rearm_receipts = [line for line in lp_window
                             if "[epaper] accepted_mode2_rearm" in line]
    pre_freeze = main_lines[:freeze_index] if freeze_index is not None else []
    lp_gc_receipts = [fields(line) for line in pre_freeze
                      if "[epaper] accepted_gc_full" in line]
    lp_gc = lp_gc_receipts[-1] if lp_gc_receipts else {}
    post_freeze = ((main_lines[freeze_index + 1:] if freeze_index is not None else [])
                   + tail_lines)
    post_driver = [line for line in post_freeze
                   if "[epaper] accepted_product_driver" in line]
    post_watchdog = [fields(line) for line in post_freeze if "[watchdog]" in line]
    deep_sleep = [fields(line) for line in post_freeze
                  if "[e]ds " in line]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in main_lines + tail_lines)})
    driver = lp_driver[0] if len(lp_driver) == 1 else {}
    try:
        busy_ms = int(driver.get("busy_ms", "0"))
        transaction_ms = int(driver.get("transaction_ms", "0"))
    except ValueError:
        busy_ms = transaction_ms = 0

    checks = {
        "maintained_changed_cf_history": len(changed_cf) >= args.min_changed_cf,
        "life_maintenance_observed": len(maintenance) >= 2,
        "two_stage_f7_path_absent": not forbidden_two_stage,
        "one_exit_equivalent_c7_lp_driver_commit": (
            len(lp_driver) == 1 and driver.get("control") == "0xC7"
            and driver.get("changed") == "1" and driver.get("bytes") == "5000"
            and driver.get("result") == "1"
            and driver.get("previous_plane_sync") == "1"
            and driver.get("post_sync_command") == "0x24"
            and driver.get("post_sync_bytes") == "10000"
        ),
        "single_c7_activation_is_bounded": (
            1400 <= busy_ms <= 2300 and transaction_ms <= 2600
        ),
        "exactly_one_visible_activation_and_no_settle": (
            len(entry_receipts) == 1
            and entry_receipts[0].get("control") == "0xC7"
            and entry_receipts[0].get("activation_count") == "1"
            and entry_receipts[0].get("deferred_settle") == "0"
            and entry_receipts[0].get("inverse_old") == "1"
            and not settle_receipts
        ),
        "no_hidden_0x99_initial_display_after_lp_c7": (
            len(rearm_skip_receipts) == 1
            and rearm_skip_receipts[0].get("control_0x99") == "0"
            and rearm_skip_receipts[0].get("initial_display_stage") == "0"
            and rearm_skip_receipts[0].get("direct_deep_sleep") == "1"
            and not hidden_rearm_receipts
        ),
        "final_pre_freeze_gc_is_inverse_old_c7_not_white_staged": (
            lp_gc.get("control") == "0xC7"
            and lp_gc.get("complete") == "1"
            and lp_gc.get("lp_white") == "0"
            and lp_gc.get("inverse_old") == "1"
            and lp_gc.get("old_source") == "inverse_target_lp"
        ),
        "freeze_committed_once": len(freeze_indexes) == 1,
        "physical_deep_sleep_committed_once": (
            len(deep_sleep) == 1
            and deep_sleep[0].get("p") == "1"
            and deep_sleep[0].get("r") == "1"
            and deep_sleep[0].get("s") == "1"
        ),
        "no_display_commit_after_freeze": not post_driver,
        "watchdog_healthy_after_freeze": (
            len(post_watchdog) >= 3
            and all(row.get("healthy") == "1" and row.get("stalled_mask") == "0x00"
                    for row in post_watchdog)
        ),
        "no_fault_markers": not faults,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_complete_wake_chain_runtime.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "maintenance_c7_requests": len(maintenance),
            "lp_visible_activations": 1,
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "post_freeze_watchdog_healthy": len(post_watchdog),
            "post_freeze_display_commits": len(post_driver),
            "post_freeze_deep_sleep_receipts": len(deep_sleep),
        },
        "identity": {
            "log_sha256": digest(args.log),
            "tail_sha256": digest(args.tail) if args.tail else None,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
