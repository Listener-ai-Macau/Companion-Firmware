#!/usr/bin/env python3
"""Gate V41's source-only five-direction gaze and Chinese review layout."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v3/candidate/two-track-layout.json"
V40_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v2/candidate/two-track-layout.json"
V39_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v1/candidate/two-track-layout.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V40_SPECIAL = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-rig-v2/candidate/functional-decoration-component-layout.json"
REPORT = ROOT / "docs/validation/companion-v41-directional-gaze-layout-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
GAZE = ("center", "left", "right", "up", "down")
EXPECTED_ENDPOINTS = {
    "center": {"primary": [1, 0], "sparkle": [1, 0]},
    "left": {"primary": [-2, 2], "sparkle": [-5, 3]},
    "right": {"primary": [5, 2], "sparkle": [5, 3]},
    "up": {"primary": [1, -3], "sparkle": [1, -5]},
    "down": {"primary": [1, 4], "sparkle": [1, 5]},
}
STORIES = {"calm_presence", "warm_presence", "curious_question", "alert_exclamation", "playful_presence", "sleepy_presence",
           "daily_attention_center", "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down",
           "recording_with_calm", "recording_with_warm", "charging_with_calm", "upgrade_with_playful", "error_with_calm", "menu_entry_notice"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, default=LAYOUT)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    layout_path = args.layout.resolve()
    layout = load(layout_path)
    require(layout.get("schema") == "companion.v41_two_track_directional_gaze_layout.v1" and
            layout.get("status") == "CANDIDATE_TRACK_MODEL_VERSIONED_RUNTIME_INACTIVE" and
            layout.get("revision") == 41 and layout.get("locked_v9_source", {}).get("sha256") == LOCKED,
            "V41 layout identity or locked V9 authority drifted")
    require(layout.get("composition", {}).get("canvas") == "200x200_1bpp_white_is_one_msb" and
            layout.get("composition", {}).get("final_plan") == "deterministic_union(expression_track, functional_decoration_track)" and
            layout.get("composition", {}).get("maximum_layers") == 16 and
            layout.get("composition", {}).get("no_mask_synthesis") is True and
            layout.get("composition", {}).get("runtime_binding") == "forbidden_until_v41_machine_audit_and_owner_review",
            "V41 must remain an inactive component-only two-track candidate")
    inherited_v40 = layout.get("inherited_v40_two_track_layout")
    require(isinstance(inherited_v40, dict) and inherited_v40.get("path") == rel(V40_LAYOUT) and
            inherited_v40.get("sha256") == sha256(V40_LAYOUT),
            "V41 source tracks are not bound to the exact rejected-but-preserved V40 authority")
    authority = layout.get("source_authority")
    require(isinstance(authority, dict) and
            authority.get("v22_face_layout", {}).get("path") == rel(V22_LAYOUT) and
            authority.get("v22_face_layout", {}).get("sha256") == sha256(V22_LAYOUT) and
            authority.get("v40_special_source_layout", {}).get("path") == rel(V40_SPECIAL) and
            authority.get("v40_special_source_layout", {}).get("sha256") == sha256(V40_SPECIAL),
            "V41 source component lineage drifted")
    expression = layout.get("expression_track")
    require(isinstance(expression, dict) and expression.get("driven_only_by") ==
            ["emotion", "attention", "energy", "interaction_memory"],
            "V41 expression track must retain deterministic state-only inputs")
    inherited_expression = expression.get("inherited_performance_layout")
    require(isinstance(inherited_expression, dict) and inherited_expression.get("path") == rel(V39_LAYOUT) and
            inherited_expression.get("sha256") == sha256(V39_LAYOUT),
            "V41 must retain V22/V39 expression-performance authority")
    gaze = expression.get("attention_demonstrations")
    require(isinstance(gaze, dict) and gaze.get("required_states") == list(GAZE) and
            gaze.get("component_ids") == {"left_primary": 1, "left_sparkle": 3,
                                           "right_primary": 5, "right_sparkle": 7, "fixed_nose": 4} and
            gaze.get("endpoint_offsets") == EXPECTED_ENDPOINTS,
            "V41 five-direction source-component endpoints drifted")
    components = {item.get("component_id"): item for item in load(V22_LAYOUT).get("components", []) if isinstance(item, dict)}
    require(set((1, 3, 4, 5, 7)).issubset(components), "V22 attention source components are missing")
    for direction, endpoint in EXPECTED_ENDPOINTS.items():
        for component_id, offset in ((1, endpoint["primary"]), (5, endpoint["primary"]),
                                     (3, endpoint["sparkle"]), (7, endpoint["sparkle"])):
            allowed = components[component_id].get("offset_range", {})
            require(allowed.get("min", [1, 1])[0] <= offset[0] <= allowed.get("max", [-1, -1])[0] and
                    allowed.get("min", [1, 1])[1] <= offset[1] <= allowed.get("max", [-1, -1])[1],
                    f"V41 {direction} offset escapes registered source component {component_id}")
    signatures = {direction: tuple(endpoint["primary"] + endpoint["sparkle"])
                  for direction, endpoint in EXPECTED_ENDPOINTS.items()}
    require(all(signatures[first] != signatures[second] for first, second in combinations(GAZE, 2)),
            "V41 gaze endpoints are not pairwise distinguishable")
    v40 = load(V40_LAYOUT)
    require(v40.get("functional_decoration_track", {}).get("driven_only_by") == ["functional_event"] and
            v40.get("menu_entry_exception", {}).get("maximum_expression_duration_ms") == 500 and
            v40.get("menu_entry_exception", {}).get("after_last_cue") == "withdraw_expression_and_functional_tracks_then_show_menu_ui",
            "V41 lost V40's independent functional track or finite Menu exception")
    preview = layout.get("preview_zh")
    stories = preview.get("stories") if isinstance(preview, dict) else None
    require(isinstance(preview, dict) and isinstance(stories, dict) and set(stories) == STORIES and
            all(isinstance(value, dict) and isinstance(value.get("label_zh"), str) and
                any(ord(char) > 127 for char in value["label_zh"]) and isinstance(value.get("overview_step"), int)
                for value in stories.values()),
            "V41 must carry a Chinese label and actual overview frame selection for every score")
    output = {
        "schema": "companion.v41_directional_gaze_layout_gate.v1",
        "status": "PASS_V41_DIRECTIONAL_GAZE_LAYOUT_RUNTIME_INACTIVE",
        "layout": rel(layout_path), "locked_v9_source_sha256": LOCKED,
        "source_components": {"v22_face": 37, "v40_special_source": 69},
        "five_gaze_states": list(GAZE), "endpoint_offsets": EXPECTED_ENDPOINTS,
        "fixed_nose": {"component_id": 4, "offset": [0, 0]},
        "preview_chinese_story_count": len(STORIES),
        "menu_entry": "touch / three frames / 460ms / withdraw both tracks before Menu UI",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_v41_machine_audit_and_owner_review",
        "non_claims": ["no_whole_face_card", "no_code_drawn_face", "no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change"],
    }
    output_path = args.write.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PASS: V41 binds five pairwise-distinct registered V9 gaze endpoints and Chinese review metadata.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
