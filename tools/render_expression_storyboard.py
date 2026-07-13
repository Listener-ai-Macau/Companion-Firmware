#!/usr/bin/env python3
"""Render ExpressionV1 journey storyboards from the journey fixture."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNEY_FIXTURE = REPO_ROOT / "docs/validation/companion-screen-expression-journeys.json"
FIXTURE_MANIFEST = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
DEFAULT_SVG = REPO_ROOT / "docs/validation/epaper/expression-storyboard.svg"
DEFAULT_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-storyboard.json"
SCHEMA_ID = "companion.pendant.expression_storyboard.v1"
VISUAL_VARIANT = "2.13in"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
            if (byte & (0x80 >> (x % 8))) == 0:
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


def load_expression_fixtures() -> dict[str, dict[str, Any]]:
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    fixtures: dict[str, dict[str, Any]] = {}
    for fixture in manifest.get("fixtures", []):
        card = fixture.get("card", {})
        if card.get("card_type") == "expression" and fixture.get("variant") == VISUAL_VARIANT:
            fixtures[str(card.get("state", ""))] = fixture
    return fixtures


def render_bitmap(path: pathlib.Path, x: int, y: int, scale: float) -> tuple[str, int, int, int]:
    data = path.read_bytes()
    width, height, payload = parse_pbm(data, rel(path))
    runs = pbm_runs(width, height, payload)
    path_data = " ".join(f"M{run_x} {run_y + 0.5}h{run_width}" for run_x, run_y, run_width in runs)
    parts = [
        f'<g transform="translate({x},{y}) scale({scale:.3f})">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fffef7"/>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="none" stroke="#171717" stroke-width="2"/>',
        f'<path d="{path_data}" fill="none" stroke="#171717" stroke-width="1" shape-rendering="crispEdges"/>',
        "</g>",
    ]
    return "\n".join(parts), width, height, len(runs)


def status_style(accepted: bool, signal: str | None) -> tuple[str, str, str]:
    if accepted:
        return "ACCEPT", "#dcefd6", "#1f5f2f"
    if signal:
        return "HOLD", "#f4e3b1", "#72520c"
    return "NOOP", "#d9e6ee", "#245069"


def short_event(event: str) -> str:
    return event.replace("recording_fsm.", "rec.").replace("battery_charging.", "battery.")


def build_svg_and_report() -> tuple[str, dict[str, Any]]:
    journey_fixture = json.loads(JOURNEY_FIXTURE.read_text(encoding="utf-8"))
    fixtures = load_expression_fixtures()
    journeys = list(journey_fixture.get("journeys", []))
    max_steps = max(len(journey.get("steps", [])) for journey in journeys)

    margin = 28
    label_width = 245
    cell_width = 164
    row_height = 136
    thumb_scale = 0.48
    thumb_width = int(250 * thumb_scale)
    thumb_height = int(122 * thumb_scale)
    width = margin * 2 + label_width + max_steps * cell_width
    height = margin * 2 + 62 + len(journeys) * row_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f6f5ef"/>',
        f'<text x="{margin}" y="{margin + 20}" font-size="21" font-family="Arial, sans-serif" fill="#111">Companion ExpressionV1 Journey Storyboard</text>',
        f'<text x="{margin}" y="{margin + 43}" font-size="12" font-family="Arial, sans-serif" fill="#333">Each panel uses the {VISUAL_VARIANT} golden expression fixture selected by the simulated journey step.</text>',
    ]
    storyboard_items: list[dict[str, Any]] = []
    total_black_runs = 0
    all_expressions: set[str] = set()
    accepted_steps = 0
    suppressed_steps = 0

    y0 = margin + 74
    for row, journey in enumerate(journeys):
        journey_id = str(journey.get("journey_id", "journey"))
        steps = list(journey.get("steps", []))
        y = y0 + row * row_height
        parts.extend(
            [
                f'<rect x="{margin}" y="{y - 18}" width="{width - margin * 2}" height="{row_height - 10}" fill="#ffffff" stroke="#d2d0c8"/>',
                f'<text x="{margin + 12}" y="{y + 4}" font-size="14" font-family="Arial, sans-serif" font-weight="700" fill="#111">{html.escape(journey_id)}</text>',
                f'<text x="{margin + 12}" y="{y + 24}" font-size="11" font-family="Arial, sans-serif" fill="#444">final: {html.escape(str(journey.get("final_expression", "")))}</text>',
            ]
        )
        previous_center: tuple[int, int] | None = None
        for step in steps:
            index = int(step.get("index", 0))
            expression = str(step.get("visible_expression", "idle"))
            signal = step.get("expression_signal")
            accepted = bool(step.get("accepted", False))
            if accepted:
                accepted_steps += 1
            elif signal:
                suppressed_steps += 1
            all_expressions.add(expression)
            fixture = fixtures[expression]
            fixture_path = REPO_ROOT / pathlib.Path(str(fixture["path"]))
            x = margin + label_width + index * cell_width
            panel_y = y
            center = (x + thumb_width // 2, panel_y + thumb_height // 2)
            if previous_center is not None:
                parts.append(
                    f'<line x1="{previous_center[0] + thumb_width // 2 + 4}" y1="{previous_center[1]}" x2="{x - 8}" y2="{center[1]}" stroke="#8e8b82" stroke-width="2"/>'
                )
            previous_center = center
            bitmap, bitmap_width, bitmap_height, black_runs = render_bitmap(fixture_path, x, panel_y, thumb_scale)
            total_black_runs += black_runs
            status, fill, stroke = status_style(accepted, str(signal) if signal else None)
            event = short_event(str(step.get("event", "")))
            parts.extend(
                [
                    bitmap,
                    f'<rect x="{x}" y="{panel_y + thumb_height + 8}" width="72" height="18" rx="2" fill="{fill}" stroke="{stroke}"/>',
                    f'<text x="{x + 6}" y="{panel_y + thumb_height + 21}" font-size="10" font-family="Arial, sans-serif" fill="{stroke}">{status}</text>',
                    f'<text x="{x}" y="{panel_y + thumb_height + 42}" font-size="11" font-family="Arial, sans-serif" fill="#111">{html.escape(expression)}</text>',
                    f'<text x="{x}" y="{panel_y + thumb_height + 59}" font-size="10" font-family="Arial, sans-serif" fill="#555">{html.escape(event[:24])}</text>',
                ]
            )
            storyboard_items.append(
                {
                    "journey_id": journey_id,
                    "step_index": index,
                    "event": str(step.get("event", "")),
                    "visible_expression": expression,
                    "accepted": accepted,
                    "expression_signal": signal,
                    "fixture_path": str(fixture["path"]),
                    "fixture_sha256": str(fixture["sha256"]),
                    "render_hashes": dict(step.get("render_hashes", {})),
                    "bitmap_width": bitmap_width,
                    "bitmap_height": bitmap_height,
                    "black_runs": black_runs,
                }
            )
    parts.append("</svg>")
    svg = "\n".join(parts) + "\n"
    report = {
        "schema_id": SCHEMA_ID,
        "svg_path": rel(DEFAULT_SVG),
        "source_journey_fixture": rel(JOURNEY_FIXTURE),
        "source_journey_schema_id": journey_fixture.get("schema_id"),
        "source_journey_sha256": sha256_hex(JOURNEY_FIXTURE.read_bytes()),
        "source_fixture_manifest": rel(FIXTURE_MANIFEST),
        "source_fixture_manifest_sha256": sha256_hex(FIXTURE_MANIFEST.read_bytes()),
        "visual_variant": VISUAL_VARIANT,
        "journey_count": len(journeys),
        "step_count": len(storyboard_items),
        "max_steps_per_journey": max_steps,
        "accepted_steps": accepted_steps,
        "suppressed_or_held_steps": suppressed_steps,
        "coverage": sorted(all_expressions),
        "storyboard_items": storyboard_items,
        "total_black_runs": total_black_runs,
        "svg_sha256": sha256_hex(svg.encode("utf-8")),
        "acceptance": {
            "all_journeys_rendered": len(storyboard_items) == sum(len(journey.get("steps", [])) for journey in journeys),
            "all_expression_states_covered": sorted(all_expressions) == sorted(journey_fixture.get("coverage", [])),
            "accepted_and_suppressed_steps_visible": accepted_steps > 0 and suppressed_steps > 0,
            "uses_golden_expression_fixtures": True,
        },
    }
    return svg, report


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
        errors.append(f"missing storyboard SVG: {rel(svg_path)}")
    elif svg_path.read_text(encoding="utf-8") != svg:
        errors.append(f"stale storyboard SVG: {rel(svg_path)}")

    if not report_path.exists():
        errors.append(f"missing storyboard report: {rel(report_path)}")
    else:
        actual = json.loads(report_path.read_text(encoding="utf-8"))
        expected = dict(report)
        expected["svg_path"] = rel(svg_path)
        if actual != expected:
            errors.append(f"stale storyboard report: {rel(report_path)}")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=pathlib.Path, default=DEFAULT_SVG)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true", help="Write deterministic SVG and JSON storyboard artifacts.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    svg_path = args.svg if args.svg.is_absolute() else REPO_ROOT / args.svg
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    svg, report = build_svg_and_report()
    if args.write:
        write_outputs(svg_path, report_path, svg, report)
    errors = verify_outputs(svg_path, report_path, svg, report)
    if errors:
        print("FAIL: Companion ExpressionV1 storyboard is stale:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 storyboard verified -> {rel(svg_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
