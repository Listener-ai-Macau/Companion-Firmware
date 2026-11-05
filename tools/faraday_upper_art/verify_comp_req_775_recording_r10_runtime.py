#!/usr/bin/env python3
"""Verify the focused COMP-REQ-775 recording R10 runtime trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"([a-zA-Z0-9_]+)=([^\s]+)", line))


def window(row: dict[str, str]) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"(\d+)-(\d+),(\d+)-(\d+)", row.get("window", ""))
    if match is None:
        raise ValueError(f"missing runtime window: {row}")
    return tuple(int(value) for value in match.groups())


def long_path(path: Path) -> Path:
    absolute = path.absolute()
    if os.name == "nt" and not str(absolute).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(absolute))
    return absolute


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    log_path = long_path(args.log)
    output_path = long_path(args.output)
    raw = log_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    starts = [line for line in lines if "action=overlay_start result=1" in line]
    stops = [line for line in lines if "signal=10" in line and "accepted=1" in line]
    ram = [fields(line) for line in lines if "[epaper] recording_ram_contract" in line]
    active_ram = [row for row in ram if row.get("present") == "1"]
    clear_ram = [row for row in ram if row.get("present") == "0"]
    traces = [fields(line) for line in lines if "[record-visual] action=overlay_trace" in line]
    visible = [row for row in traces if row.get("visible") == "1"]
    pure_visible = []
    for row in visible:
        x_start, x_end, y_start, y_end = window(row)
        if x_end <= 4 and y_start >= 20:
            window_bytes = (x_end - x_start + 1) * (y_end - y_start + 1)
            pure_visible.append((row, window_bytes))
    exit_reports = []
    for line in lines:
        if "[epaper] accepted_product_driver" not in line:
            continue
        row = fields(line)
        if (
            row.get("recording_overlay") == "0"
            and row.get("recording_overlay_only") == "1"
            and row.get("previous_plane_sync") == "1"
        ):
            exit_reports.append(row)

    checks = {
        "overlay_started": len(starts) == 1,
        "overlay_stop_accepted": len(stops) >= 1,
        "active_frames_observed": len(active_ram) >= 10,
        "entry_stages_white_to_full_microphone": bool(active_ram)
        and active_ram[0].get("body_black_previous") == "0"
        and active_ram[0].get("body_black_current") == "108",
        "steady_microphone_present_in_old_and_current": len(active_ram) >= 2
        and all(
            row.get("body_black_previous") == "108"
            and row.get("body_black_current") == "108"
            for row in active_ram[1:]
        ),
        "visible_recording_frames_are_single_cf": len(visible) >= 10
        and all(row.get("control") == "0xCF" for row in visible),
        "pure_delta_uses_three_plane_transfers": len(pure_visible) >= 4
        and all(int(row["bytes"]) == 3 * window_bytes for row, window_bytes in pure_visible),
        "composed_recording_frames_observed": any(
            window(row)[1] >= 20 for row in visible
        ),
        "recording_clear_observed": bool(clear_ram)
        and clear_ram[-1].get("body_black_previous") == "108"
        and clear_ram[-1].get("body_black_current") == "0",
        "clear_uses_old_current_post_current": len(exit_reports) == 1
        and exit_reports[0].get("control") == "0xCF"
        and exit_reports[0].get("post_sync_command") == "0x24"
        and exit_reports[0].get("post_sync_refresh") == "0"
        and int(exit_reports[0].get("bytes", "0"))
        == 3 * int(exit_reports[0].get("post_sync_bytes", "-1")),
        "no_full_refresh_in_capture": "control=0xFF" not in text
        and "control=0xC7" not in text,
        "recording_codec3_stored": bool(
            re.search(r"\[rec-flash\] stored .* codec=3 ", text)
        ),
        "watchdog_healthy": "[watchdog] healthy=1" in text,
        "no_missing_committed_base": "reason=no_committed_base" not in text,
    }
    result = {
        "schema_id": "companion.comp_req_775.recording_r10_runtime.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "log": str(args.log.absolute()),
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "counts": {
            "active_ram_frames": len(active_ram),
            "visible_recording_frames": len(visible),
            "pure_delta_visible_frames": len(pure_visible),
            "composed_visible_frames": sum(
                window(row)[1] >= 20 for row in visible
            ),
            "clear_reports": len(exit_reports),
        },
        "checks": checks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
