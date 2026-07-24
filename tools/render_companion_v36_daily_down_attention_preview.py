#!/usr/bin/env python3
"""Render a component-composed browser preview for the gated V36 Daily-down pose."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
V36_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v36-directional-eye-gaze-source"
EXPORT_ROOT = V36_ROOT / "candidate/component-export-attempt-06"
EXPORT_REPORT = EXPORT_ROOT / "export-report.json"
V9_COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
CANVAS = (200, 200)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_mask(path: pathlib.Path) -> Image.Image:
    return Image.open(path).convert("1")


def rgba_layer(mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    output = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    pixels = output.load()
    source = mask.load()
    for y in range(mask.height):
        for x in range(mask.width):
            if source[x, y] == 0:
                pixels[x, y] = (*color, 255)
    return output


def paste(canvas: Image.Image, mask: Image.Image, position: tuple[int, int], color: int) -> None:
    ink = mask.point(lambda value: 255 if value == 0 else 0)
    canvas.paste(color, position, ink)


def component_path(export_root: pathlib.Path, name: str) -> pathlib.Path:
    return export_root / "components" / name


def build_assets(export_root: pathlib.Path) -> dict[str, dict[str, object]]:
    source_paths = {
        "star": V9_COMPONENTS / "charm_star.pbm",
        "left_brow_v9": V9_COMPONENTS / "left_brow_open.pbm",
        "right_brow_v9": V9_COMPONENTS / "right_brow_open.pbm",
        "left_eye_body": V9_COMPONENTS / "left_eye_open.pbm",
        "right_eye_body": V9_COMPONENTS / "right_eye_open.pbm",
        "left_primary_v9": V9_COMPONENTS / "left_eye_highlight_open.pbm",
        "right_primary_v9": V9_COMPONENTS / "right_eye_highlight_open.pbm",
        "left_sparkle_v9": V9_COMPONENTS / "left_eye_sparkle_open.pbm",
        "right_sparkle_v9": V9_COMPONENTS / "right_eye_sparkle_open.pbm",
        "left_cheek": V9_COMPONENTS / "left_cheek_default.pbm",
        "right_cheek": V9_COMPONENTS / "right_cheek_default.pbm",
        "nose": V9_COMPONENTS / "nose_default.pbm",
        "mouth_v9": V9_COMPONENTS / "mouth_default.pbm",
        "left_brow_down": component_path(export_root, "v36_down_left_brow.pbm"),
        "right_brow_down": component_path(export_root, "v36_down_right_brow.pbm"),
        "left_primary_down": component_path(export_root, "v36_down_left_primary.pbm"),
        "right_primary_down": component_path(export_root, "v36_down_right_primary.pbm"),
        "left_sparkle_down": component_path(export_root, "v36_down_left_sparkle.pbm"),
        "right_sparkle_down": component_path(export_root, "v36_down_right_sparkle.pbm"),
        "mouth_down": component_path(export_root, "v36_down_mouth.pbm"),
    }
    positions = {
        "star": [96, 31],
        "left_brow_v9": [47, 85], "right_brow_v9": [132, 85],
        "left_brow_down": [38, 76], "right_brow_down": [120, 76],
        "left_eye_body": [42, 112], "right_eye_body": [125, 112],
        "left_primary_v9": [42, 112], "right_primary_v9": [125, 112],
        "left_sparkle_v9": [42, 112], "right_sparkle_v9": [125, 112],
        "left_primary_down": [42, 112], "right_primary_down": [125, 112],
        "left_sparkle_down": [42, 112], "right_sparkle_down": [125, 112],
        "left_cheek": [33, 160], "right_cheek": [154, 160],
        "nose": [94, 148], "mouth_v9": [86, 160], "mouth_down": [80, 150],
    }
    assets: dict[str, dict[str, object]] = {}
    for name, path in source_paths.items():
        require(path.is_file(), f"missing component asset {path}")
        mask = load_mask(path)
        is_reflection = "primary" in name or "sparkle" in name
        image = rgba_layer(mask, (255, 255, 255) if is_reflection else (0, 0, 0))
        preview_path = export_root / "preview" / "components" / f"{name}.png"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(preview_path)
        assets[name] = {
            "source_mask": rel(path),
            "source_sha256": sha256(path),
            "preview_png": rel(preview_path),
            "preview_png_sha256": sha256(preview_path),
            "position": positions[name],
            "color": "white" if is_reflection else "black",
            "data_uri": "data:image/png;base64," + base64.b64encode(preview_path.read_bytes()).decode("ascii"),
        }
    return assets


def story() -> list[dict[str, object]]:
    identity = ["star", "left_eye_body", "right_eye_body", "left_cheek", "right_cheek", "nose"]
    rest = identity + ["left_brow_v9", "right_brow_v9", "left_primary_v9", "right_primary_v9",
                       "left_sparkle_v9", "right_sparkle_v9", "mouth_v9"]
    eye_lead = identity + ["left_brow_v9", "right_brow_v9", "left_primary_down", "right_primary_down",
                           "left_sparkle_down", "right_sparkle_down", "mouth_v9"]
    brow_answer = identity + ["left_brow_down", "right_brow_down", "left_primary_down", "right_primary_down",
                              "left_sparkle_down", "right_sparkle_down", "mouth_v9"]
    hold = identity + ["left_brow_down", "right_brow_down", "left_primary_down", "right_primary_down",
                       "left_sparkle_down", "right_sparkle_down", "mouth_down"]
    return [
        {"phase": "entry", "duration_ms": 440, "layers": rest},
        {"phase": "eyes_lead", "duration_ms": 240, "layers": eye_lead},
        {"phase": "brows_answer", "duration_ms": 260, "layers": brow_answer},
        {"phase": "mouth_settles", "duration_ms": 340, "layers": hold},
        {"phase": "hold", "duration_ms": 900, "layers": hold},
        {"phase": "settle", "duration_ms": 240, "layers": rest},
        {"phase": "rest_dwell", "duration_ms": 2600, "layers": rest},
    ]


def compose_frame(assets: dict[str, dict[str, object]], layers: list[str]) -> Image.Image:
    canvas = Image.new("1", CANVAS, 255)
    for name in layers:
        source = ROOT / str(assets[name]["source_mask"])
        color = 255 if assets[name]["color"] == "white" else 0
        paste(canvas, load_mask(source), tuple(assets[name]["position"]), color)
    return canvas


def html_document(data: dict[str, object]) -> str:
    serialized = json.dumps(data, separators=(",", ":"))
    return f"""<!doctype html>
<html lang=\"en\">
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>V36 Daily Down Component Preview</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f4f4f1; color: #151515; font-family: Arial, sans-serif; }}
main {{ display: grid; gap: 12px; justify-items: center; padding: 24px; }}
canvas {{ width: min(78vw, 400px); height: min(78vw, 400px); image-rendering: pixelated; background: #fff; border: 1px solid #151515; }}
#phase {{ min-height: 1.2em; font: 14px/1.2 monospace; }}
</style>
<main>
<canvas width=\"200\" height=\"200\" aria-label=\"V36 Daily down component choreography\"></canvas>
<div id=\"phase\"></div>
</main>
<script>
const DATA={serialized};
const canvas=document.querySelector('canvas'); const ctx=canvas.getContext('2d'); ctx.imageSmoothingEnabled=false;
const phase=document.querySelector('#phase'); const images={{}};
for (const [name, asset] of Object.entries(DATA.assets)) {{ const image=new Image(); image.src=asset.data_uri; images[name]=image; }}
function draw(step) {{ ctx.fillStyle='#fff'; ctx.fillRect(0,0,200,200); for (const layer of step.layers) {{ const asset=DATA.assets[layer]; ctx.drawImage(images[layer], asset.position[0], asset.position[1]); }} phase.textContent=step.phase; }}
let index=0;
function advance() {{ const step=DATA.story[index]; draw(step); index=(index+1)%DATA.story.length; window.setTimeout(advance,step.duration_ms); }}
Promise.all(Object.values(images).map(image => new Promise(resolve => {{ image.onload=resolve; image.onerror=resolve; }}))).then(advance);
</script>
</html>
"""


def render(output: pathlib.Path, report_path: pathlib.Path) -> dict[str, object]:
    export = json.loads(EXPORT_REPORT.read_text(encoding="ascii"))
    require(export.get("status") == "PASS_V36_DAILY_DOWN_ATTENTION_SOURCE_GATE",
            "V36 source gate did not pass")
    assets = build_assets(output)
    steps = story()
    frame_records: list[dict[str, object]] = []
    for index, step in enumerate(steps):
        frame = compose_frame(assets, list(step["layers"]))
        path = output / "preview" / "pbm" / f"{index:02d}-{step['phase']}.pbm"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.save(path)
        frame_records.append({"phase": step["phase"], "duration_ms": step["duration_ms"],
                              "path": rel(path), "sha256": sha256(path), "layers": step["layers"]})
    data = {
        "schema": "companion.v36_daily_down_component_browser_preview.v1",
        "status": "PASS_COMPONENT_ONLY_PREVIEW_PLAN",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "source_gate": rel(EXPORT_REPORT),
        "source_gate_sha256": sha256(EXPORT_REPORT),
        "canvas": {"width": 200, "height": 200},
        "component_only": True,
        "full_face_cards": False,
        "random_motion": False,
        "assets": assets,
        "story": steps,
        "frame_replay": frame_records,
    }
    data_path = output / "daily-down-attention-player-data.json"
    data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    html_path = output / "daily-down-attention-player.html"
    html_path.write_text(html_document(data) + "\n", encoding="ascii")
    report = {
        "schema": "companion.v36_daily_down_component_browser_preview_gate.v1",
        "status": "PASS_COMPONENT_ONLY_BROWSER_PREVIEW_GATE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "source_gate": rel(EXPORT_REPORT),
        "source_gate_sha256": sha256(EXPORT_REPORT),
        "player": rel(html_path),
        "player_sha256": sha256(html_path),
        "data": rel(data_path),
        "data_sha256": sha256(data_path),
        "canvas": {"width": 200, "height": 200},
        "component_only": True,
        "full_face_cards": False,
        "random_motion": False,
        "frame_replay": frame_records,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=EXPORT_ROOT)
    parser.add_argument("--report", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-component-browser-preview-20260720.json")
    args = parser.parse_args()
    try:
        render(args.output.resolve(), args.report.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: V36 Daily-down browser preview composes only registered source masks on a 200x200 canvas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
