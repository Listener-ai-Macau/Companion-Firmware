#!/usr/bin/env python3
"""Fail-closed provenance verifier for the COMP-REQ-497 intake bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


UPPER_BASELINE_COMMIT = "c677deef3d94190e16a08fb83cf45d4bb7d820a5"
LOWER_BASELINE_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471/"
    "comp-req-497-candidate-intake"
)
ZERO_SIDE_EFFECT_KEYS = (
    "execute",
    "server",
    "browser",
    "prompt",
    "popup",
    "hardware",
    "lower_write",
    "registry_write",
    "platform_write",
    "production_write",
    "push",
)
COMPATIBILITY_ZERO_SIDE_EFFECT_KEYS = (
    "operator_execute",
    "server_probe",
    "server_start",
    "browser_start",
    "popup",
    "operator_prompt",
    "hardware",
    "lower_write",
    "platform_write",
    "production_write",
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


def resolve_inside(repo_root: Path, path: Path) -> Path:
    resolved = (
        path.resolve()
        if path.is_absolute()
        else (repo_root / path).resolve()
    )
    resolved.relative_to(repo_root)
    return resolved


def side_effects_zero(value: Any, required_keys: tuple[str, ...]) -> bool:
    return bool(
        isinstance(value, dict)
        and set(value) >= set(required_keys)
        and all(value.get(key) == 0 for key in required_keys)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--intake-runner", type=Path, required=True)
    parser.add_argument("--expected-intake-runner-sha256", required=True)
    parser.add_argument("--fixture-validator", type=Path, required=True)
    parser.add_argument("--expected-fixture-validator-sha256", required=True)
    parser.add_argument("--template-generator", type=Path, required=True)
    parser.add_argument("--expected-template-generator-sha256", required=True)
    parser.add_argument("--baseline-intake", type=Path, required=True)
    parser.add_argument("--expected-baseline-intake-sha256", required=True)
    parser.add_argument("--baseline-compatibility", type=Path, required=True)
    parser.add_argument(
        "--expected-baseline-compatibility-sha256",
        required=True,
    )
    parser.add_argument("--fixture-result", type=Path, required=True)
    parser.add_argument("--expected-fixture-result-sha256", required=True)
    parser.add_argument("--successor-template", type=Path, required=True)
    parser.add_argument("--expected-successor-template-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    validation_root = (repo_root / VALIDATION_REL).resolve()
    path_specs = {
        "intake_runner": (
            resolve_inside(repo_root, args.intake_runner),
            args.expected_intake_runner_sha256,
        ),
        "fixture_validator": (
            resolve_inside(repo_root, args.fixture_validator),
            args.expected_fixture_validator_sha256,
        ),
        "template_generator": (
            resolve_inside(repo_root, args.template_generator),
            args.expected_template_generator_sha256,
        ),
        "baseline_intake": (
            resolve_inside(repo_root, args.baseline_intake),
            args.expected_baseline_intake_sha256,
        ),
        "baseline_compatibility": (
            resolve_inside(repo_root, args.baseline_compatibility),
            args.expected_baseline_compatibility_sha256,
        ),
        "fixture_result": (
            resolve_inside(repo_root, args.fixture_result),
            args.expected_fixture_result_sha256,
        ),
        "successor_template": (
            resolve_inside(repo_root, args.successor_template),
            args.expected_successor_template_sha256,
        ),
    }
    output_path = resolve_inside(repo_root, args.output)
    output_path.relative_to(validation_root)

    identities = []
    for name, (path, expected) in path_specs.items():
        observed = file_sha(path) if path.is_file() else None
        identities.append(
            {
                "name": name,
                "path": path.relative_to(repo_root).as_posix(),
                "expected_sha256": expected.upper(),
                "observed_sha256": observed,
                "match": observed == expected.upper(),
            }
        )

    baseline = load_json(path_specs["baseline_intake"][0])
    compatibility = load_json(path_specs["baseline_compatibility"][0])
    fixtures = load_json(path_specs["fixture_result"][0])
    template = load_json(path_specs["successor_template"][0])
    try:
        observed_commit = subprocess.run(
            ["git", "rev-parse", f"{UPPER_BASELINE_COMMIT}^{{commit}}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        observed_commit = None

    summary = compatibility.get("summary", {})
    matrix = fixtures.get("negative_tamper_matrix", {})
    fixture_rows = matrix.get("fixtures", [])
    positive_runs = (
        fixtures.get("positive_fixture", {}).get("runs", [])
    )
    command = template.get("prewired_command_argv", [])
    command_text = "\n".join(str(value) for value in command)
    template_block = template.get("candidate_machine_ready_block_template", {})
    known_inputs = {
        path.resolve()
        for path, _ in path_specs.values()
    }
    known_inputs.add(output_path)
    unexpected_successor_passes = []
    for candidate in sorted(validation_root.glob("*.json")):
        if candidate.resolve() in known_inputs:
            continue
        try:
            value = load_json(candidate)
        except Exception:
            continue
        if value.get("status") in {
            "SUCCESSOR_INTAKE_READY",
            "JOINT_READY",
        }:
            unexpected_successor_passes.append(
                {
                    "path": candidate.relative_to(repo_root).as_posix(),
                    "sha256": file_sha(candidate),
                    "status": value.get("status"),
                }
            )

    checks = {
        "all_input_identities_exact": all(
            row["match"] for row in identities
        ),
        "upper_baseline_commit_resolves_exact": (
            observed_commit == UPPER_BASELINE_COMMIT
        ),
        "baseline_is_truthful_4dd_no_go": bool(
            baseline.get("status") == "BASELINE_NO_GO_VERIFIED"
            and baseline.get("mode") == "baseline-no-go"
            and baseline.get("lower_binding", {}).get("expected_commit")
            == LOWER_BASELINE_COMMIT
            and not baseline.get("failed_checks")
            and baseline.get("checks", {}).get(
                "baseline_mr_tool_claims_not_promoted"
            )
            is True
        ),
        "compatibility_is_17_51_8_no_go": bool(
            compatibility.get("status")
            == "NO_GO_UPPER_LOWER_EVENT_PATH_GAPS"
            and summary.get("events", {}).get("realizable") == 17
            and summary.get("pairs", {}).get("realizable") == 51
            and summary.get("pairs", {}).get(
                "semantic_noop_realizable"
            )
            == 8
            and summary.get("polarity_bridge_realizable") is True
        ),
        "baseline_double_run_byte_stable": bool(
            len(positive_runs) == 2
            and positive_runs[0] == positive_runs[1]
        ),
        "fixture_matrix_all_pass": bool(
            fixtures.get("status") == "PASS_CANDIDATE_INTAKE_FIXTURES"
            and matrix.get("fixture_count") == len(fixture_rows)
            and matrix.get("pass_count") == len(fixture_rows)
            and len(fixture_rows) >= 31
            and all(row.get("pass") is True for row in fixture_rows)
        ),
        "known_c250_direct_injection_rejected": (
            fixtures.get("known_rejected_c250_diagnostic", {}).get(
                "direct_fixture_injection_detected"
            )
            is True
        ),
        "known_c250_aggregate_claims_rejected": (
            fixtures.get("known_rejected_c250_diagnostic", {}).get(
                "aggregate_claim_detection_pass"
            )
            is True
        ),
        "template_binds_exact_tools_and_placeholders": bool(
            template.get("status") == "PREWIRED_NO_SUCCESSOR_PASS"
            and template.get("upper_baseline_commit")
            == UPPER_BASELINE_COMMIT
            and template.get("bindings", {}).get(
                "intake_runner", {}
            ).get("sha256")
            == path_specs["intake_runner"][1].upper()
            and "--runner-binding" in command
            and "--supervisor-binding" in command
            and "--tool-binding" in command
            and "<EXACT_40_HEX_SUCCESSOR_COMMIT>" in command_text
            and "<EXACT_64_HEX_LOWER_MR_SHA256>" in command_text
        ),
        "template_records_are_not_fabricated": bool(
            template_block.get("records")
            == {
                "event_records": [],
                "pair_records": [],
                "semantic_noop_records": [],
            }
            and template.get("fail_closed_contract", {}).get(
                "empty_record_arrays_cannot_pass"
            )
            is True
        ),
        "all_bound_artifact_side_effects_zero": bool(
            side_effects_zero(
                baseline.get("side_effect_counters"),
                ZERO_SIDE_EFFECT_KEYS,
            )
            and side_effects_zero(
                compatibility.get("side_effect_counters"),
                COMPATIBILITY_ZERO_SIDE_EFFECT_KEYS,
            )
            and side_effects_zero(
                fixtures.get("side_effect_counters"),
                ZERO_SIDE_EFFECT_KEYS,
            )
            and side_effects_zero(
                template.get("side_effect_counters"),
                ZERO_SIDE_EFFECT_KEYS,
            )
        ),
        "no_successor_pass_artifact_present": (
            not unexpected_successor_passes
        ),
    }
    status = (
        "CANDIDATE_INTAKE_READY_NO_SUCCESSOR"
        if all(checks.values())
        else "NO_GO"
    )
    artifact = {
        "schema": "companion.comp-req-497.candidate-intake-ready.v1",
        "requirements": ["COMP-REQ-497"],
        "status": status,
        "default_off": True,
        "upper_baseline_commit": UPPER_BASELINE_COMMIT,
        "identities": identities,
        "checks": checks,
        "failed_checks": sorted(
            name for name, passed in checks.items() if not passed
        ),
        "unexpected_successor_pass_artifacts": unexpected_successor_passes,
        "disposition": {
            "known_4dd_candidate": "DETERMINISTIC_NO_GO_BASELINE",
            "known_c250_candidate": "REJECTED_DIRECT_FIXTURE_AND_TOTALS",
            "successor": "NOT_SUPPLIED_NOT_CLAIMED",
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
            "read_only_git_processes": 1,
            "upper_artifact_writes": 1,
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
                "status": status,
                "failed_checks": artifact["failed_checks"],
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0 if status == "CANDIDATE_INTAKE_READY_NO_SUCCESSOR" else 1


if __name__ == "__main__":
    raise SystemExit(main())
