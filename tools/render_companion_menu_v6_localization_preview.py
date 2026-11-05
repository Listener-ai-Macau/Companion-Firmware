#!/usr/bin/env python3
"""Render non-importable English and zh-CN menu previews from the real C text source."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-menu-v6-four-root"
SOURCE = ART_DIR / "generated_menu_four_root_v6_candidate.png"
SOURCE_SHA256 = "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"
LOCALIZATION_C = ROOT / "app/companion_pendant/epaper/menu_v5_localization.c"
EN_PREVIEW = ART_DIR / "generated_menu_four_root_v6_en_200x200_localization_preview.png"
ZH_PREVIEW = ART_DIR / "generated_menu_four_root_v6_zh_cn_200x200_localization_preview.png"
REPORT = ROOT / "docs/validation/companion-menu-v6-localization-preview-20260717.json"
FONT = pathlib.Path(r"C:\Windows\Fonts\msyh.ttc")
TARGET_SIZE = (200, 200)
THRESHOLD = 180
ROW_CENTERS = (75, 110, 145, 180)
LABEL_CLEAR_LEFT = 51
LABEL_LEFT = 52
LABEL_RIGHT = 161
LABEL_HALF_HEIGHT = 8
ROOT_EXPECTED = {
    "en": ["Voice", "Device", "Connection", "Preferences"],
    "zh_cn": ["\u8bed\u97f3", "\u8bbe\u5907", "\u8fde\u63a5", "\u504f\u597d\u8bbe\u7f6e"],
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_root_texts() -> dict[str, list[str]]:
    content = LOCALIZATION_C.read_text(encoding="utf-8")
    result: dict[str, list[str]] = {}
    for language, array_name in (("en", "k_english"), ("zh_cn", "k_chinese")):
        match = re.search(
            rf"static const char \*const {array_name}\[[^]]+\] = \{{(?P<body>.*?)\}};",
            content,
            re.DOTALL,
        )
        if match is None:
            raise ValueError(f"unable to locate {array_name} in menu_v5_localization.c")
        values = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', match.group("body"))
        result[language] = values[:4]
    return result


def fitted_font(text: str, draw: ImageDraw.ImageDraw) -> tuple[ImageFont.FreeTypeFont, tuple[int, int, int, int]]:
    for size in range(13, 7, -1):
        font = ImageFont.truetype(str(FONT), size=size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= LABEL_RIGHT - LABEL_LEFT - 4:
            return font, bbox
    raise ValueError(f"localized root label cannot fit preview label slot: {text}")


def render_language(source: Image.Image, language: str, labels: list[str], output: pathlib.Path) -> dict[str, object]:
    canvas = source.resize(TARGET_SIZE, Image.Resampling.LANCZOS).convert("L")
    draw = ImageDraw.Draw(canvas)
    placements: list[dict[str, object]] = []
    for center, label in zip(ROW_CENTERS, labels, strict=True):
        draw.rectangle(
            (LABEL_CLEAR_LEFT, center - LABEL_HALF_HEIGHT, LABEL_RIGHT, center + LABEL_HALF_HEIGHT),
            fill=255,
        )
        font, bbox = fitted_font(label, draw)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = LABEL_LEFT + 2
        y = center - height // 2 - bbox[1]
        draw.text((x, y), label, fill=0, font=font)
        placements.append({
            "label": label,
            "font_px": font.size,
            "bbox": [x, y + bbox[1], x + width, y + bbox[3]],
        })
    preview = canvas.point(lambda value: 0 if value < THRESHOLD else 255, "1")
    output.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output)
    black_pixels = sum(value == 0 for value in preview.getdata())
    return {
        "language": language,
        "path": output.relative_to(ROOT).as_posix(),
        "labels": labels,
        "placements": placements,
        "black_pixels": black_pixels,
    }


def render() -> dict[str, object]:
    errors: list[str] = []
    if not FONT.is_file():
        errors.append(f"preview font unavailable: {FONT}")
        return {"status": "FAIL", "errors": errors}
    source_hash = sha256(SOURCE)
    if source_hash != SOURCE_SHA256:
        errors.append("menu source hash drifted from the recorded generated output")
    source = Image.open(SOURCE).convert("L")
    if source.size != (1254, 1254):
        errors.append("menu source dimensions are not the recorded square 1254x1254 output")
    labels = parse_root_texts()
    if labels != ROOT_EXPECTED:
        errors.append("menu_v5_localization root labels drifted from the four-root contract")
    previews = [
        render_language(source, "en", labels["en"], EN_PREVIEW),
        render_language(source, "zh_cn", labels["zh_cn"], ZH_PREVIEW),
    ]
    for preview in previews:
        if not 1400 <= int(preview["black_pixels"]) <= 5000:
            errors.append(f"{preview['language']} preview ink coverage is outside the review guard band")
        for placement in preview["placements"]:
            bbox = placement["bbox"]
            if bbox[0] < LABEL_LEFT or bbox[2] > LABEL_RIGHT or bbox[1] < 0 or bbox[3] > TARGET_SIZE[1]:
                errors.append(f"{preview['language']} label placement is outside its row slot")

    return {
        "schema": "companion.menu_v6_localization_preview.v1",
        "status": "PASS_MACHINE_LOCALIZATION_PREVIEW_PENDING_OWNER" if not errors else "FAIL",
        "source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": source_hash,
            "dimensions_px": list(source.size),
        },
        "localization_source": {
            "path": LOCALIZATION_C.relative_to(ROOT).as_posix(),
            "sha256": sha256(LOCALIZATION_C),
        },
        "preview_font": {
            "path": str(FONT),
            "sha256": sha256(FONT),
            "scope": "host-only review renderer; never a target font asset",
        },
        "previews": previews,
        "runtime_boundary": {
            "pbm_imported": False,
            "cemp_packed": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "owner_visual_pass": False,
            "target_font_asset_changed": False,
        },
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write both deterministic localized previews and JSON evidence.")
    args = parser.parse_args(argv)
    result = render()
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: v6 menu preview uses the real English and zh-CN four-root localization strings without runtime import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
