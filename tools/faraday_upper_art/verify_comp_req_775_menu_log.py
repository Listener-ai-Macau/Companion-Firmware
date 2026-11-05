#!/usr/bin/env python3
"""Verify real-panel menu boundary evidence for COMP-REQ-775."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DAILY = "[touch-ui] daily_to_menu gesture=any_long_press"
ENTER = "[screen] menu_boundary=enter"
RIGHT = "[touch-ui] menu_right_swipe_exit"
EXIT = "[screen] menu_boundary=exit"
DRIVER_PATTERN = re.compile(
    r"accepted_product_driver.*changed=1.*ready_checks=[1-9][0-9]*"
    r".*maintenance=1.*transport=software_direct_bsrr_diagnostic"
    r".*has_busy=1.*result=1"
)
FAILURE_PATTERN = re.compile(
    r"^\[(?:epaper|screen|screen-assets|ui-sync|rec-resource)\].*"
    r"(?:\bfault\b|terminal_fault=1|mount=(?:fail|unavailable)|"
    r"result=0|transport=unavailable|ui_generation=base_only|"
    r"selftest.*=fail)",
    re.IGNORECASE | re.MULTILINE,
)


def verify(log: bytes) -> dict:
    text = log.decode("utf-8", errors="replace")
    daily = text.find(DAILY)
    enter = text.find(ENTER)
    right = text.find(RIGHT)
    exit_index = text.find(EXIT)
    drivers = list(DRIVER_PATTERN.finditer(text))
    enter_drivers = [
        match
        for match in drivers
        if match.start() > enter and (right < 0 or match.start() < right)
    ]
    exit_drivers = [
        match for match in drivers if match.start() > exit_index
    ]
    ordered = (
        daily >= 0
        and daily < enter
        and len(enter_drivers) == 1
        and enter < enter_drivers[0].start() < right
        and right < exit_index
        and len(exit_drivers) == 1
        and exit_index < exit_drivers[0].start()
    )
    checks = {
        "one_long_press_entry": text.count(DAILY) == 1,
        "one_menu_enter_boundary": text.count(ENTER) == 1,
        "enter_maintenance_real_busy_ok": len(enter_drivers) == 1,
        "one_right_swipe_exit": text.count(RIGHT) == 1,
        "one_menu_exit_boundary": text.count(EXIT) == 1,
        "exit_maintenance_real_busy_ok": len(exit_drivers) == 1,
        "ordered_entry_then_exit": ordered,
        "no_runtime_fault": not bool(FAILURE_PATTERN.search(text)),
    }
    return {
        "schema": "companion.comp_req_775.menu_log_evidence.v1",
        "status": (
            "MACHINE_READY" if all(checks.values()) else "FAILED"
        ),
        "checks": checks,
        "accepted_maintenance_refreshes": len(drivers),
        "log_sha256": hashlib.sha256(log).hexdigest().upper(),
        "hardware_contact": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    evidence = verify(args.log.read_bytes())
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if evidence["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
