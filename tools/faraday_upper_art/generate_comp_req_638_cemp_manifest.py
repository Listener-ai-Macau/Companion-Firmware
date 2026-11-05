#!/usr/bin/env python3
"""Create an external-NOR CEMP manifest from the current browser frame map."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source_path = args.source_pack_manifest.resolve()
    output_path = args.output.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_manifest_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
    if source.get("status") != "PASS" or source.get("format", {}).get("width") != 200:
        raise ValueError("source pack must be a passing 200x200 manifest")

    state_by_id = {state["id"]: state for state in source["states"]}
    state_by_unique: dict[int, dict] = {}
    for state in source["states"]:
        state_by_unique.setdefault(int(state["unique_frame_index"]), state)
    clips = []
    for unique_index in sorted(state_by_unique):
        state = state_by_unique[unique_index]
        clips.append({
            "name": f"frame_{unique_index:04d}",
            "loop_start": 0,
            "loop_end": 1,
            "frames": [{
                "source": f"../{state['pbm_file']}",
                "duration_ms": 480,
                "dirty": [0, 0, 0, 0],
            }],
        })

    # The browser state ids are the canonical authored names.  These aliases
    # are only a transport adapter for the existing WB55 player, and point to
    # the exact same PBMs; they do not create a second art representation.
    alias_specs = {
        "idle": [
            "expression_calm_v0_0_orient",
            "expression_calm_v0_0_follow",
            "expression_calm_v0_0_settle",
        ],
        "touch": [
            "expression_delighted_v0_0_orient",
            "expression_delighted_v0_0_follow",
            "expression_delighted_v0_0_settle",
        ],
        "swipe_left": ["expression_playful_v0_0_orient"],
        "swipe_right": ["expression_bashful_v1_0_orient"],
        "swipe_up": ["expression_curious_v0_0_orient"],
        "swipe_down": ["expression_focused_v0_0_orient"],
        "listening": ["expression_curious_v0_0_hold"],
        "thinking": ["expression_thoughtful_v0_0_hold"],
        "speaking": ["expression_warm_v0_0_hold"],
        "happy": ["expression_delighted_v0_0_hold"],
        "sleepy": ["expression_sleepy_v0_0_hold"],
        "recording": ["recording_0", "recording_1", "recording_2"],
        "speaker": ["speaker_0", "speaker_1", "speaker_2"],
        "charging": ["charging_0", "charging_1", "charging_2"],
        "sync_complete": ["expression_delighted_v2_0_hold"],
        "low_battery": ["expression_alert_v0_0_hold"],
        "error": ["expression_alert_v0_0_accent"],
        "menu_hold": ["menu_mode_0"],
        "saving": ["upgrade_progress_0_5"],
        "saved": ["upgrade_progress_1"],
        "sleep": ["expression_sleepy_v0_0_hold"],
        "wake": ["expression_calm_v0_0_orient"],
        "attention.center": ["expression_curious_v0_0_follow"],
        "attention.up_left": ["expression_bashful_v1_0_follow"],
        "attention.up": ["expression_curious_v0_0_follow"],
        "attention.up_right": ["expression_focused_v0_0_follow"],
        "attention.left": ["expression_warm_v0_0_follow"],
        "attention.right": ["expression_delighted_v2_0_follow"],
        "attention.down_left": ["expression_bashful_v1_0_follow"],
        "attention.down": ["expression_sleepy_v0_0_follow"],
        "attention.down_right": ["expression_playful_v0_0_follow"],
    }
    for alias, state_ids in alias_specs.items():
        frames = []
        for state_id in state_ids:
            state = state_by_id.get(state_id)
            if state is None:
                raise ValueError(f"missing alias source state: {state_id}")
            frames.append({
                "source": f"../{state['pbm_file']}",
                "duration_ms": (
                    1440 if alias == "charging" and len(frames) in (0, 1)
                    else 480
                ),
                "dirty": [0, 0, 0, 0],
            })
        clips.append({
            "name": alias,
            "loop_start": 0,
            "loop_end": len(frames),
            "frames": frames,
        })

    tap_transition_clips = 0
    tap_edge_clips = 0
    phase_order = {
        "orient": 0,
        "anticipate": 1,
        "accent": 2,
        "follow": 3,
        "settle": 4,
    }
    tap_zones = sorted({
        state["zone"]
        for state in source["states"]
        if state["kind"] == "tap_transition"
    })
    for zone in tap_zones:
        transition_states = sorted(
            (
                state
                for state in source["states"]
                if state["kind"] == "tap_transition"
                and state["zone"] == zone
            ),
            key=lambda state: (
                int(state["route_index"]),
                phase_order[state["phase"]],
            ),
        )
        frames = [{
            "source": f"../{state['pbm_file']}",
            "duration_ms": int(state["dwell_commits"]) * 480,
            "dirty": [0, 0, 0, 0],
        } for state in transition_states]
        clips.append({
            "name": f"tap.transition.{zone}",
            "loop_start": 0,
            "loop_end": len(frames),
            "frames": frames,
        })
        tap_transition_clips += 1

    edge_keys = sorted({
        (
            state["source_family"],
            state["target_family"],
            state["zone"],
        )
        for state in source["states"]
        if state["kind"] == "tap_edge"
    })
    for source_family, target_family, zone in edge_keys:
        edge_states = sorted(
            (
                state
                for state in source["states"]
                if state["kind"] == "tap_edge"
                and state["source_family"] == source_family
                and state["target_family"] == target_family
                and state["zone"] == zone
            ),
            key=lambda state: phase_order[state["phase"]],
        )
        if [state["phase"] for state in edge_states] != list(phase_order):
            raise ValueError(
                "incomplete browser tap edge: "
                f"{source_family}->{target_family}/{zone}"
            )
        clips.append({
            "name": (
                f"tap.edge.{source_family}.{target_family}.{zone}"
            ),
            "loop_start": 0,
            "loop_end": len(edge_states),
            "frames": [{
                "source": f"../{state['pbm_file']}",
                "duration_ms": int(state["dwell_commits"]) * 480,
                "dirty": [0, 0, 0, 0],
            } for state in edge_states],
        })
        tap_edge_clips += 1

    pointer_states = [
        state for state in source["states"]
        if state["kind"] == "pointer_follow"
    ]
    pointer_by_key = {
        (
            state["family"],
            int(state["gravity_x"]),
            int(state["gravity_y"]),
        ): state
        for state in pointer_states
    }
    for family in sorted({state["family"] for state in pointer_states}):
        for gravity_y in range(-4, 5, 2):
            for gravity_x in range(-4, 5, 2):
                state = pointer_by_key.get((family, gravity_x, gravity_y))
                if state is None:
                    raise ValueError(
                        f"incomplete pointer grid: {family}/{gravity_x}/{gravity_y}"
                    )

    manifest = {
        "schema": "companion.emote_asset_pack_manifest.v1",
        "name": "comp_req_638_browser_epaper_external_nor",
        "revision": 638,
        "priority": 638,
        "profile": {
            "width": 200,
            "height": 200,
            "stride_bytes": 25,
            "pixel_format": "mono_1bpp_white_is_one_msb",
        },
        "encoding": "packbits",
        "source": {
            "browser_page": source["source"]["page_path"],
            "browser_page_sha256": source["source"]["page_sha256"],
            "source_pack_manifest_sha256": source_manifest_sha256,
            "state_count": len(source["states"]),
            "canonical_frame_clip_count": len(state_by_unique),
            "state_to_canonical_frame": {
                state["id"]: int(state["unique_frame_index"])
                for state in source["states"]
            },
            "clip_count": len(clips),
            "frame_count": sum(len(clip["frames"]) for clip in clips),
            "compatibility_alias_count": len(alias_specs),
            "tap_transition_clip_count": tap_transition_clips,
            "tap_edge_clip_count": tap_edge_clips,
            "pointer_follow_state_count": len(pointer_states),
            "pointer_follow_clip_count": 0,
            "pointer_follow_transport": "canonical_state_map",
            "pointer_follow_grid": [5, 5],
            "pointer_follow_source_grid": [9, 9],
            "pointer_return_clip_count": 0,
            "pointer_return_transport": "reuse_follow_grid_half_then_center",
            "unique_frame_count": source["invariants"]["unique_frame_count"],
        },
        "clips": clips,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": "PASS_MANIFEST_GENERATED",
        "path": output_path.as_posix(),
        "clips": len(clips),
        "page_sha256": source["source"]["page_sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
