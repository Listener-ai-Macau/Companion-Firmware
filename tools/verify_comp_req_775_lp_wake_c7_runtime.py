#!/usr/bin/env python3
"""Verify the r7 LP inverse/sleep/white then wake-C7 runtime receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    def last_index(fragment: str) -> int:
        return max((i for i, line in enumerate(lines) if fragment in line),
                   default=-1)

    lp_request = last_index("[power] low_power_face request=sleepy")
    target_c7 = last_index("[e]lpc7=1")
    gc = last_index(
        "accepted_gc_full control=0xC7 "
        "old_plane=white_inv_sleep complete=1"
    )
    driver = last_index(
        "accepted_product_driver request="
    )
    freeze = last_index("[screen] low_power_idle freeze=committed")
    deep_sleep = last_index("[epaper] deep_sleep phase=1 ready=1 sent=1")

    lp_driver_candidates = [
        (i, line) for i, line in enumerate(lines)
        if i > lp_request
        and "accepted_product_driver request=" in line
        and "control=0xC7" in line
        and "window=0-24,0-199" in line
        and "bytes=5000" in line
        and "post_sync_command=0x26" in line
        and "result=1" in line
    ]
    lp_driver = lp_driver_candidates[-1][0] if lp_driver_candidates else -1

    post_freeze_panel_commits = sum(
        1 for line in lines[freeze + 1:]
        if "accepted_product_driver" in line
        or "[screen-blink] pair" in line
        or "[screen] display_commit" in line
    ) if freeze >= 0 else -1
    unhealthy = sum(
        1 for line in lines
        if "healthy=0" in line
        or "HardFault" in line
        or "cfsr=" in line
        or "BUSY timeout" in line
    )
    ordinary_partials = sum(
        1 for line in lines[:lp_request]
        if "accepted_product_driver" in line and "control=0xCF" in line
    ) if lp_request >= 0 else 0
    automatic_maintenance = sum(
        1 for line in lines[:lp_request]
        if "maintenance_single_full" in line and "automatic_life=1" in line
    ) if lp_request >= 0 else 0

    checks = {
        "production_history_present": ordinary_partials >= 128,
        "automatic_maintenance_present": automatic_maintenance >= 1,
        "lp_sequence_ordered": (
            0 <= lp_request < target_c7 < gc < lp_driver < freeze < deep_sleep
        ),
        "lp_target_wake_c7_complete": target_c7 >= 0,
        "lp_gc_old_white_complete": gc >= 0,
        "lp_driver_full_window_c7": lp_driver >= 0,
        "freeze_committed": freeze >= 0,
        "deep_sleep_after_freeze": deep_sleep > freeze >= 0,
        "no_panel_commit_after_freeze": post_freeze_panel_commits == 0,
        "watchdog_and_faults_clean": unhealthy == 0,
    }
    ready = all(checks.values())
    result = {
        "schema": "companion.comp_req_775.lp_wake_c7_runtime.v1",
        "status": "MACHINE_READY" if ready else "MACHINE_BLOCKED",
        "optical_owner_gate_required": True,
        "checks": checks,
        "counts": {
            "ordinary_partials_before_lp": ordinary_partials,
            "automatic_life_maintenance": automatic_maintenance,
            "post_freeze_panel_commits": post_freeze_panel_commits,
            "unhealthy_or_fault_lines": unhealthy,
        },
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
