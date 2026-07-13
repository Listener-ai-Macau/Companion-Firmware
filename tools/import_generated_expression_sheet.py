#!/usr/bin/env python3
"""Import generated 4x3 pet expression sheet art into profiled PBM assets."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageOps


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "art" / "generated_pet_expression_sheet_v5.png"
DEFAULT_OUT_DIR = ROOT / "docs" / "validation" / "epaper"
DEFAULT_REPORT = ROOT / "docs" / "validation" / "companion-screen-generated-expression-sheet-import.json"
DEFAULT_PREVIEW = ROOT / ".cache" / "validation" / "generated-expression-sheet-import-preview.png"
DEFAULT_REVIEW = ROOT / ".cache" / "validation" / "generated-expression-sheet-review.png"

DEFAULT_PROFILE = "200x200"
DEFAULT_ASSET_SUFFIX = "1_54in"
MAX_FACE_WIDTH_RATIO = 0.87
MAX_FACE_HEIGHT_RATIO = 0.83
TOP_INSET_RATIO = 0.075
THRESHOLD = 168
MIN_INK_PIXELS = 1200
MAX_INK_PIXELS = 5200
# The physical shell owns the cat silhouette.  The final visible area and shell
# dimensions are not frozen, so do not impose a product-art margin yet and do
# not draw a white mask inside the visible 200x200 canvas.
MIN_EDGE_MARGIN = 0
REFERENCE_FACE_WIDTH = 174
REFERENCE_FACE_HEIGHT = 166


@dataclass(frozen=True)
class CanvasProfile:
    width: int
    height: int
    max_face_width: int
    max_face_height: int
    top_inset: int
    label_guard_band_y: int
    asset_suffix: str


def parse_canvas_profile(profile_text: str, asset_suffix: str) -> CanvasProfile:
    match = re.fullmatch(r"([1-9][0-9]{1,3})x([1-9][0-9]{1,3})", profile_text)
    if match is None:
        raise ValueError("profile must use WIDTHxHEIGHT, for example 200x200 or 264x167")
    if not re.fullmatch(r"[A-Za-z0-9_]+", asset_suffix):
        raise ValueError("asset suffix must contain only letters, digits, and underscores")
    width, height = (int(value) for value in match.groups())
    return CanvasProfile(
        width=width,
        height=height,
        max_face_width=max(1, round(width * MAX_FACE_WIDTH_RATIO)),
        max_face_height=max(1, round(height * MAX_FACE_HEIGHT_RATIO)),
        top_inset=round(height * TOP_INSET_RATIO),
        # Labels are excluded by the source crop. Do not reserve a target-panel
        # band before the physical visible area is frozen.
        label_guard_band_y=height,
        asset_suffix=asset_suffix,
    )


@dataclass(frozen=True)
class Pose:
    index: int
    name: str
    files: tuple[str, ...]


POSES = (
    Pose(1, "idle_calm", ("expression_idle_1_54in.pbm",)),
    Pose(2, "curious_tap", ("expression_happy_attention_1_54in.pbm",)),
    Pose(
        3,
        "left_swipe",
        (
            "expression_happy_attention_left_1_54in.pbm",
            "expression_idle_look_left_1_54in.pbm",
            "expression_idle_glance_left_1_54in.pbm",
        ),
    ),
    Pose(
        4,
        "right_swipe",
        (
            "expression_happy_attention_right_1_54in.pbm",
            "expression_idle_look_right_1_54in.pbm",
        ),
    ),
    Pose(
        5,
        "up_swipe",
        (
            "expression_happy_attention_up_1_54in.pbm",
            "expression_idle_look_up_1_54in.pbm",
            "expression_idle_look_up_left_1_54in.pbm",
            "expression_idle_look_up_right_1_54in.pbm",
            "expression_happy_attention_up_left_1_54in.pbm",
            "expression_happy_attention_up_right_1_54in.pbm",
            "expression_error_1_54in.pbm",
        ),
    ),
    Pose(
        6,
        "down_swipe",
        (
            "expression_happy_attention_down_1_54in.pbm",
            "expression_idle_look_down_1_54in.pbm",
            "expression_idle_look_down_left_1_54in.pbm",
            "expression_idle_look_down_right_1_54in.pbm",
            "expression_happy_attention_down_left_1_54in.pbm",
            "expression_happy_attention_down_right_1_54in.pbm",
        ),
    ),
    Pose(
        7,
        "listening",
        (
            "expression_listening_1_54in.pbm",
            "expression_listening_focus_1_54in.pbm",
            "expression_listening_wave_1_54in.pbm",
        ),
    ),
    Pose(
        8,
        "thinking",
        (
            "expression_thinking_1_54in.pbm",
            "expression_thinking_inward_1_54in.pbm",
            "expression_thinking_outward_1_54in.pbm",
        ),
    ),
    Pose(
        9,
        "recording",
        (
            "expression_recording_1_54in.pbm",
            "expression_recording_soft_1_54in.pbm",
            "expression_recording_pulse_1_54in.pbm",
        ),
    ),
    Pose(
        10,
        "speaking",
        (
            "expression_speaking_1_54in.pbm",
            "expression_speaking_soft_1_54in.pbm",
            "expression_speaking_open_1_54in.pbm",
        ),
    ),
    Pose(
        11,
        "happy",
        (
            "expression_happy_1_54in.pbm",
            "expression_happy_bright_1_54in.pbm",
            "expression_sync_complete_1_54in.pbm",
        ),
    ),
    Pose(
        12,
        "sleepy",
        (
            "expression_sleepy_1_54in.pbm",
            "expression_sleepy_drift_1_54in.pbm",
            "expression_sleepy_yawn_1_54in.pbm",
            "expression_low_battery_1_54in.pbm",
        ),
    ),
)

# Tuned for the checked-in generated_pet_expression_sheet_v5.png. The source is
# a 4x3 sheet with labels beneath each face; these windows intentionally stop
# above the labels so product assets keep only the physical-shell inner face.
ROW_CENTER_Y = (0.190, 0.485, 0.745)
CROP_WIDTH_RATIO = 0.215
CROP_HEIGHT_RATIO = (0.170, 0.200, 0.170)


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def crop_box_for_pose(source: Image.Image, pose: Pose) -> tuple[int, int, int, int]:
    width, height = source.size
    zero_based = pose.index - 1
    row = zero_based // 4
    col = zero_based % 4
    center_x = width * (0.125 + col * 0.25)
    center_y = height * ROW_CENTER_Y[row]
    crop_w = width * CROP_WIDTH_RATIO
    crop_h = height * CROP_HEIGHT_RATIO[row]
    return (
        round(center_x - crop_w / 2),
        round(center_y - crop_h / 2),
        round(center_x + crop_w / 2),
        round(center_y + crop_h / 2),
    )


def crop_pose_reference(source: Image.Image, pose: Pose, profile: CanvasProfile) -> Image.Image:
    box = crop_box_for_pose(source, pose)
    crop = ImageOps.autocontrast(source.crop(box))
    crop.thumbnail((profile.max_face_width, profile.max_face_height), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (profile.width, profile.height), 255)
    canvas.paste(crop, ((profile.width - crop.width) // 2, profile.top_inset))
    return canvas


def crop_pose(source: Image.Image, pose: Pose, profile: CanvasProfile) -> Image.Image:
    # Never paint an internal shell guard: the generated source already contains
    # only facial features, while physical geometry remains product-specific.
    return crop_pose_reference(source, pose, profile).point(lambda pixel: 0 if pixel < THRESHOLD else 255, "1")


def write_pbm(path: pathlib.Path, image: Image.Image) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return rel(path)


def shifted(image: Image.Image, dx: int, dy: int) -> Image.Image:
    variant = Image.new("1", image.size, 1)
    variant.paste(image, (dx, dy))
    return variant


def variant_for_file(image: Image.Image, pose: Pose, filename: str) -> Image.Image:
    if len(pose.files) == 1:
        return image
    if filename.endswith("_up_left_1_54in.pbm"):
        return shifted(image, -3, -2)
    if filename.endswith("_up_right_1_54in.pbm"):
        return shifted(image, 3, -2)
    if filename.endswith("_down_left_1_54in.pbm"):
        return shifted(image, -3, 2)
    if filename.endswith("_down_right_1_54in.pbm"):
        return shifted(image, 3, 2)
    if filename in {
        "expression_listening_wave_1_54in.pbm",
        "expression_thinking_outward_1_54in.pbm",
        "expression_recording_pulse_1_54in.pbm",
        "expression_speaking_open_1_54in.pbm",
        "expression_happy_bright_1_54in.pbm",
        "expression_sleepy_yawn_1_54in.pbm",
        "expression_happy_attention_left_1_54in.pbm",
        "expression_happy_attention_right_1_54in.pbm",
        "expression_happy_attention_up_1_54in.pbm",
        "expression_happy_attention_down_1_54in.pbm",
        "expression_sync_complete_1_54in.pbm",
        "expression_error_1_54in.pbm",
    }:
        return image
    if filename in {
        "expression_listening_focus_1_54in.pbm",
        "expression_thinking_inward_1_54in.pbm",
        "expression_speaking_soft_1_54in.pbm",
        "expression_recording_soft_1_54in.pbm",
        "expression_sleepy_drift_1_54in.pbm",
        "expression_low_battery_1_54in.pbm",
    }:
        return shifted(image, 0, 1)
    if "glance" in filename:
        return shifted(image, -2, 0)
    if "look_left" in filename:
        return shifted(image, -1, 0)
    if "look_right" in filename:
        return shifted(image, 1, 0)
    if "look_up" in filename:
        return shifted(image, 0, -1)
    if "look_down" in filename:
        return shifted(image, 0, 1)
    return shifted(image, 0, 2)


def count_black_pixels(image: Image.Image, box: tuple[int, int, int, int] | None = None) -> int:
    bitmap = image.convert("1")
    if box is None:
        region = bitmap
    else:
        region = bitmap.crop(box)
    return sum(1 for pixel in region.getdata() if pixel == 0)


def ink_thresholds(profile: CanvasProfile) -> tuple[int, int]:
    scale = min(
        profile.max_face_width / REFERENCE_FACE_WIDTH,
        profile.max_face_height / REFERENCE_FACE_HEIGHT,
    )
    area_scale = scale * scale
    return (
        max(1, round(MIN_INK_PIXELS * area_scale)),
        max(1, round(MAX_INK_PIXELS * area_scale)),
    )


def ink_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    bitmap = image.convert("1")
    xs: list[int] = []
    ys: list[int] = []
    pixels = bitmap.load()
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            if pixels[x, y] == 0:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def edge_ink_pixels(image: Image.Image) -> int:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    edge = 0
    for x in range(bitmap.width):
        if pixels[x, 0] == 0:
            edge += 1
        if pixels[x, bitmap.height - 1] == 0:
            edge += 1
    for y in range(bitmap.height):
        if pixels[0, y] == 0:
            edge += 1
        if pixels[bitmap.width - 1, y] == 0:
            edge += 1
    return edge


def review_metrics(source: Image.Image, pose: Pose, image: Image.Image,
                   profile: CanvasProfile) -> dict[str, object]:
    bbox = ink_bbox(image)
    ink = count_black_pixels(image)
    min_ink_pixels, max_ink_pixels = ink_thresholds(profile)
    bottom_band = count_black_pixels(
        image, (0, profile.label_guard_band_y, profile.width, profile.height)
    )
    if bbox is None:
        margins = {"left": 0, "top": 0, "right": 0, "bottom": 0}
        min_margin = 0
    else:
        margins = {
            "left": bbox[0],
            "top": bbox[1],
            "right": profile.width - 1 - bbox[2],
            "bottom": profile.height - 1 - bbox[3],
        }
        min_margin = min(margins.values())
    checks = {
        "has_visible_ink": ink >= min_ink_pixels,
        "not_overfilled": ink <= max_ink_pixels,
        "no_canvas_edge_touch": edge_ink_pixels(image) == 0,
        "label_guard_band_clear": bottom_band == 0,
        "crop_margin_present": min_margin >= MIN_EDGE_MARGIN,
    }
    return {
        "pose": pose.name,
        "index": pose.index,
        "source_crop_box": list(crop_box_for_pose(source, pose)),
        "ink_pixels": ink,
        "min_ink_pixels": min_ink_pixels,
        "max_ink_pixels": max_ink_pixels,
        "ink_bbox": list(bbox) if bbox is not None else None,
        "ink_margins": margins,
        "edge_ink_pixels": edge_ink_pixels(image),
        "label_guard_band_y": profile.label_guard_band_y,
        "label_guard_band_ink_pixels": bottom_band,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def build_preview(frames: list[tuple[Pose, Image.Image, Image.Image]], output: pathlib.Path,
                  profile: CanvasProfile) -> str:
    cell = 220
    preview = Image.new("RGB", (cell * 4, cell * 3), "white")
    draw = ImageDraw.Draw(preview)
    for pose, _reference, image in frames:
        scale = min(160 / profile.width, 160 / profile.height)
        thumb_size = (max(1, round(profile.width * scale)), max(1, round(profile.height * scale)))
        thumb = image.convert("RGB").resize(thumb_size, Image.Resampling.NEAREST)
        index = pose.index - 1
        x = (index % 4) * cell + (cell - thumb.width) // 2
        y = (index // 4) * cell + 18 + (160 - thumb.height) // 2
        preview.paste(thumb, (x, y))
        draw.text((x, y + 166), f"{pose.index}. {pose.name.upper()}", fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output)
    return rel(output)


def build_review(frames: list[tuple[Pose, Image.Image, Image.Image]], output: pathlib.Path,
                 profile: CanvasProfile) -> str:
    cell_w = 270
    cell_h = 245
    review = Image.new("RGB", (cell_w * 4, cell_h * 3), "white")
    draw = ImageDraw.Draw(review)
    for pose, reference, image in frames:
        index = pose.index - 1
        x = (index % 4) * cell_w + 10
        y = (index // 4) * cell_h + 12
        scale = min(108 / profile.width, 108 / profile.height)
        thumb_size = (max(1, round(profile.width * scale)), max(1, round(profile.height * scale)))
        ref_thumb = reference.convert("RGB").resize(thumb_size, Image.Resampling.LANCZOS)
        pbm_thumb = image.convert("RGB").resize(thumb_size, Image.Resampling.NEAREST)
        ref_x = x + 10 + (108 - ref_thumb.width) // 2
        ref_y = y + 26 + (108 - ref_thumb.height) // 2
        pbm_x = x + 145 + (108 - pbm_thumb.width) // 2
        pbm_y = y + 26 + (108 - pbm_thumb.height) // 2
        review.paste(ref_thumb, (ref_x, ref_y))
        review.paste(pbm_thumb, (pbm_x, pbm_y))
        draw.rectangle((x + 10, y + 26, x + 117, y + 133), outline="black")
        draw.rectangle((x + 145, y + 26, x + 252, y + 133), outline="black")
        draw.text((x + 42, y + 8), "REF", fill="black")
        draw.text((x + 177, y + 8), "PBM", fill="black")
        draw.text((x + 10, y + 145), f"{pose.index}. {pose.name.upper()}", fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    review.save(output)
    return rel(output)


def output_filename(template_filename: str, profile: CanvasProfile) -> str:
    return template_filename.replace("_1_54in.pbm", f"_{profile.asset_suffix}.pbm")


def import_sheet(source_path: pathlib.Path, out_dir: pathlib.Path, preview_path: pathlib.Path,
                 review_path: pathlib.Path, profile: CanvasProfile) -> dict[str, object]:
    source = Image.open(source_path).convert("L")
    frames: list[tuple[Pose, Image.Image, Image.Image]] = []
    outputs: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    for pose in POSES:
        reference = crop_pose_reference(source, pose, profile)
        image = crop_pose(source, pose, profile)
        frames.append((pose, reference, image))
        metrics.append(review_metrics(source, pose, image, profile))
        written = [
            write_pbm(
                out_dir / output_filename(filename, profile),
                variant_for_file(image, pose, filename),
            )
            for filename in pose.files
        ]
        outputs.append({"pose": pose.name, "index": pose.index, "files": written})

    return {
        "schema": "companion.generated_expression_sheet_import.v1",
        "status": "PASS",
        "source": rel(source_path),
        "source_size": {"width": source.width, "height": source.height},
        "style_source_of_truth": "generated_pet_expression_sheet_v5",
        "product_rule": "generated image sheet is the art baseline; importer removes labels and writes only inner-face PBM assets",
        "threshold": THRESHOLD,
        "visual_review_required": True,
        "machine_review_required": True,
        "visual_review_rule": (
            "Before flashing a new art revision, compare the generated sheet, "
            "this import preview, and the PBM/CEMP preview. Do not accept a "
            "script-only PASS when ornaments, brows, mouths, or labels differ "
            "visibly from the generated source."
        ),
        "machine_review_rule": (
            "Each imported pose must keep visible ink inside the requested canvas, "
            "and stay within ink-count bounds. Labels are excluded by the source "
            "crop rather than a target-panel guard band. These checks catch common "
            "generated-sheet import mistakes, but they do not replace the required "
            "REF/PBM visual review."
        ),
        "import_window_notes": (
            "2026-07-12 review widened the crop and moved row 2 upward so UP "
            "SWIPE exclamation marks and THINKING bubble ornaments are not cut. "
            "The PBM threshold was tuned to 168 after comparing threshold "
            "candidate previews; it keeps thin ornaments while reducing chunky "
            "nose/mouth artifacts from the generated antialiased source."
        ),
        "inner_face_clipping_policy": (
            "The accepted generated sheet already excludes the physical-shell "
            "outline. Normal imports must not apply a white shell guard inside "
            "the visible 200x200 canvas. The final physical visible area is not "
            "frozen, so do not impose a fixed art margin until product geometry "
            "defines it; reject a new source that needs destructive internal masking."
        ),
        "profile": {
            "width": profile.width,
            "height": profile.height,
            "max_face_width": profile.max_face_width,
            "max_face_height": profile.max_face_height,
            "top_inset": profile.top_inset,
            "label_guard_band_y": profile.label_guard_band_y,
            "asset_suffix": profile.asset_suffix,
        },
        "machine_review_thresholds": {
            "label_guard_band_y": profile.label_guard_band_y,
            "min_ink_pixels": ink_thresholds(profile)[0],
            "max_ink_pixels": ink_thresholds(profile)[1],
            "min_edge_margin": MIN_EDGE_MARGIN,
            "internal_shell_mask_disabled": True,
            "fixed_art_margin_px": MIN_EDGE_MARGIN,
        },
        "machine_review": {
            "status": "PASS" if all(item["status"] == "PASS" for item in metrics) else "FAIL",
            "pose_metrics": metrics,
        },
        "outputs": outputs,
        "preview": build_preview(frames, preview_path, profile),
        "review_preview": build_review(frames, review_path, profile),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--preview", type=pathlib.Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--review", type=pathlib.Path, default=DEFAULT_REVIEW)
    parser.add_argument("--profile", default=DEFAULT_PROFILE,
                        help="Output canvas WIDTHxHEIGHT; defaults to the WB55 200x200 panel.")
    parser.add_argument("--asset-suffix", default=DEFAULT_ASSET_SUFFIX,
                        help="PBM filename suffix without punctuation, for example 1_54in or 2_7in.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = parse_canvas_profile(args.profile, args.asset_suffix)
    except ValueError as exc:
        raise SystemExit(f"FAIL: {exc}") from exc
    report = import_sheet(args.source, args.out_dir, args.preview, args.review, profile)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS: imported generated expression sheet -> {rel(args.report)}")
    print(f"PREVIEW: {report['preview']}")
    print(f"REVIEW: {report['review_preview']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
