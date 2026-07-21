#!/usr/bin/env python3
"""Render V34/V35 browser frames from the exact inactive WB55 score contract."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
SPECIAL_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-wb55-target-profile-plan.json"
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


def render_touch_base(components: dict[int, dict[str, Any]], layers: list[dict[str, Any]]) -> tuple[Image.Image, bytes]:
    return render_frame(components, [layer for layer in layers if layer.get("component_id") not in {1, 3, 5, 7}])


def render_touch_overlay(components: dict[int, dict[str, Any]], offsets: dict[str, int]) -> Image.Image:
    overlay = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
    pixels = overlay.load()
    for component_id, key in ((1, "primary"), (5, "primary"), (3, "sparkle"), (7, "sparkle")):
        component = components.get(component_id)
        require(component is not None, f"missing registered gaze component {component_id}")
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
        mask_pixels = mask.load()
        for y in range(mask.height):
            for x in range(mask.width):
                if mask_pixels[x, y] == 0:
                    pixels[origin_x + x, origin_y + y] = (255, 255, 255, 255)
    return overlay


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
    records: list[dict[str, Any]] = []
    story_gif_frames: dict[str, list[Image.Image]] = {}
    story_gif_durations: dict[str, list[int]] = {}
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
            write_p4(pbm, target)
            image.save(png)
            record = {
                "score": score["name"], "prelude_bridge": score.get("prelude_bridge", "independent_two_track_composition"), "index": index,
                "cue": step["cue"], "phase": step.get("phase", "hold"), "duration_ms": step["duration_ms"],
                "layers": describe_layers(components, step["layers"], special_pack), "pbm": pbm.name, "png": png.name,
                "target_1bpp_sha256": hashlib.sha256(target).hexdigest().upper(),
            }
            for key in ("state_scene", "emotion", "attention", "expression_track", "expression_step", "functional_decoration_track", "functional_step"):
                if key in step:
                    record[key] = step[key]
            records.append(record)
            story_gif_frames.setdefault(score["name"], []).append(image.convert("L"))
            story_gif_durations.setdefault(score["name"], []).append(step["duration_ms"])
    require(records, "special candidate has no browser plan frames")
    story_gifs: dict[str, str] = {}
    for score_name, frames in story_gif_frames.items():
        gif = output / f"{score_name}-component-rig.gif"
        arguments: dict[str, Any] = {"save_all": True, "append_images": frames[1:], "duration": story_gif_durations[score_name]}
        if score_name != "menu_entry_notice":
            arguments["loop"] = 0
        frames[0].save(gif, **arguments)
        story_gifs[score_name] = rel(gif)
    html = output / "index.html"
    preview_zh = trace.get("preview_zh")
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
                base_image, _ = render_touch_base(components, record["layers"])
                base_path = output / f"touch-base-{score_name}-{record['index']:02d}.png"
                base_image.save(base_path)
                touch_bases[score_name][str(record["index"])] = base_path.name
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
        "mapping": "each pointer x/y independently maps to the legal V9 primary-highlight and sparkle offset ranges; no dominant-axis endpoint selection",
        "overlays": touch_overlays,
        "offsets": touch_offset_by_key,
        "bases": touch_bases,
        "center_key": touch_key(touch_offsets(100, 100)),
        "release_behavior": "center_then_resume_story",
        "gestures": (["tap", "drag", "release_to_center", "swipe_left", "swipe_right", "swipe_up", "swipe_down"]
                     if single_epaper_viewport else ["tap", "drag", "release_to_center"]),
    }
    if single_epaper_viewport:
        render_single_epaper_html(html, records, preview_zh if isinstance(preview_zh, dict) else None, touch_gaze_package)
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
        "presentation": "single_200x200_epaper_viewport_with_in_screen_touch_and_deterministic_swipe" if single_epaper_viewport else ("simultaneous_dynamic_wall" if all_performance_wall else "single_story_player"),
        "viewport_contract": {"canvas": "200x200", "owner_visible_story_count": len(owner_visible_scores),
                              "swipe_navigation": {"horizontal": True, "vertical": True, "positive_direction": "next_story", "negative_direction": "previous_story", "threshold_px": 24},
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
