#!/usr/bin/env python3
"""Verify V22 emotion components remain source-only, separated, and unbound."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
V22_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source"
OUTPUT = V22_ROOT / "candidate/component-export-attempt-03"
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-source-gate-20260719.json"
ATTEMPT = V22_ROOT / "candidate/attempt-01-generated-emotion-separation.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v22-emotion-separation-component-export-gate-20260719.json"
EMOTIONS = ("calm", "curious", "warm", "playful", "puzzled", "alert")
IDENTITY_NAMES = {
    "left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open",
    "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default",
}
BASE_ROLES = {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}
REQUIRED_PROHIBITIONS = {
    "whole-source-pose playback", "whole-face replacement", "CRIG export", "runtime activation",
    "menu recording upgrade binding", "sleep charging error fallback",
}
MIN_REASSEMBLY_DISTANCE = 500
MAX_REASSEMBLY_DISTANCE = 1300


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def checked_path(value: object, errors: list[str], label: str) -> Path | None:
    if not isinstance(value, str):
        errors.append(f"{label} path is not a string")
        return None
    path = ROOT / value
    add(errors, path.is_file(), f"{label} is missing")
    return path if path.is_file() else None


def check_mask(record: dict[str, Any], errors: list[str], label: str, identity: bool) -> None:
    path = checked_path(record.get("mask"), errors, f"{label} mask")
    if path is None:
        return
    add(errors, path.suffix.lower() == ".pbm", f"{label} must be PBM")
    add(errors, sha256(path) == record.get("mask_sha256"), f"{label} mask hash drifted")
    with Image.open(path) as mask:
        add(errors, mask.size[0] > 0 and mask.size[1] > 0, f"{label} has empty dimensions")
    path_text = path.as_posix()
    if identity:
        add(errors, "companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components" in path_text,
            f"{label} must stay locked to V9 Rig v1")
    else:
        add(errors, "component-export-attempt-03/component-masks" in path_text,
            f"{label} must be an exported V22 source component")
        add(errors, "v17-functional-context" not in path_text and "extension-v10" not in path_text and
            "extension-v11" not in path_text and "extension-v21" not in path_text,
            f"{label} illegally references a forbidden art source")


def expected_roles(emotion: str) -> set[str]:
    roles = set(BASE_ROLES)
    if emotion == "puzzled":
        roles.remove("right_cheek")
    if emotion == "playful":
        roles.add("accent")
    return roles


def main() -> int:
    errors: list[str] = []
    source_gate = load_json(SOURCE_GATE)
    attempt = load_json(ATTEMPT)
    report = load_json(OUTPUT / "export-report.json")
    layout = load_json(OUTPUT / "everyday-emotion-component-layout.json")
    audit = load_json(OUTPUT / "component-occlusion-audit.json")

    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    add(errors, source_gate.get("status") == "PASS_V22_EMOTION_SEPARATION_SOURCE_GATE_PENDING_COMPONENT_EXPORT",
        "V22 source gate is not PASS")
    generated = checked_path(attempt.get("generated_image"), errors, "V22 generated source")
    if generated is not None:
        add(errors, sha256(generated) == attempt.get("generated_image_sha256"), "V22 generated source hash drifted")
    add(errors, attempt.get("source_reference_sha256") == LOCKED_V9_SHA256,
        "V22 generated source lost locked V9 lineage")

    add(errors, report.get("status") == "PASS_V22_EMOTION_SEPARATION_SOURCE_MASK_EXPORT_UNBOUND",
        "V22 source component export report is not an unbound PASS")
    add(errors, layout.get("schema") == "companion.v22_emotion_separation_component_source_layout.v1",
        "V22 component layout schema drifted")
    add(errors, layout.get("status") == "UNBOUND_CANDIDATE_PENDING_OWNER_ART_REVIEW_AND_COMPONENT_BRIDGE_GATE",
        "V22 component layout is not in its required inactive state")
    add(errors, layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
        layout.get("generated_source") == attempt.get("generated_image") and
        layout.get("generated_source_sha256") == attempt.get("generated_image_sha256"),
        "V22 component layout source lineage drifted")
    add(errors, layout.get("runtime_resource_activated") is False and
        layout.get("active_candidate_binding") == "forbidden" and
        report.get("runtime_resource_activated") is False and
        report.get("active_candidate_binding") == "forbidden",
        "V22 component export must remain runtime inactive and unbound")
    add(errors, REQUIRED_PROHIBITIONS <= set(layout.get("prohibited_before_component_bridge_gate", [])),
        "V22 component layout does not forbid premature use")
    add(errors, not list(OUTPUT.rglob("*.crig")), "V22 component export must not contain a CRIG")

    identity = layout.get("identity_components", {})
    add(errors, set(identity) == IDENTITY_NAMES, "V22 component layout does not use exactly the locked V9 identity set")
    for name, record in identity.items():
        add(errors, record.get("source") == "locked_v9_rig_v1_component" and
            record.get("group") == "locked_v9_identity", f"{name} is not locked V9 identity")
        check_mask(record, errors, name, identity=True)

    emotion_components = layout.get("emotion_components", {})
    states = layout.get("states", {})
    add(errors, set(emotion_components) == set(EMOTIONS) and set(states) == set(EMOTIONS),
        "V22 emotion vocabulary drifted")
    expected_counts: dict[str, int] = {}
    groups_by_emotion: dict[str, dict[str, str | None]] = {}
    for emotion in EMOTIONS:
        components = emotion_components.get(emotion, {})
        roles = expected_roles(emotion)
        actual_roles = {record.get("role") for record in components.values()}
        add(errors, actual_roles == roles, f"{emotion} source component roles drifted")
        add(errors, len(components) == len(roles), f"{emotion} source component count drifted")
        expected_counts[emotion] = len(roles)
        group_hashes: dict[str, str | None] = {role: None for role in BASE_ROLES | {"accent"}}
        for name, record in components.items():
            role = record.get("role")
            add(errors, name == f"v22_{emotion}__{role}", f"{emotion} component name drifted: {name}")
            add(errors, record.get("emotion") == emotion and
                record.get("source") == "v22_generated_source_panel_thresholded_crop", f"{name} source lineage drifted")
            add(errors, record.get("composite_op") == "ink" and isinstance(record.get("source_transform"), dict) and
                isinstance(record.get("source_grid_component"), dict), f"{name} component metadata is incomplete")
            position = record.get("base_position")
            add(errors, isinstance(position, list) and len(position) == 2 and
                all(isinstance(value, int) and 0 <= value < 200 for value in position), f"{name} base position is invalid")
            check_mask(record, errors, name, identity=False)
            if isinstance(role, str):
                group_hashes[role] = record.get("mask_sha256") if isinstance(record.get("mask_sha256"), str) else None
        state = states.get(emotion, {})
        absent_roles = state.get("source_absent_roles")
        expected_absent = ["right_cheek"] if emotion == "puzzled" else []
        add(errors, absent_roles == expected_absent, f"{emotion} source-absent component declaration drifted")
        add(errors, state.get("components") == list(components), f"{emotion} state/component registration drifted")
        reassembly = checked_path(state.get("reassembly"), errors, f"{emotion} reassembly")
        preview = checked_path(state.get("reassembly_preview"), errors, f"{emotion} reassembly preview")
        if reassembly is not None:
            with Image.open(reassembly) as image:
                add(errors, image.size == (200, 200), f"{emotion} reassembly dimensions drifted")
            add(errors, sha256(reassembly) == state.get("reassembly_sha256"), f"{emotion} reassembly hash drifted")
        if preview is not None:
            with Image.open(preview) as image:
                add(errors, image.size == (800, 800), f"{emotion} reassembly preview dimensions drifted")
        groups_by_emotion[emotion] = group_hashes

    add(errors, report.get("emotion_count") == len(EMOTIONS) and report.get("identity_component_count") == len(IDENTITY_NAMES),
        "V22 component export counts drifted")
    add(errors, report.get("emotion_component_counts") == expected_counts, "V22 reported component counts drifted")
    add(errors, audit.get("status") == "PASS_ZERO_COMPONENT_OVERLAP" and not audit.get("overlaps"),
        "V22 component export has overlapping source components")
    pairwise_pixels = audit.get("pairwise_reassembly_distances", [])
    add(errors, len(pairwise_pixels) == len(list(combinations(EMOTIONS, 2))), "V22 pixel distinction audit is incomplete")
    for pair in pairwise_pixels:
        pixels = pair.get("pixels")
        add(errors, isinstance(pixels, int) and MIN_REASSEMBLY_DISTANCE <= pixels <= MAX_REASSEMBLY_DISTANCE,
            f"V22 reassembly distinction outside source-derived range: {pair}")
    group_differences: list[dict[str, object]] = []
    for left, right in combinations(EMOTIONS, 2):
        changed_groups = sorted(role for role in BASE_ROLES | {"accent"}
                               if groups_by_emotion[left][role] != groups_by_emotion[right][role])
        add(errors, len(changed_groups) >= 2, f"{left}->{right} does not change two source component groups")
        group_differences.append({"left": left, "right": right, "changed_groups": changed_groups})
    add(errors, audit.get("source_pixels_only") is True and audit.get("runtime_resource_activated") is False,
        "V22 audit no longer proves source-only, inactive extraction")

    result = {
        "schema": "companion.v22_emotion_separation_component_export_gate.v1",
        "status": "PASS_V22_EMOTION_SEPARATION_COMPONENT_EXPORT_GATE" if not errors else
                  "FAIL_V22_EMOTION_SEPARATION_COMPONENT_EXPORT_GATE",
        "source_gate": SOURCE_GATE.relative_to(ROOT).as_posix(),
        "layout": (OUTPUT / "everyday-emotion-component-layout.json").relative_to(ROOT).as_posix(),
        "emotion_component_counts": expected_counts,
        "identity_component_count": len(identity),
        "pairwise_reassembly_distinction_range": {
            "min_pixels": MIN_REASSEMBLY_DISTANCE,
            "max_pixels": MAX_REASSEMBLY_DISTANCE,
        },
        "pairwise_component_group_differences": group_differences,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    DEFAULT_WRITE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V22 emotion components are V9-identity-locked, source-only, distinct, overlap-free and unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
