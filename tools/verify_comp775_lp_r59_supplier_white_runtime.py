#!/usr/bin/env python3
"""Verify r59 supplier-white cleanup, target landing, and frozen residency."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAULTS = (
    "HARDFAULT", "HardFault", "panic", "assert failed", "BUSY timeout",
    "stalled_mask=0x01", "stalled_mask=0x02", "stalled_mask=0x04",
    "stalled_mask=0x08", "stalled_mask=0x10",
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
    parser.add_argument("--min-changed-cf", type=int, default=200)
    args = parser.parse_args()

    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = args.tail.read_text(encoding="utf-8", errors="replace").splitlines()
    drivers = [fields(line) for line in lines
               if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in drivers
                  if row.get("changed") == "1" and row.get("control") == "0xCF"]
    lp_drivers = [row for row in drivers if row.get("reason") == "7"]
    lp_request_at = [i for i, line in enumerate(lines)
                     if "[power] low_power_face request=sleepy" in line]
    freeze_at = [i for i, line in enumerate(lines)
                 if "[screen] low_power_idle freeze=committed" in line]
    deep_sleep_at = [i for i, line in enumerate(lines)
                     if "[epaper] panel_sleep deep_sleep=1" in line]
    boundary = (lines[lp_request_at[-1]:freeze_at[-1] + 1]
                if lp_request_at and freeze_at else [])
    gc_rows = [fields(line) for line in boundary
               if "[epaper] accepted_gc_full" in line]
    mode2_rearm = [line for line in boundary
                   if "[epaper] accepted_mode2_rearm" in line]
    post = ((lines[freeze_at[-1] + 1:] if freeze_at else []) + tail)
    post_driver = [line for line in post
                   if "[epaper] accepted_product_driver" in line]
    post_watchdog = [fields(line) for line in post if "[watchdog]" in line]
    fault_tokens = sorted({token for token in FAULTS
                           if any(token in line for line in lines + tail)})

    gc = gc_rows[0] if len(gc_rows) == 1 else {}
    driver = lp_drivers[0] if len(lp_drivers) == 1 else {}
    try:
        busy_ms = int(driver.get("busy_ms", "0"))
        transaction_ms = int(driver.get("transaction_ms", "0"))
    except ValueError:
        busy_ms = transaction_ms = 0

    checks = {
        "long_changed_cf_history": len(changed_cf) >= args.min_changed_cf,
        "one_lp_request_and_freeze": (
            len(lp_request_at) == 1 and len(freeze_at) == 1
            and lp_request_at[0] < freeze_at[0]
        ),
        "one_complete_supplier_white_target_chain": (
            len(gc_rows) == 1 and gc.get("control") == "0xF7"
            and gc.get("complete") == "1" and gc.get("rebaseline") == "1"
            and gc.get("mode2") == "1" and gc.get("lp_white") == "1"
        ),
        "one_target_driver_exact": (
            len(lp_drivers) == 1 and driver.get("control") == "0xF7"
            and driver.get("window") == "0-24,55-199"
            and driver.get("bytes") == "3625" and driver.get("regions") == "1"
            and driver.get("previous_plane_sync") == "1"
            and driver.get("post_sync_command") == "0x26"
            and driver.get("post_sync_bytes") == "3625"
            and driver.get("post_sync_refresh") == "0"
            and driver.get("result") == "1"
        ),
        "two_waveforms_and_discharge_timing_bounded": (
            2200 <= busy_ms <= 3600 and 4200 <= transaction_ms <= 6500
        ),
        "one_command_only_mode2_rearm": (
            len(mode2_rearm) == 1
            and "display_activation=0" in mode2_rearm[0]
            and "complete=1" in mode2_rearm[0]
        ),
        "deep_sleep_after_freeze_once": (
            len(deep_sleep_at) == 1 and len(freeze_at) == 1
            and deep_sleep_at[0] > freeze_at[0]
        ),
        "zero_display_after_freeze": not post_driver,
        "watchdog_healthy_during_extended_freeze": (
            len(post_watchdog) >= 12
            and all(row.get("healthy") == "1"
                    and row.get("stalled_mask") == "0x00"
                    for row in post_watchdog)
        ),
        "no_failed_legacy_lp_receipts": not any(
            token in "\n".join(boundary)
            for token in ("[e]58", "[e]57", "[e]lpw=", "[e]lpf7=")
        ),
        "no_faults": not fault_tokens,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_r59_supplier_white_runtime.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "total_driver_requests": len(drivers),
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "post_freeze_watchdogs": len(post_watchdog),
            "post_freeze_display_commits": len(post_driver),
            "fault_tokens": fault_tokens,
        },
        "identity": {
            "log": str(args.log.resolve()),
            "log_sha256": digest(args.log),
            "tail": str(args.tail.resolve()),
            "tail_sha256": digest(args.tail),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
