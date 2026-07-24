#!/usr/bin/env python3
"""Verify V23 special-expression performances are component-only and causal."""

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
DEFAULT_ROUTE = ROOT / "docs/validation/companion-v23-special-expression-component-performance-preview-20260720.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v23-special-expression-component-performance-parity-20260720.json"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SPECIAL_EVENTS = {
    "menu_active": ("menu_hold", "menu_exit"),
    "recording_active": ("recording_active", "recording_stop_or_cancel"),
    "charging_active": ("charging", "charging_unplug"),
}
ALLOWED_SOURCES = {"locked_v9_rig_component", "v23_generated_source_thresholded_normalization"}


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
            route.get("status") == "PASS_V23_SPECIAL_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE"
            and route.get("runtime_resource_activated") is False
            and route.get("physical_panel_acceptance") is False
            and route.get("locked_v9_source_sha256") == LOCKED_V9_SHA256
            and route.get("active_candidate_binding") == "forbidden"
        ),
        "selection_policy_is_explicit_and_fail_closed": route.get("selection_policy") == {
            "mode": "explicit_event_performance",
            "random_state_selection": False,
            "automatic_cross_state_cycle": False,
            "daily_auto_only_runs_daily_micro_choreography": True,
            "special_state_exit_returns_to": "v9_daily",
            "unavailable_special_states": ["upgrade", "sleep", "error"],
            "unavailable_special_state_policy": "fail_closed",
        },
        "daily_entry_and_final_settle_are_exact_v9": route.get("daily_entry_settle_difference_pixels") == {"entry": 0, "final_settle": 0},
        "special_holds_are_exact_component_reassemblies": route.get("special_state_reassembly_differences_pixels") == {
            "menu_active": 0,
            "recording_active": 0,
            "charging_active": 0,
        },
        "forbidden_paths_remain_declared": set(route.get("forbidden", [])) == {
            "whole-face card playback", "code-drawn face", "legacy art", "custom LUT", "runtime binding"
        },
    }
    frames = route.get("frames")
    components = {item.get("key"): item for item in route.get("components", []) if isinstance(item, dict)}
    images: dict[int, Image.Image] = {}
    frame_records: list[dict[str, object]] = []
    target_valid = isinstance(frames, list) and len(frames) == 26
    if isinstance(frames, list):
        for index, frame in enumerate(frames):
            if not isinstance(frame, dict):
                target_valid = False
                continue
            target_path = ROOT / str(frame.get("targetPbm", ""))
            layers = frame.get("layers")
            frame_valid = (
                frame.get("index") == index
                and target_path.is_file()
                and sha256(target_path) == frame.get("targetPbmSha256")
                and isinstance(layers, list)
                and isinstance(frame.get("postRefreshHoldMs"), int)
                and int(frame["postRefreshHoldMs"]) >= 180
                and frame.get("phase") in {"entry", "prepare", "transition", "micro_choreography", "emotion_hold", "release", "settle"}
            )
            if frame_valid:
                with Image.open(target_path) as raw:
                    image = raw.convert("1")
                keys = [layer.get("component") for layer in layers if isinstance(layer, dict)]
                frame_valid = (
                    image.size == (200, 200)
                    and len(keys) == len(layers) == len(set(keys))
                    and all(key in components for key in keys)
                    and all(layer.get("source") in ALLOWED_SOURCES for layer in layers if isinstance(layer, dict))
                    and all(0 <= int(layer.get("x", -1)) < 200 and 0 <= int(layer.get("y", -1)) < 200 for layer in layers if isinstance(layer, dict))
                )
                images[index] = image
            target_valid = target_valid and frame_valid
            frame_records.append({"index": index, "segment": frame.get("segment"), "valid": frame_valid, "targetPbm": frame.get("targetPbm")})
    checks["all_target_frames_are_registered_native_200x200_component_plans"] = target_valid and len(images) == 26

    performances = route.get("performances")
    performance_valid = isinstance(performances, list) and len(performances) == 4
    if isinstance(performances, list):
        by_id = {item.get("id"): item for item in performances if isinstance(item, dict)}
        daily = by_id.get("daily_micro", {})
        performance_valid = performance_valid and daily.get("event") == "daily_auto" and daily.get("frame_indices") == [0, 1, 2, 3] and daily.get("terminal_art_pose") == "v9_daily"
        for pose, (event, exit_event) in SPECIAL_EVENTS.items():
            record = by_id.get(pose, {})
            indices = record.get("frame_indices", [])
            performance_valid = performance_valid and (
                record.get("event") == event
                and record.get("exit_event") == exit_event
                and record.get("terminal_art_pose") == "v9_daily"
                and isinstance(indices, list)
                and len(indices) >= 7
                and all(isinstance(item, int) and item in images for item in indices)
                and all(pixel_distance(images[left], images[right]) > 0 for left, right in zip(indices, indices[1:]))
            )
            if isinstance(indices, list) and all(item in images for item in indices):
                state_frames = [frames[item] for item in indices if isinstance(frames[item], dict)]
                has_face_first = any(
                    frame.get("phase") == "transition"
                    and any(layer.get("source") == "v23_generated_source_thresholded_normalization" and layer.get("role") in {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}
                            for layer in frame.get("layers", []) if isinstance(layer, dict))
                    for frame in state_frames
                )
                has_secondary_accent = any(
                    frame.get("phase") in {"micro_choreography", "emotion_hold"}
                    and any(layer.get("source") == "v23_generated_source_thresholded_normalization" and layer.get("role") in {"accent", "left_listening_arc", "right_listening_arc"}
                            for layer in frame.get("layers", []) if isinstance(layer, dict))
                    for frame in state_frames
                )
                performance_valid = performance_valid and has_face_first and has_secondary_accent
    checks["each_special_event_is_a_face_first_coordinated_pose_with_a_secondary_accent"] = performance_valid

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
    checks["browser_player_uses_exact_target_component_plan"] = (
        player_path.is_file()
        and player.get("sha256") == sha256(player_path)
        and isinstance(browser_data, dict)
        and browser_data.get("frames") == frames
        and browser_data.get("performances") == performances
        and browser_data.get("selectionPolicy") == route.get("selection_policy")
    )
    runtime = player_text.split("const stage", 1)[1] if "const stage" in player_text else ""
    checks["browser_player_is_native_dom_component_composition"] = (
        "#stage{position:relative;width:200px;height:200px" in player_text
        and "image.src='components/'+layer.component.replaceAll(':','__')+'.png'" in runtime
        and "image.style.left=layer.x+'px'" in runtime
        and "image.style.top=layer.y+'px'" in runtime
        and "targetPbm" not in runtime
        and "setInterval" not in runtime
        and "if(cursor+1>=active.frame_indices.length){stop();return;}" in runtime
    )
    asset_dir = player_path.parent / "components"
    checks["browser_component_assets_exist_for_every_used_component"] = (
        asset_dir.is_dir()
        and all((asset_dir / f"{key.replace(':', '__')}.png").is_file() for key in components)
    )
    failures = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.v23_special_expression_component_performance_parity.v1",
        "status": "PASS_V23_SPECIAL_COMPONENT_PERFORMANCE_PARITY_RUNTIME_INACTIVE" if not failures else "FAIL_V23_SPECIAL_COMPONENT_PERFORMANCE_PARITY",
        "claim_scope": "native_200x200_browser_target_component_plan parity only; no runtime binding, flash, panel output, or physical acceptance",
        "route": {"path": rel(route_path), "sha256": sha256(route_path)},
        "browser_player": {"path": player.get("path"), "sha256": player.get("sha256")},
        "checks": checks,
        "failures": failures,
        "frames": frame_records,
    }
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if failures:
        print("FAIL: V23 special-expression performance parity", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: V23 special-expression browser and target component plans match -> {rel(write_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
