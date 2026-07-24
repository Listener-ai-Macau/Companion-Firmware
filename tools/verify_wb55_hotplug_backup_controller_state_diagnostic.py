#!/usr/bin/env python3
"""Static gate for dual HOTPLUG backup, controller read and one restore."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
RESEARCH = ROOT / "docs/validation/companion-wb55-hotplug-application-backup-controller-state-research-source-hash-20260721.json"
PRIOR_STATIC = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-static-20260721.json"
PRIOR_STATIC_VERIFIER = ROOT / "tools/verify_wb55_ssd1681_read_only_controller_state_diagnostic.py"
BACKUP_VERIFIER = ROOT / "tools/verify_wb55_hotplug_application_backup.py"
LOG_VERIFIER = ROOT / "tools/verify_wb55_ssd1681_read_only_controller_state_log.py"
RUNNER = ROOT / "tools/run_wb55_hotplug_backup_controller_state.ps1"
CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
LOCK = ROOT / "tools/companion_wb55_lock.ps1"
LINKER = ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/STM32WB55RGVX_FLASH.ld"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_read_only_controller_state/Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-wb55-hotplug-backup-controller-state-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")
EXPECTED_PROGRAMMER_SHA = "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E"
EXPECTED_CANDIDATE_SHA = "52D79CB3BC55D9738EFA580B95D3930216C23FD8825356F7860B7C1718C0C6AD"
EXPECTED_LINKER_SHA = "4FB899EAB4A324B5CB642D37884341577413634710B4B301B59B21493BE0E4BD"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}
    required = [REGISTRY, RESEARCH, PRIOR_STATIC, PRIOR_STATIC_VERIFIER, BACKUP_VERIFIER,
                LOG_VERIFIER, RUNNER, CAPTURE, LOCK, LINKER, CANDIDATE, CANDIDATE_ELF, PROGRAMMER]

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"schema_id": "companion.wb55.hotplug_backup_controller_state_static.v1",
                                   "status": "NO_GO_STATIC_HOTPLUG_BACKUP_CONTROLLER_STATE",
                                   "checks": checks, "failures": failures}, indent=2) + "\n", encoding="utf-8")
        return 1

    registry = REGISTRY.read_text(encoding="utf-8")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    runner = RUNNER.read_text(encoding="utf-8")
    capture = CAPTURE.read_text(encoding="utf-8")
    linker = LINKER.read_text(encoding="utf-8")
    require("registry_comp_req_259", "| COMP-REQ-259 |" in registry,
            "registry lacks unique COMP-REQ-259 recovery contract")
    require("research_exact_status",
            research.get("status") == "PASS_RESEARCH_AUTHORIZES_DUAL_HOTPLUG_APPLICATION_BACKUP_THEN_ONE_READ_ONLY_CONTROLLER_CAPTURE",
            "recovery research does not authorize this exact bounded path")
    require("programmer_hash_exact", sha(PROGRAMMER) == EXPECTED_PROGRAMMER_SHA,
            "STM32CubeProgrammer executable hash mismatch")
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    help_run = subprocess.run([str(PROGRAMMER), "--help"], capture_output=True, text=True)
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout,
            "STM32CubeProgrammer version is not 2.22.0")
    require("programmer_local_help_upload_hotplug",
            help_run.returncode == 0 and "mode. Value in {UR/HOTPLUG/NORMAL/POWERDOWN/HWRSTPULSE}" in help_run.stdout
            and "--upload" in help_run.stdout and "Upload the device memory content" in help_run.stdout,
            "local programmer help lacks HOTPLUG/upload semantics")
    require("linker_hash_and_exact_application_range",
            sha(LINKER) == EXPECTED_LINKER_SHA and
            "FLASH (rx)                 : ORIGIN = 0x08000000, LENGTH = 512K" in linker,
            "linker identity or 512K application range mismatch")
    require("candidate_hash_exact", sha(CANDIDATE) == EXPECTED_CANDIDATE_SHA,
            "candidate HEX is not the locked 52D79C... image")
    elf_text = CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore")
    require("candidate_is_read_only_profile", "[epaper] readonly_state start" in elf_text,
            "candidate ELF lacks read-only diagnostic marker")

    prior_run = subprocess.run([sys.executable, str(PRIOR_STATIC_VERIFIER)], cwd=ROOT,
                               capture_output=True, text=True)
    prior = json.loads(PRIOR_STATIC.read_text(encoding="utf-8"))
    prior_false = [name for name, passed in prior.get("checks", {}).items() if not passed]
    require("prior_diagnostic_static_only_lost_hex_failure",
            prior_run.returncode == 1 and prior_false == ["normal_restore_hash_exact"] and
            len(prior.get("failures", [])) == 1,
            "prior read-only static contract has a failure beyond the superseded lost-HEX restore gate")

    require("dual_locks_before_hardware", all(token in runner for token in (
                "Enter-CompanionWb55Lock",
                "Local\\Companion-WB55-SWD-COM-Exclusive-v1",
                "$failureStage = \"dual_backup\"")),
            "runner lacks both locks before dual backup")
    dual_start = runner.index('$failureStage = "dual_backup"')
    serial_start = runner.index('$failureStage = "serial_ready"')
    pre_backup = runner[dual_start:serial_start]
    require("exact_two_hotplug_backup_upload_calls",
            pre_backup.count('mode=HOTPLUG') == 2 and
            pre_backup.count('"-u", "0x08000000", "0x80000"') == 2 and
            pre_backup.count("Invoke-ProgrammerOnce") == 2,
            "pre-write backup stage is not exactly two HOTPLUG 0x80000 uploads")
    forbidden_prewrite = ["-rdu", '"-e"', '"-w"', '"-w8"', '"-w16"', '"-w32"',
                          '"-ob"', '"-rst"', "-hardRst", "mode=UR", "reset=HWrst",
                          '"halt"', '"run"']
    require("zero_write_reset_halt_before_backup_admission",
            not any(token in pre_backup for token in forbidden_prewrite),
            "forbidden write/reset/halt/run token appears before backup admission")
    require("backup_gate_before_serial_and_candidate",
            runner.index("--backup-a $backupA --backup-b $backupB --out $backupArtifact") < serial_start <
            runner.index("$candidateAttempted = $true"),
            "backup validation does not precede serial ready and candidate admission")
    require("serial_ready_before_candidate_write_no_reset_after_open",
            runner.index("Test-Path -LiteralPath $serialReady") < runner.index("$candidateAttempted = $true") and
            "-ResetAfterOpen" not in runner and "ReadySignalPath" in capture,
            "serial-ready ordering or single-boot contract is absent")
    require("single_candidate_and_single_restore_write",
            runner.count("$report.counters.candidate_write_calls = 1") == 1 and
            runner.count("$report.counters.restore_write_calls = 1") == 1 and
            runner.count('Operation "candidate-write"') == 1 and
            runner.count('Operation "restore-write"') == 1,
            "runner does not statically bound candidate and restore to one call each")
    finally_start = runner.index("} finally {")
    restore_block = runner[finally_start:]
    require("finally_restore_and_post_restore_hotplug_compare", all(token in restore_block for token in (
                "$candidateAttempted",
                '"-w", $backupA, "0x08000000"',
                '"-v", $backupA, "0x08000000"',
                '"mode=HOTPLUG", "-u", "0x08000000", "0x80000", $restoreVerify',
                "--restore-verify $restoreVerify",
                "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES")),
            "finally restore/verify/upload/compare contract incomplete")
    require("restore_failure_popup_and_no_second_write", all(token in restore_block for token in (
                "NEED_HUMAN_RESTORE_FAILED", "Invoke-RestoreFailurePrompt")) and
            runner.count('Operation "restore-write"') == 1,
            "restore failure does not escalate without a second write")
    require("private_cache_only", 'Join-Path $runRoot "private"' in runner and
            "docs\\validation" not in runner,
            "raw backup path is not private .cache run output")

    backup_test = subprocess.run([sys.executable, str(BACKUP_VERIFIER), "--self-test"],
                                 cwd=ROOT, capture_output=True, text=True)
    log_test = subprocess.run([sys.executable, str(LOG_VERIFIER), "--self-test"],
                              cwd=ROOT, capture_output=True, text=True)
    require("backup_negative_matrix", backup_test.returncode == 0,
            f"backup verifier self-test failed: {backup_test.stderr.strip()}")
    require("controller_log_negative_matrix", log_test.returncode == 0,
            f"controller parser self-test failed: {log_test.stderr.strip()}")
    ps_parse = subprocess.run([
        "pwsh", "-NoProfile", "-Command",
        f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"
    ], cwd=ROOT, capture_output=True, text=True)
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout,
            f"runner PowerShell parse failed: {ps_parse.stderr.strip()}")

    manifest = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                for path in required if path.is_relative_to(ROOT)}
    manifest[str(PROGRAMMER).replace("\\", "/")] = sha(PROGRAMMER)
    result = {
        "schema_id": "companion.wb55.hotplug_backup_controller_state_static.v1",
        "status": "PASS_STATIC_HOTPLUG_BACKUP_CONTROLLER_STATE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_HOTPLUG_BACKUP_CONTROLLER_STATE",
        "claim_scope": "machine-only zero-prewrite dual backup gate, one candidate, one restore and post-restore compare; no hardware result",
        "checks": checks,
        "failures": failures,
        "source_manifest": manifest,
        "candidate_hex_sha256": sha(CANDIDATE),
        "programmer_sha256": sha(PROGRAMMER),
        "host_tests": {
            "backup": backup_test.stdout.strip(),
            "controller_log": log_test.stdout.strip(),
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
