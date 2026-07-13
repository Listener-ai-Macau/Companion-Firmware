#!/usr/bin/env python3
"""Verify the WB55 active-resource serial-capture path without touching hardware."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE = current_candidate()
CAPTURE_SCRIPT = ROOT / "tools/capture_nucleo_serial.ps1"
RUNNER_SCRIPT = ROOT / "tools/run_wb55_screen_runtime_recheck.ps1"
RUN_REPORT = CANDIDATE.run_root / "runtime-recheck-run.json"
LOG_VERIFIER = ROOT / "tools/verify_wb55_screen_runtime_recheck_logs.py"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json"
EMPTY_SELFTEST_DIR = ROOT / ".cache/validation/nucleo-serial-empty-selftest"
EMPTY_SELFTEST_SUMMARY = EMPTY_SELFTEST_DIR / "nucleo-serial-summary.json"
EMPTY_SELFTEST_RAW = EMPTY_SELFTEST_DIR / "nucleo-serial-raw.log"
RESET_TIMEOUT_SELFTEST_DIR = ROOT / ".cache/validation/nucleo-serial-reset-timeout-selftest"
RESET_TIMEOUT_SELFTEST_SUMMARY = RESET_TIMEOUT_SELFTEST_DIR / "nucleo-serial-summary.json"
RESET_TIMEOUT_STDOUT = RESET_TIMEOUT_SELFTEST_DIR / "stm32-reset-stdout.log"
RESET_TIMEOUT_STDERR = RESET_TIMEOUT_SELFTEST_DIR / "stm32-reset-stderr.log"
SCHEMA_ID = "companion.screen.wb55_runtime_serial_capture_preflight.v1"
STATUS = "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT"
EXPECTED_STEPS = ["flash_provision", "capture_provision", "flash_normal", "capture_normal"]


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def has_all(text: str, tokens: list[str]) -> dict[str, bool]:
    return {token: token in text for token in tokens}


def command_line(step: dict[str, Any]) -> str:
    return " ".join([str(step.get("command", "")), *[str(arg) for arg in step.get("arguments", [])]])


def run_empty_capture_selftest() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(CAPTURE_SCRIPT),
            "-SelfTestEmptyCapture",
            "-OutDir",
            str(EMPTY_SELFTEST_DIR),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    summary = load_json(EMPTY_SELFTEST_SUMMARY) if EMPTY_SELFTEST_SUMMARY.exists() else {}
    return {
        "command": "pwsh -NoProfile -File .\\tools\\capture_nucleo_serial.ps1 -SelfTestEmptyCapture -OutDir .\\.cache\\validation\\nucleo-serial-empty-selftest",
        "returncode": completed.returncode,
        "stdout_has_expected_failure": "empty-log self-test failed as expected" in (completed.stdout + completed.stderr),
        "summary_path": rel(EMPTY_SELFTEST_SUMMARY),
        "summary_exists": EMPTY_SELFTEST_SUMMARY.exists(),
        "raw_log_path": rel(EMPTY_SELFTEST_RAW),
        "raw_log_exists": EMPTY_SELFTEST_RAW.exists(),
        "summary_status": summary.get("status"),
        "summary_mode": summary.get("mode"),
        "summary_port": summary.get("port"),
        "bytes_read": summary.get("bytes_read"),
        "reset_timeout_seconds": summary.get("reset_timeout_seconds"),
        "errors": summary.get("errors", []),
        "claim_scope": "stubbed_empty_capture_no_hardware_claim",
    }


def run_reset_timeout_selftest() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(CAPTURE_SCRIPT),
            "-SelfTestResetTimeout",
            "-OutDir",
            str(RESET_TIMEOUT_SELFTEST_DIR),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )
    summary = load_json(RESET_TIMEOUT_SELFTEST_SUMMARY) if RESET_TIMEOUT_SELFTEST_SUMMARY.exists() else {}
    return {
        "command": "pwsh -NoProfile -File .\\tools\\capture_nucleo_serial.ps1 -SelfTestResetTimeout -OutDir .\\.cache\\validation\\nucleo-serial-reset-timeout-selftest",
        "returncode": completed.returncode,
        "stdout_has_expected_failure": "reset-timeout self-test failed as expected" in (completed.stdout + completed.stderr),
        "summary_path": rel(RESET_TIMEOUT_SELFTEST_SUMMARY),
        "summary_exists": RESET_TIMEOUT_SELFTEST_SUMMARY.exists(),
        "summary_status": summary.get("status"),
        "summary_mode": summary.get("mode"),
        "summary_port": summary.get("port"),
        "bytes_read": summary.get("bytes_read"),
        "reset_timeout_seconds": summary.get("reset_timeout_seconds"),
        "reset_stdout_exists": RESET_TIMEOUT_STDOUT.exists(),
        "reset_stderr_exists": RESET_TIMEOUT_STDERR.exists(),
        "errors": summary.get("errors", []),
        "claim_scope": "stubbed_reset_timeout_no_hardware_claim",
    }


def build_preflight() -> dict[str, Any]:
    capture_text = CAPTURE_SCRIPT.read_text(encoding="utf-8")
    runner_text = RUNNER_SCRIPT.read_text(encoding="utf-8")
    verifier_text = LOG_VERIFIER.read_text(encoding="utf-8")
    run_report = load_json(RUN_REPORT)
    empty_selftest = run_empty_capture_selftest()
    reset_timeout_selftest = run_reset_timeout_selftest()
    steps = run_report.get("steps", [])
    step_lines = {str(step.get("id")): command_line(step) for step in steps if isinstance(step, dict)}
    capture_steps = {
        key: {
            "command": step_lines.get(key),
            "uses_capture_script": "capture_nucleo_serial.ps1" in step_lines.get(key, ""),
            "execute": "-Execute" in step_lines.get(key, ""),
            "workflow_lock_ack": "-WorkflowLockHeld" in step_lines.get(key, ""),
            "reset_after_open": "-ResetAfterOpen" in step_lines.get(key, ""),
            "seconds_25": "-Seconds 25" in step_lines.get(key, ""),
            "out_dir": "-OutDir" in step_lines.get(key, ""),
        }
        for key in ("capture_provision", "capture_normal")
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": STATUS,
        "claim_scope": "static_serial_capture_contract_no_hardware_claim",
        "target": f"NUCLEO-WB55RG rev{CANDIDATE.revision} runtime recheck serial capture",
        "source_files": {
            "capture_script": rel(CAPTURE_SCRIPT),
            "runtime_runner": rel(RUNNER_SCRIPT),
            "runtime_run_report": rel(RUN_REPORT),
            "runtime_log_verifier": rel(LOG_VERIFIER),
        },
        "capture_script_contract": {
            "parameters": has_all(
                capture_text,
                [
                    "[switch] $CheckOnly",
                    "[switch] $Execute",
                    "[switch] $SelfTestEmptyCapture",
                    "[switch] $SelfTestResetTimeout",
                    "[switch] $WorkflowLockHeld",
                    "[string] $Port",
                    "[int] $Seconds",
                    "[switch] $ResetAfterOpen",
                    "[int] $ResetTimeoutSeconds = 15",
                    "[ValidateRange(5, 60)]",
                    "[string] $OutDir",
                ],
            ),
            "safety": has_all(
                capture_text,
                [
                    "Refusing to open Companion NUCLEO serial port without -Execute",
                    "Refusing to open Companion NUCLEO serial port without workflow lock acknowledgement",
                    "Run through aiw with-lock -Resource Companion-WB55",
                    "Resolve-CapturePort",
                    "Get-StLinkSerialCandidates",
                    "STM32_Programmer_CLI",
                    "$serial.ReadTimeout = 250",
                    "Add-Content -LiteralPath $rawLog",
                    "No serial bytes captured during $Seconds second(s); refusing empty runtime evidence.",
                    "Invoke-ProgrammerResetWithTimeout",
                    "Start-Process",
                    "$process.WaitForExit($TimeoutSeconds * 1000)",
                    "Stop-Process -Id $process.Id -Force",
                    "reset timed out after $TimeoutSeconds second(s)",
                    "stm32-reset-stdout.log",
                    "stm32-reset-stderr.log",
                ],
            ),
            "outputs": {
                "raw_log_filename": "nucleo-serial-raw.log",
                "summary_json_filename": "nucleo-serial-summary.json",
                "raw_log_token": "nucleo-serial-raw.log" in capture_text,
                "summary_json_token": "nucleo-serial-summary.json" in capture_text,
                "summary_schema_token": "companion.nucleo_serial.capture.v1" in capture_text,
                "summary_bytes_read_token": "bytes_read = $BytesRead" in capture_text,
                "summary_reset_timeout_token": "reset_timeout_seconds = $ResetTimeoutSeconds" in capture_text,
                "summary_status_pass_token": '$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }' in capture_text,
                "empty_capture_failure_token": '$bytesRead -le 0' in capture_text,
                "selftest_empty_capture_token": "-SelfTestEmptyCapture" in capture_text,
                "selftest_reset_timeout_token": "-SelfTestResetTimeout" in capture_text,
            },
            "check_only_note": (
                "capture_nucleo_serial.ps1 -CheckOnly may enumerate the current COM port; this "
                "preflight is intentionally static so it can run when the WB55 is disconnected."
            ),
        },
        "runner_contract": {
            "capture_seconds_bounds": has_all(
                runner_text,
                [
                    "[int] $CaptureSeconds = 25",
                    "$CaptureSeconds -lt 5 -or $CaptureSeconds -gt 120",
                    "CaptureSeconds must be between 5 and 120.",
                ],
            ),
            "workflow_lock_required_for_execute": "Refusing WB55 runtime recheck without workflow lock acknowledgement" in runner_text,
            "step_order": [str(step.get("id")) for step in steps if isinstance(step, dict)],
            "capture_steps": capture_steps,
            "run_report": {
                "schema": run_report.get("schema"),
                "status": run_report.get("status"),
                "resource": run_report.get("resource", {}),
                "output": run_report.get("output", {}),
                "results_count": len(run_report.get("results", [])),
            },
        },
        "empty_capture_selftest": empty_selftest,
        "reset_timeout_selftest": reset_timeout_selftest,
        "log_verifier_contract": {
            "expects_raw_log": '"nucleo-serial-raw.log"' in verifier_text,
            "expects_summary_json": '"nucleo-serial-summary.json"' in verifier_text,
            "expects_provision_and_normal_dirs": all(token in verifier_text for token in ['log_result("provision"', 'log_result("normal"']),
            "expected_step_order": has_all(verifier_text, EXPECTED_STEPS),
            "expected_markers": {
                marker: all(
                    token in verifier_text
                    for token in (
                        "from screen_runtime_candidate import current_candidate",
                        "CANDIDATE = current_candidate()",
                        "COMMON_MARKERS = CANDIDATE.common_markers",
                        "PROVISION_MARKERS = COMMON_MARKERS +",
                        "NORMAL_MARKERS = COMMON_MARKERS +",
                    )
                )
                for marker in CANDIDATE.common_markers
            },
        },
        "operator_rule": (
            "This preflight does not open serial ports, flash firmware, or claim runtime evidence. "
            "The real capture still requires the Companion-WB55 workflow hardware lock and the "
            "runtime log verifier must remain NO_GO until provision/normal logs exist."
        ),
        "validation_commands": [
            "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
            "pwsh -NoProfile -File .\\tools\\capture_nucleo_serial.ps1 -SelfTestEmptyCapture -OutDir .\\.cache\\validation\\nucleo-serial-empty-selftest",
            "pwsh -NoProfile -File .\\tools\\capture_nucleo_serial.ps1 -SelfTestResetTimeout -OutDir .\\.cache\\validation\\nucleo-serial-reset-timeout-selftest",
            "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
        ],
    }


def check_preflight(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if data.get("status") != STATUS:
        errors.append(f"status must be {STATUS}")
    if data.get("claim_scope") != "static_serial_capture_contract_no_hardware_claim":
        errors.append("claim scope must remain no-hardware")

    for section, checks in (
        ("capture parameters", data.get("capture_script_contract", {}).get("parameters", {})),
        ("capture safety", data.get("capture_script_contract", {}).get("safety", {})),
        ("runner capture bounds", data.get("runner_contract", {}).get("capture_seconds_bounds", {})),
        ("log verifier step order", data.get("log_verifier_contract", {}).get("expected_step_order", {})),
        ("log verifier expected markers", data.get("log_verifier_contract", {}).get("expected_markers", {})),
    ):
        for token, present in checks.items():
            if present is not True:
                errors.append(f"{section} missing token {token}")

    outputs = data.get("capture_script_contract", {}).get("outputs", {})
    for key in (
        "raw_log_token",
        "summary_json_token",
        "summary_schema_token",
        "summary_bytes_read_token",
        "summary_reset_timeout_token",
        "summary_status_pass_token",
        "empty_capture_failure_token",
        "selftest_empty_capture_token",
        "selftest_reset_timeout_token",
    ):
        if outputs.get(key) is not True:
            errors.append(f"capture output contract {key} must be true")
    selftest = data.get("empty_capture_selftest", {})
    if selftest.get("claim_scope") != "stubbed_empty_capture_no_hardware_claim":
        errors.append("empty capture self-test must remain a no-hardware claim")
    if selftest.get("returncode") == 0:
        errors.append("empty capture self-test must return non-zero")
    if selftest.get("stdout_has_expected_failure") is not True:
        errors.append("empty capture self-test must print expected failure")
    if selftest.get("summary_exists") is not True:
        errors.append("empty capture self-test must write summary JSON")
    if selftest.get("raw_log_exists") is not True:
        errors.append("empty capture self-test must write raw log")
    if selftest.get("summary_status") != "FAIL":
        errors.append("empty capture self-test summary must be FAIL")
    if selftest.get("summary_mode") != "selftest-empty-capture":
        errors.append("empty capture self-test mode drifted")
    if selftest.get("summary_port") != "SELFTEST":
        errors.append("empty capture self-test port must be SELFTEST")
    if selftest.get("bytes_read") != 0:
        errors.append("empty capture self-test bytes_read must be 0")
    if selftest.get("reset_timeout_seconds") != 15:
        errors.append("empty capture self-test reset timeout must default to 15 seconds")
    if not any("No serial bytes captured" in str(error) for error in selftest.get("errors", [])):
        errors.append("empty capture self-test errors must name empty serial bytes")
    reset_selftest = data.get("reset_timeout_selftest", {})
    if reset_selftest.get("claim_scope") != "stubbed_reset_timeout_no_hardware_claim":
        errors.append("reset timeout self-test must remain a no-hardware claim")
    if reset_selftest.get("returncode") == 0:
        errors.append("reset timeout self-test must return non-zero")
    if reset_selftest.get("stdout_has_expected_failure") is not True:
        errors.append("reset timeout self-test must print expected failure")
    if reset_selftest.get("summary_exists") is not True:
        errors.append("reset timeout self-test must write summary JSON")
    if reset_selftest.get("summary_status") != "FAIL":
        errors.append("reset timeout self-test summary must be FAIL")
    if reset_selftest.get("summary_mode") != "selftest-reset-timeout":
        errors.append("reset timeout self-test mode drifted")
    if reset_selftest.get("summary_port") != "SELFTEST":
        errors.append("reset timeout self-test port must be SELFTEST")
    if reset_selftest.get("bytes_read") != 0:
        errors.append("reset timeout self-test bytes_read must be 0")
    if reset_selftest.get("reset_timeout_seconds") != 15:
        errors.append("reset timeout self-test summary must keep default reset timeout 15 seconds")
    if reset_selftest.get("reset_stdout_exists") is not True:
        errors.append("reset timeout self-test must write reset stdout log")
    if reset_selftest.get("reset_stderr_exists") is not True:
        errors.append("reset timeout self-test must write reset stderr log")
    if not any("reset timed out after 5 second" in str(error) for error in reset_selftest.get("errors", [])):
        errors.append("reset timeout self-test errors must name timeout")

    runner = data.get("runner_contract", {})
    if runner.get("workflow_lock_required_for_execute") is not True:
        errors.append("runner must require workflow lock for Execute")
    if runner.get("step_order") != EXPECTED_STEPS:
        errors.append("runtime runner must keep flash/capture/normal/capture order")
    for step_id, capture in runner.get("capture_steps", {}).items():
        for key in ("uses_capture_script", "execute", "workflow_lock_ack", "reset_after_open", "seconds_25", "out_dir"):
            if capture.get(key) is not True:
                errors.append(f"{step_id} capture command missing {key}")

    run_report = runner.get("run_report", {})
    resource = run_report.get("resource", {})
    if run_report.get("schema") != "companion.wb55_screen_runtime_recheck_run.v1":
        errors.append("run report schema drifted")
    if run_report.get("status") != "DRY-RUN":
        errors.append("preflight must consume the CheckOnly DRY-RUN report")
    if (
        resource.get("revision") != CANDIDATE.revision
        or resource.get("total_bytes") != CANDIDATE.total_bytes
        or resource.get("pack_crc32") != CANDIDATE.pack_crc32
    ):
        errors.append("run report resource must match the active candidate")
    if run_report.get("results_count") != 0:
        errors.append("CheckOnly run report must not contain real hardware results")
    output = run_report.get("output", {})
    if not str(output.get("provision_dir", "")).endswith("/provision"):
        errors.append("run report provision output dir must end with /provision")
    if not str(output.get("normal_dir", "")).endswith("/normal"):
        errors.append("run report normal output dir must end with /normal")

    verifier = data.get("log_verifier_contract", {})
    for key in ("expects_raw_log", "expects_summary_json", "expects_provision_and_normal_dirs"):
        if verifier.get(key) is not True:
            errors.append(f"log verifier contract {key} must be true")
    if "does not open serial ports" not in str(data.get("operator_rule", "")):
        errors.append("operator rule must state this preflight does not open serial ports")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    data = build_preflight()
    errors: list[str] = []
    check_preflight(data, errors)
    rendered = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write and not errors:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        elif json_path.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(json_path)}; rerun with --write")

    if errors:
        print("FAIL: WB55 runtime serial capture preflight checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 runtime serial capture preflight verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
