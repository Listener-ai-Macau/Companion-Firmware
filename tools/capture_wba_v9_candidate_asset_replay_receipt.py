#!/usr/bin/env python3
"""Capture clean-tree WBA callback replay evidence for the inactive v9 CEMP."""

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
V9_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200"
PACK = V9_ROOT / "companion-v9-expression-candidate-200x200.cemp"
MANIFEST = V9_ROOT / "v9-expression-cemp-manifest.json"
HOST_TEST = ROOT / "tools/test_wba_v9_candidate_asset_mount_host.ps1"
DEFAULT_RECEIPT = ROOT / "docs/validation/companion-wba-v9-cemp-callback-replay-20260717.json"
PACK_SHA256 = "B89E6EA1D6583063969D48D28EE3D9BF444408D4347BC4974259DD75D0633F26"
SOURCE_PATHS = (
    "app/companion_pendant/epaper/asset_store.c",
    "app/companion_pendant/epaper/asset_store.h",
    "app/companion_pendant/epaper/emote_asset_pack.c",
    "app/companion_pendant/epaper/emote_asset_pack.h",
    "app/companion_pendant/epaper/emote_player.c",
    "app/companion_pendant/epaper/emote_player.h",
    "app/companion_pendant/epaper/panel_target_stm32wba.h",
    "app/companion_pendant/epaper/screen_assets_stm32wba.c",
    "app/companion_pendant/epaper/screen_assets_stm32wba.h",
    "app/companion_pendant/epaper/tests/test_wba_v9_candidate_asset_mount.c",
    "tools/test_wba_v9_candidate_asset_mount_host.ps1",
    "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/companion-v9-expression-candidate-200x200.cemp",
    "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json",
)
SUCCESS_MARKER = (
    "PASS: WBA external-NOR callback mounted v9 candidate CEMP for WBA55 and WBA65 "
    "without runtime activation."
)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def git_output(*args: str) -> str:
    result = run(["git", *args])
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tail(output: str) -> list[str]:
    return [line for line in output.replace("\r\n", "\n").split("\n") if line][-12:]


def require_clean_tree() -> None:
    dirty = git_output("status", "--short")
    if dirty:
        raise RuntimeError("refuse WBA callback receipt from a dirty worktree:\n" + dirty)


def capture() -> dict[str, Any]:
    require_clean_tree()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(PACK) != PACK_SHA256:
        raise RuntimeError("v9 candidate CEMP hash drifted")
    if manifest.get("revision") != 90 or manifest.get("provenance", {}).get("runtime_resource_activated") is not False:
        raise RuntimeError("v9 candidate manifest is not the locked inactive revision 90 pack")
    result = run(["pwsh", "-NoProfile", "-File", str(HOST_TEST.relative_to(ROOT))])
    if result.returncode != 0 or SUCCESS_MARKER not in result.stdout:
        raise RuntimeError("WBA CEMP callback replay failed:\n" + result.stdout)
    return {
        "schema": "companion.wba_v9_cemp_callback_replay_receipt.v1",
        "status": "PASS_CURRENT_SOURCE_MACHINE_ONLY_CALLBACK_REPLAY",
        "source_commit": git_output("rev-parse", "HEAD"),
        "source_paths": list(SOURCE_PATHS),
        "candidate": {
            "pack": PACK.relative_to(ROOT).as_posix(),
            "pack_sha256": PACK_SHA256,
            "name": manifest.get("name"),
            "revision": manifest.get("revision"),
            "clips": len(manifest.get("clips", [])),
            "frames": sum(len(clip.get("frames", [])) for clip in manifest.get("clips", [])),
            "runtime_resource_activated": False,
        },
        "targets": ["WBA55", "WBA65"],
        "host_test": {
            "command": ["pwsh", "-NoProfile", "-File", HOST_TEST.relative_to(ROOT).as_posix()],
            "returncode": result.returncode,
            "output_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest().upper(),
            "output_tail": tail(result.stdout),
        },
        "boundary": {
            "real_wba_board": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "panel_command": False,
            "owner_visual_pass": False,
            "runtime_resource_activation": False,
        },
    }


def verify(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "companion.wba_v9_cemp_callback_replay_receipt.v1":
        errors.append("unexpected receipt schema")
    if data.get("status") != "PASS_CURRENT_SOURCE_MACHINE_ONLY_CALLBACK_REPLAY":
        errors.append("receipt is not a machine-only callback replay PASS")
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        errors.append("receipt has no full source commit")
        return errors
    if run(["git", "cat-file", "-e", f"{source_commit}^{{commit}}"]).returncode != 0:
        errors.append("receipt source commit is unavailable")
        return errors
    changed = git_output("diff", "--name-only", source_commit, "HEAD", "--", *SOURCE_PATHS)
    if changed:
        errors.append("WBA callback replay inputs changed after receipt:\n" + changed)
    if data.get("source_paths") != list(SOURCE_PATHS):
        errors.append("receipt source-path boundary drifted")
    candidate = data.get("candidate", {})
    if candidate.get("pack_sha256") != PACK_SHA256 or candidate.get("name") != "companion-v9-expression-candidate-200x200":
        errors.append("receipt candidate identity drifted")
    if candidate.get("revision") != 90 or candidate.get("clips") != 13 or candidate.get("frames") != 39:
        errors.append("receipt candidate geometry drifted")
    if candidate.get("runtime_resource_activated") is not False:
        errors.append("receipt incorrectly permits v9 runtime activation")
    test = data.get("host_test", {})
    if test.get("command") != ["pwsh", "-NoProfile", "-File", HOST_TEST.relative_to(ROOT).as_posix()] or test.get("returncode") != 0:
        errors.append("receipt host-test invocation drifted")
    if not re.fullmatch(r"[0-9A-F]{64}", str(test.get("output_sha256", ""))) or not test.get("output_tail"):
        errors.append("receipt host-test output evidence is incomplete")
    if data.get("targets") != ["WBA55", "WBA65"]:
        errors.append("receipt target set drifted")
    boundary = data.get("boundary", {})
    for key in ("real_wba_board", "external_flash_provisioned", "firmware_flashed", "panel_command", "owner_visual_pass", "runtime_resource_activation"):
        if boundary.get(key) is not False:
            errors.append(f"receipt boundary drifted: {key}")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Run the clean-tree callback replay and write its receipt.")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args(argv)
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
    if args.write:
        try:
            data = capture()
        except (OSError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"PASS: captured WBA v9 CEMP callback replay receipt -> {receipt_path.relative_to(ROOT).as_posix()}")
        return 0
    if not receipt_path.exists():
        print(f"FAIL: missing receipt {receipt_path.relative_to(ROOT).as_posix()}", file=sys.stderr)
        return 1
    try:
        errors = verify(json.loads(receipt_path.read_text(encoding="utf-8")))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("FAIL: WBA v9 CEMP callback replay receipt verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WBA v9 CEMP callback replay receipt remains valid -> {receipt_path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
