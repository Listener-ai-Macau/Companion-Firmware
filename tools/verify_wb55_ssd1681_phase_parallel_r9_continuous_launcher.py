#!/usr/bin/env python3
"""Fail-closed CheckOnly and negative audit for the R9 continuous launcher."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-launcher-static-20260721.json"
CACHE = ROOT / ".cache/validation"
CONSUMED_AUTHORIZATION = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-execute-authorization-20260721.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def invoke(args: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(LAUNCHER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        timeout=150,
    )
    return {
        "args": args,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def main() -> int:
    source = LAUNCHER.read_text(encoding="utf-8")
    positive_root = CACHE / "wb55-r9-continuous-r2-launcher-verifier-positive"
    lifecycle_root = CACHE / "wb55-r9-continuous-r2-launcher-verifier-child-failure"
    unauthorized_root = CACHE / "wb55-r9-continuous-r2-launcher-verifier-unauthorized"
    consumed_root = CACHE / "wb55-r9-continuous-r2-launcher-verifier-consumed"
    mixed_root = CACHE / "wb55-r9-continuous-r2-launcher-verifier-mixed"
    for path in (positive_root, lifecycle_root, unauthorized_root, consumed_root, mixed_root):
        if path.exists():
            shutil.rmtree(path)

    positive = invoke(["-CheckOnly", "-OutRoot", str(positive_root)])
    unauthorized = invoke(["-Execute", "-OutRoot", str(unauthorized_root)])
    consumed = invoke(["-Execute", "-AuthorizationArtifact", str(CONSUMED_AUTHORIZATION), "-OutRoot", str(consumed_root)])
    mixed = invoke(["-CheckOnly", "-Execute", "-OutRoot", str(mixed_root)])
    lifecycle = invoke(["-CheckOnly", "-LifecycleSelfTestFailure", "-OutRoot", str(lifecycle_root)])
    reuse = invoke(["-CheckOnly", "-OutRoot", str(positive_root)])

    positive_artifact_path = positive_root / "persistent-launch.json"
    positive_stage_path = positive_root / "stage-run.json"
    lifecycle_artifact_path = lifecycle_root / "persistent-launch.json"
    positive_artifact = json.loads(positive_artifact_path.read_text(encoding="utf-8-sig")) if positive_artifact_path.is_file() else {}
    positive_stage = json.loads(positive_stage_path.read_text(encoding="utf-8-sig")) if positive_stage_path.is_file() else {}
    lifecycle_artifact = json.loads(lifecycle_artifact_path.read_text(encoding="utf-8-sig")) if lifecycle_artifact_path.is_file() else {}

    locked_section = re.search(r"\$lockedHashes = \[ordered\]@\{(.*?)\n\}", source, re.DOTALL)
    locked = dict(re.findall(r"^\s+([a-z_]+)\s*=\s*\"([0-9A-F]{64})\"", locked_section.group(1), re.MULTILINE)) if locked_section else {}
    path_names = {
        "runner": "tools/run_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1",
        "candidate_hex": "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.hex",
        "static_verifier": "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_observation.py",
        "parser": "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_log.py",
        "monitor": "tools/monitor_wb55_ssd1681_phase_parallel_r9_continuous.ps1",
        "prompt_supervisor": "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1",
        "historical_runner": "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1",
        "historical_candidate_hex": "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex",
        "workbench": "docs/validation/companion-ssd1681-phase-parallel-r9-workbench-20260721.json",
    }
    locked_actual = {name: sha(ROOT / relative) for name, relative in path_names.items()}
    checks = {
        "locked_hashes_match_every_input": locked == locked_actual,
        "positive_checkonly_exit_zero": positive["exit_code"] == 0,
        "positive_stage_ready": positive_stage.get("status") == "READY_NO_HARDWARE_CONTACT",
        "positive_zero_hardware": positive_artifact.get("hardware_contact") == 0 and positive_stage.get("hardware_contact") == 0,
        "positive_zero_writes": positive_artifact.get("write_counter_sum") == 0,
        "positive_zero_popup_invocations": positive_artifact.get("popup_count") == 0 and positive_stage.get("operator_prompt", {}).get("invoked") is False,
        "one_acceptance_policy_preserved": positive_stage.get("popup_policy", {}).get("visual_acceptance") == 1 and positive_stage.get("operator_prompt", {}).get("required") is True,
        "missing_authorization_rejected_before_output": unauthorized["exit_code"] != 0 and not unauthorized_root.exists(),
        "consumed_authorization_rejected_before_output": consumed["exit_code"] != 0 and not consumed_root.exists() and "invalid or consumed" in str(consumed["stderr"]),
        "mixed_check_execute_rejected_before_output": mixed["exit_code"] != 0 and not mixed_root.exists(),
        "child_failure_propagated": lifecycle["exit_code"] != 0 and lifecycle_artifact.get("status") == "NO_GO_CHECK_CHILD_EXIT",
        "child_failure_zero_hardware": lifecycle_artifact.get("hardware_contact") == 0,
        "output_reuse_rejected": reuse["exit_code"] != 0,
        "execute_requires_new_root_after_comp_req_316": "AUTHORIZED_R9_CONTINUOUS_OBSERVATION_ONCE" in source and "COMP-REQ-316 R2 MACHINE_READY" in source and "consumed -ne $false" in source,
        "detached_execute_has_durable_streams": "durable_stdout_redirected = $true" in source and "durable_stderr_redirected = $true" in source,
        "launcher_never_calls_prompt": "operator-prompt" not in source,
    }
    errors = [name for name, passed in checks.items() if not passed]
    result = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous_r2_launcher_static.v1",
        "status": "PASS_STATIC_R9_CONTINUOUS_R2_LAUNCHER" if not errors else "NO_GO_R9_CONTINUOUS_R2_LAUNCHER",
        "requirement": "COMP-REQ-316",
        "hardware_contact": 0,
        "errors": errors,
        "checks": checks,
        "launcher_sha256": sha(LAUNCHER),
        "locked_hashes": locked,
        "positive_checkonly": {
            "exit_code": positive["exit_code"],
            "artifact": {
                "status": positive_artifact.get("status"),
                "hardware_contact": positive_artifact.get("hardware_contact"),
                "write_counter_sum": positive_artifact.get("write_counter_sum"),
                "popup_count": positive_artifact.get("popup_count"),
                "locked_hashes": positive_artifact.get("locked_hashes"),
            },
            "stage_status": positive_stage.get("status"),
        },
        "negative_cases": {
            "missing_authorization": {"exit_code_nonzero": unauthorized["exit_code"] != 0, "output_created": unauthorized_root.exists()},
            "consumed_authorization": {"exit_code_nonzero": consumed["exit_code"] != 0, "output_created": consumed_root.exists()},
            "mixed_modes": {"exit_code_nonzero": mixed["exit_code"] != 0, "output_created": mixed_root.exists()},
            "child_failure": {"exit_code_nonzero": lifecycle["exit_code"] != 0, "status": lifecycle_artifact.get("status"), "hardware_contact": lifecycle_artifact.get("hardware_contact")},
            "reuse": {"exit_code_nonzero": reuse["exit_code"] != 0},
        },
        "authorization": "COMP-REQ-316 R2 MACHINE_READY only; no Execute",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
