#!/usr/bin/env python3
"""Verify the build-only V9 manual-step panel-path diagnostic contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
BUILD_SCRIPT = ROOT / "tools/build_nucleo_bringup.ps1"
MANIFEST = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json"
BUNDLED_CEMP = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/companion-v9-expression-candidate-200x200.cemp"
V9_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
BINDING = ROOT / "app/companion_pendant/epaper/v9_candidate_resource_binding.c"
SCHEMA_ID = "companion.wb55.v9_manual_step_diagnostic.v1"
LOCKED_CEMP_SHA256 = "B89E6EA1D6583063969D48D28EE3D9BF444408D4347BC4974259DD75D0633F26"
LOCKED_V9_SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EXPECTED_CLIPS = ("idle", "touch", "swipe_left", "swipe_right")


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def evaluate() -> dict[str, Any]:
    app = APP_BLE.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    build = BUILD_SCRIPT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    binding = BINDING.read_text(encoding="utf-8")
    clip_map = {clip.get("name"): clip for clip in manifest.get("clips", [])}
    manual_block = app.partition("static const char *const k_companion_v9_manual_step_clips[] = {")[2].partition("bool Companion_Screen_PlayDailyRigDemo")[0]
    checks = {
        "locked_v9_identity": manifest.get("name") == "companion-v9-expression-candidate-200x200"
        and manifest.get("revision") == 90
        and manifest.get("provenance", {}).get("source_sha256")
        == LOCKED_V9_SOURCE_SHA256,
        "locked_v9_source_hash": V9_SOURCE.is_file() and digest(V9_SOURCE) == LOCKED_V9_SOURCE_SHA256,
        "locked_cemp_hash": BUNDLED_CEMP.is_file() and digest(BUNDLED_CEMP) == LOCKED_CEMP_SHA256,
        "exact_step_clips_exist_with_three_frames": all(
            isinstance(clip_map.get(name), dict)
            and len(clip_map[name].get("frames", [])) == 3
            and clip_map[name]["frames"][2].get("source") == f"pbm/v9_{name}_settle.pbm"
            for name in EXPECTED_CLIPS
        ),
        "normal_runtime_remains_inactive": "bool comp_v9_candidate_resource_runtime_activation_allowed(void)\n{\n    return false;\n}" in binding,
        "manual_step_is_explicit_compile_time_demo": "#ifndef COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC" in app
        and "#if COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC" in app
        and "Stable Daily recovery and V9 manual-step diagnostic are separate images" in app,
        "manual_step_sequence_is_exact": all(f'    "{name}",' in manual_block for name in EXPECTED_CLIPS)
        and manual_block.find('"idle",') < manual_block.find('"touch",') < manual_block.find('"swipe_left",') < manual_block.find('"swipe_right",'),
        "only_settle_frame_is_rendered_full": all(
            token in manual_block
            for token in (
                "entry.frame_in_clip != 0u",
                "sustain.frame_in_clip != 1u",
                "snapshot.frame_in_clip != 2u",
                "Companion_Display_EmitEmoteFrameMode(COMP_EPAPER_REFRESH_FULL)",
                "comp_emote_player_stop(&s_companion_emote_player);",
                "frame=2 refresh=full player=stopped source=locked_v9_cemp",
            )
        ),
        "next_press_requires_drained_queue": "comp_epaper_display_queue_pending(&s_companion_display_queue) != 0u" in manual_block
        and "reason=resource_or_refresh_busy" in manual_block,
        "motion_cancellation_precedes_manual_player_start": "Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);" in manual_block
        and "comp_emote_player_play_now_name(&s_companion_emote_player, clip_name, false)" in manual_block
        and manual_block.find(
            "Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);"
        )
        < manual_block.find(
            "comp_emote_player_play_now_name(&s_companion_emote_player, clip_name, false)"
        ),
        "manual_step_excludes_rig_v22_and_behavior_logic": all(
            token not in manual_block
            for token in ("V22", "Rig", "comp_expression_rig", "Companion_PetBehavior", "Companion_PetPerformance")
        ),
        "screen_tap_is_the_only_diagnostic_advance": "const bool queued = Companion_Screen_V9ManualStepDiagnosticAdvance();" in main
        and "[touch-ui] v9_manual_step result=%s source=screen_tap x=%u y=%u" in main
        and "[v9-manual-step] action=ignored source=board_button name=%s" in main,
        "build_requires_explicit_external_nor_provisioning": "V9 manual-step diagnostic requires -ScreenAssetProvision" in build
        and "EPAPER_V9_MANUAL_STEP_DIAGNOSTIC=1" in build
        and "EPAPER_SSD1681_VERBOSE_TRACE=1" in build
        and "TOUCH_VERBOSE_TRACE=1" in build
        and "BUILD_DIR=build_v9_manual_step_diagnostic" in build,
        "build_verifier_never_flashes_hardware": "flash_nucleo_bringup.ps1" not in build,
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
            result["failures"].append("manual_step_image_missing")
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
                result["failures"].append("manual_step_cemp_mismatch")
    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_BUILD_ONLY_PHYSICAL_DIAGNOSTIC_NOT_FLASHED"
        if not result["failures"]
        else "NO_GO_V9_MANUAL_STEP_DIAGNOSTIC_INCOMPLETE",
        "claim_scope": "build_only_locked_v9_static_panel_path_comparator_not_product_animation",
        "manual_step_sequence": list(EXPECTED_CLIPS),
        "rendered_frame_in_clip": 2,
        "refresh_mode": "full",
        "checks": result["checks"],
        "failures": result["failures"],
        "image": image,
        "provisioned_cemp": provisioned_cemp,
        "physical_flash_gate": "Requires explicit owner start for one controlled diagnostic; it does not clear the White/Black, FTS02, or rail gates.",
        "sources": {
            "app_ble": {"path": rel(APP_BLE), "sha256": digest(APP_BLE)},
            "main": {"path": rel(MAIN), "sha256": digest(MAIN)},
            "build_script": {"path": rel(BUILD_SCRIPT), "sha256": digest(BUILD_SCRIPT)},
            "locked_v9_source": {"path": rel(V9_SOURCE), "sha256": digest(V9_SOURCE)},
            "v9_manifest": {"path": rel(MANIFEST), "sha256": digest(MANIFEST)},
            "locked_v9_cemp": {"path": rel(BUNDLED_CEMP), "sha256": digest(BUNDLED_CEMP)},
            "v9_binding": {"path": rel(BINDING), "sha256": digest(BINDING)},
        },
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["failures"]:
        print(f"NO_GO: V9 manual-step diagnostic verification failed -> {rel(destination)}", file=sys.stderr)
        return 1
    print(f"PASS: V9 manual-step diagnostic build contract -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
