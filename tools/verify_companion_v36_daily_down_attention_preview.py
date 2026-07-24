#!/usr/bin/env python3
"""Independently replay the V36 Daily-down browser component plan at 200x200."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_GATE = ROOT / "docs/validation/companion-v36-daily-down-attention-source-gate-20260720.json"
PREVIEW_GATE = ROOT / "docs/validation/companion-v36-daily-down-component-browser-preview-20260720.json"
V9_IDLE = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
V9_LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
CANVAS = (200, 200)
EXPECTED_PHASES = ("entry", "eyes_lead", "brows_answer", "mouth_settles", "hold", "settle", "rest_dwell")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def paste(canvas: Image.Image, mask: Image.Image, position: tuple[int, int], color: str) -> None:
    alpha = mask.convert("1").point(lambda value: 255 if value == 0 else 0)
    canvas.paste(255 if color == "white" else 0, position, alpha)


def difference(first: Image.Image, second: Image.Image) -> int:
    return sum(first.getpixel((x, y)) != second.getpixel((x, y))
               for y in range(CANVAS[1]) for x in range(CANVAS[0]))


def verify(source_gate_path: pathlib.Path, preview_gate_path: pathlib.Path) -> dict[str, object]:
    source_gate = json.loads(source_gate_path.read_text(encoding="ascii"))
    preview_gate = json.loads(preview_gate_path.read_text(encoding="ascii"))
    require(source_gate.get("status") == "PASS_V36_DAILY_DOWN_ATTENTION_SOURCE_GATE",
            "source gate is not PASS")
    require(preview_gate.get("status") == "PASS_COMPONENT_ONLY_BROWSER_PREVIEW_GATE",
            "browser preview gate is not PASS")
    require(source_gate.get("runtime_resource_activated") is False and
            preview_gate.get("runtime_resource_activated") is False,
            "candidate unexpectedly activated")
    require(source_gate.get("active_candidate_binding") == "forbidden" and
            preview_gate.get("active_candidate_binding") == "forbidden",
            "candidate binding is not forbidden")
    require(sha256(V9_LOCKED) == V9_LOCKED_SHA256, "locked V9 source hash changed")
    data_path = ROOT / str(preview_gate["data"])
    require(sha256(data_path) == preview_gate["data_sha256"], "browser preview data hash drift")
    data = json.loads(data_path.read_text(encoding="ascii"))
    require(data.get("canvas") == {"width": 200, "height": 200}, "browser preview is not native 200x200")
    require(data.get("component_only") is True and data.get("full_face_cards") is False and
            data.get("random_motion") is False, "browser preview violates Rig-only choreography")
    require(data.get("source_gate_sha256") == sha256(source_gate_path), "preview is bound to a different source gate")
    assets = data.get("assets")
    story = data.get("story")
    replay = data.get("frame_replay")
    require(isinstance(assets, dict) and isinstance(story, list) and isinstance(replay, list),
            "preview data shape is invalid")
    require(tuple(step.get("phase") for step in story) == EXPECTED_PHASES,
            "preview phases do not follow the deterministic attention choreography")
    require(len(story) == len(replay), "preview replay does not cover every story phase")
    allowed_roots = (
        "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components/",
        "docs/art/iterations/companion-pet-expression-v9-extension-v36-directional-eye-gaze-source/candidate/component-export-attempt-06/components/",
    )
    for name, asset in assets.items():
        require(isinstance(asset, dict), f"asset {name} is not an object")
        source = str(asset.get("source_mask", ""))
        require(source.startswith(allowed_roots), f"asset {name} is not a registered V9/V36 component")
        source_path = ROOT / source
        require(source_path.is_file() and sha256(source_path) == asset.get("source_sha256"),
                f"asset {name} hash drift")
        position = asset.get("position")
        require(isinstance(position, list) and len(position) == 2 and all(isinstance(value, int) for value in position),
                f"asset {name} has an invalid position")
        require(asset.get("color") in {"black", "white"}, f"asset {name} has invalid color")
    frame_results: list[dict[str, object]] = []
    for step, expected in zip(story, replay):
        require(step.get("phase") == expected.get("phase"), "story/replay phase mismatch")
        require(step.get("layers") == expected.get("layers"), "story/replay layer mismatch")
        canvas = Image.new("1", CANVAS, 255)
        for layer_name in step["layers"]:
            require(layer_name in assets, f"unknown layer {layer_name}")
            asset = assets[layer_name]
            mask = Image.open(ROOT / asset["source_mask"]).convert("1")
            paste(canvas, mask, tuple(asset["position"]), str(asset["color"]))
        expected_path = ROOT / str(expected["path"])
        require(expected_path.is_file() and sha256(expected_path) == expected.get("sha256"),
                f"frame artifact drift for {step['phase']}")
        expected_frame = Image.open(expected_path).convert("1")
        pixels = difference(canvas, expected_frame)
        require(pixels == 0, f"component replay mismatch in {step['phase']}: {pixels}px")
        frame_results.append({"phase": step["phase"], "pixels_different_from_component_replay": pixels,
                              "frame": str(expected["path"])})
    v9_rest = Image.open(V9_IDLE).convert("1")
    entry = Image.open(ROOT / str(replay[0]["path"])).convert("1")
    settle = Image.open(ROOT / str(replay[5]["path"])).convert("1")
    dwell = Image.open(ROOT / str(replay[6]["path"])).convert("1")
    require(difference(entry, v9_rest) == 0 and difference(settle, v9_rest) == 0 and difference(dwell, v9_rest) == 0,
            "entry/settle/rest-dwell are not exact locked V9 rest")
    lead = Image.open(ROOT / str(replay[1]["path"])).convert("1")
    answer = Image.open(ROOT / str(replay[2]["path"])).convert("1")
    hold = Image.open(ROOT / str(replay[3]["path"])).convert("1")
    require(difference(entry, lead) > 0 and difference(lead, answer) > 0 and difference(answer, hold) > 0,
            "eyes, brows and mouth do not produce separate deterministic choreography beats")
    return {
        "schema": "companion.v36_daily_down_component_browser_replay_gate.v1",
        "status": "PASS_V36_DAILY_DOWN_COMPONENT_BROWSER_REPLAY_GATE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "source_gate": rel(source_gate_path),
        "source_gate_sha256": sha256(source_gate_path),
        "preview_gate": rel(preview_gate_path),
        "preview_gate_sha256": sha256(preview_gate_path),
        "locked_v9_source": rel(V9_LOCKED),
        "locked_v9_sha256": V9_LOCKED_SHA256,
        "canvas": {"width": 200, "height": 200},
        "component_only": True,
        "full_face_cards": False,
        "random_motion": False,
        "phases": list(EXPECTED_PHASES),
        "frame_replay": frame_results,
        "component_beat_differences": {
            "entry_to_eyes_lead": difference(entry, lead),
            "eyes_lead_to_brows_answer": difference(lead, answer),
            "brows_answer_to_mouth_settles": difference(answer, hold),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-gate", type=pathlib.Path, default=SOURCE_GATE)
    parser.add_argument("--preview-gate", type=pathlib.Path, default=PREVIEW_GATE)
    parser.add_argument("--write", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-component-browser-replay-20260720.json")
    args = parser.parse_args()
    try:
        result = verify(args.source_gate.resolve(), args.preview_gate.resolve())
    except (OSError, ValueError, KeyError) as exc:
        result = {"schema": "companion.v36_daily_down_component_browser_replay_gate.v1",
                  "status": "FAIL_V36_DAILY_DOWN_COMPONENT_BROWSER_REPLAY_GATE", "error": str(exc)}
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print("PASS: V36 Daily-down browser plan replays as exact component-only 200x200 frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
