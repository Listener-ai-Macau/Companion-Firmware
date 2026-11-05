#!/usr/bin/env python3
"""Verify deterministic COMP-REQ-471 browser capture and firmware export."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


OLD_PAGE_SHA = "D68478DAB33D4B2F13E5A62B63A65F1A9B37593C3551D8B19444731EA6C22116"
EXPECTED_PAGE_SHA = "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
EXPECTED_PRIOR_SHA = "9A831B882E24D5C1726B674BA40D8187F5E726E00A234BA3FFDACD33AD215123"
EXPECTED_STEADY_FACE_PNG_SHA = "3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31"
REQUIREMENT = "COMP-REQ-471"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): file_sha(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def mismatch(left: dict[str, str], right: dict[str, str]) -> list[dict[str, str | None]]:
    paths = sorted(set(left) | set(right))
    return [
        {"path": path, "canonical": left.get(path), "rerun": right.get(path)}
        for path in paths
        if left.get(path) != right.get(path)
    ]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-capture", required=True, type=Path)
    parser.add_argument("--rerun-capture", required=True, type=Path)
    parser.add_argument("--canonical-export", required=True, type=Path)
    parser.add_argument("--rerun-export", required=True, type=Path)
    parser.add_argument("--pointer-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    canonical_capture = args.canonical_capture.resolve()
    rerun_capture = args.rerun_capture.resolve()
    canonical_export = args.canonical_export.resolve()
    rerun_export = args.rerun_export.resolve()
    capture = read_json(canonical_capture / "capture-manifest.json")
    rerun = read_json(rerun_capture / "capture-manifest.json")
    contract = read_json(canonical_export / "visual-contract.json")
    transitions = read_json(canonical_export / "state-transitions.json")
    oracle = read_json(canonical_export / "pixel-oracle.json")
    handoff = read_json(canonical_export / "handoff-manifest.json")
    pointer = read_json(args.pointer_result.resolve())

    capture_tree = tree_hashes(canonical_capture)
    rerun_capture_tree = tree_hashes(rerun_capture)
    export_tree = tree_hashes(canonical_export)
    rerun_export_tree = tree_hashes(rerun_export)
    capture_mismatch = mismatch(capture_tree, rerun_capture_tree)
    export_mismatch = mismatch(export_tree, rerun_export_tree)

    state_ids = [item["id"] for item in contract["frames"]]
    frame_by_id = {item["id"]: item for item in contract["frames"]}
    pointer_scenarios = pointer.get("scenarios", {})
    pointer_matrix = {
        viewport: {
            "mouse": all(f"mouse_{name}" in scenarios for name in ["single", "drag", "hold"]),
            "touch": all(f"touch_{name}" in scenarios for name in ["single", "double", "drag"]),
            "pen": all(f"pen_{name}" in scenarios for name in ["single", "drag"]),
        }
        for viewport, scenarios in pointer_scenarios.items()
        if viewport in {"desktop", "mobile"}
    }
    route_states = {
        viewport: {
            "menu_entries": next(
                item["dom"]["interaction"]["menuEntries"]
                for item in capture["states"]
                if item["png"].split("/")[1] == viewport and item["id"] == "menu_roots"
            ),
            "recording_entries": next(
                item["dom"]["interaction"]["recordingEntries"]
                for item in capture["states"]
                if item["png"].split("/")[1] == viewport and item["id"] == "recording_entry"
            ),
        }
        for viewport in ["desktop", "mobile"]
    }
    menu_checks = [
        item
        for item in capture["checks"]["items"]
        if any(
            token in item["id"]
            for token in [
                "menu_route_once",
                "menu_exclusive_surface",
                "menu_voice",
                "menu_device",
                "menu_connection",
                "menu_preferences",
                "device_ui_assets",
                "menu_return",
            ]
        )
    ]
    recording_checks = [
        item
        for item in capture["checks"]["items"]
        if "recording_" in item["id"]
    ]
    checks = {
        "accepted_page_identity": capture["source"]["page_sha256"] == EXPECTED_PAGE_SHA
        and rerun["source"]["page_sha256"] == EXPECTED_PAGE_SHA
        and pointer["page_sha256"] == EXPECTED_PAGE_SHA,
        "old_page_identity_and_single_authorized_change": capture["source"]["old_page_sha256"]
        == OLD_PAGE_SHA
        and capture["source"]["authorized_change"]["reconstructed_old_page_sha256"] == OLD_PAGE_SHA
        and capture["source"]["authorized_change"]["only_authorized_change"] is True,
        "accepted_prior_20_of_20_identity": capture["source"]["prior_20_of_20_sha256"] == EXPECTED_PRIOR_SHA,
        "accepted_steady_face_pixels_unchanged": capture["source"][
            "accepted_steady_face_png_sha256"
        ]
        == EXPECTED_STEADY_FACE_PNG_SHA
        and all(
            state["png_sha256"] == EXPECTED_STEADY_FACE_PNG_SHA
            for state in capture["states"]
            if state["id"] == "centered_rest"
        ),
        "gesture_constants_unchanged": capture["source"]["gesture_constants_unchanged"] is True
        and capture["source"]["gesture_constants"] == {
            "menu_hold_ms": 700,
            "double_tap_gap_ms": 350,
            "double_tap_move_px": 32,
            "drag_move_px": 44,
        },
        "fresh_total_interaction_at_least_20_of_20": capture["checks"]["passed"] >= 20
        and capture["checks"]["passed"] == capture["checks"]["total"],
        "capture_byte_stable_rerun": not capture_mismatch,
        "export_byte_stable_rerun": not export_mismatch,
        "frame_count_bounded": contract["frame_count"] == len(state_ids) == transitions["state_count"],
        "frame_size_5000": all(item["byte_length"] == 5000 for item in contract["frames"]),
        "pixel_oracle_zero": oracle["total_desktop_to_raw_mismatch_bits"] == 0
        and oracle["total_mobile_to_raw_mismatch_bits"] == 0
        and oracle["total_desktop_mobile_mismatch_bits"] == 0,
        "one_primary_surface": all(item["primary_surface_count"] == 1 for item in contract["frames"]),
        "maximum_one_gaze_highlight": all(item["gaze_highlight_count"] <= 1 for item in contract["frames"]),
        "stale_clipping_overlap_zero": contract["invariants"]["measured"]["stale_layer_count"] == 0
        and contract["invariants"]["measured"]["source_black_pixels_outside_stage"] == 0
        and contract["invariants"]["policy_derived"]["clipping_violation_count"] == 0
        and contract["invariants"]["measured"]["conflicting_surface_overlap_count"] == 0
        and capture["checks"]["stale_layer_count"] == 0
        and capture["checks"]["conflicting_surface_overlap_count"] == 0,
        "measured_not_constant_oracle": all(
            "measured" in item
            and "policy_derived" in item
            and "stage_rect" in item["measured"]["desktop"]
            and "packed_edge_touch_sides" in item["measured"]["desktop"]
            for item in contract["frames"]
        ),
        "edge_contact_policy_explicit": all(
            item["policy_derived"]["edge_contact_policy"]["reason"]
            and item["policy_derived"]["clipping_violation_count"] == 0
            for item in contract["frames"]
        ),
        "route_activation_exactly_one": all(
            state["menu_entries"] == 1 and state["recording_entries"] == 1
            for state in route_states.values()
        ),
        "menu_and_recording_return_pixels_equal_rest": frame_by_id["menu_return_rest"][
            "raw_sha256"
        ]
        == frame_by_id["centered_rest"]["raw_sha256"]
        and frame_by_id["recording_return_rest"]["raw_sha256"]
        == frame_by_id["centered_rest"]["raw_sha256"],
        "return_inactive_surfaces_zero": all(
            not any(frame_by_id[state]["measured"][viewport]["inactive_surfaces"].values())
            for state in ["menu_return_rest", "recording_return_rest"]
            for viewport in ["desktop", "mobile"]
        ),
        "http_404_zero": capture["checks"]["http_404_count"] == 0 and not capture["errors"],
        "menu_regression_pass": len(menu_checks) >= 16 and all(item["pass"] for item in menu_checks),
        "recording_regression_pass": len(recording_checks) >= 4 and all(item["pass"] for item in recording_checks),
        "pointer_mouse_touch_pen_desktop_mobile_pass": pointer.get("status") == "PASS"
        and set(pointer_matrix) == {"desktop", "mobile"}
        and all(all(types.values()) for types in pointer_matrix.values()),
        "handoff_is_neutral_and_not_authorization": handoff["integration_authorized"] is False
        and handoff["hardware_contact"] == 0,
        "real_hold_binding_exactly_once": all(
            item["route_exactly_once"]
            for item in contract["hold_feedback_binding"]["real_pointer_regressions"]
        ),
        "debug_parameter_panel_hidden": contract["invariants"]["measured"][
            "debug_parameter_panel_visible_count"
        ] == 0,
        "orientation_preserved": contract["invariants"]["policy_derived"][
            "browser_orientation_preserved"
        ] is True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "schema": "companion.comp-req-467-machine-result.v1",
        "requirement": REQUIREMENT,
        "status": "PASS" if not failed else "NO_GO",
        "source": {
            "page_sha256": capture["source"]["page_sha256"],
            "prior_20_of_20_sha256": capture["source"]["prior_20_of_20_sha256"],
        },
        "fresh_browser_interaction": {
            "passed": capture["checks"]["passed"],
            "total": capture["checks"]["total"],
            "desktop_mobile": True,
            "menu_checks": len(menu_checks),
            "recording_checks": len(recording_checks),
            "pointer_matrix": pointer_matrix,
            "pointer_result_sha256": file_sha(args.pointer_result.resolve()),
        },
        "deterministic_rerun": {
            "capture_file_count": len(capture_tree),
            "capture_mismatches": capture_mismatch,
            "export_file_count": len(export_tree),
            "export_mismatches": export_mismatch,
        },
        "routes": route_states,
        "counts": {
            "frames": contract["frame_count"],
            "states": transitions["state_count"],
            "transitions": transitions["transition_count"],
            "http_404": capture["checks"]["http_404_count"],
            "stale": capture["checks"]["stale_layer_count"],
            "observed_layer_rect_clip": capture["checks"]["observed_layer_rect_clip_count"],
            "clipping_policy_violation": contract["invariants"]["policy_derived"][
                "clipping_violation_count"
            ],
            "overlap": capture["checks"]["conflicting_surface_overlap_count"],
        },
        "artifacts": {
            "frames_bin_sha256": file_sha(canonical_export / "frames.bin"),
            "visual_contract_sha256": file_sha(canonical_export / "visual-contract.json"),
            "state_transitions_sha256": file_sha(canonical_export / "state-transitions.json"),
            "pixel_oracle_sha256": file_sha(canonical_export / "pixel-oracle.json"),
            "handoff_manifest_sha256": file_sha(canonical_export / "handoff-manifest.json"),
            "capture_manifest_sha256": file_sha(canonical_capture / "capture-manifest.json"),
        },
        "artifact_file_sha256": {
            "canonical_capture": capture_tree,
            "canonical_export": export_tree,
        },
        "checks": checks,
        "failed": failed,
        "boundaries": {
            "hardware_contact": 0,
            "production_changes": 0,
            "driver_changes": 0,
            "firmware_build_wiring_changes": 0,
            "operator_prompt_count": 0,
        },
    }
    write_json(args.output.resolve(), result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "result": str(args.output.resolve()),
                "checks": f"{sum(checks.values())}/{len(checks)}",
                "capture_files_equal": not capture_mismatch,
                "export_files_equal": not export_mismatch,
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
