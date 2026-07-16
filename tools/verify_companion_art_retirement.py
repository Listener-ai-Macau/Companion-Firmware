#!/usr/bin/env python3
"""Verify only v9 renderable art remains in the Companion art workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "docs/art"
V9 = ART / "iterations/companion-pet-expression-v9"
RETIREMENT = ART / "retired-visual-rounds.json"
SOURCE = V9 / "generated_pet_expression_sheet_v9_candidate.png"
SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
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
    non_v9_renderables = [
        path.relative_to(ROOT).as_posix() for path in renderable_files
        if not path.is_relative_to(V9)
    ]
    iteration_directories = sorted(
        path.name for path in (ART / "iterations").iterdir() if path.is_dir()
    )
    retirement = json.loads(RETIREMENT.read_text(encoding="utf-8"))
    source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()

    if non_v9_renderables:
        errors.append("renderable non-v9 art remains: " + ", ".join(non_v9_renderables))
    if iteration_directories != ["companion-pet-expression-v9"]:
        errors.append("iteration directory set is not limited to companion-pet-expression-v9")
    if retirement.get("status") != "NON_RENDERABLE_AUDIT_ONLY":
        errors.append("retirement record has an unexpected status")
    if retirement.get("active_renderable_baseline_sha256", "").upper() != SOURCE_SHA256:
        errors.append("retirement record does not retain the v9 source hash")
    if source_sha256 != SOURCE_SHA256:
        errors.append("retained v9 renderable source hash drifted")

    output = {
        "schema": "companion.art_retirement_verification.v1",
        "status": "PASS_V9_ONLY_RENDERABLE_ART" if not errors else "FAIL",
        "renderable_file_count": len(renderable_files),
        "iteration_directories": iteration_directories,
        "retained_source": SOURCE.relative_to(ROOT).as_posix(),
        "retained_source_sha256": source_sha256,
        "non_v9_renderables": non_v9_renderables,
        "errors": errors,
    }
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: docs/art retains only v9 renderable Companion art and a non-renderable retirement record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
