#!/usr/bin/env python3
"""Audit V24 glance-readable special-expression sources before component export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from verify_companion_v23_special_expression_source import (
    INK_THRESHOLD,
    LOCKED_V9_SHA256,
    TARGET_EYE_CENTERS,
    binary,
    black_pixel_count,
    components,
    normalize_source,
)


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_DAILY = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
V9_DAILY_SHA256 = "B3847DF9CE2D20693C60C9CC7BC1EC8D8B8A3E23641F4521EE71508ABE13CB9E"
ITERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v24-glance-readable-special-expression-source"
LINEAGE = ITERATION / "source-lineage.json"
PREVIEW_DIR = ITERATION / "candidate/normalized-200x200-source-review"
REPORT = ROOT / "docs/validation/companion-v24-glance-readable-special-expression-source-gate-20260720.json"
CANVAS = (200, 200)
MAX_ANTIALIAS_FRACTION = 0.25
REQUIRED_POSES = ("menu_active", "recording_active", "charging_active")
FACE_PRIMARY_ZONES = {
    "brows": (30, 60, 170, 115),
    "mouth": (70, 150, 130, 195),
    "left_cheek": (15, 150, 75, 195),
    "right_cheek": (125, 150, 185, 195),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def pixel_count(image: Image.Image, box: tuple[int, int, int, int]) -> int:
    return sum(value == 0 for value in image.crop(box).convert("L").getdata())


def face_primary_mask(image: Image.Image) -> Image.Image:
    mask = Image.new("L", CANVAS, 255)
    for box in FACE_PRIMARY_ZONES.values():
        mask.paste(image.crop(box).convert("L"), box)
    return mask


def face_primary_difference(left: Image.Image, right: Image.Image) -> int:
    difference = ImageChops.difference(face_primary_mask(left), face_primary_mask(right))
    return sum(value != 0 for value in difference.getdata())


def accent_metrics(pose: str, normalized: Image.Image) -> dict[str, object]:
    parts = components(normalized)
    public = [
        {
            "area": int(part["area"]),
            "bbox": list(part["bbox"]),
            "center": [round(float(part["center"][0]), 3), round(float(part["center"][1]), 3)],
        }
        for part in parts
    ]
    if pose == "menu_active":
        dots = [part for part in parts if float(part["center"][1]) < 75 and 12 <= int(part["area"]) <= 420]
        return {"mode": "three_step_dots", "detached_component_count": len(dots), "components": public}
    if pose == "recording_active":
        left = [part for part in parts if float(part["center"][0]) < 30 and 90 <= float(part["center"][1]) <= 165]
        right = [part for part in parts if float(part["center"][0]) > 170 and 90 <= float(part["center"][1]) <= 165]
        return {
            "mode": "paired_nested_listening_arcs",
            "left_detached_component_count": len(left),
            "right_detached_component_count": len(right),
            "components": public,
        }
    arcs = [part for part in parts if float(part["center"][1]) < 75 and int(part["area"]) >= 12]
    return {"mode": "two_simple_breathing_arcs", "detached_component_count": len(arcs), "components": public}


def source_review_html() -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V24 Glance-Readable Special Expression Source Review</title>
<style>
body { margin: 0; background: #f4f4f1; color: #111; font-family: Arial, sans-serif; }
main { width: min(1120px, calc(100% - 32px)); margin: 28px auto; }
h1 { margin: 0 0 8px; font-size: 28px; font-weight: 700; letter-spacing: 0; }
p { margin: 0 0 22px; font-size: 15px; line-height: 1.45; }
.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.tile { min-width: 0; }
.tile h2 { margin: 0 0 8px; font-size: 15px; font-weight: 700; letter-spacing: 0; }
.tile img { width: 100%; aspect-ratio: 1; display: block; image-rendering: pixelated; background: #fff; border: 1px solid #111; }
.note { margin-top: 22px; padding-top: 14px; border-top: 1px solid #aaa; color: #444; }
@media (max-width: 760px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
</head>
<body>
<main>
  <h1>V24 Glance-Readable Special Expression Source Review</h1>
  <p>These are thresholded native 200x200 source normalizations. They test static face-primary distinction before component export; they are not runtime frames or animation.</p>
  <section class="grid">
    <article class="tile"><h2>locked V9 daily</h2><img src="locked-v9-daily.png" alt="Locked V9 daily"></article>
    <article class="tile"><h2>menu active</h2><img src="menu-active-source-normalized.png" alt="Menu active source"></article>
    <article class="tile"><h2>recording active</h2><img src="recording-active-source-normalized.png" alt="Recording active source"></article>
    <article class="tile"><h2>charging active</h2><img src="charging-active-source-normalized.png" alt="Charging active source"></article>
  </section>
  <p class="note">V24 remains source art only. Machine pass cannot substitute for the subsequent canonical owner at-a-glance art review.</p>
</main>
</body>
</html>
"""
    path = PREVIEW_DIR / "source-review.html"
    path.write_text(html, encoding="ascii")
    return path


def main() -> int:
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    add(errors, V9_DAILY.is_file() and sha256(V9_DAILY) == V9_DAILY_SHA256, "locked V9 daily frame hash drifted")
    add(errors, LINEAGE.is_file(), "V24 source-lineage artifact is missing")
    lineage = load_json(LINEAGE) if LINEAGE.is_file() else {}
    add(errors, lineage.get("locked_reference", {}).get("sha256") == LOCKED_V9_SHA256, "V24 lineage lost locked V9 identity")
    add(errors, lineage.get("allowed_reference_inputs") == ["locked_v9_reference_only"], "V24 accepts an unapproved visual reference")
    policy = lineage.get("source_policy", {})
    add(errors, policy.get("runtime_resource_activated") is False, "V24 candidate must remain runtime inactive")
    add(errors, policy.get("active_candidate_binding") == "forbidden", "V24 candidate binding must remain forbidden")
    candidates = lineage.get("candidate_sources", [])
    add(errors, isinstance(candidates, list) and len(candidates) == len(REQUIRED_POSES), "V24 must archive exactly three candidates")
    poses = tuple(candidate.get("pose") for candidate in candidates) if isinstance(candidates, list) else ()
    add(errors, poses == REQUIRED_POSES, "V24 candidate order or pose set drifted")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    normalized_by_pose: dict[str, Image.Image] = {}
    pose_reports: list[dict[str, object]] = []
    if V9_DAILY.is_file():
        with Image.open(V9_DAILY) as raw:
            daily = raw.convert("L")
        daily.save(PREVIEW_DIR / "locked-v9-daily.png")
    else:
        daily = Image.new("L", CANVAS, 255)

    if isinstance(candidates, list):
        for candidate in candidates:
            pose = str(candidate.get("pose", ""))
            source_path = ITERATION / str(candidate.get("generated_image", ""))
            expected_hash = str(candidate.get("generated_image_sha256", ""))
            pose_errors: list[str] = []
            add(pose_errors, source_path.is_file(), f"{pose} generated image is missing")
            metrics: dict[str, object] = {}
            if source_path.is_file():
                add(pose_errors, sha256(source_path) == expected_hash, f"{pose} generated image hash drifted")
                with Image.open(source_path) as raw:
                    source = raw.convert("L")
                add(pose_errors, source.size == (1254, 1254), f"{pose} source must remain 1254x1254")
                nonwhite = [value for value in source.getdata() if value < 245]
                anti_alias_fraction = sum(16 <= value <= 239 for value in nonwhite) / len(nonwhite) if nonwhite else 1.0
                add(pose_errors, anti_alias_fraction <= MAX_ANTIALIAS_FRACTION, f"{pose} has too much soft edge ink")
                source_binary = binary(source)
                source_bbox = ImageOps.invert(source_binary).getbbox()
                add(pose_errors, source_bbox is not None, f"{pose} has no threshold-safe ink")
                if source_bbox is not None:
                    left, top, right, bottom = source_bbox
                    add(pose_errors, left >= 30 and top >= 30 and right <= 1224 and bottom <= 1224, f"{pose} ink touches source edge")
                try:
                    normalized, eye_metrics = normalize_source(source)
                    preview_path = PREVIEW_DIR / (pose.replace("_", "-") + "-source-normalized.png")
                    normalized.save(preview_path)
                    normalized_by_pose[pose] = normalized
                    zones = {name: pixel_count(normalized, box) for name, box in FACE_PRIMARY_ZONES.items()}
                    add(pose_errors, zones["brows"] >= 40, f"{pose} lacks extractable brows")
                    add(pose_errors, zones["mouth"] >= 16, f"{pose} lacks an extractable mouth")
                    add(pose_errors, zones["left_cheek"] >= 12 and zones["right_cheek"] >= 12, f"{pose} lacks balanced cheek source marks")
                    face_delta_from_daily = face_primary_difference(normalized, daily)
                    add(pose_errors, face_delta_from_daily >= 90, f"{pose} face-primary signal is too close to V9 Daily")
                    accent = accent_metrics(pose, normalized)
                    if pose == "menu_active":
                        add(pose_errors, accent.get("detached_component_count") == 3, "menu_active needs exactly three detached step dots")
                    elif pose == "recording_active":
                        left_count = int(accent.get("left_detached_component_count", 0))
                        right_count = int(accent.get("right_detached_component_count", 0))
                        add(pose_errors, left_count == 2 and right_count == 2, "recording_active needs two detached listening arcs on each side")
                    elif pose == "charging_active":
                        add(pose_errors, accent.get("detached_component_count") == 2, "charging_active needs exactly two detached breathing arcs")
                    metrics = {
                        "source_size": list(source.size),
                        "source_ink_bbox": list(source_bbox) if source_bbox else None,
                        "anti_alias_fraction": round(anti_alias_fraction, 6),
                        "normalization": eye_metrics,
                        "normalized_source_preview": rel(preview_path),
                        "face_primary_zone_ink_pixels": zones,
                        "face_primary_delta_from_v9_daily": face_delta_from_daily,
                        "accent": accent,
                    }
                except ValueError as error:
                    pose_errors.append(f"{pose} normalization failed: {error}")
            errors.extend(pose_errors)
            pose_reports.append({"pose": pose, "errors": pose_errors, **metrics})

    pairwise: list[dict[str, object]] = []
    for index, left_pose in enumerate(REQUIRED_POSES):
        for right_pose in REQUIRED_POSES[index + 1 :]:
            if left_pose not in normalized_by_pose or right_pose not in normalized_by_pose:
                continue
            difference = face_primary_difference(normalized_by_pose[left_pose], normalized_by_pose[right_pose])
            add(errors, difference >= 70, f"{left_pose} and {right_pose} face-primary signals are too similar")
            pairwise.append({"left": left_pose, "right": right_pose, "face_primary_pixel_difference": difference})

    review_html = source_review_html()
    contact_path = PREVIEW_DIR / "source-contact-sheet.png"
    if len(normalized_by_pose) == len(REQUIRED_POSES):
        contact = Image.new("L", (800, 200), 255)
        contact.paste(daily, (0, 0))
        for index, pose in enumerate(REQUIRED_POSES, start=1):
            contact.paste(normalized_by_pose[pose], (index * 200, 0))
        contact.save(contact_path)

    result = {
        "schema": "companion.v24_glance_readable_special_expression_source_gate.v1",
        "status": "PASS_V24_SPECIAL_SOURCE_GATE_PENDING_COMPONENT_EXPORT" if not errors else "FAIL_V24_SPECIAL_SOURCE_GATE",
        "generation_request": "docs/art/iterations/companion-pet-expression-v9-extension-v24-glance-readable-special-expression-source/generation-request-v1-glance-readable.json",
        "source_lineage": rel(LINEAGE),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "locked_v9_daily": rel(V9_DAILY),
        "locked_v9_daily_sha256": V9_DAILY_SHA256,
        "target_eye_centers": [list(center) for center in TARGET_EYE_CENTERS],
        "threshold": {
            "ink_value_lt": INK_THRESHOLD,
            "max_anti_alias_fraction": MAX_ANTIALIAS_FRACTION,
            "minimum_face_primary_delta_from_daily": 90,
            "minimum_pairwise_face_primary_delta": 70
        },
        "poses": pose_reports,
        "pairwise_face_primary_differences": pairwise,
        "source_review_html": rel(review_html),
        "source_review_contact_sheet": rel(contact_path) if contact_path.is_file() else None,
        "source_preview_contract": "thresholded generated-source normalization at native 200x200 for static comparison only; not a component export, target frame, dynamic preview, CRIG, runtime binding or panel output",
        "component_export": "required_before_owner_art_review",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V24 glance-readable special sources retain locked V9 lineage and pass static face-primary inspection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
