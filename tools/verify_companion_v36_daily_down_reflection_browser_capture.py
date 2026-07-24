#!/usr/bin/env python3
"""Verify Edge captures of the V36 Daily-down component-only browser player."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_PHASES = ("rest", "eyes_lower_1", "eyes_lower_2", "down_hold", "eyes_return", "rest_dwell")
V9_LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
CANVAS = (200, 200)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def max_white_run(row: list[tuple[int, int, int]]) -> tuple[int, int]:
    best_start = best_width = current_start = current_width = 0
    for index, pixel in enumerate(row):
        if pixel == (255, 255, 255):
            if current_width == 0:
                current_start = index
            current_width += 1
            if current_width > best_width:
                best_start, best_width = current_start, current_width
        else:
            current_width = 0
    return best_start, best_width


def canvas_crop(screenshot: Image.Image) -> tuple[Image.Image, dict[str, int]]:
    image = screenshot.convert("RGB")
    width, height = image.size
    rows = [[image.getpixel((x, y)) for x in range(width)] for y in range(height)]
    runs = [max_white_run(row) for row in rows]
    x0, run_width = max(runs, key=lambda item: item[1])
    require(run_width >= 390, f"cannot locate 400px browser canvas; best white run={run_width}px")
    canvas_width = run_width
    require(x0 + canvas_width <= width, "detected browser canvas exceeds screenshot width")
    rows_inside: list[int] = []
    for y, row in enumerate(rows):
        white_count = sum(pixel == (255, 255, 255) for pixel in row[x0:x0 + canvas_width])
        if white_count >= 250:
            rows_inside.append(y)
    groups: list[list[int]] = []
    for y in rows_inside:
        if not groups or y != groups[-1][-1] + 1:
            groups.append([y])
        else:
            groups[-1].append(y)
    viable = [group for group in groups if len(group) >= 390]
    require(bool(viable), "cannot locate a 400px-tall browser canvas")
    group = max(viable, key=len)
    y0 = group[0]
    require(y0 + canvas_width <= height, "detected browser canvas exceeds screenshot height")
    crop = image.crop((x0, y0, x0 + canvas_width, y0 + canvas_width))
    return crop.resize(CANVAS, Image.Resampling.NEAREST).convert("L").point(
        lambda value: 0 if value < 160 else 255, mode="1"), {
            "x": x0, "y": y0, "width": canvas_width, "height": canvas_width
        }


def difference(first: Image.Image, second: Image.Image) -> int:
    return sum(first.getpixel((x, y)) != second.getpixel((x, y))
               for y in range(CANVAS[1]) for x in range(CANVAS[0]))


def verify(preview_gate_path: pathlib.Path, captures: list[pathlib.Path]) -> dict[str, object]:
    preview_gate = json.loads(preview_gate_path.read_text(encoding="ascii"))
    require(preview_gate.get("status") == "PASS_COMPONENT_ONLY_DIRECTIONAL_BROWSER_PREVIEW_GATE",
            "browser preview plan is not PASS")
    require(preview_gate.get("runtime_resource_activated") is False and
            preview_gate.get("active_candidate_binding") == "forbidden", "candidate unexpectedly activated")
    require(sha256(V9_LOCKED) == V9_LOCKED_SHA256, "locked V9 source hash changed")
    data_path = ROOT / str(preview_gate["data"])
    require(data_path.is_file() and sha256(data_path) == preview_gate.get("data_sha256"), "player data hash drift")
    data = json.loads(data_path.read_text(encoding="ascii"))
    replay = data.get("frame_replay")
    require(data.get("canvas") == {"width": 200, "height": 200} and isinstance(replay, list),
            "invalid native browser player data")
    require(tuple(item.get("phase") for item in replay) == EXPECTED_PHASES, "unexpected replay phase order")
    require(len(captures) == len(replay), "capture count does not cover browser choreography")
    results: list[dict[str, object]] = []
    for expected, capture in zip(replay, captures):
        require(capture.is_file(), f"missing Edge capture {capture}")
        browser_frame, box = canvas_crop(Image.open(capture))
        expected_frame_path = ROOT / str(expected["path"])
        require(expected_frame_path.is_file() and sha256(expected_frame_path) == expected.get("sha256"),
                f"registered component frame drift: {expected['phase']}")
        pixels = difference(browser_frame, Image.open(expected_frame_path).convert("1"))
        require(pixels == 0, f"Edge canvas differs from registered component plan for {expected['phase']}: {pixels}px")
        results.append({
            "phase": expected["phase"],
            "capture": rel(capture),
            "capture_sha256": sha256(capture),
            "browser_canvas_box": box,
            "pixels_different_from_registered_component_frame": pixels,
        })
    return {
        "schema": "companion.v36_daily_down_reflection_browser_capture_gate.v1",
        "status": "PASS_V36_DAILY_DOWN_REFLECTION_BROWSER_CAPTURE_GATE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "browser_engine": "Microsoft Edge headless",
        "preview_gate": rel(preview_gate_path),
        "preview_gate_sha256": sha256(preview_gate_path),
        "player": str(preview_gate["player"]),
        "player_sha256": str(preview_gate["player_sha256"]),
        "locked_v9_source": rel(V9_LOCKED),
        "locked_v9_sha256": V9_LOCKED_SHA256,
        "canvas": {"width": 200, "height": 200},
        "component_only": True,
        "full_face_cards": False,
        "random_motion": False,
        "captures": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-gate", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-browser-preview-20260720.json")
    parser.add_argument("--capture", type=pathlib.Path, nargs="+", required=True)
    parser.add_argument("--write", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-reflection-browser-capture-20260720.json")
    args = parser.parse_args()
    try:
        result = verify(args.preview_gate.resolve(), [path.resolve() for path in args.capture])
    except (OSError, ValueError, KeyError) as exc:
        result = {"schema": "companion.v36_daily_down_reflection_browser_capture_gate.v1",
                  "status": "FAIL_V36_DAILY_DOWN_REFLECTION_BROWSER_CAPTURE_GATE", "error": str(exc)}
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print("PASS: Edge canvas is pixel-identical to every registered 200x200 component choreography frame.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
