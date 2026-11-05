#!/usr/bin/env python3
"""Verify the COMP-REQ-775 display runtime ownership architecture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
QUEUE_HEADER = REPO / "app/companion_pendant/epaper/display_queue.h"
QUEUE_SOURCE = REPO / "app/companion_pendant/epaper/display_queue.c"
QUEUE_TEST = REPO / "app/companion_pendant/epaper/tests/test_motion_display_queue.c"
APP_BLE = REPO / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
MAIN = REPO / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
WATCHDOG = (
    REPO
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/companion_rtos_watchdog.c"
)
PANEL = REPO / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
ARCHITECTURE = REPO / "docs/companion_display_runtime_architecture.md"
PLAYBOOK = REPO / "docs/companion_epaper_refresh_playbook.md"
MUTATION_TEST = REPO / "tools/test_display_transaction_arbiter_host.ps1"
COVERAGE_HEADER = REPO / "app/companion_pendant/epaper/refresh_coverage.h"
COVERAGE_TEST = REPO / "app/companion_pendant/epaper/tests/test_refresh_coverage.c"
COVERAGE_RUNNER = REPO / "tools/test_refresh_coverage_host.ps1"
OVERLAY_SCHEDULER_HEADER = (
    REPO / "app/companion_pendant/epaper/overlay_commit_scheduler.h"
)
OVERLAY_SCHEDULER_SOURCE = (
    REPO / "app/companion_pendant/epaper/overlay_commit_scheduler.c"
)
OVERLAY_SCHEDULER_TEST = (
    REPO / "app/companion_pendant/epaper/tests/test_overlay_commit_scheduler.c"
)
OVERLAY_SCHEDULER_RUNNER = REPO / "tools/test_overlay_commit_scheduler_host.ps1"
TRACK_ARBITER_HEADER = REPO / "app/companion_pendant/epaper/display_track_arbiter.h"
TRACK_ARBITER_SOURCE = REPO / "app/companion_pendant/epaper/display_track_arbiter.c"
TRACK_ARBITER_TEST = (
    REPO / "app/companion_pendant/epaper/tests/test_display_track_arbiter.c"
)
TRACK_ARBITER_RUNNER = REPO / "tools/test_display_track_arbiter_host.ps1"
COMPOSITION_HEADER = REPO / "app/companion_pendant/epaper/screen_composition.h"
COMPOSITION_SOURCE = REPO / "app/companion_pendant/epaper/screen_composition.c"
COMPOSITION_TEST = (
    REPO / "app/companion_pendant/epaper/tests/test_screen_composition_journey.c"
)
COMPOSITION_RUNNER = REPO / "tools/test_screen_composition_journey_host.ps1"
SOURCE_PACK_GENERATOR = (
    REPO / "tools/faraday_upper_art/generate_comp_req_628_source_pack.mjs"
)
INTERACTION_EXPORTER = (
    REPO / "tools/faraday_upper_art/export_comp_req_775_browser_interaction_contract.mjs"
)
INTERACTION_GENERATOR = (
    REPO / "tools/faraday_upper_art/generate_browser_interaction_contract.py"
)
PRODUCT_BUILD_PREPARER = (
    REPO / "tools/faraday_upper_art/build_comp_req_775_firmware.py"
)
OUTPUT = (
    REPO
    / ".cache/validation/comp-req-775-incremental-sync/"
    "DISPLAY_RUNTIME_ARCHITECTURE_READY.json"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def contains_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


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
    paths = (
        QUEUE_HEADER,
        QUEUE_SOURCE,
        QUEUE_TEST,
        APP_BLE,
        MAIN,
        WATCHDOG,
        PANEL,
        ARCHITECTURE,
        PLAYBOOK,
        MUTATION_TEST,
        COVERAGE_HEADER,
        COVERAGE_TEST,
        COVERAGE_RUNNER,
        OVERLAY_SCHEDULER_HEADER,
        OVERLAY_SCHEDULER_SOURCE,
        OVERLAY_SCHEDULER_TEST,
        OVERLAY_SCHEDULER_RUNNER,
        TRACK_ARBITER_HEADER,
        TRACK_ARBITER_SOURCE,
        TRACK_ARBITER_TEST,
        TRACK_ARBITER_RUNNER,
        COMPOSITION_HEADER,
        COMPOSITION_SOURCE,
        COMPOSITION_TEST,
        COMPOSITION_RUNNER,
        SOURCE_PACK_GENERATOR,
        INTERACTION_EXPORTER,
    )
    missing = [str(path.relative_to(REPO)) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError("missing architecture inputs: " + ", ".join(missing))

    header = read(QUEUE_HEADER)
    queue = read(QUEUE_SOURCE)
    queue_test = read(QUEUE_TEST)
    app_ble = read(APP_BLE)
    main_source = read(MAIN)
    watchdog_source = read(WATCHDOG)
    panel = read(PANEL)
    blink_compose = function_body(
        panel, "static bool ssd1681_compose_natural_blink("
    )
    cached_mode2 = function_body(
        panel, "static bool ssd1681_cached_mode2_diff_internal("
    )
    blink_open_sync_marker = (
        "if (ok && natural_blink_frame && !natural_blink_closed)"
    )
    blink_open_sync_tail = ""
    if blink_open_sync_marker in cached_mode2:
        blink_open_sync_tail = cached_mode2.split(
            blink_open_sync_marker, 1
        )[1].split("ssd1681_comp_req_611_report_window", 1)[0]
    fast_boundary = function_body(
        panel, "static bool ssd1681_lifecycle_mode2_fast_full_activation("
    )
    hardfault_handler = function_body(main_source, "void HardFault_Handler(void)")
    daily_signal_body = function_body(
        app_ble, "bool Companion_Screen_DailyExpressionSignal("
    )
    recording_start_branch = daily_signal_body.split(
        "if (signal == COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START)", 1
    )[1].split(
        "else if (signal == COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP", 1
    )[0]
    fast_visible_stage = fast_boundary.split("if (planes_written)", 1)[0]
    architecture = read(ARCHITECTURE)
    playbook = read(PLAYBOOK)
    mutation = read(MUTATION_TEST)
    coverage_header = read(COVERAGE_HEADER)
    coverage_test = read(COVERAGE_TEST)
    overlay_header = read(OVERLAY_SCHEDULER_HEADER)
    overlay_source = read(OVERLAY_SCHEDULER_SOURCE)
    overlay_test = read(OVERLAY_SCHEDULER_TEST)
    overlay_runner = read(OVERLAY_SCHEDULER_RUNNER)
    track_arbiter = read(TRACK_ARBITER_HEADER) + read(TRACK_ARBITER_SOURCE)
    track_arbiter_test = read(TRACK_ARBITER_TEST)
    track_arbiter_runner = read(TRACK_ARBITER_RUNNER)
    composition_header = read(COMPOSITION_HEADER)
    composition_source = read(COMPOSITION_SOURCE)
    composition_test = read(COMPOSITION_TEST)
    composition_runner = read(COMPOSITION_RUNNER)
    source_pack_generator = read(SOURCE_PACK_GENERATOR)
    interaction_exporter = read(INTERACTION_EXPORTER)
    interaction_generator = read(INTERACTION_GENERATOR)
    product_build_preparer = read(PRODUCT_BUILD_PREPARER)

    checks = {
        "product_build_exports_live_browser_interaction_contract": (
            'str(INTERACTION_CONTRACT_EXPORTER)' in product_build_preparer
            and 'str(interaction_export)' in product_build_preparer
            and 'relative(BROWSER_PAGE)' in product_build_preparer
            and 'FROZEN_INTERACTION_CONTRACT' not in product_build_preparer
            and '!= [24, 32, 40]' in product_build_preparer
        ),
        "generation_activation_can_transition_false_to_ready": (
            "s_companion_ui_asset_generation_ready =\n"
            "          comp_emote_asset_pack_set_frame_override(" in app_ble
            and "s_companion_ui_asset_generation_ready &&\n"
            "          comp_emote_asset_pack_set_frame_override(" not in app_ble
        ),
        "source_timing_validation_is_not_interactive_scheduler": (
            "duration_ms =\n"
            "            COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_CADENCE_MS;"
            not in app_ble
            and "companion_browser_cemp_function_clip_timings[timing_index]"
            in app_ble
            and "comp_epaper_overlay_commit_scheduler_complete" in app_ble
        ),
        "automatic_daily_starts_from_authored_life_clip": (
            "if (!automatic_daily &&\n"
            "      !comp_emote_player_play_now_name(" in app_ble
            and "Companion_Display_EnterDailyMotion(HAL_GetTick());" in app_ble
            and "Companion_Display_ProcessDueTracks(HAL_GetTick(), refresh_mode);"
            in app_ble
        ),
        "state_dwell_is_not_frame_transport_cadence": (
            "s_companion_screen_asset_frames[override_frame_index].duration_ms !=\n"
            "        generation_entry.duration_ms" not in app_ble
            and "s_companion_screen_asset_frames[unique_frame_index].duration_ms !=\n"
            "      generation_entry.duration_ms" not in app_ble
            and "dwell_commits" in app_ble
        ),
        "four_ownership_layers_are_documented": contains_all(
            architecture,
            (
                "browser page + generated interaction/CEMP contracts",
                "target-state producers",
                "display_queue transaction arbiter (the only ordering owner)",
                "panel adapter + SSD1681 driver (the only physical refresh owner)",
            ),
        ),
        "boundary_modes_are_centralized": contains_all(
            queue,
            (
                "comp_epaper_refresh_is_boundary",
                "COMP_EPAPER_REFRESH_MAINTENANCE",
                "COMP_EPAPER_REFRESH_VISIBLE_FULL",
            ),
        ),
        "pending_and_inflight_boundaries_own_display": contains_all(
            header + queue,
            (
                "boundary_in_flight_request_id",
                "comp_epaper_queue_has_pending_boundary",
                "comp_epaper_display_queue_boundary_owned",
                "COMP_EPAPER_DISPLAY_QUEUE_BOUNDARY_OWNS_DISPLAY",
            ),
        ),
        "boundary_discards_stale_ordinary_work": (
            "if (boundary) {\n        (void)comp_epaper_queue_discard_ordinary(queue);"
            in queue
        ),
        "ordinary_work_is_rejected_during_boundary": (
            "else if (comp_epaper_display_queue_boundary_owned(queue))"
            in queue
        ),
        "feature_discard_preserves_boundaries": queue.count(
            "comp_epaper_display_request_is_boundary(source)"
        ) >= 2,
        "recording_events_discard_only_explicit_stale_classes": (
            "comp_epaper_display_class_t" in header
            and "comp_epaper_display_queue_discard_display_class" in queue
            and "COMP_EPAPER_DISPLAY_CLASS_TOUCH" in app_ble
            and "COMP_EPAPER_DISPLAY_CLASS_RECORDING" in app_ble
            and "COMP_EPAPER_DISPLAY_CLASS_ACCESSORY" in app_ble
            and "Pending ordinary frames carry an explicit base, touch, accessory, or"
            in architecture
        ),
        "matching_panel_completion_releases_owner": contains_all(
            queue + app_ble,
            (
                "comp_epaper_display_queue_complete",
                "queue->boundary_in_flight_request_id != request_id",
                "request.request_id",
            ),
        ),
        "generation_switch_clears_obsolete_owner": (
            "queue->boundary_in_flight_request_id = 0u;" in queue
        ),
        "ordinary_product_frames_use_source_driven_stable_coverage": (
            "ssd1681_product_source_complete_window(" in panel
            and "&window, &coverage_candidate, &window" in panel
            and "coverage_window" not in panel
            and "comp_epaper_refresh_coverage_expand(" in panel
            and "s_ordinary_refresh_coverage = coverage_candidate;" in panel
            and contains_all(
                coverage_header,
                (
                    "comp_epaper_refresh_coverage_expand",
                    "comp_epaper_refresh_coverage_reset",
                    "expanded->x_start_byte",
                    "expanded->y_end",
                ),
            )
        ),
        "ordinary_and_blink_share_clean_face_physical_track": (
            "ssd1681_write_plane_region(0x24u, s_frame, window)" in panel
            and "window.changed && natural_blink_frame" not in panel
            and "Replay the accepted r37 physical face path" in panel
            and "ssd1681_product_stage_region_excluding(" in panel
            and "if (!natural_blink_frame)" not in panel
            and "functional_delta_windows[functional_delta_count++] =\n"
                "                blink_regions[eye];" not in panel
            and "single-current-plane face track" in architecture
            and "split around the recording and charging functional regions exactly as\n"
                "in r37" in architecture
            and "does not grant blink permission" in architecture
        ),
        "blink_open_normalizes_previous_plane_without_second_activation": (
            "bool natural_blink_closed" in cached_mode2
            and "if (ok && natural_blink_frame && !natural_blink_closed)"
                in cached_mode2
            and "0x26u, s_frame, &sync_regions[index]" in blink_open_sync_tail
            and "ssd1681_command(0x20u)" not in blink_open_sync_tail
            and "if (ok && natural_blink_frame && natural_blink_closed)"
                not in cached_mode2
            and "report->post_sync_command = 0x26u;" in cached_mode2
            and "controller-baseline normalization" in architecture
            and "cannot run after close" in playbook
        ),
        "recording_overlay_uses_exact_delta_inside_safe_bounds": (
            contains_all(
                function_body(panel, "static bool ssd1681_cached_mode2_diff_internal("),
                (
                    "bool recording_overlay_present",
                    "if (window.changed && recording_overlay_only)",
                    "if (recording_overlay_present)",
                    "SSD1681_RECORDING_OVERLAY_WIDTH - 1u",
                    "retain the exact old/new",
                    "ssd1681_native_cached_mode2_movement_activation(",
                ),
            )
            and ".x_start_byte = x_start_byte" not in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            ).split("} else if (window.changed)", 1)[0]
            and "ssd1681_write_plane_region(0x26u, s_frame, &window)" not in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            ).count("ssd1681_native_cached_mode2_movement_activation(") == 1
        ),
        "functional_deltas_reuse_clean_ball_plane_order_only_locally": (
            (
                lambda body: (
                    "0x26u, s_blink_closed_frame, &functional_deltas[index]" in body
                    and "0x24u, s_frame, &functional_deltas[index]" in body
                    and body.count("ssd1681_write_plane_region(0x24u, s_frame, &regions[index])") == 1
                    and body.count("ssd1681_command(0x20u)") == 1
                    and "HAL_Delay(" not in body
                )
            )(
                function_body(
                    panel,
                    "static bool ssd1681_native_cached_mode2_functional_activation(",
                )
            )
            and "if (recording_delta_window.changed)" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "recording_eye_black_reinforce = true;" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "functional_delta_windows[functional_delta_count++] =\n            recording_delta_window;" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "if (charger_delta_window.changed)" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "functional_delta_windows[functional_delta_count++] =\n            charger_delta_window;" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "ssd1681_native_cached_mode2_functional_activation(" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "report->previous_plane_sync = 1u" in function_body(
                panel, "static bool ssd1681_cached_mode2_diff_internal("
            )
            and "ssd1681_write_plane_region(0x26u" not in function_body(
                panel,
                "static bool ssd1681_native_cached_mode2_movement_activation(",
            )
        ),
        "charging_uses_independent_wall_clock": (
            "now_ms = HAL_GetTick();" not in function_body(
                app_ble, "static bool Companion_CompReq775ResolveChargingFrame("
            )
            and "Companion_CompReq775ResolveChargingFrame(\n            arbiter_now_ms,"
                in app_ble
            and "s_companion_comp_req638_charging_cycle_started_ms = HAL_GetTick();"
            in app_ble
            and "synthetic browser motion clock cannot accelerate" in architecture
        ),
        "natural_blink_uses_independent_wall_clock": (
            contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_ProcessDueTracks(\n"
                    "    uint32_t now_ms,\n"
                    "    comp_epaper_refresh_mode_t refresh_mode)\n{",
                ),
                (
                    "const uint32_t blink_now_ms = HAL_GetTick();",
                    "comp_epaper_natural_blink_take_due(\n              &s_companion_blink_scheduler,",
                    "blink_now_ms,",
                ),
            )
            and "comp_epaper_natural_blink_remaining_ms(\n"
                "        &s_companion_blink_scheduler, HAL_GetTick());"
                in function_body(
                    app_ble,
                    "static void Companion_Display_ScheduleExpressionTick(uint32_t now_ms)\n{",
                )
        ),
        "natural_blink_compositor_replays_owner_accepted_cemp_state_pair": (
            contains_all(
                panel + architecture,
                (
                    "SSD1681_BROWSER_BLINK_OPEN_STATE_HASH 0x96C7864Au",
                    "SSD1681_BROWSER_BLINK_CLOSED_STATE_HASH 0xF476300Eu",
                    "ssd1681_blink_bounds_add",
                    "source=r37_cemp_state_pair",
                    "left `42,93..74,137`",
                    "right `125,93..160,139`",
                ),
            )
            and blink_compose.count(
                "comp_epaper_expression_asset_source_copy_state("
            ) == 2
            and "companion_browser_blink_authored_closed_eye_pixels" not in blink_compose
        ),
        "natural_blink_open_owns_next_slot_through_single_tail_arbiter": (
            contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_ServicePostBusyArbiter("
                    "\n    uint32_t completed_ms,\n"
                    "    comp_epaper_display_class_t completed_class)\n{",
                ),
                (
                    "s_companion_post_busy_arbiter_active",
                    "s_companion_post_busy_arbiter_pending",
                    "comp_epaper_display_queue_pending(",
                    "Companion_App_ShouldYieldDisplayForTouch()",
                    "Companion_Display_ServicePublishedTracks(completed_class);",
                ),
            )
            and contains_all(
                function_body(
                    app_ble,
                    "static bool Companion_Display_ServicePublishedTracks(\n"
                    "    comp_epaper_display_class_t completed_class)\n{",
                ),
                (
                    "comp_epaper_display_completion_service(",
                    "COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_TIMER",
                    "COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_RECORDING",
                    "Companion_Display_ProcessExpressionTick();",
                    "Companion_CompReq775TryEmitNextRecordingOverlay();",
                    "Companion_CompReq775RecordingTrackPending()",
                ),
            )
            and "Companion_Display_ProcessDueTracks(" not in function_body(
                app_ble,
                "static void Companion_Display_ServicePostBusyArbiter("
                "\n    uint32_t completed_ms,\n"
                "    comp_epaper_display_class_t completed_class)\n{",
            )
            and function_body(
                app_ble,
                "static void Companion_Display_ServicePostBusyArbiter("
                "\n    uint32_t completed_ms,\n"
                "    comp_epaper_display_class_t completed_class)\n{",
            ).count("while (") == 0
            and function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            ).count("Companion_Display_ServicePostBusyArbiter(") == 1
            and "Companion_Display_DispatchBlinkOpenAfterClosedCommit" not in app_ble
            and "Companion_Display_ScheduleExpressionTick(visible_ms);"
            in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
            and "comp_epaper_natural_blink_complete_open("
            in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
            and contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_ProcessDueTracks(\n"
                    "    uint32_t now_ms,\n"
                    "    comp_epaper_refresh_mode_t refresh_mode)\n{",
                ),
                (
                    "s_companion_blink_scheduler.open_pending",
                    "comp_epaper_natural_blink_take_due(",
                    "Companion_Display_EmitNaturalBlinkFrame(",
                    "s_companion_blink_open_enqueued_ms = HAL_GetTick();",
                ),
            )
            and contains_all(
                function_body(
                    app_ble, "static void Companion_Display_Task(void)\n{"
                ),
                (
                    "[screen-blink] pair closed_request=",
                    "queue_gap_ms=",
                    "closed_to_open_ms=",
                    "closed_control=0x%02X",
                    "open_control=0x%02X",
                ),
            )
            and "COMP_EPAPER_DISPLAY_FLAG_NATURAL_BLINK_FRAME) != 0u;"
            in panel
            and function_body(
                app_ble,
                "static bool Companion_Display_EmitEmoteFrameModeInternal(\n"
                "    comp_epaper_refresh_mode_t refresh_mode,\n"
                "    const comp_epaper_motion_request_t *motion_request,\n"
                "    uint16_t display_flags)\n{",
            ).count(
                "display_flags & COMP_EPAPER_DISPLAY_FLAG_NATURAL_BLINK_FRAME"
            ) >= 1
        ),
        "natural_blink_deadline_is_not_reset_by_transient_home_work": (
            contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_CancelAutomaticMotion(\n"
                    "    comp_epaper_motion_cancel_reason_t reason)\n{",
                ),
                (
                    "COMP_EPAPER_MOTION_CANCEL_TOUCH",
                    "COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY",
                    "preserve_blink_clock",
                    "blink_clock=%s",
                ),
            )
            and contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_EnterDailyMotion(uint32_t now_ms)\n{",
                ),
                (
                    "if (!s_companion_blink_scheduler.awake)",
                    "scheduler=preserved",
                    "comp_epaper_natural_blink_remaining_ms(",
                ),
            )
        ),
        "composed_recording_preserves_static_body_in_one_activation": (
            contains_all(
                panel,
                (
                    "ssd1681_window_from_difference_within(",
                    "ssd1681_native_cached_mode2_multi_region_activation(",
                    "ssd1681_product_stage_region_excluding(",
                    "&recording_delta_window",
                    "native_mode2_source[] = {0xCFu}",
                    "ssd1681_command(0x20u)",
                ),
            )
            and "comp_epaper_refresh_coverage_expand(\n                    &coverage_candidate"
            not in panel
            and function_body(
                panel,
                "static bool ssd1681_native_cached_mode2_multi_region_activation(",
            ).count("ssd1681_command(0x20u)") == 1
            and "static microphone body is preserved" in architecture
        ),
        "charging_region_is_not_redriven_by_recording_or_base": (
            contains_all(
                panel,
                (
                    "SSD1681_CHARGER_OVERLAY_X",
                    "charger_overlay_present",
                    "charger_delta_window =",
                    "excluded[excluded_count++] = charger_bounds;",
                    "functional_delta_windows[functional_delta_count++] =\n"
                    "            charger_delta_window;",
                ),
            )
            and "accumulated face coverage is split around that region"
            in architecture
            and "charging ornament pixels are not re-driven" in architecture
        ),
        "lifecycle_boundary_runs_reset_first_mode2_fast_ff": (
            contains_all(
                fast_boundary,
                (
                    "ssd1681_reset();",
                    "ssd1681_command(0x12u)",
                    "ssd1681_accepted_mode2_rearm(&mode2_load_elapsed_ms)",
                    "memcpy(s_blink_closed_frame, s_previous_frame, SSD1681_FRAME_BYTES)",
                    "0x26u, s_blink_closed_frame, &window",
                    "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                    "static const uint8_t fast_full_update[] = {0xFFu}",
                    "path=mode2_fast_full",
                    "reset_before_ready=1",
                    "visible_geometry=full border=0x05 partial_window_before_activation=0",
                ),
            )
            and fast_visible_stage.count(
                "ssd1681_set_window(&window, false, false)"
            ) == 2
            and "ssd1681_native_two_pass_source_window" not in fast_visible_stage
            and "Every product lifecycle boundary uses the same reset-first"
            in architecture
            and contains_all(
                function_body(
                    app_ble,
                    "bool Companion_Screen_EnterLowPowerIdle(void)",
                ),
                (
                    "refresh=lifecycle_mode2_fast_ff",
                    "COMP_EPAPER_REFRESH_VISIBLE_FULL",
                ),
            )
            and "COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG" not in function_body(
                app_ble,
                "bool Companion_Screen_EnterLowPowerIdle(void)",
            )
            and "ssd1681_official_strong_full_candidate_activation(" not in
            panel
            and "ssd1681_lifecycle_mode2_fast_full_activation(" in
            function_body(
                panel,
                "static comp_epaper_panel_result_t "
                "ssd1681_accepted_cached_mode2_product_refresh(",
            )
        ),
        "idle_visible_commit_enters_panel_deep_sleep_once": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in main_source
            and "s_epaper_deep_sleep_entered" in main_source
            and "ssd1681_command_data(\n                                  0x10u, deep_sleep_mode"
            in panel
            and "deep_sleep command=0x10 data=0x01" in panel
            and "A successfully committed low-power surface sends the SSD1681 deep-sleep"
            in architecture
        ),
        "natural_blink_is_independent_committed_composition_overlay": (
            contains_all(
                function_body(
                    app_ble,
                    "static bool Companion_Display_EmitNaturalBlinkFrame(",
                ),
                (
                    "comp_screen_composition_snapshot(",
                    "composition.base.frame_index",
                    "composition.recording_visible",
                    "COMP_EPAPER_DISPLAY_FLAG_NATURAL_BLINK_FRAME",
                    "player_mutated=0",
                    "independent_blink_overlay",
                ),
            )
            and "comp_emote_player_play_now_name(" not in function_body(
                app_ble,
                "static bool Companion_Display_EmitNaturalBlinkFrame(",
            )
            and contains_all(
                panel + architecture,
                (
                    "ssd1681_compose_natural_blink(",
                    "Replay the accepted r37 physical face path",
                    "single-current-plane face track",
                    "mutates the emotion player.",
                ),
            )
            and "SSD1681_NATURAL_BLINK_X" not in panel
            and contains_all(
                app_ble + architecture,
                (
                    "request.recording_overlay_only == 0u &&",
                    "COMP_EPAPER_DISPLAY_FLAG_NATURAL_BLINK_FRAME) == 0u",
                    "Blink close completion records that close is visible",
                    "Producer completion is state-only",
                ),
            )
            and "Companion_Display_EmitNaturalBlinkFrame(" not in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
        ),
        "recording_gesture_does_not_restart_emotion_clock": (
            contains_all(
                function_body(app_ble, "bool Companion_Screen_DailyPointerSample("),
                (
                    "Companion_CompReq775RecordingOverlayActive()",
                    "COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MAX_X_200",
                    "COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MIN_Y_200",
                    "cancelling life here only destroys the independent",
                ),
            )
            and "Companion_CompReq775ResumeBrowserLifeAfterTouch(now_ms);" not in
            daily_signal_body
            and "Companion_PetPerformance_ApplyExpressionSignal(signal);" not in
            recording_start_branch
            and "Companion_Display_ScheduleExpressionTick(now_ms);" not in
            recording_start_branch
            and "Starting and stopping recording therefore only change the" in architecture
            and "stays out of the pet-performance and base-expression" in architecture
        ),
        "pointer_follow_commits_are_single_shot": (
            contains_all(
                function_body(app_ble, "bool Companion_Screen_DailyPointerSample("),
                (
                    "COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_CADENCE_MS",
                    '"browser_pointer_follow"',
                    "s_companion_browser_pointer_next_commit_ms",
                ),
            )
            and contains_all(
                function_body(app_ble, "bool Companion_Screen_DailyPointerSample("),
                (
                    "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,\n          false,\n          \"browser_pointer_follow\"",
                    "event=release return_commits=",
                ),
            )
            and "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,\n          true,\n          \"browser_pointer_follow\""
            not in function_body(app_ble, "bool Companion_Screen_DailyPointerSample(")
            and contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_ProcessExpressionTick(void)\n{",
                ),
                (
                    "s_companion_browser_pointer_active",
                    '"browser_pointer_follow"',
                    "event=frame_complete",
                    "contact=active waiting=latest",
                ),
            )
            and "Companion_CompReq775ResumeBrowserLifeAfterTouch(now_ms);"
            in function_body(
                app_ble,
                "static void Companion_Display_ProcessExpressionTick(void)\n{",
            )
        ),
        "buffered_input_gates_every_visual_dispatch": (
            contains_all(
                function_body(
                    app_ble, "static void Companion_Display_Task(void)\n{"
                ),
                (
                    "if (Companion_App_ShouldYieldDisplayForTouch())",
                    "s_companion_post_busy_arbiter_pending = true;",
                    "if (comp_epaper_display_queue_pending(&s_companion_display_queue) == 0u)",
                    "Companion_Display_ServicePublishedTracks(",
                ),
            )
            and function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            ).index("if (Companion_App_ShouldYieldDisplayForTouch())")
            < function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            ).index("Companion_Display_ServicePublishedTracks(")
            and "Input is a pre-dispatch lane above the visual planner"
            in architecture
            and "Companion_Screen_ResumeAfterInputDrain();" in main_source
            and contains_all(
                function_body(
                    app_ble,
                    "void Companion_Screen_ResumeAfterInputDrain(void)\n{",
                ),
                (
                    "s_companion_post_busy_arbiter_pending",
                    "Companion_App_ShouldYieldDisplayForTouch()",
                    "Companion_Display_RequestTask();",
                ),
            )
        ),
        "display_coordinator_is_dedicated_event_driven_owner": (
            contains_all(
                main_source,
                (
                    "xTaskCreate(Companion_Rtos_DisplayTask,",
                    '"display",',
                    "s_companion_display_task_running = true;",
                    "Companion_Screen_DisplayCoordinatorRunOnce();",
                    "ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(250u))",
                ),
            )
            and contains_all(
                app_ble,
                (
                    "Companion_Display_SequencerTask",
                    "Companion_Rtos_RequestDisplayCoordinator()",
                    "void Companion_Screen_DisplayCoordinatorRunOnce(void)",
                    "Companion_Display_RequestTask();",
                ),
            )
            and app_ble.count(
                "UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID"
            ) == 1
            and "DisplayCoordinatorTask" in architecture
            and "the only RTOS task" in architecture
        ),
        "cross_task_screen_mutations_use_single_owner_intents": (
            contains_all(
                app_ble,
                (
                    "COMPANION_SCREEN_INTENT_QUEUE_DEPTH 48u",
                    "static bool Companion_Screen_ShouldPostIntent(void)",
                    "static bool Companion_Screen_PostIntent(",
                    "static void Companion_Screen_DrainIntents(void)",
                    "s_companion_screen_intent_queue[s_companion_screen_intent_write] = *intent;",
                    "Companion_Screen_DrainIntents();",
                    "COMPANION_SCREEN_INTENT_DAILY_POINTER",
                    "COMPANION_SCREEN_INTENT_RECORDING_STOP_FEEDBACK",
                    "COMPANION_SCREEN_INTENT_BATTERY_STATUS",
                ),
            )
            and "xQueueCreate" not in app_ble
            and function_body(
                app_ble,
                "void Companion_Screen_DisplayCoordinatorRunOnce(void)",
            ).index("Companion_Screen_DrainIntents();")
            < function_body(
                app_ble,
                "void Companion_Screen_DisplayCoordinatorRunOnce(void)",
            ).index("Companion_Display_Task();")
            and all(
                "Companion_Screen_ShouldPostIntent()" in function_body(
                    app_ble, signature
                )
                for signature in (
                    "void Companion_Screen_MenuRequest(",
                    "bool Companion_Screen_MenuRequestClean(",
                    "bool Companion_Screen_EnterLowPowerIdle(void)",
                    "bool Companion_Screen_ShowDailyClean(void)",
                    "bool Companion_Screen_WakeDailyClean(void)",
                    "bool Companion_Screen_DailyExpressionSignal(",
                    "bool Companion_Screen_RecordingExitIntentFastLatch(",
                    "bool Companion_Screen_RecordingStopFeedback(",
                    "bool Companion_Screen_DailyPointerSample(",
                    "bool Companion_Screen_DailyTapAt(",
                    "bool Companion_Screen_DailyStrokeAt(",
                    "void Companion_Screen_ResumeAfterInputDrain(void)",
                    "static void Companion_Display_EnqueueExpressionSignal(\n"
                    "    comp_epaper_expression_signal_t signal,\n"
                    "    uint32_t request_id_hint)\n{",
                    "static void Companion_Display_ApplyBatteryExpressionHint(\n"
                    "    const companion_gatt_battery_charge_v1_t *status)\n{",
                )
            )
            and "fixed-capacity intent rings" in architecture
            and "single-writer" in architecture
        ),
        "recording_control_has_priority_critical_intent_lane": (
            contains_all(
                app_ble + architecture,
                (
                    "COMPANION_SCREEN_CRITICAL_INTENT_QUEUE_DEPTH",
                    "Companion_Screen_IntentIsCritical",
                    "Companion_Screen_EnqueueIntentLocked",
                    "s_companion_screen_critical_intent_queue",
                    "s_companion_screen_critical_intent_count",
                    "s_companion_screen_critical_intent_coalesced",
                    "lane=critical",
                    "recording START, exit/fast-exit",
                    "drains that\nring first",
                    "coalesces its newest terminal state",
                ),
            )
            and app_ble.find(
                "if (s_companion_screen_critical_intent_count != 0u)"
            )
            < app_ble.find("else if (s_companion_screen_intent_count != 0u)")
        ),
        "audio_dma_isr_wakes_bounded_blocking_worker": (
            contains_all(
                function_body(main_source, "static void pdm_raw_dma_mark_half(uint8_t half)\n{"),
                (
                    "s_pdm_raw_dma_ready_mask |= bit;",
                    "vTaskNotifyGiveFromISR(s_companion_rec_task,",
                    "portYIELD_FROM_ISR(higher_priority_task_woken);",
                ),
            )
            and contains_all(
                function_body(main_source, "static void Companion_Rtos_RecTask(void *arg)\n{"),
                (
                    "ulTaskNotifyTake(pdTRUE, wait)",
                    "pdm_raw_dma_half_ready()",
                    "Companion_Recording_ServiceHotTick();",
                ),
            )
            and "taskYIELD();" not in function_body(
                main_source, "static void Companion_Rtos_RecTask(void *arg)\n{"
            )
            and "SAI DMA half/full ISR" in architecture
            and "bounded task batches" in architecture
        ),
        "browser_generation_identity_is_bound_to_each_display_request": (
            contains_all(
                app_ble,
                (
                    "request.asset_state_hash",
                    "s_companion_ui_asset_generation_in_flight_entry",
                    "s_companion_ui_asset_generation_in_flight_valid",
                    "comp_ui_asset_generation_find(",
                    "request.asset_state_hash)",
                ),
            )
            and "asset_state_hash" in header
            and "s_companion_ui_asset_generation_active_entry" not in app_ble
            and "s_companion_ui_asset_generation_in_flight_entry" in
            function_body(
                app_ble,
                "static bool Companion_CompReq775ReadOverrideFrame(",
            )
        ),
        "recording_touch_yields_without_cancelling_emotion": (
            contains_all(
                function_body(
                    main_source,
                    "bool Companion_App_ShouldCancelAutomaticMotionForTouch(void)",
                ),
                (
                    "recording_contact_pending",
                    "COMP_RECORDING_STATE_PENDING_START",
                    "COMP_RECORDING_STATE_RECORDING",
                    "touch_is_recording_corner",
                    "!recording_contact_pending",
                ),
            )
            and contains_all(
                architecture,
                (
                    "may yield the",
                    "current synchronous panel transaction",
                ),
            )
        ),
        "recording_stop_visual_timeout_is_3000ms": (
            "#define TOUCH_RECORDING_STOP_VISUAL_TIMEOUT_MS 3000u"
            in main_source
        ),
        "recording_stop_request_is_not_rearmed": app_ble.count(
            "if (s_companion_recording_stop_feedback_request_id != 0u)"
        ) >= 3,
        "recording_exit_second_down_preempts_buffer_replay": contains_all(
            main_source,
            (
                "s_recording_fast_toggle_pending",
                "s_recording_fast_exit_first_release_ms",
                "s_recording_fast_exit_submitted_ms = now_ms",
                "Companion_Rtos_KickRec();",
                "Companion_Rtos_ServiceRecordingFastToggle();",
                "owner=input_to_rec",
                "phase=browser_replay action=deduplicated",
                "reason=post_stop_touch_guard",
                "phase=clean_release guard=cleared",
            ),
        ),
        "recording_start_intent_survives_first_slot_backpressure": (
            contains_all(
                recording_start_branch + architecture,
                (
                    "initial_dispatch=scheduled",
                    "Companion_CompReq775PublishRecordingTrack();",
                    "s_companion_post_busy_arbiter_pending = true",
                    "Companion_Display_RequestTask();",
                    "return true;",
                    "durable display\nintent",
                    "same prepared first waveform",
                    "returns without enqueueing from inside intent drain",
                ),
            )
            and "Companion_Display_EmitAccessoryFrame(true, true)"
                not in recording_start_branch
        ),
        "recording_overlay_uses_deadline_composition_not_fixed_bursts": (
            "COMPANION_RECORDING_OVERLAY_FAST_BURST" not in app_ble
            and "s_companion_recording_overlay_fast_burst_count" not in app_ble
            and contains_all(
                app_ble + architecture,
                (
                    "whether its snapshot is coalescible",
                    "Companion_CompReq775TryEmitNextRecordingOverlay()",
                    "The recording arbiter has no fixed burst ratio",
                    "Recording owns otherwise free local-only",
                ),
            )
        ),
        "recording_and_emotion_clocks_are_independent": (
            "Producer completion is state-only" in architecture
            and "Recording completion never advances the\n"
                "browser-life clock" in architecture
            and "exactly one non-reentrant post-BUSY arbiter" in architecture
            and "const bool base_track_ready =" in app_ble
            and "s_companion_blink_scheduler.open_pending" in app_ble
            and "Companion_CompReq775RecordingOverlayActive()" in app_ble
            and "s_companion_recording_emotion_presentation_gate" in app_ble
            and "comp_epaper_display_presentation_gate_due(" in app_ble
            and "comp_epaper_display_presentation_gate_advance(" in app_ble
            and "independently jittered absolute presentation gate"
                in architecture
            and "Recording readiness is commit-driven" in architecture
            and "Companion_Display_ProcessExpressionTick();" not in function_body(
                app_ble,
                "static void Companion_CompReq775CompleteRecordingOverlayRequest",
            )
            and "Companion_Display_ProcessDueTracks(" not in function_body(
                app_ble,
                "static void Companion_CompReq775CompleteRecordingOverlayRequest",
            )
            and "UTIL_SEQ_SetTask(" not in function_body(
                app_ble,
                "static void Companion_CompReq775CompleteRecordingOverlayRequest",
            )
            and "Companion_Display_EmitNaturalBlinkFrame(" not in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
            and "single guarded arbiter" in architecture
            and "exact r53 failure" in architecture
            and "Companion_CompReq775RecordingOverlayRemainingMs" not in app_ble
            and "recording_remaining_ms" not in app_ble
            and not (
                "s_companion_motion_clock_ms +=\n"
                "        report.visible_to_dispatch_ms + report.request_to_visible_ms"
                in app_ble
            )
            and "s_companion_motion_clock_ms = HAL_GetTick();" in app_ble
            and "comp_epaper_display_joint_deadline_remaining_ms(" in app_ble
            and "comp_epaper_display_joint_deadline_ms(" in app_ble
            and "comp_epaper_display_completion_service(" in app_ble
            and "comp_epaper_display_completion_service(" in track_arbiter
            and "completion alone cannot wake another track" in track_arbiter_test
            and "comp_epaper_display_track_ready_mailbox_publish(" in app_ble
            and "comp_epaper_display_track_ready_mailbox_consume(" in app_ble
            and "touch yield cannot consume unpublished physical work"
                in track_arbiter_test
            and "successful recording enqueue consumes only recording"
                in track_arbiter_test
            and "There is no generic base fallback" in architecture
            and "comp_epaper_display_queue_pending(&s_companion_display_queue) == 0u)"
                in app_ble
            and "Companion_Display_ServicePublishedTracks(" in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
            and "Companion_Display_ProcessDueTracks(" not in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
        ),
        "recording_events_do_not_borrow_expression_timer": (
            contains_all(
                app_ble + architecture,
                (
                    "Companion_Display_CreateRecordingExitTimer",
                    "Companion_Display_RecordingExitTimerElapsed",
                    "s_companion_recording_exit_timer_id",
                    "dedicated one-shot timer",
                    "never stops, restarts, or borrows the expression timer",
                ),
            )
            and "Companion_Display_ScheduleExpressionTick(" not in function_body(
                app_ble, "bool Companion_Screen_RecordingExitIntent(uint16_t timeout_ms)"
            )
            and "s_companion_expression_tick_started_ms" not in function_body(
                app_ble, "bool Companion_Screen_RecordingExitIntent(uint16_t timeout_ms)"
            )
            and "Companion_Display_ScheduleExpressionTick(" not in function_body(
                app_ble,
                "bool Companion_Screen_RecordingStopFeedback(uint32_t gesture_submitted_ms)",
            )
            and "Companion_Display_ScheduleExpressionTick(" not in
                recording_start_branch
            and "request.recording_overlay_only == 0u" in function_body(
                app_ble, "static void Companion_Display_Task(void)\n{"
            )
        ),
        "independent_tracks_use_nonmutating_host_tested_arbiter": contains_all(
            track_arbiter + track_arbiter_test + track_arbiter_runner + app_ble,
            (
                "comp_epaper_display_track_arbiter_select",
                "comp_epaper_display_track_arbiter_plan",
                "candidate->coalescible",
                "out_plan->track_mask",
                "candidate->pending",
                "candidate->in_flight",
                "candidate->has_deadline",
                "recording consumes a slot while timed tracks are not due",
                "the earlier independent base deadline owns one slot",
                "one physical slot advances only its selected logical owner",
                "blink open keeps the indivisible pair's next slot",
                "MACHINE_READY: independent track deadlines",
                "COMPANION_DISPLAY_TRACK_RECORDING",
            ),
        ),
        "recording_clock_has_one_local_owner_without_cross_track_advance": (
            "Companion_CompReq775PrepareRecordingForVisibleCommit(" not in
                function_body(
                    app_ble,
                    "static bool Companion_Display_EmitEmoteFrameModeInternal(\n"
                    "    comp_epaper_refresh_mode_t refresh_mode,\n"
                    "    const comp_epaper_motion_request_t *motion_request,\n"
                    "    uint16_t display_flags)\n{",
                )
            and "Companion_CompReq775TrackRecordingOverlayRequest(" not in
                function_body(
                    app_ble,
                    "static bool Companion_Display_EmitEmoteFrameModeInternal(\n"
                    "    comp_epaper_refresh_mode_t refresh_mode,\n"
                    "    const comp_epaper_motion_request_t *motion_request,\n"
                    "    uint16_t display_flags)\n{",
                )
            and "Companion_CompReq775PrepareRecordingForVisibleCommit(" not in
                function_body(
                    app_ble, "static bool Companion_Display_EmitNaturalBlinkFrame("
                )
            and "Companion_CompReq775TrackRecordingOverlayRequest(" not in
                function_body(
                    app_ble, "static bool Companion_Display_EmitNaturalBlinkFrame("
                )
            and contains_all(
                function_body(
                    app_ble,
                    "static bool Companion_Display_EmitAccessoryFrame(\n"
                    "    bool recording_overlay_only,\n"
                    "    bool include_recording_overlay)\n{",
                ),
                (
                    "recording_overlay_only && include_recording_overlay",
                    "if (include_recording_overlay && !recording_overlay_only)",
                    "Companion_CompReq775PrepareRecordingForVisibleCommit(",
                    "Companion_CompReq775TrackRecordingOverlayRequest(request_id)",
                ),
            )
            and "request->recording_overlay_only == 0u" not in function_body(
                app_ble,
                "static void Companion_CompReq775CompleteRecordingOverlayRequest",
            )
            and "Only a\nrecording-local transaction may prepare" in architecture
            and "not\ncross-track coalescible" in architecture
        ),
        "menu_hold_uses_real_fill_milestones_and_visible_barrier": (
            "recognition_lead_ms + (index + 1) * contract.cell_step_ms"
            in source_pack_generator
            and "+ (bucket + 1) * menuHold.cell_step_ms"
            in interaction_exporter
            and "Companion_Screen_MenuHoldFinalCommitResolved"
            in main_source
            and "phase=wait_final_hold_visible" in main_source
            and "barrier=final_hold_visible" in main_source
            and "menu_hold_final_commit request=" in app_ble
            and "1500/2000/2500/3000 ms" in architecture
        ),
        "native_contract_covers_queue_full_and_matching_completion": contains_all(
            queue_test,
            (
                "COMP_EPAPER_DISPLAY_QUEUE_FULL",
                "comp_epaper_display_queue_complete(&queue, 202u)",
                "comp_epaper_display_queue_boundary_owned(&queue)",
            ),
        ),
        "mutation_gate_removes_boundary_guard": contains_all(
            mutation,
            (
                "display_queue-boundary-guard-removed.c",
                "$sourceText.Replace($guard, $mutated)",
                "Removing boundary ownership guard did not fail",
            ),
        ),
        "coverage_contract_tests_growth_and_reset": contains_all(
            coverage_test,
            (
                "coverage is the stable union, not the latest XOR",
                "contained change cannot shrink physical coverage",
                "a lifecycle full-refresh boundary starts a new epoch",
            ),
        ),
        "recording_overlay_is_rearmed_only_by_matching_panel_commit": (
            contains_all(
                overlay_header + overlay_source + app_ble,
                (
                    "COMP_EPAPER_OVERLAY_COMMIT_IN_FLIGHT",
                    "comp_epaper_overlay_commit_scheduler_mark_dispatched",
                    "scheduler->in_flight_request_id != request_id",
                    "comp_epaper_overlay_commit_scheduler_complete",
                    "action=overlay_trace",
                    "post_commit_dwell_ms=0",
                    "direct_next_dispatch",
                    "Companion_Display_ServicePostBusyArbiter(",
                    "Companion_Screen_ServiceDeferredRecordingTrace",
                    "rearm=first_available_slot",
                    "s_companion_recording_in_flight_timeline_index",
                    "request->recording_overlay_present == 0u",
                    "if (!include_recording_overlay)",
                ),
            )
            and "s_companion_recording_overlay_next_ms" not in app_ble
            and "now_ms + COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_CADENCE_MS"
            not in app_ble
        ),
        "recording_waveform_advances_only_on_matching_visible_commit": (
            contains_all(
                app_ble + architecture,
                (
                    "Companion_CompReq775PrepareRecordingForVisibleCommit",
                    "if (recording_clock_owner &&",
                    "comp_epaper_overlay_commit_scheduler_complete",
                    "matching request id",
                ),
            )
            and app_ble.count(
                "Companion_CompReq775TrackRecordingOverlayRequest"
            ) == 2
        ),
        "recording_overlay_commit_contract_rejects_failed_visible_mutant": (
            contains_all(
                overlay_test + overlay_runner,
                (
                    "a second phase cannot queue behind BUSY",
                    "matching visible completion releases the next slot",
                    "failed phase can be prepared again rather than skipped",
                    "overlay-commit-failure-promoted.c",
                    "Promoting a failed transaction to visible did not fail",
                ),
            )
        ),
        "recording_overlay_does_not_suppress_base_choreography": (
            "!s_companion_recording_overlay_active" not in app_ble
            and "COMP_EPAPER_MOTION_CANCEL_RECORDING" not in function_body(
                app_ble, "static void Companion_Display_EnqueueExpressionSignal("
            )
            and contains_all(
                app_ble + architecture + playbook,
                (
                    "owner=overlay_scheduler emotion_cancel=0",
                    "recording_intent_overlay_start",
                    "emotion,\nblink, and other events retain independent visible timing",
                    "Never let an always-ready overlay",
                ),
            )
            and contains_all(
                function_body(
                    app_ble,
                    "static void Companion_Display_ProcessDueTracks(\n"
                    "    uint32_t now_ms,\n"
                    "    comp_epaper_refresh_mode_t refresh_mode)\n{",
                ),
                (
                    ".id = COMPANION_DISPLAY_TRACK_BASE",
                    ".priority = 2u",
                    ".id = COMPANION_DISPLAY_TRACK_RECORDING",
                    ".priority = 2u",
                    "s_companion_recording_overlay_scheduler.last_visible_ms",
                    ".id = COMPANION_DISPLAY_TRACK_ACCESSORY",
                    ".priority = 4u",
                    "comp_epaper_display_track_arbiter_plan",
                    ".coalescible = false",
                ),
            )
            and "speculative, not-yet-owned pixels" in architecture
        ),
        "recording_flash_prepare_is_bounded_and_ui_interleaved": contains_all(
            main_source,
            (
                "FLASH_RECORDING_ASYNC_INITIAL_ERASE_BYTES 4096u",
                "job.kind == COMPANION_STORAGE_JOB_RECORDING_PREPARE ||",
                'interleave_ui ? "ui_interleaved_4k" : "fast_64k"',
                "taskYIELD();",
            ),
        ),
        "recording_dma_backlog_yields_bounded_cpu_slot": contains_all(
            main_source,
            (
                "A continuously ready DMA backlog must not turn the realtime",
                "s_recording_flash.capture_active ||",
                "vTaskDelay(pdMS_TO_TICKS(1u));",
            ),
        ),
        "watchdog_failure_receipt_survives_scheduler_checkpoint": contains_all(
            watchdog_source,
            (
                "uint32_t failure_mask = 0u;",
                "failure_mask = stalled_mask;",
                "healthy=%u stalled_mask=0x%02lX",
                "if (!failure_saved) {\n            companion_watchdog_clear_checkpoint();",
            ),
        ),
        "rtc_timer_display_wakeup_is_freertos_syscall_safe": contains_all(
            main_source,
            (
                "HAL_NVIC_SetPriority(\n        RTC_WKUP_IRQn,",
                "configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY",
                "display_notify=from_isr",
                "vTaskNotifyGiveFromISR(s_companion_display_task,",
            ),
        ),
        "inherited_iwdg_is_reloaded_before_scheduler_handoff": contains_all(
            main_source,
            (
                "IWDG->RLR = 0x0FFFu;",
                "IWDG->KR = 0xAAAAu;",
                "boot_handoff=reload_if_running owner=watchdog_task",
                "vTaskStartScheduler();",
            ),
        ),
        "hardfault_path_never_takes_runtime_logging_locks": (
            "companion_watchdog_record_fatal" in hardfault_handler
            and "NVIC_SystemReset" in hardfault_handler
            and "printf(" not in hardfault_handler
            and "companion_uart_transmit_sync" not in hardfault_handler
        ),
        "functional_layers_have_one_composition_authority": (
            contains_all(
                composition_header + composition_source + app_ble + architecture,
                (
                    "comp_screen_composition_set_charging",
                    "comp_screen_composition_set_recording",
                    "comp_screen_composition_snapshot",
                    "s_companion_screen_composition",
                    "Every home expression/accessory enqueue reads one immutable functional",
                    "is not allowed to become the visual-active authority",
                ),
            )
            and app_ble.count("comp_screen_composition_snapshot(") >= 3
            and "s_companion_comp_req638_charging_visual_active" not in app_ble
            and "s_companion_recording_overlay_frame_index" not in app_ble
            and "s_companion_menu_hold_return_charging" not in app_ble
        ),
        "composition_preserves_hidden_independent_tracks": contains_all(
            composition_source + composition_test + composition_runner,
            (
                "home && composition->charging.active",
                "home && composition->recording.active",
                "COMP_SCREEN_SURFACE_MENU",
                "COMP_SCREEN_SURFACE_LOW_POWER",
                "composition.charging.revision == charging_revision",
                "composition.recording.revision == recording_revision",
                "test_screen_composition_journey.exe",
            ),
        ),
        "functional_overlays_use_last_committed_base": (
            "comp_screen_composition_set_base" in composition_header
            and "comp_screen_composition_set_base(" in composition_source
            and "request.recording_overlay_only == 0u" in app_ble
            and "base_source=committed_composition" in app_ble
            and "last successful non-recording-overlay panel commit" in architecture
        ),
        "refresh_playbook_rejects_fixed_ordinary_tiers": contains_all(
            playbook,
            ("named browser/CEMP", "hard-coded 2772-byte", "hard-coded 4200-byte"),
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.display_runtime_architecture.v1",
        "status": "MACHINE_READY" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "source_sha256": {
            str(path.relative_to(REPO)).replace("\\", "/"): sha256(path)
            for path in paths
        },
        "hardware_contact": 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
