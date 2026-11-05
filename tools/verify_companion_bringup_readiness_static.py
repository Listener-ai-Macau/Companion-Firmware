#!/usr/bin/env python3
"""Verify the Companion bring-up readiness static-only contract."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-bringup-readiness-static-contract.json")
SCHEMA_ID = "companion.bringup_readiness_static_contract.v1"
READINESS = REPO_ROOT / "tools" / "verify_companion_bringup_readiness.ps1"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
WORKSPACE_POLICY = REPO_ROOT / "tools" / "verify_workspace_submodule_policy.py"
DEVBOARD_IOC = REPO_ROOT / "tools" / "verify_devboard_ioc_import.py"
SCREEN_RUNNER = REPO_ROOT / "tools" / "run_expression_acceptance.py"


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


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Static contract for the no-package Companion bring-up readiness mode that now gates workspace, IOC, and screen-expression software checks before hardware.",
        "sources": {
            "readiness_script": rel(READINESS),
            "bringup_steps": rel(BRINGUP_STEPS),
            "workspace_policy": rel(WORKSPACE_POLICY),
            "devboard_ioc_import": rel(DEVBOARD_IOC),
            "screen_acceptance_runner": rel(SCREEN_RUNNER),
            "verifier": "tools/verify_companion_bringup_readiness_static.py",
        },
        "static_only_contract": {
            "mode": "static-only",
            "package_path": "<static-only-no-package>",
            "rejects_full_mode_combo": True,
            "rejects_type_harness_combo": True,
            "rejects_package_path_combo": True,
            "skips_package_and_hardware_dry_runs": True,
            "emits_no_manual_gates": True,
        },
        "required_static_steps": [
            "Companion build environment check",
            "Companion workspace submodule policy",
            "Companion devboard IOC import",
            "verify Companion OTA static contract",
            "Companion BLE probe self-test",
            "Companion recording cache model",
            "Companion recording FSM static",
            "Companion diagnostics static",
            "Companion screen software acceptance",
            "Companion git diff check",
        ],
        "screen_acceptance_output": ".cache/validation/companion-bringup-readiness-<timestamp>/companion-screen-acceptance-run.json",
        "validation_commands": [
            "python .\\tools\\verify_companion_bringup_readiness_static.py",
            "pwsh -NoProfile -File .\\tools\\verify_companion_bringup_readiness.ps1 -StaticOnly",
        ],
    }


def check_script(errors: list[str]) -> None:
    text = read(READINESS, errors)
    for token in [
        "[switch] $StaticOnly",
        "-StaticOnly cannot be combined with -Full",
        "-StaticOnly cannot be combined with -IncludeTypeHarness",
        "-StaticOnly does not consume -PackagePath",
        '$resolvedPackagePath = if ($StaticOnly) { "<static-only-no-package>" } else { Resolve-CompanionPackage -Path $PackagePath }',
        'Invoke-ReadinessStep -Name "Companion workspace submodule policy"',
        'Invoke-ReadinessStep -Name "Companion devboard IOC import"',
        'Invoke-ReadinessStep -Name "Companion screen software acceptance"',
        'if (-not $StaticOnly) {',
        'mode = if ($StaticOnly) { "static-only" }',
        "<static-only-no-hardware-command>",
        "<static-only-no-manual-evidence-command>",
        "Static-only mode skips package, OTA dry-run, wired flash dry-run, and hardware manual-gate emission",
    ]:
        require(token in text, f"readiness script missing static-only anchor {token}", errors)


def check_docs(errors: list[str]) -> None:
    text = read(BRINGUP_STEPS, errors)
    for token in [
        "verify_companion_bringup_readiness.ps1 -StaticOnly",
        "skips package, OTA dry-run, wired flash dry-run, and manual-gate emission",
        "workspace submodule policy",
        "devboard IOC import",
        "screen-expression software acceptance",
    ]:
        require(token in text, f"bringup steps missing static-only anchor {token}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected bring-up readiness static fixture schema", errors)
    require(data.get("status") == "PASS", "bring-up readiness static fixture must be PASS", errors)
    contract = data.get("static_only_contract", {})
    for key in [
        "rejects_full_mode_combo",
        "rejects_type_harness_combo",
        "rejects_package_path_combo",
        "skips_package_and_hardware_dry_runs",
        "emits_no_manual_gates",
    ]:
        require(contract.get(key) is True, f"static-only contract missing {key}", errors)
    require(contract.get("mode") == "static-only", "static-only contract mode drifted", errors)
    require(contract.get("package_path") == "<static-only-no-package>", "static-only package sentinel drifted", errors)
    for step in build_fixture()["required_static_steps"]:
        require(step in data.get("required_static_steps", []), f"static-only fixture missing step {step}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing bring-up readiness static fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic static contract fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [READINESS, BRINGUP_STEPS, WORKSPACE_POLICY, DEVBOARD_IOC, SCREEN_RUNNER]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture() if not errors else {}
    if expected:
        check_fixture_data(expected, errors)
    check_script(errors)
    check_docs(errors)

    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion bring-up readiness static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion bring-up readiness static contract verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
