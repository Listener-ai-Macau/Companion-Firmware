#!/usr/bin/env python3
"""Prove the default-off R10 direct-driver source contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import verify_wb55_ssd1681_r10_ball_pixel_oracle as oracle


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r10_ball_diagnostic.h"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-static-20260722.json"
LUT_SHA256 = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
TAIL = bytes.fromhex("221741A83258")
R10_MACRO = "COMPANION_EPAPER_SSD1681_R10_BALL_DIAGNOSTIC"


class StaticFailure(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StaticFailure(message)


def extract_function(source: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", source, re.DOTALL)
    if match is None:
        raise StaticFailure(f"missing function {name}")
    start = match.start()
    brace = source.find("{", match.start())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise StaticFailure(f"unterminated function {name}")


def command_values(source: str) -> list[int]:
    return [
        int(token, 16)
        for token in re.findall(
            r"ssd1681_command(?:_data)?\(\s*0x([0-9A-Fa-f]{2})u", source
        )
    ]


def assert_in_order(source: str, snippets: list[str]) -> None:
    cursor = 0
    for snippet in snippets:
        index = source.find(snippet, cursor)
        if index < 0:
            raise StaticFailure(f"missing or out-of-order R10 operation: {snippet}")
        cursor = index + len(snippet)


def build_report() -> dict[str, object]:
    driver_bytes = DRIVER.read_bytes()
    driver = driver_bytes.decode("utf-8")
    header_bytes = HEADER.read_bytes()
    makefile_bytes = MAKEFILE.read_bytes()
    build_bytes = BUILD.read_bytes()
    makefile = makefile_bytes.decode("utf-8")
    build = build_bytes.decode("utf-8")

    default_match = re.search(
        rf"#ifndef\s+{R10_MACRO}\s+#define\s+{R10_MACRO}\s+(\d+)",
        driver,
    )
    require(default_match is not None and default_match.group(1) == "0", "R10 macro is not default-off")

    exclusion = re.search(
        rf"#if\s+{R10_MACRO}\s+&&\s+\\(?P<body>.*?)#error \"SSD1681 R10 ball diagnostic excludes every other diagnostic\"",
        driver,
        re.DOTALL,
    )
    require(exclusion is not None, "missing R10 mutual-exclusion guard")
    for name in (
        "PHASE_PARALLEL_R9_DIAGNOSTIC",
        "PHASE_PARALLEL_R9_CONTINUOUS_OBSERVATION_DIAGNOSTIC",
        "CUSTOM_MODE2_TRANSITION_SAFETY_DIAGNOSTIC",
        "CUSTOM_MODE2_OBSERVABLE_R6_DIAGNOSTIC",
        "RAM_COMMAND_TARGET_R8_DIAGNOSTIC",
        "DUAL_PLANE_WHITE_CLEAN_DIAGNOSTIC",
        "VENDOR_1S_LUT_DIAGNOSTIC",
        "VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC",
    ):
        require(f"COMPANION_EPAPER_SSD1681_{name}" in exclusion.group("body"), f"R10 does not exclude {name}")

    header_report = oracle.parse_and_assert_header()
    lut = bytes(oracle.parse_c_array(driver, "ssd1681_phase_parallel_r9_lut"))
    require(len(lut) == 159, f"R9 LUT length is {len(lut)}, expected 159")
    require(sha256(lut) == LUT_SHA256, "R9 LUT SHA-256 changed")
    require(lut[153:] == TAIL, "R9 LUT tail changed")

    execute = extract_function(driver, "ssd1681_r10_execute_frame")
    diagnostic = extract_function(driver, "ssd1681_phase_parallel_r10_ball_diagnostic")
    render = extract_function(driver, "ssd1681_r10_render_frame")
    window = extract_function(driver, "ssd1681_window_from_difference")
    init = extract_function(driver, "companion_epaper_panel_stm32wb_ssd1681_init")

    require("SSD1681_FRAME_BYTES" in render and "memset(frame, 0xFF" in render, "R10 renderer does not clear a full frame")
    require("comp_r10_ball_diagnostic_row_masks" in render, "R10 renderer does not use the proved C row masks")
    require("ssd1681_r10_render_frame(s_previous_frame, previous_x)" in execute, "R10 does not render the complete previous framebuffer")
    require("ssd1681_r10_render_frame(s_frame, current_x)" in execute, "R10 does not render the complete current framebuffer")
    require("s_previous_frame_valid = true" in execute, "R10 does not admit the complete previous frame")
    require("ssd1681_window_from_difference()" in execute, "R10 does not use the full-frame diff helper")
    require("for (uint16_t y = 0u; y < SSD1681_HEIGHT" in window, "diff helper does not scan all rows")
    require("for (uint8_t x = 0u; x < SSD1681_BYTES_PER_ROW" in window, "diff helper does not scan all bytes")
    require("expected_bytes = previous_x == SSD1681_R10_WHITE_POSITION ? 24u : 36u" in driver, "R10 dynamic window sizes changed")
    require("SSD1681_PHASE_PARALLEL_R9_WINDOW_BYTES" not in execute, "R10 execute path uses the fixed R9 payload size")
    require("ssd1681_custom_mode2_fill_pattern" not in execute, "R10 execute path uses the R9 pattern payload helper")

    assert_in_order(
        execute,
        [
            "ssd1681_point_probe_set_window(&record->window, 0x80u)",
            "ssd1681_write_plane_region(0x26u, s_previous_frame, &record->window)",
            "ssd1681_point_probe_set_window(&record->window, 0x80u)",
            "ssd1681_write_plane_region(0x24u, s_frame, &record->window)",
            "ssd1681_command_data(0x22u, mode2_display, sizeof(mode2_display))",
            "ssd1681_command(0x20u)",
            "ssd1681_wait_refresh_complete(0u, SSD1681_R10_BUSY_LIMIT_MS)",
            "ssd1681_point_probe_set_window(&record->window, 0x80u)",
            "ssd1681_write_plane_region(0x24u, s_frame, &record->window)",
            "HAL_Delay(SSD1681_R10_STABLE_HOLD_TARGET_MS)",
        ],
    )
    require(execute.count("ssd1681_write_plane_region(0x26u") == 1, "R10 frame does not have exactly one 0x26 write")
    require(execute.count("ssd1681_write_plane_region(0x24u") == 2, "R10 frame does not have staged and post-sync 0x24 writes")
    require(execute.count("ssd1681_command_data(0x22u") == 1, "R10 frame does not have exactly one control write")
    require(execute.count("ssd1681_command(0x20u)") == 1, "R10 frame does not have exactly one activation")
    require(execute.count("ssd1681_wait_refresh_complete") == 1, "R10 frame does not have exactly one BUSY completion")
    require("record->busy_elapsed_ms <= SSD1681_R10_BUSY_LIMIT_MS" in execute, "R10 lacks the hard BUSY limit")
    require("#define SSD1681_R10_BUSY_LIMIT_MS 600u" in driver, "R10 BUSY limit is not 600 ms")
    require("#define SSD1681_R10_STABLE_HOLD_TARGET_MS 400u" in driver and "#define SSD1681_R10_STABLE_HOLD_MAX_MS 410u" in driver, "R3 stable-hold bounds are missing")
    require("HAL_Delay(SSD1681_R10_STABLE_HOLD_TARGET_MS)" in execute and execute.count("HAL_Delay(") == 1, "R3 must have exactly one stable hold delay")
    require("record->hold_count = 1u" in execute and "record->hold_elapsed_ms >= SSD1681_R10_STABLE_HOLD_TARGET_MS" in execute and "record->hold_elapsed_ms <= SSD1681_R10_STABLE_HOLD_MAX_MS" in execute, "R3 hold measurement is not bounded")

    forbidden = {0xF7, 0xC7, 0xFF, 0x37}
    used_commands = set(command_values(execute)) | set(command_values(diagnostic))
    require(not forbidden.intersection(used_commands), f"R10 path contains forbidden commands {sorted(forbidden.intersection(used_commands))}")
    require("maintenance" not in execute.lower(), "R10 execute path contains maintenance behavior")
    require("retry" not in execute.lower(), "R10 execute path contains retry behavior")

    assert_in_order(
        diagnostic,
        [
            "ssd1681_command_data(0x32u, ssd1681_phase_parallel_r9_lut, 153u)",
            "ssd1681_command_data(0x3Fu, &ssd1681_phase_parallel_r9_lut[153], 1u)",
            "ssd1681_command_data(0x03u, &ssd1681_phase_parallel_r9_lut[154], 1u)",
            "ssd1681_command_data(0x04u, &ssd1681_phase_parallel_r9_lut[155], 3u)",
            "ssd1681_command_data(0x2Cu, &ssd1681_phase_parallel_r9_lut[158], 1u)",
        ],
    )
    require(diagnostic.count("ssd1681_command_data(0x32u") == 1, "R10 LUT is not loaded exactly once")
    require("step < COMP_R10_BALL_DIAGNOSTIC_ACTIVATIONS" in diagnostic, "R10 qualification is not exactly header-bound")
    require("for (;;)" in diagnostic, "R10 observation loop has a preset bound")
    require("uint8_t previous_x = 40u" in diagnostic and "uint8_t loop_index = 0u" in diagnostic, "R10 loop does not continue 40->32")
    require("COMP_R10_BALL_DIAGNOSTIC_LOOP_POSITIONS" in diagnostic, "R10 loop length is not header-bound")
    require("telemetry_storage=host_ring_65536" in diagnostic, "R10 does not declare bounded host telemetry")

    dispatch = re.search(
        rf"#if\s+{R10_MACRO}(?P<body>.*?)#endif",
        init,
        re.DOTALL,
    )
    require(dispatch is not None, "R10 init dispatch is not guarded by the R10 macro")
    require("ssd1681_phase_parallel_r10_ball_diagnostic();" in dispatch.group("body"), "R10 init dispatch is missing")
    require(init.count("ssd1681_phase_parallel_r10_ball_diagnostic();") == 1, "R10 init dispatch is duplicated")

    require("[switch]$EpaperSsd1681R10BallDiagnostic" in build, "R10 build switch is missing")
    require("EPAPER_SSD1681_R10_BALL_DIAGNOSTIC=1" in build, "R10 build macro mapping is missing")
    require("BUILD_DIR=build_ssd1681_r10_ball" in build, "R10 build output is not isolated")
    require("TARGET=Companion_Nucleo_WB55RG_Ssd1681R10Ball" in build, "R10 target name is not distinct")
    require("ifeq ($(EPAPER_SSD1681_R10_BALL_DIAGNOSTIC),1)" in makefile, "R10 Makefile selector is missing")

    oracle_artifact = oracle.build_artifact()
    expected_hashes = {
        transition["previous_frame_sha256"]
        for transition in oracle_artifact["qualification"]["transitions"]
    } | {
        transition["current_frame_sha256"]
        for transition in oracle_artifact["qualification"]["transitions"]
    }
    expected_payload_hashes = {
        transition[key]
        for transition in oracle_artifact["qualification"]["transitions"]
        for key in ("previous_payload_sha256", "current_payload_sha256")
    }
    for expected in expected_hashes | expected_payload_hashes:
        require(expected in driver, f"R10 source is missing oracle hash {expected}")

    return {
        "schema_id": "companion.wb55.ssd1681.r10_r3_ball_static.v2",
        "status": "PASS_R10_BALL_STATIC",
        "authority": "COMP-REQ-332",
        "source": {
            "driver": DRIVER.relative_to(ROOT).as_posix(),
            "driver_sha256": sha256(driver_bytes),
            "header": HEADER.relative_to(ROOT).as_posix(),
            "header_sha256": sha256(header_bytes),
            "makefile_sha256": sha256(makefile_bytes),
            "build_script_sha256": sha256(build_bytes),
        },
        "geometry": header_report,
        "protected_lut": {"bytes": len(lut), "sha256": sha256(lut), "tail_hex": lut[153:].hex().upper()},
        "proved": [
            "default_off_and_mutually_exclusive",
            "independent_disk_masks_and_path",
            "r9_lut_and_tail_byte_identical",
            "complete_previous_current_framebuffers_and_full_diff",
            "dynamic_24_36_byte_union_windows",
            "one_0x26_one_staged_0x24_one_activation_one_post_sync_0x24",
            "one_400_to_410ms_post_sync_stable_hold_in_qualification_and_loop",
            "busy_hard_limit_600_ms",
            "forbidden_commands_and_paths_absent",
            "exact_16_frame_qualification_and_40_to_32_loop_continuation",
            "r10_only_init_dispatch_and_isolated_build",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report()
    except (OSError, UnicodeError, oracle.OracleFailure, StaticFailure) as error:
        print(f"FAIL: R10 ball static verifier: {error}")
        return 1
    rendered = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.write:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_bytes(rendered)
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered:
        print(f"FAIL: stale R10 ball static artifact: {args.artifact.relative_to(ROOT).as_posix()}")
        return 1
    print(f"PASS: R10 ball static verifier checks={len(report['proved'])}")
    print(f"artifact={args.artifact.relative_to(ROOT).as_posix()} sha256={sha256(args.artifact.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
