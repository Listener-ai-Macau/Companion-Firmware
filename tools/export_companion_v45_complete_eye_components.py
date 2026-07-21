#!/usr/bin/env python3
"""Carry V44 special masks forward and add gated V45 complete-eye transitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import zlib
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
V44_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/v44-special-component-layout.json"
V44_OUTPUT = V44_LAYOUT.parent
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/generation-request-v5.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v2/candidate/attempt-04-complete-eye-paired-stages.png"
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_SHA = "3F423450EE647D741249AF424112DC5DDB928A279A7D9EDB48E6B0F81758DFDF"
CANVAS = (200, 200)
SAFE_INSET = 4
REVISION = 45
HEADER_BYTES = 80
INDEX_BYTES = 20
CELL_NAMES = ("left_closing", "right_closing", "left_closed", "right_closed", "left_opening", "right_opening")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{rel(path)} must contain an object")
    return value


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < 128 else 255, mode="1")


def ink_pixels(image: Image.Image) -> int:
    return sum(1 for pixel in image.convert("1").getdata() if pixel == 0)


def crop_pair_component(sheet: Image.Image, stage_index: int, side: int) -> tuple[Image.Image, list[int]]:
    """Extract one connected, complete eye group from a paired stage."""
    left = round(stage_index * sheet.width / 5)
    right = round((stage_index + 1) * sheet.width / 5)
    stage = binary(sheet.crop((left, 0, right, sheet.height)))
    width, height = stage.size
    remaining = {(x, y) for y in range(height) for x in range(width) if stage.getpixel((x, y)) == 0}
    found: list[tuple[int, list[tuple[int, int]]]] = []
    while remaining:
        seed = remaining.pop()
        queue: deque[tuple[int, int]] = deque([seed])
        points = [seed]
        while queue:
            x, y = queue.popleft()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1),
                             (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
                    points.append(neighbor)
        if len(points) > 10:
            found.append((min(x for x, _ in points), points))
    require(len(found) == 2, f"V45 stage {stage_index} must contain two complete eye groups")
    found.sort(key=lambda item: item[0])
    points = found[side][1]
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    return stage.crop(box), [left + box[0], box[1], box[2] - box[0], box[3] - box[1]]


def resize_mask(mask: Image.Image, scale: float, name: str) -> Image.Image:
    width = max(1, round(mask.width * scale))
    height = max(1, round(mask.height * scale))
    result = binary(mask.resize((width, height), Image.Resampling.LANCZOS))
    require(ink_pixels(result) > 3, f"V45 mask is too thin: {name}")
    return result


def build_pack(path: Path, components: list[dict[str, Any]]) -> dict[str, Any]:
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
        require(len(data) == stride * height, f"V45 CRIG stride drifted: {component['name']}")
        index.extend(struct.pack("<HHHHIII", component["component_id"], width, height, stride, offset, len(data), crc))
        payload.extend(data)
        records.append({"component_id": component["component_id"], "name": component["name"], "width": width,
                        "height": height, "stride_bytes": stride, "data_offset": offset, "data_size": len(data),
                        "data_crc32": f"{crc:08X}"})
    header = bytearray(HEADER_BYTES)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, HEADER_BYTES)
    struct.pack_into("<I", header, 8, data_offset + len(payload))
    struct.pack_into("<I", header, 12, REVISION)
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
    header[44:76] = bytes.fromhex(LOCKED)
    path.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    return {"path": rel(path), "sha256": sha256(path), "revision": REVISION, "component_count": len(components),
            "total_size": data_offset + len(payload), "components": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    v44 = load(V44_LAYOUT)
    request = load(REQUEST)
    require(v44.get("locked_v9_source", {}).get("sha256") == LOCKED and len(v44.get("components", [])) == 50,
            "V44 carried special layout drifted")
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            SOURCE.is_file() and sha256(SOURCE) == SOURCE_SHA, "V45 source provenance drifted")
    output = OUTPUT.resolve()
    output.mkdir(parents=True, exist_ok=True)
    mask_dir = output / "component-masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    components: list[dict[str, Any]] = []
    for original in v44["components"]:
        old_mask = ROOT / str(original["mask"])
        destination = mask_dir / f"{original['name']}.pbm"
        require(old_mask.is_file() and sha256(old_mask) == original["mask_sha256"], f"V44 mask drifted: {original['name']}")
        shutil.copyfile(old_mask, destination)
        copied = json.loads(json.dumps(original))
        copied["source_pack"] = "v45_merged_special"
        copied["mask"] = rel(destination)
        components.append(copied)
    with Image.open(SOURCE) as opened:
        sheet = opened.convert("RGB")
    stage_specs = [
        (599, "v45_blink_left_closing", "left_eye", 1, 0, [48, 115]),
        (600, "v45_blink_right_closing", "right_eye", 1, 1, [132, 115]),
        (601, "v45_blink_left_closed", "left_eye", 2, 0, [47, 130]),
        (602, "v45_blink_right_closed", "right_eye", 2, 1, [130, 130]),
        (603, "v45_blink_left_opening", "left_eye", 3, 0, [47, 115]),
        (604, "v45_blink_right_opening", "right_eye", 3, 1, [131, 115]),
    ]
    for component_id, name, role, stage_index, side, base in stage_specs:
        crop, box = crop_pair_component(sheet, stage_index, side)
        mask = resize_mask(crop, 0.33, name)
        require(base[0] >= SAFE_INSET and base[1] >= SAFE_INSET and
                base[0] + mask.width <= CANVAS[0] - SAFE_INSET and base[1] + mask.height <= CANVAS[1] - SAFE_INSET,
                f"V45 blink mask leaves safe inset: {name}")
        destination = mask_dir / f"{name}.pbm"
        mask.save(destination)
        components.append({"component_id": component_id, "name": name, "role": role, "source_pack": "v45_merged_special",
                           "source": {"kind": "imagegen_v45_complete_eye_pair_stage_connected_component_scaled", "sheet": rel(SOURCE),
                                      "sheet_sha256": SOURCE_SHA, "request": rel(REQUEST), "locked_v9_sha256": LOCKED,
                                      "crop_box_source": box, "threshold": 128, "scale": 0.33, "stage": name[9:],
                                      "paired_component_id": component_id + 1 if component_id % 2 == 1 else component_id - 1,
                                      "synchronized": True},
                           "mask": rel(destination), "mask_sha256": sha256(destination),
                           "base_position": base, "mask_size": [mask.width, mask.height],
                           "offset_range": {"min": [0, 0], "max": [0, 0]}, "z_index": 30, "composite_op": "ink",
                           "ink_pixels": ink_pixels(mask)})
    components.sort(key=lambda item: item["component_id"])
    require(len(components) == 56 and [item["component_id"] for item in components] ==
            [item["component_id"] for item in v44["components"]] + list(range(599, 605)),
            "V45 special component namespace drifted")
    crig = output / "companion-v9-v45-complete-eye-special-components-candidate-200x200.crig"
    pack = build_pack(crig, components)
    source_evidence = {"blink_transition": [{"name": name, "stage": name[9:], "component_id": component_id}
                                               for component_id, name, _, _, _, _ in stage_specs],
                       "open_reference_stages": ["open", "open_return"],
                       "stage_order": ["open", "closing", "closed", "opening", "open_return"]}
    layout = {
        "schema": "companion.v45_complete_eye_special_component_export.v1", "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "revision": REVISION, "authority": ["COMP-REQ-093", "COMP-REQ-256", "COMP-REQ-261", "COMP-REQ-267", "COMP-REQ-269"],
        "locked_v9_source": {"path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png", "sha256": LOCKED},
        "source_sheets": {"blink_transition": {"path": rel(SOURCE), "sha256": SOURCE_SHA, "request": rel(REQUEST),
                                                  "grid": [5, 1], "ordered_stages": ["open", "closing", "closed", "opening", "open_return"],
                                                  "exported_components": list(CELL_NAMES)}},
        "inherited_v44_special_layout": {"path": rel(V44_LAYOUT), "component_count": 50},
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "component_export_scope": "50 V44 special masks carried byte-identically plus 6 V45 complete-eye closing components; open stages remain the locked V22 face baseline and the V45 source is retained for transition provenance",
        "source_evidence": source_evidence, "components": components, "pack": pack,
        "non_claims": ["no_locked_v9_modification", "no_whole_face_card", "no_code_drawn_feature", "no_runtime_binding", "no_panel_or_driver_change", "no_human_acceptance"],
    }
    layout_path = output / "v45-special-component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.check:
        require(layout_path.is_file() and crig.is_file(), "V45 generated artifacts missing")
    print(f"PASS: generated inactive V45 special CRIG with 56 registered masks and six complete-eye transition components ({layout_path}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
