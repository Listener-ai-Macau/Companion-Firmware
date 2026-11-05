#!/usr/bin/env python3
"""R2 static/build/negative closure for COMP-REQ-316 prompt supervision."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_log.py"
MONITOR = ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r9_continuous.ps1"
SUPERVISOR = ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1"
PROMPT_R2 = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_prompt_supervisor_r2.py"
RUNNER = ROOT / "tools/run_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1"
HISTORICAL_RUNNER = ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation"
HEX = BUILD / "Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.hex"
ELF = HEX.with_suffix(".elf")
HISTORICAL_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-observation-static-20260721.json"

LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
HEX_SHA = "3B416BFF08B630D23BDB6107B2C17DFE9FBBFAAA7D5CFBCA5063AE68E62B79C5"
ELF_SHA = "B9808E72F8490B015A9B09B6B8B896390566D06FB8ABC98C5060CEF489BE8047"
HISTORICAL_HEX_SHA = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF"
HISTORICAL_RUNNER_SHA = "0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B"
HISTORICAL_FUNCTION_SHA = "AD0A67A9B5305D2CA17BB108213691E869F6DB5022588CF8316AC1F2CBAF6B40"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def body(source: str, name: str) -> str:
    match = re.search(rf"static void {name}\(void\)\n\{{.*?\n\}}", source, re.DOTALL)
    return match.group(0) if match else ""


def run(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8")
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def main() -> int:
    paths = (DRIVER, MAKEFILE, BUILDER, PARSER, MONITOR, SUPERVISOR, PROMPT_R2, RUNNER, REGISTRY, HEX, ELF, HISTORICAL_HEX)
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.is_file()]
    if missing:
        result = {"schema_id": "companion.wb55.r9_continuous_static.v1", "status": "NO_GO", "missing": missing}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    monitor = MONITOR.read_text(encoding="utf-8")
    supervisor = SUPERVISOR.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    historical = body(driver, "ssd1681_phase_parallel_r9_diagnostic")
    continuous = body(driver, "ssd1681_phase_parallel_r9_continuous_observation_diagnostic")
    lut_match = re.search(r"static const uint8_t ssd1681_phase_parallel_r9_lut\[159\]\s*=\s*\{(.*?)\};", driver, re.DOTALL)
    lut = bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})u?", lut_match.group(1))) if lut_match else b""

    checks: dict[str, bool] = {
        "continuous_macro_default_off": "#define COMPANION_EPAPER_SSD1681_PHASE_PARALLEL_R9_CONTINUOUS_OBSERVATION_DIAGNOSTIC 0" in driver,
        "continuous_macro_mutually_excludes_historical_r9": "COMPANION_EPAPER_SSD1681_PHASE_PARALLEL_R9_DIAGNOSTIC ||" in continuous or "continuous observation excludes every waveform/read diagnostic" in driver,
        "historical_r9_function_unchanged": hashlib.sha256(historical.encode()).hexdigest().upper() == HISTORICAL_FUNCTION_SHA,
        "historical_runner_unchanged": sha(HISTORICAL_RUNNER) == HISTORICAL_RUNNER_SHA,
        "historical_hex_unchanged": sha(HISTORICAL_HEX) == HISTORICAL_HEX_SHA,
        "same_admitted_lut_exact": len(lut) == 159 and hashlib.sha256(lut).hexdigest().upper() == LUT_SHA,
        "initial_patterns_match_16_step_r9": continuous.count("0u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u") == 1 and continuous.count("1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 0u") == 1,
        "initial_gate_exactly_16": "step < SSD1681_PHASE_PARALLEL_R9_ACTIVATIONS" in continuous and "activations_completed != SSD1681_PHASE_PARALLEL_R9_ACTIVATIONS" in continuous,
        "loop_has_no_preset_limit": "for (;;)" in continuous and "loop_limit=none" in continuous,
        "one_fixed_bank_activation_per_iteration": continuous.count("ssd1681_custom_mode2_write_plane(&window, 0x26u, previous)") == 2 and continuous.count("ssd1681_command_data(0x22u, mode2_display, sizeof(mode2_display))") == 2 and continuous.count("ssd1681_command(0x20u)") >= 2,
        "busy_limit_600_in_qualification_and_loop": continuous.count("ssd1681_wait_refresh_complete(0u, 600u)") == 2,
        "post_sync_24_in_qualification_and_loop": continuous.count("ssd1681_custom_mode2_write_plane(&window, 0x24u, current)") == 4,
        "fault_restores_bus": "loop_fault" in continuous and "ssd1681_read_only_restore_bus();" in continuous,
        "forbidden_counts_declared_zero": all(token in continuous for token in ("full_frame_writes=0", "controls_ff=0", "controls_f7=0", "controls_c7=0", "retries=0", "motion_120_frame=0")),
        "production_disabled_in_telemetry": "production_enabled=0" in continuous,
        "makefile_isolated_define": "EPAPER_SSD1681_PHASE_PARALLEL_R9_CONTINUOUS_OBSERVATION_DIAGNOSTIC" in makefile,
        "builder_isolated_switch": "EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic" in builder and "build_ssd1681_phase_parallel_r9_continuous_observation" in builder,
        "hex_identity": sha(HEX) == HEX_SHA,
        "elf_identity": sha(ELF) == ELF_SHA,
        "monitor_ring_default_65536": "[int]$RingBytes = 65536" in monitor and "Substring($script:ring.Length - $RingBytes)" in monitor,
        "monitor_checks_memory_and_disk_bound": "UTF-8 telemetry ring exceeded" in monitor and "Telemetry ring file exceeded" in monitor,
        "monitor_fail_closed_boundaries": all(token in monitor for token in ("NO_GO_CONTROLLER_DISCONNECT", "NO_GO_EMERGENCY_STOP", "NO_GO_LOOP_HEARTBEAT_TIMEOUT", "NO_GO_STORAGE_FAULT", "busy_over_600_ms")),
        "monitor_creates_no_popup": "popup_count = 0" in monitor,
        "prompt_is_canonical_two_option_only": '"operator-prompt"' in supervisor and '"通过,失败"' in supervisor and '"重新观察"' not in supervisor.split("if ($SelfTest)", 1)[1].split("if ($CheckOnly)", 1)[1],
        "prompt_requires_qualification_and_live_monitor": "acceptance prompt is forbidden" in supervisor and "The continuous monitor is not alive" in supervisor,
        "prompt_has_single_invocation_guard": "acceptance-prompt-invoked.json" in supervisor and "a second popup is forbidden" in supervisor,
        "prompt_guard_test_paths_separately_parenthesized": "if ((Test-Path -LiteralPath $guardPath -PathType Leaf) -or\n    (Test-Path -LiteralPath $reviewPath -PathType Leaf))" in supervisor,
        "simulation_injection_forbidden_in_execute": "$Execute -and -not [string]::IsNullOrWhiteSpace($SimulationPromptScript)" in supervisor and "Simulation prompt injection is forbidden in Execute mode." in supervisor,
        "simulation_records_one_process_zero_popup": "prompt_process_start_count = $promptProcessStartCount" in supervisor and "actual_popup_count = 0" in supervisor and supervisor.count("[System.Diagnostics.Process]::Start($startInfo)") == 1,
        "prompt_fault_kills_tree_and_emergency": "Stop-ProcessTree" in supervisor and "prompt_process_abnormal_exit" in supervisor,
        "operator_selection_is_only_normal_stop": 'reason = "operator_selection"' in supervisor and "Write-JsonAtomic -Path $StopSignalPath" in supervisor,
        "runner_uses_original_cleanup_restore_lifecycle": all(token in runner for token in ("postclean-white-write", "restore-write-verify-upload", "0x80000", "verify_wb55_raw_application_restore.py", "verify_wb55_normal_resume_after_ur_backup_log.py")),
        "runner_requires_later_execute_authorization": "AUTHORIZED_R9_CONTINUOUS_OBSERVATION_ONCE" in runner and "Continuous R9 Execute requires a later root-issued authorization artifact" in runner,
        "runner_starts_prompt_after_qualification": runner.index("PASS_INITIAL_16_READY_FOR_CONCURRENT_ACCEPTANCE") < runner.index("$continuousPromptProcess = Start-Process"),
        "runner_fail_closed_stops_process_trees": "runner_fail_closed_cleanup" in runner and "Stop-ProcessTree $continuousPromptProcess" in runner,
        "registry_313_present": "| COMP-REQ-313 |" in registry and "你现在就是需要无限自动刷屏。" in registry and "MACHINE_READY only" in registry,
        "registry_315_incident_preserved": "| COMP-REQ-315 |" in registry and "acceptance popup actually opened zero times" in registry and "not authorization for retry" in registry,
        "registry_316_r2_present": "| COMP-REQ-316 |" in registry and "R9 continuous R2 is a prompt-supervision repair only" in registry and "real supervisor execution path" in registry,
    }

    selftests = {
        "parser": run([sys.executable, str(PARSER), "--self-test"]),
        "monitor": run(["pwsh", "-NoProfile", "-File", str(MONITOR), "-SelfTest", "-OutDir", str(ROOT / ".cache/validation/r9-continuous-static-monitor-selftest")]),
        "prompt_supervisor_smoke": run(["pwsh", "-NoProfile", "-File", str(SUPERVISOR), "-SelfTest", "-OutRoot", str(ROOT / ".cache/validation/r9-continuous-r2-static-prompt-selftest")]),
        "prompt_supervisor_real_path": run([sys.executable, str(PROMPT_R2)]),
    }
    checks.update({f"{name}_selftest_pass": item["exit_code"] == 0 for name, item in selftests.items()})
    errors = [name for name, passed in checks.items() if not passed]
    result = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous_r2_observation_static.v1",
        "status": "PASS_STATIC_R9_CONTINUOUS_R2_OBSERVATION" if not errors else "NO_GO_R9_CONTINUOUS_R2_OBSERVATION_STATIC",
        "requirement": "COMP-REQ-316",
        "hardware_contact": 0,
        "errors": errors,
        "checks": checks,
        "identities": {
            "candidate_hex_sha256": sha(HEX),
            "candidate_elf_sha256": sha(ELF),
            "lut_sha256": LUT_SHA,
            "historical_r9_hex_sha256": sha(HISTORICAL_HEX),
            "historical_runner_sha256": sha(HISTORICAL_RUNNER),
            "continuous_runner_sha256": sha(RUNNER),
            "monitor_sha256": sha(MONITOR),
            "prompt_supervisor_sha256": sha(SUPERVISOR),
            "prompt_supervisor_r2_verifier_sha256": sha(PROMPT_R2),
            "parser_sha256": sha(PARSER),
        },
        "selftests": selftests,
        "popup_policy": {"start": 0, "cleanup": 0, "recovery": 0, "fault": 0, "acceptance": 1},
        "authorization": "R2 implementation/build/CheckOnly/MACHINE_READY only; no Execute",
        "production_allowed": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
