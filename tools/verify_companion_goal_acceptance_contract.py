#!/usr/bin/env python3
"""Verify the detailed Companion Goal acceptance contract remains evidence-bound."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "companion_goal_acceptance_contract.md"
TRIAGE = ROOT / "docs" / "validation" / "companion-owner-feedback-triage-20260717.json"
REPORT = ROOT / "docs" / "validation" / "companion-goal-acceptance-readiness-20260717.json"

REQUIRED_CONTRACT_ANCHORS = (
    "G1: Protected Behavior And Build Boundary",
    "G2: Visual Source Decisions (Three Sequential Items)",
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
    "try generic, adjacent-panel, guessed, online, or hand-authored LUT bytes.",
    "<=1 mA average over >=60 s",
    "one canonical Chinese `aiw operator-prompt` item at a time",
)

EVIDENCE = {
    "visual_review_readiness": (
        "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json",
        "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW",
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

    return {
        "schema": "companion.goal_acceptance_readiness.v1",
        "status": "PASS_ACCEPTANCE_CONTRACT_READY_OWNER_AND_HARDWARE_GATED" if not errors else "FAIL",
        "operator_prompt_opened": False,
        "next_eligible_owner_item": "menu-v6-four-root",
        "sequential_visual_review": [
            {"id": "menu-v6-four-root", "state": "ready_for_owner_decision"},
            {"id": "special-system-v1", "state": "owner_feedback_triaged_correction_required"},
            {"id": "special-journey-v1", "state": "blocked_until_prior_visual_decision"},
        ],
        "physical_acceptance": {
            "state": "not_started",
            "required_first_machine_gates": ["G1", "G3", "G4", "G5_preflight"],
            "g5_preflight": {
                "frame_safe_area": "39 inactive v9 frames have >=4 px canvas clearance",
                "ssd1681_mapping": "all 40,000 pixels are one-to-one/in-bounds through the WB55 rotation, mirror and descending-Y path",
                "limit": "neither machine gate proves a physical panel viewport or clears the lower-edge feedback",
            },
            "lower_edge_truncation": "must be checked during G5 before any visual pass",
            "vendor_waveform": "G7 remains frozen until matching CWF1",
            "wba_board": "G8 remains deferred until target board and CubeWBA project exist",
        },
        "machine_evidence": machine_evidence,
        "owner_feedback_triage": TRIAGE.relative_to(ROOT).as_posix(),
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
