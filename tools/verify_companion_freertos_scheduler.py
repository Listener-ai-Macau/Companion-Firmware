#!/usr/bin/env python3
"""Guard the Companion FreeRTOS scheduling and ownership contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
CONFIG = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/FreeRTOSConfig.h"
WATCHDOG_C = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/companion_rtos_watchdog.c"
)
WATCHDOG_H = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/companion_rtos_watchdog.h"
)
APP_ENTRY = (
    ROOT
    / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/"
    "Applications/BLE/BLE_p2pServer/Core/Src/app_entry.c"
)
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
OUTPUT = (
    ROOT
    / ".cache/validation/comp-req-775-pointer-follow-root-fix"
    / "rtos-input-owner/FREERTOS_SCHEDULER_READY.json"
)


def function_body(source: str, signature: str) -> str:
    search_from = 0
    while True:
        start = source.find(signature, search_from)
        if start < 0:
            return ""
        brace = source.find("{", start)
        semicolon = source.find(";", start)
        if brace >= 0 and (semicolon < 0 or brace < semicolon):
            break
        search_from = start + len(signature)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return ""


def all_tokens(source: str, *tokens: str) -> bool:
    return all(token in source for token in tokens)


def main() -> int:
    main_source = MAIN.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    watchdog_c = WATCHDOG_C.read_text(encoding="utf-8")
    watchdog_h = WATCHDOG_H.read_text(encoding="utf-8")
    app_entry = APP_ENTRY.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")

    seq_idle = function_body(app_entry, "void UTIL_SEQ_Idle(void)")
    hal_delay = function_body(app_entry, "void HAL_Delay(uint32_t Delay)")
    input_task = function_body(main_source, "Companion_Rtos_InputTask(")
    display_wait = function_body(
        main_source, "capture_touch_during_display_wait("
    )
    touch_poll = function_body(main_source, "poll_touch_debug(")
    touch_irq = function_body(main_source, "EXTI9_5_IRQHandler(")
    storage_task = function_body(main_source, "Companion_Rtos_StorageTask(")
    recording_prepare = function_body(
        main_source, "start_user_recording_async("
    )
    recording_complete = function_body(
        main_source, "Companion_Rtos_ServiceRecordingPrepare("
    )
    recording_toggle = function_body(main_source, "toggle_touch_recording(")
    rec_task = function_body(main_source, "Companion_Rtos_RecTask(")
    recording_stop = function_body(
        main_source, "Companion_Rtos_ServiceRecordingStop("
    )

    checks = {
        "freertos_build_is_explicit": (
            "COMPANION_USE_FREERTOS ?= 0" in makefile
            and "-DCOMPANION_USE_FREERTOS=1" in makefile
        ),
        "kernel_is_preemptive_with_stack_checks": all_tokens(
            config,
            "#define configUSE_PREEMPTION                    1",
            "#define configCHECK_FOR_STACK_OVERFLOW          2",
            "#define configUSE_TICKLESS_IDLE                 0",
        ),
        "cube_sequencer_cannot_suspend_scheduler_tick": (
            "COMPANION_USE_FREERTOS" in seq_idle
            and seq_idle.find("return;") < seq_idle.find("UTIL_LPM_EnterLowPower")
        ),
        "task_hal_delay_yields_instead_of_wfi": all_tokens(
            hal_delay,
            "xTaskGetSchedulerState() == taskSCHEDULER_RUNNING",
            "__get_IPSR() == 0U",
            "__get_PRIMASK() == 0U",
            "__get_BASEPRI() == 0U",
            "vTaskDelay(ticks);",
        )
        and hal_delay.find("vTaskDelay(ticks);") < hal_delay.find("__WFI();"),
        "product_task_priority_order_is_fixed": all_tokens(
            main_source,
            '"rec",\n                    4864,\n                    NULL,\n                    5,',
            '"input",\n                    320,\n                    NULL,\n                    6,',
            '"svc",\n                    1280,\n                    NULL,\n                    3,',
            '"flash",\n                    768,\n                    NULL,\n                    2,',
        ),
        "input_is_single_ft6336_owner": all_tokens(
            input_task,
            "companion_touch_ft6336_stm32wb_poll(&s_touch, &sample)",
            "buffer_touch_sample_during_panel_wait(&sample, now_ms)",
            "TOUCH_RTOS_COALESCE_MS",
            "COMPANION_WATCHDOG_TASK_INPUT",
        ),
        "display_busy_never_reads_touch_i2c_under_rtos": (
            "COMPANION_USE_FREERTOS" in display_wait
            and display_wait.find("return;")
            < display_wait.find("companion_touch_ft6336_stm32wb_poll(")
        ),
        "svc_only_replays_timestamped_pointer_queue_under_rtos": (
            "COMPANION_USE_FREERTOS" in touch_poll
            and "process_touch_debug_sample(&entry.sample" in touch_poll
            and "entry.timestamp_ms" in touch_poll
            and touch_poll.find("return;")
            < touch_poll.find("companion_touch_ft6336_stm32wb_poll(")
        ),
        "recording_double_tap_preempts_historical_touch_drain": (
            "comp_touch_recording_boundary_pending(" in touch_poll
            and "&s_touch_recording_boundary) != 0u" in touch_poll
            and "break;" in touch_poll
            and touch_poll.find("process_touch_debug_sample(&entry.sample")
            < touch_poll.find("comp_touch_recording_boundary_pending(")
            < touch_poll.find("break;")
            and main_source.find("poll_touch_debug();")
            < main_source.find("process_deferred_touch_runtime_action();")
        ),
        "recording_exit_rechecks_at_panel_safe_boundary": (
            "if (Companion_Rtos_ServiceDeferred()) {\n"
            "                MX_APPE_Process();\n"
            "            }" in main_source
            and main_source.find("MX_APPE_Process();\n"
                                 "            /* A second recording double tap")
            < main_source.find("if (Companion_Rtos_ServiceDeferred()) {")
        ),
        "recording_hot_loop_has_bounded_service_window": all_tokens(
            rec_task,
            "Companion_Recording_ServiceHotTick();",
            "vTaskDelay(pdMS_TO_TICKS(1u));",
        )
        and "if (!s_recording_stop_request.pending)" in rec_task,
        "recording_stop_quiesces_capture_before_visual_commit": all_tokens(
            recording_stop,
            "request.capture_quiesced",
            "pdm_raw_dma_stop_if_started()",
            "s_recording_stop_request.capture_quiesced = true",
            "stage=capture_quiesced",
            "before_visual=1",
            "Companion_Screen_RecordingStopFeedbackResolved",
        ),
        "touch_exti_only_wakes_input_task": all_tokens(
            touch_irq,
            "s_touch_irq_count++",
            "vTaskNotifyGiveFromISR(s_companion_input_task",
            "portYIELD_FROM_ISR(higher_priority_task_woken)",
        ),
        "touch_exti_priority_allows_freertos_isr_api": (
            "HAL_NVIC_SetPriority(EXTI9_5_IRQn, 8, 0)" in main_source
            and "#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY    5"
            in config
        ),
        "watchdog_covers_every_product_task": all_tokens(
            watchdog_h,
            "COMPANION_WATCHDOG_TASK_SVC = 0",
            "COMPANION_WATCHDOG_TASK_REC = 1",
            "COMPANION_WATCHDOG_TASK_STORAGE = 2",
            "COMPANION_WATCHDOG_TASK_INPUT = 3",
        )
        and all_tokens(
            watchdog_c,
            "COMPANION_WATCHDOG_PROGRESS_DEADLINE_MS 3000u",
            "COMPANION_WATCHDOG_IWDG_RELOAD_8S 999u",
            "companion_watchdog_save_failure(stalled_mask, now_ms)",
            'printf("[watchdog] feed=stopped',
            "IWDG->KR = 0xAAAAu",
        ),
        "touch_recording_prepare_never_blocks_svc": all_tokens(
            recording_prepare,
            "COMP_RECORDING_STATE_PENDING_START",
            "COMPANION_STORAGE_JOB_RECORDING_PREPARE",
            "xQueueSend(s_companion_storage_queue, &job, 0u)",
        )
        and "xTaskNotifyWait" not in recording_prepare
        and "portMAX_DELAY" not in recording_prepare,
        "flash_completion_wakes_rec_not_svc": all_tokens(
            storage_task,
            "job.kind == COMPANION_STORAGE_JOB_RECORDING_PREPARE",
            "s_recording_prepare.completed = true",
            "xTaskNotifyGive(s_companion_rec_task)",
        ),
        "rec_owns_pending_to_capture_ready_transition": all_tokens(
            recording_complete,
            "COMP_RECORDING_STATE_PENDING_START",
            "recording_flash_activate_capture(prepare.max_seconds)",
            "comp_recording_fsm_set_capture_ready(&s_recording_fsm, true)",
            "start_recording(prepare.source, prepare.reason)",
        ),
        "second_double_tap_can_cancel_pending_recording": all_tokens(
            recording_toggle,
            "COMP_RECORDING_STATE_PENDING_START",
            "COMP_RECORDING_EVENT_TOGGLE_REQUEST",
            "cancel_async_prepare",
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.freertos_scheduler.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest().upper()
            for path in (MAIN, CONFIG, WATCHDOG_C, WATCHDOG_H, APP_ENTRY, MAKEFILE)
        },
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
