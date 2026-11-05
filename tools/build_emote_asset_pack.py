#!/usr/bin/env python3
"""Build a deterministic Companion expression pack from a JSON manifest."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import zlib


MAGIC = b"CEMP"
FORMAT_VERSION = 1
HEADER_BYTES = 80
CLIP_ENTRY_BYTES = 16
FRAME_ENTRY_BYTES = 20
PIXEL_FORMATS = {"mono_1bpp_white_is_one_msb": 1}
ENCODINGS = {
    "raw_full_frame": 1,
    "packbits": 2,
}


def require_uint(value: object, name: str, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > maximum:
        raise ValueError(f"{name} must be an integer between 0 and {maximum}")
    return value


def parse_p4(path: pathlib.Path, width: int, height: int) -> bytes:
    data = path.read_bytes()
    index = 0
    tokens: list[bytes] = []

    while len(tokens) < 3:
        while index < len(data) and data[index:index + 1] in b" \t\r\n":
            index += 1
        if index < len(data) and data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] not in b"\r\n":
                index += 1
            continue
        start = index
        while index < len(data) and data[index:index + 1] not in b" \t\r\n":
            index += 1
        if start == index:
            raise ValueError(f"{path}: missing PBM header token")
        tokens.append(data[start:index])

    if tokens[0] != b"P4":
        raise ValueError(f"{path}: expected binary P4 PBM")
    if (int(tokens[1]), int(tokens[2])) != (width, height):
        raise ValueError(f"{path}: expected {width}x{height} PBM")
    if data[index:index + 2] == b"\r\n":
        index += 2
    elif data[index:index + 1] in b" \t\r\n":
        index += 1
    else:
        raise ValueError(f"{path}: missing PBM payload separator")

    frame_bytes = ((width + 7) // 8) * height
    payload = data[index:index + frame_bytes]
    if len(payload) != frame_bytes:
        raise ValueError(f"{path}: expected {frame_bytes} raster bytes, found {len(payload)}")
    # PBM stores black as one; the display-neutral Companion format stores white as one.
    return bytes(byte ^ 0xFF for byte in payload)


def encode_packbits(data: bytes) -> bytes:
    """Encode byte runs using the PackBits control-byte convention.

    A non-negative control byte stores that many following literal bytes minus
    one. A negative byte stores one repeated data byte; 0x80 remains unused.
    This is deliberately frame-local so the device can seek and decode any
    external-flash frame without previous-frame state.
    """
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
        literal_length = index - literal_start
        output.append(literal_length - 1)
        output.extend(data[literal_start:index])
    return bytes(output)


def encode_frame(data: bytes, encoding_name: str) -> bytes:
    if encoding_name == "raw_full_frame":
        return data
    if encoding_name == "packbits":
        return encode_packbits(data)
    raise ValueError(f"unsupported frame encoding: {encoding_name!r}")


def decode_packbits(data: bytes, output_size: int) -> bytes:
    output = bytearray()
    index = 0
    while index < len(data):
        control = data[index]
        index += 1
        if control <= 127:
            count = control + 1
            if index + count > len(data):
                raise ValueError("PackBits literal exceeds encoded frame")
            output.extend(data[index:index + count])
            index += count
        elif control != 128:
            count = 257 - control
            if index >= len(data):
                raise ValueError("PackBits run misses its repeated byte")
            output.extend((data[index],) * count)
            index += 1
        else:
            raise ValueError("PackBits 0x80 control is not supported")
        if len(output) > output_size:
            raise ValueError("PackBits frame expands beyond the declared profile")
    if len(output) != output_size:
        raise ValueError("PackBits frame does not expand to the declared profile")
    return bytes(output)


def add_string(table: bytearray, offsets: dict[str, int], value: str) -> int:
    if not value or "\x00" in value:
        raise ValueError("pack and clip names must be non-empty and contain no NUL")
    if value in offsets:
        return offsets[value]
    encoded = value.encode("utf-8") + b"\x00"
    offset = len(table)
    table.extend(encoded)
    offsets[value] = offset
    return offset


def build_pack(manifest_path: pathlib.Path) -> tuple[bytes, dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "companion.emote_asset_pack_manifest.v1":
        raise ValueError("unsupported or missing manifest schema")

    pack_name = manifest.get("name")
    if not isinstance(pack_name, str):
        raise ValueError("name must be a string")
    revision = require_uint(manifest.get("revision"), "revision", 0xFFFFFFFF)
    priority = require_uint(manifest.get("priority", 0), "priority", 0xFFFF)

    profile = manifest.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    width = require_uint(profile.get("width"), "profile.width", 0xFFFF)
    height = require_uint(profile.get("height"), "profile.height", 0xFFFF)
    stride = require_uint(profile.get("stride_bytes"), "profile.stride_bytes", 0xFFFF)
    if width == 0 or height == 0 or stride != (width + 7) // 8:
        raise ValueError("profile must use a non-zero, tightly packed 1bpp stride")
    pixel_format_name = profile.get("pixel_format")
    if pixel_format_name not in PIXEL_FORMATS:
        raise ValueError(f"unsupported pixel format: {pixel_format_name!r}")
    encoding_name = manifest.get("encoding")
    if encoding_name not in ENCODINGS:
        raise ValueError(f"unsupported frame encoding: {encoding_name!r}")

    clips_input = manifest.get("clips")
    if not isinstance(clips_input, list) or not clips_input or len(clips_input) > 0xFFFF:
        raise ValueError("clips must be a non-empty list with at most 65535 entries")

    strings = bytearray()
    string_offsets: dict[str, int] = {}
    pack_name_offset = add_string(strings, string_offsets, pack_name)
    clip_records: list[tuple[int, int, int, int, int]] = []
    frame_records: list[tuple[int, int, int, int, int, int, int]] = []
    payload = bytearray()
    # Frame records retain their own timing and dirty rectangle, but identical
    # decoded bitmaps may safely share one frame-local encoded payload.  This
    # keeps CEMP seekable while avoiding repeated settle frames across clips.
    payload_offsets: dict[bytes, tuple[int, int]] = {}
    encoded_payload_bytes_without_deduplication = 0
    seen_clip_names: set[str] = set()

    for clip_index, clip in enumerate(clips_input):
        if not isinstance(clip, dict):
            raise ValueError(f"clips[{clip_index}] must be an object")
        clip_name = clip.get("name")
        if not isinstance(clip_name, str) or clip_name in seen_clip_names:
            raise ValueError(f"clips[{clip_index}].name must be a unique string")
        seen_clip_names.add(clip_name)
        name_offset = add_string(strings, string_offsets, clip_name)
        frames_input = clip.get("frames")
        if not isinstance(frames_input, list) or not frames_input:
            raise ValueError(f"clip {clip_name!r} must contain at least one frame")
        first_frame = len(frame_records)
        frame_count = len(frames_input)
        if first_frame + frame_count > 0xFFFF:
            raise ValueError("total frame count exceeds 65535")
        loop_start = require_uint(clip.get("loop_start", 0), f"{clip_name}.loop_start", 0xFFFF)
        loop_end = require_uint(
            clip.get("loop_end", frame_count), f"{clip_name}.loop_end", 0xFFFF
        )
        if loop_start > loop_end or loop_end > frame_count:
            raise ValueError(f"clip {clip_name!r} has an invalid loop range")

        for frame_index, frame in enumerate(frames_input):
            if not isinstance(frame, dict):
                raise ValueError(f"{clip_name}.frames[{frame_index}] must be an object")
            source = frame.get("source")
            if not isinstance(source, str):
                raise ValueError(f"{clip_name}.frames[{frame_index}].source must be a path")
            source_path = (manifest_path.parent / source).resolve()
            frame_data = parse_p4(source_path, width, height)
            duration_ms = require_uint(
                frame.get("duration_ms"), f"{clip_name}.frames[{frame_index}].duration_ms", 0xFFFF
            )
            if duration_ms == 0:
                raise ValueError("frame duration must be greater than zero")
            dirty = frame.get("dirty", [0, 0, 0, 0])
            if not isinstance(dirty, list) or len(dirty) != 4:
                raise ValueError("dirty must be [x, y, width, height]")
            dirty_x, dirty_y, dirty_width, dirty_height = [
                require_uint(value, "dirty coordinate", 0xFFFF) for value in dirty
            ]
            if (dirty_width == 0) != (dirty_height == 0):
                raise ValueError("dirty width and height must both be zero or both be non-zero")
            if dirty_width and (
                dirty_x + dirty_width > width or dirty_y + dirty_height > height
            ):
                raise ValueError("dirty rectangle exceeds the screen profile")
            encoded_frame = encode_frame(frame_data, str(encoding_name))
            if encoding_name == "packbits" and decode_packbits(encoded_frame, len(frame_data)) != frame_data:
                raise AssertionError("PackBits frame round trip failed")
            encoded_payload_bytes_without_deduplication += len(encoded_frame)
            shared_payload = payload_offsets.get(frame_data)
            if shared_payload is None:
                data_offset = len(payload)
                encoded_size = len(encoded_frame)
                payload.extend(encoded_frame)
                payload_offsets[frame_data] = (data_offset, encoded_size)
            else:
                data_offset, encoded_size = shared_payload
            frame_records.append(
                (
                    data_offset,
                    encoded_size,
                    duration_ms,
                    dirty_x,
                    dirty_y,
                    dirty_width,
                    dirty_height,
                )
            )
        clip_records.append((name_offset, first_frame, frame_count, loop_start, loop_end))

    clip_table = bytearray()
    for name_offset, first_frame, frame_count, loop_start, loop_end in clip_records:
        clip_table.extend(
            struct.pack("<IHHHHI", name_offset, first_frame, frame_count, loop_start, loop_end, 0)
        )
    frame_table = bytearray()
    for record in frame_records:
        frame_table.extend(struct.pack("<IIHHHHHH", *record, 0))

    clip_offset = HEADER_BYTES
    frame_offset = clip_offset + len(clip_table)
    string_offset = frame_offset + len(frame_table)
    payload_offset = string_offset + len(strings)
    total_size = payload_offset + len(payload)
    if total_size > 0xFFFFFFFF:
        raise ValueError("pack exceeds the 32-bit CEMP size limit")

    index = bytes(clip_table + frame_table + strings)
    payload_bytes = bytes(payload)
    header = bytearray(HEADER_BYTES)
    header[0:4] = MAGIC
    struct.pack_into("<HH", header, 4, FORMAT_VERSION, HEADER_BYTES)
    struct.pack_into("<IIHH", header, 8, total_size, revision, priority, 0)
    struct.pack_into("<HHHBBHH", header, 20, width, height, stride,
                     PIXEL_FORMATS[pixel_format_name], ENCODINGS[encoding_name],
                     len(clip_records), len(frame_records))
    struct.pack_into("<IIIIIIII", header, 32,
                     clip_offset, frame_offset, string_offset, len(strings),
                     payload_offset, len(payload_bytes), zlib.crc32(payload_bytes),
                     zlib.crc32(index))
    struct.pack_into("<I", header, 64, pack_name_offset)
    pack = bytes(header) + index + payload_bytes
    if len(pack) != total_size:
        raise AssertionError("internal CEMP size mismatch")

    metadata = {
        "name": pack_name,
        "revision": revision,
        "priority": priority,
        "width": width,
        "height": height,
        "stride_bytes": stride,
        "clip_count": len(clip_records),
        "frame_count": len(frame_records),
        "unique_payload_frame_count": len(payload_offsets),
        "deduplicated_frame_count": len(frame_records) - len(payload_offsets),
        "payload_bytes_without_deduplication": encoded_payload_bytes_without_deduplication,
        "payload_bytes": len(payload_bytes),
        "total_bytes": len(pack),
        "payload_crc32": zlib.crc32(payload_bytes),
        "pack_crc32": zlib.crc32(pack),
    }
    return pack, metadata


def format_c_header(pack: bytes, metadata: dict[str, object]) -> str:
    lines = [
        "#ifndef COMPANION_SCREEN_ASSET_PROVISION_BLOB_H",
        "#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE {len(pack)}u",
        f"#define COMPANION_SCREEN_ASSET_PROVISION_BLOB_CRC32 0x{metadata['pack_crc32']:08X}u",
        "",
        "static const uint8_t companion_screen_asset_provision_blob[]",
        "    __attribute__((aligned(4))) = {",
    ]
    for start in range(0, len(pack), 16):
        values = ", ".join(f"0x{byte:02X}u" for byte in pack[start:start + 16])
        lines.append(f"    {values},")
    lines.extend(["};", "", "#endif /* COMPANION_SCREEN_ASSET_PROVISION_BLOB_H */", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--c-header", type=pathlib.Path)
    parser.add_argument("--metadata", type=pathlib.Path)
    args = parser.parse_args()

    pack, metadata = build_pack(args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(pack)
    if args.c_header is not None:
        args.c_header.parent.mkdir(parents=True, exist_ok=True)
        args.c_header.write_text(format_c_header(pack, metadata), encoding="ascii", newline="\n")
    if args.metadata is not None:
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    print(
        f"CEMP {metadata['name']} revision={metadata['revision']} "
        f"clips={metadata['clip_count']} frames={metadata['frame_count']} "
        f"bytes={metadata['total_bytes']} crc32=0x{metadata['pack_crc32']:08X}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
