#!/usr/bin/env python3
"""Close V41's machine-only directional-gaze and Chinese-overview audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_OWNER = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_OWNER_SHA256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V22_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V40_REJECTED = ROOT / "docs/validation/companion-v40-two-track-total-machine-audit-20260720.owner-review.json"
LAYOUT = ROOT / "docs/validation/companion-v41-directional-gaze-layout-gate-20260721.json"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v3/candidate/target-score-attempt-01/v41-wb55-target-profile-plan.json"
PROFILE = ROOT / "docs/validation/companion-v41-directional-gaze-wb55-profile-host-20260721.json"
PREVIEW = ROOT / "docs/validation/companion-v41-directional-gaze-browser-wb55-preview-20260721.json"
PARITY = ROOT / "docs/validation/companion-v41-directional-gaze-wb55-component-parity-host-20260721.json"
BROWSER_VISUAL = ROOT / "docs/validation/companion-v41-directional-gaze-browser-visual-20260721.json"
DESIGN_NOTE = ROOT / "docs/companion_expression_emotion_system_cn.md"
REPORT = ROOT / "docs/validation/companion-v41-directional-gaze-total-machine-audit-20260721.json"
GAZE = ("center", "left", "right", "up", "down")
EXPECTED_ENDPOINTS = {
    "center": {"primary": [1, 0], "sparkle": [1, 0]},
    "left": {"primary": [-2, 2], "sparkle": [-5, 3]},
    "right": {"primary": [5, 2], "sparkle": [5, 3]},
    "up": {"primary": [1, -3], "sparkle": [1, -5]},
    "down": {"primary": [1, 4], "sparkle": [1, 5]},
}
FUNCTIONAL_IDS = set(range(557, 569))
QUARANTINED_IDS = {554, 555, 556}


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


def frame_key(score: str, step: dict[str, Any]) -> tuple[str, str, int]:
    cue, duration = step.get("cue"), step.get("duration_ms")
    require(isinstance(cue, str) and isinstance(duration, int) and duration > 0, "malformed score frame")
    return score, cue, duration


def ids(layers: Any) -> set[int]:
    require(isinstance(layers, list), "layers must be a list")
    values = []
    for layer in layers:
        require(isinstance(layer, dict) and isinstance(layer.get("component_id"), int) and
                isinstance(layer.get("offset"), list) and len(layer["offset"]) == 2,
                "malformed source layer")
        values.append(layer["component_id"])
    require(len(values) == len(set(values)), "source plan has duplicate components")
    return set(values)


def layer_offset(layers: list[dict[str, Any]], component_id: int) -> list[int]:
    matches = [layer.get("offset") for layer in layers if layer.get("component_id") == component_id]
    require(len(matches) == 1 and isinstance(matches[0], list) and len(matches[0]) == 2,
            f"missing or duplicate component {component_id}")
    return matches[0]


def score(scores: list[dict[str, Any]], name: str) -> dict[str, Any]:
    found = [value for value in scores if value.get("name") == name]
    require(len(found) == 1, f"missing or duplicate score {name}")
    return found[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    require(sha256(LOCKED_V9) == LOCKED_SHA256, "locked V9 source hash drifted")
    require(sha256(PROTECTED_OWNER) == PROTECTED_OWNER_SHA256, "protected prior owner acceptance changed")
    v22 = load(V22_GATE)
    require(v22.get("status") == "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE" and
            v22.get("bridge_count") == 10 and v22.get("bridge_frame_count") == 72 and
            v22.get("runtime_resource_activated") is False, "accepted V22 daily bridge regression drifted")
    rejected = load(V40_REJECTED)
    require(rejected.get("status") == "REJECTED_OWNER_DIRECTIONAL_GAZE_AND_CHINESE_OVERVIEW_STEERING" and
            rejected.get("selected") == "失败" and rejected.get("disposition", {}).get("runtime_binding") == "forbidden",
            "V40 owner rejection must remain preserved inactive evidence")
    layout = evidence(LAYOUT, "PASS_V41_DIRECTIONAL_GAZE_LAYOUT_RUNTIME_INACTIVE")
    profile = evidence(PROFILE, "PASS_V41_DIRECTIONAL_GAZE_WB55_PROFILE_RUNTIME_INACTIVE")
    preview = evidence(PREVIEW, "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE")
    parity = evidence(PARITY, "PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE")
    browser_visual = evidence(BROWSER_VISUAL, "PASS_V41_HEADLESS_BROWSER_VISUAL_CAPTURE")
    trace = load(TRACE)
    profile_data, preview_data, parity_data = load(PROFILE), load(PREVIEW), load(PARITY)
    require(trace.get("schema") == "companion.v41_two_track_directional_gaze_wb55_target_profile_plan.v1" and
            trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED_SHA256 and
            trace.get("component_sources") == {"v22_face": 37, "v40_special_source": 69} and
            trace.get("runtime_resource_activated") is False and
            trace.get("active_candidate_binding") == "forbidden_until_v41_machine_audit_and_owner_review",
            "V41 profile provenance or inactive boundary drifted")
    require(profile_data.get("component_count") == 106 and profile_data.get("expression_track_count") == 11 and
            profile_data.get("functional_track_count") == 4 and profile_data.get("story_count") == 17 and
            profile_data.get("preview_frame_count") == 53 and profile_data.get("five_gaze_states") == list(GAZE) and
            profile_data.get("fixed_v22_nose") is True and profile_data.get("two_track_independence") is True,
            "V41 WB55 host profile evidence drifted")
    require(parity_data.get("component_count") == 106 and parity_data.get("replayed_frame_count") == 53 and
            parity_data.get("source_packs") == ["v22_face", "v40_special_source"] and
            parity_data.get("runtime_resource_activated") is False,
            "V41 browser/WB55 parity evidence drifted")
    require(trace.get("directional_gaze", {}).get("states") == list(GAZE) and
            trace.get("directional_gaze", {}).get("endpoint_offsets") == EXPECTED_ENDPOINTS and
            trace.get("directional_gaze", {}).get("fixed_nose") == {"component_id": 4, "offset": [0, 0]},
            "V41 direction-source contract drifted")
    scores = trace.get("scores")
    require(isinstance(scores, list) and len(scores) == 17, "V41 score vocabulary drifted")
    trace_frames: list[tuple[str, str, int]] = []
    for item in scores:
        name, steps = item.get("name"), item.get("steps")
        require(isinstance(name, str) and isinstance(steps, list) and steps, "malformed V41 score")
        for step in steps:
            trace_frames.append(frame_key(name, step))
            expression_ids = ids(step.get("expression_layers"))
            functional_ids = ids(step.get("functional_layers"))
            final_ids = ids(step.get("layers"))
            require(layer_offset(step["layers"], 4) == [0, 0], "V41 moved the fixed V22 nose")
            require(not final_ids & QUARANTINED_IDS and not expression_ids & FUNCTIONAL_IDS and
                    final_ids == expression_ids | functional_ids and not expression_ids & functional_ids,
                    "V41 broke independent expression/function source composition")
    require(len(trace_frames) == 53, "V41 preview frame total drifted")
    endpoint_hashes: dict[str, str] = {}
    for direction in GAZE:
        item = score(scores, f"daily_attention_{direction}")
        steps = item.get("steps")
        require(isinstance(steps, list) and len(steps) == 3 and item.get("functional_decoration_track") is None,
                f"V41 {direction} is not an independently replayable attention demonstration")
        endpoint = steps[2]
        require(endpoint.get("attention") == direction and layer_offset(endpoint["layers"], 1) == EXPECTED_ENDPOINTS[direction]["primary"] and
                layer_offset(endpoint["layers"], 5) == EXPECTED_ENDPOINTS[direction]["primary"] and
                layer_offset(endpoint["layers"], 3) == EXPECTED_ENDPOINTS[direction]["sparkle"] and
                layer_offset(endpoint["layers"], 7) == EXPECTED_ENDPOINTS[direction]["sparkle"],
                f"V41 {direction} endpoint does not use its legal registered highlight/sparkle offsets")
    preview_frames = preview_data.get("frames")
    parity_frames = parity_data.get("frames")
    require(isinstance(preview_frames, list) and isinstance(parity_frames, list), "V41 preview/parity frame lists missing")
    require([frame_key(str(frame.get("score")), frame) for frame in preview_frames] == trace_frames and
            [frame_key(str(frame.get("score")), frame) for frame in parity_frames] == trace_frames,
            "browser preview or WB55 replay sequence differs from the generated V41 score")
    for direction in GAZE:
        name = f"daily_attention_{direction}"
        found = [frame for frame in preview_frames if frame.get("score") == name and frame.get("index") == 2]
        require(len(found) == 1 and isinstance(found[0].get("target_1bpp_sha256"), str),
                f"V41 {direction} has no rendered 200x200 endpoint")
        endpoint_hashes[direction] = found[0]["target_1bpp_sha256"]
    require(len(set(endpoint_hashes.values())) == len(GAZE),
            "V41 five gaze endpoints do not produce pairwise-distinct 200x200 pixels")
    chinese = preview_data.get("chinese_overview")
    metadata = chinese.get("metadata") if isinstance(chinese, dict) else None
    require(isinstance(chinese, dict) and chinese.get("enabled") is True and chinese.get("story_count") == 17 and
            isinstance(metadata, dict) and isinstance(metadata.get("stories"), dict) and
            set(metadata["stories"]) == {value[0] for value in trace_frames},
            "V41 Chinese overview does not cover every generated score")
    html = ROOT / str(preview_data.get("dynamic_preview", {}).get("html", ""))
    gifs = preview_data.get("dynamic_preview", {}).get("story_gifs")
    html_text = html.read_text(encoding="utf-8") if html.is_file() else ""
    require(html.is_file() and '<html lang="zh-CN">' in html_text and "V9 组件表情系统预览" in html_text and
            "表情与状态总览" in html_text and "all.filter(frame=>frame.dataset.score===select.value)" in html_text and
            "index+1>=frames.length&&select.value==='menu_entry_notice'" in html_text and "player.replaceChildren();return;" in html_text and
            isinstance(gifs, dict) and set(gifs) == {value[0] for value in trace_frames} and
            all(isinstance(path, str) and (ROOT / path).is_file() for path in gifs.values()),
            "V41 Chinese selected-story preview, full atlas, or finite Menu withdrawal is incomplete")
    visual_data = load(BROWSER_VISUAL)
    visual_screenshot = ROOT / str(visual_data.get("screenshot", ""))
    require(visual_data.get("Chinese_full_atlas_visible") is True and visual_data.get("runtime_resource_activated") is False and
            visual_screenshot.is_file() and sha256(visual_screenshot) == visual_data.get("screenshot_sha256") and
            visual_data.get("viewport_capture_px", {}).get("width", 0) >= 1200 and
            visual_data.get("viewport_capture_px", {}).get("height", 0) >= 3000 and
            visual_data.get("dark_pixel_count", 0) >= 1000,
            "V41 headless visual capture is missing, blank, or has drifted")
    menu = score(scores, "menu_entry_notice")
    require(menu.get("withdraw_all_tracks_after_last_cue") is True and
            sum(step["duration_ms"] for step in menu["steps"]) == 460 and
            trace.get("menu_entry_policy", {}).get("maximum_expression_duration_ms") == 500 and
            trace.get("menu_entry_policy", {}).get("after_last_cue") == "withdraw_expression_and_functional_tracks_then_show_menu_ui",
            "V41 Menu entry is not a finite cue followed by Menu UI ownership")
    note = DESIGN_NOTE.read_text(encoding="utf-8") if DESIGN_NOTE.is_file() else ""
    require(DESIGN_NOTE.is_file() and all(term in note for term in ("functional_event", "emotion", "attention", "energy", "interaction_memory", "菜单")),
            "V41 Chinese deterministic emotion-system design note is incomplete")
    output = {
        "schema": "companion.v41_directional_gaze_total_machine_audit.v1",
        "status": "GO_HUMAN_ACCEPTANCE_MACHINE_CLOSURE_COMPLETE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242", "COMP-REQ-243"],
        "protected": {"locked_v9_source": {"path": rel(LOCKED_V9), "sha256": LOCKED_SHA256},
                      "prior_owner_acceptance": {"path": rel(PROTECTED_OWNER), "sha256": PROTECTED_OWNER_SHA256}},
        "accepted_v22_daily_regression": {"artifact": rel(V22_GATE), "bridge_count": 10, "bridge_frame_count": 72},
        "v40_rejection_preserved": {"artifact": rel(V40_REJECTED), "status": rejected["status"]},
        "v41_evidence": {"directional_layout": layout, "profile": profile, "browser_preview": preview, "browser_visual": browser_visual, "wb55_pixel_parity": parity,
                         "design_note": {"artifact": rel(DESIGN_NOTE), "sha256": sha256(DESIGN_NOTE)}},
        "machine_verified": {"canvas": "200x200_1bpp", "component_count": 106, "story_count": 17,
                             "preview_frame_count": 53, "five_gaze_states": list(GAZE),
                             "endpoint_pixel_sha256": endpoint_hashes, "fixed_v22_nose": True,
                             "Chinese_full_atlas": True, "deterministic_selection_documented": True,
                             "final_plan": "deterministic_union(expression_track, functional_decoration_track)",
                             "menu_entry": "touch / 3 frames / 460ms / withdraw both tracks / Menu UI owns screen"},
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_owner_review",
        "human_review_scope": "Review the Chinese 200x200 selected-story player and full atlas: five gaze endpoints, every listed emotion/performance, readable function decoration, and finite Menu entry. This is not physical-screen acceptance or runtime activation.",
        "non_claims": ["no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance"],
    }
    output_path = args.write.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: V41 machine audit closes five source-only gaze endpoints, Chinese overview, browser/WB55 parity, and finite Menu withdrawal for human review.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
