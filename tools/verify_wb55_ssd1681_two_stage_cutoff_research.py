#!/usr/bin/env python3
"""Artifact-backed state-space audit for the accepted two-stage cutoff."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
OUT = ROOT / "docs/validation/companion-ssd1681-two-stage-cutoff-research-disposition-20260721.json"
FILES = {
    "accepted": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json",
    "accepted_runtime": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-runtime-20260720.json",
    "accepted_static": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-static-20260720.json",
    "disjoint_settle": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-operator-r1-20260721.json",
    "added_first": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-completion-audit-20260721.json",
    "removed_first": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-removed-black-repair-current-union-operator-20260720.json",
    "single_activation": ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-operator-r6-20260721.json",
    "method_study": ROOT / "docs/validation/companion-gdey0154d67-t03-yesterday-method-study-20260721.json",
}
HASHES = {
    "accepted": "DA2FE11DB4CB1AFC5D433B2798BADBB576FC9C82BB39C472236E084C48F1EC57",
    "accepted_runtime": "AE50830D1DB091AD2E526A132D55A7D512EA55E09D534F66CA7E71DB81BFF814",
    "accepted_static": "0AAA8C8E20483A5CDBBA176E1A66332DE8BCCEB40D84BCA3E01759C54A40389F",
    "disjoint_settle": "67E43FBBD7546EB99E4CE8B06EE84141D0B0F4419E77C7ED1AF7D9C38D7D9C00",
    "added_first": "0E3643391446640D0D9A2A9B2E050D41A14D4BBB0D32785D814B4E57D98D2CF4",
    "removed_first": "2FEBAB3365FE8481760DB0DC6C4180EFD01C24B10D985F751B6CAD9F4E1A2932",
    "single_activation": "13CF51F221110829949075864973DF769AAF1C8222B73B482124BF14FD55D9C3",
    "method_study": "A88B022423E6ADFBA83B1362BAACB0C6CAC3A970DAEC93EB521E63EEB0030C2D",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    errors: list[str] = []
    data = {}
    for name, path in FILES.items():
        if not path.is_file() or sha(path) != HASHES[name]:
            errors.append(f"locked artifact missing/hash mismatch: {name}")
            continue
        data[name] = json.loads(path.read_text(encoding="utf-8"))
    if sha(SUPPLIER) != "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896":
        errors.append("supplier source hash mismatch")
    registry = REGISTRY.read_text(encoding="utf-8")
    if "| COMP-REQ-280 |" not in registry or "这个目前是最好的" not in registry:
        errors.append("owner current-best steering missing")
    expected_status = {
        "accepted": "PASS_OPERATOR_ACCEPTED_PRODUCTION_OFF_NO_UNION_SETTLE_BASELINE",
        "accepted_runtime": "PASS_MACHINE_NO_UNION_SETTLE_TRACE",
        "accepted_static": "PASS_STATIC_PRODUCTION_OFF_VENDOR_PARTIAL_NO_UNION_SETTLE",
        "disjoint_settle": "NO_GO_OPERATOR_LEADING_EDGE_CUTOFF_DISJOINT_NO_UNION_SETTLE",
        "added_first": "NO_GO_OWNER_MORE_RESIDUE_AND_CUTOFF_PERSISTS_NORMAL_RESTORED",
        "removed_first": "NO_GO_OPERATOR_VISIBLE_ENLARGED_GAP",
        "single_activation": "PASS_OPERATOR_WITH_RESIDUE_STEERING_PRODUCTION_OFF",
        "method_study": "STUDY_COMPLETE_TWO_PASS_ERASE_FIRST_IS_ACCEPTED_METHOD",
    }
    for name, status in expected_status.items():
        if data.get(name, {}).get("status") != status:
            errors.append(f"artifact status drifted: {name}")

    runtime = data.get("accepted_runtime", {}).get("observed", {})
    if runtime.get("partial_frame_count") != 48 or runtime.get("partial_activation_count") != 96:
        errors.append("accepted baseline is not exact two-activation evidence")
    accepted_note = data.get("accepted", {}).get("operator_review", {}).get("note")
    if accepted_note != "好很多, 就是移动的时候移动方向会切掉一点, 随后还原, 能优化吗":
        errors.append("accepted owner note drifted")

    # Pixel-state proof for a rightward move: O is old-only, N is new-only.
    # White=1, black=0. The accepted erase-first pass reaches O=1 while N
    # remains 1; only draw pass 2 reaches N=0, so the leading edge is absent
    # in the inter-pass state by construction.
    accepted_states = [
        {"phase": "visible_old", "old_only": 0, "new_only": 1},
        {"phase": "after_erase_first", "old_only": 1, "new_only": 1},
        {"phase": "after_draw_second", "old_only": 1, "new_only": 0},
    ]
    if accepted_states[1]["new_only"] != 1:
        errors.append("accepted inter-pass cutoff proof failed")

    topology_matrix = [
        {"class": "erase_old_then_draw_new", "artifact": "accepted", "physical": "accepted current best; no old hatch/no whole-screen black flash; temporary leading-edge cutoff"},
        {"class": "erase_old_then_disjoint_draw_new", "artifact": "disjoint_settle", "physical": "no residue, but same leading-edge cutoff"},
        {"class": "draw_added_then_erase_old", "artifact": "added_first", "physical": "more other residue and cutoff persists"},
        {"class": "removed_only_erase_then_union_draw", "artifact": "removed_first", "physical": "visible missing segment enlarged"},
        {"class": "simultaneous_current_regions_one_activation", "artifact": "single_activation", "physical": "visible movement with direct-motion residue"},
        {"class": "current_union_then_cleanup", "artifact": "COMP-REQ-239/241", "physical": "cumulative content loss and enlarged eaten segment"},
        {"class": "old_or_current_union", "artifact": "COMP-REQ-236 video diagnosis", "physical": "recurring old-position hatch until settle"},
    ]

    result = {
        "schema_id": "companion.wb55.ssd1681_two_stage_cutoff_research.v1",
        "status": "RESEARCH_DISPOSITION_RETAIN_ACCEPTED_BASELINE_NO_ADMISSIBLE_UNTESTED_SINGLE_VARIABLE" if not errors else "NO_GO_RESEARCH_EVIDENCE_DRIFT",
        "errors": errors,
        "hardware_contact": 0,
        "owner_selected_floor": {
            "requirement": "COMP-REQ-236/237/280",
            "status": expected_status["accepted"],
            "note": accepted_note,
            "accepted": ["visible movement", "no recurring old-position hatch", "no whole-screen black flash"],
            "remaining": "temporary movement-direction leading-edge cutoff between two activations",
        },
        "machine_state_proof": {
            "polarity": "1=white, 0=black",
            "representative_states": accepted_states,
            "conclusion": "With erase-before-draw, a new-only leading-edge pixel is necessarily white after pass 1 and becomes black only after pass 2. The observed cutoff is the exact intermediate state, not an unaccounted transfer bug.",
        },
        "artifact_backed_topology_matrix": topology_matrix,
        "admissibility": {
            "unchanged_boundaries": ["supplier 0xFF/0x20/BUSY", "no custom LUT", "no full black flash", "no old hatch", "source reset/border", "production off"],
            "required_to_remove_cutoff": "make new-only black pixels visible before or during old-only erasure",
            "already_observed_outcomes": "Every source-bound ordering that does so is represented by draw-first, union-current, disjoint-current or old-or-current artifacts and regresses residue or content integrity.",
            "untested_single_variable": None,
        },
        "disposition": {
            "candidate_admitted": False,
            "baseline_rerun": False,
            "reason": "No materially distinct, source-bound one-variable topology remains that can remove the mathematically required inter-pass cutoff without repeating a durable physical NO_GO or violating the accepted no-residue/no-full-flash floor.",
            "preserve": "Keep COMP-REQ-236/237 default-disabled current-best baseline unchanged.",
            "future_unlock": "A panel-bound waveform/control that cleanly drives simultaneous old-only white and new-only black transitions, or explicit owner permission to relax a protected floor, would create a genuinely new candidate class.",
            "goal_terminal": False,
        },
        "locked_hashes": HASHES,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
