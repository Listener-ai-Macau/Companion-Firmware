#!/usr/bin/env python3
"""Verify V25 component export stays V9-identity, mask-only and inactive."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
ITERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v25-representative-special-expression-source"
SOURCE_GATE = ROOT / "docs/validation/companion-v25-face-contrast-special-expression-source-gate-20260720.json"
LAYOUT = ITERATION / "candidate/component-export-attempt-01/component-layout.json"
EXPORT = ITERATION / "candidate/component-export-attempt-01/export-report.json"
REPORT = ROOT / "docs/validation/companion-v25-face-contrast-special-expression-component-export-gate-20260720.json"
POSES = ("menu_active", "recording_active", "charging_active")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def main() -> int:
    errors: list[str] = []
    source = load(SOURCE_GATE)
    layout = load(LAYOUT)
    export = load(EXPORT)
    if source.get("status") != "PASS_V25_FACE_CONTRAST_SOURCE_GATE_PENDING_COMPONENT_EXPORT":
        errors.append("V25 source gate is not PASS")
    if layout.get("locked_v9_source_sha256") != LOCKED_V9_SHA256:
        errors.append("V25 layout lost locked V9 hash")
    if layout.get("runtime_resource_activated") is not False or layout.get("active_candidate_binding") != "forbidden":
        errors.append("V25 layout is not inactive and unbound")
    if export.get("status") != "PASS_V25_FACE_CONTRAST_SOURCE_COMPONENT_EXPORT_UNBOUND":
        errors.append("V25 export report is not PASS")
    states = layout.get("states", {})
    special = layout.get("special_pose_components", {})
    if not isinstance(states, dict) or tuple(states) != POSES:
        errors.append("V25 exported state order changed")
    component_counts: dict[str, int] = {}
    for pose in POSES:
        records = special.get(pose, {}) if isinstance(special, dict) else {}
        if not isinstance(records, dict) or len(records) != 5:
            errors.append(f"{pose} does not have five face components")
            continue
        component_counts[pose] = len(records)
        required_roles = {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}
        actual_roles = {str(record.get("role", "")) for record in records.values() if isinstance(record, dict)}
        if actual_roles != required_roles:
            errors.append(f"{pose} component roles drifted: {actual_roles}")
        for name, record in records.items():
            if not isinstance(record, dict):
                errors.append(f"{pose} {name} record malformed")
                continue
            mask = ROOT / str(record.get("mask", ""))
            if not mask.is_file() or sha256(mask) != record.get("mask_sha256"):
                errors.append(f"{pose} {name} mask drifted")
            if record.get("source") != "v25_generated_source_thresholded_normalization":
                errors.append(f"{pose} {name} source is not an extracted component")
        state = states.get(pose, {}) if isinstance(states, dict) else {}
        reassembly = ROOT / str(state.get("reassembly", "")) if isinstance(state, dict) else ROOT
        if not reassembly.is_file() or sha256(reassembly) != state.get("reassembly_sha256"):
            errors.append(f"{pose} reassembly drifted")
    result = {
        "schema": "companion.v25_face_contrast_special_expression_component_export_gate.v1",
        "status": "PASS_V25_FACE_CONTRAST_COMPONENT_EXPORT_UNBOUND" if not errors else "FAIL_V25_FACE_CONTRAST_COMPONENT_EXPORT_GATE",
        "source_gate": rel(SOURCE_GATE),
        "layout": rel(LAYOUT),
        "export_report": rel(EXPORT),
        "component_counts": component_counts,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V25 component export retains only registered V9 identity and V25 face components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
