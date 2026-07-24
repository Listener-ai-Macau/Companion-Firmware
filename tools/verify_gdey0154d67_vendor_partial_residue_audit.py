#!/usr/bin/env python3
"""Audit Good Display's supplied partial-demo recovery behavior after residue."""

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
EPAPER = VENDOR_ROOT / "EPD_W21" / "EPAPER.c"
MAIN = VENDOR_ROOT / "User" / "main.c"
README = VENDOR_ROOT / "read me.txt"
TARGET_DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
SLOW_BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
PHYSICAL_STAGE = ROOT / ".cache/validation/wb55-vendor-partial-slow-motion-retry-3-20260720/stage-run.json"
PHYSICAL_TRACE = ROOT / ".cache/validation/wb55-vendor-partial-slow-motion-retry-3-20260720/vendor-partial-slow-motion-trace.json"
OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-residue-recovery-audit-20260720.json"
SCHEMA_ID = "companion.gdey0154d67_t03.vendor_partial_residue_recovery_audit.v1"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bvoid\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if match is None:
        return ""
    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    return ""


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def evaluate() -> dict[str, Any]:
    required = (EPAPER, MAIN, README, TARGET_DRIVER, SLOW_BUILD, PHYSICAL_STAGE, PHYSICAL_TRACE)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "NO_GO_INPUT_MISSING", "failures": missing, "checks": {}}

    epaper = EPAPER.read_text(encoding="utf-8-sig", errors="replace")
    main = MAIN.read_text(encoding="utf-8-sig", errors="replace")
    readme = README.read_text(encoding="utf-8-sig", errors="replace")
    target_driver = TARGET_DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    slow_build = SLOW_BUILD.read_text(encoding="utf-8-sig", errors="replace")
    stage = load_json(PHYSICAL_STAGE)
    trace = load_json(PHYSICAL_TRACE)
    part_update = function_body(epaper, "EPD_Part_Update")
    base_map = function_body(epaper, "EPD_SetRAMValue_BaseMap")
    white_clear = function_body(epaper, "EPD_WhiteScreen_White")
    partial_demo = re.search(
        r"EPD_SetRAMValue_BaseMap\(gImage_basemap\);(?P<body>.*?)while\(1\);",
        main,
        flags=re.DOTALL,
    )
    demo_body = partial_demo.group("body") if partial_demo is not None else ""

    checks = {
        "physical_rejection_is_residue_not_machine_failure": stage.get("status") == "FAIL"
        and stage.get("operator_review", {}).get("selected") == "失败"
        and stage.get("normal_firmware_restored") is True
        and trace.get("status") == "PASS_MACHINE_VENDOR_PARTIAL_SLOW_MOTION_TRACE",
        "supplied_partial_update_is_exactly_ff_then_20_busy": all(
            token in part_update
            for token in (
                "Epaper_Write_Command(0x22)",
                "Epaper_Write_Data(0xFF)",
                "Epaper_Write_Command(0x20)",
                "Epaper_READBUSY()",
            )
        ),
        "supplied_basemap_is_two_full_5000_byte_planes_then_normal_f7": all(
            token in base_map
            for token in (
                "Epaper_Write_Command(0x24)",
                "Epaper_Write_Command(0x26)",
                "for(i=0;i<ALLSCREEN_GRAGHBYTES;i++)",
                "EPD_Update()",
            )
        ),
        "supplied_clear_is_full_screen_white_f7_not_a_partial_residue_recovery": all(
            token in white_clear
            for token in (
                "Epaper_Write_Command(0x24)",
                "for(k=0;k<250;k++)",
                "for(i=0;i<25;i++)",
                "Epaper_Write_Data(0xff)",
                "EPD_Update()",
            )
        ),
        "supplier_time_demo_stops_after_six_partial_updates_then_full_white_clear": all(
            token in demo_body
            for token in (
                "EPD_Dis_Part_myself(",
                "if((fen_L==0)&&(miao_H==0)&&(miao_L==5))",
                "goto Clear;",
                "Clear:",
                "EPD_WhiteScreen_White();",
                "EPD_DeepSleep();",
            )
        ),
        "supplier_readme_mentions_background_stability_but_no_residue_free_continuous_claim": (
            "hardware reset operation" in readme
            and "background color will be unstable" in readme
            and "ghost" not in readme.lower()
            and "residue" not in readme.lower()
        ),
        "no_supplier_defined_partial_lut_initializer_exists": re.search(
            r"\bvoid\s+EPD_HW_Init_LUT_Partial\s*\(", epaper
        )
        is None,
        "no_supplier_defined_partial_count_or_content_preserving_recovery_exists": not any(
            token in demo_body
            for token in ("residue", "ghost", "recover", "refresh_count", "partial_count")
        ),
        "target_source_partial_payload_comes_from_current_whitened_frame": all(
            token in target_driver
            for token in (
                "static void frame_ball_motion_slow(uint8_t phase)",
                "frame_clear_white();",
                "ssd1681_write_plane_region(0x24u, s_frame, &source_regions[index])",
                "static uint8_t ssd1681_source_partial_dot_regions(ssd1681_window_t regions[2])",
            )
        ),
        "target_continuous_slow_loop_exceeds_supplier_six_update_then_clear_demo": all(
            token in slow_build
            for token in (
                "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
                "EPAPER_SSD1681_VENDOR_PARTIAL_SLOW_MOTION_DIAGNOSTIC=1",
            )
        )
        and "if((fen_L==0)&&(miao_H==0)&&(miao_L==5))" in demo_body
        and "EPD_WhiteScreen_White();" in demo_body,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "NO_GO_PHYSICAL_RESIDUE_OBSERVED_NO_SOURCE_BOUND_CONTINUOUS_RECOVERY"
        if not failures
        else "NO_GO_RESIDUE_RECOVERY_AUDIT_INCOMPLETE",
        "failures": failures,
        "checks": checks,
        "supplier_behavior": {
            "partial_update": "0x22=0xFF, 0x20, BUSY",
            "partial_demo_budget": "six EPD_Dis_Part_myself calls before goto Clear",
            "post_budget_action": "EPD_HW_Init then EPD_WhiteScreen_White (full 5000-byte 0x24, 0xF7), then deep sleep",
            "continuous_content_preserving_residue_recovery": "not supplied",
            "partial_lut": "not supplied as a defined implementation",
            "temperature_bands": "not supplied",
        },
        "target_transport_audit": {
            "current_region_payload": "target clears the generated frame to white before drawing the current dot, then writes s_frame through 0x24 for each selected source region",
            "continuous_loop_budget": "360 partial frames in the production-off slow diagnostic",
            "supplier_demo_budget": "six partial updates before full white clear and deep sleep",
            "proven_target_driver_issue": "the diagnostic's continuous-loop budget exceeds the supplied source demo; this is not evidence that a custom LUT would remove residue",
            "unproven": [
                "A panel-bound residue-free partial waveform.",
                "A content-preserving supplier recovery after repeated partial updates.",
                "Temperature applicability for either full or partial update behavior.",
            ],
        },
        "physical_observation": {
            "result": "failed",
            "failure_mode": "owner photo shows accumulated old-position black trail around the moving dot",
            "machine_trace": {
                "region_transfer_bytes": trace.get("region_transfer_bytes"),
                "region_refresh_elapsed_ms": trace.get("region_refresh_elapsed_ms"),
                "normal_firmware_restored": stage.get("normal_firmware_restored"),
            },
        },
        "required_disposition": {
            "production_expression_transport": "NO_GO",
            "new_physical_experiment": "NO_GO without new Good Display panel-bound residue-recovery source evidence",
            "custom_lut_or_waveform": "prohibited",
            "generic_timing_or_geometry_tuning": "prohibited",
            "full_screen_supplier_clear": "source-authentic but visibly interrupts animation and does not satisfy continuous-expression transport",
        },
        "source": {
            "vendor_root": str(VENDOR_ROOT),
            "epaper_c": {"path": str(EPAPER), "sha256": sha256(EPAPER)},
            "main_c": {"path": str(MAIN), "sha256": sha256(MAIN)},
            "readme": {"path": str(README), "sha256": sha256(README)},
            "target_driver": {"path": rel(TARGET_DRIVER), "sha256": sha256(TARGET_DRIVER)},
            "slow_build": {"path": rel(SLOW_BUILD), "sha256": sha256(SLOW_BUILD)},
            "physical_stage": {"path": rel(PHYSICAL_STAGE), "sha256": sha256(PHYSICAL_STAGE)},
            "physical_trace": {"path": rel(PHYSICAL_TRACE), "sha256": sha256(PHYSICAL_TRACE)},
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    try:
        report = evaluate()
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: cannot audit vendor partial residue recovery: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_id": SCHEMA_ID,
        "claim_scope": "read-only Good Display source plus failed physical residue observation; no waveform change",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        **report,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: vendor partial residue-recovery audit -> {rel(output)}")
    return 0 if report["status"] == "NO_GO_PHYSICAL_RESIDUE_OBSERVED_NO_SOURCE_BOUND_CONTINUOUS_RECOVERY" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
