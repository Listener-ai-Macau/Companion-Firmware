#!/usr/bin/env python3
"""Keep Companion touch-first low-power requirements and code boundaries intact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "docs" / "companion_low_power_requirements.md"
PLAN = ROOT / "docs" / "companion_screen_project_plan.md"
MAIN = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
APP_BLE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
SCREEN_UI = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "companion_screen_ui.h"
APP_CONF = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "app_conf.h"
POLICY_H = ROOT / "app" / "companion_pendant" / "power" / "power_policy.h"
POLICY_C = ROOT / "app" / "companion_pendant" / "power" / "power_policy.c"
WBA_TARGET_H = ROOT / "app" / "companion_pendant" / "power" / "power_target_stm32wba.h"
WBA_TARGET_C = ROOT / "app" / "companion_pendant" / "power" / "power_target_stm32wba.c"
TOUCH_WAKE_LOG_VERIFIER = ROOT / "tools" / "verify_wb55_touch_wake_log.py"
FIXTURE = ROOT / "docs" / "validation" / "companion-low-power-requirements.json"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()

    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    app_ble_source = APP_BLE.read_text(encoding="utf-8")
    screen_ui = SCREEN_UI.read_text(encoding="utf-8")
    app_conf = APP_CONF.read_text(encoding="utf-8")
    policy_h = POLICY_H.read_text(encoding="utf-8")
    policy_c = POLICY_C.read_text(encoding="utf-8")
    wba_target_h = WBA_TARGET_H.read_text(encoding="utf-8")
    wba_target_c = WBA_TARGET_C.read_text(encoding="utf-8")
    touch_wake_log_verifier = TOUCH_WAKE_LOG_VERIFIER.read_text(encoding="utf-8")
    errors: list[str] = []

    for anchor in [
        "真实本地唤醒词保持 `deferred`",
        "1 mA",
        "60 s",
        "TP_INT",
        "PC6",
        "UTIL_LPM",
        "hardware_current_pending",
        "WBA55/WBA65",
        "PDM/KWS",
        "TP_INT)`；`TP_RST` 未接",
        "WAKE_N",
        "地址匹配 I2C Stop 唤醒",
        "只排队一次外部 Flash `sleepy` 休眠脸",
        "不得在 Stop 中周期性唤醒或刷新电子纸",
    ]:
        require(anchor in requirements, f"low-power requirement missing: {anchor}", errors)

    require("SCR-21" in plan, "project plan does not register SCR-21", errors)
    require("COMPANION_LOW_POWER_ENABLE 1" in app_conf, "low-power configuration is not enabled", errors)
    require("COMPANION_TOUCH_INT_WIRED 1" in app_conf, "current board must declare TP_INT is wired", errors)
    require("COMPANION_TOUCH_RST_WIRED 0" in app_conf, "current board must not claim TP_RST is wired", errors)
    require("CFG_LPM_SUPPORTED 1" in app_conf, "CubeWB LPM is not enabled", errors)
    require("COMP_POWER_BLOCKER_MIC_CAPTURE" in policy_h, "policy lacks mic capture blocker", errors)
    require("COMP_POWER_BLOCKER_TOUCH_CONTACT" in policy_h, "policy lacks touch contact blocker", errors)
    require("COMP_POWER_BLOCKER_SCREEN_WAIT" in policy_h, "policy lacks screen wait blocker", errors)
    require("touch_wake_ready" in policy_c, "policy does not gate Stop on touch wake", errors)
    for blocker in [
        "COMP_POWER_BLOCKER_MIC_CAPTURE",
        "COMP_POWER_BLOCKER_TOUCH_CONTACT",
        "COMP_POWER_BLOCKER_MENU_TIMER",
        "COMP_POWER_BLOCKER_SCREEN_MAINTENANCE",
        "COMP_POWER_BLOCKER_SCREEN_WAIT",
    ]:
        require(blocker in policy_c, f"policy self-test misses: {blocker}", errors)
    require("UTIL_LPM_SetStopMode" in main_source, "WB55 target does not drive Cube LPM", errors)
    require("COMPANION_TOUCH_INT_WIRED != 0u" in main_source, "Stop does not require verified TP_INT wiring", errors)
    require("#if COMPANION_TOUCH_RST_WIRED" in main_source, "unwired TP_RST does not release PC10", errors)
    require("#if COMPANION_TOUCH_INT_WIRED" in main_source, "unwired TP_INT does not release PC6", errors)
    require("int _write(int file, char *data, int length)" in main_source, "low-power build lacks direct serial writer", errors)
    require("HAL_UART_Transmit" in main_source, "low-power serial writer does not use USART", errors)
    require("COMP_TOUCH_GESTURE_DOUBLE_TAP" in main_source, "daily double-tap recording path is absent", errors)
    require("if (!s_low_power_stop_allowed)" in main_source, "idle loop still forces fixed polling", errors)
    require("s_low_power_idle_pose_attempted" in main_source, "low-power sleep pose is not one-shot gated", errors)
    require("Companion_Screen_EnterLowPowerIdle" in main_source, "Stop path does not request the low-power sleep pose", errors)
    require("low_power_face request=sleepy animation=static" in main_source, "low-power pose diagnostic is absent", errors)
    require("Companion_Screen_EnterLowPowerIdle" in screen_ui, "screen API lacks low-power idle entry", errors)
    for anchor in [
        "COMP_EPAPER_EXPRESSION_SLEEPY",
        "low_power_idle",
        "comp_emote_player_stop",
        "HW_TS_Stop",
        "low_power_idle pose=sleepy animation=stopped",
    ]:
        require(anchor in app_ble_source, f"low-power screen implementation missing: {anchor}", errors)
    require("configure_touch_wake" in wba_target_h, "WBA target lacks touch-wake callback", errors)
    require("set_stop_allowed" in wba_target_h, "WBA target lacks Stop callback", errors)
    require("comp_power_policy_stop_allowed" in wba_target_c, "WBA target bypasses portable policy", errors)
    for forbidden in ["HAL_", "GPIO", "IPCC", "STM32_WPAN", "BLE_p2pServer"]:
        require(forbidden not in wba_target_c, f"WBA power target leaks platform detail: {forbidden}", errors)
    for anchor in [
        "touch_irq_wake=ready",
        "irq=PC6 wired=1",
        "daily_double_tap_recording",
        "action=user_store result=1",
        "--self-test",
    ]:
        require(anchor in touch_wake_log_verifier, f"touch-wake log verifier missing: {anchor}", errors)

    result = {
        "schema_id": "companion.low_power.requirements.v1",
        "status": "PASS" if not errors else "FAIL",
        "implementation_status": "static_policy_compiled; hardware_stop_wake_and_current_pending",
        "product_interaction": "daily double tap starts/stops touch-originated recording; wake word deferred",
        "low_power_visual": "one static external-Flash sleepy frame precedes Stop; no periodic e-paper breathing refresh in Stop",
        "idle_gate": "touch EXTI ready and no boot/mic/touch/menu/screen blockers",
        "target": "final product-board LP-01 standby average <= 1 mA over >= 60 s",
        "measurement_status": "hardware_current_pending",
        "portability": "HAL-free policy with WBA55/WBA65 callback-only LPM/EXTI glue",
        "errors": errors,
    }

    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
