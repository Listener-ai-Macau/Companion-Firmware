#!/usr/bin/env python3
"""Close V42 machine-only source, choreography, browser, and WB55 parity evidence."""

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
V22 = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V22_TRACE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-trace-contract-r5-20260721.json"
V41_FAILED = ROOT / "docs/validation/companion-v41-directional-gaze-total-machine-audit-20260721.owner-review.json"
V41_CANCELLED = ROOT / "docs/validation/companion-v41-directional-gaze-total-machine-audit-20260721.owner-review-r2.json"
V42_R1_PRESERVATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/revision-1-machine-closure-preservation.json"
V42_R2_PRESERVATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/revision-2-machine-closure-preservation.json"
LAYOUT = ROOT / "docs/validation/companion-v42-expression-extension-layout-gate-20260721.json"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/candidate/target-score-attempt-01/v42-wb55-target-profile-plan.json"
PROFILE = ROOT / "docs/validation/companion-v42-expression-extension-wb55-profile-host-20260721.json"
PREVIEW = ROOT / "docs/validation/companion-v42-expression-extension-browser-wb55-preview-20260721.json"
PARITY = ROOT / "docs/validation/companion-v42-expression-extension-wb55-component-parity-host-20260721.json"
VISUAL = ROOT / "docs/validation/companion-v42-expression-extension-browser-visual-20260721.json"
TOUCH = ROOT / "docs/validation/companion-expression-touch-gaze-wb55-host-20260721.json"
NOTE = ROOT / "docs/companion_expression_emotion_system_cn.md"
REPORT = ROOT / "docs/validation/companion-v42-expression-extension-total-machine-audit-20260721.json"
GAZE = ("center", "left", "right", "up", "down")
HIDDEN_GAZE = {f"daily_attention_{direction}" for direction in GAZE}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing artifact: {rel(path)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"artifact is not an object: {rel(path)}")
    return value


def evidence(path: Path, status: str) -> dict[str, str]:
    value = load(path)
    require(value.get("status") == status, f"unexpected status in {rel(path)}")
    return {"artifact": rel(path), "status": status, "sha256": sha256(path)}


def frame_key(item: dict[str, Any]) -> tuple[str, str, int]:
    score, cue, duration = item.get("score"), item.get("cue"), item.get("duration_ms")
    require(isinstance(score, str) and isinstance(cue, str) and isinstance(duration, int) and duration > 0,
            "malformed replay frame")
    return score, cue, duration


def phase_key(item: dict[str, Any]) -> tuple[str, str, str]:
    score, cue, phase = item.get("score"), item.get("cue"), item.get("phase")
    require(isinstance(score, str) and isinstance(cue, str) and isinstance(phase, str) and phase,
            "malformed choreography phase")
    return score, cue, phase


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, default=LAYOUT)
    parser.add_argument("--trace", type=Path, default=TRACE)
    parser.add_argument("--profile", type=Path, default=PROFILE)
    parser.add_argument("--preview", type=Path, default=PREVIEW)
    parser.add_argument("--parity", type=Path, default=PARITY)
    parser.add_argument("--visual", type=Path, default=VISUAL)
    parser.add_argument("--touch", type=Path, default=TOUCH)
    parser.add_argument("--v22-trace", type=Path, default=V22_TRACE)
    parser.add_argument("--revision-label", default="r1")
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    layout_path = args.layout.resolve()
    trace_path = args.trace.resolve()
    profile_path = args.profile.resolve()
    preview_path = args.preview.resolve()
    parity_path = args.parity.resolve()
    visual_path = args.visual.resolve()
    touch_path = args.touch.resolve()
    v22_trace_path = args.v22_trace.resolve()
    require(sha256(LOCKED) == LOCKED_SHA, "locked V9 source hash drifted")
    require(sha256(PROTECTED) == PROTECTED_SHA, "protected prior owner acceptance changed")
    v22 = load(V22)
    require(v22.get("status") == "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE" and
            v22.get("bridge_count") == 10 and v22.get("bridge_frame_count") == 72 and
            v22.get("runtime_resource_activated") is False, "accepted V22 daily bridge regression drifted")
    v22_layout = load(V22_LAYOUT)
    bridges = v22_layout.get("bridges", [])
    require(v22_layout.get("locked_v9_source_sha256") == LOCKED_SHA and len(bridges) == 10 and
            sum(len(bridge.get("frames", [])) for bridge in bridges) == 72 and
            all([frame.get("changed_groups") for frame in bridge.get("frames", [])][1:5] ==
                [["primary_highlights"], ["sparkles"], ["brows"], ["lower_face"]] and
                any(frame.get("changed_groups") == ["target_pose"] and frame.get("duration_ms", 0) >= 750
                    for frame in bridge.get("frames", []))
                for bridge in bridges),
            "accepted V22 daily choreography order or visible hold threshold drifted")
    v22_trace = load(v22_trace_path)
    require(v22_trace.get("status") == "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT" and
            v22_trace.get("trace_origin") == "synthetic_self_test_no_flash_no_panel" and
            v22_trace.get("bridge", {}).get("frame_count") == 7,
            "V22 WB55 trace evidence is not the bounded upper-path self-test")
    failed = load(V41_FAILED)
    cancelled = load(V41_CANCELLED)
    require(failed.get("status") == "REJECTED_OWNER_REVIEW_DELIVERY_STEERING" and failed.get("selected") == "失败" and
            failed.get("disposition", {}).get("runtime_binding") == "forbidden" and
            cancelled.get("status") == "CANCELLED_OWNER_REVIEW_NO_DECISION" and cancelled.get("selected") == "Cancel" and
            cancelled.get("disposition", {}).get("runtime_binding") == "forbidden", "V41 inactive review evidence drifted")
    r1_preservation = load(V42_R1_PRESERVATION)
    require(r1_preservation.get("status") == "PRESERVED_INACTIVE_MACHINE_EVIDENCE" and
            r1_preservation.get("runtime_resource_activated") is False,
            "V42 r1 inactive revision evidence drifted")
    r2_preservation = load(V42_R2_PRESERVATION)
    require(r2_preservation.get("status") == "PRESERVED_INACTIVE_MACHINE_EVIDENCE" and
            r2_preservation.get("runtime_resource_activated") is False,
            "V42 r2 inactive revision evidence drifted")
    layout_evidence = evidence(layout_path, "PASS_V42_EXPRESSION_EXTENSION_LAYOUT_RUNTIME_INACTIVE")
    profile_evidence = evidence(profile_path, "PASS_V42_EXPRESSION_EXTENSION_WB55_PROFILE_RUNTIME_INACTIVE")
    preview_evidence = evidence(preview_path, "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE")
    parity_evidence = evidence(parity_path, "PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE")
    visual_evidence = evidence(visual_path, "PASS_V42_HEADLESS_BROWSER_VISUAL_CAPTURE")
    touch_evidence = evidence(touch_path, "PASS_TOUCH_COORDINATE_GAZE_RUNTIME_INACTIVE")
    v22_trace_evidence = evidence(v22_trace_path, "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT")
    layout = load(layout_path)
    trace = load(trace_path)
    profile = load(profile_path)
    preview = load(preview_path)
    parity = load(parity_path)
    visual = load(visual_path)
    touch = load(touch_path)
    require(trace.get("schema") == "companion.v42_expression_extension_wb55_target_profile_plan.v1" and
            trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED_SHA and
            trace.get("component_sources") == {"v22_face": 37, "v42_special_source": 48} and
            trace.get("runtime_resource_activated") is False and
            trace.get("active_candidate_binding") == "forbidden_until_v42_machine_audit_and_owner_review",
            "V42 profile provenance or inactive boundary drifted")
    require(profile.get("component_count") == 85 and profile.get("expression_track_count") == 15 and
            profile.get("functional_track_count") == 4 and profile.get("story_count") == 21 and
            profile.get("preview_frame_count") == 93 and profile.get("sleep_zzz_only") is True and
            profile.get("recording_input_clear_of_face") is True and profile.get("wireless_dock_charging") is True,
            "V42 WB55 host profile evidence drifted")
    require(parity.get("component_count") == 85 and parity.get("replayed_frame_count") == 93 and
            parity.get("source_packs") == ["v22_face", "v42_special_source"] and
            parity.get("runtime_resource_activated") is False, "V42 browser/WB55 parity evidence drifted")
    scores = trace.get("scores", [])
    require(isinstance(scores, list) and len(scores) == 21 and sum(len(score.get("steps", [])) for score in scores) == 93,
            "V42 score coverage drifted")
    trace_frames = [frame_key({"score": score.get("name"), **step}) for score in scores for step in score.get("steps", [])]
    preview_frames = preview.get("frames")
    parity_frames = parity.get("frames")
    require(isinstance(preview_frames, list) and isinstance(parity_frames, list) and
            [frame_key(frame) for frame in preview_frames] == trace_frames and
            [frame_key(frame) for frame in parity_frames] == trace_frames,
            "V42 browser or WB55 replay sequence differs from the generated score")
    trace_phases = [phase_key({"score": score.get("name"), **step}) for score in scores for step in score.get("steps", [])]
    require([phase_key(frame) for frame in preview_frames] == trace_phases,
            "V42 browser choreography phases differ from the generated score")
    endpoints: dict[str, str] = {}
    for direction in GAZE:
        name = f"daily_attention_{direction}"
        endpoint = [frame for frame in preview_frames if frame.get("score") == name and frame.get("index") == 2]
        require(len(endpoint) == 1 and isinstance(endpoint[0].get("target_1bpp_sha256"), str),
                f"V42 {direction} has no rendered endpoint")
        endpoints[direction] = endpoint[0]["target_1bpp_sha256"]
    require(len(set(endpoints.values())) == len(GAZE), "V42 five gaze endpoints are not pixel-distinct")
    chinese = preview.get("chinese_overview", {})
    visible = set(chinese.get("owner_visible_scores", [])) if isinstance(chinese, dict) else set()
    require(chinese.get("enabled") is True and chinese.get("story_count") == 21 and chinese.get("owner_visible_story_count") == 16 and
            not visible & HIDDEN_GAZE and len(visible) == 16 and HIDDEN_GAZE.issubset({score.get("name") for score in scores}),
            "V42 owner overview scope drifted")
    require(layout.get("functional_face_pixel_overlap") == {"recording": 0, "charging": 0} and
            layout.get("sleep_zzz_only") is True and set(layout.get("owner_visible_excludes", [])) == HIDDEN_GAZE,
            "V42 source/collision or owner-visible layout gate drifted")
    html = ROOT / str(preview.get("dynamic_preview", {}).get("html", ""))
    gifs = preview.get("dynamic_preview", {}).get("story_gifs", {})
    wall = preview.get("dynamic_preview", {}).get("all_performance_wall", {})
    html_text = html.read_text(encoding="utf-8") if html.is_file() else ""
    require(wall.get("enabled") is True and wall.get("owner_visible_story_count") == 16 and
            wall.get("simultaneous_autoplay") is True,
            "V42 all-performance dynamic wall is missing or not simultaneous")
    require(html.is_file() and '<html lang="zh-CN">' in html_text and "V9 组件表情系统预览" in html_text and
            "表情与状态总览" not in html_text and "全部动态编舞" in html_text and 'id="performance-wall"' in html_text and
            html_text.count('class="performance-card"') == 16 and html_text.count('data-touch-surface="true"') == 16 and
            'id="touch-pad"' not in html_text and "录音输入中" in html_text and "无线机座充电" in html_text and
            all(name not in html_text for name in HIDDEN_GAZE) and isinstance(gifs, dict) and len(gifs) == 21,
            "V42 Chinese owner browser preview is incomplete or exposes internal gaze cards")
    screenshot = ROOT / str(visual.get("screenshot", ""))
    require(visual.get("Chinese_owner_atlas_visible") is False and visual.get("owner_visible_story_count") == 16 and
            set(visual.get("hidden_internal_gaze", [])) == HIDDEN_GAZE and screenshot.is_file() and
            sha256(screenshot) == visual.get("screenshot_sha256") and visual.get("viewport_capture_px", {}).get("width", 0) >= 1200 and
            visual.get("viewport_capture_px", {}).get("height", 0) >= 1600 and visual.get("dark_pixel_count", 0) >= 1000 and
            visual.get("in_card_touch_gaze_visible") is True and visual.get("all_performance_wall_visible") is True,
            "V42 headless visual capture is missing, blank, or drifted")
    require(touch.get("canvas") == "200x200" and touch.get("mapping") == "direct pixel-derived legal highlight and sparkle offsets" and
            touch.get("surface") == "owner_visible_performance_card_face_box" and
            touch.get("release_behavior") == "center" and touch.get("eye_body_changed") is False and
            touch.get("nose_offset") == [0, 0] and touch.get("random_selection") is False and
            touch.get("gesture_surrogates") == ["tap", "drag", "release_to_center"] and
            touch.get("runtime_resource_activated") is False,
            "V42 touch-follow gaze evidence is missing or changes protected face components")
    touch_preview = preview.get("dynamic_preview", {}).get("touch_follow_gaze", {})
    require(touch_preview.get("enabled") is True and touch_preview.get("canvas") == "200x200" and
            touch_preview.get("surface") == "owner_visible_performance_card_face_box" and
            touch_preview.get("mode") == "in_card_pointer_coordinate_to_registered_offsets" and
            touch_preview.get("overlay_count", 0) >= 64 and touch_preview.get("base_story_count") == 16 and
            "each pointer x/y independently" in touch_preview.get("mapping", "") and
            touch_preview.get("gestures") == ["tap", "drag", "release_to_center"],
            "V42 browser touch-follow preview is incomplete")
    menu = [score for score in scores if score.get("name") == "menu_entry_notice"]
    require(len(menu) == 1 and menu[0].get("withdraw_all_tracks_after_last_cue") is True and
            sum(step.get("duration_ms", 0) for step in menu[0].get("steps", [])) == 460 and
            trace.get("menu_entry_policy", {}).get("maximum_expression_duration_ms") == 500,
            "V42 Menu entry is not finite before Menu UI ownership")
    note = NOTE.read_text(encoding="utf-8") if NOTE.is_file() else ""
    require(NOTE.is_file() and all(term in note for term in ("functional_event", "emotion", "attention", "energy", "interaction_memory", "无线机座", "ZZZ")),
            "V42 Chinese deterministic logic note is incomplete")
    output = {
        "schema": "companion.v42_expression_extension_total_machine_audit.v1",
        "status": "GO_HUMAN_ACCEPTANCE_MACHINE_CLOSURE_COMPLETE",
        "authority": ["COMP-REQ-093", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242", "COMP-REQ-243", "COMP-REQ-245", "COMP-REQ-246", "COMP-REQ-247", "COMP-REQ-248", "COMP-REQ-249", "COMP-REQ-250", "COMP-REQ-251", "COMP-REQ-253", "COMP-REQ-254", "COMP-REQ-256", "COMP-REQ-258"],
        "revision_label": args.revision_label,
        "protected": {"locked_v9_source": {"path": rel(LOCKED), "sha256": LOCKED_SHA},
                      "prior_owner_acceptance": {"path": rel(PROTECTED), "sha256": PROTECTED_SHA}},
        "accepted_v22_daily_regression": {"artifact": rel(V22), "bridge_count": 10, "bridge_frame_count": 72},
        "v41_inactive_evidence_preserved": {"failed_delivery_review": rel(V41_FAILED), "cancelled_rereview": rel(V41_CANCELLED)},
        "v42_r1_inactive_evidence_preserved": {"artifact": rel(V42_R1_PRESERVATION), "sha256": sha256(V42_R1_PRESERVATION)},
        "v42_r2_inactive_evidence_preserved": {"artifact": rel(V42_R2_PRESERVATION), "sha256": sha256(V42_R2_PRESERVATION)},
        "v42_evidence": {"layout": layout_evidence, "profile": profile_evidence, "browser_preview": preview_evidence,
                          "wb55_pixel_parity": parity_evidence, "browser_visual": visual_evidence,
                          "touch_follow_gaze": touch_evidence, "v22_trace": v22_trace_evidence,
                          "design_note": {"artifact": rel(NOTE), "sha256": sha256(NOTE)}},
        "machine_verified": {"canvas": "200x200_1bpp", "component_count": 85, "special_component_count": 48,
                             "story_count": 21, "preview_frame_count": 93, "owner_visible_story_count": 16,
                             "all_performance_wall": "16 owner-visible stories simultaneously autoplay",
                             "added_emotions": ["delighted", "bashful", "thoughtful", "focused"],
                             "recording_input_face_pixel_overlap": 0, "wireless_dock_face_pixel_overlap": 0,
                             "sleep_zzz_only": True, "five_gaze_states": list(GAZE), "endpoint_pixel_sha256": endpoints,
                             "touch_follow_gaze": {"canvas": "200x200_1bpp", "surface": "owner_visible_performance_card_face_box",
                                                   "mapping": "direct pixel-derived legal highlight and sparkle offsets", "release_target": "center",
                                                   "moves": "registered primary highlight and sparkle components only"},
                             "final_plan": "deterministic_union(expression_track,functional_decoration_track)",
                             "menu_entry": "touch / 3 frames / 460ms / withdraw both tracks / Menu UI owns screen"},
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden_until_owner_review",
        "human_review_scope": "Agent first opens the bound Chinese 200x200 V42 browser preview. The owner reviews added emotion readability, recording-input and wireless-dock meaning, ZZZ-only sleep, choreography, and finite Menu entry; this is not physical-screen acceptance or runtime activation.",
        "non_claims": ["no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance"],
    }
    destination = args.write.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: V42 machine audit closes source lineage, choreography, owner-visible scope, browser/WB55 parity, and finite Menu withdrawal for human review.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
