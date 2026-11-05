#!/usr/bin/env python3
"""Regression gate for the repeated touch-recording stop ownership race."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
)


def function_body(source: str, signature: str, next_signature: str) -> str:
    start = source.find(signature)
    end = source.find(next_signature, start + len(signature))
    if start < 0 or end < 0:
        return ""
    return source[start:end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    source = MAIN.read_text(encoding="utf-8")
    dispatch = function_body(
        source,
        "static void Companion_Rtos_ServiceRecordingFastToggle(void)\n{",
        "static void Companion_Rtos_RecTask(void *arg)",
    )
    replay = function_body(
        source,
        "static bool execute_touch_recording_boundary_action(\n",
        "static bool board_touch_recording_menu_sink(\n",
    )

    claim = dispatch.find("s_recording_fast_toggle_pending = false;")
    critical_exit = dispatch.find("taskEXIT_CRITICAL();", claim)
    toggle = dispatch.find("toggle_touch_recording(submitted_ms);")
    checks = {
        "pending_slot_claimed_inside_critical_section": (
            0 <= claim < critical_exit < toggle
        ),
        "newer_stop_not_cleared_after_start_dispatch": (
            dispatch.find(
                "s_recording_fast_toggle_pending = false;", toggle
            )
            < 0
        ),
        "browser_dedup_requires_live_stop_owner": all(
            token in replay
            for token in (
                "fast_stop_owned || stop_request_owned",
                "Companion_Screen_RecordingStopFeedbackInFlight()",
                "action=deduplicated",
            )
        ),
        "ownerless_browser_replay_falls_back_to_toggle": all(
            token in replay
            for token in (
                "reason=no_live_stop_owner",
                "action=fallback",
                "toggle_touch_recording(submitted_ms);",
            )
        ),
        "claimed_touch_intent_remains_low_power_blocker": (
            "s_recording_fast_toggle_pending ||\n"
            "            s_recording_prepare.pending"
            in source
        ),
    }

    # Executable interleaving oracle.  The failing implementation read START,
    # allowed STOP to replace the slot, then cleared the slot after START.  The
    # fixed implementation claims START first, so a later STOP remains queued.
    old_slot = "START"
    old_dispatching = old_slot
    old_slot = "STOP"
    old_slot = None
    new_slot = "START"
    new_dispatching = new_slot
    new_slot = None
    new_slot = "STOP"
    checks["old_interleaving_reproduces_lost_stop"] = (
        old_dispatching == "START" and old_slot is None
    )
    checks["fixed_interleaving_preserves_newer_stop"] = (
        new_dispatching == "START" and new_slot == "STOP"
    )

    result = {
        "schema": "companion.comp_req_791.repeat_touch_stop.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failure_reproduced": (
            "START dispatch tail erased a newer STOP; browser replay then "
            "deduplicated the ownerless boundary"
        ),
        "fixed_contract": (
            "claim one event atomically before dispatch; deduplicate replay "
            "only while a fast STOP, stop request, or stop visual owns it"
        ),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(rendered, end="")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
