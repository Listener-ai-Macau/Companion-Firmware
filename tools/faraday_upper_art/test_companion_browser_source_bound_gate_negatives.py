#!/usr/bin/env python3
"""Deterministic in-memory tamper matrix for the source-bound browser gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def load_gate(tool_path: Path):
    spec = importlib.util.spec_from_file_location("browser_source_bound_gate", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load source-bound gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_overlay(
    repo_root: Path,
    relative_path: str,
    mutate: Callable[[dict[str, Any]], None],
) -> dict[str, bytes]:
    value = json.loads((repo_root / relative_path).read_text(encoding="utf-8"))
    mutate(value)
    return {relative_path: canonical_bytes(value)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--gate-tool", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    gate_tool = (repo_root / args.gate_tool).resolve()
    gate = load_gate(gate_tool)

    replay_path = gate.BOUND_FILES["replay_result"][0]
    pixel_path = gate.BOUND_FILES["pixel_dom_route"][0]
    screenshot_manifest_path = gate.BOUND_FILES["screenshot_manifest"][0]
    ready_path = gate.BOUND_FILES["browser_owner_review_ready"][0]
    replay_tool_path = gate.BOUND_FILES["replay_tool"][0]
    prior_verifier_path = gate.BOUND_FILES["prior_checkonly_verifier"][0]

    screenshot_manifest = json.loads(
        (repo_root / screenshot_manifest_path).read_text(encoding="utf-8")
    )
    first_screenshot = screenshot_manifest["screenshots"][0]["path"]

    fixtures: list[tuple[str, str, dict[str, bytes] | None, str]] = []
    fixtures.append(
        (
            "accepted_page_byte_mutation",
            gate.CANDIDATE_COMMIT,
            {gate.PAGE_PATH: (repo_root / gate.PAGE_PATH).read_bytes() + b"\n"},
            "bound file SHA mismatch: accepted_page",
        )
    )
    fixtures.append(
        (
            "replay_tool_byte_mutation",
            gate.CANDIDATE_COMMIT,
            {replay_tool_path: (repo_root / replay_tool_path).read_bytes() + b"\n"},
            "bound file SHA mismatch: replay_tool",
        )
    )
    fixtures.append(
        (
            "prior_checkonly_verifier_byte_mutation",
            gate.CANDIDATE_COMMIT,
            {prior_verifier_path: (repo_root / prior_verifier_path).read_bytes() + b"\n"},
            "bound file SHA mismatch: prior_checkonly_verifier",
        )
    )
    fixtures.append(
        (
            "replay_result_mutation",
            gate.CANDIDATE_COMMIT,
            json_overlay(
                repo_root,
                replay_path,
                lambda value: value.__setitem__("status", "PASS_FORGED"),
            ),
            "replay status",
        )
    )
    fixtures.append(
        (
            "pixel_dom_route_mutation",
            gate.CANDIDATE_COMMIT,
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["states"][0]["dom"].__setitem__("face_count", 2),
            ),
            "face_count",
        )
    )
    fixtures.append(
        (
            "screenshot_manifest_mutation",
            gate.CANDIDATE_COMMIT,
            json_overlay(
                repo_root,
                screenshot_manifest_path,
                lambda value: value["screenshots"][0].__setitem__(
                    "sha256", "0" * 64
                ),
            ),
            "screenshot SHA mismatch",
        )
    )
    screenshot_bytes = bytearray((repo_root / first_screenshot).read_bytes())
    screenshot_bytes[-1] ^= 0x01
    fixtures.append(
        (
            "screenshot_png_mutation",
            gate.CANDIDATE_COMMIT,
            {first_screenshot: bytes(screenshot_bytes)},
            "screenshot SHA mismatch",
        )
    )
    fixtures.append(
        (
            "ready_artifact_mutation",
            gate.CANDIDATE_COMMIT,
            json_overlay(
                repo_root,
                ready_path,
                lambda value: value.__setitem__("status", "OWNER_PASS_FORGED"),
            ),
            "ready status",
        )
    )
    fixtures.append(
        (
            "stale_candidate_commit",
            "b46db33a52fbad11e75d5d8970d6ccb42c90e1df",
            None,
            "candidate commit argument",
        )
    )
    fixtures.append(
        (
            "second_active_200x200_surface",
            gate.CANDIDATE_COMMIT,
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: (
                    value["invariants"].__setitem__("primary_screen_count", 2),
                    value["states"][0]["dom"].__setitem__("primary_screen_count", 2),
                ),
            ),
            "primary_screen_count",
        )
    )
    fixtures.append(
        (
            "duplicate_pointer_record",
            gate.CANDIDATE_COMMIT,
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["matrix"].append(copy.deepcopy(value["matrix"][0])),
            ),
            "matrix row count",
        )
    )
    fixtures.append(
        (
            "duplicate_route_activation",
            gate.CANDIDATE_COMMIT,
            {
                **json_overlay(
                    repo_root,
                    replay_path,
                    lambda value: value["totals"].__setitem__("route_menu_entries", 7),
                ),
                **json_overlay(
                    repo_root,
                    pixel_path,
                    lambda value: value["matrix"][3]["result"].__setitem__(
                        "menu_entries", 2
                    ),
                ),
            },
            "route_menu_entries",
        )
    )
    for fixture_id, total_key, invariant_key, expected_reason in (
        ("nonzero_http_404", "http_404_count", "http_404_count", "http_404_count"),
        ("nonzero_stale_layer", "stale_layer_count", "stale_layer_count", "stale_layer_count"),
        (
            "nonzero_conflicting_overlap",
            "conflicting_surface_overlap_count",
            "conflicting_surface_overlap_count",
            "conflicting_surface_overlap_count",
        ),
        ("nonzero_out_of_bounds", "out_of_bounds_count", "out_of_bounds_count", "out_of_bounds_count"),
        ("microphone_request", "microphone_requests", "microphone_request_count", "microphone_requests"),
    ):
        fixtures.append(
            (
                fixture_id,
                gate.CANDIDATE_COMMIT,
                {
                    **json_overlay(
                        repo_root,
                        replay_path,
                        lambda value, key=total_key: value["totals"].__setitem__(key, 1),
                    ),
                    **json_overlay(
                        repo_root,
                        pixel_path,
                        lambda value, key=invariant_key: value["invariants"].__setitem__(
                            key, 1
                        ),
                    ),
                },
                expected_reason,
            )
        )

    results = []
    for fixture_id, candidate_commit, overlay, reason_fragment in fixtures:
        outcome = gate.evaluate(repo_root, candidate_commit, overlay)
        reasons = outcome["failed_checks"]
        rejected = outcome["status"] == "NO_GO"
        reason_observed = any(reason_fragment in reason for reason in reasons)
        results.append(
            {
                "id": fixture_id,
                "status": outcome["status"],
                "rejected": rejected,
                "required_reason_fragment": reason_fragment,
                "required_reason_observed": reason_observed,
                "failure_count": len(reasons),
                "failures_sha256": sha256_bytes(canonical_bytes(reasons)),
                "pass": rejected and reason_observed,
            }
        )

    passed = all(result["pass"] for result in results)
    artifact = {
        "schema": "companion.browser-source-bound-negative-matrix.v1",
        "requirements": ["COMP-REQ-471", "COMP-REQ-504"],
        "status": "PASS_ALL_TAMPERS_FAIL_CLOSED" if passed else "NO_GO",
        "candidate_commit": gate.CANDIDATE_COMMIT,
        "gate_tool": {
            "path": Path(args.gate_tool).as_posix(),
            "sha256": sha256_bytes(gate_tool.read_bytes()),
        },
        "fixture_count": len(results),
        "passed_count": sum(1 for result in results if result["pass"]),
        "results": results,
        "real_files_mutated": False,
        "fixture_mode": "in_memory_read_overlay",
        "side_effect_counters": {
            "server_start": 0,
            "browser_start": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
            "real_accepted_file_write": 0,
            "evidence_artifact_write": 1,
        },
    }
    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(artifact["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
