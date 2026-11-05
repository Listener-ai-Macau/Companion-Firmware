#!/usr/bin/env python3
"""Fail closed on the temporary valid normal-full LP white-only probe."""

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
    checks = {
        "diagnostic_is_explicitly_enabled": (
            "#define COMPANION_EPAPER_SSD1681_LP_WHITE_ONLY_DIAGNOSTIC 1"
            in driver
        ),
        "life_cleanup_limit_remains_64": (
            "#define COMPANION_EPAPER_SSD1681_PRODUCT_PARTIAL_LIMIT 64u"
            in driver
        ),
        "white_is_supplier_current_only_f7": (
            "white_clear_first ||\n                    ssd1681_prepare_vendor_fast_profile()"
            in gc
            and "s_frame, &window, &busy_elapsed_ms, 0xF7u, false, false"
            in gc
        ),
        "no_fast_profile_before_white_f7": white < target_profile,
        "target_is_skipped_only_for_lp_probe": all(
            token in gc
            for token in (
                "const bool lp_white_only_diagnostic = lp_official_white_then_c7;",
                "if (lp_white_only_diagnostic)",
                'printf("[e]lpwo=1 target_skipped=1',
                "if (!lp_white_only_diagnostic)",
            )
        ),
        "white_truth_is_synced_without_activation": (
            "ssd1681_write_plane_region(\n                              0x26u, s_frame, &target_window)"
            in gc
            and "ssd1681_accepted_mode2_rearm(NULL)" in gc
        ),
        "probe_reports_one_f7_activation": (
            "lp_white_only_diagnostic ? 0xF7u : 0xC7u" in gc
            and "lp_white_only_diagnostic ? 1u : 2u" in gc
        ),
        "strong_idle_dispatch_is_the_only_probe_entry": (
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(\n"
            "            s_frame, sizeof(s_frame), &report, true, true, false);"
            in refresh
            and refresh.count(", true, true, false);") == 1
        ),
        "rejected_component_path_not_dispatched": (
            "ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7(\n"
            not in refresh
        ),
        "final_deep_sleep_preserved": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in deep_sleep
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp_req_775.lp_white_only_valid_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "warning": "TEMPORARY_DIAGNOSTIC_NOT_PRODUCT_DELIVERABLE",
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
