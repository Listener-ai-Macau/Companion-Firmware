#!/usr/bin/env python3
"""Verify the screen target capability profile for WB55 and future WBA ports."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-target-capabilities.json")
SCHEMA_ID = "companion.pendant.screen_target_capabilities.v1"

DISPLAY_QUEUE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "display_queue.h"
EXPRESSION_STATE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
PANEL_ADAPTER_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
SCREEN_RUNTIME_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "screen_runtime.h"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Target capability profile for keeping the screen expression layer WBA55-safe while allowing explicit WBA65 expansion.",
        "sources": {
            "display_queue_header": rel(DISPLAY_QUEUE_HEADER),
            "expression_state_header": rel(EXPRESSION_STATE_HEADER),
            "panel_adapter_header": rel(PANEL_ADAPTER_HEADER),
            "screen_runtime_header": rel(SCREEN_RUNTIME_HEADER),
            "wb55_integration": rel(APP_BLE),
            "wb55_build": rel(MAKEFILE),
            "wba_port_contract": rel(WBA_CONTRACT),
            "wba55_port_scaffold": rel(WBA_SCAFFOLD),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "target_profiles": {
            "WB55_DEVBOARD": {
                "family": "STM32WB",
                "role": "current_validation_target",
                "platform_scope": "WB55 owns CPU2/FUS/IPCC/HSEM/STM32_WPAN glue, UTIL_SEQ/HW_TS scheduling, and the current dry-run panel target adapter.",
                "build_wrapper": "tools/build_nucleo_bringup.ps1",
                "panel_adapter": "app/companion_pendant/epaper/panel_target_stm32wb.c",
                "real_panel_status": "DEFERRED_HARDWARE",
            },
            "WBA55": {
                "family": "STM32WBA",
                "role": "baseline_constrained_target",
                "platform_scope": "First WBA port must use a separate CubeWBA project, WBA build wrapper, WBA BLE/GATT adapter, WBA scheduler/timer hook, and *_stm32wba.* panel adapter.",
                "inherits_shared_screen_contract": True,
                "expansion_policy": "No common screen protocol, queue, or payload expansion without preserving this WBA55-safe profile.",
            },
            "WBA65": {
                "family": "STM32WBA",
                "role": "expanded_target",
                "platform_scope": "May use additional WBA65 resources only behind target capability flags and only after the WBA55-safe contract still passes.",
                "inherits_shared_screen_contract": True,
                "expansion_policy": "Expanded resources must not change shared ExpressionV1 IDs, CardStatusV1 meanings, display queue bounds, or real BLE evidence shape.",
            },
        },
        "shared_screen_limits": {
            "display_queue_depth": 4,
            "display_payload_max_bytes": 236,
            "expression_request_id_base": "0xe0000000",
            "expression_card_slot": 1,
            "stable_expression_states": [
                "idle",
                "listening",
                "thinking",
                "speaking",
                "happy",
                "sleepy",
                "recording",
                "sync_complete",
                "low_battery",
                "error",
            ],
            "real_ble_operations": [
                "screen_expression_status",
                "card_write",
                "settings_sleepy_screen_status",
            ],
            "runtime_snapshot_event": "e_paper.runtime_snapshot",
            "panel_callback": "comp_epaper_panel_refresh_fn_t",
        },
        "wba_expansion_rules": [
            "WBA55 is the safe baseline for shared screen protocol, queue, payload, and diagnostic contracts.",
            "WBA65 may add target-specific resources only behind explicit capability flags.",
            "Any larger WBA65-only payload, queue, panel feature, or low-power path must keep a WBA55-safe fallback and new validation evidence.",
            "Do not retarget the WB55 Cube project in place; create a separate CubeWBA project and build wrapper.",
            "Do not move BLE stack, scheduler, SPI/GPIO/BUSY, reset timing, pins, or board power policy into portable screen files.",
        ],
        "acceptance": {
            "wb55_profile_is_current_validation_target": True,
            "wba55_is_conservative_baseline": True,
            "wba65_is_expanded_only_with_capability_flags": True,
            "shared_limits_match_portable_headers": True,
            "wba_contract_reuses_target_capability_profile": True,
            "wba_scaffold_carries_target_capability_profile": True,
            "third_party_cube_repos_remain_clean": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_target_capabilities.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_expression_display_drain.py",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ],
    }


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def check_source_limits(errors: list[str]) -> None:
    queue_header = read(DISPLAY_QUEUE_HEADER, errors)
    expression_header = read(EXPRESSION_STATE_HEADER, errors)
    panel_header = read(PANEL_ADAPTER_HEADER, errors)
    runtime_header = read(SCREEN_RUNTIME_HEADER, errors)
    for token in [
        "COMP_EPAPER_DISPLAY_QUEUE_DEPTH 4u",
        "COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES 236u",
        "comp_epaper_display_queue_snapshot_t",
    ]:
        require(token in queue_header, f"display queue header missing target capability token {token}", errors)
    for token in [
        "COMP_EPAPER_EXPRESSION_IDLE",
        "COMP_EPAPER_EXPRESSION_LOW_BATTERY",
        "COMP_EPAPER_EXPRESSION_ERROR",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
        "comp_epaper_expression_signal_is_supported",
        "comp_epaper_expression_state_snapshot",
    ]:
        require(token in expression_header, f"expression state header missing target capability token {token}", errors)
    require("comp_epaper_panel_refresh_fn_t" in panel_header, "panel adapter must expose target-owned refresh callback", errors)
    require(
        "comp_epaper_screen_runtime_snapshot" in runtime_header,
        "screen runtime must expose portable aggregate snapshot for target code",
        errors,
    )


def check_wb55_boundary(errors: list[str]) -> None:
    app_ble = read(APP_BLE, errors)
    makefile = read(MAKEFILE, errors)
    for token in [
        '#include "panel_target_stm32wb.h"',
        "companion_epaper_panel_stm32wb_init(",
        "&s_companion_panel_adapter,",
        "expression_assets_ready ? &s_companion_expression_asset_source : NULL",
        "HW_TS_Create(CFG_TIM_PROC_ID_ISR",
        "UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID",
    ]:
        require(token in app_ble, f"WB55 integration missing target capability token {token}", errors)
    for token in [
        "display_queue.c",
        "expression_state.c",
        "panel_adapter.c",
        "panel_target_stm32wb.c",
        "screen_runtime.c",
    ]:
        require(token in makefile, f"WB55 build missing target capability source {token}", errors)


def check_wba_contracts(errors: list[str]) -> None:
    contract = load_json(WBA_CONTRACT, errors)
    scaffold = load_json(WBA_SCAFFOLD, errors)
    targets = contract.get("targets", {})
    require(targets.get("baseline") == "STM32WBA55", "WBA contract must keep WBA55 as baseline", errors)
    require(targets.get("expanded") == "STM32WBA65", "WBA contract must keep WBA65 as expanded target", errors)
    require("WBA55-safe" in str(targets.get("rule", "")), "WBA contract must state WBA55-safe budget rule", errors)
    portable = contract.get("portable_contracts", {})
    require(portable.get("display_queue_depth") == 4, "WBA contract queue depth drifted", errors)
    require(portable.get("display_payload_max_bytes") == 236, "WBA contract payload bound drifted", errors)
    require(
        "verify_expression_target_capabilities.py" in str(portable.get("target_capability_profile", "")),
        "WBA contract missing target capability profile invariant",
        errors,
    )
    require(
        contract.get("sources", {}).get("target_capability_profile") == rel(REPO_ROOT / DEFAULT_FIXTURE),
        "WBA contract missing target capability fixture source",
        errors,
    )
    assumptions = scaffold.get("target_assumptions", {})
    require(assumptions.get("wba55_baseline") == "STM32WBA55", "WBA scaffold lost WBA55 baseline assumption", errors)
    require(assumptions.get("wba65_expanded") == "STM32WBA65", "WBA scaffold lost WBA65 expanded assumption", errors)
    require(
        assumptions.get("target_capability_profile") == rel(REPO_ROOT / DEFAULT_FIXTURE),
        "WBA scaffold missing target capability profile source",
        errors,
    )
    invariants = scaffold.get("portable_invariants", {})
    require(
        "verify_expression_target_capabilities.py" in str(invariants.get("target_capability_profile", "")),
        "WBA scaffold missing target capability invariant",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(SCREEN_DOC, errors).split()).lower()
    wba_rules = " ".join(read(WBA_RULES, errors).split()).lower()
    readme = " ".join(read(README, errors).split()).lower()
    for token in [
        "target capability profile",
        "companion-screen-target-capabilities.json",
        "verify_expression_target_capabilities.py",
        "wba55-safe",
        "wba65 may add target-specific resources only behind capability flags",
    ]:
        require(token in screen_doc, f"screen doc missing target capability anchor {token}", errors)
    for token in [
        "target capability profile",
        "companion-screen-target-capabilities.json",
        "verify_expression_target_capabilities.py",
        "wba55-safe",
        "wba65 may add target-specific resources only behind capability flags",
    ]:
        require(token in wba_rules, f"WBA rules missing target capability anchor {token}", errors)
    for token in [
        "target capability profile",
        "verify_expression_target_capabilities.py",
    ]:
        require(token in readme, f"e-paper README missing target capability anchor {token}", errors)


def check_third_party_clean(errors: list[str]) -> None:
    changed_wb = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB").strip()
    changed_wba = git_output("diff", "--name-only", "--", "third_party/STM32CubeWBA").strip()
    require(not changed_wb, f"third_party/STM32CubeWB modified: {changed_wb}", errors)
    require(not changed_wba, f"third_party/STM32CubeWBA modified: {changed_wba}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected target capability schema", errors)
    require(data.get("status") == "PASS", "target capability fixture must be PASS", errors)
    targets = data.get("target_profiles", {})
    require(targets.get("WB55_DEVBOARD", {}).get("role") == "current_validation_target", "fixture missing WB55 validation target", errors)
    require(targets.get("WBA55", {}).get("role") == "baseline_constrained_target", "fixture missing WBA55 baseline role", errors)
    require(targets.get("WBA65", {}).get("role") == "expanded_target", "fixture missing WBA65 expanded role", errors)
    require(
        "capability flags" in str(targets.get("WBA65", {}).get("platform_scope", "")),
        "fixture must gate WBA65 expansion behind capability flags",
        errors,
    )
    limits = data.get("shared_screen_limits", {})
    require(limits.get("display_queue_depth") == 4, "fixture queue depth drifted", errors)
    require(limits.get("display_payload_max_bytes") == 236, "fixture payload bound drifted", errors)
    require(limits.get("panel_callback") == "comp_epaper_panel_refresh_fn_t", "fixture missing panel callback boundary", errors)
    require("screen_expression_status" in limits.get("real_ble_operations", []), "fixture missing real BLE expression status operation", errors)
    require("e_paper.runtime_snapshot" == limits.get("runtime_snapshot_event"), "fixture missing runtime snapshot event", errors)
    rules = " ".join(data.get("wba_expansion_rules", [])).lower()
    for token in [
        "wba55 is the safe baseline",
        "wba65 may add target-specific resources only behind explicit capability flags",
        "wba55-safe fallback",
        "separate cubewba project",
        "portable screen files",
    ]:
        require(token in rules, f"fixture missing expansion rule {token}", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "wb55_profile_is_current_validation_target",
        "wba55_is_conservative_baseline",
        "wba65_is_expanded_only_with_capability_flags",
        "shared_limits_match_portable_headers",
        "wba_contract_reuses_target_capability_profile",
        "wba_scaffold_carries_target_capability_profile",
        "third_party_cube_repos_remain_clean",
    ]:
        require(acceptance.get(token) is True, f"fixture acceptance missing {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing target capability fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update deterministic target capability fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_source_limits(errors)
    check_wb55_boundary(errors)
    if not args.write_fixture:
        check_wba_contracts(errors)
    check_docs(errors)
    check_third_party_clean(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion target capability profile checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion target capability profile verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
