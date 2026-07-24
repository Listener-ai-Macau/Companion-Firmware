#!/usr/bin/env python3
"""Derive the R2 TP-duration-only custom Mode2 candidate from admitted R1."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R1_WORKBENCH = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-workbench-20260721.json"
R1_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r1-disposition-20260721.json"
WHITE_RECOVERY = ROOT / "docs/validation/companion-ssd1681-official-white-clean-recovery-r1-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r2-20260721.json"
R1_WORKBENCH_SHA = "8653B6ABD0E299E6C99B50C5A086EE840E38CED37F358F7AA326B37F7933CF05"
TP_CHANGES = {
    60: 2, 61: 2, 63: 2, 64: 2,
    67: 1, 68: 1,
    74: 2, 75: 2, 77: 2, 78: 2,
    81: 1, 82: 1,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    errors: list[str] = []
    if sha(R1_WORKBENCH) != R1_WORKBENCH_SHA:
        errors.append("R1 workbench hash drifted")
    r1 = json.loads(R1_WORKBENCH.read_text(encoding="utf-8"))
    disposition = json.loads(R1_DISPOSITION.read_text(encoding="utf-8"))
    white = json.loads(WHITE_RECOVERY.read_text(encoding="utf-8"))
    registry = REGISTRY.read_text(encoding="utf-8")
    if disposition.get("status") != "NO_GO_BUSY_OVER_LIMIT_AND_OPERATOR_FAILED_RESTORED":
        errors.append("R1 NO_GO disposition missing")
    if max(disposition.get("machine_result", {}).get("busy_elapsed_ms", [0])) <= 600:
        errors.append("R1 does not prove the >600 ms timing defect")
    if white.get("status") != "PASS_OFFICIAL_WHITE_CLEAN_EXACT_RAW_RESTORED":
        errors.append("owner-requested White recovery is not closed")
    if "COMP-REQ-289" not in registry or "以后你实验前都恢复一下再实验" not in registry:
        errors.append("mandatory White pre-clean steering missing")

    r1_values = bytearray.fromhex(r1["candidate"]["candidate_lut_hex"])
    r2_values = bytearray(r1_values)
    for offset, value in TP_CHANGES.items():
        r2_values[offset] = value
    differences = [
        {"offset": index, "r1_hex": f"{old:02X}", "r2_hex": f"{new:02X}"}
        for index, (old, new) in enumerate(zip(r1_values, r2_values)) if old != new
    ]
    if [item["offset"] for item in differences] != list(TP_CHANGES):
        errors.append("R2 changes bytes outside locked TP offsets")
    if r2_values[:60] != r1_values[:60] or r2_values[83:] != r1_values[83:]:
        errors.append("R2 changes voltage tables or non-TP timing/tail bytes")
    for offset in range(60, 83):
        if offset not in TP_CHANGES and r2_values[offset] != r1_values[offset]:
            errors.append(f"R2 changes non-TP byte {offset}")
    if r2_values[153:159].hex().upper() != "221741A83258":
        errors.append("protected voltage tail changed")
    if r2_values[0:60] != r1_values[0:60]:
        errors.append("transition voltage tables changed")

    r1_active_tp = sum(r1_values[offset] for offset in TP_CHANGES)
    r2_active_tp = sum(r2_values[offset] for offset in TP_CHANGES)
    if (r1_active_tp, r2_active_tp) != (50, 20):
        errors.append(f"TP frame-count oracle differs: {(r1_active_tp, r2_active_tp)}")

    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_transition_timing_workbench.v1",
        "status": "PASS_WORKBENCH_ADMIT_TP_DURATION_SCALE_MODE2_R2" if not errors else "NO_GO_WORKBENCH_R2",
        "errors": errors,
        "hardware_contact": 0,
        "requirements": ["COMP-REQ-285", "COMP-REQ-289"],
        "evidence_basis": {
            "r1_status": disposition.get("status"),
            "r1_busy_elapsed_ms": disposition.get("machine_result", {}).get("busy_elapsed_ms"),
            "r1_busy_limit_ms": 600,
            "white_recovery_status": white.get("status"),
        },
        "candidate": {
            "name": "stationary_suppression_tp_scale_r2",
            "single_mechanism_variable": "scale only active TP phase durations; voltage-state tables, SR, RP, FR, XON and voltage tail remain R1-exact",
            "r1_lut_sha256": r1["candidate"]["candidate_lut_sha256"],
            "r2_lut_hex": r2_values.hex().upper(),
            "r2_lut_sha256": sha_bytes(bytes(r2_values)),
            "byte_differences_from_r1": differences,
            "r1_active_tp_frame_counts": r1_active_tp,
            "r2_active_tp_frame_counts": r2_active_tp,
            "duration_ratio": 0.4,
            "protected_tail_hex": r2_values[153:159].hex().upper(),
        },
        "machine_limits": {
            "safety_activations": 9,
            "busy_per_activation_max_ms": 600,
            "full_frame_candidate_activations": 0,
            "motion_120_frame_admitted": False,
        },
        "future_runner_contract": {
            "canonical_pre_execute_candidate_prompt": True,
            "prompt_discloses_official_white_preclean_first": True,
            "official_white_preclean": "one 5000-byte 0x24 + F7/20/BUSY source/hash-bound stage",
            "preclean_excluded_from_candidate_metrics": True,
            "preclean_cannot_mask_post_candidate_residue": True,
            "exact_raw_restore_readback_normal_resume": True,
        },
        "source_hashes": {
            str(R1_WORKBENCH): sha(R1_WORKBENCH),
            str(R1_DISPOSITION): sha(R1_DISPOSITION),
            str(WHITE_RECOVERY): sha(WHITE_RECOVERY),
        },
        "production_allowed": False,
        "goal_terminal": False,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors, "lut_sha256": report["candidate"]["r2_lut_sha256"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
