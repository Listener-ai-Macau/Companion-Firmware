#!/usr/bin/env python3
"""Verify Companion G2 has locked, one-page visual-source review evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/validation/companion-ui-visual-acceptance-manifest-20260717.json"
REPORT = ROOT / "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json"
V9 = ROOT / "docs/validation/companion-v9-home-storyboard-review-20260717.json"
MENU = ROOT / "docs/validation/companion-menu-v7-screen-family-preview-20260717.json"
SPECIAL = ROOT / "docs/validation/companion-pet-special-state-one-page-review-20260717.json"
PROMPT_FIELDS = ("target", "operator_action", "success_signal", "failure_rule", "continue_condition", "recovery_condition", "record_fields")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def flattened_v9(data: dict[str, object]) -> list[tuple[str, str]]:
    return [(frame["review_page"], frame["review_page_sha256"]) for state in data["states"] for frame in state["frames"]]


def flattened_menu(data: dict[str, object]) -> list[tuple[str, str]]:
    return [(page["review_pages"][language]["path"], page["review_pages"][language]["sha256"])
            for page in data["pages"] for language in ("source", "en", "zh_cn")]


def flattened_special(data: dict[str, object], identifier: str) -> list[tuple[str, str]]:
    source = next(source for source in data["sources"] if source["id"] == identifier)
    return [(page["review_page"], page["review_page_sha256"]) for page in source["pages"]]


def build_report() -> dict[str, object]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    v9 = json.loads(V9.read_text(encoding="utf-8"))
    menu = json.loads(MENU.read_text(encoding="utf-8"))
    special = json.loads(SPECIAL.read_text(encoding="utf-8"))
    expected = {
        "home-v9-daily-storyboard": (v9["source_sha256"], V9, flattened_v9(v9)),
        "menu-v7-screen-family": (menu["source"]["sha256"], MENU, flattened_menu(menu)),
        "special-system-v1": (next(source for source in special["sources"] if source["id"] == "special-system-v1")["source_sha256"], SPECIAL, flattened_special(special, "special-system-v1")),
        "special-journey-v1": (next(source for source in special["sources"] if source["id"] == "special-journey-v1")["source_sha256"], SPECIAL, flattened_special(special, "special-journey-v1")),
    }
    ordered_ids = list(expected)
    items = manifest.get("items", [])
    by_id = {item.get("id"): item for item in items}
    if manifest.get("schema") != "companion.ui_visual_acceptance_manifest.v2":
        errors.append("visual acceptance manifest schema drifted")
    if manifest.get("status") != "READY_FOR_SEQUENTIAL_OWNER_REVIEW":
        errors.append("visual acceptance manifest is not in the ready state")
    if [item.get("id") for item in items] != ordered_ids or [item.get("sequence") for item in items] != [1, 2, 3, 4]:
        errors.append("visual acceptance manifest must define the four ordered source families")
    if "已执行" not in manifest.get("review_style", "") or "one original image at a time" not in manifest.get("review_style", ""):
        errors.append("visual acceptance manifest lost observation-only one-page review language")
    if len(v9.get("states", [])) != 13 or len(expected["home-v9-daily-storyboard"][2]) != 39:
        errors.append("v9 daily storyboard must retain 13 states and 39 keyframes")
    if [page.get("id") for page in menu.get("pages", [])] != ["home", "voice", "device", "connection", "preferences"] or len(expected["menu-v7-screen-family"][2]) != 15:
        errors.append("v7 menu family must retain five pages and fifteen source/localized reviews")
    for identifier in ("special-system-v1", "special-journey-v1"):
        if len(expected[identifier][2]) != 12:
            errors.append(f"{identifier} must retain twelve one-page review frames")

    verified: list[dict[str, object]] = []
    for identifier, (source_sha, evidence, expected_images) in expected.items():
        item = by_id.get(identifier, {})
        if item.get("source_sha256") != source_sha:
            errors.append(f"{identifier} source hash drifted")
        if item.get("machine_evidence") != evidence.relative_to(ROOT).as_posix():
            errors.append(f"{identifier} machine-evidence path drifted")
        prompt = item.get("operator_prompt", {})
        if any(not prompt.get(field) for field in PROMPT_FIELDS):
            errors.append(f"{identifier} lacks a complete Chinese operator card")
        if not isinstance(prompt.get("success_signal"), list) or len(prompt.get("success_signal", [])) < 2:
            errors.append(f"{identifier} lacks multiple visible success signals")
        review = item.get("artifact_review", {})
        images = review.get("images", [])
        observed = [(image.get("path"), image.get("sha256")) for image in images]
        if review.get("mode") != "original_image_one_at_a_time" or observed != expected_images:
            errors.append(f"{identifier} original-image order or hash binding drifted")
        if [image.get("index") for image in images] != list(range(1, len(expected_images) + 1)):
            errors.append(f"{identifier} original-image indices drifted")
        for image in images:
            path = ROOT / image.get("path", "")
            if not path.is_file() or digest(path) != image.get("sha256"):
                errors.append(f"{identifier} image hash drifted: {image.get('path')}")
            if not image.get("context"):
                errors.append(f"{identifier} image lacks review context: {image.get('path')}")
        if item.get("owner_decision") != "PENDING_OWNER_VISUAL_REVIEW":
            errors.append(f"{identifier} owner decision is not pending")
        if "No PBM/CEMP" not in item.get("runtime_boundary", ""):
            errors.append(f"{identifier} lost its runtime non-activation boundary")
        verified.append({"id": identifier, "source_sha256": source_sha, "image_count": len(images), "machine_evidence": item.get("machine_evidence"), "artifact_review": review, "operator_prompt": prompt})

    return {
        "schema": "companion.ui_visual_acceptance_readiness.v2",
        "status": "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW" if not errors else "FAIL",
        "machine_preflight_opens_operator_prompt": False,
        "next_eligible_owner_item": ordered_ids[0],
        "sequential_visual_review": [{"id": identifier, "state": "ready_or_blocked_by_prior_locked_page" if index else "ready_for_owner_observation"} for index, identifier in enumerate(ordered_ids)],
        "items": verified,
        "review_page_total": sum(item["image_count"] for item in verified),
        "runtime_boundary": {"pbm_imported": False, "cemp_packed": False, "external_flash_provisioned": False, "firmware_flashed": False, "runtime_resource_activated": False},
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        REPORT.write_text(rendered, encoding="utf-8")
    elif not REPORT.is_file() or REPORT.read_text(encoding="utf-8") != rendered:
        report["errors"].append(f"stale {REPORT.relative_to(ROOT).as_posix()}")
    if report["errors"]:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: four Companion visual-source families retain {report['review_page_total']} sequential one-page owner reviews without runtime activation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
