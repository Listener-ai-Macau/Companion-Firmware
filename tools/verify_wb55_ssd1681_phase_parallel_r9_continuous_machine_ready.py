#!/usr/bin/env python3
"""Seal the no-hardware MACHINE_READY boundary for COMP-REQ-313."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-machine-ready-20260721.json"
PATHS = {
    "static": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-observation-static-20260721.json",
    "launcher_static": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-launcher-static-20260721.json",
    "current_goal_audit": ROOT / "docs/validation/companion-current-goal-audit-20260717.json",
    "product_requirements": ROOT / "docs/validation/companion-product-requirements.json",
    "historical_r9_disposition": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-runtime-disposition-20260721.json",
    "checkonly_launch": ROOT / ".cache/validation/wb55-r9-continuous-launcher-check-20260721-r1/persistent-launch.json",
    "checkonly_stage": ROOT / ".cache/validation/wb55-r9-continuous-launcher-check-20260721-r1/stage-run.json",
    "candidate_hex": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.hex",
    "candidate_elf": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9_continuous_observation/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation.elf",
    "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1",
    "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r9_continuous_observation.ps1",
    "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r9_continuous.ps1",
    "prompt_supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1",
    "parser": ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_continuous_log.py",
    "historical_runner": ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1",
    "historical_r9_hex": ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9/Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex",
}

EXPECTED = {
    "candidate_hex": "3B416BFF08B630D23BDB6107B2C17DFE9FBBFAAA7D5CFBCA5063AE68E62B79C5",
    "candidate_elf": "B9808E72F8490B015A9B09B6B8B896390566D06FB8ABC98C5060CEF489BE8047",
    "launcher": "C756C6048F23363787D7298D1D087A2391B1BFF7CCFE4C87F38704A29DECCCC2",
    "runner": "F608E9F1EF018EA215BD7189E415AF7490C21605C5BAE3FA8886EEC74004903A",
    "monitor": "FF60FEEA483F6844DA7B252B8910D22D6240EABCB9C42AFAE2362122C7026920",
    "prompt_supervisor": "E9CCDB0E99C6B38F0F18F46F379AB9D0A6FF7054ADE699AD32768198641CCB50",
    "parser": "859F1E3868464676859821209C765E48B8A60BCFE2E4F8E17EDC9EBE0B963A34",
    "historical_runner": "0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B",
    "historical_r9_hex": "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF",
    "historical_r9_disposition": "B5A1248CE91170631C025B8D7639D8786DBF039DD0917AD32B05A25412A8DC3D",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name: str) -> dict[str, object]:
    return json.loads(PATHS[name].read_text(encoding="utf-8-sig"))


def main() -> int:
    missing = [name for name, path in PATHS.items() if not path.is_file()]
    if missing:
        result = {"schema_id": "companion.wb55.r9_continuous_machine_ready.v1", "status": "NO_GO_MISSING_EVIDENCE", "missing": missing}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1

    static = load("static")
    launcher_static = load("launcher_static")
    audit = load("current_goal_audit")
    registry = load("product_requirements")
    historical = load("historical_r9_disposition")
    launch = load("checkonly_launch")
    stage = load("checkonly_stage")
    exception = next((item for item in audit.get("requirements", []) if item.get("id") == "ssd1681_r9_continuous_observation_exception"), {})
    hashes = {name: sha(path) for name, path in PATHS.items()}
    checks = {
        "static_pass": static.get("status") == "PASS_STATIC_R9_CONTINUOUS_OBSERVATION" and not static.get("errors"),
        "static_all_checks_true": all(static.get("checks", {}).values()),
        "launcher_static_pass": launcher_static.get("status") == "PASS_STATIC_R9_CONTINUOUS_LAUNCHER" and not launcher_static.get("errors"),
        "launcher_negative_all_true": all(launcher_static.get("checks", {}).values()),
        "checkonly_ready": launch.get("status") == "READY_NO_HARDWARE_CONTACT" and stage.get("status") == "READY_NO_HARDWARE_CONTACT",
        "zero_contact_writes_popups": launch.get("hardware_contact") == 0 and launch.get("write_counter_sum") == 0 and launch.get("popup_count") == 0 and stage.get("hardware_contact") == 0 and stage.get("operator_prompt", {}).get("invoked") is False,
        "future_acceptance_is_single_and_qualified": stage.get("operator_prompt", {}).get("required") is True and stage.get("popup_policy", {}).get("visual_acceptance") == 1 and stage.get("operator_prompt", {}).get("policy") == "one_canonical_chinese_pass_fail_concurrent_with_unbounded_local_loop_after_initial_16_pass",
        "registry_through_313": registry.get("status") == "PASS" and registry.get("requirement_ids", [])[-1:] == ["COMP-REQ-313"],
        "current_goal_exception_recorded": audit.get("status") == "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING" and exception.get("status") == "machine_ready_no_hardware_execute_forbidden_pending_root",
        "current_goal_cap_preserved": "preserves the historical 16-step qualification cap as the gate" in str(audit.get("post_safety_observation_exception")),
        "historical_r9_disposition_unchanged": historical.get("status") == "NO_GO_R9_OWNER_VISUAL_FAILED_RESTORED_STOP_NO_MOTION" and hashes["historical_r9_disposition"] == EXPECTED["historical_r9_disposition"],
        "candidate_and_tool_hashes_locked": all(hashes[name] == expected for name, expected in EXPECTED.items()),
        "same_lut_locked": static.get("identities", {}).get("lut_sha256") == "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD",
        "historical_16_step_assets_unchanged": static.get("checks", {}).get("historical_r9_function_unchanged") is True and hashes["historical_runner"] == EXPECTED["historical_runner"] and hashes["historical_r9_hex"] == EXPECTED["historical_r9_hex"],
        "bounded_telemetry": static.get("checks", {}).get("monitor_ring_default_65536") is True and static.get("checks", {}).get("monitor_checks_memory_and_disk_bound") is True,
        "fail_closed_fault_boundaries": static.get("checks", {}).get("monitor_fail_closed_boundaries") is True and static.get("checks", {}).get("prompt_fault_kills_tree_and_emergency") is True and static.get("checks", {}).get("runner_fail_closed_stops_process_trees") is True,
        "no_execute_authorization": "MACHINE_READY only" in str(launch.get("authorization_boundary")) and launch.get("authorization_artifact") is None,
    }
    errors = [name for name, passed in checks.items() if not passed]
    result = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_continuous_machine_ready.v1",
        "status": "MACHINE_READY_R9_CONTINUOUS_OBSERVATION_NO_HARDWARE_EXECUTE_FORBIDDEN_PENDING_ROOT" if not errors else "NO_GO_R9_CONTINUOUS_MACHINE_READY",
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "popup_invocation_count": 0,
        "errors": errors,
        "checks": checks,
        "contract": {
            "requirement": "COMP-REQ-313",
            "historical_qualification_changed": False,
            "fresh_qualification_activations": 16,
            "observation_loop_preset_limit": None,
            "loop_scope": "production-off physical observation only",
            "product_motion_120_frame": False,
            "lut_sha256": "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD",
            "window": "32x32 local x_bytes=1-4 y=8-39",
            "activation": "one fixed-bank 0x26/0x24 + 0x22=0xCF/0x20 + BUSY<=600 ms + post-sync 0x24 per iteration",
            "telemetry_ring_bytes": 65536,
            "acceptance_buttons": ["通过", "失败"],
            "acceptance_popup_count_if_execute_and_qualification_passes": 1,
            "other_popup_count": 0,
            "fault_cleanup": "stop prompt/loop, promptless dual-plane White postclean, exact 524288-byte restore/readback, normal resume",
        },
        "identities": hashes,
        "authorization": {
            "implementation": True,
            "isolated_build": True,
            "checkonly": True,
            "machine_ready": True,
            "execute": False,
            "hardware_contact": False,
            "production_activation": False,
            "next_boundary": "root must issue a later exact single-run authorization artifact before launcher Execute can start",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
