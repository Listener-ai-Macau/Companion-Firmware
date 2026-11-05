#!/usr/bin/env python3
"""Fail closed on one cold full-window LP C7 with an inverse old plane."""

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

    strong_dispatch = section(
        refresh,
        "if (strong_idle_enter_refresh) {",
        "\n    } else if (first_frame",
    )
    ordinary_full_dispatch = section(
        refresh,
        "} else if (first_frame || visible_full_refresh || maintenance_refresh) {",
        "\n    } else if (s_need_mode2_settle_after_mode1_gc)",
    )
    gc_function = section(
        driver,
        "static bool ssd1681_lifecycle_mode1_gc_full_activation_ex(",
        "\nstatic bool ssd1681_lifecycle_mode2_fast_full_activation(",
    )

    checks = {
        "life_cleanup_limit_remains_64": (
            "#define COMPANION_EPAPER_SSD1681_PRODUCT_PARTIAL_LIMIT 64u"
            in driver
        ),
        "producer_prequiet_is_exactly_1000ms": (
            "vTaskDelay(pdMS_TO_TICKS(1000u));" in low_power
            and low_power.index("s_companion_panel_transaction_active")
            < low_power.index("vTaskDelay(pdMS_TO_TICKS(1000u));")
        ),
        "idle_enter_uses_one_cold_inverse_old_c7": (
            "s_frame, sizeof(s_frame), &report, true, false, true, false);"
            in strong_dispatch
            and "ssd1681_lifecycle_lp_enter_inv_f7" not in strong_dispatch
            and "lp_enter_inverse_old_c7 control=0xC7" in strong_dispatch
            and "inverse_old=1" in strong_dispatch
        ),
        "inverse_old_plane_drives_every_target_pixel": (
            "if (force_inverse_old_plane)" in gc_function
            and "s_blink_closed_frame[index] = (uint8_t)~s_frame[index];"
            in gc_function
            and gc_function.index("if (force_inverse_old_plane)")
            < gc_function.index("else if (contrast_restore_from_white)")
            and "inverse_old=%u old_source=%s" in gc_function
        ),
        "idle_gc_is_not_available_to_recording_overlay": (
            "strong_idle_enter_refresh =" in refresh
            and "requested_mode == COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG;"
            in refresh
        ),
        "idle_enter_has_one_visible_activation_and_no_settle": (
            strong_dispatch.count(
                "ssd1681_lifecycle_mode1_gc_full_activation_ex(") == 1
            and strong_dispatch.count(
                "s_need_mode2_settle_after_mode1_gc = false;") == 2
            and "activation_count=%u inverse_old=1 deferred_settle=0"
            in strong_dispatch
            and "lp_settle_ff" not in strong_dispatch
        ),
        "lp_skips_hidden_0x99_initial_display_stage": (
            "if (rebaseline_complete && force_inverse_old_plane)" in gc_function
            and "lp_skip_mode2_rearm control_0x99=0" in gc_function
            and "initial_display_stage=0 direct_deep_sleep=1" in gc_function
            and gc_function.index("if (rebaseline_complete && force_inverse_old_plane)")
            < gc_function.index("ssd1681_accepted_mode2_rearm(NULL)")
        ),
        "wake_exit_uses_same_primitive_without_lp_inverse_policy": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(" in ordinary_full_dispatch
            and "s_need_mode2_settle_after_mode1_gc = false;" in ordinary_full_dispatch
            and "home_life_contrast_restore, false, false);"
            in ordinary_full_dispatch
        ),
        "logical_low_power_handoff_preserved": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in handoff
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_complete_wake_chain_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "owner_contract": (
            "LP enter uses one cold full-window C7 with inverse(target) in "
            "old RAM, one physical activation, no post-C7 0x99 initial-display "
            "stage, and no F7/FF extra refresh"
        ),
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
