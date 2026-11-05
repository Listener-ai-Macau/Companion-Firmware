#!/usr/bin/env python3
"""Machine gate for V40 face-independent functional source-mask export."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V38 = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/function-state-component-layout.json"
V40 = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-rig-v2/candidate/functional-decoration-component-layout.json"
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-source-v2/generation-request-v2.json"
GENERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-source-v2/candidate/generation-output-v2.json"
REPORT = ROOT / "docs/validation/companion-v40-functional-decoration-component-export-gate-20260720.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must be an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def mask_bytes(path: Path, size: list[Any]) -> bytes:
    image = Image.open(path).convert("1")
    require([image.width, image.height] == size, f"mask size drifted: {rel(path)}")
    return image.tobytes()


def verify_pack(layout: dict[str, Any], components: list[dict[str, Any]]) -> dict[str, Any]:
    pack = layout.get("pack")
    require(isinstance(pack, dict), "V40 CRIG metadata missing")
    path = ROOT / str(pack.get("path", ""))
    data = path.read_bytes()
    require(len(data) >= 80 and data[:4] == b"CRIG", "V40 CRIG magic invalid")
    version, header_size = struct.unpack_from("<HH", data, 4)
    total_size, revision = struct.unpack_from("<II", data, 8)
    width, height, stride = struct.unpack_from("<HHH", data, 16)
    count = struct.unpack_from("<H", data, 24)[0]
    index_offset, data_offset, payload_crc, index_crc = struct.unpack_from("<IIII", data, 28)
    require((version, header_size, total_size, revision, width, height, stride, count, index_offset) ==
            (1, 80, len(data), 40, 200, 200, 25, 69, 80) and data[23] == 4 and data[44:76].hex().upper() == LOCKED,
            "V40 CRIG header identity drifted")
    require(data_offset == index_offset + count * 20 and zlib.crc32(data[index_offset:data_offset]) & 0xFFFFFFFF == index_crc and
            zlib.crc32(data[data_offset:]) & 0xFFFFFFFF == payload_crc, "V40 CRIG checksum drifted")
    by_id = {component["component_id"]: component for component in components}
    seen: list[int] = []
    for index in range(count):
        component_id, width, height, stride, offset, size, crc = struct.unpack_from("<HHHHIII", data, index_offset + index * 20)
        component = by_id.get(component_id)
        require(component is not None and component_id not in seen and offset + size <= len(data) and
                [width, height] == component.get("mask_size") and stride == (width + 7) // 8,
                "V40 CRIG index no longer matches registered component geometry")
        payload = data[offset:offset + size]
        require(payload == mask_bytes(ROOT / str(component["mask"]), component["mask_size"]) and
                zlib.crc32(payload) & 0xFFFFFFFF == crc, "V40 CRIG payload differs from source mask")
        seen.append(component_id)
    require(seen == list(range(500, 569)), "V40 CRIG order or coverage drifted")
    return {"path": rel(path), "sha256": sha256(path), "revision": revision, "component_count": count,
            "payload_crc32": f"{payload_crc:08X}", "index_crc32": f"{index_crc:08X}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request, generation, previous, layout = load(REQUEST), load(GENERATION), load(V38), load(V40)
    components = layout.get("components")
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            generation.get("status") == "CANDIDATE_SOURCE_GENERATED_PENDING_COMPONENT_EXPORT" and
            generation.get("candidate_source", {}).get("sha256") == layout.get("source_sheet", {}).get("sha256") and
            layout.get("schema") == "companion.v40_functional_decoration_component_export.v1" and
            layout.get("runtime_resource_activated") is False and layout.get("active_candidate_binding") == "forbidden" and
            isinstance(components, list) and len(components) == 69 and
            [component.get("component_id") for component in components] == list(range(500, 569)),
            "V40 source export activation, provenance or coverage drifted")
    previous_components = previous.get("components")
    require(isinstance(previous_components, list) and len(previous_components) == 57, "V38 carry source unavailable")
    carried: list[dict[str, Any]] = []
    for component, prior in zip(components[:57], previous_components):
        source = component.get("source")
        current_path = ROOT / str(component.get("mask", ""))
        prior_path = ROOT / str(prior.get("mask", ""))
        require(component.get("component_id") == prior.get("component_id") and isinstance(source, dict) and
                source.get("kind") == "carried_forward_v38_registered_mask" and source.get("prior_component_id") == prior.get("component_id") and
                source.get("prior_layout") == rel(V38) and current_path.is_file() and prior_path.is_file() and
                sha256(current_path) == sha256(prior_path) == component.get("mask_sha256") == prior.get("mask_sha256"),
                "V40 changed a carried V38 source mask")
        carried.append({"component_id": component["component_id"], "name": component["name"], "mask_sha256": component["mask_sha256"]})
    source_cells = layout.get("source_cells")
    require(isinstance(source_cells, list) and len(source_cells) == 12, "V40 source cell coverage drifted")
    expected = {
        557: ("recording_input", "recording_input_0"), 558: ("recording_input", "recording_input_1"), 559: ("recording_input", "recording_input_2"),
        560: ("bottom_connector_charging", "bottom_charge_0"), 561: ("bottom_connector_charging", "bottom_charge_1"), 562: ("bottom_connector_charging", "bottom_charge_2"),
        563: ("upgrade_progress", "upgrade_0"), 564: ("upgrade_progress", "upgrade_1"), 565: ("upgrade_progress", "upgrade_2"),
        566: ("error_caution", "error_0"), 567: ("error_caution", "error_1"), 568: ("error_caution", "error_2"),
    }
    generated: dict[str, list[dict[str, Any]]] = {"recording_input": [], "bottom_connector_charging": [], "upgrade_progress": [], "error_caution": []}
    cell_names = {entry.get("name") for entry in source_cells if isinstance(entry, dict)}
    for component in components[57:]:
        component_id = component.get("component_id")
        event, cell = expected.get(component_id, (None, None))
        source = component.get("source")
        mask = ROOT / str(component.get("mask", ""))
        base = component.get("base_position")
        size = component.get("mask_size")
        require(event is not None and isinstance(source, dict) and component.get("event") == event and component.get("role") == "charm" and
                source.get("kind") == "imagegen_v2_grid_cell_tight_crop_scaled" and source.get("sheet_sha256") == generation["candidate_source"]["sha256"] and
                source.get("request") == rel(REQUEST) and source.get("generation_manifest") == rel(GENERATION) and source.get("cell") == cell and cell in cell_names and
                source.get("threshold") == 128 and isinstance(source.get("scale"), float) and mask.is_file() and sha256(mask) == component.get("mask_sha256") and
                isinstance(base, list) and isinstance(size, list) and base[0] >= 4 and base[1] >= 4 and base[0] + size[0] <= 196 and base[1] + size[1] <= 196 and
                component.get("offset_range") == {"min": [0, 0], "max": [0, 0]} and component.get("z_index") == 90 and component.get("composite_op") == "ink" and
                component.get("ink_pixels", 0) > 8,
                "V40 generated functional component is not a legal face-independent source mask")
        generated[event].append({"component_id": component_id, "name": component["name"], "cell": cell,
                                 "mask_sha256": component["mask_sha256"], "mask_size": size, "ink_pixels": component["ink_pixels"]})
    require({name: [entry["component_id"] for entry in values] for name, values in generated.items()} ==
            {"recording_input": [557, 558, 559], "bottom_connector_charging": [560, 561, 562],
             "upgrade_progress": [563, 564, 565], "error_caution": [566, 567, 568]},
            "V40 functional source event mapping drifted")
    output = {
        "schema": "companion.v40_functional_decoration_component_export_gate.v1",
        "status": "PASS_COMPONENT_EXPORT_RUNTIME_INACTIVE",
        "locked_v9_source_sha256": LOCKED, "layout": rel(V40), "layout_sha256": sha256(V40),
        "carried_v38_components": carried, "generated_functional_components": generated, "crig": verify_pack(layout, components),
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "non_claims": ["no_full_face_card", "no_function_event_face_mutation", "no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"]
    }
    path = args.write.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: verified inactive V40 face-independent functional decoration source components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
