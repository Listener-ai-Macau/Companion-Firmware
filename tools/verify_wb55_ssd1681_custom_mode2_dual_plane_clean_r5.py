#!/usr/bin/env python3
"""Fail-closed static gate for R5 dual-plane clean around the locked R4 candidate."""

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
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_custom_mode2_dual_plane_clean_r5.ps1"
DUAL_PARSER = ROOT / "tools/verify_wb55_ssd1681_dual_plane_white_clean_log.py"
R4_PARSER = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_transition_safety_log.py"
R4_WORKBENCH_TOOL = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_transition_timing_workbench_r4.py"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
RAM_SOURCE = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-source-hash-20260721.json"
RAM_MACHINE = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json"
R4_PRECLEAN = ROOT / ".cache/validation/wb55-custom-mode2-transition-safety-r4-execute-20260721-a/preclean-white.json"
R4_STAGE = ROOT / ".cache/validation/wb55-custom-mode2-transition-safety-r4-execute-20260721-a/stage-run.json"
R4_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r4-disposition-20260721.json"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_custom_mode2_transition_safety/Companion_Nucleo_WB55RG_Ssd1681CustomMode2TransitionSafety.hex"
DUAL_IMAGE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_dual_plane_white_clean/Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean.hex"
DUAL_ELF = DUAL_IMAGE.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-static-20260721.json"

CANDIDATE_SHA = "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564"
DUAL_SHA = "3AC4E52E37E15DC3CC058A4B0B0E6A3227D23E6C6DEFAEDCB786C08497888AAD"
DUAL_ELF_SHA = "1AE76AB804D81E828A2B3AA700821CBD69AF79561CE72E612872F1FAC8550DB0"
SUPPLIER_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
OWNER_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
R4_PRECLEAN_SHA = "AC5AE02315F064759FC3B48A3A5881F50FEB033486B190661FA7595C64B4D87D"
R4_STAGE_SHA = "596F3D250DD4628CAF126D30C6E265F27306D3F98DB162649850523E96BA8474"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ordered(text: str, tokens: tuple[str, ...]) -> bool:
    cursor = -1
    for token in tokens:
        cursor = text.find(token, cursor + 1)
        if cursor < 0:
            return False
    return True


def mutate_block(source: str, start_marker: str, end_marker: str, old: str, new: str) -> str:
    start = source.find(start_marker)
    end = source.find(end_marker, start)
    if start < 0 or end < 0:
        return source
    block = source[start:end]
    return source[:start] + block.replace(old, new, 1) + source[end:]


def dual_source_contract(source: str) -> bool:
    start = source.find("static void ssd1681_dual_plane_white_clean_diagnostic")
    end = source.find("\n#endif", start)
    if start < 0 or end < 0:
        return False
    body = source[start:end]
    read_start = source.find("static bool ssd1681_dual_white_read_ram")
    read_end = source.find("static void ssd1681_dual_plane_white_clean_diagnostic", read_start)
    read_body = source[read_start:read_end]
    return (
        ordered(body, (
            "ssd1681_dual_white_hard_reset();",
            "ssd1681_command(0x12u)",
            "ssd1681_dual_white_set_full_window()",
            "ssd1681_command(0x24u)",
            "ssd1681_data(s_frame, sizeof(s_frame))",
            "ssd1681_command(0x26u)",
            "ssd1681_data(s_frame, sizeof(s_frame))",
            "ssd1681_command_data(0x22u, normal_update",
            "ssd1681_command(0x20u)",
            "ssd1681_wait_refresh_complete",
            "for (uint8_t selector = 0u; selector < 2u; ++selector)",
            "for (uint8_t repeat = 0u; repeat < 2u; ++repeat)",
        ))
        and "memset(s_frame, 0xFF, sizeof(s_frame));" in body
        and "SSD1681_DUAL_WHITE_READ_BYTES (SSD1681_FRAME_BYTES + 1u)" in source
        and "ssd1681_dual_white_set_full_window()" in read_body
        and "ssd1681_command_data(0x41u, &selector, 1u)" in read_body
        and "ssd1681_read_only_register(0x27u" in read_body
        and body.count("ssd1681_dual_white_read_ram(") == 1
        and "selector_reads=4 window_reprograms=4 counter_reprograms=4" in body
    )


def runner_contract(source: str) -> bool:
    preclean = source.find('Operation "preclean-white-write"')
    prompt = source.find("$startDecision = Invoke-CandidateStartPrompt", preclean)
    candidate = source.find('Operation "candidate-write"', prompt)
    postclean = source.find('Operation "postclean-white-write"', candidate)
    restore = source.find('Operation "restore-write-verify-upload"', postclean)
    return (
        0 <= preclean < prompt < candidate < postclean < restore
        and "[switch]$CustomMode2TransitionSafetyDualPlaneClean" in source
        and "[switch]$DualPlaneWhiteRecoveryOnly" in source
        and "$whiteRecoveryOnly = $PostCleanWhiteRecoveryOnly.IsPresent -or $dualPlaneWhiteRecoveryOnly" in source
        and f'$dualPlaneCleanSha256 = "{DUAL_SHA}"' in source
        and f'"{CANDIDATE_SHA}"' in source
        and source.count('Operation "preclean-white-write"') == 1
        and source.count('Operation "candidate-write"') == 1
        and source.count('Operation "postclean-white-write"') == 1
        and source.count('Operation "restore-write-verify-upload"') == 1
        and "supplier_basemap_0x24_0x26_f7_white_readback" in source
        and "preclean = [ordered]@{ required = $customMode2; promptless = $true" in source
        and "postclean = [ordered]@{ required = $customMode2" in source
        and "promptless = $true" in source
        and "candidate is forbidden" in source
        and "if (-not $whiteRecoveryOnly)" in source
        and "if ($customMode2 -and $candidateAttempted)" in source
        and "PASS_MACHINE_CUSTOM_MODE2_DUAL_PLANE_CLEAN_R5_RESTORED" in source
        and "automatic_retries = 0" in source
    )


def supplier_basemap_contract(source: str) -> bool:
    start = source.find("void EPD_SetRAMValue_BaseMap")
    end = source.find("void EPD_Dis_Part", start)
    body = source[start:end]
    return start >= 0 and ordered(body, (
        "Epaper_Write_Command(0x24)",
        "for(i=0;i<ALLSCREEN_GRAGHBYTES;i++)",
        "datas=datas_flag",
        "Epaper_Write_Command(0x26)",
        "for(i=0;i<ALLSCREEN_GRAGHBYTES;i++)",
        "EPD_Update()",
    ))


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    required = [
        DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, DUAL_PARSER, R4_PARSER,
        R4_WORKBENCH_TOOL, RESTORE, NORMAL, REGISTRY, OWNER_ACCEPTANCE,
        RAM_SOURCE, RAM_MACHINE, R4_PRECLEAN, R4_STAGE, R4_DISPOSITION,
        SUPPLIER, BASELINE_A, BASELINE_B, CANDIDATE, DUAL_IMAGE, DUAL_ELF,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"status": "NO_GO_STATIC_R5", "failures": failures}, indent=2) + "\n")
        return 1

    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    supplier = SUPPLIER.read_text(encoding="utf-8", errors="replace")
    ram_source = json.loads(RAM_SOURCE.read_text(encoding="utf-8"))
    ram_machine = json.loads(RAM_MACHINE.read_text(encoding="utf-8"))
    r4_preclean = json.loads(R4_PRECLEAN.read_text(encoding="utf-8"))
    r4_stage = json.loads(R4_STAGE.read_text(encoding="utf-8"))
    r4_disposition = json.loads(R4_DISPOSITION.read_text(encoding="utf-8"))

    hashes = {
        CANDIDATE: CANDIDATE_SHA,
        DUAL_IMAGE: DUAL_SHA,
        DUAL_ELF: DUAL_ELF_SHA,
        SUPPLIER: SUPPLIER_SHA,
        OWNER_ACCEPTANCE: OWNER_SHA,
        BASELINE_A: BASELINE_SHA,
        BASELINE_B: BASELINE_SHA,
        R4_PRECLEAN: R4_PRECLEAN_SHA,
        R4_STAGE: R4_STAGE_SHA,
    }
    for path, expected in hashes.items():
        require(f"hash_{path.name}_{len(checks)}", sha(path) == expected, f"hash mismatch: {path}")

    require("unique_registry_requirement", registry.count("| COMP-REQ-297 |") == 1, "COMP-REQ-297 is missing or non-unique")
    require("supplier_basemap_exact_order", supplier_basemap_contract(supplier), "supplier BaseMap 0x24/0x26/update sequence differs")
    require("dual_source_exact", dual_source_contract(driver), "dual-plane source write/read contract differs")
    require("dual_default_off", "#define COMPANION_EPAPER_SSD1681_DUAL_PLANE_WHITE_CLEAN_DIAGNOSTIC 0" in driver, "dual-plane diagnostic is not default-off")
    require("dual_isolated_build", "EPAPER_SSD1681_DUAL_PLANE_WHITE_CLEAN_DIAGNOSTIC" in makefile and "build_ssd1681_dual_plane_white_clean" in builder and "EpaperSsd1681DualPlaneWhiteCleanDiagnostic" in builder, "isolated dual-plane build missing")
    require("runner_r5_contract", runner_contract(runner), "R5 preclean/prompt/candidate/postclean/restore contract differs")
    require("launcher_contract", all(token in launcher for token in (
        "-CustomMode2TransitionSafetyDualPlaneClean",
        'Start-Process -FilePath "pwsh"',
        "-RedirectStandardOutput $stdout",
        "-RedirectStandardError $stderr",
        "output directory already exists; reuse is forbidden",
        "READY_NO_HARDWARE_CONTACT",
    )), "R5 detached launcher durability or fresh-output contract differs")

    pre_checks = r4_preclean.get("checks", {})
    require("r4_preclean_was_single_plane", pre_checks.get("official_current_plane_only") is True and pre_checks.get("single_data_plane") is True, "R4 preclean was not proven one-plane")
    controller = r4_stage.get("controller_state", {})
    contract = controller.get("contract", {})
    require("r4_candidate_used_both_banks", controller.get("status", "").startswith("PASS_") and contract.get("old_bank") == "0x26" and contract.get("new_bank") == "0x24" and len(controller.get("observed", {}).get("steps", [])) == 9, "R4 nine-transition two-bank evidence differs")
    require("r4_dirty_failure", r4_disposition.get("status", "").startswith("NO_GO_R4_MACHINE_PASS_OPERATOR_FAILED_SCREEN_DIRTY") and r4_disposition.get("operator_review", {}).get("note") == "不太行, 屏幕很杂", "R4 dirty-screen physical failure missing")
    require("reset_ram_retention_fact", ram_source.get("manual_facts", {}).get("software_reset") == "0x12 leaves RAM unaffected, but Deep Sleep is exited only by hardware reset.", "0x12 RAM retention evidence differs")
    fingerprint = ram_machine.get("fingerprint", {})
    require("selector_mapping_proven", ram_machine.get("status") == "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED" and fingerprint.get("unique_mapping") == "activation_swapped_banks_selector0_base_selector1_current" and fingerprint.get("repeat_mismatches") == 0, "selector mapping/repeat evidence differs")

    # Mutation gates prove these failures are not accepted by the static predicates.
    diagnostic_marker = "static void ssd1681_dual_plane_white_clean_diagnostic"
    read_marker = "static bool ssd1681_dual_white_read_ram"
    require("negative_missing_0x26", not dual_source_contract(mutate_block(driver, diagnostic_marker, "\n#endif", "ssd1681_command(0x26u)", "ssd1681_command(0x25u)")), "negative fixture accepted missing 0x26")
    require("negative_missing_dual_read", not dual_source_contract(mutate_block(driver, diagnostic_marker, "\n#endif", "selector < 2u", "selector < 1u")), "negative fixture accepted missing second-bank read")
    require("negative_missing_read_reprogram", not dual_source_contract(mutate_block(driver, read_marker, diagnostic_marker, "!ssd1681_dual_white_set_full_window() ||", "")), "negative fixture accepted missing per-read window/counter setup")
    require("negative_missing_postclean", not runner_contract(runner.replace('Operation "postclean-white-write"', 'Operation "postclean-disabled"', 1)), "negative fixture accepted missing postclean")
    require("negative_cleanup_only_candidate_guard", not runner_contract(runner.replace("if (-not $whiteRecoveryOnly)", "if ($true)", 1)), "negative fixture accepted cleanup-only candidate execution")
    require("negative_candidate_hash_drift", not runner_contract(runner.replace(CANDIDATE_SHA, "0" * 64, 1)), "negative fixture accepted candidate hash drift")
    prompt_token = "$startDecision = Invoke-CandidateStartPrompt"
    prompt_before_preclean = prompt_token + "\n" + runner.replace(prompt_token, "$startDecisionDisabled = Invoke-DisabledPrompt")
    require("negative_prompt_before_preclean", not runner_contract(prompt_before_preclean), "negative fixture accepted prompt/preclean order drift")

    tests: dict[str, str] = {}
    commands = {
        "dual_parser_positive_and_negative": [sys.executable, str(DUAL_PARSER), "--self-test"],
        "r4_parser": [sys.executable, str(R4_PARSER), "--self-test"],
        "r4_workbench": [sys.executable, str(R4_WORKBENCH_TOOL)],
        "restore": [sys.executable, str(RESTORE), "--self-test"],
        "normal": [sys.executable, str(NORMAL), "--self-test"],
    }
    for name, command in commands.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        tests[name] = (proc.stdout + proc.stderr).strip()
        require(f"host_{name}", proc.returncode == 0, f"{name} failed: {tests[name]}")
    for name, path in {"runner": RUNNER, "launcher": LAUNCHER, "builder": BUILDER}.items():
        proc = subprocess.run([
            "pwsh", "-NoProfile", "-Command",
            f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{path}' -Raw)); 'PASS'",
        ], cwd=ROOT, capture_output=True, text=True)
        tests[f"powershell_{name}"] = (proc.stdout + proc.stderr).strip()
        require(f"powershell_{name}", proc.returncode == 0 and "PASS" in proc.stdout, f"PowerShell parse failed: {path}")

    result = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_dual_plane_clean_r5_static.v1",
        "status": "PASS_STATIC_CUSTOM_MODE2_DUAL_PLANE_CLEAN_R5" if not failures else "NO_GO_STATIC_CUSTOM_MODE2_DUAL_PLANE_CLEAN_R5",
        "hardware_contact": 0,
        "requirement": "COMP-REQ-297",
        "checks": checks,
        "failures": failures,
        "hypothesis_boundary": {
            "proven": "R4 preclean wrote only 0x24; R4 candidate activated a two-bank local transition; 0x12 does not clear RAM; selector mapping is machine-proven; R4 physical review reported a dirty screen.",
            "inference": "stale outside-window 0x26 content is a sufficient evidence-backed explanation for R4 whole-screen dirtiness",
            "unproven_until_physical_r5": "dual-plane White pre/post clean causally removes the dirty-screen observation",
        },
        "single_variable": "R4 candidate HEX/LUT/payload/timing/window/tail remain byte-identical; only promptless supplier BaseMap dual-plane White pre/post cleanup replaces one-plane cleanup",
        "images": {"candidate_sha256": sha(CANDIDATE), "dual_plane_clean_sha256": sha(DUAL_IMAGE), "dual_plane_clean_elf_sha256": sha(DUAL_ELF)},
        "host_tests": tests,
        "source_hashes": {str(path): sha(path) for path in (DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, DUAL_PARSER, SUPPLIER, OWNER_ACCEPTANCE)},
        "negative_fixtures": ["missing_0x26", "missing_dual_bank_read", "missing_read_window_counter_reprogram", "one_bank_nonwhite_via_parser_self_test", "missing_postclean", "cleanup_only_candidate_guard_removed", "candidate_hash_drift", "prompt_order_drift"],
        "production_allowed": False,
        "hardware_execute_allowed_after_machine_ready_only": True,
        "human_prompt_boundary": "routine pre/post White cleanup is promptless; only the genuine R5 candidate start and final physical judgment may prompt",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
