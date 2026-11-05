"""Verify the physical center/corner recording gesture policy after flash."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / ".cache/validation/comp776-component-clip-fix-20260812"
LOG = PACKAGE / "recording-entry-policy-hardware/nucleo-serial-raw.log"
OUTPUT = PACKAGE / "recording-entry-policy-hardware/MACHINE_READY.json"


def main() -> int:
    raw = LOG.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    rows = re.findall(
        r"daily_double_tap_recording x=(\d+) y=(\d+) state=([^ ]+) "
        r"corner=(\d+) allowed=(\d+) submitted=(\d+) pending=(\d+)", text)
    center = [row for row in rows if row[3:] == ("0", "0", "0", "0")]
    corner = [row for row in rows if row[3] == "1" and row[4] == "1" and row[5] == "1"]
    checks = {
        "new_app_boots_generation_20": (
            "ui_generation=active generation=20 resource_id=027D69E2" in text
            and "page_sha256=5C04FB7AC7B0B1A2585E39BF125DCA970F26AEDF1729D97295C2C1A1C1D69762" in text
        ),
        "idle_center_double_tap_never_submits_recording": len(center) >= 3,
        "mic_corner_double_tap_submits_recording": len(corner) >= 1,
        "physical_recording_starts": "touch_double_tap action=start source=2 result=0 state=recording" in text,
        "active_recording_center_exit_completes": (
            "recording_exit_intent gesture=down scope=anywhere armed=1" in text
            and "touch_double_tap action=stop source=2 stop_result=0" in text
            and "touch_double_tap action=sync_complete state=idle" in text
        ),
        "no_fault_or_watchdog_failure": (
            "HardFault" not in text and "healthy=0" not in text and "stalled_mask=0x00" in text
        ),
        "focused_window_did_not_enter_low_power": (
            "low_power_boundary=enter" not in text
            and "family=sleepy" not in text
            and "expression=sleepy" not in text
        ),
    }
    report = {
        "schema": "companion.comp_req_776.recording_entry_policy_log.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "observed": {
            "gesture_rows": len(rows),
            "center_rejected_rows": len(center),
            "corner_allowed_rows": len(corner),
            "bashful_family_rows": text.count("family=bashful"),
            "sleepy_family_rows": text.count("family=sleepy"),
            "low_power_enter_rows": text.count("low_power_boundary=enter"),
        },
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "hardware_contact": 1,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
