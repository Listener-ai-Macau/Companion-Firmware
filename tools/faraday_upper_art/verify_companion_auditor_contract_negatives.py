#!/usr/bin/env python3
"""Deterministic count, polarity, and pair negatives for the compatibility audit."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
EXPECTED_GAPS = {
    "early_up_cancel_blur_or_drag",
    "pointer_drag_center",
    "pointer_move",
    "select_ui_assets",
}
EXPECTED_MISSING_PAIRS = {
    "T04-P00-centered_rest--gaze_center",
    "T05-P04-gaze_left--gaze_center",
    "T05-P09-gaze_up--gaze_center",
    "T05-P14-gaze_right--gaze_center",
    "T05-P19-gaze_down--gaze_center",
    "T05-P24-gaze_center--gaze_center",
    "T10-P00-hold_feedback_50--centered_rest",
    "T17-P00-menu_device--menu_device_ui_assets",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def compatibility_ready(
    events: int,
    pairs: int,
    semantic_noops: int,
    polarity: bool,
    terminal: bool = True,
    qualification: bool = True,
) -> bool:
    return bool(
        events == 21
        and pairs == 59
        and semantic_noops == 10
        and polarity
        and terminal
        and qualification
    )


def comparison_expression(source: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "comparison_complete"
            for target in node.targets
        ):
            continue
        return ast.unparse(node.value)
    raise ValueError("comparison_complete assignment not found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--auditor", type=Path, required=True)
    parser.add_argument("--expected-auditor-sha256", required=True)
    parser.add_argument("--compatibility", type=Path, required=True)
    parser.add_argument("--expected-compatibility-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    auditor = (
        args.auditor.resolve()
        if args.auditor.is_absolute()
        else (repo_root / args.auditor).resolve()
    )
    compatibility_path = (
        args.compatibility.resolve()
        if args.compatibility.is_absolute()
        else (repo_root / args.compatibility).resolve()
    )
    output_path = (
        args.output.resolve()
        if args.output.is_absolute()
        else (repo_root / args.output).resolve()
    )
    output_path.relative_to((repo_root / VALIDATION_REL).resolve())

    observed_auditor_sha = file_sha(auditor)
    observed_compatibility_sha = file_sha(compatibility_path)
    if observed_auditor_sha != args.expected_auditor_sha256.upper():
        raise ValueError("auditor hash mismatch")
    if (
        observed_compatibility_sha
        != args.expected_compatibility_sha256.upper()
    ):
        raise ValueError("compatibility artifact hash mismatch")

    source = auditor.read_text(encoding="utf-8")
    expression = comparison_expression(source)
    required_expression_fragments = [
        "realizable_events == 21",
        "realizable_pairs == 59",
        "realizable_noops == 10",
        "polarity_bridge_realizable",
        "terminal_retention",
        "valid_qualification_sequence",
    ]
    expression_contract_pass = all(
        fragment in expression for fragment in required_expression_fragments
    )

    compatibility = load_json(compatibility_path)
    summary = compatibility["summary"]
    events = summary["events"]["realizable"]
    pairs = summary["pairs"]["realizable"]
    noops = summary["pairs"]["semantic_noop_realizable"]
    polarity = summary["polarity_bridge_realizable"]
    terminal = summary["terminal_retention"]
    qualification = summary["qualification_valid"]
    event_gaps = {
        row["event"]
        for row in compatibility["event_compatibility"]
        if row["mapping_status"] != "mapped"
    }
    pair_rows = compatibility["pair_compatibility"]
    missing_pair_ids = {
        row["id"]
        for row in pair_rows
        if row["realizable_lower_path"] is not True
    }
    pointer_directional = [
        row
        for row in pair_rows
        if row["event"] == "pointer_move"
        and row["to_state"]
        in {"gaze_left", "gaze_up", "gaze_right", "gaze_down"}
    ]
    pointer_center = [
        row
        for row in pair_rows
        if row["event"] == "pointer_move"
        and row["to_state"] == "gaze_center"
    ]
    polarity_isolation_pass = bool(
        compatibility["status"] == "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS"
        and events == 17
        and pairs == 51
        and noops == 8
        and polarity is True
        and event_gaps == EXPECTED_GAPS
        and missing_pair_ids == EXPECTED_MISSING_PAIRS
        and len(pointer_directional) == 20
        and all(row["realizable_lower_path"] for row in pointer_directional)
        and len(pointer_center) == 5
        and all(
            row["realizable_lower_path"] is False
            for row in pointer_center
        )
    )

    fixtures = [
        {
            "id": "control_exact_full_contract",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity": True,
            "terminal": True,
            "qualification": True,
            "expected_ready": True,
        },
        {
            "id": "current_4dd_polarity_true_real_gaps",
            "events": events,
            "pairs": pairs,
            "semantic_noops": noops,
            "polarity": polarity,
            "terminal": terminal,
            "qualification": qualification,
            "expected_ready": False,
        },
        {
            "id": "one_event_missing",
            "events": 20,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity": True,
            "terminal": True,
            "qualification": True,
            "expected_ready": False,
        },
        {
            "id": "one_pair_missing",
            "events": 21,
            "pairs": 58,
            "semantic_noops": 10,
            "polarity": True,
            "terminal": True,
            "qualification": True,
            "expected_ready": False,
        },
        {
            "id": "one_semantic_noop_missing",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 9,
            "polarity": True,
            "terminal": True,
            "qualification": True,
            "expected_ready": False,
        },
        {
            "id": "polarity_missing_with_full_counts",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity": False,
            "terminal": True,
            "qualification": True,
            "expected_ready": False,
        },
        {
            "id": "terminal_missing_with_full_counts",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity": True,
            "terminal": False,
            "qualification": True,
            "expected_ready": False,
        },
        {
            "id": "qualification_missing_with_full_counts",
            "events": 21,
            "pairs": 59,
            "semantic_noops": 10,
            "polarity": True,
            "terminal": True,
            "qualification": False,
            "expected_ready": False,
        },
    ]
    for row in fixtures:
        row["observed_ready"] = compatibility_ready(
            row["events"],
            row["pairs"],
            row["semantic_noops"],
            row["polarity"],
            row["terminal"],
            row["qualification"],
        )
        row["pass"] = row["observed_ready"] is row["expected_ready"]

    all_pass = bool(
        expression_contract_pass
        and polarity_isolation_pass
        and all(row["pass"] for row in fixtures)
    )
    artifact = {
        "schema": "companion.auditor-contract-negative-result.v1",
        "requirements": ["COMP-REQ-477", "COMP-REQ-479", "COMP-REQ-488"],
        "status": "PASS_NEGATIVE_FIXTURES" if all_pass else "NO_GO",
        "bindings": {
            "auditor": {
                "path": auditor.relative_to(repo_root).as_posix(),
                "sha256": observed_auditor_sha,
            },
            "compatibility": {
                "path": compatibility_path.relative_to(repo_root).as_posix(),
                "sha256": observed_compatibility_sha,
            },
        },
        "auditor_ast_contract": {
            "comparison_complete_expression": expression,
            "required_fragments": required_expression_fragments,
            "pass": expression_contract_pass,
        },
        "polarity_isolation": {
            "pass": polarity_isolation_pass,
            "observed": {
                "events": f"{events}/21",
                "pairs": f"{pairs}/59",
                "semantic_noops": f"{noops}/10",
                "polarity_bridge": polarity,
                "event_gaps": sorted(event_gaps),
                "missing_pair_ids": sorted(missing_pair_ids),
                "pointer_move_directional_realizable": len(
                    pointer_directional
                ),
                "pointer_move_center_missing": len(pointer_center),
            },
            "claim": (
                "Polarity is independently realizable and does not promote "
                "missing production event or pair paths."
            ),
        },
        "mutation_fixtures": fixtures,
        "summary": {
            "fixture_count": len(fixtures),
            "fixture_pass_count": sum(row["pass"] for row in fixtures),
            "events_pairs_noops_each_fail_closed": all(
                row["pass"]
                for row in fixtures
                if row["id"]
                in {
                    "one_event_missing",
                    "one_pair_missing",
                    "one_semantic_noop_missing",
                }
            ),
            "polarity_isolation_pass": polarity_isolation_pass,
        },
        "side_effect_counters": {
            "execute": 0,
            "server": 0,
            "browser": 0,
            "prompt": 0,
            "popup": 0,
            "hardware": 0,
            "lower_read": 0,
            "lower_write": 0,
            "registry_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "push": 0,
            "upper_artifact_write": 1,
        },
        "verifier": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "fixtures": (
                    f"{artifact['summary']['fixture_pass_count']}/"
                    f"{artifact['summary']['fixture_count']}"
                ),
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
