#!/usr/bin/env python3
"""Verify workspace settings for the STM32CubeWB nested submodule warning."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-workspace-submodule-policy.json")
SCHEMA_ID = "companion.workspace.submodule_policy.v1"
ROOT_GITMODULES = REPO_ROOT / ".gitmodules"
CUBEWB_GITMODULES = REPO_ROOT / "third_party" / "STM32CubeWB" / ".gitmodules"
VSCODE_SETTINGS = REPO_ROOT / ".vscode" / "settings.json"
WORKFLOW_DOC = REPO_ROOT / "docs" / "codex_development_workflow.md"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
EXPECTED_ROOT_SUBMODULES = [
    "third_party/STM32CubeWB",
    "third_party/denzic-platform",
]


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


def parse_submodules(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        header = re.match(r'\[submodule "(.+)"\]', line)
        if header:
            if current is not None:
                entries.append(current)
            current = {"name": header.group(1)}
            continue
        if current is None or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        current[key] = value
    if current is not None:
        entries.append(current)
    return entries


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


def load_settings(errors: list[str]) -> dict[str, Any]:
    text = read(VSCODE_SETTINGS, errors)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{rel(VSCODE_SETTINGS)} is not valid JSON: {exc}")
        return {}
    require(isinstance(data, dict), ".vscode/settings.json must contain an object", errors)
    return data if isinstance(data, dict) else {}


def build_fixture() -> dict[str, Any]:
    root_submodules = parse_submodules(ROOT_GITMODULES.read_text(encoding="utf-8"))
    cubewb_submodules = parse_submodules(CUBEWB_GITMODULES.read_text(encoding="utf-8"))
    settings = json.loads(VSCODE_SETTINGS.read_text(encoding="utf-8"))
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Keep VS Code from warning that STM32CubeWB's nested submodules will not open automatically, while preserving third_party as read-only reference code.",
        "sources": {
            "workspace_settings": rel(VSCODE_SETTINGS),
            "root_gitmodules": rel(ROOT_GITMODULES),
            "stm32cubewb_gitmodules": rel(CUBEWB_GITMODULES),
            "workflow_doc": rel(WORKFLOW_DOC),
            "bringup_steps": rel(BRINGUP_STEPS),
            "verifier": "tools/verify_workspace_submodule_policy.py",
        },
        "root_submodules": [entry.get("path", "") for entry in root_submodules],
        "stm32cubewb_nested_submodule_count": len(cubewb_submodules),
        "stm32cubewb_nested_submodule_paths": [entry.get("path", "") for entry in cubewb_submodules],
        "vscode_settings": {
            "git.detectSubmodules": settings.get("git.detectSubmodules"),
            "git.detectSubmodulesLimit": settings.get("git.detectSubmodulesLimit"),
        },
        "policy": [
            "Raise git.detectSubmodulesLimit above STM32CubeWB's nested submodule count so VS Code can open them without the default warning.",
            "Treat third_party/STM32CubeWB and third_party/STM32CubeWBA as read-only upstream references.",
            "Treat third_party/denzic-platform as the pinned shared Denzic platform/OTA contract submodule, not as an ST Cube package.",
            "Make Companion changes in local wrappers, board adapters, tools, docs, or generated CubeMX output instead of editing upstream packages.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_workspace_submodule_policy.py",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ],
    }


def check_settings(settings: dict[str, Any], nested_count: int, errors: list[str]) -> None:
    require(settings.get("git.detectSubmodules") is True, ".vscode/settings.json must enable git.detectSubmodules", errors)
    limit = settings.get("git.detectSubmodulesLimit")
    require(isinstance(limit, int), ".vscode/settings.json must set integer git.detectSubmodulesLimit", errors)
    if isinstance(limit, int):
        require(
            limit >= nested_count,
            f"git.detectSubmodulesLimit must be at least STM32CubeWB nested count {nested_count}",
            errors,
        )


def check_docs(errors: list[str]) -> None:
    workflow = read(WORKFLOW_DOC, errors)
    bringup = read(BRINGUP_STEPS, errors)
    for token in [
        ".vscode/settings.json",
        "git.detectSubmodulesLimit",
        "13 nested STM32CubeWB submodules",
        "verify_workspace_submodule_policy.py",
    ]:
        require(token in workflow, f"workflow doc missing workspace submodule anchor {token}", errors)
    for token in [
        ".vscode/settings.json",
        "git.detectSubmodulesLimit",
        "verify_workspace_submodule_policy.py",
        "third_party/STM32CubeWB",
    ]:
        require(token in bringup, f"bringup steps missing workspace submodule anchor {token}", errors)


def check_fixture_data(data: dict[str, Any], nested_count: int, errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected workspace submodule policy schema", errors)
    require(data.get("status") == "PASS", "workspace submodule policy fixture must be PASS", errors)
    require(data.get("root_submodules") == EXPECTED_ROOT_SUBMODULES, "root submodule policy drifted", errors)
    require(
        data.get("stm32cubewb_nested_submodule_count") == nested_count,
        "STM32CubeWB nested submodule count drifted",
        errors,
    )
    settings = data.get("vscode_settings", {})
    require(settings.get("git.detectSubmodules") is True, "fixture must enable git.detectSubmodules", errors)
    require(
        isinstance(settings.get("git.detectSubmodulesLimit"), int)
        and settings.get("git.detectSubmodulesLimit") >= nested_count,
        "fixture git.detectSubmodulesLimit must cover nested submodules",
        errors,
    )
    text = json.dumps(data, sort_keys=True)
    for token in ["STM32CubeWB", "STM32CubeWBA", "denzic-platform", "read-only upstream references", "git.detectSubmodulesLimit"]:
        require(token in text, f"workspace submodule policy fixture missing {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], nested_count: int, errors: list[str]) -> None:
    require(path.exists(), f"missing workspace submodule policy fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, nested_count, errors)


def check_third_party_clean(errors: list[str]) -> None:
    changed = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB", "third_party/STM32CubeWBA").strip()
    require(not changed, f"third_party STM32Cube packages modified: {changed}", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic workspace policy fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [ROOT_GITMODULES, CUBEWB_GITMODULES, VSCODE_SETTINGS, WORKFLOW_DOC, BRINGUP_STEPS]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if errors:
        expected: dict[str, Any] = {}
        nested_count = 0
    else:
        nested_count = len(parse_submodules(CUBEWB_GITMODULES.read_text(encoding="utf-8")))
        settings = load_settings(errors)
        check_settings(settings, nested_count, errors)
        check_docs(errors)
        check_third_party_clean(errors)
        expected = build_fixture() if not errors else {}
        if expected:
            check_fixture_data(expected, nested_count, errors)

    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, nested_count, errors)

    if errors:
        print("FAIL: Companion workspace submodule policy checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion workspace submodule policy verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
