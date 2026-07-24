#!/usr/bin/env python3
"""Verify the inactive V9/V22 touch-emotion route has target/browser component parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE = ROOT / "docs/validation/companion-v9-v22-touch-emotion-route-preview-20260720.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-v22-touch-emotion-route-parity-20260720.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def pixel_distance(left: Image.Image, right: Image.Image) -> int:
    return sum(a != b for a, b in zip(left.convert("1").getdata(), right.convert("1").getdata()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", type=Path, default=DEFAULT_ROUTE)
    parser.add_argument("--write", type=Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    route_path = args.route if args.route.is_absolute() else ROOT / args.route
    write_path = args.write if args.write.is_absolute() else ROOT / args.write
    route = load_json(route_path)
    checks: dict[str, bool] = {
        "route_is_passing_runtime_inactive_candidate": (
            route.get("status") == "PASS_V9_V22_TOUCH_EMOTION_ROUTE_RUNTIME_INACTIVE" and
            route.get("runtime_resource_activated") is False and
            route.get("physical_panel_acceptance") is False and
            route.get("source_sha256") == LOCKED_SOURCE_HASH
        ),
        "logical_route_is_causal_and_affection_uses_declared_warm_art": (
            route.get("logical_route") == ["calm", "curious", "affectionate", "curious", "calm"] and
            route.get("affectionate_art_pose") == "v22_warm"
        ),
        "v9_static_entry_and_settle_are_exact": route.get("entry_settle_v9_static_difference_pixels") == {
            "entry": 0, "settle": 0
        },
        "v22_emotion_waypoints_are_exact": (
            [item.get("emotion") for item in route.get("v22_waypoints", []) if isinstance(item, dict)] ==
            ["calm", "curious", "warm", "curious", "calm"] and
            all(item.get("different_pixels") == 0 for item in route.get("v22_waypoints", []) if isinstance(item, dict))
        ),
        "forbidden_paths_remain_declared": set(route.get("forbidden", [])) == {
            "whole-face card playback", "code-drawn face", "legacy art", "custom LUT", "runtime binding"
        } and route.get("special_state_fallback") == "fail_closed",
    }
    frames = route.get("frames")
    expected_selection_policy = {
        "mode": "explicit_event_performance",
        "random_emotion_selection": False,
        "automatic_cross_emotion_cycle": False,
        "daily_auto_only_runs_daily_micro_choreography": True,
        "familiar_touch_terminal_logical_emotion": "affectionate",
        "idle_settle_returns_to": "v9_daily",
    }
    expected_performances = [
        {"id": "daily_micro", "event": "daily_auto", "frame_indices": [0, 1, 2, 3],
         "terminal_art_pose": "v9_daily"},
        {"id": "familiar_touch", "event": "familiar_touch", "frame_indices": list(range(3, 16)),
         "terminal_art_pose": "v22_warm"},
        {"id": "idle_settle", "event": "idle_settle", "frame_indices": list(range(15, 30)),
         "terminal_art_pose": "v9_daily"},
    ]
    expected_micro_choreography = {
        "daily": [0, 1, 2, 3],
        "curious": [9, 10, 19, 20],
        "affectionate": [14, 15],
        "calm": [24, 25],
    }
    components = {item.get("key"): item for item in route.get("components", []) if isinstance(item, dict)}
    images: list[Image.Image] = []
    frame_records: list[dict[str, Any]] = []
    if not isinstance(frames, list) or len(frames) < 20:
        checks["target_frames_are_registered_200x200_component_plans"] = False
        checks["every_adjacent_target_frame_visibly_changes"] = False
    else:
        valid = True
        for frame in frames:
            if not isinstance(frame, dict):
                valid = False
                continue
            path = ROOT / str(frame.get("targetPbm", ""))
            layers = frame.get("layers")
            if not path.is_file() or sha256(path) != frame.get("targetPbmSha256") or not isinstance(layers, list):
                valid = False
                continue
            with Image.open(path) as source:
                image = source.convert("1")
            keys = [layer.get("component") for layer in layers if isinstance(layer, dict)]
            layer_valid = (
                image.size == (200, 200) and len(keys) == len(layers) == len(set(keys)) and
                all(key in components for key in keys) and
                all(layer.get("source") in {"locked_v9_rig_component", "locked_v9_rig_v1_component", "v22_generated_source_panel_thresholded_crop"}
                    for layer in layers if isinstance(layer, dict)) and
                all(isinstance(frame.get("postRefreshHoldMs"), int) and frame["postRefreshHoldMs"] >= 750 for _ in [0]) and
                frame.get("phase") in {"emotion_hold", "micro_choreography", "transition"} and
                frame.get("event") in {"daily_auto", "familiar_touch", "idle_settle"}
            )
            valid = valid and layer_valid
            images.append(image)
            frame_records.append({"index": frame.get("index"), "path": frame.get("targetPbm"), "layer_count": len(layers),
                                  "target_sha256": frame.get("targetPbmSha256"), "valid": layer_valid})
        checks["target_frames_are_registered_200x200_component_plans"] = valid and len(images) == len(frames)
        checks["every_adjacent_target_frame_visibly_changes"] = (
            len(images) == len(frames) and all(pixel_distance(left, right) > 0 for left, right in zip(images, images[1:]))
        )
    def micro_window_is_valid(indices: list[int]) -> bool:
        return (
            isinstance(frames, list) and len(indices) >= 2 and
            all(0 <= index < len(frames) and isinstance(frames[index], dict) for index in indices) and
            all(frames[index].get("phase") in {"emotion_hold", "micro_choreography"} for index in indices) and
            all(pixel_distance(images[left], images[right]) > 0 for left, right in zip(indices, indices[1:]))
        )

    checks["event_driven_performances_stop_at_declared_targets_without_random_cycle"] = (
        route.get("selection_policy") == expected_selection_policy and
        route.get("performances") == expected_performances
    )
    micro_choreography = route.get("emotion_micro_choreography")
    checks["each_declared_emotion_has_registered_component_micro_choreography"] = (
        micro_choreography == expected_micro_choreography and isinstance(micro_choreography, dict) and
        all(micro_window_is_valid(indices) for indices in micro_choreography.values())
    )
    player = route.get("browser_player", {})
    player_path = ROOT / str(player.get("path", ""))
    player_text = player_path.read_text(encoding="utf-8") if player_path.is_file() else ""
    data_match = re.search(r"const DATA=(\{.*?\});const stage", player_text, re.DOTALL)
    browser_data: dict[str, Any] | None = None
    if data_match:
        try:
            browser_data = json.loads(data_match.group(1))
        except json.JSONDecodeError:
            browser_data = None
    checks["browser_player_is_bound_to_exact_target_component_plan"] = (
        player_path.is_file() and player.get("sha256") == sha256(player_path) and
        isinstance(browser_data, dict) and browser_data.get("frames") == frames and
        browser_data.get("selectionPolicy") == expected_selection_policy and
        browser_data.get("performances") == expected_performances
    )
    runtime_script = player_text.split("const stage", 1)[1] if "const stage" in player_text else ""
    checks["browser_player_is_native_200x200_dom_component_composition"] = (
        "#stage{position:relative;width:200px;height:200px" in player_text and
        "image.src='components/'+layer.component.replace(':','__')+'.png'" in runtime_script and
        "image.style.left=layer.x+'px'" in runtime_script and "image.style.top=layer.y+'px'" in runtime_script and
        "transform:scale" not in runtime_script and "targetPbm" not in runtime_script and
        "whole-face" not in runtime_script
    )
    checks["browser_player_requires_explicit_event_and_never_auto_cycles_emotions"] = (
        "const scenes=new Map(DATA.performances.map" in runtime_script and
        "if(cursor+1>=active.frame_indices.length){stop();return;}" in runtime_script and
        "const query=new URLSearchParams(window.location.search),requested=query.get('scene')" in runtime_script and
        "setInterval" not in runtime_script
    )
    v22_review = route.get("v22_owner_review", {})
    review_path = ROOT / str(v22_review.get("path", ""))
    checks["v22_source_is_bound_to_owner_accepted_inactive_bridge"] = (
        review_path.is_file() and v22_review.get("sha256") == sha256(review_path) and
        load_json(review_path).get("status") == "PASS_OWNER_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_ACCEPTED_RUNTIME_INACTIVE"
    )
    failures = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.v9_v22_touch_emotion_route_parity.v1",
        "status": "PASS_V9_V22_TOUCH_EMOTION_ROUTE_PARITY_RUNTIME_INACTIVE" if not failures else
                  "FAIL_V9_V22_TOUCH_EMOTION_ROUTE_PARITY",
        "claim_scope": "candidate_200x200_browser_target_component_plan_parity_not_runtime_binding_flash_or_physical_acceptance",
        "checks": checks,
        "failures": failures,
        "route": {"path": rel(route_path), "sha256": sha256(route_path)},
        "browser_player": {"path": player.get("path"), "sha256": player.get("sha256")},
        "frames": frame_records,
    }
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print("FAIL: V9/V22 touch emotion route parity", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: V9/V22 touch emotion browser and target component plans match -> {rel(write_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
