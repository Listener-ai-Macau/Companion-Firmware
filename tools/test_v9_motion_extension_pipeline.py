#!/usr/bin/env python3
"""Exercise the candidate-only v9 motion-art import and rejection rules."""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import tempfile

from PIL import Image, ImageDraw

from render_companion_v9_motion_extension import LOCKED_V9_SHA256, load_layout, render
from verify_companion_v9_motion_extension import verify


ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def draw_face(image: Image.Image, offset_x: int, sustain: bool) -> None:
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((62 + offset_x, 55, 80 + offset_x, 59), radius=2, fill="black")
    draw.rounded_rectangle((120 + offset_x, 55, 138 + offset_x, 59), radius=2, fill="black")
    draw.ellipse((58 + offset_x, 70, 82 + offset_x, 108), fill="black")
    draw.ellipse((118 + offset_x, 70, 142 + offset_x, 108), fill="black")
    draw.ellipse((64 + offset_x, 78, 71 + offset_x, 88), fill="white")
    draw.ellipse((124 + offset_x, 78, 131 + offset_x, 88), fill="white")
    draw.ellipse((102 + offset_x, 112, 108 + offset_x, 118), fill="black")
    draw.arc((94 + offset_x, 116, 106 + offset_x, 128), 0, 180, fill="black", width=2)
    draw.arc((104 + offset_x, 116, 116 + offset_x, 128), 0, 180, fill="black", width=2)
    draw.ellipse((51 + offset_x, 105, 57 + offset_x, 111), fill="black")
    draw.ellipse((143 + offset_x, 105, 149 + offset_x, 111), fill="black")
    draw.polygon([(100 + offset_x, 36), (103 + offset_x, 43),
                  (110 + offset_x, 46), (103 + offset_x, 49),
                  (100 + offset_x, 56), (97 + offset_x, 49),
                  (90 + offset_x, 46), (97 + offset_x, 43)], fill="black")
    if sustain:
        draw.ellipse((64 + offset_x, 78, 71 + offset_x, 88), fill="black")
        draw.ellipse((68 + offset_x, 82, 75 + offset_x, 92), fill="white")
        draw.ellipse((124 + offset_x, 78, 131 + offset_x, 88), fill="black")
        draw.ellipse((128 + offset_x, 82, 135 + offset_x, 92), fill="white")
        draw.rectangle((62 + offset_x, 55, 80 + offset_x, 59), fill="white")
        draw.rectangle((120 + offset_x, 55, 138 + offset_x, 59), fill="white")
        draw.rounded_rectangle((62 + offset_x, 51, 80 + offset_x, 55), radius=2, fill="black")
        draw.rounded_rectangle((120 + offset_x, 51, 138 + offset_x, 55), radius=2, fill="black")
        draw.rectangle((90 + offset_x, 46, 110 + offset_x, 56), fill="white")
        draw.ellipse((100 + offset_x, 36, 110 + offset_x, 46), fill="black")


def base_layout(source: pathlib.Path) -> dict[str, object]:
    return {
        "schema": "companion.v9_motion_extension_layout.v1",
        "status": "CANDIDATE_PENDING_OWNER_REVIEW",
        "runtime_resource_activated": False,
        "source": source.resolve().relative_to(ROOT).as_posix(),
        "source_sha256": sha256(source),
        "parent_source_sha256": LOCKED_V9_SHA256,
        "prompt_revision": "test-v9-motion-extension-r1",
        "revision": 91,
        "profile": {
            "width": 200,
            "height": 200,
            "pixel_format": "mono_1bpp_white_is_one_msb",
            "safe_inset_px": 4,
        },
        "phases": [
            {"name": "entry", "source_crop_box": [0, 0, 200, 200]},
            {"name": "sustain", "source_crop_box": [200, 0, 200, 200]},
            {"name": "settle", "source_crop_box": [400, 0, 200, 200]},
        ],
        "motion_features": [
            {
                "name": "eye_highlights",
                "role": "eye_highlight",
                "regions": [[45, 70, 110, 70]],
                "min_changed_pixels": 8,
            },
            {
                "name": "brows_and_charm",
                "role": "secondary",
                "regions": [[45, 40, 110, 45], [85, 70, 30, 25]],
                "min_changed_pixels": 8,
            },
        ],
    }


def write_layout(path: pathlib.Path, layout: dict[str, object]) -> None:
    path.write_text(json.dumps(layout, indent=2) + "\n", encoding="ascii")


def main() -> int:
    cache_root = ROOT / ".cache" / "host-tests"
    cache_root.mkdir(parents=True, exist_ok=True)
    directory = pathlib.Path(tempfile.mkdtemp(prefix="v9-motion-extension-", dir=cache_root))
    try:
        source = directory / "candidate.png"
        image = Image.new("L", (600, 200), 255)
        draw_face(image, 0, False)
        draw_face(image, 200, True)
        draw_face(image, 400, False)
        image.save(source)
        layout_path = directory / "layout.json"
        write_layout(layout_path, base_layout(source))
        report = render(load_layout(layout_path), directory / "rendered")
        report_path = directory / "rendered" / "report.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
        verification = verify(report_path)
        if verification["status"] != "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED":
            raise AssertionError(f"candidate verification failed: {verification['errors']}")
        if report["whole_frame_translation_only"] or not all(
            item["pass"] for item in report["feature_diffs"]
        ):
            raise AssertionError("candidate did not retain multi-feature motion evidence")

        translation_source = directory / "translation.png"
        shifted = Image.new("L", (600, 200), 255)
        entry = image.crop((0, 0, 200, 200))
        shifted.paste(entry, (0, 0))
        shifted.paste(entry, (202, 0))
        shifted.paste(entry, (400, 0))
        shifted.save(translation_source)
        translation_layout = base_layout(translation_source)
        translation_path = directory / "translation-layout.json"
        write_layout(translation_path, translation_layout)
        try:
            render(load_layout(translation_path), directory / "translation-rendered")
        except ValueError as exc:
            if "whole-frame translation" not in str(exc):
                raise
        else:
            raise AssertionError("whole-frame translation candidate was incorrectly accepted")
    finally:
        shutil.rmtree(directory, ignore_errors=True)
    print("PASS: v9 motion extension pipeline accepts coordinated feature changes and rejects global translation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
