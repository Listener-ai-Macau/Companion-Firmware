#!/usr/bin/env python3
"""Prove native browser captures reproduce their declared 200x200 target PBMs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any

from PIL import Image, ImageChops


ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGE_BOX = (31, 65, 231, 265)
SCREENSHOT_SIZE = (520, 420)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def resolve(value: str) -> pathlib.Path:
    path = pathlib.Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def binary_stage(path: pathlib.Path) -> tuple[Image.Image, tuple[int, int]]:
    with Image.open(path) as source:
        image = source.convert("L")
        size = image.size
        stage = image.crop(STAGE_BOX).point(lambda value: 0 if value < 128 else 255, "1")
    return stage, size


def target_frame(route: dict[str, Any], scene: str, terminal: bool) -> tuple[int, dict[str, Any]]:
    performances = route.get("performances")
    frames = route.get("frames")
    if not isinstance(performances, list) or not isinstance(frames, list):
        raise ValueError("route performances or frames are malformed")
    performance = next((entry for entry in performances
                        if isinstance(entry, dict) and entry.get("id") == scene), None)
    if not isinstance(performance, dict):
        raise ValueError(f"route has no {scene} performance")
    indices = performance.get("frame_indices")
    if not isinstance(indices, list) or not indices or not all(isinstance(value, int) for value in indices):
        raise ValueError(f"{scene} has invalid frame indices")
    index = indices[-1] if terminal else indices[0]
    if not 0 <= index < len(frames) or not isinstance(frames[index], dict):
        raise ValueError(f"{scene} expected frame is malformed")
    return index, frames[index]


def compare(route: dict[str, Any], screenshot: dict[str, Any], scene: str,
            expected_pose: str, terminal: bool) -> dict[str, Any]:
    if screenshot.get("scene") != scene or screenshot.get("expected_art_pose") != expected_pose:
        raise ValueError(f"capture metadata drifted for {scene}")
    screenshot_path = resolve(str(screenshot.get("path", "")))
    index, frame = target_frame(route, scene, terminal)
    pbm_path = resolve(str(frame.get("targetPbm", "")))
    if not screenshot_path.is_file() or not pbm_path.is_file():
        raise ValueError(f"browser or PBM artifact is missing for {scene}")
    actual, screenshot_size = binary_stage(screenshot_path)
    with Image.open(pbm_path) as source:
        expected = source.convert("1")
    difference = ImageChops.difference(actual.convert("L"), expected.convert("L"))
    different_pixels = sum(1 for value in difference.getdata() if value != 0)
    return {
        "scene": scene,
        "screenshot": {"path": rel(screenshot_path), "sha256": sha256(screenshot_path), "size": list(screenshot_size)},
        "stage_box": list(STAGE_BOX),
        "expected_frame_index": index,
        "expected_art_pose": expected_pose,
        "target_pbm": {"path": rel(pbm_path), "sha256": sha256(pbm_path)},
        "different_pixels": different_pixels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", required=True)
    parser.add_argument("--capture", required=True)
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    route_path = resolve(args.route)
    capture_path = resolve(args.capture)
    write_path = resolve(args.write)
    route = load(route_path)
    capture = load(capture_path)
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    checks: dict[str, bool] = {
        "route_is_runtime_inactive_component_candidate": (
            route.get("status") == "PASS_V9_V22_TOUCH_EMOTION_ROUTE_RUNTIME_INACTIVE" and
            route.get("runtime_resource_activated") is False
        ),
        "capture_is_native_200x200_component_render": (
            capture.get("status") == "PASS_BROWSER_RENDER_INSPECTION_NATIVE_200X200" and
            capture.get("route", {}).get("sha256") == sha256(route_path)
        ),
    }
    screenshots = capture.get("screenshots")
    if not isinstance(screenshots, list):
        errors.append("capture screenshots are malformed")
    else:
        by_scene = {entry.get("scene"): entry for entry in screenshots if isinstance(entry, dict)}
        for scene, pose, terminal, check_name in [
            ("daily_micro", "v9_daily", False, "daily_stage_equals_v9_entry_pbm"),
            ("familiar_touch", "v22_warm", True, "familiar_touch_stage_equals_v22_warm_settle_pbm"),
        ]:
            try:
                record = compare(route, by_scene.get(scene, {}), scene, pose, terminal)
                records.append(record)
                checks[check_name] = (
                    tuple(record["screenshot"]["size"]) == SCREENSHOT_SIZE and
                    record["different_pixels"] == 0
                )
            except (OSError, ValueError) as error:
                errors.append(str(error))
                checks[check_name] = False
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.v9_v22_touch_emotion_browser_pixel_parity.v1",
        "status": "PASS_BROWSER_RENDER_PIXEL_PARITY_NATIVE_200X200" if not failures and not errors else "FAIL_BROWSER_RENDER_PIXEL_PARITY",
        "claim_scope": "runtime_inactive_browser_capture_pixel_parity_not_flash_or_physical_panel_acceptance",
        "route": {"path": rel(route_path), "sha256": sha256(route_path)},
        "capture": {"path": rel(capture_path), "sha256": sha256(capture_path)},
        "checks": checks,
        "records": records,
        "failures": failures + errors,
    }
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"].startswith("FAIL"):
        print(f"FAIL: browser render pixel parity -> {rel(write_path)}", file=sys.stderr)
        for failure in report["failures"]:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: browser render pixel parity -> {rel(write_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
