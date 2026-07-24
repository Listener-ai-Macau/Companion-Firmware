#!/usr/bin/env python3
"""Deterministic in-memory tamper matrix for the COMP-REQ-540 gate."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = (
    ROOT
    / "tools/faraday_upper_art/"
    "verify_companion_family_micro_source_bound_comp_req_540.py"
)


def load_gate() -> Any:
    spec = importlib.util.spec_from_file_location("comp_req_540_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_path(target: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    current: Any = target
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=(
            "docs/validation/"
            "companion-browser-family-micro-choreography-comp-req-540/"
            "source-bound-negatives.json"
        ),
    )
    args = parser.parse_args()
    gate = load_gate()
    documents = gate.load_documents()
    page_text = (ROOT / gate.PAGE).read_text(encoding="utf-8")
    baseline = gate.semantic_checks(documents, page_text)
    if not all(baseline.values()):
        raise RuntimeError("clean semantic baseline does not pass")

    mutations: list[
        tuple[str, Callable[[dict[str, Any]], None], str | None]
    ] = [
        ("focused_status", lambda d: set_path(d, ("focused", "status"), "PASS"), "FAIL"),
        (
            "focused_page_hash",
            lambda d: set_path(
                d,
                ("focused", "page", "canonical_sha256"),
                "0" * 64,
            ),
            None,
        ),
        (
            "ten_family_missing",
            lambda d: d["static"]["selected_families"].pop(),
            None,
        ),
        (
            "two_component_claim",
            lambda d: set_path(
                d,
                ("static", "checks", "two_component_classes"),
                False,
            ),
            None,
        ),
        (
            "clock_cadence_count",
            lambda d: set_path(d, ("clock", "real_clock_cadences"), 119),
            None,
        ),
        (
            "clock_trace_divergence",
            lambda d: set_path(
                d,
                ("clock", "real_clock", 0, "runs", 1, "trace_sha256"),
                "F" * 64,
            ),
            None,
        ),
        (
            "clock_first_beat_late",
            lambda d: set_path(
                d,
                ("clock", "real_clock", 0, "first_changed_cadence"),
                7,
            ),
            None,
        ),
        (
            "replay_scenario_count",
            lambda d: set_path(d, ("replay", "counts", "scenarios"), 41),
            None,
        ),
        (
            "microphone_request",
            lambda d: set_path(
                d,
                ("replay", "counts", "microphone_requests"),
                1,
            ),
            None,
        ),
        (
            "pixel_duplicate_indicator",
            lambda d: set_path(
                d,
                ("pixel", "invariants", "recording_indicator_zero"),
                False,
            ),
            None,
        ),
        (
            "screenshot_hash",
            lambda d: set_path(
                d,
                ("screenshots", "screenshots", 0, "sha256"),
                "A" * 64,
            ),
            None,
        ),
        (
            "parity_state_count",
            lambda d: set_path(
                d,
                ("parity", "observed", "state_count"),
                110,
            ),
            None,
        ),
        (
            "parity_zero_diff_claim",
            lambda d: set_path(
                d,
                ("parity", "checks", "browser_to_c_pixel_diff_zero"),
                False,
            ),
            None,
        ),
        (
            "manifest_unique_count",
            lambda d: set_path(
                d,
                ("manifest", "invariants", "unique_frame_count"),
                86,
            ),
            None,
        ),
        (
            "manifest_polarity",
            lambda d: set_path(
                d,
                ("manifest", "format", "black_bit"),
                0,
            ),
            None,
        ),
        (
            "pbm_pixel_diff",
            lambda d: set_path(
                d,
                (
                    "manifest",
                    "states",
                    0,
                    "pixel_diff_after_registered_transform",
                ),
                1,
            ),
            None,
        ),
        (
            "micro_random_choice",
            lambda d: set_path(
                d,
                (
                    "manifest",
                    "source",
                    "embedded_manifest",
                    "family_micro_choreography",
                    "random_choice",
                ),
                True,
            ),
            None,
        ),
    ]
    rows = []
    for name, mutate, status_override in mutations:
        candidate = copy.deepcopy(documents)
        mutate(candidate)
        if status_override is not None:
            candidate["focused"]["status"] = status_override
        checks = gate.semantic_checks(candidate, page_text)
        failed = sorted(key for key, value in checks.items() if not value)
        rows.append({"id": name, "failed_checks": failed, "rejected": bool(failed)})

    injected_checks = gate.semantic_checks(
        documents,
        page_text + "\n<div class='recording-indicator'></div>",
    )
    rows.append(
        {
            "id": "page_recording_indicator_injection",
            "failed_checks": sorted(
                key for key, value in injected_checks.items() if not value
            ),
            "rejected": not all(injected_checks.values()),
        }
    )
    stale_checks, _ = gate.source_identity_checks("0" * 40, documents)
    rows.append(
        {
            "id": "stale_or_missing_source_commit",
            "failed_checks": sorted(
                key for key, value in stale_checks.items() if not value
            ),
            "rejected": not all(stale_checks.values()),
        }
    )
    result = {
        "schema": "companion.comp-req-540-source-bound-negatives.v1",
        "requirements": ["COMP-REQ-540", "COMP-REQ-541"],
        "status": "PASS" if all(row["rejected"] for row in rows) else "NO_GO",
        "count": len(rows),
        "rows": rows,
        "side_effects": {
            "browser_start": 0,
            "hardware": 0,
            "owner_prompt": 0,
            "production_write": 0,
        },
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = gate.canonical_bytes(result)
    output.write_bytes(payload)
    print(
        json.dumps(
            {
                "count": len(rows),
                "sha256": gate.sha256(payload),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
