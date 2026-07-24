#!/usr/bin/env python3
"""Prove the inactive V37 sleepy-dream CRIG is sourced only from registered masks."""

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
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V34_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
V37_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/sleepy-dream-component-layout.json"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v37-sleepy-dream-component-export-gate-20260720.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def raw_mask(path: Path, expected_size: list[Any]) -> bytes:
    image = Image.open(path).convert("1")
    require([image.width, image.height] == expected_size,
            f"registered mask dimensions drifted: {rel(path)}")
    return image.tobytes()


def verify_v34_carried_forward(component: dict[str, Any], v34_by_id: dict[int, dict[str, Any]]) -> dict[str, Any]:
    source = component.get("source")
    component_id = component.get("component_id")
    require(isinstance(source, dict) and source.get("kind") == "carried_forward_v34_v35_registered_mask" and
            isinstance(component_id, int) and component_id in v34_by_id and
            source.get("prior_component_id") == component_id,
            f"V34/V35 carry-forward lineage drifted: {component.get('name')}")
    previous = v34_by_id[component_id]
    previous_mask = ROOT / str(source.get("prior_mask", ""))
    current_mask = ROOT / str(component.get("mask", ""))
    require(previous_mask.is_file() and current_mask.is_file() and
            source.get("prior_layout") == rel(V34_LAYOUT) and
            source.get("prior_mask_sha256") == previous.get("mask_sha256") and
            source.get("prior_mask_sha256") == sha256(previous_mask) and
            component.get("mask_sha256") == sha256(current_mask) and
            component.get("mask_sha256") == source.get("prior_mask_sha256") and
            component.get("base_position") == previous.get("base_position") and
            component.get("mask_size") == previous.get("mask_size") and
            component.get("offset_range") == previous.get("offset_range") and
            component.get("z_index") == previous.get("z_index") and
            component.get("composite_op") == previous.get("composite_op"),
            f"V34/V35 carried component changed during V37 export: {component.get('name')}")
    return {"component_id": component_id, "name": component["name"], "lineage": "v34_v35_carried_forward",
            "mask_sha256": component["mask_sha256"]}


def verify_locked_v9_sleep(component: dict[str, Any]) -> dict[str, Any]:
    source = component.get("source")
    require(isinstance(source, dict) and source.get("kind") == "locked_v9_registered_component" and
            source.get("path") == rel(LOCKED_V9) and source.get("sha256") == LOCKED_V9_SHA256 and
            isinstance(source.get("registered_component"), str),
            f"locked V9 sleep lineage drifted: {component.get('name')}")
    registered = ROOT / str(source.get("registered_mask", ""))
    current = ROOT / str(component.get("mask", ""))
    expected = "v9_sleep_" + source["registered_component"]
    require(registered.is_file() and current.is_file() and component.get("name") == expected and
            source.get("registered_mask_sha256") == sha256(registered) and
            component.get("mask_sha256") == sha256(current) and
            component.get("mask_sha256") == source.get("registered_mask_sha256") and
            component.get("composite_op") == "ink" and component.get("source_pack") == "v37_merged_special",
            f"locked V9 sleep component was changed during V37 export: {component.get('name')}")
    return {"component_id": component["component_id"], "name": component["name"],
            "lineage": "locked_v9_registered_component", "registered_component": source["registered_component"],
            "mask_sha256": component["mask_sha256"]}


def verify_crig(layout: dict[str, Any]) -> dict[str, Any]:
    pack_info = layout.get("pack")
    components = layout.get("components")
    require(isinstance(pack_info, dict) and isinstance(components, list), "V37 layout lacks CRIG metadata")
    pack = ROOT / str(pack_info.get("path", ""))
    data = pack.read_bytes()
    require(len(data) >= 80 and data[0:4] == b"CRIG", "V37 CRIG magic is invalid")
    version, header_bytes = struct.unpack_from("<HH", data, 4)
    total_bytes, revision = struct.unpack_from("<II", data, 8)
    width, height, stride = struct.unpack_from("<HHH", data, 16)
    component_count = struct.unpack_from("<H", data, 24)[0]
    index_offset, data_offset, payload_crc, index_crc = struct.unpack_from("<IIII", data, 28)
    require((version, header_bytes, total_bytes, revision, width, height, stride, component_count, index_offset) ==
            (1, 80, len(data), 37, 200, 200, 25, 45, 80) and data[23] == 8 and
            data[44:76].hex().upper() == LOCKED_V9_SHA256,
            "V37 CRIG header identity drifted")
    require(data_offset == index_offset + component_count * 20 and
            zlib.crc32(data[index_offset:data_offset]) & 0xFFFFFFFF == index_crc and
            zlib.crc32(data[data_offset:]) & 0xFFFFFFFF == payload_crc,
            "V37 CRIG index or payload checksum drifted")
    by_id = {int(component["component_id"]): component for component in components}
    require(len(by_id) == 45, "V37 component namespace is not unique")
    observed: list[int] = []
    for index in range(component_count):
        record = index_offset + index * 20
        component_id, mask_width, mask_height, mask_stride, offset, size, crc = struct.unpack_from("<HHHHIII", data, record)
        component = by_id.get(component_id)
        require(component is not None and component_id not in observed and
                [mask_width, mask_height] == component.get("mask_size") and
                mask_stride == (mask_width + 7) // 8 and offset + size <= len(data),
                "V37 CRIG index no longer matches the component layout")
        payload = data[offset:offset + size]
        expected = raw_mask(ROOT / str(component["mask"]), component["mask_size"])
        require(payload == expected and len(payload) == mask_stride * mask_height and
                zlib.crc32(payload) & 0xFFFFFFFF == crc,
                f"V37 CRIG payload differs from its registered source mask: {component['name']}")
        observed.append(component_id)
    require(observed == list(range(500, 545)), "V37 CRIG component order or coverage drifted")
    return {"path": rel(pack), "sha256": sha256(pack), "revision": revision, "component_count": component_count,
            "payload_crc32": f"{payload_crc:08X}", "index_crc32": f"{index_crc:08X}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    v34 = json.loads(V34_LAYOUT.read_text(encoding="utf-8"))
    layout = json.loads(V37_LAYOUT.read_text(encoding="utf-8"))
    require(sha256(LOCKED_V9) == LOCKED_V9_SHA256 and
            v34.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            layout.get("schema") == "companion.v37_sleepy_dream_component_export.v1" and
            layout.get("status") == "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING" and
            layout.get("locked_v9_source", {}).get("sha256") == LOCKED_V9_SHA256 and
            layout.get("runtime_resource_activated") is False and layout.get("active_candidate_binding") == "forbidden" and
            layout.get("sleep_source", {}).get("uses_new_image_generation") is False,
            "V37 export is not an inactive locked-V9 source-component candidate")
    v34_components = v34.get("components")
    components = layout.get("components")
    require(isinstance(v34_components, list) and len(v34_components) == 39 and
            isinstance(components, list) and len(components) == 45,
            "V37 component source coverage drifted")
    v34_by_id = {int(component["component_id"]): component for component in v34_components}
    carried = [verify_v34_carried_forward(component, v34_by_id) for component in components[:39]]
    sleep = [verify_locked_v9_sleep(component) for component in components[39:]]
    require([entry["component_id"] for entry in carried] == list(range(500, 539)) and
            [entry["component_id"] for entry in sleep] == list(range(539, 545)),
            "V37 carried/sleep component ranges drifted")
    output = {
        "schema": "companion.v37_sleepy_dream_component_export_gate.v1",
        "status": "PASS_COMPONENT_EXPORT_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239"],
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "layout": rel(V37_LAYOUT),
        "layout_sha256": sha256(V37_LAYOUT),
        "source_component_lineage": {"v34_v35_carried_forward": carried, "locked_v9_sleep": sleep},
        "crig": verify_crig(layout),
        "runtime": {"resource_activated": False, "active_candidate_binding": "forbidden",
                    "special_event_binding": "forbidden_until_machine_and_owner_gates"},
        "non_claims": ["no_new_image_generation", "no_full_face_card", "no_code_drawn_face",
                       "no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"],
    }
    report = args.write.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: verified V37 CRIG carries 39 unchanged V34/V35 masks and six locked-V9 sleep components while runtime remains inactive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
