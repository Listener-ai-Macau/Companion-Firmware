#!/usr/bin/env python3
"""Static release gate for COMP-REQ-775 r61 visible layer isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-independent-enabled", action="store_true")
    args = parser.parse_args()

    app_path = args.repo / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    driver_path = args.repo / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    app = app_path.read_text(encoding="utf-8")
    driver = driver_path.read_text(encoding="utf-8")
    motion_path = args.repo / "app/companion_pendant/epaper/motion_coordinator.c"
    motion = motion_path.read_text(encoding="utf-8")
    main_path = args.repo / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    main_source = main_path.read_text(encoding="utf-8")
    start_block = between(
        app,
        "if (signal == COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START)",
        "else if (signal == COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP")
    overlay_complete = between(
        app,
        "static void Companion_CompReq775CompleteRecordingOverlayRequest(",
        "static bool Companion_CompReq775PrepareNextRecordingOverlayFrame(")
    prepare_visible_recording = between(
        app,
        "static bool Companion_CompReq775PrepareRecordingForVisibleCommit(",
        "static bool Companion_CompReq775ForceHoldFace(")
    display_planner = between(
        app,
        "static void Companion_Display_ProcessDueTracks(",
        "static void Companion_Display_ScheduleExpressionTick(")
    enqueue_expression_decision_begin = app.rindex(
        "static void Companion_Display_EnqueueExpressionDecision(")
    enqueue_expression_decision = app[
        enqueue_expression_decision_begin:
        app.index(
            "static bool Companion_Screen_MenuRequestMode(",
            enqueue_expression_decision_begin)]
    multi_region = between(
        driver,
        "static bool ssd1681_native_cached_mode2_multi_region_activation(",
        "static bool ssd1681_native_cached_mode2_functional_activation(")
    functional_activation = between(
        driver,
        "static bool ssd1681_native_cached_mode2_functional_activation(",
        "bool companion_epaper_panel_stm32wb_ssd1681_comp_req_616_prepare(")
    face_driver = between(
        driver,
        "static bool ssd1681_cached_mode2_diff_internal(",
        "bool companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff(")
    recording_start_begin = main_source.rindex(
        "static bool start_user_recording_async(comp_recording_source_t source,")
    recording_start = main_source[
        recording_start_begin:
        main_source.index(
            "static void start_user_recording_max(comp_recording_source_t source,",
            recording_start_begin)]

    start_mutators = (
        "Companion_Display_EnterDailyMotion(",
        "comp_epaper_motion_coordinator_init(",
        "comp_epaper_motion_coordinator_cancel(",
        "comp_epaper_motion_coordinator_take_request(",
        "comp_epaper_motion_coordinator_complete_request(",
        "comp_emote_player_play_now_name(",
    )
    forbidden_legacy = (
        "life_wave_joint_r52",
        "joint=r52",
        "face_joint=r52",
        "life_wave_copaint mode=shared_0xCF",
        "authored_life_union_above_mic",
        "blink_eye_window_only",
        "Companion_CompReq775SoftAdvanceLifeBaseForCopaint",
    )
    independent_enabled = (
        "#define COMPANION_RECORDING_HOLD_FACE_DURING_REC 0" in app)
    checks = {
        "independent_mode_enabled_or_safe_preflight": (
            independent_enabled or not args.require_independent_enabled),
        "recording_start_does_not_mutate_life_story": not any(
            token in start_block for token in start_mutators),
        "recording_start_only_keeps_existing_life_awake": (
            "comp_epaper_motion_coordinator_keep_awake(" in start_block
            and "same_as_offline=1" in start_block),
        "pure_wave_emitter_is_only1": (
            "Companion_Display_EmitAccessoryFrame(true, true)" in app),
        "wave_completion_accepts_only_pure_or_explicit_carrier": (
            "request->recording_overlay_only == 0u" in overlay_complete
            and "COMP_EPAPER_DISPLAY_FLAG_AUTO_ACCESSORY" in overlay_complete),
        "recording_phase_is_carried_transport_not_clock": (
            "face_visible_activation=authored_plus_wave_single_0xcf" in app
            and "wave_owner=recording_scheduler wave_drives_life=0" in app
            and "life_drives_wave=0 ornaments_follow_authored_life=1" in app),
        "authored_deadline_not_busy_grant_owns_life_clock": (
            "coordinator->outstanding_due_ms = coordinator->next_request_ms;"
            in motion
            and "motion_advance_absolute_deadline(\n            due_ms"
            in motion),
        "no_wave_turn_gate_can_pause_wave": (
            "s_companion_recording_wave_turn_required" not in app
            and "!wave_turn_required" not in app),
        "single_busy_fairness_inserts_pure_wave_between_authored_carriers": (
            "COMPANION_RECORDING_FACE_WAVE_SLOT_DUE" in overlay_complete
            and "request->recording_overlay_only == 0u" in overlay_complete
            and "const bool pure_wave_between_authored_due" in display_planner
            and display_planner.count("!pure_wave_between_authored_due") == 2
            and "COMPANION_DISPLAY_TRACK_RECORDING" in display_planner),
        "blink_open_pair_integrity_exempts_wave_fairness_slot": (
            "const bool blink_open_ready" in display_planner
            and display_planner.index("const bool blink_open_ready") <
                display_planner.index("const bool blink_closed_ready")
            and "pure_wave_between_authored_due" not in between(
                display_planner,
                "const bool blink_open_ready",
                "const bool blink_closed_ready")),
        "face_only_fallback_freezes_exact_committed_mic_pixels": (
            "memcpy(&s_frame[row + mic_x_start]" in face_driver
            and "&s_previous_frame[row + mic_x_start]" in face_driver),
        "face_only_mic_delta_is_hard_invariant": (
            "recording_face_mic_invariant_fail" in face_driver
            and "!recording_face_mic_copaint" in face_driver),
        "r61_recording_carrier_uses_bounded_old_current_bands": (
            "ssd1681_product_exact_delta_bands_outside(" in driver
            and "best_added_area" in driver
            and "crosses_exclusion" in driver
            and "SSD1681_PRODUCT_RECORDING_FACE_REGION_MAX 30u" in driver
            and "SSD1681_PRODUCT_STAGED_REGION_MAX 34u" in driver
            and "recording_exact_face_carrier = true;" in face_driver
            and "functional_delta_windows[functional_delta_count++] =\n"
                "                        staged_regions[index];" in face_driver
            and "recording_eye_black_reinforce = true;" in face_driver
            and "recording_eye_bounds[2u]" in face_driver
            and "s_blink_closed_frame[row + x] |=\n"
                "                            (uint8_t)~s_frame[row + x];" in face_driver
            and "authored_plus_wave_isolated_bands" in face_driver
            and "unchanged_face_driven=0 old_current=1 eye_black=1" in face_driver),
        "r61_face_and_wave_use_old_current_one_busy": (
            "ssd1681_write_plane_region(\n                 0x26u, s_blink_closed_frame"
            in functional_activation
            and "ssd1681_write_plane_region(\n                 0x24u, s_frame"
            in functional_activation
            and functional_activation.count("ssd1681_command_data(0x22u") == 1
            and functional_activation.count("ssd1681_command(0x20u)") == 1
            and functional_activation.count("ssd1681_wait_refresh_complete(") == 1),
        "r61_recording_capacity_fails_closed_without_source_complete": (
            "authored_plus_wave_exact_delta_reject" in face_driver
            and "fail_closed=1" in face_driver
            and "authored_plus_wave_exact_delta_fallback" not in face_driver),
        "r61_partitioned_retry_remains_bounded_old_current": (
            "ssd1681_product_partitioned_delta_bands(" in driver
            and "authored_plus_wave_partitioned_exact" in face_driver
            and "old_current=1 exclusions=4" in face_driver
            and "safe_cells[]" in driver),
        "pre_dispatch_busy_defers_without_permanent_face_hold": (
            "rec_pre_dispatch" in app
            and "[screen-life] defer rec=1 hold=0" in app
            and "[screen-blink] defer rec=1 hold=0" in app
            and "only a completed panel request may trip HOLD" in app),
        "inflight_wave_candidate_cannot_be_reused_by_authored_face": (
            "!comp_epaper_overlay_commit_scheduler_ready(" in
                prepare_visible_recording
            and "candidate_prepared != 0u" in prepare_visible_recording
            and prepare_visible_recording.index(
                "!comp_epaper_overlay_commit_scheduler_ready(") <
                prepare_visible_recording.index("candidate_prepared != 0u")
            and "return false;" in prepare_visible_recording[
                prepare_visible_recording.index(
                    "!comp_epaper_overlay_commit_scheduler_ready("):
                prepare_visible_recording.index("candidate_prepared != 0u")]),
        "wave_bootstrap_owns_first_post_busy_slot": (
            "COMPANION_RECORDING_FACE_ENABLED |\n"
                "             COMPANION_RECORDING_FACE_WAVE_SLOT_DUE" in app
            and "overlay_start promises wave_bootstrap" in app
            and "s_companion_recording_face_state |=\n"
                "              COMPANION_RECORDING_FACE_WAVE_SLOT_DUE;" in
                display_planner),
        "generic_idle_decision_cannot_replace_recording_wave": (
            "if (Companion_CompReq775RecordingOverlayActive())" in
                enqueue_expression_decision
            and "physical r64 run1" in enqueue_expression_decision
            and enqueue_expression_decision.index(
                "if (Companion_CompReq775RecordingOverlayActive())") <
                enqueue_expression_decision.index("decision->expression !=")),
        "pure_wave_can_carry_exact_independent_accessory_delta": (
            "wave_accessory_carrier_prepare_fail" in face_driver
            and "accessory_carried=%u accessory_clock_independent=1" in face_driver
            and "ssd1681_compose_charger_overlay(\n            expression_assets, request"
                in driver
            and "due_source=charging_wall_clock" in app
            and "wave_clock_advanced=0 life_clock_advanced=0" in app),
        "recording_pending_blocks_low_power_reentry": (
            "s_recording_fsm.state == COMP_RECORDING_STATE_PENDING_START"
                in main_source
            and "s_live_mic_pending" in main_source
            and "s_recording_prepare.pending" in main_source),
        "low_power_wake_commits_before_overlay_start": (
            recording_start.count("cancel_low_power_idle_pose_timer();") >= 2
            and "start_recording_internal(source, reason, false);"
                in recording_start
            and "wait < 600u" in recording_start
            and "Companion_Screen_BoundaryOwnsDisplay()" in recording_start
            and "companion_epaper_panel_stm32wb_ssd1681_mode2_settle_pending()"
                in recording_start
            and "action=low_power_wake_abort" in recording_start
            and recording_start.index("action=low_power_wake result=%u") <
                recording_start.index("COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START")),
        "gatt_recording_never_falls_back_without_overlay": (
            "live_mic async_prepare rejected" in main_source
            and "live_mic async_prepare unavailable; fallback sync"
                not in main_source
            and main_source.index("live_mic async_prepare rejected") <
                main_source.index("#else\n    start_user_recording_max(",
                                  main_source.index(
                                      "live_mic async_prepare rejected"))),
        "runtime_causal_phase_evidence_present": all(
            token in app for token in (
                "track=wave request=%lu",
                "due_source=recording_scheduler",
                "track=face request=%lu",
                "due_source=authored_absolute_deadline",
                "track=blink request=%lu",
                "due_source=blink_scheduler",
                "wave_every_activation=1")),
        "no_rejected_legacy_joint_or_soft_advance_path": not any(
            token in app or token in driver for token in forbidden_legacy),
    }
    result = {
        "schema": "companion.comp_req_775.r61_visible_isolation_gate.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "independent_enabled": independent_enabled,
        "require_independent_enabled": args.require_independent_enabled,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "source": {
            "app": str(app_path.resolve()),
            "app_sha256": hashlib.sha256(app_path.read_bytes()).hexdigest().upper(),
            "driver": str(driver_path.resolve()),
            "driver_sha256": hashlib.sha256(driver_path.read_bytes()).hexdigest().upper(),
            "motion": str(motion_path.resolve()),
            "motion_sha256": hashlib.sha256(motion_path.read_bytes()).hexdigest().upper(),
            "main": str(main_path.resolve()),
            "main_sha256": hashlib.sha256(main_path.read_bytes()).hexdigest().upper(),
        },
    }
    output = args.output if args.output.is_absolute() else args.repo / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
