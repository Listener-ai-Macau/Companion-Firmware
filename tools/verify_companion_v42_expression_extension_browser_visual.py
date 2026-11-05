#!/usr/bin/env python3
"""Record a headless-browser visual capture for the V42 Chinese owner overview."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "docs/validation/companion-v42-expression-extension-browser-wb55-preview-20260721.json"
SCREENSHOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/candidate/wb55-browser-parity-attempt-01/v42-chinese-overview-headless.png"
REPORT = ROOT / "docs/validation/companion-v42-expression-extension-browser-visual-20260721.json"
HIDDEN_GAZE = {"daily_attention_center", "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, default=PREVIEW)
    parser.add_argument("--screenshot", type=Path, default=SCREENSHOT)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    preview_path = args.preview.resolve()
    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    screenshot = args.screenshot.resolve()
    if preview.get("status") != "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE" or not screenshot.is_file():
        raise ValueError("missing inactive V42 preview or headless browser screenshot")
    overview = preview.get("chinese_overview", {})
    visible = set(overview.get("owner_visible_scores", [])) if isinstance(overview, dict) else set()
    metadata = overview.get("metadata", {}).get("stories", {}) if isinstance(overview, dict) else {}
    if len(visible) != 16 or visible & HIDDEN_GAZE or not HIDDEN_GAZE.issubset(metadata):
        raise ValueError("V42 browser overview does not hide exactly the five internal gaze scores")
    html = ROOT / str(preview.get("dynamic_preview", {}).get("html", ""))
    html_text = html.read_text(encoding="utf-8") if html.is_file() else ""
    with Image.open(screenshot) as image:
        grayscale = image.convert("L")
        width, height = grayscale.size
        dark_pixels = sum(1 for value in grayscale.getdata() if value < 64)
    in_card_touch_visible = 'data-touch-surface="true"' in html_text and html_text.count('data-touch-surface="true"') == 16 and 'id="touch-pad"' not in html_text
    dynamic_wall_visible = "全部动态编舞" in html_text and 'id="performance-wall"' in html_text and html_text.count('class="performance-card"') == 16 and "表情与状态总览" not in html_text
    if width < 1200 or height < 1600 or dark_pixels < 1000 or "录音输入中" not in html_text or "无线机座充电" not in html_text or not in_card_touch_visible or not dynamic_wall_visible or any(name in html_text for name in HIDDEN_GAZE):
        raise ValueError("V42 screenshot is blank, undersized, or exposes hidden gaze cards")
    output = {
        "schema": "companion.v42_expression_extension_browser_visual_capture.v1",
        "status": "PASS_V42_HEADLESS_BROWSER_VISUAL_CAPTURE",
        "renderer": "Microsoft Edge headless local-file capture",
        "preview": rel(preview_path), "html": str(preview["dynamic_preview"]["html"]),
        "screenshot": rel(screenshot), "screenshot_sha256": sha256(screenshot),
        "viewport_capture_px": {"width": width, "height": height}, "dark_pixel_count": dark_pixels,
        "Chinese_owner_atlas_visible": False, "owner_visible_story_count": len(visible), "hidden_internal_gaze": sorted(HIDDEN_GAZE),
        "in_card_touch_gaze_visible": in_card_touch_visible,
        "all_performance_wall_visible": dynamic_wall_visible,
        "runtime_resource_activated": False,
        "non_claims": ["no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance"],
    }
    destination = args.write.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: V42 headless browser capture shows the Chinese dynamic wall with in-card touch surfaces and no internal gaze cards.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
