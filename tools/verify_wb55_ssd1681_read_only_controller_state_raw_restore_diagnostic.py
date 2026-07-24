#!/usr/bin/env python3
"""Static gate for one read-only controller capture and exact raw restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from verify_wb55_ur_application_backup import BackupError, validate_pair

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
RESEARCH = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-raw-restore-research-source-hash-20260721.json"
BASELINE_MACHINE = ROOT / "docs/validation/companion-wb55-ur-dual-application-backup-machine-20260721.json"
BASELINE_COMPLETION = ROOT / "docs/validation/companion-wb55-ur-dual-application-backup-completion-audit-20260721.json"
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_read_only_controller_state/Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DECODER = ROOT / "app/companion_pendant/epaper/ssd1681_read_only_controller_state.c"
HEADER = ROOT / "app/companion_pendant/epaper/ssd1681_read_only_controller_state.h"
HOST_TEST = ROOT / "tools/test_ssd1681_read_only_controller_state.c"
CONTROLLER_PARSER = ROOT / "tools/verify_wb55_ssd1681_read_only_controller_state_log.py"
PRIOR_STATIC_VERIFIER = ROOT / "tools/verify_wb55_ssd1681_read_only_controller_state_diagnostic.py"
PRIOR_STATIC = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-static-20260721.json"
BASELINE_VERIFIER = ROOT / "tools/verify_wb55_ur_application_backup.py"
RESTORE_VERIFIER = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL_VERIFIER = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
LOCK = ROOT / "tools/companion_wb55_lock.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-raw-restore-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    RESEARCH: "5AD649AF7D798D79BA6200F81BC190E65595916935E330AD4AD14602B2EE78D5",
    BASELINE_MACHINE: "88C40CA71343933EABCC1BAFDD7227DCDCE6034F98BFCA99DFAC621159A018DD",
    BASELINE_COMPLETION: "18BD912B4CFC49591D9D9866C3FD3010A4F71D5C55AC34C1E098DA252F9A3D62",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    CANDIDATE: "52D79CB3BC55D9738EFA580B95D3930216C23FD8825356F7860B7C1718C0C6AD",
    CANDIDATE_ELF: "2C37D2416EF3EABBECFE08BAC1F5886DFC93D7FFDCC24486F9A8E26E21E5CDB6",
    DRIVER: "BAE2FAEA0656ABBCFAA5765C0E6465183D5E9235E1B4FE50CDB7107BD727EB3D",
    DECODER: "661AEA992BF152A5A994FF592988535AD59740F05F5DF6FAB16116749B94EDBB",
    HEADER: "8272392B14925E7655891F65E609BE4105EA9DFC69661A208EE4DEFCA7890E97",
    HOST_TEST: "23D1BC4039FAB3A50B823CD3058EDBF1ECFD05732D40831DB826A9D80A4A157C",
    CONTROLLER_PARSER: "4D173912345257191370DE703EBFDBB790883922D192CBF1FF3C1A5B7060AB01",
    PRIOR_STATIC_VERIFIER: "F1B855F08D4CF9D89A80C1B5F370509A36EF0969985DB1A5E86F594EAE36333B",
    BASELINE_VERIFIER: "5CB48DAFFC70073E3BDA290A0252946393939005DE1188936C7EF3FA97F98F32",
    NORMAL_VERIFIER: "27C64C6B59ACEC7C8BA7C0A51BC3D3EBC5A38C03D5D53CC074504A88B1E70A3C",
    CAPTURE: "59677805F4CA7FBD181C1A19350CE89E957FCCE3F2ACB6682099D585C3789FB1",
    LOCK: "E688A06E6F6BD5DAA8D03A2E342ABF33B525FDA45F97A23AD59A56FF501F73C5",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}


class CommandError(ValueError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_candidate_args(args: list[str]) -> None:
    expected_prefix = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w"]
    if len(args) != 9 or args[:6] != expected_prefix or args[7:] != ["-v", "-rst"]:
        raise CommandError("candidate argument vector differs from whitelist")
    if Path(args[6]).name != "Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex":
        raise CommandError("candidate filename differs from locked image")
    if args.count("-c") != 1 or args.count("-w") != 1 or args.count("-rst") != 1:
        raise CommandError("candidate connect/write/reset count mismatch")


def validate_restore_args(args: list[str]) -> None:
    if len(args) != 16:
        raise CommandError(f"restore expected 16 arguments, got {len(args)}")
    if args[:6] != ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w"]:
        raise CommandError("restore connection/write prefix differs from whitelist")
    if Path(args[6]).name != "backup-a.bin" or args[7] != "0x08000000":
        raise CommandError("restore write input/address differs from baseline")
    if args[8:11] != ["-v", args[6], "0x08000000"]:
        raise CommandError("restore verify input/address differs from write")
    if args[11:14] != ["-u", "0x08000000", "0x80000"]:
        raise CommandError("post-restore upload range differs from application range")
    if Path(args[14]).name != "restore-verify.bin" or args[15] != "-rst":
        raise CommandError("post-restore private output or final reset differs")
    normalized = args[14].replace("/", "\\").lower()
    if ".cache\\validation\\" not in normalized or "\\private\\" not in normalized:
        raise CommandError("restore upload is not private .cache output")
    if args.count("-c") != 1 or args.count("-w") != 1 or args.count("-v") != 1 or \
            args.count("-u") != 1 or args.count("-rst") != 1:
        raise CommandError("restore connect/write/verify/upload/reset count mismatch")
    forbidden = {"mode=hotplug", "mode=normal", "mode=powerdown", "-rdu", "-e",
                 "-d", "-w8", "-w16", "-w32", "-ob", "-halt", "-run", "-hardrst"}
    hits = sorted(forbidden.intersection(value.lower() for value in args))
    if hits:
        raise CommandError(f"forbidden restore arguments present: {hits}")


def self_test() -> None:
    candidate = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w",
                 r"C:\repo\Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex", "-v", "-rst"]
    restore = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w",
               r"C:\repo\.cache\validation\baseline\private\backup-a.bin", "0x08000000",
               "-v", r"C:\repo\.cache\validation\baseline\private\backup-a.bin", "0x08000000",
               "-u", "0x08000000", "0x80000",
               r"C:\repo\.cache\validation\run\private\restore-verify.bin", "-rst"]
    validate_candidate_args(candidate)
    validate_restore_args(restore)
    cases = {
        "candidate_second_connection": (validate_candidate_args, candidate[:-1] + ["-c", "-rst"]),
        "candidate_second_write": (validate_candidate_args, candidate[:-1] + ["-w", "other.hex", "-rst"]),
        "candidate_wrong_image": (validate_candidate_args, candidate[:6] + ["rebuilt.hex"] + candidate[7:]),
        "restore_second_connection": (validate_restore_args, restore[:-1] + ["-c", "-rst"]),
        "restore_second_write": (validate_restore_args, restore[:-1] + ["-w", "x.bin", "-rst"]),
        "restore_rdu": (validate_restore_args, restore[:-1] + ["-rdu", "-rst"]),
        "restore_wrong_address": (validate_restore_args, restore[:7] + ["0x08080000"] + restore[8:]),
        "restore_wrong_verify": (validate_restore_args, restore[:9] + ["other.bin"] + restore[10:]),
        "restore_wrong_upload_length": (validate_restore_args, restore[:13] + ["0x80001"] + restore[14:]),
        "restore_docs_output": (validate_restore_args, restore[:14] + [r"C:\repo\docs\restore-verify.bin"] + restore[15:]),
    }
    for name, (validator, arguments) in cases.items():
        try:
            validator(arguments)
        except CommandError:
            continue
        raise AssertionError(f"negative programmer fixture unexpectedly passed: {name}")
    print("PASS: WB55 controller candidate/restore command whitelist self-test")


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

    required = [REGISTRY, *EXPECTED.keys(), RESTORE_VERIFIER, RUNNER, PRIOR_STATIC]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({
            "schema_id": "companion.wb55.ssd1681_read_only_controller_state_raw_restore_static.v1",
            "status": "NO_GO_STATIC_CONTROLLER_RAW_RESTORE",
            "checks": checks,
            "failures": failures,
        }, indent=2) + "\n", encoding="utf-8")
        return 1

    registry = REGISTRY.read_text(encoding="utf-8")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    runner = RUNNER.read_text(encoding="utf-8")
    require("registry_comp_req_264", "| COMP-REQ-264 |" in registry,
            "registry lacks COMP-REQ-264")
    require("research_exact_status",
            research.get("status") == "PASS_RESEARCH_AUTHORIZES_ONE_READ_ONLY_CONTROLLER_CAPTURE_AND_RAW_RESTORE",
            "research does not authorize this exact direction")
    for path, expected_hash in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected_hash, f"hash mismatch: {path}")

    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["shared_sha256"] == EXPECTED[BASELINE_A]
    except (BackupError, OSError):
        baseline_ok = False
    require("baseline_length_hash_bytes_vector", baseline_ok,
            "captured raw baseline no longer passes full admission")
    require("candidate_locked_not_rebuilt", sha(CANDIDATE) == EXPECTED[CANDIDATE] and
            "[epaper] readonly_state start" in CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore"),
            "locked candidate identity/marker mismatch")

    prior_run = subprocess.run([sys.executable, str(PRIOR_STATIC_VERIFIER)], cwd=ROOT,
                               capture_output=True, text=True)
    prior = json.loads(PRIOR_STATIC.read_text(encoding="utf-8"))
    prior_false = [name for name, passed in prior.get("checks", {}).items() if not passed]
    require("prior_controller_static_only_e199_file_failure",
            prior_run.returncode == 1 and prior_false == ["normal_restore_hash_exact"] and
            len(prior.get("failures", [])) == 1,
            "prior controller static has a failure beyond the superseded E199 restore file")

    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout,
            "STM32CubeProgrammer version is not 2.22.0")
    require("default_off_preflight_before_locks",
            "$CheckOnly -eq $Execute" in runner and
            runner.index("Captured raw baseline hash mismatch") < runner.index('$failureStage = "lock"') and
            runner.index("& python $staticVerifier") < runner.index('$failureStage = "lock"') and
            'status = "READY_NO_HARDWARE_CONTACT"' in runner,
            "runner does not fail closed before hardware")
    lock_index = runner.index("Enter-CompanionWb55Lock")
    mutex_index = runner.index("Local\\Companion-WB55-SWD-COM-Exclusive-v1")
    candidate_capture_index = runner.index('$candidateCapture = Start-BoundedSerialCapture')
    candidate_args_index = runner.index("$candidateArgs = @(")
    candidate_call_index = runner.index('Operation "candidate-write"')
    require("locks_and_serial_before_candidate",
            lock_index < candidate_capture_index and mutex_index < candidate_capture_index <
            candidate_args_index < candidate_call_index,
            "both locks and candidate serial readiness do not precede candidate write")
    require("candidate_single_process_and_write",
            runner.count('Operation "candidate-write"') == 1 and
            runner.count("candidate_programmer_processes = 1") == 1 and
            runner.count("candidate_write_calls = 1") == 1,
            "candidate is not bounded to one process/write")

    finally_index = runner.index("} finally {")
    restore_text = runner[finally_index:]
    restore_capture_index = restore_text.index('$normalCapture = Start-BoundedSerialCapture')
    restore_args_index = restore_text.index("$restoreArgs = @(")
    restore_call_index = restore_text.index('Operation "restore-write-verify-upload"')
    require("finally_single_restore_after_normal_serial_ready_attempt",
            "$candidateAttempted" in restore_text and
            restore_capture_index < restore_args_index < restore_call_index and
            runner.count('Operation "restore-write-verify-upload"') == 1,
            "finally restore path is not single and ordered")
    require("restore_exact_write_verify_upload_reset",
            all(token in restore_text for token in (
                '"-w", $backupA, "0x08000000"',
                '"-v", $backupA, "0x08000000"',
                '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"',
                "--restore-verify $restoreVerify", "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES")),
            "restore write/verify/upload/reset/byte-compare contract is incomplete")
    require("restore_failure_need_human_no_retry",
            "NEED_HUMAN_RESTORE_OR_APPLICATION_FAILED" in restore_text and
            "Invoke-RestoreFailurePrompt" in restore_text and
            "automatic_retries = 0" in runner and
            runner.count("restore_write_calls = 1") == 1,
            "restore failure escalation or no-retry boundary is incomplete")
    require("normal_capture_bounded_and_parsed",
            "[ValidateRange(10, 30)]" in runner and "$NormalCaptureSeconds = 30" in runner and
            "--log $normalRawLog --out $normalArtifact" in restore_text,
            "post-restore normal capture/parser contract is incomplete")
    require("success_and_invalid_read_statuses",
            "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_RESTORED" in runner and
            "NO_GO_CONTROLLER_READ_RESTORED" in runner,
            "runner does not distinguish valid/invalid read after restore")
    require("zero_panel_and_retry_counters",
            all(token in runner for token in (
                "panel_writes = 0", "panel_refresh_commands = 0",
                "panel_hard_resets = 0", "automatic_retries = 0")),
            "zero panel/retry counters are absent")
    require("no_capture_reset_or_ram_semantics",
            "-ResetAfterOpen" not in runner and "0x41" not in runner and "0x27" not in runner,
            "runner contains capture reset or forbidden RAM semantics")
    require("private_restore_upload",
            'Join-Path $privateRoot "restore-verify.bin"' in runner and
            'Join-Path $runRoot "private"' in runner,
            "restore upload is not private .cache output")

    tracked = subprocess.run(["git", "ls-files", "docs"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain", "--", "docs"], cwd=ROOT,
                            capture_output=True, text=True)
    raw_names = {"backup-a.bin", "backup-b.bin", "restore-verify.bin"}
    bad_tracked = any(Path(line.strip()).name.lower() in raw_names for line in tracked.stdout.splitlines())
    bad_status = any(any(name in line.lower() for name in raw_names) for line in status.stdout.splitlines())
    require("no_raw_bin_in_docs_git", tracked.returncode == 0 and status.returncode == 0 and
            not bad_tracked and not bad_status,
            "raw application binary appears in docs/git")

    controller_test = subprocess.run([sys.executable, str(CONTROLLER_PARSER), "--self-test"],
                                     cwd=ROOT, capture_output=True, text=True)
    restore_test = subprocess.run([sys.executable, str(RESTORE_VERIFIER), "--self-test"],
                                  cwd=ROOT, capture_output=True, text=True)
    normal_test = subprocess.run([sys.executable, str(NORMAL_VERIFIER), "--self-test"],
                                 cwd=ROOT, capture_output=True, text=True)
    whitelist_test = subprocess.run([sys.executable, str(Path(__file__)), "--self-test"],
                                    cwd=ROOT, capture_output=True, text=True)
    require("controller_parser_negative_matrix", controller_test.returncode == 0,
            f"controller parser self-test failed: {controller_test.stderr.strip()}")
    require("restore_negative_matrix", restore_test.returncode == 0,
            f"restore verifier self-test failed: {restore_test.stderr.strip()}")
    require("normal_resume_negative_matrix", normal_test.returncode == 0,
            f"normal parser self-test failed: {normal_test.stderr.strip()}")
    require("programmer_command_negative_matrix", whitelist_test.returncode == 0,
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
        "schema_id": "companion.wb55.ssd1681_read_only_controller_state_raw_restore_static.v1",
        "status": "PASS_STATIC_CONTROLLER_STATE_RAW_RESTORE_DEFAULT_OFF" if not failures
                  else "NO_GO_STATIC_CONTROLLER_RAW_RESTORE",
        "claim_scope": "Static/host proof only; no hardware or controller-value claim.",
        "checks": checks,
        "failures": failures,
        "source_manifest": manifest,
        "host_tests": {
            "controller": controller_test.stdout.strip(),
            "restore": restore_test.stdout.strip(),
            "normal": normal_test.stdout.strip(),
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
