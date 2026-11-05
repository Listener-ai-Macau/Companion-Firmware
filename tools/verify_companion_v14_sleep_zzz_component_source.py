#!/usr/bin/env python3
"""Machine-check the V14 V9-only sleep and ZZZ source before any Rig binding."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
V14_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair"
DEFAULT_CANDIDATE = V14_ROOT / "generated_pet_expression_extension_v14_sleep_zzz_component_repair_candidate.png"
DEFAULT_REQUEST = V14_ROOT / "generation-request.json"
LOCKED_V9 = "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
REQUIRED_COMPONENTS = (
    "left_brow", "right_brow", "left_closed_eye", "right_closed_eye",
    "left_cheek", "right_cheek", "nose", "mouth",
    "sleep_breath_dot_left", "sleep_breath_dot_right",
    "sleep_z_small", "sleep_z_medium", "sleep_z_large",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def components(image: Image.Image, minimum_pixels: int = 100) -> list[dict[str, int]]:
    """Find detached generated source islands without drawing any face geometry."""
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


def _symmetric(left: dict[str, int], right: dict[str, int], face_center_x: float, width: int) -> bool:
    return abs((left["center_x"] + right["center_x"]) - (2 * face_center_x)) <= round(width * 0.06)


def classify(parts: list[dict[str, int]], width: int, height: int) -> tuple[dict[str, dict[str, int]], list[str]]:
    """Assign the fixed V14 ZZZ-then-face source stack without inventing art."""
    if len(parts) != len(REQUIRED_COMPONENTS):
        return {}, [f"V14 sleep source must contain exactly thirteen detached source islands, found {len(parts)}"]
    errors: list[str] = []
    stack = sorted(parts, key=lambda part: (part["center_y"], part["center_x"]))
    z_large, z_medium, z_small = stack[0:3]
    brow_pair = sorted(stack[3:5], key=lambda part: part["center_x"])
    eye_pair = sorted(stack[5:7], key=lambda part: part["center_x"])
    nose = stack[7]
    cheek_pair = sorted(stack[8:10], key=lambda part: part["center_x"])
    mouth = stack[10]
    breath_pair = sorted(stack[11:13], key=lambda part: part["center_x"])
    left_brow, right_brow = brow_pair
    left_eye, right_eye = eye_pair
    left_cheek, right_cheek = cheek_pair
    left_dot, right_dot = breath_pair
    face_center_x = (nose["center_x"] + mouth["center_x"]) / 2
    assignments = {
        "left_brow": left_brow,
        "right_brow": right_brow,
        "left_closed_eye": left_eye,
        "right_closed_eye": right_eye,
        "left_cheek": left_cheek,
        "right_cheek": right_cheek,
        "nose": nose,
        "mouth": mouth,
        "sleep_breath_dot_left": left_dot,
        "sleep_breath_dot_right": right_dot,
        "sleep_z_small": z_small,
        "sleep_z_medium": z_medium,
        "sleep_z_large": z_large,
    }
    for label, left, right in (("brow", left_brow, right_brow), ("closed eye", left_eye, right_eye),
                               ("cheek", left_cheek, right_cheek), ("breath dot", left_dot, right_dot)):
        if not _symmetric(left, right, face_center_x, width) or abs(left["center_y"] - right["center_y"]) > round(height * 0.03):
            errors.append(f"V14 {label} pair is not a balanced V9 pair")
    if not (z_large["center_y"] < z_medium["center_y"] < z_small["center_y"] < left_brow["center_y"] <
            left_eye["center_y"] < nose["center_y"] <= left_cheek["center_y"] < mouth["center_y"] < left_dot["center_y"]):
        errors.append("V14 ZZZ/face/breath source stack is not ordered")
    if not (z_small["ink_pixels"] < z_medium["ink_pixels"] < z_large["ink_pixels"] and
            all(part["height"] > part["width"] for part in (z_small, z_medium, z_large))):
        errors.append("V14 upper components are not a distinct small/medium/large Z group")
    if not all(part["center_x"] > round(width * 0.55) for part in (z_small, z_medium, z_large)) or \
            z_small["center_y"] >= right_brow["top"]:
        errors.append("V14 ZZZ group is not isolated above and outside the upper-right face")
    if not all(part["width"] > part["height"] for part in (left_brow, right_brow, left_eye, right_eye, mouth)):
        errors.append("V14 sleep brows, closed eyes, or mouth are not horizontal source strokes")
    if not all(part["width"] <= part["height"] * 2.5 for part in (left_cheek, right_cheek, nose)):
        errors.append("V14 sleep cheeks or nose are not compact source marks")
    if not all(abs(part["width"] - part["height"]) <= max(part["width"], part["height"]) // 2 for part in (left_dot, right_dot)):
        errors.append("V14 breath components are not compact dots")
    if not (abs(nose["center_x"] - mouth["center_x"]) <= round(width * 0.06) and
            round(width * 0.2) <= face_center_x <= round(width * 0.8)):
        errors.append("V14 sleep nose or resting mouth is not locally centered")
    if not (left_dot["center_x"] < left_cheek["center_x"] < nose["center_x"] < right_cheek["center_x"] < right_dot["center_x"] and
            left_dot["center_y"] > left_cheek["center_y"] and right_dot["center_y"] > right_cheek["center_y"]):
        errors.append("V14 breath dots are not paired below and outside the cheeks")
    if not (left_dot["ink_pixels"] < left_cheek["ink_pixels"] and right_dot["ink_pixels"] < right_cheek["ink_pixels"]):
        errors.append("V14 breath dots are not restrained micro-components")
    return assignments, errors


def verify(candidate: Path, request_path: Path) -> dict[str, object]:
    errors: list[str] = []
    request = load_json(request_path)
    references = request.get("source_references")
    locked_refs = [item for item in references if isinstance(item, dict) and
                   item.get("path") == LOCKED_V9 and str(item.get("sha256", "")).upper() == LOCKED_V9_SHA256] \
        if isinstance(references, list) else []
    if request.get("iteration_id") != "companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair-20260719":
        errors.append("request is not the versioned V14 sleep ZZZ repair")
    if request.get("source_art_type") != "face_anchor" or \
            request.get("required_cells") != ["sleep_rest_no_moon_with_breath_and_zzz_components"] or \
            request.get("required_source_components") != list(REQUIRED_COMPONENTS):
        errors.append("request does not declare the one-cell V14 thirteen-component sleep source")
    if len(locked_refs) != 1 or not isinstance(references, list) or len(references) != 1:
        errors.append("V14 sleep candidate does not cite locked V9 as its only visual reference")
    profile = request.get("target_profile")
    if not isinstance(profile, dict) or profile.get("grid") != [1, 1] or \
            profile.get("runtime_status") != "inactive_pending_component_export_machine_checks_and_owner_review":
        errors.append("V14 sleep candidate is not declared as a one-cell runtime-inactive source")
    if request.get("planned_generated_output") != relative(candidate):
        errors.append("V14 request planned output does not identify this candidate")
    output = request.get("generated_output")
    if output is not None and (not isinstance(output, dict) or output.get("path") != relative(candidate) or
                               str(output.get("sha256", "")).upper() != sha256(candidate) or
                               output.get("runtime_resource_activated") is not False or
                               output.get("active_candidate_binding") != "forbidden"):
        errors.append("V14 generated-output record does not preserve its unbound policy")

    with Image.open(candidate) as image:
        width, height = image.size
        parts = components(image)
        assignments, component_errors = classify(parts, width, height)
        errors.extend(component_errors)
        all_ink = sum(part["ink_pixels"] for part in parts)
        if width != height or width < 512:
            errors.append("V14 sleep source is not a sufficiently large square source image")
        if all_ink < 5000 or all_ink > round(width * height * 0.1):
            errors.append("V14 sleep source ink density is outside the sparse V9 face range")
    return {
        "schema": "companion.v14_sleep_zzz_component_source_gate.v1",
        "status": "PASS_V14_SLEEP_ZZZ_COMPONENT_SOURCE_GATE" if not errors else "FAIL_V14_SLEEP_ZZZ_COMPONENT_SOURCE_GATE",
        "candidate": relative(candidate),
        "candidate_sha256": sha256(candidate),
        "request": relative(request_path),
        "source_reference": {"path": LOCKED_V9, "sha256": LOCKED_V9_SHA256},
        "source_component_count": len(parts),
        "required_source_components": list(REQUIRED_COMPONENTS),
        "source_components_raw": parts,
        "components": [{"name": name, **assignments[name]} for name in REQUIRED_COMPONENTS if name in assignments],
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
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
    if result["status"] != "PASS_V14_SLEEP_ZZZ_COMPONENT_SOURCE_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V14 sleep source is V9-only, complete, three-Z-equipped, and still runtime inactive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
