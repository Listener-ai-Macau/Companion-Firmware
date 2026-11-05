#!/usr/bin/env python3
"""Check that open eyes preserve the solid V9 black-eye construction."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import deque

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCKED_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
MIN_EYE_WIDTH = 40
MIN_EYE_HEIGHT = 58
MIN_EYE_AREA = 1850
MIN_EYE_FILL_RATIO = 0.60
MAX_PAIR_BASELINE_DELTA = 8


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def parse_closed_cells(values: list[str]) -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for value in values:
        row, separator, column = value.partition(",")
        if separator != "," or not row.isdigit() or not column.isdigit():
            raise ValueError(f"invalid closed-eye cell {value!r}; expected row,column")
        result.add((int(row), int(column)))
    return result


def components(image: Image.Image, box: tuple[int, int, int, int]) -> list[dict[str, float | int]]:
    grayscale = image.convert("L")
    pixels = grayscale.load()
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    visited: set[tuple[int, int]] = set()
    result: list[dict[str, float | int]] = []
    for y in range(int(height * 0.25), int(height * 0.95)):
        for x in range(width):
            if (x, y) in visited or pixels[left + x, top + y] >= 128:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                point_x, point_y = queue.popleft()
                points.append((point_x, point_y))
                for delta_x, delta_y in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                                         (0, 1), (1, -1), (1, 0), (1, 1)):
                    next_x, next_y = point_x + delta_x, point_y + delta_y
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    if (next_x, next_y) in visited or pixels[left + next_x, top + next_y] >= 128:
                        continue
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            component_width = max(xs) - min(xs) + 1
            component_height = max(ys) - min(ys) + 1
            area = len(points)
            if component_width < MIN_EYE_WIDTH or component_height < MIN_EYE_HEIGHT:
                continue
            fill_ratio = area / (component_width * component_height)
            # A detached V9 charm may be taller than a brow but cannot satisfy either eye-body floor.
            if area < MIN_EYE_AREA and fill_ratio < MIN_EYE_FILL_RATIO:
                continue
            result.append({
                "x": min(xs),
                "y": min(ys),
                "width": component_width,
                "height": component_height,
                "black_pixels": area,
                "black_fill_ratio": round(fill_ratio, 4),
            })
    return sorted(result, key=lambda item: int(item["black_pixels"]), reverse=True)


def verify(
    candidate: pathlib.Path,
    closed_cells: set[tuple[int, int]],
    rows: int,
    columns: int,
) -> dict[str, object]:
    errors: list[str] = []
    with Image.open(candidate) as image:
        width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("candidate image has no pixels")
        records: list[dict[str, object]] = []
        for row in range(rows):
            for column in range(columns):
                left = round(column * width / columns)
                right = round((column + 1) * width / columns)
                top = round(row * height / rows)
                bottom = round((row + 1) * height / rows)
                cell_id = f"{row},{column}"
                if (row, column) in closed_cells:
                    records.append({"cell": cell_id, "eye_mode": "closed", "eye_components": []})
                    continue
                eye_components = components(image, (left, top, right, bottom))
                record: dict[str, object] = {"cell": cell_id, "eye_mode": "open", "eye_components": eye_components}
                records.append(record)
                if len(eye_components) != 2:
                    errors.append(f"{cell_id}: expected exactly two open-eye bodies, found {len(eye_components)}")
                    continue
                first, second = eye_components
                baseline_delta = abs(int(first["y"]) - int(second["y"]))
                record["pair_baseline_delta_px"] = baseline_delta
                if baseline_delta > MAX_PAIR_BASELINE_DELTA:
                    errors.append(f"{cell_id}: open-eye pair is not on one baseline ({baseline_delta}px)")
                for index, eye in enumerate(eye_components):
                    if int(eye["black_pixels"]) < MIN_EYE_AREA:
                        errors.append(f"{cell_id}: eye {index} is not a sufficiently filled black body")
                    if float(eye["black_fill_ratio"]) < MIN_EYE_FILL_RATIO:
                        errors.append(f"{cell_id}: eye {index} has hollow/ring-like fill ratio {eye['black_fill_ratio']}")
    return {
        "schema": "companion.v9_open_eye_identity_gate.v1",
        "status": "PASS_OPEN_EYE_IDENTITY_GATE" if not errors else "FAIL_OPEN_EYE_IDENTITY_GATE",
        "candidate": rel(candidate),
        "candidate_sha256": sha256(candidate),
        "grid": [rows, columns],
        "closed_eye_cells": [f"{row},{column}" for row, column in sorted(closed_cells)],
        "calibration": {
            "locked_v9_source": rel(LOCKED_SOURCE),
            "locked_v9_sha256": LOCKED_SOURCE_HASH,
            "minimum_eye_width_px": MIN_EYE_WIDTH,
            "minimum_eye_height_px": MIN_EYE_HEIGHT,
            "minimum_black_pixels": MIN_EYE_AREA,
            "minimum_black_fill_ratio": MIN_EYE_FILL_RATIO,
            "maximum_pair_baseline_delta_px": MAX_PAIR_BASELINE_DELTA,
        },
        "records": records,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--grid", nargs=2, type=int, metavar=("ROWS", "COLUMNS"), default=(3, 4),
        help="Contact-sheet rows and columns; defaults to the locked V9 3 by 4 layout.")
    parser.add_argument("--closed-eye-cell", action="append", default=[],
        help="One row,column cell to exempt as a closed-eye sleep pose; may be repeated.")
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = args.candidate.resolve()
        if not candidate.is_file():
            raise ValueError(f"missing candidate: {candidate}")
        rows, columns = args.grid
        if rows <= 0 or columns <= 0:
            raise ValueError("grid dimensions must be positive")
        result = verify(candidate, parse_closed_cells(args.closed_eye_cell), rows, columns)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_OPEN_EYE_IDENTITY_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: every declared open-eye cell preserves a filled, matched V9 eye pair.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
