"""Compose all current COMP-REQ-776 evidence into one machine receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / ".cache/validation/comp775-browser-parity-audit-20260812"
DEFAULT_OUTPUT = AUDIT / "MACHINE_READY.json"
FILES = {
    "identity": AUDIT / "IDENTITY_CHAIN.json",
    "expression_completeness": AUDIT / "EXPRESSION_COMPLETENESS.json",
    "browser_pointer": AUDIT / "pointer-current/MACHINE_READY.json",
    "browser_dom": AUDIT / "DOM_LAYOUT.json",
    "gallery": AUDIT / "expression-risk-and-ten-families.json",
    "comp_req_775": ROOT / ".cache/validation/comp775-screen-final-goal-r86-20260812/MACHINE_READY.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence = {name: load(path) for name, path in FILES.items()}
    identity = evidence["identity"]
    complete = evidence["expression_completeness"]
    pointer = evidence["browser_pointer"]
    dom = evidence["browser_dom"]
    gallery = evidence["gallery"]
    comp775 = evidence["comp_req_775"]
    behavior_sha = identity["identity_graph"]["behavior_page"]["sha256"]
    resource_sha = identity["identity_graph"]["resource_page"]["sha256"]
    resource_id = identity["identity_graph"]["generation_18"]["resource_id"]

    checks = {
        "one_traceable_layered_identity_manifest": (
            identity.get("status") == "MACHINE_READY"
            and not identity.get("failed_checks")
        ),
        "all_5059_states_strict_1bpp_and_not_truncated": (
            complete.get("status") == "MACHINE_READY"
            and complete.get("state_count") == 5059
            and complete.get("failure_count") == 0
            and all(complete.get("checks", {}).values())
        ),
        "browser_pbm_generation_row_map_and_staging_are_exact": (
            complete.get("checks", {}).get("generation_18_reconstructs_all_states") is True
            and complete.get("checks", {}).get("controller_row_map_is_lossless") is True
            and complete.get("checks", {}).get("all_states_are_exact_after_source_complete_staging") is True
        ),
        "current_browser_gestures_use_current_page_without_errors": (
            pointer.get("verdict") == "MACHINE_READY"
            and pointer.get("expected_page_sha256") == behavior_sha
            and pointer.get("browser_errors") == []
            and len(pointer.get("page_loads", [])) == 4
            and all(row.get("body_sha256") == behavior_sha for row in pointer.get("page_loads", []))
        ),
        "desktop_and_mobile_dom_do_not_clip_canvas": (
            dom.get("status") == "MACHINE_READY"
            and dom.get("behavior_page_sha256") == behavior_sha
            and dom.get("browser_errors") == []
            and len(dom.get("cases", [])) == 2
            and all(not row["geometry"]["ancestor_clip_violation"] for row in dom.get("cases", []))
        ),
        "four_edge_and_ten_family_gallery_is_ready": (
            gallery.get("status") == "MACHINE_READY"
            and gallery.get("source_state_count") == 5059
            and gallery.get("four_edge_risk_count") == 4
            and gallery.get("family_count") == 10
            and gallery.get("panel_count") == 14
            and sha256(ROOT / gallery["png"]) == gallery.get("png_sha256")
        ),
        "behavior_resource_and_generation_identity_agree": (
            pointer.get("resource_page_sha256") == resource_sha
            and pointer.get("product_resource_id") == resource_id
            and complete.get("identity", {}).get("resource_page_sha256") == resource_sha
            and complete.get("identity", {}).get("resource_id") == resource_id
        ),
        "r86_current_host_and_source_audits_pass": (
            identity.get("checks", {}).get("current_host_contracts_pass") is True
            and identity.get("checks", {}).get("deleted_automatic_motion_symbol_is_absent") is True
            and identity.get("checks", {}).get("r86_binary_contains_generation_resource_identity") is True
        ),
        "historical_d308_is_quarantined_without_exception": (
            identity.get("checks", {}).get("historical_d308_verifier_is_nonexceptional_and_excluded") is True
        ),
        "comp_req_775_remains_machine_ready": (
            comp775.get("status") == "MACHINE_READY"
            and all(comp775.get("checks", {}).values())
        ),
        "no_app_resource_loader_or_recording_write": (
            identity.get("writes_this_goal")
            == {"app_flash_bytes": 0, "external_resource_bytes": 0, "loader_bytes": 0}
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.comp_req_776.completion.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "identity": {
            "behavior_page_sha256": behavior_sha,
            "resource_page_sha256": resource_sha,
            "base_cemp_sha256": identity["identity_graph"]["base_cemp"]["cemp_sha256"],
            "generation": identity["identity_graph"]["generation_18"]["active_generation"],
            "resource_id": resource_id,
            "r86_bin_sha256": identity["identity_graph"]["r86"]["bin_sha256"],
        },
        "coverage": {
            "states": complete.get("state_count"),
            "unique_frames": complete.get("unique_frame_count"),
            "kinds": complete.get("kind_counts"),
            "pixel_or_edge_failures": complete.get("failure_count"),
            "browser_fresh_loads": len(pointer.get("page_loads", [])),
            "browser_errors": len(pointer.get("browser_errors", [])),
            "dom_viewports": [row["viewport"]["name"] for row in dom.get("cases", [])],
            "gallery_panels": gallery.get("panel_count"),
        },
        "evidence": {
            name: {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(path),
            }
            for name, path in FILES.items()
        },
        "gallery": gallery.get("png"),
        "writes_this_goal": identity.get("writes_this_goal"),
        "human_boundary": {
            "status": "PENDING",
            "scope": "browser gallery only; resource and firmware are unchanged",
            "owner_result": "owner-result.txt",
        },
        "hardware_contact": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    # Compatibility entry point for callers that still use the original name.
    # Its generation-18 audit directory is historical; current closure is the
    # generation-20 component-fix gate.
    from verify_comp_req_776_component_fix_completion import main as current_main

    raise SystemExit(current_main())
