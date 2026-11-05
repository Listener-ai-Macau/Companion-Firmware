#!/usr/bin/env python3
"""Fail closed on the one-shot source-LUT LP landing with panel OTP VCOM."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def section(text: str, start_token: str, end_token: str) -> str:
    start = text.index(start_token)
    end = text.index(end_token, start)
    return text[start:end]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--app-ble", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    driver = args.driver.read_text(encoding="utf-8")
    app_ble = args.app_ble.read_text(encoding="utf-8")
    main_source = args.main.read_text(encoding="utf-8")
    landing = section(
        driver,
        "static bool ssd1681_lifecycle_lp_supplier_1s_single_activation(",
        "\nstatic bool ssd1681_lp_current_only_full(",
    )
    refresh = section(
        driver,
        "static comp_epaper_panel_result_t ssd1681_accepted_cached_mode2_product_refresh(",
        "\nstatic comp_epaper_panel_result_t ssd1681_refresh(",
    )
    low_power = section(
        app_ble,
        "bool Companion_Screen_EnterLowPowerIdle(void)",
        "\nbool Companion_Screen_ShowDaily(void)",
    )
    handoff = section(
        main_source,
        "if (low_power_committed && !s_epaper_deep_sleep_entered)",
        "} else if (!low_power_committed)",
    )

    checks = {
        "life_cleanup_limit_remains_64": (
            "#define COMPANION_EPAPER_SSD1681_PRODUCT_PARTIAL_LIMIT 64u" in driver
        ),
        "producer_prequiet_is_exactly_1000ms": (
            "vTaskDelay(pdMS_TO_TICKS(1000u));" in low_power
        ),
        "supplier_lut_is_literal_and_product_scoped": (
            "SSD1681_VENDOR_1S_LUT_SHA256 \"F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15\""
            in driver
            and "COMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT" in driver
            and "static const uint8_t ssd1681_vendor_1s_lut[159]" in driver
        ),
        "source_lut_cannot_override_panel_otp_vcom": (
            "static const uint8_t panel_otp_vcom[] = {0x28u};" in driver
            and "ssd1681_command_data(0x2Cu, panel_otp_vcom," in driver
            and "ssd1681_command_data(0x2Cu, &ssd1681_vendor_1s_lut[158], 1u)"
            not in driver
            and 'printf("[e]lp1 sha=%s v=28 ' in landing
        ),
        "landing_has_one_current_plane_and_one_activation": (
            landing.count("ssd1681_write_plane_region(0x24u") == 1
            and "ssd1681_write_plane_region(0x26u" not in landing
            and landing.count("ssd1681_command(0x20u)") == 1
            and "static const uint8_t update_control[] = {0xC7u};" in landing
            and "report->activation_count = 1u;" in landing
        ),
        "landing_has_no_rebaseline_or_settle": (
            "ssd1681_accepted_mode2_rearm" not in landing
            and "lp_settle_ff" not in landing
            and "post_sync_command = 0u" in landing
            and "post_sync_bytes = 0u" in landing
        ),
        "idle_enter_exclusively_dispatches_supplier_landing": (
            "ok = ssd1681_lifecycle_lp_supplier_1s_single_activation(" in refresh
            and "s_frame, sizeof(s_frame), &report);" in refresh
            and "source package's VCOM 0x58" in refresh
            and "lp_enter_inverse_old_c7" not in refresh
        ),
        "idle_supplier_is_not_available_to_recording_overlay": (
            "COMP_EPAPER_DISPLAY_CLASS_RECORDING" in low_power
            and "Companion_CompReq775CancelRecordingTrack();" in low_power
            and "comp_screen_composition_set_recording(\n      &s_companion_screen_composition, false" in low_power
            and "COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG" in low_power
        ),
        "deep_sleep_follows_committed_surface": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();" in handoff
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_supplier_1s_single_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "owner_contract": "one source-waveform visible activation with panel OTP VCOM 0x28; no repeated full-screen settle",
        "identity": {
            "driver_sha256": hashlib.sha256(args.driver.read_bytes()).hexdigest().upper(),
            "app_ble_sha256": hashlib.sha256(args.app_ble.read_bytes()).hexdigest().upper(),
            "main_sha256": hashlib.sha256(args.main.read_bytes()).hexdigest().upper(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
