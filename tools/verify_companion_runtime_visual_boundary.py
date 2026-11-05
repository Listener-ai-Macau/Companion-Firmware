#!/usr/bin/env python3
"""Guard the current WB55 runtime against retired procedural face fallbacks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "docs/validation/companion-runtime-visual-boundary-20260717.json"
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
PANEL_TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DISPLAY_QUEUE_HEADER = ROOT / "app/companion_pendant/epaper/display_queue.h"
DISPLAY_QUEUE_SOURCE = ROOT / "app/companion_pendant/epaper/display_queue.c"
V9_BINDING = ROOT / "app/companion_pendant/epaper/v9_candidate_resource_binding.c"
FLASH_SCRIPT = ROOT / "tools/flash_nucleo_bringup.ps1"
LEGACY_PROMOTION = ROOT / "tools/promote_wb55_screen_runtime_recheck.py"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.elf"
SOURCE_PATHS = (
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
    "app/companion_pendant/epaper/display_queue.h",
    "app/companion_pendant/epaper/display_queue.c",
    "app/companion_pendant/epaper/v9_candidate_resource_binding.c",
    "app/companion_pendant/epaper/emote_asset_pack.h",
    "app/companion_pendant/epaper/emote_asset_pack.c",
    "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
    "tools/flash_nucleo_bringup.ps1",
    "tools/promote_wb55_screen_runtime_recheck.py",
    "tools/verify_companion_runtime_visual_boundary.py",
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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


def find_nm() -> Path:
    from_path = shutil.which("arm-none-eabi-nm")
    if from_path:
        return Path(from_path)

    plugins = Path(r"C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins")
    candidates = sorted(
        plugins.glob("com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.*/tools/bin/arm-none-eabi-nm.exe")
    )
    if candidates:
        return candidates[-1]
    raise RuntimeError("arm-none-eabi-nm was not found; build the WB55 target with STM32CubeIDE installed")


def source_errors() -> list[str]:
    errors: list[str] = []
    app = APP_BLE.read_text(encoding="utf-8")
    panel = PANEL_TARGET.read_text(encoding="utf-8")
    queue = DISPLAY_QUEUE_HEADER.read_text(encoding="utf-8") + "\n" + DISPLAY_QUEUE_SOURCE.read_text(encoding="utf-8")
    v9_binding = V9_BINDING.read_text(encoding="utf-8")
    flash_script = FLASH_SCRIPT.read_text(encoding="utf-8")
    legacy_promotion = LEGACY_PROMOTION.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")

    for token in (
        "s_companion_last_emote_frame_valid",
        "comp_epaper_display_queue_enqueue_expression_frame",
        "expression_maintenance source=external_flash",
        "comp_v9_candidate_resource_runtime_activation_allowed",
        "comp_v9_candidate_resource_pack_identity_matches",
        "COMP_EMOTE_ASSET_MOUNT_INACTIVE_BY_POLICY",
        "COMP_EMOTE_ASSET_MOUNT_REJECTED_BY_POLICY",
    ):
        if token not in app:
            errors.append(f"app runtime missing required external-CEMP maintenance marker: {token}")
    for token in (
        "pet_expression.h",
        "Companion_Display_EnqueuePetPose",
        "s_companion_last_pet_pose",
        "comp_epaper_display_queue_enqueue_pet_expression",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_pet_expression_self_test",
        "comp_screen_menu_self_test",
    ):
        if token in app:
            errors.append(f"app runtime still references retired procedural visual route: {token}")
    if "external_assets_ready && visual_resource_activation_allowed" not in app:
        errors.append("app runtime may mount an external CEMP without the v9 activation gate")
    if "s_companion_screen_asset_mount = (comp_emote_asset_mount_t){0};" not in app:
        errors.append("app runtime retains a rejected external CEMP mount")
    if "rescue_ui" in app:
        errors.append("app runtime log still claims an internal visual fallback")
    if "return false;" not in v9_binding or "comp_v9_candidate_resource_runtime_activation_allowed" not in v9_binding:
        errors.append("v9 binding no longer keeps runtime activation disabled")

    for token in (
        "static bool frame_prepare",
        "source=external_flash",
        "source=unavailable kind=",
        "suppressing visual fallback",
        "COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR",
    ):
        if token not in panel:
            errors.append(f"panel runtime missing no-fallback guard: {token}")
    for token in (
        "pet_expression.h",
        "comp_pet_expression_render",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "frame_test_pattern",
        "source=procedural",
        "comp_screen_menu_render(",
        "source=rescue_ui",
    ):
        if token in panel:
            errors.append(f"panel runtime still contains retired visual fallback: {token}")
    for token in (
        "pet_expression.h",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        "comp_epaper_display_queue_enqueue_pet_expression",
        "comp_pet_expression_pose_t",
        "comp_pet_expression_pose_is_valid",
        "pet_pose",
    ):
        if token in queue:
            errors.append(f"display queue still contains retired procedural visual route: {token}")
    if "$(ROOT)/app/companion_pendant/epaper/pet_expression.c" in makefile:
        errors.append("WB55 product Makefile still compiles the retired procedural face composer")
    if "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json" not in makefile:
        errors.append("WB55 provision build is not bound to the current v9 CEMP manifest")
    if "emote_matrix_white_200x200.json" in makefile:
        errors.append("WB55 provision build still accepts the retired r53 visual manifest")
    if "Screen asset provisioning is blocked by the active Companion Goal" not in flash_script:
        errors.append("WB55 flash entry point can still provision a runtime-inactive visual pack")
    if "active Companion Goal prohibits legacy r53 runtime promotion" not in legacy_promotion:
        errors.append("legacy r53 promotion path is not blocked by the current visual policy")
    return errors


def symbol_errors() -> tuple[list[str], dict[str, Any]]:
    if not ELF.is_file():
        return [f"WB55 ELF is missing: {rel(ELF)}"], {}

    nm = find_nm()
    completed = run([str(nm), "--defined-only", "-C", str(ELF)])
    if completed.returncode != 0:
        return [f"arm-none-eabi-nm failed: {completed.stdout.strip()}"], {}

    forbidden = re.compile(
        r"\b(?:comp_pet_expression|frame_test_pattern|Companion_Display_EnqueuePetPose|comp_screen_menu_render)\b"
    )
    matches = [line for line in completed.stdout.splitlines() if forbidden.search(line)]
    if matches:
        return ["WB55 ELF still defines retired procedural visual symbols:\n" + "\n".join(matches)], {}
    return [], {
        "path": rel(ELF),
        "sha256": sha256(ELF),
        "nm": rel(nm) if nm.is_relative_to(ROOT) else str(nm).replace("\\", "/"),
        "forbidden_symbol_matches": 0,
    }


def inspect() -> tuple[list[str], dict[str, Any]]:
    errors = source_errors()
    symbol_failures, elf = symbol_errors()
    errors.extend(symbol_failures)
    source_hashes = {path: sha256(ROOT / path) for path in SOURCE_PATHS}
    return errors, {
        "source_paths": list(SOURCE_PATHS),
        "source_sha256": source_hashes,
        "elf": elf,
        "runtime_policy": {
            "active_expression_maintenance": "external CEMP frame replay only",
            "menu_visual_base": "external CEMP base required; no complete code-rendered fallback",
            "unavailable_visual_source": "return transport error; do not draw a procedural or test substitute",
            "external_mount": "v9 activation gate; inactive policy does not parse or display any CEMP pack",
            "provision_source": "v9 candidate manifest only; no retired r53 manifest",
            "provision_flash": "blocked while the v9 candidate remains runtime-inactive",
            "retired_procedural_face_linked": False,
        },
        "hardware_boundary": {
            "firmware_flashed": False,
            "panel_command": False,
            "camera_or_human_visual_pass": False,
        },
    }


def receipt_payload() -> dict[str, Any]:
    errors, details = inspect()
    if errors:
        raise RuntimeError("\n".join(errors))
    return {
        "schema": "companion.runtime_visual_boundary.v1",
        "status": "PASS_CURRENT_SOURCE_NO_PROCEDURAL_VISUAL_FALLBACK",
        "generated_on": date.today().isoformat(),
        "source_commit": git_output("rev-parse", "HEAD"),
        **details,
    }


def verify_receipt(data: dict[str, Any]) -> list[str]:
    errors, details = inspect()
    if data.get("schema") != "companion.runtime_visual_boundary.v1":
        errors.append("unexpected visual-boundary receipt schema")
    if data.get("status") != "PASS_CURRENT_SOURCE_NO_PROCEDURAL_VISUAL_FALLBACK":
        errors.append("visual-boundary receipt is not a current-source PASS")
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        errors.append("visual-boundary receipt has no full source commit")
    elif run(["git", "cat-file", "-e", f"{source_commit}^{{commit}}"]).returncode != 0:
        errors.append("visual-boundary receipt source commit is not available")
    else:
        changed = git_output("diff", "--name-only", source_commit, "HEAD", "--", *SOURCE_PATHS)
        if changed:
            errors.append("visual-boundary source inputs changed after receipt:\n" + changed)
    if data.get("source_paths") != list(SOURCE_PATHS):
        errors.append("visual-boundary source-path boundary drifted")
    if data.get("source_sha256") != details["source_sha256"]:
        errors.append("visual-boundary source digest drifted")
    if data.get("elf", {}).get("forbidden_symbol_matches") != 0:
        errors.append("visual-boundary receipt reports a forbidden ELF symbol")
    if data.get("runtime_policy") != details["runtime_policy"]:
        errors.append("visual-boundary runtime policy drifted")
    if data.get("hardware_boundary") != details["hardware_boundary"]:
        errors.append("visual-boundary hardware boundary drifted")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write a clean-tree machine-only receipt")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args(argv)
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt

    if args.write:
        try:
            if git_output("status", "--short"):
                raise RuntimeError("refuse to capture visual-boundary receipt from a dirty worktree")
            data = receipt_payload()
        except RuntimeError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"PASS: captured runtime visual-boundary receipt -> {rel(receipt_path)}")
        return 0

    if not receipt_path.is_file():
        print(f"FAIL: receipt missing: {rel(receipt_path)}", file=sys.stderr)
        return 1
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    errors = verify_receipt(data)
    if errors:
        print("FAIL:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"PASS: current source retains the no-procedural-visual-fallback boundary ({rel(receipt_path)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
