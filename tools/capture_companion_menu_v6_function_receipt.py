#!/usr/bin/env python3
"""Capture current-source four-root menu host evidence without visual activation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "docs/validation/companion-menu-v6-function-receipt-20260717.json"
MENU_ROOT = ROOT / "app/companion_pendant/epaper"
SOURCE_REVIEW = ROOT / "docs/validation/companion-menu-v6-source-review-20260717.json"
LOCALIZATION_PREVIEW = ROOT / "docs/validation/companion-menu-v6-localization-preview-20260717.json"
SOURCE_REQUEST = ROOT / "docs/art/iterations/companion-menu-v6-four-root/generation-request.json"
MENU_SHA256 = "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"
SOURCE_PATHS = (
    "app/companion_pendant/epaper/menu_v5_contract.c",
    "app/companion_pendant/epaper/menu_v5_contract.h",
    "app/companion_pendant/epaper/menu_v5_localization.c",
    "app/companion_pendant/epaper/menu_v5_localization.h",
    "app/companion_pendant/epaper/menu_v5_action_journey.c",
    "app/companion_pendant/epaper/menu_v5_action_journey.h",
    "app/companion_pendant/epaper/menu_v5_navigation.c",
    "app/companion_pendant/epaper/menu_v5_navigation.h",
    "app/companion_pendant/epaper/menu_v5_target_bridge.c",
    "app/companion_pendant/epaper/menu_v5_target_bridge.h",
    "app/companion_pendant/epaper/menu_v5_view_model.c",
    "app/companion_pendant/epaper/menu_v5_view_model.h",
    "app/companion_pendant/epaper/tests",
    "tools/test_menu_v5_contract_host.ps1",
    "tools/test_menu_v5_action_journey_host.ps1",
    "tools/test_menu_v5_navigation_host.ps1",
    "tools/test_menu_v5_target_bridge_host.ps1",
    "tools/test_menu_v5_view_model_host.ps1",
    "docs/art/iterations/companion-menu-v6-four-root",
    "docs/validation/companion-menu-v6-source-review-20260717.json",
    "docs/validation/companion-menu-v6-localization-preview-20260717.json",
)
TESTS = (
    ("contract", "tools/test_menu_v5_contract_host.ps1", "PASS: menu-v5 keeps four roots"),
    ("action_journey", "tools/test_menu_v5_action_journey_host.ps1", "PASS: menu-v5 selection routes"),
    ("navigation", "tools/test_menu_v5_navigation_host.ps1", "PASS: menu-v5 navigation keeps four roots"),
    ("target_bridge", "tools/test_menu_v5_target_bridge_host.ps1", "PASS: target bridge keeps the four-root UI contract"),
    ("view_model", "tools/test_menu_v5_view_model_host.ps1", "PASS: menu-v5 view model keeps four-root geometry"),
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def git_output(*args: str) -> str:
    completed = run(["git", *args])
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def require_clean_tree() -> None:
    dirty = git_output("status", "--short")
    if dirty:
        raise RuntimeError("refuse menu receipt from a dirty worktree:\n" + dirty)


def tail(output: str) -> list[str]:
    lines = [line for line in output.replace("\r\n", "\n").split("\n") if line]
    return lines[-12:]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_visual_source() -> dict[str, Any]:
    request = load_json(SOURCE_REQUEST)
    source_review = load_json(SOURCE_REVIEW)
    localization_preview = load_json(LOCALIZATION_PREVIEW)
    errors: list[str] = []
    if request.get("generated_output", {}).get("sha256") != MENU_SHA256:
        errors.append("generation request menu source hash drifted")
    if request.get("machine_review", {}).get("decision") != "PENDING_OWNER_VISUAL_DECISION":
        errors.append("menu generation request is not pending owner visual decision")
    if source_review.get("status") != "PASS_MACHINE_PREVIEW_PENDING_OWNER":
        errors.append("menu source review is not pending-owner PASS")
    if source_review.get("source", {}).get("sha256") != MENU_SHA256:
        errors.append("menu source-review hash drifted")
    if localization_preview.get("status") != "PASS_MACHINE_LOCALIZATION_PREVIEW_PENDING_OWNER":
        errors.append("menu localization preview is not pending-owner PASS")
    if localization_preview.get("source", {}).get("sha256") != MENU_SHA256:
        errors.append("menu localization preview hash drifted")
    for boundary in (
        source_review.get("runtime_boundary", {}),
        localization_preview.get("runtime_boundary", {}),
    ):
        for key in ("pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass"):
            if boundary.get(key) is not False:
                errors.append(f"menu visual boundary drifted: {key}")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {
        "source": request.get("generated_output", {}).get("path"),
        "source_sha256": MENU_SHA256,
        "owner_visual_decision": "PENDING_OWNER_VISUAL_DECISION",
        "source_review": rel(SOURCE_REVIEW),
        "localization_preview": rel(LOCALIZATION_PREVIEW),
        "runtime_activation": False,
        "actual_text_owner": "menu_v5_localization",
    }


def capture_test(name: str, script: str, expected: str) -> dict[str, Any]:
    command = ["pwsh", "-NoProfile", "-File", script]
    completed = run(command)
    output = completed.stdout
    if completed.returncode != 0:
        raise RuntimeError(f"menu {name} host test failed ({completed.returncode}):\n{tail(output)}")
    if expected not in output:
        raise RuntimeError(f"menu {name} host test output missed its success marker")
    return {
        "command": command,
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest().upper(),
        "output_tail": tail(output),
    }


def receipt() -> dict[str, Any]:
    require_clean_tree()
    source_commit = git_output("rev-parse", "HEAD")
    visual_source = verify_visual_source()
    results = {name: capture_test(name, script, expected) for name, script, expected in TESTS}
    return {
        "schema": "companion.menu_v6_function_receipt.v1",
        "status": "PASS_CURRENT_SOURCE_MENU_FUNCTION_PENDING_OWNER_VISUAL",
        "source_commit": source_commit,
        "source_paths": list(SOURCE_PATHS),
        "function_contract": {
            "roots": ["Voice", "Device", "Connection", "Preferences"],
            "root_count": 4,
            "language_support": ["en", "zh_cn"],
            "daily_recording_control": "double_tap_only; Voice reports truthful live state and never presents a Record action",
            "row_truth": "every detail row is an action, live datum, planned or deferred state",
        },
        "visual_source": visual_source,
        "hardware_boundary": "No PBM/CEMP import, external Flash provision, firmware flash, panel command or visual PASS; this is host-only evidence.",
        "host_tests": results,
    }


def verify_current_source(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "companion.menu_v6_function_receipt.v1":
        errors.append("unexpected receipt schema")
    if data.get("status") != "PASS_CURRENT_SOURCE_MENU_FUNCTION_PENDING_OWNER_VISUAL":
        errors.append("receipt is not a current-source menu PASS")
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        errors.append("receipt has no full source commit")
        return errors
    if run(["git", "cat-file", "-e", f"{source_commit}^{{commit}}"]).returncode != 0:
        errors.append("receipt source commit is no longer available")
        return errors
    changed = git_output("diff", "--name-only", source_commit, "HEAD", "--", *SOURCE_PATHS)
    if changed:
        errors.append("menu function inputs changed after receipt:\n" + changed)
    if data.get("source_paths") != list(SOURCE_PATHS):
        errors.append("receipt source-path boundary drifted")
    visual = data.get("visual_source", {})
    if visual.get("source_sha256") != MENU_SHA256 or visual.get("owner_visual_decision") != "PENDING_OWNER_VISUAL_DECISION":
        errors.append("receipt visual-source identity drifted")
    if visual.get("runtime_activation") is not False:
        errors.append("receipt permits menu runtime activation")
    contract = data.get("function_contract", {})
    if contract.get("roots") != ["Voice", "Device", "Connection", "Preferences"]:
        errors.append("receipt root order drifted")
    if contract.get("language_support") != ["en", "zh_cn"]:
        errors.append("receipt language support drifted")
    for name, script, _ in TESTS:
        item = data.get("host_tests", {}).get(name, {})
        if item.get("command") != ["pwsh", "-NoProfile", "-File", script] or item.get("returncode") != 0:
            errors.append(f"receipt host test drifted: {name}")
        if not re.fullmatch(r"[0-9A-F]{64}", str(item.get("output_sha256", ""))):
            errors.append(f"receipt host test has no output digest: {name}")
        if not item.get("output_tail"):
            errors.append(f"receipt host test has no output tail: {name}")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="run host tests and write the receipt")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args(argv)
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt

    if args.write:
        try:
            data = receipt()
        except RuntimeError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"PASS: captured current four-root menu function receipt -> {rel(receipt_path)}")
        return 0

    if not receipt_path.exists():
        print(f"FAIL: missing receipt {rel(receipt_path)}", file=sys.stderr)
        return 1
    try:
        errors = verify_current_source(load_json(receipt_path))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("FAIL: four-root menu function receipt verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: four-root menu function receipt remains valid -> {rel(receipt_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
