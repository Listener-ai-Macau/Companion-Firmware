#!/usr/bin/env python3
"""Preflight the three V9-only complete special-expression source requests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SPECS = {
    "menu_active": {
        "iteration": "companion-pet-expression-v9-extension-v18-menu-special-expression-source",
        "filename": "attempt-01-generated-menu-special-expression.png",
        "required": ("complete", "menu", "open rounded black eyes", "vertical trio"),
    },
    "recording_active": {
        "iteration": "companion-pet-expression-v9-extension-v19-recording-special-expression-source",
        "filename": "attempt-01-generated-recording-special-expression.png",
        "required": ("complete", "recording", "open rounded black eyes", "symmetric pair"),
    },
    "upgrade_active": {
        "iteration": "companion-pet-expression-v9-extension-v20-upgrade-special-expression-source",
        "filename": "attempt-01-generated-upgrade-special-expression.png",
        "required": ("complete", "upgrade", "open rounded black eyes", "four tiny detached rounded progress segments"),
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    errors: list[str] = []
    requests: dict[str, Any] = {}
    for function, spec in SPECS.items():
        path = ROOT / "docs/art/iterations" / spec["iteration"] / "generation-request.json"
        try:
            request = json.loads(path.read_text(encoding="utf-8"))
            requests[function] = rel(path)
            if request.get("schema") != "companion.v9_complete_special_expression_generation_request.v1" or \
                    request.get("status") != "PROMPT_VERSIONED_PENDING_GENERATION":
                errors.append(f"{function} request disposition drifted")
            if request.get("product_requirement") != "COMP-REQ-138" or request.get("function") != function or \
                    "complete special-expression source pose" not in str(request.get("named_visible_variable", "")).lower():
                errors.append(f"{function} special-expression contract drifted")
            references = request.get("reference_images")
            if not isinstance(references, list) or len(references) != 1 or \
                    references[0].get("path") != rel(LOCKED_V9) or references[0].get("sha256") != LOCKED_SHA256:
                errors.append(f"{function} request is not locked-V9-only")
            prompt = str(request.get("prompt_delta", "")).lower()
            if any(token not in prompt for token in spec["required"]):
                errors.append(f"{function} prompt misses its required complete-pose vocabulary")
            if "whole-face runtime playback" not in " ".join(request.get("negative_constraints", [])).lower() or \
                    "v17" not in " ".join(request.get("negative_constraints", [])).lower():
                errors.append(f"{function} request does not forbid card playback or V17 reuse")
            planned = str(request.get("planned_output", ""))
            if not planned.endswith(spec["filename"]) or spec["iteration"] not in planned:
                errors.append(f"{function} output path drifted")
        except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"{function}: {exc}")
    if sha256(LOCKED_V9) != LOCKED_SHA256:
        errors.append("locked V9 source hash drifted")
    result = {
        "schema": "companion.v18_v20_complete_special_expression_request_preflight.v1",
        "status": "PASS_V18_V20_VERSIONED_SPECIAL_EXPRESSION_REQUESTS" if not errors else
                  "FAIL_V18_V20_VERSIONED_SPECIAL_EXPRESSION_REQUESTS",
        "requests": requests,
        "locked_v9_source": rel(LOCKED_V9),
        "locked_v9_sha256": LOCKED_SHA256,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V18-V20 complete special-expression requests are versioned and locked-V9-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
