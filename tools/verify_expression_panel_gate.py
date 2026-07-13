#!/usr/bin/env python3
"""Verify the completed WB55 real-panel refresh gate and its evidence."""

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
        "hardware_action_required": False,
        "real_refresh_claimed": True,
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
            fact("full_refresh", "full refresh sequence", "0x24 + 0x26 + 0xF7", [refresh_path, production["log"]]),
            fact("partial_refresh", "partial refresh sequence", "0x24 + 0xFF", [refresh_path, production["log"]]),
            fact("fast_maintenance", "historical single-flash fast sequence", "vendor fast init + 0xC7 + 0x26 baseline sync", [refresh_path, fast["log"]]),
            fact("current_maintenance", "current low-flicker maintenance sequence", "0xCF maintenance + 0x26 baseline sync", [refresh_path]),
            fact("operator_visual", "operator visual evidence", display["black_pattern_operator_observation"], [bringup_path]),
            fact("orientation", "operator orientation evidence", display["human_view_orientation"], [bringup_path, display["orientation_log"]]),
            fact("touch_contact", "physical touch contact/release", touch["result"], [bringup_path, touch["log"]]),
        ],
        "runtime": {
            "full_refresh_elapsed_ms": transport["full_refresh_elapsed_ms"],
            "partial_refresh_elapsed_ms": production["observed_partial_refresh_ms"],
            "fast_refresh_elapsed_ms": fast["elapsed_ms"],
            "refresh_failures": production["refresh_failures"],
            "production_interactive_hard_limit": production["interactive_hard_limit"],
            "post_fast_partial_refresh": fast["post_fast_partial_refresh"],
        },
        "remaining_human_acceptance": [
            "Confirm current revision 39 0xCF maintenance is perceived as one quiet flash",
            "Confirm daily tap and four-way swipes stay as pet reactions",
            "Confirm anywhere 3 s hold enters the menu after the 650 ms pet tease",
            "Confirm continuous vertical drag, press-cue plus target-arrival partial refreshes, language switching, and left-edge swipe-right return",
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
            production["log"],
            fast["log"],
            display["orientation_log"],
            touch["log"],
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_gate.py",
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
    require(data.get("real_refresh_claimed") is True, "real refresh is not claimed", errors)
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
        "revision 39 0xCF maintenance",
        "daily tap and four-way swipes",
        "anywhere 3 s hold",
        "650 ms pet tease",
        "press-cue plus target-arrival partial refreshes",
        "language switching",
    ]:
        require(token in pending, f"remaining human acceptance missing current revision 39 token: {token}", errors)
    for stale in [
        "swipe-left menu entry",
        "direct visible-row entry with one refresh",
        "0xC7 maintenance",
    ]:
        require(stale not in pending, f"remaining human acceptance contains stale rule: {stale}", errors)

    bringup = load(BRINGUP)
    require(str(bringup.get("status", "")).startswith("PASS"), "bring-up status is not PASS", errors)
    require(bringup.get("target", {}).get("controller") == "SSD1681", "controller evidence drifted", errors)
    require(bringup.get("display_evidence", {}).get("black_pattern_operator_observation", "").startswith("PASS"), "operator black-screen observation missing", errors)
    require(bringup.get("display_evidence", {}).get("human_view_orientation", "").startswith("PASS"), "operator orientation observation missing", errors)
    require(bringup.get("touch_evidence", {}).get("result") == "PASS", "physical touch contact evidence missing", errors)

    refresh = load(REFRESH)
    require(refresh.get("status") == "PASS", "refresh evidence is not PASS", errors)
    require(refresh.get("fast_maintenance_runtime", {}).get("machine_result") == "PASS", "fast maintenance evidence is not PASS", errors)
    require(refresh.get("fast_maintenance_runtime", {}).get("control") == "0xC7", "fast control drifted", errors)
    require(refresh.get("production_runtime", {}).get("interactive_hard_limit") == 60, "production hard limit drifted", errors)
    require(refresh.get("production_runtime", {}).get("flash_verified") is True, "production firmware flash is not verified", errors)

    driver = DRIVER.read_text(encoding="utf-8")
    for marker in [
        "0xF7u",
        "0xFCu",
        "0xCFu",
        "ssd1681_write_plane_region(0x26u, s_frame, &window)",
        "ssd1681_write_plane_region(0x24u, s_frame, &window)",
    ]:
        require(marker in driver, f"driver missing {marker}", errors)

    production_log = evidence_path(refresh["production_runtime"]["log"]).read_text(encoding="utf-8", errors="replace")
    for marker in ["soft=5 hard=60 baseline=0", "refresh mode=full control=0xF7", "refresh mode=partial control=0xFF"]:
        require(marker in production_log, f"production log missing {marker}", errors)

    fast_log = evidence_path(refresh["fast_maintenance_runtime"]["log"]).read_text(encoding="utf-8", errors="replace")
    for marker in ["selected=fast reason=6", "fast_init temperature=0x0064", "refresh mode=fast control=0xC7", "policy_commit mode=fast ok=1 partial_count=0"]:
        require(marker in fast_log, f"fast log missing {marker}", errors)


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
    print(f"PASS: WB55 real-panel refresh evidence verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
