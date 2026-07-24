#!/usr/bin/env python3
"""Generate an inactive V36 Daily-down external-NOR Rig from the browser plan."""

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
V36_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v36-directional-eye-gaze-source"
ATTEMPT_NUMBER = 9
ATTEMPT: pathlib.Path
SOURCE_GATE: pathlib.Path
PREVIEW_GATE: pathlib.Path
REPLAY_GATE: pathlib.Path
BROWSER_CAPTURE_GATE: pathlib.Path
OUTPUT: pathlib.Path
HEADER: pathlib.Path
SOURCE: pathlib.Path
PACK_FILENAME: str
PROFILE_MACRO: str
PROFILE_FRAME_TYPE: str
PROFILE_API: str

LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V36_REVISION = 36
CANVAS = (200, 200)
STRIDE = 25
SAFE_INSET_PX = 4
HEADER_BYTES = 80
INDEX_ENTRY_BYTES = 20
EXPECTED_PHASES = ("rest", "eyes_lower_1", "eyes_lower_2", "down_hold", "eyes_return", "rest_dwell")
ATTEMPT_STATUSES = {
    "MACHINE_SOURCE_BROWSER_AND_EDGE_REPLAY_PASS_PENDING_OWNER_DIRECTION_AND_TARGET_PARITY",
    "MACHINE_SOURCE_BROWSER_AND_TARGET_HOST_PASS_PENDING_OWNER_DIRECTION",
}
ROLE_ENUM = {
    "star": "COMP_EXPRESSION_RIG_ROLE_CHARM",
    "left_brow": "COMP_EXPRESSION_RIG_ROLE_LEFT_BROW",
    "right_brow": "COMP_EXPRESSION_RIG_ROLE_RIGHT_BROW",
    "left_eye_body": "COMP_EXPRESSION_RIG_ROLE_LEFT_EYE",
    "right_eye_body": "COMP_EXPRESSION_RIG_ROLE_RIGHT_EYE",
    "left_cheek": "COMP_EXPRESSION_RIG_ROLE_LEFT_CHEEK",
    "right_cheek": "COMP_EXPRESSION_RIG_ROLE_RIGHT_CHEEK",
    "nose": "COMP_EXPRESSION_RIG_ROLE_NOSE",
    "mouth": "COMP_EXPRESSION_RIG_ROLE_MOUTH",
    "v9_left_primary": "COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT",
    "v9_right_primary": "COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT",
    "v9_left_sparkle": "COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE",
    "v9_right_sparkle": "COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE",
    "down_left_primary": "COMP_EXPRESSION_RIG_ROLE_LEFT_HIGHLIGHT",
    "down_right_primary": "COMP_EXPRESSION_RIG_ROLE_RIGHT_HIGHLIGHT",
    "down_left_sparkle": "COMP_EXPRESSION_RIG_ROLE_LEFT_SPARKLE",
    "down_right_sparkle": "COMP_EXPRESSION_RIG_ROLE_RIGHT_SPARKLE",
}
Z_INDEX = {
    "star": 10, "left_brow": 20, "right_brow": 20,
    "left_eye_body": 30, "right_eye_body": 30,
    "v9_left_primary": 31, "v9_right_primary": 31,
    "down_left_primary": 31, "down_right_primary": 31,
    "v9_left_sparkle": 32, "v9_right_sparkle": 32,
    "down_left_sparkle": 32, "down_right_sparkle": 32,
    "left_cheek": 40, "right_cheek": 40, "nose": 50, "mouth": 60,
}
SCORE_PHASE = {
    "rest": "COMP_EXPRESSION_RIG_SCORE_PHASE_ENTRY",
    "eyes_lower_1": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "eyes_lower_2": "COMP_EXPRESSION_RIG_SCORE_PHASE_LEAD",
    "down_hold": "COMP_EXPRESSION_RIG_SCORE_PHASE_HOLD",
    "eyes_return": "COMP_EXPRESSION_RIG_SCORE_PHASE_RETURN",
    "rest_dwell": "COMP_EXPRESSION_RIG_SCORE_PHASE_SETTLE",
}


def configure_attempt(attempt_number: int) -> None:
    global ATTEMPT_NUMBER, ATTEMPT, SOURCE_GATE, PREVIEW_GATE, REPLAY_GATE, BROWSER_CAPTURE_GATE
    global OUTPUT, HEADER, SOURCE, PACK_FILENAME, PROFILE_MACRO, PROFILE_FRAME_TYPE, PROFILE_API

    if attempt_number < 1 or attempt_number > 99:
        raise ValueError("V36 attempt number must be between 1 and 99")
    ATTEMPT_NUMBER = attempt_number
    suffix = "" if attempt_number == 9 else f"-attempt-{attempt_number:02d}"
    ATTEMPT = V36_ROOT / "candidate" / f"attempt-{attempt_number:02d}-generated-daily-down.json"
    SOURCE_GATE = ROOT / "docs/validation" / f"companion-v36-daily-down-reflection-source-gate{suffix}-20260720.json"
    PREVIEW_GATE = ROOT / "docs/validation" / f"companion-v36-daily-down-reflection-browser-preview{suffix}-20260720.json"
    REPLAY_GATE = ROOT / "docs/validation" / f"companion-v36-daily-down-reflection-browser-replay{suffix}-20260720.json"
    BROWSER_CAPTURE_GATE = ROOT / "docs/validation" / f"companion-v36-daily-down-reflection-browser-capture{suffix}-20260720.json"
    OUTPUT = V36_ROOT / "candidate" / f"target-rig-attempt-{attempt_number:02d}"
    if attempt_number == 9:
        profile_stem = "expression_rig_v36_daily_down_candidate_profile"
        PROFILE_MACRO = "COMP_V36_DAILY_DOWN_RIG_CANDIDATE"
        PROFILE_FRAME_TYPE = "comp_v36_daily_down_rig_frame_t"
        PROFILE_API = "comp_v36_daily_down_rig_candidate"
        PACK_FILENAME = "companion-v36-daily-down-rig-candidate-200x200.crig"
    else:
        profile_stem = f"expression_rig_v36_daily_down_attempt_{attempt_number:02d}_candidate_profile"
        PROFILE_MACRO = f"COMP_V36_DAILY_DOWN_ATTEMPT_{attempt_number:02d}_RIG_CANDIDATE"
        PROFILE_FRAME_TYPE = f"comp_v36_daily_down_attempt_{attempt_number:02d}_rig_frame_t"
        PROFILE_API = f"comp_v36_daily_down_attempt_{attempt_number:02d}_rig_candidate"
        PACK_FILENAME = f"companion-v36-daily-down-attempt-{attempt_number:02d}-rig-candidate-200x200.crig"
    HEADER = ROOT / "app/companion_pendant/epaper/generated" / f"{profile_stem}.h"
    SOURCE = ROOT / "app/companion_pendant/epaper/generated" / f"{profile_stem}.c"


configure_attempt(ATTEMPT_NUMBER)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def write_or_check(path: pathlib.Path, data: bytes, check: bool) -> bool:
    if check:
        return path.is_file() and path.read_bytes() == data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def variant(name: str) -> str:
    if "eye_body" in name or "primary" in name or "sparkle" in name:
        return "COMP_EXPRESSION_RIG_VARIANT_OPEN"
    return "COMP_EXPRESSION_RIG_VARIANT_DEFAULT"


def source_preconditions() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    attempt = load_json(ATTEMPT)
    source_gate = load_json(SOURCE_GATE)
    preview_gate = load_json(PREVIEW_GATE)
    replay_gate = load_json(REPLAY_GATE)
    browser_gate = load_json(BROWSER_CAPTURE_GATE)
    require(attempt.get("status") in ATTEMPT_STATUSES and
            attempt.get("runtime_resource_activated") is False and
            attempt.get("active_candidate_binding") == "forbidden" and
            attempt.get("source_reference_sha256") == LOCKED_V9_SHA256,
            "V36 down attempt is not an inactive locked-V9 target candidate")
    require(source_gate.get("status") == "PASS_V36_DIRECTIONAL_REFLECTION_SOURCE_GATE" and
            preview_gate.get("status") == "PASS_COMPONENT_ONLY_DIRECTIONAL_BROWSER_PREVIEW_GATE" and
            replay_gate.get("status") == "PASS_V36_DIRECTIONAL_REFLECTION_BROWSER_REPLAY_GATE" and
            browser_gate.get("status") == "PASS_V36_DAILY_DOWN_REFLECTION_BROWSER_CAPTURE_GATE",
            "V36 source/browser machine gates must pass before target Rig export")
    for gate in (source_gate, preview_gate, replay_gate, browser_gate):
        require(gate.get("runtime_resource_activated") is False and
                gate.get("active_candidate_binding") == "forbidden",
                "V36 source/browser gate unexpectedly activated candidate")
    require(sha256(SOURCE_GATE) == attempt["machine_evidence"]["source_gate"]["sha256"] and
            sha256(PREVIEW_GATE) == attempt["machine_evidence"]["browser_preview"]["sha256"] and
            sha256(REPLAY_GATE) == attempt["machine_evidence"]["browser_replay"]["sha256"] and
            sha256(BROWSER_CAPTURE_GATE) == attempt["machine_evidence"]["edge_browser_capture"]["sha256"],
            "attempt evidence hash drifted")
    data_path = ROOT / str(preview_gate.get("data", ""))
    require(data_path.is_file() and sha256(data_path) == preview_gate.get("data_sha256"),
            "browser component plan drifted")
    data = load_json(data_path)
    require(data.get("canvas") == {"width": 200, "height": 200} and
            data.get("component_only") is True and data.get("full_face_cards") is False and
            data.get("random_motion") is False and
            data.get("runtime_resource_activated") is False and
            data.get("active_candidate_binding") == "forbidden",
            "browser data is not the inactive component-only V36 plan")
    return data, preview_gate, source_gate


def normalize_plan(data: dict[str, Any], source_gate: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assets = data.get("assets")
    story = data.get("story")
    replay = data.get("frame_replay")
    require(isinstance(assets, dict) and isinstance(story, list) and isinstance(replay, list) and
            len(story) == len(replay) == len(EXPECTED_PHASES) and
            tuple(step.get("phase") for step in story) == EXPECTED_PHASES and
            tuple(step.get("phase") for step in replay) == EXPECTED_PHASES,
            "V36 browser plan phase order drifted")
    require(set(assets) == set(ROLE_ENUM), "V36 browser component vocabulary drifted")
    native_hold = ROOT / str(source_gate.get("native_200_hold", {}).get("path", ""))
    down_component_root = native_hold.parent.parent / "components"
    down_component_root_rel = rel(down_component_root) + "/"
    registered_down_hashes = source_gate.get("component_hashes")
    require(native_hold.is_file() and isinstance(registered_down_hashes, dict),
            "V36 source gate does not register its candidate components")
    positions: dict[str, list[tuple[int, int]]] = {name: [] for name in assets}
    for step, expected in zip(story, replay):
        require(step.get("layers") == expected.get("layers") and
                isinstance(step.get("duration_ms"), int) and step["duration_ms"] >= 80 and
                isinstance(expected.get("target_pbm"), str) and isinstance(expected.get("target_pbm_sha256"), str),
                f"V36 browser frame metadata drifted: {step.get('phase')}")
        seen: set[str] = set()
        for layer in step["layers"]:
            name = layer.get("asset")
            position = layer.get("position")
            require(name in assets and name not in seen and isinstance(position, list) and len(position) == 2 and
                    all(isinstance(value, int) for value in position),
                    f"V36 browser layer is invalid: {step.get('phase')}")
            seen.add(name)
            positions[name].append((position[0], position[1]))
        require(len(seen) == 13, f"V36 browser frame must contain exactly 13 component layers: {step.get('phase')}")
    components: list[dict[str, Any]] = []
    for component_id, name in enumerate(sorted(assets), start=1):
        asset = assets[name]
        require(isinstance(asset, dict) and asset.get("color") in {"black", "white"} and
                isinstance(asset.get("source_mask"), str) and isinstance(asset.get("source_sha256"), str) and
                name in ROLE_ENUM and positions[name], f"V36 asset is invalid: {name}")
        mask = ROOT / str(asset["source_mask"])
        source = str(asset["source_mask"])
        if not source.startswith("docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components/"):
            require(source.startswith(down_component_root_rel) and
                    registered_down_hashes.get(pathlib.PurePosixPath(source).name) == str(asset["source_sha256"]).upper(),
                    f"V36 asset provenance drifted: {name}")
        require(mask.is_file() and sha256(mask) == str(asset["source_sha256"]).upper(),
                f"V36 asset hash drifted: {name}")
        with Image.open(mask) as image:
            mono = image.convert("1")
            width, height = mono.size
            raw = mono.tobytes()
        base_x = min(position[0] for position in positions[name])
        base_y = min(position[1] for position in positions[name])
        components.append({
            "component_id": component_id, "name": name, "role": ROLE_ENUM[name],
            "mask": rel(mask), "mask_sha256": str(asset["source_sha256"]).upper(),
            "base_position": [base_x, base_y],
            "offset_range": {
                "min": [min(position[0] - base_x for position in positions[name]),
                        min(position[1] - base_y for position in positions[name])],
                "max": [max(position[0] - base_x for position in positions[name]),
                        max(position[1] - base_y for position in positions[name])],
            },
            "z_index": Z_INDEX[name], "composite_op": "erase" if asset["color"] == "white" else "ink",
            "width": width, "height": height, "stride_bytes": (width + 7) // 8,
            "data_size": len(raw), "data_crc32": f"{zlib.crc32(raw) & 0xFFFFFFFF:08X}",
        })
    by_name = {component["name"]: component for component in components}
    frames: list[dict[str, Any]] = []
    for index, (step, expected) in enumerate(zip(story, replay)):
        pbm = ROOT / str(expected["target_pbm"])
        require(pbm.is_file() and sha256(pbm) == expected["target_pbm_sha256"],
                f"V36 registered target PBM drifted: {step['phase']}")
        with Image.open(pbm) as image:
            require(image.convert("1").size == CANVAS, f"V36 target PBM is not 200x200: {step['phase']}")
        layers: list[dict[str, Any]] = []
        for layer in step["layers"]:
            component = by_name[str(layer["asset"])]
            position = layer["position"]
            offset = [position[0] - component["base_position"][0], position[1] - component["base_position"][1]]
            minimum, maximum = component["offset_range"]["min"], component["offset_range"]["max"]
            require(minimum[0] <= offset[0] <= maximum[0] and minimum[1] <= offset[1] <= maximum[1],
                    f"V36 target layer offset exceeds registered range: {step['phase']}")
            layers.append({"component": component["name"], "component_id": component["component_id"], "offset": offset})
        frames.append({
            "index": index, "phase": step["phase"], "duration_ms": step["duration_ms"],
            "reason": step.get("reason"), "layers": layers,
            "target_pbm": rel(pbm), "target_pbm_sha256": str(expected["target_pbm_sha256"]).upper(),
            "target_pbm_filename": pbm.name,
        })
    require(len(components) == 17 and all(len(frame["layers"]) == 13 for frame in frames),
            "V36 target component/frame cardinality drifted")
    return components, frames


def build_pack(components: list[dict[str, Any]]) -> tuple[bytes, list[dict[str, Any]]]:
    index = bytearray()
    payload = bytearray()
    packed: list[dict[str, Any]] = []
    data_offset = HEADER_BYTES + INDEX_ENTRY_BYTES * len(components)
    for component in components:
        with Image.open(ROOT / component["mask"]) as image:
            raw = image.convert("1").tobytes()
        offset = data_offset + len(payload)
        crc = zlib.crc32(raw) & 0xFFFFFFFF
        index.extend(struct.pack("<HHHHIII", component["component_id"], component["width"], component["height"],
                                 component["stride_bytes"], offset, len(raw), crc))
        payload.extend(raw)
        packed.append({**component, "data_offset": offset, "data_crc32": f"{crc:08X}"})
    header = bytearray(HEADER_BYTES)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, HEADER_BYTES)
    struct.pack_into("<I", header, 8, data_offset + len(payload))
    struct.pack_into("<I", header, 12, V36_REVISION)
    struct.pack_into("<HHH", header, 16, CANVAS[0], CANVAS[1], STRIDE)
    header[22], header[23] = 1, SAFE_INSET_PX
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED_V9_SHA256)
    return bytes(header) + bytes(index) + bytes(payload), packed


def render_header(component_count: int, frame_count: int) -> str:
    guard = "COMPANION_EPAPER_EXPRESSION_RIG_V36_DAILY_DOWN_CANDIDATE_PROFILE_H" if ATTEMPT_NUMBER == 9 else \
        f"COMPANION_EPAPER_EXPRESSION_RIG_{PROFILE_MACRO}_PROFILE_H"
    return f'''/* Generated by tools/generate_companion_v36_daily_down_target_rig.py; do not hand edit. */
#ifndef {guard}
#define {guard}

#include "expression_rig_performance_score.h"

#include <stdbool.h>
#include <stdint.h>

#define {PROFILE_MACRO}_REVISION {V36_REVISION}u
#define {PROFILE_MACRO}_COMPONENT_COUNT {component_count}u
#define {PROFILE_MACRO}_FRAME_COUNT {frame_count}u
#define {PROFILE_MACRO}_SOURCE_SHA256 "{LOCKED_V9_SHA256}"

typedef struct {{
    const char *phase;
    const char *target_pbm_filename;
    uint16_t duration_ms;
}} {PROFILE_FRAME_TYPE};

const comp_expression_rig_profile_t *{PROFILE_API}_profile(void);
bool {PROFILE_API}_runtime_activation_allowed(void);
const comp_expression_rig_registered_performance_score_t *{PROFILE_API}_score(void);
const {PROFILE_FRAME_TYPE} *{PROFILE_API}_frames(void);

#endif /* {guard} */
'''


def c_quote(value: str) -> str:
    require(value and all(32 <= ord(char) < 127 and char not in {'"', '\\'} for char in value),
            "generated C string contains unsupported characters")
    return f'"{value}"'


def render_source(components: list[dict[str, Any]], frames: list[dict[str, Any]]) -> str:
    component_lines = []
    for component in components:
        minimum, maximum = component["offset_range"]["min"], component["offset_range"]["max"]
        operation = "COMP_EXPRESSION_RIG_COMPOSITE_ERASE" if component["composite_op"] == "erase" else "COMP_EXPRESSION_RIG_COMPOSITE_INK"
        component_lines.append(
            "    {.component_id = %du, .role = %s, .variant = %s, .base_x = %d, .base_y = %d, "
            ".min_offset_x = %d, .min_offset_y = %d, .max_offset_x = %d, .max_offset_y = %d, "
            ".z_index = %du, .composite_op = %s}," % (
                component["component_id"], component["role"], variant(component["name"]),
                component["base_position"][0], component["base_position"][1], minimum[0], minimum[1],
                maximum[0], maximum[1], component["z_index"], operation))
    blocks = [
        "/* Generated from the V36 Daily-down browser component plan; do not hand edit. */",
        f"#include \"{HEADER.name}\"",
        "",
        "static const comp_expression_rig_component_info_t k_v36_components[] = {",
        "\n".join(component_lines),
        "};",
        "",
        "static const comp_expression_rig_profile_t k_v36_profile = {",
        "    .components = k_v36_components,",
        f"    .component_count = {PROFILE_MACRO}_COMPONENT_COUNT,",
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
    descriptors: list[str] = []
    score_steps: list[str] = []
    for frame in frames:
        symbol = f"k_v36_frame_{frame['index']}_pose"
        layers = "\n".join(
            "            {.component_id = %du, .offset_x = %d, .offset_y = %d, .dynamic_flags = 0u}," %
            (layer["component_id"], layer["offset"][0], layer["offset"][1]) for layer in frame["layers"])
        blocks.extend([
            "", f"static const comp_expression_rig_registered_pose_t {symbol} = {{",
            "    .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,",
            "    .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,",
            "    .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN,",
            f"    .layer_count = {len(frame['layers'])}u,",
            "    .layers = {", layers, "    },", "};",
        ])
        descriptors.append("    {.phase = %s, .target_pbm_filename = %s, .duration_ms = %du}," % (
            c_quote(frame["phase"]), c_quote(frame["target_pbm_filename"]), frame["duration_ms"]))
        score_steps.append(
            "    {.phase = %s, .duration_ms = %du, .state = {.scene = COMP_EXPRESSION_RIG_SCENE_DAILY, "
            ".emotion = COMP_EXPRESSION_RIG_EMOTION_CALM, .attention = COMP_EXPRESSION_RIG_ATTENTION_DOWN, "
            ".energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL, .interaction_memory = 0u, "
            ".phase = COMP_EXPRESSION_RIG_PHASE_SUSTAIN}, .pose = &%s}," %
            (SCORE_PHASE[frame["phase"]], frame["duration_ms"], symbol))
    blocks.extend([
        f"", f"static const {PROFILE_FRAME_TYPE} k_v36_frames[] = {{", "\n".join(descriptors), "};",
        "", "static const comp_expression_rig_registered_score_step_t k_v36_steps[] = {", "\n".join(score_steps), "};",
        "", "static const comp_expression_rig_registered_performance_score_t k_v36_score = {",
        "    .steps = k_v36_steps,",
        "    .step_count = (uint8_t)(sizeof(k_v36_steps) / sizeof(k_v36_steps[0])),",
        "};",
        "", f"const comp_expression_rig_profile_t *{PROFILE_API}_profile(void)", "{", "    return &k_v36_profile;", "}",
        "", f"bool {PROFILE_API}_runtime_activation_allowed(void)", "{", "    return false;", "}",
        "", f"const comp_expression_rig_registered_performance_score_t *{PROFILE_API}_score(void)", "{", "    return &k_v36_score;", "}",
        "", f"const {PROFILE_FRAME_TYPE} *{PROFILE_API}_frames(void)", "{", "    return k_v36_frames;", "}", "",
    ])
    return "\n".join(blocks)


def build_artifacts() -> dict[str, tuple[bytes, pathlib.Path]]:
    data, preview_gate, source_gate = source_preconditions()
    components, frames = normalize_plan(data, source_gate)
    pack, packed_components = build_pack(components)
    pack_path = OUTPUT / PACK_FILENAME
    metadata_path = OUTPUT / f"{PACK_FILENAME}.json"
    layout_path = OUTPUT / "v36-daily-down-target-rig-layout.json"
    status = "CANDIDATE_MACHINE_PARITY_PENDING_TARGET_HOST_AND_OWNER_DIRECTION"
    metadata = {
        "schema": "companion.expression_rig_component_pack.v1", "status": status,
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "revision": V36_REVISION, "source": "locked_v9_identity_plus_v36_down_reflection_components",
        "source_sha256": LOCKED_V9_SHA256, "profile": {"width": 200, "height": 200, "stride_bytes": 25,
            "pixel_format": "mono_1bpp_white_is_one_msb", "safe_inset_px": SAFE_INSET_PX},
        "pack": rel(pack_path), "pack_sha256": hashlib.sha256(pack).hexdigest().upper(),
        "total_size": len(pack), "components": packed_components,
        "whole_face_source_card_playback": "forbidden", "special_event_fallback": "fail_closed",
    }
    layout = {
        "schema": "companion.v36_daily_down_target_rig.v1", "status": status,
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden",
        "locked_v9_source_sha256": LOCKED_V9_SHA256, "attempt": rel(ATTEMPT), "attempt_sha256": sha256(ATTEMPT),
        "browser_preview_gate": rel(PREVIEW_GATE), "browser_preview_gate_sha256": sha256(PREVIEW_GATE),
        "browser_player_data": str(preview_gate["data"]), "browser_player_data_sha256": str(preview_gate["data_sha256"]),
        "pack": rel(pack_path), "pack_sha256": hashlib.sha256(pack).hexdigest().upper(),
        "generated_header": rel(HEADER), "generated_source": rel(SOURCE),
        "component_count": len(packed_components), "frame_count": len(frames), "components": packed_components, "frames": frames,
        "whole_source_pose_playback": "forbidden", "full_face_replacement": "forbidden",
        "special_event_fallback": {"menu": "fail_closed", "recording": "fail_closed", "upgrade": "fail_closed",
            "sleep": "fail_closed", "charging": "fail_closed", "error": "fail_closed"},
    }
    return {
        "pack": (pack, pack_path), "pack_metadata": (json_bytes(metadata), metadata_path),
        "layout": (json_bytes(layout), layout_path),
        "header": (render_header(len(components), len(frames)).encode("ascii"), HEADER),
        "source": (render_source(components, frames).encode("ascii"), SOURCE),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, default=9, help="Use a separately versioned V36 Daily-down candidate.")
    parser.add_argument("--check", action="store_true", help="verify generated target artifacts without writing")
    args = parser.parse_args()
    try:
        configure_attempt(args.attempt)
        artifacts = build_artifacts()
        ok = all(write_or_check(path, data, args.check) for data, path in artifacts.values())
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as exc:
        print(f"FAIL: {exc}")
        return 1
    if not ok:
        print("FAIL: V36 target Rig artifacts drifted")
        return 1
    print("PASS: V36 Daily-down external-NOR CRIG and target score are generated from the browser component plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
