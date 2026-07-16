#!/usr/bin/env python3
"""Guard the current Companion steering registry and its handoff anchors."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "companion_product_requirements.md"
FIXTURE = ROOT / "docs" / "validation" / "companion-product-requirements.json"

REQUIRED_ANCHORS = (
    "Companion Product Requirement Registry",
    "Current Goal Precedence (2026-07-17)",
    "Steering Intake Rule",
    "companion-screen-product-integration",
    "COMP-REQ-001",
    "COMP-REQ-002",
    "COMP-REQ-003",
    "COMP-REQ-004",
    "COMP-REQ-005",
    "COMP-REQ-006",
    "COMP-REQ-007",
    "COMP-REQ-008",
    "COMP-REQ-009",
    "COMP-REQ-010",
    "COMP-REQ-011",
    "COMP-REQ-012",
    "COMP-REQ-013",
    "COMP-REQ-014",
    "COMP-REQ-015",
    "COMP-REQ-016",
    "COMP-REQ-017",
    "COMP-REQ-018",
    "COMP-REQ-019",
    "COMP-REQ-020",
    "COMP-REQ-021",
    "COMP-REQ-022",
    "COMP-REQ-023",
    "COMP-REQ-024",
    "COMP-REQ-025",
    "COMP-REQ-026",
    "COMP-REQ-027",
    "COMP-REQ-028",
    "COMP-REQ-029",
    "COMP-REQ-030",
    "COMP-REQ-031",
    "COMP-REQ-032",
    "COMP-REQ-033",
    "COMP-REQ-034",
    "COMP-REQ-035",
    "COMP-REQ-036",
    "COMP-REQ-037",
    "COMP-REQ-038",
    "COMP-REQ-039",
    "COMP-REQ-076",
    "COMP-REQ-077",
    "PC6/EXTI",
    "<=1 mA",
    "external-Flash first",
    "reference-first",
    "verify_visual_reference_evidence.py",
    "PENDING_OWNER_VISUAL_REVIEW",
    "menu-v3-2026-07-13",
    "D87E45A49AA623552B867C9EDAADB906CA282DF2C2C062D3A127A277920F9F81",
    "Wake-word capture is deferred",
    "asynchronous",
    "superseded",
    "Latest Machine Evidence",
    "PASS_STATIC_PARSER",
    "no CubeWBA project, WBA hardware, or parity claim",
    "tools/run_wb55_refresh_ab.ps1",
    "docs/validation/companion-wb55-refresh-ab-runner.json",
    "docs/validation/companion-interaction-serial-quiet-20260714.json",
    "Denzic Platform shared product core",
    "A second Companion-owned recording state machine or protocol fork is prohibited",
    "two double taps, valid non-timeout PCM, stop, and external-Flash store",
    "machine-first four-layer contract",
    "Human `通过` is necessary for physical acceptance but cannot override missing machine evidence",
    "companion-pet-expression-v9",
    "companion-menu-v6-four-root",
    "physical preflight only when a healthy",
    "verify_companion_current_goal_audit.py",
    "The Goal API cannot edit or replace an unfinished active Goal",
    "main is the sole attached worktree",
    "<AI_WORKFLOW_REPO>\\docs\\agent_quickstart.md",
    "Current Visual Source Resolution (2026-07-17)",
    "historical API identifiers only",
    "reactivate any image, prompt, PBM, CEMP, menu layout, or visual validation path",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()

    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else ""
    errors = [f"missing requirement registry anchor: {anchor}" for anchor in REQUIRED_ANCHORS if anchor not in text]
    requirement_ids = sorted(
        set(re.findall(r"COMP-REQ-(\d{3})", text)),
        key=int,
    )
    result = {
        "schema_id": "companion.product.requirements.v1",
        "status": "PASS" if not errors else "FAIL",
        "registry": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
        "workflow_plan": "companion-screen-product-integration",
        "requirement_ids": [f"COMP-REQ-{number}" for number in requirement_ids],
        "current_focus": "Active Codex Goal: v9 renderer-first UI, four-root menu source review, protected touch/three-minute idle behavior, WBA external-SPI-NOR boundary, and vendor waveform freeze",
        "active_parallel_track": "WB55 FTS02/panel recovery, real touch/Stop/current and final physical review remain hardware gates; daily art validation does not require a camera",
        "current_goal_audit": "docs/validation/companion-current-goal-audit-20260717.json",
        "errors": errors,
    }
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
