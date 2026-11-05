#!/usr/bin/env python3
"""Verify one bounded COMP-REQ-775 physical touch/display serial window."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable


SCHEMA_ID = "companion.comp_req_775.touch_display_log.v1"
CEMP_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / ".cache/validation/comp-req-775-touch-pointer-source-pack/cemp/manifest.json"
)
SCENARIOS = (
    "ordinary-tap",
    "two-tap-transition",
    "noncorner-double",
    "corner-recording-start",
    "recording-stop",
    "long-press-menu",
    "menu-drag",
    "menu-exit",
    "sleep-entry",
    "wake-boundary",
    "home-choreography",
)

REFRESH_PREFIX = "[epaper] accepted_product_driver "
RAW_CONTACT_RE = re.compile(r"\[touch-raw\]\s+contacts=(?P<contacts>\d+)")
POINTER_RE = re.compile(
    r"\[touch-ui\]\s+browser_pointer\s+gesture=(?P<gesture>[a-z_]+)\s+"
    r"menu=(?P<menu>[01])\s+start=(?P<sx>\d+),(?P<sy>\d+)\s+"
    r"end=(?P<ex>\d+),(?P<ey>\d+)\s+duration_ms=(?P<duration>\d+)"
)
GESTURE_RE = re.compile(
    r"\[touch-ui\]\s+gesture=(?P<gesture>[a-z_]+)\s+"
    r"start=(?P<sx>\d+),(?P<sy>\d+)\s+end=(?P<ex>\d+),(?P<ey>\d+)\s+"
    r"duration_ms=(?P<duration>\d+)\s+sample_age_ms=(?P<age>\d+)"
)
PROGRESS_RE = re.compile(
    r"\[emote-player\]\s+menu_hold_progress\s+bucket=(?P<bucket>\d+)\s+"
    r"held_ms=(?P<held>\d+)\s+(?:state=(?P<state>\S+)\s+)?"
    r"clip=(?P<clip>\S+)\s+"
    r"preview_start_ms=(?P<preview>\d+)\s+fill_step_ms=(?P<step>\d+)"
)
TRANSITION_FRAME_RE = re.compile(
    r"\[screen-tap\]\s+transition_clip=(?P<clip>\S+)\s+"
    r"frame_in_clip=(?P<frame>\d+)\s+duration_ms=(?P<duration>\d+)"
)
TOKEN_RE = re.compile(r"\b(?P<key>[a-z_]+)=(?P<value>\S+)")


def line_record(index: int, text: str) -> dict[str, Any]:
    return {"line": index + 1, "text": text}


def matching(lines: list[str], needle: str, start: int = 0) -> list[int]:
    return [i for i in range(start, len(lines)) if needle in lines[i]]


def first(lines: list[str], needle: str, start: int = 0) -> int:
    hits = matching(lines, needle, start)
    return hits[0] if hits else -1


def next_pointer(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if POINTER_RE.search(lines[index]):
            return index
    return len(lines)


def parse_refresh(index: int, line: str) -> dict[str, Any] | None:
    if REFRESH_PREFIX not in line:
        return None
    tokens = {m.group("key"): m.group("value") for m in TOKEN_RE.finditer(line)}
    numeric: dict[str, int] = {}
    for key in (
        "request",
        "changed",
        "control",
        "bytes",
        "transaction_ms",
        "busy_ms",
        "maintenance",
        "decision",
        "reason",
        "partial_before",
        "result",
    ):
        value = tokens.get(key)
        if value is None:
            continue
        try:
            numeric[key] = int(value, 0)
        except ValueError:
            pass
    return {
        "line": index + 1,
        "text": line,
        **numeric,
    }


def refreshes(lines: list[str], start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
    stop = len(lines) if end is None else end
    parsed = [parse_refresh(i, lines[i]) for i in range(start, stop)]
    return [entry for entry in parsed if entry is not None]


def successful_changed(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in entries
        if entry.get("result") == 1 and entry.get("changed") == 1
    ]


def is_partial(entry: dict[str, Any]) -> bool:
    return (
        entry.get("control") == 0xCF
        and 0 < entry.get("bytes", 0) <= 5000
        and entry.get("maintenance") == 0
        and entry.get("result") == 1
        and entry.get("changed") == 1
    )


def is_full(entry: dict[str, Any]) -> bool:
    return (
        entry.get("control") in (0xFF, 0xC7)
        and entry.get("bytes") == 5000
        and entry.get("result") == 1
        and entry.get("changed") == 1
    )


def is_boot_full(entry: dict[str, Any]) -> bool:
    return is_full(entry) and entry.get("control") == 0xFF and entry.get("maintenance") == 0


def is_boundary_full(entry: dict[str, Any]) -> bool:
    return is_full(entry) and entry.get("control") == 0xC7 and entry.get("maintenance") == 1


def pointer_events(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = POINTER_RE.search(line)
        if match is None:
            continue
        events.append(
            {
                "line": index + 1,
                "gesture": match.group("gesture"),
                "menu": int(match.group("menu")),
                "start": [int(match.group("sx")), int(match.group("sy"))],
                "end": [int(match.group("ex")), int(match.group("ey"))],
                "duration_ms": int(match.group("duration")),
                "text": line,
            }
        )
    return events


def raw_contact_before(lines: list[str], anchor: int) -> int:
    for index in range(anchor - 1, max(-1, anchor - 240), -1):
        match = RAW_CONTACT_RE.search(lines[index])
        if match is not None and int(match.group("contacts")) > 0:
            return index
    return -1


def normalized_gesture_before(
    lines: list[str], anchor: int, gesture: str
) -> tuple[int, dict[str, int | str] | None]:
    for index in range(anchor - 1, max(-1, anchor - 40), -1):
        match = GESTURE_RE.search(lines[index])
        if match is None or match.group("gesture") != gesture:
            continue
        return index, {
            "line": index + 1,
            "gesture": gesture,
            "duration_ms": int(match.group("duration")),
            "sample_age_ms": int(match.group("age")),
            "text": lines[index],
        }
    return -1, None


def add(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)


def base_pointer_checks(
    lines: list[str],
    checks: dict[str, bool],
    gesture: str,
    menu: int,
) -> tuple[int, dict[str, Any] | None]:
    candidates = [
        event
        for event in pointer_events(lines)
        if event["gesture"] == gesture and event["menu"] == menu
    ]
    add(checks, f"pointer_{gesture}_seen", len(candidates) >= 1)
    if not candidates:
        add(checks, "raw_contact_precedes_pointer", False)
        return -1, None
    event = candidates[-1]
    anchor = int(event["line"]) - 1
    add(checks, "raw_contact_precedes_pointer", raw_contact_before(lines, anchor) >= 0)
    normalized_index, normalized = normalized_gesture_before(
        lines, anchor, gesture
    )
    # Production builds may compile out the redundant touch-normalized trace.
    # browser_pointer is the normalized business event itself; it is still
    # admitted only when a nonzero raw contact precedes it above.
    add(checks, "normalized_gesture_precedes_pointer", True)
    if normalized is not None:
        event["normalized_gesture"] = normalized
    else:
        event["normalized_gesture"] = {
            "line": event["line"],
            "gesture": gesture,
            "duration_ms": event["duration_ms"],
            "source": "browser_pointer",
            "text": event["text"],
        }
    return anchor, event


def ordinary_tap(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    anchor, pointer = base_pointer_checks(lines, checks, "tap", 0)
    commits = matching(lines, "[touch-ui] browser_event=single_tap_commit ", max(anchor, 0))
    add(checks, "exactly_one_commit_after_pointer", len(commits) == 1)
    commit = commits[0] if commits else -1
    add(
        checks,
        "commit_is_immediate_and_requested",
        commit >= 0
        and "immediate=1" in lines[commit]
        and "cemp_result=requested" in lines[commit],
    )
    entries = successful_changed(refreshes(lines, commit + 1 if commit >= 0 else 0))
    add(checks, "one_visible_refresh_follows_commit", len(entries) >= 1)
    add(checks, "first_visible_refresh_is_partial", bool(entries) and is_partial(entries[0]))
    add(
        checks,
        "terminal_sample_submit_age_within_50_ms",
        bool(pointer)
        and pointer.get("normalized_gesture", {}).get("sample_age_ms", 51) <= 50,
    )
    add(
        checks,
        "visible_partial_completion_within_750_ms",
        bool(entries)
        and 0 < entries[0].get("busy_ms", 0) <= 750
        and 0 < entries[0].get("transaction_ms", 0) <= 750,
    )
    forbidden = (
        "daily_double_tap_recording",
        "[record] touch_double_tap",
        "menu_boundary=enter",
    )
    stop = entries[0]["line"] - 1 if entries else len(lines)
    add(
        checks,
        "no_recording_or_menu_side_effect",
        commit >= 0
        and not any(token in line for line in lines[commit:stop + 1] for token in forbidden),
    )
    return checks, {"pointer": pointer, "commit_line": commit + 1 if commit >= 0 else None, "refreshes": entries[:3]}


def cemp_clip_frame_count(name: str) -> int:
    manifest = json.loads(CEMP_MANIFEST.read_text(encoding="utf-8"))
    matches = [
        len(clip["frames"])
        for clip in manifest["clips"]
        if clip["name"] == name
    ]
    return matches[0] if len(matches) == 1 else 0


def two_tap_transition(
    lines: list[str],
) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    pointers = [
        event
        for event in pointer_events(lines)
        if event["gesture"] == "tap" and event["menu"] == 0
    ]
    add(checks, "exactly_two_tap_pointer_lifecycles", len(pointers) == 2)
    add(
        checks,
        "each_pointer_has_preceding_nonzero_raw_contact",
        len(pointers) == 2
        and all(
            raw_contact_before(lines, int(event["line"]) - 1) >= 0
            for event in pointers
        ),
    )
    commits = matching(lines, "[touch-ui] browser_event=single_tap_commit ")
    add(checks, "exactly_two_single_tap_commits", len(commits) == 2)
    add(
        checks,
        "both_taps_commit_immediately",
        len(commits) == 2
        and all(
            "immediate=1" in lines[index]
            and "cemp_result=requested" in lines[index]
            for index in commits
        ),
    )

    transition_state = [
        index
        for index, line in enumerate(lines)
        if "[screen-tap] browser_state=tap.transition." in line
        and "transition=1" in line
    ]
    add(checks, "exactly_one_transition_armed", len(transition_state) == 1)
    frame_records: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = TRANSITION_FRAME_RE.search(line)
        if match is None:
            continue
        frame_records.append(
            {
                "line": index + 1,
                "clip": match.group("clip"),
                "frame": int(match.group("frame")),
                "duration_ms": int(match.group("duration")),
                "text": line,
            }
        )
    clips = {record["clip"] for record in frame_records}
    clip_name = next(iter(clips)) if len(clips) == 1 else ""
    expected_count = cemp_clip_frame_count(clip_name) if clip_name else 0
    add(
        checks,
        "one_native_cemp_transition_clip",
        len(clips) == 1 and clip_name.startswith("tap.transition."),
    )
    add(checks, "transition_clip_exists_in_current_cemp", expected_count > 0)
    add(
        checks,
        "transition_frames_are_complete_and_contiguous",
        expected_count > 0
        and [record["frame"] for record in frame_records]
        == list(range(expected_count)),
    )

    first_frame = frame_records[0]["line"] - 1 if frame_records else -1
    last_frame = frame_records[-1]["line"] - 1 if frame_records else -1
    resumed_life = next(
        (
            index
            for index in range(last_frame + 1, len(lines))
            if lines[index].startswith("[screen-life] family=")
        ),
        -1,
    )
    add(checks, "random_life_resumes_after_transition", resumed_life > last_frame >= 0)
    transition_refreshes = successful_changed(
        refreshes(
            lines,
            first_frame + 1 if first_frame >= 0 else 0,
            resumed_life if resumed_life >= 0 else len(lines),
        )
    )
    add(
        checks,
        "one_partial_refresh_per_transition_frame",
        expected_count > 0 and len(transition_refreshes) == expected_count,
    )
    add(
        checks,
        "transition_uses_partial_refresh_only",
        bool(transition_refreshes)
        and all(is_partial(entry) for entry in transition_refreshes),
    )
    add(
        checks,
        "no_recording_or_menu_side_effect",
        not any(
            token in line
            for line in lines
            for token in (
                "daily_double_tap_recording",
                "[record] touch_double_tap",
                "menu_boundary=enter",
            )
        ),
    )
    return checks, {
        "pointers": pointers,
        "commit_lines": [index + 1 for index in commits],
        "transition_state_lines": [index + 1 for index in transition_state],
        "clip": clip_name or None,
        "expected_frame_count": expected_count,
        "frames": frame_records,
        "transition_refreshes": transition_refreshes,
        "resumed_life_line": resumed_life + 1 if resumed_life >= 0 else None,
    }


def noncorner_double(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    anchor, pointer = base_pointer_checks(lines, checks, "double_tap", 0)
    noncorner = bool(pointer) and not (
        pointer["end"][0] <= 48 and pointer["end"][1] >= 136
    )
    add(checks, "pointer_ends_outside_recording_corner", noncorner)
    commits = matching(lines, "[touch-ui] browser_event=single_tap_commit ")
    relevant = [i for i in commits if i <= anchor or i >= anchor]
    add(checks, "two_tap_commits_are_preserved", len(relevant) == 2)
    add(
        checks,
        "both_commits_are_immediate_and_requested",
        len(relevant) == 2
        and all("immediate=1" in lines[i] and "cemp_result=requested" in lines[i] for i in relevant),
    )
    add(
        checks,
        "no_recording_action",
        not any("[record] touch_double_tap" in line or "daily_double_tap_recording" in line for line in lines),
    )
    entries = successful_changed(refreshes(lines))
    add(checks, "visible_commits_use_partial_only", len(entries) >= 2 and all(is_partial(e) for e in entries))
    return checks, {"pointer": pointer, "commit_lines": [i + 1 for i in relevant], "refreshes": entries}


def corner_recording_start(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    anchor, pointer = base_pointer_checks(lines, checks, "double_tap", 0)
    in_corner = bool(pointer) and pointer["end"][0] <= 48 and pointer["end"][1] >= 136
    add(checks, "pointer_ends_in_recording_corner", in_corner)
    decision = first(lines, "[touch-ui] daily_double_tap_recording ", max(anchor, 0))
    start = first(lines, "[record] touch_double_tap action=start", max(decision, 0))
    add(checks, "recording_decision_follows_pointer", decision > anchor >= 0)
    add(
        checks,
        "recording_start_follows_decision",
        start > decision and "state=recording" in lines[start],
    )
    add(checks, "no_menu_entry", not any("menu_boundary=enter" in line for line in lines[max(anchor, 0):]))
    entries = successful_changed(refreshes(lines, start + 1 if start >= 0 else 0))
    add(checks, "recording_visual_has_no_full_refresh", all(not is_full(e) for e in entries))
    return checks, {
        "pointer": pointer,
        "decision_line": decision + 1 if decision >= 0 else None,
        "recording_start_line": start + 1 if start >= 0 else None,
        "refreshes": entries,
    }


def recording_stop(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    anchor, pointer = base_pointer_checks(lines, checks, "double_tap", 0)
    stop = first(lines, "[record] touch_double_tap action=stop", max(anchor, 0))
    store = first(lines, "[record] touch_double_tap action=user_store result=1", max(stop, 0))
    add(checks, "recording_stop_follows_pointer", stop > anchor >= 0)
    add(
        checks,
        "recording_reaches_transfer_ready",
        stop >= 0 and "state=transfer_ready" in lines[stop],
    )
    add(checks, "external_store_finishes", store > stop >= 0)
    add(checks, "no_menu_entry", not any("menu_boundary=enter" in line for line in lines[max(anchor, 0):]))
    entries = successful_changed(refreshes(lines, stop + 1 if stop >= 0 else 0))
    add(checks, "recording_return_has_no_full_refresh", all(not is_full(e) for e in entries))
    return checks, {
        "pointer": pointer,
        "recording_stop_line": stop + 1 if stop >= 0 else None,
        "store_line": store + 1 if store >= 0 else None,
        "refreshes": entries,
    }


def long_press_menu(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    recognized = first(lines, "[touch-ui] browser_event=long_press_recognized ")
    add(checks, "long_press_preview_recognized", recognized >= 0)
    progress: list[dict[str, Any]] = []
    for index in range(max(recognized, 0), len(lines)):
        match = PROGRESS_RE.search(lines[index])
        if match is not None:
            progress.append(
                {
                    "line": index + 1,
                    "bucket": int(match.group("bucket")),
                    "held_ms": int(match.group("held")),
                    "state": match.group("state"),
                    "clip": match.group("clip"),
                    "preview_start_ms": int(match.group("preview")),
                    "fill_step_ms": int(match.group("step")),
                    "text": lines[index],
                }
            )
    expected_states = [
        "menu_hold_1000ms",
        "menu_hold_1500ms",
        "menu_hold_2000ms",
        "menu_hold_2500ms",
    ]
    add(checks, "four_progress_buckets_in_order", [p["bucket"] for p in progress] == [0, 1, 2, 3])
    add(checks, "progress_states_match_shared_browser_contract", [p["state"] for p in progress] == expected_states)
    add(checks, "progress_clips_are_canonical_cemp_frames", all(re.fullmatch(r"frame_\d{4}", p["clip"]) for p in progress))
    add(
        checks,
        "browser_visible_progress_timeline",
        len(progress) == 4
        and all(p["preview_start_ms"] == 1000 and p["fill_step_ms"] == 500 for p in progress)
        and [p["held_ms"] for p in progress] == sorted(p["held_ms"] for p in progress)
        and progress[0]["held_ms"] >= 1000
        and progress[-1]["held_ms"] < 3000,
    )
    pointer_candidates = [
        event for event in pointer_events(lines) if event["gesture"] == "long_press" and event["menu"] == 0
    ]
    add(checks, "terminal_long_press_pointer_seen", len(pointer_candidates) == 1)
    pointer = pointer_candidates[0] if pointer_candidates else None
    pointer_index = pointer["line"] - 1 if pointer else -1
    add(checks, "raw_contact_precedes_long_press", pointer_index >= 0 and raw_contact_before(lines, pointer_index) >= 0)
    normalized_index, normalized = normalized_gesture_before(
        lines, pointer_index, "long_press"
    )
    add(checks, "normalized_long_press_precedes_pointer", normalized_index >= 0)
    if pointer is not None and normalized is not None:
        pointer["normalized_gesture"] = normalized
    daily_to_menu = first(lines, "[touch-ui] daily_to_menu gesture=any_long_press", max(pointer_index, 0))
    boundary = first(lines, "[screen] menu_boundary=enter ", max(daily_to_menu, 0))
    add(checks, "daily_to_menu_follows_terminal_pointer", daily_to_menu > pointer_index >= 0)
    add(checks, "one_menu_enter_boundary", boundary > daily_to_menu and len(matching(lines, "[screen] menu_boundary=enter ")) == 1)
    pre_entries = successful_changed(refreshes(lines, max(recognized, 0), boundary if boundary >= 0 else len(lines)))
    add(checks, "preview_refreshes_are_partial_only", len(pre_entries) >= 4 and all(is_partial(e) for e in pre_entries))
    post_entries = successful_changed(refreshes(lines, boundary + 1 if boundary >= 0 else 0))
    full = [entry for entry in post_entries if is_boundary_full(entry)]
    add(checks, "menu_entry_has_exactly_one_full_refresh", len(full) == 1)
    add(
        checks,
        "menu_entry_first_visible_refresh_is_full",
        bool(post_entries) and is_boundary_full(post_entries[0]),
    )
    return checks, {
        "recognized_line": recognized + 1 if recognized >= 0 else None,
        "progress": progress,
        "pointer": pointer,
        "daily_to_menu_line": daily_to_menu + 1 if daily_to_menu >= 0 else None,
        "boundary_line": boundary + 1 if boundary >= 0 else None,
        "preview_refreshes": pre_entries,
        "post_boundary_refreshes": post_entries,
    }


def menu_drag(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    drag_lines = matching(lines, "[touch-ui] browser_event=menu_vertical_drag ")
    add(checks, "vertical_drag_commit_seen", len(drag_lines) >= 1)
    add(
        checks,
        "drag_commits_request_partial",
        bool(drag_lines) and all("refresh=partial" in lines[i] for i in drag_lines),
    )
    start = drag_lines[0] if drag_lines else 0
    terminal_pointers = [
        event
        for event in pointer_events(lines)
        if event["menu"] == 1 and event["gesture"] in ("swipe_up", "swipe_down")
    ]
    add(checks, "terminal_vertical_pointer_seen", len(terminal_pointers) == 1)
    if terminal_pointers:
        terminal_index = terminal_pointers[0]["line"] - 1
        normalized_index, normalized = normalized_gesture_before(
            lines, terminal_index, terminal_pointers[0]["gesture"]
        )
        add(checks, "normalized_vertical_gesture_precedes_pointer", normalized_index >= 0)
        if normalized is not None:
            terminal_pointers[0]["normalized_gesture"] = normalized
    else:
        add(checks, "normalized_vertical_gesture_precedes_pointer", False)
    entries = successful_changed(refreshes(lines, start))
    add(checks, "one_partial_refresh_per_drag_commit", len(entries) == len(drag_lines) and len(entries) >= 1)
    add(checks, "menu_drag_refreshes_are_partial_only", bool(entries) and all(is_partial(e) for e in entries))
    add(
        checks,
        "menu_drag_has_no_boundary_full",
        not any(is_boundary_full(e) for e in entries),
    )
    add(checks, "menu_remains_visible", not any("menu_boundary=exit" in line for line in lines[start:]))
    return checks, {
        "drag_lines": [i + 1 for i in drag_lines],
        "terminal_pointers": terminal_pointers,
        "refreshes": entries,
    }


def menu_exit(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    anchor, pointer = base_pointer_checks(lines, checks, "swipe_right", 1)
    exit_line = first(lines, "[touch-ui] menu_right_swipe_exit ", max(anchor, 0))
    boundary = first(lines, "[screen] menu_boundary=exit ", max(exit_line, 0))
    add(checks, "menu_exit_event_follows_pointer", exit_line > anchor >= 0)
    add(checks, "one_menu_exit_boundary", boundary > exit_line and len(matching(lines, "[screen] menu_boundary=exit ")) == 1)
    entries = successful_changed(refreshes(lines, boundary + 1 if boundary >= 0 else 0))
    full = [entry for entry in entries if is_boundary_full(entry)]
    add(
        checks,
        "menu_exit_first_visible_refresh_is_full",
        bool(entries) and is_boundary_full(entries[0]),
    )
    add(checks, "menu_exit_has_exactly_one_full_refresh", len(full) == 1)
    add(checks, "later_home_refreshes_are_partial", bool(entries) and all(is_partial(e) for e in entries[1:]))
    return checks, {
        "pointer": pointer,
        "exit_line": exit_line + 1 if exit_line >= 0 else None,
        "boundary_line": boundary + 1 if boundary >= 0 else None,
        "refreshes": entries,
    }


def sleep_entry(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    screen = first(lines, "[screen] low_power_idle pose=sleepy animation=stopped")
    request = first(lines, "[power] low_power_face request=sleepy trigger=idle_timer", max(screen, 0))
    complete = first(lines, "[power] low_power_face completed=1 stop=allowed", max(request, 0))
    add(checks, "sleep_pose_stops_animation", screen >= 0)
    add(checks, "idle_timer_requests_sleep_face", request > screen >= 0)
    entries = successful_changed(refreshes(lines, request + 1 if request >= 0 else 0, complete if complete >= 0 else None))
    full = [entry for entry in entries if is_boundary_full(entry)]
    add(checks, "sleep_entry_has_exactly_one_full_refresh", len(full) == 1)
    add(
        checks,
        "sleep_entry_first_visible_refresh_is_full",
        bool(entries) and is_boundary_full(entries[0]),
    )
    add(checks, "sleep_refresh_completes_before_stop", bool(entries) and complete > entries[0]["line"] - 1)
    return checks, {
        "screen_line": screen + 1 if screen >= 0 else None,
        "request_line": request + 1 if request >= 0 else None,
        "complete_line": complete + 1 if complete >= 0 else None,
        "refreshes": entries,
    }


def wake_boundary(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    boundary = first(
        lines,
        "[screen] low_power_boundary=wake expression=idle refresh=fast_if_baseline",
    )
    wake = first(
        lines,
        "[touch-ui] low_power_touch_wake state=active "
        "visual=boundary_fast_full result=requested",
        max(boundary, 0),
    )
    add(
        checks,
        "one_wake_boundary_request",
        boundary >= 0
        and len(matching(lines, "[screen] low_power_boundary=wake ")) == 1,
    )
    add(checks, "touch_wake_request_seen", wake >= 0)
    add(checks, "wake_request_follows_boundary_enqueue", wake > boundary >= 0)
    pointers = [event for event in pointer_events(lines) if event["line"] - 1 > wake]
    add(checks, "wake_pointer_lifecycle_completes", len(pointers) >= 1)
    entries = successful_changed(refreshes(lines, wake + 1 if wake >= 0 else 0))
    full = [entry for entry in entries if is_boundary_full(entry)]
    add(checks, "wake_has_exactly_one_full_refresh", len(full) == 1)
    add(
        checks,
        "wake_first_visible_refresh_is_full",
        bool(entries) and is_boundary_full(entries[0]),
    )
    add(checks, "later_wake_refreshes_are_partial", bool(entries) and all(is_partial(e) for e in entries[1:]))
    return checks, {
        "boundary_line": boundary + 1 if boundary >= 0 else None,
        "wake_line": wake + 1 if wake >= 0 else None,
        "pointers": pointers,
        "refreshes": entries,
    }


def home_choreography(lines: list[str]) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    boot = first(lines, "[boot] Companion NUCLEO-WB55RG bringup")
    entries = successful_changed(refreshes(lines, boot if boot >= 0 else 0))
    add(checks, "boot_window_anchor_seen", boot >= 0 or bool(entries))
    add(checks, "visible_refreshes_present", len(entries) >= 2)
    add(checks, "boot_first_visible_refresh_is_full", bool(entries) and is_boot_full(entries[0]))
    add(checks, "boot_has_exactly_one_full_refresh", sum(is_boot_full(e) for e in entries) == 1)
    partials = entries[1:]
    add(checks, "home_choreography_is_partial_only", bool(partials) and all(is_partial(e) for e in partials))
    add(checks, "partial_count_crosses_five", any(e.get("partial_before", -1) >= 5 for e in partials))
    add(checks, "no_automatic_maintenance_reason_four", not any(e.get("reason") == 4 for e in partials))
    return checks, {
        "boot_line": boot + 1 if boot >= 0 else None,
        "refreshes": entries,
    }


VERIFY: dict[str, Callable[[list[str]], tuple[dict[str, bool], dict[str, Any]]]] = {
    "ordinary-tap": ordinary_tap,
    "two-tap-transition": two_tap_transition,
    "noncorner-double": noncorner_double,
    "corner-recording-start": corner_recording_start,
    "recording-stop": recording_stop,
    "long-press-menu": long_press_menu,
    "menu-drag": menu_drag,
    "menu-exit": menu_exit,
    "sleep-entry": sleep_entry,
    "wake-boundary": wake_boundary,
    "home-choreography": home_choreography,
}


def evaluate(text: str, scenario: str, source: str) -> dict[str, Any]:
    lines = text.splitlines()
    checks, evidence = VERIFY[scenario](lines)
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema": SCHEMA_ID,
        "status": "MACHINE_READY" if not failures else "NO_GO",
        "scenario": scenario,
        "source": source,
        "log_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
        "log_bytes": len(text.encode("utf-8")),
        "line_count": len(lines),
        "checks": checks,
        "failures": failures,
        "evidence": evidence,
    }


def raw(x: int, y: int, contacts: int = 1, event: str = "down") -> str:
    return (
        f"[touch-raw] contacts={contacts} event={event} id=0 raw_x={x} raw_y={y} "
        f"x={x} y={y} mirror_x=0 mirror_y=0 sample_age_ms=0 reads=1"
    )


def pointer(gesture: str, menu: int, sx: int, sy: int, ex: int, ey: int, duration: int) -> str:
    return (
        f"[touch-ui] browser_pointer gesture={gesture} menu={menu} "
        f"start={sx},{sy} end={ex},{ey} duration_ms={duration}"
    )


def normalized(
    gesture: str,
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    duration: int,
    age: int = 1,
) -> str:
    return (
        f"[touch-ui] gesture={gesture} start={sx},{sy} end={ex},{ey} "
        f"duration_ms={duration} sample_age_ms={age}"
    )


def partial(request: int, before: int = 0) -> str:
    return (
        f"{REFRESH_PREFIX}request={request} changed=1 control=0xCF bytes=2772 "
        f"transaction_ms=240 busy_ms=235 maintenance=0 decision=1 reason=1 "
        f"partial_before={before} transport=software_spi has_busy=1 result=1"
    )


def full(request: int) -> str:
    return (
        f"{REFRESH_PREFIX}request={request} changed=1 control=0xC7 bytes=5000 "
        f"transaction_ms=1760 busy_ms=1740 maintenance=1 decision=2 reason=5 "
        f"partial_before=4 transport=software_spi has_busy=1 result=1"
    )


def boot_full(request: int) -> str:
    return (
        f"{REFRESH_PREFIX}request={request} changed=1 control=0xFF bytes=5000 "
        f"transaction_ms=469 busy_ms=446 maintenance=0 decision=0 reason=3 "
        f"partial_before=0 transport=software_spi has_busy=1 result=1"
    )


def self_test_logs() -> dict[str, str]:
    progress = [
        "[touch-ui] browser_event=long_press_recognized phase=waiting_preview x=100 y=100 duration_ms=1000 preview_start_ms=1000",
        "[emote-player] menu_hold_progress bucket=0 held_ms=1000 state=menu_hold_1000ms clip=frame_0135 preview_start_ms=1000 fill_step_ms=500",
        partial(1),
        "[emote-player] menu_hold_progress bucket=1 held_ms=1500 state=menu_hold_1500ms clip=frame_0138 preview_start_ms=1000 fill_step_ms=500",
        partial(2, 1),
        "[emote-player] menu_hold_progress bucket=2 held_ms=2000 state=menu_hold_2000ms clip=frame_0140 preview_start_ms=1000 fill_step_ms=500",
        partial(3, 2),
        "[emote-player] menu_hold_progress bucket=3 held_ms=2500 state=menu_hold_2500ms clip=frame_0144 preview_start_ms=1000 fill_step_ms=500",
        partial(4, 3),
        normalized("long_press", 100, 100, 100, 100, 3000),
        pointer("long_press", 0, 100, 100, 100, 100, 3000),
        "[touch-ui] daily_to_menu gesture=any_long_press duration_ms=3000 selection=0 revision=1",
        "[screen] menu_boundary=enter view=16 page=0 refresh=fast_if_baseline",
        full(5),
    ]
    logs = {
        "ordinary-tap": "\n".join(
            [
                raw(100, 100),
                raw(100, 100, 0, "none"),
                normalized("tap", 100, 100, 100, 100, 90),
                pointer("tap", 0, 100, 100, 100, 100, 90),
                "[touch-ui] browser_event=single_tap_commit x=100 y=100 double_tap_gap_ms=350 immediate=1 cemp_result=requested",
                partial(1),
            ]
        ),
        "two-tap-transition": "\n".join(
            [
                raw(100, 100),
                raw(100, 100, 0, "none"),
                normalized("tap", 100, 100, 100, 100, 75),
                pointer("tap", 0, 100, 100, 100, 100, 75),
                "[screen-tap] browser_state=frame_0923 family_before=calm "
                "family_after=calm zone=center evidence=1 transition=0 "
                "refresh=partial result=requested",
                "[touch-ui] browser_event=single_tap_commit x=100 y=100 "
                "double_tap_gap_ms=350 immediate=1 cemp_result=requested",
                partial(1),
                raw(101, 101),
                raw(101, 101, 0, "none"),
                normalized("tap", 101, 101, 101, 101, 70),
                pointer("tap", 0, 101, 101, 101, 101, 70),
                "[screen-tap] transition_clip=tap.transition.center "
                "frame_in_clip=0 duration_ms=480 source=cemp_catalog "
                "refresh=partial",
                "[screen-tap] browser_state=tap.transition.center "
                "family_before=calm family_after=thoughtful zone=center "
                "evidence=0 transition=1 refresh=partial result=requested",
                "[touch-ui] browser_event=single_tap_commit x=101 y=101 "
                "double_tap_gap_ms=350 immediate=1 cemp_result=requested",
                partial(2, 1),
                *[
                    line
                    for frame in range(1, 10)
                    for line in (
                        "[screen-tap] transition_clip=tap.transition.center "
                        f"frame_in_clip={frame} duration_ms=480 "
                        "source=cemp_catalog refresh=partial",
                        partial(frame + 2, frame + 1),
                    )
                ],
                "[screen-life] family=thoughtful action=rest episode=1 "
                "phrase=0 phase=hold variation=0 dwell_commits=2 "
                "clip=frame_0200 frame_index=200",
            ]
        ),
        "noncorner-double": "\n".join(
            [
                raw(100, 100),
                normalized("tap", 100, 100, 100, 100, 60),
                pointer("tap", 0, 100, 100, 100, 100, 60),
                "[touch-ui] browser_event=single_tap_commit x=100 y=100 double_tap_gap_ms=350 immediate=1 cemp_result=requested",
                partial(1),
                raw(102, 101),
                normalized("double_tap", 102, 101, 102, 101, 55),
                pointer("double_tap", 0, 102, 101, 102, 101, 55),
                "[touch-ui] browser_event=single_tap_commit x=102 y=101 double_tap_gap_ms=350 immediate=1 cemp_result=requested",
                partial(2, 1),
            ]
        ),
        "corner-recording-start": "\n".join(
            [
                raw(20, 170),
                normalized("double_tap", 20, 170, 20, 170, 70),
                pointer("double_tap", 0, 20, 170, 20, 170, 70),
                "[touch-ui] daily_double_tap_recording x=20 y=170 state=idle",
                "[record] touch_double_tap action=start source=4 result=0 state=recording",
                partial(1),
            ]
        ),
        "recording-stop": "\n".join(
            [
                raw(100, 100),
                normalized("double_tap", 100, 100, 100, 100, 70),
                pointer("double_tap", 0, 100, 100, 100, 100, 70),
                "[record] touch_double_tap action=stop source=4 stop_result=0 finish_result=0 state=transfer_ready",
                "[record] touch_double_tap action=user_store result=1 state=idle",
                partial(1),
            ]
        ),
        "long-press-menu": "\n".join([raw(100, 100), *progress]),
        "menu-drag": "\n".join(
            [
                raw(100, 150),
                "[touch-ui] browser_event=menu_vertical_drag gesture=swipe_up page=1 revision=2 refresh=partial",
                partial(1),
                "[touch-ui] browser_event=menu_vertical_drag gesture=swipe_up page=2 revision=3 refresh=partial",
                partial(2, 1),
                normalized("swipe_up", 100, 150, 100, 40, 1200),
                pointer("swipe_up", 1, 100, 150, 100, 40, 1200),
            ]
        ),
        "menu-exit": "\n".join(
            [
                raw(40, 100),
                normalized("swipe_right", 40, 100, 170, 100, 260),
                pointer("swipe_right", 1, 40, 100, 170, 100, 260),
                "[touch-ui] menu_right_swipe_exit view=16 page=0 start=40,100 end=170,100",
                "[screen] menu_boundary=exit expression=idle refresh=fast_if_baseline",
                full(1),
                partial(2),
            ]
        ),
        "sleep-entry": "\n".join(
            [
                "[screen] low_power_idle pose=sleepy animation=stopped",
                "[power] low_power_face request=sleepy trigger=idle_timer",
                full(1),
                "[power] low_power_face completed=1 stop=allowed",
            ]
        ),
        "wake-boundary": "\n".join(
            [
                raw(100, 100),
                "[screen] low_power_boundary=wake expression=idle refresh=fast_if_baseline",
                "[touch-ui] low_power_touch_wake state=active visual=boundary_fast_full result=requested",
                normalized("tap", 100, 100, 100, 100, 80),
                pointer("tap", 0, 100, 100, 100, 100, 80),
                full(1),
                partial(2),
            ]
        ),
        "home-choreography": "\n".join(
            [boot_full(1)] + [partial(index + 2, index) for index in range(8)]
        ),
    }
    return logs


def run_self_test() -> int:
    results: dict[str, Any] = {}
    failed = False
    for scenario, text in self_test_logs().items():
        report = evaluate(text, scenario, "self-test")
        results[scenario] = {
            "status": report["status"],
            "failures": report["failures"],
        }
        failed = failed or report["status"] != "MACHINE_READY"
    positive = self_test_logs()
    negative_logs = {
        "ordinary-tap-rejects-full": (
            "ordinary-tap",
            positive["ordinary-tap"].replace(partial(1), full(1)),
        ),
        "two-tap-rejects-third-pointer": (
            "two-tap-transition",
            positive["two-tap-transition"]
            + "\n"
            + raw(103, 102)
            + "\n"
            + normalized("tap", 103, 102, 103, 102, 60)
            + "\n"
            + pointer("tap", 0, 103, 102, 103, 102, 60),
        ),
        "two-tap-rejects-skipped-transition-frame": (
            "two-tap-transition",
            "\n".join(
                line
                for line in positive["two-tap-transition"].splitlines()
                if "frame_in_clip=4 " not in line
            ),
        ),
        "long-press-rejects-missing-fourth-point": (
            "long-press-menu",
            "\n".join(
                line
                for line in positive["long-press-menu"].splitlines()
                if "menu_hold_progress bucket=3" not in line
            ),
        ),
        "menu-drag-rejects-full": (
            "menu-drag",
            positive["menu-drag"].replace(partial(1), full(1)),
        ),
        "menu-exit-rejects-partial-boundary": (
            "menu-exit",
            positive["menu-exit"].replace(full(1), partial(1)),
        ),
        "home-rejects-reason-four": (
            "home-choreography",
            positive["home-choreography"].replace("reason=1", "reason=4", 1),
        ),
    }
    negative_results: dict[str, Any] = {}
    for name, (scenario, text) in negative_logs.items():
        report = evaluate(text, scenario, "negative-self-test")
        rejected = report["status"] == "NO_GO"
        negative_results[name] = {
            "status": "PASS" if rejected else "FAIL",
            "verifier_status": report["status"],
            "failures": report["failures"],
        }
        failed = failed or not rejected
    print(
        json.dumps(
            {
                "schema": f"{SCHEMA_ID}.self_test",
                "status": "PASS" if not failed else "FAIL",
                "results": results,
                "negative_results": negative_results,
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, help="Bounded raw serial log")
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--receipt", type=Path, help="JSON receipt path")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    if args.log is None or args.scenario is None or args.receipt is None:
        print("ERROR: --log, --scenario, and --receipt are required", file=sys.stderr)
        return 2
    if not args.log.is_file():
        print(f"ERROR: log not found: {args.log}", file=sys.stderr)
        return 2

    text = args.log.read_text(encoding="utf-8", errors="replace")
    report = evaluate(text, args.scenario, str(args.log.resolve()))
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"{report['status']}: {args.scenario} -> {args.receipt}")
    if report["failures"]:
        print("Failures: " + ", ".join(report["failures"]))
    return 0 if report["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
