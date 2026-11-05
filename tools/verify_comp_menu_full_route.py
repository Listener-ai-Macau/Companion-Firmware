#!/usr/bin/env python3
"""Audit every generated WB55 browser-menu row and its target-side route."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_freertos/generated"
    / "companion_browser_interaction_contract.h"
)
MENU = ROOT / "app/companion_pendant/epaper/screen_menu.c"
MENU_HEADER = ROOT / "app/companion_pendant/epaper/screen_menu.h"
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"


def enum_values(text: str, prefix: str) -> dict[int, str]:
    values: dict[int, str] = {}
    for name, value in re.findall(
        rf"\b({re.escape(prefix)}[A-Z0-9_]+)\s*=\s*(\d+)u", text
    ):
        values[int(value)] = name
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    contract = CONTRACT.read_text(encoding="utf-8")
    menu = MENU.read_text(encoding="utf-8")
    menu_header = MENU_HEADER.read_text(encoding="utf-8")
    target = MAIN.read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    kind_names = enum_values(contract, "COMPANION_BROWSER_MENU_KIND_")
    item_names = enum_values(contract, "COMPANION_BROWSER_MENU_ITEM_")
    screen_count = int(
        re.search(r"COMPANION_BROWSER_MENU_SCREEN_COUNT\s+(\d+)u", contract).group(1)
    )
    row_count = int(
        re.search(r"COMPANION_BROWSER_MENU_ROW_COUNT\s+(\d+)u", contract).group(1)
    )
    rows_block = re.search(
        r"companion_browser_menu_rows\s*\[.*?\]\s*=\s*\{(.*?)\n\};",
        contract,
        re.S,
    ).group(1)
    rows = [
        tuple(map(int, match))
        for match in re.findall(
            r"\{(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u\}",
            rows_block,
        )
    ]

    navigation_graph: dict[int, set[int]] = {
        screen: set() for screen in range(screen_count)
    }

    setting_items = {
        "COMPANION_BROWSER_MENU_ITEM_RECORDER_PROFILE",
        "COMPANION_BROWSER_MENU_ITEM_RECORDING_LIMIT",
        "COMPANION_BROWSER_MENU_ITEM_AUTO_STOP",
        "COMPANION_BROWSER_MENU_ITEM_CLOCK_FORMAT",
        "COMPANION_BROWSER_MENU_ITEM_AUTO_RECONNECT",
        "COMPANION_BROWSER_MENU_ITEM_TIME_ZONE",
        "COMPANION_BROWSER_MENU_ITEM_QUIET_HOURS",
        "COMPANION_BROWSER_MENU_ITEM_CORNER_DOUBLE_TAP",
        "COMPANION_BROWSER_MENU_ITEM_EDGE_PULL",
        "COMPANION_BROWSER_MENU_ITEM_INTERACTION_LEVEL",
        "COMPANION_BROWSER_MENU_ITEM_GAZE_FOLLOW",
        "COMPANION_BROWSER_MENU_ITEM_NATURAL_BLINK",
        "COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP",
        "COMPANION_BROWSER_MENU_ITEM_ZH_CN",
        "COMPANION_BROWSER_MENU_ITEM_EN",
    }
    action_items = {
        "COMPANION_BROWSER_MENU_ITEM_PAIR",
        "COMPANION_BROWSER_MENU_ITEM_CONNECTION_TOGGLE",
        "COMPANION_BROWSER_MENU_ITEM_RESET_NAME",
        "COMPANION_BROWSER_MENU_ITEM_SLEEP_NOW",
        "COMPANION_BROWSER_MENU_ITEM_CONFIRM_CLEAR",
        "COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE",
    }

    row_errors: list[str] = []
    seen_positions: set[tuple[int, int]] = set()
    seen_settings: set[str] = set()
    seen_actions: set[str] = set()
    kinds = Counter()
    for screen, index, kind, route_target, item in rows:
        position = (screen, index)
        if position in seen_positions:
            row_errors.append(f"duplicate row {position}")
        seen_positions.add(position)
        if screen >= screen_count:
            row_errors.append(f"screen {screen} is out of range")
        if kind not in kind_names:
            row_errors.append(f"unknown kind {kind} at {position}")
        if item not in item_names:
            row_errors.append(f"unknown item {item} at {position}")
            continue
        item_name = item_names[item]
        kind_name = kind_names.get(kind, f"kind-{kind}")
        kinds[kind_name] += 1
        if kind_name == "COMPANION_BROWSER_MENU_KIND_NAVIGATE":
            if route_target >= screen_count:
                row_errors.append(f"navigate target {route_target} is invalid at {position}")
            else:
                navigation_graph[screen].add(route_target)
        elif route_target != 255:
            row_errors.append(f"non-navigation row {position} has target {route_target}")
        if kind_name in {
            "COMPANION_BROWSER_MENU_KIND_TOGGLE",
            "COMPANION_BROWSER_MENU_KIND_CYCLE",
            "COMPANION_BROWSER_MENU_KIND_OPTION",
        }:
            seen_settings.add(item_name)
        if kind_name == "COMPANION_BROWSER_MENU_KIND_ACTION":
            seen_actions.add(item_name)

    reachable = {0}
    frontier = [(0, 0)]
    maximum_depth = 0
    while frontier:
        screen, depth = frontier.pop(0)
        maximum_depth = max(maximum_depth, depth)
        for target_screen in navigation_graph[screen]:
            if target_screen not in reachable:
                reachable.add(target_screen)
                frontier.append((target_screen, depth + 1))

    action_complete = {
        name: name in menu for name in sorted(action_items)
    }
    checks = {
        "contract_has_13_screens": screen_count == 13,
        "contract_has_63_rows": row_count == 63 and len(rows) == 63,
        "every_row_position_and_target_is_valid": not row_errors,
        "every_screen_is_reachable_from_root": (
            reachable == set(range(screen_count))
        ),
        "navigation_depth_fits_bounded_history": (
            maximum_depth <= 4
            and "COMP_SCREEN_MENU_NAV_HISTORY_DEPTH 4u" in menu_header
        ),
        "all_back_paths_share_context_restore": all(token in menu for token in (
            "comp_screen_menu_navigate_to(",
            "comp_screen_menu_back(",
            "navigation_pages",
        )),
        "every_setting_row_has_runtime_mutator": (
            seen_settings == setting_items
            and all(name in menu for name in setting_items)
            and "apply_browser_setting" in menu
        ),
        "every_action_is_acknowledged_by_menu_state": (
            seen_actions == action_items and all(action_complete.values())
        ),
        "pair_routes_to_real_ble_reconnect": (
            "COMP_SCREEN_MENU_ACTION_BROWSER_PAIR" in target
            and "process_touch_menu_phone_reconnect();" in target
        ),
        "connection_toggle_routes_to_real_ble": (
            "COMP_SCREEN_MENU_ACTION_BROWSER_CONNECTION_TOGGLE" in target
            and 'Companion_Ble_RequestDisconnect("browser_menu")' in target
        ),
        "sleep_now_routes_to_low_power_request": (
            "COMP_SCREEN_MENU_ACTION_BROWSER_SLEEP_NOW" in target
            and "Companion_Screen_EnterLowPowerIdle()" in target
        ),
        "restore_defaults_persists": (
            "COMPANION_BROWSER_MENU_ITEM_CONFIRM_RESTORE" in target
            and "(void)save_power_settings();" in target
        ),
        "clear_recordings_routes_to_flash_delete_all": (
            "COMPANION_BROWSER_MENU_ITEM_CONFIRM_CLEAR" in target
            and "Companion_RecordingFlash_Delete(\n                2u, 0u, 0u, NULL)"
            in target
        ),
        "action_success_requires_target_acceptance": (
            "if (!action_accepted)" in target
            and "reason=target_rejected" in target
            and target.index("if (!action_accepted)")
            < target.index("COMP_SCREEN_MENU_FLAG_ACTION_RESULT", target.index("if (!action_accepted)"))
        ),
        "clear_recordings_reports_async_queue": (
            "browser_menu_clear target=recording_flash" in target
            and "operation=delete_all queued=1" in target
        ),
        "reset_name_is_truthful_for_fixed_default_name": (
            "COMPANION_BROWSER_MENU_ITEM_RESET_NAME" in target
            and "browser_menu_reset_name " in target
            and "target=fixed_gap_name already_default=1" in target
        ),
        "physical_target_uses_generated_browser_not_shadow_menu": (
            '#include "companion_browser_interaction_contract.h"' in menu
            and "companion_browser_menu_row(" in menu
            and "menu_v5_target_bridge.h" not in app_ble
            and "menu_v5_contract.c" not in makefile
            and "menu_v5_target_bridge.c" not in makefile
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "MACHINE_READY" if not failed else "NO_GO"
    result = {
        "schema": "companion.wb55.browser_menu_full_route.v1",
        "status": status,
        "contract": {
            "screens": screen_count,
            "rows": len(rows),
            "kind_counts": dict(sorted(kinds.items())),
            "setting_items": sorted(seen_settings),
            "action_items": sorted(seen_actions),
            "row_errors": row_errors,
            "reachable_screens": sorted(reachable),
            "maximum_navigation_depth": maximum_depth,
        },
        "checks": checks,
        "failed_checks": failed,
        "hardware_contact": 0,
        "destructive_clear_executed": False,
    }
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if status == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
