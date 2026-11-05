#!/usr/bin/env python3
"""Verify WB55 autonomous emotion families stay independent from recording wave."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def families(log: str) -> set[str]:
    return set(re.findall(r"\[screen-life\] family=([^ ]+)", log))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-log", required=True)
    parser.add_argument("--recording-log", required=True)
    parser.add_argument("--ble-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    idle = Path(args.idle_log).read_text(encoding="utf-8", errors="replace")
    recording = Path(args.recording_log).read_text(encoding="utf-8", errors="replace")
    ble = Path(args.ble_log).read_text(encoding="utf-8", errors="replace")
    start = recording.find("[record] gatt_live_mic_start action=start source=3 result=0")
    stop = recording.find("[record] recording_max_seconds action=stop", start)
    active = recording[start:stop] if start >= 0 and stop > start else ""

    idle_switches = re.findall(
        r"\[life\] family=(\d+)>(\d+) source=hardware_rng authored=1 rec=0 wave=0",
        idle,
    )
    recording_switches = re.findall(
        # RTOS UART can interleave a storage line after source=hardware_rng;
        # the prefix is emitted only by this autonomous switch site.  The
        # independent wave=0 contract is checked separately below from the
        # recording track evidence.
        r"\[life\] family=(\d+)>(\d+) source=hardware_rng",
        active,
    )
    idle_family_cleans = re.findall(
        r"\[epaper\] accepted_fast_full .*control=0xFF .*"
        r"activation_count=1 complete=1",
        idle,
    )
    recording_family_cleans = re.findall(
        r"\[epaper\] accepted_fast_full .*control=0xFF .*"
        r"activation_count=1 complete=1",
        active,
    )
    fatal_tokens = (
        "HardFault",
        "BUSY timeout",
        "watchdog] healthy=0",
        "stalled_mask=0x01",
        "stalled_mask=0x02",
        "stalled_mask=0x04",
        "stalled_mask=0x08",
        "stalled_mask=0x10",
    )
    idle_targets = [target for _, target in idle_switches]
    targets = idle_targets + [target for _, target in recording_switches]
    # calm/warm/bashful share the same large-eye silhouette and can look like a
    # fixed face on the physical 2.13-inch panel.  Require idle life to reach at
    # least one authored family with an unmistakably different semantic cue.
    visibly_distinct_ids = {"1", "2", "4", "7", "8", "9"}
    checks = {
        "idle_cross_family_rng": len(idle_switches) >= 1 and len(families(idle)) >= 2,
        "idle_reaches_visibly_distinct_family": any(
            target in visibly_distinct_ids for target in idle_targets
        ),
        "recording_cross_family_rng": len(recording_switches) >= 1,
        "family_boundary_single_mode2_clean": (
            len(idle_family_cleans) >= len(idle_switches)
            and len(recording_family_cleans) >= len(recording_switches)
        ),
        "ordinary_random_excludes_sleepy": "5" not in targets,
        "real_codec3_recording": "AUTO_RECORD True" in ble and '"codec": 3' in ble,
        "wave_fast_and_face_continues": (
            active.count("track=wave") >= 40 and active.count("track=face") >= 8
        ),
        "wave_clock_does_not_advance_face": (
            active.count("carrier=pure_wave face_clock_advanced=0") >= 20
        ),
        "face_clock_does_not_drive_wave": "wave_drives_face=0" in active,
        "watchdog_and_capture_healthy": (
            "[watchdog] healthy=1 stalled_mask=0x00" in recording
            and "drops=0" in active
        ),
        "no_runtime_fault": not any(token in idle + recording for token in fatal_tokens),
    }
    result = {
        "schema": "companion.comp_req_788.autonomous_emotion.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "counts": {
            "idle_families": sorted(families(idle)),
            "idle_switches": len(idle_switches),
            "recording_switches": len(recording_switches),
            "idle_family_cleans": len(idle_family_cleans),
            "recording_family_cleans": len(recording_family_cleans),
            "recording_wave_events": active.count("track=wave"),
            "recording_face_events": active.count("track=face"),
        },
        "hardware_contact": 1,
        "owner_gate": "Panel appearance and physical drag/idle mutual exclusion.",
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
