#!/usr/bin/env python3
"""Gate the versioned V43 recording-input source and its 200x200 safe-zone export."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-recording-input-inward-source-v1/generation-request-v1.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-recording-input-inward-source-v1/candidate/attempt-01-recording-input-inward.png"
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v5/candidate/v43-special-component-layout.json"
REPORT = ROOT / "docs/validation/companion-v43-recording-input-inward-source-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_SHA = "278AE1ED5EED32F80CA09ACAD8C6F3112156ABCFB3653A5DAD3270C30FDFB4B7"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{rel(path)} must be an object")
    return value


def crop_metrics(image: Image.Image, index: int) -> dict[str, Any]:
    left = round(index * image.width / 3)
    right = round((index + 1) * image.width / 3)
    cell = image.crop((left, 0, right, image.height)).convert("L")
    ink = [[x, y] for y in range(cell.height) for x in range(cell.width) if cell.getpixel((x, y)) < 128]
    require(ink, f"recording source cell {index} is blank")
    xs = [point[0] for point in ink]
    ys = [point[1] for point in ink]
    bbox = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
    left_ink = sum(1 for x, _ in ink if x < cell.width * 0.50)
    right_ink = sum(1 for x, _ in ink if x >= cell.width * 0.50)
    far_right_ink = sum(1 for x, _ in ink if x >= cell.width * 0.88)
    require(left_ink > 0 and right_ink > 0, f"recording source cell {index} lacks separated inward wave/microphone sides")
    require(far_right_ink == 0, f"recording source cell {index} has outward marks on the microphone's right")
    return {"cell": index, "cell_size": [cell.width, cell.height], "ink_bbox": bbox,
            "ink_pixels": len(ink), "left_half_ink": left_ink, "right_half_ink": right_ink,
            "far_right_ink": far_right_ink}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request = load(REQUEST)
    layout = load(LAYOUT)
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            request.get("source_sheet", {}).get("recording_contract", "").find("toward the left edge") >= 0,
            "recording inward source request provenance drifted")
    require(SOURCE.is_file() and sha256(SOURCE) == SOURCE_SHA, "recording inward source hash drifted")
    with Image.open(SOURCE) as opened:
        source = opened.convert("RGB")
    require(source.size == (2172, 724), f"recording inward source dimensions drifted: {source.size}")
    metrics = [crop_metrics(source, index) for index in range(3)]
    components = {int(component["component_id"]): component for component in layout.get("components", [])}
    exported = [components.get(component_id) for component_id in (569, 570, 571)]
    require(all(component is not None for component in exported), "recording inward components are not registered")
    for component in exported:
        require(component["source"]["sheet"] == rel(SOURCE) and
                component["source"]["wave_direction"] == "inward_toward_face_on_left" and
                component["base_position"][0] >= 160 and component["base_position"][1] >= 100 and
                component["base_position"][0] + component["mask_size"][0] <= 196 and
                component["base_position"][1] + component["mask_size"][1] <= 145,
                f"recording inward component escapes registered right-side safe zone: {component['name']}")
    report = {
        "schema": "companion.v43_recording_input_inward_source_gate.v1",
        "status": "PASS_V43_RECORDING_INPUT_INWARD_SOURCE_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-263"],
        "locked_v9_source_sha256": LOCKED,
        "generated_source": {"path": rel(SOURCE), "sha256": SOURCE_SHA, "dimensions": [2172, 724],
                              "request": rel(REQUEST), "cells": metrics},
        "component_ids": [569, 570, 571],
        "semantic_gate": "microphone on right; one-to-three sound marks remain on its left and read inward toward the face",
        "face_collision_gate": "registered right-side safe zone; no eye/brow/nose/mouth/cheek overlap",
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_runtime_activation", "no_human_acceptance"],
    }
    path = args.write if args.write.is_absolute() else ROOT / args.write
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V43 recording-input source faces inward and stays in the registered right-side safe zone ({path}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
