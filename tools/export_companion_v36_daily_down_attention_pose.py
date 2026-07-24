#!/usr/bin/env python3
"""Gate and export V36 Daily-down source art as V9 component masks only."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import deque

from PIL import Image

from render_companion_v9_expression_rig import enclosed_white_island_masks


ROOT = pathlib.Path(__file__).resolve().parents[1]
V36_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v36-directional-eye-gaze-source"
ATTEMPT = V36_ROOT / "candidate/attempt-06-generated-cute-down-attention.json"
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_IDLE = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
CANVAS = (200, 200)
EYE_SPECS = {
    "left": {"box": (42, 112, 75, 157), "center": (58.0, 134.0), "body": "left_eye_open.pbm",
             "default_primary": "left_eye_highlight_open.pbm", "default_sparkle": "left_eye_sparkle_open.pbm"},
    "right": {"box": (125, 112, 159, 157), "center": (142.0, 134.0), "body": "right_eye_open.pbm",
              "default_primary": "right_eye_highlight_open.pbm", "default_sparkle": "right_eye_sparkle_open.pbm"},
}
BROW_SPECS = {
    "left": {"box": (38, 76, 80, 106), "default": "left_brow_open.pbm", "base": (47, 85)},
    "right": {"box": (120, 76, 162, 106), "default": "right_brow_open.pbm", "base": (132, 85)},
}
MOUTH_BOX = (80, 150, 120, 174)
MOUTH_BASE = (86, 160)
STATIC_BLACK_COMPONENTS = (
    ("left_cheek_default.pbm", (33, 160)),
    ("right_cheek_default.pbm", (154, 160)),
    ("nose_default.pbm", (94, 148)),
    ("charm_star.pbm", (96, 31)),
)
MIN_HOLD_PIXEL_DIFFERENCE = 300
MIN_PRIMARY_DOWN_DELTA_PX = 0.50
MIN_BROW_LOWER_DELTA_PX = 3.00


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < 160 else 255, mode="1")


def component_ink_mask(mask: Image.Image) -> Image.Image:
    return mask.convert("1").point(lambda value: 255 if value == 0 else 0)


def black_components(image: Image.Image) -> list[dict[str, object]]:
    pixels = image.convert("1").load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, object]] = []
    for y in range(round(height * 0.25), round(height * 0.90)):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] != 0:
                continue
            pending: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while pending:
                point_x, point_y = pending.popleft()
                points.append((point_x, point_y))
                for delta_x, delta_y in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                                         (0, 1), (1, -1), (1, 0), (1, 1)):
                    next_x, next_y = point_x + delta_x, point_y + delta_y
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    if (next_x, next_y) in seen or pixels[next_x, next_y] != 0:
                        continue
                    seen.add((next_x, next_y))
                    pending.append((next_x, next_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            result.append({
                "area": len(points),
                "box": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
            })
    return sorted(result, key=lambda item: int(item["area"]), reverse=True)


def eye_candidates(image: Image.Image) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for component in black_components(image):
        left, top, right, bottom = component["box"]
        width, height = right - left, bottom - top
        if width >= 16 and height >= 20 and 70 <= top <= 125 and int(component["area"]) >= 180:
            candidates.append(component)
    candidates.sort(key=lambda item: tuple(item["box"])[0])
    require(len(candidates) == 2, f"expected exactly two generated source eyes, found {len(candidates)}")
    return candidates


def center(component: dict[str, object]) -> tuple[float, float]:
    left, top, right, bottom = tuple(component["box"])
    return (left + right - 1) / 2.0, (top + bottom - 1) / 2.0


def normalize_source(source: Image.Image) -> tuple[Image.Image, dict[str, float | list[float]]]:
    initial = binary(source.resize(CANVAS, Image.Resampling.LANCZOS))
    left_eye, right_eye = eye_candidates(initial)
    left_center = center(left_eye)
    right_center = center(right_eye)
    source_distance = right_center[0] - left_center[0]
    require(source_distance > 0, "generated source eye centers are not ordered")
    target_distance = EYE_SPECS["right"]["center"][0] - EYE_SPECS["left"]["center"][0]
    scale_x = target_distance / source_distance
    source_eye_height = ((tuple(left_eye["box"])[3] - tuple(left_eye["box"])[1]) +
                         (tuple(right_eye["box"])[3] - tuple(right_eye["box"])[1])) / 2.0
    scale_y = 45.0 / source_eye_height
    translate_x = EYE_SPECS["left"]["center"][0] - left_center[0] * scale_x
    translate_y = EYE_SPECS["left"]["center"][1] - left_center[1] * scale_y
    inverse = (1.0 / scale_x, 0.0, -translate_x / scale_x, 0.0, 1.0 / scale_y, -translate_y / scale_y)
    normalized = initial.transform(CANVAS, Image.Transform.AFFINE, inverse, resample=Image.Resampling.NEAREST)
    return normalized, {
        "source_eye_boxes_200": [list(tuple(left_eye["box"])), list(tuple(right_eye["box"]))],
        "scale_x": round(scale_x, 6),
        "scale_y": round(scale_y, 6),
        "translate_x": round(translate_x, 6),
        "translate_y": round(translate_y, 6),
    }


def points(mask: Image.Image) -> list[tuple[int, int]]:
    return [(x, y) for y in range(mask.height) for x in range(mask.width) if mask.getpixel((x, y)) == 0]


def mask_metrics(mask: Image.Image) -> dict[str, object]:
    ink = points(mask)
    require(bool(ink), "component mask is empty")
    xs = [point[0] for point in ink]
    ys = [point[1] for point in ink]
    return {
        "pixels": len(ink),
        "bbox": [min(xs), min(ys), max(xs) + 1, max(ys) + 1],
        "center": [round(sum(xs) / len(ink), 3), round(sum(ys) / len(ink), 3)],
    }


def reflection_masks(normalized: Image.Image, eye: str) -> tuple[Image.Image, Image.Image, dict[str, object]]:
    spec = EYE_SPECS[eye]
    crop = normalized.crop(tuple(spec["box"]))
    islands = enclosed_white_island_masks(crop)
    require(len(islands) >= 2, f"{eye}: generated eye needs a primary oval and companion sparkle")
    primary, sparkle = islands[0], islands[1]
    body = binary(Image.open(COMPONENTS / str(spec["body"])))
    for label, mask in (("primary", primary), ("sparkle", sparkle)):
        mask_points = points(mask)
        require(mask_points, f"{eye}: {label} is empty")
        require(all(body.getpixel(point) == 0 for point in mask_points),
                f"{eye}: {label} escapes the locked V9 black eye body")
        metrics = mask_metrics(mask)
        left, top, right, bottom = metrics["bbox"]
        require(0 < left < right < crop.width and 0 < top < bottom < crop.height,
                f"{eye}: {label} touches the eye crop edge")
    primary_metrics = mask_metrics(primary)
    sparkle_metrics = mask_metrics(sparkle)
    require(int(primary_metrics["pixels"]) > int(sparkle_metrics["pixels"]) * 2,
            f"{eye}: primary reflection is not dominant over sparkle")
    primary_left, primary_top, primary_right, primary_bottom = primary_metrics["bbox"]
    require((primary_bottom - primary_top) > (primary_right - primary_left),
            f"{eye}: primary reflection is not vertically soft/elongated")
    return primary, sparkle, {"primary": primary_metrics, "sparkle": sparkle_metrics}


def raw_black_component(normalized: Image.Image, box: tuple[int, int, int, int], label: str) -> Image.Image:
    crop = normalized.crop(box).convert("1")
    require(bool(points(crop)), f"{label}: generated source component is empty")
    return crop


def paste_ink(canvas: Image.Image, component: Image.Image, position: tuple[int, int]) -> None:
    canvas.paste(0, position, component_ink_mask(component))


def paste_erase(canvas: Image.Image, component: Image.Image, position: tuple[int, int]) -> None:
    canvas.paste(255, position, component_ink_mask(component))


def load_component(name: str) -> Image.Image:
    return Image.open(COMPONENTS / name).convert("1")


def compose(reflections: dict[str, tuple[Image.Image, Image.Image]], brows: dict[str, Image.Image],
            mouth: Image.Image, use_generated_reflections: bool, use_generated_brows: bool,
            use_generated_mouth: bool) -> Image.Image:
    canvas = Image.new("1", CANVAS, 255)
    for eye, spec in EYE_SPECS.items():
        box = tuple(spec["box"])
        paste_ink(canvas, load_component(str(spec["body"])), box[:2])
        primary, sparkle = reflections[eye] if use_generated_reflections else (
            load_component(str(spec["default_primary"])), load_component(str(spec["default_sparkle"])))
        paste_erase(canvas, primary, box[:2])
        paste_erase(canvas, sparkle, box[:2])
    for side, spec in BROW_SPECS.items():
        if use_generated_brows:
            paste_ink(canvas, brows[side], tuple(spec["box"])[:2])
        else:
            paste_ink(canvas, load_component(str(spec["default"])), tuple(spec["base"]))
    if use_generated_mouth:
        paste_ink(canvas, mouth, MOUTH_BOX[:2])
    else:
        paste_ink(canvas, load_component("mouth_default.pbm"), MOUTH_BASE)
    for name, position in STATIC_BLACK_COMPONENTS:
        paste_ink(canvas, load_component(name), position)
    return canvas


def bit_difference(first: Image.Image, second: Image.Image) -> int:
    return sum(first.getpixel((x, y)) != second.getpixel((x, y))
               for y in range(CANVAS[1]) for x in range(CANVAS[0]))


def component_center_y(component: Image.Image) -> float:
    return float(mask_metrics(component)["center"][1])


def write_component(path: pathlib.Path, component: Image.Image) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    component.save(path)
    return sha256(path)


def export(output: pathlib.Path) -> dict[str, object]:
    attempt = json.loads(ATTEMPT.read_text(encoding="ascii"))
    require(attempt.get("status") == "GENERATED_PENDING_SOURCE_GATE", "attempt is not gate-pending")
    require(sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash changed")
    candidate = ROOT / str(attempt["generated_image"])
    require(candidate.is_file(), f"missing generated source: {candidate}")
    require(sha256(candidate) == attempt["generated_image_sha256"], "generated source hash drift")
    with Image.open(candidate) as source:
        normalized, transform = normalize_source(source)
    reflections: dict[str, tuple[Image.Image, Image.Image]] = {}
    reflection_metrics: dict[str, object] = {}
    for eye in EYE_SPECS:
        primary, sparkle, metrics = reflection_masks(normalized, eye)
        reflections[eye] = (primary, sparkle)
        reflection_metrics[eye] = metrics
    brows = {side: raw_black_component(normalized, tuple(spec["box"]), f"{side} brow")
             for side, spec in BROW_SPECS.items()}
    mouth = raw_black_component(normalized, MOUTH_BOX, "mouth")
    default = compose(reflections, brows, mouth, False, False, False)
    eye_lead = compose(reflections, brows, mouth, True, False, False)
    brow_answer = compose(reflections, brows, mouth, True, True, False)
    hold = compose(reflections, brows, mouth, True, True, True)
    exact_rest = binary(Image.open(V9_IDLE))
    require(bit_difference(default, exact_rest) == 0,
            "locked component baseline does not reconstruct exact V9 rest")
    default_primary_y = sum(component_center_y(load_component(str(spec["default_primary"])))
                            for spec in EYE_SPECS.values()) / 2.0
    generated_primary_y = sum(float(reflection_metrics[eye]["primary"]["center"][1])
                              for eye in EYE_SPECS) / 2.0
    primary_down_delta = generated_primary_y - default_primary_y
    default_brow_y = sum(component_center_y(load_component(str(spec["default"]))) + int(tuple(spec["base"])[1])
                         for spec in BROW_SPECS.values()) / 2.0
    generated_brow_y = sum(component_center_y(brows[side]) + tuple(spec["box"])[1]
                            for side, spec in BROW_SPECS.items()) / 2.0
    brow_lower_delta = generated_brow_y - default_brow_y
    hold_difference = bit_difference(exact_rest, hold)
    require(primary_down_delta >= MIN_PRIMARY_DOWN_DELTA_PX,
            f"down primary moved only {primary_down_delta:.2f}px from V9 rest")
    require(brow_lower_delta >= MIN_BROW_LOWER_DELTA_PX,
            f"down brows moved only {brow_lower_delta:.2f}px lower than V9 rest")
    require(hold_difference >= MIN_HOLD_PIXEL_DIFFERENCE,
            f"down hold differs by only {hold_difference}px from V9 rest")
    component_dir = output / "components"
    frame_dir = output / "pbm"
    component_hashes: dict[str, str] = {}
    for eye, (primary, sparkle) in reflections.items():
        component_hashes[f"v36_down_{eye}_primary"] = write_component(component_dir / f"v36_down_{eye}_primary.pbm", primary)
        component_hashes[f"v36_down_{eye}_sparkle"] = write_component(component_dir / f"v36_down_{eye}_sparkle.pbm", sparkle)
    for side, brow in brows.items():
        component_hashes[f"v36_down_{side}_brow"] = write_component(component_dir / f"v36_down_{side}_brow.pbm", brow)
    component_hashes["v36_down_mouth"] = write_component(component_dir / "v36_down_mouth.pbm", mouth)
    frames = [
        ("00_entry_v9_rest", exact_rest, 220),
        ("01_eye_lead", eye_lead, 240),
        ("02_brow_answer", brow_answer, 260),
        ("03_mouth_settle", hold, 340),
        ("04_hold", hold, 900),
        ("05_exact_v9_settle", exact_rest, 220),
    ]
    frame_records: list[dict[str, object]] = []
    for name, frame, duration_ms in frames:
        path = frame_dir / f"{name}.pbm"
        frame_records.append({"name": name, "path": rel(path), "sha256": write_component(path, frame),
                              "duration_ms": duration_ms})
    normalized_path = output / "normalized-source-200x200.pbm"
    normalized_hash = write_component(normalized_path, normalized)
    report = {
        "schema": "companion.v36_daily_down_attention_source_gate.v1",
        "status": "PASS_V36_DAILY_DOWN_ATTENTION_SOURCE_GATE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "locked_v9_source": rel(LOCKED_V9),
        "locked_v9_sha256": LOCKED_V9_SHA256,
        "attempt": rel(ATTEMPT),
        "candidate": rel(candidate),
        "candidate_sha256": sha256(candidate),
        "normalization": {**transform, "normalized_source": rel(normalized_path), "normalized_source_sha256": normalized_hash},
        "components": {
            "source_only": sorted(component_hashes),
            "sha256": component_hashes,
            "reflection_metrics": reflection_metrics,
            "brow_pixels": {side: mask_metrics(mask)["pixels"] for side, mask in brows.items()},
            "mouth_pixels": mask_metrics(mouth)["pixels"],
            "locked_identity_components": ["left_eye_open", "right_eye_open", "nose_default", "left_cheek_default", "right_cheek_default", "charm_star"],
        },
        "native_200_readability": {
            "primary_down_delta_px": round(primary_down_delta, 3),
            "minimum_primary_down_delta_px": MIN_PRIMARY_DOWN_DELTA_PX,
            "brow_lower_delta_px": round(brow_lower_delta, 3),
            "minimum_brow_lower_delta_px": MIN_BROW_LOWER_DELTA_PX,
            "hold_pixel_difference_from_exact_v9_rest": hold_difference,
            "minimum_hold_pixel_difference": MIN_HOLD_PIXEL_DIFFERENCE,
        },
        "choreography": {
            "deterministic": True,
            "random_motion": False,
            "full_face_cards": False,
            "ordered_components": ["exact_v9_rest", "eye_reflection_lead", "brow_answer", "mouth_settle", "hold", "exact_v9_settle"],
            "frames": frame_records,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "export-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path,
                        default=V36_ROOT / "candidate/component-export-attempt-06")
    parser.add_argument("--report", type=pathlib.Path,
                        default=ROOT / "docs/validation/companion-v36-daily-down-attention-source-gate-20260720.json")
    args = parser.parse_args()
    try:
        report = export(args.output.resolve())
    except (OSError, ValueError) as exc:
        failure = {"schema": "companion.v36_daily_down_attention_source_gate.v1",
                   "status": "FAIL_V36_DAILY_DOWN_ATTENTION_SOURCE_GATE", "error": str(exc)}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(failure, indent=2) + "\n", encoding="ascii")
        print(f"FAIL: {exc}")
        return 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print("PASS: V36 Daily-down source exported as V9-locked component masks and deterministic 200x200 choreography.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
