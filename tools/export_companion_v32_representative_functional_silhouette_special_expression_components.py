#!/usr/bin/env python3
"""Export V32 representative functional-silhouette source pixels as inactive V9-identity rig components."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
V32_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v32-representative-functional-silhouette-special-expression-source"
SOURCE_GATE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-source-gate-20260720.json"
OUTPUT = V32_ROOT / "candidate/x"
V1_COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
CANVAS = (200, 200)
CHARGING_ROUTE_COMPONENTS = frozenset({
    "small_open_side_coupler",
    "thin_continuous_short_tether",
    "small_hollow_slotted_energy_dock",
})
CHARGING_COUPLER_SEED = (0, 117, 25, 143)


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

POSE_COMPONENTS = {
    "menu_active": [
        ("left_brow", "left_brow", (40, 78, 80, 100)),
        ("right_brow", "right_brow", (120, 78, 160, 100)),
        ("left_cheek", "left_cheek", (28, 155, 50, 171)),
        ("right_cheek", "right_cheek", (150, 155, 172, 171)),
        ("mouth", "mouth", (82, 159, 119, 176)),
        ("left_hollow_page_tab", "left_hollow_page_tab", (59, 48, 81, 71)),
        ("active_hollow_notched_page_tab", "active_hollow_notched_page_tab", (90, 41, 113, 73)),
        ("right_hollow_page_tab", "right_hollow_page_tab", (123, 49, 144, 72)),
    ],
    "recording_active": [
        ("left_brow", "left_brow", (40, 78, 80, 100)),
        ("right_brow", "right_brow", (120, 78, 160, 100)),
        ("left_cheek", "left_cheek", (28, 155, 50, 171)),
        ("right_cheek", "right_cheek", (150, 155, 172, 171)),
        ("mouth", "mouth", (82, 159, 119, 178)),
        ("left_thin_receiver_cuff", "left_thin_receiver_cuff", (0, 108, 24, 153)),
        ("right_thin_receiver_cuff", "right_thin_receiver_cuff", (172, 108, 196, 153)),
        ("single_pickup_dot", "single_pickup_dot", (124, 163, 133, 173)),
    ],
    "charging_active": [
        ("left_brow", "left_brow", (40, 78, 80, 101)),
        ("right_brow", "right_brow", (120, 78, 160, 101)),
        ("left_cheek", "left_cheek", (34, 155, 50, 171)),
        ("right_cheek", "right_cheek", (150, 155, 172, 171)),
        ("mouth", "mouth", (82, 159, 119, 176)),
        ("small_open_side_coupler", "small_open_side_coupler", (0, 115, 25, 143)),
        ("thin_continuous_short_tether", "thin_continuous_short_tether", (0, 39, 81, 115)),
        ("small_hollow_slotted_energy_dock", "small_hollow_slotted_energy_dock", (81, 39, 125, 62)),
    ],
}

ROLE_STYLE = {
    "left_brow": (20, [-1, -2], [1, 1]),
    "right_brow": (20, [-1, -2], [1, 1]),
    "left_cheek": (40, [0, -1], [0, 1]),
    "right_cheek": (40, [0, -1], [0, 1]),
    "mouth": (60, [0, -1], [0, 1]),
    "left_hollow_page_tab": (10, [-1, -1], [1, 1]),
    "active_hollow_notched_page_tab": (11, [-1, -1], [1, 1]),
    "right_hollow_page_tab": (10, [-1, -1], [1, 1]),
    "left_thin_receiver_cuff": (42, [0, -1], [1, 0]),
    "right_thin_receiver_cuff": (42, [0, -1], [1, 0]),
    "single_pickup_dot": (55, [0, -1], [0, 1]),
    "small_open_side_coupler": (42, [-1, 0], [1, 0]),
    "thin_continuous_short_tether": (41, [-1, -1], [1, 1]),
    "small_hollow_slotted_energy_dock": (12, [0, -1], [0, 1]),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, object]:
    result = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(result, dict), f"{rel(path)} is not a JSON object")
    return result


def ink_count(image: Image.Image) -> int:
    return sum(value == 0 for value in image.convert("L").getdata())


def save_mask(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path)


def connected_ink_mask(image: Image.Image, seed_box: tuple[int, int, int, int]) -> Image.Image:
    """Return only the connected source route that starts at the charging coupler."""
    source = image.convert("L")
    seed: tuple[int, int] | None = None
    for y in range(seed_box[1], seed_box[3]):
        for x in range(seed_box[0], seed_box[2]):
            if source.getpixel((x, y)) == 0:
                seed = (x, y)
                break
        if seed is not None:
            break
    require(seed is not None, "charging coupler seed region has no source ink")
    visited = {seed}
    pending = [seed]
    while pending:
        x, y = pending.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < CANVAS[0] and 0 <= ny < CANVAS[1]):
                    continue
                point = (nx, ny)
                if point in visited or source.getpixel(point) != 0:
                    continue
                visited.add(point)
                pending.append(point)
    route = Image.new("L", CANVAS, 255)
    for point in visited:
        route.putpixel(point, 0)
    return route


def identity_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for component in IDENTITY:
        path = V1_COMPONENTS / f"{component.name}.pbm"
        require(path.is_file(), f"locked V9 identity component is missing: {path}")
        with Image.open(path) as raw:
            image = raw.convert("L")
        records.append({
            "name": component.name,
            "role": component.role,
            "source": "locked_v9_rig_v1_component",
            "group": "locked_v9_identity",
            "mask": rel(path),
            "mask_sha256": sha256(path),
            "base_position": list(component.position),
            "anchor": [image.width // 2, image.height // 2],
            "offset_range": {"min": [0, 0], "max": [0, 0]},
            "z_index": component.z_index,
            "composite_op": component.composite_op,
            "image": image,
        })
    return records


def export_source_component(pose: str, source_image: Image.Image, name: str, role: str,
                            box: tuple[int, int, int, int], source_kind: str) -> dict[str, object]:
    x, y, right, bottom = box
    crop = source_image.crop(box).convert("L")
    require(ink_count(crop) >= 8, f"{pose} {name} has too little source ink")
    z_index, lower, upper = ROLE_STYLE[role]
    mask_path = OUTPUT / "m" / f"{pose}-{name}.pbm"
    preview_path = OUTPUT / "p" / f"{pose}-{name}.png"
    save_mask(crop, mask_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.resize((crop.width * 6, crop.height * 6), Image.Resampling.NEAREST).save(preview_path)
    return {
        "name": f"v32_{pose}__{name}",
        "pose": pose,
        "role": role,
        "source": source_kind,
        "source_component_box": list(box),
        "mask": rel(mask_path),
        "mask_sha256": sha256(mask_path),
        "preview_layer": rel(preview_path),
        "base_position": [x, y],
        "anchor": [crop.width // 2, crop.height // 2],
        "offset_range": {"min": lower, "max": upper},
        "z_index": z_index,
        "composite_op": "ink",
        "ink_pixels": ink_count(crop),
        "image": crop,
    }


def compose(records: Iterable[dict[str, object]]) -> Image.Image:
    canvas = Image.new("L", CANVAS, 255)
    for record in sorted(records, key=lambda item: int(item["z_index"])):
        image = record["image"].convert("L")
        alpha = ImageOps.invert(image)
        ink = 255 if record["composite_op"] == "erase" else 0
        canvas.paste(ink, tuple(record["base_position"]), alpha)
    return canvas.convert("1")


def overlap_audit(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    coverage = [[0 for _ in range(CANVAS[0])] for _ in range(CANVAS[1])]
    collisions: list[dict[str, object]] = []
    for record in sorted(records, key=lambda item: int(item["z_index"])):
        if record["composite_op"] != "ink":
            continue
        image = record["image"].convert("L")
        x0, y0 = record["base_position"]
        collision_count = 0
        for y in range(image.height):
            for x in range(image.width):
                if image.getpixel((x, y)) != 0:
                    continue
                target_x, target_y = x0 + x, y0 + y
                if not (0 <= target_x < CANVAS[0] and 0 <= target_y < CANVAS[1]) or coverage[target_y][target_x]:
                    collision_count += 1
                    continue
                coverage[target_y][target_x] += 1
        if collision_count:
            collisions.append({"component": record["name"], "collision_pixels": collision_count})
    return collisions


def public(record: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in record.items() if key != "image"}


def main() -> int:
    source_gate = load_json(SOURCE_GATE)
    require(source_gate.get("status") == "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_SOURCE_GATE_PENDING_COMPONENT_EXPORT", "V32 source gate is not PASS")
    require(source_gate.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "V32 source gate lost locked V9 identity")
    require(source_gate.get("runtime_resource_activated") is False, "V32 source gate unexpectedly activated runtime")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    identity = identity_records()
    pose_records: dict[str, list[dict[str, object]]] = {}
    state_meta: dict[str, dict[str, object]] = {}
    reassemblies: dict[str, Image.Image] = {}
    for pose, definitions in POSE_COMPONENTS.items():
        normalized_path = V32_ROOT / "candidate/review-v3" / f"{pose}.png"
        require(normalized_path.is_file(), f"V32 normalized source preview is missing: {normalized_path}")
        with Image.open(normalized_path) as raw:
            normalized = raw.convert("L")
        charging_route = connected_ink_mask(normalized, CHARGING_COUPLER_SEED) if pose == "charging_active" else None
        special = [
            export_source_component(
                pose,
                charging_route if name in CHARGING_ROUTE_COMPONENTS else normalized,
                name,
                role,
                box,
                "v32_generated_source_connected_route" if name in CHARGING_ROUTE_COMPONENTS else "v32_generated_source_thresholded_normalization",
            )
            for name, role, box in definitions
        ]
        overlaps = overlap_audit([*identity, *special])
        require(not overlaps, f"{pose} component masks overlap: {overlaps}")
        reassembly = compose([*identity, *special])
        reassembly_path = OUTPUT / "r" / f"{pose}.pbm"
        preview_path = OUTPUT / "r" / f"{pose}.png"
        save_mask(reassembly, reassembly_path)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        reassembly.resize((800, 800), Image.Resampling.NEAREST).save(preview_path)
        pose_records[pose] = special
        state_meta[pose] = {
            "normalized_source": rel(normalized_path),
            "components": [record["name"] for record in special],
            "component_count": len(special),
            "reassembly": rel(reassembly_path),
            "reassembly_sha256": sha256(reassembly_path),
            "reassembly_preview": rel(preview_path),
            "component_overlap_audit": overlaps,
        }
        reassemblies[pose] = reassembly

    contact = Image.new("L", (600, 200), 255)
    for index, pose in enumerate(POSE_COMPONENTS):
        contact.paste(reassemblies[pose].convert("L"), (index * 200, 0))
    contact_path = OUTPUT / "c.png"
    contact.resize((1200, 400), Image.Resampling.NEAREST).save(contact_path)

    layout = {
        "schema": "companion.v32_representative_functional_silhouette_special_expression_component_layout.v1",
        "status": "UNBOUND_CANDIDATE_PENDING_COMPONENT_PERFORMANCE_AND_OWNER_ART_REVIEW",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "source_gate": rel(SOURCE_GATE),
        "identity_components": {record["name"]: public(record) for record in identity},
        "special_pose_components": {pose: {record["name"]: public(record) for record in records} for pose, records in pose_records.items()},
        "states": state_meta,
        "component_contact_sheet": rel(contact_path),
        "source_pixel_rule": "special brow, mouth and cheek masks are thresholded crops from the V32 generated source; eyes, highlights, sparkles and nose are exact locked V9 rig masks; no full source pose is a runtime asset",
        "prohibited_before_owner_art_review": ["whole-source-panel playback", "whole-face replacement", "CRIG export", "profile generation", "event binding", "firmware flash", "panel output"],
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    layout_path = OUTPUT / "l.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="ascii")
    report = {
        "schema": "companion.v32_representative_functional_silhouette_special_expression_component_export.v1",
        "status": "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_SOURCE_COMPONENT_EXPORT_UNBOUND",
        "source_gate": rel(SOURCE_GATE),
        "layout": rel(layout_path),
        "component_contact_sheet": rel(contact_path),
        "identity_component_count": len(identity),
        "special_component_counts": {pose: len(records) for pose, records in pose_records.items()},
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    report_path = OUTPUT / "e.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print("PASS: V32 representative functional silhouettes exported as unbound V9-identity component masks.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
