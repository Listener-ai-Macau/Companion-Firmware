#!/usr/bin/env python3
"""Verify WB55 active-resource flash preflight paths for normal/provision images."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
FLASH_SCRIPT = ROOT / "tools/flash_nucleo_bringup.ps1"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-runtime-flash-preflight.json"
SCHEMA_ID = "companion.screen.wb55_runtime_flash_preflight.v1"
CANDIDATE = current_candidate()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run_preflight(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(FLASH_SCRIPT), *args, "-CheckOnly"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    parsed: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if not line.startswith("CHECK: ") or "=" not in line:
            continue
        key, value = line[len("CHECK: ") :].split("=", 1)
        parsed[key.strip()] = value.strip()
    image = pathlib.Path(parsed.get("image", ""))
    programmer = pathlib.Path(parsed.get("programmer", ""))
    return {
        "command": " ".join(["pwsh", "-NoProfile", "-File", ".\\tools\\flash_nucleo_bringup.ps1", *args, "-CheckOnly"]),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "mode": parsed.get("mode"),
        "image": rel(image) if image.is_absolute() else parsed.get("image", ""),
        "image_exists": image.exists() if parsed.get("image") else False,
        "programmer": str(programmer),
        "programmer_exists": programmer.exists() if parsed.get("programmer") else False,
        "flash_timeout_seconds": int(parsed.get("flash_timeout_seconds", "0") or "0"),
    }


def build_fixture() -> dict[str, Any]:
    normal = run_preflight([])
    provision = run_preflight(["-ScreenAssetProvision"])
    flash_script = FLASH_SCRIPT.read_text(encoding="utf-8")
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS" if all(
            item.get("returncode") == 0
            and item.get("image_exists") is True
            and item.get("programmer_exists") is True
            for item in (normal, provision)
        ) else "FAIL",
        "purpose": f"Machine preflight for rev{CANDIDATE.revision} runtime recheck flashing; does not flash hardware.",
        "script": rel(FLASH_SCRIPT),
        "normal": normal,
        "screen_asset_provision": provision,
        "flash_timeout_contract": {
            "timeout_parameter": "[int]$FlashTimeoutSeconds = 120" in flash_script,
            "bounded_range": "[ValidateRange(30, 600)]" in flash_script,
            "start_process": "Start-Process" in flash_script,
            "wait_for_exit": "$process.WaitForExit($TimeoutSeconds * 1000)" in flash_script,
            "kills_on_timeout": "Stop-Process -Id $process.Id -Force" in flash_script,
            "timeout_error": "flash timed out after $TimeoutSeconds second(s)" in flash_script,
            "captures_stdout": "RedirectStandardOutput" in flash_script and "stm32-programmer-$stamp-$PID.stdout.log" in flash_script,
            "captures_stderr": "RedirectStandardError" in flash_script and "stm32-programmer-$stamp-$PID.stderr.log" in flash_script,
            "hidden_window": "-WindowStyle Hidden" in flash_script,
        },
        "expected_sequence": ["screen_asset_provision", "normal"],
        "safety_rules": [
            "CheckOnly only validates image/programmer paths.",
            "Real flashing is bounded by FlashTimeoutSeconds and writes stdout/stderr logs.",
            f"Provision image must run before normal image during rev{CANDIDATE.revision} runtime recheck.",
            "Normal firmware must be restored after provision.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
            "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -CheckOnly",
            "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -ScreenAssetProvision -CheckOnly",
        ],
    }


def verify(data: dict[str, Any], expected: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if data.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if data.get("status") != "PASS":
        errors.append("flash preflight status must be PASS")
    normal = data.get("normal", {})
    provision = data.get("screen_asset_provision", {})
    if normal.get("mode") != "normal":
        errors.append("normal preflight mode drifted")
    if provision.get("mode") != "screen_asset_provision":
        errors.append("provision preflight mode drifted")
    for name, item in (("normal", normal), ("screen_asset_provision", provision)):
        if item.get("returncode") != 0:
            errors.append(f"{name} preflight returned non-zero")
        if item.get("image_exists") is not True:
            errors.append(f"{name} preflight image missing")
        if item.get("programmer_exists") is not True:
            errors.append(f"{name} preflight programmer missing")
        if "STM32_Programmer_CLI.exe" not in str(item.get("programmer", "")):
            errors.append(f"{name} preflight programmer path drifted")
        if item.get("flash_timeout_seconds") != 120:
            errors.append(f"{name} preflight flash timeout must default to 120 seconds")
    if "Companion_Nucleo_WB55RG_Bringup.hex" not in str(normal.get("image", "")):
        errors.append("normal preflight image drifted")
    if "Companion_Nucleo_WB55RG_ScreenAssetProvision.hex" not in str(provision.get("image", "")):
        errors.append("provision preflight image drifted")
    serialized = json.dumps(data, ensure_ascii=False)
    for key, value in data.get("flash_timeout_contract", {}).items():
        if value is not True:
            errors.append(f"flash timeout contract {key} must be true")
    for token in (
        "screen_asset_provision",
        "normal",
        "CheckOnly",
        "FlashTimeoutSeconds",
        "Real flashing is bounded by FlashTimeoutSeconds",
        "Provision image must run before normal image",
        "Normal firmware must be restored after provision",
    ):
        if token not in serialized:
            errors.append(f"flash preflight missing token {token}")
    if expected is not None and data != expected:
        errors.append("flash preflight fixture is stale; rerun with --write")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    fixture = build_fixture()
    errors = verify(fixture)
    if args.write and not errors:
        json_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.write:
        if not json_path.exists():
            errors.append(f"missing {rel(json_path)}")
        else:
            actual = json.loads(json_path.read_text(encoding="utf-8"))
            errors.extend(verify(actual, fixture))
    if errors:
        print("FAIL: WB55 runtime flash preflight failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 runtime flash preflight verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
