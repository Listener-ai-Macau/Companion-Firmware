#!/usr/bin/env python3
"""Recover the accepted COMP-REQ-616 face strokes without baked ornaments."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / ".cache/validation/comp-req-616-ten-family-choreography"
SOURCE = SOURCE_ROOT / "wb55-frame-plan.bin"
SOURCE_PLAN = SOURCE_ROOT / "canonical-frame-plan.json"
CURRENT_FACE_ROOT = (
    ROOT / ".cache/validation/comp-req-727-generated-emotion-rig/faces"
)
CURRENT_ORNAMENT_ROOT = (
    ROOT / ".cache/validation/comp-req-727-generated-emotion-rig/ornaments"
)
OUTPUT = ROOT / ".cache/validation/comp-req-772-legacy-line-style-browser"
FRAME_BYTES = 5000
WIDTH = 200
HEIGHT = 200
STATUS_HEIGHT = 14
FACE_COMPONENT_LIMIT = 8
FAMILIES = (
    ("calm", 0),
    ("curious", 18),
    ("delighted", 36),
    ("warm", 54),
    ("playful", 72),
    ("sleepy", 90),
    ("bashful", 108),
    ("thoughtful", 126),
    ("focused", 144),
    ("alert", 162),
)
BALANCE_OFFSETS = {
    "calm": (0, 8),
    "curious": (-1, -16),
    "delighted": (-1, 4),
    "warm": (1, 13),
    "playful": (3, 8),
    "sleepy": (0, -8),
    "bashful": (0, 13),
    "thoughtful": (-5, 2),
    "focused": (-2, 13),
    "alert": (0, -14),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def decode_frame(payload: bytes) -> set[tuple[int, int]]:
    ink: set[tuple[int, int]] = set()
    for y in range(HEIGHT):
        row = payload[y * (WIDTH // 8) : (y + 1) * (WIDTH // 8)]
        for x in range(WIDTH):
            if not row[x // 8] & (0x80 >> (x % 8)):
                ink.add((x, y))
    return ink


def components(ink: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    pending = {point for point in ink if point[1] >= STATUS_HEIGHT}
    result: list[set[tuple[int, int]]] = []
    neighbours = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    )
    while pending:
        start = pending.pop()
        queue = deque((start,))
        component = {start}
        while queue:
            x, y = queue.popleft()
            for dx, dy in neighbours:
                point = (x + dx, y + dy)
                if point in pending:
                    pending.remove(point)
                    component.add(point)
                    queue.append(point)
        result.append(component)
    return sorted(result, key=len, reverse=True)


def write_png(path: Path, ink: set[tuple[int, int]]) -> None:
    image = Image.new("1", (WIDTH, HEIGHT), 1)
    pixels = image.load()
    for x, y in ink:
        pixels[x, y] = 0
    image.save(path)


def translate_ink(
    ink: set[tuple[int, int]], offset: tuple[int, int]
) -> set[tuple[int, int]]:
    dx, dy = offset
    return {
        (x + dx, y + dy)
        for x, y in ink
        if 0 <= x + dx < WIDTH and STATUS_HEIGHT <= y + dy < HEIGHT
    }


def write_alpha_png(path: Path, ink: set[tuple[int, int]]) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = image.load()
    for x, y in ink:
        pixels[x, y] = (0, 0, 0, 255)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def enclosed_white_pixels(image: Image.Image) -> set[tuple[int, int]]:
    pixels = image.load()
    exterior: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for x in range(WIDTH):
        for y in (0, HEIGHT - 1):
            if pixels[x, y] != 0 and (x, y) not in exterior:
                exterior.add((x, y))
                queue.append((x, y))
    for y in range(HEIGHT):
        for x in (0, WIDTH - 1):
            if pixels[x, y] != 0 and (x, y) not in exterior:
                exterior.add((x, y))
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            point = (x + dx, y + dy)
            if (
                0 <= point[0] < WIDTH
                and 0 <= point[1] < HEIGHT
                and point not in exterior
                and pixels[point[0], point[1]] != 0
            ):
                exterior.add(point)
                queue.append(point)
    return {
        (x, y)
        for y in range(STATUS_HEIGHT, HEIGHT)
        for x in range(WIDTH)
        if pixels[x, y] != 0 and (x, y) not in exterior
    }


def component_bounds(component: set[tuple[int, int]]) -> dict[str, float]:
    xs = [point[0] for point in component]
    ys = [point[1] for point in component]
    return {
        "left": min(xs),
        "top": min(ys),
        "right": max(xs),
        "bottom": max(ys),
        "center_x": (min(xs) + max(xs)) / 2,
        "center_y": (min(ys) + max(ys)) / 2,
    }


def rounded_superellipse(
    bounds: dict[str, float], power: float | tuple[float, float]
) -> set[tuple[int, int]]:
    left = int(bounds["left"])
    top = int(bounds["top"])
    right = int(bounds["right"])
    bottom = int(bounds["bottom"])
    width = right - left + 1
    height = bottom - top + 1
    center_x = left + width / 2
    center_y = top + height / 2
    radius_x = width / 2
    radius_y = height / 2
    power_x, power_y = (
        power if isinstance(power, tuple) else (power, power)
    )
    return {
        (x, y)
        for y in range(top, bottom + 1)
        for x in range(left, right + 1)
        if (
            abs((x + 0.5 - center_x) / radius_x) ** power_x
            + abs((y + 0.5 - center_y) / radius_y) ** power_y
            <= 1.0
        )
    }


def one_pixel_halo(
    points: set[tuple[int, int]], bounds: dict[str, float]
) -> set[tuple[int, int]]:
    return {
        (x + dx, y + dy)
        for x, y in points
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (
            bounds["left"] <= x + dx <= bounds["right"]
            and bounds["top"] <= y + dy <= bounds["bottom"]
        )
    }


def terminal_row_widths(component: set[tuple[int, int]]) -> list[int]:
    bounds = component_bounds(component)
    left = int(bounds["left"])
    right = int(bounds["right"])
    top = int(bounds["top"])
    bottom = int(bounds["bottom"])
    rows = (top, min(top + 1, bottom), max(top, bottom - 1), bottom)
    return [
        sum((x, y) in component for x in range(left, right + 1))
        for y in rows
    ]


def terminal_column_heights(component: set[tuple[int, int]]) -> list[int]:
    bounds = component_bounds(component)
    left = int(bounds["left"])
    right = int(bounds["right"])
    top = int(bounds["top"])
    bottom = int(bounds["bottom"])
    columns = (
        left,
        min(left + 1, right),
        max(left, right - 1),
        right,
    )
    return [
        sum((x, y) in component for y in range(top, bottom + 1))
        for x in columns
    ]


def taper_terminal_caps(
    component: set[tuple[int, int]],
    row_limits: tuple[int, int] = (5, 10),
    column_limits: tuple[int, int] = (5, 13),
) -> set[tuple[int, int]]:
    """Keep all four one-bit terminals pointed without thinning the eye body."""
    result = set(component)
    bounds = component_bounds(component)
    full_width = int(bounds["right"] - bounds["left"] + 1)
    full_height = int(bounds["bottom"] - bounds["top"] + 1)

    def centered(values: list[int], limit: int, reference_span: int) -> set[int]:
        if len(values) <= limit:
            return set(values)
        count = limit
        if count % 2 != reference_span % 2:
            count -= 1
        count = max(1, count)
        center = (min(values) + max(values)) / 2
        return set(
            sorted(values, key=lambda value: (abs(value - center), value))[:count]
        )

    top = int(bounds["top"])
    bottom = int(bounds["bottom"])
    for y, limit in (
        (top, row_limits[0]),
        (top + 1, row_limits[1]),
        (bottom - 1, row_limits[1]),
        (bottom, row_limits[0]),
    ):
        row = [x for x, point_y in result if point_y == y]
        keep = centered(row, limit, full_width)
        result = {
            point
            for point in result
            if point[1] != y or point[0] in keep
        }

    left = int(bounds["left"])
    right = int(bounds["right"])
    for x, limit in (
        (left, column_limits[0]),
        (left + 1, column_limits[1]),
        (right - 1, column_limits[1]),
        (right, column_limits[0]),
    ):
        column = [y for point_x, y in result if point_x == x]
        keep = centered(column, limit, full_height)
        result = {
            point
            for point in result
            if point[0] != x or point[1] in keep
        }
    return result


def replace_with_rounded_role(
    face_ink: set[tuple[int, int]],
    component: set[tuple[int, int]],
    power: float,
) -> tuple[set[tuple[int, int]], dict]:
    bounds = component_bounds(component)
    rounded = rounded_superellipse(bounds, power)
    result = set(face_ink)
    result.difference_update(component)
    result.update(rounded)
    return result, {
        "bounds": [
            int(bounds["left"]),
            int(bounds["top"]),
            int(bounds["right"]),
            int(bounds["bottom"]),
        ],
        "source_ink_pixels": len(component),
        "crafted_ink_pixels": len(rounded),
        "ink_ratio": round(len(rounded) / len(component), 4),
        "component_count": len(components(rounded)),
    }


def face_roles(
    face_components: list[set[tuple[int, int]]],
) -> dict[str, list[set[tuple[int, int]]]]:
    eyes = sorted(face_components[:2], key=lambda item: component_bounds(item)["center_x"])
    eye_bounds = [component_bounds(item) for item in eyes]
    eye_top = min(item["top"] for item in eye_bounds)
    eye_bottom = max(item["bottom"] for item in eye_bounds)
    roles: dict[str, list[set[tuple[int, int]]]] = {
        "eyes": eyes,
        "brows": [],
        "cheeks": [],
        "nose": [],
        "mouth": [],
    }
    central: list[set[tuple[int, int]]] = []
    central_feature_floor = eye_top + (eye_bottom - eye_top) * 0.45
    for component in face_components[2:]:
        bounds = component_bounds(component)
        if (
            72 <= bounds["center_x"] <= 128
            and bounds["top"] >= central_feature_floor
        ):
            central.append(component)
        elif bounds["bottom"] < eye_top:
            roles["brows"].append(component)
        elif bounds["top"] >= eye_bottom - 7:
            roles["cheeks"].append(component)
        else:
            roles["brows"].append(component)
    central.sort(key=lambda item: component_bounds(item)["center_y"])
    if central:
        roles["nose"] = central[:1]
    if len(central) > 1:
        roles["mouth"] = central[1:]
    for role in ("brows", "cheeks"):
        roles[role].sort(key=lambda item: component_bounds(item)["center_x"])
    return roles


def evenly_spaced(
    points: list[tuple[int, int]], count: int, center: tuple[float, float]
) -> list[tuple[int, int]]:
    if count >= len(points):
        return points
    cx, cy = center
    ordered = sorted(
        points,
        key=lambda point: (
            math.atan2(point[1] - cy, point[0] - cx),
            (point[0] - cx) ** 2 + (point[1] - cy) ** 2,
            point[1],
            point[0],
        ),
    )
    return [ordered[(index * len(ordered)) // count] for index in range(count)]


def grow_component(
    component: set[tuple[int, int]], target_ink: int
) -> set[tuple[int, int]]:
    grown = set(component)
    cross = ((-1, 0), (0, -1), (0, 1), (1, 0))
    diagonal = ((-1, -1), (1, -1), (-1, 1), (1, 1))
    bounds = component_bounds(component)
    center = (bounds["center_x"], bounds["center_y"])
    while len(grown) < target_ink:
        boundary = {
            (x + dx, y + dy)
            for x, y in grown
            for dx, dy in cross
            if 0 <= x + dx < WIDTH
            and STATUS_HEIGHT <= y + dy < HEIGHT
            and (x + dx, y + dy) not in grown
        }
        if not boundary:
            break
        needed = min(target_ink - len(grown), len(boundary))
        ranked: dict[tuple[int, int], tuple[int, int]] = {}
        for point in boundary:
            x, y = point
            cardinal_support = sum((x + dx, y + dy) in grown for dx, dy in cross)
            diagonal_support = sum((x + dx, y + dy) in grown for dx, dy in diagonal)
            ranked[point] = (cardinal_support, diagonal_support)
        chosen: list[tuple[int, int]] = []
        for score in sorted(set(ranked.values()), reverse=True):
            group = [point for point in boundary if ranked[point] == score]
            take = min(needed - len(chosen), len(group))
            chosen.extend(evenly_spaced(group, take, center))
            if len(chosen) == needed:
                break
        grown.update(chosen)
    return grown


def translate_component(
    component: set[tuple[int, int]],
    target: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    source_bounds = component_bounds(component)
    target_bounds = component_bounds(target)
    dx = round(target_bounds["center_x"] - source_bounds["center_x"])
    dy = round(target_bounds["center_y"] - source_bounds["center_y"])
    return {
        (x + dx, y + dy)
        for x, y in component
        if 0 <= x + dx < WIDTH and STATUS_HEIGHT <= y + dy < HEIGHT
    }


def thin_once(ink: set[tuple[int, int]]) -> set[tuple[int, int]]:
    result = set(ink)
    neighbour_offsets = (
        (0, -1),
        (1, -1),
        (1, 0),
        (1, 1),
        (0, 1),
        (-1, 1),
        (-1, 0),
        (-1, -1),
    )
    for first_pass in (True, False):
        remove: set[tuple[int, int]] = set()
        for x, y in result:
            neighbours = [
                (x + dx, y + dy) in result for dx, dy in neighbour_offsets
            ]
            count = sum(neighbours)
            transitions = sum(
                not neighbours[index] and neighbours[(index + 1) % 8]
                for index in range(8)
            )
            if not 2 <= count <= 6 or transitions != 1:
                continue
            north, east, south, west = (
                neighbours[0],
                neighbours[2],
                neighbours[4],
                neighbours[6],
            )
            if first_pass:
                protected = (
                    north and east and south
                ) or (
                    east and south and west
                )
            else:
                protected = (
                    north and east and west
                ) or (
                    north and south and west
                )
            if not protected:
                remove.add((x, y))
        result.difference_update(remove)
    return result


def current_style_candidate(
    source: Image.Image,
    legacy_face_components: list[set[tuple[int, int]]],
    family: str,
) -> tuple[Image.Image, dict]:
    native = source.convert("1")
    source_ink = {
        (x, y)
        for y in range(STATUS_HEIGHT, HEIGHT)
        for x in range(WIDTH)
        if native.getpixel((x, y)) == 0
    }
    source_components = components(source_ink)[:FACE_COMPONENT_LIMIT]
    current_roles = face_roles(source_components)
    legacy_roles = face_roles(legacy_face_components)
    styled_ink: set[tuple[int, int]] = set()
    component_rows = []
    role_caps = {
        "eyes": 1.45,
        "brows": 1.12,
        "cheeks": 1.12,
        "nose": 1.35,
        "mouth": 1.0,
    }
    for role in ("eyes", "brows", "cheeks", "nose", "mouth"):
        current = current_roles[role]
        legacy = legacy_roles[role]
        for index, component in enumerate(current):
            reference = legacy[min(index, len(legacy) - 1)] if legacy else component
            if family == "sleepy" and role == "eyes":
                target_ink = len(component)
            else:
                target_ink = min(
                    len(reference),
                    round(len(component) * role_caps[role]),
                )
                target_ink = max(len(component), target_ink)
            refined = grow_component(component, target_ink)
            styled_ink.update(refined)
            component_rows.append(
                {
                    "role": role,
                    "source_ink": len(component),
                    "legacy_reference_ink": len(reference),
                    "target_ink": target_ink,
                    "refined_ink_before_hole_restore": len(refined),
                    "growth_ratio": round(len(refined) / len(component), 4),
                }
            )
    protected_holes = enclosed_white_pixels(native)
    styled_ink.difference_update(protected_holes)
    result = Image.new("1", (WIDTH, HEIGHT), 1)
    result_pixels = result.load()
    for x, y in styled_ink:
        result_pixels[x, y] = 0
    return result, {
        "source_ink_pixels": len(source_ink),
        "styled_ink_pixels": len(styled_ink),
        "ink_ratio": round(len(styled_ink) / len(source_ink), 4),
        "protected_enclosed_white_pixels": len(protected_holes),
        "components": component_rows,
    }


def main() -> int:
    source = SOURCE.read_bytes()
    plan = json.loads(SOURCE_PLAN.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for family, frame_index in FAMILIES:
        frame = source[
            frame_index * FRAME_BYTES : (frame_index + 1) * FRAME_BYTES
        ]
        source_ink = decode_frame(frame)
        source_components = components(source_ink)
        face_components = source_components[:FACE_COMPONENT_LIMIT]
        face_ink = set().union(*face_components)
        output = OUTPUT / f"legacy-{family}-hold.png"
        write_png(output, face_ink)
        current_source = CURRENT_FACE_ROOT / f"{family}.png"
        styled, styled_metrics = current_style_candidate(
            Image.open(current_source), face_components, family
        )
        styled_output = OUTPUT / f"styled-{family}.png"
        styled.save(styled_output)
        refined_output = OUTPUT / f"refined-{family}.png"
        styled.save(refined_output)
        current_native = Image.open(current_source).convert("1")
        current_ink = {
            (x, y)
            for y in range(STATUS_HEIGHT, HEIGHT)
            for x in range(WIDTH)
            if current_native.getpixel((x, y)) == 0
        }
        polished_eye_metrics = []
        crafted_eye_metrics = []
        if family == "sleepy":
            polished_ink = current_ink
            crafted_ink = set(polished_ink)
        else:
            polished_ink = set(face_ink)
            crafted_ink = set(face_ink)
            legacy_eyes = face_roles(face_components)["eyes"]
            current_eyes = face_roles(
                components(current_ink)[:FACE_COMPONENT_LIMIT]
            )["eyes"]
            legacy_face_image = Image.open(output).convert("1")
            legacy_holes = enclosed_white_pixels(legacy_face_image)
            current_holes = enclosed_white_pixels(current_native)
            for legacy_eye, current_eye in zip(legacy_eyes, current_eyes):
                legacy_bounds = component_bounds(legacy_eye)
                current_bounds = component_bounds(current_eye)
                old_eye_holes = {
                    point
                    for point in legacy_holes
                    if legacy_bounds["left"] <= point[0] <= legacy_bounds["right"]
                    and legacy_bounds["top"] <= point[1] <= legacy_bounds["bottom"]
                }
                new_eye_holes = {
                    point
                    for point in current_holes
                    if current_bounds["left"] <= point[0] <= current_bounds["right"]
                    and current_bounds["top"] <= point[1] <= current_bounds["bottom"]
                }
                dx = round(
                    legacy_bounds["center_x"] - current_bounds["center_x"]
                )
                dy = round(
                    legacy_bounds["center_y"] - current_bounds["center_y"]
                )
                translated_holes = {
                    (x + dx, y + dy) for x, y in new_eye_holes
                }
                legacy_outer_shell = set(legacy_eye) | old_eye_holes
                safe_border = all(
                    all(
                        (x + ox, y + oy) in legacy_outer_shell
                        for ox, oy in (
                            (-1, -1), (0, -1), (1, -1),
                            (-1, 0), (0, 0), (1, 0),
                            (-1, 1), (0, 1), (1, 1),
                        )
                    )
                    for x, y in translated_holes
                )
                polished_ink.update(old_eye_holes)
                polished_ink.difference_update(translated_holes)
                crafted_shell = taper_terminal_caps(
                    rounded_superellipse(legacy_bounds, 2.0)
                )
                crafted_shell.update(
                    one_pixel_halo(translated_holes, legacy_bounds)
                )
                crafted_ink.difference_update(legacy_outer_shell)
                crafted_ink.update(crafted_shell)
                crafted_ink.difference_update(translated_holes)
                crafted_eye = crafted_shell - translated_holes
                crafted_eye_metrics.append(
                    {
                        "bounds": [
                            int(legacy_bounds["left"]),
                            int(legacy_bounds["top"]),
                            int(legacy_bounds["right"]),
                            int(legacy_bounds["bottom"]),
                        ],
                        "legacy_terminal_row_widths": terminal_row_widths(
                            legacy_outer_shell
                        ),
                        "crafted_terminal_row_widths": terminal_row_widths(
                            crafted_shell
                        ),
                        "legacy_terminal_column_heights":
                            terminal_column_heights(legacy_outer_shell),
                        "crafted_terminal_column_heights":
                            terminal_column_heights(crafted_shell),
                        "legacy_outer_shell_pixels": len(legacy_outer_shell),
                        "crafted_outer_shell_pixels": len(crafted_shell),
                        "ink_ratio": round(
                            len(crafted_shell) / len(legacy_outer_shell), 4
                        ),
                        "highlight_components": len(
                            components(translated_holes)
                        ),
                        "one_pixel_black_safe_border": one_pixel_halo(
                            translated_holes, legacy_bounds
                        ).issubset(crafted_shell),
                        "crafted_eye_components": len(
                            components(crafted_eye)
                        ),
                    }
                )
                polished_eye_metrics.append(
                    {
                        "outer_shell_pixels": len(legacy_outer_shell),
                        "legacy_highlight_pixels": len(old_eye_holes),
                        "current_highlight_pixels": len(new_eye_holes),
                        "translated_highlight_pixels": len(translated_holes),
                        "highlight_components": len(components(new_eye_holes)),
                        "one_pixel_black_safe_border": safe_border,
                        "center_offset": [dx, dy],
                    }
                )
        crafted_roles = face_roles(
            components(crafted_ink)[:FACE_COMPONENT_LIMIT]
        )
        crafted_role_metrics: dict[str, list[dict]] = {
            "nose": [],
            "cheeks": [],
        }
        for role, power in (("nose", 1.7), ("cheeks", 1.8)):
            for component in crafted_roles[role]:
                crafted_ink, role_metrics = replace_with_rounded_role(
                    crafted_ink, component, power
                )
                crafted_role_metrics[role].append(role_metrics)
        polished_output = OUTPUT / f"polished-{family}.png"
        write_png(polished_output, polished_ink)
        balance_offset = BALANCE_OFFSETS[family]
        balanced_ink = translate_ink(polished_ink, balance_offset)
        if len(balanced_ink) != len(polished_ink):
            raise RuntimeError(
                f"{family}: balance translation clipped face ink "
                f"{len(polished_ink)} -> {len(balanced_ink)}"
            )
        balanced_output = OUTPUT / f"balanced-polished-{family}.png"
        write_png(balanced_output, balanced_ink)
        crafted_balanced_ink = translate_ink(crafted_ink, balance_offset)
        if len(crafted_balanced_ink) != len(crafted_ink):
            raise RuntimeError(
                f"{family}: crafted balance translation clipped face ink "
                f"{len(crafted_ink)} -> {len(crafted_balanced_ink)}"
            )
        crafted_balanced_output = OUTPUT / f"crafted-balanced-{family}.png"
        write_png(crafted_balanced_output, crafted_balanced_ink)
        sculpted_balanced_output = (
            OUTPUT / f"sculpted-balanced-{family}.png"
        )
        write_png(sculpted_balanced_output, crafted_balanced_ink)
        finished_balanced_output = (
            OUTPUT / f"finished-balanced-{family}.png"
        )
        write_png(finished_balanced_output, crafted_balanced_ink)
        rows.append(
            {
                "family": family,
                "frame_index": frame_index,
                "frame_id": plan["entries"][frame_index]["id"],
                "frame_sha256": sha256(frame),
                "source_component_count": len(source_components),
                "kept_component_count": len(face_components),
                "source_ink_pixels": len(source_ink),
                "kept_face_ink_pixels": len(face_ink),
                "removed_baked_ornament_pixels": len(source_ink - face_ink),
                "png": str(output.relative_to(ROOT)).replace("\\", "/"),
                "png_sha256": sha256(output.read_bytes()),
                "current_rich_source": str(
                    current_source.relative_to(ROOT)
                ).replace("\\", "/"),
                "current_rich_source_sha256": sha256(
                    current_source.read_bytes()
                ),
                "styled_png": str(styled_output.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "styled_png_sha256": sha256(styled_output.read_bytes()),
                "refined_png": str(refined_output.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "refined_png_sha256": sha256(refined_output.read_bytes()),
                "polished_png": str(polished_output.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "polished_png_sha256": sha256(polished_output.read_bytes()),
                "polished_ink_pixels": len(polished_ink),
                "balance_offset": list(balance_offset),
                "balanced_polished_png": str(
                    balanced_output.relative_to(ROOT)
                ).replace("\\", "/"),
                "balanced_polished_png_sha256": sha256(
                    balanced_output.read_bytes()
                ),
                "polished_eye_metrics": polished_eye_metrics,
                "crafted_balanced_png": str(
                    crafted_balanced_output.relative_to(ROOT)
                ).replace("\\", "/"),
                "crafted_balanced_png_sha256": sha256(
                    crafted_balanced_output.read_bytes()
                ),
                "sculpted_balanced_png": str(
                    sculpted_balanced_output.relative_to(ROOT)
                ).replace("\\", "/"),
                "sculpted_balanced_png_sha256": sha256(
                    sculpted_balanced_output.read_bytes()
                ),
                "finished_balanced_png": str(
                    finished_balanced_output.relative_to(ROOT)
                ).replace("\\", "/"),
                "finished_balanced_png_sha256": sha256(
                    finished_balanced_output.read_bytes()
                ),
                "crafted_ink_pixels": len(crafted_ink),
                "crafted_eye_metrics": crafted_eye_metrics,
                "crafted_role_metrics": crafted_role_metrics,
                "styled_metrics": styled_metrics,
            }
        )
    ornament_rows = []
    ornament_output_root = OUTPUT / "ornaments"
    for source_path in sorted(CURRENT_ORNAMENT_ROOT.glob("*-stage-*.png")):
        source_image = Image.open(source_path).convert("RGBA")
        source_alpha = {
            (x, y)
            for y in range(HEIGHT)
            for x in range(WIDTH)
            if source_image.getpixel((x, y))[3] > 0
        }
        polished_alpha = thin_once(source_alpha)
        output_path = ornament_output_root / source_path.name
        write_alpha_png(output_path, polished_alpha)
        source_components = components(source_alpha)
        polished_components = components(polished_alpha)
        ornament_rows.append(
            {
                "source": str(source_path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": sha256(source_path.read_bytes()),
                "polished": str(output_path.relative_to(ROOT)).replace("\\", "/"),
                "polished_sha256": sha256(output_path.read_bytes()),
                "source_ink_pixels": len(source_alpha),
                "polished_ink_pixels": len(polished_alpha),
                "ink_ratio": round(
                    len(polished_alpha) / max(1, len(source_alpha)), 4
                ),
                "source_components": len(source_components),
                "polished_components": len(polished_components),
            }
        )
    manifest = {
        "schema": "companion.comp_req_772.legacy_line_style_faces.v4",
        "requirement": "COMP-REQ-772",
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(source),
        "width": WIDTH,
        "height": HEIGHT,
        "bits_per_pixel": 1,
        "status_bar_owned_by_browser": True,
        "current_mouths_owned_by_browser": True,
        "current_ornaments_owned_by_browser": True,
        "style_transfer": {
            "geometry_source": "current rich generated face",
            "reference": "accepted COMP-REQ-616 role-specific pixel weight",
            "method": (
                "role-aware bounded growth: open eye bodies reach the 616 mass, "
                "brows and cheeks grow at most 12%, nose at most 35%, authored "
                "mouths and sleepy closed eyes remain exact; enclosed highlights restored"
            ),
        },
        "crafted_hierarchy": {
            "method": (
                "keep the accepted face anchors and eye boxes; use a full ellipse "
                "body with explicit symmetric four-direction terminal caps, preserve "
                "both authored highlights with a one-pixel black halo, and redraw "
                "nose and cheek blobs as centered superellipses so eyes remain "
                "the primary focal mass"
            ),
            "eye_power": 2.0,
            "eye_terminal_row_limits": [5, 10],
            "eye_terminal_column_limits": [5, 13],
            "nose_power": 1.7,
            "cheek_power": 1.8,
            "mouths": "owned by the browser semantic mouth rig",
            "brows": "accepted COMP-REQ-616 emotion-specific silhouettes retained",
            "ornaments": "original COMP-REQ-727 assets retained by the browser",
        },
        "identity_balance": {
            "method": "rigid whole-face translation only",
            "awake_anchor": {
                "left_eye": [42, 93],
                "nose": [94, 129],
                "mouth": [87, 142],
            },
            "sleepy_method": (
                "whole sleepy face translated so the closed-eye visual center "
                "matches the awake open-eye visual center"
            ),
            "offsets": {
                family: list(offset)
                for family, offset in BALANCE_OFFSETS.items()
            },
        },
        "families": rows,
        "ornaments": ornament_rows,
    }
    (OUTPUT / "legacy-face-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
