"""Verify inverse F7, white F7, bbox target F7 and low-power freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--ble", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    ble = json.loads(Path(args.ble).read_text(encoding="utf-8"))
    boundary_at = text.find("[s]57=")
    status_at = text.find("[epaper] lp_target_status", max(boundary_at, 0))
    clean_at = text.find("[e]57 111111 0-24,55-199 3625", max(status_at, 0))
    if clean_at < 0:
        clean_at = text.find("[e]57c=1", max(status_at, 0))
    freeze_at = text.find("[screen] low_power_idle freeze=committed", max(boundary_at, 0))
    sleep_at = text.find("[e]ds p=1 r=1 s=1", max(freeze_at, 0))
    if sleep_at < 0:
        sleep_at = text.find("[epaper] deep_sleep phase=1", max(freeze_at, 0))
    tail = text[freeze_at:] if freeze_at >= 0 else ""
    faults = [
        token
        for token in (
            "HardFault",
            "BUSY timeout",
            "panel failure",
            "result=0",
            "stalled_mask=0x01",
            "stalled_mask=0x02",
            "stalled_mask=0x04",
            "stalled_mask=0x08",
            "stalled_mask=0x10",
            "stalled_mask=0x20",
        )
        if token in text
    ]
    battery_hex = next(
        (
            op.get("hex_prefix", "")
            for op in ble.get("operations", [])
            if op.get("operation") == "read_battery"
        ),
        "",
    )
    checks = {
        "real_ble_path": ble.get("status") == "PASS_REAL_RADIO",
        "real_clock_synced": any(
            op.get("operation") == "sync_utc_clock" and op.get("status") == "PASS"
            for op in ble.get("operations", [])
        ),
        "gatt_battery_truthful_unknown": battery_hex.startswith("01ff"),
        "low_power_boundary_observed": boundary_at >= 0,
        "target_frame_has_real_clock_and_80_fallback": status_at >= 0 and
        "clock_valid=1" in text[status_at:status_at + 220] and
        "battery_valid=0 battery_screen=80" in text[status_at:status_at + 220],
        "inverse_f7_succeeded": clean_at >= 0,
        "bbox_target_f7_from_dual_white": clean_at >= 0 and
        "control=0xF7 window=0-24,55-199 bytes=3625" in
        text[clean_at:freeze_at] and
        "post_sync_command=0x26 post_sync_bytes=3625" in
        text[clean_at:freeze_at],
        "inverse_f7_white_dual_f7_then_bbox_target_f7": clean_at >= 0 and
        (text.count("[e]57 111111 0-24,55-199 3625") == 1 or
         text.count("[e]57c=1") == 1) and
        "control=0xF7" in text[clean_at:freeze_at],
        "one_lp_display_request": clean_at >= 0 and
        text[boundary_at:freeze_at].count("[epaper] accepted_product_driver") == 1,
        "production_partial_history": "partial_before=255" in
        text[max(boundary_at - 9000, 0):freeze_at],
        "ordered_entry_receipt_then_freeze":
        0 <= boundary_at < status_at < clean_at < freeze_at,
        "deep_sleep_after_freeze": sleep_at > freeze_at,
        "zero_status_paints_after_freeze": "[screen-status]" not in tail,
        "zero_panel_activations_after_freeze": "[epaper] accepted_product_driver" not in tail,
        "zero_status_wake_after_freeze": "status_bar_wake" not in tail,
        "watchdog_healthy_after_freeze": "[watchdog] healthy=1 stalled_mask=0x00" in tail,
        "no_faults": not faults,
    }
    result = {
        "schema": "companion.comp_req_785.lp_freeze_runtime.v6",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "indices": {
            "boundary": boundary_at,
            "target_status": status_at,
            "clean_bbox_f7": clean_at,
            "freeze": freeze_at,
            "deep_sleep": sleep_at,
        },
        "post_freeze": {
            "status_paints": tail.count("[screen-status]"),
            "panel_activations": tail.count("[epaper] accepted_product_driver"),
            "status_wakes": tail.count("status_bar_wake"),
            "healthy_watchdogs": tail.count("[watchdog] healthy=1 stalled_mask=0x00"),
        },
        "faults": faults,
        "hardware_contact": 1,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
