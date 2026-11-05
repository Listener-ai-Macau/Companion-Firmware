#!/usr/bin/env python3
"""Capture durable current-source WB55 build evidence without touching hardware."""

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
DEFAULT_RECEIPT = ROOT / "docs/validation/companion-wb55-current-build-receipt-20260717.json"
BUILD_SCRIPT = ROOT / "tools/build_nucleo_bringup.ps1"
SOURCE_PATHS = (
    "app/companion_pendant",
    "cubeide/Companion_Nucleo_WB55RG_Bringup",
    "tools/build_nucleo_bringup.ps1",
)
VARIANTS = (
    ("dry_run_default", ("-Force",)),
    ("ssd1681_real_panel", ("-EpaperSsd1681Bringup", "-Force")),
    ("screen_asset_provision", ("-ScreenAssetProvision", "-Force")),
)
SIZE_PATTERN = re.compile(
    r"(?m)^\s*(?P<text>\d+)\s+(?P<data>\d+)\s+(?P<bss>\d+)\s+"
    r"(?P<dec>\d+)\s+(?P<hex>[0-9a-fA-F]+)\s+"
    r"(?P<elf>\S+\.elf)\s*$"
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
        raise RuntimeError("refuse build receipt from a dirty worktree:\n" + dirty)


def parse_size(output: str) -> dict[str, Any] | None:
    matches = list(SIZE_PATTERN.finditer(output))
    if not matches:
        return None
    match = matches[-1]
    return {
        "text": int(match.group("text")),
        "data": int(match.group("data")),
        "bss": int(match.group("bss")),
        "dec": int(match.group("dec")),
        "hex": match.group("hex").lower(),
        "elf": match.group("elf").replace("\\", "/"),
    }


def output_tail(output: str) -> list[str]:
    lines = [line for line in output.replace("\r\n", "\n").split("\n") if line]
    interesting = [
        line
        for line in lines
        if "build_nucleo_bringup:" in line
        or "arm-none-eabi-size" in line
        or line.strip().startswith("text")
        or SIZE_PATTERN.fullmatch(line) is not None
        or line.startswith("make: Leaving directory")
    ]
    return interesting[-8:]


def capture_variant(name: str, args: tuple[str, ...]) -> dict[str, Any]:
    command = ["pwsh", "-NoProfile", "-File", rel(BUILD_SCRIPT), *args]
    completed = run(command)
    output = completed.stdout
    size = parse_size(output)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} build failed ({completed.returncode}):\n{output_tail(output)}")
    if size is None:
        raise RuntimeError(f"{name} build emitted no arm-none-eabi-size result")
    if "released build lock" not in output:
        raise RuntimeError(f"{name} build did not release the bounded build lock")
    return {
        "command": command,
        "returncode": completed.returncode,
        "size": size,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest().upper(),
        "output_tail": output_tail(output),
    }


def receipt() -> dict[str, Any]:
    require_clean_tree()
    source_commit = git_output("rev-parse", "HEAD")
    variants = {name: capture_variant(name, args) for name, args in VARIANTS}
    return {
        "schema": "companion.wb55_current_build_receipt.v1",
        "status": "PASS_CURRENT_SOURCE_BUILD_NO_HARDWARE",
        "source_commit": source_commit,
        "source_paths": list(SOURCE_PATHS),
        "hardware_boundary": "No flash, serial port, lock, panel command or physical claim; this is a build-only receipt.",
        "variants": variants,
    }


def verify_current_source(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "companion.wb55_current_build_receipt.v1":
        errors.append("unexpected receipt schema")
    if data.get("status") != "PASS_CURRENT_SOURCE_BUILD_NO_HARDWARE":
        errors.append("receipt is not a current-source build PASS")
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        errors.append("receipt has no full source commit")
        return errors
    if run(["git", "cat-file", "-e", f"{source_commit}^{{commit}}"]).returncode != 0:
        errors.append("receipt source commit is no longer available")
        return errors
    changed = git_output("diff", "--name-only", source_commit, "HEAD", "--", *SOURCE_PATHS)
    if changed:
        errors.append("WB55 build inputs changed after receipt:\n" + changed)
    if data.get("source_paths") != list(SOURCE_PATHS):
        errors.append("receipt source-path boundary drifted")
    for name, args in VARIANTS:
        variant = data.get("variants", {}).get(name, {})
        expected_command = ["pwsh", "-NoProfile", "-File", rel(BUILD_SCRIPT), *args]
        if variant.get("command") != expected_command:
            errors.append(f"{name} build command drifted")
        if variant.get("returncode") != 0:
            errors.append(f"{name} did not exit successfully")
        size = variant.get("size", {})
        if not all(isinstance(size.get(key), int) for key in ("text", "data", "bss", "dec")):
            errors.append(f"{name} has no complete size result")
        if not isinstance(size.get("hex"), str) or not isinstance(size.get("elf"), str):
            errors.append(f"{name} has no ELF identity")
        if not re.fullmatch(r"[0-9A-F]{64}", str(variant.get("output_sha256", ""))):
            errors.append(f"{name} has no complete output digest")
        if not any("released build lock" in line for line in variant.get("output_tail", [])):
            errors.append(f"{name} output tail misses build-lock release")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="run all builds and write the receipt")
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
        print(f"PASS: captured current WB55 build receipt -> {rel(receipt_path)}")
        return 0

    if not receipt_path.exists():
        print(f"FAIL: missing receipt {rel(receipt_path)}", file=sys.stderr)
        return 1
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
        errors = verify_current_source(data)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("FAIL: WB55 current build receipt verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 current build receipt remains valid -> {rel(receipt_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
