#!/usr/bin/env python3
"""Export V15 generated sleep-pose source masks without creating facial pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
V15_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v15-sleep-rig-pose-source"
ATTEMPT = V15_ROOT / "candidate/attempt-01-generated-pose-sheet.json"
SOURCE_GATE = ROOT / "docs/validation/companion-v9-extension-v15-sleep-rig-pose-attempt-01-20260719.json"
DEFAULT_OUTPUT = V15_ROOT / "candidate/component-export-attempt-01"
CANVAS = (200, 200)
CELL_NAMES = ("sleep_rest_anchor", "sleep_brow_settle", "sleep_lower_face_breath", "sleep_rest_return")

# Coordinates are source-image crop records, not drawn geometry.  The offsets
# align the generated eye anchors before every component is reduced to 200px.
CELL_ALIGNMENT = {
    "sleep_rest_anchor": (0, 0),
    "sleep_brow_settle": (41, 0),
    "sleep_lower_face_breath": (0, 69),
    "sleep_rest_return": (43, 68),
}
COMPONENT_SPECS = (
    ("left_brow_rest", "sleep_rest_anchor", (170, 265, 227, 288), 20),
    ("left_brow_settle", "sleep_brow_settle", (135, 268, 193, 296), 20),
    ("right_brow_rest", "sleep_rest_anchor", (419, 265, 476, 288), 21),
    ("left_closed_eye_anchor", "sleep_rest_anchor", (157, 365, 252, 403), 30),
    ("right_closed_eye_anchor", "sleep_rest_anchor", (392, 365, 487, 403), 31),
    ("left_cheek_rest", "sleep_rest_anchor", (140, 422, 173, 444), 40),
    ("left_cheek_breath", "sleep_lower_face_breath", (140, 354, 173, 375), 40),
    ("right_cheek_rest", "sleep_rest_anchor", (470, 422, 503, 444), 41),
    ("right_cheek_breath", "sleep_lower_face_breath", (471, 354, 503, 375), 41),
    ("nose_anchor", "sleep_rest_anchor", (309, 399, 335, 414), 50),
    ("mouth_rest", "sleep_rest_anchor", (295, 431, 350, 449), 60),
    ("mouth_breath", "sleep_lower_face_breath", (307, 360, 338, 394), 60),
    ("sleep_breath_mark_left", "sleep_rest_anchor", (98, 450, 142, 484), 70),
    ("sleep_breath_mark_right", "sleep_rest_anchor", (504, 450, 548, 484), 71),
    ("sleep_zzz_cluster", "sleep_rest_anchor", (470, 145, 598, 235), 80),
)
BASE_REST_COMPONENTS = (
    "left_brow_rest", "right_brow_rest", "left_closed_eye_anchor", "right_closed_eye_anchor",
    "left_cheek_rest", "right_cheek_rest", "nose_anchor", "mouth_rest",
    "sleep_breath_mark_left", "sleep_breath_mark_right", "sleep_zzz_cluster",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="ascii")


def threshold(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < 128 else 255, mode="1")


def normalize_cells(source: Image.Image) -> dict[str, Image.Image]:
    half_x, half_y = source.width // 2, source.height // 2
    if source.width != source.height or half_x != half_y:
        raise ValueError("V15 source pose sheet must have equal square cells")
    result: dict[str, Image.Image] = {}
    for index, name in enumerate(CELL_NAMES):
        column, row = index % 2, index // 2
        right = source.width if column else half_x
        bottom = source.height if row else half_y
        cell = source.crop((column * half_x, row * half_y, right, bottom)).convert("L")
        dx, dy = CELL_ALIGNMENT[name]
        anchored = Image.new("L", (half_x, half_y), 255)
        anchored.paste(cell, (dx, dy))
        result[name] = threshold(anchored.resize(CANVAS, Image.Resampling.NEAREST))
    return result


def normalize_box(box: tuple[int, int, int, int], pose: str, source_cell_side: int) -> tuple[int, int, int, int]:
    dx, dy = CELL_ALIGNMENT[pose]
    left = (box[0] + dx) * CANVAS[0] // source_cell_side
    top = (box[1] + dy) * CANVAS[1] // source_cell_side
    right = ((box[2] + dx) * CANVAS[0] + source_cell_side - 1) // source_cell_side
    bottom = ((box[3] + dy) * CANVAS[1] + source_cell_side - 1) // source_cell_side
    if not (0 <= left < right <= CANVAS[0] and 0 <= top < bottom <= CANVAS[1]):
        raise ValueError(f"normalized crop leaves the canvas: {pose}/{box}")
    return left, top, right, bottom


def ink_pixels(mask: Image.Image) -> int:
    return sum(pixel == 0 for pixel in mask.convert("1").getdata())


def compose(records: dict[str, dict[str, object]], names: tuple[str, ...]) -> Image.Image:
    canvas = Image.new("1", CANVAS, 1)
    for name in names:
        record = records[name]
        mask = Image.open(ROOT / str(record["mask"])).convert("1")
        left, top = record["base_position"]
        canvas.paste(mask, (left, top))
    return canvas


def write_preview_mask(mask: Image.Image, target: Path) -> None:
    rgba = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    rgba.paste((0, 0, 0, 255), mask=mask.convert("L").point(lambda value: 255 if value == 0 else 0))
    rgba.save(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, default=ATTEMPT)
    parser.add_argument("--source-gate", type=Path, default=SOURCE_GATE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        attempt_path = args.attempt.resolve()
        source_gate_path = args.source_gate.resolve()
        output = args.output_dir.resolve()
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        gate = json.loads(source_gate_path.read_text(encoding="utf-8"))
        if attempt.get("status") != "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT" or \
                gate.get("status") != "PASS_V15_SLEEP_RIG_POSE_SOURCE_GATE":
            raise ValueError("V15 source is not eligible for component export")
        if attempt.get("runtime_resource_activated") is not False or attempt.get("active_candidate_binding") != "forbidden":
            raise ValueError("V15 source has an illegal runtime disposition")
        source_path = ROOT / str(attempt.get("generated_image", ""))
        if not source_path.is_file() or attempt.get("generated_image_sha256") != sha256(source_path):
            raise ValueError("V15 generated source hash drifted")
        source = Image.open(source_path).convert("L")
        cells = normalize_cells(source)
        output.mkdir(parents=True, exist_ok=True)
        masks_dir, preview_dir, frames_dir = output / "component-masks", output / "preview-layers", output / "normalized-source-poses"
        for directory in (masks_dir, preview_dir, frames_dir):
            directory.mkdir(exist_ok=True)
        source_cell_side = source.width // 2
        for name, frame in cells.items():
            frame_path = frames_dir / f"{name}.pbm"
            frame.save(frame_path)
        components: list[dict[str, object]] = []
        records: dict[str, dict[str, object]] = {}
        for component_id, (name, pose, source_box, z_index) in enumerate(COMPONENT_SPECS, start=1):
            box = normalize_box(source_box, pose, source_cell_side)
            mask = cells[pose].crop(box).convert("1")
            if ink_pixels(mask) == 0:
                raise ValueError(f"V15 component crop is blank: {name}")
            mask_path = masks_dir / f"{name}.pbm"
            preview_path = preview_dir / f"{name}.png"
            mask.save(mask_path)
            write_preview_mask(mask, preview_path)
            record = {
                "component_id": component_id, "name": name, "source_pose": pose,
                "source_component_box": list(source_box), "normalized_component_box": list(box),
                "mask": relative(mask_path), "mask_sha256": sha256(mask_path), "preview_mask": relative(preview_path),
                "base_position": [box[0], box[1]], "mask_size": [mask.width, mask.height], "z_index": z_index,
                "source_sheet": relative(source_path), "source_sheet_sha256": sha256(source_path),
            }
            records[name] = record
            components.append(record)
        reassembled = compose(records, BASE_REST_COMPONENTS)
        rest_target = cells["sleep_rest_anchor"]
        difference = sum((left ^ right).bit_count() for left, right in zip(reassembled.tobytes(), rest_target.tobytes()))
        reassembled_path = output / "reassembled-sleep-rest-anchor-200x200.pbm"
        reassembled.save(reassembled_path)
        contact = Image.new("RGB", (200 * len(CELL_NAMES), 224), "white")
        draw = ImageDraw.Draw(contact)
        for index, name in enumerate(CELL_NAMES):
            contact.paste(cells[name].convert("RGB"), (index * 200, 0))
            draw.text((index * 200 + 5, 204), name, fill="black")
        contact_path = output / "normalized-source-pose-contact-sheet.png"
        contact.save(contact_path)
        layout = {
            "schema": "companion.v15_sleep_rig_component_source_layout.v1",
            "status": "CANDIDATE_SOURCE_MASK_EXPORT_PENDING_OWNER_ART_REVIEW",
            "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "crig_mount": "forbidden",
            "source_policy": "generated V15 source masks only; full-pose-cell playback is forbidden",
            "generation_request": relative(V15_ROOT / "generation-request.json"),
            "generation_attempt": relative(attempt_path), "generation_attempt_sha256": sha256(attempt_path),
            "source_gate": relative(source_gate_path), "source_sheet": relative(source_path), "source_sheet_sha256": sha256(source_path),
            "profile": {"width": 200, "height": 200, "pixel_format": "mono_1bpp_white_is_one_msb"},
            "source_cell_alignment": {name: list(CELL_ALIGNMENT[name]) for name in CELL_NAMES},
            "components": components,
            "base_rest_component_order": list(BASE_REST_COMPONENTS),
            "reassembly": {"target": relative(frames_dir / "sleep_rest_anchor.pbm"), "target_sha256": sha256(frames_dir / "sleep_rest_anchor.pbm"),
                           "reassembled": relative(reassembled_path), "reassembled_sha256": sha256(reassembled_path), "difference_pixels": difference},
            "artifacts": {"normalized_contact_sheet": {"path": relative(contact_path), "sha256": sha256(contact_path)}}
        }
        if difference != 0:
            raise ValueError(f"V15 base rest components do not exactly reassemble the normalized source: {difference}")
        layout_path = output / "v15-sleep-rig-component-layout.json"
        write_json(layout_path, layout)
        report = {"schema": "companion.v15_sleep_rig_component_source_export.v1", "status": "PASS_V15_SOURCE_MASK_EXPORT",
                  "layout": relative(layout_path), "layout_sha256": sha256(layout_path), "component_count": len(components),
                  "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "crig_mount": "forbidden",
                  "full_pose_cell_playback": "forbidden"}
        write_json(output / "export-report.json", report)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: exported V15 source-derived sleep Rig component masks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
