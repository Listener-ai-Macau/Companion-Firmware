#!/usr/bin/env python3
"""Close the machine-only V27 special-expression candidate evidence chain."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
SOURCE_GATE = ROOT / "docs/validation/companion-v27-face-action-gesture-special-expression-source-gate-20260720.json"
EXPORT_GATE = ROOT / "docs/validation/companion-v27-face-action-gesture-special-expression-component-export-gate-20260720.json"
ROUTE = ROOT / "docs/validation/companion-v27-face-action-gesture-special-expression-component-performance-preview-20260720.json"
PARITY = ROOT / "docs/validation/companion-v27-face-action-gesture-special-expression-component-performance-parity-20260720.json"
BROWSER = ROOT / "docs/validation/companion-v27-face-action-gesture-special-expression-component-browser-render-20260720.json"
WRITE = ROOT / "docs/validation/companion-v27-face-action-gesture-special-expression-machine-closure-20260720.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return data


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256, "locked V9 source hash drifted")
    artifacts = {
        "source_gate": (SOURCE_GATE, "PASS_V27_FACE_ACTION_GESTURE_SOURCE_GATE_PENDING_COMPONENT_EXPORT"),
        "component_export_gate": (EXPORT_GATE, "PASS_V27_FACE_ACTION_GESTURE_COMPONENT_EXPORT_UNBOUND"),
        "component_performance": (ROUTE, "PASS_V27_FACE_ACTION_GESTURE_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE"),
        "browser_target_parity": (PARITY, "PASS_V27_FACE_ACTION_GESTURE_COMPONENT_PERFORMANCE_BROWSER_TARGET_PLAN_PARITY"),
        "browser_render": (BROWSER, "PASS_V27_BROWSER_RENDER_INSPECTION_NATIVE_200X200"),
    }
    records: dict[str, dict[str, object]] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for name, (path, expected_status) in artifacts.items():
        add(errors, path.is_file(), f"{name} artifact is missing")
        data = load_json(path) if path.is_file() else {}
        loaded[name] = data
        add(errors, data.get("status") == expected_status, f"{name} status is not {expected_status}")
        records[name] = {"path": rel(path), "sha256": sha256(path) if path.is_file() else None, "status": data.get("status")}
    route = loaded["component_performance"]
    add(errors, route.get("runtime_resource_activated") is False, "V27 route activated runtime")
    add(errors, route.get("physical_panel_acceptance") is False, "V27 route claimed physical panel acceptance")
    add(errors, route.get("active_candidate_binding") == "forbidden", "V27 route permits behavior binding")
    add(errors, route.get("selection_policy", {}).get("random_state_selection") is False, "V27 route allows random state selection")
    add(errors, route.get("selection_policy", {}).get("automatic_cross_state_cycle") is False, "V27 route allows automatic cross-state cycling")
    add(errors, route.get("selection_policy", {}).get("unavailable_special_state_policy") == "fail_closed", "V27 unavailable special states are not fail-closed")
    browser = loaded["browser_render"]
    screenshots = browser.get("screenshots", [])
    add(errors, isinstance(screenshots, list) and len(screenshots) == 4, "V27 browser inspection lacks four scene screenshots")
    if isinstance(screenshots, list):
        for screenshot in screenshots:
            path = ROOT / str(screenshot.get("path", ""))
            add(errors, path.is_file() and sha256(path) == screenshot.get("sha256"), "V27 browser screenshot is missing or hash drifted")
    result = {
        "schema": "companion.v27_face_action_gesture_special_expression_machine_closure.v1",
        "status": "PASS_V27_FACE_ACTION_GESTURE_MACHINE_CLOSURE_RUNTIME_INACTIVE" if not errors else "FAIL_V27_FACE_ACTION_GESTURE_MACHINE_CLOSURE",
        "claim_scope": "source-to-component-to-browser/target machine closure for an unbound runtime-inactive candidate; no firmware binding, CRIG/profile export, flash, panel output, physical acceptance, or human art acceptance",
        "locked_v9_source": {"path": rel(LOCKED_V9), "sha256": LOCKED_V9_SHA256},
        "artifacts": records,
        "selection_policy": route.get("selection_policy"),
        "next_human_boundary": "canonical browser-only Chinese owner art review of the V27 candidate; any FAIL returns to generated-source refinement before a CRIG/profile or behavior binding",
        "physical_gate": "PENDING_CURRENT_FPC_OFFICIAL_WHITE_BLACK_GATE",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "errors": errors,
    }
    WRITE.parent.mkdir(parents=True, exist_ok=True)
    WRITE.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        print("FAIL: V27 special-expression machine closure", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: V27 special-expression machine closure -> {rel(WRITE)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
