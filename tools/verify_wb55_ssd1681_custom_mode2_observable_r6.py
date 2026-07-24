#!/usr/bin/env python3
"""Static fail-closed gate for the production-off R6 observable sequence."""

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
RUNNER = ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_custom_mode2_observable_r6.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_observable_r6_log.py"
WORKBENCH_TOOL = ROOT / "tools/verify_wb55_ssd1681_custom_mode2_observable_r6_workbench.py"
WORKBENCH = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-workbench-20260721.json"
DUAL_PARSER = ROOT / "tools/verify_wb55_ssd1681_dual_plane_white_clean_log.py"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OWNER = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
R5_RUNTIME = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-runtime-20260721.json"
R5_OPERATOR = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-operator-20260721.json"
R5_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-disposition-20260721.json"
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
R5_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_custom_mode2_transition_safety/Companion_Nucleo_WB55RG_Ssd1681CustomMode2TransitionSafety.hex"
R6_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_custom_mode2_observable_r6/Companion_Nucleo_WB55RG_Ssd1681CustomMode2ObservableR6.hex"
R6_ELF = R6_HEX.with_suffix(".elf")
DUAL_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_dual_plane_white_clean/Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean.hex"
DUAL_ELF = DUAL_HEX.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-static-20260721.json"

LUT_SHA = "75D7647188ACF1C79BC37313DC40105AF4445B9B6F422AD4FDAF0A465413984D"
R5_HEX_SHA = "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564"
R6_HEX_SHA = "71933D316D2D6DCDA75DB1C387B012D7B44E9C61244BEEBD4BF7C3DD68047D99"
R6_ELF_SHA = "2D16C29543BCC56788EC892031E31F9114F5D2713D2C30E6E253338E4C434163"
DUAL_HEX_SHA = "3AC4E52E37E15DC3CC058A4B0B0E6A3227D23E6C6DEFAEDCB786C08497888AAD"
DUAL_ELF_SHA = "1AE76AB804D81E828A2B3AA700821CBD69AF79561CE72E612872F1FAC8550DB0"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
SUPPLIER_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
OWNER_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
WORKBENCH_SHA = "3BF58E753767CAC1996EB56CF36F1D630D7D7E6FAAC68D6998352445E4FFE243"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def block(source: str, start: str, end: str) -> str:
    begin = source.find(start)
    finish = source.find(end, begin + len(start))
    return "" if begin < 0 or finish < 0 else source[begin:finish]


def lut_bytes(source: str) -> bytes:
    body = block(source, "static const uint8_t ssd1681_custom_mode2_transition_lut[159] = {", "\n};")
    return bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})", body))


def mutate_r6(source: str, old: str, new: str) -> str:
    marker = "static void ssd1681_custom_mode2_observable_r6_diagnostic"
    start = source.find(marker)
    if start < 0:
        return source
    prefix, suffix = source[:start], source[start:]
    return prefix + suffix.replace(old, new, 1)


def source_contract(source: str) -> bool:
    body = block(source, "static void ssd1681_custom_mode2_observable_r6_diagnostic", "\n#endif")
    loop = block(body, "for (uint8_t step = 0u;", "const uint32_t observation_elapsed_ms")
    expected_previous = "0u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u"
    expected_current = "1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 0u"
    observation_done = body.find("custom_mode2_observable_r6 observation_complete")
    verbose_step = body.find("custom_mode2_observable_r6 step=")
    values = lut_bytes(source)
    return all((
        len(values) == 159,
        hashlib.sha256(values).hexdigest().upper() == LUT_SHA,
        values[153:159].hex().upper() == "221741A83258",
        "#define SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_ACTIVATIONS 16u" in source,
        expected_previous in body,
        expected_current in body,
        "static const uint8_t white[4] = {0xFFu, 0xFFu, 0xFFu, 0xFFu};" in source,
        "static const uint8_t pattern_a[4] = {0x00u, 0x00u, 0xFFu, 0xFFu};" in source,
        "static const uint8_t pattern_b[4] = {0x00u, 0xFFu, 0x00u, 0xFFu};" in source,
        "ssd1681_custom_mode2_write_plane(&window, 0x26u, previous)" in loop,
        "ssd1681_custom_mode2_write_plane(&window, 0x24u, current)" in loop,
        "ssd1681_command_data(0x22u, mode2_display, sizeof(mode2_display))" in loop,
        "ssd1681_command(0x20u)" in loop,
        "ssd1681_wait_refresh_complete(0u, 600u)" in loop,
        "HAL_Delay" not in loop,
        "printf" not in loop,
        observation_done >= 0 and verbose_step > observation_done,
        "countdown=0 dwell_ms=0 compensation_activations=0 verbose_during_observation=0" in body,
        "full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0" in body,
        "hard_resets_after_lut=0 retries=0 motion_120_frame=0" in body,
        "ssd1681_command(0xFFu)" not in body,
        "ssd1681_command(0xF7u)" not in body,
        "ssd1681_command(0xC7u)" not in body,
    ))


def runner_contract(source: str) -> bool:
    preclean = source.find('Operation "preclean-white-write"')
    prompt = source.find("$startDecision = Invoke-CandidateStartPrompt", preclean)
    candidate = source.find('Operation "candidate-write"', prompt)
    postclean = source.find('Operation "postclean-white-write"', candidate)
    restore = source.find('Operation "restore-write-verify-upload"', postclean)
    return all((
        0 <= preclean < prompt < candidate < postclean < restore,
        "[switch]$CustomMode2ObservableR6" in source,
        "$dualPlaneCleanProfile = $dualPlaneCustomMode2 -or $observableR6 -or $dualPlaneWhiteRecoveryOnly" in source,
        "verify_wb55_ssd1681_custom_mode2_observable_r6_log.py" in source,
        "verify_wb55_ssd1681_custom_mode2_observable_r6.py" in source,
        R6_HEX_SHA in source,
        DUAL_HEX_SHA in source,
        "Companion R6 连续局刷观察开始确认" in source,
        "开始并立即看屏幕,取消" in source,
        "点击[开始并立即看屏幕]后" in source,
        "$expectedSelection = if ($observableR6) { \"开始并立即看屏幕\" }" in source,
        "if (($dualPlaneCustomMode2 -or $observableR6) -and -not $whiteRecoveryOnly)" in source,
        "shown_after_machine_verified_preclean = $observableR6" in source,
        source.count('Operation "preclean-white-write"') == 1,
        source.count('Operation "candidate-write"') == 1,
        source.count('Operation "postclean-white-write"') == 1,
        source.count('Operation "restore-write-verify-upload"') == 1,
        "preclean = [ordered]@{ required = $customMode2; promptless = $true" in source,
        "postclean = [ordered]@{ required = $customMode2" in source,
        "automatic_retries = 0" in source,
        "PASS_MACHINE_CUSTOM_MODE2_OBSERVABLE_R6_RESTORED" in source,
    ))


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    required = [DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PARSER, WORKBENCH_TOOL, WORKBENCH,
                DUAL_PARSER, RESTORE, NORMAL, REGISTRY, OWNER, SUPPLIER, R5_RUNTIME, R5_OPERATOR,
                R5_DISPOSITION, BASELINE_A, BASELINE_B, R5_HEX, R6_HEX, R6_ELF, DUAL_HEX, DUAL_ELF]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"status": "NO_GO_STATIC_R6", "failures": failures}, indent=2) + "\n")
        return 1

    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    locked = {
        OWNER: OWNER_SHA, SUPPLIER: SUPPLIER_SHA, R5_RUNTIME: "949F9AC1DE90CD966AC915781A08B33EDA621ED47B8D88110DDCE7A12769F5EC",
        R5_OPERATOR: "868F7854441C628C48BD5534DD2214C02339F410E2DC8067734AFC12BCFC81BF",
        R5_DISPOSITION: "E061343CF42A39BE75552E528D0C2EEB8B0DBA9A8C54964E6924F64D02A0352B",
        BASELINE_A: BASELINE_SHA, BASELINE_B: BASELINE_SHA, R5_HEX: R5_HEX_SHA,
        R6_HEX: R6_HEX_SHA, R6_ELF: R6_ELF_SHA, DUAL_HEX: DUAL_HEX_SHA, DUAL_ELF: DUAL_ELF_SHA,
        WORKBENCH: WORKBENCH_SHA,
    }
    for path, expected in locked.items():
        require(f"hash_{path.name}_{len(checks)}", sha(path) == expected, f"hash drift: {path}")
    require("registry_unique", registry.count("| COMP-REQ-299 |") == 1, "COMP-REQ-299 missing or duplicate")
    require("r6_source", source_contract(driver), "R6 source sequence/LUT/no-dwell/no-extra contract differs")
    require("r6_default_off", "#define COMPANION_EPAPER_SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_DIAGNOSTIC 0" in driver, "R6 not default-off")
    require("r5_constant_preserved", "#define SSD1681_CUSTOM_MODE2_ACTIVATIONS 9u" in driver, "R5 activation constant drifted")
    require("isolated_build", all(token in makefile + builder for token in (
        "EPAPER_SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_DIAGNOSTIC", "EpaperSsd1681CustomMode2ObservableR6Diagnostic",
        "build_ssd1681_custom_mode2_observable_r6", "Companion_Nucleo_WB55RG_Ssd1681CustomMode2ObservableR6")), "isolated R6 build missing")
    require("runner", runner_contract(runner), "R6 preclean/prompt/candidate/postclean/restore contract differs")
    require("launcher", all(token in launcher for token in (
        "run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1", "-CustomMode2ObservableR6",
        'Start-Process -FilePath "pwsh"', "-RedirectStandardOutput $stdout", "-RedirectStandardError $stderr",
        "output directory already exists; reuse is forbidden", "READY_NO_HARDWARE_CONTACT")), "R6 detached launcher differs")

    # Negative mutations prove the source and runner predicates fail closed.
    require("neg_15", not source_contract(driver.replace("SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_ACTIVATIONS 16u", "SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_ACTIVATIONS 15u", 1)), "15 activation mutation accepted")
    require("neg_17", not source_contract(driver.replace("SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_ACTIVATIONS 16u", "SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_ACTIVATIONS 17u", 1)), "17 activation mutation accepted")
    loop_anchor = "ssd1681_custom_mode2_fill_pattern(previous, previous_patterns[step]);"
    require("neg_dwell", not source_contract(mutate_r6(driver, loop_anchor, "HAL_Delay(800u);\n        " + loop_anchor)), "in-loop dwell accepted")
    require("neg_early_uart", not source_contract(mutate_r6(driver, loop_anchor, 'printf("early");\n        ' + loop_anchor)), "in-loop UART accepted")
    require("neg_forbidden_control", not source_contract(mutate_r6(driver, loop_anchor, "ssd1681_command(0xF7u);\n        " + loop_anchor)), "forbidden F7 control accepted")
    require("neg_missing_postclean", not runner_contract(runner.replace('Operation "postclean-white-write"', 'Operation "postclean-disabled"', 1)), "missing postclean accepted")
    prompt_token = "$startDecision = Invoke-CandidateStartPrompt"
    prompt_before = prompt_token + "\n" + runner.replace(prompt_token, "$startDecisionDisabled = Invoke-DisabledPrompt")
    require("neg_prompt_order", not runner_contract(prompt_before), "prompt before preclean accepted")
    require("neg_button", not runner_contract(runner.replace("开始并立即看屏幕,取消", "开始实验,取消", 1)), "non-immediate prompt button accepted")
    require("neg_candidate_hash", not runner_contract(runner.replace(R6_HEX_SHA, "0" * 64, 1)), "R6 image hash drift accepted")

    tests: dict[str, str] = {}
    commands = {
        "r6_parser": [sys.executable, str(PARSER), "--self-test"],
        "r6_workbench": [sys.executable, str(WORKBENCH_TOOL)],
        "dual_parser": [sys.executable, str(DUAL_PARSER), "--self-test"],
        "restore": [sys.executable, str(RESTORE), "--self-test"],
        "normal": [sys.executable, str(NORMAL), "--self-test"],
    }
    for name, command in commands.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        tests[name] = (proc.stdout + proc.stderr).strip()
        require(f"host_{name}", proc.returncode == 0, f"{name} failed: {tests[name]}")
    for name, path in {"runner": RUNNER, "launcher": LAUNCHER, "builder": BUILDER}.items():
        proc = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{path}' -Raw)); 'PASS'"], cwd=ROOT, capture_output=True, text=True)
        tests[f"powershell_{name}"] = (proc.stdout + proc.stderr).strip()
        require(f"powershell_{name}", proc.returncode == 0 and "PASS" in proc.stdout, f"PowerShell parse failed: {path}")

    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_observable_r6_static.v1",
        "status": "PASS_STATIC_CUSTOM_MODE2_OBSERVABLE_R6" if not failures else "NO_GO_STATIC_CUSTOM_MODE2_OBSERVABLE_R6",
        "hardware_contact": 0, "requirement": "COMP-REQ-299", "checks": checks, "failures": failures,
        "single_variable": "R5 TP16 LUT/window/payload/old-new-bank/CF-20-BUSY and dual-clean/restore remain fixed; observation chain alone becomes 16 contiguous activations with no countdown/dwell/early UART",
        "images": {"r5_hex_sha256": sha(R5_HEX), "r6_hex_sha256": sha(R6_HEX), "r6_elf_sha256": sha(R6_ELF), "dual_clean_hex_sha256": sha(DUAL_HEX)},
        "negative_fixtures": ["15", "17", "dwell", "early_uart", "forbidden_control", "missing_postclean", "prompt_order", "old_button", "candidate_hash"],
        "host_tests": tests,
        "source_hashes": {str(path): sha(path) for path in (DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PARSER, WORKBENCH_TOOL, WORKBENCH, SUPPLIER, OWNER)},
        "production_allowed": False,
        "hardware_execute_allowed": False,
        "machine_ready_boundary": "only a later explicit root instruction may start the detached Execute path",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(report["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
