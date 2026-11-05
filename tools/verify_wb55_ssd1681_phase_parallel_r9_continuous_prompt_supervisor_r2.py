#!/usr/bin/env python3
"""Exercise the real R9 continuous prompt-supervisor path without hardware or UI."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1"
CACHE = ROOT / ".cache/validation/r9-continuous-r2-prompt-supervisor-regression"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-prompt-supervisor-regression-20260721.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def invoke(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(SUPERVISOR), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def qualification(case_root: Path, monitor_pid: int, *, write_signal: bool = True) -> Path:
    parser = case_root / "simulated-parser-pass.json"
    signal = case_root / "simulated-qualification-ready.json"
    write_json(
        parser,
        {
            "schema_id": "companion.test.r9_continuous_qualification.v1",
            "status": "PASS_MACHINE_R9_CONTINUOUS_TRACE",
            "hardware_contact": 0,
            "qualification": {"activations": 16, "passed_before_loop": True, "busy_max_ms": 599},
            "loop": {"records_in_ring": 1, "busy_max_ms": 597},
            "errors": [],
        },
    )
    if write_signal:
        write_json(
            signal,
            {
                "schema_id": "companion.test.r9_continuous_qualification_ready.v1",
                "status": "PASS_INITIAL_16_READY_FOR_CONCURRENT_ACCEPTANCE",
                "hardware_contact": 0,
                "parser_artifact": str(parser.resolve()),
                "process_id": monitor_pid,
            },
        )
    return signal


def common_args(case_root: Path, signal: Path, stub: Path) -> list[str]:
    return [
        "-SimulateQualifiedPrompt",
        "-QualificationSignalPath", str(signal.resolve()),
        "-MonitorResultPath", str((case_root / "monitor-result.json").resolve()),
        "-StopSignalPath", str((case_root / "operator-stop.json").resolve()),
        "-EmergencyStopPath", str((case_root / "emergency-stop.json").resolve()),
        "-SimulationPromptScript", str(stub.resolve()),
        "-OutRoot", str(case_root.resolve()),
        "-TimeoutSeconds", "60",
    ]


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    if CACHE.exists():
        shutil.rmtree(CACHE)
    CACHE.mkdir(parents=True)
    stub = CACHE / "process-only-prompt-stub.ps1"
    stub.write_text(
        """param([Parameter(Mandatory = $true)][string]$OutputPath)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[System.IO.File]::WriteAllText($OutputPath, "模拟监督器路径通过", [System.Text.UTF8Encoding]::new($false))
[ordered]@{ selected = "通过"; text = "模拟监督器路径通过" } | ConvertTo-Json -Compress
""",
        encoding="utf-8",
    )

    monitor = subprocess.Popen(
        ["pwsh", "-NoProfile", "-Command", "Start-Sleep -Seconds 120"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cases: dict[str, dict[str, Any]] = {}
    try:
        positive_root = CACHE / "positive"
        positive_root.mkdir()
        positive_signal = qualification(positive_root, monitor.pid)
        positive = invoke(common_args(positive_root, positive_signal, stub))
        guard_path = positive_root / "acceptance-prompt-invoked.json"
        receipt_path = positive_root / "prompt-simulation-receipt.json"
        review_path = positive_root / "operator-review.json"
        stop_path = positive_root / "operator-stop.json"
        guard = json.loads(guard_path.read_text(encoding="utf-8-sig")) if guard_path.is_file() else {}
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig")) if receipt_path.is_file() else {}
        review = json.loads(review_path.read_text(encoding="utf-8-sig")) if review_path.is_file() else {}
        stop = json.loads(stop_path.read_text(encoding="utf-8-sig")) if stop_path.is_file() else {}
        cases["positive"] = {
            "exit_code": positive.returncode,
            "guard_created": guard_path.is_file(),
            "prompt_process_start_count": receipt.get("prompt_process_start_count"),
            "actual_popup_count": receipt.get("actual_popup_count"),
            "review_created": review_path.is_file(),
            "stop_created": stop_path.is_file(),
            "selected": review.get("selected"),
        }
        require("positive_exit_zero", positive.returncode == 0, "simulated qualified supervisor path failed")
        require(
            "positive_guard_created_before_process",
            guard.get("status") == "INVOKED_ONCE"
            and guard.get("simulation_no_hardware") is True
            and guard.get("actual_popup_count") == 0,
            "single-use guard was not created by the real supervisor path",
        )
        require(
            "positive_exactly_one_prompt_process_zero_popup",
            receipt.get("status") == "PROMPT_PROCESS_STARTED_ONCE_NO_POPUP"
            and receipt.get("hardware_contact") == 0
            and receipt.get("prompt_process_start_count") == 1
            and receipt.get("actual_popup_count") == 0,
            "positive simulation did not start exactly one process with zero popups",
        )
        require(
            "positive_common_result_and_stop_path",
            review.get("status") == "PASS_OWNER_R9_CONTINUOUS_VISUAL"
            and review.get("selected") == "通过"
            and review.get("simulation_no_hardware") is True
            and review.get("popup_counts", {}).get("final_visual_acceptance") == 0
            and stop.get("reason") == "operator_selection"
            and not (positive_root / "emergency-stop.json").exists(),
            "positive simulation did not complete the common review/stop path",
        )

        missing_root = CACHE / "missing-qualification"
        missing_root.mkdir()
        missing_signal = qualification(missing_root, monitor.pid, write_signal=False)
        missing = invoke(common_args(missing_root, missing_signal, stub))
        cases["missing_qualification"] = {
            "exit_code_nonzero": missing.returncode != 0,
            "expected_error": "initial 16-step qualification signal is absent" in missing.stderr,
            "guard_created": (missing_root / "acceptance-prompt-invoked.json").exists(),
            "prompt_receipt_created": (missing_root / "prompt-simulation-receipt.json").exists(),
        }
        require(
            "missing_qualification_fails_before_guard_or_process",
            missing.returncode != 0
            and "initial 16-step qualification signal is absent" in missing.stderr
            and not (missing_root / "acceptance-prompt-invoked.json").exists()
            and not (missing_root / "prompt-simulation-receipt.json").exists()
            and not (missing_root / "operator-review.json").exists(),
            "missing qualification did not fail before guard/process/result",
        )

        guard_root = CACHE / "duplicate-guard"
        guard_root.mkdir()
        guard_signal = qualification(guard_root, monitor.pid)
        guard_existing = guard_root / "acceptance-prompt-invoked.json"
        write_json(guard_existing, {"fixture": "pre-existing-guard"})
        guard_before = sha(guard_existing)
        duplicate_guard = invoke(common_args(guard_root, guard_signal, stub))
        cases["duplicate_guard"] = {
            "exit_code_nonzero": duplicate_guard.returncode != 0,
            "expected_error": "sole acceptance prompt has already been invoked" in duplicate_guard.stderr,
            "preexisting_guard_unchanged": sha(guard_existing) == guard_before,
            "prompt_receipt_created": (guard_root / "prompt-simulation-receipt.json").exists(),
        }
        require(
            "duplicate_guard_fails_before_process_or_result",
            duplicate_guard.returncode != 0
            and "sole acceptance prompt has already been invoked" in duplicate_guard.stderr
            and sha(guard_existing) == guard_before
            and not (guard_root / "prompt-simulation-receipt.json").exists()
            and not (guard_root / "operator-review.json").exists(),
            "pre-existing guard did not block a duplicate process/result",
        )

        review_root = CACHE / "duplicate-review"
        review_root.mkdir()
        review_signal = qualification(review_root, monitor.pid)
        review_existing = review_root / "operator-review.json"
        write_json(review_existing, {"fixture": "pre-existing-review-result"})
        review_before = sha(review_existing)
        duplicate_review = invoke(common_args(review_root, review_signal, stub))
        cases["duplicate_review_result"] = {
            "exit_code_nonzero": duplicate_review.returncode != 0,
            "expected_error": "sole acceptance prompt has already been invoked" in duplicate_review.stderr,
            "preexisting_result_unchanged": sha(review_existing) == review_before,
            "guard_created": (review_root / "acceptance-prompt-invoked.json").exists(),
            "prompt_receipt_created": (review_root / "prompt-simulation-receipt.json").exists(),
        }
        require(
            "duplicate_review_fails_before_guard_or_process",
            duplicate_review.returncode != 0
            and "sole acceptance prompt has already been invoked" in duplicate_review.stderr
            and sha(review_existing) == review_before
            and not (review_root / "acceptance-prompt-invoked.json").exists()
            and not (review_root / "prompt-simulation-receipt.json").exists(),
            "pre-existing review/result did not block a duplicate guard/process",
        )

        injection_root = CACHE / "execute-injection"
        execute_injection = invoke([
            "-Execute", "-SimulationPromptScript", str(stub.resolve()), "-OutRoot", str(injection_root.resolve())
        ])
        cases["execute_injection"] = {
            "exit_code_nonzero": execute_injection.returncode != 0,
            "expected_error": "Simulation prompt injection is forbidden in Execute mode" in execute_injection.stderr,
            "output_root_created": injection_root.exists(),
        }
        require(
            "execute_rejects_simulation_injection_before_output",
            execute_injection.returncode != 0
            and "Simulation prompt injection is forbidden in Execute mode" in execute_injection.stderr
            and not injection_root.exists(),
            "Execute did not reject simulation injection before output",
        )
    finally:
        monitor.terminate()
        try:
            monitor.wait(timeout=5)
        except subprocess.TimeoutExpired:
            monitor.kill()
            monitor.wait(timeout=5)

    source = SUPERVISOR.read_text(encoding="utf-8")
    escaped_supervisor = str(SUPERVISOR).replace("'", "''")
    parse_script = (
        "$tokens=$null; $errors=$null; "
        f"[void][System.Management.Automation.Language.Parser]::ParseFile('{escaped_supervisor}',[ref]$tokens,[ref]$errors); "
        "if($errors.Count -ne 0){$errors | ForEach-Object { $_.Message }; exit 1}"
    )
    parsed = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", parse_script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    require("powershell_parse_pass", parsed.returncode == 0, "supervisor PowerShell parse failed")
    require(
        "exact_separately_parenthesized_guard_condition",
        "if ((Test-Path -LiteralPath $guardPath -PathType Leaf) -or\n    (Test-Path -LiteralPath $reviewPath -PathType Leaf))" in source,
        "guard/review Test-Path calls are not separately parenthesized",
    )
    require(
        "single_common_process_start_statement",
        source.count("[System.Diagnostics.Process]::Start($startInfo)") == 1,
        "supervisor has more or fewer than one common prompt-process start statement",
    )

    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous.r2_prompt_supervisor_regression.v1",
        "status": "PASS_R9_CONTINUOUS_R2_REAL_SUPERVISOR_PATH_NO_HARDWARE" if not errors else "NO_GO_R9_CONTINUOUS_R2_PROMPT_SUPERVISOR_REGRESSION",
        "requirement": "COMP-REQ-316",
        "hardware_contact": 0,
        "actual_popup_count": 0,
        "errors": errors,
        "checks": checks,
        "cases": cases,
        "positive_proof": {"guard_created": True, "prompt_process_start_count": 1, "actual_popup_count": 0},
        "negative_proof": {"missing_qualification_processes": 0, "duplicate_guard_processes": 0, "duplicate_review_result_processes": 0},
        "identities": {"supervisor_sha256": sha(SUPERVISOR), "verifier_sha256": sha(Path(__file__).resolve())},
        "authorization": "simulation and MACHINE_READY only; no Execute or hardware contact",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
