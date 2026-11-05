#!/usr/bin/env python3
"""Build an inactive merged special CRIG using existing locked V9 sleep masks."""

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
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
V9_MASKS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
SPECIAL_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate"
PACK_REVISION = 37
HEADER_BYTES = 80
INDEX_BYTES = 20
CANVAS = (200, 200)
SAFE_INSET = 8
SLEEP_COMPONENTS = (
    (539, "left_brow_sleepy"),
    (540, "right_brow_sleepy"),
    (541, "left_eye_sleepy"),
    (542, "right_eye_sleepy"),
    (543, "mouth_default"),
    (544, "charm_sleep_moon_z"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_mask_copy(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("1")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def build_components(output: Path) -> list[dict[str, Any]]:
    special = json.loads(SPECIAL_LAYOUT.read_text(encoding="utf-8"))
    v9 = json.loads(V9_LAYOUT.read_text(encoding="utf-8"))
    require(sha256(LOCKED_V9) == LOCKED_V9_SHA256 and
            special.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            v9.get("source_baseline", {}).get("sha256") == LOCKED_V9_SHA256,
            "locked V9 source lineage drifted")
    source_components = special.get("components")
    rig_components = {component.get("name"): component for component in v9.get("components", [])}
    require(isinstance(source_components, list) and len(source_components) == 39 and
            len(rig_components) == 24, "registered source component layouts drifted")
    result: list[dict[str, Any]] = []
    for source in source_components:
        require(isinstance(source, dict), "special source component is invalid")
        mask = ROOT / str(source.get("mask", ""))
        destination = output / "component-masks" / f"{source['name']}.pbm"
        require(mask.is_file() and sha256(mask) == source.get("mask_sha256"),
                f"special source mask lineage drifted: {source.get('name')}")
        write_mask_copy(mask, destination)
        result.append({
            **source,
            "source_pack": "v37_merged_special",
            "source": {"kind": "carried_forward_v34_v35_registered_mask", "prior_component_id": source["component_id"],
                       "prior_layout": rel(SPECIAL_LAYOUT), "prior_mask": str(source["mask"]),
                       "prior_mask_sha256": source["mask_sha256"]},
            "mask": rel(destination), "mask_sha256": sha256(destination),
        })
    for component_id, name in SLEEP_COMPONENTS:
        source = rig_components.get(name)
        mask = V9_MASKS / f"{name}.pbm"
        require(isinstance(source, dict) and mask.is_file(), f"locked V9 sleep component is unavailable: {name}")
        base = source.get("base_position")
        crop = source.get("crop_box")
        offset_range = source.get("offset_range")
        require(isinstance(base, list) and len(base) == 2 and isinstance(crop, list) and len(crop) == 4 and
                isinstance(offset_range, dict) and isinstance(offset_range.get("min"), list) and
                isinstance(offset_range.get("max"), list), f"locked V9 sleep geometry drifted: {name}")
        image = Image.open(mask).convert("1")
        width, height = image.size
        require([width, height] == crop[2:] and base[0] >= SAFE_INSET and base[1] >= SAFE_INSET and
                base[0] + width <= CANVAS[0] - SAFE_INSET and base[1] + height <= CANVAS[1] - SAFE_INSET,
                f"locked V9 sleep component escapes source geometry: {name}")
        destination = output / "component-masks" / f"v9_sleep_{name}.pbm"
        write_mask_copy(mask, destination)
        result.append({
            "name": f"v9_sleep_{name}", "component_id": component_id, "event": "sleepy_dream_cloud",
            "source_pack": "v37_merged_special",
            "source": {"kind": "locked_v9_registered_component", "path": rel(LOCKED_V9),
                       "sha256": LOCKED_V9_SHA256, "source_frame": source.get("source_frame"),
                       "rig_layout": rel(V9_LAYOUT), "registered_component": name,
                       "registered_mask": rel(mask), "registered_mask_sha256": sha256(mask),
                       "crop_box": crop},
            "mask": rel(destination), "mask_sha256": sha256(destination),
            "base_position": base, "mask_size": [width, height], "offset_range": offset_range,
            "z_index": source.get("z_index"), "composite_op": "ink",
        })
    ids = [component["component_id"] for component in result]
    require(len(result) == 45 and len(ids) == len(set(ids)) and ids == list(range(500, 545)),
            "merged V37 source component identifiers drifted")
    return result


def build_pack(output: Path, components: list[dict[str, Any]]) -> dict[str, Any]:
    index = bytearray()
    payload = bytearray()
    records = []
    data_offset = HEADER_BYTES + INDEX_BYTES * len(components)
    for component in components:
        image = Image.open(ROOT / str(component["mask"])).convert("1")
        width, height = image.size
        stride = (width + 7) // 8
        data = image.tobytes()
        require(len(data) == stride * height, f"PBM stride drifted: {component['name']}")
        offset = data_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        index.extend(struct.pack("<HHHHIII", component["component_id"], width, height, stride,
                                 offset, len(data), crc))
        payload.extend(data)
        records.append({"component_id": component["component_id"], "name": component["name"],
                        "width": width, "height": height, "stride_bytes": stride, "data_offset": offset,
                        "data_size": len(data), "data_crc32": f"{crc:08X}"})
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
    path = output / "companion-v9-sleepy-dream-rig-candidate-200x200.crig"
    path.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    return {"path": rel(path), "sha256": sha256(path), "revision": PACK_REVISION,
            "component_count": len(components), "total_size": total, "components": records}


def build_artifacts(output: Path) -> dict[Path, bytes]:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="sleepy-dream-build-", dir=output.parent))
    components = build_components(staging)
    pack = build_pack(staging, components)
    layout = {
        "schema": "companion.v37_sleepy_dream_component_export.v1",
        "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239"],
        "locked_v9_source": {"path": rel(LOCKED_V9), "sha256": LOCKED_V9_SHA256},
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "component_export_scope": "45 source masks: V34/V35 carried forward plus six locked-V9 sleepy face/charm components",
        "components": components, "pack": pack,
        "sleep_source": {"uses_new_image_generation": False,
                         "reason": "locked V9 source already registers the required sleepy face components"},
        "non_claims": ["no_locked_source_modification", "no_full_face_card", "no_code_drawn_face",
                       "no_runtime_binding", "no_panel_or_driver_change"],
    }

    staging_prefix = rel(staging)
    output_prefix = rel(output)

    def rebase(value: Any) -> Any:
        if isinstance(value, str):
            return output_prefix + value[len(staging_prefix):] if value.startswith(staging_prefix) else value
        if isinstance(value, list):
            return [rebase(item) for item in value]
        if isinstance(value, dict):
            return {key: rebase(item) for key, item in value.items()}
        return value

    layout = rebase(layout)
    layout_path = staging / "sleepy-dream-component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    artifacts = {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()}
    shutil.rmtree(staging)
    return {output / path: data for path, data in artifacts.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts(OUTPUT)
    if args.check:
        drifted = [path for path, data in artifacts.items() if not path.is_file() or path.read_bytes() != data]
        if drifted:
            for path in drifted:
                print(f"ERROR: generated artifact drifted: {rel(path)}")
            return 1
    else:
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        for path, data in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    action = "verified" if args.check else "generated"
    print(f"PASS: {action} inactive V37 merged special CRIG with 45 source masks including locked V9 sleepy face components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
