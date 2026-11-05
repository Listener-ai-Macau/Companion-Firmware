#!/usr/bin/env python3
"""Focused r40 regression gate for recording display tracks after LP wake."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--tail", required=True)
    parser.add_argument("--ble", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    log = Path(args.log).read_text(encoding="utf-8", errors="replace")
    tail = Path(args.tail).read_text(encoding="utf-8", errors="replace")
    ble = json.loads(Path(args.ble).read_text(encoding="utf-8"))
    operations = {op.get("operation"): op.get("status")
                  for op in ble.get("operations", [])}
    start = log.find("[record] gatt_live_mic_start action=start source=3 result=0 state=recording")
    active = log[start:] if start >= 0 else ""
    wave = active.count("[record-phase] track=wave")
    face = active.count("[record-phase] track=face")
    blink = active.count("[record-phase] track=blink")
    only1 = active.count("mic_local_partial only=1")
    authored = active.count("authored_plus_wave_isolated_bands")
    forbidden = [token for token in (
        "HardFault", "BUSY timeout", "panel failure", "result=0",
        "stalled_mask=0x01", "stalled_mask=0x02", "stalled_mask=0x04",
        "stalled_mask=0x08", "stalled_mask=0x10", "stalled_mask=0x20",
    ) if token in active and token != "result=0"]
    active_full = re.findall(
        r"accepted_product_driver .*?control=0x(?:C7|F7|FF)", active
    )
    checks = {
        "real_ble_recording_start_stop": (
            ble.get("status") == "PASS_REAL_RADIO" and
            operations.get("recording_control_start_write") == "PASS" and
            operations.get("recording_control_stop_write") == "PASS"
        ),
        "lp_wake_completed_before_recording": (
            0 <= log.find("low_power_wake_gc_clip") < start and
            0 <= log.find("mode2_settle_after_gc") < start
        ),
        "pure_wave_fast_track_continues": wave >= 40 and only1 >= 20,
        "authored_face_track_continues": face >= 8 and authored >= 8,
        "blink_track_continues": blink >= 1,
        "logical_clock_owners_remain_separate": (
            "wave_drives_life=0 life_drives_wave=0" in active and
            "face_clock_advanced=0" in active
        ),
        "no_full_refresh_while_recording": not active_full,
        "recording_watchdog_healthy": (
            "[watchdog] healthy=1 stalled_mask=0x00" in active
        ),
        "recording_capture_has_no_drops": (
            "drops=0" in active and "ring_on=1 cap=1" in active
        ),
        "stop_returns_to_idle_and_drains": (
            "state=idle" in tail and "ring_on=0 cap=0" in tail and
            "drops=0" in tail
        ),
        "no_faults": not forbidden,
    }
    result = {
        "schema": "companion.comp_req_785.recording_display_regression.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "counts": {"wave": wave, "face": face, "blink": blink,
                   "pure_wave_only1": only1, "authored_carriers": authored,
                   "active_full_refreshes": len(active_full)},
        "faults": forbidden,
        "hardware_contact": 1,
        "scope": "Regression only; physical double-tap feel and panel appearance remain Owner gates.",
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
