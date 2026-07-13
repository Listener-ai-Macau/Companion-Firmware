#!/usr/bin/env python3
"""Verify the portable parameterized electronic-pet expression architecture."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EPAPER = ROOT / "app" / "companion_pendant" / "epaper"
PET_H = EPAPER / "pet_expression.h"
PET_C = EPAPER / "pet_expression.c"
PET_STYLE_H = EPAPER / "pet_visual_style.h"
PET_BEHAVIOR_H = EPAPER / "pet_behavior.h"
PET_BEHAVIOR_C = EPAPER / "pet_behavior.c"
QUEUE_H = EPAPER / "display_queue.h"
QUEUE_C = EPAPER / "display_queue.c"
PANEL_C = EPAPER / "panel_target_stm32wb_ssd1681.c"
APP_BLE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAIN_C = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
MAKEFILE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
SYSTEM_DOC = ROOT / "docs" / "companion_screen_expression_system.md"
RESOURCE_DOC = ROOT / "docs" / "companion_resource_memory_policy.md"
WBA_DOC = ROOT / "docs" / "stm32wba_migration_rules.md"
STYLE_DOC = ROOT / "docs/validation/companion-screen-generated-art-style-contract.md"
STYLE_SNAPSHOT = ROOT / "docs/validation/companion-screen-generated-art-style-contract.json"
STYLE_SNAPSHOT_MD = ROOT / "docs/validation/companion-screen-generated-art-style-contract.snapshot.md"
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-pet-expression-system.json")


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, object]:
    return {
        "schema_id": "companion.screen.pet_expression_system.v1",
        "status": "PASS",
        "purpose": "Machine-checkable architecture contract for the portable parameterized electronic-pet face.",
        "renderer": {
            "source": "app/companion_pendant/epaper/pet_expression.h/.c",
            "logical_coordinate_space": "200x200 logical coordinates scaled to every framebuffer at or above 64x64",
            "parameters": ["expression", "gaze_x", "gaze_y", "eye_open", "eyelid_tilt", "eye_width", "eye_spacing", "eye_pair_tilt", "highlight_scale", "face_shift_x", "face_shift_y", "brow", "brow_lift", "brow_asymmetry", "mouth", "mouth_scale", "cheek_strength", "mark", "variation"],
            "internal_full_screen_expression_arrays": 0,
            "persistent_extra_framebuffers": 0,
        },
        "event_bridge": {
            "daily_touch": "continuous logical touch coordinates update engagement and become a three-phase attentive response pose",
            "daily_stroke": "left/right/up/down logical finger travel becomes a direction-specific full-face response and bounded emotional update while the reserved menu-edge gesture keeps priority",
            "product_state": "all ten ExpressionV1 states advance a bounded valence/arousal/curiosity/affection/attachment mood model before composing a pose",
            "target_request_kind": "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        },
        "behavior": {
            "source": "app/companion_pendant/epaper/pet_behavior.h/.c",
            "state": ["valence", "arousal", "curiosity", "affection", "attachment", "mood", "engagement", "focus", "stroke direction", "stroke energy", "personality"],
            "refresh_contract": "behavior advances at real product-event or touch boundaries; it does not schedule an idle animation loop",
            "living_phase_contract": "product-state faces get sparse whole-face phase motion by adjusting face shift, eye width/opening, highlight, mouth scale, and cheeks without storing extra frames",
            "premium_art_contract": "generated-art principles are translated into procedural one-bit features: rounded pet nose/mouth, hollow thought bubbles, soft listening waves, tiny record dot, and small spark marks",
            "memory_contract": "comp_pet_behavior_memory_t is a target-owned, CRC/wear-aware external user-data payload; portable behavior never writes Flash",
        },
        "resource_policy": {
            "external": "CEMP keeps replaceable timelines, menu art, fonts, and larger product assets in ui_assets; emotion memory belongs in a separate target-owned user-data partition",
            "internal": "pet_behavior and pet_expression are compact deterministic application code and render into the existing framebuffer only",
        },
        "refresh_policy": "interactive differential refresh during contact; one generic quiet maintenance pass after the pet or menu has settled; full refresh remains boot/recovery only",
        "wba_port": "Reuse pose and renderer; replace only panel transport/profile facts in target-named adapters.",
    }


def check(errors: list[str]) -> None:
    for path in (PET_H, PET_C, PET_STYLE_H, PET_BEHAVIOR_H, PET_BEHAVIOR_C, QUEUE_H, QUEUE_C,
                 PANEL_C, APP_BLE, MAIN_C, MAKEFILE, SYSTEM_DOC, RESOURCE_DOC, WBA_DOC,
                 STYLE_DOC, STYLE_SNAPSHOT, STYLE_SNAPSHOT_MD):
        require(path.is_file(), f"missing required path: {path.relative_to(ROOT)}", errors)
    if errors:
        return

    header = read(PET_H)
    source = read(PET_C)
    style_header = read(PET_STYLE_H)
    behavior_header = read(PET_BEHAVIOR_H)
    behavior_source = read(PET_BEHAVIOR_C)
    queue = read(QUEUE_H) + "\n" + read(QUEUE_C)
    panel = read(PANEL_C)
    app_ble = read(APP_BLE)
    main_c = read(MAIN_C)
    makefile = read(MAKEFILE)
    style_snapshot = read(STYLE_SNAPSHOT)
    docs = (read(SYSTEM_DOC) + "\n" + read(RESOURCE_DOC) + "\n" + read(WBA_DOC) + "\n" +
            read(STYLE_DOC) + "\n" + style_snapshot + "\n" + read(STYLE_SNAPSHOT_MD))
    portable = header + "\n" + source + "\n" + style_header + "\n" + behavior_header + "\n" + behavior_source

    for token in (
        "comp_pet_expression_pose_t",
        "comp_pet_expression_pose_from_expression",
        "comp_pet_expression_pose_from_touch",
        "comp_pet_expression_render",
        "comp_pet_expression_self_test",
        "COMP_PET_MOUTH_SMILE",
        "COMP_PET_MOUTH_SOFT",
        "COMP_PET_BROW_WARM",
        "COMP_PET_MARK_SPARK",
        "eyelid_tilt",
        "eye_width",
        "eye_spacing",
        "eye_pair_tilt",
        "highlight_scale",
        "face_shift_x",
        "face_shift_y",
        "brow_lift",
        "brow_asymmetry",
        "mouth_scale",
        "screen_framebuffer.h",
    ):
        require(token in portable, f"portable pet composer missing {token}", errors)
    for expression in (
        "IDLE", "LISTENING", "THINKING", "SPEAKING", "HAPPY", "SLEEPY",
        "RECORDING", "SYNC_COMPLETE", "LOW_BATTERY", "ERROR",
    ):
        require(
            f"COMP_EPAPER_EXPRESSION_{expression}" in source,
            f"pet composer missing profile for ExpressionV1 {expression}",
            errors,
        )
    for token in (
        "PET_LOGICAL_MAX_X", "PET_LOGICAL_MAX_Y", "PET_MIN_RENDER_WIDTH",
        "map_logical_position", "map_logical_radius", "fill_logical_ellipse",
        "draw_logical_line", "draw_brow", "draw_mouth", "draw_eye_arc", "smiling_arc",
        "sleepy_arc", "lid_inner_y", "lid_outer_y", "framebuffer_signature",
        "profile_signatures", "64u", "stroke_logical_ellipse",
        "draw_small_spark", "COMP_PET_MARK_THINK", "COMP_PET_MARK_LISTEN",
        "COMP_PET_MARK_RECORD", "COMP_PET_MARK_SPARK",
        "pet_visual_style.h", "COMP_PET_STYLE_EYE_BASE_RX",
        "COMP_PET_STYLE_EYE_CENTER_Y", "COMP_PET_STYLE_MOUTH_CENTER_Y",
        "COMP_PET_STYLE_CHEEK_LEFT_X0",
    ):
        require(token in source, f"pet composer missing profile-scaled renderer token {token}", errors)
    for token in (
        "COMP_PET_STYLE_NAME",
        "genref_sheet_12_inner_faces_v5",
        "COMP_PET_STYLE_EYE_BASE_RX",
        "COMP_PET_STYLE_EYE_OPEN_RY_GAIN",
        "COMP_PET_STYLE_HIGHLIGHT_RX",
        "COMP_PET_STYLE_MOUTH_BASE_WIDTH",
        "COMP_PET_STYLE_CHEEK_DOT_LEFT_X",
        "physical shell",
    ):
        require(token in style_header, f"pet visual style contract missing {token}", errors)
    for token in (
        "Generated Art Style Contract",
        "pet_visual_style.h",
        "MENU_V3_STYLE",
        "external flash",
        "physical shell owns the cat outline",
        "companion.screen.generated_art_style_contract.v1",
        "style_names_match",
        "quick_adjustment_workflow_recorded",
    ):
        require(token in docs, f"generated-art style docs missing {token}", errors)
    require("* 64" in source and "- 32" in source,
            "touch pose must map continuous coordinates into signed gaze", errors)
    for forbidden in ("HAL_", "GPIO", "QSPI", "SPI", "I2C", "STM32", "UTIL_SEQ"):
        require(forbidden.lower() not in portable.lower(),
                f"pet composer must remain target-free: {forbidden}", errors)
    for forbidden in ("malloc(", "calloc(", "realloc(", "free("):
        require(forbidden not in portable, f"pet composer must not allocate: {forbidden}", errors)

    for token in (
        "comp_pet_behavior_t",
        "comp_pet_behavior_init",
        "comp_pet_behavior_advance",
        "comp_pet_behavior_apply_expression",
        "comp_pet_behavior_note_touch",
        "comp_pet_behavior_stroke_direction",
        "comp_pet_behavior_stroke_name",
        "comp_pet_behavior_note_stroke",
        "comp_pet_behavior_compose_expression_pose",
        "comp_pet_behavior_compose_touch_pose",
        "comp_pet_behavior_compose_stroke_pose",
        "comp_pet_behavior_mood",
        "comp_pet_behavior_mood_name",
        "comp_pet_behavior_export_memory",
        "comp_pet_behavior_import_memory",
        "comp_pet_behavior_self_test",
        "apply_living_phase",
        "mouth_scale + 6 + warmth",
        "pose->face_shift_y = clamp_face_shift",
        "pose->highlight_scale = clamp_percent",
        "COMP_PET_ENGAGEMENT_ENGAGED",
        "COMP_PET_STROKE_LEFT",
        "COMP_PET_STROKE_RIGHT",
        "COMP_PET_STROKE_UP",
        "COMP_PET_STROKE_DOWN",
        "COMP_PET_MOOD_AFFECTIONATE",
        "COMP_PET_MOOD_DELIGHTED",
        "COMP_PET_MOOD_RESTFUL",
        "COMP_PET_MOOD_WORRIED",
        "valence",
        "arousal",
        "affection",
        "attachment",
        "last_stroke",
        "stroke_energy",
        "quiet_elapsed_ms",
        "personality_seed",
        "comp_pet_behavior_memory_t",
    ):
        require(token in behavior_header + behavior_source,
                f"portable pet behavior missing {token}", errors)

    for token in (
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_display_queue_enqueue_pet_expression",
        "comp_pet_expression_pose_is_valid(pose)",
        "request->pet_pose = *pose",
    ):
        require(token in queue, f"display queue missing parameterized-pet token {token}", errors)
    for token in (
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_pet_expression_render(&request->pet_pose, &framebuffer)",
        "face_shift=",
        "mouth_scale=",
        "source=procedural",
    ):
        require(token in panel, f"SSD1681 target path missing parameterized-pet token {token}", errors)
    for token in (
        "Companion_Display_EnqueuePetPose",
        "comp_epaper_display_queue_enqueue_expression_frame",
        "player_frame.frame_index",
        "source=external_flash",
        "comp_pet_behavior_note_touch",
        "comp_pet_behavior_note_stroke",
        "comp_pet_behavior_advance",
        "comp_pet_behavior_apply_expression",
        "Companion_PetBehavior_Advance",
        "s_companion_pet_behavior_last_advanced_ms",
        "[pet-emotion] boot",
        "pet_behavior_selftest",
        "s_companion_dynamic_touch_x",
        "s_companion_dynamic_touch_y",
        "s_companion_dynamic_touch_is_stroke",
        "Companion_Screen_DailyStrokeAt",
        "[pet-stroke]",
        "pet_expression_selftest",
        "idle_frame_suppressed",
        "frame_decision.expression == COMP_EPAPER_EXPRESSION_IDLE",
    ):
        require(token in app_ble, f"WB55 application bridge missing {token}", errors)
    for token in (
        "TOUCH_SCREEN_MAINTENANCE_QUIET_MS 1200u",
        "schedule_touch_screen_maintenance",
        "Companion_Screen_ExpressionMaintenance()",
        "Companion_Screen_MenuMaintenance()",
    ):
        require(token in main_c, f"generic quiet maintenance missing {token}", errors)
    require(
        "$(ROOT)/app/companion_pendant/epaper/pet_expression.c" in makefile,
        "WB55 Makefile does not compile pet_expression.c",
        errors,
    )
    require(
        "$(ROOT)/app/companion_pendant/epaper/pet_behavior.c" in makefile,
        "WB55 Makefile does not compile pet_behavior.c",
        errors,
    )
    for token in ("Revision 24", "Revision 25", "Revision 26", "Revision 27", "Revision 28", "Revision 29", "living emotional system", "comp_pet_behavior_memory_t", "pet_behavior", "one-bit framebuffer"):
        require(token in docs, f"product/WBA documentation missing {token}", errors)


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
        print("pet expression system: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("pet expression system: PASS")
    print("  continuous touch gaze, scaled logical geometry, and target-free WBA reuse are guarded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
