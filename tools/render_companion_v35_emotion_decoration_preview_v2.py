#!/usr/bin/env python3
"""Render V35 revision-2 component-only emotion-decoration choreography."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from render_companion_v9_expression_rig import (
    State,
    clamp_offset,
    component_offsets,
    load_rig,
    paste_component,
    selected_components,
)


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
RIG_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/request-v2.json"
SOURCES = {
    "curious_question": ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate-curious-question-v2.png",
    "alert_exclamation": ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate-alert-exclamation-v2.png",
    "sleepy_dream_cloud": ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate-sleepy-dream-cloud-v2.png",
}
SAFE_INSET_PX = 8
HIGHLIGHT_ROLES = {"left_highlight", "right_highlight"}
EYE_ROLES = {"left_eye", "right_eye", "left_highlight", "right_highlight", "left_sparkle", "right_sparkle"}
BROW_ROLES = {"left_brow", "right_brow"}
MOUTH_CHEEK_ROLES = {"mouth", "left_cheek", "right_cheek"}
STAGE_CHANNELS = {
    "source_hold": set(),
    "highlight_lead": {"left_highlight"},
    "paired_highlight_arrive": HIGHLIGHT_ROLES,
    "brow_answer": HIGHLIGHT_ROLES | BROW_ROLES,
    "mouth_cheek_reply": HIGHLIGHT_ROLES | BROW_ROLES | MOUTH_CHEEK_ROLES,
    "target_face_settle": HIGHLIGHT_ROLES | BROW_ROLES | MOUTH_CHEEK_ROLES | EYE_ROLES,
    "decoration_follow_through": HIGHLIGHT_ROLES | BROW_ROLES | MOUTH_CHEEK_ROLES | EYE_ROLES,
    "decoration_arrive": HIGHLIGHT_ROLES | BROW_ROLES | MOUTH_CHEEK_ROLES | EYE_ROLES,
    "target_hold": HIGHLIGHT_ROLES | BROW_ROLES | MOUTH_CHEEK_ROLES | EYE_ROLES,
}
TRANSITION_STAGES = [
    "source_hold",
    "highlight_lead",
    "paired_highlight_arrive",
    "brow_answer",
    "mouth_cheek_reply",
    "target_face_settle",
    "decoration_follow_through",
    "decoration_arrive",
    "target_hold",
]
TRANSITION_DURATIONS = [760, 150, 150, 170, 190, 180, 160, 240, 960]
PRESENCE_STAGES = [
    "target_hold",
    "highlight_lead",
    "paired_highlight_arrive",
    "brow_answer",
    "mouth_cheek_reply",
    "target_hold",
]
PRESENCE_DURATIONS = [900, 150, 150, 170, 190, 1100]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def make_state(name: str, scene: str, emotion: str, attention: str, energy: str) -> State:
    return State(name, scene, emotion, attention, energy, 0, "sustain")


EVENTS = {
    "curious_question": {
        "source": "curious_question",
        "source_state": make_state("calm_source", "daily", "calm", "center", "normal"),
        "target_state": make_state("curious_target", "daily", "curious", "right", "normal"),
        "micro_state": make_state("curious_micro", "daily", "curious", "up", "normal"),
        "placements": [(148, 38, 14, 20), (145, 34, 17, 24), (142, 29, 20, 28)],
        "presence_positions": [(142, 29, 20, 28), (143, 31, 19, 27), (145, 34, 17, 24), (145, 34, 17, 24), (143, 31, 19, 27), (142, 29, 20, 28)],
        "mouth_extra": (0, -1),
    },
    "alert_exclamation": {
        "source": "alert_exclamation",
        "source_state": make_state("calm_source", "daily", "calm", "center", "normal"),
        "target_state": make_state("alert_target", "daily", "focused", "up", "high"),
        "micro_state": make_state("alert_micro", "daily", "focused", "right", "high"),
        "placements": [(99, 42, 7, 18), (96, 35, 10, 26), (94, 25, 13, 34)],
        "presence_positions": [(94, 25, 13, 34), (95, 28, 12, 31), (96, 35, 10, 26), (96, 35, 10, 26), (95, 28, 12, 31), (94, 25, 13, 34)],
        "mouth_extra": (0, 1),
    },
    "sleepy_dream_cloud": {
        "source": "sleepy_dream_cloud",
        "source_state": make_state("calm_source", "daily", "calm", "center", "normal"),
        "target_state": make_state("sleepy_target", "sleep", "sleepy", "center", "low"),
        "micro_state": make_state("sleepy_micro", "sleep", "sleepy", "left", "low"),
        "placements": [(40, 41, 23, 16), (33, 35, 30, 22), (27, 30, 38, 27)],
        "presence_positions": [(27, 30, 38, 27), (29, 32, 36, 26), (33, 35, 30, 22), (33, 35, 30, 22), (29, 32, 36, 26), (27, 30, 38, 27)],
        "mouth_extra": (0, 1),
    },
}


def source_masks(path: Path) -> list[Image.Image]:
    image = Image.open(path).convert("L")
    width = image.width // 3
    masks: list[Image.Image] = []
    for index in range(3):
        cell = image.crop((index * width, 0, (index + 1) * width if index < 2 else image.width, image.height))
        mask = cell.point(lambda value: 255 if value < 128 else 0, mode="L")
        bbox = mask.getbbox()
        if bbox is None:
            raise ValueError(f"{path.name} source cell {index} has no ink")
        masks.append(mask.crop(bbox))
    return masks


def resize_mask(mask: Image.Image, width: int, height: int) -> Image.Image:
    return mask.resize((width, height), Image.Resampling.LANCZOS).point(
        lambda value: 255 if value >= 128 else 0, mode="L")


def charmless_components(rig, state: State) -> dict[str, object]:
    components = {}
    for component in selected_components(rig, state):
        if component.role == "charm":
            continue
        if component.role in components:
            raise ValueError(f"duplicate V9 component role {component.role}")
        components[component.role] = component
    return components


def target_component_roles(stage: str) -> set[str]:
    if stage not in STAGE_CHANNELS:
        raise ValueError(f"unknown choreography stage {stage}")
    return STAGE_CHANNELS[stage]


def render_stage(rig, source_images: dict[str, Image.Image], base_state: State, target_state: State,
                 stage: str, mouth_extra: tuple[int, int] = (0, 0)) -> tuple[Image.Image, list[dict[str, object]]]:
    base = charmless_components(rig, base_state)
    target = charmless_components(rig, target_state)
    target_roles = target_component_roles(stage)
    canvas = Image.new("1", (200, 200), 1)
    layers: list[dict[str, object]] = []
    for role in sorted(set(base) | set(target), key=lambda item: (
            (target.get(item) or base.get(item)).z_index, item)):
        use_target = role in target_roles
        if use_target and role not in target:
            if "left_eye" in target_roles:
                # The target eye variant is now installed, so its absent open-eye highlight retires.
                continue
            # Before an eye-variant change settles, retain the inherited V9 highlight.
            component = base.get(role)
            state = base_state
        else:
            component = target[role] if use_target else base.get(role)
            state = target_state if use_target else base_state
        if component is None:
            continue
        offset = component_offsets(state, component)
        if role == "mouth" and use_target:
            offset = (offset[0] + mouth_extra[0], offset[1] + mouth_extra[1])
        record = paste_component(canvas, source_images[component.source_frame], component,
                                 clamp_offset(component, offset))
        layers.append(record)
    if any(layer["role"] == "charm" for layer in layers):
        raise ValueError("V35 base must select no inherited charm component")
    return canvas, layers


def compose(base: Image.Image, mask: Image.Image | None,
            placement: tuple[int, int, int, int] | None) -> Image.Image:
    canvas = base.copy()
    if mask is not None and placement is not None:
        x, y, width, height = placement
        if x < SAFE_INSET_PX or y < SAFE_INSET_PX or x + width > 200 - SAFE_INSET_PX or y + height > 200 - SAFE_INSET_PX:
            raise ValueError(f"decoration exceeds native V35 safe area: {placement}")
        canvas.paste(0, (x, y), resize_mask(mask, width, height))
    return canvas


def save_sequence(output_dir: Path, name: str, frames: list[Image.Image], durations: list[int],
                  layer_records: list[list[dict[str, object]]], stages: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, frame in enumerate(frames):
        png_path = output_dir / f"{name}-{index:02d}.png"
        pbm_path = output_dir / f"{name}-{index:02d}.pbm"
        frame.save(png_path)
        frame.save(pbm_path)
        records.append({
            "frame": index,
            "stage": stages[index],
            "png": str(png_path.relative_to(ROOT)).replace("\\", "/"),
            "pbm": str(pbm_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(png_path),
            "duration_ms": durations[index],
            "v9_layers": layer_records[index],
        })
    frames[0].save(output_dir / f"{name}.gif", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2)
    return records


def contact_sheet(groups: list[list[Image.Image]], output_path: Path) -> None:
    width = max(len(group) for group in groups) * 200
    sheet = Image.new("1", (width, len(groups) * 200), 1)
    for row, frames in enumerate(groups):
        for column, frame in enumerate(frames):
            sheet.paste(frame, (column * 200, row * 200))
    sheet.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate/review-v2")
    parser.add_argument("--report", default="docs/validation/companion-v35-emotion-decoration-native-200-v2-render-20260720.json")
    args = parser.parse_args()
    if not LOCKED_V9.is_file() or sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        raise ValueError("locked V9 source is missing or drifted")
    if not REQUEST.is_file() or not all(path.is_file() for path in SOURCES.values()):
        raise ValueError("V35 revision-2 request or generated source is missing")
    rig = load_rig(RIG_LAYOUT)
    source_images = {name: Image.open(frame.path).convert("1") for name, frame in rig.sources.items()}
    masks = {name: source_masks(path) for name, path in SOURCES.items()}
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_events: dict[str, object] = {}
    contact_groups: list[list[Image.Image]] = []

    for name, definition in EVENTS.items():
        transition_frames: list[Image.Image] = []
        transition_layers: list[list[dict[str, object]]] = []
        for index, stage in enumerate(TRANSITION_STAGES):
            base, layers = render_stage(rig, source_images, definition["source_state"], definition["target_state"], stage,
                                        definition["mouth_extra"] if stage == "mouth_cheek_reply" else (0, 0))
            decoration = None if index < 6 else masks[definition["source"]][index - 6]
            placement = None if index < 6 else definition["placements"][index - 6]
            transition_frames.append(compose(base, decoration, placement))
            transition_layers.append(layers)

        presence_frames: list[Image.Image] = []
        presence_layers: list[list[dict[str, object]]] = []
        for index, stage in enumerate(PRESENCE_STAGES):
            base, layers = render_stage(rig, source_images, definition["target_state"], definition["micro_state"], stage,
                                        definition["mouth_extra"] if stage == "mouth_cheek_reply" else (0, 0))
            decoration_index = 2 if index in {0, 5} else 1
            presence_frames.append(compose(base, masks[definition["source"]][decoration_index],
                                           definition["presence_positions"][index]))
            presence_layers.append(layers)

        report_events[name] = {
            "transition": save_sequence(output_dir, f"calm-to-{name}-transition", transition_frames,
                                        TRANSITION_DURATIONS, transition_layers, TRANSITION_STAGES),
            "presence": save_sequence(output_dir, f"{name}-presence", presence_frames, PRESENCE_DURATIONS,
                                      presence_layers, PRESENCE_STAGES),
            "transition_order": TRANSITION_STAGES,
            "same_state_presence_order": PRESENCE_STAGES,
            "inherited_charm_policy": "all inherited V9 charms omitted by component selection",
        }
        contact_groups.append(presence_frames)

    contact = output_dir / "contact-native-200.png"
    contact_sheet(contact_groups, contact)
    report = {
        "schema": "companion.v35.emotion_decoration_native_200_render.v2",
        "status": "CANDIDATE_PENDING_INTERNAL_NATIVE_200_REVIEW",
        "authority": "COMP-REQ-190",
        "request": str(REQUEST.relative_to(ROOT)).replace("\\", "/"),
        "locked_v9": {"path": str(LOCKED_V9.relative_to(ROOT)).replace("\\", "/"), "sha256": LOCKED_V9_SHA256},
        "rig": {"layout": str(RIG_LAYOUT.relative_to(ROOT)).replace("\\", "/"), "revision": rig.revision},
        "generated_sources": {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)}
                              for name, path in SOURCES.items()},
        "composition": {
            "canvas": [200, 200],
            "safe_inset_px": SAFE_INSET_PX,
            "base_policy": "reconstruct each base from registered locked-V9 Rig components while omitting every inherited charm component by selection",
            "rendering_policy": "source-derived V9 Rig components plus source-derived V35 masks only; no code-drawn visual feature or full-face frame",
        },
        "events": report_events,
        "contact_sheet": {"path": str(contact.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(contact)},
        "runtime": {"resource_activated": False, "component_export": "forbidden_until_source_gate_passes"},
    }
    report_path = (ROOT / args.report).resolve()
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
