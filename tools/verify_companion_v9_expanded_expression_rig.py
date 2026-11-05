#!/usr/bin/env python3
"""Machine gate for the approved V9/V10/V11 expanded source-mask Rig."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from build_emote_asset_pack import build_pack, decode_packbits, parse_p4  # noqa: E402


DEFAULT_CANDIDATE = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v2-expanded-source/candidate"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v9-expanded-expression-rig-export-20260719.json"
EXPECTED_SOURCE_STATES = {
    "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down",
    "calm_content", "curious_question", "alert_surprised", "joyful_spark",
    "affectionate_warm", "playful_bright", "anticipatory_notice", "puzzled_processing",
    "recording_focus", "listening_focus", "menu_thinking", "sleep_rest_no_moon",
}
FAIL_CLOSED_OWNER_REJECTED_STATES = {"sleep_rest_no_moon"}
EXPECTED_STATES = EXPECTED_SOURCE_STATES - FAIL_CLOSED_OWNER_REJECTED_STATES
EXPECTED_ACCENTS = {
    "joyful_spark": {"charm_sparkle"},
    "affectionate_warm": {"charm_heart"},
}
RESTRAINED_STATES = {"calm_content", "puzzled_processing"}
PHASES = ("entry", "lead", "response", "accent", "hold", "return", "settle")
EMOTION_BASELINE_STATES = {
    "calm": "calm_content", "curious": "curious_question",
    "affectionate": "affectionate_warm", "focused": "recording_focus",
    "alert": "alert_surprised", "joyful": "joyful_spark", "playful": "playful_bright",
    "anticipatory": "anticipatory_notice", "puzzled": "puzzled_processing",
    "listening": "listening_focus", "thinking": "menu_thinking",
}
EMOTION_GRAPH_EDGES = {
    ("calm", "curious"), ("calm", "listening"),
    ("curious", "calm"), ("curious", "affectionate"), ("curious", "anticipatory"),
    ("curious", "puzzled"), ("curious", "thinking"), ("curious", "alert"),
    ("curious", "focused"),
    ("affectionate", "calm"), ("affectionate", "curious"), ("affectionate", "joyful"),
    ("affectionate", "playful"),
    ("focused", "listening"), ("focused", "thinking"), ("focused", "alert"),
    ("focused", "calm"),
    ("alert", "curious"), ("alert", "focused"), ("alert", "anticipatory"),
    ("alert", "calm"),
    ("joyful", "affectionate"), ("joyful", "playful"), ("joyful", "anticipatory"),
    ("joyful", "calm"),
    ("playful", "joyful"), ("playful", "affectionate"), ("playful", "curious"),
    ("playful", "calm"),
    ("anticipatory", "curious"), ("anticipatory", "alert"), ("anticipatory", "focused"),
    ("anticipatory", "joyful"), ("anticipatory", "calm"),
    ("puzzled", "curious"), ("puzzled", "thinking"), ("puzzled", "alert"),
    ("puzzled", "calm"),
    ("listening", "focused"), ("listening", "curious"), ("listening", "calm"),
    ("thinking", "puzzled"), ("thinking", "curious"), ("thinking", "focused"),
    ("thinking", "calm"),
}
EXPECTED_EMOTION_BRIDGES = {f"{source}_to_{target}" for source, target in EMOTION_GRAPH_EDGES}
EMOTION_BRIDGE_CUES = (
    "source_hold", "gaze_lead", "gaze_arrive", "brow_answer",
    "lower_face_reply", "accent_follow_through", "target_hold",
)
BRIDGE_IDENTITY_ROLES = {"left_eye", "right_eye", "left_sparkle", "right_sparkle", "nose"}
BRIDGE_BROW_ROLES = {"left_brow", "right_brow"}
BRIDGE_LOWER_FACE_ROLES = {"left_cheek", "right_cheek", "mouth"}
BRIDGE_ACCENT_ROLES = {"charm", "left_detail", "right_detail", "cheek_pair", "listening_detail"}
REJECTED_SCREEN_BINDINGS = {
    "cheek_dot_left", "cheek_dot_right", "detail_listening_arc_left", "detail_listening_arc_right",
}
REJECTED_SEMANTIC_CHARM_BINDINGS = {"charm_question", "charm_exclamation"}
PROTECTED_FACE_ROLES = (
    "left_brow", "right_brow", "left_eye", "right_eye",
    "left_cheek", "right_cheek", "nose", "mouth",
)
SECONDARY_OR_MOVABLE_ROLES = (
    "left_detail", "right_detail", "cheek_pair", "listening_detail", "charm",
)
SOURCE_HASHES = {
    "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png": "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA",
    "docs/art/iterations/companion-pet-expression-v9-extension-v9-expanded-daily-direction-strip/generated_pet_expression_extension_v9_expanded_daily_direction_strip_candidate.png": "06482F6401DF63ED16369660A3D2E4337A37C470F0007C0EAF8CBC90E6D768C5",
    "docs/art/iterations/companion-pet-expression-v9-extension-v10-expanded-emotion-panel/generated_pet_expression_extension_v10_expanded_emotion_panel_candidate.png": "9475CEF565608ED70258980815B31AEEA785CB431AE5B25515FE3790ADE4DD31",
    "docs/art/iterations/companion-pet-expression-v9-extension-v11-secondary-detail-kit/generated_pet_expression_extension_v11_secondary_detail_kit_candidate.png": "76B0BE9F683349490C262DD4725BDDC2252DEEDFD2B675D4EF53745D8B7C1622",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def has_black_ink(image: Image.Image) -> bool:
    return any(pixel == 0 for pixel in image.convert("1").getdata())


def pixel_difference(left: Image.Image, right: Image.Image) -> int:
    left_bytes = left.convert("1").tobytes()
    right_bytes = right.convert("1").tobytes()
    if left.size != right.size or len(left_bytes) != len(right_bytes):
        return -1
    return sum((first ^ second).bit_count() for first, second in zip(left_bytes, right_bytes))


def resolved_preview_component_offset(component: dict[str, object], state: dict[str, object],
                                      override: object) -> tuple[int, int]:
    energy_y = {"low": 1, "normal": 0, "high": -1}[str(state["energy"])]
    memory_x = int(state["interaction_memory"])
    attention_offset = {
        "center": (0, 0), "left": (-2, 0), "right": (2, 0), "up": (1, -2), "down": (1, 3),
    }[str(state["attention"])]
    delta_x, delta_y = attention_offset if component.get("role") in {
        "left_highlight", "right_highlight"} else (0, 0)
    if override is not None:
        if not isinstance(override, list) or len(override) != 2 or \
                not all(isinstance(value, int) for value in override):
            raise ValueError(f"invalid preview offset: {component.get('name', 'unknown')}")
        delta_x, delta_y = override
    motion_flags = component.get("motion_flags")
    if not isinstance(motion_flags, list):
        raise ValueError(f"component lacks preview motion flags: {component.get('name', 'unknown')}")
    if "energy_y" in motion_flags:
        delta_y += energy_y
    if "memory_x" in motion_flags:
        delta_x += memory_x
    ranges = component.get("offset_range")
    if not isinstance(ranges, dict) or not isinstance(ranges.get("min"), list) or \
            not isinstance(ranges.get("max"), list):
        raise ValueError(f"component lacks preview offset range: {component.get('name', 'unknown')}")
    return (
        max(int(ranges["min"][0]), min(int(ranges["max"][0]), delta_x)),
        max(int(ranges["min"][1]), min(int(ranges["max"][1]), delta_y)),
    )


def preview_component_frame(candidate: Path, component_map: dict[str, dict[str, object]],
                            state: dict[str, object], names: list[str],
                            offsets: dict[str, object]) -> Image.Image:
    canvas = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    for name in sorted(names, key=lambda item: int(component_map[item]["z_index"])):
        component = component_map[name]
        delta_x, delta_y = resolved_preview_component_offset(component, state, offsets.get(name))
        preview = candidate / str(component.get("preview_mask", ""))
        if not preview.is_file():
            raise ValueError(f"preview layer is missing: {name}")
        layer = Image.open(preview).convert("RGBA")
        base = component.get("base_position")
        if not isinstance(base, list) or len(base) != 2:
            raise ValueError(f"component lacks preview anchor: {name}")
        canvas.alpha_composite(layer, (int(base[0]) + delta_x, int(base[1]) + delta_y))
    return canvas.convert("1")


def component_ink_positions(component: dict[str, object], state: dict[str, object],
                            override: object) -> set[tuple[int, int]]:
    mask_path = ROOT / str(component.get("mask", ""))
    base = component.get("base_position")
    if not mask_path.is_file() or not isinstance(base, list) or len(base) != 2:
        raise ValueError(f"component lacks source-mask placement: {component.get('name', 'unknown')}")
    offset_x, offset_y = resolved_preview_component_offset(component, state, override)
    pixels: set[tuple[int, int]] = set()
    image = Image.open(mask_path).convert("1")
    for y in range(image.height):
        for x in range(image.width):
            if image.getpixel((x, y)) != 0:
                continue
            target_x = int(base[0]) + offset_x + x
            target_y = int(base[1]) + offset_y + y
            if 0 <= target_x < 200 and 0 <= target_y < 200:
                pixels.add((target_x, target_y))
    return pixels


def validate_component_occlusion(layout: dict[str, object], component_map: dict[str, dict[str, object]],
                                 state_rows: dict[object, object], core_sets: dict[object, object],
                                 state_sets: dict[object, object], performances: dict[object, object],
                                 presence_tracks: dict[object, object], emotion_bridge_tracks: dict[object, object],
                                 errors: list[str]) -> dict[str, object]:
    artifacts = layout.get("artifacts")
    artifact_map = artifacts if isinstance(artifacts, dict) else {}
    audit_info = artifact_map.get("component_occlusion_audit")
    sheets = artifact_map.get("performance_contact_sheets")
    presence_sheets = artifact_map.get("presence_contact_sheets")
    bridge_sheets = artifact_map.get("emotion_bridge_contact_sheets")
    result: dict[str, object] = {"present": False, "frame_count": 0}
    if not isinstance(audit_info, dict) or not isinstance(sheets, dict) or not isinstance(presence_sheets, dict) or \
            not isinstance(bridge_sheets, dict):
        add(errors, False, "component-occlusion audit or component-track contact sheets are missing")
        return result
    audit_path = ROOT / str(audit_info.get("path", ""))
    add(errors, audit_path.is_file() and audit_info.get("sha256") == (sha256(audit_path) if audit_path.is_file() else None),
        "component-occlusion audit hash drifted")
    add(errors, set(sheets) == EXPECTED_STATES, "per-state performance contact sheets are incomplete")
    for story, sheet_info in sheets.items():
        if not isinstance(sheet_info, dict):
            add(errors, False, f"performance contact sheet metadata is invalid: {story}")
            continue
        sheet_path = ROOT / str(sheet_info.get("path", ""))
        add(errors, sheet_path.is_file() and sheet_info.get("sha256") == (sha256(sheet_path) if sheet_path.is_file() else None),
            f"performance contact sheet hash drifted: {story}")
        if sheet_path.is_file():
            add(errors, Image.open(sheet_path).size == (1400, 224),
                f"performance contact sheet dimensions drifted: {story}")
    add(errors, set(presence_sheets) == EXPECTED_STATES, "per-state presence contact sheets are incomplete")
    for story, sheet_info in presence_sheets.items():
        if not isinstance(sheet_info, dict):
            add(errors, False, f"presence contact sheet metadata is invalid: {story}")
            continue
        sheet_path = ROOT / str(sheet_info.get("path", ""))
        add(errors, sheet_path.is_file() and sheet_info.get("sha256") == (sha256(sheet_path) if sheet_path.is_file() else None),
            f"presence contact sheet hash drifted: {story}")
        if sheet_path.is_file():
            add(errors, Image.open(sheet_path).size == (1600, 224),
                f"presence contact sheet dimensions drifted: {story}")
    add(errors, set(bridge_sheets) == EXPECTED_EMOTION_BRIDGES,
        "emotion bridge contact sheets are incomplete")
    for bridge, sheet_info in bridge_sheets.items():
        if not isinstance(sheet_info, dict):
            add(errors, False, f"emotion bridge contact sheet metadata is invalid: {bridge}")
            continue
        sheet_path = ROOT / str(sheet_info.get("path", ""))
        add(errors, sheet_path.is_file() and sheet_info.get("sha256") ==
            (sha256(sheet_path) if sheet_path.is_file() else None),
            f"emotion bridge contact sheet hash drifted: {bridge}")
        if sheet_path.is_file():
            add(errors, Image.open(sheet_path).size == (1400, 224),
                f"emotion bridge contact sheet dimensions drifted: {bridge}")
    if not audit_path.is_file():
        return result
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add(errors, False, f"component-occlusion audit cannot be read: {exc}")
        return result
    frames = audit.get("frames") if isinstance(audit, dict) else None
    reported_frames = frames if isinstance(frames, list) else []
    add(errors, isinstance(audit, dict) and audit.get("status") == "PASS_ZERO_PROTECTED_FEATURE_OVERLAP" and
        audit.get("frame_count") == 540 and len(reported_frames) == 540 and audit.get("violations") == [],
        "component-occlusion audit did not pass all transition, presence and bridge frames")
    reported = {
        (item.get("track"), item.get("story"), item.get("phase"), item.get("state"), item.get("component_set")): item
        for item in reported_frames if isinstance(item, dict)
    }
    observed_frames = 0
    for story in EXPECTED_STATES:
        performance = performances.get(story)
        steps = performance.get("steps") if isinstance(performance, dict) else None
        if not isinstance(steps, list):
            add(errors, False, f"occlusion audit cannot resolve performance steps: {story}")
            continue
        for step in steps:
            if not isinstance(step, dict):
                add(errors, False, f"occlusion audit step is invalid: {story}")
                continue
            state_name = step.get("state")
            component_set_name = step.get("set")
            state = state_rows.get(state_name)
            selected_set = core_sets if component_set_name == "core" else state_sets
            names = selected_set.get(state_name) if isinstance(selected_set, dict) else None
            offsets = step.get("offsets")
            if not isinstance(state, dict) or not isinstance(names, list) or not isinstance(offsets, dict):
                add(errors, False, f"occlusion audit cannot resolve components: {story}/{step.get('phase')}")
                continue
            role_ink: dict[str, set[tuple[int, int]]] = {}
            try:
                for name in names:
                    component = component_map[name]
                    if component.get("composite_op") != "ink":
                        continue
                    role = str(component.get("role"))
                    role_ink.setdefault(role, set()).update(
                        component_ink_positions(component, state, offsets.get(name)))
            except (KeyError, OSError, ValueError) as exc:
                add(errors, False, f"occlusion audit cannot project source mask: {story}/{step.get('phase')}: {exc}")
                continue
            protected_overlap = 0
            for index, left in enumerate(PROTECTED_FACE_ROLES):
                for right in PROTECTED_FACE_ROLES[index + 1:]:
                    protected_overlap += len(role_ink.get(left, set()) & role_ink.get(right, set()))
            protected_ink: set[tuple[int, int]] = set()
            for role in PROTECTED_FACE_ROLES:
                protected_ink.update(role_ink.get(role, set()))
            secondary_overlap = sum(
                len(role_ink.get(role, set()) & protected_ink) for role in SECONDARY_OR_MOVABLE_ROLES)
            add(errors, protected_overlap == 0 and secondary_overlap == 0,
                f"protected facial overlap detected: {story}/{step.get('phase')}")
            key = ("transition", story, step.get("phase"), state_name, component_set_name)
            reported_frame = reported.get(key)
            add(errors, isinstance(reported_frame, dict) and
                reported_frame.get("protected_role_overlap_pixels") == protected_overlap and
                reported_frame.get("secondary_overlap_pixels") == secondary_overlap,
                f"component-occlusion audit diverges from source masks: {story}/{step.get('phase')}")
            observed_frames += 1
    for story in EXPECTED_STATES:
        presence = presence_tracks.get(story)
        steps = presence.get("steps") if isinstance(presence, dict) else None
        if not isinstance(steps, list):
            add(errors, False, f"occlusion audit cannot resolve presence steps: {story}")
            continue
        for step in steps:
            if not isinstance(step, dict):
                add(errors, False, f"presence occlusion audit step is invalid: {story}")
                continue
            state_name = step.get("state")
            state = state_rows.get(state_name)
            names = state_sets.get(state_name) if isinstance(state_sets, dict) else None
            offsets = step.get("offsets")
            if not isinstance(state, dict) or not isinstance(names, list) or not isinstance(offsets, dict):
                add(errors, False, f"presence occlusion audit cannot resolve components: {story}/{step.get('cue')}")
                continue
            role_ink: dict[str, set[tuple[int, int]]] = {}
            try:
                for name in names:
                    component = component_map[name]
                    if component.get("composite_op") != "ink":
                        continue
                    role = str(component.get("role"))
                    role_ink.setdefault(role, set()).update(
                        component_ink_positions(component, state, offsets.get(name)))
            except (KeyError, OSError, ValueError) as exc:
                add(errors, False, f"presence occlusion audit cannot project source mask: {story}/{step.get('cue')}: {exc}")
                continue
            protected_overlap = 0
            for index, left in enumerate(PROTECTED_FACE_ROLES):
                for right in PROTECTED_FACE_ROLES[index + 1:]:
                    protected_overlap += len(role_ink.get(left, set()) & role_ink.get(right, set()))
            protected_ink: set[tuple[int, int]] = set()
            for role in PROTECTED_FACE_ROLES:
                protected_ink.update(role_ink.get(role, set()))
            secondary_overlap = sum(
                len(role_ink.get(role, set()) & protected_ink) for role in SECONDARY_OR_MOVABLE_ROLES)
            add(errors, protected_overlap == 0 and secondary_overlap == 0,
                f"protected facial overlap detected in presence: {story}/{step.get('cue')}")
            key = ("presence", story, step.get("phase"), state_name, "full")
            reported_frame = reported.get(key)
            add(errors, isinstance(reported_frame, dict) and
                reported_frame.get("protected_role_overlap_pixels") == protected_overlap and
                reported_frame.get("secondary_overlap_pixels") == secondary_overlap,
                f"presence component-occlusion audit diverges from source masks: {story}/{step.get('cue')}")
            observed_frames += 1
    for bridge in EXPECTED_EMOTION_BRIDGES:
        bridge_track = emotion_bridge_tracks.get(bridge)
        steps = bridge_track.get("steps") if isinstance(bridge_track, dict) else None
        if not isinstance(steps, list):
            add(errors, False, f"occlusion audit cannot resolve emotion bridge steps: {bridge}")
            continue
        for step in steps:
            if not isinstance(step, dict):
                add(errors, False, f"emotion bridge occlusion audit step is invalid: {bridge}")
                continue
            state_name = step.get("state")
            state = state_rows.get(state_name)
            names = step.get("components")
            offsets = step.get("offsets")
            if not isinstance(state, dict) or not isinstance(names, list) or \
                    not all(isinstance(name, str) and name in component_map for name in names) or \
                    not isinstance(offsets, dict):
                add(errors, False, f"emotion bridge occlusion audit cannot resolve components: {bridge}/{step.get('cue')}")
                continue
            role_ink: dict[str, set[tuple[int, int]]] = {}
            try:
                for name in names:
                    component = component_map[name]
                    if component.get("composite_op") != "ink":
                        continue
                    role = str(component.get("role"))
                    role_ink.setdefault(role, set()).update(
                        component_ink_positions(component, state, offsets.get(name)))
            except (KeyError, OSError, ValueError) as exc:
                add(errors, False, f"emotion bridge occlusion audit cannot project source mask: {bridge}/{step.get('cue')}: {exc}")
                continue
            protected_overlap = 0
            for index, left in enumerate(PROTECTED_FACE_ROLES):
                for right in PROTECTED_FACE_ROLES[index + 1:]:
                    protected_overlap += len(role_ink.get(left, set()) & role_ink.get(right, set()))
            protected_ink: set[tuple[int, int]] = set()
            for role in PROTECTED_FACE_ROLES:
                protected_ink.update(role_ink.get(role, set()))
            secondary_overlap = sum(
                len(role_ink.get(role, set()) & protected_ink) for role in SECONDARY_OR_MOVABLE_ROLES)
            add(errors, protected_overlap == 0 and secondary_overlap == 0,
                f"protected facial overlap detected in emotion bridge: {bridge}/{step.get('cue')}")
            key = ("emotion_bridge", bridge, step.get("phase"), state_name, "bridge")
            reported_frame = reported.get(key)
            add(errors, isinstance(reported_frame, dict) and
                reported_frame.get("protected_role_overlap_pixels") == protected_overlap and
                reported_frame.get("secondary_overlap_pixels") == secondary_overlap,
                f"emotion bridge component-occlusion audit diverges from source masks: {bridge}/{step.get('cue')}")
            observed_frames += 1
    add(errors, observed_frames == 540,
        "component-occlusion audit did not inspect every transition, presence and emotion bridge frame")
    result.update({
        "present": True,
        "path": relative(audit_path),
        "status": audit.get("status") if isinstance(audit, dict) else None,
        "frame_count": observed_frames,
        "performance_contact_sheet_count": len(sheets),
        "presence_contact_sheet_count": len(presence_sheets),
        "emotion_bridge_contact_sheet_count": len(bridge_sheets),
    })
    return result


def validate_component_pack(export: dict[str, object],
                            components: list[object],
                            errors: list[str]) -> dict[str, object]:
    pack_info = export.get("component_pack")
    result: dict[str, object] = {"present": False}
    if not isinstance(pack_info, dict):
        add(errors, False, "export lacks component-pack metadata")
        return result
    pack_text = pack_info.get("path")
    metadata_text = pack_info.get("metadata")
    if not isinstance(pack_text, str) or not isinstance(metadata_text, str):
        add(errors, False, "component-pack paths are missing")
        return result
    pack_path = ROOT / pack_text
    metadata_path = ROOT / metadata_text
    add(errors, pack_path.is_file() and metadata_path.is_file(),
        "component pack or pack metadata is missing")
    if not pack_path.is_file() or not metadata_path.is_file():
        return result
    try:
        pack_bytes = pack_path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add(errors, False, f"component pack metadata cannot be read: {exc}")
        return result
    result = {
        "present": True,
        "path": relative(pack_path),
        "sha256": sha256(pack_path),
        "byte_size": len(pack_bytes),
    }
    add(errors, result["sha256"] == pack_info.get("sha256") == metadata.get("pack_sha256"),
        "component-pack SHA256 does not match export metadata")
    add(errors, len(pack_bytes) == pack_info.get("total_size") == metadata.get("total_size"),
        "component-pack byte size does not match export metadata")
    add(errors, metadata.get("status") == "CANDIDATE_MACHINE_EXPORT_PENDING" and
        metadata.get("runtime_resource_activated") is False and
        metadata.get("source_sha256") == SOURCE_HASHES[
            "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"],
        "component-pack metadata is activated or does not cite the locked V9 source")
    if len(pack_bytes) < 80:
        add(errors, False, "component pack is shorter than the CRIG header")
        return result

    magic = pack_bytes[0:4]
    version, header_size = struct.unpack_from("<HH", pack_bytes, 4)
    total_size, revision = struct.unpack_from("<II", pack_bytes, 8)
    width, height, stride = struct.unpack_from("<HHH", pack_bytes, 16)
    pixel_format = pack_bytes[22]
    safe_inset = pack_bytes[23]
    component_count = struct.unpack_from("<H", pack_bytes, 24)[0]
    index_offset, data_offset, payload_crc32, index_crc32 = struct.unpack_from("<IIII", pack_bytes, 28)
    source_sha256 = pack_bytes[44:76].hex().upper()
    expected_ids = [item.get("component_id") for item in components if isinstance(item, dict)]
    add(errors, magic == b"CRIG" and version == 1 and header_size == 80 and
        total_size == len(pack_bytes) and revision > 0,
        "component pack CRIG header is invalid")
    add(errors, width == 200 and height == 200 and stride == 25 and pixel_format == 1 and safe_inset >= 4,
        "component pack profile is not the required 200x200 mono target")
    add(errors, component_count == len(expected_ids) == pack_info.get("component_count") ==
        metadata.get("component_count"), "component-pack count does not match the exported layout")
    add(errors, source_sha256 == SOURCE_HASHES[
        "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"],
        "component pack binary does not cite the locked V9 source SHA256")
    expected_data_offset = 80 + component_count * 20
    add(errors, index_offset == 80 and data_offset == expected_data_offset and data_offset <= len(pack_bytes),
        "component pack index/data offsets are invalid")
    if data_offset > len(pack_bytes):
        return result
    add(errors, (zlib.crc32(pack_bytes[index_offset:data_offset]) & 0xFFFFFFFF) == index_crc32,
        "component pack index CRC32 is invalid")
    add(errors, (zlib.crc32(pack_bytes[data_offset:]) & 0xFFFFFFFF) == payload_crc32,
        "component pack payload CRC32 is invalid")

    metadata_components = metadata.get("components")
    add(errors, isinstance(metadata_components, list) and len(metadata_components) == component_count,
        "component-pack metadata does not list every component")
    previous_end = data_offset
    actual_ids: list[int] = []
    for index in range(component_count):
        entry_offset = index_offset + index * 20
        if entry_offset + 20 > len(pack_bytes):
            add(errors, False, "component pack index exceeds its binary extent")
            break
        component_id, component_width, component_height, component_stride, component_offset, component_size = \
            struct.unpack_from("<HHHHII", pack_bytes, entry_offset)
        actual_ids.append(component_id)
        add(errors, component_id != 0xFFFF and component_width > 0 and component_height > 0 and
            component_stride >= (component_width + 7) // 8 and
            component_size == component_stride * component_height and
            component_offset == previous_end and component_offset + component_size <= len(pack_bytes),
            f"component pack index entry is invalid: {index + 1}")
        previous_end = component_offset + component_size
        if isinstance(metadata_components, list) and index < len(metadata_components):
            metadata_component = metadata_components[index]
            add(errors, isinstance(metadata_component, dict) and
                metadata_component.get("component_id") == component_id and
                metadata_component.get("width") == component_width and
                metadata_component.get("height") == component_height and
                metadata_component.get("stride_bytes") == component_stride and
                metadata_component.get("data_offset") == component_offset and
                metadata_component.get("data_size") == component_size and
                metadata_component.get("data_crc32") == f"{zlib.crc32(pack_bytes[component_offset:component_offset + component_size]) & 0xFFFFFFFF:08X}",
                f"component-pack metadata diverges from binary entry: {index + 1}")
    add(errors, actual_ids == expected_ids and previous_end == len(pack_bytes),
        "component pack ids or payload order diverges from the registered layout")
    result.update({
        "revision": revision,
        "component_count": component_count,
        "payload_crc32": f"{payload_crc32:08X}",
        "index_crc32": f"{index_crc32:08X}",
    })
    return result


def validate_audit_cemp(layout: dict[str, object], errors: list[str]) -> dict[str, object]:
    artifacts = layout.get("artifacts")
    audit = artifacts.get("audit_cemp") if isinstance(artifacts, dict) else None
    result: dict[str, object] = {"present": False}
    if not isinstance(audit, dict):
        add(errors, False, "expanded Rig lacks an audit-only CEMP artifact")
        return result
    manifest_path = ROOT / str(audit.get("manifest", ""))
    pack_path = ROOT / str(audit.get("pack", ""))
    metadata_path = ROOT / str(audit.get("metadata", ""))
    add(errors, manifest_path.is_file() and pack_path.is_file() and metadata_path.is_file(),
        "expanded audit CEMP artifact is missing")
    if not manifest_path.is_file() or not pack_path.is_file() or not metadata_path.is_file():
        return result
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected_pack, expected_metadata = build_pack(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add(errors, False, f"expanded audit CEMP cannot be rebuilt: {exc}")
        return result
    actual_pack = pack_path.read_bytes()
    clips = manifest.get("clips")
    manifest_frames: list[object] = []
    if isinstance(clips, list):
        for clip in clips:
            if isinstance(clip, dict) and isinstance(clip.get("frames"), list):
                manifest_frames.extend(clip["frames"])
    provenance = manifest.get("provenance")
    result = {
        "present": True,
        "path": relative(pack_path),
        "sha256": sha256(pack_path),
        "frame_count": len(manifest_frames),
    }
    add(errors, isinstance(provenance, dict) and provenance.get("runtime_resource_activated") is False and
        provenance.get("audit_only") is True and
        provenance.get("forbidden_runtime_paths") == ["CEMP playback", "whole-face card loop", "code-drawn face", "custom LUT"],
        "CEMP is not explicitly audit-only and runtime inactive")
    add(errors, isinstance(clips, list) and len(clips) == 15 and
        {clip.get("name") for clip in clips if isinstance(clip, dict)} == EXPECTED_STATES and
        len(manifest_frames) == 105,
        "audit CEMP clip/frame matrix drifted")
    add(errors, actual_pack == expected_pack and metadata == expected_metadata and
        result["sha256"] == audit.get("sha256") and audit.get("frame_count") == 105 and
        audit.get("runtime_resource_activated") is False and audit.get("audit_only") is True,
        "audit CEMP is not deterministic or its identity metadata drifted")
    add(errors, actual_pack[:4] == b"CEMP" and len(actual_pack) >= 56,
        "audit CEMP has an invalid binary header")
    if len(actual_pack) < 56:
        return result
    frame_count = struct.unpack_from("<H", actual_pack, 30)[0]
    frame_offset = struct.unpack_from("<I", actual_pack, 36)[0]
    payload_offset = struct.unpack_from("<I", actual_pack, 48)[0]
    payload_size = struct.unpack_from("<I", actual_pack, 52)[0]
    add(errors, frame_count == len(manifest_frames) and payload_offset + payload_size == len(actual_pack),
        "audit CEMP frame table or payload boundary drifted")
    for index, frame in enumerate(manifest_frames):
        if not isinstance(frame, dict) or frame_offset + (index + 1) * 20 > payload_offset:
            add(errors, False, f"audit CEMP frame record is invalid: {index}")
            continue
        source = manifest_path.parent / str(frame.get("source", ""))
        try:
            expected_pixels = parse_p4(source, 200, 200)
        except (OSError, ValueError) as exc:
            add(errors, False, f"audit CEMP source frame is invalid: {index}: {exc}")
            continue
        data_offset, data_size = struct.unpack_from("<II", actual_pack, frame_offset + index * 20)
        if data_offset + data_size > payload_size:
            add(errors, False, f"audit CEMP frame escapes payload: {index}")
            continue
        try:
            decoded = decode_packbits(actual_pack[payload_offset + data_offset:payload_offset + data_offset + data_size],
                                      len(expected_pixels))
        except ValueError as exc:
            add(errors, False, f"audit CEMP frame cannot decode: {index}: {exc}")
            continue
        add(errors, decoded == expected_pixels, f"audit CEMP frame decode drifted: {index}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--write", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    errors: list[str] = []
    export_path = candidate / "export-report.json"
    layout_path = candidate / "rig-layout.json"
    preview_path = candidate / "preview.html"
    add(errors, export_path.is_file() and layout_path.is_file() and preview_path.is_file(),
        "candidate export/layout/preview artifact is incomplete")
    if errors:
        report = {"schema": "companion.v9_expanded_expression_rig_machine_gate.v1", "status": "FAIL", "errors": errors}
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("FAIL: " + "; ".join(errors))
        return 1

    export = json.loads(export_path.read_text(encoding="utf-8"))
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    add(errors, export.get("status") == "PASS_SOURCE_MASK_EXPORT_CANDIDATE_RUNTIME_INACTIVE",
        "export did not pass as a runtime-inactive candidate")
    add(errors, layout.get("status") == "CANDIDATE_MACHINE_EXPORT_PENDING" and
        layout.get("runtime_resource_activated") is False,
        "layout activated or has the wrong candidate status")
    add(errors, layout.get("source_policy") == "source masks only; full-face source-card playback is forbidden",
        "source-mask policy drifted")
    add(errors, layout.get("unsupported_events_fail_closed") == ["charging", "error", "sleep"],
        "charging/error/rejected sleep are not fail-closed")
    rejected_states = layout.get("owner_rejected_states_fail_closed")
    add(errors, isinstance(rejected_states, dict) and set(rejected_states) == FAIL_CLOSED_OWNER_REJECTED_STATES,
        "owner-rejected state ledger drifted")
    if isinstance(rejected_states, dict):
        sleep_rejection = rejected_states.get("sleep_rest_no_moon")
        add(errors, isinstance(sleep_rejection, dict) and sleep_rejection.get("scene") == "sleep" and
            sleep_rejection.get("emotion") == "sleepy" and
            sleep_rejection.get("active_candidate_binding") == "forbidden" and
            sleep_rejection.get("source_components_retained_as_unbound_audit_assets") is True,
            "sleep is not recorded as an unbound fail-closed owner rejection")
    add(errors, export.get("full_face_source_card_playback") == "forbidden",
        "export permits full-face playback")
    add(errors, export.get("state_count") == 15 and export.get("component_count") == 96,
        "expected 15 active state sets and the fixed-V9-identity 96-mask export")

    for source, expected_sha in SOURCE_HASHES.items():
        path = ROOT / source
        add(errors, path.is_file() and sha256(path) == expected_sha, f"approved source drifted: {source}")
        add(errors, export.get("source_hashes", {}).get(source.replace("/", "\\")) == expected_sha or
            export.get("source_hashes", {}).get(source) == expected_sha,
            f"export did not record approved source: {source}")

    components = layout.get("components", [])
    component_map = {item.get("name"): item for item in components if isinstance(item, dict)}
    add(errors, len(component_map) == len(components), "component names are not unique")
    add(errors, [item.get("component_id") for item in components if isinstance(item, dict)] ==
        list(range(1, len(components) + 1)), "component ids are not contiguous registered ids")
    for name, item in component_map.items():
        motion_flags = item.get("motion_flags")
        add(errors, isinstance(motion_flags, list) and set(motion_flags).issubset({"energy_y", "memory_x"}),
            f"component motion flags are invalid: {name}")
    component_pack = validate_component_pack(export, components, errors)
    for name, item in component_map.items():
        mask = ROOT / str(item.get("mask", ""))
        preview = candidate / str(item.get("preview_mask", ""))
        add(errors, bool(name) and mask.is_file() and preview.is_file(), f"component artifact is missing: {name}")
        add(errors, item.get("source_sheet_sha256") in SOURCE_HASHES.values(),
            f"component does not cite an approved source hash: {name}")
        add(errors, isinstance(item.get("source_sheet_crop_box"), list) and len(item["source_sheet_crop_box"]) == 4,
            f"component lacks source-sheet crop metadata: {name}")
        add(errors, isinstance(item.get("base_position"), list) and isinstance(item.get("offset_range"), dict) and
            isinstance(item.get("z_index"), int), f"component lacks Rig placement metadata: {name}")
        if mask.is_file():
            image = Image.open(mask).convert("1")
            add(errors, has_black_ink(image), f"component mask is blank: {name}")
        if preview.is_file():
            image = Image.open(preview)
            add(errors, image.mode == "RGBA", f"preview layer is not transparent RGBA: {name}")

    source_frames = layout.get("source_frames")
    if not isinstance(source_frames, list):
        source_frames = []
    source_frame_map = {
        item.get("name"): item for item in source_frames if isinstance(item, dict)
    }
    add(errors, EXPECTED_SOURCE_STATES.issubset(source_frame_map),
        "source-frame matrix is missing an approved expression state")
    for state in EXPECTED_SOURCE_STATES:
        source_frame = source_frame_map.get(state, {})
        alignment = source_frame.get("source_alignment") if isinstance(source_frame, dict) else None
        add(errors, isinstance(alignment, dict) and alignment.get("method") == "source_eye_anchor_affine" and
            isinstance(alignment.get("uniform_scale"), (int, float)) and
            0.75 <= alignment["uniform_scale"] <= 1.25,
            f"source-frame alignment provenance is invalid: {state}")

    state_sets = layout.get("state_component_sets", {})
    core_sets = layout.get("state_core_component_sets", {})
    add(errors, set(state_sets) == EXPECTED_STATES and set(core_sets) == EXPECTED_STATES,
        "state/component-set vocabulary drifted")
    all_active_components = {name for names in state_sets.values() for name in names if isinstance(name, str)} \
        if isinstance(state_sets, dict) else set()
    sleep_components = [name for name in component_map if str(name).startswith("sleep_rest_no_moon__")]
    add(errors, bool(sleep_components) and set(sleep_components).isdisjoint(all_active_components),
        "rejected sleep source masks leaked into an active component set")
    for state in EXPECTED_STATES:
        full = set(state_sets.get(state, []))
        core = set(core_sets.get(state, []))
        add(errors, core.issubset(full) and all(name in component_map for name in full),
            f"state has an unregistered component: {state}")
        add(errors, REJECTED_SCREEN_BINDINGS.isdisjoint(full),
            f"state retains a screen-rejected secondary detail binding: {state}")
        add(errors, REJECTED_SEMANTIC_CHARM_BINDINGS.isdisjoint(full),
            f"state retains a V11 semantic charm rejected pending V16 art: {state}")
        expected_accents = EXPECTED_ACCENTS.get(state, set())
        add(errors, expected_accents.issubset(full), f"state misses approved accents: {state}")
        if state in RESTRAINED_STATES:
            add(errors, not ({"cheek_detail_left", "cheek_detail_right", "charm_sparkle", "charm_heart",
                              "charm_question", "charm_exclamation", "detail_listening_arc_left",
                              "detail_listening_arc_right"} & full),
                f"restrained state has an unapproved secondary accent: {state}")
        if state == "playful_bright":
            add(errors, {"cheek_detail_left", "cheek_detail_right", "charm_sparkle"}.isdisjoint(full),
                "playful retains an owner-rejected decorative binding")

    performances = layout.get("performances", {})
    add(errors, set(performances) == EXPECTED_STATES, "performance vocabulary drifted")
    for state, performance in performances.items():
        steps = performance.get("steps", []) if isinstance(performance, dict) else []
        phases = tuple(step.get("phase") for step in steps if isinstance(step, dict))
        add(errors, phases == PHASES, f"performance phase order is invalid: {state}")
        if len(steps) == len(PHASES):
            add(errors, steps[2].get("set") == "core" and steps[3].get("set") == "full" and
                set(steps[2].get("state", "") and core_sets.get(steps[2]["state"], [])) <=
                set(steps[3].get("state", "") and state_sets.get(steps[3]["state"], [])),
                f"accent enters before the core response: {state}")
            add(errors, steps[4].get("duration_ms", 0) >= 3000,
                f"performance hold is shorter than 3000ms: {state}")
            if state in EXPECTED_ACCENTS:
                add(errors, set(EXPECTED_ACCENTS[state]).isdisjoint(set(core_sets[state])) and
                    set(EXPECTED_ACCENTS[state]).issubset(set(state_sets[state])),
                    f"secondary accent is not deferred to the accent phase: {state}")

    raw_state_rows = layout.get("state_matrix")
    if not isinstance(raw_state_rows, list):
        raw_state_rows = []
    state_rows = {
        item.get("name"): item for item in raw_state_rows if isinstance(item, dict)
    }
    add(errors, set(state_rows) == EXPECTED_STATES,
        "performance context matrix does not match the approved state vocabulary")
    artifacts = layout.get("artifacts", {})
    performance_frames = artifacts.get("performance_frames", {}) if isinstance(artifacts, dict) else {}
    add(errors, isinstance(performance_frames, dict) and set(performance_frames) == EXPECTED_STATES,
        "performance-frame audit matrix is incomplete")
    browser_preview_parity_count = 0
    performance_frame_count = 0
    phase_metrics: dict[str, dict[str, int]] = {}
    for state in EXPECTED_STATES:
        steps = performances.get(state, {}).get("steps", []) if isinstance(performances.get(state), dict) else []
        frames = performance_frames.get(state, []) if isinstance(performance_frames, dict) else []
        if not isinstance(steps, list) or not isinstance(frames, list) or len(steps) != 7 or len(frames) != 7:
            add(errors, False, f"performance-frame count is invalid: {state}")
            continue
        audit_images: list[Image.Image] = []
        for index, (step, frame) in enumerate(zip(steps, frames)):
            if not isinstance(step, dict) or not isinstance(frame, dict):
                add(errors, False, f"performance-frame record is invalid: {state}/{index}")
                continue
            path = ROOT / str(frame.get("path", ""))
            add(errors, frame.get("index") == index and frame.get("phase") == step.get("phase") and
                frame.get("duration_ms") == step.get("duration_ms") and frame.get("state") == step.get("state") and
                frame.get("component_set") == step.get("set"),
                f"performance-frame metadata drifted: {state}/{index}")
            add(errors, path.is_file() and frame.get("sha256") == (sha256(path) if path.is_file() else None),
                f"performance-frame hash drifted: {state}/{index}")
            if not path.is_file():
                continue
            audit = Image.open(path).convert("1")
            add(errors, audit.size == (200, 200) and has_black_ink(audit),
                f"performance frame is invalid: {state}/{index}")
            audit_images.append(audit)
            performance_frame_count += 1
            step_state = state_rows.get(step.get("state"))
            component_set = core_sets if step.get("set") == "core" else state_sets
            names = component_set.get(step.get("state")) if isinstance(component_set, dict) else None
            offsets = step.get("offsets")
            if not isinstance(step_state, dict) or not isinstance(names, list) or not isinstance(offsets, dict):
                add(errors, False, f"performance-frame components are invalid: {state}/{index}")
                continue
            try:
                preview = preview_component_frame(candidate, component_map, step_state, names, offsets)
            except (OSError, ValueError, KeyError) as exc:
                add(errors, False, f"browser layer preview cannot compose {state}/{index}: {exc}")
                continue
            difference = pixel_difference(preview, audit)
            add(errors, difference == 0, f"browser/target component parity drifted: {state}/{index}")
            if difference == 0:
                browser_preview_parity_count += 1
        if len(audit_images) == 7:
            entry_to_hold = pixel_difference(audit_images[0], audit_images[4])
            entry_to_settle = pixel_difference(audit_images[0], audit_images[6])
            add(errors, entry_to_hold > 0,
                f"performance entry has no visible component motion: {state}")
            add(errors, entry_to_settle >= 0 and entry_to_settle * 4 <= entry_to_hold,
                f"performance settle does not recover near entry: {state}")
            phase_metrics[state] = {
                "entry_to_hold_pixels": entry_to_hold,
                "entry_to_settle_pixels": entry_to_settle,
            }
    add(errors, performance_frame_count == 105,
        "expanded performance audit does not contain all 105 active component frames")
    add(errors, browser_preview_parity_count == 105,
        "browser component preview does not match every active target audit frame")
    presence_tracks = layout.get("presence_tracks", {})
    presence_frames = artifacts.get("presence_frames", {}) if isinstance(artifacts, dict) else {}
    presence_frame_count = 0
    presence_browser_parity_count = 0
    presence_pixel_metrics: dict[str, dict[str, int]] = {}
    daily_gaze_vectors: set[tuple[int, int]] = set()
    expected_presence_cues = (
        "baseline", "gaze_lead", "gaze_focus", "brow_answer",
        "lower_face_reply", "gaze_return", "identity_hold", "static_rest",
    )
    add(errors, isinstance(presence_tracks, dict) and set(presence_tracks) == EXPECTED_STATES,
        "selected-state component presence vocabulary drifted")
    add(errors, isinstance(presence_frames, dict) and set(presence_frames) == EXPECTED_STATES,
        "presence-frame audit matrix is incomplete")
    for state in EXPECTED_STATES:
        track = presence_tracks.get(state) if isinstance(presence_tracks, dict) else None
        steps = track.get("steps", []) if isinstance(track, dict) else []
        frames = presence_frames.get(state, []) if isinstance(presence_frames, dict) else []
        add(errors, isinstance(track, dict) and
            track.get("loop_policy") == "same_selected_state_after_static_rest" and
            track.get("static_rest_ms") == 8000,
            f"presence loop policy is invalid: {state}")
        if not isinstance(steps, list) or not isinstance(frames, list) or len(steps) != 8 or len(frames) != 8:
            add(errors, False, f"presence-frame count is invalid: {state}")
            continue
        cues = tuple(step.get("cue") for step in steps if isinstance(step, dict))
        add(errors, cues == expected_presence_cues, f"presence cue order is invalid: {state}")
        audit_images: list[Image.Image] = []
        for index, (step, frame) in enumerate(zip(steps, frames)):
            if not isinstance(step, dict) or not isinstance(frame, dict):
                add(errors, False, f"presence frame record is invalid: {state}/{index}")
                continue
            offsets = step.get("offsets")
            path = ROOT / str(frame.get("path", ""))
            add(errors, step.get("state") == state and step.get("set") == "full" and
                isinstance(offsets, dict) and set(offsets).issubset(set(state_sets.get(state, []))),
                f"presence sample changes a face card or uses an unregistered component: {state}/{index}")
            add(errors, frame.get("index") == index and frame.get("cue") == step.get("cue") and
                frame.get("phase") == step.get("phase") and frame.get("duration_ms") == step.get("duration_ms") and
                frame.get("state") == state and frame.get("component_set") == "full",
                f"presence-frame metadata drifted: {state}/{index}")
            add(errors, path.is_file() and frame.get("sha256") == (sha256(path) if path.is_file() else None),
                f"presence-frame hash drifted: {state}/{index}")
            if not path.is_file() or not isinstance(offsets, dict):
                continue
            audit = Image.open(path).convert("1")
            add(errors, audit.size == (200, 200) and has_black_ink(audit),
                f"presence frame is invalid: {state}/{index}")
            audit_images.append(audit)
            presence_frame_count += 1
            try:
                preview = preview_component_frame(candidate, component_map, state_rows[state],
                                                  state_sets[state], offsets)
            except (OSError, ValueError, KeyError) as exc:
                add(errors, False, f"browser layer presence preview cannot compose {state}/{index}: {exc}")
                continue
            difference = pixel_difference(preview, audit)
            add(errors, difference == 0, f"browser/target component presence parity drifted: {state}/{index}")
            if difference == 0:
                presence_browser_parity_count += 1
        if len(audit_images) == 8:
            baseline_to_gaze = pixel_difference(audit_images[0], audit_images[2])
            baseline_to_brow = pixel_difference(audit_images[0], audit_images[3])
            baseline_to_lower = pixel_difference(audit_images[0], audit_images[4])
            add(errors, baseline_to_gaze > 0 and baseline_to_brow > 0 and baseline_to_lower > 0,
                f"presence track lacks a readable local component response: {state}")
            add(errors, pixel_difference(audit_images[0], audit_images[-1]) == 0,
                f"presence track does not finish at its anchored identity baseline: {state}")
            presence_pixel_metrics[state] = {
                "baseline_to_gaze_pixels": baseline_to_gaze,
                "baseline_to_brow_pixels": baseline_to_brow,
                "baseline_to_lower_pixels": baseline_to_lower,
            }
        if len(steps) == 8 and all(isinstance(step, dict) for step in steps):
            def roles_at(index: int) -> set[str]:
                offsets = steps[index].get("offsets", {})
                return {str(component_map[name].get("role")) for name in offsets if name in component_map} \
                    if isinstance(offsets, dict) else set()
            add(errors, roles_at(1) == {"left_highlight", "right_highlight"} and
                roles_at(2) == {"left_highlight", "right_highlight"},
                f"presence gaze is not isolated to the registered highlights: {state}")
            add(errors, roles_at(3).issubset({"left_highlight", "right_highlight", "left_brow", "right_brow"}) and
                {"left_brow", "right_brow"}.issubset(roles_at(3)),
                f"presence brow response is not a local causal group: {state}")
            add(errors, roles_at(4).issubset({"left_cheek", "right_cheek", "mouth"}) and
                {"left_cheek", "right_cheek", "mouth"}.issubset(roles_at(4)),
                f"presence lower-face response is not a local causal group: {state}")
            if state in {"daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down"}:
                gaze = steps[1].get("offsets", {})
                focus = steps[2].get("offsets", {})
                for offsets in (gaze, focus):
                    value = offsets.get("daily_attention_left__left_highlight") if isinstance(offsets, dict) else None
                    if isinstance(value, list) and len(value) == 2:
                        daily_gaze_vectors.add((int(value[0]), int(value[1])))
    add(errors, presence_frame_count == 120,
        "expanded presence audit does not contain all 120 selected-state component frames")
    add(errors, presence_browser_parity_count == 120,
        "browser component presence preview does not match every target audit frame")
    add(errors, len(daily_gaze_vectors) >= 8,
        "daily presence highlights do not prove left/right/up/down gaze variety")
    emotion_system = layout.get("emotion_system", {})
    emotion_bridge_tracks = layout.get("emotion_bridge_tracks", {})
    emotion_bridge_frames = artifacts.get("emotion_bridge_frames", {}) if isinstance(artifacts, dict) else {}
    bridge_frame_count = 0
    bridge_browser_parity_count = 0
    bridge_pixel_metrics: dict[str, dict[str, int]] = {}
    expected_affect_core = {"valence_range": [-2, 2], "arousal_range": [0, 3], "affinity_range": [0, 2]}
    add(errors, isinstance(emotion_system, dict) and
        emotion_system.get("schema") == "companion.v9_affect_transition_graph.v1" and
        emotion_system.get("affect_core") == expected_affect_core and
        emotion_system.get("baseline_states") == EMOTION_BASELINE_STATES and
        {tuple(edge) for edge in emotion_system.get("directed_edges", [])
         if isinstance(edge, list) and len(edge) == 2} == EMOTION_GRAPH_EDGES and
        emotion_system.get("automatic_idle_policy") == "selected_state_presence_only_no_baseline_rotation" and
        emotion_system.get("bridge_policy") == "highlights_then_brows_then_lower_face_then_approved_accent",
        "continuous affect/transition graph metadata drifted")
    add(errors, isinstance(emotion_bridge_tracks, dict) and set(emotion_bridge_tracks) == EXPECTED_EMOTION_BRIDGES,
        "emotion bridge vocabulary does not match the directed affect graph")
    add(errors, isinstance(emotion_bridge_frames, dict) and set(emotion_bridge_frames) == EXPECTED_EMOTION_BRIDGES,
        "emotion bridge frame audit matrix is incomplete")

    def roles_for(names: list[str]) -> set[str]:
        return {str(component_map[name].get("role")) for name in names if name in component_map}

    def changed_roles(left: list[str], right: list[str]) -> set[str]:
        return roles_for(list(set(left) ^ set(right)))

    def offset_roles(step: dict[str, object]) -> set[str]:
        offsets = step.get("offsets")
        return roles_for(list(offsets)) if isinstance(offsets, dict) else set()

    rendered_for_bridges = artifacts.get("rendered_frames", {}) if isinstance(artifacts, dict) else {}
    for bridge in EXPECTED_EMOTION_BRIDGES:
        source_emotion, target_emotion = bridge.split("_to_", 1)
        source_state = EMOTION_BASELINE_STATES[source_emotion]
        target_state = EMOTION_BASELINE_STATES[target_emotion]
        track = emotion_bridge_tracks.get(bridge) if isinstance(emotion_bridge_tracks, dict) else None
        steps = track.get("steps", []) if isinstance(track, dict) else []
        frames = emotion_bridge_frames.get(bridge, []) if isinstance(emotion_bridge_frames, dict) else []
        add(errors, isinstance(track, dict) and track.get("from_emotion") == source_emotion and
            track.get("to_emotion") == target_emotion and track.get("source_state") == source_state and
            track.get("target_state") == target_state,
            f"emotion bridge endpoints are invalid: {bridge}")
        if not isinstance(steps, list) or not isinstance(frames, list) or len(steps) != 7 or len(frames) != 7:
            add(errors, False, f"emotion bridge frame count is invalid: {bridge}")
            continue
        cues = tuple(step.get("cue") for step in steps if isinstance(step, dict))
        add(errors, cues == EMOTION_BRIDGE_CUES, f"emotion bridge cue order is invalid: {bridge}")
        first_names = steps[0].get("components") if isinstance(steps[0], dict) else None
        final_names = steps[-1].get("components") if isinstance(steps[-1], dict) else None
        add(errors, isinstance(first_names, list) and set(first_names) == set(state_sets[source_state]) and
            isinstance(final_names, list) and set(final_names) == set(state_sets[target_state]),
            f"emotion bridge starts or ends by replacing a whole source-card contract: {bridge}")
        audit_images: list[Image.Image] = []
        for index, (step, frame) in enumerate(zip(steps, frames)):
            if not isinstance(step, dict) or not isinstance(frame, dict):
                add(errors, False, f"emotion bridge record is invalid: {bridge}/{index}")
                continue
            names = step.get("components")
            offsets = step.get("offsets")
            state_name = step.get("state")
            path = ROOT / str(frame.get("path", ""))
            valid_names = isinstance(names, list) and all(isinstance(name, str) and name in component_map for name in names)
            add(errors, step.get("set") == "bridge" and state_name in state_rows and valid_names and
                isinstance(offsets, dict) and set(offsets).issubset(set(names) if isinstance(names, list) else set()) and
                REJECTED_SEMANTIC_CHARM_BINDINGS.isdisjoint(set(names) if isinstance(names, list) else set()),
                f"emotion bridge uses an unregistered or rejected source component: {bridge}/{index}")
            add(errors, frame.get("index") == index and frame.get("cue") == step.get("cue") and
                frame.get("phase") == step.get("phase") and frame.get("duration_ms") == step.get("duration_ms") and
                frame.get("state") == state_name and frame.get("component_set") == "bridge" and
                frame.get("components") == names,
                f"emotion bridge frame metadata drifted: {bridge}/{index}")
            add(errors, path.is_file() and frame.get("sha256") == (sha256(path) if path.is_file() else None),
                f"emotion bridge frame hash drifted: {bridge}/{index}")
            if not valid_names or not isinstance(offsets, dict) or not isinstance(state_name, str) or not path.is_file():
                continue
            audit = Image.open(path).convert("1")
            add(errors, audit.size == (200, 200) and has_black_ink(audit),
                f"emotion bridge frame is invalid: {bridge}/{index}")
            audit_images.append(audit)
            bridge_frame_count += 1
            try:
                preview = preview_component_frame(candidate, component_map, state_rows[state_name], names, offsets)
            except (OSError, ValueError, KeyError) as exc:
                add(errors, False, f"browser emotion bridge cannot compose {bridge}/{index}: {exc}")
                continue
            difference = pixel_difference(preview, audit)
            add(errors, difference == 0, f"browser/target emotion bridge parity drifted: {bridge}/{index}")
            if difference == 0:
                bridge_browser_parity_count += 1
        if all(isinstance(step, dict) and isinstance(step.get("components"), list) for step in steps):
            role_history = [roles_for(list(step["components"])) for step in steps]
            identity_history = [
                {name for name in step["components"] if str(component_map[name].get("role")) in BRIDGE_IDENTITY_ROLES}
                for step in steps
            ]
            add(errors, all(identity == identity_history[0] for identity in identity_history),
                f"emotion bridge moves or swaps a fixed V9 identity anchor: {bridge}")
            add(errors, offset_roles(steps[1]) == {"left_highlight", "right_highlight"} and
                offset_roles(steps[2]) == {"left_highlight", "right_highlight"},
                f"emotion bridge does not lead with only the registered highlights: {bridge}")
            add(errors, changed_roles(list(steps[2]["components"]), list(steps[3]["components"])) <=
                BRIDGE_BROW_ROLES and
                BRIDGE_BROW_ROLES.issubset(changed_roles(list(steps[2]["components"]), list(steps[3]["components"]))),
                f"emotion bridge brow answer is not a local causal exchange: {bridge}")
            add(errors, changed_roles(list(steps[3]["components"]), list(steps[4]["components"])) <= BRIDGE_LOWER_FACE_ROLES and
                BRIDGE_LOWER_FACE_ROLES.issubset(changed_roles(list(steps[3]["components"]), list(steps[4]["components"]))),
                f"emotion bridge lower-face reply is not a local causal exchange: {bridge}")
            add(errors, changed_roles(list(steps[4]["components"]), list(steps[5]["components"])) <= BRIDGE_ACCENT_ROLES and
                changed_roles(list(steps[5]["components"]), list(steps[6]["components"])) == set(),
                f"emotion bridge accent/hold changes more than its approved local group: {bridge}")
            add(errors, (role_history[0] ^ role_history[-1]).issubset(BRIDGE_ACCENT_ROLES),
                f"emotion bridge changed more than an approved secondary accent vocabulary: {bridge}")
        if len(audit_images) == 7:
            gaze_difference = pixel_difference(audit_images[0], audit_images[2])
            brow_difference = pixel_difference(audit_images[2], audit_images[3])
            lower_difference = pixel_difference(audit_images[3], audit_images[4])
            add(errors, gaze_difference > 0 and brow_difference > 0 and lower_difference > 0,
                f"emotion bridge lacks readable gaze, brow or lower-face causality: {bridge}")
            bridge_pixel_metrics[bridge] = {
                "source_to_gaze_pixels": gaze_difference,
                "gaze_to_brow_pixels": brow_difference,
                "brow_to_lower_pixels": lower_difference,
            }
            target_rendered = ROOT / str(rendered_for_bridges.get(target_state, "")) \
                if isinstance(rendered_for_bridges, dict) else ROOT
            add(errors, target_rendered.is_file() and
                pixel_difference(audit_images[-1], Image.open(target_rendered).convert("1")) == 0,
                f"emotion bridge target hold does not land on the selected target baseline: {bridge}")
    add(errors, bridge_frame_count == 315,
        "emotion bridge audit does not contain all directed component-level samples")
    add(errors, bridge_browser_parity_count == 315,
        "browser emotion bridge preview does not match every target sample")
    occlusion_audit = validate_component_occlusion(layout, component_map, state_rows, core_sets,
                                                   state_sets, performances, presence_tracks, emotion_bridge_tracks, errors)
    audit_cemp = validate_audit_cemp(layout, errors)

    rendered = layout.get("artifacts", {}).get("rendered_frames", {})
    add(errors, set(rendered) == EXPECTED_STATES, "rendered frame matrix drifted")
    rendered_hashes: list[str] = []
    for state, path_text in rendered.items():
        path = ROOT / str(path_text)
        add(errors, path.is_file(), f"rendered audit frame is missing: {state}")
        if path.is_file():
            image = Image.open(path).convert("1")
            add(errors, image.size == (200, 200) and image.getbbox() is not None,
                f"rendered audit frame is invalid: {state}")
            rendered_hashes.append(sha256(path))
    add(errors, len(set(rendered_hashes)) == 15, "rendered component frames are not all unique")

    preview_text = preview_path.read_text(encoding="utf-8")
    forbidden = ("generated_pet_expression", "rendered-200x200")
    add(errors, all(token not in preview_text for token in forbidden),
        "browser preview references a prohibited whole-face/source asset")
    add(errors, "preview-layers/" in preview_text and "presenceTracks" in preview_text and
        "bridgeTracks" in preview_text and "findRoute(from, to)" in preview_text and
        "playDirectBridge(from, to, done)" in preview_text and
        "setTimeout(() => select(" not in preview_text and "#atlas" not in preview_text and
        "performances" not in preview_text,
        "browser preview does not replay the registered selected-state/bridge component plans")

    report = {
        "schema": "companion.v9_expanded_expression_rig_machine_gate.v1",
        "status": "PASS_EXPANDED_COMPONENT_RIG_MACHINE_GATE" if not errors else "FAIL_EXPANDED_COMPONENT_RIG_MACHINE_GATE",
        "candidate": relative(candidate),
        "layout_sha256": sha256(layout_path),
        "source_hashes": SOURCE_HASHES,
        "state_count": len(state_sets),
        "owner_rejected_fail_closed_state_count": len(FAIL_CLOSED_OWNER_REJECTED_STATES),
        "component_count": len(component_map),
        "component_pack": component_pack,
        "component_occlusion_audit": occlusion_audit,
        "audit_cemp": audit_cemp,
        "unique_rendered_frame_hashes": len(set(rendered_hashes)),
        "performance_frame_count": performance_frame_count,
        "presence_frame_count": presence_frame_count,
        "emotion_bridge_count": len(emotion_bridge_tracks) if isinstance(emotion_bridge_tracks, dict) else 0,
        "emotion_bridge_frame_count": bridge_frame_count,
        "browser_component_preview_parity_frames": browser_preview_parity_count + presence_browser_parity_count +
            bridge_browser_parity_count,
        "presence_browser_component_preview_parity_frames": presence_browser_parity_count,
        "emotion_bridge_browser_component_preview_parity_frames": bridge_browser_parity_count,
        "performance_phase_pixel_metrics": phase_metrics,
        "presence_pixel_metrics": presence_pixel_metrics,
        "emotion_bridge_pixel_metrics": bridge_pixel_metrics,
        "runtime_resource_activated": layout.get("runtime_resource_activated"),
        "full_face_source_card_playback": export.get("full_face_source_card_playback"),
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if errors:
        print("FAIL: " + "; ".join(errors))
        return 1
    print("PASS: expanded Rig contains only approved source masks, deferred accents and component-level choreography")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
