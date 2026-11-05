#!/usr/bin/env python3
"""Promote an owner-approved v9 Rig dynamic preview into a regression baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
from datetime import datetime, timezone

from verify_companion_v9_expression_rig_dynamic_preview import LOCKED_SOURCE_HASH, story_phase_frames


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OWNER_SUMMARY = ROOT / "docs/validation/companion-v9-expression-rig-dynamic-owner-review-summary-20260717.json"
DEFAULT_PREVIEW_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-dynamic-preview-20260717.json"
DEFAULT_DISTANCE_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-preview-distance-20260717.json"
DEFAULT_RENDER_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-render-20260717.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-rig-accepted-dynamic-baseline.json"
DEFAULT_ARTIFACT_DIR = ROOT / "docs/validation/artifacts/companion-v9-expression-rig-accepted-dynamic-baseline"
PHASES = ("entry", "sustain", "settle")


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def copy_file(source: pathlib.Path, destination: pathlib.Path) -> dict[str, object]:
    require(source.is_file(), f"missing artifact to copy: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "path": rel(destination),
        "sha256": sha256(destination),
        "bytes": destination.stat().st_size,
    }


def sorted_strings(value: object) -> list[str]:
    return sorted(str(item) for item in value) if isinstance(value, list) else []


def existing_matches_current(existing: dict[str, object],
                             preview: dict[str, object]) -> bool:
    if existing.get("schema") != "companion.v9_expression_rig_accepted_dynamic_baseline.v1":
        return False
    if existing.get("status") != "ACCEPTED_DYNAMIC_BASELINE":
        return False
    if existing.get("source_sha256") != preview.get("source_sha256"):
        return False
    if existing.get("component_layer_count") != preview.get("component_layer_count"):
        return False
    if sorted_strings(existing.get("stories")) != sorted_strings(preview.get("stories")):
        return False
    if sorted_strings(existing.get("dynamic_groups")) != sorted_strings(preview.get("dynamic_groups")):
        return False
    artifacts = existing.get("artifacts") if isinstance(existing.get("artifacts"), dict) else {}
    for name, report_key in (
        ("review_page", "review_page_sha256"),
        ("owner_review_page", "owner_review_page_sha256"),
        ("animated_preview", "animated_preview_sha256"),
        ("keyframe_strip", "keyframe_strip_sha256"),
    ):
        artifact = artifacts.get(name) if isinstance(artifacts.get(name), dict) else {}
        if artifact.get("sha256") != preview.get(report_key):
            return False
    return True


def validate_inputs(summary: dict[str, object],
                    preview: dict[str, object],
                    distance: dict[str, object],
                    render: dict[str, object]) -> None:
    require(summary.get("schema") == "companion.v9_expression_rig_owner_review_summary.v1",
            "owner summary schema is not the dynamic owner review summary")
    require(summary.get("status") == "PASS_OWNER_REVIEW" and summary.get("selected") == "通过",
            "owner summary is not a canonical PASS")
    require(summary.get("source_sha256") == LOCKED_SOURCE_HASH,
            "owner summary source hash is not the locked v9 source")
    require(summary.get("runtime_resource_activated") is False,
            "owner-approved dynamic baseline must remain runtime inactive")
    require(summary.get("preview_distance_status") == "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT",
            "owner summary did not record a passing preview-distance gate")

    require(preview.get("schema") == "companion.v9_expression_rig_dynamic_preview.v1",
            "dynamic preview report schema is unexpected")
    require(preview.get("status") == "PASS_DYNAMIC_COMPONENT_PREVIEW_READY",
            "dynamic preview report is not PASS")
    require(distance.get("schema") == "companion.v9_expression_rig_preview_distance.v1",
            "preview-distance report schema is unexpected")
    require(distance.get("status") == "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT",
            "preview-distance report is not PASS")
    require(render.get("schema") == "companion.v9_expression_rig_render.v1",
            "Rig render report schema is unexpected")
    require(render.get("status") == "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW",
            "Rig render report is not PASS pending owner review")

    for label, report in (("preview", preview), ("distance", distance), ("render", render)):
        require(report.get("source_sha256") == LOCKED_SOURCE_HASH,
                f"{label} report source hash is not the locked v9 source")
        require(report.get("runtime_resource_activated") is False,
                f"{label} report must remain runtime inactive")


def build_manifest(owner_summary_path: pathlib.Path,
                   owner_result_path: pathlib.Path | None,
                   preview_report_path: pathlib.Path,
                   distance_report_path: pathlib.Path,
                   render_report_path: pathlib.Path,
                   artifact_dir: pathlib.Path,
                   allow_replace: bool,
                   write_path: pathlib.Path) -> dict[str, object]:
    summary = load_json(owner_summary_path)
    preview = load_json(preview_report_path)
    distance = load_json(distance_report_path)
    render = load_json(render_report_path)
    validate_inputs(summary, preview, distance, render)

    if write_path.exists() and not allow_replace:
        existing = load_json(write_path)
        if existing_matches_current(existing, preview):
            return existing
        raise ValueError(
            f"accepted dynamic baseline already exists and differs: {write_path}; "
            "use --allow-replace only after a new owner PASS intentionally supersedes it"
        )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "review_page": copy_file(ROOT / str(preview.get("review_page", "")), artifact_dir / "v9-expression-rig-dynamic-player.html"),
        "owner_review_page": copy_file(ROOT / str(preview.get("owner_review_page", "")), artifact_dir / "v9-expression-rig-owner-review.html"),
        "animated_preview": copy_file(ROOT / str(preview.get("animated_preview", "")), artifact_dir / "v9-expression-rig-dynamic-preview.gif"),
        "keyframe_strip": copy_file(ROOT / str(preview.get("keyframe_strip", "")), artifact_dir / "v9-expression-rig-dynamic-keyframes.png"),
    }

    source_layer_dir = ROOT / str(preview.get("component_layer_dir", ""))
    require(source_layer_dir.is_dir(), "dynamic preview component layer directory is missing")
    target_layer_dir = artifact_dir / "dynamic-review-layers"
    target_layer_dir.mkdir(parents=True, exist_ok=True)
    component_layers: list[dict[str, object]] = []
    for source in sorted(source_layer_dir.glob("*.png")):
        copied = copy_file(source, target_layer_dir / source.name)
        copied["component"] = source.stem
        component_layers.append(copied)
    require(len(component_layers) == int(preview.get("component_layer_count", -1)),
            "component layer count does not match dynamic preview report")

    story_phases = story_phase_frames(render)
    story_phase_artifacts: list[dict[str, object]] = []
    for story in sorted_strings(preview.get("stories")):
        require(story in story_phases, f"render report is missing story: {story}")
        for phase in PHASES:
            frame = story_phases[story].get(phase)
            require(frame is not None, f"render report is missing story phase: {story}/{phase}")
            source = ROOT / str(frame.get("path", ""))
            copied = copy_file(source, artifact_dir / "story-phases" / f"{story}_{phase}.pbm")
            copied.update({
                "story": story,
                "phase": phase,
                "frame_sha256": frame.get("sha256"),
                "layer_count": len(frame.get("layers", [])) if isinstance(frame.get("layers"), list) else 0,
            })
            require(copied["sha256"] == frame.get("sha256"),
                    f"copied story phase hash drifted: {story}/{phase}")
            story_phase_artifacts.append(copied)

    owner_result: dict[str, object] | None = None
    if owner_result_path is not None and owner_result_path.is_file():
        owner_result = {
            "path": rel(owner_result_path),
            "sha256": sha256(owner_result_path),
        }

    manifest = {
        "schema": "companion.v9_expression_rig_accepted_dynamic_baseline.v1",
        "status": "ACCEPTED_DYNAMIC_BASELINE",
        "accepted_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "owner_review": {
            "summary_path": rel(owner_summary_path),
            "result": owner_result,
            "status": summary.get("status"),
            "selected": summary.get("selected"),
            "text": summary.get("text"),
        },
        "preview_report": {
            "path": rel(preview_report_path),
            "sha256": sha256(preview_report_path),
        },
        "preview_distance_report": {
            "path": rel(distance_report_path),
            "sha256": sha256(distance_report_path),
        },
        "render_report": {
            "path": rel(render_report_path),
            "sha256": sha256(render_report_path),
        },
        "artifacts": artifacts,
        "component_layer_dir": rel(target_layer_dir),
        "component_layer_count": preview.get("component_layer_count"),
        "component_layers": component_layers,
        "story_count": preview.get("story_count"),
        "stories": sorted_strings(preview.get("stories")),
        "dynamic_groups": sorted_strings(preview.get("dynamic_groups")),
        "distance_records": distance.get("distance_records"),
        "story_phase_frames": story_phase_artifacts,
        "max_allowed_pixel_distance_for_regression": 0,
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-summary", type=pathlib.Path, default=DEFAULT_OWNER_SUMMARY)
    parser.add_argument("--owner-result", type=pathlib.Path)
    parser.add_argument("--preview-report", type=pathlib.Path, default=DEFAULT_PREVIEW_REPORT)
    parser.add_argument("--distance-report", type=pathlib.Path, default=DEFAULT_DISTANCE_REPORT)
    parser.add_argument("--render-report", type=pathlib.Path, default=DEFAULT_RENDER_REPORT)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--allow-replace", action="store_true")
    args = parser.parse_args()

    try:
        manifest = build_manifest(
            args.owner_summary.resolve(),
            args.owner_result.resolve() if args.owner_result is not None else None,
            args.preview_report.resolve(),
            args.distance_report.resolve(),
            args.render_report.resolve(),
            args.artifact_dir.resolve(),
            args.allow_replace,
            args.write.resolve(),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1

    write_json(args.write.resolve(), manifest)
    print(f"PASS: accepted v9 Rig dynamic baseline recorded at {rel(args.write.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
