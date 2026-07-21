#!/usr/bin/env python3
"""Verify the inactive V22 CRIG/profile target path against its accepted bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys
import zlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from generate_companion_v22_emotion_separation_target_rig import (  # noqa: E402
    BRIDGE_LAYOUT,
    HEADER_BYTES,
    INDEX_ENTRY_BYTES,
    LOCKED_V9_SHA256,
    OUTPUT,
    V22_REVISION,
    build_artifacts,
)


DEFAULT_WRITE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
PACK = OUTPUT / "companion-v22-emotion-separation-rig-candidate-200x200.crig"
LAYOUT = OUTPUT / "v22-emotion-separation-target-rig-layout.json"
HOST_EVIDENCE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-wba-host-20260719.json"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def verify() -> dict[str, Any]:
    errors: list[str] = []
    expected = build_artifacts()
    expected_pack, expected_pack_path = expected["pack"]
    expected_layout, expected_layout_path = expected["layout"]
    expected_header, expected_header_path = expected["header"]
    expected_source, expected_source_path = expected["source"]
    expected_metadata, expected_metadata_path = expected["pack_metadata"]
    for label, path, content in (
        ("pack", expected_pack_path, expected_pack),
        ("layout", expected_layout_path, expected_layout),
        ("header", expected_header_path, expected_header),
        ("source", expected_source_path, expected_source),
        ("pack metadata", expected_metadata_path, expected_metadata),
    ):
        if not path.is_file() or path.read_bytes() != content:
            errors.append(f"generated V22 target {label} drifted")

    target = load_json(LAYOUT)
    bridge = load_json(BRIDGE_LAYOUT)
    host = load_json(HOST_EVIDENCE)
    pack = PACK.read_bytes() if PACK.is_file() else b""
    if len(pack) < HEADER_BYTES or pack[0:4] != b"CRIG":
        errors.append("V22 CRIG header is missing or has invalid magic")
    else:
        version, header_bytes = struct.unpack_from("<HH", pack, 4)
        total_size, revision = struct.unpack_from("<II", pack, 8)
        width, height, stride = struct.unpack_from("<HHH", pack, 16)
        component_count = struct.unpack_from("<H", pack, 24)[0]
        index_offset, data_offset, payload_crc, index_crc = struct.unpack_from("<IIII", pack, 28)
        source_sha = pack[44:76].hex().upper()
        expected_components = target.get("components")
        if version != 1 or header_bytes != HEADER_BYTES or total_size != len(pack) or revision != V22_REVISION:
            errors.append("V22 CRIG version, size, or revision drifted")
        if (width, height, stride, pack[22], pack[23]) != (200, 200, 25, 1, 4):
            errors.append("V22 CRIG canvas contract drifted")
        if source_sha != LOCKED_V9_SHA256:
            errors.append("V22 CRIG must retain the locked V9 identity SHA in its header")
        if not isinstance(expected_components, list) or component_count != len(expected_components) or \
                component_count != 37 or index_offset != HEADER_BYTES or \
                data_offset != HEADER_BYTES + component_count * INDEX_ENTRY_BYTES:
            errors.append("V22 CRIG component index layout drifted")
        elif data_offset <= len(pack):
            index = pack[index_offset:data_offset]
            payload = pack[data_offset:]
            if zlib.crc32(index) & 0xFFFFFFFF != index_crc or zlib.crc32(payload) & 0xFFFFFFFF != payload_crc:
                errors.append("V22 CRIG index or payload CRC drifted")
            else:
                for index_number, component in enumerate(expected_components):
                    offset = index_number * INDEX_ENTRY_BYTES
                    component_id, component_width, component_height, component_stride, component_offset, component_size, component_crc = \
                        struct.unpack_from("<HHHHIII", index, offset)
                    if component_id != component.get("component_id") or \
                            (component_width, component_height, component_stride, component_size) != \
                            (component.get("width"), component.get("height"), component.get("stride_bytes"), component.get("data_size")) or \
                            component_offset != component.get("data_offset") or \
                            component_offset < data_offset or component_offset + component_size > len(pack) or \
                            zlib.crc32(pack[component_offset:component_offset + component_size]) & 0xFFFFFFFF != component_crc:
                        errors.append(f"V22 CRIG component entry {index_number} drifted")
                        break

    target_bridges = target.get("bridges")
    source_bridges = bridge.get("bridges")
    if not isinstance(target_bridges, list) or not isinstance(source_bridges, dict) or len(target_bridges) != 10:
        errors.append("V22 target bridge graph is incomplete")
    else:
        frame_count = 0
        for target_bridge in target_bridges:
            name = target_bridge.get("name")
            source_bridge = source_bridges.get(name)
            frames = target_bridge.get("frames")
            if not isinstance(name, str) or not isinstance(source_bridge, dict) or not isinstance(frames, list) or \
                    len(frames) != len(source_bridge.get("frames", [])):
                errors.append(f"V22 target bridge {name!r} drifted from browser/PBM plan")
                continue
            for target_frame, source_frame in zip(frames, source_bridge["frames"]):
                frame_count += 1
                expected_layer_plan = [
                    {"component": layer.get("component"), "offset": layer.get("offset")}
                    for layer in source_frame.get("layers", [])
                ]
                actual_layer_plan = [
                    {"component": layer.get("component"), "offset": layer.get("offset")}
                    for layer in target_frame.get("layers", [])
                ]
                if target_frame.get("cue") != source_frame.get("cue") or \
                        target_frame.get("duration_ms") != source_frame.get("duration_ms") or \
                        target_frame.get("target_pbm") != source_frame.get("target_pbm") or \
                        target_frame.get("target_pbm_sha256") != source_frame.get("target_pbm_sha256") or \
                        actual_layer_plan != expected_layer_plan:
                    errors.append(f"V22 target frame plan drifted: {name}/{target_frame.get('index')}")
                    break
        if frame_count != 72 or target.get("bridge_frame_count") != 72:
            errors.append("V22 target bridge sample count must remain 72")

    if target.get("status") != "CANDIDATE_OWNER_ACCEPTED_RUNTIME_INACTIVE" or \
            target.get("runtime_resource_activated") is not False or \
            target.get("active_candidate_binding") != "forbidden" or \
            target.get("whole_source_pose_playback") != "forbidden" or \
            target.get("full_face_replacement") != "forbidden" or \
            target.get("special_event_fallback") != {
                "menu": "fail_closed", "recording": "fail_closed", "upgrade": "fail_closed",
                "sleep": "fail_closed", "charging": "fail_closed", "error": "fail_closed"}:
        errors.append("V22 target candidate activation or fail-closed policy drifted")
    if host.get("status") != "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_WBA_EXTERNAL_NOR_PARITY" or \
            host.get("targets") != ["WBA55", "WBA65"] or host.get("bridge_count") != 10 or \
            host.get("runtime_resource_activated") is not False or host.get("special_event_fallback") != "fail_closed" or \
            host.get("whole_face_source_card_playback") != "forbidden":
        errors.append("V22 WBA external-NOR parity host evidence is incomplete")

    return {
        "schema": "companion.v22_emotion_separation_target_rig_gate.v1",
        "status": "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE" if not errors else
                  "FAIL_V22_EMOTION_SEPARATION_TARGET_RIG_GATE",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "pack": str(PACK.relative_to(ROOT)).replace("\\", "/"),
        "pack_sha256": sha256(PACK) if PACK.is_file() else None,
        "component_count": target.get("component_count"),
        "bridge_count": target.get("bridge_count"),
        "bridge_frame_count": target.get("bridge_frame_count"),
        "browser_target_component_plan_parity": "exact_same_layers_offsets_durations_and_pbm_hashes",
        "wba_external_nor_host": host.get("status"),
        "runtime_resource_activated": target.get("runtime_resource_activated"),
        "special_event_fallback": target.get("special_event_fallback"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    try:
        result = verify()
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if result["status"] != "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V22 owner-accepted browser/PBM component plan replays from external NOR on both WBA targets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
