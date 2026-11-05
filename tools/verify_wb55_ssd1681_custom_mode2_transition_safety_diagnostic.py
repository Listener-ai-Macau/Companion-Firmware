#!/usr/bin/env python3
"""Fail-closed static gate for the bounded custom Mode2 safety candidate."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from verify_wb55_ur_application_backup import BackupError, validate_pair


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_transition_safety_log.py"
WORKBENCH_TOOL = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_transition_timing_workbench_r4.py"
WORKBENCH = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r4-20260721.json"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
DETACHED_LAUNCHER = ROOT / "tools/start_wb55_ssd1681_custom_mode2_transition_safety.ps1"
DETACHED_LAUNCHER_VERIFIER = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_detached_launcher.py"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
FPC = ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
WHITE_RAIL = ROOT / "docs/validation/companion-screen-wb55-white-rail-measurement-current-source-r2-20260720.json"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_custom_mode2_transition_safety/Companion_Nucleo_WB55RG_Ssd1681CustomMode2TransitionSafety.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
PRECLEAN_IMAGE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_official_full_diagnostic_white/Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
PRECLEAN_PARSER = ROOT / "tools/verify_wb55_official_full_diagnostic_log.py"
PRECLEAN_SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-r2-20260721.json"
WHITE_RECOVERY = ROOT / "docs/validation/companion-ssd1681-official-white-clean-recovery-r1-20260721.json"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    WORKBENCH: "E7467B808CE7BD1BE317BC282B7990CF343922DE8C15B092588B9968DEAB444D",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    FPC: "E1124866DBBBF083B3512EB75A4C8AE14BF6808ACCDD45B774A5095BD41D7D35",
    WHITE_RAIL: "827DC52B8E7CA8CF0BF0B6E5CC2A64D37F3B1F69C1B73E4D2CED2CA7E6C51A8C",
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    CANDIDATE: "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564",
    CANDIDATE_ELF: "BD1003A14BB2F62B58E6A56AA2926633D3A1B5A8FD58BC6D263E8FE2A56A2698",
    PRECLEAN_IMAGE: "F7CB7EE8C497CF1A01ACFF4BC921B43E274B0A934CA8B658AC24C34480F32925",
    PRECLEAN_SOURCE_AUDIT: "5395705759D9F149B0CCE4FCC5C576B78D3A13A5FBD45FF0F0799495736EF645",
    WHITE_RECOVERY: "77A30C9151B34C59FA48D193F30D59939ABC901E88083E55DB91BDC6FDC8E17C",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}
LUT_SHA = "75D7647188ACF1C79BC37313DC40105AF4445B9B6F422AD4FDAF0A465413984D"
R4_TP_DIFF_OFFSETS = {61, 64, 75, 78}
R4_ACTIVE_TP_GROUPS = [[60, 61, 63, 64, 67, 68], [74, 75, 77, 78, 81, 82]]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_array(source: str, name: str) -> list[int]:
    match = re.search(
        rf"static\s+const\s+uint8_t\s+{re.escape(name)}\[159\]\s*=\s*\{{(.*?)\}};",
        source,
        re.DOTALL,
    )
    return [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1))] if match else []


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    required = [DRIVER, MAKEFILE, BUILDER, PARSER, WORKBENCH_TOOL, RUNNER, DETACHED_LAUNCHER, DETACHED_LAUNCHER_VERIFIER, RESTORE, NORMAL, PRECLEAN_PARSER, REGISTRY, *EXPECTED.keys()]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"status": "NO_GO_STATIC_CUSTOM_MODE2", "failures": failures}, indent=2) + "\n", encoding="utf-8")
        return 1
    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")

    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    workbench = json.loads(WORKBENCH.read_text(encoding="utf-8"))
    fpc = json.loads(FPC.read_text(encoding="utf-8"))
    white_rail = json.loads(WHITE_RAIL.read_text(encoding="utf-8"))
    candidate = parse_array(driver, "ssd1681_custom_mode2_transition_lut")
    expected_candidate = bytes.fromhex(workbench["candidate"]["r4_lut_hex"])

    require("registry_authorization", all(f"| COMP-REQ-{req} |" in registry for req in (285, 289, 292)), "COMP-REQ-285/289/292 authorization missing")
    require("workbench_admission", workbench.get("status") == "PASS_WORKBENCH_ADMIT_UNIFORM_ACTIVE_TP16_MODE2_R4" and not workbench.get("errors"), "workbench did not admit R4 uniform TP16")
    require("candidate_array_exact", bytes(candidate) == expected_candidate and sha_bytes(bytes(candidate)) == LUT_SHA, "driver candidate differs from workbench bytes")
    require("protected_tail", candidate[153:159] == [0x22, 0x17, 0x41, 0xA8, 0x32, 0x58], "protected voltage tail differs")
    require("transition_tables_exact", candidate[12:36] == list(expected_candidate[12:36]), "BW/WB transition tables differ")
    diff_offsets = {item.get("offset") for item in workbench["candidate"].get("byte_differences_from_r2", [])}
    model = workbench.get("timing_model", {})
    require("single_tp_mechanism_diff", diff_offsets == R4_TP_DIFF_OFFSETS, "R4 changes bytes outside the admitted quantized TP16 assignment")
    require("uniform_tp16", model.get("r4_tp_frame_counts") == 16 and model.get("predicted_r4_busy_ms", 999) <= 550 and model.get("predicted_margin_ms", 0) >= 50, "R4 TP16 timing thresholds differ")
    require("symmetric_integer_allocation", workbench["candidate"].get("active_tp_groups") == R4_ACTIVE_TP_GROUPS and workbench["candidate"].get("group_outputs") == [[2, 1, 2, 1, 1, 1], [2, 1, 2, 1, 1, 1]] and workbench["candidate"].get("all_active_fields_nonzero") is True, "R4 active TP group allocation differs")

    macro = "COMPANION_EPAPER_SSD1681_CUSTOM_MODE2_TRANSITION_SAFETY_DIAGNOSTIC"
    require("default_off", f"#define {macro} 0" in driver and f"-D{macro}=1" in makefile, "candidate is not compile-time default-off")
    start = driver.find("static void ssd1681_custom_mode2_transition_safety_diagnostic")
    end = driver.find("\n#endif", start)
    diagnostic = driver[start:end]
    require("function_present", start >= 0, "custom Mode2 safety function missing")
    require("bounded_activations", "SSD1681_CUSTOM_MODE2_ACTIVATIONS 9u" in driver and "step < SSD1681_CUSTOM_MODE2_ACTIVATIONS" in diagnostic, "activation count is not exactly 9")
    require("local_window", all(token in driver for token in ("WINDOW_X_START_BYTE 1u", "WINDOW_X_END_BYTE 4u", "WINDOW_Y_START 8u", "WINDOW_Y_END 39u", "WINDOW_BYTES 128u")), "32x32 local window differs")
    require("explicit_old_new", diagnostic.count("ssd1681_custom_mode2_write_plane(&window, 0x26u") == 1 and diagnostic.count("ssd1681_custom_mode2_write_plane(&window, 0x24u") == 1, "explicit old/new plane topology differs")
    require("cf_20_busy", "mode2_display[] = {0xCFu}" in diagnostic and diagnostic.count("ssd1681_command_data(0x22u") == 1 and diagnostic.count("ssd1681_command(0x20u)") == 1 and diagnostic.count("ssd1681_wait_refresh_complete(0u, 600u)") == 1, "CF/20/BUSY topology or 600 ms limit differs")
    require("exact_lut_load", all(token in diagnostic for token in ("0x3Fu, &ssd1681_custom_mode2_transition_lut[153], 1u", "0x03u, &ssd1681_custom_mode2_transition_lut[154], 1u", "0x04u, &ssd1681_custom_mode2_transition_lut[155], 3u", "0x2Cu, &ssd1681_custom_mode2_transition_lut[158], 1u", "0x32u, ssd1681_custom_mode2_transition_lut, 153u")), "exact LUT/tail load topology differs")
    require("no_reset_after_load", diagnostic.count("ssd1681_point_probe_hard_reset();") == 1 and diagnostic.find("ssd1681_point_probe_hard_reset();") < diagnostic.find("0x32u"), "hard reset exists after custom LUT load")
    require("four_class_oracle", all(token in diagnostic for token in ("ww=", "wb=", "bw=", "bb=", "previous_patterns", "current_patterns")), "four-transition oracle/logging missing")
    require("final_local_white", "2u, 0u};" in diagnostic and "final_local_state=%s" in diagnostic, "final local white restore step missing")
    require("forbidden_controls_zero", all(token in diagnostic for token in ("full_refreshes=0", "controls_ff=0", "controls_f7=0", "controls_c7=0", "retries=0", "voltage_tail_changes=0")), "forbidden control count marker missing")
    require("isolated_builder", "[switch]$EpaperSsd1681CustomMode2TransitionSafetyDiagnostic" in builder and "build_ssd1681_custom_mode2_transition_safety" in builder, "isolated builder target missing")
    require("candidate_marker", "[epaper] custom_mode2_safety start" in CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore"), "candidate ELF marker missing")
    require("runner_binding", all(token in runner for token in ("[switch]$CustomMode2TransitionSafety", f'$candidateSha256 = "{EXPECTED[CANDIDATE]}"', "production-off R4 custom Mode2 candidate", PARSER.name, "PASS_MACHINE_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED", "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED", "$observedTransitions = @($report.controller_state.observed.steps).Count", "panel_refresh_commands = $observedTransitions")), "raw-restore R4 binding differs")
    prompt_pos = runner.find("$startDecision = Invoke-CandidateStartPrompt")
    preclean_pos = runner.find('Operation "preclean-white-write"')
    candidate_pos = runner.find('Operation "candidate-write"')
    require("runner_preexecute_prompt", all(token in runner for token in ('-Title "Companion R4 局刷实验开始确认"', '-Buttons "开始实验,取消"', '$startDecision.selected -ne "开始实验"', "shown_before_hardware_contact = $true")) and 0 <= prompt_pos < preclean_pos, "canonical R4 pre-execute start gate missing or ordered after hardware")
    require("runner_preclean_before_candidate", all(token in runner for token in (EXPECTED[PRECLEAN_IMAGE], PRECLEAN_PARSER.name, "--pattern white", "official_0x24_f7_white", "excluded_from_candidate_metrics = $true", "Deterministic White pre-clean machine gate failed; candidate is forbidden.")) and 0 <= preclean_pos < candidate_pos, "source-bound White pre-clean is missing or ordered after candidate")
    require("runner_single_write_restore", runner.count('Operation "preclean-white-write"') == 1 and runner.count('Operation "candidate-write"') == 1 and runner.count('Operation "restore-write-verify-upload"') == 1 and "automatic_retries = 0" in runner, "runner preclean/candidate/restore/retry boundary differs")
    require("runner_preclean_failure_restores", "if ($hardwareImageAttempted)" in runner and "NO_GO_CUSTOM_MODE2_PRECLEAN_RESTORED" in runner, "pre-clean failure is not restore-bound")
    launcher = DETACHED_LAUNCHER.read_text(encoding="utf-8")
    require("detached_launcher_contract", all(token in launcher for token in ('Start-Process -FilePath "pwsh"', "-RedirectStandardOutput $stdout", "-RedirectStandardError $stderr", "output directory already exists; reuse is forbidden", '"-CustomMode2TransitionSafety"', '"STARTED_DETACHED"')), "detached launcher durability/reuse/custom-mode contract differs")
    require("fpc_prerequisite", fpc.get("status") == "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE", "replacement FPC prerequisite missing")
    require("white_rail_prerequisite", white_rail.get("status") == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE", "White rail prerequisite missing")
    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["length_bytes"] == 524288 and baseline["shared_sha256"] == EXPECTED[BASELINE_A]
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("raw_restore_baseline", baseline_ok, "captured raw restore baseline invalid")

    tests = {}
    for name, command in {
        "workbench": [sys.executable, str(WORKBENCH_TOOL)],
        "parser": [sys.executable, str(PARSER), "--self-test"],
        "detached_launcher": [sys.executable, str(DETACHED_LAUNCHER_VERIFIER)],
        "restore": [sys.executable, str(RESTORE), "--self-test"],
        "normal": [sys.executable, str(NORMAL), "--self-test"],
    }.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        tests[name] = proc.stdout.strip()
        require(f"{name}_test", proc.returncode == 0, f"{name} test failed: {proc.stderr.strip()}")
    ps_parse = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"], cwd=ROOT, capture_output=True, text=True)
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout, f"runner parse failed: {ps_parse.stderr.strip()}")
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout, "programmer is not v2.22.0")

    result = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_transition_safety_static.v1",
        "status": "PASS_STATIC_CUSTOM_MODE2_TRANSITION_SAFETY_DEFAULT_OFF_RAW_RESTORE" if not failures else "NO_GO_STATIC_CUSTOM_MODE2",
        "hardware_contact": 0,
        "checks": checks,
        "failures": failures,
        "candidate": {"hex_sha256": sha(CANDIDATE), "elf_sha256": sha(CANDIDATE_ELF), "lut_sha256": LUT_SHA},
        "prerequisites": {"replacement_fpc_status": fpc.get("status"), "white_rail_status": white_rail.get("status")},
        "baseline": {"bytes": 524288, "sha256": EXPECTED[BASELINE_A]},
        "host_tests": tests,
        "source_hashes": {str(path): sha(path) for path in (DRIVER, MAKEFILE, BUILDER, PARSER, WORKBENCH_TOOL, RUNNER, DETACHED_LAUNCHER, DETACHED_LAUNCHER_VERIFIER)},
        "production_allowed": False,
        "human_acceptance_required_after_machine_pass": True,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


if __name__ == "__main__":
    raise SystemExit(main())
