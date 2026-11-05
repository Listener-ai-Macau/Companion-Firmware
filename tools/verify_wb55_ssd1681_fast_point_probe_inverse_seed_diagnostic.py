#!/usr/bin/env python3
"""Static/raw-restore gate for fast-point round 2 inverse previous-plane seed."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from verify_wb55_ur_application_backup import BackupError, validate_pair


ROOT = Path(__file__).resolve().parents[1]
P = lambda value: ROOT / value
REGISTRY = P("docs/companion_product_requirements.md")
PHASE_A = P("docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json")
DIAGNOSIS = P("docs/validation/companion-ssd1681-fast-point-probe-round1-diagnosis-20260721.json")
OWNER = P("docs/validation/companion-pet-special-system-owner-acceptance-20260717.json")
SUPPLIER = P(".cache/incoming/S-GDEY0154D67-FP-Touch-official-20260720/S-GDEY0154D67-FP-Touch20230303/HARDWARE/EPD/Display_EPD_W21.c")
BASE_A = P(".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin")
BASE_B = P(".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin")
DRIVER = P("app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c")
MAKEFILE = P("cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile")
BUILDER = P("tools/build_nucleo_bringup.ps1")
PARSER = P("tools/verify_wb55_ssd1681_fast_point_probe_inverse_seed_log.py")
RUNNER = P("tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1")
RESTORE = P("tools/verify_wb55_raw_application_restore.py")
NORMAL = P("tools/verify_wb55_normal_resume_after_ur_backup_log.py")
HEX = P("cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_fast_point_probe_inverse_seed/Companion_Nucleo_WB55RG_Ssd1681FastPointProbeInverseSeed.hex")
ELF = HEX.with_suffix(".elf")
OUT = P("docs/validation/companion-ssd1681-fast-point-probe-inverse-seed-static-20260721.json")
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    PHASE_A: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    DIAGNOSIS: "990B3D9AEB57B21F8AB4A02AE98900394AC25D780694845E9D52E55F6E53F929",
    OWNER: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    SUPPLIER: "CD08AFD1D56E8F7E1D0AE5C935A4D060E65C658ABC30CE29ACF65166141ACEE2",
    BASE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    DRIVER: "E88FAB6309DFC9FC83455E76319E6196C252A62809FEB7C21860E369CB6CE3AA",
    MAKEFILE: "B2C28E1C7EC1D20A3A20E248D749DEFB605571270A69DF7E1FDA6EBF56D3DE94",
    BUILDER: "83CF4CA96F3A4F65B4B3AAF9BA56B69C41B51E1ABCA0061EB7422B8E091E5739",
    PARSER: "F08406218CA0544BB5D10F5A9E027B4EA3A80894854DAF335259784D490ED547",
    RUNNER: "675210ED4CD20B0D176A9F151617FE8E3ED694734411F6CF8077870E50CAFC4B",
    HEX: "F7E20B26A479F690064F95FED25B18F632B3CDBC2AEDDD842645377CA0EBB2E9",
    ELF: "D5D61FCFAAFFCD1FBAC3199E5864C9660B1759E1BDC683C1BE5E4A5B7A5B2FF2",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, value: bool, detail: str) -> None:
        checks[name] = bool(value)
        if not value:
            failures.append(detail)

    missing = [str(path) for path in [REGISTRY, RESTORE, NORMAL, *EXPECTED] if not path.is_file()]
    require("inputs", not missing, f"missing inputs: {missing}")
    if missing:
        return 1
    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")

    registry = REGISTRY.read_text(encoding="utf-8")
    diagnosis = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    phase_a = json.loads(PHASE_A.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    require("registry", "| COMP-REQ-275 |" in registry and "没看出来有移动, 屏幕无变化" in registry, "round-1 steering is absent")
    require("diagnosis", diagnosis.get("status") == "PASS_DIAGNOSIS_PREVIOUS_PLANE_NOT_PHYSICALLY_SYNCHRONIZED" and diagnosis.get("next_single_variable", {}).get("name") == "first_frame_previous_plane_seed", "round-1 diagnosis does not admit this candidate")
    require("ram_phase", phase_a.get("fingerprint", {}).get("unique_mapping") == "activation_swapped_banks_selector0_base_selector1_current", "RAM phase mapping drifted")
    try:
        baseline = validate_pair(BASE_A.read_bytes(), BASE_B.read_bytes())
        baseline_ok = baseline["length_bytes"] == 524288 and baseline["shared_sha256"] == EXPECTED[BASE_A]
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("raw_restore", baseline_ok, "raw restore baseline invalid")

    macro = "COMPANION_EPAPER_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_DIAGNOSTIC"
    require("default_off", f"#define {macro} 0" in driver and f"-D{macro}=1" in makefile, "inverse seed is not default-off")
    start = driver.find("static void ssd1681_fast_point_probe_diagnostic(bool inverse_seed)")
    end = driver.find("\n#endif", start)
    body = driver[start:end]
    loop = body[body.find("for (uint16_t frame = 0u"):]
    require("single_variable_seed", all(token in body for token in ("if (inverse_seed)", "first_previous_plane_seed=local_inverse_corridor", "current_0x24=frame1 previous_0x26=local_inverse_corridor")), "inverse previous-plane seed code/markers absent")
    require("first_frame_corridor", "x < x_positions[4] + SSD1681_POINT_PROBE_SIZE" in body and "s_previous_frame[index] &= (uint8_t)~mask" in body, "inverse trajectory corridor differs")
    require("unchanged_motion_topology", loop.count("ssd1681_command_data(0x22u") == 1 and loop.count("ssd1681_command(0x20u)") == 1 and loop.count("ssd1681_wait_refresh_complete(0u, 1000u)") == 1 and loop.count("ssd1681_point_probe_write_current(&window") == 2, "one FF/20/BUSY/two 0x24 writes per frame drifted")
    require("zero_forbidden", "ssd1681_command(0x26u)" not in loop and all(token in body for token in ("motion_0x26_writes=0", "full_refreshes=0", "controls_f7=0", "controls_c7=0", "lut_writes=0", "retries=0")) and "0x32u" not in body, "motion/full/LUT/retry boundary drifted")
    require("cadence_trajectory", all(token in body for token in ("frames=120", "target_spacing_ms=500", "step_px=8", "excursion_px=32", "countdown = 3u")), "cadence/trajectory drifted")
    require("isolated_build", "[switch]$EpaperSsd1681FastPointProbeInverseSeedDiagnostic" in builder and "build_ssd1681_fast_point_probe_inverse_seed" in builder, "isolated inverse-seed builder absent")
    require("candidate_marker", "first_previous_plane_seed=local_inverse_corridor" in ELF.read_bytes().decode("latin1", errors="ignore"), "ELF inverse-seed marker absent")
    require("runner_binding", all(token in runner for token in ("[switch]$FastPointProbeInverseSeed", EXPECTED[HEX], "verify_wb55_ssd1681_fast_point_probe_inverse_seed_log.py", "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED", "NO_GO_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED")), "runner binding differs")
    require("one_attempt", runner.count('Operation "candidate-write"') == 1 and "automatic_retries = 0" in runner, "one-attempt boundary differs")
    finally_text = runner[runner.index("} finally {"):]
    require("finally_restore", finally_text.count('Operation "restore-write-verify-upload"') == 1 and all(token in finally_text for token in ('"-w", $backupA, "0x08000000"', '"-v", $backupA, "0x08000000"', '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"')), "finally restore differs")

    tests = {}
    for name, command in {"parser": [sys.executable, str(PARSER), "--self-test"], "restore": [sys.executable, str(RESTORE), "--self-test"], "normal": [sys.executable, str(NORMAL), "--self-test"]}.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        tests[name] = proc.stdout.strip()
        require(f"{name}_self_test", proc.returncode == 0, f"{name} self-test failed")
    ps = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"], capture_output=True, text=True)
    ver = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("runner_parse", ps.returncode == 0 and "PASS" in ps.stdout, "runner PowerShell parse failed")
    require("programmer", ver.returncode == 0 and "version: 2.22.0" in ver.stdout, "programmer version differs")
    result = {
        "schema_id": "companion.wb55.ssd1681_fast_point_probe_inverse_seed_static.v1",
        "status": "PASS_STATIC_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RAW_RESTORE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_INVERSE_SEED",
        "checks": checks, "failures": failures, "single_variable": "first_frame_previous_plane_seed",
        "candidate": {"hex_sha256": sha(HEX), "elf_sha256": sha(ELF)}, "host_tests": tests,
        "claim_scope": "Machine-ready evidence only; hardware_contact=0 and no visual claim.",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
