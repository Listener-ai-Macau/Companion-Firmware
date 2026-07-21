#!/usr/bin/env python3
"""Gate the V45 complete-eye-group blink source before Rig export."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/generation-request-v4.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/candidate/attempt-03-complete-eye-groups.png"
REPORT = ROOT / "docs/validation/companion-v45-complete-eye-source-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_SHA = "BE15833DDA125C969B99D9D6F96638A493375E426ABC17CFCEDFD7CBD2DA1586"
EXPECTED_SIZE = (1774, 887)
CELL_NAMES = ("left_open", "right_open", "left_closing", "right_closing", "left_closed", "right_closed", "left_opening", "right_opening")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{rel(path)} must contain an object")
    return value


def crop_cell(sheet: Image.Image, index: int) -> tuple[dict[str, Any], Image.Image]:
    left = round(index * sheet.width / 8)
    right = round((index + 1) * sheet.width / 8)
    cell = sheet.crop((left, 0, right, sheet.height)).convert("L")
    ink = [(x, y) for y in range(cell.height) for x in range(cell.width) if cell.getpixel((x, y)) < 128]
    require(ink, f"V45 complete-eye cell is blank: {CELL_NAMES[index]}")
    xs = [point[0] for point in ink]
    ys = [point[1] for point in ink]
    bbox = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
    tight = cell.crop(tuple(bbox)).point(lambda value: 0 if value < 128 else 255, mode="1")
    return {"name": CELL_NAMES[index], "cell_index": index, "cell_size": [cell.width, cell.height],
            "ink_bbox": bbox, "ink_pixels": len(ink), "tight_size": list(tight.size)}, tight


def mirror_difference(left: Image.Image, right: Image.Image) -> int:
    width = max(left.width, right.width)
    height = max(left.height, right.height)
    left_canvas = Image.new("1", (width, height), 1)
    right_canvas = Image.new("1", (width, height), 1)
    left_canvas.paste(left, ((width - left.width) // 2, (height - left.height) // 2))
    right_canvas.paste(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                      ((width - right.width) // 2, (height - right.height) // 2))
    return sum(1 for pixel in ImageChops.difference(left_canvas, right_canvas).getdata() if pixel != 0)


def interior_white_pixels(mask: Image.Image) -> int:
    pixels = mask.convert("1")
    width, height = pixels.size
    white = {(x, y) for y in range(height) for x in range(width) if pixels.getpixel((x, y)) != 0}
    outside: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for point in white:
        if point[0] in {0, width - 1} or point[1] in {0, height - 1}:
            outside.add(point)
            queue.append(point)
    while queue:
        x, y = queue.popleft()
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbor in white and neighbor not in outside:
                outside.add(neighbor)
                queue.append(neighbor)
    return len(white - outside)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request = load(REQUEST)
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            request.get("source_sheet", {}).get("grid", {}).get("columns") == 8,
            "V45 complete-eye request provenance drifted")
    require(SOURCE.is_file() and sha256(SOURCE) == SOURCE_SHA, "V45 complete-eye source hash drifted")
    with Image.open(SOURCE) as opened:
        sheet = opened.convert("RGB")
    require(sheet.size == EXPECTED_SIZE, f"V45 complete-eye source dimensions drifted: {sheet.size}")
    metrics: list[dict[str, Any]] = []
    cells: list[Image.Image] = []
    for index in range(8):
        metric, cell = crop_cell(sheet, index)
        metric["interior_white_pixels"] = interior_white_pixels(cell)
        metrics.append(metric)
        cells.append(cell)
    pairs = {"open": mirror_difference(cells[0], cells[1]), "closing": mirror_difference(cells[2], cells[3]),
             "closed": mirror_difference(cells[4], cells[5]), "opening": mirror_difference(cells[6], cells[7])}
    require(all(value <= 2 for value in pairs.values()), f"V45 complete-eye pair symmetry drifted: {pairs}")
    heights = [metrics[index]["tight_size"][1] for index in (0, 2, 4, 6)]
    require(heights[0] > heights[3] > heights[1] > heights[2],
            f"V45 complete-eye stage heights are not open>opening>closing>closed: {heights}")
    require(all(metrics[index]["interior_white_pixels"] > 0 for index in (0, 1, 2, 3, 6, 7)),
            "V45 open/closing/opening eye groups lost their internal V9 reflection or sparkle holes")
    report = {
        "schema": "companion.v45_complete_eye_source_gate.v1",
        "status": "PASS_V45_COMPLETE_EYE_CLOSURE_SOURCE_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-267", "COMP-REQ-269"],
        "locked_v9_source_sha256": LOCKED,
        "generated_source": {"path": rel(SOURCE), "sha256": SOURCE_SHA, "dimensions": list(EXPECTED_SIZE),
                              "request": rel(REQUEST), "cells": metrics},
        "pair_symmetry_pixel_difference": pairs,
        "stage_height_order": {"open": heights[0], "closing": heights[1], "closed": heights[2], "opening": heights[3]},
        "complete_eye_contract": "eye body + white primary reflection + tiny white sparkle for open/closing/opening; closed stroke for closed",
        "runtime_resource_activated": False,
        "non_claims": ["no_whole_face_art", "no_lower_driver_change", "no_human_acceptance"],
    }
    output = args.write if args.write.is_absolute() else ROOT / args.write
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V45 complete-eye closure source is paired, stage-ordered and source-only ({output}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
