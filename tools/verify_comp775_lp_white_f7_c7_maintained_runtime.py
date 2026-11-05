#!/usr/bin/env python3
"""Verify maintained life history and the two-activation LP boundary on WB55."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAULT_TOKENS = (
    "HardFault", "panic", "assert failed", "healthy=0",
    "stalled_mask=0x01", "stalled_mask=0x02", "stalled_mask=0x04",
    "stalled_mask=0x08", "stalled_mask=0x10",
)


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def current_boot(lines: list[str]) -> list[str]:
    starts = [i for i, line in enumerate(lines) if "[stage] uart ok" in line]
    return lines[starts[-1]:] if starts else lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--tail", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    main_lines = current_boot(
        args.log.read_text(encoding="utf-8", errors="replace").splitlines())
    tail_lines = args.tail.read_text(
        encoding="utf-8", errors="replace").splitlines()
    drivers = [fields(line) for line in main_lines
               if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in drivers
                  if row.get("control") == "0xCF" and row.get("changed") == "1"]
    maintenance_lines = [line for line in main_lines
                         if "maintenance_single_full" in line
                         and "automatic_life=1" in line]
    maintenance_partials = [
        int(match.group(1)) for line in maintenance_lines
        if (match := re.search(r"partial_before=(\d+)", line))
    ]
    lpw = [line for line in main_lines if "[e]lpw=1" in line]
    lpc7 = [line for line in main_lines if "[e]lpc7=1" in line]
    rejected_zones = [line for line in main_lines if "[e] z=" in line]
    lp_driver = [row for row in drivers if row.get("reason") == "7"]
    freeze_indexes = [i for i, line in enumerate(main_lines)
                      if "[screen] low_power_idle freeze=committed" in line]
    freeze_index = freeze_indexes[-1] if freeze_indexes else None
    post_freeze = ((main_lines[freeze_index + 1:] if freeze_index is not None else [])
                   + tail_lines)
    post_driver = [line for line in post_freeze
                   if "[epaper] accepted_product_driver" in line]
    post_watchdog = [fields(line) for line in post_freeze
                     if "[watchdog]" in line]
    deep_sleep = [line for line in post_freeze
                  if "[epaper] panel_sleep deep_sleep=1" in line]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in main_lines + tail_lines)})
    lp = lp_driver[0] if len(lp_driver) == 1 else {}
    try:
        partial_before = int(lp.get("partial_before", "-1"))
        busy_ms = int(lp.get("busy_ms", "0"))
        transaction_ms = int(lp.get("transaction_ms", "0"))
    except ValueError:
        partial_before = -1
        busy_ms = transaction_ms = 0

    checks = {
        "ordinary_history_exercised": len(changed_cf) >= 200,
        "bounded_life_maintenance_exercised": (
            len(maintenance_partials) >= 3
            and all(64 <= value <= 65 for value in maintenance_partials)
        ),
        "exactly_one_white_f7_receipt": len(lpw) == 1,
        "exactly_one_target_c7_receipt": len(lpc7) == 1,
        "rejected_component_f7_absent": not rejected_zones,
        "exactly_one_lp_driver_commit": (
            len(lp_driver) == 1
            and lp.get("control") == "0xC7"
            and lp.get("changed") == "1"
            and lp.get("bytes") == "5000"
            and lp.get("regions") == "1"
            and lp.get("result") == "1"
            and lp.get("previous_plane_sync") == "1"
            and lp.get("post_sync_command") == "0x26"
            and lp.get("post_sync_bytes") == "5000"
            and lp.get("post_sync_refresh") == "0"
        ),
        "lp_enters_after_recent_maintenance": 0 <= partial_before <= 64,
        "two_activation_timing_bounded": (
            2600 <= busy_ms <= 3800 and transaction_ms <= 5000
        ),
        "freeze_committed_once": len(freeze_indexes) == 1,
        "deep_sleep_once_after_freeze": len(deep_sleep) == 1,
        "no_display_commit_after_freeze": not post_driver,
        "watchdog_healthy_after_freeze": (
            len(post_watchdog) >= 10
            and all(row.get("healthy") == "1"
                    and row.get("stalled_mask") == "0x00"
                    for row in post_watchdog)
        ),
        "no_fault_markers": not faults,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_white_f7_c7_maintained_runtime.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "automatic_life_maintenance_count": len(maintenance_partials),
            "automatic_life_maintenance_partial_before": maintenance_partials,
            "lp_partial_before": partial_before,
            "lp_visible_activation_count": 2,
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "post_freeze_watchdog_healthy": len(post_watchdog),
            "post_freeze_display_commits": len(post_driver),
            "fault_markers": faults,
        },
        "identity": {
            "log": str(args.log.resolve()),
            "log_sha256": digest(args.log),
            "tail": str(args.tail.resolve()),
            "tail_sha256": digest(args.tail),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
