#!/usr/bin/env python3
"""Verify V24 source-component export remains a locked-V9, unbound candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GATE = ROOT / "docs/validation/companion-v24-glance-readable-special-expression-source-gate-20260720.json"
EXPORT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v24-glance-readable-special-expression-source/candidate/component-export-attempt-01"
LAYOUT = EXPORT / "component-layout.json"
REPORT = ROOT / "docs/validation/companion-v24-glance-readable-special-expression-component-export-gate-20260720.json"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
IDENTITY_NAMES = {
    "left_eye_open",
    "right_eye_open",
    "left_eye_highlight_open",
    "right_eye_highlight_open",
    "left_eye_sparkle_open",
    "right_eye_sparkle_open",
    "nose_default",
}
EXPECTED_COUNTS = {"menu_active": 8, "recording_active": 9, "charging_active": 7}
FORBIDDEN_SPECIAL_ROLES = {"left_eye", "right_eye", "left_highlight", "right_highlight", "left_sparkle", "right_sparkle", "nose"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def valid_mask(path: Path) -> bool:
    if not path.is_file():
        return False
    with Image.open(path) as raw:
        image = raw.convert("L")
    return image.width > 0 and image.height > 0 and any(value == 0 for value in image.getdata())


def main() -> int:
    errors: list[str] = []
    add(errors, SOURCE_GATE.is_file(), "V24 source gate artifact is missing")
    source_gate = load_json(SOURCE_GATE) if SOURCE_GATE.is_file() else {}
    add(errors, source_gate.get("status") == "PASS_V24_SPECIAL_SOURCE_GATE_PENDING_COMPONENT_EXPORT", "V24 source gate is not PASS")
    add(errors, source_gate.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "V24 source gate lost locked V9 hash")
    add(errors, LAYOUT.is_file(), "V24 component layout is missing")
    layout = load_json(LAYOUT) if LAYOUT.is_file() else {}
    add(errors, layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "V24 layout lost locked V9 hash")
    add(errors, layout.get("runtime_resource_activated") is False, "V24 layout unexpectedly activated runtime")
    add(errors, layout.get("active_candidate_binding") == "forbidden", "V24 layout permits a candidate binding")
    identity = layout.get("identity_components", {})
    add(errors, isinstance(identity, dict) and set(identity) == IDENTITY_NAMES, "V24 identity component set drifted")
    identity_checks: list[dict[str, object]] = []
    if isinstance(identity, dict):
        for name, record in identity.items():
            path = ROOT / str(record.get("mask", ""))
            valid = valid_mask(path)
            hash_matches = valid and sha256(path) == record.get("mask_sha256")
            add(errors, valid, f"V24 identity mask is invalid: {name}")
            add(errors, hash_matches, f"V24 identity mask hash drifted: {name}")
            add(errors, record.get("source") == "locked_v9_rig_v1_component", f"V24 identity source drifted: {name}")
            identity_checks.append({"name": name, "mask": record.get("mask"), "hash_matches": hash_matches})

    pose_checks: list[dict[str, object]] = []
    special = layout.get("special_pose_components", {})
    states = layout.get("states", {})
    add(errors, isinstance(special, dict) and set(special) == set(EXPECTED_COUNTS), "V24 special pose set drifted")
    for pose, expected_count in EXPECTED_COUNTS.items():
        records = special.get(pose, {}) if isinstance(special, dict) else {}
        state = states.get(pose, {}) if isinstance(states, dict) else {}
        add(errors, isinstance(records, dict) and len(records) == expected_count, f"{pose} component count drifted")
        component_checks: list[dict[str, object]] = []
        if isinstance(records, dict):
            for name, record in records.items():
                mask_path = ROOT / str(record.get("mask", ""))
                valid = valid_mask(mask_path)
                hash_matches = valid and sha256(mask_path) == record.get("mask_sha256")
                position = record.get("base_position", [])
                offset_range = record.get("offset_range", {})
                add(errors, valid, f"{pose} source mask is invalid: {name}")
                add(errors, hash_matches, f"{pose} source mask hash drifted: {name}")
                add(errors, record.get("source") == "v24_generated_source_thresholded_normalization", f"{pose} source is not V24: {name}")
                add(errors, record.get("role") not in FORBIDDEN_SPECIAL_ROLES, f"{pose} illegally exports locked identity role: {name}")
                add(errors, len(position) == 2 and all(isinstance(value, int) and 0 <= value < 200 for value in position), f"{pose} position out of range: {name}")
                add(errors, isinstance(offset_range, dict) and set(offset_range) == {"min", "max"}, f"{pose} offset range missing: {name}")
                component_checks.append({"name": name, "mask": record.get("mask"), "hash_matches": hash_matches, "role": record.get("role")})
        reassembly_path = ROOT / str(state.get("reassembly", "")) if isinstance(state, dict) else ROOT
        reassembly_valid = valid_mask(reassembly_path)
        reassembly_hash_matches = reassembly_valid and sha256(reassembly_path) == state.get("reassembly_sha256")
        add(errors, reassembly_valid, f"{pose} reassembly is invalid")
        add(errors, reassembly_hash_matches, f"{pose} reassembly hash drifted")
        add(errors, state.get("component_overlap_audit") == [], f"{pose} has source-component overlap")
        pose_checks.append(
            {
                "pose": pose,
                "expected_component_count": expected_count,
                "actual_component_count": len(records) if isinstance(records, dict) else None,
                "components": component_checks,
                "reassembly": state.get("reassembly") if isinstance(state, dict) else None,
                "reassembly_hash_matches": reassembly_hash_matches,
            }
        )

    result = {
        "schema": "companion.v24_glance_readable_special_expression_component_export_gate.v1",
        "status": "PASS_V24_SPECIAL_COMPONENT_EXPORT_UNBOUND" if not errors else "FAIL_V24_SPECIAL_COMPONENT_EXPORT",
        "source_gate": rel(SOURCE_GATE),
        "layout": rel(LAYOUT),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "identity": identity_checks,
        "poses": pose_checks,
        "required_next_stage": "component performance plan plus browser-target parity before owner art review",
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
    print("PASS: V24 special-expression component export is source-only, V9-identity locked, and unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
