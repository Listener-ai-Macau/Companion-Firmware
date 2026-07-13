#!/usr/bin/env python3
"""Verify ExpressionV1 copy fits the renderer layout on supported screens."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import textwrap
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import DISPLAY_VARIANTS, EXPRESSION_COPY, EXPRESSION_KINDS  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-layout-contract.json")
SCHEMA_ID = "companion.pendant.screen_expression_layout_contract.v1"

RENDERER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "card_renderer.py"
CATALOG = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-catalog.json"
VISUAL_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-visual-contract.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"


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


def wrap_lines(text: str, max_chars: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return textwrap.wrap(
        normalized,
        width=max(1, max_chars),
        break_long_words=True,
        replace_whitespace=True,
    )


def layout_budget(width: int, height: int) -> dict[str, int]:
    margin = 8 if width <= 200 else 7
    header_h = 25 if height <= 130 else 30
    footer_h = 17 if height <= 130 else 22
    title_scale = 2 if height <= 130 else 3
    body_scale = 1
    if height <= 130:
        face_size = min(74, height - header_h - footer_h - margin)
        face_x = margin + 2
        face_y = header_h + (height - header_h - footer_h - face_size) // 2
        body_x = face_x + face_size + margin
        body_y = header_h + margin + 2
        body_width = width - body_x - margin
        body_max_lines = 4
        body_line_step = 10
    else:
        face_size = min(112, width - 2 * margin, height - header_h - footer_h - 44)
        face_x = (width - face_size) // 2
        face_y = header_h + 7
        body_x = margin
        body_y = face_y + face_size + 9
        body_width = width - 2 * margin
        remaining = height - footer_h - body_y - 2
        body_line_step = 8 * body_scale + 2
        body_max_lines = max(1, remaining // body_line_step)
    return {
        "margin": margin,
        "header_h": header_h,
        "footer_h": footer_h,
        "title_scale": title_scale,
        "body_scale": body_scale,
        "title_max_chars": max(4, (width - 2 * margin) // (6 * title_scale)),
        "footer_max_chars": max(1, (width - 2 * margin) // 6),
        "body_x": body_x,
        "body_y": body_y,
        "body_width": body_width,
        "body_max_chars": max(8, body_width // (6 * body_scale)),
        "body_max_lines": body_max_lines,
        "body_line_step": body_line_step,
        "face_x": face_x,
        "face_y": face_y,
        "face_size": face_size,
        "content_bottom_y": height - footer_h,
    }


def expression_metric(expression: str, variant_key: str, variant: Any) -> dict[str, Any]:
    title, body, footer = EXPRESSION_COPY[expression]
    budget = layout_budget(int(variant.width), int(variant.height))
    body_lines = wrap_lines(body, budget["body_max_chars"])
    title_fits = len(title.upper()) <= budget["title_max_chars"]
    body_fits = len(body_lines) <= budget["body_max_lines"]
    footer_fits = len(footer.upper()) <= budget["footer_max_chars"]
    rendered_body_lines = body_lines[: budget["body_max_lines"]]
    body_bottom_y = budget["body_y"]
    if rendered_body_lines:
        body_bottom_y += (len(rendered_body_lines) - 1) * budget["body_line_step"] + 7 * budget["body_scale"]
    title_bottom_y = 6 + 7 * budget["title_scale"]
    footer_bottom_y = int(variant.height) - budget["footer_h"] + 5 + 7
    return {
        "expression": expression,
        "variant": variant_key,
        "title": title,
        "body": body,
        "footer": footer,
        "title_chars": len(title.upper()),
        "title_max_chars": budget["title_max_chars"],
        "title_fits": title_fits,
        "body_lines": body_lines,
        "body_line_count": len(body_lines),
        "body_max_chars": budget["body_max_chars"],
        "body_max_lines": budget["body_max_lines"],
        "body_fits": body_fits,
        "footer_chars": len(footer.upper()),
        "footer_max_chars": budget["footer_max_chars"],
        "footer_fits": footer_fits,
        "title_bottom_y": title_bottom_y,
        "header_bottom_y": budget["header_h"],
        "body_bottom_y": body_bottom_y,
        "content_bottom_y": budget["content_bottom_y"],
        "footer_bottom_y": footer_bottom_y,
        "screen_height": int(variant.height),
        "layout": budget,
    }


def build_contract() -> dict[str, Any]:
    metrics: list[dict[str, Any]] = []
    for variant_key, variant in DISPLAY_VARIANTS.items():
        for expression in sorted(EXPRESSION_KINDS):
            metrics.append(expression_metric(expression, variant_key, variant))
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Guard ExpressionV1 title/body/footer copy against renderer truncation or vertical overlap on supported e-paper variants.",
        "sources": {
            "renderer": rel(RENDERER),
            "catalog": rel(CATALOG),
            "visual_contract": rel(VISUAL_CONTRACT),
        },
        "variants": sorted(DISPLAY_VARIANTS),
        "expressions": sorted(EXPRESSION_KINDS),
        "acceptance": {
            "all_titles_fit": all(metric["title_fits"] for metric in metrics),
            "all_bodies_fit": all(metric["body_fits"] for metric in metrics),
            "all_footers_fit": all(metric["footer_fits"] for metric in metrics),
            "no_title_header_overlap": all(metric["title_bottom_y"] < metric["header_bottom_y"] for metric in metrics),
            "no_body_footer_overlap": all(metric["body_bottom_y"] < metric["content_bottom_y"] for metric in metrics),
            "footer_stays_on_screen": all(metric["footer_bottom_y"] <= metric["screen_height"] for metric in metrics),
            "wba_reuses_same_copy_budget": True,
        },
        "metrics": metrics,
        "validation_commands": [
            "python .\\tools\\verify_expression_layout_contract.py",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_visual_contract.py",
            "python .\\tools\\verify_epaper_assets.py",
        ],
    }


def check_contract(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected layout contract schema", errors)
    require(data.get("status") == "PASS", "layout contract fixture must be PASS", errors)
    require(data.get("expressions") == sorted(EXPRESSION_KINDS), "layout contract expression set drifted", errors)
    require(data.get("variants") == sorted(DISPLAY_VARIANTS), "layout contract variant set drifted", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "all_titles_fit",
        "all_bodies_fit",
        "all_footers_fit",
        "no_title_header_overlap",
        "no_body_footer_overlap",
        "footer_stays_on_screen",
        "wba_reuses_same_copy_budget",
    ]:
        require(acceptance.get(token) is True, f"layout acceptance missing {token}", errors)
    expected_count = len(EXPRESSION_KINDS) * len(DISPLAY_VARIANTS)
    metrics = data.get("metrics", [])
    require(len(metrics) == expected_count, "layout metric count drifted", errors)
    for metric in metrics:
        if not isinstance(metric, dict):
            errors.append("layout metric must be an object")
            continue
        label = f"{metric.get('variant')}/{metric.get('expression')}"
        require(metric.get("title_fits") is True, f"{label} title would truncate", errors)
        require(metric.get("body_fits") is True, f"{label} body would truncate", errors)
        require(metric.get("footer_fits") is True, f"{label} footer would truncate", errors)
        require(int(metric.get("title_bottom_y", 0)) < int(metric.get("header_bottom_y", 0)), f"{label} title overlaps header edge", errors)
        require(int(metric.get("body_bottom_y", 0)) < int(metric.get("content_bottom_y", 0)), f"{label} body overlaps footer area", errors)
        require(int(metric.get("footer_bottom_y", 0)) <= int(metric.get("screen_height", 0)), f"{label} footer runs off screen", errors)
        require(int(metric.get("body_max_lines", 0)) >= int(metric.get("body_line_count", 0)), f"{label} body line budget too small", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    index = read(ACCEPTANCE_INDEX, errors)
    renderer = read(RENDERER, errors)
    for token in [
        "expression_layout_contract",
        "Expression layout contract",
        "companion-screen-expression-layout-contract.json",
        "verify_expression_layout_contract.py",
        "title/body/footer",
    ]:
        require(token in screen_doc, f"screen doc missing layout contract anchor {token}", errors)
    for token in ["layout contract", "verify_expression_layout_contract.py", "WBA"]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing layout contract anchor {token}", errors)
    require("layout contract" in readme.lower(), "e-paper README missing layout contract note", errors)
    require(fixture_rel in index, "acceptance index missing layout contract fixture", errors)
    require("body_scale = 1" in renderer, "renderer must keep ExpressionV1 body scale at 1 for layout fit", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression layout contract fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_contract(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic layout contract JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    errors: list[str] = []
    for path in [RENDERER, CATALOG, VISUAL_CONTRACT]:
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
        print("FAIL: ExpressionV1 layout contract checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: ExpressionV1 layout contract verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
