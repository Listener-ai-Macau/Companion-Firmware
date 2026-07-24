#!/usr/bin/env python3
"""Classify the locked v9 idle frames without mistaking a whole-face shift for animation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-render-report.json"
OUTPUT = ROOT / "docs/validation/companion-v9-idle-motion-analysis-20260717.json"
EXPECTED_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PHASES = ("entry", "sustain", "settle")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_idle_frames() -> list[dict[str, object]]:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("source_sha256") != EXPECTED_SOURCE_SHA256:
        raise ValueError("locked v9 source hash drifted")
    frames = [frame for frame in report.get("frames", []) if frame.get("clip") == "idle"]
    if [frame.get("phase") for frame in frames] != list(PHASES):
        raise ValueError("idle phases must remain entry, sustain, settle in order")
    for frame in frames:
        path = ROOT / str(frame["path"])
        if sha256(path) != frame.get("sha256"):
            raise ValueError(f"PBM hash drifted: {frame['path']}")
        if frame.get("source_sha256") != EXPECTED_SOURCE_SHA256:
            raise ValueError("idle frame is not from the locked v9 source")
        if tuple(frame.get("final_output_bounds", [])) != tuple(frame.get("dirty", [])):
            raise ValueError("idle frame dirty bounds and output bounds disagree")
    return frames


def analyze() -> dict[str, object]:
    frames = load_idle_frames()
    source_crops = {tuple(frame["source_crop_box"]) for frame in frames}
    offsets = [tuple(frame["phase_offset"]) for frame in frames]
    unique_hashes = {str(frame["sha256"]) for frame in frames}
    global_translation_only = len(source_crops) == 1 and len(unique_hashes) == 2 and offsets[0] == offsets[2]
    multi_feature_ready = not global_translation_only and len(unique_hashes) == 3
    return {
        "schema": "companion.v9_idle_motion_analysis.v1",
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "clip": "idle",
        "phases": [
            {
                "phase": frame["phase"],
                "pbm": frame["path"],
                "sha256": frame["sha256"],
                "source_crop_box": frame["source_crop_box"],
                "phase_offset": frame["phase_offset"],
                "bounds": frame["final_output_bounds"],
            }
            for frame in frames
        ],
        "global_translation_only": global_translation_only,
        "multi_feature_daily_motion_ready": multi_feature_ready,
        "status": (
            "REWORK_ART_GLOBAL_TRANSLATION_ONLY"
            if global_translation_only
            else "PASS_CANDIDATE_MULTI_FRAME_ART_REQUIRES_FEATURE_MASK_REVIEW"
        ),
        "next_required_art": (
            "Create a versioned v9 motion extension where eye/highlight or gaze changes and "
            "at least one brow, mouth, cheek, or ornament also changes; retain the same identity."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the deterministic analysis artifact")
    parser.add_argument("--require-multi-feature", action="store_true",
                        help="fail unless the current three frames are true multi-feature motion art")
    args = parser.parse_args()
    analysis = analyze()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(analysis, indent=2) + "\n", encoding="ascii")
    print(f"{analysis['status']}: {OUTPUT.relative_to(ROOT)}")
    if args.require_multi_feature and not analysis["multi_feature_daily_motion_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
