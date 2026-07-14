#!/usr/bin/env python3
"""Verify the Companion expression demo to real-panel evidence handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-demo-panel-handoff.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-expression-demo-panel-handoff.md")
DEMO_SEQUENCE = REPO_ROOT / "docs/validation/companion-screen-expression-demo-sequence.json"
REAL_BLE_BENCH = REPO_ROOT / "docs/validation/companion-screen-real-ble-bench.json"
PANEL_SESSION = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-session.json"
PANEL_PLAN = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-acceptance-plan.json"
PANEL_GATE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
PANEL_RECOVERY_GATE = REPO_ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
PANEL_TEMPLATE = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-template.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
WBA_RULES = REPO_ROOT / "docs/stm32wba_migration_rules.md"
SCHEMA_ID = "companion.pendant.expression_demo_panel_handoff.v1"
TARGETS = ("WB55", "WBA55", "WBA65")
EXPECTED_MANUAL_VISUAL_FACES = ["happy", "listening", "speaking", "thinking"]


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


def session_root(target: str) -> str:
    return f".cache/validation/companion-real-panel-{target.lower()}-<timestamp>"


def visual_path(target: str, order: int, step_index: int, expression: str) -> str:
    safe_expression = expression.replace("_", "-")
    return f"{session_root(target)}/visual/demo-sequence/{order:02d}-{step_index:02d}-{safe_expression}.jpg"


def target_resources(target: str) -> str:
    if target == "WB55":
        return "Companion-WB55,BLE-Companion"
    return f"Companion-{target},BLE-Companion"


def target_resource_arg(target: str) -> str:
    return f"'{target_resources(target)}'"


def flatten_demo_steps(demo_sequence: dict[str, Any], real_ble_faces: set[str]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for demo in demo_sequence.get("demos", []):
        order = int(demo.get("order", 0))
        demo_id = str(demo.get("demo_id", "demo"))
        for step in demo.get("steps", []):
            expression = str(step.get("visible_expression", ""))
            steps.append(
                {
                    "demo_order": order,
                    "demo_id": demo_id,
                    "step_index": int(step.get("index", 0)),
                    "event": str(step.get("event", "")),
                    "expression_signal": step.get("expression_signal"),
                    "visible_expression": expression,
                    "expected_result": str(step.get("expected_result", "")),
                    "fixture_path": str(step.get("fixture_path", "")),
                    "fixture_sha256": str(step.get("fixture_sha256", "")),
                    "capture_mode": (
                        "real_ble_sequence_baseline_plus_visual"
                        if expression in real_ble_faces
                        else "manual_visual_required"
                    ),
                }
            )
    return steps


def build_target_handoff(target: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "target": target,
        "session_root_pattern": session_root(target),
        "hardware_lock_resources": target_resources(target),
        "demo_visual_root": f"{session_root(target)}/visual/demo-sequence",
        "operator_checklist_path": f"{session_root(target)}/demo-panel-handoff.md",
        "required_commands": [
            "python .\\tools\\verify_expression_demo_panel_handoff.py",
            "python .\\tools\\verify_expression_demo_sequence.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_panel_hardware_session.py",
            (
                "pwsh -NoProfile -File <ai-collaboration-workflow>\\scripts\\aiw.ps1 "
                f"with-lock -Resource {target_resource_arg(target)} -Purpose \"Companion {target} expression demo panel handoff\" "
                "-Run python .\\tools\\companion_ble_real_bench.py --name companion --timeout 20 "
                "--notify-timeout 10 --screen-final-timeout 30 --expect-real-panel "
                f"--output {session_root(target)}\\companion-ble-real-bench.json --json"
            ),
            f"python .\\tools\\verify_expression_panel_evidence_record.py --record {session_root(target)}\\panel-evidence-record.json",
        ],
        "visual_capture_items": [
            {
                "demo_id": step["demo_id"],
                "step_index": step["step_index"],
                "event": step["event"],
                "visible_expression": step["visible_expression"],
                "expected_result": step["expected_result"],
                "capture_mode": step["capture_mode"],
                "expected_fixture": step["fixture_path"],
                "expected_fixture_sha256": step["fixture_sha256"],
                "target_photo": visual_path(
                    target,
                    int(step["demo_order"]),
                    int(step["step_index"]),
                    str(step["visible_expression"]),
                ),
            }
            for step in steps
        ],
        "promotion_rule": (
            "This handoff is a checklist only; the hardware gate still needs the filled "
            "panel evidence record, real BLE rendered/ok artifact, diagnostics bundle, "
            "and visual proof before PASS can be claimed."
        ),
        "real_ble_failure_evidence": {
            "failed_runs_preserve_operations": True,
            "required_fields": ["operations", "partial_operation_count"],
        },
    }


def build_report(errors: list[str]) -> dict[str, Any]:
    demo_sequence = load_json(DEMO_SEQUENCE, errors)
    real_ble = load_json(REAL_BLE_BENCH, errors)
    panel_session = load_json(PANEL_SESSION, errors)
    panel_plan = load_json(PANEL_PLAN, errors)
    panel_gate = load_json(PANEL_GATE, errors)
    panel_recovery = load_json(PANEL_RECOVERY_GATE, errors)
    load_json(PANEL_TEMPLATE, errors)
    if errors:
        return {"schema_id": SCHEMA_ID, "status": "FAIL", "errors": errors}

    demo_faces = sorted(str(face) for face in demo_sequence.get("summary", {}).get("expression_coverage", []))
    real_ble_faces = set(
        str(face)
        for face in real_ble.get("expression_status_sequence_operation", {}).get("required_faces", [])
    )
    real_ble_covered_faces = sorted(set(demo_faces) & real_ble_faces)
    manual_visual_required_faces = sorted(set(demo_faces) - real_ble_faces)
    steps = flatten_demo_steps(demo_sequence, real_ble_faces)
    manual_visual_step_count = sum(1 for step in steps if step["capture_mode"] == "manual_visual_required")

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "claim_scope": "no_hardware_handoff_plan",
        "gate_id": "wb55_real_panel_refresh",
        "current_gate_status": panel_recovery.get("status"),
        "real_refresh_claimed": False,
        "historical_wb55_refresh_evidence_status": panel_gate.get("status"),
        "historical_wb55_real_refresh_claimed": panel_gate.get("historical_real_refresh_claimed"),
        "sources": {
            "demo_sequence": rel(DEMO_SEQUENCE),
            "demo_sequence_sha256": sha256_hex(DEMO_SEQUENCE.read_bytes()),
            "real_ble_bench": rel(REAL_BLE_BENCH),
            "real_ble_bench_sha256": sha256_hex(REAL_BLE_BENCH.read_bytes()),
            "panel_hardware_session": rel(PANEL_SESSION),
            "panel_hardware_acceptance_plan": rel(PANEL_PLAN),
            "panel_hardware_gate": rel(PANEL_GATE),
            "panel_hardware_recovery_gate": rel(PANEL_RECOVERY_GATE),
            "panel_evidence_template": rel(PANEL_TEMPLATE),
            "screen_doc": rel(SCREEN_DOC),
            "epaper_readme": rel(EPAPER_README),
            "wba_rules": rel(WBA_RULES),
        },
        "summary": {
            "target_count": len(TARGETS),
            "demo_count": int(demo_sequence.get("summary", {}).get("demo_count", 0)),
            "demo_step_count": len(steps),
            "demo_expression_coverage": demo_faces,
            "real_ble_sequence_faces": sorted(real_ble_faces),
            "real_ble_covered_demo_faces": real_ble_covered_faces,
            "manual_visual_required_faces": manual_visual_required_faces,
            "manual_visual_step_count": manual_visual_step_count,
            "operator_markdown": rel(REPO_ROOT / DEFAULT_MARKDOWN),
        },
        "handoff_contract": {
            "reuses_no_hardware_demo_sequence": True,
            "reuses_real_ble_screen_bench": True,
            "reuses_panel_hardware_session_scaffold": True,
            "does_not_move_hardware_gate": True,
            "manual_visual_gap_is_explicit": True,
            "wba55_wba65_reuse_same_demo_order": True,
        },
        "demo_steps": steps,
        "target_handoffs": [build_target_handoff(target, steps) for target in TARGETS],
        "source_gate_snapshot": {
            "panel_session_gate_status": panel_session.get("current_gate_status"),
            "panel_plan_gate_status": panel_plan.get("current_gate_status"),
            "current_panel_recovery_status": panel_recovery.get("status"),
            "current_panel_real_refresh_claimed": False,
            "historical_panel_gate_status": panel_gate.get("status"),
            "historical_panel_gate_real_refresh_claimed": panel_gate.get("historical_real_refresh_claimed"),
            "real_ble_expect_panel_flag": real_ble.get("bench_operation", {}).get("real_panel_flag"),
            "real_ble_contract_only_sequence": real_ble.get("expression_status_sequence_operation", {}).get("contract_only"),
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_demo_panel_handoff.py",
            "python .\\tools\\verify_expression_demo_sequence.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_panel_hardware_session.py",
            "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
        ],
    }


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Companion Screen Expression Demo Panel Handoff",
        "",
        f"Status: {report.get('status')}",
        f"Gate snapshot: `{report.get('gate_id')}` is `{report.get('current_gate_status')}`",
        f"Demo source: `{report.get('sources', {}).get('demo_sequence')}`",
        f"Real BLE bench source: `{report.get('sources', {}).get('real_ble_bench')}`",
        "",
        "## Coverage",
        "",
        f"- Demo steps: {summary.get('demo_step_count')}",
        f"- Demo expressions: {', '.join(summary.get('demo_expression_coverage', []))}",
        f"- Real BLE sequence faces: {', '.join(summary.get('real_ble_sequence_faces', []))}",
        f"- Manual visual required faces: {', '.join(summary.get('manual_visual_required_faces', []))}",
        f"- Manual visual step count: {summary.get('manual_visual_step_count')}",
        "",
        "## Step Capture Checklist",
        "",
        "| Demo | Step | Event | Face | Result | Capture mode | Fixture |",
        "|---|---:|---|---|---|---|---|",
    ]
    for step in report.get("demo_steps", []):
        lines.append(
            "| "
            f"`{md_cell(step.get('demo_id'))}` | "
            f"{step.get('step_index')} | "
            f"`{md_cell(step.get('event'))}` | "
            f"`{md_cell(step.get('visible_expression'))}` | "
            f"`{md_cell(step.get('expected_result'))}` | "
            f"`{md_cell(step.get('capture_mode'))}` | "
            f"`{md_cell(step.get('fixture_path'))}` |"
        )
    lines.extend(["", "## Target Sessions", "", "| Target | Visual root | BLE lock |", "|---|---|---|"])
    for target in report.get("target_handoffs", []):
        lines.append(
            "| "
            f"`{md_cell(target.get('target'))}` | "
            f"`{md_cell(target.get('demo_visual_root'))}` | "
            f"`{md_cell(target.get('hardware_lock_resources'))}` |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_report(report: dict[str, Any], errors: list[str]) -> None:
    require(report.get("schema_id") == SCHEMA_ID, "unexpected demo panel handoff schema", errors)
    require(report.get("status") == "PASS", "demo panel handoff must be PASS", errors)
    require(report.get("claim_scope") == "no_hardware_handoff_plan", "demo panel handoff must be a no-hardware plan", errors)
    require(report.get("current_gate_status") == "DEFERRED_HARDWARE_FTS02_BOOST", "demo panel handoff must record the current FTS02 blocker", errors)
    require(report.get("real_refresh_claimed") is False, "demo panel handoff must not claim current WB55 refresh", errors)
    require(report.get("historical_wb55_refresh_evidence_status") == "PASS", "demo panel handoff must retain historical WB55 evidence", errors)
    require(report.get("historical_wb55_real_refresh_claimed") is True, "demo panel handoff must preserve the historical refresh claim", errors)
    summary = report.get("summary", {})
    require(summary.get("demo_step_count") == len(report.get("demo_steps", [])), "demo panel handoff step count mismatch", errors)
    require(summary.get("target_count") == len(TARGETS), "demo panel handoff target count mismatch", errors)
    require(
        summary.get("manual_visual_required_faces") == EXPECTED_MANUAL_VISUAL_FACES,
        "manual visual required faces drifted from known real BLE sequence gap",
        errors,
    )
    require(summary.get("manual_visual_step_count", 0) > 0, "demo panel handoff must expose manual visual steps", errors)
    contract = report.get("handoff_contract", {})
    for key in [
        "reuses_no_hardware_demo_sequence",
        "reuses_real_ble_screen_bench",
        "reuses_panel_hardware_session_scaffold",
        "does_not_move_hardware_gate",
        "manual_visual_gap_is_explicit",
        "wba55_wba65_reuse_same_demo_order",
    ]:
        require(contract.get(key) is True, f"demo panel handoff contract missing {key}", errors)
    targets = {entry.get("target"): entry for entry in report.get("target_handoffs", []) if isinstance(entry, dict)}
    require(set(targets) == set(TARGETS), "demo panel handoff must cover WB55, WBA55, and WBA65", errors)
    for target, entry in targets.items():
        serialized = json.dumps(entry, sort_keys=True)
        normalized = serialized.replace("\\\\", "\\")
        require(target_resources(str(target)) in normalized, f"{target} handoff missing hardware lock resources", errors)
        require(target_resource_arg(str(target)) in normalized, f"{target} handoff must quote hardware lock resources in commands", errors)
        require("partial_operation_count" in normalized, f"{target} handoff missing partial failure evidence", errors)
        require("--expect-real-panel" in normalized, f"{target} handoff missing real-panel BLE command", errors)
        require("verify_expression_panel_evidence_record.py --record" in normalized, f"{target} handoff missing record validator", errors)
        require("manual_visual_required" in normalized, f"{target} handoff missing manual visual capture mode", errors)
        require("real_ble_sequence_baseline_plus_visual" in normalized, f"{target} handoff missing real BLE capture mode", errors)
        for capture in entry.get("visual_capture_items", []):
            path = str(capture.get("target_photo", ""))
            require(path.startswith(session_root(str(target))), f"{target} visual capture path leaves session root: {path}", errors)
        if str(target).startswith("WBA"):
            for wb55_pin in ["PA9", "PC1", "PC2", "PA6", "SPI2_CS"]:
                require(wb55_pin not in normalized, f"{target} handoff leaked WB55 pin fact {wb55_pin}", errors)


def check_docs(errors: list[str]) -> None:
    for path in [SCREEN_DOC, EPAPER_README, WBA_RULES]:
        require(path.exists(), f"missing doc source {rel(path)}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "screen_expression_demo_panel_handoff",
            "companion-screen-expression-demo-panel-handoff.json",
            "companion-screen-expression-demo-panel-handoff.md",
            "verify_expression_demo_panel_handoff.py",
            "manual_visual_required_faces",
        ]:
            require(token in text, f"{rel(path)} missing demo panel handoff token {token}", errors)


def check_outputs(
    fixture_path: pathlib.Path,
    markdown_path: pathlib.Path,
    report: dict[str, Any],
    markdown: str,
    errors: list[str],
) -> None:
    require(fixture_path.exists(), f"missing demo panel handoff fixture: {rel(fixture_path)}", errors)
    if fixture_path.exists():
        actual = json.loads(fixture_path.read_text(encoding="utf-8"))
        require(actual == report, f"{rel(fixture_path)} is stale; rerun with --write-fixture", errors)
    require(markdown_path.exists(), f"missing demo panel handoff checklist: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        require(markdown_path.read_text(encoding="utf-8") == markdown, f"{rel(markdown_path)} is stale; rerun with --write-fixture", errors)


def write_outputs(fixture_path: pathlib.Path, markdown_path: pathlib.Path, report: dict[str, Any], markdown: str) -> None:
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic JSON and Markdown handoff artifacts.")
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
        print("FAIL: Companion screen expression demo panel handoff checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen expression demo panel handoff verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
