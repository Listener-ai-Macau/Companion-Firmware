#!/usr/bin/env python3
"""Audit V23 special-expression source art before any component extraction."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_DAILY = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
V9_DAILY_SHA256 = "B3847DF9CE2D20693C60C9CC7BC1EC8D8B8A3E23641F4521EE71508ABE13CB9E"
ITERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v23-core-special-expression-source"
LINEAGE = ITERATION / "source-lineage.json"
PREVIEW_DIR = ITERATION / "candidate/normalized-200x200-source-review"
REPORT = ROOT / "docs/validation/companion-v23-core-special-expression-source-gate-20260720.json"
CANVAS = (200, 200)
INK_THRESHOLD = 96
MAX_ANTIALIAS_FRACTION = 0.25
REQUIRED_POSES = ("menu_active", "recording_active", "charging_active")
TARGET_EYE_CENTERS = ((58.5, 134.5), (142.0, 134.5))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < INK_THRESHOLD else 255, mode="L")


def components(image: Image.Image) -> list[dict[str, object]]:
    pixels = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    found: list[dict[str, object]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] != 0:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                points.append((current_x, current_y))
                for near_x, near_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if (
                        0 <= near_x < width
                        and 0 <= near_y < height
                        and (near_x, near_y) not in seen
                        and pixels[near_x, near_y] == 0
                    ):
                        seen.add((near_x, near_y))
                        queue.append((near_x, near_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            found.append(
                {
                    "area": len(points),
                    "bbox": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                    "center": (sum(xs) / len(xs), sum(ys) / len(ys)),
                }
            )
    return sorted(found, key=lambda component: int(component["area"]), reverse=True)


def normalize_source(image: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    source = binary(image)
    parts = components(source)
    if len(parts) < 2:
        raise ValueError("source has fewer than two ink components")
    left_eye, right_eye = sorted(parts[:2], key=lambda component: float(component["center"][0]))
    left_center = left_eye["center"]
    right_center = right_eye["center"]
    left_box = left_eye["bbox"]
    right_box = right_eye["bbox"]
    eye_gap = float(right_center[0]) - float(left_center[0])
    eye_height = ((left_box[3] - left_box[1]) + (right_box[3] - right_box[1])) / 2
    if eye_gap <= 40 or eye_height <= 30:
        raise ValueError("source did not yield a plausible open-eye pair")
    scale_x = (TARGET_EYE_CENTERS[1][0] - TARGET_EYE_CENTERS[0][0]) / eye_gap
    scale_y = 45.0 / eye_height
    inverse = (
        1.0 / scale_x,
        0.0,
        float(left_center[0]) - TARGET_EYE_CENTERS[0][0] / scale_x,
        0.0,
        1.0 / scale_y,
        float(left_center[1]) - TARGET_EYE_CENTERS[0][1] / scale_y,
    )
    normalized = source.transform(CANVAS, Image.Transform.AFFINE, inverse, Image.Resampling.NEAREST, fillcolor=255)
    return normalized, {
        "source_left_eye_bbox": list(left_box),
        "source_right_eye_bbox": list(right_box),
        "source_left_eye_center": [round(float(left_center[0]), 3), round(float(left_center[1]), 3)],
        "source_right_eye_center": [round(float(right_center[0]), 3), round(float(right_center[1]), 3)],
        "source_eye_gap": round(eye_gap, 3),
        "source_average_eye_height": round(eye_height, 3),
        "normalization_scale": [round(scale_x, 6), round(scale_y, 6)],
    }


def black_pixel_count(image: Image.Image, box: tuple[int, int, int, int] | None = None) -> int:
    target = image.crop(box) if box else image
    return sum(value == 0 for value in target.convert("L").getdata())


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
        dots = [part for part in parts if float(part["center"][1]) < 75 and 12 <= int(part["area"]) <= 280]
        return {"mode": "top_thinking_dots", "detached_component_count": len(dots), "components": public}
    if pose == "recording_active":
        left = [part for part in parts if float(part["center"][0]) < 30 and 95 <= float(part["center"][1]) <= 160]
        right = [part for part in parts if float(part["center"][0]) > 170 and 95 <= float(part["center"][1]) <= 160]
        return {
            "mode": "symmetric_outer_listening_arcs",
            "left_detached_component_count": len(left),
            "right_detached_component_count": len(right),
            "components": public,
        }
    arcs = [part for part in parts if float(part["center"][1]) < 75 and int(part["area"]) >= 12]
    return {"mode": "top_breathing_arc", "detached_component_count": len(arcs), "components": public}


def save_source_preview_html() -> Path:
    html = """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>V23 Special Expression Source Review</title>
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
  <h1>V23 Special Expression Source Review</h1>
  <p>Locked V9 Daily appears first. The remaining panels are thresholded source normalizations for comparison only, not component exports, runtime frames, or a dynamic preview.</p>
  <section class=\"grid\">
    <article class=\"tile\"><h2>locked V9 daily</h2><img src=\"locked-v9-daily.png\" alt=\"Locked V9 daily\"></article>
    <article class=\"tile\"><h2>menu active candidate</h2><img src=\"menu-active-source-normalized.png\" alt=\"Menu active source candidate\"></article>
    <article class=\"tile\"><h2>recording active candidate</h2><img src=\"recording-active-source-normalized.png\" alt=\"Recording active source candidate\"></article>
    <article class=\"tile\"><h2>charging active candidate</h2><img src=\"charging-active-source-normalized.png\" alt=\"Charging active source candidate\"></article>
  </section>
  <p class=\"note\">The next permitted stage is component extraction using locked V9 eye identity. No V23 image is bound to behavior, CRIG, firmware, or panel output.</p>
</main>
</body>
</html>
"""
    path = PREVIEW_DIR / "v23-special-expression-source-review.html"
    path.write_text(html, encoding="ascii")
    return path


def main() -> int:
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    add(errors, V9_DAILY.is_file() and sha256(V9_DAILY) == V9_DAILY_SHA256, "locked V9 daily frame hash drifted")
    add(errors, LINEAGE.is_file(), "V23 source-lineage artifact is missing")
    lineage = load_json(LINEAGE) if LINEAGE.is_file() else {}
    add(errors, lineage.get("locked_reference", {}).get("sha256") == LOCKED_V9_SHA256, "V23 lineage lost locked V9 identity")
    policy = lineage.get("source_policy", {})
    add(errors, policy.get("runtime_resource_activated") is False, "V23 candidate must remain runtime inactive")
    add(errors, policy.get("active_candidate_binding") == "forbidden", "V23 candidate binding must remain forbidden")
    candidates = lineage.get("candidate_sources", [])
    add(errors, isinstance(candidates, list) and len(candidates) == len(REQUIRED_POSES), "V23 must archive exactly three core candidates")
    poses = tuple(candidate.get("pose") for candidate in candidates) if isinstance(candidates, list) else ()
    add(errors, poses == REQUIRED_POSES, "V23 core candidate order or pose set drifted")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    normalized_paths: dict[str, Path] = {}
    pose_reports: list[dict[str, object]] = []
    if V9_DAILY.is_file():
        with Image.open(V9_DAILY) as daily_raw:
            daily = daily_raw.convert("L")
        daily.save(PREVIEW_DIR / "locked-v9-daily.png")

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
                grayscale = list(source.getdata())
                nonwhite = [value for value in grayscale if value < 245]
                antialias_fraction = (
                    sum(16 <= value <= 239 for value in nonwhite) / len(nonwhite) if nonwhite else 1.0
                )
                add(pose_errors, antialias_fraction <= MAX_ANTIALIAS_FRACTION, f"{pose} has too much soft edge ink")
                source_binary = binary(source)
                source_bbox = ImageOps.invert(source_binary).getbbox()
                add(pose_errors, source_bbox is not None, f"{pose} has no threshold-safe ink")
                if source_bbox is not None:
                    left, top, right, bottom = source_bbox
                    add(pose_errors, left >= 30 and top >= 30 and right <= 1224 and bottom <= 1224, f"{pose} ink touches source edge")
                try:
                    normalized, eye_metrics = normalize_source(source)
                    filename = pose.replace("_", "-") + "-source-normalized.png"
                    preview_path = PREVIEW_DIR / filename
                    normalized.save(preview_path)
                    normalized_paths[pose] = preview_path
                    normalized_bbox = ImageOps.invert(normalized).getbbox()
                    add(pose_errors, normalized_bbox is not None, f"{pose} normalization produced no ink")
                    feature_zones = {
                        "brows": black_pixel_count(normalized, (30, 60, 170, 115)),
                        "mouth": black_pixel_count(normalized, (75, 150, 125, 195)),
                        "left_cheek": black_pixel_count(normalized, (15, 150, 75, 190)),
                        "right_cheek": black_pixel_count(normalized, (125, 150, 185, 190)),
                    }
                    add(pose_errors, feature_zones["brows"] >= 40, f"{pose} lacks an extractable brow pair")
                    add(pose_errors, feature_zones["mouth"] >= 16, f"{pose} lacks an extractable mouth signal")
                    accent = accent_metrics(pose, normalized)
                    if pose == "menu_active":
                        add(pose_errors, accent.get("detached_component_count") == 3, "menu_active needs exactly three detached thinking dots")
                    elif pose == "recording_active":
                        left_count = int(accent.get("left_detached_component_count", 0))
                        right_count = int(accent.get("right_detached_component_count", 0))
                        add(pose_errors, left_count >= 1 and left_count == right_count, "recording_active needs symmetric detached listening arcs")
                    elif pose == "charging_active":
                        add(pose_errors, accent.get("detached_component_count") == 2, "charging_active needs exactly two detached breathing-arc parts")
                    metrics = {
                        "source_size": list(source.size),
                        "source_ink_bbox": list(source_bbox) if source_bbox else None,
                        "anti_alias_fraction": antialias_fraction,
                        "normalization": eye_metrics,
                        "normalized_source_preview": rel(preview_path),
                        "normalized_ink_bbox": list(normalized_bbox) if normalized_bbox else None,
                        "feature_zone_ink_pixels": feature_zones,
                        "accent": accent,
                    }
                except ValueError as error:
                    pose_errors.append(f"{pose} normalization failed: {error}")
            errors.extend(pose_errors)
            pose_reports.append({"pose": pose, "errors": pose_errors, **metrics})

    preview_html = save_source_preview_html()
    contact_path = PREVIEW_DIR / "v23-special-expression-source-contact-sheet.png"
    if V9_DAILY.is_file() and len(normalized_paths) == len(REQUIRED_POSES):
        with Image.open(PREVIEW_DIR / "locked-v9-daily.png") as baseline:
            contact = Image.new("L", (800, 200), 255)
            contact.paste(baseline.convert("L"), (0, 0))
        for index, pose in enumerate(REQUIRED_POSES, start=1):
            with Image.open(normalized_paths[pose]) as preview:
                contact.paste(preview.convert("L"), (index * 200, 0))
        contact.save(contact_path)

    result = {
        "schema": "companion.v23_core_special_expression_source_gate.v1",
        "status": "PASS_V23_SPECIAL_SOURCE_GATE_PENDING_COMPONENT_EXPORT" if not errors else "FAIL_V23_SPECIAL_SOURCE_GATE",
        "generation_request": "docs/art/iterations/companion-pet-expression-v9-extension-v23-core-special-expression-source/generation-request-v3-coordinated-pose.json",
        "source_lineage": rel(LINEAGE),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "locked_v9_daily": rel(V9_DAILY),
        "locked_v9_daily_sha256": V9_DAILY_SHA256,
        "threshold": {"ink_value_lt": INK_THRESHOLD, "max_anti_alias_fraction": MAX_ANTIALIAS_FRACTION},
        "poses": pose_reports,
        "source_review_html": rel(preview_html),
        "source_review_contact_sheet": rel(contact_path) if contact_path.is_file() else None,
        "source_preview_contract": "thresholded generated-source normalization for comparison only; not a component export, target frame, dynamic preview, CRIG, runtime binding, or panel output",
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
    print("PASS: V23 core special sources retain locked V9 lineage and pass threshold-safe source inspection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
