#!/usr/bin/env python3
"""Verify the premium pet face uses whole-face motion, not eye-only swaps."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs" / "validation" / "epaper"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-screen-premium-pet-art-contract.json"
DEFAULT_MD = ROOT / "docs" / "validation" / "companion-screen-premium-pet-art-contract.md"
STYLE_DOC = ROOT / "docs" / "validation" / "companion-screen-generated-art-style-contract.md"
STYLE_SNAPSHOT = ROOT / "docs" / "validation" / "companion-screen-generated-art-style-contract.json"
SCREEN_DOC = ROOT / "docs" / "companion_screen_expression_system.md"
PROJECT_PLAN = ROOT / "docs" / "companion_screen_project_plan.md"
README = ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

SCHEMA_ID = "companion.screen.premium_pet_art_contract.v1"
STYLE_NAME = "genref_sheet_12_inner_faces_v5"
PRIMARY_PANEL = "1.54in"

POSE_SHEET = [
    ("idle_calm", "expression_idle_1_54in.pbm", "reference base"),
    ("curious_tap", "expression_happy_attention_1_54in.pbm", "tap response"),
    ("left_swipe", "expression_happy_attention_left_1_54in.pbm", "left stroke"),
    ("right_swipe", "expression_happy_attention_right_1_54in.pbm", "right stroke"),
    ("up_swipe", "expression_happy_attention_up_1_54in.pbm", "up stroke"),
    ("down_swipe", "expression_happy_attention_down_1_54in.pbm", "down stroke"),
    ("listening", "expression_listening_wave_1_54in.pbm", "listening wave"),
    ("thinking", "expression_thinking_outward_1_54in.pbm", "thinking bubble"),
    ("recording", "expression_recording_pulse_1_54in.pbm", "recording pulse"),
    ("speaking", "expression_speaking_open_1_54in.pbm", "speaking open mouth"),
    ("happy", "expression_happy_bright_1_54in.pbm", "bright happy"),
    ("sleepy", "expression_sleepy_yawn_1_54in.pbm", "sleepy yawn"),
]

ZONES = {
    "upper_marks": (35, 18, 165, 55),
    "eyes_brows": (35, 45, 165, 105),
    "mouth_nose": (45, 92, 155, 145),
    "cheeks_lower_marks": (15, 112, 185, 165),
    "full_inner_face": (8, 8, 192, 192),
}

ZONE_DISTANCE_THRESHOLDS = {
    "upper_marks": 120,
    "eyes_brows": 400,
    "mouth_nose": 240,
    "cheeks_lower_marks": 200,
}
MIN_CHANGED_ZONES = 3
MIN_FULL_DISTANCE = 1000
OUTER_CLEAR_MARGIN_PERCENT = 5


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def parse_pbm(path: pathlib.Path) -> tuple[int, int, list[int]]:
    data = path.read_bytes()
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
        raise ValueError(f"{rel(path)} is not a binary PBM")
    while index < len(data) and data[index:index + 1].isspace():
        index += 1
    width = int(tokens[1])
    height = int(tokens[2])
    row_bytes = (width + 7) // 8
    payload = data[index:index + row_bytes * height]
    if len(payload) != row_bytes * height:
        raise ValueError(f"{rel(path)} PBM payload is truncated")
    pixels: list[int] = []
    for y in range(height):
        row_start = y * row_bytes
        for x in range(width):
            pixels.append(1 if payload[row_start + (x // 8)] & (0x80 >> (x % 8)) else 0)
    return width, height, pixels


def crop(pixels: list[int], width: int, box: tuple[int, int, int, int]) -> list[int]:
    x0, y0, x1, y1 = box
    return [pixels[y * width + x] for y in range(y0, y1) for x in range(x0, x1)]


def distance(left: list[int], right: list[int]) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


def outer_margin_pixels(pixels: list[int], width: int, height: int) -> int:
    margin_x = max(1, width * OUTER_CLEAR_MARGIN_PERCENT // 100)
    margin_y = max(1, height * OUTER_CLEAR_MARGIN_PERCENT // 100)
    count = 0
    for y in range(height):
        for x in range(width):
            if x < margin_x or x >= width - margin_x or y < margin_y or y >= height - margin_y:
                count += pixels[y * width + x]
    return count


def build_contract() -> dict[str, Any]:
    style_snapshot = json.loads(STYLE_SNAPSHOT.read_text(encoding="utf-8"))
    base_path = ASSET_DIR / POSE_SHEET[0][1]
    width, height, base_pixels = parse_pbm(base_path)
    rows: list[dict[str, Any]] = []
    for pose_id, filename, intent in POSE_SHEET:
        path = ASSET_DIR / filename
        pose_width, pose_height, pixels = parse_pbm(path)
        if (pose_width, pose_height) != (width, height):
            raise ValueError(f"{rel(path)} size drifted from {width}x{height}")
        zone_black = {name: sum(crop(pixels, width, box)) for name, box in ZONES.items()}
        zone_distance = {
            name: distance(crop(pixels, width, box), crop(base_pixels, width, box))
            for name, box in ZONES.items()
        }
        changed_zones = [
            name for name, threshold in ZONE_DISTANCE_THRESHOLDS.items()
            if zone_distance[name] >= threshold
        ]
        rows.append(
            {
                "pose_id": pose_id,
                "intent": intent,
                "path": rel(path),
                "zone_black_pixels": zone_black,
                "zone_distance_from_idle": zone_distance,
                "changed_zone_count": 0 if pose_id == "idle_calm" else len(changed_zones),
                "changed_zones": [] if pose_id == "idle_calm" else changed_zones,
                "outer_margin_pixels": outer_margin_pixels(pixels, width, height),
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "style_name": STYLE_NAME,
        "primary_panel": PRIMARY_PANEL,
        "purpose": (
            "Guard the premium electronic-pet art direction: white background, "
            "physical shell owns the cat outline, and interaction poses move "
            "eyes/brows, mouth/nose, cheeks, and ornaments together."
        ),
        "source_style_contract": rel(STYLE_DOC),
        "style_snapshot": rel(STYLE_SNAPSHOT),
        "style_snapshot_name": style_snapshot.get("style_name"),
        "thresholds": {
            "minimum_changed_zones_from_idle": MIN_CHANGED_ZONES,
            "minimum_full_inner_face_distance_from_idle": MIN_FULL_DISTANCE,
            "zone_distance_thresholds": ZONE_DISTANCE_THRESHOLDS,
            "outer_clear_margin_percent": OUTER_CLEAR_MARGIN_PERCENT,
        },
        "pose_count": len(rows),
        "poses": rows,
        "validation_commands": [
            "python .\\tools\\verify_premium_pet_art_contract.py",
            "python .\\tools\\verify_expression_visual_contract.py",
            "python .\\tools\\verify_epaper_assets.py",
        ],
    }


def render_markdown(contract: dict[str, Any]) -> str:
    lines = [
        "# Companion Premium Pet Art Contract",
        "",
        "This file is generated. Update it with",
        "`python .\\tools\\verify_premium_pet_art_contract.py --write`.",
        "",
        f"- Style: `{contract['style_name']}`",
        f"- Primary panel: `{contract['primary_panel']}`",
        f"- Pose count: `{contract['pose_count']}`",
        "",
        "## Pose Metrics",
        "",
        "| Pose | Changed Zones | Full Distance | Outer Margin |",
        "|---|---:|---:|---:|",
    ]
    for row in contract["poses"]:
        lines.append(
            f"| `{row['pose_id']}` | `{row['changed_zone_count']}` | "
            f"`{row['zone_distance_from_idle']['full_inner_face']}` | "
            f"`{row['outer_margin_pixels']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def check_contract(contract: dict[str, Any], errors: list[str]) -> None:
    if contract.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if contract.get("status") != "PASS":
        errors.append("premium pet art contract must be PASS")
    if contract.get("style_name") != STYLE_NAME:
        errors.append("premium pet art style name drifted")
    if contract.get("style_snapshot_name") != STYLE_NAME:
        errors.append("style snapshot name must match premium contract style")
    poses = contract.get("poses", [])
    if len(poses) != len(POSE_SHEET):
        errors.append("pose sheet count drifted")
    for row in poses:
        pose_id = str(row.get("pose_id", ""))
        if row.get("outer_margin_pixels") != 0:
            errors.append(f"{pose_id} draws pixels in the shell-owned outer margin")
        if pose_id == "idle_calm":
            continue
        if int(row.get("changed_zone_count", 0)) < MIN_CHANGED_ZONES:
            errors.append(f"{pose_id} changes too few face zones")
        distance_from_idle = row.get("zone_distance_from_idle", {})
        if int(distance_from_idle.get("full_inner_face", 0)) < MIN_FULL_DISTANCE:
            errors.append(f"{pose_id} is too close to idle")
        if "mouth_nose" not in row.get("changed_zones", []):
            errors.append(f"{pose_id} must include mouth/nose motion, not only eye motion")


def check_project_links(errors: list[str]) -> None:
    for path, label in ((SCREEN_DOC, "screen doc"), (PROJECT_PLAN, "project plan"), (README, "epaper README")):
        text = path.read_text(encoding="utf-8")
        for token in ("verify_premium_pet_art_contract.py", "premium pet art contract"):
            if token not in text:
                errors.append(f"{label} missing {token}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    md_path = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown

    errors: list[str] = []
    try:
        contract = build_contract()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    check_contract(contract, errors)
    check_project_links(errors)

    rendered_json = json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    rendered_md = render_markdown(contract)
    if args.write:
        json_path.write_text(rendered_json, encoding="utf-8")
        md_path.write_text(rendered_md, encoding="utf-8")
    else:
        if not json_path.exists() or json_path.read_text(encoding="utf-8") != rendered_json:
            errors.append(f"{rel(json_path)} is stale; rerun with --write")
        if not md_path.exists() or md_path.read_text(encoding="utf-8") != rendered_md:
            errors.append(f"{rel(md_path)} is stale; rerun with --write")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: premium pet art contract verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
