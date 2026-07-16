#!/usr/bin/env python3
"""Produce a deterministic non-importable preview of the pending v9 system sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-pet-special-states-v1"
SOURCE = ART_DIR / "generated_pet_special_system_v1_candidate.png"
EXPECTED_SHA256 = "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82"
PREVIEW = ART_DIR / "generated_pet_special_system_v1_candidate_200x200_preview.png"
REPORT = ROOT / "docs/validation/companion-pet-special-system-source-review-20260717.json"
TARGET_SIZE = (200, 200)
SOURCE_SIZE = (1254, 1254)
THRESHOLD = 180
ROWS = 3
COLUMNS = 4
SCENE_FAMILIES = [
    "voice.speaking", "recording.error", "power.charge_detected", "power.charging",
    "power.charged", "power.low_battery", "link.pairing", "link.connected",
    "link.syncing", "link.synced", "link.error", "system.error",
]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def cell_ink(bitmap: Image.Image) -> list[dict[str, int | str]]:
    pixels = bitmap.load()
    cells: list[dict[str, int | str]] = []
    for row in range(ROWS):
        y0 = row * bitmap.height // ROWS
        y1 = (row + 1) * bitmap.height // ROWS
        for column in range(COLUMNS):
            x0 = column * bitmap.width // COLUMNS
            x1 = (column + 1) * bitmap.width // COLUMNS
            ink = sum(
                pixels[x, y] == 0
                for y in range(y0, y1)
                for x in range(x0, x1)
            )
            cells.append({
                "scene_family": SCENE_FAMILIES[row * COLUMNS + column],
                "row": row,
                "column": column,
                "source_ink_pixels": ink,
            })
    return cells


def render_preview() -> dict[str, object]:
    errors: list[str] = []
    source_hash = sha256(SOURCE)
    if source_hash != EXPECTED_SHA256:
        errors.append("system source hash drifted from the recorded generated output")
    source = Image.open(SOURCE).convert("L")
    if source.size != SOURCE_SIZE:
        errors.append("system source is not the recorded square 1254x1254 output")
    bitmap = source.point(lambda value: 0 if value < THRESHOLD else 255, "1")
    cells = cell_ink(bitmap)
    for cell in cells:
        if not 4500 <= int(cell["source_ink_pixels"]) <= 15000:
            errors.append(
                f"{cell['scene_family']} has invalid source cell ink {cell['source_ink_pixels']}"
            )

    preview = source.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    preview = preview.point(lambda value: 0 if value < THRESHOLD else 255, "1")
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    preview.save(PREVIEW)
    black_pixels = sum(value == 0 for value in preview.getdata())
    if not 1600 <= black_pixels <= 6000:
        errors.append("system threshold preview ink coverage is outside the review guard band")

    return {
        "schema": "companion.pet_special_system_source_review.v1",
        "status": "PASS_MACHINE_PREVIEW_PENDING_OWNER" if not errors else "FAIL",
        "style_reference": {
            "path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png",
            "sha256": "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA",
        },
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
            "grid": [ROWS, COLUMNS],
            "cell_ink": cells,
        },
        "runtime_boundary": {
            "pbm_imported": False,
            "cemp_packed": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "owner_visual_pass": False,
        },
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the deterministic preview and review JSON.")
    args = parser.parse_args(argv)
    result = render_preview()
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: system v9 candidate source has twelve populated 3x4 cells and a non-importable 200x200 preview.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
