#!/usr/bin/env python3
"""Verify the production LP dispatch preserves the owner-accepted r57 topology."""

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
    vendor_lut_guard = driver[max(0, vendor_lut_at - 320):vendor_lut_at]

    checks = {
        "product_dispatches_r57": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(" in lp_dispatch
            and "&report, true, true, false, false" in lp_dispatch
            and "lp_supplier_1s_single" not in lp_dispatch
        ),
        "inverse_current_only_f7": (
            "s_frame, &window, &busy_elapsed_ms, 0xF7u, false, false"
            in lp_branch
        ),
        "controller_off_two_second_dwell": (
            "ssd1681_command_data(0x10u" in lp_branch
            and "HAL_Delay(100u);" in lp_branch
            and "HAL_Delay(2000u);" in lp_branch
            and "ssd1681_reset();" in lp_branch
        ),
        "white_dual_plane_f7": (
            "s_frame, &window, &busy_elapsed_ms, 0xF7u, true, false"
            in lp_branch
        ),
        "target_is_white_difference_bbox": (
            "target_window = ssd1681_window_from_difference();" in lp_branch
        ),
        "target_current_only_f7": (
            "s_previous_frame, &target_window, &busy_elapsed_ms"
            in lp_branch
            and "0xF7u, false, true" in lp_branch
        ),
        "three_visible_activations_reported": (
            "report->activation_count = 3u;" in lifecycle
        ),
        "old_ram_bbox_sync_only": (
            "0x26u, s_frame, &target_window" in rebaseline
            and "0x24u" not in rebaseline
        ),
        "command_only_mode2_rearm": (
            "mode2_rearmed = rebaseline_complete" in lifecycle
            and "ssd1681_accepted_mode2_rearm(NULL)" in lifecycle
        ),
        "receipt_records_all_stages": (
            'printf("[e]57 inv=%u white=%u target=%u' in lp_branch
        ),
        "supplier_lut_product_off": (
            "#if COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC"
            in vendor_lut_guard
            and "ACCEPTED_CACHED_MODE2_PRODUCT" not in vendor_lut_guard
        ),
        "final_deep_sleep_latched": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in main_lp
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_r57_product_static.v1",
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
