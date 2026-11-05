#!/usr/bin/env python3
"""Render the owner-approved v9 sheet into a machine-only 200x200 PBM candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from dataclasses import dataclass

from PIL import Image, ImageDraw

from companion_expression_anchor import ANCHOR_POLICY, CANONICAL_CENTER, normalize, output_bounds, translate


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9"
SOURCE = ART_DIR / "generated_pet_expression_sheet_v9_candidate.png"
EXPECTED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
OUT_DIR = ART_DIR / "rendered-200x200"
PBM_DIR = OUT_DIR / "pbm"
MANIFEST = OUT_DIR / "v9-expression-cemp-manifest.json"
REPORT = OUT_DIR / "v9-expression-render-report.json"
POSE_REVIEW = OUT_DIR / "v9-expression-reference-to-pbm.png"
FRAME_REVIEW = OUT_DIR / "v9-expression-frame-contact-sheet.png"

CANVAS = (200, 200)
THRESHOLD = 180


@dataclass(frozen=True)
class Pose:
    name: str
    row: int
    column: int
    crop_box: tuple[int, int, int, int]


@dataclass(frozen=True)
class FrameSpec:
    pose: str
    phase: str
    dx: int
    dy: int
    duration_ms: int


# These 300x300 source windows are intentionally explicit. They retain each
# complete v9 face and its semantic charm without sampling any retired sheet.
POSES = (
    Pose("idle_calm", 0, 0, (7, 92, 307, 392)),
    Pose("curious_tap", 0, 1, (320, 92, 620, 392)),
    Pose("swipe_left", 0, 2, (614, 92, 934, 412)),
    Pose("swipe_right", 0, 3, (947, 92, 1247, 392)),
    Pose("swipe_up", 1, 0, (7, 470, 307, 770)),
    Pose("swipe_down", 1, 1, (320, 470, 620, 770)),
    Pose("listening", 1, 2, (614, 450, 934, 770)),
    Pose("recording", 1, 3, (947, 470, 1247, 770)),
    Pose("saving", 2, 0, (7, 810, 307, 1110)),
    Pose("saved", 2, 1, (320, 810, 620, 1110)),
    Pose("sleep", 2, 2, (634, 810, 934, 1110)),
    Pose("menu_hold", 2, 3, (947, 810, 1247, 1110)),
)


CLIPS = (
    ("idle", (FrameSpec("idle_calm", "entry", 0, 0, 1800), FrameSpec("idle_calm", "sustain", -1, 0, 1300), FrameSpec("idle_calm", "settle", 0, 0, 1600))),
    ("touch", (FrameSpec("curious_tap", "entry", 0, 0, 700), FrameSpec("curious_tap", "sustain", 0, -1, 900), FrameSpec("curious_tap", "settle", 0, 0, 1400))),
    ("swipe_left", (FrameSpec("swipe_left", "entry", 1, 0, 650), FrameSpec("swipe_left", "sustain", 0, 0, 850), FrameSpec("swipe_left", "settle", -1, 0, 1100))),
    ("swipe_right", (FrameSpec("swipe_right", "entry", -1, 0, 650), FrameSpec("swipe_right", "sustain", 0, 0, 850), FrameSpec("swipe_right", "settle", 1, 0, 1100))),
    ("swipe_up", (FrameSpec("swipe_up", "entry", 0, 1, 650), FrameSpec("swipe_up", "sustain", 0, 0, 850), FrameSpec("swipe_up", "settle", 0, -1, 1100))),
    ("swipe_down", (FrameSpec("swipe_down", "entry", 0, -1, 650), FrameSpec("swipe_down", "sustain", 0, 0, 850), FrameSpec("swipe_down", "settle", 0, 1, 1100))),
    ("listening", (FrameSpec("listening", "entry", 0, 0, 1000), FrameSpec("listening", "sustain", 0, -1, 1200), FrameSpec("listening", "settle", 0, 0, 1400))),
    ("recording", (FrameSpec("recording", "entry", 0, 0, 900), FrameSpec("recording", "sustain", 1, 0, 1200), FrameSpec("recording", "settle", 0, 0, 1200))),
    ("saving", (FrameSpec("saving", "entry", 0, 0, 900), FrameSpec("saving", "sustain", 0, 1, 1100), FrameSpec("saving", "settle", 0, 0, 1000))),
    ("saved", (FrameSpec("saved", "entry", 0, 0, 800), FrameSpec("saved", "sustain", 0, -1, 1000), FrameSpec("saved", "settle", 0, 0, 1300))),
    # Sleep is intentionally static after entry: Stop must not create a wake loop.
    ("sleep", (FrameSpec("sleep", "entry", 0, 0, 1800), FrameSpec("sleep", "sustain", 0, 0, 3000), FrameSpec("sleep", "settle", 0, 0, 3000))),
    ("menu_hold", (FrameSpec("menu_hold", "entry", 0, 0, 900), FrameSpec("menu_hold", "sustain", 0, -1, 1200), FrameSpec("menu_hold", "settle", 0, 0, 1100))),
    ("wake", (FrameSpec("sleep", "entry", 0, 0, 700), FrameSpec("idle_calm", "sustain", 0, 0, 900), FrameSpec("curious_tap", "settle", 0, -1, 1100))),
)


def repo_rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def black_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            if pixels[x, y] == 0:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    return left, top, right - left + 1, bottom - top + 1


def edge_black_pixels(image: Image.Image) -> int:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    count = 0
    for x in range(bitmap.width):
        count += pixels[x, 0] == 0
        count += pixels[x, bitmap.height - 1] == 0
    for y in range(1, bitmap.height - 1):
        count += pixels[0, y] == 0
        count += pixels[bitmap.width - 1, y] == 0
    return count


def to_pbm(source: Image.Image, pose: Pose) -> tuple[Image.Image, Image.Image, object]:
    reference = source.crop(pose.crop_box).resize(CANVAS, Image.Resampling.LANCZOS)
    bitmap, anchor = normalize(reference, CANONICAL_CENTER)
    return reference, bitmap, anchor


def write_pose_review(items: list[tuple[Pose, Image.Image, Image.Image]]) -> None:
    cell_w, cell_h = 400, 270
    review = Image.new("RGB", (cell_w * 4, cell_h * 3), "white")
    draw = ImageDraw.Draw(review)
    for pose, reference, bitmap in items:
        x = pose.column * cell_w
        y = pose.row * cell_h
        ref = reference.convert("RGB").resize((160, 160), Image.Resampling.LANCZOS)
        pbm = bitmap.convert("RGB").resize((160, 160), Image.Resampling.NEAREST)
        review.paste(ref, (x + 20, y + 35))
        review.paste(pbm, (x + 220, y + 35))
        draw.rectangle((x + 20, y + 35, x + 179, y + 194), outline="black")
        draw.rectangle((x + 220, y + 35, x + 379, y + 194), outline="black")
        draw.text((x + 75, y + 10), "SOURCE", fill="black")
        draw.text((x + 280, y + 10), "PBM", fill="black")
        draw.text((x + 20, y + 215), pose.name, fill="black")
    POSE_REVIEW.parent.mkdir(parents=True, exist_ok=True)
    review.save(POSE_REVIEW)


def write_frame_review(frames: list[dict[str, object]]) -> None:
    cell_w, cell_h, columns = 260, 250, 3
    rows = (len(frames) + columns - 1) // columns
    review = Image.new("RGB", (cell_w * columns, cell_h * rows), "white")
    draw = ImageDraw.Draw(review)
    for index, frame in enumerate(frames):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        bitmap = Image.open(ROOT / str(frame["path"])).convert("1")
        thumb = bitmap.convert("RGB").resize((180, 180), Image.Resampling.NEAREST)
        review.paste(thumb, (x + 40, y + 22))
        draw.rectangle((x + 40, y + 22, x + 219, y + 201), outline="black")
        draw.text((x + 12, y + 208), f"{frame['clip']}.{frame['phase']}", fill="black")
        draw.text((x + 12, y + 226), f"{frame['pose']} dx={frame['translation'][0]} dy={frame['translation'][1]}", fill="black")
    FRAME_REVIEW.parent.mkdir(parents=True, exist_ok=True)
    review.save(FRAME_REVIEW)


def render() -> dict[str, object]:
    if sha256(SOURCE) != EXPECTED_SHA256:
        raise ValueError("v9 source hash drifted; renderer refuses to use another visual source")
    source = Image.open(SOURCE).convert("L")
    if source.size != (1254, 1254):
        raise ValueError("v9 source dimensions drifted; crop geometry is no longer valid")

    pose_by_name = {pose.name: pose for pose in POSES}
    pose_images: dict[str, Image.Image] = {}
    pose_anchors: dict[str, object] = {}
    pose_review_items: list[tuple[Pose, Image.Image, Image.Image]] = []
    for pose in POSES:
        reference, bitmap, anchor = to_pbm(source, pose)
        pose_images[pose.name] = bitmap
        pose_anchors[pose.name] = anchor
        pose_review_items.append((pose, reference, bitmap))

    rendered: list[dict[str, object]] = []
    manifest_clips: list[dict[str, object]] = []
    for clip_name, frame_specs in CLIPS:
        manifest_frames: list[dict[str, object]] = []
        for spec in frame_specs:
            pose = pose_by_name[spec.pose]
            image = translate(pose_images[spec.pose], (spec.dx, spec.dy))
            file_name = f"v9_{clip_name}_{spec.phase}.pbm"
            output = PBM_DIR / file_name
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output)
            bbox = output_bounds(image)
            anchor = pose_anchors[spec.pose]
            if edge_black_pixels(image):
                raise ValueError(f"{file_name} clips ink at a canvas edge")
            item = {
                "clip": clip_name,
                "phase": spec.phase,
                "pose": spec.pose,
                "path": repo_rel(output),
                "sha256": sha256(output),
                "source": repo_rel(SOURCE),
                "source_sha256": EXPECTED_SHA256,
                "source_crop_box": list(pose.crop_box),
                "anchor_policy": ANCHOR_POLICY,
                "source_anchor": list(anchor.source_anchor),
                "canonical_center": list(anchor.canonical_center),
                "normalization_offset": list(anchor.normalization_offset),
                "phase_offset": [spec.dx, spec.dy],
                "requested_center": [anchor.canonical_center[0] + spec.dx,
                                     anchor.canonical_center[1] + spec.dy],
                "translation": [spec.dx, spec.dy],
                "duration_ms": spec.duration_ms,
                "dirty": list(bbox),
                "final_output_bounds": list(bbox),
                "edge_black_pixels": edge_black_pixels(image),
            }
            rendered.append(item)
            manifest_frames.append(
                {
                    "source": f"pbm/{file_name}",
                    "duration_ms": spec.duration_ms,
                    "dirty": list(bbox),
                }
            )
        manifest_clips.append(
            {
                "name": clip_name,
                "loop_start": 1,
                "loop_end": len(manifest_frames),
                "frames": manifest_frames,
            }
        )

    if len(rendered) != 39:
        raise ValueError(f"expected exactly 39 v9 frames, rendered {len(rendered)}")
    manifest = {
        "schema": "companion.emote_asset_pack_manifest.v1",
        "name": "companion-v9-expression-candidate-200x200",
        "revision": 90,
        "priority": 0,
        "profile": {
            "width": 200,
            "height": 200,
            "stride_bytes": 25,
            "pixel_format": "mono_1bpp_white_is_one_msb",
        },
        "encoding": "packbits",
        "provenance": {
            "source": repo_rel(SOURCE),
            "source_sha256": EXPECTED_SHA256,
            "baseline_lock": "docs/art/iterations/companion-pet-expression-v9/baseline-lock.json",
            "runtime_resource_activated": False,
            "machine_only_candidate": True,
            "forbidden_inputs": ["legacy CEMP", "rejected art", "code-drawn face"],
        },
        "clips": manifest_clips,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    write_pose_review(pose_review_items)
    write_frame_review(rendered)
    report = {
        "schema": "companion.v9_expression_render.v1",
        "status": "PASS_MACHINE_RENDER_CANDIDATE_NOT_ACTIVATED",
        "source": repo_rel(SOURCE),
        "source_sha256": EXPECTED_SHA256,
        "profile": {"width": 200, "height": 200, "pixel_format": "mono_1bpp_white_is_one_msb"},
        "threshold": THRESHOLD,
        "pose_count": len(POSES),
        "frame_count": len(rendered),
        "manifest": repo_rel(MANIFEST),
        "pose_review": repo_rel(POSE_REVIEW),
        "frame_review": repo_rel(FRAME_REVIEW),
        "frames": rendered,
        "runtime_resource_activated": False,
        "external_flash_provisioned": False,
        "firmware_flashed": False,
        "physical_or_owner_visual_pass": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write PBM, manifest, report, and review images")
    args = parser.parse_args()
    if not args.write:
        print("PASS: renderer is source-locked; use --write to produce the machine-only candidate.")
        return 0
    report = render()
    print(
        "PASS: rendered v9 source to "
        f"{report['frame_count']}/39 PBM frames and a non-activated CEMP manifest."
    )
    print(f"REVIEW: {report['pose_review']}")
    print(f"FRAMES: {report['frame_review']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
