#!/usr/bin/env python3
"""Targeted R4 corridor/source and generic-MR host checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
PARSER = ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py"
MONITOR = ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1"
SUPERVISOR = ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1"
LUT_SHA256 = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    driver = DRIVER.read_text(encoding="utf-8")
    parser = PARSER.read_text(encoding="utf-8")
    monitor = MONITOR.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    supervisor = SUPERVISOR.read_text(encoding="utf-8")
    frame_start = driver.index("static bool ssd1681_r10_execute_frame")
    frame_end = driver.index("static void ssd1681_r10_print_frame", frame_start)
    frame_source = driver[frame_start:frame_end]
    checks = {
        "fixed_corridor": all(token in driver for token in (
            "SSD1681_R10_CORRIDOR_X_START_BYTE 4u",
            "SSD1681_R10_CORRIDOR_X_END_BYTE 9u",
            "SSD1681_R10_CORRIDOR_Y_START 80u",
            "SSD1681_R10_CORRIDOR_Y_END 91u",
            "SSD1681_R10_CORRIDOR_BYTES 72u",
            "ssd1681_r10_corridor_from_difference",
            "ssd1681_window_byte_count(window) == SSD1681_R10_CORRIDOR_BYTES",
        )),
        "full_diff_then_corridor": "ssd1681_window_from_difference()" in driver and "ssd1681_r10_corridor_from_difference(&difference)" in driver,
        "classes": all(token in driver for token in ("record->ww != 464u", "record->wb != 112u", "record->ww != 376u", "record->bw != 88u", "record->bb != 24u")),
        "exact_transport": frame_source.count("ssd1681_write_plane_region(0x26u") == 1 and frame_source.count("ssd1681_write_plane_region(0x24u") == 2 and "ssd1681_command(0x20u)" in frame_source,
        "r3_hold_preserved": "HAL_Delay(SSD1681_R10_STABLE_HOLD_TARGET_MS)" in driver and "SSD1681_R10_STABLE_HOLD_MAX_MS 410u" in driver,
        "r9_waveform_preserved": "ssd1681_phase_parallel_r9_lut" in driver and "221741A83258" in driver,
        "r4_schema": ("phase_parallel_r10_ball schema=v3" in driver or "phase_parallel_r10_ball schema=v4" in driver or "phase_parallel_r10_ball schema=v5" in driver) and "corridor_window=x4-9,y80-91,bytes72" in driver and ("SSD1681_R10_R5_LUT_SHA256" in driver or "SSD1681_R10_R6_LUT_SHA256" in driver) and ("ssd1681_r10_r5_lut" in driver or "ssd1681_r10_r6_lut" in driver) and "candidate_sha256=%s" in driver,
        "r6_schema_and_lut_load": "phase_parallel_r10_ball schema=v5" in driver and "SSD1681_R10_R6_LUT_SHA256" in driver and all(token in driver for token in ("ssd1681_command_data(0x32u, ssd1681_r10_r6_lut, 153u)", "ssd1681_command_data(0x3Fu, &ssd1681_r10_r6_lut[153], 1u)", "ssd1681_command_data(0x03u, &ssd1681_r10_r6_lut[154], 1u)", "ssd1681_command_data(0x04u, &ssd1681_r10_r6_lut[155], 3u)", "ssd1681_command_data(0x2Cu, &ssd1681_r10_r6_lut[158], 1u)")),
        "parser_r4_and_preamble": all(token in parser for token in ("R4_PREFIX", "r4_transition", "validate_loop_preamble", "ignored_preamble_lines")),
        "ring_line_boundary": "Telemetry ring overflowed before a complete line boundary" in monitor,
        "generic_launcher_manifest": all(token in launcher for token in ("Validate-MachineManifest", "machine_ready_path", "docs\\validation")) and "r10-r3-execute-ready-machine-ready" not in launcher,
        "generic_runner_manifest": all(token in runner for token in ("Validate-MachineManifest", "machine_ready_path", "machine_ready_sha256")) and "r10-r3-execute-ready-machine-ready" not in runner,
        "popup_and_lifecycle_untouched": all(token in supervisor for token in ("通过", "失败", "StopSignalPath", "EmergencyStopPath", "-OutRoot")),
    }
    lut_source = driver.split("ssd1681_phase_parallel_r9_lut", 1)[-1]
    return_value = {"schema_id": "companion.wb55.ssd1681.r10_r4.corridor_static.v1", "status": "PASS_R10_R4_CORRIDOR_STATIC" if all(checks.values()) else "NO_GO_R10_R4_CORRIDOR_STATIC", "checks": checks, "lut_sha256": LUT_SHA256, "parser_sha256": sha(PARSER), "monitor_sha256": sha(MONITOR), "launcher_sha256": sha(LAUNCHER), "runner_sha256": sha(RUNNER), "supervisor_sha256": sha(SUPERVISOR), "driver_sha256": sha(DRIVER), "lut_source_present": bool(lut_source)}
    print(json.dumps(return_value, ensure_ascii=False, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
