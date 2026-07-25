#!/usr/bin/env python3
"""Tamper negatives for the COMP-REQ-560 MACHINE_READY verifier."""

from __future__ import annotations

import copy
import argparse
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "docs/validation/companion-rigid-eye-highlight-comp-req-560"
VERIFIER = (
    ROOT
    / "tools/faraday_upper_art/"
    "verify_companion_rigid_eye_highlight_machine_ready_comp_req_560.py"
)

spec = importlib.util.spec_from_file_location("comp_req_560_verifier", VERIFIER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def store(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


cases = [
    (
        "unpaired_cluster",
        "rigid-eye-highlight.json",
        lambda value: value["directions"][1].update({"paired_clusters": False}),
        "paired direction clusters",
    ),
    (
        "stale_source_pixel",
        "rigid-eye-highlight.json",
        lambda value: value["directions"][2].update({"residual_source_pixels": 1}),
        "source cleanup",
    ),
    (
        "interaction_drop",
        "interaction-42/interaction-successor-result.json",
        lambda value: value.update({"scenarios_pass_under_current_contract": 41}),
        "interaction scenarios",
    ),
    (
        "browser_c_pixel_drift",
        "ten-family-parity.json/visual-frame-manifest.json",
        lambda value: value["invariants"].update({"browser_to_c_pixel_diff": 1}),
        "browser C parity",
    ),
    (
        "hardware_contact",
        "MACHINE_READY.json",
        lambda value: value["checkonly"].update({"hardware_contact": 1}),
        "machine side effects",
    ),
]

results = []
with tempfile.TemporaryDirectory(prefix="comp-req-560-negatives-") as temporary:
    temp_root = Path(temporary)
    for name, relative, mutate, expected_failure in cases:
        candidate = temp_root / name
        shutil.copytree(VALIDATION, candidate)
        target = candidate / relative
        value = copy.deepcopy(load(target))
        mutate(value)
        store(target, value)
        result = module.verify(candidate)
        assert result["status"] == "NO_GO", f"{name} unexpectedly passed"
        assert expected_failure in result["failures"], (
            f"{name} did not hit {expected_failure}: {result['failures']}"
        )
        results.append({
            "name": name,
            "status": result["status"],
            "expected_failure": expected_failure,
        })

result = {
    "schema": "companion.comp_req_560.machine_ready_negatives.v1",
    "status": "PASS",
    "cases": results,
}
parser = argparse.ArgumentParser()
parser.add_argument("--output")
args = parser.parse_args()
if args.output:
    output = (ROOT / args.output).resolve()
    if ROOT not in output.parents:
        raise SystemExit("output must remain in repository")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, separators=(",", ":")))
