#!/usr/bin/env python3
"""Gate V44 blink provenance, paired-mask symmetry, stable gaze, and blink choreography."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v1/generation-request-v1.json"
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-blink-source-v1/candidate/attempt-01-blink-component-source.png"
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/v44-special-component-layout.json"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate/target-score-attempt-01/v44-wb55-target-profile-plan.json"
REPORT = ROOT / "docs/validation/companion-v44-blink-stable-center-layout-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_SHA = "BAAC2D677AAC557AB74E54718B2748C4FA8D460715B8C96AB1491FD7894504FB"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{rel(path)} must contain an object")
    return value


def black_pixels(image: Image.Image) -> int:
    return sum(1 for pixel in image.convert("1").getdata() if pixel == 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    request = load(REQUEST)
    layout = load(LAYOUT)
    trace = load(TRACE)
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            request.get("blink_contract", {}).get("pairing") == "left/right matched and synchronized",
            "V44 blink request provenance drifted")
    require(SOURCE.is_file() and sha256(SOURCE) == SOURCE_SHA, "V44 blink source hash drifted")
    with Image.open(SOURCE) as opened:
        source = opened.convert("RGB")
    require(source.size == (1774, 887), f"V44 blink source dimensions drifted: {source.size}")
    components = {int(item["component_id"]): item for item in layout.get("components", [])}
    left = components.get(597)
    right = components.get(598)
    require(left is not None and right is not None, "V44 blink pair is not registered")
    left_mask = Image.open(ROOT / left["mask"]).convert("1")
    right_mask = Image.open(ROOT / right["mask"]).convert("1")
    mirrored = right_mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pixel_diff = sum(1 for first, second in zip(left_mask.getdata(), mirrored.getdata()) if first != second)
    require(left["role"] == "left_eye" and right["role"] == "right_eye" and
            left["source"]["sheet"] == rel(SOURCE) and right["source"]["sheet"] == rel(SOURCE) and
            left["source"]["synchronized"] is True and right["source"]["synchronized"] is True and
            left["base_position"] == [42, 128] and right["base_position"] == [125, 128] and
            left["offset_range"] == {"min": [0, 0], "max": [0, 0]} and
            right["offset_range"] == {"min": [0, 0], "max": [0, 0]} and
            abs(black_pixels(left_mask) - black_pixels(right_mask)) <= 2 and pixel_diff <= 2,
            f"V44 blink pair is not matched: left={black_pixels(left_mask)} right={black_pixels(right_mask)} mirror_diff={pixel_diff}")
    calm = next(score for score in trace["scores"] if score["name"] == "calm_presence")
    require([step["cue"] for step in calm["steps"]] == ["calm_entry", "calm_blink_close", "calm_blink_hold", "calm_hold", "calm_settle"],
            "V44 calm blink cue order drifted")
    require([step["duration_ms"] for step in calm["steps"]] == [220, 110, 90, 1800, 360],
            "V44 calm blink timing drifted")
    for score in trace["scores"]:
        if score["name"].startswith("daily_attention_"):
            continue
        for frame in score["steps"]:
            layers = {layer["component_id"]: layer["offset"] for layer in frame["layers"]}
            for component_id in (1, 5, 3, 7):
                if component_id in layers:
                    require(layers[component_id] == [1, 0],
                            f"automatic gaze drifted from center: {score['name']} {frame['cue']}")
    blink_frames = [step for step in calm["steps"] if step["cue"] in {"calm_blink_close", "calm_blink_hold"}]
    require(all({597, 598}.issubset({layer["component_id"] for layer in frame["layers"]}) for frame in blink_frames),
            "V44 blink frames do not contain both registered closed-eye components")
    require(all(not ({1, 2, 3, 5, 6, 7} & {layer["component_id"] for layer in frame["layers"]}) for frame in blink_frames),
            "V44 blink frames retain open-eye or highlight components")
    report = {
        "schema": "companion.v44_blink_stable_center_layout_gate.v1",
        "status": "PASS_V44_BLINK_STABLE_CENTER_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-093", "COMP-REQ-261"],
        "locked_v9_source_sha256": LOCKED,
        "blink_source": {"path": rel(SOURCE), "sha256": SOURCE_SHA, "dimensions": [1774, 887],
                          "request": rel(REQUEST), "left_mask_sha256": left["mask_sha256"],
                          "right_mask_sha256": right["mask_sha256"], "mirror_pixel_diff": pixel_diff},
        "idle_contract": {"automatic_gaze": "center", "synchronized_blink_cues": ["calm_blink_close", "calm_blink_hold"],
                          "durations_ms": [110, 90], "open_eye_components_removed": [1, 2, 3, 5, 6, 7]},
        "runtime_resource_activated": False,
        "non_claims": ["no_lower_driver_change", "no_runtime_activation", "no_human_acceptance"],
    }
    path = args.write if args.write.is_absolute() else ROOT / args.write
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: V44 blink pair, stable-center automatic gaze, and blink choreography are gated ({path}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
