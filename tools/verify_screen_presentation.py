#!/usr/bin/env python3
"""Verify portable menu/expression presentation and responsive gesture wiring."""

from __future__ import annotations

import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def require_tokens(label: str, content: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    for token in tokens:
        if token not in content:
            errors.append(f"{label} missing {token}")


def main() -> int:
    errors: list[str] = []
    epaper = ROOT / "app/companion_pendant/epaper"
    touch = ROOT / "app/companion_pendant/touch"
    presentation_h = (epaper / "screen_presentation.h").read_text(encoding="utf-8")
    presentation_c = (epaper / "screen_presentation.c").read_text(encoding="utf-8")
    menu_c = (epaper / "screen_menu.c").read_text(encoding="utf-8")
    menu_h = (epaper / "screen_menu.h").read_text(encoding="utf-8")
    display_queue_c = (epaper / "display_queue.c").read_text(encoding="utf-8")
    gesture_h = (touch / "touch_gesture.h").read_text(encoding="utf-8")
    gesture_c = (touch / "touch_gesture.c").read_text(encoding="utf-8")
    app = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c").read_text(encoding="utf-8")
    main_source = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text(encoding="utf-8")
    makefile = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile").read_text(encoding="utf-8")
    screen_doc = (ROOT / "docs/companion_screen_expression_system.md").read_text(encoding="utf-8")
    project_plan = (ROOT / "docs/companion_screen_project_plan.md").read_text(encoding="utf-8")
    presentation_fixture = json.loads(
        (ROOT / "docs/validation/companion-screen-presentation-wb55.json").read_text(encoding="utf-8")
    )
    touch_fixture = json.loads(
        (ROOT / "docs/validation/companion-screen-touch-ft6336-wb55.json").read_text(encoding="utf-8")
    )
    bilingual_fixture = json.loads(
        (ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json").read_text(encoding="utf-8")
    )

    require_tokens("screen_presentation.h", presentation_h, (
        "COMP_SCREEN_PRESENTATION_MENU",
        "COMP_SCREEN_PRESENTATION_EXPRESSION",
        "COMP_SCREEN_PRESENTATION_ACTION_RESTORE_MENU",
        "menu_language",
        "menu_page",
        "expression_returns_to_menu",
        "comp_screen_presentation_show_daily",
    ), errors)
    require_tokens("screen_presentation.c", presentation_c, (
        "comp_screen_presentation_apply_product_expression",
        "COMP_EPAPER_EXPRESSION_IDLE",
        "COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION",
        "COMP_SCREEN_PRESENTATION_ACTION_RESTORE_MENU",
        "comp_screen_presentation_show_daily",
        "state->expression_returns_to_menu = false",
        "comp_screen_presentation_self_test",
    ), errors)
    require_tokens("screen_menu.c", menu_c, (
        "COMP_TOUCH_GESTURE_SWIPE_LEFT",
        "COMP_TOUCH_GESTURE_SWIPE_RIGHT",
        "comp_screen_menu_drag",
        "COMP_SCREEN_MENU_SCROLL_QUANTUM_PX",
        "home_scroll_offset_px",
        "comp_screen_menu_exact_scroll_offset_px",
        "COMP_SCREEN_MENU_SCROLL_MAX_PX",
        "home_scroll_frame_from_offset",
        "comp_screen_menu_home_hit_test",
        "comp_screen_menu_is_daily_entry_gesture",
        "menu->home_scroll_offset_px = (uint16_t)home_scroll_offset_px",
        "The accepted v3 source has no separate home pet panel",
        "COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE",
        "comp_screen_menu_with_ble_flag",
        "flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_BLE_CONNECTED",
        "comp_screen_framebuffer_invert_rect",
        "COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT",
        "COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING",
        "comp_screen_menu_set_phone_reconnect_state",
    ), errors)
    require_tokens("touch_gesture", gesture_h + gesture_c, (
        "consumed_until_release",
        "is_horizontal_swipe",
        "fill_event",
        "live_type",
        "vertical axis lock for live scrolling",
        "comp_touch_gesture_is_vertical_drag",
        "comp_touch_gesture_self_test",
    ), errors)
    require_tokens("app_ble.c", app, (
        "comp_screen_presentation_apply_product_expression",
        "presentation=restore_menu",
        "Companion_Screen_MenuRequest",
        "Companion_Screen_RefreshBleStatus",
        "status_ble connected=%u refresh=partial",
        "Companion_Screen_RuntimeMenuFlags",
        "Companion_Ble_RequestAdvertising",
        "s_companion_ble_advertising",
        "advertising %s skipped: already active",
        "COMP_SCREEN_MENU_FLAG_RECORDING",
        "comp_emote_player_play_after_tail_name",
        "COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_SIGNAL",
        "COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL",
        "product_demo_end signal=",
        "bool expression_changed = false",
        "if (!expression_changed &&",
        "Companion_Screen_DailyTap",
        "Companion_Screen_ShowDaily",
        "Companion_Screen_ExpressionMaintenance",
        "comp_epaper_display_queue_enqueue_expression_frame",
        "player_frame.frame_index",
        "source=external_flash",
        "comp_pet_behavior_note_touch",
        "Companion_PetBehavior_Advance",
        "[pet-emotion] boot",
        "Companion_Display_EmitEmoteFrame(false)",
        "s_companion_expression_transition_immediate = true",
        "comp_emote_player_play_now_name(",
        "transition=immediate",
        "comp_emote_player_play_now_name(&s_companion_emote_player",
        "clip_name,\n                                       false)",
    ), errors)
    if app.find("comp_epaper_expression_state_tick") > app.find("comp_emote_player_tick"):
        errors.append("product expression state must advance before the emote player")
    require_tokens("main.c", main_source, (
        "TOUCH_TAP_MAX_DURATION_MS 1100u",
        "TOUCH_TAP_MAX_MOVE_PX 24u",
        "TOUCH_LONG_PRESS_MAX_MOVE_PX 46u",
        "TOUCH_SWIPE_MIN_MOVE_PX 30u",
        "TOUCH_AXIS_LOCK_MIN_MOVE_PX 10u",
        "TOUCH_AXIS_SLOP_PX 5u",
        "TOUCH_AXIS_DOMINANCE_PERCENT 120u",
        "TOUCH_SWIPE_MAX_DURATION_MS 1400u",
        "TOUCH_MIN_CONTACT_SAMPLES 1u",
        "TOUCH_RELEASE_DEBOUNCE_SAMPLES 1u",
        "COMPANION_TOUCH_MIRROR_Y 0u",
        "comp_touch_gesture_init(&s_touch_gesture, &gesture_config)",
        "gesture.type == COMP_TOUCH_GESTURE_TAP",
        "daily_reaction",
        "daily_hold_menu_prepare",
        "daily_to_menu gesture=any_long_press",
        "daily_stroke gesture=%s",
        "comp_screen_menu_is_daily_entry_gesture(&gesture)",
        "comp_screen_menu_is_exit_gesture(&gesture)",
        "menu_right_swipe_exit",
        "Companion_Screen_DailyTapAt(gesture.end_x, gesture.end_y)",
        "Companion_Screen_DailyStrokeAt(gesture.start_x",
        "Companion_Screen_ShowDailyClean()",
        "menu_entry_activate",
        "TOUCH_MENU_LONG_PRESS_DURATION_MS 3000u",
        "TOUCH_MENU_ENTRY_CUE_MS 360u",
        "TOUCH_MENU_PRESS_CUE_DELAY_MS 160u",
        "TOUCH_SAMPLE_LOG_INTERVAL_MS 250u",
        "menu_press_deferred",
        "comp_touch_gesture_is_horizontal_drag",
        "visual=deferred_until_menu",
        "low_power_touch_wake expression=idle refresh=partial",
        "Companion_Screen_ShowDaily()",
        "process_menu_entry_transition",
        "s_menu_entry_pending",
        "TOUCH_SCREEN_MAINTENANCE_QUIET_MS 1200u",
        "schedule_touch_screen_maintenance",
        "process_touch_screen_maintenance",
        "Companion_Screen_ExpressionMaintenance()",
        "Companion_Screen_RefreshRecordingStatus",
        "record_state active=%u refresh=partial",
        "Companion_Screen_RuntimeMenuFlags",
        "COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT",
        "Companion_Ble_RequestAdvertising(\"touch-menu\")",
        "phone_reconnect result=%u state=%u",
    ), errors)
    require_tokens("screen_menu.h", menu_h, (
        "three-second hold anywhere",
        "comp_screen_menu_is_daily_entry_gesture",
        "comp_screen_menu_is_exit_gesture",
        "COMP_SCREEN_MENU_ACTION_EXIT_DAILY",
    ), errors)
    if "central_long_press" in main_source or "centered nearly still hold enters" in json.dumps(bilingual_fixture, sort_keys=True):
        errors.append("daily menu entry must remain any-position 3 s long press, not centered-only")
    for stale_contract in (
        "exactly one item",
        "unfocused row selects it",
        "focused row opens it",
    ):
        for label, content in (
            ("screen expression doc", screen_doc),
            ("presentation fixture", json.dumps(presentation_fixture, sort_keys=True)),
            ("touch fixture", json.dumps(touch_fixture, sort_keys=True)),
            ("bilingual fixture", json.dumps(bilingual_fixture, sort_keys=True)),
        ):
            if stale_contract in content:
                errors.append(f"{label} retains obsolete item-snap navigation contract: {stale_contract}")

    gesture_navigation = presentation_fixture.get("contract", {}).get("gesture_navigation", {})
    bilingual_gestures = bilingual_fixture.get("menu_contract", {}).get("gesture_contract", {})
    require_tokens("current screen navigation documentation", screen_doc + project_plan, (
        "menu-v3 static home contract",
        "one stable 200x200",
        "does not use a numbered scroll asset",
        "press-cue partial refresh",
        "target-arrival partial refresh",
        "0xFC",
        "0xCF",
    ), errors)
    for label, contract in (
        ("presentation fixture navigation", gesture_navigation),
        ("bilingual fixture navigation", bilingual_gestures),
    ):
        require_tokens(label, json.dumps(contract, sort_keys=True), (
            "home_rendering",
            "one owner-approved static",
            "home_scroll",
            "retired",
            "tap_selection",
            "press-cue partial refresh",
        ), errors)
    require_tokens("touch fixture remaining acceptance", json.dumps(touch_fixture.get("remaining_acceptance", [])), (
        "six-row",
        "press-cue",
    ), errors)
    require_tokens("display_queue.c", display_queue_c, (
        "comp_epaper_display_queue_discard_kind",
        "original_count - kept_count",
        "bool replace_pending_menu = false",
        "queue->items[latest].request_kind ==",
        "COMP_EPAPER_DISPLAY_REQUEST_MENU",
        "replace_pending_menu = true",
        "if (!replace_pending_menu)",
    ), errors)
    menu_request_start = app.find("static bool Companion_Screen_MenuRequestMode")
    menu_request_end = app.find("static void Companion_Screen_RefreshBleStatus", menu_request_start)
    menu_request = app[menu_request_start:menu_request_end]
    require_tokens("Companion_Screen_MenuRequestMode", menu_request, (
        "comp_epaper_display_queue_discard_kind",
        "COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION",
        "flags = comp_screen_menu_with_ble_flag(flags, s_companion_ble_connected)",
        "comp_epaper_refresh_mode_t refresh_mode",
        "COMP_EPAPER_REFRESH_MAINTENANCE",
        "if (queue_result == COMP_EPAPER_DISPLAY_QUEUE_OK)",
        "comp_screen_presentation_show_menu",
        "discarded_expression_frames",
    ), errors)
    if menu_request.find("comp_screen_presentation_show_menu") < menu_request.find(
        "if (queue_result == COMP_EPAPER_DISPLAY_QUEUE_OK)"
    ):
        errors.append("menu presentation state must commit only after queue acceptance")
    ble_refresh_start = app.rfind("static void Companion_Screen_RefreshBleStatus(void)")
    ble_refresh_end = app.find("static bool Companion_Screen_StartExpression", ble_refresh_start)
    ble_refresh = app[ble_refresh_start:ble_refresh_end]
    require_tokens("Companion_Screen_RefreshBleStatus", ble_refresh, (
        "s_companion_screen_presentation.mode != COMP_SCREEN_PRESENTATION_MENU",
        "s_companion_screen_presentation.menu_view != COMP_SCREEN_MENU_VIEW_STATUS",
        "s_companion_screen_presentation.menu_view != COMP_SCREEN_MENU_VIEW_PHONE",
        "comp_screen_menu_with_ble_flag",
        "Companion_Screen_MenuRequest",
    ), errors)
    record_refresh_start = main_source.find("static void Companion_Screen_RefreshRecordingStatus(void)")
    record_refresh_end = main_source.find("static void handle_touch_menu_sample", record_refresh_start)
    record_refresh = main_source[record_refresh_start:record_refresh_end]
    require_tokens("Companion_Screen_RefreshRecordingStatus", record_refresh, (
        "COMP_SCREEN_MENU_VIEW_RECORD",
        "COMP_SCREEN_MENU_VIEW_STATUS",
        "Companion_Screen_RuntimeMenuFlags()",
        "Companion_Screen_MenuRequest",
    ), errors)
    require_tokens("Makefile", makefile, (
        "screen_presentation.c",
        "touch_gesture.c",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_SIGNAL",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_END_SIGNAL",
    ), errors)

    build_script = (ROOT / "tools/build_nucleo_bringup.ps1").read_text(encoding="utf-8")
    require_tokens("build_nucleo_bringup.ps1", build_script, (
        "EpaperProductExpressionDemoExpression",
        "EpaperDailyTapDemo",
        "EPAPER_DAILY_TAP_DEMO=1",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_SIGNAL=$productExpressionSignal",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_END_SIGNAL=$productExpressionEndSignal",
    ), errors)

    portable = presentation_h + presentation_c + menu_c + gesture_h + gesture_c
    for forbidden in ("stm32", "HAL_", "GPIO", "FT6336", "HW_TS"):
        if forbidden.lower() in portable.lower():
            errors.append(f"portable presentation/gesture layer contains platform token {forbidden}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: portable presentation state, product-event restore, and responsive gestures verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
