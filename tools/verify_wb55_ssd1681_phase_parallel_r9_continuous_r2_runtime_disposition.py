#!/usr/bin/env python3
"""Verify the consumed R9 continuous R2 owner-FAIL and exact restore closure."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".cache/validation/wb55-r9-continuous-r2-execute-20260721-r1"
ARCHIVE = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-runtime-20260721"
AUTH = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-execute-authorization-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-runtime-disposition-20260721.json"

NOTE = "呃，这样子的话就不是一个连续的球在运动，作为那个连续球运动的东西。\r\n"
NOTE_SHA = "30DDA3C9CC92110E636C9954652716EA805086DD15E889ED26B4F88D720B5698"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
MACHINE_READY_SHA = "59DA81BDCDC31AB93459BFCA6575F5A007182374912D1A476B54B747A106D5E7"
AUTH_BEFORE_SHA = "5960EFF0D0A2D58F03A07589E476D4362767E62243F79CE81933739F632A034D"

FILES = {
    "persistent-launch.json": RUN / "persistent-launch.json",
    "baseline-gate.json": RUN / "baseline-gate.json",
    "preclean-white.json": RUN / "preclean-white.json",
    "continuous-monitor-ready.json": RUN / "continuous-monitor-ready.json",
    "continuous-qualification-ready.json": RUN / "continuous-qualification-ready.json",
    "controller-state.json": RUN / "controller-state.json",
    "acceptance-prompt-invoked.json": RUN / "acceptance-prompt-invoked.json",
    "acceptance-prompt.stdout.log": RUN / "acceptance-prompt.stdout.log",
    "acceptance-prompt.stderr.log": RUN / "acceptance-prompt.stderr.log",
    "prompt-supervisor.stdout.log": RUN / "prompt-supervisor.stdout.log",
    "prompt-supervisor.stderr.log": RUN / "prompt-supervisor.stderr.log",
    "operator-note.txt": RUN / "operator-note.txt",
    "operator-review.json": RUN / "operator-review.json",
    "continuous-stop.json": RUN / "continuous-stop.json",
    "postclean-white.json": RUN / "postclean-white.json",
    "restore-gate.json": RUN / "restore-gate.json",
    "normal-resume.json": RUN / "normal-resume.json",
    "stage-run.json": RUN / "stage-run.json",
    "runner.stdout.log": RUN / "runner.stdout.log",
    "runner.stderr.log": RUN / "runner.stderr.log",
    "qualification-and-ring.json": RUN / "continuous-monitor/qualification-and-ring.json",
    "monitor-result.json": RUN / "continuous-monitor/monitor-result.json",
    "telemetry-ring.log": RUN / "continuous-monitor/telemetry-ring.log",
    "preclean-serial-raw.log": RUN / "preclean-capture/nucleo-serial-raw.log",
    "preclean-serial-summary.json": RUN / "preclean-capture/nucleo-serial-summary.json",
    "postclean-serial-raw.log": RUN / "postclean-capture/nucleo-serial-raw.log",
    "postclean-serial-summary.json": RUN / "postclean-capture/nucleo-serial-summary.json",
    "normal-serial-raw.log": RUN / "normal-capture/nucleo-serial-raw.log",
    "normal-serial-summary.json": RUN / "normal-capture/nucleo-serial-summary.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name: str) -> dict[str, Any]:
    return json.loads((ARCHIVE / name).read_text(encoding="utf-8-sig"))


def process_matches() -> list[dict[str, Any]] | None:
    script = r"""
$needle = 'wb55-r9-continuous-r2-execute-20260721-r1'
$matches = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.ProcessId -ne $PID -and $_.CommandLine -and ($_.CommandLine.Contains($needle) -or $_.Name -eq 'STM32_Programmer_CLI.exe')
} | Select-Object ProcessId, Name)
$matches | ConvertTo-Json -Compress
"""
    completed = subprocess.run(["pwsh", "-NoProfile", "-Command", script], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    if not text:
        return []
    value = json.loads(text)
    return value if isinstance(value, list) else [value]


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    missing = [name for name, source in FILES.items() if not source.is_file() or not (ARCHIVE / name).is_file()]
    require("runtime_and_archive_inputs", not missing and AUTH.is_file() and REGISTRY.is_file(), f"missing runtime/archive files: {missing}")
    if missing:
        return 1

    archive_hashes = {name: sha(ARCHIVE / name) for name in FILES}
    require("archive_byte_identical", all(FILES[name].read_bytes() == (ARCHIVE / name).read_bytes() for name in FILES), "runtime/archive byte mismatch")

    auth = json.loads(AUTH.read_text(encoding="utf-8-sig"))
    registry = REGISTRY.read_text(encoding="utf-8")
    controller = load("controller-state.json")
    monitor = load("monitor-result.json")
    guard = load("acceptance-prompt-invoked.json")
    review = load("operator-review.json")
    stop = load("continuous-stop.json")
    preclean = load("preclean-white.json")
    postclean = load("postclean-white.json")
    restore = load("restore-gate.json")
    normal = load("normal-resume.json")
    stage = load("stage-run.json")
    ring_text = (ARCHIVE / "telemetry-ring.log").read_text(encoding="utf-8", errors="replace")
    loop_matches = list(re.finditer(r"loop_iteration=(\d+).*?busy_elapsed_ms=(\d+).*?step_ok=1", ring_text))
    iterations = [int(match.group(1)) for match in loop_matches]
    busy_values = [int(match.group(2)) for match in loop_matches]

    require(
        "authorization_consumed_once",
        auth.get("consumed") is True
        and auth.get("authorization_sha256_before_consumption") == AUTH_BEFORE_SHA
        and auth.get("machine_ready_sha256") == MACHINE_READY_SHA
        and auth.get("attempt_limit") == 1
        and auth.get("automatic_retries") == 0
        and auth.get("owner_selection") == "失败"
        and auth.get("owner_note") == NOTE,
        "consumed authorization differs",
    )
    require(
        "qualification_pass",
        controller.get("status") == "PASS_MACHINE_R9_CONTINUOUS_TRACE"
        and controller.get("qualification", {}).get("activations") == 16
        and controller.get("qualification", {}).get("busy_max_ms") == 599
        and controller.get("qualification", {}).get("passed_before_loop") is True,
        "fresh 16-step qualification differs",
    )
    require(
        "bounded_contiguous_loop",
        monitor.get("status") == "STOP_REQUESTED_AFTER_QUALIFICATION"
        and monitor.get("qualified") is True
        and monitor.get("loop_records_seen") == 1060
        and monitor.get("last_iteration") == 1060
        and monitor.get("ring_peak_bytes") == 65536
        and monitor.get("ring_final_bytes") == 65536
        and monitor.get("ring_bytes_limit") == 65536
        and monitor.get("unbounded_log_created") is False
        and iterations
        and iterations == list(range(iterations[0], 1061))
        and max(busy_values) <= 600
        and all(token in ring_text for token in ("old_command=0x26", "new_command=0x24", "control=0xCF", "post_sync_command=0x24", "full_frame_writes=0", "controls_f7=0", "controls_c7=0", "controls_ff=0", "retries=0")),
        "bounded loop telemetry differs",
    )
    require(
        "single_canonical_owner_fail",
        guard.get("status") == "INVOKED_ONCE"
        and guard.get("actual_popup_count") == 1
        and guard.get("simulation_no_hardware") is False
        and review.get("status") == "NO_GO_OWNER_R9_CONTINUOUS_VISUAL"
        and review.get("selected") == "失败"
        and review.get("note") == NOTE
        and review.get("note_sha256") == NOTE_SHA
        and sha(ARCHIVE / "operator-note.txt") == NOTE_SHA
        and stop.get("reason") == "operator_selection"
        and (ARCHIVE / "acceptance-prompt.stderr.log").stat().st_size == 0
        and (ARCHIVE / "prompt-supervisor.stderr.log").stat().st_size == 0,
        "owner FAIL or single canonical prompt evidence differs",
    )
    clean_status = "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE"
    require("promptless_preclean_postclean", preclean.get("status") == clean_status and postclean.get("status") == clean_status, "pre/post clean differs")
    require(
        "exact_restore_normal_resume",
        restore.get("status") == "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES"
        and restore.get("length_bytes") == 524288
        and restore.get("baseline_sha256") == BASELINE_SHA
        and restore.get("restore_sha256") == BASELINE_SHA
        and restore.get("byte_identical") is True
        and normal.get("status") == "PASS_APPLICATION_RESUMED_AFTER_BACKUP"
        and normal.get("ready_after_boot") is True,
        "restore or normal resume differs",
    )
    counters = stage.get("counters", {})
    require(
        "stage_counts_and_no_retry",
        stage.get("status") == "NO_GO_R9_CONTINUOUS_VISUAL_NOT_PASSED_RESTORED"
        and counters.get("panel_refresh_commands") == 1076
        and counters.get("panel_busy_waits") == 1076
        and counters.get("panel_writes") == 3228
        and counters.get("automatic_retries") == 0
        and stage.get("popup_policy", {}).get("visual_acceptance") == 1
        and stage.get("popup_policy", {}).get("pre_execute") == 0
        and stage.get("popup_policy", {}).get("cleanup") == 0
        and stage.get("popup_policy", {}).get("recovery_or_fault_acknowledgement") == 0,
        "stage counters or popup policy differ",
    )
    require("registry_verbatim_disposition", registry.count("| COMP-REQ-318 |") == 1 and NOTE.strip() in registry, "COMP-REQ-318 verbatim owner disposition is absent")
    matches = process_matches()
    require("all_run_processes_exited", matches == [], "run/programmer process remains or process audit failed")

    result = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous.r2_runtime_disposition.v1",
        "status": "NO_GO_R9_CONTINUOUS_R2_OWNER_VISUAL_FAILED_RESTORED_NO_RETRY" if not errors else "NO_GO_R9_CONTINUOUS_R2_RUNTIME_ARCHIVE_INVALID",
        "requirements": ["COMP-REQ-313", "COMP-REQ-316", "COMP-REQ-317", "COMP-REQ-318"],
        "errors": errors,
        "checks": checks,
        "qualification": {"activations": 16, "busy_max_ms": 599},
        "loop": {"records": 1060, "last_iteration": 1060, "archived_tail_first_iteration": iterations[0] if iterations else None, "archived_tail_records": len(iterations), "archived_tail_busy_max_ms": max(busy_values) if busy_values else None, "ring_bytes": 65536},
        "operator": {"selected": "失败", "note": NOTE, "note_sha256": NOTE_SHA, "popup_count": 1},
        "restore": {"status": restore.get("status"), "bytes": 524288, "sha256": BASELINE_SHA, "normal_resume_status": normal.get("status")},
        "authorization": {"consumed": True, "retry_allowed": False, "sha256_before_consumption": AUTH_BEFORE_SHA, "current_sha256": sha(AUTH)},
        "motion_or_promotion_entered": False,
        "process_matches": [],
        "archive_root": ARCHIVE.relative_to(ROOT).as_posix(),
        "archive_hashes": archive_hashes,
        "next_boundary": "new R10 payload-topology contract and MACHINE_READY only; no hardware Execute without root authorization",
        "tool_sha256": sha(Path(__file__).resolve()),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
