#!/usr/bin/env python3
"""Seal the no-hardware R9 continuous R2 prompt-supervisor repair."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-machine-ready-20260721.json"
PATHS = {
    "r1_machine_ready": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-machine-ready-20260721.json",
    "r1_authorization": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-execute-authorization-20260721.json",
    "r1_incident": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-runtime-disposition-20260721.json",
    "prompt_regression": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-prompt-supervisor-regression-20260721.json",
    "static": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-observation-static-20260721.json",
    "launcher_static": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-launcher-static-20260721.json",
    "direct_check_stage": ROOT / ".cache/validation/wb55-r9-continuous-r2-runner-checkonly-20260721-r1/stage-run.json",
    "persistent_check_launch": ROOT / ".cache/validation/wb55-r9-continuous-r2-persistent-checkonly-20260721-r1/persistent-launch.json",
    "persistent_check_stage": ROOT / ".cache/validation/wb55-r9-continuous-r2-persistent-checkonly-20260721-r1/stage-run.json",
    "current_goal": ROOT / "docs/validation/companion-current-goal-audit-20260717.json",
    "product_requirements": ROOT / "docs/validation/companion-product-requirements.json",
    "candidate_hex": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.hex",
    "candidate_elf": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.elf",
    "candidate_bin": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.bin",
    "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1",
    "prompt_regression_verifier": ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_prompt_supervisor_r2.py",
    "static_verifier": ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_observation.py",
    "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1",
    "launcher_verifier": ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_launcher.py",
    "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1",
    "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r9_continuous.ps1",
    "parser": ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_log.py",
    "historical_runner": ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1",
    "historical_hex": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex",
    "protected_v9": ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png",
    "protected_owner_acceptance": ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json",
}

EXPECTED = {
    "r1_machine_ready": "68BA95CE95BF4FA3D17847B1A3731E26012CAE5A166B4156C2B44457B139E170",
    "candidate_hex": "3B416BFF08B630D23BDB6107B2C17DFE9FBBFAAA7D5CFBCA5063AE68E62B79C5",
    "candidate_elf": "B9808E72F8490B015A9B09B6B8B896390566D06FB8ABC98C5060CEF489BE8047",
    "candidate_bin": "6B72087A256515BEBAA52C2C43A0B7E1BB373F3C06B5DCB5791C7BF479BDC352",
    "runner": "F608E9F1EF018EA215BD7189E415AF7490C21605C5BAE3FA8886EEC74004903A",
    "monitor": "FF60FEEA483F6844DA7B252B8910D22D6240EABCB9C42AFAE2362122C7026920",
    "parser": "859F1E3868464676859821209C765E48B8A60BCFE2E4F8E17EDC9EBE0B963A34",
    "historical_runner": "0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B",
    "historical_hex": "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF",
    "protected_v9": "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA",
    "protected_owner_acceptance": "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
}
LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name: str) -> dict[str, Any]:
    return json.loads(PATHS[name].read_text(encoding="utf-8-sig"))


def run(command: list[str]) -> bool:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return completed.returncode == 0


def parse_powershell(paths: list[Path]) -> bool:
    quoted = ",".join("'" + str(path).replace("'", "''") + "'" for path in paths)
    script = (
        f"$paths=@({quoted}); foreach($path in $paths){{"
        "$tokens=$null; $errors=$null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors); "
        "if($errors.Count -ne 0){$errors | ForEach-Object {$_.Message}; exit 1}}"
    )
    return run(["pwsh", "-NoProfile", "-Command", script])


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    missing = [name for name, path in PATHS.items() if not path.is_file()]
    require("required_inputs", not missing, f"missing R2 evidence: {missing}")
    if missing:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"status": "NO_GO_R9_CONTINUOUS_R2_MACHINE_READY", "errors": errors}, indent=2) + "\n", encoding="utf-8")
        return 1

    hashes = {name: sha(path) for name, path in PATHS.items()}
    r1_authorization = load("r1_authorization")
    r1_incident = load("r1_incident")
    prompt = load("prompt_regression")
    static = load("static")
    launcher_static = load("launcher_static")
    direct_stage = load("direct_check_stage")
    persistent_launch = load("persistent_check_launch")
    persistent_stage = load("persistent_check_stage")
    goal = load("current_goal")
    registry = load("product_requirements")

    require("protected_expected_hashes", all(hashes[name] == expected for name, expected in EXPECTED.items()), "candidate, historical, or accepted protected identity differs")
    require(
        "r1_incident_closed_without_visual_verdict",
        r1_incident.get("status") == "NO_GO_R9_CONTINUOUS_PROMPT_SUPERVISOR_PRE_GUARD_FAILED_RESTORED_NO_RETRY"
        and r1_incident.get("acceptance") == {
            "popup_opened": False,
            "guard_created": False,
            "selected": None,
            "note": None,
            "visual_verdict": None,
            "reason": "prompt_supervisor_failed_before_guard",
        }
        and r1_incident.get("restore", {}).get("sha256") == BASELINE_SHA
        and r1_incident.get("checks", {}).get("all_run_processes_exited") is True,
        "R1 incident closure differs",
    )
    require(
        "one_shot_authorization_consumed_no_retry",
        r1_authorization.get("consumed") is True
        and r1_authorization.get("attempt_limit") == 1
        and r1_authorization.get("automatic_retries") == 0
        and r1_authorization.get("acceptance_popup_actually_opened") is False
        and r1_incident.get("authorization", {}).get("retry_allowed") is False,
        "R1 authorization is not sealed as consumed/no-retry",
    )
    require(
        "real_supervisor_path_guard_and_one_process",
        prompt.get("status") == "PASS_R9_CONTINUOUS_R2_REAL_SUPERVISOR_PATH_NO_HARDWARE"
        and prompt.get("hardware_contact") == 0
        and prompt.get("actual_popup_count") == 0
        and prompt.get("positive_proof") == {"guard_created": True, "prompt_process_start_count": 1, "actual_popup_count": 0}
        and all(prompt.get("checks", {}).values()),
        "real supervisor-path positive proof differs",
    )
    require(
        "supervisor_negatives_fail_before_process",
        prompt.get("negative_proof") == {
            "missing_qualification_processes": 0,
            "duplicate_guard_processes": 0,
            "duplicate_review_result_processes": 0,
        }
        and prompt.get("checks", {}).get("execute_rejects_simulation_injection_before_output") is True,
        "supervisor negative fixtures differ",
    )
    require(
        "static_r2_pass_and_firmware_unchanged",
        static.get("status") == "PASS_STATIC_R9_CONTINUOUS_R2_OBSERVATION"
        and static.get("hardware_contact") == 0
        and all(static.get("checks", {}).values())
        and static.get("identities", {}).get("candidate_hex_sha256") == EXPECTED["candidate_hex"]
        and static.get("identities", {}).get("candidate_elf_sha256") == EXPECTED["candidate_elf"]
        and static.get("identities", {}).get("lut_sha256") == LUT_SHA,
        "R2 static/build identity differs",
    )
    require(
        "launcher_r2_pass_and_consumed_auth_rejected",
        launcher_static.get("status") == "PASS_STATIC_R9_CONTINUOUS_R2_LAUNCHER"
        and launcher_static.get("hardware_contact") == 0
        and all(launcher_static.get("checks", {}).values())
        and launcher_static.get("checks", {}).get("consumed_authorization_rejected_before_output") is True,
        "R2 launcher static/negative gate differs",
    )
    counters = direct_stage.get("counters", {})
    require(
        "direct_runner_checkonly_zero_contact_writes_popups",
        direct_stage.get("status") == "READY_NO_HARDWARE_CONTACT"
        and direct_stage.get("mode") == "check_only"
        and direct_stage.get("hardware_contact") == 0
        and all(value == 0 for value in counters.values())
        and direct_stage.get("operator_prompt", {}).get("invoked") is False,
        "direct runner CheckOnly differs",
    )
    require(
        "persistent_checkonly_zero_contact_writes_popups",
        persistent_launch.get("status") == "READY_NO_HARDWARE_CONTACT"
        and persistent_launch.get("hardware_contact") == 0
        and persistent_launch.get("write_counter_sum") == 0
        and persistent_launch.get("popup_count") == 0
        and persistent_launch.get("authorization_artifact") is None
        and persistent_stage.get("status") == "READY_NO_HARDWARE_CONTACT"
        and persistent_stage.get("hardware_contact") == 0
        and persistent_stage.get("operator_prompt", {}).get("invoked") is False,
        "persistent launcher CheckOnly differs",
    )
    locked = persistent_launch.get("locked_hashes", {})
    require(
        "launcher_locked_current_r2_inputs",
        locked.get("runner") == hashes["runner"]
        and locked.get("candidate_hex") == hashes["candidate_hex"]
        and locked.get("static_verifier") == hashes["static_verifier"]
        and locked.get("parser") == hashes["parser"]
        and locked.get("monitor") == hashes["monitor"]
        and locked.get("prompt_supervisor") == hashes["supervisor"]
        and locked.get("historical_runner") == hashes["historical_runner"]
        and locked.get("historical_candidate_hex") == hashes["historical_hex"],
        "persistent launcher locked hashes differ from current R2 inputs",
    )
    exception = next((item for item in goal.get("requirements", []) if item.get("id") == "ssd1681_r9_continuous_observation_exception"), {})
    require(
        "registry_and_current_goal_r2_boundary",
        registry.get("status") == "PASS"
        and registry.get("requirement_ids", [])[-2:] == ["COMP-REQ-315", "COMP-REQ-316"]
        and goal.get("status") == "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING"
        and exception.get("status") == "r2_machine_closed_no_hardware_execute_forbidden_pending_root"
        and "no Execute, retry or product motion is authorized" in str(goal.get("post_safety_observation_exception")),
        "registry/current-goal R2 boundary differs",
    )

    supervisor_source = PATHS["supervisor"].read_text(encoding="utf-8")
    require(
        "exact_boolean_repair",
        "if ((Test-Path -LiteralPath $guardPath -PathType Leaf) -or\n    (Test-Path -LiteralPath $reviewPath -PathType Leaf))" in supervisor_source,
        "the exact separately-parenthesized Test-Path repair is absent",
    )
    require(
        "powershell_parse_all",
        parse_powershell([PATHS[name] for name in ("supervisor", "launcher", "runner", "monitor")]),
        "a R2 PowerShell entry point does not parse",
    )
    require(
        "registry_verifier",
        run([sys.executable, str(ROOT / "tools/verify_companion_product_requirements.py")]),
        "product registry verifier failed",
    )
    require(
        "current_goal_verifier",
        run([sys.executable, str(ROOT / "tools/verify_companion_current_goal_audit.py")]),
        "current Goal verifier failed",
    )
    diff_paths = [
        "docs/companion_product_requirements.md",
        "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1",
        "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_prompt_supervisor_r2.py",
        "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_observation.py",
        "tools/start_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1",
        "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_launcher.py",
        "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_runtime_disposition.py",
        "tools/verify_companion_current_goal_audit.py",
    ]
    require("diff_check", run(["git", "diff", "--check", "--", *diff_paths]), "R2 diff check failed")

    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous_r2_machine_ready.v1",
        "status": "MACHINE_READY_R9_CONTINUOUS_R2_PROMPT_SUPERVISOR_NO_HARDWARE_EXECUTE_FORBIDDEN_PENDING_ROOT" if not errors else "NO_GO_R9_CONTINUOUS_R2_MACHINE_READY",
        "requirement": "COMP-REQ-316",
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "actual_popup_count": 0,
        "errors": errors,
        "checks": checks,
        "repair": {
            "scope": "prompt supervisor boolean syntax and no-hardware regression only",
            "guard_condition": "separately parenthesized Test-Path guard and review checks around -or",
            "real_path_guard_created": True,
            "real_path_prompt_process_start_count": 1,
            "real_path_actual_popup_count": 0,
            "simulated_selection_is_not_owner_verdict": True,
        },
        "preserved": {
            "candidate_hex_sha256": EXPECTED["candidate_hex"],
            "candidate_elf_sha256": EXPECTED["candidate_elf"],
            "candidate_bin_sha256": EXPECTED["candidate_bin"],
            "lut_sha256": LUT_SHA,
            "historical_r9_hex_sha256": EXPECTED["historical_hex"],
            "historical_runner_sha256": EXPECTED["historical_runner"],
            "r1_popup_opened": False,
            "r1_visual_verdict": None,
            "r1_restore_sha256": BASELINE_SHA,
            "r1_retry_allowed": False,
        },
        "identities": {**hashes, "machine_ready_verifier": sha(Path(__file__).resolve())},
        "authorization": {
            "implementation": True,
            "build": True,
            "checkonly": True,
            "machine_ready": True,
            "execute": False,
            "hardware_contact": False,
            "popup_acceptance": False,
            "production_motion": False,
            "retry": False,
            "next_boundary": "root must issue a new explicit single-run authorization artifact before any Execute",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
