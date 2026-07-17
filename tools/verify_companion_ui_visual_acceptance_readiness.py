#!/usr/bin/env python3
"""Verify all generated Companion UI candidates are ready for sequential owner review."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/validation/companion-ui-visual-acceptance-manifest-20260717.json"
REPORT = ROOT / "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json"
EXPECTED = {
    "menu-v6-four-root": {
        "source": "docs/art/iterations/companion-menu-v6-four-root/generated_menu_four_root_v6_candidate.png",
        "sha256": "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868",
        "evidence": "docs/validation/companion-menu-v6-localization-preview-20260717.json",
        "status": "PASS_MACHINE_LOCALIZATION_PREVIEW_PENDING_OWNER",
    },
    "special-system-v1": {
        "source": "docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_system_v1_candidate.png",
        "sha256": "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82",
        "evidence": "docs/validation/companion-pet-special-system-source-review-20260717.json",
        "status": "PASS_MACHINE_PREVIEW_PENDING_OWNER",
        "crop_preflight_source": "special-system-v1",
    },
    "special-journey-v1": {
        "source": "docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_journey_v1_candidate.png",
        "sha256": "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F",
        "evidence": "docs/validation/companion-pet-special-journey-source-review-20260717.json",
        "status": "PASS_MACHINE_PREVIEW_PENDING_OWNER",
        "crop_preflight_source": "special-journey-v1",
    },
}
ARTIFACT_IMAGES = {
    "menu-v6-four-root": [
        ("docs/art/iterations/companion-menu-v6-four-root/generated_menu_four_root_v6_candidate.png", "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"),
        ("docs/art/iterations/companion-menu-v6-four-root/generated_menu_four_root_v6_en_200x200_localization_preview.png", "3C2BAB9734CA44E95DE82D7580132195B59488C6D133B64B7F1B49A5144488ED"),
        ("docs/art/iterations/companion-menu-v6-four-root/generated_menu_four_root_v6_zh_cn_200x200_localization_preview.png", "6C244277526E268A337096483F8D3D3D2E8E2756C63596C4ECA3803DEF0F3941"),
    ],
    "special-system-v1": [
        ("docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_system_v1_candidate.png", "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82"),
        ("docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_system_v1_candidate_200x200_preview.png", "A4BBB8246E380FE80964DBA36F90D319A3936C6DA117A8F433E3A86873D0046D"),
        ("docs/art/iterations/companion-pet-special-states-v1/review-200x200/generated_pet_special_system_v1_crop_preflight_contact_sheet.png", "0CA22E270C246A450FEE176730394DC8487D1FB81EE492A088CAA69DB4D6E6E5"),
    ],
    "special-journey-v1": [
        ("docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_journey_v1_candidate.png", "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F"),
        ("docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_journey_v1_candidate_200x200_preview.png", "7207889637184F887E5EBFCA6A8C64776D23E9D46E0B9A0F7A227F2C087A0534"),
        ("docs/art/iterations/companion-pet-special-states-v1/review-200x200/generated_pet_special_journey_v1_crop_preflight_contact_sheet.png", "B072603D667B8BC9C54A0322E6C009526CF11D63D85AE553E931684B94AAC082"),
    ],
}
BOUNDARY_KEYS = ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"]
PROMPT_FIELDS = (
    "target",
    "operator_action",
    "success_signal",
    "failure_rule",
    "continue_condition",
    "recovery_condition",
    "record_fields",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify() -> dict[str, object]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    crop_preflight_path = ROOT / "docs/validation/companion-pet-special-state-crop-preflight-20260717.json"
    crop_preflight = json.loads(crop_preflight_path.read_text(encoding="utf-8")) if crop_preflight_path.is_file() else {}
    if crop_preflight.get("status") != "PASS_MACHINE_SAFE_CROP_PREVIEW_NOT_IMPORTABLE":
        errors.append("special-state crop preflight is not ready")
    crop_by_id = {item.get("id"): item for item in crop_preflight.get("sources", [])}
    items = manifest.get("items", [])
    by_id = {item.get("id"): item for item in items}
    if manifest.get("status") != "READY_FOR_SEQUENTIAL_OWNER_REVIEW":
        errors.append("visual acceptance manifest is not in the ready state")
    if [item.get("sequence") for item in items] != [1, 2, 3] or set(by_id) != set(EXPECTED):
        errors.append("visual acceptance manifest must define the exact three sequential review items")

    verified: list[dict[str, str]] = []
    for item_id, expected in EXPECTED.items():
        item = by_id.get(item_id, {})
        source = ROOT / expected["source"]
        evidence = ROOT / expected["evidence"]
        if item.get("source_sha256", "").upper() != expected["sha256"]:
            errors.append(f"{item_id} manifest hash drifted")
        if not source.is_file() or sha256(source) != expected["sha256"]:
            errors.append(f"{item_id} source hash drifted")
        if item.get("owner_decision") != "PENDING_OWNER_VISUAL_DECISION":
            errors.append(f"{item_id} is not pending owner review")
        prompt = item.get("operator_prompt", {})
        if not isinstance(prompt, dict):
            errors.append(f"{item_id} missing structured operator prompt")
            prompt = {}
        for field in PROMPT_FIELDS:
            value = prompt.get(field)
            if not value:
                errors.append(f"{item_id} operator prompt missing {field}")
        if not isinstance(prompt.get("success_signal"), list) or len(prompt.get("success_signal", [])) < 2:
            errors.append(f"{item_id} operator prompt needs multiple success signals")
        if not isinstance(prompt.get("record_fields"), list) or "选择结果" not in prompt.get("record_fields", []):
            errors.append(f"{item_id} operator prompt must retain a selection result field")
        artifact_review = item.get("artifact_review", {})
        if artifact_review.get("mode") != "original_image_one_at_a_time":
            errors.append(f"{item_id} must retain original-image one-at-a-time review mode")
        images = artifact_review.get("images", [])
        expected_images = ARTIFACT_IMAGES[item_id]
        if len(images) != len(expected_images):
            errors.append(f"{item_id} original-image review count drifted")
        for index, expected_image in enumerate(expected_images, start=1):
            image = images[index - 1] if len(images) >= index else {}
            image_path, image_hash = expected_image
            if image.get("index") != index or image.get("path") != image_path or image.get("sha256", "").upper() != image_hash:
                errors.append(f"{item_id} original-image review metadata drifted at index {index}")
            if image_path not in item.get("artifacts", []):
                errors.append(f"{item_id} original-image review is not bound to a listed artifact: {image_path}")
            resolved_image = ROOT / image_path
            if not resolved_image.is_file() or sha256(resolved_image) != image_hash:
                errors.append(f"{item_id} original-image review hash drifted at index {index}")
        review = json.loads(evidence.read_text(encoding="utf-8")) if evidence.is_file() else {}
        if review.get("status") != expected["status"]:
            errors.append(f"{item_id} machine evidence is not ready")
        boundary = review.get("runtime_boundary", {})
        for key in BOUNDARY_KEYS:
            if boundary.get(key) is not False:
                errors.append(f"{item_id} evidence must keep {key}=false")
        for artifact in item.get("artifacts", []):
            if not (ROOT / artifact).is_file():
                errors.append(f"{item_id} listed artifact is missing: {artifact}")
        crop_id = expected.get("crop_preflight_source")
        if crop_id:
            crop = crop_by_id.get(crop_id, {})
            if len(crop.get("frames", [])) != 12:
                errors.append(f"{item_id} crop preflight must retain twelve frames")
            for frame in crop.get("frames", []):
                if frame.get("edge_ink_pixels") != 0 or frame.get("minimum_clearance_px", 0) < 4:
                    errors.append(f"{item_id} crop preflight contains an unsafe frame")
        verified.append({
            "id": item_id,
            "source_sha256": expected["sha256"],
            "evidence": expected["evidence"],
            "operator_prompt": prompt,
            "artifact_review": artifact_review,
        })

    return {
        "schema": "companion.ui_visual_acceptance_readiness.v1",
        "status": "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW" if not errors else "FAIL",
        "items": verified,
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the readiness report.")
    args = parser.parse_args(argv)
    result = verify()
    if args.write:
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: three Companion visual items are ready for sequential owner review without runtime activation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
