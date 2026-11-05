#!/usr/bin/env python3
"""Verify component-only, state-bound previews for the remaining registered v9 stories."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image, ImageSequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
SCORE = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/state-preview-rig-score-v1.json"
DEFAULT_PREVIEW = ROOT / "docs/validation/companion-v9-expression-rig-registered-states-preview-20260718.json"
DEFAULT_RENDER = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-rig-registered-states-machine-20260718.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_ACCEPTANCE_HASH = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
EXPECTED_STORIES = (
    "touch_left", "touch_right", "swipe_left", "swipe_right", "swipe_down",
    "recording_focus", "menu_focus", "sleep_enter",
)
PHASES = ("entry", "prepare", "lead", "response", "accent", "hold", "release", "return", "settle")
REQUIRED_GROUPS = {
    "eyes/highlights", "brows", "nose-mouth/lips", "cheeks", "side detail strokes", "small charm",
}
MIN_VISIBLE_STEPS = 8
MIN_MAX_STEP_PIXELS = 650
MAX_MAX_STEP_PIXELS = 6500


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def layer_signature(layers: object) -> tuple[tuple[object, ...], ...]:
    result: list[tuple[object, ...]] = []
    if not isinstance(layers, list):
        return ()
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        offset = layer.get("offset")
        result.append((str(layer.get("component", "")), str(layer.get("role", "")),
                       tuple(offset) if isinstance(offset, list) else (),
                       str(layer.get("source_frame", "")), str(layer.get("composite_op", ""))))
    return tuple(sorted(result))


def story_phases(render: dict[str, object]) -> dict[str, dict[str, dict[str, object]]]:
    result: dict[str, dict[str, dict[str, object]]] = {}
    frames = render.get("frames")
    if not isinstance(frames, list):
        return result
    for frame in frames:
        if not isinstance(frame, dict) or frame.get("kind") != "story":
            continue
        name = str(frame.get("name", ""))
        for phase in ("entry", "sustain", "settle"):
            if name.endswith(f"_{phase}"):
                result.setdefault(str(frame.get("story", "")), {})[phase] = frame
                break
    return result


def verify(preview_path: pathlib.Path, render_path: pathlib.Path) -> dict[str, object]:
    errors: list[str] = []
    preview = load_json(preview_path)
    render = load_json(render_path)
    layout = load_json(LAYOUT)
    score = load_json(SCORE)

    add(errors, preview.get("schema") == "companion.v9_expression_rig_dynamic_preview.v1" and
        preview.get("status") == "PASS_DYNAMIC_COMPONENT_PREVIEW_READY",
        "registered-state preview report is not machine-ready")
    add(errors, preview.get("preview_scope") == "registered_states",
        "preview did not use the registered-state scope")
    add(errors, preview.get("source_sha256") == LOCKED_SOURCE_HASH and
        render.get("source_sha256") == LOCKED_SOURCE_HASH and
        score.get("source_sha256") == LOCKED_SOURCE_HASH,
        "locked v9 source hash drifted")
    add(errors, preview.get("runtime_resource_activated") is False and
        render.get("runtime_resource_activated") is False and
        score.get("runtime_resource_activated") is False,
        "registered-state preview activated a candidate runtime resource")
    add(errors, tuple(preview.get("stories", [])) == EXPECTED_STORIES,
        "preview does not cover exactly the remaining registered stories in order")
    add(errors, set(preview.get("dynamic_groups", [])) == REQUIRED_GROUPS,
        "registered-state preview does not animate every registered component group")
    add(errors, preview.get("animation_source") == "component_png_layers_from_crig_masks",
        "preview is not declared as component-mask composition")
    forbidden = set(preview.get("forbidden_animation_sources", []))
    add(errors, {"whole-face PBM flipbook", "legacy art", "code-drawn face", "custom LUT"}.issubset(forbidden),
        "preview does not prohibit all forbidden animation sources")
    add(errors, preview.get("charging_error") == "fail_closed_no_registered_components",
        "charging/error is not fail-closed")

    choreography = preview.get("preview_choreography")
    add(errors, isinstance(choreography, dict) and
        choreography.get("schema") == score.get("schema") and
        choreography.get("source") == rel(SCORE) and
        choreography.get("source_sha256") == sha256(SCORE) and
        choreography.get("source_layout") == rel(LAYOUT) and
        choreography.get("source_layout_revision") == layout.get("revision") and
        choreography.get("presentation_mode") == "state_bound_single_story_loop" and
        choreography.get("automatic_story_rotation") is False,
        "preview is not bound to the versioned state score or still rotates stories automatically")
    fail_closed = score.get("fail_closed_events")
    fail_closed_map = {
        str(item.get("event")): str(item.get("status")) for item in fail_closed
        if isinstance(fail_closed, list) and isinstance(item, dict)
    }
    add(errors, fail_closed_map == {
        "charging": "fail_closed_no_registered_components",
        "error": "fail_closed_no_registered_components",
    }, "state score does not fail closed for charging/error")

    components = render.get("components")
    component_records = {
        str(component.get("name")): component for component in components
        if isinstance(components, list) and isinstance(component, dict)
    }
    layout_components = layout.get("components")
    ranges: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}
    roles: set[str] = set()
    for component in layout_components if isinstance(layout_components, list) else []:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name", ""))
        offset_range = component.get("offset_range")
        if isinstance(offset_range, dict):
            low, high = offset_range.get("min"), offset_range.get("max")
            if isinstance(low, list) and isinstance(high, list) and len(low) == 2 and len(high) == 2:
                ranges[name] = ((int(low[0]), int(low[1])), (int(high[0]), int(high[1])))
        roles.add(str(component.get("role", "")))
    add(errors, len(component_records) == len(ranges) == int(preview.get("component_layer_count", -1)),
        "component registry/count drifted")

    layout_stories = {
        str(story.get("name")): story for story in layout.get("stories", [])
        if isinstance(story, dict)
    }
    score_items = score.get("performances")
    score_by_story = {
        str(item.get("name")): item for item in score_items
        if isinstance(score_items, list) and isinstance(item, dict)
    }
    preview_drivers = preview.get("state_drivers")
    preview_driver_map = preview_drivers if isinstance(preview_drivers, dict) else {}
    render_story_phases = story_phases(render)
    sequences = preview.get("story_sequences")
    sequence_map = {
        str(item.get("story")): item for item in sequences
        if isinstance(sequences, list) and isinstance(item, dict)
    }

    for story in EXPECTED_STORIES:
        score_item = score_by_story.get(story)
        sequence = sequence_map.get(story)
        layout_story = layout_stories.get(story)
        add(errors, isinstance(score_item, dict) and isinstance(sequence, dict) and isinstance(layout_story, dict),
            f"missing score/preview/layout record for {story}")
        if not isinstance(score_item, dict) or not isinstance(sequence, dict) or not isinstance(layout_story, dict):
            continue
        driver = score_item.get("driver")
        add(errors, isinstance(driver, dict) and driver == preview_driver_map.get(story) and
            all(driver.get(field) == layout_story.get(field) for field in
                ("emotion", "attention", "energy", "interaction_memory")) and
            isinstance(driver.get("event"), str) and bool(driver.get("event")),
            f"{story} driver is not an explicit registered state input")
        audit = sequence.get("frame_audit")
        add(errors, isinstance(audit, list) and len(audit) == len(PHASES),
            f"{story} has no complete component score audit")
        if not isinstance(audit, list) or len(audit) != len(PHASES):
            continue
        phases = tuple(str(frame.get("phase", "")) for frame in audit if isinstance(frame, dict))
        add(errors, phases == PHASES and "legacy" not in phases,
            f"{story} did not use the complete non-legacy state score")
        add(errors, int(sequence.get("visible_step_count", 0)) >= MIN_VISIBLE_STEPS and
            MIN_MAX_STEP_PIXELS <= int(sequence.get("max_step_pixels", 0)) <= MAX_MAX_STEP_PIXELS,
            f"{story} motion is outside the source-only legibility bounds")
        entry, hold, settle = audit[0], audit[5], audit[-1]
        add(errors, isinstance(entry, dict) and isinstance(hold, dict) and isinstance(settle, dict),
            f"{story} has malformed score boundary frames")
        if not isinstance(entry, dict) or not isinstance(hold, dict) or not isinstance(settle, dict):
            continue
        state_roles = hold.get("state_roles")
        add(errors, isinstance(state_roles, list) and len(state_roles) == len(set(state_roles)) and
            set(str(role) for role in state_roles).issubset(roles),
            f"{story} hold selects an unregistered role")
        phases_for_story = render_story_phases.get(story, {})
        static_entry = phases_for_story.get("entry", {})
        static_sustain = phases_for_story.get("sustain", {})
        add(errors, layer_signature(entry.get("layers")) == layer_signature(static_entry.get("layers")) and
            layer_signature(settle.get("layers")) == layer_signature(static_entry.get("layers")),
            f"{story} entry/settle does not preserve the exact calm Rig identity")
        add(errors, layer_signature(hold.get("layers")) == layer_signature(static_sustain.get("layers")),
            f"{story} hold does not exactly match its deterministic Rig sustain state")
        static_roles = {
            str(layer.get("role", "")) for layer in static_sustain.get("layers", [])
            if isinstance(layer, dict)
        }
        add(errors, static_roles.issubset(set(str(role) for role in state_roles)),
            f"{story} hold does not explicitly select every active source role")
        for index, frame in enumerate(audit):
            if not isinstance(frame, dict):
                continue
            layers = frame.get("layers")
            add(errors, isinstance(layers, list) and bool(layers), f"{story} score frame {index} has no layers")
            for layer in layers if isinstance(layers, list) else []:
                if not isinstance(layer, dict):
                    errors.append(f"{story} score frame {index} has malformed layer")
                    continue
                component = str(layer.get("component", ""))
                offset = layer.get("offset")
                record = component_records.get(component)
                add(errors, component in ranges and record is not None and
                    isinstance(offset, list) and len(offset) == 2 and
                    all(isinstance(value, int) for value in offset),
                    f"{story} score frame {index} uses an unregistered component/offset")
                if component not in ranges or not isinstance(offset, list) or len(offset) != 2:
                    continue
                low, high = ranges[component]
                add(errors, low[0] <= int(offset[0]) <= high[0] and low[1] <= int(offset[1]) <= high[1],
                    f"{story} score frame {index} exceeds {component} legal offset range")
                add(errors, record is not None and layer.get("source_frame") == record.get("source_frame") and
                    layer.get("composite_op") == record.get("composite_op", "ink"),
                    f"{story} score frame {index} source component provenance drifted")

    review_page = ROOT / str(preview.get("review_page", ""))
    owner_page = ROOT / str(preview.get("owner_review_page", ""))
    gif = ROOT / str(preview.get("animated_preview", ""))
    for path, label in ((review_page, "player"), (owner_page, "owner player"), (gif, "animated evidence")):
        add(errors, path.is_file(), f"missing {label}: {path}")
    if review_page.is_file():
        text = review_page.read_text(encoding="utf-8")
        add(errors, "stateBound" in text and "interaction_memory" in text and
            "registered-state-preview-layers" in text and ".pbm" not in text and "legacy" not in text,
            "browser player is not a state-bound component preview")
    if review_page.is_file() and owner_page.is_file():
        add(errors, review_page.read_bytes() == owner_page.read_bytes(),
            "owner preview differs from the browser component player")
    if gif.is_file():
        with Image.open(gif) as image:
            add(errors, sum(1 for _ in ImageSequence.Iterator(image)) >= len(EXPECTED_STORIES) * len(PHASES),
                "animated evidence has too few component frames")
    add(errors, PROTECTED_ACCEPTANCE.is_file() and sha256(PROTECTED_ACCEPTANCE) == PROTECTED_ACCEPTANCE_HASH,
        "protected owner acceptance artifact hash drifted")

    return {
        "schema": "companion.v9_expression_rig_registered_state_preview_machine.v1",
        "status": "PASS_REGISTERED_STATE_PREVIEW_MACHINE" if not errors else "FAIL",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "preview_report": rel(preview_path),
        "score_contract": rel(SCORE),
        "score_contract_sha256": sha256(SCORE),
        "stories": list(EXPECTED_STORIES),
        "minimum_visible_steps": MIN_VISIBLE_STEPS,
        "minimum_max_step_pixels": MIN_MAX_STEP_PIXELS,
        "maximum_max_step_pixels": MAX_MAX_STEP_PIXELS,
        "charging_error": "fail_closed_no_registered_components",
        "protected_owner_acceptance_sha256": PROTECTED_ACCEPTANCE_HASH,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=pathlib.Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--render", type=pathlib.Path, default=DEFAULT_RENDER)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    try:
        result = verify(args.preview.resolve(), args.render.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if result["status"] != "PASS_REGISTERED_STATE_PREVIEW_MACHINE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: remaining v9 state previews are state-bound, source-component-only, and fail closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
