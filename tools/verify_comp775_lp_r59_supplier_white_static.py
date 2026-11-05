#!/usr/bin/env python3
"""Verify r59 uses one supplier-white cleanup then one r57 target F7."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def between(source: str, start_token: str, end_token: str) -> str:
    start = source.index(start_token)
    return source[start:source.index(end_token, start)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    driver = args.driver.read_text(encoding="utf-8")
    main_source = args.main.read_text(encoding="utf-8")
    lifecycle = between(
        driver,
        "static bool ssd1681_lifecycle_mode1_gc_full_activation_ex(",
        "\nstatic bool ssd1681_lifecycle_mode2_fast_full_activation(",
    )
    lp_branch = between(
        lifecycle,
        "if (window_set && white_clear_first) {",
        "\n    } else {",
    )
    rebaseline = between(
        lifecycle,
        "rebaseline_complete = activation_complete &&",
        "\n    mode2_rearmed =",
    )
    product_refresh = between(
        driver,
        "static comp_epaper_panel_result_t "
        "ssd1681_accepted_cached_mode2_product_refresh(",
        "\nstatic comp_epaper_panel_result_t ssd1681_refresh(",
    )
    lp_dispatch = between(
        product_refresh,
        "if (strong_idle_enter_refresh) {",
        "\n    } else if (first_frame",
    )
    main_lp = between(
        main_source,
        "if (low_power_committed && !s_epaper_deep_sleep_entered)",
        "} else if (!low_power_committed)",
    )
    vendor_lut_at = driver.index(
        "static const uint8_t ssd1681_vendor_1s_lut")
    vendor_lut_guard = driver[max(0, vendor_lut_at - 420):vendor_lut_at]

    checks = {
        "product_dispatch_preserved": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(" in lp_dispatch
            and "&report, true, true, false, false" in lp_dispatch
            and "lp_supplier_1s_single" not in lp_dispatch
        ),
        "supplier_lut_exact_identity": (
            'SSD1681_VENDOR_1S_LUT_SHA256 '
            '"F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15"'
            in driver
            and "static const uint8_t ssd1681_vendor_1s_lut[159]" in driver
        ),
        "supplier_lut_product_scoped": (
            "COMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT"
            in vendor_lut_guard
        ),
        "one_supplier_white_activation": (
            "memset(s_frame, 0xFFu, SSD1681_FRAME_BYTES);" in lp_branch
            and "ssd1681_reset_vendor_1s_lut();" in lp_branch
            and "ssd1681_set_window(&window, false, true)" in lp_branch
            and "s_frame, &window, &busy_elapsed_ms, 0xC7u, false, false"
            in lp_branch
        ),
        "supplier_white_current_only": (
            "0xC7u, false, false" in lp_branch
        ),
        "two_second_discharge_and_cold_reinit": (
            "ssd1681_command_data(0x10u" in lp_branch
            and "HAL_Delay(100u);" in lp_branch
            and "HAL_Delay(2000u);" in lp_branch
            and "ssd1681_command(0x12u)" in lp_branch
            and "ssd1681_set_window(&window, false, false)" in lp_branch
        ),
        "target_is_white_difference_bbox": (
            "target_window = ssd1681_window_from_difference();" in lp_branch
        ),
        "target_current_only_f7": (
            "s_previous_frame, &target_window, &busy_elapsed_ms" in lp_branch
            and "0xF7u, false, true" in lp_branch
        ),
        "no_inverse_or_double_white": (
            "inverse_precondition" not in lp_branch
            and "white_settle" not in lp_branch
            and lp_branch.count("ssd1681_lp_current_only_full(") == 2
        ),
        "two_visible_activations_reported": (
            "report->activation_count = 2u;" in lifecycle
            and "report->activation_count = 4u;" not in lifecycle
        ),
        "old_ram_bbox_sync_only": (
            "0x26u, s_frame, &target_window" in rebaseline
            and "0x24u" not in rebaseline
        ),
        "command_only_mode2_rearm": (
            "mode2_rearmed = rebaseline_complete" in lifecycle
            and "ssd1681_accepted_mode2_rearm(NULL)" in lifecycle
        ),
        "existing_receipt_covers_complete_chain": (
            "ready = ready && supplier_white_ok && white_reinitialized"
            in lp_branch
            and "target_draw_ok;" in lp_branch
            and '"[epaper] accepted_gc_full control=0x%02X "'
            in lifecycle
            and '"complete=%u busy_ms=%lu rebaseline=%u mode2=%u lp_white=%u'
            in lifecycle
        ),
        "ordinary_mode2_unchanged": (
            "Ordinary product partial: single 0xCF path" in product_refresh
            and "ssd1681_cached_mode2_diff_internal(" in product_refresh
        ),
        "final_deep_sleep_latched": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in main_lp
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_r59_supplier_white_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "driver": str(args.driver.resolve()),
        "driver_sha256": hashlib.sha256(args.driver.read_bytes()).hexdigest().upper(),
        "main": str(args.main.resolve()),
        "main_sha256": hashlib.sha256(args.main.read_bytes()).hexdigest().upper(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
