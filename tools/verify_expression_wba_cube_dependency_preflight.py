#!/usr/bin/env python3
"""Verify the STM32WBA upstream dependency state before a real WBA port starts."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-wba-cube-dependency-preflight.json")
SCHEMA_ID = "companion.pendant.screen_wba_cube_dependency_preflight.v1"

THIRD_PARTY_WB = REPO_ROOT / "third_party" / "STM32CubeWB"
THIRD_PARTY_WBA = REPO_ROOT / "third_party" / "STM32CubeWBA"
ROOT_GITMODULES = REPO_ROOT / ".gitmodules"
WORKSPACE_POLICY = REPO_ROOT / "docs" / "validation" / "companion-workspace-submodule-policy.json"
WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-port-contract.json"
WBA55_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

ST_SOURCES = {
    "stm32wba_series": "https://www.st.com/en/microcontrollers-microprocessors/stm32wba-series.html",
    "stm32cubewba": "https://www.st.com/en/embedded-software/stm32cubewba.html",
    "wba_ble_build_project": "https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32WBA_Build_BLE_Project",
    "wba_ble_cubemx_server": "https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32WBA_BLE_STM32CubeMX",
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


def local_wba_mode() -> str:
    if THIRD_PARTY_WBA.exists():
        return "local_reference_available"
    return "missing_upstream_reference"


def root_gitmodules_mentions_wba() -> bool:
    if not ROOT_GITMODULES.exists():
        return False
    return "STM32CubeWBA" in ROOT_GITMODULES.read_text(encoding="utf-8")


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Make the current STM32WBA upstream dependency state explicit before "
            "a real WBA55/WBA65 CubeWBA project or build wrapper is claimed."
        ),
        "sources": {
            "root_gitmodules": rel(ROOT_GITMODULES),
            "workspace_submodule_policy": rel(WORKSPACE_POLICY),
            "wba_port_contract": rel(WBA_CONTRACT),
            "wba55_port_scaffold": rel(WBA55_SCAFFOLD),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
            **ST_SOURCES,
        },
        "local_state": {
            "stm32cubewb_path": rel(THIRD_PARTY_WB),
            "stm32cubewb_present": THIRD_PARTY_WB.exists(),
            "stm32cubewba_path": rel(THIRD_PARTY_WBA),
            "stm32cubewba_present": THIRD_PARTY_WBA.exists(),
            "root_gitmodules_mentions_stm32cubewba": root_gitmodules_mentions_wba(),
            "mode": local_wba_mode(),
        },
        "contract": {
            "wba_parity_claim_allowed": False,
            "wba_port_status_until_dependency_lands": "DRAFT_PRE_PORT",
            "do_not_retarget_wb55_cube_project": True,
            "do_not_edit_third_party_packages": True,
            "cube_wba_dependency_required_before_build_wrapper": True,
            "official_starting_points": [
                "STM32CubeWBA package",
                "STM32WBA BLE example project build flow",
                "STM32CubeMX WBA BLE server generation flow",
            ],
        },
        "required_before_wba_parity": [
            "Local STM32CubeWBA upstream reference or documented CubeWBA package source.",
            "Separate CubeWBA IOC/project for WBA55 or WBA65.",
            "Scriptable WBA build wrapper.",
            "WBA BLE/GATT adapter wired behind screen_gatt_stm32wba.",
            "WBA scheduler/timer hook wired behind screen_scheduler_stm32wba.",
            "Target-named WBA panel transport and filled panel evidence record.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py",
            "python .\\tools\\verify_workspace_submodule_policy.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ],
    }


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WBA Cube dependency preflight schema", errors)
    require(data.get("status") == "PASS", "WBA Cube dependency preflight fixture must be PASS", errors)
    sources = data.get("sources", {})
    for key, url in ST_SOURCES.items():
        require(sources.get(key) == url, f"WBA Cube dependency preflight missing official source {key}", errors)
    state = data.get("local_state", {})
    require(state.get("stm32cubewb_present") is True, "WBA preflight expects current STM32CubeWB reference to be present", errors)
    require(
        state.get("stm32cubewba_present") == THIRD_PARTY_WBA.exists(),
        "WBA preflight fixture local STM32CubeWBA presence drifted",
        errors,
    )
    require(
        state.get("root_gitmodules_mentions_stm32cubewba") == root_gitmodules_mentions_wba(),
        "WBA preflight fixture root .gitmodules WBA state drifted",
        errors,
    )
    require(state.get("mode") == local_wba_mode(), "WBA preflight fixture local mode drifted", errors)
    contract = data.get("contract", {})
    for key in [
        "do_not_retarget_wb55_cube_project",
        "do_not_edit_third_party_packages",
        "cube_wba_dependency_required_before_build_wrapper",
    ]:
        require(contract.get(key) is True, f"WBA Cube dependency contract missing {key}", errors)
    require(contract.get("wba_parity_claim_allowed") is False, "WBA parity must not be claimable from dependency preflight", errors)
    require(
        contract.get("wba_port_status_until_dependency_lands") == "DRAFT_PRE_PORT",
        "WBA port must stay DRAFT_PRE_PORT until CubeWBA dependency lands",
        errors,
    )
    serialized = json.dumps(data, sort_keys=True)
    for token in [
        "STM32CubeWBA",
        "CubeWBA IOC/project",
        "screen_gatt_stm32wba",
        "screen_scheduler_stm32wba",
        "WBA BLE/GATT adapter",
        "git diff --name-only --",
        "STM32CubeWB",
        "STM32CubeWBA",
    ]:
        require(token in serialized, f"WBA Cube dependency fixture missing {token}", errors)


def check_project_links(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    readme = read_text(README, errors)
    for text, name in [(screen_doc, "screen doc"), (wba_rules, "WBA rules"), (readme, "epaper README")]:
        for token in [
            "wba_cube_dependency_preflight",
            "WBA CubeWBA dependency preflight",
            "companion-screen-wba-cube-dependency-preflight.json",
            "verify_expression_wba_cube_dependency_preflight.py",
            "third_party/STM32CubeWBA",
            "DRAFT_PRE_PORT",
        ]:
            require(token in text, f"{name} missing WBA Cube dependency anchor {token}", errors)
    contract = read_json(WBA_CONTRACT, errors)
    scaffold = read_json(WBA55_SCAFFOLD, errors)
    for token in ["CubeWBA dependency preflight", "third_party/STM32CubeWBA", "verify_expression_wba_cube_dependency_preflight.py"]:
        require(token in json.dumps(contract, sort_keys=True), f"WBA portability contract missing {token}", errors)
    for token in ["cube_wba_dependency_preflight", "third_party/STM32CubeWBA", "DRAFT_PRE_PORT"]:
        require(token in json.dumps(scaffold, sort_keys=True), f"WBA55 port scaffold missing {token}", errors)
    if allow_stale_index:
        return
    index = read_json(REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json", errors)
    matches = [
        item
        for item in index.get("items", [])
        if isinstance(item, dict) and item.get("id") == "wba_cube_dependency_preflight"
    ]
    require(len(matches) == 1, "acceptance index must contain one wba_cube_dependency_preflight item", errors)
    if matches:
        item = matches[0]
        require(item.get("status") == "PASS", "wba_cube_dependency_preflight item must be PASS", errors)
        require(
            "docs/validation/companion-screen-wba-cube-dependency-preflight.json" in item.get("evidence_paths", []),
            "wba_cube_dependency_preflight item must link its fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py" in item.get("validation_commands", []),
            "wba_cube_dependency_preflight item must run its verifier",
            errors,
        )


def check_third_party_clean(errors: list[str]) -> None:
    changed = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB", "third_party/STM32CubeWBA").strip()
    require(not changed, f"third_party STM32Cube packages modified: {changed}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WBA Cube dependency preflight fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WBA dependency preflight fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []

    for path in [ROOT_GITMODULES, THIRD_PARTY_WB, WORKSPACE_POLICY, WBA_CONTRACT, WBA55_SCAFFOLD, SCREEN_DOC, WBA_RULES, README]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture() if not errors else {}
    if expected:
        check_fixture_data(expected, errors)
    check_project_links(errors, allow_stale_index=bool(args.write_fixture))
    check_third_party_clean(errors)

    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion WBA Cube dependency preflight checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WBA Cube dependency preflight verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
