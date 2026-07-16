#!/usr/bin/env python3
"""Verify the v9 machine-only CEMP candidate decodes exactly to its PBMs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from build_emote_asset_pack import build_pack, decode_packbits, parse_p4  # noqa: E402


ART_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200"
MANIFEST = ART_DIR / "v9-expression-cemp-manifest.json"
PACK = ART_DIR / "companion-v9-expression-candidate-200x200.cemp"
METADATA = ART_DIR / "companion-v9-expression-candidate-200x200.cemp.json"
RENDER_REPORT = ART_DIR / "v9-expression-render-report.json"
REPORT = ROOT / "docs/validation/companion-v9-expression-cemp-20260716.json"
FRAME_ENTRY_BYTES = 20


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    render_report = json.loads(RENDER_REPORT.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    expected_pack, expected_metadata = build_pack(MANIFEST)
    actual_pack = PACK.read_bytes()

    frames = [frame for clip in manifest.get("clips", []) for frame in clip.get("frames", [])]
    if len(frames) != 39:
        errors.append(f"manifest must contain exactly 39 frames, found {len(frames)}")
    if render_report.get("frame_count") != 39 or len(render_report.get("frames", [])) != 39:
        errors.append("renderer report does not retain 39/39 frame provenance")
    if manifest.get("provenance", {}).get("runtime_resource_activated") is not False:
        errors.append("candidate manifest incorrectly claims runtime activation")
    if actual_pack != expected_pack:
        errors.append("CEMP is not the deterministic build of the v9 manifest")
    if metadata != expected_metadata:
        errors.append("CEMP metadata does not match the deterministic pack build")
    if actual_pack[:4] != b"CEMP":
        errors.append("candidate does not have a CEMP header")
    frame_count = struct.unpack_from("<H", actual_pack, 30)[0]
    frame_offset = struct.unpack_from("<I", actual_pack, 36)[0]
    payload_offset = struct.unpack_from("<I", actual_pack, 48)[0]
    payload_size = struct.unpack_from("<I", actual_pack, 52)[0]
    if frame_count != len(frames):
        errors.append("CEMP frame count does not match manifest")
    if payload_offset + payload_size != len(actual_pack):
        errors.append("CEMP payload boundary does not end at the pack boundary")

    for index, frame in enumerate(frames):
        source = frame.get("source")
        if not isinstance(source, str):
            errors.append(f"manifest frame {index} has no source")
            continue
        expected_pixels = parse_p4((MANIFEST.parent / source).resolve(), 200, 200)
        data_offset, data_size = struct.unpack_from(
            "<II", actual_pack, frame_offset + index * FRAME_ENTRY_BYTES
        )
        if data_offset + data_size > payload_size:
            errors.append(f"CEMP frame {index} points outside the payload")
            continue
        decoded = decode_packbits(
            actual_pack[payload_offset + data_offset:payload_offset + data_offset + data_size],
            len(expected_pixels),
        )
        if decoded != expected_pixels:
            errors.append(f"CEMP frame {index} does not decode to its PBM source")

    output = {
        "schema": "companion.v9_expression_cemp_verification.v1",
        "status": "PASS_MACHINE_ONLY_CEMP_NOT_ACTIVATED" if not errors else "FAIL",
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "pack": PACK.relative_to(ROOT).as_posix(),
        "pack_sha256": sha256(PACK),
        "render_report": RENDER_REPORT.relative_to(ROOT).as_posix(),
        "render_review": "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-reference-to-pbm.png",
        "frame_review": "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-frame-contact-sheet.png",
        "frame_count": frame_count,
        "clip_count": expected_metadata["clip_count"],
        "unique_payload_frame_count": expected_metadata["unique_payload_frame_count"],
        "deduplicated_frame_count": expected_metadata["deduplicated_frame_count"],
        "runtime_resource_activated": False,
        "external_flash_provisioned": False,
        "firmware_flashed": False,
        "physical_or_owner_visual_pass": False,
        "errors": errors,
    }
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "PASS: deterministic v9 CEMP decodes to all "
        f"{frame_count}/39 declared PBM frames without runtime activation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
