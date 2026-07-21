#!/usr/bin/env python3
"""Build the owner-facing vertical V45 review wall from parity-verified frame records."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "docs/validation/companion-v45-complete-eye-browser-wb55-preview-20260721.json"
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/expanded-review-wall-01/index.html"
REPORT = ROOT / "docs/validation/companion-v45-expanded-review-wall-20260721.json"
TOUCH_HTML = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing artifact: {rel(path)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"artifact is not an object: {rel(path)}")
    return value


def load_touch_package() -> dict[str, Any]:
    """Carry the exact parity viewport's registered touch assets into the wall."""
    require(TOUCH_HTML.is_file(), f"missing touch parity viewport: {rel(TOUCH_HTML)}")
    source = TOUCH_HTML.read_text(encoding="utf-8")
    match = re.search(r"const touchData=(\{.*?\});(?:const reviewRevision='[^']+';)?const screen=", source)
    require(match is not None, "V45 touch parity package is not embedded in the source viewport")
    package = json.loads(match.group(1))
    require(package.get("canvas") == "200x200" and package.get("mode") ==
            "single_200x200_viewport_pointer_coordinate_to_registered_offsets" and
            package.get("release_behavior") == "center_then_resume_story",
            "V45 touch parity package is not the registered 200x200 interaction contract")
    return package


def build_artifacts() -> tuple[Path, str, Path, str]:
    preview = load(PREVIEW)
    require(preview.get("status") == "PASS_BROWSER_COMPONENT_PREVIEW_RENDERED_RUNTIME_INACTIVE" and
            preview.get("runtime_resource_activated") is False and
            preview.get("canvas", {}).get("width") == 200 and
            preview.get("canvas", {}).get("height") == 200,
            "V45 source preview is not an inactive 200x200 component preview")
    overview = preview.get("chinese_overview", {})
    visible_scores = overview.get("owner_visible_scores", [])
    metadata = overview.get("metadata", {}).get("stories", {})
    require(isinstance(visible_scores, list) and len(visible_scores) == 16,
            "V45 owner-visible story coverage drifted")
    frames_by_story: dict[str, list[dict[str, Any]]] = {name: [] for name in visible_scores}
    for frame in preview.get("frames", []):
        score = frame.get("score")
        if score in frames_by_story:
            require(isinstance(frame.get("cue"), str) and isinstance(frame.get("phase"), str) and
                    isinstance(frame.get("duration_ms"), int) and frame["duration_ms"] > 0 and
                    isinstance(frame.get("target_1bpp_sha256"), str),
                    f"malformed V45 frame record: {score}")
            png = Path(str(frame.get("png", "")))
            source_png = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01" / png.name
            require(source_png.is_file(), f"V45 frame PNG is missing: {frame.get('png')}")
            frames_by_story[score].append(frame)
    require(all(frames_by_story[name] for name in visible_scores), "expanded wall has an empty story")
    frame_count = sum(len(frames_by_story[name]) for name in visible_scores)
    require(frame_count == 78, "expanded wall frame count drifted")
    touch_package = load_touch_package()
    require(len(touch_package.get("overlays", {})) == 280 and
            len(touch_package.get("bases", {})) == 16,
            "V45 expanded wall lost the registered touch overlay/base package")

    wall_frames: dict[str, list[dict[str, Any]]] = {}
    report_stories: list[dict[str, Any]] = []
    for name in visible_scores:
        wall_frames[name] = []
        report_frames: list[dict[str, Any]] = []
        for index, frame in enumerate(frames_by_story[name]):
            source_png = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01" / str(frame["png"])
            filename = source_png.name
            wall_frames[name].append({
                "src": Path("../wb55-browser-parity-attempt-01").joinpath(filename).as_posix(),
                "touch_base": Path("../wb55-browser-parity-attempt-01").joinpath(
                    str(touch_package["bases"][name][str(index)])).as_posix(),
                "cue": frame["cue"],
                "phase": frame["phase"],
                "duration_ms": frame["duration_ms"],
                "target_1bpp_sha256": frame["target_1bpp_sha256"],
            })
            report_frames.append({"index": index, "src": filename, "cue": frame["cue"],
                                  "phase": frame["phase"], "duration_ms": frame["duration_ms"],
                                  "target_1bpp_sha256": frame["target_1bpp_sha256"]})
        story = metadata.get(name, {})
        report_stories.append({"name": name, "label_zh": story.get("label_zh", name),
                               "summary_zh": story.get("summary_zh", ""), "frames": report_frames})
    cards: list[str] = []
    for name in visible_scores:
        story = metadata.get(name, {})
        label = html.escape(str(story.get("label_zh", name)))
        summary = html.escape(str(story.get("summary_zh", "")))
        cards.append(
            f'<article class="story" data-story="{html.escape(name)}">'
            f'<header><h2>{label}</h2><p>{summary}</p></header>'
            f'<div class="epaper-screen" data-review-revision="v45-touch-failsafe-r7" data-cache-review="v45-touch-failsafe-r7-20260721" data-canvas="200x200" data-touch-surface="true" role="application" aria-label="{label}">'
            f'<img class="frame" draggable="false" width="200" height="200" alt="{label}">'
            f'<img class="frame-staging" draggable="false" width="200" height="200" alt="" hidden aria-hidden="true">'
            f'<img class="gaze" draggable="false" width="200" height="200" alt="" hidden>'
            f'</div><p class="status" aria-live="polite"></p></article>'
        )
    data = json.dumps(wall_frames, ensure_ascii=False, separators=(",", ":"))
    touch_data = json.dumps({"overlays": {
        key: Path("../wb55-browser-parity-attempt-01").joinpath(str(value)).as_posix()
        for key, value in touch_package["overlays"].items()},
        "center_key": touch_package["center_key"]}, ensure_ascii=False, separators=(",", ":"))
    title = "V45 组件表情系统·完整展开验收"
    html_text = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
.epaper-screen img{{pointer-events:none;user-select:none;-webkit-user-drag:none}}
:root{{color-scheme:light;background:#f3f3f1;color:#161616;font-family:"Microsoft YaHei UI",system-ui,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;padding:28px 24px 64px;background:#f3f3f1}}
main{{max-width:720px;margin:0 auto}}h1{{font-size:28px;margin:0 0 8px}}.intro{{margin:0 0 24px;color:#4b4b4b}}
#wall{{display:grid;grid-template-columns:1fr;gap:18px;align-items:start}}
.story{{background:#fff;border:1px solid #888;padding:14px;min-width:0}}
.story header{{min-height:76px}}h2{{font-size:18px;margin:0 0 5px}}.story header p{{font-size:13px;line-height:1.5;margin:0;color:#555}}
.epaper-screen{{position:relative;width:200px;height:200px;margin:12px auto 10px;background:#fff;border:1px solid #333;overflow:hidden;touch-action:none;cursor:crosshair}}
.frame,.frame-staging,.gaze{{position:absolute;inset:0;display:block;width:200px;height:200px;image-rendering:pixelated;image-rendering:crisp-edges;pointer-events:none;user-select:none;-webkit-user-drag:none}}.frame,.frame-staging{{background:#fff}}.gaze{{background:transparent}}
.gaze[hidden]{{display:none}}
.status{{font:12px ui-monospace,SFMono-Regular,Consolas,monospace;color:#333;margin:0;min-height:18px;text-align:center}}
@media (max-width:620px){{body{{padding:18px 12px 40px}}}}
</style></head><body><main data-renderer="registered-200x200-component-frames"><h1>{title}</h1>
<p class="intro">Touch fail-safe r7 · v45-touch-failsafe-r7-20260721 · 16 个真实 200x200 动态视口从上到下展开；按下只改变当前情绪的眼神高光/小星光，不触发眨眼或切换故事。</p>
<section id="wall" aria-label="全部动态故事">{''.join(cards)}</section></main>
<script>
const wallData={data};const touchData={touch_data};const reviewRevision='v45-touch-failsafe-r7-20260721';
function touchPoint(stage,event){{const rect=stage.getBoundingClientRect();return {{x:Math.max(0,Math.min(199,Math.round((event.clientX-rect.left)/rect.width*199))),y:Math.max(0,Math.min(199,Math.round((event.clientY-rect.top)/rect.height*199)))}};}}
function touchTarget(point){{const x=point.x,y=point.y;function axis(value,negative,positive,center){{if(value<=100)return center+Math.round((value-100)*(center-negative)/100);return center+Math.round((value-100)*(positive-center)/99);}}return {{primary_x:axis(x,-2,5,1),primary_y:axis(y,-3,4,0),sparkle_x:axis(x,-6,5,1),sparkle_y:axis(y,-6,6,0)}};}}
function targetKey(target){{return [target.primary_x,target.primary_y,target.sparkle_x,target.sparkle_y].join(',');}}
for(const card of document.querySelectorAll('.story')){{
  const frames=wallData[card.dataset.story]||[];const stage=card.querySelector('.epaper-screen');const image=card.querySelector('.frame');const staging=card.querySelector('.frame-staging');const gaze=card.querySelector('.gaze');const status=card.querySelector('.status');
  const state={{index:0,timer:0,touching:false,mouseDown:false,renderRequest:0,gazeRequest:0,activeFrame:null,activeFrameIndex:-1,activeBaseSrc:'',activeFrameStartedAt:0,activeFrameDurationMs:0,pausedRemainingMs:0}};
  const trace=[];function record(kind,extra){{const item=Object.assign({{kind:kind,t_ms:Math.round(performance.now()),story_index:state.storyIndex||0,active_frame_index:state.activeFrameIndex,active_frame_cue:state.activeFrame?state.activeFrame.cue:null}},extra||{{}});trace.push(item);if(trace.length>240)trace.shift();stage.dataset.activeFrameCue=state.activeFrame?state.activeFrame.cue:'';stage.dataset.storyIndex=String(state.storyIndex||0);}}function debugState(){{return{{revision:reviewRevision,page_review:new URLSearchParams(window.location.search).get('review'),story_index:state.storyIndex||0,next_frame_index:state.index,active_frame_index:state.activeFrameIndex,active_frame_cue:state.activeFrame?state.activeFrame.cue:null,active_base_src:state.activeBaseSrc,touching:state.touching,remaining_ms:Math.max(0,Math.round(state.pausedRemainingMs)),gaze_hidden:gaze.hidden,render_request:state.renderRequest}}}}stage.__v45TouchState=debugState;stage.__v45TouchTrace=trace;if(!window.__v45TouchState){{window.__v45TouchState=debugState;window.__v45TouchTrace=trace;}}function cached(src){{return src+(src.indexOf('?')>=0?'&':'?')+'review='+encodeURIComponent(reviewRevision);}}
  function waitPaint(){{return new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));}}
  const touchCache=new Map();
  function waitForImage(node){{if(node.complete)return Promise.resolve(node.naturalWidth>0);return new Promise(resolve=>{{node.addEventListener('load',()=>resolve(true),{{once:true}});node.addEventListener('error',()=>resolve(false),{{once:true}});}});}}
  async function decodeImage(node){{if(!node||!node.complete||node.naturalWidth<=0)return false;if(typeof node.decode==='function'){{try{{await node.decode();}}catch{{return false;}}}}return node.complete&&node.naturalWidth>0;}}
  function loadAsset(src){{if(!src)return Promise.resolve(false);let ready=touchCache.get(src);if(!ready){{const asset=new Image();ready=new Promise(resolve=>{{asset.addEventListener('load',()=>resolve(true),{{once:true}});asset.addEventListener('error',()=>resolve(false),{{once:true}});asset.src=cached(src);}}).then(ok=>ok?decodeImage(asset):false);touchCache.set(src,ready);}}return ready;}}
  async function presentBase(src,request){{if(!src||request!==state.renderRequest)return false;if(state.activeBaseSrc===src&&!image.hidden&&await decodeImage(image))return true;const url=cached(src);staging.hidden=true;staging.src=url;if(!await waitForImage(staging)||!await decodeImage(staging)){{record('base_load_failed',{{src:src}});return false;}}if(request!==state.renderRequest)return false;image.src=url;image.hidden=false;state.activeBaseSrc=src;record('base_presented',{{src:src}});return true;}}
  function showGaze(overlay,label,mode){{const request=++state.gazeRequest;gaze.hidden=true;if(label&&state.activeFrame)status.textContent=label;if(!overlay){{record('gaze_fail_closed',{{mode:mode}});return;}}loadAsset(overlay).then(async ok=>{{if(!ok||request!==state.gazeRequest){{if(!ok)record('gaze_fail_closed',{{mode:mode}});return;}}gaze.src=cached(overlay);if(await decodeImage(gaze)&&request===state.gazeRequest&&(mode==='idle'||mode==='touch'||mode==='release')){{gaze.hidden=false;await waitPaint();if(request===state.gazeRequest){{record('gaze_presented',{{mode:mode,overlay:overlay}});}}else{{gaze.hidden=true;}}}}else{{gaze.hidden=true;record('gaze_fail_closed',{{mode:mode}});}}}});}}
  function show(frame,extra){{const request=++state.renderRequest;state.gazeRequest++;gaze.hidden=true;const baseSrc=frame.touch_base||frame.src;presentBase(baseSrc,request).then(ok=>{{if(!ok||state.touching||request!==state.renderRequest)return;state.activeFrame=frame;state.activeFrameIndex=state.index;state.index=(state.index+1)%frames.length;state.activeFrameStartedAt=performance.now();state.activeFrameDurationMs=frame.duration_ms;state.pausedRemainingMs=frame.duration_ms;status.textContent=extra||frame.phase+' / '+frame.cue+' / '+frame.duration_ms+' ms';record('frame_presented',{{cue:frame.cue,phase:frame.phase,duration_ms:frame.duration_ms}});showGaze(touchData.overlays[touchData.center_key],null,'idle');state.timer=window.setTimeout(play,frame.duration_ms);}});}}
  function play(){{if(state.touching||!frames.length)return;show(frames[state.index%frames.length]);}}
  function showTouch(frame,baseSrc,overlay,label,mode){{if(!frame||!baseSrc)return;status.textContent=label;showGaze(overlay,label,mode||'touch');}}
  function follow(event){{const point=touchPoint(stage,event);state.lastPoint=point;const target=touchTarget(point),key=targetKey(target);const frame=state.activeFrame;const baseSrc=state.activeBaseSrc;const overlay=touchData.overlays[key];if(!frame||!baseSrc)return;showTouch(frame,baseSrc,overlay,frame.phase+' / 触摸注视 ('+point.x+','+point.y+')','touch');}}
  function pauseCurrentFrame(){{window.clearTimeout(state.timer);if(state.activeFrame)state.pausedRemainingMs=Math.max(0,Math.round(state.activeFrameDurationMs-(performance.now()-state.activeFrameStartedAt)));record('touch_pause',{{remaining_ms:state.pausedRemainingMs}});}}
  function release(event){{if(!state.touching)return;state.touching=false;const end=event?touchPoint(stage,event):(state.lastPoint||state.startPoint);const start=state.startPoint||end;const dx=end.x-start.x,dy=end.y-start.y;state.startPoint=null;state.lastPoint=null;if(Math.max(Math.abs(dx),Math.abs(dy))>=24){{const horizontal=Math.abs(dx)>=Math.abs(dy);const direction=horizontal?(dx>0?1:-1):(dy>0?1:-1);const sibling=direction>0?card.nextElementSibling:card.previousElementSibling;gaze.hidden=true;if(sibling&&sibling.classList.contains('story')){{sibling.scrollIntoView({{behavior:'smooth',block:'center'}});sibling.querySelector('.status').textContent='滑动 / '+(direction>0?'下一故事':'上一故事');}}else{{status.textContent='滑动边界 / '+(direction>0?'已是最后故事':'已是第一个故事');}}window.clearTimeout(state.timer);state.timer=window.setTimeout(play,180);record('story_browse',{{direction:direction}});return;}}const frame=state.activeFrame;const center=touchData.overlays[touchData.center_key];const resumeDelay=Math.max(180,state.pausedRemainingMs);if(frame)showTouch(frame,state.activeBaseSrc,center,frame.phase+' / 释放回正中','release');record('touch_release',{{resume_delay_ms:resumeDelay,frame_cue:frame?frame.cue:null}});window.clearTimeout(state.timer);window.setTimeout(()=>{{if(!state.touching)play();}},resumeDelay);}}
  function begin(event){{if(event.button!==undefined&&event.button!==0)return;if(state.touching)return;if(!state.activeFrame||image.hidden||!image.complete||!image.naturalWidth)return;event.preventDefault();state.touching=true;pauseCurrentFrame();record('touch_begin',{{frame_cue:state.activeFrame.cue}});state.startPoint=touchPoint(stage,event);state.lastPoint=state.startPoint;if(event.pointerId!==undefined){{try{{stage.setPointerCapture(event.pointerId);}}catch{{}}}}follow(event);}}
  function move(event){{if(state.touching){{event.preventDefault();follow(event);}}}}
  function end(event){{state.mouseDown=false;release(event);}}
  stage.addEventListener('dragstart',event=>{{event.preventDefault();}});stage.addEventListener('pointerdown',event=>{{if(event.pointerType!=='mouse')begin(event);}});stage.addEventListener('pointermove',event=>{{if(event.pointerType!=='mouse')move(event);}});stage.addEventListener('pointerup',event=>{{if(event.pointerType!=='mouse')end(event);}});stage.addEventListener('pointercancel',event=>{{if(event.pointerType!=='mouse')end(event);}});stage.addEventListener('lostpointercapture',()=>{{if(state.touching&&!state.mouseDown)release(null);}});
  stage.addEventListener('mousedown',event=>{{event.preventDefault();state.mouseDown=true;begin(event);}});stage.addEventListener('mousemove',event=>{{if(state.mouseDown)move(event);}});stage.addEventListener('mouseup',end);window.addEventListener('mouseup',event=>{{if(state.mouseDown)end(null);}});
  state.storyIndex=0;record('page_ready',{{revision:reviewRevision}});for(const frame of frames){{loadAsset(frame.touch_base||frame.src);}}
  for(const overlay of Object.values(touchData.overlays)){{loadAsset(overlay);}}play();
}}
</script></body></html>'''
    report = {
        "schema": "companion.v45_expanded_review_wall.v1",
        "status": "PASS_V45_EXPANDED_DYNAMIC_REVIEW_WALL_RUNTIME_INACTIVE",
        "source_preview_artifact": rel(PREVIEW),
        "source_preview_sha256": sha256(PREVIEW),
        "locked_v9_source_sha256": preview.get("locked_v9_source_sha256"),
        "canvas": {"width": 200, "height": 200, "pixel_format": "1bpp_white_is_one_msb"},
        "presentation": "vertical_scroll_single_column_all_owner_visible_stories",
        "owner_visible_story_count": len(visible_scores),
        "stories": report_stories,
        "expanded_frame_count": frame_count,
        "frame_source_rule": "every wall frame references an existing parity-rendered PNG and target_1bpp_sha256",
        "touch_interaction": {"surface": "each_story_200x200_viewport", "mode": "registered_pointer_and_mouse_coordinate_to_gaze_overlay",
                              "overlay_count": len(touch_package.get("overlays", {})), "base_story_count": len(touch_package.get("bases", {})),
                              "center_key": touch_package.get("center_key"), "mapping": "pointer x/y maps to registered highlight and sparkle offsets",
                              "release_behavior": "center_then_resume_story", "gestures": ["tap", "drag", "release_to_center", "swipe_left", "swipe_right", "swipe_up", "swipe_down"],
                              "swipe_behavior": "scroll_to_adjacent_story", "mouse_fallback": "mousedown_mousemove_mouseup"},
        "no_canvas": True,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_v45_machine_audit_and_owner_review",
        "html": rel(OUTPUT),
    }
    return OUTPUT, html_text, REPORT, json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    output, html_text, report, report_text = artifacts
    if args.check:
        require(output.is_file() and output.read_text(encoding="utf-8") == html_text,
                f"expanded wall drifted: {rel(output)}")
        require(report.is_file() and report.read_text(encoding="utf-8") == report_text,
                f"expanded wall report drifted: {rel(report)}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html_text, encoding="utf-8")
        report.write_text(report_text, encoding="utf-8")
    print(f"PASS: generated inactive vertical V45 review wall with 16 real 200x200 story viewports and 78 parity frame references ({rel(output)}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
