#!/usr/bin/env python3
"""Gate V18-V20 complete special-expression sources before mask extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from verify_companion_v17_functional_context_source import border_ink, connected_components


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SPECS = {
    "menu_active": {
        "version": "v18",
        "iteration": "companion-pet-expression-v9-extension-v18-menu-special-expression-source",
        "attempt": "attempt-01-generated-menu-special-expression.json",
        "special": "menu_three_dot_stack",
    },
    "recording_active": {
        "version": "v19",
        "iteration": "companion-pet-expression-v9-extension-v19-recording-special-expression-source",
        "attempt": "attempt-01-generated-recording-special-expression.json",
        "special": "recording_side_ripples",
    },
    "upgrade_active": {
        "version": "v20",
        "iteration": "companion-pet-expression-v9-extension-v20-upgrade-special-expression-source",
        "attempt": "attempt-01-generated-upgrade-special-expression.json",
        "special": "upgrade_four_segment_ring",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def center(item: dict[str, Any]) -> tuple[float, float]:
    raw = item["center"]
    return float(raw[0]), float(raw[1])


def size(item: dict[str, Any]) -> tuple[int, int]:
    crop = item["crop"]
    return int(crop[2] - crop[0]), int(crop[3] - crop[1])


def face_geometry(components: list[dict[str, Any]], width: int, height: int) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    ordered = sorted(components, key=lambda item: int(item["ink_pixels"]), reverse=True)
    if len(ordered) < 2:
        return None, ["candidate lacks two eye-body source components"]
    left_eye, right_eye = sorted(ordered[:2], key=lambda item: center(item)[0])
    left_w, left_h = size(left_eye)
    right_w, right_h = size(right_eye)
    left_x, left_y = center(left_eye)
    right_x, right_y = center(right_eye)
    if min(left_eye["ink_pixels"], right_eye["ink_pixels"]) < 15000:
        errors.append("candidate eye bodies are not the dominant complete-face ink")
    if abs(left_w - right_w) > max(left_w, right_w) * 0.08 or abs(left_h - right_h) > max(left_h, right_h) * 0.08:
        errors.append("candidate eye pair does not preserve matched V9 eye geometry")
    if abs(left_y - right_y) > 4:
        errors.append("candidate eye pair loses the shared V9 eye-height anchor")
    eye_gap = right_x - left_x - (left_w + right_w) / 2
    if not (1.2 <= eye_gap / ((left_w + right_w) / 2) <= 1.9):
        errors.append("candidate eye spacing is outside the V9 open-eye geometry envelope")
    pair_x = (left_x + right_x) / 2
    pair_y = (left_y + right_y) / 2
    if abs(pair_x - width / 2) > width * 0.08 or not height * 0.42 <= pair_y <= height * 0.64:
        errors.append("candidate face is not a single centered V9-like pose")
    brows = [item for item in components if 1000 <= item["ink_pixels"] <= 6000 and
             center(item)[1] < pair_y - min(left_h, right_h) * 0.5]
    cheeks = [item for item in components if 1000 <= item["ink_pixels"] <= 6000 and
              center(item)[1] > pair_y + min(left_h, right_h) * 0.45]
    if len(brows) < 2:
        errors.append("candidate lacks a source-derived paired brow response")
    if len(cheeks) < 2:
        errors.append("candidate lacks a source-derived lower-face/cheek vocabulary")
    return {
        "left_eye": {"crop": left_eye["crop"], "ink_pixels": left_eye["ink_pixels"]},
        "right_eye": {"crop": right_eye["crop"], "ink_pixels": right_eye["ink_pixels"]},
        "eye_pair_center": [pair_x, pair_y],
        "eye_gap_ratio": eye_gap / ((left_w + right_w) / 2),
        "brow_component_count": len(brows),
        "lower_face_component_count": len(cheeks),
    }, errors


def special_geometry(function: str, components: list[dict[str, Any]], eyes: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    left_eye_crop = eyes["left_eye"]["crop"]
    right_eye_crop = eyes["right_eye"]["crop"]
    pair_center_y = eyes["eye_pair_center"][1]
    if function == "menu_active":
        marks = [item for item in components if item["ink_pixels"] < 1200 and center(item)[1] < pair_center_y - 100]
        ordered = sorted(marks, key=lambda item: center(item)[1])
        if len(ordered) != 3:
            errors.append("Menu special pose must contain exactly three detached context dots")
        elif max(center(item)[0] for item in ordered) - min(center(item)[0] for item in ordered) > 10 or \
                any(center(ordered[index + 1])[1] - center(ordered[index])[1] < 30 for index in range(2)):
            errors.append("Menu context dots are not a compact vertical source group")
        return {"context_component_count": len(marks), "context_crops": [item["crop"] for item in ordered]}, errors
    if function == "recording_active":
        marks = [item for item in components if item["ink_pixels"] >= 1000 and
                 left_eye_crop[0] > item["crop"][2] or False]
        side_marks = [item for item in components if item["ink_pixels"] >= 1000 and
                      (item["crop"][2] <= left_eye_crop[0] or item["crop"][0] >= right_eye_crop[2]) and
                      left_eye_crop[1] <= center(item)[1] <= left_eye_crop[3]]
        left = [item for item in side_marks if center(item)[0] < left_eye_crop[0]]
        right = [item for item in side_marks if center(item)[0] > right_eye_crop[2]]
        if len(left) != 2 or len(right) != 2:
            errors.append("Recording special pose must contain two source ripples on each outer side")
        return {"context_component_count": len(side_marks), "left_ripple_count": len(left), "right_ripple_count": len(right),
                "context_crops": [item["crop"] for item in side_marks]}, errors
    marks = [item for item in components if item["ink_pixels"] < 1200 and center(item)[1] < pair_center_y - 100]
    horizontal = [item for item in marks if size(item)[0] > size(item)[1]]
    vertical = [item for item in marks if size(item)[0] <= size(item)[1]]
    if len(marks) != 4 or len(horizontal) != 2 or len(vertical) != 2:
        errors.append("Upgrade special pose must contain exactly four separate ring segments")
    return {"context_component_count": len(marks), "context_crops": [item["crop"] for item in marks]}, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    errors: list[str] = []
    entries: dict[str, Any] = {}
    for function, spec in SPECS.items():
        attempt_path = ROOT / "docs/art/iterations" / spec["iteration"] / "candidate" / spec["attempt"]
        entry_errors: list[str] = []
        try:
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
            expected_schema = f"companion.{spec['version']}_complete_special_expression_generation_attempt.v1"
            if attempt.get("schema") != expected_schema or attempt.get("status") not in {
                "PENDING_MACHINE_SOURCE_GATE", "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT"
            }:
                entry_errors.append("generation attempt disposition drifted")
            if attempt.get("function") != function or attempt.get("source_reference_sha256") != LOCKED_V9_SHA256:
                entry_errors.append("function or locked V9 reference drifted")
            if attempt.get("runtime_resource_activated") is not False or \
                    attempt.get("active_candidate_binding") != "forbidden" or \
                    attempt.get("component_export") not in {"forbidden_pending_machine_source_gate", "pending_source_mask_export"}:
                entry_errors.append("candidate runtime disposition drifted")
            image_path = ROOT / str(attempt.get("generated_image", ""))
            if not image_path.is_file() or attempt.get("generated_image_sha256") != sha256(image_path):
                entry_errors.append("generated image is missing or hash drifted")
                image = None
            else:
                image = Image.open(image_path).convert("L")
            metrics: dict[str, Any] = {}
            if image is not None:
                if image.size != (1254, 1254):
                    entry_errors.append("complete special-expression source must be a 1254 square")
                components = connected_components(image)
                metrics["component_count"] = len(components)
                metrics["ink_pixels"] = sum(item["ink_pixels"] for item in components)
                metrics["border_ink_pixels"] = border_ink(image)
                if not 10 <= len(components) <= 14 or not 50000 <= metrics["ink_pixels"] <= 90000:
                    entry_errors.append("candidate is not a single sparse complete face with context detail")
                if metrics["border_ink_pixels"] > 20:
                    entry_errors.append("candidate contains an illegal border or UI frame")
                eyes, face_errors = face_geometry(components, image.width, image.height)
                entry_errors.extend(face_errors)
                if eyes is not None:
                    special, special_errors = special_geometry(function, components, eyes)
                    metrics["identity_geometry"] = eyes
                    metrics["special_geometry"] = special
                    entry_errors.extend(special_errors)
            entries[function] = {
                "attempt": rel(attempt_path),
                "status": "PASS" if not entry_errors else "FAIL",
                "metrics": metrics,
                "errors": entry_errors,
            }
            errors.extend(f"{function}: {error}" for error in entry_errors)
        except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"{function}: {exc}")
    result = {
        "schema": "companion.v18_v20_complete_special_expression_source_gate.v1",
        "status": "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_GATE" if not errors else
                  "FAIL_V18_V20_COMPLETE_SPECIAL_EXPRESSION_SOURCE_GATE",
        "entries": entries,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "component_export": "pending_source_mask_export" if not errors else "forbidden",
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V18-V20 each provide one V9-anchored complete special-expression source pose.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
