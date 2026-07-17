#!/usr/bin/env python3
"""Static contract check for the isolated WB55 ball-motion diagnostic."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(text: str, token: str, label: str, errors: list[str]) -> None:
    if token not in text:
        errors.append(f"missing {label}: {token}")


def main() -> int:
    errors: list[str] = []
    registry = (ROOT / "docs/companion_product_requirements.md").read_text(encoding="utf-8")
    header = (ROOT / "app/companion_pendant/epaper/ball_motion_diagnostic.h").read_text(encoding="utf-8")
    driver = (ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c").read_text(encoding="utf-8")
    app = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c").read_text(encoding="utf-8")
    main_c = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text(encoding="utf-8")
    makefile = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile").read_text(encoding="utf-8")
    build = (ROOT / "tools/build_nucleo_bringup.ps1").read_text(encoding="utf-8")

    require(registry, "COMP-REQ-086", "owner motion-baseline requirement", errors)
    for token, label in (
        ("COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS 6u", "six interactive steps"),
        ("COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_RADIUS 10u", "fixed ball radius"),
        ("comp_epaper_ball_motion_diagnostic_center_x", "shared center mapping"),
    ):
        require(header, token, label, errors)
    for token, label in (
        ("COMPANION_EPAPER_SSD1681_BALL_MOTION_DIAGNOSTIC 0", "production-off driver switch"),
        ("frame_ball_motion", "ball raster function"),
        ("ball_motion step=%u center=%u,%u radius=%u", "per-frame geometry log"),
        ("COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN == 4u", "reserved ball pattern"),
        ("COMPANION_EPAPER_SSD1681_BALL_MOTION_DIAGNOSTIC == 0", "no boot auto-run for touch diagnostic"),
    ):
        require(driver, token, label, errors)
    for token, label in (
        ("COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC 0", "production-off app switch"),
        ("ball_motion_diagnostic ready action=single_touch", "touch-ready marker"),
        ("Companion_Screen_BallMotionDiagnosticStart", "touch start entry"),
        ("COMP_EPAPER_REFRESH_FULL", "full baseline request"),
        ("COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE", "current-profile motion request"),
        ("ball_motion_diagnostic done interactive_steps=%u cleanup_expected=1", "completion marker"),
        ("Companion_Display_AdvanceBallMotionDiagnostic(&request, panel_result)", "post-refresh sequencer"),
        ("comp_epaper_display_queue_pending(&s_companion_display_queue)", "live queue re-schedule"),
    ):
        require(app, token, label, errors)
    for token, label in (
        ("Companion_Screen_BallMotionDiagnosticStart()", "tap trigger"),
        ("Companion_Screen_BallMotionDiagnosticIsActive()", "input isolation"),
    ):
        require(main_c, token, label, errors)
    for token, label in (
        ("EPAPER_SSD1681_BALL_MOTION_DIAGNOSTIC", "isolated make switch"),
        ("COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4u", "ball pattern definition"),
    ):
        require(makefile, token, label, errors)
    for token, label in (
        ("EpaperSsd1681BallMotionDiagnostic", "build parameter"),
        ("BUILD_DIR=build_ball_motion_diagnostic", "isolated build output"),
        ("TARGET=Companion_Nucleo_WB55RG_BallMotionDiagnostic", "isolated target"),
    ):
        require(build, token, label, errors)

    if errors:
        print("wb55 ball-motion diagnostic: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("wb55 ball-motion diagnostic: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
