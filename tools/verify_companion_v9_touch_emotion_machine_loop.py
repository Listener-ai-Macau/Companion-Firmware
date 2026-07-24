#!/usr/bin/env python3
"""Close the runtime-inactive touch-to-V9-Rig machine loop without flashing."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
TRACE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-20260719.json"
PREVIEW = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-preview-20260719.json"
PARITY = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-parity-20260719.json"
VISUAL_ROUTE = ROOT / "docs/validation/companion-v9-v22-touch-emotion-route-preview-20260720.json"
VISUAL_ROUTE_PARITY = ROOT / "docs/validation/companion-v9-v22-touch-emotion-route-parity-20260720.json"
BROWSER_RENDER_INSPECTION = ROOT / "docs/validation/companion-v9-v22-touch-emotion-route-browser-render-20260720.json"
WRITE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-closure-20260720.json"
LOCKED_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
PROTECTED_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
EXPECTED_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EXPECTED_ACCEPTANCE_SHA256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
TARGET_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.hex"
TARGET_ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.elf"
TARGET_OBJECT = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/expression_interaction_session.o"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
SESSION_SOURCE = ROOT / "app/companion_pendant/epaper/expression_interaction_session.c"
PROFILE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v9_candidate_profile.c"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: pathlib.Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def run(command: list[str]) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {command[0]}")


def main() -> int:
    commands = [
        ["pwsh", "-NoProfile", "-File", "tools/test_expression_rig_host.ps1"],
        ["pwsh", "-NoProfile", "-File", "tools/test_expression_choreographer_host.ps1",
         "-EvidencePath", "docs/validation/companion-v9-expression-choreographer-20260720-touch-loop.json"],
        ["pwsh", "-NoProfile", "-File", "tools/test_motion_coordinator_host.ps1"],
        ["pwsh", "-NoProfile", "-File", "tools/test_motion_display_queue_host.ps1"],
        ["pwsh", "-NoProfile", "-File", "tools/test_expression_interaction_session_host.ps1"],
        [sys.executable, "tools/render_companion_v9_touch_emotion_machine_preview.py"],
        [sys.executable, "tools/verify_companion_v9_touch_emotion_machine_preview.py"],
        [sys.executable, "tools/render_companion_v9_v22_touch_emotion_route.py"],
        [sys.executable, "tools/verify_companion_v9_v22_touch_emotion_route.py"],
        ["pwsh", "-NoProfile", "-File", "tools/capture_companion_v9_v22_touch_emotion_route_browser.ps1"],
        ["pwsh", "-NoProfile", "-File", "tools/build_nucleo_bringup.ps1",
         "-EpaperSsd1681Bringup", "-Force"],
    ]
    for command in commands:
        run(command)

    trace = load(TRACE)
    preview = load(PREVIEW)
    parity = load(PARITY)
    visual_route = load(VISUAL_ROUTE)
    visual_route_parity = load(VISUAL_ROUTE_PARITY)
    browser_render_inspection = load(BROWSER_RENDER_INSPECTION)
    frame_semantics = [
        ("performance", "entry", "daily", "calm"),
        ("performance", "lead", "daily", "calm"),
        ("performance", "response", "daily", "calm"),
        ("performance", "accent", "daily", "calm"),
        ("performance", "release", "daily", "calm"),
        ("bridge", None, "daily", "curious"),
        ("target", None, "daily", "affectionate"),
        ("settle", None, "daily", "calm"),
    ]
    actual_semantics = [
        (frame.get("kind"), frame.get("score_phase"), frame.get("scene"), frame.get("emotion"))
        for frame in trace.get("frames", []) if isinstance(frame, dict)
    ]
    presentation = trace.get("presentation")
    checks = {
        "locked_v9_source_hash": LOCKED_SOURCE.is_file() and sha256(LOCKED_SOURCE) == EXPECTED_SOURCE_SHA256,
        "protected_owner_acceptance_hash": (
            PROTECTED_ACCEPTANCE.is_file() and sha256(PROTECTED_ACCEPTANCE) == EXPECTED_ACCEPTANCE_SHA256
        ),
        "touch_trace_is_runtime_inactive_pass": (
            trace.get("status") == "PASS_TOUCH_TO_RIG_MACHINE_LOOP_RUNTIME_INACTIVE" and
            trace.get("runtime_resource_activated") is False and
            trace.get("source_sha256") == EXPECTED_SOURCE_SHA256
        ),
        "touch_trace_has_registered_component_keyframes_and_causal_route": actual_semantics == frame_semantics,
        "notice_score_is_coalesced_for_epaper": (
            isinstance(presentation, dict) and
            presentation.get("notice_score") == "daily_right" and
            presentation.get("source_score_step_count") == 18 and
            presentation.get("selected_component_keyframes") == 5 and
            presentation.get("omitted_transient_score_steps") ==
            presentation.get("source_score_step_count", 0) -
            presentation.get("selected_component_keyframes", 0) and
            presentation.get("minimum_post_refresh_hold_ms") == 750 and
            presentation.get("all_visible_frames_require_prior_refresh_completion") is True
        ),
        "touch_trace_sequences_only_after_visible_completion": trace.get("sequencing") == {
            "next_frame_blocked_until_completion": True,
            "failed_frame_retries_same_plan": True,
            "visible_frame_count": 8,
            "submitted_frame_count": 9,
        },
        "unavailable_system_faces_remain_fail_closed": trace.get("fail_closed") == [
            "menu_hold", "recording_active", "charging", "error", "upgrade_active"
        ],
        "browser_preview_is_runtime_inactive_component_only": (
            preview.get("status") == "PASS_BROWSER_COMPONENT_PREVIEW_FROM_TARGET_TRACE" and
            preview.get("runtime_resource_activated") is False and
            preview.get("component_layer_count") > 0
        ),
        "browser_target_trace_parity": parity.get("status") == "PASS_TOUCH_EMOTION_BROWSER_TARGET_PARITY_RUNTIME_INACTIVE",
        "v22_visual_route_is_runtime_inactive_200x200_component_candidate": (
            visual_route.get("status") == "PASS_V9_V22_TOUCH_EMOTION_ROUTE_RUNTIME_INACTIVE" and
            visual_route.get("runtime_resource_activated") is False and
            visual_route.get("physical_panel_acceptance") is False and
            visual_route.get("entry_settle_v9_static_difference_pixels") == {"entry": 0, "settle": 0} and
            visual_route.get("affectionate_art_pose") == "v22_warm"
        ),
        "v22_visual_route_has_actual_curious_and_warm_component_waypoints": (
            [item.get("emotion") for item in visual_route.get("v22_waypoints", []) if isinstance(item, dict)] ==
            ["calm", "curious", "warm", "curious", "calm"] and
            all(item.get("different_pixels") == 0 for item in visual_route.get("v22_waypoints", [])
                if isinstance(item, dict))
        ),
        "v22_visual_route_browser_target_plan_parity": (
            visual_route_parity.get("status") == "PASS_V9_V22_TOUCH_EMOTION_ROUTE_PARITY_RUNTIME_INACTIVE"
        ),
        "v22_visual_route_is_event_driven_micro_choreography": (
            visual_route.get("selection_policy") == {
                "mode": "explicit_event_performance",
                "random_emotion_selection": False,
                "automatic_cross_emotion_cycle": False,
                "daily_auto_only_runs_daily_micro_choreography": True,
                "familiar_touch_terminal_logical_emotion": "affectionate",
                "idle_settle_returns_to": "v9_daily",
            } and
            [item.get("id") for item in visual_route.get("performances", []) if isinstance(item, dict)] ==
            ["daily_micro", "familiar_touch", "idle_settle"] and
            set(visual_route.get("emotion_micro_choreography", {})) == {"daily", "curious", "affectionate", "calm"} and
            visual_route_parity.get("checks", {}).get(
                "event_driven_performances_stop_at_declared_targets_without_random_cycle") is True and
            visual_route_parity.get("checks", {}).get(
                "each_declared_emotion_has_registered_component_micro_choreography") is True and
            visual_route_parity.get("checks", {}).get(
                "browser_player_requires_explicit_event_and_never_auto_cycles_emotions") is True
        ),
        "v22_visual_route_actual_browser_render_inspection_passes": (
            browser_render_inspection.get("status") == "PASS_BROWSER_RENDER_INSPECTION_NATIVE_200X200" and
            browser_render_inspection.get("route", {}).get("sha256") == sha256(VISUAL_ROUTE) and
            len(browser_render_inspection.get("screenshots", [])) == 2 and
            all(item.get("expected_art_pose") in {"v9_daily", "v22_warm"}
                for item in browser_render_inspection.get("screenshots", []) if isinstance(item, dict))
        ),
        "target_build_compiled_interaction_session_without_flash": (
            TARGET_HEX.is_file() and TARGET_ELF.is_file() and TARGET_OBJECT.is_file() and
            "expression_interaction_session.c" in MAKEFILE.read_text(encoding="utf-8")
        ),
        "session_uses_component_score_not_face_drawing": (
            "comp_expression_rig_apply_score_step" in SESSION_SOURCE.read_text(encoding="utf-8") and
            "whole-face" not in SESSION_SOURCE.read_text(encoding="utf-8") and
            "return false;" in PROFILE.read_text(encoding="utf-8")
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.v9_rig_touch_emotion_machine_closure.v1",
        "status": "PASS_TOUCH_EMOTION_MACHINE_CLOSURE_RUNTIME_INACTIVE" if not failures else "FAIL_TOUCH_EMOTION_MACHINE_CLOSURE",
        "claim_scope": "simulated_touch_component_rig_browser_target_parity_and_wb55_compile_only_not_flash_or_physical_panel_acceptance",
        "runtime_resource_activated": False,
        "commands": commands,
        "checks": checks,
        "failures": failures,
        "artifacts": {
            "touch_trace": {"path": rel(TRACE), "sha256": sha256(TRACE)},
            "browser_preview": {"path": rel(PREVIEW), "sha256": sha256(PREVIEW)},
            "browser_target_parity": {"path": rel(PARITY), "sha256": sha256(PARITY)},
            "v22_visual_route_candidate": {"path": rel(VISUAL_ROUTE), "sha256": sha256(VISUAL_ROUTE)},
            "v22_visual_route_parity": {"path": rel(VISUAL_ROUTE_PARITY), "sha256": sha256(VISUAL_ROUTE_PARITY)},
            "v22_visual_route_browser_render_inspection": {
                "path": rel(BROWSER_RENDER_INSPECTION), "sha256": sha256(BROWSER_RENDER_INSPECTION)
            },
            "target_hex": {"path": rel(TARGET_HEX), "sha256": sha256(TARGET_HEX)},
            "target_elf": {"path": rel(TARGET_ELF), "sha256": sha256(TARGET_ELF)},
            "target_interaction_object": {"path": rel(TARGET_OBJECT), "sha256": sha256(TARGET_OBJECT)},
        },
        "physical_gate": {
            "white_black_hardware_pass_required_before_dynamic_flash_or_panel_acceptance": True,
            "current_state": "PENDING_FTS02_REPLACEMENT_OR_CROSS_SWAP_RAIL_EVIDENCE",
        },
    }
    WRITE.parent.mkdir(parents=True, exist_ok=True)
    WRITE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print("FAIL: touch/emotion machine closure", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: touch/emotion machine closure -> {rel(WRITE)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
