#!/usr/bin/env python3
"""Render a human-readable Companion screen acceptance report."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
DEFAULT_REPORT = REPO_ROOT / "docs/validation/companion-screen-acceptance-report.md"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def bullet_list(values: list[Any], empty: str = "None") -> list[str]:
    if not values:
        return [f"- {empty}"]
    return [f"- `{clean_cell(value)}`" for value in values]


def load_index(path: pathlib.Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    return json.loads(resolved.read_text(encoding="utf-8"))


def build_markdown(index: dict[str, Any], index_path: pathlib.Path) -> str:
    summary = index.get("summary", {})
    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    lines = [
        "# Companion Screen Acceptance Report",
        "",
        f"Source index: `{rel(index_path)}`",
        "",
        "This report is generated. Update it with `python .\\tools\\render_expression_acceptance_report.py --write`.",
        "",
        "## Summary",
        "",
        f"- PASS: {int(summary.get('pass_count', 0))}",
        f"- DEFERRED_HARDWARE: {int(summary.get('deferred_count', 0))}",
        f"- PENDING_HUMAN: {int(summary.get('pending_human_count', 0))}",
        f"- TOTAL: {int(summary.get('total_count', len(items)))}",
        f"- Next hardware gate: `{clean_cell(summary.get('next_hardware_gate') or 'none')}`",
        f"- Next human gate: `{clean_cell(summary.get('next_human_gate', ''))}`",
        "",
        "## Item Status",
        "",
        "| # | Status | ID | Title |",
        "|---:|---|---|---|",
    ]
    for index_number, item in enumerate(items, start=1):
        lines.append(
            "| "
            f"{index_number} | {clean_cell(item.get('status', ''))} | "
            f"`{clean_cell(item.get('id', ''))}` | {clean_cell(item.get('title', ''))} |"
        )

    lines.extend(["", "## Item Details", ""])
    for index_number, item in enumerate(items, start=1):
        item_id = clean_cell(item.get("id", ""))
        title = clean_cell(item.get("title", ""))
        status = clean_cell(item.get("status", ""))
        lines.extend(
            [
                f"### {index_number}. {title}",
                "",
                f"- ID: `{item_id}`",
                f"- Status: `{status}`",
                f"- Summary: {clean_cell(item.get('summary', ''))}",
                f"- WBA impact: {clean_cell(item.get('wba_impact', ''))}",
                "",
                "Evidence:",
            ]
        )
        lines.extend(bullet_list(list(item.get("evidence_paths", []))))
        lines.extend(["", "Validation commands:"])
        lines.extend(bullet_list(list(item.get("validation_commands", []))))
        missing = list(item.get("missing_hardware_facts", []))
        if missing:
            lines.extend(["", "Missing hardware facts:"])
            lines.extend(f"- {clean_cell(value)}" for value in missing)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(path: pathlib.Path, markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(markdown.encode("utf-8"))


def verify_report(path: pathlib.Path, markdown: str) -> list[str]:
    if not path.exists():
        return [f"missing acceptance report: {rel(path)}"]
    if path.read_text(encoding="utf-8") != markdown:
        return [f"stale acceptance report: {rel(path)}"]
    return []


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=pathlib.Path, default=DEFAULT_INDEX)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true", help="Write the deterministic Markdown report.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    index_path = args.index if args.index.is_absolute() else REPO_ROOT / args.index
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    index = load_index(index_path)
    markdown = build_markdown(index, index_path)
    if args.write:
        write_report(report_path, markdown)
    errors = verify_report(report_path, markdown)
    if errors:
        print("FAIL: Companion screen acceptance report is stale:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen acceptance report verified -> {rel(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
