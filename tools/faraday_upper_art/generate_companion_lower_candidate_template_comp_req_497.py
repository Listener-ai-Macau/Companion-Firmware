#!/usr/bin/env python3
"""Generate the default-off COMP-REQ-497 successor intake template."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


UPPER_BASELINE_COMMIT = "c677deef3d94190e16a08fb83cf45d4bb7d820a5"
LOWER_BASELINE_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
SUCCESSOR_SCHEMA = "companion.comp-req-497.candidate-intake.v1"
VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471/"
    "comp-req-497-candidate-intake"
)
SOURCE_ROLES = (
    "main_dispatch",
    "gaze_controller",
    "hold_cancel_controller",
    "menu_controller",
    "visual_runtime",
)
SIDE_EFFECT_KEYS = (
    "execute",
    "server",
    "browser",
    "prompt",
    "popup",
    "hardware",
    "write",
    "programmer",
    "serial",
    "flash",
    "production",
    "push",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def resolve_inside(repo_root: Path, path: Path) -> Path:
    resolved = (
        path.resolve()
        if path.is_absolute()
        else (repo_root / path).resolve()
    )
    resolved.relative_to(repo_root)
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--intake-runner", type=Path, required=True)
    parser.add_argument("--expected-intake-runner-sha256", required=True)
    parser.add_argument("--compatibility-auditor", type=Path, required=True)
    parser.add_argument(
        "--expected-compatibility-auditor-sha256",
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    intake_runner = resolve_inside(repo_root, args.intake_runner)
    auditor = resolve_inside(repo_root, args.compatibility_auditor)
    output_path = resolve_inside(repo_root, args.output)
    output_path.relative_to((repo_root / VALIDATION_REL).resolve())

    intake_sha = file_sha(intake_runner)
    auditor_sha = file_sha(auditor)
    if intake_sha != args.expected_intake_runner_sha256.upper():
        raise SystemExit("candidate intake runner hash mismatch")
    if auditor_sha != args.expected_compatibility_auditor_sha256.upper():
        raise SystemExit("compatibility auditor hash mismatch")

    intake_rel = intake_runner.relative_to(repo_root).as_posix()
    auditor_rel = auditor.relative_to(repo_root).as_posix()
    output_prefix = VALIDATION_REL.as_posix()
    placeholders = {
        "lower_root": "<LOWER_ROOT>",
        "commit": "<EXACT_40_HEX_SUCCESSOR_COMMIT>",
        "machine_ready": "<EXACT_LOWER_MACHINE_READY_PATH>",
        "machine_ready_sha256": "<EXACT_64_HEX_LOWER_MR_SHA256>",
        "runner_binding": "<RUNNER_REPO_PATH>=<EXACT_COMMITTED_SHA256>",
        "supervisor_binding": (
            "<SUPERVISOR_REPO_PATH>=<EXACT_COMMITTED_SHA256>"
        ),
        "tool_binding": "<TOOL_REPO_PATH>=<EXACT_COMMITTED_SHA256>",
        "result_name": "<SUCCESSOR_COMMIT12>-candidate-intake.json",
        "compatibility_name": (
            "<SUCCESSOR_COMMIT12>-upper-lower-compatibility.json"
        ),
    }
    command = [
        "python",
        "-B",
        intake_rel,
        "--mode",
        "successor",
        "--repo-root",
        ".",
        "--lower-root",
        placeholders["lower_root"],
        "--expected-commit",
        placeholders["commit"],
        "--lower-machine-ready",
        placeholders["machine_ready"],
        "--expected-lower-machine-ready-sha256",
        placeholders["machine_ready_sha256"],
        "--runner-binding",
        placeholders["runner_binding"],
        "--supervisor-binding",
        placeholders["supervisor_binding"],
        "--tool-binding",
        placeholders["tool_binding"],
        "--compatibility-auditor",
        auditor_rel,
        "--expected-compatibility-auditor-sha256",
        auditor_sha,
        "--compatibility-output",
        f"{output_prefix}/{placeholders['compatibility_name']}",
        "--output",
        f"{output_prefix}/{placeholders['result_name']}",
    ]
    candidate_block = {
        "schema": SUCCESSOR_SCHEMA,
        "base_commit": LOWER_BASELINE_COMMIT,
        "source_commit": placeholders["commit"],
        "production_sources": [
            {
                "role": role,
                "path": f"<COMMITTED_PRODUCTION_PATH_FOR_{role.upper()}>",
                "sha256": "<EXACT_COMMITTED_BLOB_CONTENT_SHA256>",
            }
            for role in SOURCE_ROLES
        ],
        "tool_identities": [
            {
                "kind": "runner",
                "path": "<RUNNER_REPO_PATH>",
                "sha256": "<EXACT_COMMITTED_SHA256>",
            },
            {
                "kind": "supervisor",
                "path": "<SUPERVISOR_REPO_PATH>",
                "sha256": "<EXACT_COMMITTED_SHA256>",
            },
            {
                "kind": "tool",
                "path": "<TOOL_REPO_PATH>",
                "sha256": "<EXACT_COMMITTED_SHA256>",
            },
        ],
        "records": {
            "event_records": [],
            "pair_records": [],
            "semantic_noop_records": [],
        },
        "side_effect_counters": {key: 0 for key in SIDE_EFFECT_KEYS},
    }
    artifact = {
        "schema": "companion.comp-req-497.lower-candidate-template.v1",
        "requirements": ["COMP-REQ-497"],
        "status": "PREWIRED_NO_SUCCESSOR_PASS",
        "default_off": True,
        "upper_baseline_commit": UPPER_BASELINE_COMMIT,
        "lower_baseline_commit": LOWER_BASELINE_COMMIT,
        "bindings": {
            "intake_runner": {
                "path": intake_rel,
                "sha256": intake_sha,
            },
            "compatibility_auditor": {
                "path": auditor_rel,
                "sha256": auditor_sha,
            },
        },
        "prewired_command_argv": command,
        "candidate_machine_ready_block_template": candidate_block,
        "operator_actions": [
            "Replace every angle-bracket placeholder with an exact value.",
            (
                "Populate all 21 event, 59 pair, and 10 semantic no-op "
                "records from the candidate's executed production-path trace."
            ),
            (
                "Repeat --tool-binding for every candidate tool identity "
                "declared in candidate_intake.tool_identities."
            ),
            (
                "Run from the Companion-Firmware repository root; the runner "
                "reads lower Git objects and writes only upper validation."
            ),
        ],
        "fail_closed_contract": {
            "empty_record_arrays_cannot_pass": True,
            "lower_head_must_equal_expected_commit": True,
            "tracked_lower_worktree_must_be_clean": True,
            "identities_are_recomputed_from_committed_tree": True,
            "aggregate_totals_are_not_accepted_as_records": True,
            "direct_fixture_event_injection_is_rejected": True,
            "known_4dd_baseline_cannot_be_a_successor": True,
            "successor_pass_is_not_predeclared": True,
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
            "upper_artifact_writes": 1,
        },
        "generator": {
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
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
