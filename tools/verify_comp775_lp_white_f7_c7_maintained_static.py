#!/usr/bin/env python3
"""Fail closed on the maintained-history LP white-F7 -> target-C7 path."""

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
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    driver = args.driver.read_text(encoding="utf-8")
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
    deep_sleep = section(
        main_source,
        "if (low_power_committed && !s_epaper_deep_sleep_entered)",
        "} else if (!low_power_committed)",
    )

    white = gc.index(
        "s_frame, &window, &busy_elapsed_ms, 0xF7u, false, false")
    target_profile = gc.index("ssd1681_prepare_vendor_fast_profile()", white)
    target_c7 = gc.index("const uint8_t full_update = 0xC7u", target_profile)
    checks = {
        "life_cleanup_limit_is_64": (
            "#define COMPANION_EPAPER_SSD1681_PRODUCT_PARTIAL_LIMIT 64u"
            in driver
        ),
        "lp_uses_exactly_two_visible_activations": (
            "report->activation_count = 2u;" in gc
            and gc.count("0xF7u") == 1
            and gc.count("const uint8_t full_update = 0xC7u") == 1
        ),
        "white_is_supplier_current_only_f7": (
            "white_clear_first ||\n                    ssd1681_prepare_vendor_fast_profile()"
            in gc
            and "s_frame, &window, &busy_elapsed_ms, 0xF7u, false, false"
            in gc
        ),
        "white_precedes_target_profile_and_c7": white < target_profile < target_c7,
        "target_is_reset_first_white_old_sleepy_current": all(
            token in gc
            for token in (
                "HAL_Delay(250u);",
                "ssd1681_reset();",
                "memset(s_blink_closed_frame, 0xFFu, SSD1681_FRAME_BYTES);",
                "0x26u, s_blink_closed_frame, &window",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
            )
        ),
        "lp_receipts_present": (
            'printf("[e]lpw=%u' in gc and 'printf("[e]lpc7=%u' in gc
        ),
        "strong_idle_dispatches_white_f7_c7": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(\n"
            "            s_frame, sizeof(s_frame), &report, true, true, false);"
            in refresh
        ),
        "rejected_component_f7_not_dispatched": (
            "ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7(\n"
            not in refresh
        ),
        "final_mode2_rearm_is_command_only": (
            "mode2_rearmed = rebaseline_complete &&\n"
            "                    ssd1681_accepted_mode2_rearm(NULL);"
            in gc
        ),
        "final_deep_sleep_preserved": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in deep_sleep
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_white_f7_c7_maintained_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "identity": {
            "driver": str(args.driver.resolve()),
            "driver_sha256": hashlib.sha256(args.driver.read_bytes()).hexdigest().upper(),
            "main": str(args.main.resolve()),
            "main_sha256": hashlib.sha256(args.main.read_bytes()).hexdigest().upper(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
