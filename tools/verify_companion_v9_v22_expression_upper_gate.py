#!/usr/bin/env python3
"""Close the runtime-inactive upper V9/V22 Rig admission without driver work."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
DEFAULTS = {
    "v9_parity": "docs/validation/companion-v9-rig-touch-emotion-machine-parity-r2-20260720.json",
    "route": "docs/validation/companion-v9-v22-touch-emotion-route-preview-r2-20260720.json",
    "route_parity": "docs/validation/companion-v9-v22-touch-emotion-route-parity-r2-20260720.json",
    "browser_pixels": "docs/validation/companion-v9-v22-touch-emotion-route-browser-pixels-r2-20260720.json",
    "everyday_router": "docs/validation/companion-v22-everyday-bridge-router-r2-20260720.json",
    "target_rig": "docs/validation/companion-v22-emotion-separation-target-rig-gate-r2-20260720.json",
    "wba_host": "docs/validation/companion-v22-emotion-separation-target-rig-wba-host-20260719.json",
    "build_dir": "cubeide/Companion_Nucleo_WB55RG_Bringup/build_v22_emotion_bridge_demo_0",
}


def resolve(value: str) -> pathlib.Path:
    path = pathlib.Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def status_is(data: dict[str, Any], expected: str) -> bool:
    return data.get("status") == expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in DEFAULTS.items():
        parser.add_argument(f"--{name.replace('_', '-')}", default=default)
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    paths = {name: resolve(getattr(args, name)) for name in DEFAULTS if name != "build_dir"}
    build_dir = resolve(args.build_dir)
    write_path = resolve(args.write)
    artifacts = {name: load(path) for name, path in paths.items()}
    v9_parity = artifacts["v9_parity"]
    route = artifacts["route"]
    route_parity = artifacts["route_parity"]
    browser_pixels = artifacts["browser_pixels"]
    everyday_router = artifacts["everyday_router"]
    target_rig = artifacts["target_rig"]
    wba_host = artifacts["wba_host"]
    image_stem = "Companion_Nucleo_WB55RG_V22EmotionBridgeDemo_0"
    build_files = {
        "hex": build_dir / f"{image_stem}.hex",
        "elf": build_dir / f"{image_stem}.elf",
        "map": build_dir / f"{image_stem}.map",
        "everyday_router_object": build_dir / "expression_v22_everyday_bridge_router.o",
        "everyday_session_object": build_dir / "expression_v22_everyday_bridge_session.o",
        "provisioned_candidate_blob": build_dir / "generated/companion-v22-emotion-separation-rig-candidate-200x200.crig",
    }
    map_text = build_files["map"].read_text(encoding="utf-8", errors="replace") if build_files["map"].is_file() else ""
    source_pack = resolve(str(target_rig.get("pack", "")))
    checks = {
        "locked_v9_identity_is_preserved": LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256,
        "v9_touch_score_browser_target_parity_passes": status_is(
            v9_parity, "PASS_TOUCH_EMOTION_BROWSER_TARGET_PARITY_RUNTIME_INACTIVE"
        ),
        "v22_route_is_event_driven_runtime_inactive": (
            status_is(route, "PASS_V9_V22_TOUCH_EMOTION_ROUTE_RUNTIME_INACTIVE") and
            route.get("runtime_resource_activated") is False and
            route.get("selection_policy", {}).get("random_emotion_selection") is False and
            route.get("selection_policy", {}).get("automatic_cross_emotion_cycle") is False
        ),
        "v22_browser_target_component_plan_parity_passes": status_is(
            route_parity, "PASS_V9_V22_TOUCH_EMOTION_ROUTE_PARITY_RUNTIME_INACTIVE"
        ),
        "native_browser_daily_and_warm_pixels_match_target_pbms": status_is(
            browser_pixels, "PASS_BROWSER_RENDER_PIXEL_PARITY_NATIVE_200X200"
        ),
        "v22_everyday_router_covers_all_accepted_causal_edges_without_special_event_binding": (
            status_is(everyday_router, "PASS_V22_EVERYDAY_BRIDGE_ROUTER_RUNTIME_INACTIVE") and
            everyday_router.get("runtime_resource_activated") is False and
            everyday_router.get("candidate_runtime_activation_allowed") is False and
            everyday_router.get("ordinary_affect_only") is True and
            everyday_router.get("bridge_count") == 10 and
            everyday_router.get("replayed_step_count") == 72 and
            everyday_router.get("session_visible_step_count") == 72 and
            everyday_router.get("session_requires_visible_acknowledgement") is True and
            everyday_router.get("session_min_post_refresh_hold_ms") == 750 and
            everyday_router.get("unbound_product_states") == [
                "menu", "recording", "upgrade", "sleep", "charging", "error"
            ]
        ),
        "external_nor_component_pack_and_special_fail_closed_policy_pass": (
            status_is(target_rig, "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_GATE") and
            target_rig.get("runtime_resource_activated") is False and
            target_rig.get("special_event_fallback") == {
                "menu": "fail_closed", "recording": "fail_closed", "upgrade": "fail_closed",
                "sleep": "fail_closed", "charging": "fail_closed", "error": "fail_closed",
            }
        ),
        "wba_external_nor_component_replay_passes": (
            status_is(wba_host, "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_WBA_EXTERNAL_NOR_PARITY")
        ),
        "wb55_v22_candidate_build_contains_component_bridge_and_exact_crig": (
            all(path.is_file() for path in build_files.values()) and source_pack.is_file() and
            sha256(build_files["provisioned_candidate_blob"]) == sha256(source_pack) and
            "comp_v22_emotion_separation_rig_candidate_profile" in map_text and
            "comp_v22_emotion_separation_rig_candidate_bridge" in map_text
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.v9_v22_expression_upper_gate.v1",
        "status": "PASS_V9_V22_EXPRESSION_UPPER_GATE_RUNTIME_INACTIVE" if not failures else "FAIL_V9_V22_EXPRESSION_UPPER_GATE",
        "claim_scope": "upper_expression_rig_choreography_browser_target_and_build_admission_only_not_driver_change_flash_or_physical_panel_acceptance",
        "driver_workstream": "delegated_to_separate_ai_per_comp_req_229",
        "runtime_resource_activated": False,
        "candidate_provision_or_flash_performed_by_this_gate": False,
        "checks": checks,
        "failures": failures,
        "artifacts": {
            name: {"path": rel(path), "sha256": sha256(path)} for name, path in paths.items()
        } | {
            "candidate_source_pack": {"path": rel(source_pack), "sha256": sha256(source_pack)} if source_pack.is_file() else None,
            "candidate_build": {
                name: {"path": rel(path), "sha256": sha256(path)} if path.is_file() else None
                for name, path in build_files.items()
            },
        },
        "next_boundary": "No driver, LUT, refresh-policy, hardware or physical panel action belongs to this upper-expression gate.",
    }
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print(f"FAIL: V9/V22 upper expression gate -> {rel(write_path)}", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(f"PASS: V9/V22 upper expression gate -> {rel(write_path)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
