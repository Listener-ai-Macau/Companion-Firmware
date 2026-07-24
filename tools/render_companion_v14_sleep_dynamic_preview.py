#!/usr/bin/env python3
"""Render the V14 source-mask-only sleep choreography without a runtime binding."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
V14_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair"
DEFAULT_REQUEST = V14_ROOT / "candidate/sleep-v14-dynamic-proof-request.json"
DEFAULT_OUTPUT = V14_ROOT / "candidate/dynamic-proof"
CANVAS = (200, 200)
COMPONENTS = (
    "left_brow", "right_brow", "left_closed_eye", "right_closed_eye", "left_cheek", "right_cheek",
    "nose", "mouth", "sleep_breath_dot_left", "sleep_breath_dot_right",
    "sleep_z_small", "sleep_z_medium", "sleep_z_large",
)
PHASES = ("entry", "lead", "response", "accent", "hold", "return", "settle")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="ascii")


def pair(value: object, name: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{name} must be an integer pair")
    return int(value[0]), int(value[1])


def load_request(path: Path) -> tuple[dict[str, object], dict[str, object], dict[str, dict[str, object]]]:
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict) or request.get("schema") != "companion.v14_sleep_zzz_unbound_dynamic_proof_request.v1":
        raise ValueError("unsupported V14 dynamic proof request")
    if request.get("status") not in {"CHOREOGRAPHY_VERSIONED_PENDING_MACHINE_PROOF", "MACHINE_DYNAMIC_PROOF_PASS_PENDING_OWNER_REVIEW"}:
        raise ValueError("V14 dynamic request is not eligible for source-only proof rendering")
    if request.get("runtime_resource_activated") is not False or request.get("active_candidate_binding") != "forbidden" or \
            request.get("crig_mount") != "forbidden" or request.get("full_face_source_card_playback") != "forbidden":
        raise ValueError("V14 dynamic request has an illegal runtime disposition")
    if request.get("phase_order") != list(PHASES):
        raise ValueError("V14 dynamic request phase order drifted")
    source_path = (ROOT / str(request.get("source_layout", ""))).resolve()
    if not source_path.is_file() or request.get("source_layout_sha256") != sha256(source_path):
        raise ValueError("V14 static source layout drifted")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict) or source.get("schema") != "companion.v14_sleep_zzz_component_source_layout.v1" or \
            source.get("runtime_resource_activated") is not False or source.get("active_candidate_binding") != "forbidden":
        raise ValueError("V14 static source is not an unbound component candidate")
    rows = source.get("components")
    if not isinstance(rows, list):
        raise ValueError("V14 static source component records are missing")
    by_name = {str(row.get("name")): row for row in rows if isinstance(row, dict)}
    if tuple(by_name) != COMPONENTS:
        raise ValueError("V14 dynamic proof component vocabulary drifted")
    legal = request.get("component_legal_offsets")
    if not isinstance(legal, dict) or set(legal) != set(COMPONENTS):
        raise ValueError("V14 dynamic legal-offset vocabulary drifted")
    for name in COMPONENTS:
        limits = legal[name]
        if not isinstance(limits, dict):
            raise ValueError(f"V14 dynamic limits missing: {name}")
        low, high = pair(limits.get("min"), f"{name}.min"), pair(limits.get("max"), f"{name}.max")
        if low[0] > high[0] or low[1] > high[1]:
            raise ValueError(f"V14 dynamic limits are inverted: {name}")
    phases = request.get("phases")
    if not isinstance(phases, list) or [step.get("phase") for step in phases if isinstance(step, dict)] != list(PHASES):
        raise ValueError("V14 dynamic phase steps drifted")
    return request, source, by_name


def offsets_for(request: dict[str, object], step: dict[str, object]) -> dict[str, tuple[int, int]]:
    legal = request["component_legal_offsets"]
    raw = step.get("offsets")
    if not isinstance(raw, dict):
        raise ValueError(f"{step.get('phase')} offsets must be an object")
    resolved: dict[str, tuple[int, int]] = {}
    for name in COMPONENTS:
        offset = pair(raw.get(name, [0, 0]), f"{step.get('phase')}.{name}")
        limits = legal[name]
        if not isinstance(limits, dict):
            raise ValueError(f"legal limits missing: {name}")
        low, high = pair(limits.get("min"), f"{name}.min"), pair(limits.get("max"), f"{name}.max")
        if not (low[0] <= offset[0] <= high[0] and low[1] <= offset[1] <= high[1]):
            raise ValueError(f"illegal V14 dynamic offset: {step.get('phase')}/{name}")
        resolved[name] = offset
    return resolved


def compose(component_map: dict[str, dict[str, object]], offsets: dict[str, tuple[int, int]]) -> Image.Image:
    canvas = Image.new("1", CANVAS, 1)
    for name in sorted(COMPONENTS, key=lambda item: int(component_map[item]["z_index"])):
        component = component_map[name]
        mask_path = ROOT / str(component.get("mask", ""))
        base = pair(component.get("base_position"), f"{name}.base_position")
        offset = offsets[name]
        mask = Image.open(mask_path).convert("1")
        x, y = base[0] + offset[0], base[1] + offset[1]
        if x < 0 or y < 0 or x + mask.width > CANVAS[0] or y + mask.height > CANVAS[1]:
            raise ValueError(f"V14 component leaves the 200x200 canvas: {name}")
        canvas.paste(mask, (x, y))
    return canvas


def component_ink(component: dict[str, object], offset: tuple[int, int]) -> set[tuple[int, int]]:
    mask_path = ROOT / str(component.get("mask", ""))
    base = pair(component.get("base_position"), f"{component.get('name')}.base_position")
    mask = Image.open(mask_path).convert("1")
    result: set[tuple[int, int]] = set()
    for y in range(mask.height):
        for x in range(mask.width):
            if mask.getpixel((x, y)) == 0:
                result.add((base[0] + offset[0] + x, base[1] + offset[1] + y))
    return result


def write_contact_sheet(frames: list[tuple[str, Image.Image]], target: Path) -> None:
    sheet = Image.new("RGB", (200 * len(frames), 224), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (phase, frame) in enumerate(frames):
        sheet.paste(frame.convert("RGB"), (index * 200, 0))
        draw.text((index * 200 + 6, 204), phase, fill="black")
    sheet.save(target)


def build_preview_html(target: Path, layout: dict[str, object]) -> None:
    components = layout["components"]
    phases = layout["phase_plan"]
    browser_components = []
    for item in components:
        if not isinstance(item, dict):
            continue
        browser_components.append({
            "name": item["name"], "src": "../preview-layers/" + Path(str(item["preview_mask"])).name,
            "x": item["base_position"][0], "y": item["base_position"][1],
            "width": item["mask_size"][0], "height": item["mask_size"][1], "z": item["z_index"],
        })
    browser_phases = [
        {"phase": item["phase"], "duration_ms": item["duration_ms"],
         "visible_components": item["visible_components"], "offsets": item["offsets"]}
        for item in phases if isinstance(item, dict)
    ]
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>V14 Sleep Source-Mask Dynamic Proof</title>
<style>
body {{ margin:0; background:#eef0ed; color:#192229; font-family:Arial,sans-serif; }}
main {{ max-width:980px; margin:20px auto; padding:0 18px 28px; display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:18px; align-items:start; }}
#screen {{ position:relative; width:min(100%,620px); aspect-ratio:1; background:#fff; border:1px solid #1d2930; overflow:hidden; image-rendering:pixelated; }}
#screen img {{ position:absolute; image-rendering:pixelated; }}
#panel {{ display:grid; gap:10px; }} button {{ min-height:38px; border:1px solid #1d2930; background:#fff; color:#192229; cursor:pointer; }} button.active {{ background:#dce8e3; font-weight:700; }} #play {{ background:#17272b; color:#fff; }}
#phase {{ min-height:24px; font-weight:700; }}
@media(max-width:720px) {{ main {{ display:flex; flex-direction:column; padding:0 10px 20px; }} #screen {{ width:100%; }} #panel {{ width:100%; grid-template-columns:repeat(2,minmax(0,1fr)); }} #phase {{ grid-column:1/-1; }} }}
</style><main><section id="screen" aria-label="V14 source-mask sleep animation"></section><aside id="panel"><div id="phase"></div><button id="play" type="button">Replay</button><div id="phaseButtons"></div></aside></main>
<script id="component-plan" type="application/json">{json.dumps(browser_components, separators=(",", ":"))}</script>
<script id="phase-plan" type="application/json">{json.dumps(browser_phases, separators=(",", ":"))}</script>
<script>
const components=JSON.parse(document.querySelector('#component-plan').textContent); const phases=JSON.parse(document.querySelector('#phase-plan').textContent);
const screen=document.querySelector('#screen'), label=document.querySelector('#phase'), buttons=document.querySelector('#phaseButtons'); let timer=0, index=0;
window.__companionSleepV14={{components,phases}};
function render(step) {{ screen.replaceChildren(); const offsets=step.offsets||{{}}; for(const item of [...components].sort((a,b)=>a.z-b.z)) {{ const delta=offsets[item.name]||[0,0]; const image=document.createElement('img'); image.src=item.src; image.alt=item.name; image.style.left=`${{(item.x+delta[0])/2}}%`; image.style.top=`${{(item.y+delta[1])/2}}%`; image.style.width=`${{item.width/2}}%`; image.style.height=`${{item.height/2}}%`; image.style.zIndex=item.z; screen.append(image); }} label.textContent=step.phase; for(const button of buttons.children) button.classList.toggle('active',button.dataset.phase===step.phase); }}
function play(start=0) {{ clearTimeout(timer); index=start; function next() {{ const step=phases[index]; render(step); index=(index+1)%phases.length; timer=setTimeout(next,step.duration_ms); }} next(); }}
for(const step of phases) {{ const button=document.createElement('button'); button.type='button'; button.textContent=step.phase; button.dataset.phase=step.phase; button.onclick=()=>{{clearTimeout(timer);render(step);}}; buttons.append(button); }}
document.querySelector('#play').onclick=()=>play(0); const fixedPhase=new URLSearchParams(location.search).get('phase'); const fixedIndex=phases.findIndex(step=>step.phase===fixedPhase); if(fixedIndex>=0) render(phases[fixedIndex]); else play(0);
</script></html>"""
    target.write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        request_path = args.request.resolve()
        output = args.output_dir.resolve()
        request, source_layout, component_map = load_request(request_path)
        output.mkdir(parents=True, exist_ok=True)
        frames_dir = output / "target-frames"
        frames_dir.mkdir(exist_ok=True)
        phase_rows = request["phases"]
        assert isinstance(phase_rows, list)
        rendered: list[tuple[str, Image.Image]] = []
        phase_records: list[dict[str, object]] = []
        audit_frames: list[dict[str, object]] = []
        for index, raw_step in enumerate(phase_rows):
            if not isinstance(raw_step, dict) or raw_step.get("phase") != PHASES[index] or \
                    raw_step.get("visible_components") != "all_registered_v14_masks" or \
                    not isinstance(raw_step.get("duration_ms"), int):
                raise ValueError("V14 dynamic phase schema drifted")
            offsets = offsets_for(request, raw_step)
            frame = compose(component_map, offsets)
            phase = PHASES[index]
            pbm = frames_dir / f"{index:02d}-{phase}.pbm"
            png = frames_dir / f"{index:02d}-{phase}.png"
            frame.save(pbm)
            frame.convert("L").resize((1000, 1000), Image.Resampling.NEAREST).save(png)
            rendered.append((phase, frame))
            phase_records.append({"index": index, "phase": phase, "duration_ms": raw_step["duration_ms"],
                                  "visible_components": list(COMPONENTS),
                                  "offsets": {name: list(value) for name, value in offsets.items()},
                                  "target_pbm": relative(pbm), "target_pbm_sha256": sha256(pbm),
                                  "target_preview": relative(png), "target_preview_sha256": sha256(png)})
            ink = {name: component_ink(component_map[name], offsets[name]) for name in COMPONENTS}
            overlap = sum(len(ink[left] & ink[right]) for position, left in enumerate(COMPONENTS) for right in COMPONENTS[position + 1:])
            audit_frames.append({"phase": phase, "component_count": len(ink), "overlap_pixels": overlap,
                                 "offsets": {name: list(value) for name, value in offsets.items()}})
        contact = output / "sleep-v14-dynamic-contact-sheet.png"
        write_contact_sheet(rendered, contact)
        audit = {"schema": "companion.v14_sleep_dynamic_component_occlusion_audit.v1",
                 "status": "PASS_ZERO_COMPONENT_OVERLAP" if all(row["overlap_pixels"] == 0 for row in audit_frames) else "FAIL_COMPONENT_OVERLAP",
                 "frame_count": len(audit_frames), "frames": audit_frames}
        audit_path = output / "component-occlusion-audit.json"
        write_json(audit_path, audit)
        if audit["status"] != "PASS_ZERO_COMPONENT_OVERLAP":
            raise ValueError("V14 dynamic proof has component overlap")
        entry = rendered[0][1]
        motion = {"schema": "companion.v14_sleep_dynamic_motion.v1",
                  "entry_pixel_difference": {phase: sum((a ^ b).bit_count() for a, b in zip(entry.tobytes(), frame.tobytes()))
                                             for phase, frame in rendered},
                  "unique_target_frame_hashes": len({sha256(frames_dir / f"{index:02d}-{phase}.pbm")
                                                      for index, (phase, _) in enumerate(rendered)})}
        motion_path = output / "motion-report.json"
        write_json(motion_path, motion)
        components = []
        legal = request["component_legal_offsets"]
        assert isinstance(legal, dict)
        for name in COMPONENTS:
            source = component_map[name]
            components.append({"name": name, "component_id": source["component_id"], "mask": source["mask"],
                               "mask_sha256": source["mask_sha256"], "preview_mask": source["preview_mask"],
                               "base_position": source["base_position"], "mask_size": source["mask_size"],
                               "z_index": source["z_index"], "source_sheet": source["source_sheet"],
                               "source_sheet_sha256": source["source_sheet_sha256"], "legal_offset": legal[name]})
        layout = {"schema": "companion.v14_sleep_zzz_unbound_dynamic_layout.v1",
                  "status": "CANDIDATE_UNBOUND_DYNAMIC_PROOF_PENDING_OWNER_REVIEW",
                  "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "crig_mount": "forbidden",
                  "full_face_source_card_playback": "forbidden", "source_policy": "registered V14 source masks only",
                  "source_request": relative(request_path), "source_request_sha256": sha256(request_path),
                  "source_static_layout": request["source_layout"], "source_static_layout_sha256": request["source_layout_sha256"],
                  "source_image": request["source_image"], "source_image_sha256": request["source_image_sha256"],
                  "profile": {"width": 200, "height": 200, "pixel_format": "mono_1bpp_white_is_one_msb"},
                  "components": components, "phase_plan": phase_records,
                  "artifacts": {"preview": "preview.html", "target_frames": phase_records,
                                "contact_sheet": {"path": relative(contact), "sha256": sha256(contact)},
                                "component_occlusion_audit": {"path": relative(audit_path), "sha256": sha256(audit_path), "status": audit["status"]},
                                "motion_report": {"path": relative(motion_path), "sha256": sha256(motion_path)}}}
        layout_path = output / "sleep-v14-dynamic-layout.json"
        write_json(layout_path, layout)
        build_preview_html(output / "preview.html", layout)
        report = {"schema": "companion.v14_sleep_zzz_unbound_dynamic_export.v1",
                  "status": "PASS_V14_UNBOUND_DYNAMIC_PROOF_EXPORT", "layout": relative(layout_path),
                  "layout_sha256": sha256(layout_path), "phase_count": len(phase_records), "component_count": len(components),
                  "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "crig_mount": "forbidden",
                  "full_face_source_card_playback": "forbidden"}
        write_json(output / "export-report.json", report)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: rendered V14 source-mask-only seven-phase sleep dynamic proof.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
