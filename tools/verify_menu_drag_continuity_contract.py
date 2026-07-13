#!/usr/bin/env python3
"""Guard the menu-v3 one-frame home contract after retiring legacy scrolling."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs" / "validation" / "epaper"
MANIFEST = ROOT / "app" / "companion_pendant" / "epaper" / "assets" / "emote_matrix_white_200x200.json"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-screen-menu-drag-continuity-contract.json"
DEFAULT_MD = ROOT / "docs" / "validation" / "companion-screen-menu-drag-continuity-contract.md"
PROJECT_PLAN = ROOT / "docs" / "companion_screen_project_plan.md"
SCREEN_DOC = ROOT / "docs" / "companion_screen_expression_system.md"
README = ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

SCHEMA_ID = "companion.screen.menu_v3_static_home_contract.v1"
LANGUAGES = ("zh", "en")
FRAME_COUNT = 1
HOME_ROWS = 6


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_home(language: str) -> Image.Image:
    path = ASSET_DIR / f"menu_home_{language}_1_54in.pbm"
    image = Image.open(path).convert("1")
    if image.size != (200, 200):
        raise ValueError(f"{rel(path)} must stay 200x200")
    return image


def black_pixels(image: Image.Image) -> int:
    return sum(pixel == 0 for pixel in image.getdata())


def analyze_language(language: str) -> dict[str, Any]:
    image = load_home(language)
    selected = black_pixels(image.crop((5, 35, 195, 61)))
    rows = [black_pixels(image.crop((5, 35 + index * 26, 195, 61 + index * 26)))
            for index in range(HOME_ROWS)]
    return {
        "language": language,
        "frame_count": FRAME_COUNT,
        "black_pixels": black_pixels(image),
        "selected_row_black_pixels": selected,
        "row_black_pixels": rows,
    }


def build_contract() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    menu_home_clips = {
        clip["name"]: clip for clip in manifest.get("clips", [])
        if clip.get("name") in {"menu.home.zh", "menu.home.en"}
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Guard the owner-approved menu-v3 home as one stable 200x200 "
            "external-Flash frame per language. The six-row source layout "
            "replaces legacy numbered scrolling home frames."
        ),
        "frame_count_per_language": FRAME_COUNT,
        "home_rows": HOME_ROWS,
        "home_scroll_policy": "retired by the six-row menu-v3 source reference",
        "manifest_home_frames": {
            name: len(clip.get("frames", [])) for name, clip in menu_home_clips.items()
        },
        "languages": [analyze_language(language) for language in LANGUAGES],
        "validation_commands": [
            "python .\\tools\\verify_menu_drag_continuity_contract.py",
            "python .\\tools\\verify_screen_menu_assets.py",
            "python .\\tools\\verify_screen_presentation.py",
        ],
    }


def check_contract(contract: dict[str, Any], errors: list[str]) -> None:
    if contract.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if contract.get("status") != "PASS":
        errors.append("menu-v3 static home contract must be PASS")
    if contract.get("frame_count_per_language") != FRAME_COUNT:
        errors.append("home frame count drifted")
    if contract.get("home_rows") != HOME_ROWS:
        errors.append("menu-v3 must retain all six home rows")
    expected_clips = {"menu.home.zh": 1, "menu.home.en": 1}
    if contract.get("manifest_home_frames") != expected_clips:
        errors.append("normal CEMP manifest must retain exactly one home frame per language")
    for entry in contract.get("languages", []):
        language = str(entry.get("language", ""))
        if entry.get("frame_count") != FRAME_COUNT:
            errors.append(f"{language} frame count drifted")
        if int(entry.get("black_pixels", 0)) < 700:
            errors.append(f"{language} home appears blank")
        if int(entry.get("selected_row_black_pixels", 0)) < 1000:
            errors.append(f"{language} lost the source-layout selected row")
        rows = entry.get("row_black_pixels", [])
        if len(rows) != HOME_ROWS or any(int(value) < 30 for value in rows):
            errors.append(f"{language} lost a visible source-layout home row")


def render_markdown(contract: dict[str, Any]) -> str:
    lines = [
        "# Companion Menu v3 Static Home Contract",
        "",
        "This file is generated. Update it with",
        "`python .\\tools\\verify_menu_drag_continuity_contract.py --write`.",
        "",
        f"- Frames per language: `{contract['frame_count_per_language']}`",
        f"- Visible home rows: `{contract['home_rows']}`",
        f"- Scroll policy: `{contract['home_scroll_policy']}`",
        "",
        "## Languages",
        "",
        "| Language | Black Pixels | Selected Row Pixels | Row Pixels |",
        "|---|---:|---:|---|",
    ]
    for entry in contract["languages"]:
        lines.append(
            f"| `{entry['language']}` | `{entry['black_pixels']}` | "
            f"`{entry['selected_row_black_pixels']}` | `{entry['row_black_pixels']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def check_project_links(errors: list[str]) -> None:
    for path, label in ((PROJECT_PLAN, "project plan"), (SCREEN_DOC, "screen doc"), (README, "epaper README")):
        text = path.read_text(encoding="utf-8")
        for token in ("verify_menu_drag_continuity_contract.py", "menu-v3 static home contract"):
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
    print(f"PASS: menu-v3 static home contract verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
