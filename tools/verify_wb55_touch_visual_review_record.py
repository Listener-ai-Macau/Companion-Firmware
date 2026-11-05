#!/usr/bin/env python3
"""Verify the filled WB55 touch/visual operator review record.

The generated default fixture is intentionally NO_GO_NOT_STARTED. It documents
the publishable acceptance contract without pretending that the human review has
already happened.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.json"
DEFAULT_RECORD = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-record.json"
DEFAULT_FILLED_INPUT = ROOT / ".cache/validation/wb55-touch-visual-review/latest-review-record.json"
SCHEMA_ID = "companion.pendant.wb55_touch_visual_review_record.v1"
TEMPLATE_SCHEMA_ID = "companion.pendant.wb55_touch_visual_review_template.v1"
NO_GO_STATUS = "NO_GO_NOT_STARTED"
PASS_STATUS = "PASS_READY_FOR_PUBLISHABLE_REVIEW"
ALLOWED_STATES = {
    "fixed_with_machine_evidence",
    "deferred_by_product_decision",
    "accepted_benign_with_evidence",
    "open_requires_fix",
}
NON_PASS_STATES = {"open_requires_fix"}
VISUAL_ISSUE_CLASSES = {
    "none",
    "physical afterimage",
    "stale queued frame",
    "stale asset revision",
    "rescue/procedural fallback leakage",
    "stale_generation_content",
}
SOFTWARE_GENERATION_CLASSES = {
    "stale queued frame",
    "stale asset revision",
    "rescue/procedural fallback leakage",
    "stale_generation_content",
}
VISUAL_ISSUE_KEYWORDS = (
    "old",
    "ghost",
    "afterimage",
    "stale",
    "mixed",
    "interleav",
    "residual",
    "旧",
    "残影",
    "交织",
    "混",
    "重影",
    "上一版",
    "旧风格",
)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_steps(template: dict[str, Any]) -> list[dict[str, Any]]:
    records = template.get("review_records", [])
    return [record for record in records if isinstance(record, dict)]


def empty_record_for_step(template_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_step_id": template_record.get("source_step_id"),
        "title": template_record.get("title"),
        "operator_observation": "",
        "operator_note": "",
        "triage_items": [],
        "visual_issue_classification": "none",
        "resolution_state": "open_requires_fix",
        "evidence_path": "",
        "next_review_scope": "",
        "publishable_pass_allowed": False,
    }


def normalize_filled_record(data: dict[str, Any]) -> list[dict[str, Any]]:
    records = data.get("review_records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def validate_filled_records(
    records: list[dict[str, Any]],
    template: dict[str, Any],
    filled_input: pathlib.Path,
) -> tuple[str, list[str], list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    open_items: list[dict[str, Any]] = []
    expected = expected_steps(template)
    expected_ids = [str(record.get("source_step_id")) for record in expected]
    record_ids = [str(record.get("source_step_id")) for record in records]
    if record_ids != expected_ids:
        errors.append("review_records must mirror template source_step_id order")

    for index, record in enumerate(records):
        step_id = str(record.get("source_step_id", ""))
        state = str(record.get("resolution_state", ""))
        note = str(record.get("operator_note", "")).strip()
        observation = str(record.get("operator_observation", "")).strip()
        evidence = str(record.get("evidence_path", "")).strip()
        triage_items = record.get("triage_items", [])
        visual_issue = str(record.get("visual_issue_classification", "none")).strip() or "none"
        publishable = record.get("publishable_pass_allowed")
        combined_note = f"{note} {observation}".lower()

        if state not in ALLOWED_STATES:
            errors.append(f"{step_id or index}: invalid resolution_state {state!r}")
        if visual_issue not in VISUAL_ISSUE_CLASSES:
            errors.append(f"{step_id or index}: invalid visual_issue_classification {visual_issue!r}")
        if not observation:
            errors.append(f"{step_id or index}: operator_observation is required in filled record")
        if note and not isinstance(triage_items, list):
            errors.append(f"{step_id or index}: triage_items must be a list")
        if note and isinstance(triage_items, list) and not triage_items:
            errors.append(f"{step_id or index}: non-empty operator_note requires triage_items")
        if any(keyword in combined_note for keyword in VISUAL_ISSUE_KEYWORDS) and visual_issue == "none":
            errors.append(f"{step_id or index}: old/ghost/mixed visual note requires visual_issue_classification")
        if state in NON_PASS_STATES:
            open_items.append(
                {
                    "source_step_id": step_id,
                    "reason": "resolution_state is open_requires_fix",
                    "operator_note": note,
                }
            )
        else:
            if not evidence:
                errors.append(f"{step_id or index}: closed resolution_state requires evidence_path")
            if publishable is not True:
                errors.append(f"{step_id or index}: closed step must set publishable_pass_allowed=true")
            if note and not str(record.get("next_review_scope", "")).strip():
                errors.append(f"{step_id or index}: closed noted item requires next_review_scope")
            if visual_issue in SOFTWARE_GENERATION_CLASSES and state == "accepted_benign_with_evidence":
                errors.append(f"{step_id or index}: stale generation content cannot be accepted benign")
        if publishable is True and state in NON_PASS_STATES:
            errors.append(f"{step_id or index}: open step cannot allow publishable PASS")

    if errors or open_items:
        return "NO_GO_OPEN_REVIEW_ITEMS", errors, open_items, expected_ids
    return PASS_STATUS, errors, open_items, expected_ids


def build_record(filled_input: pathlib.Path) -> dict[str, Any]:
    template = load_json(TEMPLATE)
    if template.get("schema_id") != TEMPLATE_SCHEMA_ID:
        raise ValueError("unexpected review template schema")
    expected = expected_steps(template)
    expected_ids = [str(record.get("source_step_id")) for record in expected]
    triage = template.get("triage_contract", {})

    if filled_input.exists():
        source_data = load_json(filled_input)
        filled_records = normalize_filled_record(source_data)
        status, errors, open_items, _ = validate_filled_records(filled_records, template, filled_input)
        review_records = filled_records
        source_status = str(source_data.get("status", "FILLED_RECORD_INPUT"))
    else:
        errors = []
        open_items = [
            {
                "source_step_id": step_id,
                "reason": "human review has not started",
                "operator_note": "",
            }
            for step_id in expected_ids
        ]
        review_records = [empty_record_for_step(record) for record in expected]
        status = NO_GO_STATUS
        source_status = "MISSING_FILLED_INPUT"

    publishable_pass_allowed = status == PASS_STATUS and not errors and not open_items
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": "filled_operator_review_record_validator",
        "publishable_pass_allowed": publishable_pass_allowed,
        "source_template": rel(TEMPLATE),
        "filled_input_path": rel(filled_input),
        "source_status": source_status,
        "gate_id": template.get("gate_id"),
        "target": template.get("target"),
        "required_step_ids": expected_ids,
        "review_records": review_records,
        "open_items": open_items,
        "validation_errors": errors,
        "triage_contract": {
            "required_fields": triage.get("required_fields", []),
            "allowed_resolution_states": triage.get("allowed_resolution_states", []),
            "allowed_visual_issue_classifications": triage.get("allowed_visual_issue_classifications", []),
            "publishable_pass_rule": triage.get("publishable_pass_rule", ""),
        },
        "next_action": (
            "等待操作者明确说开始验收，然后把填好的结构化 review record 写入 filled_input_path。"
            if status == NO_GO_STATUS
            else "关闭 open review items 并补齐 evidence_path 后重新运行本校验器。"
            if status != PASS_STATUS
            else "可作为 publishable human review evidence 附到 acceptance packet。"
        ),
        "validation_commands": [
            "python .\\tools\\verify_wb55_touch_visual_review_record.py",
            "python .\\tools\\render_wb55_touch_visual_review_template.py",
            "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
        ],
    }


def verify_record(data: dict[str, Any], expected: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if data.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if data.get("claim_scope") != "filled_operator_review_record_validator":
        errors.append("claim_scope drifted")
    if data.get("gate_id") != "wb55_touch_visual_acceptance":
        errors.append("record must point at wb55_touch_visual_acceptance")
    if data.get("source_template") != rel(TEMPLATE):
        errors.append("source_template drifted")
    status = data.get("status")
    if status not in {NO_GO_STATUS, "NO_GO_OPEN_REVIEW_ITEMS", PASS_STATUS}:
        errors.append(f"unexpected status {status!r}")
    if status != PASS_STATUS and data.get("publishable_pass_allowed") is not False:
        errors.append("non-PASS review record must not allow publishable PASS")
    if status == PASS_STATUS and data.get("publishable_pass_allowed") is not True:
        errors.append("PASS review record must allow publishable PASS")
    validation_errors = data.get("validation_errors", [])
    if validation_errors:
        for error in validation_errors:
            errors.append(f"filled review validation error: {error}")

    template = load_json(TEMPLATE)
    expected_ids = [str(record.get("source_step_id")) for record in expected_steps(template)]
    if data.get("required_step_ids") != expected_ids:
        errors.append("required_step_ids must mirror review template")
    record_ids = [str(record.get("source_step_id")) for record in data.get("review_records", [])]
    if record_ids != expected_ids:
        errors.append("review_records must mirror review template")

    triage = data.get("triage_contract", {})
    for field in ("source_step_id", "operator_note", "triage_items", "resolution_state", "evidence_path", "next_review_scope", "visual_issue_classification"):
        if field not in triage.get("required_fields", []):
            errors.append(f"triage_contract missing required field {field}")
    for state in ALLOWED_STATES:
        if state not in triage.get("allowed_resolution_states", []):
            errors.append(f"triage_contract missing allowed state {state}")
    for state in VISUAL_ISSUE_CLASSES:
        if state not in triage.get("allowed_visual_issue_classifications", []):
            errors.append(f"triage_contract missing visual issue class {state}")
    if "open_requires_fix" not in str(triage.get("publishable_pass_rule", "")):
        errors.append("publishable rule must block open_requires_fix")
    if "stale_generation_content" not in str(triage.get("publishable_pass_rule", "")):
        errors.append("publishable rule must block benign stale_generation_content")
    serialized = json.dumps(data, ensure_ascii=False)
    for token in (
        "publishable_pass_allowed",
        "daily_tap_social_response",
        "premium_pet_feel",
        "open_requires_fix",
        "evidence_path",
        "visual_issue_classification",
        "stale_generation_content",
        "verify_wb55_touch_visual_review_record.py",
    ):
        if token not in serialized:
            errors.append(f"record missing token {token}")
    if status == NO_GO_STATUS and NO_GO_STATUS not in serialized:
        errors.append(f"record missing token {NO_GO_STATUS}")
    if expected is not None and data != expected:
        errors.append("record fixture is stale; rerun with --write")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update the deterministic review-record fixture.")
    parser.add_argument("--record", type=pathlib.Path, default=DEFAULT_RECORD)
    parser.add_argument("--filled-input", type=pathlib.Path, default=DEFAULT_FILLED_INPUT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    record_path = args.record if args.record.is_absolute() else ROOT / args.record
    filled_input = args.filled_input if args.filled_input.is_absolute() else ROOT / args.filled_input
    expected = build_record(filled_input)
    errors = verify_record(expected)

    if args.write and not errors:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(expected, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.write:
        if not record_path.exists():
            errors.append(f"missing {rel(record_path)}")
        else:
            actual = load_json(record_path)
            errors.extend(verify_record(actual, expected))

    if errors:
        print("FAIL: WB55 touch/visual review record checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 touch/visual review record verified -> {rel(record_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
