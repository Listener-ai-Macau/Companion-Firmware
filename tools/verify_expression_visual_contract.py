#!/usr/bin/env python3
"""Verify ExpressionV1 visual distinctness and bitmap health."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from itertools import combinations
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import DISPLAY_VARIANTS, EXPRESSION_KINDS, sha256_hex  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-visual-contract.json")
SCHEMA_ID = "companion.pendant.screen_expression_visual_contract.v1"

MANIFEST = REPO_ROOT / "docs" / "validation" / "companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
CATALOG = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-catalog.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

FULL_INK_RATIO_PPM_MIN = 10_000
FULL_INK_RATIO_PPM_MAX = 170_000
FACE_INK_RATIO_PPM_MIN = 20_000
FACE_INK_RATIO_PPM_MAX = 235_000
MIN_FULL_DISTANCE_PPM = 1_000
MIN_FACE_DISTANCE_PPM = 2_500

DISPLAY_EDGE_CLEAR_MARGIN_PERCENT = 5
MAX_INNER_FACE_EDGE_ACCENT_PIXELS = 200


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_pbm(data: bytes, label: str) -> tuple[int, int, list[int]]:
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 3 and index < len(data):
        if data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] not in {b"\n", b"\r"}:
                index += 1
            continue
        if data[index:index + 1].isspace():
            index += 1
            continue
        start = index
        while index < len(data) and not data[index:index + 1].isspace():
            index += 1
        tokens.append(data[start:index])
    if len(tokens) != 3 or tokens[0] != b"P4":
        raise ValueError(f"{label}: expected PBM P4 header")
    while index < len(data) and data[index:index + 1].isspace():
        index += 1
    width = int(tokens[1])
    height = int(tokens[2])
    row_bytes = (width + 7) // 8
    payload = data[index:index + row_bytes * height]
    if len(payload) != row_bytes * height:
        raise ValueError(f"{label}: PBM payload is truncated")
    pixels: list[int] = []
    for y in range(height):
        row_start = y * row_bytes
        for x in range(width):
            pixels.append(1 if payload[row_start + (x // 8)] & (0x80 >> (x % 8)) else 0)
    return width, height, pixels


def expression_face_box(width: int, height: int) -> dict[str, int]:
    if height <= 130:
        face_size = height - 32
        face_x = (width - face_size) // 2
        face_y = 16
    else:
        face_size = min(width, height) - 36
        face_x = (width - face_size) // 2
        face_y = (height - face_size) // 2
    return {"x": face_x, "y": face_y, "width": face_size, "height": face_size}


def crop_pixels(pixels: list[int], width: int, box: dict[str, int]) -> list[int]:
    return [
        pixels[y * width + x]
        for y in range(box["y"], box["y"] + box["height"])
        for x in range(box["x"], box["x"] + box["width"])
    ]


def ratio_ppm(count: int, total: int) -> int:
    return int(round(count * 1_000_000 / total))


def distance_ppm(left: list[int], right: list[int]) -> int:
    if len(left) != len(right) or not left:
        return 0
    return ratio_ppm(sum(1 for a, b in zip(left, right) if a != b), len(left))


def inner_face_edge_accent_pixels(pixels: list[int], width: int,
                                  box: dict[str, int]) -> int:
    margin_x = max(1, box["width"] * DISPLAY_EDGE_CLEAR_MARGIN_PERCENT // 100)
    margin_y = max(1, box["height"] * DISPLAY_EDGE_CLEAR_MARGIN_PERCENT // 100)
    count = 0
    for y in range(box["y"], box["y"] + box["height"]):
        for x in range(box["x"], box["x"] + box["width"]):
            local_x = x - box["x"]
            local_y = y - box["y"]
            if (local_x < margin_x or local_x >= box["width"] - margin_x or
                    local_y < margin_y or local_y >= box["height"] - margin_y):
                count += pixels[y * width + x]
    return count


def outer_display_margin_pixels(pixels: list[int], width: int, height: int) -> int:
    margin_x = max(1, width * DISPLAY_EDGE_CLEAR_MARGIN_PERCENT // 100)
    margin_y = max(1, height * DISPLAY_EDGE_CLEAR_MARGIN_PERCENT // 100)
    return sum(
        pixels[y * width + x]
        for y in range(height)
        for x in range(width)
        if x < margin_x or x >= width - margin_x or y < margin_y or y >= height - margin_y
    )


def expression_fixture_rows(manifest: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fixture in manifest.get("fixtures", []):
        if not isinstance(fixture, dict):
            continue
        fixture_id = str(fixture.get("id", ""))
        if not fixture_id.startswith("expression_"):
            continue
        expression = fixture_id.removeprefix("expression_")
        path = REPO_ROOT / str(fixture.get("path", ""))
        require(path.exists(), f"missing expression PBM fixture {fixture.get('path')}", errors)
        if not path.exists():
            continue
        data = path.read_bytes()
        width, height, pixels = parse_pbm(data, rel(path))
        box = expression_face_box(width, height)
        face = crop_pixels(pixels, width, box)
        full_black = sum(pixels)
        face_black = sum(face)
        rows.append(
            {
                "expression": expression,
                "variant": str(fixture.get("variant", "")),
                "path": rel(path),
                "sha256": sha256_hex(data),
                "manifest_sha256": str(fixture.get("sha256", "")),
                "width": width,
                "height": height,
                "full_black_pixels": full_black,
                "full_ink_ratio_ppm": ratio_ppm(full_black, len(pixels)),
                "face_box": box,
                "face_black_pixels": face_black,
                "face_ink_ratio_ppm": ratio_ppm(face_black, len(face)),
                "inner_face_edge_accent_pixels": inner_face_edge_accent_pixels(pixels, width, box),
                "outer_display_margin_pixels": outer_display_margin_pixels(pixels, width, height),
                "display_edge_clear_margin_percent": DISPLAY_EDGE_CLEAR_MARGIN_PERCENT,
                "_pixels": pixels,
                "_face_pixels": face,
            }
        )
    return rows


def pairwise_distances(rows: list[dict[str, Any]], key: str) -> tuple[int, dict[str, Any]]:
    distances: list[dict[str, Any]] = []
    for left, right in combinations(rows, 2):
        distances.append(
            {
                "left": left["expression"],
                "right": right["expression"],
                "distance_ppm": distance_ppm(left[key], right[key]),
            }
        )
    closest = min(distances, key=lambda item: int(item["distance_ppm"]))
    return int(closest["distance_ppm"]), closest


def build_contract() -> dict[str, Any]:
    errors: list[str] = []
    manifest = load_json(MANIFEST)
    rows = expression_fixture_rows(manifest, errors)
    if errors:
        raise RuntimeError("; ".join(errors))

    metrics: list[dict[str, Any]] = []
    distance_by_variant: list[dict[str, Any]] = []
    for variant in sorted(DISPLAY_VARIANTS):
        variant_rows = sorted(
            [row for row in rows if row["variant"] == variant],
            key=lambda row: str(row["expression"]),
        )
        full_distance, closest_full = pairwise_distances(variant_rows, "_pixels")
        face_distance, closest_face = pairwise_distances(variant_rows, "_face_pixels")
        distance_by_variant.append(
            {
                "variant": variant,
                "minimum_full_image_distance_ppm": full_distance,
                "closest_full_image_pair": closest_full,
                "minimum_face_crop_distance_ppm": face_distance,
                "closest_face_crop_pair": closest_face,
            }
        )
        for row in variant_rows:
            public_row = {key: value for key, value in row.items() if not key.startswith("_")}
            metrics.append(public_row)

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Guard the generated inner-face baseline against blank, overfilled, duplicate, "
            "or display-edge shell artwork while allowing small reference-derived accents at "
            "the inner-face boundary."
        ),
        "source_manifest": rel(MANIFEST),
        "source_catalog": rel(CATALOG),
        "expression_count": len(EXPRESSION_KINDS),
        "expressions": sorted(EXPRESSION_KINDS),
        "variants": sorted(DISPLAY_VARIANTS),
        "thresholds": {
            "full_ink_ratio_ppm_min": FULL_INK_RATIO_PPM_MIN,
            "full_ink_ratio_ppm_max": FULL_INK_RATIO_PPM_MAX,
            "face_ink_ratio_ppm_min": FACE_INK_RATIO_PPM_MIN,
            "face_ink_ratio_ppm_max": FACE_INK_RATIO_PPM_MAX,
            "minimum_full_image_distance_ppm": MIN_FULL_DISTANCE_PPM,
            "minimum_face_crop_distance_ppm": MIN_FACE_DISTANCE_PPM,
            "display_edge_clear_margin_percent": DISPLAY_EDGE_CLEAR_MARGIN_PERCENT,
            "maximum_inner_face_edge_accent_pixels": MAX_INNER_FACE_EDGE_ACCENT_PIXELS,
        },
        "metrics": metrics,
        "distance_by_variant": distance_by_variant,
        "validation_commands": [
            "python .\\tools\\render_epaper_fixtures.py --self-test",
            "python .\\tools\\verify_expression_visual_contract.py",
            "python .\\tools\\verify_epaper_assets.py",
        ],
    }


def check_contract(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected visual contract schema", errors)
    require(data.get("status") == "PASS", "visual contract must be PASS", errors)
    require(data.get("expressions") == sorted(EXPRESSION_KINDS), "visual contract expression set drifted", errors)
    require(data.get("variants") == sorted(DISPLAY_VARIANTS), "visual contract variant set drifted", errors)

    metrics = data.get("metrics", [])
    expected_count = len(EXPRESSION_KINDS) * len(DISPLAY_VARIANTS)
    require(len(metrics) == expected_count, "visual contract metric count drifted", errors)
    seen = {(metric.get("variant"), metric.get("expression")) for metric in metrics if isinstance(metric, dict)}
    for variant in DISPLAY_VARIANTS:
        for expression in EXPRESSION_KINDS:
            require((variant, expression) in seen, f"visual contract missing {variant}/{expression}", errors)

    for metric in metrics:
        if not isinstance(metric, dict):
            errors.append("visual contract metric must be an object")
            continue
        path = REPO_ROOT / str(metric.get("path", ""))
        require(path.exists(), f"visual contract references missing PBM {metric.get('path')}", errors)
        require(metric.get("sha256") == metric.get("manifest_sha256"), f"{metric.get('path')} hash drifted from manifest", errors)
        require(
            FULL_INK_RATIO_PPM_MIN <= int(metric.get("full_ink_ratio_ppm", 0)) <= FULL_INK_RATIO_PPM_MAX,
            f"{metric.get('variant')}/{metric.get('expression')} full ink ratio out of bounds",
            errors,
        )
        require(
            FACE_INK_RATIO_PPM_MIN <= int(metric.get("face_ink_ratio_ppm", 0)) <= FACE_INK_RATIO_PPM_MAX,
            f"{metric.get('variant')}/{metric.get('expression')} face ink ratio out of bounds",
            errors,
        )
        require(
            int(metric.get("outer_display_margin_pixels", -1)) == 0,
            f"{metric.get('variant')}/{metric.get('expression')} draws pixels in the shell-owned display margin",
            errors,
        )
        require(
            int(metric.get("inner_face_edge_accent_pixels", -1)) <= MAX_INNER_FACE_EDGE_ACCENT_PIXELS,
            f"{metric.get('variant')}/{metric.get('expression')} exceeds the generated inner-face accent boundary",
            errors,
        )
        box = metric.get("face_box", {})
        require(isinstance(box, dict) and int(box.get("width", 0)) > 0 and int(box.get("height", 0)) > 0, "face box must be populated", errors)

    for entry in data.get("distance_by_variant", []):
        if not isinstance(entry, dict):
            errors.append("visual distance entry must be an object")
            continue
        require(
            int(entry.get("minimum_full_image_distance_ppm", 0)) >= MIN_FULL_DISTANCE_PPM,
            f"{entry.get('variant')} full-image visual distance below threshold",
            errors,
        )
        require(
            int(entry.get("minimum_face_crop_distance_ppm", 0)) >= MIN_FACE_DISTANCE_PPM,
            f"{entry.get('variant')} face-crop visual distance below threshold",
            errors,
        )


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    index = read(ACCEPTANCE_INDEX, errors)
    catalog = read(CATALOG, errors)
    for token in [
        "expression_visual_contract",
        "Expression visual contract",
        "companion-screen-expression-visual-contract.json",
        "verify_expression_visual_contract.py",
        "visually duplicate faces",
    ]:
        require(token in screen_doc, f"screen doc missing visual contract anchor {token}", errors)
    for token in [
        "visual contract",
        "verify_expression_visual_contract.py",
        "WBA",
    ]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing visual contract anchor {token}", errors)
    require("visual contract" in readme.lower(), "e-paper README missing visual contract note", errors)
    require(fixture_rel in index, "acceptance index missing visual contract fixture", errors)
    require("sync_complete" in catalog and "happy" in catalog, "expression catalog missing sync_complete/happy anchors", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression visual contract fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_contract(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic visual contract JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    errors: list[str] = []
    for path in [MANIFEST, CATALOG]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_contract() if not errors else {}
    if expected:
        check_contract(expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: ExpressionV1 visual contract checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: ExpressionV1 visual contract verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
