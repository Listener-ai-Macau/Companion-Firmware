#!/usr/bin/env python3
"""Generate an inactive WB55 V37 profile with locked-V9 sleepy components."""

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
V34_CONTRACT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-score-contract.json"
V37 = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/sleepy-dream-component-layout.json"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v37_sleepy_dream_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v37_sleepy_dream_candidate_profile.c"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/target-score-attempt-01/sleepy-dream-wb55-target-profile-plan.json"
SCORE_ORDER = ("recording_input", "bottom_connector_charging", "curious_question", "alert_exclamation", "sleepy_dream_cloud")
CONTEXT = {
    "recording_input": ("COMP_EXPRESSION_RIG_SCENE_RECORDING", "COMP_EXPRESSION_RIG_EMOTION_FOCUSED"),
    "bottom_connector_charging": ("COMP_EXPRESSION_RIG_SCENE_CHARGING", "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE"),
    "curious_question": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_CURIOUS"),
    "alert_exclamation": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_ALERT"),
    "sleepy_dream_cloud": ("COMP_EXPRESSION_RIG_SCENE_SLEEP", "COMP_EXPRESSION_RIG_EMOTION_SLEEPY"),
}
PHASE = {
    "source_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "primary_highlight_lead": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "sparkle_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "eyes_soften": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "lower_face_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "dream_lift": "COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT",
    "sleep_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
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


def normalize_components(v22: dict[str, Any], v37: dict[str, Any]) -> list[dict[str, Any]]:
    source_lists = (("v22_face", v22.get("components")), ("v37_merged_special", v37.get("components")))
    require(v22.get("locked_v9_source_sha256") == LOCKED and
            v37.get("locked_v9_source", {}).get("sha256") == LOCKED and
            v37.get("runtime_resource_activated") is False and v37.get("active_candidate_binding") == "forbidden",
            "V37 component source lineage or activation boundary drifted")
    result: list[dict[str, Any]] = []
    for pack, raw_components in source_lists:
        expected_count = 37 if pack == "v22_face" else 45
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
            require(isinstance(component_id, int) and component_id > 0 and role in ROLE_ENUM and
                    isinstance(raw.get("name"), str) and isinstance(base, list) and len(base) == 2 and
                    isinstance(offset, dict) and isinstance(offset.get("min"), list) and len(offset["min"]) == 2 and
                    isinstance(offset.get("max"), list) and len(offset["max"]) == 2 and
                    isinstance(size, list) and len(size) == 2 and mask.is_file() and
                    sha256(mask) == str(raw.get("mask_sha256", "")).upper() and
                    raw.get("composite_op") in {"ink", "erase"},
                    f"unregistered component source: {raw.get('name')}")
            result.append({"component_id": component_id, "name": raw["name"], "role": role, "base": base,
                           "offset": offset, "z": raw.get("z_index"), "op": raw["composite_op"], "pack": pack,
                           "mask_bytes": ((size[0] + 7) // 8) * size[1]})
    ids = [component["component_id"] for component in result]
    require(len(result) == 82 and len(ids) == len(set(ids)), "V37 profile component namespace is not exact")
    return sorted(result, key=lambda component: component["component_id"])


def checked_layer(component_by_id: dict[int, dict[str, Any]], component_id: int, offset: list[int], pack: str) -> dict[str, Any]:
    component = component_by_id.get(component_id)
    require(component is not None and component["pack"] == pack and len(offset) == 2 and
            component["offset"]["min"][0] <= offset[0] <= component["offset"]["max"][0] and
            component["offset"]["min"][1] <= offset[1] <= component["offset"]["max"][1],
            f"score uses an illegal component layer: {component_id}")
    return {"component_id": component_id, "offset": offset, "pack": pack}


def build_scores(contract: dict[str, Any], v22: dict[str, Any], components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    component_by_id = {component["component_id"]: component for component in components}
    raw_scores = contract.get("scores")
    require(contract.get("locked_v9_source_sha256") == LOCKED and isinstance(raw_scores, dict),
            "V34/V35 contract lineage drifted")
    scores: list[dict[str, Any]] = []
    for name in SCORE_ORDER[:-1]:
        raw = raw_scores.get(name)
        require(isinstance(raw, dict) and isinstance(raw.get("steps"), list) and len(raw["steps"]) == 3,
                f"V37 must retain three V34/V35 source steps for {name}")
        steps = []
        for step in raw["steps"]:
            layers = [checked_layer(component_by_id, layer["component_id"], list(layer["offset"]),
                                    "v22_face" if layer["component_id"] < 500 else "v37_merged_special")
                      for layer in step["layers"]]
            require(step.get("cue") in PHASE and len(layers) <= 16 and
                    any(layer["component_id"] == 4 and layer["offset"] == [0, 0] for layer in layers) and
                    any(layer["component_id"] >= 500 for layer in layers), "V37 carried score drifted")
            steps.append({"cue": step["cue"], "duration_ms": step["duration_ms"], "layers": layers})
        scores.append({"name": name, "prelude_bridge": raw["prelude_bridge"], "steps": steps})
    bridges = {bridge.get("name"): bridge for bridge in v22.get("bridges", []) if isinstance(bridge, dict)}
    calm = bridges.get("calm__curious")
    require(isinstance(calm, dict) and isinstance(calm.get("frames"), list) and calm["frames"],
            "V22 calm source hold is unavailable")
    source_hold = [checked_layer(component_by_id, layer["component_id"], list(layer["offset"]), "v22_face")
                   for layer in calm["frames"][0]["layers"]]
    sleep_core = [
        checked_layer(component_by_id, 539, [0, 0], "v37_merged_special"),
        checked_layer(component_by_id, 540, [0, 0], "v37_merged_special"),
        checked_layer(component_by_id, 541, [0, 0], "v37_merged_special"),
        checked_layer(component_by_id, 542, [0, 0], "v37_merged_special"),
        checked_layer(component_by_id, 14, [0, 0], "v22_face"),
        checked_layer(component_by_id, 17, [0, 0], "v22_face"),
        checked_layer(component_by_id, 4, [0, 0], "v22_face"),
        checked_layer(component_by_id, 543, [0, 0], "v37_merged_special"),
    ]
    sleep_steps = [
        {"cue": "source_hold", "duration_ms": 420, "layers": source_hold},
        {"cue": "eyes_soften", "duration_ms": 360, "layers": sleep_core},
        {"cue": "lower_face_arrive", "duration_ms": 320,
         "layers": sleep_core + [checked_layer(component_by_id, 544, [0, 0], "v37_merged_special")]},
        {"cue": "dream_lift", "duration_ms": 420,
         "layers": sleep_core + [checked_layer(component_by_id, 544, [0, -1], "v37_merged_special"),
                                  checked_layer(component_by_id, 531, [0, 0], "v37_merged_special")]},
        {"cue": "sleep_hold", "duration_ms": 1400,
         "layers": sleep_core + [checked_layer(component_by_id, 544, [0, -1], "v37_merged_special"),
                                  checked_layer(component_by_id, 532, [0, 0], "v37_merged_special")]},
    ]
    require(all(len(step["layers"]) <= 16 for step in sleep_steps), "sleep score exceeds Rig layer capacity")
    scores.append({"name": "sleepy_dream_cloud", "prelude_bridge": "daily_calm_to_sleepy_component_entry",
                   "steps": sleep_steps})
    return scores


def render_header(component_count: int, max_mask_bytes: int) -> str:
    return f'''/* Generated by tools/generate_companion_v37_sleepy_dream_target_profile.py; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V37_SLEEPY_DREAM_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V37_SLEEPY_DREAM_CANDIDATE_PROFILE_H

#include "expression_rig_performance_score.h"
#include <stdbool.h>
#include <stdint.h>

#define COMP_V37_SLEEPY_DREAM_CANDIDATE_REVISION 37u
#define COMP_V37_SLEEPY_DREAM_CANDIDATE_COMPONENT_COUNT {component_count}u
#define COMP_V37_SLEEPY_DREAM_CANDIDATE_SCORE_COUNT 5u
#define COMP_V37_SLEEPY_DREAM_CANDIDATE_MAX_MASK_BYTES {max_mask_bytes}u
#define COMP_V37_SLEEPY_DREAM_CANDIDATE_SOURCE_SHA256 "{LOCKED}"

typedef struct {{ const char *cue; const char *browser_pbm_filename; uint16_t duration_ms; }}
comp_v37_sleepy_dream_candidate_frame_t;
typedef struct {{ const char *name; const char *prelude_bridge; const comp_expression_rig_registered_performance_score_t *score;
                 const comp_v37_sleepy_dream_candidate_frame_t *frames; uint8_t frame_count; }}
comp_v37_sleepy_dream_candidate_score_t;

const comp_expression_rig_profile_t *comp_v37_sleepy_dream_candidate_profile(void);
bool comp_v37_sleepy_dream_candidate_runtime_activation_allowed(void);
uint8_t comp_v37_sleepy_dream_candidate_score_count(void);
const comp_v37_sleepy_dream_candidate_score_t *comp_v37_sleepy_dream_candidate_score(uint8_t index);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V37_SLEEPY_DREAM_CANDIDATE_PROFILE_H */
'''


def render_source(components: list[dict[str, Any]], scores: list[dict[str, Any]]) -> str:
    lines = ["/* Generated from V22/V34/V35 and locked V9 sleep source components; do not hand edit. */",
             "#include \"expression_rig_v37_sleepy_dream_candidate_profile.h\"", "",
             "static const comp_expression_rig_component_info_t k_v37_components[] = {"]
    for component in components:
        minimum, maximum = component["offset"]["min"], component["offset"]["max"]
        op = "COMP_EXPRESSION_RIG_COMPOSITE_INK" if component["op"] == "ink" else "COMP_EXPRESSION_RIG_COMPOSITE_ERASE"
        lines.append("    {.component_id = %du, .role = %s, .variant = %s, .base_x = %d, .base_y = %d, .min_offset_x = %d, .min_offset_y = %d, .max_offset_x = %d, .max_offset_y = %d, .z_index = %du, .composite_op = %s}," %
                     (component["component_id"], ROLE_ENUM[component["role"]], component_variant(component["name"]),
                      component["base"][0], component["base"][1], minimum[0], minimum[1], maximum[0], maximum[1],
                      component["z"], op))
    lines.extend(["};", "", "static const comp_expression_rig_profile_t k_v37_profile = {",
                  "    .components = k_v37_components,", "    .component_count = COMP_V37_SLEEPY_DREAM_CANDIDATE_COMPONENT_COUNT,",
                  "    .scene_charm_component = {[COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID, [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID},",
                  "    .registered_poses = NULL, .registered_pose_count = 0u,", "};"])
    descriptors = []
    for score_index, score in enumerate(scores):
        scene, emotion = CONTEXT[score["name"]]
        for step_index, step in enumerate(score["steps"]):
            pose = f"k_v37_score_{score_index}_step_{step_index}_pose"
            lines.extend(["", f"static const comp_expression_rig_registered_pose_t {pose} = {{",
                          f"    .scene = {scene}, .emotion = {emotion}, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .layer_count = {len(step['layers'])}u, .layers = {{"])
            lines.extend("        {.component_id = %du, .offset_x = %d, .offset_y = %d, .dynamic_flags = 0u}," %
                         (layer["component_id"], layer["offset"][0], layer["offset"][1]) for layer in step["layers"])
            lines.extend(["    },", "};"])
        lines.extend(["", f"static const comp_expression_rig_registered_score_step_t k_v37_score_{score_index}_steps[] = {{"])
        for step_index, step in enumerate(score["steps"]):
            lines.append("    {.phase = %s, .duration_ms = %du, .state = {.scene = %s, .emotion = %s, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_LOW, .interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v37_score_%d_step_%d_pose}," %
                         (PHASE[step["cue"]], step["duration_ms"], scene, emotion, score_index, step_index))
        lines.extend(["};", f"static const comp_expression_rig_registered_performance_score_t k_v37_score_{score_index} = {{.steps = k_v37_score_{score_index}_steps, .step_count = (uint8_t)(sizeof(k_v37_score_{score_index}_steps) / sizeof(k_v37_score_{score_index}_steps[0]))}};",
                      f"static const comp_v37_sleepy_dream_candidate_frame_t k_v37_score_{score_index}_frames[] = {{"])
        for step_index, step in enumerate(score["steps"]):
            lines.append("    {.cue = %s, .browser_pbm_filename = %s, .duration_ms = %du}," %
                         (c_string(step["cue"]), c_string(f"{score['name']}-{step_index:02d}-{step['cue']}.pbm"), step["duration_ms"]))
        lines.append("};")
        descriptors.append("    {.name = %s, .prelude_bridge = %s, .score = &k_v37_score_%d, .frames = k_v37_score_%d_frames, .frame_count = (uint8_t)(sizeof(k_v37_score_%d_frames) / sizeof(k_v37_score_%d_frames[0]))}," %
                           (c_string(score["name"]), c_string(score["prelude_bridge"]), score_index, score_index, score_index, score_index))
    lines.extend(["", "static const comp_v37_sleepy_dream_candidate_score_t k_v37_scores[] = {", *descriptors, "};", "",
                  "const comp_expression_rig_profile_t *comp_v37_sleepy_dream_candidate_profile(void) { return &k_v37_profile; }",
                  "bool comp_v37_sleepy_dream_candidate_runtime_activation_allowed(void) { return false; }",
                  "uint8_t comp_v37_sleepy_dream_candidate_score_count(void) { return (uint8_t)(sizeof(k_v37_scores) / sizeof(k_v37_scores[0])); }",
                  "const comp_v37_sleepy_dream_candidate_score_t *comp_v37_sleepy_dream_candidate_score(uint8_t index) { return index < comp_v37_sleepy_dream_candidate_score_count() ? &k_v37_scores[index] : NULL; }", ""])
    return "\n".join(lines)


def build_artifacts() -> dict[Path, str]:
    v22, contract, v37 = load(V22), load(V34_CONTRACT), load(V37)
    components = normalize_components(v22, v37)
    scores = build_scores(contract, v22, components)
    max_mask_bytes = max(component["mask_bytes"] for component in components)
    trace = {"schema": "companion.v37_sleepy_dream_wb55_target_profile_plan.v1",
             "status": "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE", "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239"],
             "locked_v9_source_sha256": LOCKED, "runtime_resource_activated": False,
             "active_candidate_binding": "forbidden_until_total_machine_audit_and_owner_review",
             "component_sources": {"v22_face": 37, "v37_merged_special": 45},
             "max_component_mask_bytes": max_mask_bytes, "scores": scores,
             "non_claims": ["no_full_face_card", "no_code_drawn_face", "no_runtime_binding", "no_panel_or_driver_change"]}
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
    print(f"PASS: {'verified' if args.check else 'generated'} inactive V37 WB55 profile with 82 source components and 17 score frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
