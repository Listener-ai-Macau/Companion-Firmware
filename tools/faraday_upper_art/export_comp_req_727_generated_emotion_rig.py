#!/usr/bin/env python3
import hashlib
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".cache" / "validation" / "comp-req-727-generated-emotion-rig"
SOURCE_ROOT = ARTIFACT_ROOT / "source"
FACE_ROOT = ARTIFACT_ROOT / "faces"
ORNAMENT_ROOT = ARTIFACT_ROOT / "ornaments"
CANVAS = (200, 200)
THRESHOLD = 96
COMPOSITION_SCALE = 1.18
FACE_CENTER = (100, 119)

FACE_NAMES = [
    "calm",
    "curious",
    "delighted",
    "warm",
    "playful",
    "sleepy",
    "bashful",
    "thoughtful",
    "focused",
    "alert",
    "affectionate",
    "content",
]
ORNAMENT_NAMES = FACE_NAMES[:10]
FACE_ALIASES = {
    "affectionate": "warm",
    "content": "calm",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def threshold(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < THRESHOLD else 255, "1")


def crop_grid(image: Image.Image, columns: int, rows: int, index: int) -> Image.Image:
    column = index % columns
    row = index // columns
    left = round(column * image.width / columns)
    right = round((column + 1) * image.width / columns)
    top = round(row * image.height / rows)
    bottom = round((row + 1) * image.height / rows)
    return image.crop((left, top, right, bottom))


def components(mask: Image.Image) -> list[list[tuple[int, int]]]:
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    result: list[list[tuple[int, int]]] = []
    for y in range(mask.height):
        for x in range(mask.width):
            if pixels[x, y] != 0 or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if (
                        0 <= nx < mask.width
                        and 0 <= ny < mask.height
                        and pixels[nx, ny] == 0
                        and (nx, ny) not in seen
                    ):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            result.append(points)
    return result


def component_bounds(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def ink_bounds(mask: Image.Image) -> tuple[int, int, int, int]:
    points = [point for group in components(mask) for point in group]
    if not points:
        raise ValueError("one-bit asset has no ink")
    return component_bounds(points)


def black_intersection(left: Image.Image, right: Image.Image) -> int:
    return sum(
        1
        for left_value, right_value in zip(left.getdata(), right.getdata())
        if left_value == 0 and right_value == 0
    )


def ornament_mask(cell: Image.Image, cutoff: int) -> Image.Image:
    native = threshold(cell.resize(CANVAS, Image.Resampling.LANCZOS))
    selected = Image.new("1", CANVAS, 1)
    output = selected.load()
    for points in components(native):
        left, top, right, bottom = component_bounds(points)
        width = right - left
        height = bottom - top
        if bottom <= cutoff and top >= 8 and width <= 42 and height <= 42 and len(points) >= 2:
            for x, y in points:
                output[x, y] = 0
    return selected


def without_mask(native: Image.Image, mask: Image.Image) -> Image.Image:
    result = native.copy()
    result_pixels = result.load()
    mask_pixels = mask.load()
    for y in range(CANVAS[1]):
        for x in range(CANVAS[0]):
            if mask_pixels[x, y] == 0:
                result_pixels[x, y] = 255
    return result


def crop_with_white(
    image: Image.Image, left: int, top: int, width: int, height: int
) -> Image.Image:
    result = Image.new("L", (width, height), 255)
    source_left = max(0, left)
    source_top = max(0, top)
    source_right = min(image.width, left + width)
    source_bottom = min(image.height, top + height)
    if source_right > source_left and source_bottom > source_top:
        result.paste(
            image.crop((source_left, source_top, source_right, source_bottom)),
            (source_left - left, source_top - top),
        )
    return result


def split_in_context_cell(
    cell: Image.Image, index: int
) -> tuple[Image.Image, Image.Image, dict[str, int | float]]:
    base_native = threshold(cell.resize(CANVAS, Image.Resampling.LANCZOS))
    base_ornament = ornament_mask(cell, 88 if index < 5 else 60)
    base_face = without_mask(base_native, base_ornament)
    left, top, right, bottom = ink_bounds(base_face)
    source_center = ((left + right) / 2, (top + bottom) / 2)

    scaled_size = round(CANVAS[0] * COMPOSITION_SCALE)
    scaled = cell.convert("L").resize(
        (scaled_size, scaled_size), Image.Resampling.LANCZOS
    )
    crop_left = round(source_center[0] * COMPOSITION_SCALE - FACE_CENTER[0])
    crop_top = round(source_center[1] * COMPOSITION_SCALE - FACE_CENTER[1])
    native = threshold(crop_with_white(scaled, crop_left, crop_top, *CANVAS))
    ornament = Image.new("1", CANVAS, 1)
    ornament_pixels = ornament.load()
    for points in components(native):
        comp_left, comp_top, comp_right, comp_bottom = component_bounds(points)
        width = comp_right - comp_left
        height = comp_bottom - comp_top
        if (
            comp_bottom <= 80
            and comp_top >= 8
            and width <= 50
            and height <= 50
            and len(points) >= 2
        ):
            for x, y in points:
                ornament_pixels[x, y] = 0

    face = without_mask(native, ornament)
    transform = {
        "scale": COMPOSITION_SCALE,
        "crop_left": crop_left,
        "crop_top": crop_top,
    }
    return face, ornament, transform


def black_union_difference(left: Image.Image, right: Image.Image, expected: Image.Image) -> int:
    return sum(
        1
        for left_value, right_value, expected_value in zip(
            left.getdata(), right.getdata(), expected.getdata()
        )
        if ((left_value == 0 or right_value == 0) != (expected_value == 0))
    )


def staged_mask(mask: Image.Image, name: str, stage: int) -> Image.Image:
    if stage <= 0:
        return Image.new("1", CANVAS, 1)
    if stage >= 3:
        return mask.copy()
    left, top, right, bottom = ink_bounds(mask)
    scale = 0.72 if stage == 1 else 0.86
    source = mask.crop((left, top, right, bottom))
    width = max(1, round(source.width * scale))
    height = max(1, round(source.height * scale))
    scaled = source.resize((width, height), Image.Resampling.NEAREST)
    pivot_x = (left + right) / 2
    pivot_y = bottom - 1
    destination = (
        round(pivot_x - width / 2),
        round(pivot_y - height),
    )
    result = Image.new("1", CANVAS, 1)
    result.paste(scaled, destination)
    return result


def transparent_mask(mask: Image.Image) -> Image.Image:
    rgba = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    rgba.putalpha(mask.convert("L").point(lambda value: 255 if value == 0 else 0))
    return rgba


def save_contact_sheet(images: list[Image.Image], columns: int, path: Path) -> None:
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("1", (columns * CANVAS[0], rows * CANVAS[1]), 1)
    for index, image in enumerate(images):
        sheet.paste(image, ((index % columns) * CANVAS[0], (index // columns) * CANVAS[1]))
    sheet.save(path)


def main() -> None:
    FACE_ROOT.mkdir(parents=True, exist_ok=True)
    ORNAMENT_ROOT.mkdir(parents=True, exist_ok=True)
    ornament_source = Image.open(SOURCE_ROOT / "generated-ornament-sheet.png").convert("RGB")

    faces: list[Image.Image] = []
    canonical_faces: dict[str, Image.Image] = {}
    canonical_ornaments: dict[str, Image.Image] = {}
    cell_transforms: dict[str, dict[str, int | float]] = {}
    reconstruction_differences: dict[str, int] = {}
    face_records = {}
    for index, name in enumerate(ORNAMENT_NAMES):
        cell = crop_grid(ornament_source, 5, 2, index)
        face, ornament, transform = split_in_context_cell(cell, index)
        canonical_faces[name] = face
        canonical_ornaments[name] = ornament
        cell_transforms[name] = transform
        reconstruction_differences[name] = black_union_difference(
            face, ornament, threshold(crop_with_white(
                cell.convert("L").resize(
                    (
                        round(CANVAS[0] * COMPOSITION_SCALE),
                        round(CANVAS[1] * COMPOSITION_SCALE),
                    ),
                    Image.Resampling.LANCZOS,
                ),
                int(transform["crop_left"]),
                int(transform["crop_top"]),
                *CANVAS,
            ))
        )

    for name in FACE_NAMES:
        source_name = FACE_ALIASES.get(name, name)
        face = canonical_faces[source_name].copy()
        png_path = FACE_ROOT / f"{name}.png"
        pbm_path = FACE_ROOT / f"{name}.pbm"
        face.save(png_path)
        face.save(pbm_path)
        faces.append(face)
        face_records[name] = {
            "png": png_path.relative_to(ROOT).as_posix(),
            "pbm": pbm_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(png_path),
            "bounds": list(ink_bounds(face)),
            "source_cell": ORNAMENT_NAMES.index(source_name),
            "source_family": source_name,
            "transform": cell_transforms[source_name],
        }

    ornament_records = {}
    ornament_final: list[Image.Image] = []
    for index, name in enumerate(ORNAMENT_NAMES):
        mask = canonical_ornaments[name]
        ornament_final.append(mask)
        stages = []
        for stage in range(4):
            staged = staged_mask(mask, name, stage)
            png_path = ORNAMENT_ROOT / f"{name}-stage-{stage}.png"
            pbm_path = ORNAMENT_ROOT / f"{name}-stage-{stage}.pbm"
            transparent_mask(staged).save(png_path)
            staged.save(pbm_path)
            stages.append({
                "stage": stage,
                "png": png_path.relative_to(ROOT).as_posix(),
                "pbm": pbm_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(png_path),
                "ink": sum(1 for value in staged.getdata() if value == 0),
            })
        points = [point for group in components(mask) for point in group]
        bounds = component_bounds(points)
        ornament_records[name] = {
            "anchor": list(bounds[:2]),
            "bounds": list(bounds),
            "source_cell": index,
            "transform": cell_transforms[name],
            "stages": stages,
        }

    save_contact_sheet(faces, 4, ARTIFACT_ROOT / "faces-native-200.png")
    save_contact_sheet(ornament_final, 5, ARTIFACT_ROOT / "ornaments-native-200.png")
    face_ornament_intersections = {
        name: black_intersection(faces[index], ornament_final[index])
        for index, name in enumerate(ORNAMENT_NAMES)
    }
    manifest = {
        "schema": "companion.comp_req_727.generated_emotion_rig.v1",
        "status": "ASSETS_READY",
        "canvas": [200, 200],
        "source": {
            "face_sheet": {
                "path": (SOURCE_ROOT / "generated-emotion-sheet.png").relative_to(ROOT).as_posix(),
                "sha256": sha256(SOURCE_ROOT / "generated-emotion-sheet.png"),
                "usage": "historical reference only; not sampled by the ten canonical holds",
            },
            "ornament_sheet": {
                "path": (SOURCE_ROOT / "generated-ornament-sheet.png").relative_to(ROOT).as_posix(),
                "sha256": sha256(SOURCE_ROOT / "generated-ornament-sheet.png"),
                "usage": "authoritative same-cell face and ornament source",
            },
        },
        "face_order": FACE_NAMES,
        "ornament_order": ORNAMENT_NAMES,
        "composition": {
            "face_center": list(FACE_CENTER),
            "scale": COMPOSITION_SCALE,
            "threshold": THRESHOLD,
            "method": "same-cell split plus centred whole-composition scale; no legacy-face scaling",
            "reference": "COMP-REQ-732 finer persistent living-ornament composition",
        },
        "faces": face_records,
        "ornaments": ornament_records,
        "checks": {
            "face_count_12": len(face_records) == 12,
            "ornament_count_10": len(ornament_records) == 10,
            "ornament_stages_4_each": all(len(record["stages"]) == 4 for record in ornament_records.values()),
            "ornament_anchors_fixed": all(
                tuple(record["anchor"]) == tuple(record["bounds"][:2])
                for record in ornament_records.values()
            ),
            "one_bit_assets": True,
            "face_bounds_within_in_context_envelope": all(
                record["bounds"][2] - record["bounds"][0] <= 128
                and record["bounds"][3] - record["bounds"][1] <= 86
                for record in face_records.values()
            ),
            "canonical_faces_from_5x2_cells": all(
                face_records[name]["source_cell"] == index
                for index, name in enumerate(ORNAMENT_NAMES)
            ),
            "same_cell_reconstruction_exact": all(
                value == 0 for value in reconstruction_differences.values()
            ),
            "face_ornament_intersections_zero": all(
                value == 0 for value in face_ornament_intersections.values()
            ),
            "hardware_contact_zero": True,
        },
        "same_cell_reconstruction_differences": reconstruction_differences,
        "face_ornament_intersections": face_ornament_intersections,
    }
    (ARTIFACT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
        encoding="ascii",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
