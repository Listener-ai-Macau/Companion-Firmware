#!/usr/bin/env python3
"""Audit the supplied Good Display partial path against the WB55 diagnostic transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR_ROOT = pathlib.Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷")
VENDOR_EPAPER = VENDOR_ROOT / "EPD_W21" / "EPAPER.c"
VENDOR_MAIN = VENDOR_ROOT / "User" / "main.c"
TARGET_DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
SLOW_TRACE = ROOT / ".cache/validation/wb55-vendor-partial-slow-motion-retry-3-20260720/vendor-partial-slow-motion-trace.json"
SLOW_STAGE = ROOT / ".cache/validation/wb55-vendor-partial-slow-motion-retry-3-20260720/stage-run.json"
SLOW_RAW_LOG = ROOT / ".cache/validation/wb55-vendor-partial-slow-motion-retry-3-20260720/capture/nucleo-serial-raw.log"
OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-target-partial-transport-audit-20260720.json"
SCHEMA_ID = "companion.gdey0154d67_t03.target_partial_transport_audit.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def contains_all(source: str, tokens: tuple[str, ...]) -> bool:
    return all(token in source for token in tokens)


def parse_partial_timings(log: str) -> list[tuple[int, int]]:
    """Return source-partial payload and BUSY-refresh times from one raw trace."""
    matches = re.findall(
        r"refresh mode=differential profile=good_display_vendor_partial_source "
        r"control=0xFF.*?elapsed_ms=(\d+).*?\n"
        r"\[epaper\] timing mode=differential .*?transfer_before_waveform_ms=(\d+) "
        r".*?bytes=(\d+) data_planes=1",
        log,
        flags=re.DOTALL,
    )
    return [(int(elapsed_ms), int(transfer_ms)) for elapsed_ms, transfer_ms, _ in matches]


def extract_multi_region_source(source: str) -> str:
    match = re.search(
        r"void EPD_Dis_Part_myself\(.*?(?=//Loading waveform)",
        source,
        flags=re.DOTALL,
    )
    return "" if match is None else match.group(0)


def build_report() -> dict[str, Any]:
    required = (
        VENDOR_EPAPER,
        VENDOR_MAIN,
        TARGET_DRIVER,
        SOURCE_AUDIT,
        SLOW_TRACE,
        SLOW_STAGE,
        SLOW_RAW_LOG,
    )
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {
            "schema_id": SCHEMA_ID,
            "status": "NO_GO_TRANSPORT_AUDIT_INPUT_MISSING",
            "failures": missing,
            "checks": {},
        }

    vendor_epaper = VENDOR_EPAPER.read_text(encoding="utf-8-sig", errors="replace")
    vendor_main = VENDOR_MAIN.read_text(encoding="utf-8-sig", errors="replace")
    target = TARGET_DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    source_audit = load_json(SOURCE_AUDIT)
    trace = load_json(SLOW_TRACE)
    stage = load_json(SLOW_STAGE)
    partial_timings = parse_partial_timings(SLOW_RAW_LOG.read_text(encoding="utf-8", errors="replace"))
    multi_region_source = extract_multi_region_source(vendor_epaper)
    critical = source_audit.get("source_manifest", {}).get("critical_sources", {})
    target_binding = critical.get("current_ssd1681_target", {}).get("sha256")
    vendor_binding = critical.get("epaper_c", {}).get("sha256")

    checks = {
        "source_audit_binds_current_target_and_vendor_hashes": (
            source_audit.get("machine_status") == "PASS_AUDIT_COMPLETE"
            and source_audit.get("promotion_status") == "NO_GO_PANEL_IDENTITY_UNPROVEN"
            and target_binding == digest(TARGET_DRIVER)
            and vendor_binding == digest(VENDOR_EPAPER)
        ),
        "vendor_partial_data_polarity_is_white_ff_black_zero": contains_all(
            vendor_epaper,
            (
                "write RAM for black(0)/white (1)",
                "Epaper_Write_Data(0xff)",
            ),
        ),
        "target_partial_data_polarity_is_white_ff_black_zero": contains_all(
            target,
            (
                "memset(s_frame, 0xFF, sizeof(s_frame));",
                "s_frame[index] &= (uint8_t)~mask;",
                "s_frame[index] |= mask;",
            ),
        ),
        "vendor_partial_sequence_has_10ms_reset_border_window_counter_24_ff_20_busy": contains_all(
            vendor_epaper,
            (
                "void EPD_Dis_Part_myself(",
                "driver_delay_xms(10)",
                "Epaper_Write_Command(0x3C)",
                "Epaper_Write_Data(0x80)",
                "Epaper_Write_Command(0x44)",
                "Epaper_Write_Command(0x45)",
                "Epaper_Write_Command(0x4E)",
                "Epaper_Write_Command(0x4F)",
                "Epaper_Write_Command(0x24)",
                "Epaper_Write_Data(0xFF)",
                "Epaper_Write_Command(0x20)",
                "Epaper_READBUSY()",
            ),
        ),
        "vendor_source_supports_five_separate_ram_regions_before_one_partial_activation": (
            multi_region_source.count("Epaper_Write_Command(0x24)") == 5
            and multi_region_source.count("EPD_Part_Update();") == 1
            and all(
                token in multi_region_source
                for token in (
                    "//Data A",
                    "//Data B",
                    "//Data C",
                    "//Data D",
                    "//Data E",
                    "Epaper_Write_Command(0x44)",
                    "Epaper_Write_Command(0x45)",
                    "Epaper_Write_Command(0x4E)",
                    "Epaper_Write_Command(0x4F)",
                )
            )
        ),
        "target_partial_sequence_has_source_reset_border_window_counter_24_ff_20_busy": contains_all(
            target,
            (
                "static void ssd1681_reset(void)",
                "HAL_Delay(10u);",
                "vendor_partial_source region_reset low_ms=10 high_ms=10",
                "static bool ssd1681_set_window_vendor_partial_source",
                "ssd1681_command_data(0x3Cu, border_lock",
                "ssd1681_command_data(0x44u, ram_x",
                "ssd1681_command_data(0x45u, ram_y",
                "ssd1681_command_data(0x4Eu, x_counter",
                "ssd1681_command_data(0x4Fu, y_counter",
                "ssd1681_write_plane_region(0x24u, s_frame",
                "? 0xFFu",
                "ssd1681_command(0x20u)",
            ),
        ),
        "target_updates_whitened_old_region_and_current_region_from_one_frame": contains_all(
            target,
            (
                "static void frame_ball_motion_slow(uint8_t phase)",
                "frame_clear_white();",
                "static uint8_t ssd1681_source_partial_dot_regions",
                "previous = ssd1681_window_from_black_pixels(s_previous_frame);",
                "current = ssd1681_window_from_black_pixels(s_frame);",
                "ssd1681_write_plane_region(0x24u, s_frame, &source_regions[index])",
            ),
        ),
        "default_differential_path_uses_actual_changed_window_old_new_planes_and_identical_skip": contains_all(
            target,
            (
                "static ssd1681_window_t ssd1681_window_from_difference(void)",
                "if (s_frame[row_offset + x] == s_previous_frame[row_offset + x])",
                "window = partial ? ssd1681_window_from_difference() : ssd1681_window_full();",
                "if (partial && !window.changed)",
                "differential_skip identical_frame",
                "ssd1681_write_plane_region(0x26u, s_previous_frame, &window)",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
            ),
        ),
        "target_transform_and_controller_y_mapping_are_explicit": contains_all(
            target,
            (
                "frame_apply_target_rotation();",
                "frame_apply_horizontal_mirror();",
                "controller_y_start = (SSD1681_HEIGHT - 1u) - window->y_start;",
                "controller_y_end = (SSD1681_HEIGHT - 1u) - window->y_end;",
            ),
        ),
        "physical_trace_proves_each_tested_partial_used_one_source_reset_ff_20_busy": (
            trace.get("status") == "PASS_MACHINE_VENDOR_PARTIAL_SLOW_MOTION_TRACE"
            and trace.get("checks", {}).get("each_later_frame_uses_one_10ms_reset_one_ff_20_busy")
            is True
            and trace.get("checks", {}).get("each_later_frame_has_one_or_two_successful_0x24_regions_below_accepted_limit")
            is True
        ),
        "owner_photo_rejected_continuous_partial_for_residue_with_normal_restore": (
            stage.get("status") == "FAIL"
            and stage.get("operator_review", {}).get("selected") == "失败"
            and stage.get("normal_firmware_restored") is True
        ),
        "supplier_demo_has_six_updates_then_full_white_clear_not_continuous_recovery": contains_all(
            vendor_main,
            (
                "EPD_SetRAMValue_BaseMap(gImage_basemap);",
                "EPD_Dis_Part_myself(",
                "if((fen_L==0)&&(miao_H==0)&&(miao_L==5))",
                "goto Clear;",
                "Clear:",
                "EPD_WhiteScreen_White();",
                "EPD_DeepSleep();",
            ),
        ),
        "source_partial_waveform_busy_dominates_payload_transfer": (
            len(partial_timings) >= 5
            and all(refresh_ms >= 400 and transfer_ms <= 15
                    for refresh_ms, transfer_ms in partial_timings[:5])
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    status = (
        "NO_GO_CONTINUOUS_DYNAMIC_NEEDS_PANEL_BOUND_WAVEFORM_RECOVERY"
        if not failures
        else "NO_GO_TARGET_PARTIAL_TRANSPORT_AUDIT_INCOMPLETE"
    )
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": "read-only source-vs-target transport audit; no LUT synthesis, production policy change, or physical promotion",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "checks": checks,
        "failures": failures,
        "match_conclusion": {
            "matched": [
                "Data polarity: 0xFF is white and cleared bits are black.",
                "Each tested partial performs the supplier-style 10 ms reset, border lock, RAM window/counters, one 0x24 region write, 0xFF control, 0x20 activation and BUSY completion.",
                "The target makes transform and SSD1681 descending-Y mapping explicit; the physical trace records the configured transform for each tested frame.",
                "Old dot pixels are whitened in the target frame before the old/current selected regions are written.",
                "The ordinary differential path independently derives the byte-aligned changed window from the previous and current frame, skips an identical frame, and transmits both its old and current pixels.",
                "The supplier's EPD_Dis_Part_myself transport programs five distinct RAM regions before one partial activation, so non-contiguous dirty islands are source-backed as a data-volume optimization.",
            ],
            "proven_mismatch": "The operator slow-motion diagnostic deliberately extended the supplier demo from six partial updates to 360 continuous partial frames. The owner photo records residue during that extension.",
            "not_a_proven_mismatch": [
                "No omitted source partial reset, border, RAM-window, data-polarity, 0x24, 0xFF, 0x20 or BUSY command was found in the tested path.",
                "No source evidence permits deriving different LUT bytes, drive voltages, temperature bands or waveform timing.",
                "The measured 75-81 byte source-partial payload takes 11 ms before activation, while the panel remains BUSY for 446-447 ms; further payload/SPI reduction cannot materially change cadence or residue.",
                "Five-region staging is not a new partial waveform or a residue-recovery sequence: it ends in the same source 0xFF/0x20/BUSY activation that left residual image in the physical continuous-motion run.",
            ],
        },
        "disposition": {
            "production_dynamic_expression": "NO_GO",
            "self_authored_waveform_or_lut": "prohibited",
            "source_authentic_six_update_recovery": "would be a full-white 0x24/F7 clear and visibly interrupts animation, so it does not satisfy the owner requirement",
            "source_bounded_multi_region_transport": "The vendor source permits at most five preloaded local regions before one existing partial activation; it is diagnostic-only until identity and rail gates pass, and it cannot make a no-residue claim.",
            "next_required_supplier_input": "Exact-panel partial waveform/recovery guidance that preserves content after repeated partial updates, plus its temperature applicability.",
        },
        "timing_evidence": {
            "source_partial_samples": [
                {
                    "busy_refresh_ms": refresh_ms,
                    "payload_transfer_before_activation_ms": transfer_ms,
                    "payload_share_percent": round((100.0 * transfer_ms) / refresh_ms, 1),
                }
                for refresh_ms, transfer_ms in partial_timings[:5]
            ],
            "conclusion": "Panel waveform/BUSY time, not the 75-81 byte SPI payload, dominates observed source-partial cadence.",
        },
        "source": {
            "vendor_epaper_c": {"path": str(VENDOR_EPAPER), "sha256": digest(VENDOR_EPAPER)},
            "vendor_main_c": {"path": str(VENDOR_MAIN), "sha256": digest(VENDOR_MAIN)},
            "target_driver": {"path": rel(TARGET_DRIVER), "sha256": digest(TARGET_DRIVER)},
            "source_audit": {"path": rel(SOURCE_AUDIT), "sha256": digest(SOURCE_AUDIT)},
            "slow_trace": {"path": rel(SLOW_TRACE), "sha256": digest(SLOW_TRACE)},
            "slow_stage": {"path": rel(SLOW_STAGE), "sha256": digest(SLOW_STAGE)},
            "slow_raw_log": {"path": rel(SLOW_RAW_LOG), "sha256": digest(SLOW_RAW_LOG)},
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    try:
        report = build_report()
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: cannot audit target partial transport: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: target partial transport audit -> {rel(output)}")
    return 0 if report["status"] == "NO_GO_CONTINUOUS_DYNAMIC_NEEDS_PANEL_BOUND_WAVEFORM_RECOVERY" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
