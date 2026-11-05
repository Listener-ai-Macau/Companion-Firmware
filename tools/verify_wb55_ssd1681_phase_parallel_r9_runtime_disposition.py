#!/usr/bin/env python3
"""Archive and verify the sole authorized R9 physical disposition."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / ".cache/validation/wb55-phase-parallel-r9-persistent-execute-20260721-r1"
MACHINE_READY = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-machine-ready-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
REGISTRY_FIXTURE = ROOT / "docs/validation/companion-product-requirements.json"
CURRENT_GOAL = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
OWNER = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
ARCHIVE = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-runtime-20260721"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-runtime-disposition-20260721.json"

MACHINE_READY_SHA = "B3B93CE7EBB97425F10CFC60425D99B97224B995ADF065AE388E062C022C8879"
HEX_SHA = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF"
LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
NOTE_TEXT = "你这个应该要一直运动才行，因为我也不是一直在屏幕前的。\r\n"
NOTE_SHA = "E2EDDD3239D7FE8E195D266040B0C1800D585887788FE64D9D6B772692928E56"
V9_SHA = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
OWNER_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"

FILES = {
    "persistent-launch.json": RUN_ROOT / "persistent-launch.json",
    "baseline-gate.json": RUN_ROOT / "baseline-gate.json",
    "preclean-white.json": RUN_ROOT / "preclean-white.json",
    "controller-state.json": RUN_ROOT / "controller-state.json",
    "operator-review.json": RUN_ROOT / "operator-review.json",
    "operator-note.txt": RUN_ROOT / "operator-note.txt",
    "postclean-white.json": RUN_ROOT / "postclean-white.json",
    "restore-gate.json": RUN_ROOT / "restore-gate.json",
    "normal-resume.json": RUN_ROOT / "normal-resume.json",
    "stage-run.json": RUN_ROOT / "stage-run.json",
    "runner.stdout.log": RUN_ROOT / "runner.stdout.log",
    "runner.stderr.log": RUN_ROOT / "runner.stderr.log",
    "preclean-serial-raw.log": RUN_ROOT / "preclean-capture/nucleo-serial-raw.log",
    "candidate-serial-raw.log": RUN_ROOT / "candidate-capture/nucleo-serial-raw.log",
    "postclean-serial-raw.log": RUN_ROOT / "postclean-capture/nucleo-serial-raw.log",
    "normal-serial-raw.log": RUN_ROOT / "normal-capture/nucleo-serial-raw.log",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    required = [MACHINE_READY, REGISTRY, REGISTRY_FIXTURE, CURRENT_GOAL, V9, OWNER, *FILES.values()]
    missing = [rel(path) for path in required if not path.is_file()]
    require("required_inputs", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.write_text(json.dumps({"status": "NO_GO_R9_RUNTIME_CLOSURE", "errors": errors}, indent=2) + "\n")
        return 1

    machine_ready = load(MACHINE_READY)
    launch = load(FILES["persistent-launch.json"])
    stage = load(FILES["stage-run.json"])
    controller = load(FILES["controller-state.json"])
    operator = load(FILES["operator-review.json"])
    preclean = load(FILES["preclean-white.json"])
    postclean = load(FILES["postclean-white.json"])
    restore = load(FILES["restore-gate.json"])
    normal = load(FILES["normal-resume.json"])
    registry_fixture = load(REGISTRY_FIXTURE)
    goal = load(CURRENT_GOAL)
    registry = REGISTRY.read_text(encoding="utf-8")
    note_bytes = FILES["operator-note.txt"].read_bytes()
    stdout = FILES["runner.stdout.log"].read_text(encoding="utf-8-sig")
    stderr = FILES["runner.stderr.log"].read_text(encoding="utf-8-sig")

    require(
        "sealed_authorization",
        sha(MACHINE_READY) == MACHINE_READY_SHA
        and machine_ready.get("machine_ready") is True
        and machine_ready.get("candidate", {}).get("hex_sha256") == HEX_SHA
        and machine_ready.get("candidate", {}).get("lut_sha256") == LUT_SHA,
        "sealed MACHINE_READY/HEX/LUT identity differs",
    )
    require(
        "registry_disposition",
        registry.count("| COMP-REQ-310 |") == 1
        and registry.count("| COMP-REQ-311 |") == 1
        and registry_fixture.get("status") == "PASS"
        and registry_fixture.get("requirement_ids", [])[-2:] == ["COMP-REQ-310", "COMP-REQ-311"],
        "COMP-REQ-310/311 steering is not uniquely registered",
    )
    require(
        "goal_and_protected_behavior",
        goal.get("status") == "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING"
        and not goal.get("errors")
        and sha(V9) == V9_SHA
        and sha(OWNER) == OWNER_SHA,
        "current Goal or protected accepted behavior differs",
    )
    require(
        "persistent_execute",
        launch.get("status") == "STARTED_DETACHED"
        and launch.get("mode") == "execute"
        and launch.get("locked_hashes", {}).get("candidate_hex") == HEX_SHA
        and launch.get("locked_hashes", {}).get("workbench") == "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF",
        "persistent execute launch identity differs",
    )

    steps = controller.get("observed", {}).get("steps", [])
    contract = controller.get("contract", {})
    require(
        "controller_machine_pass",
        controller.get("status") == "PASS_MACHINE_PHASE_PARALLEL_R9"
        and not controller.get("errors")
        and controller.get("candidate", {}).get("lut_sha256") == LUT_SHA
        and controller.get("observed", {}).get("records") == 16
        and len(steps) == 16
        and [item.get("step") for item in steps] == list(range(1, 17))
        and all(item.get("busy_complete") == 1 and 1 <= item.get("busy_ms", 0) <= 600 for item in steps)
        and all(item.get("post_sync_bytes") == 128 and item.get("step_ok") == 1 for item in steps)
        and controller.get("observed", {}).get("busy_max_ms") == 599,
        "controller did not preserve the exact 16/16 bounded PASS",
    )
    require(
        "controller_forbidden_zero",
        contract.get("activations") == 16
        and contract.get("control") == "0xCF"
        and contract.get("refresh") == "0x20"
        and contract.get("full_frame_writes") == 0
        and contract.get("forbidden_controls") == {"0xF7": 0, "0xC7": 0, "0xFF": 0}
        and contract.get("automatic_retries") == 0
        and contract.get("motion_120_frame") is False,
        "controller forbidden-operation counters differ",
    )
    require(
        "operator_verbatim_fail",
        operator.get("status") == "NO_GO_OWNER_R9_LOCAL_VISUAL"
        and operator.get("selected") == "失败"
        and operator.get("note") == NOTE_TEXT
        and operator.get("note_sha256") == NOTE_SHA
        and operator.get("controller_sha256") == sha(FILES["controller-state.json"])
        and operator.get("machine_steps") == 16
        and operator.get("machine_busy_max_ms") == 599.0
        and operator.get("popup_counts") == {
            "start": 0,
            "cleanup": 0,
            "recovery": 0,
            "fault": 0,
            "final_visual_acceptance": 1,
        }
        and note_bytes == NOTE_TEXT.encode("utf-8")
        and sha(FILES["operator-note.txt"]) == NOTE_SHA,
        "operator FAIL selection or verbatim note differs",
    )
    require(
        "stage_disposition",
        stage.get("status") == "NO_GO_R9_VISUAL_NOT_PASSED_RESTORED"
        and stage.get("hardware_contact") == 1
        and stage.get("controller_state", {}).get("status") == "PASS_MACHINE_PHASE_PARALLEL_R9"
        and stage.get("operator_prompt", {}).get("required") is True
        and stage.get("operator_prompt", {}).get("invoked") is True
        and stage.get("operator_prompt", {}).get("selected") == "失败"
        and stage.get("operator_prompt", {}).get("error") is None
        and stage.get("popup_policy") == {
            "pre_execute": 0,
            "cleanup": 0,
            "recovery_or_fault_acknowledgement": 0,
            "machine_only_r8_total": None,
            "visual_acceptance": 1,
        },
        "stage owner-failed restored disposition differs",
    )
    counters = stage.get("counters", {})
    require(
        "bounded_counts",
        [item.get("operation") for item in stage.get("programmer_calls", [])] == [
            "preclean-white-write",
            "candidate-write",
            "postclean-white-write",
            "restore-write-verify-upload",
        ]
        and counters.get("panel_refresh_commands") == 16
        and counters.get("panel_busy_waits") == 16
        and counters.get("automatic_retries") == 0
        and counters.get("restore_write_calls") == 1
        and counters.get("restore_verify_operations") == 1
        and counters.get("restore_upload_calls") == 1,
        "bounded runtime/programmer counters differ",
    )

    clean_status = "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE"
    require(
        "promptless_clean_both_banks",
        preclean.get("status") == clean_status
        and postclean.get("status") == clean_status
        and all(item.get("payload_all_white") is True for item in preclean.get("observed", {}).get("reads", []))
        and all(item.get("payload_all_white") is True for item in postclean.get("observed", {}).get("reads", []))
        and len(preclean.get("observed", {}).get("reads", [])) == 4
        and len(postclean.get("observed", {}).get("reads", [])) == 4,
        "pre/post dual-plane repeated White readback differs",
    )
    require(
        "exact_restore_and_normal_resume",
        restore.get("status") == "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES"
        and restore.get("length_bytes") == 524288
        and restore.get("baseline_sha256") == BASELINE_SHA
        and restore.get("restore_sha256") == BASELINE_SHA
        and restore.get("byte_identical") is True
        and normal.get("status") == "PASS_APPLICATION_RESUMED_AFTER_BACKUP"
        and normal.get("ready_after_boot") is True
        and not normal.get("controller_diagnostic_markers")
        and not normal.get("panel_error_markers")
        and not normal.get("hardfault_markers"),
        "exact captured-application restore or normal resume differs",
    )
    require(
        "durable_logs",
        all(token in stdout for token in (
            "PASS_MACHINE_PHASE_PARALLEL_R9",
            "PASS_RESTORE_EQUALS_CAPTURED_PRE_RUN_APPLICATION_BYTES",
            "PASS_APPLICATION_RESUMED_AFTER_BACKUP",
        ))
        and "Diagnostic machine gate failed; captured raw application bytes were restored exactly." in stderr
        and "HardFault" not in stderr,
        "durable stdout/stderr disposition differs",
    )

    commands: dict[str, dict[str, Any]] = {}
    command_map = {
        "registry": [sys.executable, str(ROOT / "tools/verify_companion_product_requirements.py")],
        "current_goal": [sys.executable, str(ROOT / "tools/verify_companion_current_goal_audit.py")],
        "diff_check": ["git", "diff", "--check", "--", rel(REGISTRY)],
    }
    for name, command in command_map.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        output = (proc.stdout + proc.stderr).strip()
        commands[name] = {"command": command, "returncode": proc.returncode, "output": output[-2000:]}
        require(f"command_{name}", proc.returncode == 0, f"closure command failed: {name}: {output}")

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive_evidence: dict[str, dict[str, Any]] = {}
    for name, source in FILES.items():
        target = ARCHIVE / name
        shutil.copyfile(source, target)
        archive_evidence[name] = {
            "source": rel(source),
            "source_sha256": sha(source),
            "archive_sha256": sha(target),
            "bytes": target.stat().st_size,
            "byte_identical": source.read_bytes() == target.read_bytes(),
        }
        require(f"archive_{name}", archive_evidence[name]["byte_identical"], f"archive copy differs: {name}")

    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9.runtime_disposition.v1",
        "status": (
            "NO_GO_R9_OWNER_VISUAL_FAILED_RESTORED_STOP_NO_MOTION"
            if not errors
            else "NO_GO_R9_RUNTIME_CLOSURE_INVALID"
        ),
        "requirements": ["COMP-REQ-310", "COMP-REQ-311"],
        "errors": errors,
        "checks": checks,
        "machine_status": controller.get("status"),
        "machine_steps": len(steps),
        "machine_busy_min_ms": min(item["busy_ms"] for item in steps),
        "machine_busy_max_ms": max(item["busy_ms"] for item in steps),
        "operator_status": operator.get("status"),
        "operator_selected": operator.get("selected"),
        "operator_note_verbatim": operator.get("note"),
        "operator_note_sha256": sha(FILES["operator-note.txt"]),
        "popup_counts": operator.get("popup_counts"),
        "restore_status": restore.get("status"),
        "restore_bytes": restore.get("length_bytes"),
        "restore_sha256": restore.get("restore_sha256"),
        "normal_resume_status": normal.get("status"),
        "authorization_consumed": True,
        "retry_allowed": False,
        "motion_stage_entered": False,
        "motion_authorized": False,
        "production_allowed": False,
        "next_boundary": "root review of restored owner FAIL; a new explicit contract is required for any motion or hardware contact",
        "commands": commands,
        "archive_root": rel(ARCHIVE),
        "archive_evidence": archive_evidence,
        "protected_hashes": {
            "machine_ready_sha256": sha(MACHINE_READY),
            "locked_v9_source_sha256": sha(V9),
            "owner_acceptance_sha256": sha(OWNER),
            "registry_sha256": sha(REGISTRY),
            "registry_fixture_sha256": sha(REGISTRY_FIXTURE),
            "current_goal_sha256": sha(CURRENT_GOAL),
            "closure_tool_sha256": sha(Path(__file__).resolve()),
        },
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
