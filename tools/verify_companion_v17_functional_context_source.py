#!/usr/bin/env python3
"""Gate the V17 V9-only functional-context source panel before extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTEMPT = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-extension-v17-functional-context-accents/"
    "candidate/attempt-01-generated-functional-context-accent-panel.json"
)
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EXPECTED_GROUPS = ("menu_active", "recording_active", "upgrade_active")
INK_THRESHOLD = 128


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def connected_components(image: Image.Image) -> list[dict[str, Any]]:
    mono = image.convert("L")
    width, height = mono.size
    pixels = mono.load()
    seen = bytearray(width * height)
    components: list[dict[str, Any]] = []
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if seen[index] or pixels[x, y] >= INK_THRESHOLD:
                continue
            seen[index] = 1
            queue: deque[tuple[int, int]] = deque([(x, y)])
            area = 0
            min_x = max_x = x
            min_y = max_y = y
            while queue:
                current_x, current_y = queue.popleft()
                area += 1
                min_x = min(min_x, current_x)
                max_x = max(max_x, current_x)
                min_y = min(min_y, current_y)
                max_y = max(max_y, current_y)
                for next_x, next_y in (
                    (current_x - 1, current_y), (current_x + 1, current_y),
                    (current_x, current_y - 1), (current_x, current_y + 1),
                ):
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    next_index = next_y * width + next_x
                    if not seen[next_index] and pixels[next_x, next_y] < INK_THRESHOLD:
                        seen[next_index] = 1
                        queue.append((next_x, next_y))
            if area >= 20:
                components.append({
                    "ink_pixels": area,
                    "crop": [min_x, min_y, max_x + 1, max_y + 1],
                    "center": [(min_x + max_x + 1) / 2, (min_y + max_y + 1) / 2],
                })
    return components


def border_ink(image: Image.Image) -> int:
    mono = image.convert("L")
    width, height = mono.size
    strips = (
        mono.crop((0, 0, width, 5)), mono.crop((0, height - 5, width, height)),
        mono.crop((0, 0, 5, height)), mono.crop((width - 5, 0, width, height)),
    )
    return sum(pixel < INK_THRESHOLD for strip in strips for pixel in strip.getdata())


def split_groups(components: list[dict[str, Any]], width: int) -> dict[str, list[dict[str, Any]]]:
    return {
        "menu_active": [item for item in components if item["center"][0] < width * 0.33],
        "recording_active": [item for item in components if width * 0.33 <= item["center"][0] < width * 0.70],
        "upgrade_active": [item for item in components if item["center"][0] >= width * 0.70],
    }


def valid_menu_group(items: list[dict[str, Any]]) -> bool:
    if len(items) != 3:
        return False
    ordered = sorted(items, key=lambda item: item["center"][1])
    centers_x = [item["center"][0] for item in ordered]
    centers_y = [item["center"][1] for item in ordered]
    return max(centers_x) - min(centers_x) <= 8 and \
        all(centers_y[index + 1] - centers_y[index] >= 25 for index in range(2)) and \
        all(300 <= item["ink_pixels"] <= 700 for item in ordered)


def valid_recording_group(items: list[dict[str, Any]], width: int) -> bool:
    if len(items) != 4:
        return False
    left = sorted((item for item in items if item["center"][0] < width / 2), key=lambda item: item["center"][0])
    right = sorted((item for item in items if item["center"][0] >= width / 2), key=lambda item: item["center"][0])
    if len(left) != 2 or len(right) != 2:
        return False
    all_items = left + right
    vertical_spans = [item["crop"][3] - item["crop"][1] for item in all_items]
    centers_y = [item["center"][1] for item in all_items]
    return min(vertical_spans) >= 35 and max(centers_y) - min(centers_y) <= 12 and \
        left[0]["center"][0] < left[1]["center"][0] < right[0]["center"][0] < right[1]["center"][0]


def valid_upgrade_group(items: list[dict[str, Any]]) -> bool:
    if len(items) != 4:
        return False
    horizontal = [item for item in items if (item["crop"][2] - item["crop"][0]) > (item["crop"][3] - item["crop"][1])]
    vertical = [item for item in items if (item["crop"][2] - item["crop"][0]) <= (item["crop"][3] - item["crop"][1])]
    if len(horizontal) != 2 or len(vertical) != 2:
        return False
    top, bottom = sorted(horizontal, key=lambda item: item["center"][1])
    left, right = sorted(vertical, key=lambda item: item["center"][0])
    return top["center"][1] < left["center"][1] < bottom["center"][1] and \
        top["center"][1] < right["center"][1] < bottom["center"][1] and \
        left["center"][0] < top["center"][0] < right["center"][0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, default=DEFAULT_ATTEMPT)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    attempt_path = args.attempt.resolve()
    errors: list[str] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    metrics: dict[str, Any] = {}
    try:
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        if attempt.get("schema") != "companion.v17_functional_context_generation_attempt.v1" or \
                attempt.get("status") not in {"PENDING_MACHINE_SOURCE_GATE", "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT"}:
            errors.append("V17 generation attempt disposition drifted")
        if attempt.get("source_reference_sha256") != LOCKED_V9_SHA256:
            errors.append("V17 attempt does not record the locked V9 source")
        if attempt.get("requested_context_groups") != list(EXPECTED_GROUPS):
            errors.append("V17 attempt context-group vocabulary drifted")
        if attempt.get("runtime_resource_activated") is not False or \
                attempt.get("active_candidate_binding") != "forbidden" or \
                attempt.get("component_export") not in {
                    "forbidden_pending_machine_source_gate", "pending_source_mask_export"
                }:
            errors.append("V17 attempt has an illegal runtime disposition")
        request_path = ROOT / str(attempt.get("generation_request", ""))
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if request.get("status") != "PROMPT_VERSIONED_PENDING_GENERATION" or \
                request.get("named_visible_variable") != "functional-context accent vocabulary only; no face component may be changed":
            errors.append("V17 versioned request contract drifted")
        references = request.get("reference_images")
        if not isinstance(references, list) or len(references) != 1 or \
                references[0].get("sha256") != LOCKED_V9_SHA256:
            errors.append("V17 request is not locked-V9-only")
        image_path = ROOT / str(attempt.get("generated_image", ""))
        if not image_path.is_file() or attempt.get("generated_image_sha256") != sha256(image_path):
            errors.append("V17 generated image is missing or hash drifted")
            image = None
        else:
            image = Image.open(image_path).convert("L")
        if image is not None:
            if image.width != image.height or image.width < 800:
                errors.append("V17 generated source is not a sufficiently large square panel")
            components = connected_components(image)
            groups = split_groups(components, image.width)
            metrics = {
                "image_size": [image.width, image.height],
                "ink_pixels": sum(item["ink_pixels"] for item in components),
                "border_ink_pixels": border_ink(image),
                "component_count": len(components),
                "groups": groups,
            }
            if len(components) != 11:
                errors.append("V17 source must contain exactly 11 extractable marks (3 menu, 4 recording, 4 upgrade)")
            if not 6000 <= metrics["ink_pixels"] <= 16000:
                errors.append("V17 source ink density is outside the sparse accent budget")
            if metrics["border_ink_pixels"] > 20:
                errors.append("V17 generated source contains an illegal panel border")
            if not valid_menu_group(groups["menu_active"]):
                errors.append("V17 menu source is not a compact extractable three-dot group")
            if not valid_recording_group(groups["recording_active"], image.width):
                errors.append("V17 recording source is not a symmetric four-mark ripple pair")
            if not valid_upgrade_group(groups["upgrade_active"]):
                errors.append("V17 upgrade source is not an independently extractable four-segment ring")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(str(exc))
    result = {
        "schema": "companion.v17_functional_context_source_gate.v1",
        "status": "PASS_V17_FUNCTIONAL_CONTEXT_SOURCE_GATE" if not errors else "FAIL_V17_FUNCTIONAL_CONTEXT_SOURCE_GATE",
        "attempt": attempt_path.relative_to(ROOT).as_posix(),
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "component_export": "pending_source_mask_export" if not errors else "forbidden",
        "metrics": metrics,
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V17 functional context source is V9-only, sparse, and independently extractable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
