#!/usr/bin/env python3
"""Build one complete UI manifest plus only its newly changed frame payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path


MANIFEST_HEADER_BYTES = 32
MANIFEST_ENTRY_BYTES = 24
FORMAT_VERSION = 1
FLAG_OVERRIDE_PACKBITS = 0x0002
FLAG_XOR_PATCH = 0x0004
FRAME_BYTES = 200 * 25


def fnv1a32(value: str) -> int:
    result = 0x811C9DC5
    for byte in value.encode("ascii"):
        result = ((result ^ byte) * 0x01000193) & 0xFFFFFFFF
    return result


def read_pbm_display_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if not data.startswith(b"P4"):
        raise ValueError(f"{path}: expected binary PBM")
    tokens: list[bytes] = []
    index = 2
    while len(tokens) < 2:
        while index < len(data) and data[index:index + 1] in b" \t\r\n":
            index += 1
        if index < len(data) and data[index:index + 1] == b"#":
            index = data.index(b"\n", index) + 1
            continue
        end = index
        while end < len(data) and data[end:end + 1] not in b" \t\r\n":
            end += 1
        tokens.append(data[index:end])
        index = end
    while index < len(data) and data[index:index + 1] in b" \t\r\n":
        index += 1
    width, height = (int(token) for token in tokens)
    if (width, height) != (200, 200):
        raise ValueError(f"{path}: expected 200x200, got {width}x{height}")
    raster = data[index:index + FRAME_BYTES]
    if len(raster) != FRAME_BYTES:
        raise ValueError(f"{path}: expected {FRAME_BYTES} raster bytes")
    # PBM uses one for black. CEMP and SSD1681-neutral resources use one for white.
    return bytes(byte ^ 0xFF for byte in raster)


def encode_packbits(data: bytes) -> bytes:
    output = bytearray()
    index = 0
    while index < len(data):
        run_length = 1
        while (index + run_length < len(data) and run_length < 128 and
               data[index + run_length] == data[index]):
            run_length += 1
        if run_length >= 3:
            output.extend((257 - run_length, data[index]))
            index += run_length
            continue
        literal_start = index
        index += run_length
        while index < len(data) and index - literal_start < 128:
            run_length = 1
            while (index + run_length < len(data) and run_length < 128 and
                   data[index + run_length] == data[index]):
                run_length += 1
            if run_length >= 3:
                break
            index += min(run_length, 128 - (index - literal_start))
        output.append(index - literal_start - 1)
        output.extend(data[literal_start:index])
    return bytes(output)


def encode_xor_patch(base: bytes, target: bytes) -> bytes:
    if len(base) != FRAME_BYTES or len(target) != FRAME_BYTES:
        raise ValueError("XOR patch frames must be exactly 5000 bytes")
    changed = [index for index, pair in enumerate(zip(base, target))
               if pair[0] != pair[1]]
    output = bytearray()
    cursor = 0
    while cursor < len(changed):
        start = changed[cursor]
        end = start + 1
        cursor += 1
        while cursor < len(changed):
            next_index = changed[cursor]
            if next_index - end > 3 or next_index - start >= 255:
                break
            end = next_index + 1
            cursor += 1
        while end - start > 255:
            chunk_end = start + 255
            xor = bytes(base[index] ^ target[index]
                        for index in range(start, chunk_end))
            output.extend(struct.pack("<HB", start, len(xor)))
            output.extend(xor)
            start = chunk_end
        xor = bytes(base[index] ^ target[index]
                    for index in range(start, end))
        output.extend(struct.pack("<HB", start, len(xor)))
        output.extend(xor)
    return bytes(output)


def patch_base_state_ids(state: dict,
                         base_states: dict[str, dict]) -> list[str]:
    state_id = state["id"]
    candidates: list[str] = []
    candidate = re.sub(r"_v\d+$", "", state_id)
    if candidate in base_states:
        candidates.append(candidate)
    if "_result_" in candidate:
        processing = candidate.replace("_result_", "_processing_", 1)
        if processing in base_states:
            candidates.append(processing)
    if state.get("kind") in ("life", "pointer_follow"):
        prefix = f"expression_{state.get('family', '')}_"
        candidates.extend(
            base_id for base_id, base_state in base_states.items()
            if base_state.get("kind") == "expression" and
            base_id.startswith(prefix)
        )
    if state.get("kind") == "recording_timeline":
        # The fixed-page recording timeline is a browser-composed face plus
        # the recording accessory. Diff it from the existing recording/base
        # face states instead of storing another full 200x200 bitmap.
        candidates.extend(
            base_id for base_id in (
                "recording_0",
                "expression_calm_v0_0_hold",
            )
            if base_id in base_states
        )
    return list(dict.fromkeys(candidates))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_source(path: Path) -> tuple[dict, Path]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("status") != "PASS":
        raise ValueError(f"{path}: source pack is not passing")
    invariants = source.get("invariants", {})
    if (not invariants.get("all_states_are_5000_bytes") or
            not invariants.get("all_inputs_binary")):
        raise ValueError(f"{path}: source pack is not strict 200x200 1bpp")
    return source, path.resolve().parent


def load_active(path: Path | None) -> dict:
    if path is None:
        return {"generation": 0, "entries_by_id": {}}
    active = json.loads(path.read_text(encoding="utf-8"))
    if active.get("schema") != "companion.ui_asset_generation.v1":
        raise ValueError("active generation sidecar has an unsupported schema")
    return active


def state_duration_ms(state: dict) -> int:
    dwell_commits = int(state.get("dwell_commits", 1))
    duration_ms = dwell_commits * 480
    if dwell_commits <= 0 or duration_ms > 0xFFFF:
        raise ValueError(
            f"{state.get('id', '<unknown>')}: invalid dwell_commits "
            f"{dwell_commits}"
        )
    return duration_ms


def resource_identity(rows: list[tuple[str, str, int]]) -> bytes:
    digest = hashlib.sha256()
    digest.update(b"companion-ui-assets-v2\0")
    digest.update(b"200x200\0row-major-msb-first\0one-is-white\0")
    for state_id, display_sha, duration_ms in sorted(rows):
        digest.update(state_id.encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(display_sha))
        digest.update(struct.pack("<H", duration_ms))
    return digest.digest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--base-source-pack-manifest", required=True, type=Path)
    parser.add_argument("--active-generation", type=Path)
    parser.add_argument("--planned-blob-offset", required=True,
                        type=lambda value: int(value, 0))
    parser.add_argument("--output-blob", required=True, type=Path)
    parser.add_argument("--output-generation", required=True, type=Path)
    args = parser.parse_args()

    source, source_root = load_source(args.source_pack_manifest)
    base, base_root = load_source(args.base_source_pack_manifest)
    active = load_active(args.active_generation)
    active_entries = active.get("entries_by_id", {})
    base_states = {state["id"]: state for state in base["states"]}

    base_frames: dict[str, int] = {}
    base_raw_by_id: dict[str, bytes] = {}
    for state in base["states"]:
        raw = read_pbm_display_bytes(base_root / state["pbm_file"])
        base_raw_by_id[state["id"]] = raw
        base_frames.setdefault(sha256_hex(raw), int(state["unique_frame_index"]))

    current_rows: list[dict] = []
    identity_rows: list[tuple[str, str, int]] = []
    current_payload_by_sha: dict[str, dict] = {}
    new_payloads: list[tuple[str, bytes]] = []
    state_hashes: set[int] = set()

    for state in source["states"]:
        state_id = state["id"]
        state_hash = fnv1a32(state_id)
        if state_hash in state_hashes:
            raise ValueError(f"FNV-1a state hash collision at {state_id}")
        state_hashes.add(state_hash)
        raw = read_pbm_display_bytes(source_root / state["pbm_file"])
        display_sha = sha256_hex(raw)
        frame_crc = zlib.crc32(raw)
        duration_ms = state_duration_ms(state)
        identity_rows.append((state_id, display_sha, duration_ms))

        active_entry = active_entries.get(state_id)
        if (active_entry is not None and
                active_entry.get("display_sha256") == display_sha):
            row = dict(active_entry)
            row.update(state_id=state_id, state_hash=state_hash,
                       display_sha256=display_sha, frame_crc32=frame_crc)
        elif display_sha in base_frames:
            row = {
                "state_id": state_id,
                "state_hash": state_hash,
                "display_sha256": display_sha,
                "frame_crc32": frame_crc,
                "base_frame_index": base_frames[display_sha],
                "flags": 0,
                "payload_offset": 0,
                "payload_size": 0,
                "payload_crc32": 0,
                "duration_ms": duration_ms,
            }
        elif display_sha in current_payload_by_sha:
            row = dict(current_payload_by_sha[display_sha])
            row.update(state_id=state_id, state_hash=state_hash)
        else:
            encoded = encode_packbits(raw)
            patch_base_index = 0xFFFF
            patch_base_id = None
            flags = FLAG_OVERRIDE_PACKBITS
            for base_state_id in patch_base_state_ids(state, base_states):
                patch = encode_xor_patch(base_raw_by_id[base_state_id], raw)
                if len(patch) < len(encoded):
                    encoded = patch
                    patch_base_index = int(
                        base_states[base_state_id]["unique_frame_index"])
                    patch_base_id = base_state_id
                    flags = FLAG_XOR_PATCH
            row = {
                "state_id": state_id,
                "state_hash": state_hash,
                "display_sha256": display_sha,
                "frame_crc32": frame_crc,
                "base_frame_index": patch_base_index,
                "flags": flags,
                "payload_offset": None,
                "payload_size": len(encoded),
                "payload_crc32": zlib.crc32(encoded),
                "duration_ms": duration_ms,
            }
            if patch_base_id is not None:
                row["patch_base_state_id"] = patch_base_id
            current_payload_by_sha[display_sha] = row
            new_payloads.append((display_sha, encoded))
        row["duration_ms"] = duration_ms
        current_rows.append(row)

    resource_id = resource_identity(identity_rows)
    page_sha = source.get("source", {}).get("page_sha256")
    if active.get("resource_id") == resource_id.hex().upper():
        generation = dict(active)
        generation.update({
            "status": "ALREADY_CURRENT",
            "page_sha256": page_sha,
            "source_pack_manifest_sha256":
                sha256_hex(args.source_pack_manifest.read_bytes()),
            "new_payload_count": 0,
            "new_payload_bytes": 0,
            "blob_bytes": 0,
            "flash_write_bytes": 0,
            "internal_flash_write_bytes": 0,
        })
        args.output_blob.parent.mkdir(parents=True, exist_ok=True)
        args.output_generation.parent.mkdir(parents=True, exist_ok=True)
        args.output_blob.write_bytes(b"")
        args.output_generation.write_text(
            json.dumps(generation, ensure_ascii=True, indent=2) + "\n",
            encoding="ascii",
            newline="\n",
        )
        print(json.dumps({
            "status": "PASS_UI_ASSET_ALREADY_CURRENT",
            "resource_id": generation["resource_id"],
            "states": len(current_rows),
            "new_payloads": 0,
            "blob_bytes": 0,
            "external_flash_write_bytes": 0,
            "internal_flash_write_bytes": 0,
        }, ensure_ascii=True))
        return 0

    current_rows.sort(key=lambda row: row["state_hash"])
    manifest_size = MANIFEST_HEADER_BYTES + len(current_rows) * MANIFEST_ENTRY_BYTES
    payload_cursor = manifest_size
    new_offsets: dict[str, int] = {}
    payload_blob = bytearray()
    for display_sha, encoded in new_payloads:
        new_offsets[display_sha] = args.planned_blob_offset + payload_cursor
        payload_blob.extend(encoded)
        payload_cursor += len(encoded)
    for row in current_rows:
        if row["payload_offset"] is None:
            row["payload_offset"] = new_offsets[row["display_sha256"]]
        elif (row["flags"] & FLAG_OVERRIDE_PACKBITS and
              row["display_sha256"] in new_offsets):
            row["payload_offset"] = new_offsets[row["display_sha256"]]

    manifest = bytearray(manifest_size)
    struct.pack_into("<4sHHHHI", manifest, 0, b"CUIM", FORMAT_VERSION,
                     MANIFEST_HEADER_BYTES, len(current_rows),
                     MANIFEST_ENTRY_BYTES, manifest_size)
    for index, row in enumerate(current_rows):
        struct.pack_into(
            "<IHHIIHHI",
            manifest,
            MANIFEST_HEADER_BYTES + index * MANIFEST_ENTRY_BYTES,
            row["state_hash"],
            row["base_frame_index"],
            row["flags"],
            row["frame_crc32"],
            row["payload_offset"],
            row["payload_size"],
            row["duration_ms"],
            row["payload_crc32"],
        )

    blob = bytes(manifest + payload_blob)
    generation = {
        "schema": "companion.ui_asset_generation.v1",
        "status": "PASS",
        "generation": int(active.get("generation", 0)) + 1,
        "resource_id": resource_id.hex().upper(),
        "page_sha256": page_sha,
        "source_pack_manifest_sha256":
            sha256_hex(args.source_pack_manifest.read_bytes()),
        "base_source_pack_manifest_sha256":
            sha256_hex(args.base_source_pack_manifest.read_bytes()),
        "planned_blob_offset": args.planned_blob_offset,
        "blob_bytes": len(blob),
        "blob_crc32": zlib.crc32(blob),
        "blob_sha256": sha256_hex(blob),
        "manifest_bytes": len(manifest),
        "manifest_crc32": zlib.crc32(manifest),
        "state_count": len(current_rows),
        "new_payload_count": len(new_payloads),
        "new_payload_bytes": len(payload_blob),
        "entries_by_id": {
            row["state_id"]: row for row in current_rows
        },
    }
    args.output_blob.parent.mkdir(parents=True, exist_ok=True)
    args.output_generation.parent.mkdir(parents=True, exist_ok=True)
    args.output_blob.write_bytes(blob)
    args.output_generation.write_text(
        json.dumps(generation, ensure_ascii=True, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(json.dumps({
        "status": "PASS_UI_ASSET_GENERATION_BUILT",
        "resource_id": generation["resource_id"],
        "states": generation["state_count"],
        "new_payloads": generation["new_payload_count"],
        "new_payload_bytes": generation["new_payload_bytes"],
        "manifest_bytes": generation["manifest_bytes"],
        "blob_bytes": generation["blob_bytes"],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
