#!/usr/bin/env python3
"""Require V32 functional silhouettes to be distinct before an owner sees them."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-source-gate-20260720.json"
EXPORT = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-export-gate-20260720.json"
PERFORMANCE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-performance-preview-20260720.json"
PARITY = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-performance-parity-20260720.json"
BROWSER = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-browser-render-20260720.json"
CLOSURE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-machine-closure-20260720.json"
WRITE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-internal-visual-preflight-20260720.json"
POSES = ("menu_active", "recording_active", "charging_active")
ROLES = {
    "menu_active": {"left_hollow_page_tab", "active_hollow_notched_page_tab", "right_hollow_page_tab"},
    "recording_active": {"left_thin_receiver_cuff", "right_thin_receiver_cuff", "single_pickup_dot"},
    "charging_active": {"small_open_side_coupler", "thin_continuous_short_tether", "small_hollow_slotted_energy_dock"},
}
MICRO = {
    "menu_active": ("menu_active_scan_left", {"left_hollow_page_tab": [-1, 0], "active_hollow_notched_page_tab": [-1, 0], "right_hollow_page_tab": [-1, 0]}),
    "recording_active": ("recording_active_listen_pulse", {"left_thin_receiver_cuff": [0, -1], "right_thin_receiver_cuff": [1, 0], "single_pickup_dot": [0, -1]}),
    "charging_active": ("charging_active_recovery_breathe", {"small_open_side_coupler": [1, 0], "thin_continuous_short_tether": [1, 0], "small_hollow_slotted_energy_dock": [0, -1]}),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def role_offsets(frame: dict[str, Any]) -> dict[str, list[int]]:
    return {str(layer.get("role")): list(layer.get("offset", [])) for layer in frame.get("layers", []) if isinstance(layer, dict)}


def main() -> int:
    errors: list[str] = []
    artifacts = {
        "source_gate": (SOURCE, "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_SOURCE_GATE_PENDING_COMPONENT_EXPORT"),
        "component_export_gate": (EXPORT, "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_EXPORT_UNBOUND"),
        "component_performance": (PERFORMANCE, "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE"),
        "browser_target_parity": (PARITY, "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_PERFORMANCE_BROWSER_TARGET_PLAN_PARITY"),
        "browser_render": (BROWSER, "PASS_V32_BROWSER_RENDER_INSPECTION_NATIVE_200X200"),
        "machine_closure": (CLOSURE, "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_MACHINE_CLOSURE_RUNTIME_INACTIVE"),
    }
    loaded: dict[str, dict[str, Any]] = {}
    records: dict[str, dict[str, object]] = {}
    for name, (path, status) in artifacts.items():
        add(errors, path.is_file(), f"{name} artifact is missing")
        data = load(path) if path.is_file() else {}
        loaded[name] = data
        add(errors, data.get("status") == status, f"{name} status is not {status}")
        records[name] = {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path) if path.is_file() else None, "status": data.get("status")}

    source = loaded["source_gate"]
    add(errors, source.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "source gate lost locked V9 identity")
    limit = source.get("object_part_ink_limit")
    add(errors, isinstance(limit, int) and limit > 0, "source gate lacks the V9 half-eye object limit")
    pose_source = {entry.get("pose"): entry for entry in source.get("poses", []) if isinstance(entry, dict)}
    for pose in POSES:
        entry = pose_source.get(pose, {})
        parts = entry.get("state_object_ink_pixels", {}) if isinstance(entry, dict) else {}
        add(errors, isinstance(parts, dict) and set(parts) == ROLES[pose], f"{pose} lacks its declared representative silhouette")
        add(errors, isinstance(parts, dict) and all(isinstance(value, int) and 8 <= value <= limit for value in parts.values()), f"{pose} object part exceeds the compact V9 budget")
        add(errors, entry.get("outside_face_ink_pixels") == 0, f"{pose} has undeclared non-face ink")
    mouths = source.get("mouth_contours", {})
    add(errors, isinstance(mouths, dict) and all(mouths.get(pose, {}).get("connected_contours") == 1 for pose in POSES), "special states do not have one extractable mouth contour each")
    mouth_pairs = source.get("pairwise_mouth_differences", [])
    add(errors, isinstance(mouth_pairs, list) and len(mouth_pairs) == 3 and all(pair.get("same_mask") is False and int(pair.get("mouth_pixel_difference", 0)) >= 100 for pair in mouth_pairs if isinstance(pair, dict)), "special-state mouths are not materially distinct")
    face_pairs = source.get("pairwise_face_primary_differences", [])
    add(errors, isinstance(face_pairs, list) and len(face_pairs) == 3 and all(int(pair.get("face_primary_pixel_difference", 0)) >= 25000 for pair in face_pairs if isinstance(pair, dict)), "special-state faces are insufficiently differentiated")

    route = loaded["component_performance"]
    frames = [frame for frame in route.get("frames", []) if isinstance(frame, dict)]
    by_segment = {str(frame.get("segment")): frame for frame in frames}
    choreography: dict[str, dict[str, object]] = {}
    for pose in POSES:
        state_frames = [frame for frame in frames if str(frame.get("segment", "")).startswith(f"{pose}_")]
        segments = [str(frame.get("segment")) for frame in state_frames]
        required = [f"{pose}_{suffix}" for suffix in ("daily_entry", "notice", "brows_arrive", "mouth_arrive", "object_arrive", "object_connect", "face_settle", "object_release", "release_face", "daily_settle")]
        if pose == "menu_active":
            required.append("menu_active_active_page_arrive")
        add(errors, all(segment in segments for segment in required), f"{pose} lacks a complete causal arrival/hold/release sequence")
        hold_suffix = "decision_hold" if pose == "menu_active" else "listen_hold" if pose == "recording_active" else "recovery_hold"
        hold_roles = {str(layer.get("role")) for layer in by_segment.get(f"{pose}_{hold_suffix}", {}).get("layers", []) if isinstance(layer, dict)}
        add(errors, ROLES[pose].issubset(hold_roles), f"{pose} hold omits its functional silhouette")
        micro_segment, expected = MICRO[pose]
        actual = role_offsets(by_segment.get(micro_segment, {}))
        add(errors, all(actual.get(role) == offset for role, offset in expected.items()), f"{pose} causal micro-action lost its registered offsets")
        add(errors, bool(state_frames) and state_frames[0].get("artPose") == "v9_daily" and state_frames[-1].get("artPose") == "v9_daily", f"{pose} does not return to exact V9 Daily")
        choreography[pose] = {"segments": segments, "hold_roles": sorted(hold_roles & ROLES[pose]), "micro_segment": micro_segment, "micro_offsets": {role: actual.get(role) for role in expected}}

    result = {
        "schema": "companion.v32_representative_functional_silhouette_internal_visual_preflight.v1",
        "status": "PASS_INTERNAL_VISUAL_PREFLIGHT_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTES" if not errors else "FAIL_INTERNAL_VISUAL_PREFLIGHT_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTES",
        "candidate": "V32 locked-V9-only representative functional-silhouette source, attempt 03",
        "machine_evidence": records,
        "inspection_contract": {"native_target_size": [200, 200], "labels_hidden_for_reading": True, "same_browser_target_component_plan": True, "whole_face_playback": False, "runtime_resource_activated": False, "object_parts_per_state": 3, "object_part_ink_limit": limit},
        "representative_readability": {"roles_by_state": {pose: sorted(ROLES[pose]) for pose in POSES}, "minimum_pairwise_mouth_difference": 100, "minimum_pairwise_face_primary_difference": 25000, "mouth_contours": mouths, "pairwise_mouth_differences": mouth_pairs, "pairwise_face_primary_differences": face_pairs},
        "causal_performance_evidence": choreography,
        "decision": {"owner_operator_prompt_opened": False, "human_art_acceptance_requested": False, "candidate_disposition": "PENDING_CANONICAL_OWNER_ART_REVIEW", "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "still_forbidden_before_owner_acceptance": ["CRIG_export", "profile_generation", "event_binding", "firmware_flash", "physical_panel_claim", "whole_face_fallback"], "owner_fail_route": "Freeze V32 as audit-only and return to a fresh locked-V9-only source direction."},
        "errors": errors,
    }
    WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: V32 representative functional silhouettes and causal choreography preflight -> {WRITE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
