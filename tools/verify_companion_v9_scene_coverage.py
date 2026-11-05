#!/usr/bin/env python3
"""Check v9 coverage accounts for every portable pet resource family."""

from __future__ import annotations

import argparse
import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200"
COVERAGE = ART_DIR / "v9-scene-resource-coverage.json"
MANIFEST = ART_DIR / "v9-expression-cemp-manifest.json"
PERFORMANCE = ROOT / "app/companion_pendant/epaper/pet_performance.c"
REPORT = ROOT / "docs/validation/companion-v9-scene-coverage-20260716.json"


def source_resource_families() -> set[str]:
    text = PERFORMANCE.read_text(encoding="utf-8")
    return set(re.findall(r'SCENE_(?:MOTION|STATIC)\([^\n]+, "([^"]+)", "([^"]+)"\)', text))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_pairs = source_resource_families()
    expected = {family for _scene, family in expected_pairs}
    entries = coverage.get("entries", [])
    actual = {entry.get("resource_family") for entry in entries}
    clips = {clip.get("name") for clip in manifest.get("clips", [])}

    if coverage.get("candidate_runtime_resource_activated") is not False:
        errors.append("coverage incorrectly claims candidate resource activation")
    if len(entries) != len(actual):
        errors.append("coverage contains duplicate resource-family entries")
    if actual != expected:
        errors.append("coverage families do not exactly match portable pet-performance families")
    for entry in entries:
        status = entry.get("status")
        clip = entry.get("candidate_clip")
        if status == "CANDIDATE_AVAILABLE_NOT_ACTIVE":
            if clip not in clips:
                errors.append(f"available {entry.get('resource_family')} references a missing clip")
        elif status in {"PENDING_VISUAL_BASELINE", "PENDING_MENU_VISUAL_BASELINE"}:
            if clip is not None:
                errors.append(f"pending {entry.get('resource_family')} must not choose a fallback clip")
        else:
            errors.append(f"unknown coverage status for {entry.get('resource_family')}")

    output = {
        "schema": "companion.v9_scene_coverage_verification.v1",
        "status": "PASS_MACHINE_ONLY_NO_LEGACY_FALLBACK" if not errors else "FAIL",
        "portable_resource_family_count": len(expected),
        "coverage_entry_count": len(entries),
        "candidate_mapping_count": sum(entry.get("candidate_clip") is not None for entry in entries),
        "pending_no_fallback_count": sum(entry.get("candidate_clip") is None for entry in entries),
        "candidate_runtime_resource_activated": False,
        "physical_or_owner_visual_pass": False,
        "errors": errors,
    }
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "PASS: all portable pet resource families are either v9 candidate-mapped "
        "or explicitly pending with no legacy fallback."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
