#!/usr/bin/env python3
"""Generate the inactive V41 two-track profile with five visible Daily gaze endpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import generate_companion_v40_two_track_target_profile as v40


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v3/candidate/two-track-layout.json"
V40_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v2/candidate/two-track-layout.json"
V39_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v1/candidate/two-track-layout.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V40_SPECIAL_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-rig-v2/candidate/functional-decoration-component-layout.json"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v41_directional_gaze_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v41_directional_gaze_candidate_profile.c"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v3/candidate/target-score-attempt-01/v41-wb55-target-profile-plan.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
NO_FUNCTIONAL = 0xFF
GAZE_ORDER = ("center", "left", "right", "up", "down")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def attention_layers(components: dict[int, dict[str, Any]], base_face: list[int],
                     endpoint: dict[str, list[int]]) -> list[dict[str, Any]]:
    primary = tuple(endpoint["primary"])
    sparkle = tuple(endpoint["sparkle"])
    require(len(primary) == 2 and len(sparkle) == 2 and
            all(isinstance(value, int) for value in primary + sparkle),
            "V41 attention endpoint offsets are malformed")
    layers: list[dict[str, Any]] = []
    for component_id in base_face:
        if component_id in {1, 5}:
            offset = primary
        elif component_id in {3, 7}:
            offset = sparkle
        else:
            offset = (0, 0)
        layers.append(v40.make_layer(components, component_id, offset))
    return v40.sort_layers(components, layers)


def attention_tracks(components: dict[int, dict[str, Any]], inherited_expression: dict[str, Any],
                     layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    specification = layout["expression_track"]["attention_demonstrations"]
    endpoints = specification["endpoint_offsets"]
    base_face = inherited_expression["expression_track"]["performances"]["calm_presence"]["base_face"]
    result: dict[str, dict[str, Any]] = {}
    for direction in GAZE_ORDER:
        endpoint = endpoints.get(direction)
        require(isinstance(endpoint, dict), f"missing V41 {direction} endpoint")
        center_layers = attention_layers(components, base_face, endpoints["center"])
        endpoint_layers = attention_layers(components, base_face, endpoint)
        prefix = f"daily_attention_{direction}"
        if direction == "center":
            rows = [
                ("gaze_center_entry", 220, "center", center_layers, "entry"),
                ("gaze_center_micro", 260, "center", center_layers, "lead"),
                ("gaze_center_hold", 900, "center", endpoint_layers, "hold"),
            ]
        else:
            rows = [
                (f"gaze_{direction}_depart", 180, "center", center_layers, "entry"),
                (f"gaze_{direction}_arrive", 260, direction, endpoint_layers, "lead"),
                (f"gaze_{direction}_hold", 900, direction, endpoint_layers, "hold"),
            ]
        result[prefix] = {
            "name": prefix,
            "kind": "attention_demonstration",
            "gaze_endpoint": direction,
            "steps": [
                {"cue": cue, "duration_ms": duration, "phase": phase, "scene": "daily",
                 "emotion": "calm", "attention": attention, "layers": layers}
                for cue, duration, attention, layers, phase in rows
            ],
        }
    return result


def gaze_stories(components: dict[int, dict[str, Any]], tracks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    for name, track in tracks.items():
        steps = []
        for index, step in enumerate(track["steps"]):
            layers = v40.sort_layers(components, list(step["layers"]))
            nose = [layer for layer in layers if layer["component_id"] == 4]
            require(len(layers) <= 16 and len(nose) == 1 and nose[0]["offset"] == [0, 0],
                    f"V41 {name} moved or omitted the fixed V22 nose")
            steps.append({
                "cue": step["cue"], "duration_ms": step["duration_ms"], "state_scene": "daily",
                "emotion": step["emotion"], "attention": step["attention"],
                "expression_track": name, "expression_step": index,
                "functional_decoration_track": None, "functional_step": None,
                "expression_layers": step["layers"], "functional_layers": [], "layers": layers,
            })
        stories.append({"name": name, "expression_track": name, "functional_decoration_track": None,
                        "withdraw_all_tracks_after_last_cue": False, "steps": steps})
    return stories


def build_artifacts() -> dict[Path, str]:
    layout = v40.load(LAYOUT)
    inherited_v40 = v40.load(V40_LAYOUT)
    inherited_expression = v40.load(V39_LAYOUT)
    v22 = v40.load(V22_LAYOUT)
    v40_special = v40.load(V40_SPECIAL_LAYOUT)
    require(layout.get("schema") == "companion.v41_two_track_directional_gaze_layout.v1" and
            layout.get("revision") == 41 and layout.get("status") == "CANDIDATE_TRACK_MODEL_VERSIONED_RUNTIME_INACTIVE" and
            layout.get("locked_v9_source", {}).get("sha256") == LOCKED and
            layout.get("composition", {}).get("runtime_binding") == "forbidden_until_v41_machine_audit_and_owner_review",
            "V41 layout identity or inactive boundary drifted")
    inherited = layout.get("inherited_v40_two_track_layout")
    require(isinstance(inherited, dict) and inherited.get("path") == rel(V40_LAYOUT) and
            inherited.get("sha256") == sha256(V40_LAYOUT),
            "V41 must retain the exact V40 source-track authority")
    source_authority = layout.get("source_authority")
    require(isinstance(source_authority, dict) and
            source_authority.get("v22_face_layout", {}).get("path") == rel(V22_LAYOUT) and
            source_authority.get("v22_face_layout", {}).get("sha256") == sha256(V22_LAYOUT) and
            source_authority.get("v40_special_source_layout", {}).get("path") == rel(V40_SPECIAL_LAYOUT) and
            source_authority.get("v40_special_source_layout", {}).get("sha256") == sha256(V40_SPECIAL_LAYOUT),
            "V41 source authority hash drifted")
    demonstrations = layout.get("expression_track", {}).get("attention_demonstrations", {})
    require(demonstrations.get("required_states") == list(GAZE_ORDER) and
            demonstrations.get("component_ids") == {"left_primary": 1, "left_sparkle": 3,
                                                       "right_primary": 5, "right_sparkle": 7,
                                                       "fixed_nose": 4},
            "V41 must retain all five source-only attention endpoints")

    v40.ATTENTION_ENUM.update({
        "up": "COMP_EXPRESSION_RIG_ATTENTION_UP",
        "down": "COMP_EXPRESSION_RIG_ATTENTION_DOWN",
    })
    components = v40.normalize_components(v22, v40_special)
    by_id = {component["component_id"]: component for component in components}
    expressions = v40.expression_steps(by_id, inherited_expression)
    directional_tracks = attention_tracks(by_id, inherited_expression, layout)
    expressions.update(directional_tracks)
    functional = v40.functional_steps(by_id, inherited_v40)
    base_stories = v40.build_stories(by_id, {name: expressions[name] for name in (
        "calm_presence", "warm_presence", "curious_question", "alert_exclamation", "playful_presence", "sleepy_presence")}, functional)
    stories = base_stories[:6] + gaze_stories(by_id, directional_tracks) + base_stories[6:]
    require(len(expressions) == 11 and len(functional) == 5 and len(stories) == 17 and
            sum(len(story["steps"]) for story in stories) == 53,
            "V41 expression, functional, directional, or story coverage drifted")
    max_mask = max(component["mask_bytes"] for component in components)
    trace = {
        "schema": "companion.v41_two_track_directional_gaze_wb55_target_profile_plan.v1",
        "status": "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242", "COMP-REQ-243"],
        "locked_v9_source_sha256": LOCKED,
        "track_layout": rel(LAYOUT), "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_v41_machine_audit_and_owner_review",
        "component_sources": {"v22_face": 37, "v40_special_source": 69}, "max_component_mask_bytes": max_mask,
        "two_track_contract": {"expression_driven_only_by": ["emotion", "attention", "energy", "interaction_memory"],
                               "functional_driven_only_by": ["functional_event"],
                               "final_plan": "deterministic_union(expression_track, functional_decoration_track)",
                               "quarantined_rejected_v38_face_components": [554, 555, 556]},
        "expression_tracks": list(expressions.values()),
        "functional_decoration_tracks": [functional[name] for name in ("recording_input", "bottom_connector_charging", "upgrade_progress", "error_caution")],
        "directional_gaze": {"states": list(GAZE_ORDER), "endpoint_offsets": demonstrations["endpoint_offsets"],
                             "component_ids": demonstrations["component_ids"], "fixed_nose": {"component_id": 4, "offset": [0, 0]},
                             "selection": "deterministic; no random gaze selection"},
        "menu_entry_track": functional["menu_entry_notice"], "scores": stories,
        "preview_zh": layout["preview_zh"],
        "menu_entry_policy": {"state_scene": "touch", "maximum_expression_duration_ms": 500,
                              "after_last_cue": "withdraw_expression_and_functional_tracks_then_show_menu_ui",
                              "persistent_menu_score": "forbidden", "menu_ui_owns_screen_after_last_cue": True},
        "non_claims": ["no_v40_profile_promotion", "no_whole_face_card", "no_code_drawn_face", "no_runtime_binding", "no_panel_or_driver_change"],
    }
    header = (v40.render_header(len(components), len(expressions), 4, len(stories), max_mask)
              .replace("tools/generate_companion_v40_two_track_target_profile.py",
                       "tools/generate_companion_v41_directional_gaze_target_profile.py")
              .replace("V40", "V41").replace("v40", "v41"))
    source = (v40.render_source(components, expressions, functional, stories)
              .replace("V39", "V41").replace("v39", "v41")
              .replace("expression_rig_v41_two_track_candidate_profile.h",
                       "expression_rig_v41_directional_gaze_candidate_profile.h"))
    return {HEADER: header, SOURCE: source, TRACE: json.dumps(trace, indent=2, ensure_ascii=False) + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    drifted = [path for path, content in artifacts.items() if args.check and
               (not path.is_file() or path.read_text(encoding="utf-8") != content)]
    if drifted:
        for path in drifted:
            print(f"ERROR: generated artifact drifted: {rel(path)}")
        return 1
    if not args.check:
        for path, content in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("PASS: generated inactive V41 two-track profile with 106 source components, five Daily gaze endpoints, 17 stories and 53 preview frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
