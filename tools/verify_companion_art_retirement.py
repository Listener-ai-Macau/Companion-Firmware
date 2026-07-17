#!/usr/bin/env python3
"""Verify only v9 and explicitly audited pending visual sources remain renderable."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/art"
V9 = ART / "iterations/companion-pet-expression-v9"
MENU_V6 = ART / "iterations/companion-menu-v6-four-root"
MENU_V7 = ART / "iterations/companion-menu-v7-screen-family"
SPECIAL = ART / "iterations/companion-pet-special-states-v1"
RETIREMENT = ART / "retired-visual-rounds.json"
V9_SOURCE = V9 / "generated_pet_expression_sheet_v9_candidate.png"
V9_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V7_SOURCE = MENU_V7 / "generated_menu_screen_family_v7_3_candidate.png"
V7_HASH = "D2D36B1CD51D153758E64C4DCBE0E0B7192F2E3F895D62CD3C432DDFA8476C37"
MENU_REPORT = ROOT / "docs/validation/companion-menu-v7-screen-family-preview-20260717.json"
SPECIAL_REPORT = ROOT / "docs/validation/companion-pet-special-state-one-page-review-20260717.json"
REPORT = ROOT / "docs/validation/companion-art-retirement-20260716.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    allowed_dirs = {V9.resolve(), MENU_V6.resolve(), MENU_V7.resolve(), SPECIAL.resolve()}
    actual_dirs = {path.resolve() for path in (ART / "iterations").iterdir() if path.is_dir()}
    if actual_dirs != allowed_dirs:
        errors.append("iteration directory set is not limited to v9, rejected v6, pending v7 and pending special art")
    renderable_suffixes = {".png", ".jpg", ".jpeg", ".pbm", ".cemp"}
    renderables = [path for path in ART.rglob("*") if path.is_file() and path.suffix.lower() in renderable_suffixes]
    unauthorized = [path.relative_to(ROOT).as_posix() for path in renderables if not any(path.is_relative_to(directory) for directory in allowed_dirs)]
    if unauthorized:
        errors.append("unauthorized renderable art remains: " + ", ".join(unauthorized))
    if digest(V9_SOURCE) != V9_HASH:
        errors.append("retained v9 source hash drifted")
    generation = json.loads((MENU_V7 / "generation-request.json").read_text(encoding="utf-8"))
    history = json.loads((MENU_V7 / "generation-history.json").read_text(encoding="utf-8"))
    architecture = json.loads((MENU_V7 / "information-architecture.json").read_text(encoding="utf-8"))
    menu_report = json.loads(MENU_REPORT.read_text(encoding="utf-8"))
    special_report = json.loads(SPECIAL_REPORT.read_text(encoding="utf-8"))
    retirement = json.loads(RETIREMENT.read_text(encoding="utf-8"))
    if digest(V7_SOURCE) != V7_HASH:
        errors.append("pending v7.3 menu source hash drifted")
    if generation.get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER" or generation.get("generated_output", {}).get("sha256") != V7_HASH:
        errors.append("v7.3 generation record drifted")
    for key in ("pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "runtime_resource_activated"):
        if generation.get("runtime_boundary", {}).get(key) is not False:
            errors.append(f"v7.3 source must keep {key}=false")
    history_v73 = next((round_ for round_ in history.get("rounds", []) if round_.get("prompt_version") == "v7.3"), {})
    if history_v73.get("status") != "GENERATED_MACHINE_REVIEW_PENDING_OWNER" or history_v73.get("output", {}).get("sha256") != V7_HASH:
        errors.append("v7.3 history does not bind the pending source hash")
    if architecture.get("visual_contract", {}).get("inner_face", "").lower().startswith("no inner face") is False:
        errors.append("menu information architecture must prohibit faces inside pages")
    screens = {screen.get("id"): screen for screen in architecture.get("screens_in_review_order", [])}
    if screens.get("home", {}).get("rows") != ["Voice", "Device", "Connection", "Preferences"]:
        errors.append("menu Home must retain exactly four roots")
    if screens.get("connection", {}).get("rows") != ["Pair new device", "Link status", "Reconnect"]:
        errors.append("menu Connection must retain exactly three truthful rows")
    if screens.get("preferences", {}).get("rows") != ["Language", "Interaction", "Diagnostics", "About"]:
        errors.append("menu Preferences must retain the compact four-row contract")
    if menu_report.get("status") != "PASS_MACHINE_SCREEN_FAMILY_PREVIEW_PENDING_OWNER" or menu_report.get("source", {}).get("sha256") != V7_HASH:
        errors.append("v7.3 menu one-page preview is not bound to the current source")
    if len(menu_report.get("pages", [])) != 5 or any(len(page.get("review_pages", {})) != 3 for page in menu_report.get("pages", [])):
        errors.append("v7.3 menu must retain five raw/English/zh-CN page groups")
    if special_report.get("status") != "PASS_MACHINE_ONE_PAGE_PER_SPECIAL_STATE_PENDING_OWNER":
        errors.append("special-state one-page review is not machine-ready")
    if {source.get("id") for source in special_report.get("sources", [])} != {"special-system-v1", "special-journey-v1"} or any(len(source.get("pages", [])) != 12 for source in special_report.get("sources", [])):
        errors.append("special-state one-page review must retain two twelve-page sources")
    retired_ids = {entry.get("id"): entry for entry in retirement.get("retired_groups", [])}
    if retirement.get("status") != "NON_RENDERABLE_AUDIT_ONLY" or retired_ids.get("menu-v6-root-only-candidate", {}).get("decision") != "not_renderable":
        errors.append("retirement record does not retain rejected v6 audit-only status")
    for directory, name in ((MENU_V6, "v6"), (MENU_V7, "v7"), (SPECIAL, "special")):
        if any(path.suffix.lower() in {".pbm", ".cemp"} for path in directory.rglob("*")):
            errors.append(f"{name} visual-source directory contains an unauthorized PBM/CEMP")

    result = {
        "schema": "companion.art_retirement_verification.v2",
        "status": "PASS_V9_BASELINE_PENDING_MENU_V7_AND_SPECIAL_V1" if not errors else "FAIL",
        "iteration_directories": sorted(path.name for path in actual_dirs),
        "retained_source": V9_SOURCE.relative_to(ROOT).as_posix(),
        "retained_source_sha256": V9_HASH,
        "pending_menu_source": V7_SOURCE.relative_to(ROOT).as_posix(),
        "pending_menu_source_sha256": V7_HASH,
        "pending_menu_preview": MENU_REPORT.relative_to(ROOT).as_posix(),
        "pending_special_one_page_preview": SPECIAL_REPORT.relative_to(ROOT).as_posix(),
        "renderable_file_count": len(renderables),
        "unauthorized_renderables": unauthorized,
        "errors": errors,
    }
    if args.write:
        REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: docs/art retains v9, rejected v6 audit evidence, pending v7.3 menu and pending special sources without runtime resources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
