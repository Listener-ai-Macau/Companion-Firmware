#!/usr/bin/env python3
"""Close the V40 two-track expression candidate's machine-only audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_OWNER = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_OWNER_SHA256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V22_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V38_REJECTED = ROOT / "docs/validation/companion-v9-expression-total-machine-audit-20260720.owner-review.json"
V40_EXPORT = ROOT / "docs/validation/companion-v40-functional-decoration-component-export-gate-20260720.json"
V40_LAYOUT = ROOT / "docs/validation/companion-v40-two-track-layout-gate-20260720.json"
V40_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v2/candidate/target-score-attempt-01/two-track-wb55-target-profile-plan.json"
V40_PROFILE = ROOT / "docs/validation/companion-v40-two-track-wb55-profile-host-20260720.json"
V40_PREVIEW = ROOT / "docs/validation/companion-v40-two-track-browser-wb55-preview-20260720.json"
V40_PARITY = ROOT / "docs/validation/companion-v40-two-track-wb55-component-parity-host-20260720.json"
REPORT = ROOT / "docs/validation/companion-v40-two-track-total-machine-audit-20260720.json"
FUNCTIONAL_IDS = set(range(557, 569))
MENU_IDS = {545, 546, 547}
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


def verify_artifact(path: Path, status: str) -> dict[str, Any]:
    value = load(path)
    require(value.get("status") == status, f"unexpected status in {rel(path)}")
    return {"artifact": rel(path), "status": status, "sha256": sha256(path)}


def frame_key(score: str, step: dict[str, Any]) -> tuple[str, str, int]:
    cue = step.get("cue")
    duration = step.get("duration_ms")
    require(isinstance(cue, str) and isinstance(duration, int) and duration > 0,
            f"invalid score frame in {score}")
    return score, cue, duration


def component_ids(layers: Any) -> set[int]:
    require(isinstance(layers, list), "frame layers must be a list")
    ids = []
    for layer in layers:
        require(isinstance(layer, dict) and isinstance(layer.get("component_id"), int) and
                isinstance(layer.get("offset"), list) and len(layer["offset"]) == 2,
                "frame layer is malformed")
        ids.append(layer["component_id"])
    require(len(ids) == len(set(ids)), "frame contains duplicate source components")
    return set(ids)


def find_score(scores: list[dict[str, Any]], name: str) -> dict[str, Any]:
    found = [score for score in scores if score.get("name") == name]
    require(len(found) == 1, f"missing or duplicate score: {name}")
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
            v22.get("runtime_resource_activated") is False,
            "accepted V22 choreography regression contract drifted")
    rejected = load(V38_REJECTED)
    require(rejected.get("status") == "REJECTED_OWNER_ARCHITECTURE_STEERING" and
            rejected.get("disposition", {}).get("runtime_binding") == "forbidden",
            "rejected V38 architecture evidence was not preserved")

    export = verify_artifact(V40_EXPORT, "PASS_COMPONENT_EXPORT_RUNTIME_INACTIVE")
    layout = verify_artifact(V40_LAYOUT, "PASS_V40_TWO_TRACK_LAYOUT_RUNTIME_INACTIVE")
    profile = verify_artifact(V40_PROFILE, "PASS_V40_TWO_TRACK_WB55_PROFILE_RUNTIME_INACTIVE")
    preview = verify_artifact(V40_PREVIEW, "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE")
    parity = verify_artifact(V40_PARITY, "PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE")
    trace = load(V40_TRACE)
    profile_data = load(V40_PROFILE)
    preview_data = load(V40_PREVIEW)
    parity_data = load(V40_PARITY)

    require(trace.get("schema") == "companion.v40_two_track_wb55_target_profile_plan.v1" and
            trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED_SHA256 and
            trace.get("runtime_resource_activated") is False and
            trace.get("active_candidate_binding") == "forbidden_until_v40_machine_audit_and_owner_review" and
            trace.get("component_sources") == {"v22_face": 37, "v40_special_source": 69},
            "V40 target profile provenance or inactive boundary drifted")
    require(profile_data.get("component_count") == 106 and profile_data.get("expression_track_count") == 6 and
            profile_data.get("functional_track_count") == 4 and profile_data.get("story_count") == 12 and
            profile_data.get("preview_frame_count") == 38 and profile_data.get("two_track_independence") is True and
            profile_data.get("runtime_resource_activated") is False,
            "V40 host profile evidence drifted")
    require(parity_data.get("component_count") == 106 and parity_data.get("replayed_frame_count") == 38 and
            parity_data.get("source_packs") == ["v22_face", "v40_special_source"] and
            parity_data.get("runtime_resource_activated") is False,
            "V40 browser/WB55 parity evidence drifted")

    scores = trace.get("scores")
    require(isinstance(scores, list) and len(scores) == 12, "V40 score vocabulary drifted")
    trace_frames: list[tuple[str, str, int]] = []
    for score in scores:
        name = score.get("name")
        steps = score.get("steps")
        require(isinstance(name, str) and isinstance(steps, list) and steps, "score is malformed")
        for step in steps:
            trace_frames.append(frame_key(name, step))
            expression_layers = component_ids(step.get("expression_layers"))
            functional_layers = component_ids(step.get("functional_layers"))
            final_layers = component_ids(step.get("layers"))
            nose_layers = [layer for layer in step["layers"] if layer.get("component_id") == 4]
            require(len(nose_layers) == 1 and nose_layers[0].get("offset") == [0, 0],
                    "V40 moved or omitted fixed V22 nose identity")
            require(not final_layers & QUARANTINED_IDS and not expression_layers & FUNCTIONAL_IDS,
                    "function state selected a quarantined face component or function component in expression track")
            require(final_layers == expression_layers | functional_layers and not expression_layers & functional_layers,
                    "V40 final plan is not the deterministic disjoint two-track union")
            if name == "menu_entry_notice":
                require(step.get("state_scene") == "touch" and functional_layers.issubset(MENU_IDS) and functional_layers,
                        "Menu may use only finite touch cue decoration")
            else:
                require(functional_layers.issubset(FUNCTIONAL_IDS),
                        "functional decoration used a non-V40 component")
    require(len(trace_frames) == 38, "V40 preview frame total drifted")

    recording_calm = find_score(scores, "recording_with_calm")["steps"][0]
    recording_warm = find_score(scores, "recording_with_warm")["steps"][0]
    require(component_ids(recording_calm["functional_layers"]) == {557} and
            component_ids(recording_warm["functional_layers"]) == {557} and
            component_ids(recording_calm["expression_layers"]) != component_ids(recording_warm["expression_layers"]),
            "same recording decoration does not remain independent of the selected face expression")
    menu = find_score(scores, "menu_entry_notice")
    policy = trace.get("menu_entry_policy")
    require(menu.get("withdraw_all_tracks_after_last_cue") is True and
            sum(step["duration_ms"] for step in menu["steps"]) == 460 and
            isinstance(policy, dict) and policy.get("state_scene") == "touch" and
            policy.get("maximum_expression_duration_ms") == 500 and
            policy.get("after_last_cue") == "withdraw_expression_and_functional_tracks_then_show_menu_ui" and
            policy.get("persistent_menu_score") == "forbidden" and
            policy.get("menu_ui_owns_screen_after_last_cue") is True,
            "Menu entry is not a finite cue followed by menu UI ownership")

    preview_frames = [frame_key(str(frame.get("score")), frame) for frame in preview_data.get("frames", []) if isinstance(frame, dict)]
    parity_frames = [frame_key(str(frame.get("score")), frame) for frame in parity_data.get("frames", []) if isinstance(frame, dict)]
    require(preview_data.get("frame_count") == 38 and preview_frames == trace_frames and parity_frames == trace_frames,
            "browser preview or WB55 replay sequence differs from the generated V40 score")
    dynamic = preview_data.get("dynamic_preview")
    require(isinstance(dynamic, dict), "V40 browser preview lacks a dynamic story player")
    html = ROOT / str(dynamic.get("html", ""))
    story_gifs = dynamic.get("story_gifs")
    require(isinstance(story_gifs, dict) and set(story_gifs) == {score["name"] for score in scores} and
            all(isinstance(path, str) and (ROOT / path).is_file() for path in story_gifs.values()),
            "browser preview must provide one dynamic artifact per story instead of one cross-state animation")
    html_text = html.read_text(encoding="ascii") if html.is_file() else ""
    require(html.is_file() and "all.filter(frame=>frame.dataset.score===select.value)" in html_text and
            "index+1>=frames.length&&select.value==='menu_entry_notice'" in html_text and "player.replaceChildren();return;" in html_text,
            "browser preview must loop only the selected story and withdraw the finite Menu cue instead of replaying a face behind Menu UI")

    output = {
        "schema": "companion.v40_two_track_total_machine_audit.v1",
        "status": "GO_HUMAN_ACCEPTANCE_MACHINE_CLOSURE_COMPLETE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242"],
        "protected": {"locked_v9_source": {"path": rel(LOCKED_V9), "sha256": LOCKED_SHA256},
                      "prior_owner_acceptance": {"path": rel(PROTECTED_OWNER), "sha256": PROTECTED_OWNER_SHA256}},
        "accepted_v22_daily_regression": {"artifact": rel(V22_GATE), "bridge_count": 10, "bridge_frame_count": 72},
        "rejected_v38_architecture_preserved": {"artifact": rel(V38_REJECTED), "status": rejected["status"]},
        "v40_evidence": {"functional_export": export, "two_track_layout": layout, "profile": profile,
                           "browser_preview": preview, "wb55_pixel_parity": parity},
        "machine_verified": {"canvas": "200x200_1bpp", "component_count": 106, "story_count": 12,
                             "preview_frame_count": 38, "final_plan": "deterministic_union(expression_track, functional_decoration_track)",
                             "same_recording_decoration_over_independent_calm_and_warm_faces": True,
                             "function_track_component_ids": sorted(FUNCTIONAL_IDS),
                             "quarantined_v38_face_component_ids": sorted(QUARANTINED_IDS),
                             "menu_entry": "touch / 3 frames / 460ms / withdraw both tracks / menu UI owns screen",
                             "selected_story_browser_player": True},
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_owner_review",
        "human_review_scope": "Review the selected-story 200x200 dynamic preview for readable functional decorations, independent face emotion, and finite menu entry before any runtime binding.",
        "non_claims": ["no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance"]
    }
    path = args.write.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: V40 total machine audit closes the inactive two-track candidate for human review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
