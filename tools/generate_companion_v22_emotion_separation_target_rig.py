#!/usr/bin/env python3
"""Generate the inactive V22 external-NOR component Rig and bridge profile.

The source of truth is the owner-accepted V22 browser/PBM component bridge.  This
tool copies only its registered source masks into a CRIG bundle and generates C
plans for exactly the same layers, offsets, and durations.  It never serializes
or selects a complete-face frame.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import zlib
from typing import Any

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
V22_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source"
EXPORT_LAYOUT = V22_ROOT / "candidate/component-export-attempt-03/everyday-emotion-component-layout.json"
BRIDGE_LAYOUT = V22_ROOT / "candidate/component-bridge-attempt-01/component-bridge-layout.json"
COMPONENT_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-component-export-gate-20260719.json"
BRIDGE_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-component-bridge-gate-20260719.json"
OWNER_REVIEW = ROOT / "docs/validation/companion-v22-emotion-separation-component-bridge-owner-art-screen-review-20260719.json"
OUTPUT = V22_ROOT / "candidate/target-rig-attempt-01"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v22_emotion_separation_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v22_emotion_separation_candidate_profile.c"

LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V22_REVISION = 22
CANVAS = (200, 200)
STRIDE = 25
SAFE_INSET_PX = 4
HEADER_BYTES = 80
INDEX_ENTRY_BYTES = 20
MAX_LAYERS = 16

ROLE_ENUM = {
    "left_brow": "COMP_EXPRESSION_RIG_ROLE_LEFT_BROW",
    "right_brow": "COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW",
    "left_eye": "COMP_EXPRESSION_RIG_ROLE_LEFT_EYE",
    "right_eye": "COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE",
    "left_highlight": "COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT",
    "right_highlight": "COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT",
    "left_sparkle": "COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE",
    "right_sparkle": "COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE",
    "left_cheek": "COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK",
    "right_cheek": "COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK",
    "nose": "COMP_EXPRESSION_RIG_ROLE_NOSE",
    "mouth": "COMP_EXPRESSION_RIG_ROLE_MOUTH",
    "accent": "COMP_EXPRESSION_RIG_ROLE_CHARM",
    "charm": "COMP_EXPRESSION_RIG_ROLE_CHARM",
}
EMOTION_ENUM = {
    "calm": "COMP_EXPRESSION_RIG_EMOTION_CALM",
    "curious": "COMP_EXPRESSION_RIG_EMOTION_CURIOUS",
    "warm": "COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE",
    "playful": "COMP_EXPRESSION_RIG_EMOTION_PLAYFUL",
    "puzzled": "COMP_EXPRESSION_RIG_EMOTION_PUZZLED",
    "alert": "COMP_EXPRESSION_RIG_EMOTION_ALERT",
}
SCORE_PHASE_ENUM = {
    "source_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "primary_highlight_lead": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "sparkle_arrive": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "brow_apex": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "lower_face_apex": "COMP_EXPRESSION_RIG_SCORE_PHASE_RESPONSE",
    "accent_resolve": "COMP_EXPRESSION_RIG_SCORE_PHASE_ACCENT",
    "target_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
    "highlight_settle": "COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def write_or_check(path: pathlib.Path, data: bytes, check: bool) -> bool:
    if check:
        return path.is_file() and path.read_bytes() == data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def component_variant(name: str) -> str:
    if name in {
        "left_eye_open", "right_eye_open", "left_eye_highlight_open",
        "right_eye_highlight_open", "left_eye_sparkle_open", "right_eye_sparkle_open",
    }:
        return "COMP_EXPRESSION_RIG_VARIANT_OPEN"
    return "COMP_EXPRESSION_RIG_VARIANT_DEFAULT"


def component_op(value: str) -> str:
    require(value in {"ink", "erase"}, f"unsupported composite op {value}")
    return "COMP_EXPRESSION_RIG_COMPOSITE_INK" if value == "ink" else "COMP_EXPRESSION_RIG_COMPOSITE_ERASE"


def source_preconditions() -> tuple[dict[str, Any], dict[str, Any]]:
    component_gate = load_json(COMPONENT_GATE)
    bridge_gate = load_json(BRIDGE_GATE)
    owner_review = load_json(OWNER_REVIEW)
    require(component_gate.get("status") == "PASS_V22_EMOTION_SEPARATION_COMPONENT_EXPORT_GATE",
            "V22 component export gate must pass before target Rig export")
    require(bridge_gate.get("status") == "PASS_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_GATE",
            "V22 browser/PBM bridge gate must pass before target Rig export")
    require(owner_review.get("status") ==
            "PASS_OWNER_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_ACCEPTED_RUNTIME_INACTIVE" and
            owner_review.get("selected") == "通过" and
            owner_review.get("runtime_resource_activated") is False and
            owner_review.get("active_candidate_binding") == "forbidden",
            "V22 owner acceptance must be present and remain runtime-inactive")
    return bridge_gate, owner_review


def normalize_components(export_layout: dict[str, Any], bridge_layout: dict[str, Any]) -> list[dict[str, Any]]:
    components = bridge_layout.get("components")
    identity = export_layout.get("identity_components")
    emotions = export_layout.get("emotion_components")
    require(isinstance(components, dict) and isinstance(identity, dict) and isinstance(emotions, dict),
            "V22 source component registries are missing")
    expected_names = set(identity)
    for records in emotions.values():
        require(isinstance(records, dict), "V22 emotion component records are invalid")
        expected_names.update(records)
    require(set(components) == expected_names, "bridge component vocabulary drifted from the V22 export")

    result: list[dict[str, Any]] = []
    for component_id, name in enumerate(sorted(components), start=1):
        record = components[name]
        require(isinstance(record, dict), f"component {name} is invalid")
        role = record.get("role")
        base = record.get("base_position")
        offset_range = record.get("offset_range")
        size = record.get("size")
        mask = ROOT / str(record.get("mask", ""))
        expected_hash = str(record.get("mask_sha256", "")).upper()
        require(role in ROLE_ENUM and isinstance(base, list) and len(base) == 2 and
                isinstance(offset_range, dict) and isinstance(size, list) and len(size) == 2 and
                mask.is_file() and len(expected_hash) == 64 and sha256(mask) == expected_hash,
                f"component {name} has invalid source provenance")
        minimum, maximum = offset_range.get("min"), offset_range.get("max")
        require(isinstance(minimum, list) and len(minimum) == 2 and
                isinstance(maximum, list) and len(maximum) == 2 and
                all(isinstance(value, int) and -127 <= value <= 127 for value in minimum + maximum) and
                all(isinstance(value, int) for value in base + size) and
                minimum[0] <= maximum[0] and minimum[1] <= maximum[1] and
                isinstance(record.get("z_index"), int) and 0 <= record["z_index"] <= 255 and
                record.get("composite_op") in {"ink", "erase"},
                f"component {name} geometry is invalid")
        with Image.open(mask) as image:
            mono = image.convert("1")
            width, height = mono.size
            data = mono.tobytes()
        require([width, height] == size and width > 0 and height > 0 and
                len(data) == ((width + 7) // 8) * height,
                f"component {name} mask dimensions drifted")
        result.append({
            "component_id": component_id,
            "name": name,
            "role": role,
            "emotion": record.get("emotion"),
            "source": record.get("source"),
            "mask": rel(mask),
            "mask_sha256": expected_hash,
            "base_position": base,
            "offset_range": {"min": minimum, "max": maximum},
            "z_index": record["z_index"],
            "composite_op": record["composite_op"],
            "width": width,
            "height": height,
            "stride_bytes": (width + 7) // 8,
            "data_size": len(data),
            "data_crc32": f"{zlib.crc32(data) & 0xFFFFFFFF:08X}",
        })
    return result


def normalize_bridges(bridge_layout: dict[str, Any], components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_bridges = bridge_layout.get("bridges")
    by_name = {component["name"]: component for component in components}
    require(isinstance(raw_bridges, dict) and len(raw_bridges) == 10, "V22 must retain ten legal directed bridges")
    result: list[dict[str, Any]] = []
    for key in sorted(raw_bridges):
        bridge = raw_bridges[key]
        require(isinstance(bridge, dict), f"bridge {key} is invalid")
        source = bridge.get("source")
        target = bridge.get("target")
        frames = bridge.get("frames")
        require(key == f"{source}__{target}" and source in EMOTION_ENUM and target in EMOTION_ENUM and
                source != target and isinstance(frames, list) and 7 <= len(frames) <= 8,
                f"bridge {key} is invalid")
        clean_frames: list[dict[str, Any]] = []
        for index, frame in enumerate(frames):
            require(isinstance(frame, dict) and frame.get("index") == index, f"bridge {key} frame order drifted")
            cue = frame.get("cue")
            layers = frame.get("layers")
            target_pbm = ROOT / str(frame.get("target_pbm", ""))
            target_hash = str(frame.get("target_pbm_sha256", "")).upper()
            require(cue in SCORE_PHASE_ENUM and isinstance(frame.get("duration_ms"), int) and
                    frame["duration_ms"] >= 80 and isinstance(layers, list) and 0 < len(layers) <= MAX_LAYERS and
                    target_pbm.is_file() and len(target_hash) == 64 and sha256(target_pbm) == target_hash,
                    f"bridge {key} frame {index} is invalid")
            clean_layers: list[dict[str, Any]] = []
            seen: set[str] = set()
            for layer in layers:
                require(isinstance(layer, dict), f"bridge {key} layer is invalid")
                name = layer.get("component")
                offset = layer.get("offset")
                component = by_name.get(str(name))
                require(component is not None and name not in seen and isinstance(offset, list) and len(offset) == 2 and
                        all(isinstance(value, int) and -127 <= value <= 127 for value in offset),
                        f"bridge {key} references an invalid component")
                seen.add(str(name))
                minimum = component["offset_range"]["min"]
                maximum = component["offset_range"]["max"]
                require(minimum[0] <= offset[0] <= maximum[0] and minimum[1] <= offset[1] <= maximum[1] and
                        layer.get("position") == [component["base_position"][0] + offset[0],
                                                  component["base_position"][1] + offset[1]] and
                        layer.get("z_index") == component["z_index"] and
                        layer.get("composite_op") == component["composite_op"],
                        f"bridge {key} layer geometry drifted from the registered component")
                clean_layers.append({"component": name, "component_id": component["component_id"],
                                     "offset": offset})
            clean_frames.append({
                "index": index,
                "cue": cue,
                "source_phase": frame.get("phase"),
                "duration_ms": frame["duration_ms"],
                "changed_groups": frame.get("changed_groups"),
                "layers": clean_layers,
                "target_pbm": rel(target_pbm),
                "target_pbm_sha256": target_hash,
                "target_pbm_filename": target_pbm.name,
            })
        require(clean_frames[0]["cue"] == "source_hold" and clean_frames[-1]["cue"] == "highlight_settle" and
                bridge.get("final_target_pixel_distance") == 0,
                f"bridge {key} no longer settles to its target reassembly")
        result.append({
            "name": key,
            "source": source,
            "target": target,
            "event": bridge.get("event"),
            "gaze_offset": bridge.get("gaze_offset"),
            "policy": bridge.get("policy"),
            "frames": clean_frames,
            "target_reassembly": bridge.get("target_reassembly"),
            "final_target_pixel_distance": bridge.get("final_target_pixel_distance"),
        })
    return result


def build_pack(components: list[dict[str, Any]]) -> tuple[bytes, list[dict[str, Any]]]:
    index = bytearray()
    payload = bytearray()
    packed_components: list[dict[str, Any]] = []
    data_offset = HEADER_BYTES + INDEX_ENTRY_BYTES * len(components)
    for component in components:
        with Image.open(ROOT / component["mask"]) as image:
            mono = image.convert("1")
            data = mono.tobytes()
        offset = data_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        index.extend(struct.pack("<HHHHIII", component["component_id"], component["width"],
                                 component["height"], component["stride_bytes"], offset, len(data), crc))
        payload.extend(data)
        packed_components.append({**component, "data_offset": offset, "data_crc32": f"{crc:08X}"})
    total_size = data_offset + len(payload)
    header = bytearray(HEADER_BYTES)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, HEADER_BYTES)
    struct.pack_into("<I", header, 8, total_size)
    struct.pack_into("<I", header, 12, V22_REVISION)
    struct.pack_into("<H", header, 16, CANVAS[0])
    struct.pack_into("<H", header, 18, CANVAS[1])
    struct.pack_into("<H", header, 20, STRIDE)
    header[22] = 1
    header[23] = SAFE_INSET_PX
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED_V9_SHA256)
    return bytes(header) + bytes(index) + bytes(payload), packed_components


def render_header(component_count: int) -> str:
    return f'''/* Generated by tools/generate_companion_v22_emotion_separation_target_rig.py; do not hand edit. */
#ifndef COMPANION_EPAPER_EXPRESSION_RIG_V22_EMOTION_SEPARATION_CANDIDATE_PROFILE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_V22_EMOTION_SEPARATION_CANDIDATE_PROFILE_H

#include "expression_rig_performance_score.h"

#include <stdbool.h>
#include <stdint.h>

#define COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_REVISION {V22_REVISION}u
#define COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_COMPONENT_COUNT {component_count}u
#define COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_BRIDGE_COUNT 10u
#define COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_SOURCE_SHA256 "{LOCKED_V9_SHA256}"

typedef struct {{
    const char *cue;
    const char *source_phase;
    const char *target_pbm_filename;
    uint16_t duration_ms;
}} comp_v22_emotion_separation_rig_frame_t;

typedef struct {{
    const char *name;
    const char *source_emotion;
    const char *target_emotion;
    const char *event_name;
    const comp_expression_rig_registered_performance_score_t *score;
    const comp_v22_emotion_separation_rig_frame_t *frames;
    uint8_t frame_count;
}} comp_v22_emotion_separation_rig_bridge_t;

const comp_expression_rig_profile_t *comp_v22_emotion_separation_rig_candidate_profile(void);
bool comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed(void);
uint8_t comp_v22_emotion_separation_rig_candidate_bridge_count(void);
const comp_v22_emotion_separation_rig_bridge_t *comp_v22_emotion_separation_rig_candidate_bridge(uint8_t index);

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_V22_EMOTION_SEPARATION_CANDIDATE_PROFILE_H */
'''


def c_quote(value: str | None) -> str:
    require(isinstance(value, str) and value and all(32 <= ord(char) < 127 and char not in {'"', '\\'} for char in value),
            "generated C string contains unsupported characters")
    return f'"{value}"'


def render_source(components: list[dict[str, Any]], bridges: list[dict[str, Any]]) -> str:
    component_lines = []
    for component in components:
        component_lines.append(
            "    {.component_id = %du, .role = %s, .variant = %s, .base_x = %d, .base_y = %d, "
            ".min_offset_x = %d, .min_offset_y = %d, .max_offset_x = %d, .max_offset_y = %d, "
            ".z_index = %du, .composite_op = %s}," % (
                component["component_id"], ROLE_ENUM[component["role"]], component_variant(component["name"]),
                component["base_position"][0], component["base_position"][1],
                component["offset_range"]["min"][0], component["offset_range"]["min"][1],
                component["offset_range"]["max"][0], component["offset_range"]["max"][1],
                component["z_index"], component_op(component["composite_op"])))
    blocks = [
        "/* Generated from the accepted V22 component bridge; do not hand edit. */",
        "#include \"expression_rig_v22_emotion_separation_candidate_profile.h\"",
        "",
        "static const comp_expression_rig_component_info_t k_v22_components[] = {",
        "\n".join(component_lines),
        "};",
        "",
        "static const comp_expression_rig_profile_t k_v22_profile = {",
        "    .components = k_v22_components,",
        "    .component_count = COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_COMPONENT_COUNT,",
        "    .scene_charm_component = {",
        "        [COMP_EXPRESSION_RIG_SCENE_DAILY] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_TOUCH] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_SWIPE] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_RECORDING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_MENU] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_SLEEP] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_CHARGING] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "        [COMP_EXPRESSION_RIG_SCENE_ERROR] = COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID,",
        "    },",
        "    .registered_poses = NULL,",
        "    .registered_pose_count = 0u,",
        "};",
    ]
    bridge_entries: list[str] = []
    for bridge_index, bridge in enumerate(bridges):
        pose_symbols: list[str] = []
        descriptor_lines: list[str] = []
        score_lines: list[str] = []
        for frame in bridge["frames"]:
            symbol = f"k_v22_bridge_{bridge_index}_frame_{frame['index']}_pose"
            pose_symbols.append(symbol)
            layers = "\n".join(
                "            {.component_id = %du, .offset_x = %d, .offset_y = %d, .dynamic_flags = 0u}," %
                (layer["component_id"], layer["offset"][0], layer["offset"][1])
                for layer in frame["layers"]
            )
            blocks.extend([
                "",
                f"static const comp_expression_rig_registered_pose_t {symbol} = {{",
                "    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,",
                f"    .emotion = {EMOTION_ENUM[bridge['source']]},",
                "    .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,",
                f"    .layer_count = {len(frame['layers'])}u,",
                "    .layers = {",
                layers,
                "    },",
                "};",
            ])
            descriptor_lines.append(
                "    {.cue = %s, .source_phase = %s, .target_pbm_filename = %s, .duration_ms = %du}," % (
                    c_quote(frame["cue"]), c_quote(str(frame["source_phase"])),
                    c_quote(frame["target_pbm_filename"]), frame["duration_ms"]))
            score_lines.append(
                "    {.phase = %s, .duration_ms = %du, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, "
                ".emotion = %s, .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER, "
                ".energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, "
                ".phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &%s}," % (
                    SCORE_PHASE_ENUM[frame["cue"]], frame["duration_ms"], EMOTION_ENUM[bridge["source"]], symbol))
        blocks.extend([
            "",
            f"static const comp_v22_emotion_separation_rig_frame_t k_v22_bridge_{bridge_index}_frames[] = {{",
            "\n".join(descriptor_lines),
            "};",
            "",
            f"static const comp_expression_rig_registered_score_step_t k_v22_bridge_{bridge_index}_steps[] = {{",
            "\n".join(score_lines),
            "};",
            "",
            f"static const comp_expression_rig_registered_performance_score_t k_v22_bridge_{bridge_index}_score = {{",
            f"    .steps = k_v22_bridge_{bridge_index}_steps,",
            f"    .step_count = (uint8_t)(sizeof(k_v22_bridge_{bridge_index}_steps) / sizeof(k_v22_bridge_{bridge_index}_steps[0])),",
            "};",
        ])
        bridge_entries.append(
            "    {.name = %s, .source_emotion = %s, .target_emotion = %s, .event_name = %s, "
            ".score = &k_v22_bridge_%d_score, .frames = k_v22_bridge_%d_frames, "
            ".frame_count = (uint8_t)(sizeof(k_v22_bridge_%d_frames) / sizeof(k_v22_bridge_%d_frames[0]))}," % (
                c_quote(bridge["name"]), c_quote(bridge["source"]), c_quote(bridge["target"]),
                c_quote(str(bridge["event"])), bridge_index, bridge_index, bridge_index, bridge_index))
    blocks.extend([
        "",
        "static const comp_v22_emotion_separation_rig_bridge_t k_v22_bridges[] = {",
        "\n".join(bridge_entries),
        "};",
        "",
        "const comp_expression_rig_profile_t *comp_v22_emotion_separation_rig_candidate_profile(void)",
        "{",
        "    return &k_v22_profile;",
        "}",
        "",
        "bool comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed(void)",
        "{",
        "    return false;",
        "}",
        "",
        "uint8_t comp_v22_emotion_separation_rig_candidate_bridge_count(void)",
        "{",
        "    return (uint8_t)(sizeof(k_v22_bridges) / sizeof(k_v22_bridges[0]));",
        "}",
        "",
        "const comp_v22_emotion_separation_rig_bridge_t *comp_v22_emotion_separation_rig_candidate_bridge(uint8_t index)",
        "{",
        "    if (index >= comp_v22_emotion_separation_rig_candidate_bridge_count()) {",
        "        return NULL;",
        "    }",
        "    return &k_v22_bridges[index];",
        "}",
        "",
    ])
    return "\n".join(blocks)


def build_artifacts() -> dict[str, tuple[bytes, pathlib.Path]]:
    source_preconditions()
    export_layout = load_json(EXPORT_LAYOUT)
    bridge_layout = load_json(BRIDGE_LAYOUT)
    require(export_layout.get("locked_v9_source_sha256") == LOCKED_V9_SHA256 and
            export_layout.get("runtime_resource_activated") is False and
            export_layout.get("active_candidate_binding") == "forbidden" and
            bridge_layout.get("runtime_resource_activated") is False and
            bridge_layout.get("active_candidate_binding") == "forbidden",
            "V22 source lineage or inactive-binding contract drifted")
    components = normalize_components(export_layout, bridge_layout)
    bridges = normalize_bridges(bridge_layout, components)
    pack, packed_components = build_pack(components)
    pack_path = OUTPUT / "companion-v22-emotion-separation-rig-candidate-200x200.crig"
    pack_metadata_path = OUTPUT / "companion-v22-emotion-separation-rig-candidate-200x200.crig.json"
    layout_path = OUTPUT / "v22-emotion-separation-target-rig-layout.json"
    total_frames = sum(len(bridge["frames"]) for bridge in bridges)
    pack_metadata = {
        "schema": "companion.expression_rig_component_pack.v1",
        "status": "CANDIDATE_OWNER_ACCEPTED_RUNTIME_INACTIVE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "revision": V22_REVISION,
        "source": "locked_v9_identity_baseline",
        "source_sha256": LOCKED_V9_SHA256,
        "v22_generated_source": export_layout.get("generated_source"),
        "v22_generated_source_sha256": export_layout.get("generated_source_sha256"),
        "profile": {"width": 200, "height": 200, "stride_bytes": 25,
                    "pixel_format": "mono_1bpp_white_is_one_msb", "safe_inset_px": SAFE_INSET_PX},
        "pack": rel(pack_path),
        "pack_sha256": hashlib.sha256(pack).hexdigest().upper(),
        "total_size": len(pack),
        "components": packed_components,
        "whole_face_source_card_playback": "forbidden",
        "special_event_fallback": "fail_closed",
    }
    target_layout = {
        "schema": "companion.v22_emotion_separation_target_rig.v1",
        "status": "CANDIDATE_OWNER_ACCEPTED_RUNTIME_INACTIVE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "v22_generated_source": export_layout.get("generated_source"),
        "v22_generated_source_sha256": export_layout.get("generated_source_sha256"),
        "source_component_layout": rel(EXPORT_LAYOUT),
        "source_component_layout_sha256": sha256(EXPORT_LAYOUT),
        "source_bridge_layout": rel(BRIDGE_LAYOUT),
        "source_bridge_layout_sha256": sha256(BRIDGE_LAYOUT),
        "component_export_gate": rel(COMPONENT_GATE),
        "component_bridge_gate": rel(BRIDGE_GATE),
        "owner_art_screen_review": rel(OWNER_REVIEW),
        "pack": rel(pack_path),
        "pack_sha256": hashlib.sha256(pack).hexdigest().upper(),
        "generated_header": rel(HEADER),
        "generated_source": rel(SOURCE),
        "component_count": len(packed_components),
        "bridge_count": len(bridges),
        "bridge_frame_count": total_frames,
        "components": packed_components,
        "bridges": bridges,
        "whole_source_pose_playback": "forbidden",
        "full_face_replacement": "forbidden",
        "special_event_fallback": {"menu": "fail_closed", "recording": "fail_closed", "upgrade": "fail_closed",
                                   "sleep": "fail_closed", "charging": "fail_closed", "error": "fail_closed"},
    }
    return {
        "pack": (pack, pack_path),
        "pack_metadata": (json_bytes(pack_metadata), pack_metadata_path),
        "layout": (json_bytes(target_layout), layout_path),
        "header": (render_header(len(components)).encode("ascii"), HEADER),
        "source": (render_source(components, bridges).encode("ascii"), SOURCE),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated target artifacts without writing")
    args = parser.parse_args()
    try:
        artifacts = build_artifacts()
        ok = all(write_or_check(path, data, args.check) for data, path in artifacts.values())
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as exc:
        print(f"FAIL: {exc}")
        return 1
    if not ok:
        print("FAIL: V22 target Rig artifacts drifted")
        return 1
    print("PASS: V22 external-NOR CRIG and target bridge profile are generated from the accepted component plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
