#!/usr/bin/env python3
"""Verify V21 accepted everyday emotion components remain source-only and unbound."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
V21_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source"
OUTPUT = V21_ROOT / "candidate/component-export-attempt-01"
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_GATE = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-source-gate-20260719.json"
OWNER_REVIEW = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-owner-art-review-20260719.json"
OWNER_NOTE = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-owner-art-review-20260719.note.txt"
ATTEMPT = V21_ROOT / "candidate/attempt-01-generated-everyday-emotion-distinction.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-component-export-gate-20260719.json"
EMOTIONS = ("calm", "curious", "warm", "playful", "puzzled", "alert")
IDENTITY_NAMES = {
    "left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open",
    "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default",
}
ROLE_NAMES = {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}
REQUIRED_PROHIBITIONS = {
    "whole-source-pose playback", "whole-face replacement", "CRIG export", "runtime activation",
    "menu recording upgrade binding", "sleep charging error fallback",
}
MIN_REASSEMBLY_DISTANCE = 250
MAX_REASSEMBLY_DISTANCE = 1000


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
        add(errors, "component-export-attempt-01/component-masks" in path_text,
            f"{label} must be an exported V21 source component")
        add(errors, "v17-functional-context" not in path_text and "extension-v10" not in path_text and
            "extension-v11" not in path_text, f"{label} illegally references superseded art")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, default=DEFAULT_WRITE)
    args = parser.parse_args()

    errors: list[str] = []
    source_gate = load_json(SOURCE_GATE)
    owner_review = load_json(OWNER_REVIEW)
    attempt = load_json(ATTEMPT)
    report = load_json(OUTPUT / "export-report.json")
    layout = load_json(OUTPUT / "everyday-emotion-component-layout.json")
    audit = load_json(OUTPUT / "component-occlusion-audit.json")

    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    add(errors, source_gate.get("status") == "PASS_V21_EVERYDAY_EMOTION_DISTINCTION_SOURCE_GATE_PENDING_OWNER_ART_REVIEW",
        "V21 source gate is not PASS")
    add(errors, owner_review.get("status") == "PASS_OWNER_V21_EVERYDAY_EMOTION_ART_ACCEPTED_PENDING_COMPONENT_EXPORT" and
        owner_review.get("selected") == "通过", "V21 owner source-art acceptance is missing")
    add(errors, OWNER_NOTE.is_file() and OWNER_NOTE.read_text(encoding="utf-8").strip() == "可以的, 方向是对的",
        "V21 owner acceptance note drifted")
    generated = checked_path(attempt.get("generated_image"), errors, "V21 generated source")
    if generated is not None:
        add(errors, sha256(generated) == attempt.get("generated_image_sha256"), "V21 generated source hash drifted")
    add(errors, attempt.get("source_reference_sha256") == LOCKED_V9_SHA256,
        "V21 generated source lost locked V9 lineage")

    add(errors, report.get("status") == "PASS_ACCEPTED_EVERYDAY_EMOTION_SOURCE_MASK_EXPORT_UNBOUND",
        "V21 source component export report is not an unbound PASS")
    add(errors, layout.get("schema") == "companion.v21_everyday_emotion_component_source_layout.v1",
        "V21 component layout schema drifted")
    add(errors, layout.get("status") == "UNBOUND_ACCEPTED_SOURCE_PENDING_COMPONENT_BRIDGE_GATE",
        "V21 component layout is not bridge-gate pending")
    add(errors, layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256,
        "V21 component layout lost locked V9 lineage")
    add(errors, layout.get("generated_source") == attempt.get("generated_image") and
        layout.get("generated_source_sha256") == attempt.get("generated_image_sha256"),
        "V21 component layout generated-source lineage drifted")
    add(errors, layout.get("runtime_resource_activated") is False and
        layout.get("active_candidate_binding") == "forbidden" and
        report.get("runtime_resource_activated") is False and
        report.get("active_candidate_binding") == "forbidden",
        "V21 component export must remain runtime inactive and unbound")
    add(errors, REQUIRED_PROHIBITIONS <= set(layout.get("prohibited_before_component_bridge_gate", [])),
        "V21 component layout does not forbid premature use")
    add(errors, not list(OUTPUT.rglob("*.crig")), "V21 component export must not contain a CRIG")

    identity = layout.get("identity_components", {})
    add(errors, set(identity) == IDENTITY_NAMES, "V21 component layout does not use exactly the locked V9 identity set")
    for name, record in identity.items():
        add(errors, record.get("source") == "locked_v9_rig_v1_component" and
            record.get("group") == "locked_v9_identity", f"{name} is not locked V9 identity")
        check_mask(record, errors, name, identity=True)

    emotion_components = layout.get("emotion_components", {})
    states = layout.get("states", {})
    add(errors, set(emotion_components) == set(EMOTIONS) and set(states) == set(EMOTIONS),
        "V21 emotion vocabulary drifted")
    expected_counts: dict[str, int] = {}
    reassemblies: dict[str, Path] = {}
    for emotion in EMOTIONS:
        components = emotion_components.get(emotion, {})
        expected_roles = set(ROLE_NAMES)
        if emotion == "playful":
            expected_roles.add("accent")
        actual_roles = {record.get("role") for record in components.values()}
        add(errors, actual_roles == expected_roles, f"{emotion} source component roles drifted")
        add(errors, len(components) == len(expected_roles), f"{emotion} source component count drifted")
        expected_counts[emotion] = len(expected_roles)
        for name, record in components.items():
            add(errors, name == f"v21_{emotion}__{record.get('role')}", f"{emotion} component name drifted: {name}")
            add(errors, record.get("emotion") == emotion and
                record.get("source") == "v21_generated_source_panel_thresholded_crop", f"{name} source lineage drifted")
            add(errors, record.get("composite_op") == "ink" and isinstance(record.get("source_transform"), dict) and
                isinstance(record.get("source_grid_component"), dict), f"{name} component metadata is incomplete")
            position = record.get("base_position")
            add(errors, isinstance(position, list) and len(position) == 2 and
                all(isinstance(value, int) and 0 <= value < 200 for value in position), f"{name} base position is invalid")
            check_mask(record, errors, name, identity=False)
        state = states.get(emotion, {})
        add(errors, state.get("components") == list(components), f"{emotion} state/component registration drifted")
        reassembly = checked_path(state.get("reassembly"), errors, f"{emotion} reassembly")
        preview = checked_path(state.get("reassembly_preview"), errors, f"{emotion} reassembly preview")
        if reassembly is not None:
            with Image.open(reassembly) as image:
                add(errors, image.size == (200, 200), f"{emotion} reassembly dimensions drifted")
            add(errors, sha256(reassembly) == state.get("reassembly_sha256"), f"{emotion} reassembly hash drifted")
            reassemblies[emotion] = reassembly
        if preview is not None:
            with Image.open(preview) as image:
                add(errors, image.size == (800, 800), f"{emotion} reassembly preview dimensions drifted")

    add(errors, report.get("emotion_count") == len(EMOTIONS) and report.get("identity_component_count") == len(IDENTITY_NAMES),
        "V21 component export counts drifted")
    add(errors, report.get("emotion_component_counts") == expected_counts, "V21 reported component counts drifted")
    add(errors, audit.get("status") == "PASS_ZERO_COMPONENT_OVERLAP" and not audit.get("overlaps"),
        "V21 component export has overlapping source components")
    pairwise = audit.get("pairwise_reassembly_distances", [])
    add(errors, len(pairwise) == len(list(combinations(EMOTIONS, 2))), "V21 pairwise distinction audit is incomplete")
    for pair in pairwise:
        pixels = pair.get("pixels")
        add(errors, isinstance(pixels, int) and MIN_REASSEMBLY_DISTANCE <= pixels <= MAX_REASSEMBLY_DISTANCE,
            f"V21 reassembly distinction outside source-derived range: {pair}")
    add(errors, audit.get("source_pixels_only") is True and audit.get("runtime_resource_activated") is False,
        "V21 audit no longer proves source-only, inactive extraction")

    result = {
        "schema": "companion.v21_everyday_emotion_component_export_gate.v1",
        "status": "PASS_V21_EVERYDAY_EMOTION_COMPONENT_EXPORT_GATE" if not errors else
                  "FAIL_V21_EVERYDAY_EMOTION_COMPONENT_EXPORT_GATE",
        "source_gate": SOURCE_GATE.relative_to(ROOT).as_posix(),
        "owner_art_review": OWNER_REVIEW.relative_to(ROOT).as_posix(),
        "layout": (OUTPUT / "everyday-emotion-component-layout.json").relative_to(ROOT).as_posix(),
        "emotion_component_counts": expected_counts,
        "identity_component_count": len(identity),
        "pairwise_reassembly_distinction_range": {
            "min_pixels": MIN_REASSEMBLY_DISTANCE,
            "max_pixels": MAX_REASSEMBLY_DISTANCE,
        },
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V21 emotion components are V9-identity-locked, source-only, distinct, overlap-free and unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
