#!/usr/bin/env python3
"""Verify FT6336 protocol identity, WB55 diagnostics, and portable gestures."""

from __future__ import annotations

import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def require(label: str, content: str, tokens: tuple[str, ...], errors: list[str]) -> None:
    for token in tokens:
        if token not in content:
            errors.append(f"{label} missing {token}")


def extract_function(content: str, name: str) -> str:
    match = re.search(
        rf"^[ \t]*(?:[A-Za-z_]\w*[ \t]+)+\**{re.escape(name)}"
        rf"\s*\([^;{{}}]*\)\s*\{{",
        content,
        re.M | re.S,
    )
    if match is None:
        raise ValueError(f"missing function body: {name}")
    brace = content.find("{", match.start())
    depth = 0
    for index in range(brace, len(content)):
        if content[index] == "{":
            depth += 1
        elif content[index] == "}":
            depth -= 1
            if depth == 0:
                return content[brace : index + 1]
    raise ValueError(f"unterminated function body: {name}")


def main() -> int:
    errors: list[str] = []
    touch_root = ROOT / "app/companion_pendant/touch"
    protocol = (touch_root / "ft6336.h").read_text(encoding="utf-8")
    target_h = (touch_root / "touch_target_stm32wb_ft6336.h").read_text(encoding="utf-8")
    target_c = (touch_root / "touch_target_stm32wb_ft6336.c").read_text(encoding="utf-8")
    gesture = (touch_root / "touch_gesture.c").read_text(encoding="utf-8")
    visual_decision = (touch_root / "touch_visual_decision.c").read_text(encoding="utf-8")
    tap_arbiter = (touch_root / "touch_tap_arbiter.c").read_text(encoding="utf-8")
    tap_arbiter_h = (touch_root / "touch_tap_arbiter.h").read_text(encoding="utf-8")
    host_test = (touch_root / "tests/test_touch_gesture.c").read_text(encoding="utf-8")
    host_runner = (ROOT / "tools/test_touch_gesture_host.ps1").read_text(encoding="utf-8")
    main_source = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text(encoding="utf-8")
    app_ble_source = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c").read_text(encoding="utf-8")
    makefile = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile").read_text(encoding="utf-8")
    build = (ROOT / "tools/build_nucleo_bringup.ps1").read_text(encoding="utf-8")
    recording_acceptance = (ROOT / "tools/run_wb55_recording_chain_acceptance.ps1").read_text(encoding="utf-8")
    touch_wake_parser = (ROOT / "tools/verify_wb55_touch_wake_log.py").read_text(encoding="utf-8")
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
        "#ifndef COMP_FT6336_COMPANION_TOUCH_THRESHOLD",
        "COMP_FT6336_COMPANION_TOUCH_THRESHOLD 0x40u",
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
        "COMPANION_TOUCH_FT6336_I2C_SETUP_TIMEOUT_MS 20u",
        "COMPANION_TOUCH_FT6336_I2C_POLL_TIMEOUT_MS 5u",
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
        "TOUCH_RELEASE_DEBOUNCE_SAMPLES 2u",
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
        "s_touch_runtime_actions_deferred",
        "defer_touch_runtime_action",
        "process_deferred_touch_runtime_action",
        "COMP_TOUCH_RUNTIME_ACTION_TOGGLE_RECORDING",
        "COMP_TOUCH_RUNTIME_ACTION_MENU_RECORD_START",
        "COMP_TOUCH_RUNTIME_ACTION_MENU_RECORD_STOP",
        "COMP_TOUCH_RUNTIME_ACTION_PHONE_RECONNECT",
        "deferred_runtime_action action=%s phase=queued",
        "deferred_runtime_action action=%s phase=execute delay_ms=%lu",
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
        "TOUCH_MENU_PRESS_CUE_DELAY_MS 160u",
        "TOUCH_SAMPLE_LOG_INTERVAL_MS 250u",
        "COMPANION_TOUCH_VERBOSE_TRACE 0",
        "COMPANION_EPAPER_SSD1681_VERBOSE_TRACE 0",
        "COMPANION_INTERACTION_BUILD_PROFILE \"quiet\"",
        "#define TOUCH_VERBOSE_TRACE(...) printf(__VA_ARGS__)",
        "#define TOUCH_VERBOSE_TRACE(...) do { if (0) { printf(__VA_ARGS__); } } while (0)",
        "TOUCH_VERBOSE_TRACE(\"[touch] contacts=",
        "TOUCH_VERBOSE_TRACE(\"[touch-ui] gesture=",
        "[build] interaction_profile=%s epaper_trace=%u touch_trace=%u ft6336_threshold=0x%02X",
        "refresh_policy=partial_x5_then_fast_cleanup",
        ".double_tap_max_gap_ms = TOUCH_DOUBLE_TAP_MAX_GAP_MS",
        ".double_tap_max_move_px = TOUCH_DOUBLE_TAP_MAX_MOVE_PX",
        "process_menu_entry_transition",
        "s_menu_entry_pending",
        "long_press_max_move_px",
        "sample_age_ms=%lu",
        "menu_press_deferred",
        "[touch-ui] menu_press",
        "daily_hold_menu_prepare",
        "visual=deferred_until_menu",
        "comp_touch_gesture_is_horizontal_drag",
        "s_low_power_touch_wake_requested",
        "low_power_touch_wake state=active visual=boundary_fast_full result=requested",
        "tap/swipe/record/menu",
        "Companion_Screen_MenuRequestClean(",
        "Companion_Screen_ShowDailyClean()",
        "s_touch_gesture.consumed_until_release",
        "recontact_boundary",
        "schedule_daily_tap_reaction",
        "cancel_daily_tap_reaction",
        "process_daily_tap_reaction",
        "daily_reaction phase=deferred",
        "daily_reaction phase=cancelled",
        "daily_reaction phase=execute",
        "tap_arbiter=%s contract=confirmed_single_before_display",
        "comp_touch_tap_arbiter_self_test",
        "[record-visual] action=start expression=recording",
        "[record-visual] action=store expression=%s",
    ), errors)
    require("touch diagnostic build", makefile + build, (
        "COMPANION_TOUCH_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "Ft6336TouchThreshold",
        "FT6336_TOUCH_THRESHOLD=0x{0:X2}u",
        "touch_tap_arbiter.c",
    ), errors)
    require("screen interaction trace gate", app_ble_source, (
        "COMPANION_TOUCH_VERBOSE_TRACE 0",
        "#define SCREEN_INTERACTION_TRACE(...) printf(__VA_ARGS__)",
        "#define SCREEN_INTERACTION_TRACE(...) do { if (0) { printf(__VA_ARGS__); } } while (0)",
        "SCREEN_INTERACTION_TRACE(\"[screen] menu enqueue",
        "SCREEN_INTERACTION_TRACE(\"[screen] display_result",
        "SCREEN_INTERACTION_TRACE(\"[pet-renderer]",
        "SCREEN_INTERACTION_TRACE(\"[pet-attention]",
        "SCREEN_INTERACTION_TRACE(\"[pet-stroke]",
        "SCREEN_INTERACTION_TRACE(\"[pet-emotion]",
        "static bool s_companion_screen_coherent_generation_marker_logged = false;",
        "if (!s_companion_screen_coherent_generation_marker_logged &&",
        "printf(\"[screen] coherent_generation=1 resource_revision=",
        "printf(\"[screen] menu enqueue_failed",
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
        "comp_touch_gesture_is_horizontal_drag",
        "vertical axis lock for live scrolling",
        "axis_dominance_percent",
        "min_contact_samples",
        "state->release_samples >= state->config.release_debounce_samples",
        "state->contact_samples < state->config.min_contact_samples",
        "self_test_one_sample_explicit_release",
        "self_test_tap_slop_precedes_drag",
        "self_test_vertical_drag_release",
        "self_test_expired_drag_rearms_tap",
        "self_test_double_tap_without_idle_sample",
        "self_test_implicit_double_tap_consumes_boundary_down",
        "comp_touch_gesture_restart_contact",
        "comp_touch_gesture_self_test",
    ), errors)
    require("native WB55 gesture replay", host_test + host_runner, (
        "replay_wb55_double_tap_boundary",
        "replay_two_recording_double_taps",
        "recording replay must preserve start and stop double taps",
        "95u, 128u, 100u",
        "109u, 129u, 232u",
        "0u, 0u, 4535u",
        "COMP_TOUCH_GESTURE_DOUBLE_TAP",
        "state.consumed_until_release",
        "test_touch_gesture.exe",
        "cl.exe /nologo /W4 /WX /std:c11",
    ), errors)
    require("portable tap arbiter", tap_arbiter + tap_arbiter_h, (
        "comp_touch_tap_arbiter_defer",
        "comp_touch_tap_arbiter_cancel",
        "comp_touch_tap_arbiter_poll",
        "now_ms + arbiter->confirmation_window_ms + 1u",
        "contact_active || detector_tap_pending",
        "self_test_confirmed_single_tap",
        "self_test_captured_recontact_double_tap",
        "0u, 159u, 100u",
        "COMP_TOUCH_GESTURE_DOUBLE_TAP",
        "comp_touch_tap_arbiter_self_test",
    ), errors)

    for forbidden in ("HAL_", "stm32", "GPIO", "I2C_HandleTypeDef"):
        if forbidden.lower() in (gesture + tap_arbiter).lower():
            errors.append(f"portable touch logic contains platform token {forbidden}")

    try:
        restart_body = extract_function(gesture, "comp_touch_gesture_restart_contact")
        recording_start = extract_function(main_source, "start_recording")
        recording_stop = extract_function(main_source, "stop_recording")
        recording_cancel = extract_function(main_source, "cancel_recording")
        microphone_probe = extract_function(main_source, "run_microphone_probe")
        dma_stop = extract_function(main_source, "pdm_raw_dma_stop_if_started")
        touch_dispatch = extract_function(main_source, "handle_touch_menu_sample")
        main_loop = extract_function(main_source, "main")
        recording_pending = extract_function(main_source, "recording_touch_work_pending")
        recording_touch_account = extract_function(main_source, "account_recording_touch_service")
        recording_touch_flash = extract_function(main_source, "capture_recording_touch_during_flash_write")
        recording_touch_service = extract_function(main_source, "service_recording_touch")
        recording_touch_due = extract_function(main_source, "service_recording_touch_if_due")
        recording_app_service = extract_function(main_source, "recording_loop_should_process_app")
        recording_flash_append = extract_function(main_source, "recording_flash_append_pcm")
        recording_flash_drain = extract_function(main_source, "recording_flash_drain_stage")
        recording_start = extract_function(main_source, "start_recording")
    except ValueError as exc:
        errors.append(str(exc))
    else:
        require("implicit double-tap boundary consumption", restart_body, (
            "previous_ready && out_event->type == COMP_TOUCH_GESTURE_DOUBLE_TAP",
            "state->consumed_until_release = true",
            "return true",
        ), errors)
        require("WB55 restart-contact call edge", visual_decision, (
            "sample->event == COMP_FT6336_TOUCH_EVENT_DOWN",
            "comp_touch_gesture_restart_contact(",
            "gesture_state, logical_x, logical_y, now_ms",
        ), errors)
        dma_start = recording_start.find("pdm_raw_dma_start_if_needed()")
        recording_status = recording_start.find("Companion_Screen_RefreshRecordingStatus()")
        recording_visual = recording_start.find("Companion_Screen_DailyExpressionSignal(")
        if not (0 <= dma_start < recording_status and dma_start < recording_visual):
            errors.append("recording DMA must start before any recording screen request")
        require("recording DMA lifecycle", recording_stop + recording_cancel + microphone_probe + dma_stop, (
            "HAL_SAI_DMAStop(&hsai_BlockA1)",
            "s_pdm_raw_dma_started = false",
            "[mic-dma] action=stop",
        ), errors)
        for operation, body in (
            ("recording stop", recording_stop),
            ("recording cancel", recording_cancel),
            ("microphone probe", microphone_probe),
        ):
            if "pdm_raw_dma_stop_if_started()" not in body:
                errors.append(f"{operation} must stop PDM DMA before low-power idle")
        recording_guard = touch_dispatch.find(
            "s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING &&"
        )
        menu_entry = touch_dispatch.find("comp_screen_menu_is_daily_entry_gesture")
        if not (0 <= recording_guard < menu_entry):
            errors.append("recording gesture guard must precede daily menu entry")
        require("recording provisional gesture isolation", touch_dispatch, (
            "gesture.type != COMP_TOUCH_GESTURE_DOUBLE_TAP",
            "recording_gesture gesture=%s action=provisional_or_ignored display_request=0",
        ), errors)
        if "touch_recording_tap_retained" in touch_dispatch:
            errors.append("provisional recording tap still requests an e-paper expression")
        require("recording touch priority guard", recording_pending, (
            "s_touch_contact_active",
            "s_touch_gesture.active",
            "s_touch_gesture.consumed_until_release",
            "s_touch_gesture.tap_pending",
            "s_touch_irq_count != s_touch_irq_consumed_count",
            "s_touch_refresh_buffer_count != 0u",
            "s_touch_deferred_action != COMP_TOUCH_RUNTIME_ACTION_NONE",
        ), errors)
        require("recording touch service", recording_touch_service, (
            "poll_board_buttons();",
            "poll_touch_debug();",
            "process_deferred_touch_runtime_action();",
        ), errors)
        require("recording hot-path touch cadence", recording_touch_due, (
            "recording_touch_work_pending()",
            "TOUCH_ACTIVE_POLL_MS",
            "RECORDING_TOUCH_IDLE_POLL_MS",
            "return service_recording_touch();",
        ), errors)
        require("recording touch health cadence", main_source, (
            "#define RECORDING_TOUCH_HEALTH_TRACE_MS 250u",
        ), errors)
        require("recording touch health reset", recording_start, (
            "s_recording_touch_service_count = 0u;",
            "s_recording_touch_last_read_count = s_touch.read_count;",
            "s_recording_touch_next_health_ms = HAL_GetTick();",
        ), errors)
        require("recording touch health trace", recording_touch_account, (
            "s_recording_touch_service_count++;",
            "s_touch.read_count",
            "s_touch.error_count",
            "s_touch_irq_count",
            "s_touch_irq_consumed_count",
            "HAL_GPIO_ReadPin(BOARD_TOUCH_INT_GPIO_PORT, BOARD_TOUCH_INT_PIN)",
            "s_touch_next_poll_ms - now_ms",
            "s_touch_contact_active",
            "s_touch_gesture.active",
            "s_touch_gesture.consumed_until_release",
            "s_touch_gesture.tap_pending",
            "s_touch_refresh_buffer_count",
            "touch_runtime_action_name(s_touch_deferred_action)",
            "TOUCH_VERBOSE_TRACE(",
            "[record-touch]",
        ), errors)
        if 'printf("[record-touch]' in recording_touch_account:
            errors.append("recording touch health must stay out of quiet-build direct printf")
        require("recording Flash touch service", recording_touch_flash, (
            "s_touch_runtime_actions_deferred = true;",
            "poll_touch_debug();",
            "account_recording_touch_service();",
            "s_touch_runtime_actions_deferred = actions_were_deferred;",
        ), errors)
        require("bounded recording Flash drain", recording_flash_drain, (
            "pages_written < page_budget",
            "page_size - (address % page_size)",
            "recording_flash_write_bytes(s_recording_flash_stage, chunk)",
            "capture_recording_touch_during_flash_write();",
        ), errors)
        require("incremental recording Flash schedule", recording_flash_append, (
            "recording_flash_drain_stage(1u, false)",
            "FLASH_RECORDING_DRAIN_HIGH_WATER_BYTES",
        ), errors)
        if "recording_flash_flush_stage()" in recording_flash_append:
            errors.append("recording append must not flush the full stage synchronously")
        require("recording acceptance trace preflight", recording_acceptance, (
            '"[record-touch]"',
        ), errors)
        require("recording touch root-cause classifier", touch_wake_parser, (
            "def recording_touch_samples(",
            "def summarize_recording_touch_health(",
            '"recording_touch_health_observed"',
            '"no_microphone_dma_overrun"',
            '"RECORDING_TOUCH_SCHEDULER_STALLED"',
            '"FT6336_I2C_READ_FAILURE"',
            '"FT6336_POLL_STALLED"',
            '"FT6336_IRQ_NOT_CONSUMED"',
            '"FT6336_PC6_STUCK_LOW"',
            '"FT6336_NO_TOUCH_DETECTION"',
            '"FT6336_IRQ_WITHOUT_CONTACT_REPORT"',
            '"TOUCH_CONTACT_WITHOUT_GESTURE"',
            '"TOUCH_GESTURE_NOT_COMPLETED"',
            '"findings": findings',
            '"scheduler_gap_count": scheduler_gap_count',
            '"no_second_touch_classified"',
            '"scheduler_and_no_touch_classified"',
            '"dma_overrun_rejected"',
            '"i2c_failure_classified"',
        ), errors)
        require("one-shot touch recording display service", recording_app_service, (
            "s_recording_fsm.active_source == COMP_RECORDING_SOURCE_USER_TOUCH",
            "return !s_touch_recording_initial_app_serviced;",
            "ble_audio_stream_enabled_for_recording()",
        ), errors)
        require("touch recording display service reset", recording_start, (
            "s_touch_recording_initial_app_serviced = false;",
        ), errors)
        recording_branch_start = main_loop.find(
            "if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {"
        )
        recording_branch_end = main_loop.find(
            "\n        update_low_power_policy();\n        MX_APPE_Process();",
            recording_branch_start + 1,
        )
        if recording_branch_start < 0 or recording_branch_end < 0:
            errors.append("recording main-loop branch is not inspectable")
        else:
            recording_branch = main_loop[recording_branch_start:recording_branch_end]
            first_touch_service = recording_branch.find("service_recording_touch_if_due()")
            first_app = recording_branch.find("MX_APPE_Process()")
            capture = recording_branch.find("capture_microphone_block(")
            touch_services = [
                match.start()
                for match in re.finditer(
                    "service_recording_touch(?:_if_due)?\\(\\)",
                    recording_branch,
                )
            ]
            if not (0 <= first_touch_service < first_app < capture):
                errors.append("recording loop must service touch before app/display and microphone capture")
            if len(touch_services) < 3 or not any(
                first_app < position < capture for position in touch_services
            ) or not any(position > capture for position in touch_services):
                errors.append("recording loop must re-service touch after app/display and microphone capture")
            if "recording_touch_work_pending()" not in recording_branch or \
                    "!preserve_touch_window" not in recording_branch:
                errors.append("touch-originated recording must suppress app/display work during gesture arbitration")
            app_service = recording_branch.find("MX_APPE_Process()")
            app_latched = recording_branch.find(
                "s_touch_recording_initial_app_serviced = true;",
                app_service,
            )
            if app_service < 0 or app_latched < app_service:
                errors.append("touch-originated recording must latch its one allowed display service")

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
    if "Companion_Screen_DailyExpression(\n                COMP_EPAPER_EXPRESSION_THINKING" in main_source:
        errors.append("650 ms hold acknowledgement must not start an e-paper refresh before the 3 s decision")
    if 'printf("[touch-irq] observed=' in main_source:
        errors.append("normal touch path must not synchronously print every touch IRQ")
    if "phase_changed" not in main_source or "TOUCH_SAMPLE_LOG_INTERVAL_MS" not in main_source:
        errors.append("changed-coordinate touch diagnostics must be rate limited")

    busy_capture_marker = "static void capture_touch_during_display_wait(void *context, uint32_t now_ms)"
    busy_capture_end = "static void process_touch_debug_sample("
    if busy_capture_marker not in main_source or busy_capture_end not in main_source:
        errors.append("WB55 BUSY touch callback must remain separately inspectable")
    else:
        busy_capture = main_source.rsplit(busy_capture_marker, 1)[1].split(busy_capture_end, 1)[0]
        expected_busy_sequence = (
            "bool actions_were_deferred = s_touch_runtime_actions_deferred;\n"
            "    s_touch_runtime_actions_deferred = true;\n"
            "    process_touch_debug_sample(&sample, now_ms);\n"
            "    s_touch_runtime_actions_deferred = actions_were_deferred;"
        )
        if expected_busy_sequence not in busy_capture:
            errors.append("BUSY callback must bracket gesture processing and defer runtime work")

    deferred_marker = "static void process_deferred_touch_runtime_action(void)"
    deferred_tail = "static void update_low_power_policy(void)"
    if deferred_marker not in main_source or deferred_tail not in main_source:
        errors.append("WB55 deferred touch runtime executor is missing")
    else:
        deferred_block = main_source.rsplit(deferred_marker, 1)[1].split(deferred_tail, 1)[0]
        for action in (
            "toggle_touch_recording(queued_ms);",
            "start_manual_recording();",
            "stop_manual_recording(\"touch-menu\");",
            "process_touch_menu_phone_reconnect();",
        ):
            if action not in deferred_block:
                errors.append(f"deferred touch executor missing {action}")

    double_tap_marker = "} else if (gesture.type == COMP_TOUCH_GESTURE_DOUBLE_TAP) {"
    double_tap_tail = "} else if (gesture.type == COMP_TOUCH_GESTURE_TAP) {"
    if double_tap_marker not in main_source or double_tap_tail not in main_source:
        errors.append("daily double-tap branch must remain explicit")
    else:
        double_tap_block = main_source.split(double_tap_marker, 1)[1].split(double_tap_tail, 1)[0]
        if "cancel_touch_screen_maintenance" in double_tap_block:
            errors.append("daily double-tap must not restore the obsolete delayed maintenance path")
        if "COMP_TOUCH_RUNTIME_ACTION_TOGGLE_RECORDING" not in double_tap_block:
            # The production path queues the toggle before this logging branch.
            # The queue is serviced only after the display wait callback returns;
            # requiring a second direct enqueue here would double-trigger it.
            dispatch_before_branch = main_source.rfind(
                "comp_touch_recording_boundary_dispatch(", 0,
                main_source.find(double_tap_marker),
            ) >= 0
            deferred_service = (
                "comp_touch_recording_boundary_service(" in main_source and
                "process_deferred_touch_runtime_action" in main_source
            )
            if not (dispatch_before_branch and deferred_service):
                errors.append("daily double-tap must defer recording while the panel is BUSY")

    daily_tap_tail = "} else if (gesture.type == COMP_TOUCH_GESTURE_SWIPE_LEFT ||"
    if double_tap_tail not in main_source or daily_tap_tail not in main_source:
        errors.append("daily tap branch must remain separately inspectable")
    else:
        daily_tap_block = main_source.split(double_tap_tail, 1)[1].split(daily_tap_tail, 1)[0]
        if "schedule_daily_tap_reaction" not in daily_tap_block:
            errors.append("daily tap must wait for the double-tap decision window")
        if "Companion_Screen_DailyTapAt" in daily_tap_block:
            errors.append("daily first tap must not start an e-paper refresh before double-tap classification")

    if "poll_touch_debug();\n        process_daily_tap_reaction(HAL_GetTick());" not in main_source:
        errors.append("idle loop must execute a deferred single-tap reaction after touch classification")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: FT6336 identity diagnostics and portable gesture boundary verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
