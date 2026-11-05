#!/usr/bin/env python3
"""Render one V36 directional gaze as a deterministic V9 component-only player."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
V36_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v36-directional-eye-gaze-source"
V9_LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_IDLE = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
V9_COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
CANVAS = (200, 200)
EYES = {
    "left": {"body_asset": "left_eye_body", "base": (42, 112)},
    "right": {"body_asset": "right_eye_body", "base": (125, 112)},
}
STATIC_LAYERS = (
    ("star", (96, 31)),
    ("left_brow", (47, 85)),
    ("right_brow", (132, 85)),
    ("left_eye_body", (42, 112)),
    ("right_eye_body", (125, 112)),
    ("left_cheek", (33, 160)),
    ("right_cheek", (154, 160)),
    ("nose", (94, 148)),
    ("mouth", (86, 160)),
)
EXPECTED_PHASES = ("rest", "eyes_lower_1", "eyes_lower_2", "down_hold", "eyes_return", "rest_dwell")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_mask(path: pathlib.Path) -> Image.Image:
    return Image.open(path).convert("1")


def ink(mask: Image.Image) -> Image.Image:
    return mask.point(lambda value: 255 if value == 0 else 0)


def paste(canvas: Image.Image, mask: Image.Image, position: tuple[int, int], color: str) -> None:
    canvas.paste(255 if color == "white" else 0, position, ink(mask))


def rgba_component(mask: Image.Image, color: str) -> Image.Image:
    output = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    pixels = output.load()
    source = mask.load()
    rgb = (255, 255, 255) if color == "white" else (0, 0, 0)
    for y in range(mask.height):
        for x in range(mask.width):
            if source[x, y] == 0:
                pixels[x, y] = (*rgb, 255)
    return output


def component_assets(export_root: pathlib.Path) -> dict[str, dict[str, object]]:
    paths = {
        "star": (V9_COMPONENTS / "charm_star.pbm", "black"),
        "left_brow": (V9_COMPONENTS / "left_brow_open.pbm", "black"),
        "right_brow": (V9_COMPONENTS / "right_brow_open.pbm", "black"),
        "left_eye_body": (V9_COMPONENTS / "left_eye_open.pbm", "black"),
        "right_eye_body": (V9_COMPONENTS / "right_eye_open.pbm", "black"),
        "left_cheek": (V9_COMPONENTS / "left_cheek_default.pbm", "black"),
        "right_cheek": (V9_COMPONENTS / "right_cheek_default.pbm", "black"),
        "nose": (V9_COMPONENTS / "nose_default.pbm", "black"),
        "mouth": (V9_COMPONENTS / "mouth_default.pbm", "black"),
        "v9_left_primary": (V9_COMPONENTS / "left_eye_highlight_open.pbm", "white"),
        "v9_left_sparkle": (V9_COMPONENTS / "left_eye_sparkle_open.pbm", "white"),
        "v9_right_primary": (V9_COMPONENTS / "right_eye_highlight_open.pbm", "white"),
        "v9_right_sparkle": (V9_COMPONENTS / "right_eye_sparkle_open.pbm", "white"),
        "down_left_primary": (export_root / "components/v36_down_left_primary.pbm", "white"),
        "down_left_sparkle": (export_root / "components/v36_down_left_sparkle.pbm", "white"),
        "down_right_primary": (export_root / "components/v36_down_right_primary.pbm", "white"),
        "down_right_sparkle": (export_root / "components/v36_down_right_sparkle.pbm", "white"),
    }
    assets: dict[str, dict[str, object]] = {}
    for name, (path, color) in paths.items():
        require(path.is_file(), f"missing component {path}")
        mask = load_mask(path)
        preview = export_root / "preview/components" / f"{name}.png"
        preview.parent.mkdir(parents=True, exist_ok=True)
        rgba_component(mask, color).save(preview)
        assets[name] = {
            "source_mask": rel(path),
            "source_sha256": sha256(path),
            "color": color,
            "width": mask.width,
            "height": mask.height,
            "preview_png": rel(preview),
            "preview_png_sha256": sha256(preview),
            "data_uri": "data:image/png;base64," + base64.b64encode(preview.read_bytes()).decode("ascii"),
        }
    return assets


def layer(name: str, position: tuple[int, int]) -> dict[str, object]:
    return {"asset": name, "position": list(position)}


def static_layers() -> list[dict[str, object]]:
    return [layer(name, position) for name, position in STATIC_LAYERS]


def reflection_layers(variant: str, vertical_offset: int = 0) -> list[dict[str, object]]:
    require(variant in {"v9", "down"}, f"unknown reflection variant {variant}")
    result: list[dict[str, object]] = []
    for eye, spec in EYES.items():
        base_x, base_y = tuple(spec["base"])
        prefix = "v9" if variant == "v9" else "down"
        result.extend((
            layer(f"{prefix}_{eye}_primary", (base_x, base_y + vertical_offset)),
            layer(f"{prefix}_{eye}_sparkle", (base_x, base_y + vertical_offset)),
        ))
    return result


def require_reflections_inside_v9_bodies(assets: dict[str, dict[str, object]], story: list[dict[str, object]]) -> None:
    for step in story:
        for eye, spec in EYES.items():
            body = load_mask(ROOT / str(assets[str(spec["body_asset"])]["source_mask"]))
            base_x, base_y = tuple(spec["base"])
            for current in step["layers"]:
                name = str(current["asset"])
                if not name.endswith(f"_{eye}_primary") and not name.endswith(f"_{eye}_sparkle"):
                    continue
                position = tuple(current["position"])
                offset_x, offset_y = position[0] - base_x, position[1] - base_y
                reflection = load_mask(ROOT / str(assets[name]["source_mask"]))
                for y in range(reflection.height):
                    for x in range(reflection.width):
                        if reflection.getpixel((x, y)) != 0:
                            continue
                        target_x, target_y = x + offset_x, y + offset_y
                        require(0 <= target_x < body.width and 0 <= target_y < body.height and
                                body.getpixel((target_x, target_y)) == 0,
                                f"{step['phase']}/{name}: reflection exits locked V9 eye body")


def choreography() -> list[dict[str, object]]:
    base = static_layers()
    return [
        {"phase": "rest", "duration_ms": 2200, "reason": "daily_relaxed_baseline",
         "layers": base + reflection_layers("v9")},
        {"phase": "eyes_lower_1", "duration_ms": 140, "reason": "attention_gaze_lead",
         "layers": base + reflection_layers("v9", 4)},
        {"phase": "eyes_lower_2", "duration_ms": 160, "reason": "attention_gaze_track",
         "layers": base + reflection_layers("v9", 8)},
        {"phase": "down_hold", "duration_ms": 900, "reason": "selected_down_source_endpoint",
         "layers": base + reflection_layers("down")},
        {"phase": "eyes_return", "duration_ms": 180, "reason": "attention_release",
         "layers": base + reflection_layers("v9", 4)},
        {"phase": "rest_dwell", "duration_ms": 3000, "reason": "exact_v9_daily_return",
         "layers": base + reflection_layers("v9")},
    ]


def compose(assets: dict[str, dict[str, object]], layers: list[dict[str, object]]) -> Image.Image:
    canvas = Image.new("1", CANVAS, 255)
    for current in layers:
        asset = assets[str(current["asset"])]
        source = load_mask(ROOT / str(asset["source_mask"]))
        paste(canvas, source, tuple(current["position"]), str(asset["color"]))
    return canvas


def html_document(data: dict[str, object]) -> str:
    serialized = json.dumps(data, separators=(",", ":"))
    return f"""<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>V36 Daily Down Rig Preview</title>
<style>
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:#f4f4f1; color:#151515; font-family:Arial,sans-serif; }}
main {{ display:grid; gap:12px; justify-items:center; padding:24px; }}
canvas {{ width:min(78vw,400px); height:min(78vw,400px); image-rendering:pixelated; background:#fff; border:1px solid #151515; }}
#phase {{ min-height:1.2em; font:14px/1.2 monospace; }}
</style>
<main><canvas width=\"200\" height=\"200\" aria-label=\"V36 Daily down component choreography\"></canvas><div id=\"phase\"></div></main>
<script>
const DATA={serialized};
const canvas=document.querySelector('canvas'); const ctx=canvas.getContext('2d'); ctx.imageSmoothingEnabled=false;
const phase=document.querySelector('#phase'); const images={{}};
for (const [name,asset] of Object.entries(DATA.assets)) {{ const image=new Image(); image.src=asset.data_uri; images[name]=image; }}
function draw(step) {{ ctx.fillStyle='#fff'; ctx.fillRect(0,0,200,200); for (const current of step.layers) {{ const asset=DATA.assets[current.asset]; ctx.drawImage(images[current.asset],current.position[0],current.position[1]); }} phase.textContent=step.phase; }}
Promise.all(Object.values(images).map(image=>image.decode().catch(()=>undefined))).then(()=>{{ let index=0; function advance() {{ const step=DATA.story[index]; draw(step); index=(index+1)%DATA.story.length; window.setTimeout(advance,step.duration_ms); }} advance(); }});
</script></html>
"""


def render(direction: str, export_root: pathlib.Path, source_gate_path: pathlib.Path,
           output: pathlib.Path, report_path: pathlib.Path) -> dict[str, object]:
    require(direction == "down", "only the recorded V36 Daily-down attempt is supported")
    source_gate = json.loads(source_gate_path.read_text(encoding="ascii"))
    require(source_gate.get("status") == "PASS_V36_DIRECTIONAL_REFLECTION_SOURCE_GATE", "source gate is not PASS")
    require(source_gate.get("direction") == direction, "source gate direction does not match")
    require(source_gate.get("runtime_resource_activated") is False and
            source_gate.get("active_candidate_binding") == "forbidden", "candidate unexpectedly activated")
    require(sha256(V9_LOCKED) == V9_LOCKED_SHA256, "locked V9 source hash changed")
    assets = component_assets(export_root)
    story = choreography()
    require(tuple(step["phase"] for step in story) == EXPECTED_PHASES, "unexpected gaze choreography")
    require_reflections_inside_v9_bodies(assets, story)
    frames: list[dict[str, object]] = []
    for index, step in enumerate(story):
        frame = compose(assets, step["layers"])
        frame_path = output / "frames" / f"{index:02d}-{step['phase']}-200x200.png"
        pbm_path = output / "pbm" / f"{index:02d}-{step['phase']}-200x200.pbm"
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        pbm_path.parent.mkdir(parents=True, exist_ok=True)
        frame.save(frame_path)
        frame.save(pbm_path)
        frames.append({"phase": step["phase"], "duration_ms": step["duration_ms"], "reason": step["reason"],
                       "path": rel(frame_path), "sha256": sha256(frame_path),
                       "target_pbm": rel(pbm_path), "target_pbm_sha256": sha256(pbm_path),
                       "layers": step["layers"]})
    data = {
        "schema": "companion.v36_directional_reflection_browser_player.v1",
        "status": "PASS_COMPONENT_ONLY_DIRECTIONAL_PREVIEW_PLAN",
        "direction": direction,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "source_gate": rel(source_gate_path), "source_gate_sha256": sha256(source_gate_path),
        "canvas": {"width": 200, "height": 200},
        "component_only": True, "full_face_cards": False, "random_motion": False,
        "assets": assets, "story": story, "frame_replay": frames,
    }
    output.mkdir(parents=True, exist_ok=True)
    data_path = output / f"daily-{direction}-reflection-player-data.json"
    data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    player_path = output / f"daily-{direction}-reflection-player.html"
    player_path.write_text(html_document(data) + "\n", encoding="ascii")
    report = {
        "schema": "companion.v36_directional_reflection_browser_preview_gate.v1",
        "status": "PASS_COMPONENT_ONLY_DIRECTIONAL_BROWSER_PREVIEW_GATE",
        "direction": direction,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "source_gate": rel(source_gate_path), "source_gate_sha256": sha256(source_gate_path),
        "player": rel(player_path), "player_sha256": sha256(player_path),
        "data": rel(data_path), "data_sha256": sha256(data_path),
        "canvas": {"width": 200, "height": 200},
        "component_only": True, "full_face_cards": False, "random_motion": False,
        "frame_replay": frames,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=("down",), default="down")
    parser.add_argument("--export-root", type=pathlib.Path,
                        default=V36_ROOT / "candidate/component-export-attempt-09")
    parser.add_argument("--source-gate", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-source-gate-20260720.json")
    parser.add_argument("--output", type=pathlib.Path,
                        default=V36_ROOT / "candidate/component-export-attempt-09/preview")
    parser.add_argument("--report", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-browser-preview-20260720.json")
    args = parser.parse_args()
    try:
        render(args.direction, args.export_root.resolve(), args.source_gate.resolve(), args.output.resolve(), args.report.resolve())
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: V36 Daily-down preview is a deterministic 200x200 V9 component-only gaze choreography.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
