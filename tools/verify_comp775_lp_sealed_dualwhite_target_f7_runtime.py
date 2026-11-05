#!/usr/bin/env python3
"""Verify the restored sealed LP dual-white-F7 -> target-F7 hardware path."""

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
    parser.add_argument("--tail", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-changed-cf", type=int, default=140)
    args = parser.parse_args()

    main_lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail_lines = args.tail.read_text(encoding="utf-8", errors="replace").splitlines()
    drivers = [fields(line) for line in main_lines
               if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in drivers
                  if row.get("control") == "0xCF" and row.get("changed") == "1"]
    maintenance = [row for row in drivers
                   if row.get("reason") == "4" and row.get("control") == "0xC7"]
    lp_driver = [row for row in drivers if row.get("reason") == "7"]
    white_receipts = [line for line in main_lines
                      if "[e]lpw=1" in line and "dual=1" in line
                      and "partial=0" in line]
    white_rebaseline_receipts = [line for line in main_lines
                                 if "[e]lpwrb=1" in line
                                 and "old=white" in line
                                 and "current=white" in line]
    invalid_white_receipts = [line for line in main_lines
                              if "[e]lpw=" in line and line not in white_receipts]
    target_receipts = [line for line in main_lines if "[e]lpf7=1" in line]
    gpio_reprepare_receipts = [line for line in main_lines
                               if "mode1_gc_cold_path" in line
                               and "gpio_reinit=1" in line
                               and "ready=1" in line]
    forbidden_receipts = [line for line in main_lines
                          if "[e]lpc7=" in line or "[e]lpwo=" in line]
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
    awake_freeze = [line for line in post_freeze
                    if "[epaper] panel_sleep" in line
                    and "skipped=controller_awake_freeze" in line]
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
        "one_dual_white_f7_receipt": len(white_receipts) == 1,
        "one_r1_gpio_reprepare_before_white_f7": (
            len(gpio_reprepare_receipts) == 1
            and main_lines.index(gpio_reprepare_receipts[0])
            < main_lines.index(white_receipts[0])
        ) if white_receipts else False,
        "one_r1_white_rebaseline_before_target": (
            len(white_rebaseline_receipts) == 1
            and main_lines.index(white_receipts[0])
            < main_lines.index(white_rebaseline_receipts[0])
            < main_lines.index(target_receipts[0])
        ) if white_receipts and target_receipts else False,
        "no_single_plane_or_partial_white_receipt": not invalid_white_receipts,
        "one_target_f7_receipt": len(target_receipts) == 1,
        "no_c7_target_or_white_only_probe": not forbidden_receipts,
        "exactly_one_successful_lp_driver_commit": (
            len(lp_driver) == 1 and driver.get("control") == "0xF7"
            and driver.get("changed") == "1" and driver.get("bytes") == "5000"
            and driver.get("result") == "1"
            and driver.get("previous_plane_sync") == "1"
            and driver.get("post_sync_command") == "0x24"
            and driver.get("post_sync_bytes") == "10000"
        ),
        "two_f7_busy_intervals_are_bounded": (
            2400 <= busy_ms <= 3400 and transaction_ms <= 5000
        ),
        "freeze_committed_once": len(freeze_indexes) == 1,
        "controller_awake_freeze_committed_once": (
            len(awake_freeze) == 1 and not deep_sleep
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
        "schema": "companion.comp_req_775.lp_sealed_dualwhite_target_f7_runtime.v2",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "maintenance_c7_requests": len(maintenance),
            "lp_visible_activations": 2,
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "post_freeze_watchdog_healthy": len(post_watchdog),
            "post_freeze_display_commits": len(post_driver),
        },
        "identity": {
            "log_sha256": digest(args.log),
            "tail_sha256": digest(args.tail),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
