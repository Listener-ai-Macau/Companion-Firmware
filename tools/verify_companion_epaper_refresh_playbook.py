#!/usr/bin/env python3
"""Guard the accepted Companion SSD1681 refresh matrix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
APP = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
PLAYBOOK = ROOT / "docs/companion_epaper_refresh_playbook.md"
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
INTERACTION_EXPORTER = ROOT / "tools/faraday_upper_art/export_comp_req_775_browser_interaction_contract.mjs"
INTERACTION_GENERATOR = ROOT / "tools/faraday_upper_art/generate_browser_interaction_contract.py"
OUTPUT = ROOT / ".cache/validation/comp-req-775-incremental-sync/EPAPER_REFRESH_PLAYBOOK_READY.json"
BLINK_OPEN = (
    ROOT
    / ".cache/validation/comp775-r33-expression-coverage-audit/"
    "source-pack/frames/blink_open.pbm"
)
BLINK_CLOSED = (
    ROOT
    / ".cache/validation/comp775-r33-expression-coverage-audit/"
    "source-pack/frames/blink_closed.pbm"
)


def read_product_p4(path: Path) -> bytes:
    raw = path.read_bytes()
    header = b"P4\n200 200\n"
    if not raw.startswith(header) or len(raw) != len(header) + 5000:
        raise ValueError(f"unexpected product PBM: {path}")
    return raw[len(header):]


def blink_difference_bounds(open_frame: bytes, closed_frame: bytes) -> list[list[int]]:
    bounds: list[list[int]] = []
    for left, right in ((0, 99), (100, 199)):
        changed: list[tuple[int, int]] = []
        for y in range(200):
            for x in range(left, right + 1):
                mask = 0x80 >> (x & 7)
                index = y * 25 + x // 8
                if bool(open_frame[index] & mask) != bool(closed_frame[index] & mask):
                    changed.append((x, y))
        if not changed:
            bounds.append([])
        else:
            bounds.append(
                [
                    min(x for x, _ in changed),
                    min(y for _, y in changed),
                    max(x for x, _ in changed),
                    max(y for _, y in changed),
                ]
            )
    return bounds


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
    panel = PANEL.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    playbook = PLAYBOOK.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    interaction_exporter = INTERACTION_EXPORTER.read_text(encoding="utf-8")
    interaction_generator = INTERACTION_GENERATOR.read_text(encoding="utf-8")
    product = function_body(
        panel, "static comp_epaper_panel_result_t ssd1681_accepted_cached_mode2_product_refresh("
    )
    fast_boundary = function_body(
        panel, "static bool ssd1681_lifecycle_mode1_gc_full_activation_ex("
    )
    idle_enter = function_body(
        app, "bool Companion_Screen_EnterLowPowerIdle("
    )
    idle_wake = function_body(
        app, "bool Companion_Screen_WakeDailyClean("
    )
    recording_stop = function_body(
        app, "bool Companion_Screen_RecordingStopFeedback("
    )
    post_busy_arbiter = function_body(
        app,
        "static void Companion_Display_ServicePostBusyArbiter("
        "\n    uint32_t completed_ms,\n"
        "    comp_epaper_display_class_t completed_class)\n{",
    )
    published_tracks = function_body(
        app,
        "static bool Companion_Display_ServicePublishedTracks(\n"
        "    comp_epaper_display_class_t completed_class)\n{",
    )
    automatic_motion = function_body(
        app,
        "static void Companion_Display_ProcessDueTracks(\n"
        "    uint32_t now_ms,\n"
        "    comp_epaper_refresh_mode_t refresh_mode)\n{",
    )
    cancel_motion = function_body(
        app,
        "static void Companion_Display_CancelAutomaticMotion(\n"
        "    comp_epaper_motion_cancel_reason_t reason)\n{",
    )
    enter_daily = function_body(
        app, "static void Companion_Display_EnterDailyMotion(uint32_t now_ms)\n{"
    )
    display_task = function_body(
        app, "static void Companion_Display_Task(void)\n{"
    )
    blink_compose = function_body(
        panel, "static bool ssd1681_compose_natural_blink("
    )
    cached_mode2 = function_body(
        panel, "static bool ssd1681_cached_mode2_diff_internal("
    )
    blink_open = read_product_p4(BLINK_OPEN)
    blink_closed = read_product_p4(BLINK_CLOSED)
    blink_bounds = blink_difference_bounds(blink_open, blink_closed)
    blink_emit = function_body(
        app, "static bool Companion_Display_EmitNaturalBlinkFrame("
    )
    blink_scheduler = (
        ROOT / "app/companion_pendant/epaper/motion_coordinator.c"
    ).read_text(encoding="utf-8")
    blink_header = (
        ROOT / "app/companion_pendant/epaper/motion_coordinator.h"
    ).read_text(encoding="utf-8")
    overlay_scheduler = (
        ROOT / "app/companion_pendant/epaper/overlay_commit_scheduler.c"
    ).read_text(encoding="utf-8")
    checks = {
        "lifecycle_intents_use_explicit_r57_and_mode1_boundaries": (
            "if (strong_idle_enter_refresh)" in product
            and product.count(
                "ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7("
            ) == 1
            and product.count(
                "ssd1681_lifecycle_mode1_gc_full_activation_ex("
            ) == 1
            and "ssd1681_official_strong_full_candidate_activation(" not in panel
            and "COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG" in idle_enter
            and "COMP_EPAPER_REFRESH_VISIBLE_FULL" in idle_wake
            and "ssd1681_accepted_fast_full_activation(" not in product
            and "ssd1681_accepted_visible_full_activation(" not in panel
            and "ssd1681_accepted_true_full_activation(" not in panel
        ),
        "menu_boot_wake_maintenance_use_mode1_gc_c7": all(
            token in fast_boundary
            for token in (
                "const uint8_t full_update = 0xC7u",
                "memcpy(s_blink_closed_frame, s_previous_frame, SSD1681_FRAME_BYTES)",
                "0x26u, s_blink_closed_frame, &window",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                "ssd1681_comp_req_611_report_window(\n        report, &window, 0xC7u",
                "ssd1681_prepare_vendor_fast_profile",
                "ssd1681_accepted_mode2_rearm",
            )
        )
        and "s_previous_frame_valid && s_controller_initialized" in fast_boundary
        and fast_boundary.index("ssd1681_reset();")
        < fast_boundary.index("ssd1681_wait_ready(0u, SSD1681_READY_TIMEOUT_MS)")
        and "ssd1681_native_two_pass_source_window" not in fast_boundary,
        "lifecycle_rejects_mode2_ff_fast_and_inverse_on_baseline": (
            "ssd1681_official_strong_full_candidate_activation(" not in panel
            and "Do not replace with Mode-2 Fast" in playbook
            and "Do not seed lifecycle `old_plane=inverse_target`" in playbook
            and "ordinary `0xCF`" in playbook
            and "要走全刷不要走快刷" in playbook
        ),
        "recording_exit_home_uses_single_local_partial": (
            "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE" in recording_stop
            and "Companion_Display_EmitAccessoryFrameEx(" in recording_stop
            and "refresh=single_cached_mode2_0xcf" in recording_stop
            and "Companion_Screen_RecordingStopFeedbackInFlight()"
                in recording_stop
            and "Companion_Display_EnterDailyMotion" not in recording_stop
        ),
        "home_choreography_has_no_periodic_full": (
            "comp_epaper_refresh_policy_init(&s_target_context.refresh_policy,"
            in panel
            and "UINT8_MAX" in panel
        ),
        "ordinary_choreography_replays_r37_source_complete_coverage": (
            "ssd1681_product_source_complete_window(" in panel
            and "&window, &coverage_candidate, &window" in panel
            and "coverage_window" not in panel
            and "comp_epaper_refresh_coverage_expand(" in panel
            and "ssd1681_product_stage_region_excluding(" in panel
            and "if (!natural_blink_frame)" not in panel
            and "s_ordinary_refresh_coverage = coverage_candidate;" in panel
            and "comp_epaper_refresh_coverage_reset(" in product
        ),
        "blink_uses_independent_control_and_clean_face_physical_track": (
            "window.changed && natural_blink_frame" not in panel
            and "Replay the accepted r37 physical face path" in panel
            and "ssd1681_product_stage_region_excluding(" in panel
            and "functional_delta_windows[functional_delta_count++] =\n"
                "                blink_regions[eye];" not in panel
            and "comp_screen_composition_snapshot(" in blink_emit
            and "comp_emote_player_play_now_name(" not in blink_emit
            and "player_mutated=0" in blink_emit
            and "after subtracting independent functional\n"
                "  regions" in playbook
            and "single-current-plane face path" in playbook
        ),
        "blink_open_previous_plane_normalization_is_nonvisible": (
            "if (ok && natural_blink_frame && !natural_blink_closed)"
                in cached_mode2
            and "0x26u, s_frame, &sync_regions[index]" in cached_mode2
            and "report->post_sync_command = 0x26u;" in cached_mode2
            and "cannot run after close" in playbook
            and "cannot add a visible activation" in playbook
        ),
        "blink_reopens_in_first_post_commit_slot": (
            "#define COMP_EPAPER_NATURAL_BLINK_CLOSED_HOLD_MS 0u" in blink_header
            and "now_ms + COMP_EPAPER_NATURAL_BLINK_CLOSED_HOLD_MS" in blink_scheduler
            and "Companion_Display_DispatchBlinkOpenAfterClosedCommit" not in app
            and display_task.count("Companion_Display_ServicePostBusyArbiter(") == 1
            and "s_companion_post_busy_arbiter_active" in post_busy_arbiter
            and "Companion_Display_ProcessDueTracks(" not in post_busy_arbiter
            and "Companion_Display_ServicePublishedTracks(completed_class);"
                in post_busy_arbiter
            and "COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_TIMER" in published_tracks
            and "Companion_CompReq775RecordingTrackPending()" in published_tracks
            and "Companion_Display_ProcessDueTracks(" not in published_tracks
            and "s_companion_blink_scheduler.open_pending" in automatic_motion
            and "comp_epaper_natural_blink_take_due(" in automatic_motion
            and "Companion_Display_EmitNaturalBlinkFrame(" in automatic_motion
            and "s_companion_blink_open_enqueued_ms = HAL_GetTick();"
            in automatic_motion
            and "[screen-blink] pair closed_request=" in app
            and "queue_gap_ms=" in app
            and "closed_to_open_ms=" in app
            and "defer_panel_trace" in panel
            and "Companion_Display_ScheduleExpressionTick(visible_ms);"
            in display_task
            and "comp_epaper_natural_blink_complete_open(" in display_task
            and "next_due_in_ms=" in display_task
            and "visible_ms + (uint32_t)interval_commits * scheduler->cadence_ms"
            in blink_scheduler
        ),
        "blink_uses_owner_accepted_sparse_browser_cadence": (
            "const BLINK_FIRST_INTERVAL_COMMITS = 24;" in page
            and "const BLINK_INTERVAL_COMMITS = Object.freeze([24, 32, 40]);"
                in page
            and "`24/32/40` commits" in playbook
        ),
        "blink_pixels_replay_owner_accepted_cemp_state_pair": (
            "SSD1681_BROWSER_BLINK_OPEN_STATE_HASH 0x96C7864Au" in panel
            and "SSD1681_BROWSER_BLINK_CLOSED_STATE_HASH 0xF476300Eu" in panel
            and blink_compose.count(
                "comp_epaper_expression_asset_source_copy_state("
            ) == 2
            and "ssd1681_blink_bounds_add" in blink_compose
            and "source=r37_cemp_state_pair" in blink_compose
            and "`42,93..74,137`" in playbook
            and "`125,93..160,139`" in playbook
            and "companion_browser_blink_authored_closed_eye_pixels" not in blink_compose
            and blink_bounds == [[42, 93, 74, 137], [125, 93, 160, 139]]
        ),
        "blink_clock_survives_transient_home_work": (
            "COMP_EPAPER_MOTION_CANCEL_TOUCH" in cancel_motion
            and "COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY" in cancel_motion
            and "blink_clock=%s" in cancel_motion
            and "if (!s_companion_blink_scheduler.awake)" in enter_daily
            and "scheduler=preserved" in enter_daily
        ),
        "recording_waveform_declares_highest_480ms_tier": (
            "COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_CADENCE_MS" in app
            and "recording_overlay_only" in panel
            and "comp_epaper_overlay_commit_scheduler_complete" in app
            and "COMP_EPAPER_OVERLAY_COMMIT_IN_FLIGHT" in overlay_scheduler
            and "s_companion_recording_overlay_next_ms" not in app
            and "144 bytes" in playbook
            and "tier reference, not added dwell" in playbook
        ),
        "playbook_records_rejected_full_and_blink_paths": all(
            token in playbook
            for token in (
                "Mode-1 GC `0xC7` 全刷",
                "Mode-2 Fast `0xFF` 快刷",
                "要走全刷不要走快刷",
                "accepted r37 physical baseline grows one source-complete face coverage epoch",
                "hard-coded 4200-byte content tier",
            )
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.epaper_refresh_playbook.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "blink_state_pair": {
            "open_sha256": hashlib.sha256(BLINK_OPEN.read_bytes()).hexdigest().upper(),
            "closed_sha256": hashlib.sha256(BLINK_CLOSED.read_bytes()).hexdigest().upper(),
            "difference_bounds": blink_bounds,
        },
        "hardware_contact": 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
