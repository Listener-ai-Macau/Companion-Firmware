#!/usr/bin/env python3
"""Fail-closed static and no-hardware negative gate for the R8 launcher."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_ram_command_target_r8.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-persistent-launcher-static-20260721.json"
RUNNER_HASH = "3E1A3FFDC4B44BDE107CF6A0922E81ECA1F95442B8A6A3BDF4F71C018806D017"
CANDIDATE_HASH = "9ECF8F4A2A75A054077908C775879447ADCE089F55DC33315A8C852C4F47CB13"


def evaluate(source: str) -> list[str]:
    errors: list[str] = []
    required = {
        "mode_exclusive": "if ($CheckOnly -eq $Execute)",
        "fixture_checkonly_only": "LifecycleSelfTestFailure is allowed only with -CheckOnly",
        "reuse_rejected": "R8 persistent launch output directory already exists; reuse is forbidden",
        "new_output_directory": "New-Item -ItemType Directory -Path $runRoot",
        "single_child": '$process = Start-Process -FilePath "pwsh"',
        "stdout_redirect": "-RedirectStandardOutput $stdout",
        "stderr_redirect": "-RedirectStandardError $stderr",
        "hidden_pid": "-WindowStyle Hidden -PassThru",
        "pid_record": "process_id = $process.Id",
        "arguments_record": "arguments = @($arguments)",
        "r8_mode": '"-RamCommandTargetR8"',
        "runner_mode": '$(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" })',
        "durable_contract": "observer_may_exit_without_closing_runner_streams = $true",
        "detached_execute": '"STARTED_DETACHED"',
        "child_failure": '"NO_GO_CHECK_CHILD_EXIT"',
        "check_stage": '$stage.status -eq "READY_NO_HARDWARE_CONTACT"',
        "zero_writes": "$writeSum -eq 0",
        "zero_preexecute_popup": "$stage.pre_execute_prompt.invoked -eq $false",
        "zero_operator_popup": "$stage.operator_prompt.invoked -eq $false",
        "runner_hash": RUNNER_HASH,
        "candidate_hash": CANDIDATE_HASH,
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
        "allows_reuse": (source.replace("R8 persistent launch output directory already exists; reuse is forbidden", "reuse accepted", 1), True),
        "ignores_child_failure": (source.replace('"NO_GO_CHECK_CHILD_EXIT"', '"READY_NO_HARDWARE_CONTACT"', 1), True),
        "wrong_runner_hash": (source.replace(RUNNER_HASH, "0" * 64, 1), True),
        "wrong_candidate_hash": (source.replace(CANDIDATE_HASH, "F" * 64, 1), True),
        "execute_in_checkonly": (source.replace('$(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" })', '"-Execute"', 1), True),
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
    with tempfile.TemporaryDirectory(prefix="r8-launcher-negative-", dir=cache_root) as temp:
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

        both = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(LAUNCHER), "-CheckOnly", "-Execute", "-OutRoot", str(temp_path / "both")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        both_ok = both.returncode != 0 and "Choose exactly one" in (both.stdout + both.stderr) and not (temp_path / "both").exists()
        if not both_ok:
            errors.append("checkonly_execute_exclusive")
        evidence["checkonly_execute_exclusive"] = {"passed": both_ok, "process_exit": both.returncode}
    return errors, evidence


def main() -> int:
    source = LAUNCHER.read_text(encoding="utf-8") if LAUNCHER.is_file() else ""
    errors = [f"source:{item}" for item in evaluate(source)]
    errors.extend(f"static_fixture:{item}" for item in static_fixtures(source))

    parse = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{LAUNCHER}' -Raw)); 'PASS'"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if parse.returncode != 0 or "PASS" not in parse.stdout:
        errors.append("powershell_parse")

    dynamic_errors, dynamic_evidence = dynamic_negative_fixtures()
    errors.extend(f"dynamic_fixture:{item}" for item in dynamic_errors)
    report = {
        "schema_id": "companion.wb55.ssd1681_ram_command_target_r8.persistent_launcher_static.v1",
        "status": "PASS_R8_PERSISTENT_LAUNCHER_STATIC_AND_NEGATIVE_FIXTURES" if not errors else "NO_GO_R8_PERSISTENT_LAUNCHER",
        "errors": errors,
        "checks": {
            "source_contract": not evaluate(source),
            "static_negative_fixture_count": 9,
            "powershell_parse": parse.returncode == 0 and "PASS" in parse.stdout,
            "dynamic_no_hardware_negative_fixtures": dynamic_evidence,
            "hardware_contact": 0,
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
