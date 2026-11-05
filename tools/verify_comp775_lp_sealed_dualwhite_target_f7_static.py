#!/usr/bin/env python3
"""Fail closed on the restored sealed LP dual-white-F7 -> target-F7 boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    gc = section(
        driver,
        "static bool ssd1681_lifecycle_mode1_gc_full_activation_ex(",
        "\nstatic bool ssd1681_lifecycle_mode2_fast_full_activation(",
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
    deep_sleep = section(
        main_source,
        "if (low_power_committed && !s_epaper_deep_sleep_entered)",
        "} else if (!low_power_committed)",
    )

    checks = {
        "sealed_baseline_is_documented_in_source": (
            "sealed 2026-08-07 / 2026-08-15 owner-PASS boundary" in gc
        ),
        "life_cleanup_limit_remains_64": (
            "#define COMPANION_EPAPER_SSD1681_PRODUCT_PARTIAL_LIMIT 64u"
            in driver
        ),
        "producer_prequiet_is_exactly_1000ms": (
            "once every producer\n   * is cancelled" in low_power
            and "vTaskDelay(pdMS_TO_TICKS(1000u));" in low_power
            and low_power.index("s_companion_panel_transaction_active")
            < low_power.index("vTaskDelay(pdMS_TO_TICKS(1000u));")
        ),
        "white_basemap_is_dual_ram_normal_window_f7": (
            "s_frame, &window, &busy_elapsed_ms, 0xF7u, true, false" in gc
            and "s_frame, &window, &busy_elapsed_ms, 0xF7u, false, true"
            not in gc
            and "memset(s_frame, 0xFFu, SSD1681_FRAME_BYTES);" in gc
            and "memset(s_blink_closed_frame, 0xFFu, SSD1681_FRAME_BYTES);"
            in gc
            and 'printf("[e]lpw=%u dual=1 partial=0' in gc
        ),
        "normal_f7_skips_fast_profile": (
            re.search(
                r"white_clear_first\s*\|\|\s*"
                r"ssd1681_prepare_vendor_fast_profile\(\)",
                gc,
            )
            is not None
        ),
        "r1_lp_gpio_and_controller_reprepare_restored": (
            "if (white_clear_first) {" in gc
            and "companion_epaper_panel_stm32wb_ssd1681_comp_req_616_prepare();"
            in gc
            and "gpio_reinit=1" in gc
        ),
        "r1_white_rebaseline_precedes_target_f7": (
            re.search(
                r'printf\("\[e\]lpw=.*?'
                r'ssd1681_write_plane_region\(0x26u, s_frame, &window\).*?'
                r'ssd1681_write_plane_region\(0x24u, s_frame, &window\).*?'
                r'printf\("\[e\]lpwrb=',
                gc,
                re.DOTALL,
            )
            is not None
            and gc.index('printf("[e]lpwrb=')
            < gc.index("memcpy(s_frame, s_previous_frame, SSD1681_FRAME_BYTES);")
        ),
        "target_is_white_old_sleepy_current_f7": all(
            token in gc
            for token in (
                "const uint8_t full_update = white_clear_first ? 0xF7u : 0xC7u;",
                "0x26u, s_blink_closed_frame, &window",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                'printf("[e]lpf7=%u',
            )
        ),
        "target_rebaseline_writes_both_rams_without_activation": (
            "0x26u, s_frame, &target_window" in gc
            and "0x24u, s_frame, &target_window" in gc
            and "ssd1681_accepted_mode2_rearm(NULL)" in gc
        ),
        "lp_reports_exactly_two_f7_activations": (
            "report->activation_count = 2u;" in gc
            and "white_clear_first ? 0xF7u : 0xC7u" in gc
            and "report->post_sync_command = 0x24u;" in gc
            and "report->post_sync_bytes = SSD1681_FRAME_BYTES * 2u;" in gc
        ),
        "strong_idle_dispatches_sealed_path_only": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(\n"
            "            s_frame, sizeof(s_frame), &report, true, true, false);"
            in refresh
            and "ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7(\n"
            not in refresh
        ),
        "white_only_diagnostic_removed": (
            "LP_WHITE_ONLY_DIAGNOSTIC" not in driver
            and "lpwo=" not in driver
        ),
        "post_commit_deep_sleep_isolated": (
            "panel_sleep skipped=controller_awake_freeze" in deep_sleep
            and "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            not in deep_sleep
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_sealed_dualwhite_target_f7_static.v2",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "sealed_reference": {
            "package": ".cache/validation/screen-freeze-fix-20260806/baseline-lp-enter-clean-screen-20260807",
            "bin_sha256": "C09538DC11D95C6ECC6D84C25910DC20EB232E1476E0ADDD5071A41A0BC33DDD",
            "owner_result": "现在确实是干净的，没问题，这样进入低功耗就可以了。",
        },
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
