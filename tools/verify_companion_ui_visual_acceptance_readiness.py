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
    },
    "special-journey-v1": {
        "source": "docs/art/iterations/companion-pet-special-states-v1/generated_pet_special_journey_v1_candidate.png",
        "sha256": "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F",
        "evidence": "docs/validation/companion-pet-special-journey-source-review-20260717.json",
        "status": "PASS_MACHINE_PREVIEW_PENDING_OWNER",
    },
}
BOUNDARY_KEYS = ["pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify() -> dict[str, object]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
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
        verified.append({"id": item_id, "source_sha256": expected["sha256"], "evidence": expected["evidence"]})

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
