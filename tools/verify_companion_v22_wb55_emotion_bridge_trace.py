#!/usr/bin/env python3
"""Parse one WB55 V22 bridge trace into an observed browser replay timeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_LAYOUT = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/"
    "candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
)
BROWSER_LAYOUT = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/"
    "candidate/component-bridge-attempt-01/component-bridge-layout.json"
)
BUILD_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-demo-build-gate-20260719.json"
TARGET_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-trace-contract-20260719.json"

START_RE = re.compile(
    r"^\[v22-rig-demo\] production=off start bridge=(?P<bridge>\S+) "
    r"source=(?P<source>\S+) target=(?P<target>\S+) event=(?P<event>\S+) "
    r"frames=(?P<frames>\d+) refresh=full_only reverse=disabled playlist=disabled$"
)
FRAME_RE = re.compile(
    r"^\[v22-rig-demo\] bridge=(?P<bridge>\S+) step=(?P<step>\d+) "
    r"cue=(?P<cue>\S+) source_phase=(?P<phase>\S+) "
    r"score_duration_ms=(?P<score>\d+) refresh_elapsed_ms=(?P<refresh>\d+) "
    r"post_refresh_delay_ms=(?P<post>\d+) layers=(?P<layers>\d+) bytes=(?P<bytes>\d+)$"
)
END_RE = re.compile(
    r"^\[v22-rig-demo\] result=pass bridge=(?P<bridge>\S+) "
    r"settled_target=(?P<target>\S+) composed=(?P<composed>\d+) "
    r"rejected_copies=(?P<rejected>\d+) reverse=disabled next_auto_frame=none$"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def bridge_for_edge(edge: int) -> dict[str, Any]:
    layout = load_json(TARGET_LAYOUT)
    bridges = layout.get("bridges")
    if not isinstance(bridges, list) or edge >= len(bridges):
        raise ValueError(f"V22 target layout does not define bridge edge {edge}")
    bridge = bridges[edge]
    if not isinstance(bridge, dict):
        raise ValueError(f"V22 bridge edge {edge} is malformed")
    return bridge


def synthetic_trace(edge: int) -> str:
    bridge = bridge_for_edge(edge)
    frames = bridge.get("frames", [])
    if not isinstance(frames, list):
        raise ValueError("V22 bridge has no frame list")
    lines = [
        "[v22-rig-demo] production=off start "
        f"bridge={bridge['name']} source={bridge['source']} target={bridge['target']} "
        f"event={bridge['event']} frames={len(frames)} refresh=full_only reverse=disabled playlist=disabled"
    ]
    for frame in frames:
        index = int(frame["index"])
        score = int(frame["duration_ms"])
        refresh = 900 + index * 41
        post = max(score - refresh, 0)
        layers = len(frame.get("layers", []))
        lines.append(
            f"[v22-rig-demo] bridge={bridge['name']} step={index} cue={frame['cue']} "
            f"source_phase={frame['source_phase']} score_duration_ms={score} "
            f"refresh_elapsed_ms={refresh} post_refresh_delay_ms={post} "
            f"layers={layers} bytes={10000 + index}"
        )
    lines.append(
        f"[v22-rig-demo] result=pass bridge={bridge['name']} settled_target={bridge['target']} "
        f"composed={len(frames)} rejected_copies=0 reverse=disabled next_auto_frame=none"
    )
    return "\n".join(lines) + "\n"


def parse(trace: str, edge: int, trace_origin: str) -> dict[str, Any]:
    errors: list[str] = []
    bridge = bridge_for_edge(edge)
    frames = bridge.get("frames", [])
    if not isinstance(frames, list):
        raise ValueError("V22 bridge frames are malformed")
    start: dict[str, str] | None = None
    ending: dict[str, str] | None = None
    actual_frames: list[dict[str, int | str]] = []

    for raw_line in trace.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "[v22-rig-demo] result=blocked" in line:
            errors.append("WB55 trace contains a blocked V22 demo result")
            continue
        match = START_RE.fullmatch(line)
        if match is not None:
            if start is not None:
                errors.append("WB55 trace contains more than one V22 start marker")
            start = match.groupdict()
            continue
        match = FRAME_RE.fullmatch(line)
        if match is not None:
            actual_frames.append({
                name: int(value) if name in {"step", "score", "refresh", "post", "layers", "bytes"} else value
                for name, value in match.groupdict().items()
            })
            continue
        match = END_RE.fullmatch(line)
        if match is not None:
            if ending is not None:
                errors.append("WB55 trace contains more than one V22 completion marker")
            ending = match.groupdict()

    if start is None:
        errors.append("WB55 trace is missing the production-off V22 start marker")
    else:
        expected_start = {
            "bridge": bridge.get("name"), "source": bridge.get("source"),
            "target": bridge.get("target"), "event": bridge.get("event"),
        }
        for field, expected in expected_start.items():
            if start.get(field) != expected:
                errors.append(f"WB55 trace {field} is not registered V22 edge {edge}")
        if start.get("frames") != str(len(frames)):
            errors.append("WB55 trace start frame count drifted")
    if ending is None:
        errors.append("WB55 trace is missing the no-reverse V22 completion marker")
    else:
        if ending.get("bridge") != bridge.get("name") or ending.get("target") != bridge.get("target"):
            errors.append("WB55 trace completed a different V22 bridge")
        if ending.get("composed") != str(len(frames)) or ending.get("rejected") != "0":
            errors.append("WB55 trace has an incomplete composition count or rejected source copies")

    replay_steps: list[dict[str, Any]] = []
    if len(actual_frames) != len(frames):
        errors.append("WB55 trace does not contain exactly one frame report for every registered step")
    for expected, actual in zip(frames, actual_frames):
        expected_index = int(expected.get("index", -1))
        if actual["bridge"] != bridge.get("name") or actual["step"] != expected_index:
            errors.append(f"WB55 trace frame {expected_index} has an unexpected bridge or order")
        if actual["cue"] != expected.get("cue") or actual["phase"] != expected.get("source_phase"):
            errors.append(f"WB55 trace frame {expected_index} cue/phase drifted from the V22 profile")
        if actual["score"] != expected.get("duration_ms") or actual["layers"] != len(expected.get("layers", [])):
            errors.append(f"WB55 trace frame {expected_index} score or component layer count drifted")
        if actual["bytes"] < 10000:
            errors.append(f"WB55 trace frame {expected_index} did not report a full-frame transfer")
        if actual["post"] != max(int(actual["score"]) - int(actual["refresh"]), 0):
            errors.append(f"WB55 trace frame {expected_index} has an invalid post-refresh dwell")
        replay_steps.append({
            "index": expected_index,
            "cue": expected.get("cue"),
            "source_phase": expected.get("source_phase"),
            "target_pbm": expected.get("target_pbm"),
            "target_pbm_sha256": expected.get("target_pbm_sha256"),
            "score_duration_ms": int(actual["score"]),
            "observed_refresh_elapsed_ms": int(actual["refresh"]),
            "post_refresh_hold_ms": int(actual["post"]),
            "observed_request_to_next_step_ms": int(actual["refresh"]) + int(actual["post"]),
            "component_layer_count": int(actual["layers"]),
            "transferred_bytes": int(actual["bytes"]),
        })
    for step_index, step in enumerate(replay_steps):
        if step_index + 1 < len(replay_steps):
            step["browser_next_final_frame_visible_delay_ms"] = (
                step["post_refresh_hold_ms"] +
                replay_steps[step_index + 1]["observed_refresh_elapsed_ms"]
            )
        else:
            step["browser_next_final_frame_visible_delay_ms"] = None

    build_gate = load_json(BUILD_GATE)
    target_gate = load_json(TARGET_GATE)
    recovery = load_json(RECOVERY_GATE)
    app_ble = APP_BLE.read_text(encoding="utf-8")
    if build_gate.get("status") != "PASS_V22_EMOTION_SEPARATION_WB55_PRODUCTION_OFF_DEMO_BUILD_GATE":
        errors.append("V22 WB55 build identity gate is not PASS")
    if target_gate.get("status") != "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE":
        errors.append("V22 target Rig gate is not PASS")
    for marker in ("refresh=full_only", "waveform=vendor_cwf1_pending", "next_auto_frame=none"):
        if marker not in app_ble:
            errors.append(f"V22 runtime marker drifted: {marker}")

    return {
        "schema": "companion.v22_emotion_separation_wb55_observed_bridge_trace.v1",
        "status": "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT" if not errors else
                  "FAIL_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT",
        "trace_origin": trace_origin,
        "bridge_edge": edge,
        "bridge": {
            "name": bridge.get("name"), "source": bridge.get("source"),
            "target": bridge.get("target"), "event": bridge.get("event"),
            "frame_count": len(frames),
        },
        "browser_observed_replay_timeline": replay_steps,
        "browser_replay_contract": {
            "component_plan_and_target_pbm": "must use the registered V22 profile frame listed for each step",
            "timing_source": "the initial source baseline is already settled; each next final frame waits for the prior post_refresh_hold_ms plus that next frame observed_refresh_elapsed_ms from this exact WB55 trace",
            "no_waveform_simulation_claim": "CWF1 is required before a browser can claim pixel-level physical waveform equivalence",
        },
        "runtime_resource_activated": False,
        "firmware_flashed": False,
        "panel_observed": False,
        "physical_panel_acceptance": False,
        "recovery_gate_status": recovery.get("status"),
        "cwf1_status": "pending_vendor_matched_package",
        "errors": errors,
    }


def write_browser_replay_html(path: pathlib.Path, result: dict[str, Any]) -> None:
    """Write a non-looping DOM-layer replay paced by one parsed WB55 trace."""
    browser_layout = load_json(BROWSER_LAYOUT)
    bridge_name = result["bridge"]["name"]
    bridge = browser_layout.get("bridges", {}).get(bridge_name)
    components = browser_layout.get("components")
    timeline = result["browser_observed_replay_timeline"]
    if not isinstance(bridge, dict) or not isinstance(components, dict) or not isinstance(timeline, list):
        raise ValueError("V22 browser component layout is incomplete")
    frames = bridge.get("frames")
    if not isinstance(frames, list) or len(frames) != len(timeline):
        raise ValueError("V22 browser component frames do not match the parsed WB55 trace")
    component_layer_directory = pathlib.Path(os.path.relpath(
        BROWSER_LAYOUT.parent / "component-layers", path.parent
    )).as_posix()
    payload = {
        "components": components,
        "bridge": {
            "name": bridge.get("name"),
            "source": bridge.get("source"),
            "target": bridge.get("target"),
            "frames": [{
                "cue": frame.get("cue"),
                "layers": frame.get("layers"),
            } for frame in frames],
        },
        "timeline": [{
            "cue": item.get("cue"),
            "observed_request_to_next_step_ms": item.get("observed_request_to_next_step_ms"),
            "observed_refresh_elapsed_ms": item.get("observed_refresh_elapsed_ms"),
            "post_refresh_hold_ms": item.get("post_refresh_hold_ms"),
            "browser_next_final_frame_visible_delay_ms": item.get(
                "browser_next_final_frame_visible_delay_ms"),
        } for item in timeline],
        "trace_origin": result["trace_origin"],
        "component_layer_directory": component_layer_directory,
        "physical_panel_acceptance": False,
    }
    serialized = json.dumps(payload, separators=(",", ":"))
    page = f"""<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>V22 Observed Bridge Replay</title>
<style>
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; background:#eef0eb; color:#15181a; font-family:Arial,sans-serif; }}
main {{ max-width:1060px; margin:0 auto; padding:24px; }}
header {{ display:flex; align-items:center; justify-content:space-between; gap:16px; border-bottom:1px solid #23272a; padding-bottom:14px; }}
h1 {{ margin:0; font-size:22px; letter-spacing:0; }}
button {{ width:36px; min-height:36px; border:1px solid #23272a; border-radius:3px; background:#fff; color:#15181a; cursor:pointer; font-size:17px; }}
.stage-row {{ display:grid; grid-template-columns:minmax(0,1fr) 260px; gap:24px; padding-top:24px; align-items:start; }}
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
<main><header><h1>V22 Observed Bridge</h1><div><button id=\"play\" title=\"Pause\" aria-label=\"Pause\">&#10074;&#10074;</button><button id=\"restart\" title=\"Restart bridge\" aria-label=\"Restart bridge\">&#8634;</button></div></header>
<section class=\"stage-row\"><div class=\"stage-wrap\"><div id=\"stage\" aria-label=\"Component-composed observed bridge replay\"></div></div><aside class=\"route\"><p class=\"route-name\" id=\"route\"></p><div id=\"phases\"></div></aside></section></main>
<script>
const data={serialized}; const scale=4;
const stage=document.querySelector('#stage'), route=document.querySelector('#route'), phases=document.querySelector('#phases'), play=document.querySelector('#play'), restart=document.querySelector('#restart');
let frameIndex=0, running=true, timer=null;
function clearTimer() {{ if(timer!==null) {{ clearTimeout(timer); timer=null; }} }}
function phaseList(index) {{ route.textContent=data.bridge.source+' to '+data.bridge.target; phases.replaceChildren(); data.timeline.forEach((item,row)=>{{ const node=document.createElement('p'); node.className='phase'+(row===index?' active':''); node.textContent=item.cue.replaceAll('_',' '); phases.append(node); }}); }}
function render(index) {{ const frame=data.bridge.frames[index]; stage.replaceChildren(); frame.layers.forEach(layer=>{{ const spec=data.components[layer.component]; const image=document.createElement('img'); image.src=data.component_layer_directory+'/'+spec.browser_layer; image.width=spec.size[0]*scale; image.height=spec.size[1]*scale; image.style.left=(layer.position[0]*scale)+'px'; image.style.top=(layer.position[1]*scale)+'px'; image.style.zIndex=String(layer.z_index); image.alt=''; stage.append(image); }}); phaseList(index); }}
function step() {{ clearTimer(); render(frameIndex); if(!running) return; if(frameIndex<data.timeline.length-1) {{ const dwell=data.timeline[frameIndex].browser_next_final_frame_visible_delay_ms; frameIndex++; timer=setTimeout(step,dwell); return; }} running=false; play.innerHTML='&#9654;'; play.title='Replay bridge'; play.setAttribute('aria-label',play.title); }}
play.addEventListener('click',()=>{{ running=!running; play.innerHTML=running?'&#10074;&#10074;':'&#9654;'; play.title=running?'Pause':'Replay bridge'; play.setAttribute('aria-label',play.title); if(running) step(); else clearTimer(); }});
restart.addEventListener('click',()=>{{ frameIndex=0; running=true; play.innerHTML='&#10074;&#10074;'; play.title='Pause'; play.setAttribute('aria-label',play.title); step(); }}); step();
</script>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=pathlib.Path)
    parser.add_argument("--edge", type=int, choices=range(10), default=0)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    parser.add_argument("--replay", type=pathlib.Path)
    parser.add_argument("--replay-html", type=pathlib.Path)
    args = parser.parse_args()
    if args.self_test == (args.trace is not None):
        parser.error("choose exactly one of --self-test or --trace")
    try:
        if args.self_test:
            trace = synthetic_trace(args.edge)
            origin = "synthetic_self_test_no_flash_no_panel"
        else:
            trace = args.trace.read_text(encoding="utf-8", errors="replace")
            origin = str(args.trace)
        result = parse(trace, args.edge, origin)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.replay is not None:
        args.replay.parent.mkdir(parents=True, exist_ok=True)
        args.replay.write_text(json.dumps({
            "schema": result["schema"],
            "trace_origin": result["trace_origin"],
            "bridge": result["bridge"],
            "browser_observed_replay_timeline": result["browser_observed_replay_timeline"],
            "browser_replay_contract": result["browser_replay_contract"],
            "physical_panel_acceptance": False,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.replay_html is not None:
        try:
            write_browser_replay_html(args.replay_html, result)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"FAIL: {exc}")
            return 1
    if result["status"] != "PASS_V22_EMOTION_SEPARATION_WB55_TRACE_CONTRACT":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: the V22 WB55 trace preserves every registered component step and exports observed browser replay timing without a panel claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
