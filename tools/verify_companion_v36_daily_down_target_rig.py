#!/usr/bin/env python3
"""Verify V36 Daily-down CRIG/profile provenance and browser-target frame parity."""

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

import generate_companion_v36_daily_down_target_rig as rig  # noqa: E402


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def verify() -> dict[str, Any]:
    errors: list[str] = []
    expected = rig.build_artifacts()
    for label, (content, path) in expected.items():
        if not path.is_file() or path.read_bytes() != content:
            errors.append(f"generated V36 target {label} drifted")
    layout = rig.OUTPUT / "v36-daily-down-target-rig-layout.json"
    pack_path = rig.OUTPUT / rig.PACK_FILENAME
    target = load_json(layout)
    preview_gate = load_json(rig.PREVIEW_GATE)
    data = load_json(ROOT / str(preview_gate["data"]))
    pack = pack_path.read_bytes() if pack_path.is_file() else b""
    if len(pack) < rig.HEADER_BYTES or pack[:4] != b"CRIG":
        errors.append("V36 CRIG header is missing or invalid")
    else:
        version, header_bytes = struct.unpack_from("<HH", pack, 4)
        total_size, revision = struct.unpack_from("<II", pack, 8)
        width, height, stride = struct.unpack_from("<HHH", pack, 16)
        component_count = struct.unpack_from("<H", pack, 24)[0]
        index_offset, data_offset, payload_crc, index_crc = struct.unpack_from("<IIII", pack, 28)
        components = target.get("components")
        if version != 1 or header_bytes != rig.HEADER_BYTES or total_size != len(pack) or revision != rig.V36_REVISION or \
                (width, height, stride, pack[22], pack[23]) != (200, 200, 25, 1, 4) or \
                pack[44:76].hex().upper() != rig.LOCKED_V9_SHA256:
            errors.append("V36 CRIG header contract drifted")
        if not isinstance(components, list) or component_count != len(components) or component_count != 17 or \
                index_offset != rig.HEADER_BYTES or data_offset != rig.HEADER_BYTES + component_count * rig.INDEX_ENTRY_BYTES:
            errors.append("V36 CRIG component index layout drifted")
        elif zlib.crc32(pack[index_offset:data_offset]) & 0xFFFFFFFF != index_crc or \
                zlib.crc32(pack[data_offset:]) & 0xFFFFFFFF != payload_crc:
            errors.append("V36 CRIG index or payload CRC drifted")
        else:
            for number, component in enumerate(components):
                offset = number * rig.INDEX_ENTRY_BYTES
                entry = struct.unpack_from("<HHHHIII", pack, index_offset + offset)
                identifier, width, height, stride, data_location, size, crc = entry
                if identifier != component.get("component_id") or (width, height, stride, size) != \
                        (component.get("width"), component.get("height"), component.get("stride_bytes"), component.get("data_size")) or \
                        data_location != component.get("data_offset") or data_location < data_offset or \
                        data_location + size > len(pack) or zlib.crc32(pack[data_location:data_location + size]) & 0xFFFFFFFF != crc:
                    errors.append(f"V36 CRIG component entry {number} drifted")
                    break
    frames = target.get("frames")
    replay = data.get("frame_replay")
    if not isinstance(frames, list) or not isinstance(replay, list) or len(frames) != 6 or len(replay) != 6:
        errors.append("V36 browser/target frame cardinality drifted")
    elif tuple(frame.get("phase") for frame in frames) != rig.EXPECTED_PHASES:
        errors.append("V36 target phase order drifted")
    else:
        for frame, browser in zip(frames, replay):
            browser_layers = browser.get("layers")
            target_layers = frame.get("layers")
            expected_layers = [{"component": layer.get("asset"), "offset": [
                layer["position"][0] - next(component["base_position"][0] for component in target["components"] if component["name"] == layer["asset"]),
                layer["position"][1] - next(component["base_position"][1] for component in target["components"] if component["name"] == layer["asset"]),
            ]} for layer in browser_layers]
            actual_layers = [{"component": layer.get("component"), "offset": layer.get("offset")} for layer in target_layers]
            if frame.get("phase") != browser.get("phase") or frame.get("duration_ms") != browser.get("duration_ms") or \
                    frame.get("target_pbm") != browser.get("target_pbm") or frame.get("target_pbm_sha256") != browser.get("target_pbm_sha256") or \
                    actual_layers != expected_layers:
                errors.append(f"V36 browser/target component plan drifted at {frame.get('phase')}")
                break
    inactive = target.get("runtime_resource_activated") is False and target.get("active_candidate_binding") == "forbidden" and \
        target.get("whole_source_pose_playback") == "forbidden" and target.get("full_face_replacement") == "forbidden" and \
        target.get("special_event_fallback") == {"menu": "fail_closed", "recording": "fail_closed", "upgrade": "fail_closed",
            "sleep": "fail_closed", "charging": "fail_closed", "error": "fail_closed"}
    if not inactive:
        errors.append("V36 target candidate activation or fail-closed policy drifted")
    return {
        "schema": "companion.v36_daily_down_target_rig_gate.v1",
        "status": "PASS_V36_DAILY_DOWN_TARGET_RIG_GENERATION_GATE" if not errors else "FAIL_V36_DAILY_DOWN_TARGET_RIG_GENERATION_GATE",
        "locked_v9_source_sha256": rig.LOCKED_V9_SHA256,
        "pack": str(pack_path.relative_to(ROOT)).replace("\\", "/"), "pack_sha256": sha256(pack_path) if pack_path.is_file() else None,
        "component_count": target.get("component_count"), "frame_count": target.get("frame_count"),
        "browser_target_component_plan_parity": "exact_same_layers_offsets_durations_and_pbm_hashes",
        "runtime_resource_activated": target.get("runtime_resource_activated"), "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, default=9, help="Verify one separately versioned V36 Daily-down candidate.")
    parser.add_argument("--write", type=pathlib.Path)
    args = parser.parse_args()
    try:
        rig.configure_attempt(args.attempt)
        result = verify()
    except (OSError, ValueError, json.JSONDecodeError, struct.error, StopIteration) as exc:
        print(f"FAIL: {exc}")
        return 1
    suffix = "" if args.attempt == 9 else f"-attempt-{args.attempt:02d}"
    write_path = args.write or (ROOT / "docs/validation" / f"companion-v36-daily-down-target-rig-gate{suffix}-20260720.json")
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"].startswith("FAIL"):
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V36 Daily-down CRIG/profile exactly preserves the browser component/PBM plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
