#!/usr/bin/env python3
"""Verify menu home frames preserve finger-like continuous drag semantics."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs" / "validation" / "epaper"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-screen-menu-drag-continuity-contract.json"
DEFAULT_MD = ROOT / "docs" / "validation" / "companion-screen-menu-drag-continuity-contract.md"
PROJECT_PLAN = ROOT / "docs" / "companion_screen_project_plan.md"
SCREEN_DOC = ROOT / "docs" / "companion_screen_expression_system.md"
README = ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

SCHEMA_ID = "companion.screen.menu_drag_continuity_contract.v1"
LANGUAGES = ("zh", "en")
FRAME_COUNT = 43
HEADER_BOTTOM = 38
CONTENT_DIFF_MIN = 3000
CONTENT_DIFF_MAX = 14000
ORDINARY_DIFF_MAX = 7000
MAX_ALLOWED_LARGE_DIFFS = 2
MIN_SCROLLBAR_ADVANCE_PX = 45


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_frame(language: str, frame: int) -> Image.Image:
    suffix = "" if frame == 0 else str(frame)
    path = ASSET_DIR / f"menu_home{suffix}_{language}_1_54in.pbm"
    if not path.exists():
        raise FileNotFoundError(rel(path))
    image = Image.open(path).convert("1")
    if image.size != (200, 200):
        raise ValueError(f"{rel(path)} must stay 200x200")
    return image


def pixels(image: Image.Image) -> list[int]:
    return [0 if pixel == 255 else 1 for pixel in image.getdata()]


def pixel_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(pixels(left), pixels(right)))


def crop_distance(left: Image.Image, right: Image.Image, box: tuple[int, int, int, int]) -> int:
    return pixel_distance(left.crop(box), right.crop(box))


def has_black(image: Image.Image, box: tuple[int, int, int, int]) -> bool:
    return any(pixel == 0 for pixel in image.crop(box).getdata())


def scrollbar_top(image: Image.Image) -> int:
    rows: list[int] = []
    for y in range(HEADER_BOTTOM, 196):
        # x=196 and x=198 are the static scrollbar rails.  The thumb fills
        # the center column, so x=197 is the stable movement signal.
        if image.getpixel((197, y)) == 0:
            rows.append(y)
    if not rows:
        return -1
    runs: list[tuple[int, int]] = []
    start = prev = rows[0]
    for y in rows[1:]:
        if y == prev + 1:
            prev = y
        else:
            runs.append((start, prev))
            start = prev = y
    runs.append((start, prev))
    start, _end = max(runs, key=lambda item: item[1] - item[0])
    return start


def analyze_language(language: str) -> dict[str, Any]:
    frames = [load_frame(language, index) for index in range(FRAME_COUNT)]
    header_reference = frames[0].crop((0, 0, 200, HEADER_BOTTOM)).tobytes()
    adjacent: list[dict[str, int]] = []
    scroll_tops: list[int] = []
    for index, image in enumerate(frames):
        if image.crop((0, 0, 200, HEADER_BOTTOM)).tobytes() != header_reference:
            raise ValueError(f"{language} frame {index} fixed header drifted")
        if has_black(image, (0, 32, 200, HEADER_BOTTOM)):
            raise ValueError(f"{language} frame {index} overwrites the white header gutter")
        scroll_tops.append(scrollbar_top(image))
        if index == 0:
            continue
        full_diff = pixel_distance(frames[index - 1], image)
        content_diff = crop_distance(frames[index - 1], image, (0, HEADER_BOTTOM, 196, 196))
        adjacent.append({"frame": index, "full_diff": full_diff, "content_diff": content_diff})

    large_diffs = [
        row for row in adjacent
        if int(row["content_diff"]) > ORDINARY_DIFF_MAX
    ]
    return {
        "language": language,
        "frame_count": len(frames),
        "scrollbar_tops": scroll_tops,
        "scrollbar_total_advance_px": scroll_tops[-1] - scroll_tops[0],
        "adjacent_diffs": adjacent,
        "content_diff_min": min(row["content_diff"] for row in adjacent),
        "content_diff_max": max(row["content_diff"] for row in adjacent),
        "large_diff_frames": [row["frame"] for row in large_diffs],
        "large_diff_count": len(large_diffs),
    }


def build_contract() -> dict[str, Any]:
    analyses = [analyze_language(language) for language in LANGUAGES]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Guard the menu home PBM sequence as a finger-anchored continuous "
            "drag surface: fixed top bar, white gutter, monotonic scrollbar, "
            "and bounded adjacent-frame changes."
        ),
        "frame_quantum_px": 2,
        "frame_count_per_language": FRAME_COUNT,
        "thresholds": {
            "content_diff_min": CONTENT_DIFF_MIN,
            "content_diff_max": CONTENT_DIFF_MAX,
            "ordinary_content_diff_max": ORDINARY_DIFF_MAX,
            "max_allowed_large_diffs": MAX_ALLOWED_LARGE_DIFFS,
            "minimum_scrollbar_advance_px": MIN_SCROLLBAR_ADVANCE_PX,
        },
        "languages": analyses,
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
        errors.append("menu drag continuity contract must be PASS")
    if contract.get("frame_count_per_language") != FRAME_COUNT:
        errors.append("home frame count drifted")
    for entry in contract.get("languages", []):
        language = str(entry.get("language", ""))
        if entry.get("frame_count") != FRAME_COUNT:
            errors.append(f"{language} frame count drifted")
        tops = entry.get("scrollbar_tops", [])
        if any(not isinstance(top, int) or top < HEADER_BOTTOM for top in tops):
            errors.append(f"{language} scrollbar top missing or enters header")
        if any(int(left) > int(right) for left, right in zip(tops, tops[1:])):
            errors.append(f"{language} scrollbar moves backward")
        if int(entry.get("scrollbar_total_advance_px", 0)) < MIN_SCROLLBAR_ADVANCE_PX:
            errors.append(f"{language} scrollbar barely moves")
        if int(entry.get("large_diff_count", 99)) > MAX_ALLOWED_LARGE_DIFFS:
            errors.append(f"{language} has too many large adjacent jumps")
        if int(entry.get("content_diff_min", 0)) < CONTENT_DIFF_MIN:
            errors.append(f"{language} adjacent frames are too similar")
        if int(entry.get("content_diff_max", 0)) > CONTENT_DIFF_MAX:
            errors.append(f"{language} adjacent frames jump too far")


def render_markdown(contract: dict[str, Any]) -> str:
    lines = [
        "# Companion Menu Drag Continuity Contract",
        "",
        "This file is generated. Update it with",
        "`python .\\tools\\verify_menu_drag_continuity_contract.py --write`.",
        "",
        f"- Frame quantum: `{contract['frame_quantum_px']}` px",
        f"- Frames per language: `{contract['frame_count_per_language']}`",
        "",
        "## Languages",
        "",
        "| Language | Scroll Advance | Diff Min | Diff Max | Large Diffs |",
        "|---|---:|---:|---:|---|",
    ]
    for entry in contract["languages"]:
        lines.append(
            f"| `{entry['language']}` | `{entry['scrollbar_total_advance_px']}` | "
            f"`{entry['content_diff_min']}` | `{entry['content_diff_max']}` | "
            f"`{entry['large_diff_frames']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def check_project_links(errors: list[str]) -> None:
    for path, label in ((PROJECT_PLAN, "project plan"), (SCREEN_DOC, "screen doc"), (README, "epaper README")):
        text = path.read_text(encoding="utf-8")
        for token in ("verify_menu_drag_continuity_contract.py", "menu drag continuity contract"):
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
    print(f"PASS: menu drag continuity contract verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
