#!/usr/bin/env python3
"""Verify the v9 Rig dynamic preview before an owner visual prompt."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections.abc import Iterable

from PIL import Image, ImageSequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PREVIEW_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-dynamic-preview-20260717.json"
DEFAULT_RENDER_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-rig-preview-distance-20260717.json"
DEFAULT_ACCEPTED_BASELINE = ROOT / "docs/validation/companion-v9-expression-rig-accepted-dynamic-baseline.json"
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
MIN_CALIBRATED_DAILY_VISIBLE_DISTANCE_PIXELS = 600
MAX_WHOLE_FACE_DISTANCE_PIXELS = 6500
MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS = 0
REQUIRED_DYNAMIC_STORIES = {
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
}
REQUIRED_DYNAMIC_GROUPS = {
    "eyes/highlights",
    "brows",
    "nose-mouth/lips",
    "cheeks",
    "side detail strokes",
    "small charm",
}
DAILY_FOCUS_STORIES = {"daily_left", "daily_right", "daily_up", "daily_down"}
DAILY_FOCUS_GROUPS = REQUIRED_DYNAMIC_GROUPS - {"side detail strokes"}
DAILY_PREVIEW_SCOPES = {"daily_focus", "daily_selected_state"}
MIN_DAILY_INTERMEDIATE_FRAMES = 8
MIN_DAILY_RELEASE_FRAMES = 4
MIN_DAILY_VISIBLE_STEPS = 8
SCORE_PHASES = ("entry", "prepare", "lead", "response", "accent", "hold", "release", "return", "settle")
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
DAILY_MIN_OUTLINE_CLEARANCE_PIXELS = {
    "daily_left": 4,
    "daily_right": 5,
    "daily_up": 4,
    "daily_down": 5,
}
MOBILE_PRIMARY_COMPONENTS = {
    "left_eye_highlight_open",
    "right_eye_highlight_open",
}
MOBILE_REFLECTION_PAIRS = {
    "left_eye_highlight_open": "left_eye_sparkle_open",
    "right_eye_highlight_open": "right_eye_sparkle_open",
}
REACTION_CORE_COMPONENTS = {
    "left_brow_open",
    "right_brow_open",
    "mouth_default",
    "left_cheek_default",
    "right_cheek_default",
}
FORBIDDEN_HTML_TOKENS = (
    "v9-expression-rig-state-matrix.png",
    ".pbm",
    "pbm/",
    "matrix_",
    "story_",
)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def add_error(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def image_pixels(path: pathlib.Path) -> list[int]:
    return list(Image.open(path).convert("1").getdata())


def image_pixel_distance(left: pathlib.Path, right: pathlib.Path) -> int:
    with Image.open(left) as left_image, Image.open(right) as right_image:
        left_bits = left_image.convert("1")
        right_bits = right_image.convert("1")
        if left_bits.size != right_bits.size:
            raise ValueError(f"image size mismatch: {left}={left_bits.size} {right}={right_bits.size}")
        return pixel_distance(left_bits.getdata(), right_bits.getdata())


def source_eye_outline_clearance(eye_mask: pathlib.Path, primary_mask: pathlib.Path,
                                 sparkle_mask: pathlib.Path, offset: tuple[int, int]) -> int:
    def black_pixels(path: pathlib.Path) -> set[tuple[int, int]]:
        with Image.open(path) as image:
            bits = image.convert("1")
            return {(x, y) for y in range(bits.height) for x in range(bits.width)
                    if bits.getpixel((x, y)) == 0}

    eye_pixels = black_pixels(eye_mask)
    reflections = {(x + offset[0], y + offset[1])
                   for pixels in (black_pixels(primary_mask), black_pixels(sparkle_mask))
                   for x, y in pixels}
    if not reflections or not reflections <= eye_pixels:
        return -1
    outline = {(x, y) for x, y in eye_pixels if any((x + dx, y + dy) not in eye_pixels
                                                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    if not outline:
        return -1
    return min(abs(x - edge_x) + abs(y - edge_y)
               for x, y in reflections for edge_x, edge_y in outline)


def pixel_distance(left: Iterable[int], right: Iterable[int]) -> int:
    return sum(a != b for a, b in zip(left, right))


def gif_frame_count(path: pathlib.Path) -> int:
    with Image.open(path) as image:
        return sum(1 for _ in ImageSequence.Iterator(image))


def gif_frame_records(path: pathlib.Path) -> list[dict[str, object]]:
    with Image.open(path) as image:
        result: list[dict[str, object]] = []
        for frame in ImageSequence.Iterator(image):
            image_bits = frame.convert("1")
            result.append({
                "duration_ms": int(frame.info.get("duration", 0)),
                "pixels": image_bits.tobytes(),
                "size": image_bits.size,
            })
    return result


def component_layer_hashes(layer_dir: pathlib.Path) -> dict[str, str]:
    if not layer_dir.is_dir():
        raise ValueError(f"component layer directory is missing: {layer_dir}")
    return {path.stem: sha256(path) for path in sorted(layer_dir.glob("*.png"))}


def story_phase_frames(render_report: dict[str, object]) -> dict[str, dict[str, dict[str, object]]]:
    frames = render_report.get("frames")
    if not isinstance(frames, list):
        return {}
    result: dict[str, dict[str, dict[str, object]]] = {}
    for frame in frames:
        if not isinstance(frame, dict) or frame.get("kind") != "story":
            continue
        story = str(frame.get("story"))
        name = str(frame.get("name"))
        for phase in ("entry", "sustain", "settle"):
            if name.endswith(f"_{phase}"):
                result.setdefault(story, {})[phase] = frame
                break
    return result


def layout_offset_ranges() -> dict[str, tuple[tuple[int, int], tuple[int, int]]]:
    layout = load_json(LAYOUT)
    choreography = layout.get("preview_choreography")
    if not isinstance(choreography, dict) or \
            choreography.get("schema") != "companion.v9_expression_rig_performance_score.v2":
        raise ValueError("layout does not declare the reusable v2 component performance score")
    components = layout.get("components")
    if not isinstance(components, list):
        raise ValueError("layout has no component registry")
    ranges: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("layout component is not an object")
        name = str(component.get("name", ""))
        offset_range = component.get("offset_range")
        if not name or not isinstance(offset_range, dict):
            raise ValueError("layout component has no legal offset range")
        low = offset_range.get("min")
        high = offset_range.get("max")
        if not isinstance(low, list) or not isinstance(high, list) or len(low) != 2 or len(high) != 2 or \
                not all(isinstance(value, int) for value in low + high):
            raise ValueError(f"layout component {name} has invalid legal offset range")
        ranges[name] = ((int(low[0]), int(low[1])), (int(high[0]), int(high[1])))
    return ranges


def layout_duration_bounds() -> tuple[int, int]:
    layout = load_json(LAYOUT)
    choreography = layout.get("preview_choreography")
    if not isinstance(choreography, dict):
        raise ValueError("layout has no component performance score")
    bounds = choreography.get("step_duration_ms")
    if not isinstance(bounds, dict):
        raise ValueError("layout score has no duration bounds")
    low = bounds.get("min")
    high = bounds.get("max")
    if not isinstance(low, int) or not isinstance(high, int) or not 80 <= low <= high <= 5000:
        raise ValueError("layout score duration bounds are invalid")
    return low, high


def layer_offsets(frame: dict[str, object]) -> dict[str, tuple[int, int]]:
    layers = frame.get("layers")
    if not isinstance(layers, list):
        return {}
    result: dict[str, tuple[int, int]] = {}
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        component = str(layer.get("component", ""))
        offset = layer.get("offset")
        if component and isinstance(offset, list) and len(offset) == 2 and \
                all(isinstance(value, int) for value in offset):
            result[component] = (int(offset[0]), int(offset[1]))
    return result


def verify_daily_score_audit(preview: dict[str, object],
                             phases: dict[str, dict[str, dict[str, object]]],
                             errors: list[str]) -> None:
    choreography = preview.get("preview_choreography")
    add_error(errors, isinstance(choreography, dict) and
              choreography.get("schema") == "companion.v9_expression_rig_performance_score.v2",
              "daily preview is not driven by the reusable v2 component performance score")
    ranges = layout_offset_ranges()
    duration_min, duration_max = layout_duration_bounds()
    sequences = preview.get("story_sequences")
    sequence_items = sequences if isinstance(sequences, list) else []
    by_story = {str(item.get("story")): item for item in sequence_items if isinstance(item, dict)}
    for story in DAILY_REFLECTION_TARGETS:
        sequence = by_story.get(story, {})
        audit = sequence.get("frame_audit") if isinstance(sequence, dict) else None
        add_error(errors, isinstance(audit, list) and len(audit) >= 14,
                  f"{story} has no complete component-level score audit")
        if not isinstance(audit, list) or not audit:
            continue
        semantic_phases = tuple(str(frame.get("phase", "")) for frame in audit if isinstance(frame, dict))
        add_error(errors, semantic_phases[0:1] == ("entry",) and semantic_phases[-1:] == ("settle",) and
                  all(phase in semantic_phases for phase in SCORE_PHASES),
                  f"{story} omits a reusable score phase")
        entry_audit = audit[0] if isinstance(audit[0], dict) else {}
        settle_audit = audit[-1] if isinstance(audit[-1], dict) else {}
        entry_offsets = entry_audit.get("component_offsets") if isinstance(entry_audit, dict) else {}
        settle_offsets = settle_audit.get("component_offsets") if isinstance(settle_audit, dict) else {}
        add_error(errors, entry_offsets == settle_offsets,
                  f"{story} score does not return exactly to its component entry baseline")
        entry_components = layer_offsets(phases.get(story, {}).get("entry", {}))
        sustain_components = layer_offsets(phases.get(story, {}).get("sustain", {}))
        first_primary_motion: dict[str, int] = {}
        first_reaction_motion: dict[str, int] = {}
        first_charm_motion: int | None = None
        overlap_count = 0
        hold_offsets: dict[str, object] | None = None
        hold_index: int | None = None
        first_shared_rest: int | None = None
        positions: dict[str, list[tuple[int, int]]] = {
            component: [] for component in entry_components
        }
        for index, raw_frame in enumerate(audit):
            if not isinstance(raw_frame, dict):
                errors.append(f"{story} has a malformed score frame audit")
                continue
            duration = raw_frame.get("duration_ms")
            offsets = raw_frame.get("component_offsets")
            add_error(errors, isinstance(duration, int) and
                      duration_min <= duration <= duration_max,
                      f"{story} score frame {index} has an invalid duration")
            add_error(errors, isinstance(offsets, dict) and set(offsets) == set(entry_components),
                      f"{story} score frame {index} changes the registered component set")
            if not isinstance(offsets, dict):
                continue
            changed_primary = False
            changed_reaction = False
            for component, raw_offset in offsets.items():
                add_error(errors, component in ranges and isinstance(raw_offset, list) and len(raw_offset) == 2 and
                          all(isinstance(value, int) for value in raw_offset),
                          f"{story} score frame {index} has an invalid component pose")
                if component not in ranges or not isinstance(raw_offset, list) or len(raw_offset) != 2 or \
                        not all(isinstance(value, int) for value in raw_offset):
                    continue
                offset = (int(raw_offset[0]), int(raw_offset[1]))
                low, high = ranges[component]
                add_error(errors, low[0] <= offset[0] <= high[0] and low[1] <= offset[1] <= high[1],
                          f"{story} score frame {index} exceeds {component} legal offset range")
                if component in {"left_eye_open", "right_eye_open"}:
                    add_error(errors, offset == entry_components.get(component),
                              f"{story} moves eye body {component} instead of its internal highlight")
                if component == "nose_default":
                    add_error(errors, offset == entry_components.get(component),
                              f"{story} moves the fail-closed source nose anchor")
                positions.setdefault(component, []).append(offset)
                if component in MOBILE_PRIMARY_COMPONENTS and \
                        offset != entry_components.get(component):
                    changed_primary = True
                    first_primary_motion.setdefault(component, index)
                if component in REACTION_CORE_COMPONENTS and \
                        offset != entry_components.get(component):
                    changed_reaction = True
                    first_reaction_motion.setdefault(component, index)
                if component == "charm_star" and offset != entry_components.get(component) and \
                        first_charm_motion is None:
                    first_charm_motion = index
            for primary, sparkle in MOBILE_REFLECTION_PAIRS.items():
                primary_offset = offsets.get(primary)
                sparkle_offset = offsets.get(sparkle)
                add_error(errors, primary_offset == sparkle_offset,
                          f"{story} score frame {index} splits paired reflection {primary}/{sparkle}")
                if isinstance(primary_offset, list) and len(primary_offset) == 2 and \
                        all(isinstance(value, int) for value in primary_offset):
                    add_error(errors, (int(primary_offset[0]), int(primary_offset[1])) in
                              DAILY_REFLECTION_CORRIDORS[story],
                              f"{story} score frame {index} leaves its dynamic-rest reflection corridor")
            if first_shared_rest is None and all(
                    offsets.get(primary) == list(DAILY_REFLECTION_REST)
                    for primary in MOBILE_PRIMARY_COMPONENTS):
                first_shared_rest = index
            if changed_primary and changed_reaction:
                overlap_count += 1
            if raw_frame.get("phase") == "hold":
                hold_offsets = offsets
                hold_index = index
        add_error(errors, set(first_primary_motion) == MOBILE_PRIMARY_COMPONENTS,
                  f"{story} does not animate exactly one registered primary reflection per eye")
        add_error(errors, len(set(first_primary_motion.values())) == 2,
                  f"{story} does not stagger the two primary-reflection pickups")
        add_error(errors, set(first_reaction_motion) == REACTION_CORE_COMPONENTS and
                  len(set(first_reaction_motion.values())) == 1,
                  f"{story} does not start brows, mouth and both cheeks as one facial response")
        reaction_onset = next(iter(first_reaction_motion.values()), None)
        add_error(errors, reaction_onset is not None and first_charm_motion is not None and
                  reaction_onset < first_charm_motion,
                  f"{story} charm accent does not follow the coordinated facial response")
        add_error(errors, overlap_count >= 2,
                  f"{story} has too little component overlap for a living Daily performance")
        add_error(errors, hold_offsets == {component: list(offset) for component, offset in sustain_components.items()},
                  f"{story} score hold does not match the deterministic Rig sustain plan")
        if isinstance(hold_offsets, dict) and hold_index is not None:
            primary_arrivals: list[int] = []
            for primary in MOBILE_PRIMARY_COMPONENTS:
                primary_positions = positions.get(primary, [])
                target = hold_offsets.get(primary)
                if isinstance(target, list) and len(target) == 2 and primary_positions:
                    target_pair = (int(target[0]), int(target[1]))
                    arrival = next((index for index, offset in enumerate(primary_positions)
                                    if index >= (first_shared_rest or 0) and offset == target_pair), None)
                    add_error(errors, arrival is not None,
                              f"{story} primary reflection never reaches its registered hold pose")
                    if arrival is not None:
                        primary_arrivals.append(arrival)
                    add_error(errors, all(offset in DAILY_REFLECTION_CORRIDORS[story]
                                          for offset in primary_positions) and
                              all(abs(current[0] - previous[0]) <= 1 and
                                  abs(current[1] - previous[1]) <= 1
                                  for previous, current in zip(primary_positions, primary_positions[1:])),
                              f"{story} primary reflection does not follow its one-pixel dynamic-rest route")
            add_error(errors, first_shared_rest is not None and
                      (reaction_onset is None or first_shared_rest < reaction_onset),
                      f"{story} facial response begins before both reflections reach dynamic rest")
            add_error(errors, reaction_onset is not None and len(primary_arrivals) == 2 and
                      reaction_onset > max(primary_arrivals),
                      f"{story} facial response begins before both primary reflections arrive")
            add_error(errors, hold_offsets.get("nose_default") == list(entry_components.get("nose_default", ())),
                      f"{story} nose hold is not at its fail-closed V9 anchor")
            for primary in MOBILE_PRIMARY_COMPONENTS:
                offset = hold_offsets.get(primary)
                add_error(errors, isinstance(offset, list) and len(offset) == 2 and
                          (int(offset[0]), int(offset[1])) == DAILY_REFLECTION_TARGETS[story],
                          f"{story} primary reflection hold misses its calibrated eye-clearance target")


def compare_accepted_dynamic_baseline(accepted_baseline_path: pathlib.Path | None,
                                      preview: dict[str, object],
                                      render: dict[str, object],
                                      errors: list[str]) -> dict[str, object]:
    if accepted_baseline_path is None:
        return {
            "status": "not_configured",
            "comparison_required": False,
            "reason": "accepted dynamic baseline comparison was explicitly skipped",
        }

    baseline_path = accepted_baseline_path.resolve()
    if not baseline_path.exists():
        return {
            "status": "not_yet_accepted",
            "comparison_required": False,
            "path": rel(baseline_path),
            "reason": "no canonical owner PASS has promoted a dynamic preview baseline yet",
        }

    baseline = load_json(baseline_path)
    baseline_errors: list[str] = []

    def add_baseline_error(condition: bool, message: str) -> None:
        if not condition:
            baseline_errors.append(message)
            errors.append(message)

    add_baseline_error(baseline.get("schema") == "companion.v9_expression_rig_accepted_dynamic_baseline.v1",
                       "unexpected accepted dynamic baseline schema")
    add_baseline_error(baseline.get("status") == "ACCEPTED_DYNAMIC_BASELINE",
                       "accepted dynamic baseline is not marked ACCEPTED_DYNAMIC_BASELINE")
    add_baseline_error(baseline.get("source_sha256") == LOCKED_SOURCE_HASH,
                       "accepted dynamic baseline source hash is not the locked v9 source")
    add_baseline_error(preview.get("source_sha256") == baseline.get("source_sha256") and
                       render.get("source_sha256") == baseline.get("source_sha256"),
                       "current preview/render source hash differs from accepted dynamic baseline")
    add_baseline_error(baseline.get("runtime_resource_activated") is False,
                       "accepted dynamic baseline must remain runtime inactive")

    baseline_group_items = baseline.get("dynamic_groups")
    preview_group_items = preview.get("dynamic_groups")
    baseline_groups = sorted(str(item) for item in baseline_group_items) if isinstance(baseline_group_items, list) else []
    preview_groups = sorted(str(item) for item in preview_group_items) if isinstance(preview_group_items, list) else []
    add_baseline_error(preview_groups == baseline_groups,
                       "current dynamic groups differ from accepted dynamic baseline")

    baseline_story_items = baseline.get("stories")
    preview_story_items = preview.get("stories")
    baseline_stories = sorted(str(item) for item in baseline_story_items) if isinstance(baseline_story_items, list) else []
    preview_stories = sorted(str(item) for item in preview_story_items) if isinstance(preview_story_items, list) else []
    add_baseline_error(preview_stories == baseline_stories,
                       "current story list differs from accepted dynamic baseline")
    add_baseline_error(preview.get("component_layer_count") == baseline.get("component_layer_count"),
                       "current component layer count differs from accepted dynamic baseline")

    artifact_distances: list[dict[str, object]] = []
    artifacts = baseline.get("artifacts") if isinstance(baseline.get("artifacts"), dict) else {}

    keyframe_artifact = artifacts.get("keyframe_strip") if isinstance(artifacts.get("keyframe_strip"), dict) else {}
    keyframe_baseline_path = ROOT / str(keyframe_artifact.get("path", ""))
    keyframe_current_path = ROOT / str(preview.get("keyframe_strip", ""))
    if keyframe_baseline_path.is_file() and keyframe_current_path.is_file():
        keyframe_distance = image_pixel_distance(keyframe_current_path, keyframe_baseline_path)
        artifact_distances.append({
            "artifact": "keyframe_strip",
            "pixels": keyframe_distance,
            "max_allowed_pixels": MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS,
        })
        add_baseline_error(keyframe_distance <= MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS,
                           "current keyframe strip drifted from accepted dynamic baseline")
    else:
        add_baseline_error(False, "missing keyframe strip for accepted dynamic baseline comparison")

    baseline_component_items = baseline.get("component_layers")
    baseline_components: dict[str, str] = {}
    if isinstance(baseline_component_items, list):
        for item in baseline_component_items:
            if not isinstance(item, dict):
                add_baseline_error(False, "accepted dynamic baseline component layer is not an object")
                continue
            name = item.get("component")
            component_hash = item.get("sha256")
            if not isinstance(name, str) or not isinstance(component_hash, str) or len(component_hash) != 64:
                add_baseline_error(False, "accepted dynamic baseline component layer is incomplete")
                continue
            baseline_components[name] = component_hash
    else:
        add_baseline_error(False, "accepted dynamic baseline has no component layer hashes")
    current_layer_dir = ROOT / str(preview.get("component_layer_dir", ""))
    current_components = component_layer_hashes(current_layer_dir) if current_layer_dir.is_dir() else {}
    add_baseline_error(bool(current_components), "current preview component layer directory is missing or empty")
    add_baseline_error(set(current_components) == set(baseline_components),
                       "current component layer set differs from accepted dynamic baseline")
    component_mismatches = sorted(
        name for name in set(current_components) | set(baseline_components)
        if current_components.get(name) != baseline_components.get(name)
    )
    add_baseline_error(not component_mismatches,
                       "current component mask bytes differ from accepted dynamic baseline")

    animated_artifact = artifacts.get("animated_preview") if isinstance(artifacts.get("animated_preview"), dict) else {}
    baseline_gif_path = ROOT / str(animated_artifact.get("path", ""))
    current_gif_path = ROOT / str(preview.get("animated_preview", ""))
    gif_comparison: dict[str, object] = {
        "baseline_path": rel(baseline_gif_path) if baseline_gif_path.is_file() else None,
        "current_path": rel(current_gif_path) if current_gif_path.is_file() else None,
    }
    if baseline_gif_path.is_file() and current_gif_path.is_file():
        baseline_gif_frames = gif_frame_records(baseline_gif_path)
        current_gif_frames = gif_frame_records(current_gif_path)
        frame_count_matches = len(baseline_gif_frames) == len(current_gif_frames)
        gif_comparison["baseline_frame_count"] = len(baseline_gif_frames)
        gif_comparison["current_frame_count"] = len(current_gif_frames)
        gif_comparison["frame_count_matches"] = frame_count_matches
        add_baseline_error(frame_count_matches,
                           "current animated preview frame count differs from accepted dynamic baseline")
        per_frame_pixels: list[dict[str, object]] = []
        mismatched_pixels = 0
        for index, (baseline_frame, current_frame) in enumerate(zip(baseline_gif_frames, current_gif_frames)):
            sizes_match = baseline_frame["size"] == current_frame["size"]
            add_baseline_error(sizes_match,
                               f"animated preview frame {index} size differs from accepted dynamic baseline")
            pixels = pixel_distance(baseline_frame["pixels"], current_frame["pixels"]) if sizes_match else -1
            per_frame_pixels.append({
                "index": index,
                "pixels": pixels,
                "baseline_duration_ms": baseline_frame["duration_ms"],
                "current_duration_ms": current_frame["duration_ms"],
            })
            if pixels > 0:
                mismatched_pixels += pixels
        add_baseline_error(mismatched_pixels == 0,
                           "current animated preview pixels differ from accepted dynamic baseline")
        duration_matches = frame_count_matches and all(
            item["baseline_duration_ms"] == item["current_duration_ms"] for item in per_frame_pixels
        )
        current_durations = [int(item["current_duration_ms"]) for item in per_frame_pixels]
        gif_comparison.update({
            "per_frame_pixels": per_frame_pixels,
            "mismatched_pixels": mismatched_pixels,
            "max_allowed_pixels": MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS,
            "duration_matches_historical_preview": duration_matches,
            "current_min_duration_ms": min(current_durations) if current_durations else None,
            "current_panel_paced": bool(current_durations) and min(current_durations) >= 650,
        })
        add_baseline_error(gif_comparison["current_panel_paced"],
                           "current animated preview does not meet the minimum panel pacing dwell")
    else:
        add_baseline_error(False, "missing animated preview for accepted dynamic baseline comparison")

    current_phases = story_phase_frames(render)
    baseline_phase_items = baseline.get("story_phase_frames")
    add_baseline_error(isinstance(baseline_phase_items, list) and bool(baseline_phase_items),
                       "accepted dynamic baseline has no story phase frames")
    phase_distances: list[dict[str, object]] = []
    baseline_phase_keys: set[tuple[str, str]] = set()
    if isinstance(baseline_phase_items, list):
        for item in baseline_phase_items:
            if not isinstance(item, dict):
                add_baseline_error(False, "accepted dynamic baseline story phase record is not an object")
                continue
            story = str(item.get("story"))
            phase = str(item.get("phase"))
            baseline_phase_keys.add((story, phase))
            current = current_phases.get(story, {}).get(phase)
            if current is None:
                add_baseline_error(False, f"missing current story phase from accepted baseline: {story}/{phase}")
                continue
            current_path = ROOT / str(current.get("path", ""))
            baseline_phase_path = ROOT / str(item.get("path", ""))
            if not current_path.is_file() or not baseline_phase_path.is_file():
                add_baseline_error(False, f"missing PBM artifact for accepted baseline comparison: {story}/{phase}")
                continue
            distance = image_pixel_distance(current_path, baseline_phase_path)
            phase_distances.append({
                "story": story,
                "phase": phase,
                "pixels": distance,
                "max_allowed_pixels": MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS,
            })
            add_baseline_error(current.get("sha256") == item.get("sha256"),
                               f"{story}/{phase} hash differs from accepted dynamic baseline")
            add_baseline_error(distance <= MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS,
                               f"{story}/{phase} pixel distance differs from accepted dynamic baseline")

    current_phase_keys = {
        (story, phase)
        for story, phases in current_phases.items()
        for phase in phases
        if story in preview_stories
    }
    add_baseline_error(current_phase_keys == baseline_phase_keys,
                       "current story phase set differs from accepted dynamic baseline")

    return {
        "status": "PASS_ACCEPTED_DYNAMIC_BASELINE_MATCH" if not baseline_errors
        else "FAIL_ACCEPTED_DYNAMIC_BASELINE_DRIFT",
        "comparison_required": True,
        "path": rel(baseline_path),
        "max_allowed_pixel_distance": MAX_ACCEPTED_BASELINE_DISTANCE_PIXELS,
        "artifact_distances": artifact_distances,
        "component_layer_comparison": {
            "baseline_count": len(baseline_components),
            "current_count": len(current_components),
            "mismatched_components": component_mismatches,
        },
        "animated_preview_comparison": gif_comparison,
        "nonvisual_artifact_byte_variance": {
            "review_page_hash_matches_historical": preview.get("review_page_sha256") ==
            (artifacts.get("review_page", {}) if isinstance(artifacts.get("review_page"), dict) else {}).get("sha256"),
            "owner_review_page_hash_matches_historical": preview.get("owner_review_page_sha256") ==
            (artifacts.get("owner_review_page", {}) if isinstance(artifacts.get("owner_review_page"), dict) else {}).get("sha256"),
            "animated_preview_hash_matches_historical": preview.get("animated_preview_sha256") ==
            animated_artifact.get("sha256"),
        },
        "story_phase_distances": phase_distances,
        "errors": baseline_errors,
    }


def verify(preview_report_path: pathlib.Path,
           render_report_path: pathlib.Path,
           accepted_baseline_path: pathlib.Path | None = DEFAULT_ACCEPTED_BASELINE) -> dict[str, object]:
    errors: list[str] = []
    preview = load_json(preview_report_path)
    render = load_json(render_report_path)

    add_error(errors, preview.get("schema") == "companion.v9_expression_rig_dynamic_preview.v1",
              "unexpected dynamic preview schema")
    add_error(errors, preview.get("status") == "PASS_DYNAMIC_COMPONENT_PREVIEW_READY",
              "dynamic preview is not ready")
    add_error(errors, render.get("schema") == "companion.v9_expression_rig_render.v1",
              "unexpected Rig render schema")
    add_error(errors, render.get("status") == "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW",
              "Rig render is not PASS pending review")
    add_error(errors, preview.get("source_sha256") == LOCKED_SOURCE_HASH and
              render.get("source_sha256") == LOCKED_SOURCE_HASH,
              "preview or render source hash drifted from locked v9")
    add_error(errors, preview.get("runtime_resource_activated") is False and
              render.get("runtime_resource_activated") is False,
              "candidate preview/render must remain runtime inactive")
    add_error(errors, preview.get("human_prompt_launched") is False,
              "preview-distance gate must run before the owner prompt")

    scope = str(preview.get("preview_scope", "full_library"))
    add_error(errors, scope in {"full_library", "daily_focus", "daily_selected_state"},
              "dynamic preview has an unsupported scope")
    required_groups = DAILY_FOCUS_GROUPS if scope in DAILY_PREVIEW_SCOPES else REQUIRED_DYNAMIC_GROUPS
    required_stories = DAILY_FOCUS_STORIES if scope in DAILY_PREVIEW_SCOPES else REQUIRED_DYNAMIC_STORIES
    groups = set(preview.get("dynamic_groups") if isinstance(preview.get("dynamic_groups"), list) else [])
    missing_groups = sorted(required_groups - groups)
    add_error(errors, not missing_groups, f"dynamic preview missing groups: {', '.join(missing_groups)}")
    if scope in DAILY_PREVIEW_SCOPES:
        side_detail = preview.get("side_detail_strokes")
        add_error(errors, isinstance(side_detail, dict) and
                  side_detail.get("status") == "fail_closed_not_in_daily_scope",
                  "daily focus must report source detail strokes as fail-closed")
    if scope == "daily_selected_state":
        choreography = preview.get("preview_choreography")
        add_error(errors, isinstance(choreography, dict) and
                  choreography.get("presentation_mode") == "state_bound_single_story_loop" and
                  choreography.get("automatic_story_rotation") is False,
                  "selected Daily preview must hold one state instead of rotating stories")
        add_error(errors, preview.get("playback_story_order") == ["daily_right"],
                  "selected Daily preview must replay only its selected right-gaze track")
    add_error(errors, preview.get("animation_source") == "component_png_layers_from_crig_masks",
              "dynamic preview is not declared as component-layer animation")
    forbidden_sources = set(preview.get("forbidden_animation_sources")
                            if isinstance(preview.get("forbidden_animation_sources"), list) else [])
    add_error(errors, "whole-face PBM flipbook" in forbidden_sources,
              "preview report does not forbid whole-face PBM flipbooks")

    review_page = ROOT / str(preview.get("review_page", ""))
    owner_review_page = ROOT / str(preview.get("owner_review_page", ""))
    animated_preview = ROOT / str(preview.get("animated_preview", ""))
    keyframe_strip = ROOT / str(preview.get("keyframe_strip", ""))
    layer_dir = ROOT / str(preview.get("component_layer_dir", ""))
    for label, path in (
        ("review page", review_page),
        ("owner review page", owner_review_page),
        ("animated preview", animated_preview),
        ("keyframe strip", keyframe_strip),
        ("component layer dir", layer_dir),
    ):
        add_error(errors, path.exists(), f"missing {label}: {path}")
    if review_page.is_file():
        add_error(errors, preview.get("review_page_sha256") == sha256(review_page),
                  "review page SHA-256 drifted from preview report")
    if owner_review_page.is_file():
        add_error(errors, preview.get("owner_review_page_sha256") == sha256(owner_review_page),
                  "owner review page SHA-256 drifted from preview report")
    if animated_preview.is_file():
        add_error(errors, preview.get("animated_preview_sha256") == sha256(animated_preview),
                  "animated preview SHA-256 drifted from preview report")
    if keyframe_strip.is_file():
        add_error(errors, preview.get("keyframe_strip_sha256") == sha256(keyframe_strip),
                  "keyframe strip SHA-256 drifted from preview report")

    if review_page.is_file():
        html = review_page.read_text(encoding="utf-8")
        layer_reference = layer_dir.relative_to(review_page.parent).as_posix() + "/" \
            if layer_dir.is_relative_to(review_page.parent) else ""
        add_error(errors, bool(layer_reference) and layer_reference in html,
                  "review page does not reference component layer images")
        for token in FORBIDDEN_HTML_TOKENS:
            add_error(errors, token not in html,
                      f"review page references forbidden full-frame token: {token}")
        add_error(errors, html.count(layer_reference) >= int(preview.get("component_layer_count", 0)),
                  "review page does not include the recorded component layer count")
        add_error(errors, "id=\"eyeAudit\"" in html and "function renderEyeAudit" in html and
                  "primary motion ' + (primary ? primary.offset.join(',')" in html and
                  "sparkle motion ' + (sparkle ? sparkle.offset.join(',')" in html,
                  "review page lacks the magnified paired-eye-reflection audit")
    if owner_review_page.is_file() and review_page.is_file():
        add_error(errors, owner_review_page.read_bytes() == review_page.read_bytes(),
                  "owner review page differs from the dynamic player")
    if animated_preview.is_file():
        minimum_gif_frames = 14 if scope in DAILY_PREVIEW_SCOPES else 20
        add_error(errors, gif_frame_count(animated_preview) >= minimum_gif_frames,
                  "animated preview GIF has too few frames for a dynamic Rig preview")
    if keyframe_strip.is_file():
        with Image.open(keyframe_strip) as image:
            add_error(errors, image.size[0] >= 900 and image.size[1] >= 600,
                      "keyframe strip is too small to review component motion")
    if layer_dir.is_dir():
        layers = sorted(layer_dir.glob("*.png"))
        add_error(errors, len(layers) == int(preview.get("component_layer_count", -1)),
                  "component layer PNG count does not match preview report")
        for path in layers:
            add_error(errors, path.stat().st_size > 0, f"empty component layer: {rel(path)}")

    stories = preview.get("stories")
    preview_stories = set(stories if isinstance(stories, list) else [])
    missing_stories = sorted(required_stories - preview_stories)
    add_error(errors, not missing_stories, f"dynamic preview missing expression stories: {', '.join(missing_stories)}")
    if scope in DAILY_PREVIEW_SCOPES:
        add_error(errors, preview_stories == DAILY_FOCUS_STORIES,
                  "daily focus preview must contain only the four daily gaze stories")
        sequences = preview.get("story_sequences")
        sequence_items = sequences if isinstance(sequences, list) else []
        by_story = {str(item.get("story")): item for item in sequence_items if isinstance(item, dict)}
        add_error(errors, set(by_story) == DAILY_FOCUS_STORIES,
                  "daily focus preview is missing versioned daily story sequence evidence")
        beat_signatures: set[tuple[str, ...]] = set()
        for story in sorted(DAILY_FOCUS_STORIES):
            sequence = by_story.get(story, {})
            beats = sequence.get("beats") if isinstance(sequence, dict) else None
            beat_tuple = tuple(str(beat) for beat in beats) if isinstance(beats, list) else ()
            add_error(errors, len(beat_tuple) >= 5 and len(beat_tuple) == len(set(beat_tuple)),
                      f"{story} does not have a complete ordered daily component sequence")
            beat_signatures.add(beat_tuple)
            minimum_intermediate_frames = (MIN_DAILY_INTERMEDIATE_FRAMES - 2
                                           if story in {"daily_left", "daily_up"}
                                           else MIN_DAILY_INTERMEDIATE_FRAMES)
            add_error(errors, int(sequence.get("intermediate_frames_before_sustain", 0)) >=
                      minimum_intermediate_frames,
                      f"{story} has too few daily lead/arrive frames")
            add_error(errors, int(sequence.get("release_frames_before_settle", 0)) >=
                      MIN_DAILY_RELEASE_FRAMES,
                      f"{story} has too few daily release frames")
            add_error(errors, int(sequence.get("visible_step_count", 0)) >= MIN_DAILY_VISIBLE_STEPS,
                      f"{story} does not show enough visible component motion steps")
        add_error(errors, len(beat_signatures) == len(DAILY_FOCUS_STORIES),
                  "daily gaze stories regressed to one shared beat order")
    phases = story_phase_frames(render)
    if scope in DAILY_PREVIEW_SCOPES:
        verify_daily_score_audit(preview, phases, errors)
    component_records = render.get("components")
    components_by_role: dict[str, list[dict[str, object]]] = {}
    components_by_name: dict[str, dict[str, object]] = {}
    if isinstance(component_records, list):
        for component in component_records:
            if isinstance(component, dict):
                components_by_role.setdefault(str(component.get("role")), []).append(component)
                components_by_name[str(component.get("name"))] = component
    for side in ("left", "right"):
        eye = [item for item in components_by_role.get(f"{side}_eye", [])
               if item.get("variant") == "open"]
        primary = [item for item in components_by_role.get(f"{side}_highlight", [])
                   if item.get("variant") == "open"]
        sparkle = [item for item in components_by_role.get(f"{side}_sparkle", [])
                   if item.get("variant") == "open"]
        add_error(errors, len(eye) == 1 and eye[0].get("composite_op") == "ink" and
                  eye[0].get("extraction") == "eye_body_fill_enclosed_white",
                  f"{side} open eye body is not source-derived ink geometry")
        add_error(errors, len(primary) == 1 and primary[0].get("composite_op") == "erase" and
                  primary[0].get("extraction") == "eye_highlight_primary_enclosed_white",
                  f"{side} open primary reflection is not source-derived erase geometry")
        add_error(errors, len(sparkle) == 1 and sparkle[0].get("composite_op") == "erase" and
                  sparkle[0].get("extraction") == "eye_highlight_sparkle_enclosed_white",
                  f"{side} open sparkle is not independently source-derived erase geometry")
    matrix = render.get("state_matrix")
    frame_hashes = matrix.get("frame_hashes") if isinstance(matrix, dict) else {}
    baseline_hash = frame_hashes.get("daily_calm_center") if isinstance(frame_hashes, dict) else None
    add_error(errors, isinstance(baseline_hash, str) and len(baseline_hash) == 64,
              "missing daily_calm_center baseline hash")

    distance_records: list[dict[str, object]] = []
    for story in sorted(preview_stories):
        story_phases = phases.get(story)
        if not story_phases or any(phase not in story_phases for phase in ("entry", "sustain", "settle")):
            errors.append(f"missing render phases for preview story: {story}")
            continue
        entry = story_phases["entry"]
        sustain = story_phases["sustain"]
        settle = story_phases["settle"]
        entry_path = ROOT / str(entry.get("path", ""))
        sustain_path = ROOT / str(sustain.get("path", ""))
        settle_path = ROOT / str(settle.get("path", ""))
        if not entry_path.is_file() or not sustain_path.is_file() or not settle_path.is_file():
            errors.append(f"missing PBM distance artifacts for story: {story}")
            continue
        entry_pixels = image_pixels(entry_path)
        sustain_pixels = image_pixels(sustain_path)
        settle_pixels = image_pixels(settle_path)
        entry_to_sustain = pixel_distance(entry_pixels, sustain_pixels)
        entry_to_settle = pixel_distance(entry_pixels, settle_pixels)
        add_error(errors, entry.get("sha256") == baseline_hash,
                  f"{story} entry does not match the accepted v9 calm baseline")
        minimum_visible_distance = MIN_CALIBRATED_DAILY_VISIBLE_DISTANCE_PIXELS
        add_error(errors, entry_to_sustain >= minimum_visible_distance,
                  f"{story} sustain distance is too small to read as dynamic")
        add_error(errors, entry_to_sustain <= MAX_WHOLE_FACE_DISTANCE_PIXELS,
                  f"{story} sustain distance is too large and may be a whole-face replacement")
        add_error(errors, entry_to_settle <= max(1, entry_to_sustain // 4),
                  f"{story} settle does not return near entry")
        roles = sorted({str(layer.get("role")) for layer in sustain.get("layers", [])
                        if isinstance(layer, dict)})
        outline_clearances: dict[str, int] = {}
        if scope in DAILY_PREVIEW_SCOPES:
            component_offsets = layer_offsets(sustain)
            eye_offsets = {str(layer.get("role")): tuple(layer.get("offset", []))
                           for layer in sustain.get("layers", []) if isinstance(layer, dict) and
                           str(layer.get("role")) in {"left_eye", "right_eye", "left_highlight", "right_highlight",
                                                        "left_sparkle", "right_sparkle", "nose"}}
            add_error(errors, eye_offsets.get("left_eye") == (0, 0) and
                      eye_offsets.get("right_eye") == (0, 0),
                      f"{story} moves an entire eye body instead of holding the daily V9 eye anchor")
            add_error(errors, all(eye_offsets.get(role) != (0, 0) for role in
                                   ("left_highlight", "right_highlight")),
                      f"{story} does not move both source-derived primary reflections")
            add_error(errors, eye_offsets.get("left_highlight") == eye_offsets.get("left_sparkle") and
                      eye_offsets.get("right_highlight") == eye_offsets.get("right_sparkle"),
                      f"{story} splits a source-derived paired eye reflection")
            add_error(errors, eye_offsets.get("nose") == (0, 0),
                      f"{story} moves the fail-closed source nose anchor")
            for side in ("left", "right"):
                names = (f"{side}_eye_open", f"{side}_eye_highlight_open", f"{side}_eye_sparkle_open")
                records = [components_by_name.get(name) for name in names]
                mask_paths = [ROOT / str(record.get("component_mask", ""))
                              for record in records if isinstance(record, dict)]
                offset = component_offsets.get(f"{side}_eye_highlight_open")
                if len(mask_paths) != 3 or not all(path.is_file() for path in mask_paths) or offset is None:
                    errors.append(f"{story} lacks source masks for {side} eye-clearance verification")
                    continue
                clearance = source_eye_outline_clearance(mask_paths[0], mask_paths[1], mask_paths[2], offset)
                outline_clearances[side] = clearance
                add_error(errors, clearance >= DAILY_MIN_OUTLINE_CLEARANCE_PIXELS[story],
                          f"{story} {side} paired reflection approaches the fixed eye outline")
        if story == "swipe_left":
            add_error(errors, "left_detail" in roles and "right_detail" not in roles,
                      "swipe_left must use only left source-derived detail strokes")
        if story == "swipe_right":
            add_error(errors, "right_detail" in roles and "left_detail" not in roles,
                      "swipe_right must use only right source-derived detail strokes")
        distance_records.append({
            "story": story,
            "entry_to_sustain_pixels": entry_to_sustain,
            "entry_to_settle_pixels": entry_to_settle,
            "minimum_visible_distance_pixels": minimum_visible_distance,
            "source_eye_outline_clearance_pixels": outline_clearances,
            "minimum_source_eye_outline_clearance_pixels": (
                DAILY_MIN_OUTLINE_CLEARANCE_PIXELS.get(story) if scope in DAILY_PREVIEW_SCOPES else None
            ),
            "sustain_layer_count": len(sustain.get("layers", [])) if isinstance(sustain.get("layers"), list) else 0,
            "sustain_roles": roles,
        })

    add_error(errors, len(distance_records) >= len(required_stories),
              "preview distance gate covered too few expression stories")
    accepted_dynamic_baseline = compare_accepted_dynamic_baseline(accepted_baseline_path, preview, render, errors)
    return {
        "schema": "companion.v9_expression_rig_preview_distance.v1",
        "status": "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT" if not errors else "FAIL",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "preview_scope": scope,
        "preview_report": rel(preview_report_path),
        "render_report": rel(render_report_path),
        "min_calibrated_daily_visible_distance_pixels": MIN_CALIBRATED_DAILY_VISIBLE_DISTANCE_PIXELS,
        "max_whole_face_distance_pixels": MAX_WHOLE_FACE_DISTANCE_PIXELS,
        "dynamic_groups": sorted(groups),
        "distance_records": distance_records,
        "accepted_dynamic_baseline": accepted_dynamic_baseline,
        "forbidden_html_tokens": list(FORBIDDEN_HTML_TOKENS),
        "human_prompt_launched": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-report", type=pathlib.Path, default=DEFAULT_PREVIEW_REPORT)
    parser.add_argument("--render-report", type=pathlib.Path, default=DEFAULT_RENDER_REPORT)
    parser.add_argument("--accepted-baseline", type=pathlib.Path, default=DEFAULT_ACCEPTED_BASELINE)
    parser.add_argument("--skip-accepted-baseline", action="store_true")
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    try:
        accepted_baseline = None if args.skip_accepted_baseline else args.accepted_baseline.resolve()
        result = verify(args.preview_report.resolve(), args.render_report.resolve(), accepted_baseline)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if result["status"] != "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: v9 dynamic preview is component-layered and stays near the accepted identity baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
