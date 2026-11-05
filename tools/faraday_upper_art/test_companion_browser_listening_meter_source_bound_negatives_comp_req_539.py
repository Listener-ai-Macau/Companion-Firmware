#!/usr/bin/env python3
"""Deterministic tamper matrix for the COMP-REQ-539 source-bound gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import verify_companion_browser_listening_meter_source_bound_comp_req_539 as gate


ROOT = Path(__file__).resolve().parents[2]


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--stale-commit", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def mutate_case(
    original: dict,
    page_text: str,
    name: str,
    expected_check: str,
    mutation,
) -> dict:
    documents = copy.deepcopy(original)
    candidate_page = page_text
    result = mutation(documents, candidate_page)
    if isinstance(result, str):
        candidate_page = result
    checks = gate.semantic_checks(documents, candidate_page)
    return {
        "name": name,
        "expected_failed_check": expected_check,
        "observed": checks.get(expected_check),
        "pass": checks.get(expected_check) is False,
    }


def main() -> int:
    args = parse_args()
    output_path = (ROOT / args.output).resolve()
    output_path.relative_to(ROOT)
    original = gate.load_documents()
    page_text = (ROOT / gate.PAGE).read_text(encoding="utf-8")
    cases = []

    def add(name: str, expected: str, mutation) -> None:
        cases.append(
            mutate_case(original, page_text, name, expected, mutation)
        )

    add(
        "focused_status_forged",
        "focused_all_checks_true",
        lambda docs, _: docs["focused"].update(status="PASS", failed=["x"]),
    )
    add(
        "scheduler_inert",
        "idle_scheduler_live_and_bounded",
        lambda docs, _: [
            row.update(changed=False, refresh_requested=False)
            for run in docs["focused"]["observed"]["idle"]["runs"]
            for row in run
        ],
    )
    add(
        "scheduler_first_change_late",
        "idle_scheduler_live_and_bounded",
        lambda docs, _: docs["focused"]["observed"]["idle"].update(
            first_changed_within_960ms=False
        ),
    )
    add(
        "scheduler_nondeterministic",
        "idle_real_clock_60x2_deterministic",
        lambda docs, _: docs["focused"]["observed"]["idle"]["runs"][1][0]
        .update(key="forged"),
    )
    add(
        "progress_dom_returned",
        "hold_progress_absent_all_paths",
        lambda _docs, source: source + "\n.hold-progress{}\n",
    )
    add(
        "progress_node_observed",
        "hold_progress_absent_all_paths",
        lambda docs, _: docs["focused"]["observed"]["hold"]["rows"][1]
        .update(nodes=1),
    )
    add(
        "hold_threshold_drift",
        "hold_3000_direct_menu_once",
        lambda docs, _: docs["focused"]["observed"]["hold"].update(
            menu_hold_ms=2999
        ),
    )
    add(
        "residual_arc_pixels",
        "no_arc_or_legacy_renderer",
        lambda docs, _: docs["focused"]["checks"].update(
            no_arc_pixels=False
        ),
    )
    add(
        "legacy_arc_renderer_returned",
        "no_arc_or_legacy_renderer",
        lambda _docs, source: source + "\ndrawBinaryWaveFront();\n",
    )
    add(
        "browser_intermediate_frame",
        "committed_480ms_no_intermediate",
        lambda docs, _: docs["manifest"]["source"]["embedded_manifest"][
            "rendering"
        ].update(committed_frames_only=False),
    )
    add(
        "meter_column_count_forged",
        "meter_three_equal_discrete_columns",
        lambda docs, _: docs["focused"]["observed"]["meter"]["rows"][0]
        .update(column_count=2),
    )
    add(
        "meter_shift_reversed",
        "meter_shift_inward_outer_insert",
        lambda docs, _: docs["focused"]["observed"]["meter"]["rows"][1][
            "transition"
        ]["shifted"][0].update(to=2),
    )
    add(
        "recording_freezes_affect",
        "recording_accessory_orthogonal_exit_only",
        lambda docs, _: docs["focused"]["checks"].update(
            accessory_does_not_replace_affect=False
        ),
    )
    add(
        "replay_aggregate_forged",
        "replay_6x7_42_pass",
        lambda docs, _: docs["replay"]["counts"].update(scenarios=41),
    )
    add(
        "microphone_request",
        "replay_zero_mic_404_and_side_effects",
        lambda docs, _: docs["replay"]["counts"].update(
            microphone_requests=1
        ),
    )
    add(
        "screenshot_hash_drift",
        "screenshots_12_exact",
        lambda docs, _: docs["screenshots"]["screenshots"][0].update(
            sha256="0" * 64
        ),
    )
    add(
        "parity_count_forged",
        "parity_independently_passes",
        lambda docs, _: docs["parity"]["observed"].update(state_count=81),
    )
    add(
        "manifest_pixel_diff_forged",
        "manifest_82_states_59_unique",
        lambda docs, _: docs["manifest"]["invariants"].update(
            browser_to_c_pixel_diff=1
        ),
    )
    add(
        "polarity_drift",
        "one_bit_identity_orientation",
        lambda docs, _: docs["manifest"]["format"].update(
            black_bit=0, white_bit=1
        ),
    )

    current_checks, _ = gate.source_identity_checks(
        args.source_commit,
        original,
    )
    stale_checks, _ = gate.source_identity_checks(
        args.stale_commit,
        original,
    )
    cases.extend([
        {
            "name": "current_source_identity_control",
            "expected_failed_check": None,
            "observed": all(current_checks.values()),
            "pass": all(current_checks.values()),
        },
        {
            "name": "stale_source_commit",
            "expected_failed_check": "source_identity",
            "observed": all(stale_checks.values()),
            "pass": not all(stale_checks.values()),
        },
    ])
    failed = [case["name"] for case in cases if not case["pass"]]
    result = {
        "schema": "companion.comp-req-539-source-bound-negatives.v1",
        "status": "PASS" if not failed else "NO_GO",
        "case_count": len(cases),
        "cases": cases,
        "failed": failed,
        "inputs": {
            "source_commit": args.source_commit,
            "stale_commit": args.stale_commit,
        },
        "side_effects": {
            "browser": 0,
            "hardware": 0,
            "owner_prompt": 0,
            "production_write": 0,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = canonical_bytes(result)
    output_path.write_bytes(output)
    print(json.dumps({
        "cases": len(cases),
        "failed": failed,
        "sha256": sha256(output),
        "status": result["status"],
    }, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
