#!/usr/bin/env python3
"""Verify WB55 panel wiring preflight facts before real e-paper hardware work."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-wiring-preflight.json")
SCHEMA_ID = "companion.pendant.screen_panel_wiring_preflight.v1"

DEVBOARD_IOC = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG" / "Companion_Nucleo_WB55RG.ioc"
DEVBOARD_IOC_IMPORT = REPO_ROOT / "docs" / "validation" / "companion-devboard-ioc-import.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"
PANEL_RECOVERY_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-wb55-hardware-recovery-gate.json"
PANEL_ACCEPTANCE_PLAN = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-acceptance-plan.json"
BRINGUP_README = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "README.md"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
EPAPER_README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
PHYSICAL_CHECKLIST = REPO_ROOT / "docs" / "companion_devboard_physical_checklist.md"

SPI2_EXPECTED = {
    "instance": "SPI2",
    "sck_pin": "PA9",
    "sck_signal": "SPI2_SCK",
    "mosi_pin": "PC1",
    "mosi_signal": "SPI2_MOSI",
    "miso_pin": "PC2",
    "miso_signal": "SPI2_MISO",
    "cs_pin": "PA6",
    "cs_signal": "GPIO_Output",
    "cs_label": "EPAPER_CS",
    "mode": "SPI_MODE_MASTER",
    "direction": "SPI_DIRECTION_2LINES",
    "baudrate": "16.0 MBits/s",
}

PANEL_CONTROL_EXPECTED = {
    "cs": {"fts02": "P9 T7", "connector": "CN10-13", "pin": "PA6", "signal": "GPIO_Output", "label": "EPAPER_CS"},
    "dc": {"fts02": "P9 T6", "connector": "CN10-22", "pin": "PB0", "signal": "GPIO_Output", "label": "EPAPER_DC"},
    "reset": {"fts02": "P9 T5", "connector": "CN10-24", "pin": "PB1", "signal": "GPIO_Output", "label": "EPAPER_RESET"},
    "busy": {"fts02": "P9 T4", "connector": "CN7-3", "pin": "PC5", "signal": "GPIO_Input", "label": "EPAPER_BUSY"},
}

TOUCH_EXPECTED = {
    "scl": {"fts02": "P10 A4", "connector": "CN7-28", "pin": "PC0", "signal": "I2C3_SCL"},
    "sda": {"fts02": "P10 A5", "connector": "CN7-1", "pin": "PB11", "signal": "I2C3_SDA"},
    "interrupt": {"fts02": "P10 A0", "connector": "CN10-33", "pin": "PC6", "signal": "GPXTI6", "label": "TOUCH_INT"},
    "optional_reset": {"fts02": "P10 A3", "connector": "CN10-29", "pin": "PC10", "connected": False},
}

CURRENT_BENCH_POWER = {
    "logic_3v3": {"fts02": "P8 3.3V", "connector": "CN7-12", "rail": "3V3 / IOREF"},
    "ground": {"fts02": "P8 GND", "connector": "CN7-19", "rail": "GND"},
}

VERIFIED_GATE_FACTS = {
    "controller_model",
    "dc_pin",
    "rst_pin",
    "busy_pin",
}


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read_text(path, errors)
    if not text:
        return {}
    return json.loads(text)


def parse_ioc(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key] = value
    return values


def gate_fact_status(gate: dict[str, Any], fact_id: str) -> str:
    for fact in gate.get("required_hardware_facts", []):
        if isinstance(fact, dict) and fact.get("id") == fact_id:
            return str(fact.get("status", ""))
    return ""


def build_fixture() -> dict[str, Any]:
    values = parse_ioc(DEVBOARD_IOC)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "WB55 panel wiring preflight that records imported SPI2 transport pins, historical control facts, and the current FTS02 recovery blocker.",
        "sources": {
            "devboard_ioc": rel(DEVBOARD_IOC),
            "devboard_ioc_import": rel(DEVBOARD_IOC_IMPORT),
            "panel_hardware_gate": rel(PANEL_GATE),
            "panel_hardware_recovery_gate": rel(PANEL_RECOVERY_GATE),
            "panel_hardware_acceptance_plan": rel(PANEL_ACCEPTANCE_PLAN),
            "bringup_readme": rel(BRINGUP_README),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(EPAPER_README),
            "physical_checklist": rel(PHYSICAL_CHECKLIST),
            "verifier": "tools/verify_expression_panel_wiring_preflight.py",
        },
        "wb55_devboard_transport": {
            "spi_instance": SPI2_EXPECTED["instance"],
            "sck": {
                "pin": SPI2_EXPECTED["sck_pin"],
                "signal": values.get(f"{SPI2_EXPECTED['sck_pin']}.Signal"),
                "mode": values.get(f"{SPI2_EXPECTED['sck_pin']}.Mode"),
            },
            "mosi": {
                "pin": SPI2_EXPECTED["mosi_pin"],
                "signal": values.get(f"{SPI2_EXPECTED['mosi_pin']}.Signal"),
                "mode": values.get(f"{SPI2_EXPECTED['mosi_pin']}.Mode"),
            },
            "miso": {
                "pin": SPI2_EXPECTED["miso_pin"],
                "signal": values.get(f"{SPI2_EXPECTED['miso_pin']}.Signal"),
                "mode": values.get(f"{SPI2_EXPECTED['miso_pin']}.Mode"),
            },
            "chip_select_candidate": {
                "pin": SPI2_EXPECTED["cs_pin"],
                "signal": values.get(f"{SPI2_EXPECTED['cs_pin']}.Signal"),
                "label": values.get(f"{SPI2_EXPECTED['cs_pin']}.GPIO_Label"),
            },
            "mode": values.get("SPI2.Mode"),
            "direction": values.get("SPI2.Direction"),
            "baudrate": values.get("SPI2.CalculateBaudRate"),
        },
        "wb55_devboard_controls": PANEL_CONTROL_EXPECTED,
        "wb55_devboard_touch": TOUCH_EXPECTED,
        "wb55_current_bench_power": CURRENT_BENCH_POWER,
        "historical_verified_panel_facts": [
            "e-paper controller model",
            "DC pin",
            "RST pin",
            "BUSY pin",
            "reset timing",
            "full refresh sequence",
            "partial refresh policy",
            "visual before/during/after evidence",
        ],
        "hardware_gate": {
            "gate_id": "wb55_real_panel_refresh",
            "current_status": "DEFERRED_HARDWARE_FTS02_BOOST",
            "current_real_refresh_claimed": False,
            "historical_evidence_status": "PASS",
            "historical_real_refresh_claimed": True,
            "control_facts_expected_verified": sorted(VERIFIED_GATE_FACTS),
        },
        "wba_impact": "WBA55/WBA65 must create their own CubeWBA IOC/project and *_stm32wba.* panel adapter; WB55 SPI2 pins are devboard facts, not portable screen constants.",
        "acceptance": {
            "spi2_transport_pins_preserved_from_ioc": True,
            "chip_select_candidate_named_in_ioc": True,
            "controller_and_control_pins_are_owned_by_hardware_gate": True,
            "current_real_refresh_deferred_to_recovery_gate": True,
            "historical_refresh_evidence_remains_traceable": True,
            "wba_must_not_copy_wb55_pin_facts_into_portable_code": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_wiring_preflight.py",
            "python .\\tools\\verify_devboard_ioc_import.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_ioc(errors: list[str]) -> None:
    values = parse_ioc(DEVBOARD_IOC)
    require(values.get("Mcu.CPN") == "STM32WB55RGV6", "devboard IOC must stay on STM32WB55RGV6", errors)
    require(values.get("SPI2.Mode") == SPI2_EXPECTED["mode"], "devboard IOC SPI2 mode drifted", errors)
    require(values.get("SPI2.Direction") == SPI2_EXPECTED["direction"], "devboard IOC SPI2 direction drifted", errors)
    require(values.get("SPI2.CalculateBaudRate") == SPI2_EXPECTED["baudrate"], "devboard IOC SPI2 baudrate drifted", errors)
    for key in ["sck", "mosi", "miso"]:
        pin = SPI2_EXPECTED[f"{key}_pin"]
        signal = SPI2_EXPECTED[f"{key}_signal"]
        require(values.get(f"{pin}.Signal") == signal, f"devboard IOC {pin} expected {signal}", errors)
        require(values.get(f"{pin}.Mode") == "Full_Duplex_Master", f"devboard IOC {pin} must stay SPI2 full-duplex master", errors)
    cs_pin = SPI2_EXPECTED["cs_pin"]
    require(values.get(f"{cs_pin}.Signal") == SPI2_EXPECTED["cs_signal"], "devboard IOC PA6 must stay GPIO output for SPI2 CS", errors)
    require(values.get(f"{cs_pin}.GPIO_Label") == SPI2_EXPECTED["cs_label"], "devboard IOC PA6 must keep EPAPER_CS label", errors)
    for role, expected in PANEL_CONTROL_EXPECTED.items():
        pin = expected["pin"]
        require(values.get(f"{pin}.Signal") == expected["signal"], f"devboard IOC {role} pin {pin} signal drifted", errors)
        require(values.get(f"{pin}.GPIO_Label") == expected["label"], f"devboard IOC {role} pin {pin} label drifted", errors)
    for role in ["scl", "sda", "interrupt"]:
        expected = TOUCH_EXPECTED[role]
        pin = expected["pin"]
        require(values.get(f"{pin}.Signal") == expected["signal"], f"devboard IOC touch {role} pin {pin} drifted", errors)
        if "label" in expected:
            require(values.get(f"{pin}.GPIO_Label") == expected["label"], f"devboard IOC touch {role} label drifted", errors)
    require("PC10.Signal" not in values, "optional touch reset PC10 must remain unconnected in current IOC", errors)


def check_devboard_import(errors: list[str]) -> None:
    data = read_json(DEVBOARD_IOC_IMPORT, errors)
    require(data.get("schema_id") == "companion.devboard_ioc_import.v1", "unexpected devboard IOC import schema", errors)
    acceptance = data.get("acceptance", {})
    require(acceptance.get("external_hardware_keys_preserved") is True, "devboard IOC import must preserve external hardware keys", errors)
    require(acceptance.get("product_ioc_kept_separate") is True, "devboard IOC import must keep product IOC separate", errors)
    pins = data.get("devboard_ioc", {}).get("hardware_summary", {}).get("pins", {})
    require(pins.get("PA9.Signal") == "SPI2_SCK", "devboard IOC import fixture missing SPI2 SCK", errors)
    require(pins.get("PC1.Signal") == "SPI2_MOSI", "devboard IOC import fixture missing SPI2 MOSI", errors)
    require(pins.get("PC2.Signal") == "SPI2_MISO", "devboard IOC import fixture missing SPI2 MISO", errors)
    require(pins.get("PA6.Signal") == "GPIO_Output", "devboard IOC import fixture missing PA6 GPIO CS candidate", errors)
    overrides = data.get("devboard_ioc", {}).get("hardware_summary", {}).get("allowed_repo_overrides", {})
    for key, expected in {
        "PA6.GPIO_Label": "EPAPER_CS",
        "PB0.GPIO_Label": "EPAPER_DC",
        "PB1.GPIO_Label": "EPAPER_RESET",
    }.items():
        require(overrides.get(key, {}).get("repo") == expected, f"devboard IOC import fixture missing {expected} override", errors)


def check_panel_gate(errors: list[str]) -> None:
    gate = read_json(PANEL_GATE, errors)
    require(gate.get("gate_id") == "wb55_real_panel_refresh", "panel gate id drifted", errors)
    require(gate.get("status") == "PASS", "historical panel evidence integrity must remain PASS", errors)
    require(gate.get("evidence_scope") == "historical_refresh_evidence_integrity", "panel gate must identify historical scope", errors)
    require(gate.get("historical_real_refresh_claimed") is True, "historical panel evidence must retain its original claim", errors)
    require(gate.get("current_real_refresh_claimed") is False, "historical panel evidence must not claim current acceptance", errors)
    for fact_id in VERIFIED_GATE_FACTS:
        require(gate_fact_status(gate, fact_id) == "verified", f"panel gate fact {fact_id} must remain verified", errors)
    serialized = json.dumps(gate, sort_keys=True)
    require("companion-screen-panel-wiring-preflight.json" in serialized, "panel gate must link panel wiring preflight", errors)
    require("verify_expression_panel_wiring_preflight.py" in serialized, "panel gate must run panel wiring preflight verifier", errors)
    recovery = read_json(PANEL_RECOVERY_GATE, errors)
    require(recovery.get("status") == "DEFERRED_HARDWARE_FTS02_BOOST", "current panel recovery must remain deferred", errors)
    require(recovery.get("claim_scope") == "current_hardware_recovery_gate_no_panel_acceptance", "current panel recovery must not claim acceptance", errors)


def check_acceptance_plan(errors: list[str]) -> None:
    plan = read_json(PANEL_ACCEPTANCE_PLAN, errors)
    serialized = json.dumps(plan, sort_keys=True)
    require("companion-screen-panel-wiring-preflight.json" in serialized, "panel hardware acceptance plan must link wiring preflight", errors)
    require("verify_expression_panel_wiring_preflight.py" in serialized, "panel hardware acceptance plan must run wiring preflight", errors)
    require("target SPI/DC/RST/BUSY/power pins recorded" in serialized, "panel hardware plan must still require full target pin evidence", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read_text(SCREEN_DOC, errors).split()).lower()
    wba_rules = " ".join(read_text(WBA_RULES, errors).split()).lower()
    readme = " ".join(read_text(EPAPER_README, errors).split()).lower()
    bringup_readme = " ".join(read_text(BRINGUP_README, errors).split()).lower()
    physical_checklist = " ".join(read_text(PHYSICAL_CHECKLIST, errors).split()).lower()
    for token in [
        "panel wiring preflight",
        "companion-screen-panel-wiring-preflight.json",
        "verify_expression_panel_wiring_preflight.py",
        "spi2",
        "pa9 / pc1 / pc2 / pa6",
        "dc/rst/busy",
    ]:
        require(token in screen_doc, f"screen doc missing panel wiring preflight anchor {token}", errors)
    for token in [
        "panel wiring preflight",
        "verify_expression_panel_wiring_preflight.py",
        "wb55 spi2 pins are devboard facts",
        "cubewba ioc/project",
    ]:
        require(token in wba_rules, f"WBA rules missing panel wiring preflight anchor {token}", errors)
    for token in [
        "panel wiring preflight",
        "verify_expression_panel_wiring_preflight.py",
    ]:
        require(token in readme, f"e-paper README missing panel wiring preflight anchor {token}", errors)
    for token in [
        "spi2 sck/mosi/miso/cs",
        "pa9 / pc1 / pc2 / pa6",
        "verify_devboard_ioc_import.py",
    ]:
        require(token in bringup_readme, f"bringup README missing panel wiring source anchor {token}", errors)
    for token in [
        "`p8 3.3v` | `cn7-12` | `3v3 / ioref`",
        "`p9 t4` | `cn7-3` | `pc5`",
        "`p10 a0` | `cn10-33` | `pc6`",
        "`p10 a3`（可选，不接） | `cn10-29` | `pc10`",
    ]:
        require(token in physical_checklist, f"physical checklist missing current wiring anchor {token}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel wiring preflight schema", errors)
    require(data.get("status") == "PASS", "panel wiring preflight fixture must be PASS", errors)
    transport = data.get("wb55_devboard_transport", {})
    require(transport.get("spi_instance") == "SPI2", "wiring preflight fixture must use SPI2", errors)
    require(transport.get("sck", {}).get("pin") == "PA9", "wiring preflight fixture SCK pin drifted", errors)
    require(transport.get("mosi", {}).get("pin") == "PC1", "wiring preflight fixture MOSI pin drifted", errors)
    require(transport.get("miso", {}).get("pin") == "PC2", "wiring preflight fixture MISO pin drifted", errors)
    require(transport.get("chip_select_candidate", {}).get("pin") == "PA6", "wiring preflight fixture CS pin drifted", errors)
    require(transport.get("chip_select_candidate", {}).get("label") == "EPAPER_CS", "wiring preflight fixture CS label drifted", errors)
    require(data.get("wb55_devboard_controls") == PANEL_CONTROL_EXPECTED, "wiring preflight control map drifted", errors)
    require(data.get("wb55_devboard_touch") == TOUCH_EXPECTED, "wiring preflight touch map drifted", errors)
    require(data.get("wb55_current_bench_power") == CURRENT_BENCH_POWER, "wiring preflight current bench power map drifted", errors)
    gate = data.get("hardware_gate", {})
    require(gate.get("current_status") == "DEFERRED_HARDWARE_FTS02_BOOST", "wiring preflight fixture must show the current FTS02 blocker", errors)
    require(gate.get("current_real_refresh_claimed") is False, "wiring preflight fixture must not claim current refresh", errors)
    require(gate.get("historical_evidence_status") == "PASS", "wiring preflight fixture must retain historical evidence", errors)
    require(gate.get("historical_real_refresh_claimed") is True, "wiring preflight fixture must preserve historical refresh evidence", errors)
    require(set(gate.get("control_facts_expected_verified", [])) == VERIFIED_GATE_FACTS, "wiring preflight fixture missing verified control fact guard", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "spi2_transport_pins_preserved_from_ioc",
        "chip_select_candidate_named_in_ioc",
        "controller_and_control_pins_are_owned_by_hardware_gate",
        "current_real_refresh_deferred_to_recovery_gate",
        "historical_refresh_evidence_remains_traceable",
        "wba_must_not_copy_wb55_pin_facts_into_portable_code",
    ]:
        require(acceptance.get(token) is True, f"wiring preflight acceptance missing {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel wiring preflight fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update deterministic panel wiring preflight JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_ioc(errors)
    check_devboard_import(errors)
    if not args.write_fixture:
        check_panel_gate(errors)
        check_acceptance_plan(errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion panel wiring preflight checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion panel wiring preflight verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
