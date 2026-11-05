#!/usr/bin/env python3
"""Verify the WBA LSE/low-power clock contract stays explicit before porting."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wba-lse-clock-contract.json"
WBA_RULES = ROOT / "docs/stm32wba_migration_rules.md"
WBA_PORT = ROOT / "docs/validation/companion-screen-wba-port-contract.json"
WBA_REAL_PARITY = ROOT / "docs/validation/companion-screen-wba-real-parity-gate.json"
SCHEMA_ID = "companion.pendant.screen_wba_lse_clock_contract.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_contract() -> dict[str, Any]:
    wba_rules = WBA_RULES.read_text(encoding="utf-8")
    port = load_json(WBA_PORT)
    parity = load_json(WBA_REAL_PARITY)
    rule_tokens = [
        "Default the WBA55/WBA65 production board to an assembled 32.768 kHz LSE",
        "BLE sleep timing",
        "RTC",
        "timed wake-up",
        "omitting LSE",
        "cost-down variant",
        "radio-clock",
        "accuracy",
        "power evidence",
        "OSC32_IN",
        "OSC32_OUT",
        "AN2867/AN5948",
        "enable LSE",
        "prove startup",
        "RTC continuity",
        "advertising/connection through sleep",
        "timed wake-up on real hardware",
    ]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_PRE_PORT_CLOCK_CONTRACT_RECORDED",
        "claim_scope": "wba_clock_design_contract_no_hardware_claim",
        "target_family": "STM32WBA",
        "targets": ["WBA55", "WBA65"],
        "source_rules": {
            "wba_rules": rel(WBA_RULES),
            "wba_port_contract": rel(WBA_PORT),
            "wba_real_parity_gate": rel(WBA_REAL_PARITY),
        },
        "default_design": {
            "lse_crystal": "assemble 32.768 kHz LSE crystal and target-specific load capacitors by default",
            "placement": "place crystal/capacitors next to OSC32_IN/OSC32_OUT with short symmetric traces",
            "selection_rule": "select crystal and capacitors from the chosen WBA package datasheet and AN2867/AN5948",
            "do_not_copy_from_wb55": True,
        },
        "why_required": [
            "BLE sleep timing",
            "RTC continuity",
            "timed wake-up",
            "low-power Companion behavior",
        ],
        "no_lse_exception_requires": [
            "explicit product cost-down decision",
            "radio-clock source selection evidence",
            "BLE advertising and connection accuracy evidence through sleep",
            "RTC or replacement timebase accuracy evidence",
            "timed wake-up evidence",
            "power budget evidence",
        ],
        "future_wba_evidence": [
            "CubeWBA target enables LSE",
            "LSE startup is logged on real WBA hardware",
            "RTC continuity is proven across sleep",
            "BLE advertising/connection survives sleep",
            "timed wake-up is proven on real hardware",
            "no-LSE variant, if chosen, records radio-clock, accuracy, and power evidence",
        ],
        "current_state": {
            "cube_wba_present": parity.get("current_state", {}).get("stm32cubewba_present"),
            "wba_port_status": port.get("status"),
            "wba_parity_claim_allowed": parity.get("parity_claim_allowed"),
            "hardware_claimed": False,
        },
        "rule_tokens": {token: token in wba_rules for token in rule_tokens},
        "validation_commands": [
            "python .\\tools\\verify_expression_wba_lse_clock_contract.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\verify_expression_wba_real_parity_gate.py",
        ],
    }


def check_contract(contract: dict[str, Any], errors: list[str]) -> None:
    if contract.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if contract.get("status") != "PASS_PRE_PORT_CLOCK_CONTRACT_RECORDED":
        errors.append("unexpected status")
    if contract.get("claim_scope") != "wba_clock_design_contract_no_hardware_claim":
        errors.append("contract must not claim WBA clock hardware")
    if contract.get("target_family") != "STM32WBA":
        errors.append("target family must be STM32WBA")
    for target in ("WBA55", "WBA65"):
        if target not in contract.get("targets", []):
            errors.append(f"missing target {target}")
    if contract.get("default_design", {}).get("do_not_copy_from_wb55") is not True:
        errors.append("contract must forbid copying WB55 LSE values into WBA")
    for token, present in contract.get("rule_tokens", {}).items():
        if present is not True:
            errors.append(f"WBA rules missing LSE token: {token}")
    for token in (
        "BLE sleep timing",
        "RTC continuity",
        "timed wake-up",
        "low-power Companion behavior",
    ):
        if token not in contract.get("why_required", []):
            errors.append(f"missing why_required token {token}")
    for token in (
        "radio-clock source selection evidence",
        "BLE advertising and connection accuracy evidence through sleep",
        "power budget evidence",
    ):
        if token not in contract.get("no_lse_exception_requires", []):
            errors.append(f"missing no-LSE exception token {token}")
    for token in (
        "CubeWBA target enables LSE",
        "LSE startup is logged on real WBA hardware",
        "RTC continuity is proven across sleep",
        "BLE advertising/connection survives sleep",
        "timed wake-up is proven on real hardware",
    ):
        if token not in contract.get("future_wba_evidence", []):
            errors.append(f"missing future WBA evidence token {token}")
    state = contract.get("current_state", {})
    if state.get("cube_wba_present") is not False:
        errors.append("current pre-port state should record CubeWBA as not present")
    if state.get("wba_port_status") != "PASS":
        errors.append("WBA port contract should remain PASS")
    if state.get("wba_parity_claim_allowed") is not False:
        errors.append("WBA parity must remain blocked")
    if state.get("hardware_claimed") is not False:
        errors.append("LSE contract must not claim hardware")
    serialized = json.dumps(contract, ensure_ascii=False)
    for token in (
        "32.768 kHz",
        "OSC32_IN/OSC32_OUT",
        "AN2867/AN5948",
        "no-LSE variant",
        "wba_clock_design_contract_no_hardware_claim",
    ):
        if token not in serialized:
            errors.append(f"contract missing token {token}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)

    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    contract = build_contract()
    errors: list[str] = []
    check_contract(contract, errors)
    rendered = json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.write and not errors:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        elif json_path.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(json_path)}; rerun with --write")

    if errors:
        print("FAIL: WBA LSE clock contract checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WBA LSE clock contract verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
