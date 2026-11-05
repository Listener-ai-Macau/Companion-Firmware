#!/usr/bin/env python3
"""Verify the bounded ten-minute COMP-REQ-775 WB55 runtime capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAULT_RE = re.compile(
    r"HardFault|MemManage|BusFault|UsageFault|assert failed|stack overflow",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--capture-summary", required=True, type=Path)
    parser.add_argument("--build-receipt", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expected-generation", type=int, default=15)
    parser.add_argument("--expected-resource-prefix", default="28CF8B30")
    parser.add_argument("--expected-state-count", type=int, default=4995)
    args = parser.parse_args()

    log = args.log.read_text(encoding="utf-8", errors="replace")
    summary = json.loads(args.capture_summary.read_text(encoding="utf-8"))
    build = json.loads(args.build_receipt.read_text(encoding="utf-8"))
    firmware = build.get("firmware", {})
    generation_marker = (
        f"ui_generation=active generation={args.expected_generation} "
        f"resource_id={args.expected_resource_prefix} "
        f"entries={args.expected_state_count}"
    )
    ticks = [int(value) for value in re.findall(r"\[tick\] t_ms=(\d+)", log)]
    partials = [
        int(value)
        for value in re.findall(
            r"accepted_product_driver[^\r\n]*control=0xCF[^\r\n]*partial_before=(\d+)",
            log,
        )
    ]
    watchdog_rows = re.findall(r"\[watchdog\][^\r\n]*healthy=\d+[^\r\n]*", log)
    touch_rows = re.findall(r"\[touch-health\][^\r\n]*", log)
    complete_touch_rows = [
        row
        for row in touch_rows
        if re.search(r"\berrors=\d+\b", row)
        and re.search(r"\brecoveries=\d+\b", row)
        and re.search(r"\bdropped=\d+\b", row)
    ]
    full_controls = re.findall(
        r"accepted_(?:product_driver|true_full)[^\r\n]*control=0x(FF|C7)", log
    )
    families = sorted(set(re.findall(r"\[screen-life\] family=([^ ]+)", log)))
    charging_frames = sorted(
        set(int(value) for value in re.findall(
            r"\[screen-charging\] frame=(\d+) source=browser_timeline", log
        ))
    )
    blink_closed_count = log.count("[screen-blink] phase=closed")
    blink_open_count = log.count("[screen-blink] phase=open")
    authored_loop_matches = list(
        re.finditer(r"\[screen-life\] authored_loop family=([^ ]+) episodes=(\d+)", log)
    )
    life_after_first_loop = (
        len(re.findall(r"\[screen-life\] family=", log[authored_loop_matches[0].end():]))
        if authored_loop_matches
        else 0
    )
    life_after_last_loop = (
        len(re.findall(r"\[screen-life\] family=", log[authored_loop_matches[-1].end():]))
        if authored_loop_matches
        else 0
    )
    hardware_contact = bool(
        re.search(r"\[touch-raw\][^\r\n]*contacts=[1-9]", log)
        or re.search(r"\[touch-health\][^\r\n]*irq=[1-9]\d*", log)
    )
    sleep_boundary_count = len(re.findall(
        r"accepted_product_driver[^\r\n]*control=0xC7[^\r\n]*reason=5",
        log,
    ))

    checks = {
        "capture_completed_620_seconds": (
            summary.get("status") == "PASS"
            and int(summary.get("seconds", 0)) >= 620
        ),
        "runtime_exceeds_ten_minutes": bool(ticks) and max(ticks) >= 600_000,
        "single_boot": log.count("[boot] Companion NUCLEO-WB55RG bringup") == 1,
        "formal_latest_build_ready": (
            build.get("status") == "FIRMWARE_BUILD_READY"
            and all(build.get("checks", {}).values())
            and firmware.get("hex_minimum_address") == "0x08007000"
            and int(firmware.get("hex_maximum_address_exclusive", "0"), 16)
            <= 0x08080000
        ),
        "expected_generation_active": generation_marker in log,
        "interaction_replay_passed": (
            "menu_hold_replay=pass cycles=1000" in log
        ),
        "mixed_trajectory_replay_passed": (
            "mixed_trajectory_replay=pass cycles=1000" in log
            and "failed_cycle=1000 expected=none actual=none" in log
        ),
        "watchdog_continuously_healthy": (
            len(watchdog_rows) >= 5
            and all("healthy=1" in row for row in watchdog_rows)
            and "[watchdog] iwdg=armed" in log
        ),
        "touch_queue_never_dropped": (
            len(complete_touch_rows) >= 5
            and all(re.search(r"\bdropped=0\b", row) for row in complete_touch_rows)
        ),
        "touch_driver_no_errors_or_recovery": (
            len(complete_touch_rows) >= 5
            and all(
                re.search(r"\berrors=0\b", row)
                and re.search(r"\brecoveries=0\b", row)
                for row in complete_touch_rows
            )
        ),
        "no_runtime_fault": FAULT_RE.search(log) is None,
        "active_awake_window_has_no_sleep_boundary": sleep_boundary_count == 0,
        "startup_is_only_full_refresh": full_controls == ["FF"],
        "no_automatic_maintenance": "reason=4" not in log,
        "partial_choreography_continues_past_200": (
            len(partials) >= 200 and max(partials, default=-1) >= 200
        ),
        "life_frames_continue": log.count("[screen-life]") >= 200,
        "charging_three_frame_timeline_continues": charging_frames == [0, 1, 2],
        "seeded_blink_continues_partial_only": (
            blink_closed_count >= 3
            and blink_open_count == blink_closed_count
            and "[screen-blink] scheduler=enabled source=browser_seeded_v1" in log
            and "natural_blink_compose source=current_life" in log
            and "control=0xCF window=5-20,60-106 bytes=752" in log
        ),
        "authored_episode_loop_observed": (
            bool(authored_loop_matches)
            and authored_loop_matches[-1].group(1) in families
            and int(authored_loop_matches[-1].group(2)) > 0
        ),
        # A complete loop can occur late in a ten-minute window now that
        # charging and blink commits share the authored cadence. Substantial
        # post-loop progress plus a frame after the latest loop proves that
        # life resumed; the independent source-pack gate covers >=100 commits
        # for every selectable family.
        "substantial_life_progress_after_first_loop": life_after_first_loop >= 50,
        "life_continues_after_latest_loop": life_after_last_loop >= 1,
    }
    failed = [name for name, passed in checks.items() if not passed]
    receipt = {
        "schema": "companion.comp_req_775.ten_minute_runtime.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "capture_seconds": summary.get("seconds"),
        "maximum_tick_ms": max(ticks, default=0),
        "watchdog_sample_count": len(watchdog_rows),
        "touch_health_sample_count": len(touch_rows),
        "complete_touch_health_sample_count": len(complete_touch_rows),
        "partial_submit_count": len(partials),
        "maximum_partial_before": max(partials, default=-1),
        "observed_life_families": families,
        "charging_frames": charging_frames,
        "blink_closed_count": blink_closed_count,
        "blink_open_count": blink_open_count,
        "authored_loop_count": len(authored_loop_matches),
        "life_frames_after_first_loop": life_after_first_loop,
        "life_frames_after_last_loop": life_after_last_loop,
        "log_sha256": hashlib.sha256(args.log.read_bytes()).hexdigest().upper(),
        "hardware_contact": 1 if hardware_contact else 0,
        "sleep_boundary_count": sleep_boundary_count,
        "identity": {
            "generation": args.expected_generation,
            "resource_prefix": args.expected_resource_prefix,
            "state_count": args.expected_state_count,
            "hex_sha256": firmware.get("hex_sha256"),
            "hex_minimum_address": firmware.get("hex_minimum_address"),
            "hex_maximum_address_exclusive": firmware.get(
                "hex_maximum_address_exclusive"
            ),
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
