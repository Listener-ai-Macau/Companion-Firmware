#!/usr/bin/env python3
"""Extract V22 emotion components without making full-pose runtime assets."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
V22_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source"
ATTEMPT = V22_ROOT / "candidate/attempt-01-generated-emotion-separation.json"
SOURCE_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-source-gate-20260719.json"
OUTPUT = V22_ROOT / "candidate/component-export-attempt-03"
V1_COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EMOTIONS = ("calm", "curious", "warm", "playful", "puzzled", "alert")
CANVAS = (200, 200)
INK_THRESHOLD = 96


@dataclass(frozen=True)
class IdentityComponent:
    name: str
    role: str
    position: tuple[int, int]
    z_index: int
    composite_op: str


IDENTITY = (
    IdentityComponent("left_eye_open", "left_eye", (42, 112), 30, "ink"),
    IdentityComponent("right_eye_open", "right_eye", (125, 112), 30, "ink"),
    IdentityComponent("left_eye_highlight_open", "left_highlight", (42, 112), 31, "erase"),
    IdentityComponent("right_eye_highlight_open", "right_highlight", (125, 112), 31, "erase"),
    IdentityComponent("left_eye_sparkle_open", "left_sparkle", (42, 112), 32, "erase"),
    IdentityComponent("right_eye_sparkle_open", "right_sparkle", (125, 112), 32, "erase"),
    IdentityComponent("nose_default", "nose", (94, 148), 50, "ink"),
)
TARGET_EYE_CENTERS = ((58.5, 134.5), (142.0, 134.5))
ROLE_STYLES = {
    "left_brow": (20, [-1, -3], [1, 1]),
    "right_brow": (20, [-1, -3], [1, 1]),
    "left_cheek": (40, [0, -1], [0, 1]),
    "right_cheek": (40, [0, -1], [0, 1]),
    "mouth": (60, [0, -1], [0, 1]),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def cell_box(index: int, width: int, height: int) -> tuple[int, int, int, int]:
    column = index % 3
    row = index // 3
    return column * width // 3, row * height // 2, (column + 1) * width // 3, (row + 1) * height // 2


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < INK_THRESHOLD else 255, mode="L")


def connected_components(image: Image.Image) -> list[dict[str, object]]:
    pixels = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, object]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] != 0:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                points.append((current_x, current_y))
                for near_x, near_y in ((current_x - 1, current_y), (current_x + 1, current_y),
                                       (current_x, current_y - 1), (current_x, current_y + 1)):
                    if 0 <= near_x < width and 0 <= near_y < height and (near_x, near_y) not in seen and \
                            pixels[near_x, near_y] == 0:
                        seen.add((near_x, near_y))
                        queue.append((near_x, near_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            result.append({
                "area": len(points),
                "bbox": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                "center": (sum(xs) / len(xs), sum(ys) / len(ys)),
            })
    return sorted(result, key=lambda component: int(component["area"]), reverse=True)


def source_to_target(cell: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    source = binary(cell)
    components = connected_components(source)
    require(len(components) >= 2, "source cell has too few ink components")
    eyes = sorted(components[:2], key=lambda component: float(component["center"][0]))
    left_eye, right_eye = eyes
    left_center = left_eye["center"]
    right_center = right_eye["center"]
    eye_gap = float(right_center[0]) - float(left_center[0])
    left_box = left_eye["bbox"]
    right_box = right_eye["bbox"]
    average_eye_height = ((int(left_box[3]) - int(left_box[1])) + (int(right_box[3]) - int(right_box[1]))) / 2
    require(eye_gap > 40 and average_eye_height > 30, "source cell did not yield a valid eye pair")
    scale_x = (TARGET_EYE_CENTERS[1][0] - TARGET_EYE_CENTERS[0][0]) / eye_gap
    scale_y = 45.0 / average_eye_height
    inverse = (
        1.0 / scale_x,
        0.0,
        float(left_center[0]) - TARGET_EYE_CENTERS[0][0] / scale_x,
        0.0,
        1.0 / scale_y,
        float(left_center[1]) - TARGET_EYE_CENTERS[0][1] / scale_y,
    )
    mapped = source.transform(CANVAS, Image.Transform.AFFINE, inverse, Image.Resampling.NEAREST, fillcolor=255)
    return mapped, {
        "source_left_eye_bbox": list(left_box),
        "source_right_eye_bbox": list(right_box),
        "source_left_eye_center": [round(float(left_center[0]), 3), round(float(left_center[1]), 3)],
        "source_right_eye_center": [round(float(right_center[0]), 3), round(float(right_center[1]), 3)],
        "scale": [round(scale_x, 6), round(scale_y, 6)],
    }


def ink_count(mask: Image.Image) -> int:
    return sum(value == 0 for value in mask.convert("L").getdata())


def save_mask(mask: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mask.convert("1").save(path)


def padded_box(box: tuple[int, int, int, int], padding: int = 1) -> tuple[int, int, int, int]:
    return max(0, box[0] - padding), max(0, box[1] - padding), \
        min(CANVAS[0], box[2] + padding), min(CANVAS[1], box[3] + padding)


def source_component(mask: Image.Image, role: str, emotion: str, source_meta: dict[str, object],
                     ink_box: tuple[int, int, int, int]) -> dict[str, object]:
    x, y, right, bottom = padded_box(ink_box)
    width, height = right - x, bottom - y
    z_index, minimum, maximum = ROLE_STYLES[role]
    crop = mask.crop((x, y, right, bottom))
    require(ink_count(crop) >= 8, f"{emotion} {role} crop has too little source ink")
    mask_path = OUTPUT / "component-masks" / f"{emotion}-{role}.pbm"
    preview_path = OUTPUT / "preview-layers" / f"{emotion}-{role}.png"
    save_mask(crop, mask_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.resize((width * 8, height * 8), Image.Resampling.NEAREST).convert("L").save(preview_path)
    return {
        "name": f"v22_{emotion}__{role}",
        "emotion": emotion,
        "role": role,
        "source": "v22_generated_source_panel_thresholded_crop",
        "source_transform": source_meta,
        "source_grid_component": {"role": role, "normalized_ink_box": list(ink_box)},
        "mask": rel(mask_path),
        "mask_sha256": sha256(mask_path),
        "preview_layer": rel(preview_path),
        "base_position": [x, y],
        "anchor": [width // 2, height // 2],
        "offset_range": {"min": minimum, "max": maximum},
        "z_index": z_index,
        "composite_op": "ink",
        "ink_pixels": ink_count(crop),
        "image": crop,
    }


def playful_accent(mask: Image.Image, source_meta: dict[str, object], ink_box: tuple[int, int, int, int]) -> dict[str, object]:
    left, top, right, bottom = padded_box(ink_box)
    crop = mask.crop((left, top, right, bottom))
    require(ink_count(crop) >= 20, "playful accent crop has too little source ink")
    mask_path = OUTPUT / "component-masks" / "playful-accent.pbm"
    preview_path = OUTPUT / "preview-layers" / "playful-accent.png"
    save_mask(crop, mask_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.resize((crop.width * 8, crop.height * 8), Image.Resampling.NEAREST).convert("L").save(preview_path)
    return {
        "name": "v22_playful__accent",
        "emotion": "playful",
        "role": "accent",
        "source": "v22_generated_source_panel_thresholded_crop",
        "source_transform": source_meta,
        "source_grid_component": {"role": "playful_integrated_sparkle", "normalized_ink_box": list(ink_box)},
        "mask": rel(mask_path),
        "mask_sha256": sha256(mask_path),
        "preview_layer": rel(preview_path),
        "base_position": [left, top],
        "anchor": [crop.width // 2, crop.height // 2],
        "offset_range": {"min": [0, -2], "max": [2, 1]},
        "z_index": 10,
        "composite_op": "ink",
        "ink_pixels": ink_count(crop),
        "image": crop,
    }


def choose_component(components: list[dict[str, object]], label: str,
                     predicate: Callable[[dict[str, object]], bool],
                     target: tuple[float, float]) -> tuple[int, int, int, int]:
    candidates = [component for component in components if predicate(component)]
    require(candidates, f"source has no candidate for {label}")
    selected = min(candidates, key=lambda component:
                   abs(float(component["center"][0]) - target[0]) + abs(float(component["center"][1]) - target[1]))
    return tuple(int(value) for value in selected["bbox"])


def choose_optional_component(components: list[dict[str, object]],
                              predicate: Callable[[dict[str, object]], bool],
                              target: tuple[float, float]) -> tuple[int, int, int, int] | None:
    candidates = [component for component in components if predicate(component)]
    if not candidates:
        return None
    selected = min(candidates, key=lambda component:
                   abs(float(component["center"][0]) - target[0]) + abs(float(component["center"][1]) - target[1]))
    return tuple(int(value) for value in selected["bbox"])


def locate_expression_components(mask: Image.Image, emotion: str) -> tuple[dict[str, tuple[int, int, int, int] | None],
                                                                             tuple[int, int, int, int] | None]:
    components = connected_components(mask)
    require(len(components) >= 7, f"{emotion} normalized source has too few disconnected features")
    def bbox(component: dict[str, object]) -> tuple[int, int, int, int]:
        return tuple(int(value) for value in component["bbox"])
    def width(component: dict[str, object]) -> int:
        box = bbox(component)
        return box[2] - box[0]
    def height(component: dict[str, object]) -> int:
        box = bbox(component)
        return box[3] - box[1]
    def center(component: dict[str, object]) -> tuple[float, float]:
        return float(component["center"][0]), float(component["center"][1])
    small = [component for component in components if int(component["area"]) >= 8 and height(component) <= 26]
    locations = {
        "left_brow": choose_component(small, f"{emotion} left brow",
            lambda component: 28 <= center(component)[0] <= 102 and 55 <= center(component)[1] <= 118 and
            width(component) >= 10, (58.0, 90.0)),
        "right_brow": choose_component(small, f"{emotion} right brow",
            lambda component: 98 <= center(component)[0] <= 178 and 55 <= center(component)[1] <= 125 and
            width(component) >= 10, (143.0, 90.0)),
        "left_cheek": choose_component(small, f"{emotion} left cheek",
            lambda component: center(component)[0] <= 78 and center(component)[1] >= 154, (40.0, 165.0)),
        "right_cheek": choose_optional_component(small,
            lambda component: center(component)[0] >= 120 and center(component)[1] >= 154, (160.0, 165.0)),
        "mouth": choose_component(small, f"{emotion} mouth",
            lambda component: 75 <= center(component)[0] <= 125 and center(component)[1] >= 154, (101.0, 166.0)),
    }
    accent = None
    if emotion == "playful":
        accent = choose_component(small, "playful accent",
            lambda component: 160 <= center(component)[0] <= 185 and 135 <= center(component)[1] <= 160 and
            width(component) >= 6, (169.0, 154.0))
    return locations, accent


def identity_records() -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for component in IDENTITY:
        path = V1_COMPONENTS / f"{component.name}.pbm"
        require(path.is_file(), f"locked V9 identity component is missing: {path}")
        with Image.open(path) as image:
            mask = image.convert("L")
        records.append({
            "name": component.name,
            "role": component.role,
            "source": "locked_v9_rig_v1_component",
            "group": "locked_v9_identity",
            "mask": rel(path),
            "mask_sha256": sha256(path),
            "base_position": list(component.position),
            "z_index": component.z_index,
            "composite_op": component.composite_op,
            "image": mask,
        })
    return tuple(records)


def paste_component(canvas: Image.Image, record: dict[str, object]) -> None:
    mask = record["image"].convert("L")
    alpha = ImageOps.invert(mask)
    color = 0 if record["composite_op"] == "ink" else 255
    canvas.paste(color, tuple(record["base_position"]), alpha)


def compose(identity: Iterable[dict[str, object]], special: Iterable[dict[str, object]]) -> Image.Image:
    canvas = Image.new("L", CANVAS, 255)
    for record in sorted(identity, key=lambda item: int(item["z_index"])):
        paste_component(canvas, record)
    for record in sorted(special, key=lambda item: int(item["z_index"])):
        paste_component(canvas, record)
    return canvas.convert("1")


def pixel_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.convert("1").getdata(), right.convert("1").getdata()))


def main() -> int:
    source_gate = load_json(SOURCE_GATE)
    require(source_gate.get("status") == "PASS_V22_EMOTION_SEPARATION_SOURCE_GATE_PENDING_COMPONENT_EXPORT",
            "V22 source gate is not PASS")
    attempt = load_json(ATTEMPT)
    generated = ROOT / str(attempt["generated_image"])
    require(generated.is_file() and sha256(generated) == attempt["generated_image_sha256"],
            "V22 source image is missing or hash drifted")
    require(attempt.get("source_reference_sha256") == LOCKED_V9_SHA256, "V22 lost V9 source lineage")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with Image.open(generated) as raw:
        source = raw.convert("L")
    identity = identity_records()
    state_records: dict[str, list[dict[str, object]]] = {}
    state_meta: dict[str, object] = {}
    renderings: dict[str, Image.Image] = {}
    for index, emotion in enumerate(EMOTIONS):
        cell = source.crop(cell_box(index, *source.size))
        mapped, transform_meta = source_to_target(cell)
        mapped_path = OUTPUT / "normalized-source" / f"{emotion}.png"
        mapped_path.parent.mkdir(parents=True, exist_ok=True)
        mapped.resize((800, 800), Image.Resampling.NEAREST).save(mapped_path)
        locations, accent_box = locate_expression_components(mapped, emotion)
        special = [
            source_component(mapped, role, emotion, transform_meta, locations[role])
            for role in ROLE_STYLES if locations[role] is not None
        ]
        if emotion == "playful":
            require(accent_box is not None, "playful source has no integrated source accent")
            special.append(playful_accent(mapped, transform_meta, accent_box))
        state_records[emotion] = special
        state_meta[emotion] = {
            "source_grid_box": list(cell_box(index, *source.size)),
            "normalized_source_preview": rel(mapped_path),
            "components": [record["name"] for record in special],
            "source_absent_roles": [role for role, ink_box in locations.items() if ink_box is None],
        }
        reassembly = compose(identity, special)
        reassembly_path = OUTPUT / "reassembled-200x200" / f"{emotion}.pbm"
        preview_path = OUTPUT / "reassembled-800" / f"{emotion}.png"
        save_mask(reassembly, reassembly_path)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        reassembly.resize((800, 800), Image.Resampling.NEAREST).convert("L").save(preview_path)
        state_meta[emotion]["reassembly"] = rel(reassembly_path)
        state_meta[emotion]["reassembly_sha256"] = sha256(reassembly_path)
        state_meta[emotion]["reassembly_preview"] = rel(preview_path)
        renderings[emotion] = reassembly

    contact = Image.new("L", (600, 400), 255)
    for index, emotion in enumerate(EMOTIONS):
        contact.paste(renderings[emotion], ((index % 3) * 200, (index // 3) * 200))
    contact_path = OUTPUT / "v22-emotion-separation-component-reassembly-contact-sheet.png"
    contact.resize((1200, 800), Image.Resampling.NEAREST).save(contact_path)

    distances = []
    for left, right in combinations(EMOTIONS, 2):
        distances.append({"left": left, "right": right, "pixels": pixel_distance(renderings[left], renderings[right])})
    coverage = [[0 for _ in range(CANVAS[0])] for _ in range(CANVAS[1])]
    overlaps: list[dict[str, object]] = []
    for emotion in EMOTIONS:
        for record in [*identity, *state_records[emotion]]:
            if record["composite_op"] != "ink":
                continue
            mask = record["image"].convert("L")
            x0, y0 = record["base_position"]
            collision = 0
            for y in range(mask.height):
                for x in range(mask.width):
                    if mask.getpixel((x, y)) != 0:
                        continue
                    target_x, target_y = x0 + x, y0 + y
                    if coverage[target_y][target_x]:
                        collision += 1
                    coverage[target_y][target_x] += 1
            if collision:
                overlaps.append({"emotion": emotion, "component": record["name"], "collision_pixels": collision})
        for row in coverage:
            row[:] = [0] * CANVAS[0]

    def public(record: dict[str, object]) -> dict[str, object]:
        return {key: value for key, value in record.items() if key != "image"}

    layout = {
        "schema": "companion.v22_emotion_separation_component_source_layout.v1",
        "status": "UNBOUND_CANDIDATE_PENDING_OWNER_ART_REVIEW_AND_COMPONENT_BRIDGE_GATE",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "generated_source": attempt["generated_image"],
        "generated_source_sha256": attempt["generated_image_sha256"],
        "identity_components": {record["name"]: public(record) for record in identity},
        "emotion_components": {
            emotion: {record["name"]: public(record) for record in state_records[emotion]}
            for emotion in EMOTIONS
        },
        "states": state_meta,
        "component_contact_sheet": rel(contact_path),
        "prohibited_before_component_bridge_gate": [
            "whole-source-pose playback", "whole-face replacement", "CRIG export", "runtime activation",
            "menu recording upgrade binding", "sleep charging error fallback",
        ],
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    layout_path = OUTPUT / "everyday-emotion-component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    audit = {
        "schema": "companion.v22_emotion_separation_component_occlusion_audit.v1",
        "status": "PASS_ZERO_COMPONENT_OVERLAP" if not overlaps else "FAIL_COMPONENT_OVERLAP",
        "overlaps": overlaps,
        "pairwise_reassembly_distances": distances,
        "source_pixels_only": True,
        "runtime_resource_activated": False,
    }
    audit_path = OUTPUT / "component-occlusion-audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="ascii")
    report = {
        "schema": "companion.v22_emotion_separation_component_export.v1",
        "status": "PASS_V22_EMOTION_SEPARATION_SOURCE_MASK_EXPORT_UNBOUND" if not overlaps else
                  "FAIL_V22_EMOTION_SEPARATION_SOURCE_MASK_EXPORT",
        "layout": rel(layout_path),
        "occlusion_audit": rel(audit_path),
        "component_contact_sheet": rel(contact_path),
        "emotion_count": len(EMOTIONS),
        "identity_component_count": len(identity),
        "emotion_component_counts": {emotion: len(records) for emotion, records in state_records.items()},
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    (OUTPUT / "export-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if overlaps:
        raise ValueError("V22 source extraction produced overlapping components")
    print("PASS: V22 source poses exported as locked-identity component masks and unbound reassemblies.")


if __name__ == "__main__":
    raise SystemExit(main())
