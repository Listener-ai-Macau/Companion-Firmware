#!/usr/bin/env python3
"""Verify the COMP-REQ-775 low-power-to-recording physical paint order."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def first_after(lines: list[str], marker: str, after: int = -1) -> int | None:
    for index in range(after + 1, len(lines)):
        if marker in lines[index]:
            return index
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw = args.log.read_bytes()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    lp_enter = first_after(lines, "low_power_boundary=enter")
    deferred = first_after(lines, "action=fsm_status_deferred", lp_enter or -1)
    wake = first_after(lines, "low_power_boundary=wake", deferred or -1)
    gc_done = first_after(lines, "accepted_gc_full", wake or -1)
    settle_done = first_after(lines, "accepted_fast_full", gc_done or -1)
    gate_done = first_after(
        lines, "action=low_power_wake result=1 committed=1", settle_done or -1)
    first_mic = first_after(lines, "mic_local_partial only=1", settle_done or -1)
    stop = first_after(lines, "action=stop_queue", first_mic or -1)

    ordered = all(value is not None for value in (
        lp_enter, deferred, wake, gc_done, settle_done, gate_done,
        first_mic, stop))
    if ordered:
        ordered = (lp_enter < deferred < wake < gc_done < settle_done
                   < gate_done < first_mic < stop)

    recording_lines = (lines[first_mic:stop + 1]
                       if first_mic is not None and stop is not None else [])
    lifecycle_during_recording = [
        line for line in recording_lines
        if re.search(r"control=0x(?:C7|F7|FF)\b", line)
    ]
    faults = [line for line in lines if "HardFault" in line or "IWDG" in line]
    unhealthy = [line for line in lines if re.search(
        r"stalled_mask=0x0[1-9A-Fa-f]|(?:pcm_)?drops=[1-9]", line)]
    settle_gate_clear = (
        gate_done is not None and "mode2_settle_pending=0" in lines[gate_done])
    mic_only = bool(recording_lines) and all(
        "only=1" in line for line in recording_lines
        if "mic_local_partial" in line)

    checks = {
        "lp_enter_then_recording_start_deferred": (
            lp_enter is not None and deferred is not None and lp_enter < deferred),
        "wake_gc_settle_gate_mic_physical_order": ordered,
        "mode2_settle_flag_clear_before_mic": settle_gate_clear,
        "no_lifecycle_full_during_recording": not lifecycle_during_recording,
        "recording_mic_path_remains_only1": mic_only,
        "watchdog_audio_and_faults_clean": not faults and not unhealthy,
    }
    result = {
        "schema": "companion.comp_req_775.lp_recording_boundary.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "log": str(args.log.resolve()),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "checks": checks,
        "line_numbers": {
            "lp_enter": None if lp_enter is None else lp_enter + 1,
            "fsm_status_deferred": None if deferred is None else deferred + 1,
            "wake": None if wake is None else wake + 1,
            "gc_done": None if gc_done is None else gc_done + 1,
            "mode2_settle_done": None if settle_done is None else settle_done + 1,
            "wake_gate_done": None if gate_done is None else gate_done + 1,
            "first_mic_only1": None if first_mic is None else first_mic + 1,
            "stop_queue": None if stop is None else stop + 1,
        },
        "lifecycle_during_recording": lifecycle_during_recording,
        "faults_or_unhealthy": faults + unhealthy,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
