#!/usr/bin/env python3
"""Preflight the versioned V15 sleep Rig source-pose generation request."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v15-sleep-rig-pose-source/generation-request.json"
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
POSES = ("sleep_rest_anchor", "sleep_brow_settle", "sleep_lower_face_breath", "sleep_rest_return")
REQUIRED_COMPONENTS = {
    "left_brow_rest", "left_brow_settle", "right_brow_rest", "left_closed_eye_anchor", "right_closed_eye_anchor",
    "left_cheek_rest", "left_cheek_breath", "right_cheek_rest", "right_cheek_breath", "nose_anchor",
    "mouth_rest", "mouth_breath", "sleep_breath_mark_left", "sleep_breath_mark_right", "sleep_zzz_cluster",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, default=REQUEST)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    request_path = args.request.resolve()
    errors: list[str] = []
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if request.get("schema") != "companion.v9_expression_rig_pose_generation_request.v1":
            errors.append("V15 request schema drifted")
        if request.get("status") != "VERSIONED_PROMPT_PENDING_GENERATION" or request.get("owner_requirement") != "COMP-REQ-131":
            errors.append("V15 request disposition drifted")
        if request.get("target_profile", {}).get("grid") != [2, 2]:
            errors.append("V15 must request a 2x2 source pose sheet")
        references = request.get("source_references")
        if not isinstance(references, list) or len(references) != 1 or references[0].get("path") != LOCKED_V9.relative_to(ROOT).as_posix() or references[0].get("sha256") != LOCKED_SHA256:
            errors.append("V15 must use only the locked V9 reference")
        if sha256(LOCKED_V9) != LOCKED_SHA256:
            errors.append("locked V9 source hash drifted")
        rejected = request.get("rejected_predecessors")
        if not isinstance(rejected, list) or not all(f"v{version}-" in " ".join(rejected) for version in (12, 13, 14)):
            errors.append("V15 must explicitly reject V12, V13 and V14 sources")
        poses = request.get("pose_cells")
        if not isinstance(poses, list) or [row.get("name") for row in poses if isinstance(row, dict)] != list(POSES):
            errors.append("V15 pose order drifted")
        components = request.get("required_source_components")
        if not isinstance(components, list) or set(components) != REQUIRED_COMPONENTS:
            errors.append("V15 component vocabulary drifted")
        if any("zzz" in name and name != "sleep_zzz_cluster" for name in components if isinstance(name, str)):
            errors.append("V15 may export only one compact zzz cluster")
        prompt = request.get("prompt")
        if not isinstance(prompt, str) or any(token not in prompt.lower() for token in ("only visual reference", "2 by 2", "not three independently floating stickers", "only registered masks")):
            errors.append("V15 prompt misses the Rig-source constraints")
        negative = request.get("negative_constraints")
        if not isinstance(negative, list) or not any("whole-face runtime playback" in item for item in negative if isinstance(item, str)):
            errors.append("V15 negative constraints miss whole-face playback ban")
        if request.get("current_runtime_disposition") != "Sleep remains fail-closed in the active expanded Rig pending V15 machine gates and owner acceptance.":
            errors.append("V15 fail-closed disposition drifted")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(str(exc))
    result = {
        "schema": "companion.v15_sleep_rig_pose_request_preflight.v1",
        "status": "PASS_V15_VERSIONED_PROMPT_PREFLIGHT" if not errors else "FAIL_V15_VERSIONED_PROMPT_PREFLIGHT",
        "request": request_path.relative_to(ROOT).as_posix(),
        "locked_v9_source": LOCKED_V9.relative_to(ROOT).as_posix(),
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
    print("PASS: V15 sleep Rig pose request is versioned and V9-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
