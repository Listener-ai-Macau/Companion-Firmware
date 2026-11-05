#!/usr/bin/env python3
"""Render V34/V35 browser frames from the exact inactive WB55 score contract."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from companion_expression_anchor import (
    ANCHOR_POLICY,
    CANONICAL_CENTER,
    ink_bounds,
    output_bounds,
    source_anchor,
    translate,
)


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
SPECIAL_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-wb55-target-profile-plan.json"
CHOREOGRAPHER_C = ROOT / "app/companion_pendant/epaper/expression_choreographer.c"
CHOREOGRAPHER_H = ROOT / "app/companion_pendant/epaper/expression_choreographer.h"
GESTURE_C = ROOT / "app/companion_pendant/touch/touch_gesture.c"
GESTURE_H = ROOT / "app/companion_pendant/touch/touch_gesture.h"
DEFAULT_OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/wb55-browser-parity-attempt-01"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v34-v35-special-decoration-browser-wb55-preview-20260720.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def component_map(v22_layout: Path, special_layout: Path) -> dict[int, dict[str, Any]]:
    v22 = load_json(v22_layout)
    special = load_json(special_layout)
    special_locked = special.get("locked_v9_source_sha256")
    if special_locked is None:
        special_locked = special.get("locked_v9_source", {}).get("sha256")
    require(v22.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            special_locked == LOCKED_V9_SHA256,
            "component layouts lost locked V9 lineage")
    v22_components = list(v22.get("components", []))
    special_components = list(special.get("components", []))
    result: dict[int, dict[str, Any]] = {}
    for raw in v22_components + special_components:
        require(isinstance(raw, dict), "component layout record is invalid")
        component_id = raw.get("component_id")
        mask = ROOT / str(raw.get("mask", ""))
        base = raw.get("base_position")
        offset_range = raw.get("offset_range")
        require(isinstance(component_id, int) and component_id not in result and
                mask.is_file() and sha256(mask) == str(raw.get("mask_sha256", "")).upper() and
                isinstance(base, list) and len(base) == 2 and isinstance(offset_range, dict) and
                isinstance(offset_range.get("min"), list) and isinstance(offset_range.get("max"), list) and
                raw.get("composite_op") in {"ink", "erase"},
                f"component {component_id} is not a registered source mask")
        result[component_id] = {
            "mask": mask,
            "base": base,
            "offset_range": offset_range,
            "composite_op": raw["composite_op"],
        }
    require(len(result) == len(v22_components) + len(special_components),
            "browser parity renderer did not receive both registered CRIG namespaces")
    return result


def render_frame(components: dict[int, dict[str, Any]], layers: list[dict[str, Any]]) -> tuple[Image.Image, bytes]:
    target = bytearray(b"\xFF" * 5000)
    for layer in layers:
        component_id = layer.get("component_id")
        offset = layer.get("offset")
        component = components.get(component_id)
        require(component is not None and isinstance(offset, list) and len(offset) == 2 and
                all(isinstance(value, int) for value in offset), "frame references an invalid component layer")
        minimum = component["offset_range"]["min"]
        maximum = component["offset_range"]["max"]
        require(minimum[0] <= offset[0] <= maximum[0] and minimum[1] <= offset[1] <= maximum[1],
                "frame offset exceeds registered component bounds")
        with Image.open(component["mask"]) as source:
            mask = source.convert("1")
        width, height = mask.size
        origin_x = component["base"][0] + offset[0]
        origin_y = component["base"][1] + offset[1]
        require(origin_x >= 0 and origin_y >= 0 and origin_x + width <= 200 and origin_y + height <= 200,
                "component would leave the 200x200 source canvas")
        pixels = mask.load()
        for y in range(height):
            for x in range(width):
                if pixels[x, y] != 0:
                    continue
                target_x = origin_x + x
                target_y = origin_y + y
                index = target_y * 25 + target_x // 8
                bit = 0x80 >> (target_x & 7)
                if component["composite_op"] == "ink":
                    target[index] &= ~bit
                else:
                    target[index] |= bit
    image = Image.frombytes("1", (200, 200), bytes(target))
    return image, bytes(target)


def describe_layers(components: dict[int, dict[str, Any]], layers: list[dict[str, Any]], special_pack: str) -> list[dict[str, Any]]:
    """Expose the exact registered plan that produced the browser pixels."""
    described: list[dict[str, Any]] = []
    for layer in layers:
        component_id = layer.get("component_id")
        component = components.get(component_id)
        offset = layer.get("offset")
        require(component is not None and isinstance(offset, list) and len(offset) == 2 and
                all(isinstance(value, int) for value in offset),
                "cannot describe an invalid component layer")
        expected_pack = "v22_face" if component_id < 500 else special_pack
        require(layer.get("pack") == expected_pack, "frame layer pack does not match its registered namespace")
        described.append({"component_id": component_id, "pack": expected_pack,
                          "anchor": list(component["base"]), "offset": list(offset),
                          "composite_op": component["composite_op"]})
    return described


def write_p4(path: Path, target_bytes: bytes) -> None:
    require(len(target_bytes) == 5000, "target frame must be 200x200 1bpp")
    path.write_bytes(b"P4\n200 200\n" + bytes(value ^ 0xFF for value in target_bytes))


def rounded_dividend(value: int, divisor: int) -> int:
    require(divisor > 0, "touch mapping divisor must be positive")
    if value >= 0:
        return (value + divisor // 2) // divisor
    return -((-value + divisor // 2) // divisor)


def map_touch_axis(value: int, negative: int, positive: int, center: int) -> int:
    """Map one 0..199 touch axis to a registered offset without a dead zone."""
    require(0 <= value < 200, "touch coordinate must be inside the 200x200 face")
    if value <= 100:
        return center + rounded_dividend((value - 100) * (center - negative), 100)
    return center + rounded_dividend((value - 100) * (positive - center), 99)


def touch_offsets(x: int, y: int) -> dict[str, int]:
    return {
        "primary_x": map_touch_axis(x, -2, 5, 1),
        "primary_y": map_touch_axis(y, -3, 4, 0),
        "sparkle_x": map_touch_axis(x, -6, 5, 1),
        "sparkle_y": map_touch_axis(y, -6, 6, 0),
    }


def touch_key(offsets: dict[str, int]) -> str:
    return ",".join(str(offsets[key]) for key in ("primary_x", "primary_y", "sparkle_x", "sparkle_y"))


def emotion_authority() -> dict[str, Any]:
    """Export the registered C affect/selection contract without inventing browser thresholds."""
    source_c = CHOREOGRAPHER_C.read_text(encoding="utf-8")
    source_h = CHOREOGRAPHER_H.read_text(encoding="utf-8")
    required_c = (
        "bool comp_expression_rig_affect_update(",
        "bool comp_expression_rig_affect_target_emotion(",
        "case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP:",
        "case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE:",
        "case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO:",
        "affect->affinity >= 2u && affect->valence >= 1",
        "input->energy == COMP_EXPRESSION_RIG_ENERGY_HIGH && affect->affinity >= 2u &&",
        "affect->arousal >= 3u",
    )
    require(all(marker in source_c for marker in required_c), "emotion choreographer C authority markers drifted")
    required_h = (
        "int8_t valence; /* -2 (unpleasant) through +2 (pleasant). */",
        "uint8_t arousal; /* 0 (resting) through 3 (highly engaged). */",
        "uint8_t affinity; /* 0 through 2, informed by interaction_memory. */",
    )
    require(all(marker in source_h for marker in required_h), "emotion choreographer H value-domain markers drifted")
    return {
        "gesture_authority": gesture_authority(),
        "source": {
            "c": rel(CHOREOGRAPHER_C),
            "c_sha256": sha256(CHOREOGRAPHER_C),
            "h": rel(CHOREOGRAPHER_H),
            "h_sha256": sha256(CHOREOGRAPHER_H),
            "authority_functions": ["comp_expression_rig_affect_update", "comp_expression_rig_affect_target_emotion"],
        },
        "domains": {
            "valence": {"min": -2, "max": 2, "source": "expression_choreographer.h:45"},
            "arousal": {"min": 0, "max": 3, "source": "expression_choreographer.h:46"},
            "affinity": {"min": 0, "max": 2, "source": "expression_choreographer.h:47"},
            "interaction_memory": {"min": 0, "max": 2, "source": "expression_choreographer.c:95-97"},
            "energy": ["low", "normal", "high"],
        },
        "events": ["daily_auto", "touch_tap", "touch_swipe", "recording_active", "menu_hold",
                   "sleep", "wake", "charging", "error", "upgrade_active"],
        "event_priority": {
            "error": 100, "recording_active": 90, "menu_hold": 90, "upgrade_active": 90,
            "sleep": 80, "wake": 70, "touch_swipe": 50, "touch_tap": 40,
            "charging": 30, "daily_auto": 0,
        },
        "affect_update": {
            "daily_auto": {"valence": "toward_neutral", "arousal": "decrement_if_above_1", "affinity": "decrement_if_memory_lower"},
            "touch_tap": {"valence": "clamp_plus_1", "arousal": "at_least_2"},
            "touch_swipe": {"valence": "clamp_plus_1", "arousal": "clamp_plus_1_then_at_least_2"},
            "recording_active": {"valence": "toward_neutral", "arousal": "at_least_2"},
            "menu_hold": {"valence": "toward_neutral", "arousal": "at_least_1"},
            "upgrade_active": {"valence": "toward_neutral", "arousal": "at_least_1"},
            "sleep": {"arousal": "set_0"}, "wake": {"arousal": "set_2"},
            "charging": {"arousal": "set_0"}, "error": {"valence": "clamp_minus_1", "arousal": "set_3"},
        },
        "target_rules": {
            "recording_active": [{"when": [], "emotion": "focused", "branch": "recording_active"}],
            "menu_hold": [{"when": [], "emotion": "thinking", "branch": "menu_hold"}],
            "upgrade_active": [{"when": [], "emotion": "calm", "branch": "upgrade_active"}],
            "charging": [{"when": [], "emotion": "calm", "branch": "charging"}],
            "error": [{"when": [], "emotion": "alert", "branch": "error"}],
            "sleep": [{"when": [], "emotion": "sleepy", "branch": "sleep"}],
            "wake": [{"when": [], "emotion": "curious", "branch": "wake"}],
            "touch_tap": [
                {"when": [["affinity", ">=", 2], ["valence", ">=", 1]], "emotion": "affectionate", "branch": "affinity>=2 && valence>=1"},
                {"when": [], "emotion": "curious", "branch": "else"},
            ],
            "touch_swipe": [
                {"when": [["energy", "==", "high"], ["affinity", ">=", 2], ["valence", ">=", 0]], "emotion": "playful", "branch": "energy==HIGH && affinity>=2 && valence>=0"},
                {"when": [["affinity", ">=", 2], ["valence", ">=", 1]], "emotion": "affectionate", "branch": "affinity>=2 && valence>=1"},
                {"when": [], "emotion": "curious", "branch": "else"},
            ],
            "daily_auto": [
                {"when": [["valence", "<", 0], ["arousal", ">=", 2]], "emotion": "puzzled", "branch": "valence<0 && arousal>=2"},
                {"when": [["valence", "<", 0]], "emotion": "calm", "branch": "valence<0"},
                {"when": [["arousal", ">=", 3], ["affinity", ">=", 2], ["valence", ">=", 1]], "emotion": "playful", "branch": "arousal>=3 && affinity>=2 && valence>=1"},
                {"when": [["arousal", ">=", 3]], "emotion": "anticipatory", "branch": "arousal>=3"},
                {"when": [["valence", ">=", 2], ["affinity", ">=", 2]], "emotion": "joyful", "branch": "valence>=2 && affinity>=2"},
                {"when": [["affinity", ">=", 2], ["valence", ">=", 1]], "emotion": "affectionate", "branch": "affinity>=2 && valence>=1"},
                {"when": [["arousal", ">=", 2]], "emotion": "curious", "branch": "arousal>=2"},
                {"when": [], "emotion": "calm", "branch": "else"},
            ],
        },
        "graph_contract": {"source": "expression_choreographer.c:223-328", "max_route": 12, "min_intent_hold_steps": 2},
    }


def render_touch_base(components: dict[int, dict[str, Any]], layers: list[dict[str, Any]]) -> tuple[Image.Image, bytes]:
    """Keep the complete current face in the base while a gaze overlay moves."""
    return render_frame(components, layers)


def render_touch_overlay(components: dict[int, dict[str, Any]], offsets: dict[str, int]) -> Image.Image:
    """Render source-backed white reflection cutouts clipped to the black eye bodies."""
    overlay = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
    pixels = overlay.load()
    for component_id, body_id, key in ((1, 2, "primary"), (5, 6, "primary"),
                                       (3, 2, "sparkle"), (7, 6, "sparkle")):
        component = components.get(component_id)
        body = components.get(body_id)
        require(component is not None and body is not None,
                f"missing registered gaze/body components {component_id}/{body_id}")
        offset_x = offsets[f"{key}_x"]
        offset_y = offsets[f"{key}_y"]
        minimum = component["offset_range"]["min"]
        maximum = component["offset_range"]["max"]
        require(minimum[0] <= offset_x <= maximum[0] and minimum[1] <= offset_y <= maximum[1],
                f"touch gaze offset exceeds component {component_id} bounds")
        with Image.open(component["mask"]) as source:
            mask = source.convert("1")
        origin_x = component["base"][0] + offset_x
        origin_y = component["base"][1] + offset_y
        require(origin_x >= 0 and origin_y >= 0 and origin_x + mask.width <= 200 and origin_y + mask.height <= 200,
                f"touch gaze component {component_id} leaves the 200x200 canvas")
        with Image.open(body["mask"]) as body_source:
            body_mask = body_source.convert("1")
        mask_pixels = mask.load()
        body_pixels = body_mask.load()
        require(mask.size == body_mask.size,
                f"gaze component {component_id} is not congruent with eye body {body_id}")
        for y in range(mask.height):
            for x in range(mask.width):
                if mask_pixels[x, y] == 0 and body_pixels[x, y] == 0:
                    pixels[origin_x + x, origin_y + y] = (255, 255, 255, 255)
    return overlay


def gesture_authority() -> dict[str, Any]:
    """Parse the product touch classifier defaults; browser thresholds are not local guesses."""
    source_c = GESTURE_C.read_text(encoding="utf-8")
    source_h = GESTURE_H.read_text(encoding="utf-8")
    match = re.search(r"static const comp_touch_gesture_config_t defaults = \{(.*?)\n    \};",
                      source_c, re.DOTALL)
    require(match is not None, "touch_gesture.c defaults block drifted")
    block = match.group(1)
    fields = ("tap_max_move_px", "long_press_max_move_px", "swipe_min_move_px",
              "axis_lock_min_move_px", "axis_slop_px", "tap_max_duration_ms",
              "swipe_max_duration_ms", "hold_feedback_min_duration_ms",
              "long_press_min_duration_ms", "axis_dominance_percent",
              "min_contact_samples", "release_debounce_samples")
    values: dict[str, int] = {}
    for field in fields:
        found = re.search(rf"\.{field}\s*=\s*(\d+)u", block)
        require(found is not None, f"touch classifier default missing {field}")
        values[field] = int(found.group(1))
    for marker in ("COMP_TOUCH_GESTURE_TAP", "COMP_TOUCH_GESTURE_SWIPE_LEFT",
                   "typedef struct", "tap_max_move_px", "swipe_min_move_px"):
        require(marker in source_h, f"touch gesture header marker drifted: {marker}")
    return {
        "source": {"c": rel(GESTURE_C), "c_sha256": sha256(GESTURE_C),
                    "h": rel(GESTURE_H), "h_sha256": sha256(GESTURE_H)},
        "defaults": values,
        "classification": {
            "tap": "duration<=tap_max_duration_ms and abs(dx),abs(dy)<=tap_max_move_px",
            "swipe": "duration<=swipe_max_duration_ms and locked_axis movement>=swipe_min_move_px",
            "axis_lock": "movement>=axis_lock_min_move_px, axis_slop_px and axis_dominance_percent",
            "long_press": "duration>=long_press_min_duration_ms and abs(dx),abs(dy)<=long_press_max_move_px",
        },
        "overall_mapping": {"tap": "touch_tap", "swipe_left": "touch_swipe",
                             "swipe_right": "touch_swipe", "swipe_up": "touch_swipe",
                             "swipe_down": "touch_swipe"},
    }


def render_html(output: Path, frame_records: list[dict[str, Any]], preview_zh: dict[str, Any] | None,
                touch_gaze_package: dict[str, Any] | None = None,
                all_performance_wall: bool = False) -> None:
    stories = list(dict.fromkeys(record["score"] for record in frame_records))
    metadata = preview_zh.get("stories", {}) if isinstance(preview_zh, dict) else {}

    def story_value(name: str, key: str, fallback: str) -> str:
        value = metadata.get(name, {}) if isinstance(metadata, dict) else {}
        return str(value.get(key, fallback)) if isinstance(value, dict) else fallback

    def owner_visible(name: str) -> bool:
        value = metadata.get(name, {}) if isinstance(metadata, dict) else {}
        return not isinstance(value, dict) or value.get("owner_visible", True) is not False

    visible_stories = [name for name in stories if owner_visible(name)]
    require(visible_stories, "browser preview has no owner-visible stories")

    options = "".join(
        f'<option value="{escape(name)}">{escape(story_value(name, "label_zh", name))}</option>'
        for name in visible_stories)
    slides = "\n".join(
        f'<figure data-score="{escape(record["score"])}" data-duration="{record["duration_ms"]}"><img src="{escape(record["png"])}" alt="{escape(story_value(record["score"], "label_zh", record["score"]))} {escape(record["cue"])}"><figcaption>{escape(story_value(record["score"], "label_zh", record["score"]))} / {escape(record["cue"])} / {record["duration_ms"]} ms</figcaption></figure>'
        for record in frame_records if owner_visible(record["score"]))
    atlas_cards: list[str] = []
    for name in visible_stories:
        story_records = [record for record in frame_records if record["score"] == name]
        overview_step = metadata.get(name, {}).get("overview_step", len(story_records) - 1) if isinstance(metadata, dict) else len(story_records) - 1
        if not isinstance(overview_step, int) or not 0 <= overview_step < len(story_records):
            overview_step = len(story_records) - 1
        record = story_records[overview_step]
        label = story_value(name, "label_zh", name)
        summary = story_value(name, "summary_zh", "")
        atlas_cards.append(
            f'<article><img src="{escape(record["png"])}" alt="{escape(label)}"><h2>{escape(label)}</h2><p>{escape(summary)}</p></article>')
    wall = ""
    wall_script = ""
    if all_performance_wall:
        wall_data: dict[str, list[dict[str, Any]]] = {}
        wall_cards: list[str] = []
        for name in visible_stories:
            story_records = [record for record in frame_records if record["score"] == name]
            require(story_records, f"missing owner-visible dynamic story: {name}")
            wall_data[name] = [{"src": record["png"], "cue": record["cue"], "phase": record.get("phase", "hold"),
                                "duration_ms": record["duration_ms"]} for record in story_records]
            first = story_records[0]
            label = story_value(name, "label_zh", name)
            wall_cards.append(
                f'<article class="performance-card" data-score="{escape(name)}">'
                f'<div class="performance-frame" data-touch-surface="true" role="application" aria-label="{escape(label)}">'
                f'<img class="performance-frame-image" src="{escape(first["png"])}" alt="{escape(label)}">'
                f'<img class="performance-frame-gaze" alt="" hidden>'
                f'</div>'
                f'<h3>{escape(label)}</h3><p class="performance-stage">{escape(first.get("phase", "hold"))} / {escape(first["cue"])} / {first["duration_ms"]} ms</p>'
                f'<p>{escape(story_value(name, "summary_zh", ""))}</p></article>')
        wall = f'''<section id="performance-wall"><h2>全部动态编舞</h2><p>16 个可见情绪和功能故事同时播放；每张图都由同一套 200x200 组件计划实时切帧。</p><div id="performance-grid">{"".join(wall_cards)}</div></section>'''
        touch_json = touch_gaze_package or {"overlays": {}, "bases": {}, "center_key": "1,0,1,0"}
        wall_script = f'''const wallData={json.dumps(wall_data, ensure_ascii=False)};const touchData={json.dumps(touch_json, ensure_ascii=False)};function touchPoint(stage,event){{const rect=stage.getBoundingClientRect();return {{x:Math.max(0,Math.min(199,Math.round((event.clientX-rect.left)/rect.width*199))),y:Math.max(0,Math.min(199,Math.round((event.clientY-rect.top)/rect.height*199)))}};}}function touchTarget(point){{const x=point.x,y=point.y;function axis(value,negative,positive,center){{if(value<=100)return center+Math.round((value-100)*(center-negative)/100);return center+Math.round((value-100)*(positive-center)/99);}}return {{primary_x:axis(x,-2,5,1),primary_y:axis(y,-3,4,0),sparkle_x:axis(x,-6,5,1),sparkle_y:axis(y,-6,6,0)}};}}function targetKey(target){{return [target.primary_x,target.primary_y,target.sparkle_x,target.sparkle_y].join(',');}}for(const card of document.querySelectorAll('.performance-card')){{const frames=wallData[card.dataset.score]||[];const stage=card.querySelector('.performance-frame');const image=card.querySelector('.performance-frame-image');const gaze=card.querySelector('.performance-frame-gaze');const status=card.querySelector('.performance-stage');const state={{index:0,timer:0,touching:false}};function show(frame){{image.hidden=false;image.src=frame.src;gaze.hidden=true;status.textContent=frame.phase+' / '+frame.cue+' / '+frame.duration_ms+' ms';}}function play(){{if(state.touching||!frames.length)return;const frame=frames[state.index];show(frame);state.index=(state.index+1)%frames.length;state.timer=window.setTimeout(play,frame.duration_ms);}}function follow(event){{const point=touchPoint(stage,event),target=touchTarget(point),key=targetKey(target),frame=frames[Math.max(0,state.index-1)%frames.length];const base=((touchData.bases[card.dataset.score]||{{}})[String(Math.max(0,state.index-1)%frames.length)]);const overlay=touchData.overlays[key];if(!frame||!base||!overlay)return;image.src=base;image.hidden=false;gaze.src=overlay;gaze.hidden=false;status.textContent=frame.phase+' / 触摸看向 ('+point.x+','+point.y+')';}}function release(){{state.touching=false;const center=touchData.overlays[touchData.center_key];const frame=frames[Math.max(0,state.index-1)%frames.length];const base=((touchData.bases[card.dataset.score]||{{}})[String(Math.max(0,state.index-1)%frames.length)]);if(frame&&base&&center){{image.src=base;image.hidden=false;gaze.src=center;gaze.hidden=false;status.textContent=frame.phase+' / 释放回正中';}}window.clearTimeout(state.timer);state.timer=window.setTimeout(play,260);}}stage.addEventListener('pointerdown',event=>{{state.touching=true;window.clearTimeout(state.timer);stage.setPointerCapture(event.pointerId);follow(event);}});stage.addEventListener('pointermove',event=>{{if(state.touching&&event.buttons!==0)follow(event);}});stage.addEventListener('pointerup',release);stage.addEventListener('pointercancel',release);stage.addEventListener('lostpointercapture',release);play();}}'''
    title = str(preview_zh.get("title", "V9 Component-Rig Preview")) if isinstance(preview_zh, dict) else "V9 Component-Rig Preview"
    player_label = str(preview_zh.get("player_label", "Story")) if isinstance(preview_zh, dict) else "Story"
    restart_label = str(preview_zh.get("restart_label", "Restart")) if isinstance(preview_zh, dict) else "Restart"
    atlas_title = str(preview_zh.get("atlas_title", "Stories")) if isinstance(preview_zh, dict) else "Stories"
    atlas_summary = str(preview_zh.get("atlas_summary", "")) if isinstance(preview_zh, dict) else ""
    language = "zh-CN" if isinstance(preview_zh, dict) else "en"
    output.write_text(f'''<!doctype html>
<html lang="{language}"><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;margin:20px;background:#f5f5f2;color:#171717}}main{{max-width:980px;margin:auto}}header{{display:flex;align-items:center;gap:8px;margin-bottom:12px}}h1{{font-size:22px;margin:0}}select,button{{height:32px;border:1px solid #222;background:#fff;font:14px Arial,sans-serif}}button{{width:32px}}#player{{background:#fff;border:1px solid #222;padding:12px;display:inline-block}}#player img{{width:400px;height:400px;image-rendering:pixelated;display:block}}figcaption{{padding-top:8px;font-family:monospace}}#strip{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}#strip img{{width:100px;height:100px;border:1px solid #777;image-rendering:pixelated}}#strip figure{{margin:0}}#performance-wall{{margin-top:28px;border-top:1px solid #777;padding-top:18px}}#performance-wall h2{{font-size:20px;margin:0 0 6px}}#performance-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}.performance-card{{background:#fff;border:1px solid #777;padding:8px;min-width:0}}.performance-frame{{position:relative;display:block;width:100%;max-width:200px;aspect-ratio:1;image-rendering:pixelated;background:#fff;touch-action:none;cursor:crosshair;overflow:hidden}}.performance-frame-image,.performance-frame-gaze{{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated}}.performance-card h3{{font-size:15px;margin:7px 0 4px}}.performance-card p{{font-size:12px;line-height:1.4;margin:4px 0}}.performance-stage{{font-family:monospace;min-height:30px}}</style>
<main><header><h1>{escape(title)}</h1>{'' if all_performance_wall else f'<label for="story">{escape(player_label)}</label><select id="story" aria-label="{escape(player_label)}">{options}</select><button id="restart" type="button" title="{escape(restart_label)}" aria-label="{escape(restart_label)}">&#8635;</button>'}</header>{wall}{'' if all_performance_wall else f'<section id="player"></section><section id="strip">{slides}</section><section id="atlas"><h2>{escape(atlas_title)}</h2><p>{escape(atlas_summary)}</p><div id="atlas-grid">{"".join(atlas_cards)}</div></section>'}</main>
<script>{wall_script if all_performance_wall else "const all=[...document.querySelectorAll('#strip figure')],player=document.querySelector('#player'),select=document.querySelector('#story'),restart=document.querySelector('#restart');let frames=[],index=0,timer=0;function visible(){for(const frame of all)frame.hidden=frame.dataset.score!==select.value;}function show(){const frame=frames[index];player.replaceChildren(frame.cloneNode(true));timer=setTimeout(()=>{if(index+1>=frames.length&&select.value==='menu_entry_notice'){player.replaceChildren();return;}index=(index+1)%frames.length;show();},Number(frame.dataset.duration));}function choose(reset){clearTimeout(timer);frames=all.filter(frame=>frame.dataset.score===select.value);if(reset)index=0;visible();show();}select.addEventListener('change',()=>choose(true));restart.addEventListener('click',()=>choose(true));choose(true);"}</script></html>
''', encoding="utf-8")


def render_single_epaper_html(output: Path, frame_records: list[dict[str, Any]],
                              preview_zh: dict[str, Any] | None,
                              touch_gaze_package: dict[str, Any]) -> None:
    """Render one source-backed 200x200 e-paper viewport with deterministic browse/touch input."""
    metadata = preview_zh.get("stories", {}) if isinstance(preview_zh, dict) else {}
    story_names = list(dict.fromkeys(record["score"] for record in frame_records))
    visible_names = [name for name in story_names
                     if not isinstance(metadata.get(name, {}), dict) or metadata.get(name, {}).get("owner_visible", True) is not False]
    require(visible_names, "single e-paper preview has no owner-visible stories")

    def label(name: str) -> str:
        value = metadata.get(name, {}) if isinstance(metadata, dict) else {}
        return str(value.get("label_zh", name)) if isinstance(value, dict) else name

    def summary(name: str) -> str:
        value = metadata.get(name, {}) if isinstance(metadata, dict) else {}
        return str(value.get("summary_zh", "")) if isinstance(value, dict) else ""

    story_data: list[dict[str, Any]] = []
    for name in visible_names:
        story_data.append({
            "name": name,
            "label": label(name),
            "summary": summary(name),
            "frames": [{"src": record["png"], "cue": record["cue"],
                         "phase": record.get("phase", "hold"), "duration_ms": record["duration_ms"]}
                        for record in frame_records if record["score"] == name],
        })
    story_json = json.dumps(story_data, ensure_ascii=False)
    touch_json = json.dumps(touch_gaze_package, ensure_ascii=False)
    title = str(preview_zh.get("title", "V9 200×200 水墨屏表情预览")) if isinstance(preview_zh, dict) else "V9 200x200 E-paper Preview"
    template = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
.epaper-screen img{pointer-events:none;user-select:none;-webkit-user-drag:none}
*{box-sizing:border-box}body{margin:0;background:#e9e9e5;color:#161616;font-family:Arial,sans-serif}main{width:min(620px,100%);margin:0 auto;padding:28px 20px 36px}h1{font-size:24px;line-height:1.2;margin:0 0 18px;font-weight:700}p{margin:0}.epaper-device{background:#f7f7f3;border:1px solid #8a8a84;padding:18px;box-shadow:3px 3px 0 #c4c4bc}.epaper-screen{position:relative;width:400px;height:400px;max-width:100%;margin:0 auto;background:#fff;border:2px solid #222;touch-action:none;cursor:crosshair;image-rendering:pixelated;overflow:hidden}.epaper-screen img{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated}.epaper-screen img[hidden]{display:none}.screen-meta{display:flex;justify-content:space-between;gap:12px;margin-top:13px;font:14px/1.4 monospace;min-height:20px}.screen-label{font-weight:700;font-family:Arial,sans-serif;font-size:18px}.screen-summary{margin-top:8px;min-height:22px;font:13px/1.45 Arial,sans-serif}.screen-hint{margin-top:16px;color:#45453f;font:12px/1.4 monospace}.story-dots{display:flex;flex-wrap:wrap;gap:5px;margin-top:16px;justify-content:center}.story-dots i{display:block;width:7px;height:7px;border:1px solid #555;background:#fff}.story-dots i.active{background:#111}
</style>
<main><h1>__TITLE__ · Touch fail-safe r7 · v45-touch-failsafe-r7-20260721</h1><section class="epaper-device" aria-label="200x200 monochrome e-paper expression viewport"><div id="epaper-screen" class="epaper-screen" data-review-revision="v45-touch-failsafe-r7" data-cache-review="v45-touch-failsafe-r7-20260721" data-canvas="200x200" data-touch-surface="true" role="application" aria-label="200x200 水墨屏表情视口"><img id="epaper-frame" draggable="false" alt=""><img id="epaper-frame-staging" draggable="false" alt="" hidden aria-hidden="true"><img id="epaper-gaze" draggable="false" alt="" hidden></div><div class="screen-meta"><span id="screen-label" class="screen-label"></span><span id="screen-status"></span></div><p id="screen-summary" class="screen-summary"></p><p class="screen-hint">轻触/拖动：注视触点　横向或纵向滑动：浏览表情</p><div id="story-dots" class="story-dots" aria-hidden="true"></div></section></main>
<script>
const stories=__STORIES__;const touchData=__TOUCH__;const reviewRevision='v45-touch-failsafe-r7-20260721';const screen=document.querySelector('#epaper-screen');const frameImage=document.querySelector('#epaper-frame');const frameStaging=document.querySelector('#epaper-frame-staging');const gazeImage=document.querySelector('#epaper-gaze');const labelNode=document.querySelector('#screen-label');const statusNode=document.querySelector('#screen-status');const summaryNode=document.querySelector('#screen-summary');const dotsNode=document.querySelector('#story-dots');let storyIndex=0;let frameIndex=0;let timer=0;let touching=false;let mouseDown=false;let startPoint=null;let lastPoint=null;let activeFrame=null;let activeFrameIndex=-1;let activeBaseSrc='';let activeFrameStartedAt=0;let activeFrameDurationMs=0;let pausedRemainingMs=0;let renderRequest=0;let gazeRequest=0;const touchCache=new Map();const trace=[];
function record(kind,extra){const item=Object.assign({kind:kind,t_ms:Math.round(performance.now()),story_index:storyIndex,active_frame_index:activeFrameIndex,active_frame_cue:activeFrame?activeFrame.cue:null},extra||{});trace.push(item);if(trace.length>240)trace.shift();screen.dataset.storyIndex=String(storyIndex);screen.dataset.activeFrameCue=activeFrame?activeFrame.cue:''}
function debugState(){return{revision:reviewRevision,page_review:new URLSearchParams(window.location.search).get('review'),story_index:storyIndex,next_frame_index:frameIndex,active_frame_index:activeFrameIndex,active_frame_cue:activeFrame?activeFrame.cue:null,active_base_src:activeBaseSrc,touching:touching,remaining_ms:Math.max(0,Math.round(pausedRemainingMs)),gaze_hidden:gazeImage.hidden,render_request:renderRequest}}
window.__v45TouchState=debugState;window.__v45TouchTrace=trace;
function cached(src){return src+(src.indexOf('?')>=0?'&':'?')+'review='+encodeURIComponent(reviewRevision)}
for(let index=0;index<stories.length;index++){const dot=document.createElement('i');dot.dataset.index=String(index);dotsNode.appendChild(dot)}
function story(){return stories[storyIndex]}
function point(event){const rect=screen.getBoundingClientRect();return{x:Math.max(0,Math.min(199,Math.round((event.clientX-rect.left)/rect.width*199))),y:Math.max(0,Math.min(199,Math.round((event.clientY-rect.top)/rect.height*199)))}}
function target(point){function axis(value,negative,positive,center){if(value<=100)return center+Math.round((value-100)*(center-negative)/100);return center+Math.round((value-100)*(positive-center)/99)}return{primary_x:axis(point.x,-2,5,1),primary_y:axis(point.y,-3,4,0),sparkle_x:axis(point.x,-6,5,1),sparkle_y:axis(point.y,-6,6,0)}}
function targetKey(value){return[value.primary_x,value.primary_y,value.sparkle_x,value.sparkle_y].join(',')}
function currentFrame(){return activeFrame}
function waitPaint(){return new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))}
function waitForImage(image){if(image.complete)return Promise.resolve(image.naturalWidth>0);return new Promise(resolve=>{image.addEventListener('load',()=>resolve(true),{once:true});image.addEventListener('error',()=>resolve(false),{once:true})})}
async function decodeImage(image){if(!image||!image.complete||image.naturalWidth<=0)return false;if(typeof image.decode==='function'){try{await image.decode()}catch{return false}}return image.complete&&image.naturalWidth>0}
function loadAsset(src){if(!src)return Promise.resolve(false);let ready=touchCache.get(src);if(!ready){const asset=new Image();ready=new Promise(resolve=>{asset.addEventListener('load',()=>resolve(true),{once:true});asset.addEventListener('error',()=>resolve(false),{once:true});asset.src=cached(src)}).then(ok=>ok?decodeImage(asset):false);touchCache.set(src,ready)}return ready}
async function presentBase(src,request){if(!src||request!==renderRequest)return false;if(activeBaseSrc===src&&!frameImage.hidden&&await decodeImage(frameImage))return true;const url=cached(src);frameStaging.hidden=true;frameStaging.src=url;if(!await waitForImage(frameStaging)||!await decodeImage(frameStaging)){record('base_load_failed',{src:src});return false}if(request!==renderRequest)return false;frameImage.src=url;frameImage.hidden=false;activeBaseSrc=src;record('base_presented',{src:src});return true}
function setChrome(frame,extra){labelNode.textContent=story().label;statusNode.textContent=(extra||((frame.phase||'hold')+' / '+frame.cue+' / '+frame.duration_ms+' ms'));summaryNode.textContent=story().summary;for(const dot of dotsNode.children)dot.classList.toggle('active',Number(dot.dataset.index)===storyIndex)}
function showGaze(overlay,label,mode){const request=++gazeRequest;gazeImage.hidden=true;if(label&&activeFrame)setChrome(activeFrame,label);if(!overlay){record('gaze_fail_closed',{mode:mode});return}loadAsset(overlay).then(async ok=>{if(!ok||request!==gazeRequest){if(!ok)record('gaze_fail_closed',{mode:mode});return}gazeImage.src=cached(overlay);if(await decodeImage(gazeImage)&&request===gazeRequest&&(mode==='idle'||mode==='touch'||mode==='release')){gazeImage.hidden=false;await waitPaint();if(request===gazeRequest){record('gaze_presented',{mode:mode,overlay:overlay})}else{gazeImage.hidden=true;}}else{gazeImage.hidden=true;record('gaze_fail_closed',{mode:mode})}})}
function baseFor(index){return((touchData.bases[story().name]||{})[String(index)])||story().frames[index].src}
function showFrame(extra){if(touching)return;const frames=story().frames;const next=frameIndex%frames.length;const frame=frames[next];const request=++renderRequest;gazeRequest++;gazeImage.hidden=true;const baseSrc=baseFor(next);presentBase(baseSrc,request).then(ok=>{if(!ok||touching||request!==renderRequest)return;activeFrame=frame;activeFrameIndex=next;frameIndex=(next+1)%frames.length;activeFrameStartedAt=performance.now();activeFrameDurationMs=frame.duration_ms;pausedRemainingMs=frame.duration_ms;setChrome(frame,extra);record('frame_presented',{cue:frame.cue,phase:frame.phase,duration_ms:frame.duration_ms});showGaze(touchData.overlays[touchData.center_key],null,'idle');window.clearTimeout(timer);timer=window.setTimeout(showFrame,frame.duration_ms)})}
function showTouch(frame,baseSrc,overlay,label,mode){if(!frame||!baseSrc)return;setChrome(frame,label);showGaze(overlay,label,mode||'touch')}
function follow(event){const p=point(event);lastPoint=p;const mapped=target(p);const baseSrc=activeBaseSrc;const overlay=touchData.overlays[targetKey(mapped)];const frame=currentFrame();if(!frame||!baseSrc)return;showTouch(frame,baseSrc,overlay,'触摸注视 ('+p.x+','+p.y+')','touch')}
function pauseCurrentFrame(){window.clearTimeout(timer);if(activeFrame)pausedRemainingMs=Math.max(0,Math.round(activeFrameDurationMs-(performance.now()-activeFrameStartedAt)));record('touch_pause',{remaining_ms:pausedRemainingMs})}
function centerAndResume(){const frame=currentFrame();const center=touchData.overlays[touchData.center_key];const resumeDelay=Math.max(180,pausedRemainingMs);if(frame)showTouch(frame,activeBaseSrc,center,'释放回正中','release');record('touch_release',{resume_delay_ms:resumeDelay,frame_cue:frame?frame.cue:null,story_index:storyIndex});window.clearTimeout(timer);timer=window.setTimeout(()=>{if(!touching)showFrame()},resumeDelay)}
function browse(direction){storyIndex=(storyIndex+direction+stories.length)%stories.length;frameIndex=0;activeFrame=null;activeFrameIndex=-1;activeBaseSrc='';gazeRequest++;gazeImage.hidden=true;window.clearTimeout(timer);record('story_browse',{direction:direction,story_index:storyIndex});showFrame('过渡 / '+(direction>0?'下一表情':'上一表情'))}
function release(event){if(!touching)return;touching=false;const end=event?point(event):lastPoint||startPoint;const origin=startPoint||end;const dx=end.x-origin.x;const dy=end.y-origin.y;if(Math.max(Math.abs(dx),Math.abs(dy))>=24){const direction=Math.abs(dx)>=Math.abs(dy)?(dx>0?1:-1):(dy>0?1:-1);startPoint=null;lastPoint=null;browse(direction);return}startPoint=null;lastPoint=null;centerAndResume()}
function begin(event){if(event.button!==undefined&&event.button!==0)return;if(touching)return;if(!activeFrame||frameImage.hidden||!frameImage.complete||!frameImage.naturalWidth)return;event.preventDefault();touching=true;pauseCurrentFrame();record('touch_begin',{story_index:storyIndex,frame_cue:activeFrame.cue});startPoint=point(event);lastPoint=startPoint;if(event.pointerId!==undefined){try{screen.setPointerCapture(event.pointerId)}catch{}}follow(event)}
function move(event){if(touching){event.preventDefault();follow(event)}}
function end(event){mouseDown=false;release(event)}
screen.addEventListener('dragstart',event=>event.preventDefault());screen.addEventListener('pointerdown',event=>{if(event.pointerType!=='mouse')begin(event)});screen.addEventListener('pointermove',event=>{if(event.pointerType!=='mouse')move(event)});screen.addEventListener('pointerup',event=>{if(event.pointerType!=='mouse')end(event)});screen.addEventListener('pointercancel',event=>{if(event.pointerType!=='mouse')end(event)});screen.addEventListener('lostpointercapture',()=>{if(touching&&!mouseDown)release(null)});screen.addEventListener('mousedown',event=>{event.preventDefault();mouseDown=true;begin(event)});screen.addEventListener('mousemove',event=>{if(mouseDown)move(event)});screen.addEventListener('mouseup',end);window.addEventListener('mouseup',event=>{if(mouseDown)end(null)});
for(const item of stories){for(let index=0;index<item.frames.length;index++){loadAsset((touchData.bases[item.name]||{})[String(index)]||item.frames[index].src)}}for(const overlay of Object.values(touchData.overlays)){loadAsset(overlay)}record('page_ready',{revision:reviewRevision});showFrame();
</script></html>"""
    html = (template.replace("__TITLE__", escape(title))
            .replace("__STORIES__", story_json)
            .replace("__TOUCH__", touch_json))
    output.write_text(html, encoding="utf-8")


def render_centered_gallery_html(output: Path, frame_records: list[dict[str, Any]],
                                 preview_zh: dict[str, Any] | None,
                                 touch_gaze_package: dict[str, Any]) -> None:
    """Render one live viewport plus one centered representative for each visible story."""
    metadata = preview_zh.get("stories", {}) if isinstance(preview_zh, dict) else {}
    story_names = list(dict.fromkeys(record["score"] for record in frame_records))
    visible_names = [name for name in story_names
                     if not isinstance(metadata.get(name, {}), dict) or
                     metadata.get(name, {}).get("owner_visible", True) is not False]
    require(len(visible_names) == 16, f"expected 16 owner-visible stories, got {len(visible_names)}")

    def story_meta(name: str) -> dict[str, Any]:
        value = metadata.get(name, {})
        return value if isinstance(value, dict) else {}

    def representative(name: str) -> dict[str, Any]:
        records = [record for record in frame_records if record["score"] == name]
        step = story_meta(name).get("overview_step", len(records) - 1)
        if not isinstance(step, int) or not 0 <= step < len(records):
            step = len(records) - 1
        return records[step]

    story_data: list[dict[str, Any]] = []
    gallery: list[str] = []
    for name in visible_names:
        story_records = [record for record in frame_records if record["score"] == name]
        item = story_meta(name)
        rep = representative(name)
        story_data.append({
            "name": name,
            "label": str(item.get("label_zh", name)),
            "summary": str(item.get("summary_zh", "")),
            "source_anchor": rep["source_anchor"],
            "normalization_offset": rep["normalization_offset"],
            "frames": [{"src": record["png"], "touch_base": record["touch_base"],
                        "cue": record["cue"], "phase": record.get("phase", "hold"),
                        "duration_ms": record["duration_ms"]} for record in story_records],
        })
        gallery.append(
            f'<button class="story-option" type="button" data-story="{escape(name)}" '
            f'aria-pressed="false"><img src="{escape(rep["png"])}" alt="{escape(str(item.get("label_zh", name)))}" '
            f'data-representative="true"><span><strong>{escape(str(item.get("label_zh", name)))}</strong>'
            f'<small>{escape(str(item.get("summary_zh", "")))}</small></span></button>')

    title = str(preview_zh.get("title", "V9 200×200 水墨屏表情预览")) if isinstance(preview_zh, dict) else "V9 200x200 E-paper Preview"
    story_json = json.dumps(story_data, ensure_ascii=False)
    touch_json = json.dumps(touch_gaze_package, ensure_ascii=False)
    template = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#e9e9e5;color:#161616;font-family:Arial,sans-serif}main{width:min(760px,100%);margin:0 auto;padding:24px 18px 36px}h1{font-size:24px;line-height:1.2;margin:0 0 18px}.epaper-device{display:flex;flex-direction:column;align-items:center}.epaper-screen{position:relative;width:200px;height:200px;background:#fff;border:2px solid #222;touch-action:none;cursor:crosshair;image-rendering:pixelated;overflow:hidden}.epaper-screen img{position:absolute;inset:0;width:200px;height:200px;image-rendering:pixelated;pointer-events:none;user-select:none;-webkit-user-drag:none}.epaper-screen img[hidden]{display:none}.screen-meta{width:100%;max-width:520px;display:flex;justify-content:space-between;gap:12px;margin-top:12px;font:14px/1.4 monospace;min-height:20px}.screen-label{font-weight:700;font-family:Arial,sans-serif;font-size:18px}.screen-summary{width:100%;max-width:520px;margin-top:6px;font:13px/1.45 Arial,sans-serif;min-height:22px}.screen-hint{width:100%;max-width:520px;margin-top:12px;color:#45453f;font:12px/1.4 monospace}.gallery-title{margin:28px 0 10px;font-size:20px}.story-gallery{display:flex;flex-direction:column;gap:12px}.story-option{display:grid;grid-template-columns:200px minmax(0,1fr);gap:16px;align-items:center;width:100%;padding:0 0 12px;border:0;border-bottom:1px solid #8a8a84;background:transparent;color:inherit;text-align:left;cursor:pointer}.story-option img{display:block;width:200px;height:200px;background:#fff;image-rendering:pixelated}.story-option span{display:flex;flex-direction:column;gap:8px;min-width:0}.story-option strong{font-size:17px}.story-option small{font-size:13px;line-height:1.5}.story-option[aria-pressed="true"] img{outline:3px solid #161616;outline-offset:-3px}.story-option:focus-visible{outline:2px solid #161616;outline-offset:4px}@media(max-width:480px){main{padding:18px 12px 28px}h1{font-size:21px}.story-option{grid-template-columns:200px minmax(0,1fr);gap:10px}.story-option strong{font-size:15px}.story-option small{font-size:12px}}
</style>
<main><h1>__TITLE__ · 居中表情总览</h1><section class="epaper-device" aria-label="200x200 monochrome e-paper expression viewport"><div id="epaper-screen" class="epaper-screen" data-review-revision="v45-centered-gallery-r1" data-canvas="200x200" data-touch-surface="true" role="application" aria-label="200x200 水墨屏表情视口"><img id="epaper-frame" draggable="false" alt=""><img id="epaper-frame-staging" draggable="false" alt="" hidden aria-hidden="true"><img id="epaper-gaze" draggable="false" alt="" hidden></div><div class="screen-meta"><span id="screen-label" class="screen-label"></span><span id="screen-status"></span></div><p id="screen-summary" class="screen-summary"></p><p class="screen-hint">按住并拖动：只改变眼神高光；松开回到正中并继续当前表情。</p></section><h2 class="gallery-title">全部 16 个表情</h2><section id="story-gallery" class="story-gallery" aria-label="全部 16 个 owner-visible stories">__GALLERY__</section></main>
<script>
const stories=__STORIES__;const touchData=__TOUCH__;const screen=document.querySelector('#epaper-screen');const frameImage=document.querySelector('#epaper-frame');const frameStaging=document.querySelector('#epaper-frame-staging');const gazeImage=document.querySelector('#epaper-gaze');const labelNode=document.querySelector('#screen-label');const statusNode=document.querySelector('#screen-status');const summaryNode=document.querySelector('#screen-summary');const gallery=document.querySelector('#story-gallery');let storyIndex=0;let frameIndex=0;let timer=0;let touching=false;let mouseDown=false;let startPoint=null;let lastPoint=null;let activeFrame=null;let activeFrameIndex=-1;let activeBaseSrc='';let activeFrameStartedAt=0;let activeFrameDurationMs=0;let pausedRemainingMs=0;let renderRequest=0;let gazeRequest=0;const touchCache=new Map();const trace=[];
function record(kind,extra){const item=Object.assign({kind:kind,t_ms:Math.round(performance.now()),story_index:storyIndex,active_frame_index:activeFrameIndex,active_frame_cue:activeFrame?activeFrame.cue:null},extra||{});trace.push(item);if(trace.length>240)trace.shift();screen.dataset.storyIndex=String(storyIndex);screen.dataset.activeFrameCue=activeFrame?activeFrame.cue:''}
function debugState(){return{revision:'v45-centered-gallery-r1',story_index:storyIndex,story_name:stories[storyIndex]?stories[storyIndex].name:null,next_frame_index:frameIndex,active_frame_index:activeFrameIndex,active_frame_cue:activeFrame?activeFrame.cue:null,active_base_src:activeBaseSrc,touching:touching,remaining_ms:Math.max(0,Math.round(pausedRemainingMs)),gaze_hidden:gazeImage.hidden,render_request:renderRequest}}
window.__v45TouchState=debugState;window.__v45TouchTrace=trace;
function cached(src){return src+(src.indexOf('?')>=0?'&':'?')+'review=v45-centered-gallery-r1'}function story(){return stories[storyIndex]}function point(event){const rect=screen.getBoundingClientRect();return{x:Math.max(0,Math.min(199,Math.round((event.clientX-rect.left)/rect.width*199))),y:Math.max(0,Math.min(199,Math.round((event.clientY-rect.top)/rect.height*199)))}}
function target(value){function axis(v,negative,positive,center){if(v<=100)return center+Math.round((v-100)*(center-negative)/100);return center+Math.round((v-100)*(positive-center)/99)}return{primary_x:axis(value.x,-2,5,1),primary_y:axis(value.y,-3,4,0),sparkle_x:axis(value.x,-6,5,1),sparkle_y:axis(value.y,-6,6,0)}}function targetKey(value){return[value.primary_x,value.primary_y,value.sparkle_x,value.sparkle_y].join(',')}function waitPaint(){return new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))}function waitForImage(image){if(image.complete)return Promise.resolve(image.naturalWidth>0);return new Promise(resolve=>{image.addEventListener('load',()=>resolve(true),{once:true});image.addEventListener('error',()=>resolve(false),{once:true})})}async function decodeImage(image){if(!image||!image.complete||image.naturalWidth<=0)return false;if(typeof image.decode==='function'){try{await image.decode()}catch{return false}}return image.complete&&image.naturalWidth>0}
function frameAt(index){return story().frames[index%story().frames.length]}function showChrome(frame,extra){labelNode.textContent=story().label;summaryNode.textContent=story().summary;statusNode.textContent=extra||((frame.phase||'hold')+' / '+frame.cue+' / '+frame.duration_ms+' ms');for(const item of gallery.children)item.setAttribute('aria-pressed',item.dataset.story===story().name?'true':'false')}
async function presentBase(src,request){if(!src||request!==renderRequest)return false;if(activeBaseSrc===src&&!frameImage.hidden&&await decodeImage(frameImage))return true;const url=cached(src);frameStaging.hidden=true;frameStaging.src=url;if(!await waitForImage(frameStaging)||!await decodeImage(frameStaging)){record('base_load_failed',{src:src});return false}if(request!==renderRequest)return false;frameImage.src=url;frameImage.hidden=false;activeBaseSrc=src;record('base_presented',{src:src});return true}
function showGaze(overlay,label,mode){const request=++gazeRequest;gazeImage.hidden=true;if(label&&activeFrame)showChrome(activeFrame,label);if(!overlay){record('gaze_fail_closed',{mode:mode});return}gazeImage.style.transform='translate('+touchData.story_offsets[story().name][0]+'px,'+touchData.story_offsets[story().name][1]+'px)';gazeImage.src=cached(overlay);gazeImage.hidden=false;waitPaint().then(()=>{if(request===gazeRequest&&!gazeImage.hidden)record('gaze_presented',{mode:mode,overlay:overlay})})}
function baseFor(index){return frameAt(index).touch_base||frameAt(index).src}function showFrame(extra){if(touching)return;const next=frameIndex%story().frames.length;const frame=frameAt(next);const request=++renderRequest;gazeRequest++;gazeImage.hidden=true;presentBase(baseFor(next),request).then(ok=>{if(!ok||touching||request!==renderRequest)return;activeFrame=frame;activeFrameIndex=next;frameIndex=(next+1)%story().frames.length;activeFrameStartedAt=performance.now();activeFrameDurationMs=frame.duration_ms;pausedRemainingMs=frame.duration_ms;showChrome(frame,extra);record('frame_presented',{cue:frame.cue,phase:frame.phase,duration_ms:frame.duration_ms});showGaze(touchData.overlays[touchData.center_key],null,'idle');window.clearTimeout(timer);timer=window.setTimeout(showFrame,frame.duration_ms)})}
function follow(event){const mapped=target(point(event));const overlay=touchData.overlays[targetKey(mapped)];if(activeFrame&&activeBaseSrc)showGaze(overlay,'触摸注视','touch')}function pauseCurrentFrame(){window.clearTimeout(timer);if(activeFrame)pausedRemainingMs=Math.max(0,Math.round(activeFrameDurationMs-(performance.now()-activeFrameStartedAt)));record('touch_pause',{remaining_ms:pausedRemainingMs})}function centerAndResume(){const frame=activeFrame;const center=touchData.overlays[touchData.center_key];if(frame)showGaze(center,'释放回正中','release');record('touch_release',{resume_delay_ms:Math.max(180,pausedRemainingMs),frame_cue:frame?frame.cue:null,story_index:storyIndex});window.clearTimeout(timer);window.setTimeout(()=>{if(!touching)showFrame()},Math.max(180,pausedRemainingMs))}
function chooseStory(name){const next=stories.findIndex(item=>item.name===name);if(next<0||next===storyIndex&&activeFrame)return;window.clearTimeout(timer);storyIndex=next;frameIndex=0;activeFrame=null;activeFrameIndex=-1;activeBaseSrc='';gazeRequest++;gazeImage.hidden=true;record('story_select',{story_name:name});showFrame('选择 / '+story().label)}function begin(event){if(event.button!==undefined&&event.button!==0)return;if(touching||!activeFrame||frameImage.hidden||!frameImage.complete||!frameImage.naturalWidth)return;event.preventDefault();touching=true;pauseCurrentFrame();record('touch_begin',{story_index:storyIndex,frame_cue:activeFrame.cue});startPoint=point(event);lastPoint=startPoint;if(event.pointerId!==undefined){try{screen.setPointerCapture(event.pointerId)}catch{}}follow(event)}function move(event){if(touching){event.preventDefault();lastPoint=point(event);follow(event)}}function end(event){mouseDown=false;if(!touching)return;touching=false;startPoint=null;lastPoint=null;centerAndResume()}
for(const item of gallery.children)item.addEventListener('click',()=>chooseStory(item.dataset.story));screen.addEventListener('dragstart',event=>event.preventDefault());screen.addEventListener('pointerdown',event=>{if(event.pointerType!=='mouse')begin(event)});screen.addEventListener('pointermove',event=>{if(event.pointerType!=='mouse')move(event)});screen.addEventListener('pointerup',event=>{if(event.pointerType!=='mouse')end(event)});screen.addEventListener('pointercancel',event=>{if(event.pointerType!=='mouse')end(event)});screen.addEventListener('mousedown',event=>{event.preventDefault();mouseDown=true;begin(event)});screen.addEventListener('mousemove',event=>{if(mouseDown)move(event)});screen.addEventListener('mouseup',end);window.addEventListener('mouseup',event=>{if(mouseDown)end(event)});for(const item of stories){for(const frame of item.frames){const base=frame.touch_base||frame.src;const image=new Image();image.src=cached(base)}for(const overlay of Object.values(touchData.overlays)){const image=new Image();image.src=cached(overlay)}}record('page_ready',{owner_visible_story_count:stories.length,anchor_policy:'whole_expression_visible_bbox_center',canonical_center:[100,100]});showFrame();
</script></html>"""
    html = (template.replace("__TITLE__", escape(title))
            .replace("__GALLERY__", "".join(gallery))
            .replace("__STORIES__", story_json)
            .replace("__TOUCH__", touch_json))
    output.write_text(html, encoding="utf-8")


def render_authority_wall_html(output: Path, frame_records: list[dict[str, Any]],
                               preview_zh: dict[str, Any] | None,
                               touch_gaze_package: dict[str, Any],
                               authority: dict[str, Any]) -> None:
    """Render the source-bound decision screen and independently animated story viewports."""
    metadata = preview_zh.get("stories", {}) if isinstance(preview_zh, dict) else {}
    story_names = list(dict.fromkeys(record["score"] for record in frame_records))
    visible_names = [name for name in story_names if not isinstance(metadata.get(name, {}), dict) or
                     metadata.get(name, {}).get("owner_visible", True) is not False]
    require(len(visible_names) == 16, f"expected 16 owner-visible stories, got {len(visible_names)}")

    def meta(name: str) -> dict[str, Any]:
        value = metadata.get(name, {})
        return value if isinstance(value, dict) else {}

    story_data: list[dict[str, Any]] = []
    story_rows: list[str] = []
    for name in visible_names:
        item = meta(name)
        records = [record for record in frame_records if record["score"] == name]
        story_data.append({
            "name": name,
            "label": str(item.get("label_zh", name)),
            "summary": str(item.get("summary_zh", "")),
            "frames": [{"src": record["png"], "touch_base": record["touch_base"], "cue": record["cue"],
                        "phase": record.get("phase", "hold"), "duration_ms": record["duration_ms"]} for record in records],
        })
        story_rows.append(
            f'<section class="story-row" data-story="{escape(name)}"><div class="story-copy"><h2>{escape(str(item.get("label_zh", name)))}</h2>'
            f'<p>{escape(str(item.get("summary_zh", "")))}</p><span class="story-status" data-status-for="{escape(name)}"></span></div>'
            f'<div class="live-viewport" data-viewport-story="{escape(name)}" data-touch-surface="true" role="application" aria-label="{escape(str(item.get("label_zh", name)))} 200x200 实时编舞">'
            '<img class="viewport-frame" draggable="false" alt=""><img class="viewport-staging" draggable="false" alt="" hidden aria-hidden="true"><img class="viewport-gaze" draggable="false" alt="" hidden></div></section>')

    authority["visual_story_map"] = {
        "calm": {"story": "calm_presence", "reason": "registered calm presence"},
        "curious": {"story": "curious_question", "reason": "registered curious story"},
        "affectionate": {"story": "warm_presence", "reason": "registered warm story"},
        "focused": {"story": "focused_presence", "reason": "registered focused story"},
        "sleepy": {"story": "sleepy_presence", "reason": "registered sleepy story"},
        "alert": {"story": "alert_exclamation", "reason": "registered alert story"},
        "joyful": {"story": "delighted_presence", "reason": "registered joyful story"},
        "playful": {"story": "playful_presence", "reason": "registered playful story"},
        "thinking": {"story": "thoughtful_presence", "reason": "registered thinking story"},
        "puzzled": {"story": "curious_question", "reason": "registered curious visual fallback for puzzled family"},
        "anticipatory": {"story": "curious_question", "reason": "registered curious visual fallback for anticipatory family"},
        "listening": {"story": "focused_presence", "reason": "registered focused visual fallback for listening family"},
    }
    title = str(preview_zh.get("title", "V9 200×200 水墨屏表情预览")) if isinstance(preview_zh, dict) else "V9 200x200 E-paper Preview"
    template = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#e9e9e5;color:#161616;font-family:Arial,sans-serif}main{width:min(820px,100%);margin:0 auto;padding:20px 16px 40px}h1{font-size:24px;line-height:1.2;margin:0 0 16px}.authority-head{display:grid;grid-template-columns:200px minmax(0,1fr);gap:18px;align-items:start}.live-viewport{position:relative;width:200px;height:200px;background:#fff;outline:none;touch-action:none;cursor:crosshair;image-rendering:pixelated;overflow:hidden;flex:0 0 200px}.live-viewport img{position:absolute;inset:0;width:200px;height:200px;image-rendering:pixelated;pointer-events:none;user-select:none;-webkit-user-drag:none}.live-viewport img[hidden]{display:none}.decision-panel{min-width:0;padding-top:8px}.emotion-current{font-size:22px;font-weight:700;min-height:28px}.emotion-rule{margin-top:10px;font:14px/1.5 monospace;min-height:24px}.gesture-status{margin-top:8px;color:#45453f;font:12px/1.4 monospace;min-height:18px}.screen-meta{display:flex;justify-content:space-between;gap:10px;margin-top:8px;font:12px/1.35 monospace}.story-wall-title{font-size:20px;margin:28px 0 10px}.story-wall{display:flex;flex-direction:column;gap:14px}.story-row{display:flex;flex-direction:row-reverse;justify-content:flex-end;gap:18px;align-items:center;border-bottom:1px solid #8a8a84;padding:0 0 14px}.story-copy{min-width:0;flex:1}.story-copy h2{font-size:18px;margin:0 0 8px}.story-copy p{font-size:13px;line-height:1.5;margin:0}.story-status{display:block;margin-top:10px;font:12px/1.3 monospace;min-height:16px}.story-row .live-viewport{order:0}.authority-source{margin-top:16px;color:#45453f;font:11px/1.4 monospace;word-break:break-word}@media(max-width:620px){main{padding:16px 10px 28px}h1{font-size:21px}.authority-head{grid-template-columns:200px minmax(0,1fr);gap:10px}.story-row{gap:10px}.story-copy h2{font-size:15px}.story-copy p{font-size:12px}}
</style>
<main><h1>__TITLE__ · 表情与注视</h1><section class="authority-head"><div><div id="overall-viewport" class="live-viewport" data-touch-surface="true" role="application" aria-label="总体 200x200 水墨屏"><img class="viewport-frame" draggable="false" alt=""><img class="viewport-staging" draggable="false" alt="" hidden aria-hidden="true"><img class="viewport-gaze" draggable="false" alt="" hidden></div><div class="screen-meta"><span id="overall-label"></span><span id="overall-status"></span></div></div><div class="decision-panel"><div id="emotion-current" class="emotion-current"></div><div id="emotion-rule" class="emotion-rule"></div><div id="gesture-status" class="gesture-status"></div><div class="authority-source">registered emotion and touch authority</div></div></section><h2 class="story-wall-title">全部 owner-visible expression stories · 每个独立实时 viewport</h2><section id="story-wall" class="story-wall">__STORY_ROWS__</section></main>
<script>
const stories=__STORIES__;const touchData=__TOUCH__;const authority=__AUTHORITY__;const gestureAuthority=authority.gesture_authority;const sourceRevision='v45-authority-wall-r2';const storyByName=new Map(stories.map(item=>[item.name,item]));const viewportStates={};const viewportTraceLimit=64;const imagePromises=new Map();
function cached(src){return src+(src.indexOf('?')>=0?'&':'?')+'review='+encodeURIComponent(sourceRevision)}function clamp(value,min,max){return Math.max(min,Math.min(max,value))}function imageReady(src){if(!imagePromises.has(src))imagePromises.set(src,new Promise(resolve=>{const image=new Image();const done=async()=>{try{if(image.decode)await image.decode()}catch{}resolve(image.complete&&image.naturalWidth===200)};image.addEventListener('load',done,{once:true});image.addEventListener('error',()=>resolve(false),{once:true});image.src=cached(src);if(image.complete)done()}));return imagePromises.get(src)}function ruleMatches(rule,affect,input){return rule.when.every(([name,op,value])=>op==='>='?affect[name]>=value:op==='>'?affect[name]>value:op==='<'?affect[name]<value:op==='=='?input[name]===value:false)}function updateAffect(input){const a={valence:Number(input.valence),arousal:Number(input.arousal),affinity:Math.max(Number(input.affinity),Number(input.interaction_memory))};switch(input.event){case'daily_auto':a.valence=a.valence===0?0:(a.valence>0?a.valence-1:a.valence+1);if(a.arousal>1)a.arousal-=1;if(Number(input.interaction_memory)<a.affinity&&a.affinity>0)a.affinity-=1;break;case'touch_tap':a.valence=clamp(a.valence+1,-2,2);a.arousal=Math.max(a.arousal,2);break;case'touch_swipe':a.valence=clamp(a.valence+1,-2,2);a.arousal=clamp(a.arousal+1,0,3);a.arousal=Math.max(a.arousal,2);break;case'recording_active':a.valence=a.valence===0?0:(a.valence>0?a.valence-1:a.valence+1);a.arousal=Math.max(a.arousal,2);break;case'menu_hold':case'upgrade_active':a.valence=a.valence===0?0:(a.valence>0?a.valence-1:a.valence+1);a.arousal=Math.max(a.arousal,1);break;case'sleep':a.arousal=0;break;case'wake':a.arousal=2;break;case'charging':a.arousal=0;break;case'error':a.valence=clamp(a.valence-1,-2,2);a.arousal=3;break}return a}
function decide(input){const affect=updateAffect(input);const rules=authority.target_rules[input.event]||[];const matched=rules.find(rule=>ruleMatches(rule,affect,input))||{emotion:'calm',branch:'fail_closed_no_registered_branch',when:[]};const visual=authority.visual_story_map[matched.emotion]||authority.visual_story_map.calm;return{input:Object.assign({},input),affect_after:affect,event_priority:authority.event_priority[input.event]??0,matched_branch:matched.branch,conditions_evaluated:rules.map(rule=>({branch:rule.branch,matched:rule===matched,when:rule.when})),emotion:matched.emotion,visual_story:visual.story,visual_mapping_reason:visual.reason}}
function point(stage,event){const rect=stage.getBoundingClientRect();return{x:clamp(Math.round((event.clientX-rect.left)/rect.width*199),0,199),y:clamp(Math.round((event.clientY-rect.top)/rect.height*199),0,199)}}function gazeKey(value){function axis(v,n,p,c){return v<=100?c+Math.round((v-100)*(c-n)/100):c+Math.round((v-100)*(p-c)/99)}return[axis(value.x,-2,5,1),axis(value.y,-3,4,0),axis(value.x,-6,5,1),axis(value.y,-6,6,0)].join(',')}
function record(state,kind,extra){state.trace.push(Object.assign({kind,t_ms:Math.round(performance.now()),story:state.storyName,frame:state.activeFrameIndex,cue:state.activeFrame?state.activeFrame.cue:null},extra||{}));if(state.trace.length>viewportTraceLimit)state.trace.shift()}
function classifyGesture(state,end){const start=state.gestureStart||end;const dx=Math.abs(end.x-start.x),dy=Math.abs(end.y-start.y),duration=Math.round(performance.now()-state.gestureStartedAt);const maxMove=Math.max(dx,dy);let gesture='none',attention='center';if(duration>=gestureAuthority.defaults.long_press_min_duration_ms&&maxMove<=gestureAuthority.defaults.long_press_max_move_px)gesture='long_press';else if(duration<=gestureAuthority.defaults.tap_max_duration_ms&&maxMove<=gestureAuthority.defaults.tap_max_move_px)gesture='tap';else if(duration<=gestureAuthority.defaults.swipe_max_duration_ms&&((state.gestureAxis==='x'&&dx>=gestureAuthority.defaults.swipe_min_move_px)||(state.gestureAxis==='y'&&dy>=gestureAuthority.defaults.swipe_min_move_px))){gesture='swipe';attention=state.gestureAxis==='x'?(end.x>=start.x?'right':'left'):(end.y>=start.y?'down':'up')}return{gesture,event:gesture==='tap'?'TOUCH_TAP':gesture==='swipe'?'TOUCH_SWIPE':null,attention,duration_ms:duration,dx,dy}}
function updateGestureAxis(state,current){if(state.gestureAxis)return;const start=state.gestureStart||current;const dx=Math.abs(current.x-start.x),dy=Math.abs(current.y-start.y);if(Math.max(dx,dy)<gestureAuthority.defaults.axis_lock_min_move_px)return;if(dx>=dy+gestureAuthority.defaults.axis_slop_px&&dx*100>=dy*gestureAuthority.defaults.axis_dominance_percent){state.gestureAxis='x'}else if(dy>=dx+gestureAuthority.defaults.axis_slop_px&&dy*100>=dx*gestureAuthority.defaults.axis_dominance_percent){state.gestureAxis='y'}}
function mountViewport(stage,storyName,labelNode,statusNode,scope){const state={scope,storyName,frameIndex:0,activeFrame:null,activeFrameIndex:-1,activeBaseSrc:'',activeFrameStartedAt:0,activeFrameDurationMs:0,pausedRemainingMs:0,timer:0,touching:false,mouseDown:false,request:0,gazeRequest:0,start:null,trace:[],framePresentCount:0,gestureStart:null,gestureStartedAt:0,gestureAxis:null,gestureSamples:0};viewportStates[scope]=state;const frame=stage.querySelector('.viewport-frame');const staging=stage.querySelector('.viewport-staging');const gaze=stage.querySelector('.viewport-gaze');const story=()=>storyByName.get(state.storyName);const paint=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
function chrome(item,extra){if(labelNode)labelNode.textContent=item?story().label:'';if(statusNode)statusNode.textContent=extra||`${item.phase||'hold'} / ${item.cue} / ${item.duration_ms} ms`;const status=document.querySelector(`[data-status-for="${CSS.escape(state.storyName)}"]`);if(status)status.textContent=`${item.phase||'hold'} / ${item.cue} / ${item.duration_ms} ms`}
async function presentComposite(baseSrc,overlaySrc,request,mode){if(request!==state.request||!baseSrc||!overlaySrc)return false;const offset=touchData.story_offsets[state.storyName]||[0,0];const ready=await Promise.all([imageReady(baseSrc),imageReady(overlaySrc)]);if(!ready[0]||!ready[1]||request!==state.request)return false;frame.src=cached(baseSrc);gaze.style.transform=`translate(${offset[0]}px,${offset[1]}px)`;gaze.src=cached(overlaySrc);frame.hidden=false;gaze.hidden=false;staging.hidden=true;state.activeBaseSrc=baseSrc;record(state,'composite_presented',{src:baseSrc,overlay:overlaySrc,mode});return true}
async function showGaze(overlay,mode){const request=++state.gazeRequest;if(!overlay){record(state,'gaze_fail_closed',{mode});return false}if(!await imageReady(overlay)||request!==state.gazeRequest){record(state,'gaze_fail_closed',{mode});return false}const offset=touchData.story_offsets[state.storyName]||[0,0];gaze.style.transform=`translate(${offset[0]}px,${offset[1]}px)`;gaze.src=cached(overlay);gaze.hidden=false;await paint();if(request===state.gazeRequest)record(state,'gaze_presented',{mode,overlay});return request===state.gazeRequest}
function playFrame(extra){if(state.touching)return;const item=story().frames[state.frameIndex%story().frames.length];const index=state.frameIndex%story().frames.length;const request=++state.request;presentComposite(item.touch_base||item.src,touchData.overlays[touchData.center_key],request,'idle').then(ok=>{if(!ok||state.touching||request!==state.request)return;state.activeFrame=item;state.activeFrameIndex=index;state.frameIndex=(index+1)%story().frames.length;state.framePresentCount++;state.activeFrameStartedAt=performance.now();state.activeFrameDurationMs=item.duration_ms;state.pausedRemainingMs=item.duration_ms;chrome(item,extra);record(state,'frame_presented',{phase:item.phase});clearTimeout(state.timer);state.timer=setTimeout(()=>playFrame(),item.duration_ms)})}
function follow(event){if(!state.activeFrame||!state.activeBaseSrc)return;const key=gazeKey(point(stage,event));showGaze(touchData.overlays[key],'touch')}
function choose(name,extra){if(!storyByName.has(name))return;clearTimeout(state.timer);state.storyName=name;state.frameIndex=0;state.activeFrame=null;state.activeFrameIndex=-1;state.activeBaseSrc='';state.request++;record(state,'story_select',{story:name});playFrame(extra||`选择 / ${story().label}`)}
function begin(event){if(event.button!==undefined&&event.button!==0||state.touching||!state.activeFrame||frame.hidden)return;event.preventDefault();state.touching=true;clearTimeout(state.timer);state.pausedRemainingMs=Math.max(0,Math.round(state.activeFrameDurationMs-(performance.now()-state.activeFrameStartedAt)));state.start=point(stage,event);state.gestureStart=state.start;state.gestureStartedAt=performance.now();state.gestureAxis=null;state.gestureSamples=1;record(state,'touch_begin',{remaining_ms:state.pausedRemainingMs});if(event.pointerId!==undefined){try{stage.setPointerCapture(event.pointerId)}catch{}}follow(event)}function move(event){if(state.touching){event.preventDefault();const current=point(stage,event);state.gestureSamples=Math.min(2,state.gestureSamples+1);updateGestureAxis(state,current);state.start=state.gestureStart;follow(event)}}function end(event){state.mouseDown=false;if(!state.touching)return;const endPoint=event&&event.clientX!==undefined?point(stage,event):(state.gestureStart||{x:100,y:100});const classified=classifyGesture(state,endPoint);state.touching=false;state.start=null;const item=state.activeFrame;showGaze(touchData.overlays[touchData.center_key],'release');record(state,'gesture_classified',Object.assign({samples:Math.max(2,state.gestureSamples)},classified));record(state,'touch_release',{story:state.storyName,frame:state.activeFrameIndex});if(scope==='overall'&&classified.event)runAuthorityEvent(classified.event,classified.attention,classified.gesture);clearTimeout(state.timer);state.timer=setTimeout(()=>{if(!state.touching)playFrame()},Math.max(180,state.pausedRemainingMs))}
stage.addEventListener('pointerdown',event=>{if(event.pointerType!=='mouse')begin(event)});stage.addEventListener('pointermove',event=>{if(event.pointerType!=='mouse')move(event)});stage.addEventListener('pointerup',event=>{if(event.pointerType!=='mouse')end(event)});stage.addEventListener('pointercancel',event=>{if(event.pointerType!=='mouse')end(event)});stage.addEventListener('mousedown',event=>{state.mouseDown=true;begin(event)});stage.addEventListener('mousemove',event=>{if(state.mouseDown)move(event)});stage.addEventListener('mouseup',end);window.addEventListener('mouseup',event=>{if(state.mouseDown)end(event)});record(state,'page_ready');playFrame();return{state,choose,playFrame}}
let currentAffect={valence:0,arousal:1,affinity:0,interaction_memory:0,energy:'normal'};function runAuthorityEvent(event,attention,gesture){const authorityEvent=event==='TOUCH_TAP'?'touch_tap':event==='TOUCH_SWIPE'?'touch_swipe':event;const decision=decide(Object.assign({},currentAffect,{event:authorityEvent,attention,gesture_code:event}));currentAffect=Object.assign({},decision.affect_after,{interaction_memory:currentAffect.interaction_memory,energy:currentAffect.energy});document.querySelector('#emotion-current').textContent=`当前情绪：${decision.emotion} · ${decision.visual_story}`;document.querySelector('#emotion-rule').textContent=`命中：${decision.matched_branch} · 输出：${decision.emotion}`;document.querySelector('#gesture-status').textContent=`${gesture==='tap'?'点击/轻触':'拖动/滑动'} · 注视：${attention}`;window.__lastEmotionDecision=decision;window.__companionAffectState=currentAffect;overallController.choose(decision.visual_story,`权威输出 / ${decision.emotion}`)}
const overallController=mountViewport(document.querySelector('#overall-viewport'),'calm_presence',document.querySelector('#overall-label'),document.querySelector('#overall-status'),'overall');for(const item of stories)mountViewport(document.querySelector(`[data-viewport-story="${CSS.escape(item.name)}"]`),item.name,null,null,item.name);window.__companionViewportStates=viewportStates;window.__companionAuthorityDecide=decide;window.__companionAuthorityDebug={authority,decide,gestureAuthority};window.__companionAuthorityDomains=authority.domains;window.__companionGestureAuthority=gestureAuthority;window.__v45TouchState=()=>{const s=viewportStates.overall;return{revision:sourceRevision,story_name:s.storyName,story_index:stories.findIndex(item=>item.name===s.storyName),active_frame_index:s.activeFrameIndex,active_frame_cue:s.activeFrame?s.activeFrame.cue:null,active_base_src:s.activeBaseSrc,touching:s.touching,trace_length:s.trace.length,frame_present_count:s.framePresentCount,active_frame_elapsed_ms:s.activeFrameStartedAt?Math.round(performance.now()-s.activeFrameStartedAt):0,gesture_axis:s.gestureAxis}};window.__v45TouchTrace=viewportStates.overall.trace;runAuthorityEvent('daily_auto','center','idle');
</script></html>"""
    html = (template.replace("__TITLE__", escape(title))
            .replace("__AUTHORITY_SOURCE__", escape(f'{authority["source"]["c"]} + {authority["source"]["h"]}'))
            .replace("__STORY_ROWS__", "".join(story_rows))
            .replace("__STORIES__", json.dumps(story_data, ensure_ascii=False))
            .replace("__TOUCH__", json.dumps(touch_gaze_package, ensure_ascii=False))
            .replace("__AUTHORITY__", json.dumps(authority, ensure_ascii=False)))
    html = html.replace("join('\n')", "join('\\\\n')")
    html = html.replace("const top=mountViewport", "const overallController=mountViewport")
    html = html.replace(";top.choose(", ";overallController.choose(")
    output.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--trace", type=Path, default=TRACE)
    parser.add_argument("--v22-layout", type=Path, default=V22_LAYOUT)
    parser.add_argument("--special-layout", type=Path, default=SPECIAL_LAYOUT)
    parser.add_argument("--candidate-label", default="v34_v35_special_decoration")
    args = parser.parse_args()
    trace = load_json(args.trace.resolve())
    special_pack = "v45_special_source" if str(trace.get("schema", "")).startswith("companion.v45_") else "v34_v35_decoration"
    accepted_bindings = {"forbidden_until_wb55_component_plan_parity_and_owner_review",
                         "forbidden_until_total_machine_audit_and_owner_review",
                         "forbidden_until_v39_machine_audit_and_owner_review",
                         "forbidden_until_v40_machine_audit_and_owner_review",
                         "forbidden_until_v41_machine_audit_and_owner_review",
                         "forbidden_until_v42_machine_audit_and_owner_review",
                         "forbidden_until_v43_machine_audit_and_owner_review",
                         "forbidden_until_v44_machine_audit_and_owner_review",
                         "forbidden_until_v45_machine_audit_and_owner_review"}
    require(trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            trace.get("runtime_resource_activated") is False and
            trace.get("active_candidate_binding") in accepted_bindings,
            "WB55 target-score trace is not an inactive candidate")
    components = component_map(args.v22_layout.resolve(), args.special_layout.resolve())
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    preview_zh = trace.get("preview_zh")
    metadata = preview_zh.get("stories", {}) if isinstance(preview_zh, dict) else {}
    records: list[dict[str, Any]] = []
    raw_images: dict[int, Image.Image] = {}
    for score in trace.get("scores", []):
        require(isinstance(score, dict) and isinstance(score.get("name"), str) and
                isinstance(score.get("steps"), list) and score["steps"],
                "score trace shape drifted")
        for index, step in enumerate(score["steps"]):
            require(isinstance(step, dict) and isinstance(step.get("cue"), str) and
                    isinstance(step.get("duration_ms"), int) and isinstance(step.get("layers"), list),
                    "score step trace drifted")
            image, target = render_frame(components, step["layers"])
            stem = f'{score["name"]}-{index:02d}-{step["cue"]}'
            pbm = output / f"{stem}.pbm"
            png = output / f"{stem}.png"
            record = {
                "score": score["name"], "prelude_bridge": score.get("prelude_bridge", "independent_two_track_composition"), "index": index,
                "cue": step["cue"], "phase": step.get("phase", "hold"), "duration_ms": step["duration_ms"],
                "layers": describe_layers(components, step["layers"], special_pack), "pbm": pbm.name, "png": png.name,
                "source_1bpp_sha256": hashlib.sha256(target).hexdigest().upper(),
            }
            for key in ("state_scene", "emotion", "attention", "expression_track", "expression_step", "functional_decoration_track", "functional_step"):
                if key in step:
                    record[key] = step[key]
            records.append(record)
            raw_images[id(record)] = image
    require(records, "special candidate has no browser plan frames")

    story_names = list(dict.fromkeys(record["score"] for record in records))
    story_offsets: dict[str, list[int]] = {}
    derived_images: dict[int, Image.Image] = {}
    for name in story_names:
        story_records = [record for record in records if record["score"] == name]
        overview_step = metadata.get(name, {}).get("overview_step", len(story_records) - 1) if isinstance(metadata, dict) else len(story_records) - 1
        if not isinstance(overview_step, int) or not 0 <= overview_step < len(story_records):
            overview_step = len(story_records) - 1
        reference = story_records[overview_step]
        reference_image = raw_images[id(reference)]
        anchor = source_anchor(reference_image)
        offset = (CANONICAL_CENTER[0] - anchor[0], CANONICAL_CENTER[1] - anchor[1])
        story_offsets[name] = [offset[0], offset[1]]
        for record in story_records:
            source_image = raw_images[id(record)]
            source_bounds = ink_bounds(source_image)
            require(source_bounds[0] + offset[0] >= 0 and source_bounds[1] + offset[1] >= 0 and
                    source_bounds[2] + offset[0] < 200 and source_bounds[3] + offset[1] < 200,
                    f"{name}/{record['cue']} would clip after canonical centering")
            derived = translate(source_image, offset)
            derived_bounds = ink_bounds(derived)
            derived_target = derived.tobytes()
            write_p4(output / record["pbm"], derived_target)
            derived.save(output / record["png"])
            record.update({
                "anchor_policy": ANCHOR_POLICY,
                "canonical_center": list(CANONICAL_CENTER),
                "source_anchor": list(anchor),
                "normalization_offset": list(offset),
                "source_bounds": list(source_bounds),
                "output_bounds": list(output_bounds(derived)),
                "derived_1bpp_sha256": hashlib.sha256(derived_target).hexdigest().upper(),
                "story_uniform_offset": True,
            })
            derived_images[id(record)] = derived

    story_gifs: dict[str, str] = {}
    for score_name in story_names:
        frames = [derived_images[id(record)].convert("L") for record in records if record["score"] == score_name]
        durations = [record["duration_ms"] for record in records if record["score"] == score_name]
        gif = output / f"{score_name}-component-rig.gif"
        arguments: dict[str, Any] = {"save_all": True, "append_images": frames[1:], "duration": durations}
        if score_name != "menu_entry_notice":
            arguments["loop"] = 0
        frames[0].save(gif, **arguments)
        story_gifs[score_name] = rel(gif)

    html = output / "index.html"
    single_epaper_viewport = trace.get("schema") in {
        "companion.v44_expression_extension_wb55_target_profile_plan.v1",
        "companion.v45_complete_eye_expression_extension_wb55_target_profile_plan.v1",
    }
    all_performance_wall = trace.get("schema") in {
        "companion.v42_expression_extension_wb55_target_profile_plan.v1",
        "companion.v43_expression_extension_wb55_target_profile_plan.v1",
    }
    metadata = preview_zh.get("stories", {}) if isinstance(preview_zh, dict) else {}
    owner_visible_scores = [name for name in dict.fromkeys(record["score"] for record in records)
                            if not isinstance(metadata.get(name, {}), dict) or metadata.get(name, {}).get("owner_visible", True) is not False]
    touch_bases: dict[str, dict[str, str]] = {}
    if all_performance_wall or single_epaper_viewport:
        for score_name in owner_visible_scores:
            touch_bases[score_name] = {}
            for record in records:
                if record["score"] != score_name:
                    continue
                base_image = derived_images[id(record)]
                base_path = output / f"touch-base-{score_name}-{record['index']:02d}.png"
                base_image.save(base_path)
                touch_bases[score_name][str(record["index"])] = base_path.name
                record["touch_base"] = base_path.name
    touch_overlays: dict[str, str] = {}
    touch_offset_by_key: dict[str, dict[str, int]] = {}
    for x in range(200):
        for y in range(200):
            offsets = touch_offsets(x, y)
            key = touch_key(offsets)
            if key in touch_overlays:
                continue
            overlay_path = output / f"touch-gaze-overlay-{len(touch_overlays):03d}.png"
            render_touch_overlay(components, offsets).save(overlay_path)
            touch_overlays[key] = overlay_path.name
            touch_offset_by_key[key] = offsets
    touch_gaze_package = {
        "canvas": "200x200",
        "mode": ("single_200x200_viewport_pointer_coordinate_to_registered_offsets"
                  if single_epaper_viewport else "in_card_pointer_coordinate_to_registered_offsets"),
        "mapping": "each pointer x/y independently maps to source-derived white V9 primary-highlight and sparkle cutouts clipped inside the corresponding black eye bodies",
        "overlay_contract": {"rgba": "white_opaque_or_transparent", "source_components": [1, 3, 5, 7],
                             "eye_body_components": [2, 6], "clip": "primary/sparkle pixels intersect corresponding eye-body mask only",
                             "atomic_presentation": True},
        "overlays": touch_overlays,
        "offsets": touch_offset_by_key,
        "bases": touch_bases,
        "story_offsets": {name: story_offsets[name] for name in owner_visible_scores},
        "center_key": touch_key(touch_offsets(100, 100)),
        "release_behavior": "center_then_resume_story",
        "gestures": (["tap", "drag", "release_to_center", "gallery_story_select"]
                     if single_epaper_viewport else ["tap", "drag", "release_to_center"]),
    }
    authority = emotion_authority() if single_epaper_viewport else None
    if single_epaper_viewport:
        render_authority_wall_html(html, records, preview_zh if isinstance(preview_zh, dict) else None, touch_gaze_package, authority)
    else:
        render_html(html, records, preview_zh if isinstance(preview_zh, dict) else None, touch_gaze_package, all_performance_wall)
    score_names = [record["score"] for record in records]
    source_scores = list(dict.fromkeys(score_names))
    report = {
        "schema": f"companion.{args.candidate_label}_browser_wb55_preview.v1",
        "status": "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-250", "COMP-REQ-253", "COMP-REQ-254", "COMP-REQ-256", "COMP-REQ-258", "COMP-REQ-261", "COMP-REQ-262", "COMP-REQ-263"],
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "canvas": {"width": 200, "height": 200, "stride_bytes": 25, "pixel_format": "1bpp_white_is_one_msb"},
        "renderer": "registered source masks only; ordered ink/erase composition; no full-face source frame",
        "presentation": "single_200x200_authority_viewport_with_16_independent_live_story_viewports" if single_epaper_viewport else ("simultaneous_dynamic_wall" if all_performance_wall else "single_story_player"),
        "viewport_contract": {"canvas": "200x200", "owner_visible_story_count": len(owner_visible_scores),
                              "gallery": {"orientation": "vertical", "owner_visible_story_count": len(owner_visible_scores), "mode": "independent_live_choreography_viewports"},
                              "authority_decision_screen": True,
                              "decision_controls": ["event", "energy", "valence", "arousal", "affinity", "interaction_memory"],
                              "touch_surface": "the_200x200_viewport_itself", "idle_gaze": "registered_center_unless_pointer_pressed", "release": "center_then_resume", "runtime_resource_activated": False} if single_epaper_viewport else None,
        "source_score_coverage": source_scores,
        "frame_count": len(records), "frames": records,
        "dynamic_preview": {"html": rel(html), "story_gifs": story_gifs,
                            "all_performance_wall": {"enabled": all_performance_wall, "owner_visible_story_count": len(owner_visible_scores),
                                                      "simultaneous_autoplay": all_performance_wall},
                            "touch_follow_gaze": {"enabled": True, "canvas": "200x200",
                                                   "surface": ("the_200x200_viewport_itself" if single_epaper_viewport else "owner_visible_performance_card_face_box"),
                                                   "mode": touch_gaze_package["mode"], "mapping": touch_gaze_package["mapping"],
                                                   "overlay_count": len(touch_overlays), "base_story_count": len(touch_bases),
                                                   "center_key": touch_gaze_package["center_key"],
                                                   "release_behavior": touch_gaze_package["release_behavior"],
                                                   "gestures": touch_gaze_package["gestures"]}},
        "emotion_authority": authority,
        "chinese_overview": {"enabled": isinstance(preview_zh, dict), "story_count": len(source_scores), "owner_visible_story_count": len(owner_visible_scores),
                               "owner_visible_scores": owner_visible_scores,
                               "metadata": preview_zh if isinstance(preview_zh, dict) else None},
        "runtime_resource_activated": False,
        "active_candidate_binding": trace["active_candidate_binding"],
        "fail_closed": {"all_special_runtime_binding": "forbidden_until_total_machine_audit_and_owner_review"},
        "non_claims": ["no_target_pixel_parity_yet", "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"],
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: rendered {len(records)} component-only 200x200 browser frames for later WB55 parity replay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
