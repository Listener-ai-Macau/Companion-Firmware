#!/usr/bin/env python3
"""Assemble the final no-hardware R8-R2 transport/readiness closure."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-machine-ready-20260721.json"
R1 = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-machine-ready-20260721.json"
STATIC = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-static-20260721.json"
LAUNCHER_STATIC = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-persistent-launcher-static-20260721.json"
INCIDENT = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-launch-transport-incident-20260721.json"
GOAL_AUDIT = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
CHECK_ROOT = ROOT / ".cache/validation/wb55-ram-command-target-r8-r2-persistent-checkonly-20260721-r1"
CHECK_LAUNCH = CHECK_ROOT / "persistent-launch.json"
CHECK_STAGE = CHECK_ROOT / "stage-run.json"
RUNNER = ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_ram_command_target_r8.ps1"
CANDIDATE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_ram_command_target_r8/Companion_Nucleo_WB55RG_Ssd1681RamCommandTargetR8.hex"
OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")

EXPECTED = {
    R1: "5FC97C92136A2EAC862620C847C1B6910491800EC84248ED8F255D32D9DFA568",
    STATIC: "C855F1883EFB4AC66E1C99D419BF2210A19F14B84881BF1FC371BBABFE77F66E",
    LAUNCHER_STATIC: "03B05783166631436DEC344BAF3EF8C958E6C6BEA535E6010627752D4E718B54",
    INCIDENT: "C3D8C8809C2C807592A92D9749F235013AF465434DD16ED9B558308E71CB7900",
    CHECK_LAUNCH: "E3F24A8E478818DB72F602306E37D28ECCB040A7B0490846E348A03AD2B3B954",
    CHECK_STAGE: "A44544343CD02DA4A65B087CB9F2F38CBA742E925E6C3E81C6223545C358A57C",
    RUNNER: "3E1A3FFDC4B44BDE107CF6A0922E81ECA1F95442B8A6A3BDF4F71C018806D017",
    LAUNCHER: "697CDA08E8DC3DBAEAFDCA373A008FFF9D81D2AB1FAD08B087F793ECF940D568",
    CANDIDATE: "9ECF8F4A2A75A054077908C775879447ADCE089F55DC33315A8C852C4F47CB13",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(name: str, command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main() -> int:
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    for path, expected in EXPECTED.items():
        require(f"hash:{path.name}", path.is_file() and sha(path) == expected, f"hash mismatch: {path}")

    documents: dict[Path, dict[str, object]] = {}
    for path in (R1, STATIC, LAUNCHER_STATIC, INCIDENT, GOAL_AUDIT, CHECK_LAUNCH, CHECK_STAGE):
        try:
            documents[path] = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load {path}: {exc}")

    if errors:
        result = {
            "schema_id": "companion.wb55.ssd1681_ram_command_target_r8.r2_closure.v1",
            "status": "NO_GO_R8_R2_CLOSURE_INPUTS",
            "hardware_contact": 0,
            "execute_performed": False,
            "errors": errors,
            "checks": checks,
        }
        OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["status"])
        return 1

    r1 = documents[R1]
    static = documents[STATIC]
    launcher_static = documents[LAUNCHER_STATIC]
    incident = documents[INCIDENT]
    goal_audit = documents[GOAL_AUDIT]
    launch = documents[CHECK_LAUNCH]
    stage = documents[CHECK_STAGE]

    require("r1_candidate_machine_ready", r1.get("status") == "MACHINE_READY_R8_NO_HARDWARE_CONTACT_EXECUTE_FORBIDDEN_PENDING_ROOT", "R8 R1 candidate evidence differs")
    require("r2_static", static.get("status") == "MACHINE_READY_R8_R2_NO_HARDWARE_CONTACT_EXECUTE_FORBIDDEN_PENDING_ROOT", "R8-R2 static gate differs")
    require("launcher_static", launcher_static.get("status") == "PASS_R8_PERSISTENT_LAUNCHER_STATIC_AND_NEGATIVE_FIXTURES", "R8 launcher fixture gate differs")
    require("incident_archived", incident.get("status") == "R8_CANDIDATE_NOT_EXECUTED_CLEAN_RESTORE_RESUME_PASS_LAUNCH_TRANSPORT_FAILED", "R8 transport incident differs")
    require("incident_candidate_zero", incident.get("candidate_boundary", {}).get("candidate_write_calls") == 0 and incident.get("candidate_boundary", {}).get("r8_experiment_consumed") is False, "incident consumed or overclaims an R8 experiment")
    require("incident_no_synthetic_response", incident.get("superseded_non_acceptance_prompt", {}).get("selected") is None and incident.get("superseded_non_acceptance_prompt", {}).get("visual_acceptance") is False, "incident fabricates human acceptance")
    require("goal_audit", goal_audit.get("status") == "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING", "current Goal audit is not active/pass")

    require("persistent_checkonly", launch.get("status") == "READY_NO_HARDWARE_CONTACT" and launch.get("mode") == "check_only", "persistent CheckOnly launcher differs")
    require("persistent_streams", launch.get("durable_stdout_redirected") is True and launch.get("durable_stderr_redirected") is True and launch.get("hidden_child") is True and launch.get("persistent_child") is True, "persistent child streams/lifecycle differ")
    require("persistent_child_exit", launch.get("exit_code") == 0 and isinstance(launch.get("process_id"), int), "persistent child PID/exit differs")
    require("persistent_zero_contact", launch.get("hardware_contact") == 0 and launch.get("write_counter_sum") == 0, "persistent CheckOnly contacted hardware or wrote")
    arguments = launch.get("arguments", [])
    require("checkonly_never_execute", "-CheckOnly" in arguments and "-Execute" not in arguments and "-RamCommandTargetR8" in arguments, "persistent CheckOnly arguments can cross into Execute")
    require("stage_ready", stage.get("status") == "READY_NO_HARDWARE_CONTACT" and stage.get("hardware_contact") == 0, "inner R8 stage is not zero-contact ready")
    counters = stage.get("counters", {})
    require("stage_zero_writes", isinstance(counters, dict) and all(value == 0 for value in counters.values()), "inner R8 CheckOnly counters are nonzero")
    require("stage_zero_popups", stage.get("popup_policy", {}).get("machine_only_r8_total") == 0 and stage.get("pre_execute_prompt", {}).get("invoked") is False and stage.get("operator_prompt", {}).get("invoked") is False, "inner R8 CheckOnly popup count differs")

    command_results = [
        run("product_registry", [sys.executable, str(ROOT / "tools/verify_companion_product_requirements.py")]),
        run("current_goal_audit", [sys.executable, str(ROOT / "tools/verify_companion_current_goal_audit.py")]),
        run("r8_static", [sys.executable, str(ROOT / "tools/verify_wb55_ssd1681_ram_command_target_r8_diagnostic.py")]),
        run("launcher_static_negative_fixtures", [sys.executable, str(ROOT / "tools/verify_wb55_ssd1681_ram_command_target_r8_launcher.py")]),
        run("python_compile", [sys.executable, "-m", "py_compile", str(ROOT / "tools/verify_wb55_ssd1681_ram_command_target_r8_diagnostic.py"), str(ROOT / "tools/verify_wb55_ssd1681_ram_command_target_r8_launcher.py")]),
        run("git_diff_check", ["git", "diff", "--check"]),
    ]
    for command in command_results:
        require(f"command:{command['name']}", command["returncode"] == 0, f"command failed: {command['name']}")

    result = {
        "schema_id": "companion.wb55.ssd1681_ram_command_target_r8.r2_closure.v1",
        "status": "MACHINE_READY_R8_R2_NO_HARDWARE_CONTACT_EXECUTE_FORBIDDEN_PENDING_ROOT" if not errors else "NO_GO_R8_R2_CLOSURE",
        "claim_scope": "R8 candidate bytes are unchanged; this closes only persistent launch transport, zero-popup policy, no-hardware lifecycle and prior incident disposition.",
        "hardware_contact": 0,
        "execute_performed": False,
        "automatic_retry_performed": False,
        "goal_action": "none_root_owned",
        "checks": checks,
        "errors": errors,
        "candidate": {
            "hex_sha256": sha(CANDIDATE),
            "changed_by_r2": False,
            "production_enabled": False,
            "swap_activations_max_if_later_authorized": 1,
            "post_tag_activations": 0,
            "selector_reads": 28,
        },
        "incident": {
            "candidate_write_calls": 0,
            "preclean": "PASS",
            "postclean": "PASS",
            "raw_restore": "PASS_524288_BYTES_EXACT",
            "normal_resume": "PASS",
            "non_acceptance_prompt": "SUPERSEDED_CANCELLED_EMPTY_NO_SYNTHETIC_RESPONSE",
        },
        "persistent_checkonly": {
            "launch_sha256": sha(CHECK_LAUNCH),
            "stage_sha256": sha(CHECK_STAGE),
            "child_process_id": launch.get("process_id"),
            "child_exit_code": launch.get("exit_code"),
            "hardware_contact": launch.get("hardware_contact"),
            "write_counter_sum": launch.get("write_counter_sum"),
            "stdout_sha256": sha(CHECK_ROOT / "runner.stdout.log"),
            "stderr_sha256": sha(CHECK_ROOT / "runner.stderr.log"),
        },
        "popup_policy": {
            "cleanup": 0,
            "recovery_or_fault_acknowledgement": 0,
            "pre_execute_or_start": 0,
            "machine_only_r8_total": 0,
            "genuinely_visual_candidate": "one final canonical PASS/FAIL acceptance popup only",
        },
        "evidence_hashes": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
            for path in (R1, STATIC, LAUNCHER_STATIC, INCIDENT, GOAL_AUDIT, RUNNER, LAUNCHER)
        },
        "protected_hashes": {
            str(OWNER_ACCEPTANCE.relative_to(ROOT)).replace("\\", "/"): sha(OWNER_ACCEPTANCE),
            str(SUPPLIER): sha(SUPPLIER),
        },
        "commands": command_results,
        "next_boundary": "Stop. No Execute or retry is authorized. Root must record a new explicit one-run authorization before using the persistent launcher with -Execute.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
