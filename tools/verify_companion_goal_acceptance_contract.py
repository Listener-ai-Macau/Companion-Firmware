#!/usr/bin/env python3
"""Verify the detailed Companion Goal acceptance contract remains evidence-bound."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "companion_goal_acceptance_contract.md"
TRIAGE = ROOT / "docs" / "validation" / "companion-owner-feedback-triage-20260717.json"
G2_GROUP_TRIAGE = ROOT / "docs" / "validation" / "companion-g2-menu-group-review-triage-20260717.json"
G2_HOME_CONTEXT_TRIAGE = ROOT / "docs" / "validation" / "companion-g2-home-artifact1-triage-20260717.json"
G2_HOME_ANCHOR_TRIAGE = ROOT / "docs" / "validation" / "companion-g2-home-artifact1-anchor-triage-20260717.json"
V9_RENDER = ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9" / "rendered-200x200" / "v9-expression-render-report.json"
SPECIAL_PREFLIGHT = ROOT / "docs" / "validation" / "companion-pet-special-state-crop-preflight-20260717.json"
PLACEMENT_SOURCE = ROOT / "app" / "companion_pendant" / "epaper" / "expression_frame_placement.c"
PLACEMENT_HEADER = ROOT / "app" / "companion_pendant" / "epaper" / "expression_frame_placement.h"
PLACEMENT_TEST = ROOT / "tools" / "test_expression_frame_placement_host.ps1"
REPORT = ROOT / "docs" / "validation" / "companion-goal-acceptance-readiness-20260717.json"

REQUIRED_CONTRACT_ANCHORS = (
    "G1: Protected Behavior And Build Boundary",
    "G2: Visual Source Observations (Four Sequential Families)",
    "G3: Renderer And External Resource Chain",
    "G4: Four-Root Menu Function And Physical Presentation",
    "G5: WB55 Panel, Touch, And Low-Power Reality",
    "G6: Double-Tap Recording And External-Flash Store",
    "G7: Refresh, Residue, And Waveform Gate",
    "G8: WBA55/WBA65 Board Parity",
    "exactly 39 frames / 13 clips",
    "40,000",
    "4 px",
    "durable request record",
    "next-prompt delta",
    "special-state crop preflight",
    "target, operator action, success signal, failure",
    "one canonical prompt per image",
    "locked generated-art baseline",
    "desktop output",
    "whole-expression anchor policy",
    "canonical center `(100,100)`",
    "source anchor",
    "requested center",
    "portable requested-center placement host test",
    "This is not an electronic-paper panel review",
    "已执行",
    "需修改",
    "home-v9-daily-storyboard",
    "menu-v7-screen-family",
    "try generic, adjacent-panel, guessed, online, or hand-authored LUT bytes.",
    "<=1 mA average over >=60 s",
    "one canonical Chinese `aiw operator-prompt` item at a time",
    "run_companion_goal_visual_source_acceptance.ps1",
)

G2_RUNNER = ROOT / "tools" / "run_companion_goal_visual_source_acceptance.ps1"
G2_RUNNER_TEST = ROOT / "tools" / "test_companion_goal_visual_source_acceptance.ps1"

EVIDENCE = {
    "visual_review_readiness": (
        "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json",
        "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW",
    ),
    "visual_comparison_pages": (
        "docs/validation/companion-ui-visual-comparison-pages-20260717.json",
        "PASS_PAIRED_ART_BASELINE_AND_DESKTOP_OUTPUT_READY",
    ),
    "v9_cemp_pixels": (
        "docs/validation/companion-v9-expression-cemp-20260716.json",
        "PASS_MACHINE_ONLY_CEMP_NOT_ACTIVATED",
    ),
    "v9_scene_coverage": (
        "docs/validation/companion-v9-scene-coverage-20260716.json",
        "PASS_MACHINE_ONLY_NO_LEGACY_FALLBACK",
    ),
    "v9_resource_binding": (
        "docs/validation/companion-v9-candidate-resource-binding-20260717.json",
        "PASS_MACHINE_ONLY_INACTIVE",
    ),
    "visual_reference_ledger": (
        "docs/validation/companion-visual-reference-evidence.json",
        "PASS_LEDGER_INTEGRITY",
    ),
    "v9_home_storyboard": (
        "docs/validation/companion-v9-home-storyboard-review-20260717.json",
        "PASS_MACHINE_ONE_PAGE_PER_KEYFRAME_PENDING_OWNER",
    ),
    "menu_v7_screen_family": (
        "docs/validation/companion-menu-v7-screen-family-preview-20260717.json",
        "PASS_MACHINE_SCREEN_FAMILY_PREVIEW_PENDING_OWNER",
    ),
    "special_one_page_review": (
        "docs/validation/companion-pet-special-state-one-page-review-20260717.json",
        "PASS_MACHINE_ONE_PAGE_PER_SPECIAL_STATE_PENDING_OWNER",
    ),
    "menu_function": (
        "docs/validation/companion-menu-v6-function-receipt-20260717.json",
        "PASS_CURRENT_SOURCE_MENU_FUNCTION_PENDING_OWNER_VISUAL",
    ),
    "wba_boundary": (
        "docs/validation/companion-v9-wba-visual-boundary-20260717.json",
        "PASS_V9_WBA_VISUAL_BOUNDARY_PENDING_OWNER",
    ),
    "frame_safe_area": (
        "docs/validation/companion-v9-frame-safe-area-20260717.json",
        "PASS_MACHINE_SAFE_AREA_PHYSICAL_REVIEW_PENDING",
    ),
    "special_state_crop_preflight": (
        "docs/validation/companion-pet-special-state-crop-preflight-20260717.json",
        "PASS_MACHINE_SAFE_CROP_PREVIEW_NOT_IMPORTABLE",
    ),
    "v9_anchor_render": (
        "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-render-report.json",
        "PASS_MACHINE_RENDER_CANDIDATE_NOT_ACTIVATED",
    ),
    "ssd1681_frame_mapping": (
        "docs/validation/companion-ssd1681-frame-mapping-20260717.json",
        "PASS_MACHINE_EXHAUSTIVE_FRAME_MAPPING_PHYSICAL_REVIEW_PENDING",
    ),
}


def load_status(relative_path: str, errors: list[str]) -> str | None:
    path = ROOT / relative_path
    if not path.is_file():
        errors.append(f"missing evidence: {relative_path}")
        return None
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("status"))
    except json.JSONDecodeError:
        errors.append(f"invalid JSON evidence: {relative_path}")
        return None


def build_report() -> dict[str, object]:
    errors: list[str] = []
    text = CONTRACT.read_text(encoding="utf-8") if CONTRACT.is_file() else ""
    for anchor in REQUIRED_CONTRACT_ANCHORS:
        if anchor not in text:
            errors.append(f"missing contract anchor: {anchor}")
    for runner in (G2_RUNNER, G2_RUNNER_TEST):
        if not runner.is_file():
            errors.append(f"missing G2 runner artifact: {runner.relative_to(ROOT).as_posix()}")
    if G2_RUNNER.is_file():
        runner_text = G2_RUNNER.read_text(encoding="utf-8")
        for token in (
            "-Execute -OwnerStartAcknowledged",
            "OWNER_ARTIFACT_OBSERVATION_CAPTURED",
            "已执行",
            "需修改",
            "不是开发板上的电子纸实物屏",
            "operator-prompt",
            "manifest_owner_decision_changed = $false",
            "runtime_resource_activated = $false",
            "original_image_one_at_a_time",
            "-OriginalImageOpened $true",
            "-ComparisonImageOpened $true",
            "comparison_image_opened",
            "Start-Process -FilePath $comparisonPagePath",
            "-SelfTest",
        ):
            if token not in runner_text:
                errors.append(f"G2 runner missing fail-closed token: {token}")

    machine_evidence: dict[str, dict[str, str | None]] = {}
    for name, (path, expected) in EVIDENCE.items():
        actual = load_status(path, errors)
        if actual != expected:
            errors.append(f"{name} has status {actual!r}, expected {expected!r}")
        machine_evidence[name] = {"path": path, "status": actual}

    triage: dict[str, object] = {}
    if TRIAGE.is_file():
        try:
            triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("owner feedback triage is invalid JSON")
    else:
        errors.append("missing owner feedback triage")
    if triage.get("status") != "OPEN_P0_PHYSICAL_VISUAL_RECHECK":
        errors.append("lower-edge truncation must remain an open physical visual recheck")
    if triage.get("triage", {}).get("requirement") != "COMP-REQ-078":
        errors.append("lower-edge truncation is not linked to COMP-REQ-078")
    if triage.get("source", {}).get("note") != "有一些是截断了的表情, 下面截断了一点":
        errors.append("owner feedback text drifted")

    g2_group_triage: dict[str, object] = {}
    if G2_GROUP_TRIAGE.is_file():
        try:
            g2_group_triage = json.loads(G2_GROUP_TRIAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("G2 grouped-review triage is invalid JSON")
    else:
        errors.append("missing G2 grouped-review triage")
    if g2_group_triage.get("status") != "OPEN_REVIEW_FLOW_REWORK_REQUIRED":
        errors.append("G2 grouped menu review must remain open for original-image rework")
    if g2_group_triage.get("requirement") != "COMP-REQ-079":
        errors.append("G2 grouped menu review is not linked to COMP-REQ-079")
    raw_review = g2_group_triage.get("raw_review", {})
    if raw_review.get("selected") != "通过" or raw_review.get("sha256") != "C03D6F50DCC8086F820EDF347094B16D3C1E618B5FCD5E10EB0C55521840EF3E":
        errors.append("G2 grouped menu raw result drifted")
    resolution = g2_group_triage.get("resolution", {})
    if resolution.get("group_selection_applied") is not False or resolution.get("manifest_owner_decision_changed") is not False:
        errors.append("G2 grouped menu selection was incorrectly applied")

    g2_home_context_triage: dict[str, object] = {}
    if G2_HOME_CONTEXT_TRIAGE.is_file():
        try:
            g2_home_context_triage = json.loads(G2_HOME_CONTEXT_TRIAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("G2 home context triage is invalid JSON")
    else:
        errors.append("missing G2 home context triage")
    if g2_home_context_triage.get("status") != "NOT_APPLIED_OWNER_CONTEXT_MISMATCH" or g2_home_context_triage.get("requirement") != "COMP-REQ-083":
        errors.append("G2 home observation must remain unapplied for computer/physical context mismatch")
    if g2_home_context_triage.get("decision", {}).get("selection_applied") is not False:
        errors.append("G2 home context-mismatch selection was incorrectly applied")

    g2_home_anchor_triage: dict[str, object] = {}
    if G2_HOME_ANCHOR_TRIAGE.is_file():
        try:
            g2_home_anchor_triage = json.loads(G2_HOME_ANCHOR_TRIAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("G2 home anchor triage is invalid JSON")
    else:
        errors.append("missing G2 home anchor triage")
    if (g2_home_anchor_triage.get("status") != "OPEN_ANCHOR_NORMALIZATION_REWORK_REQUIRED" or
            g2_home_anchor_triage.get("requirement") != "COMP-REQ-085"):
        errors.append("G2 home anchor rework must remain linked to COMP-REQ-085")
    if g2_home_anchor_triage.get("decision", {}).get("selection_applied") is not False:
        errors.append("G2 home anchor selection was incorrectly applied")

    try:
        v9_render = json.loads(V9_RENDER.read_text(encoding="utf-8"))
        special_preflight = json.loads(SPECIAL_PREFLIGHT.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        errors.append(f"missing or invalid expression-anchor evidence: {exc}")
        v9_render = {}
        special_preflight = {}
    v9_frames = v9_render.get("frames", [])
    if len(v9_frames) != 39 or not all(
            frame.get("anchor_policy") == "whole_expression_visible_bbox_center" and
            frame.get("canonical_center") == [100, 100] and
            isinstance(frame.get("source_anchor"), list) and
            isinstance(frame.get("normalization_offset"), list) and
            isinstance(frame.get("requested_center"), list) and
            isinstance(frame.get("final_output_bounds"), list)
            for frame in v9_frames):
        errors.append("v9 frames lack complete whole-expression anchor records")
    special_frames = [frame for source in special_preflight.get("sources", [])
                      for frame in source.get("frames", [])]
    if len(special_frames) != 24 or not all(
            frame.get("anchor_policy") == "whole_expression_visible_bbox_center" and
            frame.get("canonical_center") == [100, 100] and
            isinstance(frame.get("source_anchor"), list) and
            isinstance(frame.get("normalization_offset"), list) and
            isinstance(frame.get("requested_center"), list) and
            isinstance(frame.get("final_output_bounds"), list)
            for frame in special_frames):
        errors.append("special frames lack complete whole-expression anchor records")
    for path in (PLACEMENT_SOURCE, PLACEMENT_HEADER, PLACEMENT_TEST):
        if not path.is_file():
            errors.append(f"missing portable expression placement artifact: {path.relative_to(ROOT).as_posix()}")
    if PLACEMENT_SOURCE.is_file():
        placement_text = PLACEMENT_SOURCE.read_text(encoding="utf-8")
        for token in ("comp_expression_frame_place_1bpp", "destination_x < 0"):
            if token not in placement_text:
                errors.append(f"portable expression placement missing fail-closed token: {token}")
    if PLACEMENT_HEADER.is_file() and "leaves destination untouched" not in PLACEMENT_HEADER.read_text(encoding="utf-8"):
        errors.append("portable expression placement header lacks untouched-destination contract")

    return {
        "schema": "companion.goal_acceptance_readiness.v2",
        "status": "PASS_ACCEPTANCE_CONTRACT_READY_OWNER_AND_HARDWARE_GATED" if not errors else "FAIL",
        "machine_preflight_opens_operator_prompt": False,
        "next_eligible_owner_item": "home-v9-daily-storyboard",
        "sequential_visual_review": [
            {"id": "home-v9-daily-storyboard", "state": "ready_for_owner_observation", "pages": 39},
            {"id": "menu-v7-screen-family", "state": "blocked_until_prior_pages_observed", "pages": 15},
            {"id": "special-system-v1", "state": "blocked_until_prior_pages_observed", "pages": 12},
            {"id": "special-journey-v1", "state": "blocked_until_prior_pages_observed", "pages": 12},
        ],
        "physical_acceptance": {
            "state": "not_started",
            "required_first_machine_gates": ["G1", "G3", "G4", "G5_preflight"],
            "g5_preflight": {
                "frame_safe_area": "39 inactive v9 frames have >=4 px canvas clearance",
                "special_state_crop_preflight": "24 pending special-state review frames have >=4 px source-crop canvas clearance without PBM/CEMP import",
                "ssd1681_mapping": "all 40,000 pixels are one-to-one/in-bounds through the WB55 rotation, mirror and descending-Y path",
                "limit": "neither machine gate proves a physical panel viewport or clears the lower-edge feedback",
            },
            "lower_edge_truncation": "must be checked during G5 before any visual pass",
            "vendor_waveform": "G7 remains frozen until matching CWF1",
            "wba_board": "G8 remains deferred until target board and CubeWBA project exist",
        },
        "machine_evidence": machine_evidence,
        "owner_feedback_triage": TRIAGE.relative_to(ROOT).as_posix(),
        "g2_group_review_triage": G2_GROUP_TRIAGE.relative_to(ROOT).as_posix(),
        "g2_home_context_triage": G2_HOME_CONTEXT_TRIAGE.relative_to(ROOT).as_posix(),
        "g2_home_anchor_triage": G2_HOME_ANCHOR_TRIAGE.relative_to(ROOT).as_posix(),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the deterministic readiness artifact.")
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
    print("PASS: detailed Goal acceptance contract is machine-ready and human/hardware-gated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
