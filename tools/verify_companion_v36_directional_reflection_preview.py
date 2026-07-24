#!/usr/bin/env python3
"""Independently replay the V36 directional reflection browser component plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
V9_LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_IDLE = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
CANVAS = (200, 200)
EXPECTED_PHASES = ("rest", "eyes_lower_1", "eyes_lower_2", "down_hold", "eyes_return", "rest_dwell")
V9_COMPONENT_ROOT = "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components/"


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
    return sum(first.getpixel((x, y)) != second.getpixel((x, y)) for y in range(200) for x in range(200))


def verify(source_gate_path: pathlib.Path, preview_gate_path: pathlib.Path) -> dict[str, object]:
    source_gate = json.loads(source_gate_path.read_text(encoding="ascii"))
    preview_gate = json.loads(preview_gate_path.read_text(encoding="ascii"))
    require(source_gate.get("status") == "PASS_V36_DIRECTIONAL_REFLECTION_SOURCE_GATE", "source gate is not PASS")
    require(preview_gate.get("status") == "PASS_COMPONENT_ONLY_DIRECTIONAL_BROWSER_PREVIEW_GATE", "preview gate is not PASS")
    require(source_gate.get("direction") == "down" and preview_gate.get("direction") == "down", "direction mismatch")
    require(sha256(V9_LOCKED) == V9_LOCKED_SHA256, "locked V9 source hash changed")
    require(preview_gate.get("source_gate_sha256") == sha256(source_gate_path), "preview binds a different source gate")
    require(preview_gate.get("runtime_resource_activated") is False and
            preview_gate.get("active_candidate_binding") == "forbidden", "preview unexpectedly activated")
    data_path = ROOT / str(preview_gate["data"])
    require(data_path.is_file() and sha256(data_path) == preview_gate.get("data_sha256"), "preview data hash drift")
    data = json.loads(data_path.read_text(encoding="ascii"))
    require(data.get("canvas") == {"width": 200, "height": 200}, "preview is not native 200x200")
    require(data.get("component_only") is True and data.get("full_face_cards") is False and
            data.get("random_motion") is False, "preview is not component-only deterministic choreography")
    native_hold = ROOT / str(source_gate.get("native_200_hold", {}).get("path", ""))
    down_component_root = native_hold.parent.parent / "components"
    down_component_root_rel = rel(down_component_root) + "/"
    registered_down_hashes = source_gate.get("component_hashes")
    require(native_hold.is_file() and isinstance(registered_down_hashes, dict),
            "source gate does not register its candidate components")
    story = data.get("story")
    replay = data.get("frame_replay")
    assets = data.get("assets")
    require(isinstance(story, list) and isinstance(replay, list) and isinstance(assets, dict), "invalid preview data")
    require(tuple(step.get("phase") for step in story) == EXPECTED_PHASES, "unexpected phase order")
    require(len(story) == len(replay), "replay does not cover all phases")
    for name, asset in assets.items():
        require(isinstance(asset, dict), f"asset {name} is invalid")
        source = str(asset.get("source_mask", ""))
        if not source.startswith(V9_COMPONENT_ROOT):
            require(source.startswith(down_component_root_rel) and
                    registered_down_hashes.get(pathlib.PurePosixPath(source).name) == asset.get("source_sha256"),
                    f"asset {name} is not a registered component from this source gate")
        source_path = ROOT / source
        require(source_path.suffix == ".pbm" and source_path.is_file() and
                sha256(source_path) == asset.get("source_sha256"), f"asset {name} hash drift")
        require(asset.get("color") in {"black", "white"}, f"asset {name} has invalid color")
    expected_static: list[dict[str, object]] | None = None
    results: list[dict[str, object]] = []
    for step, expected in zip(story, replay):
        require(step.get("phase") == expected.get("phase") and step.get("layers") == expected.get("layers"),
                "story and frame replay differ")
        layers = step["layers"]
        static = [current for current in layers if not str(current.get("asset", "")).endswith(("_primary", "_sparkle"))]
        if expected_static is None:
            expected_static = static
        else:
            require(static == expected_static, f"{step['phase']}: non-reflection V9 identity changed")
        canvas = Image.new("1", CANVAS, 255)
        for current in layers:
            name = str(current.get("asset", ""))
            require(name in assets, f"unknown component {name}")
            position = current.get("position")
            require(isinstance(position, list) and len(position) == 2 and all(isinstance(value, int) for value in position),
                    f"{step['phase']}/{name}: invalid component position")
            asset = assets[name]
            paste(canvas, Image.open(ROOT / str(asset["source_mask"])).convert("1"), tuple(position), str(asset["color"]))
        frame_path = ROOT / str(expected["path"])
        require(frame_path.is_file() and sha256(frame_path) == expected.get("sha256"), f"{step['phase']}: frame hash drift")
        expected_frame = Image.open(frame_path).convert("1")
        pixels = difference(canvas, expected_frame)
        require(pixels == 0, f"{step['phase']}: component replay differs by {pixels}px")
        pbm_path = ROOT / str(expected.get("target_pbm", ""))
        require(pbm_path.is_file() and sha256(pbm_path) == expected.get("target_pbm_sha256"),
                f"{step['phase']}: target PBM hash drift")
        require(difference(expected_frame, Image.open(pbm_path).convert("1")) == 0,
                f"{step['phase']}: PNG/PBM source-plan pixels differ")
        results.append({"phase": step["phase"], "pixels_different_from_component_replay": pixels,
                        "frame": str(expected["path"]), "target_pbm": str(expected["target_pbm"])})
    frames = [Image.open(ROOT / str(item["path"])).convert("1") for item in replay]
    rest = Image.open(V9_IDLE).convert("1")
    require(difference(frames[0], rest) == 0 and difference(frames[-1], rest) == 0,
            "opening or final dwell is not exact locked V9 rest")
    beat_differences = [difference(frames[index], frames[index + 1]) for index in range(len(frames) - 1)]
    require(all(value > 0 for value in beat_differences), "gaze choreography contains a static transition beat")
    return {
        "schema": "companion.v36_directional_reflection_browser_replay_gate.v1",
        "status": "PASS_V36_DIRECTIONAL_REFLECTION_BROWSER_REPLAY_GATE",
        "direction": "down",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "source_gate": rel(source_gate_path), "source_gate_sha256": sha256(source_gate_path),
        "preview_gate": rel(preview_gate_path), "preview_gate_sha256": sha256(preview_gate_path),
        "locked_v9_source": rel(V9_LOCKED), "locked_v9_sha256": V9_LOCKED_SHA256,
        "canvas": {"width": 200, "height": 200},
        "component_only": True, "full_face_cards": False, "random_motion": False,
        "phases": list(EXPECTED_PHASES), "frame_replay": results,
        "component_beat_differences": dict(zip(("rest_to_lower_1", "lower_1_to_lower_2", "lower_2_to_hold", "hold_to_return", "return_to_rest"), beat_differences)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-gate", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-source-gate-20260720.json")
    parser.add_argument("--preview-gate", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-browser-preview-20260720.json")
    parser.add_argument("--write", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-browser-replay-20260720.json")
    args = parser.parse_args()
    try:
        result = verify(args.source_gate.resolve(), args.preview_gate.resolve())
    except (OSError, ValueError, KeyError) as exc:
        result = {"schema": "companion.v36_directional_reflection_browser_replay_gate.v1",
                  "status": "FAIL_V36_DIRECTIONAL_REFLECTION_BROWSER_REPLAY_GATE", "error": str(exc)}
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print("PASS: V36 Daily-down browser plan independently replays as exact V9 component-only frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
