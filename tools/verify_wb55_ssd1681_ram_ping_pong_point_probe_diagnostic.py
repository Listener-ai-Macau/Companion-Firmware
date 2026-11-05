#!/usr/bin/env python3
"""Static gate for the Phase B SSD1681 ping-pong point probe."""

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
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
SUPPLIER = ROOT / ".cache/incoming/S-GDEY0154D67-FP-Touch-official-20260720/S-GDEY0154D67-FP-Touch20230303/HARDWARE/EPD/Display_EPD_W21.c"
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_ram_ping_pong_point_probe_log.py"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_ram_ping_pong_point_probe/Companion_Nucleo_WB55RG_Ssd1681RamPingPongPointProbe.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-point-probe-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    PHASE_A: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    SUPPLIER: "CD08AFD1D56E8F7E1D0AE5C935A4D060E65C658ABC30CE29ACF65166141ACEE2",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    DRIVER: "5CDCA0BAF418207C6D19AAB16292D6BCEDCC010470F419E3DE4B9CE8B232D2AF",
    MAKEFILE: "F78867048E94D6A88B0685FAC010974217EA50F5E12F832BFDE96E215873353F",
    BUILDER: "16C115F6975CF6FA3A015F795FA8C97C14E48D684F25632FFD8B4D7EF028728A",
    PARSER: "68FF6EBCF90C05E9D19534D1311677FFC41D52CE64460B5635D7E59FA8F749F7",
    RUNNER: "58EA03DE86434C09438658A0F4CB0E32C8C39CD3BCF0186EF79FBEFA64173801",
    CANDIDATE: "00880EBC4678ED83927FE69A797876C0513BF7AE4D18119FCE5E7FC833A64F0B",
    CANDIDATE_ELF: "30552D02473C2943105D8159A7A361D33305947C474DF4234FD968CE3B9BF5D4",
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

    missing = [str(path) for path in [REGISTRY, RESTORE, NORMAL, *EXPECTED.keys()] if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"schema_id": "companion.wb55.ssd1681_ram_ping_pong_point_probe_static.v1", "status": "NO_GO_STATIC_POINT_PROBE", "checks": checks, "failures": failures}, indent=2) + "\n", encoding="utf-8")
        return 1

    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")
    registry = REGISTRY.read_text(encoding="utf-8")
    phase_a = json.loads(PHASE_A.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")

    require("registry_contract", "| COMP-REQ-266 |" in registry and "post_sync_0x24" not in registry, "COMP-REQ-266 contract drifted")
    require("unique_phase_a_admission", phase_a.get("status") == "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED" and phase_a.get("fingerprint", {}).get("unique_mapping") == "activation_swapped_banks_selector0_base_selector1_current" and phase_a.get("phase_b_admission", {}).get("admitted") is True, "Phase A does not uniquely admit Phase B")
    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["length_bytes"] == 524288 and baseline["shared_sha256"] == EXPECTED[BASELINE_A]
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("raw_restore_baseline", baseline_ok, "captured raw restore baseline is invalid")

    macro = "COMPANION_EPAPER_SSD1681_RAM_PING_PONG_POINT_PROBE_DIAGNOSTIC"
    require("default_off", f"#define {macro} 0" in driver and f"-D{macro}=1" in makefile, "point probe is not default-off")
    start = driver.find("static void ssd1681_ram_ping_pong_point_probe_diagnostic")
    end = driver.find("\n#endif", start)
    diagnostic = driver[start:end]
    loop_start = diagnostic.find("for (uint16_t frame = 0u")
    loop = diagnostic[loop_start:]
    require("function_and_24_frames", start >= 0 and "SSD1681_POINT_PROBE_FRAMES 24u" in driver and "frame < SSD1681_POINT_PROBE_FRAMES" in diagnostic, "24-frame diagnostic is absent")
    require("generic_diff_not_geometry_bound", "ssd1681_point_probe_diff_window(s_previous_frame, s_frame)" in diagnostic and "geometry_role=diagnostic_only" in diagnostic, "motion path is not generic previous/current framebuffer diff")
    require("one_ff_20_busy_per_frame", loop.count("ssd1681_command_data(0x22u") == 1 and loop.count("ssd1681_command(0x20u)") == 1 and loop.count("ssd1681_wait_refresh_complete(0u, 1000u)") == 1 and "controls_ff=24 refresh_20=24 busy_completions=24" in diagnostic, "per-frame FF/20/BUSY sequence differs")
    require("post_activation_0x24_sync", loop.count("ssd1681_point_probe_write_current(&window") == 2 and "post_sync_24=24 post_sync_refresh=0" in diagnostic, "post-activation 0x24 no-refresh sync is not exact")
    require("zero_motion_0x26", "ssd1681_command(0x26u)" not in loop and "motion_0x26_writes=0" in diagnostic, "motion loop writes 0x26 or lacks zero marker")
    require("seed_not_activated", diagnostic.count("ssd1681_command(0x26u)") == 1 and "seed banks=0x24,0x26 bytes_each=5000 activation=0" in diagnostic, "initial equal-bank seed differs")
    require("timing_bounds", "SSD1681_POINT_PROBE_FRAME_SPACING_MS 800u" in driver and "ssd1681_wait_refresh_complete(0u, 1000u)" in diagnostic, "frame/BUSY timing bounds differ")
    require("transfer_oracle", all(token in diagnostic for token in ("changed_bytes", "oracle_bytes", "stage_bytes == oracle_bytes", "sync_bytes == oracle_bytes")), "byte-aligned transfer oracle is incomplete")
    require("zero_forbidden_activation", all(token in diagnostic for token in ("full_refreshes=0", "controls_f7=0", "controls_c7=0", "lut_writes=0", "retries=0")) and "0x32u" not in diagnostic and "0x37u" not in diagnostic, "forbidden activation/LUT path is present")
    require("isolated_builder", "[switch]$EpaperSsd1681RamPingPongPointProbeDiagnostic" in builder and "build_ssd1681_ram_ping_pong_point_probe" in builder, "builder lacks isolated point probe")
    require("candidate_marker", "[epaper] ping_pong_probe start" in CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore"), "candidate ELF marker is absent")
    require("runner_binding", all(token in runner for token in ("[switch]$RamPingPongPointProbe", EXPECTED[CANDIDATE], "verify_wb55_ssd1681_ram_ping_pong_point_probe_log.py", "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE_RESTORED", "NO_GO_RAM_PING_PONG_POINT_PROBE_RESTORED")), "runner lacks exact Phase B binding")
    require("runner_preflight_zero_retry", runner.index("Captured raw baseline hash mismatch") < runner.index('$failureStage = "lock"') and "automatic_retries = 0" in runner and runner.count('Operation "candidate-write"') == 1, "runner preflight/retry/attempt boundary differs")
    finally_text = runner[runner.index("} finally {"):]
    require("one_finally_restore", finally_text.count('Operation "restore-write-verify-upload"') == 1 and all(token in finally_text for token in ('"-w", $backupA, "0x08000000"', '"-v", $backupA, "0x08000000"', '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"')), "finally raw restore differs")

    parser_test = subprocess.run([sys.executable, str(PARSER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    restore_test = subprocess.run([sys.executable, str(RESTORE), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    normal_test = subprocess.run([sys.executable, str(NORMAL), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    ps_parse = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"], cwd=ROOT, capture_output=True, text=True)
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("parser_negative_matrix", parser_test.returncode == 0, f"parser self-test failed: {parser_test.stderr.strip()}")
    require("restore_negative_matrix", restore_test.returncode == 0, f"restore self-test failed: {restore_test.stderr.strip()}")
    require("normal_negative_matrix", normal_test.returncode == 0, f"normal self-test failed: {normal_test.stderr.strip()}")
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout, f"runner parse failed: {ps_parse.stderr.strip()}")
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout, "programmer is not v2.22.0")

    result = {
        "schema_id": "companion.wb55.ssd1681_ram_ping_pong_point_probe_static.v1",
        "status": "PASS_STATIC_RAM_PING_PONG_POINT_PROBE_RAW_RESTORE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_POINT_PROBE",
        "claim_scope": "Static/build/host proof only; no Phase B hardware or visual result.",
        "checks": checks,
        "failures": failures,
        "candidate": {"hex_sha256": sha(CANDIDATE), "elf_sha256": sha(CANDIDATE_ELF)},
        "phase_a_mapping": phase_a["fingerprint"]["unique_mapping"],
        "baseline": {"bytes": 524288, "sha256": EXPECTED[BASELINE_A]},
        "host_tests": {"parser": parser_test.stdout.strip(), "restore": restore_test.stdout.strip(), "normal": normal_test.stdout.strip()},
        "forbidden_claims": ["no hardware/visual/production result", "no LUT/waveform/temperature/voltage/Rig/CRIG/touch/BLE change"],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
