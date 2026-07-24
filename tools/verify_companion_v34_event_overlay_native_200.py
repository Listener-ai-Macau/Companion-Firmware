#!/usr/bin/env python3
"""Verify that V34 browser-preview pixels are target-ready 200x200 PBM frames."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
FACE_BOXES = ((42, 112, 33, 45), (125, 112, 34, 45), (47, 85, 23, 12),
              (132, 85, 23, 12), (94, 148, 13, 8), (86, 160, 29, 10))
EXPECTED = {
    "recording_input": ["center", "right", "right"],
    "bottom_connector_charging": ["center", "down", "down"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_image(path: Path) -> Image.Image:
    image = Image.open(path).convert("1")
    if image.size != (200, 200):
        raise ValueError(f"{path} must be 200x200, got {image.size}")
    return image


def changed_bounds(base: Image.Image, candidate: Image.Image) -> tuple[int, tuple[int, int, int, int]]:
    points: list[tuple[int, int]] = []
    for y in range(200):
        for x in range(200):
            if base.getpixel((x, y)) != candidate.getpixel((x, y)):
                points.append((x, y))
            if base.getpixel((x, y)) == 0 and candidate.getpixel((x, y)) != 0:
                raise ValueError("preview erased a baseline pixel instead of composing a source-derived overlay")
    if not points:
        raise ValueError("preview frame contains no event-overlay pixels")
    min_x = min(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_x = max(point[0] for point in points)
    max_y = max(point[1] for point in points)
    if min_x < 8 or min_y < 8 or max_x > 191 or max_y > 191:
        raise ValueError(f"event-overlay pixels escape the 8px safe area: {(min_x, min_y, max_x, max_y)}")
    return len(points), (min_x, min_y, max_x, max_y)


def assert_face_preserved(base: Image.Image, candidate: Image.Image) -> None:
    for x, y, width, height in FACE_BOXES:
        if base.crop((x, y, x + width, y + height)).tobytes() != candidate.crop((x, y, x + width, y + height)).tobytes():
            raise ValueError(f"event overlay changed protected facial pixels in {(x, y, width, height)}")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-report", default="docs/validation/companion-v34-event-overlay-native-200-render-20260720.json")
    parser.add_argument("--write", default="docs/validation/companion-v34-event-overlay-native-200-machine-gate-20260720.json")
    args = parser.parse_args()
    if sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        raise ValueError("locked V9 source hash drifted")
    render_path = ROOT / args.render_report
    render = json.loads(render_path.read_text(encoding="utf-8"))
    if render.get("status") != "CANDIDATE_PENDING_INTERNAL_NATIVE_200_REVIEW":
        raise ValueError("render report has an unexpected candidate state")
    if render.get("locked_v9", {}).get("sha256") != LOCKED_V9_SHA256:
        raise ValueError("render report is not rooted in locked V9")
    preview = ROOT / "docs/art/iterations/companion-pet-expression-v9-event-overlay-v1/candidate/review-v1/native-200-playback-preview.html"
    preview_text = preview.read_text(encoding="utf-8")
    records: dict[str, object] = {}
    for event_name, expected_micro in EXPECTED.items():
        event = render.get("overlays", {}).get(event_name)
        if not isinstance(event, dict) or event.get("daily_micro_sequence") != expected_micro:
            raise ValueError(f"{event_name} does not have the required daily Rig sequence")
        frame_records = event.get("frames")
        if not isinstance(frame_records, list) or len(frame_records) != 3:
            raise ValueError(f"{event_name} must retain exactly three deterministic frames")
        if event.get("sequence_ms") != [700, 420, 420]:
            raise ValueError(f"{event_name} has an unexpected playback timing")
        per_frame: list[dict[str, object]] = []
        hashes: list[str] = []
        for index, frame in enumerate(frame_records):
            png_path = ROOT / frame["png"]
            pbm_path = ROOT / frame["pbm"]
            png = load_image(png_path)
            pbm = load_image(pbm_path)
            if png.tobytes() != pbm.tobytes():
                raise ValueError(f"{event_name} frame {index} browser PNG and target PBM differ")
            if sha256(png_path) != frame.get("sha256"):
                raise ValueError(f"{event_name} frame {index} PNG hash drifted")
            base_info = render["daily_micro_bases"][expected_micro[index]]
            base = load_image(ROOT / base_info["path"])
            assert_face_preserved(base, png)
            changed_count, bounds = changed_bounds(base, png)
            if changed_count > 800:
                raise ValueError(f"{event_name} frame {index} changes too much of the daily face: {changed_count}")
            if png_path.name not in preview_text:
                raise ValueError(f"{event_name} frame {index} is absent from the native playback preview")
            hashes.append(frame["sha256"])
            per_frame.append({"frame": index, "changed_pixels": changed_count, "changed_bounds": list(bounds),
                              "png": relative(png_path), "pbm": relative(pbm_path)})
        if len(set(hashes)) != 3:
            raise ValueError(f"{event_name} does not visibly progress across its three frames")
        records[event_name] = {"daily_micro_sequence": expected_micro, "frames": per_frame}
    result = {
        "schema": "companion.v34.event_overlay_native_200_machine_gate.v1",
        "status": "PASS_MACHINE_PREVIEW_ONLY_RUNTIME_INACTIVE",
        "render_report": relative(render_path),
        "locked_v9_sha256": LOCKED_V9_SHA256,
        "checks": ["200x200 PNG/PBM pixel equality", "daily Rig base selection", "protected eye/brow/nose/mouth equality", "overlay-only additive pixels", "8px overlay safe area", "deterministic three-frame playback", "browser preview frame binding"],
        "events": records,
        "non_claims": ["no_component_export", "no_CRIG_binding", "no_firmware_flash", "no_panel_residue_clearance", "no_human_art_acceptance"]
    }
    write_path = ROOT / args.write
    write_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
