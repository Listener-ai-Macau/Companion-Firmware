#!/usr/bin/env python3
"""Gate one V36 directional reflection source after fixed V9 eye-body normalization."""

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
V9_LOCKED = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
V9_LOCKED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V9_IDLE = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/v9_idle_entry.pbm"
COMPONENTS = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components"
CANVAS = (200, 200)
ATTEMPTS = {
    "left": V36_ROOT / "candidate/attempt-07-generated-daily-left.json",
    "up": V36_ROOT / "candidate/attempt-08-generated-daily-up.json",
    "down": V36_ROOT / "candidate/attempt-09-generated-daily-down.json",
}
EYES = {
    "left": {"box": (42, 112, 75, 157), "center": (58.0, 134.0), "body": "left_eye_open.pbm",
             "primary": "left_eye_highlight_open.pbm", "sparkle": "left_eye_sparkle_open.pbm"},
    "right": {"box": (125, 112, 159, 157), "center": (142.0, 134.0), "body": "right_eye_open.pbm",
              "primary": "right_eye_highlight_open.pbm", "sparkle": "right_eye_sparkle_open.pbm"},
}
STATIC_LAYERS = (
    ("charm_star.pbm", (96, 31), "black"),
    ("left_brow_open.pbm", (47, 85), "black"),
    ("right_brow_open.pbm", (132, 85), "black"),
    ("left_cheek_default.pbm", (33, 160), "black"),
    ("right_cheek_default.pbm", (154, 160), "black"),
    ("nose_default.pbm", (94, 148), "black"),
    ("mouth_default.pbm", (86, 160), "black"),
)
MIN_PRIMARY_DELTA_PX = 3.0
MIN_SPARKLE_DELTA_PX = 1.0
GATE_ELIGIBLE_STATUSES = {
    "GENERATED_PENDING_SOURCE_GATE",
    "MACHINE_SOURCE_AND_200X200_BROWSER_REPLAY_PASS_PENDING_OWNER_DIRECTION_AND_TARGET_PARITY",
    "MACHINE_SOURCE_BROWSER_AND_EDGE_REPLAY_PASS_PENDING_OWNER_DIRECTION_AND_TARGET_PARITY",
    "MACHINE_SOURCE_BROWSER_AND_TARGET_HOST_PASS_PENDING_OWNER_DIRECTION",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < 160 else 255, mode="1")


def ink(mask: Image.Image) -> Image.Image:
    return mask.convert("1").point(lambda value: 255 if value == 0 else 0)


def black_components(image: Image.Image) -> list[dict[str, object]]:
    pixels = image.convert("1").load()
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, object]] = []
    for y in range(50, 180):
        for x in range(200):
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
                    if not (0 <= next_x < 200 and 0 <= next_y < 200):
                        continue
                    if (next_x, next_y) in seen or pixels[next_x, next_y] != 0:
                        continue
                    seen.add((next_x, next_y))
                    pending.append((next_x, next_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
            if box[2] - box[0] >= 16 and box[3] - box[1] >= 20 and 70 <= box[1] <= 125 and len(points) >= 180:
                result.append({"area": len(points), "box": box})
    return sorted(result, key=lambda item: tuple(item["box"])[0])


def normalize(source: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    initial = binary(source.resize(CANVAS, Image.Resampling.LANCZOS))
    eyes = black_components(initial)
    require(len(eyes) == 2, f"expected exactly two generated eye bodies, found {len(eyes)}")
    left_box, right_box = (tuple(eyes[0]["box"]), tuple(eyes[1]["box"]))
    left_center = ((left_box[0] + left_box[2] - 1) / 2.0, (left_box[1] + left_box[3] - 1) / 2.0)
    right_center = ((right_box[0] + right_box[2] - 1) / 2.0, (right_box[1] + right_box[3] - 1) / 2.0)
    scale_x = (EYES["right"]["center"][0] - EYES["left"]["center"][0]) / (right_center[0] - left_center[0])
    source_height = ((left_box[3] - left_box[1]) + (right_box[3] - right_box[1])) / 2.0
    scale_y = 45.0 / source_height
    translate_x = EYES["left"]["center"][0] - left_center[0] * scale_x
    translate_y = EYES["left"]["center"][1] - left_center[1] * scale_y
    inverse = (1.0 / scale_x, 0.0, -translate_x / scale_x, 0.0, 1.0 / scale_y, -translate_y / scale_y)
    normalized = initial.transform(CANVAS, Image.Transform.AFFINE, inverse, resample=Image.Resampling.NEAREST)
    return normalized, {
        "source_eye_boxes_200": [list(left_box), list(right_box)],
        "scale_x": round(scale_x, 6), "scale_y": round(scale_y, 6),
        "translate_x": round(translate_x, 6), "translate_y": round(translate_y, 6),
    }


def mask_points(mask: Image.Image) -> list[tuple[int, int]]:
    return [(x, y) for y in range(mask.height) for x in range(mask.width) if mask.getpixel((x, y)) == 0]


def metrics(mask: Image.Image) -> dict[str, object]:
    points = mask_points(mask)
    require(bool(points), "empty reflection component")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return {
        "pixels": len(points),
        "bbox": [min(xs), min(ys), max(xs) + 1, max(ys) + 1],
        "center": [round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3)],
    }


def reflection_pair(source: Image.Image, eye: str) -> tuple[Image.Image, Image.Image, dict[str, object]]:
    spec = EYES[eye]
    crop = source.crop(tuple(spec["box"]))
    islands = enclosed_white_island_masks(crop)
    require(len(islands) >= 2, f"{eye}: source must contain a primary plus sparkle")
    primary, sparkle = islands[0], islands[1]
    body = Image.open(COMPONENTS / str(spec["body"])).convert("1")
    for label, mask in (("primary", primary), ("sparkle", sparkle)):
        points = mask_points(mask)
        require(all(body.getpixel(point) == 0 for point in points), f"{eye}: {label} exits V9 body")
        result = metrics(mask)
        left, top, right, bottom = result["bbox"]
        require(0 < left < right < crop.width and 0 < top < bottom < crop.height,
                f"{eye}: {label} touches eye crop edge")
    primary_metrics, sparkle_metrics = metrics(primary), metrics(sparkle)
    require(int(primary_metrics["pixels"]) > int(sparkle_metrics["pixels"]) * 2,
            f"{eye}: primary does not dominate sparkle")
    box = primary_metrics["bbox"]
    require(box[3] - box[1] > box[2] - box[0], f"{eye}: primary is not vertically soft")
    return primary, sparkle, {"primary": primary_metrics, "sparkle": sparkle_metrics}


def paste(canvas: Image.Image, component: Image.Image, position: tuple[int, int], color: int) -> None:
    canvas.paste(color, position, ink(component))


def compose(reflections: dict[str, tuple[Image.Image, Image.Image]]) -> Image.Image:
    canvas = Image.new("1", CANVAS, 255)
    for name, position, color in STATIC_LAYERS:
        paste(canvas, Image.open(COMPONENTS / name).convert("1"), position, 255 if color == "white" else 0)
    for eye, spec in EYES.items():
        box = tuple(spec["box"])
        paste(canvas, Image.open(COMPONENTS / str(spec["body"])).convert("1"), box[:2], 0)
        primary, sparkle = reflections[eye]
        paste(canvas, primary, box[:2], 255)
        paste(canvas, sparkle, box[:2], 255)
    return canvas


def diff(first: Image.Image, second: Image.Image) -> int:
    return sum(first.getpixel((x, y)) != second.getpixel((x, y)) for y in range(200) for x in range(200))


def default_metrics(eye: str) -> dict[str, dict[str, object]]:
    spec = EYES[eye]
    source = Image.open(V9_IDLE).convert("1").crop(tuple(spec["box"]))
    primary, sparkle = enclosed_white_island_masks(source)[:2]
    return {"primary": metrics(primary), "sparkle": metrics(sparkle)}


def delta(direction: str, generated: float, baseline: float) -> float:
    return baseline - generated if direction in {"left", "up"} else generated - baseline


def gate(direction: str, attempt_path: pathlib.Path, output: pathlib.Path) -> dict[str, object]:
    attempt = json.loads(attempt_path.read_text(encoding="ascii"))
    require(attempt.get("status") in GATE_ELIGIBLE_STATUSES, "attempt is not source-gate eligible")
    require(sha256(V9_LOCKED) == V9_LOCKED_SHA256, "locked V9 hash drift")
    candidate = ROOT / str(attempt["generated_image"])
    require(candidate.is_file() and sha256(candidate) == attempt["generated_image_sha256"], "candidate hash drift")
    with Image.open(candidate) as image:
        normalized, transform = normalize(image)
    reflections: dict[str, tuple[Image.Image, Image.Image]] = {}
    generated_metrics: dict[str, dict[str, object]] = {}
    baseline_metrics: dict[str, dict[str, object]] = {}
    deltas: dict[str, dict[str, float]] = {}
    axis = 0 if direction == "left" else 1
    for eye in EYES:
        primary, sparkle, current = reflection_pair(normalized, eye)
        baseline = default_metrics(eye)
        primary_delta = delta(direction, float(current["primary"]["center"][axis]), float(baseline["primary"]["center"][axis]))
        sparkle_delta = delta(direction, float(current["sparkle"]["center"][axis]), float(baseline["sparkle"]["center"][axis]))
        require(primary_delta >= MIN_PRIMARY_DELTA_PX,
                f"{direction}/{eye}: primary moves only {primary_delta:.3f}px")
        require(sparkle_delta >= MIN_SPARKLE_DELTA_PX,
                f"{direction}/{eye}: sparkle moves only {sparkle_delta:.3f}px")
        reflections[eye] = (primary, sparkle)
        generated_metrics[eye], baseline_metrics[eye] = current, baseline
        deltas[eye] = {"primary_axis_delta_px": round(primary_delta, 3), "sparkle_axis_delta_px": round(sparkle_delta, 3)}
    preview = compose(reflections)
    exact_rest = Image.open(V9_IDLE).convert("1")
    difference = diff(preview, exact_rest)
    require(difference >= 300, f"{direction}: native preview differs by only {difference}px")
    component_dir = output / "components"
    component_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for eye, (primary, sparkle) in reflections.items():
        for role, mask in (("primary", primary), ("sparkle", sparkle)):
            path = component_dir / f"v36_{direction}_{eye}_{role}.pbm"
            mask.save(path)
            hashes[path.name] = sha256(path)
    preview_path = output / "pbm" / f"v36_{direction}_hold.pbm"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(preview_path)
    normalized_path = output / "normalized-source-200x200.pbm"
    normalized.save(normalized_path)
    return {
        "schema": "companion.v36_directional_reflection_source_gate.v1",
        "status": "PASS_V36_DIRECTIONAL_REFLECTION_SOURCE_GATE",
        "direction": direction,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "locked_v9_source": rel(V9_LOCKED), "locked_v9_sha256": V9_LOCKED_SHA256,
        "attempt": rel(attempt_path), "candidate": rel(candidate), "candidate_sha256": sha256(candidate),
        "normalization": {**transform, "normalized_source": rel(normalized_path), "normalized_source_sha256": sha256(normalized_path)},
        "source_reflection_metrics": generated_metrics,
        "v9_rest_reflection_metrics": baseline_metrics,
        "direction_deltas": deltas,
        "minimum_primary_axis_delta_px": MIN_PRIMARY_DELTA_PX,
        "minimum_sparkle_axis_delta_px": MIN_SPARKLE_DELTA_PX,
        "native_200_hold": {"path": rel(preview_path), "sha256": sha256(preview_path), "pixels_different_from_exact_v9_rest": difference},
        "component_hashes": hashes,
        "component_only": True, "full_face_cards": False, "random_motion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=tuple(ATTEMPTS), required=True)
    parser.add_argument("--attempt", type=int, help="Use a separately versioned candidate attempt without replacing default evidence.")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--write", type=pathlib.Path)
    args = parser.parse_args()
    attempt_numbers = {"left": 7, "up": 8, "down": 9}
    attempt_number = args.attempt or attempt_numbers[args.direction]
    attempt_path = ATTEMPTS[args.direction] if args.attempt is None else \
        V36_ROOT / "candidate" / f"attempt-{attempt_number:02d}-generated-daily-{args.direction}.json"
    output = args.output or (V36_ROOT / f"candidate/component-export-attempt-{attempt_number:02d}")
    suffix = "" if args.attempt is None else f"-attempt-{attempt_number:02d}"
    report_path = args.write or (ROOT / "docs/validation" /
                                 f"companion-v36-daily-{args.direction}-reflection-source-gate{suffix}-20260720.json")
    try:
        report = gate(args.direction, attempt_path, output.resolve())
    except (OSError, ValueError) as exc:
        report = {"schema": "companion.v36_directional_reflection_source_gate.v1",
                  "status": "FAIL_V36_DIRECTIONAL_REFLECTION_SOURCE_GATE", "direction": args.direction,
                  "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "error": str(exc)}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
        print(f"FAIL: {exc}")
        return 1
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print(f"PASS: V36 {args.direction} source exports fixed-V9-body reflection components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
