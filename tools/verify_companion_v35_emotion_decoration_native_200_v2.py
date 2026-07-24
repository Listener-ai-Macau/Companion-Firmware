#!/usr/bin/env python3
"""Machine gate for the V35 r2 native-200 component choreography preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/request-v2.json"
LINEAGE = ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/source-lineage-v2.json"
REPORT = ROOT / "docs/validation/companion-v35-emotion-decoration-native-200-v2-render-20260720.json"
PLAYBACK = ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate/review-v2/native-200-playback-preview.html"
EVENTS = ("curious_question", "alert_exclamation", "sleepy_dream_cloud")
TRANSITION_STAGES = [
    "source_hold",
    "highlight_lead",
    "paired_highlight_arrive",
    "brow_answer",
    "mouth_cheek_reply",
    "target_face_settle",
    "decoration_follow_through",
    "decoration_arrive",
    "target_hold",
]
PRESENCE_STAGES = [
    "target_hold",
    "highlight_lead",
    "paired_highlight_arrive",
    "brow_answer",
    "mouth_cheek_reply",
    "target_hold",
]
PRIMARY_ROLES = {"left_brow", "right_brow", "left_eye", "right_eye", "left_cheek", "right_cheek", "nose", "mouth"}
OPEN_EYE_DETAIL_ROLES = {"left_highlight", "right_highlight", "left_sparkle", "right_sparkle"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def image_1bit(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.size != (200, 200):
        raise ValueError(f"{path} is not 200x200")
    values = set(image.convert("L").getdata())
    if not values.issubset({0, 255}):
        raise ValueError(f"{path} is not pure monochrome")
    return image.convert("1")


def ink_bounds(image: Image.Image) -> list[int]:
    bbox = image.convert("1").point(lambda value: 255 if value == 0 else 0, mode="L").getbbox()
    if bbox is None:
        raise ValueError("frame has no black ink")
    return [bbox[0], bbox[1], bbox[2] - 1, bbox[3] - 1]


def assert_png_pbm(frame: dict[str, object]) -> dict[str, object]:
    png = ROOT / str(frame["png"])
    pbm = ROOT / str(frame["pbm"])
    if sha256(png) != frame["sha256"]:
        raise ValueError(f"PNG hash drifted: {png}")
    png_image = image_1bit(png)
    pbm_image = image_1bit(pbm)
    if ImageChops.difference(png_image, pbm_image).getbbox() is not None:
        raise ValueError(f"PNG/PBM pixel mismatch: {png.name}")
    bounds = ink_bounds(png_image)
    if min(bounds[0], bounds[1]) < 8 or max(bounds[2], bounds[3]) > 191:
        raise ValueError(f"frame violates 8px safe inset: {png.name} {bounds}")
    layers = frame.get("v9_layers")
    if not isinstance(layers, list) or not layers:
        raise ValueError(f"frame missing V9 component layer evidence: {png.name}")
    roles = {layer.get("role") for layer in layers if isinstance(layer, dict)}
    if not PRIMARY_ROLES.issubset(roles):
        raise ValueError(f"frame missing primary V9 facial component role: {png.name}")
    eye_variants = {layer.get("variant") for layer in layers if isinstance(layer, dict) and layer.get("role") in {"left_eye", "right_eye"}}
    if eye_variants == {"open"} and not OPEN_EYE_DETAIL_ROLES.issubset(roles):
        raise ValueError(f"open-eye frame missing V9 highlight identity roles: {png.name}")
    if "charm" in roles:
        raise ValueError(f"frame selected an inherited charm: {png.name}")
    return {"path": str(png.relative_to(ROOT)).replace("\\", "/"), "bounds": bounds}


def added_ink(before: Image.Image, after: Image.Image) -> Image.Image:
    before_pixels = before.convert("1").load()
    after_pixels = after.convert("1").load()
    result = Image.new("1", (200, 200), 1)
    result_pixels = result.load()
    for y in range(200):
        for x in range(200):
            if before_pixels[x, y] == 255 and after_pixels[x, y] == 0:
                result_pixels[x, y] = 0
            if before_pixels[x, y] == 0 and after_pixels[x, y] == 255:
                raise ValueError("decoration follow-through erased existing face ink")
    return result


def source_gate(request: dict[str, object], lineage: dict[str, object], render: dict[str, object]) -> list[dict[str, object]]:
    if request.get("status") != "GENERATED_PENDING_NATIVE_200_MACHINE_PREVIEW":
        raise ValueError("V35 r2 request is not the expected generated candidate")
    locked = request.get("locked_reference")
    if not isinstance(locked, dict) or locked.get("sha256") != LOCKED_V9_SHA256:
        raise ValueError("request does not lock the V9 source hash")
    if lineage.get("sole_visual_reference", {}).get("sha256") != LOCKED_V9_SHA256:
        raise ValueError("lineage does not lock the V9 source hash")
    if render.get("locked_v9", {}).get("sha256") != LOCKED_V9_SHA256:
        raise ValueError("render does not lock the V9 source hash")
    if lineage.get("generation", {}).get("reference_inputs") != ["locked_v9_reference_only"]:
        raise ValueError("lineage permits an unapproved visual input")
    request_sources = request.get("component_sources")
    report_sources = render.get("generated_sources")
    lineage_sources = {item["component"]: item for item in lineage.get("sources", [])}
    if not isinstance(request_sources, dict) or not isinstance(report_sources, dict):
        raise ValueError("source metadata is malformed")
    result = []
    for name in EVENTS:
        request_item = request_sources.get(name)
        report_item = report_sources.get(name)
        lineage_item = lineage_sources.get(name)
        if not isinstance(request_item, dict) or not isinstance(report_item, dict) or not isinstance(lineage_item, dict):
            raise ValueError(f"missing V35 source metadata for {name}")
        path = REQUEST.parent / str(request_item.get("candidate"))
        actual = sha256(path)
        if actual != request_item.get("sha256") or actual != report_item.get("sha256") or actual != lineage_item.get("sha256"):
            raise ValueError(f"source hash mismatch for {name}")
        prompt = REQUEST.parent / str(request_item.get("prompt"))
        prompt_text = prompt.read_text(encoding="utf-8")
        if "locked V9" not in prompt_text or "V35" not in prompt_text:
            raise ValueError(f"prompt missing V9-only revision identity for {name}")
        if "v1" in prompt_text.lower():
            raise ValueError(f"prompt reuses rejected V35 revision-1 language for {name}")
        result.append({"component": name, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": actual})
    return result


def browser_binding(render: dict[str, object]) -> dict[str, object]:
    html = PLAYBACK.read_text(encoding="utf-8")
    if "window.v35Native200Score" not in html:
        raise ValueError("browser preview does not expose its native score")
    found = re.findall(r'\["([A-Za-z0-9_\-]+\.png)",\s*(\d+)\]', html)
    expected: list[tuple[str, str]] = []
    for event in EVENTS:
        presence = render["events"][event]["presence"]
        expected.extend((Path(item["png"]).name, str(item["duration_ms"])) for item in presence)
    if found != expected:
        raise ValueError("browser playback score is not bound to the reported native PNG frame plan")
    return {"path": str(PLAYBACK.relative_to(ROOT)).replace("\\", "/"), "frame_bindings": len(found)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", default=str(REQUEST.relative_to(ROOT)))
    parser.add_argument("--lineage", default=str(LINEAGE.relative_to(ROOT)))
    parser.add_argument("--report", default=str(REPORT.relative_to(ROOT)))
    parser.add_argument("--write", default="docs/validation/companion-v35-emotion-decoration-native-200-v2-machine-gate-20260720.json")
    args = parser.parse_args()
    request = read_json((ROOT / args.request).resolve())
    lineage = read_json((ROOT / args.lineage).resolve())
    render = read_json((ROOT / args.report).resolve())
    if render.get("status") != "CANDIDATE_PENDING_INTERNAL_NATIVE_200_REVIEW":
        raise ValueError("render is not a pending internal candidate")
    sources = source_gate(request, lineage, render)
    evidence_events: dict[str, object] = {}

    for event in EVENTS:
        event_data = render["events"].get(event)
        if not isinstance(event_data, dict):
            raise ValueError(f"render missing event {event}")
        transition = event_data.get("transition")
        presence = event_data.get("presence")
        if not isinstance(transition, list) or not isinstance(presence, list):
            raise ValueError(f"event frame records malformed: {event}")
        if [frame.get("stage") for frame in transition] != TRANSITION_STAGES:
            raise ValueError(f"transition order drifted for {event}")
        if [frame.get("stage") for frame in presence] != PRESENCE_STAGES:
            raise ValueError(f"same-state presence order drifted for {event}")
        if event_data.get("transition_order") != TRANSITION_STAGES or event_data.get("same_state_presence_order") != PRESENCE_STAGES:
            raise ValueError(f"event choreography metadata drifted for {event}")
        if event_data.get("inherited_charm_policy") != "all inherited V9 charms omitted by component selection":
            raise ValueError(f"event does not suppress mutually exclusive inherited charms: {event}")
        transition_evidence = [assert_png_pbm(frame) for frame in transition]
        presence_evidence = [assert_png_pbm(frame) for frame in presence]
        if len({frame["sha256"] for frame in transition}) < 7 or len({frame["sha256"] for frame in presence}) < 4:
            raise ValueError(f"insufficient component motion in {event}")
        if json.dumps(transition[5]["v9_layers"], sort_keys=True) != json.dumps(transition[6]["v9_layers"], sort_keys=True):
            raise ValueError(f"target face is not stable before decoration entry for {event}")
        before = image_1bit(ROOT / transition[5]["png"])
        after = image_1bit(ROOT / transition[6]["png"])
        decoration = added_ink(before, after)
        decoration_bounds = ink_bounds(decoration)
        decoration_pixels = sum(1 for pixel in decoration.getdata() if pixel == 0)
        if decoration_pixels < 8:
            raise ValueError(f"decoration entry has too little source-derived ink for {event}")
        evidence_events[event] = {
            "transition_frames": transition_evidence,
            "presence_frames": presence_evidence,
            "decoration_entry": {"added_ink_pixels": decoration_pixels, "bounds": decoration_bounds},
        }

    binding = browser_binding(render)
    output = {
        "schema": "companion.v35.emotion_decoration_native_200_machine_gate.v2",
        "status": "PASS_MACHINE_PREVIEW_ONLY_RUNTIME_INACTIVE",
        "authority": "COMP-REQ-190",
        "render": str((ROOT / args.report).resolve().relative_to(ROOT)).replace("\\", "/"),
        "source_gate": sources,
        "browser_binding": binding,
        "events": evidence_events,
        "runtime": {
            "resource_activated": False,
            "component_export": "forbidden",
            "firmware_binding": "forbidden",
            "panel_claim": "forbidden_until_P0_panel_and_later_runtime_gates_pass",
        },
    }
    output_path = (ROOT / args.write).resolve()
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
