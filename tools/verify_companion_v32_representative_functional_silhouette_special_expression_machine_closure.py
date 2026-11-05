#!/usr/bin/env python3
"""Close the machine-only V32 representative special-expression evidence chain."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
ARTIFACTS = {
    "source_gate": ("docs/validation/companion-v32-representative-functional-silhouette-special-expression-source-gate-20260720.json", "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_SOURCE_GATE_PENDING_COMPONENT_EXPORT"),
    "component_export_gate": ("docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-export-gate-20260720.json", "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_EXPORT_UNBOUND"),
    "component_performance": ("docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-performance-preview-20260720.json", "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE"),
    "browser_target_parity": ("docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-performance-parity-20260720.json", "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_COMPONENT_PERFORMANCE_BROWSER_TARGET_PLAN_PARITY"),
    "browser_render": ("docs/validation/companion-v32-representative-functional-silhouette-special-expression-component-browser-render-20260720.json", "PASS_V32_BROWSER_RENDER_INSPECTION_NATIVE_200X200"),
}
WRITE = ROOT / "docs/validation/companion-v32-representative-functional-silhouette-special-expression-machine-closure-20260720.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    records: dict[str, dict[str, object]] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for name, (relative, expected_status) in ARTIFACTS.items():
        path = ROOT / relative
        add(errors, path.is_file(), f"{name} artifact is missing")
        data = load(path) if path.is_file() else {}
        loaded[name] = data
        add(errors, data.get("status") == expected_status, f"{name} status is not {expected_status}")
        records[name] = {"path": relative.replace("\\", "/"), "sha256": sha256(path) if path.is_file() else None, "status": data.get("status")}

    route = loaded["component_performance"]
    policy = route.get("selection_policy", {})
    add(errors, route.get("runtime_resource_activated") is False, "V32 route activated runtime")
    add(errors, route.get("physical_panel_acceptance") is False, "V32 route claimed physical panel acceptance")
    add(errors, route.get("active_candidate_binding") == "forbidden", "V32 route permits a behavior binding")
    add(errors, policy.get("random_state_selection") is False, "V32 route allows random state selection")
    add(errors, policy.get("automatic_cross_state_cycle") is False, "V32 route allows automatic cross-state cycling")
    add(errors, policy.get("unavailable_special_state_policy") == "fail_closed", "V32 unavailable special states are not fail-closed")

    browser = loaded["browser_render"]
    checks = browser.get("checks", {})
    add(errors, checks.get("component_asset_map_present") is True, "browser does not prove mapped component assets")
    add(errors, checks.get("legacy_component_filename_lookup_absent") is True, "browser retains legacy component filename lookup")
    screenshots = browser.get("screenshots", [])
    add(errors, isinstance(screenshots, list) and len(screenshots) == 4, "browser inspection lacks four scene screenshots")
    if isinstance(screenshots, list):
        for screenshot in screenshots:
            path = ROOT / str(screenshot.get("path", ""))
            add(errors, path.is_file() and sha256(path) == screenshot.get("sha256"), "browser screenshot is missing or hash drifted")

    result = {
        "schema": "companion.v32_representative_functional_silhouette_special_expression_machine_closure.v1",
        "status": "PASS_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_MACHINE_CLOSURE_RUNTIME_INACTIVE" if not errors else "FAIL_V32_REPRESENTATIVE_FUNCTIONAL_SILHOUETTE_MACHINE_CLOSURE",
        "claim_scope": "source-to-component-to-browser/target machine closure for a runtime-inactive V32 candidate; no CRIG/profile export, event binding, firmware flash, panel output, physical acceptance, or human art acceptance",
        "locked_v9_source": {"path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png", "sha256": LOCKED_V9_SHA256},
        "artifacts": records,
        "selection_policy": policy,
        "next_human_boundary": "internal V32 representative-readability preflight, then canonical browser-only Chinese owner art review; a FAIL freezes V32 and returns to a fresh locked-V9-only source direction",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    WRITE.parent.mkdir(parents=True, exist_ok=True)
    WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        print("FAIL: V32 special-expression machine closure", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: V32 special-expression machine closure -> {WRITE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
