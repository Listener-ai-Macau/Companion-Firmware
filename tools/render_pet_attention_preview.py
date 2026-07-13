#!/usr/bin/env python3
"""Render the nine directional Companion touch responses for visual review."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs" / "validation" / "epaper"
DEFAULT_OUTPUT = ROOT / ".cache" / "validation" / "pet-attention" / "attention-grid.png"
DEFAULT_REPORT = ROOT / "docs" / "validation" / "companion-screen-pet-attention-preview.json"
DIRECTIONS = (
    "up_left", "up", "up_right",
    "left", "center", "right",
    "down_left", "down", "down_right",
)


def source_for(direction: str) -> pathlib.Path:
    if direction == "center":
        return ASSET_DIR / "expression_happy_attention_1_54in.pbm"
    return ASSET_DIR / f"expression_happy_attention_{direction}_1_54in.pbm"


def sha256_hex(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_preview() -> tuple[Image.Image, dict[str, object]]:
    cell_width = 220
    cell_height = 232
    image = Image.new("1", (cell_width * 3, cell_height * 3), 1)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    entries: list[dict[str, str]] = []

    for index, direction in enumerate(DIRECTIONS):
        source = source_for(direction)
        if not source.is_file():
            raise FileNotFoundError(source)
        with Image.open(source) as frame:
            panel = frame.convert("1")
        x = (index % 3) * cell_width + 10
        y = (index // 3) * cell_height + 8
        image.paste(panel, (x, y))
        draw.rectangle((x, y, x + 199, y + 199), outline=0, width=1)
        draw.text((x, y + 207), direction.upper(), font=font, fill=0)
        entries.append(
            {
                "direction": direction,
                "source": source.relative_to(ROOT).as_posix(),
                "sha256": sha256_hex(source),
            }
        )

    report = {
        "schema_id": "companion.pendant.pet_attention_preview.v1",
        "directions": list(DIRECTIONS),
        "grid": "3x3 directional touch response",
        "response": "notice toward the logical touch cell, then a happy settle frame",
        "storage": "external ui_assets CEMP pack",
        "entries": entries,
    }
    return image, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    image, report = build_preview()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    expected_report = dict(report)
    expected_report["preview_path"] = output.relative_to(ROOT).as_posix()

    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        report_path.write_text(json.dumps(expected_report, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: wrote {output.relative_to(ROOT)} and {report_path.relative_to(ROOT)}")
        return 0

    if not output.is_file() or not report_path.is_file():
        raise FileNotFoundError("run with --write to create the directional attention preview")
    actual_report = json.loads(report_path.read_text(encoding="utf-8"))
    if actual_report != expected_report:
        raise ValueError("directional attention preview report is stale")
    print(f"PASS: directional attention preview verified -> {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
