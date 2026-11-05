#!/usr/bin/env python3
"""Render the WB55 touch/visual operator review template."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKET = ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.json"
DEFAULT_MD = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.md"
SCHEMA_ID = "companion.pendant.wb55_touch_visual_review_template.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_template() -> dict[str, Any]:
    packet = load_json(PACKET)
    triage = packet.get("review_note_triage_contract", {})
    return {
        "schema_id": SCHEMA_ID,
        "status": "TEMPLATE_NOT_ACCEPTANCE_RESULT",
        "claim_scope": "blank_operator_review_template",
        "source_packet": rel(PACKET),
        "gate_id": packet.get("gate_id"),
        "target": packet.get("target"),
        "start_rule": packet.get("start_rule"),
        "machine_precondition": packet.get("machine_precondition"),
        "machine_state": packet.get("machine_state", {}),
        "triage_contract": triage,
        "review_records": [
            {
                "source_step_id": item.get("id"),
                "title": item.get("title"),
                "operator_action": item.get("operator_action"),
                "success_signal": item.get("success_signal"),
                "regression_guard": item.get("regression_guard"),
                "expected_record_fields": item.get("record", []),
                "operator_observation": "",
                "operator_note": "",
                "triage_items": [],
                "visual_issue_classification": "none",
                "resolution_state": "open_requires_fix",
                "evidence_path": "",
                "next_review_scope": "",
                "publishable_pass_allowed": False,
            }
            for item in packet.get("operator_steps", [])
        ],
        "completion_rule": (
            "This template is not a PASS artifact. After review, each non-empty "
            "operator_note must be split into triage_items, assigned one allowed "
            "resolution_state, and linked to evidence_path before the acceptance "
            "packet can be considered publishable PASS."
        ),
        "validation_commands": [
            "python .\\tools\\render_wb55_touch_visual_review_template.py",
            "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
        ],
    }


def render_markdown(template: dict[str, Any]) -> str:
    lines = [
        "# WB55 Touch/Visual Review Template",
        "",
        "This file is generated. Fill a copy during the active acceptance session;",
        "do not edit this template as the final evidence record.",
        "",
        f"- Status: `{template['status']}`",
        f"- Gate: `{template['gate_id']}`",
        f"- Target: `{template['target']}`",
        f"- Source packet: `{template['source_packet']}`",
        f"- Start rule: {template['start_rule']}",
        f"- Machine precondition: {template['machine_precondition']}",
        "",
        "## Review Records",
        "",
    ]
    for index, record in enumerate(template["review_records"], start=1):
        lines.extend([
            f"### {index}. {record['title']}",
            "",
            f"- Step ID: `{record['source_step_id']}`",
            f"- Action: {record['operator_action']}",
            f"- Success signal: {record['success_signal']}",
            f"- Regression guard: {record['regression_guard']}",
            "- Expected record fields:",
        ])
        lines.extend(f"  - {field}" for field in record["expected_record_fields"])
        lines.extend([
            "- Operator observation:",
            "- Operator note:",
            "- Triage items:",
            "  - (pending)",
            "- Visual issue classification: `none`",
            "- Resolution state: `open_requires_fix`",
            "- Evidence path:",
            "- Next review scope:",
            "- Publishable PASS allowed: `false`",
            "",
        ])
    triage = template["triage_contract"]
    lines.extend([
        "## Triage Contract",
        "",
        f"- Scope: {triage.get('scope')}",
        f"- Publishable PASS rule: {triage.get('publishable_pass_rule')}",
        "- Allowed visual issue classifications:",
    ])
    lines.extend(f"  - `{state}`" for state in triage.get("allowed_visual_issue_classifications", []))
    lines.extend([
        "- Allowed resolution states:",
    ])
    lines.extend(f"  - `{state}`" for state in triage.get("allowed_resolution_states", []))
    lines.extend(["", f"Completion rule: {template['completion_rule']}", ""])
    return "\n".join(lines)


def verify(template: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if template.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if template.get("status") != "TEMPLATE_NOT_ACCEPTANCE_RESULT":
        errors.append("review template must not claim acceptance result")
    if template.get("claim_scope") != "blank_operator_review_template":
        errors.append("review template claim scope drifted")
    if template.get("source_packet") != rel(PACKET):
        errors.append("review template source packet drifted")
    triage = template.get("triage_contract", {})
    required_fields = set(triage.get("required_fields", []))
    allowed_states = set(triage.get("allowed_resolution_states", []))
    for field in ("source_step_id", "operator_note", "triage_items", "resolution_state", "evidence_path", "next_review_scope", "visual_issue_classification"):
        if field not in required_fields:
            errors.append(f"triage contract missing required field {field}")
    for state in ("fixed_with_machine_evidence", "deferred_by_product_decision", "accepted_benign_with_evidence", "open_requires_fix"):
        if state not in allowed_states:
            errors.append(f"triage contract missing state {state}")
    visual_issue_classes = set(triage.get("allowed_visual_issue_classifications", []))
    for state in ("none", "physical afterimage", "stale queued frame", "stale asset revision", "rescue/procedural fallback leakage", "stale_generation_content"):
        if state not in visual_issue_classes:
            errors.append(f"triage contract missing visual issue class {state}")
    records = template.get("review_records", [])
    packet = load_json(PACKET)
    if template.get("machine_precondition") != packet.get("machine_precondition"):
        errors.append("review template machine precondition drifted from acceptance packet")
    packet_ids = [item.get("id") for item in packet.get("operator_steps", [])]
    record_ids = [item.get("source_step_id") for item in records]
    if record_ids != packet_ids:
        errors.append("review records must mirror packet operator step order")
    required_operator_steps = {
        "daily_tap_social_response",
        "daily_swipe_pet_response",
        "anywhere_hold_menu_entry",
        "menu_boundary_single_clean_refresh",
        "menu_home_static_vertical_stroke",
        "row_press_and_back",
        "phone_reconnect_advertising",
        "language_switch_single_language",
        "maintenance_single_quiet_flash",
        "premium_pet_feel",
    }
    if set(packet_ids) != required_operator_steps:
        errors.append("review template packet must retain the complete focused interaction coverage")
    if len(records) != len(required_operator_steps):
        errors.append("review template step count does not match focused coverage")
    for record in records:
        if record.get("resolution_state") != "open_requires_fix":
            errors.append(f"{record.get('source_step_id')} template resolution must default open_requires_fix")
        if record.get("publishable_pass_allowed") is not False:
            errors.append(f"{record.get('source_step_id')} template must default publishable_pass_allowed=false")
        if record.get("visual_issue_classification") != "none":
            errors.append(f"{record.get('source_step_id')} template visual_issue_classification must default none")
        if not record.get("expected_record_fields"):
            errors.append(f"{record.get('source_step_id')} missing expected record fields")
    serialized = json.dumps(template, ensure_ascii=False)
    for token in (
        "TEMPLATE_NOT_ACCEPTANCE_RESULT",
        "open_requires_fix",
        "fixed_with_machine_evidence",
        "deferred_by_product_decision",
        "accepted_benign_with_evidence",
        "publishable PASS",
        "daily_tap_social_response",
        "premium_pet_feel",
        "visual_issue_classification",
        "stale_generation_content",
    ):
        if token not in serialized:
            errors.append(f"template missing token {token}")
    packet_precondition = str(packet.get("machine_precondition", ""))
    if packet_precondition.startswith("PASS:"):
        if "PASS: rev" not in serialized:
            errors.append("template missing promoted runtime PASS precondition")
    elif not packet_precondition.startswith("NO_GO_"):
        errors.append("template missing a runtime-recheck blocker precondition")
    return errors


def write_outputs(json_path: pathlib.Path, md_path: pathlib.Path, template: dict[str, Any], markdown: str) -> None:
    json_path.write_text(json.dumps(template, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    md_path = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    template = build_template()
    markdown = render_markdown(template)
    errors = verify(template)

    if args.write and not errors:
        write_outputs(json_path, md_path, template, markdown)
    elif not args.write:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        elif json.loads(json_path.read_text(encoding="utf-8")) != template:
            errors.append(f"stale {rel(json_path)}")
        if not md_path.exists():
            errors.append(f"missing {rel(md_path)}")
        elif md_path.read_text(encoding="utf-8") != markdown:
            errors.append(f"stale {rel(md_path)}")

    if errors:
        print("FAIL: WB55 touch/visual review template checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 touch/visual review template verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
