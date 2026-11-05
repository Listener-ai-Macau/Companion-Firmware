#!/usr/bin/env python3
"""Verify and inventory the durable Companion art-generation handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART_ROOT = ROOT / "docs" / "art" / "iterations"
MANIFEST = ROOT / "docs" / "validation" / "companion-art-generation-lineage-manifest-20260721.json"
LOCKED_V9 = ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9" / "generated_pet_expression_sheet_v9_candidate.png"
PROTECTED_ACCEPTANCE = ROOT / "docs" / "validation" / "companion-pet-special-system-owner-acceptance-20260717.json"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_ACCEPTANCE_SHA256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
TEXT_EXTENSIONS = {".md", ".json", ".txt"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def history_files() -> list[Path]:
    files: list[Path] = []
    for iteration_root in sorted(ART_ROOT.glob("companion-pet-expression-v9*")):
        if not iteration_root.is_dir():
            continue
        for path in sorted(iteration_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            files.append(path)
    return files


def category(path: Path) -> str:
    name = path.name.lower()
    if "prompt" in name:
        return "generation_prompt"
    if "request" in name:
        return "generation_request"
    if "lineage" in name:
        return "source_lineage"
    if "ledger" in name or "history" in name:
        return "iteration_ledger"
    if "layout" in name or "plan" in name or "profile" in name:
        return "rig_or_target_plan"
    if "choreograph" in name:
        return "choreography"
    if "triage" in name or "review" in name or "accept" in name:
        return "review_or_triage"
    if "contract" in name:
        return "art_contract"
    return "art_metadata"


def inventory() -> dict[str, object]:
    entries = [
        {
            "path": rel(path),
            "category": category(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in history_files()
    ]
    protected = {
        "locked_v9_source": {
            "path": rel(LOCKED_V9),
            "exists": LOCKED_V9.exists(),
            "sha256": sha256(LOCKED_V9) if LOCKED_V9.exists() else None,
        },
        "protected_owner_acceptance": {
            "path": rel(PROTECTED_ACCEPTANCE),
            "exists": PROTECTED_ACCEPTANCE.exists(),
            "sha256": sha256(PROTECTED_ACCEPTANCE) if PROTECTED_ACCEPTANCE.exists() else None,
        },
    }
    return {
        "schema": "companion.art_generation_lineage_manifest.v1",
        "revision": "v45-touch-failsafe-r7-20260721",
        "generated_from_commit": git_head(),
        "history_root": "docs/art/iterations/companion-pet-expression-v9*",
        "image_files_are_not_required_for_history": True,
        "entry_count": len(entries),
        "entries": entries,
        "protected": protected,
        "expected_sha256": {
            "locked_v9_source": LOCKED_V9_SHA256,
            "protected_owner_acceptance": PROTECTED_ACCEPTANCE_SHA256,
        },
    }


def check(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    required = [
        ROOT / "docs" / "companion_art_generation_lineage.md",
        ROOT / "docs" / "companion_v45_art_handoff.md",
        ROOT / "docs" / "companion_product_requirements.md",
        ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9-two-track-rig-v7" / "candidate" / "v45-special-component-layout.json",
        ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9-two-track-rig-v7" / "candidate" / "target-score-attempt-01" / "v45-wb55-target-profile-plan.json",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required handoff file: {rel(path)}")

    if not LOCKED_V9.exists() or sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        errors.append("locked V9 source hash mismatch")
    if not PROTECTED_ACCEPTANCE.exists() or sha256(PROTECTED_ACCEPTANCE) != PROTECTED_ACCEPTANCE_SHA256:
        errors.append("protected owner acceptance hash mismatch")

    entries = manifest.get("entries", [])
    if not isinstance(entries, list) or not entries:
        errors.append("manifest has no prompt/history entries")
    else:
        for item in entries:
            path = ROOT / str(item["path"])
            if not path.exists():
                errors.append(f"manifest entry missing: {item['path']}")
                continue
            if sha256(path) != item["sha256"]:
                errors.append(f"manifest hash drift: {item['path']}")

    if manifest.get("image_files_are_not_required_for_history") is not True:
        errors.append("manifest must remain independent of image files")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write a refreshed manifest")
    parser.add_argument("--check", action="store_true", help="check the committed manifest")
    args = parser.parse_args()
    current = inventory()
    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(current, ensure_ascii=True, indent=2) + "\n")
    if args.check or not args.write:
        if not MANIFEST.exists():
            print(f"FAIL: missing {rel(MANIFEST)}")
            return 1
        recorded = json.loads(MANIFEST.read_text())
        errors = check(recorded)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print(f"PASS_ART_HANDOFF_MANIFEST entries={recorded['entry_count']} revision={recorded['revision']}")
        return 0
    print(f"WROTE {rel(MANIFEST)} entries={current['entry_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
