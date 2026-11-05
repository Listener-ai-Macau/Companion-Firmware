#!/usr/bin/env python3
"""Export V40 face-independent functional decoration components from the recorded V2 source sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-source-v2/generation-request-v2.json"
GENERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-source-v2/candidate/generation-output-v2.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-source-v2/candidate/generated-functional-decoration-source-v2-candidate.png"
V38_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/function-state-component-layout.json"
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-rig-v2/candidate"
REVISION = 40
HEADER_BYTES = 80
INDEX_BYTES = 20
CANVAS = (200, 200)
SAFE_INSET = 4
GRID_COLUMNS = 3
GRID_ROWS = 4


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_pbm(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path)


def ink_pixels(image: Image.Image) -> int:
    return sum(1 for value in image.convert("1").getdata() if value == 0)


def source_cell(sheet: Image.Image, index: int, name: str) -> tuple[Image.Image, tuple[int, int, int, int]]:
    row, column = divmod(index, GRID_COLUMNS)
    left = round(column * sheet.width / GRID_COLUMNS)
    right = round((column + 1) * sheet.width / GRID_COLUMNS)
    top = round(row * sheet.height / GRID_ROWS)
    bottom = round((row + 1) * sheet.height / GRID_ROWS)
    cell = sheet.crop((left, top, right, bottom)).convert("L")
    mono = cell.point(lambda value: 0 if value < 128 else 255, mode="1")
    inverse = mono.point(lambda value: 255 if value == 0 else 0, mode="1")
    bbox = inverse.getbbox()
    require(bbox is not None, f"V40 source cell has no ink: {name}")
    crop = mono.crop(bbox)
    return crop, (left + bbox[0], top + bbox[1], crop.width, crop.height)


def resize_mask(mask: Image.Image, scale: float, name: str) -> Image.Image:
    width = max(1, round(mask.width * scale))
    height = max(1, round(mask.height * scale))
    resized = mask.convert("L").resize((width, height), Image.Resampling.LANCZOS)
    result = resized.point(lambda value: 0 if value < 128 else 255, mode="1")
    require(ink_pixels(result) > 8, f"V40 component is unexpectedly thin after 1bpp scaling: {name}")
    return result


def copy_v38_components(output: Path) -> list[dict[str, Any]]:
    layout = json.loads(V38_LAYOUT.read_text(encoding="utf-8"))
    components = layout.get("components")
    require(layout.get("schema") == "companion.v38_function_state_component_export.v1" and
            layout.get("runtime_resource_activated") is False and layout.get("active_candidate_binding") == "forbidden" and
            isinstance(components, list) and len(components) == 57 and
            [component.get("component_id") for component in components] == list(range(500, 557)),
            "V38 source-mask lineage drifted")
    copied: list[dict[str, Any]] = []
    for component in components:
        source = ROOT / str(component.get("mask", ""))
        destination = output / "component-masks" / f"{component['name']}.pbm"
        require(source.is_file() and sha256(source) == component.get("mask_sha256"),
                f"V38 source mask drifted: {component.get('name')}")
        write_pbm(Image.open(source).convert("1"), destination)
        require(sha256(destination) == component.get("mask_sha256"),
                f"V38 source mask changed during V40 carry: {component.get('name')}")
        copied.append({
            **component,
            "source_pack": "v40_merged_special",
            "source": {"kind": "carried_forward_v38_registered_mask", "prior_component_id": component["component_id"],
                       "prior_layout": rel(V38_LAYOUT), "prior_mask": component["mask"],
                       "prior_mask_sha256": component["mask_sha256"]},
            "mask": rel(destination), "mask_sha256": sha256(destination),
        })
    return copied


def generated_components(output: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    generation = json.loads(GENERATION.read_text(encoding="utf-8"))
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            request.get("target_track") == "functional_decoration_track_only" and
            generation.get("status") == "CANDIDATE_SOURCE_GENERATED_PENDING_COMPONENT_EXPORT" and
            generation.get("candidate_source", {}).get("sha256") == sha256(SOURCE) and
            generation.get("candidate_source", {}).get("dimensions") == [1254, 1254],
            "V40 V2 image-generation provenance drifted")
    sheet = Image.open(SOURCE).convert("RGB")
    require(sheet.size == (1254, 1254), "V40 source sheet dimensions drifted")
    cells = (
        "recording_input_0", "recording_input_1", "recording_input_2",
        "bottom_charge_0", "bottom_charge_1", "bottom_charge_2",
        "upgrade_0", "upgrade_1", "upgrade_2",
        "error_0", "error_1", "error_2",
    )
    snapshots: list[dict[str, Any]] = []
    extracted: dict[str, Image.Image] = {}
    source_boxes: dict[str, tuple[int, int, int, int]] = {}
    for index, cell_name in enumerate(cells):
        mask, box = source_cell(sheet, index, cell_name)
        snapshot = output / "source-cells" / f"{cell_name}.pbm"
        write_pbm(mask, snapshot)
        extracted[cell_name] = mask
        source_boxes[cell_name] = box
        snapshots.append({"name": cell_name, "path": rel(snapshot), "sha256": sha256(snapshot),
                          "crop_box_source": list(box), "ink_pixels": ink_pixels(mask)})
    definitions = [
        (557, "v40_recording_input_0", "recording_input", "recording_input_0", 0.22, [146, 120]),
        (558, "v40_recording_input_1", "recording_input", "recording_input_1", 0.22, [146, 120]),
        (559, "v40_recording_input_2", "recording_input", "recording_input_2", 0.22, [146, 120]),
        (560, "v40_bottom_charge_0", "bottom_connector_charging", "bottom_charge_0", 0.30, [82, 153]),
        (561, "v40_bottom_charge_1", "bottom_connector_charging", "bottom_charge_1", 0.30, [82, 153]),
        (562, "v40_bottom_charge_2", "bottom_connector_charging", "bottom_charge_2", 0.30, [82, 153]),
        (563, "v40_upgrade_0", "upgrade_progress", "upgrade_0", 0.27, [92, 12]),
        (564, "v40_upgrade_1", "upgrade_progress", "upgrade_1", 0.27, [92, 12]),
        (565, "v40_upgrade_2", "upgrade_progress", "upgrade_2", 0.27, [92, 12]),
        (566, "v40_error_0", "error_caution", "error_0", 0.25, [86, 5]),
        (567, "v40_error_1", "error_caution", "error_1", 0.25, [86, 5]),
        (568, "v40_error_2", "error_caution", "error_2", 0.25, [86, 5]),
    ]
    result: list[dict[str, Any]] = []
    for component_id, name, event, cell_name, scale, base in definitions:
        mask = resize_mask(extracted[cell_name], scale, name)
        destination = output / "component-masks" / f"{name}.pbm"
        write_pbm(mask, destination)
        require(base[0] >= SAFE_INSET and base[1] >= SAFE_INSET and base[0] + mask.width <= CANVAS[0] - SAFE_INSET and
                base[1] + mask.height <= CANVAS[1] - SAFE_INSET,
                f"V40 generated component escapes the 200x200 safe inset: {name}")
        result.append({
            "component_id": component_id, "name": name, "event": event, "role": "charm", "source_pack": "v40_merged_special",
            "source": {"kind": "imagegen_v2_grid_cell_tight_crop_scaled", "sheet": rel(SOURCE), "sheet_sha256": sha256(SOURCE),
                       "request": rel(REQUEST), "generation_manifest": rel(GENERATION), "locked_v9_sha256": LOCKED,
                       "cell": cell_name, "crop_box_source": list(source_boxes[cell_name]), "threshold": 128, "scale": scale},
            "mask": rel(destination), "mask_sha256": sha256(destination), "base_position": base,
            "mask_size": [mask.width, mask.height], "offset_range": {"min": [0, 0], "max": [0, 0]},
            "z_index": 90, "composite_op": "ink", "ink_pixels": ink_pixels(mask),
        })
    require([component["component_id"] for component in result] == list(range(557, 569)),
            "V40 generated component ID coverage drifted")
    return result, snapshots


def build_pack(output: Path, components: list[dict[str, Any]]) -> dict[str, Any]:
    index = bytearray()
    payload = bytearray()
    records: list[dict[str, Any]] = []
    data_offset = HEADER_BYTES + INDEX_BYTES * len(components)
    for component in components:
        image = Image.open(ROOT / str(component["mask"])).convert("1")
        width, height = image.size
        stride = (width + 7) // 8
        data = image.tobytes()
        offset = data_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        require(len(data) == stride * height, f"V40 component stride drifted: {component['name']}")
        index.extend(struct.pack("<HHHHIII", component["component_id"], width, height, stride, offset, len(data), crc))
        payload.extend(data)
        records.append({"component_id": component["component_id"], "name": component["name"], "width": width, "height": height,
                        "stride_bytes": stride, "data_offset": offset, "data_size": len(data), "data_crc32": f"{crc:08X}"})
    total_size = data_offset + len(payload)
    header = bytearray(HEADER_BYTES)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, HEADER_BYTES)
    struct.pack_into("<I", header, 8, total_size)
    struct.pack_into("<I", header, 12, REVISION)
    struct.pack_into("<H", header, 16, 200)
    struct.pack_into("<H", header, 18, 200)
    struct.pack_into("<H", header, 20, 25)
    header[22] = 1
    header[23] = SAFE_INSET
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED)
    path = output / "companion-v9-functional-decoration-rig-v2-candidate-200x200.crig"
    path.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    return {"path": rel(path), "sha256": sha256(path), "revision": REVISION, "component_count": len(components),
            "total_size": total_size, "components": records}


def build_artifacts() -> dict[Path, bytes]:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="v40-functional-decoration-", dir=OUTPUT.parent))
    carried = copy_v38_components(staging)
    generated, snapshots = generated_components(staging)
    components = carried + generated
    require(len(components) == 69 and [component["component_id"] for component in components] == list(range(500, 569)),
            "V40 merged component namespace drifted")
    pack = build_pack(staging, components)
    layout = {
        "schema": "companion.v40_functional_decoration_component_export.v1",
        "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-240", "COMP-REQ-242"],
        "locked_v9_source": {"path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png", "sha256": LOCKED},
        "source_sheet": {"path": rel(SOURCE), "sha256": sha256(SOURCE), "request": rel(REQUEST),
                         "generation_manifest": rel(GENERATION), "dimensions": [1254, 1254], "threshold": 128, "grid": [3, 4]},
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "component_export_scope": "69 source masks: 57 V38 masks carried byte-identically plus 12 V40 face-independent functional masks",
        "source_cells": snapshots, "components": components, "pack": pack,
        "non_claims": ["no_locked_v9_modification", "no_full_face_card", "no_code_drawn_face", "no_runtime_binding",
                       "no_panel_or_driver_change", "no_human_acceptance"],
    }
    prefix = rel(staging)
    target_prefix = rel(OUTPUT)

    def rebase(value: Any) -> Any:
        if isinstance(value, str):
            return target_prefix + value[len(prefix):] if value.startswith(prefix) else value
        if isinstance(value, list):
            return [rebase(item) for item in value]
        if isinstance(value, dict):
            return {key: rebase(item) for key, item in value.items()}
        return value

    layout_path = staging / "functional-decoration-component-layout.json"
    layout_path.write_text(json.dumps(rebase(layout), indent=2) + "\n", encoding="utf-8")
    artifacts = {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()}
    shutil.rmtree(staging)
    return {OUTPUT / path: data for path, data in artifacts.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    if args.check:
        drifted = [path for path, data in artifacts.items() if not path.is_file() or path.read_bytes() != data]
        if drifted:
            for path in drifted:
                print(f"ERROR: generated artifact drifted: {rel(path)}")
            return 1
    else:
        for path, data in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("PASS: generated inactive V40 functional-decoration CRIG with 69 registered source masks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
