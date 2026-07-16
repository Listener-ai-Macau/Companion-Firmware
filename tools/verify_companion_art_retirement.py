#!/usr/bin/env python3
"""Verify only v9, the pending v6 menu source, and a non-renderable v9 plan remain."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "docs/art"
V9 = ART / "iterations/companion-pet-expression-v9"
MENU_V6 = ART / "iterations/companion-menu-v6-four-root"
SPECIAL_STATES = ART / "iterations/companion-pet-special-states-v1"
RETIREMENT = ART / "retired-visual-rounds.json"
SOURCE = V9 / "generated_pet_expression_sheet_v9_candidate.png"
SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
MENU_SOURCE = MENU_V6 / "generated_menu_four_root_v6_candidate.png"
MENU_SOURCE_SHA256 = "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"
MENU_PREVIEW = MENU_V6 / "generated_menu_four_root_v6_candidate_200x200_preview.png"
REPORT = ROOT / "docs/validation/companion-art-retirement-20260716.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    renderable_suffixes = {".png", ".jpg", ".jpeg", ".pbm", ".cemp"}
    renderable_files = [
        path for path in ART.rglob("*")
        if path.is_file() and path.suffix.lower() in renderable_suffixes
    ]
    allowed_menu_renderables = {MENU_SOURCE.resolve(), MENU_PREVIEW.resolve()}
    unauthorized_renderables = [
        path.relative_to(ROOT).as_posix() for path in renderable_files
        if not path.is_relative_to(V9) and path.resolve() not in allowed_menu_renderables
    ]
    iteration_directories = sorted(
        path.name for path in (ART / "iterations").iterdir() if path.is_dir()
    )
    retirement = json.loads(RETIREMENT.read_text(encoding="utf-8"))
    source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    menu_source_sha256 = hashlib.sha256(MENU_SOURCE.read_bytes()).hexdigest().upper()
    menu_generation = json.loads((MENU_V6 / "generation-request.json").read_text(encoding="utf-8"))
    menu_ledger = json.loads((MENU_V6 / "iteration-ledger.json").read_text(encoding="utf-8"))
    menu_review = json.loads(
        (ROOT / "docs/validation/companion-menu-v6-source-review-20260717.json").read_text(
            encoding="utf-8"
        )
    )

    if unauthorized_renderables:
        errors.append("unauthorized renderable art remains: " + ", ".join(unauthorized_renderables))
    if iteration_directories != [
        "companion-menu-v6-four-root",
        "companion-pet-expression-v9",
        "companion-pet-special-states-v1",
    ]:
        errors.append("iteration directory set is not limited to v9, pending v6 menu, and non-renderable special-state plan")
    if retirement.get("status") != "NON_RENDERABLE_AUDIT_ONLY":
        errors.append("retirement record has an unexpected status")
    if retirement.get("active_renderable_baseline_sha256", "").upper() != SOURCE_SHA256:
        errors.append("retirement record does not retain the v9 source hash")
    if source_sha256 != SOURCE_SHA256:
        errors.append("retained v9 renderable source hash drifted")
    if menu_source_sha256 != MENU_SOURCE_SHA256:
        errors.append("pending v6 menu source hash drifted")
    if menu_generation.get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("v6 menu generation record is not pending owner review")
    if menu_generation.get("generated_output", {}).get("sha256", "").upper() != MENU_SOURCE_SHA256:
        errors.append("v6 menu generation output hash drifted")
    if menu_ledger.get("baseline", {}).get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("v6 menu ledger must remain pending owner review")
    if menu_review.get("status") != "PASS_MACHINE_PREVIEW_PENDING_OWNER":
        errors.append("v6 menu machine review must remain a pending-owner preview")
    if menu_review.get("source", {}).get("sha256", "").upper() != MENU_SOURCE_SHA256:
        errors.append("v6 menu machine review does not match the pending source hash")
    if menu_review.get("preview", {}).get("dimensions_px") != [200, 200]:
        errors.append("v6 menu machine review is missing the 200x200 preview")
    runtime_boundary = menu_review.get("runtime_boundary", {})
    for key in ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"]:
        if runtime_boundary.get(key) is not False:
            errors.append(f"v6 menu review must keep {key}=false")
    if any(path.suffix.lower() in {".pbm", ".cemp"} for path in MENU_V6.rglob("*")):
        errors.append("pending v6 menu source must not contain PBM or CEMP")
    special_plan = json.loads((SPECIAL_STATES / "generation-plan.json").read_text(encoding="utf-8"))
    if special_plan.get("status") != "NON_RENDERABLE_PLAN_PENDING_GENERATION":
        errors.append("special-state plan must remain non-renderable and pending generation")
    if any(path.is_file() and path.suffix.lower() in renderable_suffixes for path in SPECIAL_STATES.rglob("*")):
        errors.append("special-state plan must not contain a renderable source before its individual generation record")

    output = {
        "schema": "companion.art_retirement_verification.v1",
        "status": "PASS_V9_BASELINE_PENDING_MENU_V6_AND_SPECIAL_STATE_PLAN" if not errors else "FAIL",
        "renderable_file_count": len(renderable_files),
        "iteration_directories": iteration_directories,
        "retained_source": SOURCE.relative_to(ROOT).as_posix(),
        "retained_source_sha256": source_sha256,
        "pending_menu_source": MENU_SOURCE.relative_to(ROOT).as_posix(),
        "pending_menu_source_sha256": menu_source_sha256,
        "non_renderable_special_state_plan": SPECIAL_STATES.relative_to(ROOT).as_posix(),
        "unauthorized_renderables": unauthorized_renderables,
        "errors": errors,
    }
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: docs/art retains only v9, the pending non-importable v6 menu source, and the non-renderable special-state plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
