#!/usr/bin/env python3
"""Validate the paused SSD1681 lower-driver handoff without hardware access."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_JSON = ROOT / "docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-20260721.json"
HANDOFF_MD = ROOT / "docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-20260721.md"
CHECK_JSON = ROOT / "docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-check-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
CURRENT_GOAL = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"

PROTECTED_HASHES = {
    "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png": "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA",
    "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json": "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json": "DA2FE11DB4CB1AFC5D433B2798BADBB576FC9C82BB39C472236E084C48F1EC57",
    "docs/validation/companion-ssd1681-ram-command-target-r8-r2-runtime-20260721.json": "BAD97BBABFD2E1B515A2E1D1A45EE3C4E68EF3FFC167D03468E1859659C07FF5",
    "docs/validation/companion-ssd1681-phase-parallel-r9-workbench-20260721.json": "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF",
    "docs/validation/companion-ssd1681-phase-parallel-r9-runtime-disposition-20260721.json": "B5A1248CE91170631C025B8D7639D8786DBF039DD0917AD32B05A25412A8DC3D",
    "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-runtime-disposition-20260721.json": "976018FA78CAE8B17B4A06D0AD2CC415DC72598AAE087F5F041B16C3040631DD",
    "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-machine-ready-20260721.json": "59DA81BDCDC31AB93459BFCA6575F5A007182374912D1A476B54B747A106D5E7",
    "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-runtime-disposition-20260721.json": "C7F097CE905AA84F687C9E2EC6E5FEAEDED8D0D6C9C98DF8E09F3624797DE0CA",
    "tools/supervise_wb55_ssd1681_phase_parallel_r9_continuous_prompt.ps1": "39ACC31A561413717B77ACAFE5E7E562B0C44734F07D72007B46C900C85883D2",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    checks: OrderedDict[str, bool] = OrderedDict()

    def check(name: str, condition: bool) -> None:
        checks[name] = condition
        if not condition:
            failures.append(name)

    check("handoff_json_exists", HANDOFF_JSON.is_file())
    check("handoff_markdown_exists", HANDOFF_MD.is_file())
    check("registry_exists", REGISTRY.is_file())
    check("current_goal_exists", CURRENT_GOAL.is_file())
    check("driver_exists", DRIVER.is_file())
    if failures:
        print("FAIL: required handoff inputs are missing")
        return 1

    handoff = load_json(HANDOFF_JSON)
    current_goal = load_json(CURRENT_GOAL)
    registry = REGISTRY.read_text(encoding="utf-8")
    markdown = HANDOFF_MD.read_text(encoding="utf-8")
    driver = DRIVER.read_text(encoding="utf-8")

    check("schema", handoff.get("schema_id") == "companion.wb55.ssd1681_lower_driver.next_agent_handoff.v1")
    check("status", handoff.get("status") == "HANDOFF_COMPLETE_OWNER_PAUSED_R10_NOT_STARTED")
    check("requirement", handoff.get("requirement") == "COMP-REQ-320")
    check("status_legend_complete", set(handoff.get("status_legend", {})) == {"MACHINE PASS", "MACHINE FAIL", "HUMAN PASS", "HUMAN FAIL", "NOT OBSERVED", "NOT RUN"})
    pause = handoff.get("pause", {})
    check("owner_pause_active", pause.get("status") == "ACTIVE")
    check("pause_forbids_candidate_work", all(pause.get(key) is False for key in ("implementation", "build", "flash", "execute", "hardware_contact", "popup")))
    check("r10_planned_not_started", pause.get("r10") == "PLANNED_NOT_STARTED" and handoff.get("r10_plan", {}).get("implementation_status") == "NOT_STARTED")
    check("r10_not_machine_ready_or_authorized", handoff.get("r10_plan", {}).get("machine_ready") is False and handoff.get("r10_plan", {}).get("hardware_authorized") is False)

    supplier = handoff.get("supplier_159_byte_decode", {})
    check("supplier_lut_hash", supplier.get("source_lut_sha256") == "F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15")
    check("supplier_153_plus_tail", supplier.get("total_bytes") == 159 and supplier.get("command_0x32_payload_bytes") == 153 and supplier.get("tail_hex") == "221741A83258")
    check("supplier_tail_commands", supplier.get("tail_commands") == {"0x3F": ["0x22"], "0x03": ["0x17"], "0x04": ["0x41", "0xA8", "0x32"], "0x2C": ["0x58"]})

    baseline = handoff.get("best_visual_baseline", {})
    check("accepted_baseline_statuses", baseline.get("machine_status") == "MACHINE PASS" and baseline.get("human_status") == "HUMAN PASS")
    check("accepted_baseline_note", baseline.get("owner_note") == "好很多, 就是移动的时候移动方向会切掉一点, 随后还原, 能优化吗")
    check("accepted_baseline_hash", baseline.get("sha256") == PROTECTED_HASHES["docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json"])
    check("partial_history_coverage", len(handoff.get("partial_topology_history", [])) >= 11)

    rounds = {item.get("round"): item for item in handoff.get("custom_lut_rounds", [])}
    check("custom_rounds_r1_to_r6", set(rounds) == {"R1", "R2", "R3", "R4", "R5", "R6"})
    check("r1_r3_machine_fail", all(rounds[name].get("machine") == "MACHINE FAIL" for name in ("R1", "R2", "R3")))
    check("r4_r6_machine_pass", all(rounds[name].get("machine") == "MACHINE PASS" for name in ("R4", "R5", "R6")))
    check("r6_human_fail_note", rounds["R6"].get("human") == "HUMAN FAIL" and "没有图案了直接" in rounds["R6"].get("note", ""))

    phase = handoff.get("phase_a_r7_r8", {})
    check("phase_a_mapping", phase.get("phase_a", {}).get("mapping_after_activation") == "selector0=P and selector1=N")
    check("r7_no_go_not_run", phase.get("r7", {}).get("candidate") == "NOT RUN" and str(phase.get("r7", {}).get("decision", "")).startswith("NO_GO_R7"))
    check("r8_fixed_bank", phase.get("r8_r2", {}).get("mapping") == "fixed_bank" and phase.get("r8_r2", {}).get("command_0x24_target_selector") == 0 and phase.get("r8_r2", {}).get("command_0x26_target_selector") == 1)

    lineage = handoff.get("r9_lineage", {})
    check("r9_lut_hash", lineage.get("workbench", {}).get("lut_sha256") == "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD")
    check("r9_one_shot_machine_human_split", lineage.get("one_shot", {}).get("machine") == "MACHINE PASS" and lineage.get("one_shot", {}).get("human") == "HUMAN FAIL")
    check("r9_r1_no_visual", lineage.get("continuous_r1", {}).get("visual") == "NOT OBSERVED" and lineage.get("continuous_r1", {}).get("popup") == "NOT RUN")
    r2 = lineage.get("continuous_r2", {})
    check("r9_r2_machine_human_split", r2.get("machine") == "MACHINE PASS" and r2.get("human") == "HUMAN FAIL")
    check("r9_r2_note_hash", r2.get("operator_note_sha256") == "30DDA3C9CC92110E636C9954652716EA805086DD15E889ED26B4F88D720B5698")
    check("r9_r2_disposition_hash", r2.get("runtime_disposition_sha256") == PROTECTED_HASHES["docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-runtime-disposition-20260721.json"])
    check("restore_hash", handoff.get("cleanup_restore_contract", {}).get("protected_restore_sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C")

    current = handoff.get("current_state", {})
    check("handoff_zero_contact", current.get("handoff_hardware_contact") == 0 and current.get("handoff_popup_count") == 0)
    check("archived_no_processes", current.get("live_process_matches") == [] and current.get("known_run_pids_alive") == [])
    check("first_30_minutes", len(handoff.get("next_agent_first_30_minutes", [])) == 6)
    gates = handoff.get("stop_go_gates", {})
    check("stop_go_gates", all(gates.get(name) for name in ("stop_now", "go_to_implementation_only", "go_to_machine_ready_only", "go_to_hardware_only", "always_stop_after_future_run")))
    check("admission_questions", len(handoff.get("r10_plan", {}).get("admission_questions", [])) >= 6)

    check("registry_comp320_unique", registry.count("| COMP-REQ-320 |") == 1)
    check("registry_pause_text", "R10 remains planned but NOT STARTED" in registry and "pauses all lower-driver implementation, build, flash, Execute" in registry)
    check("current_goal_r2_closed", "r2_owner_visual_failed_restored_owner_pause_r10_not_started" in json.dumps(current_goal, ensure_ascii=False))
    check("driver_has_no_r10_scaffold", "R10_BALL" not in driver)
    check("r10_oracle_tool_absent", not (ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r10_ball_pixel_oracle.py").exists())
    check("r10_oracle_artifact_absent", not (ROOT / "docs/validation/companion-ssd1681-phase-parallel-r10-ball-pixel-oracle-20260721.json").exists())

    required_markdown = [
        "## 2. 产品与来源边界",
        "## 3. 159 字节供应商 LUT",
        "## 5. 当前最佳视觉基线",
        "## 6. 所有相关 partial topology",
        "## 8. Custom LUT R1-R6",
        "## 9. R9 lineage",
        "## 10. Popup policy 演化",
        "## 12. Runner、PowerShell 与 timeout 陷阱",
        "## 13. 绝不能重跑",
        "## 15. R10 方向：计划但 NOT STARTED",
        "## 16. 下一位前 30 分钟",
        "## 17. Stop/Go gates",
    ]
    check("markdown_sections", all(token in markdown for token in required_markdown))
    check("markdown_status_distinctions", all(token in markdown for token in ("`MACHINE PASS`", "`MACHINE FAIL`", "`HUMAN PASS`", "`HUMAN FAIL`", "`NOT OBSERVED`", "`NOT RUN`")))

    actual_hashes: dict[str, str] = {}
    for relative, expected in PROTECTED_HASHES.items():
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else "MISSING"
        actual_hashes[relative] = actual
        check(f"protected_hash:{relative}", actual == expected)

    artifact = {
        "schema_id": "companion.wb55.ssd1681_lower_driver.next_agent_handoff_check.v1",
        "status": "PASS_HANDOFF_SCHEMA_HASH_BOUNDARIES_NO_HARDWARE" if not failures else "NO_GO_HANDOFF_CHECK",
        "requirement": "COMP-REQ-320",
        "hardware_contact": 0,
        "popup_count": 0,
        "checks": checks,
        "failures": failures,
        "source_hashes": {
            HANDOFF_JSON.relative_to(ROOT).as_posix(): sha256(HANDOFF_JSON),
            HANDOFF_MD.relative_to(ROOT).as_posix(): sha256(HANDOFF_MD),
            REGISTRY.relative_to(ROOT).as_posix(): sha256(REGISTRY),
            CURRENT_GOAL.relative_to(ROOT).as_posix(): sha256(CURRENT_GOAL),
            **actual_hashes,
        },
        "claims_not_made": [
            "no build",
            "no flash",
            "no panel/programmer/device contact",
            "no popup",
            "no R10 implementation or MACHINE_READY claim",
        ],
    }
    rendered = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"

    if args.write:
        CHECK_JSON.write_text(rendered, encoding="utf-8")
    elif not CHECK_JSON.is_file():
        failures.append("check_artifact_missing")
    elif CHECK_JSON.read_text(encoding="utf-8") != rendered:
        failures.append("check_artifact_stale")

    if failures:
        print("FAIL: SSD1681 lower-driver handoff")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print(f"PASS: SSD1681 lower-driver handoff -> {CHECK_JSON.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
