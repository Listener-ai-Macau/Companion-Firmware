#!/usr/bin/env python3
"""Fail-closed gate for COMP-REQ-775 accepted deep-scrub LP entry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
APP = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
MOTION = ROOT / "app/companion_pendant/epaper/motion_coordinator.c"
R62_STATIC = ROOT / ".cache/validation/comp775-independent-choreography-r62-final-20260810/evidence/r61-static.json"
# r70 changed only menu intent/partial-refresh handling after r62 recording
# acceptance. Recording runtime invariants below remain fail-closed and reuse
# the 180-second real-board evidence; LP work must preserve this exact descendant.
R70_APP_SHA256 = "57E83DC198E2D0CAF0F44490F0C2AA431D2988EE0B851244ED49FAA138620DC9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ordered(text: str, tokens: list[str]) -> bool:
    cursor = 0
    for token in tokens:
        cursor = text.find(token, cursor)
        if cursor < 0:
            return False
        cursor += len(token)
    return True


def count(text: str, token: str) -> int:
    return text.count(token)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--natural-log", type=Path, required=True)
    parser.add_argument("--recording-log", type=Path, required=True)
    parser.add_argument("--ble", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--hex", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    driver = DRIVER.read_text(encoding="utf-8")
    start = driver.index("if (strong_idle_enter_refresh) {")
    end = driver.index("} else if (first_frame", start)
    lp = driver[start:end]
    natural = args.natural_log.read_text(encoding="utf-8", errors="replace")
    recording = args.recording_log.read_text(encoding="utf-8", errors="replace")
    ble = json.loads(args.ble.read_text(encoding="utf-8-sig"))
    layout = json.loads(args.layout.read_text(encoding="utf-8-sig"))
    sealed = json.loads(R62_STATIC.read_text(encoding="utf-8-sig"))["source"]

    freeze_at = natural.find("low_power_idle freeze=committed quiet=1")
    post_freeze = natural[freeze_at:] if freeze_at >= 0 else natural
    lp_elapsed_at = natural.find("low_power_idle_timer=elapsed")
    if lp_elapsed_at < 0:
        # The product RTC timer logs its accepted screen boundary instead of
        # the diagnostic HAL-tick "elapsed" marker.
        lp_elapsed_at = natural.find("[screen] low_power_boundary=enter")
    lp_runtime = natural[lp_elapsed_at:freeze_at if freeze_at >= 0 else len(natural)]
    overlay_at = recording.rfind("action=overlay_start result=1")
    stop_at = recording.find("gatt_recording_stop action=user_store result=1", max(overlay_at, 0))
    active = recording[max(overlay_at, 0):stop_at if stop_at >= 0 else len(recording)]
    stored = re.findall(
        r"\[rec-flash\] stored .*?duration_ms=(\d+).*?drops=(\d+)", recording)
    stored_duration = max((int(row[0]) for row in stored), default=0)
    stored_drops = max((int(row[1]) for row in stored), default=-1)

    checks = {
        "r70_app_source_descendant_unchanged": sha256(APP) == R70_APP_SHA256,
        "r62_main_source_unchanged": sha256(MAIN) == sealed["main_sha256"],
        "r62_motion_source_unchanged": sha256(MOTION) == sealed["motion_sha256"],
        "lp_static_restores_accepted_enter_only_deep_scrub": ordered(lp, [
            "s_need_mode2_settle_after_mode1_gc = false;",
            "ssd1681_lifecycle_lp_enter_freeze_clean(",
            "s_frame, sizeof(s_frame), &report);",
            "s_need_mode2_settle_after_mode1_gc = false;",
        ]),
        "lp_static_has_no_c7_ff_or_cf_after_deep_scrub": (
            lp.count("s_need_mode2_settle_after_mode1_gc = false;") >= 2
            and "ssd1681_lifecycle_mode1_gc_full_activation_ex(" not in lp
            and "ssd1681_lifecycle_mode2_fast_full_activation(" not in lp
            and "ssd1681_cached_mode2_diff_internal(" not in lp
        ),
        "natural_boundary_is_pure_sleepy": "full_refresh=1 pure_sleepy=1 no_mic=1" in natural,
        "natural_skips_all_functional_compose": "lp_enter_skip_functional_compose recording=0 charger=0 blink=0 pure_sleepy=1" in natural,
        "natural_enter_physically_scrubs_black_then_white": (
            "lp_enter_step=black_white control=0xF7" in lp_runtime
            and "physical=1 cold_reset=1" in lp_runtime
            and "result=1/1" in lp_runtime
        ),
        "natural_enter_paints_target_cf_regions_from_clean_white": (
            "lp_enter_f7f7cf white=1 target=1 base=1" in lp_runtime
            and "exact_delta_bands regions=" in lp_runtime
            and any(
                int(value) < 3000
                for value in re.findall(
                    r"accepted_product_driver .*?control=0xCF .*?bytes=(\d+)",
                    lp_runtime,
                )
            )
        ),
        "natural_lp_has_one_target_cf_and_no_c7_or_ff": (
            count(lp_runtime, "lp_enter_f7f7cf") == 1
            and count(lp_runtime, "control=0xCF") == 1
            and "control=0xC7" not in lp_runtime
            and "control=0xFF" not in lp_runtime
            and "accepted_fast_full" not in lp_runtime
            and "accepted_gc_full" not in lp_runtime
        ),
        "natural_freeze_stops_all_tracks": "quiet=1 life=0 blink=0 wave=0 accessory=0 tick=stopped arbiter=0" in natural,
        "natural_has_no_post_freeze_paint": freeze_at >= 0 and "accepted_product_driver" not in post_freeze,
        "natural_watchdog_healthy_after_freeze": freeze_at >= 0 and "[watchdog] healthy=1" in post_freeze,
        "natural_has_no_watchdog_feed_stop": "[watchdog] feed=stopped" not in natural,
        "natural_has_no_hardfault_or_panel_failure": (
            "HARDFAULT" not in natural
            and "lp_enter_f7f7cf white=1 target=1 base=1" in lp_runtime
        ),
        "real_ble_start_stop_pass": ble.get("status") == "PASS_REAL_RADIO" and all(
            any(op.get("operation") == name and op.get("status") == "PASS" for op in ble.get("operations", []))
            for name in ("recording_control_start_write", "recording_control_stop_write")
        ),
        "recording_start_stop_and_store_complete": (
            "gatt_live_mic_start action=start source=3 result=0 state=recording" in recording
            and "gatt_recording_stop action=user_store result=1 state=idle" in recording
            and stored_duration >= 9000 and stored_drops == 0
        ),
        "recording_wave_keeps_fastest_track": count(active, "[record-phase] track=wave") >= 20 and count(active, "mic_local_partial only=1") >= 10,
        "recording_face_remains_authored_independent": count(active, "[record-phase] track=face") >= 5 and count(active, "due_source=authored_absolute_deadline") >= 5 and count(active, "wave_drives_face=0") >= 5,
        "recording_blink_and_accessory_remain_independent": count(active, "[record-phase] track=blink") >= 2 and count(active, "[accessory-clock]") >= 1,
        "recording_uses_isolated_one_busy_carriers": count(active, "authored_plus_wave_isolated_bands") >= 5 and "authored_plus_wave_source_complete" not in active,
        "recording_has_no_full_refresh_or_fault": "control=0xF7" not in active and "control=0xC7" not in active and "HARDFAULT" not in recording,
        "recording_watchdog_healthy": "[watchdog] healthy=1" in active,
        "ota_app_layout_valid": layout.get("status") == "MACHINE_READY" and layout.get("maximum_address_exclusive", "") <= "0x08080000",
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp775.lp_enter_deep_scrub_f7_f7_cf_exact_bands.v11",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "identity": {
            "bin_sha256": sha256(args.bin),
            "hex_sha256": sha256(args.hex),
            "driver_sha256": sha256(DRIVER),
            "app_sha256": sha256(APP),
            "maximum_address_exclusive": layout.get("maximum_address_exclusive"),
        },
        "runtime": {
            "lp_deep_scrub_total_ms": [int(v) for v in re.findall(r"lp_enter_f7f7cf .*?total=(\d+)", lp_runtime)],
            "recording_duration_ms": stored_duration,
            "recording_drops": stored_drops,
            "wave_events": count(active, "[record-phase] track=wave"),
            "face_events": count(active, "[record-phase] track=face"),
            "blink_events": count(active, "[record-phase] track=blink"),
        },
        "evidence": {
            "natural_log": str(args.natural_log.resolve()),
            "recording_log": str(args.recording_log.resolve()),
            "ble": str(args.ble.resolve()),
        },
        "human_visual_required": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
