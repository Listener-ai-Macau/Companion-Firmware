#!/usr/bin/env python3
"""Prove that a WBA UI generation changes menu rasters and nothing else.

The profile's per-state image SHA-256 values are bound to the resource id that
is stored in the UI partition root.  The verifier also checks the partition,
root, generation blob, and manifest CRCs before comparing the complete state
catalog.  It never writes a device or grants hardware/owner acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BEFORE = ROOT / ".cache/confirmed-discard-20261005/before/.cache/wba-product-resources"
DEFAULT_AFTER = ROOT / ".cache/wba-product-resources"
ROOT_OFFSET = 0x1FE000
ROOT_BYTES = 128
MENU_PREFIX = "menu_ui_"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def validate_side(label: str, profile_path: Path, image_path: Path) -> dict:
    profile = load_object(profile_path)
    image = image_path.read_bytes()
    states = profile.get("states")
    if profile.get("schema") != "companion.wba.product.resources.v1":
        raise ValueError(f"{label}: unexpected profile schema")
    if profile.get("status") != "PASS_SOFTWARE_RESOURCE_BUILD":
        raise ValueError(f"{label}: profile is not a passing software resource build")
    if profile.get("hardwareAcceptance") != "NOT_RUN":
        raise ValueError(f"{label}: profile must not claim hardware acceptance")
    if not isinstance(states, dict) or not states:
        raise ValueError(f"{label}: profile has no complete state catalog")
    if profile.get("stateCount") != len(states):
        raise ValueError(f"{label}: state count differs from catalog")
    if profile.get("uiPartitionBytes") != len(image):
        raise ValueError(f"{label}: UI partition byte count differs")
    image_sha = sha256(image_path)
    if image_sha != str(profile.get("uiPartitionSha256", "")).lower():
        raise ValueError(f"{label}: UI partition SHA-256 differs from profile")
    if len(image) < ROOT_OFFSET + ROOT_BYTES:
        raise ValueError(f"{label}: UI partition is shorter than its generation root")

    root = image[ROOT_OFFSET : ROOT_OFFSET + ROOT_BYTES]
    if zlib.crc32(root[:124]) != struct.unpack_from("<I", root, 124)[0]:
        raise ValueError(f"{label}: UI generation root CRC differs")
    (magic, version, root_size, generation, base_pack_size, blob_offset,
     blob_size, blob_crc, _flags, manifest_size, manifest_crc,
     arena_next) = struct.unpack_from("<4sHHIIIIIIIII", root, 0)
    if magic != b"CUIR" or version != 1 or root_size != ROOT_BYTES:
        raise ValueError(f"{label}: unsupported UI generation root")
    if generation != profile.get("generation"):
        raise ValueError(f"{label}: mounted generation differs from profile")
    if base_pack_size != profile.get("cempBytes"):
        raise ValueError(f"{label}: CEMP byte count differs from profile")
    if blob_size != profile.get("generationBytes"):
        raise ValueError(f"{label}: generation blob byte count differs from profile")
    if (blob_offset > len(image) or blob_size > len(image) - blob_offset or
            manifest_size > blob_size or arena_next < blob_offset + blob_size):
        raise ValueError(f"{label}: generation blob bounds are invalid")
    blob = image[blob_offset : blob_offset + blob_size]
    if zlib.crc32(blob) != blob_crc:
        raise ValueError(f"{label}: generation blob CRC differs")
    if zlib.crc32(blob[:manifest_size]) != manifest_crc:
        raise ValueError(f"{label}: generation manifest CRC differs")

    identity = hashlib.sha256()
    identity.update(f"companion-wba-ui-assets-generation{generation}\0".encode("ascii"))
    for name in sorted(states):
        state = states[name]
        if not isinstance(state, dict):
            raise ValueError(f"{label}: invalid state metadata: {name}")
        frame_sha = state.get("sha256")
        duration = state.get("duration_ms")
        if (not isinstance(frame_sha, str) or len(frame_sha) != 64 or
                any(ch not in "0123456789abcdefABCDEF" for ch in frame_sha)):
            raise ValueError(f"{label}: invalid image SHA-256: {name}")
        if not isinstance(duration, int) or not 0 <= duration <= 0xFFFF:
            raise ValueError(f"{label}: invalid duration: {name}")
        identity.update(name.encode("ascii") + b"\0" + bytes.fromhex(frame_sha) +
                        struct.pack("<H", duration))
    resource_id = identity.hexdigest()
    root_resource_id = root[44:76].hex()
    if resource_id != str(profile.get("resourceId", "")).lower():
        raise ValueError(f"{label}: state image SHA catalog is not bound to profile resource id")
    if resource_id != root_resource_id:
        raise ValueError(f"{label}: profile resource id is not bound to UI partition root")
    return {
        "generation": generation,
        "uiPartitionSha256": image_sha,
        "stateCount": len(states),
        "states": states,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-profile", type=Path,
                        default=DEFAULT_BEFORE / "profile.json")
    parser.add_argument("--before-ui", type=Path,
                        default=DEFAULT_BEFORE / "ui-partition.bin")
    parser.add_argument("--after-profile", type=Path,
                        default=DEFAULT_AFTER / "profile.json")
    parser.add_argument("--after-ui", type=Path,
                        default=DEFAULT_AFTER / "ui-partition.bin")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before-generation", type=int, default=51)
    parser.add_argument("--after-generation", type=int, default=52)
    args = parser.parse_args(argv)

    output = args.output.resolve()
    if output.exists():
        parser.error("preserve existing evidence; output must not exist")
    output.parent.mkdir(parents=True, exist_ok=True)
    before = validate_side("before", args.before_profile.resolve(), args.before_ui.resolve())
    after = validate_side("after", args.after_profile.resolve(), args.after_ui.resolve())
    before_names = set(before["states"])
    after_names = set(after["states"])
    removed = sorted(before_names - after_names)
    added = sorted(after_names - before_names)
    before_non_menu = {name for name in before_names if not name.startswith(MENU_PREFIX)}
    after_non_menu = {name for name in after_names if not name.startswith(MENU_PREFIX)}
    if removed:
        raise ValueError(f"candidate removed existing states: {removed[:8]}")
    if any(not name.startswith(MENU_PREFIX) for name in added):
        raise ValueError(f"candidate added non-menu states: {added[:8]}")
    if before_non_menu != after_non_menu:
        raise ValueError("non-menu state coverage changed")
    changed_existing = {
        name for name in before_names
        if before["states"][name]["sha256"].lower() !=
        after["states"][name]["sha256"].lower()
    }
    changed = sorted(changed_existing | set(added))
    unexpected = [name for name in changed if not name.startswith(MENU_PREFIX)]
    non_menu_count = len(before_non_menu)
    if before["generation"] != args.before_generation or after["generation"] != args.after_generation:
        raise ValueError("menu art delta does not bind the requested frozen and candidate generations")
    if not changed:
        raise ValueError("candidate does not change any authored state image")
    if unexpected:
        raise ValueError(f"non-menu state images changed: {unexpected[:8]}")

    receipt = {
        "schema": "companion.wba.menu-art-delta.v1",
        "result": "PASS_MENU_ART_SCOPE_SOFTWARE_ONLY",
        "before": {
            "generation": before["generation"],
            "uiPartitionSha256": before["uiPartitionSha256"],
            "stateCount": len(before_names),
        },
        "after": {
            "generation": after["generation"],
            "uiPartitionSha256": after["uiPartitionSha256"],
            "stateCount": len(after_names),
        },
        "stateCount": len(after_names),
        "nonMenuStateCount": non_menu_count,
        "changedStates": changed,
        "unexpectedChangedStates": unexpected,
        "addedStates": added,
        "removedStates": removed,
        "hardwareAcceptance": "NOT_RUN",
        "ownerAcceptance": "NOT_RUN",
    }
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "result": receipt["result"],
        "changedStates": len(changed),
        "nonMenuStateCount": non_menu_count,
        "output": str(output),
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
