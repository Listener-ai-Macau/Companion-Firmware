#!/usr/bin/env python3
"""Close the no-hardware MACHINE_READY evidence for SSD1681 R9."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
REGISTRY_ARTIFACT = ROOT / "docs/validation/companion-product-requirements.json"
CURRENT_GOAL = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
WORKBENCH = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-workbench-20260721.json"
STATIC = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-static-20260721.json"
LAUNCHER_STATIC = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-persistent-launcher-static-20260721.json"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9.ps1"
PROMPT = ROOT / "tools/invoke_wb55_ssd1681_phase_parallel_r9_final_visual_prompt.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_log.py"
STATIC_TOOL = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_diagnostic.py"
LAUNCHER_TOOL = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_launcher.py"
WORKBENCH_TOOL = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_workbench.py"
MACHINE_READY_TOOL = Path(__file__).resolve()
R9_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex"
R9_ELF = R9_HEX.with_suffix(".elf")
OWNER = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-machine-ready-20260721.json"

WORKBENCH_SHA = "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF"
LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
R9_HEX_SHA = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF"
R9_ELF_SHA = "777A1288A0E6FC83373602F9895B07AA08F31269AB68B7EB1699723583D03485"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
OWNER_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V9_SHA = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkonly-root",
        type=Path,
        default=ROOT / ".cache/validation/wb55-phase-parallel-r9-persistent-checkonly-20260721-r3",
    )
    parser.add_argument(
        "--rejected-checkonly-root",
        type=Path,
        default=ROOT / ".cache/validation/wb55-phase-parallel-r9-persistent-checkonly-20260721-r1",
    )
    args = parser.parse_args()
    check_root = args.checkonly_root.resolve()
    rejected_root = args.rejected_checkonly_root.resolve()
    launch_path = check_root / "persistent-launch.json"
    stage_path = check_root / "stage-run.json"
    stdout_path = check_root / "runner.stdout.log"
    stderr_path = check_root / "runner.stderr.log"
    rejected_launch_path = rejected_root / "persistent-launch.json"
    rejected_stage_path = rejected_root / "stage-run.json"

    errors: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    required = [
        REGISTRY, REGISTRY_ARTIFACT, CURRENT_GOAL, WORKBENCH, STATIC, LAUNCHER_STATIC,
        DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PROMPT, PARSER, STATIC_TOOL,
        LAUNCHER_TOOL, WORKBENCH_TOOL, MACHINE_READY_TOOL, R9_HEX, R9_ELF, OWNER, V9, launch_path,
        stage_path, stdout_path, stderr_path, rejected_launch_path, rejected_stage_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"status": "NO_GO_R9_MACHINE_READY", "errors": errors}, indent=2) + "\n")
        return 1

    registry = REGISTRY.read_text(encoding="utf-8")
    registry_artifact = load(REGISTRY_ARTIFACT)
    goal = load(CURRENT_GOAL)
    workbench = load(WORKBENCH)
    static = load(STATIC)
    launcher_static = load(LAUNCHER_STATIC)
    launch = load(launch_path)
    stage = load(stage_path)
    rejected_launch = load(rejected_launch_path)
    rejected_stage = load(rejected_stage_path)

    require(
        "registry",
        registry.count("| COMP-REQ-309 |") == 1
        and registry_artifact.get("status") == "PASS"
        and "COMP-REQ-309" in registry_artifact.get("requirement_ids", []),
        "registry verifier or COMP-REQ-309 differs",
    )
    require(
        "current_goal",
        goal.get("status") == "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING"
        and goal.get("codex_goal_status") == "active"
        and not goal.get("errors"),
        "current Goal audit is not active/PASS",
    )
    require(
        "workbench",
        sha(WORKBENCH) == WORKBENCH_SHA
        and workbench.get("status") == "ADMIT_ONE_VARIABLE_R9"
        and workbench.get("candidate", {}).get("lut_sha256") == LUT_SHA,
        "sealed R9 workbench admission differs",
    )
    require(
        "static",
        static.get("status") == "PASS_STATIC_PHASE_PARALLEL_R9"
        and not static.get("failures")
        and all(static.get("checks", {}).values())
        and static.get("candidate", {}).get("lut_byte_count") == 159
        and static.get("candidate", {}).get("lut_sha256") == LUT_SHA
        and static.get("candidate", {}).get("tail_hex") == "221741A83258"
        and all(static.get("negative_fixtures", {}).values()),
        "R9 static/lineage/negative gate differs",
    )
    oracle = static.get("transition_oracle", {}).get("transitions", {})
    require(
        "transition_oracle",
        static.get("transition_oracle", {}).get("shared_timing_frames") == 16
        and oracle.get("BW", {}).get("effective_drive_frames") == 16
        and oracle.get("BW", {}).get("positive_drive_frames") == 8
        and oracle.get("BW", {}).get("negative_drive_frames") == 8
        and oracle.get("BW", {}).get("source_volt_frame_impulse") == 0
        and oracle.get("WB", {}).get("effective_drive_frames") == 16
        and oracle.get("WB", {}).get("positive_drive_frames") == 8
        and oracle.get("WB", {}).get("negative_drive_frames") == 8
        and oracle.get("WB", {}).get("source_volt_frame_impulse") == 0
        and oracle.get("WW", {}).get("effective_drive_frames") == 0
        and oracle.get("BB", {}).get("effective_drive_frames") == 0,
        "R9 transition impulse oracle differs",
    )
    require(
        "launcher_static",
        launcher_static.get("status") == "PASS_R9_PERSISTENT_LAUNCHER_STATIC_AND_NEGATIVE_FIXTURES"
        and not launcher_static.get("errors")
        and launcher_static.get("checks", {}).get("hardware_contact") == 0
        and launcher_static.get("checks", {}).get("execute_invoked") is False,
        "persistent launcher static/negative gate differs",
    )
    require(
        "build_identity",
        sha(R9_HEX) == R9_HEX_SHA and sha(R9_ELF) == R9_ELF_SHA,
        "isolated R9 HEX/ELF identity differs",
    )
    require(
        "persistent_launch",
        launch.get("status") == "READY_NO_HARDWARE_CONTACT"
        and launch.get("mode") == "check_only"
        and launch.get("exit_code") == 0
        and launch.get("hardware_contact") == 0
        and launch.get("write_counter_sum") == 0
        and launch.get("durable_stdout_redirected") is True
        and launch.get("durable_stderr_redirected") is True
        and launch.get("hidden_child") is True
        and launch.get("persistent_child") is True,
        "persistent CheckOnly launch differs",
    )
    locked = launch.get("locked_hashes", {})
    require(
        "persistent_hashes",
        locked.get("runner") == sha(RUNNER)
        and locked.get("candidate_hex") == R9_HEX_SHA
        and locked.get("workbench") == WORKBENCH_SHA
        and locked.get("final_visual_prompt") == sha(PROMPT),
        "persistent launcher locked hashes differ from current sources",
    )
    counters = stage.get("counters", {})
    require(
        "checkonly_stage",
        stage.get("status") == "READY_NO_HARDWARE_CONTACT"
        and stage.get("mode") == "check_only"
        and stage.get("hardware_contact") == 0
        and all(value == 0 for value in counters.values())
        and not stage.get("programmer_calls")
        and stage.get("locks", {}).get("swd_com", {}).get("acquired") is False,
        "CheckOnly stage touched hardware or has nonzero counters",
    )
    require(
        "checkonly_images",
        stage.get("images", {}).get("candidate", {}).get("sha256") == R9_HEX_SHA
        and stage.get("images", {}).get("baseline_a", {}).get("bytes") == 524288
        and stage.get("images", {}).get("baseline_a", {}).get("sha256") == BASELINE_SHA
        and stage.get("images", {}).get("baseline_b", {}).get("bytes") == 524288
        and stage.get("images", {}).get("baseline_b", {}).get("sha256") == BASELINE_SHA,
        "CheckOnly candidate/baseline identity differs",
    )
    require(
        "popup_policy",
        stage.get("popup_policy") == {
            "pre_execute": 0,
            "cleanup": 0,
            "recovery_or_fault_acknowledgement": 0,
            "machine_only_r8_total": None,
            "visual_acceptance": 1,
        }
        and stage.get("pre_execute_prompt", {}).get("invoked") is False
        and stage.get("operator_prompt", {}).get("required") is True
        and stage.get("operator_prompt", {}).get("invoked") is False
        and not (check_root / "operator-review.json").exists()
        and not (check_root / "operator-note.txt").exists(),
        "CheckOnly popup policy or zero-invocation evidence differs",
    )
    require(
        "durable_logs",
        stderr_path.stat().st_size == 0
        and "PASS_STATIC_PHASE_PARALLEL_R9" in stdout_path.read_text(encoding="utf-8-sig")
        and "hardware_contact=0" in stdout_path.read_text(encoding="utf-8-sig"),
        "durable CheckOnly stdout/stderr differs",
    )
    require(
        "rejected_r1_archived",
        rejected_launch.get("status") == "NO_GO_CHECK_STAGE"
        and rejected_launch.get("hardware_contact") == 0
        and rejected_launch.get("write_counter_sum") == 0
        and rejected_stage.get("status") == "READY_NO_HARDWARE_CONTACT"
        and rejected_stage.get("hardware_contact") == 0,
        "the fail-closed r1 schema rejection is missing or touched hardware",
    )
    require(
        "protected_hashes",
        sha(V9) == V9_SHA and sha(OWNER) == OWNER_SHA,
        "locked V9 source or protected owner acceptance drifted",
    )

    commands: dict[str, dict[str, Any]] = {}
    command_map = {
        "registry": [sys.executable, str(ROOT / "tools/verify_companion_product_requirements.py")],
        "current_goal": [sys.executable, str(ROOT / "tools/verify_companion_current_goal_audit.py")],
        "diff_check": [
            "git", "diff", "--check", "--",
            relative(DRIVER), relative(MAKEFILE), relative(BUILDER), relative(RUNNER),
            relative(REGISTRY),
        ],
    }
    for name, command in command_map.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        output = (proc.stdout + proc.stderr).strip()
        commands[name] = {"command": command, "returncode": proc.returncode, "output": output[-2000:]}
        require(f"command_{name}", proc.returncode == 0, f"closure command failed: {name}: {output}")

    source_files = [
        DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PROMPT, PARSER,
        STATIC_TOOL, LAUNCHER_TOOL, WORKBENCH_TOOL, MACHINE_READY_TOOL,
    ]
    whitespace_errors: list[str] = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            whitespace_errors.append(f"{relative(path)}:missing-final-newline")
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                whitespace_errors.append(f"{relative(path)}:{number}:trailing-whitespace")
    require("source_whitespace", not whitespace_errors, f"source whitespace errors: {whitespace_errors}")

    evidence_paths = [
        WORKBENCH, STATIC, LAUNCHER_STATIC, R9_HEX, R9_ELF, launch_path, stage_path,
        stdout_path, stderr_path, rejected_launch_path, rejected_stage_path,
        REGISTRY_ARTIFACT, CURRENT_GOAL,
    ]
    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9.machine_ready.v1",
        "status": (
            "MACHINE_READY_R9_NO_HARDWARE_CONTACT_EXECUTE_FORBIDDEN_PENDING_ROOT"
            if not errors
            else "NO_GO_R9_MACHINE_READY"
        ),
        "requirement": "COMP-REQ-309",
        "errors": errors,
        "checks": checks,
        "hardware_contact": 0,
        "execute_invoked": False,
        "popup_invoked": 0,
        "candidate": {
            "lut_sha256": LUT_SHA,
            "lut_byte_count": 159,
            "tail_hex": "221741A83258",
            "hex_sha256": sha(R9_HEX),
            "elf_sha256": sha(R9_ELF),
            "production_enabled": False,
            "default_enabled": False,
        },
        "waveform": {
            "shared_timing_frames": 16,
            "BW": {"drive": 16, "positive": 8, "negative": 8, "net_impulse": 0},
            "WB": {"drive": 16, "positive": 8, "negative": 8, "net_impulse": 0},
            "WW_drive": 0,
            "BB_drive": 0,
            "full_manifest_artifact": relative(STATIC),
        },
        "bounded_future_execute_contract": {
            "local_window": "32x32",
            "maximum_activations": 16,
            "control": "0xCF",
            "refresh": "0x20",
            "busy_limit_ms": 600,
            "fixed_bank": {"0x24": 0, "0x26": 1},
            "post_activation_sync": "0x24 selector0, no refresh",
            "forbidden": ["full-frame", "0xF7", "0xC7", "0xFF", "0x37", "retry", "120-frame motion"],
        },
        "popup_policy": {
            "start": 0,
            "cleanup": 0,
            "recovery": 0,
            "fault": 0,
            "final_visual_acceptance": "exactly one canonical Chinese PASS/FAIL after future machine PASS only",
            "checkonly_invoked": 0,
        },
        "restore_contract": {
            "captured_raw_bytes": 524288,
            "captured_raw_sha256": BASELINE_SHA,
            "promptless_dual_plane_preclean": True,
            "promptless_dual_plane_postclean": True,
            "normal_resume_required": True,
        },
        "persistent_checkonly": {
            "root": relative(check_root),
            "launch_sha256": sha(launch_path),
            "stage_sha256": sha(stage_path),
            "stdout_sha256": sha(stdout_path),
            "stderr_sha256": sha(stderr_path),
            "child_exit_code": launch.get("exit_code"),
            "hardware_contact": launch.get("hardware_contact"),
            "write_counter_sum": launch.get("write_counter_sum"),
        },
        "rejected_checkonly_r1": {
            "root": relative(rejected_root),
            "status": rejected_launch.get("status"),
            "reason": "SwitchParameter serialized as an object; launcher rejected the schema before any hardware contact. R2 explicitly casts the field to boolean.",
            "launch_sha256": sha(rejected_launch_path),
            "stage_sha256": sha(rejected_stage_path),
            "hardware_contact": rejected_launch.get("hardware_contact"),
            "write_counter_sum": rejected_launch.get("write_counter_sum"),
        },
        "protected_hashes": {
            "locked_v9_source_sha256": sha(V9),
            "owner_acceptance_sha256": sha(OWNER),
            "workbench_sha256": sha(WORKBENCH),
        },
        "commands": commands,
        "evidence": {
            relative(path): {"sha256": sha(path), "bytes": path.stat().st_size}
            for path in evidence_paths
        },
        "source_hashes": {relative(path): sha(path) for path in source_files},
        "machine_ready": not errors,
        "hardware_execute_allowed": False,
        "production_allowed": False,
        "next_boundary": "root review and a separate explicit hardware authorization contract; do not Execute from COMP-REQ-309",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
