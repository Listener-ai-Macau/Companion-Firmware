#!/usr/bin/env python3
"""Verify the unbound V18-V20 complete special-expression component exports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from verify_companion_v18_v20_special_expression_sources import SPECS


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GATE = ROOT / "docs/validation/companion-v18-v20-special-expression-source-gate-20260719.json"
EXPORT_SUMMARY = ROOT / "docs/validation/companion-v18-v20-special-expression-component-export-20260719.json"
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
IDENTITY_NAMES = {
    "left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open",
    "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default",
}
EXPECTED_SPECIAL_COUNTS = {"menu_active": 8, "recording_active": 9, "upgrade_active": 9}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def check_mask(path_value: str, expected_hash: str | None, errors: list[str], label: str, source_kind: str) -> None:
    path = ROOT / path_value
    add(errors, path.is_file(), f"{label} mask is missing")
    if not path.is_file():
        return
    add(errors, path.suffix.lower() == ".pbm", f"{label} must be a PBM mask")
    if source_kind == "identity":
        add(errors, "companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components" in path.as_posix(),
            f"{label} must remain a V9 Rig v1 component")
    else:
        add(errors, "component-masks" in path.parts, f"{label} must remain under component-masks")
    add(errors, "v17-functional-context" not in path.as_posix(), f"{label} must not reference superseded V17")
    if expected_hash:
        add(errors, sha256(path) == expected_hash, f"{label} mask hash drifted")


def verify_one(function: str, spec: dict[str, str], errors: list[str]) -> dict[str, Any]:
    iteration_root = ROOT / "docs/art/iterations" / spec["iteration"]
    output = iteration_root / "candidate/component-export-attempt-01"
    attempt = read_json(iteration_root / "candidate" / spec["attempt"])
    report = read_json(output / "export-report.json")
    layout = read_json(output / "complete-special-expression-component-layout.json")
    audit = read_json(output / "component-occlusion-audit.json")

    add(errors, attempt.get("status") == "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT",
        f"{function} attempt is not source-gated for component export")
    source_path = ROOT / str(attempt.get("generated_image", ""))
    add(errors, source_path.is_file(), f"{function} generated source is missing")
    if source_path.is_file():
        add(errors, sha256(source_path) == attempt.get("generated_image_sha256"), f"{function} source hash drifted")
    add(errors, report.get("status") == "PASS_COMPLETE_SPECIAL_EXPRESSION_SOURCE_MASK_EXPORT_UNBOUND",
        f"{function} export report is not unbound PASS")
    add(errors, report.get("function") == function and layout.get("function") == function,
        f"{function} export identity drifted")
    add(errors, layout.get("status") == "UNBOUND_PENDING_OWNER_ART_REVIEW",
        f"{function} layout is not owner-review pending")
    add(errors, layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256,
        f"{function} locked V9 source hash drifted")
    add(errors, layout.get("generated_source") == attempt.get("generated_image") and
        layout.get("generated_source_sha256") == attempt.get("generated_image_sha256"),
        f"{function} generated source lineage drifted")
    add(errors, layout.get("runtime_resource_activated") is False and
        layout.get("active_candidate_binding") == "forbidden",
        f"{function} must remain runtime inactive and unbound")
    prohibited = set(layout.get("prohibited_before_owner_art_review", []))
    add(errors, {"whole-source-pose playback", "event choreography", "CRIG export", "runtime activation"} <= prohibited,
        f"{function} layout does not forbid pre-review use")

    identity = layout.get("identity_components", {})
    add(errors, set(identity) == IDENTITY_NAMES, f"{function} must use exactly the locked V9 identity vocabulary")
    for name, record in identity.items():
        add(errors, record.get("source") == "locked_v9_rig_v1_component" and
            record.get("group") == "locked_v9_identity", f"{function} {name} is not a locked V9 identity component")
        check_mask(str(record.get("mask", "")), record.get("mask_sha256"), errors, f"{function} {name}", "identity")

    special = layout.get("special_expression_components", {})
    add(errors, len(special) == EXPECTED_SPECIAL_COUNTS[function], f"{function} special component count drifted")
    expected_prefix = f"{spec['version']}_{function}__"
    seen_masks: set[str] = set()
    for name, record in special.items():
        add(errors, name.startswith(expected_prefix), f"{function} special component name drifted: {name}")
        add(errors, record.get("source") == "generated_complete_special_pose", f"{function} {name} source is invalid")
        add(errors, record.get("group") in {"expression", "context_detail"}, f"{function} {name} group is invalid")
        mask = str(record.get("mask", ""))
        add(errors, mask not in seen_masks, f"{function} duplicate component mask: {mask}")
        seen_masks.add(mask)
        check_mask(mask, record.get("mask_sha256"), errors, f"{function} {name}", "special")

    add(errors, audit.get("status") == "PASS_ZERO_COMPONENT_OVERLAP" and not audit.get("overlaps"),
        f"{function} source components overlap")
    reassembly = ROOT / str(layout.get("reassembly", ""))
    preview = ROOT / str(layout.get("reassembly_preview", ""))
    add(errors, reassembly.is_file(), f"{function} PBM reassembly is missing")
    add(errors, preview.is_file(), f"{function} visual reassembly preview is missing")
    if reassembly.is_file():
        add(errors, Image.open(reassembly).size == (200, 200), f"{function} reassembly dimensions drifted")
    if preview.is_file():
        add(errors, Image.open(preview).size == (800, 800), f"{function} reassembly preview dimensions drifted")
    add(errors, not list(output.rglob("*.crig")), f"{function} must not produce a CRIG before art review")

    return {
        "function": function,
        "special_component_count": len(special),
        "identity_component_count": len(identity),
        "reassembly": layout.get("reassembly"),
        "reassembly_preview": layout.get("reassembly_preview"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    gate = read_json(SOURCE_GATE)
    summary = read_json(EXPORT_SUMMARY)
    add(errors, gate.get("status") == "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_GATE", "source gate is not PASS")
    add(errors, summary.get("status") == "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_MASK_EXPORT_UNBOUND",
        "component export summary is not unbound PASS")
    exports = [verify_one(function, spec, errors) for function, spec in SPECS.items()]
    result = {
        "schema": "companion.v18_v20_complete_special_expression_component_export_gate.v1",
        "status": "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_COMPONENT_EXPORT_GATE" if not errors else
                  "FAIL_V18_V20_COMPLETE_SPECIAL_EXPRESSION_COMPONENT_EXPORT_GATE",
        "exports": exports,
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
    print("PASS: V18-V20 special-expression exports are source-only, V9-identity-locked, and unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
