#!/usr/bin/env python3
"""Machine-check the single V12 V9-derived sleep source before any Rig binding."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v12-sleep-anchor-repair/"
    "generated_pet_expression_extension_v12_sleep_anchor_repair_candidate.png"
)
DEFAULT_REQUEST = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v12-sleep-anchor-repair/"
    "generation-request.json"
)
LOCKED_V9 = "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
REQUIRED_COMPONENTS = (
    "left_brow", "right_brow", "left_closed_eye", "right_closed_eye",
    "left_cheek", "right_cheek", "nose", "mouth",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def components(image: Image.Image, minimum_pixels: int = 100) -> list[dict[str, int]]:
    """Find source ink islands without inventing or redrawing facial geometry."""
    mono = image.convert("L")
    width, height = mono.size
    pixels = mono.load()
    visited: set[tuple[int, int]] = set()
    result: list[dict[str, int]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited or pixels[x, y] >= 128:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited.add((x, y))
            count = 0
            left = right = x
            top = bottom = y
            while queue:
                point_x, point_y = queue.popleft()
                count += 1
                left, right = min(left, point_x), max(right, point_x)
                top, bottom = min(top, point_y), max(bottom, point_y)
                for delta_x, delta_y in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                                         (0, 1), (1, -1), (1, 0), (1, 1)):
                    next_x, next_y = point_x + delta_x, point_y + delta_y
                    if 0 <= next_x < width and 0 <= next_y < height and \
                            (next_x, next_y) not in visited and pixels[next_x, next_y] < 128:
                        visited.add((next_x, next_y))
                        queue.append((next_x, next_y))
            if count >= minimum_pixels:
                result.append({
                    "ink_pixels": count,
                    "left": left,
                    "top": top,
                    "width": right - left + 1,
                    "height": bottom - top + 1,
                    "center_x": (left + right) // 2,
                    "center_y": (top + bottom) // 2,
                })
    return result


def classify(parts: list[dict[str, int]], width: int, height: int,
             top_empty_ratio: float = 0.28) -> tuple[dict[str, dict[str, int]], list[str]]:
    errors: list[str] = []
    assignments: dict[str, dict[str, int]] = {}
    top_limit = round(height * top_empty_ratio)
    if any(part["top"] < top_limit for part in parts):
        errors.append("sleep source contains forbidden ink above the brow zone")
    if len(parts) != len(REQUIRED_COMPONENTS):
        errors.append(f"sleep source must contain exactly eight facial source islands, found {len(parts)}")

    brows = [part for part in parts if round(height * 0.29) <= part["center_y"] < round(height * 0.49)]
    eyes = [part for part in parts if round(height * 0.49) <= part["center_y"] < round(height * 0.62) and
            part["width"] > part["height"] * 2]
    lower = [part for part in parts if round(height * 0.58) <= part["center_y"] < round(height * 0.75)]
    if len(brows) != 2:
        errors.append("sleep source lacks exactly two brows")
    if len(eyes) != 2:
        errors.append("sleep source lacks exactly two closed-eye strokes")
    if len(lower) != 4:
        errors.append("sleep source lacks exactly two cheeks, nose, and mouth")
    if errors:
        return assignments, errors

    brows.sort(key=lambda part: part["center_x"])
    eyes.sort(key=lambda part: part["center_x"])
    lower.sort(key=lambda part: part["center_x"])
    assignments["left_brow"], assignments["right_brow"] = brows
    assignments["left_closed_eye"], assignments["right_closed_eye"] = eyes
    assignments["left_cheek"], assignments["nose"], assignments["mouth"], assignments["right_cheek"] = lower

    if not assignments["left_cheek"]["center_x"] < assignments["nose"]["center_x"] < assignments["right_cheek"]["center_x"]:
        errors.append("sleep cheek/nose horizontal order is invalid")
    if assignments["mouth"]["center_x"] < width * 0.42 or assignments["mouth"]["center_x"] > width * 0.58:
        errors.append("sleep mouth is not centered")
    if assignments["mouth"]["center_y"] <= assignments["nose"]["center_y"]:
        errors.append("sleep mouth does not sit below the nose")
    for name in ("left_brow", "right_brow", "left_closed_eye", "right_closed_eye", "mouth"):
        part = assignments[name]
        if part["width"] <= part["height"]:
            errors.append(f"sleep {name} is not a horizontal source stroke")
    for name in ("left_cheek", "right_cheek", "nose"):
        part = assignments[name]
        if part["width"] > part["height"] * 2:
            errors.append(f"sleep {name} is not a compact source mark")
    return assignments, errors


def verify(candidate: Path, request_path: Path) -> dict[str, object]:
    errors: list[str] = []
    request = load_json(request_path)
    references = request.get("source_references")
    locked_refs = [item for item in references if isinstance(item, dict) and
                   item.get("path") == LOCKED_V9 and str(item.get("sha256", "")).upper() == LOCKED_V9_SHA256] \
        if isinstance(references, list) else []
    if request.get("iteration_id") != "companion-pet-expression-v9-extension-v12-sleep-anchor-repair-20260719":
        errors.append("request is not the versioned V12 sleep repair")
    if request.get("source_art_type") != "face_anchor" or request.get("required_cells") != ["sleep_rest_no_moon"]:
        errors.append("request does not declare one sleep face anchor")
    if len(locked_refs) != 1 or len(references) != 1:
        errors.append("sleep candidate does not cite locked V9 as its only visual reference")
    profile = request.get("target_profile")
    if not isinstance(profile, dict) or profile.get("grid") != [1, 1] or \
            profile.get("runtime_status") != "inactive_pending_component_export_machine_checks_and_owner_review":
        errors.append("sleep candidate is not declared as a one-cell runtime-inactive source")
    output = request.get("generated_output")
    if not isinstance(output, dict) or output.get("path") != rel(candidate) or \
            str(output.get("sha256", "")).upper() != sha256(candidate) or \
            output.get("status") != "machine_source_gate_pass_pending_owner_art_review" or \
            output.get("runtime_resource_activated") is not False or \
            output.get("active_candidate_binding") != "forbidden":
        errors.append("request generated-output record is missing or does not preserve the V12 unbound policy")

    with Image.open(candidate) as image:
        width, height = image.size
        parts = components(image)
        assignments, component_errors = classify(parts, width, height)
        errors.extend(component_errors)
        all_ink = sum(part["ink_pixels"] for part in parts)
        if width != height or width < 512:
            errors.append("sleep source is not a sufficiently large square source image")
        if all_ink < 4000 or all_ink > round(width * height * 0.08):
            errors.append("sleep source ink density is outside the V9 sparse-face range")
    return {
        "schema": "companion.v12_sleep_anchor_source_gate.v1",
        "status": "PASS_V12_SLEEP_ANCHOR_SOURCE_GATE" if not errors else "FAIL_V12_SLEEP_ANCHOR_SOURCE_GATE",
        "candidate": rel(candidate),
        "candidate_sha256": sha256(candidate),
        "request": rel(request_path),
        "source_reference": {"path": LOCKED_V9, "sha256": LOCKED_V9_SHA256},
        "source_component_count": len(parts),
        "required_source_components": list(REQUIRED_COMPONENTS),
        "source_components_raw": parts,
        "components": [{"name": name, **part} for name, part in assignments.items()],
        "runtime_resource_activated": False,
        "full_face_playback": "forbidden",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    try:
        candidate = args.candidate.resolve()
        if not candidate.is_file():
            raise ValueError(f"missing candidate: {candidate}")
        result = verify(candidate, args.request.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_V12_SLEEP_ANCHOR_SOURCE_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V12 sleep source is complete, V9-only, moon/Z-free, and still runtime inactive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
