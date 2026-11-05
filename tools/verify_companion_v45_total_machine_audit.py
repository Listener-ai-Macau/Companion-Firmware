#!/usr/bin/env python3
"""Close the V45 complete-eye upper-art machine evidence before human review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image



ROOT = Path(__file__).resolve().parents[1]
LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_SHA = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V22_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V22_TRACE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-trace-contract-r5-20260721.json"
V22_ROUTER = ROOT / "docs/validation/companion-v22-everyday-bridge-router-r2-20260720.json"
V43_GATE = ROOT / "docs/validation/companion-v43-recording-input-inward-source-gate-20260721.json"
V44_LAYOUT_GATE = ROOT / "docs/validation/companion-v44-blink-stable-center-layout-gate-20260721.json"
V44_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/v44-special-component-layout.json"
V44_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/target-score-attempt-01/v44-wb55-target-profile-plan.json"
V44_PROFILE = ROOT / "docs/validation/companion-v44-blink-stable-center-wb55-profile-host-20260721.json"
V44_PREVIEW = ROOT / "docs/validation/companion-v44-blink-stable-center-single-epaper-browser-wb55-preview-20260721.json"
V44_PARITY = ROOT / "docs/validation/companion-v44-blink-stable-center-wb55-component-parity-host-20260721.json"
V44_VISUAL = ROOT / "docs/validation/companion-v44-single-epaper-browser-visual-20260721.json"
V44_TOUCH = ROOT / "docs/validation/companion-v44-single-epaper-touch-host-20260721.json"
V45_SOURCE_GATE = ROOT / "docs/validation/companion-v45-complete-eye-pair-source-v6-gate-20260721.json"
V45_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/v45-special-component-layout.json"
V45_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/target-score-attempt-01/v45-wb55-target-profile-plan.json"
V45_PROFILE = ROOT / "docs/validation/companion-v45-complete-eye-wb55-profile-host-20260721.json"
V45_PREVIEW = ROOT / "docs/validation/companion-v45-complete-eye-browser-wb55-preview-20260721.json"
V45_PARITY = ROOT / "docs/validation/companion-v45-complete-eye-wb55-component-parity-host-20260721.json"
V45_VISUAL = ROOT / "docs/validation/companion-v45-single-epaper-browser-visual-20260721.json"
V45_TOUCH = ROOT / "docs/validation/companion-v45-single-epaper-touch-host-20260721.json"
V45_WALL = ROOT / "docs/validation/companion-v45-expanded-review-wall-20260721.json"
V45_BROWSER_POINTER = ROOT / "docs/validation/companion-v45-browser-pointer-fail-safe-20260721.json"
V34_PROFILE = ROOT / "docs/validation/companion-v34-v35-special-decoration-wb55-profile-host-20260720.json"
V34_PARITY = ROOT / "docs/validation/companion-v34-v35-special-decoration-wb55-component-parity-host-20260720.json"
V34_PREVIEW = ROOT / "docs/validation/companion-v34-v35-special-decoration-browser-wb55-preview-20260720.json"
V34_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
V22_FACE_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V45_REVIEW = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721.owner-review.json"
V45_REVIEW_NOTE = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721.owner-review.note.txt"
V45_R4_REVIEW = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721-r4.owner-review.json"
V45_R4_REVIEW_NOTE = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721-r4.owner-review.note.txt"
V45_R5_REVIEW = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721-r5.owner-review.json"
V45_R5_REVIEW_NOTE = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721-r5.owner-review.note.txt"
REPORT = ROOT / "docs/validation/companion-v45-total-machine-audit-20260721.json"
GAZE = {"daily_attention_center", "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down"}
SPECIAL_EVENT_COMPONENTS = {
    "menu_entry": (545, 546, 547),
    "upgrade_progress": (563, 564, 565),
    "error_caution": (566, 567, 568),
    "recording_input": (569, 570, 571, 605, 606, 607, 608),
    "wireless_dock_charge": (572, 573, 574),
    "sleep_zzz": (594, 595, 596),
}
FUNCTIONAL_TRACK_COMPONENTS = {
    "recording_input": (605, 606, 607, 608),
    "bottom_connector_charging": (572, 573, 574),
    "upgrade_progress": (563, 564, 565),
    "error_caution": (566, 567, 568),
}
FUNCTIONAL_SCORE_COMPONENTS = {
    "recording_with_calm": (605, 606, 607, 608),
    "recording_with_warm": (605, 606, 607, 608),
    "charging_with_calm": (572, 573, 574),
    "upgrade_with_playful": (563, 564, 565),
    "error_with_calm": (566, 567, 568),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing artifact: {path.relative_to(ROOT).as_posix()}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"artifact is not an object: {path.relative_to(ROOT).as_posix()}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def evidence(path: Path, status: str) -> dict[str, str]:
    value = load(path)
    require(value.get("status") == status, f"unexpected status in {rel(path)}")
    require(value.get("runtime_resource_activated") is False,
            f"runtime activation boundary drifted in {rel(path)}")
    return {"artifact": rel(path), "status": status, "sha256": sha256(path)}


def frame_key(item: dict[str, Any]) -> tuple[str, str, str, int]:
    score, cue, phase, duration = item.get("score"), item.get("cue"), item.get("phase"), item.get("duration_ms")
    require(isinstance(score, str) and isinstance(cue, str) and isinstance(phase, str) and
            isinstance(duration, int) and duration > 0, "malformed choreography frame")
    return score, cue, phase, duration


def replay_key(item: dict[str, Any]) -> tuple[str, str, int]:
    score, cue, duration = item.get("score"), item.get("cue"), item.get("duration_ms")
    require(isinstance(score, str) and isinstance(cue, str) and isinstance(duration, int) and duration > 0,
            "malformed parity replay frame")
    return score, cue, duration


def plan_layer_key(layer: dict[str, Any]) -> tuple[int, str, tuple[int, int], tuple[int, int], str]:
    component_id = layer.get("component_id")
    pack = layer.get("pack")
    anchor = layer.get("anchor")
    offset = layer.get("offset")
    composite_op = layer.get("composite_op")
    require(isinstance(component_id, int) and isinstance(pack, str) and
            isinstance(anchor, list) and len(anchor) == 2 and all(isinstance(value, int) for value in anchor) and
            isinstance(offset, list) and len(offset) == 2 and all(isinstance(value, int) for value in offset) and
            composite_op in {"ink", "erase"}, "malformed parity component plan layer")
    return component_id, pack, tuple(anchor), tuple(offset), composite_op


def layout_component_map(v22_layout: dict[str, Any], special_layout: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for component in list(v22_layout.get("components", [])) + list(special_layout.get("components", [])):
        component_id = int(component["component_id"])
        require(component_id not in result, f"duplicate component id in parity layout: {component_id}")
        result[component_id] = component
    return result


def canonical_trace_layers(layers: list[dict[str, Any]], components: dict[int, dict[str, Any]]) -> list[tuple[int, str, tuple[int, int], tuple[int, int], str]]:
    result = []
    for layer in layers:
        component_id = layer.get("component_id")
        component = components.get(component_id)
        require(component is not None, f"trace references an unknown component: {component_id}")
        pack = layer.get("pack")
        expected_pack = "v22_face" if component_id < 512 else "v45_special_source"
        require(pack == expected_pack, f"trace component pack drifted: {component_id}")
        result.append(plan_layer_key({"component_id": component_id, "pack": pack,
                                      "anchor": component.get("base_position"),
                                      "offset": layer.get("offset"),
                                      "composite_op": component.get("composite_op")}))
    return result


def pbm_pixels(path: Path) -> tuple[int, int, set[tuple[int, int]]]:
    raw = path.read_bytes()
    cursor = 0
    tokens: list[str] = []
    while len(tokens) < 3:
        while cursor < len(raw) and chr(raw[cursor]).isspace():
            cursor += 1
        if cursor < len(raw) and raw[cursor] == ord("#"):
            while cursor < len(raw) and raw[cursor] not in (10, 13):
                cursor += 1
            continue
        start = cursor
        while cursor < len(raw) and not chr(raw[cursor]).isspace():
            cursor += 1
        require(start < cursor, f"malformed PBM header: {rel(path)}")
        tokens.append(raw[start:cursor].decode("ascii"))
    require(tokens[0] == "P4", f"special mask is not binary PBM: {rel(path)}")
    width, height = int(tokens[1]), int(tokens[2])
    require(width > 0 and height > 0, f"special mask has invalid dimensions: {rel(path)}")
    require(cursor < len(raw), f"special mask has no payload: {rel(path)}")
    cursor += 1
    stride = (width + 7) // 8
    payload = raw[cursor:cursor + stride * height]
    require(len(payload) == stride * height, f"special mask payload is truncated: {rel(path)}")
    pixels = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if not (payload[y * stride + x // 8] & (0x80 >> (x & 7)))
    }
    return width, height, pixels


def positioned_pixels(component: dict[str, Any]) -> set[tuple[int, int]]:
    mask_path = ROOT / str(component.get("mask", ""))
    require(mask_path.is_file(), f"special component mask is missing: {component.get('component_id')}")
    width, height, pixels = pbm_pixels(mask_path)
    base = component.get("base_position")
    require(isinstance(base, list) and len(base) == 2 and all(isinstance(item, int) for item in base),
            f"special component anchor is malformed: {component.get('component_id')}")
    declared_size = component.get("mask_size")
    if declared_size is not None:
        require(declared_size == [width, height],
                f"special component mask size drifted: {component.get('component_id')}")
    positioned = {(base[0] + x, base[1] + y) for x, y in pixels}
    require(all(0 <= x < 200 and 0 <= y < 200 for x, y in positioned),
            f"special component leaves the 200x200 canvas: {component.get('component_id')}")
    return positioned


def rendered_ink_pixels(component: dict[str, Any]) -> set[tuple[int, int]]:
    """Read the PBM polarity used by the browser/WB55 renderer."""
    mask_path = ROOT / str(component.get("mask", ""))
    base = component.get("base_position")
    require(mask_path.is_file() and isinstance(base, list) and len(base) == 2,
            f"component mask cannot be read for rendered geometry: {component.get('component_id')}")
    with Image.open(mask_path) as opened:
        image = opened.convert("1")
        return {(base[0] + x, base[1] + y)
                for y in range(image.height)
                for x in range(image.width)
                if image.getpixel((x, y)) == 0}


def component_event(component: dict[str, Any]) -> str | None:
    event = component.get("event")
    if isinstance(event, str):
        return event
    source = component.get("source")
    if isinstance(source, dict) and isinstance(source.get("event"), str):
        return source["event"]
    return None


def bbox_center2(pixels: set[tuple[int, int]]) -> tuple[int, int]:
    require(pixels, "cannot calculate an empty component bbox")
    xs = [x for x, _ in pixels]
    ys = [y for _, y in pixels]
    return min(xs) + max(xs), min(ys) + max(ys)


def centroid_milli(pixels: set[tuple[int, int]]) -> tuple[int, int]:
    """Return the black-ink centroid in thousandths of a pixel."""
    require(pixels, "cannot calculate an empty component centroid")
    count = len(pixels)
    return (round(sum(x for x, _ in pixels) * 1000 / count),
            round(sum(y for _, y in pixels) * 1000 / count))


def blink_eye_geometry_gate(special_layout: dict[str, Any], v22_layout: dict[str, Any]) -> dict[str, Any]:
    components = layout_component_map(v22_layout, special_layout)
    groups = {
        "left": {"open": [2, 1, 3], "closing": [599], "closed": [601], "opening": [603]},
        "right": {"open": [6, 5, 7], "closing": [600], "closed": [602], "opening": [604]},
    }
    stages = ("closing", "closed", "opening")
    result: dict[str, Any] = {}
    for side, stage_groups in groups.items():
        reference_center = bbox_center2(set().union(*(rendered_ink_pixels(components[component_id])
                                                       for component_id in stage_groups["open"])))
        stage_result: dict[str, Any] = {"reference_component_ids": stage_groups["open"],
                                        "reference_bbox_center_x2_y2": list(reference_center), "stages": {}}
        for stage in stages:
            component_ids = stage_groups[stage]
            center = bbox_center2(set().union(*(rendered_ink_pixels(components[component_id])
                                                 for component_id in component_ids)))
            delta = [center[0] - reference_center[0], center[1] - reference_center[1]]
            for component_id in component_ids:
                revision = components[component_id].get("anchor_revision", {})
                require(revision.get("kind") == "v45_eye_group_centroid_reanchor" and
                        revision.get("reference_v22_eye_group") == stage_groups["open"],
                        f"V45 {side} {stage} component {component_id} lacks the registered eye-group anchor revision")
            require(abs(delta[0]) <= 2 and abs(delta[1]) <= 1,
                    f"V45 {side} {stage} eye group shifts from the V22 open-eye center: {delta}")
            stage_result["stages"][stage] = {"component_ids": component_ids,
                                               "bbox_center_x2_y2": list(center), "delta_x2_y2": delta}
        result[side] = stage_result
    return result


def special_state_machine_gate(special_layout: dict[str, Any], v22_layout: dict[str, Any]) -> dict[str, Any]:
    components = {int(item["component_id"]): item for item in special_layout.get("components", [])}
    require(len(components) == 60, "V45 special component namespace is incomplete")
    face_pixels: set[tuple[int, int]] = set()
    for component in v22_layout.get("components", []):
        face_pixels.update(positioned_pixels(component))

    event_metrics: dict[str, Any] = {}
    for event, expected_ids in SPECIAL_EVENT_COMPONENTS.items():
        event_components = {
            component_id: components.get(component_id)
            for component_id in expected_ids
        }
        require(all(component is not None for component in event_components.values()),
                f"{event} source component group is incomplete")
        actual_ids = tuple(sorted(component_id for component_id, component in components.items()
                                  if component_event(component) == event))
        require(actual_ids == tuple(sorted(expected_ids)),
                f"{event} has an unregistered or missing component id")
        union: set[tuple[int, int]] = set()
        for component_id, component in event_components.items():
            assert component is not None
            mask_path = ROOT / str(component.get("mask", ""))
            require(sha256(mask_path) == str(component.get("mask_sha256", "")).upper(),
                    f"{event} mask hash drifted for component {component_id}")
            source = component.get("source", {})
            require(isinstance(source, dict), f"{event} source lineage is missing for component {component_id}")
            request_path = ROOT / str(source.get("request", ""))
            prior_layout = ROOT / str(source.get("prior_layout", ""))
            prior_mask = ROOT / str(source.get("prior_mask", ""))
            derived_split = source.get("kind") == "source_derived_recording_mic_wave_split"
            if derived_split:
                source_masks = source.get("source_masks", [])
                require(source.get("event") == "recording_input" and
                        source.get("no_new_image_generation") is True and
                        [item.get("component_id") for item in source_masks] == [569, 570, 571],
                        f"{event} derived split lineage is incomplete for component {component_id}")
                for source_mask in source_masks:
                    source_path = ROOT / str(source_mask.get("path", ""))
                    require(source_path.is_file() and
                            sha256(source_path) == str(source_mask.get("sha256", "")).upper(),
                            f"{event} derived split source mask drifted for component {component_id}")
            else:
                require((request_path.is_file() and source.get("locked_v9_sha256") == LOCKED_SHA) or
                        (prior_layout.is_file() and prior_mask.is_file() and
                         source.get("prior_mask_sha256") == component.get("mask_sha256")),
                        f"{event} component {component_id} has no versioned source lineage")
            union.update(positioned_pixels(component))
        overlap = union & face_pixels
        if event == "menu_entry":
            require(len(overlap) <= 8 and max(y for _, y in union) <= 80,
                    "Menu entry ornament escaped its short upper cue zone")
        else:
            require(not overlap, f"{event} ornament overlaps a V22 face pixel")
        xs = [x for x, _ in union]
        ys = [y for _, y in union]
        event_metrics[event] = {
            "component_ids": list(expected_ids),
            "pixel_count": len(union),
            "face_pixel_overlap": len(overlap),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
        }

    for component_id in (572, 573, 574):
        require(components[component_id].get("base_position") == [86, 181] and
                components[component_id].get("anchor_revision", {}).get("kind") ==
                "v45_below_face_safe_zone_reanchor",
                "V45 wireless dock anchor did not move below the V22 face")
    v22_components = {int(item["component_id"]): item for item in v22_layout.get("components", [])}
    blink_reference_groups = {
        "left_eye": (599, [2, 1, 3]),
        "right_eye": (600, [6, 5, 7]),
    }
    blink_stage_metrics: dict[str, Any] = {}
    for side, (first_component_id, reference_ids) in blink_reference_groups.items():
        reference_pixels: set[tuple[int, int]] = set()
        for reference_id in reference_ids:
            require(reference_id in v22_components, f"V22 blink reference component is missing: {reference_id}")
            reference_pixels.update(rendered_ink_pixels(v22_components[reference_id]))
        expected_center2 = bbox_center2(reference_pixels)
        for component_id in (first_component_id, first_component_id + 2, first_component_id + 4):
            component = components[component_id]
            require(component.get("anchor_revision", {}).get("kind") == "v45_eye_group_centroid_reanchor" and
                    component.get("anchor_revision", {}).get("reference_v22_eye_group") == reference_ids,
                    f"V45 blink anchor provenance is missing for component {component_id}")
            actual_center2 = bbox_center2(rendered_ink_pixels(component))
            require(abs(actual_center2[0] - expected_center2[0]) <= 2 and
                    abs(actual_center2[1] - expected_center2[1]) <= 1,
                    f"V45 {side} blink component {component_id} shifts away from its V22 eye-group center")
            blink_stage_metrics[str(component_id)] = {
                "side": side,
                "reference_component_ids": reference_ids,
                "bbox_center2": list(actual_center2),
                "center": [actual_center2[0] / 2, actual_center2[1] / 2],
                "reference_bbox_center2": list(expected_center2),
                "bbox_center_error2": [actual_center2[0] - expected_center2[0], actual_center2[1] - expected_center2[1]],
                "mask_sha256": component.get("mask_sha256"),
            }
    return {"event_groups": event_metrics, "blink_stage_centers": blink_stage_metrics,
            "face_pixel_count": len(face_pixels)}


def functional_track_gate(trace: dict[str, Any]) -> dict[str, Any]:
    tracks = {track.get("name"): track for track in trace.get("functional_decoration_tracks", [])}
    result: dict[str, Any] = {}
    for name, expected_ids in FUNCTIONAL_TRACK_COMPONENTS.items():
        track = tracks.get(name)
        require(isinstance(track, dict) and isinstance(track.get("steps"), list) and len(track["steps"]) == 5,
                f"functional track is missing or not five-phase: {name}")
        used = []
        for step in track["steps"]:
            require(isinstance(step.get("duration_ms"), int) and step["duration_ms"] > 0,
                    f"functional track duration is invalid: {name}")
            ids = [int(layer.get("component_id")) for layer in step.get("layers", [])]
            if name == "recording_input":
                require(len(ids) == 2 and ids[0] == 605 and ids[1] in {606, 607, 608},
                        f"functional track {name} must hold the fixed microphone and one registered waveform")
                used.extend(ids)
            else:
                require(len(ids) == 1 and ids[0] in expected_ids,
                        f"functional track {name} borrowed an unavailable component")
                used.append(ids[0])
        require(set(used) == set(expected_ids), f"functional track {name} does not cover its full source group")
        result[name] = {"component_ids": list(expected_ids), "step_component_ids": used}
    menu = trace.get("menu_entry_track", {})
    menu_ids = [int(layer.get("component_id")) for step in menu.get("steps", []) for layer in step.get("layers", [])]
    require(menu_ids == [545, 546, 547], "Menu entry cue is not the registered finite three-stage source track")
    result["menu_entry"] = {"component_ids": menu_ids}
    for score_name, expected_ids in FUNCTIONAL_SCORE_COMPONENTS.items():
        score = next((score for score in trace.get("scores", []) if score.get("name") == score_name), None)
        require(isinstance(score, dict), f"functional score is missing: {score_name}")
        used = {int(layer.get("component_id")) for step in score.get("steps", [])
                for layer in step.get("layers", []) if int(layer.get("component_id", -1)) in expected_ids}
        require(used == set(expected_ids), f"functional score {score_name} does not carry its registered event source")
    return result


def fixed_nose_and_choreography_gate(trace: dict[str, Any], v22_layout: dict[str, Any],
                                     special_layout: dict[str, Any]) -> dict[str, Any]:
    components = layout_component_map(v22_layout, special_layout)
    roles = {component_id: component.get("role") for component_id, component in components.items()}
    dynamic_roles = {
        "left_brow", "right_brow", "left_cheek", "right_cheek", "mouth",
        "left_highlight", "right_highlight", "left_sparkle", "right_sparkle",
        "left_eye", "right_eye",
    }
    owner_expression_scores = {
        "calm_presence", "warm_presence", "curious_question", "alert_exclamation",
        "playful_presence", "delighted_presence", "bashful_presence", "thoughtful_presence",
        "focused_presence",
    }
    richer_scores = {"delighted_presence", "bashful_presence", "thoughtful_presence", "focused_presence"}
    metrics: dict[str, Any] = {}
    for score in trace.get("scores", []):
        name = str(score.get("name"))
        signatures: list[tuple[Any, ...]] = []
        brow_offsets: list[tuple[int, int]] = []
        mouth_ids: list[int] = []
        for step in score.get("steps", []):
            layers = step.get("layers", [])
            require(isinstance(layers, list) and len(layers) <= 16,
                    f"V45 frame exceeds the registered layer budget: {name}")
            noses = [layer for layer in layers if layer.get("component_id") == 4]
            require(len(noses) == 1 and noses[0].get("offset") == [0, 0],
                    f"V45 frame does not retain the fixed nose at [0,0]: {name}")
            signature: list[tuple[Any, ...]] = []
            for layer in layers:
                component_id = int(layer["component_id"])
                role = roles.get(component_id)
                if role in dynamic_roles:
                    signature.append((component_id, tuple(layer["offset"]), components[component_id].get("composite_op")))
                if role in {"left_brow", "right_brow"}:
                    brow_offsets.append(tuple(layer["offset"]))
                if role == "mouth":
                    mouth_ids.append(component_id)
            signatures.append(tuple(signature))
        if name in owner_expression_scores:
            require(len(set(signatures)) >= 2,
                    f"V45 expression choreography has no registered component variation: {name}")
        if name in richer_scores:
            require(len(set(brow_offsets)) >= 2 and len(set(mouth_ids)) >= 2,
                    f"V45 richer expression lacks brow and mouth choreography: {name}")
        metrics[name] = {
            "frame_count": len(signatures),
            "fixed_nose_frames": len(signatures),
            "unique_registered_face_signatures": len(set(signatures)),
            "brow_offset_variants": [list(value) for value in sorted(set(brow_offsets))],
            "mouth_component_variants": sorted(set(mouth_ids)),
        }
    require(len(metrics) == 21, "V45 choreography evidence does not cover every story")
    return metrics


def expanded_review_wall_gate(wall: dict[str, Any], preview: dict[str, Any]) -> dict[str, Any]:
    overview = preview.get("chinese_overview", {})
    expected_scores = overview.get("owner_visible_scores", [])
    actual_stories = wall.get("stories", [])
    require(wall.get("presentation") == "vertical_scroll_single_column_all_owner_visible_stories" and
            wall.get("canvas") == {"width": 200, "height": 200, "pixel_format": "1bpp_white_is_one_msb"} and
            wall.get("owner_visible_story_count") == 16 and
            wall.get("expanded_frame_count") == 78 and
            [story.get("name") for story in actual_stories] == expected_scores,
            "V45 expanded review wall presentation or story coverage drifted")
    expected_by_score: dict[str, list[dict[str, Any]]] = {}
    for frame in preview.get("frames", []):
        expected_by_score.setdefault(str(frame.get("score")), []).append(frame)
    total = 0
    for story in actual_stories:
        name = str(story.get("name"))
        expected = expected_by_score.get(name, [])
        actual = story.get("frames", [])
        require(len(actual) == len(expected) and actual, f"expanded wall frame coverage drifted: {name}")
        for index, (actual_frame, expected_frame) in enumerate(zip(actual, expected)):
            require(actual_frame.get("index") == index and
                    actual_frame.get("src") == expected_frame.get("png") and
                    actual_frame.get("cue") == expected_frame.get("cue") and
                    actual_frame.get("phase") == expected_frame.get("phase") and
                    actual_frame.get("duration_ms") == expected_frame.get("duration_ms") and
                    actual_frame.get("target_1bpp_sha256") == expected_frame.get("target_1bpp_sha256"),
                    f"expanded wall frame differs from the registered preview: {name}/{index}")
            total += 1
    html_path = ROOT / str(wall.get("html", ""))
    require(html_path.is_file(), "expanded V45 review wall HTML is missing")
    html = html_path.read_text(encoding="utf-8")
    wall_runtime_markers = ("pointerdown", "pointermove", "pointerup", "mousedown", "mousemove", "mouseup",
                            "touchData", "touchTarget", "showTouch", "touchCache", "loadAsset", "baseSrc",
                            "overlay", "释放回正中", "滑动边界")
    require(html.count('data-review-revision="v45-touch-failsafe-r7"') == 16 and
            'Touch fail-safe r7' in html and html.count('data-canvas="200x200"') == 16 and "<canvas" not in html.lower() and
            html.count('data-renderer="registered-200x200-component-frames"') == 1 and
            html.count('data-touch-surface="true"') == 16 and
            all(marker in html for marker in wall_runtime_markers) and
            ("touchRequest" in html or "renderRequest" in html) and
            ("presentBase" in html or "image.onerror" in html) and
            "frame-staging" in html and "decodeImage" in html and
            ".gaze{background:transparent}" in html,
            "expanded V45 review wall is not sixteen real 200x200 image viewports")
    touch = wall.get("touch_interaction", {})
    require(touch == {"surface": "each_story_200x200_viewport", "mode": "registered_pointer_and_mouse_coordinate_to_gaze_overlay",
                      "overlay_count": 280, "base_story_count": 16, "center_key": "1,0,1,0",
                      "mapping": "pointer x/y maps to registered highlight and sparkle offsets",
                      "release_behavior": "center_then_resume_story",
                      "gestures": ["tap", "drag", "release_to_center", "swipe_left", "swipe_right", "swipe_up", "swipe_down"],
                      "swipe_behavior": "scroll_to_adjacent_story", "mouse_fallback": "mousedown_mousemove_mouseup"},
                      "expanded V45 review wall touch interaction contract drifted")
    return {"story_count": len(actual_stories), "frame_count": total,
            "html": rel(html_path), "source_preview": rel(V45_PREVIEW), "touch_interaction": touch}


def real_browser_pointer_gate(pointer: dict[str, Any]) -> dict[str, Any]:
    raw_report_name = pointer.get("raw_report")
    require(isinstance(raw_report_name, str) and raw_report_name, "V45 browser pointer raw report is missing")
    raw_path = ROOT / raw_report_name
    raw = load(raw_path)
    require(raw.get("errors") == [] and raw.get("stats", {}).get("unexpected") == 0 and
            raw.get("stats", {}).get("expected") == 2,
            "V45 Playwright pointer replay did not complete cleanly")
    suites = raw.get("suites", [])
    require(isinstance(suites, list) and len(suites) == 1, "V45 Playwright pointer suite coverage drifted")
    specs = suites[0].get("specs", [])
    require(isinstance(specs, list) and len(specs) == 2, "V45 Playwright pointer spec coverage drifted")
    expected_titles = {
        "real mouse press, drag and release never hide the primary expression frame",
        "expanded wall mouse input keeps the story viewport visible",
    }
    actual_titles = {spec.get("title") for spec in specs}
    require(actual_titles == expected_titles and all(spec.get("ok") is True for spec in specs),
            "V45 Playwright pointer assertions did not pass")
    durations = []
    for spec in specs:
        tests = spec.get("tests", [])
        require(isinstance(tests, list) and len(tests) == 1 and tests[0].get("status") == "expected",
                "V45 Playwright pointer test result is not expected-pass")
        results = tests[0].get("results", [])
        require(isinstance(results, list) and len(results) == 1 and results[0].get("status") == "passed",
                "V45 Playwright pointer worker result is not passed")
        durations.append(results[0].get("duration"))
    spec_path = ROOT / "tools/v45-click.spec.js"
    require(spec_path.is_file(), "V45 Playwright pointer spec is missing")
    source = spec_path.read_text(encoding="utf-8")
    for marker in ("msedge.exe", "page.mouse.down()", "page.mouse.move(", "page.mouse.up()",
                   "#epaper-frame", "primary expression frame"):
        require(marker in source, f"V45 Playwright pointer spec marker missing: {marker}")
    screenshots = pointer.get("screenshots", [])
    require(pointer.get("screen_count") == 6 and isinstance(screenshots, list) and len(screenshots) == 6,
            "V45 real-browser pointer screenshots are incomplete")
    for screenshot in screenshots:
        path = ROOT / str(screenshot.get("path", ""))
        require(path.is_file() and screenshot.get("black_pixel_count", 0) >= 500 and
                screenshot.get("black_pixel_ratio", 0) > 0,
                f"V45 real-browser pointer screenshot is blank: {screenshot.get('path')}")
    return {"raw_report": rel(raw_path), "spec": rel(spec_path), "titles": sorted(actual_titles),
            "input_sequence": ["mouse_down", "mouse_drag", "mouse_up"],
            "primary_frame_assertions": ["not_hidden_after_press", "src_nonempty_after_press",
                                          "not_hidden_after_drag", "not_hidden_after_release",
                                          "src_nonempty_after_release"],
            "playwright_status": "passed", "spec_count": len(specs),
            "screenshots": screenshots,
            "duration_ms": durations}


def v34_v35_source_gate(layout: dict[str, Any]) -> dict[str, Any]:
    components = layout.get("components", [])
    require(layout.get("schema") == "companion.v34_v35_special_decoration_component_layout.v1" and
            layout.get("locked_v9_source_sha256") == LOCKED_SHA and
            layout.get("runtime_resource_activated") is False and len(components) == 39 and
            {component.get("component_id") for component in components} == set(range(500, 539)),
            "V34/V35 source layout lineage or component coverage drifted")
    for component in components:
        mask = ROOT / str(component.get("mask", ""))
        require(mask.is_file() and component.get("mask_sha256") == sha256(mask),
                f"V34/V35 source mask/hash drifted: {component.get('component_id')}")
    pack = layout.get("pack", {})
    crig = ROOT / str(pack.get("path", ""))
    require(crig.is_file() and pack.get("sha256") == sha256(crig) and
            pack.get("component_count") == 39 and pack.get("total_size") == crig.stat().st_size,
            "V34/V35 CRIG source package/hash drifted")
    return {"component_count": len(components), "component_id_range": [500, 538],
            "mask_hashes": "all_39_source_mask_sha256_match", "crig": rel(crig),
            "crig_sha256": sha256(crig), "crig_size": crig.stat().st_size}


def v22_daily_contract_gate(layout: dict[str, Any], trace: dict[str, Any], router: dict[str, Any]) -> dict[str, Any]:
    components = layout.get("components", [])
    require(layout.get("schema") == "companion.v22_emotion_separation_target_rig.v1" and
            layout.get("locked_v9_source_sha256") == LOCKED_SHA and
            layout.get("runtime_resource_activated") is False and len(components) == 37 and
            {component.get("component_id") for component in components} == set(range(1, 38)),
            "V22 source component coverage or lineage drifted")
    component_map = {component["component_id"]: component for component in components}
    required_roles = {"left_eye", "right_eye", "left_highlight", "right_highlight", "left_sparkle",
                      "right_sparkle", "left_brow", "right_brow", "left_cheek", "right_cheek", "mouth", "nose"}
    require(required_roles <= {component.get("role") for component in components},
            "V22 face component-addressability roles are incomplete")
    for component in components:
        mask = ROOT / str(component.get("mask", ""))
        require(mask.is_file() and component.get("mask_sha256") == sha256(mask),
                f"V22 source mask/hash drifted: {component.get('component_id')}")
    pack = layout.get("pack")
    crig = ROOT / str(pack)
    require(crig.is_file() and sha256(crig) == "43184DE67E28EEA2B5277A406145B54C6204453E4441F9D1BD9DE20EEEA25333",
            "V22 CRIG source package/hash drifted")
    expected_cues = ["source_hold", "primary_highlight_lead", "sparkle_arrive", "brow_apex", "lower_face_apex"]
    total_frames = 0
    bridge_summary: list[dict[str, Any]] = []
    for bridge in layout.get("bridges", []):
        frames = bridge.get("frames", [])
        cues = [frame.get("cue") for frame in frames]
        require(cues[:5] == expected_cues and cues[-2:] == ["target_hold", "highlight_settle"] and
                cues[5:-2] in ([], ["accent_resolve"]),
                f"V22 bridge cue order drifted: {bridge.get('name')}")
        hold = next((frame for frame in frames if frame.get("cue") == "target_hold"), None)
        require(isinstance(hold, dict) and hold.get("duration_ms", 0) >= 750,
                f"V22 visible target hold is below 750 ms: {bridge.get('name')}")
        for frame in frames:
            layers = frame.get("layers", [])
            require(isinstance(layers, list) and 0 < len(layers) <= 16,
                    f"V22 frame layer budget drifted: {bridge.get('name')}/{frame.get('index')}")
            for layer in layers:
                component_id = layer.get("component_id")
                require(component_id in component_map and isinstance(layer.get("offset"), list) and
                        len(layer["offset"]) == 2,
                        f"V22 frame references an unregistered component: {bridge.get('name')}")
                component = component_map[component_id]
                offset = layer["offset"]
                minimum = component["offset_range"]["min"]
                maximum = component["offset_range"]["max"]
                require(all(minimum[index] <= offset[index] <= maximum[index] for index in (0, 1)),
                        f"V22 frame offset exceeds registered range: {bridge.get('name')}")
                if component_id == 4:
                    require(offset == [0, 0], f"V22 nose moved from [0,0]: {bridge.get('name')}")
            target = ROOT / str(frame.get("target_pbm", ""))
            require(target.is_file() and frame.get("target_pbm_sha256") == sha256(target),
                    f"V22 target PBM/hash drifted: {bridge.get('name')}/{frame.get('index')}")
        total_frames += len(frames)
        bridge_summary.append({"name": bridge.get("name"), "frame_count": len(frames),
                               "cue_order": cues, "target_hold_ms": hold["duration_ms"]})
    require(len(layout.get("bridges", [])) == 10 and total_frames == 72,
            "V22 bridge/frame coverage drifted")
    require(router.get("ordinary_affect_only") is True and router.get("bridge_count") == 10 and
            router.get("replayed_step_count") == 72 and router.get("session_visible_step_count") == 72 and
            router.get("session_requires_visible_acknowledgement") is True and
            router.get("session_min_post_refresh_hold_ms") >= 750 and
            router.get("candidate_runtime_activation_allowed") is False and
            router.get("runtime_resource_activated") is False and
            set(router.get("unbound_product_states", [])) >=
            {"menu", "recording", "upgrade", "sleep", "charging", "error"},
            "V22 deterministic everyday router contract drifted")
    timeline = trace.get("browser_observed_replay_timeline", [])
    reference = next(bridge for bridge in layout["bridges"] if bridge.get("name") == trace.get("bridge", {}).get("name"))
    require(len(timeline) == len(reference.get("frames", [])), "V22 WB55 trace timeline length drifted")
    for observed, expected in zip(timeline, reference["frames"]):
        require(observed.get("cue") == expected.get("cue") and
                observed.get("target_pbm") == expected.get("target_pbm") and
                observed.get("target_pbm_sha256") == expected.get("target_pbm_sha256") and
                observed.get("score_duration_ms") == expected.get("duration_ms"),
                "V22 trace replay differs from the registered bridge plan")
    return {"component_count": len(components), "component_mask_hashes": "37_of_37_match",
            "crig": rel(crig), "crig_sha256": sha256(crig), "bridge_count": 10,
            "bridge_frame_count": total_frames, "bridges": bridge_summary,
            "deterministic_trace": {"bridge": reference.get("name"), "frame_count": len(timeline),
                                     "target_pbms_and_hashes_match": True},
            "session_min_post_refresh_hold_ms": router["session_min_post_refresh_hold_ms"]}


def v34_v35_special_gate(profile: dict[str, Any], parity: dict[str, Any], preview: dict[str, Any],
                          source: dict[str, Any]) -> dict[str, Any]:
    require(profile.get("component_count") == 76 and profile.get("score_count") == 4 and
            profile.get("replayed_score_steps") == 12 and
            profile.get("special_event_binding") ==
            "forbidden_until_browser_wb55_component_plan_parity_and_owner_review" and
            profile.get("dream_cloud") == "fail_closed_pending_v9_sleep_profile" and
            profile.get("runtime_resource_activated") is False,
            "V34/V35 inactive profile coverage or fail-closed policy drifted")
    require(parity.get("canvas") == {"width": 200, "height": 200, "stride_bytes": 25} and
            parity.get("source_packs") == ["v22_face", "v34_v35_decoration"] and
            parity.get("component_count") == 76 and parity.get("replayed_frame_count") == 12 and
            parity.get("special_event_binding") == "forbidden_until_owner_review" and
            parity.get("dream_cloud") == "fail_closed_pending_v9_sleep_profile" and
            parity.get("runtime_resource_activated") is False,
            "V34/V35 browser/WB55 component parity drifted")
    require(preview.get("locked_v9_source_sha256") == LOCKED_SHA and
            preview.get("canvas") == {"width": 200, "height": 200, "stride_bytes": 25,
                                      "pixel_format": "1bpp_white_is_one_msb"} and
            preview.get("frame_count") == 12 and
            preview.get("source_score_coverage") == ["recording_input", "bottom_connector_charging",
                                                       "curious_question", "alert_exclamation"] and
            preview.get("runtime_resource_activated") is False and
            preview.get("active_candidate_binding") == "forbidden_until_wb55_component_plan_parity_and_owner_review" and
            preview.get("fail_closed", {}).get("all_special_runtime_binding") ==
            "forbidden_until_total_machine_audit_and_owner_review" and
            preview.get("fail_closed", {}).get("dream_cloud") is None,
            "V34/V35 browser preview provenance or fail-closed policy drifted")
    return {"profile": {"component_count": profile["component_count"], "score_count": profile["score_count"],
                         "replayed_score_steps": profile["replayed_score_steps"]},
            "parity": {"source_packs": parity["source_packs"], "component_count": parity["component_count"],
                       "replayed_frame_count": parity["replayed_frame_count"]},
            "preview": {"frame_count": preview["frame_count"],
                        "source_score_coverage": preview["source_score_coverage"]},
            "source": source,
            "dream_cloud": "fail_closed_pending_v9_sleep_profile"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()

    require(sha256(LOCKED) == LOCKED_SHA, "locked V9 source hash drifted")
    require(sha256(PROTECTED) == PROTECTED_SHA, "protected owner acceptance changed")

    v22 = load(V22_GATE)
    v22_layout = load(V22_LAYOUT)
    v22_trace = load(V22_TRACE)
    v22_router = load(V22_ROUTER)
    require(v22.get("status") == "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE" and
            v22.get("bridge_count") == 10 and v22.get("bridge_frame_count") == 72 and
            v22.get("runtime_resource_activated") is False, "accepted V22 daily regression drifted")
    bridges = v22_layout.get("bridges", [])
    require(v22_layout.get("locked_v9_source_sha256") == LOCKED_SHA and len(bridges) == 10 and
            sum(len(bridge.get("frames", [])) for bridge in bridges) == 72, "V22 bridge coverage drifted")
    require(v22_trace.get("status") == "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT" and
            v22_trace.get("trace_origin") == "synthetic_self_test_no_flash_no_panel" and
            v22_trace.get("bridge", {}).get("frame_count") == 7 and
            v22_trace.get("runtime_resource_activated") is False, "V22 upper-path trace drifted")
    v22_daily_evidence = v22_daily_contract_gate(v22_layout, v22_trace, v22_router)

    v43_gate = evidence(V43_GATE, "PASS_V43_RECORDING_INPUT_INWARD_SOURCE_RUNTIME_INACTIVE")
    v44_layout_gate = evidence(V44_LAYOUT_GATE, "PASS_V44_BLINK_STABLE_CENTER_RUNTIME_INACTIVE")
    v45_source_gate = evidence(V45_SOURCE_GATE, "PASS_V45_COMPLETE_EYE_CLOSURE_PAIR_SOURCE_RUNTIME_INACTIVE")
    profile_evidence = evidence(V45_PROFILE, "PASS_V45_COMPLETE_EYE_WB55_PROFILE_RUNTIME_INACTIVE")
    preview_evidence = evidence(V45_PREVIEW, "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE")
    parity_evidence = evidence(V45_PARITY, "PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE")
    visual_evidence = evidence(V45_VISUAL, "PASS_V45_SINGLE_200X200_BROWSER_VIEWPORT_RUNTIME_INACTIVE")
    touch_evidence = evidence(V45_TOUCH, "PASS_V45_SINGLE_VIEWPORT_TOUCH_SWIPE_REPLAY_RUNTIME_INACTIVE")
    browser_pointer_evidence = evidence(V45_BROWSER_POINTER, "PASS_V45_REAL_BROWSER_POINTER_FAIL_SAFE_RUNTIME_INACTIVE")
    browser_pointer_replay = real_browser_pointer_gate(load(V45_BROWSER_POINTER))
    wall_evidence = evidence(V45_WALL, "PASS_V45_EXPANDED_DYNAMIC_REVIEW_WALL_RUNTIME_INACTIVE")
    v34_profile_evidence = evidence(V34_PROFILE, "PASS_V34_V35_SPECIAL_DECORATION_WB55_PROFILE_RUNTIME_INACTIVE")
    v34_parity_evidence = evidence(V34_PARITY, "PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE")
    v34_preview_evidence = evidence(V34_PREVIEW, "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE")

    special_layout = load(V45_LAYOUT)
    trace = load(V45_TRACE)
    profile = load(V45_PROFILE)
    preview = load(V45_PREVIEW)
    parity = load(V45_PARITY)
    visual = load(V45_VISUAL)
    touch = load(V45_TOUCH)
    wall = load(V45_WALL)
    v34_profile = load(V34_PROFILE)
    v34_parity = load(V34_PARITY)
    v34_preview = load(V34_PREVIEW)
    v34_layout = load(V34_LAYOUT)
    v34_v35_source = v34_v35_source_gate(v34_layout)
    v34_v35_evidence = v34_v35_special_gate(v34_profile, v34_parity, v34_preview, v34_v35_source)
    components = special_layout.get("components", [])
    plan_components = layout_component_map(v22_layout, special_layout)
    blink_eye_geometry = blink_eye_geometry_gate(special_layout, v22_layout)
    special_state_evidence = special_state_machine_gate(special_layout, v22_layout)
    require(special_layout.get("schema") == "companion.v45_complete_eye_special_component_export.v1" and
            len(components) == 60 and special_layout.get("locked_v9_source", {}).get("sha256") == LOCKED_SHA and
            special_layout.get("runtime_resource_activated") is False, "V45 special layout provenance drifted")
    blink_source = special_layout.get("source_sheets", {}).get("blink_transition", {})
    require(blink_source.get("path", "").endswith("attempt-05-complete-eye-width-preserving.png") and
            blink_source.get("sha256") == "07EADF4D5273CAD598631BB8A3D64231101FAA805D3F019DCEEACD54BBBCE007" and
            blink_source.get("ordered_stages") == ["open", "closing", "closed", "opening", "open_return"] and
            blink_source.get("exported_components") == ["left_closing", "right_closing", "left_closed", "right_closed", "left_opening", "right_opening"],
            "V45 complete-eye source provenance drifted")
    for component_id in range(599, 605):
        component = next((item for item in components if int(item.get("component_id", -1)) == component_id), None)
        require(component is not None and
                component.get("source", {}).get("kind") == "imagegen_v45_complete_eye_pair_stage_connected_component_scaled" and
                component.get("source", {}).get("sheet_sha256") == blink_source.get("sha256") and
                component.get("source", {}).get("paired_component_id") in range(599, 605),
                f"V45 complete-eye component {component_id} is not source-registered")
    source_recording = load(V44_LAYOUT).get("source_sheets", {}).get("recording", {})
    require(source_recording.get("wave_direction") == "inward_toward_face_on_left",
            "recording source no longer declares inward wave direction")
    by_id = {int(component["component_id"]): component for component in components}
    require(set((569, 570, 571, 605, 606, 607, 608)).issubset(by_id), "recording input components are missing")
    for component_id in (569, 570, 571):
        component = next(item for item in load(V44_LAYOUT).get("components", []) if int(item.get("component_id")) == component_id)
        require(component.get("source", {}).get("wave_direction") == "inward_toward_face_on_left" and
                component.get("base_position", [0, 0])[0] >= 160 and
                component.get("base_position", [0, 0])[0] + component.get("mask_size", [0, 0])[0] <= 196,
                f"recording component {component_id} escaped the inward right-side safe zone")
    recording_split = special_layout.get("source_sheets", {}).get("recording_input_split", {})
    require(recording_split == {
        "source_component_ids": [569, 570, 571],
        "derived_component_ids": [605, 606, 607, 608],
        "microphone_component_id": 605,
        "waveform_component_ids": [606, 607, 608],
        "source_derived_without_new_image_generation": True,
    }, "recording input split provenance drifted")
    microphone = by_id[605]
    require(microphone.get("anchor_revision", {}).get("kind") == "v45_recording_fixed_microphone_anchor" and
            microphone.get("base_position") == [177, 116] and
            microphone.get("offset_range") == {"min": [0, 0], "max": [0, 0]},
            "recording microphone is not fixed at the registered source anchor")
    microphone_pixels = positioned_pixels(microphone)
    for component_id in (606, 607, 608):
        waveform = by_id[component_id]
        require(waveform.get("anchor_revision", {}).get("kind") == "v45_recording_waveform_anchor" and
                not (positioned_pixels(waveform) & microphone_pixels),
                f"recording waveform {component_id} is not a separate non-overlapping source component")

    require(trace.get("schema") == "companion.v45_complete_eye_expression_extension_wb55_target_profile_plan.v1" and
            trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED_SHA and
            trace.get("component_sources") == {"v22_face": 37, "v45_special_source": 60} and
            trace.get("runtime_resource_activated") is False and
            trace.get("active_candidate_binding") == "forbidden_until_v45_machine_audit_and_owner_review",
            "V45 target trace provenance or inactive boundary drifted")
    require(profile.get("component_count") == 97 and profile.get("expression_track_count") == 15 and
            profile.get("functional_track_count") == 4 and profile.get("story_count") == 21 and
            profile.get("preview_frame_count") == 93 and profile.get("five_gaze_states") == ["center", "left", "right", "up", "down"] and
            profile.get("recording_input_clear_of_face") is True and profile.get("wireless_dock_charging") is True and
            profile.get("sleep_zzz_only") is True and
            profile.get("fail_closed") == {"invalid_functional_track": True, "invalid_functional_step": True,
                                            "missing_source_pose": True, "generic_menu_synthesis": True},
            "V45 WB55 profile evidence drifted")
    require(parity.get("component_count") == 97 and parity.get("replayed_frame_count") == 93 and
            parity.get("source_packs") == ["v22_face", "v45_special_source"], "V45 browser/WB55 parity drifted")

    scores = trace.get("scores", [])
    require(isinstance(scores, list) and len(scores) == 21 and sum(len(score.get("steps", [])) for score in scores) == 93,
            "V44 score coverage drifted")
    functional_evidence = functional_track_gate(trace)
    choreography_evidence = fixed_nose_and_choreography_gate(trace, v22_layout, special_layout)
    wall_geometry = expanded_review_wall_gate(wall, preview)
    calm = next((score for score in scores if score.get("name") == "calm_presence"), None)
    require(calm is not None and len(calm.get("steps", [])) == 5 and
            trace.get("blink_choreography") == {
                "source": "registered_complete_eye_components_599_to_604",
                "schedule": "deterministic_human_like",
                "open_interval_ms": 6800,
                "closing_ms": 140,
                "closed_ms": 120,
                "opening_ms": 150,
                "cycle_ms": 7430,
                "random_facial_motion": False,
            },
            "V45 calm blink track is missing")
    calm_steps = calm["steps"]
    require([step.get("duration_ms") for step in calm_steps] == [220, 140, 120, 150, 6800],
            "V45 calm blink timing drifted")
    calm_transition_ids = [sorted(layer.get("component_id") for layer in step.get("layers", []) if 599 <= layer.get("component_id", -1) <= 604)
                           for step in calm_steps]
    require(calm_transition_ids == [[], [599, 600], [601, 602], [603, 604], []],
            "V45 calm blink does not use open->closing->closed->opening->open source components")
    trace_frames = [frame_key({"score": score.get("name"), **step}) for score in scores for step in score.get("steps", [])]
    trace_layer_plans = [canonical_trace_layers(step.get("layers", []), plan_components)
                         for score in scores for step in score.get("steps", [])]
    preview_frames = preview.get("frames", [])
    parity_frames = parity.get("frames", [])
    require([frame_key(frame) for frame in preview_frames] == trace_frames and
            [frame_key(frame) for frame in parity_frames] == [frame_key(frame) for frame in preview_frames] and
            [[plan_layer_key(layer) for layer in frame.get("layers", [])] for frame in preview_frames] == trace_layer_plans and
            [[plan_layer_key(layer) for layer in frame.get("layers", [])] for frame in parity_frames] == trace_layer_plans,
            "browser/WB55 replay plan differs in component id, pack, anchor, offset, composite operation, phase or duration")
    hidden = {name for name in preview.get("source_score_coverage", []) if name in GAZE}
    require(hidden == GAZE and preview.get("viewport_contract", {}).get("owner_visible_story_count") == 16,
            "V44 internal gaze regression scope drifted")

    html_path = ROOT / str(preview.get("dynamic_preview", {}).get("html", ""))
    require(html_path.is_file(), "V44 single viewport HTML is missing")
    html = html_path.read_text(encoding="utf-8")
    require('data-review-revision="v45-touch-failsafe-r7"' in html and 'Touch fail-safe r7' in html and
            html.count('id="epaper-screen"') == 1 and html.count('data-canvas="200x200"') == 1 and
            html.count('data-touch-surface="true"') == 1 and "<canvas" not in html.lower() and
            "performance-card" not in html and "表情与状态总览" not in html and
            all(name not in html for name in GAZE) and
            all(marker in html for marker in ("showTouch", "touchCache", "loadAsset", "baseSrc", "overlay", "mousedown", "mousemove", "mouseup", "dragstart", "draggable=\"false\"", "preventDefault")) and
            ("touchRequest" in html or "renderRequest" in html) and
            ("presentBase" in html or "image.onerror" in html),
            "V44 owner HTML exposes a forbidden fallback or hidden gaze story")
    require(visual.get("viewport", {}).get("owner_visible_story_count") == 16 and
            visual.get("viewport", {}).get("touch_surface") == "the_200x200_viewport_itself" and
            touch.get("canvas") == "200x200" and touch.get("random_selection") is False,
            "V44 single viewport visual/touch evidence drifted")

    menu = next(score for score in scores if score.get("name") == "menu_entry_notice")
    require(menu.get("withdraw_all_tracks_after_last_cue") is True and
            sum(step.get("duration_ms", 0) for step in menu.get("steps", [])) <= 500,
            "Menu entry cue is not finite before Menu UI ownership")
    require(all("no_whole_face_card" in item for item in [trace.get("non_claims", [])]),
            "V44 trace no-whole-face boundary missing")

    review = load(V45_REVIEW)
    review_note = V45_REVIEW_NOTE.read_text(encoding="utf-8").strip() if V45_REVIEW_NOTE.is_file() else ""
    require(review.get("selected") == "通过" and "眨眼" in review_note and "搁置" in review_note,
            "V45 prior owner review does not preserve the blink deferral note")
    r4_review = load(V45_R4_REVIEW)
    r4_note = V45_R4_REVIEW_NOTE.read_text(encoding="utf-8").strip() if V45_R4_REVIEW_NOTE.is_file() else ""
    require(r4_review.get("selected") == "需修改" and r4_note == "还是一按下表情就消失了",
            "V45 r4 touch rejection is missing or was overwritten")
    r5_review = load(V45_R5_REVIEW)
    r5_note = V45_R5_REVIEW_NOTE.read_text(encoding="utf-8").strip() if V45_R5_REVIEW_NOTE.is_file() else ""
    require(r5_review.get("selected") == "需修改" and
            r5_review.get("text") == "还是一样的现象" and
            r5_note == "还是按下就消失",
            "V45 r5 touch rejection is missing or was overwritten")

    output = {
        "schema": "companion.v45_total_machine_audit.v1",
        "status": "PASS_MACHINE_CLOSED_PENDING_V45_R7_REVIEW",
        "runtime_resource_activated": False,
        "authority": ["COMP-REQ-093", "COMP-REQ-250", "COMP-REQ-253", "COMP-REQ-256", "COMP-REQ-258", "COMP-REQ-261", "COMP-REQ-262", "COMP-REQ-263", "COMP-REQ-267", "COMP-REQ-269", "COMP-REQ-276", "COMP-REQ-279", "COMP-REQ-282", "COMP-REQ-283", "COMP-REQ-284", "COMP-REQ-286", "COMP-REQ-287", "COMP-REQ-288", "COMP-REQ-290", "COMP-REQ-294"],
        "protected": {"locked_v9_source": {"path": rel(LOCKED), "sha256": LOCKED_SHA},
                      "prior_owner_acceptance": {"path": rel(PROTECTED), "sha256": PROTECTED_SHA}},
        "accepted_v22_daily_regression": {"artifact": rel(V22_GATE), "bridge_count": 10, "bridge_frame_count": 72,
                                           "trace_artifact": rel(V22_TRACE), "router_artifact": rel(V22_ROUTER),
                                           "contract_gate": v22_daily_evidence},
        "v45_evidence": {"recording_source_gate": v43_gate, "inherited_v44_layout_gate": v44_layout_gate,
                          "complete_eye_source_gate": v45_source_gate,
                          "special_state_source_collision_gate": special_state_evidence,
                          "blink_eye_geometry_gate": blink_eye_geometry,
                          "functional_track_gate": functional_evidence,
                          "fixed_nose_and_choreography_gate": choreography_evidence,
                          "profile_host": profile_evidence, "browser_preview": preview_evidence,
                          "wb55_pixel_parity": parity_evidence, "single_viewport_visual": visual_evidence,
                          "real_browser_pointer_fail_safe": browser_pointer_evidence,
                          "real_browser_pointer_replay": browser_pointer_replay,
                          "v34_v35_special_decorations": {"profile": v34_profile_evidence,
                                                            "browser_preview": v34_preview_evidence,
                                                            "wb55_pixel_parity": v34_parity_evidence,
                                                            "machine_gate": v34_v35_evidence},
                          "touch_swipe_host": touch_evidence, "expanded_review_wall": wall_evidence},
        "machine_verified": {"canvas": "200x200_1bpp", "v22_daily_regression": v22_daily_evidence,
                             "component_count": 97, "special_component_count": 60,
                             "story_count": 21, "preview_frame_count": 93, "owner_visible_story_count": 16,
                             "source_packs": ["v22_face", "v45_special_source"], "recording_wave": "inward_toward_face_on_left",
                             "recording_face_pixel_overlap": special_state_evidence["event_groups"]["recording_input"]["face_pixel_overlap"],
                             "wireless_dock_face_pixel_overlap": special_state_evidence["event_groups"]["wireless_dock_charge"]["face_pixel_overlap"],
                             "idle_gaze": "stable_center", "blink_machine_choreography": True,
                             "blink_timing": trace["blink_choreography"],
                             "blink_eye_geometry": blink_eye_geometry,
                             "fixed_nose_and_choreography": choreography_evidence,
                             "fail_closed": profile["fail_closed"],
                             "expanded_review_wall": wall_geometry,
                             "blink_visual_human_acceptance": False, "blink_disposition": "PENDING_NEW_REVIEW_AFTER_TIMING_REVISION",
                             "touch": "pointer_coordinate_to_registered_highlight_and_sparkle; release_center",
                             "real_browser_pointer_fail_safe": True,
                             "real_browser_pointer_replay": browser_pointer_replay,
                             "v34_v35_special_decorations": v34_v35_evidence,
                             "swipe": "horizontal_or_vertical; positive_next_negative_previous",
                             "runtime_resource_activated": False},
        "human_review": {"historical_artifact": rel(V45_REVIEW), "historical_note": rel(V45_REVIEW_NOTE),
                          "historical_selected": review.get("selected"),
                          "historical_disposition": "SUPERSEDED_BY_COMP_REQ_282_TIMING_AND_COMP_REQ_283_284_REVIEW_REVISIONS",
                          "r4_artifact": rel(V45_R4_REVIEW), "r4_note": rel(V45_R4_REVIEW_NOTE),
                          "r4_selected": r4_review.get("selected"),
                          "r4_disposition": "REJECTED_COMP_REQ_290_REAL_BROWSER_TOUCH_FAIL_SAFE",
                          "r5_artifact": rel(V45_R5_REVIEW), "r5_note": rel(V45_R5_REVIEW_NOTE),
                          "r5_selected": r5_review.get("selected"),
                          "r5_disposition": "REJECTED_PRESERVED_ORDERED_TOUCH_FAILURE",
                          "current_review": "not_started_after_r7_real_browser_pixel_fail_safe_fix", "note_is_dispositive_for_touch_fix": True},
        "non_claims": ["no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_physical_screen_acceptance", "no_blink_visual_acceptance"],
        "human_boundary": "The prior canonical Chinese reviews remain preserved. r4 and r5 rejected the real touch behavior; this machine-closed r7 real-browser pixel fail-safe revision requires a new canonical Chinese review before promotion and remains separate from physical panel acceptance.",
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V45 total machine audit closes complete-eye source lineage, human-like deterministic blink timing, single viewport, touch/swipe replay, and WB55 parity ({destination}); r7 touch review is pending.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
