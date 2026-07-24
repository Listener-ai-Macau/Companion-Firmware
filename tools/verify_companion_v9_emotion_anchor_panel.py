#!/usr/bin/env python3
"""Verify the eight non-Daily V9 emotion anchors in a source-only 2x4 panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_STATES = (
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
    """The closed-eye rest pose must not carry a top charm, moon, or Z."""
    return sum(bits[:width * round(height * 0.28)])


def verify(candidate: pathlib.Path, request_path: pathlib.Path, eye_report_path: pathlib.Path) -> dict[str, object]:
    errors: list[str] = []
    request = load_json(request_path)
    eye_report = load_json(eye_report_path)
    required_states = tuple(request.get("required_cells", []))
    transition_roles = request.get("transition_roles")
    target_profile = request.get("target_profile")
    if required_states != EXPECTED_STATES:
        errors.append("emotion-panel request does not enumerate the ordered eight-state program")
    if not isinstance(transition_roles, dict) or tuple(transition_roles) != EXPECTED_STATES:
        errors.append("emotion-panel request does not bind a transition role to every anchor")
    if not isinstance(target_profile, dict) or target_profile.get("grid") != [2, 4]:
        errors.append("emotion-panel request is not a 2x4 source panel")
    if eye_report.get("status") != "PASS_OPEN_EYE_IDENTITY_GATE" or eye_report.get("candidate_sha256") != sha256(candidate):
        errors.append("emotion-panel open-eye identity evidence is missing or mismatched")

    with Image.open(candidate) as image:
        width, height = image.size
        cells: list[bytes] = []
        hashes: list[str] = []
        records: list[dict[str, object]] = []
        for index, state in enumerate(EXPECTED_STATES):
            row, column = divmod(index, 4)
            box = (
                round(column * width / 4), round(row * height / 2),
                round((column + 1) * width / 4), round((row + 1) * height / 2),
            )
            bits = cell_bits(image, box)
            ink_pixels = sum(bits)
            digest = hashlib.sha256(bits).hexdigest().upper()
            record: dict[str, object] = {
                "state": state,
                "cell": f"{row},{column}",
                "transition_role": transition_roles.get(state) if isinstance(transition_roles, dict) else None,
                "ink_pixels": ink_pixels,
                "binary_sha256": digest,
            }
            if state == "sleep_rest_no_moon":
                upper_band_ink = upper_band_ink_pixels(bits, box[2] - box[0], box[3] - box[1])
                record["upper_band_ink_pixels"] = upper_band_ink
                if upper_band_ink > SLEEP_TOP_DECORATION_MAX_INK_PIXELS:
                    errors.append(
                        "sleep_rest_no_moon contains a forbidden upper decoration; "
                        "sleep must not add moon, crescent, Z, or detached top marks"
                    )
            records.append(record)
            cells.append(bits)
            hashes.append(digest)
            if ink_pixels < MIN_INK_PIXELS:
                errors.append(f"{state} is visually blank")
        if len(set(hashes)) != len(EXPECTED_STATES):
            errors.append("emotion-panel source contains duplicate full-cell anchors")
        minimum_difference = None
        for left in range(len(cells)):
            for right in range(left + 1, len(cells)):
                difference = sum(first != second for first, second in zip(cells[left], cells[right]))
                minimum_difference = difference if minimum_difference is None else min(minimum_difference, difference)
                if difference < MIN_PAIR_PIXEL_DIFFERENCE:
                    errors.append(f"{EXPECTED_STATES[left]}/{EXPECTED_STATES[right]} are too similar ({difference}px)")
    return {
        "schema": "companion.v9_emotion_anchor_panel_gate.v1",
        "status": "PASS_EMOTION_ANCHOR_PANEL_GATE" if not errors else "FAIL_EMOTION_ANCHOR_PANEL_GATE",
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
    if result["status"] != "PASS_EMOTION_ANCHOR_PANEL_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: all eight non-Daily V9 emotion anchors are distinct and transition-bound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
