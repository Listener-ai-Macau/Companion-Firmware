#!/usr/bin/env python3
"""Gate the versioned V45 source-only blink transition sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/generation-request-v1.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/candidate/attempt-01-blink-transition-components.png"
REPORT = ROOT / "docs/validation/companion-v45-blink-transition-source-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_SHA = "1D15DF8B54DEE465D45FFF9C46B02458428B4B31DDC2AB21CB9037E477BB6E33"
EXPECTED_SIZE = (1774, 887)
CELL_NAMES = ("left_half_close", "right_half_close", "left_closed", "right_closed", "left_half_open", "right_half_open")


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


def cell_metrics(sheet: Image.Image, index: int) -> tuple[dict[str, Any], Image.Image]:
    left = round(index * sheet.width / 6)
    right = round((index + 1) * sheet.width / 6)
    cell = sheet.crop((left, 0, right, sheet.height)).convert("L")
    ink = [(x, y) for y in range(cell.height) for x in range(cell.width) if cell.getpixel((x, y)) < 128]
    require(ink, f"V45 source cell {CELL_NAMES[index]} is blank")
    xs = [point[0] for point in ink]
    ys = [point[1] for point in ink]
    bbox = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
    tight = cell.crop(tuple(bbox)).point(lambda value: 0 if value < 128 else 255, mode="1")
    return {"name": CELL_NAMES[index], "cell_index": index, "cell_size": [cell.width, cell.height],
            "ink_bbox": bbox, "ink_pixels": len(ink)}, tight


def mirror_difference(left: Image.Image, right: Image.Image) -> int:
    width = max(left.width, right.width)
    height = max(left.height, right.height)
    left_canvas = Image.new("1", (width, height), 1)
    right_canvas = Image.new("1", (width, height), 1)
    left_canvas.paste(left, ((width - left.width) // 2, (height - left.height) // 2))
    right_canvas.paste(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                      ((width - right.width) // 2, (height - right.height) // 2))
    return sum(1 for pixel in ImageChops.difference(left_canvas, right_canvas).getdata() if pixel == 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request = load(REQUEST)
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            request.get("source_sheet", {}).get("grid") == {"columns": 6, "rows": 1,
                                                               "ordered_cells": list(CELL_NAMES)},
            "V45 source request provenance drifted")
    require(SOURCE.is_file() and sha256(SOURCE) == SOURCE_SHA, "V45 source hash drifted")
    with Image.open(SOURCE) as opened:
        sheet = opened.convert("RGB")
    require(sheet.size == EXPECTED_SIZE, f"V45 source dimensions drifted: {sheet.size}")
    metrics: list[dict[str, Any]] = []
    cells: list[Image.Image] = []
    for index in range(6):
        metric, cell = cell_metrics(sheet, index)
        metrics.append(metric)
        cells.append(cell)
    pair_differences = {
        "half_close": mirror_difference(cells[0], cells[1]),
        "closed": mirror_difference(cells[2], cells[3]),
        "half_open": mirror_difference(cells[4], cells[5]),
    }
    require(all(value <= 2 for value in pair_differences.values()),
            f"V45 blink pair symmetry drifted: {pair_differences}")
    masses = [metric["ink_pixels"] for metric in metrics]
    require(masses[0] != masses[2] and masses[4] != masses[2],
            "V45 transition source has no stage separation from closed")
    require(all(metric["ink_bbox"][1] >= 100 and metric["ink_bbox"][3] <= 800 for metric in metrics),
            "V45 source component left its isolated horizontal source band")
    report = {
        "schema": "companion.v45_blink_transition_source_gate.v1",
        "status": "PASS_V45_BLINK_TRANSITION_SOURCE_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-256", "COMP-REQ-261", "COMP-REQ-267"],
        "locked_v9_source_sha256": LOCKED,
        "generated_source": {"path": rel(SOURCE), "sha256": SOURCE_SHA, "dimensions": list(EXPECTED_SIZE),
                              "request": rel(REQUEST), "cells": metrics},
        "pair_symmetry_pixel_difference": pair_differences,
        "stage_separation": {"half_close_black_pixels": masses[0], "closed_black_pixels": masses[2],
                              "half_open_black_pixels": masses[4]},
        "runtime_resource_activated": False,
        "non_claims": ["no_whole_face_art", "no_lower_driver_change", "no_human_acceptance"],
    }
    output = args.write if args.write.is_absolute() else ROOT / args.write
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V45 blink transition source is versioned, paired, stage-distinct and runtime inactive ({output}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
