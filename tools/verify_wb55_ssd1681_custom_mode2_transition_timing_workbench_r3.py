#!/usr/bin/env python3
"""Fit the R1/R2 timing model and derive the minimum-integer R3 TP candidate."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R2_WORKBENCH = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r2-20260721.json"
R1_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r1-disposition-20260721.json"
R2_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r2-disposition-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r3-20260721.json"
R2_WORKBENCH_SHA = "266FC130BAEB68219A759A9A15E292D6E2BED97919FC5A9F0086BCC6733A5148"
R2_DISPOSITION_SHA = "05A96AED5B1989AA958B971011CCC3835231ED58BDFB5D169E7AA4DCD072197A"
R3_CHANGED_OFFSET = 74
BUSY_LIMIT_MS = 600.0
MINIMUM_PREDICTED_MARGIN_MS = 15.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    errors: list[str] = []
    if sha(R2_WORKBENCH) != R2_WORKBENCH_SHA:
        errors.append("R2 workbench hash drifted")
    if sha(R2_DISPOSITION) != R2_DISPOSITION_SHA:
        errors.append("R2 disposition hash drifted")

    r2_workbench = json.loads(R2_WORKBENCH.read_text(encoding="utf-8"))
    r1_disposition = json.loads(R1_DISPOSITION.read_text(encoding="utf-8"))
    r2_disposition = json.loads(R2_DISPOSITION.read_text(encoding="utf-8"))
    registry = REGISTRY.read_text(encoding="utf-8")
    if "COMP-REQ-291" not in registry:
        errors.append("R3 registry contract missing")
    if r1_disposition.get("status") != "NO_GO_BUSY_OVER_LIMIT_AND_OPERATOR_FAILED_RESTORED":
        errors.append("R1 timing control disposition missing")
    if r2_disposition.get("status") != "NO_GO_R2_BUSY_602_OVER_600_EXACT_RAW_RESTORED":
        errors.append("R2 timing control disposition missing")
    if r2_disposition.get("candidate", {}).get("actual_local_activations") != 1:
        errors.append("R2 must remain a one-activation NO_GO and must not be rerun")

    r1_busy = r1_disposition.get("machine_result", {}).get("busy_elapsed_ms", [])
    r2_busy = float(r2_disposition.get("candidate", {}).get("first_step", {}).get("busy_elapsed_ms", 0))
    r1_tp = 50
    r2_tp = int(r2_workbench.get("candidate", {}).get("r2_active_tp_frame_counts", 0))
    r3_tp = r2_tp - 1
    if len(r1_busy) != 9 or min(r1_busy, default=0) < 1284 or max(r1_busy, default=0) > 1285:
        errors.append("R1 measured timing distribution differs")
    if r2_busy != 602.0 or r2_tp != 20 or r3_tp != 19:
        errors.append("R2/R3 timing anchors differ")

    r1_mean_ms = sum(r1_busy) / len(r1_busy) if r1_busy else 0.0
    ms_per_tp_count = (r1_mean_ms - r2_busy) / (r1_tp - r2_tp) if r1_tp != r2_tp else 0.0
    fixed_overhead_ms = r2_busy - ms_per_tp_count * r2_tp
    predicted_r3_ms = fixed_overhead_ms + ms_per_tp_count * r3_tp
    predicted_margin_ms = BUSY_LIMIT_MS - predicted_r3_ms
    if not (22.0 <= ms_per_tp_count <= 23.5):
        errors.append("two-point TP slope is outside the measured oracle")
    if predicted_margin_ms < MINIMUM_PREDICTED_MARGIN_MS:
        errors.append("TP19 does not provide the required predicted margin")

    r2_values = bytearray.fromhex(r2_workbench["candidate"]["r2_lut_hex"])
    r3_values = bytearray(r2_values)
    if r2_values[R3_CHANGED_OFFSET] != 0x02:
        errors.append("R2 selected TP byte is not 0x02")
    r3_values[R3_CHANGED_OFFSET] = 0x01
    differences = [
        {"offset": index, "r2_hex": f"{old:02X}", "r3_hex": f"{new:02X}"}
        for index, (old, new) in enumerate(zip(r2_values, r3_values))
        if old != new
    ]
    if differences != [{"offset": R3_CHANGED_OFFSET, "r2_hex": "02", "r3_hex": "01"}]:
        errors.append("R3 must change exactly one admitted TP duration byte")
    if r3_values[:R3_CHANGED_OFFSET] != r2_values[:R3_CHANGED_OFFSET] or r3_values[R3_CHANGED_OFFSET + 1 :] != r2_values[R3_CHANGED_OFFSET + 1 :]:
        errors.append("R3 changes bytes outside the selected TP duration")
    if r3_values[153:159].hex().upper() != "221741A83258":
        errors.append("protected voltage tail changed")
    if r3_values[:60] != r2_values[:60] or r3_values[83:] != r2_values[83:]:
        errors.append("R3 changes voltage tables, SR/RP/FR/XON or tail")

    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_transition_timing_workbench.v2",
        "status": "PASS_WORKBENCH_ADMIT_MINIMUM_INTEGER_TP19_MODE2_R3" if not errors else "NO_GO_WORKBENCH_R3",
        "errors": errors,
        "hardware_contact": 0,
        "requirements": ["COMP-REQ-285", "COMP-REQ-289", "COMP-REQ-291"],
        "timing_model": {
            "type": "two_point_linear_estimate_for_candidate_selection_only",
            "r1_tp_frame_counts": r1_tp,
            "r1_busy_elapsed_ms": r1_busy,
            "r1_busy_mean_ms": round(r1_mean_ms, 3),
            "r2_tp_frame_counts": r2_tp,
            "r2_busy_elapsed_ms": r2_busy,
            "estimated_ms_per_tp_count": round(ms_per_tp_count, 3),
            "estimated_fixed_overhead_ms": round(fixed_overhead_ms, 3),
            "r3_tp_frame_counts": r3_tp,
            "predicted_r3_busy_ms": round(predicted_r3_ms, 3),
            "busy_limit_ms": BUSY_LIMIT_MS,
            "predicted_margin_ms": round(predicted_margin_ms, 3),
            "minimum_required_predicted_margin_ms": MINIMUM_PREDICTED_MARGIN_MS,
            "boundary": "prediction selects the smallest integer candidate; hardware BUSY remains the authoritative gate",
        },
        "candidate": {
            "name": "stationary_suppression_tp19_r3",
            "single_mechanism_variable": "decrement exactly one active TP duration byte so total active TP frame-counts change from 20 to 19",
            "selected_offset": R3_CHANGED_OFFSET,
            "selection_reason": "minimum integer decrement on the long transition timing group exercised by the R2 first W-to-B safety step",
            "r2_lut_sha256": r2_workbench["candidate"]["r2_lut_sha256"],
            "r3_lut_hex": r3_values.hex().upper(),
            "r3_lut_sha256": sha_bytes(bytes(r3_values)),
            "byte_differences_from_r2": differences,
            "protected_tail_hex": r3_values[153:159].hex().upper(),
        },
        "machine_limits": {
            "safety_activations": 9,
            "maximum_activations": 16,
            "busy_per_activation_max_ms": 600,
            "full_frame_candidate_activations": 0,
            "motion_120_frame_admitted": False,
            "r2_rerun_allowed": False,
        },
        "runner_contract": {
            "detached_execute_required": True,
            "durable_stdout_stderr_required": True,
            "output_directory_reuse_forbidden": True,
            "canonical_pre_execute_candidate_prompt": True,
            "deterministic_white_preclean_first": True,
            "exact_raw_restore_readback_normal_resume": True,
        },
        "source_hashes": {
            str(R2_WORKBENCH): sha(R2_WORKBENCH),
            str(R1_DISPOSITION): sha(R1_DISPOSITION),
            str(R2_DISPOSITION): sha(R2_DISPOSITION),
        },
        "production_allowed": False,
        "goal_terminal": False,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors, "lut_sha256": report["candidate"]["r3_lut_sha256"], "predicted_busy_ms": report["timing_model"]["predicted_r3_busy_ms"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
