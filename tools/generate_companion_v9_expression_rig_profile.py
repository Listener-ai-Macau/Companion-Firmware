#!/usr/bin/env python3
"""Generate the inactive WB55/WBA v9 Rig profile from its audited layout."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
DEFAULT_HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v9_candidate_profile.h"
DEFAULT_SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v9_candidate_profile.c"

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
    "left_detail": "COMP_EXPRESSION_RIG_ROLE_LEFT_DETAIL",
    "right_detail": "COMP_EXPRESSION_RIG_ROLE_RIGHT_DETAIL",
    "charm": "COMP_EXPRESSION_RIG_ROLE_CHARM",
}
COMPOSITE_OP_ENUM = {
    "ink": "COMP_EXPRESSION_RIG_COMPOSITE_INK",
    "erase": "COMP_EXPRESSION_RIG_COMPOSITE_ERASE",
}
VARIANT_ENUM = {
    "default": "COMP_EXPRESSION_RIG_VARIANT_DEFAULT",
    "open": "COMP_EXPRESSION_RIG_VARIANT_OPEN",
    "sleepy": "COMP_EXPRESSION_RIG_VARIANT_SLEEPY",
    "swipe": "COMP_EXPRESSION_RIG_VARIANT_SWIPE",
}
SCENE_ENUM = {
    "daily": "COMP_EXPRESSION_RIG_SCENE_DAILY",
    "touch": "COMP_EXPRESSION_RIG_SCENE_TOUCH",
    "swipe": "COMP_EXPRESSION_RIG_SCENE_SWIPE",
    "recording": "COMP_EXPRESSION_RIG_SCENE_RECORDING",
    "menu": "COMP_EXPRESSION_RIG_SCENE_MENU",
    "sleep": "COMP_EXPRESSION_RIG_SCENE_SLEEP",
    "charging": "COMP_EXPRESSION_RIG_SCENE_CHARGING",
    "error": "COMP_EXPRESSION_RIG_SCENE_ERROR",
}
SCORE_PHASE_ENUM = {
    "entry": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "prepare": "COMP_EXPRESSION_RIG_SCORE_PHASE_PREPARE",
    "lead": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "response": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "accent": "COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT",
    "hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
    "release": "COMP_EXPRESSION_RIG_SCORE_PHASE_RELEASE",
    "return": "COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN",
    "settle": "COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE",
}
DAILY_ATTENTION_ENUM = {
    "daily_left": "COMP_EXPRESSION_RIG_ATTENTION_LEFT",
    "daily_right": "COMP_EXPRESSION_RIG_ATTENTION_RIGHT",
    "daily_up": "COMP_EXPRESSION_RIG_ATTENTION_UP",
    "daily_down": "COMP_EXPRESSION_RIG_ATTENTION_DOWN",
}


def require(value: object, description: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{description} must be a non-empty string")
    return value


def pair(value: object, description: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{description} must be an integer pair")
    return value[0], value[1]


def panel_presentation_story_order(layout: dict[str, object]) -> tuple[str, ...]:
    choreography = layout.get("preview_choreography")
    if not isinstance(choreography, dict):
        raise ValueError("preview_choreography must be an object")
    presentation = choreography.get("panel_presentation")
    if not isinstance(presentation, dict):
        raise ValueError("layout must declare the dedicated Daily panel presentation contract")
    replay_mode = presentation.get("replay_mode")
    story_order = presentation.get("story_order")
    if replay_mode != "continuous_story_cycle" or not isinstance(story_order, list) or \
            tuple(story_order) != tuple(DAILY_ATTENTION_ENUM):
        raise ValueError("Daily panel presentation must declare the shared continuous story order")
    return tuple(story_order)


def render_header(layout: dict[str, object]) -> str:
    baseline = layout.get("source_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("source_baseline must be an object")
    revision = layout.get("revision")
    components = layout.get("components")
    if not isinstance(revision, int) or not isinstance(components, list) or not components:
        raise ValueError("layout needs revision and components")
    source_sha = require(baseline.get("sha256"), "source_baseline.sha256")
    prompt_revision = require(baseline.get("prompt_revision"), "source_baseline.prompt_revision")
    choreography = layout.get("preview_choreography")
    if not isinstance(choreography, dict):
        raise ValueError("preview_choreography must be an object")
    presentation = choreography.get("panel_presentation")
    if not isinstance(presentation, dict) or \
            presentation.get("schema") != "companion.v9_expression_rig_panel_presentation.v1" or \
            presentation.get("scope") != "dedicated_daily_rig_demo_only":
        raise ValueError("layout must declare the dedicated Daily panel presentation contract")
    initial_dwell = presentation.get("initial_baseline_min_dwell_ms")
    minimum_dwell = presentation.get("minimum_step_dwell_ms")
    partial_limit = presentation.get("partial_limit")
    story_order = panel_presentation_story_order(layout)
    if not isinstance(initial_dwell, int) or not 750 <= initial_dwell <= 3000 or \
            not isinstance(minimum_dwell, int) or not 650 <= minimum_dwell <= initial_dwell or \
            not isinstance(partial_limit, int) or \
            not (14 <= partial_limit <= 64 or partial_limit == 255):
        raise ValueError("Daily panel presentation values are invalid")
    return f"""/* Generated from {DEFAULT_LAYOUT.relative_to(ROOT).as_posix()}; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V9_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V9_CANDIDATE_PROFILE_H

#include \"expression_rig_performance_score.h\"

#include <stdbool.h>

#define COMP_V9_EXPRESSION_RIG_CANDIDATE_REVISION {revision}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT {len(components)}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_DAILY_SCORE_COUNT {len(DAILY_ATTENTION_ENUM)}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_SOURCE_SHA256 \"{source_sha}\"
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PROMPT_REVISION \"{prompt_revision}\"
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_INITIAL_DWELL_MS {initial_dwell}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_MINIMUM_DWELL_MS {minimum_dwell}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_PARTIAL_LIMIT {partial_limit}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_STORY_COUNT {len(story_order)}u
#define COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_CONTINUOUS_REPLAY 1u

const comp_expression_rig_profile_t *comp_v9_expression_rig_candidate_profile(void);
const comp_expression_rig_performance_score_t *comp_v9_expression_rig_candidate_daily_score(
    comp_expression_rig_attention_t attention);
uint8_t comp_v9_expression_rig_candidate_daily_presentation_story_count(void);
bool comp_v9_expression_rig_candidate_daily_presentation_attention(
    uint8_t story_index,
    comp_expression_rig_attention_t *out_attention);

/* Candidate art never activates itself. A separate owner visual gate controls
 * any future runtime binding. */
bool comp_v9_expression_rig_candidate_runtime_activation_allowed(void);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V9_CANDIDATE_PROFILE_H */
"""


def render_daily_score_source(layout: dict[str, object], ids: dict[str, int]) -> str:
    choreography = layout.get("preview_choreography")
    if not isinstance(choreography, dict) or \
            choreography.get("schema") != "companion.v9_expression_rig_performance_score.v2":
        raise ValueError("layout must declare the v2 component performance score")
    performances = choreography.get("performances")
    if not isinstance(performances, list):
        raise ValueError("performance score has no performances")
    story_order = panel_presentation_story_order(layout)
    daily_reflection_targets = {
        "daily_left": (-1, 2),
        "daily_right": (1, 2),
        "daily_up": (0, 1),
        "daily_down": (0, 2),
    }
    daily_reflection_rest = (0, 2)
    daily_reflection_corridors = {
        "daily_left": {(0, 0), (0, 1), daily_reflection_rest, (-1, 2)},
        "daily_right": {(0, 0), (0, 1), daily_reflection_rest, (1, 2)},
        "daily_up": {(0, 0), (0, 1), daily_reflection_rest},
        "daily_down": {(0, 0), (0, 1), daily_reflection_rest},
    }
    reflection_pairs = (
        ("left_eye_highlight_open", "left_eye_sparkle_open"),
        ("right_eye_highlight_open", "right_eye_sparkle_open"),
    )
    blocks: list[str] = []
    score_names: list[str] = []
    seen: set[str] = set()
    for performance in performances:
        if not isinstance(performance, dict):
            raise ValueError("performance score item must be an object")
        name = require(performance.get("name"), "performance.name")
        raw_score = performance.get("score")
        if name not in DAILY_ATTENTION_ENUM or name in seen or not isinstance(raw_score, list) or not raw_score:
            raise ValueError(f"unsupported or duplicate Daily performance score {name}")
        seen.add(name)
        current: dict[str, tuple[int, int]] = {}
        target_reflection = daily_reflection_targets[name]
        reflection_corridor = daily_reflection_corridors[name]
        previous_reflections = {primary_name: (0, 0) for primary_name, _ in reflection_pairs}
        reached_shared_rest = False
        reached_target = False
        step_lines: list[str] = []
        pose_blocks: list[str] = []
        for step_index, raw_step in enumerate(raw_score):
            if not isinstance(raw_step, dict):
                raise ValueError(f"Daily score {name} step {step_index} must be an object")
            phase = require(raw_step.get("phase"), f"Daily score {name} step.phase")
            duration_ms = raw_step.get("duration_ms")
            raw_poses = raw_step.get("poses")
            return_to_entry = raw_step.get("return_to_entry", False)
            if phase not in SCORE_PHASE_ENUM or not isinstance(duration_ms, int) or \
                    not 80 <= duration_ms <= 1500 or not isinstance(raw_poses, dict) or \
                    not isinstance(return_to_entry, bool):
                raise ValueError(f"Daily score {name} step {step_index} is invalid")
            if return_to_entry:
                current = {}
            for component_name, raw_offset in raw_poses.items():
                if component_name not in ids:
                    raise ValueError(f"Daily score {name} references unknown component {component_name}")
                current[component_name] = pair(raw_offset, f"Daily score {name} pose {component_name}")
            for primary_name, sparkle_name in reflection_pairs:
                current_reflection = current.get(primary_name, (0, 0))
                if current_reflection != current.get(sparkle_name, (0, 0)):
                    raise ValueError(
                        f"Daily score {name} splits the paired reflection {primary_name}/{sparkle_name}"
                    )
                if current_reflection not in reflection_corridor:
                    raise ValueError(f"Daily score {name} leaves its calibrated V9 dynamic-rest corridor")
                previous = previous_reflections[primary_name]
                if abs(current_reflection[0] - previous[0]) > 1 or \
                        abs(current_reflection[1] - previous[1]) > 1:
                    raise ValueError(f"Daily score {name} primary highlight jumps more than one pixel")
                previous_reflections[primary_name] = current_reflection
            reached_shared_rest = reached_shared_rest or all(
                current.get(primary_name, (0, 0)) == daily_reflection_rest
                for primary_name, _ in reflection_pairs
            )
            if reached_shared_rest:
                reached_target = reached_target or all(
                    current.get(primary_name, (0, 0)) == target_reflection
                    for primary_name, _ in reflection_pairs
                )
            active_poses = [(component_name, offset) for component_name, offset in current.items()
                            if offset != (0, 0)]
            pose_name = f"k_{name}_step_{step_index}_poses"
            if active_poses:
                pose_blocks.append(
                    f"static const comp_expression_rig_score_pose_t {pose_name}[] = {{\n" +
                    "\n".join(
                        f"    {{{ids[component_name]}u, {offset[0]}, {offset[1]}}},"
                        for component_name, offset in active_poses
                    ) + "\n};"
                )
                pose_ref = pose_name
                pose_count = f"(uint8_t)(sizeof({pose_name}) / sizeof({pose_name}[0]))"
            else:
                pose_ref = "NULL"
                pose_count = "0u"
            step_lines.append(
                f"    {{{SCORE_PHASE_ENUM[phase]}, {duration_ms}u, {pose_ref}, {pose_count}}},"
            )
        blocks.append(
            "\n".join(pose_blocks) + "\n\n" +
            f"static const comp_expression_rig_score_step_t k_{name}_steps[] = {{\n" +
            "\n".join(step_lines) + "\n};\n\n" +
            f"static const comp_expression_rig_performance_score_t k_{name}_score = {{\n" +
            f"    .steps = k_{name}_steps,\n" +
            f"    .step_count = (uint8_t)(sizeof(k_{name}_steps) / sizeof(k_{name}_steps[0])),\n" +
            "};"
        )
        score_names.append(name)
        if not reached_shared_rest:
            raise ValueError(f"Daily score {name} must reach the V9 dynamic rest anchor")
        if not reached_target:
            raise ValueError(f"Daily score {name} must lead from dynamic rest to its calibrated target")
    if set(score_names) != set(DAILY_ATTENTION_ENUM):
        raise ValueError("Daily performance score must cover left, right, up and down exactly once")
    cases = "\n".join(
        f"    case {DAILY_ATTENTION_ENUM[name]}: return &k_{name}_score;"
        for name in DAILY_ATTENTION_ENUM
    )
    presentation_order = ", ".join(DAILY_ATTENTION_ENUM[name] for name in story_order)
    return "\n\n".join(blocks) + "\n\n" + f"""static const comp_expression_rig_attention_t k_v9_candidate_daily_presentation_order[] = {{
    {presentation_order},
}};

uint8_t comp_v9_expression_rig_candidate_daily_presentation_story_count(void)
{{
    return (uint8_t)(sizeof(k_v9_candidate_daily_presentation_order) /
                     sizeof(k_v9_candidate_daily_presentation_order[0]));
}}

bool comp_v9_expression_rig_candidate_daily_presentation_attention(
    uint8_t story_index,
    comp_expression_rig_attention_t *out_attention)
{{
    if (out_attention == NULL ||
        story_index >= comp_v9_expression_rig_candidate_daily_presentation_story_count()) {{
        return false;
    }}
    *out_attention = k_v9_candidate_daily_presentation_order[story_index];
    return true;
}}

const comp_expression_rig_performance_score_t *comp_v9_expression_rig_candidate_daily_score(
    comp_expression_rig_attention_t attention)
{{
    switch (attention) {{
{cases}
    case COMP_EXPRESSION_RIG_ATTENTION_CENTER:
    case COMP_EXPRESSION_RIG_ATTENTION_COUNT:
    default:
        return NULL;
    }}
}}
"""


def render_source(layout: dict[str, object]) -> str:
    components = layout.get("components")
    charms = layout.get("scene_charms")
    if not isinstance(components, list) or not isinstance(charms, dict):
        raise ValueError("layout needs components and scene_charms")
    ids: dict[str, int] = {}
    lines: list[str] = []
    for index, item in enumerate(components, start=1):
        if not isinstance(item, dict):
            raise ValueError("component must be an object")
        name = require(item.get("name"), "component.name")
        role = require(item.get("role"), f"component {name}.role")
        variant = require(item.get("variant", "default"), f"component {name}.variant")
        composite_op = require(item.get("composite_op", "ink"), f"component {name}.composite_op")
        if role == "charm":
            variant = "default"
        if name in ids or role not in ROLE_ENUM or variant not in VARIANT_ENUM or composite_op not in COMPOSITE_OP_ENUM:
            raise ValueError(f"unsupported or duplicate component {name}")
        base_x, base_y = pair(item.get("base_position"), f"component {name}.base_position")
        ranges = item.get("offset_range")
        if not isinstance(ranges, dict):
            raise ValueError(f"component {name}.offset_range must be an object")
        min_x, min_y = pair(ranges.get("min"), f"component {name}.offset_range.min")
        max_x, max_y = pair(ranges.get("max"), f"component {name}.offset_range.max")
        z_index = item.get("z_index")
        if not isinstance(z_index, int) or not 0 <= z_index <= 255:
            raise ValueError(f"component {name}.z_index must fit uint8")
        ids[name] = index
        lines.append(
            "    {"
            f".component_id = {index}u, .role = {ROLE_ENUM[role]}, "
            f".variant = {VARIANT_ENUM[variant]}, .base_x = {base_x}, .base_y = {base_y}, "
            f".min_offset_x = {min_x}, .min_offset_y = {min_y}, "
            f".max_offset_x = {max_x}, .max_offset_y = {max_y}, .z_index = {z_index}u, "
            f".composite_op = {COMPOSITE_OP_ENUM[composite_op]}"
            "},"
        )
    charm_lines: list[str] = []
    for scene, enum_name in SCENE_ENUM.items():
        charm = charms.get(scene)
        component_id = ids.get(charm, "COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID")
        charm_lines.append(f"        [{enum_name}] = {component_id},")
    profile_source = """/* Generated from the owner-reviewed v9 Rig layout; do not hand edit. */
#include "expression_rig_v9_candidate_profile.h"

static const comp_expression_rig_component_info_t k_v9_candidate_components[] = {
%s
};

static const comp_expression_rig_profile_t k_v9_candidate_profile = {
    .components = k_v9_candidate_components,
    .component_count = COMP_V9_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT,
    .scene_charm_component = {
%s
    },
};

const comp_expression_rig_profile_t *comp_v9_expression_rig_candidate_profile(void)
{
    return &k_v9_candidate_profile;
}

bool comp_v9_expression_rig_candidate_runtime_activation_allowed(void)
{
    return false;
}
""" % ("\n".join(lines), "\n".join(charm_lines))
    return profile_source + "\n" + render_daily_score_source(layout, ids)


def write_or_check(path: pathlib.Path, content: str, check: bool) -> bool:
    if check:
        return path.is_file() and path.read_text(encoding="ascii") == content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="ascii", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=pathlib.Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--header", type=pathlib.Path, default=DEFAULT_HEADER)
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        layout = json.loads(args.layout.resolve().read_text(encoding="utf-8"))
        header = render_header(layout)
        source = render_source(layout)
        header_ok = write_or_check(args.header.resolve(), header, args.check)
        source_ok = write_or_check(args.source.resolve(), source, args.check)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if not header_ok or not source_ok:
        print("FAIL: generated v9 Rig profile drifted")
        return 1
    print("PASS: v9 Rig profile is generated deterministically from the audited layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
