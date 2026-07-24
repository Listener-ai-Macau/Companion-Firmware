#!/usr/bin/env python3
"""Gate a generated V15 sleep Rig pose sheet before component extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTEMPT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v15-sleep-rig-pose-source/candidate/attempt-01-generated-pose-sheet.json"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ink_count(image: Image.Image) -> int:
    return sum(pixel < 96 for pixel in image.convert("L").getdata())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, default=DEFAULT_ATTEMPT)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    attempt_path = args.attempt.resolve()
    errors: list[str] = []
    cells: list[dict[str, object]] = []
    try:
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        if attempt.get("schema") != "companion.v15_sleep_rig_pose_generation_attempt.v1" or attempt.get("status") not in {"PENDING_MACHINE_SOURCE_GATE", "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT"}:
            errors.append("V15 generation attempt disposition drifted")
        if attempt.get("source_reference_sha256") != LOCKED_V9_SHA256:
            errors.append("V15 attempt does not record the locked V9 source")
        if attempt.get("runtime_resource_activated") is not False or attempt.get("active_candidate_binding") != "forbidden" or attempt.get("component_export") not in {"forbidden_pending_machine_source_gate", "pending_source_mask_export"}:
            errors.append("V15 attempt has an illegal runtime disposition")
        image_path = ROOT / str(attempt.get("generated_image", ""))
        if not image_path.is_file() or attempt.get("generated_image_sha256") != sha256(image_path):
            errors.append("V15 generated image is missing or hash drifted")
            image = None
        else:
            image = Image.open(image_path).convert("L")
        if image is not None:
            if image.width != image.height or image.width < 800:
                errors.append("V15 generated source is not a sufficiently large square pose sheet")
            half_x, half_y = image.width // 2, image.height // 2
            names = ("sleep_rest_anchor", "sleep_brow_settle", "sleep_lower_face_breath", "sleep_rest_return")
            for index, name in enumerate(names):
                column, row = index % 2, index // 2
                left, top = column * half_x, row * half_y
                right = image.width if column else half_x
                bottom = image.height if row else half_y
                cell = image.crop((left, top, right, bottom))
                upper = cell.crop((0, 0, cell.width, cell.height // 3))
                zzz_cluster_region = cell.crop((int(cell.width * 0.55), 0, cell.width, int(cell.height * 0.42)))
                metrics = {"name": name, "ink_pixels": ink_count(cell), "upper_third_ink_pixels": ink_count(upper),
                           "upper_right_zzz_cluster_ink_pixels": ink_count(zzz_cluster_region)}
                cells.append(metrics)
                if metrics["ink_pixels"] < 700:
                    errors.append(f"V15 pose cell lacks a complete face: {name}")
                if metrics["upper_right_zzz_cluster_ink_pixels"] < 60:
                    errors.append(f"V15 pose cell lacks its required compact zzz cluster: {name}")
            border = []
            for box in ((0, 0, image.width, 3), (0, image.height - 3, image.width, image.height),
                        (0, 0, 3, image.height), (image.width - 3, 0, image.width, image.height)):
                border.extend(image.crop(box).getdata())
            if sum(pixel < 96 for pixel in border) > 40:
                errors.append("V15 generated source contains an illegal panel border")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(str(exc))
    result = {
        "schema": "companion.v15_sleep_rig_pose_source_gate.v1",
        "status": "PASS_V15_SLEEP_RIG_POSE_SOURCE_GATE" if not errors else "FAIL_V15_SLEEP_RIG_POSE_SOURCE_GATE",
        "attempt": attempt_path.relative_to(ROOT).as_posix(),
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "component_export": "forbidden" if errors else "pending_owner_art_and_component_export",
        "cell_metrics": cells,
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V15 generated pose source satisfies the extraction preflight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
