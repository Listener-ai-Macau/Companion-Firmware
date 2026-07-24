#!/usr/bin/env python3
"""Static gate for one SSD1681 reset/read capture and exact raw restore."""

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
RESEARCH = ROOT / "docs/validation/companion-ssd1681-reset-read-controller-state-research-source-hash-20260721.json"
PREREQUISITE = ROOT / "docs/validation/companion-ssd1681-reset-read-controller-state-hardware-prerequisite-20260721.json"
PRIOR_MACHINE = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-raw-restore-machine-20260721.json"
PRIOR_COMPLETION = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-raw-restore-completion-audit-20260721.json"
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_reset_read_controller_state/Companion_Nucleo_WB55RG_Ssd1681ResetReadControllerState.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DECODER = ROOT / "app/companion_pendant/epaper/ssd1681_read_only_controller_state.c"
HEADER = ROOT / "app/companion_pendant/epaper/ssd1681_read_only_controller_state.h"
HOST_TEST = ROOT / "tools/test_ssd1681_read_only_controller_state.c"
PARSER = ROOT / "tools/verify_wb55_ssd1681_reset_read_controller_state_log.py"
RESTORE_VERIFIER = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL_VERIFIER = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
BASELINE_VERIFIER = ROOT / "tools/verify_wb55_ur_application_backup.py"
CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
LOCK = ROOT / "tools/companion_wb55_lock.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-reset-read-controller-state-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")
ARM_GCC = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740\tools\bin\arm-none-eabi-gcc.exe")

EXPECTED = {
    RESEARCH: "F703B02FDBCC23C7440BEEF9990127E3ABA22FCCD1368158E599E8B8873B9BFF",
    PREREQUISITE: "04E3DC8A8A57ACE0E312B11C41128499285510A3C04003C4A0C24DFAE895DEDE",
    PRIOR_MACHINE: "27F90202D5D1FA82871AAEDA72F7BEFAA3EEAE4DD4B3095857CEBE2652BDD92C",
    PRIOR_COMPLETION: "C52315DD2B7A6AB18BE68A2F74F17E31DC6650B1E3FCF323F4E66097FC3188C5",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    CANDIDATE: "DB6F1CDBC091A8F4B12AFDB82BBCA62E9C850D57B343E722C4EBE5E05BB7AD7E",
    CANDIDATE_ELF: "26719D1B999D6723A15A254EA4B7C1D45DDF22AD01BB1F146EE9EFEB66A96717",
    DRIVER: "5680AE90E6A3385450756F42B00D265BA9E42602FDC87E81763A2210F32F13FA",
    DECODER: "661AEA992BF152A5A994FF592988535AD59740F05F5DF6FAB16116749B94EDBB",
    HEADER: "8272392B14925E7655891F65E609BE4105EA9DFC69661A208EE4DEFCA7890E97",
    HOST_TEST: "23D1BC4039FAB3A50B823CD3058EDBF1ECFD05732D40831DB826A9D80A4A157C",
    PARSER: "3C0868149A49A45BDA032ADF47B1F459582FD60407F5D3D433FAD5FD99C00300",
    RESTORE_VERIFIER: "22F167723E99F885D92061F5E6BA2DDEC0111E35F3DE7D88FB4A5544F6830733",
    NORMAL_VERIFIER: "27C64C6B59ACEC7C8BA7C0A51BC3D3EBC5A38C03D5D53CC074504A88B1E70A3C",
    BASELINE_VERIFIER: "5CB48DAFFC70073E3BDA290A0252946393939005DE1188936C7EF3FA97F98F32",
    CAPTURE: "59677805F4CA7FBD181C1A19350CE89E957FCCE3F2ACB6682099D585C3789FB1",
    LOCK: "E688A06E6F6BD5DAA8D03A2E342ABF33B525FDA45F97A23AD59A56FF501F73C5",
    RUNNER: "D42DF688263D05D6F5EF90AFE43F5B97984EF16D12F8B2A8B23158D5E7A716B2",
    MAKEFILE: "43F01A86B02E06A95672980252C5ACFDC16CEE84FF354BD7BE21DDD3D2993671",
    BUILDER: "4BEBD2D253DD250D9E7AE553F0C7D09F9D2B964DC354F8FF9CFEAA63CF069510",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}


class CommandError(ValueError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_candidate_args(args: list[str]) -> None:
    if len(args) != 9 or args[:6] != ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w"]:
        raise CommandError("candidate prefix differs from whitelist")
    if Path(args[6]).name != "Companion_Nucleo_WB55RG_Ssd1681ResetReadControllerState.hex":
        raise CommandError("candidate filename differs from locked reset-read image")
    if args[7:] != ["-v", "-rst"] or args.count("-c") != 1 or args.count("-w") != 1 or args.count("-rst") != 1:
        raise CommandError("candidate operation count differs from whitelist")


def validate_restore_args(args: list[str]) -> None:
    if len(args) != 16 or args[:6] != ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w"]:
        raise CommandError("restore prefix differs from whitelist")
    if Path(args[6]).name != "backup-a.bin" or args[7] != "0x08000000":
        raise CommandError("restore source/address differs from baseline")
    if args[8:11] != ["-v", args[6], "0x08000000"]:
        raise CommandError("restore verify differs from write")
    if args[11:14] != ["-u", "0x08000000", "0x80000"] or Path(args[14]).name != "restore-verify.bin" or args[15] != "-rst":
        raise CommandError("restore upload/reset differs from whitelist")
    if ".cache\\validation\\" not in args[14].replace("/", "\\").lower() or "\\private\\" not in args[14].replace("/", "\\").lower():
        raise CommandError("restore upload is not private")
    if any(token in {value.lower() for value in args} for token in ("-rdu", "-e", "-d", "-ob", "-halt", "-run", "-hardrst")):
        raise CommandError("restore contains a forbidden operation")


def self_test() -> None:
    candidate = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w",
                 r"C:\repo\Companion_Nucleo_WB55RG_Ssd1681ResetReadControllerState.hex", "-v", "-rst"]
    restore = ["-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w",
               r"C:\repo\.cache\validation\baseline\private\backup-a.bin", "0x08000000",
               "-v", r"C:\repo\.cache\validation\baseline\private\backup-a.bin", "0x08000000",
               "-u", "0x08000000", "0x80000",
               r"C:\repo\.cache\validation\run\private\restore-verify.bin", "-rst"]
    validate_candidate_args(candidate)
    validate_restore_args(restore)
    bad = [
        (validate_candidate_args, candidate[:-1] + ["-c", "-rst"]),
        (validate_candidate_args, candidate[:6] + ["old.hex"] + candidate[7:]),
        (validate_restore_args, restore[:-1] + ["-rdu", "-rst"]),
        (validate_restore_args, restore[:13] + ["0x80001"] + restore[14:]),
        (validate_restore_args, restore[:14] + [r"C:\repo\docs\restore-verify.bin"] + restore[15:]),
    ]
    for validator, args in bad:
        try:
            validator(args)
        except CommandError:
            continue
        raise AssertionError("negative programmer vector unexpectedly passed")
    print("PASS: SSD1681 reset-read programmer whitelist positive/negative self-test")


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

    required = [REGISTRY, *EXPECTED.keys(), ARM_GCC]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"schema_id": "companion.wb55.ssd1681_reset_read_controller_state_static.v1", "status": "NO_GO_STATIC_RESET_READ_CONTROLLER_STATE", "checks": checks, "failures": failures}, indent=2) + "\n", encoding="utf-8")
        return 1

    registry = REGISTRY.read_text(encoding="utf-8")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    prerequisite = json.loads(PREREQUISITE.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_MACHINE.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")

    require("registry_comp_req_265", "| COMP-REQ-265 |" in registry, "registry lacks COMP-REQ-265")
    require("research_authorizes_exact_single_attempt", research.get("status") == "PASS_RESEARCH_AUTHORIZES_ONE_RESET_READ_CONTROLLER_CAPTURE_AND_RAW_RESTORE" and research.get("candidate_contract", {}).get("hardware_attempts") == 1 and research.get("candidate_contract", {}).get("automatic_retries") == 0, "research artifact does not authorize the exact bounded attempt")
    require("human_wiring_prerequisite", prerequisite.get("status") == "PASS_HUMAN_WIRING_PREREQUISITE_ONLY" and prerequisite.get("owner_chat_confirmation", {}).get("verbatim") == "确认接了", "RES/BUSY human prerequisite is not exact")
    require("prior_all_ff_was_restored", prior.get("status") == "NO_GO_CONTROLLER_READ_RESTORED" and prior.get("restore", {}).get("restore_identity") == "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES", "prior all-FF attempt or exact restore is not preserved")
    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")

    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["shared_sha256"] == EXPECTED[BASELINE_A] and baseline["length_bytes"] == 524288
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("baseline_length_hash_bytes_vector", baseline_ok, "private raw baseline no longer passes admission")

    macro = "COMPANION_EPAPER_SSD1681_RESET_READ_CONTROLLER_STATE_DIAGNOSTIC"
    require("candidate_default_off", f"#define {macro} 0" in driver and f"-D{macro}=1" in makefile, "reset-read candidate is not separately default-off")
    prepare_start = driver.find("static bool ssd1681_reset_read_prepare")
    prepare_end = driver.find("\n#endif", prepare_start)
    diagnostic_start = driver.find("static void ssd1681_read_only_controller_state_diagnostic")
    diagnostic_end = driver.find("\n}\n#endif", diagnostic_start)
    prepare = driver[prepare_start:prepare_end]
    diagnostic = driver[diagnostic_start:diagnostic_end]
    require("one_hard_reset_100_100", prepare_start >= 0 and prepare.count("GPIO_PIN_RESET") == 1 and prepare.count("GPIO_PIN_SET") == 1 and prepare.count("HAL_Delay(100u)") == 2, "candidate does not contain exactly one 100/100 hard reset")
    require("one_bounded_busy_wait", prepare.count("ssd1681_wait_ready(0u, SSD1681_READY_TIMEOUT_MS)") == 1 and "SSD1681_READY_TIMEOUT_MS 5000u" in driver, "candidate BUSY wait is absent or unbounded")
    require("exact_read_commands", diagnostic.count("ssd1681_read_only_register(0x2Fu") == 1 and diagnostic.count("ssd1681_read_only_register(0x2Du") == 1 and "COMP_SSD1681_CONTROLLER_STATE_GROUPS" in diagnostic, "candidate command/group source differs")
    forbidden = ("0x20u", "0x22u", "0x24u", "0x26u", "0x27u", "0x32u", "0x37u", "0x41u")
    require("no_forbidden_command_in_candidate_function", all(token not in diagnostic for token in forbidden), "candidate diagnostic contains a forbidden panel command")
    require("group_end_gpio_contract", all(token in diagnostic for token in ("gpio_restore=%u sda=0 sck=0 cs=1", "ssd1681_read_only_bus_restored")), "group-end GPIO contract is absent")
    require("build_wrapper_isolated", "[switch]$EpaperSsd1681ResetReadControllerStateDiagnostic" in builder and "build_ssd1681_reset_read_controller_state" in builder and "Choose exactly one SSD1681 controller-state diagnostic" in builder, "build wrapper lacks isolated reset-read switch")

    candidate_strings = CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore")
    require("candidate_locked_marker", "[epaper] reset_read_state start" in candidate_strings and "[epaper] readonly_state start" not in candidate_strings, "candidate ELF marker/profile mismatch")
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout, "STM32CubeProgrammer is not v2.22.0")

    require("runner_reset_read_binding", all(token in runner for token in ("[switch]$ResetReadControllerState", "Ssd1681ResetReadControllerState.hex", EXPECTED[CANDIDATE], "verify_wb55_ssd1681_reset_read_controller_state_log.py", "PASS_MACHINE_RESET_READ_CONTROLLER_STATE_RESTORED")), "runner lacks exact reset-read binding")
    require("runner_preflight_before_lock", runner.index("Captured raw baseline hash mismatch") < runner.index('$failureStage = "lock"') and runner.index("& python $staticVerifier") < runner.index('$failureStage = "lock"') and 'status = "READY_NO_HARDWARE_CONTACT"' in runner, "runner does not fail closed before locks/contact")
    require("runner_one_candidate_zero_retry", runner.count('Operation "candidate-write"') == 1 and runner.count("candidate_write_calls = 1") == 1 and "automatic_retries = 0" in runner, "runner candidate attempt/retry count is wrong")
    finally_text = runner[runner.index("} finally {"):]
    require("runner_exact_single_restore", finally_text.count('Operation "restore-write-verify-upload"') == 1 and all(token in finally_text for token in ('"-w", $backupA, "0x08000000"', '"-v", $backupA, "0x08000000"', '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"', "restore_write_calls = 1", "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES")), "runner exact restore contract is incomplete")
    require("runner_invalid_capture_archived", "$controllerParserExit = $LASTEXITCODE" in runner and "Test-Path -LiteralPath $controllerArtifact" in runner and runner.index("Test-Path -LiteralPath $controllerArtifact") < runner.index("if ($controllerParserExit -ne 0)"), "runner does not retain invalid raw controller artifact")
    require("runner_restore_failure_human_only", "NEED_HUMAN_RESTORE_OR_APPLICATION_FAILED" in finally_text and "Invoke-RestoreFailurePrompt" in finally_text, "restore/application uncertainty does not fail to human")

    parser_test = subprocess.run([sys.executable, str(PARSER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    restore_test = subprocess.run([sys.executable, str(RESTORE_VERIFIER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    normal_test = subprocess.run([sys.executable, str(NORMAL_VERIFIER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    whitelist_test = subprocess.run([sys.executable, str(Path(__file__)), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    syntax = subprocess.run([str(ARM_GCC), "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(HEADER.parent), "-fsyntax-only", str(DECODER), str(HOST_TEST)], cwd=ROOT, capture_output=True, text=True)
    ps_parse = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"], cwd=ROOT, capture_output=True, text=True)
    require("controller_parser_negative_matrix", parser_test.returncode == 0, f"controller parser self-test failed: {parser_test.stderr.strip()}")
    require("restore_negative_matrix", restore_test.returncode == 0, f"restore verifier self-test failed: {restore_test.stderr.strip()}")
    require("normal_resume_negative_matrix", normal_test.returncode == 0, f"normal parser self-test failed: {normal_test.stderr.strip()}")
    require("programmer_whitelist_negative_matrix", whitelist_test.returncode == 0, f"programmer whitelist self-test failed: {whitelist_test.stderr.strip()}")
    require("decoder_host_compile_clean", syntax.returncode == 0, f"decoder host syntax failed: {syntax.stderr.strip()}")
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout, f"runner parse failed: {ps_parse.stderr.strip()}")

    tracked = subprocess.run(["git", "ls-files", "docs"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain", "--", "docs"], cwd=ROOT, capture_output=True, text=True)
    raw_names = {"backup-a.bin", "backup-b.bin", "restore-verify.bin"}
    require("no_private_raw_binary_in_docs_git", tracked.returncode == 0 and status.returncode == 0 and not any(Path(line.strip()).name.lower() in raw_names for line in tracked.stdout.splitlines()) and not any(any(name in line.lower() for name in raw_names) for line in status.stdout.splitlines()), "private raw application binary appears in docs/git")

    manifest = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in EXPECTED if path.is_relative_to(ROOT)}
    manifest[str(PROGRAMMER).replace("\\", "/")] = sha(PROGRAMMER)
    result = {
        "schema_id": "companion.wb55.ssd1681_reset_read_controller_state_static.v1",
        "status": "PASS_STATIC_RESET_READ_CONTROLLER_STATE_RAW_RESTORE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_RESET_READ_CONTROLLER_STATE",
        "claim_scope": "Static/host/build proof only; no hardware or controller-value claim.",
        "checks": checks,
        "failures": failures,
        "candidate": {"hex_sha256": sha(CANDIDATE), "elf_sha256": sha(CANDIDATE_ELF)},
        "baseline": {"bytes": 524288, "sha256": EXPECTED[BASELINE_A]},
        "source_manifest": manifest,
        "host_tests": {"controller": parser_test.stdout.strip(), "restore": restore_test.stdout.strip(), "normal": normal_test.stdout.strip(), "programmer_whitelist": whitelist_test.stdout.strip()},
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
