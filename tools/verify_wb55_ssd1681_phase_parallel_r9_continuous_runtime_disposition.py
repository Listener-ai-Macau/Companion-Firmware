#!/usr/bin/env python3
"""Close the consumed R9 continuous R1 attempt without inventing a visual verdict."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-runtime-20260721"
AUTHORIZATION = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-execute-authorization-20260721.json"
MACHINE_READY = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-machine-ready-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
REGISTRY_FIXTURE = ROOT / "docs/validation/companion-product-requirements.json"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-runtime-disposition-20260721.json"

MACHINE_READY_SHA = "68BA95CE95BF4FA3D17847B1A3731E26012CAE5A166B4156C2B44457B139E170"
AUTHORIZATION_SHA_BEFORE_CONSUMPTION = "8183D7803AC4177B86042805BD8CB98912FE4DC72674E88D8F8B87E5C5064306"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
HEX_SHA = "3B416BFF08B630D23BDB6107B2C17DFE9FBBFAAA7D5CFBCA5063AE68E62B79C5"
LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"

EXPECTED_HASHES = {
    "continuous-emergency-stop.json": "9675375441218D5BCF358BE15FCD7C9D362C1C9E09481DAF680C44CC8D30CF55",
    "continuous-qualification-ready.json": "24CD22E2BF0114308253EEE850492B0C9E5B20A1E53B750301312968DA5B7BA6",
    "controller-state.json": "558A375AE7FCC33BAF25F88F5FE466DB47927BFFF77BEFECB3500E2C42393A0B",
    "final-ring-parse.json": "B5297629734F94BA77664B03B7E14B04581D7B5884C80371F8B0F9B209289085",
    "monitor-result.json": "8E31CDF93D2729210279C42C42A353B5CC9E541357D377D8DD7A466B18773995",
    "normal-resume.json": "048DE073BA860A41B481BB61F360DEE091BE551BD9CE974758BCBFCC679956EC",
    "persistent-launch.json": "AAE554D7DA0817A38E014F0CEE78A6E9F2EC5B386A24BFF4829D9B9E7FDCEF59",
    "postclean-white.json": "64D33D192CA81C59AA440658939AC75E18C8F1997CCED8B02B9200233F042A49",
    "preclean-white.json": "64D33D192CA81C59AA440658939AC75E18C8F1997CCED8B02B9200233F042A49",
    "prompt-supervisor.stderr.log": "2570645DCFC2D4A05D8DB590A05C3677CD3BE42798B5986A711D10738CE63716",
    "prompt-supervisor.stdout.log": "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
    "qualification-and-ring.json": "558A375AE7FCC33BAF25F88F5FE466DB47927BFFF77BEFECB3500E2C42393A0B",
    "restore-gate.json": "EC2A9488D09FE7E53CE91F7D5F9D029A9F8FA09ABC9B508A8533AE10AC5226D7",
    "stage-run.json": "0A5823EE2B95E12BF3883F2F32C29242683CDD021BC5B0373D8BB60D22866F3E",
    "telemetry-ring.log": "3C7C787B8A85F03F203BF26551AAB5249A16272236EFF38F4CFD77C073DCBD19",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name: str) -> dict[str, Any]:
    return json.loads((ARCHIVE / name).read_text(encoding="utf-8-sig"))


def process_audit() -> dict[str, Any]:
    script = r"""
$needle = 'wb55-r9-continuous-execute-20260721-r1'
$known = @(32136, 24316)
$matches = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine.Contains($needle)
} | Select-Object ProcessId, Name, CommandLine)
$knownAlive = @($known | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
[ordered]@{ command_line_matches = $matches; known_pids_alive = $knownAlive } | ConvertTo-Json -Depth 5 -Compress
"""
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed.returncode != 0:
        return {"audit_error": (completed.stdout + completed.stderr).strip(), "command_line_matches": None, "known_pids_alive": None}
    return json.loads(completed.stdout)


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    required = [AUTHORIZATION, MACHINE_READY, REGISTRY, REGISTRY_FIXTURE, *(ARCHIVE / name for name in EXPECTED_HASHES)]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
    require("required_inputs", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"status": "NO_GO_R9_CONTINUOUS_R1_ARCHIVE_INVALID", "errors": errors}, indent=2) + "\n", encoding="utf-8")
        return 1

    actual_hashes = {name: sha(ARCHIVE / name) for name in EXPECTED_HASHES}
    require("archive_hashes_exact", actual_hashes == EXPECTED_HASHES, "archived runtime bytes differ")

    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8-sig"))
    machine_ready = json.loads(MACHINE_READY.read_text(encoding="utf-8-sig"))
    registry_fixture = json.loads(REGISTRY_FIXTURE.read_text(encoding="utf-8-sig"))
    registry = REGISTRY.read_text(encoding="utf-8")
    ring = load("final-ring-parse.json")
    monitor = load("monitor-result.json")
    stage = load("stage-run.json")
    restore = load("restore-gate.json")
    normal = load("normal-resume.json")
    launch = load("persistent-launch.json")
    qualification = load("continuous-qualification-ready.json")
    emergency = load("continuous-emergency-stop.json")
    preclean = load("preclean-white.json")
    postclean = load("postclean-white.json")
    prompt_stderr = (ARCHIVE / "prompt-supervisor.stderr.log").read_text(encoding="utf-8-sig")

    require(
        "authorization_consumed_once",
        authorization.get("consumed") is True
        and authorization.get("attempt_limit") == 1
        and authorization.get("automatic_retries") == 0
        and authorization.get("authorization_sha256_before_consumption") == AUTHORIZATION_SHA_BEFORE_CONSUMPTION
        and authorization.get("consumed_result") == "NO_GO_R9_CONTINUOUS_VISUAL_NOT_PASSED_RESTORED"
        and authorization.get("acceptance_popup_actually_opened") is False
        and authorization.get("owner_selection") is None
        and authorization.get("owner_note") is None,
        "one-shot authorization consumption differs",
    )
    require(
        "sealed_machine_identity",
        sha(MACHINE_READY) == MACHINE_READY_SHA
        and machine_ready.get("identities", {}).get("candidate_hex") == HEX_SHA
        and machine_ready.get("contract", {}).get("lut_sha256") == LUT_SHA
        and launch.get("locked_hashes", {}).get("candidate_hex") == HEX_SHA,
        "sealed MACHINE_READY/HEX/LUT identity differs",
    )
    require(
        "registry_incident_unique",
        registry.count("| COMP-REQ-315 |") == 1
        and registry_fixture.get("status") == "PASS"
        and "COMP-REQ-315" in registry_fixture.get("requirement_ids", []),
        "COMP-REQ-315 incident steering is not uniquely registered",
    )
    require(
        "qualification_and_loop_observed",
        ring.get("status") == "PASS_MACHINE_R9_CONTINUOUS_TRACE"
        and ring.get("qualification", {}).get("activations") == 16
        and ring.get("qualification", {}).get("busy_max_ms") == 599
        and ring.get("qualification", {}).get("passed_before_loop") is True
        and ring.get("loop", {}).get("records_in_ring") == 1
        and ring.get("loop", {}).get("first_iteration") == 1
        and ring.get("loop", {}).get("last_iteration") == 1
        and ring.get("loop", {}).get("busy_max_ms") == 597
        and not ring.get("errors"),
        "qualification or bounded loop evidence differs",
    )
    require(
        "bounded_telemetry",
        monitor.get("qualified") is True
        and monitor.get("loop_records_seen") == 1
        and monitor.get("ring_bytes_limit") == 65536
        and monitor.get("ring_peak_bytes") == 10736
        and monitor.get("ring_final_bytes") == 10736
        and monitor.get("unbounded_log_created") is False
        and (ARCHIVE / "telemetry-ring.log").stat().st_size == 10736,
        "telemetry ring is not the sealed bounded capture",
    )
    require(
        "exact_prompt_supervisor_failure",
        "prompt.ps1:126" in prompt_stderr
        and "Cannot bind parameter because parameter 'LiteralPath' is specified more than once" in prompt_stderr
        and (ARCHIVE / "prompt-supervisor.stdout.log").stat().st_size == 0,
        "prompt-supervisor failure signature differs",
    )
    absent_acceptance = all(not (ARCHIVE / name).exists() for name in ("acceptance-prompt-invoked.json", "operator-review.json", "operator-note.txt"))
    require("no_popup_or_operator_result", absent_acceptance, "a guard, operator review, or note unexpectedly exists")
    require(
        "fail_closed_stop",
        monitor.get("status") == "NO_GO_EMERGENCY_STOP"
        and monitor.get("popup_count") == 0
        and emergency.get("reason") == "runner_fail_closed_cleanup"
        and stage.get("status") == "NO_GO_R9_CONTINUOUS_VISUAL_NOT_PASSED_RESTORED",
        "fail-closed runtime disposition differs",
    )
    clean_status = "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE"
    require(
        "promptless_preclean_postclean",
        preclean.get("status") == clean_status and postclean.get("status") == clean_status,
        "dual-plane preclean or postclean differs",
    )
    require(
        "exact_restore_and_normal_resume",
        restore.get("status") == "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES"
        and restore.get("length_bytes") == 524288
        and restore.get("baseline_sha256") == BASELINE_SHA
        and restore.get("restore_sha256") == BASELINE_SHA
        and restore.get("byte_identical") is True
        and normal.get("status") == "PASS_APPLICATION_RESUMED_AFTER_BACKUP"
        and normal.get("ready_after_boot") is True,
        "exact application restore or normal resume differs",
    )
    require(
        "qualification_signal_identity",
        qualification.get("status") == "PASS_INITIAL_16_READY_FOR_CONCURRENT_ACCEPTANCE"
        and qualification.get("process_id") == 24316,
        "qualification-ready signal differs",
    )

    processes = process_audit()
    require(
        "all_run_processes_exited",
        not processes.get("audit_error")
        and processes.get("command_line_matches") == []
        and processes.get("known_pids_alive") == [],
        "a sealed-run process remains or the process audit failed",
    )

    registry_check = subprocess.run(
        [sys.executable, str(ROOT / "tools/verify_companion_product_requirements.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    require("registry_verifier_pass", registry_check.returncode == 0, "product registry verifier failed")

    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous.r1_runtime_disposition.v1",
        "status": "NO_GO_R9_CONTINUOUS_PROMPT_SUPERVISOR_PRE_GUARD_FAILED_RESTORED_NO_RETRY" if not errors else "NO_GO_R9_CONTINUOUS_R1_ARCHIVE_INVALID",
        "requirements": ["COMP-REQ-313", "COMP-REQ-314", "COMP-REQ-315"],
        "errors": errors,
        "checks": checks,
        "machine_qualification": {"status": ring.get("status"), "activations": 16, "busy_max_ms": 599},
        "continuous_loop": {"records": 1, "busy_max_ms": 597, "ring_bytes": 10736, "ring_limit_bytes": 65536},
        "acceptance": {"popup_opened": False, "guard_created": False, "selected": None, "note": None, "visual_verdict": None, "reason": "prompt_supervisor_failed_before_guard"},
        "restore": {"status": restore.get("status"), "bytes": 524288, "sha256": BASELINE_SHA, "normal_resume_status": normal.get("status")},
        "authorization": {"consumed": True, "retry_allowed": False, "original_sha256": AUTHORIZATION_SHA_BEFORE_CONSUMPTION, "current_sha256": sha(AUTHORIZATION)},
        "process_audit": processes,
        "archive_root": ARCHIVE.relative_to(ROOT).as_posix(),
        "archive_hashes": actual_hashes,
        "next_boundary": "R2 implementation/build/CheckOnly/MACHINE_READY only; any Execute requires a new explicit root authorization",
        "protected_hashes": {
            "machine_ready_sha256": sha(MACHINE_READY),
            "candidate_hex_sha256": HEX_SHA,
            "lut_sha256": LUT_SHA,
            "registry_sha256": sha(REGISTRY),
            "registry_fixture_sha256": sha(REGISTRY_FIXTURE),
            "disposition_tool_sha256": sha(Path(__file__).resolve()),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
