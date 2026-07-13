#!/usr/bin/env python3
"""Verify the no-hardware Companion screen expression demo sequence."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-demo-sequence.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-expression-demo-sequence.md")
JOURNEY_FIXTURE = REPO_ROOT / "docs/validation/companion-screen-expression-journeys.json"
STORYBOARD_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-storyboard.json"
STORYBOARD_SVG = REPO_ROOT / "docs/validation/epaper/expression-storyboard.svg"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
SCHEMA_ID = "companion.pendant.expression_demo_sequence.v1"


DEMO_CASES = [
    {
        "demo_id": "wake_recording_sync",
        "journey_id": "wake_to_recording_sync",
        "product_check": "Wake, listen, record, think, and show sync complete in order.",
        "acceptance_focus": ["listening", "recording", "thinking", "sync_complete"],
    },
    {
        "demo_id": "speaker_prompt_result",
        "journey_id": "speaker_prompt_result",
        "product_check": "Speaker prompt shows speaking, then happy after the result.",
        "acceptance_focus": ["speaking", "happy"],
    },
    {
        "demo_id": "settings_sleepy_hint",
        "journey_id": "settings_sleepy_hint",
        "product_check": "Display-off and quiet-hours hints show sleepy without hiding recording.",
        "acceptance_focus": ["sleepy", "recording"],
    },
    {
        "demo_id": "recording_low_battery_priority",
        "journey_id": "recording_low_battery_priority",
        "product_check": "Low battery does not interrupt active recording, then appears after recording stops.",
        "acceptance_focus": ["recording", "low_battery"],
    },
    {
        "demo_id": "battery_recovery_guard",
        "journey_id": "battery_recovery_only_clears_low_battery",
        "product_check": "Battery recovery only clears a visible low-battery face.",
        "acceptance_focus": ["low_battery", "idle", "error"],
    },
    {
        "demo_id": "error_override_recovery",
        "journey_id": "error_overrides_and_recovers",
        "product_check": "Error overrides lower-priority faces and returns to idle after recovery.",
        "acceptance_focus": ["error", "idle"],
    },
    {
        "demo_id": "transient_auto_recovery",
        "journey_id": "transient_expression_auto_recovery",
        "product_check": "Transient faces recover to idle while recording remains stable.",
        "acceptance_focus": ["happy", "sync_complete", "idle", "recording"],
    },
]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    require(path.exists(), f"missing required source {rel(path)}", errors)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def storyboard_index(storyboard: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for item in storyboard.get("storyboard_items", []):
        if isinstance(item, dict):
            indexed[(str(item.get("journey_id")), int(item.get("step_index", -1)))] = item
    return indexed


def build_report(errors: list[str]) -> dict[str, Any]:
    journey_fixture = load_json(JOURNEY_FIXTURE, errors)
    storyboard = load_json(STORYBOARD_REPORT, errors)
    require(STORYBOARD_SVG.exists(), f"missing required source {rel(STORYBOARD_SVG)}", errors)
    if errors:
        return {"schema_id": SCHEMA_ID, "status": "FAIL", "errors": errors}

    journey_by_id = {
        str(journey.get("journey_id")): journey
        for journey in journey_fixture.get("journeys", [])
        if isinstance(journey, dict)
    }
    storyboard_by_step = storyboard_index(storyboard)
    demos: list[dict[str, Any]] = []
    expression_coverage: set[str] = set()
    accepted_count = 0
    held_count = 0

    for order, demo in enumerate(DEMO_CASES, start=1):
        journey_id = str(demo["journey_id"])
        require(journey_id in journey_by_id, f"demo journey missing from fixture: {journey_id}", errors)
        journey = journey_by_id.get(journey_id, {})
        demo_steps = []
        for step in journey.get("steps", []):
            index = int(step.get("index", 0))
            expression = str(step.get("visible_expression", ""))
            expression_coverage.add(expression)
            accepted = bool(step.get("accepted", False))
            if accepted:
                accepted_count += 1
                expected_result = "accept"
            else:
                held_count += 1
                expected_result = "hold"
            visual = storyboard_by_step.get((journey_id, index), {})
            require(bool(visual.get("fixture_path")), f"{journey_id} step {index} missing storyboard fixture", errors)
            require(bool(step.get("render_hashes", {}).get("1.54in")), f"{journey_id} step {index} missing 1.54in render hash", errors)
            require(bool(step.get("render_hashes", {}).get("2.13in")), f"{journey_id} step {index} missing 2.13in render hash", errors)
            demo_steps.append(
                {
                    "index": index,
                    "event": str(step.get("event", "")),
                    "expression_signal": step.get("expression_signal"),
                    "visible_expression": expression,
                    "expected_result": expected_result,
                    "reason": str(step.get("reason", "")),
                    "fixture_path": str(visual.get("fixture_path", "")),
                    "fixture_sha256": str(visual.get("fixture_sha256", "")),
                    "render_hashes": dict(step.get("render_hashes", {})),
                }
            )
        demos.append(
            {
                "order": order,
                "demo_id": str(demo["demo_id"]),
                "journey_id": journey_id,
                "product_check": str(demo["product_check"]),
                "acceptance_focus": list(demo["acceptance_focus"]),
                "final_expression": str(journey.get("final_expression", "")),
                "steps": demo_steps,
            }
        )

    source_coverage = sorted(str(item) for item in journey_fixture.get("coverage", []))
    demo_coverage = sorted(expression_coverage)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "journey_fixture": rel(JOURNEY_FIXTURE),
            "journey_fixture_sha256": sha256_hex(JOURNEY_FIXTURE.read_bytes()),
            "storyboard_report": rel(STORYBOARD_REPORT),
            "storyboard_report_sha256": sha256_hex(STORYBOARD_REPORT.read_bytes()),
            "storyboard_svg": rel(STORYBOARD_SVG),
            "storyboard_svg_sha256": sha256_hex(STORYBOARD_SVG.read_bytes()),
            "screen_acceptance": rel(SCREEN_DOC),
            "epaper_readme": rel(EPAPER_README),
        },
        "summary": {
            "demo_count": len(demos),
            "step_count": sum(len(demo["steps"]) for demo in demos),
            "accepted_step_count": accepted_count,
            "held_step_count": held_count,
            "expression_coverage": demo_coverage,
            "source_expression_coverage": source_coverage,
            "markdown_checklist": rel(REPO_ROOT / DEFAULT_MARKDOWN),
        },
        "demos": demos,
        "acceptance": {
            "all_required_demo_journeys_present": all(str(demo["journey_id"]) in journey_by_id for demo in DEMO_CASES),
            "covers_all_expression_states": demo_coverage == source_coverage,
            "has_accepted_and_held_steps": accepted_count > 0 and held_count > 0,
            "all_steps_have_visual_fixtures": all(
                bool(step.get("fixture_path"))
                for demo in demos
                for step in demo.get("steps", [])
            ),
            "all_steps_have_dual_variant_hashes": all(
                bool(step.get("render_hashes", {}).get("1.54in"))
                and bool(step.get("render_hashes", {}).get("2.13in"))
                for demo in demos
                for step in demo.get("steps", [])
            ),
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_demo_sequence.py",
            "python .\\tools\\verify_expression_journeys.py",
            "python .\\tools\\render_expression_storyboard.py",
        ],
    }


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Companion Screen Expression Demo Sequence",
        "",
        f"Status: {report.get('status')}",
        f"Source journey fixture: `{report.get('sources', {}).get('journey_fixture')}`",
        f"Storyboard: `{report.get('sources', {}).get('storyboard_svg')}`",
        "",
        "## Demo Order",
        "",
        "| Order | Demo | Product check | Final face |",
        "|---:|---|---|---|",
    ]
    for demo in report.get("demos", []):
        lines.append(
            "| "
            f"{demo.get('order')} | "
            f"`{md_cell(demo.get('demo_id'))}` | "
            f"{md_cell(demo.get('product_check'))} | "
            f"`{md_cell(demo.get('final_expression'))}` |"
        )

    lines.extend(
        [
            "",
            "## Step Checklist",
            "",
            "| Demo | Step | Event | Visible face | Result | Fixture |",
            "|---|---:|---|---|---|---|",
        ]
    )
    for demo in report.get("demos", []):
        for step in demo.get("steps", []):
            lines.append(
                "| "
                f"`{md_cell(demo.get('demo_id'))}` | "
                f"{step.get('index')} | "
                f"`{md_cell(step.get('event'))}` | "
                f"`{md_cell(step.get('visible_expression'))}` | "
                f"`{md_cell(step.get('expected_result'))}` | "
                f"`{md_cell(step.get('fixture_path'))}` |"
            )

    summary = report.get("summary", {})
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Demo count: {summary.get('demo_count')}",
            f"- Step count: {summary.get('step_count')}",
            f"- Accepted steps: {summary.get('accepted_step_count')}",
            f"- Held steps: {summary.get('held_step_count')}",
            f"- Expressions: {', '.join(summary.get('expression_coverage', []))}",
            "",
        ]
    )
    return "\n".join(lines)


def validate_report(report: dict[str, Any], errors: list[str]) -> None:
    require(report.get("schema_id") == SCHEMA_ID, "unexpected demo sequence schema", errors)
    require(report.get("status") == "PASS", "demo sequence must be PASS", errors)
    acceptance = report.get("acceptance", {})
    for key in [
        "all_required_demo_journeys_present",
        "covers_all_expression_states",
        "has_accepted_and_held_steps",
        "all_steps_have_visual_fixtures",
        "all_steps_have_dual_variant_hashes",
    ]:
        require(acceptance.get(key) is True, f"demo sequence acceptance missing {key}", errors)
    summary = report.get("summary", {})
    require(summary.get("demo_count") == len(DEMO_CASES), "demo sequence demo_count mismatch", errors)
    require(summary.get("step_count", 0) >= 20, "demo sequence should cover at least 20 steps", errors)
    require("speaking" in summary.get("expression_coverage", []), "demo sequence must include speaking face", errors)
    require("low_battery" in summary.get("expression_coverage", []), "demo sequence must include low_battery face", errors)
    require("error" in summary.get("expression_coverage", []), "demo sequence must include error face", errors)


def check_docs(errors: list[str]) -> None:
    for path in [SCREEN_DOC, EPAPER_README]:
        require(path.exists(), f"missing doc source {rel(path)}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "screen_expression_demo_sequence",
            "companion-screen-expression-demo-sequence.json",
            "companion-screen-expression-demo-sequence.md",
            "verify_expression_demo_sequence.py",
        ]:
            require(token in text, f"{rel(path)} missing demo sequence token {token}", errors)


def check_outputs(
    fixture_path: pathlib.Path,
    markdown_path: pathlib.Path,
    report: dict[str, Any],
    markdown: str,
    errors: list[str],
) -> None:
    require(fixture_path.exists(), f"missing demo sequence fixture: {rel(fixture_path)}", errors)
    if fixture_path.exists():
        actual = json.loads(fixture_path.read_text(encoding="utf-8"))
        require(actual == report, f"{rel(fixture_path)} is stale; rerun with --write-fixture", errors)
    require(markdown_path.exists(), f"missing demo sequence checklist: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        actual_md = markdown_path.read_text(encoding="utf-8")
        require(actual_md == markdown, f"{rel(markdown_path)} is stale; rerun with --write-fixture", errors)


def write_outputs(fixture_path: pathlib.Path, markdown_path: pathlib.Path, report: dict[str, Any], markdown: str) -> None:
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic JSON and Markdown demo artifacts.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    markdown_path = args.markdown if args.markdown.is_absolute() else REPO_ROOT / args.markdown
    errors: list[str] = []
    report = build_report(errors)
    markdown = render_markdown(report)
    validate_report(report, errors)
    check_docs(errors)
    if args.write_fixture and not errors:
        write_outputs(fixture_path, markdown_path, report, markdown)
    if not args.write_fixture:
        check_outputs(fixture_path, markdown_path, report, markdown, errors)
    if errors:
        print("FAIL: Companion screen expression demo sequence checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen expression demo sequence verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
