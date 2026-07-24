#!/usr/bin/env python3
"""Build and verify the offline R10 solid-ball framebuffer contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-pixel-oracle-20260722.json"
R2_ARTIFACT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r10-ball-pixel-oracle-20260722.json"
HEADER = ROOT / "app/companion_pendant/epaper/r10_ball_diagnostic.h"
WIDTH = 200
HEIGHT = 200
BYTES_PER_ROW = WIDTH // 8
FRAME_BYTES = BYTES_PER_ROW * HEIGHT
BALL_SIZE = 12
BALL_Y = 80
POSITIONS = (32, 40, 48, 56, 64)
QUALIFICATION_POSITIONS = (32, 40, 48, 56, 64, 56, 48, 40, 32, 40, 48, 56, 64, 56, 48, 40)
LOOP_POSITIONS = (32, 40, 48, 56, 64, 56, 48, 40)
LUT_SHA256 = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
TAIL_HEX = "221741A83258"
RESTORE_SHA256 = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"


class OracleFailure(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_c_integer(token: str) -> int:
    return int(re.sub(r"[uUlL]+$", "", token), 0)


def parse_c_array(source: str, name: str) -> list[int]:
    match = re.search(
        rf"\b{name}\s*\[[^=]*\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        source,
        re.DOTALL,
    )
    if match is None:
        raise OracleFailure(f"missing C array {name}")
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", match.group("body"), flags=re.DOTALL)
    return [parse_c_integer(token) for token in re.findall(r"\b(?:0[xX][0-9a-fA-F]+|\d+)[uUlL]*\b", body)]


def parse_c_define(source: str, name: str) -> int:
    match = re.search(rf"^\s*#define\s+{name}\s+([^\s/]+)", source, re.MULTILINE)
    if match is None:
        raise OracleFailure(f"missing C define {name}")
    return parse_c_integer(match.group(1))


def solid_disk_pixels(x: int, y: int) -> set[tuple[int, int]]:
    if x % 8 != 0 or x < 0 or y < 0 or x + BALL_SIZE > WIDTH or y + BALL_SIZE > HEIGHT:
        raise OracleFailure("ball position is out of bounds or not byte-aligned")
    pixels: set[tuple[int, int]] = set()
    for row in range(BALL_SIZE):
        for column in range(BALL_SIZE):
            dx = 2 * column - 11
            dy = 2 * row - 11
            if dx * dx + dy * dy <= 12 * 12:
                pixels.add((x + column, y + row))
    return pixels


def pixels_from_c_masks(x: int, y: int, masks: tuple[tuple[int, int], ...]) -> set[tuple[int, int]]:
    pixels: set[tuple[int, int]] = set()
    for row, row_masks in enumerate(masks):
        for byte_offset, value in enumerate(row_masks):
            for bit in range(8):
                column = byte_offset * 8 + bit
                if value & (0x80 >> bit):
                    if column >= BALL_SIZE:
                        raise OracleFailure(f"C row mask sets a pixel outside the 12x12 box at row={row}")
                    pixels.add((x + column, y + row))
    return pixels


def parse_and_assert_header() -> dict[str, object]:
    source_bytes = HEADER.read_bytes()
    source = source_bytes.decode("ascii")
    expected_defines = {
        "COMP_R10_BALL_DIAGNOSTIC_ACTIVATIONS": len(QUALIFICATION_POSITIONS),
        "COMP_R10_BALL_DIAGNOSTIC_LOOP_POSITIONS": len(LOOP_POSITIONS),
        "COMP_R10_BALL_DIAGNOSTIC_X_START": min(POSITIONS),
        "COMP_R10_BALL_DIAGNOSTIC_X_END": max(POSITIONS),
        "COMP_R10_BALL_DIAGNOSTIC_X_STEP": 8,
        "COMP_R10_BALL_DIAGNOSTIC_Y": BALL_Y,
        "COMP_R10_BALL_DIAGNOSTIC_SIZE": BALL_SIZE,
        "COMP_R10_BALL_DIAGNOSTIC_TRAVEL": 32,
    }
    for name, expected in expected_defines.items():
        actual = parse_c_define(source, name)
        if actual != expected:
            raise OracleFailure(f"C define {name}={actual}, expected {expected}")

    header_positions = tuple(parse_c_array(source, "comp_r10_ball_diagnostic_positions"))
    if header_positions != QUALIFICATION_POSITIONS:
        raise OracleFailure("C qualification positions do not match the independent path")

    flat_masks = parse_c_array(source, "comp_r10_ball_diagnostic_row_masks")
    if len(flat_masks) != BALL_SIZE * 2:
        raise OracleFailure(f"C row mask length is {len(flat_masks)}, expected {BALL_SIZE * 2}")
    masks = tuple((flat_masks[index], flat_masks[index + 1]) for index in range(0, len(flat_masks), 2))
    expected_row_widths = [4, 8, 10, 10, 12, 12, 12, 12, 10, 10, 8, 4]
    actual_row_widths = []
    for row in range(BALL_SIZE):
        actual_row_widths.append(sum(1 for _, pixel_y in pixels_from_c_masks(0, 0, masks) if pixel_y == row))
    if actual_row_widths != expected_row_widths:
        raise OracleFailure(f"C row widths {actual_row_widths}, expected {expected_row_widths}")
    for x in POSITIONS:
        if pixels_from_c_masks(x, BALL_Y, masks) != solid_disk_pixels(x, BALL_Y):
            raise OracleFailure(f"C row masks differ from the independent disk equation at x={x}")
    return {
        "path": HEADER.relative_to(ROOT).as_posix(),
        "sha256": sha256(source_bytes),
        "positions": list(header_positions),
        "row_masks_hex": [[f"{first:02X}", f"{second:02X}"] for first, second in masks],
        "row_widths": actual_row_widths,
        "black_pixel_count": len(pixels_from_c_masks(0, 0, masks)),
        "matches_independent_equation_at_all_positions": True,
    }


def frame_for_position(x: int | None) -> bytes:
    frame = bytearray([0xFF] * FRAME_BYTES)
    if x is None:
        return bytes(frame)
    for pixel_x, pixel_y in solid_disk_pixels(x, BALL_Y):
        index = pixel_y * BYTES_PER_ROW + pixel_x // 8
        frame[index] &= ~(0x80 >> (pixel_x & 7))
    return bytes(frame)


def black_pixels(frame: bytes) -> set[tuple[int, int]]:
    pixels: set[tuple[int, int]] = set()
    for y in range(HEIGHT):
        row_offset = y * BYTES_PER_ROW
        for byte_index in range(BYTES_PER_ROW):
            value = frame[row_offset + byte_index]
            for bit in range(8):
                if not (value & (0x80 >> bit)):
                    pixels.add((byte_index * 8 + bit, y))
    return pixels


def expected_window(previous: bytes, current: bytes) -> dict[str, int | bool]:
    changed: list[tuple[int, int]] = []
    for y in range(HEIGHT):
        row_offset = y * BYTES_PER_ROW
        for byte_index in range(BYTES_PER_ROW):
            before = previous[row_offset + byte_index]
            after = current[row_offset + byte_index]
            difference = before ^ after
            for bit in range(8):
                if difference & (0x80 >> bit):
                    changed.append((byte_index * 8 + bit, y))
    if not changed:
        return {
            "changed": False,
            "x_start_byte": 0,
            "x_end_byte": 0,
            "y_start": 0,
            "y_end": 0,
            "bytes": 0,
        }
    min_x = min(x for x, _ in changed)
    max_x = max(x for x, _ in changed)
    min_y = min(y for _, y in changed)
    max_y = max(y for _, y in changed)
    x_start_byte = min_x // 8
    x_end_byte = max_x // 8
    return {
        "changed": True,
        "x_start_byte": x_start_byte,
        "x_end_byte": x_end_byte,
        "y_start": min_y,
        "y_end": max_y,
        "bytes": (x_end_byte - x_start_byte + 1) * (max_y - min_y + 1),
    }


def count_classes(previous: bytes, current: bytes, window: dict[str, int | bool]) -> dict[str, int]:
    if not window["changed"]:
        return {"ww": 0, "wb": 0, "bw": 0, "bb": 0}
    counts = {"ww": 0, "wb": 0, "bw": 0, "bb": 0}
    start = int(window["x_start_byte"])
    end = int(window["x_end_byte"])
    for y in range(int(window["y_start"]), int(window["y_end"]) + 1):
        offset = y * BYTES_PER_ROW
        for index in range(offset + start, offset + end + 1):
            for bit in range(8):
                old_white = bool(previous[index] & (0x80 >> bit))
                new_white = bool(current[index] & (0x80 >> bit))
                if old_white and new_white:
                    counts["ww"] += 1
                elif old_white:
                    counts["wb"] += 1
                elif new_white:
                    counts["bw"] += 1
                else:
                    counts["bb"] += 1
    return counts


def payload(previous: bytes, window: dict[str, int | bool]) -> bytes:
    if not window["changed"]:
        return b""
    start = int(window["x_start_byte"])
    end = int(window["x_end_byte"])
    rows = []
    for y in range(int(window["y_start"]), int(window["y_end"]) + 1):
        row_offset = y * BYTES_PER_ROW
        rows.append(previous[row_offset + start : row_offset + end + 1])
    return b"".join(rows)


def assert_disk(frame: bytes, x: int | None) -> None:
    actual = black_pixels(frame)
    expected = solid_disk_pixels(x, BALL_Y) if x is not None else set()
    if actual != expected:
        raise OracleFailure(f"disk pixel set mismatch at x={x}")
    if x is not None:
        xs = [pixel_x for pixel_x, _ in actual]
        ys = [pixel_y for _, pixel_y in actual]
        if (min(xs), max(xs), min(ys), max(ys)) != (x, x + 11, BALL_Y, BALL_Y + 11):
            raise OracleFailure(f"disk bounding box mismatch at x={x}")


def assert_transition(previous: bytes, current: bytes, old_x: int | None, new_x: int) -> dict[str, object]:
    assert_disk(previous, old_x)
    assert_disk(current, new_x)
    window = expected_window(previous, current)
    union = (solid_disk_pixels(old_x, BALL_Y) if old_x is not None else set()) | solid_disk_pixels(new_x, BALL_Y)
    min_x = min(x for x, _ in union)
    max_x = max(x for x, _ in union)
    min_y = min(y for _, y in union)
    max_y = max(y for _, y in union)
    expected = {
        "changed": True,
        "x_start_byte": min_x // 8,
        "x_end_byte": max_x // 8,
        "y_start": min_y,
        "y_end": max_y,
        "bytes": (max_x // 8 - min_x // 8 + 1) * (max_y - min_y + 1),
    }
    assert_window(window, expected, old_x, new_x)
    old_black = solid_disk_pixels(old_x, BALL_Y) if old_x is not None else set()
    new_black = solid_disk_pixels(new_x, BALL_Y)
    changed_black = old_black ^ new_black
    if not changed_black or not changed_black <= union:
        raise OracleFailure(f"changed union is not complete for {old_x}->{new_x}")
    old_payload = payload(previous, window)
    new_payload = payload(current, window)
    return {
        "previous_x": old_x,
        "current_x": new_x,
        "previous_frame_sha256": sha256(previous),
        "current_frame_sha256": sha256(current),
        "previous_payload_sha256": sha256(old_payload),
        "current_payload_sha256": sha256(new_payload),
        "window": window,
        "changed_pixels": len(changed_black),
        "transition_classes": count_classes(previous, current, window),
    }


def assert_window(
    actual: dict[str, int | bool],
    expected: dict[str, int | bool],
    old_x: int | None,
    new_x: int,
) -> None:
    if actual != expected:
        raise OracleFailure(f"union window mismatch for {old_x}->{new_x}: {actual} != {expected}")


def assert_position_path(
    qualification_positions: tuple[int, ...] = QUALIFICATION_POSITIONS,
    positions: tuple[int, ...] = POSITIONS,
) -> None:
    if len(qualification_positions) != 16:
        raise OracleFailure("qualification must contain exactly 16 positions")
    if min(positions) + 32 != max(positions):
        raise OracleFailure("position path does not span exactly 32 pixels")
    if any(position not in positions for position in qualification_positions):
        raise OracleFailure("qualification uses a position outside the admitted set")
    for before, after in zip(qualification_positions, qualification_positions[1:]):
        if abs(after - before) != 8:
            raise OracleFailure(f"position step is not 8 pixels: {before}->{after}")


def negative_fixtures() -> list[dict[str, str]]:
    accepted: list[dict[str, str]] = []
    valid = frame_for_position(32)
    broken = bytearray(valid)
    black = sorted(solid_disk_pixels(32, BALL_Y))
    pixel_x, pixel_y = black[0]
    broken[pixel_y * BYTES_PER_ROW + pixel_x // 8] |= 0x80 >> (pixel_x & 7)
    try:
        assert_disk(bytes(broken), 32)
    except OracleFailure:
        accepted.append({"name": "missing_pixel", "result": "rejected"})
    else:
        raise OracleFailure("negative missing_pixel was accepted")

    square = bytearray([0xFF] * FRAME_BYTES)
    for y in range(BALL_Y, BALL_Y + BALL_SIZE):
        for x in range(32, 32 + BALL_SIZE):
            square[y * BYTES_PER_ROW + x // 8] &= ~(0x80 >> (x & 7))
    try:
        assert_disk(bytes(square), 32)
    except OracleFailure:
        accepted.append({"name": "solid_square", "result": "rejected"})
    else:
        raise OracleFailure("negative solid_square was accepted")

    bad_positions = (32, 48, 56, 64, 56, 48, 40, 32, 40, 48, 56, 64, 56, 48, 40, 32)
    try:
        assert_position_path(bad_positions)
    except OracleFailure:
        accepted.append({"name": "wrong_step", "result": "rejected"})
    else:
        raise OracleFailure("negative wrong_step was accepted")

    previous = frame_for_position(32)
    current = frame_for_position(40)
    window = expected_window(previous, current)
    wrong_window = dict(window)
    wrong_window["x_end_byte"] = int(wrong_window["x_end_byte"]) - 1
    try:
        assert_window(wrong_window, window, 32, 40)
    except OracleFailure:
        accepted.append({"name": "clipped_union_window", "result": "rejected"})
    else:
        raise OracleFailure("negative clipped_union_window was accepted")
    return accepted


def build_artifact() -> dict[str, object]:
    assert_position_path()
    c_header = parse_and_assert_header()
    states: tuple[int | None, ...] = (None,) + QUALIFICATION_POSITIONS
    transitions = []
    for old_x, new_x in zip(states, states[1:]):
        transitions.append(assert_transition(frame_for_position(old_x), frame_for_position(new_x), old_x, new_x))
    r2 = json.loads(R2_ARTIFACT.read_text(encoding="utf-8"))
    r2_transitions = r2["qualification"]["transitions"]
    r3_hashes = [(item["previous_frame_sha256"], item["current_frame_sha256"], item["previous_payload_sha256"], item["current_payload_sha256"]) for item in transitions]
    r2_hashes = [(item["previous_frame_sha256"], item["current_frame_sha256"], item["previous_payload_sha256"], item["current_payload_sha256"]) for item in r2_transitions]
    if r3_hashes != r2_hashes:
        raise OracleFailure("R3 frame/payload hashes differ from the accepted R2 oracle")
    return {
        "schema_id": "companion.wb55.ssd1681.r10_r3_ball_pixel_oracle.v2",
        "status": "PASS_R10_BALL_PIXEL_ORACLE",
        "geometry": {
            "frame_width": WIDTH,
            "frame_height": HEIGHT,
            "ball_shape": "solid_disk",
            "ball_bounding_box": [BALL_SIZE, BALL_SIZE],
            "ball_radius_doubled": 12,
            "y": BALL_Y,
            "x_positions": list(POSITIONS),
            "stride_px": 8,
            "travel_span_px": 32,
            "path": "ping_pong",
            "independent_equation": "(2*x-11)^2 + (2*y-11)^2 <= 144",
            "black_pixel_count": 112,
        },
        "c_header": c_header,
        "qualification": {
            "activation_count": len(transitions),
            "positions": list(QUALIFICATION_POSITIONS),
            "initial_previous": "white",
            "full_frame_bytes": FRAME_BYTES,
            "window_rule": "exact black-pixel union envelope with byte-aligned X",
            "transitions": transitions,
        },
        "loop": {
            "positions": list(LOOP_POSITIONS),
            "bounded_telemetry_required": True,
            "automatic_until_owner_verdict": True,
        },
        "protected": {
            "lut_sha256": LUT_SHA256,
            "tail_hex": TAIL_HEX,
            "old_command": "0x26",
            "new_command": "0x24",
            "post_sync_command": "0x24",
            "control": "0xCF",
            "refresh": "0x20",
            "restore_application_sha256": RESTORE_SHA256,
        },
        "r2_payload_hash_identity": {"artifact": R2_ARTIFACT.relative_to(ROOT).as_posix(), "artifact_sha256": sha256(R2_ARTIFACT.read_bytes()), "frame_and_payload_hashes_match": True},
        "negative_fixtures": negative_fixtures(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        artifact = build_artifact()
    except OracleFailure as error:
        print(f"FAIL: R10 ball pixel oracle: {error}")
        return 1
    rendered = json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_bytes(rendered.encode("utf-8"))
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered.encode("utf-8"):
        print(f"FAIL: stale R10 ball pixel oracle artifact: {args.artifact.relative_to(ROOT).as_posix()}")
        return 1
    print(f"PASS: R10 ball pixel oracle transitions={len(artifact['qualification']['transitions'])} negative_fixtures={len(artifact['negative_fixtures'])}")
    artifact_sha256 = sha256(args.artifact.read_bytes())
    print(f"artifact={args.artifact.relative_to(ROOT).as_posix()} sha256={artifact_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
