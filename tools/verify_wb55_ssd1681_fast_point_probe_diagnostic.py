#!/usr/bin/env python3
"""Static/default-off/raw-restore gate for the fast SSD1681 point probe."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from verify_wb55_ur_application_backup import BackupError, validate_pair


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
PHASE_A = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json"
PHASE_B = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-point-probe-completion-audit-20260721.json"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
SUPPLIER = ROOT / ".cache/incoming/S-GDEY0154D67-FP-Touch-official-20260720/S-GDEY0154D67-FP-Touch20230303/HARDWARE/EPD/Display_EPD_W21.c"
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_fast_point_probe_log.py"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_fast_point_probe/Companion_Nucleo_WB55RG_Ssd1681FastPointProbe.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-ssd1681-fast-point-probe-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    PHASE_A: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    PHASE_B: "BE01F8D9AF6157A3A8524728245FFBAB3EC5F9A5CCB162125F7AEE7C796C97CC",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    SUPPLIER: "CD08AFD1D56E8F7E1D0AE5C935A4D060E65C658ABC30CE29ACF65166141ACEE2",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    DRIVER: "7632A6E45E16CEF0C4E8DECD5E1527E8C84FEAAA4E762E263A4ED615AF4FA136",
    MAKEFILE: "236D5C67FE3A24438AE834FA904ACDD5D4668D09B42BAB0AAAB595A9CB4B4226",
    BUILDER: "843FE7B9F6C7162ECA6EA50B8A5F6AC44F16CD86D3AB64E24C8BBDF671D0E873",
    PARSER: "14A88C3C2951A02C50743AE71A585612F43AEEEB06C70993D9A7F3B456ECE694",
    RUNNER: "170A57CF273DBFFDF2A5920E329A989230B4199412FC67AA06F6FDB2B03AD5CB",
    CANDIDATE: "210B9851889457F951E20FC96DC509CA4DCB8B779E40031F7DC47C136C4CB222",
    CANDIDATE_ELF: "38B1DC3942624F3DF5FF28CEB5A47E21F12584B6160A315B77F5EE88465E24B1",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    required = [REGISTRY, RESTORE, NORMAL, *EXPECTED.keys()]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"schema_id": "companion.wb55.ssd1681_fast_point_probe_static.v1", "status": "NO_GO_STATIC_FAST_POINT_PROBE", "checks": checks, "failures": failures}, indent=2) + "\n", encoding="utf-8")
        return 1

    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")
    registry = REGISTRY.read_text(encoding="utf-8")
    phase_a = json.loads(PHASE_A.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")

    require("registry_contract", "| COMP-REQ-273 |" in registry and all(token in registry for token in ("120", "475", "550", "p95", "8 px", "32 px")), "COMP-REQ-273 fast-motion contract is absent")
    require("unique_phase_a_admission", phase_a.get("status") == "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED" and phase_a.get("fingerprint", {}).get("unique_mapping") == "activation_swapped_banks_selector0_base_selector1_current", "Phase A mapping is not uniquely proved")
    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["length_bytes"] == 524288 and baseline["shared_sha256"] == EXPECTED[BASELINE_A]
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("raw_restore_baseline", baseline_ok, "captured raw restore baseline is invalid")

    macro = "COMPANION_EPAPER_SSD1681_FAST_POINT_PROBE_DIAGNOSTIC"
    require("default_off", f"#define {macro} 0" in driver and f"-D{macro}=1" in makefile, "fast point probe is not default-off")
    start = driver.find("static void ssd1681_fast_point_probe_diagnostic")
    end = driver.find("\n#endif", start)
    diagnostic = driver[start:end]
    loop_start = diagnostic.find("for (uint16_t frame = 0u")
    loop = diagnostic[loop_start:]
    require("function_and_120_frames", start >= 0 and "SSD1681_FAST_POINT_PROBE_FRAMES 120u" in driver and "frame < SSD1681_FAST_POINT_PROBE_FRAMES" in diagnostic, "120-frame diagnostic is absent")
    require("non_screen_countdown", "countdown = 3u" in diagnostic and "screen_commands=0 screen_refreshes=0" in diagnostic and "start_signal=1" in diagnostic, "three-second non-screen countdown/start marker differs")
    require("fast_trajectory", "52u, 60u, 68u, 76u, 84u, 76u, 68u, 60u" in diagnostic and "step_px=8 excursion_px=32" in diagnostic, "8 px/32 px trajectory differs")
    require("generic_diff", "ssd1681_point_probe_diff_window(s_previous_frame, s_frame)" in diagnostic and "geometry_role=diagnostic_only" in diagnostic, "generic previous/current framebuffer diff is absent")
    require("one_ff_20_busy_per_frame", loop.count("ssd1681_command_data(0x22u") == 1 and loop.count("ssd1681_command(0x20u)") == 1 and loop.count("ssd1681_wait_refresh_complete(0u, 1000u)") == 1 and "controls_ff=120 refresh_20=120 busy_completions=120" in diagnostic, "per-frame FF/20/BUSY sequence differs")
    require("post_activation_0x24_sync", loop.count("ssd1681_point_probe_write_current(&window") == 2 and "post_sync_24=120 post_sync_refresh=0" in diagnostic, "post-activation 0x24 no-refresh sync differs")
    require("zero_motion_0x26", "ssd1681_command(0x26u)" not in loop and "motion_0x26_writes=0" in diagnostic, "motion loop writes 0x26")
    require("seed_not_activated", diagnostic.count("ssd1681_command(0x26u)") == 1 and "seed banks=0x24,0x26 bytes_each=5000 activation=0" in diagnostic, "initial equal-bank seed differs")
    require("timing_contract", "SSD1681_FAST_POINT_PROBE_FRAME_SPACING_MS 500u" in driver and "motion_elapsed_ms" in diagnostic, "500 ms pacing/elapsed marker absent")
    require("transfer_oracle", all(token in diagnostic for token in ("changed_bytes", "oracle_bytes", "stage_bytes == oracle_bytes", "sync_bytes == oracle_bytes")), "transfer oracle is incomplete")
    require("zero_forbidden", all(token in diagnostic for token in ("full_refreshes=0", "controls_f7=0", "controls_c7=0", "lut_writes=0", "retries=0")) and "0x32u" not in diagnostic and "0x37u" not in diagnostic, "forbidden full/LUT path is present")
    require("isolated_builder", "[switch]$EpaperSsd1681FastPointProbeDiagnostic" in builder and "build_ssd1681_fast_point_probe" in builder, "builder lacks isolated fast point probe")
    require("candidate_marker", "[epaper] fast_probe start" in CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore"), "candidate ELF marker is absent")
    require("runner_binding", all(token in runner for token in ("[switch]$FastPointProbe", EXPECTED[CANDIDATE], "verify_wb55_ssd1681_fast_point_probe_log.py", "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_RESTORED", "NO_GO_SSD1681_FAST_POINT_PROBE_RESTORED", "panel_hard_resets = 121", "panel_writes = 242")), "runner lacks exact fast point binding")
    require("runner_zero_retry", "automatic_retries = 0" in runner and runner.count('Operation "candidate-write"') == 1, "runner attempt boundary differs")
    finally_text = runner[runner.index("} finally {"):]
    require("one_finally_restore", finally_text.count('Operation "restore-write-verify-upload"') == 1 and all(token in finally_text for token in ('"-w", $backupA, "0x08000000"', '"-v", $backupA, "0x08000000"', '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"')), "finally raw restore differs")

    tests = {}
    for name, command in {
        "parser": [sys.executable, str(PARSER), "--self-test"],
        "restore": [sys.executable, str(RESTORE), "--self-test"],
        "normal": [sys.executable, str(NORMAL), "--self-test"],
    }.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        tests[name] = proc.stdout.strip()
        require(f"{name}_negative_matrix", proc.returncode == 0, f"{name} self-test failed: {proc.stderr.strip()}")
    ps_parse = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"], cwd=ROOT, capture_output=True, text=True)
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout, f"runner parse failed: {ps_parse.stderr.strip()}")
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout, "programmer is not v2.22.0")

    result = {
        "schema_id": "companion.wb55.ssd1681_fast_point_probe_static.v1",
        "status": "PASS_STATIC_SSD1681_FAST_POINT_PROBE_RAW_RESTORE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_FAST_POINT_PROBE",
        "claim_scope": "Static/build/host proof only; hardware_contact=0 and no visual result.",
        "checks": checks,
        "failures": failures,
        "candidate": {"hex_sha256": sha(CANDIDATE), "elf_sha256": sha(CANDIDATE_ELF)},
        "phase_a_mapping": phase_a["fingerprint"]["unique_mapping"],
        "baseline": {"bytes": 524288, "sha256": EXPECTED[BASELINE_A]},
        "host_tests": tests,
        "forbidden_claims": ["no hardware/visual/production result", "no custom LUT/waveform/temperature/voltage/Rig/CRIG/touch/BLE change"],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
