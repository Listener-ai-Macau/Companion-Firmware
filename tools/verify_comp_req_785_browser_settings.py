#!/usr/bin/env python3
"""Machine audit for COMP-REQ-785 persisted WB55 browser settings."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
APP = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
WATCHDOG = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/companion_rtos_watchdog.c"
OTA_LOADER_MAIN = ROOT / (
    "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/"
    "BLE/BLE_Ota/Core/Src/main.c"
)
APP_ENTRY = ROOT / (
    "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/"
    "BLE/BLE_p2pServer/Core/Src/app_entry.c"
)
PANEL = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MENU = ROOT / "app/companion_pendant/epaper/screen_menu.c"
STORE = ROOT / "app/companion_pendant/power/power_settings_store.c"
STORE_H = ROOT / "app/companion_pendant/power/power_settings_store.h"
POWER_TEST = ROOT / "app/companion_pendant/power/tests/test_power_policy.c"
TOUCH_TEST = ROOT / "app/companion_pendant/touch/tests/test_touch_visual_release.c"
TOUCH_SCRIPT = ROOT / "tools/test_touch_gesture_host.ps1"
LAYOUT = ROOT / ".cache/validation/build-nucleo/ota-app-layout-Companion_Nucleo_WB55RG_FreeRTOS.json"
DEFAULT_OUT = ROOT / ".cache/validation/comp785-browser-settings-20260816/MACHINE_READY.json"


def run_ps(script: str) -> dict[str, object]:
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / script)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    return {"status": "PASS" if proc.returncode == 0 else "FAIL",
            "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    sources = {
        "main": MAIN.read_text(encoding="utf-8"),
        "app": APP.read_text(encoding="utf-8"),
        "watchdog": WATCHDOG.read_text(encoding="utf-8"),
        "ota_loader_main": OTA_LOADER_MAIN.read_text(encoding="utf-8"),
        "app_entry": APP_ENTRY.read_text(encoding="utf-8"),
        "panel": PANEL.read_text(encoding="utf-8"),
        "menu": MENU.read_text(encoding="utf-8"),
        "store": STORE.read_text(encoding="utf-8"),
        "store_h": STORE_H.read_text(encoding="utf-8"),
        "power_test": POWER_TEST.read_text(encoding="utf-8"),
        "touch_test": TOUCH_TEST.read_text(encoding="utf-8"),
        "touch_script": TOUCH_SCRIPT.read_text(encoding="utf-8"),
    }
    maintenance = sources["app"].split(
        "bool Companion_Screen_ExpressionMaintenance(void)", 1)[1].split(
        "static void Companion_Screen_RefreshBleStatus(void)", 1)[0]
    maintenance_flat = " ".join(maintenance.split())
    silence_runtime = sources["main"].split(
        "raw_stats_t raw_stats = { 0 };", 1)[1].split(
        "/* Live-mic: push PCM to ring only", 1)[0]
    errors: list[str] = []
    fields = [
        "silent_auto_stop", "auto_reconnect", "clock_24_hour", "gaze_follow",
        "natural_blink", "recording_limit_minutes", "recorder_profile",
        "interaction_level", "quiet_hours", "time_zone_offset_minutes",
        "recording_gesture",
    ]
    consumer_contracts = {
        "silent_auto_stop": (
            "comp_power_settings_silence_tracker_step(" in sources["main"]
            and "s_recording_flash.deadline_tick_ms = HAL_GetTick();" in sources["main"]
        ),
        "auto_reconnect": "if (s_companion_browser_auto_reconnect)" in sources["app"],
        "clock_24_hour": (
            "comp_power_settings_display_hour(" in sources["main"]
            and "values.clock_24_hour ? 0x4000u : 0u" in sources["main"]
        ),
        "gaze_follow": (
            sources["main"].count("!s_screen_menu.browser.gaze_follow") >= 2
        ),
        "natural_blink": (
            "s_companion_browser_natural_blink = browser->natural_blink" in sources["app"]
            and "if (!s_companion_browser_natural_blink)" in sources["app"]
        ),
        "recording_limit_minutes": (
            sources["main"].count("comp_power_settings_recording_max_seconds(&values)") >= 2
        ),
        "recorder_profile": (
            "values->recorder_profile == 0u ? 500u : 1500u" in sources["store"]
            and "next.recorder_profile_id = browser->recorder_profile" in sources["app"]
        ),
        "interaction_level": (
            "comp_power_settings_interaction_interval_ms(&values)" in sources["main"]
        ),
        "quiet_hours": (
            "comp_power_settings_quiet_hours_active(" in sources["main"]
            and "apply_browser_settings_runtime();" in sources["main"]
        ),
        "time_zone_offset_minutes": (
            "s_screen_menu.browser.time_zone_offset_minutes" in sources["main"]
            and "minute %= 1440" in sources["main"]
        ),
        "recording_gesture": (
            "comp_power_settings_recording_entry_allowed(" in sources["main"]
            and "edge_dx >= 36" in sources["main"]
        ),
    }
    for field in fields:
        if field not in sources["store_h"] or field not in sources["store"]:
            errors.append(f"not persisted: {field}")
        if not consumer_contracts[field]:
            errors.append(f"no target runtime consumer: {field}")

    required = {
        "version2_and_v1_migration": "COMP_POWER_SETTINGS_VERSION 2u" in sources["store"] and
            "record[8] == COMP_POWER_SETTINGS_VERSION_LEGACY" in sources["store"],
        "record_stays_16_bytes": "COMP_POWER_SETTINGS_RECORD_BYTES 16u" in sources["store_h"],
        "crc_correct_reserved_encoding_rejected": (
            "(get_u16(&record[10]) & 0x6000u) == 0x6000u" in sources["store"]
            and "reserved v2 encoding falls back to prior generation" in sources["power_test"]
        ),
        "append_only_write_amplification_fixture": (
            "programmed_bytes" in sources["power_test"]
            and "unchanged settings write amplification" in sources["power_test"]
            and "COMP_POWER_SETTINGS_RECORD_BYTES" in sources["power_test"]
        ),
        "all_field_boundary_fixture": (
            "test_all_settings_round_trip" in sources["power_test"]
            and "test_browser_policy_matrix" in sources["power_test"]
        ),
        "source_pack_one_input_one_transition_fixture": (
            "browser_setting_event_matrix" in sources["touch_test"]
            and "browser_field_diff_count(&before, &menu->browser) == 1u" in sources["touch_test"]
            and "menu->revision == revision + 1u" in sources["touch_test"]
            and "/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1" in sources["touch_script"]
        ),
        "recording_deadline_policy": "comp_power_settings_recording_max_seconds" in sources["main"],
        "silence_after_voice_policy": (
            "comp_power_settings_silence_tracker_step(" in silence_runtime
            and "comp_power_settings_silence_stop_blocks(values)" in sources["store_h"]
        ),
        "silence_tracker_independent_from_live_gatt_sequence": (
            "uint16_t silence_tracker" in sources["main"]
            and "uint32_t packet_sequence_next" in sources["main"]
            and "packet_sequence_next" not in silence_runtime
            and "voice silence threshold exact boundary" in sources["power_test"]
            and "meeting silence threshold exact boundary" in sources["power_test"]
        ),
        "gesture_selector": "comp_power_settings_recording_entry_allowed" in sources["main"] and
            "edge_dx >= 36" in sources["main"],
        "real_connection_state": "Companion_Ble_IsConnected()" in sources["main"] and
            "Companion_Ble_RequestDisconnect" in sources["main"],
        "auto_reconnect_gate": "if (s_companion_browser_auto_reconnect)" in sources["app"],
        "blink_gate": "s_companion_browser_natural_blink" in sources["app"],
        "gaze_gate": "!s_screen_menu.browser.gaze_follow" in sources["main"],
        "interaction_cadence": "comp_power_settings_interaction_interval_ms" in sources["main"],
        "quiet_hours_runtime": "comp_power_settings_quiet_hours_active" in sources["main"],
        "clock_runtime": "Companion_App_StatusClockPacked" in sources["main"] and
            "Companion_App_SyncUtcClock" in sources["main"] and
            "RTC_BKP_DR16" in sources["main"] and
            "scaled_seconds * 16u" in sources["main"] and
            "time.SecondFraction - time.SubSeconds" in sources["main"] and
            "RTC_BKP_DR17" in sources["main"] and
            "RTC_BKP_DR19" not in sources["main"] and
            "BKP17R" not in sources["watchdog"] and
            "event->payload_len >= 13u" in sources["app"] and
            "comp_screen_menu_render_status_bar" in sources["panel"],
        "clock_survives_loader_pin_reset": (
            "rtc_source != RCC_RTCCLKSOURCE_NONE" in sources["ota_loader_main"]
            and "rtc_source != RCC_RTCCLKSOURCE_LSE" in sources["ota_loader_main"]
            and "rtc_source != RCC_RTCCLKSOURCE_NONE" in sources["app_entry"]
            and "rtc_source != RCC_RTCCLKSOURCE_LSE" in sources["app_entry"]
            and "__HAL_RCC_BACKUPRESET_FORCE();" in sources["ota_loader_main"]
            and "__HAL_RCC_BACKUPRESET_FORCE();" in sources["app_entry"]
            and "[clock] boot rtc_source=" in sources["main"]
            and "[clock] sync utc=" in sources["main"]
        ),
        "qualified_lp_inverse_f7_white_dual_f7_bbox_f7_boundary": "pdMS_TO_TICKS(1000u)" in sources["app"] and
            "HAL_Delay(1000u)" in sources["app"] and
            "COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG" in sources["app"] and
            "[s]57=%u" in sources["app"] and
            "[e]57c=%u" in sources["panel"] and
            "ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7(" in sources["panel"] and
            "frame, frame_bytes, report, true, true" in sources["panel"] and
            "ssd1681_lp_current_only_f7(" in sources["panel"] and
            "s_frame, &window, &busy_elapsed_ms, true" in sources["panel"] and
            "memcpy(s_frame, s_previous_frame, SSD1681_FRAME_BYTES);" in sources["panel"] and
            sources["panel"].count("ssd1681_lp_sleep2s_reinit(&window, NULL)") == 1 and
            "ssd1681_set_window(&target_window, true, false)" in sources["panel"] and
            "ssd1681_write_plane_region(0x24u, frame, window)" in sources["panel"] and
            "s_previous_frame, &target_window, &busy_elapsed_ms," in sources["panel"] and
            "false, true);" in sources["panel"] and
            "[epaper] lp_target_status" in sources["panel"] and
            "battery_screen=%u top_hash=%08lX" in sources["panel"],
        "status_bar_runtime_delivery":
            "0u, 0u, 200u, 16u, packed_status" in maintenance_flat and
            "COMP_EPAPER_DISPLAY_STATUS_BAR_CARD_SLOT" in maintenance and
            "request->card_slot != COMP_EPAPER_DISPLAY_STATUS_BAR_CARD_SLOT" in sources["panel"] and
            "request->card_slot == COMP_EPAPER_DISPLAY_STATUS_BAR_CARD_SLOT," in sources["panel"] and
            "COMP_EPAPER_REFRESH_PARTIAL" in maintenance and
            "COMP_EPAPER_REFRESH_MAINTENANCE" not in maintenance and
            "Companion_Screen_SurfaceOwner() != COMP_SCREEN_SURFACE_HOME" in maintenance and
            "Companion_Screen_IsLowPowerCommitted()" in maintenance and
            "Companion_Screen_ServiceStatusBar(now_ms)" in sources["app"] and
            "s_companion_status_bar_next_poll_ms = now_ms + 1000u" in sources["app"] and
            "r30 proved that waking the deep-sleeping controller" in maintenance and
            "s_companion_status_bar_last_packed = packed_status;" in maintenance and
            "Companion_CompReq775RecordingOverlayActive()" in maintenance and
            "if (s_companion_screen_presentation.mode != COMP_SCREEN_PRESENTATION_MENU)" in sources["app"] and
            sources["app"].count("(void)Companion_Screen_ExpressionMaintenance();") >= 3,
        "truthful_devboard_battery":
            "#define COMPANION_WB55_HAS_BATTERY_MEASUREMENT 0" in sources["app"] and
            "#if !COMPANION_WB55_HAS_BATTERY_MEASUREMENT" in sources["app"] and
            ".percent = 0xFFu" in sources["app"] and
            ".charger_present = 0u" in sources["app"] and
            ".millivolts = 0u" in sources["app"] and
            ".percent = 100u" not in sources["app"] and
            ".millivolts = 5000u" not in sources["app"],
        "ordinary_life_single_literal_bbox":
            "bool literal_single_bbox" in sources["panel"] and
            "!persistent_content_window &&\n               !literal_single_bbox" in sources["panel"] and
            "const bool ordinary_life_literal_bbox" in sources["panel"] and
            "request->recording_overlay_present == 0u" in sources["panel"] and
            "request->recording_overlay_only == 0u" in sources["panel"] and
            "!natural_blink_frame" in sources["panel"] and
            "if (literal_single_bbox && window.changed)" in sources["panel"] and
            "functional_delta_windows[functional_delta_count++] = window;" in sources["panel"] and
            "ordinary_life_literal_bbox,\n            &report" in sources["panel"],
        "life_wave_clocks_untouched": "COMPANION_DISPLAY_TRACK_RECORDING" in sources["app"] and
            "COMPANION_DISPLAY_TRACK_BASE" in sources["app"],
    }
    errors.extend(name for name, ok in required.items() if not ok)

    power_test = run_ps("tools/test_power_policy_host.ps1")
    touch_test = run_ps("tools/test_touch_gesture_host.ps1")
    if power_test["status"] != "PASS":
        errors.append("power host test")
    elif "settings all-field/boundary/v1-migration/CRC/torn/write-amplification and behavior matrix pass" not in power_test["stdout"]:
        errors.append("power host test lacks semantic matrix receipt")
    if touch_test["status"] != "PASS":
        errors.append("touch/menu host test")

    headroom = -1
    layout_status = "MISSING"
    if LAYOUT.exists():
        layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
        layout_status = layout.get("status", "UNKNOWN")
        maximum = int(layout["maximum_address_exclusive"], 16)
        headroom = 0x08080000 - maximum
        if layout_status != "MACHINE_READY" or headroom < 1024:
            errors.append("OTA layout/headroom")
    else:
        errors.append("OTA layout receipt missing")

    result = {
        "schema": "companion.comp_req_785.browser_settings.v2",
        "status": "MACHINE_READY" if not errors else "FAILED",
        "persisted_fields": fields,
        "runtime_consumers": consumer_contracts,
        "checks": required,
        "host_tests": {"power": power_test, "touch_menu": touch_test},
        "ota": {"layout_status": layout_status, "headroom_bytes": headroom,
                "minimum_headroom_bytes": 1024},
        "protected_clocks": "recording pure-wave and authored base remain separate display tracks",
        "errors": errors,
        "hardware_contact": 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
