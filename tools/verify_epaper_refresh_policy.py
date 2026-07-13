#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(text: str, needle: str, label: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"missing {label}: {needle}")


def main() -> int:
    errors: list[str] = []
    header = (ROOT / "app/companion_pendant/epaper/refresh_policy.h").read_text(
        encoding="utf-8"
    )
    source = (ROOT / "app/companion_pendant/epaper/refresh_policy.c").read_text(
        encoding="utf-8"
    )
    request = (ROOT / "app/companion_pendant/epaper/display_queue.h").read_text(
        encoding="utf-8"
    )
    driver = (
        ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    ).read_text(encoding="utf-8")
    makefile = (
        ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
    ).read_text(encoding="utf-8")
    main_source = (
        ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    ).read_text(encoding="utf-8")
    evidence = json.loads(
        (
            ROOT
            / "docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json"
        ).read_text(encoding="utf-8")
    )
    asset_manifest = json.loads(
        (
            ROOT
            / "app/companion_pendant/epaper/assets/emote_matrix_white_200x200.json"
        ).read_text(encoding="utf-8")
    )
    asset_revision = asset_manifest.get("revision")

    require(header, "COMP_EPAPER_REFRESH_DEFAULT_PARTIAL_LIMIT 5u", "five-update limit", errors)
    require(header, "COMP_EPAPER_REFRESH_DEFAULT_INTERACTIVE_HARD_LIMIT 60u", "interactive hard limit", errors)
    require(header, "COMP_EPAPER_REFRESH_DECISION_FAST", "fast maintenance decision", errors)
    require(header, "COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED", "baseline guard", errors)
    require(header, "COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT", "limit guard", errors)
    require(header, "COMP_EPAPER_REFRESH_REASON_MAINTENANCE_DEFERRED", "deferred cleanup", errors)
    require(header, "COMP_EPAPER_REFRESH_REASON_INTERACTIVE_HARD_LIMIT", "interactive safety guard", errors)
    require(source, "!policy->baseline_valid", "baseline selection", errors)
    require(source, "policy->partial_count >= policy->partial_limit", "limit selection", errors)
    require(source, "policy->partial_count >= policy->interactive_hard_limit", "interactive limit selection", errors)
    require(source, "requested_mode == COMP_EPAPER_REFRESH_MAINTENANCE", "post-gesture cleanup selection", errors)
    require(source, "selection.reason = COMP_EPAPER_REFRESH_REASON_MAINTENANCE_DEFERRED", "maintenance cleanup reason", errors)
    require(source, "comp_epaper_refresh_policy_self_test", "portable self-test", errors)
    require(request, "COMP_EPAPER_REFRESH_PARTIAL", "portable partial intent", errors)
    require(request, "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE", "interactive partial intent", errors)
    require(request, "COMP_EPAPER_REFRESH_MAINTENANCE", "deferred maintenance intent", errors)
    require(request, "uint16_t dirty_width", "16-bit dirty rectangle", errors)
    require(driver, "ssd1681_window_from_difference", "frame difference window", errors)
    require(driver, "ssd1681_write_plane_region(0x24u, s_frame, &window)", "current BW RAM write", errors)
    require(driver, "Differential mode needs the old and new pixels", "explicit differential old/new plane contract", errors)
    require(
        driver,
        "ssd1681_write_plane_region(0x26u, s_previous_frame, &window)",
        "previous-frame differential plane",
        errors,
    )
    require(driver, "ssd1681_write_plane_region(0x26u, s_frame, &window)", "post-wave previous plane sync", errors)
    require(driver, "s_controller_initialized", "controller reset guard", errors)
    require(driver, "if (controller_initialization_required)", "no reset during repeated partial updates", errors)
    require(driver, "? 0xFCu", "differential update control", errors)
    require(driver, ": 0xF7u", "full update control", errors)
    require(driver, "? 0xC7u", "Good Display fast maintenance control", errors)
    require(driver, "SSD1681_VENDOR_FAST_PROFILE_NAME", "vendor fast profile name", errors)
    require(driver, "ssd1681_prepare_vendor_fast_profile", "vendor fast profile loader", errors)
    require(driver, "0xB1u", "vendor fast temperature-load command", errors)
    require(driver, "0x91u", "vendor fast Mode 1 LUT-load command", errors)
    require(driver, "differential_skip identical_frame", "identical frame suppression", errors)
    require(driver, "comp_epaper_refresh_policy_commit", "result commit", errors)
    require(main_source, "TOUCH_SCREEN_MAINTENANCE_QUIET_MS 1200u", "quiet maintenance delay", errors)
    require(main_source, "s_touch_contact_active", "maintenance touch exclusion", errors)
    require(main_source, "Companion_Screen_MenuMaintenance()", "deferred maintenance request", errors)
    require(main_source, "Companion_Screen_ExpressionMaintenance()", "daily-face deferred maintenance request", errors)
    require(main_source, "schedule_touch_screen_maintenance(now_ms)", "generic post-interaction maintenance schedule", errors)
    require(makefile, "epaper/refresh_policy.c", "firmware linkage", errors)

    if evidence.get("status") != "PASS":
        errors.append("WB55 evidence status is not PASS")
    observed = evidence.get("observed", {})
    expected = {
        "baseline_full_count": 1,
        "partial_count": 5,
        "forced_full_count": 1,
        "partial_busy_active_ms": 225,
        "full_busy_active_ms": 649,
    }
    for key, value in expected.items():
        if observed.get(key) != value:
            errors.append(f"evidence {key} expected {value}, got {observed.get(key)!r}")
    strategy = evidence.get("revision_17_differential_strategy", {})
    if strategy.get("hardware_revalidation") != "PENDING":
        errors.append("revision 17 strategy must remain pending hardware revalidation")
    if not isinstance(asset_revision, int) or asset_revision < 1:
        errors.append(f"current expression asset revision must be a positive integer, got {asset_revision!r}")

    if errors:
        print("epaper refresh policy: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "epaper refresh policy: PASS "
        f"(static contract; current resource rev{asset_revision} runtime/visual recheck pending)"
    )
    print("  post-gesture cleanup target: one Good Display Mode 1 / 0xC7 maintenance pass")
    print("  interactive safety limit: 60 partial updates")
    print("  historical strict diagnostic retained: full + 5 partial + forced full")
    print("  revision 63 controls: full=0xF7 maintenance=0xC7 differential=0xFC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
