#!/usr/bin/env python3
"""Verify r61 normal-white, dwell, wake-C7, and standby LP topology."""

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
        "if (white_clear_first) {\n"
        "        static const uint8_t target_full_update[] = {0xC7u};",
        "\n    } else {",
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
    standby = between(
        driver,
        "static bool ssd1681_deep_sleep_phase(",
        "\n#if 0 /* Rejected r45",
    )
    main_lp = between(
        main_source,
        "if (low_power_committed && !s_epaper_deep_sleep_entered)",
        "} else if (!low_power_committed)",
    )

    checks = {
        "product_dispatch_preserved": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(" in lp_dispatch
            and "&report, true, true, false, false" in lp_dispatch
        ),
        "official_current_only_white_f7": (
            "memset(s_frame, 0xFFu" in lp_branch
            and "ssd1681_lp_current_only_full(" in lp_branch
            and "s_frame, &window, &busy_elapsed_ms, 0xF7u, false, false"
            in lp_branch
        ),
        "white_ram_truth_before_dwell": (
            "white_ram_ok = white_clear_ok" in lp_branch
            and "ssd1681_write_plane_region(0x26u, s_frame, &window)" in lp_branch
            and lp_branch.count(
                "ssd1681_write_plane_region(0x24u, s_frame, &window)") >= 2
        ),
        "one_second_no_activation_dwell": (
            lp_branch.count("HAL_Delay(1000u)") == 1
            and lp_branch.index("HAL_Delay(1000u)")
            < lp_branch.index("ssd1681_prepare_vendor_fast_profile()")
        ),
        "wake_equivalent_target_c7": (
            "ssd1681_reset();" in lp_branch
            and "ssd1681_prepare_vendor_fast_profile()" in lp_branch
            and "target_full_update[] = {0xC7u}" in lp_branch
            and "ssd1681_write_plane_region(0x26u, s_blink_closed_frame, &window)"
            in lp_branch
            and lp_branch.count("ssd1681_command(0x20u)") == 1
        ),
        "no_supplier_lut_or_mode2_ff_in_lp": (
            "ssd1681_reset_vendor_1s_lut" not in lp_branch
            and "ssd1681_set_window(&window, false, true)" not in lp_branch
            and "fast_full_update" not in lp_branch
            and "lp_settle_ff" not in lp_branch
        ),
        "target_rebaseline_and_mode2_rearm": (
            "rebaseline_complete = activation_complete" in lp_branch
            and "mode2_rearmed = rebaseline_complete" in lp_branch
            and "ssd1681_accepted_mode2_rearm(NULL)" in lp_branch
        ),
        "two_activation_report": (
            "report->activation_count = 2u;" in lifecycle
            and "report->previous_plane_sync = 1u;" in lifecycle
            and "report->post_sync_command = 0x24u;" in lifecycle
            and "report->post_sync_bytes = SSD1681_FRAME_BYTES * 2u;" in lifecycle
        ),
        "normal_standby_not_controller_deep_sleep": (
            "skipped=normal_standby" in standby
            and "ssd1681_command_data(0x10u" not in standby
            and "s_controller_deep_sleep = false;" in standby
        ),
        "logical_lp_handoff_preserved": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in main_lp
        ),
        "ordinary_mode2_unchanged": (
            "Ordinary product partial: single 0xCF path" in product_refresh
            and "ssd1681_cached_mode2_diff_internal(" in product_refresh
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_r61_white_dwell_wake_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "driver": str(args.driver.resolve()),
        "driver_sha256": hashlib.sha256(args.driver.read_bytes()).hexdigest().upper(),
        "main": str(args.main.resolve()),
        "main_sha256": hashlib.sha256(args.main.read_bytes()).hexdigest().upper(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
