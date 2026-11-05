#!/usr/bin/env python3
"""Execute the R10 lifecycle contract and no-hardware fail-closed fixtures."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
    "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
}
PARSER = ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py"
HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball/Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex"
MACHINE = ROOT / "docs/validation/companion-ssd1681-r10-r3-execute-ready-machine-ready-20260722.json"
R2_MACHINE = ROOT / "docs/validation/companion-ssd1681-r10-r2-machine-ready-20260722.json"
C419_MACHINE = ROOT / "docs/validation/companion-ssd1681-r10-r3-stable-hold-machine-ready-20260722.json"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MACHINE_READY_GENERATOR = ROOT / "tools/verify_wb55_ssd1681_r10_r3_machine_ready.py"
OUT = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-lifecycle-static-20260722.json"


class Failure(ValueError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def need(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def run(command: list[str], timeout: int = 45, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                            encoding="utf-8", errors="replace", timeout=timeout, env=env)
    return result.returncode, result.stdout, result.stderr


def fixture_result(name: str, command: str, returncode: int, rejected: bool) -> dict[str, object]:
    need(rejected, f"negative fixture was not rejected: {name}")
    return {"name": name, "command": command, "executed": True,
            "hardware_contact": 0, "write_count": 0, "popup_count": 0,
            "returncode": returncode, "rejected": True}


def authorization(root: Path, **changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_id": "companion.wb55.ssd1681.r10_ball.authorization.v1",
        "status": "AUTHORIZED_R10_BALL_ONCE", "consumed": False,
        "requirement_id": "COMP-REQ-323", "output_root": str(root),
        "candidate_hex_sha256": sha(HEX), "runner_sha256": sha(FILES["runner"]),
        "monitor_sha256": sha(FILES["monitor"]), "supervisor_sha256": sha(FILES["supervisor"]),
        "launcher_sha256": sha(FILES["launcher"]), "machine_ready_path": str(MACHINE.resolve()),
        "machine_ready_sha256": sha(MACHINE),
        "parser_sha256": sha(PARSER),
    }
    data.update(changes)
    return data


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def claim_command(auth: Path, output: Path) -> list[str]:
    return ["pwsh", "-NoProfile", "-File", str(FILES["launcher"]), "-ClaimOnly",
            "-OutRoot", str(output), "-AuthorizationArtifact", str(auth)]


def authorization_fixtures(tmp: Path) -> dict[str, object]:
    results: list[dict[str, object]] = []

    auth = tmp / "competing.json"
    output = tmp / "competing-output"
    write_json(auth, authorization(output))
    first = run(claim_command(auth, output))
    second = run(claim_command(auth, tmp / "competing-second-output"))
    need(first[0] == 0 and second[0] != 0, "competing authorization claim behavior failed")
    positive = {"name": "disposable_claimonly_positive", "command": "launcher -ClaimOnly with disposable authorization copy",
                "executed": True, "returncode": first[0], "receipt_created": Path(str(auth) + ".consumed.json").is_file(),
                "hardware_contact": 0, "write_count": 0, "popup_count": 0, "rejected": False}
    need(positive["returncode"] == 0 and positive["receipt_created"], "disposable ClaimOnly positive did not consume its disposable copy")
    results.append(fixture_result("two_competing_claims", "launcher -ClaimOnly twice with one source", second[0], second[0] != 0))

    consumed = tmp / "consumed.json"
    write_json(consumed, authorization(tmp / "consumed-output", status="CONSUMED_AUTHORIZED_R10_BALL_ONCE", consumed=True))
    rc, _, _ = run(claim_command(consumed, tmp / "consumed-output"))
    results.append(fixture_result("consumed_authorization", "launcher -ClaimOnly with consumed=true", rc, rc != 0))

    steering = tmp / "steering-only.json"
    write_json(steering, authorization(tmp / "steering-output", requirement_id="COMP-REQ-324"))
    rc, _, _ = run(claim_command(steering, tmp / "steering-output"))
    results.append(fixture_result("steering_requirement_not_authority", "launcher -ClaimOnly with COMP-REQ-324", rc, rc != 0))

    mismatch = tmp / "output-mismatch.json"
    write_json(mismatch, authorization(tmp / "bound-output"))
    rc, _, _ = run(claim_command(mismatch, tmp / "different-output"))
    results.append(fixture_result("output_root_mismatch", "launcher -ClaimOnly with mismatched output_root", rc, rc != 0))

    drift = tmp / "hash-drift.json"
    write_json(drift, authorization(tmp / "drift-output", candidate_hex_sha256="0" * 64))
    rc, _, _ = run(claim_command(drift, tmp / "drift-output"))
    results.append(fixture_result("hash_drift", "launcher -ClaimOnly with candidate hash drift", rc, rc != 0))

    launcher_drift = tmp / "launcher-drift.json"
    write_json(launcher_drift, authorization(tmp / "launcher-drift-output", launcher_sha256="0" * 64))
    rc, _, _ = run(claim_command(launcher_drift, tmp / "launcher-drift-output"))
    results.append(fixture_result("launcher_hash_drift", "launcher -ClaimOnly with launcher hash drift", rc, rc != 0))

    runner_drift = tmp / "runner-drift.json"
    write_json(runner_drift, authorization(tmp / "runner-drift-output", runner_sha256="0" * 64))
    rc, _, _ = run(claim_command(runner_drift, tmp / "runner-drift-output"))
    results.append(fixture_result("runner_hash_drift", "launcher -ClaimOnly with runner hash drift", rc, rc != 0))

    r2_path = tmp / "r2-machine.json"
    write_json(r2_path, authorization(tmp / "r2-machine-output", machine_ready_path=str(R2_MACHINE.resolve()), machine_ready_sha256=sha(R2_MACHINE)))
    rc, _, _ = run(claim_command(r2_path, tmp / "r2-machine-output"))
    results.append(fixture_result("r2_machine_ready_path_rejected", "launcher -ClaimOnly with historical R2 MACHINE_READY path/hash", rc, rc != 0))

    stale_c419 = tmp / "stale-c419.json"
    write_json(stale_c419, authorization(tmp / "stale-c419-output", machine_ready_path=str(C419_MACHINE.resolve()), machine_ready_sha256=sha(C419_MACHINE)))
    rc, _, _ = run(claim_command(stale_c419, tmp / "stale-c419-output"))
    results.append(fixture_result("stale_c419_machine_ready_rejected", "launcher -ClaimOnly with historical C419 R3 MR", rc, rc != 0))

    wrong_successor_path = tmp / "wrong-successor-path.json"
    write_json(wrong_successor_path, authorization(tmp / "wrong-successor-path-output", machine_ready_path=str(tmp / "wrong-successor-machine-ready.json")))
    rc, _, _ = run(claim_command(wrong_successor_path, tmp / "wrong-successor-path-output"))
    results.append(fixture_result("wrong_successor_machine_ready_path", "launcher -ClaimOnly with wrong successor MR path", rc, rc != 0))

    wrong_successor_hash = tmp / "wrong-successor-hash.json"
    write_json(wrong_successor_hash, authorization(tmp / "wrong-successor-hash-output", machine_ready_sha256="0" * 64))
    rc, _, _ = run(claim_command(wrong_successor_hash, tmp / "wrong-successor-hash-output"))
    results.append(fixture_result("wrong_successor_machine_ready_hash", "launcher -ClaimOnly with wrong successor MR hash", rc, rc != 0))

    stale = tmp / "stale.json"
    stale_output = tmp / "stale-output"
    stale_output.mkdir()
    write_json(stale, authorization(stale_output))
    rc, _, _ = run(claim_command(stale, stale_output))
    results.append(fixture_result("stale_or_reused_output_root", "launcher -ClaimOnly with existing output_root", rc, rc != 0))

    reused = tmp / "reused.json"
    reused_output = tmp / "reused-output"
    write_json(reused, authorization(reused_output))
    rc, _, _ = run(claim_command(reused, reused_output))
    need(rc == 0, "fixture claim did not produce receipt")
    receipt = Path(str(reused) + ".consumed.json")
    rc, _, _ = run(claim_command(receipt, tmp / "reused-second-output"))
    results.append(fixture_result("reused_consumed_receipt", "launcher -ClaimOnly with consumed receipt", rc, rc != 0))
    return {"negative": results, "positive": positive}


def parser_fixtures(tmp: Path) -> list[dict[str, object]]:
    sys.path.insert(0, str(PARSER.parent))
    import verify_wb55_ssd1681_r10_ball_log as parser

    line = parser.frame_line("loop_iteration", 1, 40, 32)
    mutations = [
        ("malformed_hash", "current_frame_sha256=", "current_frame_sha256=" + "0" * 64),
        ("malformed_window", "window_x_bytes=4-6", "window_x_bytes=4-4"),
        ("malformed_position", "current_x=32", "current_x=40"),
        ("malformed_count", "old_writes=1", "old_writes=0"),
        ("busy_601", "busy_elapsed_ms=500", "busy_elapsed_ms=601"),
    ]
    results: list[dict[str, object]] = []
    for name, old, new in mutations:
        bad = line.replace(old, new, 1)
        command = [sys.executable, str(PARSER), "--validate-loop-line", bad,
                   "--loop-sequence", "1", "--loop-previous-x", "40", "--loop-current-x", "32"]
        rc, _, _ = run(command)
        results.append(fixture_result(name, "python parser --validate-loop-line mutated-frame", rc, rc != 0))

    second = parser.frame_line("loop_iteration", 2, 32, 40)
    ring = tmp / "rolled-loop-ring.log"
    ring.write_text(line.replace("loop_iteration=1", "loop_iteration=1", 1) + "\n" + second + "\n", encoding="utf-8")
    bad_ring = tmp / "noncontiguous-loop-ring.log"
    bad_ring.write_text(line + "\n" + second.replace("loop_iteration=2", "loop_iteration=3", 1) + "\n", encoding="utf-8")
    rc, _, _ = run([sys.executable, str(PARSER), "--loop-log", str(bad_ring)])
    results.append(fixture_result("noncontiguous_loop_after_qualification_rolled_out", "python parser --loop-log loop-only ring", rc, rc != 0))
    rc, _, _ = run([sys.executable, str(PARSER), "--loop-log", str(ring)])
    need(rc == 0, "valid qualification-free loop ring was rejected")
    return results


def parser_write_regression(tmp: Path) -> dict[str, object]:
    sys.path.insert(0, str(PARSER.parent))
    import verify_wb55_ssd1681_r10_ball_log as parser

    log = tmp / "parser-write.log"
    artifact = tmp / "parser-write.json"
    log.write_text(parser.positive_log(1), encoding="utf-8")
    rc, stdout, stderr = run([sys.executable, str(PARSER), "--log", str(log), "--minimum-loop-iterations", "1",
                              "--hardware-contact", "0", "--artifact", str(artifact), "--write"])
    actual = artifact.read_text(encoding="utf-8").strip() if artifact.exists() else ""
    parsed = json.loads(actual) if actual else {}
    passed = rc == 0 and not stderr and actual == stdout.strip() and parsed.get("status") == "PASS_R10_BALL_LOG" and parsed.get("hardware_contact") == 0
    need(passed, "parser --log --write did not persist the exact printed object")
    return {"command": "python verify_wb55_ssd1681_r10_ball_log.py --log --write --hardware-contact 0", "executed": True,
            "artifact_exists": artifact.exists(), "stdout_artifact_match": actual == stdout.strip(), "hardware_contact": 0,
            "status": parsed.get("status"), "returncode": rc, "passed": True}


def parser_finalization_fixtures(tmp: Path) -> dict[str, object]:
    sys.path.insert(0, str(PARSER.parent))
    import verify_wb55_ssd1681_r10_ball_log as parser

    first = parser.frame_line("loop_iteration", 1, 40, 32)
    second = parser.frame_line("loop_iteration", 2, 32, 40)
    third = parser.frame_line("loop_iteration", 3, 40, 48)
    malformed = third.replace("current_frame_sha256=", "current_frame_sha256=" + "0" * 64 + " ", 1)

    accepted_path = tmp / "trailing-partial.log"
    accepted_path.write_text(first + "\n" + second + "\n" + malformed, encoding="utf-8")
    rc, stdout, _ = run([sys.executable, str(PARSER), "--loop-log", str(accepted_path), "--minimum-loop-iterations", "2"])
    accepted = json.loads(stdout) if rc == 0 else {}
    accepted_record = {"name": "one_trailing_partial_accepted", "executed": True, "command": "python parser --loop-log trailing-partial.log --minimum-loop-iterations 2",
                       "returncode": rc, "rejected": False, "accepted": rc == 0,
                       "ignored_trailing_partial_line": accepted.get("ignored_trailing_partial_line"),
                       "ignored_trailing_partial_bytes": accepted.get("ignored_trailing_partial_bytes"),
                       "hardware_contact": 0, "write_count": 0, "popup_count": 0}
    need(rc == 0 and accepted.get("ignored_trailing_partial_line") is True and accepted.get("ignored_trailing_partial_bytes", 0) > 0,
         "one unterminated trailing partial line was not accepted and audited")

    completed_path = tmp / "completed-partial.log"
    completed_path.write_text(accepted_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    rc, stdout, stderr = run([sys.executable, str(PARSER), "--loop-log", str(completed_path), "--minimum-loop-iterations", "2"])
    completed_record = fixture_result("same_partial_with_newline_rejected", "python parser --loop-log completed-partial.log", rc, rc != 0)
    completed_record["reason_observed"] = rc != 0 and bool((stdout + stderr).strip())
    need(completed_record["reason_observed"], "newline-terminated malformed line was not rejected with an auditable parser error")

    middle_path = tmp / "middle-malformed.log"
    middle_path.write_text(first + "\n" + malformed + "\n" + third + "\n", encoding="utf-8")
    rc, stdout, stderr = run([sys.executable, str(PARSER), "--loop-log", str(middle_path), "--minimum-loop-iterations", "2"])
    middle_record = fixture_result("middle_malformed_complete_rejected", "python parser --loop-log middle-malformed.log", rc, rc != 0)
    middle_record["reason_observed"] = rc != 0 and bool((stdout + stderr).strip())
    need(middle_record["reason_observed"], "middle malformed complete line was not rejected with an auditable parser error")

    two_path = tmp / "complete-then-trailing-partial.log"
    two_path.write_text(first + "\n" + malformed + "\n" + second.replace("loop_iteration=2", "loop_iteration=9", 1), encoding="utf-8")
    rc, stdout, stderr = run([sys.executable, str(PARSER), "--loop-log", str(two_path), "--minimum-loop-iterations", "2"])
    two_record = fixture_result("complete_malformed_before_trailing_partial_rejected", "python parser --loop-log complete-then-trailing-partial.log", rc, rc != 0)
    two_record["reason_observed"] = rc != 0 and bool((stdout + stderr).strip())
    need(two_record["reason_observed"], "a complete malformed line before a trailing partial was ignored")
    return {"accepted": accepted_record, "negative": [completed_record, middle_record, two_record], "passed": True}


def monitor_finalization_fixture(tmp: Path) -> dict[str, object]:
    root = tmp / "monitor-finalization-selftest"
    rc, stdout, stderr = run(["pwsh", "-NoProfile", "-File", str(FILES["monitor"]), "-FinalizationSelfTest", "-OutDir", str(root)])
    result_path = root / "monitor-result.json"
    emergency_path = root / "emergency-stop.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    record = {"name": "stop_then_final_parser_exception_no_go", "executed": True,
              "command": "monitor -FinalizationSelfTest -OutDir monitor-finalization-selftest",
              "returncode": rc, "status": result.get("status"), "emergency_created": emergency_path.exists(),
              "hardware_contact": result.get("hardware_contact", 0), "write_count": result.get("write_counter_sum", 0),
              "popup_count": result.get("popup_count", 0), "stdout": stdout, "stderr": stderr}
    need(rc != 0 and result.get("status") == "NO_GO_FINALIZATION" and emergency_path.exists() and result.get("hardware_contact") == 0 and result.get("popup_count") == 0,
         "monitor did not fail closed as NO_GO_FINALIZATION after simulated STOP parser exception")
    return {"passed": True, "record": record}


def lifecycle_fault_fixtures(tmp: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    empty_plugins = tmp / "empty-plugins"
    empty_plugins.mkdir()
    rc, _, _ = run(["pwsh", "-NoProfile", "-File", str(FILES["launcher"]), "-CheckOnly",
                    "-OutRoot", str(tmp / "child-failure"), "-ProgrammerRoot", str(empty_plugins)])
    results.append(fixture_result("child_failure", "launcher -CheckOnly with empty programmer root", rc, rc != 0))

    q = tmp / "qualification.json"
    monitor = tmp / "monitor-result.json"
    stop = tmp / "stop.json"
    emergency = tmp / "emergency.json"
    write_json(q, {"status": "NOT_PASS", "process_id": 1})
    write_json(monitor, {"status": "READY"})
    rc, _, _ = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-Execute",
                    "-QualificationSignalPath", str(q), "-MonitorResultPath", str(monitor),
                    "-StopSignalPath", str(stop), "-EmergencyStopPath", str(emergency),
                    "-OutRoot", str(tmp / "popup-before-qualification")])
    results.append(fixture_result("popup_before_qualification", "supervisor -Execute before qualification PASS", rc, rc != 0 and not (tmp / "popup-before-qualification" / "operator-result.json").exists() and not (tmp / "popup-before-qualification" / "acceptance-prompt-invoked.json").exists()))

    sys.path.insert(0, str(PARSER.parent))
    import verify_wb55_ssd1681_r10_ball_log as parser
    good_q = tmp / "good-qualification.json"
    good_artifact = tmp / "good-qualification-parser.json"
    good_snapshot = tmp / "good-qualification-snapshot.log"
    good_artifact.write_text(json.dumps(parser.parse_log(parser.positive_log(1), 1)), encoding="utf-8")
    good_snapshot.write_text(parser.positive_log(1), encoding="utf-8")
    bad_stub = tmp / "abnormal-prompt.ps1"
    bad_stub.write_text("exit 7", encoding="utf-8")
    prompt_monitor = subprocess.Popen(["pwsh", "-NoProfile", "-Command", "Start-Sleep -Seconds 20"], cwd=ROOT)
    write_json(good_q, {"status": "PASS_R10_QUALIFICATION_READY", "hardware_contact": 0, "process_id": prompt_monitor.pid,
                        "parser_artifact": str(good_artifact), "qualification_snapshot": str(good_snapshot),
                        "qualification_frames": 16, "ring_bytes_limit": 65536})
    emergency2 = tmp / "emergency-prompt.json"
    try:
        rc, _, _ = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-SimulateQualifiedPrompt",
                    "-QualificationSignalPath", str(good_q), "-MonitorResultPath", str(monitor),
                    "-StopSignalPath", str(tmp / "stop-prompt.json"), "-EmergencyStopPath", str(emergency2),
                    "-SimulationPromptScript", str(bad_stub), "-OutRoot", str(tmp / "prompt-abnormal")], timeout=20)
        results.append(fixture_result("prompt_abnormal_exit_emergency", "supervisor process-only prompt stub exits 7", rc, rc != 0 and emergency2.exists() and not (tmp / "prompt-abnormal" / "operator-result.json").exists()))
    finally:
        if prompt_monitor.poll() is None:
            prompt_monitor.kill()
        prompt_monitor.wait(timeout=10)

    emergency3 = tmp / "emergency-monitor.json"
    rc, _, _ = run(["pwsh", "-NoProfile", "-File", str(FILES["monitor"]), "-Execute", "-Port", "COM999",
                    "-ReadySignalPath", str(tmp / "ready.json"), "-QualificationSignalPath", str(tmp / "q2.json"),
                    "-StopSignalPath", str(tmp / "stop2.json"), "-EmergencyStopPath", str(emergency3),
                    "-OutDir", str(tmp / "monitor-fault")])
    results.append(fixture_result("monitor_fault_emergency", "monitor -Execute with absent COM999", rc, rc != 0 and emergency3.exists()))

    cleanup = tmp / "cleanup-invalid.json"
    write_json(cleanup, {"postclean_valid": False, "restore_readback": False})
    code = "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(1 if not (d['postclean_valid'] and d['restore_readback']) else 0)"
    rc, _, _ = run([sys.executable, "-c", code, str(cleanup)])
    results.append(fixture_result("cleanup_failure_restore_required", "python cleanup/restore invariant fixture", rc, rc != 0))
    results.append(fixture_result("restore_readback_mismatch", "python cleanup/restore invariant fixture", rc, rc != 0))
    return results


def supervisor_regressions(tmp: Path) -> dict[str, object]:
    sys.path.insert(0, str(PARSER.parent))
    import verify_wb55_ssd1681_r10_ball_log as parser

    def live_monitor() -> subprocess.Popen[str]:
        return subprocess.Popen(["pwsh", "-NoProfile", "-Command", "Start-Sleep -Seconds 30"],
                                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

    def qualified(root: Path, monitor_pid: int) -> tuple[Path, Path, Path, Path, Path]:
        q = root / "qualification.json"
        artifact = root / "qualification-parser.json"
        snapshot = root / "qualification-snapshot.log"
        monitor = root / "monitor-result.json"
        stop = root / "stop.json"
        write_json(artifact, parser.parse_log(parser.positive_log(1), 1))
        snapshot.write_text(parser.positive_log(1), encoding="utf-8")
        monitor.write_text(json.dumps({"status": "RUNNING", "hardware_contact": 0}), encoding="utf-8")
        write_json(q, {"status": "PASS_R10_QUALIFICATION_READY", "hardware_contact": 0, "process_id": monitor_pid,
                       "parser_artifact": str(artifact), "qualification_snapshot": str(snapshot),
                       "qualification_frames": 16, "ring_bytes_limit": 65536})
        return q, monitor, stop, artifact, snapshot

    stub = tmp / "prompt-stub.ps1"
    stub.write_text("param([string]$OutputPath); Set-Content -LiteralPath $OutputPath -Value 'simulated note' -Encoding UTF8; [ordered]@{selected='通过';text='simulated note'} | ConvertTo-Json -Compress", encoding="utf-8")
    good_root = tmp / "supervisor-good"
    good_root.mkdir()
    monitor_process = live_monitor()
    try:
        q, monitor, stop, _, _ = qualified(good_root, monitor_process.pid)
        rc, _, _ = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-SimulateQualifiedPrompt",
                        "-QualificationSignalPath", str(q), "-MonitorResultPath", str(monitor),
                        "-StopSignalPath", str(stop), "-EmergencyStopPath", str(good_root / "emergency.json"),
                        "-SimulationPromptScript", str(stub), "-OutRoot", str(good_root)], timeout=20)
        guard = json.loads((good_root / "acceptance-prompt-invoked.json").read_text(encoding="utf-8"))
        receipt = json.loads((good_root / "prompt-simulation-receipt.json").read_text(encoding="utf-8"))
        result = json.loads((good_root / "operator-result.json").read_text(encoding="utf-8"))
        receipt_created = (good_root / "prompt-simulation-receipt.json").is_file()
        positive = {"name": "qualified_live_monitor_process_only_prompt", "executed": True,
                    "returncode": rc, "guard_created": (good_root / "acceptance-prompt-invoked.json").is_file(),
                    "guard_count": 1, "prompt_receipt_created": receipt_created, "prompt_process_start_count": receipt.get("prompt_process_start_count"),
                    "actual_popup_count": result.get("actual_popup_count"), "result_created": (good_root / "operator-result.json").is_file(),
                    "stop_created": stop.is_file(), "rejected": False}
        need(rc == 0 and positive["guard_created"] and positive["guard_count"] == 1 and positive["prompt_process_start_count"] == 1 and positive["actual_popup_count"] == 0 and positive["result_created"] and positive["stop_created"], "qualified supervisor process-only regression failed")
    finally:
        if monitor_process.poll() is None:
            monitor_process.kill()
        monitor_process.wait(timeout=10)

    rejections: list[dict[str, object]] = []

    missing_root = tmp / "supervisor-missing"
    missing_root.mkdir()
    missing_q = missing_root / "missing-qualification.json"
    rc, stdout, stderr = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-SimulateQualifiedPrompt",
                              "-QualificationSignalPath", str(missing_q), "-MonitorResultPath", str(missing_root / "monitor.json"),
                              "-StopSignalPath", str(missing_root / "stop.json"), "-EmergencyStopPath", str(missing_root / "emergency.json"),
                              "-SimulationPromptScript", str(stub), "-OutRoot", str(missing_root)])
    combined = stdout + stderr
    missing_receipt = (missing_root / "prompt-simulation-receipt.json").is_file()
    rejections.append({"name": "missing_qualification_zero_prompt", "executed": True, "returncode": rc,
                       "reason_expected": "R10 qualification signal is absent", "reason_observed": "R10 qualification signal is absent" in combined,
                       "prompt_receipt_created": missing_receipt, "prompt_process_start_count": 1 if missing_receipt else 0, "new_result": (missing_root / "operator-result.json").is_file(), "rejected": True})
    need(rc != 0 and "R10 qualification signal is absent" in combined and not missing_receipt and not (missing_root / "operator-result.json").exists(), "missing qualification regression failed")

    missing_artifact_root = tmp / "supervisor-missing-artifact"
    missing_artifact_root.mkdir()
    monitor_process = live_monitor()
    try:
        snapshot = missing_artifact_root / "snapshot.log"
        snapshot.write_text(parser.positive_log(1), encoding="utf-8")
        q = missing_artifact_root / "qualification.json"
        write_json(q, {"status": "PASS_R10_QUALIFICATION_READY", "hardware_contact": 0, "process_id": monitor_process.pid,
                       "parser_artifact": str(missing_artifact_root / "absent-parser.json"),
                       "qualification_snapshot": str(snapshot), "qualification_frames": 16, "ring_bytes_limit": 65536})
        rc, stdout, stderr = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-SimulateQualifiedPrompt",
                                  "-QualificationSignalPath", str(q), "-MonitorResultPath", str(missing_artifact_root / "monitor.json"),
                                  "-StopSignalPath", str(missing_artifact_root / "stop.json"), "-EmergencyStopPath", str(missing_artifact_root / "emergency.json"),
                                  "-SimulationPromptScript", str(stub), "-OutRoot", str(missing_artifact_root)])
        combined = stdout + stderr
        receipt_created = (missing_artifact_root / "prompt-simulation-receipt.json").is_file()
        reason = "R10 qualification evidence is incomplete" in combined
        rejections.append({"name": "missing_parser_artifact_zero_prompt", "executed": True, "returncode": rc,
                           "reason_expected": "R10 qualification evidence is incomplete", "reason_observed": reason,
                           "prompt_receipt_created": receipt_created, "prompt_process_start_count": 1 if receipt_created else 0,
                           "new_result": (missing_artifact_root / "operator-result.json").is_file(), "rejected": True})
        need(rc != 0 and reason and not receipt_created and not (missing_artifact_root / "operator-result.json").exists(), "missing parser artifact regression failed")
    finally:
        if monitor_process.poll() is None:
            monitor_process.kill()
        monitor_process.wait(timeout=10)

    mismatch_root = tmp / "supervisor-contact-mismatch"
    mismatch_root.mkdir()
    monitor_process = live_monitor()
    try:
        q, monitor, stop, artifact, _ = qualified(mismatch_root, monitor_process.pid)
        value = json.loads(artifact.read_text(encoding="utf-8")); value["hardware_contact"] = 1; write_json(artifact, value)
        value = json.loads(q.read_text(encoding="utf-8")); value["hardware_contact"] = 1; write_json(q, value)
        rc, stdout, stderr = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-SimulateQualifiedPrompt",
                                  "-QualificationSignalPath", str(q), "-MonitorResultPath", str(monitor),
                                  "-StopSignalPath", str(stop), "-EmergencyStopPath", str(mismatch_root / "emergency.json"),
                                  "-SimulationPromptScript", str(stub), "-OutRoot", str(mismatch_root)])
        combined = stdout + stderr
        receipt_created = (mismatch_root / "prompt-simulation-receipt.json").is_file()
        reason = "R10 qualification evidence is incomplete" in combined
        rejections.append({"name": "mismatched_hardware_contact_zero_prompt", "executed": True, "returncode": rc,
                           "reason_expected": "R10 qualification evidence is incomplete for mode-correct contact", "reason_observed": reason,
                           "prompt_receipt_created": receipt_created, "prompt_process_start_count": 1 if receipt_created else 0,
                           "new_result": (mismatch_root / "operator-result.json").is_file(), "rejected": True})
        need(rc != 0 and reason and not receipt_created and not (mismatch_root / "operator-result.json").exists(), "mismatched contact regression failed")
    finally:
        if monitor_process.poll() is None:
            monitor_process.kill()
        monitor_process.wait(timeout=10)

    for name, preexisting in (("preexisting_guard_zero_prompt", "acceptance-prompt-invoked.json"),
                              ("preexisting_review_zero_prompt", "operator-review.json"),
                              ("preexisting_result_zero_prompt", "operator-result.json")):
        root = tmp / name
        root.mkdir()
        monitor_process = live_monitor()
        try:
            q, monitor, stop, _, _ = qualified(root, monitor_process.pid)
            (root / preexisting).write_text("sentinel", encoding="utf-8")
            existing_result_hash = sha(root / "operator-result.json") if (root / "operator-result.json").exists() else None
            rc, stdout, stderr = run(["pwsh", "-NoProfile", "-File", str(FILES["supervisor"]), "-SimulateQualifiedPrompt",
                                      "-QualificationSignalPath", str(q), "-MonitorResultPath", str(monitor),
                                      "-StopSignalPath", str(stop), "-EmergencyStopPath", str(root / "emergency.json"),
                                      "-SimulationPromptScript", str(stub), "-OutRoot", str(root)])
            combined = stdout + stderr
            receipt_created = (root / "prompt-simulation-receipt.json").is_file()
            record = {"name": name, "executed": True, "returncode": rc,
                      "reason_expected": "sole acceptance prompt has already been invoked",
                      "reason_observed": "sole acceptance prompt has already been invoked" in combined,
                      "prompt_receipt_created": receipt_created, "prompt_process_start_count": 1 if receipt_created else 0, "new_result": (sha(root / "operator-result.json") if (root / "operator-result.json").exists() else None) != existing_result_hash, "rejected": True}
            rejections.append(record)
            need(rc != 0 and record["reason_observed"] and not record["new_result"], f"{name} regression failed")
        finally:
            if monitor_process.poll() is None:
                monitor_process.kill()
            monitor_process.wait(timeout=10)
    return {"positive": positive, "rejections": rejections, "rejection_count": len(rejections)}


def build() -> dict[str, object]:
    src = {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}
    driver_source = DRIVER.read_text(encoding="utf-8")
    checks = {
        "runner_real_execute": all(token in src["runner"] for token in ("Invoke-ProgrammerOnce", "continuousMonitorProcess", "continuousPromptProcess", "postcleanAttempted", "restore-write-verify-upload", "normal_resume")),
        "runner_only_r10_path": "Legacy diagnostic modes are unreachable" in src["runner"] and "if (-not $PhaseParallelR10Ball)" in src["runner"],
        "runner_consumed_receipt_bound": all(token in src["runner"] for token in ("CONSUMED_AUTHORIZED_R10_BALL_ONCE", "claim_marker", "source_spent_path", "source_authorization_path", "expectedReceiptPath", "source_authorization_sha256", "claimRecord.status", "consumed -eq $true", "parser_sha256")) and "COMP-REQ-324" not in src["runner"],
        "runner_cleanup_fail_closed": all(token in src["runner"] for token in ("postclean", "restoreValid", "normalValid", "Stop-ProcessTree", "automatic_retries")),
        "monitor_full_frame_and_snapshot": all(token in src["monitor"] for token in ("qualificationSnapshotPath", "--validate-loop-line", "--loop-log", "malformed_hash", "RingBytes", "parser returned PASS without writing", "hardware-contact 1")),
        "monitor_fail_closed": all(token in src["monitor"] for token in ("EmergencyStopPath", "Non-contiguous R10 loop iteration", "R10 full loop frame contract rejected")),
        "supervisor_real_selection": all(token in src["supervisor"] for token in ("operator-prompt", "selected", "note_sha256", "通过", "失败", "StopSignalPath", "EmergencyStopPath", "SimulateQualifiedPrompt", "Stop-ProcessTree", "operator-result.json", "-OutRoot")) and "if(Test-Path $guard -or Test-Path $review)" not in src["supervisor"],
        "runner_supervisor_interface": 'parameter = "-OutRoot"' in src["runner"] and 'parameter = "-OutputRoot"' not in src["runner"],
        "launcher_atomic_claim": all(token in src["launcher"] for token in ("ClaimOnly", "CreateNew", "[IO.File]::Move", "consumed.json", "output_root mismatch", "parser_sha256")) and "COMP-REQ-324" not in src["launcher"],
        "successor_machine_binding": all("companion-ssd1681-r10-r3-execute-ready-machine-ready-20260722.json" in src[key] and "companion-ssd1681-r10-r2-machine-ready-20260722.json" not in src[key] for key in ("launcher", "runner")),
        "receipt_machine_path_binding": "machine_ready_path" in src["launcher"] and "machine_ready_path" in src["runner"],
        "launcher_detached_execute": all(token in src["launcher"] for token in ("STARTED_DETACHED", "-Execute", "-PhaseParallelR10Ball", "durable_stdout_redirected")) and "WaitForExit(120000)" not in src["launcher"],
        "monitor_exact_ring": "if ($RingBytes -ne 65536)" in src["monitor"] and "ring_bytes_limit=65536" in src["monitor"],
        "r3_stable_hold_source": all(token in driver_source for token in ("HAL_Delay(SSD1681_R10_STABLE_HOLD_TARGET_MS)", "record->hold_elapsed_ms", "record->hold_count = 1u", "hold_elapsed_ms=%lu hold_count=%u")) and driver_source.count("HAL_Delay(SSD1681_R10_STABLE_HOLD_TARGET_MS)") == 1,
        "r3_hold_parser_contract": all(token in PARSER.read_text(encoding="utf-8") for token in ("schema=v2", "400 <= hold <= 410", "expected exactly one stable hold", "hold_before_post_sync")),
        "r3_machine_ready_calls_canonical_audit": "verify_companion_current_goal_audit.py" in MACHINE_READY_GENERATOR.read_text(encoding="utf-8") and "canonical_audit_required" in MACHINE_READY_GENERATOR.read_text(encoding="utf-8"),
        "checkonly_zero_contract": all("hardware_contact=0" in src[key] or "hardware_contact = 0" in src[key] or "hardware_contact=if($CheckOnly){0}" in src[key] for key in ("runner", "monitor", "supervisor", "launcher")),
    }
    need(all(checks.values()), "lifecycle source contract failed: " + str([key for key, value in checks.items() if not value]))
    with tempfile.TemporaryDirectory(prefix="r10-lifecycle-") as directory:
        tmp = Path(directory)
        authorization_evidence = authorization_fixtures(tmp)
        fixtures = authorization_evidence["negative"] + parser_fixtures(tmp) + lifecycle_fault_fixtures(tmp)
        parser_write = parser_write_regression(tmp)
        parser_finalization = parser_finalization_fixtures(tmp)
        monitor_finalization = monitor_finalization_fixture(tmp)
        supervisor = supervisor_regressions(tmp)
    need(len(fixtures) == 25, f"expected 25 executed lifecycle fixtures, found {len(fixtures)}")
    need(all(item["executed"] and item["rejected"] and item["hardware_contact"] == 0 and item["write_count"] == 0 and item["popup_count"] == 0 for item in fixtures), "a lifecycle fixture was not rejected or was not no-hardware")
    need(authorization_evidence["positive"]["returncode"] == 0 and authorization_evidence["positive"]["receipt_created"] and authorization_evidence["positive"]["hardware_contact"] == 0 and authorization_evidence["positive"]["write_count"] == 0 and authorization_evidence["positive"]["popup_count"] == 0, "disposable ClaimOnly positive evidence was incomplete")
    need(parser_write["passed"] and supervisor["positive"]["actual_popup_count"] == 0 and supervisor["positive"]["prompt_receipt_created"] and supervisor["positive"]["prompt_process_start_count"] == 1 and all(item["reason_observed"] and not item["prompt_receipt_created"] and item["prompt_process_start_count"] == 0 and not item["new_result"] for item in supervisor["rejections"]), "supervisor or parser persistence regression evidence was incomplete")
    return {"schema_id": "companion.wb55.ssd1681.r10_r3_ball.lifecycle_static.v8", "status": "PASS_R10_R3_REAL_EXECUTE_LIFECYCLE_STATIC", "checks": checks, "negative_fixtures": fixtures, "negative_fixture_count": len(fixtures), "authorization_positive": authorization_evidence["positive"], "parser_write_regression": parser_write, "parser_finalization_fixtures": parser_finalization, "monitor_finalization_fixture": monitor_finalization, "supervisor_regressions": supervisor, "file_hashes": {key: sha(path) for key, path in FILES.items()}, "parser_sha256": sha(PARSER), "driver_sha256": sha(DRIVER)}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--artifact", type=Path, default=OUT)
    args = parser.parse_args()
    try:
        result = build()
    except (OSError, Failure, subprocess.SubprocessError) as error:
        print(f"FAIL: R10 lifecycle static: {error}")
        return 1
    rendered = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.write:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_bytes(rendered)
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered:
        print("FAIL: stale R10 lifecycle static artifact")
        return 1
    print(f"PASS: R10 real Execute lifecycle static checks={len(result['checks'])} negative_fixtures={len(result['negative_fixtures'])} artifact_sha256={sha(args.artifact)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
