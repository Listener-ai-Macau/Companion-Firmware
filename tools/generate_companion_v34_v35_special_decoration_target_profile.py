#!/usr/bin/env python3
"""Generate an inactive WB55 score profile from the special-decoration plan.

This is deliberately a plan compiler, not an art generator.  It copies only
registered source-component IDs, legal offsets, and durations from the browser
score contract into a C profile.  Runtime binding remains forbidden until the
separate browser/WB55 composition-parity gate passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
SPECIAL_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
SCORE_CONTRACT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-score-contract.json"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v34_v35_special_decoration_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v34_v35_special_decoration_candidate_profile.c"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-wb55-target-profile-plan.json"

REVISION = 35
MAX_LAYERS = 16
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
SCORE_CONTEXT = {
    "recording_input": ("COMP_EXPRESSION_RIG_SCENE_RECORDING", "COMP_EXPRESSION_RIG_EMOTION_FOCUSED"),
    "bottom_connector_charging": ("COMP_EXPRESSION_RIG_SCENE_CHARGING", "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE"),
    "curious_question": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_CURIOUS"),
    "alert_exclamation": ("COMP_EXPRESSION_RIG_SCENE_DAILY", "COMP_EXPRESSION_RIG_EMOTION_ALERT"),
}
SCORE_ORDER = tuple(SCORE_CONTEXT)
SCORE_PHASE = {
    "source_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "primary_highlight_lead": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "sparkle_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_or_check(path: Path, text: str, check: bool) -> bool:
    content = text.encode("ascii")
    if check:
        return path.is_file() and path.read_bytes() == content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def c_string(value: str) -> str:
    require(value and all(32 <= ord(char) < 127 and char not in {'"', '\\'} for char in value),
            "generated C string is not safe ASCII")
    return f'"{value}"'


def component_variant(name: str) -> str:
    if name in {
        "left_eye_open", "right_eye_open", "left_eye_highlight_open",
        "right_eye_highlight_open", "left_eye_sparkle_open", "right_eye_sparkle_open",
    }:
        return "COMP_EXPRESSION_RIG_VARIANT_OPEN"
    return "COMP_EXPRESSION_RIG_VARIANT_DEFAULT"


def normalized_components(v22: dict[str, Any], special: dict[str, Any]) -> list[dict[str, Any]]:
    raw_v22 = v22.get("components")
    raw_special = special.get("components")
    require(v22.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            special.get("locked_v9_source_sha256") == LOCKED_V9_SHA256,
            "component layouts do not retain locked V9 lineage")
    require(isinstance(raw_v22, list) and len(raw_v22) == 37 and
            isinstance(raw_special, list) and len(raw_special) == 39,
            "component layouts no longer have the registered V22/V34/V35 counts")
    result: list[dict[str, Any]] = []
    for source_name, records in (("v22_face", raw_v22), ("v34_v35_decoration", raw_special)):
        for raw in records:
            require(isinstance(raw, dict), "component record is invalid")
            component_id = raw.get("component_id")
            name = raw.get("name")
            base = raw.get("base_position")
            offset_range = raw.get("offset_range")
            role = raw.get("role") or "charm"
            mask = ROOT / str(raw.get("mask", ""))
            mask_hash = str(raw.get("mask_sha256", "")).upper()
            size = raw.get("mask_size") or raw.get("size")
            if size is None and isinstance(raw.get("width"), int) and isinstance(raw.get("height"), int):
                size = [raw["width"], raw["height"]]
            require(isinstance(component_id, int) and 0 < component_id < 0xFFFF and
                    isinstance(name, str) and name and role in ROLE_ENUM and
                    isinstance(base, list) and len(base) == 2 and
                    isinstance(offset_range, dict) and isinstance(size, list) and len(size) == 2 and
                    isinstance(offset_range.get("min"), list) and len(offset_range["min"]) == 2 and
                    isinstance(offset_range.get("max"), list) and len(offset_range["max"]) == 2 and
                    all(isinstance(value, int) for value in base + size + offset_range["min"] + offset_range["max"]) and
                    all(-127 <= value <= 127 for value in offset_range["min"] + offset_range["max"]) and
                    offset_range["min"][0] <= offset_range["max"][0] and
                    offset_range["min"][1] <= offset_range["max"][1] and
                    isinstance(raw.get("z_index"), int) and 0 <= raw["z_index"] <= 255 and
                    raw.get("composite_op") in {"ink", "erase"} and mask.is_file() and
                    len(mask_hash) == 64 and sha256(mask) == mask_hash,
                    f"component {name!r} is not a registered source mask")
            result.append({
                "component_id": component_id,
                "name": name,
                "role": role,
                "base_position": base,
                "offset_range": offset_range,
                "z_index": raw["z_index"],
                "composite_op": raw["composite_op"],
                "source_pack": source_name,
            })
    ids = [component["component_id"] for component in result]
    require(len(ids) == len(set(ids)) == 76, "merged target profile has duplicate or missing source component ids")
    return sorted(result, key=lambda component: int(component["component_id"]))


def normalized_scores(contract: dict[str, Any], components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_scores = contract.get("scores")
    require(contract.get("status") == "CANDIDATE_TARGET_PROFILE_PENDING" and
            contract.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            contract.get("runtime_resource_activated") is False and
            contract.get("active_candidate_binding") == "forbidden" and
            isinstance(source_scores, dict) and set(source_scores) == set(SCORE_ORDER) | {"sleepy_dream_cloud"},
            "special score contract activation or vocabulary drifted")
    dream = source_scores["sleepy_dream_cloud"]
    require(isinstance(dream, dict) and dream.get("runtime_binding") == "fail_closed_pending_v9_sleep_profile" and
            not dream.get("steps"), "dream-cloud must stay fail-closed without a V9 sleepy face profile")
    by_id = {component["component_id"]: component for component in components}
    result: list[dict[str, Any]] = []
    for name in SCORE_ORDER:
        raw = source_scores[name]
        require(isinstance(raw, dict) and raw.get("runtime_binding") ==
                "forbidden_until_target_replay_and_owner_review" and
                isinstance(raw.get("prelude_bridge"), str) and
                isinstance(raw.get("steps"), list) and len(raw["steps"]) == 3,
                f"{name} is not a candidate-only three-step score")
        steps: list[dict[str, Any]] = []
        for step in raw["steps"]:
            require(isinstance(step, dict) and step.get("cue") in SCORE_PHASE and
                    isinstance(step.get("duration_ms"), int) and 80 <= step["duration_ms"] <= 5000 and
                    isinstance(step.get("layers"), list) and 0 < len(step["layers"]) <= MAX_LAYERS,
                    f"{name} step is invalid")
            seen: set[int] = set()
            layers: list[dict[str, Any]] = []
            has_special = False
            nose_ok = False
            for layer in step["layers"]:
                require(isinstance(layer, dict), f"{name} layer is invalid")
                component_id = layer.get("component_id")
                offset = layer.get("offset")
                component = by_id.get(component_id)
                expected_pack = "v22_face" if isinstance(component_id, int) and component_id < 500 else "v34_v35_decoration"
                require(component is not None and component_id not in seen and
                        isinstance(offset, list) and len(offset) == 2 and
                        all(isinstance(value, int) and -127 <= value <= 127 for value in offset) and
                        layer.get("pack") == expected_pack == component["source_pack"] and
                        component["offset_range"]["min"][0] <= offset[0] <= component["offset_range"]["max"][0] and
                        component["offset_range"]["min"][1] <= offset[1] <= component["offset_range"]["max"][1],
                        f"{name} layer is outside its registered source component contract")
                seen.add(component_id)
                has_special = has_special or component_id >= 500
                nose_ok = nose_ok or (component_id == 4 and offset == [0, 0])
                layers.append({"component_id": component_id, "offset": offset, "pack": expected_pack})
            require(has_special and nose_ok, f"{name} does not preserve the fixed V9 nose or special marker")
            steps.append({"cue": step["cue"], "duration_ms": step["duration_ms"], "layers": layers})
        result.append({"name": name, "prelude_bridge": raw["prelude_bridge"], "steps": steps})
    return result


def render_header(component_count: int, score_count: int) -> str:
    return f'''/* Generated by tools/generate_companion_v34_v35_special_decoration_target_profile.py; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V34_V35_SPECIAL_DECORATION_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V34_V35_SPECIAL_DECORATION_CANDIDATE_PROFILE_H

#include "expression_rig_performance_score.h"

#include <stdbool.h>
#include <stdint.h>

#define COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_REVISION {REVISION}u
#define COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_COMPONENT_COUNT {component_count}u
#define COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_SCORE_COUNT {score_count}u
#define COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_SOURCE_SHA256 "{LOCKED_V9_SHA256}"

typedef struct {{
    const char *cue;
    const char *browser_pbm_filename;
    uint16_t duration_ms;
}} comp_v34_v35_special_decoration_candidate_frame_t;

typedef struct {{
    const char *name;
    const char *prelude_bridge;
    const comp_expression_rig_registered_performance_score_t *score;
    const comp_v34_v35_special_decoration_candidate_frame_t *frames;
    uint8_t frame_count;
}} comp_v34_v35_special_decoration_candidate_score_t;

const comp_expression_rig_profile_t *comp_v34_v35_special_decoration_candidate_profile(void);
bool comp_v34_v35_special_decoration_candidate_runtime_activation_allowed(void);
uint8_t comp_v34_v35_special_decoration_candidate_score_count(void);
const comp_v34_v35_special_decoration_candidate_score_t *
comp_v34_v35_special_decoration_candidate_score(uint8_t index);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V34_V35_SPECIAL_DECORATION_CANDIDATE_PROFILE_H */
'''


def render_source(components: list[dict[str, Any]], scores: list[dict[str, Any]]) -> str:
    component_lines = []
    for component in components:
        minimum = component["offset_range"]["min"]
        maximum = component["offset_range"]["max"]
        op = "COMP_EXPRESSION_RIG_COMPOSITE_INK" if component["composite_op"] == "ink" else "COMP_EXPRESSION_RIG_COMPOSITE_ERASE"
        component_lines.append(
            "    {.component_id = %du, .role = %s, .variant = %s, .base_x = %d, .base_y = %d, "
            ".min_offset_x = %d, .min_offset_y = %d, .max_offset_x = %d, .max_offset_y = %d, "
            ".z_index = %du, .composite_op = %s}," % (
                component["component_id"], ROLE_ENUM[component["role"]], component_variant(component["name"]),
                component["base_position"][0], component["base_position"][1], minimum[0], minimum[1],
                maximum[0], maximum[1], component["z_index"], op))
    blocks = [
        "/* Generated from V22/V34/V35 registered component score contracts; do not hand edit. */",
        "#include \"expression_rig_v34_v35_special_decoration_candidate_profile.h\"",
        "",
        "static const comp_expression_rig_component_info_t k_v34_v35_components[] = {",
        "\n".join(component_lines),
        "};",
        "",
        "static const comp_expression_rig_profile_t k_v34_v35_profile = {",
        "    .components = k_v34_v35_components,",
        "    .component_count = COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_COMPONENT_COUNT,",
        "    .scene_charm_component = {",
        "        [COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "    },",
        "    /* Duplicate role variants deliberately disable generic state synthesis. */",
        "    .registered_poses = NULL,",
        "    .registered_pose_count = 0u,",
        "};",
    ]
    descriptor_lines = []
    for score_index, score in enumerate(scores):
        score_symbol = f"k_v34_v35_score_{score_index}"
        for step_index, step in enumerate(score["steps"]):
            pose_symbol = f"k_v34_v35_score_{score_index}_step_{step_index}_pose"
            scene, emotion = SCORE_CONTEXT[score["name"]]
            layer_lines = [
                "            {.component_id = %du, .offset_x = %d, .offset_y = %d, .dynamic_flags = 0u}," %
                (layer["component_id"], layer["offset"][0], layer["offset"][1])
                for layer in step["layers"]
            ]
            blocks.extend([
                "",
                f"static const comp_expression_rig_registered_pose_t {pose_symbol} = {{",
                f"    .scene = {scene}, .emotion = {emotion},",
                "    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,",
                f"    .layer_count = {len(step['layers'])}u,",
                "    .layers = {",
                "\n".join(layer_lines),
                "    },",
                "};",
            ])
        step_lines = []
        for step_index, step in enumerate(score["steps"]):
            scene, emotion = SCORE_CONTEXT[score["name"]]
            step_lines.append(
                "    {.phase = %s, .duration_ms = %du, .state = {.scene = %s, .emotion = %s, "
                ".attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, "
                ".interaction_memory = 0u, .phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &k_v34_v35_score_%d_step_%d_pose}," %
                (SCORE_PHASE[step["cue"]], step["duration_ms"], scene, emotion, score_index, step_index))
        blocks.extend([
            "",
            f"static const comp_expression_rig_registered_score_step_t k_v34_v35_score_{score_index}_steps[] = {{",
            "\n".join(step_lines),
            "};",
            "",
            f"static const comp_expression_rig_registered_performance_score_t {score_symbol} = {{",
            f"    .steps = k_v34_v35_score_{score_index}_steps,",
            f"    .step_count = (uint8_t)(sizeof(k_v34_v35_score_{score_index}_steps) / sizeof(k_v34_v35_score_{score_index}_steps[0])),",
            "};",
        ])
        frame_lines = [
            "    {.cue = %s, .browser_pbm_filename = %s, .duration_ms = %du}," %
            (c_string(step["cue"]), c_string(f"{score['name']}-{step_index:02d}-{step['cue']}.pbm"),
             step["duration_ms"])
            for step_index, step in enumerate(score["steps"])
        ]
        blocks.extend([
            "",
            f"static const comp_v34_v35_special_decoration_candidate_frame_t k_v34_v35_score_{score_index}_frames[] = {{",
            "\n".join(frame_lines),
            "};",
        ])
        descriptor_lines.append(
            "    {.name = %s, .prelude_bridge = %s, .score = &%s, .frames = k_v34_v35_score_%d_frames, "
            ".frame_count = (uint8_t)(sizeof(k_v34_v35_score_%d_frames) / sizeof(k_v34_v35_score_%d_frames[0]))}," %
            (c_string(score["name"]), c_string(score["prelude_bridge"]), score_symbol, score_index,
             score_index, score_index))
    blocks.extend([
        "",
        "static const comp_v34_v35_special_decoration_candidate_score_t k_v34_v35_scores[] = {",
        "\n".join(descriptor_lines),
        "};",
        "",
        "const comp_expression_rig_profile_t *comp_v34_v35_special_decoration_candidate_profile(void)",
        "{",
        "    return &k_v34_v35_profile;",
        "}",
        "",
        "bool comp_v34_v35_special_decoration_candidate_runtime_activation_allowed(void)",
        "{",
        "    return false;",
        "}",
        "",
        "uint8_t comp_v34_v35_special_decoration_candidate_score_count(void)",
        "{",
        "    return (uint8_t)(sizeof(k_v34_v35_scores) / sizeof(k_v34_v35_scores[0]));",
        "}",
        "",
        "const comp_v34_v35_special_decoration_candidate_score_t *",
        "comp_v34_v35_special_decoration_candidate_score(uint8_t index)",
        "{",
        "    if (index >= comp_v34_v35_special_decoration_candidate_score_count()) {",
        "        return NULL;",
        "    }",
        "    return &k_v34_v35_scores[index];",
        "}",
        "",
    ])
    return "\n".join(blocks)


def build_artifacts() -> dict[Path, str]:
    v22 = load_json(V22_LAYOUT)
    special = load_json(SPECIAL_LAYOUT)
    contract = load_json(SCORE_CONTRACT)
    components = normalized_components(v22, special)
    scores = normalized_scores(contract, components)
    trace = {
        "schema": "companion.v34_v35_special_decoration_wb55_target_profile_plan.v1",
        "status": "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233"],
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_wb55_component_plan_parity_and_owner_review",
        "component_sources": {
            "v22_face": {"component_count": 37, "layout": rel(V22_LAYOUT)},
            "v34_v35_decoration": {"component_count": 39, "layout": rel(SPECIAL_LAYOUT)},
        },
        "scores": scores,
        "fail_closed": {"sleepy_dream_cloud": "pending_v9_sleep_profile", "runtime_special_event_binding": "forbidden"},
        "non_claims": ["no_full_face_card", "no_code_drawn_face", "no_runtime_binding", "no_panel_or_driver_change"],
    }
    return {
        HEADER: render_header(len(components), len(scores)),
        SOURCE: render_source(components, scores),
        TRACE: json.dumps(trace, indent=2, ensure_ascii=True) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated outputs without writing")
    args = parser.parse_args()
    artifacts = build_artifacts()
    drifted = [path for path, text in artifacts.items() if not write_or_check(path, text, args.check)]
    if drifted:
        for path in drifted:
            print(f"ERROR: generated artifact drifted: {rel(path)}")
        return 1
    action = "verified" if args.check else "generated"
    print(f"PASS: {action} inactive WB55 special-decoration score profile with 76 registered source components and 4 score plans; dream remains fail-closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
