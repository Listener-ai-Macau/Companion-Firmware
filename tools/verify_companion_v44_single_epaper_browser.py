#!/usr/bin/env python3
"""Verify the owner-visible V44 browser is one dynamic 200x200 e-paper viewport."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREVIEW = ROOT / "docs/validation/companion-v44-blink-stable-center-single-epaper-browser-wb55-preview-20260721.json"
DEFAULT_CAPTURE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/wb55-browser-parity-attempt-02/headless-capture-r1/v42-chinese-overview-headless-r6.png"
REPORT = ROOT / "docs/validation/companion-v44-single-epaper-browser-visual-20260721.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()

    preview_path = args.preview if args.preview.is_absolute() else ROOT / args.preview
    capture_path = args.capture if args.capture.is_absolute() else ROOT / args.capture
    preview = load(preview_path)
    require(preview.get("schema") == "companion.v44_blink_stable_center_single_epaper_browser_wb55_preview.v1",
            "preview is not the V44 single-e-paper report")
    require(preview.get("status") == "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE",
            "preview status is not PASS")
    require(preview.get("runtime_resource_activated") is not True,
            "V44 browser preview must remain inactive")
    require(preview.get("canvas") == {"width": 200, "height": 200, "stride_bytes": 25,
                                       "pixel_format": "1bpp_white_is_one_msb"},
            "preview canvas is not native 200x200 1bpp")
    require(preview.get("presentation") == "single_200x200_epaper_viewport_with_in_screen_touch_and_deterministic_swipe",
            "owner preview is not the single viewport presentation")
    viewport = preview.get("viewport_contract")
    require(isinstance(viewport, dict) and viewport.get("canvas") == "200x200" and
            viewport.get("owner_visible_story_count") == 16 and
            viewport.get("touch_surface") == "the_200x200_viewport_itself" and
            viewport.get("idle_gaze") == "registered_center_unless_pointer_pressed" and
            viewport.get("release") == "center_then_resume" and
            viewport.get("runtime_resource_activated") is False,
            "single viewport contract drifted")
    swipe = viewport.get("swipe_navigation", {})
    require(swipe == {"horizontal": True, "vertical": True, "positive_direction": "next_story",
                      "negative_direction": "previous_story", "threshold_px": 24},
            "swipe contract drifted")
    require(preview.get("frame_count") == 93, "V44 frame count drifted")
    html_rel = preview.get("dynamic_preview", {}).get("html")
    require(isinstance(html_rel, str), "preview does not name its HTML")
    html_path = ROOT / html_rel
    require(html_path.is_file(), f"preview HTML is missing: {html_rel}")
    html = html_path.read_text(encoding="utf-8")
    require(html.count('id="epaper-screen"') == 1 and html.count('data-canvas="200x200"') == 1 and
            html.count('data-touch-surface="true"') == 1,
            "HTML does not expose exactly one native viewport")
    require(html.count('id="epaper-frame"') == 1 and html.count('id="epaper-gaze"') == 1,
            "HTML frame/gaze layers drifted")
    for marker in ("pointerdown", "pointermove", "pointerup", "lostpointercapture", "centerAndResume", "browse"):
        require(marker in html, f"HTML interaction marker missing: {marker}")
    require("<canvas" not in html.lower() and "performance-card" not in html and "表情与状态总览" not in html,
            "owner preview contains a forbidden canvas/wall/atlas fallback")
    require("const stories" in html and "swipe" in html,
            "single-screen story navigation is not embedded in HTML")

    touch = preview.get("dynamic_preview", {}).get("touch_follow_gaze", {})
    require(touch.get("surface") == "the_200x200_viewport_itself" and
            touch.get("mode") == "single_200x200_viewport_pointer_coordinate_to_registered_offsets" and
            touch.get("release_behavior") == "center_then_resume_story" and
            set(touch.get("gestures", [])) == {"tap", "drag", "release_to_center", "swipe_left", "swipe_right", "swipe_up", "swipe_down"},
            "touch package does not describe the single viewport contract")

    require(capture_path.is_file(), f"headless browser capture is missing: {capture_path}")
    with Image.open(capture_path) as capture:
        capture.load()
        require(capture.width > 0 and capture.height > 0, "headless capture is blank")
        capture_size = [capture.width, capture.height]

    report = {
        "schema": "companion.v44_single_epaper_browser_visual.v1",
        "status": "PASS_V44_SINGLE_200X200_BROWSER_VIEWPORT_RUNTIME_INACTIVE",
        "preview_report": preview_path.resolve().relative_to(ROOT).as_posix(),
        "html": html_path.resolve().relative_to(ROOT).as_posix(),
        "headless_capture": {"path": capture_path.resolve().relative_to(ROOT).as_posix(), "dimensions": capture_size},
        "viewport": {"canvas": "200x200", "presentation": preview["presentation"],
                     "owner_visible_story_count": viewport["owner_visible_story_count"],
                     "horizontal_swipe": "positive_next_negative_previous",
                     "vertical_swipe": "positive_next_negative_previous",
                     "touch_surface": viewport["touch_surface"], "idle": viewport["idle_gaze"],
                     "release": viewport["release"]},
        "forbidden_fallbacks": {"whole_face_carousel": False, "static_wall": False, "canvas_face_drawing": False,
                                "legacy_art": False, "runtime_activation": False},
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_physical_panel_acceptance", "no_human_acceptance"],
    }
    output = args.write if args.write.is_absolute() else ROOT / args.write
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V44 owner preview is one dynamic 200x200 e-paper viewport with in-screen touch and deterministic swipe ({output}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
