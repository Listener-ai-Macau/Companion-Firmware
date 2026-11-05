#!/usr/bin/env python3
"""Build an inactive V9-to-V22 component-only touch emotion route at 200x200."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
V9_RENDER = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
V9_TOUCH_TRACE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-20260719.json"
V9_DAILY = ROOT / (
    "docs/validation/artifacts/companion-v9-expression-rig-daily-focus-accepted-dynamic-baseline-20260718/"
    "story-phases/daily_right_entry.pbm"
)
V22_LAYOUT = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/"
    "candidate/component-bridge-attempt-01/component-bridge-layout.json"
)
V22_REASSEMBLED = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/"
    "candidate/component-export-attempt-03/reassembled-200x200"
)
V22_OWNER_REVIEW = ROOT / "docs/validation/companion-v22-emotion-separation-component-bridge-owner-art-screen-review-20260719.json"
DEFAULT_ARTIFACT_DIR = ROOT / "docs/validation/artifacts/companion-v9-v22-touch-emotion-route-preview-20260720"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v9-v22-touch-emotion-route-preview-20260720.json"
CANVAS = (200, 200)
V22_SELECTED_CUES = ("primary_highlight_lead", "brow_apex", "lower_face_apex", "target_hold", "highlight_settle")


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
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def image_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.convert("1").getdata(), right.convert("1").getdata()))


def component_from_record(key: str, name: str, role: str, source: str, mask_path: Path,
                          mask_sha256: str, base: list[int], offset_range: dict[str, Any],
                          z_index: int, composite_op: str) -> Component:
    require(mask_path.is_file(), f"Component mask is missing: {mask_path}")
    require(sha256(mask_path) == mask_sha256, f"Component mask hash drifted: {key}")
    with Image.open(mask_path) as source_image:
        mask = source_image.convert("1")
    low = offset_range.get("min", [0, 0])
    high = offset_range.get("max", [0, 0])
    require(len(base) == len(low) == len(high) == 2, f"Component geometry is invalid: {key}")
    return Component(
        key=key,
        name=name,
        role=role,
        source=source,
        mask_path=mask_path,
        mask_sha256=mask_sha256,
        base=(int(base[0]), int(base[1])),
        minimum=(int(low[0]), int(low[1])),
        maximum=(int(high[0]), int(high[1])),
        z_index=z_index,
        composite_op=composite_op,
        mask=mask,
    )


def load_components() -> tuple[dict[str, Component], dict[int, Component], dict[str, Component], dict[str, Any]]:
    v9_layout = load_json(V9_LAYOUT)
    v9_render = load_json(V9_RENDER)
    v22_layout = load_json(V22_LAYOUT)
    require(v9_layout.get("source_baseline", {}).get("sha256") == LOCKED_SOURCE_HASH,
            "V9 layout is not bound to the locked source")
    require(v22_layout.get("runtime_resource_activated") is False and
            v22_layout.get("active_candidate_binding") == "forbidden",
            "V22 source candidate must remain inactive and unbound")
    masks = {
        str(item.get("name")): item.get("component_mask")
        for item in v9_render.get("components", []) if isinstance(item, dict)
    }
    by_key: dict[str, Component] = {}
    v9_by_id: dict[int, Component] = {}
    v9_by_name: dict[str, Component] = {}
    for index, item in enumerate(v9_layout.get("components", []), start=1):
        require(isinstance(item, dict), "V9 component record is malformed")
        name = str(item.get("name", ""))
        mask = masks.get(name)
        require(name and isinstance(mask, str), f"V9 component has no rendered mask: {name}")
        component = component_from_record(
            f"v9:{name}", name, str(item.get("role")), "locked_v9_rig_component",
            ROOT / mask, sha256(ROOT / mask), list(item.get("base_position", [])),
            dict(item.get("offset_range", {})), int(item.get("z_index")),
            str(item.get("composite_op", "ink")),
        )
        by_key[component.key] = component
        v9_by_id[index] = component
        v9_by_name[name] = component
    for name, item in v22_layout.get("components", {}).items():
        require(isinstance(item, dict), "V22 component record is malformed")
        component = component_from_record(
            f"v22:{name}", str(item.get("name")), str(item.get("role")), str(item.get("source")),
            ROOT / str(item.get("mask")), str(item.get("mask_sha256")),
            list(item.get("base_position", [])), dict(item.get("offset_range", {})),
            int(item.get("z_index")), str(item.get("composite_op")),
        )
        by_key[component.key] = component
    return by_key, v9_by_id, v9_by_name, v22_layout


def validate_layer(layer: Layer) -> None:
    offset = (layer.x - layer.component.base[0], layer.y - layer.component.base[1])
    require(layer.component.minimum[0] <= offset[0] <= layer.component.maximum[0] and
            layer.component.minimum[1] <= offset[1] <= layer.component.maximum[1],
            f"{layer.component.key} offset {offset} is outside its registered range")
    require(0 <= layer.x <= CANVAS[0] - layer.component.mask.width and
            0 <= layer.y <= CANVAS[1] - layer.component.mask.height,
            f"{layer.component.key} leaves the 200x200 target canvas")


def sorted_layers(layers: list[Layer]) -> list[Layer]:
    keys = [layer.component.key for layer in layers]
    require(len(keys) == len(set(keys)), "Component plan duplicates a source component")
    result = sorted(layers, key=lambda layer: (layer.component.z_index, layer.component.key))
    for layer in result:
        validate_layer(layer)
    return result


def compose(layers: list[Layer]) -> Image.Image:
    canvas = Image.new("L", CANVAS, 255)
    for layer in sorted_layers(layers):
        alpha = layer.component.mask.convert("L").point(lambda value: 255 if value == 0 else 0)
        color = 255 if layer.component.composite_op == "erase" else 0
        canvas.paste(color, (layer.x, layer.y), alpha)
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
    output = Image.new("RGBA", component.mask.size, (0, 0, 0, 0))
    output.paste(color, (0, 0), alpha)
    output.save(destination)


def v9_daily_layers(v9_by_id: dict[int, Component]) -> list[Layer]:
    trace = load_json(V9_TOUCH_TRACE)
    require(trace.get("status") == "PASS_TOUCH_TO_RIG_MACHINE_LOOP_RUNTIME_INACTIVE",
            "V9 touch trace is not a passing inactive fixture")
    frame = trace.get("frames", [None])[0]
    require(isinstance(frame, dict), "V9 touch trace has no entry frame")
    layers: list[Layer] = []
    for item in frame.get("layers", []):
        require(isinstance(item, dict), "V9 entry layer is malformed")
        component = v9_by_id.get(item.get("component_id"))
        require(component is not None, "V9 entry layer references an unregistered component")
        require(item.get("composite_op") == (1 if component.composite_op == "erase" else 0),
                "V9 entry layer composite operation drifted")
        layers.append(Layer(component, int(item.get("base_x")) + int(item.get("offset_x")),
                            int(item.get("base_y")) + int(item.get("offset_y"))))
    return sorted_layers(layers)


def v22_layers(v22_layout: dict[str, Any], components: dict[str, Component], bridge: str, cue: str) -> list[Layer]:
    frames = v22_layout.get("bridges", {}).get(bridge, {}).get("frames", [])
    frame = next((item for item in frames if item.get("cue") == cue), None)
    require(isinstance(frame, dict), f"V22 bridge {bridge} has no {cue} frame")
    result: list[Layer] = []
    for item in frame.get("layers", []):
        require(isinstance(item, dict), f"V22 bridge {bridge} layer is malformed")
        key = f"v22:{item.get('component')}"
        component = components.get(key)
        require(component is not None, f"V22 bridge references unknown component {key}")
        position = item.get("position")
        require(isinstance(position, list) and len(position) == 2, f"V22 bridge position is malformed: {key}")
        result.append(Layer(component, int(position[0]), int(position[1])))
    return sorted_layers(result)


def replace_roles(base: list[Layer], replacement: list[Layer], roles: set[str], remove_charm: bool) -> list[Layer]:
    result = [layer for layer in base if layer.component.role not in roles and
              not (remove_charm and layer.component.role == "charm")]
    result.extend(layer for layer in replacement if layer.component.role in roles)
    return sorted_layers(result)


def move_roles(base: list[Layer], offsets: dict[str, tuple[int, int]]) -> list[Layer]:
    return sorted_layers([
        replace(layer, x=layer.x + offsets[layer.component.role][0], y=layer.y + offsets[layer.component.role][1])
        if layer.component.role in offsets else layer
        for layer in base
    ])


def add_star(base: list[Layer], star: Component) -> list[Layer]:
    return sorted_layers([*base, Layer(star, star.base[0] + 1, star.base[1] - 2)])


def write_player(path: Path, data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    template = """<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>V9 Touch Emotion Route</title><style>
body{{margin:0;background:#f3f3f1;color:#151515;font:14px Arial,sans-serif}}main{{max-width:460px;margin:24px auto;padding:0 18px}}h1{{margin:0 0 14px;font-size:22px}}#stage{{position:relative;width:200px;height:200px;background:#fff;border:1px solid #202020;image-rendering:pixelated}}#stage img{{position:absolute;width:auto;height:auto;image-rendering:pixelated}}#meta{{margin:12px 0;font-family:monospace;white-space:pre-wrap}}button{{margin:0 8px 8px 0;padding:7px 10px;border:1px solid #222;background:#fff;color:#111}}button.active{{background:#151515;color:#fff}}
</style><main><h1>V9 Touch Emotion Route</h1><div id=\"stage\"></div><div id=\"meta\"></div><div><button data-scene=\"daily_micro\">Daily</button><button data-scene=\"familiar_touch\">Familiar touch</button><button data-scene=\"idle_settle\">Settle</button></div><button id=\"prev\">Previous</button><button id=\"next\">Next</button><button id=\"play\">Play</button></main><script>
const DATA=__DATA__;const stage=document.getElementById('stage'),meta=document.getElementById('meta'),play=document.getElementById('play');const scenes=new Map(DATA.performances.map((entry)=>[entry.id,entry]));let active=scenes.get('daily_micro'),cursor=0,index=active.frame_indices[0],timer=null;
function render(){{const frame=DATA.frames[index];stage.replaceChildren();for(const layer of frame.layers){{const image=document.createElement('img');image.src='components/'+layer.component.replace(':','__')+'.png';image.style.left=layer.x+'px';image.style.top=layer.y+'px';stage.append(image);}}meta.textContent=`${{active.event}}  ${{cursor+1}}/${{active.frame_indices.length}}  ${{frame.phase}}\n${{frame.logicalEmotion}} / ${{frame.artPose}}`;for(const button of document.querySelectorAll('[data-scene]')){{button.classList.toggle('active',button.dataset.scene===active.id);}}}}
function stop(){{if(timer){{clearTimeout(timer);timer=null;}}play.textContent='Play';}}
function choose(id){{stop();active=scenes.get(id);cursor=0;index=active.frame_indices[0];render();}}
function move(delta){{stop();cursor=(cursor+active.frame_indices.length+delta)%active.frame_indices.length;index=active.frame_indices[cursor];render();}}
function advance(){{if(cursor+1>=active.frame_indices.length){{stop();return;}}cursor+=1;index=active.frame_indices[cursor];render();timer=setTimeout(advance,DATA.frames[index].postRefreshHoldMs);}}
document.querySelectorAll('[data-scene]').forEach((button)=>{{button.onclick=()=>choose(button.dataset.scene);}});
document.getElementById('prev').onclick=()=>move(-1);document.getElementById('next').onclick=()=>move(1);
play.onclick=()=>{{if(timer){{stop();}}else{{if(cursor+1>=active.frame_indices.length){{cursor=0;index=active.frame_indices[0];render();}}play.textContent='Pause';timer=setTimeout(advance,DATA.frames[index].postRefreshHoldMs);}}};
const query=new URLSearchParams(window.location.search),requested=query.get('scene');if(scenes.has(requested)){{choose(requested);}}render();if(query.get('autoplay')==='1'){{play.click();}}
</script></html>"""
    rendered = template.replace("{{", "{").replace("}}", "}")
    path.write_text(rendered.replace("__DATA__", payload), encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--write", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    report_path = args.write if args.write.is_absolute() else ROOT / args.write
    components, v9_by_id, v9_by_name, v22_layout = load_components()
    require(load_json(V22_OWNER_REVIEW).get("status") ==
            "PASS_OWNER_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_ACCEPTED_RUNTIME_INACTIVE",
            "V22 source bridge lacks its owner-accepted inactive review")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    component_dir = artifact_dir / "components"
    component_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    used: dict[str, Component] = {}

    def append(segment: str, logical_emotion: str, art_pose: str, layers: list[Layer], hold: int = 750,
               *, phase: str, event: str) -> None:
        ordered = sorted_layers(layers)
        image = compose(ordered)
        if images:
            require(image_distance(images[-1], image) > 0, f"{segment} repeated its previous full target frame")
        index = len(frames)
        pbm = artifact_dir / f"frame-{index:02d}-{segment}.pbm"
        image.save(pbm, format="PPM")
        for layer in ordered:
            used[layer.component.key] = layer.component
        frames.append({
            "index": index,
            "segment": segment,
            "logicalEmotion": logical_emotion,
            "artPose": art_pose,
            "phase": phase,
            "event": event,
            "postRefreshHoldMs": hold,
            "layers": [public_layer(layer) for layer in ordered],
            "targetPbm": rel(pbm),
            "targetPbmSha256": sha256(pbm),
        })
        images.append(image)

    v9 = v9_daily_layers(v9_by_id)
    star = v9_by_name["charm_star"]
    v22_calm = v22_layers(v22_layout, components, "calm__curious", "source_hold")
    append("v9_daily_entry", "calm", "v9_daily", v9, phase="emotion_hold", event="daily_auto")
    append("v9_attention_lead", "calm", "v9_daily",
           move_roles(v9, {"left_highlight": (1, -1), "right_highlight": (1, -1)}),
           phase="micro_choreography", event="daily_auto")
    append("v9_charm_lift", "calm", "v9_daily", move_roles(v9, {"charm": (1, -2)}),
           phase="micro_choreography", event="daily_auto")
    append("v9_daily_micro_settle", "calm", "v9_daily", v9, phase="emotion_hold", event="daily_auto")
    daily_micro_settle_index = len(frames) - 1
    append("v9_to_calm_brows", "calm", "v22_calm",
           replace_roles(v9, v22_calm, {"left_brow", "right_brow"}, True),
           phase="transition", event="familiar_touch")
    append("v9_to_calm_lower", "calm", "v22_calm", replace_roles(v9, v22_calm,
           {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}, True),
           phase="transition", event="familiar_touch")
    waypoint_indices = {"v22_calm": len(frames) - 1}

    def append_v22_bridge(key: str, logical_target: str, art_target: str, event: str) -> None:
        for cue in V22_SELECTED_CUES:
            append(f"{key}_{cue}", logical_target, art_target,
                   v22_layers(v22_layout, components, key, cue), 1500 if cue == "target_hold" else 750,
                   phase=("emotion_hold" if cue == "target_hold" else
                          "micro_choreography" if cue == "highlight_settle" else "transition"),
                   event=event)
        waypoint_indices[f"{key}_target"] = len(frames) - 1

    append_v22_bridge("calm__curious", "curious", "v22_curious", "familiar_touch")
    append_v22_bridge("curious__warm", "affectionate", "v22_warm", "familiar_touch")
    familiar_touch_terminal_index = waypoint_indices["curious__warm_target"]
    append_v22_bridge("warm__curious", "curious", "v22_curious", "idle_settle")
    append_v22_bridge("curious__calm", "calm", "v22_calm", "idle_settle")

    returning = v22_layers(v22_layout, components, "curious__calm", "highlight_settle")
    append("calm_to_v9_brows", "calm", "v9_daily",
           replace_roles(returning, v9, {"left_brow", "right_brow"}, False),
           phase="transition", event="idle_settle")
    append("calm_to_v9_lower", "calm", "v9_daily", replace_roles(returning, v9,
           {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}, False),
           phase="transition", event="idle_settle")
    append("calm_to_v9_charm", "calm", "v9_daily", add_star(replace_roles(returning, v9,
           {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}, False), star),
           phase="transition", event="idle_settle")
    append("v9_daily_settle", "calm", "v9_daily", v9, phase="emotion_hold", event="idle_settle")

    with Image.open(V9_DAILY) as source:
        v9_static = source.convert("1")
    static_differences = {
        "entry": image_distance(images[0], v9_static),
        "settle": image_distance(images[-1], v9_static),
    }
    require(static_differences == {"entry": 0, "settle": 0}, "Route did not return to the exact V9 Daily baseline")
    daily_micro_settle_difference = image_distance(images[daily_micro_settle_index], v9_static)
    require(daily_micro_settle_difference == 0, "Daily micro choreography did not settle to the exact V9 baseline")
    v22_waypoints: list[dict[str, Any]] = []
    for name, emotion in (("v22_calm", "calm"), ("calm__curious_target", "curious"),
                          ("curious__warm_target", "warm"), ("warm__curious_target", "curious"),
                          ("curious__calm_target", "calm")):
        index = waypoint_indices[name]
        with Image.open(V22_REASSEMBLED / f"{emotion}.pbm") as target:
            difference = image_distance(images[index], target.convert("1"))
        require(difference == 0, f"Route {name} drifted from its accepted V22 {emotion} component pose")
        v22_waypoints.append({"name": name, "frame_index": index, "emotion": emotion, "different_pixels": difference})
    performances = [
        {
            "id": "daily_micro",
            "event": "daily_auto",
            "frame_indices": list(range(0, daily_micro_settle_index + 1)),
            "terminal_art_pose": "v9_daily",
        },
        {
            "id": "familiar_touch",
            "event": "familiar_touch",
            "frame_indices": list(range(daily_micro_settle_index, familiar_touch_terminal_index + 1)),
            "terminal_art_pose": "v22_warm",
        },
        {
            "id": "idle_settle",
            "event": "idle_settle",
            "frame_indices": list(range(familiar_touch_terminal_index, len(frames))),
            "terminal_art_pose": "v9_daily",
        },
    ]
    micro_choreography = {
        "daily": list(range(0, daily_micro_settle_index + 1)),
        "curious": [waypoint_indices["calm__curious_target"] - 1, waypoint_indices["calm__curious_target"],
                    waypoint_indices["warm__curious_target"] - 1, waypoint_indices["warm__curious_target"]],
        "affectionate": [familiar_touch_terminal_index - 1, familiar_touch_terminal_index],
        "calm": [waypoint_indices["curious__calm_target"] - 1, waypoint_indices["curious__calm_target"]],
    }
    selection_policy = {
        "mode": "explicit_event_performance",
        "random_emotion_selection": False,
        "automatic_cross_emotion_cycle": False,
        "daily_auto_only_runs_daily_micro_choreography": True,
        "familiar_touch_terminal_logical_emotion": "affectionate",
        "idle_settle_returns_to": "v9_daily",
    }
    for component in used.values():
        export_layer(component, component_dir / f"{component.key.replace(':', '__')}.png")
    browser_data = {
        "schema": "companion.v9_v22_touch_emotion_browser_trace.v1",
        "runtimeResourceActivated": False,
        "selectionPolicy": selection_policy,
        "performances": performances,
        "frames": frames,
    }
    player = artifact_dir / "v9-v22-touch-emotion-route-player.html"
    write_player(player, browser_data)
    report = {
        "schema": "companion.v9_v22_touch_emotion_route_preview.v1",
        "status": "PASS_V9_V22_TOUCH_EMOTION_ROUTE_RUNTIME_INACTIVE",
        "claim_scope": "candidate_component_route_preview_and_target_pbm_plan_not_runtime_binding_flash_or_physical_acceptance",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "physical_panel_acceptance": False,
        "logical_route": ["calm", "curious", "affectionate", "curious", "calm"],
        "art_route": ["v9_daily", "v22_calm", "v22_curious", "v22_warm", "v22_curious", "v22_calm", "v9_daily"],
        "affectionate_art_pose": "v22_warm",
        "entry_settle_v9_static_difference_pixels": static_differences,
        "daily_micro_settle_v9_static_difference_pixels": daily_micro_settle_difference,
        "v22_waypoints": v22_waypoints,
        "selection_policy": selection_policy,
        "performances": performances,
        "emotion_micro_choreography": micro_choreography,
        "frames": frames,
        "browser_player": {"path": rel(player), "sha256": sha256(player)},
        "component_count": len(used),
        "components": [{
            "key": component.key, "name": component.name, "role": component.role, "source": component.source,
            "mask": rel(component.mask_path), "mask_sha256": component.mask_sha256,
        } for component in sorted(used.values(), key=lambda item: item.key)],
        "v9_daily_baseline": {"path": rel(V9_DAILY), "sha256": sha256(V9_DAILY)},
        "v22_owner_review": {"path": rel(V22_OWNER_REVIEW), "sha256": sha256(V22_OWNER_REVIEW)},
        "forbidden": ["whole-face card playback", "code-drawn face", "legacy art", "custom LUT", "runtime binding"],
        "special_state_fallback": "fail_closed",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: rendered {len(frames)} V9/V22 touch-emotion component frames -> {rel(report_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
