#!/usr/bin/env python3
"""Verify retained historical WB55 panel evidence and the current recovery gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = Path("docs/validation/companion-screen-panel-hardware-gate.json")
BRINGUP = ROOT / "docs/validation/companion-screen-wb55-ssd1681-bringup.json"
REFRESH = ROOT / "docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json"
TOUCH = ROOT / "docs/validation/companion-screen-touch-ft6336-wb55.json"
WIRING_PREFLIGHT = ROOT / "docs/validation/companion-screen-panel-wiring-preflight.json"
REAL_BLE_BENCH = ROOT / "docs/validation/companion-screen-real-ble-bench.json"
EVIDENCE_RECORD_VALIDATOR = ROOT / "docs/validation/companion-screen-panel-evidence-record-validator.json"
EVIDENCE_TEMPLATE = ROOT / "docs/validation/companion-screen-panel-evidence-template.json"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
CURRENT_RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
GATE_ID = "wb55_real_panel_refresh"
SCHEMA_ID = "companion.pendant.screen_panel_hardware_gate.v1"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def evidence_path(value: Any) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def build_gate() -> dict[str, Any]:
    bringup = load(BRINGUP)
    refresh = load(REFRESH)
    target = bringup["target"]
    transport = bringup["transport"]
    display = bringup["display_evidence"]
    touch = bringup["touch_evidence"]
    fast = refresh["fast_maintenance_runtime"]
    production = refresh["production_runtime"]
    recovery = load(CURRENT_RECOVERY_GATE)

    fact = lambda fact_id, label, value, paths: {
        "id": fact_id,
        "label": label,
        "status": "verified",
        "value": value,
        "evidence_paths": paths,
    }
    bringup_path = rel(BRINGUP)
    refresh_path = rel(REFRESH)
    return {
        "schema_id": SCHEMA_ID,
        "gate_id": GATE_ID,
        "status": "PASS",
        "evidence_scope": "historical_refresh_evidence_integrity",
        "current_acceptance_status": recovery.get("status"),
        "current_real_refresh_claimed": False,
        "superseded_for_current_acceptance_by": rel(CURRENT_RECOVERY_GATE),
        "hardware_action_required": False,
        "historical_real_refresh_claimed": True,
        "real_refresh_claim_is_historical": True,
        "result": (
            "WB55 drove the physical GDEY0154D67-T03 through SSD1681 full, "
            "partial, and fast refresh paths; the operator confirmed a visible "
            "black update and upright non-mirrored orientation."
        ),
        "target_backend": {
            "initializer": "companion_epaper_panel_stm32wb_init",
            "dispatcher": "app/companion_pendant/epaper/panel_target_stm32wb.c",
            "driver": "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
            "controller": "SSD1681",
            "dry_run_role": "fallback_only",
        },
        "required_hardware_facts": [
            fact("controller_model", "e-paper controller model", target["controller"], [bringup_path]),
            fact("panel_model", "panel module", target["panel"], [bringup_path]),
            fact("logic_voltage", "measured target voltage", f"{target['measured_target_voltage_v']:.2f} V", [bringup_path]),
            fact("dc_pin", "DC pin", transport["dc"], [bringup_path]),
            fact("rst_pin", "RST pin", transport["rst"], [bringup_path]),
            fact("busy_pin", "BUSY pin", transport["busy"], [bringup_path]),
            fact("full_refresh", "full refresh sequence", "0x24 + 0x26 + 0xF7", [refresh_path]),
            fact("partial_refresh", "partial refresh sequence", "0x24 + 0xFF", [refresh_path]),
            fact("fast_maintenance", "verified Mode-1 single-flash sequence", "vendor fast init + 0xC7 + 0x26 baseline sync", [refresh_path]),
            fact("legacy_maintenance", "retired historical maintenance sequence", "0xCF maintenance + 0x26 baseline sync", [refresh_path]),
            fact("operator_visual", "operator visual evidence", display["black_pattern_operator_observation"], [bringup_path]),
            fact("orientation", "operator orientation evidence", display["human_view_orientation"], [bringup_path]),
            fact("touch_contact", "physical touch contact/release", touch["result"], [bringup_path, rel(TOUCH)]),
        ],
        "runtime": {
            "full_refresh_elapsed_ms": transport["full_refresh_elapsed_ms"],
            "partial_refresh_elapsed_ms": production["observed_partial_refresh_ms"],
            "fast_refresh_elapsed_ms": fast["elapsed_ms"],
            "refresh_failures": production["refresh_failures"],
            "historical_production_interactive_hard_limit": production["interactive_hard_limit"],
            "post_fast_partial_refresh": fast["post_fast_partial_refresh"],
        },
        "remaining_human_acceptance": [
            "Confirm current vendor Mode-1 0xC7 maintenance is perceived as one quiet flash",
            "Confirm daily tap and four-way swipes stay as pet reactions",
            "Confirm anywhere 3 s hold enters the menu after the 650 ms pet tease",
            "Confirm continuous vertical drag, press-cue plus target-arrival partial refreshes, language switching, and anywhere-right-swipe return",
        ],
        "evidence_paths": [
            bringup_path,
            refresh_path,
            rel(TOUCH),
            rel(WIRING_PREFLIGHT),
            rel(REAL_BLE_BENCH),
            rel(EVIDENCE_TEMPLATE),
            rel(EVIDENCE_RECORD_VALIDATOR),
            rel(DRIVER),
            rel(CURRENT_RECOVERY_GATE),
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_wb55_screen_hardware_recovery_gate.py",
            "python .\\tools\\verify_screen_menu_assets.py",
            "python .\\tools\\verify_epaper_refresh_policy.py",
            "python .\\tools\\verify_epaper_fast_maintenance_runtime.py",
            "python .\\tools\\verify_touch_ft6336.py",
            "python .\\tools\\verify_expression_panel_wiring_preflight.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_panel_evidence_template.py",
            "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
            "python .\\tools\\verify_expression_panel_target_stm32wb.py",
        ],
        "wba_impact": (
            "WBA55/WBA65 reuse the portable framebuffer, display queue, refresh "
            "policy, asset store, and presentation state; only target panel, "
            "touch, storage, and timer backends may change."
        ),
    }


def validate(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected gate schema", errors)
    require(data.get("gate_id") == GATE_ID, "unexpected gate id", errors)
    require(data.get("status") == "PASS", "real-panel refresh gate is not PASS", errors)
    require(
        data.get("evidence_scope") == "historical_refresh_evidence_integrity",
        "panel gate must identify its historical evidence scope",
        errors,
    )
    require(
        data.get("current_acceptance_status") == "DEFERRED_HARDWARE_FTS02_BOOST",
        "panel gate must link the current FTS02-deferred status",
        errors,
    )
    require(
        data.get("current_real_refresh_claimed") is False,
        "historical panel gate must not claim current refresh acceptance",
        errors,
    )
    require(
        data.get("real_refresh_claim_is_historical") is True,
        "historical refresh claim must be explicit",
        errors,
    )
    require(data.get("historical_real_refresh_claimed") is True, "historical real refresh evidence is not retained", errors)
    require(data.get("hardware_action_required") is False, "gate still asks for hardware facts", errors)

    facts = data.get("required_hardware_facts", [])
    require(isinstance(facts, list) and len(facts) >= 13, "verified hardware facts are incomplete", errors)
    for fact in facts if isinstance(facts, list) else []:
        require(isinstance(fact, dict), "hardware fact must be an object", errors)
        if not isinstance(fact, dict):
            continue
        require(fact.get("status") == "verified", f"fact {fact.get('id')} is not verified", errors)
        require(fact.get("value") not in {None, ""}, f"fact {fact.get('id')} has no value", errors)
        require(bool(fact.get("evidence_paths")), f"fact {fact.get('id')} has no evidence", errors)

    for value in data.get("evidence_paths", []):
        require(evidence_path(value).exists(), f"missing evidence path: {value}", errors)

    pending = "\n".join(str(item) for item in data.get("remaining_human_acceptance", []))
    for token in [
        "vendor Mode-1 0xC7 maintenance",
        "daily tap and four-way swipes",
        "anywhere 3 s hold",
        "650 ms pet tease",
        "press-cue plus target-arrival partial refreshes",
        "language switching",
    ]:
        require(token in pending, f"remaining human acceptance missing current interaction token: {token}", errors)
    for stale in [
        "swipe-left menu entry",
        "direct visible-row entry with one refresh",
        "revision 39 0xCF maintenance",
        "left-edge swipe-right return",
    ]:
        require(stale not in pending, f"remaining human acceptance contains stale rule: {stale}", errors)

    bringup = load(BRINGUP)
    require(str(bringup.get("status", "")).startswith("PASS"), "bring-up status is not PASS", errors)
    require(bringup.get("target", {}).get("controller") == "SSD1681", "controller evidence drifted", errors)
    require(bringup.get("display_evidence", {}).get("black_pattern_operator_observation", "").startswith("PASS"), "operator black-screen observation missing", errors)
    require(bringup.get("display_evidence", {}).get("human_view_orientation", "").startswith("PASS"), "operator orientation observation missing", errors)
    require(bringup.get("touch_evidence", {}).get("result") == "PASS", "physical touch contact evidence missing", errors)

    refresh = load(REFRESH)
    fast = refresh.get("fast_maintenance_runtime", {})
    production = refresh.get("production_runtime", {})
    require(refresh.get("status") == "PASS", "refresh evidence is not PASS", errors)
    require(refresh.get("fast_maintenance_runtime", {}).get("machine_result") == "PASS", "fast maintenance evidence is not PASS", errors)
    require(refresh.get("fast_maintenance_runtime", {}).get("control") == "0xC7", "fast control drifted", errors)
    require(refresh.get("production_runtime", {}).get("interactive_hard_limit") == 60, "historical production hard limit drifted", errors)
    require(refresh.get("production_runtime", {}).get("flash_verified") is True, "production firmware flash is not verified", errors)

    recovery = load(CURRENT_RECOVERY_GATE)
    require(
        recovery.get("status") == "DEFERRED_HARDWARE_FTS02_BOOST",
        "current recovery gate must remain FTS02-deferred",
        errors,
    )
    require(
        recovery.get("acceptance_criteria", {}).get("normal_current_expression_visible") is False,
        "current normal expression must remain unaccepted",
        errors,
    )

    driver = DRIVER.read_text(encoding="utf-8")
    for marker in [
        "0xF7u",
        "0xFCu",
        "0xC7u",
        "SSD1681_VENDOR_FAST_PROFILE_NAME",
        "ssd1681_prepare_vendor_fast_profile",
        "ssd1681_write_plane_region(0x26u, s_frame, &window)",
        "ssd1681_write_plane_region(0x24u, s_frame, &window)",
    ]:
        require(marker in driver, f"driver missing {marker}", errors)

    require(production.get("interactive_soft_limit") == 5, "historical soft limit drifted", errors)
    require(production.get("interactive_hard_limit") == 60, "historical hard limit drifted", errors)
    require(production.get("observed_partial_refresh_count") == 4, "historical partial count drifted", errors)
    require(fast.get("decision") == "fast", "historical fast decision drifted", errors)
    require(fast.get("reason") == "interactive_hard_limit", "historical fast reason drifted", errors)
    require(fast.get("complete") is True, "historical fast completion drifted", errors)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-template", action="store_true")
    args = parser.parse_args(argv)
    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    expected = build_gate()
    errors: list[str] = []
    validate(expected, errors)
    if args.write_template and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.write_template:
        require(fixture.exists(), f"missing fixture: {rel(fixture)}", errors)
        if fixture.exists():
            require(load(fixture) == expected, f"{rel(fixture)} is stale; rerun with --write-template", errors)
    if errors:
        print("FAIL: WB55 real-panel refresh gate", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: historical WB55 panel evidence verified; current recovery remains deferred -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
