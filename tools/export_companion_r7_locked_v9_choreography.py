#!/usr/bin/env python3
"""Export a deterministic, production-off R7 package from the COMP-REQ-402 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from companion_expression_anchor import ANCHOR_POLICY, CANONICAL_CENTER, output_bounds


ROOT = Path(__file__).resolve().parents[1]
REPORT_DEFAULT = ROOT / ".cache/validation/companion-v45-centered-gallery-r1-20260723/render-report.json"
SOURCE_DEFAULT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01"
OUTPUT_DEFAULT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/r7-locked-v9-export-20260723"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def safe(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def selected_specs() -> list[dict[str, str]]:
    return [
        {"story": "calm_presence", "cue": "calm_entry", "emotion": "calm", "role": "center_entry", "reason": "neutral baseline enters"},
        {"story": "daily_attention_right", "cue": "gaze_right_arrive", "emotion": "curious", "role": "gaze_arrive", "reason": "rightward gaze arrives as a changed frame"},
        {"story": "curious_question", "cue": "question_entry", "emotion": "curious", "role": "expression_entry", "reason": "curious face enters"},
        {"story": "curious_question", "cue": "question_brow_lead", "emotion": "curious", "role": "brow_lead", "reason": "registered brow component leads"},
        {"story": "curious_question", "cue": "question_mouth_arrive", "emotion": "curious", "role": "mouth_arrive", "reason": "registered mouth component arrives"},
        {"story": "curious_question", "cue": "question_hold", "emotion": "curious", "role": "expression_hold", "reason": "curious apex remains visible once"},
        {"story": "warm_presence", "cue": "warm_entry", "emotion": "affectionate", "role": "expression_entry", "reason": "warm face enters"},
        {"story": "warm_presence", "cue": "warm_brow_lead", "emotion": "affectionate", "role": "brow_lead", "reason": "registered warm brow leads"},
        {"story": "warm_presence", "cue": "warm_smile_arrive", "emotion": "affectionate", "role": "mouth_arrive", "reason": "registered smile arrives"},
        {"story": "delighted_presence", "cue": "delighted_entry", "emotion": "joyful", "role": "cheek_decoration_entry", "reason": "registered joyful cheek/decoration enters"},
        {"story": "delighted_presence", "cue": "delighted_brow_lead", "emotion": "joyful", "role": "cheek_decoration_attack", "reason": "registered joyful brow and cheek/decoration attack"},
        {"story": "delighted_presence", "cue": "delighted_mouth_arrive", "emotion": "joyful", "role": "cheek_decoration_hold", "reason": "registered joyful mouth/cheek apex remains visible once"},
        {"story": "bashful_presence", "cue": "bashful_entry", "emotion": "bashful", "role": "expression_attack", "reason": "registered bashful emotion change"},
        {"story": "bashful_presence", "cue": "bashful_brow_lead", "emotion": "bashful", "role": "brow_lead", "reason": "registered bashful brow attack"},
        {"story": "focused_presence", "cue": "focused_mouth_arrive", "emotion": "focused", "role": "expression_attack", "reason": "registered focused mouth attack"},
        {"story": "warm_presence", "cue": "warm_settle", "emotion": "affectionate", "role": "return_settle", "reason": "registered recovery frame before loop return"},
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    source_dir = args.source_dir if args.source_dir.is_absolute() else ROOT / args.source_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    report = json.loads(report_path.read_text(encoding="utf-8"))
    frames = report["frames"]
    frame_index = {(frame["score"], frame["cue"]): frame for frame in frames}
    output_dir.mkdir(parents=True, exist_ok=True)
    all_dir = output_dir / "all-candidates"
    plan_dir = output_dir / "component-plans"
    all_dir.mkdir(exist_ok=True)
    plan_dir.mkdir(exist_ok=True)

    all_candidates: list[dict[str, Any]] = []
    for frame in frames:
        key = (frame["score"], frame["cue"])
        source = source_dir / frame["pbm"]
        if not source.is_file():
            raise FileNotFoundError(source)
        story_dir = all_dir / safe(frame["score"])
        story_plan_dir = plan_dir / safe(frame["score"])
        story_dir.mkdir(exist_ok=True)
        story_plan_dir.mkdir(exist_ok=True)
        target = story_dir / f'{frame["index"]:02d}-{safe(frame["cue"])}.pbm'
        shutil.copyfile(source, target)
        with Image.open(target) as image:
            bitmap = image.convert("1")
            preview = story_dir / f'{frame["index"]:02d}-{safe(frame["cue"])}.png'
            bitmap.save(preview, format="PNG", optimize=False, compress_level=9)
            actual_bounds = list(output_bounds(bitmap))
        plan = {
            "schema": "companion.r7.locked_v9.component_plan.v1",
            "story": frame["score"], "cue": frame["cue"], "phase": frame["phase"],
            "duration_ms": frame["duration_ms"], "index": frame["index"],
            "source_frame": rel(source), "source_pbm_sha256": sha256(source),
            "exported_pbm": rel(target), "exported_pbm_sha256": sha256(target),
            "preview_png": rel(preview), "preview_png_sha256": sha256(preview),
            "anchor_policy": frame["anchor_policy"], "canonical_center": frame["canonical_center"],
            "source_anchor": frame["source_anchor"], "normalization_offset": frame["normalization_offset"],
            "source_bounds": frame["source_bounds"], "output_bounds": actual_bounds,
            "source_1bpp_sha256": frame["source_1bpp_sha256"],
            "derived_1bpp_sha256": frame["derived_1bpp_sha256"],
            "layers": frame["layers"], "source_linkage": {"report": rel(report_path), "report_frame_key": list(key)},
        }
        plan_path = story_plan_dir / f'{frame["index"]:02d}-{safe(frame["cue"])}.json'
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        all_candidates.append({"story": frame["score"], "cue": frame["cue"], "phase": frame["phase"],
                              "index": frame["index"], "pbm": rel(target), "plan": rel(plan_path),
                              "source_pbm": rel(source), "source_pbm_sha256": sha256(source),
                              "exported_pbm_sha256": sha256(target), "anchor_policy": frame["anchor_policy"],
                              "canonical_center": frame["canonical_center"], "source_bounds": frame["source_bounds"],
                              "output_bounds": actual_bounds, "source_anchor": frame["source_anchor"],
                              "normalization_offset": frame["normalization_offset"],
                              "layers": frame["layers"]})

    chosen: list[dict[str, Any]] = []
    phase_by_role = {
        "center_entry": "gaze_lead", "gaze_depart": "gaze_lead", "gaze_arrive": "gaze_lead", "gaze_hold": "gaze_lead",
        "expression_entry": "expression_attack", "expression_attack": "expression_attack", "brow_lead": "expression_attack", "mouth_arrive": "expression_attack",
        "cheek_decoration_attack": "expression_attack",
        "expression_hold": "apex_hold", "cheek_decoration_entry": "expression_attack", "cheek_decoration_hold": "apex_hold",
        "expression_settle": "settle_recovery", "return_settle": "settle_recovery",
    }
    for transition_index, spec in enumerate(selected_specs(), start=1):
        frame = frame_index.get((spec["story"], spec["cue"]))
        if frame is None:
            raise ValueError(f'missing selected frame: {spec["story"]}/{spec["cue"]}')
        candidate = next(item for item in all_candidates if item["story"] == frame["score"] and item["cue"] == frame["cue"])
        graph_phase = phase_by_role[spec["role"]]
        chosen.append({"transition": transition_index, **spec, "graph_phase": graph_phase,
                       "tick_duration_ms": 470 if graph_phase == "apex_hold" else frame["duration_ms"],
                       "complete_frame_per_tick": True, "story": frame["score"], "cue": frame["cue"],
                       "phase": frame["phase"], "duration_ms": frame["duration_ms"], "frame_index": frame["index"],
                       "pbm": candidate["pbm"], "plan": candidate["plan"], "source_pbm": candidate["source_pbm"],
                       "source_pbm_sha256": candidate["source_pbm_sha256"], "exported_pbm_sha256": candidate["exported_pbm_sha256"],
                       "normalization_offset": candidate["normalization_offset"], "source_anchor": candidate["source_anchor"],
                       "layers": candidate["layers"]})

    owner_visible_names = list(report.get("chinese_overview", {}).get("owner_visible_scores", []))
    manifest = {
        "schema": "companion.r7.locked_v9.export.v1", "status": "EXPORT_COMPLETE_PRODUCTION_OFF",
        "source_baseline": {"report": rel(report_path), "report_sha256": sha256(report_path),
                             "canonical_candidate_dir": rel(source_dir), "canonical_candidate_files_unchanged": True},
        "canvas": {"width": 200, "height": 200, "format": "PBM P4 1bpp", "anchor_policy": ANCHOR_POLICY,
                    "canonical_center": list(CANONICAL_CENTER)},
        "locked_sources": {"v22_layout": rel(V22_LAYOUT), "v22_layout_sha256": sha256(V22_LAYOUT),
                            "locked_v9_source_sha256": report["locked_v9_source_sha256"]},
        "candidate_count": len(all_candidates), "owner_visible_story_count": len(owner_visible_names),
        "owner_visible_stories": owner_visible_names,
        "supporting_story_count": len({item["story"] for item in all_candidates} - set(owner_visible_names)),
        "all_candidates": all_candidates, "transition_count": len(chosen), "transitions": chosen,
        "adopted_rules": {
            "source_requirement": "one_complete_locked_v9_200x200_1bpp_frame_per_physical_tick",
            "finite_phase_graph": ["gaze_lead", "expression_attack", "apex_hold", "settle_recovery"],
            "apex_hold_interval_ms": 470, "duplicate_identical_activation_or_dwell": False,
            "every_tick_must_change_frame": True, "white_listed_intermediate_max": 1,
            "white_listed_intermediate_settles_on_next_frame": True,
            "priority": ["cleanup_safety", "touch", "semantic_emotion", "idle"],
            "idle_policy": "fixed_index", "randomness": False, "interpolation_30_60fps": False,
            "continuous_geometry_mutation": False, "runtime_drawing": False, "external_code_or_assets": [],
            "double_face": False, "transient_residue": False,
            "blink_highlight_sparkle": "bounded_source_backed_components_only",
        },
        "white_listed_intermediate_count": 0,
        "non_claims": ["no lower-driver change", "no menu or production integration", "no hardware or Git staging", "R6 fit is verified separately"],
    }
    (output_dir / "r7-export-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (output_dir / "r7-transition-graph.json").write_text(json.dumps({"schema": "companion.r7.transition_graph.v1", "transitions": chosen}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"PASS: exported {len(all_candidates)} owner-visible candidate frames and {len(chosen)} deterministic transitions -> {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
