#!/usr/bin/env python3
"""Static and no-hardware negative gate for the R9 persistent launcher."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-persistent-launcher-static-20260721.json"
RUNNER_HASH = "0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B"
CANDIDATE_HASH = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF"
WORKBENCH_HASH = "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF"
PROMPT_HASH = "56794D5856248E1D868DEF23DC9CE983F7069CF4C15A59308F2F011BC9164E15"


def evaluate(source: str) -> list[str]:
    errors: list[str] = []
    required = {
        "mode_exclusive": "if ($CheckOnly -eq $Execute)",
        "fixture_checkonly_only": "LifecycleSelfTestFailure is allowed only with -CheckOnly",
        "reuse_rejected": "R9 persistent launch output directory already exists; reuse is forbidden",
        "new_output_directory": "New-Item -ItemType Directory -Path $runRoot",
        "single_child": '$process = Start-Process -FilePath "pwsh"',
        "stdout_redirect": "-RedirectStandardOutput $stdout",
        "stderr_redirect": "-RedirectStandardError $stderr",
        "hidden_pid": "-WindowStyle Hidden -PassThru",
        "pid_record": "process_id = $process.Id",
        "arguments_record": "arguments = @($arguments)",
        "r9_mode": '"-PhaseParallelR9"',
        "runner_mode": '$(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" })',
        "durable_contract": "observer_may_exit_without_closing_runner_streams = $true",
        "detached_execute": '"STARTED_DETACHED"',
        "child_failure": '"NO_GO_CHECK_CHILD_EXIT"',
        "check_stage": '$stage.status -eq "READY_NO_HARDWARE_CONTACT"',
        "zero_writes": "$writeSum -eq 0",
        "zero_preexecute_popup": "$stage.pre_execute_prompt.invoked -eq $false",
        "final_prompt_not_checkonly": "$stage.operator_prompt.invoked -eq $false",
        "final_prompt_declared": "$stage.operator_prompt.required -eq $true",
        "popup_count": "$stage.popup_policy.visual_acceptance -eq 1",
        "machine_ready_only": "COMP-REQ-309 authorizes CheckOnly and MACHINE_READY only",
        "runner_hash": RUNNER_HASH,
        "candidate_hash": CANDIDATE_HASH,
        "workbench_hash": WORKBENCH_HASH,
        "prompt_hash": PROMPT_HASH,
    }
    for name, token in required.items():
        if token not in source:
            errors.append(name)
    if source.count('Start-Process -FilePath "pwsh"') != 1:
        errors.append("single_child_count")
    return errors


def static_fixtures(source: str) -> list[str]:
    cases = {
        "good": (source, False),
        "missing_stdout": (source.replace("-RedirectStandardOutput $stdout", "-NoNewWindow", 1), True),
        "missing_stderr": (source.replace("-RedirectStandardError $stderr", "", 1), True),
        "missing_hidden": (source.replace("-WindowStyle Hidden -PassThru", "-PassThru", 1), True),
        "missing_pid": (source.replace("process_id = $process.Id", "process_id = $null", 1), True),
        "allows_reuse": (source.replace("R9 persistent launch output directory already exists; reuse is forbidden", "reuse accepted", 1), True),
        "ignores_child_failure": (source.replace('"NO_GO_CHECK_CHILD_EXIT"', '"READY_NO_HARDWARE_CONTACT"', 1), True),
        "wrong_runner_hash": (source.replace(RUNNER_HASH, "0" * 64, 1), True),
        "wrong_candidate_hash": (source.replace(CANDIDATE_HASH, "F" * 64, 1), True),
        "wrong_workbench_hash": (source.replace(WORKBENCH_HASH, "0" * 64, 1), True),
        "wrong_prompt_hash": (source.replace(PROMPT_HASH, "0" * 64, 1), True),
        "execute_in_checkonly": (
            source.replace('$(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" })', '"-Execute"', 1),
            True,
        ),
        "prompt_in_checkonly": (source.replace("$stage.operator_prompt.invoked -eq $false", "$true", 1), True),
    }
    errors: list[str] = []
    for name, (candidate, should_fail) in cases.items():
        failed = bool(evaluate(candidate))
        if failed != should_fail:
            errors.append(name)
    return errors


def dynamic_negative_fixtures() -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    evidence: dict[str, object] = {}
    cache_root = ROOT / ".cache/validation"
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="r9-launcher-negative-", dir=cache_root) as temp:
        temp_path = Path(temp)
        failure_root = temp_path / "child-failure"
        child_failure = subprocess.run(
            [
                "pwsh", "-NoProfile", "-File", str(LAUNCHER),
                "-CheckOnly", "-LifecycleSelfTestFailure", "-OutRoot", str(failure_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        launch_path = failure_root / "persistent-launch.json"
        launch = json.loads(launch_path.read_text(encoding="utf-8-sig")) if launch_path.is_file() else {}
        child_ok = (
            child_failure.returncode != 0
            and launch.get("status") == "NO_GO_CHECK_CHILD_EXIT"
            and launch.get("exit_code") == 23
            and launch.get("hardware_contact") == 0
            and launch.get("write_counter_sum") == 0
            and not (failure_root / "stage-run.json").exists()
        )
        if not child_ok:
            errors.append("child_nonzero_fail_closed")
        evidence["child_nonzero"] = {
            "passed": child_ok,
            "process_exit": child_failure.returncode,
            "child_exit": launch.get("exit_code"),
            "status": launch.get("status"),
            "hardware_contact": launch.get("hardware_contact"),
        }

        reuse = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(LAUNCHER), "-CheckOnly", "-OutRoot", str(failure_root)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        reuse_ok = reuse.returncode != 0 and "reuse is forbidden" in (reuse.stdout + reuse.stderr)
        if not reuse_ok:
            errors.append("reused_output_root_fail_closed")
        evidence["reused_output_root"] = {"passed": reuse_ok, "process_exit": reuse.returncode}

        both_root = temp_path / "both"
        both = subprocess.run(
            [
                "pwsh", "-NoProfile", "-File", str(LAUNCHER),
                "-CheckOnly", "-Execute", "-OutRoot", str(both_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        both_ok = (
            both.returncode != 0
            and "Choose exactly one" in (both.stdout + both.stderr)
            and not both_root.exists()
        )
        if not both_ok:
            errors.append("checkonly_execute_exclusive")
        evidence["checkonly_execute_exclusive"] = {"passed": both_ok, "process_exit": both.returncode}
    return errors, evidence


def main() -> int:
    source = LAUNCHER.read_text(encoding="utf-8") if LAUNCHER.is_file() else ""
    errors = [f"source:{item}" for item in evaluate(source)]
    errors.extend(f"static_fixture:{item}" for item in static_fixtures(source))

    parse = subprocess.run(
        [
            "pwsh", "-NoProfile", "-Command",
            f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{LAUNCHER}' -Raw)); 'PASS'",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if parse.returncode != 0 or "PASS" not in parse.stdout:
        errors.append("powershell_parse")

    dynamic_errors, dynamic_evidence = dynamic_negative_fixtures()
    errors.extend(f"dynamic_fixture:{item}" for item in dynamic_errors)
    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9.persistent_launcher_static.v1",
        "status": (
            "PASS_R9_PERSISTENT_LAUNCHER_STATIC_AND_NEGATIVE_FIXTURES"
            if not errors
            else "NO_GO_R9_PERSISTENT_LAUNCHER"
        ),
        "errors": errors,
        "checks": {
            "source_contract": not evaluate(source),
            "static_negative_fixture_count": len(static_fixtures(source)) if errors else 12,
            "powershell_parse": parse.returncode == 0 and "PASS" in parse.stdout,
            "dynamic_no_hardware_negative_fixtures": dynamic_evidence,
            "hardware_contact": 0,
            "execute_invoked": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
