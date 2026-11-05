#!/usr/bin/env python3
"""Verify that touch recording stop feedback commits before flash finalize."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def last_index(lines: list[str], pattern: str) -> int:
    matches = [index for index, line in enumerate(lines) if pattern in line]
    return matches[-1] if matches else -1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    stop_index = last_index(lines, "touch_double_tap action=stop_queued result=1")
    queue_index = last_index(lines, "[record-visual] action=stop_queue result=1")
    commit_index = last_index(lines, "[record-visual] action=stop_commit")
    resume_index = last_index(lines, "[record-visual] action=resume_daily")
    handoff_index = last_index(lines, "[record-stop] stage=visual_handoff")
    finalize_index = last_index(lines, "[record-stop] stage=finalize_begin")
    store_index = last_index(lines, "action=user_store result=1")

    commit_line = lines[commit_index] if commit_index >= 0 else ""
    queue_line = lines[queue_index] if queue_index >= 0 else ""
    handoff_line = lines[handoff_index] if handoff_index >= 0 else ""
    request_match = re.search(r"request=(\d+)", commit_line)
    request_id = request_match.group(1) if request_match else ""
    panel_index = last_index(
        lines, f"accepted_product_driver request={request_id}"
    ) if request_id else -1
    panel_line = lines[panel_index] if panel_index >= 0 else ""
    wait_match = re.search(r"wait_ms=(\d+)", handoff_line)
    wait_ms = int(wait_match.group(1)) if wait_match else None
    gesture_visible_match = re.search(
        r"gesture_to_visible_ms=(\d+)", commit_line
    )
    gesture_to_visible_ms = (
        int(gesture_visible_match.group(1)) if gesture_visible_match else None
    )

    checks = {
        "touch_stop_was_submitted": stop_index >= 0,
        "authored_exit_was_queued": queue_index >= 0,
        "exact_browser_return_frame_was_queued": (
            "restore_clip=" in queue_line
            and "restore_frame=" in queue_line
            and "restore_in_clip=" in queue_line
            and "discarded_recording_frames=" in queue_line
        ),
        "panel_commit_was_visible": "visible=1" in commit_line,
        "exit_refresh_was_fast_full": (
            "control=0xC7" in panel_line
            and "bytes=5000" in panel_line
            and "maintenance=1" in panel_line
        ),
        "panel_commit_preceded_finalize": (
            0 <= stop_index <= queue_index <= panel_index <= commit_index
            <= handoff_index <= finalize_index
        ),
        "visual_handoff_resolved_without_timeout": (
            "resolved=1" in handoff_line
            and "visible=1" in handoff_line
            and "timeout=0" in handoff_line
        ),
        "gesture_to_visible_within_boundary_budget": (
            gesture_to_visible_ms is not None and gesture_to_visible_ms <= 2600
        ),
        "recording_was_stored_after_finalize": store_index > finalize_index,
        "daily_choreography_resumed_after_restore_commit": (
            commit_index < resume_index < handoff_index
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.recording_stop_handoff.v1",
        "status": "MACHINE_READY" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "log": str(args.log.resolve()),
        "request_id": request_id or None,
        "visual_wait_ms": wait_ms,
        "gesture_to_visible_ms": gesture_to_visible_ms,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
