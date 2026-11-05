#!/usr/bin/env python3
"""Static fail-closed gate for one SSD1681 RAM fingerprint and raw restore."""

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
RESEARCH = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-source-hash-20260721.json"
PRIOR_MACHINE = ROOT / "docs/validation/companion-ssd1681-reset-read-controller-state-machine-20260721.json"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
MANUAL = ROOT / ".cache/validation/ssd1681-read-only-research/ssd1681-rev013-2.pdf"
SUPPLIER = ROOT / ".cache/incoming/S-GDEY0154D67-FP-Touch-official-20260720/S-GDEY0154D67-FP-Touch20230303/HARDWARE/EPD/Display_EPD_W21.c"
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_ram_ping_pong_fingerprint_log.py"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
RESTORE_VERIFIER = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL_VERIFIER = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
BASELINE_VERIFIER = ROOT / "tools/verify_wb55_ur_application_backup.py"
CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
LOCK = ROOT / "tools/companion_wb55_lock.ps1"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_ram_ping_pong_fingerprint/Companion_Nucleo_WB55RG_Ssd1681RamPingPongFingerprint.hex"
CANDIDATE_ELF = CANDIDATE.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-static-20260721.json"
PROGRAMMER = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe")

EXPECTED = {
    RESEARCH: "1270787E592283394A8089C3169CCF11DFE506BD9F59CCA81F6D6AF208D94CF6",
    PRIOR_MACHINE: "70D235CC0228C8326438B325A0A145D66AFF9D0D60BA5A38200DD6F3E4666E13",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    MANUAL: "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B",
    SUPPLIER: "CD08AFD1D56E8F7E1D0AE5C935A4D060E65C658ABC30CE29ACF65166141ACEE2",
    BASELINE_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BASELINE_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    DRIVER: "B44B2A68CBD4C039091A7B7A2ED6AC3A599F36744439940CA801DF5BD4F95FC6",
    MAKEFILE: "5BECB5CC47DF9892706E23DEE0FFD0CB864595081C0FF096C27303ABCCC14CAF",
    BUILDER: "17E3AD93EF481F22075CBFD7254522A27D5F94BF88DE6BDC764BFF0C6446335E",
    PARSER: "B53B99C972930F49047B5A11EA8DAAE30CB3DA552D4798DC65084D0ED276B7C2",
    RUNNER: "14FAA3BF43E2564A3039B9081B2549F85F13579F4478DCEF56AA98888CD67C38",
    RESTORE_VERIFIER: "22F167723E99F885D92061F5E6BA2DDEC0111E35F3DE7D88FB4A5544F6830733",
    NORMAL_VERIFIER: "27C64C6B59ACEC7C8BA7C0A51BC3D3EBC5A38C03D5D53CC074504A88B1E70A3C",
    BASELINE_VERIFIER: "5CB48DAFFC70073E3BDA290A0252946393939005DE1188936C7EF3FA97F98F32",
    CAPTURE: "59677805F4CA7FBD181C1A19350CE89E957FCCE3F2ACB6682099D585C3789FB1",
    LOCK: "E688A06E6F6BD5DAA8D03A2E342ABF33B525FDA45F97A23AD59A56FF501F73C5",
    CANDIDATE: "2ED8AEC1B665C4FF516BE603D9C2CCEEAEB6411CFF38B6113283FBEEA7E17B90",
    CANDIDATE_ELF: "76AA2C64F4545ECC3ED5FC17F02EB84CF22C368FDC79C8B62898DB3B6BFD38A7",
    PROGRAMMER: "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = subprocess.run([sys.executable, str(PARSER), "--self-test"], cwd=ROOT)
        return result.returncode

    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    missing = [str(path) for path in [REGISTRY, *EXPECTED.keys()] if not path.is_file()]
    require("required_inputs_exist", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"schema_id": "companion.wb55.ssd1681_ram_ping_pong_fingerprint_static.v1", "status": "NO_GO_STATIC_RAM_FINGERPRINT", "checks": checks, "failures": failures}, indent=2) + "\n", encoding="utf-8")
        return 1

    for path, expected in EXPECTED.items():
        require(f"hash_{path.name}", sha(path) == expected, f"hash mismatch: {path}")

    registry = REGISTRY.read_text(encoding="utf-8")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_MACHINE.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    require("registry_comp_req_266", "| COMP-REQ-266 |" in registry and "那你看一下，继续进行这个修复?" in registry, "registry lacks exact COMP-REQ-266 steering")
    require("research_admission", research.get("status") == "PASS_RESEARCH_ADMITS_ONE_PHASE_A_FINGERPRINT_BUILD_BEFORE_HARDWARE" and research.get("phase_a_design", {}).get("hardware_executes") == 1 and research.get("phase_a_design", {}).get("automatic_retries") == 0, "research does not admit exactly one Phase A attempt")
    require("controller_prerequisite", prior.get("status") == "PASS_MACHINE_RESET_READ_CONTROLLER_STATE_RESTORED" and prior.get("controller_capture", {}).get("decoded", {}).get("f6_mode2_ram_ping_pong_enabled") is True, "F6.6 ping-pong prerequisite is not proven")

    try:
        baseline = validate_pair(BASELINE_A.read_bytes(), BASELINE_B.read_bytes())
        baseline_ok = baseline["length_bytes"] == 524288 and baseline["shared_sha256"] == EXPECTED[BASELINE_A]
    except (BackupError, OSError, KeyError):
        baseline_ok = False
    require("raw_restore_baseline", baseline_ok, "captured raw restore baseline is invalid")

    macro = "COMPANION_EPAPER_SSD1681_RAM_PING_PONG_FINGERPRINT_DIAGNOSTIC"
    require("default_off", f"#define {macro} 0" in driver and f"-D{macro}=1" in makefile, "RAM fingerprint is not default-off and build-gated")
    start = driver.find("static void ssd1681_ram_ping_pong_fingerprint_diagnostic")
    end = driver.find("\n#endif", start)
    diagnostic = driver[start:end]
    read_start = driver.find("static bool ssd1681_fingerprint_read_ram")
    read_end = driver.find("\n}", read_start)
    read_function = driver[read_start:read_end]
    require("diagnostic_function_found", start >= 0 and end > start, "fingerprint function is absent")
    require("exact_basemap_writes", diagnostic.count("ssd1681_command(0x24u)") == 2 and diagnostic.count("ssd1681_command(0x26u)") == 1 and diagnostic.count("sizeof(s_previous_frame)") == 2, "5000-byte 0x24/0x26 basemap or dirty write count differs")
    require("exact_controls_and_activations", diagnostic.count("ssd1681_command(0x20u)") == 2 and "0xF7u" in diagnostic and "0xFFu" in diagnostic and "controls=F7,FF" in diagnostic, "F7/FF activation sequence differs")
    require("busy_and_reset_bounds", diagnostic.count("ssd1681_fingerprint_hard_reset()") == 2 and diagnostic.count("ssd1681_wait_refresh_complete") == 2 and "retries=0" in diagnostic, "reset/BUSY/retry bounds differ")
    require("dirty_region_is_generic_non_art", all(token in driver for token in ("SSD1681_FINGERPRINT_X_START_BYTE 10u", "SSD1681_FINGERPRINT_X_END_BYTE 11u", "SSD1681_FINGERPRINT_Y_START 96u", "SSD1681_FINGERPRINT_Y_END 103u", "^= 0x3Cu")), "deterministic 16-byte non-art dirty region differs")
    require("twelve_reads_and_pointer_reissue", "for (uint8_t selector = 0u; selector < 2u" in driver and "for (uint8_t repeat = 0u; repeat < 2u" in driver and all(token in read_function for token in ("ssd1681_fingerprint_set_window", "0x41u", "0x27u")), "twelve reads or per-read pointer/selector reissue is absent")
    require("response_dummy_contract", "SSD1681_FINGERPRINT_READ_BYTES (SSD1681_FRAME_BYTES + 1u)" in driver and "len=5001" in driver, "5001-byte dummy+payload contract differs")
    require("gpio_restore_contract", all(token in driver for token in ("ssd1681_read_only_restore_bus", "gpio_restore=%u sda=0 sck=0 cs=1")), "GPIO restore contract is absent")
    require("forbidden_waveform_commands_absent", "0x32u" not in diagnostic and "0x37u" not in diagnostic, "fingerprint function contains forbidden waveform commands")
    require("three_stage_markers", all(stage in diagnostic for stage in ("after_basemap_activation", "after_dirty_staging_before_activation", "after_partial_activation")), "three fingerprint stages are incomplete")

    require("isolated_builder_switch", "[switch]$EpaperSsd1681RamPingPongFingerprintDiagnostic" in builder and "build_ssd1681_ram_ping_pong_fingerprint" in builder and "Ssd1681RamPingPongFingerprint" in builder, "builder does not expose one isolated fingerprint target")
    require("candidate_marker", "[epaper] ram_fingerprint start" in CANDIDATE_ELF.read_bytes().decode("latin1", errors="ignore"), "candidate ELF lacks RAM fingerprint marker")
    require("runner_locked_candidate", all(token in runner for token in ("[switch]$RamPingPongFingerprint", EXPECTED[CANDIDATE], "verify_wb55_ssd1681_ram_ping_pong_fingerprint_log.py", "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED")), "runner lacks exact locked fingerprint binding")
    require("runner_preflight_before_contact", runner.index("Captured raw baseline hash mismatch") < runner.index('$failureStage = "lock"') and runner.index("& python $staticVerifier") < runner.index('$failureStage = "lock"') and 'status = "READY_NO_HARDWARE_CONTACT"' in runner, "runner does not fail closed before contact")
    require("runner_one_candidate_zero_retry", runner.count('Operation "candidate-write"') == 1 and runner.count("candidate_write_calls = 1") == 1 and "automatic_retries = 0" in runner, "candidate/retry count differs")
    finally_text = runner[runner.index("} finally {"):]
    require("runner_one_exact_restore", finally_text.count('Operation "restore-write-verify-upload"') == 1 and all(token in finally_text for token in ('"-w", $backupA, "0x08000000"', '"-v", $backupA, "0x08000000"', '"-u", "0x08000000", "0x80000", $restoreVerify, "-rst"', "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES")), "finally restore is not exact and singular")
    require("runner_invalid_mapping_restored", "NO_GO_RAM_MAPPING_RESTORED" in runner and "controllerParserExit" in runner, "invalid mapping does not fail closed after restore")

    parser_test = subprocess.run([sys.executable, str(PARSER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    restore_test = subprocess.run([sys.executable, str(RESTORE_VERIFIER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    normal_test = subprocess.run([sys.executable, str(NORMAL_VERIFIER), "--self-test"], cwd=ROOT, capture_output=True, text=True)
    ps_parse = subprocess.run(["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{RUNNER}' -Raw)); 'PASS'"], cwd=ROOT, capture_output=True, text=True)
    version = subprocess.run([str(PROGRAMMER), "--version"], capture_output=True, text=True)
    require("parser_fixture_matrix", parser_test.returncode == 0, f"parser self-test failed: {parser_test.stderr.strip()}")
    require("restore_fixture_matrix", restore_test.returncode == 0, f"restore self-test failed: {restore_test.stderr.strip()}")
    require("normal_fixture_matrix", normal_test.returncode == 0, f"normal parser self-test failed: {normal_test.stderr.strip()}")
    require("runner_powershell_parse", ps_parse.returncode == 0 and "PASS" in ps_parse.stdout, f"runner parse failed: {ps_parse.stderr.strip()}")
    require("programmer_v2_22", version.returncode == 0 and "version: 2.22.0" in version.stdout, "STM32CubeProgrammer is not v2.22.0")

    tracked = subprocess.run(["git", "ls-files", "docs"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain", "--", "docs"], cwd=ROOT, capture_output=True, text=True)
    raw_names = ("backup-a.bin", "backup-b.bin", "restore-verify.bin")
    require("no_private_raw_in_docs", tracked.returncode == 0 and status.returncode == 0 and not any(name in (tracked.stdout + status.stdout).lower() for name in raw_names), "private raw application bytes appear in docs/git")

    result = {
        "schema_id": "companion.wb55.ssd1681_ram_ping_pong_fingerprint_static.v1",
        "status": "PASS_STATIC_RAM_PING_PONG_FINGERPRINT_RAW_RESTORE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_RAM_FINGERPRINT",
        "claim_scope": "Static/build/host proof only; hardware contact remains forbidden until the runner CheckOnly gate passes.",
        "checks": checks,
        "failures": failures,
        "candidate": {"hex_sha256": sha(CANDIDATE), "elf_sha256": sha(CANDIDATE_ELF)},
        "baseline": {"bytes": 524288, "sha256": EXPECTED[BASELINE_A]},
        "source_manifest": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in EXPECTED if path.is_relative_to(ROOT)},
        "host_tests": {"fingerprint_parser": parser_test.stdout.strip(), "restore": restore_test.stdout.strip(), "normal": normal_test.stdout.strip()},
        "forbidden_claims": ["no hardware result", "no Phase B admission", "no production, LUT, waveform, temperature, voltage, Rig, CRIG, touch, or BLE claim"],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
