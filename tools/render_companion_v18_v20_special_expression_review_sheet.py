#!/usr/bin/env python3
"""Render one review-only sheet for the V18-V20 complete special-expression poses."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SPECS = (
    ("V18 MENU", "companion-pet-expression-v9-extension-v18-menu-special-expression-source",
     "attempt-01-generated-menu-special-expression.png", "menu_active-source-component-reassembly-preview.png"),
    ("V19 RECORDING", "companion-pet-expression-v9-extension-v19-recording-special-expression-source",
     "attempt-01-generated-recording-special-expression.png", "recording_active-source-component-reassembly-preview.png"),
    ("V20 UPGRADE", "companion-pet-expression-v9-extension-v20-upgrade-special-expression-source",
     "attempt-01-generated-upgrade-special-expression.png", "upgrade_active-source-component-reassembly-preview.png"),
)
CANVAS = (1520, 2100)
SOURCE_BOX = (80, 100, 730, 690)
RIG_BOX = (790, 100, 1440, 690)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def place_contained(canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    image = image.convert("RGB")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    offset_x = left + (width - image.width) // 2
    offset_y = top + (height - image.height) // 2
    canvas.paste(image, (offset_x, offset_y))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report_path = args.write if args.write.is_absolute() else ROOT / args.write
    if not LOCKED_V9.is_file() or sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        raise SystemExit("FAIL: locked V9 source hash drifted")
    font = ImageFont.load_default()
    sheet = Image.new("RGB", CANVAS, "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((80, 42), "V18-V20 COMPLETE SPECIAL EXPRESSION SOURCE REVIEW", fill="black", font=font)
    draw.text((80, 65), "LEFT: generated complete source pose | RIGHT: V9 identity component reassembly", fill="black", font=font)
    inputs: list[dict[str, str]] = []
    for index, (name, iteration, source_name, preview_name) in enumerate(SPECS):
        row_top = 125 + index * 650
        source_path = ROOT / "docs/art/iterations" / iteration / "candidate" / source_name
        preview_path = ROOT / "docs/art/iterations" / iteration / "candidate/component-export-attempt-01" / preview_name
        if not source_path.is_file() or not preview_path.is_file():
            raise SystemExit(f"FAIL: missing review input for {name}")
        draw.rectangle((50, row_top - 20, 1470, row_top + 590), outline="black", width=2)
        draw.text((80, row_top), name, fill="black", font=font)
        draw.text((80, row_top + 18), "COMPLETE SOURCE POSE", fill="black", font=font)
        draw.text((790, row_top + 18), "LOCKED V9 IDENTITY REASSEMBLY", fill="black", font=font)
        source_box = (SOURCE_BOX[0], row_top + 45, SOURCE_BOX[2], row_top + 575)
        rig_box = (RIG_BOX[0], row_top + 45, RIG_BOX[2], row_top + 575)
        draw.rectangle(source_box, outline="black", width=1)
        draw.rectangle(rig_box, outline="black", width=1)
        place_contained(sheet, Image.open(source_path), source_box)
        place_contained(sheet, Image.open(preview_path), rig_box)
        inputs.append({
            "name": name,
            "source": source_path.relative_to(ROOT).as_posix(),
            "source_sha256": sha256(source_path),
            "reassembly_preview": preview_path.relative_to(ROOT).as_posix(),
            "reassembly_preview_sha256": sha256(preview_path),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    result = {
        "schema": "companion.v18_v20_special_expression_owner_art_review_sheet.v1",
        "status": "PASS_REVIEW_ONLY_CONTACT_SHEET",
        "locked_v9_source": LOCKED_V9.relative_to(ROOT).as_posix(),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "sheet": output.relative_to(ROOT).as_posix(),
        "sheet_sha256": sha256(output),
        "dimensions": list(CANVAS),
        "inputs": inputs,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(f"PASS: wrote V18-V20 review-only special-expression sheet -> {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
