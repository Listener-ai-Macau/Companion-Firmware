#!/usr/bin/env python3
"""Render a visual ExpressionV1 contact sheet from e-paper PBM fixtures."""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import EXPRESSION_KINDS, sha256_hex  # noqa: E402


FIXTURE_MANIFEST = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
DEFAULT_SVG = REPO_ROOT / "docs/validation/epaper/expression-preview.svg"
DEFAULT_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-preview.json"
SCHEMA_ID = "companion.pendant.expression_preview.v1"
EXPRESSION_ORDER = [
    "idle",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "sleepy",
    "recording",
    "sync_complete",
    "low_battery",
    "error",
]
VARIANT_ORDER = ["2.13in", "1.54in"]


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_pbm(data: bytes, label: str) -> tuple[int, int, bytes]:
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
        raise ValueError(f"{label}: truncated PBM payload")
    return width, height, payload


def pbm_runs(width: int, height: int, payload: bytes) -> list[tuple[int, int, int]]:
    row_bytes = (width + 7) // 8
    runs: list[tuple[int, int, int]] = []
    for y in range(height):
        x = 0
        while x < width:
            byte = payload[y * row_bytes + (x // 8)]
            black = (byte & (0x80 >> (x % 8))) != 0
            if not black:
                x += 1
                continue
            start = x
            while x < width:
                byte = payload[y * row_bytes + (x // 8)]
                if (byte & (0x80 >> (x % 8))) == 0:
                    break
                x += 1
            runs.append((start, y, x - start))
    return runs


def load_expression_fixtures() -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    fixtures: dict[tuple[str, str], dict[str, Any]] = {}
    for fixture in manifest.get("fixtures", []):
        card = fixture.get("card", {})
        if card.get("card_type") != "expression":
            continue
        expression = str(card.get("state", ""))
        variant = str(fixture.get("variant", ""))
        if expression and variant:
            fixtures[(expression, variant)] = fixture
    return fixtures, manifest


def render_bitmap_group(path: pathlib.Path, x: int, y: int, scale: int, label: str) -> tuple[str, int, int, int]:
    data = path.read_bytes()
    width, height, payload = parse_pbm(data, rel(path))
    runs = pbm_runs(width, height, payload)
    parts = [
        f'<g transform="translate({x},{y})">',
        f'<rect x="0" y="0" width="{width * scale}" height="{height * scale}" fill="#fff"/>',
        f'<rect x="0" y="0" width="{width * scale}" height="{height * scale}" fill="none" stroke="#111" stroke-width="1"/>',
        f'<g transform="scale({scale})" fill="none" stroke="#111" stroke-width="1" shape-rendering="crispEdges">',
    ]
    path_data = " ".join(f"M{run_x} {run_y + 0.5}h{run_width}" for run_x, run_y, run_width in runs)
    parts.append(f'<path d="{path_data}"/>')
    parts.extend(
        [
            "</g>",
            f'<text x="0" y="{height * scale + 16}" font-size="12" fill="#111">{html.escape(label)}</text>',
            "</g>",
        ]
    )
    return "\n".join(parts), width, height, len(runs)


def build_svg() -> tuple[str, dict[str, Any]]:
    fixtures, source_manifest = load_expression_fixtures()
    missing = [
        f"{expression}/{variant}"
        for expression in EXPRESSION_ORDER
        for variant in VARIANT_ORDER
        if (expression, variant) not in fixtures
    ]
    if missing:
        raise ValueError(f"missing expression fixtures: {', '.join(missing)}")

    margin = 24
    label_width = 112
    col_gap = 36
    scale = 1
    col_widths = {"2.13in": 250, "1.54in": 200}
    row_height = 238
    width = margin * 2 + label_width + sum(col_widths[v] for v in VARIANT_ORDER) + col_gap
    height = margin * 2 + 54 + row_height * len(EXPRESSION_ORDER)
    y0 = margin + 54
    x_positions = {
        "2.13in": margin + label_width,
        "1.54in": margin + label_width + col_widths["2.13in"] + col_gap,
    }

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f7f2"/>',
        f'<text x="{margin}" y="{margin + 18}" font-size="20" font-family="Arial, sans-serif" fill="#111">Companion ExpressionV1 Preview</text>',
        f'<text x="{margin}" y="{margin + 40}" font-size="12" font-family="Arial, sans-serif" fill="#333">Golden PBM fixtures rendered as SVG for no-hardware visual acceptance.</text>',
    ]
    preview_items: list[dict[str, Any]] = []
    total_runs = 0
    for row, expression in enumerate(EXPRESSION_ORDER):
        y = y0 + row * row_height
        parts.append(
            f'<text x="{margin}" y="{y + 24}" font-size="16" font-family="Arial, sans-serif" fill="#111">{html.escape(expression)}</text>'
        )
        for variant in VARIANT_ORDER:
            fixture = fixtures[(expression, variant)]
            path = REPO_ROOT / pathlib.Path(str(fixture["path"]))
            group, bitmap_width, bitmap_height, run_count = render_bitmap_group(
                path,
                x_positions[variant],
                y,
                scale,
                f"{variant} {bitmap_width_label(fixture)}",
            )
            parts.append(group)
            total_runs += run_count
            preview_items.append(
                {
                    "expression": expression,
                    "variant": variant,
                    "fixture_path": fixture["path"],
                    "fixture_sha256": fixture["sha256"],
                    "width": bitmap_width,
                    "height": bitmap_height,
                    "black_runs": run_count,
                }
            )
    parts.append("</svg>")
    svg = "\n".join(parts) + "\n"
    report = {
        "schema_id": SCHEMA_ID,
        "svg_path": rel(DEFAULT_SVG),
        "source_manifest": rel(FIXTURE_MANIFEST),
        "source_manifest_sha256": sha256_hex(FIXTURE_MANIFEST.read_bytes()),
        "expressions": EXPRESSION_ORDER,
        "variants": VARIANT_ORDER,
        "preview_items": preview_items,
        "svg_sha256": sha256_hex(svg.encode("utf-8")),
        "total_black_runs": total_runs,
        "source_schema_id": source_manifest.get("schema_id"),
    }
    return svg, report


def bitmap_width_label(fixture: dict[str, Any]) -> str:
    return f"{int(fixture['width'])}x{int(fixture['height'])}"


def write_outputs(svg_path: pathlib.Path, report_path: pathlib.Path, svg: str, report: dict[str, Any]) -> None:
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_bytes(svg.encode("utf-8"))
    report_with_path = dict(report)
    report_with_path["svg_path"] = rel(svg_path)
    report_path.write_bytes((json.dumps(report_with_path, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def verify_outputs(svg_path: pathlib.Path, report_path: pathlib.Path, svg: str, report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not svg_path.exists():
        errors.append(f"missing preview SVG: {rel(svg_path)}")
    elif svg_path.read_bytes() != svg.encode("utf-8"):
        errors.append(f"stale preview SVG: {rel(svg_path)}")

    if not report_path.exists():
        errors.append(f"missing preview report: {rel(report_path)}")
    else:
        actual = json.loads(report_path.read_text(encoding="utf-8"))
        expected = dict(report)
        expected["svg_path"] = rel(svg_path)
        if actual != expected:
            errors.append(f"stale preview report: {rel(report_path)}")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=pathlib.Path, default=DEFAULT_SVG)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true", help="Write deterministic SVG and JSON preview artifacts.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    svg_path = args.svg if args.svg.is_absolute() else REPO_ROOT / args.svg
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    svg, report = build_svg()
    if args.write:
        write_outputs(svg_path, report_path, svg, report)
    errors = verify_outputs(svg_path, report_path, svg, report)
    if errors:
        print("FAIL: Companion ExpressionV1 preview is stale:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 preview verified -> {rel(svg_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
