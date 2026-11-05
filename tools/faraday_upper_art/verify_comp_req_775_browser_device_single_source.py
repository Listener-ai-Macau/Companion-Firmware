#!/usr/bin/env python3
"""Audit the current fixed-browser to WB55 single-source product chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FIXED_URL = (
    "http://127.0.0.1:4185/"
    ".cache/validation/comp-req-628-status-bar/index.html"
)
PAGE_SHA256 = "D308CB63D287EFADC6DAC70F5E0DDE1BCA3AD13803B5A93E625BBB8505A7DAAE"
FAMILIES = (
    "calm", "curious", "delighted", "warm", "playful", "sleepy",
    "bashful", "thoughtful", "focused", "alert",
)
RESOURCE_ID = "28CF8B30A7AA3090647DBAA8F98030985CA0EE193BBFF20E5299E135E2107BF4"
CONTRACT_SHA256 = "0A66B1F7ECED5A7C82EBD521D88AC4C8D813D2C5BB5C75CD5E66719C8F4C8CB9"


def load(relative: str) -> dict:
    return json.loads((REPO / relative).read_text(encoding="utf-8"))


def normalized_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError(f"unterminated function: {signature}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--boot-dir",
        type=Path,
        default=Path(
            ".cache/validation/comp-req-775-browser-device-single-source-final/"
            "54-generation15-boot-90s"
        ),
    )
    parser.add_argument(
        "--browser-pointer",
        type=Path,
        default=Path(
            ".cache/validation/comp-req-775-browser-device-single-source-final/"
            "22-fixed-page-complete-pointer-replay/MACHINE_READY.json"
        ),
    )
    parser.add_argument(
        "--life-trace",
        type=Path,
        default=Path(
            ".cache/validation/comp-req-775-browser-device-single-source-final/"
            "64-life-trace-100-commits/MACHINE_READY.json"
        ),
    )
    args = parser.parse_args()

    with urllib.request.urlopen(FIXED_URL, timeout=5) as response:
        http_status = response.status
        page_bytes = response.read()
    source = load(
        ".cache/validation/comp-req-775-browser-device-single-source-final/"
        "45-menu-full-state-prototype/source-pack-full/source-pack-manifest.json"
    )
    generation = load(
        ".cache/validation/comp-req-775-browser-device-single-source-final/"
        "50-generation-15-compacted/generation.json"
    )
    generation_verification = load(
        ".cache/validation/comp-req-775-browser-device-single-source-final/"
        "50-generation-15-compacted/verification.json"
    )
    sync = load(
        ".cache/validation/comp-req-775-browser-device-single-source-final/"
        "50-generation-15-compacted/hardware/SYNC_RECEIPT.json"
    )
    interaction = load(
        ".cache/validation/comp-req-775-menu-hold-milestone-source-pack-v3/"
        "interaction-contract.json"
    )
    generated = load(
        "cubeide/Companion_Nucleo_WB55RG_Bringup/"
        "build_comp_req_775_recording_resources/generated/"
        "companion_browser_interaction_contract.json"
    )
    build = load(
        ".cache/validation/comp-req-775-incremental-sync/"
        "FIRMWARE_BUILD_READY.json"
    )
    boot_dir = args.boot_dir if args.boot_dir.is_absolute() else REPO / args.boot_dir
    browser_pointer_path = (
        args.browser_pointer
        if args.browser_pointer.is_absolute()
        else REPO / args.browser_pointer
    )
    life_trace_path = (
        args.life_trace if args.life_trace.is_absolute()
        else REPO / args.life_trace
    )
    boot = json.loads((boot_dir / "BOOT_EVIDENCE.json").read_text(encoding="utf-8"))
    browser_pointer = json.loads(browser_pointer_path.read_text(encoding="utf-8"))
    life_trace = json.loads(life_trace_path.read_text(encoding="utf-8-sig"))
    boot_log = (boot_dir / "nucleo-serial-raw.log").read_text(
        encoding="utf-8", errors="replace"
    )
    app = (
        REPO / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    ).read_text(encoding="utf-8")
    main_source = (
        REPO / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    ).read_text(encoding="utf-8")
    panel_source = (
        REPO / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    ).read_text(encoding="utf-8")
    menu_source = (
        REPO / "app/companion_pendant/epaper/screen_menu.c"
    ).read_text(encoding="utf-8")
    browser_runtime_source = (
        REPO / "app/companion_pendant/touch/browser_interaction_runtime.c"
    ).read_text(encoding="utf-8")
    service_loop = main_source.rsplit(
        "static void Companion_App_ServiceForever(void)", 1
    )[1].split("static bool button_is_pressed", 1)[0]
    low_power_policy = main_source.split(
        "static void update_low_power_policy(void)", 1
    )[1].split("void Companion_App_OnScreenRefreshComplete", 1)[0]
    low_power_freertos_keepalive_index = low_power_policy.find(
        "FreeRTOS must keep its tick and worker tasks alive"
    )
    low_power_blocker_index = low_power_policy.find(
        "COMP_POWER_BLOCKER_MIC_CAPTURE"
    )
    low_power_sleep_due_index = low_power_policy.find(
        "else if (s_low_power_idle_pose_due)"
    )
    low_power_freertos_return_index = low_power_policy.rfind(
        "#if COMPANION_USE_FREERTOS"
    )
    visible_idle_gate = low_power_policy.split(
        "visible_idle_allowed =", 1
    )[1].split("stop_allowed =", 1)[0]
    menu_enter_boundary = app.split(
        "bool Companion_Screen_MenuRequestClean", 1
    )[1].split("bool Companion_Screen_MenuMaintenance", 1)[0]
    sleep_enter_boundary = app.split(
        "bool Companion_Screen_EnterLowPowerIdle(void)", 1
    )[1].split("bool Companion_Screen_ShowDaily(void)", 1)[0]
    menu_exit_boundary = app.split(
        "bool Companion_Screen_ShowDailyClean(void)", 1
    )[1].split("bool Companion_Screen_WakeDailyClean(void)", 1)[0]
    sleep_wake_boundary = app.split(
        "bool Companion_Screen_WakeDailyClean(void)", 1
    )[1].split("bool Companion_Screen_DailyExpression", 1)[0]
    menu_hold_cancel = app.split(
        "bool Companion_Screen_MenuHoldCancel(void)", 1
    )[1].split("bool Companion_Screen_ExpressionPreview", 1)[0]
    early_touch_index = service_loop.find("poll_touch_debug();")
    early_boundary_index = service_loop.find(
        "process_deferred_touch_runtime_action();"
    )
    first_freertos_display_pump_index = service_loop.find(
        "MX_APPE_Process();", early_boundary_index
    )
    offline_capture_policy_index = service_loop.find(
        "const bool offline_capture_hot"
    )

    states = source["states"]
    state_ids = {state["id"] for state in states}
    kind_counts = Counter(state.get("kind") for state in states)
    life_commit_counts = {
        family: sum(
            int(state.get("dwell_commits", 1))
            for state in states
            if state.get("kind") == "life" and state.get("family") == family
        )
        for family in FAMILIES
    }
    protected = sync["protected_partitions"]
    zero_write_keys = (
        "fus_write_bytes", "loader_internal_flash_write_bytes",
        "mass_erase_calls", "option_byte_write_bytes",
        "ota_app_internal_flash_write_bytes", "other_internal_flash_write_bytes",
        "otp_write_bytes", "recording_partition_write_bytes",
    )
    checks = {
        "fixed_url_http_200": http_status == 200,
        "fixed_page_identity": normalized_sha256(page_bytes) == PAGE_SHA256,
        "source_pack_pass": source.get("status") == "PASS",
        "source_pack_page_identity": source.get("source", {}).get("page_sha256") == PAGE_SHA256,
        "ten_life_families": all(life_commit_counts[family] >= 100 for family in FAMILIES),
        "ten_life_families_first_100_commits_exact": (
            life_trace.get("status") == "MACHINE_READY"
            and all(life_trace.get("checks", {}).values())
            and all(
                life_trace.get("observed", {}).get(family, {}).get("commits", 0)
                >= 100
                for family in FAMILIES
            )
        ),
        "menu_state_coverage": kind_counts["menu_ui"] == 2110,
        "pointer_state_coverage": kind_counts["pointer_follow"] == 250,
        "generation_complete_state_map": set(generation.get("entries_by_id", {})) == state_ids,
        "generation_identity": generation.get("generation") == 15 and generation.get("resource_id") == RESOURCE_ID,
        "all_4995_frames_pixel_equivalent": (
            generation_verification.get("status") == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation_verification.get("states_checked") == len(states) == 4995
            and generation_verification.get("strict_1bpp") is True
        ),
        "interaction_page_identity": interaction.get("source", {}).get("page_sha256") == PAGE_SHA256,
        "four_authored_hold_milestones": [
            row.get("held_ms") for row in interaction.get("gesture", {}).get("menu_hold_milestones", [])
        ] == [1000, 1500, 2000, 2500],
        "generated_contract_identity": (
            generated.get("contract_sha256") == CONTRACT_SHA256
            and generated.get("product_resource_id") == RESOURCE_ID
            and generated.get("life_family_mask") == 0x03FF
            and generated.get("pointer_state_count") == 250
            and generated.get("menu_state_count") == 2110
            and generated.get("menu_screen_count") == 13
            and generated.get("menu_row_count") == 63
        ),
        "resource_sync_readback": (
            sync.get("status") == "COMPLETE"
            and sync.get("partition_readback_verified") is True
            and sync.get("active_generation_after") == 15
            and sync.get("target_root", {}).get("resource_id") == RESOURCE_ID
            and sync.get("generation_compaction") is True
        ),
        "protected_regions_zero_write": all(protected.get(key) == 0 for key in zero_write_keys),
        "recording_resource_unchanged": (
            sync.get("recording_resource_pack", {}).get("current_match") is True
            and sync.get("recording_resource_pack", {}).get("changed_sector_count") == 0
        ),
        "formal_app_build": build.get("status") == "FIRMWARE_BUILD_READY" and all(build.get("checks", {}).values()),
        "ota_app_address_guard": (
            build.get("firmware", {}).get("hex_minimum_address") == "0x08007000"
            and int(build.get("firmware", {}).get("hex_maximum_address_exclusive"), 16) <= 0x08080000
        ),
        "boot_generation_identity": "ui_generation=active generation=15 resource_id=28CF8B30 entries=4995" in boot_log,
        "boot_1000_hold_replay": (
            "menu_hold_replay=pass cycles=1000" in boot_log
            and f"contract_sha256={CONTRACT_SHA256}" in boot_log
        ),
        "boot_1000_mixed_trajectory_replay": (
            "mixed_trajectory_replay=pass cycles=1000" in boot_log
            and "failed_cycle=1000 expected=none actual=none" in boot_log
        ),
        "boot_watchdog_and_touch": "[watchdog] healthy=1" in boot_log and "wait_buffer_selftest_done pass=1" in boot_log,
        "boot_refresh_contract": (
            boot.get("status") == "MACHINE_READY"
            and all(boot.get("checks", {}).values())
        ),
        "boot_seeded_blink_partial_only": (
            "[screen-blink] scheduler=enabled source=browser_seeded_v1"
            in boot_log
            and "[screen-blink] phase=closed" in boot_log
            and "[screen-blink] phase=open" in boot_log
            and "natural_blink_compose source=current_life" in boot_log
            and "control=0xCF window=5-20,60-106 bytes=752" in boot_log
        ),
        "browser_pointer_contract": (
            browser_pointer.get("verdict") == "MACHINE_READY"
            and browser_pointer.get("pointer_contract", {})
            .get("lower_left_double_tap", {})
            .get("exact_return_frame") is True
        ),
        "firmware_no_pointer_state_string_builder": "pointer_follow_%" not in app,
        "firmware_no_menu_state_string_builder": "menu_ui_%" not in app,
        "firmware_no_sticky_hold_bucket": "s_companion_comp_req638_menu_progress_bucket" not in app,
        "irq_only_does_not_cancel_life_scheduler": (
            "Companion_App_ShouldCancelAutomaticMotionForTouch()" in app
            and "automatic_request &&" in app
            and "s_touch_irq_count != s_touch_irq_consumed_count" not in main_source.split(
                "bool Companion_App_ShouldCancelAutomaticMotionForTouch(void)", 1
            )[1].split("static void process_menu_entry_transition", 1)[0]
        ),
        "menu_exit_contact_does_not_cancel_life_scheduler": (
            "menu_exit_contact_suppressed = s_menu_exit_contact_suppressed;"
            in main_source
            and "return !menu_exit_contact_suppressed && contact_pending;"
            in main_source
        ),
        "firmware_uses_generated_state_tables": all(
            token in app
            for token in (
                "companion_browser_pointer_state_id_format(",
                "companion_browser_menu_state_id_format(",
                "companion_browser_life_episode_limit(",
                "companion_browser_generation_resource_id",
            )
        ),
        "main_uses_generated_gesture_contract": all(
            token in main_source
            for token in (
                "COMPANION_BROWSER_INTERACTION_MENU_RIGHT_EXIT_THRESHOLD_200",
                "COMPANION_BROWSER_INTERACTION_MENU_VERTICAL_SWIPE_THRESHOLD_200",
                "COMPANION_BROWSER_INTERACTION_MENU_SCROLL_CADENCE_MS",
                "companion_browser_menu_hold_milestones[",
            )
        ),
        "menu_uses_generated_browser_action_map": all(
            token in menu_source
            for token in (
                '#include "companion_browser_interaction_contract.h"',
                "companion_browser_menu_item_counts",
                "companion_browser_menu_row(",
                "COMPANION_BROWSER_MENU_KIND_STATUS",
                "COMPANION_BROWSER_MENU_KIND_NAVIGATE",
                "COMPANION_BROWSER_MENU_KIND_BACK",
            )
        ),
        "menu_uses_exact_browser_timing_and_phases": all(
            token in main_source
            for token in (
                "COMPANION_BROWSER_MENU_TAP_ACK_MS",
                "COMPANION_BROWSER_MENU_ACTION_PROCESSING_MS",
                "browser_menu_navigation item=%u phase=ack",
                'kind == COMPANION_BROWSER_MENU_KIND_ACTION\n'
                '                           ? "processing"',
                "COMP_SCREEN_MENU_FLAG_ACTION_RESULT",
                "browser_menu_action item=%u phase=result",
            )
        ),
        "menu_sleep_uses_one_explicit_maintenance_boundary": (
            "browser_event=menu_sleep boundary=single_maintenance" in main_source
            and "Companion_Screen_EnterLowPowerIdle()" in main_source
            and "COMP_EPAPER_REFRESH_MAINTENANCE" in app.split(
                "bool Companion_Screen_EnterLowPowerIdle(void)", 1
            )[1].split("bool Companion_Screen_ShowDaily(void)", 1)[0]
        ),
        "surface_boundaries_are_guarded_and_exactly_one_visible_full": (
            "s_companion_screen_surface_owner != COMPANION_SCREEN_SURFACE_HOME"
                in menu_enter_boundary
            and "s_companion_screen_surface_owner != COMPANION_SCREEN_SURFACE_MENU"
                in menu_exit_boundary
            and "s_companion_screen_surface_owner != COMPANION_SCREEN_SURFACE_HOME &&"
                in sleep_enter_boundary
            and "s_companion_screen_surface_owner != COMPANION_SCREEN_SURFACE_MENU"
                in sleep_enter_boundary
            and "s_companion_screen_surface_owner != COMPANION_SCREEN_SURFACE_LOW_POWER"
                in sleep_wake_boundary
            and all(
                body.count("COMP_EPAPER_REFRESH_MAINTENANCE") == 1
                for body in (
                    menu_enter_boundary,
                    menu_exit_boundary,
                    sleep_enter_boundary,
                    sleep_wake_boundary,
                )
            )
            and "ssd1681_accepted_true_full_activation(" in panel_source
            and "control=0xC7" in panel_source
        ),
        "cancelled_hold_is_atomic_exact_partial_return": (
            "cancel_daily_menu_hold(" in main_source
            and "s_menu_entry_pending = false;" in main_source.rsplit(
                "static bool cancel_daily_menu_hold", 1
            )[1].split("static void process_daily_menu_hold_progress", 1)[0]
            and "s_daily_menu_hold_cancel_suppress_pointer_once = true;"
                in main_source
            and "if (!hold_cancelled && !Companion_Screen_IsMenuVisible())"
                in main_source
            and "s_companion_menu_hold_return_frame" in menu_hold_cancel
            and "comp_epaper_display_queue_discard_kind(" in menu_hold_cancel
            and "comp_epaper_display_queue_enqueue_expression_frame("
                in menu_hold_cancel
            and "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE" in menu_hold_cancel
            and "COMP_EPAPER_REFRESH_MAINTENANCE" not in menu_hold_cancel
            and "menu_hold_cancel result=exact_return_queued" in menu_hold_cancel
            and "reason=menu_hold_cancel_commit resume=browser_life" in app
        ),
        "hold_runtime_end_replay_rejects_all_late_milestones": (
            "for (uint8_t cancel_after = 0u;" in browser_runtime_source
            and "comp_browser_menu_hold_end(&runtime);" in browser_runtime_source
            and "runtime.active || runtime.next_milestone != 0u" in browser_runtime_source
            and "comp_browser_menu_hold_next(&runtime, UINT32_MAX, &event)"
                in browser_runtime_source
            and "comp_browser_menu_hold_commit(&runtime, 0u)"
                in browser_runtime_source
        ),
        "awake_life_uses_generated_continuous_contract": (
            "COMPANION_BROWSER_INTERACTION_AWAKE_LIFE_CONTINUOUS" in app
            and "comp_epaper_motion_coordinator_keep_awake(" in app
            and "[screen-life] authored_loop" in app
            and boot_log.count("[screen-life] family=calm action=") >= 8
        ),
        "charging_choreography_uses_generated_three_frame_timeline": (
            all(state_id in state_ids for state_id in (
                "charging_0", "charging_1", "charging_2"
            ))
            and "Companion_CompReq775ChargingTiming" in app
            and "companion_browser_cemp_function_clip_timings" in app
            and "Companion_Display_EmitChargingAccessoryFrame" in app
            and "source=browser_timeline" in app
            and "copy_clip_frame" in panel_source
            and "copy_clip_last_frame" not in panel_source.split(
                "static bool ssd1681_compose_charger_overlay", 1
            )[1].split("#endif", 1)[0]
        ),
        "touch_recording_feedback_precedes_bounded_initial_erase": (
            "FLASH_RECORDING_ASYNC_INITIAL_ERASE_BYTES 4096u" in main_source
            and "COMPANION_STORAGE_JOB_RECORDING_ERASE_AHEAD" in main_source
            and "touch_recording_pending_start" in main_source
            and "latency_class=immediate" in main_source
            and "initial_bytes=%lu" in main_source
            and "total_bytes=%lu" in main_source
        ),
        "recording_erase_ahead_interleaves_cemp_and_touch_flash_access": (
            "job.kind == COMPANION_STORAGE_JOB_RECORDING_PREPARE ||"
                in main_source
            and "job.kind == COMPANION_STORAGE_JOB_RECORDING_ERASE_AHEAD"
                in main_source
            and "interleave_ui ? \"ui_interleaved_4k\" : \"fast_64k\""
                in main_source
            and "if (!interleave_ui && remaining >= block_size" in main_source
            and "if (interleave_ui) {\n            /* A sector command still owns"
                in main_source
            and "taskYIELD();" in main_source
        ),
        "touch_recording_stop_panel_commit_hands_off_to_rec_task": (
            "Companion_Screen_RecordingStopFeedback(" in main_source
            and "Companion_Rtos_ServiceRecordingStop();\n"
                "        Companion_Recording_ServiceHotTick();" in main_source
            and "stage=visual_handoff" in main_source
            and "stage=finalize_begin owner=%s visual_precedes=%u" in main_source
            and "action=stop_commit request=%lu visible=%u" in app
            and "s_companion_recording_stop_feedback_resolved = true;" in app
            and "touch_recording_stop_feedback" in app
        ),
        "pending_recording_cancel_uses_same_exact_return_path": (
            "s_recording_fsm.state == COMP_RECORDING_STATE_PENDING_START"
                in main_source
            and "return_queued = Companion_Screen_RecordingStopFeedback(\n"
                "                gesture_submitted_ms);" in main_source
            and "action=cancel_pending " in main_source
            and "restore=exact_return result=%u" in main_source
            and "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED,\n"
                "                \"touch_recording_prepare_canceled\""
                not in main_source
        ),
        "freertos_touch_and_recording_boundary_precede_first_display_pump": (
            0 <= early_touch_index < early_boundary_index
            < offline_capture_policy_index
            < first_freertos_display_pump_index
            and "Input already owns FT6336 sampling while SSD1681 is BUSY"
                in service_loop
        ),
        "freertos_keeps_tasks_alive_without_bypassing_visible_sleep": (
            0 <= low_power_freertos_keepalive_index
            < low_power_blocker_index
            < low_power_sleep_due_index
            < low_power_freertos_return_index
            and "s_low_power_stop_allowed = false;" in low_power_policy
            and "Companion_Screen_EnterLowPowerIdle()" in low_power_policy
            and "COMP_POWER_BLOCKER_UI_PENDING" not in visible_idle_gate
            and "COMP_POWER_BLOCKER_MIC_CAPTURE" in visible_idle_gate
            and "COMP_POWER_BLOCKER_TOUCH_CONTACT" in visible_idle_gate
            and "COMP_POWER_BLOCKER_TOUCH_CONFIRMATION" in visible_idle_gate
            and "visible_idle_allowed = true;" in low_power_policy
            and "stays awake and polls FT6336" in low_power_policy
        ),
        "recording_exit_restores_exact_browser_return_frame_once": (
            "s_companion_recording_return_clip_name" in app
            and "s_companion_recording_return_frame" in app
            and "s_companion_recording_return_decision" in app
            and "action=capture_return valid=%u clip=%s " in app
            and '"frame=%u in_clip=%u charging=%u charger_frame=%u' in app
            and "restore_clip=%s restore_frame=%u restore_in_clip=%u" in app
            and "comp_epaper_display_queue_discard_kind(" in app
            and "comp_epaper_display_queue_enqueue_expression_frame(" in app
            and "s_companion_recording_return_frame.frame_index" in app
            and "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE" in app
            and "Companion_Screen_StartNamedClip(\n"
                "        s_companion_recording_return_clip_name" not in app
            and "action=resume_daily after=stop_commit" in app
            and "s_companion_last_emote_frame.clip_name != NULL)" in app
            and "player_decision_live=%u" in app
        ),
        "recording_first_tap_reserves_next_display_slot": (
            "Companion_Screen_RecordingExitIntent(" in main_source
            and "recording_exit_intent gesture=tap" in main_source
            and "s_recording_fsm.state == COMP_RECORDING_STATE_PENDING_START ||\n"
                "             s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING"
                in main_source
            and "s_companion_recording_exit_intent_pending" in app
            and "action=exit_intent phase=armed" in app
            and "action=exit_intent phase=timeout_resume" in app
            and "display_request=0" in app
            and app.index("s_companion_recording_exit_intent_pending = false;",
                          app.index("bool Companion_Screen_RecordingStopFeedback"))
                < app.index("comp_epaper_display_queue_discard_display_class(",
                            app.index("bool Companion_Screen_RecordingStopFeedback"))
        ),
        "recording_anywhere_down_reserves_display_before_first_release": (
            "recording_exit_intent gesture=down scope=anywhere" in main_source
            and "sample->event == COMP_FT6336_TOUCH_EVENT_DOWN" in main_source
            and "s_recording_fsm.state == COMP_RECORDING_STATE_PENDING_START ||\n"
                in main_source
            and "s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING)) {"
                in main_source
            and "!Companion_Screen_IsMenuVisible()" in main_source
        ),
        "recording_busy_input_fast_latch_precedes_buffer_replay": (
            "bool Companion_Screen_RecordingExitIntentFastLatch" in app
            and "static volatile bool s_companion_recording_exit_intent_pending"
                in app
            and "Companion_Screen_RecordingExitIntentFastLatch(" in main_source
            and main_source.index(
                "Companion_Screen_RecordingExitIntentFastLatch(",
                main_source.index("static void Companion_Rtos_InputTask"),
            )
            < main_source.index(
                "buffer_touch_sample_during_panel_wait(&sample, now_ms);",
                main_source.index("static void Companion_Rtos_InputTask"),
            )
        ),
        "recording_exit_intent_blocks_queued_frame_before_dequeue": (
            "queued_frame=preserved" in app
            and "s_companion_recording_exit_intent_pending" in app
            and app.index("if (s_companion_recording_exit_intent_pending",
                          app.index("static void Companion_Display_Task(void)\n{"))
                < app.index("comp_epaper_display_queue_dequeue(",
                            app.index("static void Companion_Display_Task(void)\n{"))
            and "gesture_to_visible_ms=%lu return_budget_ms=2600" in app
            and "return_refresh=single_cached_mode2_0xcf" in app
            and "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE" in function_body(
                app, "bool Companion_Screen_RecordingStopFeedback("
            )
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    receipt = {
        "schema": "companion.comp_req_775.browser_device_single_source_audit.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "fixed_url": FIXED_URL,
        "page_sha256": PAGE_SHA256,
        "contract_sha256": CONTRACT_SHA256,
        "resource_id": RESOURCE_ID,
        "generation": 15,
        "state_count": len(states),
        "kind_counts": dict(kind_counts),
        "life_commit_counts": life_commit_counts,
        "hardware_contact": 0,
        "human_acceptance": "pending",
        "evidence": {
            "boot_dir": str(boot_dir.relative_to(REPO)).replace("\\", "/"),
            "browser_pointer": str(browser_pointer_path.relative_to(REPO)).replace("\\", "/"),
            "life_trace": str(life_trace_path.relative_to(REPO)).replace("\\", "/"),
        },
    }
    output = args.output if args.output.is_absolute() else REPO / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
