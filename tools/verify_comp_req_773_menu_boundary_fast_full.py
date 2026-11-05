#!/usr/bin/env python3
"""Verify that menu enter/exit use the accepted fast full-refresh boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / ".cache"
    / "validation"
    / "comp-req-773-menu-boundary-fast-full"
    / "MACHINE_READY.json"
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def function_body(source: str, signature: str) -> str:
    start = -1
    brace = -1
    search_from = 0
    while True:
        candidate = source.find(signature, search_from)
        if candidate < 0:
            return ""
        candidate_brace = source.find("{", candidate)
        candidate_semicolon = source.find(";", candidate)
        if candidate_brace >= 0 and (
            candidate_semicolon < 0 or candidate_brace < candidate_semicolon
        ):
            start = candidate
            brace = candidate_brace
            break
        search_from = candidate + len(signature)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return ""


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().upper()


def main() -> int:
    paths = {
        "registry": "docs/companion_product_requirements.md",
        "header": (
            "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/"
            "companion_screen_ui.h"
        ),
        "main": (
            "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
        ),
        "app": (
            "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
        ),
        "policy": "app/companion_pendant/epaper/refresh_policy.c",
        "driver": (
            "app/companion_pendant/epaper/"
            "panel_target_stm32wb_ssd1681.c"
        ),
    }
    texts = {name: read(path) for name, path in paths.items()}

    enter = function_body(
        texts["app"], "bool Companion_Screen_MenuRequestClean("
    )
    exit_menu = function_body(
        texts["app"], "bool Companion_Screen_ShowDailyClean("
    )
    ordinary_menu = function_body(
        texts["app"], "void Companion_Screen_MenuRequest("
    )
    policy_select = function_body(
        texts["policy"], "comp_epaper_refresh_policy_select("
    )
    accepted_driver = function_body(
        texts["driver"],
        "ssd1681_accepted_cached_mode2_product_refresh(",
    )
    ordinary_driver = function_body(
        texts["driver"],
        "ssd1681_cached_mode2_diff_internal(",
    )
    fast_full = function_body(
        texts["driver"],
        "ssd1681_lifecycle_mode2_fast_full_activation(",
    )
    fast_visible_stage = fast_full.split("if (planes_written)", 1)[0]
    mode2_rearm = function_body(
        texts["driver"],
        "ssd1681_accepted_mode2_rearm(",
    )
    automatic_motion = function_body(
        texts["app"],
        "static void Companion_Display_ProcessDueTracks(",
    )
    automatic_frame = function_body(
        texts["app"],
        "static bool Companion_Display_EmitAutomaticMotionFrame(",
    )

    checks = {
        "owner_steering_registered": (
            "### COMP-REQ-773 菜单进出边界使用既有快速全刷路径"
            in texts["registry"]
        ),
        "clean_boundary_api_declared": all(
            token in texts["header"]
            for token in (
                "Companion_Screen_MenuRequestClean",
                "Companion_Screen_ShowDailyClean",
            )
        ),
        "long_press_enters_through_clean_boundary": (
            "Companion_Screen_MenuRequestClean(" in texts["main"]
        ),
        "right_swipe_exits_through_clean_boundary": (
            "Companion_Screen_ShowDailyClean();" in texts["main"]
        ),
        "menu_enter_requests_maintenance_once": (
            enter.count("COMP_EPAPER_REFRESH_MAINTENANCE") == 1
            and "menu_boundary=enter" in enter
        ),
        "menu_exit_requests_maintenance_once": (
            exit_menu.count("COMP_EPAPER_REFRESH_MAINTENANCE") == 1
            and "menu_boundary=exit" in exit_menu
        ),
        "menu_exit_mode_reaches_first_daily_frame": (
            "Companion_Display_ProcessDueTracks(HAL_GetTick(), refresh_mode);"
            in texts["app"]
            and "Companion_Display_EmitAutomaticMotionFrame(&motion_request,"
            in automatic_motion
            and "refresh_mode" in automatic_motion
            and "Companion_Display_EmitEmoteFrameModeInternal("
            in automatic_frame
            and "refresh_mode, motion_request" in automatic_frame
        ),
        "boundary_logs_survive_nonverbose_product_build": all(
            token in source
            for source, token in (
                (
                    texts["main"],
                    'printf("[touch-ui] daily_to_menu '
                    'gesture=any_long_press',
                ),
                (
                    texts["main"],
                    'printf("[touch-ui] menu_right_swipe_exit',
                ),
                (
                    enter,
                    'printf("[screen] menu_boundary=enter',
                ),
                (
                    exit_menu,
                    'printf("[screen] menu_boundary=exit',
                ),
            )
        ),
        "menu_internal_requests_remain_partial": (
            "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE" in ordinary_menu
            and "COMP_EPAPER_REFRESH_MAINTENANCE" not in ordinary_menu
        ),
        "valid_baseline_maps_boundary_to_fast": all(
            token in policy_select
            for token in (
                "requested_mode == COMP_EPAPER_REFRESH_MAINTENANCE",
                "selection.decision = COMP_EPAPER_REFRESH_DECISION_FAST",
                "COMP_EPAPER_REFRESH_REASON_MAINTENANCE_BOUNDARY",
            )
        ),
        "missing_baseline_keeps_safe_full_fallback": (
            "!policy->baseline_valid" in policy_select
        ),
        "accepted_driver_uses_unique_mode2_ff_boundary": all(
            token in fast_full
            for token in (
                "static const uint8_t fast_full_update[] = {0xFFu}",
                "0x26u, s_blink_closed_frame, &window",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                "control=0xFF window=200x200 bytes_each=5000 data_planes=2",
                'committed_previous_used ? "committed_previous" : "inverse_target"',
                "visible_geometry=full border=0x05 partial_window_before_activation=0",
                "rebaseline_commands=0x26,0x24",
                "rebaseline_activation=0",
                "mode2_load=0x99",
            )
        )
        and fast_visible_stage.count(
            "ssd1681_set_window(&window, false, false)"
        ) == 2
        and "ssd1681_native_two_pass_source_window" not in fast_visible_stage
        and "control=0xC7" not in fast_full
        and "control=0xF7" not in fast_full
        and accepted_driver.count(
            "ssd1681_lifecycle_mode2_fast_full_activation("
        ) == 1
        and "ssd1681_accepted_visible_fast_full_activation(" not in accepted_driver,
        "accepted_driver_keeps_single_plane_partial_with_banded_life": all(
            token in texts["driver"]
            for token in (
                "ssd1681_product_source_complete_window(",
                "ssd1681_product_stage_changed_byte_components(",
                "ssd1681_native_cached_mode2_movement_activation(",
            )
        )
        and "ssd1681_cached_mode2_diff_internal(" in accepted_driver
        and "exact changed-byte components on the accepted"
        in accepted_driver
        and "single-current-plane path"
        in accepted_driver,
        "accepted_boundary_has_one_visible_activation_then_no_display_rebaseline": (
            fast_full.count("ssd1681_command(0x20u)") == 1
            and "activation_count=%u" in fast_full
            and "rebaseline_activation=0" in fast_full
            and "static const uint8_t load_lut_mode2[] = {0x99u}"
            in mode2_rearm
            and "display_activation=0" in mode2_rearm
        ),
    }
    passed = all(checks.values())
    report = {
        "schema": "companion.comp_req_773.menu_boundary_fast_full.v1",
        "status": "MACHINE_READY" if passed else "NO_GO",
        "behavior": {
            "menu_enter": "one maintenance request -> one visible lifecycle Mode-2 full 0xFF",
            "menu_exit": "one maintenance request -> one visible lifecycle Mode-2 full 0xFF",
            "menu_internal": "partial interactive",
            "fallback": "first frame or invalid baseline uses the same accepted visible 0xFF path",
            "ordinary": "source-complete changed-byte components -> one 0xCF activation",
        },
        "checks": checks,
        "source_sha256": {name: sha256(path) for name, path in paths.items()},
        "hardware_contact": "not_performed_by_this_verifier",
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
