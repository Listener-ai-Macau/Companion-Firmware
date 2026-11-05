#!/usr/bin/env python3
"""Gate the V45 five-stage complete-eye pair source before Rig export."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/generation-request-v6.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/candidate/attempt-05-complete-eye-width-preserving.png"
REPORT = ROOT / "docs/validation/companion-v45-complete-eye-pair-source-v6-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_SHA = "07EADF4D5273CAD598631BB8A3D64231101FAA805D3F019DCEEACD54BBBCE007"
STAGES = ("open", "closing", "closed", "opening", "open_return")


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


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < 128 else 255, mode="1")


def components(image: Image.Image) -> list[Image.Image]:
    """Split a stage into its two source-derived complete eye groups."""
    mask = binary(image)
    width, height = mask.size
    remaining = {(x, y) for y in range(height) for x in range(width) if mask.getpixel((x, y)) == 0}
    found: list[tuple[int, Image.Image]] = []
    while remaining:
        seed = remaining.pop()
        queue: deque[tuple[int, int]] = deque([seed])
        points = [seed]
        while queue:
            x, y = queue.popleft()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1),
                             (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
                    points.append(neighbor)
        if len(points) > 10:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
            found.append((min(xs), mask.crop(box)))
    require(len(found) == 2, f"V45 stage must contain exactly two eye groups, found {len(found)}")
    return [item[1] for item in sorted(found, key=lambda item: item[0])]


def ink_pixels(mask: Image.Image) -> int:
    return sum(1 for pixel in mask.convert("1").getdata() if pixel == 0)


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


def direct_pair_difference(left: Image.Image, right: Image.Image) -> int:
    width = max(left.width, right.width)
    height = max(left.height, right.height)
    left_canvas = Image.new("1", (width, height), 1)
    right_canvas = Image.new("1", (width, height), 1)
    left_canvas.paste(left, ((width - left.width) // 2, (height - left.height) // 2))
    right_canvas.paste(right, ((width - right.width) // 2, (height - right.height) // 2))
    return sum(1 for pixel in ImageChops.difference(left_canvas, right_canvas).getdata() if pixel != 0)


def stage_metrics(stage: str, pair: list[Image.Image]) -> dict[str, Any]:
    left, right = pair
    left_ink = ink_pixels(left)
    right_ink = ink_pixels(right)
    delta = abs(left_ink - right_ink) / max(left_ink, right_ink)
    require(left.height == right.height, f"V45 {stage} pair heights drifted: {left.size}, {right.size}")
    require(abs(left.width - right.width) <= 2, f"V45 {stage} pair widths drifted: {left.size}, {right.size}")
    require(delta <= 0.05, f"V45 {stage} pair ink delta exceeded 5%: {left_ink}, {right_ink}")
    return {
        "name": stage,
        "left": {"tight_size": list(left.size), "ink_pixels": left_ink, "interior_white_pixels": interior_white_pixels(left)},
        "right": {"tight_size": list(right.size), "ink_pixels": right_ink, "interior_white_pixels": interior_white_pixels(right)},
        "width_delta": abs(left.width - right.width),
        "relative_ink_delta": delta,
        "direct_pair_pixel_difference": direct_pair_difference(left, right),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request = load(REQUEST)
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            request.get("source_sheet", {}).get("grid", {}).get("columns") == 5,
            "V45 complete-eye pair request provenance drifted")
    require(SOURCE.is_file() and sha256(SOURCE) == SOURCE_SHA, "V45 complete-eye pair source hash drifted")
    with Image.open(SOURCE) as opened:
        sheet = binary(opened)
    stages: list[list[Image.Image]] = []
    metrics: list[dict[str, Any]] = []
    for index, name in enumerate(STAGES):
        left = round(index * sheet.width / 5)
        right = round((index + 1) * sheet.width / 5)
        pair = components(sheet.crop((left, 0, right, sheet.height)))
        stages.append(pair)
        metrics.append(stage_metrics(name, pair))
    heights = [metrics[index]["left"]["tight_size"][1] for index in range(5)]
    require(heights[0] > heights[1] > heights[2] and heights[2] < heights[3] < heights[4],
            f"V45 complete-eye stage heights are not open>closing>closed<opening<open: {heights}")
    require(abs(heights[0] - heights[4]) <= 2, f"V45 open return height drifted: {heights[0]}, {heights[4]}")
    require(all(metrics[index]["left"]["interior_white_pixels"] > 0 and
                metrics[index]["right"]["interior_white_pixels"] > 0 for index in (0, 1, 3, 4)),
            "V45 open/closing/opening eye groups lost their internal V9 reflection or sparkle holes")
    report = {
        "schema": "companion.v45_complete_eye_pair_source_v6_gate.v1",
        "status": "PASS_V45_COMPLETE_EYE_CLOSURE_PAIR_SOURCE_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-267", "COMP-REQ-269"],
        "locked_v9_source_sha256": LOCKED,
        "generated_source": {"path": rel(SOURCE), "sha256": SOURCE_SHA, "dimensions": list(sheet.size),
                              "request": rel(REQUEST), "stages": metrics},
        "stage_height_order": {"open": heights[0], "closing": heights[1], "closed": heights[2],
                                "opening": heights[3], "open_return": heights[4]},
        "complete_eye_contract": "eye body + white primary reflection + tiny white sparkle for open/closing/opening; closed stroke for closed",
        "runtime_resource_activated": False,
        "non_claims": ["no_whole_face_art", "no_lower_driver_change", "no_human_acceptance"],
    }
    output = args.write if args.write.is_absolute() else ROOT / args.write
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V45 complete-eye pair source is stage-ordered, paired and source-only ({output}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
