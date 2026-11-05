#!/usr/bin/env python3
"""Guard browser-equivalent FT6336 pointer lifecycle handling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
)
APP_BLE = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
)
SCREEN_UI = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/companion_screen_ui.h"
)
POWER_POLICY = ROOT / "app/companion_pendant/power/power_policy.h"
BROWSER_RUNTIME = (
    ROOT / "app/companion_pendant/touch/browser_interaction_runtime.c"
)
PANEL = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
SCREEN_LIFECYCLE = (
    ROOT / "app/companion_pendant/epaper/screen_lifecycle.c"
)
OUTPUT = (
    ROOT
    / ".cache/validation/comp-req-775-incremental-sync"
    / "POINTER_EQUIVALENCE_READY.json"
)


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


def main() -> int:
    source = MAIN.read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    screen_ui = SCREEN_UI.read_text(encoding="utf-8")
    power_policy = POWER_POLICY.read_text(encoding="utf-8")
    browser_runtime = BROWSER_RUNTIME.read_text(encoding="utf-8")
    panel = PANEL.read_text(encoding="utf-8")
    screen_lifecycle = SCREEN_LIFECYCLE.read_text(encoding="utf-8")
    wait = function_body(source, "capture_touch_during_display_wait(")
    input_task = function_body(source, "Companion_Rtos_InputTask(")
    input_irq = function_body(source, "EXTI9_5_IRQHandler(")
    poll = function_body(source, "poll_touch_debug(")
    buffer = function_body(
        source, "buffer_touch_sample_during_panel_wait("
    )
    process = function_body(source, "process_touch_debug_sample(")
    wake = function_body(source, "request_low_power_touch_wake(")
    recording_touch_due = function_body(
        source, "static bool service_recording_touch_if_due(void)"
    )
    recording_branch = source.find(
        "if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {"
    )
    recording_due_call = source.find(
        "service_recording_touch_if_due()", recording_branch
    )
    recording_capture = source.find(
        "capture_microphone_block(", recording_due_call
    )
    automatic_motion = function_body(
        app_ble, "Companion_Display_ProcessDueTracks("
    )
    automatic_frame = function_body(
        app_ble, "Companion_Display_EmitAutomaticMotionFrame("
    )
    idle_enter = function_body(
        app_ble, "bool Companion_Screen_EnterLowPowerIdle("
    )
    surface_complete = function_body(
        app_ble, "static void Companion_Screen_CompleteSurfaceRequest("
    )
    lifecycle_complete = function_body(
        screen_lifecycle, "bool comp_screen_lifecycle_complete("
    )
    touch_lifecycle_buffered = function_body(
        source, "int Companion_TouchLifecycleBufferedForDisplay("
    )
    display_task = function_body(
        app_ble, "static void Companion_Display_Task("
    )
    low_power_policy = function_body(
        source, "static void update_low_power_policy("
    )
    checks = {
        "rtos_input_task_is_single_ft6336_owner": all(
            token in input_task
            for token in (
                "companion_touch_ft6336_stm32wb_poll(&s_touch, &sample)",
                "buffer_touch_sample_during_panel_wait(&sample, now_ms)",
                "TOUCH_RTOS_COALESCE_MS",
                "companion_watchdog_heartbeat(COMPANION_WATCHDOG_TASK_INPUT)",
            )
        ),
        "rtos_display_wait_never_polls_touch_i2c": (
            "#if COMPANION_USE_FREERTOS" in wait
            and "(void)now_ms;" in wait
            and "companion_watchdog_heartbeat(COMPANION_WATCHDOG_TASK_SVC)"
            in wait
            and wait.find("return;")
            < wait.find("companion_touch_ft6336_stm32wb_poll(")
        ),
        "rtos_svc_only_drains_timestamped_pointer_queue": (
            "#if COMPANION_USE_FREERTOS" in poll
            and "pop_buffered_touch_sample(&entry)" in poll
            and "process_touch_debug_sample(&entry.sample," in poll
            and "entry.timestamp_ms," in poll
            and poll.find("return;")
            < poll.find("companion_touch_ft6336_stm32wb_poll(")
        ),
        "ft6336_irq_wakes_input_owner": all(
            token in input_irq
            for token in (
                "s_companion_input_task_running",
                "vTaskNotifyGiveFromISR(s_companion_input_task",
                "portYIELD_FROM_ISR(higher_priority_task_woken)",
            )
        ),
        "rtos_task_priority_contract_is_explicit": all(
            token in source
            for token in (
                '"rec",\n                    4864,\n                    NULL,\n                    5,',
                '"input",\n                    320,\n                    NULL,\n                    6,',
                '"svc",\n                    1280,\n                    NULL,\n                    3,',
                "vTaskDelay(pdMS_TO_TICKS(1u));",
                '"flash",\n                    768,\n                    NULL,\n                    2,',
            )
        ),
        "panel_busy_only_buffers_raw_pointer_samples": (
            "buffer_touch_sample_during_panel_wait(&sample, now_ms)" in wait
            and "process_touch_debug_sample(" not in wait
            and "handle_touch_menu_sample(" not in wait
        ),
        "buffer_preserves_down_latest_move_and_up": all(
            token in buffer
            for token in (
                "push_buffered_touch_sample(&normalized, now_ms)",
                "s_touch_refresh_latest_contact",
                "flush_buffered_touch_latest_contact()",
            )
        ),
        "busy_contact_first_replays_as_new_pointerdown": all(
            token in buffer
            for token in (
                "s_touch_refresh_last_release_ms",
                "release_gap_ms >= TOUCH_RECONTACT_RESTART_GAP_MS",
                "normalized.event = COMP_FT6336_TOUCH_EVENT_DOWN",
                "s_touch_refresh_last_contact.sample",
            )
        ),
        "repeated_down_is_normalized_to_pointer_move": all(
            token in source
            for token in (
                "normalized.event = COMP_FT6336_TOUCH_EVENT_CONTACT",
                "A repeated FT6336 DOWN is pointermove",
                "Browser pointer semantics treat every later report as move",
            )
        ),
        "browser_double_tap_window_is_350ms": (
            "COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_GAP_MS" in source
            and "COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_MAX_DISTANCE_200"
            in source
        ),
        "recording_double_tap_preempts_historical_queue_drain": (
            "comp_touch_recording_boundary_pending(" in poll
            and "&s_touch_recording_boundary) != 0u" in poll
            and "break;" in poll
            and poll.find("process_touch_debug_sample(&entry.sample")
            < poll.find("comp_touch_recording_boundary_pending(")
            < poll.find("break;")
        ),
        "recording_exit_intent_waits_for_buffered_terminal_sample": (
            all(
                token in touch_lifecycle_buffered
                for token in (
                    "s_touch_refresh_capture_active",
                    "s_touch_refresh_buffer_count != 0u",
                    "s_touch_refresh_latest_contact_valid",
                )
            )
            and "s_companion_recording_exit_intent_pending" in display_task
            and "Companion_TouchLifecycleBufferedForDisplay() != 0"
            in display_task
        ),
        "right_swipe_and_vertical_drag_share_normalized_gesture": all(
            token in source
            for token in (
                "gesture.type == COMP_TOUCH_GESTURE_SWIPE_RIGHT",
                "TOUCH_MENU_RIGHT_EXIT_MIN_MOVE_PX",
                "menu_right_swipe_rejected",
                "menu_right_swipe_exit",
                "menu_left_swipe action=none",
                "comp_touch_gesture_is_vertical_drag(&s_touch_gesture)",
                "browser_event=menu_vertical_drag",
            )
        ),
        "ordinary_home_tap_matches_browser_immediate_commit": all(
            token in source
            for token in (
                "touch_is_recording_corner",
                "COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MAX_X_200",
                "COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MIN_Y_200",
                "immediate_non_recording_area",
                "immediate=%u cemp_result=%s",
            )
        ),
        "non_corner_double_tap_cannot_start_recording": all(
            token in source
            for token in (
                "non_recording_area_double_tap",
                "!touch_is_recording_corner(gesture.end_x, gesture.end_y)",
                "!non_recording_area_double_tap",
            )
        ),
        "recording_hot_path_keeps_pointer_service": (
            "#define RECORDING_TOUCH_IDLE_POLL_MS 20u" in source
            and all(
                token in recording_touch_due
                for token in (
                    "recording_touch_work_pending()",
                    "TOUCH_ACTIVE_POLL_MS",
                    "RECORDING_TOUCH_IDLE_POLL_MS",
                    "return service_recording_touch();",
                )
            )
            and 0 <= recording_branch < recording_due_call < recording_capture
            and source.find(
                "if (!service_recording_touch_if_due())",
                recording_branch,
                recording_capture,
            )
            >= 0
        ),
        "pointer_release_work_blocks_stop_until_drained": (
            "COMP_POWER_BLOCKER_UI_PENDING" in power_policy
            and "Companion_Screen_HasPendingWork(void)" in screen_ui
            and all(
                token in app_ble
                for token in (
                    "bool Companion_Screen_HasPendingWork(void)",
                    "comp_epaper_display_queue_pending(&s_companion_display_queue)",
                )
            )
            and all(
                token in source
                for token in (
                    "COMP_POWER_BLOCKER_UI_PENDING",
                    "Companion_Screen_HasPendingWork()",
                    "s_touch_refresh_buffer_count != 0u",
                    "s_touch_refresh_latest_contact_valid",
                    "s_daily_tap_arbiter.pending",
                    "comp_touch_recording_boundary_pending(",
                    "s_visual_runtime.ring_count != 0u",
                )
            )
        ),
        "pending_touch_irq_blocks_stop_before_ft6336_poll": all(
            token in source
            for token in (
                "COMP_POWER_BLOCKER_SCREEN_WAIT",
                "s_touch_irq_count !=",
                "s_touch_irq_consumed_count ||",
                "poll_touch_debug();",
            )
        ),
        "menu_hold_uses_browser_visible_timeline": (
            all(
            token in source
            for token in (
                "comp_browser_menu_hold_begin(&s_daily_menu_hold_runtime)",
                "comp_browser_menu_hold_next(",
                "comp_browser_menu_hold_commit(",
                "comp_browser_menu_hold_end(&s_daily_menu_hold_runtime)",
                "Companion_Screen_MenuHoldState(",
                "event.state_id",
            )
            )
            and all(
            token in app_ble
            for token in (
                "bool Companion_Screen_MenuHoldState(const char *state_id",
                "Companion_CompReq638CanonicalClipForState(",
                "COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT",
                "comp_browser_menu_hold_verify_replay(",
                '"failed_cycle=%u failed_bucket=%u contract_sha256=%s',
            )
            )
            and all(
                token in browser_runtime
                for token in (
                    "companion_browser_menu_hold_milestones[",
                    "runtime->next_milestone = 0u",
                    "event->state_id = milestone->state_id",
                    "runtime->next_milestone++",
                    "for (cycle = 0u; cycle < cycles; ++cycle)",
                )
            )
            and all(
                stale not in app_ble
                for stale in (
                    '"menu_progress_0"',
                    '"menu_progress_0_5"',
                    '"menu_progress_0_75"',
                    '"menu_progress_1"',
                )
            )
        ),
        "touch_clip_cadence_does_not_double_panel_latency": all(
            token in app_ble
            for token in (
                "panel_transaction_started_ms = HAL_GetTick();",
                "panel_transaction_ms = s_companion_panel_transaction_completed_ms -",
                "transport_credit_ms",
                "visible_dwell_ms - 1u",
                "comp_emote_player_tick_sequential(",
                "cadence_origin=panel_transaction_start",
            )
        ),
        "ordinary_exact_bands_and_single_plane_blink_have_separate_scope": (
            all(
                token in panel
                for token in (
                    "ssd1681_product_source_complete_window(",
                    "comp_epaper_refresh_coverage_expand(",
                    "ssd1681_product_stage_changed_byte_components(",
                    "if (window.changed && recording_overlay_only)",
                    "ssd1681_native_cached_mode2_movement_activation(",
                    "static const uint8_t native_mode2_source[] = {0xCFu};",
                    "ssd1681_write_plane_region(0x24u, s_frame, window)",
                    "Both remain on the accepted single-current-plane RAM topology.",
                    "single-current-plane path",
                )
            )
            and "functional_delta_windows[functional_delta_count++] =\n                        staged_regions[index];" not in panel
            and "blink_phase_parallel =" not in panel
            and "phase_parallel_blink == 2u" not in panel
        ),
        "recording_stop_owns_next_display_slot": all(
            token in app_ble
            for token in (
                "s_companion_recording_exit_intent_pending &&\n      s_companion_recording_stop_feedback_request_id == 0u",
                "if (s_companion_recording_stop_feedback_request_id != 0u)",
                "s_companion_browser_pointer_active = false;",
            )
        ),
        "daily_boundary_mode_reaches_first_automatic_frame": (
            "comp_epaper_refresh_mode_t refresh_mode" in automatic_motion
            and "Companion_Display_EmitAutomaticMotionFrame(&motion_request,"
            in automatic_motion
            and "refresh_mode" in automatic_frame
            and "Companion_Display_EmitEmoteFrameModeInternal("
            in automatic_frame
            and "refresh_mode, motion_request" in automatic_frame
            and all(
                token in app_ble
                for token in (
                    "Companion_Display_ProcessDueTracks(HAL_GetTick(), refresh_mode);",
                    "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE);",
                )
            )
        ),
        "low_power_wake_requests_one_fast_full_boundary": (
            "if (s_low_power_touch_wake_requested ||" in wake
            and "Companion_Screen_WakeDailyClean()" in wake
            and "visual=visible_lifecycle_full contact_scope=wake_only "
            in wake
            and "bool Companion_Screen_WakeDailyClean(void)" in app_ble
            and "low_power_boundary=wake" in app_ble
            and "COMP_EPAPER_REFRESH_MAINTENANCE" in app_ble
            and "Companion_Screen_WakeDailyClean(void)" in screen_ui
        ),
        "low_power_enter_freezes_only_after_visible_commit": (
            "s_companion_last_expression_frame_request_id" in idle_enter
            and "comp_epaper_display_queue_discard_kind(" in idle_enter
            and "discarded_pending_frames" in idle_enter
            and "surface_rollback" in idle_enter
            and "animation=running_until_commit" in idle_enter
            and "comp_emote_player_stop" not in idle_enter
            and "Companion_Screen_CompleteSurfaceRequest(" in display_task
            and "panel_result == COMP_EPAPER_PANEL_RESULT_OK" in display_task
            and "comp_screen_lifecycle_complete(" in surface_complete
            and "COMP_SCREEN_LIFECYCLE_ACTION_FREEZE_LOW_POWER"
            in surface_complete
            and "comp_emote_player_stop" in surface_complete
            and "resolved_surface = visible ? lifecycle->requested_surface"
            in lifecycle_complete
            and "lifecycle->rollback_surface" in lifecycle_complete
            and "if (visible)" in lifecycle_complete
            and "lifecycle->commit_count++" in lifecycle_complete
            and "lifecycle->rollback_count++" in lifecycle_complete
            and "freeze=after_visible_commit" in idle_enter
        ),
        "low_power_deadline_survives_transient_display_blocker": (
            "if (s_low_power_idle_pose_due && visible_idle_allowed" in low_power_policy
            and "Companion_Screen_EnterLowPowerIdle()" in low_power_policy
            and "s_low_power_idle_pose_due = false;" in low_power_policy
            and "if (!visible_idle_allowed)" not in low_power_policy
            and low_power_policy.find("Companion_Screen_EnterLowPowerIdle()")
            < low_power_policy.find("s_low_power_idle_pose_due = false;")
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.comp_req_775.pointer_equivalence.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "main_sha256": hashlib.sha256(MAIN.read_bytes()).hexdigest().upper(),
        "app_ble_sha256": hashlib.sha256(APP_BLE.read_bytes()).hexdigest().upper(),
        "screen_ui_sha256": hashlib.sha256(SCREEN_UI.read_bytes()).hexdigest().upper(),
        "power_policy_sha256": hashlib.sha256(
            POWER_POLICY.read_bytes()
        ).hexdigest().upper(),
        "browser_runtime_sha256": hashlib.sha256(
            BROWSER_RUNTIME.read_bytes()
        ).hexdigest().upper(),
        "panel_sha256": hashlib.sha256(PANEL.read_bytes()).hexdigest().upper(),
        "hardware_contact": 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
