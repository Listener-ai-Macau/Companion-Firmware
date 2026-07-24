"""Shared whole-expression anchor math for locked 200x200 visual candidates."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


CANVAS = (200, 200)
THRESHOLD = 180
CANONICAL_CENTER = (100, 100)
ANCHOR_POLICY = "whole_expression_visible_bbox_center"


@dataclass(frozen=True)
class AnchorTransform:
    source_anchor: tuple[int, int]
    canonical_center: tuple[int, int]
    normalization_offset: tuple[int, int]


def threshold(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < THRESHOLD else 255, "1")


def translate(image: Image.Image, offset: tuple[int, int]) -> Image.Image:
    result = Image.new("1", CANVAS, 255)
    result.paste(image.convert("1"), offset)
    return result


def ink_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    points = [(x, y) for y in range(bitmap.height) for x in range(bitmap.width) if pixels[x, y] == 0]
    if not points:
        raise ValueError("expression frame has no visible ink")
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def source_anchor(image: Image.Image) -> tuple[int, int]:
    left, top, right, bottom = ink_bounds(image)
    return ((left + right) // 2, (top + bottom) // 2)


def normalize(image: Image.Image, canonical_center: tuple[int, int] = CANONICAL_CENTER) -> tuple[Image.Image, AnchorTransform]:
    bitmap = threshold(image)
    anchor = source_anchor(bitmap)
    offset = (canonical_center[0] - anchor[0], canonical_center[1] - anchor[1])
    left, top, right, bottom = ink_bounds(bitmap)
    if (left + offset[0] < 0 or top + offset[1] < 0 or
            right + offset[0] >= CANVAS[0] or bottom + offset[1] >= CANVAS[1]):
        raise ValueError("canonical anchor normalization would clip visible expression ink")
    normalized = translate(bitmap, offset)
    return normalized, AnchorTransform(anchor, canonical_center, offset)


def output_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    left, top, right, bottom = ink_bounds(image)
    return left, top, right - left + 1, bottom - top + 1
