#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_comp_req_775_screen_final.py")
SPEC = importlib.util.spec_from_file_location("screen_final", MODULE_PATH)
assert SPEC and SPEC.loader
screen_final = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen_final)

CAPTURE_MODULE_PATH = Path(__file__).with_name(
    "capture_comp_req_775_touch_recording.py")
CAPTURE_SPEC = importlib.util.spec_from_file_location(
    "touch_capture", CAPTURE_MODULE_PATH)
assert CAPTURE_SPEC and CAPTURE_SPEC.loader
touch_capture = importlib.util.module_from_spec(CAPTURE_SPEC)
CAPTURE_SPEC.loader.exec_module(touch_capture)


DRIVER = r"""
static bool ssd1681_lifecycle_mode1_gc_full_activation_ex(
    const uint8_t *frame, size_t frame_bytes, void *report,
    bool force_cold_reset, bool contrast_restore_from_white,
    bool force_inverse_old_plane, bool inline_mode2_settle_requested)
{
    const uint8_t full_update = 0xC7u;
    if (force_inverse_old_plane) {
        for (size_t index = 0u; index < SSD1681_FRAME_BYTES; ++index) {
            s_blink_closed_frame[index] = (uint8_t)~s_frame[index];
        }
    } else if (contrast_restore_from_white) {
        memset(s_blink_closed_frame, 0xFFu, SSD1681_FRAME_BYTES);
    }
    ssd1681_reset();
    ssd1681_write_plane_region(0x26u, s_blink_closed_frame, &window);
    ssd1681_write_plane_region(0x24u, s_frame, &window);
    ssd1681_command_data(0x22u, &full_update, sizeof(full_update));
    if (rebaseline_complete && force_inverse_old_plane) {
        printf("[epaper] lp_skip_mode2_rearm control_0x99=0 "
               "initial_display_stage=0 direct_deep_sleep=1");
    } else {
        ssd1681_accepted_mode2_rearm(NULL);
    }
    return true;
}

static comp_epaper_panel_result_t ssd1681_accepted_cached_mode2_product_refresh(
    void *target, const void *request, void *out_report)
{
    if (strong_idle_enter_refresh) {
        s_need_mode2_settle_after_mode1_gc = false;
        ok = ssd1681_lifecycle_mode1_gc_full_activation_ex(
            s_frame, sizeof(s_frame), &report, true, false, true, false);
        printf("[epaper] lp_enter_inverse_old_c7 control=0xC7");
        s_need_mode2_settle_after_mode1_gc = false;
    } else if (first_frame || visible_full_refresh || maintenance_refresh) {
        ok = ssd1681_lifecycle_mode1_gc_full_activation_ex(
            s_frame, sizeof(s_frame), &report, force_cold, false, false, false);
    }
    return ok;
}
"""


def good_log(duration: int = 12000, p95_gap: int = 600) -> str:
    lines = [
        "[screen-life] enter family=calm cadence_ms=480 at=1",
    ]
    for i in range(6):
        lines.append("[screen-life] family=calm action=rest episode=0 "
                     f"phrase={i % 3} phase=hold dwell_commits={(i % 4) + 1} "
                     f"frame_index={100 + i}")
    lines += [
        "[screen-blink] phase=closed due_source=blink_scheduler "
        "wave_drives_blink=0 blink_drives_wave=0",
        "[screen-blink] phase=open due_source=blink_scheduler "
        "wave_drives_blink=0 blink_drives_wave=0",
        "[record-visual] option2=1 hold_face=0 face_clock=authored_daily_life "
        "same_as_offline=1 blink_clock=independent accessory_clock=independent "
        "no_soft_advance=1 no_cross_track_advance=1 no_full_refresh=1 "
        "cadence_ms=480",
        "[record-visual] action=overlay_start result=1 "
        "initial_dispatch=wave_bootstrap post_commit_dwell_ms=0 "
        "no_predeadline_wave_suppression=1 "
        "tracks=wave_authored_life_independent",
        screen_final.START_TOKEN,
    ]
    visible = 1000
    for i in range(20):
        carrier = "pure_wave"
        only = "1"
        lines.append("[record-phase] track=wave "
                     f"request={3758096400 + i} "
                     "due_source=recording_scheduler "
                     f"visible_ms={visible} only={only} carrier={carrier} "
                     "face_clock_advanced=0 accessory_clock_advanced=0")
        lines.append("[record-visual] action=overlay_trace visible=1 control=0xCF "
                     "post_commit_dwell_ms=0 dropped=0")
        if i in {2, 5, 8, 11, 14, 17}:
            lines += [
                "[record-phase] track=face due_source=authored_absolute_deadline "
                f"visible_ms={visible} wave_carried=0 wave_drives_face=0",
                "[record-visual] authored_life_enqueue "
                "due_source=authored_absolute_deadline wave_drives_life=0 "
                "life_drives_wave=0 ornaments_follow_authored_life=1",
                "[screen-life] family=calm action=notice_right episode=1 "
                f"phrase={i % 3} phase=accent dwell_commits={(i % 4) + 1} "
                f"frame_index={200 + i}",
            ]
        if i in {1, 6}:
            lines.append("[accessory-clock] due_source=charging_wall_clock "
                         "wave_clock_advanced=0 life_clock_advanced=0 "
                         "blink_clock_advanced=0")
        visible += p95_gap
    lines += [
        "[rec-flash] live_hot blocks=1000 drops=0 depth=0",
        "[record] touch_double_tap action=stop source=2 stop_result=0 "
        "finish_result=0 state=transfer_ready",
        f"[rec-flash] stored id=1 bytes=40000 duration_ms={duration} drops=0",
        "[epaper] accepted_product_driver control=0xCF partial_before=140 result=1",
        "[screen] boundary_enqueue reason=low_power_idle refresh=6",
        "[epaper] lp_enter_skip_functional_compose recording=0 charger=0 "
        "blink=0 pure_sleepy=1",
        "[epaper] accepted_gc_full control=0xC7 complete=1 "
        "inverse_old=1 old_source=inverse_target_lp",
        "[epaper] lp_skip_mode2_rearm control_0x99=0 "
        "initial_display_stage=0 direct_deep_sleep=1",
        "[epaper] lp_enter_inverse_old_c7 control=0xC7 activation_count=1 "
        "inverse_old=1 deferred_settle=0 complete=1",
        "[epaper] accepted_product_driver changed=1 control=0xC7 reason=7 "
        "partial_before=158 result=1",
        "[screen] low_power_idle freeze=committed quiet=1 life=0 blink=0 "
        "wave=0 accessory=0",
    ]
    lines += ["[watchdog] healthy=1 stalled_mask=0x00" for _ in range(3)]
    return "\n".join(lines) + "\n"


class ScreenFinalVerifierTest(unittest.TestCase):
    def run_case(self, log: str, lifecycle_log: str | None = None,
                 scheduler_log: str | None = None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log_path = root / "serial.log"
            driver_path = root / "driver.c"
            bin_path = root / "app.bin"
            ota_path = root / "ota.json"
            lifecycle_path = root / "lifecycle.log"
            scheduler_path = root / "scheduler.log"
            log_path.write_text(log, encoding="utf-8")
            driver_path.write_text(DRIVER, encoding="utf-8")
            bin_path.write_bytes(b"firmware")
            ota_path.write_text(json.dumps({
                "status": "MACHINE_READY",
                "checks": {"inside_app": True, "vector_valid": True},
            }), encoding="utf-8")
            if lifecycle_log is not None:
                lifecycle_path.write_text(lifecycle_log, encoding="utf-8")
            if scheduler_log is not None:
                scheduler_path.write_text(scheduler_log, encoding="utf-8")
            return screen_final.analyze(
                log_path, driver_path, bin_path,
                screen_final.sha256(b"firmware"), ota_path,
                lifecycle_log_path=(lifecycle_path
                                    if lifecycle_log is not None else None),
                scheduler_log_path=(scheduler_path
                                    if scheduler_log is not None else None))

    def test_complete_log_is_machine_ready(self):
        result = self.run_case(good_log())
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertEqual([], result["failed_checks"])
        self.assertEqual(1, result["low_power"]["inverse_old_activations"])
        self.assertEqual(1, result["low_power"]["sleepy_paint_activations"])

    def test_short_recording_and_slow_wave_are_rejected(self):
        result = self.run_case(good_log(duration=6500, p95_gap=800))
        self.assertEqual("NO_GO", result["status"])
        self.assertIn("recording_is_at_least_minimum_and_drop_free",
                      result["failed_checks"])
        self.assertIn("wave_uses_first_available_slots", result["failed_checks"])

    def test_wave_driven_face_is_rejected(self):
        log = good_log().replace("wave_carried=0 wave_drives_face=0",
                                 "wave_carried=0 wave_drives_face=1", 1)
        result = self.run_case(log)
        self.assertEqual("NO_GO", result["status"])
        self.assertIn("face_uses_authored_clock_not_wave_clock",
                      result["failed_checks"])

    def test_post_freeze_panel_commit_is_rejected(self):
        log = good_log() + "[epaper] accepted_product_driver control=0xCF result=1\n"
        result = self.run_case(log)
        self.assertEqual("NO_GO", result["status"])
        self.assertIn("lp_freeze_stops_all_screen_tracks",
                      result["failed_checks"])

    def test_watchdog_boot_rows_are_not_unhealthy_samples(self):
        log = ("[watchdog] boot_handoff=reload_if_running owner=watchdog_task\n"
               "[watchdog] previous_reset=none\n" + good_log())
        result = self.run_case(log)
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertEqual(3, result["stability"]["watchdog_rows"])
        self.assertEqual(0, result["stability"]["unhealthy_watchdog_rows"])

    def test_recording_and_lifecycle_may_be_consecutive_captures(self):
        complete = good_log()
        boundary = complete.index("[epaper] accepted_product_driver control=0xCF")
        recording = complete[:boundary]
        lifecycle = complete[:complete.index(screen_final.START_TOKEN)] + complete[boundary:]
        result = self.run_case(recording, lifecycle)
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertNotEqual(result["identity"]["log_sha256"],
                            result["identity"]["lifecycle_log_sha256"])

    def test_uart_spliced_wave_timestamp_does_not_invent_a_gap(self):
        log = good_log().replace(
            "visible_ms=3400 only=1 carrier=pure_wave",
            "only=1 carrier=pure_wave", 1)
        result = self.run_case(log)
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertGreaterEqual(result["recording"]["wave_parse_fraction"], 0.90)

    def test_explicit_cross_clock_advance_is_never_treated_as_uart_splice(self):
        log = good_log().replace("face_clock_advanced=0",
                                 "face_clock_advanced=1", 1)
        result = self.run_case(log)
        self.assertEqual("NO_GO", result["status"])
        self.assertIn("wave_uses_first_available_slots", result["failed_checks"])

    def test_diagnostic_trace_ring_loss_is_not_a_display_frame_drop(self):
        log = good_log().replace("dropped=0", "dropped=17")
        result = self.run_case(log)
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertEqual(17,
                         result["recording"]["overlay_trace_buffer_dropped_max"])

    def test_uart_spliced_accessory_row_does_not_invent_cross_clock(self):
        marker = "[rec-flash] live_hot blocks=1000 drops=0 depth=0"
        log = good_log().replace(
            marker,
            "[accessory-clock] track=charging due_sou[record-phase] "
            "wave_clock_advanced=0 life_clock_advanced=0 "
            "blink_clock_advanced=0\n" + marker)
        result = self.run_case(log)
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertEqual(2, result["independent_tracks"]
                         ["recording_accessory_complete_rows"])
        self.assertEqual(1, result["independent_tracks"]
                         ["recording_accessory_uart_spliced_rows"])

    def test_explicit_accessory_cross_clock_is_rejected(self):
        log = good_log().replace("wave_clock_advanced=0 life_clock_advanced=0",
                                 "wave_clock_advanced=1 life_clock_advanced=0",
                                 1)
        result = self.run_case(log)
        self.assertEqual("NO_GO", result["status"])
        self.assertIn("accessory_clock_is_independent_during_recording",
                      result["failed_checks"])

    def test_explicit_runtime_dwell_is_rejected(self):
        log = good_log().replace("post_commit_dwell_ms=0 dropped=0",
                                 "post_commit_dwell_ms=1 dropped=0", 1)
        result = self.run_case(log)
        self.assertEqual("NO_GO", result["status"])
        self.assertIn("wave_uses_first_available_slots", result["failed_checks"])

    def test_scheduler_probe_is_auxiliary_not_touch_substitution(self):
        result = self.run_case(good_log(), scheduler_log=good_log())
        self.assertEqual("MACHINE_READY", result["status"])
        self.assertEqual("MACHINE_READY_SCHEDULER_ONLY",
                         result["scheduler_auxiliary"]["status"])
        self.assertIn("does not replace", result["scheduler_auxiliary"]["note"])

    def test_touch_capture_patterns_reject_pending_and_accept_real_edges(self):
        self.assertIsNone(touch_capture.START_PATTERN.search(
            "[record] touch_double_tap action=start source=2 result=2 "
            "state=pending_start"))
        self.assertIsNotNone(touch_capture.START_PATTERN.search(
            screen_final.START_TOKEN))
        self.assertIsNotNone(touch_capture.STOP_PATTERN.search(
            "[record] touch_double_tap action=stop source=2 stop_result=0 "
            "finish_result=0 state=transfer_ready"))


if __name__ == "__main__":
    unittest.main()
