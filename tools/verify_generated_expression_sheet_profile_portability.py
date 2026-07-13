#!/usr/bin/env python3
"""Verify generated expression imports remain portable across panel profiles."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "tools" / "import_generated_expression_sheet.py"
SOURCE = ROOT / "docs" / "art" / "generated_pet_expression_sheet_v5.png"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-screen-generated-art-profile-portability.json"
SCHEMA_ID = "companion.screen.generated_art_profile_portability.v1"
ALTERNATE_PROFILE = "264x167"
ALTERNATE_SUFFIX = "2_7in"
EXPECTED_ASSET_COUNT = 39


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def run_alternate_import(workdir: pathlib.Path) -> dict[str, Any]:
    output_dir = workdir / "assets"
    report_path = workdir / "report.json"
    preview_path = workdir / "preview.png"
    review_path = workdir / "review.png"
    completed = subprocess.run(
        [
            sys.executable,
            str(IMPORTER),
            "--source", str(SOURCE),
            "--profile", ALTERNATE_PROFILE,
            "--asset-suffix", ALTERNATE_SUFFIX,
            "--out-dir", str(output_dir),
            "--report", str(report_path),
            "--preview", str(preview_path),
            "--review", str(review_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    assets = sorted(output_dir.glob("*.pbm"))
    dimensions = []
    for asset in assets:
        with Image.open(asset) as image:
            dimensions.append(list(image.size))
    return {
        "returncode": completed.returncode,
        "report": report,
        "asset_names": [asset.name for asset in assets],
        "asset_dimensions": dimensions,
        "preview_exists": preview_path.exists(),
        "review_exists": review_path.exists(),
    }


def build_fixture() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="companion-generated-art-profile-") as tempdir:
        result = run_alternate_import(pathlib.Path(tempdir))
    report = result["report"]
    profile = report.get("profile", {})
    width, height = (int(value) for value in ALTERNATE_PROFILE.split("x"))
    all_dimensions_match = all(item == [width, height] for item in result["asset_dimensions"])
    all_names_match = all(name.endswith(f"_{ALTERNATE_SUFFIX}.pbm") for name in result["asset_names"])
    checks = {
        "alternate_import_passes": result["returncode"] == 0 and report.get("status") == "PASS",
        "profile_is_reported": profile == {
            "width": width,
            "height": height,
            "max_face_width": 230,
            "max_face_height": 139,
            "top_inset": 13,
            "label_guard_band_y": height,
            "asset_suffix": ALTERNATE_SUFFIX,
        },
        "all_expression_assets_emitted": len(result["asset_names"]) == EXPECTED_ASSET_COUNT,
        "all_expression_assets_use_requested_suffix": all_names_match,
        "all_expression_assets_match_requested_dimensions": all_dimensions_match,
        "review_artifacts_emitted": result["preview_exists"] and result["review_exists"],
        "machine_review_passes": report.get("machine_review", {}).get("status") == "PASS",
        "no_fixed_art_margin": (
            report.get("machine_review_thresholds", {}).get("fixed_art_margin_px") == 0
            and report.get("machine_review_thresholds", {}).get("internal_shell_mask_disabled") is True
        ),
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "purpose": (
            "Prove one accepted generated expression sheet can produce isolated "
            "assets for a second panel profile without rewriting the art engine "
            "or mutating WB55 1.54in output names."
        ),
        "source": rel(SOURCE),
        "alternate_profile": ALTERNATE_PROFILE,
        "alternate_asset_suffix": ALTERNATE_SUFFIX,
        "checks": checks,
        "asset_count": len(result["asset_names"]),
        "validation_command": "python .\\tools\\verify_generated_expression_sheet_profile_portability.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args()
    output = args.json if args.json.is_absolute() else ROOT / args.json
    fixture = build_fixture()
    errors: list[str] = []
    if fixture["status"] != "PASS":
        errors.append("profile portability fixture did not pass")
    rendered = json.dumps(fixture, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not output.exists() or output.read_text(encoding="utf-8") != rendered:
        errors.append(f"{rel(output)} is stale; rerun with --write")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: generated art profile portability verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
