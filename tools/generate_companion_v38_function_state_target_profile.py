#!/usr/bin/env python3
"""Generate the inactive WB55 V38 profile with one-shot Menu entry semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from generate_companion_v34_v35_special_decoration_target_profile import ROLE_ENUM, component_variant


ROOT = Path(__file__).resolve().parents[1]
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V22 = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V37_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/target-score-attempt-01/sleepy-dream-wb55-target-profile-plan.json"
V38 = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/function-state-component-layout.json"
INTERPRETATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-source-v1/candidate/choreography-interpretation-v2.json"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v38_function_state_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v38_function_state_candidate_profile.c"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/target-score-attempt-01/function-state-wb55-target-profile-plan.json"
SCORE_ORDER = ("recording_input", "bottom_connector_charging", "curious_question", "alert_exclamation", "sleepy_dream_cloud",
               "menu_entry_notice", "upgrade_progress", "error_caution")
CONTEXT = {
    "recording_input": ("COMP_EXPRESSION_RIG_SCENE_RECORDING", "COMP_EXPRESSION_RIG_EMOTION_FOCUSED"),
    "bottom_connector_charging": ("COMP_EXPRESSION_RIG_SCENE_CHARGING", "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE"),
    "curious_question": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_CURIOUS"),
    "alert_exclamation": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_ALERT"),
    "sleepy_dream_cloud": ("COMP_EXPRESSION_RIG_SCENE_SLEEP", "COMP_EXPRESSION_RIG_EMOTION_SLEEPY"),
    "menu_entry_notice": ("COMP_EXPRESSION_RIG_SCENE_TOUCH", "COMP_EXPRESSION_RIG_EMOTION_CURIOUS"),
    "upgrade_progress": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE"),
    "error_caution": ("COMP_EXPRESSION_RIG_SCENE_ERROR", "COMP_EXPRESSION_RIG_EMOTION_PUZZLED"),
}
TRACE_SCENE = {
    "COMP_EXPRESSION_RIG_SCENE_DAILY": "daily",
    "COMP_EXPRESSION_RIG_SCENE_TOUCH": "touch",
    "COMP_EXPRESSION_RIG_SCENE_RECORDING": "recording",
    "COMP_EXPRESSION_RIG_SCENE_SLEEP": "sleep",
    "COMP_EXPRESSION_RIG_SCENE_CHARGING": "charging",
    "COMP_EXPRESSION_RIG_SCENE_ERROR": "error",
}
PHASE = {
    "source_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "primary_highlight_lead": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "sparkle_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "eyes_soften": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "lower_face_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "dream_lift": "COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT",
    "sleep_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
    "menu_grid_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "menu_selection_confirm": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "menu_entry_commit": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
    "upgrade_start": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "upgrade_rise": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "upgrade_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
    "error_notice": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "error_settle": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "error_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def c_string(value: str) -> str:
    require(value and all(32 <= ord(char) < 127 and char not in {'"', '\\'} for char in value),
            "generated C descriptor text is not ASCII safe")
    return f'"{value}"'


def normalize_components(v22: dict[str, Any], v38: dict[str, Any]) -> list[dict[str, Any]]:
    source_lists = (("v22_face", v22.get("components")), ("v38_merged_special", v38.get("components")))
    require(v22.get("locked_v9_source_sha256") == LOCKED and
            v38.get("locked_v9_source", {}).get("sha256") == LOCKED and
            v38.get("runtime_resource_activated") is False and v38.get("active_candidate_binding") == "forbidden",
            "V38 component source lineage or activation boundary drifted")
    result: list[dict[str, Any]] = []
    for pack, raw_components in source_lists:
        expected_count = 37 if pack == "v22_face" else 57
        require(isinstance(raw_components, list) and len(raw_components) == expected_count,
                f"{pack} component count drifted")
        for raw in raw_components:
            require(isinstance(raw, dict), "component record is invalid")
            component_id = raw.get("component_id")
            mask = ROOT / str(raw.get("mask", ""))
            base = raw.get("base_position")
            offset = raw.get("offset_range")
            size = raw.get("mask_size") or ([raw["width"], raw["height"]]
                                              if isinstance(raw.get("width"), int) and isinstance(raw.get("height"), int)
                                              else None)
            role = raw.get("role") or "charm"
            require(isinstance(component_id, int) and component_id > 0 and role in ROLE_ENUM and isinstance(raw.get("name"), str) and
                    isinstance(base, list) and len(base) == 2 and isinstance(offset, dict) and
                    isinstance(offset.get("min"), list) and len(offset["min"]) == 2 and
                    isinstance(offset.get("max"), list) and len(offset["max"]) == 2 and
                    isinstance(size, list) and len(size) == 2 and mask.is_file() and
                    sha256(mask) == str(raw.get("mask_sha256", "")).upper() and raw.get("composite_op") in {"ink", "erase"},
                    f"unregistered component source: {raw.get('name')}")
            result.append({"component_id": component_id, "name": raw["name"], "role": role, "base": base, "offset": offset,
                           "z": raw.get("z_index"), "op": raw["composite_op"], "pack": pack,
                           "mask_bytes": ((size[0] + 7) // 8) * size[1]})
    ids = [component["component_id"] for component in result]
    require(len(result) == 94 and len(ids) == len(set(ids)), "V38 profile component namespace is not exact")
    return sorted(result, key=lambda component: component["component_id"])


def layer(component_by_id: dict[int, dict[str, Any]], component_id: int, offset: list[int]) -> dict[str, Any]:
    component = component_by_id.get(component_id)
    require(component is not None and len(offset) == 2 and
            component["offset"]["min"][0] <= offset[0] <= component["offset"]["max"][0] and
            component["offset"]["min"][1] <= offset[1] <= component["offset"]["max"][1],
            f"score uses an illegal component layer: {component_id}")
    return {"component_id": component_id, "offset": offset, "pack": component["pack"]}


def face_layers(component_by_id: dict[int, dict[str, Any]], affect: str) -> list[dict[str, Any]]:
    lower = {
        "calm": (13, 16, 14, 17, 15),
        "warm": (33, 36, 34, 37, 35),
        "error": (554, 555, 14, 17, 556),
    }[affect]
    left_brow, right_brow, left_cheek, right_cheek, mouth = lower
    return [layer(component_by_id, left_brow, [0, 0]), layer(component_by_id, right_brow, [0, 0]),
            layer(component_by_id, 2, [0, 0]), layer(component_by_id, 6, [0, 0]),
            layer(component_by_id, 1, [0, 0]), layer(component_by_id, 5, [0, 0]),
            layer(component_by_id, 3, [0, 0]), layer(component_by_id, 7, [0, 0]),
            layer(component_by_id, left_cheek, [0, 0]), layer(component_by_id, right_cheek, [0, 0]),
            layer(component_by_id, 4, [0, 0]), layer(component_by_id, mouth, [0, 0])]


def copied_v37_scores(v37_trace: dict[str, Any], component_by_id: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    raw_scores = v37_trace.get("scores")
    expected_counts = {"recording_input": 3, "bottom_connector_charging": 3, "curious_question": 3,
                       "alert_exclamation": 3, "sleepy_dream_cloud": 5}
    require(v37_trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            isinstance(raw_scores, list) and len(raw_scores) == 5, "V37 source score evidence drifted")
    copied = []
    for score in raw_scores:
        name = score.get("name") if isinstance(score, dict) else None
        steps = score.get("steps") if isinstance(score, dict) else None
        require(isinstance(name, str) and isinstance(steps, list) and len(steps) == expected_counts.get(name),
                "V37 score coverage drifted")
        new_steps = []
        for step in steps:
            raw_layers = step.get("layers") if isinstance(step, dict) else None
            require(isinstance(raw_layers, list) and raw_layers and len(raw_layers) <= 16, "V37 score step drifted")
            new_steps.append({"cue": step["cue"], "duration_ms": step["duration_ms"],
                              "layers": [layer(component_by_id, item["component_id"], item["offset"]) for item in raw_layers]})
        copied.append({"name": name, "prelude_bridge": score["prelude_bridge"], "steps": new_steps,
                       "withdraw_expression_rig_after_last_cue": False})
    return copied


def build_scores(v37_trace: dict[str, Any], component_by_id: dict[int, dict[str, Any]], interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    scores = copied_v37_scores(v37_trace, component_by_id)
    menu_steps = []
    for component_id, cue, duration in ((545, "menu_grid_arrive", 140), (546, "menu_selection_confirm", 140), (547, "menu_entry_commit", 180)):
        menu_steps.append({"cue": cue, "duration_ms": duration,
                           "layers": face_layers(component_by_id, "calm") + [layer(component_by_id, component_id, [0, 0])]})
    require(sum(step["duration_ms"] for step in menu_steps) <= interpretation["menu"]["maximum_expression_duration_ms"],
            "Menu entry must withdraw before the persistent menu UI")
    scores.append({"name": "menu_entry_notice", "prelude_bridge": "daily_calm_to_menu_ui_entry", "steps": menu_steps,
                   "withdraw_expression_rig_after_last_cue": True})
    upgrade_steps = []
    for component_id, cue, duration, offset_y in ((548, "upgrade_start", 700, 2), (549, "upgrade_rise", 420, 1), (550, "upgrade_hold", 900, 0)):
        upgrade_steps.append({"cue": cue, "duration_ms": duration,
                              "layers": face_layers(component_by_id, "warm") + [layer(component_by_id, component_id, [0, offset_y])]})
    scores.append({"name": "upgrade_progress", "prelude_bridge": "calm_to_warm_upgrade_progress", "steps": upgrade_steps,
                   "withdraw_expression_rig_after_last_cue": False})
    error_steps = []
    for component_id, cue, duration, offset_y in ((551, "error_notice", 260, 2), (552, "error_settle", 260, 1), (553, "error_hold", 1200, 0)):
        error_steps.append({"cue": cue, "duration_ms": duration,
                            "layers": face_layers(component_by_id, "error") + [layer(component_by_id, component_id, [0, offset_y])]})
    scores.append({"name": "error_caution", "prelude_bridge": "daily_calm_to_error_caution", "steps": error_steps,
                   "withdraw_expression_rig_after_last_cue": False})
    require(tuple(score["name"] for score in scores) == SCORE_ORDER and
            all(0 < len(score["steps"]) <= 16 for score in scores), "V38 score order or layer capacity drifted")
    return scores


def render_header(component_count: int, max_mask_bytes: int) -> str:
    return f'''/* Generated by tools/generate_companion_v38_function_state_target_profile.py; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V38_FUNCTION_STATE_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V38_FUNCTION_STATE_CANDIDATE_PROFILE_H

#include "expression_rig_performance_score.h"
#include <stdbool.h>
#include <stdint.h>

#define COMP_V38_FUNCTION_STATE_CANDIDATE_REVISION 38u
#define COMP_V38_FUNCTION_STATE_CANDIDATE_COMPONENT_COUNT {component_count}u
#define COMP_V38_FUNCTION_STATE_CANDIDATE_SCORE_COUNT 8u
#define COMP_V38_FUNCTION_STATE_CANDIDATE_MAX_MASK_BYTES {max_mask_bytes}u
#define COMP_V38_FUNCTION_STATE_CANDIDATE_SOURCE_SHA256 "{LOCKED}"

typedef struct {{ const char *cue; const char *browser_pbm_filename; uint16_t duration_ms; }}
comp_v38_function_state_candidate_frame_t;
typedef struct {{ const char *name; const char *prelude_bridge; const comp_expression_rig_registered_performance_score_t *score;
                 const comp_v38_function_state_candidate_frame_t *frames; uint8_t frame_count;
                 bool withdraw_expression_rig_after_last_cue; }} comp_v38_function_state_candidate_score_t;

const comp_expression_rig_profile_t *comp_v38_function_state_candidate_profile(void);
bool comp_v38_function_state_candidate_runtime_activation_allowed(void);
uint8_t comp_v38_function_state_candidate_score_count(void);
const comp_v38_function_state_candidate_score_t *comp_v38_function_state_candidate_score(uint8_t index);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V38_FUNCTION_STATE_CANDIDATE_PROFILE_H */
'''


def render_source(components: list[dict[str, Any]], scores: list[dict[str, Any]]) -> str:
    lines = ["/* Generated from V22, V37 and recorded V38 source components; do not hand edit. */",
             "#include \"expression_rig_v38_function_state_candidate_profile.h\"", "",
             "static const comp_expression_rig_component_info_t k_v38_components[] = {"]
    for component in components:
        minimum, maximum = component["offset"]["min"], component["offset"]["max"]
        op = "COMP_EXPRESSION_RIG_COMPOSITE_INK" if component["op"] == "ink" else "COMP_EXPRESSION_RIG_COMPOSITE_ERASE"
        lines.append("    {.component_id = %du, .role = %s, .variant = %s, .base_x = %d, .base_y = %d, .min_offset_x = %d, .min_offset_y = %d, .max_offset_x = %d, .max_offset_y = %d, .z_index = %du, .composite_op = %s}," %
                     (component["component_id"], ROLE_ENUM[component["role"]], component_variant(component["name"]), component["base"][0],
                      component["base"][1], minimum[0], minimum[1], maximum[0], maximum[1], component["z"], op))
    lines.extend(["};", "", "static const comp_expression_rig_profile_t k_v38_profile = {", "    .components = k_v38_components,",
                  "    .component_count = COMP_V38_FUNCTION_STATE_CANDIDATE_COMPONENT_COUNT,",
                  "    .scene_charm_component = {[COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID},",
                  "    .registered_poses = NULL, .registered_pose_count = 0u,", "};"])
    descriptors = []
    for score_index, score in enumerate(scores):
        scene, emotion = CONTEXT[score["name"]]
        for step_index, step in enumerate(score["steps"]):
            pose = f"k_v38_score_{score_index}_step_{step_index}_pose"
            lines.extend(["", f"static const comp_expression_rig_registered_pose_t {pose} = {{",
                          f"    .scene = {scene}, .emotion = {emotion}, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = {len(step['layers'])}u, .layers = {{"])
            lines.extend("        {.component_id = %du, .offset_x = %d, .offset_y = %d, .dynamic_flags = 0u}," %
                         (item["component_id"], item["offset"][0], item["offset"][1]) for item in step["layers"])
            lines.extend(["    },", "};"])
        lines.extend(["", f"static const comp_expression_rig_registered_score_step_t k_v38_score_{score_index}_steps[] = {{"])
        for step_index, step in enumerate(score["steps"]):
            lines.append("    {.phase = %s, .duration_ms = %du, .state = {.scene = %s, .emotion = %s, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v38_score_%d_step_%d_pose}," %
                         (PHASE[step["cue"]], step["duration_ms"], scene, emotion, score_index, step_index))
        lines.extend(["};", f"static const comp_expression_rig_registered_performance_score_t k_v38_score_{score_index} = {{.steps = k_v38_score_{score_index}_steps, .step_count = (uint8_t)(sizeof(k_v38_score_{score_index}_steps) / sizeof(k_v38_score_{score_index}_steps[0]))}};",
                      f"static const comp_v38_function_state_candidate_frame_t k_v38_score_{score_index}_frames[] = {{"])
        for step_index, step in enumerate(score["steps"]):
            lines.append("    {.cue = %s, .browser_pbm_filename = %s, .duration_ms = %du}," %
                         (c_string(step["cue"]), c_string(f"{score['name']}-{step_index:02d}-{step['cue']}.pbm"), step["duration_ms"]))
        lines.append("};")
        withdrawal = "true" if score["withdraw_expression_rig_after_last_cue"] else "false"
        descriptors.append("    {.name = %s, .prelude_bridge = %s, .score = &k_v38_score_%d, .frames = k_v38_score_%d_frames, .frame_count = (uint8_t)(sizeof(k_v38_score_%d_frames) / sizeof(k_v38_score_%d_frames[0])), .withdraw_expression_rig_after_last_cue = %s}," %
                           (c_string(score["name"]), c_string(score["prelude_bridge"]), score_index, score_index, score_index, score_index, withdrawal))
    lines.extend(["", "static const comp_v38_function_state_candidate_score_t k_v38_scores[] = {", *descriptors, "};", "",
                  "const comp_expression_rig_profile_t *comp_v38_function_state_candidate_profile(void) { return &k_v38_profile; }",
                  "bool comp_v38_function_state_candidate_runtime_activation_allowed(void) { return false; }",
                  "uint8_t comp_v38_function_state_candidate_score_count(void) { return (uint8_t)(sizeof(k_v38_scores) / sizeof(k_v38_scores[0])); }",
                  "const comp_v38_function_state_candidate_score_t *comp_v38_function_state_candidate_score(uint8_t index) { return index < comp_v38_function_state_candidate_score_count() ? &k_v38_scores[index] : NULL; }", ""])
    return "\n".join(lines)


def build_artifacts() -> dict[Path, str]:
    v22, v37_trace, v38, interpretation = load(V22), load(V37_TRACE), load(V38), load(INTERPRETATION)
    require(interpretation.get("menu", {}).get("event") == "menu_entry_notice" and
            interpretation.get("menu", {}).get("maximum_expression_duration_ms") == 500 and
            interpretation.get("menu", {}).get("after_last_cue") == "withdraw_expression_rig_then_show_menu_ui",
            "Menu entry interpretation drifted")
    components = normalize_components(v22, v38)
    component_by_id = {component["component_id"]: component for component in components}
    scores = build_scores(v37_trace, component_by_id, interpretation)
    for score in scores:
        scene, _ = CONTEXT[score["name"]]
        for step in score["steps"]:
            # The trace is the browser/WB55 contract: Menu's finite cue is touch, never Menu UI.
            step["state_scene"] = TRACE_SCENE[scene]
    max_mask_bytes = max(component["mask_bytes"] for component in components)
    frame_count = sum(len(score["steps"]) for score in scores)
    trace = {"schema": "companion.v38_function_state_wb55_target_profile_plan.v1",
             "status": "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE",
             "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240"],
             "locked_v9_source_sha256": LOCKED, "runtime_resource_activated": False,
             "active_candidate_binding": "forbidden_until_total_machine_audit_and_owner_review",
             "component_sources": {"v22_face": 37, "v38_merged_special": 57}, "max_component_mask_bytes": max_mask_bytes,
             "menu_entry_policy": {"maximum_expression_duration_ms": 500,
                                   "after_last_cue": "withdraw_expression_rig_then_show_menu_ui",
                                   "persistent_menu_score": "forbidden",
                                   "entry_cue_state_scene": "touch",
                                   "menu_ui_owns_screen_after_last_cue": True},
             "scores": scores,
             "non_claims": ["no_full_face_card", "no_code_drawn_face", "no_menu_expression_behind_menu_ui", "no_runtime_binding", "no_panel_or_driver_change"]}
    require(frame_count == 26, "V38 score frame coverage drifted")
    return {HEADER: render_header(len(components), max_mask_bytes), SOURCE: render_source(components, scores),
            TRACE: json.dumps(trace, indent=2, ensure_ascii=True) + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
    print(f"PASS: {'verified' if args.check else 'generated'} inactive V38 WB55 profile with 94 source components and 26 score frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
