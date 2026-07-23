#!/usr/bin/env python3
"""Focused deterministic fixtures for the COMP-REQ-497 candidate intake."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471/"
    "comp-req-497-candidate-intake"
)
BASELINE_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
BASELINE_MR_SHA = (
    "8BD2C5F3F9CEFD4794DEC29C6C244A66C0A7F99D495E9A221465019C355FB04F"
)
REJECTED_C250_COMMIT = "c250436e2cc3fcc8d706363fc33fc666f76dbefa"
REJECTED_C250_MR_SHA = (
    "0003E26B56CA55ED257B56C12821F11B5BEC3A06063DE87ABB32F6C808B2D0A1"
)
BASELINE_RUNNER = (
    "tools/run_wb55_ssd1681_r7_locked_v9.ps1="
    "890DCB397AA10B1E09A2B7BC1616134BF9EF3076CDDBE95D178862A7CA369FA4"
)
BASELINE_SUPERVISOR = (
    "tools/supervise_wb55_ssd1681_r7_locked_v9.ps1="
    "91F2D42F50530BE53834D8D8CFF056B7A3D9C8AB51BFD74817D0D13812876F9E"
)
BASELINE_TOOL = (
    "tools/verify_comp_req_472_visual_runtime.py="
    "0B08F7444ACA3D67782FCE19F3B135AD7255120555A1F8812DE7C3C486D2DF0D"
)


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


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("candidate_intake", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load candidate intake module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--intake-runner", type=Path, required=True)
    parser.add_argument("--expected-intake-runner-sha256", required=True)
    parser.add_argument("--lower-root", type=Path, required=True)
    parser.add_argument("--baseline-machine-ready", type=Path, required=True)
    parser.add_argument(
        "--expected-baseline-machine-ready-sha256",
        default=BASELINE_MR_SHA,
    )
    parser.add_argument("--rejected-machine-ready", type=Path, required=True)
    parser.add_argument(
        "--expected-rejected-machine-ready-sha256",
        default=REJECTED_C250_MR_SHA,
    )
    parser.add_argument("--compatibility-auditor", type=Path, required=True)
    parser.add_argument(
        "--expected-compatibility-auditor-sha256",
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    intake_runner = (
        args.intake_runner.resolve()
        if args.intake_runner.is_absolute()
        else (repo_root / args.intake_runner).resolve()
    )
    lower_root = args.lower_root.resolve()
    baseline_mr = args.baseline_machine_ready.resolve()
    rejected_mr = args.rejected_machine_ready.resolve()
    auditor = (
        args.compatibility_auditor.resolve()
        if args.compatibility_auditor.is_absolute()
        else (repo_root / args.compatibility_auditor).resolve()
    )
    output_path = (
        args.output.resolve()
        if args.output.is_absolute()
        else (repo_root / args.output).resolve()
    )
    validation_root = (repo_root / VALIDATION_REL).resolve()
    output_path.relative_to(validation_root)
    if file_sha(intake_runner) != args.expected_intake_runner_sha256.upper():
        raise SystemExit("candidate intake runner hash mismatch")
    if (
        file_sha(auditor)
        != args.expected_compatibility_auditor_sha256.upper()
    ):
        raise SystemExit("compatibility auditor hash mismatch")
    if (
        file_sha(baseline_mr)
        != args.expected_baseline_machine_ready_sha256.upper()
    ):
        raise SystemExit("baseline MACHINE_READY hash mismatch")
    if (
        file_sha(rejected_mr)
        != args.expected_rejected_machine_ready_sha256.upper()
    ):
        raise SystemExit("rejected MACHINE_READY hash mismatch")

    module = load_module(intake_runner)
    baseline_compatibility = (
        validation_root
        / "upper-lower-compatibility-comp-req-497-baseline-4dd.json"
    )
    baseline_result = validation_root / "baseline-4dd-intake.json"
    command = [
        sys.executable,
        "-B",
        str(intake_runner),
        "--mode",
        "baseline-no-go",
        "--repo-root",
        str(repo_root),
        "--lower-root",
        str(lower_root),
        "--expected-commit",
        BASELINE_COMMIT,
        "--lower-machine-ready",
        str(baseline_mr),
        "--expected-lower-machine-ready-sha256",
        args.expected_baseline_machine_ready_sha256.upper(),
        "--runner-binding",
        BASELINE_RUNNER,
        "--supervisor-binding",
        BASELINE_SUPERVISOR,
        "--tool-binding",
        BASELINE_TOOL,
        "--compatibility-auditor",
        str(auditor),
        "--expected-compatibility-auditor-sha256",
        args.expected_compatibility_auditor_sha256.upper(),
        "--compatibility-output",
        str(baseline_compatibility),
        "--output",
        str(baseline_result),
    ]
    baseline_runs = []
    for _ in range(2):
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        artifact = load_json(baseline_result)
        compatibility = load_json(baseline_compatibility)
        baseline_runs.append(
            {
                "return_code": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "result_sha256": file_sha(baseline_result),
                "compatibility_sha256": file_sha(baseline_compatibility),
                "status": artifact.get("status"),
                "failed_checks": artifact.get("failed_checks"),
                "counts": {
                    "events": compatibility.get("summary", {})
                    .get("events", {})
                    .get("realizable"),
                    "pairs": compatibility.get("summary", {})
                    .get("pairs", {})
                    .get("realizable"),
                    "semantic_noops": compatibility.get("summary", {})
                    .get("pairs", {})
                    .get("semantic_noop_realizable"),
                },
                "mr_tool_claims_not_promoted": artifact.get("checks", {}).get(
                    "baseline_mr_tool_claims_not_promoted"
                ),
            }
        )
    baseline_positive_pass = bool(
        baseline_runs[0] == baseline_runs[1]
        and all(row["return_code"] == 0 for row in baseline_runs)
        and all(
            row["status"] == "BASELINE_NO_GO_VERIFIED"
            for row in baseline_runs
        )
        and all(not row["failed_checks"] for row in baseline_runs)
        and all(
            row["counts"]
            == {"events": 17, "pairs": 51, "semantic_noops": 8}
            for row in baseline_runs
        )
        and all(
            row["mr_tool_claims_not_promoted"] is True
            for row in baseline_runs
        )
    )

    control = {
        name: True for name in module.successor_gate_checks({})
    }
    mutation_specs = [
        ("stale_4dd_commit", "successor_not_baseline"),
        ("stale_4dd_machine_ready", "successor_mr_not_baseline"),
        (
            "stale_4dd_upper_artifact",
            "successor_has_no_stale_upper_hash",
        ),
        ("dirty_worktree_mapping", "lower_worktree_clean"),
        ("uncommitted_only_mapping", "lower_head_exact"),
        ("machine_ready_hash_drift", "mr_hash_exact"),
        ("machine_ready_source_commit_drift", "mr_source_commit_exact"),
        ("machine_ready_schema_drift", "mr_schema_exact"),
        ("runner_identity_drift", "runner_identity_exact"),
        ("supervisor_identity_drift", "supervisor_identity_exact"),
        ("tool_identity_drift", "tool_identities_exact"),
        ("tool_identity_undeclared", "tool_identities_declared"),
        ("source_role_missing", "source_roles_complete"),
        ("source_blob_wrong", "source_blobs_exact"),
        ("production_source_unchanged", "production_source_changed"),
        (
            "direct_fixture_event_injection",
            "direct_fixture_injection_absent",
        ),
        ("claimed_aggregate_totals", "aggregate_claims_absent"),
        ("event_record_mismatch", "event_records_exact"),
        ("pair_record_mismatch", "pair_records_exact"),
        ("semantic_noop_record_mismatch", "noop_records_exact"),
        ("compatibility_commit_drift", "compatibility_commit_exact"),
        ("compatibility_status_claim_only", "compatibility_status_pass"),
        ("compatibility_event_gap", "compatibility_events_21"),
        ("compatibility_pair_gap", "compatibility_pairs_59"),
        ("compatibility_noop_gap", "compatibility_noops_10"),
        (
            "compatibility_polarity_or_terminal_gap",
            "compatibility_polarity_terminal_qualification",
        ),
        (
            "compatibility_nonzero_side_effect",
            "compatibility_side_effects_zero",
        ),
        ("machine_ready_nonzero_side_effect", "mr_side_effects_zero"),
        ("upper_baseline_drift", "upper_baseline_exact"),
        ("lower_commit_object_drift", "lower_commit_exact"),
    ]
    matrix = []
    control_checks = module.successor_gate_checks(control)
    matrix.append(
        {
            "id": "control_all_required_observations",
            "mutated_check": None,
            "expected_ready": True,
            "observed_ready": all(control_checks.values()),
            "pass": all(control_checks.values()),
        }
    )
    for fixture_id, check_name in mutation_specs:
        observed = dict(control)
        observed[check_name] = False
        gate = module.successor_gate_checks(observed)
        ready = all(gate.values())
        matrix.append(
            {
                "id": fixture_id,
                "mutated_check": check_name,
                "expected_ready": False,
                "observed_ready": ready,
                "failed_checks": sorted(
                    name for name, passed in gate.items() if not passed
                ),
                "pass": not ready and gate.get(check_name) is False,
            }
        )

    lower_git = module.GitReader(lower_root)
    rejected_injections = module.changed_fixture_injections(
        lower_git,
        BASELINE_COMMIT,
        REJECTED_C250_COMMIT,
    )
    c250_injection_pass = bool(
        any(
            row["path"] == "tools/comp_req_494_visual_touch_trace.c"
            and "COMPANION_VISUAL_EVENT_POINTER_DRAG_CENTER"
            in row["event_tokens"]
            and "COMPANION_VISUAL_EVENT_EARLY_UP_CANCEL_BLUR_OR_DRAG"
            in row["event_tokens"]
            for row in rejected_injections
        )
    )
    rejected_claims = module.aggregate_claims(load_json(rejected_mr))
    c250_aggregate_pass = bool(
        {row["reason"] for row in rejected_claims}
        >= {
            "forbidden_aggregate_key",
            "forbidden_aggregate_token:21/21",
            "forbidden_aggregate_token:59/59",
            "forbidden_aggregate_token:10/10",
        }
    )

    all_pass = bool(
        baseline_positive_pass
        and all(row["pass"] for row in matrix)
        and c250_injection_pass
        and c250_aggregate_pass
    )
    artifact = {
        "schema": "companion.comp-req-497.candidate-intake-fixtures.v1",
        "requirements": ["COMP-REQ-494", "COMP-REQ-497"],
        "status": (
            "PASS_CANDIDATE_INTAKE_FIXTURES" if all_pass else "NO_GO"
        ),
        "bindings": {
            "intake_runner": {
                "path": intake_runner.relative_to(repo_root).as_posix(),
                "sha256": file_sha(intake_runner),
            },
            "compatibility_auditor": {
                "path": auditor.relative_to(repo_root).as_posix(),
                "sha256": file_sha(auditor),
            },
            "baseline_machine_ready": {
                "path": baseline_mr.as_posix(),
                "sha256": file_sha(baseline_mr),
            },
            "rejected_c250_machine_ready": {
                "path": rejected_mr.as_posix(),
                "sha256": file_sha(rejected_mr),
            },
        },
        "positive_fixture": {
            "id": "known_4dd_truthful_no_go",
            "status": "PASS" if baseline_positive_pass else "NO_GO",
            "expected_disposition": "BASELINE_NO_GO_VERIFIED",
            "expected_counts": {
                "events": 17,
                "pairs": 51,
                "semantic_noops": 8,
            },
            "runs": baseline_runs,
        },
        "negative_tamper_matrix": {
            "fixture_count": len(matrix),
            "pass_count": sum(row["pass"] for row in matrix),
            "fixtures": matrix,
        },
        "known_rejected_c250_diagnostic": {
            "commit": REJECTED_C250_COMMIT,
            "direct_fixture_injection_detected": c250_injection_pass,
            "injections": rejected_injections,
            "aggregate_claim_detection_pass": c250_aggregate_pass,
            "aggregate_claims": rejected_claims,
            "successor_ready_claimed": False,
        },
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
            "read_only_baseline_intake_processes": 2,
            "read_only_git_processes": lower_git.command_count,
            "upper_artifact_writes": 1,
        },
        "validator": {
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
                "baseline_positive": baseline_positive_pass,
                "negative_fixtures": (
                    f"{artifact['negative_tamper_matrix']['pass_count']}/"
                    f"{artifact['negative_tamper_matrix']['fixture_count']}"
                ),
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
