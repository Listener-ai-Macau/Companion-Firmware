#!/usr/bin/env python3
"""Verify the build-only, one-frame V9 stable daily recovery image contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
BUILD_SCRIPT = ROOT / "tools/build_nucleo_bringup.ps1"
MANIFEST = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json"
BUNDLED_CEMP = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/companion-v9-expression-candidate-200x200.cemp"
BINDING = ROOT / "app/companion_pendant/epaper/v9_candidate_resource_binding.c"
SCHEMA_ID = "companion.wb55.v9_stable_daily_recovery.v1"
LOCKED_CEMP_SHA256 = "B89E6EA1D6583063969D48D28EE3D9BF444408D4347BC4974259DD75D0633F26"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def evaluate() -> dict[str, Any]:
    app = APP_BLE.read_text(encoding="utf-8")
    build = BUILD_SCRIPT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    binding = BINDING.read_text(encoding="utf-8")
    idle = next((clip for clip in manifest.get("clips", []) if clip.get("name") == "idle"), None)
    checks = {
        "locked_v9_identity": manifest.get("name") == "companion-v9-expression-candidate-200x200"
        and manifest.get("revision") == 90
        and manifest.get("provenance", {}).get("source_sha256")
        == "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA",
        "idle_has_exact_three_rendered_frames": isinstance(idle, dict) and len(idle.get("frames", [])) == 3,
        "locked_cemp_hash": BUNDLED_CEMP.is_file() and digest(BUNDLED_CEMP) == LOCKED_CEMP_SHA256,
        "normal_runtime_remains_inactive": "bool comp_v9_candidate_resource_runtime_activation_allowed(void)\n{\n    return false;\n}" in binding,
        "demo_is_explicit_and_compile_time_gated": "#ifndef COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO" in app
        and "#if COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO" in app
        and "const bool visual_resource_activation_allowed = true;" in app,
        "demo_selects_only_idle_settle": all(
            token in app
            for token in (
                "comp_emote_player_play_now_name(&s_companion_emote_player, \"idle\", false)",
                "entry.frame_in_clip != 0u",
                "sustain.frame_in_clip != 1u",
                "snapshot.frame_in_clip != 2u",
                "Companion_Display_EmitEmoteFrameMode(COMP_EPAPER_REFRESH_FULL)",
                "comp_emote_player_stop(&s_companion_emote_player);",
                "[stable-daily-recovery] result=queued clip=idle frame=2 refresh=full player=stopped source=locked_v9_cemp",
            )
        ),
        "demo_refuses_other_expression_producers": "Stable Daily recovery must be the sole expression producer" in app,
        "build_requires_explicit_external_nor_provisioning": "Stable Daily recovery requires -ScreenAssetProvision" in build
        and "EPAPER_STABLE_DAILY_RECOVERY_DEMO=1" in build
        and "BUILD_DIR=build_v9_stable_daily_recovery" in build,
        "no_hardware_flash_in_build_verifier": "flash_nucleo_bringup.ps1" not in build,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {"checks": checks, "failures": failures}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    parser.add_argument("--image", type=pathlib.Path)
    args = parser.parse_args(argv)
    result = evaluate()
    image = None
    provisioned_cemp = None
    if args.image is not None:
        image_path = args.image if args.image.is_absolute() else ROOT / args.image
        image = {
            "path": rel(image_path),
            "exists": image_path.is_file(),
            "sha256": digest(image_path) if image_path.is_file() else None,
        }
        if not image["exists"]:
            result["failures"].append("stable_recovery_image_missing")
        else:
            provisioned_path = image_path.parent / "generated" / BUNDLED_CEMP.name
            provisioned_cemp = {
                "path": rel(provisioned_path),
                "exists": provisioned_path.is_file(),
                "sha256": digest(provisioned_path) if provisioned_path.is_file() else None,
            }
            result["checks"]["provisioned_cemp_byte_identical_to_locked_v9"] = (
                provisioned_cemp["exists"]
                and provisioned_cemp["sha256"] == LOCKED_CEMP_SHA256
            )
            if not result["checks"]["provisioned_cemp_byte_identical_to_locked_v9"]:
                result["failures"].append("stable_recovery_cemp_mismatch")
    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_BUILD_ONLY_PHYSICAL_FLASH_BLOCKED" if not result["failures"] else "NO_GO_STABLE_RECOVERY_BUILD_INCOMPLETE",
        "claim_scope": "build_only_locked_v9_idle_settle_no_hardware_or_panel_acceptance",
        "checks": result["checks"],
        "failures": result["failures"],
        "image": image,
        "provisioned_cemp": provisioned_cemp,
        "physical_flash_gate": "Blocked until a later official White PASS and ordered Black PASS under COMP-REQ-145.",
        "sources": {
            "app_ble": {"path": rel(APP_BLE), "sha256": digest(APP_BLE)},
            "build_script": {"path": rel(BUILD_SCRIPT), "sha256": digest(BUILD_SCRIPT)},
            "v9_manifest": {"path": rel(MANIFEST), "sha256": digest(MANIFEST)},
            "locked_v9_cemp": {"path": rel(BUNDLED_CEMP), "sha256": digest(BUNDLED_CEMP)},
            "v9_binding": {"path": rel(BINDING), "sha256": digest(BINDING)},
        },
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["failures"]:
        print(f"NO_GO: stable daily recovery verification failed -> {rel(destination)}", file=sys.stderr)
        return 1
    print(f"PASS: stable daily recovery build contract -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
