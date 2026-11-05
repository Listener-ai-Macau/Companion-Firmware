#!/usr/bin/env python3
"""Verify source, provenance and non-card dynamics of a v9 Rig candidate."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from build_emote_asset_pack import build_pack, decode_packbits, parse_p4  # noqa: E402
from render_companion_v9_expression_rig import (  # noqa: E402
    REQUIRED_ROLES,
    load_rig,
    render_state,
    sha256,
)

FRAME_ENTRY_BYTES = 20


def required_component_roles(report: dict[str, object]) -> set[str]:
    components = report.get("components")
    if not isinstance(components, list):
        return set()
    return {item.get("role") for item in components if isinstance(item, dict) and isinstance(item.get("role"), str)}


def verify(report_path: pathlib.Path) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if report.get("schema") != "companion.v9_expression_rig_render.v1":
        errors.append("unexpected Rig render schema")
    if report.get("status") != "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW":
        errors.append("Rig is not a pending machine candidate")
    if report.get("runtime_resource_activated") is not False:
        errors.append("Rig report claims runtime activation")
    if report.get("source_sha256") != "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA":
        errors.append("Rig source is not the locked v9 baseline")
    if not REQUIRED_ROLES.issubset(required_component_roles(report)):
        errors.append("Rig is missing required facial component roles")

    layout_path = ROOT / str(report.get("layout", ""))
    if not layout_path.is_file():
        errors.append("missing Rig layout")
        return {"status": "FAIL", "errors": errors}
    try:
        rig = load_rig(layout_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Rig layout is invalid: {exc}")
        return {"status": "FAIL", "errors": errors}

    components = report.get("components")
    if not isinstance(components, list) or len(components) != len(rig.components):
        errors.append("component record count drifted")
    else:
        for record in components:
            if not isinstance(record, dict):
                errors.append("invalid component record")
                continue
            component = rig.components.get(record.get("name"))
            mask_path = ROOT / str(record.get("component_mask", ""))
            if component is None or not mask_path.is_file() or record.get("component_mask_sha256") != sha256(mask_path):
                errors.append(f"component provenance drifted: {record.get('name')}")
                continue
            source = rig.sources[component.source_frame]
            if record.get("source_frame_sha256") != source.sha256:
                errors.append(f"component source hash drifted: {component.name}")

    frames = report.get("frames")
    if not isinstance(frames, list):
        errors.append("Rig has no frame records")
        frames = []
    by_name = {item.get("name"): item for item in frames if isinstance(item, dict)}
    matrix = report.get("state_matrix")
    if not isinstance(matrix, dict) or matrix.get("unique_frame_hashes", 0) < 12:
        errors.append("Rig did not prove twelve unique state-matrix frames")
    hashes = matrix.get("frame_hashes") if isinstance(matrix, dict) else None
    if not isinstance(hashes, dict) or len(set(hashes.values())) < 12:
        errors.append("state-matrix hash map is insufficiently diverse")
    for direction in ("left", "right", "up", "down"):
        directional = [state.name for state in rig.state_matrix if state.attention == direction]
        if not directional or not all(name in hashes for name in directional):
            errors.append(f"missing {direction} attention evidence")
    for frame in frames:
        path = ROOT / str(frame.get("path", ""))
        bounds = frame.get("bounds")
        if not path.is_file() or frame.get("sha256") != sha256(path):
            errors.append(f"frame artifact drifted: {frame.get('name')}")
            continue
        if not isinstance(bounds, list) or len(bounds) != 4 or bounds[0] < 4 or bounds[1] < 4 or bounds[0] + bounds[2] > 196 or bounds[1] + bounds[3] > 196:
            errors.append(f"frame safe inset drifted: {frame.get('name')}")
        layers = frame.get("layers")
        if not isinstance(layers, list) or not layers:
            errors.append(f"frame has no source-derived layers: {frame.get('name')}")
        elif any(layer.get("component") not in rig.components for layer in layers if isinstance(layer, dict)):
            errors.append(f"frame references an unregistered component: {frame.get('name')}")

    for story in rig.stories:
        entries = [by_name.get(f"{story.name}_{phase}") for phase in ("entry", "sustain", "settle")]
        if any(item is None for item in entries):
            errors.append(f"story phase missing: {story.name}")
            continue
        entry, sustain, settle = entries
        entry_pixels = parse_p4(ROOT / str(entry["path"]), 200, 200)
        sustain_pixels = parse_p4(ROOT / str(sustain["path"]), 200, 200)
        settle_pixels = parse_p4(ROOT / str(settle["path"]), 200, 200)
        entry_to_sustain = sum(left != right for left, right in zip(entry_pixels, sustain_pixels))
        entry_to_settle = sum(left != right for left, right in zip(entry_pixels, settle_pixels))
        if entry_to_sustain == 0 or entry_to_settle > entry_to_sustain // 4:
            errors.append(f"story recovery drifted: {story.name}")

    manifest_path = ROOT / str(report.get("manifest", ""))
    pack_path = ROOT / str(report.get("pack", ""))
    metadata_path = ROOT / str(report.get("metadata", ""))
    if not manifest_path.is_file() or not pack_path.is_file() or not metadata_path.is_file():
        errors.append("Rig CEMP artifacts are missing")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_pack, expected_metadata = build_pack(manifest_path)
        actual_pack = pack_path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if manifest.get("provenance", {}).get("runtime_resource_activated") is not False:
            errors.append("Rig CEMP manifest is not runtime inactive")
        if actual_pack != expected_pack or metadata != expected_metadata:
            errors.append("Rig CEMP is not deterministic")
        if report.get("pack_sha256") != sha256(pack_path):
            errors.append("Rig CEMP SHA-256 drifted")
        if actual_pack[:4] != b"CEMP":
            errors.append("Rig pack has invalid magic")
        elif len(actual_pack) >= 56:
            frame_count = struct.unpack_from("<H", actual_pack, 30)[0]
            frame_offset = struct.unpack_from("<I", actual_pack, 36)[0]
            payload_offset = struct.unpack_from("<I", actual_pack, 48)[0]
            payload_size = struct.unpack_from("<I", actual_pack, 52)[0]
            manifest_frames = [frame for clip in manifest.get("clips", []) for frame in clip.get("frames", [])]
            if frame_count != len(manifest_frames) or payload_offset + payload_size != len(actual_pack):
                errors.append("Rig CEMP frame table or payload bounds drifted")
            else:
                for index, frame in enumerate(manifest_frames):
                    expected_pixels = parse_p4((manifest_path.parent / frame["source"]).resolve(), 200, 200)
                    data_offset, data_size = struct.unpack_from("<II", actual_pack, frame_offset + index * FRAME_ENTRY_BYTES)
                    if data_offset + data_size > payload_size:
                        errors.append(f"Rig CEMP frame escapes payload: {index}")
                        continue
                    decoded = decode_packbits(actual_pack[payload_offset + data_offset:payload_offset + data_offset + data_size], len(expected_pixels))
                    if decoded != expected_pixels:
                        errors.append(f"Rig CEMP frame decode drifted: {index}")

    return {
        "schema": "companion.v9_expression_rig_verification.v1",
        "status": "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED" if not errors else "FAIL",
        "render_report": report_path.resolve().relative_to(ROOT).as_posix(),
        "unique_state_frames": matrix.get("unique_frame_hashes") if isinstance(matrix, dict) else 0,
        "runtime_resource_activated": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--write", type=pathlib.Path)
    args = parser.parse_args()
    result = verify(args.report.resolve())
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: v9 Rig preserves source-derived components, deterministic diversity, recovery and CEMP decode without activation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
