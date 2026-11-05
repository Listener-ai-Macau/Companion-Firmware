#!/usr/bin/env python3
"""Export V24 glance-readable source pixels as unbound V9-identity rig components."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
V24_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v24-glance-readable-special-expression-source"
SOURCE_GATE = ROOT / "docs/validation/companion-v24-glance-readable-special-expression-source-gate-20260720.json"
OUTPUT = V24_ROOT / "candidate/component-export-attempt-01"
V1_COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
CANVAS = (200, 200)


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

ROLE_STYLE = {
    "left_brow": (20, [-1, -3], [1, 1]),
    "right_brow": (20, [-1, -3], [1, 1]),
    "left_cheek": (40, [0, -1], [0, 1]),
    "right_cheek": (40, [0, -1], [0, 1]),
    "mouth": (60, [0, -1], [0, 1]),
    "accent": (10, [0, -2], [0, 2]),
    "left_listening_arc": (35, [-1, -1], [0, 1]),
    "right_listening_arc": (35, [0, -1], [1, 1]),
}

POSE_COMPONENTS = {
    "menu_active": [
        ("left_brow", "left_brow", (47, 88, 73, 101)),
        ("right_brow", "right_brow", (128, 88, 153, 101)),
        ("left_cheek", "left_cheek", (31, 157, 46, 166)),
        ("right_cheek", "right_cheek", (154, 157, 169, 166)),
        ("mouth", "mouth", (85, 160, 115, 169)),
        ("selection_dot_left", "accent", (74, 62, 82, 70)),
        ("selection_dot_center", "accent", (96, 62, 103, 70)),
        ("selection_dot_right", "accent", (117, 62, 125, 70)),
    ],
    "recording_active": [
        ("left_brow", "left_brow", (47, 84, 69, 97)),
        ("right_brow", "right_brow", (132, 84, 155, 97)),
        ("left_cheek", "left_cheek", (32, 157, 48, 165)),
        ("right_cheek", "right_cheek", (152, 157, 167, 166)),
        ("mouth", "mouth", (89, 158, 109, 175)),
        ("left_listening_outer", "left_listening_arc", (0, 115, 11, 151)),
        ("left_listening_inner", "left_listening_arc", (12, 122, 20, 144)),
        ("right_listening_inner", "right_listening_arc", (181, 122, 189, 144)),
        ("right_listening_outer", "right_listening_arc", (190, 115, 200, 150)),
    ],
    "charging_active": [
        ("left_brow", "left_brow", (46, 89, 69, 99)),
        ("right_brow", "right_brow", (130, 89, 153, 99)),
        ("left_cheek", "left_cheek", (32, 153, 45, 162)),
        ("right_cheek", "right_cheek", (155, 153, 168, 162)),
        ("mouth", "mouth", (85, 158, 114, 171)),
        ("breathing_arc_left", "accent", (64, 40, 87, 49)),
        ("breathing_arc_right", "accent", (115, 40, 138, 49)),
    ],
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


def ink_count(image: Image.Image) -> int:
    return sum(value == 0 for value in image.convert("L").getdata())


def save_mask(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path)


def identity_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for component in IDENTITY:
        path = V1_COMPONENTS / f"{component.name}.pbm"
        require(path.is_file(), f"locked V9 identity component is missing: {path}")
        with Image.open(path) as raw:
            image = raw.convert("L")
        records.append(
            {
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
            }
        )
    return records


def export_source_component(pose: str, normalized: Image.Image, component_name: str, role: str,
                            box: tuple[int, int, int, int]) -> dict[str, object]:
    x, y, right, bottom = box
    crop = normalized.crop(box).convert("L")
    require(ink_count(crop) >= 8, f"{pose} {component_name} has too little source ink")
    style_role = role
    if role == "left_listening_arc" or role == "right_listening_arc":
        style_role = role
    z_index, minimum, maximum = ROLE_STYLE[style_role]
    mask_path = OUTPUT / "component-masks" / f"{pose}-{component_name}.pbm"
    preview_path = OUTPUT / "preview-layers" / f"{pose}-{component_name}.png"
    save_mask(crop, mask_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.resize((crop.width * 8, crop.height * 8), Image.Resampling.NEAREST).save(preview_path)
    return {
        "name": f"v24_{pose}__{component_name}",
        "pose": pose,
        "role": role,
        "source": "v24_generated_source_thresholded_normalization",
        "source_component_box": list(box),
        "mask": rel(mask_path),
        "mask_sha256": sha256(mask_path),
        "preview_layer": rel(preview_path),
        "base_position": [x, y],
        "anchor": [crop.width // 2, crop.height // 2],
        "offset_range": {"min": minimum, "max": maximum},
        "z_index": z_index,
        "composite_op": "ink",
        "ink_pixels": ink_count(crop),
        "image": crop,
    }


def paste_component(canvas: Image.Image, record: dict[str, object]) -> None:
    image = record["image"].convert("L")
    alpha = ImageOps.invert(image)
    ink = 0 if record["composite_op"] == "ink" else 255
    canvas.paste(ink, tuple(record["base_position"]), alpha)


def compose(identity: Iterable[dict[str, object]], special: Iterable[dict[str, object]]) -> Image.Image:
    canvas = Image.new("L", CANVAS, 255)
    for record in sorted([*identity, *special], key=lambda item: int(item["z_index"])):
        paste_component(canvas, record)
    return canvas.convert("1")


def component_overlaps(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    coverage = [[0 for _ in range(CANVAS[0])] for _ in range(CANVAS[1])]
    overlaps: list[dict[str, object]] = []
    for record in sorted(records, key=lambda item: int(item["z_index"])):
        if record["composite_op"] != "ink":
            continue
        image = record["image"].convert("L")
        x0, y0 = record["base_position"]
        collision = 0
        for y in range(image.height):
            for x in range(image.width):
                if image.getpixel((x, y)) != 0:
                    continue
                target_x, target_y = x0 + x, y0 + y
                if not (0 <= target_x < CANVAS[0] and 0 <= target_y < CANVAS[1]):
                    collision += 1
                    continue
                if coverage[target_y][target_x]:
                    collision += 1
                coverage[target_y][target_x] += 1
        if collision:
            overlaps.append({"component": record["name"], "collision_pixels": collision})
    return overlaps


def public(record: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in record.items() if key != "image"}


def main() -> int:
    source_gate = load_json(SOURCE_GATE)
    require(source_gate.get("status") == "PASS_V24_SPECIAL_SOURCE_GATE_PENDING_COMPONENT_EXPORT", "V24 source gate is not PASS")
    require(source_gate.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "V24 source gate lost V9 identity")
    require(source_gate.get("runtime_resource_activated") is False, "V24 source gate unexpectedly activated runtime")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    identity = identity_records()
    pose_records: dict[str, list[dict[str, object]]] = {}
    pose_meta: dict[str, dict[str, object]] = {}
    reassemblies: dict[str, Image.Image] = {}
    for pose, definitions in POSE_COMPONENTS.items():
        preview_path = V24_ROOT / "candidate/normalized-200x200-source-review" / f"{pose.replace('_', '-')}-source-normalized.png"
        require(preview_path.is_file(), f"V24 normalized source preview is missing: {preview_path}")
        with Image.open(preview_path) as raw:
            normalized = raw.convert("L")
        special = [
            export_source_component(pose, normalized, component_name, role, box)
            for component_name, role, box in definitions
        ]
        overlaps = component_overlaps([*identity, *special])
        require(not overlaps, f"{pose} source masks overlap: {overlaps}")
        reassembly = compose(identity, special)
        reassembly_path = OUTPUT / "reassembled-200x200" / f"{pose}.pbm"
        preview_path = OUTPUT / "reassembled-800" / f"{pose}.png"
        save_mask(reassembly, reassembly_path)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        reassembly.resize((800, 800), Image.Resampling.NEAREST).save(preview_path)
        pose_records[pose] = special
        pose_meta[pose] = {
            "normalized_source": rel(V24_ROOT / "candidate/normalized-200x200-source-review" / f"{pose.replace('_', '-')}-source-normalized.png"),
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
    contact_path = OUTPUT / "contact-sheet.png"
    contact.resize((1200, 400), Image.Resampling.NEAREST).save(contact_path)

    layout = {
        "schema": "companion.v24_glance_readable_special_expression_component_layout.v1",
        "status": "UNBOUND_CANDIDATE_PENDING_COMPONENT_PARITY_AND_OWNER_ART_REVIEW",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "source_gate": rel(SOURCE_GATE),
        "identity_components": {record["name"]: public(record) for record in identity},
        "special_pose_components": {
            pose: {record["name"]: public(record) for record in records}
            for pose, records in pose_records.items()
        },
        "states": pose_meta,
        "component_contact_sheet": rel(contact_path),
        "source_pixel_rule": "special brow, mouth, cheek, and accent masks are thresholded crops from the V24 generated source; eyes, highlights, sparkles, and nose are exact locked V9 rig masks; no full source pose is a runtime asset",
        "prohibited_before_owner_art_review": [
            "whole-source-pose playback",
            "whole-face replacement",
            "CRIG export",
            "profile generation",
            "menu recording charging behavior binding",
            "firmware flash",
            "panel output"
        ],
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden"
    }
    layout_path = OUTPUT / "component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="ascii")
    report = {
        "schema": "companion.v24_glance_readable_special_expression_component_export.v1",
        "status": "PASS_V24_SPECIAL_SOURCE_COMPONENT_EXPORT_UNBOUND",
        "source_gate": rel(SOURCE_GATE),
        "layout": rel(layout_path),
        "component_contact_sheet": rel(contact_path),
        "identity_component_count": len(identity),
        "special_component_counts": {pose: len(records) for pose, records in pose_records.items()},
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden"
    }
    report_path = OUTPUT / "export-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print("PASS: V24 special sources exported as unbound V9-identity component masks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
