#!/usr/bin/env python3
"""Compile a source-derived v9 component Rig into deterministic e-paper frames.

The input is not a sheet of finished animation cards.  It declares individual
components extracted from the owner-approved static v9 source, their anchors
and legal motion ranges.  A small deterministic choreographer then composes
the components for an explicit state matrix and its entry/sustain/settle
stories.  The generated CEMP is machine-only until a separate visual gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys
import zlib
from dataclasses import dataclass

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from build_emote_asset_pack import build_pack  # noqa: E402


CANVAS = (200, 200)
SAFE_INSET_PX = 4
RIG_COMPONENT_PACK_HEADER_BYTES = 80
RIG_COMPONENT_PACK_INDEX_ENTRY_BYTES = 20
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
VALID_ATTENTION = {"center", "left", "right", "up", "down"}
VALID_EMOTIONS = {"calm", "curious", "affectionate", "focused", "sleepy"}
VALID_ENERGY = {"low", "normal", "high"}
PHASE_ORDER = ("entry", "sustain", "settle")
REQUIRED_ROLES = {
    "left_brow", "right_brow", "left_eye", "right_eye", "left_highlight", "right_highlight", "left_cheek",
    "right_cheek", "nose", "mouth", "left_detail", "right_detail",
    "left_sparkle", "right_sparkle",
}
VALID_COMPOSITE_OPS = {"ink", "erase"}
VALID_EXTRACTIONS = {
    "raw_black",
    "eye_body_fill_enclosed_white",
    "eye_highlight_primary_enclosed_white",
    "eye_highlight_sparkle_enclosed_white",
}


@dataclass(frozen=True)
class SourceFrame:
    name: str
    path: pathlib.Path
    sha256: str


@dataclass(frozen=True)
class Component:
    name: str
    role: str
    variant: str
    source_frame: str
    crop_box: tuple[int, int, int, int]
    base_position: tuple[int, int]
    anchor: tuple[int, int]
    min_offset: tuple[int, int]
    max_offset: tuple[int, int]
    z_index: int
    composite_op: str
    extraction: str


@dataclass(frozen=True)
class State:
    name: str
    scene: str
    emotion: str
    attention: str
    energy: str
    interaction_memory: int
    phase: str


@dataclass(frozen=True)
class Story:
    name: str
    scene: str
    emotion: str
    attention: str
    energy: str
    interaction_memory: int


@dataclass(frozen=True)
class Rig:
    path: pathlib.Path
    source: pathlib.Path
    source_sha256: str
    prompt_revision: str
    revision: int
    sources: dict[str, SourceFrame]
    components: dict[str, Component]
    scene_charms: dict[str, str]
    state_matrix: tuple[State, ...]
    stories: tuple[Story, ...]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def require_sha256(value: object, name: str) -> str:
    result = require_string(value, name).upper()
    if len(result) != 64 or any(char not in "0123456789ABCDEF" for char in result):
        raise ValueError(f"{name} must be an uppercase SHA-256 digest")
    return result


def require_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def require_pair(value: object, name: str, minimum: int, maximum: int) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be [x, y]")
    return (
        require_int(value[0], f"{name}[0]", minimum, maximum),
        require_int(value[1], f"{name}[1]", minimum, maximum),
    )


def require_box(value: object, name: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{name} must be [x, y, width, height]")
    x = require_int(value[0], f"{name}[0]", 0, 199)
    y = require_int(value[1], f"{name}[1]", 0, 199)
    width = require_int(value[2], f"{name}[2]", 1, 200)
    height = require_int(value[3], f"{name}[3]", 1, 200)
    if x + width > 200 or y + height > 200:
        raise ValueError(f"{name} must remain within 200x200")
    return x, y, width, height


def load_state(raw: object, name: str) -> State:
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    state_name = require_string(raw.get("name"), f"{name}.name")
    scene = require_string(raw.get("scene"), f"{name}.scene")
    emotion = require_string(raw.get("emotion"), f"{name}.emotion")
    attention = require_string(raw.get("attention"), f"{name}.attention")
    energy = require_string(raw.get("energy"), f"{name}.energy")
    memory = require_int(raw.get("interaction_memory"), f"{name}.interaction_memory", 0, 2)
    phase = require_string(raw.get("phase"), f"{name}.phase")
    if emotion not in VALID_EMOTIONS or attention not in VALID_ATTENTION or energy not in VALID_ENERGY:
        raise ValueError(f"{name} has unsupported emotion, attention or energy")
    if phase not in PHASE_ORDER:
        raise ValueError(f"{name}.phase must be entry, sustain or settle")
    return State(state_name, scene, emotion, attention, energy, memory, phase)


def load_story(raw: object, name: str) -> Story:
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    story_name = require_string(raw.get("name"), f"{name}.name")
    scene = require_string(raw.get("scene"), f"{name}.scene")
    emotion = require_string(raw.get("emotion"), f"{name}.emotion")
    attention = require_string(raw.get("attention"), f"{name}.attention")
    energy = require_string(raw.get("energy"), f"{name}.energy")
    memory = require_int(raw.get("interaction_memory"), f"{name}.interaction_memory", 0, 2)
    if emotion not in VALID_EMOTIONS or attention not in VALID_ATTENTION or energy not in VALID_ENERGY:
        raise ValueError(f"{name} has unsupported emotion, attention or energy")
    return Story(story_name, scene, emotion, attention, energy, memory)


def load_rig(path: pathlib.Path) -> Rig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "companion.v9_expression_rig_layout.v1":
        raise ValueError("unsupported v9 expression Rig layout schema")
    if raw.get("status") != "CANDIDATE_PENDING_OWNER_REVIEW":
        raise ValueError("Rig layout must remain pending owner review")
    if raw.get("runtime_resource_activated") is not False:
        raise ValueError("Rig layout may not activate a runtime resource")
    source_raw = raw.get("source_baseline")
    if not isinstance(source_raw, dict):
        raise ValueError("source_baseline must be an object")
    source = (ROOT / require_string(source_raw.get("source"), "source_baseline.source")).resolve()
    source_sha = require_sha256(source_raw.get("sha256"), "source_baseline.sha256")
    if source_sha != LOCKED_V9_SHA256 or not source.is_file() or sha256(source) != source_sha:
        raise ValueError("Rig must be rooted in the locked v9 source")
    prompt_revision = require_string(source_raw.get("prompt_revision"), "source_baseline.prompt_revision")
    revision = require_int(raw.get("revision"), "revision", 92, 0x7FFFFFFF)

    profile = raw.get("profile")
    if profile != {
        "width": 200,
        "height": 200,
        "pixel_format": "mono_1bpp_white_is_one_msb",
        "safe_inset_px": SAFE_INSET_PX,
    }:
        raise ValueError("Rig must use the fixed 200x200 1-bit safe-area profile")

    sources_raw = raw.get("source_frames")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ValueError("Rig needs source_frames")
    sources: dict[str, SourceFrame] = {}
    for index, item in enumerate(sources_raw):
        if not isinstance(item, dict):
            raise ValueError(f"source_frames[{index}] must be an object")
        frame_name = require_string(item.get("name"), f"source_frames[{index}].name")
        frame_path = (ROOT / require_string(item.get("path"), f"source_frames[{index}].path")).resolve()
        frame_sha = require_sha256(item.get("sha256"), f"source_frames[{index}].sha256")
        if frame_name in sources or not frame_path.is_file() or sha256(frame_path) != frame_sha:
            raise ValueError(f"source frame {frame_name} is missing or drifted")
        frame = Image.open(frame_path).convert("1")
        if frame.size != CANVAS:
            raise ValueError(f"source frame {frame_name} is not 200x200")
        sources[frame_name] = SourceFrame(frame_name, frame_path, frame_sha)

    components_raw = raw.get("components")
    if not isinstance(components_raw, list) or not components_raw:
        raise ValueError("Rig needs components")
    components: dict[str, Component] = {}
    roles: set[str] = set()
    for index, item in enumerate(components_raw):
        if not isinstance(item, dict):
            raise ValueError(f"components[{index}] must be an object")
        component_name = require_string(item.get("name"), f"components[{index}].name")
        role = require_string(item.get("role"), f"components[{index}].role")
        variant = require_string(item.get("variant", "default"), f"components[{index}].variant")
        source_frame = require_string(item.get("source_frame"), f"components[{index}].source_frame")
        crop_box = require_box(item.get("crop_box"), f"components[{index}].crop_box")
        base_position = require_pair(item.get("base_position"), f"components[{index}].base_position", 0, 199)
        anchor = require_pair(item.get("anchor"), f"components[{index}].anchor", 0, 199)
        ranges = item.get("offset_range")
        if not isinstance(ranges, dict):
            raise ValueError(f"components[{index}].offset_range must be an object")
        min_offset = require_pair(ranges.get("min"), f"components[{index}].offset_range.min", -20, 0)
        max_offset = require_pair(ranges.get("max"), f"components[{index}].offset_range.max", 0, 20)
        if min_offset[0] > max_offset[0] or min_offset[1] > max_offset[1]:
            raise ValueError(f"components[{index}] has inverted offset range")
        z_index = require_int(item.get("z_index"), f"components[{index}].z_index", 0, 100)
        composite_op = require_string(item.get("composite_op", "ink"),
                                      f"components[{index}].composite_op")
        extraction = require_string(item.get("extraction", "raw_black"),
                                    f"components[{index}].extraction")
        if composite_op not in VALID_COMPOSITE_OPS or extraction not in VALID_EXTRACTIONS:
            raise ValueError(f"component {component_name} has unsupported compositing metadata")
        if extraction == "eye_body_fill_enclosed_white" and composite_op != "ink":
            raise ValueError(f"component {component_name} eye body must use ink compositing")
        if extraction in {"eye_highlight_primary_enclosed_white", "eye_highlight_sparkle_enclosed_white"} and \
                composite_op != "erase":
            raise ValueError(f"component {component_name} highlight must use erase compositing")
        if component_name in components or source_frame not in sources:
            raise ValueError(f"component {component_name} is duplicated or has unknown source")
        if anchor[0] >= crop_box[2] or anchor[1] >= crop_box[3]:
            raise ValueError(f"component {component_name} anchor must be inside its crop")
        if base_position[0] + crop_box[2] > 200 or base_position[1] + crop_box[3] > 200:
            raise ValueError(f"component {component_name} base placement exceeds canvas")
        components[component_name] = Component(component_name, role, variant, source_frame, crop_box,
                                               base_position, anchor, min_offset, max_offset, z_index,
                                               composite_op, extraction)
        roles.add(role)
    if not REQUIRED_ROLES.issubset(roles):
        raise ValueError("Rig is missing one or more required facial roles")
    validate_open_highlight_containment(sources, components)

    charms_raw = raw.get("scene_charms")
    if not isinstance(charms_raw, dict) or not charms_raw:
        raise ValueError("Rig needs scene_charms")
    scene_charms: dict[str, str] = {}
    for scene, component_name in charms_raw.items():
        if not isinstance(scene, str) or component_name not in components or components[component_name].role != "charm":
            raise ValueError("every scene charm must reference a declared charm component")
        scene_charms[scene] = component_name

    matrix_raw = raw.get("state_matrix")
    if not isinstance(matrix_raw, list) or len(matrix_raw) < 12:
        raise ValueError("Rig state matrix must contain at least twelve snapshots")
    matrix = tuple(load_state(item, f"state_matrix[{index}]") for index, item in enumerate(matrix_raw))
    if len({state.name for state in matrix}) != len(matrix):
        raise ValueError("Rig state matrix names must be unique")
    if any(state.scene not in scene_charms for state in matrix):
        raise ValueError("state matrix scene has no charm mapping")

    stories_raw = raw.get("stories")
    if not isinstance(stories_raw, list) or not stories_raw:
        raise ValueError("Rig needs stories")
    stories = tuple(load_story(item, f"stories[{index}]") for index, item in enumerate(stories_raw))
    if len({story.name for story in stories}) != len(stories) or any(story.scene not in scene_charms for story in stories):
        raise ValueError("stories must have unique names and mapped scenes")
    return Rig(path.resolve(), source, source_sha, prompt_revision, revision, sources, components,
               scene_charms, matrix, stories)


def validate_open_highlight_containment(sources: dict[str, SourceFrame],
                                       components: dict[str, Component]) -> None:
    """Prove every registered open-eye highlight offset remains inside its eye body."""
    for side in ("left", "right"):
        body_matches = [component for component in components.values()
                        if component.role == f"{side}_eye" and component.variant == "open"]
        highlight_matches = [component for component in components.values()
                             if component.role == f"{side}_highlight" and component.variant == "open"]
        if len(body_matches) != 1 or len(highlight_matches) != 1:
            raise ValueError(f"Rig needs one open {side} eye body and highlight")
        body = body_matches[0]
        highlight = highlight_matches[0]
        if body.composite_op != "ink" or highlight.composite_op != "erase":
            raise ValueError(f"{side} eye/highlight compositing polarity is invalid")
        body_source = Image.open(sources[body.source_frame].path).convert("1")
        highlight_source = Image.open(sources[highlight.source_frame].path).convert("1")
        body_mask = component_ink_mask(component_mask_from_source(body_source, body))
        highlight_mask = component_ink_mask(component_mask_from_source(highlight_source, highlight))
        body_canvas = Image.new("1", CANVAS, 1)
        body_canvas.paste(0, body.base_position, body_mask)
        body_pixels = body_canvas.load()
        highlight_pixels = highlight_mask.load()
        for offset_x in range(highlight.min_offset[0], highlight.max_offset[0] + 1):
            for offset_y in range(highlight.min_offset[1], highlight.max_offset[1] + 1):
                for crop_y in range(highlight_mask.height):
                    for crop_x in range(highlight_mask.width):
                        if highlight_pixels[crop_x, crop_y] != 255:
                            continue
                        canvas_x = highlight.base_position[0] + offset_x + crop_x
                        canvas_y = highlight.base_position[1] + offset_y + crop_y
                        if (canvas_x < 0 or canvas_y < 0 or canvas_x >= CANVAS[0] or canvas_y >= CANVAS[1] or
                                body_pixels[canvas_x, canvas_y] != 0):
                            raise ValueError(
                                f"{highlight.name} offset [{offset_x}, {offset_y}] leaves its source eye body")


def state_for_story(story: Story, phase: str) -> State:
    if phase == "sustain":
        return State(f"{story.name}_{phase}", story.scene, story.emotion, story.attention,
                     story.energy, story.interaction_memory, phase)
    return State(f"{story.name}_{phase}", "daily", "calm", "center", "normal", 0, phase)


def effective_state(state: State) -> State:
    if state.phase == "sustain":
        return state
    return State(state.name, "daily", "calm", "center", "normal", 0, state.phase)


def component_by_role(rig: Rig, role: str, variant: str) -> Component:
    candidates = [component for component in rig.components.values()
                  if component.role == role and component.variant == variant]
    if len(candidates) != 1:
        raise ValueError(f"Rig needs exactly one {role}.{variant} component")
    return candidates[0]


def component_offsets(state: State, component: Component) -> tuple[int, int]:
    attention = {
        "center": (0, 0), "left": (-3, 0), "right": (3, 0),
        "up": (0, -2), "down": (0, 2),
    }[state.attention]
    emotion = {
        "calm": {"brow": (0, 0), "mouth": (0, 0), "cheek": (0, 0), "charm": (0, 0)},
        "curious": {"brow": (0, -2), "mouth": (0, 1), "cheek": (0, -1), "charm": (0, -2)},
        "affectionate": {"brow": (0, -2), "mouth": (0, -1), "cheek": (0, -1), "charm": (0, -2)},
        "focused": {"brow": (0, 0), "mouth": (0, -1), "cheek": (0, 1), "charm": (0, -2)},
        "sleepy": {"brow": (0, 1), "mouth": (0, 0), "cheek": (0, 0), "charm": (0, 0)},
    }[state.emotion]
    energy_y = {"low": 1, "normal": 0, "high": -1}[state.energy]
    if component.role in {"left_highlight", "right_highlight", "left_sparkle", "right_sparkle"}:
        if state.scene == "daily":
            return {
                "center": (0, 0), "left": (-1, 2), "right": (1, 2),
                "up": (0, 1), "down": (0, 2),
            }[state.attention]
        return attention
    if component.role in {"left_eye", "right_eye"}:
        # Daily gaze keeps the V9 eye body stable; the source-derived highlight leads.
        return (0, 0) if state.scene == "daily" else attention
    if component.role in {"left_brow", "right_brow"}:
        return int(attention[0] / 2) + emotion["brow"][0], int(attention[1] / 2) + emotion["brow"][1] + energy_y
    if component.role in {"left_cheek", "right_cheek"}:
        return 0, emotion["cheek"][1]
    if component.role == "mouth":
        return emotion["mouth"]
    if component.role == "charm":
        return state.interaction_memory, emotion["charm"][1] + energy_y
    if component.role == "left_detail" and state.scene == "swipe" and state.attention == "left":
        return -1, energy_y
    if component.role == "right_detail" and state.scene == "swipe" and state.attention == "right":
        return 1, energy_y
    return 0, 0


def clamp_offset(component: Component, offset: tuple[int, int]) -> tuple[int, int]:
    return (
        max(component.min_offset[0], min(component.max_offset[0], offset[0])),
        max(component.min_offset[1], min(component.max_offset[1], offset[1])),
    )


def selected_components(rig: Rig, state: State) -> list[Component]:
    state = effective_state(state)
    eye_variant = "sleepy" if state.emotion == "sleepy" else "open"
    brow_variant = "sleepy" if state.emotion == "sleepy" else "open"
    selected = [
        component_by_role(rig, "left_brow", brow_variant),
        component_by_role(rig, "right_brow", brow_variant),
        component_by_role(rig, "left_eye", eye_variant),
        component_by_role(rig, "right_eye", eye_variant),
        component_by_role(rig, "left_cheek", "default"),
        component_by_role(rig, "right_cheek", "default"),
        component_by_role(rig, "nose", "default"),
        component_by_role(rig, "mouth", "default"),
        rig.components[rig.scene_charms[state.scene]],
    ]
    if eye_variant == "open":
        selected.extend([
            component_by_role(rig, "left_highlight", "open"),
            component_by_role(rig, "right_highlight", "open"),
            component_by_role(rig, "left_sparkle", "open"),
            component_by_role(rig, "right_sparkle", "open"),
        ])
    if state.scene == "swipe" and state.attention == "left":
        selected.append(component_by_role(rig, "left_detail", "swipe"))
    elif state.scene == "swipe" and state.attention == "right":
        selected.append(component_by_role(rig, "right_detail", "swipe"))
    return sorted(selected, key=lambda component: (component.z_index, component.name))


def bitmap_bounds(image: Image.Image) -> list[int]:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    points = [(x, y) for y in range(200) for x in range(200) if pixels[x, y] == 0]
    if not points:
        raise ValueError("Rig rendered an empty frame")
    xs, ys = zip(*points)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    if left < SAFE_INSET_PX or top < SAFE_INSET_PX or right >= 200 - SAFE_INSET_PX or bottom >= 200 - SAFE_INSET_PX:
        raise ValueError("Rig rendered outside the four-pixel safe inset")
    return [left, top, right - left + 1, bottom - top + 1]


def enclosed_white_mask(crop: Image.Image) -> Image.Image:
    """Return source-white islands enclosed by source ink within one feature crop."""
    bitmap = crop.convert("1")
    width, height = bitmap.size
    pixels = bitmap.load()
    outside: set[tuple[int, int]] = set()
    pending: list[tuple[int, int]] = []

    for x in range(width):
        for y in (0, height - 1):
            if pixels[x, y] != 0:
                pending.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if pixels[x, y] != 0:
                pending.append((x, y))
    while pending:
        x, y = pending.pop()
        if (x, y) in outside or pixels[x, y] == 0:
            continue
        outside.add((x, y))
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= next_x < width and 0 <= next_y < height:
                pending.append((next_x, next_y))

    result = Image.new("1", bitmap.size, 1)
    for y in range(height):
        for x in range(width):
            if pixels[x, y] != 0 and (x, y) not in outside:
                result.putpixel((x, y), 0)
    return result


def enclosed_white_island_masks(crop: Image.Image) -> list[Image.Image]:
    """Split the source-enclosed white eye pixels into deterministic 4-connected islands."""
    enclosed = enclosed_white_mask(crop)
    width, height = enclosed.size
    pixels = enclosed.load()
    visited: set[tuple[int, int]] = set()
    islands: list[list[tuple[int, int]]] = []
    for start_y in range(height):
        for start_x in range(width):
            if pixels[start_x, start_y] != 0 or (start_x, start_y) in visited:
                continue
            pending = [(start_x, start_y)]
            points: list[tuple[int, int]] = []
            while pending:
                x, y = pending.pop()
                if (x, y) in visited or x < 0 or y < 0 or x >= width or y >= height or pixels[x, y] != 0:
                    continue
                visited.add((x, y))
                points.append((x, y))
                pending.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
            if points:
                islands.append(points)
    if len(islands) < 2:
        raise ValueError("open eye needs distinct source-derived primary and sparkle white islands")
    masks: list[Image.Image] = []
    for points in sorted(islands, key=lambda item: (-len(item), min(item))):
        mask = Image.new("1", enclosed.size, 1)
        for x, y in points:
            mask.putpixel((x, y), 0)
        masks.append(mask)
    return masks


def component_mask_from_source(source: Image.Image, component: Component) -> Image.Image:
    x, y, width, height = component.crop_box
    crop = source.crop((x, y, x + width, y + height)).convert("1")
    enclosed = enclosed_white_mask(crop)
    if component.extraction == "raw_black":
        return crop
    if component.extraction == "eye_highlight_primary_enclosed_white":
        return enclosed_white_island_masks(crop)[0]
    if component.extraction == "eye_highlight_sparkle_enclosed_white":
        islands = enclosed_white_island_masks(crop)[1:]
        sparkle = Image.new("1", enclosed.size, 1)
        for island in islands:
            sparkle.paste(0, (0, 0), component_ink_mask(island))
        return sparkle
    if component.extraction == "eye_body_fill_enclosed_white":
        body = crop.copy()
        body_pixels = body.load()
        enclosed_pixels = enclosed.load()
        for crop_y in range(height):
            for crop_x in range(width):
                if enclosed_pixels[crop_x, crop_y] == 0:
                    body_pixels[crop_x, crop_y] = 0
        return body
    raise ValueError(f"component {component.name} has an unsupported extraction rule")


def component_ink_mask(component_mask: Image.Image) -> Image.Image:
    return component_mask.point(lambda value: 255 if value == 0 else 0)


def paste_component(canvas: Image.Image, source: Image.Image, component: Component,
                    offset: tuple[int, int]) -> dict[str, object]:
    dx, dy = offset
    if not component.min_offset[0] <= dx <= component.max_offset[0] or not component.min_offset[1] <= dy <= component.max_offset[1]:
        raise ValueError(f"component {component.name} exceeded its legal offset")
    _, _, width, height = component.crop_box
    destination_x = component.base_position[0] + dx
    destination_y = component.base_position[1] + dy
    if destination_x < 0 or destination_y < 0 or destination_x + width > 200 or destination_y + height > 200:
        raise ValueError(f"component {component.name} placement exceeds canvas")
    component_mask = component_mask_from_source(source, component)
    mask = component_ink_mask(component_mask)
    if mask.getbbox() is None:
        raise ValueError(f"component {component.name} extraction has no source-derived ink")
    canvas.paste(0 if component.composite_op == "ink" else 1,
                 (destination_x, destination_y), mask)
    return {
        "component": component.name,
        "role": component.role,
        "variant": component.variant,
        "source_frame": component.source_frame,
        "source_crop_box": list(component.crop_box),
        "composite_op": component.composite_op,
        "extraction": component.extraction,
        "component_anchor": list(component.anchor),
        "base_position": list(component.base_position),
        "offset": [dx, dy],
        "placed_anchor": [destination_x + component.anchor[0], destination_y + component.anchor[1]],
        "legal_offset_range": {"min": list(component.min_offset), "max": list(component.max_offset)},
    }


def render_state(rig: Rig, state: State, source_images: dict[str, Image.Image]) -> tuple[Image.Image, dict[str, object]]:
    effective = effective_state(state)
    canvas = Image.new("1", CANVAS, 1)
    layers: list[dict[str, object]] = []
    for component in selected_components(rig, effective):
        layers.append(paste_component(canvas, source_images[component.source_frame], component,
                                      clamp_offset(component, component_offsets(effective, component))))
    return canvas, {
        "name": state.name,
        "input_state": {
            "scene": state.scene,
            "emotion": state.emotion,
            "attention": state.attention,
            "energy": state.energy,
            "interaction_memory": state.interaction_memory,
            "phase": state.phase,
        },
        "effective_state": {
            "scene": effective.scene,
            "emotion": effective.emotion,
            "attention": effective.attention,
            "energy": effective.energy,
            "interaction_memory": effective.interaction_memory,
            "phase": effective.phase,
        },
        "semantic_anchor": [100, 100],
        "layers": layers,
        "bounds": bitmap_bounds(canvas),
    }


def write_sheet(items: list[tuple[str, Image.Image]], output: pathlib.Path, title: str) -> None:
    columns = 4
    cell_width, cell_height = 230, 240
    rows = (len(items) + columns - 1) // columns
    image = Image.new("RGB", (columns * cell_width, rows * cell_height), "white")
    draw = ImageDraw.Draw(image)
    for index, (name, bitmap) in enumerate(items):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        thumb = bitmap.convert("RGB").resize((180, 180), Image.Resampling.NEAREST)
        image.paste(thumb, (x + 25, y + 28))
        draw.rectangle((x + 25, y + 28, x + 204, y + 207), outline="black")
        draw.text((x + 8, y + 8), name, fill="black")
    draw.text((8, image.height - 18), title, fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def build_component_asset_pack(rig: Rig, component_dir: pathlib.Path,
                               component_records: list[dict[str, object]],
                               output_dir: pathlib.Path) -> dict[str, object]:
    """Pack source masks for the portable Rig compositor, not finished cards."""
    by_name = {str(record["name"]): record for record in component_records}
    index = bytearray()
    payload = bytearray()
    component_metadata: list[dict[str, object]] = []
    data_offset = RIG_COMPONENT_PACK_HEADER_BYTES + \
        RIG_COMPONENT_PACK_INDEX_ENTRY_BYTES * len(rig.components)

    for component in rig.components.values():
        record = by_name.get(component.name)
        if record is None:
            raise ValueError(f"missing component record for {component.name}")
        component_id = int(record["component_id"])
        mask_path = component_dir / f"{component.name}.pbm"
        image = Image.open(mask_path).convert("1")
        width, height = image.size
        stride = (width + 7) // 8
        data = image.tobytes()
        if len(data) != stride * height:
            raise ValueError(f"component mask has unexpected byte size: {component.name}")
        offset = data_offset + len(payload)
        data_crc32 = zlib.crc32(data) & 0xFFFFFFFF
        index.extend(struct.pack("<HHHHIII", component_id, width, height, stride,
                                 offset, len(data), data_crc32))
        payload.extend(data)
        component_metadata.append({
            "component_id": component_id,
            "name": component.name,
            "width": width,
            "height": height,
            "stride_bytes": stride,
            "data_offset": offset,
            "data_size": len(data),
            "data_crc32": f"{data_crc32:08X}",
        })

    total_size = data_offset + len(payload)
    header = bytearray(RIG_COMPONENT_PACK_HEADER_BYTES)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, RIG_COMPONENT_PACK_HEADER_BYTES)
    struct.pack_into("<I", header, 8, total_size)
    struct.pack_into("<I", header, 12, rig.revision)
    struct.pack_into("<H", header, 16, CANVAS[0])
    struct.pack_into("<H", header, 18, CANVAS[1])
    struct.pack_into("<H", header, 20, CANVAS[0] // 8)
    header[22] = 1
    header[23] = SAFE_INSET_PX
    struct.pack_into("<H", header, 24, len(component_metadata))
    struct.pack_into("<I", header, 28, RIG_COMPONENT_PACK_HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(rig.source_sha256)
    pack_path = output_dir / "companion-v9-expression-rig-candidate-200x200.crig"
    pack_path.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    metadata = {
        "schema": "companion.expression_rig_component_pack.v1",
        "status": "CANDIDATE_PENDING_OWNER_REVIEW",
        "runtime_resource_activated": False,
        "revision": rig.revision,
        "source": rel(rig.source),
        "source_sha256": rig.source_sha256,
        "prompt_revision": rig.prompt_revision,
        "profile": {
            "width": CANVAS[0], "height": CANVAS[1], "stride_bytes": CANVAS[0] // 8,
            "pixel_format": "mono_1bpp_white_is_one_msb", "safe_inset_px": SAFE_INSET_PX,
        },
        "pack": rel(pack_path),
        "pack_sha256": sha256(pack_path),
        "total_size": total_size,
        "components": component_metadata,
    }
    metadata_path = output_dir / "companion-v9-expression-rig-candidate-200x200.crig.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    return {"path": pack_path, "sha256": sha256(pack_path), "metadata": metadata_path,
            "component_count": len(component_metadata), "total_size": total_size}


def render(rig: Rig, output_dir: pathlib.Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    component_dir = output_dir / "components"
    frame_dir = output_dir / "pbm"
    component_dir.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)
    source_images = {name: Image.open(source.path).convert("1") for name, source in rig.sources.items()}

    component_ids = {component.name: index for index, component in enumerate(rig.components.values(), start=1)}
    component_records: list[dict[str, object]] = []
    for component in rig.components.values():
        source = source_images[component.source_frame]
        component_mask = component_mask_from_source(source, component)
        if component_ink_mask(component_mask).getbbox() is None:
            raise ValueError(f"component {component.name} extraction has no source-derived ink")
        output = component_dir / f"{component.name}.pbm"
        component_mask.save(output)
        component_records.append({
            "component_id": component_ids[component.name],
            "name": component.name,
            "role": component.role,
            "variant": component.variant,
            "source_frame": component.source_frame,
            "source_frame_sha256": rig.sources[component.source_frame].sha256,
            "source_crop_box": list(component.crop_box),
            "composite_op": component.composite_op,
            "extraction": component.extraction,
            "component_mask": rel(output),
            "component_mask_sha256": sha256(output),
            "component_anchor": list(component.anchor),
            "base_position": list(component.base_position),
            "legal_offset_range": {"min": list(component.min_offset), "max": list(component.max_offset)},
            "z_index": component.z_index,
        })
    component_pack = build_component_asset_pack(rig, component_dir, component_records, output_dir)

    rendered_frames: list[dict[str, object]] = []
    preview_items: list[tuple[str, Image.Image]] = []
    manifest_clips: list[dict[str, object]] = []
    matrix_hashes: dict[str, str] = {}
    frame_images: dict[str, Image.Image] = {}
    for state in rig.state_matrix:
        bitmap, record = render_state(rig, state, source_images)
        output = frame_dir / f"matrix_{state.name}.pbm"
        bitmap.save(output)
        record.update({"kind": "state_matrix", "path": rel(output), "sha256": sha256(output)})
        rendered_frames.append(record)
        matrix_hashes[state.name] = record["sha256"]
        frame_images[f"pbm/matrix_{state.name}.pbm"] = bitmap
        preview_items.append((state.name, bitmap))
    if len(set(matrix_hashes.values())) < 12:
        raise ValueError("state matrix did not produce twelve distinct composed frames")
    for direction in ("left", "right", "up", "down"):
        candidates = [state for state in rig.state_matrix if state.attention == direction]
        if not candidates:
            raise ValueError(f"state matrix has no {direction} attention input")
        if all(matrix_hashes[candidate.name] == matrix_hashes.get("daily_calm_center", "") for candidate in candidates):
            raise ValueError(f"{direction} attention did not change a composed frame")

    manifest_clips.append({
        "name": "state_matrix",
        "loop_start": 0,
        "loop_end": len(rig.state_matrix),
        "frames": [{"source": f"pbm/matrix_{state.name}.pbm", "duration_ms": 3000,
                    "dirty": next(frame["bounds"] for frame in rendered_frames if frame["name"] == state.name)}
                   for state in rig.state_matrix],
    })
    for story in rig.stories:
        story_frames: list[dict[str, object]] = []
        for phase in PHASE_ORDER:
            state = state_for_story(story, phase)
            bitmap, record = render_state(rig, state, source_images)
            output = frame_dir / f"story_{story.name}_{phase}.pbm"
            bitmap.save(output)
            record.update({"kind": "story", "story": story.name, "path": rel(output), "sha256": sha256(output)})
            rendered_frames.append(record)
            preview_items.append((state.name, bitmap))
            frame_images[f"pbm/story_{story.name}_{phase}.pbm"] = bitmap
            story_frames.append({"source": f"pbm/story_{story.name}_{phase}.pbm", "duration_ms": 3000,
                                "dirty": record["bounds"]})
        entry, sustain, settle = story_frames
        entry_image = frame_images[entry["source"]]
        sustain_image = frame_images[sustain["source"]]
        settle_image = frame_images[settle["source"]]
        def different(a: Image.Image, b: Image.Image) -> int:
            return sum((left == 0) != (right == 0) for left, right in zip(a.getdata(), b.getdata()))
        entry_to_sustain = different(entry_image, sustain_image)
        entry_to_settle = different(entry_image, settle_image)
        if entry_to_sustain == 0 or entry_to_settle > entry_to_sustain // 4:
            raise ValueError(f"story {story.name} does not satisfy entry/sustain/settle recovery")
        manifest_clips.append({"name": story.name, "loop_start": 0, "loop_end": 3, "frames": story_frames})

    manifest = {
        "schema": "companion.emote_asset_pack_manifest.v1",
        "name": "companion-v9-expression-rig-candidate-200x200",
        "revision": rig.revision,
        "priority": 0,
        "profile": {"width": 200, "height": 200, "stride_bytes": 25,
                    "pixel_format": "mono_1bpp_white_is_one_msb"},
        "encoding": "packbits",
        "provenance": {
            "source": rel(rig.source), "source_sha256": rig.source_sha256,
            "prompt_revision": rig.prompt_revision, "layout": rel(rig.path),
            "runtime_resource_activated": False, "machine_only_candidate": True,
            "forbidden_inputs": ["legacy CEMP", "rejected art", "code-drawn face", "ball", "custom LUT"],
        },
        "clips": manifest_clips,
    }
    manifest_path = output_dir / "v9-expression-rig-cemp-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    pack, metadata = build_pack(manifest_path)
    pack_path = output_dir / "companion-v9-expression-rig-candidate-200x200.cemp"
    metadata_path = output_dir / "companion-v9-expression-rig-candidate-200x200.cemp.json"
    pack_path.write_bytes(pack)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    preview_path = output_dir / "v9-expression-rig-state-matrix.png"
    write_sheet(preview_items, preview_path, "v9 source-derived Rig state matrix; candidate only")
    return {
        "schema": "companion.v9_expression_rig_render.v1",
        "status": "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW",
        "source": rel(rig.source), "source_sha256": rig.source_sha256,
        "prompt_revision": rig.prompt_revision, "layout": rel(rig.path),
        "profile": {"width": 200, "height": 200, "safe_inset_px": SAFE_INSET_PX},
        "components": component_records,
        "state_matrix": {"frame_hashes": matrix_hashes, "unique_frame_hashes": len(set(matrix_hashes.values()))},
        "frames": rendered_frames,
        "manifest": rel(manifest_path), "pack": rel(pack_path), "pack_sha256": sha256(pack_path),
        "metadata": rel(metadata_path), "preview": rel(preview_path),
        "component_pack": rel(component_pack["path"]),
        "component_pack_sha256": component_pack["sha256"],
        "component_pack_metadata": rel(component_pack["metadata"]),
        "component_pack_component_count": component_pack["component_count"],
        "component_pack_total_size": component_pack["total_size"],
        "runtime_resource_activated": False, "external_flash_provisioned": False,
        "firmware_flashed": False, "owner_visual_pass": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        result = render(load_rig(args.layout.resolve()), args.output_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print("PASS: v9 Rig composed deterministic non-card state-matrix frames and a pending CEMP candidate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
