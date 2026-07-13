#!/usr/bin/env python3
"""Verify the real-panel hardware acceptance plan for Companion screen work."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-hardware-acceptance-plan.json")
SCHEMA_ID = "companion.pendant.screen_panel_hardware_acceptance_plan.v1"
GATE_ID = "wb55_real_panel_refresh"

SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
BRINGUP_DOC = REPO_ROOT / "docs" / "bringup_steps.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"
PANEL_TEMPLATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-template.json"
PANEL_RECORD_VALIDATOR = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-record-validator.json"
PANEL_HARDWARE_SESSION = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-session.json"
PANEL_WIRING_PREFLIGHT = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-wiring-preflight.json"
REAL_BLE_BENCH = REPO_ROOT / "docs" / "validation" / "companion-screen-real-ble-bench.json"
DEMO_HOST_STATUS_SEQUENCE = (
    REPO_ROOT / "docs" / "validation" / "companion-screen-expression-demo-host-status-sequence.json"
)
RUNTIME_DIAGNOSTICS = REPO_ROOT / "docs" / "validation" / "companion-screen-runtime-diagnostics.json"
RUNTIME_DIAGNOSTIC_DECODE = REPO_ROOT / "docs" / "validation" / "companion-screen-runtime-diagnostic-decode.json"
DIAGNOSTICS_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-diagnostics-fixture" / "summary.json"
PANEL_BOUNDARY = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-adapter-boundary.json"
PANEL_BEHAVIOR = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-adapter-behavior.json"
PANEL_TARGET_STM32WB = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-target-stm32wb.json"
WBA_PORT_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA55_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"


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


def target_record_path(target: str) -> str:
    return f"docs/validation/companion-screen-panel-evidence-record-{target.lower()}.json"


def build_target_plan(target: str) -> dict[str, Any]:
    adapter_glob = "*_stm32wb.*" if target == "WB55" else "*_stm32wba.*"
    resources = "Companion-WB55,BLE-Companion" if target == "WB55" else f"Companion-{target},BLE-Companion"
    resource_arg = f"'{resources}'"
    record_path = target_record_path(target)
    return {
        "target": target,
        "adapter_file_pattern": adapter_glob,
        "evidence_record": record_path,
        "hardware_lock_resources": resources,
        "hardware_lock_resource_arg": resource_arg,
        "session_scaffold": {
            "session_root_pattern": f".cache/validation/companion-real-panel-{target.lower()}-<timestamp>",
            "fixture": "docs/validation/companion-screen-panel-hardware-session.json",
            "verifier": "python .\\tools\\verify_expression_panel_hardware_session.py",
        },
        "init_record_command": (
            "python .\\tools\\init_expression_panel_evidence_record.py "
            f"--target {target} --output {record_path} --write"
        ),
        "real_ble_expect_panel_command": (
            "pwsh -NoProfile -File <ai-collaboration-workflow>\\scripts\\aiw.ps1 "
            f"with-lock -Resource {resource_arg} -Purpose \"Companion {target} real e-paper panel BLE evidence\" "
            "-Run python .\\tools\\companion_ble_real_bench.py --name companion --timeout 20 "
            "--notify-timeout 10 --screen-final-timeout 30 --expect-real-panel "
            f"--output .\\.cache\\validation\\companion-real-panel-{target.lower()}-<timestamp>\\companion-ble-real-bench.json --json"
        ),
        "real_ble_failure_evidence": {
            "failed_runs_preserve_operations": True,
            "required_fields": ["operations", "partial_operation_count"],
        },
        "record_validator_command": f"python .\\tools\\verify_expression_panel_evidence_record.py --record {record_path}",
        "portability_command": "python .\\tools\\verify_expression_wba_portability.py"
        if target.startswith("WBA")
        else "python .\\tools\\verify_expression_panel_gate.py",
    }


def build_plan() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Records the accepted WB55 real-panel refresh evidence and keeps a "
            "target-specific acceptance handoff ready for WBA55/WBA65 hardware sessions."
        ),
        "gate_id": GATE_ID,
        "current_gate_status": "PASS",
        "real_refresh_claimed_before_hardware": False,
        "evidence_paths": [
            "docs/validation/companion-screen-panel-hardware-acceptance-plan.json",
            "docs/validation/companion-screen-panel-hardware-gate.json",
            "docs/validation/companion-screen-panel-evidence-template.json",
            "docs/validation/companion-screen-panel-evidence-record-validator.json",
            "docs/validation/companion-screen-panel-hardware-session.json",
            "docs/validation/companion-screen-panel-wiring-preflight.json",
            "docs/validation/companion-screen-real-ble-bench.json",
            "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
            "docs/validation/companion-screen-runtime-diagnostics.json",
            "docs/validation/companion-screen-runtime-diagnostic-decode.json",
            "docs/validation/companion-diagnostics-fixture/summary.json",
            "docs/validation/companion-screen-panel-adapter-boundary.json",
            "docs/validation/companion-screen-panel-adapter-behavior.json",
            "docs/validation/companion-screen-panel-target-stm32wb.json",
            "docs/validation/companion-screen-wba-port-contract.json",
            "docs/validation/companion-screen-wba55-port-scaffold.json",
            "docs/companion_screen_expression_system.md",
            "docs/bringup_steps.md",
            "docs/stm32wba_migration_rules.md",
            "tools/verify_expression_panel_hardware_acceptance_plan.py",
            "tools/verify_expression_panel_hardware_session.py",
        ],
        "static_preflight_commands": [
            "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
            "python .\\tools\\verify_expression_panel_hardware_session.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_panel_adapter_behavior.py",
            "python .\\tools\\verify_expression_panel_adapter_boundary.py",
            "python .\\tools\\verify_expression_panel_target_stm32wb.py",
            "python .\\tools\\verify_expression_panel_evidence_template.py",
            "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
            "python .\\tools\\verify_expression_panel_wiring_preflight.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
            "python .\\tools\\verify_companion_diagnostics_static.py",
            "python .\\tools\\verify_screen_presentation.py",
            "python .\\tools\\verify_touch_ft6336.py",
            "python .\\tools\\verify_epaper_refresh_policy.py",
            "python .\\tools\\verify_epaper_fast_maintenance_runtime.py",
            "python .\\tools\\verify_screen_resource_architecture.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
        "target_plans": [
            build_target_plan("WB55"),
            build_target_plan("WBA55"),
            build_target_plan("WBA65"),
        ],
        "hardware_exit_criteria": [
            "selected controller model and datasheet revision recorded",
            "target SPI/DC/RST/BUSY/power pins recorded",
            "reset timing, BUSY timeout, full refresh sequence, partial refresh policy, and sleep sequence recorded",
            "real BLE bench run with --expect-real-panel and real_panel_refresh_claimed=true",
            "failed real BLE bench artifacts preserve operations and partial_operation_count",
            "real BLE bench artifact includes screen_expression_status six-face host sequence baseline",
            "real BLE bench artifact includes screen_expression_demo_status full demo host sequence baseline",
            "card_write and settings_sleepy_screen_status final_card_status are rendered/ok",
            "accepted and final CardStatusV1 request_id/content_crc32 identity is preserved",
            "e_paper.runtime_snapshot decoded_args show zero panel errors, zero pending display work, and zero dropped display work",
            "diagnostics_bundle_artifact summary.json includes epaper.runtime_snapshot_decoded with zero panel errors, zero pending display work, and zero dropped display work",
            "before/during/after visual evidence paths exist and after-photo sha256 matches",
            "target_adapter_file matches *_stm32wb.* for WB55 or *_stm32wba.* for WBA55/WBA65",
            "third_party/STM32CubeWB and third_party/STM32CubeWBA remain clean",
            "verify_expression_panel_evidence_record.py --record passes for the target record",
        ],
        "forbidden_shortcuts": [
            "Do not change wb55_real_panel_refresh to PASS from photos or logs alone.",
            "Do not accept final_card_status=failed/deferred_no_panel or failed/deferred_controller_unknown as real refresh evidence.",
            "Do not put SPI/GPIO/BUSY/reset code into ExpressionV1, display_queue, or panel_adapter portable files.",
            "Do not claim WBA parity from a WB55 adapter rename; WBA needs a CubeWBA project, build wrapper, scheduler hook, BLE adapter, and target evidence record.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
            "python .\\tools\\verify_expression_panel_hardware_session.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\render_expression_acceptance_report.py",
            "python .\\tools\\verify_screen_presentation.py",
            "python .\\tools\\verify_touch_ft6336.py",
            "python .\\tools\\verify_epaper_fast_maintenance_runtime.py",
        ],
    }


def check_plan(data: dict[str, Any], errors: list[str], allow_missing_own_fixture: bool = False) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel hardware acceptance plan schema", errors)
    require(data.get("status") == "PASS", "panel hardware acceptance plan must be PASS", errors)
    require(data.get("gate_id") == GATE_ID, "panel hardware acceptance plan points at the wrong gate", errors)
    require(
        data.get("current_gate_status") == "PASS",
        "panel hardware acceptance plan must record the accepted WB55 hardware gate",
        errors,
    )
    require(
        data.get("real_refresh_claimed_before_hardware") is False,
        "panel hardware acceptance plan must not claim refresh before evidence",
        errors,
    )

    own_fixture = DEFAULT_FIXTURE.as_posix()
    for evidence in data.get("evidence_paths", []):
        if allow_missing_own_fixture and str(evidence).replace("\\", "/") == own_fixture:
            continue
        require((REPO_ROOT / str(evidence)).exists(), f"plan evidence path missing: {evidence}", errors)
    commands = "\n".join(str(command) for command in data.get("static_preflight_commands", []))
    for token in [
        "verify_expression_panel_hardware_session.py",
        "verify_expression_panel_gate.py",
        "verify_expression_panel_adapter_behavior.py",
        "verify_expression_panel_adapter_boundary.py",
        "verify_expression_panel_target_stm32wb.py",
        "verify_expression_panel_evidence_template.py",
        "verify_expression_panel_evidence_record.py --self-test",
        "verify_expression_panel_wiring_preflight.py",
        "verify_expression_real_ble_screen_bench.py",
        "verify_expression_screen_runtime_diagnostics.py",
        "verify_expression_screen_runtime_diagnostic_decode.py",
        "verify_companion_diagnostics_static.py",
        "verify_screen_presentation.py",
        "verify_touch_ft6336.py",
        "verify_epaper_refresh_policy.py",
        "verify_epaper_fast_maintenance_runtime.py",
        "verify_screen_resource_architecture.py",
        "verify_expression_wba_portability.py",
        "build_nucleo_bringup.ps1",
    ]:
        require(token in commands, f"static preflight command missing {token}", errors)

    targets = {entry.get("target"): entry for entry in data.get("target_plans", []) if isinstance(entry, dict)}
    require(set(targets) == {"WB55", "WBA55", "WBA65"}, "target plans must cover WB55, WBA55, and WBA65", errors)
    for target, entry in targets.items():
        serialized = json.dumps(entry, sort_keys=True)
        require(f"--target {target}" in serialized, f"{target} plan missing init target", errors)
        require(
            f"companion-real-panel-{target.lower()}-<timestamp>" in serialized,
            f"{target} plan missing target session root",
            errors,
        )
        require(
            "companion-screen-panel-hardware-session.json" in serialized,
            f"{target} plan missing hardware session fixture",
            errors,
        )
        require("--expect-real-panel" in serialized, f"{target} plan missing real-panel BLE bench flag", errors)
        require("-Resource '" in serialized, f"{target} plan must quote comma-separated hardware lock resources", errors)
        require("partial_operation_count" in serialized, f"{target} plan missing partial failure evidence", errors)
        require("verify_expression_panel_evidence_record.py --record" in serialized, f"{target} plan missing record validator", errors)
        if target == "WB55":
            require("*_stm32wb.*" in serialized, "WB55 plan missing *_stm32wb.* adapter pattern", errors)
            require("Companion-WB55,BLE-Companion" in serialized, "WB55 plan missing hardware lock resources", errors)
        else:
            require("*_stm32wba.*" in serialized, f"{target} plan missing *_stm32wba.* adapter pattern", errors)
            require("verify_expression_wba_portability.py" in serialized, f"{target} plan missing WBA portability check", errors)

    exit_criteria = "\n".join(str(value) for value in data.get("hardware_exit_criteria", []))
    for token in [
        "rendered/ok",
        "real_panel_refresh_claimed=true",
        "partial_operation_count",
        "screen_expression_status",
        "screen_expression_demo_status",
        "request_id/content_crc32",
        "e_paper.runtime_snapshot",
        "diagnostics_bundle_artifact",
        "epaper.runtime_snapshot_decoded",
        "zero panel errors",
        "before/during/after visual evidence",
        "third_party/STM32CubeWB",
        "third_party/STM32CubeWBA",
        "verify_expression_panel_evidence_record.py --record",
    ]:
        require(token in exit_criteria, f"hardware exit criteria missing {token}", errors)
    forbidden = "\n".join(str(value) for value in data.get("forbidden_shortcuts", []))
    for token in ["deferred_no_panel", "portable files", "WBA parity", "WB55 adapter rename"]:
        require(token in forbidden, f"forbidden shortcuts missing {token}", errors)


def check_existing_contracts(errors: list[str]) -> None:
    gate = read_json(PANEL_GATE, errors)
    require(gate.get("gate_id") == GATE_ID, "panel gate fixture uses unexpected gate id", errors)
    require(gate.get("status") == "PASS", "panel gate fixture must record accepted real refresh", errors)
    require(gate.get("real_refresh_claimed") is True, "panel gate fixture must claim verified real refresh", errors)

    real_ble = read_json(REAL_BLE_BENCH, errors)
    serialized_real_ble = json.dumps(real_ble, sort_keys=True)
    require("--expect-real-panel" in serialized_real_ble, "real BLE bench fixture missing --expect-real-panel", errors)
    require("screen_expression_status" in serialized_real_ble, "real BLE bench fixture missing screen_expression_status operation", errors)
    require(
        "screen_expression_demo_status" in serialized_real_ble,
        "real BLE bench fixture missing screen_expression_demo_status operation",
        errors,
    )
    require("settings_sleepy_screen_status" in serialized_real_ble, "real BLE bench fixture missing settings sleepy operation", errors)
    require("real_panel_refresh_claimed" in serialized_real_ble, "real BLE bench fixture missing real panel claim field", errors)

    template = read_json(PANEL_TEMPLATE, errors)
    serialized_template = json.dumps(template, sort_keys=True)
    for token in [
        "real_ble_bench_artifact",
        "diagnostics_bundle_artifact",
        "screen_expression_status",
        "screen_expression_demo_status",
        "e_paper.runtime_snapshot",
        "target_adapter_file",
        "before_photo",
        "during_refresh_photo_or_video",
        "after_photo",
    ]:
        require(token in serialized_template, f"panel evidence template missing {token}", errors)

    session = read_json(PANEL_HARDWARE_SESSION, errors)
    require(
        session.get("schema_id") == "companion.pendant.screen_panel_hardware_session.v1",
        "panel hardware session fixture uses unexpected schema",
        errors,
    )
    require(session.get("status") == "PASS", "panel hardware session fixture must be PASS", errors)
    require(
        session.get("current_gate_status") == "DEFERRED_HARDWARE",
        "panel hardware session scaffold must start future target sessions as deferred",
        errors,
    )

    validator = read_json(PANEL_RECORD_VALIDATOR, errors)
    serialized_validator = json.dumps(validator, sort_keys=True)
    require("placeholder tokens such as TODO_CONTROLLER_MODEL are rejected recursively" in serialized_validator, "record validator must reject TODO placeholders", errors)
    require("e_paper.runtime_snapshot decoded_args show zero panel errors" in serialized_validator, "record validator must require runtime snapshot health", errors)
    require("diagnostics bundle summary carries epaper.runtime_snapshot_decoded" in serialized_validator, "record validator must require diagnostics bundle health", errors)
    require("screen_expression_status six-face host sequence baseline" in serialized_validator, "record validator must require screen expression sequence baseline", errors)
    require(
        "screen_expression_demo_status full demo host sequence baseline" in serialized_validator,
        "record validator must require screen expression demo sequence baseline",
        errors,
    )
    require("scaffold records stay DRAFT_UNFILLED" in serialized_validator, "record validator must reject draft scaffolds", errors)

    require(RUNTIME_DIAGNOSTICS.exists(), "runtime diagnostics fixture missing", errors)
    require(RUNTIME_DIAGNOSTIC_DECODE.exists(), "runtime diagnostic decode fixture missing", errors)
    require(DIAGNOSTICS_FIXTURE.exists(), "diagnostics summary fixture missing", errors)
    require(PANEL_WIRING_PREFLIGHT.exists(), "panel wiring preflight fixture missing", errors)
    require(DEMO_HOST_STATUS_SEQUENCE.exists(), "demo host expression status sequence fixture missing", errors)
    require(PANEL_BOUNDARY.exists(), "panel adapter boundary fixture missing", errors)
    require(PANEL_BEHAVIOR.exists(), "panel adapter behavior fixture missing", errors)
    require(PANEL_TARGET_STM32WB.exists(), "WB55 panel target adapter fixture missing", errors)
    require(WBA_PORT_CONTRACT.exists(), "WBA port contract fixture missing", errors)
    require(WBA55_SCAFFOLD.exists(), "WBA55 port scaffold fixture missing", errors)


def check_docs_and_index(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    bringup_doc = read_text(BRINGUP_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    index = read_json(ACCEPTANCE_INDEX, errors)

    for text, name in [(screen_doc, "screen doc"), (bringup_doc, "bringup doc")]:
        for token in [
            "panel_hardware_acceptance_plan",
            "companion-screen-panel-hardware-acceptance-plan.json",
            "companion-screen-panel-wiring-preflight.json",
            "companion-screen-panel-hardware-session.json",
            "verify_expression_panel_wiring_preflight.py",
            "verify_expression_panel_hardware_acceptance_plan.py",
            "verify_expression_panel_hardware_session.py",
            "panel_hardware_session_scaffold",
            "companion-real-panel-wb55-<timestamp>",
            "operator-notes.md",
            "visual/before_photo.jpg",
            "--expect-real-panel",
            "screen_expression_status",
            "screen_expression_demo_status",
            "verify_expression_panel_evidence_record.py --record",
            "e_paper.runtime_snapshot",
            "diagnostics_bundle_artifact",
            "collect_companion_diagnostics.ps1",
        ]:
            require(token in text, f"{name} missing hardware acceptance plan anchor {token}", errors)

    for token in [
        "WBA55",
        "WBA65",
        "panel hardware acceptance plan",
        "panel_error_count=0",
        "diagnostics_bundle_artifact",
        "screen_expression_status",
        "screen_expression_demo_status",
        "*_stm32wba.*",
        "verify_expression_panel_hardware_acceptance_plan.py",
        "verify_expression_panel_hardware_session.py",
        "panel hardware session scaffold",
        "companion-screen-panel-hardware-session.json",
    ]:
        require(token in wba_rules, f"WBA rules missing hardware acceptance plan anchor {token}", errors)

    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    plan_items = [item for item in items if item.get("id") == "panel_hardware_acceptance_plan"]
    if allow_stale_index:
        return
    require(len(plan_items) == 1, "acceptance index must contain one panel_hardware_acceptance_plan item", errors)
    if plan_items:
        item = plan_items[0]
        require(item.get("status") == "PASS", "panel_hardware_acceptance_plan index item must be PASS", errors)
        require(
            "docs/validation/companion-screen-panel-hardware-acceptance-plan.json" in item.get("evidence_paths", []),
            "panel_hardware_acceptance_plan item must link its fixture",
            errors,
        )
        require(
            "docs/validation/companion-screen-panel-hardware-session.json" in item.get("evidence_paths", []),
            "panel_hardware_acceptance_plan item must link the hardware session fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py" in item.get("validation_commands", []),
            "panel_hardware_acceptance_plan item must run its verifier",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_panel_hardware_session.py" in item.get("validation_commands", []),
            "panel_hardware_acceptance_plan item must run the hardware session verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel hardware acceptance plan fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_plan(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic hardware acceptance plan JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_plan()
    errors: list[str] = []

    check_plan(expected, errors, allow_missing_own_fixture=bool(args.write_fixture))
    check_existing_contracts(errors)
    check_docs_and_index(errors, allow_stale_index=bool(args.write_fixture))

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen panel hardware acceptance plan checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen panel hardware acceptance plan verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
