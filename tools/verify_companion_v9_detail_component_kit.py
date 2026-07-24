#!/usr/bin/env python3
"""Verify an isolated V9 secondary-detail component source sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import deque

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_COMPONENTS = (
    "cheek_detail_left", "cheek_detail_right", "cheek_dot_pair", "charm_sparkle",
    "charm_heart", "charm_question", "charm_exclamation", "detail_listening_arcs",
)
MIN_INK_PIXELS = 30
MAX_COMPONENT_INK_PIXELS = 6000
MIN_PAIR_PIXEL_DIFFERENCE = 100


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def cell_bits(image: Image.Image, box: tuple[int, int, int, int]) -> bytes:
    return bytes(1 if value < 128 else 0 for value in image.convert("L").crop(box).getdata())


def eye_like_components(image: Image.Image) -> int:
    """A source detail cell may not secretly contain a filled V9 eye body."""
    pixels = image.convert("L").load()
    width, height = image.size
    visited: set[tuple[int, int]] = set()
    count = 0
    for y in range(height):
        for x in range(width):
            if (x, y) in visited or pixels[x, y] >= 128:
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
                    if (next_x, next_y) in visited or pixels[next_x, next_y] >= 128:
                        continue
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            component_width = max(xs) - min(xs) + 1
            component_height = max(ys) - min(ys) + 1
            fill_ratio = len(points) / (component_width * component_height)
            if component_height >= 80 and 0.35 <= component_width / component_height <= 0.85 and fill_ratio >= 0.55:
                count += 1
    return count


def verify(candidate: pathlib.Path, request_path: pathlib.Path) -> dict[str, object]:
    errors: list[str] = []
    request = load_json(request_path)
    required_components = tuple(request.get("required_cells", []))
    semantics = request.get("component_semantics")
    target_profile = request.get("target_profile")
    if request.get("source_art_type") != "detail_component_kit":
        errors.append("detail-kit request is not declared as an isolated component source")
    if required_components != EXPECTED_COMPONENTS:
        errors.append("detail-kit request does not enumerate the ordered eight-component vocabulary")
    if not isinstance(semantics, dict) or tuple(semantics) != EXPECTED_COMPONENTS:
        errors.append("detail-kit request does not bind semantics to every component")
    if not isinstance(target_profile, dict) or target_profile.get("grid") != [2, 4]:
        errors.append("detail-kit request is not a 2x4 source sheet")

    with Image.open(candidate) as image:
        width, height = image.size
        cells: list[bytes] = []
        hashes: list[str] = []
        records: list[dict[str, object]] = []
        for index, component in enumerate(EXPECTED_COMPONENTS):
            row, column = divmod(index, 4)
            box = (
                round(column * width / 4), round(row * height / 2),
                round((column + 1) * width / 4), round((row + 1) * height / 2),
            )
            crop = image.crop(box)
            bits = cell_bits(image, box)
            ink_pixels = sum(bits)
            digest = hashlib.sha256(bits).hexdigest().upper()
            eye_like_count = eye_like_components(crop)
            records.append({
                "component": component,
                "cell": f"{row},{column}",
                "semantic": semantics.get(component) if isinstance(semantics, dict) else None,
                "ink_pixels": ink_pixels,
                "eye_like_component_count": eye_like_count,
                "binary_sha256": digest,
            })
            cells.append(bits)
            hashes.append(digest)
            if ink_pixels < MIN_INK_PIXELS:
                errors.append(f"{component} is visually blank")
            if ink_pixels > MAX_COMPONENT_INK_PIXELS:
                errors.append(f"{component} is too dense to be an isolated secondary detail")
            if eye_like_count:
                errors.append(f"{component} contains a forbidden eye-like filled oval")
        if len(set(hashes)) != len(EXPECTED_COMPONENTS):
            errors.append("detail-kit source contains duplicate component cells")
        minimum_difference = None
        for left in range(len(cells)):
            for right in range(left + 1, len(cells)):
                difference = sum(first != second for first, second in zip(cells[left], cells[right]))
                minimum_difference = difference if minimum_difference is None else min(minimum_difference, difference)
                if difference < MIN_PAIR_PIXEL_DIFFERENCE:
                    errors.append(f"{EXPECTED_COMPONENTS[left]}/{EXPECTED_COMPONENTS[right]} are too similar ({difference}px)")
    return {
        "schema": "companion.v9_detail_component_kit_gate.v1",
        "status": "PASS_DETAIL_COMPONENT_KIT_GATE" if not errors else "FAIL_DETAIL_COMPONENT_KIT_GATE",
        "candidate": rel(candidate),
        "candidate_sha256": sha256(candidate),
        "request": rel(request_path),
        "component_count": len(EXPECTED_COMPONENTS),
        "unique_component_count": len(set(hashes)),
        "minimum_pair_pixel_difference": minimum_difference,
        "records": records,
        "runtime_resource_activated": False,
        "full_face_playback": "forbidden",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--request", type=pathlib.Path, required=True)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = args.candidate.resolve()
        if not candidate.is_file():
            raise ValueError(f"missing candidate: {candidate}")
        result = verify(candidate, args.request.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_DETAIL_COMPONENT_KIT_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: eight isolated secondary V9 detail components are source-ready candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
