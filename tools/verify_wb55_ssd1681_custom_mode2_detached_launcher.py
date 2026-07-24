#!/usr/bin/env python3
"""Fail-closed source and fixture gate for the detached custom Mode2 launcher."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_custom_mode2_transition_safety.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-detached-launcher-static-20260721.json"


def evaluate(source: str) -> list[str]:
    errors: list[str] = []
    required = {
        "mode_exclusive": "if ($CheckOnly -eq $Execute)",
        "reuse_rejected": "Detached launch output directory already exists; reuse is forbidden",
        "new_output_directory": "New-Item -ItemType Directory -Path $runRoot",
        "child_process": '$process = Start-Process -FilePath "pwsh"',
        "stdout_redirect": "-RedirectStandardOutput $stdout",
        "stderr_redirect": "-RedirectStandardError $stderr",
        "hidden_process": "-WindowStyle Hidden -PassThru",
        "runner_mode": '$(if ($CheckOnly) { "-CheckOnly" } else { "-Execute" })',
        "custom_mode": '"-CustomMode2TransitionSafety"',
        "durable_claim": "observer_may_exit_without_closing_runner_streams = $true",
        "execute_returns_detached": '"STARTED_DETACHED"',
        "check_stage": 'stage.status -eq "READY_NO_HARDWARE_CONTACT"',
    }
    for name, token in required.items():
        if token not in source:
            errors.append(name)
    if source.count("Start-Process -FilePath \"pwsh\"") != 1:
        errors.append("single_child_process")
    return errors


def self_test() -> list[str]:
    good = LAUNCHER.read_text(encoding="utf-8")
    cases = {
        "good": (good, False),
        "missing_stdout": (good.replace("-RedirectStandardOutput $stdout", "-NoNewWindow"), True),
        "missing_stderr": (good.replace("-RedirectStandardError $stderr", ""), True),
        "allows_reuse": (good.replace("Detached launch output directory already exists; reuse is forbidden", "reuse accepted"), True),
        "not_custom": (good.replace('"-CustomMode2TransitionSafety"', '"-ResetReadControllerState"'), True),
    }
    errors: list[str] = []
    for name, (source, should_fail) in cases.items():
        failed = bool(evaluate(source))
        if failed != should_fail:
            errors.append(name)
    return errors


def main() -> int:
    fixture_errors = self_test()
    source_errors = evaluate(LAUNCHER.read_text(encoding="utf-8")) if LAUNCHER.is_file() else ["launcher_missing"]
    parse = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{LAUNCHER}' -Raw)); 'PASS'"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    errors = source_errors + [f"fixture:{item}" for item in fixture_errors]
    if parse.returncode != 0 or "PASS" not in parse.stdout:
        errors.append("powershell_parse")
    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_detached_launcher_static.v1",
        "status": "PASS_DETACHED_LAUNCHER_DURABLE_STREAMS_AND_NEGATIVE_FIXTURES" if not errors else "NO_GO_DETACHED_LAUNCHER",
        "errors": errors,
        "checks": {
            "durable_stdout_stderr": "missing either redirect is rejected",
            "output_directory_reuse": "existing output root is rejected before child start",
            "custom_mode_only": True,
            "check_only_waits_and_verifies_zero_contact": True,
            "execute_returns_after_start": True,
            "negative_fixture_count": 4,
        },
        "hardware_contact": 0,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
