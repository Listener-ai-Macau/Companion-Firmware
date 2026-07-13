#!/usr/bin/env python3
"""Verify the optional WB55 six-request refresh-cadence diagnostic wiring."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(text: str, token: str, label: str, errors: list[str]) -> None:
    if token not in text:
        errors.append(f"missing {label}: {token}")


def main() -> int:
    errors: list[str] = []
    app = (
        ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    ).read_text(encoding="utf-8")
    driver = (
        ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    ).read_text(encoding="utf-8")
    makefile = (
        ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
    ).read_text(encoding="utf-8")
    build = (ROOT / "tools/build_nucleo_bringup.ps1").read_text(encoding="utf-8")
    parser = (ROOT / "tools/verify_wb55_refresh_cadence_log.py").read_text(
        encoding="utf-8"
    )

    for token, label in (
        ("COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC 0", "production-off default"),
        ("COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS 6u", "six-request limit"),
        ("refresh_cadence_diagnostic start requests=%u", "diagnostic start marker"),
        ("refresh_cadence_diagnostic baseline_complete=1", "baseline marker"),
        ("refresh_cadence_diagnostic queue step=%u", "queued-step marker"),
        ("refresh_cadence_diagnostic complete step=%u", "completed-step marker"),
        ("interactive_requests=%u cleanup_expected=1", "completion marker"),
        ("COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE", "portable interactive request"),
        ("COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE", "rendered menu variation"),
        ("Companion_Display_AdvanceRefreshCadenceDiagnostic(&request, panel_result)", "post-refresh sequencing"),
    ):
        require(app, token, label, errors)
    require(
        makefile,
        "COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC=1",
        "diagnostic build definition",
        errors,
    )
    require(
        build,
        "EpaperRefreshCadenceDiagnostic",
        "diagnostic build switch",
        errors,
    )
    require(
        build,
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC=1",
        "diagnostic make argument",
        errors,
    )
    require(
        build,
        "BUILD_DIR=build_refresh_cadence_diagnostic",
        "isolated diagnostic build directory",
        errors,
    )
    for token, label in (
        (
            "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC 0",
            "vendor partial production-off default",
        ),
        ("good_display_vendor_partial_ab", "vendor partial diagnostic profile"),
        ("? 0xFFu", "vendor partial update control"),
        ("Diagnostic-only A/B", "vendor partial isolation rationale"),
        ("static const uint8_t vendor_partial_border[] = {0x80u};", "vendor partial border setting"),
        ("ssd1681_set_window(&window, vendor_sample_partial)", "vendor partial window selection"),
        ("ssd1681_write_plane_region(0x24u, s_frame, &window)", "vendor current-plane write"),
    ):
        require(driver, token, label, errors)
    require(
        makefile,
        "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1",
        "vendor partial build definition",
        errors,
    )
    require(
        build,
        "EpaperSsd1681VendorPartialDiagnostic",
        "vendor partial build switch",
        errors,
    )
    require(
        build,
        "EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1",
        "vendor partial make argument",
        errors,
    )
    require(
        build,
        "BUILD_DIR=build_vendor_partial_diagnostic",
        "isolated vendor partial build directory",
        errors,
    )
    for token, label in (
        ("five_differential_requests", "five-partial parser check"),
        ("one_sixth_request_maintenance", "sixth-cleanup parser check"),
        ("PARTIAL_PROFILES", "profiled partial parser"),
        ("no_post_waveform_transfer", "post-wave transfer elimination parser check"),
        ("correct_data_plane_count", "partial plane-count parser check"),
        ("vendor_sample", "vendor partial parser profile"),
        ("no_obsolete_delayed_maintenance", "old-timer parser check"),
        ("PASS_STATIC_PARSER", "parser self-test result"),
    ):
        require(parser, token, label, errors)

    if errors:
        print("wb55 refresh cadence diagnostic: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("wb55 refresh cadence diagnostic: PASS")
    print("  dedicated build is production-off and sequences six post-refresh menu frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
