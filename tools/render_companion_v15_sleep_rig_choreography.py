#!/usr/bin/env python3
"""Render the V15 source-mask sleep choreography without a runtime binding."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
V15_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v15-sleep-rig-pose-source"
DEFAULT_REQUEST = V15_ROOT / "candidate/sleep-v15-component-choreography-request.json"
DEFAULT_OUTPUT = V15_ROOT / "candidate/dynamic-proof-attempt-01"
CANVAS = (200, 200)
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


def validate_owner_acceptance(request: dict[str, object]) -> None:
    if request.get("status") != "OWNER_DYNAMIC_DIRECTION_ACCEPTED_RUNTIME_INACTIVE":
        return
    acceptance = request.get("owner_acceptance")
    if not isinstance(acceptance, dict) or acceptance.get("selected") != "通过" or not isinstance(acceptance.get("exact_note"), str):
        raise ValueError("V15 accepted choreography is missing its canonical owner result")
    for artifact in ("result", "note", "summary"):
        path = ROOT / str(acceptance.get(artifact, ""))
        expected_hash = acceptance.get(f"{artifact}_sha256")
        if not path.is_file() or not isinstance(expected_hash, str) or sha256(path) != expected_hash:
            raise ValueError(f"V15 accepted choreography owner {artifact} drifted")
    result = json.loads((ROOT / str(acceptance["result"])).read_text(encoding="utf-8"))
    summary = json.loads((ROOT / str(acceptance["summary"])).read_text(encoding="utf-8"))
    note = (ROOT / str(acceptance["note"])).read_text(encoding="utf-8").strip()
    if result.get("selected") != "通过" or result.get("text") != acceptance["exact_note"] or note != acceptance["exact_note"] or \
            summary.get("status") != "PASS_OWNER_V15_SLEEP_RIG_V2_REVIEW":
        raise ValueError("V15 accepted choreography owner disposition drifted")


def load_request(path: Path) -> tuple[dict[str, object], dict[str, dict[str, object]], dict[str, list[str]]]:
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict) or request.get("schema") not in {
            "companion.v15_sleep_rig_component_choreography_request.v1",
            "companion.v15_sleep_rig_component_choreography_request.v2",
    }:
        raise ValueError("unsupported V15 choreography request")
    if request.get("status") not in {"CHOREOGRAPHY_VERSIONED_PENDING_MACHINE_PROOF", "MACHINE_DYNAMIC_PROOF_PASS_PENDING_OWNER_REVIEW",
                                      "OWNER_DYNAMIC_DIRECTION_ACCEPTED_RUNTIME_INACTIVE"}:
        raise ValueError("V15 choreography request is not eligible for source-only proof rendering")
    if request.get("runtime_resource_activated") is not False or request.get("active_candidate_binding") != "forbidden" or \
            request.get("crig_mount") != "forbidden" or request.get("full_pose_cell_playback") != "forbidden":
        raise ValueError("V15 choreography request has an illegal runtime disposition")
    validate_owner_acceptance(request)
    if request.get("phase_order") != list(PHASES):
        raise ValueError("V15 choreography phase order drifted")
    layout_path = ROOT / str(request.get("source_layout", ""))
    if not layout_path.is_file() or request.get("source_layout_sha256") != sha256(layout_path):
        raise ValueError("V15 component source layout drifted")
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if not isinstance(layout, dict) or layout.get("schema") != "companion.v15_sleep_rig_component_source_layout.v1" or \
            layout.get("status") != "CANDIDATE_SOURCE_MASK_EXPORT_PENDING_OWNER_ART_REVIEW" or \
            layout.get("runtime_resource_activated") is not False or layout.get("active_candidate_binding") != "forbidden":
        raise ValueError("V15 source layout is not an unbound component candidate")
    rows = layout.get("components")
    if not isinstance(rows, list):
        raise ValueError("V15 source component records are missing")
    components = {str(row.get("name")): row for row in rows if isinstance(row, dict)}
    slots = request.get("component_slots")
    if not isinstance(slots, dict) or not all(isinstance(name, str) and isinstance(values, list) for name, values in slots.items()):
        raise ValueError("V15 component slots are missing")
    slot_map = {str(name): [str(value) for value in values] for name, values in slots.items()}
    component_names = [name for values in slot_map.values() for name in values]
    if len(component_names) != len(set(component_names)) or set(component_names) != set(components):
        raise ValueError("V15 slots do not cover the exact source component vocabulary")
    legal = request.get("component_legal_offsets")
    if not isinstance(legal, dict) or set(legal) != set(components):
        raise ValueError("V15 component offset vocabulary drifted")
    phases = request.get("phases")
    if not isinstance(phases, list) or [step.get("phase") for step in phases if isinstance(step, dict)] != list(PHASES):
        raise ValueError("V15 choreography phase steps drifted")
    return request, components, slot_map


def selected_for(step: dict[str, object], slots: dict[str, list[str]]) -> list[str]:
    selected = step.get("components")
    if not isinstance(selected, dict) or set(selected) != set(slots):
        raise ValueError(f"{step.get('phase')} component slots drifted")
    names: list[str] = []
    for slot, options in slots.items():
        name = selected[slot]
        if name not in options:
            raise ValueError(f"{step.get('phase')} selects an illegal source component for {slot}")
        names.append(str(name))
    return names


def offsets_for(request: dict[str, object], step: dict[str, object], selected: list[str]) -> dict[str, tuple[int, int]]:
    legal = request["component_legal_offsets"]
    raw = step.get("offsets")
    if not isinstance(raw, dict) or not set(raw).issubset(set(selected)):
        raise ValueError(f"{step.get('phase')} offsets must target selected components only")
    offsets: dict[str, tuple[int, int]] = {}
    for name in selected:
        offset = pair(raw.get(name, [0, 0]), f"{step.get('phase')}.{name}")
        limits = legal[name]
        if not isinstance(limits, dict):
            raise ValueError(f"V15 offset limits missing: {name}")
        low, high = pair(limits.get("min"), f"{name}.min"), pair(limits.get("max"), f"{name}.max")
        if not (low[0] <= offset[0] <= high[0] and low[1] <= offset[1] <= high[1]):
            raise ValueError(f"illegal V15 choreography offset: {step.get('phase')}/{name}")
        offsets[name] = offset
    return offsets


def timeline_for(request: dict[str, object], slots: dict[str, list[str]]) -> list[dict[str, object]]:
    """Expand V2's seven named phases into source-mask component track samples."""
    config = request.get("component_timeline")
    if config is None:
        return []
    if not isinstance(config, dict) or config.get("mode") != "stepwise_component_tracks" or \
            config.get("playback_mode") not in {"one_shot_then_static", "loop"}:
        raise ValueError("V15 component timeline is missing its source-mask track mode")
    frame_duration = config.get("frame_duration_ms")
    sample_counts = config.get("sample_counts")
    if not isinstance(frame_duration, int) or frame_duration <= 0 or not isinstance(sample_counts, dict) or \
            set(sample_counts) != set(PHASES):
        raise ValueError("V15 component timeline cadence drifted")
    steps = request.get("phases")
    if not isinstance(steps, list):
        raise ValueError("V15 choreography phases are missing")
    previous_offsets: dict[str, tuple[int, int]] = {}
    result: list[dict[str, object]] = []
    frame_index = 0
    for phase_index, raw_step in enumerate(steps):
        if not isinstance(raw_step, dict) or raw_step.get("phase") != PHASES[phase_index]:
            raise ValueError("V15 component timeline phase order drifted")
        phase = PHASES[phase_index]
        sample_count = sample_counts.get(phase)
        if not isinstance(sample_count, int) or sample_count <= 0 or raw_step.get("duration_ms") != sample_count * frame_duration:
            raise ValueError(f"V15 component timeline duration drifted: {phase}")
        selected = selected_for(raw_step, slots)
        endpoint = offsets_for(request, raw_step, selected)
        for sample_index in range(1, sample_count + 1):
            offsets: dict[str, tuple[int, int]] = {}
            for name in selected:
                start = previous_offsets.get(name, (0, 0))
                end = endpoint[name]
                offsets[name] = tuple(round(start[axis] + (end[axis] - start[axis]) * sample_index / sample_count)
                                      for axis in range(2))
            result.append({"frame_index": frame_index, "frame_id": f"{phase}-{sample_index:02d}-of-{sample_count:02d}",
                           "phase": phase, "sample_index": sample_index, "sample_count": sample_count,
                           "duration_ms": frame_duration, "active_components": selected,
                           "offsets": {name: list(value) for name, value in offsets.items()}})
            frame_index += 1
        previous_offsets = endpoint
    return result


def compose(components: dict[str, dict[str, object]], selected: list[str], offsets: dict[str, tuple[int, int]]) -> Image.Image:
    canvas = Image.new("1", CANVAS, 1)
    for name in sorted(selected, key=lambda item: int(components[item]["z_index"])):
        component = components[name]
        mask = Image.open(ROOT / str(component["mask"])).convert("1")
        base = pair(component["base_position"], f"{name}.base_position")
        offset = offsets[name]
        left, top = base[0] + offset[0], base[1] + offset[1]
        if left < 0 or top < 0 or left + mask.width > CANVAS[0] or top + mask.height > CANVAS[1]:
            raise ValueError(f"V15 component leaves the 200x200 canvas: {name}")
        canvas.paste(mask, (left, top))
    return canvas


def component_ink(component: dict[str, object], offset: tuple[int, int]) -> set[tuple[int, int]]:
    mask = Image.open(ROOT / str(component["mask"])).convert("1")
    base = pair(component["base_position"], f"{component.get('name')}.base_position")
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


def write_timeline_contact_sheet(frames: list[tuple[str, Image.Image]], target: Path) -> None:
    columns = 4
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new("RGB", (200 * columns, 224 * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, frame) in enumerate(frames):
        left, top = (index % columns) * 200, (index // columns) * 224
        sheet.paste(frame.convert("RGB"), (left, top))
        draw.text((left + 6, top + 204), label, fill="black")
    sheet.save(target)


def write_dynamic_apng(frames: list[Image.Image], durations: list[int], target: Path, loop_count: int) -> None:
    if not frames or len(frames) != len(durations):
        raise ValueError("V15 dynamic APNG needs one duration for every source-mask frame")
    if loop_count not in {0, 1}:
        raise ValueError("V15 dynamic APNG loop mode drifted")
    prepared = [frame.convert("RGBA") for frame in frames]
    prepared[0].save(target, format="PNG", save_all=True, append_images=prepared[1:], duration=durations, loop=loop_count, disposal=2, blend=0)


def build_preview_html(target: Path, layout: dict[str, object]) -> None:
    components = layout["components"]
    phase_plan = layout["phase_plan"]
    timeline_plan = layout.get("timeline_plan", [])
    playback_mode = layout.get("playback_mode", "loop")
    browser_components = [{"name": item["name"], "src": "../component-export-attempt-01/preview-layers/" + Path(str(item["preview_mask"])).name,
                           "x": item["base_position"][0], "y": item["base_position"][1], "width": item["mask_size"][0],
                           "height": item["mask_size"][1], "z": item["z_index"]}
                          for item in components if isinstance(item, dict)]
    browser_phases = [{"phase": item["phase"], "duration_ms": item["duration_ms"],
                       "active_components": item["active_components"], "offsets": item["offsets"]}
                      for item in phase_plan if isinstance(item, dict)]
    browser_timeline = [{"frame_id": item["frame_id"], "phase": item["phase"], "sample_index": item["sample_index"],
                         "sample_count": item["sample_count"], "duration_ms": item["duration_ms"],
                         "active_components": item["active_components"], "offsets": item["offsets"]}
                        for item in timeline_plan if isinstance(item, dict)]
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>V15 Sleep Component Choreography Proof</title>
<style>
body {{ margin:0; background:#eef0ed; color:#192229; font-family:Arial,sans-serif; }}
main {{ max-width:980px; margin:20px auto; padding:0 18px 28px; display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:18px; align-items:start; }}
#screen {{ position:relative; width:min(100%,620px); aspect-ratio:1; background:#fff; border:1px solid #1d2930; overflow:hidden; image-rendering:pixelated; }}
#screen img {{ position:absolute; image-rendering:pixelated; }}
#panel {{ display:grid; gap:10px; }} button {{ min-height:38px; border:1px solid #1d2930; background:#fff; color:#192229; cursor:pointer; }} button.active {{ background:#dce8e3; font-weight:700; }} #play {{ background:#17272b; color:#fff; }}
#phase {{ min-height:24px; font-weight:700; }}
@media(max-width:720px) {{ main {{ display:flex; flex-direction:column; padding:0 10px 20px; }} #screen {{ width:100%; }} #panel {{ width:100%; grid-template-columns:repeat(2,minmax(0,1fr)); }} #phase {{ grid-column:1/-1; }} }}
</style><main><section id="screen" aria-label="V15 source-mask sleep animation"></section><aside id="panel"><div id="phase"></div><button id="play" type="button">Replay</button><div id="phaseButtons"></div></aside></main>
<script id="component-plan" type="application/json">{json.dumps(browser_components, separators=(",", ":"))}</script>
<script id="phase-plan" type="application/json">{json.dumps(browser_phases, separators=(",", ":"))}</script>
<script id="timeline-plan" type="application/json">{json.dumps(browser_timeline, separators=(",", ":"))}</script>
<script id="playback-mode" type="application/json">{json.dumps(playback_mode)}</script>
<script>
const components=JSON.parse(document.querySelector('#component-plan').textContent); const phases=JSON.parse(document.querySelector('#phase-plan').textContent); const timeline=JSON.parse(document.querySelector('#timeline-plan').textContent); const playbackMode=JSON.parse(document.querySelector('#playback-mode').textContent); const replayPlan=timeline.length?timeline:phases;
const screen=document.querySelector('#screen'), label=document.querySelector('#phase'), buttons=document.querySelector('#phaseButtons'); let timer=0, index=0;
window.__companionSleepV15={{components,phases,timeline:replayPlan,playbackMode}};
function render(step) {{ screen.replaceChildren(); const offsets=step.offsets||{{}}; const active=new Set(step.active_components); for(const item of [...components].sort((a,b)=>a.z-b.z)) {{ if(!active.has(item.name)) continue; const delta=offsets[item.name]||[0,0]; const image=document.createElement('img'); image.src=item.src; image.alt=item.name; image.style.left=`${{(item.x+delta[0])/2}}%`; image.style.top=`${{(item.y+delta[1])/2}}%`; image.style.width=`${{item.width/2}}%`; image.style.height=`${{item.height/2}}%`; image.style.zIndex=item.z; screen.append(image); }} label.textContent=step.frame_id||step.phase; for(const button of buttons.children) button.classList.toggle('active',button.dataset.phase===step.phase); }}
function play(start=0) {{ clearTimeout(timer); index=start; function next() {{ const step=replayPlan[index]; render(step); if(index===replayPlan.length-1 && playbackMode!=="loop") {{ timer=0; return; }} index=(index+1)%replayPlan.length; timer=setTimeout(next,step.duration_ms); }} next(); }}
for(const step of phases) {{ const button=document.createElement('button'); button.type='button'; button.textContent=step.phase; button.dataset.phase=step.phase; button.onclick=()=>{{clearTimeout(timer);const matching=replayPlan.filter(item=>item.phase===step.phase);render(matching[matching.length-1]||step);}}; buttons.append(button); }}
document.querySelector('#play').onclick=()=>play(0); const fixedPhase=new URLSearchParams(location.search).get('phase'); const fixedSteps=replayPlan.filter(step=>step.phase===fixedPhase); if(fixedSteps.length) render(fixedSteps[fixedSteps.length-1]); else play(0);
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
        request, component_map, slots = load_request(request_path)
        output.mkdir(parents=True, exist_ok=True)
        frames_dir = output / "target-frames"
        frames_dir.mkdir(exist_ok=True)
        request_steps = request["phases"]
        assert isinstance(request_steps, list)
        phase_definitions: list[dict[str, object]] = []
        for index, raw_step in enumerate(request_steps):
            if not isinstance(raw_step, dict) or raw_step.get("phase") != PHASES[index] or not isinstance(raw_step.get("duration_ms"), int) or \
                    raw_step.get("primary_group") not in {"rest", "brow", "lower_face"}:
                raise ValueError("V15 choreography phase schema drifted")
            selected = selected_for(raw_step, slots)
            offsets = offsets_for(request, raw_step, selected)
            phase = PHASES[index]
            phase_definitions.append({"index": index, "phase": phase, "duration_ms": raw_step["duration_ms"],
                                      "primary_group": raw_step["primary_group"], "active_components": selected,
                                      "offsets": {name: list(value) for name, value in offsets.items()}})
        timeline_records = timeline_for(request, slots)
        if request.get("schema") == "companion.v15_sleep_rig_component_choreography_request.v2" and not timeline_records:
            raise ValueError("V15 v2 must expand into component-track samples")
        if not timeline_records:
            timeline_records = [{"frame_index": row["index"], "frame_id": row["phase"], "phase": row["phase"],
                                 "sample_index": 1, "sample_count": 1, "duration_ms": row["duration_ms"],
                                 "active_components": row["active_components"], "offsets": row["offsets"]}
                                for row in phase_definitions]
        rendered_timeline: list[tuple[str, Image.Image]] = []
        audit_frames: list[dict[str, object]] = []
        endpoint_records: dict[str, dict[str, object]] = {}
        timeline_has_tracks = request.get("component_timeline") is not None
        for row in timeline_records:
            phase = str(row["phase"])
            selected = [str(name) for name in row["active_components"]]
            offsets = {name: pair(value, f"{phase}.{name}") for name, value in row["offsets"].items()}
            frame = compose(component_map, selected, offsets)
            suffix = f"{int(row['frame_index']):02d}-{row['frame_id']}" if timeline_has_tracks else f"{int(row['frame_index']):02d}-{phase}"
            pbm = frames_dir / f"{suffix}.pbm"
            png = frames_dir / f"{suffix}.png"
            frame.save(pbm)
            frame.convert("L").resize((1000, 1000), Image.Resampling.NEAREST).save(png)
            row["target_pbm"] = relative(pbm)
            row["target_pbm_sha256"] = sha256(pbm)
            row["target_preview"] = relative(png)
            row["target_preview_sha256"] = sha256(png)
            rendered_timeline.append((str(row["frame_id"]), frame))
            ink = {name: component_ink(component_map[name], offsets[name]) for name in selected}
            overlap = sum(len(ink[left] & ink[right]) for position, left in enumerate(selected) for right in selected[position + 1:])
            audit_frames.append({"frame_id": row["frame_id"], "phase": phase, "component_count": len(selected), "overlap_pixels": overlap,
                                 "active_components": selected, "offsets": {name: list(value) for name, value in offsets.items()}})
            if row["sample_index"] == row["sample_count"]:
                endpoint_records[phase] = row
        if set(endpoint_records) != set(PHASES):
            raise ValueError("V15 component timeline is missing a phase endpoint")
        phase_records: list[dict[str, object]] = []
        phase_frames: list[tuple[str, Image.Image]] = []
        for definition in phase_definitions:
            endpoint = endpoint_records[definition["phase"]]
            endpoint_frame = next(frame for label, frame in rendered_timeline if label == endpoint["frame_id"])
            phase_records.append({**definition, "target_pbm": endpoint["target_pbm"], "target_pbm_sha256": endpoint["target_pbm_sha256"],
                                  "target_preview": endpoint["target_preview"], "target_preview_sha256": endpoint["target_preview_sha256"]})
            phase_frames.append((str(definition["phase"]), endpoint_frame))
        contact = output / "sleep-v15-dynamic-contact-sheet.png"
        if timeline_has_tracks:
            write_timeline_contact_sheet(rendered_timeline, contact)
        else:
            write_contact_sheet(phase_frames, contact)
        dynamic_apng = output / "sleep-v15-dynamic-preview.apng"
        playback_mode = str(request.get("component_timeline", {}).get("playback_mode", "loop"))
        write_dynamic_apng([frame for _, frame in rendered_timeline], [int(row["duration_ms"]) for row in timeline_records], dynamic_apng,
                           1 if playback_mode == "one_shot_then_static" else 0)
        audit = {"schema": "companion.v15_sleep_dynamic_component_occlusion_audit.v1",
                 "status": "PASS_ZERO_COMPONENT_OVERLAP" if all(row["overlap_pixels"] == 0 for row in audit_frames) else "FAIL_COMPONENT_OVERLAP",
                 "frame_count": len(audit_frames), "frames": audit_frames}
        audit_path = output / "component-occlusion-audit.json"
        write_json(audit_path, audit)
        if audit["status"] != "PASS_ZERO_COMPONENT_OVERLAP":
            raise ValueError("V15 choreography has component overlap")
        entry = phase_frames[0][1]
        motion = {"schema": "companion.v15_sleep_component_choreography_motion.v1",
                  "entry_pixel_difference": {phase: sum((left ^ right).bit_count() for left, right in zip(entry.tobytes(), frame.tobytes()))
                                             for phase, frame in phase_frames},
                  "timeline_frame_count": len(timeline_records),
                  "unique_target_frame_hashes": len({str(row["target_pbm_sha256"]) for row in timeline_records})}
        motion_path = output / "motion-report.json"
        write_json(motion_path, motion)
        layout_path = ROOT / str(request["source_layout"])
        source_layout = json.loads(layout_path.read_text(encoding="utf-8"))
        layout_status = "CANDIDATE_UNBOUND_OWNER_DIRECTION_ACCEPTED_RUNTIME_INACTIVE" if \
            request.get("status") == "OWNER_DYNAMIC_DIRECTION_ACCEPTED_RUNTIME_INACTIVE" else \
            "CANDIDATE_UNBOUND_DYNAMIC_PROOF_PENDING_OWNER_REVIEW"
        layout = {"schema": "companion.v15_sleep_component_choreography_layout.v1",
                  "status": layout_status,
                  "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "crig_mount": "forbidden",
                  "full_pose_cell_playback": "forbidden", "source_policy": "registered V15 source masks only",
                  "source_request": relative(request_path), "source_request_sha256": sha256(request_path),
                  "source_component_layout": relative(layout_path), "source_component_layout_sha256": sha256(layout_path),
                  "source_image": request["source_image"], "source_image_sha256": request["source_image_sha256"],
                  "profile": {"width": 200, "height": 200, "pixel_format": "mono_1bpp_white_is_one_msb"},
                   "components": source_layout["components"], "component_slots": slots, "phase_plan": phase_records,
                   "timeline_mode": request.get("component_timeline", {}).get("mode", "phase_keyframes"),
                   "playback_mode": playback_mode,
                  "timeline_plan": timeline_records if timeline_has_tracks else [],
                  "artifacts": {"preview": "preview.html", "target_frames": timeline_records,
                                 "key_phase_frames": phase_records,
                                 "contact_sheet": {"path": relative(contact), "sha256": sha256(contact)},
                                 "dynamic_apng": {"path": relative(dynamic_apng), "sha256": sha256(dynamic_apng),
                                                  "frame_count": len(timeline_records),
                                                  "playback_mode": playback_mode,
                                                  "source": "same registered-mask timeline as browser and target PBM"},
                                 "component_occlusion_audit": {"path": relative(audit_path), "sha256": sha256(audit_path), "status": audit["status"]},
                                "motion_report": {"path": relative(motion_path), "sha256": sha256(motion_path)}}}
        layout_output = output / "sleep-v15-component-choreography-layout.json"
        write_json(layout_output, layout)
        build_preview_html(output / "preview.html", layout)
        report = {"schema": "companion.v15_sleep_component_choreography_export.v1", "status": "PASS_V15_UNBOUND_DYNAMIC_PROOF_EXPORT",
                  "layout": relative(layout_output), "layout_sha256": sha256(layout_output), "phase_count": len(phase_records),
                  "timeline_frame_count": len(timeline_records),
                  "component_count": len(component_map), "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
                  "crig_mount": "forbidden", "full_pose_cell_playback": "forbidden"}
        write_json(output / "export-report.json", report)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: rendered V15 source-mask-only sleep component choreography proof.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
