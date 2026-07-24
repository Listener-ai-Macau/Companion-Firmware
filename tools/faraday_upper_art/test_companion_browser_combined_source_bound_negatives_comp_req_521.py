#!/usr/bin/env python3
"""Deterministic in-memory tamper matrix for the COMP-REQ-521 browser gate."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import verify_companion_browser_combined_source_bound_comp_req_521 as gate


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


def wrong_commit(value: str) -> str:
    return value[:-1] + ("0" if value[-1] != "0" else "1")


def run_case(
    repo_root: Path,
    case_id: str,
    overlay: dict[str, bytes] | None = None,
    source_commit: str = gate.SOURCE_COMMIT,
    tool_commit: str = gate.TOOL_COMMIT,
) -> dict[str, Any]:
    result = gate.evaluate(
        repo_root,
        overlay=overlay,
        source_commit=source_commit,
        tool_commit=tool_commit,
    )
    return {
        "failed_check_count": len(result["failed_checks"]),
        "id": case_id,
        "rejected": result["status"] == "NO_GO",
        "sample_failures": result["failed_checks"][:5],
        "status": result["status"],
    }


def mutate_recording_result(
    value: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    row = next(
        item for item in value["matrix"]
        if item["id"].endswith("-recording-return")
    )
    mutation(row["result"])


def build(repo_root: Path) -> dict[str, Any]:
    replay_path = gate.BOUND_FILES["replay_result"][0]
    pixel_path = gate.BOUND_FILES["pixel_dom_route"][0]
    manifest_path = gate.BOUND_FILES["screenshot_manifest"][0]
    natural_path = gate.BOUND_FILES["focused_natural"][0]
    recording_path = gate.BOUND_FILES["focused_recording"][0]
    determinism_path = gate.BOUND_FILES["determinism_receipt"][0]
    replay_tool_path = gate.BOUND_FILES["replay_tool"][0]
    first_screenshot = load_json(
        repo_root, manifest_path
    )["screenshots"][0]["path"]

    cases = [
        run_case(repo_root, "clean"),
        run_case(
            repo_root,
            "page_source_drift",
            {
                gate.PAGE_PATH: (
                    repo_root / gate.PAGE_PATH
                ).read_bytes().replace(b"naturalState", b"naturalStXte", 1)
            },
        ),
        run_case(
            repo_root,
            "replay_tool_drift",
            {
                replay_tool_path: (
                    repo_root / replay_tool_path
                ).read_bytes() + b"\n"
            },
        ),
        run_case(
            repo_root,
            "stale_source_commit",
            source_commit=wrong_commit(gate.SOURCE_COMMIT),
        ),
        run_case(
            repo_root,
            "stale_tool_commit",
            tool_commit=wrong_commit(gate.TOOL_COMMIT),
        ),
        run_case(
            repo_root,
            "forged_aggregate_totals",
            json_overlay(
                repo_root,
                replay_path,
                lambda value: value["totals"].__setitem__(
                    "natural_bridge_commits", 7
                ),
            ),
        ),
        run_case(
            repo_root,
            "duplicate_matrix_record",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["matrix"].__setitem__(
                    1, copy.deepcopy(value["matrix"][0])
                ),
            ),
        ),
        run_case(
            repo_root,
            "stale_pupil_pixel",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: value["states"][0]["pupil_oracle"].__setitem__(
                    "stale_center_mask_left_eye", 1
                ),
            ),
        ),
        run_case(
            repo_root,
            "recording_indicator_missing",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: next(
                    row for row in value["states"]
                    if row["contract"]["mode"] == "recording"
                )["dom"].__setitem__("recording_indicator_count", 0),
            ),
        ),
        run_case(
            repo_root,
            "microphone_request_nonzero",
            json_overlay(
                repo_root,
                replay_path,
                lambda value: value["totals"].__setitem__(
                    "microphone_requests", 1
                ),
            ),
        ),
        run_case(
            repo_root,
            "natural_discriminator_drift",
            json_overlay(
                repo_root,
                natural_path,
                lambda value: value["observations"]["contract"]["contract"]
                .__setitem__("tapDiscriminatorMs", 649),
            ),
        ),
        run_case(
            repo_root,
            "natural_priority_drift",
            json_overlay(
                repo_root,
                natural_path,
                lambda value: value["observations"]["contract"]["contract"]
                ["priority"].reverse(),
            ),
        ),
        run_case(
            repo_root,
            "recording_thoughtful_injected",
            json_overlay(
                repo_root,
                recording_path,
                lambda value: value["observation"]["phase_trace"].__setitem__(
                    2, "thoughtful_listening"
                ),
            ),
        ),
        run_case(
            repo_root,
            "recording_outward_wrap",
            json_overlay(
                repo_root,
                recording_path,
                lambda value: value["observation"]["outward_transitions"].append(
                    {"from": 8, "to": 36}
                ),
            ),
        ),
        run_case(
            repo_root,
            "recording_matrix_wave_reversed",
            json_overlay(
                repo_root,
                pixel_path,
                lambda value: mutate_recording_result(
                    value,
                    lambda result: result["inward_wave_cycle"].reverse(),
                ),
            ),
        ),
        run_case(
            repo_root,
            "determinism_false",
            json_overlay(
                repo_root,
                determinism_path,
                lambda value: value.__setitem__("byte_identical", False),
            ),
        ),
        run_case(
            repo_root,
            "runtime_url_drift",
            json_overlay(
                repo_root,
                replay_path,
                lambda value: value["page"].__setitem__(
                    "runtime_url", "http://127.0.0.1:4174/wrong"
                ),
            ),
        ),
        run_case(
            repo_root,
            "screenshot_payload_drift",
            {
                first_screenshot: (
                    repo_root / first_screenshot
                ).read_bytes() + b"\x00"
            },
        ),
        run_case(
            repo_root,
            "screenshot_manifest_drift",
            json_overlay(
                repo_root,
                manifest_path,
                lambda value: value["screenshots"][0].__setitem__(
                    "bytes", value["screenshots"][0]["bytes"] + 1
                ),
            ),
        ),
        run_case(
            repo_root,
            "successor_owner_result_preexists",
            {gate.OWNER_RESULT_PATH: b'{"selected":"failure"}\n'},
        ),
    ]
    clean = cases[0]
    negative_cases = cases[1:]
    pass_condition = (
        clean["status"] == "MACHINE_READY"
        and all(item["rejected"] for item in negative_cases)
    )
    return {
        "cases": cases,
        "clean_status": clean["status"],
        "negative_case_count": len(negative_cases),
        "rejected_negative_count": sum(
            item["rejected"] for item in negative_cases
        ),
        "requirements": ["COMP-REQ-518", "COMP-REQ-520", "COMP-REQ-521"],
        "schema": "companion.browser-combined-source-bound-negatives.v1",
        "side_effect_counters": {
            "browser": 0,
            "hardware": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
            "server_start": 0,
        },
        "status": "PASS" if pass_condition else "NO_GO",
    }


def main() -> int:
    repo_root = Path.cwd().resolve()
    output = repo_root / gate.VALIDATION_DIR / "source-bound-negatives.json"
    result = build(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(result)
    output.write_bytes(payload)
    print(json.dumps({
        "artifact_sha256": sha256_bytes(payload),
        "negative_case_count": result["negative_case_count"],
        "rejected_negative_count": result["rejected_negative_count"],
        "status": result["status"],
    }, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
