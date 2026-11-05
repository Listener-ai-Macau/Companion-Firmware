#!/usr/bin/env python3
"""Archive a reproducible fail-closed COMP-REQ-467 browser-source blocker."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_PAGE_SHA = "D68478DAB33D4B2F13E5A62B63A65F1A9B37593C3551D8B19444731EA6C22116"
EXPECTED_PRIOR_SHA = "9A831B882E24D5C1726B674BA40D8187F5E726E00A234BA3FFDACD33AD215123"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): file_sha(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-capture", required=True, type=Path)
    parser.add_argument("--rerun-capture", required=True, type=Path)
    parser.add_argument("--diagnostic", required=True, type=Path)
    parser.add_argument("--pointer-result", required=True, type=Path)
    parser.add_argument("--export-path", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    canonical_dir = args.canonical_capture.resolve()
    rerun_dir = args.rerun_capture.resolve()
    canonical = read_json(canonical_dir / "capture-manifest.json")
    rerun = read_json(rerun_dir / "capture-manifest.json")
    diagnostic = read_json(args.diagnostic.resolve())
    pointer = read_json(args.pointer_result.resolve())
    canonical_tree = tree_hashes(canonical_dir)
    rerun_tree = tree_hashes(rerun_dir)
    mismatch = [
        {
            "path": path,
            "canonical": canonical_tree.get(path),
            "rerun": rerun_tree.get(path),
        }
        for path in sorted(set(canonical_tree) | set(rerun_tree))
        if canonical_tree.get(path) != rerun_tree.get(path)
    ]
    failed_capture_checks = sorted(
        item["id"] for item in canonical["checks"]["items"] if not item["pass"]
    )
    expected_failed_checks = ["desktop.menu_return", "mobile.menu_return"]
    blockers = diagnostic["blockers"]
    expected_blockers = all(
        item["state"] == "menu_return_rest"
        and item["stale"] == 1
        and item["overlap"] == 1
        and item["clipping"] == 1
        and item["visible_roles"] == ["face_base", "gaze_highlight", "exclusive_menu"]
        for item in blockers
    )
    evidence_checks = {
        "accepted_page_identity": canonical["source"]["page_sha256"] == EXPECTED_PAGE_SHA
        and rerun["source"]["page_sha256"] == EXPECTED_PAGE_SHA
        and pointer["page_sha256"] == EXPECTED_PAGE_SHA,
        "accepted_prior_20_of_20_identity": canonical["source"]["prior_20_of_20_sha256"]
        == EXPECTED_PRIOR_SHA,
        "deterministic_capture_rerun_byte_equal": not mismatch,
        "exact_two_menu_return_failures": failed_capture_checks == expected_failed_checks,
        "measured_blocker_exact": len(blockers) == 2 and expected_blockers,
        "measured_source_black_pixels_outside_zero": diagnostic["measured_totals"][
            "source_black_pixels_outside_stage"
        ]
        == 0,
        "measured_stale_and_overlap_two": diagnostic["measured_totals"]["stale_layer_count"]
        == 2
        and diagnostic["measured_totals"]["conflicting_surface_overlap_count"] == 2,
        "state_specific_edge_policy": diagnostic["policy_derived_totals"]["no_global_edge_policy"]
        is True,
        "policy_clipping_violations_two": diagnostic["policy_derived_totals"][
            "clipping_violation_count"
        ]
        == 2,
        "real_hold_route_exactly_once": all(
            item["route_exactly_once"]
            and item["menu_entries"] == 1
            and item["recording_entries"] == 0
            for item in diagnostic["hold_feedback_binding"]["real_pointer_regressions"]
        ),
        "fresh_pointer_mouse_touch_pen_pass": pointer["status"] == "PASS"
        and set(pointer["scenarios"]) == {"desktop", "mobile"},
        "http_404_zero": canonical["checks"]["http_404_count"] == 0 and not canonical["errors"],
        "firmware_contract_not_emitted": not args.export_path.resolve().exists(),
    }
    evidence_failed = sorted(name for name, passed in evidence_checks.items() if not passed)
    result = {
        "schema": "companion.comp-req-467-no-go-result.v1",
        "requirement": "COMP-REQ-467/469",
        "status": "NO_GO_BROWSER_SOURCE_MENU_RETURN_STALE",
        "source": {
            "page_sha256": canonical["source"]["page_sha256"],
            "prior_20_of_20_sha256": canonical["source"]["prior_20_of_20_sha256"],
        },
        "reason": (
            "The accepted page leaves exclusive_menu visible after returnToExpression; "
            "desktop and mobile each render face_base, gaze_highlight, and exclusive_menu together."
        ),
        "fresh_capture": {
            "passed": canonical["checks"]["passed"],
            "total": canonical["checks"]["total"],
            "failed_checks": failed_capture_checks,
            "http_404": canonical["checks"]["http_404_count"],
        },
        "measured": diagnostic["measured_totals"],
        "policy_derived": diagnostic["policy_derived_totals"],
        "hold_feedback_binding": diagnostic["hold_feedback_binding"],
        "blockers": blockers,
        "deterministic_rerun": {
            "file_count": len(canonical_tree),
            "mismatches": mismatch,
        },
        "pointer_result": {
            "status": pointer["status"],
            "sha256": file_sha(args.pointer_result.resolve()),
            "viewports": sorted(pointer["scenarios"]),
        },
        "firmware_visual_contract_emitted": False,
        "evidence_checks": evidence_checks,
        "evidence_check_failures": evidence_failed,
        "boundaries": {
            "accepted_page_modified": False,
            "firmware_driver_hardware_platform_production_changes": 0,
            "hardware_contact": 0,
            "operator_prompt_count": 0,
            "push_count": 0,
        },
        "required_next_action": (
            "A separately reviewed browser-source correction must hide #integrated-menu on menu return, "
            "then COMP-REQ-467 must be rerun from the newly accepted page identity."
        ),
    }
    write_json(args.output.resolve(), result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "result": str(args.output.resolve()),
                "evidence_checks": f"{sum(evidence_checks.values())}/{len(evidence_checks)}",
                "deterministic_mismatches": len(mismatch),
            },
            indent=2,
        )
    )
    return 0 if not evidence_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
