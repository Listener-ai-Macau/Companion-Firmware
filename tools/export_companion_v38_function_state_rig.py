#!/usr/bin/env python3
"""Export inactive V38 function-state components from the recorded V1 source sheet."""

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
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V37_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/sleepy-dream-component-layout.json"
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/generation-request-v1.json"
GENERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/candidate/generation-output-v1.json"
INTERPRETATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/candidate/choreography-interpretation-v2.json"
SOURCE_SHEET = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/candidate/generated-function-state-decoration-source-v1-candidate.png"
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate"
PACK_REVISION = 38
HEADER_BYTES = 80
INDEX_BYTES = 20
CELL_SIZE = 418
CANVAS = (200, 200)
SAFE_INSET = 8


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def canonical_cell(sheet: Image.Image, row: int, column: int) -> Image.Image:
    left = column * CELL_SIZE
    top = row * CELL_SIZE
    cell = sheet.crop((left, top, left + CELL_SIZE, top + CELL_SIZE))
    cell = cell.resize(CANVAS, Image.Resampling.LANCZOS).convert("L")
    return cell.point(lambda value: 0 if value < 128 else 255, mode="1")


def ink_bbox(image: Image.Image, region: tuple[int, int, int, int], name: str) -> tuple[Image.Image, tuple[int, int, int, int]]:
    source = image.crop(region).convert("1")
    pixels = source.load()
    points = [(x, y) for y in range(source.height) for x in range(source.width) if pixels[x, y] == 0]
    require(points, f"source crop has no ink: {name}")
    left = min(x for x, _ in points)
    top = min(y for _, y in points)
    right = max(x for x, _ in points) + 1
    bottom = max(y for _, y in points) + 1
    result = source.crop((left, top, right, bottom))
    return result, (region[0] + left, region[1] + top, result.width, result.height)


def write_pbm(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path)


def ink_pixels(image: Image.Image) -> int:
    return sum(1 for value in image.convert("1").getdata() if value == 0)


def copy_prior_components(output: Path) -> list[dict[str, Any]]:
    layout = json.loads(V37_LAYOUT.read_text(encoding="utf-8"))
    components = layout.get("components")
    require(layout.get("locked_v9_source", {}).get("sha256") == LOCKED_V9_SHA256 and
            layout.get("runtime_resource_activated") is False and layout.get("active_candidate_binding") == "forbidden" and
            isinstance(components, list) and len(components) == 45,
            "V37 source component lineage drifted")
    result: list[dict[str, Any]] = []
    for component in components:
        require(isinstance(component, dict), "V37 component record is invalid")
        source_mask = ROOT / str(component.get("mask", ""))
        destination = output / "component-masks" / f"{component['name']}.pbm"
        require(source_mask.is_file() and sha256(source_mask) == component.get("mask_sha256"),
                f"V37 component mask lineage drifted: {component.get('name')}")
        write_pbm(Image.open(source_mask).convert("1"), destination)
        require(sha256(destination) == component.get("mask_sha256"),
                f"V37 component changed while carrying into V38: {component.get('name')}")
        result.append({
            **component,
            "source_pack": "v38_merged_special",
            "source": {
                "kind": "carried_forward_v37_registered_mask",
                "prior_component_id": component["component_id"],
                "prior_layout": rel(V37_LAYOUT),
                "prior_mask": str(component["mask"]),
                "prior_mask_sha256": component["mask_sha256"],
            },
            "mask": rel(destination),
            "mask_sha256": sha256(destination),
        })
    return result


def generated_components(output: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    generation = json.loads(GENERATION.read_text(encoding="utf-8"))
    interpretation = json.loads(INTERPRETATION.read_text(encoding="utf-8"))
    require(request.get("status") == "REQUEST_RECORDED_PENDING_IMAGE_GENERATION" and
            request.get("locked_reference", {}).get("sha256") == LOCKED_V9_SHA256 and
            generation.get("status") == "GENERATED_SOURCE_PENDING_MACHINE_GATE" and
            generation.get("candidate_sheet", {}).get("sha256") == sha256(SOURCE_SHEET) and
            generation.get("candidate_sheet", {}).get("dimensions") == [1254, 1254] and
            interpretation.get("status") == "CANDIDATE_SOURCE_SCOPE_REINTERPRETED_BEFORE_COMPONENT_EXPORT" and
            interpretation.get("menu", {}).get("event") == "menu_entry_notice" and
            interpretation.get("menu", {}).get("maximum_expression_duration_ms") == 500 and
            interpretation.get("menu", {}).get("after_last_cue") == "withdraw_expression_rig_then_show_menu_ui",
            "V38 generated source provenance drifted")
    sheet = Image.open(SOURCE_SHEET).convert("RGB")
    require(sheet.size == (CELL_SIZE * 3, CELL_SIZE * 3), "generated V38 sheet dimensions drifted")
    cells: dict[str, Image.Image] = {}
    snapshots: list[dict[str, Any]] = []
    names = ("menu_grid_0", "menu_grid_1", "menu_grid_2", "upgrade_rise_0", "upgrade_rise_1", "upgrade_rise_2",
             "error_caution_0", "error_caution_1", "error_caution_2")
    for index, name in enumerate(names):
        row, column = divmod(index, 3)
        cell = canonical_cell(sheet, row, column)
        snapshot = output / "source-cells" / f"{name}.pbm"
        write_pbm(cell, snapshot)
        require(ink_pixels(cell) >= 700, f"generated V38 cell is unexpectedly empty: {name}")
        cells[name] = cell
        snapshots.append({"name": name, "path": rel(snapshot), "sha256": sha256(snapshot),
                          "cell_box_source": [column * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE],
                          "native_canvas": [200, 200], "ink_pixels": ink_pixels(cell)})

    definitions = [
        (545, "v38_menu_grid_0", "menu_entry", "menu_grid_0", (65, 30, 135, 90), (0, 0), 90, "charm", "menu_grid_0"),
        (546, "v38_menu_grid_1", "menu_entry", "menu_grid_1", (65, 30, 135, 90), (0, 0), 90, "charm", "menu_grid_1"),
        (547, "v38_menu_grid_2", "menu_entry", "menu_grid_2", (65, 30, 135, 90), (0, 0), 90, "charm", "menu_grid_2"),
        (548, "v38_upgrade_rise_0", "upgrade", "upgrade_rise_0", (75, 15, 125, 85), (0, 2), 90, "charm", "upgrade_rise_0"),
        (549, "v38_upgrade_rise_1", "upgrade", "upgrade_rise_1", (75, 15, 125, 85), (0, 2), 90, "charm", "upgrade_rise_1"),
        (550, "v38_upgrade_rise_2", "upgrade", "upgrade_rise_2", (75, 15, 125, 85), (0, 2), 90, "charm", "upgrade_rise_2"),
        (551, "v38_error_caution_0", "error", "error_caution_0", (75, 10, 125, 55), (0, 2), 90, "charm", "error_caution_0"),
        (552, "v38_error_caution_1", "error", "error_caution_1", (75, 10, 125, 55), (0, 2), 90, "charm", "error_caution_1"),
        (553, "v38_error_caution_2", "error", "error_caution_2", (75, 10, 125, 55), (0, 2), 90, "charm", "error_caution_2"),
        (554, "v38_error_left_brow", "error", "error_caution_1", (35, 50, 85, 85), (0, 0), 20, "left_brow", "error_brow_mouth"),
        (555, "v38_error_right_brow", "error", "error_caution_1", (115, 50, 165, 85), (0, 0), 20, "right_brow", "error_brow_mouth"),
        (556, "v38_error_mouth", "error", "error_caution_1", (75, 124, 125, 150), (0, 0), 60, "mouth", "error_brow_mouth"),
    ]
    result: list[dict[str, Any]] = []
    for component_id, name, event, cell_name, region, y_range, z_index, role, source_part in definitions:
        mask, crop = ink_bbox(cells[cell_name], region, name)
        destination = output / "component-masks" / f"{name}.pbm"
        write_pbm(mask, destination)
        if role == "charm":
            base = [(200 - mask.width) // 2, {"menu_entry": 47, "upgrade": 29, "error": 18}[event]]
        elif role == "left_brow":
            base = [45, 86]
        elif role == "right_brow":
            base = [127, 86]
        else:
            base = [100 - mask.width // 2, 160]
        require(base[0] >= SAFE_INSET and base[1] >= SAFE_INSET and
                base[0] + mask.width <= CANVAS[0] - SAFE_INSET and base[1] + mask.height <= CANVAS[1] - SAFE_INSET,
                f"generated V38 component escapes safe inset: {name}")
        result.append({
            "name": name, "component_id": component_id, "event": event, "source_pack": "v38_merged_special",
            "source": {
                "kind": "imagegen_v1_canonical_cell_crop",
                "sheet": rel(SOURCE_SHEET), "sheet_sha256": sha256(SOURCE_SHEET),
                "generation_manifest": rel(GENERATION), "request": rel(REQUEST), "locked_v9_sha256": LOCKED_V9_SHA256,
                "cell": cell_name, "cell_box_source": snapshots[names.index(cell_name)]["cell_box_source"],
                "canonical_cell": rel(output / "source-cells" / f"{cell_name}.pbm"),
                "canonical_cell_sha256": snapshots[names.index(cell_name)]["sha256"],
                "threshold": 128, "source_part": source_part, "crop_box_canonical": list(crop),
            },
            "mask": rel(destination), "mask_sha256": sha256(destination), "base_position": base,
            "mask_size": [mask.width, mask.height], "offset_range": {"min": [0, y_range[0]], "max": [0, y_range[1]]},
            "z_index": z_index, "composite_op": "ink", "role": role, "ink_pixels": ink_pixels(mask),
        })
    require([component["component_id"] for component in result] == list(range(545, 557)),
            "V38 generated component identifiers drifted")
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
        require(len(data) == stride * height, f"component stride drifted: {component['name']}")
        offset = data_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        index.extend(struct.pack("<HHHHIII", component["component_id"], width, height, stride, offset, len(data), crc))
        payload.extend(data)
        records.append({"component_id": component["component_id"], "name": component["name"], "width": width,
                        "height": height, "stride_bytes": stride, "data_offset": offset, "data_size": len(data),
                        "data_crc32": f"{crc:08X}"})
    header = bytearray(HEADER_BYTES)
    total = data_offset + len(payload)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, HEADER_BYTES)
    struct.pack_into("<I", header, 8, total)
    struct.pack_into("<I", header, 12, PACK_REVISION)
    struct.pack_into("<H", header, 16, CANVAS[0])
    struct.pack_into("<H", header, 18, CANVAS[1])
    struct.pack_into("<H", header, 20, 25)
    header[22] = 1
    header[23] = SAFE_INSET
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED_V9_SHA256)
    path = output / "companion-v9-function-state-rig-candidate-200x200.crig"
    path.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    return {"path": rel(path), "sha256": sha256(path), "revision": PACK_REVISION, "component_count": len(components),
            "total_size": total, "components": records}


def build_artifacts() -> dict[Path, bytes]:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="function-state-build-", dir=OUTPUT.parent))
    prior = copy_prior_components(staging)
    generated, snapshots = generated_components(staging)
    components = prior + generated
    require(len(components) == 57 and [component["component_id"] for component in components] == list(range(500, 557)),
            "V38 merged component coverage drifted")
    pack = build_pack(staging, components)
    layout = {
        "schema": "companion.v38_function_state_component_export.v1",
        "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240"],
        "locked_v9_source": {"path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png",
                             "sha256": LOCKED_V9_SHA256},
        "source_sheet": {"path": rel(SOURCE_SHEET), "sha256": sha256(SOURCE_SHEET), "request": rel(REQUEST),
                         "generation_manifest": rel(GENERATION), "choreography_interpretation": rel(INTERPRETATION),
                         "dimensions": [1254, 1254], "threshold": 128},
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "component_export_scope": "57 source masks: 45 V37 masks carried byte-identically plus 12 V38 generated function-state masks",
        "source_cells": snapshots, "components": components, "pack": pack,
        "non_claims": ["no_locked_source_modification", "no_full_face_card", "no_code_drawn_face", "no_runtime_binding",
                       "no_panel_or_driver_change", "no_human_acceptance"],
    }
    staging_prefix = rel(staging)
    output_prefix = rel(OUTPUT)

    def rebase(value: Any) -> Any:
        if isinstance(value, str):
            return output_prefix + value[len(staging_prefix):] if value.startswith(staging_prefix) else value
        if isinstance(value, list):
            return [rebase(item) for item in value]
        if isinstance(value, dict):
            return {key: rebase(item) for key, item in value.items()}
        return value

    layout = rebase(layout)
    layout_path = staging / "function-state-component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    artifacts = {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()}
    shutil.rmtree(staging)
    return {OUTPUT / path: data for path, data in artifacts.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
    print("PASS: generated inactive V38 function-state CRIG with 57 source masks from V37 carry-forward and recorded imagegen cells.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
