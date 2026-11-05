#!/usr/bin/env python3
"""Create or verify the first STM32WBA screen-port scaffold."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "docs/validation/companion-screen-wba55-port-scaffold.json"
WBA_CONTRACT = REPO_ROOT / "docs/validation/companion-screen-wba-port-contract.json"
PANEL_EVIDENCE_TOOL = REPO_ROOT / "tools" / "init_expression_panel_evidence_record.py"
SCHEMA_ID = "companion.pendant.screen_wba_port_scaffold.v1"
TARGETS = ("WBA55", "WBA65")


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def lower_target(target: str) -> str:
    return target.lower()


def target_mode(target: str) -> str:
    if target == "WBA55":
        return "baseline_constrained_target"
    return "expanded_target_must_preserve_wba55_safe_contract"


def build_scaffold(target: str) -> dict[str, Any]:
    contract = load_json(WBA_CONTRACT)
    target_slug = lower_target(target)
    panel_record = f"docs/validation/companion-screen-panel-evidence-record-{target_slug}-scaffold.json"
    return {
        "_instructions": [
            "This scaffold is intentionally a pre-port checklist, not parity evidence.",
            "Keep status DRAFT_PRE_PORT until a separate CubeWBA project, WBA build wrapper, WBA BLE adapter, scheduler hook, and target-named panel adapter exist.",
            "Use the listed invariants to review the WBA branch before claiming it matches WB55 behavior.",
            "Generate the target panel evidence record separately and keep it failing until real controller, pin, timing, BLE, and visual evidence are filled.",
        ],
        "schema_id": SCHEMA_ID,
        "status": "DRAFT_PRE_PORT",
        "target": target,
        "source_contract": rel(WBA_CONTRACT),
        "target_assumptions": {
            "target_mode": target_mode(target),
            "wba55_baseline": contract.get("targets", {}).get("baseline"),
            "wba65_expanded": contract.get("targets", {}).get("expanded"),
            "budget_rule": contract.get("targets", {}).get("rule"),
            "target_capability_profile": contract.get("sources", {}).get("target_capability_profile"),
        },
        "carry_over_portable_files": contract.get("portable_screen_files", []),
        "portable_invariants": {
            "expression_states": contract.get("portable_contracts", {}).get("expression_states", []),
            "display_queue_depth": contract.get("portable_contracts", {}).get("display_queue_depth"),
            "display_payload_max_bytes": contract.get("portable_contracts", {}).get("display_payload_max_bytes"),
            "display_drain_contract": contract.get("portable_contracts", {}).get("display_drain_contract"),
            "target_capability_profile": contract.get("portable_contracts", {}).get("target_capability_profile"),
            "wba_cube_dependency_preflight": contract.get("portable_contracts", {}).get("wba_cube_dependency_preflight"),
            "settings_sleepy_signal": contract.get("portable_contracts", {}).get("settings_sleepy_signal"),
            "expression_request_id_base": contract.get("portable_contracts", {}).get("expression_request_id_base"),
            "expression_card_slot": contract.get("portable_contracts", {}).get("expression_card_slot"),
            "expression_visual_contract": contract.get("portable_contracts", {}).get("expression_visual_contract"),
            "expression_copy_contract": contract.get("portable_contracts", {}).get("expression_copy_contract"),
            "expression_layout_contract": contract.get("portable_contracts", {}).get("expression_layout_contract"),
            "expression_priority_matrix": contract.get("portable_contracts", {}).get("expression_priority_matrix"),
            "expression_input_source_matrix": contract.get("portable_contracts", {}).get("expression_input_source_matrix"),
            "panel_callback": contract.get("portable_contracts", {}).get("panel_callback"),
            "wba_panel_target_scaffold": contract.get("portable_contracts", {}).get("wba_panel_target_scaffold"),
            "wba_display_scheduler_scaffold": contract.get("portable_contracts", {}).get("wba_display_scheduler_scaffold"),
            "wba_screen_gatt_scaffold": contract.get("portable_contracts", {}).get("wba_screen_gatt_scaffold"),
            "wba_screen_assets_scaffold": contract.get("portable_contracts", {}).get("wba_screen_assets_scaffold"),
            "wba_touch_target_scaffold": contract.get("portable_contracts", {}).get("wba_touch_target_scaffold"),
            "screen_runtime_snapshot": contract.get("portable_contracts", {}).get("screen_runtime_snapshot"),
            "card_status_contract": contract.get("portable_contracts", {}).get("card_status_contract"),
            "real_ble_screen_operations": contract.get("portable_contracts", {}).get("real_ble_screen_operations", []),
        },
        "required_new_artifacts": [
            {
                "id": "cube_project",
                "path": f"TODO_CUBEWBA_PROJECT_PATH_FOR_{target}",
                "acceptance": "Separate CubeWBA project; do not retarget the WB55 Cube project in place.",
            },
            {
                "id": "cube_wba_dependency_preflight",
                "path": "docs/validation/companion-screen-wba-cube-dependency-preflight.json",
                "acceptance": "Records whether third_party/STM32CubeWBA is present, keeps WBA status DRAFT_PRE_PORT while the CubeWBA dependency/build wrapper is missing, and passes verify_expression_wba_cube_dependency_preflight.py.",
            },
            {
                "id": "build_wrapper",
                "path": f"TODO_WBA_BUILD_WRAPPER_FOR_{target}",
                "acceptance": "Scriptable build wrapper analogous to tools/build_nucleo_bringup.ps1.",
            },
            {
                "id": "ble_gatt_adapter",
                "path": "TODO_WBA_BLE_GATT_ADAPTER_*_stm32wba.*",
                "acceptance": "Preserves UUIDs, payload layouts, CardStatusV1 meanings, and settings_sleepy_screen_status behavior.",
            },
            {
                "id": "ble_gatt_adapter_scaffold",
                "path": "app/companion_pendant/epaper/screen_gatt_stm32wba.c",
                "acceptance": "Initial WBA55/WBA65 screen GATT scaffold exists, exposes companion_epaper_stm32wba_screen_gatt_accept_card_write, preserves screen_expression_status identity rules, and passes verify_expression_screen_gatt_stm32wba.py before CubeWBA service integration is added.",
            },
            {
                "id": "scheduler_timer_hook",
                "path": "TODO_WBA_SCHEDULER_TIMER_HOOK_*_stm32wba.*",
                "acceptance": "Wakes the WBA display task and feeds comp_epaper_expression_state_tick().",
            },
            {
                "id": "scheduler_timer_hook_scaffold",
                "path": "app/companion_pendant/epaper/screen_scheduler_stm32wba.c",
                "acceptance": "Initial WBA55/WBA65 display scheduler/timer scaffold exists, exposes companion_epaper_stm32wba_schedule_expression_tick, stays callback-only, and passes verify_expression_screen_scheduler_stm32wba.py before CubeWBA scheduler integration is added.",
            },
            {
                "id": "panel_target_adapter_scaffold",
                "path": "app/companion_pendant/epaper/panel_target_stm32wba.c",
                "acceptance": "Initial WBA55/WBA65 target-named scaffold defaults to dry-run, binds only a target-owned refresh callback, and passes verify_expression_panel_target_stm32wba.py before real transport is added.",
            },
            {
                "id": "panel_transport_adapter",
                "path": "TODO_WBA_PANEL_TRANSPORT_*_stm32wba.*",
                "acceptance": "Wired only through comp_epaper_panel_refresh_fn_t and keeps SPI/GPIO/BUSY code out of portable files.",
            },
            {
                "id": "screen_assets_adapter_scaffold",
                "path": "app/companion_pendant/epaper/screen_assets_stm32wba.c",
                "acceptance": "Initial WBA55/WBA65 screen-assets scaffold binds a target-owned logical external-NOR partition reader, checks every read against partition_size, and passes verify_expression_screen_assets_stm32wba.py before CubeWBA storage integration is added.",
            },
            {
                "id": "touch_target_adapter_scaffold",
                "path": "app/companion_pendant/touch/touch_target_stm32wba_ft6336.c",
                "acceptance": "Initial WBA55/WBA65 FT6336 scaffold uses 7-bit probe/register-read callbacks, reuses the portable decoder, and passes verify_touch_target_stm32wba_ft6336.py before CubeWBA I2C integration is added.",
            },
            {
                "id": "real_ble_bench_artifact",
                "path": f"TODO_REAL_BLE_BENCH_EXPECT_REAL_PANEL_{target}.json",
                "acceptance": "Includes screen_expression_status six-face baseline plus card_write and settings_sleepy_screen_status final rendered/ok evidence with --expect-real-panel.",
            },
            {
                "id": "panel_evidence_record",
                "path": panel_record,
                "acceptance": "Passes verify_expression_panel_evidence_record.py --record only after real panel facts and visual evidence are filled.",
            },
        ],
        "forbidden_shortcuts": [
            "Do not copy WB55 CPU2/FUS/IPCC/HSEM/STM32_WPAN mechanics into WBA portable files.",
            "Do not rename a WB55 adapter as WBA without a separate CubeWBA build and real validation.",
            "Do not use WBA65-only resources unless the WBA55-safe contract still passes or a capability flag gates the expansion.",
            "Do not move panel SPI/GPIO/reset/BUSY timing into ExpressionV1, display_queue, or panel_adapter portable files.",
            "Do not put a physical flash address, erase/write routine, or active-pack switch into the portable asset store or its WBA read adapter.",
        ],
        "bootstrap_commands": [
            f"python .\\tools\\init_expression_wba_port_scaffold.py --target {target} --write",
            f"python .\\tools\\init_expression_panel_evidence_record.py --target {target} --output {panel_record} --write",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py",
            "python .\\tools\\verify_expression_display_drain.py",
            "python .\\tools\\verify_expression_target_capabilities.py",
            "python .\\tools\\verify_expression_visual_contract.py",
            "python .\\tools\\verify_expression_layout_contract.py",
            "python .\\tools\\verify_expression_priority_matrix.py",
            "python .\\tools\\verify_expression_input_source_matrix.py",
            "python .\\tools\\verify_expression_screen_assets_stm32wba.py",
            "python .\\tools\\verify_touch_target_stm32wba_ft6336.py",
            "python .\\tools\\run_expression_acceptance.py --pass-only --skip-build --output .\\.cache\\validation\\companion-screen-wba-pre-port-run.json",
        ],
        "parity_exit_criteria": [
            "WBA build wrapper passes for the selected target.",
            "The no-hardware screen acceptance suite passes with WBA platform code added.",
            "Display drain contract stays passing after WBA display task and panel transport are added.",
            "Target capability profile stays WBA55-safe before any WBA65-only resource or larger shared limit is used.",
            "Expression visual and layout contracts stay passing after WBA platform code is added.",
            "Expression priority matrix stays passing after WBA scheduler or status-adapter code is added.",
            "Expression input source matrix stays passing after WBA status adapters are added.",
            "Real BLE bench carries screen_expression_status baseline and preserves accepted/final CardStatusV1 identity for card_write and settings_sleepy_screen_status.",
            "Panel evidence record passes with a *_stm32wba.* adapter file, real panel timing, clean portability notes, and visual proof.",
            "third_party/STM32CubeWB and third_party/STM32CubeWBA remain clean.",
        ],
    }


def write_output(path: pathlib.Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_record(record: dict[str, Any], target: str) -> list[str]:
    errors: list[str] = []
    require(record.get("schema_id") == SCHEMA_ID, "unexpected WBA port scaffold schema", errors)
    require(record.get("status") == "DRAFT_PRE_PORT", "WBA port scaffold must stay DRAFT_PRE_PORT", errors)
    require(record.get("target") == target, f"WBA port scaffold target must be {target}", errors)
    require(record.get("source_contract") == rel(WBA_CONTRACT), "WBA port scaffold source contract drifted", errors)
    assumptions = record.get("target_assumptions", {})
    require(assumptions.get("target_mode") == target_mode(target), "WBA port scaffold target mode drifted", errors)
    require(
        assumptions.get("target_capability_profile") == "docs/validation/companion-screen-target-capabilities.json",
        "WBA port scaffold missing target capability profile source",
        errors,
    )
    invariants = record.get("portable_invariants", {})
    require(invariants.get("display_queue_depth") == 4, "WBA port scaffold queue depth drifted", errors)
    require(invariants.get("display_payload_max_bytes") == 236, "WBA port scaffold payload bound drifted", errors)
    require(
        "verify_expression_display_drain.py" in str(invariants.get("display_drain_contract", "")),
        "WBA port scaffold missing display drain invariant",
        errors,
    )
    require(
        "verify_expression_target_capabilities.py" in str(invariants.get("target_capability_profile", "")),
        "WBA port scaffold missing target capability invariant",
        errors,
    )
    require(
        "third_party/STM32CubeWBA" in str(invariants.get("wba_cube_dependency_preflight", "")),
        "WBA port scaffold missing CubeWBA dependency preflight invariant",
        errors,
    )
    require(
        invariants.get("settings_sleepy_signal") == "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "WBA port scaffold missing settings sleepy invariant",
        errors,
    )
    require(
        invariants.get("panel_callback") == "comp_epaper_panel_refresh_fn_t",
        "WBA port scaffold missing panel callback invariant",
        errors,
    )
    require(
        "panel_target_stm32wba.h/.c" in str(invariants.get("wba_panel_target_scaffold", "")),
        "WBA port scaffold missing WBA panel target scaffold invariant",
        errors,
    )
    require(
        "screen_scheduler_stm32wba.h/.c" in str(invariants.get("wba_display_scheduler_scaffold", "")),
        "WBA port scaffold missing WBA display scheduler scaffold invariant",
        errors,
    )
    require(
        "screen_gatt_stm32wba.h/.c" in str(invariants.get("wba_screen_gatt_scaffold", "")),
        "WBA port scaffold missing WBA screen GATT scaffold invariant",
        errors,
    )
    require(
        "screen_assets_stm32wba.h/.c" in str(invariants.get("wba_screen_assets_scaffold", "")),
        "WBA port scaffold missing WBA screen-assets scaffold invariant",
        errors,
    )
    require(
        "touch_target_stm32wba_ft6336.h/.c" in str(invariants.get("wba_touch_target_scaffold", "")),
        "WBA port scaffold missing WBA touch target scaffold invariant",
        errors,
    )
    require(
        "verify_expression_visual_contract.py" in str(invariants.get("expression_visual_contract", "")),
        "WBA port scaffold missing expression visual contract invariant",
        errors,
    )
    require(
        "verify_expression_copy_contract.py" in str(invariants.get("expression_copy_contract", "")),
        "WBA port scaffold missing expression copy contract invariant",
        errors,
    )
    require(
        "verify_expression_layout_contract.py" in str(invariants.get("expression_layout_contract", "")),
        "WBA port scaffold missing expression layout contract invariant",
        errors,
    )
    require(
        "verify_expression_priority_matrix.py" in str(invariants.get("expression_priority_matrix", "")),
        "WBA port scaffold missing expression priority matrix invariant",
        errors,
    )
    require(
        "verify_expression_input_source_matrix.py" in str(invariants.get("expression_input_source_matrix", "")),
        "WBA port scaffold missing expression input source matrix invariant",
        errors,
    )
    require(
        "comp_epaper_screen_runtime_snapshot" in str(invariants.get("screen_runtime_snapshot", "")),
        "WBA port scaffold missing screen runtime snapshot invariant",
        errors,
    )
    artifacts = {str(item.get("id")): item for item in record.get("required_new_artifacts", []) if isinstance(item, dict)}
    for artifact_id in [
        "cube_project",
        "cube_wba_dependency_preflight",
        "build_wrapper",
        "ble_gatt_adapter",
        "ble_gatt_adapter_scaffold",
        "scheduler_timer_hook",
        "scheduler_timer_hook_scaffold",
        "panel_transport_adapter",
        "panel_target_adapter_scaffold",
        "screen_assets_adapter_scaffold",
        "touch_target_adapter_scaffold",
        "real_ble_bench_artifact",
        "panel_evidence_record",
    ]:
        require(artifact_id in artifacts, f"WBA port scaffold missing artifact {artifact_id}", errors)
    serialized = json.dumps(record, sort_keys=True)
    for token in [
        "TODO_WBA_BLE_GATT_ADAPTER_*_stm32wba.*",
        "companion-screen-wba-cube-dependency-preflight.json",
        "verify_expression_wba_cube_dependency_preflight.py",
        "third_party/STM32CubeWBA",
        "screen_gatt_stm32wba.c",
        "verify_expression_screen_gatt_stm32wba.py",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "screen_assets_stm32wba.c",
        "verify_expression_screen_assets_stm32wba.py",
        "partition_size",
        "TODO_WBA_PANEL_TRANSPORT_*_stm32wba.*",
        "panel_target_stm32wba.c",
        "verify_expression_panel_target_stm32wba.py",
        "screen_scheduler_stm32wba.c",
        "verify_expression_screen_scheduler_stm32wba.py",
        "touch_target_stm32wba_ft6336.c",
        "verify_touch_target_stm32wba_ft6336.py",
        "--expect-real-panel",
        "screen_expression_status",
        "settings_sleepy_screen_status",
        "verify_expression_display_drain.py",
        "verify_expression_target_capabilities.py",
        "verify_expression_visual_contract.py",
        "verify_expression_copy_contract.py",
        "verify_expression_layout_contract.py",
        "verify_expression_priority_matrix.py",
        "verify_expression_input_source_matrix.py",
        "comp_epaper_screen_runtime_snapshot",
        "verify_expression_panel_evidence_record.py --record",
    ]:
        require(token in serialized, f"WBA port scaffold missing anchor {token}", errors)
    if target == "WBA65":
        require("WBA55-safe" in serialized, "WBA65 scaffold must preserve WBA55-safe contract note", errors)
    return errors


def verify_output(path: pathlib.Path, expected: dict[str, Any], target: str) -> list[str]:
    errors = verify_record(expected, target)
    if not path.exists():
        errors.append(f"missing WBA port scaffold: {rel(path)}")
        return errors
    actual = load_json(path)
    if actual != expected:
        errors.append(f"stale WBA port scaffold: {rel(path)}")
    errors.extend(verify_record(actual, target))
    return errors


def run_self_test() -> list[str]:
    errors: list[str] = []
    for target in TARGETS:
        record = build_scaffold(target)
        errors.extend(verify_record(record, target))
        serialized = json.dumps(record, sort_keys=True)
        require(f"TODO_CUBEWBA_PROJECT_PATH_FOR_{target}" in serialized, f"self-test missing CubeWBA TODO for {target}", errors)
        require(f"--target {target}" in serialized, f"self-test missing target bootstrap command for {target}", errors)
        require("STM32_WPAN" in serialized, f"self-test missing WB55 forbidden shortcut for {target}", errors)
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target", choices=TARGETS, default="WBA55")
    parser.add_argument("--write", action="store_true", help="Write the scaffold JSON.")
    parser.add_argument("--self-test", action="store_true", help="Verify WBA55 and WBA65 scaffold generation.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    for path in [WBA_CONTRACT, PANEL_EVIDENCE_TOOL]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if not errors and args.self_test:
        errors.extend(run_self_test())

    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    if not errors:
        record = build_scaffold(args.target)
        if args.write:
            write_output(output, record)
        errors.extend(verify_output(output, record, args.target))

    if errors:
        print("FAIL: Companion WBA port scaffold checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WBA port scaffold verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
