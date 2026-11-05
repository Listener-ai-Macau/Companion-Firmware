#!/usr/bin/env python3
"""Fail closed unless frozen LP enters SSD1681 Deep Sleep 1 exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = args.source.read_text(encoding="utf-8")
    start = text.index("if (low_power_committed && !s_epaper_deep_sleep_entered)")
    end = text.index("} else if (!low_power_committed)", start)
    body = text[start:end]
    checks = {
        "physical_deep_sleep_result_latched": (
            "s_epaper_deep_sleep_entered =\n"
            "            companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in body),
        "normal_standby_skip_absent": "deep_sleep skipped=normal_standby" not in body,
        "wake_guard_still_armed": (
            "s_low_power_wake_arm_ms = HAL_GetTick() + 1200u" in body),
        "touch_reentry_still_reset": (
            'Companion_App_TouchReentryReset("low_power_enter_committed")' in body),
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_final_deep_sleep_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "source": str(args.source.resolve()),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest().upper(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
