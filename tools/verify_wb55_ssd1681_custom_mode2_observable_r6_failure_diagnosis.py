#!/usr/bin/env python3
"""Research-only diagnosis of the R6 optical failure against supplier LUT semantics."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
R1 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-workbench-20260721.json"
R4 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r4-20260721.json"
MAPPING = ROOT / "docs/validation/companion-ssd1681-custom-mode2-mapping-r5-disposition-20260721.json"
R6_RUNTIME = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-runtime-20260721.json"
R6_OPERATOR = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-operator-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-failure-diagnosis-20260721.json"
EXPECTED_HASHES = {
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    R1: "8653B6ABD0E299E6C99B50C5A086EE840E38CED37F358F7AA326B37F7933CF05",
    R4: "E7467B808CE7BD1BE317BC282B7990CF343922DE8C15B092588B9968DEAB444D",
    MAPPING: "3EDF9BF927291D78DC4119C160B25B985350803502C0A5F5C297774C574FCD39",
    R6_RUNTIME: "6CB1E7D395D6CACF4297D5E95FCE3E74A078D446762F27A57738F3FD6A6359DE",
    R6_OPERATOR: "A031EAE5E7FE365741D023F715F04973B78D69012FDC2149B57F0623F81F77D0",
}
STATIONARY_OFFSETS = [0, 1, 2, 3, 36, 37, 38, 39]
TIMING_OFFSETS = [60, 61, 63, 64, 67, 68, 74, 75, 77, 78, 81, 82]
GROUPS = ([60, 61, 63, 64, 67, 68], [74, 75, 77, 78, 81, 82])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def supplier_lut(source: str) -> bytes:
    match = re.search(r"const\s+unsigned\s+char\s+LUT_DATA\s*\[159\]\s*=\s*\{(.*?)\};", source, re.S)
    return bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})", match.group(1))) if match else b""


def main() -> int:
    errors: list[str] = []
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file() or sha(path) != expected:
            errors.append(f"sealed input missing or drifted: {path}")
    if errors:
        print(json.dumps({"status": "NO_GO_R6_FAILURE_DIAGNOSIS", "errors": errors}))
        return 1

    source = SUPPLIER.read_text(encoding="utf-8", errors="replace")
    supplier = supplier_lut(source)
    r1 = json.loads(R1.read_text(encoding="utf-8"))
    r4 = json.loads(R4.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    runtime = json.loads(R6_RUNTIME.read_text(encoding="utf-8"))
    operator = json.loads(R6_OPERATOR.read_text(encoding="utf-8"))
    registry = REGISTRY.read_text(encoding="utf-8")
    r4_lut = bytes.fromhex(r4.get("candidate", {}).get("r4_lut_hex", ""))
    r1_supplier = bytes.fromhex(r1.get("candidate", {}).get("supplier_lut_hex", ""))
    if len(supplier) != 159 or supplier != r1_supplier:
        errors.append("supplier active LUT parse differs from sealed R1 source copy")
    if len(r4_lut) != 159:
        errors.append("R4/R6 TP16 LUT is not 159 bytes")
    if registry.count("| COMP-REQ-300 |") != 1:
        errors.append("COMP-REQ-300 missing or non-unique")
    if runtime.get("status") != "PASS_MACHINE_CUSTOM_MODE2_OBSERVABLE_R6_RESTORED":
        errors.append("R6 machine PASS/restore evidence missing")
    if operator.get("selected") != "失败" or operator.get("note") != "这个不太行, 应该方向是错误的, 没有图案了直接":
        errors.append("R6 canonical hard-failure note differs")
    if mapping.get("status") != "PASS_R5_MAPPING_CONFIRMS_LUT0_LUT3_TARGETING_NO_NEW_HARDWARE_CANDIDATE":
        errors.append("sealed controller mapping audit differs")

    differences = [
        {"offset": index, "supplier_hex": f"{old:02X}", "tp16_hex": f"{new:02X}"}
        for index, (old, new) in enumerate(zip(supplier, r4_lut)) if old != new
    ]
    difference_offsets = [item["offset"] for item in differences]
    if difference_offsets != STATIONARY_OFFSETS + TIMING_OFFSETS:
        errors.append(f"supplier-to-TP16 difference set differs: {difference_offsets}")
    supplier_groups = [[supplier[index] for index in group] for group in GROUPS]
    tp16_groups = [[r4_lut[index] for index in group] for group in GROUPS]
    if supplier_groups != [[5, 5, 5, 5, 3, 2], [5, 5, 5, 5, 3, 2]]:
        errors.append(f"supplier transition timing groups differ: {supplier_groups}")
    if tp16_groups != [[2, 1, 2, 1, 1, 1], [2, 1, 2, 1, 1, 1]]:
        errors.append(f"TP16 transition timing groups differ: {tp16_groups}")
    supplier_group_sum = sum(supplier_groups[0]) if supplier_groups else 0
    tp16_group_sum = sum(tp16_groups[0]) if tp16_groups else 0
    ratio = tp16_group_sum / supplier_group_sum if supplier_group_sum else 0.0
    lut1_lut2_exact = r4_lut[12:36] == supplier[12:36]
    stationary_zeroed = all(r4_lut[index] == 0 for index in STATIONARY_OFFSETS)
    tail_exact = r4_lut[153:159] == supplier[153:159] == bytes.fromhex("221741A83258")
    source_full_lut_topology = all(token in source for token in (
        "Epaper_Write_Command(0x24)", "EPD_Update_LUT();", "Epaper_Write_Data(0xC7)",
        "Epaper_Write_Command(0x32)", "for(count=0;count<153;count++)",
    ))

    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_observable_r6_failure_diagnosis.v1",
        "status": "PASS_RESEARCH_R6_FAILURE_DIAGNOSIS_NO_NEW_HARDWARE_CANDIDATE" if not errors else "NO_GO_R6_FAILURE_DIAGNOSIS",
        "errors": errors,
        "hardware_contact": 0,
        "requirement": "COMP-REQ-300",
        "observed_failure": {
            "machine_status": runtime.get("status"),
            "activations": runtime.get("candidate", {}).get("activation_records"),
            "observation_elapsed_ms": runtime.get("candidate", {}).get("observation_elapsed_ms"),
            "busy_elapsed_ms": runtime.get("candidate", {}).get("busy_elapsed_ms"),
            "canonical_selected": operator.get("selected"),
            "canonical_note": operator.get("note"),
        },
        "supplier_vs_tp16": {
            "supplier_lut_sha256": hashlib.sha256(supplier).hexdigest().upper(),
            "tp16_lut_sha256": hashlib.sha256(r4_lut).hexdigest().upper(),
            "difference_count": len(differences),
            "differences": differences,
            "stationary_tables": {
                "mapping": {"LUT0": "BB", "LUT3": "WW"},
                "supplier_nonzero_offsets": STATIONARY_OFFSETS,
                "tp16_zeroed": stationary_zeroed,
                "effect": "TP16 intentionally supplies no reinforcing drive for already-black BB or already-white WW cells",
            },
            "transition_tables": {
                "mapping": {"LUT1": "BW", "LUT2": "WB"},
                "voltage_code_bytes_12_through_35_supplier_exact": lut1_lut2_exact,
                "supplier_timing_groups": supplier_groups,
                "tp16_timing_groups": tp16_groups,
                "supplier_frame_count_per_symmetric_group": supplier_group_sum,
                "tp16_frame_count_per_symmetric_group": tp16_group_sum,
                "tp16_to_supplier_duration_ratio": ratio,
                "duration_reduction_percent": round((1.0 - ratio) * 100.0, 1),
            },
            "protected_tail_equal": tail_exact,
        },
        "first_activation_optical_obligation": {
            "transition": "W->A",
            "classes": {"WW": 512, "WB": 512, "BW": 0, "BB": 0},
            "required_visible_effect": "the 512 WB pixels must darken through LUT2 to make pattern A visible",
            "actual_owner_observation": "no pattern; it disappeared directly",
        },
        "diagnosis": {
            "mapping_error_found": False,
            "transport_error_found": False,
            "strongest_evidence_backed_hypothesis": (
                "TP16 kept the supplier BW/WB voltage-code tables but reduced each active transition timing group "
                "from 25 to 8 frame counts (32 percent of supplier duration) while also removing all BB/WW "
                "reinforcement. The first W-to-A activation therefore depended entirely on the shortened WB "
                "drive for 512 pixels. The canonical disappearance is consistent with insufficient optical "
                "transition impulse, not with an old/new RAM mapping swap."
            ),
            "why_busy_pass_does_not_refute": (
                "BUSY remained 599 ms on the controller timing plateau; it proves completion and the safety bound, "
                "not that the shortened voltage phases moved enough pigment to render black."
            ),
            "causality_limit": (
                "The owner verdict is not a time-resolved optical measurement, so insufficient transition impulse "
                "is a bounded inference rather than a proven per-phase causal attribution."
            ),
        },
        "supplier_original_boundary": {
            "source_topology_confirmed": source_full_lut_topology,
            "source_behavior": "the supplied LUT path writes a 5000-byte 0x24 full frame and activates 0xC7; it is not a supplied local old/new-bank no-flash profile",
            "not_safe_to_infer": [
                "copying the full supplier LUT into the R6 local 0x26/0x24/0xCF topology will be no-flash",
                "restoring stationary BB/WW drive only inside a local window will not affect the rest of the panel",
                "a new intermediate timing scale is supplier-authored or temperature-complete",
            ],
        },
        "disposition": {
            "r6_rerun_allowed": False,
            "motion_120_frame_allowed": False,
            "new_lut_or_hardware_candidate_admitted": False,
            "next_step": "root review is required before any new bounded contract; research alone does not authorize waveform tuning or flash",
        },
        "source_hashes": {str(path): sha(path) for path in EXPECTED_HASHES},
        "production_allowed": False,
        "goal_terminal": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
