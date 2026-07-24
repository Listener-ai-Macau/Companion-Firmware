#!/usr/bin/env python3
"""Compose V34 generated event-overlay masks over the locked V9 daily baseline.

This tool never draws a facial feature or invents decoration pixels. It extracts
connected black-ink masks from versioned generated source sheets and composes
them with the locked 200x200 V9 daily source. The protected V9 face layers are
restored above the overlay so eye, brow and mouth performance remains primary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (200, 200)
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
DAILY_BASES = {
    "center": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_daily_calm_center.pbm",
    "right": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_daily_calm_right.pbm",
    "down": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_daily_calm_down.pbm",
}
RECORDING_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-event-overlay-v1/candidate-recording-input-v1.png"
CHARGING_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-event-overlay-v1/candidate-bottom-connector-charging-v2.png"


@dataclass(frozen=True)
class InkPart:
    area: int
    bbox: tuple[int, int, int, int]
    mask: Image.Image


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def binary_mask(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 255 if value < 128 else 0, mode="L")


def split_sheet(path: Path) -> list[Image.Image]:
    image = Image.open(path).convert("L")
    if image.width < 300:
        raise ValueError(f"{path} is not a three-cell source sheet")
    cell_width = image.width // 3
    return [
        image.crop((index * cell_width, 0, (index + 1) * cell_width if index < 2 else image.width, image.height))
        for index in range(3)
    ]


def connected_ink_parts(image: Image.Image) -> list[InkPart]:
    mask = binary_mask(image)
    width, height = mask.size
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    parts: list[InkPart] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] == 0:
                continue
            pending = [(x, y)]
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while pending:
                current_x, current_y = pending.pop()
                points.append((current_x, current_y))
                for next_x in (current_x - 1, current_x, current_x + 1):
                    for next_y in (current_y - 1, current_y, current_y + 1):
                        if (0 <= next_x < width and 0 <= next_y < height and
                                (next_x, next_y) not in seen and pixels[next_x, next_y] != 0):
                            seen.add((next_x, next_y))
                            pending.append((next_x, next_y))
            if len(points) < 64:
                continue
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points) + 1
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points) + 1
            part_mask = Image.new("L", (max_x - min_x, max_y - min_y), 0)
            part_pixels = part_mask.load()
            for point_x, point_y in points:
                part_pixels[point_x - min_x, point_y - min_y] = 255
            parts.append(InkPart(len(points), (min_x, min_y, max_x, max_y), part_mask))
    return sorted(parts, key=lambda part: part.area, reverse=True)


def resize_mask(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    return mask.resize(size, Image.Resampling.LANCZOS).point(lambda value: 255 if value >= 128 else 0, mode="L")


def bottom_connector_mask(cell: Image.Image) -> Image.Image:
    """Select the generated central underside attachment, excluding its unused long outline."""
    mask = binary_mask(cell)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("bottom-connector source cell is empty")
    center_x = cell.width // 2
    crop = mask.crop((center_x - 50, bbox[1] + 55, center_x + 50, bbox[3]))
    cropped_bbox = crop.getbbox()
    if cropped_bbox is None:
        raise ValueError("bottom-connector crop is empty")
    return crop.crop(cropped_bbox)


def paste_ink(canvas: Image.Image, mask: Image.Image, position: tuple[int, int]) -> None:
    x, y = position
    if x < 8 or y < 8 or x + mask.width > 192 or y + mask.height > 192:
        raise ValueError(f"overlay mask escapes the 8 px event-overlay safe area at {position} with {mask.size}")
    canvas.paste(0, position, mask)


def restore_primary_face(canvas: Image.Image, daily: Image.Image) -> None:
    # These crops are locked V9 source pixels, re-layered so overlays cannot cover the face-performance channels.
    for x, y, width, height in ((42, 112, 33, 45), (125, 112, 34, 45), (47, 85, 23, 12),
                                (132, 85, 23, 12), (94, 148, 13, 8), (86, 160, 29, 10)):
        canvas.paste(daily.crop((x, y, x + width, y + height)), (x, y))


def recording_frames(daily_bases: dict[str, Image.Image]) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index, cell in enumerate(split_sheet(RECORDING_SOURCE)):
        parts = connected_ink_parts(cell)
        if not parts:
            raise ValueError(f"recording source cell {index} is empty")
        daily = daily_bases[("center", "right", "right")[index]]
        canvas = daily.copy()
        microphone = resize_mask(parts[0].mask, (9, 19))
        paste_ink(canvas, microphone, (182, 127))
        if index == 1:
            paste_ink(canvas, resize_mask(parts[1].mask, (4, 12)), (168, 130))
        if index == 2:
            arcs = sorted(parts[1:], key=lambda part: part.bbox[0])
            paste_ink(canvas, resize_mask(arcs[0].mask, (4, 12)), (163, 130))
            paste_ink(canvas, resize_mask(arcs[1].mask, (5, 18)), (170, 127))
        restore_primary_face(canvas, daily)
        frames.append(canvas)
    return frames


def charging_frames(daily_bases: dict[str, Image.Image]) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index, cell in enumerate(split_sheet(CHARGING_SOURCE)):
        parts = connected_ink_parts(cell)
        if not parts:
            raise ValueError(f"charging source cell {index} is empty")
        daily = daily_bases[("center", "down", "down")[index]]
        canvas = daily.copy()
        paste_ink(canvas, resize_mask(bottom_connector_mask(cell), (42, 20)), (79, 172))
        if index == 1:
            paste_ink(canvas, resize_mask(parts[1].mask, (8, 3)), (96, 168))
        if index == 2:
            arcs = sorted(parts[1:], key=lambda part: part.area, reverse=True)
            paste_ink(canvas, resize_mask(arcs[0].mask, (16, 4)), (92, 163))
            paste_ink(canvas, resize_mask(arcs[1].mask, (10, 3)), (95, 168))
        restore_primary_face(canvas, daily)
        frames.append(canvas)
    return frames


def save_frames(output_dir: Path, prefix: str, frames: list[Image.Image]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, frame in enumerate(frames):
        png_path = output_dir / f"{prefix}-{index:02d}.png"
        pbm_path = output_dir / f"{prefix}-{index:02d}.pbm"
        frame.save(png_path)
        frame.save(pbm_path)
        records.append({"frame": index, "png": str(png_path.relative_to(ROOT)).replace('\\', '/'),
                        "pbm": str(pbm_path.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(png_path)})
    gif_path = output_dir / f"{prefix}.gif"
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=[700, 420, 420], loop=0, disposal=2)
    return records


def contact_sheet(recording: list[Image.Image], charging: list[Image.Image], output_path: Path) -> None:
    sheet = Image.new("1", (600, 400), 1)
    for index, frame in enumerate(recording):
        sheet.paste(frame, (index * 200, 0))
    for index, frame in enumerate(charging):
        sheet.paste(frame, (index * 200, 200))
    sheet.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="docs/art/iterations/companion-pet-expression-v9-event-overlay-v1/candidate/review-v1")
    parser.add_argument("--report", default="docs/validation/companion-v34-event-overlay-native-200-render-20260720.json")
    args = parser.parse_args()
    if not LOCKED_V9.is_file() or sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        raise ValueError("locked V9 identity source is missing or drifted")
    if not all(path.is_file() for path in DAILY_BASES.values()) or not RECORDING_SOURCE.is_file() or not CHARGING_SOURCE.is_file():
        raise ValueError("daily Rig baseline or V34 generated source is missing")
    daily_bases = {name: Image.open(path).convert("1") for name, path in DAILY_BASES.items()}
    if any(image.size != CANVAS for image in daily_bases.values()):
        raise ValueError("every daily Rig source must be exactly 200x200")
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    recording = recording_frames(daily_bases)
    charging = charging_frames(daily_bases)
    report = {
        "schema": "companion.v34.event_overlay_native_200_render.v1",
        "status": "CANDIDATE_PENDING_INTERNAL_NATIVE_200_REVIEW",
        "authority": "COMP-REQ-187",
        "locked_v9": {"path": str(LOCKED_V9.relative_to(ROOT)).replace('\\', '/'), "sha256": LOCKED_V9_SHA256},
        "daily_micro_bases": {
            name: {"path": str(path.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(path)}
            for name, path in DAILY_BASES.items()
        },
        "generated_sources": {
            "recording_input": {"path": str(RECORDING_SOURCE.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(RECORDING_SOURCE)},
            "bottom_connector_charging": {"path": str(CHARGING_SOURCE.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(CHARGING_SOURCE)}
        },
        "composition": {"canvas": [200, 200], "safe_inset_px": 8, "face_channels_restored_above_overlay": ["eyes", "brows", "nose", "mouth"],
                        "rendering_policy": "source-derived masks only; no code-drawn visual feature"},
        "overlays": {
            "recording_input": {"frames": save_frames(output_dir, "recording-input", recording), "sequence_ms": [700, 420, 420],
                                "daily_micro_sequence": ["center", "right", "right"],
                                "meaning": "the daily highlight turns toward a compact sensor as environment input pulses toward it"},
            "bottom_connector_charging": {"frames": save_frames(output_dir, "bottom-connector-charging", charging), "sequence_ms": [700, 420, 420],
                                  "daily_micro_sequence": ["center", "down", "down"],
                                  "meaning": "the daily highlight settles down toward the bottom-attached connector as restrained energy rises"}
        }
    }
    contact = output_dir / "contact-native-200.png"
    contact_sheet(recording, charging, contact)
    report["contact_sheet"] = {"path": str(contact.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(contact)}
    report_path = (ROOT / args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
