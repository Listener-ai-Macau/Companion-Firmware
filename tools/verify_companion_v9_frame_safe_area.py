#!/usr/bin/env python3
"""Verify every inactive v9 PBM frame keeps a physical-panel safety margin."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9"
MANIFEST = ART_DIR / "rendered-200x200" / "v9-expression-cemp-manifest.json"
SOURCE = ART_DIR / "generated_pet_expression_sheet_v9_candidate.png"
REPORT = ROOT / "docs" / "validation" / "companion-v9-frame-safe-area-20260717.json"
EXPECTED_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
FRAME_SIZE = (200, 200)
MIN_EDGE_CLEARANCE_PX = 4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def frame_clearance(path: Path) -> dict[str, object]:
    bitmap = Image.open(path).convert("1")
    if bitmap.size != FRAME_SIZE:
        raise ValueError(f"{path.name} is {bitmap.size}, expected {FRAME_SIZE}")
    pixels = bitmap.load()
    ink = [(x, y) for y in range(bitmap.height) for x in range(bitmap.width) if pixels[x, y] == 0]
    if not ink:
        raise ValueError(f"{path.name} has no visible ink")
    xs, ys = zip(*ink)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    clearance = {
        "left": left,
        "top": top,
        "right": bitmap.width - 1 - right,
        "bottom": bitmap.height - 1 - bottom,
    }
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "ink_bbox": [left, top, right - left + 1, bottom - top + 1],
        "edge_clearance_px": clearance,
        "minimum_clearance_px": min(clearance.values()),
    }


def build_report() -> dict[str, object]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    source_hash = sha256(SOURCE) if SOURCE.is_file() else None
    if source_hash is None:
        errors.append("v9 source is missing")
    elif source_hash != EXPECTED_SOURCE_SHA256:
        errors.append("v9 source hash drifted")
    if manifest.get("profile", {}).get("width") != 200 or manifest.get("profile", {}).get("height") != 200:
        errors.append("v9 manifest no longer targets 200x200")
    if manifest.get("provenance", {}).get("runtime_resource_activated") is not False:
        errors.append("safe-area check must not imply runtime activation")

    frames: list[dict[str, object]] = []
    for clip in manifest.get("clips", []):
        for frame in clip.get("frames", []):
            source = ART_DIR / "rendered-200x200" / str(frame.get("source", ""))
            try:
                result = frame_clearance(source)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                continue
            result["clip"] = clip.get("name")
            if int(result["minimum_clearance_px"]) < MIN_EDGE_CLEARANCE_PX:
                errors.append(
                    f"{result['path']} has only {result['minimum_clearance_px']} px edge clearance"
                )
            frames.append(result)

    if len(frames) != 39:
        errors.append(f"expected 39 v9 frames, checked {len(frames)}")
    return {
        "schema": "companion.v9_frame_safe_area.v1",
        "status": "PASS_MACHINE_SAFE_AREA_PHYSICAL_REVIEW_PENDING" if not errors else "FAIL",
        "source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": source_hash,
        },
        "frame_profile": {"width": 200, "height": 200, "minimum_edge_clearance_px": MIN_EDGE_CLEARANCE_PX},
        "frame_count": len(frames),
        "frames": frames,
        "runtime_resource_activated": False,
        "physical_panel_review": "PENDING: a machine margin cannot prove panel orientation, viewport offsets, or lower-edge truncation.",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the deterministic safe-area report.")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        REPORT.write_text(rendered, encoding="utf-8")
    elif not REPORT.is_file() or REPORT.read_text(encoding="utf-8") != rendered:
        report["errors"].append(f"stale {REPORT.relative_to(ROOT).as_posix()}")
    if report["errors"]:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        return 1
    print("PASS: all 39 inactive v9 frames retain at least 4 px of canvas clearance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
