#!/usr/bin/env python3
"""Verify menu internal updates stay partial while enter/exit stay full."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAIN = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
GESTURE = ROOT / "app" / "companion_pendant" / "touch" / "touch_gesture.c"
SCREEN_MENU = ROOT / "app" / "companion_pendant" / "epaper" / "screen_menu.c"
REQ = ROOT / "docs" / "companion_product_requirements.md"
DEFAULT_OUT = ROOT / ".cache" / "validation" / "comp-req-781-power-settings-20260815" / "MENU_REFRESH_MACHINE_READY.json"


def function(source: str, start: str, end: str) -> str:
    first = source.index(start)
    last = source.index(end, first)
    return source[first:last]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    source = APP.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    gesture_source = GESTURE.read_text(encoding="utf-8")
    screen_menu_source = SCREEN_MENU.read_text(encoding="utf-8")
    req = REQ.read_text(encoding="utf-8")
    menu = function(source, "void Companion_Screen_MenuRequest(", "bool Companion_Screen_MenuRequestClean(")
    enter = function(source, "bool Companion_Screen_MenuRequestClean(", "bool Companion_Screen_MenuMaintenance(")
    exit_path = function(source, "bool Companion_Screen_ShowDailyClean(void)", "bool Companion_Screen_WakeDailyClean(void)")
    checks = {
        "submenu_view_change_selects_full": "view != s_companion_screen_presentation.menu_view" in menu and "menu_boundary=submenu" in menu,
        "same_view_updates_select_partial": "(!in_menu || submenu_boundary)" in menu and "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE" in menu,
        "internal_updates_log_partial": "menu_update=interactive" in menu and "control=0xCF" in menu,
        "no_content_change_full_branch": "menu_content_changed" not in menu and "menu_boundary=content_change" not in menu,
        "entry_is_visible_full": "COMP_EPAPER_REFRESH_VISIBLE_FULL" in enter and "menu_boundary=enter" in enter,
        "exit_is_visible_full": "COMP_EPAPER_REFRESH_VISIBLE_FULL" in exit_path and "menu_boundary=exit" in exit_path,
        "menu_tap_has_8px_gate": "TOUCH_MENU_TAP_MAX_MOVE_PX 8u" in main_source and "menu_tap suppressed=drag" in main_source,
        "menu_scroll_uses_12px_intent_lock": "TOUCH_MENU_SCROLL_ACTIVATION_PX 12u" in main_source and "comp_screen_menu_browser_drag_from(" in main_source,
        "menu_scroll_is_origin_relative_row_snap": all(token in screen_menu_source for token in (
            "comp_screen_menu_browser_drag_from(",
            "start_page",
            "distance + row_height_px / 2u",
            "rows = 1u",
        )),
        "menu_drag_survives_release_debounce": "if (contact_now && Companion_Screen_IsMenuVisible()" in main_source and "commit_menu_vertical_drag(&settle_result, release_delta_y, 'r')" in main_source,
        "owner_short_and_long_drag_replays": all(token in screen_menu_source for token in (
            "-11, 12u, 40u",
            "-12, 12u, 40u",
            "-78, 12u, 40u",
            "2u, 22, 12u, 40u",
        )),
        "release_excursion_preserved": "Keep final excursion available" in gesture_source,
        "owner_contract_registered": "### COMP-REQ-782" in req and "父页与子菜单" in req and "12 px" in req and "78 px" in req,
    }
    result = {
        "schema": "companion.comp_req_782.menu_refresh_boundary.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "contract": "HOME<->MENU and parent<->submenu full; vertical page/value/press partial; 8px tap gate + 12px origin-relative row-snap scroll",
        "checks": checks,
        "hardware_contact": 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
