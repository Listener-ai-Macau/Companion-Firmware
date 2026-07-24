#!/usr/bin/env python3
"""Exercise the source-derived v9 Rig twice and reject a card-like matrix."""

from __future__ import annotations

import json
import pathlib
import shutil
import tempfile

from PIL import Image

from promote_companion_v9_expression_rig_dynamic_baseline import (
    build_manifest,
    write_json,
)
from render_companion_v9_expression_rig import ROOT, load_rig, render
from render_companion_v9_expression_rig_dynamic_preview import (
    ComponentLayer,
    ScoreStep,
    render as render_dynamic_preview,
    selected_state_layers,
    validate_daily_reflection_score,
)
from verify_companion_v9_expression_rig import verify
from verify_companion_v9_expression_rig_dynamic_preview import (
    verify as verify_dynamic_preview,
)


LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
PREVIEW_DISTANCE_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-preview-distance-20260717.json"
LOCKED_SOURCE_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def render_once(directory: pathlib.Path) -> tuple[dict[str, object], pathlib.Path, pathlib.Path]:
    report = render(load_rig(LAYOUT), directory)
    report_path = directory / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    verification = verify(report_path)
    if verification["status"] != "PASS_MACHINE_CANDIDATE_NOT_ACTIVATED":
        raise AssertionError(verification["errors"])
    cemp_path = directory / "cemp.json"
    cemp_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="ascii")
    return report, report_path, cemp_path


def write_synthetic_owner_pass(directory: pathlib.Path, preview_report_path: pathlib.Path,
                               distance_report_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    summary_path = directory / "synthetic-owner-pass-summary.json"
    result_path = directory / "synthetic-owner-pass-result.json"
    preview = json.loads(preview_report_path.read_text(encoding="utf-8"))
    result_path.write_text(
        json.dumps({"selected": "通过", "text": "synthetic pipeline-only PASS"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_json(summary_path, {
        "schema": "companion.v9_expression_rig_owner_review_summary.v1",
        "status": "PASS_OWNER_REVIEW",
        "selected": "通过",
        "text": "synthetic pipeline-only PASS",
        "result_path": str(result_path.relative_to(ROOT)).replace("\\", "/"),
        "note_path": str((directory / "synthetic-owner-pass.note.txt").relative_to(ROOT)).replace("\\", "/"),
        "review_page": preview["owner_review_page"],
        "preview_distance": str(distance_report_path.relative_to(ROOT)).replace("\\", "/"),
        "preview_distance_status": "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT",
        "accepted_dynamic_baseline_path": str((directory / "accepted-dynamic-baseline.json").relative_to(ROOT)).replace("\\", "/"),
        "accepted_dynamic_baseline_status": "not_yet_accepted",
        "accepted_dynamic_baseline_promotion_status": "not_applicable",
        "source_sha256": LOCKED_SOURCE_HASH,
        "runtime_resource_activated": False,
        "goal_complete": False,
        "goal_completion_candidate": True,
        "goal_completion_requires_codex_audit": True,
    })
    return summary_path, result_path


def test_synthetic_accepted_dynamic_baseline(directory: pathlib.Path,
                                            preview_report_path: pathlib.Path,
                                            distance_report_path: pathlib.Path,
                                            render_report_path: pathlib.Path) -> None:
    summary_path, result_path = write_synthetic_owner_pass(
        directory, preview_report_path, distance_report_path,
    )
    baseline_path = directory / "accepted-dynamic-baseline.json"
    artifact_dir = directory / "accepted-dynamic-baseline-artifacts"
    manifest = build_manifest(
        summary_path,
        result_path,
        preview_report_path,
        distance_report_path,
        render_report_path,
        artifact_dir,
        False,
        baseline_path,
    )
    write_json(baseline_path, manifest)
    matched = verify_dynamic_preview(preview_report_path, render_report_path, baseline_path)
    accepted = matched.get("accepted_dynamic_baseline", {})
    if matched["status"] != "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT":
        raise AssertionError(matched["errors"])
    if not isinstance(accepted, dict) or accepted.get("status") != "PASS_ACCEPTED_DYNAMIC_BASELINE_MATCH":
        raise AssertionError(accepted)

    drift_baseline_path = directory / "accepted-dynamic-baseline-drift.json"
    drift_manifest = json.loads(json.dumps(manifest))
    keyframe = drift_manifest["artifacts"]["keyframe_strip"]
    source_keyframe = ROOT / keyframe["path"]
    drift_keyframe = directory / "drift-keyframes.png"
    with Image.open(source_keyframe) as image:
        changed = image.convert("RGB")
    changed.putpixel((0, 0), (0, 0, 0) if changed.getpixel((0, 0)) != (0, 0, 0) else (255, 255, 255))
    changed.save(drift_keyframe)
    keyframe["path"] = str(drift_keyframe.relative_to(ROOT)).replace("\\", "/")
    keyframe["sha256"] = "0" * 64
    write_json(drift_baseline_path, drift_manifest)
    drifted = verify_dynamic_preview(preview_report_path, render_report_path, drift_baseline_path)
    drifted_accepted = drifted.get("accepted_dynamic_baseline", {})
    if drifted["status"] != "FAIL":
        raise AssertionError("dynamic preview verifier did not reject an accepted-baseline pixel drift")
    if not isinstance(drifted_accepted, dict) or drifted_accepted.get("status") != "FAIL_ACCEPTED_DYNAMIC_BASELINE_DRIFT":
        raise AssertionError(drifted_accepted)


def assert_legacy_state_decoration_stays_fail_closed(directory: pathlib.Path,
                                                      render_report_path: pathlib.Path,
                                                      cemp_report_path: pathlib.Path,
                                                      scope: str) -> None:
    try:
        render_dynamic_preview(
            directory / f"{scope}-preview.json",
            scope,
            render_report_path=render_report_path,
            cemp_report_path=cemp_report_path,
            artifact_root=directory / f"{scope}-artifacts",
        )
    except ValueError as error:
        if "registered-state score selects a role without exact state_components" not in str(error):
            raise AssertionError(f"{scope} failed for an unexpected reason: {error}") from error
        return
    raise AssertionError(f"{scope} accepted an unselected legacy decoration")


def test_exact_state_component_selection() -> None:
    layer_path = ROOT / "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rig-layout.json"
    entry = ComponentLayer("charm_star", "charm", "idle", 96, 31, (0, 0), 10, "ink", layer_path)
    question = ComponentLayer("charm_question", "charm", "touch", 137, 26, (0, 0), 10, "ink", layer_path)
    selected = selected_state_layers(
        {"charm": (entry,)}, {"charm": (question,)}, ("charm_question",),
    )
    if tuple(layer.component for layer in selected) != ("charm_question",):
        raise AssertionError("exact component selection did not replace the entry role")
    try:
        selected_state_layers({"charm": (entry,)}, {"charm": (question,)}, ("charm_star",))
    except ValueError as error:
        if "absent from its source sustain Rig layers" not in str(error):
            raise AssertionError(f"unexpected component-selection rejection: {error}") from error
    else:
        raise AssertionError("state selection accepted an entry component absent from sustain")


def test_daily_dynamic_rest_guard() -> None:
    valid = (
        ScoreStep("entry", "entry", 750, (), False),
        ScoreStep("prepare", "left enters rest", 750,
                  (("left_eye_highlight_open", (0, 1)),
                   ("left_eye_sparkle_open", (0, 1))), False),
        ScoreStep("lead", "left reaches rest", 750,
                  (("left_eye_highlight_open", (0, 2)),
                   ("left_eye_sparkle_open", (0, 2))), False),
        ScoreStep("lead", "right enters rest", 750,
                  (("right_eye_highlight_open", (0, 1)),
                   ("right_eye_sparkle_open", (0, 1))), False),
        ScoreStep("lead", "right reaches rest", 750,
                  (("right_eye_highlight_open", (0, 2)),
                   ("right_eye_sparkle_open", (0, 2))), False),
        ScoreStep("lead", "left leads outward", 750,
                  (("left_eye_highlight_open", (-1, 2)),
                   ("left_eye_sparkle_open", (-1, 2))), False),
        ScoreStep("lead", "right joins left gaze", 750,
                  (("right_eye_highlight_open", (-1, 2)),
                   ("right_eye_sparkle_open", (-1, 2))), False),
        ScoreStep("hold", "both hold left", 750,
                  (), False),
        ScoreStep("return", "both return to rest", 750,
                  (("left_eye_highlight_open", (0, 2)),
                   ("left_eye_sparkle_open", (0, 2)),
                   ("right_eye_highlight_open", (0, 2)),
                   ("right_eye_sparkle_open", (0, 2))), False),
        ScoreStep("return", "both rise home", 750,
                  (("left_eye_highlight_open", (0, 1)),
                   ("left_eye_sparkle_open", (0, 1)),
                   ("right_eye_highlight_open", (0, 1)),
                   ("right_eye_sparkle_open", (0, 1))), False),
        ScoreStep("settle", "settle", 750, (), True),
    )
    validate_daily_reflection_score("daily_left", valid)
    invalid = valid[:2] + (
        ScoreStep("lead", "left skips the rest anchor", 750,
                  (("left_eye_highlight_open", (-1, 0)),
                   ("left_eye_sparkle_open", (-1, 0))), False),
    ) + valid[2:]
    try:
        validate_daily_reflection_score("daily_left", invalid)
    except ValueError as error:
        if "dynamic-rest corridor" not in str(error):
            raise AssertionError(f"unexpected rest-anchor rejection: {error}") from error
    else:
        raise AssertionError("dynamic rest guard accepted the old source-centre left hold")
    split = valid[:2] + (
        ScoreStep("lead", "left sparkle stays behind", 750,
                  (("left_eye_highlight_open", (0, 0)),), False),
    ) + valid[2:]
    try:
        validate_daily_reflection_score("daily_left", split)
    except ValueError as error:
        if "paired eye reflection" not in str(error):
            raise AssertionError(f"unexpected paired-reflection rejection: {error}") from error
    else:
        raise AssertionError("paired-reflection guard accepted a pinned sparkle")


def main() -> int:
    cache = ROOT / ".cache" / "host-tests"
    cache.mkdir(parents=True, exist_ok=True)
    first = pathlib.Path(tempfile.mkdtemp(prefix="v9-rig-a-", dir=cache))
    second = pathlib.Path(tempfile.mkdtemp(prefix="v9-rig-b-", dir=cache))
    try:
        first_report, first_render_report, first_cemp_report = render_once(first)
        second_report, _, _ = render_once(second)
        if first_report["state_matrix"]["frame_hashes"] != second_report["state_matrix"]["frame_hashes"]:
            raise AssertionError("Rig state matrix is not deterministic")
        if first_report["state_matrix"]["unique_frame_hashes"] < 12:
            raise AssertionError("Rig regressed to fewer than twelve dynamic state outputs")
        test_exact_state_component_selection()
        test_daily_dynamic_rest_guard()
        daily = first_report["state_matrix"]["frame_hashes"]
        for direction in ("left", "right", "up", "down"):
            if daily["daily_calm_center"] == daily[f"daily_calm_{direction}"]:
                raise AssertionError(f"{direction} gaze regressed to the center card")
        daily_preview_report = first / "daily-focus-preview.json"
        daily_preview = render_dynamic_preview(
            daily_preview_report,
            "daily_focus",
            render_report_path=first_render_report,
            cemp_report_path=first_cemp_report,
            artifact_root=first / "daily-focus-artifacts",
        )
        if daily_preview.get("preview_scope") != "daily_focus" or \
                set(daily_preview.get("stories", [])) != {"daily_left", "daily_right", "daily_up", "daily_down"}:
            raise AssertionError("daily focus preview did not isolate the four daily gaze stories")
        daily_distance = verify_dynamic_preview(daily_preview_report, first_render_report)
        if daily_distance["status"] != "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT":
            raise AssertionError(daily_distance["errors"])
        daily_distance_report = first / "daily-focus-distance.json"
        daily_distance_report.write_text(json.dumps(daily_distance, indent=2) + "\n", encoding="ascii")
        assert_legacy_state_decoration_stays_fail_closed(
            first, first_render_report, first_cemp_report, "registered_states",
        )
        assert_legacy_state_decoration_stays_fail_closed(
            first, first_render_report, first_cemp_report, "expression_atlas",
        )
        test_synthetic_accepted_dynamic_baseline(
            first, daily_preview_report, daily_distance_report, first_render_report,
        )
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)
    print("PASS: v9 Rig preserves source-derived Daily choreography and rejects unselected legacy decorations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
