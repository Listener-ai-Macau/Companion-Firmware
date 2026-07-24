#!/usr/bin/env python3
"""Render V32 component-only representative functional-silhouette performances at native 200x200."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from PIL import Image

import render_companion_v24_glance_readable_special_expression_performances as rig


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
V9_RENDER = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
V9_DAILY = ROOT / "docs/validation/artifacts/companion-v9-expression-rig-daily-focus-accepted-dynamic-baseline-20260718/story-phases/daily_right_entry.pbm"
V32_EXPORT_GATE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-export-gate-20260720.json"
V32_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v32-representative-functional-silhouette-special-expression-source/candidate/x/l.json"
DEFAULT_ARTIFACT_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v32-representative-functional-silhouette-special-expression-source/candidate/pf"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-performance-preview-20260720.json"
CANVAS = (200, 200)
IDENTITY_NAMES = ("left_eye_open", "right_eye_open", "left_eye_highlight_open", "right_eye_highlight_open", "left_eye_sparkle_open", "right_eye_sparkle_open", "nose_default")
BASE_FACE_ROLES = {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"}
OBJECT_ROLES = {
    "menu_active": {"left_hollow_page_tab", "active_hollow_notched_page_tab", "right_hollow_page_tab"},
    "recording_active": {"left_thin_receiver_cuff", "right_thin_receiver_cuff", "single_pickup_dot"},
    "charging_active": {"small_open_side_coupler", "thin_continuous_short_tether", "small_hollow_slotted_energy_dock"},
}
OBJECT_ENTRY_ROLES = {
    "menu_active": {"left_hollow_page_tab"},
    "recording_active": {"left_thin_receiver_cuff", "right_thin_receiver_cuff"},
    "charging_active": {"small_open_side_coupler"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    rig.require(isinstance(value, dict), f"{rel(path)} is not a JSON object")
    return value


def load_components() -> tuple[dict[int, rig.Component], dict[str, rig.Component], dict[str, list[rig.Component]], dict[str, Any]]:
    v9_layout = load_json(V9_LAYOUT)
    v9_render = load_json(V9_RENDER)
    v32_layout = load_json(V32_LAYOUT)
    rig.require(v9_layout.get("source_baseline", {}).get("sha256") == LOCKED_V9_SHA256, "V9 layout lost locked source")
    rig.require(v32_layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256, "V32 layout lost locked source")
    rig.require(v32_layout.get("runtime_resource_activated") is False and v32_layout.get("active_candidate_binding") == "forbidden", "V32 layout is not inactive/unbound")
    masks = {str(item.get("name")): item.get("component_mask") for item in v9_render.get("components", []) if isinstance(item, dict)}
    v9_by_id: dict[int, rig.Component] = {}
    v9_by_name: dict[str, rig.Component] = {}
    for index, record in enumerate(v9_layout.get("components", []), start=1):
        rig.require(isinstance(record, dict), "V9 layout component is malformed")
        name = str(record.get("name", ""))
        mask = masks.get(name)
        rig.require(isinstance(mask, str), f"V9 component mask is missing: {name}")
        component = rig.component_from_record(
            f"v9:{name}", name, str(record.get("role", "")), "locked_v9_rig_component", ROOT / mask,
            sha256(ROOT / mask), list(record.get("base_position", [])), dict(record.get("offset_range", {})),
            int(record.get("z_index", 0)), str(record.get("composite_op", "ink")),
        )
        v9_by_id[index] = component
        v9_by_name[name] = component
    special_by_pose: dict[str, list[rig.Component]] = {}
    for pose, records in v32_layout.get("special_pose_components", {}).items():
        rig.require(isinstance(records, dict), f"V32 {pose} component map is malformed")
        components: list[rig.Component] = []
        for name, record in records.items():
            rig.require(isinstance(record, dict), f"V32 {pose} component is malformed")
            components.append(rig.component_from_record(
                f"v32:{name}", str(record.get("name", "")), str(record.get("role", "")), str(record.get("source", "")),
                ROOT / str(record.get("mask", "")), str(record.get("mask_sha256", "")), list(record.get("base_position", [])),
                dict(record.get("offset_range", {})), int(record.get("z_index", 0)), str(record.get("composite_op", "ink")),
            ))
        special_by_pose[str(pose)] = components
    return v9_by_id, v9_by_name, special_by_pose, v32_layout


def face_layers(v9_by_name: dict[str, rig.Component], special_by_pose: dict[str, list[rig.Component]], pose: str,
                roles: set[str], highlight_offset: tuple[int, int] = (0, 0),
                face_offsets: dict[str, tuple[int, int]] | None = None) -> list[rig.Layer]:
    result: list[rig.Layer] = []
    for name in IDENTITY_NAMES:
        component = v9_by_name[name]
        offset = highlight_offset if component.role in {"left_highlight", "right_highlight"} else (0, 0)
        result.append(rig.Layer(component, component.base[0] + offset[0], component.base[1] + offset[1]))
    for component in special_by_pose[pose]:
        if component.role not in roles:
            continue
        offset = (face_offsets or {}).get(component.role, (0, 0))
        result.append(rig.Layer(component, component.base[0] + offset[0], component.base[1] + offset[1]))
    return rig.sorted_layers(result)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--write", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    report_path = args.write if args.write.is_absolute() else ROOT / args.write
    export_gate = load_json(V32_EXPORT_GATE)
    rig.require(export_gate.get("status") == "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_EXPORT_UNBOUND", "V32 component export gate is not PASS")
    rig.require(export_gate.get("runtime_resource_activated") is False, "V32 export gate unexpectedly activated runtime")
    v9_by_id, v9_by_name, special_by_pose, v32_layout = load_components()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    component_dir = artifact_dir / "c"
    component_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    used: dict[str, rig.Component] = {}

    def append(segment: str, logical_state: str, art_pose: str, layers: list[rig.Layer], event: str, phase: str, hold: int, *, allow_event_entry_repeat: bool = False) -> int:
        ordered = rig.sorted_layers(layers)
        image = rig.compose(ordered)
        if images and not allow_event_entry_repeat:
            rig.require(rig.image_distance(images[-1], image) > 0, f"{segment} repeated its preceding component frame")
        index = len(frames)
        target = artifact_dir / f"frame-{index:02d}-{segment}.pbm"
        image.save(target, format="PPM")
        for layer in ordered:
            used[layer.component.key] = layer.component
        frames.append({
            "index": index,
            "segment": segment,
            "logicalState": logical_state,
            "artPose": art_pose,
            "event": event,
            "phase": phase,
            "postRefreshHoldMs": hold,
            "layers": [rig.public_layer(layer) for layer in ordered],
            "targetPbm": rel(target),
            "targetPbmSha256": sha256(target),
        })
        images.append(image)
        return index

    daily = rig.v9_daily_layers(v9_by_id)
    with Image.open(V9_DAILY) as raw:
        daily_static = raw.convert("1")
    rig.require(rig.image_distance(rig.compose(daily), daily_static) == 0, "V9 component plan does not reconstruct accepted Daily")
    append("daily_entry", "daily", "v9_daily", daily, "daily_auto", "emotion_hold", 900)
    append("daily_notice", "daily", "v9_daily", rig.move_roles(daily, {"left_highlight": (1, -1), "right_highlight": (1, -1)}), "daily_auto", "micro_choreography", 240)
    append("daily_settle", "daily", "v9_daily", daily, "daily_auto", "emotion_hold", 1050)
    performances: list[dict[str, Any]] = [{"id": "daily_micro", "event": "daily_auto", "frame_indices": [0, 1, 2], "inspect_frame_index": 0, "terminal_art_pose": "v9_daily"}]
    reassembly_differences: dict[str, int] = {}

    def add_special(pose: str, entry_event: str, exit_event: str, action: str) -> None:
        start = len(frames)
        object_roles = OBJECT_ROLES[pose]
        full_roles = BASE_FACE_ROLES | object_roles
        append(f"{pose}_daily_entry", "daily", "v9_daily", daily, entry_event, "entry", 720, allow_event_entry_repeat=True)
        append(f"{pose}_notice", "daily", "v9_daily", rig.move_roles(daily, {"left_highlight": (1, -1), "right_highlight": (1, -1)}), entry_event, "prepare", 300)
        brows = face_layers(v9_by_name, special_by_pose, pose, {"left_brow", "right_brow"}, (1, -1), {"left_brow": (0, -1), "right_brow": (0, -1)})
        append(f"{pose}_brows_arrive", pose, pose, brows, entry_event, "face_arrival", 320)
        brow_mouth = face_layers(v9_by_name, special_by_pose, pose, {"left_brow", "right_brow", "mouth"}, (1, -1), {"mouth": (0, 1)})
        append(f"{pose}_mouth_arrive", pose, pose, brow_mouth, entry_event, "face_arrival", 320)
        object_arrive = face_layers(v9_by_name, special_by_pose, pose, {"left_brow", "right_brow", "mouth", *OBJECT_ENTRY_ROLES[pose]}, (1, -1))
        append(f"{pose}_object_arrive", pose, pose, object_arrive, entry_event, "object_arrival", 280)
        if action == "menu_scan":
            object_center = face_layers(
                v9_by_name,
                special_by_pose,
                pose,
                {"left_brow", "right_brow", "mouth", "left_hollow_page_tab", "active_hollow_notched_page_tab"},
                (1, -1),
            )
            append(f"{pose}_active_page_arrive", pose, pose, object_center, entry_event, "object_arrival", 240)
        object_connect = face_layers(v9_by_name, special_by_pose, pose, {"left_brow", "right_brow", "mouth", *object_roles})
        append(f"{pose}_object_connect", pose, pose, object_connect, entry_event, "object_connection", 280)
        full = face_layers(v9_by_name, special_by_pose, pose, full_roles)
        append(f"{pose}_face_settle", pose, pose, full, entry_event, "face_settle", 420)
        if action == "menu_scan":
            append(f"{pose}_scan_left", pose, pose, face_layers(v9_by_name, special_by_pose, pose, full_roles, (-2, 0), {"left_hollow_page_tab": (-1, 0), "active_hollow_notched_page_tab": (-1, 0), "right_hollow_page_tab": (-1, 0)}), entry_event, "micro_choreography", 300)
            append(f"{pose}_scan_center", pose, pose, full, entry_event, "micro_choreography", 300)
            target_layers = face_layers(v9_by_name, special_by_pose, pose, full_roles, (3, 0), {"left_hollow_page_tab": (1, 0), "active_hollow_notched_page_tab": (0, -1), "right_hollow_page_tab": (1, 0)})
            target_index = append(f"{pose}_decision_hold", pose, pose, target_layers, entry_event, "emotion_hold", 1350)
        elif action == "recording_ack":
            append(f"{pose}_listen_pulse", pose, pose, face_layers(v9_by_name, special_by_pose, pose, full_roles, (1, -1), {"left_thin_receiver_cuff": (0, -1), "right_thin_receiver_cuff": (1, 0), "single_pickup_dot": (0, -1), "mouth": (0, -1)}), entry_event, "micro_choreography", 320)
            target_index = append(f"{pose}_listen_hold", pose, pose, full, entry_event, "emotion_hold", 1350)
        else:
            append(f"{pose}_recovery_breathe", pose, pose, face_layers(v9_by_name, special_by_pose, pose, full_roles, (1, -1), {"left_brow": (0, -1), "right_brow": (0, -1), "mouth": (0, -1), "small_open_side_coupler": (1, 0), "thin_continuous_short_tether": (1, 0), "small_hollow_slotted_energy_dock": (0, -1)}), entry_event, "micro_choreography", 360)
            target_index = append(f"{pose}_recovery_hold", pose, pose, full, entry_event, "emotion_hold", 1350)
        target_path = ROOT / str(v32_layout["states"][pose]["reassembly"])
        with Image.open(target_path) as raw:
            reassembly_differences[pose] = rig.image_distance(rig.compose(full), raw.convert("1"))
        rig.require(reassembly_differences[pose] == 0, f"{pose} full component state drifted from export reassembly")
        release_face = face_layers(v9_by_name, special_by_pose, pose, {"left_brow", "right_brow", "left_cheek", "right_cheek", "mouth"})
        append(f"{pose}_object_release", pose, pose, release_face, exit_event, "release", 260)
        append(f"{pose}_release_face", pose, pose, brow_mouth, exit_event, "release", 340)
        append(f"{pose}_daily_settle", "daily", "v9_daily", daily, exit_event, "settle", 900)
        performances.append({"id": pose, "event": entry_event, "exit_event": exit_event, "frame_indices": list(range(start, len(frames))), "inspect_frame_index": target_index, "terminal_art_pose": "v9_daily"})

    add_special("menu_active", "menu_hold", "menu_exit", "menu_scan")
    add_special("recording_active", "recording_active", "recording_stop_or_cancel", "recording_ack")
    add_special("charging_active", "charging", "charging_unplug", "charging_release")
    rig.require(rig.image_distance(images[-1], daily_static) == 0, "V32 performances do not settle to exact V9 Daily")
    policy = {
        "mode": "explicit_event_performance",
        "random_state_selection": False,
        "automatic_cross_state_cycle": False,
        "special_state_exit_returns_to": "v9_daily",
        "unavailable_special_states": ["upgrade", "sleep", "error"],
        "unavailable_special_state_policy": "fail_closed",
    }
    component_assets: dict[str, str] = {}
    for index, component in enumerate(sorted(used.values(), key=lambda item: item.key)):
        asset = f"c/{index:02d}.png"
        rig.export_layer(component, artifact_dir / asset)
        component_assets[component.key] = asset
    browser_data = {"schema": "companion.v32_representative_functional_silhouette_special_expression_component_browser_trace.v1", "runtimeResourceActivated": False, "selectionPolicy": policy, "componentAssets": component_assets, "performances": performances, "frames": frames}
    player = artifact_dir / "player.html"
    rig.write_player(player, browser_data)
    player_text = player.read_text(encoding="utf-8").replace("V24", "V32")
    player_text = player_text.replace(
        "image.src='components/'+layer.component.replaceAll(':','__')+'.png';",
        "image.src=DATA.componentAssets[layer.component];",
    )
    player_text = player_text.replace(
        "<p>Each choice plays one explicit event performance and stops at Daily. The stage is a native 200x200 component compositor; it does not play whole-face cards.</p>",
        "",
    )
    player.write_text(player_text, encoding="utf-8")
    report = {
        "schema": "companion.v32_representative_functional_silhouette_special_expression_component_performance_preview.v1",
        "status": "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE",
        "claim_scope": "candidate component choreography and identical browser/target PBM plan only; not a behavior binding, CRIG, firmware flash, panel output, or physical acceptance",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "source_component_export_gate": rel(V32_EXPORT_GATE),
        "runtime_resource_activated": False,
        "physical_panel_acceptance": False,
        "selection_policy": policy,
        "performances": performances,
        "special_state_reassembly_differences_pixels": reassembly_differences,
        "daily_entry_settle_difference_pixels": {"entry": rig.image_distance(images[0], daily_static), "final_settle": rig.image_distance(images[-1], daily_static)},
        "frames": frames,
        "browser_player": {"path": rel(player), "sha256": sha256(player)},
        "component_count": len(used),
        "components": [{"key": component.key, "name": component.name, "role": component.role, "source": component.source, "mask": rel(component.mask_path), "mask_sha256": component.mask_sha256} for component in sorted(used.values(), key=lambda item: item.key)],
        "forbidden": ["whole-face card playback", "code-drawn face", "legacy art", "custom LUT", "runtime binding"],
        "active_candidate_binding": "forbidden",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: rendered {len(frames)} V32 component-performance frames -> {rel(report_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
