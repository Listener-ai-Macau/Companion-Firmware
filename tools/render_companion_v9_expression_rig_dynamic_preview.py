#!/usr/bin/env python3
"""Build a component-layer dynamic preview for the locked v9 expression Rig."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
from dataclasses import dataclass, replace

from PIL import Image, ImageDraw


ROOT = pathlib.Path(__file__).resolve().parents[1]
RENDER_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200"
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
STATE_PREVIEW_SCORE = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/state-preview-rig-score-v1.json"
EXPRESSION_ATLAS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/expression-atlas-v1.json"
RENDER_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
CEMP_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-cemp-20260717.json"
CHOREOGRAPHER_REPORT = ROOT / "docs/validation/companion-v9-expression-choreographer-20260717.json"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-dynamic-preview-20260717.json"
LAYER_DIR = RENDER_DIR / "dynamic-review-layers"
DYNAMIC_PAGE = RENDER_DIR / "v9-expression-rig-dynamic-player.html"
OWNER_REVIEW_PAGE = RENDER_DIR / "v9-expression-rig-owner-review.html"
ANIMATED_GIF = RENDER_DIR / "v9-expression-rig-dynamic-preview.gif"
KEYFRAME_STRIP = RENDER_DIR / "v9-expression-rig-dynamic-keyframes.png"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"

PHASES = ("entry", "sustain", "settle")
STORY_ORDER = (
    "daily_left",
    "daily_right",
    "daily_up",
    "daily_down",
    "touch_left",
    "touch_right",
    "swipe_left",
    "swipe_right",
    "swipe_down",
    "recording_focus",
    "menu_focus",
    "sleep_enter",
)
DAILY_STORY_ORDER = tuple(story for story in STORY_ORDER if story.startswith("daily_"))
REGISTERED_STATE_STORY_ORDER = (
    "touch_left",
    "touch_right",
    "swipe_left",
    "swipe_right",
    "swipe_down",
    "recording_focus",
    "menu_focus",
    "sleep_enter",
)
ROLE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("eyes/highlights", ("left_eye", "right_eye", "left_highlight", "right_highlight", "left_sparkle", "right_sparkle")),
    ("brows", ("left_brow", "right_brow")),
    ("nose-mouth/lips", ("nose", "mouth")),
    ("cheeks", ("left_cheek", "right_cheek")),
    ("side detail strokes", ("left_detail", "right_detail")),
    ("small charm", ("charm",)),
)
REQUIRED_DYNAMIC_GROUPS = {
    "eyes/highlights",
    "brows",
    "nose-mouth/lips",
    "cheeks",
    "side detail strokes",
    "small charm",
}
SCORE_PHASES = (
    "entry", "prepare", "lead", "response", "accent", "hold", "release", "return", "settle",
)


@dataclass(frozen=True)
class ComponentLayer:
    component: str
    role: str
    source_frame: str
    x: int
    y: int
    offset: tuple[int, int]
    z_index: int
    composite_op: str
    png: pathlib.Path


@dataclass(frozen=True)
class PreviewFrame:
    story: str
    label: str
    duration_ms: int
    layers: tuple[ComponentLayer, ...]
    activated_groups: tuple[str, ...]
    semantic_phase: str
    state_roles: tuple[str, ...] = ()
    state_components: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoreStep:
    semantic_phase: str
    label: str
    duration_ms: int
    poses: tuple[tuple[str, tuple[int, int]], ...]
    return_to_entry: bool
    state_roles: tuple[str, ...] = ()
    match_sustain: bool = False
    state_components: tuple[str, ...] = ()


@dataclass(frozen=True)
class PerformanceScore:
    beats: tuple[str, ...]
    steps: tuple[ScoreStep, ...]


@dataclass(frozen=True)
class PreviewArtifacts:
    layer_dir: pathlib.Path
    dynamic_page: pathlib.Path
    owner_review_page: pathlib.Path
    animated_gif: pathlib.Path
    keyframe_strip: pathlib.Path


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifacts_for_scope(scope: str, artifact_root: pathlib.Path) -> PreviewArtifacts:
    if scope == "full_library":
        return PreviewArtifacts(
            artifact_root / "dynamic-review-layers",
            artifact_root / "v9-expression-rig-dynamic-player.html",
            artifact_root / "v9-expression-rig-owner-review.html",
            artifact_root / "v9-expression-rig-dynamic-preview.gif",
            artifact_root / "v9-expression-rig-dynamic-keyframes.png",
        )
    if scope == "daily_focus":
        return PreviewArtifacts(
            artifact_root / "daily-focus-layers",
            artifact_root / "v9-expression-rig-daily-focus-player.html",
            artifact_root / "v9-expression-rig-daily-focus-owner-review.html",
            artifact_root / "v9-expression-rig-daily-focus-preview.gif",
            artifact_root / "v9-expression-rig-daily-focus-keyframes.png",
        )
    if scope == "daily_selected_state":
        return PreviewArtifacts(
            artifact_root / "daily-selected-state-layers",
            artifact_root / "v9-expression-rig-daily-selected-state-player.html",
            artifact_root / "v9-expression-rig-daily-selected-state-owner-review.html",
            artifact_root / "v9-expression-rig-daily-selected-state-preview.gif",
            artifact_root / "v9-expression-rig-daily-selected-state-keyframes.png",
        )
    if scope == "registered_states":
        return PreviewArtifacts(
            artifact_root / "registered-state-preview-layers",
            artifact_root / "v9-expression-rig-registered-states-player.html",
            artifact_root / "v9-expression-rig-registered-states-owner-review.html",
            artifact_root / "v9-expression-rig-registered-states-preview.gif",
            artifact_root / "v9-expression-rig-registered-states-keyframes.png",
        )
    if scope == "expression_atlas":
        return PreviewArtifacts(
            artifact_root / "expression-atlas-layers",
            artifact_root / "v9-expression-rig-expression-atlas-player.html",
            artifact_root / "v9-expression-rig-expression-atlas-owner-review.html",
            artifact_root / "v9-expression-rig-expression-atlas-preview.gif",
            artifact_root / "v9-expression-rig-expression-atlas-keyframes.png",
        )
    raise ValueError(f"unsupported preview scope: {scope}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def export_component_pngs(render_report: dict[str, object], layer_dir: pathlib.Path) -> dict[str, pathlib.Path]:
    components = render_report.get("components")
    require(isinstance(components, list) and components, "render report has no components")
    layer_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, pathlib.Path] = {}
    for item in components:
        require(isinstance(item, dict), "component record must be an object")
        name = str(item.get("name"))
        mask_path = ROOT / str(item.get("component_mask", ""))
        require(mask_path.is_file(), f"missing component mask: {name}")
        mask = Image.open(mask_path).convert("1")
        alpha = mask.convert("L").point(lambda value: 255 if value == 0 else 0)
        require(alpha.getbbox() is not None, f"empty component mask: {name}")
        color = (255, 255, 255, 255) if item.get("composite_op") == "erase" else (0, 0, 0, 255)
        layer = Image.new("RGBA", mask.size, (0, 0, 0, 0))
        layer.paste(Image.new("RGBA", mask.size, color), (0, 0), alpha)
        output = layer_dir / f"{name}.png"
        layer.save(output)
        result[name] = output
    return result


def component_index(render_report: dict[str, object]) -> dict[str, dict[str, object]]:
    components = render_report.get("components")
    require(isinstance(components, list), "components must be a list")
    result: dict[str, dict[str, object]] = {}
    for item in components:
        require(isinstance(item, dict), "component must be an object")
        name = str(item.get("name"))
        result[name] = item
    return result


def phase_name(frame: dict[str, object]) -> str:
    name = str(frame.get("name"))
    for phase in PHASES:
        if name.endswith(f"_{phase}"):
            return phase
    raise ValueError(f"frame has no phase suffix: {name}")


def story_frames(render_report: dict[str, object]) -> dict[str, dict[str, dict[str, object]]]:
    frames = render_report.get("frames")
    require(isinstance(frames, list) and frames, "render report has no frames")
    result: dict[str, dict[str, dict[str, object]]] = {}
    for frame in frames:
        if not isinstance(frame, dict) or frame.get("kind") != "story":
            continue
        story = str(frame.get("story"))
        result.setdefault(story, {})[phase_name(frame)] = frame
    for story, phases in result.items():
        missing = [phase for phase in PHASES if phase not in phases]
        require(not missing, f"story {story} is missing phases: {', '.join(missing)}")
    return result


def layer_from_record(record: dict[str, object],
                      components: dict[str, dict[str, object]],
                      pngs: dict[str, pathlib.Path]) -> ComponentLayer:
    name = str(record.get("component"))
    component = components[name]
    base = record.get("base_position")
    offset = record.get("offset")
    require(isinstance(base, list) and len(base) == 2, f"bad base position: {name}")
    require(isinstance(offset, list) and len(offset) == 2, f"bad offset: {name}")
    return ComponentLayer(
        component=name,
        role=str(record.get("role")),
        source_frame=str(record.get("source_frame")),
        x=int(base[0]) + int(offset[0]),
        y=int(base[1]) + int(offset[1]),
        offset=(int(offset[0]), int(offset[1])),
        z_index=int(component.get("z_index", 0)),
        composite_op=str(record.get("composite_op", component.get("composite_op", "ink"))),
        png=pngs[name],
    )


def layers_by_role(frame: dict[str, object],
                   components: dict[str, dict[str, object]],
                   pngs: dict[str, pathlib.Path]) -> dict[str, tuple[ComponentLayer, ...]]:
    raw_layers = frame.get("layers")
    require(isinstance(raw_layers, list) and raw_layers, f"frame has no layers: {frame.get('name')}")
    by_role: dict[str, list[ComponentLayer]] = {}
    for item in raw_layers:
        require(isinstance(item, dict), "layer record must be an object")
        layer = layer_from_record(item, components, pngs)
        by_role.setdefault(layer.role, []).append(layer)
    return {
        role: tuple(sorted(layers, key=lambda layer: (layer.z_index, layer.component)))
        for role, layers in by_role.items()
    }


def role_signature(layers: dict[str, tuple[ComponentLayer, ...]], roles: tuple[str, ...]) -> tuple[object, ...]:
    signature: list[object] = []
    for role in roles:
        signature.append(tuple((layer.component, layer.x, layer.y, layer.offset) for layer in layers.get(role, ())))
    return tuple(signature)


def role_set(groups: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    selected = set(groups)
    for label, roles in ROLE_GROUPS:
        if label in selected:
            result.update(roles)
    return result


DAILY_REFLECTION_TARGETS = {
    "daily_left": (-1, 2),
    "daily_right": (1, 2),
    "daily_up": (0, 1),
    "daily_down": (0, 2),
}
DAILY_REFLECTION_REST = (0, 2)
DAILY_REFLECTION_CORRIDORS = {
    "daily_left": {(0, 0), (0, 1), DAILY_REFLECTION_REST, (-1, 2)},
    "daily_right": {(0, 0), (0, 1), DAILY_REFLECTION_REST, (1, 2)},
    "daily_up": {(0, 0), (0, 1), DAILY_REFLECTION_REST},
    "daily_down": {(0, 0), (0, 1), DAILY_REFLECTION_REST},
}


def validate_daily_reflection_score(story: str,
                                    steps: tuple[ScoreStep, ...]) -> None:
    target = DAILY_REFLECTION_TARGETS.get(story)
    require(target is not None, f"unsupported Daily reflection score {story}")
    corridor = DAILY_REFLECTION_CORRIDORS[story]
    reflection_pairs = (
        ("left_eye_highlight_open", "left_eye_sparkle_open"),
        ("right_eye_highlight_open", "right_eye_sparkle_open"),
    )
    reflections = tuple(component for pair in reflection_pairs for component in pair)
    offsets = {component: (0, 0) for component in reflections}
    reached_shared_rest = False
    reached_target = False
    for step in steps:
        if step.return_to_entry:
            next_offsets = {component: (0, 0) for component in reflections}
        else:
            next_offsets = dict(offsets)
            for component, offset in step.poses:
                if component in next_offsets:
                    next_offsets[component] = offset
        for primary, sparkle in reflection_pairs:
            require(next_offsets[primary] == next_offsets[sparkle],
                    f"{story} paired eye reflection must keep its primary highlight and sparkle together")
            offset_x, offset_y = next_offsets[primary]
            previous_x, previous_y = offsets[primary]
            require((offset_x, offset_y) in corridor,
                    f"{story} reflection leaves its calibrated V9 dynamic-rest corridor")
            require(abs(offset_x - previous_x) <= 1 and abs(offset_y - previous_y) <= 1,
                    f"{story} primary highlight jumps more than one pixel per score step")
        reached_shared_rest = reached_shared_rest or all(
            next_offsets[primary] == DAILY_REFLECTION_REST for primary, _ in reflection_pairs
        )
        if reached_shared_rest:
            reached_target = reached_target or all(
                next_offsets[primary] == target for primary, _ in reflection_pairs
            )
        offsets = next_offsets
    require(reached_shared_rest,
            f"{story} paired eye reflections must arrive at the V9 dynamic rest anchor")
    require(reached_target,
            f"{story} paired eye reflection must lead from dynamic rest to its calibrated target")


def load_daily_choreography() -> dict[str, PerformanceScore]:
    layout = load_json(LAYOUT)
    choreography = layout.get("preview_choreography")
    require(isinstance(choreography, dict) and
            choreography.get("schema") == "companion.v9_expression_rig_performance_score.v2" and
            choreography.get("scope") == "daily_first",
            "layout is missing the versioned Daily component performance score")
    vocabulary = choreography.get("phase_vocabulary")
    require(isinstance(vocabulary, list) and tuple(str(item) for item in vocabulary) == SCORE_PHASES,
            "Daily score must declare the complete reusable phase vocabulary")
    duration_bounds = choreography.get("step_duration_ms")
    require(isinstance(duration_bounds, dict), "Daily score has no duration bounds")
    duration_min = duration_bounds.get("min")
    duration_max = duration_bounds.get("max")
    require(isinstance(duration_min, int) and isinstance(duration_max, int) and
            80 <= duration_min <= duration_max <= 5000,
            "Daily score duration bounds are invalid")
    presentation = choreography.get("panel_presentation")
    require(isinstance(presentation, dict) and
            presentation.get("schema") == "companion.v9_expression_rig_panel_presentation.v1" and
            presentation.get("scope") == "dedicated_daily_rig_demo_only",
            "Daily score has no versioned panel presentation contract")
    initial_dwell = presentation.get("initial_baseline_min_dwell_ms")
    minimum_dwell = presentation.get("minimum_step_dwell_ms")
    partial_limit = presentation.get("partial_limit")
    replay_mode = presentation.get("replay_mode")
    panel_story_order = presentation.get("story_order")
    require(isinstance(initial_dwell, int) and isinstance(minimum_dwell, int) and
            isinstance(partial_limit, int) and 750 <= initial_dwell <= duration_max and
            650 <= minimum_dwell <= initial_dwell and
            (14 <= partial_limit <= 64 or partial_limit == 255) and
            replay_mode == "continuous_story_cycle" and
            isinstance(panel_story_order, list) and tuple(panel_story_order) == DAILY_STORY_ORDER,
            "Daily panel presentation contract is invalid")

    layout_components = layout.get("components")
    require(isinstance(layout_components, list), "layout has no component registry")
    legal_offsets: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}
    for component in layout_components:
        require(isinstance(component, dict), "layout component must be an object")
        name = str(component.get("name", ""))
        offset_range = component.get("offset_range")
        require(name and isinstance(offset_range, dict), "layout component has no legal offset range")
        low = offset_range.get("min")
        high = offset_range.get("max")
        require(isinstance(low, list) and isinstance(high, list) and len(low) == 2 and len(high) == 2 and
                all(isinstance(value, int) for value in low + high),
                f"layout component {name} has invalid legal offset range")
        legal_offsets[name] = ((int(low[0]), int(low[1])), (int(high[0]), int(high[1])))

    performance_raw = choreography.get("performances")
    require(isinstance(performance_raw, list), "Daily score has no performances")
    performances: dict[str, PerformanceScore] = {}
    valid_groups = {name for name, _ in ROLE_GROUPS}
    for item in performance_raw:
        require(isinstance(item, dict), "Daily performance must be an object")
        name = str(item.get("name", ""))
        beats = item.get("beats")
        score_raw = item.get("score")
        require(name in DAILY_STORY_ORDER and isinstance(beats, list) and beats and
                isinstance(score_raw, list) and score_raw,
                "Daily performance must name a story, beats and component score")
        beat_order = tuple(str(beat) for beat in beats)
        require(len(beat_order) == len(set(beat_order)) and set(beat_order).issubset(valid_groups),
                f"Daily score beats are invalid for {name}")
        steps: list[ScoreStep] = []
        for step_index, raw_step in enumerate(score_raw):
            require(isinstance(raw_step, dict), f"Daily score step is invalid for {name}")
            semantic_phase = str(raw_step.get("phase", ""))
            label = str(raw_step.get("label", ""))
            duration_ms = raw_step.get("duration_ms")
            raw_poses = raw_step.get("poses")
            return_to_entry = raw_step.get("return_to_entry", False)
            require(semantic_phase in SCORE_PHASES and label and
                    isinstance(duration_ms, int) and duration_min <= duration_ms <= duration_max and
                    isinstance(raw_poses, dict) and isinstance(return_to_entry, bool),
                    f"Daily score step is malformed for {name}")
            poses: list[tuple[str, tuple[int, int]]] = []
            for component_name, raw_offset in raw_poses.items():
                require(isinstance(component_name, str) and component_name in legal_offsets and
                        isinstance(raw_offset, list) and len(raw_offset) == 2 and
                        all(isinstance(value, int) for value in raw_offset),
                        f"Daily score {name} references an unregistered component pose")
                low, high = legal_offsets[component_name]
                offset = (int(raw_offset[0]), int(raw_offset[1]))
                require(low[0] <= offset[0] <= high[0] and low[1] <= offset[1] <= high[1],
                        f"Daily score {name} places {component_name} outside its legal range")
                poses.append((component_name, offset))
            require(len({component for component, _ in poses}) == len(poses),
                    f"Daily score {name} duplicates a component pose")
            presentation_duration = max(duration_ms,
                                        initial_dwell if step_index == 0 else minimum_dwell)
            steps.append(ScoreStep(semantic_phase, label, presentation_duration,
                                   tuple(poses), return_to_entry))
        phases = tuple(step.semantic_phase for step in steps)
        require(phases[0] == "entry" and phases[-1] == "settle" and steps[-1].return_to_entry and
                all(phase in phases for phase in SCORE_PHASES) and len(steps) >= 14,
                f"Daily score {name} is missing reusable performance phases")
        require(sum(step.semantic_phase == "hold" for step in steps) == 1 and
                sum(step.semantic_phase == "settle" for step in steps) == 1,
                f"Daily score {name} must have one hold and one calm return")
        score = PerformanceScore(beat_order, tuple(steps))
        validate_daily_reflection_score(name, score.steps)
        performances[name] = score
    require(set(performances) == set(DAILY_STORY_ORDER),
            "Daily score must cover each daily gaze story exactly once")
    return performances


def load_registered_state_choreography() -> tuple[dict[str, PerformanceScore], dict[str, dict[str, object]], dict[str, object]]:
    contract = load_json(STATE_PREVIEW_SCORE)
    layout = load_json(LAYOUT)
    require(contract.get("schema") == "companion.v9_expression_rig_registered_state_preview_score.v1" and
            contract.get("scope") == "registered_states_after_daily" and
            contract.get("runtime_resource_activated") is False and
            contract.get("source_sha256") == LOCKED_SOURCE_HASH and
            contract.get("source_layout") == rel(LAYOUT) and
            contract.get("source_layout_revision") == layout.get("revision"),
            "registered-state preview score is not bound to the locked v9 Rig layout")
    driver_fields = contract.get("driver_fields")
    require(isinstance(driver_fields, list) and tuple(str(field) for field in driver_fields) ==
            ("event", "emotion", "attention", "energy", "interaction_memory"),
            "registered-state preview score has an incomplete driver contract")
    vocabulary = contract.get("phase_vocabulary")
    require(isinstance(vocabulary, list) and tuple(str(item) for item in vocabulary) == SCORE_PHASES,
            "registered-state preview score has an invalid phase vocabulary")
    presentation = contract.get("presentation")
    require(isinstance(presentation, dict) and
            presentation.get("mode") == "state_bound_single_story_loop" and
            presentation.get("automatic_story_rotation") is False,
            "registered-state preview must not automatically rotate state stories")
    fail_closed = contract.get("fail_closed_events")
    fail_closed_records = fail_closed if isinstance(fail_closed, list) else []
    fail_closed_events = {
        str(item.get("event")): str(item.get("status")) for item in fail_closed_records
        if isinstance(item, dict)
    }
    require(fail_closed_events == {
        "charging": "fail_closed_no_registered_components",
        "error": "fail_closed_no_registered_components",
    }, "registered-state preview must fail closed for charging and error")
    duration_bounds = contract.get("step_duration_ms")
    require(isinstance(duration_bounds, dict), "registered-state preview score has no duration bounds")
    duration_min = duration_bounds.get("min")
    duration_max = duration_bounds.get("max")
    require(isinstance(duration_min, int) and isinstance(duration_max, int) and
            80 <= duration_min <= duration_max <= 5000,
            "registered-state preview score duration bounds are invalid")

    components = layout.get("components")
    states = layout.get("stories")
    require(isinstance(components, list) and isinstance(states, list),
            "Rig layout has no component/story registry")
    legal_offsets: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}
    valid_roles: set[str] = set()
    for component in components:
        require(isinstance(component, dict), "layout component must be an object")
        name = str(component.get("name", ""))
        role = str(component.get("role", ""))
        offset_range = component.get("offset_range")
        require(name and role and isinstance(offset_range, dict),
                "layout component has no legal role/offset range")
        low = offset_range.get("min")
        high = offset_range.get("max")
        require(isinstance(low, list) and isinstance(high, list) and len(low) == 2 and len(high) == 2 and
                all(isinstance(value, int) for value in low + high),
                f"layout component {name} has invalid legal offset range")
        legal_offsets[name] = ((int(low[0]), int(low[1])), (int(high[0]), int(high[1])))
        valid_roles.add(role)
    state_by_name = {
        str(state.get("name")): state for state in states
        if isinstance(state, dict) and isinstance(state.get("name"), str)
    }
    performances_raw = contract.get("performances")
    require(isinstance(performances_raw, list), "registered-state preview score has no performances")
    performances: dict[str, PerformanceScore] = {}
    drivers: dict[str, dict[str, object]] = {}
    valid_groups = {name for name, _ in ROLE_GROUPS}
    for item in performances_raw:
        require(isinstance(item, dict), "registered-state performance must be an object")
        name = str(item.get("name", ""))
        beats = item.get("beats")
        driver = item.get("driver")
        score_raw = item.get("score")
        expected_state = state_by_name.get(name)
        require(name in REGISTERED_STATE_STORY_ORDER and isinstance(beats, list) and beats and
                isinstance(driver, dict) and isinstance(score_raw, list) and score_raw and
                isinstance(expected_state, dict),
            "registered-state performance must bind an existing Rig story to a score")
        require(all(driver.get(field) == expected_state.get(field) for field in
                    ("emotion", "attention", "energy", "interaction_memory")) and
                isinstance(driver.get("event"), str) and bool(driver.get("event")),
                f"registered-state driver drifted from Rig state: {name}")
        beat_order = tuple(str(beat) for beat in beats)
        require(len(beat_order) == len(set(beat_order)) and set(beat_order).issubset(valid_groups),
                f"registered-state score beats are invalid for {name}")
        steps: list[ScoreStep] = []
        for raw_step in score_raw:
            require(isinstance(raw_step, dict), f"registered-state score step is invalid for {name}")
            semantic_phase = str(raw_step.get("phase", ""))
            label = str(raw_step.get("label", ""))
            duration_ms = raw_step.get("duration_ms")
            raw_poses = raw_step.get("poses")
            raw_roles = raw_step.get("state_roles")
            raw_components = raw_step.get("state_components", [])
            return_to_entry = raw_step.get("return_to_entry", False)
            match_sustain = raw_step.get("match_sustain", False)
            require(semantic_phase in SCORE_PHASES and label and
                    isinstance(duration_ms, int) and duration_min <= duration_ms <= duration_max and
                    isinstance(raw_poses, dict) and isinstance(raw_roles, list) and
                    isinstance(raw_components, list) and
                    isinstance(return_to_entry, bool) and isinstance(match_sustain, bool),
                    f"registered-state score step is malformed for {name}")
            state_roles = tuple(str(role) for role in raw_roles)
            require(len(state_roles) == len(set(state_roles)) and set(state_roles).issubset(valid_roles),
                    f"registered-state score selects an unknown role for {name}")
            state_components = tuple(str(component) for component in raw_components)
            require(len(state_components) == len(set(state_components)) and
                    set(state_components).issubset(legal_offsets),
                    f"registered-state score selects an unknown component for {name}")
            require(not state_roles or bool(state_components),
                    f"registered-state score selects a role without exact state_components for {name}")
            require(not return_to_entry or not state_components,
                    f"registered-state score {name} cannot select state_components while returning to entry")
            poses: list[tuple[str, tuple[int, int]]] = []
            for component_name, raw_offset in raw_poses.items():
                require(isinstance(component_name, str) and component_name in legal_offsets and
                        isinstance(raw_offset, list) and len(raw_offset) == 2 and
                        all(isinstance(value, int) for value in raw_offset),
                        f"registered-state score {name} references an unregistered component pose")
                low, high = legal_offsets[component_name]
                offset = (int(raw_offset[0]), int(raw_offset[1]))
                require(low[0] <= offset[0] <= high[0] and low[1] <= offset[1] <= high[1],
                        f"registered-state score {name} places {component_name} outside its legal range")
                poses.append((component_name, offset))
            require(len({component for component, _ in poses}) == len(poses),
                    f"registered-state score {name} duplicates a component pose")
            steps.append(ScoreStep(semantic_phase, label, duration_ms, tuple(poses), return_to_entry,
                                   state_roles, match_sustain, state_components))
        phases = tuple(step.semantic_phase for step in steps)
        require(phases[0] == "entry" and phases[-1] == "settle" and steps[-1].return_to_entry and
                all(phase in phases for phase in SCORE_PHASES) and len(steps) >= len(SCORE_PHASES),
                f"registered-state score {name} is missing reusable performance phases")
        require(sum(step.semantic_phase == "hold" for step in steps) == 1 and
                sum(step.match_sustain for step in steps) == 1,
                f"registered-state score {name} must have one static Rig sustain match")
        performances[name] = PerformanceScore(beat_order, tuple(steps))
        drivers[name] = {field: driver[field] for field in driver_fields}
    require(tuple(performances) == REGISTERED_STATE_STORY_ORDER,
            "registered-state preview must cover every remaining registered story once in declaration order")
    return performances, drivers, contract


def load_expression_atlas_contract() -> dict[str, object]:
    contract = load_json(EXPRESSION_ATLAS)
    layout = load_json(LAYOUT)
    require(contract.get("schema") == "companion.v9_expression_rig_expression_atlas.v1" and
            contract.get("scope") == "all_registered_v9_stories" and
            contract.get("source_sha256") == LOCKED_SOURCE_HASH and
            contract.get("source_layout") == rel(LAYOUT) and
            contract.get("source_layout_revision") == layout.get("revision") and
            contract.get("runtime_resource_activated") is False,
            "expression atlas is not bound to the locked v9 Rig layout")
    presentation = contract.get("presentation")
    require(isinstance(presentation, dict) and
            presentation.get("first_viewport") == "compact_component_composed_expression_atlas" and
            presentation.get("selected_story_loop") is True and
            presentation.get("automatic_story_rotation") is False and
            presentation.get("atlas_thumbnail_phase") == "hold",
            "expression atlas presentation contract is invalid")
    families = contract.get("families")
    require(isinstance(families, list) and families, "expression atlas has no state families")
    ordered_stories: list[str] = []
    for family in families:
        require(isinstance(family, dict) and isinstance(family.get("id"), str) and
                isinstance(family.get("label_zh"), str) and isinstance(family.get("description_zh"), str) and
                isinstance(family.get("stories"), list),
                "expression atlas family is malformed")
        ordered_stories.extend(str(story) for story in family["stories"])
    require(set(ordered_stories) == set(STORY_ORDER) and len(ordered_stories) == len(set(ordered_stories)),
            "expression atlas must cover every registered V9 story exactly once")
    labels = contract.get("story_labels")
    events = contract.get("story_driver_events")
    require(isinstance(labels, dict) and set(labels) == set(STORY_ORDER) and
            all(isinstance(value, str) and value for value in labels.values()) and
            isinstance(events, dict) and set(events) == set(STORY_ORDER) and
            all(isinstance(value, str) and value for value in events.values()),
            "expression atlas labels or driver events are incomplete")
    fail_closed = contract.get("fail_closed_events")
    fail_closed_events = {
        str(item.get("event")): str(item.get("status")) for item in fail_closed
        if isinstance(fail_closed, list) and isinstance(item, dict)
    }
    require(fail_closed_events == {
        "charging": "fail_closed_no_registered_components",
        "error": "fail_closed_no_registered_components",
    }, "expression atlas must fail closed for charging and error")
    return contract


def interpolate_coordinate(start: int, end: int, numerator: int, denominator: int) -> int:
    delta = end - start
    magnitude = (abs(delta) * numerator + denominator // 2) // denominator
    return start + (magnitude if delta >= 0 else -magnitude)


def interpolate_role_layers(entry_layers: tuple[ComponentLayer, ...],
                            sustain_layers: tuple[ComponentLayer, ...],
                            numerator: int, denominator: int) -> tuple[ComponentLayer, ...]:
    entry_by_component = {layer.component: layer for layer in entry_layers}
    sustain_by_component = {layer.component: layer for layer in sustain_layers}
    if set(entry_by_component) != set(sustain_by_component):
        return entry_layers if numerator < denominator else sustain_layers
    result: list[ComponentLayer] = []
    for component in sorted(entry_by_component):
        entry_layer = entry_by_component[component]
        sustain_layer = sustain_by_component[component]
        if entry_layer.composite_op != sustain_layer.composite_op:
            return entry_layers if numerator < denominator else sustain_layers
        result.append(replace(
            entry_layer,
            x=interpolate_coordinate(entry_layer.x, sustain_layer.x, numerator, denominator),
            y=interpolate_coordinate(entry_layer.y, sustain_layer.y, numerator, denominator),
            offset=(
                interpolate_coordinate(entry_layer.offset[0], sustain_layer.offset[0], numerator, denominator),
                interpolate_coordinate(entry_layer.offset[1], sustain_layer.offset[1], numerator, denominator),
            ),
        ))
    return tuple(result)


def component_layers(layers: dict[str, tuple[ComponentLayer, ...]]) -> dict[str, ComponentLayer]:
    result: dict[str, ComponentLayer] = {}
    for role_layers in layers.values():
        for layer in role_layers:
            require(layer.component not in result, f"duplicate component layer: {layer.component}")
            result[layer.component] = layer
    return result


def groups_for_offsets(entry: dict[str, ComponentLayer],
                       offsets: dict[str, tuple[int, int]]) -> tuple[str, ...]:
    changed_roles = {
        layer.role for component, layer in entry.items()
        if offsets[component] != layer.offset
    }
    return tuple(label for label, roles in ROLE_GROUPS if any(role in changed_roles for role in roles))


def scored_layers(entry: dict[str, ComponentLayer],
                  offsets: dict[str, tuple[int, int]]) -> tuple[ComponentLayer, ...]:
    result: list[ComponentLayer] = []
    for component, layer in entry.items():
        offset = offsets[component]
        result.append(replace(
            layer,
            x=layer.x - layer.offset[0] + offset[0],
            y=layer.y - layer.offset[1] + offset[1],
            offset=offset,
        ))
    return tuple(sorted(result, key=lambda layer: (layer.z_index, layer.component)))


def compose_score_timeline(story: str,
                           phases: dict[str, dict[str, object]],
                           components: dict[str, dict[str, object]],
                           pngs: dict[str, pathlib.Path],
                           performance: PerformanceScore) -> tuple[list[PreviewFrame], set[str]]:
    entry_by_component = component_layers(layers_by_role(phases["entry"], components, pngs))
    sustain_by_component = component_layers(layers_by_role(phases["sustain"], components, pngs))
    settle_by_component = component_layers(layers_by_role(phases["settle"], components, pngs))
    require(set(entry_by_component) == set(sustain_by_component) == set(settle_by_component),
            f"Daily score {story} changes component identity instead of animating registered layers")
    entry_offsets = {component: layer.offset for component, layer in entry_by_component.items()}
    sustain_offsets = {component: layer.offset for component, layer in sustain_by_component.items()}
    current_offsets = dict(entry_offsets)
    frames: list[PreviewFrame] = []
    changed_groups: set[str] = set()
    saw_hold = False

    for step in performance.steps:
        if step.return_to_entry:
            current_offsets = dict(entry_offsets)
        else:
            for component, offset in step.poses:
                require(component in entry_by_component,
                        f"Daily score {story} poses a component absent from its entry Rig")
                current_offsets[component] = offset
        for component, layer in entry_by_component.items():
            if layer.role in {"left_eye", "right_eye"}:
                require(current_offsets[component] == entry_offsets[component],
                        f"Daily score {story} moves a V9 eye body instead of only its internal highlight")
        if step.semantic_phase == "hold":
            require(current_offsets == sustain_offsets,
                    f"Daily score {story} hold does not match the deterministic Rig sustain state")
            saw_hold = True
        if step.semantic_phase == "settle":
            require(current_offsets == entry_offsets,
                    f"Daily score {story} settle does not return to the calm entry state")
        active_groups = groups_for_offsets(entry_by_component, current_offsets)
        changed_groups.update(active_groups)
        frames.append(PreviewFrame(
            story=story,
            label=step.label,
            duration_ms=step.duration_ms,
            layers=scored_layers(entry_by_component, current_offsets),
            activated_groups=active_groups,
            semantic_phase=step.semantic_phase,
        ))
    require(saw_hold, f"Daily score {story} never reaches its deterministic sustain state")
    return frames, changed_groups


def selected_state_layers(entry: dict[str, tuple[ComponentLayer, ...]],
                          sustain: dict[str, tuple[ComponentLayer, ...]],
                          state_components: tuple[str, ...]) -> tuple[ComponentLayer, ...]:
    selected_components = set(state_components)
    sustain_components = {
        layer.component for role_layers in sustain.values() for layer in role_layers
    }
    require(selected_components.issubset(sustain_components),
            "state score selects a component absent from its source sustain Rig layers")
    layers: list[ComponentLayer] = []
    for role in sorted(set(entry) | set(sustain)):
        selected_for_role = tuple(
            layer for layer in sustain.get(role, ()) if layer.component in selected_components
        )
        layers.extend(selected_for_role if selected_for_role else entry.get(role, ()))
    result = tuple(sorted(layers, key=lambda layer: (layer.z_index, layer.component)))
    require(len({layer.component for layer in result}) == len(result),
            "state score selected a component more than once")
    return result


def layer_signature(layers: tuple[ComponentLayer, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple((layer.component, layer.role, layer.x, layer.y, layer.offset, layer.z_index,
                  layer.composite_op, layer.source_frame) for layer in layers)


def groups_for_layers(entry: tuple[ComponentLayer, ...],
                      current: tuple[ComponentLayer, ...]) -> tuple[str, ...]:
    entry_by_role: dict[str, list[ComponentLayer]] = {}
    current_by_role: dict[str, list[ComponentLayer]] = {}
    for layer in entry:
        entry_by_role.setdefault(layer.role, []).append(layer)
    for layer in current:
        current_by_role.setdefault(layer.role, []).append(layer)
    changed_roles = {
        role for role in set(entry_by_role) | set(current_by_role)
        if layer_signature(tuple(sorted(entry_by_role.get(role, ()), key=lambda item: (item.z_index, item.component)))) !=
        layer_signature(tuple(sorted(current_by_role.get(role, ()), key=lambda item: (item.z_index, item.component))))
    }
    return tuple(label for label, roles in ROLE_GROUPS if any(role in changed_roles for role in roles))


def offset_layers(layers: tuple[ComponentLayer, ...],
                  poses: tuple[tuple[str, tuple[int, int]], ...]) -> tuple[ComponentLayer, ...]:
    by_component = {layer.component: layer for layer in layers}
    offsets = {component: layer.offset for component, layer in by_component.items()}
    for component, offset in poses:
        require(component in offsets,
                f"state score poses a component absent from its selected Rig layers: {component}")
        offsets[component] = offset
    return tuple(sorted((replace(layer,
                                 x=layer.x - layer.offset[0] + offsets[layer.component][0],
                                 y=layer.y - layer.offset[1] + offsets[layer.component][1],
                                 offset=offsets[layer.component])
                         for layer in layers),
                        key=lambda layer: (layer.z_index, layer.component)))


def compose_registered_state_score_timeline(story: str,
                                            phases: dict[str, dict[str, object]],
                                            components: dict[str, dict[str, object]],
                                            pngs: dict[str, pathlib.Path],
                                            performance: PerformanceScore) -> tuple[list[PreviewFrame], set[str]]:
    entry_by_role = layers_by_role(phases["entry"], components, pngs)
    sustain_by_role = layers_by_role(phases["sustain"], components, pngs)
    settle_by_role = layers_by_role(phases["settle"], components, pngs)
    entry = selected_state_layers(entry_by_role, {}, ())
    all_sustain_components = tuple(
        layer.component for role_layers in sustain_by_role.values() for layer in role_layers
    )
    sustain = selected_state_layers({}, sustain_by_role, all_sustain_components)
    settle = selected_state_layers(settle_by_role, {}, ())
    all_sustain_roles = tuple(sorted({layer.role for layer in sustain}))
    frames: list[PreviewFrame] = []
    changed_groups: set[str] = set()
    saw_sustain = False
    for step in performance.steps:
        selected_roles = () if step.return_to_entry else step.state_roles
        selected_components = () if step.return_to_entry else step.state_components
        selected = selected_state_layers(entry_by_role, sustain_by_role, selected_components)
        current = offset_layers(selected, step.poses)
        selected_component_roles = {
            layer.role for layer in current if layer.component in set(selected_components)
        }
        require(selected_component_roles == set(selected_roles),
                f"registered-state score {story} role list diverges from exact selected components")
        if step.match_sustain:
            require(set(selected_components) == set(all_sustain_components) and
                    set(all_sustain_roles) == set(selected_roles),
                    f"registered-state score {story} sustain must name every source Rig component")
            require(not step.poses and layer_signature(current) == layer_signature(sustain),
                    f"registered-state score {story} hold does not exactly match the source Rig sustain state")
            saw_sustain = True
        if step.return_to_entry:
            require(not step.poses and layer_signature(current) == layer_signature(entry),
                    f"registered-state score {story} settle does not return exactly to the calm entry state")
        active_groups = groups_for_layers(entry, current)
        changed_groups.update(active_groups)
        frames.append(PreviewFrame(
            story=story,
            label=step.label,
            duration_ms=step.duration_ms,
            layers=current,
            activated_groups=active_groups,
            semantic_phase=step.semantic_phase,
            state_roles=selected_roles,
            state_components=selected_components,
        ))
    require(saw_sustain, f"registered-state score {story} never reaches the deterministic Rig sustain state")
    require(layer_signature(entry) == layer_signature(settle),
            f"registered-state score {story} does not preserve the calm entry/settle identity")
    return frames, changed_groups


def compose_timeline_for_story(story: str,
                               phases: dict[str, dict[str, object]],
                               components: dict[str, dict[str, object]],
                               pngs: dict[str, pathlib.Path],
                               performance: PerformanceScore | None = None) -> tuple[list[PreviewFrame], set[str]]:
    entry = layers_by_role(phases["entry"], components, pngs)
    sustain = layers_by_role(phases["sustain"], components, pngs)
    settle = layers_by_role(phases["settle"], components, pngs)
    if performance is not None:
        return compose_score_timeline(story, phases, components, pngs, performance)
    changed_groups: list[str] = []
    active_groups: list[str] = []
    output: list[PreviewFrame] = []

    def build(label: str, duration_ms: int, groups: tuple[str, ...], final_settle: bool = False,
              transition_group: str | None = None, transition_numerator: int = 0,
              transition_denominator: int = 1) -> PreviewFrame:
        active_roles = role_set(groups)
        transition_roles = role_set((transition_group,)) if transition_group is not None else set()
        source_roles = set(entry) | set(sustain) | set(settle)
        layers: list[ComponentLayer] = []
        for role in sorted(source_roles):
            if final_settle:
                selected = settle.get(role, ())
            elif role in transition_roles:
                selected = interpolate_role_layers(entry.get(role, ()), sustain.get(role, ()),
                                                   transition_numerator, transition_denominator)
            elif role in active_roles:
                selected = sustain.get(role, ())
            else:
                selected = entry.get(role, ())
            layers.extend(selected)
        return PreviewFrame(
            story=story,
            label=label,
            duration_ms=duration_ms,
            layers=tuple(sorted(layers, key=lambda layer: (layer.z_index, layer.component))),
            activated_groups=groups,
            semantic_phase="legacy",
        )

    for label, roles in ROLE_GROUPS:
        if role_signature(entry, roles) != role_signature(sustain, roles):
            changed_groups.append(label)
    output.append(build("entry baseline", 700, tuple()))
    for label in changed_groups:
        active_groups.append(label)
        output.append(build(label, 420, tuple(active_groups)))
    output.append(build("sustain hold", 1100, tuple(active_groups)))
    for label in reversed(changed_groups):
        output.append(build(f"settle {label}", 360, tuple(active_groups)))
        active_groups = [group for group in active_groups if group != label]
    output.append(build("settle baseline", 900, tuple(), final_settle=True))
    return output, set(changed_groups)


def compose_face(layers: tuple[ComponentLayer, ...]) -> Image.Image:
    canvas = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    for layer in layers:
        image = Image.open(layer.png).convert("RGBA")
        canvas.alpha_composite(image, (layer.x, layer.y))
    return canvas.convert("RGB")


def frame_pixel_distance(left: PreviewFrame, right: PreviewFrame) -> int:
    left_pixels = compose_face(left.layers).convert("1").getdata()
    right_pixels = compose_face(right.layers).convert("1").getdata()
    return sum(a != b for a, b in zip(left_pixels, right_pixels))


def timeline_metrics(frames: list[PreviewFrame]) -> dict[str, object]:
    by_label = {frame.label: frame for frame in frames}
    entry = by_label["entry baseline"]
    sustain = by_label["sustain hold"]
    settle = by_label["settle baseline"]
    sustain_index = frames.index(sustain)
    step_distances = [frame_pixel_distance(left, right) for left, right in zip(frames, frames[1:])]
    layer_offsets = [
        abs(layer.offset[0]) + abs(layer.offset[1])
        for layer in sustain.layers
    ]
    return {
        "entryToSustainPixels": frame_pixel_distance(entry, sustain),
        "entryToSettlePixels": frame_pixel_distance(entry, settle),
        "sustainGroupCount": len(sustain.activated_groups),
        "sustainLayerCount": len(sustain.layers),
        "maxLayerOffset": max(layer_offsets) if layer_offsets else 0,
        "intermediateFramesBeforeSustain": sustain_index - 1,
        "releaseFramesBeforeSettle": len(frames) - sustain_index - 2,
        "visibleStepCount": sum(distance > 0 for distance in step_distances),
        "maxStepPixels": max(step_distances, default=0),
    }


def score_frame_audit(frames: list[PreviewFrame]) -> list[dict[str, object]]:
    return [
        {
            "index": index,
            "phase": frame.semantic_phase,
            "label": frame.label,
            "duration_ms": frame.duration_ms,
            "activated_groups": list(frame.activated_groups),
            "state_roles": list(frame.state_roles),
            "state_components": list(frame.state_components),
            "component_offsets": {layer.component: list(layer.offset) for layer in frame.layers},
            "layers": [
                {
                    "component": layer.component,
                    "role": layer.role,
                    "source_frame": layer.source_frame,
                    "offset": list(layer.offset),
                    "composite_op": layer.composite_op,
                }
                for layer in frame.layers
            ],
        }
        for index, frame in enumerate(frames)
    ]


def preview_frame_image(frame: PreviewFrame, scale: int = 2) -> Image.Image:
    face = compose_face(frame.layers).resize((200 * scale, 200 * scale), Image.Resampling.NEAREST)
    image = Image.new("RGB", (200 * scale + 32, 200 * scale + 70), "white")
    draw = ImageDraw.Draw(image)
    draw.text((12, 10), frame.story, fill="black")
    draw.text((12, 30), frame.label, fill="black")
    image.paste(face, (16, 58))
    draw.rectangle((16, 58, 16 + 200 * scale - 1, 58 + 200 * scale - 1), outline="black")
    return image


def write_animated_gif(timelines: dict[str, list[PreviewFrame]], output: pathlib.Path,
                       story_order: tuple[str, ...]) -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []
    for story in story_order:
        for frame in timelines.get(story, []):
            frames.append(preview_frame_image(frame))
            durations.append(frame.duration_ms)
    require(frames, "no dynamic frames were generated")
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
    )


def write_keyframe_strip(timelines: dict[str, list[PreviewFrame]], output: pathlib.Path,
                         story_order: tuple[str, ...], daily_focus: bool) -> None:
    selected: list[PreviewFrame] = []
    for story in story_order:
        frames = timelines.get(story, [])
        if not frames:
            continue
        if daily_focus:
            selected.extend(frame for frame in frames
                            if frame.semantic_phase in {"entry", "lead", "response", "accent", "hold", "release", "settle"})
        else:
            selected.extend(frame for frame in frames
                            if frame.label in {"entry baseline", "sustain hold", "settle baseline"} or
                            frame.label in {group for group, _ in ROLE_GROUPS})
    require(selected, "no keyframes selected for strip")
    thumbs = [preview_frame_image(frame, scale=1) for frame in selected]
    columns = 5 if daily_focus else 4
    rows = (len(thumbs) + columns - 1) // columns
    cell_w, cell_h = thumbs[0].size
    strip = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for index, thumb in enumerate(thumbs):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        strip.paste(thumb, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    strip.save(output)


def html_story_data(timelines: dict[str, list[PreviewFrame]], story_order: tuple[str, ...],
                    artifact_root: pathlib.Path) -> dict[str, object]:
    stories: dict[str, object] = {}
    metrics: dict[str, object] = {}
    for story, frames in timelines.items():
        stories[story] = [
            {
                "label": frame.label,
                "semanticPhase": frame.semantic_phase,
                "durationMs": frame.duration_ms,
                "activatedGroups": list(frame.activated_groups),
                "stateRoles": list(frame.state_roles),
                "stateComponents": list(frame.state_components),
                "layers": [
                    {
                        "component": layer.component,
                        "role": layer.role,
                        "sourceFrame": layer.source_frame,
                        "x": layer.x,
                        "y": layer.y,
                        "offset": list(layer.offset),
                        "z": layer.z_index,
                        "compositeOp": layer.composite_op,
                        "src": layer.png.resolve().relative_to(artifact_root.resolve()).as_posix(),
                    }
                    for layer in frame.layers
                ],
            }
            for frame in frames
        ]
        metrics[story] = timeline_metrics(frames)
    return {
        "storyOrder": [story for story in story_order if story in stories],
        "stories": stories,
        "metrics": metrics,
    }


def build_html(timelines: dict[str, list[PreviewFrame]],
               dynamic_groups: set[str],
               missing_groups: set[str], story_order: tuple[str, ...], scope: str,
               drivers: dict[str, dict[str, object]] | None = None,
               presentation_mode: str = "continuous_story_cycle",
               atlas_contract: dict[str, object] | None = None,
               artifact_root: pathlib.Path | None = None) -> str:
    require(artifact_root is not None, "dynamic preview HTML requires an explicit artifact root")
    data = html_story_data(timelines, story_order, artifact_root)
    data["drivers"] = drivers or {}
    if presentation_mode == "state_bound_single_story_loop":
        data["stateBound"] = True
    if scope == "daily_selected_state":
        data["defaultStory"] = "daily_right"
    atlas_mode = atlas_contract is not None
    if atlas_contract is not None:
        data["atlas"] = {
            "families": atlas_contract["families"],
            "storyLabels": atlas_contract["story_labels"],
            "thumbnailPhase": atlas_contract["presentation"]["atlas_thumbnail_phase"],
        }
        data["defaultStory"] = "touch_left"
    rows = "".join(
        f"<tr><th>{html.escape(group)}</th><td>{'PASS' if group in dynamic_groups else 'fail-closed / not registered'}</td></tr>"
        for group in sorted(REQUIRED_DYNAMIC_GROUPS)
    )
    missing = ", ".join(sorted(missing_groups)) if missing_groups else "none"
    atlas_section = """
  <section class="expression-atlas" aria-label="V9 expression atlas">
    <div class="atlas-heading">
      <div><h2>V9 全部已登记表情</h2><div class="atlas-meta">12 个 source-component 状态；当前选中状态独立循环。</div></div>
      <div id="atlasSelected" class="selected-state"></div>
    </div>
    <div id="expressionAtlas" class="atlas-families"></div>
  </section>
""" if atlas_mode else ""
    selector_section = "" if atlas_mode else "      <div id=\"controls\" class=\"controls\"></div>"
    library_section = "" if atlas_mode else """
  <section class="library">
    <h2>Expression Stories</h2>
    <div id="storyCards" class="story-cards"></div>
  </section>
"""
    atlas_class = " atlas-mode" if atlas_mode else ""
    title = "Companion v9 情绪图谱" if atlas_mode else "Companion v9 动态表情 Rig Library"
    header_meta = "锁定 V9 | source-component Rig | runtime inactive" if atlas_mode else \
        f"电脑侧组件播放器。所有表情都由 V9 source-derived component PNG 层组合；候选 runtime inactive；当前范围：{html.escape(scope)}。"
    header_state = "准备、回应、停留、恢复" if atlas_mode else \
        "Entry 必须贴近 calm baseline；Sustain 展示更明显的眼睛、眉、嘴、腮点和挂件变化；Settle 回到同一张 V9 身份。"
    audit_section = "" if atlas_mode else f"""
  <section class="audit">
      <h2>Component Motion Audit</h2>
      <table><tbody>{rows}</tbody></table>
      <div class="warning">Missing dynamic groups: {html.escape(missing)}. Charging/error remain fail-closed because no approved V9 components are registered for them.</div>
      <p>Static matrix/CEMP are audit artifacts only; this player does not use full-frame PBM/CEMP images as its animation source.</p>
  </section>
"""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Companion v9 component Rig dynamic preview</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Microsoft YaHei UI", Arial, sans-serif;
      color: #181818;
      background: #efeee8;
    }}
    main {{ max-width: 1420px; margin: 0 auto; padding: 20px; }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: end;
      margin-bottom: 14px;
    }}
    h1 {{ margin: 0; font-size: 26px; }}
    h2 {{ margin: 0 0 10px; font-size: 17px; }}
    p {{ line-height: 1.45; }}
    .meta {{ max-width: 600px; font-size: 13px; line-height: 1.45; color: #3d3d3d; }}
    .expression-atlas {{ border: 1px solid #2b2b2b; background: #fff; padding: 14px; margin-bottom: 16px; }}
    .atlas-heading {{ display: flex; justify-content: space-between; align-items: end; gap: 16px; margin-bottom: 12px; }}
    .atlas-meta {{ font-size: 13px; color: #3d3d3d; }}
    .selected-state {{ border: 1px solid #111; background: #f1f6ff; padding: 7px 9px; font-size: 13px; }}
    .atlas-families {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }}
    .atlas-family {{ border: 1px solid #c5c1b5; background: #fbfbf8; min-width: 0; }}
    .atlas-family-title {{ padding: 8px 9px 4px; font-weight: 700; font-size: 14px; }}
    .atlas-family-note {{ padding: 0 9px 8px; min-height: 42px; color: #4a4a4a; font-size: 11px; line-height: 1.35; }}
    .atlas-state-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; padding: 0 6px 6px; }}
    .atlas-state {{ min-height: 126px; border: 1px solid #b8b3a6; background: #fff; padding: 5px; text-align: left; font-family: inherit; }}
    .atlas-state.active {{ border: 2px solid #111; background: #f1f6ff; }}
    .atlas-face-shell {{ width: 94px; height: 94px; margin: 0 auto 4px; overflow: hidden; background: white; border-bottom: 1px solid #e0ddd3; }}
    .atlas-stage {{ position: relative; width: 200px; height: 200px; transform: scale(0.47); transform-origin: top left; background: white; }}
    .atlas-state-label {{ display: block; font-weight: 700; font-size: 12px; overflow-wrap: anywhere; }}
    .atlas-state-driver {{ display: block; margin-top: 3px; color: #4a4a4a; font-size: 10px; line-height: 1.3; overflow-wrap: anywhere; }}
    .workspace {{ display: grid; grid-template-columns: minmax(700px, 1fr) 410px; gap: 16px; align-items: start; }}
    .stage-panel, .inspect, .library, .audit {{
      background: #ffffff;
      border: 1px solid #2b2b2b;
    }}
    .stage-panel {{ padding: 16px; }}
    .stage-row {{ display: grid; grid-template-columns: 600px 196px; gap: 16px; align-items: start; }}
    .stage-shell {{
      width: 600px;
      height: 600px;
      background: white;
      border: 2px solid #111;
      overflow: hidden;
      box-shadow: 0 8px 0 #d5d1c4;
    }}
    .stage, .mini-stage {{
      position: relative;
      width: 200px;
      height: 200px;
      background: white;
    }}
    .stage {{ transform: scale(3); transform-origin: top left; }}
    .stage img, .mini-stage img {{ position: absolute; image-rendering: pixelated; }}
    .compare {{ grid-column: 1 / -1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .compare-cell {{ border: 1px solid #9d9d9d; padding: 8px; background: #fbfbf8; }}
    .compare-label {{ font-size: 12px; margin-bottom: 6px; color: #303030; }}
    .mini-shell {{ width: 160px; height: 160px; overflow: hidden; border: 1px solid #111; background: white; }}
    .mini-stage {{ transform: scale(0.8); transform-origin: top left; }}
    .eye-audit {{ display: grid; gap: 10px; align-content: start; }}
    .eye-card {{ border: 1px solid #9d9d9d; padding: 8px; background: #fbfbf8; }}
    .eye-label {{ font-size: 12px; margin-bottom: 6px; color: #303030; }}
    .eye-shell {{ position: relative; width: 180px; height: 180px; overflow: hidden; border: 1px solid #111; background: white; }}
    .eye-stage {{ position: absolute; width: 200px; height: 200px; transform: scale(3); transform-origin: top left; }}
    .eye-stage img {{ position: absolute; image-rendering: pixelated; }}
    .eye-offset {{ margin-top: 6px; font-size: 11px; line-height: 1.4; color: #303030; }}
    .controls, .story-cards, .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .controls {{ margin: 14px 0 0; }}
    button {{
      min-height: 34px;
      border: 1px solid #4e4e4e;
      background: #fff;
      padding: 7px 10px;
      cursor: pointer;
      font-size: 13px;
    }}
    button.active {{ background: #111; color: white; }}
    .inspect {{ padding: 14px; }}
    .frame-label {{ font-size: 14px; margin: 4px 0 12px; color: #303030; }}
    .meter {{ margin: 8px 0 14px; }}
    .meter-line {{ height: 12px; border: 1px solid #111; background: #f0efe8; }}
    .meter-fill {{ display: block; height: 100%; width: 0%; background: #2c7a66; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin: 10px 0 14px; }}
    .metric {{ border: 1px solid #c5c1b5; padding: 8px; background: #faf9f3; }}
    .metric strong {{ display: block; font-size: 18px; }}
    .badge {{ border: 1px solid #111; padding: 4px 7px; font-size: 12px; background: #e7f4ef; }}
    .library {{ margin-top: 16px; padding: 14px; }}
    .story-card {{ width: 166px; border: 1px solid #b8b3a6; padding: 9px; background: #fbfbf8; }}
    .story-card.active {{ border-color: #111; background: #f1f6ff; }}
    .story-card button {{ width: 100%; border-color: #111; margin-bottom: 8px; }}
    .small-meter {{ height: 7px; border: 1px solid #8b887d; background: #eeeae0; }}
    .small-meter span {{ display: block; height: 100%; background: #315f8c; }}
    .audit {{ margin-top: 16px; padding: 14px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 10px; font-size: 12px; }}
    th, td {{ border: 1px solid #c8c8c8; padding: 6px; text-align: left; vertical-align: top; }}
    .warning {{ margin-top: 10px; padding: 9px; border-left: 4px solid #b77a00; background: #fff4d9; }}
    .atlas-mode .stage-panel {{ padding: 14px; }}
    .atlas-mode .stage-row {{ grid-template-columns: 600px; }}
    .atlas-mode .eye-audit {{ display: none; }}
    .atlas-mode .metric-grid {{ display: none; }}
    .atlas-mode .inspect {{ padding: 14px; }}
    .atlas-mode .inspect table {{ display: none; }}
    @media (max-width: 1180px) {{
      .workspace, .stage-row {{ grid-template-columns: 1fr; }}
      .stage-shell {{ width: 540px; height: 540px; }}
      .stage {{ transform: scale(2.7); }}
    }}
    @media (max-width: 980px) {{
      .atlas-families {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .atlas-heading {{ align-items: start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
<main class="{atlas_class.strip()}">
  <header>
    <div>
      <h1>{title}</h1>
      <div class="meta">{header_meta}</div>
    </div>
    <div class="meta">{header_state}</div>
  </header>
{atlas_section}
  <div class="workspace">
    <section class="stage-panel">
      <div class="stage-row">
        <div id="stageShell" class="stage-shell"><div class="stage"></div></div>
        <div id="eyeAudit" class="eye-audit"></div>
        <div class="compare" id="compare"></div>
      </div>
{selector_section}
    </section>
    <section class="inspect">
      <h2 id="storyTitle">story</h2>
      <div id="frameLabel" class="frame-label"></div>
      <div class="meter">
        <div id="distanceText"></div>
        <div class="meter-line"><span id="distanceBar" class="meter-fill"></span></div>
      </div>
      <div class="metric-grid">
        <div class="metric"><strong id="groupCount">0</strong>dynamic groups</div>
        <div class="metric"><strong id="layerCount">0</strong>sustain layers</div>
        <div class="metric"><strong id="offsetMax">0</strong>max layer offset</div>
        <div class="metric"><strong id="settleDistance">0</strong>settle pixels</div>
      </div>
      <div id="groupBadges" class="badges"></div>
      <table><tbody id="activeLayers"></tbody></table>
    </section>
  </div>
{library_section}
{audit_section}
</main>
<script>
const DATA = {json.dumps(data, ensure_ascii=False)};
let story = DATA.defaultStory || DATA.storyOrder[0];
let frameIndex = 0;
let timer = null;

function driverText(item) {{
  const driver = DATA.drivers[item];
  if (!driver) {{
    return 'driver=shared showcase';
  }}
  return 'event=' + driver.event + ' | emotion=' + driver.emotion +
    ' | attention=' + driver.attention + ' | energy=' + driver.energy +
    ' | interaction_memory=' + driver.interaction_memory;
}}

function driverShort(item) {{
  const driver = DATA.drivers[item];
  if (!driver) {{
    return 'shared preview';
  }}
  return driver.event + ' | ' + driver.emotion + ' | ' + driver.attention;
}}

function selectStory(item) {{
  story = item;
  frameIndex = 0;
  renderControls();
  renderAtlas();
  renderFrame();
}}

function renderControls() {{
  const controls = document.getElementById('controls');
  const cards = document.getElementById('storyCards');
  if (!controls || !cards) {{
    return;
  }}
  controls.innerHTML = '';
  cards.innerHTML = '';
  for (const item of DATA.storyOrder) {{
    const metric = DATA.metrics[item];
    const button = document.createElement('button');
    button.textContent = item;
    button.className = item === story ? 'active' : '';
    button.onclick = () => selectStory(item);
    controls.appendChild(button);
    const card = document.createElement('div');
    card.className = item === story ? 'story-card active' : 'story-card';
    const cardButton = document.createElement('button');
    cardButton.textContent = item;
    cardButton.onclick = button.onclick;
    const width = Math.min(100, Math.round(metric.entryToSustainPixels / 45));
    card.innerHTML =
      '<div class="small-meter"><span style="width:' + width + '%"></span></div>' +
      '<div>' + metric.entryToSustainPixels + ' px movement</div>' +
      '<div>' + metric.sustainGroupCount + ' groups</div>' +
      '<div>' + driverText(item) + '</div>';
    card.prepend(cardButton);
    cards.appendChild(card);
  }}
}}

function renderAtlas() {{
  const atlas = document.getElementById('expressionAtlas');
  const selected = document.getElementById('atlasSelected');
  if (!atlas || !selected || !DATA.atlas) {{
    return;
  }}
  atlas.innerHTML = '';
  selected.textContent = '正在播放：' + DATA.atlas.storyLabels[story] + ' / ' + driverShort(story);
  for (const family of DATA.atlas.families) {{
    const familyNode = document.createElement('section');
    familyNode.className = 'atlas-family';
    const title = document.createElement('div');
    title.className = 'atlas-family-title';
    title.textContent = family.label_zh;
    const note = document.createElement('div');
    note.className = 'atlas-family-note';
    note.textContent = family.description_zh;
    const states = document.createElement('div');
    states.className = 'atlas-state-grid';
    for (const item of family.stories) {{
      const frames = DATA.stories[item];
      const hold = frames.find(frame => frame.semanticPhase === DATA.atlas.thumbnailPhase) || frames[0];
      const card = document.createElement('button');
      card.type = 'button';
      card.className = item === story ? 'atlas-state active' : 'atlas-state';
      const face = document.createElement('div');
      face.className = 'atlas-face-shell';
      renderLayered(face, hold, 'atlas-stage');
      const label = document.createElement('span');
      label.className = 'atlas-state-label';
      label.textContent = DATA.atlas.storyLabels[item];
      const driver = document.createElement('span');
      driver.className = 'atlas-state-driver';
      driver.textContent = driverShort(item);
      card.appendChild(face);
      card.appendChild(label);
      card.appendChild(driver);
      card.onclick = () => selectStory(item);
      states.appendChild(card);
    }}
    familyNode.appendChild(title);
    familyNode.appendChild(note);
    familyNode.appendChild(states);
    atlas.appendChild(familyNode);
  }}
}}

function renderLayered(target, frame, scaleClass) {{
  target.innerHTML = '';
  const stage = document.createElement('div');
  stage.className = scaleClass;
  for (const layer of frame.layers) {{
    const img = document.createElement('img');
    img.src = layer.src;
    img.alt = layer.component;
    img.style.left = layer.x + 'px';
    img.style.top = layer.y + 'px';
    img.style.zIndex = layer.z;
    stage.appendChild(img);
  }}
  target.appendChild(stage);
}}

function renderCompare(frames) {{
  const compare = document.getElementById('compare');
  compare.innerHTML = '';
  const picks = [
    ['entry', frames[0]],
    ['sustain', frames.find(frame => frame.label === 'sustain hold') || frames[Math.floor(frames.length / 2)]],
    ['settle', frames[frames.length - 1]],
  ];
  for (const item of picks) {{
    const cell = document.createElement('div');
    cell.className = 'compare-cell';
    const label = document.createElement('div');
    label.className = 'compare-label';
    label.textContent = item[0] + ' / ' + item[1].label;
    const shell = document.createElement('div');
    shell.className = 'mini-shell';
    renderLayered(shell, item[1], 'mini-stage');
    cell.appendChild(label);
    cell.appendChild(shell);
    compare.appendChild(cell);
  }}
}}

function renderEyeAudit(frame) {{
  const audit = document.getElementById('eyeAudit');
  audit.innerHTML = '';
  const eyes = [
    {{ side: 'left', origin: [32, 106] }},
    {{ side: 'right', origin: [116, 106] }},
  ];
  for (const eye of eyes) {{
    const card = document.createElement('div');
    card.className = 'eye-card';
    const label = document.createElement('div');
    label.className = 'eye-label';
    label.textContent = eye.side + ' eye / component audit';
    const shell = document.createElement('div');
    shell.className = 'eye-shell';
    const stage = document.createElement('div');
    stage.className = 'eye-stage';
    stage.style.left = (-eye.origin[0] * 3) + 'px';
    stage.style.top = (-eye.origin[1] * 3) + 'px';
    for (const layer of frame.layers) {{
      const img = document.createElement('img');
      img.src = layer.src;
      img.alt = layer.component;
      img.style.left = layer.x + 'px';
      img.style.top = layer.y + 'px';
      img.style.zIndex = layer.z;
      stage.appendChild(img);
    }}
    shell.appendChild(stage);
    const reflection = frame.layers.filter(layer =>
      layer.role === eye.side + '_highlight' || layer.role === eye.side + '_sparkle');
    const primary = reflection.find(layer => layer.role === eye.side + '_highlight');
    const sparkle = reflection.find(layer => layer.role === eye.side + '_sparkle');
    const offsets = document.createElement('div');
    offsets.className = 'eye-offset';
    offsets.textContent = 'primary motion ' + (primary ? primary.offset.join(',') : 'missing') +
      ' | sparkle motion ' + (sparkle ? sparkle.offset.join(',') : 'missing');
    card.appendChild(label);
    card.appendChild(shell);
    card.appendChild(offsets);
    audit.appendChild(card);
  }}
}}

function renderFrame() {{
  if (timer !== null) {{
    window.clearTimeout(timer);
  }}
  const frames = DATA.stories[story];
  const frame = frames[frameIndex % frames.length];
  const metric = DATA.metrics[story];
  renderLayered(document.getElementById('stageShell'), frame, 'stage');
  renderEyeAudit(frame);
  renderCompare(frames);
  document.getElementById('storyTitle').textContent = story + ' / ' + driverText(story);
  document.getElementById('frameLabel').textContent =
    frame.label + ' / ' + (frame.activatedGroups.join(', ') || 'calm baseline') +
    ' / state roles=' + (frame.stateRoles.join(', ') || 'entry');
  document.getElementById('distanceText').textContent =
    'entry to sustain: ' + metric.entryToSustainPixels + ' pixels';
  document.getElementById('distanceBar').style.width =
    Math.min(100, Math.round(metric.entryToSustainPixels / 45)) + '%';
  document.getElementById('groupCount').textContent = metric.sustainGroupCount;
  document.getElementById('layerCount').textContent = metric.sustainLayerCount;
  document.getElementById('offsetMax').textContent = metric.maxLayerOffset;
  document.getElementById('settleDistance').textContent = metric.entryToSettlePixels;
  const badges = document.getElementById('groupBadges');
  badges.innerHTML = '';
  for (const group of frame.activatedGroups) {{
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = group;
    badges.appendChild(badge);
  }}
  const activeLayers = document.getElementById('activeLayers');
  activeLayers.innerHTML = '';
  for (const layer of frame.layers) {{
    const row = document.createElement('tr');
    row.innerHTML =
      '<th>' + layer.role + '</th><td>' + layer.component + '</td><td>source=' +
      layer.sourceFrame + '</td><td>xy=' + layer.x + ',' + layer.y + '</td><td>offset=' +
      layer.offset[0] + ',' + layer.offset[1] + '</td>';
    activeLayers.appendChild(row);
  }}
  frameIndex += 1;
  if (frameIndex >= frames.length) {{
    if (DATA.stateBound === true) {{
      frameIndex = 0;
    }} else {{
      const currentStoryIndex = DATA.storyOrder.indexOf(story);
      story = DATA.storyOrder[(currentStoryIndex + 1) % DATA.storyOrder.length];
      frameIndex = 0;
      renderControls();
    }}
  }}
  timer = window.setTimeout(renderFrame, frame.durationMs);
}}

renderControls();
renderAtlas();
renderFrame();
</script>
</body>
</html>
"""


def validate_reports(render_report: dict[str, object],
                     cemp_report: dict[str, object],
                     choreographer_report: dict[str, object]) -> None:
    require(render_report.get("status") == "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW",
            "Rig render report is not PASS")
    require(cemp_report.get("status") == "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED",
            "Rig CEMP verification is not PASS")
    require(choreographer_report.get("status") == "PASS",
            "choreographer report is not PASS")
    require(render_report.get("source_sha256") == LOCKED_SOURCE_HASH,
            "render report source hash drifted")
    require(render_report.get("runtime_resource_activated") is False and
            cemp_report.get("runtime_resource_activated") is False and
            choreographer_report.get("runtime_resource_activated") is False,
            "dynamic preview cannot activate runtime")


def render(report_path: pathlib.Path, scope: str = "full_library", *,
           render_report_path: pathlib.Path = RENDER_REPORT,
           cemp_report_path: pathlib.Path = CEMP_REPORT,
           choreographer_report_path: pathlib.Path = CHOREOGRAPHER_REPORT,
           artifact_root: pathlib.Path | None = None) -> dict[str, object]:
    require(artifact_root is not None,
            "dynamic preview requires an explicit revisioned --artifact-root; mutable candidate output is not evidence")
    artifact_root = artifact_root.resolve()
    try:
        artifact_root.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("dynamic preview artifact root must stay inside the repository") from exc
    render_report_path = render_report_path.resolve()
    cemp_report_path = cemp_report_path.resolve()
    choreographer_report_path = choreographer_report_path.resolve()
    render_report = load_json(render_report_path)
    cemp_report = load_json(cemp_report_path)
    choreographer_report = load_json(choreographer_report_path)
    validate_reports(render_report, cemp_report, choreographer_report)
    artifacts = artifacts_for_scope(scope, artifact_root)
    story_order = STORY_ORDER if scope == "full_library" else DAILY_STORY_ORDER
    daily_performances: dict[str, PerformanceScore] = {}
    registered_state_performances: dict[str, PerformanceScore] = {}
    state_drivers: dict[str, dict[str, object]] = {}
    state_preview_contract: dict[str, object] | None = None
    atlas_contract: dict[str, object] | None = None
    if scope in {"daily_focus", "daily_selected_state"}:
        daily_performances = load_daily_choreography()
    elif scope == "registered_states":
        story_order = REGISTERED_STATE_STORY_ORDER
        registered_state_performances, state_drivers, state_preview_contract = \
            load_registered_state_choreography()
    elif scope == "expression_atlas":
        story_order = STORY_ORDER
        daily_performances = load_daily_choreography()
        registered_state_performances, registered_drivers, state_preview_contract = \
            load_registered_state_choreography()
        atlas_contract = load_expression_atlas_contract()
        layout_stories = {
            str(item.get("name")): item for item in load_json(LAYOUT).get("stories", [])
            if isinstance(item, dict)
        }
        events = atlas_contract["story_driver_events"]
        for story in STORY_ORDER:
            layout_story = layout_stories.get(story)
            require(isinstance(layout_story, dict), f"expression atlas story is absent from the Rig: {story}")
            driver = {
                "event": events[story],
                "emotion": layout_story["emotion"],
                "attention": layout_story["attention"],
                "energy": layout_story["energy"],
                "interaction_memory": layout_story["interaction_memory"],
            }
            if story in registered_drivers:
                require(driver == registered_drivers[story],
                        f"expression atlas driver drifted from registered state score: {story}")
            state_drivers[story] = driver
    pngs = export_component_pngs(render_report, artifacts.layer_dir)
    components = component_index(render_report)
    stories = story_frames(render_report)
    timelines: dict[str, list[PreviewFrame]] = {}
    dynamic_groups: set[str] = set()
    for story in story_order:
        if story not in stories:
            continue
        if story in registered_state_performances:
            timeline, changed = compose_registered_state_score_timeline(
                story, stories[story], components, pngs, registered_state_performances[story],
            )
        else:
            timeline, changed = compose_timeline_for_story(
                story, stories[story], components, pngs,
                daily_performances.get(story),
            )
        timelines[story] = timeline
        dynamic_groups.update(changed)
    required_groups = REQUIRED_DYNAMIC_GROUPS if scope in {"full_library", "registered_states", "expression_atlas"} else \
        REQUIRED_DYNAMIC_GROUPS - {"side detail strokes"}
    missing_groups = required_groups - dynamic_groups
    require(not missing_groups, f"dynamic preview is missing groups: {', '.join(sorted(missing_groups))}")
    if scope == "full_library":
        require("swipe_left" in timelines and "swipe_right" in timelines,
                "side detail stroke stories are missing")
    if scope == "registered_states":
        require(tuple(timelines) == REGISTERED_STATE_STORY_ORDER,
                "registered-state preview is missing a declared state story")
    if scope == "expression_atlas":
        require(tuple(timelines) == STORY_ORDER,
                "expression atlas is missing a registered V9 story")
    require(all(frame.layers for frames in timelines.values() for frame in frames),
            "dynamic preview has an empty frame")
    presentation_mode = "state_bound_single_story_loop" if scope in {
        "daily_selected_state", "registered_states", "expression_atlas",
    } else "continuous_story_cycle"
    html_content = build_html(
        timelines, dynamic_groups, missing_groups, story_order, scope, state_drivers,
        presentation_mode,
        atlas_contract,
        artifact_root,
    )
    artifacts.dynamic_page.write_text(html_content, encoding="utf-8")
    artifacts.owner_review_page.write_text(html_content, encoding="utf-8")
    playback_story_order = ("daily_right",) if scope == "daily_selected_state" else story_order
    write_animated_gif(timelines, artifacts.animated_gif, playback_story_order)
    write_keyframe_strip(
        timelines, artifacts.keyframe_strip, playback_story_order,
        scope in {"daily_focus", "daily_selected_state"},
    )

    story_sequences = []
    for story, frames in timelines.items():
        metrics = timeline_metrics(frames)
        story_sequences.append({
            "story": story,
            "beats": list(daily_performances[story].beats) if story in daily_performances else
            list(registered_state_performances[story].beats) if story in registered_state_performances else [],
            "driver": state_drivers.get(story),
            "frame_count": len(frames),
            "intermediate_frames_before_sustain": metrics["intermediateFramesBeforeSustain"],
            "release_frames_before_settle": metrics["releaseFramesBeforeSettle"],
            "visible_step_count": metrics["visibleStepCount"],
            "max_step_pixels": metrics["maxStepPixels"],
            "semantic_phases": [frame.semantic_phase for frame in frames],
            "frame_audit": score_frame_audit(frames) if story in daily_performances or
            story in registered_state_performances else [],
        })

    result = {
        "schema": "companion.v9_expression_rig_dynamic_preview.v1",
        "status": "PASS_DYNAMIC_COMPONENT_PREVIEW_READY",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "preview_scope": scope,
        "input_evidence": {
            "render_report": {"path": rel(render_report_path), "sha256": sha256(render_report_path)},
            "cemp_report": {"path": rel(cemp_report_path), "sha256": sha256(cemp_report_path)},
            "choreographer_report": {
                "path": rel(choreographer_report_path),
                "sha256": sha256(choreographer_report_path),
            },
            "artifact_root": rel(artifact_root),
        },
        "review_page": rel(artifacts.dynamic_page),
        "review_page_sha256": sha256(artifacts.dynamic_page),
        "owner_review_page": rel(artifacts.owner_review_page),
        "owner_review_page_sha256": sha256(artifacts.owner_review_page),
        "animated_preview": rel(artifacts.animated_gif),
        "animated_preview_sha256": sha256(artifacts.animated_gif),
        "keyframe_strip": rel(artifacts.keyframe_strip),
        "keyframe_strip_sha256": sha256(artifacts.keyframe_strip),
        "component_layer_dir": rel(artifacts.layer_dir),
        "component_layer_count": len(pngs),
        "story_count": len(timelines),
        "stories": list(timelines.keys()),
        "playback_story_order": list(playback_story_order),
        "dynamic_groups": sorted(dynamic_groups),
        "story_sequences": story_sequences,
        "preview_choreography": {
            "scope": scope,
            "source": rel(EXPRESSION_ATLAS) if atlas_contract is not None else
            rel(LAYOUT) if scope in {"daily_focus", "daily_selected_state"} else
            rel(STATE_PREVIEW_SCORE) if scope == "registered_states" else None,
            "source_sha256": sha256(EXPRESSION_ATLAS) if atlas_contract is not None else
            sha256(STATE_PREVIEW_SCORE) if scope == "registered_states" else None,
            "source_layout": rel(LAYOUT) if scope in {"registered_states", "expression_atlas"} else None,
            "source_layout_revision": atlas_contract.get("source_layout_revision") if atlas_contract is not None else
            state_preview_contract.get("source_layout_revision") if state_preview_contract is not None else None,
            "schema": atlas_contract.get("schema") if atlas_contract is not None else
            "companion.v9_expression_rig_performance_score.v2" if scope in {"daily_focus", "daily_selected_state"} else
            state_preview_contract.get("schema") if state_preview_contract is not None else None,
            "presentation_mode": "state_bound_single_story_loop" if scope == "daily_selected_state" or atlas_contract is not None else
            state_preview_contract.get("presentation", {}).get("mode")
            if state_preview_contract is not None else "continuous_story_cycle",
            "automatic_story_rotation": False if scope == "daily_selected_state" or atlas_contract is not None else
            state_preview_contract.get("presentation", {}).get("automatic_story_rotation")
            if state_preview_contract is not None else True,
            "intermediate_layer_policy": "each score frame composes only registered component masks at its declared legal offset; no full-face frame is animated",
        },
        "side_detail_strokes": {
            "status": "source_confirmed_registered" if scope in {"full_library", "registered_states"} else "fail_closed_not_in_daily_scope",
            "source_frames": ["swipe_left", "swipe_right"],
            "components": ["left_detail_swipe", "right_detail_swipe"],
            "usage_limit": "only swipe left/right stories; daily focus keeps this feature fail-closed",
        },
        "nose_mouth_group": {
            "nose": "anchored source component",
            "mouth": "legal source component offset drives visible lip/mouth change",
        },
        "charging_error": "fail_closed_no_registered_components",
        "state_drivers": state_drivers,
        "expression_atlas": {
            "contract": rel(EXPRESSION_ATLAS),
            "contract_sha256": sha256(EXPRESSION_ATLAS),
            "families": atlas_contract.get("families"),
            "story_labels": atlas_contract.get("story_labels"),
            "first_viewport": atlas_contract.get("presentation", {}).get("first_viewport"),
            "thumbnail_phase": atlas_contract.get("presentation", {}).get("atlas_thumbnail_phase"),
        } if atlas_contract is not None else None,
        "animation_source": "component_png_layers_from_crig_masks",
        "forbidden_animation_sources": ["whole-face PBM flipbook", "static contact sheet", "legacy art", "code-drawn face", "custom LUT"],
        "human_prompt_launched": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--render-report", type=pathlib.Path, default=RENDER_REPORT)
    parser.add_argument("--cemp-report", type=pathlib.Path, default=CEMP_REPORT)
    parser.add_argument("--choreographer-report", type=pathlib.Path, default=CHOREOGRAPHER_REPORT)
    parser.add_argument("--artifact-root", type=pathlib.Path, required=True,
                        help="Versioned output root; the mutable legacy candidate root is not accepted.")
    parser.add_argument("--scope", choices=(
        "full_library", "daily_focus", "daily_selected_state", "registered_states", "expression_atlas",
    ), default="full_library")
    args = parser.parse_args()
    try:
        result = render(
            args.write.resolve(), args.scope,
            render_report_path=args.render_report,
            cemp_report_path=args.cemp_report,
            choreographer_report_path=args.choreographer_report,
            artifact_root=args.artifact_root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"PASS: component-layer dynamic v9 Rig preview ready at {result['review_page']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
