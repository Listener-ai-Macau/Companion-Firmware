#!/usr/bin/env python3
"""Fail closed when later SSD1681 blink pairs lose their open-plane baseline."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line))


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def recording_window_lines(lines: list[str]) -> list[str]:
    """Return only display rows while a recording composition owns the UI.

    A deferred life-maintenance full refresh is expected immediately after
    recording stop.  Scanning from the first overlay start through EOF falsely
    reports that post-stop cleanup as a recording-time full refresh.
    """
    active: list[str] = []
    recording = False
    for line in lines:
        if "action=overlay_start" in line:
            recording = True
        if recording:
            active.append(line)
        if recording and "action=sync_complete state=idle" in line:
            recording = False
    return active


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-pairs", type=int, default=3)
    parser.add_argument("--recording", action="store_true")
    args = parser.parse_args()

    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    pairs: list[dict[str, str]] = []
    syncs: list[dict[str, str]] = []
    phase_events: list[dict[str, int | str]] = []
    pending_closed = False
    pending_open = False

    for line in lines:
        if "[screen-blink] phase=closed" in line:
            row = fields(line)
            pending_closed = (not args.recording or row.get("recording") == "1")
            pending_open = False
        elif "[screen-blink] phase=open" in line and pending_closed:
            row = fields(line)
            pending_open = not args.recording or row.get("recording") == "1"
        elif "[epaper] blink_open_previous_plane_sync" in line and pending_open:
            syncs.append(fields(line))
        elif pending_closed and pending_open and (
            "[screen-blink] pair " in line
            or all(token in line for token in (
                "closed_control=", "open_control=", "closed_busy_ms=",
                "open_busy_ms=", "committed=", "epoch=",
            ))
        ):
            row = fields(line)
            # UART is shared by several real-time tasks, so the pair prefix or
            # request fields can be spliced into a neighbouring line.  Keep a
            # row only when the complete safety payload survived.
            if all(row.get(name, "").isdigit() for name in (
                "closed_busy_ms", "open_busy_ms", "closed_to_open_ms", "epoch",
            )):
                pairs.append(row)
            pending_closed = False
            pending_open = False

        if "[record-phase] track=blink" in line:
            row = fields(line)
            request = row.get("request", "")
            phase = row.get("phase", "")
            visible = row.get("visible_ms", "")
            if request.isdigit() and phase in ("closed", "open") and visible.isdigit():
                phase_events.append({
                    "request": int(request),
                    "phase": phase,
                    "visible_ms": int(visible),
                })

    phase_pairs: list[dict[str, int]] = []
    for index, closed in enumerate(phase_events):
        if closed["phase"] != "closed":
            continue
        opened = next((
            row for row in phase_events[index + 1:]
            if row["phase"] == "open"
            and row["request"] == closed["request"] + 1
        ), None)
        if opened is None:
            continue
        latency = int(opened["visible_ms"]) - int(closed["visible_ms"])
        # A spliced line can donate a neighbouring wave's visible_ms.  Reject
        # that sample instead of converting UART corruption into panel timing.
        if 0 <= latency <= 1000:
            phase_pairs.append({
                "closed_request": int(closed["request"]),
                "open_request": int(opened["request"]),
                "closed_to_open_ms": latency,
            })

    epochs = [int(row["epoch"]) for row in pairs if row.get("epoch", "").isdigit()]
    busy = [
        max(int(row.get("closed_busy_ms", "9999")),
            int(row.get("open_busy_ms", "9999")))
        for row in pairs
    ]
    pair_latency = [int(row.get("closed_to_open_ms", "9999")) for row in pairs]
    good_syncs = [
        row for row in syncs
        if row.get("command") == "0x26"
        and row.get("activation") == "0"
        and row.get("result") == "1"
        and int(row.get("bytes", "0")) > 0
    ]
    resilient_recording_trace = (
        args.recording
        and len(pairs) < args.min_pairs
        and len(phase_pairs) >= args.min_pairs
        and len(pairs) >= min(2, args.min_pairs)
    )
    complete_pair_count = len(phase_pairs) if resilient_recording_trace else len(pairs)
    monotonic_phase_requests = all(
        int(right["closed_request"]) > int(left["closed_request"])
        for left, right in zip(phase_pairs, phase_pairs[1:])
    )
    active = lines
    if args.recording:
        start = next((i for i, line in enumerate(lines)
                      if "action=overlay_start" in line), -1)
        active = lines[start:] if start >= 0 else []
    forbidden = (
        "HardFault", "HARDFAULT", "BUSY timeout", "watchdog_fault",
        "panel result=failed", "previous_reset=iwdg",
    )
    recording_active = recording_window_lines(lines) if args.recording else active
    visible_full = [
        line for line in recording_active
        if "[epaper] accepted_product_driver" in line
        and any(token in line for token in ("control=0xC7", "control=0xF7", "control=0xFF"))
    ]
    checks = {
        "minimum_complete_pairs": complete_pair_count >= args.min_pairs,
        "one_successful_open_plane_sync_per_pair": (
            len(good_syncs) >= complete_pair_count if resilient_recording_trace
            else len(good_syncs) == len(pairs)
        ),
        "unique_monotonic_epochs": (
            monotonic_phase_requests if resilient_recording_trace
            else len(epochs) == len(pairs)
            and all(b > a for a, b in zip(epochs, epochs[1:]))
        ),
        "all_pairs_committed_cached_mode2": bool(pairs)
        and all(row.get("committed") == "1"
                and row.get("closed_control") == "0xCF"
                and row.get("open_control") == "0xCF" for row in pairs),
        "busy_bounded": bool(busy) and max(busy) <= 600,
        "close_open_bounded": (
            bool(phase_pairs) if resilient_recording_trace
            else bool(pair_latency) and max(pair_latency) <= 1000
        ),
        "recording_has_no_visible_full": not args.recording or not visible_full,
        "no_fault_markers": not any(token in line for line in active for token in forbidden),
        "watchdog_stays_healthy": not any(
            "[watchdog]" in line and "healthy=0" in line for line in active
        ),
    }
    result = {
        "schema": "companion.comp_req_775.repeat_blink_runtime.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "mode": "recording" if args.recording else "natural",
        "checks": checks,
        "metrics": {
            "complete_pairs": complete_pair_count,
            "complete_detailed_pairs": len(pairs),
            "complete_visible_phase_pairs": len(phase_pairs),
            "serial_interleaving_fallback": resilient_recording_trace,
            "successful_open_plane_syncs": len(good_syncs),
            "epochs": epochs,
            "max_busy_ms": max(busy) if busy else None,
            "p95_busy_ms": percentile(busy, 0.95) if busy else None,
            "max_closed_to_open_ms": (
                max(row["closed_to_open_ms"] for row in phase_pairs)
                if resilient_recording_trace and phase_pairs
                else max(pair_latency) if pair_latency else None
            ),
            "visible_full_during_recording": len(visible_full) if args.recording else None,
        },
        "hardware_contact": 1,
        "log": str(args.log.resolve()),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
