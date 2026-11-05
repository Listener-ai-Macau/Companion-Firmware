#!/usr/bin/env python3
"""Run and archive the active Goal's current source-mask Rig machine closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-rig-goal-machine-closure-20260719.json"
LOCKED_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
PROTECTED_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
EXPANDED_RIG_REPORT = ROOT / "docs/validation/companion-v9-expanded-expression-rig-export-20260719.json"
EMOTION_BRIDGE_BROWSER_CAPTURE = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v2-expanded-source/candidate/emotion-bridge-browser-capture-report.json"
FULL_SOURCE_BUNDLE_REVIEW = ROOT / "docs/validation/companion-v9-full-expression-source-bundle-owner-art-review-20260718.json"
V22_COMPONENT_BRIDGE_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-component-bridge-gate-20260719.json"
V22_OWNER_ART_SCREEN_REVIEW = ROOT / "docs/validation/companion-v22-emotion-separation-component-bridge-owner-art-screen-review-20260719.json"
V22_TARGET_RIG_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V22_WB55_DEMO_BUILD_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-demo-build-gate-20260719.json"
V22_WB55_TRACE_CONTRACT = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-trace-contract-20260719.json"
DETERMINISTIC_BEHAVIOR = ROOT / "docs/validation/companion-v9-expression-choreographer-20260719-deterministic-behavior.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_ACCEPTANCE_HASH = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def command_matrix() -> list[tuple[str, list[str]]]:
    return [
        ("profile", [sys.executable, "tools/generate_companion_v9_expression_rig_profile.py", "--check"]),
        ("render", [sys.executable, "tools/render_companion_v9_expression_rig.py", "--layout",
            "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json", "--output-dir",
            "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200", "--report",
            "docs/validation/companion-v9-expression-rig-render-20260717.json"]),
        ("rig_verify", [sys.executable, "tools/verify_companion_v9_expression_rig.py", "--report",
            "docs/validation/companion-v9-expression-rig-render-20260717.json", "--write",
            "docs/validation/companion-v9-expression-rig-cemp-20260717.json"]),
        ("rig_host", ["pwsh", "-NoProfile", "-File", "tools/test_expression_rig_host.ps1"]),
        ("choreographer_host", ["pwsh", "-NoProfile", "-File", "tools/test_expression_choreographer_host.ps1",
            "-EvidencePath", "docs/validation/companion-v9-expression-choreographer-20260719-deterministic-behavior.json"]),
        ("wba_mount_host", ["pwsh", "-NoProfile", "-File", "tools/test_wba_v9_expression_rig_asset_mount_host.ps1"]),
        ("motion_coordinator_host", ["pwsh", "-NoProfile", "-File", "tools/test_motion_coordinator_host.ps1"]),
        ("motion_queue_host", ["pwsh", "-NoProfile", "-File", "tools/test_motion_display_queue_host.ps1"]),
        ("pipeline", [sys.executable, "tools/test_v9_expression_rig_pipeline.py"]),
        ("display_queue_static", [sys.executable, "tools/verify_display_queue_static.py"]),
        ("art_lineage", [sys.executable, "tools/verify_companion_v9_art_lineage.py", "--write",
            "docs/validation/companion-v9-art-lineage-machine-20260718.json"]),
        ("expanded_export", [sys.executable, "tools/export_companion_v9_expanded_expression_rig.py", "--clean"]),
        ("expanded_profile", [sys.executable, "tools/generate_companion_v9_expanded_expression_rig_profile.py", "--check"]),
        ("expanded_rig_verify", [sys.executable, "tools/verify_companion_v9_expanded_expression_rig.py", "--write",
            "docs/validation/companion-v9-expanded-expression-rig-export-20260719.json"]),
        ("expanded_wba_mount_host", ["pwsh", "-NoProfile", "-File",
            "tools/test_wba_v9_expanded_expression_rig_asset_mount_host.ps1"]),
        ("expanded_emotion_bridge_browser", ["pwsh", "-NoProfile", "-File",
            "tools/capture_companion_v9_expanded_expression_rig_emotion_bridge_browser.ps1"]),
        ("v22_target_rig_profile", [sys.executable,
            "tools/generate_companion_v22_emotion_separation_target_rig.py", "--check"]),
        ("v22_target_rig_wba_mount_host", ["pwsh", "-NoProfile", "-File",
            "tools/test_wba_v22_emotion_separation_rig_asset_mount_host.ps1"]),
        ("v22_target_rig_verify", [sys.executable,
            "tools/verify_companion_v22_emotion_separation_target_rig.py", "--write",
            "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"]),
        ("v22_wb55_production_off_demo_build", ["pwsh", "-NoProfile", "-File",
            "tools/test_wb55_v22_emotion_separation_demo_build.ps1"]),
        ("v22_wb55_observed_trace_contract", ["pwsh", "-NoProfile", "-File",
            "tools/test_v22_wb55_emotion_bridge_trace.ps1"]),
    ]


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = f"{completed.stdout}{completed.stderr}"
    return {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "stdout_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest().upper(),
        "output_tail": output[-1200:],
    }


def verify_art_reports(errors: list[str]) -> dict[str, Any]:
    cemp = load_json(ROOT / "docs/validation/companion-v9-expression-rig-cemp-20260717.json")
    lineage = load_json(ROOT / "docs/validation/companion-v9-art-lineage-machine-20260718.json")
    expanded_rig = load_json(EXPANDED_RIG_REPORT)
    bridge_capture = load_json(EMOTION_BRIDGE_BROWSER_CAPTURE)
    source_bundle_review = load_json(FULL_SOURCE_BUNDLE_REVIEW)
    v22_bridge_gate = load_json(V22_COMPONENT_BRIDGE_GATE)
    v22_owner_review = load_json(V22_OWNER_ART_SCREEN_REVIEW)
    v22_target_rig_gate = load_json(V22_TARGET_RIG_GATE)
    v22_wb55_demo_build_gate = load_json(V22_WB55_DEMO_BUILD_GATE)
    v22_wb55_trace_contract = load_json(V22_WB55_TRACE_CONTRACT)
    deterministic_behavior = load_json(DETERMINISTIC_BEHAVIOR)
    expected = (
        (cemp.get("status"), "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED", "Rig CEMP verification"),
        (lineage.get("status"), "PASS_ART_LINEAGE", "art lineage verification"),
        (expanded_rig.get("status"), "PASS_EXPANDED_COMPONENT_RIG_MACHINE_GATE", "expanded Rig verification"),
        (bridge_capture.get("status"), "PASS_EXPANDED_COMPONENT_EMOTION_BRIDGE_BROWSER_CAPTURE", "emotion bridge browser capture"),
        (source_bundle_review.get("selected"), "通过", "full source-bundle art review"),
        (v22_bridge_gate.get("status"), "PASS_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_GATE",
         "V22 component bridge machine gate"),
        (v22_owner_review.get("status"), "PASS_OWNER_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_ACCEPTED_RUNTIME_INACTIVE",
         "V22 owner art/screen review"),
        (v22_target_rig_gate.get("status"), "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE",
         "V22 external-NOR target Rig verification"),
        (v22_wb55_demo_build_gate.get("status"),
         "PASS_V22_EMOTION_SEPARATION_WB55_PRODUCTION_OFF_DEMO_BUILD_GATE",
         "V22 production-off WB55 demo build verification"),
        (v22_wb55_trace_contract.get("status"),
         "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT",
         "V22 WB55 observed-trace parser self-test"),
        (deterministic_behavior.get("status"), "PASS", "deterministic behavior-arbitration host test"),
    )
    for actual, expected_status, label in expected:
        if actual != expected_status:
            errors.append(f"{label} expected {expected_status!r}, found {actual!r}")
    behavior_arbitration = deterministic_behavior.get("behavior_arbitration")
    if not isinstance(behavior_arbitration, dict) or \
            behavior_arbitration.get("intent") != "alert_response" or \
            behavior_arbitration.get("reason") != "event_appraisal" or \
            behavior_arbitration.get("event_priority") != 100 or \
            behavior_arbitration.get("cancels_active_intent") is not True or \
            behavior_arbitration.get("route_count") != 3:
        errors.append("deterministic behavior evidence lost its causal priority/route contract")
    trace_timeline = v22_wb55_trace_contract.get("browser_observed_replay_timeline")
    if not isinstance(trace_timeline, list) or len(trace_timeline) < 2:
        errors.append("V22 WB55 trace timeline is missing")
    else:
        for index, step in enumerate(trace_timeline):
            if not isinstance(step, dict):
                errors.append("V22 WB55 trace timeline contains an invalid step")
                break
            visible_delay = step.get("browser_next_final_frame_visible_delay_ms")
            if index + 1 == len(trace_timeline):
                if visible_delay is not None:
                    errors.append("V22 final settled browser frame must not auto-replay")
                continue
            following = trace_timeline[index + 1]
            if not isinstance(following, dict) or visible_delay != (
                    step.get("post_refresh_hold_ms", -1) +
                    following.get("observed_refresh_elapsed_ms", -1)):
                errors.append("V22 browser final-frame visibility timing drifted from the observed trace")
                break
    expected_expanded_metrics = {
        "state_count": 15,
        "component_count": 96,
        "performance_frame_count": 105,
        "presence_frame_count": 120,
        "emotion_bridge_count": 45,
        "emotion_bridge_frame_count": 315,
        "browser_component_preview_parity_frames": 540,
        "presence_browser_component_preview_parity_frames": 120,
        "emotion_bridge_browser_component_preview_parity_frames": 315,
        "owner_rejected_fail_closed_state_count": 1,
        "runtime_resource_activated": False,
        "full_face_source_card_playback": "forbidden",
    }
    for field, expected_value in expected_expanded_metrics.items():
        if expanded_rig.get(field) != expected_value:
            errors.append(
                f"expanded Rig {field} expected {expected_value!r}, found {expanded_rig.get(field)!r}")
    occlusion = expanded_rig.get("component_occlusion_audit")
    if not isinstance(occlusion, dict) or occlusion.get("status") != "PASS_ZERO_PROTECTED_FEATURE_OVERLAP" or \
            occlusion.get("frame_count") != 540 or occlusion.get("performance_contact_sheet_count") != 15 or \
            occlusion.get("presence_contact_sheet_count") != 15 or \
            occlusion.get("emotion_bridge_contact_sheet_count") != 45:
        errors.append("expanded Rig component-occlusion audit did not prove all transition, presence, and emotion-bridge frames safe")
    if bridge_capture.get("source_emotion") != "curious" or bridge_capture.get("target_emotion") != "affectionate":
        errors.append("emotion bridge browser capture did not preserve the registered Curious-to-Affectionate directed edge")
    bridge_diffs = bridge_capture.get("source_hold_pixel_differences")
    if not isinstance(bridge_diffs, dict) or any(
            not isinstance(bridge_diffs.get(cue), int) or bridge_diffs[cue] <= 0
            for cue in ("gaze_lead", "brow_answer", "lower_face_reply", "target_hold")):
        errors.append("emotion bridge browser capture did not prove visible staged component changes")
    return {
        "rig_cemp": cemp.get("status"),
        "art_lineage": lineage.get("status"),
        "full_source_bundle_owner_art": source_bundle_review.get("selected"),
        "v22_component_bridge_gate": v22_bridge_gate.get("status"),
        "v22_owner_art_screen_review": v22_owner_review.get("status"),
        "v22_runtime_resource_activated": v22_owner_review.get("runtime_resource_activated"),
        "v22_target_rig_gate": v22_target_rig_gate.get("status"),
        "v22_target_rig_wba_external_nor_host": v22_target_rig_gate.get("wba_external_nor_host"),
        "v22_target_rig_component_count": v22_target_rig_gate.get("component_count"),
        "v22_target_rig_bridge_frame_count": v22_target_rig_gate.get("bridge_frame_count"),
        "v22_wb55_production_off_demo_build": v22_wb55_demo_build_gate.get("status"),
        "v22_wb55_demo_runtime_resource_activated": v22_wb55_demo_build_gate.get("runtime_resource_activated"),
        "v22_wb55_demo_firmware_flashed": v22_wb55_demo_build_gate.get("firmware_flashed"),
        "v22_wb55_demo_panel_observed": v22_wb55_demo_build_gate.get("panel_observed"),
        "v22_wb55_trace_contract": v22_wb55_trace_contract.get("status"),
        "v22_wb55_trace_origin": v22_wb55_trace_contract.get("trace_origin"),
        "v22_wb55_trace_panel_observed": v22_wb55_trace_contract.get("panel_observed"),
        "deterministic_behavior_arbitration": deterministic_behavior.get("status"),
        "deterministic_behavior_intent": behavior_arbitration.get("intent") if isinstance(behavior_arbitration, dict) else None,
        "deterministic_behavior_reason": behavior_arbitration.get("reason") if isinstance(behavior_arbitration, dict) else None,
        "expanded_component_rig": expanded_rig.get("status"),
        "expanded_state_count": expanded_rig.get("state_count"),
        "expanded_component_count": expanded_rig.get("component_count"),
        "expanded_performance_frame_count": expanded_rig.get("performance_frame_count"),
        "expanded_presence_frame_count": expanded_rig.get("presence_frame_count"),
        "expanded_emotion_bridge_count": expanded_rig.get("emotion_bridge_count"),
        "expanded_emotion_bridge_frame_count": expanded_rig.get("emotion_bridge_frame_count"),
        "expanded_browser_component_preview_parity_frames":
            expanded_rig.get("browser_component_preview_parity_frames"),
        "expanded_presence_browser_component_preview_parity_frames":
            expanded_rig.get("presence_browser_component_preview_parity_frames"),
        "expanded_emotion_bridge_browser_component_preview_parity_frames":
            expanded_rig.get("emotion_bridge_browser_component_preview_parity_frames"),
        "expanded_component_occlusion": occlusion.get("status") if isinstance(occlusion, dict) else None,
        "expanded_occlusion_frame_count": occlusion.get("frame_count") if isinstance(occlusion, dict) else None,
        "expanded_performance_contact_sheet_count":
            occlusion.get("performance_contact_sheet_count") if isinstance(occlusion, dict) else None,
        "expanded_presence_contact_sheet_count":
            occlusion.get("presence_contact_sheet_count") if isinstance(occlusion, dict) else None,
        "expanded_emotion_bridge_contact_sheet_count":
            occlusion.get("emotion_bridge_contact_sheet_count") if isinstance(occlusion, dict) else None,
        "emotion_bridge_browser_capture": bridge_capture.get("status"),
        "emotion_bridge_browser_capture_preview_sha256": bridge_capture.get("preview_sha256"),
        "expanded_runtime_resource_activated": expanded_rig.get("runtime_resource_activated"),
    }


def verify() -> dict[str, Any]:
    errors: list[str] = []
    commands = [run_command(name, command) for name, command in command_matrix()]
    for command in commands:
        if command["returncode"] != 0:
            errors.append(f"{command['name']} returned {command['returncode']}")
    if not LOCKED_SOURCE.is_file() or sha256(LOCKED_SOURCE) != LOCKED_SOURCE_HASH:
        errors.append("locked V9 source hash drifted")
    if not PROTECTED_ACCEPTANCE.is_file() or sha256(PROTECTED_ACCEPTANCE) != PROTECTED_ACCEPTANCE_HASH:
        errors.append("protected owner acceptance hash drifted")
    art_reports = verify_art_reports(errors)
    return {
        "schema": "companion.v9_expression_rig_goal_machine_closure.v1",
        "status": "PASS_GOAL_MACHINE_CLOSURE_V22_EXTERNAL_NOR_PARITY_SCREEN_ACCEPTED_EXTERNAL_GATES_PENDING" if not errors else "FAIL_GOAL_MACHINE_CLOSURE",
        "locked_v9_source": rel(LOCKED_SOURCE),
        "locked_v9_source_sha256": LOCKED_SOURCE_HASH,
        "protected_owner_acceptance_sha256": PROTECTED_ACCEPTANCE_HASH,
        "commands": commands,
        "art_reports": art_reports,
        "runtime_resource_activated": False,
        "charging_error": "fail_closed_no_registered_components",
        "owner_screen_review": "V22 daily component choreography is owner accepted and remains runtime inactive. Its exact browser/PBM plan now replays from an external-NOR CRIG on WBA55/WBA65 host adapters and a separately compiled production-off WB55 single-bridge demo. Behavior arbitration is deterministic and causal: idle preserves its selected baseline, events select one ranked intent and only a higher-priority event may cancel it. A self-tested parser turns a future exact WB55 trace into a component-only browser replay clock whose next stable face waits for the following observed refresh completion, but this closure has no physical trace, waveform, flash, or panel claim; the broader G1-G8 physical/hardware acceptance and unbound special-function source-art gates remain pending.",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    try:
        result = verify()
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if result["status"] != "PASS_GOAL_MACHINE_CLOSURE_V22_EXTERNAL_NOR_PARITY_SCREEN_ACCEPTED_EXTERNAL_GATES_PENDING":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: active Goal machine closure passed; V22 screen review and external-NOR target parity are accepted, while external G1-G8 and special-art gates remain pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
