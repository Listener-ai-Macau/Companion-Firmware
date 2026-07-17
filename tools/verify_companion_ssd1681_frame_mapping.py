#!/usr/bin/env python3
"""Prove the SSD1681 200x200 transform/window path cannot crop a source pixel.

This is deliberately a host-only proof.  It checks the exact source tokens for
the WB55 driver's byte/bit transforms, then exhaustively maps every logical
pixel through each supported build orientation and through the driver's
descending-Y SSD1681 RAM addressing.  It cannot prove the analog panel viewport
or the physical image, so it leaves the owner feedback gate open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb_ssd1681.c"
BUILD_WRAPPER = ROOT / "tools" / "build_nucleo_bringup.ps1"
ART_DIR = ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9"
MANIFEST = ART_DIR / "rendered-200x200" / "v9-expression-cemp-manifest.json"
SOURCE = ART_DIR / "generated_pet_expression_sheet_v9_candidate.png"
REPORT = ROOT / "docs" / "validation" / "companion-ssd1681-frame-mapping-20260717.json"

WIDTH = 200
HEIGHT = 200
BYTES_PER_ROW = 25
EXPECTED_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
ACTUAL_BUILD_ROTATION = 180
ACTUAL_BUILD_MIRROR_X = 1


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_source_contract(driver: str, wrapper: str, errors: list[str]) -> None:
    for token in (
        "#define SSD1681_WIDTH 200u",
        "#define SSD1681_HEIGHT 200u",
        "#define SSD1681_BYTES_PER_ROW (SSD1681_WIDTH / 8u)",
        "static uint8_t frame_reverse_bits(uint8_t value)",
        "static void frame_apply_target_rotation(void)",
        "#if COMPANION_EPAPER_SSD1681_ROTATION_DEGREES == 180u",
        "for (size_t left = 0u, right = sizeof(s_frame) - 1u; left < right;",
        "s_frame[left] = frame_reverse_bits(s_frame[right]);",
        "s_frame[right] = frame_reverse_bits(left_value);",
        "static void frame_apply_horizontal_mirror(void)",
        "#if COMPANION_EPAPER_SSD1681_MIRROR_X != 0u",
        "size_t right = left + SSD1681_BYTES_PER_ROW - 1u;",
        "s_frame[left] = frame_reverse_bits(s_frame[right]);",
        "s_frame[right] = frame_reverse_bits(left_value);",
        "controller_y_start = (SSD1681_HEIGHT - 1u) - window->y_start;",
        "controller_y_end = (SSD1681_HEIGHT - 1u) - window->y_end;",
        "static const uint8_t data_entry[] = {0x01u};",
        "frame_apply_target_rotation();",
        "frame_apply_horizontal_mirror();",
        "window = partial ? ssd1681_window_from_difference() : ssd1681_window_full();",
    ):
        if token not in driver:
            errors.append(f"driver transform/window contract drifted: missing {token!r}")
    for token in (
        "[int]$EpaperSsd1681Rotation = 180",
        "[int]$EpaperSsd1681MirrorX = 1",
        '"EPAPER_SSD1681_ROTATION=$EpaperSsd1681Rotation"',
        '"EPAPER_SSD1681_MIRROR_X=$EpaperSsd1681MirrorX"',
    ):
        if token not in wrapper:
            errors.append(f"WB55 build orientation contract drifted: missing {token!r}")


def frame_coordinate(x: int, y: int, rotation: int, mirror_x: int) -> tuple[int, int]:
    """Model the driver's byte reversal plus bit reversal in call order."""
    if rotation == 180:
        x, y = WIDTH - 1 - x, HEIGHT - 1 - y
    if mirror_x:
        x = WIDTH - 1 - x
    return x, y


def controller_coordinate(x: int, y: int) -> tuple[int, int, int]:
    """Model the source driver's byte/MSB-first X and descending SSD1681 Y."""
    return x // 8, 7 - (x % 8), HEIGHT - 1 - y


def exhaustive_configuration(rotation: int, mirror_x: int) -> dict[str, object]:
    seen_frame: set[tuple[int, int]] = set()
    seen_controller: set[tuple[int, int, int]] = set()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            frame_x, frame_y = frame_coordinate(x, y, rotation, mirror_x)
            controller = controller_coordinate(frame_x, frame_y)
            if not (0 <= frame_x < WIDTH and 0 <= frame_y < HEIGHT):
                raise ValueError(f"frame mapping escapes bounds for ({x}, {y})")
            if not (0 <= controller[0] < BYTES_PER_ROW and 0 <= controller[1] < 8 and 0 <= controller[2] < HEIGHT):
                raise ValueError(f"controller mapping escapes bounds for ({x}, {y})")
            seen_frame.add((frame_x, frame_y))
            seen_controller.add(controller)
    if len(seen_frame) != WIDTH * HEIGHT:
        raise ValueError(f"frame transform is not one-to-one: {len(seen_frame)} pixels")
    if len(seen_controller) != WIDTH * HEIGHT:
        raise ValueError(f"controller mapping is not one-to-one: {len(seen_controller)} pixels")
    corners = {
        f"{x},{y}": {
            "framebuffer": list(frame_coordinate(x, y, rotation, mirror_x)),
            "controller_ram": list(controller_coordinate(*frame_coordinate(x, y, rotation, mirror_x))),
        }
        for x, y in ((0, 0), (WIDTH - 1, 0), (0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1))
    }
    return {
        "rotation_degrees": rotation,
        "mirror_x": mirror_x,
        "logical_pixels": WIDTH * HEIGHT,
        "framebuffer_unique_pixels": len(seen_frame),
        "controller_unique_bits": len(seen_controller),
        "corners": corners,
    }


def frame_clearance(path: Path, rotation: int, mirror_x: int) -> dict[str, object]:
    image = Image.open(path).convert("1")
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"{path.name} is {image.size}, expected {(WIDTH, HEIGHT)}")
    pixels = image.load()
    mapped = [
        frame_coordinate(x, y, rotation, mirror_x)
        for y in range(HEIGHT)
        for x in range(WIDTH)
        if pixels[x, y] == 0
    ]
    if not mapped:
        raise ValueError(f"{path.name} has no visible ink")
    xs, ys = zip(*mapped)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    clearance = {
        "left": left,
        "top": top,
        "right": WIDTH - 1 - right,
        "bottom": HEIGHT - 1 - bottom,
    }
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "mapped_ink_bbox": [left, top, right - left + 1, bottom - top + 1],
        "mapped_edge_clearance_px": clearance,
        "minimum_clearance_px": min(clearance.values()),
    }


def build_report() -> dict[str, object]:
    errors: list[str] = []
    driver = DRIVER.read_text(encoding="utf-8") if DRIVER.is_file() else ""
    wrapper = BUILD_WRAPPER.read_text(encoding="utf-8") if BUILD_WRAPPER.is_file() else ""
    if not driver:
        errors.append(f"missing driver {DRIVER.relative_to(ROOT).as_posix()}")
    if not wrapper:
        errors.append(f"missing build wrapper {BUILD_WRAPPER.relative_to(ROOT).as_posix()}")
    require_source_contract(driver, wrapper, errors)

    configurations: list[dict[str, object]] = []
    for rotation in (0, 180):
        for mirror_x in (0, 1):
            try:
                configurations.append(exhaustive_configuration(rotation, mirror_x))
            except ValueError as exc:
                errors.append(str(exc))

    source_sha = sha256(SOURCE) if SOURCE.is_file() else None
    if source_sha != EXPECTED_SOURCE_SHA256:
        errors.append("v9 source hash drifted or is missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    if manifest.get("profile", {}).get("width") != WIDTH or manifest.get("profile", {}).get("height") != HEIGHT:
        errors.append("v9 manifest no longer targets the 200x200 panel")

    product_frames: list[dict[str, object]] = []
    for clip in manifest.get("clips", []):
        for frame in clip.get("frames", []):
            path = ART_DIR / "rendered-200x200" / str(frame.get("source", ""))
            try:
                result = frame_clearance(path, ACTUAL_BUILD_ROTATION, ACTUAL_BUILD_MIRROR_X)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                continue
            result["clip"] = clip.get("name")
            if int(result["minimum_clearance_px"]) < 4:
                errors.append(f"mapped frame edge clearance below 4 px: {result['path']}")
            product_frames.append(result)
    if len(product_frames) != 39:
        errors.append(f"expected 39 v9 frames, mapped {len(product_frames)}")

    return {
        "schema": "companion.ssd1681_frame_mapping.v1",
        "status": "PASS_MACHINE_EXHAUSTIVE_FRAME_MAPPING_PHYSICAL_REVIEW_PENDING" if not errors else "FAIL",
        "source_driver": {
            "path": DRIVER.relative_to(ROOT).as_posix(),
            "sha256": sha256(DRIVER) if DRIVER.is_file() else None,
        },
        "geometry": {"width": WIDTH, "height": HEIGHT, "bytes_per_row": BYTES_PER_ROW},
        "supported_build_configurations": configurations,
        "product_build_orientation": {
            "rotation_degrees": ACTUAL_BUILD_ROTATION,
            "mirror_x": ACTUAL_BUILD_MIRROR_X,
            "framebuffer_mapping": "logical (x,y) -> framebuffer (x,199-y)",
            "controller_mapping": "framebuffer (x,y) -> SSD1681 byte x//8, MSB bit 7-(x%8), RAM y 199-y",
        },
        "v9_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": source_sha,
            "frame_count": len(product_frames),
            "mapped_frames": product_frames,
            "minimum_mapped_edge_clearance_px": min(
                (int(frame["minimum_clearance_px"]) for frame in product_frames), default=0
            ),
        },
        "hardware_boundary": {
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "panel_command": False,
            "camera_or_human_visual_pass": False,
            "physical_panel_viewport_proved": False,
        },
        "conclusion": "The compiled 200x200 transforms and RAM window mapping are exhaustive, one-to-one and in-bounds. This does not clear the physical lower-edge truncation report; G5 still requires real-panel inspection.",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the deterministic mapping report.")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        REPORT.write_text(rendered, encoding="utf-8")
    elif not REPORT.is_file() or REPORT.read_text(encoding="utf-8") != rendered:
        report["errors"].append(f"stale {REPORT.relative_to(ROOT).as_posix()}")
    if report["errors"]:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        return 1
    print("PASS: SSD1681 frame transforms and RAM addressing map all 40,000 pixels in-bounds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
