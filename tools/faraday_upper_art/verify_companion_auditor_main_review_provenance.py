#!/usr/bin/env python3
"""Fail-closed provenance verification for the corrected upper/lower auditor."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
TOOL_REL = Path("tools/faraday_upper_art")
LOWER_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
OLD_ARTIFACTS = {
    (
        VALIDATION_REL
        / "joint-upper-lower-4ddf970-8bd2-comp-req-488.json"
    ): "D2A08C0DAFF41973B048D5F6902457E1359E5D3EEF0ED70D06221BF6C7094B76",
    (
        VALIDATION_REL
        / "upper-lower-compatibility-4ddf970-8bd2-comp-req-488.json"
    ): "34BB174F93392300363BFBB378117A69DC9B71DC77133442853BB3671C3574D3",
}
EXPECTED_GAPS = [
    "early_up_cancel_blur_or_drag",
    "pointer_drag_center",
    "pointer_move",
    "select_ui_assets",
]
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
EXTERNAL_ZERO_KEYS = {
    "execute",
    "server",
    "server_probe",
    "server_start",
    "browser",
    "browser_start",
    "prompt",
    "operator_prompt",
    "operator_execute",
    "popup",
    "hardware",
    "lower_write",
    "registry_write",
    "platform_write",
    "production_write",
    "push",
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


def add_check(
    checks: dict[str, bool],
    name: str,
    value: Any,
) -> None:
    checks[name] = bool(value)


def identity(
    repo_root: Path,
    path: Path,
    expected_sha: str,
) -> dict[str, Any]:
    absolute = (
        path.resolve()
        if path.is_absolute()
        else (repo_root / path).resolve()
    )
    observed = file_sha(absolute)
    return {
        "path": absolute.relative_to(repo_root).as_posix(),
        "expected_sha256": expected_sha.upper(),
        "observed_sha256": observed,
        "match": observed == expected_sha.upper(),
    }


def side_effects_zero(value: dict[str, Any]) -> bool:
    counters = value.get("side_effect_counters")
    return bool(
        isinstance(counters, dict)
        and all(counters.get(key, 0) == 0 for key in EXTERNAL_ZERO_KEYS)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--compatibility", type=Path, required=True)
    parser.add_argument("--expected-compatibility-sha256", required=True)
    parser.add_argument("--joint-result", type=Path, required=True)
    parser.add_argument("--expected-joint-result-sha256", required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--expected-handoff-sha256", required=True)
    parser.add_argument(
        "--auditor-negative-result", type=Path, required=True
    )
    parser.add_argument(
        "--expected-auditor-negative-result-sha256", required=True
    )
    parser.add_argument("--expected-auditor-sha256", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--expected-validator-sha256", required=True)
    parser.add_argument("--expected-handoff-generator-sha256", required=True)
    parser.add_argument(
        "--expected-auditor-negative-verifier-sha256", required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_path = (
        args.output.resolve()
        if args.output.is_absolute()
        else (repo_root / args.output).resolve()
    )
    output_path.relative_to((repo_root / VALIDATION_REL).resolve())

    paths = {
        "auditor": TOOL_REL
        / "audit_companion_upper_lower_compatibility_comp_req_474.py",
        "runner": TOOL_REL
        / "run_companion_joint_offline_gate_comp_req_479.py",
        "validator": TOOL_REL
        / "validate_companion_joint_offline_gate_comp_req_479.py",
        "handoff_generator": TOOL_REL
        / "generate_companion_lower_handoff_contract_comp_req_479.py",
        "auditor_negative_verifier": TOOL_REL
        / "verify_companion_auditor_contract_negatives.py",
        "compatibility": args.compatibility,
        "joint_result": args.joint_result,
        "handoff": args.handoff,
        "auditor_negative_result": args.auditor_negative_result,
    }
    expected = {
        "auditor": args.expected_auditor_sha256,
        "runner": args.expected_runner_sha256,
        "validator": args.expected_validator_sha256,
        "handoff_generator": args.expected_handoff_generator_sha256,
        "auditor_negative_verifier": (
            args.expected_auditor_negative_verifier_sha256
        ),
        "compatibility": args.expected_compatibility_sha256,
        "joint_result": args.expected_joint_result_sha256,
        "handoff": args.expected_handoff_sha256,
        "auditor_negative_result": (
            args.expected_auditor_negative_result_sha256
        ),
    }
    identities = {
        key: identity(repo_root, path, expected[key])
        for key, path in paths.items()
    }
    old_identities = {
        path.as_posix(): identity(repo_root, path, digest)
        for path, digest in OLD_ARTIFACTS.items()
    }

    compatibility = load_json(
        repo_root / identities["compatibility"]["path"]
    )
    joint = load_json(repo_root / identities["joint_result"]["path"])
    handoff = load_json(repo_root / identities["handoff"]["path"])
    negative = load_json(
        repo_root / identities["auditor_negative_result"]["path"]
    )

    checks: dict[str, bool] = {}
    add_check(
        checks,
        "all_requested_identities_exact",
        all(item["match"] for item in identities.values()),
    )
    add_check(
        checks,
        "old_artifacts_unchanged",
        all(item["match"] for item in old_identities.values()),
    )

    summary = compatibility.get("summary", {})
    gap_names = sorted(
        row["event"]
        for row in compatibility.get("event_compatibility", [])
        if row.get("mapping_status") != "mapped"
    )
    pair_rows = compatibility.get("pair_compatibility", [])
    missing_pair_ids = {
        row["id"]
        for row in pair_rows
        if row.get("realizable_lower_path") is not True
    }
    pointer_move_directional = [
        row
        for row in pair_rows
        if row.get("event") == "pointer_move"
        and row.get("to_state")
        in {"gaze_left", "gaze_up", "gaze_right", "gaze_down"}
    ]
    pointer_move_center = [
        row
        for row in pair_rows
        if row.get("event") == "pointer_move"
        and row.get("to_state") == "gaze_center"
    ]
    add_check(
        checks,
        "compatibility_status_exact_no_go",
        compatibility.get("status")
        == "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS",
    )
    add_check(
        checks,
        "compatibility_lower_commit_exact",
        compatibility.get("lower_binding", {}).get("resolved_commit")
        == LOWER_COMMIT,
    )
    add_check(
        checks,
        "compatibility_counts_exact_17_51_8",
        summary.get("events", {}).get("realizable") == 17
        and summary.get("pairs", {}).get("realizable") == 51
        and summary.get("pairs", {}).get("semantic_noop_realizable") == 8,
    )
    add_check(
        checks,
        "polarity_isolated_from_mapping",
        summary.get("polarity_bridge_realizable") is True
        and gap_names == EXPECTED_GAPS
        and missing_pair_ids == EXPECTED_MISSING_PAIRS,
    )
    add_check(
        checks,
        "pointer_move_20_directional_5_center",
        len(pointer_move_directional) == 20
        and all(
            row.get("realizable_lower_path") is True
            for row in pointer_move_directional
        )
        and len(pointer_move_center) == 5
        and all(
            row.get("realizable_lower_path") is False
            for row in pointer_move_center
        ),
    )
    add_check(
        checks,
        "compatibility_external_side_effects_zero",
        side_effects_zero(compatibility),
    )

    add_check(
        checks,
        "joint_exact_no_go_only_full_count_gate",
        joint.get("status") == "NO_GO"
        and joint.get("failed_checks") == ["compatibility.full_21_59_10"]
        and joint.get("compatibility", {}).get("status")
        == "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS",
    )
    add_check(
        checks,
        "joint_external_side_effects_zero",
        side_effects_zero(joint),
    )

    handoff_by_event = {
        row["event"]: row for row in handoff.get("handoffs", [])
    }
    pointer_handoff = handoff_by_event.get("pointer_move", {})
    partition = pointer_handoff.get("pair_partition", {})
    add_check(
        checks,
        "handoff_status_and_four_events",
        handoff.get("status") == "NO_GO_LOWER_HANDOFFS_REQUIRED"
        and set(handoff_by_event) == {
            "pointer_drag_center",
            "pointer_move",
            "early_up_cancel_blur_or_drag",
            "select_ui_assets",
        },
    )
    add_check(
        checks,
        "handoff_exact_pointer_partition",
        partition.get("directional_target_realizable", {}).get("count") == 20
        and partition.get("center_target_missing", {}).get("count") == 5,
    )
    add_check(
        checks,
        "handoff_source_and_frame_contract_complete",
        all(
            row.get("upper_source_locations")
            and row.get("precondition_states")
            and row.get("expected_next_states")
            and row.get("pairs")
            and row.get("why_current_lower_is_unreachable")
            and row.get("minimal_lower_mapping")
            for row in handoff_by_event.values()
        )
        and all(
            pair.get("expected_next_frame_sha256")
            and pair.get("classification")
            for row in handoff_by_event.values()
            for pair in row["pairs"]
        ),
    )
    add_check(
        checks,
        "handoff_external_side_effects_zero",
        side_effects_zero(handoff),
    )

    negative_summary = negative.get("summary", {})
    add_check(
        checks,
        "auditor_negative_result_exact",
        negative.get("status") == "PASS_NEGATIVE_FIXTURES"
        and negative_summary.get("fixture_count") == 8
        and negative_summary.get("fixture_pass_count") == 8
        and negative_summary.get(
            "events_pairs_noops_each_fail_closed"
        )
        is True
        and negative_summary.get("polarity_isolation_pass") is True,
    )
    matrix = negative.get("mutation_fixtures", [])
    add_check(
        checks,
        "auditor_negative_matrix_all_pass",
        len(matrix) == 8
        and all(row.get("pass") is True for row in matrix)
        and negative.get("polarity_isolation", {}).get("pass") is True,
    )
    add_check(
        checks,
        "negative_result_external_side_effects_zero",
        side_effects_zero(negative),
    )

    failed = sorted(name for name, passed in checks.items() if not passed)
    artifact = {
        "schema": "companion.auditor-main-review-provenance.v1",
        "requirements": ["COMP-REQ-477", "COMP-REQ-479", "COMP-REQ-488"],
        "status": (
            "PASS_DETERMINISTIC_PROVENANCE" if not failed else "NO_GO"
        ),
        "scope": "upper_owned_offline_auditor_provenance",
        "identity_bindings": identities,
        "protected_old_artifacts": old_identities,
        "observed_contract": {
            "lower_commit": LOWER_COMMIT,
            "events": "17/21",
            "pairs": "51/59",
            "semantic_noops": "8/10",
            "polarity_bridge": True,
            "handoffs": sorted(handoff_by_event),
            "pointer_move_directional_pairs": 20,
            "pointer_move_missing_center_pairs": 5,
            "missing_pair_ids": sorted(missing_pair_ids),
            "joint_status": "NO_GO",
        },
        "checks": checks,
        "failed_checks": failed,
        "side_effect_counters": {
            "execute": 0,
            "server": 0,
            "browser": 0,
            "prompt": 0,
            "popup": 0,
            "hardware": 0,
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
                "failed_check_count": len(failed),
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
