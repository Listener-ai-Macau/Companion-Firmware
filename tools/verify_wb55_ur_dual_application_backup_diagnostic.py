#!/usr/bin/env python3
"""Static and negative gate for one UR dual application-backup run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
RESEARCH = ROOT / "docs/validation/companion-wb55-ur-dual-application-backup-research-source-hash-20260721.json"
PRIOR_MACHINE = ROOT / "docs/validation/companion-wb55-hotplug-backup-controller-state-machine-20260721.json"
PRIOR_COMPLETION = ROOT / "docs/validation/companion-wb55-hotplug-backup-controller-state-completion-audit-20260721.json"
FLASH_RUNNER = ROOT / "tools/flash_nucleo_bringup.ps1"
CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
LOCK = ROOT / "tools/companion_wb55_lock.ps1"
BACKUP_VERIFIER = ROOT / "tools/verify_wb55_ur_application_backup.py"
RESUME_VERIFIER = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
RUNNER = ROOT / "tools/run_wb55_ur_dual_application_backup.ps1"
LINKER = ROOT / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/STM32WB55RGVX_FLASH.ld"
PRIOR_RESTORE = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-completion-audit-20260721.json"
PRIOR_RESTORE_STDOUT = ROOT / ".cache/validation/flash-nucleo/stm32-programmer-20260721-115950-29716.stdout.log"
NORMAL_REFERENCE = ROOT / "docs/validation/companion-screen-normal-restore-after-black-20260714.raw.log"
OUT = ROOT / "docs/validation/companion-wb55-ur-dual-application-backup-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    RESEARCH: "CD997124E365D0D15C9557C51FEAC19B3FA9C15632B934BDFE435019E32C750F",
    PRIOR_MACHINE: "1A830C5F0F574E9B6A85534A56298E32DD58243340E219D00C3EEA4513746A32",
    PRIOR_COMPLETION: "CD35A3C379197EADD4B5C99FAAD93A32D755999C0574851DD0E6C4AE938909DD",
    FLASH_RUNNER: "1FEFF712B6CA1DADC328C50FAD7CBB7B297E627585BFD4288EAF49108BB35D56",
    LINKER: "4FB899EAB4A324B5CB642D37884341577413634710B4B301B59B21493BE0E4BD",
    PRIOR_RESTORE: "0E3643391446640D0D9A2A9B2E050D41A14D4BBB0D32785D814B4E57D98D2CF4",
    PRIOR_RESTORE_STDOUT: "E7738539B9EE71721A45A54B61350BA98FA776753E3CDB4ECD8DD2CFA8106977",
    NORMAL_REFERENCE: "3AE5B0DD29CA1A6785C5D986C0D91C9C80EDA9916A279B8EAF064B34486BF405",
    CAPTURE: "59677805F4CA7FBD181C1A19350CE89E957FCCE3F2ACB6682099D585C3789FB1",
    LOCK: "E688A06E6F6BD5DAA8D03A2E342ABF33B525FDA45F97A23AD59A56FF501F73C5",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}


class CommandError(ValueError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_programmer_args(args: list[str]) -> None:
    if len(args) != 14:
        raise CommandError(f"expected 14 arguments, got {len(args)}")
    if args[:8] != ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                   "-u", "0x08000000", "0x80000"]:
        raise CommandError("connection or first upload prefix differs from whitelist")
    if args[9:13] != ["-u", "0x08000000", "0x80000", args[12]]:
        raise CommandError("second upload differs from whitelist")
    if Path(args[8]).name != "backup-a.bin" or Path(args[12]).name != "backup-b.bin":
        raise CommandError("private backup filenames are not exact")
    if args[8] == args[12]:
        raise CommandError("backup paths are not independent")
    normalized = [value.replace("/", "\\").lower() for value in (args[8], args[12])]
    if not all(".cache\\validation\\" in value and "\\private\\" in value for value in normalized):
        raise CommandError("backup files are not private .cache validation outputs")
    if args[13] != "-rst":
        raise CommandError("sole final reset argument is missing")
    if args.count("-c") != 1 or args.count("-u") != 2 or args.count("-rst") != 1:
        raise CommandError("connection/upload/reset count mismatch")
    forbidden = {"mode=hotplug", "mode=normal", "mode=powerdown", "-rdu", "-e", "-w",
                 "-d", "-w8", "-w16", "-w32", "-ob", "-halt", "-run", "-hardrst",
                 "-otp", "-firmwaredelete", "-firmwareupgrade", "-startfus"}
    hits = sorted(forbidden.intersection(value.lower() for value in args))
    if hits:
        raise CommandError(f"forbidden arguments present: {hits}")


def self_test() -> None:
    base = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
            "-u", "0x08000000", "0x80000", r"C:\repo\.cache\validation\run\private\backup-a.bin",
            "-u", "0x08000000", "0x80000", r"C:\repo\.cache\validation\run\private\backup-b.bin", "-rst"]
    validate_programmer_args(base)
    cases = {
        "second_connection": base[:-1] + ["-c", "port=SWD", "-rst"],
        "second_reset": base + ["-rst"],
        "hotplug": base[:2] + ["mode=HOTPLUG"] + base[3:],
        "normal": base[:2] + ["mode=NORMAL"] + base[3:],
        "write": base[:-1] + ["-w", "image.hex", "-rst"],
        "read_unprotect": base[:-1] + ["-rdu", "-rst"],
        "option_byte": base[:-1] + ["-ob", "displ", "-rst"],
        "above_application": base[:11] + ["0x08080000"] + base[12:],
        "one_upload": base[:9] + ["-rst"],
        "three_uploads": base[:-1] + ["-u", "0x08000000", "0x80000", "third.bin", "-rst"],
        "docs_backup": base[:8] + [r"C:\repo\docs\backup-a.bin"] + base[9:],
    }
    for name, case in cases.items():
        try:
            validate_programmer_args(case)
        except CommandError:
            continue
        raise AssertionError(f"negative command fixture unexpectedly passed: {name}")
    print("PASS: WB55 UR programmer whitelist positive/negative self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    required = [REGISTRY, *EXPECTED.keys(), BACKUP_VERIFIER, RESUME_VERIFIER, RUNNER]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({
            "schema_id": "companion.wb55.ur_dual_application_backup_static.v1",
            "status": "NO_GO_STATIC_UR_DUAL_APPLICATION_BACKUP",
            "checks": checks,
            "failures": failures,
        }, indent=2) + "\n", encoding="utf-8")
        return 1

    registry = REGISTRY.read_text(encoding="utf-8")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    runner = RUNNER.read_text(encoding="utf-8")
    flash_runner = FLASH_RUNNER.read_text(encoding="utf-8")
    linker = LINKER.read_text(encoding="utf-8")
    prior_machine = json.loads(PRIOR_MACHINE.read_text(encoding="utf-8"))
    prior_restore_text = PRIOR_RESTORE_STDOUT.read_text(encoding="utf-8", errors="replace")
    normal_reference = NORMAL_REFERENCE.read_text(encoding="utf-8", errors="replace")

    require("registry_comp_req_260", "| COMP-REQ-260 |" in registry,
            "registry lacks COMP-REQ-260")
    require("research_exact_status",
            research.get("status") == "PASS_RESEARCH_AUTHORIZES_ONE_UR_DUAL_APPLICATION_BACKUP_ZERO_WRITES",
            "research does not authorize this exact bounded direction")
    for path, expected_hash in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected_hash,
                f"hash mismatch: {path}")
    require("prior_hotplug_durable_no_go",
            prior_machine.get("status") == "NO_GO_DUAL_BACKUP_ZERO_WRITES" and
            prior_machine.get("counters", {}).get("candidate_write_calls") == 0,
            "COMP-REQ-259 durable zero-write NO_GO is not intact")

    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    help_run = subprocess.run([str(PROGRAMMER), "--help"], capture_output=True, text=True)
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout,
            "STM32CubeProgrammer version is not 2.22.0")
    require("local_help_ur_upload_reset", help_run.returncode == 0 and
            "mode. Value in {UR/HOTPLUG/NORMAL/POWERDOWN/HWRSTPULSE}" in help_run.stdout and
            "Reset mode with UR connection mode is HWrst" in help_run.stdout and
            "--upload" in help_run.stdout and "Upload the device memory content" in help_run.stdout and
            "-rst" in help_run.stdout and "Reset system" in help_run.stdout,
            "local programmer help lacks UR/HWrst/upload/reset semantics")
    require("existing_runner_exact_ur_connection",
            '@("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000"' in flash_runner,
            "existing flash runner does not retain the proven UR connection")
    require("linker_exact_application_range",
            "FLASH (rx)                 : ORIGIN = 0x08000000, LENGTH = 512K" in linker,
            "linker application range is not exact")
    require("prior_restore_connected_same_board",
            all(token in prior_restore_text for token in (
                "ST-LINK SN  : 066EFF535570514867221931", "Voltage     : 3.24V",
                "Connect mode: Under Reset", "Reset mode  : Hardware reset",
                "Device ID   : 0x495", "Device name : STM32WB5x/35xx",
                "Download verified successfully")),
            "prior same-board UR restore evidence is incomplete")
    require("normal_reference_markers",
            "[boot] Companion NUCLEO-WB55RG bringup" in normal_reference and
            "[boot] boot_selftests=skipped reason=production_ble_path" in normal_reference,
            "normal boot identity/ready reference is incomplete")

    require("default_off_and_static_before_hardware",
            "$CheckOnly -eq $Execute" in runner and
            runner.index("& python $staticVerifier") < runner.index('$failureStage = "lock"') and
            'status = "READY_NO_HARDWARE_CONTACT"' in runner,
            "runner default-off or static-before-hardware contract is missing")
    lock_index = runner.index("Enter-CompanionWb55Lock")
    mutex_index = runner.index("Local\\Companion-WB55-SWD-COM-Exclusive-v1")
    capture_index = runner.index('$captureProcess = Start-Process -FilePath "pwsh"')
    args_index = runner.index("$programmerArgs = @(")
    call_index = runner.index("Invoke-SoleProgrammerProcess -Programmer")
    require("dual_locks_before_serial_and_programmer",
            lock_index < capture_index and mutex_index < capture_index < args_index < call_index,
            "both locks and serial-open order are not before programmer")
    require("serial_ready_before_programmer_no_capture_reset",
            runner.index("Test-Path -LiteralPath $serialReady") < args_index and
            "ReadySignalPath" in runner and "-ResetAfterOpen" not in runner,
            "serial ready ordering or no-capture-reset boundary is absent")
    expected_literal = ('@("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",\n'
                        '                        "-u", "0x08000000", "0x80000", $backupA,\n'
                        '                        "-u", "0x08000000", "0x80000", $backupB, "-rst")')
    require("exact_literal_programmer_whitelist", expected_literal in runner,
            "runner programmer argument vector differs from exact whitelist")
    require("one_programmer_process_call",
            runner.count("Invoke-SoleProgrammerProcess -Programmer") == 1 and
            runner.count('$process = Start-Process -FilePath $Programmer') == 1,
            "runner does not statically bound programmer to one process/call")
    require("counter_contract_zero_write",
            all(token in runner for token in (
                "programmer_connection_processes = 1", "under_reset_connections = 1",
                "upload_arguments = 2", "explicit_reset_arguments = 1",
                "application_write_commands = 0", "erase_commands = 0",
                "panel_commands = 0", "automatic_retries = 0")),
            "runner counters do not prove 1 connect / 2 upload / 1 reset / 0 write")
    require("private_cache_outputs",
            'Join-Path $runRoot "private"' in runner and
            'Join-Path $privateRoot "backup-a.bin"' in runner and
            'Join-Path $privateRoot "backup-b.bin"' in runner,
            "backup binaries are not private run outputs")
    require("normal_resume_timeout_and_need_human",
            "[ValidateRange(10, 30)]" in runner and "$CaptureSeconds = 30" in runner and
            "NEED_HUMAN_APPLICATION_RESUME_UNPROVEN" in runner and
            "Invoke-ResumeFailurePrompt" in runner,
            "bounded normal resume / human escalation contract is incomplete")

    args_fixture = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                    "-u", "0x08000000", "0x80000", r"C:\repo\.cache\validation\run\private\backup-a.bin",
                    "-u", "0x08000000", "0x80000", r"C:\repo\.cache\validation\run\private\backup-b.bin", "-rst"]
    try:
        validate_programmer_args(args_fixture)
        whitelist_ok = True
    except CommandError:
        whitelist_ok = False
    require("programmer_whitelist_parser", whitelist_ok,
            "internal exact programmer whitelist parser rejected positive vector")

    tracked = subprocess.run(["git", "ls-files", "docs"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain", "--", "docs"], cwd=ROOT,
                            capture_output=True, text=True)
    backup_bin_in_git = any(Path(line.strip()).name.lower() in {"backup-a.bin", "backup-b.bin"}
                            for line in tracked.stdout.splitlines())
    backup_bin_in_status = any("backup-a.bin" in line.lower() or "backup-b.bin" in line.lower()
                               for line in status.stdout.splitlines())
    require("no_backup_bin_in_docs_git", tracked.returncode == 0 and status.returncode == 0 and
            not backup_bin_in_git and not backup_bin_in_status,
            "a raw backup binary appears in docs/git")

    panel_tokens = ["0x20", "0x22", "0x24", "0x26", "0x32", "0x37", "panel_spi"]
    require("runner_has_no_panel_command_surface",
            not any(token.lower() in runner.lower() for token in panel_tokens),
            "runner exposes a forbidden panel command surface")
    require("runner_has_no_candidate_or_controller_read",
            "candidate" not in runner.lower() and "0x2d" not in runner.lower() and
            "0x2f" not in runner.lower(),
            "runner contains candidate/controller read behavior")

    backup_test = subprocess.run([sys.executable, str(BACKUP_VERIFIER), "--self-test"],
                                 cwd=ROOT, capture_output=True, text=True)
    resume_test = subprocess.run([sys.executable, str(RESUME_VERIFIER), "--self-test"],
                                 cwd=ROOT, capture_output=True, text=True)
    whitelist_test = subprocess.run([sys.executable, str(Path(__file__)), "--self-test"],
                                    cwd=ROOT, capture_output=True, text=True)
    require("backup_negative_matrix", backup_test.returncode == 0,
            f"backup verifier self-test failed: {backup_test.stderr.strip()}")
    require("normal_resume_negative_matrix", resume_test.returncode == 0,
            f"normal resume parser self-test failed: {resume_test.stderr.strip()}")
    require("programmer_whitelist_negative_matrix", whitelist_test.returncode == 0,
            f"programmer whitelist self-test failed: {whitelist_test.stderr.strip()}")
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
        "schema_id": "companion.wb55.ur_dual_application_backup_static.v1",
        "status": "PASS_STATIC_UR_DUAL_APPLICATION_BACKUP_DEFAULT_OFF" if not failures
                  else "NO_GO_STATIC_UR_DUAL_APPLICATION_BACKUP",
        "claim_scope": "Static/host proof only; no hardware contact or application-byte claim.",
        "checks": checks,
        "failures": failures,
        "source_manifest": manifest,
        "host_tests": {
            "backup": backup_test.stdout.strip(),
            "normal_resume": resume_test.stdout.strip(),
            "programmer_whitelist": whitelist_test.stdout.strip(),
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
