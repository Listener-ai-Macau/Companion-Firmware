#!/usr/bin/env python3
"""Gate V21 everyday emotion bridges as directed, component-only browser/target candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

from render_companion_v21_everyday_emotion_component_bridges import (
    BRIDGE_EDGES, EMOTIONS, PRIMARY_HIGHLIGHT_NAMES, SPARKLE_NAMES,
)


ROOT = Path(__file__).resolve().parents[1]
V21_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source"
SOURCE_OUTPUT = V21_ROOT / "candidate/component-export-attempt-01"
SOURCE_LAYOUT = SOURCE_OUTPUT / "everyday-emotion-component-layout.json"
COMPONENT_GATE = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-component-export-gate-20260719.json"
OUTPUT = V21_ROOT / "candidate/component-bridge-v2"
LAYOUT = OUTPUT / "component-bridge-layout.json"
RENDER_REPORT = OUTPUT / "bridge-render-report.json"
CAPTURE_REPORT = OUTPUT / "browser-capture-report.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v21-everyday-emotion-component-bridge-v2-gate-20260719.json"
PROHIBITED = {
    "whole-source-pose playback", "whole-face replacement", "CEMP flipbook playback", "CRIG export",
    "runtime activation", "random emotion playlist", "menu recording upgrade binding",
    "sleep charging error fallback", "code-drawn facial pixels",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def frame_layers(frame: dict[str, Any]) -> dict[str, dict[str, Any]]:
    layers = frame.get("layers", [])
    return {str(layer.get("component")): layer for layer in layers if isinstance(layer, dict)}


def changed_components(left: dict[str, Any], right: dict[str, Any]) -> set[str]:
    left_layers, right_layers = frame_layers(left), frame_layers(right)
    names = set(left_layers) | set(right_layers)
    changed: set[str] = set()
    for name in names:
        if left_layers.get(name) != right_layers.get(name):
            changed.add(name)
    return changed


def browser_payload(preview: Path, errors: list[str]) -> dict[str, Any] | None:
    text = preview.read_text(encoding="utf-8")
    match = re.search(r"const data=(\{.*\});\nconst scale=", text, flags=re.DOTALL)
    add(errors, match is not None, "browser preview has no registered component plan payload")
    if match is None:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as error:
        errors.append(f"browser component plan JSON is invalid: {error}")
        return None


def expected_browser_bridges(bridges: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, bridge in bridges.items():
        result[key] = {
            field: value for field, value in bridge.items()
            if field not in {"target_reassembly", "final_target_pixel_distance", "contact_sheet"}
        }
        result[key]["frames"] = [
            {field: value for field, value in frame.items() if field not in {"target_pbm", "target_pbm_sha256"}}
            for frame in bridge["frames"]
        ]
    return result


def check_frame_asset(frame: dict[str, Any], errors: list[str], label: str) -> Image.Image | None:
    path_value = frame.get("target_pbm")
    path = ROOT / str(path_value)
    add(errors, path.is_file(), f"{label} PBM is missing")
    if not path.is_file():
        return None
    add(errors, path.suffix.lower() == ".pbm", f"{label} target asset is not PBM")
    add(errors, sha256(path) == frame.get("target_pbm_sha256"), f"{label} PBM hash drifted")
    with Image.open(path) as raw:
        image = raw.convert("1")
    add(errors, image.size == (200, 200), f"{label} PBM dimensions drifted")
    return image


def pixel_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.getdata(), right.getdata()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    errors: list[str] = []
    component_gate = load_json(COMPONENT_GATE)
    source_layout = load_json(SOURCE_LAYOUT)
    layout = load_json(LAYOUT)
    render_report = load_json(RENDER_REPORT)
    capture = load_json(CAPTURE_REPORT)

    add(errors, component_gate.get("status") == "PASS_V21_EVERYDAY_EMOTION_COMPONENT_EXPORT_GATE",
        "V21 component export gate is not PASS")
    add(errors, source_layout.get("status") == "UNBOUND_ACCEPTED_SOURCE_PENDING_COMPONENT_BRIDGE_GATE" and
        source_layout.get("runtime_resource_activated") is False and source_layout.get("active_candidate_binding") == "forbidden",
        "V21 source layout is not an inactive unbound component candidate")
    add(errors, layout.get("status") == "CANDIDATE_MACHINE_BRIDGE_GATE_PENDING",
        "V21 bridge layout is not pending its machine gate")
    add(errors, layout.get("source_component_layout") == SOURCE_LAYOUT.relative_to(ROOT).as_posix() and
        layout.get("source_component_layout_sha256") == sha256(SOURCE_LAYOUT),
        "V21 bridge lost its source component layout lineage")
    add(errors, render_report.get("status") == "PASS_V21_COMPONENT_ONLY_EMOTION_BRIDGE_RESEARCH_REFINED_CANDIDATE",
        "V21 bridge renderer report is not PASS")
    add(errors, layout.get("runtime_resource_activated") is False and
        layout.get("active_candidate_binding") == "forbidden" and
        render_report.get("runtime_resource_activated") is False and
        render_report.get("active_candidate_binding") == "forbidden",
        "V21 bridge candidate must remain runtime inactive and unbound")
    add(errors, PROHIBITED <= set(layout.get("prohibited", [])), "V21 bridge prohibition contract drifted")
    refinement = layout.get("research_refinement", {})
    add(errors, refinement.get("event_to_primary_highlight_lead_ms") == 680 and
        refinement.get("temporal_shape") == ["onset", "apex", "offset"] and
        refinement.get("automatic_reverse") == "forbidden",
        "V21 research-refined timing contract drifted")
    add(errors, not list(OUTPUT.rglob("*.crig")) and not list(OUTPUT.rglob("*.cemp")),
        "V21 bridge output must not contain runtime pack or CEMP playback assets")

    expected_edges = {(source, target, event) for source, target, event, _ in BRIDGE_EDGES}
    actual_edges = {(item.get("source"), item.get("target"), item.get("event")) for item in layout.get("directed_edges", [])}
    add(errors, actual_edges == expected_edges, "V21 directed affect graph drifted")
    affect_nodes = layout.get("affect_core", {}).get("nodes", {})
    add(errors, set(affect_nodes) == set(EMOTIONS), "V21 affect node vocabulary drifted")
    bridges = layout.get("bridges", {})
    expected_keys = {f"{source}__{target}" for source, target, _, _ in BRIDGE_EDGES}
    add(errors, set(bridges) == expected_keys, "V21 bridge set does not exactly match the legal graph")

    source_components = {
        **source_layout.get("identity_components", {}),
        **{name: record for state in source_layout.get("emotion_components", {}).values() for name, record in state.items()},
    }
    components = layout.get("components", {})
    add(errors, set(components) == set(source_components), "V21 bridge component catalog drifted from source export")
    for name, record in components.items():
        source = source_components.get(name, {})
        add(errors, record.get("mask") == source.get("mask") and record.get("mask_sha256") == source.get("mask_sha256") and
            record.get("source") == source.get("source"), f"{name} is not an exact source component reference")
        browser_layer = OUTPUT / "component-layers" / str(record.get("browser_layer", ""))
        add(errors, browser_layer.is_file() and sha256(browser_layer) == record.get("browser_layer_sha256"),
            f"{name} browser layer drifted")
        add(errors, str(record.get("mask", "")).endswith(".pbm"), f"{name} is not a source PBM mask")

    bridge_metrics: list[dict[str, Any]] = []
    for key, bridge in bridges.items():
        source, target = str(bridge.get("source")), str(bridge.get("target"))
        frames = bridge.get("frames", [])
        accent_edge = source == "playful" or target == "playful"
        expected_cues = ["source_hold", "primary_highlight_lead", "sparkle_arrive", "brow_apex", "lower_face_apex"]
        if accent_edge:
            expected_cues.append("accent_resolve")
        expected_cues.extend(["target_hold", "highlight_settle"])
        add(errors, [frame.get("cue") for frame in frames] == expected_cues, f"{key} causal cue sequence drifted")
        add(errors, bridge.get("policy") == "primary highlights lead; sparkles follow; brows and lower face reach apex; approved accent resolves last; highlights settle at target",
            f"{key} bridge policy drifted")
        images: list[Image.Image] = []
        for index, frame in enumerate(frames):
            duration = frame.get("duration_ms")
            add(errors, isinstance(duration, int) and 120 <= duration <= 2000,
                f"{key} frame {index} duration is outside component-motion bounds")
            if frame.get("cue") == "source_hold":
                add(errors, duration == 680, f"{key} event response latency drifted")
            layers = frame_layers(frame)
            add(errors, len(layers) == len(frame.get("layers", [])), f"{key} frame {index} duplicates a component layer")
            add(errors, set(layers) <= set(components), f"{key} frame {index} references an unregistered component")
            for layer in layers.values():
                component = components.get(layer.get("component"), {})
                offset = layer.get("offset")
                offset_range = component.get("offset_range", {})
                add(errors, isinstance(offset, list) and len(offset) == 2 and
                    offset_range.get("min", [999, 999])[0] <= offset[0] <= offset_range.get("max", [-999, -999])[0] and
                    offset_range.get("min", [999, 999])[1] <= offset[1] <= offset_range.get("max", [-999, -999])[1],
                    f"{key} frame {index} places {layer.get('component')} outside a legal offset")
            image = check_frame_asset(frame, errors, f"{key} frame {index}")
            if image is not None:
                images.append(image)
        if len(frames) >= 5:
            first, primary, sparkle, brows, lower = frames[:5]
            primary_changes = changed_components(first, primary)
            add(errors, primary_changes and primary_changes <= PRIMARY_HIGHLIGHT_NAMES,
                f"{key} primary highlight lead changes something other than registered primary highlights")
            sparkle_changes = changed_components(primary, sparkle)
            add(errors, sparkle_changes and sparkle_changes <= SPARKLE_NAMES,
                f"{key} sparkle arrival changes something other than registered sparkles")
            brow_changes = changed_components(sparkle, brows)
            add(errors, brow_changes and all(components[name].get("role") == "left_brow" or
                components[name].get("role") == "right_brow" for name in brow_changes),
                f"{key} brow apex changes non-brow components")
            lower_changes = changed_components(brows, lower)
            add(errors, lower_changes and all(components[name].get("role") in {"left_cheek", "right_cheek", "mouth", "left_brow", "right_brow"}
                for name in lower_changes), f"{key} lower-face apex changes an illegal group")
            if accent_edge:
                accent_frame = frames[5]
                accent_changes = changed_components(lower, accent_frame)
                add(errors, accent_changes and any(components[name].get("role") == "accent" for name in accent_changes),
                    f"{key} approved accent does not resolve last")
        if images:
            target_reassembly = ROOT / str(bridge.get("target_reassembly"))
            add(errors, target_reassembly.is_file(), f"{key} target reassembly is missing")
            if target_reassembly.is_file():
                with Image.open(target_reassembly) as target_image:
                    distance = pixel_distance(images[-1], target_image.convert("1"))
                add(errors, distance == 0 and bridge.get("final_target_pixel_distance") == 0,
                    f"{key} final target does not match source-component reassembly")
            changes = [pixel_distance(images[index - 1], image) for index, image in enumerate(images) if index]
            add(errors, all(change > 0 for change in changes), f"{key} contains a static card-like adjacent sample")
            bridge_metrics.append({"bridge": key, "frame_count": len(frames), "adjacent_pixel_changes": changes})

    preview = ROOT / str(layout.get("browser_preview", ""))
    add(errors, preview.is_file(), "V21 browser preview is missing")
    payload = browser_payload(preview, errors) if preview.is_file() else None
    if payload is not None:
        add(errors, payload.get("bridges") == expected_browser_bridges(bridges) and payload.get("components") == components,
            "browser preview is not using the exact registered component sample plan")
        preview_text = preview.read_text(encoding="utf-8")
        add(errors, "bridge-frames-200x200" not in preview_text and
            "attempt-01-generated-everyday-emotion-distinction.png" not in preview_text and
            "reverse=" not in preview_text and
            payload.get("browser_rendering") == "registered_component_dom_layers_only",
            "browser preview references a complete pose/target PBM frame or reverses without an event")

    add(errors, capture.get("status") == "PASS_V21_COMPONENT_EMOTION_BRIDGE_BROWSER_CAPTURE_RESEARCH_REFINED" and
        capture.get("source_emotion") == "calm" and capture.get("target_emotion") == "curious" and
        capture.get("browser_rendering") == "registered_component_dom_layers_only",
        "V21 browser capture evidence is missing or drifted")
    if preview.is_file():
        add(errors, capture.get("preview_sha256") == sha256(preview), "browser capture does not match current preview")
    browser_diffs = capture.get("source_hold_pixel_differences", {})
    thresholds = {
        "primary_highlight_lead": 80, "sparkle_arrive": 120, "brow_apex": 300,
        "lower_face_apex": 450, "target_hold": 550, "highlight_settle": 550, "target_persistent": 550,
    }
    add(errors, set(browser_diffs) == set(thresholds) and all(
        isinstance(browser_diffs.get(name), int) and browser_diffs[name] >= minimum
        for name, minimum in thresholds.items()),
        "browser capture lacks visible component choreography")
    add(errors, capture.get("settle_to_target_persistent_pixel_difference") == 0,
        "browser bridge automatically reverses or mutates after target settle")

    result = {
        "schema": "companion.v21_everyday_emotion_component_bridge_gate.v2",
        "status": "PASS_V21_EVERYDAY_EMOTION_COMPONENT_BRIDGE_V2_GATE" if not errors else
                  "FAIL_V21_EVERYDAY_EMOTION_COMPONENT_BRIDGE_V2_GATE",
        "component_export_gate": COMPONENT_GATE.relative_to(ROOT).as_posix(),
        "layout": LAYOUT.relative_to(ROOT).as_posix(),
        "browser_capture": CAPTURE_REPORT.relative_to(ROOT).as_posix(),
        "legal_directed_bridge_count": len(bridges),
        "bridge_metrics": bridge_metrics,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "screen_review": "pending_research_refined_machine_bridge_gate",
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V21 research-refined affect bridges are directed, source-component-only and browser/target-plan identical.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
