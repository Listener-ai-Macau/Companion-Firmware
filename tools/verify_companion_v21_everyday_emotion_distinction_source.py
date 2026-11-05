#!/usr/bin/env python3
"""Gate the V21 six-pose emotion source sheet before component extraction."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
REQUEST = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source/"
    "generation-request.json"
)
ATTEMPT = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source/"
    "candidate/attempt-01-generated-everyday-emotion-distinction.json"
)
DEFAULT_WRITE = ROOT / "docs/validation/companion-v21-everyday-emotion-distinction-source-gate-20260719.json"
EMOTIONS = ("calm", "curious", "warm", "playful", "puzzled", "alert")
INK_THRESHOLD = 96
MIN_POSE_INK_PIXELS = 9000
MAX_POSE_INK_PIXELS = 15000
MIN_PAIRWISE_NORMALIZED_DIFFERENCE = 1000
MAX_PAIRWISE_NORMALIZED_DIFFERENCE = 4200
MAX_THRESHOLD_SAFE_ANTIALIAS_FRACTION = 0.20


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def cell_box(index: int, width: int, height: int) -> tuple[int, int, int, int]:
    column = index % 3
    row = index // 3
    return column * width // 3, row * height // 2, (column + 1) * width // 3, (row + 1) * height // 2


def binary_crop(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    return image.crop(box).point(lambda value: 255 if value < INK_THRESHOLD else 0, mode="1")


def main() -> int:
    errors: list[str] = []
    request = load_json(REQUEST)
    attempt = load_json(ATTEMPT)
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256,
        "locked V9 source hash drifted")
    add(errors, attempt.get("source_reference_sha256") == LOCKED_V9_SHA256,
        "attempt lost locked V9 lineage")
    add(errors, attempt.get("grid", {}).get("row_major_emotions") == list(EMOTIONS),
        "attempt emotion order drifted")
    add(errors, attempt.get("runtime_resource_activated") is False and
        attempt.get("active_candidate_binding") == "forbidden",
        "V21 candidate must remain runtime inactive and unbound")
    generated = ROOT / str(attempt.get("generated_image", ""))
    add(errors, generated.is_file(), "V21 generated source image is missing")
    image_metrics: list[dict[str, object]] = []
    pairwise: list[dict[str, object]] = []
    anti_alias_fraction = 1.0
    if generated.is_file():
        add(errors, sha256(generated) == attempt.get("generated_image_sha256"),
            "V21 generated source hash drifted")
        with Image.open(generated) as raw:
            image = raw.convert("L")
        width, height = image.size
        add(errors, (width, height) == (1254, 1254), "V21 source must remain the recorded square image size")
        gray_values = list(image.getdata())
        nonwhite = [value for value in gray_values if value < 245]
        anti_alias_fraction = (sum(16 <= value <= 239 for value in nonwhite) / len(nonwhite)) if nonwhite else 1.0
        add(errors, anti_alias_fraction <= MAX_THRESHOLD_SAFE_ANTIALIAS_FRACTION,
            "V21 source has too much soft edge content for deterministic threshold extraction")
        normalized: list[tuple[str, list[int]]] = []
        for index, emotion in enumerate(EMOTIONS):
            box = cell_box(index, width, height)
            binary = binary_crop(image, box)
            bbox = binary.getbbox()
            ink_pixels = sum(value == 255 for value in binary.getdata())
            cell_width, cell_height = binary.size
            add(errors, bbox is not None, f"{emotion} has no extractable ink")
            if bbox is not None:
                left, top, right, bottom = bbox
                add(errors, left >= 35 and top >= 60 and right <= cell_width - 10 and bottom <= cell_height - 40,
                    f"{emotion} source pose touches a grid edge")
            add(errors, MIN_POSE_INK_PIXELS <= ink_pixels <= MAX_POSE_INK_PIXELS,
                f"{emotion} ink coverage is outside the source-pose range")
            reduced = binary.resize((200, 200), Image.Resampling.NEAREST)
            normalized.append((emotion, list(reduced.getdata())))
            image_metrics.append({
                "emotion": emotion,
                "grid_box": list(box),
                "ink_bbox": list(bbox) if bbox is not None else None,
                "ink_pixels": ink_pixels,
            })
        for (left_name, left_pixels), (right_name, right_pixels) in combinations(normalized, 2):
            difference = sum(left != right for left, right in zip(left_pixels, right_pixels))
            add(errors, MIN_PAIRWISE_NORMALIZED_DIFFERENCE <= difference <= MAX_PAIRWISE_NORMALIZED_DIFFERENCE,
                f"{left_name}->{right_name} distinction is outside the same-character source range")
            pairwise.append({"left": left_name, "right": right_name, "normalized_difference_pixels": difference})
    prompt = str(request.get("prompt_delta", ""))
    add(errors, all(name.title() in prompt for name in EMOTIONS),
        "V21 prompt lineage does not name all six emotions")
    result = {
        "schema": "companion.v21_everyday_emotion_distinction_source_gate.v1",
        "status": "PASS_V21_EVERYDAY_EMOTION_DISTINCTION_SOURCE_GATE_PENDING_OWNER_ART_REVIEW" if not errors else
                  "FAIL_V21_EVERYDAY_EMOTION_DISTINCTION_SOURCE_GATE",
        "generation_request": REQUEST.relative_to(ROOT).as_posix(),
        "attempt": ATTEMPT.relative_to(ROOT).as_posix(),
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "generated_image": attempt.get("generated_image"),
        "generated_image_sha256": attempt.get("generated_image_sha256"),
        "threshold": {
            "ink_value_lt": INK_THRESHOLD,
            "anti_alias_fraction": anti_alias_fraction,
            "max_threshold_safe_anti_alias_fraction": MAX_THRESHOLD_SAFE_ANTIALIAS_FRACTION,
        },
        "poses": image_metrics,
        "pairwise_distinction": pairwise,
        "component_export": "forbidden_pending_owner_art_review",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    DEFAULT_WRITE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V21 source sheet has six threshold-safe, distinct same-character emotion poses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
