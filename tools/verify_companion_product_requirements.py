#!/usr/bin/env python3
"""Guard the current Companion steering registry and its handoff anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "companion_product_requirements.md"
FIXTURE = ROOT / "docs" / "validation" / "companion-product-requirements.json"

REQUIRED_ANCHORS = (
    "Companion Product Requirement Registry",
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
    "PC6/EXTI",
    "<=1 mA",
    "external-Flash first",
    "reference-first",
    "menu-v3-2026-07-13",
    "D87E45A49AA623552B867C9EDAADB906CA282DF2C2C062D3A127A277920F9F81",
    "Wake-word capture is deferred",
    "asynchronous",
    "superseded",
    "Latest Machine Evidence",
    "PASS_STATIC_PARSER",
    "no CubeWBA project, WBA hardware, or parity claim",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()

    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else ""
    errors = [f"missing requirement registry anchor: {anchor}" for anchor in REQUIRED_ANCHORS if anchor not in text]
    result = {
        "schema_id": "companion.product.requirements.v1",
        "status": "PASS" if not errors else "FAIL",
        "registry": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
        "workflow_plan": "companion-screen-product-integration",
        "requirement_ids": [f"COMP-REQ-{number:03d}" for number in range(1, 16)],
        "current_focus": "COMP-REQ-015 accepted menu-v3 external-Flash resource import",
        "active_parallel_track": "COMP-REQ-009 generated low-power/wake/dynamic-recording expression art",
        "errors": errors,
    }
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
