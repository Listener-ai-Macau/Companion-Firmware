#!/usr/bin/env python3
"""Mutation coverage for the focused COMP-REQ-775 machine gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "tools" / "verify_comp_req_775_recording_lp_race.py"
spec = importlib.util.spec_from_file_location("recording_lp_race", VERIFIER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture() -> list[str]:
    rows = [
        "[record] gatt_live_mic_start action=start source=3 result=0 state=recording",
        "[record-visual] action=overlay_start result=1 tracks=wave_authored_life_independent",
    ]
    visible = 1000
    for index in range(10):
        rows.append("[epaper] mic_local_partial only=1")
        rows.append(
            f"[record-phase] track=wave request={index} "
            f"due_source=recording_scheduler visible_ms={visible} only=1 "
            "carrier=pure_wave face_clock_advanced=0 accessory_clock_advanced=0")
        visible += 480
        if index in {2, 7}:
            rows.append(
                f"[record-visual] authored_life_enqueue request={index} "
                "due_source=authored_absolute_deadline wave_drives_life=0 "
                "life_drives_wave=0 ornaments_follow_authored_life=1")
            rows.append(
                f"[record-phase] track=face request={index} "
                f"due_source=authored_absolute_deadline visible_ms={visible} "
                "wave_carried=1 wave_drives_face=0")
        rows.append(
            f"[accessory-clock] track=charging request={index} "
            "due_source=charging_wall_clock wave_clock_advanced=0 "
            "life_clock_advanced=0 blink_clock_advanced=0")
    rows.extend([
        "[screen-blink] phase=closed request=20 due_source=blink_scheduler "
        "wave_drives_blink=0 blink_drives_wave=0",
        "[record-phase] track=blink request=20 due_source=blink_scheduler "
        "visible_ms=5800 wave_carried=1 wave_drives_blink=0 blink_drives_wave=0",
        "[rec-flash] stored id=1 bytes=100 duration_ms=5000 codec=3 frames=1 drops=0",
        "[record-visual] action=stop_queue result=1 request=50",
        "[epaper] accepted_product_driver request=50 control=0xCF partial_before=20 result=1",
        "[record-visual] action=stop_commit request=50 control=0xCF",
        "[epaper] accepted_product_driver request=51 control=0xCF partial_before=21 result=1",
        "[watchdog] healthy=1 stalled_mask=0x00",
        "[watchdog] healthy=1 stalled_mask=0x00",
    ])
    return rows


def must_fail(lines: list[str], check: str) -> None:
    result = module.analyze(lines)
    assert result["status"] == "NO_GO", result
    assert check in result["failed_checks"], result


def idle_fixture() -> list[str]:
    return [
        # Normal runtime refreshes before the idle boundary are deliberately
        # outside the LP-entry transaction and must not poison that verdict.
        "[epaper] accepted_product_driver control=0xFF result=1",
        "[power] low_power_idle_timer=armed delay_ms=180000 source=rtc_ts",
        "[screen] low_power_boundary=enter control=0xC7",
        "[epaper] accepted_product_driver reason=7 control=0xC7 "
        "window=0-24,0-199 bytes=5000 previous_plane_sync=1 "
        "post_sync_command=0x24 post_sync_bytes=10000 result=1",
        "[screen] low_power_idle freeze=committed quiet=1 life=0 blink=0 "
        "wave=0 accessory=0 tick=stopped arbiter=0",
        "[watchdog] healthy=1 stalled_mask=0x00",
        "[watchdog] healthy=1 stalled_mask=0x00",
    ]


def main() -> int:
    base = fixture()
    result = module.analyze(base)
    assert result["status"] == "MACHINE_READY", result
    assert result["counts"]["wave_recovered_from_blink_receipt"] == 1, result

    board_summary = list(base)
    stop = board_summary.index(
        "[record-visual] action=stop_queue result=1 request=50")
    board_summary.insert(
        stop,
        "[rec-gap] n=11 g=10 o=0 m=480 p=1 f=2 b=1 x=0")
    result = module.analyze(board_summary)
    assert result["status"] == "MACHINE_READY", result
    assert result["counts"]["wave_gap_summary"] == 1, result
    malformed_visible = [
        line.replace("visible_ms=1000", "visible_ms=lock_advanced=0")
        for line in board_summary
    ]
    result = module.analyze(malformed_visible)
    assert result["status"] == "MACHINE_READY", result
    malformed_watchdog = [
        line.replace("stalled_mask=0x00", "stalled_mask=0x00=3808", 1)
        for line in board_summary
    ]
    result = module.analyze(malformed_watchdog)
    assert result["status"] == "MACHINE_READY", result
    bad_board_summary = [
        line.replace("o=0 m=480 p=1", "o=2 m=900 p=0")
        for line in board_summary
    ]
    must_fail(bad_board_summary, "wave_fastest_available_partial_lane")

    slow_shared_carrier = [
        line.replace("visible_ms=5800 wave_carried=1",
                     "visible_ms=6000 wave_carried=1")
        for line in base
    ]
    must_fail(slow_shared_carrier, "wave_fastest_available_partial_lane")

    corrupted_face_deadline = [
        line.replace("track=face request=2 due_source=authored_absolute_deadline",
                     "track=face request=2 due_source=authored_a171")
        for line in base
    ]
    result = module.analyze(corrupted_face_deadline)
    assert result["status"] == "MACHINE_READY", result
    assert result["counts"]["face_recovered_from_life_receipt"] == 1, result

    no_charger = [line for line in base if "[accessory-clock]" not in line]
    result = module.analyze(no_charger)
    assert result["status"] == "MACHINE_READY", result
    assert result["counts"]["authored_ornament_clock_safe"] == 1, result
    active_charger_without_clock = [
        line.replace("due_source=blink_scheduler wave_drives_blink=0",
                     "due_source=blink_scheduler charging=1 "
                     "wave_drives_blink=0")
        for line in no_charger
    ]
    must_fail(active_charger_without_clock, "accessory_clock_independent")

    boundary_blink = list(base)
    source = boundary_blink.index(
        "[screen-blink] phase=closed request=20 due_source=blink_scheduler "
        "wave_drives_blink=0 blink_drives_wave=0")
    boundary_blink[source] = (
        "[screen-blink] phase=open request=20 due_source=blink_scheduler "
        "wave_drives_blink=0 blink_drives_wave=0")
    boundary_blink.insert(1,
        "[record-visual] action=pending_start expression=recording result=1")
    boundary_blink.insert(2, boundary_blink.pop(source + 1))
    result = module.analyze(boundary_blink)
    assert result["status"] == "MACHINE_READY", result

    missing_blink_source = [line for line in base
                            if "[screen-blink] phase=" not in line]
    must_fail(missing_blink_source, "blink_clock_independent_if_due")

    interleaved_uart = [
        line.replace(
            "[record] gatt_live_mic_start action=start source=3 result=0 state=recording",
            "[record] touch_double_tap action=start source=2 result=0 "
            "state=recordin=recording result=already_visible")
        for line in base
    ]
    result = module.analyze(interleaved_uart)
    assert result["status"] == "MACHINE_READY", result

    split_store_uart = []
    for line in base:
        if "[rec-flash] stored" in line:
            split_store_uart.extend([
                "[rec-flash] stored id=1 bytes=100 duration_ms=50[uart-splice]",
                "00 codec=3 frames=1 drops=0 crc=0x12345678",
            ])
        else:
            split_store_uart.append(line)
    result = module.analyze(split_store_uart)
    assert result["status"] == "MACHINE_READY", result
    assert result["checks"]["codec3_stored_without_drops"], result

    missing_wave_receipt = [line for line in base
                            if "track=wave request=2 " not in line]
    missing_wave_receipt = [
        line.replace("visible_ms=2440 wave_carried=1",
                     "visible_ms=1960 wave_carried=1")
        for line in missing_wave_receipt
    ]
    result = module.analyze(missing_wave_receipt)
    assert result["status"] == "MACHINE_READY", result
    assert result["counts"]["wave_recovered_from_face_receipt"] == 1, result

    low_power = list(base)
    low_power.insert(8, "[screen] low_power_boundary=enter control=0xF7")
    must_fail(low_power, "recording_interval_has_no_low_power_or_full_refresh")
    product_low_power = list(base)
    product_low_power.insert(
        8, "[screen] boundary_enqueue reason=low_power_idle refresh=6")
    must_fail(product_low_power,
              "recording_interval_has_no_low_power_or_full_refresh")

    coupled = [line.replace("wave_drives_face=0", "wave_drives_face=1")
               for line in base]
    must_fail(coupled, "face_authored_clock_independent")

    double_full = list(base)
    stop = double_full.index("[record-visual] action=stop_commit request=50 control=0xCF")
    double_full.insert(stop, "[epaper] accepted_product_driver control=0xC7")
    must_fail(double_full, "stop_exactly_one_local_cf")

    stale_epoch = [line.replace("control=0xCF partial_before=21",
                                "control=0xCF partial_before=0")
                   for line in base]
    must_fail(stale_epoch, "next_panel_remains_cf_without_lifecycle_reset")

    unhealthy = list(base)
    unhealthy[-1] = "[watchdog] healthy=0 stalled_mask=0x04"
    must_fail(unhealthy, "watchdog_healthy_and_no_fault")

    idle = module.analyze_idle(idle_fixture())
    assert idle["status"] == "MACHINE_READY", idle
    product_idle = [
        line.replace("[screen] low_power_boundary=enter control=0xC7",
                     "[screen] boundary_enqueue reason=low_power_idle "
                     "refresh=6")
        for line in idle_fixture()
    ]
    idle = module.analyze_idle(product_idle)
    assert idle["status"] == "MACHINE_READY", idle
    self_wake = idle_fixture() + ["[screen] low_power_boundary=wake"]
    idle = module.analyze_idle(self_wake)
    assert idle["status"] == "NO_GO"
    assert "idle_does_not_self_wake" in idle["failed_checks"]
    post_freeze_panel = idle_fixture() + [
        "[epaper] accepted_product_driver control=0xCF result=1"]
    idle = module.analyze_idle(post_freeze_panel)
    assert idle["status"] == "NO_GO"
    assert "no_panel_work_after_freeze" in idle["failed_checks"]
    lp_window_ff = idle_fixture()
    lp_window_ff.insert(3,
        "[epaper] accepted_product_driver control=0xFF result=1")
    idle = module.analyze_idle(lp_window_ff)
    assert idle["status"] == "NO_GO"
    assert "idle_uses_exactly_one_white_dwell_wake_and_no_ff" in idle["failed_checks"]

    print("PASS: recording/LP race oracle accepts product trace and rejects "
          "LP, coupled-face, double-full, stale-epoch, watchdog, self-wake, "
          "and post-freeze-panel mutants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
