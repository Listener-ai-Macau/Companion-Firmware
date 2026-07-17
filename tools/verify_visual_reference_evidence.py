#!/usr/bin/env python3
"""Audit Companion generated-art ledgers before any visual acceptance claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART_ITERATIONS = ROOT / "docs" / "art" / "iterations"
FIXTURE = ROOT / "docs" / "validation" / "companion-visual-reference-evidence.json"
SCHEMA_ID = "companion.visual_reference_evidence.v1"
WORKFLOW_RULE_PATH = "docs/agent_quickstart.md"
PRODUCT_RULE_PATH = "docs/companion_product_requirements.md"
DEFAULT_WORKFLOW_REPO = Path(r"C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow")

PENDING_MARKER = "PENDING_OWNER_VISUAL_REVIEW"
REJECTED_MARKERS = ("rejected", "not_used")
ACTIVE_MARKERS = ("activated", "active_cemp", "resource_revision_active")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def resolve_workflow_rule() -> tuple[Path, str]:
    configured = os.environ.get("AI_WORKFLOW_REPO", "").strip()
    candidates = []
    if configured:
        candidates.append((Path(configured), "AI_WORKFLOW_REPO"))
    candidates.append((DEFAULT_WORKFLOW_REPO, "default_workflow_repo"))
    for repository, source in candidates:
        if (repository / "docs" / "agent_quickstart.md").is_file():
            return repository / WORKFLOW_RULE_PATH, source
    return DEFAULT_WORKFLOW_REPO / WORKFLOW_RULE_PATH, "default_workflow_repo_missing_quickstart"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def path_with_hash(path_text: str, expected_hash: str, label: str, errors: list[str]) -> dict[str, Any]:
    path = ROOT / path_text
    exists = path.is_file()
    actual_hash = sha256(path) if exists else None
    require(exists, f"{label} missing file {path_text}", errors)
    require(bool(expected_hash), f"{label} missing SHA-256", errors)
    if exists and expected_hash:
        require(actual_hash == expected_hash.upper(), f"{label} SHA-256 drifted for {path_text}", errors)
    return {
        "path": path_text,
        "expected_sha256": expected_hash.upper(),
        "actual_sha256": actual_hash,
        "hash_matches": exists and bool(expected_hash) and actual_hash == expected_hash.upper(),
    }


def is_pending(iteration: dict[str, Any]) -> bool:
    return "candidate" in str(iteration.get("status", "")).lower() or "pending_owner" in str(
        iteration.get("review", {}).get("outcome", "")
    ).lower()


def is_rejected(iteration: dict[str, Any]) -> bool:
    values = (
        str(iteration.get("status", "")).lower(),
        str(iteration.get("review", {}).get("outcome", "")).lower(),
        str(iteration.get("implementation", {}).get("status", "")).lower(),
    )
    return any(marker in value for marker in REJECTED_MARKERS for value in values)


def requires_output(iteration: dict[str, Any]) -> bool:
    outcome = str(iteration.get("review", {}).get("outcome", "")).lower()
    status = str(iteration.get("status", "")).lower()
    return outcome != "not_generated" and status not in {"superseded", "prompt_ready"}


def active_implementation(iteration: dict[str, Any]) -> bool:
    implementation = iteration.get("implementation", {})
    if not isinstance(implementation, dict):
        return False
    status = str(implementation.get("status", "")).lower()
    explicitly_inactive = "not_activated" in status or "not_started" in status
    return (
        not explicitly_inactive
        and (any(marker in status for marker in ACTIVE_MARKERS) or implementation.get("resource_revision") is not None)
    )


def audit_ledger(path: Path, errors: list[str]) -> dict[str, Any]:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    label = rel(path)
    require(ledger.get("schema") == "denzic.product_visual_iteration.v1", f"{label} schema drifted", errors)
    require(ledger.get("rule") == WORKFLOW_RULE_PATH, f"{label} must point at the workflow quickstart", errors)
    require(ledger.get("product_rule") == PRODUCT_RULE_PATH, f"{label} must point at the Companion visual-source registry", errors)
    require(bool(ledger.get("feature")), f"{label} missing feature", errors)
    require(bool(ledger.get("target_profile")), f"{label} missing target profile", errors)

    baseline = ledger.get("baseline")
    require(isinstance(baseline, dict), f"{label} missing immutable accepted baseline", errors)
    baseline_result: dict[str, Any] = {}
    if isinstance(baseline, dict):
        source = str(baseline.get("accepted_source", ""))
        expected_hash = str(baseline.get("sha256", ""))
        require(bool(source), f"{label} baseline missing accepted_source", errors)
        require(bool(baseline.get("owner_visual_decision")), f"{label} baseline missing owner_visual_decision", errors)
        require(bool(baseline.get("comparison_artifact")), f"{label} baseline missing comparison_artifact", errors)
        if source:
            baseline_result = path_with_hash(source, expected_hash, f"{label} baseline", errors)
        comparison = ROOT / str(baseline.get("comparison_artifact", ""))
        require(comparison.is_file(), f"{label} baseline comparison artifact is missing", errors)

    iterations = ledger.get("iterations", [])
    require(isinstance(iterations, list) and iterations, f"{label} needs one or more iterations", errors)
    rows: list[dict[str, Any]] = []
    for iteration in iterations if isinstance(iterations, list) else []:
        if not isinstance(iteration, dict):
            errors.append(f"{label} iteration must be an object")
            continue
        iteration_id = str(iteration.get("iteration_id", ""))
        review = iteration.get("review", {})
        implementation = iteration.get("implementation", {})
        require(bool(iteration_id), f"{label} iteration missing iteration_id", errors)
        require(bool(iteration.get("status")), f"{label} {iteration_id} missing durable status", errors)
        require(bool(iteration.get("authoring_request")), f"{label} {iteration_id} missing authoring_request", errors)
        require(bool(iteration.get("prompt")), f"{label} {iteration_id} missing exact prompt", errors)
        require(bool(iteration.get("source_references")), f"{label} {iteration_id} missing source references", errors)
        require(isinstance(review, dict), f"{label} {iteration_id} missing review", errors)
        require(bool(review.get("outcome")), f"{label} {iteration_id} missing review outcome", errors)
        require(bool(review.get("reason")), f"{label} {iteration_id} missing review reason", errors)
        require(isinstance(implementation, dict), f"{label} {iteration_id} missing implementation mapping", errors)
        if isinstance(implementation, dict):
            require(bool(implementation.get("status")), f"{label} {iteration_id} missing implementation status", errors)

        output = iteration.get("output")
        expected_hash = iteration.get("sha256")
        output_result: dict[str, Any] | None = None
        if output or expected_hash:
            require(bool(output) and bool(expected_hash), f"{label} {iteration_id} output/hash must be paired", errors)
            if output and expected_hash:
                output_result = path_with_hash(str(output), str(expected_hash), f"{label} {iteration_id}", errors)
        elif requires_output(iteration):
            errors.append(f"{label} {iteration_id} lacks preserved generated output/hash")

        pending = is_pending(iteration)
        rejected = is_rejected(iteration)
        implementation_active = active_implementation(iteration)
        if pending:
            require(not implementation_active, f"{label} {iteration_id} candidate must not activate resources", errors)
            require(
                PENDING_MARKER in str(review.get("outcome", "")).upper()
                or "pending_owner" in str(review.get("outcome", "")).lower()
                or "pending_owner" in str(iteration.get("status", "")).lower(),
                f"{label} {iteration_id} candidate must remain pending owner review",
                errors,
            )
        if rejected:
            require(not implementation_active, f"{label} {iteration_id} rejected art must not activate resources", errors)

        rows.append(
            {
                "iteration_id": iteration_id,
                "status": iteration.get("status"),
                "review_outcome": review.get("outcome"),
                "output": output_result,
                "pending_owner_review": pending,
                "rejected": rejected,
                "implementation_status": implementation.get("status") if isinstance(implementation, dict) else None,
                "resource_revision": implementation.get("resource_revision") if isinstance(implementation, dict) else None,
            }
        )

    return {
        "ledger": label,
        "feature": ledger.get("feature"),
        "target_profile": ledger.get("target_profile"),
        "baseline": baseline_result,
        "iterations": rows,
    }


def build_report() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    workflow_rule, _workflow_rule_resolution = resolve_workflow_rule()
    workflow_rule_exists = workflow_rule.is_file()
    product_rule = ROOT / PRODUCT_RULE_PATH
    require(workflow_rule_exists, f"workflow quickstart is missing: {workflow_rule}", errors)
    require(product_rule.is_file(), f"Companion visual-source registry is missing: {product_rule}", errors)
    workflow_rule_sha256 = sha256(workflow_rule) if workflow_rule_exists else None
    product_rule_sha256 = sha256(product_rule) if product_rule.is_file() else None
    ledgers = sorted(ART_ITERATIONS.glob("*/iteration-ledger.json"))
    require(bool(ledgers), "no visual iteration ledgers found", errors)
    rows = [audit_ledger(path, errors) for path in ledgers]
    pending = [
        {"ledger": row["ledger"], "iteration_id": item["iteration_id"]}
        for row in rows for item in row["iterations"] if item["pending_owner_review"]
    ]
    rejected = [
        {"ledger": row["ledger"], "iteration_id": item["iteration_id"]}
        for row in rows for item in row["iterations"] if item["rejected"]
    ]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_LEDGER_INTEGRITY" if not errors else "FAIL",
        "purpose": "Machine audit only. It proves visual evidence is retained; it does not replace owner visual acceptance.",
        "workflow_rule": {
            "path": WORKFLOW_RULE_PATH,
            "sha256": workflow_rule_sha256,
            "resolution": "agent_quickstart",
        },
        "product_rule": {"path": PRODUCT_RULE_PATH, "sha256": product_rule_sha256},
        "visual_pass_rule": (
            "A visible design stays PENDING_VISUAL_BASELINE or PENDING_OWNER_VISUAL_REVIEW until its approved source, "
            "prompt, source/output hashes, comparison artifact, and owner decision are all present."
        ),
        "ledger_count": len(rows),
        "ledgers": rows,
        "pending_owner_visual_review": pending,
        "rejected_history_preserved": rejected,
        "errors": errors,
    }, errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-fixture", action="store_true")
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args(argv)
    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    report, errors = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write_fixture and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(rendered, encoding="utf-8")
    elif not args.write_fixture:
        if not fixture.is_file():
            errors.append(f"missing {rel(fixture)}")
        elif fixture.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(fixture)}; rerun with --write-fixture")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: visual reference evidence retained -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
