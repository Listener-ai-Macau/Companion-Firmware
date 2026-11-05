#!/usr/bin/env python3
"""Verify the compact, component-composed v9 expression atlas preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image, ImageSequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
STATE_SCORE = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/state-preview-rig-score-v1.json"
ATLAS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/expression-atlas-v1.json"
DEFAULT_PREVIEW = ROOT / "docs/validation/companion-v9-expression-rig-expression-atlas-preview-20260718.json"
DEFAULT_RENDER = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-rig-expression-atlas-machine-20260718.json"
PROTECTED_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_ACCEPTANCE_HASH = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
EXPECTED_STORIES = (
    "daily_left", "daily_right", "daily_up", "daily_down",
    "touch_left", "touch_right", "swipe_left", "swipe_right", "swipe_down",
    "recording_focus", "menu_focus", "sleep_enter",
)
REQUIRED_DRIVER_FIELDS = ("event", "emotion", "attention", "energy", "interaction_memory")


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def verify(preview_path: pathlib.Path, render_path: pathlib.Path) -> dict[str, object]:
    errors: list[str] = []
    preview = load_json(preview_path)
    render = load_json(render_path)
    layout = load_json(LAYOUT)
    state_score = load_json(STATE_SCORE)
    atlas = load_json(ATLAS)

    add(errors, preview.get("schema") == "companion.v9_expression_rig_dynamic_preview.v1" and
        preview.get("status") == "PASS_DYNAMIC_COMPONENT_PREVIEW_READY" and
        preview.get("preview_scope") == "expression_atlas",
        "expression atlas preview is not machine-ready")
    add(errors, preview.get("source_sha256") == LOCKED_SOURCE_HASH and
        render.get("source_sha256") == LOCKED_SOURCE_HASH and
        atlas.get("source_sha256") == LOCKED_SOURCE_HASH,
        "locked v9 source hash drifted")
    add(errors, preview.get("runtime_resource_activated") is False and
        render.get("runtime_resource_activated") is False and
        atlas.get("runtime_resource_activated") is False,
        "expression atlas activated a candidate runtime resource")
    add(errors, tuple(preview.get("stories", [])) == EXPECTED_STORIES and
        int(preview.get("story_count", 0)) == len(EXPECTED_STORIES),
        "expression atlas does not cover all twelve registered V9 stories")
    add(errors, preview.get("animation_source") == "component_png_layers_from_crig_masks" and
        {"whole-face PBM flipbook", "legacy art", "code-drawn face", "custom LUT"}.issubset(
            set(preview.get("forbidden_animation_sources", []))),
        "expression atlas does not enforce component-only animation")
    add(errors, preview.get("charging_error") == "fail_closed_no_registered_components",
        "expression atlas charging/error path is not fail-closed")

    presentation = atlas.get("presentation")
    families = atlas.get("families")
    labels = atlas.get("story_labels")
    events = atlas.get("story_driver_events")
    ordered_family_stories: list[str] = []
    if isinstance(families, list):
        for family in families:
            if isinstance(family, dict) and isinstance(family.get("stories"), list):
                ordered_family_stories.extend(str(story) for story in family["stories"])
    add(errors, atlas.get("schema") == "companion.v9_expression_rig_expression_atlas.v1" and
        atlas.get("scope") == "all_registered_v9_stories" and
        atlas.get("source_layout") == rel(LAYOUT) and
        atlas.get("source_layout_revision") == layout.get("revision") and
        isinstance(presentation, dict) and
        presentation.get("first_viewport") == "compact_component_composed_expression_atlas" and
        presentation.get("selected_story_loop") is True and
        presentation.get("automatic_story_rotation") is False and
        presentation.get("atlas_thumbnail_phase") == "hold" and
        set(ordered_family_stories) == set(EXPECTED_STORIES) and
        len(ordered_family_stories) == len(set(ordered_family_stories)) and
        isinstance(labels, dict) and set(labels) == set(EXPECTED_STORIES) and
        isinstance(events, dict) and set(events) == set(EXPECTED_STORIES),
        "expression atlas contract is incomplete or permits automatic rotation")

    choreography = preview.get("preview_choreography")
    add(errors, isinstance(choreography, dict) and
        choreography.get("source") == rel(ATLAS) and
        choreography.get("source_sha256") == sha256(ATLAS) and
        choreography.get("source_layout") == rel(LAYOUT) and
        choreography.get("source_layout_revision") == layout.get("revision") and
        choreography.get("schema") == atlas.get("schema") and
        choreography.get("presentation_mode") == "state_bound_single_story_loop" and
        choreography.get("automatic_story_rotation") is False,
        "preview is not bound to the no-rotation expression atlas contract")

    reported_atlas = preview.get("expression_atlas")
    add(errors, isinstance(reported_atlas, dict) and
        reported_atlas.get("contract") == rel(ATLAS) and
        reported_atlas.get("contract_sha256") == sha256(ATLAS) and
        reported_atlas.get("families") == families and
        reported_atlas.get("story_labels") == labels and
        reported_atlas.get("first_viewport") == "compact_component_composed_expression_atlas" and
        reported_atlas.get("thumbnail_phase") == "hold",
        "preview report does not expose the component-composed atlas")

    layout_stories = {
        str(item.get("name")): item for item in layout.get("stories", [])
        if isinstance(item, dict)
    }
    components = {
        str(item.get("name")): item for item in render.get("components", [])
        if isinstance(item, dict)
    }
    ranges: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}
    for component in layout.get("components", []):
        if not isinstance(component, dict):
            continue
        offset_range = component.get("offset_range")
        if not isinstance(offset_range, dict):
            continue
        low, high = offset_range.get("min"), offset_range.get("max")
        if isinstance(low, list) and isinstance(high, list) and len(low) == len(high) == 2:
            ranges[str(component.get("name"))] = ((int(low[0]), int(low[1])), (int(high[0]), int(high[1])))
    add(errors, len(components) == len(ranges) == int(preview.get("component_layer_count", -1)),
        "component registry/count drifted")

    drivers = preview.get("state_drivers")
    driver_map = drivers if isinstance(drivers, dict) else {}
    sequences = preview.get("story_sequences")
    sequence_map = {
        str(item.get("story")): item for item in sequences
        if isinstance(sequences, list) and isinstance(item, dict)
    }
    hold_signatures: set[tuple[tuple[object, ...], ...]] = set()
    for story in EXPECTED_STORIES:
        layout_story = layout_stories.get(story)
        driver = driver_map.get(story)
        sequence = sequence_map.get(story)
        add(errors, isinstance(layout_story, dict) and isinstance(driver, dict) and
            isinstance(sequence, dict) and set(driver) == set(REQUIRED_DRIVER_FIELDS) and
            driver.get("event") == events.get(story) and
            all(driver.get(field) == layout_story.get(field) for field in REQUIRED_DRIVER_FIELDS[1:]),
            f"{story} does not expose its registered driver contract")
        if not isinstance(sequence, dict):
            continue
        audit = sequence.get("frame_audit")
        add(errors, isinstance(audit, list) and audit and
            str(audit[0].get("phase", "")) == "entry" and
            str(audit[-1].get("phase", "")) == "settle" and
            sum(str(frame.get("phase", "")) == "hold" for frame in audit if isinstance(frame, dict)) == 1,
            f"{story} does not contain one complete component performance")
        if not isinstance(audit, list):
            continue
        hold = next((frame for frame in audit if isinstance(frame, dict) and frame.get("phase") == "hold"), None)
        if isinstance(hold, dict):
            layers = hold.get("layers")
            if isinstance(layers, list):
                hold_signatures.add(tuple(sorted(
                    (str(layer.get("component", "")), tuple(layer.get("offset", [])),
                     str(layer.get("source_frame", "")), str(layer.get("composite_op", "")))
                    for layer in layers if isinstance(layer, dict)
                )))
        for frame_index, frame in enumerate(audit):
            if not isinstance(frame, dict):
                errors.append(f"{story} frame {frame_index} is malformed")
                continue
            layers = frame.get("layers")
            add(errors, isinstance(layers, list) and bool(layers),
                f"{story} frame {frame_index} has no component layers")
            for layer in layers if isinstance(layers, list) else []:
                if not isinstance(layer, dict):
                    errors.append(f"{story} frame {frame_index} has a malformed layer")
                    continue
                component = str(layer.get("component", ""))
                offset = layer.get("offset")
                record = components.get(component)
                add(errors, record is not None and component in ranges and
                    isinstance(offset, list) and len(offset) == 2 and
                    all(isinstance(value, int) for value in offset),
                    f"{story} frame {frame_index} uses an unregistered component/offset")
                if record is None or component not in ranges or not isinstance(offset, list) or len(offset) != 2:
                    continue
                low, high = ranges[component]
                add(errors, low[0] <= offset[0] <= high[0] and low[1] <= offset[1] <= high[1] and
                    layer.get("source_frame") == record.get("source_frame") and
                    layer.get("composite_op") == record.get("composite_op", "ink"),
                    f"{story} frame {frame_index} violates registered source-component provenance")
    add(errors, len(hold_signatures) >= 8,
        "expression atlas has too few distinct source-component hold poses")

    review_page = ROOT / str(preview.get("review_page", ""))
    owner_page = ROOT / str(preview.get("owner_review_page", ""))
    gif = ROOT / str(preview.get("animated_preview", ""))
    for path, label in ((review_page, "atlas player"), (owner_page, "owner atlas player"), (gif, "atlas animation evidence")):
        add(errors, path.is_file(), f"missing {label}: {path}")
    if review_page.is_file():
        text = review_page.read_text(encoding="utf-8")
        add(errors, "expressionAtlas" in text and "atlas-state" in text and
            "DATA.atlas" in text and "stateBound" in text and
            "expression-atlas-layers" in text and ".pbm" not in text,
            "browser page is not a component-composed expression atlas")
    if review_page.is_file() and owner_page.is_file():
        add(errors, review_page.read_bytes() == owner_page.read_bytes(),
            "owner atlas differs from the browser atlas")
    if gif.is_file():
        with Image.open(gif) as image:
            add(errors, sum(1 for _ in ImageSequence.Iterator(image)) >= len(EXPECTED_STORIES) * 9,
                "atlas animated evidence has too few component frames")
    add(errors, PROTECTED_ACCEPTANCE.is_file() and sha256(PROTECTED_ACCEPTANCE) == PROTECTED_ACCEPTANCE_HASH,
        "protected owner acceptance artifact hash drifted")

    return {
        "schema": "companion.v9_expression_rig_expression_atlas_machine.v1",
        "status": "PASS_EXPRESSION_ATLAS_MACHINE" if not errors else "FAIL",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "preview_report": rel(preview_path),
        "atlas_contract": rel(ATLAS),
        "atlas_contract_sha256": sha256(ATLAS),
        "stories": list(EXPECTED_STORIES),
        "family_count": len(families) if isinstance(families, list) else 0,
        "distinct_hold_pose_count": len(hold_signatures),
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
    if result["status"] != "PASS_EXPRESSION_ATLAS_MACHINE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: v9 expression atlas covers all registered stories with source-component poses only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
