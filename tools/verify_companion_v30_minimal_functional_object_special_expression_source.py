#!/usr/bin/env python3
"""Validate the V30 V9-only minimal object source panel before component export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from verify_companion_v23_special_expression_source import (
    LOCKED_V9_SHA256,
    TARGET_EYE_CENTERS,
    binary,
    normalize_source,
)


ROOT = Path(__file__).resolve().parents[1]
ITERATION = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v30-minimal-functional-object-special-expression-source"
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_DAILY = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
LINEAGE = ITERATION / "candidate/source-lineage.json"
PREVIEW_DIR = ITERATION / "candidate/normalized-200x200-source-review"
REPORT = ROOT / "docs/validation/companion-v30-minimal-functional-object-special-expression-source-gate-20260720.json"
CANVAS = (200, 200)
POSES = ("menu_active", "recording_active", "charging_active")
FACE_BOXES = {
    "left_brow": (18, 62, 96, 110),
    "right_brow": (104, 62, 182, 110),
    "left_eye": (25, 95, 94, 155),
    "right_eye": (106, 95, 175, 155),
    "nose": (82, 135, 118, 160),
    "left_cheek": (8, 145, 76, 185),
    "right_cheek": (124, 145, 192, 185),
    "mouth": (72, 150, 128, 190),
}
FACE_PRIMARY_BOXES = (FACE_BOXES["left_brow"], FACE_BOXES["right_brow"], FACE_BOXES["left_cheek"], FACE_BOXES["right_cheek"], FACE_BOXES["mouth"])
POSE_OBJECT_BOXES = {
    "menu_active": {
        "left_tab": (60, 55, 84, 73),
        "center_tab": (87, 55, 114, 73),
        "right_tab": (115, 55, 142, 73),
    },
    "recording_active": {
        "left_ear_cuff": (6, 108, 38, 164),
        "right_ear_cuff": (162, 108, 194, 164),
        "pickup_point": (118, 156, 130, 170),
    },
    "charging_active": {
        "charge_clasp": (8, 151, 36, 171),
        "short_tether": (8, 118, 36, 153),
        "energy_core": (85, 34, 116, 66),
    },
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


def ink_count(image: Image.Image, box: tuple[int, int, int, int]) -> int:
    return sum(value == 0 for value in image.crop(box).convert("L").getdata())


def face_primary_difference(left: Image.Image, right: Image.Image) -> int:
    difference = Image.new("L", CANVAS, 255)
    for box in FACE_PRIMARY_BOXES:
        difference.paste(ImageChops.difference(left.crop(box), right.crop(box)), box)
    return sum(value != 0 for value in difference.getdata())


def outside_face_ink(image: Image.Image, object_boxes: tuple[tuple[int, int, int, int], ...]) -> int:
    allowed = Image.new("1", CANVAS, 0)
    for box in FACE_BOXES.values():
        allowed.paste(1, box)
    for box in object_boxes:
        allowed.paste(1, box)
    source = image.convert("1")
    count = 0
    for y in range(CANVAS[1]):
        for x in range(CANVAS[0]):
            if source.getpixel((x, y)) == 0 and allowed.getpixel((x, y)) == 0:
                count += 1
    return count


def write_review_html() -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    html = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>V30 Minimal Object Source Review</title>
<style>body{margin:0;background:#f4f4f1;color:#111;font-family:Arial,sans-serif}main{width:min(1120px,calc(100% - 32px));margin:28px auto}h1{font-size:28px;letter-spacing:0}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.tile h2{font-size:15px;letter-spacing:0}.tile img{width:100%;aspect-ratio:1;display:block;image-rendering:pixelated;background:#fff;border:1px solid #111}@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style></head>
<body><main><h1>V30 Minimal Object Source Review</h1><section class=\"grid\"><article class=\"tile\"><h2>locked V9 daily</h2><img src=\"locked-v9-daily.png\"></article><article class=\"tile\"><h2>menu active</h2><img src=\"menu-active-source-normalized.png\"></article><article class=\"tile\"><h2>recording active</h2><img src=\"recording-active-source-normalized.png\"></article><article class=\"tile\"><h2>charging active</h2><img src=\"charging-active-source-normalized.png\"></article></section></main></body></html>
"""
    path = PREVIEW_DIR / "source-review.html"
    path.write_text(html, encoding="ascii")
    return path


def main() -> int:
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    add(errors, LINEAGE.is_file(), "V30 source-lineage artifact is missing")
    lineage = load_json(LINEAGE) if LINEAGE.is_file() else {}
    add(errors, lineage.get("locked_reference", {}).get("sha256") == LOCKED_V9_SHA256, "V30 lineage lost locked V9 identity")
    add(errors, lineage.get("allowed_reference_inputs") == ["locked_v9_reference_only"], "V30 accepts an unapproved visual reference")
    policy = lineage.get("source_policy", {})
    add(errors, policy.get("runtime_resource_activated") is False, "V30 candidate must remain runtime inactive")
    add(errors, policy.get("active_candidate_binding") == "forbidden", "V30 candidate binding must remain forbidden")

    panel = lineage.get("source_panel", {}) if isinstance(lineage, dict) else {}
    panel_path = ROOT / str(panel.get("path", ""))
    expected_hash = str(panel.get("sha256", ""))
    crop_columns = panel.get("crop_columns", [])
    pose_order = tuple(panel.get("pose_order", []))
    add(errors, panel_path.is_file(), "V30 source panel is missing")
    add(errors, pose_order == POSES, "V30 source panel pose order drifted")
    add(errors, isinstance(crop_columns, list) and len(crop_columns) == len(POSES), "V30 source panel crop metadata is invalid")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    normalized_by_pose: dict[str, Image.Image] = {}
    pose_reports: list[dict[str, object]] = []
    if V9_DAILY.is_file():
        with Image.open(V9_DAILY) as raw:
            daily = raw.convert("L")
        daily.save(PREVIEW_DIR / "locked-v9-daily.png")
    else:
        daily = Image.new("L", CANVAS, 255)
    v9_eye_ink_pixels = {
        "left_eye": ink_count(daily, FACE_BOXES["left_eye"]),
        "right_eye": ink_count(daily, FACE_BOXES["right_eye"]),
    }
    object_part_ink_limit = min(v9_eye_ink_pixels.values()) // 2

    if panel_path.is_file():
        add(errors, sha256(panel_path) == expected_hash, "V30 source panel hash drifted")
        with Image.open(panel_path) as raw:
            panel_image = raw.convert("L")
        add(errors, list(panel_image.size) == panel.get("size"), "V30 source panel size drifted")
        for pose, box_raw in zip(POSES, crop_columns):
            pose_errors: list[str] = []
            try:
                box = tuple(int(value) for value in box_raw)
                add(pose_errors, len(box) == 4, f"{pose} crop has invalid dimensions")
                crop = panel_image.crop(box)
                normalized, eye_metrics = normalize_source(crop)
                normalized = binary(normalized)
                normalized_path = PREVIEW_DIR / f"{pose.replace('_', '-')}-source-normalized.png"
                normalized.save(normalized_path)
                normalized_by_pose[pose] = normalized
                component_ink = {name: ink_count(normalized, region) for name, region in FACE_BOXES.items()}
                object_ink = {name: ink_count(normalized, region) for name, region in POSE_OBJECT_BOXES[pose].items()}
                add(pose_errors, component_ink["left_brow"] >= 25 and component_ink["right_brow"] >= 25, f"{pose} lacks extractable brows")
                add(pose_errors, component_ink["mouth"] >= 10, f"{pose} lacks an extractable mouth")
                add(pose_errors, component_ink["left_cheek"] >= 8 and component_ink["right_cheek"] >= 8, f"{pose} lacks balanced cheeks")
                add(pose_errors, len(object_ink) == 3 and all(count >= 8 for count in object_ink.values()), f"{pose} lacks three extractable state-object parts")
                add(pose_errors, all(count <= object_part_ink_limit for count in object_ink.values()), f"{pose} contains an object part larger than half a locked V9 eye")
                outside = outside_face_ink(normalized, tuple(POSE_OBJECT_BOXES[pose].values()))
                add(pose_errors, outside == 0, f"{pose} contains forbidden outside-face ink ({outside} pixels)")
                delta_daily = face_primary_difference(normalized, daily)
                add(pose_errors, delta_daily >= 70, f"{pose} face-primary pose is too close to V9 Daily")
                pose_reports.append({
                    "pose": pose,
                    "crop": list(box),
                    "normalization": eye_metrics,
                    "normalized_source_preview": rel(normalized_path),
                    "component_ink_pixels": component_ink,
                    "state_object_ink_pixels": object_ink,
                    "object_part_ink_limit": object_part_ink_limit,
                    "outside_face_ink_pixels": outside,
                    "face_primary_delta_from_v9_daily": delta_daily,
                    "errors": pose_errors,
                })
            except (TypeError, ValueError) as error:
                pose_errors.append(f"{pose} normalization failed: {error}")
                pose_reports.append({"pose": pose, "errors": pose_errors})
            errors.extend(pose_errors)

    pairwise: list[dict[str, object]] = []
    for index, left_pose in enumerate(POSES):
        for right_pose in POSES[index + 1:]:
            if left_pose not in normalized_by_pose or right_pose not in normalized_by_pose:
                continue
            difference = face_primary_difference(normalized_by_pose[left_pose], normalized_by_pose[right_pose])
            add(errors, difference >= 45, f"{left_pose} and {right_pose} face-primary poses are too similar")
            pairwise.append({"left": left_pose, "right": right_pose, "face_primary_pixel_difference": difference})

    review_html = write_review_html()
    contact_path = PREVIEW_DIR / "source-contact-sheet.png"
    if len(normalized_by_pose) == len(POSES):
        contact = Image.new("L", (800, 200), 255)
        contact.paste(daily, (0, 0))
        for index, pose in enumerate(POSES, start=1):
            contact.paste(normalized_by_pose[pose], (index * 200, 0))
        contact.save(contact_path)

    report = {
        "schema": "companion.v30_minimal_functional_object_special_expression_source_gate.v1",
        "status": "PASS_V30_MINIMAL_FUNCTIONAL_OBJECT_SOURCE_GATE_PENDING_COMPONENT_EXPORT" if not errors else "FAIL_V30_MINIMAL_FUNCTIONAL_OBJECT_SOURCE_GATE",
        "generation_request": rel(ITERATION / "generation-request-v1-minimal-functional-object-panel.json"),
        "generation_prompt": rel(ITERATION / "generation-prompt-v1-minimal-functional-object-panel.md"),
        "source_lineage": rel(LINEAGE),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "locked_v9_eye_ink_pixels": v9_eye_ink_pixels,
        "object_part_ink_limit": object_part_ink_limit,
        "target_eye_centers": [list(center) for center in TARGET_EYE_CENTERS],
        "poses": pose_reports,
        "pairwise_face_primary_differences": pairwise,
        "source_review_html": rel(review_html),
        "source_review_contact_sheet": rel(contact_path) if contact_path.is_file() else None,
        "source_preview_contract": "thresholded native 200x200 source normalization for static provenance comparison only; not a runtime frame, component export, target output or animation",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V30 minimal functional-object panel retains locked V9 lineage and passes static component-source inspection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
