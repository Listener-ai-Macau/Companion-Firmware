#!/usr/bin/env python3
"""Render source-component-only V21 everyday emotion bridges for browser and 200x200 target parity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
V21_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source"
SOURCE_OUTPUT = V21_ROOT / "candidate/component-export-attempt-01"
SOURCE_LAYOUT = SOURCE_OUTPUT / "everyday-emotion-component-layout.json"
COMPONENT_GATE = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-component-export-gate-20260719.json"
V1_RIG_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
OUTPUT = V21_ROOT / "candidate/component-bridge-v2"
EMOTIONS = ("calm", "curious", "warm", "playful", "puzzled", "alert")
IDENTITY_NAMES = (
    "left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open",
    "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default",
)
PRIMARY_HIGHLIGHT_NAMES = {"left_eye_highlight_open", "right_eye_highlight_open"}
SPARKLE_NAMES = {"left_eye_sparkle_open", "right_eye_sparkle_open"}
HIGHLIGHT_NAMES = PRIMARY_HIGHLIGHT_NAMES | SPARKLE_NAMES
BRIDGE_EDGES = (
    ("calm", "curious", "attention_novelty", (-1, -2)),
    ("curious", "calm", "novelty_resolved", (1, 1)),
    ("curious", "warm", "positive_reciprocity", (2, 0)),
    ("warm", "curious", "attention_shift", (-2, 0)),
    ("warm", "playful", "shared_play", (1, -1)),
    ("playful", "warm", "energy_settle", (-1, 1)),
    ("calm", "puzzled", "ambiguous_input", (-2, 1)),
    ("puzzled", "calm", "ambiguity_resolved", (2, -1)),
    ("puzzled", "alert", "high_salience", (2, -1)),
    ("alert", "puzzled", "salience_reduced", (-2, 1)),
)
AFFECT_NODES = {
    "calm": {"valence": 0, "arousal": 1, "interaction_memory": "neutral_safe"},
    "curious": {"valence": 0, "arousal": 2, "interaction_memory": "novel_attention"},
    "warm": {"valence": 1, "arousal": 1, "interaction_memory": "positive_reciprocity"},
    "playful": {"valence": 2, "arousal": 3, "interaction_memory": "shared_play"},
    "puzzled": {"valence": -1, "arousal": 2, "interaction_memory": "ambiguity"},
    "alert": {"valence": -1, "arousal": 3, "interaction_memory": "high_salience"},
}
CANVAS = (200, 200)


@dataclass(frozen=True)
class Component:
    name: str
    role: str
    emotion: str | None
    source: str
    mask_path: Path
    mask_sha256: str
    position: tuple[int, int]
    z_index: int
    composite_op: str
    offset_min: tuple[int, int]
    offset_max: tuple[int, int]
    mask: Image.Image


@dataclass(frozen=True)
class Layer:
    component: Component
    offset: tuple[int, int]

    @property
    def position(self) -> tuple[int, int]:
        return self.component.position[0] + self.offset[0], self.component.position[1] + self.offset[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="ascii")


def load_component(record: dict[str, Any], emotion: str | None,
                   offset_override: tuple[tuple[int, int], tuple[int, int]] | None = None) -> Component:
    mask_path = ROOT / str(record["mask"])
    require(mask_path.is_file(), f"component mask is missing: {mask_path}")
    require(sha256(mask_path) == record["mask_sha256"], f"component mask hash drifted: {record['name']}")
    with Image.open(mask_path) as source:
        mask = source.convert("L")
    position = record["base_position"]
    offset_range = record.get("offset_range", {"min": [0, 0], "max": [0, 0]})
    offset_min, offset_max = offset_override if offset_override is not None else (
        (int(offset_range["min"][0]), int(offset_range["min"][1])),
        (int(offset_range["max"][0]), int(offset_range["max"][1])),
    )
    return Component(
        name=str(record["name"]),
        role=str(record["role"]),
        emotion=emotion,
        source=str(record["source"]),
        mask_path=mask_path,
        mask_sha256=str(record["mask_sha256"]),
        position=(int(position[0]), int(position[1])),
        z_index=int(record["z_index"]),
        composite_op=str(record["composite_op"]),
        offset_min=offset_min,
        offset_max=offset_max,
        mask=mask,
    )


def validate_offset(component: Component, offset: tuple[int, int]) -> None:
    require(component.offset_min[0] <= offset[0] <= component.offset_max[0] and
            component.offset_min[1] <= offset[1] <= component.offset_max[1],
            f"{component.name} offset {offset} is outside its registered legal range")


def rgba_layer(component: Component) -> Image.Image:
    alpha = ImageOps.invert(component.mask)
    color = (0, 0, 0, 255) if component.composite_op == "ink" else (255, 255, 255, 255)
    layer = Image.new("RGBA", component.mask.size, (0, 0, 0, 0))
    layer.paste(color, (0, 0), alpha)
    return layer


def compose(layers: Iterable[Layer]) -> Image.Image:
    canvas = Image.new("L", CANVAS, 255)
    for layer in sorted(layers, key=lambda item: (item.component.z_index, item.component.name)):
        validate_offset(layer.component, layer.offset)
        alpha = ImageOps.invert(layer.component.mask)
        color = 0 if layer.component.composite_op == "ink" else 255
        canvas.paste(color, layer.position, alpha)
    return canvas.convert("1")


def write_mask(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PPM")


def image_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.convert("1").getdata(), right.convert("1").getdata()))


def component_public(component: Component, png_path: Path) -> dict[str, Any]:
    return {
        "name": component.name,
        "role": component.role,
        "emotion": component.emotion,
        "source": component.source,
        "mask": rel(component.mask_path),
        "mask_sha256": component.mask_sha256,
        "browser_layer": png_path.name,
        "browser_layer_sha256": sha256(png_path),
        "base_position": list(component.position),
        "z_index": component.z_index,
        "composite_op": component.composite_op,
        "offset_range": {"min": list(component.offset_min), "max": list(component.offset_max)},
        "size": list(component.mask.size),
    }


def layer_public(layer: Layer) -> dict[str, Any]:
    return {
        "component": layer.component.name,
        "role": layer.component.role,
        "emotion": layer.component.emotion,
        "source": layer.component.source,
        "base_position": list(layer.component.position),
        "offset": list(layer.offset),
        "position": list(layer.position),
        "z_index": layer.component.z_index,
        "composite_op": layer.component.composite_op,
    }


def state_by_role(components: dict[str, Component], emotion: str) -> dict[str, Component]:
    result = {component.role: component for component in components.values() if component.emotion == emotion}
    require(set(result) == {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"} |
            ({"accent"} if emotion == "playful" else set()),
            f"{emotion} special component roles are incomplete")
    return result


def locked_v9_offset_ranges() -> dict[str, tuple[tuple[int, int], tuple[int, int]]]:
    layout = load_json(V1_RIG_LAYOUT)
    components = layout.get("components")
    require(isinstance(components, list), "locked V9 Rig layout has no component registry")
    ranges: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}
    for record in components:
        if not isinstance(record, dict):
            continue
        name = str(record.get("name", ""))
        offset_range = record.get("offset_range")
        if not name or not isinstance(offset_range, dict):
            continue
        low, high = offset_range.get("min"), offset_range.get("max")
        if isinstance(low, list) and isinstance(high, list) and len(low) == 2 and len(high) == 2:
            ranges[name] = ((int(low[0]), int(low[1])), (int(high[0]), int(high[1])))
    require(set(IDENTITY_NAMES) <= set(ranges), "locked V9 identity legal offset ranges are incomplete")
    return ranges


def build_layers(identity: dict[str, Component], special: dict[str, Component], source: str, target: str,
                 group_state: dict[str, str], primary_highlight_offset: tuple[int, int],
                 sparkle_offset: tuple[int, int],
                 local_offsets: dict[str, tuple[int, int]]) -> list[Layer]:
    layers: list[Layer] = []
    for name in IDENTITY_NAMES:
        component = identity[name]
        if name in PRIMARY_HIGHLIGHT_NAMES:
            offset = primary_highlight_offset
        elif name in SPARKLE_NAMES:
            offset = sparkle_offset
        else:
            offset = (0, 0)
        layers.append(Layer(component, offset))
    source_roles = state_by_role(special, source)
    target_roles = state_by_role(special, target)
    for role in ("left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"):
        selected = source_roles[role] if group_state[role] == "source" else target_roles[role]
        layers.append(Layer(selected, local_offsets.get(role, (0, 0))))
    source_accent = source_roles.get("accent")
    target_accent = target_roles.get("accent")
    accent_state = group_state.get("accent", "none")
    if accent_state == "source":
        require(source_accent is not None, "bridge selected a missing source accent")
        layers.append(Layer(source_accent, local_offsets.get("accent", (0, 0))))
    elif accent_state == "target":
        require(target_accent is not None, "bridge selected a missing target accent")
        layers.append(Layer(target_accent, local_offsets.get("accent", (0, 0))))
    else:
        require(accent_state == "none", f"unknown accent state: {accent_state}")
    return layers


def frame_spec(cue: str, phase: str, duration_ms: int, changed_groups: tuple[str, ...],
               layers: list[Layer]) -> dict[str, Any]:
    return {
        "cue": cue,
        "phase": phase,
        "duration_ms": duration_ms,
        "changed_groups": list(changed_groups),
        "layers": [layer_public(layer) for layer in sorted(layers, key=lambda item: (item.component.z_index, item.component.name))],
    }


def bridge_frames(identity: dict[str, Component], special: dict[str, Component], source: str, target: str,
                  gaze: tuple[int, int]) -> list[dict[str, Any]]:
    source_state = {role: "source" for role in ("left_brow", "right_brow", "left_cheek", "right_cheek", "mouth")}
    source_state["accent"] = "source" if source == "playful" else "none"
    source_layers = build_layers(identity, special, source, target, source_state, (0, 0), (0, 0), {})
    frames = [frame_spec("source_hold", "entry", 680, (), source_layers)]
    frames.append(frame_spec("primary_highlight_lead", "onset", 160, ("primary_highlights",),
        build_layers(identity, special, source, target, source_state, gaze, (0, 0), {})))
    frames.append(frame_spec("sparkle_arrive", "onset", 160, ("sparkles",),
        build_layers(identity, special, source, target, source_state, gaze, gaze, {})))
    brow_state = dict(source_state)
    brow_state["left_brow"] = "target"
    brow_state["right_brow"] = "target"
    frames.append(frame_spec("brow_apex", "apex", 280, ("brows",),
        build_layers(identity, special, source, target, brow_state, gaze, gaze,
                     {"left_brow": (0, -1), "right_brow": (0, -1)})))
    lower_state = dict(brow_state)
    lower_state.update({"left_cheek": "target", "right_cheek": "target", "mouth": "target"})
    frames.append(frame_spec("lower_face_apex", "apex", 320, ("lower_face",),
        build_layers(identity, special, source, target, lower_state, gaze, gaze,
                     {"left_cheek": (0, -1), "right_cheek": (0, -1), "mouth": (0, 1)})))
    accent_involved = source == "playful" or target == "playful"
    target_state = {role: "target" for role in ("left_brow", "right_brow", "left_cheek", "right_cheek", "mouth")}
    target_state["accent"] = "target" if target == "playful" else "none"
    if accent_involved:
        accent_offsets = {"left_cheek": (0, -1), "right_cheek": (0, -1), "mouth": (0, 1)}
        if target == "playful":
            accent_offsets["accent"] = (0, -1)
        frames.append(frame_spec("accent_resolve", "apex", 240, ("accent",),
            build_layers(identity, special, source, target, target_state, gaze, gaze, accent_offsets)))
    frames.append(frame_spec("target_hold", "hold", 1800, ("target_pose",),
        build_layers(identity, special, source, target, target_state, gaze, gaze, {})))
    frames.append(frame_spec("highlight_settle", "offset", 360, ("highlights",),
        build_layers(identity, special, source, target, target_state, (0, 0), (0, 0), {})))
    return frames


def write_contact_sheet(path: Path, frames: list[Image.Image]) -> None:
    sheet = Image.new("L", (len(frames) * CANVAS[0], CANVAS[1]), 255)
    for index, frame in enumerate(frames):
        sheet.paste(frame.convert("L"), (index * CANVAS[0], 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.resize((sheet.width * 3, sheet.height * 3), Image.Resampling.NEAREST).save(path)


def write_gif(path: Path, images: list[Image.Image], durations: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    images[0].convert("P").save(path, save_all=True, append_images=[image.convert("P") for image in images[1:]],
                              duration=durations, loop=0, disposal=2)


def browser_bridge_payload(bridges: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
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


def build_preview_html(path: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, separators=(",", ":"))
    page = f"""<!doctype html>
<html lang=\"en\">
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>V21 Component Emotion Bridges</title>
<style>
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; background:#eef0eb; color:#15181a; font-family:Arial,sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:24px; }}
header {{ display:flex; align-items:center; justify-content:space-between; gap:16px; border-bottom:1px solid #23272a; padding-bottom:14px; }}
h1 {{ margin:0; font-size:22px; font-weight:700; letter-spacing:0; }}
.controls {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
select,button {{ min-height:36px; border:1px solid #23272a; border-radius:3px; background:#fff; color:#15181a; font:inherit; }}
select {{ padding:0 9px; }}
button {{ width:36px; padding:0; cursor:pointer; font-size:17px; }}
button:hover {{ background:#dfe8e1; }}
.stage-row {{ display:grid; grid-template-columns:minmax(0,1fr) 250px; gap:24px; padding-top:24px; align-items:start; }}
.stage-wrap {{ display:flex; justify-content:center; background:#fff; border:1px solid #23272a; padding:24px; }}
#stage {{ position:relative; width:800px; height:800px; max-width:100%; aspect-ratio:1; background:#fff; overflow:hidden; }}
#stage img {{ position:absolute; image-rendering:pixelated; image-rendering:crisp-edges; }}
.route {{ border-left:1px solid #23272a; padding-left:18px; }}
.route-name {{ margin:0 0 18px; font-size:18px; font-weight:700; }}
.phase {{ margin:0; padding:8px 0; border-top:1px solid #c8cdca; font-size:14px; }}
.phase:last-child {{ border-bottom:1px solid #c8cdca; }}
.active {{ font-weight:700; color:#1e5d45; }}
@media (max-width:760px) {{ main {{ padding:14px; }} header {{ align-items:flex-start; flex-direction:column; }} .stage-row {{ grid-template-columns:1fr; gap:16px; }} #stage {{ width:min(100%,800px); height:auto; }} .stage-wrap {{ padding:10px; }} .route {{ border-left:0; border-top:1px solid #23272a; padding:14px 0 0; }} }}
</style>
<main>
  <header>
    <h1>V21 Emotion Bridge</h1>
    <div class=\"controls\">
      <select id=\"source\" aria-label=\"Source emotion\"></select>
      <select id=\"target\" aria-label=\"Target emotion\"></select>
      <button id=\"play\" title=\"Pause\" aria-label=\"Pause\">&#10074;&#10074;</button>
      <button id=\"restart\" title=\"Restart selected bridge\" aria-label=\"Restart selected bridge\">&#8634;</button>
    </div>
  </header>
  <section class=\"stage-row\">
    <div class=\"stage-wrap\"><div id=\"stage\" aria-label=\"Component-composed emotion transition\"></div></div>
    <aside class=\"route\"><p class=\"route-name\" id=\"route\"></p><div id=\"phases\"></div></aside>
  </section>
</main>
<script>
const data={serialized};
const scale=4, stage=document.querySelector('#stage'), source=document.querySelector('#source'), target=document.querySelector('#target');
const play=document.querySelector('#play'), restart=document.querySelector('#restart'), route=document.querySelector('#route'), phases=document.querySelector('#phases');
let timer=0, running=true, frameIndex=0, activeKey='';
const titleCase=value=>value[0].toUpperCase()+value.slice(1);
function readQuery() {{ const q=new URLSearchParams(location.search); return {{source:q.get('state'),target:q.get('target')}}; }}
function legalTargets(value) {{ return Object.values(data.bridges).filter(b=>b.source===value).map(b=>b.target); }}
function setOptions(select, values, wanted) {{ select.innerHTML=''; values.forEach(value=>{{const option=document.createElement('option');option.value=value;option.textContent=titleCase(value);select.append(option);}});select.value=values.includes(wanted)?wanted:values[0]; }}
function selectedBridge() {{ return data.bridges[`${{source.value}}__${{target.value}}`]; }}
function refreshTargets(wanted) {{ setOptions(target,legalTargets(source.value),wanted); }}
function phaseList(bridge, frame) {{ route.textContent=`${{titleCase(bridge.source)}} to ${{titleCase(bridge.target)}}`; phases.innerHTML=''; bridge.frames.forEach((item,index)=>{{const row=document.createElement('p');row.className='phase'+(index===frame?' active':'');row.textContent=item.cue.replaceAll('_',' ');phases.append(row);}}); }}
function render(bridge, index) {{ const item=bridge.frames[index]; stage.replaceChildren(); item.layers.forEach(layer=>{{ const spec=data.components[layer.component]; const image=document.createElement('img'); image.src='component-layers/'+spec.browser_layer; image.width=spec.size[0]*scale; image.height=spec.size[1]*scale; image.style.left=(layer.position[0]*scale)+'px'; image.style.top=(layer.position[1]*scale)+'px'; image.style.zIndex=String(layer.z_index); image.alt=''; stage.append(image); }}); phaseList(bridge,index); }}
function clearTimer() {{ if(timer){{clearTimeout(timer);timer=0;}} }}
function step() {{ clearTimer(); const bridge=selectedBridge(); if(!bridge) return; render(bridge,frameIndex); if(!running) return; const frame=bridge.frames[frameIndex]; if(frameIndex<bridge.frames.length-1) {{ frameIndex++; timer=setTimeout(step,frame.duration_ms); return; }} running=false; play.innerHTML='&#9654;'; play.title='Replay selected bridge'; play.setAttribute('aria-label',play.title); }}
function start() {{ running=true; play.innerHTML='&#10074;&#10074;'; play.title='Pause'; play.setAttribute('aria-label',play.title); frameIndex=0; activeKey=`${{source.value}}__${{target.value}}`; step(); }}
const query=readQuery(); setOptions(source,data.emotions,query.source); refreshTargets(query.target); start();
source.addEventListener('change',()=>{{refreshTargets();start();}}); target.addEventListener('change',start);
play.addEventListener('click',()=>{{if(!running){{start();return;}} running=false;play.innerHTML='&#9654;';play.title='Play';play.setAttribute('aria-label',play.title);clearTimer();}});
restart.addEventListener('click',start);
</script>
</html>
"""
    path.write_text(page, encoding="utf-8")


def main() -> int:
    gate = load_json(COMPONENT_GATE)
    require(gate.get("status") == "PASS_V21_EVERYDAY_EMOTION_COMPONENT_EXPORT_GATE",
            "V21 component source gate must pass before bridge rendering")
    layout = load_json(SOURCE_LAYOUT)
    require(layout.get("status") == "UNBOUND_ACCEPTED_SOURCE_PENDING_COMPONENT_BRIDGE_GATE" and
            layout.get("runtime_resource_activated") is False and layout.get("active_candidate_binding") == "forbidden",
            "V21 source layout is not an inactive component-only candidate")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    layer_dir = OUTPUT / "component-layers"
    layer_dir.mkdir(parents=True, exist_ok=True)

    identity_ranges = locked_v9_offset_ranges()
    identity = {
        name: load_component(record, None, identity_ranges[name])
        for name, record in layout["identity_components"].items()
    }
    require(tuple(sorted(identity)) == tuple(sorted(IDENTITY_NAMES)), "V21 identity vocabulary drifted")
    special: dict[str, Component] = {}
    for emotion, records in layout["emotion_components"].items():
        for name, record in records.items():
            special[name] = load_component(record, emotion)
    all_components = {**identity, **special}
    for component in all_components.values():
        png_path = layer_dir / f"{component.name}.png"
        rgba_layer(component).save(png_path)

    bridges: dict[str, dict[str, Any]] = {}
    default_images: list[Image.Image] = []
    default_durations: list[int] = []
    for source, target, event, gaze in BRIDGE_EDGES:
        key = f"{source}__{target}"
        specs = bridge_frames(identity, special, source, target, gaze)
        frame_images: list[Image.Image] = []
        rendered: list[dict[str, Any]] = []
        for index, spec in enumerate(specs):
            layers = [Layer(all_components[item["component"]], tuple(item["offset"])) for item in spec["layers"]]
            image = compose(layers)
            frame_images.append(image)
            target_path = OUTPUT / "bridge-frames-200x200" / f"{key}-{index:02d}-{spec['cue']}.pbm"
            write_mask(target_path, image)
            rendered.append({
                "index": index,
                **spec,
                "target_pbm": rel(target_path),
                "target_pbm_sha256": sha256(target_path),
            })
        settle_path = ROOT / str(layout["states"][target]["reassembly"])
        with Image.open(settle_path) as target_image:
            settle_distance = image_distance(frame_images[-1], target_image)
        require(settle_distance == 0, f"{key} final composed target differs from V21 reassembly")
        contact_path = OUTPUT / "bridge-contact-sheets" / f"{key}.png"
        write_contact_sheet(contact_path, frame_images)
        bridges[key] = {
            "source": source,
            "target": target,
            "event": event,
            "gaze_offset": list(gaze),
            "policy": "primary highlights lead; sparkles follow; brows and lower face reach apex; approved accent resolves last; highlights settle at target",
            "frames": rendered,
            "target_reassembly": layout["states"][target]["reassembly"],
            "final_target_pixel_distance": settle_distance,
            "contact_sheet": rel(contact_path),
        }
        if key == "calm__curious":
            default_images = frame_images
            default_durations = [int(spec["duration_ms"]) for spec in specs]

    gif_path = OUTPUT / "v21-everyday-emotion-component-bridge-preview.gif"
    write_gif(gif_path, default_images, default_durations)
    components_payload = {
        name: component_public(component, layer_dir / f"{name}.png")
        for name, component in sorted(all_components.items())
    }
    preview_payload = {
        "emotions": list(EMOTIONS),
        "components": components_payload,
        "bridges": browser_bridge_payload(bridges),
        "state_rotation": "forbidden",
        "whole_source_pose_playback": "forbidden",
        "browser_rendering": "registered_component_dom_layers_only",
    }
    preview_path = OUTPUT / "preview.html"
    build_preview_html(preview_path, preview_payload)
    layout_out = {
        "schema": "companion.v21_everyday_emotion_component_bridge_layout.v1",
        "status": "CANDIDATE_MACHINE_BRIDGE_GATE_PENDING",
        "source_component_layout": rel(SOURCE_LAYOUT),
        "source_component_layout_sha256": sha256(SOURCE_LAYOUT),
        "component_gate": rel(COMPONENT_GATE),
        "affect_core": {"valence_range": [-1, 2], "arousal_range": [1, 3], "nodes": AFFECT_NODES},
        "directed_edges": [{"source": source, "target": target, "event": event} for source, target, event, _ in BRIDGE_EDGES],
        "bridge_policy": "selected legal edge completes at the target baseline; primary highlights lead, sparkles follow, then brows/lower face/accent; no autonomous reverse or playlist",
        "research_refinement": {
            "owner_review": "docs/validation/companion-v21-everyday-emotion-component-bridge-owner-screen-review-20260719.json",
            "event_to_primary_highlight_lead_ms": 680,
            "temporal_shape": ["onset", "apex", "offset"],
            "automatic_reverse": "forbidden",
        },
        "components": components_payload,
        "bridges": bridges,
        "browser_preview": rel(preview_path),
        "browser_rendering": "registered_component_dom_layers_only",
        "target_rendering": "same_registered_component_sample_plan_to_200x200_pbm",
        "gif_preview": rel(gif_path),
        "prohibited": [
            "whole-source-pose playback", "whole-face replacement", "CEMP flipbook playback", "CRIG export",
            "runtime activation", "random emotion playlist", "menu recording upgrade binding",
            "sleep charging error fallback", "code-drawn facial pixels",
        ],
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    layout_path = OUTPUT / "component-bridge-layout.json"
    save_json(layout_path, layout_out)
    report = {
        "schema": "companion.v21_everyday_emotion_component_bridge_render.v1",
        "status": "PASS_V21_COMPONENT_ONLY_EMOTION_BRIDGE_RESEARCH_REFINED_CANDIDATE",
        "layout": rel(layout_path),
        "layout_sha256": sha256(layout_path),
        "bridge_count": len(bridges),
        "bridge_frame_count": sum(len(bridge["frames"]) for bridge in bridges.values()),
        "browser_preview": rel(preview_path),
        "gif_preview": rel(gif_path),
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
    }
    save_json(OUTPUT / "bridge-render-report.json", report)
    print(f"PASS: rendered {len(bridges)} V21 component-only directed emotion bridges for browser/200x200 parity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
