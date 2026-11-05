"""Verify the real WB55 status-bar connect/clock/disconnect transaction."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DRIVER = re.compile(
    r"accepted_product_driver .*?control=(0x[0-9A-F]+) "
    r"window=(\d+)-(\d+),(\d+)-(\d+) bytes=(\d+) regions=(\d+) "
    r"charger_window=(\d+) recording_overlay=(\d+) "
    r"recording_overlay_only=(\d+).*?blink_compose_ms=(\d+)"
)
STATUS = re.compile(r"\[screen-status\] p=([0-9A-F]{8}) lp=([01])")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--ble", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    ble = json.loads(Path(args.ble).read_text(encoding="utf-8"))
    low_power_match = next(
        (match for match in STATUS.finditer(text) if match.group(2) == "1"),
        None,
    )
    tail = text[low_power_match.start():] if low_power_match is not None else ""
    connected_at = tail.find("[ble] connected handle=")
    status_events: list[dict[str, int]] = []
    candidates: list[dict[str, int | str]] = []
    for status_match in STATUS.finditer(tail):
        next_status = STATUS.search(tail, status_match.end())
        driver_match = DRIVER.search(
            tail,
            status_match.end(),
            next_status.start() if next_status is not None else len(tail),
        )
        packed = int(status_match.group(1), 16)
        status_events.append(
            {
                "packed": packed,
                "low_power": int(status_match.group(2)),
                "clock_valid": 1 if packed & 0x8000 else 0,
                "ble_connected": 1 if packed & (1 << 16) else 0,
                "battery_valid": 1 if packed & (1 << 17) else 0,
                "hour": (packed >> 8) & 0x1F,
                "minute": packed & 0x3F,
            }
        )
        if driver_match is None:
            continue
        match = driver_match
        control, x0, x1, y0, y1, count, regions, charger, recording, only, compose = match.groups()
        item = {
            "control": control,
            "x_start_byte": int(x0),
            "x_end_byte": int(x1),
            "y_start": int(y0),
            "y_end": int(y1),
            "bytes": int(count),
            "regions": int(regions),
            "charger_window": int(charger),
            "recording_overlay": int(recording),
            "recording_overlay_only": int(only),
            "blink_compose_ms": int(compose),
        }
        if (
            item["bytes"] > 0
            and item["charger_window"] == 0
            and item["recording_overlay"] == 0
            and item["recording_overlay_only"] == 0
            and item["blink_compose_ms"] == 0
        ):
            candidates.append(item)

    top_only = [
        item for item in candidates
        if item["control"] == "0xCF"
        and item["y_start"] >= 184
        and item["y_end"] <= 199
        and item["regions"] == 1
        and item["bytes"] <= 400
    ]
    faults = [
        token for token in (
            "HardFault", "BUSY timeout", "panel failure", "result=0",
            "stalled_mask=0x01", "stalled_mask=0x02", "stalled_mask=0x04",
            "stalled_mask=0x08", "stalled_mask=0x10", "stalled_mask=0x20",
        ) if token in text
    ]
    checks = {
        "real_ble_path": ble.get("status") == "PASS_REAL_RADIO",
        "low_power_status_observed": low_power_match is not None,
        "connected_observed_in_low_power": connected_at >= 0,
        "three_runtime_updates": len(top_only) >= 3,
        "clock_region_observed": any(item["x_start_byte"] <= 7 for item in top_only),
        "ble_region_twice": sum(item["x_start_byte"] >= 18 for item in top_only) >= 2,
        "all_status_candidates_top_only": len(candidates) == len(top_only),
        "no_full_after_connect": "control=0xC7" not in tail and "control=0xFF" not in tail,
        "wake_rebaseline_observed": tail.count("status_bar_wake rebaseline_no_activation=1") >= 3,
        "deep_sleep_resealed": tail.count("deep_sleep command=0x10 data=0x01") >= 3,
        "real_clock_observed": any(event["clock_valid"] for event in status_events),
        "connected_and_disconnected_observed": (
            any(event["ble_connected"] for event in status_events)
            and any(not event["ble_connected"] for event in status_events)
        ),
        "no_fake_battery_on_unmeasured_board": all(
            not event["battery_valid"] for event in status_events
        ),
        "no_faults": not faults,
    }
    result = {
        "schema": "companion.comp_req_785.statusbar_runtime.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "status_transactions": top_only,
        "status_events": status_events,
        "faults": faults,
        "hardware_contact": 1,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
