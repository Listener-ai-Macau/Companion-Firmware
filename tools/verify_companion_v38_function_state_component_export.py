#!/usr/bin/env python3
"""Machine gate for the inactive V38 Menu-entry, Upgrade and Error component export."""

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
V37_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/sleepy-dream-component-layout.json"
V38_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/function-state-component-layout.json"
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/generation-request-v1.json"
GENERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/candidate/generation-output-v1.json"
INTERPRETATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/candidate/choreography-interpretation-v2.json"
REPORT = ROOT / "docs/validation/companion-v38-function-state-component-export-gate-20260720.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def raw_mask(path: Path, expected_size: list[Any]) -> bytes:
    image = Image.open(path).convert("1")
    require([image.width, image.height] == expected_size, f"mask dimensions drifted: {rel(path)}")
    return image.tobytes()


def verify_pack(layout: dict[str, Any], components: list[dict[str, Any]]) -> dict[str, Any]:
    pack_info = layout.get("pack")
    require(isinstance(pack_info, dict), "V38 layout lacks CRIG metadata")
    path = ROOT / str(pack_info.get("path", ""))
    data = path.read_bytes()
    require(len(data) >= 80 and data[0:4] == b"CRIG", "V38 CRIG magic is invalid")
    version, header_size = struct.unpack_from("<HH", data, 4)
    total_size, revision = struct.unpack_from("<II", data, 8)
    width, height, stride = struct.unpack_from("<HHH", data, 16)
    count = struct.unpack_from("<H", data, 24)[0]
    index_offset, data_offset, payload_crc, index_crc = struct.unpack_from("<IIII", data, 28)
    require((version, header_size, total_size, revision, width, height, stride, count, index_offset) ==
            (1, 80, len(data), 38, 200, 200, 25, 57, 80) and data[23] == 8 and
            data[44:76].hex().upper() == LOCKED_V9_SHA256,
            "V38 CRIG header identity drifted")
    require(data_offset == index_offset + count * 20 and
            zlib.crc32(data[index_offset:data_offset]) & 0xFFFFFFFF == index_crc and
            zlib.crc32(data[data_offset:]) & 0xFFFFFFFF == payload_crc,
            "V38 CRIG index or payload checksum drifted")
    by_id = {int(component["component_id"]): component for component in components}
    seen: list[int] = []
    for index in range(count):
        position = index_offset + index * 20
        component_id, mask_width, mask_height, mask_stride, offset, size, crc = struct.unpack_from("<HHHHIII", data, position)
        component = by_id.get(component_id)
        require(component is not None and component_id not in seen and offset + size <= len(data) and
                [mask_width, mask_height] == component.get("mask_size") and mask_stride == (mask_width + 7) // 8,
                "V38 CRIG index no longer matches its registered components")
        payload = data[offset:offset + size]
        expected = raw_mask(ROOT / str(component["mask"]), component["mask_size"])
        require(payload == expected and len(payload) == mask_stride * mask_height and
                zlib.crc32(payload) & 0xFFFFFFFF == crc,
                f"V38 CRIG payload differs from registered source: {component['name']}")
        seen.append(component_id)
    require(seen == list(range(500, 557)), "V38 CRIG component order or coverage drifted")
    return {"path": rel(path), "sha256": sha256(path), "revision": revision, "component_count": count,
            "payload_crc32": f"{payload_crc:08X}", "index_crc32": f"{index_crc:08X}"}


def verify_carried(previous: list[dict[str, Any]], components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_by_id = {int(component["component_id"]): component for component in previous}
    output = []
    for component in components[:45]:
        source = component.get("source")
        component_id = component.get("component_id")
        expected = previous_by_id.get(component_id)
        current_mask = ROOT / str(component.get("mask", ""))
        prior_mask = ROOT / str(source.get("prior_mask", "")) if isinstance(source, dict) else Path()
        require(isinstance(source, dict) and expected is not None and source.get("kind") == "carried_forward_v37_registered_mask" and
                source.get("prior_component_id") == component_id and source.get("prior_layout") == rel(V37_LAYOUT) and
                prior_mask.is_file() and current_mask.is_file() and
                source.get("prior_mask_sha256") == expected.get("mask_sha256") == sha256(prior_mask) and
                component.get("mask_sha256") == source.get("prior_mask_sha256") == sha256(current_mask),
                f"V37 component changed while carried into V38: {component.get('name')}")
        output.append({"component_id": component_id, "name": component["name"], "mask_sha256": component["mask_sha256"]})
    return output


def verify_generated(layout: dict[str, Any], components: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    source_sheet = layout.get("source_sheet")
    snapshots = layout.get("source_cells")
    require(isinstance(source_sheet, dict) and isinstance(snapshots, list) and len(snapshots) == 9 and
            source_sheet.get("sha256") == sha256(ROOT / str(source_sheet.get("path", ""))) and
            source_sheet.get("request") == rel(REQUEST) and source_sheet.get("generation_manifest") == rel(GENERATION) and
            source_sheet.get("choreography_interpretation") == rel(INTERPRETATION) and source_sheet.get("dimensions") == [1254, 1254] and
            source_sheet.get("threshold") == 128,
            "V38 source-sheet provenance drifted")
    snapshot_by_name = {str(snapshot.get("name")): snapshot for snapshot in snapshots if isinstance(snapshot, dict)}
    require(set(snapshot_by_name) == {"menu_grid_0", "menu_grid_1", "menu_grid_2", "upgrade_rise_0", "upgrade_rise_1", "upgrade_rise_2",
                                      "error_caution_0", "error_caution_1", "error_caution_2"},
            "V38 canonical source-cell coverage drifted")
    for snapshot in snapshot_by_name.values():
        path = ROOT / str(snapshot.get("path", ""))
        image = Image.open(path).convert("1")
        require(path.is_file() and sha256(path) == snapshot.get("sha256") and image.size == (200, 200) and
                isinstance(snapshot.get("ink_pixels"), int) and snapshot["ink_pixels"] >= 700,
                "V38 source-cell snapshot is invalid")
    expected = {
        545: ("menu_entry", "charm", "menu_grid_0"), 546: ("menu_entry", "charm", "menu_grid_1"),
        547: ("menu_entry", "charm", "menu_grid_2"), 548: ("upgrade", "charm", "upgrade_rise_0"),
        549: ("upgrade", "charm", "upgrade_rise_1"), 550: ("upgrade", "charm", "upgrade_rise_2"),
        551: ("error", "charm", "error_caution_0"), 552: ("error", "charm", "error_caution_1"),
        553: ("error", "charm", "error_caution_2"), 554: ("error", "left_brow", "error_caution_1"),
        555: ("error", "right_brow", "error_caution_1"), 556: ("error", "mouth", "error_caution_1"),
    }
    by_event: dict[str, list[dict[str, Any]]] = {"menu_entry": [], "upgrade": [], "error": []}
    hashes: dict[str, set[str]] = {key: set() for key in by_event}
    for component in components[45:]:
        component_id = int(component.get("component_id", 0))
        source = component.get("source")
        event, role, cell = expected.get(component_id, (None, None, None))
        mask = ROOT / str(component.get("mask", ""))
        require(isinstance(source, dict) and event is not None and component.get("event") == event and component.get("role") == role and
                source.get("kind") == "imagegen_v1_canonical_cell_crop" and source.get("sheet_sha256") == source_sheet.get("sha256") and
                source.get("request") == rel(REQUEST) and source.get("generation_manifest") == rel(GENERATION) and
                source.get("locked_v9_sha256") == LOCKED_V9_SHA256 and source.get("cell") == cell and
                source.get("canonical_cell") == snapshot_by_name[cell].get("path") and
                source.get("canonical_cell_sha256") == snapshot_by_name[cell].get("sha256") and
                source.get("threshold") == 128 and mask.is_file() and sha256(mask) == component.get("mask_sha256") and
                component.get("composite_op") == "ink" and isinstance(component.get("ink_pixels"), int) and component["ink_pixels"] > 0,
                f"V38 generated component provenance drifted: {component.get('name')}")
        base = component.get("base_position")
        size = component.get("mask_size")
        offset = component.get("offset_range")
        require(isinstance(base, list) and isinstance(size, list) and len(base) == 2 and len(size) == 2 and
                isinstance(offset, dict) and offset.get("min")[0] == 0 and offset.get("max")[0] == 0 and
                base[0] >= 8 and base[1] >= 8 and base[0] + size[0] <= 192 and base[1] + size[1] <= 192,
                f"V38 generated component geometry drifts outside the registered safe canvas: {component.get('name')}")
        if component_id == 556:
            crop = source.get("crop_box_canonical")
            require(isinstance(crop, list) and crop[1] >= 124 and size[1] <= 10,
                    "V38 error mouth crop may not include the locked nose")
        hashes[event].add(component["mask_sha256"])
        by_event[event].append({"component_id": component_id, "name": component["name"], "role": role,
                                "cell": cell, "mask_sha256": component["mask_sha256"], "ink_pixels": component["ink_pixels"]})
    require([entry["component_id"] for entry in by_event["menu_entry"]] == [545, 546, 547] and len(hashes["menu_entry"]) == 3 and
            [entry["component_id"] for entry in by_event["upgrade"]] == [548, 549, 550] and len(hashes["upgrade"]) == 3 and
            [entry["component_id"] for entry in by_event["error"]] == [551, 552, 553, 554, 555, 556] and len(hashes["error"]) >= 4,
            "V38 state components no longer provide distinct source-derived progress frames")
    return by_event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    generation = json.loads(GENERATION.read_text(encoding="utf-8"))
    interpretation = json.loads(INTERPRETATION.read_text(encoding="utf-8"))
    previous = json.loads(V37_LAYOUT.read_text(encoding="utf-8"))
    layout = json.loads(V38_LAYOUT.read_text(encoding="utf-8"))
    components = layout.get("components")
    require(sha256(LOCKED_V9) == LOCKED_V9_SHA256 and request.get("locked_reference", {}).get("sha256") == LOCKED_V9_SHA256 and
            generation.get("candidate_sheet", {}).get("sha256") == "7A8B64F8735EF2A74F1CEB2502D029236D87EA026DFF96AE218B356E8B44E449" and
            interpretation.get("menu", {}).get("event") == "menu_entry_notice" and
            interpretation.get("menu", {}).get("maximum_expression_duration_ms") == 500 and
            interpretation.get("menu", {}).get("after_last_cue") == "withdraw_expression_rig_then_show_menu_ui" and
            layout.get("schema") == "companion.v38_function_state_component_export.v1" and
            layout.get("status") == "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING" and
            layout.get("runtime_resource_activated") is False and layout.get("active_candidate_binding") == "forbidden" and
            isinstance(components, list) and len(components) == 57 and
            [component.get("component_id") for component in components] == list(range(500, 557)),
            "V38 source candidate activation, scope or component coverage drifted")
    carried = verify_carried(previous.get("components", []), components)
    generated = verify_generated(layout, components)
    output = {
        "schema": "companion.v38_function_state_component_export_gate.v1",
        "status": "PASS_COMPONENT_EXPORT_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240"],
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "layout": rel(V38_LAYOUT), "layout_sha256": sha256(V38_LAYOUT),
        "carried_v37_components": carried, "generated_function_state_components": generated,
        "crig": verify_pack(layout, components),
        "menu_entry_policy": {"maximum_expression_duration_ms": 500,
                              "after_last_cue": "withdraw_expression_rig_then_show_menu_ui",
                              "persistent_menu_score": "forbidden"},
        "runtime": {"resource_activated": False, "active_candidate_binding": "forbidden",
                    "special_event_binding": "forbidden_until_total_machine_audit_and_owner_review"},
        "non_claims": ["no_complete_runtime_face_card", "no_menu_expression_behind_menu_ui", "no_runtime_binding",
                       "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"],
    }
    path = args.write.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: verified inactive V38 source components, including one-shot Menu entry and source-derived Upgrade/Error masks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
