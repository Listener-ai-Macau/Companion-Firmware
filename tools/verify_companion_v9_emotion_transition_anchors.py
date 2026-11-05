#!/usr/bin/env python3
"""Verify completeness and visible source-pose diversity for a V9 emotion sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_STATES = (
    "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down",
    "curious_question", "alert_surprised", "joyful_spark", "affectionate_warm",
    "recording_focus", "listening_focus", "menu_thinking", "sleep_rest_no_moon",
)
MIN_INK_PIXELS = 150
MIN_PAIR_PIXEL_DIFFERENCE = 100
SLEEP_TOP_DECORATION_MAX_INK_PIXELS = 20


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def cell_bits(image: Image.Image, box: tuple[int, int, int, int]) -> bytes:
    return bytes(1 if value < 128 else 0 for value in image.convert("L").crop(box).getdata())


def upper_band_ink_pixels(bits: bytes, width: int, height: int) -> int:
    """Sleep is rest-only: no moon, crescent, Z, or detached top decoration."""
    top_height = round(height * 0.28)
    return sum(bits[:width * top_height])


def verify(candidate: pathlib.Path, request_path: pathlib.Path, eye_report_path: pathlib.Path) -> dict[str, object]:
    errors: list[str] = []
    request = load_json(request_path)
    eye_report = load_json(eye_report_path)
    required_states = tuple(request.get("required_cells", []))
    transition_roles = request.get("transition_roles")
    target_profile = request.get("target_profile")
    if required_states != EXPECTED_STATES:
        errors.append("extension request does not enumerate the complete ordered twelve-state anchor program")
    if not isinstance(transition_roles, dict) or tuple(transition_roles) != EXPECTED_STATES:
        errors.append("extension request does not bind a transition role to every anchor")
    if not isinstance(target_profile, dict) or target_profile.get("grid") != [3, 4]:
        errors.append("extension request is not a 3x4 source sheet")
    if eye_report.get("status") != "PASS_OPEN_EYE_IDENTITY_GATE" or eye_report.get("candidate_sha256") != sha256(candidate):
        errors.append("extension open-eye identity evidence is missing or mismatched")

    with Image.open(candidate) as image:
        width, height = image.size
        records: list[dict[str, object]] = []
        cells: list[bytes] = []
        hashes: list[str] = []
        for index, state in enumerate(EXPECTED_STATES):
            row, column = divmod(index, 4)
            box = (
                round(column * width / 4), round(row * height / 3),
                round((column + 1) * width / 4), round((row + 1) * height / 3),
            )
            bits = cell_bits(image, box)
            ink_pixels = sum(bits)
            cell_width = box[2] - box[0]
            cell_height = box[3] - box[1]
            upper_band_ink = upper_band_ink_pixels(bits, cell_width, cell_height) if \
                state == "sleep_rest_no_moon" else None
            digest = hashlib.sha256(bits).hexdigest().upper()
            cells.append(bits)
            hashes.append(digest)
            records.append({
                "state": state,
                "cell": f"{row},{column}",
                "transition_role": transition_roles.get(state) if isinstance(transition_roles, dict) else None,
                "ink_pixels": ink_pixels,
                "binary_sha256": digest,
            })
            if upper_band_ink is not None:
                records[-1]["upper_band_ink_pixels"] = upper_band_ink
                if upper_band_ink > SLEEP_TOP_DECORATION_MAX_INK_PIXELS:
                    errors.append(
                        "sleep_rest_no_moon contains a forbidden upper decoration; "
                        "sleep must not add moon, crescent, Z, or other detached top marks"
                    )
            if ink_pixels < MIN_INK_PIXELS:
                errors.append(f"{state} is visually blank")
        if len(set(hashes)) != len(EXPECTED_STATES):
            errors.append("emotion source sheet contains duplicate full-cell anchors")
        minimum_difference = None
        for left in range(len(cells)):
            for right in range(left + 1, len(cells)):
                difference = sum(first != second for first, second in zip(cells[left], cells[right]))
                minimum_difference = difference if minimum_difference is None else min(minimum_difference, difference)
                if difference < MIN_PAIR_PIXEL_DIFFERENCE:
                    errors.append(f"{EXPECTED_STATES[left]}/{EXPECTED_STATES[right]} are too similar ({difference}px)")
    return {
        "schema": "companion.v9_emotion_transition_anchor_gate.v1",
        "status": "PASS_EMOTION_TRANSITION_ANCHOR_GATE" if not errors else "FAIL_EMOTION_TRANSITION_ANCHOR_GATE",
        "candidate": rel(candidate),
        "candidate_sha256": sha256(candidate),
        "request": rel(request_path),
        "open_eye_identity_report": rel(eye_report_path),
        "state_count": len(EXPECTED_STATES),
        "unique_anchor_count": len(set(hashes)),
        "minimum_pair_pixel_difference": minimum_difference,
        "records": records,
        "runtime_resource_activated": False,
        "full_face_playback": "forbidden",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--request", type=pathlib.Path, required=True)
    parser.add_argument("--open-eye-report", type=pathlib.Path, required=True)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = args.candidate.resolve()
        if not candidate.is_file():
            raise ValueError(f"missing candidate: {candidate}")
        result = verify(candidate, args.request.resolve(), args.open_eye_report.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_EMOTION_TRANSITION_ANCHOR_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: all twelve V9 emotion anchors are present, distinct and transition-bound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
