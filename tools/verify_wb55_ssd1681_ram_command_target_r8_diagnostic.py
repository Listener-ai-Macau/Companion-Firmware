#!/usr/bin/env python3
"""Static/build/runner gate for the default-off R8 RAM target discriminator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from verify_wb55_ur_application_backup import BackupError, validate_pair


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_ram_command_target_r8.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_ram_command_target_r8_log.py"
PRECLEAN_PARSER = ROOT / "tools/verify_wb55_ssd1681_dual_plane_white_clean_log.py"
RESTORE_VERIFIER = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL_VERIFIER = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
PHASE_A = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json"
R7 = ROOT / "docs/validation/companion-ssd1681-r7-activation-state-audit-20260721.json"
INCIDENT = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-launch-transport-incident-20260721.json"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
BASELINE_ROOT = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private"
BASELINE_A = BASELINE_ROOT / "backup-a.bin"
BASELINE_B = BASELINE_ROOT / "backup-b.bin"
CANDIDATE_DIR = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_ram_command_target_r8"
CANDIDATE = CANDIDATE_DIR / "Companion_Nucleo_WB55RG_Ssd1681RamCommandTargetR8.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
PRECLEAN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_dual_plane_white_clean/Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean.hex"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")
OUTPUT = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-static-20260721.json"

EXPECTED = {
    PHASE_A: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    R7: "404D86ACBF7F25EC6B1D39002065800CAD2FAB8698E3BBF3285B40AA36FA73C2",
    INCIDENT: "C3D8C8809C2C807592A92D9749F235013AF465434DD16ED9B558308E71CB7900",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    PRECLEAN: "3AC4E52E37E15DC3CC058A4B0B0E6A3227D23E6C6DEFAEDCB786C08497888AAD",
    CANDIDATE: "9ECF8F4A2A75A054077908C775879447ADCE089F55DC33315A8C852C4F47CB13",
    CANDIDATE_ELF: "D03547885EAB885AF206FB7971F9C99D96BAE315CAC16D8F361E3F2D832D6852",
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

    required = [
        REGISTRY, DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PARSER, PRECLEAN_PARSER,
        RESTORE_VERIFIER, NORMAL_VERIFIER, *EXPECTED.keys(),
    ]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUTPUT.write_text(json.dumps({
            "schema_id": "companion.wb55.ssd1681_ram_command_target_r8.machine_ready.v2",
            "status": "NO_GO_R8_STATIC_INPUTS",
            "hardware_contact": 0,
            "checks": checks,
            "failures": failures,
        }, indent=2) + "\n", encoding="utf-8")
        return 1

    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")

    registry = REGISTRY.read_text(encoding="utf-8")
    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    phase_a = json.loads(PHASE_A.read_text(encoding="utf-8"))
    r7 = json.loads(R7.read_text(encoding="utf-8"))

    require(
        "registry_comp_req_302",
        "| COMP-REQ-302 |" in registry
        and "readback-only discriminator" in registry
        and "automatic `-Execute` is forbidden" in registry,
        "COMP-REQ-302 R8 contract is missing",
    )
    require(
        "registry_comp_req_304_305",
        "| COMP-REQ-304 |" in registry
        and "MACHINE_READY_R8_R2" in registry
        and "| COMP-REQ-305 |" in registry
        and "machine-only R8 command-target run therefore has no canonical operator window" in registry,
        "COMP-REQ-304/305 transport and popup steering is missing",
    )
    require(
        "sealed_phase_a",
        phase_a.get("fingerprint", {}).get("unique_mapping")
        == "activation_swapped_banks_selector0_base_selector1_current",
        "sealed Phase-A selector mapping differs",
    )
    require(
        "r7_evidence_gap",
        r7.get("status")
        == "NO_GO_R7_POST_ACTIVATION_SYNC_TARGET_UNPROVEN_NO_NEW_VISUAL_CANDIDATE"
        and r7.get("recommendation", {}).get("next_hardware_variable") is None,
        "R7 evidence-gap disposition differs",
    )
    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["length_bytes"] == 524288 and baseline["shared_sha256"] == EXPECTED[BASELINE_A]
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("exact_raw_baseline", baseline_ok, "captured raw application baseline differs")

    macro = "COMPANION_EPAPER_SSD1681_RAM_COMMAND_TARGET_R8_DIAGNOSTIC"
    require(
        "default_off_isolated_build",
        f"#define {macro} 0" in driver
        and f"-D{macro}=1" in makefile
        and "EPAPER_SSD1681_RAM_COMMAND_TARGET_R8_DIAGNOSTIC=1" in builder
        and "build_ssd1681_ram_command_target_r8" in builder,
        "R8 is not default-off and isolated",
    )
    start = driver.find("static void ssd1681_ram_command_target_r8_diagnostic")
    end = driver.find("#if COMPANION_EPAPER_SSD1681_DUAL_PLANE_WHITE_CLEAN_DIAGNOSTIC", start)
    diagnostic = driver[start:end]
    r8_block_start = driver.rfind(
        "#if COMPANION_EPAPER_SSD1681_RAM_COMMAND_TARGET_R8_DIAGNOSTIC",
        0,
        start,
    )
    r8_block = driver[r8_block_start:end]
    probe_start = driver.find("static bool ssd1681_r8_probe_command")
    probe_end = driver.find("static void ssd1681_ram_command_target_r8_diagnostic", probe_start)
    probe = driver[probe_start:probe_end]
    read_start = driver.find("static bool ssd1681_fingerprint_read_ram")
    read_end = driver.find("static bool ssd1681_fingerprint_capture_stage", read_start)
    read_helper = driver[read_start:read_end]
    require("diagnostic_functions_present", start >= 0 and end > start and probe_start >= 0, "R8 functions are missing")
    require(
        "one_known_swap_activation",
        diagnostic.count("ssd1681_command_data(0x22u") == 1
        and diagnostic.count("ssd1681_command(0x20u)") == 1
        and diagnostic.count("ssd1681_wait_refresh_complete") == 1
        and "partial_update[] = {0xFFu}" in diagnostic
        and "swap_activations=1" in diagnostic,
        "R8 known-swap activation is not singular FF/20/BUSY",
    )
    require(
        "zero_post_tag_activation",
        "0x22u" not in probe
        and "0x20u" not in probe
        and "wait_refresh_complete" not in probe
        and "activation_after_tag=0" in probe
        and "post_tag_activations=0" in diagnostic,
        "R8 probe can activate a tag",
    )
    require(
        "distinct_tags_and_restores",
        all(token in diagnostic for token in (
            "memset(swap_seed, 0xC3", "memset(tag24, 0x5A", "memset(tag26, 0xA5",
            "ssd1681_r8_probe_command(0x24u", "ssd1681_r8_probe_command(0x26u",
        ))
        and "ssd1681_r8_extract_window" in probe
        and "ssd1681_r8_write_tag(command, restore)" in probe,
        "R8 tags or same-command restore differ",
    )
    require(
        "selector_repeat_readback",
        all(token in read_helper for token in ("ssd1681_fingerprint_set_window", "0x41u", "0x27u"))
        and "for (uint8_t selector = 0u; selector < 2u" in r8_block
        and "for (uint8_t repeat = 0u; repeat < 2u" in r8_block
        and "selector_reads=28" in diagnostic
        and all(stage in diagnostic for stage in (
            "before_swap", "before_swap_activation", "after_swap",
            "after_tag_24", "after_restore_24", "after_tag_26", "after_restore_26",
        )),
        "R8 selector/repeat/stage readback contract differs",
    )
    require(
        "no_unknown_waveform_or_motion",
        all(token not in diagnostic for token in (
            "0x32u", "0x37u", "0xCFu", "0xF7u", "0xC7u",
            "ball_motion", "point_probe", "HAL_Delay(800", "120u",
        )),
        "R8 contains a forbidden waveform/full/motion mechanism",
    )
    require(
        "machine_mapping_classification",
        "mapping = \"fixed_bank\"" in diagnostic
        and "mapping = \"role_based_current_0x24_base_0x26\"" in diagnostic
        and "mapping = \"unresolved\"" in diagnostic,
        "R8 mapping classification is incomplete",
    )

    elf_text = CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore")
    require(
        "candidate_markers",
        all(marker in elf_text for marker in (
            "ram_command_target_r8 start", "post_tag_activations=0",
            "role_based_current_0x24_base_0x26",
        )),
        "R8 ELF lacks locked contract markers",
    )
    require(
        "runner_locked_lifecycle",
        all(token in runner for token in (
            "[switch]$RamCommandTargetR8", EXPECTED[CANDIDATE],
            "verify_wb55_ssd1681_ram_command_target_r8_log.py",
            "PASS_MACHINE_RAM_COMMAND_TARGET_R8_RESTORED",
            "supplier_basemap_0x24_0x26_f7_white_readback",
            "machine_only_r8_total", "final_visual_acceptance_only_outside_machine_runner",
        )),
        "R8 runner image/parser/prompt binding differs",
    )
    require(
        "runner_zero_popup_policy",
        "Invoke-CandidateStartPrompt" not in runner
        and "Invoke-RestoreFailurePrompt" not in runner
        and "operator-prompt" not in runner
        and 'pre_execute = 0' in runner
        and 'recovery_or_fault_acknowledgement = 0' in runner
        and 'NO_GO_RESTORE_OR_APPLICATION_FAILED_PROMPTLESS' in runner,
        "R8 runner can still open a start, cleanup, recovery, or machine-only popup",
    )
    require(
        "persistent_launcher_contract",
        all(token in launcher for token in (
            "R8 persistent launch output directory already exists; reuse is forbidden",
            'Start-Process -FilePath "pwsh"',
            "-RedirectStandardOutput $stdout", "-RedirectStandardError $stderr",
            "-WindowStyle Hidden -PassThru", '"-RamCommandTargetR8"',
            '"STARTED_DETACHED"', '"READY_NO_HARDWARE_CONTACT"',
            '"NO_GO_CHECK_CHILD_EXIT"', 'process_id = $process.Id',
            'observer_may_exit_without_closing_runner_streams = $true',
            EXPECTED[CANDIDATE], EXPECTED[INCIDENT],
        ))
        and launcher.count('Start-Process -FilePath "pwsh"') == 1,
        "R8 persistent launcher durability/hash/fail-closed contract differs",
    )
    static_index = runner.index("& python $staticVerifier")
    checkonly_index = runner.index("if ($CheckOnly) {", static_index)
    lock_index = runner.index('$failureStage = "lock"')
    require(
        "runner_checkonly_before_contact",
        static_index < checkonly_index < lock_index
        and 'status = "READY_NO_HARDWARE_CONTACT"' in runner,
        "R8 CheckOnly is not fail-closed before hardware contact",
    )
    finally_text = runner[runner.index("} finally {"):]
    require(
        "runner_postclean_and_exact_restore",
        "$commandTargetR8 -and $precleanAttempted" in finally_text
        and finally_text.count('Operation "postclean-white-write"') == 1
        and finally_text.count('Operation "restore-write-verify-upload"') == 1
        and all(token in finally_text for token in (
            '"-w", $backupA, "0x08000000"',
            '"-v", $backupA, "0x08000000"',
            '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"',
            "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES",
        )),
        "R8 postclean or exact restore finally contract differs",
    )
    require(
        "no_automatic_execute",
        "-Execute" not in runner[runner.find("if ($CheckOnly)"):runner.find('$failureStage = "lock"')]
        and "automatic_retries = 0" in runner,
        "R8 runner can automatically cross into Execute or retry",
    )

    parser_test = subprocess.run([sys.executable, str(PARSER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    preclean_test = subprocess.run([sys.executable, str(PRECLEAN_PARSER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    restore_test = subprocess.run([sys.executable, str(RESTORE_VERIFIER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    normal_test = subprocess.run([sys.executable, str(NORMAL_VERIFIER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    ps_parse = subprocess.run([
        "pwsh", "-NoProfile", "-Command",
        f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'",
    ], cwd=ROOT, capture_output=True, text=True)
    launcher_parse = subprocess.run([
        "pwsh", "-NoProfile", "-Command",
        f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{LAUNCHER}' -Raw)); 'PASS'",
    ], cwd=ROOT, capture_output=True, text=True)
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("parser_negative_fixtures", parser_test.returncode == 0, f"R8 parser fixtures failed: {parser_test.stderr}")
    require("preclean_negative_fixtures", preclean_test.returncode == 0, f"dual-plane White fixtures failed: {preclean_test.stderr}")
    require("restore_negative_fixtures", restore_test.returncode == 0, f"restore fixtures failed: {restore_test.stderr}")
    require("normal_negative_fixtures", normal_test.returncode == 0, f"normal fixtures failed: {normal_test.stderr}")
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout, f"runner parse failed: {ps_parse.stderr}")
    require("launcher_powershell_parse", launcher_parse.returncode == 0 and "PASS" in launcher_parse.stdout, f"launcher parse failed: {launcher_parse.stderr}")
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout, "programmer version differs")

    source_paths = (DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PARSER, PRECLEAN_PARSER, RESTORE_VERIFIER, NORMAL_VERIFIER)
    result = {
        "schema_id": "companion.wb55.ssd1681_ram_command_target_r8.machine_ready.v2",
        "status": "MACHINE_READY_R8_R2_NO_HARDWARE_CONTACT_EXECUTE_FORBIDDEN_PENDING_ROOT" if not failures else "NO_GO_R8_R2_STATIC_GATE",
        "claim_scope": "Static, parser, isolated-build and CheckOnly readiness only; no panel command, flash, visual or production result.",
        "hardware_contact": 0,
        "execute_performed": False,
        "goal_action": "none_root_owned",
        "checks": checks,
        "failures": failures,
        "candidate": {
            "hex_sha256": sha(CANDIDATE),
            "elf_sha256": sha(CANDIDATE_ELF),
            "swap_activations_max": 1,
            "post_tag_activations": 0,
            "selector_reads": 28,
            "human_visual_verdict": False,
        },
        "protected_hashes": {
            str(OWNER_ACCEPTANCE.relative_to(ROOT)).replace("\\", "/"): sha(OWNER_ACCEPTANCE),
            str(SUPPLIER): sha(SUPPLIER),
        },
        "source_manifest": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
            for path in source_paths
        },
        "host_tests": {
            "r8_parser": parser_test.stdout.strip(),
            "dual_plane_white_parser": preclean_test.stdout.strip(),
            "restore": restore_test.stdout.strip(),
            "normal_resume": normal_test.stdout.strip(),
            "runner_parse": ps_parse.stdout.strip(),
            "launcher_parse": launcher_parse.stdout.strip(),
        },
        "popup_policy": {
            "machine_only_r8_total": 0,
            "cleanup": 0,
            "recovery_or_fault_acknowledgement": 0,
            "pre_execute": 0,
            "visual_candidate_final_acceptance_only": 1,
        },
        "next_boundary": "root review and a new explicit one-run authorization; do not invoke launcher or runner -Execute",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
