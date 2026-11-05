#!/usr/bin/env python3
"""Verify all no-fallback scene gaps have exact pending visual-source mappings."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPECIAL = ROOT / "docs/art/iterations/companion-pet-special-states-v1"
MAPPING = SPECIAL / "pending-source-mapping.json"
COVERAGE = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-scene-resource-coverage.json"
REPORT = ROOT / "docs/validation/companion-pending-special-source-mapping-20260717.json"
EXPECTED_SOURCES = {
    "menu_v6": "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868",
    "system": "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82",
    "journey": "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F",
}
EXPECTED_CELLS = {
    "voice.speaking": [[0, 0]], "recording.error": [[0, 1]],
    "power.charge_detected": [[0, 2]], "power.charging": [[0, 3]],
    "power.charged": [[1, 0]], "power.low_battery": [[1, 1]],
    "link.pairing": [[1, 2]], "link.connected": [[1, 3]],
    "link.syncing": [[2, 0]], "link.synced": [[2, 1]],
    "link.error": [[2, 2]], "system.error": [[2, 3]],
    "menu.open": [[0, 0], [0, 1]], "menu.blocked": [[0, 2]],
    "menu.exit": [[0, 3]], "upgrade.offer": [[1, 0]],
    "upgrade.prepare": [[1, 1]], "upgrade.transfer": [[1, 2]],
    "upgrade.verify": [[1, 3]], "upgrade.restart": [[2, 0]],
    "upgrade.success": [[2, 1]], "upgrade.error": [[2, 2], [2, 3]],
}
SYSTEM_FAMILIES = {
    "voice.speaking", "recording.error", "power.charge_detected", "power.charging",
    "power.charged", "power.low_battery", "link.pairing", "link.connected",
    "link.syncing", "link.synced", "link.error", "system.error",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify() -> dict[str, object]:
    errors: list[str] = []
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    pending = {
        entry["resource_family"]
        for entry in coverage.get("entries", [])
        if entry.get("status", "").startswith("PENDING")
    }
    entries = {entry.get("resource_family"): entry for entry in mapping.get("entries", [])}

    if mapping.get("status") != "PENDING_OWNER_VISUAL_DECISION_NO_RUNTIME_ACTIVATION":
        errors.append("mapping must remain pending owner visual decision")
    if set(entries) != pending:
        errors.append("mapping families do not exactly match v9 no-fallback gaps")
    if len(entries) != 22:
        errors.append("mapping must contain exactly 22 pending scene families")

    catalog = mapping.get("source_catalog", {})
    for key, expected_hash in EXPECTED_SOURCES.items():
        source = catalog.get(key, {})
        path = ROOT / source.get("path", "")
        if source.get("sha256", "").upper() != expected_hash:
            errors.append(f"{key} catalog hash is not locked")
        if not path.is_file() or sha256(path) != expected_hash:
            errors.append(f"{key} catalog source hash drifted")
        if source.get("status") != "PENDING_OWNER_VISUAL_DECISION":
            errors.append(f"{key} catalog source is not pending owner review")

    for family, expected_cells in EXPECTED_CELLS.items():
        entry = entries.get(family, {})
        expected_source = "system" if family in SYSTEM_FAMILIES else "journey"
        if entry.get("primary_source") != expected_source:
            errors.append(f"{family} maps to the wrong primary candidate source")
        if entry.get("cells") != expected_cells:
            errors.append(f"{family} cell mapping drifted")
    menu_open = entries.get("menu.open", {})
    if menu_open.get("requires_source") != "menu_v6":
        errors.append("menu.open must require the separate four-root menu source")
    if "never replaces menu_v6" not in menu_open.get("composition_rule", ""):
        errors.append("menu.open composition rule must prohibit replacing menu_v6")

    boundary = mapping.get("runtime_boundary", {})
    for key in [
        "candidate_resource_binding_available", "pbm_imported", "cemp_packed",
        "external_flash_provisioned", "firmware_flashed", "ota_behavior_changed",
        "owner_visual_pass",
    ]:
        if boundary.get(key) is not False:
            errors.append(f"runtime boundary must keep {key}=false")
    if boundary.get("fallback") != "forbidden":
        errors.append("runtime boundary must forbid fallback")

    return {
        "schema": "companion.pending_special_source_mapping_validation.v1",
        "status": "PASS_EXACT_PENDING_SOURCE_MAPPING_NO_RUNTIME" if not errors else "FAIL",
        "pending_family_count": len(pending),
        "mapped_family_count": len(entries),
        "source_hashes": EXPECTED_SOURCES,
        "runtime_boundary": boundary,
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the mapping validation report.")
    args = parser.parse_args(argv)
    result = verify()
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: all 22 no-fallback scene gaps map to exact pending sources without runtime activation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
