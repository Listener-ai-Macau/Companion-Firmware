#!/usr/bin/env python3
"""Admit the single-variable R6 contiguous observation sequence without hardware."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R4 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r4-20260721.json"
R5_RUNTIME = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-runtime-20260721.json"
R5_OPERATOR = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-operator-20260721.json"
R5_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-dual-plane-clean-r5-disposition-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-workbench-20260721.json"
HASHES = {
    R4: "E7467B808CE7BD1BE317BC282B7990CF343922DE8C15B092588B9968DEAB444D",
    R5_RUNTIME: "949F9AC1DE90CD966AC915781A08B33EDA621ED47B8D88110DDCE7A12769F5EC",
    R5_OPERATOR: "868F7854441C628C48BD5534DD2214C02339F410E2DC8067734AFC12BCFC81BF",
    R5_DISPOSITION: "E061343CF42A39BE75552E528D0C2EEB8B0DBA9A8C54964E6924F64D02A0352B",
}
LUT_SHA = "75D7647188ACF1C79BC37313DC40105AF4445B9B6F422AD4FDAF0A465413984D"
R5_HEX_SHA = "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def payload(row: bytes) -> bytes:
    return row * 32


def main() -> int:
    errors: list[str] = []
    for path, expected in HASHES.items():
        if not path.is_file() or sha(path) != expected:
            errors.append(f"sealed input missing or drifted: {path}")
    if errors:
        print(json.dumps({"status": "NO_GO_WORKBENCH_R6", "errors": errors}))
        return 1

    r4 = json.loads(R4.read_text(encoding="utf-8"))
    runtime = json.loads(R5_RUNTIME.read_text(encoding="utf-8"))
    operator = json.loads(R5_OPERATOR.read_text(encoding="utf-8"))
    disposition = json.loads(R5_DISPOSITION.read_text(encoding="utf-8"))
    registry = REGISTRY.read_text(encoding="utf-8")
    if registry.count("| COMP-REQ-299 |") != 1:
        errors.append("COMP-REQ-299 missing or non-unique")
    if r4.get("candidate", {}).get("r4_lut_sha256") != LUT_SHA:
        errors.append("R4 TP16 LUT lineage differs")
    busy = runtime.get("candidate", {}).get("busy_elapsed_ms", [])
    if busy != [598, 599, 599, 599, 599, 599, 599, 599, 599]:
        errors.append(f"R5 BUSY observations differ: {busy}")
    if disposition.get("status") != "NO_GO_R5_MACHINE_PASS_OPERATOR_FAILED_NOT_OBSERVED_EXACT_RAW_RESTORED":
        errors.append("R5 missed-observation disposition differs")
    expected_note = "没看见, 下次你搞连续的变动, 然后有一次提醒就行我就会来看"
    if operator.get("note") != expected_note:
        errors.append("R5 exact owner note differs")

    previous = ["W", "A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A"]
    current = ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A", "W"]
    predicted = busy[0] + busy[-1] * 15 if busy else 0
    if predicted != 9583 or len(previous) != 16 or len(current) != 16:
        errors.append("R6 16-activation timing oracle differs")
    if previous[0] != "W" or current[-1] != "W" or any(current[i] != previous[i + 1] for i in range(15)):
        errors.append("R6 sequence is not a complete contiguous W-to-W chain")

    payloads = {
        "W": payload(bytes.fromhex("FFFFFFFF")),
        "A": payload(bytes.fromhex("0000FFFF")),
        "B": payload(bytes.fromhex("00FF00FF")),
    }
    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_observable_r6_workbench.v1",
        "status": "PASS_WORKBENCH_ADMIT_R6_EXACTLY_16_CONTIGUOUS_LOCAL_ACTIVATIONS" if not errors else "NO_GO_WORKBENCH_R6",
        "errors": errors,
        "hardware_contact": 0,
        "requirement": "COMP-REQ-299",
        "sealed_lineage": {
            "r5_hex_sha256": R5_HEX_SHA,
            "tp16_lut_sha256": LUT_SHA,
            "protected_tail_hex": "221741A83258",
            "dual_plane_clean_hex_sha256": runtime["dual_plane_preclean"]["hex_sha256"],
        },
        "single_variable": "increase the byte-identical local activation chain from 9 to exactly 16 while removing countdown, dwell and in-observation verbose UART",
        "sequence": {
            "previous": previous, "current": current, "activations": 16,
            "chain": [f"{old}->{new}" for old, new in zip(previous, current)],
            "window": {"x_bytes": [1, 4], "y": [8, 39], "pixels": [32, 32], "bytes_per_plane": 128},
            "payloads": {name: {"row_hex": data[:4].hex().upper(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest().upper()} for name, data in payloads.items()},
            "every_activation": {"old_bank": "0x26", "new_bank": "0x24", "old_bytes": 128, "new_bytes": 128, "control": "0xCF", "refresh": "0x20", "busy_max_ms": 600},
        },
        "timing": {
            "r5_measured_busy_ms": busy,
            "prediction_method": "one observed 598 ms activation plus fifteen conservative observed 599 ms activations",
            "predicted_busy_sum_ms": predicted,
            "bounded_expected_observation_ms": [9000, 11000],
            "countdown_seconds": 0, "inter_activation_dwell_ms": 0, "verbose_uart_during_observation": False,
        },
        "forbidden": {"extra_activations": True, "compensation": True, "full_frame": True, "controls_ff_f7_c7": True, "retry": True, "motion_120_frame": True},
        "human_boundary": "one canonical Chinese start popup only after dual-plane preclean passes; clicking starts the candidate immediately; later verdict is record-only",
        "admission": "machine-only; hardware candidate remains forbidden pending explicit root instruction after MACHINE_READY",
        "source_hashes": {str(path): sha(path) for path in HASHES},
        "production_allowed": False,
        "goal_terminal": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "predicted_ms": predicted, "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
