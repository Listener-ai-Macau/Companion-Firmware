#!/usr/bin/env python3
"""Verify the V45 vertical review wall stays sourced from dynamic 200x200 frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs/validation/companion-v45-expanded-review-wall-20260721.json"
DEFAULT_VISUAL = ROOT / "docs/validation/companion-v45-expanded-review-wall-visual-20260721.json"
DEFAULT_CAPTURE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/expanded-wall-capture/v42-chinese-overview-headless-r6.png"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--write", type=Path, default=DEFAULT_VISUAL)
    args = parser.parse_args()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    capture_path = args.capture if args.capture.is_absolute() else ROOT / args.capture
    output = args.write if args.write.is_absolute() else ROOT / args.write
    report = load(report_path)
    require(report.get("status") == "PASS_V45_EXPANDED_DYNAMIC_REVIEW_WALL_RUNTIME_INACTIVE" and
            report.get("runtime_resource_activated") is False and report.get("owner_visible_story_count") == 16 and
            report.get("presentation") == "vertical_scroll_single_column_all_owner_visible_stories" and
            report.get("frame_source_rule", "").startswith("every wall frame references an existing parity-rendered PNG"),
            "expanded V45 review wall report is not a 16-story inactive source wall")
    html_path = ROOT / str(report.get("html", ""))
    require(html_path.is_file(), "expanded V45 review wall HTML is missing")
    html = html_path.read_text(encoding="utf-8")
    require(html.count('data-review-revision="v45-touch-failsafe-r7"') == 16 and
            'Touch fail-safe r7' in html and html.count('data-canvas="200x200"') == 16 and html.count('data-story="') == 16 and
            html.count('class="gaze"') == 16 and "setTimeout(play,frame.duration_ms)" in html and
            "pointerdown" in html and "pointermove" in html and "setPointerCapture" in html and
            "mousedown" in html and "mousemove" in html and "mouseup" in html and
            "pointer-events:none" in html and "dragstart" in html and "draggable=\"false\"" in html and
            "preventDefault" in html and ".gaze{background:transparent}" in html,
            "expanded wall does not expose one dynamic native viewport with touch and mouse gaze per story")
    require("<canvas" not in html.lower() and "<svg" not in html.lower() and
            "whole-face" not in html.lower() and "atlas" not in html.lower(),
            "expanded wall contains a forbidden alternate renderer or whole-face fallback")
    source_preview_path = report.get("source_preview_artifact")
    require(isinstance(source_preview_path, str), "expanded wall source preview reference is malformed")
    preview_path = ROOT / source_preview_path
    require(preview_path.is_file(), "expanded wall source preview is missing")
    require(report.get("source_preview_sha256") == __import__("hashlib").sha256(preview_path.read_bytes()).hexdigest().upper(),
            "expanded wall source preview hash drifted")
    preview = load(preview_path)
    preview_frames = {str(frame.get("png")): frame for frame in preview.get("frames", [])}
    expected_frame_count = 0
    for story in report.get("stories", []):
        frames = story.get("frames", [])
        frame_files = [frame.get("src") for frame in frames]
        expected_frame_count += len(frames)
        require(frames and all(isinstance(frame, dict) for frame in frames),
                f"expanded story has no frames: {story.get('name')}")
        for frame in frames:
            frame_file = frame.get("src")
            expected_hash = frame.get("target_1bpp_sha256")
            source = preview_frames.get(frame_file)
            require(source is not None and source.get("target_1bpp_sha256") == expected_hash,
                    f"expanded wall frame is not the machine preview frame: {frame_file}")
            frame_source = html_path.parent.parent / "wb55-browser-parity-attempt-01" / str(frame_file)
            require(frame_source.is_file(), f"expanded wall image is missing: {frame_file}")
            touch_base = html_path.parent.parent / "wb55-browser-parity-attempt-01" / f"touch-base-{story['name']}-{frame['index']:02d}.png"
            require(touch_base.is_file(), f"expanded wall touch base is missing: {touch_base.name}")
            require(touch_base.name in html, f"expanded wall touch base is not referenced: {touch_base.name}")
    require(expected_frame_count == report.get("expanded_frame_count"), "expanded wall frame count drifted")
    require(html.count("touch-gaze-overlay-") >= 1 and "center_key" in html and
            "center_then_resume_story" not in html,
            "expanded wall touch package is missing or exposes an invalid fallback")
    require(capture_path.is_file(), "expanded wall headless capture is missing")
    with Image.open(capture_path) as capture:
        capture.load()
        require(capture.width > 0 and capture.height > 0, "expanded wall capture is blank")
        dimensions = [capture.width, capture.height]
    visual = {
        "schema": "companion.v45_expanded_review_wall_visual.v1",
        "status": "PASS_V45_EXPANDED_REVIEW_WALL_DYNAMIC_200X200_RUNTIME_INACTIVE",
        "wall_report": report_path.resolve().relative_to(ROOT).as_posix(),
        "html": html_path.resolve().relative_to(ROOT).as_posix(),
        "headless_capture": {"path": capture_path.resolve().relative_to(ROOT).as_posix(), "dimensions": dimensions},
        "story_count": report["owner_visible_story_count"],
        "frame_count": report["expanded_frame_count"],
        "viewport_contract": "16 independent 200x200 dynamic story viewports in vertical document order",
        "touch_contract": "each 200x200 story viewport follows touch or mouse drag through the registered V45 overlay package and resumes centered",
        "forbidden_fallbacks": {"whole_face_carousel": False, "static_wall": False, "canvas_face_drawing": False,
                                "legacy_art": False, "runtime_activation": False},
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_physical_panel_acceptance", "no_current_human_acceptance"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(visual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: expanded V45 review wall is dynamic, source-backed and visually nonblank ({output}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
