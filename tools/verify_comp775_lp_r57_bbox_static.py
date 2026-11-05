#!/usr/bin/env python3
"""Verify archived r57 visible topology and selected controller handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def c_function(source: str, signature: str) -> str:
    """Return one C function without leaking checks into following functions."""
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    state = "code"
    index = brace
    while index < len(source):
        ch = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if ch == '"':
                state = "string"
            elif ch == "'":
                state = "char"
            elif ch == "/" and nxt == "/":
                state = "line_comment"
                index += 1
            elif ch == "/" and nxt == "*":
                state = "block_comment"
                index += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]
        elif state in ("string", "char"):
            if ch == "\\":
                index += 1
            elif (state == "string" and ch == '"') or (
                    state == "char" and ch == "'"):
                state = "code"
        elif state == "line_comment":
            if ch == "\n":
                state = "code"
        elif state == "block_comment" and ch == "*" and nxt == "/":
            state = "code"
            index += 1
        index += 1
    raise ValueError(f"unterminated C function: {signature}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--handoff", choices=("no-rearm", "exact-r57", "zoned-r57",
                              "fine-zoned-r57", "component-r57",
                              "component-f7-r57"),
        default="no-rearm")
    args = parser.parse_args()
    driver = args.driver.read_text(encoding="utf-8")
    main_source = args.main.read_text(encoding="utf-8")
    body = c_function(driver, "static bool ssd1681_lp_white_then_sleepy_f7(")
    wrapper = c_function(
        driver,
        "static bool ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7(")
    sleep_body = c_function(driver, "static bool ssd1681_deep_sleep_phase(")
    product_body = c_function(
        driver,
        "static comp_epaper_panel_result_t ssd1681_accepted_cached_mode2_product_refresh(")
    main_start = main_source.index(
        "if (low_power_committed && !s_epaper_deep_sleep_entered)")
    main_end = main_source.index("} else if (!low_power_committed)", main_start)
    main_body = main_source[main_start:main_end]
    checks = {
        "inverse_current_only_f7": (
            "s_frame, &window, &total_busy_ms, 0xF7u, false, false" in body),
        "two_second_controller_off_dwell": (
            "ssd1681_lp_sleep2s_reinit(&window, NULL)" in body),
        "white_dual_plane_f7": (
            "s_frame, &window, &total_busy_ms, 0xF7u, true, false" in body),
        "target_is_white_difference_bbox": (
            "target_window = ssd1681_window_from_difference();" in body),
        "target_current_only_f7": (
            ("control, false, true" in body)
            if args.handoff == "component-r57" else
            ("0xF7u, false, true" in body)),
        "no_target_c7_or_fast_profile": (
            "0xC7u" not in body and "ssd1681_prepare_vendor_fast_profile" not in body),
        "receipt_records_target_path": (
            ("[e] z=" in body if args.handoff in
             ("component-r57", "component-f7-r57") else
             "[e] lpz" in body) if args.handoff in ("zoned-r57", "fine-zoned-r57",
                                                     "component-r57",
                                                     "component-f7-r57")
            else "[e]57 " in body),
        "final_deep_sleep_latched": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in main_body),
        "real_deep_sleep_command": (
            "ssd1681_command_data(" in sleep_body and
            "0x10u, deep_sleep_mode" in sleep_body and
            "s_controller_deep_sleep = true" in sleep_body),
        "product_dispatches_r57": (
            "ok = ssd1681_lifecycle_lp_enter_inv_f7_s2_white_dual_f7_bbox24_f7("
            in product_body and "lp_enter_exit_equivalent" not in product_body),
    }
    if args.handoff in ("exact-r57", "zoned-r57", "fine-zoned-r57",
                        "component-r57", "component-f7-r57"):
        checks.update({
            "no_duplicate_driver_prequiet": "HAL_Delay(1000u)" not in body,
            "old_ram_sync_without_current_repaint": (
                re.search(
                    r"ssd1681_write_plane_region\s*\(\s*0x26u,\s*"
                    r"mapped_sleepy,\s*&target_window\s*\)", body) is not None
                and re.search(
                    r"ssd1681_write_plane_region\s*\(\s*0x24u,\s*"
                    r"mapped_sleepy", body) is None),
            "command_only_mode2_rearm": (
                "mode2_rearmed = rebaseline_complete" in body
                and "ssd1681_accepted_mode2_rearm(NULL)" in body
                and (("[e] z=" if args.handoff in
                      ("component-r57", "component-f7-r57") else
                      "m2=%u f=%u" if args.handoff in
                      ("zoned-r57", "fine-zoned-r57") else
                      "[e]57 ") in body)),
            "report_uses_old_ram_sync": (
                "report->post_sync_command = clean_ok ? 0x26u : 0u;" in wrapper
                and "report->post_sync_bytes = clean_ok ? painted_region_bytes : 0u;"
                in wrapper),
            "logical_settle_flag_preserved": (
                "s_need_mode2_settle_after_mode1_gc = clean_ok;" in wrapper),
        })
        if args.handoff in ("zoned-r57", "fine-zoned-r57", "component-r57",
                            "component-f7-r57"):
            expected_count = (11 if args.handoff in
                              ("component-r57", "component-f7-r57") else
                              5 if args.handoff == "fine-zoned-r57" else 3)
            expected_bytes = (708 if args.handoff in
                              ("component-r57", "component-f7-r57") else
                              1090 if args.handoff == "fine-zoned-r57" else 1727)
            component_bounds = (
                "{11u, 13u, 55u, 58u, true}",
                "{4u, 6u, 57u, 64u, true}",
                "{18u, 20u, 57u, 64u, true}",
                "{11u, 13u, 72u, 77u, true}",
                "{5u, 9u, 79u, 89u, true}",
                "{15u, 19u, 79u, 89u, true}",
                "{6u, 8u, 116u, 125u, true}",
                "{16u, 18u, 116u, 125u, true}",
                "{4u, 5u, 148u, 158u, true}",
                "{1u, 2u, 153u, 171u, true}",
            )
            checks.update({
                "semantic_ink_zones": (
                    f"#define SSD1681_LP_SLEEPY_INK_ZONE_COUNT {expected_count}u" in driver
                    and f"#define SSD1681_LP_SLEEPY_INK_ZONE_BYTES {expected_bytes}u" in driver),
                "zone_bounds_locked_to_active_sleepy_target": all(
                    token in body for token in (
                        ((component_bounds + ("{0u, 24u, 184u, 199u, true}",))
                         if args.handoff in
                         ("component-r57", "component-f7-r57") else
                         ("{4u, 20u, 55u, 64u, true}",
                          "{5u, 19u, 72u, 89u, true}",
                          "{6u, 18u, 116u, 125u, true}")
                         if args.handoff == "fine-zoned-r57"
                         else ("{4u, 20u, 55u, 125u, true}",))
                        + (
                        "{1u, 5u, 148u, 171u, true}",
                        "{0u, 24u, 184u, 199u, true}",
                    ) if args.handoff not in
                    ("component-r57", "component-f7-r57") else ())),
                "serial_target_f7_activations": (
                    "&target_zones[index], &total_busy_ms" in body
                    and "index < SSD1681_LP_SLEEPY_INK_ZONE_COUNT" in body),
                "zone_old_ram_sync": (
                    "ssd1681_set_window(&target_zones[index], true, false)" in body
                    and "0x26u, mapped_sleepy, &target_zones[index]" in body),
                "visible_activations_reported": (
                    "? (uint8_t)(2u + painted_region_count)" in wrapper),
                "zoned_receipt": (
                    ('"[e] z=%u' in body if args.handoff in
                     ("component-r57", "component-f7-r57") else
                     '"[e] lpz ok=%u z=%u zb=%lu m2=%u f=%u b=%lu' in body)),
            })
            if args.handoff == "component-r57":
                checks.update({
                    "ten_component_cf_then_status_f7": (
                        "? 0xF7u : 0xCFu" in body
                        and "target_mode2_ready = target_ready &&" in body),
                })
            elif args.handoff == "component-f7-r57":
                checks.update({
                    "eleven_component_f7": (
                        "0xF7u, false, true" in body
                        and "target_mode2_ready" not in body
                        and "? 0xF7u : 0xCFu" not in body),
                })
        else:
            checks.update({
                "single_bbox_target_f7": (
                    "&target_window, &total_busy_ms" in body
                    and "target_zones" not in body),
            })
    else:
        checks.update({
            "full_ram_truth_without_activation": (
                "ssd1681_write_plane_region(0x26u, mapped_sleepy, &window)" in body
                and "ssd1681_write_plane_region(0x24u, mapped_sleepy, &window)" in body),
            "no_frozen_mode2_rearm": "ssd1681_accepted_mode2_rearm" not in body,
            "receipt_records_no_rearm": "m2=0 frozen=%u" in body,
        })
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_r57_bbox_static.v3",
        "handoff": args.handoff,
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
