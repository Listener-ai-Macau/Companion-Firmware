#!/usr/bin/env python3
"""Static checks for the WB55 Companion e-paper display queue boundary."""

from __future__ import annotations

import pathlib
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
QUEUE_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.c"
EXPRESSION_EVENTS_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.h"
EXPRESSION_EVENTS_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_events.c"
EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EXPRESSION_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
PANEL_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
PANEL_TARGET_STM32WB_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb.h"
PANEL_TARGET_STM32WB_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_target_stm32wb.c"
SCREEN_RUNTIME_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.h"
SCREEN_RUNTIME_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.c"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
APP_CONF = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "app_conf.h"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def slice_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    end_index = text.find(end, start_index)
    if end_index < 0:
        return text[start_index:]
    return text[start_index:end_index]


def check_queue_module(errors: list[str]) -> None:
    header = read(QUEUE_HEADER)
    source = read(QUEUE_SOURCE)
    for token in [
        '#include "expression_state.h"',
        '#include "pet_expression.h"',
        "COMP_EPAPER_DISPLAY_QUEUE_DEPTH",
        "COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES",
        "COMP_EPAPER_RENDER_STATE_ACCEPTED",
        "COMP_EPAPER_RENDER_STATE_RENDERED",
        "COMP_EPAPER_RENDER_STATE_BUSY",
        "COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_display_queue_enqueue_card_write",
        "comp_epaper_display_queue_enqueue_expression",
        "comp_epaper_display_queue_enqueue_pet_expression",
        "comp_epaper_display_queue_dequeue",
        "comp_epaper_display_queue_discard_kind",
        "comp_epaper_display_queue_set_resource_revision",
        "resource_revision",
        "active_resource_revision",
        "generation_switch_count",
        "last_stale_generation_discarded",
        "stale_generation_discard_count",
        "comp_epaper_display_queue_snapshot_t",
        "comp_epaper_display_queue_snapshot",
        "comp_epaper_display_queue_pending",
        "comp_epaper_display_queue_high_water_count",
        "high_water_count",
        "pet_pose",
    ]:
        require(token in header, f"display_queue.h missing {token}", errors)
    for token in [
        "memcpy(request->payload, payload, payload_len)",
        "queue->dropped_count++",
        "COMP_EPAPER_DISPLAY_QUEUE_FULL",
        "COMP_EPAPER_DISPLAY_QUEUE_PAYLOAD_TOO_LONG",
        "COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_expression_is_supported",
        "comp_pet_expression_pose_is_valid(pose)",
        "request->pet_pose = *pose",
        "(*out_request)->resource_revision = queue->active_resource_revision",
        "comp_epaper_display_queue_set_resource_revision",
        "queue->last_stale_generation_discarded = (uint32_t)discarded",
        "queue->generation_switch_count++",
        "queue->stale_generation_discard_count += (uint32_t)discarded",
        "request_kind > COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "queue->high_water_count = queue->count",
        "out_snapshot->pending_count = queue->count",
        "out_snapshot->high_water_count = queue->high_water_count",
        "out_snapshot->queue_depth = COMP_EPAPER_DISPLAY_QUEUE_DEPTH",
        "out_snapshot->active_resource_revision = queue->active_resource_revision",
        "out_snapshot->generation_switch_count = queue->generation_switch_count",
        "out_snapshot->last_stale_generation_discarded",
        "out_snapshot->stale_generation_discard_count",
        "comp_epaper_display_queue_high_water_count",
        "original_count - kept_count",
        "replace_pending_menu",
        "request->resource_revision = queue->active_resource_revision",
    ]:
        require(token in source, f"display_queue.c missing {token}", errors)
    for forbidden in ["HAL_", "GPIO", "SPI", "QSPI", "stm32", "STMWPAN", "UTIL_SEQ"]:
        require(forbidden.lower() not in (header + source).lower(), f"display queue must stay platform-free: {forbidden}", errors)


def check_expression_state(errors: list[str]) -> None:
    header = read(EXPRESSION_HEADER)
    source = read(EXPRESSION_SOURCE)
    expressions = [
        "IDLE",
        "LISTENING",
        "THINKING",
        "SPEAKING",
        "HAPPY",
        "SLEEPY",
        "RECORDING",
        "SYNC_COMPLETE",
        "LOW_BATTERY",
        "ERROR",
    ]
    for token in [
        "comp_epaper_expression_state_t",
        "comp_epaper_expression_state_snapshot_t",
        "comp_epaper_expression_decision_t",
        "comp_epaper_expression_state_apply_signal",
        "comp_epaper_expression_state_tick",
        "comp_epaper_expression_state_snapshot",
        "comp_epaper_expression_auto_recover_ms",
        "comp_epaper_expression_decision_crc32",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE",
        "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_HAPPY_MS",
        "visible_age_ms",
        "suppressed_duplicate_count",
    ]:
        require(token in header, f"expression_state.h missing {token}", errors)
    for expression in expressions:
        require(
            f"COMP_EPAPER_EXPRESSION_{expression}" in header,
            f"expression_state.h missing ExpressionV1 enum {expression}",
            errors,
        )
    for token in [
        '"idle"',
        '"listening"',
        '"thinking"',
        '"speaking"',
        '"happy"',
        '"sleepy"',
        '"recording"',
        '"sync_complete"',
        '"low_battery"',
        '"error"',
        "recording stored for sync",
        "Capture indicator stays visible",
        "decision.priority < state->priority",
        "decision.expression == state->current",
        "state->suppressed_duplicate_count++",
        "state->visible_age_ms += elapsed_ms",
        "comp_epaper_expression_state_snapshot",
        "out_snapshot->current = state->current",
        "out_snapshot->last_signal = state->last_signal",
        "out_snapshot->auto_recover_ms = comp_epaper_expression_auto_recover_ms(state->current)",
        "out_snapshot->suppressed_duplicate_count = state->suppressed_duplicate_count",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY",
        "quiet hours or display-off screen setting",
        "can_apply_lower_priority_signal",
        "state->current == COMP_EPAPER_EXPRESSION_IDLE",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_DISABLED_MS",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SYNC_COMPLETE_MS",
        "comp_epaper_expression_decision_crc32",
    ]:
        require(token in source, f"expression_state.c missing {token}", errors)
    for forbidden in ["HAL_", "GPIO", "SPI", "QSPI", "stm32", "STMWPAN", "UTIL_SEQ"]:
        require(
            forbidden.lower() not in (header + source).lower(),
            f"expression state must stay platform-free: {forbidden}",
            errors,
        )


def check_expression_events(errors: list[str]) -> None:
    header = read(EXPRESSION_EVENTS_HEADER)
    source = read(EXPRESSION_EVENTS_SOURCE)
    for token in [
        '#include "diag_log_events.h"',
        '#include "expression_state.h"',
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY_PERCENT 20u",
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY_MV 3600u",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED 0u",
        "comp_epaper_expression_signal_from_device_status",
        "COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING 1u",
        "COMP_EPAPER_EXPRESSION_SPEAKER_STATE_PROMPT_ACCEPTED 2u",
        "COMP_EPAPER_EXPRESSION_WAKE_EVENT_DETECTED 2u",
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER_BIT 3u",
        "comp_epaper_expression_signal_from_diag_event",
        "comp_epaper_expression_signal_from_ota_readiness",
    ]:
        require(token in header, f"expression_events.h missing {token}", errors)
    for token in [
        "COMP_DIAG_EVT_WAKE_WORD_DETECTED",
        "COMP_DIAG_EVT_SPEAKER_PROMPT",
        "COMP_DIAG_EVT_MEETING_FINALIZE",
        "COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED",
        "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
        "COMP_DIAG_EVT_ERRORS_FAULT",
        "COMP_DIAG_EVENT_SOURCE(event_code) == (uint8_t)COMP_DIAG_SRC_EPAPER",
        "severity >= COMP_DIAG_SEV_ERROR",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_AUDIO",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT",
        "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED",
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER",
        "blocker_bitmap != 0u",
    ]:
        require(token in source, f"expression_events.c missing {token}", errors)
    for forbidden in ["HAL_", "GPIO", "QSPI", "stm32", "STMWPAN", "UTIL_SEQ"]:
        require(
            forbidden.lower() not in (header + source).lower(),
            f"expression events must stay platform-free: {forbidden}",
            errors,
        )


def check_panel_adapter(errors: list[str]) -> None:
    header = read(PANEL_HEADER)
    source = read(PANEL_SOURCE)
    for token in [
        "COMP_EPAPER_PANEL_RESULT_OK",
        "COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL",
        "COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN",
        "comp_epaper_panel_refresh_fn_t",
        "comp_epaper_panel_adapter_init_dry_run",
        "comp_epaper_panel_adapter_refresh_card",
        "comp_epaper_panel_adapter_render_state",
        "comp_epaper_panel_adapter_status_error",
        "comp_epaper_panel_adapter_snapshot_t",
        "comp_epaper_panel_adapter_snapshot",
    ]:
        require(token in header, f"panel_adapter.h missing {token}", errors)
    for token in [
        ".hardware_present = false",
        ".controller_known = false",
        ".refresh = NULL",
        ".context = NULL",
        "COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL",
        "adapter->config.refresh == NULL",
        "adapter->config.refresh(adapter->config.context",
        "COMP_EPAPER_RENDER_STATE_FAILED",
        "COMP_EPAPER_RENDER_STATE_RENDERED",
        "adapter->last_result = result",
        "out_snapshot->attempted_count = adapter->attempted_count",
    ]:
        require(token in source, f"panel_adapter.c missing {token}", errors)
    for forbidden in ["HAL_", "stm32", "STMWPAN", "UTIL_SEQ"]:
        require(forbidden.lower() not in (header + source).lower(), f"panel adapter contract must stay platform-free for now: {forbidden}", errors)


def check_panel_target_stm32wb(errors: list[str]) -> None:
    header = read(PANEL_TARGET_STM32WB_HEADER)
    source = read(PANEL_TARGET_STM32WB_SOURCE)
    for token in [
        '#include "panel_adapter.h"',
        "companion_epaper_panel_stm32wb_init",
    ]:
        require(token in header, f"panel_target_stm32wb.h missing {token}", errors)
    for token in [
        '#include "panel_target_stm32wb.h"',
        "void companion_epaper_panel_stm32wb_init",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
    ]:
        require(token in source, f"panel_target_stm32wb.c missing {token}", errors)
    for forbidden in ["HAL_SPI", "HAL_QSPI", "GPIO_PIN_", "BSP_", "EPD_"]:
        require(forbidden not in source, f"WB55 panel target scaffold must not claim transport before hardware evidence: {forbidden}", errors)


def check_screen_runtime(errors: list[str]) -> None:
    header = read(SCREEN_RUNTIME_HEADER)
    source = read(SCREEN_RUNTIME_SOURCE)
    for token in [
        '#include "display_queue.h"',
        '#include "expression_state.h"',
        '#include "panel_adapter.h"',
        "comp_epaper_screen_runtime_snapshot_t",
        "comp_epaper_expression_state_snapshot_t expression;",
        "comp_epaper_display_queue_snapshot_t display_queue;",
        "comp_epaper_panel_adapter_snapshot_t panel;",
        "comp_epaper_screen_runtime_snapshot",
    ]:
        require(token in header, f"screen_runtime.h missing {token}", errors)
    for token in [
        "void comp_epaper_screen_runtime_snapshot",
        "memset(out_snapshot, 0, sizeof(*out_snapshot));",
        "comp_epaper_expression_state_snapshot(expression_state",
        "comp_epaper_display_queue_snapshot(display_queue",
        "comp_epaper_panel_adapter_snapshot(panel_adapter",
    ]:
        require(token in source, f"screen_runtime.c missing {token}", errors)
    for forbidden in ["HAL_", "GPIO", "SPI", "QSPI", "stm32", "STMWPAN", "UTIL_SEQ", "CPU2", "FUS", "IPCC", "HSEM"]:
        require(
            forbidden.lower() not in (header + source).lower(),
            f"screen runtime must stay platform-free: {forbidden}",
            errors,
        )


def check_wb55_integration(errors: list[str]) -> None:
    app_ble = read(APP_BLE)
    app_conf = read(APP_CONF)
    makefile = read(MAKEFILE)

    for token in [
        '#include "display_queue.h"',
        '#include "expression_events.h"',
        '#include "expression_state.h"',
        '#include "panel_adapter.h"',
        '#include "panel_target_stm32wb.h"',
        '#include "screen_runtime.h"',
        '#include "diag_log.h"',
        "static comp_epaper_display_queue_t s_companion_display_queue;",
        "static comp_epaper_expression_state_t s_companion_expression_state;",
        "static comp_epaper_panel_adapter_t s_companion_panel_adapter;",
        "comp_epaper_screen_runtime_snapshot_t runtime_stats",
        "comp_epaper_screen_runtime_snapshot(&s_companion_expression_state",
        "runtime_stats.panel.attempted_count",
        "runtime_stats.display_queue.pending_count",
        "comp_epaper_display_queue_init(&s_companion_display_queue)",
        "comp_epaper_display_queue_discard_kind(",
        "COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_display_queue_set_resource_revision(",
        "queue_generation revision=",
        "display_result id=%lu kind=%u resource_revision=%lu active_revision=%lu coherent_generation=%u",
        "generation_switches=%lu last_stale_discarded=%lu",
        "discarded_pet_expression_frames",
        "comp_epaper_expression_state_init(&s_companion_expression_state)",
        "companion_epaper_panel_stm32wb_init(",
        "s_companion_expression_asset_source",
        "UTIL_SEQ_RegTask(1 << CFG_TASK_COMPANION_DISPLAY_ID",
        "HW_TS_Create(CFG_TIM_PROC_ID_ISR",
        "Companion_Display_CreateExpressionTickTimer()",
        "Companion_Display_TickTimerElapsed",
        "Companion_Display_ProcessExpressionTick",
        "Companion_Display_ScheduleExpressionTick",
        "comp_epaper_expression_state_snapshot_t expression_stats",
        "comp_epaper_expression_state_snapshot(&s_companion_expression_state",
        "expression_stats.auto_recover_ms",
        "Companion_Display_EnqueueExpressionDecision",
        "CFG_TS_TICK_VAL",
        "Companion_Display_EnqueueExpressionSignal(COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE",
        "static void Companion_Display_Task(void)",
        "static void Companion_Display_EnqueueExpressionSignal",
        "static void Companion_Display_EnqueueExpressionEvent",
        "Companion_Display_ApplyBatteryExpressionHint",
        "Companion_Gatt_PublishBatteryCharge(false)",
        "Companion_Gatt_PublishBatteryCharge(true)",
        "COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE",
        "COMPANION_SETTINGS_FLAG_QUIET_HOURS_ACTIVE",
        "Companion_Settings_WantsSleepy",
        "Companion_Display_ApplySettingsExpressionHint",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "static void Companion_Diag_RecordAndEnqueueExpression",
        "comp_epaper_display_queue_snapshot_t queue_stats",
        "comp_epaper_display_queue_snapshot(&s_companion_display_queue, &queue_stats)",
        "queue_stats.pending_count",
        "queue_stats.dropped_count",
        "COMP_DIAG_EVT_EPAPER_RENDER_REQUEST",
        "COMP_DIAG_EVT_EPAPER_UPDATE_RESULT",
        "COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT",
        "Companion_Display_RecordRuntimeSnapshot",
    ]:
        require(token in app_ble, f"app_ble.c missing display queue integration token {token}", errors)

    card_write = slice_between(
        app_ble,
        "case COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE:",
        "case COMPANION_GATT_CHAR_RECORDING_CONTROL:",
    )
    require(card_write, "could not isolate CardWrite handler", errors)
    if card_write:
        require("comp_epaper_display_queue_enqueue_card_write" in card_write, "CardWrite handler does not enqueue display work", errors)
        require("UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID" in card_write, "CardWrite handler does not schedule display task", errors)
        require("comp_epaper_display_queue_dequeue" not in card_write, "CardWrite handler must not dequeue/process display work", errors)
        for forbidden in ["HAL_SPI", "HAL_QSPI", "BSP_", "EPD_", "busy-pin", "refresh waveform"]:
            require(forbidden not in card_write, f"CardWrite handler must not block on display IO: {forbidden}", errors)

    display_task = slice_between(
        app_ble,
        "static void Companion_Display_Task(void)\n{",
        "static void Companion_Gatt_HandleEvent",
    )
    require(display_task, "could not isolate Companion_Display_Task", errors)
    if display_task:
        require("Companion_Display_ProcessExpressionTick()" in display_task, "display task must process expression tick before dequeue", errors)
        require("comp_epaper_display_queue_dequeue" in display_task, "display task must dequeue display work", errors)
        require("comp_epaper_panel_adapter_refresh_card" in display_task, "display task must call panel adapter", errors)
        require("comp_epaper_panel_adapter_render_state" in display_task, "display task must map panel result to render_state", errors)
        require("comp_epaper_panel_adapter_status_error" in display_task, "display task must map panel result to last_error", errors)
        require("comp_epaper_screen_runtime_snapshot" in display_task, "display task must collect screen runtime telemetry snapshot", errors)
        require("runtime_stats.panel.attempted_count" in display_task, "display task must log panel adapter attempts from runtime snapshot", errors)
        require("runtime_stats.display_queue.pending_count" in display_task, "display task must reschedule from runtime queue snapshot", errors)
        require("COMP_DIAG_EVT_EPAPER_UPDATE_RESULT" in display_task, "display task must log update_result", errors)
        require("Companion_Display_RecordRuntimeSnapshot(&runtime_stats)" in display_task, "display task must record runtime diagnostics from aggregate snapshot", errors)

    expression_path = slice_between(
        app_ble,
        "static void Companion_Display_CreateExpressionTickTimer",
        "static void Companion_Gatt_HandleEvent",
    )
    require(expression_path, "could not isolate expression enqueue/tick helpers", errors)
    if expression_path:
        require("HW_TS_Create(CFG_TIM_PROC_ID_ISR" in expression_path, "expression path must create a WB55 timer-server hook", errors)
        require("HW_TS_Start(s_companion_expression_tick_timer_id" in expression_path, "expression path must start auto-recovery timer", errors)
        require("HW_TS_Stop(s_companion_expression_tick_timer_id" in expression_path, "expression path must stop/restart auto-recovery timer", errors)
        require("UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID" in expression_path, "timer callback must schedule display task", errors)
        require("comp_epaper_expression_state_tick" in expression_path, "expression path must feed elapsed time into portable state tick", errors)
        require("comp_epaper_expression_state_snapshot" in expression_path, "expression scheduler must read portable state snapshot", errors)
        require("expression_stats.visible_age_ms" in expression_path, "expression scheduler must use snapshot visible age", errors)
        require("comp_epaper_expression_state_apply_signal" in expression_path, "expression helper must apply portable expression state", errors)
        require("comp_epaper_display_queue_enqueue_expression" in expression_path, "expression helper must enqueue expression display work", errors)
        require("s_companion_expression_state = *previous_state" in expression_path, "expression helper must roll back state when enqueue fails", errors)
        require("suppressed_duplicate_count" in expression_path, "duplicate suppression must reschedule expression timer", errors)
        for forbidden in ["HAL_SPI", "HAL_QSPI", "BSP_", "EPD_", "busy-pin", "refresh waveform"]:
            require(forbidden not in expression_path, f"expression helper must not block on display IO: {forbidden}", errors)

    settings_write = slice_between(
        app_ble,
        "case COMPANION_GATT_CHAR_SETTINGS:",
        "case COMPANION_GATT_CHAR_BLE_NAME_CONFIG:",
    )
    require(settings_write, "could not isolate Settings handler", errors)
    if settings_write:
        require(
            "Companion_Display_ApplySettingsExpressionHint(&s_companion_gatt_settings)" in settings_write,
            "Settings handler must feed display settings expression hint",
            errors,
        )
        require(
            "comp_epaper_display_queue_dequeue" not in settings_write,
            "Settings handler must not process display queue work inline",
            errors,
        )

    require(
        "comp_epaper_expression_signal_from_diag_event" in app_ble,
        "app_ble.c must use portable diagnostic-event expression mapper",
        errors,
    )
    require(
        "comp_epaper_expression_signal_from_device_status" in app_ble,
        "app_ble.c must use portable DeviceStatus expression mapper",
        errors,
    )
    require(
        "comp_epaper_expression_signal_from_ota_readiness" in app_ble,
        "app_ble.c must use portable OTA readiness expression mapper",
        errors,
    )
    for mapper in [
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
    ]:
        require(mapper in app_ble, f"app_ble.c must use portable interaction status expression mapper {mapper}", errors)
    require(
        "Companion_Diag_RecordAndEnqueueExpression" in app_ble,
        "app_ble.c must expose record-and-enqueue helper for V1 product events",
        errors,
    )
    for token in [
        "COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST",
        "COMP_DIAG_EVT_RECORDING_FSM_STOP_REQUEST",
        "COMP_DIAG_EVT_RECORDING_FSM_CANCEL_REQUEST",
        "COMP_DIAG_EVT_MEETING_START",
        "COMP_DIAG_EVT_MEETING_FINALIZE",
        "COMP_DIAG_EVT_SPEAKER_PROMPT",
        "COMP_DIAG_EVT_WAKE_WORD_ARMED",
        "COMP_DIAG_EVT_WAKE_WORD_DISABLED",
        "COMP_DIAG_EVT_WAKE_WORD_DETECTED",
        "COMP_DIAG_EVT_WAKE_WORD_REJECTED",
    ]:
        require(token in app_ble, f"app_ble.c missing firmware expression event {token}", errors)

    require("CFG_TASK_COMPANION_DISPLAY_ID" in app_conf, "app_conf.h missing display task id", errors)
    require("CFG_LAST_TASK_ID_WITH_HCICMD (CFG_TASK_COMPANION_DISPLAY_ID + 1)" in app_conf, "app_conf.h last task id does not include display task", errors)
    require("$(ROOT)/app/companion_pendant/epaper" in makefile, "Makefile missing e-paper include path", errors)
    require("$(ROOT)/app/companion_pendant/epaper/display_queue.c" in makefile, "Makefile missing display_queue.c", errors)
    require("$(ROOT)/app/companion_pendant/epaper/expression_events.c" in makefile, "Makefile missing expression_events.c", errors)
    require("$(ROOT)/app/companion_pendant/epaper/expression_state.c" in makefile, "Makefile missing expression_state.c", errors)
    require("$(ROOT)/app/companion_pendant/epaper/panel_adapter.c" in makefile, "Makefile missing panel_adapter.c", errors)
    require("$(ROOT)/app/companion_pendant/epaper/panel_target_stm32wb.c" in makefile, "Makefile missing panel_target_stm32wb.c", errors)
    require("$(ROOT)/app/companion_pendant/epaper/screen_runtime.c" in makefile, "Makefile missing screen_runtime.c", errors)


def check_docs(errors: list[str]) -> None:
    readme = read(README)
    plan = read(PLAN_DOC)
    compact_readme = " ".join(readme.split())
    compact_plan = " ".join(plan.split())
    for token in ["expression_events", "expression_state", "display_queue", "panel adapter", "panel_target_stm32wb", "screen runtime", "runtime diagnostics", "enqueue display work", "should not block on panel IO"]:
        require(token in compact_readme, f"e-paper README missing display queue anchor: {token}", errors)
    for token in ["Firmware ExpressionV1 state path", "WB55 display queue boundary", "Display queue fault paths", "WB55 device status expression hint", "WB55 interaction status expression hint", "WB55 battery expression hint", "WB55 OTA readiness expression hint", "WB55 settings expression hint", "panel adapter", "Screen runtime snapshot", "Screen runtime diagnostics", "Companion_Display_Task", "verify_display_queue_static.py"]:
        require(token in compact_plan, f"screen expression doc missing display queue anchor: {token}", errors)


def check_third_party_clean(errors: list[str]) -> None:
    changed = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB").strip()
    require(not changed, f"third_party/STM32CubeWB modified: {changed}", errors)


def main() -> int:
    errors: list[str] = []
    for path in [
        QUEUE_HEADER,
        QUEUE_SOURCE,
        EXPRESSION_EVENTS_HEADER,
        EXPRESSION_EVENTS_SOURCE,
        EXPRESSION_HEADER,
        EXPRESSION_SOURCE,
        PANEL_HEADER,
        PANEL_SOURCE,
        PANEL_TARGET_STM32WB_HEADER,
        PANEL_TARGET_STM32WB_SOURCE,
        SCREEN_RUNTIME_HEADER,
        SCREEN_RUNTIME_SOURCE,
        APP_BLE,
        APP_CONF,
        MAKEFILE,
        README,
        PLAN_DOC,
    ]:
        require(path.exists(), f"missing required path {path.relative_to(REPO_ROOT)}", errors)
    if not errors:
        check_queue_module(errors)
        check_expression_events(errors)
        check_expression_state(errors)
        check_panel_adapter(errors)
        check_panel_target_stm32wb(errors)
        check_screen_runtime(errors)
        check_wb55_integration(errors)
        check_docs(errors)
        check_third_party_clean(errors)

    if errors:
        print("FAIL: Companion display queue static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion WB55 display queue boundary verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
