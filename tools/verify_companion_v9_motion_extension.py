#!/usr/bin/env python3
"""Verify a candidate-only v9 daily-motion pack against its source manifest."""

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
from render_companion_v9_motion_extension import sha256  # noqa: E402

FRAME_ENTRY_BYTES = 20


def verify(report_path: pathlib.Path) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if report.get("status") != "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW":
        errors.append("render report is not a pending machine-pass candidate")
    if report.get("runtime_resource_activated") is not False:
        errors.append("motion candidate claims runtime activation")
    frames = report.get("frames")
    if not isinstance(frames, list) or [frame.get("phase") for frame in frames] != ["entry", "sustain", "settle"]:
        errors.append("render report must preserve entry, sustain, settle order")
    feature_diffs = report.get("feature_diffs")
    if not isinstance(feature_diffs, list) or not any(
        diff.get("role") == "eye_highlight" and diff.get("pass") is True for diff in feature_diffs
    ) or not any(diff.get("role") == "secondary" and diff.get("pass") is True for diff in feature_diffs):
        errors.append("motion report must prove eye/highlight and secondary feature changes")
    if report.get("whole_frame_translation_only") is not False:
        errors.append("motion candidate must not rely on global translation")

    manifest_path = ROOT / str(report.get("manifest", ""))
    pack_path = ROOT / str(report.get("pack", ""))
    metadata_path = ROOT / str(report.get("metadata", ""))
    source_to_pbm_path = ROOT / str(report.get("source_to_pbm_preview", ""))
    for path in (manifest_path, pack_path, metadata_path, source_to_pbm_path):
        if not path.is_file():
            errors.append(f"missing candidate artifact: {path}")
    if errors:
        return {"status": "FAIL", "errors": errors}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_pack, expected_metadata = build_pack(manifest_path)
    actual_pack = pack_path.read_bytes()
    manifest_frames = [frame for clip in manifest.get("clips", []) for frame in clip.get("frames", [])]
    if manifest.get("provenance", {}).get("runtime_resource_activated") is not False:
        errors.append("manifest must remain runtime inactive")
    if len(manifest_frames) != 3:
        errors.append("motion manifest must contain exactly three daily frames")
    if actual_pack != expected_pack:
        errors.append("CEMP does not equal its deterministic manifest build")
    if metadata != expected_metadata:
        errors.append("CEMP metadata does not equal deterministic pack metadata")
    if report.get("pack_sha256") != sha256(pack_path):
        errors.append("reported CEMP hash drifted")
    if actual_pack[:4] != b"CEMP":
        errors.append("candidate pack has no CEMP header")
    if not errors:
        frame_count = struct.unpack_from("<H", actual_pack, 30)[0]
        frame_offset = struct.unpack_from("<I", actual_pack, 36)[0]
        payload_offset = struct.unpack_from("<I", actual_pack, 48)[0]
        payload_size = struct.unpack_from("<I", actual_pack, 52)[0]
        if frame_count != len(manifest_frames):
            errors.append("CEMP frame count differs from manifest")
        if payload_offset + payload_size != len(actual_pack):
            errors.append("CEMP payload does not end at pack boundary")
        for index, frame in enumerate(manifest_frames):
            expected_pixels = parse_p4((manifest_path.parent / frame["source"]).resolve(), 200, 200)
            data_offset, data_size = struct.unpack_from(
                "<II", actual_pack, frame_offset + index * FRAME_ENTRY_BYTES
            )
            if data_offset + data_size > payload_size:
                errors.append(f"CEMP frame {index} exceeds its payload")
                continue
            decoded = decode_packbits(
                actual_pack[payload_offset + data_offset:payload_offset + data_offset + data_size],
                len(expected_pixels),
            )
            if decoded != expected_pixels:
                errors.append(f"CEMP frame {index} does not decode to its PBM")
    return {
        "schema": "companion.v9_motion_extension_cemp_verification.v1",
        "status": "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED" if not errors else "FAIL",
        "render_report": report_path.resolve().relative_to(ROOT).as_posix(),
        "pack": pack_path.resolve().relative_to(ROOT).as_posix(),
        "frame_count": len(manifest_frames),
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
    print("PASS: candidate CEMP decodes to each three-stage v9 motion PBM without activation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
