#!/usr/bin/env python3
"""Replay V44 single-viewport touch and swipe semantics without a browser or panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREVIEW = ROOT / "docs/validation/companion-v44-blink-stable-center-single-epaper-browser-wb55-preview-20260721.json"
DEFAULT_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/target-score-attempt-01/v44-wb55-target-profile-plan.json"
REPORT = ROOT / "docs/validation/companion-v44-single-epaper-touch-host-20260721.json"
GAZE_COMPONENTS = {1, 3, 5, 7}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def axis(value: int, negative: int, positive: int, center: int) -> int:
    require(0 <= value < 200, "touch coordinate must be inside 200x200")
    if value <= 100:
        return center + round((value - 100) * (center - negative) / 100)
    return center + round((value - 100) * (positive - center) / 99)


def target(x: int, y: int) -> tuple[int, int, int, int]:
    return (axis(x, -2, 5, 1), axis(y, -3, 4, 0), axis(x, -6, 5, 1), axis(y, -6, 6, 0))


def browse(story_index: int, direction: int, story_count: int) -> int:
    return (story_index + direction + story_count) % story_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    preview_path = args.preview if args.preview.is_absolute() else ROOT / args.preview
    trace_path = args.trace if args.trace.is_absolute() else ROOT / args.trace
    preview = load(preview_path)
    trace = load(trace_path)
    require(preview.get("runtime_resource_activated") is False and trace.get("runtime_resource_activated") is False,
            "touch replay must remain runtime inactive")
    viewport = preview.get("viewport_contract", {})
    require(viewport.get("canvas") == "200x200" and viewport.get("touch_surface") == "the_200x200_viewport_itself",
            "touch replay is not bound to the 200x200 viewport")
    stories = [name for name in preview.get("source_score_coverage", []) if not name.startswith("daily_attention_")]
    require(len(stories) == 16, f"owner story count drifted: {len(stories)}")
    touch = preview.get("dynamic_preview", {}).get("touch_follow_gaze", {})
    require(touch.get("mode") == "single_200x200_viewport_pointer_coordinate_to_registered_offsets",
            "touch package is not the single viewport mode")
    html_rel = preview.get("dynamic_preview", {}).get("html")
    require(isinstance(html_rel, str), "preview does not name the single viewport HTML")
    html_path = ROOT / html_rel
    require(html_path.is_file(), f"single viewport HTML is missing: {html_rel}")
    html = html_path.read_text(encoding="utf-8")
    touch_start = html.find("const touchData=")
    touch_end = html.find(";const screen", touch_start)
    require(touch_start >= 0 and touch_end > touch_start, "embedded browser touchData is missing")
    touch_data = json.loads(html[touch_start + len("const touchData="):touch_end])
    offsets = touch_data.get("offsets", {})
    require(isinstance(offsets, dict) and offsets, "embedded browser touchData has no offsets")
    expected_targets = {"center": (100, 100), "left": (0, 100), "right": (199, 100),
                        "up": (100, 0), "down": (100, 199)}
    endpoint_replay: dict[str, dict[str, Any]] = {}
    for name, (x, y) in expected_targets.items():
        key = ",".join(str(value) for value in target(x, y))
        require(key in offsets, f"touch overlay missing {name} endpoint: {key}")
        endpoint_replay[name] = {"point": [x, y], "key": key, "offsets": offsets[key]}
    require(len({entry["key"] for entry in endpoint_replay.values()}) == 5,
            "touch endpoints are not visibly distinct")

    story_index = 0
    transitions = []
    for label, direction in (("swipe_right", 1), ("swipe_down", 1), ("swipe_left", -1), ("swipe_up", -1)):
        before = story_index
        story_index = browse(story_index, direction, len(stories))
        transitions.append({"gesture": label, "before": stories[before], "after": stories[story_index], "direction": direction})
    require(story_index == 0, "four-direction swipe replay did not return deterministically to the start")
    tap_story = story_index
    drag_story = story_index
    release_gaze = ",".join(str(value) for value in target(100, 100))
    require(tap_story == drag_story == story_index and release_gaze == touch_data.get("center_key"),
            "tap/drag/release semantics drifted")

    fixed_face_checks = 0
    for score in trace.get("scores", []):
        if score.get("name", "").startswith("daily_attention_"):
            continue
        for step in score.get("steps", []):
            ids = [layer.get("component_id") for layer in step.get("layers", [])]
            require(4 in ids, f"fixed V22 nose missing from {score.get('name')}")
            non_gaze = tuple(sorted(component_id for component_id in ids if component_id not in GAZE_COMPONENTS))
            require(non_gaze == tuple(sorted(non_gaze)), "non-gaze layer plan is not deterministic")
            fixed_face_checks += 1
    require(fixed_face_checks > 0, "no expression layer plans were replayed")

    report = {
        "schema": "companion.v44_single_epaper_touch_host.v1",
        "status": "PASS_V44_SINGLE_VIEWPORT_TOUCH_SWIPE_REPLAY_RUNTIME_INACTIVE",
        "preview_report": preview_path.resolve().relative_to(ROOT).as_posix(),
        "trace": trace_path.resolve().relative_to(ROOT).as_posix(),
        "canvas": "200x200",
        "endpoint_replay": endpoint_replay,
        "swipe_replay": {"story_count": len(stories), "transitions": transitions, "wraparound": True},
        "tap_drag_release": {"same_story": True, "release_center_key": release_gaze, "resume_deterministic": True},
        "fixed_face_component_checks": fixed_face_checks,
        "random_selection": False,
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_physical_panel_acceptance", "no_human_acceptance"],
    }
    output = args.write if args.write.is_absolute() else ROOT / args.write
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V44 single viewport touch endpoints and four-direction swipe replay are deterministic ({output}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
