#!/usr/bin/env python3
"""Verify the current portable behavior plus external-CEMP expression boundary."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EPAPER = ROOT / "app" / "companion_pendant" / "epaper"
BEHAVIOR_H = EPAPER / "pet_behavior.h"
BEHAVIOR_C = EPAPER / "pet_behavior.c"
PANEL_C = EPAPER / "panel_target_stm32wb_ssd1681.c"
APP_BLE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SYSTEM_DOC = ROOT / "docs" / "companion_screen_expression_system.md"
RESOURCE_POLICY = ROOT / "docs" / "validation" / "companion-screen-resource-memory-policy.json"
WBA_DOC = ROOT / "docs" / "stm32wba_migration_rules.md"
V9_BASELINE = ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9" / "baseline-lock.json"
V9_BINDING = ROOT / "docs" / "validation" / "companion-v9-candidate-resource-binding-20260717.json"
RUNTIME_BOUNDARY = ROOT / "docs" / "validation" / "companion-runtime-visual-boundary-20260717.json"
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-pet-expression-system.json")

V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(read(path))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, object]:
    return {
        "schema_id": "companion.screen.external_expression_system.v2",
        "status": "PASS",
        "purpose": "Machine-checkable current Goal contract for portable pet behavior and approved external-CEMP visual playback.",
        "visual_baseline": {
            "iteration": "companion-pet-expression-v9",
            "source_sha256": V9_SHA256,
            "runtime_resource_activated": False,
            "rule": "The approved v9 source is the sole inner-face candidate; no legacy, rejected, test, or code-drawn face may substitute for it.",
        },
        "behavior": {
            "source": "app/companion_pendant/epaper/pet_behavior.h/.c",
            "role": "portable event and mood state only; it selects a semantic expression but does not compose product pixels",
            "state": ["valence", "arousal", "curiosity", "affection", "attachment", "engagement", "stroke direction", "personality"],
            "memory_contract": "comp_pet_behavior_memory_t remains target-owned external user-data payload; portable behavior never writes Flash",
        },
        "event_bridge": {
            "touch": "touch and stroke events update portable behavior before the external emote player receives an expression decision",
            "product_state": "recording, power and connection states remain semantic behavior inputs; visual frames come only from CEMP",
            "expression_transport": "COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION carrying a CEMP player frame",
        },
        "resource_policy": {
            "external": "CEMP stores replaceable v9 timelines, menu bases, fonts and larger product assets in ui_assets",
            "unavailable": "fail closed: keep the existing panel image and report transport/resource failure without drawing a substitute",
            "internal": "application code, behavior state, drivers and parser only; no linked full-frame face arrays or complete code-rendered menu",
        },
        "runtime_guard": {
            "expression_maintenance": "replay the last external CEMP frame only",
            "forbidden": ["procedural face", "test pattern", "complete code-rendered menu", "legacy r53 visual fallback"],
        },
        "wba_port": "Reuse behavior, CEMP/parser and callback-only external-NOR contract; WBA adapters must not revive the retired procedural composer.",
    }


def check(errors: list[str]) -> None:
    required = (
        BEHAVIOR_H, BEHAVIOR_C, PANEL_C, APP_BLE, MAKEFILE, SYSTEM_DOC,
        RESOURCE_POLICY, WBA_DOC, V9_BASELINE, V9_BINDING, RUNTIME_BOUNDARY,
    )
    for path in required:
        require(path.is_file(), f"missing required path: {path.relative_to(ROOT)}", errors)
    if errors:
        return

    behavior = read(BEHAVIOR_H) + "\n" + read(BEHAVIOR_C)
    panel = read(PANEL_C)
    app_ble = read(APP_BLE)
    makefile = read(MAKEFILE)
    system_doc = read(SYSTEM_DOC)
    wba_doc = read(WBA_DOC)
    resource_policy = load(RESOURCE_POLICY)
    baseline = load(V9_BASELINE)
    binding = load(V9_BINDING)
    runtime = load(RUNTIME_BOUNDARY)

    for token in (
        "comp_pet_behavior_t", "comp_pet_behavior_init", "comp_pet_behavior_advance",
        "comp_pet_behavior_apply_expression", "comp_pet_behavior_note_touch",
        "comp_pet_behavior_note_stroke", "comp_pet_behavior_stroke_direction",
        "comp_pet_behavior_mood", "comp_pet_behavior_export_memory",
        "comp_pet_behavior_import_memory", "comp_pet_behavior_self_test",
        "valence", "arousal", "curiosity", "affection", "attachment",
    ):
        require(token in behavior, f"portable behavior missing {token}", errors)
    for forbidden in ("HAL_", "GPIO", "QSPI", "SPI", "I2C", "STM32", "UTIL_SEQ"):
        require(forbidden.lower() not in behavior.lower(),
                f"portable behavior must remain target-free: {forbidden}", errors)
    for forbidden in ("malloc(", "calloc(", "realloc(", "free("):
        require(forbidden not in behavior, f"portable behavior must not allocate: {forbidden}", errors)

    for token in (
        "comp_emote_asset_pack_mount", "comp_emote_player_init",
        "Companion_Display_EmitEmoteFrameMode", "source=external_flash",
        "comp_pet_behavior_note_touch", "comp_pet_behavior_note_stroke",
        "comp_pet_behavior_apply_expression", "expression_maintenance source=external_flash",
    ):
        require(token in app_ble, f"WB55 external-CEMP event bridge missing {token}", errors)
    for token in (
        "frame_prepare", "source=external_flash",
        "source=unavailable kind=%u; suppressing visual fallback",
        "COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR",
    ):
        require(token in panel, f"SSD1681 external-CEMP path missing {token}", errors)

    retired_app_tokens = (
        '#include "pet_expression.h"', "Companion_Display_EnqueuePetPose",
        "comp_pet_expression_render", "pet_expression_selftest",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_display_queue_enqueue_pet_expression", "s_companion_last_pet_pose",
    )
    retired_panel_tokens = (
        "comp_pet_expression_render", "source=procedural", "frame_test_pattern",
        "comp_screen_menu_render(",
    )
    for token in retired_app_tokens:
        require(token not in app_ble, f"retired procedural app route remains: {token}", errors)
    for token in retired_panel_tokens:
        require(token not in panel, f"retired procedural panel route remains: {token}", errors)
    require("$(ROOT)/app/companion_pendant/epaper/pet_expression.c" not in makefile,
            "WB55 Makefile must not compile the retired pet_expression.c", errors)
    require("$(ROOT)/app/companion_pendant/epaper/pet_behavior.c" in makefile,
            "WB55 Makefile does not compile portable pet_behavior.c", errors)

    require("## Current Goal Expression Boundary" in system_doc,
            "expression system document lacks active Goal override", errors)
    require("external CEMP" in system_doc and "retired procedural composer" in system_doc,
            "expression system document lacks current external-CEMP boundary", errors)
    require("companion-pet-expression-v9" in wba_doc and "retired procedural face composer" in wba_doc,
            "WBA migration rules lack current visual portability boundary", errors)

    require(baseline.get("status") == "OWNER_APPROVED_SOURCE_LOCKED_MACHINE_RENDER_AUTHORIZED",
            "v9 baseline is not owner-locked", errors)
    require(baseline.get("accepted_source", {}).get("sha256") == V9_SHA256,
            "v9 baseline hash drifted", errors)
    require(binding.get("status") == "PASS_MACHINE_ONLY_INACTIVE",
            "v9 candidate binding is not inactive machine-only PASS", errors)
    candidate = binding.get("candidate_pack", {})
    require(candidate.get("name") == "companion-v9-expression-candidate-200x200"
            and candidate.get("revision") == 90
            and candidate.get("runtime_resource_activated") is False,
            "v9 candidate binding drifted or permits runtime activation", errors)
    current_boundary = resource_policy.get("current_goal_visual_boundary", {})
    require(current_boundary.get("active_inner_face_source") == "companion-pet-expression-v9"
            and current_boundary.get("active_inner_face_sha256") == V9_SHA256,
            "resource policy current v9 visual boundary drifted", errors)
    require("external CEMP base only" in str(current_boundary.get("product_runtime", "")),
            "resource policy permits an internal visual fallback", errors)
    runtime_policy = runtime.get("runtime_policy", {})
    require(runtime.get("status") == "PASS_CURRENT_SOURCE_NO_PROCEDURAL_VISUAL_FALLBACK",
            "runtime visual boundary is not PASS", errors)
    require(runtime_policy.get("active_expression_maintenance") == "external CEMP frame replay only",
            "runtime maintenance is not external CEMP only", errors)
    require(runtime_policy.get("retired_procedural_face_linked") is False,
            "retired procedural face is linked into product runtime", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write", action="store_true", help="write the deterministic architecture fixture")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    expected = build_fixture()
    check(errors)
    fixture = ROOT / args.fixture
    if not errors and args.write:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not errors and not args.write:
        require(fixture.is_file(), f"missing fixture: {fixture.relative_to(ROOT)}", errors)
        if fixture.is_file():
            require(json.loads(read(fixture)) == expected,
                    f"stale fixture: {fixture.relative_to(ROOT)}; rerun with --write", errors)
    if errors:
        print("external expression system: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("external expression system: PASS")
    print("  portable behavior, v9 external-CEMP playback, fail-closed visuals, and WBA reuse are guarded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
