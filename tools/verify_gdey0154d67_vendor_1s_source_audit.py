#!/usr/bin/env python3
"""Audit the read-only Good Display one-second LUT package without promoting it."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR_ROOT = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷"
)
EPAPER_REL = pathlib.PurePosixPath("EPD_W21/EPAPER.c")
HEADER_REL = pathlib.PurePosixPath("EPD_W21/EPAPER.h")
README_REL = pathlib.PurePosixPath("read me.txt")
PANEL_TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DEFAULT_OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
SCHEMA_ID = "companion.gdey0154d67_t03.vendor_1s_source_audit.v1"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def digest(path: pathlib.Path) -> str:
    return digest_bytes(path.read_bytes())


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\bvoid\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", text)
    if match is None:
        return ""
    depth = 0
    for index in range(match.end() - 1, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    return ""


def command_data_sequence(body: str, command: int, values: list[int]) -> bool:
    pattern = rf"Epaper_Write_Command\s*\(\s*0x{command:02X}\s*\)"
    match = re.search(pattern, body, flags=re.IGNORECASE)
    if match is None:
        return False
    cursor = match.end()
    for value in values:
        next_data = re.search(
            rf"Epaper_Write_Data\s*\(\s*0x{value:02X}\s*\)",
            body[cursor:],
            flags=re.IGNORECASE,
        )
        if next_data is None:
            return False
        cursor += next_data.end()
    return True


def extract_lut(epaper_text: str) -> list[int]:
    active = strip_block_comments(epaper_text)
    match = re.search(
        r"\bconst\s+unsigned\s+char\s+LUT_DATA\s*\[\s*159\s*\]\s*=\s*\{(?P<body>.*?)\}\s*;",
        active,
        flags=re.DOTALL,
    )
    if match is None:
        return []
    return [int(token, 16) for token in re.findall(r"0x([0-9A-Fa-f]{2})", match.group("body"))]


def extract_target_vendor_lut(driver_text: str) -> list[int]:
    match = re.search(
        r"\bstatic\s+const\s+uint8_t\s+ssd1681_vendor_1s_lut\s*"
        r"\[\s*159\s*\]\s*=\s*\{(?P<body>.*?)\}\s*;",
        driver_text,
        flags=re.DOTALL,
    )
    if match is None:
        return []
    return [int(token, 16) for token in re.findall(r"0x([0-9A-Fa-f]{2})", match.group("body"))]


def manifest_tree(root: pathlib.Path) -> list[dict[str, Any]]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in files
    ]


def source_check(condition: bool, name: str, failures: list[str]) -> bool:
    if not condition:
        failures.append(name)
    return condition


def evaluate(vendor_root: pathlib.Path) -> dict[str, Any]:
    epaper = vendor_root / EPAPER_REL
    header = vendor_root / HEADER_REL
    readme = vendor_root / README_REL
    failures: list[str] = []
    missing = [str(path.relative_to(vendor_root)) for path in (epaper, header, readme) if not path.is_file()]
    if missing:
        return {
            "machine_status": "FAIL_SOURCE_INPUT_MISSING",
            "promotion_status": "NO_GO_SOURCE_INPUT_MISSING",
            "failures": missing,
        }

    epaper_text = epaper.read_text(encoding="utf-8", errors="replace")
    header_text = header.read_text(encoding="utf-8", errors="replace")
    readme_text = readme.read_text(encoding="utf-8", errors="replace")
    lut = extract_lut(epaper_text)
    lut_bytes = bytes(lut)
    active = strip_block_comments(epaper_text)
    normal_init = function_body(active, "EPD_HW_Init")
    lut_init = function_body(active, "EPD_HW_Init_LUT")
    normal_update = function_body(active, "EPD_Update")
    partial_update = function_body(active, "EPD_Part_Update")
    lut_update = function_body(active, "EPD_Update_LUT")
    lut_full = function_body(active, "EPD_WhiteScreen_ALL_LUT")
    base_map = function_body(active, "EPD_SetRAMValue_BaseMap")
    partial = function_body(active, "EPD_Dis_Part")
    partial_myself = function_body(active, "EPD_Dis_Part_myself")
    driver = PANEL_TARGET.read_text(encoding="utf-8-sig", errors="replace")
    target_vendor_lut = extract_target_vendor_lut(driver)

    tail = lut[153:] if len(lut) == 159 else []
    vendor_checks = {
        "lut_declares_159_bytes": bool(re.search(r"LUT_DATA\s*\[\s*159\s*\]", active)),
        "lut_has_exactly_159_literals": len(lut) == 159,
        "load_0x32_has_exactly_153_payload_bytes": bool(
            re.search(r"Epaper_Write_Command\s*\(\s*0x32\s*\).*?count\s*<\s*153", function_body(active, "EPD_select_LUT"), re.DOTALL)
        ),
        "lut_tail_is_bound_to_0x3f_0x03_0x04_0x2c": tail == [0x22, 0x17, 0x41, 0xA8, 0x32, 0x58]
        and all(
            token in lut_init
            for token in ("0x3F", "LUT_DATA[153]", "0x03", "LUT_DATA[154]", "0x04", "LUT_DATA[155]", "LUT_DATA[156]", "LUT_DATA[157]", "0x2C", "LUT_DATA[158]")
        ),
        "normal_full_update_is_0xf7_then_0x20": command_data_sequence(normal_update, 0x22, [0xF7])
        and bool(re.search(r"Epaper_Write_Command\s*\(\s*0x20\s*\)", normal_update, re.I)),
        "lut_fast_update_is_0xc7_then_0x20": command_data_sequence(lut_update, 0x22, [0xC7])
        and bool(re.search(r"Epaper_Write_Command\s*\(\s*0x20\s*\)", lut_update, re.I)),
        "full_lut_frame_is_0x24_one_5000_byte_plane": bool(
            re.search(r"Epaper_Write_Command\s*\(\s*0x24\s*\).*?i\s*<\s*5000", lut_full, re.DOTALL | re.I)
        ),
        "resolution_declares_200x200_and_5000_bytes": all(
            token in header_text for token in ("MAX_LINE_BYTES 25", "MAX_COLUMN_BYTES  200", "ALLSCREEN_GRAGHBYTES\t5000")
        ),
        "busy_waits_for_low_ready": "if(isEPD_W21_BUSY==0) break" in active,
        "reset_and_normal_border_are_explicit": "EPD_W21_RST_0" in normal_init
        and "EPD_W21_RST_1" in normal_init
        and command_data_sequence(normal_init, 0x3C, [0x05]),
        "partial_path_resets_and_locks_border_0x80": "EPD_W21_RST_0" in partial
        and "EPD_W21_RST_1" in partial
        and command_data_sequence(partial, 0x3C, [0x80]),
        "partial_path_uses_10ms_reset_region_0x24_and_0xff_0x20": all(
            token in partial
            for token in (
                "driver_delay_xms(10)",
                "Epaper_Write_Command(0x24)",
                "PART_COLUMN*PART_LINE/8",
                "EPD_Part_Update();",
            )
        )
        and command_data_sequence(partial_update, 0x22, [0xFF])
        and bool(re.search(r"Epaper_Write_Command\s*\(\s*0x20\s*\)", partial_update, re.I)),
        "partial_basemap_writes_0x24_then_0x26_before_normal_f7": all(
            token in base_map
            for token in (
                "Epaper_Write_Command(0x24)",
                "Epaper_Write_Command(0x26)",
                "ALLSCREEN_GRAGHBYTES",
                "EPD_Update();",
            )
        )
        and base_map.find("Epaper_Write_Command(0x24)") < base_map.find("Epaper_Write_Command(0x26)"),
        "partial_multi_region_path_uses_one_reset_border_five_0x24_then_one_ff_0x20": "EPD_W21_RST_0" in partial_myself
        and "EPD_W21_RST_1" in partial_myself
        and "driver_delay_xms(10)" in partial_myself
        and command_data_sequence(partial_myself, 0x3C, [0x80])
        and partial_myself.count("Epaper_Write_Command(0x24)") == 5
        and partial_myself.count("EPD_Part_Update();") == 1
        and command_data_sequence(partial_update, 0x22, [0xFF])
        and bool(re.search(r"Epaper_Write_Command\s*\(\s*0x20\s*\)", partial_update, re.I)),
        "readme_requires_post_partial_hardware_reset_and_border_change": "hardware reset" in readme_text.lower()
        and "0x05-->0x80" in readme_text,
    }
    for name, passed in vendor_checks.items():
        source_check(passed, name, failures)

    driver_checks = {
        "target_declares_200x200_5000_bytes": all(
            token in driver
            for token in ("#define SSD1681_WIDTH 200u", "#define SSD1681_HEIGHT 200u", "SSD1681_FRAME_BYTES")
        ),
        "target_full_window_is_25_by_200": "x_end_byte = SSD1681_BYTES_PER_ROW - 1u" in driver
        and "y_end = SSD1681_HEIGHT - 1u" in driver,
        "target_full_recovery_is_0x24_one_plane_then_0xf7_0x20": all(
            token in driver
            for token in (
                "good_display_official_0x24_only",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
                "0xF7u",
                "ssd1681_command(0x20u)",
            )
        ),
        "target_busy_is_high_active_low_ready": "#define SSD1681_BUSY_READY_LEVEL GPIO_PIN_RESET" in driver,
        "target_normal_border_is_0x05": "static const uint8_t normal_border[] = {0x05u};" in driver,
        "target_vendor_lut_is_not_present_in_production": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC 0",
                "#if COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC",
                "Literal, source-bound copy of Good Display's active 159-byte LUT_DATA.",
            )
        ),
        "target_vendor_lut_diagnostic_is_verbatim": target_vendor_lut == lut,
        "target_fast_profile_is_distinct_from_new_vendor_lut": "good_display_mode1" in driver
        and "ssd1681_prepare_vendor_fast_profile" in driver,
        "target_vendor_partial_operator_loop_is_default_off": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC 0",
                "SSD1681 vendor partial operator loop requires the vendor partial diagnostic path",
            )
        ),
        "target_vendor_partial_operator_loop_matches_basemap_and_region_sequence": all(
            token in driver
            for token in (
                "ssd1681_reset_vendor_partial_basemap",
                "vendor_partial_source basemap_reset low_ms=100 high_ms=100",
                "vendor_partial_source region_reset low_ms=10 high_ms=10",
                "ssd1681_set_window_vendor_partial_source",
                "static const uint8_t border_lock[] = {0x80u};",
                "good_display_vendor_partial_basemap_0x24_then_0x26",
                "ssd1681_write_plane_region(0x24u, s_frame, &window) &&\n                            ssd1681_write_plane_region(0x26u, s_frame, &window)",
                "good_display_vendor_partial_source",
            )
        ),
    }
    for name, passed in driver_checks.items():
        source_check(passed, name, failures)

    identity_evidence = {
        "target_string_present_in_vendor_text": "GDEY0154D67-T03" in (epaper_text + header_text + readme_text),
        "controller_identity_ssd1681_or_ssd1680_is_explicit": bool(re.search(r"SSD168[01]", epaper_text + header_text, re.I)),
        "resolution_200x200_is_explicit": vendor_checks["resolution_declares_200x200_and_5000_bytes"],
        "data_polarity_is_documented": "black(0)/white (1)" in epaper_text,
        "init_order_can_be_audited": all(
            vendor_checks[name]
            for name in (
                "reset_and_normal_border_are_explicit",
                "busy_waits_for_low_ready",
                "normal_full_update_is_0xf7_then_0x20",
            )
        ),
        "temperature_banded_cwf1_table_is_documented": False,
    }
    identity_unproven = [
        name
        for name, passed in identity_evidence.items()
        if not passed and name in ("target_string_present_in_vendor_text", "temperature_banded_cwf1_table_is_documented")
    ]
    machine_status = "PASS_AUDIT_COMPLETE" if not failures else "FAIL_AUDIT_EXTRACTION_OR_STATIC_CONTRACT"
    promotion_status = (
        "NO_GO_PANEL_IDENTITY_UNPROVEN"
        if machine_status == "PASS_AUDIT_COMPLETE" and identity_unproven
        else "NO_GO_AUDIT_FAILURE" if failures else "NO_GO_TEMPERATURE_CWF1_UNPROVEN"
    )
    tree = manifest_tree(vendor_root)
    return {
        "machine_status": machine_status,
        "promotion_status": promotion_status,
        "failures": failures,
        "identity_unproven": identity_unproven,
        "vendor_checks": vendor_checks,
        "driver_checks": driver_checks,
        "identity_evidence": identity_evidence,
        "source_manifest": {
            "vendor_root": str(vendor_root),
            "vendor_tree_sha256": digest_bytes(
                "\n".join(f"{item['path']} {item['sha256']}" for item in tree).encode("utf-8")
            ),
            "file_count": len(tree),
            "files": tree,
            "critical_sources": {
                "epaper_c": {"path": str(epaper), "sha256": digest(epaper)},
                "epaper_h": {"path": str(header), "sha256": digest(header)},
                "readme": {"path": str(readme), "sha256": digest(readme)},
                "current_ssd1681_target": {"path": rel(PANEL_TARGET), "sha256": digest(PANEL_TARGET)},
            },
            "lut_data": {
                "declared_bytes": 159,
                "literal_count": len(lut),
                "sha256": digest_bytes(lut_bytes),
                "load_command": "0x32",
                "load_payload_bytes": 153,
                "tail_bindings": {
                    "0x3F": [f"0x{value:02X}" for value in tail[0:1]],
                    "0x03": [f"0x{value:02X}" for value in tail[1:2]],
                    "0x04": [f"0x{value:02X}" for value in tail[2:5]],
                    "0x2C": [f"0x{value:02X}" for value in tail[5:6]],
                },
            },
        },
        "verbatim_diff": {
            "matching_evidence": [
                "200x200 / 5000-byte full-plane geometry is explicit in both sources.",
                "Both audited full paths use 0x24 for the current plane, 0x22=0xF7, 0x20 and BUSY completion.",
                "Both sources use normal border 0x3C=0x05; the vendor partial path hard-resets and uses 0x3C=0x80.",
                "Both sources treat BUSY high as active and low as ready.",
            ],
            "differences": [
                "The new package loads one literal 159-byte LUT through 0x32 plus controller tail registers, while the current production path uses the recorded SSD1681 Mode-1 profile and does not contain this LUT.",
                "The package's ordinary partial function activates 0xFF; its LUT full update activates 0xC7. Neither is authorized as production behavior by this audit.",
                "The package declares 200x200 geometry but does not declare GDEY0154D67-T03 panel/FPC identity or a temperature-banded CWF1 table.",
            ],
            "match_conclusion": "NO_GO_PANEL_IDENTITY_UNPROVEN; retain as read-only, production-off candidate only.",
        },
        "command_evidence": {
            "full_update_control": "0xF7",
            "lut_fast_update_control": "0xC7",
            "master_activation": "0x20",
            "full_plane_command": "0x24",
            "full_plane_bytes": 5000,
            "busy_polarity": "high_active_low_ready",
            "production_lut_reference_absent": driver_checks["target_vendor_lut_is_not_present_in_production"],
        },
        "production_off_diagnostic": {
            "allowed": False,
            "reason": "Panel/FPC/controller identity and temperature coverage are not proven by the supplied package.",
            "non_goals": [
                "No production LUT import.",
                "No CWF1 or temperature-band claim.",
                "No expression, Rig, CRIG, browser-preview, dynamic-binding or animation change.",
            ],
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor-root", type=pathlib.Path, default=VENDOR_ROOT)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    vendor_root = args.vendor_root.resolve()
    output = args.out if args.out.is_absolute() else ROOT / args.out
    report = {
        "schema_id": SCHEMA_ID,
        "claim_scope": "read_only_supplier_source_audit_and_production_off_gate_only",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "supplier_input_is_read_only": True,
        **evaluate(vendor_root),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"{report['machine_status']}: vendor one-second source audit -> {rel(output)}; "
        f"promotion={report['promotion_status']}"
    )
    return 0 if report["machine_status"] == "PASS_AUDIT_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
