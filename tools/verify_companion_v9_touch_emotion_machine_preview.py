#!/usr/bin/env python3
"""Prove browser and target retain the same touch-driven Rig trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
DEFAULT_TRACE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-20260719.json"
DEFAULT_PREVIEW = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-preview-20260719.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-machine-parity-20260719.json"
DEFAULT_ACCEPTED_BASELINE = ROOT / "docs/validation/companion-v9-rig-touch-emotion-browser-accepted-baseline-20260720.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def target_layers(frame: dict[str, Any], names: dict[int, str]) -> list[dict[str, Any]]:
    layers = frame.get("layers")
    if not isinstance(layers, list):
        raise ValueError("target frame has invalid layers")
    result: list[dict[str, Any]] = []
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("target layer is malformed")
        component_id = layer.get("component_id")
        if not isinstance(component_id, int) or component_id not in names:
            raise ValueError("target layer references unregistered component")
        result.append({
            "component": names[component_id],
            "componentId": component_id,
            "baseX": layer.get("base_x"),
            "baseY": layer.get("base_y"),
            "offsetX": layer.get("offset_x"),
            "offsetY": layer.get("offset_y"),
            "compositeOp": "erase" if layer.get("composite_op") == 1 else "ink",
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=pathlib.Path, default=DEFAULT_TRACE)
    parser.add_argument("--preview", type=pathlib.Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    parser.add_argument("--accepted-baseline", type=pathlib.Path, default=DEFAULT_ACCEPTED_BASELINE)
    args = parser.parse_args()
    trace_path = args.trace if args.trace.is_absolute() else ROOT / args.trace
    preview_path = args.preview if args.preview.is_absolute() else ROOT / args.preview
    report_path = args.write if args.write.is_absolute() else ROOT / args.write
    baseline_path = (args.accepted_baseline if args.accepted_baseline.is_absolute()
                     else ROOT / args.accepted_baseline)
    trace = load_json(trace_path)
    preview = load_json(preview_path)
    layout = load_json(LAYOUT)
    names = {
        index: str(component.get("name"))
        for index, component in enumerate(layout.get("components", []), start=1)
        if isinstance(component, dict) and isinstance(component.get("name"), str)
    }
    presentation = trace.get("presentation")
    checks: dict[str, bool] = {
        "target_trace_passes_runtime_inactive_loop": trace.get("status") == "PASS_TOUCH_TO_RIG_MACHINE_LOOP_RUNTIME_INACTIVE",
        "preview_is_runtime_inactive_component_player": (
            preview.get("status") == "PASS_BROWSER_COMPONENT_PREVIEW_FROM_TARGET_TRACE" and
            preview.get("runtime_resource_activated") is False
        ),
        "locked_v9_source_is_preserved": (
            trace.get("source_sha256") == LOCKED_SOURCE_HASH and preview.get("source_sha256") == LOCKED_SOURCE_HASH
        ),
        "touch_fixture_is_single_right_tap_with_familiar_memory": trace.get("touch_fixture") == {
            "decoder_event": "tap", "start": [160, 100], "end": [161, 100],
            "attention": "right", "energy": "high", "interaction_memory": 2,
        },
        "causal_emotion_route_is_calm_curious_affectionate": trace.get("behavior", {}).get("route") == [
            "calm", "curious", "affectionate"
        ],
        "refresh_sequence_rejects_early_next_frame_and_retries_same_plan": (
            trace.get("sequencing", {}).get("next_frame_blocked_until_completion") is True and
            trace.get("sequencing", {}).get("failed_frame_retries_same_plan") is True and
            trace.get("sequencing", {}).get("visible_frame_count") == 8 and
            trace.get("sequencing", {}).get("submitted_frame_count") == 9
        ),
        "notice_score_is_coalesced_to_epaper_safe_component_keyframes": (
            isinstance(presentation, dict) and
            presentation.get("notice_score") == "daily_right" and
            presentation.get("source_score_step_count") == 18 and
            presentation.get("selected_component_keyframes") == 5 and
            presentation.get("omitted_transient_score_steps") ==
            presentation.get("source_score_step_count", 0) -
            presentation.get("selected_component_keyframes", 0) and
            presentation.get("minimum_post_refresh_hold_ms") == 750 and
            presentation.get("all_visible_frames_require_prior_refresh_completion") is True
        ),
        "special_system_states_remain_fail_closed": trace.get("fail_closed") == [
            "menu_hold", "recording_active", "charging", "error", "upgrade_active"
        ],
        "forbidden_paths_are_preserved": trace.get("forbidden_runtime_paths") == [
            "whole-face card loop", "code-drawn face", "legacy art", "custom LUT"
        ],
    }
    target_frames = trace.get("frames")
    browser_trace = preview.get("browser_trace", {})
    browser_frames = browser_trace.get("frames") if isinstance(browser_trace, dict) else None
    parity_records: list[dict[str, Any]] = []
    if not isinstance(target_frames, list) or not isinstance(browser_frames, list):
        checks["browser_target_frame_count_matches"] = False
        checks["browser_target_state_component_offset_order_matches"] = False
    else:
        checks["browser_target_frame_count_matches"] = len(target_frames) == len(browser_frames) == 8
        exact = True
        for target, browser in zip(target_frames, browser_frames):
            if not isinstance(target, dict) or not isinstance(browser, dict):
                exact = False
                break
            expected_state = {
                "scene": target.get("scene"), "emotion": target.get("emotion"),
                "attention": target.get("attention"), "energy": target.get("energy"),
                "interactionMemory": target.get("interaction_memory"), "phase": target.get("phase"),
            }
            expected_layers = target_layers(target, names)
            actual_layers = browser.get("layers")
            browser_layer_projection = [
                {
                    "component": layer.get("component"),
                    "componentId": layer.get("componentId"),
                    "baseX": layer.get("baseX"),
                    "baseY": layer.get("baseY"),
                    "offsetX": layer.get("offsetX"),
                    "offsetY": layer.get("offsetY"),
                    "compositeOp": layer.get("compositeOp"),
                }
                for layer in actual_layers
            ] if isinstance(actual_layers, list) and all(isinstance(layer, dict) for layer in actual_layers) else []
            layer_match = browser_layer_projection == expected_layers
            state_match = browser.get("state") == expected_state
            frame_match = (browser.get("index") == target.get("index") and
                           browser.get("kind") == target.get("kind") and
                           browser.get("routeIndex") == target.get("route_index") and
                           browser.get("scorePhase") == target.get("score_phase") and
                           browser.get("scoreStepIndex") == target.get("score_step_index") and
                           browser.get("postRefreshHoldMs") == target.get("post_refresh_hold_ms"))
            exact = exact and layer_match and state_match and frame_match
            parity_records.append({
                "index": target.get("index"), "state_match": state_match,
                "component_offset_order_match": layer_match, "frame_metadata_match": frame_match,
            })
        checks["browser_target_state_component_offset_order_matches"] = exact
    expected_frames = [
        ("performance", "entry", "daily", "calm"),
        ("performance", "lead", "daily", "calm"),
        ("performance", "response", "daily", "calm"),
        ("performance", "accent", "daily", "calm"),
        ("performance", "release", "daily", "calm"),
        ("bridge", None, "daily", "curious"),
        ("target", None, "daily", "affectionate"),
        ("settle", None, "daily", "calm"),
    ]
    checks["frame_semantics_follow_causal_route"] = isinstance(target_frames, list) and [
        (frame.get("kind"), frame.get("score_phase"), frame.get("scene"), frame.get("emotion"))
        for frame in target_frames if isinstance(frame, dict)
    ] == expected_frames
    player = preview.get("browser_player", {})
    player_path = ROOT / str(player.get("path", ""))
    checks["browser_player_hash_is_bound"] = (
        player_path.is_file() and player.get("sha256") == sha256(player_path) and
        re.search(r"const DATA = \{.*?\};", player_path.read_text(encoding="utf-8"), re.DOTALL) is not None
    )
    checks["browser_player_is_single_causal_run_with_target_hold_timing"] = (
        player_path.is_file() and
        "if(index+1>=DATA.frames.length){stop();return;}" in player_path.read_text(encoding="utf-8") and
        "postRefreshHoldMs" in player_path.read_text(encoding="utf-8")
    )
    player_text = player_path.read_text(encoding="utf-8") if player_path.is_file() else ""
    static_composition = preview.get("native_static_composition", {})
    static_differences = static_composition.get("frame_differences", []) if isinstance(static_composition, dict) else []
    checks["entry_and_settle_reconstruct_accepted_daily_static_composition"] = (
        isinstance(static_composition, dict) and
        static_composition.get("baseline", {}).get("sha256") ==
        "B3847DF9CE2D20693C60C9CC7BC1EC8D8B8A3E23641F4521EE71508ABE13CB9E" and
        static_differences == [
            {"frame_index": 0, "different_pixels": 0},
            {"frame_index": 7, "different_pixels": 0},
        ]
    )
    checks["browser_presents_native_200x200_component_composition"] = (
        "id=\"stage\"" in player_text and
        "width:200px;height:200px;background:#fff" in player_text and
        "img.style.left=layer.x+'px'" in player_text and
        "img.style.top=layer.y+'px'" in player_text and
        "layer.x*2" not in player_text and "layer.y*2" not in player_text and
        "transform:scale" not in player_text
    )
    accepted_baseline: dict[str, Any] | None = None
    if baseline_path.is_file():
        accepted_baseline = load_json(baseline_path)
        expected_frame_hashes = [item.get("sha256") for item in accepted_baseline.get("frames", [])
                                 if isinstance(item, dict)]
        current_frame_hashes = [item.get("sha256") for item in preview.get("frames", [])
                                if isinstance(item, dict)]
        checks["accepted_browser_preview_regression_matches"] = (
            accepted_baseline.get("status") ==
            "PASS_ACCEPTED_TOUCH_EMOTION_BROWSER_PREVIEW_RUNTIME_INACTIVE" and
            accepted_baseline.get("source_sha256") == LOCKED_SOURCE_HASH and
            accepted_baseline.get("browser_player", {}).get("sha256") == player.get("sha256") and
            expected_frame_hashes == current_frame_hashes and
            accepted_baseline.get("component_layer_count") == preview.get("component_layer_count")
        )
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.v9_rig_touch_emotion_machine_parity.v1",
        "status": "PASS_TOUCH_EMOTION_BROWSER_TARGET_PARITY_RUNTIME_INACTIVE" if not failures else "FAIL_TOUCH_EMOTION_BROWSER_TARGET_PARITY",
        "claim_scope": "simulated_touch_to_runtime_inactive_component_rig_trace_not_flash_or_physical_acceptance",
        "checks": checks,
        "failures": failures,
        "target_trace": {"path": rel(trace_path), "sha256": sha256(trace_path)},
        "browser_preview": {"path": rel(preview_path), "sha256": sha256(preview_path)},
        "accepted_browser_baseline": (
            {"status": "not_yet_accepted"} if accepted_baseline is None else
            {"path": rel(baseline_path), "sha256": sha256(baseline_path),
             "status": accepted_baseline.get("status")}
        ),
        "parity_frames": parity_records,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print("FAIL: touch/emotion browser-target parity", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: touch/emotion browser-target parity -> {rel(report_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
