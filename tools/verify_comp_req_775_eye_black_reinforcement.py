#!/usr/bin/env python3
"""Prove COMP-REQ-775 recording eye cleanup against the shipped calm art.

This gate deliberately checks both sides of the contract: every current-black
pixel in the authored eye windows receives a synthetic white old-plane value,
and the functional path still performs exactly one cached Mode-2 activation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


CALM_FRAME_RANGE = range(176, 191)
EYES_BROWSER = ((42, 74, 93, 137), (125, 158, 93, 137))
EYES_CONTROLLER_BYTES = ((5, 9, 62, 106), (15, 19, 62, 106))


def read_p4(path: Path) -> tuple[int, int, bytes]:
    raw = path.read_bytes()
    cursor = 0
    tokens: list[bytes] = []
    while len(tokens) < 3:
        while cursor < len(raw) and raw[cursor] in b" \t\r\n":
            cursor += 1
        if cursor < len(raw) and raw[cursor] == ord("#"):
            cursor = raw.find(b"\n", cursor)
            if cursor < 0:
                raise ValueError(f"unterminated PBM comment: {path}")
            continue
        end = cursor
        while end < len(raw) and raw[end] not in b" \t\r\n":
            end += 1
        tokens.append(raw[cursor:end])
        cursor = end
    if tokens[0] != b"P4":
        raise ValueError(f"not a binary PBM: {path}")
    width, height = int(tokens[1]), int(tokens[2])
    while cursor < len(raw) and raw[cursor] in b" \t\r\n":
        cursor += 1
    payload = raw[cursor:]
    expected = ((width + 7) // 8) * height
    if len(payload) != expected:
        raise ValueError(f"PBM payload {len(payload)} != {expected}: {path}")
    return width, height, payload


def black(payload: bytes, width: int, x: int, y: int) -> bool:
    stride = (width + 7) // 8
    return bool(payload[y * stride + x // 8] & (0x80 >> (x % 8)))


def component(payload: bytes, width: int, height: int, seed: tuple[int, int]) -> set[tuple[int, int]]:
    seen: set[tuple[int, int]] = set()
    pending = [seed]
    while pending:
        x, y = pending.pop()
        if (x, y) in seen or not (0 <= x < width and 0 <= y < height):
            continue
        if not black(payload, width, x, y):
            continue
        seen.add((x, y))
        pending.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return seen


def largest_component_in_box(payload: bytes, width: int, height: int,
                             box: tuple[int, int, int, int]) -> set[tuple[int, int]]:
    x0, x1, y0, y1 = box
    visited: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x, y) in visited or not black(payload, width, x, y):
                continue
            found = component(payload, width, height, (x, y))
            visited.update(found)
            if len(found) > len(largest):
                largest = found
    return largest


def bounds(points: set[tuple[int, int]]) -> tuple[int, int, int, int] | None:
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def extract_function(source: str, name: str) -> str:
    start = source.find(name)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    pack = args.source_pack.resolve()
    manifest_path = pack / "source-pack-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_index: dict[int, dict] = {}
    for state in manifest["states"]:
        index = int(state["unique_frame_index"])
        if index in CALM_FRAME_RANGE and index not in by_index:
            by_index[index] = state

    frames: dict[int, tuple[int, int, bytes]] = {}
    hashes_ok = True
    dimensions_ok = True
    for index in CALM_FRAME_RANGE:
        state = by_index.get(index)
        if state is None:
            continue
        path = pack / state["pbm_file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        hashes_ok &= digest == state["pbm_sha256"].upper()
        frame = read_p4(path)
        dimensions_ok &= frame[:2] == (200, 200)
        frames[index] = frame

    shell_bounds: dict[str, list[list[int] | None]] = {"left": [], "right": []}
    shell_pixels: dict[str, list[int]] = {"left": [], "right": []}
    invariant_shell_bounds = True
    for index in CALM_FRAME_RANGE:
        width, height, payload = frames[index]
        for eye_name, eye_box in zip(("left", "right"), EYES_BROWSER):
            found = largest_component_in_box(payload, width, height, eye_box)
            found_bounds = bounds(found)
            shell_bounds[eye_name].append(list(found_bounds) if found_bounds else None)
            shell_pixels[eye_name].append(len(found))
            invariant_shell_bounds &= found_bounds == eye_box

    transition_counts: list[dict[str, int]] = []
    transition_coverage_ok = True
    total_white_to_black = 0
    for previous_index, current_index in zip(CALM_FRAME_RANGE, range(177, 191)):
        width, _, previous = frames[previous_index]
        _, _, current = frames[current_index]
        per_eye: dict[str, int] = {}
        for eye_name, eye_box, controller_box in zip(
                ("left", "right"), EYES_BROWSER, EYES_CONTROLLER_BYTES):
            count = 0
            x0, x1, y0, y1 = eye_box
            bx0, bx1, cy0, cy1 = controller_box
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    if not black(previous, width, x, y) and black(current, width, x, y):
                        count += 1
                        controller_y = 199 - y
                        transition_coverage_ok &= bx0 <= x // 8 <= bx1 and cy0 <= controller_y <= cy1
            per_eye[eye_name] = count
            total_white_to_black += count
        transition_counts.append({"from": previous_index, "to": current_index, **per_eye})

    driver_path = repo / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    driver = driver_path.read_text(encoding="utf-8")
    activation = extract_function(driver, "ssd1681_native_cached_mode2_functional_activation")
    checks = {
        "all_15_calm_frames_present": len(frames) == 15,
        "manifest_pbm_hashes_match": hashes_ok,
        "frames_are_200x200": dimensions_ok,
        "eye_shell_bounds_invariant": invariant_shell_bounds,
        "white_to_black_transitions_exist": total_white_to_black > 0,
        "all_eye_transitions_inside_reinforcement_windows": transition_coverage_ok,
        "fixed_two_eye_window_geometry": all(token in driver for token in (
            "recording_eye_bounds[2u]", ".x_start_byte = 5u, .x_end_byte = 9u",
            ".x_start_byte = 15u, .x_end_byte = 19u", ".y_start = 62u, .y_end = 106u")),
        "bounded_region_capacity_30_plus_functional": (
            "SSD1681_PRODUCT_RECORDING_FACE_REGION_MAX 30u" in driver and
            "SSD1681_PRODUCT_STAGED_REGION_MAX 34u" in driver),
        "partitioned_retry_preserves_eye_exclusions": all(token in driver for token in (
            "ssd1681_product_partitioned_delta_bands(",
            "{0u, 4u, 62u, 106u, true}",
            "{10u, 14u, 62u, 106u, true}",
            "{20u, 24u, 62u, 106u, true}")),
        "eye_windows_excluded_from_duplicate_exact_bands": all(token in driver for token in (
            "ssd1681_window_t excluded[4u]", "const size_t excluded_count = 4u",
            "excluded[2] = recording_eye_bounds[0]",
            "excluded[3] = recording_eye_bounds[1]")),
        "synthetic_old_white_for_current_black": bool(re.search(
            r"s_blink_closed_frame\[row \+ x\]\s*\|=\s*\n?\s*\(uint8_t\)~s_frame\[row \+ x\]", driver)),
        "functional_old_plane_uses_reinforcement_scratch": (
            "0x26u, s_blink_closed_frame" in activation),
        "functional_path_one_mode2_activation": (
            activation.count("{0xCFu}") == 1 and activation.count("ssd1681_command(0x20u)") == 1),
        "functional_path_has_no_full_control": not any(token in activation for token in ("0xFFu", "0xC7u", "0xF7u")),
        "runtime_evidence_marker_present": "eye_black=1" in driver,
    }
    status = "MACHINE_READY" if all(checks.values()) else "NO_GO"
    report = {
        "schema": "companion.comp_req_775.eye_black_reinforcement.v1",
        "status": status,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "source_pack": str(pack),
        "source_pack_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper(),
        "driver": str(driver_path),
        "driver_sha256": hashlib.sha256(driver_path.read_bytes()).hexdigest().upper(),
        "calm_unique_frame_indices": list(CALM_FRAME_RANGE),
        "eye_browser_bounds": EYES_BROWSER,
        "eye_controller_byte_windows": EYES_CONTROLLER_BYTES,
        "eye_shell_bounds_by_frame": shell_bounds,
        "eye_shell_pixels_by_frame": shell_pixels,
        "white_to_black_transition_total": total_white_to_black,
        "white_to_black_transitions": transition_counts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
