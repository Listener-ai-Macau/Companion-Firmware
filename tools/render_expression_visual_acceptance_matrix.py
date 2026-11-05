#!/usr/bin/env python3
"""Render a per-face ExpressionV1 visual acceptance matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = pathlib.Path("docs/validation/companion-screen-expression-visual-acceptance-matrix.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-expression-visual-acceptance-matrix.md")
SCHEMA_ID = "companion.pendant.screen_expression_visual_acceptance_matrix.v1"

HOST_MANIFEST = REPO_ROOT / "docs/validation/companion-screen-expression-host-manifest.json"
VISUAL_CONTRACT = REPO_ROOT / "docs/validation/companion-screen-expression-visual-contract.json"
EPAPER_FIXTURES = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
PREVIEW_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-preview.json"
PREVIEW_SVG = REPO_ROOT / "docs/validation/epaper/expression-preview.svg"
STORYBOARD_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-storyboard.json"
STORYBOARD_SVG = REPO_ROOT / "docs/validation/epaper/expression-storyboard.svg"
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
WBA_RULES = REPO_ROOT / "docs/stm32wba_migration_rules.md"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_md(value: object) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def visual_metrics_by_face(visual: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    metrics: dict[tuple[str, str], dict[str, Any]] = {}
    for row in visual.get("metrics", []):
        if not isinstance(row, dict):
            continue
        metrics[(str(row.get("expression")), str(row.get("variant")))] = row
    return metrics


def fixtures_by_face(epaper: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    fixtures: dict[tuple[str, str], dict[str, Any]] = {}
    for fixture in epaper.get("fixtures", []):
        if not isinstance(fixture, dict):
            continue
        fixture_id = str(fixture.get("id", ""))
        if not fixture_id.startswith("expression_"):
            continue
        face = fixture_id.removeprefix("expression_")
        fixtures[(face, str(fixture.get("variant")))] = fixture
    return fixtures


def metric_in_thresholds(metric: dict[str, Any], thresholds: dict[str, Any]) -> bool:
    full = int(metric.get("full_ink_ratio_ppm", -1))
    face = int(metric.get("face_ink_ratio_ppm", -1))
    return (
        int(thresholds.get("full_ink_ratio_ppm_min", 0)) <= full <= int(thresholds.get("full_ink_ratio_ppm_max", 0))
        and int(thresholds.get("face_ink_ratio_ppm_min", 0)) <= face <= int(thresholds.get("face_ink_ratio_ppm_max", 0))
    )


def build_matrix(errors: list[str]) -> dict[str, Any]:
    host = load_json(HOST_MANIFEST)
    visual = load_json(VISUAL_CONTRACT)
    epaper = load_json(EPAPER_FIXTURES)

    metrics = visual_metrics_by_face(visual)
    fixtures = fixtures_by_face(epaper)
    thresholds = visual.get("thresholds", {})
    variants = sorted(str(item) for item in visual.get("variants", []))
    rows: list[dict[str, Any]] = []

    for face in host.get("faces", []):
        if not isinstance(face, dict):
            continue
        name = str(face.get("name"))
        variant_rows: list[dict[str, Any]] = []
        for variant in variants:
            metric = metrics.get((name, variant), {})
            fixture = fixtures.get((name, variant), {})
            path_text = str(metric.get("path", fixture.get("path", "")))
            path = REPO_ROOT / path_text
            actual_sha = sha256_file(path) if path.exists() else ""
            metric_sha = str(metric.get("sha256", ""))
            manifest_sha = str(fixture.get("sha256", metric.get("manifest_sha256", "")))
            variant_rows.append(
                {
                    "variant": variant,
                    "fixture_id": fixture.get("id"),
                    "path": path_text,
                    "width": metric.get("width"),
                    "height": metric.get("height"),
                    "sha256": metric_sha,
                    "manifest_sha256": manifest_sha,
                    "actual_sha256": actual_sha,
                    "full_ink_ratio_ppm": metric.get("full_ink_ratio_ppm"),
                    "face_ink_ratio_ppm": metric.get("face_ink_ratio_ppm"),
                    "face_box": metric.get("face_box"),
                    "fixture_hash_matches_visual_contract": bool(metric_sha and manifest_sha == metric_sha),
                    "actual_hash_matches_visual_contract": bool(actual_sha and actual_sha == metric_sha),
                    "density_within_contract": metric_in_thresholds(metric, thresholds) if metric else False,
                }
            )

        rows.append(
            {
                "id": face.get("id"),
                "name": name,
                "title": face.get("title"),
                "body": face.get("body"),
                "footer": face.get("footer"),
                "priority": face.get("priority"),
                "stability": face.get("stability"),
                "auto_recover_ms": face.get("auto_recover_ms"),
                "signals": [signal.get("signal") for signal in face.get("signals", []) if isinstance(signal, dict)],
                "policy_case_ids": face.get("policy_case_ids", []),
                "host_coverage": {
                    "legacy_host_sequence_covered": face.get("legacy_host_sequence_covered"),
                    "demo_host_sequence_covered": face.get("demo_host_sequence_covered"),
                    "legacy_host_examples": face.get("legacy_host_examples", []),
                    "demo_host_examples": face.get("demo_host_examples", []),
                    "acceptance_hint": face.get("host_acceptance_hint"),
                },
                "variants": variant_rows,
                "visual_acceptance": {
                    "variant_count": len(variant_rows),
                    "fixture_hashes_match": all(row.get("fixture_hash_matches_visual_contract") for row in variant_rows),
                    "actual_hashes_match": all(row.get("actual_hash_matches_visual_contract") for row in variant_rows),
                    "density_metrics_in_bounds": all(row.get("density_within_contract") for row in variant_rows),
                    "demo_host_covered": face.get("demo_host_sequence_covered") is True,
                    "accepted_without_real_panel": True,
                },
            }
        )

    legacy_gaps = host.get("coverage", {}).get("legacy_gap_faces", [])
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Per-face acceptance matrix that links ExpressionV1 visual fixtures, visual metrics, copy, source signals, policy cases, and host coverage.",
        "sources": {
            "host_manifest": rel(HOST_MANIFEST),
            "visual_contract": rel(VISUAL_CONTRACT),
            "epaper_fixtures": rel(EPAPER_FIXTURES),
            "preview_report": rel(PREVIEW_REPORT),
            "preview_svg": rel(PREVIEW_SVG),
            "storyboard_report": rel(STORYBOARD_REPORT),
            "storyboard_svg": rel(STORYBOARD_SVG),
            "matrix_tool": "tools/render_expression_visual_acceptance_matrix.py",
        },
        "coverage": {
            "expression_count": len(rows),
            "variant_count": len(variants),
            "matrix_cell_count": sum(len(row.get("variants", [])) for row in rows),
            "variants": variants,
            "demo_covers_all_faces": all(row.get("host_coverage", {}).get("demo_host_sequence_covered") for row in rows),
            "legacy_gap_faces": legacy_gaps,
            "real_refresh_claimed": False,
            "panel_gate_must_remain": "DEFERRED_HARDWARE",
        },
        "visual_thresholds": thresholds,
        "distance_by_variant": visual.get("distance_by_variant", []),
        "rows": rows,
        "wba_contract": {
            "same_expression_visual_matrix": True,
            "same_fixture_hashes_before_target_transport": True,
            "same_host_face_signal_mapping": True,
            "target_adapter_only_replaces_panel_transport": True,
            "real_panel_refresh_claimed": False,
        },
        "validation_commands": [
            "python .\\tools\\render_expression_visual_acceptance_matrix.py",
            "python .\\tools\\render_expression_visual_acceptance_matrix.py --self-test",
            "python .\\tools\\render_epaper_fixtures.py --self-test",
            "python .\\tools\\verify_expression_visual_contract.py",
            "python .\\tools\\render_expression_host_manifest.py",
            "python .\\tools\\verify_epaper_assets.py",
        ],
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    coverage = matrix.get("coverage", {})
    lines = [
        "# Companion ExpressionV1 Visual Acceptance Matrix",
        "",
        "This matrix is generated. Update it with `python .\\tools\\render_expression_visual_acceptance_matrix.py --write`.",
        "",
        "## Coverage",
        "",
        f"- Expressions: `{clean_md(coverage.get('expression_count'))}`",
        f"- Variants: `{clean_md(coverage.get('variants'))}`",
        f"- Matrix cells: `{clean_md(coverage.get('matrix_cell_count'))}`",
        f"- Demo covers all faces: `{clean_md(coverage.get('demo_covers_all_faces'))}`",
        f"- Legacy gap faces: `{clean_md(coverage.get('legacy_gap_faces'))}`",
        f"- Real refresh claimed: `{clean_md(coverage.get('real_refresh_claimed'))}`",
        f"- Panel gate: `{clean_md(coverage.get('panel_gate_must_remain'))}`",
        "",
        "## Face Matrix",
        "",
        "| ID | Face | Fixtures | Host coverage | Signals | Acceptance |",
        "|---:|---|---|---|---|---|",
    ]
    for row in matrix.get("rows", []):
        fixtures = [
            f"{variant.get('variant')}: {variant.get('path')}"
            for variant in row.get("variants", [])
            if isinstance(variant, dict)
        ]
        host = row.get("host_coverage", {})
        acceptance = row.get("visual_acceptance", {})
        host_label = "legacy+demo" if host.get("legacy_host_sequence_covered") else "demo"
        checks = [
            f"hashes={acceptance.get('actual_hashes_match')}",
            f"density={acceptance.get('density_metrics_in_bounds')}",
            f"demo={acceptance.get('demo_host_covered')}",
        ]
        lines.append(
            "| "
            f"{clean_md(row.get('id'))} | "
            f"`{clean_md(row.get('name'))}` | "
            f"{clean_md(fixtures)} | "
            f"{clean_md(host_label)} | "
            f"{clean_md(row.get('signals'))} | "
            f"{clean_md(checks)} |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_matrix(matrix: dict[str, Any], errors: list[str]) -> None:
    require(matrix.get("schema_id") == SCHEMA_ID, f"matrix schema_id must be {SCHEMA_ID}", errors)
    require(matrix.get("status") == "PASS", "visual acceptance matrix must be PASS", errors)
    coverage = matrix.get("coverage", {})
    rows = matrix.get("rows", [])
    require(coverage.get("expression_count") == 10, "matrix must list 10 ExpressionV1 faces", errors)
    require(coverage.get("variant_count") == 2, "matrix must list the two supported display variants", errors)
    require(coverage.get("matrix_cell_count") == 20, "matrix must have 20 face/variant cells", errors)
    require(coverage.get("demo_covers_all_faces") is True, "demo host sequence must cover every matrix face", errors)
    require(coverage.get("legacy_gap_faces") == ["happy", "listening", "speaking", "thinking"], "legacy host gap faces drifted", errors)
    require(coverage.get("real_refresh_claimed") is False, "matrix must not claim real panel refresh", errors)
    require(coverage.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "matrix must leave panel gate deferred", errors)
    names = [row.get("name") for row in rows if isinstance(row, dict)]
    require(len(names) == len(set(names)) == 10, "matrix face names must be unique", errors)
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        variants = row.get("variants", [])
        acceptance = row.get("visual_acceptance", {})
        require(len(variants) == 2, f"{name} must have two visual variants", errors)
        require(row.get("signals"), f"{name} must link source signals", errors)
        require(row.get("policy_case_ids"), f"{name} must link policy cases", errors)
        require(acceptance.get("fixture_hashes_match") is True, f"{name} fixture hashes must match manifest", errors)
        require(acceptance.get("actual_hashes_match") is True, f"{name} actual PBM hashes must match visual contract", errors)
        require(acceptance.get("density_metrics_in_bounds") is True, f"{name} density metrics must remain in bounds", errors)
        require(acceptance.get("demo_host_covered") is True, f"{name} must be covered by demo host status", errors)
        require(acceptance.get("accepted_without_real_panel") is True, f"{name} matrix is AI-testable without real panel", errors)
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            path = REPO_ROOT / str(variant.get("path", ""))
            require(path.exists(), f"{name}/{variant.get('variant')} missing PBM path {rel(path)}", errors)
            require(variant.get("fixture_id") == f"expression_{name}", f"{name}/{variant.get('variant')} fixture id drifted", errors)
            require(variant.get("sha256") == variant.get("manifest_sha256"), f"{name}/{variant.get('variant')} manifest hash mismatch", errors)
            require(variant.get("sha256") == variant.get("actual_sha256"), f"{name}/{variant.get('variant')} actual hash mismatch", errors)
            require(variant.get("density_within_contract") is True, f"{name}/{variant.get('variant')} density outside visual contract", errors)
    wba = matrix.get("wba_contract", {})
    for key in [
        "same_expression_visual_matrix",
        "same_fixture_hashes_before_target_transport",
        "same_host_face_signal_mapping",
        "target_adapter_only_replaces_panel_transport",
    ]:
        require(wba.get(key) is True, f"WBA matrix contract missing {key}", errors)
    require(wba.get("real_panel_refresh_claimed") is False, "WBA matrix contract must not claim real refresh", errors)


def check_project_links(errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (EPAPER_README, "epaper README"), (WBA_RULES, "WBA rules")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "expression_visual_acceptance_matrix",
            "companion-screen-expression-visual-acceptance-matrix.json",
            "companion-screen-expression-visual-acceptance-matrix.md",
            "render_expression_visual_acceptance_matrix.py",
        ]:
            require(token in text, f"{name} missing visual acceptance matrix anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [
            item
            for item in index.get("items", [])
            if isinstance(item, dict) and item.get("id") == "expression_visual_acceptance_matrix"
        ]
        require(len(items) == 1, "acceptance index must contain one expression_visual_acceptance_matrix item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "expression_visual_acceptance_matrix item must be PASS", errors)
            evidence = item.get("evidence_paths", [])
            require(
                "docs/validation/companion-screen-expression-visual-acceptance-matrix.json" in evidence,
                "expression_visual_acceptance_matrix item must link JSON fixture",
                errors,
            )


def check_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, matrix: dict[str, Any], markdown: str, errors: list[str]) -> None:
    require(json_path.exists(), f"missing visual acceptance matrix JSON: {rel(json_path)}", errors)
    if json_path.exists():
        require(load_json(json_path) == matrix, f"{rel(json_path)} is stale; rerun with --write", errors)
    require(markdown_path.exists(), f"missing visual acceptance matrix Markdown: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        require(markdown_path.read_text(encoding="utf-8") == markdown, f"{rel(markdown_path)} is stale; rerun with --write", errors)


def write_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, matrix: dict[str, Any], markdown: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")


def run_self_test() -> list[str]:
    errors: list[str] = []
    matrix = build_matrix(errors)
    validate_matrix(matrix, errors)
    rows = {row.get("name"): row for row in matrix.get("rows", []) if isinstance(row, dict)}
    require(rows.get("recording", {}).get("host_coverage", {}).get("legacy_host_sequence_covered") is True, "recording should stay in legacy host coverage", errors)
    require(rows.get("thinking", {}).get("host_coverage", {}).get("legacy_host_sequence_covered") is False, "thinking should remain a legacy host gap", errors)
    require(rows.get("speaking", {}).get("visual_acceptance", {}).get("actual_hashes_match") is True, "speaking visual hashes should match", errors)
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--write", action="store_true", help="Write the deterministic JSON and Markdown matrix.")
    parser.add_argument("--self-test", action="store_true", help="Run matrix coverage checks.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    markdown_path = args.markdown if args.markdown.is_absolute() else REPO_ROOT / args.markdown
    errors: list[str] = []

    for path in [HOST_MANIFEST, VISUAL_CONTRACT, EPAPER_FIXTURES, PREVIEW_REPORT, PREVIEW_SVG, STORYBOARD_REPORT, STORYBOARD_SVG]:
        require(path.exists(), f"missing required source {rel(path)}", errors)
    matrix = build_matrix(errors) if not errors else {"schema_id": SCHEMA_ID, "status": "FAIL"}
    markdown = render_markdown(matrix)
    validate_matrix(matrix, errors)
    if args.self_test:
        errors.extend(run_self_test())
    if not args.write:
        check_project_links(errors)
        check_outputs(json_path, markdown_path, matrix, markdown, errors)
    if args.write and not errors:
        write_outputs(json_path, markdown_path, matrix, markdown)

    if errors:
        print("FAIL: Companion ExpressionV1 visual acceptance matrix checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 visual acceptance matrix verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
