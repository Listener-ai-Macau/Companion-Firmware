#!/usr/bin/env python3
"""Verify the staged WB55 FTS02 replacement recovery runner."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/run_wb55_screen_hardware_recovery.ps1"
PARSER = ROOT / "tools/verify_wb55_official_full_diagnostic_log.py"
BUILD_WRAPPER = ROOT / "tools/build_nucleo_bringup.ps1"
PANEL_TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DEFAULT_FIXTURE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-runner.json"
CHECK_ROOT = ROOT / ".cache/validation/wb55-fts02-recovery-preflight"
RECOVERY_ROOT = ROOT / ".cache/validation/wb55-fts02-recovery-selftest"
STUB_IMAGE_ROOT = CHECK_ROOT / "images"
SCHEMA_ID = "companion.screen.wb55_hardware_recovery_runner.v1"
PREPARATION_COMMANDS = (
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681Bringup -Force",
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681OfficialFullDiagnostic -EpaperSsd1681DiagnosticPattern white -Force",
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681OfficialFullDiagnostic -EpaperSsd1681DiagnosticPattern black -Force",
)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def run(*args: str, timeout: int = 60) -> dict[str, Any]:
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(RUNNER), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def load_report(root: pathlib.Path, stage: str) -> dict[str, Any]:
    return json.loads((root / stage / "stage-run.json").read_text(encoding="utf-8-sig"))


def build_snapshot() -> dict[str, Any]:
    build_wrapper_text = BUILD_WRAPPER.read_text(encoding="utf-8-sig")
    official_start = build_wrapper_text.find("if ($EpaperSsd1681OfficialFullDiagnostic)")
    official_end = (
        build_wrapper_text.find("if ($EpaperProductExpressionDemo)", official_start)
        if official_start >= 0
        else -1
    )
    official_block = (
        build_wrapper_text[official_start:official_end]
        if official_start >= 0 and official_end > official_start
        else ""
    )
    panel_target_text = PANEL_TARGET.read_text(encoding="utf-8-sig")
    stub_images = {
        name: STUB_IMAGE_ROOT / f"{name}.hex"
        for name in ("normal", "white", "black")
    }
    STUB_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    for image in stub_images.values():
        image.write_text(":00000001FF\n", encoding="ascii")
    image_args = [
        "-NormalImagePath", str(stub_images["normal"]),
        "-WhiteImagePath", str(stub_images["white"]),
        "-BlackImagePath", str(stub_images["black"]),
    ]
    parser = subprocess.run(
        ["python", str(PARSER), "--self-test"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    stage_results: dict[str, Any] = {}
    for stage in ("White", "Black", "RestoreNormal"):
        result = run(
            "-CheckOnly", "-Stage", stage, "-OutRoot", str(CHECK_ROOT), *image_args
        )
        report = load_report(CHECK_ROOT, stage.lower())
        stage_results[stage.lower()] = {
            "returncode": result["returncode"],
            "report_status": report.get("status"),
            "claim_scope": report.get("claim_scope"),
            "step_ids": [step.get("id") for step in report.get("steps", [])],
            "result_count": len(report.get("results", [])),
            "image": report.get("image"),
            "safety": report.get("safety", {}),
        }

    negative = run("-Execute", "-Stage", "White", timeout=30)
    negative_text = negative["stdout"] + negative["stderr"]
    recovery = run("-SelfTestRecovery", "-OutRoot", str(RECOVERY_ROOT), timeout=30)
    recovery_text = recovery["stdout"] + recovery["stderr"]
    recovery_report = load_report(RECOVERY_ROOT, "selftest")
    statuses = {
        str(result.get("id")): str(result.get("status"))
        for result in recovery_report.get("results", [])
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_PREFLIGHT",
        "claim_scope": "static_and_stubbed_recovery_no_hardware_claim",
        "runner": rel(RUNNER),
        "parser": rel(PARSER),
        "diagnostic_image_contract": {
            "build_wrapper": rel(BUILD_WRAPPER),
            "panel_target": rel(PANEL_TARGET),
            "official_mode_enables_ssd1681_driver": '"EPAPER_SSD1681_BRINGUP=1"' in official_block,
            "official_mode_enables_single_plane_path": (
                '"EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC=1"' in official_block
            ),
            "runtime_marker_records_pattern_and_official_path": (
                '"[epaper] boot_diag pattern=%u official=%u cycle=%u result=%u bytes=%lu busy=%d\\r\\n"'
                in panel_target_text
            ),
        },
        "parser_selftest": {
            "returncode": parser.returncode,
            "passed": parser.returncode == 0 and "PASS: official full diagnostic parser self-test" in parser.stdout,
        },
        "stages": stage_results,
        "execute_without_lock_negative": {
            "returncode": negative["returncode"],
            "refused_before_hardware": (
                negative["returncode"] != 0
                and "Refusing WB55 FTS02 recovery execution without workflow lock acknowledgement" in negative_text
                and "RUN:" not in negative_text
            ),
        },
        "recovery_selftest": {
            "returncode": recovery["returncode"],
            "stdout_has_recovery": "RECOVERY: flash_normal_restore_after_failure" in recovery_text,
            "report_status": recovery_report.get("status"),
            "claim_scope": recovery_report.get("claim_scope"),
            "normal_firmware_restored": recovery_report.get("normal_firmware_restored"),
            "result_ids": list(statuses),
            "result_statuses": statuses,
        },
        "preparation_commands": list(PREPARATION_COMMANDS),
        "operator_sequence": [
            "Run White under Companion-WB55 lock, then record one focused visible-frame decision.",
            "Only after White PASS, run Black and record one focused visible-frame decision.",
            "Run RestoreNormal before any product interaction or runtime-resource acceptance.",
            "If either visible frame fails, measure PREVGH1/PREVGL1 during that verified refresh and stop software changes.",
        ],
        "wba_boundary": (
            "WBA55/WBA65 reuse the staged machine/operator evidence shape but must provide target-local "
            "flash, serial, panel-power, rail, and normal-restore commands."
        ),
        "validation_commands": [
            "python .\\tools\\verify_wb55_official_full_diagnostic_log.py --self-test",
            "python .\\tools\\verify_wb55_screen_hardware_recovery_runner.py",
            "pwsh -NoProfile -File .\\tools\\run_wb55_screen_hardware_recovery.ps1 -CheckOnly -Stage White",
            "pwsh -NoProfile -File .\\tools\\run_wb55_screen_hardware_recovery.ps1 -CheckOnly -Stage Black",
            "pwsh -NoProfile -File .\\tools\\run_wb55_screen_hardware_recovery.ps1 -CheckOnly -Stage RestoreNormal",
        ],
    }


def verify(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if snapshot.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if snapshot.get("claim_scope") != "static_and_stubbed_recovery_no_hardware_claim":
        errors.append("preflight must retain no-hardware claim scope")
    image_contract = snapshot.get("diagnostic_image_contract", {})
    for key in (
        "official_mode_enables_ssd1681_driver",
        "official_mode_enables_single_plane_path",
        "runtime_marker_records_pattern_and_official_path",
    ):
        if image_contract.get(key) is not True:
            errors.append(f"diagnostic image contract failed: {key}")
    if snapshot.get("parser_selftest", {}).get("passed") is not True:
        errors.append("official diagnostic parser self-test must pass")
    if snapshot.get("preparation_commands") != list(PREPARATION_COMMANDS):
        errors.append("diagnostic preparation command sequence drifted")
    expected_steps = {
        "white": ["flash_white", "capture_white", "parse_white"],
        "black": ["flash_black", "capture_black", "parse_black"],
        "restorenormal": ["flash_normal_restore"],
    }
    expected_images = {
        "white": ".cache/validation/wb55-fts02-recovery-preflight/images/white.hex",
        "black": ".cache/validation/wb55-fts02-recovery-preflight/images/black.hex",
        "restorenormal": ".cache/validation/wb55-fts02-recovery-preflight/images/normal.hex",
    }
    for stage, step_ids in expected_steps.items():
        result = snapshot.get("stages", {}).get(stage, {})
        if result.get("returncode") != 0 or result.get("report_status") != "DRY-RUN":
            errors.append(f"{stage} CheckOnly must pass as DRY-RUN")
        if result.get("claim_scope") != "preflight_only_no_hardware_claim":
            errors.append(f"{stage} CheckOnly claim scope drifted")
        if result.get("step_ids") != step_ids or result.get("result_count") != 0:
            errors.append(f"{stage} stage order drifted")
        if result.get("image") != expected_images[stage]:
            errors.append(f"{stage} CheckOnly did not use its isolated stub image")
        if not all(result.get("safety", {}).values()):
            errors.append(f"{stage} safety contract is incomplete")
    negative = snapshot.get("execute_without_lock_negative", {})
    if negative.get("returncode") == 0 or negative.get("refused_before_hardware") is not True:
        errors.append("Execute must refuse before hardware without Companion-WB55 lock acknowledgement")
    recovery = snapshot.get("recovery_selftest", {})
    if recovery.get("returncode") == 0 or recovery.get("stdout_has_recovery") is not True:
        errors.append("recovery self-test must fail and invoke normal restore")
    if recovery.get("report_status") != "FAIL" or recovery.get("normal_firmware_restored") is not True:
        errors.append("recovery self-test must prove normal firmware restoration")
    if recovery.get("claim_scope") != "stubbed_failure_recovery_no_hardware_claim":
        errors.append("recovery self-test claim scope drifted")
    if recovery.get("result_ids") != ["flash_white", "capture_white", "flash_normal_restore_after_failure"]:
        errors.append("recovery self-test step order drifted")
    if recovery.get("result_statuses") != {
        "flash_white": "PASS",
        "capture_white": "FAIL",
        "flash_normal_restore_after_failure": "PASS",
    }:
        errors.append("recovery self-test result matrix drifted")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args(argv)
    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    snapshot = build_snapshot()
    errors = verify(snapshot)
    rendered = json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(rendered, encoding="utf-8")
    elif not fixture.exists():
        errors.append(f"missing fixture {rel(fixture)}")
    elif fixture.read_text(encoding="utf-8") != rendered:
        errors.append(f"stale fixture {rel(fixture)}; rerun with --write")
    if errors:
        print("FAIL: WB55 FTS02 recovery runner preflight failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 staged FTS02 recovery runner verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
