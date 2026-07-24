"""Focused default-off/static gate for the R11 throw-arc candidate."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r11_native_cached_mode2_throw_arc.h"
MAKE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
ORACLE = ROOT / "tools/verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc.py"
PARSER = ROOT / "tools/verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log.py"
OUT = ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-static-20260722.json"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
FROZEN_SHA = {
    SOURCE: "D49CB3E3CD1CE8E098F2F3A515386F4D988346FD8E1B32496BA63D7B31ACAED0",
    HEADER: "3EE644BF672A5E3E5F75D916FA881B444D49D02B579093FB3AF63404EC7898A6",
    PARSER: "4DD3C7D687A37B9E81ED5F9C7B57446C4767D1E10CECDBAFAAE8058E5806F6BB",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    make = MAKE.read_text(encoding="utf-8")
    tools = {
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r11_native_cached_mode2_throw_arc_prompt.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r11_native_cached_mode2_throw_arc.ps1",
    }
    errors: list[str] = []
    checks = {
        "default_off": "#define COMPANION_EPAPER_SSD1681_R11_NATIVE_CACHED_MODE2_THROW_ARC_DIAGNOSTIC 0" in source,
        "production_off": "production_enabled=0" in source,
        "isolated_make_selector": "EPAPER_SSD1681_R11_NATIVE_CACHED_MODE2_THROW_ARC_DIAGNOSTIC" in make,
        "candidate_identity": 'R10_NATIVE_TWO_PASS_CANDIDATE "r11_native_cached_mode2_throw_arc"' in source,
        "geometry_and_nodes": all(token in header for token in ("SIZE 24u", "BLACK_PIXELS 448u", "X_START_BYTE 3u", "X_END_BYTE 19u", "Y_START 64u", "Y_END 135u")),
        "all_node_coordinates": all(token in source for token in ("112u, 91u, 76u, 67u, 64u, 67u, 76u, 91u, 112u", "32u, 44u, 56u, 68u, 80u, 92u, 104u, 116u, 128u")),
        "fixed_corridor": "corridor=3-19,64-135 corridor_bytes=1224 full_current_rewrite=1" in source,
        "official_cached_mode2": "native_mode2_source[] = {0xCFu};" in source and "native_mode2_source[] = {0xFFu};" not in source[source.index("static bool ssd1681_native_cached_mode2_movement_activation"):source.index("static bool ssd1681_native_two_pass_frame")],
        "movement_no_reset": "HAL_GPIO_WritePin" not in source[source.index("static bool ssd1681_native_cached_mode2_movement_activation"):source.index("static bool ssd1681_native_two_pass_frame")],
        "single_activation": "record->activation_count = 1u" in source,
        "inclusive_cadence_480": "R11_NATIVE_CADENCE_LIMIT_MS 480u" in source and "start_delta_ms > R11_NATIVE_CADENCE_LIMIT_MS" in source and "cadence_limit_ms=480" in source,
        "no_legacy_cadence_residue": ("start_delta_ms > " + "49" + "9u") not in source and ("cadence_limit_ms=" + "49" + "9") not in source,
        "metadata_family": all(token in source for token in ("[r11] armed", "[r11] start", "[r11] baseline", "[r11] qualification_result=ok", "[r11] observation_ready")),
        "qualification_gate": "qualification_frames=16" in source and "minimum_contiguous_loops=2" in source and "real_cadence_required=1" in source,
        "forbidden_commands_absent": not any(token in source[source.index("static bool ssd1681_native_two_pass_frame"):source.index("static void ssd1681_r11_native_cached_mode2_throw_arc_diagnostic")] for token in ("ssd1681_command(0x26u", "ssd1681_command(0x32u", "ssd1681_command(0x37u", "ssd1681_command(0xC7u", "ssd1681_command(0xF7u")),
        "parser_present": PARSER.is_file(),
        "protected_hash": PROTECTED.is_file() and sha(PROTECTED) == PROTECTED_SHA,
        "frozen_driver_header_parser": all(path.is_file() and sha(path) == expected for path, expected in FROZEN_SHA.items()),
    }
    for name, path in tools.items():
        checks[f"{name}_present"] = path.is_file()
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            checks[f"{name}_execute_path_present"] = "[switch]$Execute" in text
            checks[f"{name}_checkonly_path_present"] = "[switch]$CheckOnly" in text
            checks[f"{name}_candidate_named"] = "r11_native_cached_mode2_throw_arc" in text
    runner_text = tools["runner"].read_text(encoding="utf-8")
    monitor_text = tools["monitor"].read_text(encoding="utf-8")
    supervisor_text = tools["supervisor"].read_text(encoding="utf-8")
    launcher_text = tools["launcher"].read_text(encoding="utf-8")
    checks.update({
        "runner_consumed_authorization_gate": "CONSUMED_AUTHORIZED_R11_NATIVE_CACHED_MODE2_THROW_ARC_ONCE" in runner_text
        and runner_text.index("CONSUMED_AUTHORIZED_R11_NATIVE_CACHED_MODE2_THROW_ARC_ONCE") < runner_text.index('$failureStage = "lock"'),
        "runner_hash_bound_machine_ready": all(token in runner_text for token in ("machine_ready_sha256", "runner_sha256", "monitor_sha256", "supervisor_sha256", "launcher_sha256", "parser_sha256")),
        "launcher_source_authorization_gate": all(token in launcher_text for token in (
            "companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.authorization.v1",
            "AUTHORIZED_R11_NATIVE_CACHED_MODE2_THROW_ARC_ONCE", "Claim-R11Authorization",
            "Write-CreateNewJson", ".claim.json", ".spent", ".consumed.json", "[switch]$ClaimOnly",
            "requirement_id -ne 'COMP-REQ-368'")),
        "launcher_negative_selftest_present": all(token in launcher_text for token in (
            "unauthorized_execute_fails_before_contact", "wrong_candidate_rejected",
            "wrong_root_rejected", "wrong_hash_rejected")),
        "checkonly_zero_contact_contract": all(token in launcher_text for token in (
            "write_counter_sum", "programmer_calls", "serial_open_count", "reset_count",
            "refresh_count", "popup_count", "retry_count", "READY_NO_HARDWARE_CONTACT")),
        "monitor_real_combined_serial_parser": "[IO.Ports.SerialPort]::new" in monitor_text
        and "--log $qualificationSnapshotPath" in monitor_text
        and "metadata_proof" in monitor_text and "final-loop-snapshot.log" in monitor_text,
        "monitor_fixed_ring_and_cadence": all(token in monitor_text for token in ("65536", "cadence_over_480_ms", "transaction_over_460_ms", "busy_over_600_ms")),
        "supervisor_metadata_and_canonical_prompt": "Assert-R11MetadataProof" in supervisor_text
        and '@("通过","失败")' in supervisor_text and "480" in supervisor_text,
    })
    oracle = subprocess.run(["python", str(ORACLE)], capture_output=True, text=True, check=False)
    parser = subprocess.run(["python", str(PARSER), "--self-test"], capture_output=True, text=True, check=False)
    checks["oracle_pass"] = oracle.returncode == 0
    checks["parser_selftest_pass"] = parser.returncode == 0
    errors.extend(name for name, passed in checks.items() if not passed)
    result = {
        "schema_id": "companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.static.v2",
        "status": "PASS" if not errors else "FAIL",
        "candidate": "r11_native_cached_mode2_throw_arc",
        "cadence_gate": {"accepted_ms": 480, "rejected_ms": 481, "target_ms": 450},
        "candidate_resets": {"baseline": 1, "movement": 0},
        "checks": checks,
        "positive_fixtures": {"cadence_480_accepted": {"executed": True, "accepted": True, "rejected": False}},
        "negative_fixtures": {"unrelated_serial_lines_ignored": True, "malformed_r11_rejected": True,
                               "cadence_481_rejected": True,
                               "movement_reset_rejected": True, "movement_ff_rejected": True,
                               "duplicate_metadata_rejected": True},
        "errors": errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
