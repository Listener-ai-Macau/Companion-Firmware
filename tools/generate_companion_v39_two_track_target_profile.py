#!/usr/bin/env python3
"""Generate the inactive V39 expression/function two-track WB55 candidate profile."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v1/candidate/two-track-layout.json"
V22 = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V38 = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/function-state-component-layout.json"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v39_two_track_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v39_two_track_candidate_profile.c"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v1/candidate/target-score-attempt-01/two-track-wb55-target-profile-plan.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
NO_FUNCTIONAL = 0xFF

ROLE_ENUM = {
    "left_brow": "COMP_EXPRESSION_RIG_ROLE_LEFT_BROW",
    "right_brow": "COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW",
    "left_eye": "COMP_EXPRESSION_RIG_ROLE_LEFT_EYE",
    "right_eye": "COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE",
    "left_highlight": "COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT",
    "right_highlight": "COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT",
    "left_sparkle": "COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE",
    "right_sparkle": "COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE",
    "left_cheek": "COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK",
    "right_cheek": "COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK",
    "nose": "COMP_EXPRESSION_RIG_ROLE_NOSE",
    "mouth": "COMP_EXPRESSION_RIG_ROLE_MOUTH",
    "accent": "COMP_EXPRESSION_RIG_ROLE_CHARM",
    "charm": "COMP_EXPRESSION_RIG_ROLE_CHARM",
}
SCENE_ENUM = {
    "daily": "COMP_EXPRESSION_RIG_SCENE_DAILY",
    "touch": "COMP_EXPRESSION_RIG_SCENE_TOUCH",
    "recording": "COMP_EXPRESSION_RIG_SCENE_RECORDING",
    "charging": "COMP_EXPRESSION_RIG_SCENE_CHARGING",
    "sleep": "COMP_EXPRESSION_RIG_SCENE_SLEEP",
    "error": "COMP_EXPRESSION_RIG_SCENE_ERROR",
}
EMOTION_ENUM = {
    "calm": "COMP_EXPRESSION_RIG_EMOTION_CALM",
    "curious": "COMP_EXPRESSION_RIG_EMOTION_CURIOUS",
    "affectionate": "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE",
    "focused": "COMP_EXPRESSION_RIG_EMOTION_FOCUSED",
    "sleepy": "COMP_EXPRESSION_RIG_EMOTION_SLEEPY",
    "alert": "COMP_EXPRESSION_RIG_EMOTION_ALERT",
    "playful": "COMP_EXPRESSION_RIG_EMOTION_PLAYFUL",
}
ATTENTION_ENUM = {
    "center": "COMP_EXPRESSION_RIG_ATTENTION_CENTER",
    "left": "COMP_EXPRESSION_RIG_ATTENTION_LEFT",
    "right": "COMP_EXPRESSION_RIG_ATTENTION_RIGHT",
}
PHASE_ENUM = {
    "entry": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "lead": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "response": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "accent": "COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT",
    "hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
}
SPECIAL_ROLE = {539: "left_brow", 540: "right_brow", 541: "left_eye", 542: "right_eye", 543: "mouth"}


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


def c_string(value: str) -> str:
    require(value and all(32 <= ord(char) < 127 and char not in {'"', '\\'} for char in value),
            "generated C string is not ASCII-safe")
    return f'"{value}"'


def normalize_components(v22: dict[str, Any], v38: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for pack, source, count in (("v22_face", v22, 37), ("v38_special_source", v38, 57)):
        raw_components = source.get("components")
        require(isinstance(raw_components, list) and len(raw_components) == count, f"{pack} component count drifted")
        for raw in raw_components:
            require(isinstance(raw, dict), "component record is invalid")
            component_id = raw.get("component_id")
            base = raw.get("base_position")
            offset = raw.get("offset_range")
            size = raw.get("mask_size") or ([raw.get("width"), raw.get("height")]
                                              if isinstance(raw.get("width"), int) and isinstance(raw.get("height"), int)
                                              else None)
            role = raw.get("role") or SPECIAL_ROLE.get(component_id) or "charm"
            mask = ROOT / str(raw.get("mask", ""))
            require(isinstance(component_id, int) and isinstance(raw.get("name"), str) and role in ROLE_ENUM and
                    isinstance(base, list) and len(base) == 2 and isinstance(offset, dict) and
                    isinstance(offset.get("min"), list) and len(offset["min"]) == 2 and
                    isinstance(offset.get("max"), list) and len(offset["max"]) == 2 and
                    isinstance(size, list) and len(size) == 2 and raw.get("composite_op") in {"ink", "erase"} and
                    mask.is_file() and sha256(mask) == str(raw.get("mask_sha256", "")).upper(),
                    f"unregistered {pack} component source")
            result.append({"component_id": component_id, "name": raw["name"], "role": role, "base": base,
                           "offset": offset, "z": raw.get("z_index"), "op": raw["composite_op"], "pack": pack,
                           "mask_bytes": ((size[0] + 7) // 8) * size[1]})
    ids = [component["component_id"] for component in result]
    require(len(result) == 94 and len(ids) == len(set(ids)), "V39 component namespace drifted")
    return sorted(result, key=lambda component: component["component_id"])


def make_layer(components: dict[int, dict[str, Any]], component_id: int, offset: tuple[int, int] = (0, 0)) -> dict[str, Any]:
    component = components.get(component_id)
    require(component is not None and component["offset"]["min"][0] <= offset[0] <= component["offset"]["max"][0] and
            component["offset"]["min"][1] <= offset[1] <= component["offset"]["max"][1],
            f"component {component_id} offset is not registered")
    return {"component_id": component_id, "offset": [offset[0], offset[1]], "pack": component["pack"]}


def sort_layers(components: dict[int, dict[str, Any]], layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[int] = set()
    for layer in layers:
        component_id = layer.get("component_id")
        require(isinstance(component_id, int) and component_id not in seen and component_id in components,
                "track contains duplicate or unknown component")
        seen.add(component_id)
    return sorted(layers, key=lambda layer: components[layer["component_id"]]["z"])


def face_layers(components: dict[int, dict[str, Any]], base: list[int], highlight: tuple[int, int] = (0, 0),
                accent: list[int] | None = None) -> list[dict[str, Any]]:
    output = []
    for component_id in base + (accent or []):
        offset = highlight if component_id in {1, 3, 5, 7} else (0, 0)
        output.append(make_layer(components, component_id, offset))
    return sort_layers(components, output)


def expression_steps(components: dict[int, dict[str, Any]], layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    performances = layout["expression_track"]["performances"]
    specs = {
        "calm_presence": [("settled", 520, (0, 0), "center", "entry"),
                          ("soft_glance", 280, (-1, 1), "left", "lead"),
                          ("return", 820, (0, 0), "center", "hold")],
        "warm_presence": [("settled", 520, (0, 0), "center", "entry"),
                          ("soft_glance", 280, (1, 1), "right", "lead"),
                          ("return", 820, (0, 0), "center", "hold")],
        "curious_question": [("question_arrive", 160, (0, 0), "center", "entry"),
                             ("question_lift", 240, (-1, 1), "left", "lead"),
                             ("question_hold", 960, (0, 0), "center", "hold")],
        "alert_exclamation": [("exclamation_arrive", 160, (0, 0), "center", "entry"),
                               ("exclamation_lift", 240, (1, 1), "right", "lead"),
                               ("exclamation_hold", 960, (0, 0), "center", "hold")],
        "playful_presence": [("settled", 440, (0, 0), "center", "entry"),
                              ("sparkle_lead", 300, (1, 1), "right", "lead"),
                              ("return", 820, (0, 0), "center", "hold")],
    }
    result: dict[str, dict[str, Any]] = {}
    for name, rows in specs.items():
        performance = performances[name]
        accent_steps = performance.get("expression_owned_accent_steps", [])
        steps = []
        for index, (cue, duration, highlight, attention, phase) in enumerate(rows):
            accent = accent_steps[index] if accent_steps else []
            steps.append({"cue": cue, "duration_ms": duration, "phase": phase, "scene": "daily",
                          "emotion": performance["emotion"], "attention": attention,
                          "layers": face_layers(components, performance["base_face"], highlight, accent)})
        result[name] = {"name": name, "steps": steps}
    sleepy = performances["sleepy_presence"]
    sleepy_rows = [("sleep_entry", 420, "daily", "calm", "center", "entry"),
                   ("eyes_soften", 360, "sleep", "sleepy", "center", "lead"),
                   ("moon_arrive", 320, "sleep", "sleepy", "center", "response"),
                   ("dream_lift", 420, "sleep", "sleepy", "center", "accent"),
                   ("sleep_hold", 1400, "sleep", "sleepy", "center", "hold")]
    result["sleepy_presence"] = {"name": "sleepy_presence", "steps": [
        {"cue": cue, "duration_ms": duration, "phase": phase, "scene": scene, "emotion": emotion,
         "attention": attention, "layers": sort_layers(components, [make_layer(components, component_id)
                                                                          for component_id in sleepy["base_face_steps"][index]])}
        for index, (cue, duration, scene, emotion, attention, phase) in enumerate(sleepy_rows)
    ]}
    return result


def functional_steps(components: dict[int, dict[str, Any]], layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    contexts = {
        "recording_input": ("recording", "focused"),
        "bottom_connector_charging": ("charging", "affectionate"),
        "upgrade_progress": ("touch", "calm"),
        "error_caution": ("error", "calm"),
    }
    result: dict[str, dict[str, Any]] = {}
    for name, event in layout["functional_decoration_track"]["events"].items():
        scene, emotion = contexts[name]
        steps = []
        for index, component_ids in enumerate(event["frames"]):
            steps.append({"cue": f"{name}_{index}", "duration_ms": event["durations_ms"][index], "phase":
                          ("entry", "lead", "hold")[index], "scene": scene, "emotion": emotion,
                          "attention": "center", "layers": sort_layers(components, [make_layer(components, component_id)
                                                                                          for component_id in component_ids])})
        result[name] = {"name": name, "steps": steps}
    menu = layout["menu_entry_exception"]
    result["menu_entry_notice"] = {"name": "menu_entry_notice", "steps": [
        {"cue": cue, "duration_ms": menu["durations_ms"][index], "phase": ("entry", "lead", "hold")[index],
         "scene": "touch", "emotion": "curious", "attention": "center",
         "layers": sort_layers(components, [make_layer(components, component_id) for component_id in component_ids])}
        for index, (cue, component_ids) in enumerate(zip(("menu_grid_arrive", "menu_selection_confirm", "menu_entry_commit"), menu["frames"]))
    ]}
    return result


def build_stories(components: dict[int, dict[str, Any]], expressions: dict[str, dict[str, Any]],
                  functional: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selection = [
        ("calm_presence", "calm_presence", None, False),
        ("warm_presence", "warm_presence", None, False),
        ("curious_question", "curious_question", None, False),
        ("alert_exclamation", "alert_exclamation", None, False),
        ("playful_presence", "playful_presence", None, False),
        ("sleepy_presence", "sleepy_presence", None, False),
        ("recording_with_calm", "calm_presence", "recording_input", False),
        ("recording_with_warm", "warm_presence", "recording_input", False),
        ("charging_with_calm", "calm_presence", "bottom_connector_charging", False),
        ("upgrade_with_playful", "playful_presence", "upgrade_progress", False),
        ("error_with_calm", "calm_presence", "error_caution", False),
        ("menu_entry_notice", "calm_presence", "menu_entry_notice", True),
    ]
    stories: list[dict[str, Any]] = []
    for name, expression_name, functional_name, withdraw in selection:
        expression = expressions[expression_name]
        decoration = functional.get(functional_name) if functional_name else None
        count = len(decoration["steps"]) if decoration else len(expression["steps"])
        require(len(expression["steps"]) == count or decoration is None,
                "V39 preview stories require equal independently replayable track steps")
        steps = []
        for index in range(count):
            expression_step = expression["steps"][index]
            functional_step = decoration["steps"][index] if decoration else None
            final = sort_layers(components, expression_step["layers"] + (functional_step["layers"] if functional_step else []))
            require(len(final) <= 16 and any(layer["component_id"] == 4 and layer["offset"] == [0, 0] for layer in final),
                    "V39 final plan must remain legal and preserve fixed V9 nose")
            steps.append({"cue": functional_step["cue"] if functional_step else expression_step["cue"],
                          "duration_ms": functional_step["duration_ms"] if functional_step else expression_step["duration_ms"],
                          "state_scene": "touch" if withdraw else expression_step["scene"],
                          "expression_track": expression_name, "expression_step": index,
                          "functional_decoration_track": functional_name, "functional_step": index if functional_step else None,
                          "expression_layers": expression_step["layers"],
                          "functional_layers": functional_step["layers"] if functional_step else [], "layers": final})
        stories.append({"name": name, "expression_track": expression_name, "functional_decoration_track": functional_name,
                        "withdraw_all_tracks_after_last_cue": withdraw, "steps": steps})
    return stories


def render_header(component_count: int, expression_count: int, functional_count: int, story_count: int,
                  max_mask_bytes: int) -> str:
    return f'''/* Generated by tools/generate_companion_v39_two_track_target_profile.py; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V39_TWO_TRACK_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V39_TWO_TRACK_CANDIDATE_PROFILE_H

#include "expression_rig_performance_score.h"

#include <stdbool.h>
#include <stdint.h>

#define COMP_V39_TWO_TRACK_CANDIDATE_COMPONENT_COUNT {component_count}u
#define COMP_V39_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT {expression_count}u
#define COMP_V39_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT {functional_count}u
#define COMP_V39_TWO_TRACK_CANDIDATE_STORY_COUNT {story_count}u
#define COMP_V39_TWO_TRACK_CANDIDATE_MAX_MASK_BYTES {max_mask_bytes}u
#define COMP_V39_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK 0xFFu

typedef struct {{ const char *name; const comp_expression_rig_registered_performance_score_t *score; uint8_t step_count; }}
comp_v39_two_track_candidate_track_t;
typedef struct {{ const char *cue; const char *browser_pbm_filename; uint16_t duration_ms; uint8_t expression_step_index; uint8_t functional_step_index; }}
comp_v39_two_track_candidate_frame_t;
typedef struct {{ const char *name; uint8_t expression_track_index; uint8_t functional_track_index; bool uses_menu_entry_track; const comp_v39_two_track_candidate_frame_t *frames; uint8_t frame_count; bool withdraw_all_tracks_after_last_cue; }}
comp_v39_two_track_candidate_story_t;

const comp_expression_rig_profile_t *comp_v39_two_track_candidate_profile(void);
bool comp_v39_two_track_candidate_runtime_activation_allowed(void);
const comp_v39_two_track_candidate_track_t *comp_v39_two_track_candidate_expression_track(uint8_t index);
const comp_v39_two_track_candidate_track_t *comp_v39_two_track_candidate_functional_track(uint8_t index);
const comp_v39_two_track_candidate_track_t *comp_v39_two_track_candidate_menu_entry_track(void);
const comp_v39_two_track_candidate_story_t *comp_v39_two_track_candidate_story(uint8_t index);
bool comp_v39_two_track_candidate_build_composed_frame(uint8_t expression_track_index, uint8_t expression_step_index, uint8_t functional_track_index, uint8_t functional_step_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan);
bool comp_v39_two_track_candidate_build_menu_entry_frame(uint8_t expression_track_index, uint8_t expression_step_index, uint8_t menu_entry_step_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan);
bool comp_v39_two_track_candidate_build_story_frame(const comp_v39_two_track_candidate_story_t *story, uint8_t frame_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V39_TWO_TRACK_CANDIDATE_PROFILE_H */
'''


def render_score(symbol: str, track: dict[str, Any]) -> tuple[list[str], str]:
    lines: list[str] = []
    for index, step in enumerate(track["steps"]):
        pose = f"{symbol}_step_{index}_pose"
        lines.extend(["", f"static const comp_expression_rig_registered_pose_t {pose} = {{",
                      f"    .scene = {SCENE_ENUM[step['scene']]}, .emotion = {EMOTION_ENUM[step['emotion']]}, .attention = {ATTENTION_ENUM[step['attention']]},",
                      f"    .layer_count = {len(step['layers'])}u, .layers = {{"])
        lines.extend("        {.component_id = %du, .offset_x = %d, .offset_y = %d, .dynamic_flags = 0u}," %
                     (layer["component_id"], layer["offset"][0], layer["offset"][1]) for layer in step["layers"])
        lines.extend(["    },", "};"])
    lines.extend(["", f"static const comp_expression_rig_registered_score_step_t {symbol}_steps[] = {{"])
    for index, step in enumerate(track["steps"]):
        lines.append("    {.phase = %s, .duration_ms = %du, .state = {.scene = %s, .emotion = %s, .attention = %s, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &%s_step_%d_pose}," %
                     (PHASE_ENUM[step["phase"]], step["duration_ms"], SCENE_ENUM[step["scene"]], EMOTION_ENUM[step["emotion"]],
                      ATTENTION_ENUM[step["attention"]], symbol, index))
    lines.extend(["};", f"static const comp_expression_rig_registered_performance_score_t {symbol} = {{.steps = {symbol}_steps, .step_count = (uint8_t)(sizeof({symbol}_steps) / sizeof({symbol}_steps[0]))}};"])
    return lines, symbol


def render_source(components: list[dict[str, Any]], expressions: dict[str, dict[str, Any]],
                  functional: dict[str, dict[str, Any]], stories: list[dict[str, Any]]) -> str:
    lines = ["/* Generated from the versioned V39 two-track layout; do not hand edit. */",
             "#include \"expression_rig_v39_two_track_candidate_profile.h\"", "#include \"expression_rig_track_composer.h\"", "",
             "static const comp_expression_rig_component_info_t k_v39_components[] = {"]
    for component in components:
        minimum, maximum = component["offset"]["min"], component["offset"]["max"]
        operation = "COMP_EXPRESSION_RIG_COMPOSITE_INK" if component["op"] == "ink" else "COMP_EXPRESSION_RIG_COMPOSITE_ERASE"
        lines.append("    {.component_id = %du, .role = %s, .variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, .base_x = %d, .base_y = %d, .min_offset_x = %d, .min_offset_y = %d, .max_offset_x = %d, .max_offset_y = %d, .z_index = %du, .composite_op = %s}," %
                     (component["component_id"], ROLE_ENUM[component["role"]], component["base"][0], component["base"][1],
                      minimum[0], minimum[1], maximum[0], maximum[1], component["z"], operation))
    lines.extend(["};", "", "static const comp_expression_rig_profile_t k_v39_profile = {",
                  "    .components = k_v39_components, .component_count = COMP_V39_TWO_TRACK_CANDIDATE_COMPONENT_COUNT,",
                  "    .scene_charm_component = {[COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID},",
                  "    .registered_poses = NULL, .registered_pose_count = 0u,", "};"])
    expression_items = list(expressions.items())
    functional_items = [(name, functional[name]) for name in ("recording_input", "bottom_connector_charging", "upgrade_progress", "error_caution")]
    for index, (_, track) in enumerate(expression_items):
        block, _ = render_score(f"k_v39_expression_{index}", track)
        lines.extend(block)
    for index, (_, track) in enumerate(functional_items):
        block, _ = render_score(f"k_v39_functional_{index}", track)
        lines.extend(block)
    menu_block, _ = render_score("k_v39_menu_entry", functional["menu_entry_notice"])
    lines.extend(menu_block)
    lines.extend(["", "static const comp_v39_two_track_candidate_track_t k_v39_expression_tracks[] = {"])
    lines.extend("    {.name = %s, .score = &k_v39_expression_%d, .step_count = %du}," %
                 (c_string(name), index, len(track["steps"])) for index, (name, track) in enumerate(expression_items))
    lines.extend(["};", "", "static const comp_v39_two_track_candidate_track_t k_v39_functional_tracks[] = {"])
    lines.extend("    {.name = %s, .score = &k_v39_functional_%d, .step_count = %du}," %
                 (c_string(name), index, len(track["steps"])) for index, (name, track) in enumerate(functional_items))
    lines.extend(["};", "", "static const comp_v39_two_track_candidate_track_t k_v39_menu_entry_track = {.name = \"menu_entry_notice\", .score = &k_v39_menu_entry, .step_count = 3u};"])
    expression_index = {name: index for index, (name, _) in enumerate(expression_items)}
    functional_index = {name: index for index, (name, _) in enumerate(functional_items)}
    story_lines = []
    for story_index, story in enumerate(stories):
        symbol = f"k_v39_story_{story_index}_frames"
        lines.extend(["", f"static const comp_v39_two_track_candidate_frame_t {symbol}[] = {{"])
        for step_index, step in enumerate(story["steps"]):
            function_step = step["functional_step"] if step["functional_step"] is not None else NO_FUNCTIONAL
            lines.append("    {.cue = %s, .browser_pbm_filename = %s, .duration_ms = %du, .expression_step_index = %du, .functional_step_index = %du}," %
                         (c_string(step["cue"]), c_string(f"{story['name']}-{step_index:02d}-{step['cue']}.pbm"),
                          step["duration_ms"], step["expression_step"], function_step))
        lines.append("};")
        function_id = functional_index.get(story["functional_decoration_track"], NO_FUNCTIONAL)
        uses_menu = "true" if story["functional_decoration_track"] == "menu_entry_notice" else "false"
        withdrawal = "true" if story["withdraw_all_tracks_after_last_cue"] else "false"
        story_lines.append("    {.name = %s, .expression_track_index = %du, .functional_track_index = %du, .uses_menu_entry_track = %s, .frames = %s, .frame_count = (uint8_t)(sizeof(%s) / sizeof(%s[0])), .withdraw_all_tracks_after_last_cue = %s}," %
                           (c_string(story["name"]), expression_index[story["expression_track"]], function_id, uses_menu,
                            symbol, symbol, symbol, withdrawal))
    lines.extend(["", "static const comp_v39_two_track_candidate_story_t k_v39_stories[] = {", *story_lines, "};", "",
                  "const comp_expression_rig_profile_t *comp_v39_two_track_candidate_profile(void) { return &k_v39_profile; }",
                  "bool comp_v39_two_track_candidate_runtime_activation_allowed(void) { return false; }",
                  "const comp_v39_two_track_candidate_track_t *comp_v39_two_track_candidate_expression_track(uint8_t index) { return index < COMP_V39_TWO_TRACK_CANDIDATE_EXPRESSION_TRACK_COUNT ? &k_v39_expression_tracks[index] : NULL; }",
                  "const comp_v39_two_track_candidate_track_t *comp_v39_two_track_candidate_functional_track(uint8_t index) { return index < COMP_V39_TWO_TRACK_CANDIDATE_FUNCTIONAL_TRACK_COUNT ? &k_v39_functional_tracks[index] : NULL; }",
                  "const comp_v39_two_track_candidate_track_t *comp_v39_two_track_candidate_menu_entry_track(void) { return &k_v39_menu_entry_track; }", "",
                  "static bool build_with_optional_functional(const comp_v39_two_track_candidate_track_t *expression, uint8_t expression_step, const comp_v39_two_track_candidate_track_t *functional, uint8_t functional_step, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {",
                  "    comp_expression_rig_plan_t expression_plan; comp_expression_rig_plan_t functional_plan;",
                  "    if (expression == NULL || expression->score == NULL || expression_step >= expression->step_count || out_plan == NULL || !comp_expression_rig_build_registered_score_step(&k_v39_profile, expression->score, expression_step, dynamic_context, &expression_plan)) { return false; }",
                  "    if (functional == NULL) { return comp_expression_rig_merge_tracks(&k_v39_profile, &expression_plan, NULL, out_plan); }",
                  "    return functional->score != NULL && functional_step < functional->step_count && comp_expression_rig_build_registered_score_step(&k_v39_profile, functional->score, functional_step, NULL, &functional_plan) && comp_expression_rig_merge_tracks(&k_v39_profile, &expression_plan, &functional_plan, out_plan);",
                  "}", "",
                  "bool comp_v39_two_track_candidate_build_composed_frame(uint8_t expression_track_index, uint8_t expression_step_index, uint8_t functional_track_index, uint8_t functional_step_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {",
                  "    const comp_v39_two_track_candidate_track_t *functional = functional_track_index == COMP_V39_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK ? NULL : comp_v39_two_track_candidate_functional_track(functional_track_index);",
                  "    if (functional == NULL && functional_track_index != COMP_V39_TWO_TRACK_CANDIDATE_NO_FUNCTIONAL_TRACK) { return false; }",
                  "    return build_with_optional_functional(comp_v39_two_track_candidate_expression_track(expression_track_index), expression_step_index, functional, functional_step_index, dynamic_context, out_plan);",
                  "}", "",
                  "bool comp_v39_two_track_candidate_build_menu_entry_frame(uint8_t expression_track_index, uint8_t expression_step_index, uint8_t menu_entry_step_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {",
                  "    return build_with_optional_functional(comp_v39_two_track_candidate_expression_track(expression_track_index), expression_step_index, &k_v39_menu_entry_track, menu_entry_step_index, dynamic_context, out_plan);",
                  "}", "",
                  "bool comp_v39_two_track_candidate_build_story_frame(const comp_v39_two_track_candidate_story_t *story, uint8_t frame_index, const comp_expression_rig_state_t *dynamic_context, comp_expression_rig_plan_t *out_plan) {",
                  "    const comp_v39_two_track_candidate_frame_t *frame;",
                  "    if (story == NULL || out_plan == NULL || story->frames == NULL || frame_index >= story->frame_count) { return false; }",
                  "    frame = &story->frames[frame_index];",
                  "    return story->uses_menu_entry_track ? comp_v39_two_track_candidate_build_menu_entry_frame(story->expression_track_index, frame->expression_step_index, frame->functional_step_index, dynamic_context, out_plan) : comp_v39_two_track_candidate_build_composed_frame(story->expression_track_index, frame->expression_step_index, story->functional_track_index, frame->functional_step_index, dynamic_context, out_plan);",
                  "}", "",
                  "const comp_v39_two_track_candidate_story_t *comp_v39_two_track_candidate_story(uint8_t index) { return index < COMP_V39_TWO_TRACK_CANDIDATE_STORY_COUNT ? &k_v39_stories[index] : NULL; }", ""])
    return "\n".join(lines)


def build_artifacts() -> dict[Path, str]:
    layout, v22, v38 = load(LAYOUT), load(V22), load(V38)
    require(layout.get("schema") == "companion.v39_two_track_rig_layout.v1" and layout.get("revision") == 39 and
            layout.get("locked_v9_source", {}).get("sha256") == LOCKED and
            layout.get("composition", {}).get("runtime_binding") == "forbidden_until_v39_machine_audit_and_owner_review",
            "V39 layout authority drifted")
    components = normalize_components(v22, v38)
    by_id = {component["component_id"]: component for component in components}
    expressions = expression_steps(by_id, layout)
    functional = functional_steps(by_id, layout)
    stories = build_stories(by_id, expressions, functional)
    require(len(expressions) == 6 and len(functional) == 5 and len(stories) == 12 and
            sum(len(story["steps"]) for story in stories) == 38,
            "V39 track/story coverage drifted")
    max_mask = max(component["mask_bytes"] for component in components)
    trace = {
        "schema": "companion.v39_two_track_wb55_target_profile_plan.v1",
        "status": "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242"],
        "locked_v9_source_sha256": LOCKED,
        "track_layout": rel(LAYOUT), "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_v39_machine_audit_and_owner_review",
        "component_sources": {"v22_face": 37, "v38_special_source": 57}, "max_component_mask_bytes": max_mask,
        "two_track_contract": {"expression_driven_only_by": ["emotion", "attention", "energy", "interaction_memory"],
                               "functional_driven_only_by": ["functional_event"],
                               "final_plan": "deterministic_union(expression_track, functional_decoration_track)",
                               "quarantined_rejected_v38_face_components": [554, 555, 556]},
        "expression_tracks": list(expressions.values()),
        "functional_decoration_tracks": [functional[name] for name in ("recording_input", "bottom_connector_charging", "upgrade_progress", "error_caution")],
        "menu_entry_track": functional["menu_entry_notice"], "scores": stories,
        "menu_entry_policy": {"state_scene": "touch", "maximum_expression_duration_ms": 500,
                              "after_last_cue": "withdraw_expression_and_functional_tracks_then_show_menu_ui",
                              "persistent_menu_score": "forbidden", "menu_ui_owns_screen_after_last_cue": True},
        "non_claims": ["no_v38_profile_promotion", "no_whole_face_card", "no_code_drawn_face", "no_runtime_binding", "no_panel_or_driver_change"]
    }
    return {HEADER: render_header(len(components), 6, 4, len(stories), max_mask),
            SOURCE: render_source(components, expressions, functional, stories),
            TRACE: json.dumps(trace, indent=2) + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    drifted = [path for path, content in artifacts.items() if args.check and (not path.is_file() or path.read_text(encoding="utf-8") != content)]
    if drifted:
        for path in drifted:
            print(f"ERROR: generated artifact drifted: {rel(path)}")
        return 1
    if not args.check:
        for path, content in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("PASS: generated inactive V39 two-track profile with 94 source components, 6 expression tracks, 4 functional tracks and 38 preview frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
