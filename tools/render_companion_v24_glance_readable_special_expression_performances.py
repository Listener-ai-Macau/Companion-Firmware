#!/usr/bin/env python3
"""Render unbound V24 special-state component performances at native 200x200."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
V9_RENDER = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
V9_TOUCH_TRACE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-20260719.json"
V9_DAILY = ROOT / "docs/validation/artifacts/companion-v9-expression-rig-daily-focus-accepted-dynamic-baseline-20260718/story-phases/daily_right_entry.pbm"
V24_EXPORT_GATE = ROOT / "docs/validation/companion-v24-glance-readable-special-expression-component-export-gate-20260720.json"
V24_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v24-glance-readable-special-expression-source/candidate/component-export-attempt-01/component-layout.json"
DEFAULT_ARTIFACT_DIR = ROOT / "docs/validation/artifacts/companion-v24-special-expression-performance-preview-20260720"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v24-glance-readable-special-expression-component-performance-preview-20260720.json"
CANVAS = (200, 200)
IDENTITY_ROLES = {"left_eye", "right_eye", "left_highlight", "right_highlight", "left_sparkle", "right_sparkle", "nose"}


@dataclass(frozen=True)
class Component:
    key: str
    name: str
    role: str
    source: str
    mask_path: Path
    mask_sha256: str
    base: tuple[int, int]
    minimum: tuple[int, int]
    maximum: tuple[int, int]
    z_index: int
    composite_op: str
    mask: Image.Image


@dataclass(frozen=True)
class Layer:
    component: Component
    x: int
    y: int


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def image_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.convert("1").getdata(), right.convert("1").getdata()))


def component_from_record(key: str, name: str, role: str, source: str, mask_path: Path,
                          mask_sha256: str, base: list[int], offset_range: dict[str, Any],
                          z_index: int, composite_op: str) -> Component:
    require(mask_path.is_file(), f"component mask is missing: {mask_path}")
    require(sha256(mask_path) == mask_sha256, f"component mask hash drifted: {key}")
    with Image.open(mask_path) as raw:
        mask = raw.convert("1")
    lower = offset_range.get("min", [0, 0])
    upper = offset_range.get("max", [0, 0])
    require(len(base) == len(lower) == len(upper) == 2, f"component geometry is invalid: {key}")
    return Component(
        key=key,
        name=name,
        role=role,
        source=source,
        mask_path=mask_path,
        mask_sha256=mask_sha256,
        base=(int(base[0]), int(base[1])),
        minimum=(int(lower[0]), int(lower[1])),
        maximum=(int(upper[0]), int(upper[1])),
        z_index=int(z_index),
        composite_op=composite_op,
        mask=mask,
    )


def load_components() -> tuple[dict[str, Component], dict[int, Component], dict[str, Component], dict[str, list[Component]], dict[str, Any]]:
    v9_layout = load_json(V9_LAYOUT)
    v9_render = load_json(V9_RENDER)
    v24_layout = load_json(V24_LAYOUT)
    require(v9_layout.get("source_baseline", {}).get("sha256") == LOCKED_V9_SHA256, "V9 layout lost locked source")
    require(v24_layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "V24 layout lost locked source")
    require(v24_layout.get("runtime_resource_activated") is False and v24_layout.get("active_candidate_binding") == "forbidden", "V24 layout is not runtime inactive and unbound")
    masks = {str(item.get("name")): item.get("component_mask") for item in v9_render.get("components", []) if isinstance(item, dict)}
    all_components: dict[str, Component] = {}
    v9_by_id: dict[int, Component] = {}
    v9_by_name: dict[str, Component] = {}
    for index, record in enumerate(v9_layout.get("components", []), start=1):
        require(isinstance(record, dict), "V9 layout component is malformed")
        name = str(record.get("name", ""))
        path = masks.get(name)
        require(name and isinstance(path, str), f"V9 component mask is missing: {name}")
        component = component_from_record(
            f"v9:{name}", name, str(record.get("role", "")), "locked_v9_rig_component", ROOT / path,
            sha256(ROOT / path), list(record.get("base_position", [])), dict(record.get("offset_range", {})),
            int(record.get("z_index", 0)), str(record.get("composite_op", "ink")),
        )
        all_components[component.key] = component
        v9_by_id[index] = component
        v9_by_name[name] = component
    special_by_pose: dict[str, list[Component]] = {}
    for pose, records in v24_layout.get("special_pose_components", {}).items():
        require(isinstance(records, dict), f"V24 {pose} component map is malformed")
        exported: list[Component] = []
        for name, record in records.items():
            require(isinstance(record, dict), f"V24 {pose} component is malformed")
            component = component_from_record(
                f"v24:{name}", str(record.get("name", "")), str(record.get("role", "")), str(record.get("source", "")),
                ROOT / str(record.get("mask", "")), str(record.get("mask_sha256", "")),
                list(record.get("base_position", [])), dict(record.get("offset_range", {})),
                int(record.get("z_index", 0)), str(record.get("composite_op", "ink")),
            )
            all_components[component.key] = component
            exported.append(component)
        special_by_pose[str(pose)] = exported
    return all_components, v9_by_id, v9_by_name, special_by_pose, v24_layout


def validate_layer(layer: Layer) -> None:
    offset = (layer.x - layer.component.base[0], layer.y - layer.component.base[1])
    require(layer.component.minimum[0] <= offset[0] <= layer.component.maximum[0] and layer.component.minimum[1] <= offset[1] <= layer.component.maximum[1], f"{layer.component.key} offset {offset} is outside its registered range")
    require(0 <= layer.x <= CANVAS[0] - layer.component.mask.width and 0 <= layer.y <= CANVAS[1] - layer.component.mask.height, f"{layer.component.key} leaves the target canvas")


def sorted_layers(layers: list[Layer]) -> list[Layer]:
    keys = [layer.component.key for layer in layers]
    require(len(keys) == len(set(keys)), "component plan duplicates a source component")
    ordered = sorted(layers, key=lambda layer: (layer.component.z_index, layer.component.key))
    for layer in ordered:
        validate_layer(layer)
    return ordered


def compose(layers: list[Layer]) -> Image.Image:
    canvas = Image.new("L", CANVAS, 255)
    for layer in sorted_layers(layers):
        alpha = layer.component.mask.convert("L").point(lambda value: 255 if value == 0 else 0)
        canvas.paste(255 if layer.component.composite_op == "erase" else 0, (layer.x, layer.y), alpha)
    return canvas.convert("1")


def public_layer(layer: Layer) -> dict[str, Any]:
    component = layer.component
    return {
        "component": component.key,
        "name": component.name,
        "role": component.role,
        "source": component.source,
        "x": layer.x,
        "y": layer.y,
        "offset": [layer.x - component.base[0], layer.y - component.base[1]],
        "z_index": component.z_index,
        "composite_op": component.composite_op,
    }


def export_layer(component: Component, destination: Path) -> None:
    alpha = component.mask.convert("L").point(lambda value: 255 if value == 0 else 0)
    color = (255, 255, 255, 255) if component.composite_op == "erase" else (0, 0, 0, 255)
    image = Image.new("RGBA", component.mask.size, (0, 0, 0, 0))
    image.paste(color, (0, 0), alpha)
    image.save(destination)


def v9_daily_layers(v9_by_id: dict[int, Component]) -> list[Layer]:
    trace = load_json(V9_TOUCH_TRACE)
    require(trace.get("status") == "PASS_TOUCH_TO_RIG_MACHINE_LOOP_RUNTIME_INACTIVE", "V9 Daily trace is not a passing inactive fixture")
    frame = trace.get("frames", [None])[0]
    require(isinstance(frame, dict), "V9 Daily trace has no entry frame")
    layers: list[Layer] = []
    for record in frame.get("layers", []):
        require(isinstance(record, dict), "V9 Daily layer is malformed")
        component = v9_by_id.get(record.get("component_id"))
        require(component is not None, "V9 Daily references an unregistered component")
        expected = 1 if component.composite_op == "erase" else 0
        require(record.get("composite_op") == expected, "V9 Daily composite operation drifted")
        layers.append(Layer(component, int(record.get("base_x")) + int(record.get("offset_x")), int(record.get("base_y")) + int(record.get("offset_y"))))
    return sorted_layers(layers)


def move_roles(layers: list[Layer], offsets: dict[str, tuple[int, int]]) -> list[Layer]:
    return sorted_layers([
        replace(layer, x=layer.x + offsets[layer.component.role][0], y=layer.y + offsets[layer.component.role][1]) if layer.component.role in offsets else layer
        for layer in layers
    ])


def special_layers(v9_by_name: dict[str, Component], special_by_pose: dict[str, list[Component]], pose: str,
                    include: set[str] | None = None, accent_offset: tuple[int, int] = (0, 0),
                    highlight_offset: tuple[int, int] = (0, 0),
                    face_offsets: dict[str, tuple[int, int]] | None = None) -> list[Layer]:
    identity = [
        "left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open",
        "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default",
    ]
    result: list[Layer] = []
    for name in identity:
        component = v9_by_name[name]
        offset = highlight_offset if component.role in {"left_highlight", "right_highlight"} else (0, 0)
        result.append(Layer(component, component.base[0] + offset[0], component.base[1] + offset[1]))
    require(pose in special_by_pose, f"V24 special pose is missing: {pose}")
    for component in special_by_pose[pose]:
        is_accent = component.role in {"accent", "left_listening_arc", "right_listening_arc"}
        if is_accent and include is not None and component.name not in include:
            continue
        offset = accent_offset if is_accent else (face_offsets or {}).get(component.role, (0, 0))
        result.append(Layer(component, component.base[0] + offset[0], component.base[1] + offset[1]))
    return sorted_layers(result)


def accent_names(special_by_pose: dict[str, list[Component]], pose: str, suffixes: set[str] | None = None) -> set[str]:
    names: set[str] = set()
    for component in special_by_pose[pose]:
        if component.role not in {"accent", "left_listening_arc", "right_listening_arc"}:
            continue
        if suffixes is None or any(component.name.endswith(suffix) for suffix in suffixes):
            names.add(component.name)
    return names


def write_player(path: Path, data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    template = """<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>V24 Special Expression Component Preview</title><style>
body{{margin:0;background:#f3f3f1;color:#151515;font:14px Arial,sans-serif}}main{{max-width:560px;margin:24px auto;padding:0 18px}}h1{{margin:0 0 10px;font-size:24px}}p{{margin:0 0 14px;line-height:1.45}}#stage{{position:relative;width:200px;height:200px;background:#fff;border:1px solid #202020;image-rendering:pixelated}}#stage img{{position:absolute;width:auto;height:auto;image-rendering:pixelated}}#meta{{margin:12px 0;font-family:monospace;white-space:pre-wrap}}button{{margin:0 8px 8px 0;padding:7px 10px;border:1px solid #222;background:#fff;color:#111}}button.active{{background:#151515;color:#fff}}
</style><main><h1>V24 Special Expression Component Preview</h1><p>Each choice plays one explicit event performance and stops at Daily. The stage is a native 200x200 component compositor; it does not play whole-face cards.</p><div id=\"stage\"></div><div id=\"meta\"></div><div><button data-scene=\"daily_micro\">Daily</button><button data-scene=\"menu_active\">Menu</button><button data-scene=\"recording_active\">Recording</button><button data-scene=\"charging_active\">Charging</button></div><button id=\"prev\">Previous</button><button id=\"next\">Next</button><button id=\"play\">Play</button></main><script>
const DATA=__DATA__;const stage=document.getElementById('stage'),meta=document.getElementById('meta'),play=document.getElementById('play');const scenes=new Map(DATA.performances.map((entry)=>[entry.id,entry]));function inspectCursor(scene){{const target=Number.isInteger(scene.inspect_frame_index)?scene.inspect_frame_index:scene.frame_indices[0];const found=scene.frame_indices.indexOf(target);return found>=0?found:0;}}let active=scenes.get('daily_micro'),cursor=inspectCursor(active),index=active.frame_indices[cursor],timer=null,inspection=true;
function render(){{const frame=DATA.frames[index];stage.replaceChildren();for(const layer of frame.layers){{const image=document.createElement('img');image.src='components/'+layer.component.replaceAll(':','__')+'.png';image.style.left=layer.x+'px';image.style.top=layer.y+'px';stage.append(image);}}meta.textContent=`${{active.event}}  ${{cursor+1}}/${{active.frame_indices.length}}  ${{frame.phase}}\n${{frame.logicalState}} / ${{frame.artPose}}`;for(const button of document.querySelectorAll('[data-scene]')){{button.classList.toggle('active',button.dataset.scene===active.id);}}}}
function stop(){{if(timer){{clearTimeout(timer);timer=null;}}play.textContent='Play';}}
function choose(id){{stop();active=scenes.get(id);cursor=inspectCursor(active);index=active.frame_indices[cursor];inspection=true;render();}}
function move(delta){{stop();inspection=false;cursor=(cursor+active.frame_indices.length+delta)%active.frame_indices.length;index=active.frame_indices[cursor];render();}}
function advance(){{if(cursor+1>=active.frame_indices.length){{stop();return;}}cursor+=1;index=active.frame_indices[cursor];render();timer=setTimeout(advance,DATA.frames[index].postRefreshHoldMs);}}
document.querySelectorAll('[data-scene]').forEach((button)=>{{button.onclick=()=>choose(button.dataset.scene);}});document.getElementById('prev').onclick=()=>move(-1);document.getElementById('next').onclick=()=>move(1);play.onclick=()=>{{if(timer){{stop();}}else{{if(inspection||cursor+1>=active.frame_indices.length){{cursor=0;index=active.frame_indices[0];inspection=false;render();}}play.textContent='Pause';timer=setTimeout(advance,DATA.frames[index].postRefreshHoldMs);}}};const query=new URLSearchParams(window.location.search),requested=query.get('scene');if(scenes.has(requested)){{choose(requested);}}render();if(query.get('autoplay')==='1'){{play.click();}}
</script></html>"""
    path.write_text(template.replace("{{", "{").replace("}}", "}").replace("__DATA__", payload), encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--write", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    report_path = args.write if args.write.is_absolute() else ROOT / args.write
    export_gate = load_json(V24_EXPORT_GATE)
    require(export_gate.get("status") == "PASS_V24_SPECIAL_COMPONENT_EXPORT_UNBOUND", "V24 component export gate is not PASS")
    require(export_gate.get("runtime_resource_activated") is False, "V24 export gate unexpectedly activated runtime")
    components, v9_by_id, v9_by_name, special_by_pose, v24_layout = load_components()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    component_dir = artifact_dir / "components"
    component_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    used: dict[str, Component] = {}

    def append(segment: str, logical_state: str, art_pose: str, layers: list[Layer], event: str, phase: str, hold: int = 750, *, allow_event_entry_repeat: bool = False) -> None:
        ordered = sorted_layers(layers)
        image = compose(ordered)
        if images and not allow_event_entry_repeat:
            require(image_distance(images[-1], image) > 0, f"{segment} repeated the preceding target frame")
        index = len(frames)
        target = artifact_dir / f"frame-{index:02d}-{segment}.pbm"
        image.save(target, format="PPM")
        for layer in ordered:
            used[layer.component.key] = layer.component
        frames.append({
            "index": index,
            "segment": segment,
            "logicalState": logical_state,
            "artPose": art_pose,
            "event": event,
            "phase": phase,
            "postRefreshHoldMs": hold,
            "layers": [public_layer(layer) for layer in ordered],
            "targetPbm": rel(target),
            "targetPbmSha256": sha256(target),
        })
        images.append(image)

    daily = v9_daily_layers(v9_by_id)
    with Image.open(V9_DAILY) as raw:
        daily_static = raw.convert("1")
    require(image_distance(compose(daily), daily_static) == 0, "V9 component plan does not reconstruct the accepted Daily frame")
    append("daily_entry", "daily", "v9_daily", daily, "daily_auto", "emotion_hold", 800)
    append("daily_highlight_notice", "daily", "v9_daily", move_roles(daily, {"left_highlight": (1, -1), "right_highlight": (1, -1)}), "daily_auto", "micro_choreography", 180)
    append("daily_star_lift", "daily", "v9_daily", move_roles(daily, {"charm": (1, -2)}), "daily_auto", "micro_choreography", 220)
    append("daily_settle", "daily", "v9_daily", daily, "daily_auto", "emotion_hold", 1000)
    daily_performance = list(range(0, len(frames)))
    performances: list[dict[str, Any]] = [{"id": "daily_micro", "event": "daily_auto", "frame_indices": daily_performance, "inspect_frame_index": 0, "terminal_art_pose": "v9_daily"}]
    special_reassembly_differences: dict[str, int] = {}

    def append_special_performance(pose: str, enter_event: str, exit_event: str, sequence: list[tuple[str, set[str] | None, dict[str, tuple[int, int]], tuple[int, int], tuple[int, int], str, int]]) -> None:
        start = len(frames)
        append(f"{pose}_daily_entry", "daily", "v9_daily", daily, enter_event, "entry", 700, allow_event_entry_repeat=True)
        append(f"{pose}_daily_notice", "daily", "v9_daily", move_roles(daily, {"left_highlight": (1, -1), "right_highlight": (1, -1)}), enter_event, "prepare", 380)
        state_hold_index: int | None = None
        for label, included, face_offsets, accent_delta, highlight_delta, phase, hold in sequence:
            layers = special_layers(v9_by_name, special_by_pose, pose, included, accent_delta, highlight_delta, face_offsets)
            append(f"{pose}_{label}", pose, pose, layers, enter_event if phase != "release" else exit_event, phase, hold)
            if label == "state_hold":
                state_hold_index = len(frames) - 1
                target_path = ROOT / str(v24_layout["states"][pose]["reassembly"])
                with Image.open(target_path) as raw:
                    difference = image_distance(compose(layers), raw.convert("1"))
                require(difference == 0, f"{pose} state hold drifted from V24 component reassembly")
                special_reassembly_differences[pose] = difference
        append(f"{pose}_daily_settle", "daily", "v9_daily", daily, exit_event, "settle", 900)
        require(state_hold_index is not None, f"{pose} has no target hold frame")
        performances.append({"id": pose, "event": enter_event, "exit_event": exit_event, "frame_indices": list(range(start, len(frames)),), "inspect_frame_index": state_hold_index, "terminal_art_pose": "v9_daily"})

    menu_accents = accent_names(special_by_pose, "menu_active")
    append_special_performance(
        "menu_active", "menu_hold", "menu_exit",
        [
            ("face_arrival", set(), {"left_brow": (0, -2), "right_brow": (0, -2), "left_cheek": (0, 1), "right_cheek": (0, 1), "mouth": (0, 1)}, (0, 0), (0, -1), "transition", 420),
            ("face_settle", set(), {}, (0, 0), (0, 0), "transition", 420),
            ("dots_lead", {"v24_menu_active__selection_dot_left"}, {}, (0, -1), (0, -1), "micro_choreography", 300),
            ("dots_response", {"v24_menu_active__selection_dot_left", "v24_menu_active__selection_dot_center"}, {}, (0, -1), (0, -1), "micro_choreography", 300),
            ("state_hold", menu_accents, {}, (0, 0), (0, 0), "emotion_hold", 1400),
            ("dots_release", set(), {}, (0, 0), (0, -1), "release", 360),
        ],
    )
    recording_inner = accent_names(special_by_pose, "recording_active", {"left_listening_inner", "right_listening_inner"})
    recording_all = accent_names(special_by_pose, "recording_active")
    append_special_performance(
        "recording_active", "recording_active", "recording_stop_or_cancel",
        [
            ("face_arrival", set(), {"left_brow": (0, -2), "right_brow": (0, -2), "left_cheek": (0, 1), "right_cheek": (0, 1), "mouth": (0, 1)}, (0, 0), (0, -1), "transition", 420),
            ("face_settle", set(), {}, (0, 0), (0, 0), "transition", 420),
            ("listening_inner", recording_inner, {}, (0, 0), (0, -1), "micro_choreography", 320),
            ("state_hold", recording_all, {}, (0, 0), (0, 0), "emotion_hold", 1400),
            ("listening_release", set(), {}, (0, 0), (0, -1), "release", 360),
        ],
    )
    charging_left = accent_names(special_by_pose, "charging_active", {"breathing_arc_left"})
    charging_all = accent_names(special_by_pose, "charging_active")
    append_special_performance(
        "charging_active", "charging", "charging_unplug",
        [
            ("face_arrival", set(), {"left_brow": (0, -2), "right_brow": (0, -2), "left_cheek": (0, 1), "right_cheek": (0, 1), "mouth": (0, 1)}, (0, 0), (0, -1), "transition", 420),
            ("face_settle", set(), {}, (0, 0), (0, 0), "transition", 420),
            ("breathing_lead", charging_left, {}, (0, -1), (0, -1), "micro_choreography", 360),
            ("state_hold", charging_all, {}, (0, 0), (0, 0), "emotion_hold", 1400),
            ("breathing_release", set(), {}, (0, 0), (0, -1), "release", 360),
        ],
    )
    require(image_distance(images[-1], daily_static) == 0, "V24 special performances do not settle to exact V9 Daily")
    selection_policy = {
        "mode": "explicit_event_performance",
        "random_state_selection": False,
        "automatic_cross_state_cycle": False,
        "daily_auto_only_runs_daily_micro_choreography": True,
        "special_state_exit_returns_to": "v9_daily",
        "unavailable_special_states": ["upgrade", "sleep", "error"],
        "unavailable_special_state_policy": "fail_closed",
    }
    for component in used.values():
        export_layer(component, component_dir / f"{component.key.replace(':', '__')}.png")
    browser_data = {
        "schema": "companion.v24_glance_readable_special_expression_component_browser_trace.v1",
        "runtimeResourceActivated": False,
        "selectionPolicy": selection_policy,
        "performances": performances,
        "frames": frames,
    }
    player = artifact_dir / "player.html"
    write_player(player, browser_data)
    report = {
        "schema": "companion.v24_glance_readable_special_expression_component_performance_preview.v1",
        "status": "PASS_V24_SPECIAL_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE",
        "claim_scope": "candidate component choreography and target PBM plan only; not a behavior binding, CRIG, firmware flash, panel output, or physical acceptance",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "source_component_export_gate": rel(V24_EXPORT_GATE),
        "runtime_resource_activated": False,
        "physical_panel_acceptance": False,
        "selection_policy": selection_policy,
        "performances": performances,
        "special_state_reassembly_differences_pixels": special_reassembly_differences,
        "daily_entry_settle_difference_pixels": {"entry": image_distance(images[0], daily_static), "final_settle": image_distance(images[-1], daily_static)},
        "frames": frames,
        "browser_player": {"path": rel(player), "sha256": sha256(player)},
        "component_count": len(used),
        "components": [
            {"key": component.key, "name": component.name, "role": component.role, "source": component.source, "mask": rel(component.mask_path), "mask_sha256": component.mask_sha256}
            for component in sorted(used.values(), key=lambda item: item.key)
        ],
        "forbidden": ["whole-face card playback", "code-drawn face", "legacy art", "custom LUT", "runtime binding"],
        "active_candidate_binding": "forbidden",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: rendered {len(frames)} V24 component-performance frames -> {rel(report_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
