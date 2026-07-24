#!/usr/bin/env python3
"""Compose V35 source-derived emotion decorations over V9 Rig base frames."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
BASES = {
    "center": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_daily_calm_center.pbm",
    "right": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_daily_calm_right.pbm",
    "up": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_daily_calm_up.pbm",
    "sleepy": ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/pbm/matrix_sleep_low_center.pbm",
}
SOURCES = {
    "curious_question": ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate-curious-question-v1.png",
    "alert_exclamation": ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate-alert-exclamation-v1.png",
    "sleepy_dream_cloud": ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate-sleepy-dream-cloud-v1.png",
}
FACE_BOXES = ((42, 112, 33, 45), (125, 112, 34, 45), (47, 85, 23, 12),
              (132, 85, 23, 12), (94, 148, 13, 8), (86, 160, 29, 10))
PRESENCE = {
    "curious_question": {"bases": ["center", "right", "right"], "placements": [(142, 34, 16, 27), (140, 31, 16, 28), (138, 28, 16, 27)]},
    "alert_exclamation": {"bases": ["center", "up", "up"], "placements": [(97, 37, 5, 20), (96, 30, 7, 27), (96, 24, 7, 34)]},
    "sleepy_dream_cloud": {"bases": ["sleepy", "sleepy", "sleepy"], "placements": [(39, 39, 26, 20), (32, 33, 31, 20), (26, 27, 36, 20)]},
}
DURATIONS = [700, 420, 420]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_masks(path: Path) -> list[Image.Image]:
    image = Image.open(path).convert("L")
    width = image.width // 3
    masks: list[Image.Image] = []
    for index in range(3):
        cell = image.crop((index * width, 0, (index + 1) * width if index < 2 else image.width, image.height))
        mask = cell.point(lambda value: 255 if value < 128 else 0, mode="L")
        bbox = mask.getbbox()
        if bbox is None:
            raise ValueError(f"{path.name} source cell {index} has no ink")
        masks.append(mask.crop(bbox))
    return masks


def resize_mask(mask: Image.Image, width: int, height: int) -> Image.Image:
    return mask.resize((width, height), Image.Resampling.LANCZOS).point(lambda value: 255 if value >= 128 else 0, mode="L")


def restore_primary_face(canvas: Image.Image, base: Image.Image) -> None:
    for x, y, width, height in FACE_BOXES:
        canvas.paste(base.crop((x, y, x + width, y + height)), (x, y))


def compose(base: Image.Image, mask: Image.Image | None, placement: tuple[int, int, int, int] | None) -> Image.Image:
    canvas = base.copy()
    if mask is not None and placement is not None:
        x, y, width, height = placement
        if x < 8 or y < 8 or x + width > 192 or y + height > 192:
            raise ValueError(f"decoration exceeds native event safe area: {placement}")
        canvas.paste(0, (x, y), resize_mask(mask, width, height))
    restore_primary_face(canvas, base)
    return canvas


def save_sequence(output_dir: Path, name: str, frames: list[Image.Image], durations: list[int]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, frame in enumerate(frames):
        png_path = output_dir / f"{name}-{index:02d}.png"
        pbm_path = output_dir / f"{name}-{index:02d}.pbm"
        frame.save(png_path)
        frame.save(pbm_path)
        records.append({"frame": index, "png": str(png_path.relative_to(ROOT)).replace('\\', '/'),
                        "pbm": str(pbm_path.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(png_path),
                        "duration_ms": durations[index]})
    frames[0].save(output_dir / f"{name}.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=2)
    return records


def contact_sheet(groups: list[list[Image.Image]], output_path: Path) -> None:
    sheet = Image.new("1", (600, 600), 1)
    for row, frames in enumerate(groups):
        for column, frame in enumerate(frames):
            sheet.paste(frame, (column * 200, row * 200))
    sheet.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1/candidate/review-v1")
    parser.add_argument("--report", default="docs/validation/companion-v35-emotion-decoration-native-200-render-20260720.json")
    args = parser.parse_args()
    if not LOCKED_V9.is_file() or sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        raise ValueError("locked V9 source is missing or drifted")
    if not all(path.is_file() for path in BASES.values()) or not all(path.is_file() for path in SOURCES.values()):
        raise ValueError("a V9 Rig base or V35 source is missing")
    bases = {name: Image.open(path).convert("1") for name, path in BASES.items()}
    if any(image.size != (200, 200) for image in bases.values()):
        raise ValueError("all V9 Rig bases must be 200x200")
    masks = {name: source_masks(path) for name, path in SOURCES.items()}
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_events: dict[str, object] = {}
    presence_groups: list[list[Image.Image]] = []
    for name, definition in PRESENCE.items():
        frames = [compose(bases[definition["bases"][index]], masks[name][index], definition["placements"][index]) for index in range(3)]
        presence_groups.append(frames)
        bridge = [compose(bases["center"], None, None), compose(bases[definition["bases"][1]], None, None), *frames]
        report_events[name] = {
            "presence_daily_bases": definition["bases"],
            "presence": save_sequence(output_dir, f"{name}-presence", frames, DURATIONS),
            "transition": save_sequence(output_dir, f"calm-to-{name}-transition", bridge, [680, 240, *DURATIONS]),
            "transition_order": ["source_hold", "highlight_lead", "decoration_follow_through", "target_hold"]
        }
    contact = output_dir / "contact-native-200.png"
    contact_sheet(presence_groups, contact)
    report = {
        "schema": "companion.v35.emotion_decoration_native_200_render.v1",
        "status": "CANDIDATE_PENDING_INTERNAL_NATIVE_200_REVIEW",
        "authority": "COMP-REQ-190",
        "locked_v9": {"path": str(LOCKED_V9.relative_to(ROOT)).replace('\\', '/'), "sha256": LOCKED_V9_SHA256},
        "daily_rig_bases": {name: {"path": str(path.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(path)} for name, path in BASES.items()},
        "generated_sources": {name: {"path": str(path.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(path)} for name, path in SOURCES.items()},
        "composition": {"canvas": [200, 200], "safe_inset_px": 8, "face_channels_restored_above_decoration": ["eyes", "brows", "nose", "mouth"], "rendering_policy": "source-derived masks only; no code-drawn visual feature"},
        "events": report_events,
        "contact_sheet": {"path": str(contact.relative_to(ROOT)).replace('\\', '/'), "sha256": sha256(contact)},
        "runtime": {"resource_activated": False, "component_export": "forbidden_until_source_gate_passes"}
    }
    report_path = (ROOT / args.report).resolve()
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
