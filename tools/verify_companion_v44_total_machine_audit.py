#!/usr/bin/env python3
"""Close the V44 upper-art machine evidence before any human review window."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SHA = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V22_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V22_TRACE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-trace-contract-r5-20260721.json"
V43_GATE = ROOT / "docs/validation/companion-v43-recording-input-inward-source-gate-20260721.json"
V44_LAYOUT_GATE = ROOT / "docs/validation/companion-v44-blink-stable-center-layout-gate-20260721.json"
V44_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/v44-special-component-layout.json"
V44_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/target-score-attempt-01/v44-wb55-target-profile-plan.json"
V44_PROFILE = ROOT / "docs/validation/companion-v44-blink-stable-center-wb55-profile-host-20260721.json"
V44_PREVIEW = ROOT / "docs/validation/companion-v44-blink-stable-center-single-epaper-browser-wb55-preview-20260721.json"
V44_PARITY = ROOT / "docs/validation/companion-v44-blink-stable-center-wb55-component-parity-host-20260721.json"
V44_VISUAL = ROOT / "docs/validation/companion-v44-single-epaper-browser-visual-20260721.json"
V44_TOUCH = ROOT / "docs/validation/companion-v44-single-epaper-touch-host-20260721.json"
REPORT = ROOT / "docs/validation/companion-v44-total-machine-audit-20260721.json"
GAZE = {"daily_attention_center", "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing artifact: {path.relative_to(ROOT).as_posix()}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"artifact is not an object: {path.relative_to(ROOT).as_posix()}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def evidence(path: Path, status: str) -> dict[str, str]:
    value = load(path)
    require(value.get("status") == status, f"unexpected status in {rel(path)}")
    require(value.get("runtime_resource_activated") is False,
            f"runtime activation boundary drifted in {rel(path)}")
    return {"artifact": rel(path), "status": status, "sha256": sha256(path)}


def frame_key(item: dict[str, Any]) -> tuple[str, str, str, int]:
    score, cue, phase, duration = item.get("score"), item.get("cue"), item.get("phase"), item.get("duration_ms")
    require(isinstance(score, str) and isinstance(cue, str) and isinstance(phase, str) and
            isinstance(duration, int) and duration > 0, "malformed choreography frame")
    return score, cue, phase, duration


def replay_key(item: dict[str, Any]) -> tuple[str, str, int]:
    score, cue, duration = item.get("score"), item.get("cue"), item.get("duration_ms")
    require(isinstance(score, str) and isinstance(cue, str) and isinstance(duration, int) and duration > 0,
            "malformed parity replay frame")
    return score, cue, duration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()

    require(sha256(LOCKED) == LOCKED_SHA, "locked V9 source hash drifted")
    require(sha256(PROTECTED) == PROTECTED_SHA, "protected owner acceptance changed")

    v22 = load(V22_GATE)
    v22_layout = load(V22_LAYOUT)
    v22_trace = load(V22_TRACE)
    require(v22.get("status") == "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE" and
            v22.get("bridge_count") == 10 and v22.get("bridge_frame_count") == 72 and
            v22.get("runtime_resource_activated") is False, "accepted V22 daily regression drifted")
    bridges = v22_layout.get("bridges", [])
    require(v22_layout.get("locked_v9_source_sha256") == LOCKED_SHA and len(bridges) == 10 and
            sum(len(bridge.get("frames", [])) for bridge in bridges) == 72, "V22 bridge coverage drifted")
    require(v22_trace.get("status") == "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT" and
            v22_trace.get("trace_origin") == "synthetic_self_test_no_flash_no_panel" and
            v22_trace.get("bridge", {}).get("frame_count") == 7 and
            v22_trace.get("runtime_resource_activated") is False, "V22 upper-path trace drifted")

    v43_gate = evidence(V43_GATE, "PASS_V43_RECORDING_INPUT_INWARD_SOURCE_RUNTIME_INACTIVE")
    v44_layout_gate = evidence(V44_LAYOUT_GATE, "PASS_V44_BLINK_STABLE_CENTER_RUNTIME_INACTIVE")
    profile_evidence = evidence(V44_PROFILE, "PASS_V44_BLINK_STABLE_CENTER_WB55_PROFILE_RUNTIME_INACTIVE")
    preview_evidence = evidence(V44_PREVIEW, "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE")
    parity_evidence = evidence(V44_PARITY, "PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE")
    visual_evidence = evidence(V44_VISUAL, "PASS_V44_SINGLE_200X200_BROWSER_VIEWPORT_RUNTIME_INACTIVE")
    touch_evidence = evidence(V44_TOUCH, "PASS_V44_SINGLE_VIEWPORT_TOUCH_SWIPE_REPLAY_RUNTIME_INACTIVE")

    special_layout = load(V44_LAYOUT)
    trace = load(V44_TRACE)
    profile = load(V44_PROFILE)
    preview = load(V44_PREVIEW)
    parity = load(V44_PARITY)
    visual = load(V44_VISUAL)
    touch = load(V44_TOUCH)
    components = special_layout.get("components", [])
    require(special_layout.get("schema") == "companion.v44_special_component_export.v1" and
            len(components) == 50 and special_layout.get("locked_v9_source", {}).get("sha256") == LOCKED_SHA and
            special_layout.get("runtime_resource_activated") is False, "V44 special layout provenance drifted")
    source_recording = special_layout.get("source_sheets", {}).get("recording", {})
    require(source_recording.get("wave_direction") == "inward_toward_face_on_left",
            "recording source no longer declares inward wave direction")
    by_id = {int(component["component_id"]): component for component in components}
    require(set((569, 570, 571)).issubset(by_id), "recording input components are missing")
    for component_id in (569, 570, 571):
        component = by_id[component_id]
        require(component.get("source", {}).get("wave_direction") == "inward_toward_face_on_left" and
                component.get("base_position", [0, 0])[0] >= 160 and
                component.get("base_position", [0, 0])[0] + component.get("mask_size", [0, 0])[0] <= 196,
                f"recording component {component_id} escaped the inward right-side safe zone")

    require(trace.get("schema") == "companion.v44_expression_extension_wb55_target_profile_plan.v1" and
            trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED_SHA and
            trace.get("component_sources") == {"v22_face": 37, "v44_special_source": 50} and
            trace.get("runtime_resource_activated") is False and
            trace.get("active_candidate_binding") == "forbidden_until_v44_machine_audit_and_owner_review",
            "V44 target trace provenance or inactive boundary drifted")
    require(profile.get("component_count") == 87 and profile.get("expression_track_count") == 15 and
            profile.get("functional_track_count") == 4 and profile.get("story_count") == 21 and
            profile.get("preview_frame_count") == 93 and profile.get("five_gaze_states") == ["center", "left", "right", "up", "down"] and
            profile.get("recording_input_clear_of_face") is True and profile.get("wireless_dock_charging") is True and
            profile.get("sleep_zzz_only") is True, "V44 WB55 profile evidence drifted")
    require(parity.get("component_count") == 87 and parity.get("replayed_frame_count") == 93 and
            parity.get("source_packs") == ["v22_face", "v44_special_source"], "V44 browser/WB55 parity drifted")

    scores = trace.get("scores", [])
    require(isinstance(scores, list) and len(scores) == 21 and sum(len(score.get("steps", [])) for score in scores) == 93,
            "V44 score coverage drifted")
    trace_frames = [frame_key({"score": score.get("name"), **step}) for score in scores for step in score.get("steps", [])]
    preview_frames = preview.get("frames", [])
    parity_frames = parity.get("frames", [])
    require([frame_key(frame) for frame in preview_frames] == trace_frames and
            [replay_key(frame) for frame in parity_frames] == [replay_key(frame) for frame in preview_frames],
            "browser/WB55 replay sequence differs from the generated V44 plan")
    hidden = {name for name in preview.get("source_score_coverage", []) if name in GAZE}
    require(hidden == GAZE and preview.get("viewport_contract", {}).get("owner_visible_story_count") == 16,
            "V44 internal gaze regression scope drifted")

    html_path = ROOT / str(preview.get("dynamic_preview", {}).get("html", ""))
    require(html_path.is_file(), "V44 single viewport HTML is missing")
    html = html_path.read_text(encoding="utf-8")
    require(html.count('id="epaper-screen"') == 1 and html.count('data-canvas="200x200"') == 1 and
            html.count('data-touch-surface="true"') == 1 and "<canvas" not in html.lower() and
            "performance-card" not in html and "表情与状态总览" not in html and
            all(name not in html for name in GAZE), "V44 owner HTML exposes a forbidden fallback or hidden gaze story")
    require(visual.get("viewport", {}).get("owner_visible_story_count") == 16 and
            visual.get("viewport", {}).get("touch_surface") == "the_200x200_viewport_itself" and
            touch.get("canvas") == "200x200" and touch.get("random_selection") is False,
            "V44 single viewport visual/touch evidence drifted")

    menu = next(score for score in scores if score.get("name") == "menu_entry_notice")
    require(menu.get("withdraw_all_tracks_after_last_cue") is True and
            sum(step.get("duration_ms", 0) for step in menu.get("steps", [])) <= 500,
            "Menu entry cue is not finite before Menu UI ownership")
    require(all("no_whole_face_card" in item for item in [trace.get("non_claims", [])]),
            "V44 trace no-whole-face boundary missing")

    output = {
        "schema": "companion.v44_total_machine_audit.v1",
        "status": "GO_HUMAN_ACCEPTANCE_MACHINE_CLOSURE_COMPLETE",
        "authority": ["COMP-REQ-093", "COMP-REQ-250", "COMP-REQ-256", "COMP-REQ-258", "COMP-REQ-261", "COMP-REQ-262", "COMP-REQ-263"],
        "protected": {"locked_v9_source": {"path": rel(LOCKED), "sha256": LOCKED_SHA},
                      "prior_owner_acceptance": {"path": rel(PROTECTED), "sha256": PROTECTED_SHA}},
        "accepted_v22_daily_regression": {"artifact": rel(V22_GATE), "bridge_count": 10, "bridge_frame_count": 72,
                                           "trace_artifact": rel(V22_TRACE)},
        "v44_evidence": {"recording_source_gate": v43_gate, "layout_gate": v44_layout_gate,
                          "profile_host": profile_evidence, "browser_preview": preview_evidence,
                          "wb55_pixel_parity": parity_evidence, "single_viewport_visual": visual_evidence,
                          "touch_swipe_host": touch_evidence},
        "machine_verified": {"canvas": "200x200_1bpp", "component_count": 87, "special_component_count": 50,
                             "story_count": 21, "preview_frame_count": 93, "owner_visible_story_count": 16,
                             "source_packs": ["v22_face", "v44_special_source"], "recording_wave": "inward_toward_face_on_left",
                             "idle_gaze": "stable_center", "synchronized_blink": True,
                             "touch": "pointer_coordinate_to_registered_highlight_and_sparkle; release_center",
                             "swipe": "horizontal_or_vertical; positive_next_negative_previous",
                             "runtime_resource_activated": False},
        "non_claims": ["no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance", "no_human_acceptance"],
        "human_boundary": "Only after this machine closure may the canonical Chinese owner review open the current single viewport; that review is separate from physical panel acceptance.",
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V44 total machine audit closes source lineage, deterministic choreography, single viewport, touch/swipe replay, and WB55 parity ({destination}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
