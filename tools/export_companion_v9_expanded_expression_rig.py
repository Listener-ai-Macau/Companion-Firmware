#!/usr/bin/env python3
"""Export the owner-approved V9/V10/V11 art bundle as source-mask Rig data.

The tool deliberately exports only registered component masks.  The generated
preview is assembled from those masks as HTML image layers; it never embeds,
cycles, or otherwise plays a complete source-face cell.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from build_emote_asset_pack import build_pack  # noqa: E402


CANVAS = (200, 200)
WHITE = 255
BLACK = 0

LOCKED_V9 = (
    "docs/art/iterations/companion-pet-expression-v9/"
    "generated_pet_expression_sheet_v9_candidate.png"
)
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
DAILY_SOURCE = (
    "docs/art/iterations/companion-pet-expression-v9-extension-v9-expanded-daily-direction-strip/"
    "generated_pet_expression_extension_v9_expanded_daily_direction_strip_candidate.png"
)
DAILY_SHA256 = "06482F6401DF63ED16369660A3D2E4337A37C470F0007C0EAF8CBC90E6D768C5"
EMOTION_SOURCE = (
    "docs/art/iterations/companion-pet-expression-v9-extension-v10-expanded-emotion-panel/"
    "generated_pet_expression_extension_v10_expanded_emotion_panel_candidate.png"
)
EMOTION_SHA256 = "9475CEF565608ED70258980815B31AEEA785CB431AE5B25515FE3790ADE4DD31"
DETAIL_SOURCE = (
    "docs/art/iterations/companion-pet-expression-v9-extension-v11-secondary-detail-kit/"
    "generated_pet_expression_extension_v11_secondary_detail_kit_candidate.png"
)
DETAIL_SHA256 = "76B0BE9F683349490C262DD4725BDDC2252DEEDFD2B675D4EF53745D8B7C1622"
BUNDLE_MANIFEST = (
    "docs/art/iterations/companion-pet-expression-v9-extension-v11-secondary-detail-kit/"
    "full-source-bundle-manifest.json"
)
OWNER_REVIEW = "docs/validation/companion-v9-full-expression-source-bundle-owner-art-review-20260718.json"

DEFAULT_OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v2-expanded-source/candidate"


@dataclass(frozen=True)
class SourceFrame:
    name: str
    path: str
    sha256: str
    crop_box: tuple[int, int, int, int]
    state: str | None


@dataclass(frozen=True)
class Crop:
    role: str
    box: tuple[int, int, int, int]
    z_index: int
    composite_op: str = "ink"
    extraction: str = "raw_black"
    offset_min: tuple[int, int] = (0, 0)
    offset_max: tuple[int, int] = (0, 0)


# These boxes are normalized 200x200 component-safe areas, not geometry drawn
# by code.  The source pixels inside them remain the sole visual output.
FACE_CROPS = (
    Crop("left_brow", (45, 70, 45, 30), 20, offset_min=(-2, -4), offset_max=(2, 2)),
    Crop("right_brow", (125, 70, 45, 30), 20, offset_min=(-2, -4), offset_max=(2, 2)),
    Crop("left_eye", (40, 70, 56, 95), 30, extraction="eye_body_fill_enclosed_white",
         offset_min=(-2, -2), offset_max=(2, 2)),
    Crop("right_eye", (124, 70, 52, 95), 30, extraction="eye_body_fill_enclosed_white",
         offset_min=(-2, -2), offset_max=(2, 2)),
    Crop("left_highlight", (40, 70, 56, 95), 31, composite_op="erase",
         extraction="eye_highlight_primary_enclosed_white", offset_min=(-4, -4), offset_max=(5, 5)),
    Crop("right_highlight", (124, 70, 52, 95), 31, composite_op="erase",
         extraction="eye_highlight_primary_enclosed_white", offset_min=(-4, -4), offset_max=(5, 5)),
    Crop("left_sparkle", (40, 70, 56, 95), 32, composite_op="erase",
         extraction="eye_highlight_sparkle_enclosed_white", offset_min=(-2, -2), offset_max=(2, 2)),
    Crop("right_sparkle", (124, 70, 52, 95), 32, composite_op="erase",
         extraction="eye_highlight_sparkle_enclosed_white", offset_min=(-2, -2), offset_max=(2, 2)),
    Crop("left_cheek", (42, 147, 22, 16), 40, offset_min=(-1, -2), offset_max=(1, 2)),
    Crop("right_cheek", (157, 147, 20, 16), 40, offset_min=(-1, -2), offset_max=(1, 2)),
    Crop("nose", (98, 132, 22, 13), 50, offset_min=(-1, -1), offset_max=(1, 1)),
    Crop("mouth", (92, 145, 40, 28), 60, offset_min=(-1, -3), offset_max=(1, 3)),
)
SLEEP_FACE_CROPS = (
    Crop("left_brow", (45, 70, 45, 30), 20, offset_min=(-2, -4), offset_max=(2, 2)),
    Crop("right_brow", (125, 70, 45, 30), 20, offset_min=(-2, -4), offset_max=(2, 2)),
    Crop("left_eye", (46, 108, 48, 28), 30, offset_min=(-2, -2), offset_max=(2, 2)),
    Crop("right_eye", (125, 108, 48, 28), 30, offset_min=(-2, -2), offset_max=(2, 2)),
    Crop("left_cheek", (42, 136, 20, 12), 40, offset_min=(-1, -2), offset_max=(1, 2)),
    Crop("right_cheek", (158, 136, 20, 12), 40, offset_min=(-1, -2), offset_max=(1, 2)),
    Crop("nose", (98, 132, 22, 13), 50, offset_min=(-1, -1), offset_max=(1, 1)),
)

STATE_ROWS = (
    ("daily_attention_left", "daily", "calm", "left", "normal", 0),
    ("daily_attention_right", "daily", "calm", "right", "normal", 0),
    ("daily_attention_up", "daily", "curious", "up", "high", 1),
    ("daily_attention_down", "daily", "affectionate", "down", "normal", 2),
    ("calm_content", "daily", "calm", "center", "normal", 0),
    ("curious_question", "touch", "curious", "center", "high", 1),
    ("alert_surprised", "touch", "alert", "center", "high", 1),
    ("joyful_spark", "daily", "joyful", "center", "high", 2),
    ("affectionate_warm", "swipe", "affectionate", "center", "normal", 2),
    ("playful_bright", "swipe", "playful", "center", "high", 2),
    ("anticipatory_notice", "daily", "anticipatory", "up", "high", 1),
    ("puzzled_processing", "daily", "puzzled", "center", "normal", 1),
    ("recording_focus", "recording", "focused", "center", "high", 1),
    ("listening_focus", "daily", "listening", "center", "normal", 1),
    ("menu_thinking", "menu", "thinking", "up", "normal", 1),
    ("sleep_rest_no_moon", "sleep", "sleepy", "center", "low", 0),
)
STATE_BY_NAME = {row[0]: row for row in STATE_ROWS}
FAIL_CLOSED_OWNER_REJECTED_STATES = {
    "sleep_rest_no_moon": {
        "scene": "sleep",
        "emotion": "sleepy",
        "reason": "owner_screen_rejected_incomplete_component_composition_pending_v12_locked_v9_only_source_art",
    },
}
ACTIVE_STATE_NAMES = tuple(
    row[0] for row in STATE_ROWS if row[0] not in FAIL_CLOSED_OWNER_REJECTED_STATES
)

DETAIL_SOURCE_NAMES = (
    "cheek_detail_left", "cheek_detail_right", "cheek_dot_pair", "charm_sparkle",
    "charm_heart", "charm_question", "charm_exclamation", "detail_listening_arcs",
)

# Every crop remains raw approved source ink. Split the pair-shaped V11 details
# before anchoring them outside the primary facial reading, so motion cannot
# carry one wide layer across an eye or the mouth.
DETAIL_SPECS = (
    ("cheek_detail_left", "cheek_detail_left", "left_detail", "detail_left", (16, 128), (-2, -2), (1, 2), 45, None),
    ("cheek_detail_right", "cheek_detail_right", "right_detail", "detail_right", (171, 110), (-1, -1), (1, 1), 45, None),
    ("cheek_dot_pair", "cheek_dot_left", "cheek_pair", "detail_pair_left", (23, 146), (-1, -2), (1, 2), 45, (81, 130, 14, 13)),
    ("cheek_dot_pair", "cheek_dot_right", "cheek_pair", "detail_pair_right", (177, 146), (-1, -2), (1, 2), 45, (114, 130, 13, 13)),
    ("charm_sparkle", "charm_sparkle", "charm", "sparkle", (84, 22), (-2, -3), (2, 2), 10, None),
    ("charm_heart", "charm_heart", "charm", "heart", (84, 22), (-2, -3), (2, 2), 10, None),
    ("charm_question", "charm_question", "charm", "question", (84, 22), (-2, -3), (2, 2), 10, None),
    ("charm_exclamation", "charm_exclamation", "charm", "exclamation", (84, 22), (-2, -3), (2, 2), 10, None),
    ("detail_listening_arcs", "detail_listening_arc_left", "listening_detail", "listening_left", (10, 96), (-1, -2), (1, 2), 35, (40, 34, 25, 45)),
    ("detail_listening_arcs", "detail_listening_arc_right", "listening_detail", "listening_right", (166, 96), (-1, -2), (1, 2), 35, (102, 34, 24, 45)),
)

STATE_ACCENTS = {
    "daily_attention_left": ("charm_sparkle",),
    "daily_attention_right": ("charm_sparkle",),
    "daily_attention_up": ("charm_sparkle",),
    "daily_attention_down": ("charm_sparkle",),
    "calm_content": (),
    # The V11 punctuation treatments were visually rejected.  Keep their
    # source masks in the external pack for audit, but do not bind them until
    # a separately reviewed V16 source supplies replacement components.
    "curious_question": (),
    "alert_surprised": (),
    "joyful_spark": ("charm_sparkle",),
    "affectionate_warm": ("charm_heart",),
    "playful_bright": (),
    "anticipatory_notice": ("charm_sparkle",),
    "puzzled_processing": (),
    "recording_focus": (),
    "listening_focus": (),
    "menu_thinking": (),
    "sleep_rest_no_moon": (),
}

# These are semantic baselines, not a playlist.  The directed edge list mirrors
# expression_choreographer.c so the browser and generated target profile can
# render only causally permitted component bridges.
EMOTION_BASELINE_STATES = {
    "calm": "calm_content",
    "curious": "curious_question",
    "affectionate": "affectionate_warm",
    "focused": "recording_focus",
    "alert": "alert_surprised",
    "joyful": "joyful_spark",
    "playful": "playful_bright",
    "anticipatory": "anticipatory_notice",
    "puzzled": "puzzled_processing",
    "listening": "listening_focus",
    "thinking": "menu_thinking",
}
EMOTION_GRAPH_EDGES = (
    ("calm", "curious"), ("calm", "listening"),
    ("curious", "calm"), ("curious", "affectionate"), ("curious", "anticipatory"),
    ("curious", "puzzled"), ("curious", "thinking"), ("curious", "alert"),
    ("curious", "focused"),
    ("affectionate", "calm"), ("affectionate", "curious"), ("affectionate", "joyful"),
    ("affectionate", "playful"),
    ("focused", "listening"), ("focused", "thinking"), ("focused", "alert"),
    ("focused", "calm"),
    ("alert", "curious"), ("alert", "focused"), ("alert", "anticipatory"),
    ("alert", "calm"),
    ("joyful", "affectionate"), ("joyful", "playful"), ("joyful", "anticipatory"),
    ("joyful", "calm"),
    ("playful", "joyful"), ("playful", "affectionate"), ("playful", "curious"),
    ("playful", "calm"),
    ("anticipatory", "curious"), ("anticipatory", "alert"), ("anticipatory", "focused"),
    ("anticipatory", "joyful"), ("anticipatory", "calm"),
    ("puzzled", "curious"), ("puzzled", "thinking"), ("puzzled", "alert"),
    ("puzzled", "calm"),
    ("listening", "focused"), ("listening", "curious"), ("listening", "calm"),
    ("thinking", "puzzled"), ("thinking", "curious"), ("thinking", "focused"),
    ("thinking", "calm"),
)
BRIDGE_CUES = (
    "source_hold", "gaze_lead", "gaze_arrive", "brow_answer",
    "lower_face_reply", "accent_follow_through", "target_hold",
)
BRIDGE_IDENTITY_ROLES = {
    "left_eye", "right_eye", "left_sparkle", "right_sparkle", "nose",
}
BRIDGE_BROW_ROLES = {"left_brow", "right_brow"}
BRIDGE_LOWER_FACE_ROLES = {"left_cheek", "right_cheek", "mouth"}
BRIDGE_ACCENT_ROLES = {"charm", "left_detail", "right_detail", "cheek_pair", "listening_detail"}

ATTENTION_OFFSETS = {
    "center": (0, 0), "left": (-2, 0), "right": (2, 0),
    "up": (1, -2), "down": (1, 3),
}
ENERGY_MOTION_ROLES = {
    "left_brow", "right_brow", "left_detail", "right_detail",
    "charm", "cheek_pair", "listening_detail",
}
PROTECTED_FACE_ROLES = (
    "left_brow", "right_brow", "left_eye", "right_eye",
    "left_cheek", "right_cheek", "nose", "mouth",
)
SECONDARY_OR_MOVABLE_ROLES = (
    "left_detail", "right_detail", "cheek_pair", "listening_detail", "charm",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_pbm(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path)


def crop_square(image: Image.Image, center_x: int, center_y: int, side: int) -> Image.Image:
    """Crop a source-square, filling panel exterior with white where necessary."""
    result = Image.new("L", (side, side), WHITE)
    left = center_x - side // 2
    top = center_y - side // 2
    source_left = max(0, left)
    source_top = max(0, top)
    source_right = min(image.width, left + side)
    source_bottom = min(image.height, top + side)
    if source_right > source_left and source_bottom > source_top:
        result.paste(image.crop((source_left, source_top, source_right, source_bottom)),
                     (source_left - left, source_top - top))
    return result


def normalize_cell(image: Image.Image, center_x: int, center_y: int, side: int) -> Image.Image:
    square = crop_square(image.convert("L"), center_x, center_y, side)
    resized = square.resize(CANVAS, Image.Resampling.LANCZOS)
    return resized.point(lambda value: WHITE if value >= 128 else BLACK, mode="1")


def black_component_boxes(image: Image.Image, minimum_pixels: int) -> list[tuple[int, tuple[int, int, int, int]]]:
    """Return connected source-ink boxes; no facial geometry is synthesized."""
    pixels = image.convert("1").load()
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, tuple[int, int, int, int]]] = []
    for y in range(image.height):
        for x in range(image.width):
            if pixels[x, y] != BLACK or (x, y) in seen:
                continue
            queue = [(x, y)]
            seen.add((x, y))
            count = 0
            left = right = x
            top = bottom = y
            while queue:
                px, py = queue.pop()
                count += 1
                left = min(left, px)
                right = max(right, px)
                top = min(top, py)
                bottom = max(bottom, py)
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < image.width and 0 <= ny < image.height and \
                            (nx, ny) not in seen and pixels[nx, ny] == BLACK:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if count >= minimum_pixels:
                components.append((count, (left, top, right, bottom)))
    return components


def align_face_to_v9_eye_anchor(frame: Image.Image, state_name: str) -> tuple[Image.Image, dict[str, object]]:
    """Affine-align existing face pixels to the locked V9 eye anchor.

    The V10 panel has uneven source-cell framing.  This normalizes only its
    source pixels before extraction, so the recorded component anchors still
    describe one character rather than a collection of drifting source cards.
    """
    candidates = black_component_boxes(frame, 250 if state_name == "sleep_rest_no_moon" else 700)
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) < 2:
        raise ValueError(f"{state_name} lacks a paired source-eye anchor")
    _, first = candidates[0]
    _, second = candidates[1]
    if first[0] > second[0]:
        first, second = second, first
    first_center = ((first[0] + first[2]) / 2.0, (first[1] + first[3]) / 2.0)
    second_center = ((second[0] + second[2]) / 2.0, (second[1] + second[3]) / 2.0)
    source_center = ((first_center[0] + second_center[0]) / 2.0,
                     (first_center[1] + second_center[1]) / 2.0)
    source_spacing = second_center[0] - first_center[0]
    target_center = (109.0, 122.5)
    target_spacing = 78.0
    if source_spacing <= 0.0:
        raise ValueError(f"{state_name} source-eye anchors are not ordered")
    scale = target_spacing / source_spacing
    if not 0.75 <= scale <= 1.25:
        raise ValueError(f"{state_name} source-eye scale is outside the registered V9 range")
    inverse_scale = 1.0 / scale
    aligned = frame.convert("L").transform(
        CANVAS,
        Image.Transform.AFFINE,
        (inverse_scale, 0.0, source_center[0] - target_center[0] * inverse_scale,
         0.0, inverse_scale, source_center[1] - target_center[1] * inverse_scale),
        resample=Image.Resampling.BICUBIC,
        fillcolor=WHITE,
    ).point(lambda value: WHITE if value >= 128 else BLACK, mode="1")
    return aligned, {
        "method": "source_eye_anchor_affine",
        "source_pair_centers": [[round(first_center[0], 2), round(first_center[1], 2)],
                                [round(second_center[0], 2), round(second_center[1], 2)]],
        "target_pair_centers": [[70.0, 122.5], [148.0, 122.5]],
        "uniform_scale": round(scale, 6),
        "source_center": [round(source_center[0], 2), round(source_center[1], 2)],
        "target_center": list(target_center),
    }


def source_frames() -> tuple[SourceFrame, ...]:
    frames: list[SourceFrame] = []
    daily_width = 2172 // 4
    for index, state in enumerate(("daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down")):
        frames.append(SourceFrame(state, DAILY_SOURCE, DAILY_SHA256,
                                  (index * daily_width, (724 - daily_width) // 2, daily_width, daily_width), state))
    # The 3x4 panel keeps a generous white gutter.  A 300px square preserves
    # V9 proportions and normalizes its face scale to the daily source strip
    # without stretching the rectangular grid cell.
    for index, state in enumerate(tuple(row[0] for row in STATE_ROWS[4:])):
        column = index % 4
        row = index // 4
        frames.append(SourceFrame(state, EMOTION_SOURCE, EMOTION_SHA256,
                                  (int(round((column + 0.5) * 1254 / 4)) - 150,
                                   row * 418 + 95,
                                   300, 300), state))
    return tuple(frames)


def detail_frames() -> tuple[SourceFrame, ...]:
    frames: list[SourceFrame] = []
    for index, name in enumerate(DETAIL_SOURCE_NAMES):
        column = index % 4
        row = index // 4
        side = 384
        frames.append(SourceFrame(name, DETAIL_SOURCE, DETAIL_SHA256,
                                  (column * side, row * 512 + (512 - side) // 2, side, side), None))
    return tuple(frames)


def ink_mask(frame: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x, y, width, height = box
    return frame.crop((x, y, x + width, y + height)).convert("1")


def black_pixels(image: Image.Image) -> set[tuple[int, int]]:
    pixels = image.convert("1").load()
    return {(x, y) for y in range(image.height) for x in range(image.width) if pixels[x, y] == BLACK}


def largest_black_component_mask(image: Image.Image) -> Image.Image:
    """Keep the source eye body while excluding nearby brows and cheek dots."""
    pixels = image.convert("1").load()
    seen: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for y in range(image.height):
        for x in range(image.width):
            if pixels[x, y] != BLACK or (x, y) in seen:
                continue
            queue = [(x, y)]
            component: set[tuple[int, int]] = set()
            seen.add((x, y))
            while queue:
                px, py = queue.pop()
                component.add((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < image.width and 0 <= ny < image.height and (nx, ny) not in seen and pixels[nx, ny] == BLACK:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if len(component) > len(largest):
                largest = component
    if not largest:
        raise ValueError("eye crop has no source ink")
    result = Image.new("1", image.size, WHITE)
    result_pixels = result.load()
    for x, y in largest:
        result_pixels[x, y] = BLACK
    return result


def white_regions_surrounded_by_black(frame: Image.Image, box: tuple[int, int, int, int]) -> list[set[tuple[int, int]]]:
    crop = frame.crop((box[0], box[1], box[0] + box[2], box[1] + box[3])).convert("1")
    pixels = crop.load()
    seen: set[tuple[int, int]] = set()
    regions: list[set[tuple[int, int]]] = []
    for y in range(crop.height):
        for x in range(crop.width):
            if pixels[x, y] != WHITE or (x, y) in seen:
                continue
            queue = [(x, y)]
            region: set[tuple[int, int]] = set()
            touches_edge = False
            seen.add((x, y))
            while queue:
                px, py = queue.pop()
                region.add((px, py))
                touches_edge |= px == 0 or py == 0 or px == crop.width - 1 or py == crop.height - 1
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < crop.width and 0 <= ny < crop.height and (nx, ny) not in seen and pixels[nx, ny] == WHITE:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if not touches_edge:
                regions.append(region)
    return regions


def component_mask(frame: Image.Image, crop: Crop) -> Image.Image:
    if crop.extraction == "raw_black":
        return ink_mask(frame, crop.box)
    if crop.extraction == "eye_body_fill_enclosed_white":
        # Fill the source reflections so the black eye body can be composited
        # before the independently movable erase masks.
        body = largest_black_component_mask(ink_mask(frame, crop.box))
        regions = white_regions_surrounded_by_black(body, (0, 0, body.width, body.height))
        body_pixels = body.load()
        for region in regions:
            for x, y in region:
                body_pixels[x, y] = BLACK
        return body
    regions = white_regions_surrounded_by_black(frame, crop.box)
    if not regions:
        raise ValueError(f"{crop.role} lacks enclosed white source pixels")
    largest = max(regions, key=len)
    if crop.extraction == "eye_highlight_sparkle_enclosed_white":
        candidates = [region for region in regions if region is not largest]
        if not candidates:
            # Some resampled source cells merge at low resolution.  The small
            # component remains static by exporting an empty source-only mask.
            return Image.new("1", (crop.box[2], crop.box[3]), WHITE)
        selected = max(candidates, key=len)
    elif crop.extraction == "eye_highlight_primary_enclosed_white":
        selected = largest
    else:
        raise ValueError(f"unsupported extraction {crop.extraction}")
    mask = Image.new("1", (crop.box[2], crop.box[3]), WHITE)
    pixels = mask.load()
    for x, y in selected:
        pixels[x, y] = BLACK
    return mask


def face_crops_for_frame(frame: SourceFrame) -> Iterable[Crop]:
    if frame.name != "sleep_rest_no_moon":
        return FACE_CROPS
    # Closed sleep eyes have a separate approved source placement. There is no
    # sleep mouth or open-eye reflection to borrow from a waking state.
    return SLEEP_FACE_CROPS


def paste_component(canvas: Image.Image, component: dict[str, object], mask_path: Path,
                    offset: tuple[int, int] = (0, 0)) -> None:
    mask = Image.open(mask_path).convert("1")
    # PBM black is source ink. PIL paste masks use white as the write-enable
    # value, so invert only for this preview compositor.
    write_mask = mask.point(lambda value: WHITE if value == BLACK else BLACK, mode="1")
    x, y = component["base_position"]  # type: ignore[index]
    origin = (int(x) + offset[0], int(y) + offset[1])
    op = component["composite_op"]
    if op == "ink":
        canvas.paste(BLACK, origin, write_mask)
    else:
        canvas.paste(WHITE, origin, write_mask)


def energy_offset(energy: str) -> int:
    return {"low": 1, "normal": 0, "high": -1}[energy]


def resolved_component_offset(component: dict[str, object], state_name: str,
                              requested: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    _, _, _, attention, energy, interaction_memory = STATE_BY_NAME[state_name]
    offset_x, offset_y = requested
    motion_flags = component.get("motion_flags", [])
    if "energy_y" in motion_flags:
        offset_y += energy_offset(energy)
    if "memory_x" in motion_flags:
        offset_x += interaction_memory
    ranges = component["offset_range"]
    minimum = ranges["min"]
    maximum = ranges["max"]
    return (
        max(int(minimum[0]), min(int(maximum[0]), offset_x)),
        max(int(minimum[1]), min(int(maximum[1]), offset_y)),
    )


def compose_components(state_name: str, names: list[str], offsets: dict[str, list[int]],
                       components: dict[str, dict[str, object]], paths: dict[str, Path]) -> Image.Image:
    canvas = Image.new("1", CANVAS, WHITE)
    attention = STATE_BY_NAME[state_name][3]
    for name in sorted(names, key=lambda item: int(components[item]["z_index"])):
        component = components[name]
        offset = ATTENTION_OFFSETS[attention] if str(component["role"]) in {
            "left_highlight", "right_highlight"} else (0, 0)
        if name in offsets:
            raw = offsets[name]
            if not isinstance(raw, list) or len(raw) != 2 or not all(isinstance(value, int) for value in raw):
                raise ValueError(f"performance offset is invalid: {state_name}/{name}")
            offset = (raw[0], raw[1])
        paste_component(canvas, component, paths[name], resolved_component_offset(component, state_name, offset))
    return canvas


def component_ink_positions(component: dict[str, object], mask_path: Path, state_name: str,
                            requested: tuple[int, int]) -> set[tuple[int, int]]:
    """Project registered source ink into target coordinates without drawing it."""
    offset_x, offset_y = resolved_component_offset(component, state_name, requested)
    base_x, base_y = component["base_position"]  # type: ignore[index]
    positions: set[tuple[int, int]] = set()
    for x, y in black_pixels(Image.open(mask_path).convert("1")):
        target_x = int(base_x) + offset_x + x
        target_y = int(base_y) + offset_y + y
        if 0 <= target_x < CANVAS[0] and 0 <= target_y < CANVAS[1]:
            positions.add((target_x, target_y))
    return positions


def audit_component_occlusion(performances: dict[str, dict[str, object]],
                              presence_tracks: dict[str, dict[str, object]],
                              emotion_bridge_tracks: dict[str, dict[str, object]],
                              state_core_sets: dict[str, list[str]],
                              state_sets: dict[str, list[str]],
                              components: dict[str, dict[str, object]],
                              paths: dict[str, Path]) -> dict[str, object]:
    """Reject source-mask layers that cover another protected facial feature."""
    frames: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []
    sequences = (("transition", performances), ("presence", presence_tracks),
                 ("emotion_bridge", emotion_bridge_tracks))
    for track, stories in sequences:
        for story, performance in stories.items():
            steps = performance["steps"]
            for step in steps:  # type: ignore[union-attr]
                state_name = str(step["state"])
                if track == "emotion_bridge":
                    names = step.get("components")
                    if not isinstance(names, list) or not all(isinstance(name, str) and name in components for name in names):
                        raise ValueError(f"emotion bridge step has invalid source components: {story}")
                else:
                    names = state_core_sets[state_name] if step["set"] == "core" else state_sets[state_name]
                role_ink: dict[str, set[tuple[int, int]]] = {}
                attention = STATE_BY_NAME[state_name][3]
                for name in names:
                    component = components[name]
                    if component["composite_op"] != "ink":
                        continue
                    requested = ATTENTION_OFFSETS[attention] if str(component["role"]) in {
                        "left_highlight", "right_highlight"} else (0, 0)
                    raw = step["offsets"].get(name)  # type: ignore[index]
                    if raw is not None:
                        requested = (int(raw[0]), int(raw[1]))
                    role = str(component["role"])
                    role_ink.setdefault(role, set()).update(
                        component_ink_positions(component, paths[name], state_name, requested))
                protected_pairs: list[dict[str, object]] = []
                for index, left in enumerate(PROTECTED_FACE_ROLES):
                    for right in PROTECTED_FACE_ROLES[index + 1:]:
                        overlap = len(role_ink.get(left, set()) & role_ink.get(right, set()))
                        if overlap:
                            protected_pairs.append({"roles": [left, right], "pixels": overlap})
                protected_ink: set[tuple[int, int]] = set()
                for role in PROTECTED_FACE_ROLES:
                    protected_ink.update(role_ink.get(role, set()))
                secondary_overlaps: list[dict[str, object]] = []
                for role in SECONDARY_OR_MOVABLE_ROLES:
                    overlap = len(role_ink.get(role, set()) & protected_ink)
                    if overlap:
                        secondary_overlaps.append({"role": role, "pixels": overlap})
                frame = {
                    "story": story,
                    "track": track,
                    "phase": step["phase"],
                    "state": state_name,
                    "component_set": step["set"],
                    "protected_role_overlap_pixels": sum(item["pixels"] for item in protected_pairs),
                    "secondary_overlap_pixels": sum(item["pixels"] for item in secondary_overlaps),
                    "protected_role_pairs": protected_pairs,
                    "secondary_role_overlaps": secondary_overlaps,
                }
                frames.append(frame)
                if protected_pairs or secondary_overlaps:
                    violations.append(frame)
    return {
        "schema": "companion.v9_expanded_expression_rig_component_occlusion_audit.v1",
        "status": "PASS_ZERO_PROTECTED_FEATURE_OVERLAP" if not violations else "FAIL_PROTECTED_FEATURE_OVERLAP",
        "frame_count": len(frames),
        "protected_face_roles": list(PROTECTED_FACE_ROLES),
        "secondary_or_movable_roles": list(SECONDARY_OR_MOVABLE_ROLES),
        "frames": frames,
        "violations": violations,
    }


def bounding_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    ink = black_pixels(image)
    if not ink:
        return None
    xs, ys = zip(*ink)
    return min(xs), min(ys), max(xs), max(ys)


def bitmap_bounds(image: Image.Image) -> list[int]:
    box = bounding_box(image)
    if box is None:
        return [0, 0, 0, 0]
    left, top, right, bottom = box
    return [left, top, right - left + 1, bottom - top + 1]


def build_audit_cemp(output: Path, performance_frames: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    clips: list[dict[str, object]] = []
    for state, frames in performance_frames.items():
        clip_frames: list[dict[str, object]] = []
        for frame in frames:
            path = ROOT / str(frame["path"])
            image = Image.open(path).convert("1")
            clip_frames.append({
                "source": path.relative_to(output).as_posix(),
                "duration_ms": int(frame["duration_ms"]),
                "dirty": bitmap_bounds(image),
            })
        clips.append({"name": state, "loop_start": 0, "loop_end": len(clip_frames), "frames": clip_frames})
    manifest = {
        "schema": "companion.emote_asset_pack_manifest.v1",
        "name": "companion-v9-expanded-expression-rig-audit-200x200",
        "revision": 2,
        "priority": 0,
        "profile": {"width": 200, "height": 200, "stride_bytes": 25,
                    "pixel_format": "mono_1bpp_white_is_one_msb"},
        "encoding": "packbits",
        "provenance": {
            "source": LOCKED_V9,
            "source_sha256": LOCKED_V9_SHA256,
            "source_hashes": {LOCKED_V9: LOCKED_V9_SHA256, DAILY_SOURCE: DAILY_SHA256,
                              EMOTION_SOURCE: EMOTION_SHA256, DETAIL_SOURCE: DETAIL_SHA256},
            "runtime_resource_activated": False,
            "machine_only_candidate": True,
            "audit_only": True,
            "forbidden_runtime_paths": ["CEMP playback", "whole-face card loop", "code-drawn face", "custom LUT"],
        },
        "clips": clips,
    }
    manifest_path = output / "expanded-expression-rig-audit-cemp-manifest.json"
    write_json(manifest_path, manifest)
    pack, metadata = build_pack(manifest_path)
    pack_path = output / "companion-v9-expanded-expression-rig-audit-200x200.cemp"
    metadata_path = output / "companion-v9-expanded-expression-rig-audit-200x200.cemp.json"
    pack_path.write_bytes(pack)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    return {
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "pack": pack_path.relative_to(ROOT).as_posix(),
        "metadata": metadata_path.relative_to(ROOT).as_posix(),
        "sha256": sha256(pack_path),
        "clip_count": len(clips),
        "frame_count": sum(len(frames) for frames in performance_frames.values()),
        "runtime_resource_activated": False,
        "audit_only": True,
    }


def component_record(name: str, source_frame: SourceFrame, crop: Crop, mask_path: Path) -> dict[str, object]:
    mask = Image.open(mask_path).convert("1")
    motion_flags: list[str] = []
    if crop.role in ENERGY_MOTION_ROLES:
        motion_flags.append("energy_y")
    if crop.role == "charm":
        motion_flags.append("memory_x")
    return {
        "name": name,
        "role": crop.role,
        "variant": source_frame.state or name,
        "source_frame": source_frame.name,
        "source_sheet": source_frame.path,
        "source_sheet_sha256": source_frame.sha256,
        "source_sheet_crop_box": list(source_frame.crop_box),
        "crop_box": list(crop.box),
        "base_position": [crop.box[0], crop.box[1]],
        "anchor": [crop.box[2] // 2, crop.box[3] // 2],
        "offset_range": {"min": list(crop.offset_min), "max": list(crop.offset_max)},
        "z_index": crop.z_index,
        "composite_op": crop.composite_op,
        "motion_flags": motion_flags,
        "extraction": crop.extraction,
        "mask": mask_path.relative_to(ROOT).as_posix(),
        "mask_sha256": sha256(mask_path),
        "mask_size": [mask.width, mask.height],
    }


def write_preview_png(mask_path: Path, target: Path, composite_op: str) -> None:
    """Write one transparent source-mask layer for the browser candidate only."""
    mask = Image.open(mask_path).convert("1")
    alpha = mask.point(lambda value: WHITE if value == BLACK else BLACK, mode="L")
    color = WHITE if composite_op == "erase" else BLACK
    image = Image.new("RGBA", mask.size, (color, color, color, 0))
    image.putalpha(alpha)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)


def build_component_asset_pack(output: Path, components: list[dict[str, object]]) -> dict[str, object]:
    """Build the existing CRIG v1 external-NOR format from source masks only."""
    header_bytes = 80
    index_entry_bytes = 20
    index = bytearray()
    payload = bytearray()
    records: list[dict[str, object]] = []
    data_offset = header_bytes + index_entry_bytes * len(components)
    for component in components:
        component_id = int(component["component_id"])
        mask_path = ROOT / str(component["mask"])
        image = Image.open(mask_path).convert("1")
        width, height = image.size
        stride = (width + 7) // 8
        data = image.tobytes()
        if len(data) != stride * height:
            raise ValueError(f"component mask stride mismatch: {component['name']}")
        offset = data_offset + len(payload)
        index.extend(struct.pack("<HHHHIII", component_id, width, height, stride,
                                 offset, len(data), zlib.crc32(data) & 0xFFFFFFFF))
        payload.extend(data)
        records.append({
            "component_id": component_id,
            "name": component["name"],
            "width": width,
            "height": height,
            "stride_bytes": stride,
            "data_offset": offset,
            "data_size": len(data),
            "data_crc32": f"{zlib.crc32(data) & 0xFFFFFFFF:08X}",
        })
    total_size = data_offset + len(payload)
    header = bytearray(header_bytes)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, header_bytes)
    struct.pack_into("<I", header, 8, total_size)
    struct.pack_into("<I", header, 12, 1)
    struct.pack_into("<H", header, 16, 200)
    struct.pack_into("<H", header, 18, 200)
    struct.pack_into("<H", header, 20, 25)
    header[22] = 1
    header[23] = 8
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, header_bytes)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED_V9_SHA256)
    pack = output / "companion-v9-expanded-expression-rig-candidate-200x200.crig"
    pack.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    metadata = {
        "schema": "companion.expression_rig_component_pack.v1",
        "status": "CANDIDATE_MACHINE_EXPORT_PENDING",
        "runtime_resource_activated": False,
        "source_sha256": LOCKED_V9_SHA256,
        "profile": {"width": 200, "height": 200, "stride_bytes": 25,
                    "pixel_format": "mono_1bpp_white_is_one_msb", "safe_inset_px": 8},
        "pack": pack.relative_to(ROOT).as_posix(),
        "pack_sha256": sha256(pack),
        "total_size": total_size,
        "component_count": len(records),
        "components": records,
    }
    metadata_path = pack.with_suffix(pack.suffix + ".json")
    write_json(metadata_path, metadata)
    return {"path": pack.relative_to(ROOT).as_posix(), "sha256": sha256(pack),
            "metadata": metadata_path.relative_to(ROOT).as_posix(), "total_size": total_size,
            "component_count": len(records)}


def build_preview_html(output: Path, layout: dict[str, object]) -> None:
    component_map = {item["name"]: item for item in layout["components"]}  # type: ignore[index]
    state_sets = layout["state_component_sets"]  # type: ignore[index]
    presence_tracks = layout["presence_tracks"]  # type: ignore[index]
    emotion_system = layout["emotion_system"]  # type: ignore[index]
    emotion_bridge_tracks = layout["emotion_bridge_tracks"]  # type: ignore[index]
    if not isinstance(emotion_system, dict) or not isinstance(emotion_bridge_tracks, dict):
        raise ValueError("expanded preview requires the registered emotion system")
    baseline_states = emotion_system.get("baseline_states")
    directed_edges = emotion_system.get("directed_edges")
    if not isinstance(baseline_states, dict) or not isinstance(directed_edges, list):
        raise ValueError("expanded preview emotion graph is invalid")
    def encode_sets(sets: dict[str, list[str]]) -> dict[str, list[dict[str, object]]]:
        return {
            name: [
                {"src": str(component_map[component]["preview_mask"]),
                 "x": component_map[component]["base_position"][0],
                 "y": component_map[component]["base_position"][1],
                 "width": component_map[component]["mask_size"][0],
                 "height": component_map[component]["mask_size"][1],
                 "z": component_map[component]["z_index"],
                 "min": component_map[component]["offset_range"]["min"],
                 "max": component_map[component]["offset_range"]["max"],
                 "motion": component_map[component]["motion_flags"],
                 "name": component}
                for component in names
            ]
            for name, names in sets.items()
        }
    contexts = {
        name: {"energy": STATE_BY_NAME[name][4], "memory": STATE_BY_NAME[name][5]}
        for name in state_sets
    }
    encoded = json.dumps({"full": encode_sets(state_sets), "contexts": contexts})
    encoded_component_layers = json.dumps({
        name: {
            "src": str(component["preview_mask"]), "x": component["base_position"][0],
            "y": component["base_position"][1], "width": component["mask_size"][0],
            "height": component["mask_size"][1], "z": component["z_index"],
            "min": component["offset_range"]["min"], "max": component["offset_range"]["max"],
            "motion": component["motion_flags"], "name": name,
        }
        for name, component in component_map.items()
    })
    order = json.dumps(list(state_sets))
    encoded_presence_tracks = json.dumps(presence_tracks)
    encoded_baselines = json.dumps(baseline_states)
    encoded_edges = json.dumps(directed_edges)
    encoded_bridges = json.dumps(emotion_bridge_tracks)
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>V9 Expanded Component Rig Candidate</title>
<style>
body {{ margin: 0; background: #f2f1ed; color: #1f252b; font-family: Arial, sans-serif; }}
main {{ max-width: 840px; margin: 20px auto; padding: 0 18px 28px; }}
#player {{ display: grid; grid-template-columns: minmax(0, 1fr) 42px; gap: 10px; align-items: start; }}
#screen {{ position: relative; width: 100%; aspect-ratio: 1; background: #fff; border: 1px solid #222; image-rendering: pixelated; overflow: hidden; }}
#screen img {{ position: absolute; image-rendering: pixelated; }}
#controls {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; margin-top: 10px; }}
#source, #target {{ min-width: 0; height: 42px; border: 1px solid #24313b; background: #fff; color: #15202a; padding: 0 10px; }}
#play {{ width: 42px; height: 42px; border: 1px solid #24313b; background: #17232d; color: #fff; padding: 0; cursor: pointer; font-size: 18px; }}
@media (max-width: 760px) {{ main {{ margin-top: 12px; padding: 0 10px 20px; }} }}
</style><main><section id="player"><div id="screen"></div><button id="play" type="button" title="Replay emotional component bridge" aria-label="Replay emotional component bridge">&#9654;</button></section><section id="controls"><select id="source" aria-label="Current emotion"></select><select id="target" aria-label="Next emotion"></select></section></main>
<script>
const states = {encoded}; const componentLayers = {encoded_component_layers}; const order = {order}; const presenceTracks = {encoded_presence_tracks}; const baselines = {encoded_baselines}; const directedEdges = {encoded_edges}; const bridgeTracks = {encoded_bridges}; const screen = document.querySelector('#screen'); const sourceSelect = document.querySelector('#source'); const targetSelect = document.querySelector('#target'); const query = new URLSearchParams(location.search); const requested = query.get('state'); const requestedTarget = query.get('target'); const emotionNames = Object.keys(baselines); const baselineEmotion = Object.fromEntries(Object.entries(baselines).map(([emotion, state]) => [state, emotion])); let selected = emotionNames.includes(requested) ? requested : baselineEmotion[requested] || 'calm'; let timer = 0;
function energyY(energy) {{ return energy === 'low' ? 1 : energy === 'high' ? -1 : 0; }}
function clamp(value, low, high) {{ return Math.max(low, Math.min(high, value)); }}
function renderLayers(name, offsets = {{}}, componentNames = null) {{ screen.replaceChildren(); const context = states.contexts[name]; const layers = componentNames ? componentNames.map(component => componentLayers[component]) : states.full[name]; for (const item of layers) {{ const delta = offsets[item.name] || [0, 0]; let dx = delta[0]; let dy = delta[1]; if (item.motion.includes('energy_y')) dy += energyY(context.energy); if (item.motion.includes('memory_x')) dx += context.memory; dx = clamp(dx, item.min[0], item.max[0]); dy = clamp(dy, item.min[1], item.max[1]); const image = document.createElement('img'); image.src = item.src; image.style.left = `${{(item.x + dx) / 2}}%`; image.style.top = `${{(item.y + dy) / 2}}%`; image.style.width = `${{item.width / 2}}%`; image.style.height = `${{item.height / 2}}%`; image.style.zIndex = item.z; screen.append(image); }} }}
function playPresence(emotion) {{ clearTimeout(timer); const name = baselines[emotion]; const steps = presenceTracks[name].steps; let index = 0; function next() {{ const step = steps[index++]; renderLayers(step.state, step.offsets); if (index < steps.length) {{ timer = setTimeout(next, step.duration_ms); }} else if (selected === emotion) {{ timer = setTimeout(() => playPresence(emotion), step.duration_ms); }} }} next(); }}
function findRoute(from, to) {{ if (from === to) return [from]; const parents = new Map([[from, null]]); const queue = [from]; for (let cursor = 0; cursor < queue.length && !parents.has(to); cursor += 1) {{ const current = queue[cursor]; for (const [edgeFrom, edgeTo] of directedEdges) {{ if (edgeFrom === current && !parents.has(edgeTo)) {{ parents.set(edgeTo, current); queue.push(edgeTo); }} }} }} if (!parents.has(to)) return null; const result = []; for (let current = to; current !== null; current = parents.get(current)) result.push(current); return result.reverse(); }}
function playDirectBridge(from, to, done) {{ const bridge = bridgeTracks[`${{from}}_to_${{to}}`]; if (!bridge) {{ done(); return; }} let index = 0; function next() {{ const step = bridge.steps[index++]; renderLayers(step.state, step.offsets, step.components); if (index < bridge.steps.length) timer = setTimeout(next, step.duration_ms); else done(); }} next(); }}
function playRoute(from, to) {{ clearTimeout(timer); const route = findRoute(from, to); if (!route) {{ playPresence(from); return; }} let edge = 0; function next() {{ if (edge + 1 >= route.length) {{ selected = to; sourceSelect.value = to; playPresence(to); return; }} const bridgeFrom = route[edge]; const bridgeTo = route[++edge]; playDirectBridge(bridgeFrom, bridgeTo, next); }} next(); }}
function selectSource(emotion) {{ selected = emotion; sourceSelect.value = emotion; playPresence(emotion); }}
for (const emotion of emotionNames) {{ const sourceOption = document.createElement('option'); sourceOption.value = emotion; sourceOption.textContent = emotion; sourceSelect.append(sourceOption); const targetOption = document.createElement('option'); targetOption.value = emotion; targetOption.textContent = emotion; targetSelect.append(targetOption); }} sourceSelect.onchange = () => selectSource(sourceSelect.value); targetSelect.onchange = () => playRoute(selected, targetSelect.value); document.querySelector('#play').onclick = () => playRoute(selected, targetSelect.value); const initialTarget = emotionNames.includes(requestedTarget) ? requestedTarget : selected; sourceSelect.value = selected; targetSelect.value = initialTarget; if (initialTarget === selected) selectSource(selected); else playRoute(selected, initialTarget);
</script></html>"""
    output.write_text(page, encoding="utf-8")


def write_contact_sheet(output: Path, rendered: dict[str, Path]) -> None:
    sheet = Image.new("1", (4 * 200, 4 * 220), WHITE)
    draw = ImageDraw.Draw(sheet)
    for index, (name, path) in enumerate(rendered.items()):
        x = (index % 4) * 200
        y = (index // 4) * 220
        sheet.paste(Image.open(path).convert("1"), (x, y))
        draw.text((x + 4, y + 202), name, fill=BLACK)
    sheet.save(output)


def write_performance_contact_sheets(output: Path,
                                     performance_frames: dict[str, list[dict[str, object]]]) -> dict[str, str]:
    """Persist one readable seven-phase sheet per story for visual regression review."""
    directory = output / "performance-contact-sheets"
    directory.mkdir(exist_ok=True)
    sheets: dict[str, str] = {}
    for story, frames in performance_frames.items():
        sheet = Image.new("1", (7 * 200, 224), WHITE)
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(frames):
            path = ROOT / str(frame["path"])
            sheet.paste(Image.open(path).convert("1"), (index * 200, 0))
            draw.text((index * 200 + 4, 202), str(frame["phase"]), fill=BLACK)
        target = directory / f"{story}.png"
        sheet.save(target)
        sheets[story] = target.relative_to(ROOT).as_posix()
    return sheets


def write_presence_contact_sheets(output: Path,
                                  presence_frames: dict[str, list[dict[str, object]]]) -> dict[str, str]:
    """Persist the selected-state component tracks without turning them into face cards."""
    directory = output / "presence-contact-sheets"
    directory.mkdir(exist_ok=True)
    sheets: dict[str, str] = {}
    for state, frames in presence_frames.items():
        sheet = Image.new("1", (len(frames) * 200, 224), WHITE)
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(frames):
            path = ROOT / str(frame["path"])
            sheet.paste(Image.open(path).convert("1"), (index * 200, 0))
            draw.text((index * 200 + 4, 202), str(frame["cue"]), fill=BLACK)
        target = directory / f"{state}.png"
        sheet.save(target)
        sheets[state] = target.relative_to(ROOT).as_posix()
    return sheets


def replace_component_roles(base: list[str], donor: list[str], roles: set[str],
                            components: dict[str, dict[str, object]]) -> list[str]:
    """Replace one causal role group without swapping an entire face set."""
    result = [name for name in base if str(components[name]["role"]) not in roles]
    result.extend(name for name in donor if str(components[name]["role"]) in roles)
    if len(result) != len(set(result)):
        raise ValueError("emotion bridge produced duplicate component layers")
    return result


def bridge_gaze_offsets(source_state: str, target_state: str, names: list[str],
                        components: dict[str, dict[str, object]], factor: float) -> dict[str, list[int]]:
    source = ATTENTION_OFFSETS[STATE_BY_NAME[source_state][3]]
    target = ATTENTION_OFFSETS[STATE_BY_NAME[target_state][3]]
    if source == target:
        # A center-to-center affect change still needs a readable attention
        # pickup. Pick one legal cardinal glance deterministically from the
        # state pair, then return to the target's anchored baseline at hold.
        choices = ((-2, 0), (2, 0), (1, -2), (1, 3))
        target = choices[sum(ord(char) for char in f"{source_state}:{target_state}") % len(choices)]
    requested = (
        int(round(source[0] + (target[0] - source[0]) * factor)),
        int(round(source[1] + (target[1] - source[1]) * factor)),
    )
    return {
        name: [requested[0], requested[1]]
        for name in names
        if str(components[name]["role"]) in {"left_highlight", "right_highlight"}
    }


def bridge_response_offsets(names: list[str], components: dict[str, dict[str, object]],
                            roles: set[str]) -> dict[str, list[int]]:
    requested = {
        "left_brow": (0, -1), "right_brow": (0, -1),
        "left_cheek": (0, -1), "right_cheek": (0, -1), "mouth": (0, 1),
    }
    return {
        name: [requested[str(components[name]["role"])][0], requested[str(components[name]["role"])][1]]
        for name in names if str(components[name]["role"]) in roles
    }


def merge_component_offsets(*groups: dict[str, list[int]]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for group in groups:
        result.update(group)
    return result


def build_emotion_bridge_tracks(state_sets: dict[str, list[str]],
                                components: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    """Build the direct edges of the affect graph from source components only."""
    if set(EMOTION_BASELINE_STATES.values()) - set(state_sets):
        raise ValueError("emotion bridge baseline is not an active component state")
    tracks: dict[str, dict[str, object]] = {}
    for source_emotion, target_emotion in EMOTION_GRAPH_EDGES:
        source_state = EMOTION_BASELINE_STATES[source_emotion]
        target_state = EMOTION_BASELINE_STATES[target_emotion]
        source_full = list(state_sets[source_state])
        target_full = list(state_sets[target_state])
        # Accents deliberately remain in their source state through the brow and
        # lower-face replies.  Adding or removing them before the final follow-
        # through reads as a card swap instead of a secondary reaction.
        brow_components = replace_component_roles(
            source_full, target_full, BRIDGE_BROW_ROLES, components)
        lower_components = replace_component_roles(
            brow_components, target_full, BRIDGE_LOWER_FACE_ROLES, components)
        accent_components = replace_component_roles(
            lower_components, target_full, BRIDGE_ACCENT_ROLES, components)
        track_name = f"{source_emotion}_to_{target_emotion}"
        tracks[track_name] = {
            "from_emotion": source_emotion,
            "to_emotion": target_emotion,
            "source_state": source_state,
            "target_state": target_state,
            "policy": "directed affect edge; highlights lead, brows answer, lower face replies, approved accent follows",
            "steps": [
                {"cue": "source_hold", "phase": "entry", "set": "bridge", "state": source_state,
                 "components": source_full, "duration_ms": 820, "offsets": {}},
                {"cue": "gaze_lead", "phase": "lead", "set": "bridge", "state": source_state,
                 "components": source_full, "duration_ms": 240,
                 "offsets": bridge_gaze_offsets(source_state, target_state, source_full, components, 0.5)},
                {"cue": "gaze_arrive", "phase": "response", "set": "bridge", "state": source_state,
                 "components": source_full, "duration_ms": 300,
                 "offsets": bridge_gaze_offsets(source_state, target_state, source_full, components, 1.0)},
                {"cue": "brow_answer", "phase": "accent", "set": "bridge", "state": target_state,
                 "components": brow_components, "duration_ms": 340,
                 "offsets": merge_component_offsets(
                     bridge_gaze_offsets(source_state, target_state, brow_components, components, 1.0),
                     bridge_response_offsets(brow_components, components, BRIDGE_BROW_ROLES))},
                {"cue": "lower_face_reply", "phase": "hold", "set": "bridge", "state": target_state,
                 "components": lower_components, "duration_ms": 480,
                 "offsets": merge_component_offsets(
                     bridge_gaze_offsets(source_state, target_state, lower_components, components, 1.0),
                     bridge_response_offsets(lower_components, components,
                                             BRIDGE_BROW_ROLES | BRIDGE_LOWER_FACE_ROLES))},
                {"cue": "accent_follow_through", "phase": "release", "set": "bridge", "state": target_state,
                 "components": accent_components, "duration_ms": 380,
                 "offsets": merge_component_offsets(
                     bridge_gaze_offsets(source_state, target_state, accent_components, components, 1.0),
                     bridge_response_offsets(accent_components, components,
                                             BRIDGE_BROW_ROLES | BRIDGE_LOWER_FACE_ROLES))},
                {"cue": "target_hold", "phase": "settle", "set": "bridge", "state": target_state,
                 "components": target_full, "duration_ms": 3200, "offsets": {}},
            ],
        }
    return tracks


def write_emotion_bridge_contact_sheets(output: Path,
                                        bridge_frames: dict[str, list[dict[str, object]]]) -> dict[str, str]:
    directory = output / "emotion-bridge-contact-sheets"
    directory.mkdir(exist_ok=True)
    sheets: dict[str, str] = {}
    for bridge, frames in bridge_frames.items():
        sheet = Image.new("1", (len(frames) * 200, 224), WHITE)
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(frames):
            path = ROOT / str(frame["path"])
            sheet.paste(Image.open(path).convert("1"), (index * 200, 0))
            draw.text((index * 200 + 4, 202), str(frame["cue"]), fill=BLACK)
        target = directory / f"{bridge}.png"
        sheet.save(target)
        sheets[bridge] = target.relative_to(ROOT).as_posix()
    return sheets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if args.clean and output.exists():
        try:
            shutil.rmtree(output)
        except PermissionError:
            # A local owner review can keep preview.html's directory open on
            # Windows.  Regenerate every referenced artifact in place instead
            # of forcibly closing that review window; stale unreferenced files
            # are never part of the layout, pack, or machine evidence.
            pass
    output.mkdir(parents=True, exist_ok=True)

    expected = {
        ROOT / LOCKED_V9: LOCKED_V9_SHA256,
        ROOT / DAILY_SOURCE: DAILY_SHA256,
        ROOT / EMOTION_SOURCE: EMOTION_SHA256,
        ROOT / DETAIL_SOURCE: DETAIL_SHA256,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"approved source drifted: {path}")
    bundle = json.loads((ROOT / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    if bundle.get("status") != "APPROVED_OWNER_FULL_SOURCE_BUNDLE_COMPONENT_EXPORT_ALLOWED_RUNTIME_INACTIVE" or \
            bundle.get("component_export_eligible") is not True or bundle.get("runtime_resource_activated") is not False:
        raise ValueError("full source bundle is not approved for inactive component extraction")
    review = json.loads((ROOT / OWNER_REVIEW).read_text(encoding="utf-8"))
    if review.get("selected") != "通过":
        raise ValueError("owner approval result is missing")

    normalized_dir = output / "normalized-source-frames"
    masks_dir = output / "component-masks"
    preview_dir = output / "preview-layers"
    rendered_dir = output / "rendered-200x200"
    performance_dir = output / "performance-frames-200x200"
    normalized_dir.mkdir(exist_ok=True)
    masks_dir.mkdir(exist_ok=True)
    preview_dir.mkdir(exist_ok=True)
    rendered_dir.mkdir(exist_ok=True)
    performance_dir.mkdir(exist_ok=True)

    image_cache: dict[str, Image.Image] = {}
    for source_path in (DAILY_SOURCE, EMOTION_SOURCE, DETAIL_SOURCE):
        image_cache[source_path] = Image.open(ROOT / source_path).convert("L")

    frames = source_frames()
    normalized: dict[str, Path] = {}
    source_alignments: dict[str, dict[str, object]] = {}
    for frame in frames:
        x, y, side, _ = frame.crop_box
        normalized_frame = normalize_cell(image_cache[frame.path], x + side // 2, y + side // 2, side)
        normalized_frame, source_alignments[frame.name] = align_face_to_v9_eye_anchor(
            normalized_frame, frame.name)
        target = normalized_dir / f"{frame.name}.pbm"
        write_pbm(target, normalized_frame)
        normalized[frame.name] = target

    components: list[dict[str, object]] = []
    state_sets: dict[str, list[str]] = {}
    component_paths: dict[str, Path] = {}
    fixed_identity_roles = ("left_eye", "right_eye", "left_highlight", "right_highlight",
                            "left_sparkle", "right_sparkle", "nose")
    for frame in frames:
        source = Image.open(normalized[frame.name]).convert("1")
        names: list[str] = []
        for crop in face_crops_for_frame(frame):
            # The owner-approved V10 panel deliberately preserves one fixed V9
            # eye identity.  Reuse the daily-left source masks for every open
            # state so only source-derived brows/mouth/details vary by emotion.
            if frame.name != "daily_attention_left" and crop.role in fixed_identity_roles:
                continue
            name = f"{frame.name}__{crop.role}"
            mask = component_mask(source, crop)
            mask_path = masks_dir / f"{name}.pbm"
            write_pbm(mask_path, mask)
            preview_path = preview_dir / f"{name}.png"
            write_preview_png(mask_path, preview_path, crop.composite_op)
            record = component_record(name, frame, crop, mask_path)
            record["preview_mask"] = preview_path.relative_to(output).as_posix()
            components.append(record)
            component_paths[name] = mask_path
            names.append(name)
        state_sets[frame.name] = names

    baseline_identity_components = [
        f"daily_attention_left__{role}" for role in fixed_identity_roles
        if f"daily_attention_left__{role}" in component_paths
    ]
    if len(baseline_identity_components) < 5:
        raise ValueError("daily-left source failed to export the fixed V9 identity component set")
    for state, names in state_sets.items():
        if state != "daily_attention_left" and state != "sleep_rest_no_moon":
            names.extend(baseline_identity_components)

    normalized_details: dict[str, tuple[SourceFrame, Image.Image]] = {}
    for frame in detail_frames():
        image = image_cache[frame.path]
        x, y, side, _ = frame.crop_box
        normalized_detail = normalize_cell(image, x + side // 2, y + side // 2, side)
        source_target = normalized_dir / f"{frame.name}.pbm"
        write_pbm(source_target, normalized_detail)
        normalized[frame.name] = source_target
        normalized_details[frame.name] = (frame, normalized_detail)

    for detail in DETAIL_SPECS:
        source_name, name, role, variant, base, minimum, maximum, z_index, source_box = detail
        frame, normalized_detail = normalized_details[source_name]
        if source_box is None:
            bbox = bounding_box(normalized_detail)
            if bbox is None:
                raise ValueError(f"detail source {source_name} has no ink")
            left, top, right, bottom = bbox
            source_box = (left, top, right - left + 1, bottom - top + 1)
        crop = Crop(role, source_box, z_index,
                    offset_min=minimum, offset_max=maximum)
        mask_path = masks_dir / f"{name}.pbm"
        write_pbm(mask_path, ink_mask(normalized_detail, crop.box))
        if not black_pixels(Image.open(mask_path).convert("1")):
            raise ValueError(f"detail component {name} has no approved source ink")
        preview_path = preview_dir / f"{name}.png"
        write_preview_png(mask_path, preview_path, crop.composite_op)
        record = component_record(name, frame, crop, mask_path)
        record["preview_mask"] = preview_path.relative_to(output).as_posix()
        record["variant"] = variant
        record["base_position"] = list(base)
        components.append(record)
        component_paths[name] = mask_path

    by_name = {item["name"]: item for item in components}
    for component_id, component in enumerate(components, start=1):
        component["component_id"] = component_id
    component_pack = build_component_asset_pack(output, components)
    # The rejected sleep source masks remain registered audit assets, but must
    # not compose a live state until a separately accepted V12 source exists.
    state_sets = {state: names for state, names in state_sets.items() if state in ACTIVE_STATE_NAMES}
    state_core_sets = {state: list(names) for state, names in state_sets.items()}
    for state, accents in STATE_ACCENTS.items():
        if state in state_sets:
            state_sets[state].extend(accents)

    def highlight_offsets(state: str, factor: float) -> dict[str, list[int]]:
        if state == "sleep_rest_no_moon":
            return {}
        target = (1, -2) if state == "calm_content" else ATTENTION_OFFSETS[STATE_BY_NAME[state][3]]
        offsets = [int(round(target[0] * factor)), int(round(target[1] * factor))]
        return {
            "daily_attention_left__left_highlight": offsets,
            "daily_attention_left__right_highlight": offsets,
        }

    performances = {
        state: {
            "policy": "entry -> lead -> response -> accent -> hold -> return -> settle; source components only",
            "steps": [
                {"phase": "entry", "set": "core", "state": "calm_content", "duration_ms": 420, "offsets": {}},
                {"phase": "lead", "set": "core", "state": "calm_content", "duration_ms": 140,
                 "offsets": highlight_offsets(state, 0.5)},
                {"phase": "response", "set": "core", "state": state, "duration_ms": 180,
                 "offsets": highlight_offsets(state, 1.0)},
                {"phase": "accent", "set": "full", "state": state, "duration_ms": 180,
                 "offsets": highlight_offsets(state, 1.0)},
                {"phase": "hold", "set": "full", "state": state, "duration_ms": 3400,
                 "offsets": highlight_offsets(state, 1.0)},
                {"phase": "return", "set": "core", "state": "calm_content", "duration_ms": 220,
                 "offsets": highlight_offsets(state, 0.5)},
                {"phase": "settle", "set": "core", "state": "calm_content", "duration_ms": 720, "offsets": {}},
            ],
            "response_components": state_core_sets[state],
            "accent_components": state_sets[state],
        }
        for state in state_sets
    }

    # A selected emotion is an anchored identity baseline.  Its ordinary
    # playback therefore changes only a small causal component group at a
    # time, rather than cycling through state faces or translating the face.
    gaze_wander = {
        "left": ((-1, -1), (-1, 1)),
        "right": ((1, 1), (1, -1)),
        "up": ((-1, -1), (1, -1)),
        "down": ((-1, 1), (1, 1)),
        "center": ((-1, 0), (1, -1)),
    }

    def offsets_for_roles(state: str, role_offsets: dict[str, tuple[int, int]]) -> dict[str, list[int]]:
        return {
            name: [offset[0], offset[1]]
            for name in state_sets[state]
            if (offset := role_offsets.get(str(by_name[name]["role"]))) is not None
        }

    def gaze_offsets(state: str, delta: tuple[int, int]) -> dict[str, list[int]]:
        base = ATTENTION_OFFSETS[STATE_BY_NAME[state][3]]
        return offsets_for_roles(state, {
            "left_highlight": (base[0] + delta[0], base[1] + delta[1]),
            "right_highlight": (base[0] + delta[0], base[1] + delta[1]),
        })

    def merge_offsets(*groups: dict[str, list[int]]) -> dict[str, list[int]]:
        merged: dict[str, list[int]] = {}
        for group in groups:
            merged.update(group)
        return merged

    presence_tracks: dict[str, dict[str, object]] = {}
    for state in state_sets:
        first_gaze, second_gaze = gaze_wander[STATE_BY_NAME[state][3]]
        presence_tracks[state] = {
            "policy": "selected-state component presence only; fixed identity, causal local responses, no face-card rotation",
            "loop_policy": "same_selected_state_after_static_rest",
            "static_rest_ms": 8000,
            "steps": [
                {"cue": "baseline", "phase": "entry", "set": "full", "state": state,
                 "duration_ms": 2600, "offsets": {}},
                {"cue": "gaze_lead", "phase": "lead", "set": "full", "state": state,
                 "duration_ms": 320, "offsets": gaze_offsets(state, first_gaze)},
                {"cue": "gaze_focus", "phase": "response", "set": "full", "state": state,
                 "duration_ms": 420, "offsets": gaze_offsets(state, second_gaze)},
                {"cue": "brow_answer", "phase": "accent", "set": "full", "state": state,
                 "duration_ms": 360, "offsets": merge_offsets(
                     gaze_offsets(state, second_gaze),
                     offsets_for_roles(state, {"left_brow": (0, -1), "right_brow": (0, -1)}))},
                {"cue": "lower_face_reply", "phase": "hold", "set": "full", "state": state,
                 "duration_ms": 460, "offsets": offsets_for_roles(state, {
                     "left_cheek": (0, -1), "right_cheek": (0, -1), "mouth": (0, 1)} )},
                {"cue": "gaze_return", "phase": "return", "set": "full", "state": state,
                 "duration_ms": 360, "offsets": {}},
                {"cue": "identity_hold", "phase": "settle", "set": "full", "state": state,
                 "duration_ms": 3000, "offsets": {}},
                {"cue": "static_rest", "phase": "settle", "set": "full", "state": state,
                 "duration_ms": 8000, "offsets": {}},
            ],
        }

    emotion_bridge_tracks = build_emotion_bridge_tracks(state_sets, by_name)

    rendered: dict[str, Path] = {}
    for state, names in state_sets.items():
        canvas = compose_components(state, names, {}, by_name, component_paths)
        target = rendered_dir / f"{state}.pbm"
        write_pbm(target, canvas)
        rendered[state] = target

    performance_rendered: dict[str, list[dict[str, object]]] = {}
    for state, performance in performances.items():
        frames_for_state: list[dict[str, object]] = []
        for step_index, step in enumerate(performance["steps"]):
            step_state = str(step["state"])
            component_set = state_core_sets if step["set"] == "core" else state_sets
            image = compose_components(step_state, component_set[step_state], step["offsets"],
                                       by_name, component_paths)
            phase = str(step["phase"])
            path = performance_dir / f"{state}-{step_index:02d}-{phase}.pbm"
            write_pbm(path, image)
            frames_for_state.append({
                "index": step_index,
                "phase": phase,
                "duration_ms": step["duration_ms"],
                "state": step_state,
                "component_set": step["set"],
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
            })
        performance_rendered[state] = frames_for_state

    presence_dir = output / "presence-frames-200x200"
    presence_dir.mkdir(exist_ok=True)
    presence_rendered: dict[str, list[dict[str, object]]] = {}
    for state, track in presence_tracks.items():
        frames_for_state: list[dict[str, object]] = []
        for step_index, step in enumerate(track["steps"]):
            image = compose_components(state, state_sets[state], step["offsets"], by_name, component_paths)
            phase = str(step["phase"])
            path = presence_dir / f"{state}-{step_index:02d}-{phase}.pbm"
            write_pbm(path, image)
            frames_for_state.append({
                "index": step_index,
                "cue": step["cue"],
                "phase": phase,
                "duration_ms": step["duration_ms"],
                "state": state,
                "component_set": "full",
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
            })
        presence_rendered[state] = frames_for_state

    bridge_dir = output / "emotion-bridge-frames-200x200"
    bridge_dir.mkdir(exist_ok=True)
    emotion_bridge_rendered: dict[str, list[dict[str, object]]] = {}
    for bridge, track in emotion_bridge_tracks.items():
        frames_for_bridge: list[dict[str, object]] = []
        for step_index, step in enumerate(track["steps"]):
            state_name = str(step["state"])
            names = list(step["components"])
            image = compose_components(state_name, names, step["offsets"], by_name, component_paths)
            phase = str(step["phase"])
            path = bridge_dir / f"{bridge}-{step_index:02d}-{phase}.pbm"
            write_pbm(path, image)
            frames_for_bridge.append({
                "index": step_index,
                "cue": step["cue"],
                "phase": phase,
                "duration_ms": step["duration_ms"],
                "state": state_name,
                "component_set": "bridge",
                "components": names,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
            })
        emotion_bridge_rendered[bridge] = frames_for_bridge

    performance_contact_sheets = write_performance_contact_sheets(output, performance_rendered)
    presence_contact_sheets = write_presence_contact_sheets(output, presence_rendered)
    emotion_bridge_contact_sheets = write_emotion_bridge_contact_sheets(output, emotion_bridge_rendered)
    occlusion_audit = audit_component_occlusion(performances, presence_tracks, emotion_bridge_tracks,
                                                state_core_sets, state_sets,
                                                by_name, component_paths)
    occlusion_path = output / "component-occlusion-audit.json"
    write_json(occlusion_path, occlusion_audit)
    if occlusion_audit["status"] != "PASS_ZERO_PROTECTED_FEATURE_OVERLAP":
        raise ValueError("expanded Rig source masks overlap protected facial features")
    audit_cemp = build_audit_cemp(output, performance_rendered)

    layout = {
        "schema": "companion.v9_expanded_expression_rig_layout.v1",
        "revision": 1,
        "status": "CANDIDATE_MACHINE_EXPORT_PENDING",
        "runtime_resource_activated": False,
        "source_policy": "source masks only; full-face source-card playback is forbidden",
        "source_bundle_manifest": BUNDLE_MANIFEST,
        "owner_review": OWNER_REVIEW,
        "source_baseline": {"source": LOCKED_V9, "sha256": LOCKED_V9_SHA256},
        "profile": {"width": 200, "height": 200, "pixel_format": "mono_1bpp_white_is_one_msb", "safe_inset_px": 8},
        "source_frames": [
            {"name": frame.name, "path": normalized[frame.name].relative_to(ROOT).as_posix(),
             "sha256": sha256(normalized[frame.name]), "source_sheet": frame.path,
             "source_sheet_sha256": frame.sha256, "source_sheet_crop_box": list(frame.crop_box),
             **({"source_alignment": source_alignments[frame.name]} if frame.name in source_alignments else {})}
            for frame in frames + detail_frames()
        ],
        "components": components,
        "state_matrix": [
            {"name": row[0], "scene": row[1], "emotion": row[2], "attention": row[3],
             "energy": row[4], "interaction_memory": row[5], "phase": "sustain"}
            for row in STATE_ROWS if row[0] in ACTIVE_STATE_NAMES
        ],
        "state_component_sets": state_sets,
        "state_core_component_sets": state_core_sets,
        "performances": performances,
        "presence_tracks": presence_tracks,
        "emotion_system": {
            "schema": "companion.v9_affect_transition_graph.v1",
            "affect_core": {"valence_range": [-2, 2], "arousal_range": [0, 3],
                            "affinity_range": [0, 2]},
            "baseline_states": EMOTION_BASELINE_STATES,
            "directed_edges": [list(edge) for edge in EMOTION_GRAPH_EDGES],
            "automatic_idle_policy": "selected_state_presence_only_no_baseline_rotation",
            "bridge_policy": "highlights_then_brows_then_lower_face_then_approved_accent",
        },
        "emotion_bridge_tracks": emotion_bridge_tracks,
        "secondary_detail_policy": {
            "source": DETAIL_SOURCE, "sha256": DETAIL_SHA256,
            "allowed_only_as_sparse_secondary_accents": True,
            "no_cat_outline_or_permanent_whiskers": True,
        },
        "unsupported_events_fail_closed": ["charging", "error", "sleep"],
        "owner_rejected_states_fail_closed": {
            name: {
                **value,
                "source_components_retained_as_unbound_audit_assets": True,
                "active_candidate_binding": "forbidden",
            }
            for name, value in FAIL_CLOSED_OWNER_REJECTED_STATES.items()
        },
        "artifacts": {
            "preview": "preview.html",
            "contact_sheet": "expanded-component-rig-contact-sheet.png",
            "component_pack": component_pack,
            "rendered_frames": {name: path.relative_to(ROOT).as_posix() for name, path in rendered.items()},
            "performance_frames": performance_rendered,
            "performance_contact_sheets": {
                state: {"path": path, "sha256": sha256(ROOT / path)}
                for state, path in performance_contact_sheets.items()
            },
            "presence_frames": presence_rendered,
            "presence_contact_sheets": {
                state: {"path": path, "sha256": sha256(ROOT / path)}
                for state, path in presence_contact_sheets.items()
            },
            "emotion_bridge_frames": emotion_bridge_rendered,
            "emotion_bridge_contact_sheets": {
                bridge: {"path": path, "sha256": sha256(ROOT / path)}
                for bridge, path in emotion_bridge_contact_sheets.items()
            },
            "component_occlusion_audit": {
                "path": occlusion_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(occlusion_path),
                "status": occlusion_audit["status"],
                "frame_count": occlusion_audit["frame_count"],
            },
            "audit_cemp": audit_cemp,
        },
    }
    layout_path = output / "rig-layout.json"
    write_json(layout_path, layout)
    build_preview_html(output / "preview.html", layout)
    write_contact_sheet(output / "expanded-component-rig-contact-sheet.png", rendered)
    report = {
        "schema": "companion.v9_expanded_expression_rig_export.v1",
        "status": "PASS_SOURCE_MASK_EXPORT_CANDIDATE_RUNTIME_INACTIVE",
        "layout": layout_path.relative_to(ROOT).as_posix(),
        "layout_sha256": sha256(layout_path),
        "source_hashes": {str(path.relative_to(ROOT)): digest for path, digest in expected.items()},
        "state_count": len(state_sets),
        "component_count": len(components),
        "component_pack": component_pack,
        "audit_cemp": audit_cemp,
        "component_occlusion_audit": {
            "path": occlusion_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(occlusion_path),
            "status": occlusion_audit["status"],
            "frame_count": occlusion_audit["frame_count"],
        },
        "unique_rendered_frame_hashes": len({sha256(path) for path in rendered.values()}),
        "performance_frame_count": sum(len(frames) for frames in performance_rendered.values()),
        "presence_frame_count": sum(len(frames) for frames in presence_rendered.values()),
        "emotion_bridge_count": len(emotion_bridge_rendered),
        "emotion_bridge_frame_count": sum(len(frames) for frames in emotion_bridge_rendered.values()),
        "full_face_source_card_playback": "forbidden",
        "runtime_resource_activated": False,
    }
    write_json(output / "export-report.json", report)
    print(f"PASS: exported {len(components)} source masks for {len(state_sets)} expanded Rig states")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
