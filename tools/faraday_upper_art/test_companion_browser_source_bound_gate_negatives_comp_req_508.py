#!/usr/bin/env python3
"""Deterministic in-memory tamper matrix for the COMP-REQ-508 source gate."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import verify_companion_browser_source_bound_gate_comp_req_508 as gate


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json(repo_root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def json_overlay(
    repo_root: Path,
    relative_path: str,
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, bytes]:
    value = load_json(repo_root, relative_path)
    mutation(value)
    return {relative_path: canonical_bytes(value)}


def mutate_page(data: bytes) -> bytes:
    return data.replace(b"touchSetGaze", b"touchSetGazX", 1)


def wrong_commit(value: str) -> str:
    return value[:-1] + ("0" if value[-1] != "0" else "1")


def mutate_recording_result(
    value: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    row = next(
        item for item in value["matrix"]
        if item["id"].endswith("-recording-return")
    )
    mutation(row["result"])


def mutate_recording_state(
    value: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    row = next(
        item for item in value["states"]
        if item["contract"]["mode"] == "recording"
    )
    mutation(row)


def run_case(
    repo_root: Path,
    case_id: str,
    overlay: dict[str, bytes] | None = None,
    source_commit: str = gate.SOURCE_COMMIT,
    evidence_commit: str = gate.EVIDENCE_COMMIT,
) -> dict[str, Any]:
    result = gate.evaluate(
        repo_root,
        source_commit,
        evidence_commit,
        overlay,
    )
    return {
        "failed_check_count": len(result["failed_checks"]),
        "id": case_id,
        "rejected": result["status"] == "NO_GO",
        "sample_failures": result["failed_checks"][:4],
        "status": result["status"],
    }


def build(repo_root: Path) -> dict[str, Any]:
    pixel_path = f"{gate.VALIDATION_DIR}/pixel-dom-route-artifact.json"
    replay_path = f"{gate.VALIDATION_DIR}/browser-replay-result.json"
    manifest_path = f"{gate.VALIDATION_DIR}/screenshot-manifest.json"
    after_path = f"{gate.VALIDATION_DIR}/after-fix/stale-gaze-oracle.json"
    before_path = f"{gate.VALIDATION_DIR}/before-fix/stale-gaze-oracle.json"
    determinism_path = f"{gate.VALIDATION_DIR}/clean-replay-determinism.json"
    replay_tool_path = gate.BOUND_FILES["replay_tool"][0]
    first_screenshot = load_json(repo_root, manifest_path)["screenshots"][0]["path"]
    cases: list[dict[str, Any]] = []
    cases.append(
        run_case(
            repo_root,
            "page_source_drift",
            {
                gate.PAGE_PATH: mutate_page(
                    (repo_root / gate.PAGE_PATH).read_bytes()
                )
            },
        )
    )
    cases.append(
        run_case(
            repo_root,
            "replay_tool_drift",
            {
                replay_tool_path: (
                    repo_root / replay_tool_path
                ).read_bytes() + b"\n"
            },
        )
    )
    cases.append(
        run_case(
            repo_root,
            "stale_source_commit",
            source_commit=wrong_commit(gate.SOURCE_COMMIT),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "stale_evidence_commit",
            evidence_commit=wrong_commit(gate.EVIDENCE_COMMIT),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "second_active_200x200",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["invariants"].__setitem__(
                    "primary_screen_count", 2
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "duplicate_pointer_record",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["matrix"].__setitem__(
                    1, copy.deepcopy(value["matrix"][0])
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "duplicate_route_document",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["matrix"][0].__setitem__(
                    "document_requests", 2
                ),
            ),
        )
    )
    for case_id, key in (
        ("http_404_nonzero", "http_404_count"),
        ("stale_layer_nonzero", "stale_layer_count"),
        ("overlap_nonzero", "conflicting_surface_overlap_count"),
        ("microphone_request_nonzero", "microphone_requests"),
        ("stale_pupil_total_nonzero", "stale_pupil_pixel_count"),
        ("microphone_glyph_pixel_nonzero", "mic_glyph_pixel_count"),
        ("recording_exit_total_forged", "route_recording_exits"),
    ):
        cases.append(
            run_case(
                repo_root,
                case_id,
                json_overlay(
                    repo_root,
                    replay_path,
                    lambda value, key=key: value["totals"].__setitem__(key, 1),
                ),
            )
        )
    cases.append(
        run_case(
            repo_root,
            "state_stale_pupil_left",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["states"][0]["pupil_oracle"].__setitem__(
                    "stale_center_mask_left_eye", 1
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "runtime_url_drift",
            json_overlay(
                repo_root,
                replay_path,
                lambda value: value["page"].__setitem__(
                    "runtime_url",
                    "http://127.0.0.1:4174/wrong",
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "recording_phase_order_drift",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: mutate_recording_result(
                    value,
                    lambda result: result.__setitem__(
                        "ordered_phases",
                        ["expression", "thoughtful_listening", "listening"],
                    ),
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "inward_wave_centroid_reversed",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: mutate_recording_result(
                    value,
                    lambda result: result["inward_wave_cycle"].reverse(),
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "recording_mic_mask_overlap",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: mutate_recording_state(
                    value,
                    lambda state: state["microphone_oracle"].__setitem__(
                        "current_wave_mask_overlap",
                        1,
                    ),
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "duplicate_interaction_event_id",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: mutate_recording_state(
                    value,
                    lambda state: state["events"]["event_ids"].append(
                        state["events"]["event_ids"][0]
                    ),
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "after_oracle_forged_stale",
            json_overlay(
                repo_root,
                after_path,
                lambda value: value["measurement"]["pixel"].__setitem__(
                    "stale_center_mask_total", 1
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "before_negative_erased",
            json_overlay(
                repo_root,
                before_path,
                lambda value: value.__setitem__("status", "PASS"),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "screenshot_manifest_duplicate",
            json_overlay(
                repo_root,
                manifest_path,
                lambda value: value["screenshots"].__setitem__(
                    1, copy.deepcopy(value["screenshots"][0])
                ),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "screenshot_pixel_drift",
            {
                first_screenshot: (
                    repo_root / first_screenshot
                ).read_bytes()[:-1] + b"\x00"
            },
        )
    )
    cases.append(
        run_case(
            repo_root,
            "determinism_false",
            json_overlay(
                repo_root,
                determinism_path,
                lambda value: value.__setitem__("byte_identical", False),
            ),
        )
    )
    cases.append(
        run_case(
            repo_root,
            "new_owner_result_preexists",
            {gate.NEW_OWNER_RESULT: b'{"selected":"through"}\n'},
        )
    )
    cases.append(
        run_case(
            repo_root,
            "prior_owner_failure_drift",
            json_overlay(
                repo_root,
                gate.BOUND_FILES["failed_owner_result"][0],
                lambda value: value.__setitem__("selected", "through"),
            ),
        )
    )
    baseline = gate.evaluate(
        repo_root,
        gate.SOURCE_COMMIT,
        gate.EVIDENCE_COMMIT,
    )
    passed = (
        baseline["status"] == "BROWSER_OWNER_REVIEW_READY_SUCCESSOR"
        and len(cases) >= 20
        and all(case["rejected"] for case in cases)
    )
    return {
        "baseline_status": baseline["status"],
        "cases": cases,
        "negative_count": len(cases),
        "rejected_count": sum(case["rejected"] for case in cases),
        "requirements": [
            "COMP-REQ-504",
            "COMP-REQ-507",
            "COMP-REQ-508",
            "COMP-REQ-509",
            "COMP-REQ-510",
        ],
        "schema": "companion.browser-source-bound-negative-matrix.v3",
        "side_effect_counters": {
            "browser": 0,
            "hardware": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
            "popup": 0,
            "process": 0,
            "server_start": 0,
        },
        "status": "PASS" if passed else "NO_GO",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    result = build(repo_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "artifact_sha256": sha256_bytes(output.read_bytes()),
                "negative_count": result["negative_count"],
                "status": result["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
