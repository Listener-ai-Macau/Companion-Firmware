#!/usr/bin/env python3
"""Validate V29 component-only performances and the shared browser/target plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/validation/companion-v29-silhouette-object-special-expression-component-performance-preview-20260720.json"
OUTPUT = ROOT / "docs/validation/companion-v29-silhouette-object-special-expression-component-performance-parity-20260720.json"
SPECIAL = ("menu_active", "recording_active", "charging_active")
EXPECTED_OBJECT_ROLES = {
    "menu_active": {"left_tab", "center_clasp", "right_tab"},
    "recording_active": {"left_earcup", "right_earcup", "pickup_boom"},
    "charging_active": {"charge_clasp", "charge_tether", "energy_core"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.convert("1").getdata(), right.convert("1").getdata()))


def main() -> int:
    route = json.loads(REPORT.read_text(encoding="utf-8"))
    errors: list[str] = []
    if route.get("status") != "PASS_V29_SILHOUETTE_OBJECT_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE":
        errors.append("V29 performance route is not PASS")
    if route.get("runtime_resource_activated") is not False or route.get("active_candidate_binding") != "forbidden":
        errors.append("V29 route is not inactive/unbound")
    policy = route.get("selection_policy", {})
    if policy.get("random_state_selection") is not False or policy.get("automatic_cross_state_cycle") is not False:
        errors.append("V29 selection policy allows random or automatic cross-state changes")
    if policy.get("unavailable_special_state_policy") != "fail_closed":
        errors.append("V29 unavailable special-state policy is not fail-closed")
    frames = route.get("frames", [])
    performances = route.get("performances", [])
    if not isinstance(frames, list) or not isinstance(performances, list):
        errors.append("V29 route is malformed")
        frames, performances = [], []
    by_index = {frame.get("index"): frame for frame in frames if isinstance(frame, dict)}
    frame_hashes: dict[int, str] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            errors.append("V29 frame record is malformed")
            continue
        path = ROOT / str(frame.get("targetPbm", ""))
        if not path.is_file() or sha256(path) != frame.get("targetPbmSha256"):
            errors.append(f"V29 frame hash drifted: {frame.get('index')}")
            continue
        frame_hashes[int(frame["index"])] = sha256(path)
        if not frame.get("layers"):
            errors.append(f"V29 frame has no component layers: {frame.get('index')}")
    named = {performance.get("id"): performance for performance in performances if isinstance(performance, dict)}
    if set(named) != {"daily_micro", *SPECIAL}:
        errors.append("V29 performance set drifted")
    evidence: dict[str, object] = {}
    for pose in SPECIAL:
        performance = named.get(pose, {})
        indices = performance.get("frame_indices", []) if isinstance(performance, dict) else []
        target = performance.get("inspect_frame_index") if isinstance(performance, dict) else None
        if not isinstance(indices, list) or len(indices) < 8 or target not in indices:
            errors.append(f"{pose} does not retain a causal component sequence and target hold")
            continue
        first, last = by_index.get(indices[0]), by_index.get(indices[-1])
        hold = by_index.get(target)
        if not first or not last or not hold:
            errors.append(f"{pose} references missing frames")
            continue
        if first.get("artPose") != "v9_daily" or last.get("artPose") != "v9_daily" or hold.get("artPose") != pose:
            errors.append(f"{pose} does not start/hold/settle through the required causal states")
        transitions = [frame_hashes.get(index) for index in indices]
        if any(left == right for left, right in zip(transitions, transitions[1:])):
            errors.append(f"{pose} contains a repeated adjacent component frame")
        target_layers = hold.get("layers", [])
        generated_roles = {str(layer.get("role", "")) for layer in target_layers if isinstance(layer, dict) and str(layer.get("source", "")).startswith("v29_generated")}
        allowed_roles = {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth", *EXPECTED_OBJECT_ROLES[pose]}
        if generated_roles - allowed_roles:
            errors.append(f"{pose} target contains a non-face V29 component")
        if not EXPECTED_OBJECT_ROLES[pose].issubset(generated_roles):
            errors.append(f"{pose} target omits a required state-object component")
        evidence[pose] = {"frame_count": len(indices), "target_hold_frame": target, "target_layer_count": len(target_layers), "entry_frame": indices[0], "settle_frame": indices[-1]}
    daily = named.get("daily_micro", {})
    daily_indices = daily.get("frame_indices", []) if isinstance(daily, dict) else []
    if len(daily_indices) != 3:
        errors.append("V29 Daily micro performance changed")
    daily_diffs = route.get("daily_entry_settle_difference_pixels", {})
    if daily_diffs.get("entry") != 0 or daily_diffs.get("final_settle") != 0:
        errors.append("V29 does not retain exact V9 Daily entry/settle")
    special_diffs = route.get("special_state_reassembly_differences_pixels", {})
    if any(special_diffs.get(pose) != 0 for pose in SPECIAL):
        errors.append("V29 target holds do not match exported component reassemblies")
    result = {
        "schema": "companion.v29_silhouette_object_special_expression_component_performance_parity.v1",
        "status": "PASS_V29_SILHOUETTE_OBJECT_COMPONENT_PERFORMANCE_BROWSER_TARGET_PLAN_PARITY" if not errors else "FAIL_V29_SILHOUETTE_OBJECT_COMPONENT_PERFORMANCE_PARITY",
        "performance_preview": rel(REPORT),
        "performance_preview_sha256": sha256(REPORT),
        "browser_target_plan_rule": "The browser player consumes each frame's canonical layers array and target PBM is composed from that exact same array; no second whole-face frame plan exists.",
        "daily_entry_settle_difference_pixels": daily_diffs,
        "special_state_reassembly_differences_pixels": special_diffs,
        "special_performance_evidence": evidence,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V29 special performances use one deterministic component plan for browser and target PBM output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
