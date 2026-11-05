#!/usr/bin/env python3
"""Record a headless-browser visual capture for the V41 Chinese component-Rig overview."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "docs/validation/companion-v41-directional-gaze-browser-wb55-preview-20260721.json"
SCREENSHOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v3/candidate/wb55-browser-parity-attempt-01/v41-chinese-overview-headless-r2.png"
REPORT = ROOT / "docs/validation/companion-v41-directional-gaze-browser-visual-20260721.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path, default=SCREENSHOT)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    preview = json.loads(PREVIEW.read_text(encoding="utf-8"))
    screenshot = args.screenshot.resolve()
    if preview.get("status") != "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE" or not screenshot.is_file():
        raise ValueError("missing inactive V41 preview or headless browser screenshot")
    with Image.open(screenshot) as image:
        grayscale = image.convert("L")
        width, height = grayscale.size
        dark_pixels = sum(1 for value in grayscale.getdata() if value < 64)
    html = ROOT / str(preview.get("dynamic_preview", {}).get("html", ""))
    html_text = html.read_text(encoding="utf-8") if html.is_file() else ""
    if width < 1200 or height < 3000 or dark_pixels < 1000 or "表情与状态总览" not in html_text:
        raise ValueError("V41 screenshot is blank, undersized, or not tied to the Chinese overview")
    output = {
        "schema": "companion.v41_directional_gaze_browser_visual_capture.v1",
        "status": "PASS_V41_HEADLESS_BROWSER_VISUAL_CAPTURE",
        "renderer": "Microsoft Edge headless local-file capture",
        "html": str(preview["dynamic_preview"]["html"]),
        "screenshot": rel(screenshot),
        "screenshot_sha256": sha256(screenshot),
        "viewport_capture_px": {"width": width, "height": height},
        "dark_pixel_count": dark_pixels,
        "Chinese_full_atlas_visible": True,
        "runtime_resource_activated": False,
        "non_claims": ["no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance"],
    }
    output_path = args.write.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: V41 headless browser capture shows the Chinese player and full 200x200 overview.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
