#!/usr/bin/env python3
"""Verify V17 source-mask export without authorizing any functional binding."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
V17_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v17-functional-context-accents"
SOURCE_GATE = ROOT / "docs/validation/companion-v9-extension-v17-functional-context-source-20260719.json"
DEFAULT_EXPORT = V17_ROOT / "candidate/component-export-attempt-01/export-report.json"
EXPECTED_GROUPS = {
    "menu_active": {"menu_dot_top", "menu_dot_middle", "menu_dot_bottom"},
    "recording_active": {
        "recording_ripple_left_outer", "recording_ripple_left_inner",
        "recording_ripple_right_inner", "recording_ripple_right_outer",
    },
    "upgrade_active": {
        "upgrade_segment_top", "upgrade_segment_right", "upgrade_segment_bottom", "upgrade_segment_left",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ink_count(path: Path) -> int:
    image = Image.open(path).convert("1")
    return sum(pixel == 0 for pixel in image.getdata())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    errors: list[str] = []
    component_metrics: dict[str, dict[str, Any]] = {}
    group_metrics: dict[str, dict[str, int]] = {}
    try:
        source_gate = json.loads(SOURCE_GATE.read_text(encoding="utf-8"))
        if source_gate.get("status") != "PASS_V17_FUNCTIONAL_CONTEXT_SOURCE_GATE":
            errors.append("V17 source gate has not passed")
        export_path = args.export.resolve()
        export = json.loads(export_path.read_text(encoding="utf-8"))
        if export.get("schema") != "companion.v17_functional_context_component_source_export.v1" or \
                export.get("status") != "PASS_V17_FUNCTIONAL_CONTEXT_SOURCE_MASK_EXPORT_UNBOUND":
            errors.append("V17 component export disposition drifted")
        if export.get("runtime_resource_activated") is not False or export.get("active_candidate_binding") != "forbidden":
            errors.append("V17 source export illegally activates a runtime candidate")
        layout_path = ROOT / str(export.get("layout", ""))
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        if layout.get("schema") != "companion.v17_functional_context_component_source_layout.v1" or \
                layout.get("status") != "UNBOUND_PENDING_OWNER_ART_REVIEW":
            errors.append("V17 source layout disposition drifted")
        if layout.get("canvas") != [200, 200] or layout.get("runtime_resource_activated") is not False or \
                layout.get("active_candidate_binding") != "forbidden":
            errors.append("V17 source layout canvas or inactive contract drifted")
        if set(layout.get("context_groups", {})) != set(EXPECTED_GROUPS) or \
                any(set(layout["context_groups"].get(group, [])) != names for group, names in EXPECTED_GROUPS.items()):
            errors.append("V17 source layout group vocabulary drifted")
        forbidden = set(layout.get("prohibited_before_owner_art_review", []))
        if not {"face binding", "event choreography", "external NOR CRIG export", "runtime activation"}.issubset(forbidden):
            errors.append("V17 source layout does not keep feature binding gated")
        components = layout.get("components", {})
        if set(components) != set().union(*EXPECTED_GROUPS.values()) or export.get("component_count") != 11:
            errors.append("V17 source component count or vocabulary drifted")
        source_crops: list[tuple[int, int, int, int]] = []
        for name, component in components.items():
            if not isinstance(component, dict):
                errors.append(f"V17 component record is invalid: {name}")
                continue
            mask_path = ROOT / str(component.get("mask", ""))
            preview_path = ROOT / str(component.get("preview_layer", ""))
            crop = component.get("source_crop")
            if not isinstance(crop, list) or len(crop) != 4 or not all(isinstance(value, int) for value in crop):
                errors.append(f"V17 source crop is invalid: {name}")
                continue
            source_crops.append(tuple(crop))
            if not mask_path.is_file() or component.get("mask_sha256") != sha256(mask_path):
                errors.append(f"V17 mask hash drifted: {name}")
                continue
            if not preview_path.is_file() or component.get("preview_layer_sha256") != sha256(preview_path):
                errors.append(f"V17 preview-layer hash drifted: {name}")
                continue
            mask = Image.open(mask_path).convert("1")
            preview = Image.open(preview_path).convert("RGBA")
            target_size = component.get("target_size")
            if target_size != [mask.width, mask.height] or preview.size != mask.size or ink_count(mask_path) <= 0:
                errors.append(f"V17 component export geometry is invalid: {name}")
                continue
            component_metrics[name] = {"target_size": target_size, "ink_pixels": ink_count(mask_path)}
        for index, first in enumerate(source_crops):
            for second in source_crops[index + 1:]:
                if max(first[0], second[0]) < min(first[2], second[2]) and \
                        max(first[1], second[1]) < min(first[3], second[3]):
                    errors.append("V17 source crops overlap before any component binding")
        for group, names in EXPECTED_GROUPS.items():
            reassembly_path = ROOT / str(layout.get("source_only_reassemblies", {}).get(group, ""))
            if not reassembly_path.is_file() or Image.open(reassembly_path).size != (200, 200):
                errors.append(f"V17 source-only reassembly is missing: {group}")
                continue
            component_ink = sum(component_metrics.get(name, {}).get("ink_pixels", 0) for name in names)
            reassembly_ink = ink_count(reassembly_path)
            group_metrics[group] = {"component_ink_pixels": component_ink, "reassembly_ink_pixels": reassembly_ink}
            if component_ink <= 0 or component_ink != reassembly_ink:
                errors.append(f"V17 source-only reassembly overlaps or omits a component: {group}")
        contact_path = ROOT / str(layout.get("contact_sheet", ""))
        if not contact_path.is_file() or Image.open(contact_path).size != (600, 200):
            errors.append("V17 source-only contact sheet is missing or malformed")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(str(exc))
    result = {
        "schema": "companion.v17_functional_context_component_export_gate.v1",
        "status": "PASS_V17_FUNCTIONAL_CONTEXT_COMPONENT_EXPORT_UNBOUND" if not errors else
                  "FAIL_V17_FUNCTIONAL_CONTEXT_COMPONENT_EXPORT",
        "component_metrics": component_metrics,
        "group_metrics": group_metrics,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "next_gate": "canonical_owner_art_review_before_face_binding_or_event_choreography",
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V17 functional-context masks reassemble exactly as unbound source components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
