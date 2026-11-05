#!/usr/bin/env python3
"""Generate the inactive expanded V9 registered-pose C profile from its layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v2-expanded-source/candidate/rig-layout.json"
DEFAULT_HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v9_expanded_candidate_profile.h"
DEFAULT_SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v9_expanded_candidate_profile.c"

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
    "cheek_pair": "COMP_EXPRESSION_RIG_ROLE_CHEEK_PAIR",
    "listening_detail": "COMP_EXPRESSION_RIG_ROLE_LISTENING_DETAIL",
}
SCENE_ENUM = {
    "daily": "COMP_EXPRESSION_RIG_SCENE_DAILY",
    "touch": "COMP_EXPRESSION_RIG_SCENE_TOUCH",
    "swipe": "COMP_EXPRESSION_RIG_SCENE_SWIPE",
    "recording": "COMP_EXPRESSION_RIG_SCENE_RECORDING",
    "menu": "COMP_EXPRESSION_RIG_SCENE_MENU",
    "sleep": "COMP_EXPRESSION_RIG_SCENE_SLEEP",
}
EMOTION_ENUM = {
    "calm": "COMP_EXPRESSION_RIG_EMOTION_CALM",
    "curious": "COMP_EXPRESSION_RIG_EMOTION_CURIOUS",
    "affectionate": "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE",
    "focused": "COMP_EXPRESSION_RIG_EMOTION_FOCUSED",
    "sleepy": "COMP_EXPRESSION_RIG_EMOTION_SLEEPY",
    "alert": "COMP_EXPRESSION_RIG_EMOTION_ALERT",
    "joyful": "COMP_EXPRESSION_RIG_EMOTION_JOYFUL",
    "playful": "COMP_EXPRESSION_RIG_EMOTION_PLAYFUL",
    "anticipatory": "COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY",
    "puzzled": "COMP_EXPRESSION_RIG_EMOTION_PUZZLED",
    "listening": "COMP_EXPRESSION_RIG_EMOTION_LISTENING",
    "thinking": "COMP_EXPRESSION_RIG_EMOTION_THINKING",
}
ATTENTION_ENUM = {
    "center": "COMP_EXPRESSION_RIG_ATTENTION_CENTER",
    "left": "COMP_EXPRESSION_RIG_ATTENTION_LEFT",
    "right": "COMP_EXPRESSION_RIG_ATTENTION_RIGHT",
    "up": "COMP_EXPRESSION_RIG_ATTENTION_UP",
    "down": "COMP_EXPRESSION_RIG_ATTENTION_DOWN",
}
COMPOSITE_ENUM = {
    "ink": "COMP_EXPRESSION_RIG_COMPOSITE_INK",
    "erase": "COMP_EXPRESSION_RIG_COMPOSITE_ERASE",
}
ATTENTION_OFFSET = {
    "center": (0, 0), "left": (-2, 0), "right": (2, 0), "up": (1, -2), "down": (1, 3),
}
ENERGY_ENUM = {
    "low": "COMP_EXPRESSION_RIG_ENERGY_LOW",
    "normal": "COMP_EXPRESSION_RIG_ENERGY_NORMAL",
    "high": "COMP_EXPRESSION_RIG_ENERGY_HIGH",
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
MOTION_FLAG_ENUM = {
    "energy_y": "COMP_EXPRESSION_RIG_POSE_DYNAMIC_ENERGY_Y",
    "memory_x": "COMP_EXPRESSION_RIG_POSE_DYNAMIC_MEMORY_X",
}


def require_string(value: object, description: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{description} must be a non-empty string")
    return value


def pair(value: object, description: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{description} must be an integer pair")
    return value[0], value[1]


def source_sha(layout: dict[str, object]) -> str:
    baseline = layout.get("source_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("layout lacks source baseline")
    value = require_string(baseline.get("sha256"), "source baseline sha256").upper()
    if len(value) != 64 or any(char not in "0123456789ABCDEF" for char in value):
        raise ValueError("source baseline sha256 is invalid")
    return value


def load_components(layout: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    raw = layout.get("components")
    if not isinstance(raw, list) or not raw:
        raise ValueError("layout lacks components")
    components: list[dict[str, object]] = []
    by_name: dict[str, dict[str, object]] = {}
    for expected_id, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError("component must be an object")
        name = require_string(item.get("name"), "component name")
        role = require_string(item.get("role"), f"component {name} role")
        if name in by_name or role not in ROLE_ENUM or item.get("component_id") != expected_id:
            raise ValueError(f"component identity/role is invalid: {name}")
        base_x, base_y = pair(item.get("base_position"), f"component {name} position")
        ranges = item.get("offset_range")
        if not isinstance(ranges, dict):
            raise ValueError(f"component {name} lacks offset range")
        min_x, min_y = pair(ranges.get("min"), f"component {name} min offset")
        max_x, max_y = pair(ranges.get("max"), f"component {name} max offset")
        z = item.get("z_index")
        composite = require_string(item.get("composite_op"), f"component {name} composite")
        if not isinstance(z, int) or not 0 <= z <= 255 or composite not in COMPOSITE_ENUM:
            raise ValueError(f"component metadata is invalid: {name}")
        if min_x > max_x or min_y > max_y:
            raise ValueError(f"component offsets are inverted: {name}")
        motion_flags = item.get("motion_flags")
        if not isinstance(motion_flags, list) or not all(
                isinstance(flag, str) and flag in MOTION_FLAG_ENUM for flag in motion_flags):
            raise ValueError(f"component motion flags are invalid: {name}")
        components.append(item)
        by_name[name] = item
    return components, by_name


def dynamic_flags(component: dict[str, object]) -> str:
    flags = component.get("motion_flags")
    if not isinstance(flags, list):
        raise ValueError(f"component lacks motion flags: {component.get('name')}")
    return " | ".join(MOTION_FLAG_ENUM[str(flag)] for flag in flags) if flags else "0u"


def state_map(layout: dict[str, object]) -> dict[str, dict[str, object]]:
    matrix = layout.get("state_matrix")
    rejected = layout.get("owner_rejected_states_fail_closed")
    if not isinstance(rejected, dict) or set(rejected) != {"sleep_rest_no_moon"}:
        raise ValueError("expanded layout must record the rejected sleep state as fail-closed")
    sleep = rejected.get("sleep_rest_no_moon")
    if not isinstance(sleep, dict) or sleep.get("scene") != "sleep" or sleep.get("emotion") != "sleepy" or \
            sleep.get("active_candidate_binding") != "forbidden":
        raise ValueError("rejected sleep state is not fail-closed")
    if not isinstance(matrix, list) or len(matrix) != 15:
        raise ValueError("expanded layout must contain exactly fifteen active state rows")
    result: dict[str, dict[str, object]] = {}
    for item in matrix:
        if not isinstance(item, dict):
            raise ValueError("state row must be an object")
        name = require_string(item.get("name"), "state name")
        scene = require_string(item.get("scene"), f"state {name} scene")
        emotion = require_string(item.get("emotion"), f"state {name} emotion")
        attention = require_string(item.get("attention"), f"state {name} attention")
        energy = require_string(item.get("energy"), f"state {name} energy")
        interaction_memory = item.get("interaction_memory")
        if name in result or scene not in SCENE_ENUM or emotion not in EMOTION_ENUM or \
                attention not in ATTENTION_ENUM or energy not in ENERGY_ENUM or \
                not isinstance(interaction_memory, int) or not 0 <= interaction_memory <= 2:
            raise ValueError(f"unsupported state row: {name}")
        if name in rejected or scene == "sleep":
            raise ValueError(f"rejected sleep state leaked into active matrix: {name}")
        result[name] = item
    return result


def build_poses(layout: dict[str, object], components: dict[str, dict[str, object]]) -> list[tuple[str, str, str, list[str]]]:
    states = state_map(layout)
    sets = layout.get("state_component_sets")
    if not isinstance(sets, dict) or set(sets) != set(states):
        raise ValueError("state component sets do not match state rows")
    poses: dict[tuple[str, str, str], list[str]] = {}

    def add(scene: str, emotion: str, attention: str, state_name: str) -> None:
        names = sets.get(state_name)
        if not isinstance(names, list) or not all(isinstance(name, str) and name in components for name in names):
            raise ValueError(f"invalid component set: {state_name}")
        key = (scene, emotion, attention)
        poses.setdefault(key, list(names))

    for name, state in states.items():
        add(require_string(state["scene"], "scene"), require_string(state["emotion"], "emotion"),
            require_string(state["attention"], "attention"), name)

    daily_for_attention = {
        "left": "daily_attention_left", "right": "daily_attention_right",
        "up": "daily_attention_up", "down": "daily_attention_down",
        "center": "calm_content",
    }
    for emotion in ("calm", "curious", "affectionate"):
        for attention, state_name in daily_for_attention.items():
            add("daily", emotion, attention, state_name)
    for attention in ATTENTION_ENUM:
        add("touch", "curious", attention, "curious_question")
        add("swipe", "curious", attention, "affectionate_warm")
        add("swipe", "affectionate", attention, "affectionate_warm")
        add("swipe", "playful", attention, "playful_bright")
    for attention in ("center", "up"):
        add("menu", "thinking", attention, "menu_thinking")
        add("menu", "curious", attention, "menu_thinking")
    return [(scene, emotion, attention, names) for (scene, emotion, attention), names in poses.items()]


def render_pose(scene: str, emotion: str, attention: str, names: list[str],
                components: dict[str, dict[str, object]],
                offsets: dict[str, list[int]] | None = None) -> str:
    ordered = sorted(names, key=lambda name: int(components[name]["z_index"]))
    if not ordered or len(ordered) > 16:
        raise ValueError(f"registered pose has invalid layer count: {scene}/{emotion}/{attention}")
    overrides = offsets or {}
    layers: list[str] = []
    highlight_offset = ATTENTION_OFFSET[attention]
    for name in ordered:
        item = components[name]
        offset_x, offset_y = (0, 0)
        if item["role"] in {"left_highlight", "right_highlight"}:
            offset_x, offset_y = highlight_offset
        override = overrides.get(name)
        if override is not None:
            if len(override) != 2 or not all(isinstance(value, int) for value in override):
                raise ValueError(f"performance offset is invalid: {name}")
            offset_x, offset_y = override
        layers.append(
            "            {"
            f".component_id = {item['component_id']}u, .offset_x = {offset_x}, .offset_y = {offset_y}, "
            f".dynamic_flags = {dynamic_flags(item)}"
            "},"
        )
    return (
        "{"
        f".scene = {SCENE_ENUM[scene]}, .emotion = {EMOTION_ENUM[emotion]}, "
        f".attention = {ATTENTION_ENUM[attention]}, .layer_count = {len(ordered)}u, .layers = {{\n"
        + "\n".join(layers) + "\n        }}"
    )


def render_state_initializer(state: dict[str, object]) -> str:
    return (
        "{"
        f".scene = {SCENE_ENUM[str(state['scene'])]}, "
        f".emotion = {EMOTION_ENUM[str(state['emotion'])]}, "
        f".attention = {ATTENTION_ENUM[str(state['attention'])]}, "
        f".energy = {ENERGY_ENUM[str(state['energy'])]}, "
        f".interaction_memory = {state['interaction_memory']}u, "
        ".phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN"
        "}"
    )


def render_performance_scores(layout: dict[str, object],
                              states: dict[str, dict[str, object]],
                              components: dict[str, dict[str, object]]) -> tuple[str, str, str]:
    full_sets = layout.get("state_component_sets")
    core_sets = layout.get("state_core_component_sets")
    performances = layout.get("performances")
    if not isinstance(full_sets, dict) or not isinstance(core_sets, dict) or \
            not isinstance(performances, dict) or set(performances) != set(states):
        raise ValueError("expanded performance score vocabulary drifted")
    pose_lines: list[str] = []
    score_lines: list[str] = []
    selector_lines: list[str] = []
    pose_index = 0
    for state_name, root_state in states.items():
        performance = performances.get(state_name)
        if not isinstance(performance, dict):
            raise ValueError(f"performance is invalid: {state_name}")
        raw_steps = performance.get("steps")
        if not isinstance(raw_steps, list) or len(raw_steps) != 7:
            raise ValueError(f"performance step count is invalid: {state_name}")
        step_lines: list[str] = []
        for step in raw_steps:
            if not isinstance(step, dict):
                raise ValueError(f"performance step is invalid: {state_name}")
            phase = require_string(step.get("phase"), f"performance phase {state_name}")
            set_name = require_string(step.get("set"), f"performance component set {state_name}")
            pose_state_name = require_string(step.get("state"), f"performance pose state {state_name}")
            duration = step.get("duration_ms")
            offsets = step.get("offsets")
            if phase not in SCORE_PHASE_ENUM or set_name not in {"core", "full"} or \
                    pose_state_name not in states or not isinstance(duration, int) or duration < 80 or \
                    not isinstance(offsets, dict):
                raise ValueError(f"performance step is invalid: {state_name}/{phase}")
            source_sets = core_sets if set_name == "core" else full_sets
            names = source_sets.get(pose_state_name)
            if not isinstance(names, list) or not all(isinstance(name, str) and name in components for name in names):
                raise ValueError(f"performance pose components are invalid: {state_name}/{phase}")
            normalized_offsets: dict[str, list[int]] = {}
            for component_name, offset in offsets.items():
                if not isinstance(component_name, str) or component_name not in names or \
                        not isinstance(offset, list):
                    raise ValueError(f"performance offset is not a member of its pose: {state_name}/{phase}")
                normalized_offsets[component_name] = offset
            pose_state = states[pose_state_name]
            pose_lines.append("    " + render_pose(
                str(pose_state["scene"]), str(pose_state["emotion"]),
                str(pose_state["attention"]), list(names), components, normalized_offsets) + ",")
            step_lines.append(
                "    {"
                f".phase = {SCORE_PHASE_ENUM[phase]}, .duration_ms = {duration}u, "
                f".state = {render_state_initializer(pose_state)}, "
                f".pose = &k_v9_expanded_performance_poses[{pose_index}]"
                "},"
            )
            pose_index += 1
        score_symbol = f"k_v9_expanded_{state_name}_score"
        score_lines.append(
            f"static const comp_expression_rig_registered_score_step_t {score_symbol}_steps[] = {{\n"
            + "\n".join(step_lines) + "\n};\n\n"
            f"static const comp_expression_rig_registered_performance_score_t {score_symbol} = {{\n"
            f"    .steps = {score_symbol}_steps,\n"
            f"    .step_count = (uint8_t)(sizeof({score_symbol}_steps) / sizeof({score_symbol}_steps[0])),\n"
            "};"
        )
        selector_lines.append(
            f"    if (scene == {SCENE_ENUM[str(root_state['scene'])]} && "
            f"emotion == {EMOTION_ENUM[str(root_state['emotion'])]} && "
            f"attention == {ATTENTION_ENUM[str(root_state['attention'])]}) {{\n"
            f"        return &{score_symbol};\n"
            "    }"
        )
    if pose_index != len(states) * 7:
        raise ValueError("expanded performance pose count drifted")
    return "\n".join(pose_lines), "\n\n".join(score_lines), "\n".join(selector_lines)


def render_presence_scores(layout: dict[str, object],
                           states: dict[str, dict[str, object]],
                           components: dict[str, dict[str, object]]) -> tuple[str, str, str, int]:
    full_sets = layout.get("state_component_sets")
    tracks = layout.get("presence_tracks")
    if not isinstance(full_sets, dict) or not isinstance(tracks, dict) or set(tracks) != set(states):
        raise ValueError("expanded presence-track vocabulary drifted")
    pose_lines: list[str] = []
    score_lines: list[str] = []
    selector_lines: list[str] = []
    pose_index = 0
    sample_count: int | None = None
    for state_name, root_state in states.items():
        track = tracks.get(state_name)
        if not isinstance(track, dict) or track.get("loop_policy") != "same_selected_state_after_static_rest":
            raise ValueError(f"presence track is invalid: {state_name}")
        raw_steps = track.get("steps")
        if not isinstance(raw_steps, list) or len(raw_steps) < 8:
            raise ValueError(f"presence step count is invalid: {state_name}")
        if sample_count is None:
            sample_count = len(raw_steps)
        elif sample_count != len(raw_steps):
            raise ValueError("presence tracks must have a deterministic common sample count")
        names = full_sets.get(state_name)
        if not isinstance(names, list) or not all(isinstance(name, str) and name in components for name in names):
            raise ValueError(f"presence components are invalid: {state_name}")
        step_lines: list[str] = []
        for step in raw_steps:
            if not isinstance(step, dict):
                raise ValueError(f"presence step is invalid: {state_name}")
            cue = require_string(step.get("cue"), f"presence cue {state_name}")
            phase = require_string(step.get("phase"), f"presence phase {state_name}")
            duration = step.get("duration_ms")
            offsets = step.get("offsets")
            if not cue or phase not in SCORE_PHASE_ENUM or step.get("set") != "full" or \
                    step.get("state") != state_name or not isinstance(duration, int) or duration < 80 or \
                    not isinstance(offsets, dict):
                raise ValueError(f"presence step is invalid: {state_name}/{cue}")
            normalized_offsets: dict[str, list[int]] = {}
            for component_name, offset in offsets.items():
                if not isinstance(component_name, str) or component_name not in names or not isinstance(offset, list):
                    raise ValueError(f"presence offset is not a member of its pose: {state_name}/{cue}")
                pair(offset, f"presence offset {state_name}/{component_name}")
                normalized_offsets[component_name] = offset
            pose_lines.append("    " + render_pose(
                str(root_state["scene"]), str(root_state["emotion"]), str(root_state["attention"]),
                list(names), components, normalized_offsets) + ",")
            step_lines.append(
                "    {"
                f".phase = {SCORE_PHASE_ENUM[phase]}, .duration_ms = {duration}u, "
                f".state = {render_state_initializer(root_state)}, "
                f".pose = &k_v9_expanded_presence_poses[{pose_index}]"
                "},"
            )
            pose_index += 1
        score_symbol = f"k_v9_expanded_{state_name}_presence_score"
        score_lines.append(
            f"static const comp_expression_rig_registered_score_step_t {score_symbol}_steps[] = {{\n"
            + "\n".join(step_lines) + "\n};\n\n"
            f"static const comp_expression_rig_registered_performance_score_t {score_symbol} = {{\n"
            f"    .steps = {score_symbol}_steps,\n"
            f"    .step_count = (uint8_t)(sizeof({score_symbol}_steps) / sizeof({score_symbol}_steps[0])),\n"
            "};"
        )
        selector_lines.append(
            f"    if (scene == {SCENE_ENUM[str(root_state['scene'])]} && "
            f"emotion == {EMOTION_ENUM[str(root_state['emotion'])]} && "
            f"attention == {ATTENTION_ENUM[str(root_state['attention'])]}) {{\n"
            f"        return &{score_symbol};\n"
            "    }"
        )
    if sample_count is None or pose_index != len(states) * sample_count:
        raise ValueError("expanded presence pose count drifted")
    return "\n".join(pose_lines), "\n\n".join(score_lines), "\n".join(selector_lines), sample_count


def render_emotion_bridge_scores(layout: dict[str, object],
                                 states: dict[str, dict[str, object]],
                                 components: dict[str, dict[str, object]]) -> tuple[str, str, str, int, int]:
    bridges = layout.get("emotion_bridge_tracks")
    emotion_system = layout.get("emotion_system")
    if not isinstance(bridges, dict) or not isinstance(emotion_system, dict):
        raise ValueError("expanded layout lacks emotion bridge vocabulary")
    baseline_states = emotion_system.get("baseline_states")
    directed_edges = emotion_system.get("directed_edges")
    if not isinstance(baseline_states, dict) or not isinstance(directed_edges, list):
        raise ValueError("emotion system metadata is invalid")
    expected_names: set[str] = set()
    for edge in directed_edges:
        if not isinstance(edge, list) or len(edge) != 2 or \
                not all(isinstance(value, str) and value in EMOTION_ENUM for value in edge):
            raise ValueError("emotion graph edge is invalid")
        expected_names.add(f"{edge[0]}_to_{edge[1]}")
    if set(bridges) != expected_names:
        raise ValueError("emotion bridge tracks do not match the directed affect graph")
    pose_lines: list[str] = []
    score_lines: list[str] = []
    selector_lines: list[str] = []
    pose_index = 0
    sample_count: int | None = None
    for bridge_name, bridge in bridges.items():
        if not isinstance(bridge, dict):
            raise ValueError(f"emotion bridge is invalid: {bridge_name}")
        from_emotion = require_string(bridge.get("from_emotion"), f"emotion bridge source {bridge_name}")
        to_emotion = require_string(bridge.get("to_emotion"), f"emotion bridge target {bridge_name}")
        source_state = require_string(bridge.get("source_state"), f"emotion bridge source state {bridge_name}")
        target_state = require_string(bridge.get("target_state"), f"emotion bridge target state {bridge_name}")
        raw_steps = bridge.get("steps")
        if from_emotion not in EMOTION_ENUM or to_emotion not in EMOTION_ENUM or \
                source_state not in states or target_state not in states or \
                baseline_states.get(from_emotion) != source_state or \
                baseline_states.get(to_emotion) != target_state or \
                not isinstance(raw_steps, list) or len(raw_steps) != 7:
            raise ValueError(f"emotion bridge is invalid: {bridge_name}")
        if sample_count is None:
            sample_count = len(raw_steps)
        elif sample_count != len(raw_steps):
            raise ValueError("emotion bridges must have a deterministic common sample count")
        step_lines: list[str] = []
        for step in raw_steps:
            if not isinstance(step, dict):
                raise ValueError(f"emotion bridge step is invalid: {bridge_name}")
            cue = require_string(step.get("cue"), f"emotion bridge cue {bridge_name}")
            phase = require_string(step.get("phase"), f"emotion bridge phase {bridge_name}")
            state_name = require_string(step.get("state"), f"emotion bridge state {bridge_name}")
            names = step.get("components")
            duration = step.get("duration_ms")
            offsets = step.get("offsets")
            if not cue or phase not in SCORE_PHASE_ENUM or step.get("set") != "bridge" or \
                    state_name not in states or not isinstance(names, list) or \
                    not all(isinstance(name, str) and name in components for name in names) or \
                    not isinstance(duration, int) or duration < 80 or not isinstance(offsets, dict):
                raise ValueError(f"emotion bridge step is invalid: {bridge_name}/{cue}")
            normalized_offsets: dict[str, list[int]] = {}
            for component_name, offset in offsets.items():
                if not isinstance(component_name, str) or component_name not in names or not isinstance(offset, list):
                    raise ValueError(f"emotion bridge offset is not a member of its pose: {bridge_name}/{cue}")
                pair(offset, f"emotion bridge offset {bridge_name}/{component_name}")
                normalized_offsets[component_name] = offset
            state = states[state_name]
            pose_lines.append("    " + render_pose(
                str(state["scene"]), str(state["emotion"]), str(state["attention"]),
                list(names), components, normalized_offsets) + ",")
            step_lines.append(
                "    {"
                f".phase = {SCORE_PHASE_ENUM[phase]}, .duration_ms = {duration}u, "
                f".state = {render_state_initializer(state)}, "
                f".pose = &k_v9_expanded_emotion_bridge_poses[{pose_index}]"
                "},"
            )
            pose_index += 1
        score_symbol = f"k_v9_expanded_{bridge_name}_bridge_score"
        score_lines.append(
            f"static const comp_expression_rig_registered_score_step_t {score_symbol}_steps[] = {{\n"
            + "\n".join(step_lines) + "\n};\n\n"
            f"static const comp_expression_rig_registered_performance_score_t {score_symbol} = {{\n"
            f"    .steps = {score_symbol}_steps,\n"
            f"    .step_count = (uint8_t)(sizeof({score_symbol}_steps) / sizeof({score_symbol}_steps[0])),\n"
            "};"
        )
        selector_lines.append(
            f"    if (from == {EMOTION_ENUM[from_emotion]} && to == {EMOTION_ENUM[to_emotion]}) {{\n"
            f"        return &{score_symbol};\n"
            "    }"
        )
    if sample_count is None or pose_index != len(bridges) * sample_count:
        raise ValueError("emotion bridge pose count drifted")
    return "\n".join(pose_lines), "\n\n".join(score_lines), "\n".join(selector_lines), len(bridges), sample_count


def render_header(layout: dict[str, object], component_count: int, pose_count: int,
                  performance_count: int, presence_sample_count: int,
                  bridge_count: int, bridge_sample_count: int) -> str:
    source = source_sha(layout)
    return f"""/* Generated from the approved expanded V9 source-mask Rig; do not hand edit. */
#ifndef COMPANION_EPAPER_GENERATED_EXPRESSION_RIG_V9_EXPANDED_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_GENERATED_EXPRESSION_RIG_V9_EXPANDED_CANDIDATE_PROFILE_H

#include \"expression_rig_performance_score.h\"

#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT {component_count}u
#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_POSE_COUNT {pose_count}u
#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_PERFORMANCE_COUNT {performance_count}u
#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_PRESENCE_SAMPLE_COUNT {presence_sample_count}u
#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_EMOTION_BRIDGE_COUNT {bridge_count}u
#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_EMOTION_BRIDGE_SAMPLE_COUNT {bridge_sample_count}u
#define COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_SOURCE_SHA256 \"{source}\"

const comp_expression_rig_profile_t *comp_v9_expanded_expression_rig_candidate_profile(void);
const comp_expression_rig_registered_performance_score_t *
comp_v9_expanded_expression_rig_candidate_performance_score(
    comp_expression_rig_scene_t scene,
    comp_expression_rig_emotion_t emotion,
    comp_expression_rig_attention_t attention);
const comp_expression_rig_registered_performance_score_t *
comp_v9_expanded_expression_rig_candidate_presence_score(
    comp_expression_rig_scene_t scene,
    comp_expression_rig_emotion_t emotion,
    comp_expression_rig_attention_t attention);
const comp_expression_rig_registered_performance_score_t *
comp_v9_expanded_expression_rig_candidate_emotion_bridge_score(
    comp_expression_rig_emotion_t from,
    comp_expression_rig_emotion_t to);
bool comp_v9_expanded_expression_rig_candidate_runtime_activation_allowed(void);

#endif /* COMPANION_EPAPER_GENERATED_EXPRESSION_RIG_V9_EXPANDED_CANDIDATE_PROFILE_H */
"""


def render_source(layout: dict[str, object]) -> str:
    components, by_name = load_components(layout)
    poses = build_poses(layout, by_name)
    states = state_map(layout)
    component_lines: list[str] = []
    for item in components:
        name = str(item["name"])
        base_x, base_y = pair(item["base_position"], f"component {name} position")
        min_x, min_y = pair(item["offset_range"]["min"], f"component {name} min")  # type: ignore[index]
        max_x, max_y = pair(item["offset_range"]["max"], f"component {name} max")  # type: ignore[index]
        component_lines.append(
            "    {"
            f".component_id = {item['component_id']}u, .role = {ROLE_ENUM[str(item['role'])]}, "
            ".variant = COMP_EXPRESSION_RIG_VARIANT_DEFAULT, "
            f".base_x = {base_x}, .base_y = {base_y}, .min_offset_x = {min_x}, .min_offset_y = {min_y}, "
            f".max_offset_x = {max_x}, .max_offset_y = {max_y}, .z_index = {item['z_index']}u, "
            f".composite_op = {COMPOSITE_ENUM[str(item['composite_op'])]}"
            "},"
        )
    pose_lines: list[str] = []
    for scene, emotion, attention, names in poses:
        pose_lines.append("    " + render_pose(scene, emotion, attention, names, by_name) + ",")
    performance_pose_lines, performance_score_lines, performance_selector_lines = \
        render_performance_scores(layout, states, by_name)
    presence_pose_lines, presence_score_lines, presence_selector_lines, _ = \
        render_presence_scores(layout, states, by_name)
    bridge_pose_lines, bridge_score_lines, bridge_selector_lines, _, _ = \
        render_emotion_bridge_scores(layout, states, by_name)
    return """/* Generated from the approved expanded V9 source-mask Rig; do not hand edit. */
#include "expression_rig_v9_expanded_candidate_profile.h"

static const comp_expression_rig_component_info_t k_v9_expanded_components[] = {
%s
};

static const comp_expression_rig_registered_pose_t k_v9_expanded_poses[] = {
%s
};

static const comp_expression_rig_registered_pose_t k_v9_expanded_performance_poses[] = {
%s
};

%s

static const comp_expression_rig_registered_pose_t k_v9_expanded_presence_poses[] = {
%s
};

%s

static const comp_expression_rig_registered_pose_t k_v9_expanded_emotion_bridge_poses[] = {
%s
};

%s

static const comp_expression_rig_profile_t k_v9_expanded_profile = {
    .components = k_v9_expanded_components,
    .component_count = COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT,
    .scene_charm_component = {
        [COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
        [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,
    },
    .registered_poses = k_v9_expanded_poses,
    .registered_pose_count = COMP_V9_EXPANDED_EXPRESSION_RIG_CANDIDATE_POSE_COUNT,
};

const comp_expression_rig_profile_t *comp_v9_expanded_expression_rig_candidate_profile(void)
{
    return &k_v9_expanded_profile;
}

const comp_expression_rig_registered_performance_score_t *
comp_v9_expanded_expression_rig_candidate_performance_score(
    comp_expression_rig_scene_t scene,
    comp_expression_rig_emotion_t emotion,
    comp_expression_rig_attention_t attention)
{
%s
    return NULL;
}

const comp_expression_rig_registered_performance_score_t *
comp_v9_expanded_expression_rig_candidate_presence_score(
    comp_expression_rig_scene_t scene,
    comp_expression_rig_emotion_t emotion,
    comp_expression_rig_attention_t attention)
{
%s
    return NULL;
}

const comp_expression_rig_registered_performance_score_t *
comp_v9_expanded_expression_rig_candidate_emotion_bridge_score(
    comp_expression_rig_emotion_t from,
    comp_expression_rig_emotion_t to)
{
%s
    return NULL;
}

bool comp_v9_expanded_expression_rig_candidate_runtime_activation_allowed(void)
{
    return false;
}
""" % ("\n".join(component_lines), "\n".join(pose_lines),
       performance_pose_lines, performance_score_lines,
       presence_pose_lines, presence_score_lines,
       bridge_pose_lines, bridge_score_lines,
       performance_selector_lines, presence_selector_lines, bridge_selector_lines)


def write_or_check(path: Path, content: str, check: bool) -> bool:
    if check:
        return path.is_file() and path.read_text(encoding="ascii") == content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="ascii", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        layout = json.loads(args.layout.resolve().read_text(encoding="utf-8"))
        components, by_name = load_components(layout)
        poses = build_poses(layout, by_name)
        states = state_map(layout)
        _, _, _, presence_sample_count = render_presence_scores(layout, states, by_name)
        _, _, _, bridge_count, bridge_sample_count = render_emotion_bridge_scores(layout, states, by_name)
        header = render_header(layout, len(components), len(poses), len(state_map(layout)),
                               presence_sample_count, bridge_count, bridge_sample_count)
        source = render_source(layout)
        header_ok = write_or_check(args.header.resolve(), header, args.check)
        source_ok = write_or_check(args.source.resolve(), source, args.check)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if not header_ok or not source_ok:
        print("FAIL: generated expanded V9 Rig profile drifted")
        return 1
    print("PASS: expanded V9 Rig profile is generated deterministically from the registered source-mask layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
