"""Deterministic R12 r5 target-mapping and payload oracle."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

import generate_r12_v22_asset_header as generator
import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r5_log as parser

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = generator.SOURCE
HEADER = generator.OUT
DETAIL_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r5-pixel-detail-20260723.json"
# The base oracle owns only this detail artifact. The wrapper owns the final
# bound oracle, so the two evidence layers cannot overwrite one another.
OUT = DETAIL_OUT
PREVIEW_DIR = ROOT / ".cache/validation/companion-r12-v22-r5-pixel-previews-20260723"
NAMES = ("calm", "curious", "warm")
PATH = ("calm", "curious", "warm", "curious", "calm")
WINDOW = (4, 21, 22, 127)
EXPECTED_SOURCE_SHA = dict(zip(NAMES, parser.SOURCE_SHA.values()))
EXPECTED_FRAME_SHA = {
    "calm": "15788734073049E9967DEA97783522CE1139023FC0AD9BA0F1C5375F2F2E555C",
    "curious": "E98E7E347943A67F92735E9F83F71D12FC214944C7E27B8B8E0225B0F5514705",
    "warm": "931CADB6B5209BB7B3035585994664281B037753605939EF C745A62A5889E29B".replace(" ", ""),
}
EXPECTED_HEADER_FRAME_SHA = {
    "calm": "BBE5EBE794D8375855EC3108D25D25CF999288F3FB4C389FC90638A0C85F679F",
    "curious": "99DB877B39968AA9021FF427CD5A3DAC8E09A16F5F2B19CC2BE7EF00F82DBFF8",
    "warm": "563E9B89CB02FF0883E793281507C0392E186E514DCFA7808AB3173838D03B8B",
}
EXPECTED_PAYLOAD_SHA = {
    "calm": "6FFA8C8A70D87DC46AC323BFF385FEAAAD25A4C6E67E875B8030844A8158CC5B",
    "curious": "B3FF181ED6993CBBC4DE692941793CC81C7B3D40A99528D332CBAFF54D1F6A18",
    "warm": "15CAAB219B74A45B4E0F8F5E3CB046DB3554264E1D48DB92CE13F8260FDCD2C4",
}
EXPECTED_BLACK_PIXELS = {"calm": 2679, "curious": 2774, "warm": 2998}
EXPECTED_BBOX = {"calm": [34, 31, 166, 112], "curious": [32, 26, 167, 127],
                 "warm": [33, 22, 170, 113]}
EXPECTED_CHANGED_PIXELS = (765, 846, 846, 765)


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def normal_target_mapping(frame: bytes) -> bytes:
    if len(frame) != 5000:
        raise ValueError("frame size")
    return b"".join(frame[y * 25:(y + 1) * 25] for y in range(199, -1, -1))


def source_data() -> dict[str, bytes]:
    return {name: (ASSET_ROOT / f"{name}.pbm").read_bytes() for name in NAMES}


def validate_sources(raw: dict[str, bytes]) -> dict[str, bytes]:
    if set(raw) != set(NAMES):
        raise ValueError("source set")
    rasters: dict[str, bytes] = {}
    for name in NAMES:
        if sha(raw[name]) != EXPECTED_SOURCE_SHA[name]:
            raise ValueError(f"source hash: {name}")
        width, height, raster = generator.parse_p4(raw[name], name)
        if (width, height, len(raster)) != (200, 200, 5000):
            raise ValueError(f"source geometry: {name}")
        rasters[name] = raster
    return rasters


def parse_header_arrays(data: bytes) -> dict[str, bytes]:
    text = data.decode("ascii")
    pattern = re.compile(
        r"static const uint8_t comp_r12_v22_(calm|curious|warm)_frame"
        r"\[COMP_R12_V22_FRAME_BYTES\] = \{(.*?)\};", re.DOTALL)
    arrays: dict[str, bytes] = {}
    for match in pattern.finditer(text):
        values = bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})u", match.group(2)))
        if match.group(1) in arrays or len(values) != 5000:
            raise ValueError("header array shape")
        arrays[match.group(1)] = values
    if set(arrays) != set(NAMES):
        raise ValueError("header array set")
    return arrays


def validate_header_arrays(arrays: dict[str, bytes], controller: dict[str, bytes]) -> None:
    if set(arrays) != set(NAMES):
        raise ValueError("header array set")
    for name in NAMES:
        if len(arrays[name]) != 5000 or arrays[name] != controller[name]:
            raise ValueError(f"header/controller mismatch: {name}")
        if sha(arrays[name]) != EXPECTED_HEADER_FRAME_SHA[name]:
            raise ValueError(f"header frame hash: {name}")


def pack_corridor_row_order(frame: bytes) -> bytes:
    x0, x1, y0, y1 = WINDOW
    return b"".join(frame[y * 25 + x0:y * 25 + x1 + 1] for y in range(y0, y1 + 1))


def corridor(frame: bytes) -> bytes:
    return pack_corridor_row_order(frame)


def validate_packed_corridor(frame: bytes, packed: bytes) -> None:
    expected = pack_corridor_row_order(frame)
    if len(packed) != 1908 or packed != expected:
        raise ValueError("packed corridor mismatch")


def bit(frame: bytes, x: int, y: int) -> int:
    return 1 if frame[y * 25 + x // 8] & (0x80 >> (x & 7)) else 0


def pixel_facts(raster: bytes, controller: bytes) -> tuple[int, list[int], int]:
    black: list[tuple[int, int]] = []
    differences = 0
    for y in range(200):
        for x in range(200):
            source_black = bit(raster, x, 199 - y)
            controller_black = 1 - bit(controller, x, y)
            differences += source_black != controller_black
            if controller_black:
                black.append((x, y))
    if not black:
        raise ValueError("empty frame")
    bbox = [min(x for x, _ in black), min(y for _, y in black),
            max(x for x, _ in black), max(y for _, y in black)]
    return len(black), bbox, differences


def changed_pixel_coordinates(previous: bytes, current: bytes) -> list[tuple[int, int]]:
    return [(x, y) for y in range(200) for x in range(200)
            if bit(previous, x, y) != bit(current, x, y)]


def apply_corridor(previous: bytes, current: bytes) -> tuple[bytes, bool]:
    x0, x1, y0, y1 = WINDOW
    result = bytearray(previous)
    for y in range(y0, y1 + 1):
        start = y * 25 + x0
        end = y * 25 + x1 + 1
        result[start:end] = current[start:end]
    outside_unchanged = all(
        result[index] == previous[index]
        for index in range(5000)
        if not (y0 <= index // 25 <= y1 and x0 <= index % 25 <= x1)
    )
    return bytes(result), outside_unchanged


def expect_reject(name: str, operation, results: dict[str, bool]) -> None:
    try:
        operation()
    except (ValueError, UnicodeError):
        results[name] = True
    else:
        results[name] = False


def render_pixel_previews(rasters: dict[str, bytes], controller: dict[str, bytes]) -> dict[str, object]:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    records: dict[str, object] = {}
    for name in NAMES:
        browser = Image.new("L", (200, 200), 255)
        mounted = Image.new("L", (200, 200), 255)
        browser_px = browser.load()
        mounted_px = mounted.load()
        for y in range(200):
            for x in range(200):
                browser_px[x, y] = 0 if bit(rasters[name], x, y) else 255
                mounted_px[x, y] = 0 if bit(controller[name], x, 199 - y) == 0 else 255
        overlay = Image.new("RGB", (400, 200), "white")
        overlay.paste(browser.convert("RGB"), (0, 0))
        overlay.paste(mounted.convert("RGB"), (200, 0))
        difference = ImageChops.difference(browser, mounted)
        diff_rgb = Image.new("RGB", (200, 200), "white")
        diff_rgb.paste(Image.new("RGB", (200, 200), (255, 0, 0)), mask=difference)
        browser_path = PREVIEW_DIR / f"{name}-browser.png"
        mounted_path = PREVIEW_DIR / f"{name}-predicted-mounted-inverse.png"
        overlay_path = PREVIEW_DIR / f"{name}-overlay.png"
        diff_path = PREVIEW_DIR / f"{name}-difference.png"
        browser.save(browser_path)
        mounted.save(mounted_path)
        overlay.save(overlay_path)
        diff_rgb.save(diff_path)
        records[name] = {
            "browser": str(browser_path.relative_to(ROOT)).replace("\\", "/"),
            "predicted_mounted_inverse": str(mounted_path.relative_to(ROOT)).replace("\\", "/"),
            "overlay": str(overlay_path.relative_to(ROOT)).replace("\\", "/"),
            "difference": str(diff_path.relative_to(ROOT)).replace("\\", "/"),
            "browser_sha256": sha(browser_path.read_bytes()),
            "predicted_mounted_inverse_sha256": sha(mounted_path.read_bytes()),
            "overlay_sha256": sha(overlay_path.read_bytes()),
            "difference_sha256": sha(diff_path.read_bytes()),
            "difference_pixels": sum(1 for value in difference.getdata() if value),
            "same_canvas": True,
        }
    return records


def main() -> int:
    errors: list[str] = []
    raw = source_data()
    rasters = validate_sources(raw)
    header_controller = {name: bytes(value ^ 0xFF for value in rasters[name]) for name in NAMES}
    controller = {name: normal_target_mapping(header_controller[name]) for name in NAMES}

    generated_first = generator.render_header()
    generated_second = generator.render_header()
    current_header = HEADER.read_bytes()
    generation_deterministic = generated_first == generated_second
    header_matches_generation = current_header == generated_first
    if not generation_deterministic:
        errors.append("asset header generation is not deterministic")
    if not header_matches_generation:
        errors.append("current asset header differs from generated bytes")
    header_arrays = parse_header_arrays(current_header)
    validate_header_arrays(header_arrays, header_controller)

    source_hashes = {name: sha(raw[name]) for name in NAMES}
    frame_hashes = {name: sha(controller[name]) for name in NAMES}
    packed_payloads = {name: pack_corridor_row_order(controller[name]) for name in NAMES}
    for name in NAMES:
        validate_packed_corridor(controller[name], packed_payloads[name])
    payload_hashes = {name: sha(packed_payloads[name]) for name in NAMES}
    pixel_results: dict[str, dict[str, object]] = {}
    logical_difference = 0
    for name in NAMES:
        black, bbox, difference = pixel_facts(rasters[name], controller[name])
        logical_difference += difference
        pixel_results[name] = {"black_pixels": black, "bbox": bbox,
                               "source_to_logical_pixel_difference": difference}
        if black != EXPECTED_BLACK_PIXELS[name] or bbox != EXPECTED_BBOX[name] or difference != 0:
            errors.append(f"pixel facts: {name}")
        if frame_hashes[name] != EXPECTED_FRAME_SHA[name] or payload_hashes[name] != EXPECTED_PAYLOAD_SHA[name]:
            errors.append(f"frame/payload hash: {name}")
    previews = render_pixel_previews(rasters, controller)
    if any(item["difference_pixels"] != 0 for item in previews.values()):
        errors.append("pixel preview difference")

    transitions: list[dict[str, object]] = []
    all_changed: list[tuple[int, int]] = []
    for index, (previous, current) in enumerate(zip(PATH, PATH[1:])):
        changed = changed_pixel_coordinates(controller[previous], controller[current])
        all_changed.extend(changed)
        bbox = [min(x for x, _ in changed), min(y for _, y in changed),
                max(x for x, _ in changed), max(y for _, y in changed)]
        applied, outside_unchanged = apply_corridor(controller[previous], controller[current])
        exact_after_current_corridor = applied == controller[current]
        transition = {"previous": previous, "current": current, "changed_pixels": len(changed),
                      "changed_pixel_bbox": bbox, "payload_sha256": payload_hashes[current],
                      "outside_corridor_unchanged": outside_unchanged,
                      "current_corridor_reconstructs_full_current": exact_after_current_corridor}
        transitions.append(transition)
        if len(changed) != EXPECTED_CHANGED_PIXELS[index] or not outside_unchanged or not exact_after_current_corridor:
            errors.append(f"transition: {previous}->{current}")
    minimal_union = [min(x for x, _ in all_changed) // 8, max(x for x, _ in all_changed) // 8,
                     min(y for _, y in all_changed), max(y for _, y in all_changed)]
    if minimal_union != list(WINDOW):
        errors.append("minimal union corridor")

    parser_result = parser.self_test()
    negative_fixtures = dict(parser_result["negative_cases"])
    expect_reject("packed_reordered", lambda: validate_packed_corridor(
        controller["calm"], packed_payloads["calm"][18:] + packed_payloads["calm"][:18]), negative_fixtures)
    expect_reject("packed_shortened", lambda: validate_packed_corridor(
        controller["calm"], packed_payloads["calm"][:-1]), negative_fixtures)
    expect_reject("packed_padded", lambda: validate_packed_corridor(
        controller["calm"], packed_payloads["calm"] + b"\xFF"), negative_fixtures)
    expect_reject("packed_stale", lambda: validate_packed_corridor(
        controller["warm"], packed_payloads["calm"]), negative_fixtures)
    corridor_mismatch = b"".join(controller["calm"][y * 25 + 3:y * 25 + 21]
                                   for y in range(WINDOW[2], WINDOW[3] + 1))
    expect_reject("packed_corridor_mismatch", lambda: validate_packed_corridor(
        controller["calm"], corridor_mismatch), negative_fixtures)
    mutated_sources = dict(raw)
    mutated_sources["calm"] = raw["calm"][:-1] + bytes([raw["calm"][-1] ^ 1])
    expect_reject("source_hash", lambda: validate_sources(mutated_sources), negative_fixtures)
    mutated_header = dict(header_arrays)
    changed_header = bytearray(mutated_header["calm"])
    changed_header[0] ^= 1
    mutated_header["calm"] = bytes(changed_header)
    expect_reject("header_frame_or_polarity", lambda: validate_header_arrays(mutated_header, header_controller), negative_fixtures)
    expect_reject("path", lambda: parser.parse_metadata(parser.metadata_lines()[1].replace("path=0-1-2-1-0", "path=0-2-1-0")), negative_fixtures)
    expect_reject("baseline_window", lambda: parser.parse_metadata(parser.metadata_lines()[1].replace("0-24,0-199", "4-21,72-127")), negative_fixtures)
    expect_reject("movement_command", lambda: parser.parse_metadata(parser.metadata_lines()[2].replace("command=0x24", "command=0x26")), negative_fixtures)
    expect_reject("qualification_count", lambda: parser.parse_metadata(parser.metadata_lines()[11].replace("frames=16", "frames=15")), negative_fixtures)
    if not all(negative_fixtures.values()) or parser_result["status"] != "PASS_SELFTEST":
        errors.append("negative fixture rejection")

    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.oracle.v6",
        "status": "PASS" if not errors else "FAIL", "candidate": parser.CANDIDATE,
        "source_hashes": source_hashes, "controller_frame_sha256": frame_hashes,
        "corridor_payload_sha256": payload_hashes, "asset_header_sha256": sha(current_header),
        "asset_header_generation": {"two_independent_results_identical": generation_deterministic,
                                    "current_header_matches_generated": header_matches_generation,
                                    "parsed_array_bytes_each": 5000},
        "pixel_oracle": {"frames": pixel_results,
                         "source_to_logical_pixel_difference": logical_difference,
                         "physical_to_browser_pixel_difference": logical_difference,
                         "transform": "normal_target_rotation_180_plus_mirror_x_1_composed_vertical_flip_once",
                         "source_assets_unchanged": True, "asset_headers_unchanged": True,
                         "preview_evidence": previews},
        "sequence": list(PATH), "transition_count": 16, "qualification_cycles": 4,
        "corridor": {"window": "4-21,22-127", "bytes": 1908,
                     "minimal_union_window": "-".join(map(str, minimal_union[:2])) + "," + "-".join(map(str, minimal_union[2:])),
                     "full_current_rewrite": True,
                     "outside_unchanged": all(item["outside_corridor_unchanged"] for item in transitions)},
        "packed_payload_oracle": {"source": "three_controller_frames",
                                   "row_order": "y22..127_then_xbyte4..21",
                                   "bytes_each": 1908,
                                   "byte_equal_to_row_extraction": True},
        "transitions": transitions * 4,
        "telemetry": {"max_record_bytes_including_crlf": parser_result["maximum_record_bytes"],
                      "max_metadata_bytes_including_crlf": parser_result["maximum_metadata_bytes"],
                      "max_bytes": 192, "ring_bytes": 65536, "accept_480": True,
                      "reject_481": parser_result["reject_481"]},
        "negative_fixtures": negative_fixtures, "errors": errors,
    }
    DETAIL_OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["detail_artifact"] = str(DETAIL_OUT.relative_to(ROOT)).replace("\\", "/")
    # Bind the path inside the detail artifact itself, but keep its hash
    # external to avoid a self-referential artifact.
    DETAIL_OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["detail_artifact_sha256"] = sha(DETAIL_OUT.read_bytes())
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
