#!/usr/bin/env python3
"""Generate the WB55 compile-time contract from one browser-authored CEMP."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def c_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def fnv1a32(value: str) -> int:
    result = 0x811C9DC5
    for byte in value.encode("ascii"):
        result = ((result ^ byte) * 0x01000193) & 0xFFFFFFFF
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cemp", required=True, type=Path)
    parser.add_argument("--cemp-manifest", required=True, type=Path)
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--output-header", required=True, type=Path)
    parser.add_argument("--output-receipt", type=Path)
    args = parser.parse_args()

    cemp_path = args.cemp.resolve()
    cemp = cemp_path.read_bytes()
    if len(cemp) < 80 or cemp[:4] != b"CEMP":
        raise ValueError("input is not a complete CEMP v1 pack")

    version, header_bytes = struct.unpack_from("<HH", cemp, 4)
    total_bytes, revision = struct.unpack_from("<II", cemp, 8)
    width, height, stride = struct.unpack_from("<HHH", cemp, 20)
    pixel_format, encoding, clip_count, frame_count = struct.unpack_from(
        "<BBHH", cemp, 26
    )
    (
        clip_offset,
        frame_offset,
        string_offset,
        string_bytes,
        payload_offset,
        payload_bytes,
        payload_crc32,
        index_crc32,
    ) = struct.unpack_from("<IIIIIIII", cemp, 32)
    (pack_name_offset,) = struct.unpack_from("<I", cemp, 64)

    if version != 1 or header_bytes != 80 or total_bytes != len(cemp):
        raise ValueError("CEMP header version or total size is inconsistent")
    if (width, height, stride, pixel_format) != (200, 200, 25, 1):
        raise ValueError("CEMP is not the Companion 200x200 1bpp profile")
    if clip_offset != header_bytes or frame_offset < clip_offset:
        raise ValueError("CEMP catalog offsets are inconsistent")
    if not (
        frame_offset <= string_offset <= payload_offset <= len(cemp)
        and string_offset + string_bytes == payload_offset
        and payload_offset + payload_bytes == len(cemp)
    ):
        raise ValueError("CEMP string or payload range is inconsistent")
    if zlib.crc32(cemp[clip_offset:payload_offset]) != index_crc32:
        raise ValueError("CEMP index CRC mismatch")
    if zlib.crc32(cemp[payload_offset:]) != payload_crc32:
        raise ValueError("CEMP payload CRC mismatch")
    if pack_name_offset >= string_bytes:
        raise ValueError("CEMP pack-name offset is outside the string table")
    name_start = string_offset + pack_name_offset
    name_end = cemp.find(b"\0", name_start, payload_offset)
    if name_end < 0:
        raise ValueError("CEMP pack name is not NUL terminated")
    pack_name = cemp[name_start:name_end].decode("ascii")

    cemp_manifest = json.loads(args.cemp_manifest.read_text(encoding="utf-8"))
    source_manifest = json.loads(
        args.source_pack_manifest.read_text(encoding="utf-8")
    )
    source = cemp_manifest.get("source", {})
    if source_manifest.get("status") != "PASS":
        raise ValueError("browser source pack is not passing")
    if cemp_manifest.get("name") != pack_name:
        raise ValueError("CEMP name differs from its generated manifest")
    if cemp_manifest.get("revision") != revision:
        raise ValueError("CEMP revision differs from its generated manifest")
    if source.get("clip_count") != clip_count:
        raise ValueError("CEMP clip count differs from its generated manifest")
    if source.get("frame_count") != frame_count:
        raise ValueError("CEMP frame count differs from its generated manifest")
    page_sha256 = source_manifest.get("source", {}).get("page_sha256")
    if source.get("browser_page_sha256") != page_sha256:
        raise ValueError("browser page identity differs across generated manifests")
    if not isinstance(page_sha256, str) or len(page_sha256) != 64:
        raise ValueError("browser page SHA-256 is missing")

    cemp_sha256 = sha256(cemp_path)
    source_manifest_sha256 = sha256(args.source_pack_manifest.resolve())
    family_order = [
        "calm",
        "curious",
        "delighted",
        "warm",
        "playful",
        "sleepy",
        "bashful",
        "thoughtful",
        "focused",
        "alert",
    ]
    life_episode_counts = source_manifest.get("invariants", {}).get(
        "life_episode_counts", {}
    )
    if not isinstance(life_episode_counts, dict):
        raise ValueError("browser life episode contract is missing")
    exported_life_episodes: dict[str, set[int]] = {}
    for state in source_manifest.get("states", []):
        if state.get("kind") != "life":
            continue
        family = state.get("family")
        episode = state.get("action_episode")
        if not isinstance(family, str) or not isinstance(episode, int):
            raise ValueError("browser life state metadata is incomplete")
        exported_life_episodes.setdefault(family, set()).add(episode)
    episode_limits = set()
    life_family_mask = 0
    for family, count in life_episode_counts.items():
        if family not in family_order or not isinstance(count, int) or count < 1:
            raise ValueError("browser life episode contract is invalid")
        episode_limits.add(count)
        life_family_mask |= 1 << family_order.index(family)
        if exported_life_episodes.get(family) != set(range(count)):
            raise ValueError(f"browser life episode coverage is incomplete: {family}")
    if set(exported_life_episodes) != set(life_episode_counts):
        raise ValueError("browser life family coverage differs from its contract")
    if len(episode_limits) != 1:
        raise ValueError("browser life families must share one episode limit")
    life_episode_limit = next(iter(episode_limits))
    state_map = source.get("state_to_canonical_frame")
    if not isinstance(state_map, dict) or set(state_map) != {
        state["id"] for state in source_manifest.get("states", [])
    }:
        raise ValueError("canonical browser state map is incomplete")
    hashed_states = sorted(
        (fnv1a32(state_id), int(unique_index), state_id)
        for state_id, unique_index in state_map.items()
    )
    if len({item[0] for item in hashed_states}) != len(hashed_states):
        raise ValueError("browser state hash collision")
    canonical_count = int(source.get("canonical_frame_clip_count", 0))
    if canonical_count < 1:
        raise ValueError("canonical frame clip count is missing")
    contract = {
        "status": "PASS",
        "pack_name": pack_name,
        "revision": revision,
        "clip_count": clip_count,
        "frame_count": frame_count,
        "string_bytes": string_bytes,
        "total_bytes": total_bytes,
        "encoding": encoding,
        "life_family_mask": life_family_mask,
        "life_episode_limit": life_episode_limit,
        "canonical_frame_clip_count": canonical_count,
        "state_map_count": len(hashed_states),
        "browser_page_sha256": page_sha256.upper(),
        "source_pack_manifest_sha256": source_manifest_sha256,
        "cemp_sha256": cemp_sha256,
    }
    function_clip_names = ("charging", "recording", "speaker")
    manifest_clips = {
        clip.get("name"): clip for clip in cemp_manifest.get("clips", [])
    }
    function_clip_rows = []
    for clip_name in function_clip_names:
        clip = manifest_clips.get(clip_name)
        if clip is None or len(clip.get("frames", [])) != 3:
            raise ValueError(
                f"browser function clip timing is incomplete: {clip_name}"
            )
        durations = [int(frame["duration_ms"]) for frame in clip["frames"]]
        if any(duration < 1 or duration > 0xFFFF for duration in durations):
            raise ValueError(f"browser function clip duration is invalid: {clip_name}")
        function_clip_rows.append(
            "  {"
            f"{c_string(clip_name)}, "
            "{" + ", ".join(f"{duration}u" for duration in durations) + "}"
            "},"
        )
    contract["function_clip_timing_count"] = len(function_clip_rows)
    state_rows = "\n".join(
        f"  {{0x{state_hash:08X}u, {unique_index}u}}, /* {state_id} */"
        for state_hash, unique_index, state_id in hashed_states
    )
    string_table = cemp[string_offset:payload_offset]
    string_rows = "\n".join(
        "  " + ", ".join(f"0x{byte:02X}u" for byte in string_table[offset : offset + 16]) + ","
        for offset in range(0, len(string_table), 16)
    )
    clip_rows_list = []
    for index in range(clip_count):
        entry_offset = clip_offset + index * 16
        name_offset, first_frame, clip_frames, loop_start, loop_end = struct.unpack_from(
            "<IHHHH", cemp, entry_offset
        )
        if name_offset > 0xFFFF:
            raise ValueError("CEMP string offset exceeds generated clip contract")
        clip_rows_list.append(
            "  {.name = (const char *)&companion_browser_cemp_strings["
            f"{name_offset}u], .first_frame = {first_frame}u, "
            f".frame_count = {clip_frames}u, .loop_start = {loop_start}u, "
            f".loop_end = {loop_end}u}},"
        )
    clip_rows_list.append(
        "  {.name = \"browser_state_override\", "
        f".first_frame = {frame_count}u, .frame_count = 1u, "
        ".loop_start = 0u, .loop_end = 1u},"
    )
    clip_rows = "\n".join(clip_rows_list)
    frame_rows_list = []
    for index in range(frame_count):
        entry_offset = frame_offset + index * 20
        (
            data_offset,
            data_size,
            duration_ms,
            dirty_x,
            dirty_y,
            dirty_width,
            dirty_height,
        ) = struct.unpack_from("<IIHHHHH", cemp, entry_offset)
        if data_size > 0xFFFF:
            raise ValueError("CEMP frame data size exceeds runtime contract")
        frame_rows_list.append(
            "  {.data_offset = "
            f"{data_offset}u, .data_size = {data_size}u, "
            f".duration_ms = {duration_ms}u, .dirty_x = {dirty_x}u, "
            f".dirty_y = {dirty_y}u, .dirty_width = {dirty_width}u, "
            f".dirty_height = {dirty_height}u}},"
        )
    frame_rows_list.append(
        "  {.data_offset = 0u, .data_size = 1u, "
        ".duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, "
        ".dirty_width = 0u, .dirty_height = 0u},"
    )
    frame_rows = "\n".join(frame_rows_list)
    header = "\n".join(
        [
            "#ifndef COMPANION_BROWSER_CEMP_CONTRACT_H",
            "#define COMPANION_BROWSER_CEMP_CONTRACT_H",
            "",
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "#include \"emote_player.h\"",
            "",
            "/* Generated from the browser-authored CEMP. Do not edit. */",
            f"#define COMPANION_BROWSER_CEMP_PACK_NAME {c_string(pack_name)}",
            f"#define COMPANION_BROWSER_CEMP_PACK_REVISION {revision}u",
            f"#define COMPANION_BROWSER_CEMP_CLIP_COUNT {clip_count}u",
            f"#define COMPANION_BROWSER_CEMP_FRAME_COUNT {frame_count}u",
            f"#define COMPANION_BROWSER_CEMP_STRING_BYTES {string_bytes}u",
            f"#define COMPANION_BROWSER_CEMP_TOTAL_BYTES {total_bytes}u",
            f"#define COMPANION_BROWSER_CEMP_CANONICAL_FRAME_CLIP_COUNT {canonical_count}u",
            f"#define COMPANION_BROWSER_CEMP_STATE_MAP_COUNT {len(hashed_states)}u",
            "#define COMPANION_BROWSER_CEMP_FUNCTION_CLIP_TIMING_COUNT "
            f"{len(function_clip_rows)}u",
            f"#define COMPANION_BROWSER_LIFE_FAMILY_MASK 0x{life_family_mask:08X}u",
            f"#define COMPANION_BROWSER_LIFE_EPISODE_LIMIT {life_episode_limit}u",
            f"#define COMPANION_BROWSER_PAGE_SHA256 {c_string(page_sha256.upper())}",
            f"#define COMPANION_BROWSER_CEMP_SHA256 {c_string(cemp_sha256)}",
            "",
            "static const uint8_t companion_browser_cemp_strings[",
            "    COMPANION_BROWSER_CEMP_STRING_BYTES] = {",
            string_rows,
            "};",
            "",
            "static const comp_emote_clip_t companion_browser_cemp_clips[",
            "    COMPANION_BROWSER_CEMP_CLIP_COUNT + 1u] = {",
            clip_rows,
            "};",
            "",
            "static const comp_emote_frame_t companion_browser_cemp_frames[",
            "    COMPANION_BROWSER_CEMP_FRAME_COUNT + 1u] = {",
            frame_rows,
            "};",
            "",
            "typedef struct {",
            "  const char *name;",
            "  uint16_t durations_ms[3];",
            "} companion_browser_cemp_function_clip_timing_t;",
            "",
            "static const companion_browser_cemp_function_clip_timing_t",
            "    companion_browser_cemp_function_clip_timings",
            "    [COMPANION_BROWSER_CEMP_FUNCTION_CLIP_TIMING_COUNT] = {",
            *function_clip_rows,
            "};",
            "",
            "typedef struct {",
            "  uint32_t hash;",
            "  uint16_t unique_frame_index;",
            "} companion_browser_cemp_state_map_entry_t;",
            "",
            "static const companion_browser_cemp_state_map_entry_t",
            "    companion_browser_cemp_state_map[COMPANION_BROWSER_CEMP_STATE_MAP_COUNT] = {",
            state_rows,
            "};",
            "",
            "static inline uint32_t companion_browser_cemp_state_hash(const char *value)",
            "{",
            "  uint32_t hash = 0x811C9DC5u;",
            "  if (value == NULL) return 0u;",
            "  while (*value != '\\0') {",
            "    hash = (hash ^ (uint8_t)*value++) * 0x01000193u;",
            "  }",
            "  return hash;",
            "}",
            "",
            "static inline bool companion_browser_cemp_state_unique_index(",
            "    const char *state_id, uint16_t *unique_frame_index)",
            "{",
            "  const uint32_t target = companion_browser_cemp_state_hash(state_id);",
            "  size_t low = 0u;",
            "  size_t high = COMPANION_BROWSER_CEMP_STATE_MAP_COUNT;",
            "  while (low < high) {",
            "    const size_t middle = low + (high - low) / 2u;",
            "    const uint32_t hash = companion_browser_cemp_state_map[middle].hash;",
            "    if (hash < target) low = middle + 1u;",
            "    else high = middle;",
            "  }",
            "  if (low >= COMPANION_BROWSER_CEMP_STATE_MAP_COUNT ||",
            "      companion_browser_cemp_state_map[low].hash != target) return false;",
            "  if (unique_frame_index != NULL) {",
            "    *unique_frame_index = companion_browser_cemp_state_map[low].unique_frame_index;",
            "  }",
            "  return true;",
            "}",
            "",
            "#endif /* COMPANION_BROWSER_CEMP_CONTRACT_H */",
            "",
        ]
    )
    args.output_header.parent.mkdir(parents=True, exist_ok=True)
    args.output_header.write_text(header, encoding="ascii", newline="\n")
    if args.output_receipt is not None:
        args.output_receipt.parent.mkdir(parents=True, exist_ok=True)
        args.output_receipt.write_text(
            json.dumps(contract, ensure_ascii=True, indent=2) + "\n",
            encoding="ascii",
            newline="\n",
        )
    print(json.dumps(contract, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
