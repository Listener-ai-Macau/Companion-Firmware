#!/usr/bin/env python3
"""Export V13 sleep source masks as an inactive, unbound audit candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from verify_companion_v13_sleep_micro_component_source import REQUIRED_COMPONENTS, classify, components, sha256


ROOT = Path(__file__).resolve().parents[1]
V13_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v13-sleep-micro-component-repair"
DEFAULT_SOURCE = V13_ROOT / "generated_pet_expression_extension_v13_sleep_micro_component_repair_candidate.png"
DEFAULT_GATE = ROOT / "docs/validation/companion-v9-extension-v13-sleep-micro-component-repair-machine-20260719.json"
DEFAULT_OUTPUT = V13_ROOT / "candidate"
LOCKED_V9 = "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
CANVAS = (200, 200)


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="ascii")


def square_normalize(image: Image.Image, source_parts: list[dict[str, int]]) -> tuple[Image.Image, dict[str, int]]:
    left = min(part["left"] for part in source_parts)
    top = min(part["top"] for part in source_parts)
    right = max(part["left"] + part["width"] for part in source_parts)
    bottom = max(part["top"] + part["height"] for part in source_parts)
    side = round(max(right - left, bottom - top) * 1.14)
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    crop_left = center_x - side // 2
    crop_top = center_y - side // 2
    source = image.convert("L")
    square = Image.new("L", (side, side), 255)
    source_left = max(0, crop_left)
    source_top = max(0, crop_top)
    source_right = min(source.width, crop_left + side)
    source_bottom = min(source.height, crop_top + side)
    square.paste(source.crop((source_left, source_top, source_right, source_bottom)),
                 (source_left - crop_left, source_top - crop_top))
    normalized = square.resize(CANVAS, Image.Resampling.LANCZOS).point(
        lambda value: 255 if value >= 128 else 0, mode="1"
    )
    return normalized, {"left": crop_left, "top": crop_top, "side": side}


def preview_mask(mask: Image.Image) -> Image.Image:
    result = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    pixels = result.load()
    source = mask.convert("1").load()
    for y in range(mask.height):
        for x in range(mask.width):
            if source[x, y] == 0:
                pixels[x, y] = (0, 0, 0, 255)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--source-gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source_path = args.source.resolve()
    gate_path = args.source_gate.resolve()
    output = args.output_dir.resolve()
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("status") != "PASS_V13_SLEEP_MICRO_COMPONENT_SOURCE_GATE" or \
                gate.get("candidate_sha256") != sha256(source_path):
            raise ValueError("V13 source gate has not passed for this exact image")
        image = Image.open(source_path).convert("L")
        source_parts = components(image)
        normalized, crop = square_normalize(image, source_parts)
        output.mkdir(parents=True, exist_ok=True)
        normalized_path = output / "normalized-sleep-micro-component-source-200x200.pbm"
        normalized_preview_path = output / "normalized-sleep-micro-component-source-200x200.png"
        normalized_contact_path = output / "normalized-sleep-micro-component-source-contact.png"
        normalized.save(normalized_path)
        normalized.save(normalized_preview_path)
        normalized.convert("L").resize((1000, 1000), Image.Resampling.NEAREST).save(normalized_contact_path)
        normalized_parts = components(normalized, minimum_pixels=20)
        assignments, errors = classify(normalized_parts, *CANVAS, top_empty_ratio=0.25)
        if errors or set(assignments) != set(REQUIRED_COMPONENTS):
            raise ValueError(
                "normalized V13 source no longer has the required extractable components: "
                f"{errors}; found {len(normalized_parts)} islands"
            )

        masks = output / "component-masks"
        previews = output / "preview-layers"
        masks.mkdir(parents=True, exist_ok=True)
        previews.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, object]] = []
        for component_id, name in enumerate(REQUIRED_COMPONENTS, start=1):
            part = assignments[name]
            box = (part["left"], part["top"], part["left"] + part["width"], part["top"] + part["height"])
            mask = normalized.crop(box).convert("1")
            mask_path = masks / f"{name}.pbm"
            preview_path = previews / f"{name}.png"
            mask.save(mask_path)
            preview_mask(mask).save(preview_path)
            records.append({
                "component_id": component_id,
                "name": name,
                "source_component_box": list(box),
                "base_position": [part["left"], part["top"]],
                "mask_size": [part["width"], part["height"]],
                "mask": relative(mask_path),
                "mask_sha256": sha256(mask_path),
                "preview_mask": relative(preview_path),
                "z_index": component_id,
                "legal_offset": {"min": [0, 0], "max": [0, 0]},
                "source_sheet": relative(source_path),
                "source_sheet_sha256": sha256(source_path),
            })
        layout = {
            "schema": "companion.v13_sleep_micro_component_source_layout.v1",
            "status": "CANDIDATE_SOURCE_COMPONENT_EXPORT_PENDING_OWNER_ART_REVIEW",
            "runtime_resource_activated": False,
            "active_candidate_binding": "forbidden",
            "source_policy": "generated V13 source masks only; full-face source-card playback is forbidden",
            "source_baseline": {"source": LOCKED_V9, "sha256": LOCKED_V9_SHA256},
            "source_image": {"path": relative(source_path), "sha256": sha256(source_path)},
            "source_gate": relative(gate_path),
            "normalization": {"method": "generated_ink_bounds_square_crop_then_200px_threshold", "source_crop": crop,
                              "normalized": relative(normalized_path), "normalized_sha256": sha256(normalized_path)},
            "components": records,
            "owner_gate": "V13 owner art acceptance is required before any sleep runtime binding or CRIG revision",
        }
        layout_path = output / "sleep-micro-component-source-layout.json"
        write_json(layout_path, layout)
        report = {
            "schema": "companion.v13_sleep_micro_component_source_export.v1",
            "status": "PASS_V13_SLEEP_MICRO_COMPONENT_SOURCE_EXPORT_RUNTIME_INACTIVE",
            "layout": relative(layout_path),
            "layout_sha256": sha256(layout_path),
            "source": relative(source_path),
            "source_sha256": sha256(source_path),
            "component_count": len(records),
            "runtime_resource_activated": False,
            "active_candidate_binding": "forbidden",
            "full_face_source_card_playback": "forbidden",
        }
        write_json(output / "export-report.json", report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: exported ten V13 sleep source masks as an unbound runtime-inactive candidate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
