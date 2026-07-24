#!/usr/bin/env python3
"""Verify readable left/right/up/down attention in a V9 eye-identity proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import deque

from PIL import Image

from verify_companion_v9_open_eye_identity import components


ROOT = pathlib.Path(__file__).resolve().parents[1]
MIN_PAIR_PIXEL_DIFFERENCE = 100
LEFT_MAX_PRIMARY_X = 0.47
RIGHT_MIN_PRIMARY_X = 0.53
UP_MAX_PRIMARY_Y = 0.43
DOWN_MIN_PRIMARY_Y = 0.57


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def enclosed_white_components(image: Image.Image, eye: dict[str, float | int]) -> list[dict[str, float | int]]:
    pixels = image.convert("L").load()
    left, top = int(eye["x"]), int(eye["y"])
    width, height = int(eye["width"]), int(eye["height"])
    visited: set[tuple[int, int]] = set()
    result: list[dict[str, float | int]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited or pixels[left + x, top + y] < 200:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited.add((x, y))
            points: list[tuple[int, int]] = []
            touches_edge = False
            while queue:
                point_x, point_y = queue.popleft()
                points.append((point_x, point_y))
                touches_edge = touches_edge or point_x in (0, width - 1) or point_y in (0, height - 1)
                for delta_x, delta_y in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                                         (0, 1), (1, -1), (1, 0), (1, 1)):
                    next_x, next_y = point_x + delta_x, point_y + delta_y
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    if (next_x, next_y) in visited or pixels[left + next_x, top + next_y] < 200:
                        continue
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))
            if touches_edge or len(points) < 20:
                continue
            center_x = sum(point[0] for point in points) / len(points)
            center_y = sum(point[1] for point in points) / len(points)
            result.append({
                "white_pixels": len(points),
                "relative_x": round(center_x / width, 4),
                "relative_y": round(center_y / height, 4),
            })
    return sorted(result, key=lambda item: int(item["white_pixels"]), reverse=True)


def cell_bits(image: Image.Image, box: tuple[int, int, int, int]) -> bytes:
    crop = image.convert("L").crop(box)
    return bytes(1 if value < 128 else 0 for value in crop.getdata())


def parse_cell(value: str) -> tuple[int, int]:
    row, separator, column = value.partition(",")
    if separator != "," or not row.isdigit() or not column.isdigit():
        raise ValueError(f"invalid cell {value!r}; expected row,column")
    return int(row), int(column)


def verify(
    candidate: pathlib.Path,
    rows: int,
    columns: int,
    locations: dict[str, tuple[int, int]],
) -> dict[str, object]:
    errors: list[str] = []
    labels = tuple((row, column, label) for label, (row, column) in locations.items())
    with Image.open(candidate) as image:
        width, height = image.size
        cells: dict[str, bytes] = {}
        positions: dict[str, dict[str, float]] = {}
        for row, column, label in labels:
            if row >= rows or column >= columns:
                errors.append(f"{label}: cell {row},{column} is outside {rows}x{columns}")
                continue
            left = round(column * width / columns)
            right = round((column + 1) * width / columns)
            top = round(row * height / rows)
            bottom = round((row + 1) * height / rows)
            cell = image.crop((left, top, right, bottom))
            eye_components = components(cell, (0, 0, cell.width, cell.height))
            if len(eye_components) != 2:
                errors.append(f"{label}: expected two detected open-eye bodies")
                continue
            primary_marks = [enclosed_white_components(cell, eye)[:1] for eye in eye_components]
            if any(not marks for marks in primary_marks):
                errors.append(f"{label}: a primary in-eye reflection could not be found")
                continue
            positions[label] = {
                "primary_reflection_x": round(sum(float(marks[0]["relative_x"]) for marks in primary_marks) / 2, 4),
                "primary_reflection_y": round(sum(float(marks[0]["relative_y"]) for marks in primary_marks) / 2, 4),
            }
            cells[label] = cell_bits(image, (left, top, right, bottom))

    for left_label, right_label in (("left", "right"), ("left", "up"), ("left", "down"),
                                    ("right", "up"), ("right", "down"), ("up", "down")):
        if left_label not in cells or right_label not in cells:
            continue
        difference = sum(left != right for left, right in zip(cells[left_label], cells[right_label]))
        if difference < MIN_PAIR_PIXEL_DIFFERENCE:
            errors.append(f"{left_label}/{right_label}: only {difference} pixels differ")
    if "left" in positions and positions["left"]["primary_reflection_x"] > LEFT_MAX_PRIMARY_X:
        errors.append("left: primary reflection is not visibly left-biased")
    if "right" in positions and positions["right"]["primary_reflection_x"] < RIGHT_MIN_PRIMARY_X:
        errors.append("right: primary reflection is not visibly right-biased")
    if "up" in positions and positions["up"]["primary_reflection_y"] > UP_MAX_PRIMARY_Y:
        errors.append("up: primary reflection is not visibly upper-biased")
    if "down" in positions and positions["down"]["primary_reflection_y"] < DOWN_MIN_PRIMARY_Y:
        errors.append("down: primary reflection is not visibly lower-biased")

    return {
        "schema": "companion.v9_daily_attention_proof_gate.v1",
        "status": "PASS_DAILY_ATTENTION_PROOF_GATE" if not errors else "FAIL_DAILY_ATTENTION_PROOF_GATE",
        "candidate": rel(candidate),
        "candidate_sha256": sha256(candidate),
        "grid": [rows, columns],
        "direction_cells": {label: f"{row},{column}" for label, (row, column) in locations.items()},
        "direction_primary_positions": positions,
        "minimum_pair_pixel_difference": MIN_PAIR_PIXEL_DIFFERENCE,
        "direction_thresholds": {
            "left_max_primary_x": LEFT_MAX_PRIMARY_X,
            "right_min_primary_x": RIGHT_MIN_PRIMARY_X,
            "up_max_primary_y": UP_MAX_PRIMARY_Y,
            "down_min_primary_y": DOWN_MIN_PRIMARY_Y,
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--grid", nargs=2, type=int, metavar=("ROWS", "COLUMNS"), default=(2, 2))
    parser.add_argument("--left-cell", default="0,0")
    parser.add_argument("--right-cell", default="0,1")
    parser.add_argument("--up-cell", default="1,0")
    parser.add_argument("--down-cell", default="1,1")
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = args.candidate.resolve()
        if not candidate.is_file():
            raise ValueError(f"missing candidate: {candidate}")
        rows, columns = args.grid
        if rows <= 0 or columns <= 0:
            raise ValueError("grid dimensions must be positive")
        locations = {
            "left": parse_cell(args.left_cell),
            "right": parse_cell(args.right_cell),
            "up": parse_cell(args.up_cell),
            "down": parse_cell(args.down_cell),
        }
        result = verify(candidate, rows, columns, locations)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_DAILY_ATTENTION_PROOF_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: daily left/right/up/down have distinct, directionally readable reflections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
