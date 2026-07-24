#!/usr/bin/env python3
"""Verify V30 has compact source components and causal, non-card choreography."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-source-gate-20260720.json"
EXPORT = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-component-export-gate-20260720.json"
PERFORMANCE = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-component-performance-preview-20260720.json"
PARITY = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-component-performance-parity-20260720.json"
BROWSER = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-component-browser-render-20260720.json"
CLOSURE = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-machine-closure-20260720.json"
WRITE = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-internal-visual-preflight-20260720.json"

POSES = ("menu_active", "recording_active", "charging_active")
OBJECT_ROLES = {
    "menu_active": {"left_tab", "center_tab", "right_tab"},
    "recording_active": {"left_ear_cuff", "right_ear_cuff", "pickup_point"},
    "charging_active": {"charge_clasp", "short_tether", "energy_core"},
}
MICRO_OFFSETS = {
    "menu_active": ("menu_active_scan_left", {"left_tab": [-1, 0], "center_tab": [-1, 0], "right_tab": [-1, 0]}),
    "recording_active": ("recording_active_listen_pulse", {"left_ear_cuff": [-1, 0], "right_ear_cuff": [1, 0], "pickup_point": [0, -1]}),
    "charging_active": ("charging_active_recovery_breathe", {"charge_clasp": [1, 0], "short_tether": [1, 0], "energy_core": [0, -1]}),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def roles(frame: dict[str, Any]) -> set[str]:
    return {str(layer.get("role", "")) for layer in frame.get("layers", []) if isinstance(layer, dict)}


def offsets(frame: dict[str, Any]) -> dict[str, list[int]]:
    return {
        str(layer.get("role", "")): list(layer.get("offset", []))
        for layer in frame.get("layers", [])
        if isinstance(layer, dict)
    }


def main() -> int:
    errors: list[str] = []
    artifacts = {
        "source_gate": (SOURCE, "PASS_V30_MINIMAL_FUNCTIONAL_OBJECT_SOURCE_GATE_PENDING_COMPONENT_EXPORT"),
        "component_export_gate": (EXPORT, "PASS_V30_MINIMAL_FUNCTIONAL_OBJECT_COMPONENT_EXPORT_UNBOUND"),
        "component_performance": (PERFORMANCE, "PASS_V30_MINIMAL_FUNCTIONAL_OBJECT_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE"),
        "browser_target_parity": (PARITY, "PASS_V30_MINIMAL_FUNCTIONAL_OBJECT_COMPONENT_PERFORMANCE_BROWSER_TARGET_PLAN_PARITY"),
        "browser_render": (BROWSER, "PASS_V30_BROWSER_RENDER_INSPECTION_NATIVE_200X200"),
        "machine_closure": (CLOSURE, "PASS_V30_MINIMAL_FUNCTIONAL_OBJECT_MACHINE_CLOSURE_RUNTIME_INACTIVE"),
    }
    loaded: dict[str, dict[str, Any]] = {}
    records: dict[str, dict[str, object]] = {}
    for name, (path, expected_status) in artifacts.items():
        add(errors, path.is_file(), f"{name} artifact is missing")
        data = load(path) if path.is_file() else {}
        loaded[name] = data
        add(errors, data.get("status") == expected_status, f"{name} status is not {expected_status}")
        records[name] = {"path": rel(path), "sha256": sha256(path) if path.is_file() else None, "status": data.get("status")}

    source = loaded["source_gate"]
    add(errors, source.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "source gate lost locked V9 identity")
    part_limit = source.get("object_part_ink_limit")
    add(errors, isinstance(part_limit, int) and part_limit > 0, "source gate lacks the V9 half-eye object limit")
    source_poses = {entry.get("pose"): entry for entry in source.get("poses", []) if isinstance(entry, dict)}
    source_evidence: dict[str, dict[str, object]] = {}
    for pose in POSES:
        entry = source_poses.get(pose, {})
        object_ink = entry.get("state_object_ink_pixels", {}) if isinstance(entry, dict) else {}
        add(errors, isinstance(object_ink, dict) and set(object_ink) == OBJECT_ROLES[pose], f"{pose} has the wrong V30 object-part set")
        if isinstance(object_ink, dict) and isinstance(part_limit, int):
            add(errors, all(isinstance(count, int) and 8 <= count <= part_limit for count in object_ink.values()), f"{pose} object part violates the native 200x200 ink budget")
        add(errors, entry.get("outside_face_ink_pixels") == 0, f"{pose} has undeclared non-face ink")
        source_evidence[pose] = {
            "object_roles": sorted(object_ink) if isinstance(object_ink, dict) else [],
            "object_ink_pixels": object_ink,
            "object_part_ink_limit": part_limit,
            "outside_face_ink_pixels": entry.get("outside_face_ink_pixels"),
        }

    route = loaded["component_performance"]
    add(errors, route.get("runtime_resource_activated") is False, "V30 route activated runtime")
    add(errors, route.get("active_candidate_binding") == "forbidden", "V30 route permits a behavior binding")
    policy = route.get("selection_policy", {})
    add(errors, policy.get("random_state_selection") is False, "V30 route allows random state selection")
    add(errors, policy.get("automatic_cross_state_cycle") is False, "V30 route allows automatic cross-state cycling")
    add(errors, policy.get("unavailable_special_state_policy") == "fail_closed", "V30 unavailable states are not fail-closed")
    frames_by_segment = {str(frame.get("segment")): frame for frame in route.get("frames", []) if isinstance(frame, dict)}
    performance_evidence: dict[str, dict[str, object]] = {}
    for pose in POSES:
        prefix = f"{pose}_"
        state_frames = [frame for frame in route.get("frames", []) if isinstance(frame, dict) and str(frame.get("segment", "")).startswith(prefix)]
        segments = [str(frame.get("segment")) for frame in state_frames]
        required_sequence = [
            f"{pose}_daily_entry",
            f"{pose}_notice",
            f"{pose}_brows_arrive",
            f"{pose}_mouth_arrive",
            f"{pose}_object_arrive",
            f"{pose}_object_connect",
            f"{pose}_face_settle",
            f"{pose}_object_release",
            f"{pose}_release_face",
            f"{pose}_daily_settle",
        ]
        add(errors, all(segment in segments for segment in required_sequence), f"{pose} lacks a complete entry/connect/hold/release sequence")
        connect = frames_by_segment.get(f"{pose}_object_connect", {})
        hold_suffix = "decision_hold" if pose == "menu_active" else "listen_hold" if pose == "recording_active" else "recovery_hold"
        hold = frames_by_segment.get(f"{pose}_{hold_suffix}", {})
        add(errors, OBJECT_ROLES[pose].issubset(roles(connect)), f"{pose} object connection omits a registered object component")
        add(errors, OBJECT_ROLES[pose].issubset(roles(hold)), f"{pose} hold omits a registered object component")
        micro_segment, expected_offsets = MICRO_OFFSETS[pose]
        micro = frames_by_segment.get(micro_segment, {})
        actual_offsets = offsets(micro)
        add(errors, all(actual_offsets.get(role) == expected for role, expected in expected_offsets.items()), f"{pose} micro-action lacks its registered one-pixel causal offsets")
        add(errors, state_frames and state_frames[0].get("artPose") == "v9_daily" and state_frames[-1].get("artPose") == "v9_daily", f"{pose} does not return to exact V9 Daily")
        performance_evidence[pose] = {
            "segments": segments,
            "connect_roles": sorted(roles(connect) & OBJECT_ROLES[pose]),
            "hold_roles": sorted(roles(hold) & OBJECT_ROLES[pose]),
            "micro_segment": micro_segment,
            "micro_offsets": {role: actual_offsets.get(role) for role in expected_offsets},
        }

    browser = loaded["browser_render"]
    screenshots = browser.get("screenshots", [])
    add(errors, isinstance(screenshots, list) and len(screenshots) == 4, "browser capture lacks the four native scene screenshots")
    if isinstance(screenshots, list):
        for screenshot in screenshots:
            path = ROOT / str(screenshot.get("path", ""))
            add(errors, path.is_file() and sha256(path) == screenshot.get("sha256"), "browser screenshot is missing or hash drifted")

    result = {
        "schema": "companion.v9_special_expression_internal_visual_preflight.v5",
        "status": "PASS_INTERNAL_VISUAL_PREFLIGHT_V30_MINIMAL_FUNCTIONAL_OBJECTS" if not errors else "FAIL_INTERNAL_VISUAL_PREFLIGHT_V30_MINIMAL_FUNCTIONAL_OBJECTS",
        "candidate": "V30 V9-only minimal functional-object special-expression source, attempt 01",
        "machine_evidence": records,
        "inspection_contract": {
            "native_target_size": [200, 200],
            "labels_hidden_for_reading": True,
            "same_browser_target_component_plan": True,
            "whole_face_playback": False,
            "runtime_resource_activated": False,
            "object_parts_per_state": 3,
            "object_part_ink_limit": part_limit,
        },
        "source_component_evidence": source_evidence,
        "causal_performance_evidence": performance_evidence,
        "decision": {
            "owner_operator_prompt_opened": False,
            "human_art_acceptance_requested": False,
            "candidate_disposition": "PENDING_CANONICAL_OWNER_ART_REVIEW",
            "runtime_resource_activated": False,
            "active_candidate_binding": "forbidden",
            "still_forbidden_before_owner_acceptance": ["CRIG_export", "profile_generation", "event_binding", "firmware_flash", "physical_panel_claim", "whole_face_fallback"],
            "owner_fail_route": "Freeze V30 as audit-only, preserve the machine artifacts, forbid it as a future visual prompt/reference input, and return to a new locked-V9-only source direction.",
        },
        "errors": errors,
    }
    WRITE.parent.mkdir(parents=True, exist_ok=True)
    WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: V30 compact object and causal choreography preflight -> {rel(WRITE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
