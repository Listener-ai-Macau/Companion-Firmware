#!/usr/bin/env python3
"""Deterministic tamper matrix for the COMP-REQ-533/534 source-bound gate."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import verify_companion_browser_three_wave_state_view_source_bound_comp_req_533_534 as gate


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def wrong_commit(value: str) -> str:
    return value[:-1] + ("0" if value[-1] != "0" else "1")


def load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def mutate_json(
    root: Path,
    relative: str,
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, bytes]:
    value = load_json(root, relative)
    mutation(value)
    return {relative: canonical_bytes(value)}


def run_case(
    root: Path,
    case_id: str,
    overlay: dict[str, bytes] | None = None,
    source_commit: str = gate.SOURCE_COMMIT,
    tool_commit: str = gate.TOOL_COMMIT,
) -> dict[str, Any]:
    result = gate.evaluate(
        root,
        overlay=overlay,
        source_commit=source_commit,
        tool_commit=tool_commit,
    )
    return {
        "id": case_id,
        "status": result["status"],
        "rejected": result["status"] == "NO_GO",
        "failed_check_count": len(result["failed_checks"]),
        "sample_failures": result["failed_checks"][:4],
    }


def build(root: Path) -> dict[str, Any]:
    after_path = gate.BOUND_FILES["after_oracle"][0]
    before_path = gate.BOUND_FILES["before_oracle"][0]
    replay_path = gate.BOUND_FILES["replay"][0]
    pixel_path = gate.BOUND_FILES["pixel"][0]
    determinism_path = gate.BOUND_FILES["determinism"][0]
    replay_tool_path = gate.BOUND_FILES["replay_tool"][0]
    screenshot_manifest = load_json(
        root, gate.BOUND_FILES["screenshots"][0]
    )
    screenshot_path = screenshot_manifest["screenshots"][0]["path"]

    clean = run_case(root, "clean")
    newline_overlay = {
        gate.PAGE_PATH: (
            root / gate.PAGE_PATH
        ).read_bytes().replace(b"\r\n", b"\n")
    }
    for relative, _, _ in gate.BOUND_FILES.values():
        newline_overlay[relative] = (
            root / relative
        ).read_bytes().replace(b"\r\n", b"\n")
    newline_equivalence = run_case(
        root,
        "canonical_lf_equivalent_checkout",
        newline_overlay,
    )
    negative_cases = [
        run_case(
            root,
            "page_drift",
            {gate.PAGE_PATH: (root / gate.PAGE_PATH).read_bytes() + b"\n"},
        ),
        run_case(
            root,
            "stale_source_commit",
            source_commit=wrong_commit(gate.SOURCE_COMMIT),
        ),
        run_case(
            root,
            "stale_tool_commit",
            tool_commit=wrong_commit(gate.TOOL_COMMIT),
        ),
        run_case(
            root,
            "replay_tool_drift",
            {
                replay_tool_path:
                (root / replay_tool_path).read_bytes() + b"\n"
            },
        ),
        run_case(
            root,
            "forged_before_pass",
            mutate_json(
                root,
                before_path,
                lambda value: value.update(
                    {"status": "PASS", "failed_checks": []}
                ),
            ),
        ),
        run_case(
            root,
            "two_wave_components",
            mutate_json(
                root,
                after_path,
                lambda value: value["observed"]["steps"][0][
                    "components"
                ].pop(),
            ),
        ),
        run_case(
            root,
            "outward_wave_transition",
            mutate_json(
                root,
                after_path,
                lambda value: value["observed"]["identityTransitions"][0]
                .__setitem__("kind", "outward_wrap"),
            ),
        ),
        run_case(
            root,
            "forged_edge_accepted",
            mutate_json(
                root,
                after_path,
                lambda value: value["observed"]["edgeChecks"]["forged"][0]
                .__setitem__("allowed", True),
            ),
        ),
        run_case(
            root,
            "separate_demo_state_source",
            mutate_json(
                root,
                after_path,
                lambda value: value["observed"]["stateView"].__setitem__(
                    "source_identity", "demoState"
                ),
            ),
        ),
        run_case(
            root,
            "early_intermediate_frame",
            mutate_json(
                root,
                after_path,
                lambda value: value["observed"].__setitem__(
                    "firstObservedChangeMs", 120
                ),
            ),
        ),
        run_case(
            root,
            "forged_aggregate_totals",
            mutate_json(
                root,
                replay_path,
                lambda value: value["totals"].__setitem__(
                    "scenario_count", 43
                ),
            ),
        ),
        run_case(
            root,
            "duplicate_named_scenario",
            mutate_json(
                root,
                pixel_path,
                lambda value: value["matrix"].__setitem__(
                    1, copy.deepcopy(value["matrix"][0])
                ),
            ),
        ),
        run_case(
            root,
            "stale_pupil_nonzero",
            mutate_json(
                root,
                pixel_path,
                lambda value: value["invariants"].__setitem__(
                    "stale_pupil_pixel_count", 1
                ),
            ),
        ),
        run_case(
            root,
            "screenshot_pixel_drift",
            {
                screenshot_path:
                (root / screenshot_path).read_bytes()[:-1] + b"\0"
            },
        ),
        run_case(
            root,
            "determinism_forged",
            mutate_json(
                root,
                determinism_path,
                lambda value: value.__setitem__("byte_identical", False),
            ),
        ),
        run_case(
            root,
            "owner_result_precreated",
            {gate.OWNER_RESULT_PATH: b'{"selected":"\\u901a\\u8fc7"}\n'},
        ),
    ]
    rejected = sum(row["rejected"] for row in negative_cases)
    status = (
        "PASS"
        if clean["status"] == "MACHINE_READY"
        and newline_equivalence["status"] == "MACHINE_READY"
        and rejected == len(negative_cases)
        else "NO_GO"
    )
    return {
        "schema": "companion.browser-three-wave-state-view-negatives.v1",
        "requirements": ["COMP-REQ-533", "COMP-REQ-534"],
        "status": status,
        "clean": clean,
        "newline_equivalence": newline_equivalence,
        "identity_basis": "git_blob_plus_canonical_lf_sha256",
        "negative_case_count": len(negative_cases),
        "rejected_negative_count": rejected,
        "cases": negative_cases,
        "side_effect_counters": {
            "server_start": 0,
            "visible_browser": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "product_write": 0,
            "registry_write": 0,
        },
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output = (
        root
        / gate.VALIDATION_DIR
        / "source-bound-negatives.json"
    )
    result = build(root)
    output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "status": result["status"],
        "negative_case_count": result["negative_case_count"],
        "rejected_negative_count": result["rejected_negative_count"],
        "canonical_sha256": sha256_bytes(
            gate.canonical_lf_bytes(output.read_bytes())
        ),
    }))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
