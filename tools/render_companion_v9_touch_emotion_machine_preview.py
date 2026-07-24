#!/usr/bin/env python3
"""Render a browser component player from the runtime-inactive target touch trace."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
from typing import Any

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
RENDER_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
DEFAULT_TRACE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-20260719.json"
DEFAULT_ARTIFACT_DIR = ROOT / "docs/validation/artifacts/companion-v9-rig-touch-emotion-machine-preview-20260719"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-preview-20260719.json"
DAILY_RIGHT_STATIC_BASELINE = ROOT / (
    "docs/validation/artifacts/companion-v9-expression-rig-daily-focus-accepted-dynamic-baseline-20260718/"
    "story-phases/daily_right_entry.pbm"
)
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def catalog(layout: dict[str, Any], render_report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    raw_components = layout.get("components")
    render_components = render_report.get("components")
    require(isinstance(raw_components, list) and raw_components, "Rig layout has no components")
    require(isinstance(render_components, list) and render_components, "Rig render report has no components")
    masks = {
        str(component.get("name")): component.get("component_mask")
        for component in render_components
        if isinstance(component, dict)
    }
    output: dict[int, dict[str, Any]] = {}
    for index, component in enumerate(raw_components, start=1):
        require(isinstance(component, dict), "Rig component record is malformed")
        name = component.get("name")
        mask = masks.get(str(name))
        require(isinstance(name, str) and isinstance(mask, str),
                f"Rig component {name!r} has no rendered source mask")
        output[index] = {
            "name": name,
            "role": str(component.get("role")),
            "composite_op": str(component.get("composite_op", "ink")),
            "mask": ROOT / mask,
        }
    return output


def export_layer(source: pathlib.Path, composite_op: str, destination: pathlib.Path) -> None:
    mask = Image.open(source).convert("1")
    alpha = mask.convert("L").point(lambda value: 255 if value == 0 else 0)
    color = (255, 255, 255, 255) if composite_op == "erase" else (0, 0, 0, 255)
    output = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    output.paste(Image.new("RGBA", mask.size, color), (0, 0), alpha)
    output.save(destination)


def make_browser_frame(frame: dict[str, Any], components: dict[int, dict[str, Any]]) -> tuple[dict[str, Any], Image.Image]:
    raw_layers = frame.get("layers")
    require(isinstance(raw_layers, list) and raw_layers, "target trace frame has no layers")
    canvas = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    browser_layers: list[dict[str, Any]] = []
    for raw_layer in raw_layers:
        require(isinstance(raw_layer, dict), "target trace layer is malformed")
        component_id = raw_layer.get("component_id")
        require(isinstance(component_id, int) and component_id in components,
                "target trace references an unregistered component")
        component = components[component_id]
        base_x = raw_layer.get("base_x")
        base_y = raw_layer.get("base_y")
        offset_x = raw_layer.get("offset_x")
        offset_y = raw_layer.get("offset_y")
        composite_op = raw_layer.get("composite_op")
        require(all(isinstance(value, int) for value in (base_x, base_y, offset_x, offset_y, composite_op)),
                "target trace layer has non-integer geometry")
        require((component["composite_op"] == "erase") == (composite_op == 1),
                "target trace layer composite operation diverges from source component")
        x = base_x + offset_x
        y = base_y + offset_y
        with Image.open(component["mask"]) as mask_source:
            mask = mask_source.convert("1")
        require(0 <= x <= 200 - mask.width and 0 <= y <= 200 - mask.height,
                f"target trace component leaves canvas: {component['name']}")
        alpha = mask.convert("L").point(lambda value: 255 if value == 0 else 0)
        color = (255, 255, 255, 255) if composite_op == 1 else (0, 0, 0, 255)
        rgba = Image.new("RGBA", mask.size, (0, 0, 0, 0))
        rgba.paste(Image.new("RGBA", mask.size, color), (0, 0), alpha)
        canvas.alpha_composite(rgba, (x, y))
        browser_layers.append({
            "component": component["name"],
            "componentId": component_id,
            "role": component["role"],
            "baseX": base_x,
            "baseY": base_y,
            "offsetX": offset_x,
            "offsetY": offset_y,
            "x": x,
            "y": y,
            "compositeOp": "erase" if composite_op == 1 else "ink",
        })
    state = {
        "scene": frame.get("scene"),
        "emotion": frame.get("emotion"),
        "attention": frame.get("attention"),
        "energy": frame.get("energy"),
        "interactionMemory": frame.get("interaction_memory"),
        "phase": frame.get("phase"),
    }
    require(all(value is not None for value in state.values()), "target trace state is incomplete")
    score_phase = frame.get("score_phase")
    score_step_index = frame.get("score_step_index")
    post_refresh_hold_ms = frame.get("post_refresh_hold_ms")
    require(score_phase is None or isinstance(score_phase, str), "target trace score phase is invalid")
    require(score_step_index is None or isinstance(score_step_index, int),
            "target trace score step is invalid")
    require(isinstance(post_refresh_hold_ms, int) and 750 <= post_refresh_hold_ms <= 5000,
            "target trace post-refresh hold is outside the e-paper-safe range")
    return {
        "index": frame.get("index"),
        "kind": frame.get("kind"),
        "routeIndex": frame.get("route_index"),
        "state": state,
        "scorePhase": score_phase,
        "scoreStepIndex": score_step_index,
        "postRefreshHoldMs": post_refresh_hold_ms,
        "layers": browser_layers,
    }, canvas.convert("RGB")


def write_player(path: pathlib.Path, data: dict[str, Any]) -> None:
    title = "V9 Touch Emotion Machine Preview"
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    template = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>__TITLE__</title><style>
body{{margin:0;background:#f3f3f1;color:#151515;font:14px Arial,sans-serif}}main{{max-width:780px;margin:24px auto;padding:0 18px}}#stage{{position:relative;width:200px;height:200px;background:#fff;border:1px solid #202020;image-rendering:pixelated}}#stage img{{position:absolute;width:auto;height:auto;image-rendering:pixelated}}button{{margin:12px 8px 0 0;padding:7px 10px;border:1px solid #222;background:#fff;color:#111}}#meta{{margin:12px 0;font-family:monospace;white-space:pre-wrap}}
</style></head><body><main><h1>__TITLE__</h1><div id=\"stage\"></div><div id=\"meta\"></div><button id=\"prev\">Previous</button><button id=\"next\">Next</button><button id=\"play\">Play</button></main><script>
const DATA = __DATA__;
const stage=document.getElementById('stage'),meta=document.getElementById('meta');let index=0,timer=null;
function render(){{const frame=DATA.frames[index];stage.replaceChildren();for(const layer of frame.layers){{const img=document.createElement('img');img.src='components/'+layer.component+'.png';img.style.left=layer.x+'px';img.style.top=layer.y+'px';img.style.width='auto';img.style.height='auto';stage.append(img);}}meta.textContent=`${{index+1}}/${{DATA.frames.length}}  ${{frame.kind}}  ${{frame.scorePhase||'route'}}  ${{frame.state.scene}} / ${{frame.state.emotion}} / ${{frame.state.attention}}`;}}
function stop(){{if(timer){{clearTimeout(timer);timer=null;}}document.getElementById('play').textContent='Play';}}
function advance(){{if(index+1>=DATA.frames.length){{stop();return;}}index+=1;render();timer=setTimeout(advance,DATA.frames[index].postRefreshHoldMs);}}
document.getElementById('prev').onclick=()=>{{stop();index=(index+DATA.frames.length-1)%DATA.frames.length;render();}};
document.getElementById('next').onclick=()=>{{stop();index=(index+1)%DATA.frames.length;render();}};
document.getElementById('play').onclick=()=>{{if(timer){{stop();}}else{{if(index+1>=DATA.frames.length){{index=0;render();}}document.getElementById('play').textContent='Pause';timer=setTimeout(advance,DATA.frames[index].postRefreshHoldMs);}}};render();
if(new URLSearchParams(window.location.search).get('autoplay')==='1'){{document.getElementById('play').click();}}
</script></body></html>
"""
    rendered = template.replace("{{", "{").replace("}}", "}")
    path.write_text(rendered.replace("__TITLE__", html.escape(title)).replace("__DATA__", payload),
                    encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=pathlib.Path, default=DEFAULT_TRACE)
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    trace_path = args.trace if args.trace.is_absolute() else ROOT / args.trace
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    report_path = args.write if args.write.is_absolute() else ROOT / args.write
    trace = load_json(trace_path)
    layout = load_json(LAYOUT)
    render_report = load_json(RENDER_REPORT)
    require(trace.get("status") == "PASS_TOUCH_TO_RIG_MACHINE_LOOP_RUNTIME_INACTIVE",
            "touch trace did not pass its runtime-inactive machine loop")
    require(trace.get("source_sha256") == LOCKED_SOURCE_HASH and
            trace.get("runtime_resource_activated") is False,
            "touch trace is not bound to the locked inactive V9 source")
    components = catalog(layout, render_report)
    raw_frames = trace.get("frames")
    require(isinstance(raw_frames, list) and raw_frames, "touch trace has no frames")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    component_dir = artifact_dir / "components"
    component_dir.mkdir(parents=True, exist_ok=True)
    browser_frames: list[dict[str, Any]] = []
    frame_records: list[dict[str, Any]] = []
    used_ids: set[int] = set()
    rendered_images: dict[int, Image.Image] = {}
    for raw_frame in raw_frames:
        require(isinstance(raw_frame, dict), "touch trace frame is malformed")
        browser_frame, image = make_browser_frame(raw_frame, components)
        index = browser_frame.get("index")
        require(isinstance(index, int), "touch trace frame index is invalid")
        image_path = artifact_dir / f"frame-{index:02d}-{browser_frame['kind']}.png"
        image.save(image_path)
        rendered_images[index] = image
        browser_frames.append(browser_frame)
        frame_records.append({"index": index, "kind": browser_frame["kind"], "path": rel(image_path),
                              "sha256": sha256(image_path)})
        for layer in browser_frame["layers"]:
            used_ids.add(int(layer["componentId"]))
    for component_id in sorted(used_ids):
        component = components[component_id]
        export_layer(component["mask"], component["composite_op"], component_dir / f"{component['name']}.png")
    browser_data = {
        "schema": "companion.v9_rig_touch_emotion_browser_trace.v1",
        "sourceTraceSha256": sha256(trace_path),
        "runtimeResourceActivated": False,
        "frames": browser_frames,
    }
    player_path = artifact_dir / "touch-emotion-component-player.html"
    write_player(player_path, browser_data)
    require(DAILY_RIGHT_STATIC_BASELINE.is_file(), "Accepted Daily static baseline is missing")
    baseline = Image.open(DAILY_RIGHT_STATIC_BASELINE).convert("1")
    native_static_differences: list[dict[str, int]] = []
    for index in (0, 7):
        candidate = rendered_images.get(index)
        require(candidate is not None, f"Touch preview is missing static-composition frame {index}")
        difference = sum(
            left != right
            for left, right in zip(candidate.convert("1").getdata(), baseline.getdata())
        )
        native_static_differences.append({"frame_index": index, "different_pixels": difference})
        require(difference == 0,
                f"Touch preview frame {index} no longer reconstructs the accepted Daily static baseline")
    report = {
        "schema": "companion.v9_rig_touch_emotion_machine_preview.v1",
        "status": "PASS_BROWSER_COMPONENT_PREVIEW_FROM_TARGET_TRACE",
        "claim_scope": "browser_component_preview_from_runtime_inactive_target_trace_not_firmware_flash_or_panel_acceptance",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "target_trace": {"path": rel(trace_path), "sha256": sha256(trace_path)},
        "browser_player": {"path": rel(player_path), "sha256": sha256(player_path)},
        "browser_trace": browser_data,
        "frames": frame_records,
        "component_layer_dir": rel(component_dir),
        "component_layer_count": len(used_ids),
        "native_static_composition": {
            "baseline": {"path": rel(DAILY_RIGHT_STATIC_BASELINE), "sha256": sha256(DAILY_RIGHT_STATIC_BASELINE)},
            "frame_differences": native_static_differences,
        },
        "forbidden_runtime_paths": trace.get("forbidden_runtime_paths"),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: rendered {len(browser_frames)} touch/emotion browser component frames -> {rel(report_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
