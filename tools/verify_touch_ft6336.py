#!/usr/bin/env python3
"""Verify FT6336 protocol identity, WB55 diagnostics, and portable gestures."""

from __future__ import annotations

import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def require(label: str, content: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    for token in tokens:
        if token not in content:
            errors.append(f"{label} missing {token}")


def main() -> int:
    errors: list[str] = []
    touch_root = ROOT / "app/companion_pendant/touch"
    protocol = (touch_root / "ft6336.h").read_text(encoding="utf-8")
    target_h = (touch_root / "touch_target_stm32wb_ft6336.h").read_text(encoding="utf-8")
    target_c = (touch_root / "touch_target_stm32wb_ft6336.c").read_text(encoding="utf-8")
    gesture = (touch_root / "touch_gesture.c").read_text(encoding="utf-8")
    main_source = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text(encoding="utf-8")
    panel_header = (ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.h").read_text(encoding="utf-8")
    panel_source = (ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c").read_text(encoding="utf-8")
    touch_fixture = json.loads(
        (ROOT / "docs/validation/companion-screen-touch-ft6336-wb55.json").read_text(encoding="utf-8")
    )

    require("ft6336 protocol", protocol, (
        "COMP_FT6336_I2C_ADDRESS_7BIT 0x38u",
        "COMP_FT6336_IDENTITY_REGISTER 0xA3u",
        "COMP_FT6336_IDENTITY_BYTES 6u",
        "COMP_FT6336_G_MODE_REGISTER 0xA4u",
        "COMP_FT6336_G_MODE_TRIGGER 0x01u",
        "COMP_FT6336_TOUCH_THRESHOLD_REGISTER 0x80u",
        "COMP_FT6336_PERIOD_ACTIVE_REGISTER 0x88u",
        "COMP_FT6336_PERIOD_MONITOR_REGISTER 0x89u",
        "COMP_FT6336_COMPANION_TOUCH_THRESHOLD 0x90u",
        "COMP_FT6336_COMPANION_ACTIVE_PERIOD 0x04u",
        "COMP_FT6336_COMPANION_MONITOR_PERIOD 0x04u",
        "comp_ft6336_identity_t",
    ), errors)
    require("WB55 touch target", target_h + target_c, (
        "companion_touch_ft6336_stm32wb_read_identity",
        "identity_attempted",
        "identity_valid",
        ".cipher = registers[0]",
        ".firmware_id = registers[3]",
        ".chip_id = registers[5]",
        "HAL_I2C_Mem_Read",
        "HAL_I2C_Mem_Write",
        "companion_touch_ft6336_stm32wb_configure_interrupt",
        "companion_touch_ft6336_stm32wb_configure_runtime_tuning",
        "interrupt_mode_valid",
        "runtime_tuning_valid",
    ), errors)
    require("WB55 touch diagnostics", main_source, (
        "[touch-health] detected=%u identity=%u",
        "cipher=0x%02X fw=0x%02X chip=0x%02X",
        "print_touch_health();",
        "TOUCH_TAP_MAX_DURATION_MS 1100u",
        "TOUCH_TAP_MAX_MOVE_PX 24u",
        "TOUCH_DOUBLE_TAP_MAX_GAP_MS 650u",
        "TOUCH_DOUBLE_TAP_MAX_MOVE_PX 40u",
        "TOUCH_SWIPE_MIN_MOVE_PX 30u",
        "TOUCH_AXIS_LOCK_MIN_MOVE_PX 10u",
        "TOUCH_AXIS_SLOP_PX 5u",
        "TOUCH_AXIS_DOMINANCE_PERCENT 120u",
        "TOUCH_SWIPE_MAX_DURATION_MS 1400u",
        "TOUCH_MIN_CONTACT_SAMPLES 1u",
        "TOUCH_RELEASE_DEBOUNCE_SAMPLES 1u",
        "COMPANION_TOUCH_MIRROR_Y 0u",
        "TOUCH_I2C_RECOVERY_FAILURES 8u",
        "recover_touch_i2c3_bus",
        "GPIO_MODE_OUTPUT_OD",
        "TOUCH_I2C_RECOVERY_CLOCKS",
        "HAL_I2C_DeInit(&hi2c3)",
        "[touch-recovery] count=%lu",
        "recoveries=%lu failure_streak=%u",
        "TOUCH_ACTIVE_POLL_MS 5u",
        "TOUCH_IDLE_POLL_MS 8u",
        "TOUCH_REFRESH_POLL_MS 5u",
        "TOUCH_REFRESH_BUFFER_CAPACITY 256u",
        "BOARD_TOUCH_INT_PIN GPIO_PIN_6",
        "BOARD_TOUCH_RST_PIN GPIO_PIN_10",
        "GPIO_MODE_IT_FALLING",
        "EXTI9_5_IRQHandler",
        "capture_touch_during_display_wait",
        "buffer_touch_sample_during_panel_wait",
        "touch_wait_buffer_self_test",
        "wait_buffer_selftest=%u",
        "[touch-buffer] drained=%u",
        "buffered=%lu dropped=%lu",
        "irq_mode=%s irq_cfg_errors=%lu",
        "irq_mode=%u irq_cfg=%lu irq_cfg_errors=%lu",
        "tuning=%u threshold=0x%02X active_period=%u monitor_period=%u",
        "[touch-ui] menu_entry_activate",
        "TOUCH_HOLD_FEEDBACK_MIN_DURATION_MS 650u",
        "TOUCH_MENU_LONG_PRESS_DURATION_MS 3000u",
        "TOUCH_LONG_PRESS_MAX_MOVE_PX 46u",
        "TOUCH_MENU_ENTRY_CUE_MS 360u",
        ".double_tap_max_gap_ms = TOUCH_DOUBLE_TAP_MAX_GAP_MS",
        ".double_tap_max_move_px = TOUCH_DOUBLE_TAP_MAX_MOVE_PX",
        "process_menu_entry_transition",
        "s_menu_entry_pending",
        "long_press_max_move_px",
        "sample_age_ms=%lu",
        "[touch-ui] menu_press",
        "daily_hold_menu_prepare",
        "Companion_Screen_DailyExpression(",
        "Companion_Screen_DailyExpressionSignal(",
        "Companion_Screen_MenuRequestClean(",
        "Companion_Screen_ShowDailyClean()",
        "screen_maintenance cancelled=transition",
        "[record-visual] action=start expression=recording",
        "[record-visual] action=store expression=%s",
    ), errors)
    boot_health_marker = (
        "comp_power_policy_set_blocker(&s_power_policy, COMP_POWER_BLOCKER_BOOT, false);\n"
        "    /* Preserve the configured FT6336/TP_INT state before the normal idle\n"
        "     * path can enter Stop and defer its periodic heartbeat. */\n"
        "    print_touch_health();\n"
        "    update_low_power_policy();"
    )
    if boot_health_marker not in main_source:
        errors.append("WB55 normal boot must log touch health before Stop becomes eligible")
    require("SSD1681 wait service", panel_header + panel_source, (
        "companion_epaper_wait_service_fn",
        "companion_epaper_panel_stm32wb_ssd1681_set_wait_service",
        "ssd1681_service_wait();",
        "wait_service_next_ms",
    ), errors)
    require("portable gesture", gesture, (
        "consumed_until_release",
        "long_press_max_move_px",
        "update_axis_lock",
        "is_horizontal_swipe",
        "vertical axis lock for live scrolling",
        "axis_dominance_percent",
        "min_contact_samples",
        "state->release_samples >= state->config.release_debounce_samples",
        "state->contact_samples < state->config.min_contact_samples",
        "self_test_one_sample_explicit_release",
        "self_test_tap_slop_precedes_drag",
        "self_test_vertical_drag_release",
        "self_test_expired_drag_rearms_tap",
        "comp_touch_gesture_self_test",
    ), errors)

    for forbidden in ("HAL_", "stm32", "GPIO", "I2C_HandleTypeDef"):
        if forbidden.lower() in gesture.lower():
            errors.append(f"portable gesture contains platform token {forbidden}")

    gesture_contract = touch_fixture.get("gesture_contract", {})
    if gesture_contract.get("minimum_contact_samples") != 1:
        errors.append("touch fixture must preserve the one-sample tap candidate configuration")
    if "press cue follows the current touched row" not in " ".join(touch_fixture.get("remaining_acceptance", [])):
        errors.append("touch fixture must retain current-row press tracking acceptance")
    if touch_fixture.get("gesture_contract", {}).get("home_vertical_stroke") != "menu-v3 home tracks the current pressed row but never synthesizes legacy scroll frames":
        errors.append("touch fixture must preserve the static menu-v3 press-tracking contract")
    require("daily stroke bridge", main_source, (
        "Companion_Screen_DailyStrokeAt",
        "[touch-ui] daily_stroke",
        "gesture.type == COMP_TOUCH_GESTURE_SWIPE_RIGHT",
        "gesture.type == COMP_TOUCH_GESTURE_SWIPE_UP",
        "gesture.type == COMP_TOUCH_GESTURE_SWIPE_DOWN",
    ), errors)
    if "daily_swipe_ignored" in main_source:
        errors.append("daily non-navigation swipes must reach the pet, not be discarded")
    if touch_fixture.get("gesture_contract", {}).get("daily_stroke") != "all non-menu-entry swipes react as directional pet strokes":
        errors.append("touch fixture must retain the directional daily-stroke contract")
    if touch_fixture.get("gesture_contract", {}).get("daily_enter_menu") != "3000 ms any-position long_press with 46 px wobble tolerance":
        errors.append("touch fixture must require any-position 3 s long-press menu entry")

    double_tap_marker = "} else if (gesture.type == COMP_TOUCH_GESTURE_DOUBLE_TAP) {"
    double_tap_tail = "} else if (gesture.type == COMP_TOUCH_GESTURE_TAP) {"
    if double_tap_marker not in main_source or double_tap_tail not in main_source:
        errors.append("daily double-tap branch must remain explicit")
    else:
        double_tap_block = main_source.split(double_tap_marker, 1)[1].split(double_tap_tail, 1)[0]
        if "cancel_touch_screen_maintenance();" not in double_tap_block:
            errors.append("daily double-tap must cancel first-tap maintenance before recording art")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: FT6336 identity diagnostics and portable gesture boundary verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
