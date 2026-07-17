#!/usr/bin/env python3
"""Verify only locked v9 sources and pending machine-reviewed visual candidates remain."""

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
MENU_EN_PREVIEW = MENU_V6 / "generated_menu_four_root_v6_en_200x200_localization_preview.png"
MENU_ZH_PREVIEW = MENU_V6 / "generated_menu_four_root_v6_zh_cn_200x200_localization_preview.png"
SYSTEM_SOURCE = SPECIAL_STATES / "generated_pet_special_system_v1_candidate.png"
SYSTEM_SOURCE_SHA256 = "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82"
SYSTEM_PREVIEW = SPECIAL_STATES / "generated_pet_special_system_v1_candidate_200x200_preview.png"
JOURNEY_SOURCE = SPECIAL_STATES / "generated_pet_special_journey_v1_candidate.png"
JOURNEY_SOURCE_SHA256 = "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F"
JOURNEY_PREVIEW = SPECIAL_STATES / "generated_pet_special_journey_v1_candidate_200x200_preview.png"
SPECIAL_REVIEW_DIR = SPECIAL_STATES / "review-200x200"
SYSTEM_CROP_PREFLIGHT = SPECIAL_REVIEW_DIR / "generated_pet_special_system_v1_crop_preflight_contact_sheet.png"
JOURNEY_CROP_PREFLIGHT = SPECIAL_REVIEW_DIR / "generated_pet_special_journey_v1_crop_preflight_contact_sheet.png"
SPECIAL_CROP_PREFLIGHT_REPORT = ROOT / "docs/validation/companion-pet-special-state-crop-preflight-20260717.json"
SPECIAL_MAPPING = SPECIAL_STATES / "pending-source-mapping.json"
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
    allowed_menu_renderables = {
        MENU_SOURCE.resolve(), MENU_PREVIEW.resolve(), MENU_EN_PREVIEW.resolve(), MENU_ZH_PREVIEW.resolve(),
    }
    allowed_system_renderables = {SYSTEM_SOURCE.resolve(), SYSTEM_PREVIEW.resolve(), SYSTEM_CROP_PREFLIGHT.resolve()}
    allowed_journey_renderables = {JOURNEY_SOURCE.resolve(), JOURNEY_PREVIEW.resolve(), JOURNEY_CROP_PREFLIGHT.resolve()}
    unauthorized_renderables = [
        path.relative_to(ROOT).as_posix() for path in renderable_files
        if not path.is_relative_to(V9)
        and path.resolve() not in allowed_menu_renderables
        and path.resolve() not in allowed_system_renderables
        and path.resolve() not in allowed_journey_renderables
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
    menu_localization_review = json.loads(
        (ROOT / "docs/validation/companion-menu-v6-localization-preview-20260717.json").read_text(
            encoding="utf-8"
        )
    )
    special_plan = json.loads((SPECIAL_STATES / "generation-plan.json").read_text(encoding="utf-8"))
    system_attempts = json.loads((SPECIAL_STATES / "system-generation-attempts.json").read_text(encoding="utf-8"))
    system_review = json.loads(
        (ROOT / "docs/validation/companion-pet-special-system-source-review-20260717.json").read_text(
            encoding="utf-8"
        )
    )
    journey_attempts = json.loads((SPECIAL_STATES / "journey-generation-attempts.json").read_text(encoding="utf-8"))
    journey_review = json.loads(
        (ROOT / "docs/validation/companion-pet-special-journey-source-review-20260717.json").read_text(
            encoding="utf-8"
        )
    )
    special_mapping = json.loads(SPECIAL_MAPPING.read_text(encoding="utf-8"))
    special_crop_preflight = json.loads(SPECIAL_CROP_PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    system_source_sha256 = hashlib.sha256(SYSTEM_SOURCE.read_bytes()).hexdigest().upper()
    journey_source_sha256 = hashlib.sha256(JOURNEY_SOURCE.read_bytes()).hexdigest().upper()

    if unauthorized_renderables:
        errors.append("unauthorized renderable art remains: " + ", ".join(unauthorized_renderables))
    if iteration_directories != [
        "companion-menu-v6-four-root",
        "companion-pet-expression-v9",
        "companion-pet-special-states-v1",
    ]:
        errors.append("iteration directory set is not limited to v9, pending v6 menu, and pending v9 special art")
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
    menu_iterations = menu_ledger.get("iterations", [])
    menu_candidate = next(
        (
            iteration
            for iteration in menu_iterations
            if iteration.get("iteration_id") == "menu-v6-four-root-source-2026-07-17"
        ),
        {},
    )
    if (
        menu_candidate.get("status") != "generated_machine_review_pending_owner"
        or menu_candidate.get("review", {}).get("outcome") != "PENDING_OWNER_VISUAL_REVIEW"
        or menu_candidate.get("implementation", {}).get("status") != "not_activated_pending_owner_visual_review"
    ):
        errors.append("v6 menu ledger must retain the pending-owner, not-activated candidate")
    if (
        menu_candidate.get("output") != MENU_SOURCE.relative_to(ROOT).as_posix()
        or menu_candidate.get("sha256", "").upper() != MENU_SOURCE_SHA256
    ):
        errors.append("v6 menu ledger candidate output/hash drifted")
    if menu_review.get("status") != "PASS_MACHINE_PREVIEW_PENDING_OWNER":
        errors.append("v6 menu machine review must remain a pending-owner preview")
    if menu_review.get("source", {}).get("sha256", "").upper() != MENU_SOURCE_SHA256:
        errors.append("v6 menu machine review does not match the pending source hash")
    if menu_review.get("preview", {}).get("dimensions_px") != [200, 200]:
        errors.append("v6 menu machine review is missing the 200x200 preview")
    if menu_localization_review.get("status") != "PASS_MACHINE_LOCALIZATION_PREVIEW_PENDING_OWNER":
        errors.append("v6 menu localized previews must remain a pending-owner machine preview")
    if menu_localization_review.get("source", {}).get("sha256", "").upper() != MENU_SOURCE_SHA256:
        errors.append("v6 menu localized previews do not match the pending source hash")
    localized_previews = menu_localization_review.get("previews", [])
    if [preview.get("language") for preview in localized_previews] != ["en", "zh_cn"]:
        errors.append("v6 menu localized previews must contain English then zh-CN")
    if any(preview.get("labels") != expected for preview, expected in zip(
        localized_previews,
        [["Voice", "Device", "Connection", "Preferences"], ["\u8bed\u97f3", "\u8bbe\u5907", "\u8fde\u63a5", "\u504f\u597d\u8bbe\u7f6e"]],
        strict=True,
    )):
        errors.append("v6 menu localized preview labels drifted from the four-root contract")
    runtime_boundary = menu_review.get("runtime_boundary", {})
    for key in ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"]:
        if runtime_boundary.get(key) is not False:
            errors.append(f"v6 menu review must keep {key}=false")
    localized_runtime_boundary = menu_localization_review.get("runtime_boundary", {})
    for key in ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass", "target_font_asset_changed"]:
        if localized_runtime_boundary.get(key) is not False:
            errors.append(f"v6 menu localized preview must keep {key}=false")
    if any(path.suffix.lower() in {".pbm", ".cemp"} for path in MENU_V6.rglob("*")):
        errors.append("pending v6 menu source must not contain PBM or CEMP")
    if special_plan.get("status") != "SYSTEM_AND_JOURNEY_SOURCES_GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("special-state plan has an unexpected source-review status")
    system_sheet = next((sheet for sheet in special_plan.get("sheets", []) if sheet.get("id") == "system"), {})
    if system_sheet.get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("system sheet must remain pending owner review")
    if system_sheet.get("generated_output", {}).get("sha256", "").upper() != SYSTEM_SOURCE_SHA256:
        errors.append("system sheet output hash drifted")
    if system_source_sha256 != SYSTEM_SOURCE_SHA256:
        errors.append("pending system source hash drifted")
    if system_review.get("status") != "PASS_MACHINE_PREVIEW_PENDING_OWNER":
        errors.append("system source machine review must remain a pending-owner preview")
    if system_review.get("source", {}).get("sha256", "").upper() != SYSTEM_SOURCE_SHA256:
        errors.append("system source machine review does not match the pending source hash")
    if system_review.get("preview", {}).get("dimensions_px") != [200, 200]:
        errors.append("system source machine review is missing the 200x200 preview")
    if system_review.get("geometry", {}).get("grid") != [3, 4]:
        errors.append("system source machine review is missing 3x4 geometry")
    if not system_attempts.get("attempts") or system_attempts["attempts"][-1].get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("system attempt history must end with the pending square source")
    runtime_boundary = system_review.get("runtime_boundary", {})
    for key in ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"]:
        if runtime_boundary.get(key) is not False:
            errors.append(f"system source review must keep {key}=false")
    journey_sheet = next((sheet for sheet in special_plan.get("sheets", []) if sheet.get("id") == "journey"), {})
    if journey_sheet.get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("journey sheet must remain pending owner review")
    if journey_sheet.get("generated_output", {}).get("sha256", "").upper() != JOURNEY_SOURCE_SHA256:
        errors.append("journey sheet output hash drifted")
    if journey_source_sha256 != JOURNEY_SOURCE_SHA256:
        errors.append("pending journey source hash drifted")
    if journey_review.get("status") != "PASS_MACHINE_PREVIEW_PENDING_OWNER":
        errors.append("journey source machine review must remain a pending-owner preview")
    if journey_review.get("source", {}).get("sha256", "").upper() != JOURNEY_SOURCE_SHA256:
        errors.append("journey source machine review does not match the pending source hash")
    if journey_review.get("preview", {}).get("dimensions_px") != [200, 200]:
        errors.append("journey source machine review is missing the 200x200 preview")
    if journey_review.get("geometry", {}).get("grid") != [3, 4]:
        errors.append("journey source machine review is missing 3x4 geometry")
    if not journey_attempts.get("attempts") or journey_attempts["attempts"][-1].get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER":
        errors.append("journey attempt history must end with the pending square source")
    journey_runtime_boundary = journey_review.get("runtime_boundary", {})
    for key in ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"]:
        if journey_runtime_boundary.get(key) is not False:
            errors.append(f"journey source review must keep {key}=false")
    if special_crop_preflight.get("status") != "PASS_MACHINE_SAFE_CROP_PREVIEW_NOT_IMPORTABLE":
        errors.append("special crop preflight must remain review-only machine evidence")
    crop_sources = {item.get("id"): item for item in special_crop_preflight.get("sources", [])}
    for identifier, expected_source_hash, expected_contact in (
        ("special-system-v1", SYSTEM_SOURCE_SHA256, SYSTEM_CROP_PREFLIGHT),
        ("special-journey-v1", JOURNEY_SOURCE_SHA256, JOURNEY_CROP_PREFLIGHT),
    ):
        crop_source = crop_sources.get(identifier, {})
        if crop_source.get("source_sha256", "").upper() != expected_source_hash:
            errors.append(f"{identifier} crop preflight source hash drifted")
        if crop_source.get("contact_sheet") != expected_contact.relative_to(ROOT).as_posix():
            errors.append(f"{identifier} crop preflight contact path drifted")
        if not expected_contact.is_file() or crop_source.get("contact_sheet_sha256", "").upper() != hashlib.sha256(expected_contact.read_bytes()).hexdigest().upper():
            errors.append(f"{identifier} crop preflight contact hash drifted")
        frames = crop_source.get("frames", [])
        if len(frames) != 12 or any(frame.get("edge_ink_pixels") != 0 or frame.get("minimum_clearance_px", 0) < 4 for frame in frames):
            errors.append(f"{identifier} crop preflight must retain twelve >=4 px no-edge-ink frames")
    crop_boundary = special_crop_preflight.get("runtime_boundary", {})
    for key in ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "ota_behavior_changed", "owner_visual_pass"]:
        if crop_boundary.get(key) is not False:
            errors.append(f"special crop preflight must keep {key}=false")
    if any(path.suffix.lower() in {".pbm", ".cemp"} for path in SPECIAL_STATES.rglob("*")):
        errors.append("pending special sources must not contain PBM or CEMP")
    if special_mapping.get("status") != "PENDING_OWNER_VISUAL_DECISION_NO_RUNTIME_ACTIVATION":
        errors.append("special-state source mapping must remain pending owner decision without runtime activation")

    output = {
        "schema": "companion.art_retirement_verification.v1",
        "status": "PASS_V9_BASELINE_PENDING_MENU_V6_AND_SPECIAL_V1" if not errors else "FAIL",
        "renderable_file_count": len(renderable_files),
        "iteration_directories": iteration_directories,
        "retained_source": SOURCE.relative_to(ROOT).as_posix(),
        "retained_source_sha256": source_sha256,
        "pending_menu_source": MENU_SOURCE.relative_to(ROOT).as_posix(),
        "pending_menu_source_sha256": menu_source_sha256,
        "pending_menu_localization_previews": [
            MENU_EN_PREVIEW.relative_to(ROOT).as_posix(), MENU_ZH_PREVIEW.relative_to(ROOT).as_posix(),
        ],
        "pending_system_source": SYSTEM_SOURCE.relative_to(ROOT).as_posix(),
        "pending_system_source_sha256": system_source_sha256,
        "pending_journey_source": JOURNEY_SOURCE.relative_to(ROOT).as_posix(),
        "pending_journey_source_sha256": journey_source_sha256,
        "pending_special_crop_preflight": SPECIAL_CROP_PREFLIGHT_REPORT.relative_to(ROOT).as_posix(),
        "pending_special_crop_previews": [
            SYSTEM_CROP_PREFLIGHT.relative_to(ROOT).as_posix(), JOURNEY_CROP_PREFLIGHT.relative_to(ROOT).as_posix(),
        ],
        "special_state_plan": SPECIAL_STATES.relative_to(ROOT).as_posix(),
        "pending_special_mapping": SPECIAL_MAPPING.relative_to(ROOT).as_posix(),
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
    print("PASS: docs/art retains only v9, the pending localized v6 menu source, two pending special sources, and their exact review-only no-runtime mappings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
