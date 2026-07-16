#!/usr/bin/env python3
"""Produce a deterministic non-importable preview of the v6 four-root menu."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-menu-v6-four-root"
SOURCE = ART_DIR / "generated_menu_four_root_v6_candidate.png"
EXPECTED_SHA256 = "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"
PREVIEW = ART_DIR / "generated_menu_four_root_v6_candidate_200x200_preview.png"
REPORT = ROOT / "docs/validation/companion-menu-v6-source-review-20260717.json"
TARGET_SIZE = (200, 200)
THRESHOLD = 180


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def horizontal_rule_centers(source: Image.Image) -> list[int]:
    bitmap = source.point(lambda value: 0 if value < THRESHOLD else 255, "1")
    pixels = bitmap.load()
    candidates = []
    minimum_ink = int(source.width * 0.90)
    for y in range(source.height):
        if sum(pixels[x, y] == 0 for x in range(source.width)) >= minimum_ink:
            candidates.append(y)
    centers: list[int] = []
    for row in candidates:
        if not centers or row > centers[-1] + 2:
            centers.append(row)
        else:
            centers[-1] = (centers[-1] + row) // 2
    return centers


def render_preview() -> dict[str, object]:
    errors: list[str] = []
    source_hash = sha256(SOURCE)
    if source_hash != EXPECTED_SHA256:
        errors.append("source hash drifted from the recorded generated output")
    source = Image.open(SOURCE).convert("L")
    if source.size != (1254, 1254):
        errors.append("source dimensions are not the recorded square 1254x1254 output")
    rule_centers = horizontal_rule_centers(source)
    if len(rule_centers) != 4:
        errors.append(f"expected four full-width menu separators, found {len(rule_centers)}")
    scaled_centers = [round(center * TARGET_SIZE[1] / source.height, 2) for center in rule_centers]
    if rule_centers and (scaled_centers[0] < 45 or scaled_centers[-1] > 175):
        errors.append("header or final menu row falls outside the 200x200 review geometry")

    preview = source.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    preview = preview.point(lambda value: 0 if value < THRESHOLD else 255, "1")
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    preview.save(PREVIEW)
    black_pixels = sum(value == 0 for value in preview.getdata())
    if black_pixels < 1200 or black_pixels > 12000:
        errors.append("threshold preview ink coverage is outside the review guard band")

    result: dict[str, object] = {
        "schema": "companion.menu_v6_source_review.v1",
        "status": "PASS_MACHINE_PREVIEW_PENDING_OWNER" if not errors else "FAIL",
        "source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": source_hash,
            "dimensions_px": list(source.size),
        },
        "preview": {
            "path": PREVIEW.relative_to(ROOT).as_posix(),
            "dimensions_px": list(TARGET_SIZE),
            "pixel_format": "1-bit preview only",
            "threshold": THRESHOLD,
            "black_pixels": black_pixels,
        },
        "geometry": {
            "full_width_separator_count": len(rule_centers),
            "source_separator_centers_y": rule_centers,
            "preview_separator_centers_y": scaled_centers,
            "root_rows": 4,
        },
        "runtime_boundary": {
            "pbm_imported": False,
            "cemp_packed": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "owner_visual_pass": False,
            "actual_text_owner": "menu_v5_localization",
        },
        "errors": errors,
    }
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the deterministic 200x200 preview and review JSON.")
    args = parser.parse_args(argv)
    result = render_preview()
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: v6 menu source has four-root geometry and a non-importable 200x200 preview.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
