#!/usr/bin/env python3
"""Verify long-history bbox-F7 low-power entry and frozen residency."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAULTS = ("HARDFAULT", "HardFault", "panic", "assert failed", "BUSY timeout",
          "stalled_mask=0x01", "stalled_mask=0x02", "stalled_mask=0x04",
          "stalled_mask=0x08", "stalled_mask=0x10")


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line))


def lp_fields(line: str) -> dict[str, str]:
    row = fields(line)
    match = re.search(
        r"\[e\]57 ([01])([01])([01])([01])([01])([01]) "
        r"(\d+)-(\d+),(\d+)-(\d+) (\d+)", line)
    if match:
        values = match.groups()
        row.update(dict(zip(("i", "ir", "w", "t", "m2", "frozen"),
                            values[:6])))
        row["window"] = f"{values[6]}-{values[7]},{values[8]}-{values[9]}"
        row["bytes"] = values[10]
    return row


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--tail", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-changed-cf", type=int, default=140)
    parser.add_argument(
        "--handoff", choices=("no-rearm", "exact-r57", "zoned-r57",
                              "fine-zoned-r57", "component-r57",
                              "component-f7-r57", "double-white-r58"),
        default="no-rearm")
    args = parser.parse_args()
    main_lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail_lines = args.tail.read_text(encoding="utf-8", errors="replace").splitlines()
    lp_rows = [lp_fields(line) for line in main_lines
               if ("[e] z=" in line or "[e] lpz " in line or
                   "[e]57" in line or "[e]58" in line or
                   ("[e] lp2 " in line and " c=" in line))]
    drivers = [fields(line) for line in main_lines
               if "[epaper] accepted_product_driver" in line]
    changed_cf = [row for row in drivers
                  if row.get("changed") == "1" and row.get("control") == "0xCF"]
    lp_driver = [row for row in drivers if row.get("reason") == "7"]
    freeze_at = [index for index, line in enumerate(main_lines)
                 if "[screen] low_power_idle freeze=committed" in line]
    post = ((main_lines[freeze_at[-1] + 1:] if freeze_at else []) + tail_lines)
    post_driver = [line for line in post if "accepted_product_driver" in line]
    watchdog = [fields(line) for line in post if "[watchdog]" in line]
    deep_sleep = [line for line in post
                  if ("[epaper] panel_sleep deep_sleep=1" in line or
                      "[epaper] deep_sleep phase=1" in line or
                      "[e]ds p=1 r=1 s=1" in line)]
    boundary_at = [index for index, line in enumerate(main_lines)
                   if "[screen] boundary_enqueue reason=low_power_idle" in line]
    boundary_slice = (main_lines[boundary_at[-1]:freeze_at[-1]]
                      if boundary_at and freeze_at else [])
    rearm = [line for line in boundary_slice
             if "[epaper] accepted_mode2_rearm" in line]
    fault_tokens = sorted({token for token in FAULTS
                           if any(token in line for line in main_lines + tail_lines)})
    lp = lp_rows[0] if len(lp_rows) == 1 else {}
    driver = lp_driver[0] if len(lp_driver) == 1 else {}
    try:
        busy_ms = int(
            driver.get("busy_ms", "0")
            if args.handoff in ("exact-r57", "double-white-r58", "component-r57",
                                "component-f7-r57") and "b" not in lp
            else lp.get("b", "0"))
        transaction_ms = int(driver.get("transaction_ms", "0"))
    except ValueError:
        busy_ms = transaction_ms = 0
    checks = {
        "long_changed_cf_history": len(changed_cf) >= args.min_changed_cf,
        "one_target_receipt": (
            len(lp_rows) == 1 and
            ((args.handoff in ("component-r57", "component-f7-r57")
              and lp.get("z") == "11")
             or (args.handoff in ("zoned-r57", "fine-zoned-r57")
              and lp.get("ok") == "1"
              and lp.get("z") == ("5" if args.handoff == "fine-zoned-r57" else "3")
              and lp.get("zb") == ("1090" if args.handoff == "fine-zoned-r57" else "1727")
              and lp.get("m2") == "1"
              and lp.get("f") == "1")
              or (args.handoff == "exact-r57" and
                  ((all(lp.get(key) == "1" for key in
                        ("i", "ir", "w", "t", "m2", "frozen"))
                    and lp.get("window") == "0-24,55-199"
                    and lp.get("bytes") == "3625")
                   or (lp.get("c") == "F7F7F7"
                    and all(lp.get(key) == "1" for key in
                            ("i", "ir", "w", "ws", "t", "ts", "frozen"))
                    and lp.get("m2") == "1")
                   or all(lp.get(key) == "1" for key in
                          ("inv", "white", "target"))
                   or lp.get("57c") == "1"))
              or (args.handoff == "double-white-r58"
                  and all(lp.get(key) == "1" for key in
                          ("i", "w", "w2", "t")))
              or (args.handoff == "no-rearm"
                  and lp.get("c") == "F7F7F7"
                  and all(lp.get(key) == "1" for key in
                          ("i", "ir", "w", "ws", "t", "ts", "frozen"))
                  and lp.get("m2") == "0"))),
        "target_geometry_exact": (
            len(lp_driver) == 1 and driver.get("control") == "0xF7"
            and driver.get("window") == "0-24,55-199"
            and driver.get("bytes") ==
                ("708" if args.handoff in
                 ("component-r57", "component-f7-r57") else
                 "1090" if args.handoff == "fine-zoned-r57" else
                 "1727" if args.handoff == "zoned-r57" else "3625")
            and driver.get("regions") ==
                ("11" if args.handoff in
                 ("component-r57", "component-f7-r57") else
                 "5" if args.handoff == "fine-zoned-r57" else
                 "3" if args.handoff == "zoned-r57" else "1")
            and driver.get("result") == "1"),
        "ram_handoff_without_activation": (
            driver.get("previous_plane_sync") == "1"
            and driver.get("post_sync_command") ==
                ("0x26" if args.handoff in ("exact-r57", "double-white-r58", "zoned-r57",
                                             "fine-zoned-r57", "component-r57",
                                             "component-f7-r57") else "0x24")
            and driver.get("post_sync_bytes") ==
                ("708" if args.handoff in
                 ("component-r57", "component-f7-r57") else
                 "1090" if args.handoff == "fine-zoned-r57" else
                 "1727" if args.handoff == "zoned-r57" else
                 "3625" if args.handoff in ("exact-r57", "double-white-r58") else "10000")
            and driver.get("post_sync_refresh") == "0"),
        "controller_handoff_exact": (
            len(rearm) == (2 if args.handoff == "component-r57" else 1)
            and all("display_activation=0" in row and "complete=1" in row
                    for row in rearm))
            if args.handoff in ("exact-r57", "double-white-r58", "zoned-r57", "fine-zoned-r57",
                                "component-r57", "component-f7-r57") else not rearm,
        "busy_and_transaction_bounded": (
            (8000 <= busy_ms <= 10500 and transaction_ms <= 13000)
            if args.handoff == "component-r57" else
            (14000 <= busy_ms <= 18000 and transaction_ms <= 21000)
            if args.handoff == "component-f7-r57" else
            (7800 <= busy_ms <= 9500 and transaction_ms <= 12000)
            if args.handoff == "fine-zoned-r57" else
            (6000 <= busy_ms <= 7500 and transaction_ms <= 10000)
            if args.handoff == "zoned-r57" else
            (4700 <= busy_ms <= 6000 and transaction_ms <= 8500)
            if args.handoff == "double-white-r58" else
            (3500 <= busy_ms <= 4500
             and transaction_ms <= (7000 if args.handoff == "exact-r57" else 8000))),
        "freeze_once": len(freeze_at) == 1,
        "deep_sleep_once": len(deep_sleep) == 1,
        "zero_display_after_freeze": not post_driver,
        "watchdog_healthy_after_freeze": (
            len(watchdog) >= 3 and all(row.get("healthy") == "1"
                                      and row.get("stalled_mask") == "0x00"
                                      for row in watchdog)),
        "no_faults": not fault_tokens,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_bbox_runtime.v3",
        "handoff": args.handoff,
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "metrics": {
            "changed_cf_activations": len(changed_cf),
            "total_driver_requests": len(drivers),
            "lp_busy_ms": busy_ms,
            "lp_transaction_ms": transaction_ms,
            "post_freeze_watchdogs": len(watchdog),
            "post_freeze_display_commits": len(post_driver),
            "fault_tokens": fault_tokens,
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
