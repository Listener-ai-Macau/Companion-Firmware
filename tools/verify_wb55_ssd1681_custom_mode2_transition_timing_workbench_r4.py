#!/usr/bin/env python3
"""Derive the R4 uniformly scaled active-TP candidate with deterministic quantization."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R2_WORKBENCH = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r2-20260721.json"
R1_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r1-disposition-20260721.json"
R2_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r2-disposition-20260721.json"
R3_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r3-disposition-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r4-20260721.json"
R2_WORKBENCH_SHA = "266FC130BAEB68219A759A9A15E292D6E2BED97919FC5A9F0086BCC6733A5148"
R2_DISPOSITION_SHA = "05A96AED5B1989AA958B971011CCC3835231ED58BDFB5D169E7AA4DCD072197A"
R3_DISPOSITION_SHA = "65F9CC8C505B370F0D683CDD9FAA08BDF22168E8D481D322EDC30270CEE407DC"
ACTIVE_TP_GROUPS = (
    (60, 61, 63, 64, 67, 68),
    (74, 75, 77, 78, 81, 82),
)
SCALE_NUMERATOR = 4
SCALE_DENOMINATOR = 5
BUSY_LIMIT_MS = 600.0
PREDICTED_MAX_MS = 550.0
MINIMUM_MARGIN_MS = 50.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def cumulative_quantize(values: list[int]) -> list[int]:
    """Round scaled cumulative duration half-up, then take adjacent differences."""
    cumulative = 0
    previous_scaled = 0
    output: list[int] = []
    for value in values:
        cumulative += value
        scaled = (cumulative * SCALE_NUMERATOR * 2 + SCALE_DENOMINATOR) // (2 * SCALE_DENOMINATOR)
        output.append(scaled - previous_scaled)
        previous_scaled = scaled
    return output


def main() -> int:
    errors: list[str] = []
    if sha(R2_WORKBENCH) != R2_WORKBENCH_SHA:
        errors.append("R2 workbench hash drifted")
    if sha(R2_DISPOSITION) != R2_DISPOSITION_SHA:
        errors.append("R2 disposition hash drifted")
    if sha(R3_DISPOSITION) != R3_DISPOSITION_SHA:
        errors.append("R3 disposition hash drifted")

    r2_workbench = json.loads(R2_WORKBENCH.read_text(encoding="utf-8"))
    r1_disposition = json.loads(R1_DISPOSITION.read_text(encoding="utf-8"))
    r2_disposition = json.loads(R2_DISPOSITION.read_text(encoding="utf-8"))
    r3_disposition = json.loads(R3_DISPOSITION.read_text(encoding="utf-8"))
    registry = REGISTRY.read_text(encoding="utf-8")
    if "| COMP-REQ-292 |" not in registry or R3_DISPOSITION_SHA not in registry:
        errors.append("R4 registry contract or sealed R3 lineage hash missing")
    if r3_disposition.get("status") != "NO_GO_R3_BUSY_602_OVER_600_EXACT_RAW_RESTORED":
        errors.append("R3 plateau disposition missing")
    if r3_disposition.get("execution", {}).get("first_busy_elapsed_ms") != 602:
        errors.append("R3 plateau timing differs")
    if r3_disposition.get("r3_rerun_allowed") is not False:
        errors.append("R3 rerun boundary missing")

    r2_values = bytearray.fromhex(r2_workbench["candidate"]["r2_lut_hex"])
    r4_values = bytearray(r2_values)
    group_inputs: list[list[int]] = []
    group_outputs: list[list[int]] = []
    for group in ACTIVE_TP_GROUPS:
        before = [r2_values[offset] for offset in group]
        after = cumulative_quantize(before)
        group_inputs.append(before)
        group_outputs.append(after)
        for offset, value in zip(group, after):
            r4_values[offset] = value

    if group_inputs != [[2, 2, 2, 2, 1, 1], [2, 2, 2, 2, 1, 1]]:
        errors.append(f"R2 symmetric active TP groups differ: {group_inputs}")
    if group_outputs != [[2, 1, 2, 1, 1, 1], [2, 1, 2, 1, 1, 1]]:
        errors.append(f"R4 deterministic quantization differs: {group_outputs}")
    active_offsets = {offset for group in ACTIVE_TP_GROUPS for offset in group}
    differences = [
        {"offset": index, "r2_hex": f"{old:02X}", "r4_hex": f"{new:02X}"}
        for index, (old, new) in enumerate(zip(r2_values, r4_values))
        if old != new
    ]
    if {item["offset"] for item in differences} != {61, 64, 75, 78}:
        errors.append("R4 quantized byte differences differ")
    if any(index not in active_offsets for index, (old, new) in enumerate(zip(r2_values, r4_values)) if old != new):
        errors.append("R4 changes a byte outside the locked active TP set")
    if any(r4_values[offset] < 1 for offset in active_offsets):
        errors.append("R4 disables an active TP field")
    if group_outputs[0] != group_outputs[1]:
        errors.append("R4 symmetric TP groups differ")
    if r4_values[:60] != r2_values[:60] or r4_values[83:] != r2_values[83:]:
        errors.append("R4 changes voltage levels, SR/RP/FR/XON or tail")
    if r4_values[153:159].hex().upper() != "221741A83258":
        errors.append("protected voltage tail changed")

    r1_busy = r1_disposition.get("machine_result", {}).get("busy_elapsed_ms", [])
    r1_mean_ms = sum(r1_busy) / len(r1_busy) if r1_busy else 0.0
    r2_busy = float(r2_disposition.get("candidate", {}).get("first_step", {}).get("busy_elapsed_ms", 0))
    r3_busy = float(r3_disposition.get("execution", {}).get("first_busy_elapsed_ms", 0))
    r1_tp = 50
    r2_tp = sum(r2_values[offset] for offset in active_offsets)
    r4_tp = sum(r4_values[offset] for offset in active_offsets)
    slope = (r1_mean_ms - max(r2_busy, r3_busy)) / (r1_tp - r2_tp)
    fixed = max(r2_busy, r3_busy) - slope * r2_tp
    predicted = fixed + slope * r4_tp
    margin = BUSY_LIMIT_MS - predicted
    if (r2_tp, r4_tp) != (20, 16):
        errors.append(f"aggregate TP oracle differs: {(r2_tp, r4_tp)}")
    if predicted > PREDICTED_MAX_MS or margin < MINIMUM_MARGIN_MS:
        errors.append("TP16 does not meet the R4 predicted timing threshold")

    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_transition_timing_workbench.v3",
        "status": "PASS_WORKBENCH_ADMIT_UNIFORM_ACTIVE_TP16_MODE2_R4" if not errors else "NO_GO_WORKBENCH_R4",
        "errors": errors,
        "hardware_contact": 0,
        "requirements": ["COMP-REQ-285", "COMP-REQ-289", "COMP-REQ-292"],
        "plateau_evidence": {
            "r3_disposition_sha256": sha(R3_DISPOSITION),
            "r3_change": "one active TP field 0x02 to 0x01",
            "r2_busy_ms": r2_busy,
            "r3_busy_ms": r3_busy,
            "conclusion": "single-field one-count decrement had no observed physical timing effect",
        },
        "timing_model": {
            "type": "R1-to-max(R2,R3) linear estimate for candidate selection only",
            "r1_tp_frame_counts": r1_tp,
            "r1_busy_mean_ms": round(r1_mean_ms, 3),
            "r2_tp_frame_counts": r2_tp,
            "r2_r3_conservative_anchor_ms": max(r2_busy, r3_busy),
            "estimated_ms_per_tp_count": round(slope, 3),
            "estimated_fixed_overhead_ms": round(fixed, 3),
            "r4_tp_frame_counts": r4_tp,
            "predicted_r4_busy_ms": round(predicted, 3),
            "predicted_margin_ms": round(margin, 3),
            "required_predicted_max_ms": PREDICTED_MAX_MS,
            "required_minimum_margin_ms": MINIMUM_MARGIN_MS,
            "boundary": "prediction selects the candidate; hardware BUSY remains authoritative",
        },
        "candidate": {
            "name": "stationary_suppression_uniform_tp16_r4",
            "single_mechanism_variable": "uniform 4/5 aggregate scale of both complete symmetric active-TP groups with cumulative half-up integer allocation",
            "active_tp_groups": [list(group) for group in ACTIVE_TP_GROUPS],
            "group_inputs": group_inputs,
            "group_outputs": group_outputs,
            "all_active_fields_nonzero": True,
            "r2_lut_sha256": r2_workbench["candidate"]["r2_lut_sha256"],
            "r4_lut_hex": r4_values.hex().upper(),
            "r4_lut_sha256": sha_bytes(bytes(r4_values)),
            "byte_differences_from_r2": differences,
            "protected_tail_hex": r4_values[153:159].hex().upper(),
        },
        "machine_limits": {
            "safety_activations": 9,
            "busy_per_activation_max_ms": 600,
            "full_frame_candidate_activations": 0,
            "motion_120_frame_admitted": False,
            "r2_r3_rerun_allowed": False,
        },
        "runner_contract": {
            "detached_execute_required": True,
            "fresh_output_directory_required": True,
            "canonical_r4_pre_execute_prompt": True,
            "deterministic_white_preclean_first": True,
            "exact_raw_restore_readback_normal_resume": True,
        },
        "source_hashes": {
            str(R2_WORKBENCH): sha(R2_WORKBENCH),
            str(R1_DISPOSITION): sha(R1_DISPOSITION),
            str(R2_DISPOSITION): sha(R2_DISPOSITION),
            str(R3_DISPOSITION): sha(R3_DISPOSITION),
        },
        "production_allowed": False,
        "goal_terminal": False,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors, "lut_sha256": report["candidate"]["r4_lut_sha256"], "predicted_busy_ms": report["timing_model"]["predicted_r4_busy_ms"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
