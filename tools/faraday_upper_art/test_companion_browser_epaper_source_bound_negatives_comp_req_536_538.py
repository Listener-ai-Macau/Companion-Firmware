#!/usr/bin/env python3
"""Deterministic tamper matrix for the COMP-REQ-536/537/538 source gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_gate(root: Path) -> Any:
    path = (
        root
        / "tools/faraday_upper_art/"
        "verify_companion_browser_epaper_source_bound_comp_req_536_538.py"
    )
    spec = importlib.util.spec_from_file_location("comp_req_536_538_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("source gate import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    gate = load_gate(root)

    def json_file(name: str) -> dict[str, Any]:
        relative = gate.BOUND_FILES[name][0]
        return json.loads((root / relative).read_text(encoding="utf-8"))

    cases: list[tuple[str, dict[str, bytes] | None, str]] = []

    page_path = gate.BOUND_FILES["page"][0]
    cases.append(("page_byte_drift", {page_path: b"<!doctype html>tampered\n"}, gate.SOURCE_COMMIT))

    focused = json_file("focused")
    for case_id, mutate in (
        ("focused_css_interpolation", lambda d: d["checks"].update(no_css_interpolation=False)),
        ("focused_idle_nondeterminism", lambda d: d["checks"].update(idle_two_runs_equal=False)),
        (
            "focused_wave_count",
            lambda d: d["observed"]["waves"][0].update(
                arcs=d["observed"]["waves"][0]["arcs"][:2]
            ),
        ),
    ):
        candidate = deepcopy(focused)
        mutate(candidate)
        cases.append((case_id, {gate.BOUND_FILES["focused"][0]: canonical(candidate)}, gate.SOURCE_COMMIT))

    replay = json_file("replay")
    for case_id, mutate in (
        ("replay_claimed_total", lambda d: d["counts"].update(scenarios=41)),
        ("replay_microphone_request", lambda d: d["counts"].update(microphone_requests=1)),
        (
            "replay_scenario_record",
            lambda d: d["scenarios"][0].update({"pass": False}),
        ),
    ):
        candidate = deepcopy(replay)
        mutate(candidate)
        cases.append((case_id, {gate.BOUND_FILES["replay"][0]: canonical(candidate)}, gate.SOURCE_COMMIT))

    pixel = json_file("pixel")
    pixel["invariants"]["recording_is_orthogonal"] = False
    cases.append(("pixel_orthogonality", {gate.BOUND_FILES["pixel"][0]: canonical(pixel)}, gate.SOURCE_COMMIT))

    screenshots = json_file("screenshots")
    screenshot_path = screenshots["screenshots"][0]["path"]
    cases.append(("screenshot_bytes", {screenshot_path: b"not a png"}, gate.SOURCE_COMMIT))
    screenshots["screenshots"][0]["sha256"] = "0" * 64
    cases.append(("screenshot_claim", {gate.BOUND_FILES["screenshots"][0]: canonical(screenshots)}, gate.SOURCE_COMMIT))

    parity = json_file("parity")
    parity["checks"]["browser_to_c_pixel_diff_zero"] = False
    cases.append(("parity_pixel_diff", {gate.BOUND_FILES["parity"][0]: canonical(parity)}, gate.SOURCE_COMMIT))

    manifest = json_file("manifest")
    manifest["invariants"]["state_count"] = 70
    cases.append(("manifest_claimed_state_count", {gate.BOUND_FILES["manifest"][0]: canonical(manifest)}, gate.SOURCE_COMMIT))

    cases.extend(
        [
            (
                "frames_payload",
                {gate.BOUND_FILES["frames"][0]: b"\x00" * 5000},
                gate.SOURCE_COMMIT,
            ),
            (
                "c_pack",
                {gate.BOUND_FILES["c_pack"][0]: b"#error tampered\n"},
                gate.SOURCE_COMMIT,
            ),
            (
                "h_pack",
                {gate.BOUND_FILES["h_pack"][0]: b"#define ENABLE 1\n"},
                gate.SOURCE_COMMIT,
            ),
        ]
    )

    manifest = json_file("manifest")
    pbm_path = f"{gate.EXPORT_DIR}/{manifest['states'][0]['pbm_file']}"
    cases.append(("pbm_payload", {pbm_path: b"P4\n200 200\n"}, gate.SOURCE_COMMIT))
    cases.append(("stale_source_commit", None, "cfe7a9d086dfaa2615dd1e2a437f9c70db316e6d"))

    rows = []
    for case_id, overlay, source_commit in cases:
        result = gate.evaluate(root, overlay=overlay, source_commit=source_commit)
        rejected = result["status"] == "NO_GO" and bool(result["failed_checks"])
        rows.append(
            {
                "id": case_id,
                "rejected": rejected,
                "failure_count": len(result["failed_checks"]),
            }
        )

    output = {
        "schema": "companion.browser-epaper-source-bound-negatives.v1",
        "requirements": ["COMP-REQ-536", "COMP-REQ-537", "COMP-REQ-538"],
        "status": "PASS" if all(row["rejected"] for row in rows) else "NO_GO",
        "negative_case_count": len(rows),
        "rejected_negative_count": sum(row["rejected"] for row in rows),
        "cases": rows,
        "side_effects": {
            "browser": 0,
            "hardware": 0,
            "owner_prompt": 0,
            "production_write": 0,
            "server": 0,
        },
    }
    path = (root / args.output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(output))
    print(json.dumps(output, sort_keys=True))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
