#!/usr/bin/env python3
"""Export V18-V20 complete source poses as unbound V9 Rig component masks."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from verify_companion_v17_functional_context_source import connected_components
from verify_companion_v18_v20_special_expression_sources import SPECS, face_geometry, special_geometry


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GATE = ROOT / "docs/validation/companion-v18-v20-special-expression-source-gate-20260719.json"
BASE_RIG = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
BASE_COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
IDENTITY_NAMES = (
    "left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open",
    "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default",
)
CANVAS = (200, 200)
FILE_PREFIX = {
    "menu_active": "m",
    "recording_active": "r",
    "upgrade_active": "u",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def crop_center(crop: list[int]) -> tuple[float, float]:
    return ((crop[0] + crop[2]) / 2, (crop[1] + crop[3]) / 2)


def item_center(item: dict[str, Any]) -> tuple[float, float]:
    return crop_center(item["crop"])


def item_size(item: dict[str, Any]) -> tuple[int, int]:
    crop = item["crop"]
    return crop[2] - crop[0], crop[3] - crop[1]


def mask_from_component(source: Image.Image, crop: list[int], scale: float) -> Image.Image:
    left, top, right, bottom = crop
    raw = source.crop((left, top, right, bottom)).convert("L")
    mask = Image.new("1", raw.size, 1)
    for y in range(raw.height):
        for x in range(raw.width):
            if raw.getpixel((x, y)) < 128:
                mask.putpixel((x, y), 0)
    return mask.resize((max(1, round(mask.width * scale)), max(1, round(mask.height * scale))), Image.Resampling.NEAREST)


def transparent_preview(mask: Image.Image) -> Image.Image:
    preview = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    pixels = preview.load()
    for y in range(mask.height):
        for x in range(mask.width):
            if mask.getpixel((x, y)) == 0:
                pixels[x, y] = (0, 0, 0, 255)
    return preview


def base_component_records() -> dict[str, dict[str, Any]]:
    layout = json.loads(BASE_RIG.read_text(encoding="utf-8"))
    records = {row["name"]: row for row in layout["components"] if row["name"] in IDENTITY_NAMES}
    if set(records) != set(IDENTITY_NAMES):
        raise ValueError("locked V9 identity component vocabulary drifted")
    return records


def feature_selection(function: str, components: list[dict[str, Any]], identity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    left_eye = identity["left_eye"]
    right_eye = identity["right_eye"]
    eye_y = identity["eye_pair_center"][1]
    eye_h = (left_eye["crop"][3] - left_eye["crop"][1] + right_eye["crop"][3] - right_eye["crop"][1]) / 2
    pair_x = identity["eye_pair_center"][0]
    candidates = components[2:]
    brows = [item for item in candidates if 1000 <= item["ink_pixels"] <= 6000 and
             item_center(item)[1] < eye_y - eye_h * 0.45]
    brows = sorted(brows, key=lambda item: item_center(item)[0])
    lower = [item for item in candidates if 1000 <= item["ink_pixels"] <= 6000 and
             item_center(item)[1] > eye_y + eye_h * 0.42]
    left_cheek = max((item for item in lower if item_center(item)[0] < pair_x - 65), key=lambda item: item["ink_pixels"])
    right_cheek = max((item for item in lower if item_center(item)[0] > pair_x + 65), key=lambda item: item["ink_pixels"])
    mouth = max((item for item in lower if abs(item_center(item)[0] - pair_x) <= 90), key=lambda item: item["ink_pixels"])
    result: dict[str, dict[str, Any]] = {
        "left_brow": brows[0], "right_brow": brows[-1], "left_cheek": left_cheek,
        "right_cheek": right_cheek, "mouth": mouth,
    }
    if function == "menu_active":
        marks = sorted((item for item in candidates if item["ink_pixels"] < 1200 and item_center(item)[1] < eye_y - 100),
                       key=lambda item: item_center(item)[1])
        result.update({f"menu_dot_{index + 1}": item for index, item in enumerate(marks)})
    elif function == "recording_active":
        marks = [item for item in candidates if item["ink_pixels"] >= 1000 and
                 (item["crop"][2] <= left_eye["crop"][0] or item["crop"][0] >= right_eye["crop"][2]) and
                 left_eye["crop"][1] <= item_center(item)[1] <= left_eye["crop"][3]]
        left = sorted((item for item in marks if item_center(item)[0] < left_eye["crop"][0]), key=lambda item: item_center(item)[0])
        right = sorted((item for item in marks if item_center(item)[0] > right_eye["crop"][2]), key=lambda item: item_center(item)[0])
        result.update({"recording_ripple_left_outer": left[0], "recording_ripple_left_inner": left[1],
                       "recording_ripple_right_inner": right[0], "recording_ripple_right_outer": right[1]})
    else:
        marks = [item for item in candidates if item["ink_pixels"] < 1200 and item_center(item)[1] < eye_y - 100]
        horizontal = sorted((item for item in marks if item_size(item)[0] > item_size(item)[1]), key=lambda item: item_center(item)[1])
        vertical = sorted((item for item in marks if item_size(item)[0] <= item_size(item)[1]), key=lambda item: item_center(item)[0])
        result.update({"upgrade_segment_top": horizontal[0], "upgrade_segment_bottom": horizontal[1],
                       "upgrade_segment_left": vertical[0], "upgrade_segment_right": vertical[1]})
    return result


def paste_mask(canvas: Image.Image, mask: Image.Image, position: tuple[int, int], erase: bool = False) -> set[tuple[int, int]]:
    pixels = canvas.load()
    occupied: set[tuple[int, int]] = set()
    for y in range(mask.height):
        for x in range(mask.width):
            if mask.getpixel((x, y)) == 0:
                target_x, target_y = position[0] + x, position[1] + y
                if 0 <= target_x < canvas.width and 0 <= target_y < canvas.height:
                    pixels[target_x, target_y] = 1 if erase else 0
                    occupied.add((target_x, target_y))
    return occupied


def export_one(function: str, spec: dict[str, str], base: dict[str, dict[str, Any]], clean: bool) -> dict[str, Any]:
    iteration_root = ROOT / "docs/art/iterations" / spec["iteration"]
    attempt_path = iteration_root / "candidate" / spec["attempt"]
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    if attempt.get("status") != "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT":
        raise ValueError(f"{function} is not ready for source-mask export")
    source_path = ROOT / str(attempt["generated_image"])
    source = Image.open(source_path).convert("L")
    components = sorted(connected_components(source), key=lambda item: int(item["ink_pixels"]), reverse=True)
    identity, errors = face_geometry(components, source.width, source.height)
    if errors or identity is None:
        raise ValueError(f"{function} source geometry drifted: {errors}")
    _, special_errors = special_geometry(function, components, identity)
    if special_errors:
        raise ValueError(f"{function} source detail geometry drifted: {special_errors}")
    selected = feature_selection(function, components, identity)
    left_source = crop_center(identity["left_eye"]["crop"])
    right_source = crop_center(identity["right_eye"]["crop"])
    left_target = (base["left_eye_open"]["base_position"][0] + base["left_eye_open"]["anchor"][0],
                   base["left_eye_open"]["base_position"][1] + base["left_eye_open"]["anchor"][1])
    right_target = (base["right_eye_open"]["base_position"][0] + base["right_eye_open"]["anchor"][0],
                    base["right_eye_open"]["base_position"][1] + base["right_eye_open"]["anchor"][1])
    scale = (right_target[0] - left_target[0]) / (right_source[0] - left_source[0])
    tx, ty = left_target[0] - scale * left_source[0], left_target[1] - scale * left_source[1]
    output = iteration_root / "candidate/component-export-attempt-01"
    if clean and output.exists():
        shutil.rmtree(output)
    masks_dir, preview_dir = output / "component-masks", output / "preview-layers"
    masks_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, Any] = {}
    file_prefix = FILE_PREFIX[function]
    group_by_name: dict[str, str] = {}
    for base_name, role, z in (
        ("left_brow", "left_brow", 20), ("right_brow", "right_brow", 20),
        ("left_cheek", "left_cheek", 40), ("right_cheek", "right_cheek", 40), ("mouth", "mouth", 60),
    ):
        item = selected[base_name]
        name = f"{spec['version']}_{function}__{base_name}"
        group_by_name[name] = "expression"
        mask = mask_from_component(source, item["crop"], scale)
        position = (round(item["crop"][0] * scale + tx), round(item["crop"][1] * scale + ty))
        # Keep Windows paths below MAX_PATH; semantic component names stay in the layout.
        mask_path, preview_path = masks_dir / f"{file_prefix}{len(records):02d}.pbm", preview_dir / f"{file_prefix}{len(records):02d}.png"
        mask.save(mask_path); transparent_preview(mask).save(preview_path)
        records[name] = {"role": role, "group": "expression", "source_crop": item["crop"],
                         "base_position": list(position), "anchor": [mask.width // 2, mask.height // 2],
                         "offset_range": {"min": [-2, -2], "max": [2, 2]}, "z_index": z,
                         "mask": mask_path.relative_to(ROOT).as_posix(), "mask_sha256": sha256(mask_path),
                         "preview_layer": preview_path.relative_to(ROOT).as_posix(), "preview_layer_sha256": sha256(preview_path),
                         "mask_size": [mask.width, mask.height], "source": "generated_complete_special_pose"}
    for base_name, item in selected.items():
        if base_name in {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}:
            continue
        name = f"{spec['version']}_{function}__{base_name}"
        group_by_name[name] = "context_detail"
        mask = mask_from_component(source, item["crop"], scale)
        position = (round(item["crop"][0] * scale + tx), round(item["crop"][1] * scale + ty))
        mask_path, preview_path = masks_dir / f"{file_prefix}{len(records):02d}.pbm", preview_dir / f"{file_prefix}{len(records):02d}.png"
        mask.save(mask_path); transparent_preview(mask).save(preview_path)
        records[name] = {"role": "context_detail", "group": "context_detail", "source_crop": item["crop"],
                         "base_position": list(position), "anchor": [mask.width // 2, mask.height // 2],
                         "offset_range": {"min": [-2, -2], "max": [2, 2]}, "z_index": 10,
                         "mask": mask_path.relative_to(ROOT).as_posix(), "mask_sha256": sha256(mask_path),
                         "preview_layer": preview_path.relative_to(ROOT).as_posix(), "preview_layer_sha256": sha256(preview_path),
                         "mask_size": [mask.width, mask.height], "source": "generated_complete_special_pose"}
    identity_records: dict[str, Any] = {}
    for name, item in base.items():
        mask_path = BASE_COMPONENTS / f"{name}.pbm"
        identity_records[name] = {"role": item["role"], "group": "locked_v9_identity", "base_position": item["base_position"],
                                  "anchor": item["anchor"], "offset_range": item["offset_range"], "z_index": item["z_index"],
                                  "composite_op": item.get("composite_op", "ink"), "mask": mask_path.relative_to(ROOT).as_posix(),
                                  "mask_sha256": sha256(mask_path), "mask_size": list(Image.open(mask_path).size),
                                  "source": "locked_v9_rig_v1_component"}
    canvas = Image.new("1", CANVAS, 1)
    occupied_by: dict[str, set[tuple[int, int]]] = {}
    for name, record in sorted(identity_records.items(), key=lambda pair: pair[1]["z_index"]):
        mask = Image.open(ROOT / record["mask"]).convert("1")
        occupied_by[name] = paste_mask(canvas, mask, tuple(record["base_position"]), record.get("composite_op") == "erase")
    for name, record in sorted(records.items(), key=lambda pair: pair[1]["z_index"]):
        mask = Image.open(ROOT / record["mask"]).convert("1")
        occupied_by[name] = paste_mask(canvas, mask, tuple(record["base_position"]))
    all_ink = [(name, pixels) for name, pixels in occupied_by.items() if identity_records.get(name, records.get(name, {})).get("composite_op") != "erase"]
    overlaps = []
    for index, (first_name, first_pixels) in enumerate(all_ink):
        for second_name, second_pixels in all_ink[index + 1:]:
            shared = first_pixels & second_pixels
            if shared:
                overlaps.append({"first": first_name, "second": second_name, "pixels": len(shared)})
    reassembly_path = output / f"{function}-source-component-reassembly-200x200.pbm"
    canvas.save(reassembly_path)
    reassembly_preview_path = output / f"{function}-source-component-reassembly-preview.png"
    canvas.resize((800, 800), Image.Resampling.NEAREST).convert("L").save(reassembly_preview_path)
    audit = {"schema": "companion.v18_v20_special_expression_component_occlusion_audit.v1",
             "status": "PASS_ZERO_COMPONENT_OVERLAP" if not overlaps else "FAIL_COMPONENT_OVERLAP",
             "function": function, "overlaps": overlaps}
    audit_path = output / "component-occlusion-audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="ascii")
    layout = {"schema": "companion.v18_v20_complete_special_expression_component_source_layout.v1",
              "status": "UNBOUND_PENDING_OWNER_ART_REVIEW", "function": function,
              "generated_source": attempt["generated_image"], "generated_source_sha256": attempt["generated_image_sha256"],
              "locked_v9_source_sha256": LOCKED_V9_SHA256, "canvas": list(CANVAS),
              "source_alignment": {"method": "source_eye_anchor_affine", "source_pair_centers": [list(left_source), list(right_source)],
                                   "target_pair_centers": [list(left_target), list(right_target)], "uniform_scale": scale, "translation": [tx, ty]},
              "identity_components": identity_records, "special_expression_components": records,
              "reassembly": reassembly_path.relative_to(ROOT).as_posix(),
              "reassembly_preview": reassembly_preview_path.relative_to(ROOT).as_posix(),
              "occlusion_audit": audit_path.relative_to(ROOT).as_posix(),
              "prohibited_before_owner_art_review": ["whole-source-pose playback", "event choreography", "CRIG export", "runtime activation"],
              "runtime_resource_activated": False, "active_candidate_binding": "forbidden"}
    layout_path = output / "complete-special-expression-component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="ascii")
    report = {"schema": "companion.v18_v20_complete_special_expression_component_export.v1",
              "status": "PASS_COMPLETE_SPECIAL_EXPRESSION_SOURCE_MASK_EXPORT_UNBOUND" if not overlaps else "FAIL_COMPLETE_SPECIAL_EXPRESSION_SOURCE_MASK_EXPORT",
              "function": function, "layout": layout_path.relative_to(ROOT).as_posix(), "component_count": len(records),
              "identity_component_count": len(identity_records), "reassembly": reassembly_path.relative_to(ROOT).as_posix(),
              "reassembly_preview": reassembly_preview_path.relative_to(ROOT).as_posix(),
              "runtime_resource_activated": False, "active_candidate_binding": "forbidden"}
    (output / "export-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if overlaps:
        raise ValueError(f"{function} component export overlaps: {overlaps}")
    return {"function": function, "output": output.relative_to(ROOT).as_posix(),
            "reassembly": reassembly_path.relative_to(ROOT).as_posix(),
            "reassembly_preview": reassembly_preview_path.relative_to(ROOT).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    errors: list[str] = []
    exports: list[dict[str, Any]] = []
    try:
        gate = json.loads(SOURCE_GATE.read_text(encoding="utf-8"))
        if gate.get("status") != "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_GATE":
            raise ValueError("V18-V20 complete special-expression source gate has not passed")
        base = base_component_records()
        for function, spec in SPECS.items():
            try:
                exports.append(export_one(function, spec, base, args.clean))
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                errors.append(f"{function}: {exc}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    result = {"schema": "companion.v18_v20_complete_special_expression_component_export_summary.v1",
              "status": "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_MASK_EXPORT_UNBOUND" if not errors else
                        "FAIL_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_MASK_EXPORT",
              "exports": exports, "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "errors": errors}
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: exported V18-V20 complete special-expression source masks with locked V9 identity components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
