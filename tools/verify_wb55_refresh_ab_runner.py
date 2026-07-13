#!/usr/bin/env python3
"""Verify that the WB55 refresh A/B runner is safe before real hardware use."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_wb55_refresh_ab.ps1"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-wb55-refresh-ab-runner.json"
CHECK_ROOT = ROOT / ".cache" / "validation" / "companion-performance" / "refresh-ab-checkonly"
RECOVERY_ROOT = ROOT / ".cache" / "validation" / "companion-performance" / "refresh-ab-recovery-selftest"
EXPECTED_STEPS = [
    "flash_differential",
    "capture_differential",
    "parse_differential",
    "flash_direct_bsrr",
    "capture_direct_bsrr",
    "parse_direct_bsrr",
    "flash_vendor_partial",
    "capture_vendor_partial",
    "parse_vendor_partial",
    "flash_normal_restore",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_runner(*args: str, timeout: int = 60) -> dict[str, Any]:
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(RUNNER), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def source_safety_contract(text: str) -> dict[str, bool]:
    return {
        "check_only_is_non_hardware": all(token in text for token in ("if ($CheckOnly)", "DRY-RUN", "exit 0")),
        "execute_requires_workflow_lock": all(
            token in text
            for token in (
                "if ($Execute -and -not $WorkflowLockHeld)",
                "Refusing WB55 refresh A/B execution without workflow lock acknowledgement",
                "aiw with-lock -Resource Companion-WB55",
            )
        ),
        "all_three_profiles_are_explicit": all(
            token in text
            for token in (
                'id = "differential"',
                'id = "direct_bsrr"',
                'id = "vendor_partial"',
                'expected_control = "0xFC"',
                'expected_control = "0xFF"',
            )
        ),
        "each_capture_is_reset_bounded": all(
            token in text for token in ("-ResetAfterOpen", "nucleo-serial-raw.log", "-Seconds", "$CaptureSeconds")
        ),
        "each_trace_uses_strict_parser": all(
            token in text
            for token in (
                "verify_wb55_refresh_cadence_log.py",
                "--partial-profile",
                "--transport-profile",
                "refresh-cadence-result.json",
            )
        ),
        "restores_normal_firmware_after_failure": all(
            token in text
            for token in (
                "$diagnosticFlashed = $false",
                "$normalRestored = $false",
                "RECOVERY: flash_normal_restore_after_failure",
                "$report.normal_firmware_restored = [bool]$normalRestored",
            )
        ),
        "selftest_recovery_is_no_hardware": all(
            token in text
            for token in (
                "SELFTEST: flash_differential",
                "SELFTEST: capture_differential failure",
                "SELFTEST: flash_normal_restore",
            )
        ),
    }


def build_snapshot() -> dict[str, Any]:
    runner_text = RUNNER.read_text(encoding="utf-8")
    check = run_runner("-CheckOnly", "-OutRoot", str(CHECK_ROOT))
    check_text = check["stdout"] + check["stderr"]
    check_report = load_json(CHECK_ROOT / "refresh-ab-run.json")

    negative = run_runner("-Execute", timeout=30)
    negative_text = negative["stdout"] + negative["stderr"]

    recovery = run_runner("-SelfTestRecovery", "-OutRoot", str(RECOVERY_ROOT))
    recovery_text = recovery["stdout"] + recovery["stderr"]
    recovery_report = load_json(RECOVERY_ROOT / "refresh-ab-run.json")
    recovery_statuses = {
        str(item.get("id")): str(item.get("status"))
        for item in recovery_report.get("results", [])
        if isinstance(item, dict)
    }
    recovery_codes = {
        str(item.get("id")): item.get("exit_code")
        for item in recovery_report.get("results", [])
        if isinstance(item, dict)
    }

    return {
        "schema_id": "companion.wb55.refresh_ab_runner_validation.v1",
        "status": "PASS",
        "runner": rel(RUNNER),
        "safety_contract": source_safety_contract(runner_text),
        "check_only": {
            "returncode": check["returncode"],
            "sequence_banner": "CHECK: WB55 refresh A/B sequence profiles=differential,direct_bsrr,vendor_partial" in check_text,
            "report_path": rel(CHECK_ROOT / "refresh-ab-run.json"),
            "report_exists": (CHECK_ROOT / "refresh-ab-run.json").exists(),
            "report_schema": check_report.get("schema_id"),
            "report_status": check_report.get("status"),
            "report_claim_scope": check_report.get("claim_scope"),
            "result_count": len(check_report.get("results", [])),
            "step_ids": [
                str(item.get("id")) for item in check_report.get("steps", []) if isinstance(item, dict)
            ],
            "profiles": check_report.get("profiles", []),
        },
        "execute_without_lock_negative": {
            "returncode": negative["returncode"],
            "refused_before_hardware": (
                negative["returncode"] != 0
                and "Refusing WB55 refresh A/B execution without workflow lock acknowledgement" in negative_text
                and "RUN:" not in negative_text
            ),
            "claim_scope": "negative_execute_lock_guard_no_hardware_claim",
        },
        "recovery_selftest": {
            "returncode": recovery["returncode"],
            "stdout_has_recovery": "RECOVERY: flash_normal_restore_after_failure" in recovery_text,
            "report_path": rel(RECOVERY_ROOT / "refresh-ab-run.json"),
            "report_exists": (RECOVERY_ROOT / "refresh-ab-run.json").exists(),
            "report_status": recovery_report.get("status"),
            "normal_firmware_restored": recovery_report.get("normal_firmware_restored"),
            "result_ids": list(recovery_statuses),
            "result_statuses": recovery_statuses,
            "result_exit_codes": recovery_codes,
            "claim_scope": recovery_report.get("claim_scope"),
        },
        "commands": [
            "pwsh -NoProfile -File .\\tools\\run_wb55_refresh_ab.ps1 -CheckOnly",
            "pwsh -NoProfile -File .\\tools\\run_wb55_refresh_ab.ps1 -SelfTestRecovery",
            "pwsh -NoProfile -File C:\\Users\\Billy\\Desktop\\Denzic\\ai-collaboration-workflow\\scripts\\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose \"Companion WB55 refresh A/B\" -Run pwsh -NoProfile -File .\\tools\\run_wb55_refresh_ab.ps1 -Execute -WorkflowLockHeld",
        ],
    }


def verify(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if snapshot.get("schema_id") != "companion.wb55.refresh_ab_runner_validation.v1":
        errors.append("unexpected schema_id")
    if snapshot.get("runner") != rel(RUNNER):
        errors.append("runner path drifted")
    for key, value in snapshot.get("safety_contract", {}).items():
        if value is not True:
            errors.append(f"safety_contract.{key} is not true")

    check = snapshot.get("check_only", {})
    if check.get("returncode") != 0 or check.get("sequence_banner") is not True:
        errors.append("runner -CheckOnly must complete and describe all three profiles")
    if check.get("report_exists") is not True:
        errors.append("runner -CheckOnly must write a dry-run report")
    if check.get("report_schema") != "companion.wb55.refresh_ab_run.v1":
        errors.append("check-only report schema drifted")
    if check.get("report_status") != "DRY-RUN":
        errors.append("check-only report must remain DRY-RUN")
    if check.get("report_claim_scope") != "preflight_only_no_hardware_claim":
        errors.append("check-only report must retain the no-hardware claim scope")
    if check.get("result_count") != 0:
        errors.append("check-only report must not execute any step")
    if check.get("step_ids") != EXPECTED_STEPS:
        errors.append("refresh A/B step order drifted")
    profiles = check.get("profiles", [])
    expected_profiles = [
        ("differential", "differential", "vendor_edges", "0xFC", 2),
        ("direct_bsrr", "differential", "direct_bsrr", "0xFC", 2),
        ("vendor_partial", "vendor_sample", "vendor_edges", "0xFF", 1),
    ]
    observed_profiles = [
        (
            item.get("id"),
            item.get("partial_profile"),
            item.get("transport_profile"),
            item.get("expected_control"),
            item.get("expected_planes"),
        )
        for item in profiles
        if isinstance(item, dict)
    ]
    if observed_profiles != expected_profiles:
        errors.append("refresh A/B profile matrix drifted")

    negative = snapshot.get("execute_without_lock_negative", {})
    if negative.get("returncode") == 0 or negative.get("refused_before_hardware") is not True:
        errors.append("runner -Execute must refuse before hardware without a workflow lock")

    recovery = snapshot.get("recovery_selftest", {})
    if recovery.get("returncode") == 0 or recovery.get("stdout_has_recovery") is not True:
        errors.append("recovery self-test must fail after capture and attempt normal firmware restoration")
    if recovery.get("report_status") != "FAIL" or recovery.get("normal_firmware_restored") is not True:
        errors.append("recovery report must preserve normal firmware restoration evidence")
    if recovery.get("result_ids") != [
        "flash_differential",
        "capture_differential",
        "flash_normal_restore_after_failure",
    ]:
        errors.append("recovery self-test step order drifted")
    if recovery.get("result_statuses") != {
        "flash_differential": "PASS",
        "capture_differential": "FAIL",
        "flash_normal_restore_after_failure": "PASS",
    }:
        errors.append("recovery self-test results drifted")
    if recovery.get("result_exit_codes", {}).get("capture_differential") != 7:
        errors.append("recovery self-test capture failure code must remain 7")
    if recovery.get("claim_scope") != "stubbed_failure_recovery_no_hardware_claim":
        errors.append("recovery self-test claim scope drifted")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args()
    output = args.json if args.json.is_absolute() else ROOT / args.json
    snapshot = build_snapshot()
    errors = verify(snapshot)
    rendered = json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write and not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not output.exists():
            errors.append(f"missing {rel(output)}")
        elif output.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(output)}; rerun with --write")
    if errors:
        print("FAIL: WB55 refresh A/B runner verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 refresh A/B runner verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
