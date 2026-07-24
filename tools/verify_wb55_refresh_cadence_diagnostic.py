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
        ("COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_GROUPS 1u", "one-group production-off default"),
        ("refresh_cadence_diagnostic start requests=%u", "diagnostic start marker"),
        ("refresh_cadence_diagnostic group_start group=%u", "group-start marker"),
        ("refresh_cadence_diagnostic group_complete group=%u", "group-complete marker"),
        ("refresh_cadence_diagnostic baseline_complete=1", "baseline marker"),
        ("refresh_cadence_diagnostic queue step=%u", "queued-step marker"),
        ("refresh_cadence_diagnostic complete step=%u", "completed-step marker"),
        ("interactive_requests=%u cleanup_expected=1", "completion marker"),
        ("COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE", "portable interactive request"),
        ("COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE", "rendered menu variation"),
        (
            "s_companion_refresh_cadence_diagnostic_groups_completed *\n"
            "                        COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS +",
            "monotonic in-image micro-motion phase",
        ),
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
        "EpaperRefreshCadenceDiagnosticGroups",
        "bounded cadence-group build parameter",
        errors,
    )
    require(
        build,
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC_GROUPS=",
        "cadence-group make argument",
        errors,
    )
    require(
        build,
        "EPAPER_SSD1681_BRINGUP=1",
        "SSD1681 bringup make argument",
        errors,
    )
    require(
        build,
        "EPAPER_MENU=1",
        "screen-menu make argument",
        errors,
    )
    require(
        build,
        "EPAPER_SSD1681_CADENCE_MICRO_MOTION_DIAGNOSTIC=1",
        "in-image micro-motion renderer make argument",
        errors,
    )
    require(
        build,
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=5",
        "in-image micro-motion pattern make argument",
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
        '"build_refresh_cadence_diagnostic"',
        "isolated diagnostic build directory",
        errors,
    )
    for token, label in (
        (
            "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC 0",
            "vendor partial production-off default",
        ),
        (
            "COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC 0",
            "direct GPIO transport production-off default",
        ),
        (
            "COMPANION_EPAPER_SSD1681_VERBOSE_TRACE 0",
            "verbose UART trace production-off default",
        ),
        ("#define SSD1681_VERBOSE_TRACE(...) printf(__VA_ARGS__)", "verbose trace enable macro"),
        ("#define SSD1681_VERBOSE_TRACE(...) do { if (0) { printf(__VA_ARGS__); } } while (0)", "quiet production trace macro"),
        ("good_display_vendor_partial_ab", "vendor partial diagnostic profile"),
        ("? 0xFFu", "vendor partial update control"),
        ("Diagnostic-only A/B", "vendor partial isolation rationale"),
        ("software_direct_bsrr_diagnostic", "direct GPIO diagnostic transport marker"),
        ("GPIOA->BSRR = sck_low", "direct GPIO clock low edge"),
        ("GPIOC->BSRR = (value & 0x80u)", "direct GPIO data edge"),
        ("static const uint8_t vendor_partial_border[] = {0x80u};", "vendor partial border setting"),
        (
            "ssd1681_set_window(&window,\n"
            "                                                vendor_sample_partial,\n"
            "                                                vendor_1s_lut_diagnostic)",
            "vendor partial window selection",
        ),
        ("ssd1681_write_plane_region(0x24u, s_frame, &window)", "vendor current-plane write"),
        ("COMPANION_EPAPER_SSD1681_CADENCE_MICRO_MOTION_DIAGNOSTIC 0", "micro-motion production-off default"),
        ("frame_cadence_micro_motion", "micro-motion frame generator"),
        ("SSD1681_CADENCE_MICRO_MOTION_HIGHLIGHT_PIXELS 4u", "four-pixel highlight geometry"),
        ("SSD1681_CADENCE_MICRO_MOTION_ORIGIN_Y 98u", "fixed four-scanline highlight origin"),
        ("step % 8u", "one-pixel micro-motion phase sequence"),
        ("96u + offset", "byte-contained one-pixel coordinate sequence"),
        ("cadence_micro_motion step=%u", "micro-motion serial marker"),
        ("size=%u delta_x=1", "four-pixel one-pixel-step evidence"),
    ):
        require(driver, token, label, errors)
    require(
        makefile,
        "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1",
        "vendor partial build definition",
        errors,
    )
    require(
        makefile,
        "COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1",
        "direct GPIO transport build definition",
        errors,
    )
    require(
        makefile,
        "COMPANION_EPAPER_SSD1681_VERBOSE_TRACE=1",
        "verbose trace build definition",
        errors,
    )
    require(
        build,
        "EpaperSsd1681VerboseTrace",
        "manual verbose trace build switch",
        errors,
    )
    require(
        build,
        '"EPAPER_SSD1681_VERBOSE_TRACE=1"',
        "cadence diagnostics retain verbose trace evidence",
        errors,
    )
    require(
        build,
        "BUILD_DIR=build_verbose_trace",
        "isolated manual verbose trace build directory",
        errors,
    )
    require(
        build,
        "EpaperSsd1681DirectGpioSpiDiagnostic",
        "direct GPIO transport build switch",
        errors,
    )
    require(
        build,
        "EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1",
        "direct GPIO transport make argument",
        errors,
    )
    require(
        build,
        "BUILD_DIR=build_direct_gpio_spi_diagnostic",
        "isolated direct GPIO transport build directory",
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
        ("expected_groups_started", "bounded-group parser start check"),
        ("expected_groups_completed", "bounded-group parser completion check"),
        ("--groups", "bounded-group parser argument"),
        ("--micro-motion", "micro-motion parser argument"),
        ("micro_motion_sequence", "micro-motion coordinate parser check"),
        ("micro_motion_local_window", "micro-motion local-window parser check"),
        ("window_bytes\"] == 4", "four-byte local-window parser threshold"),
        ("PARTIAL_PROFILES", "profiled partial parser"),
        ("TRANSPORT_PROFILES", "profiled transport parser"),
        ("no_post_waveform_transfer", "post-wave transfer elimination parser check"),
        ("correct_data_plane_count", "partial plane-count parser check"),
        ("correct_transport_profile", "transport identity parser check"),
        ("direct_bsrr", "direct GPIO transport parser profile"),
        ("vendor_sample", "vendor partial parser profile"),
        ("no_obsolete_delayed_maintenance", "old-timer parser check"),
        ("PASS_STATIC_PARSER", "parser self-test result"),
    ):
        require(parser, token, label, errors)

    for text, token, label in (
        (build, "EpaperRefreshCadenceDiagnosticPartialLimit", "unrun cadence-limit extension"),
        (build, "EPAPER_REFRESH_CADENCE_DIAGNOSTIC_PARTIAL_LIMIT", "unrun cadence-limit make argument"),
        (parser, "--partial-limit", "unrun cadence-limit parser argument"),
    ):
        if token in text:
            errors.append(f"unexpected {label}: {token}")

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
