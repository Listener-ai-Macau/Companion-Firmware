#!/usr/bin/env python3
"""Verify the staged WB55 replacement-display-FPC recovery runner."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/run_wb55_screen_hardware_recovery.ps1"
LOCK_HELPER = ROOT / "tools/companion_wb55_lock.ps1"
LOCK_HOST_TEST = ROOT / "tools/test_companion_wb55_lock_host.ps1"
FLASH_RUNNER = ROOT / "tools/flash_nucleo_bringup.ps1"
SERIAL_RUNNER = ROOT / "tools/capture_nucleo_serial.ps1"
PARSER = ROOT / "tools/verify_wb55_official_full_diagnostic_log.py"
RAIL_PARSER = ROOT / "tools/verify_wb55_official_full_rail_measurement.py"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
FPC_EVIDENCE = ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
BUILD_WRAPPER = ROOT / "tools/build_nucleo_bringup.ps1"
PANEL_TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DEFAULT_FIXTURE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-runner.json"
CHECK_ROOT = ROOT / ".cache/validation/wb55-display-fpc-recovery-preflight"
RECOVERY_ROOT = ROOT / ".cache/validation/wb55-display-fpc-recovery-selftest"
OPERATOR_REJECT_ROOT = ROOT / ".cache/validation/wb55-display-fpc-operator-reject-selftest"
OPERATOR_PASS_ROOT = ROOT / ".cache/validation/wb55-display-fpc-operator-pass-selftest"
PRESERVE_ROOT = ROOT / ".cache/validation/wb55-display-fpc-checkonly-preservation-selftest"
STUB_IMAGE_ROOT = CHECK_ROOT / "images"
SCHEMA_ID = "companion.screen.wb55_hardware_recovery_runner.v1"
PREPARATION_COMMANDS = (
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681Bringup -Force",
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681OfficialFullDiagnostic -EpaperSsd1681DiagnosticPattern white -Force",
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681OfficialFullDiagnostic -EpaperSsd1681DiagnosticPattern black -Force",
    "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 "
    "-EpaperSsd1681OfficialWhiteRailProbe -Force",
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
    runner_text = RUNNER.read_text(encoding="utf-8-sig")
    flash_runner_text = FLASH_RUNNER.read_text(encoding="utf-8-sig")
    serial_runner_text = SERIAL_RUNNER.read_text(encoding="utf-8-sig")
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
    source_audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8")) if SOURCE_AUDIT.is_file() else {}
    stub_images = {
        name: STUB_IMAGE_ROOT / f"{name}.hex"
        for name in ("normal", "white", "black")
    }
    STUB_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    for image in stub_images.values():
        image.write_text(":00000001FF\n", encoding="ascii")
    if not FPC_EVIDENCE.is_file():
        raise FileNotFoundError(f"missing replacement display-FPC evidence: {rel(FPC_EVIDENCE)}")
    image_args = [
        "-NormalImagePath", str(stub_images["normal"]),
        "-WhiteImagePath", str(stub_images["white"]),
        "-BlackImagePath", str(stub_images["black"]),
        "-DisplayFpcReplacementEvidencePath", str(FPC_EVIDENCE),
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
    rail_parser = subprocess.run(
        ["python", str(RAIL_PARSER), "--self-test"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    lock_host_test = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(LOCK_HOST_TEST)],
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
            "operator_review": report.get("operator_review", {}),
            "prerequisites": report.get("prerequisites", {}),
        }

    protected_report = PRESERVE_ROOT / "white" / "stage-run.json"
    protected_report.parent.mkdir(parents=True, exist_ok=True)
    protected_report.write_text(
        json.dumps(
            {
                "schema_id": "companion.wb55.screen_recovery_stage_run.v2",
                "status": "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS",
                "claim_scope": "machine_digital_trace_pending_operator_visual_gate",
                "evidence_marker": "must-survive-checkonly",
            },
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    protected_before = protected_report.read_bytes()
    protected_check = run(
        "-CheckOnly", "-Stage", "White", "-OutRoot", str(PRESERVE_ROOT), *image_args
    )
    protected_text = protected_check["stdout"] + protected_check["stderr"]
    protected_after = protected_report.read_bytes()

    negative = run(
        "-Execute",
        "-Stage",
        "White",
        "-DisplayFpcReplacementEvidencePath",
        str(CHECK_ROOT / "missing-display-fpc.json"),
        timeout=30,
    )
    negative_text = negative["stdout"] + negative["stderr"]
    locked_missing_fpc = run(
        "-Execute", "-WorkflowLockHeld", "-Stage", "White",
        "-DisplayFpcReplacementEvidencePath", str(CHECK_ROOT / "missing-display-fpc.json"),
        timeout=30,
    )
    locked_missing_fpc_text = locked_missing_fpc["stdout"] + locked_missing_fpc["stderr"]
    black_missing_white_rail = run(
        "-Execute",
        "-WorkflowLockHeld",
        "-Stage",
        "Black",
        timeout=30,
    )
    black_missing_white_rail_text = black_missing_white_rail["stdout"] + black_missing_white_rail["stderr"]
    recovery = run("-SelfTestRecovery", "-OutRoot", str(RECOVERY_ROOT), timeout=30)
    recovery_text = recovery["stdout"] + recovery["stderr"]
    recovery_report = load_report(RECOVERY_ROOT, "selftest")
    statuses = {
        str(result.get("id")): str(result.get("status"))
        for result in recovery_report.get("results", [])
    }
    operator_reject = run(
        "-SelfTestRecovery",
        "-SelfTestOperatorSelection", "失败",
        "-OutRoot", str(OPERATOR_REJECT_ROOT),
        timeout=30,
    )
    operator_reject_text = operator_reject["stdout"] + operator_reject["stderr"]
    operator_reject_report = load_report(OPERATOR_REJECT_ROOT, "selftest")
    operator_reject_statuses = {
        str(result.get("id")): str(result.get("status"))
        for result in operator_reject_report.get("results", [])
    }
    operator_pass = run(
        "-SelfTestRecovery",
        "-SelfTestOperatorSelection", "通过",
        "-OutRoot", str(OPERATOR_PASS_ROOT),
        timeout=30,
    )
    operator_pass_report = load_report(OPERATOR_PASS_ROOT, "selftest")
    operator_pass_statuses = {
        str(result.get("id")): str(result.get("status"))
        for result in operator_pass_report.get("results", [])
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
                '"[epaper] boot_diag pattern=%u official=%u cycle=%u result=%u bytes=%lu busy=%d'
                in panel_target_text
                and "(unsigned)COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC" in panel_target_text
            ),
            "isolated_white_rail_probe_profile": all(
                token in build_wrapper_text
                for token in (
                    "$EpaperSsd1681OfficialWhiteRailProbe",
                    "EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC=1",
                    "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=1",
                    "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=30",
                    "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=5000",
                    "BUILD_DIR=build_official_full_rail_probe_white",
                    "TARGET=Companion_Nucleo_WB55RG_OfficialFullRailProbeWhite",
                )
            ),
        },
        "operator_prompt_contract": {
            "canonical_aiw_command_present": "operator-prompt" in runner_text,
            "review_style_present": "-ReviewStyle -Input" in runner_text,
            "durable_output_path_present": "operator-prompt-observation.txt" in runner_text,
            "four_result_buttons_present": '"通过,失败,跳过,中止"' in runner_text,
            "prompt_after_machine_steps": (
                runner_text.find("foreach ($step in $steps)")
                < runner_text.find("Invoke-OperatorReview -ReviewStage")
            ),
        "normal_restore_after_review_present": "flash_normal_restore_after_review" in runner_text,
        "nonempty_operator_observation_required": "without the required physical observation note" in runner_text,
        "operator_observation_template_present": "-DefaultText $Spec.default_note" in runner_text,
        },
        "prerequisite_guard_contract": {
            "replacement_display_fpc_schema_guard_present": "companion.wb55.display_fpc_replacement_evidence.v1" in runner_text,
            "white_execute_requires_replacement_display_fpc": "Assert-DisplayFpcReplacementEvidence" in runner_text,
            "black_execute_requires_white_rail": "Assert-WhiteRailEvidence" in runner_text,
            "white_rail_schema_guard_present": "companion.wb55.official_full_rail_measurement.v1" in runner_text,
            "vendor_source_audit_guard_present": "Assert-VendorSourceAudit" in runner_text,
            "checkonly_preserves_completed_evidence": (
                "Assert-CheckOnlyWillNotOverwriteCompletedEvidence" in runner_text
            ),
        },
        "hardware_lock_contract": {
            "helper": rel(LOCK_HELPER),
            "helper_exists": LOCK_HELPER.is_file(),
            "runner_imports_helper": "companion_wb55_lock.ps1" in runner_text,
            "runner_acquires_before_steps": "Enter-CompanionWb55Lock -Purpose \"official full $Stage recovery\"" in runner_text,
            "child_grant_is_recorded": "Get-CompanionWb55LockEvidenceSummary" in runner_text,
            "legacy_boolean_is_not_authority": "legacy_workflow_lock_boolean_is_not_authority" in runner_text,
            "flash_child_imports_and_uses_helper": (
                "companion_wb55_lock.ps1" in flash_runner_text
                and "Enter-CompanionWb55Lock" in flash_runner_text
                and "Exit-CompanionWb55Lock" in flash_runner_text
            ),
            "serial_child_imports_and_uses_helper": (
                "companion_wb55_lock.ps1" in serial_runner_text
                and "Enter-CompanionWb55Lock" in serial_runner_text
                and "Exit-CompanionWb55Lock" in serial_runner_text
            ),
            "runner_does_not_forward_legacy_boolean_to_serial_child": (
                '"-Execute", "-WorkflowLockHeld"' not in runner_text
            ),
            "mutex_spans_step_sequence_and_restore": (
                runner_text.find("Enter-CompanionWb55Lock -Purpose \"official full $Stage recovery\"")
                < runner_text.rfind("Exit-CompanionWb55Lock")
            ),
            "host_mutex_test_returncode": lock_host_test.returncode,
            "host_mutex_test_passed": (
                lock_host_test.returncode == 0
                and "PASS: Companion-WB55 host mutex rejects contention and releases cleanly." in lock_host_test.stdout
            ),
        },
        "source_audit_contract": {
            "path": rel(SOURCE_AUDIT) if SOURCE_AUDIT.is_file() else None,
            "schema_id": source_audit.get("schema_id"),
            "machine_status": source_audit.get("machine_status"),
            "promotion_status": source_audit.get("promotion_status"),
            "production_lut_reference_absent": source_audit.get("command_evidence", {}).get("production_lut_reference_absent"),
            "runner_binds_parser_audit_argument": "--source-audit" in runner_text,
            "runner_rehashes_audited_sources_before_execute": "Get-FileHash" in runner_text,
        },
        "parser_selftest": {
            "returncode": parser.returncode,
            "passed": parser.returncode == 0 and "PASS: official full diagnostic parser self-test" in parser.stdout,
        },
        "rail_measurement_parser_selftest": {
            "path": rel(RAIL_PARSER),
            "returncode": rail_parser.returncode,
            "passed": rail_parser.returncode == 0
            and "PASS: official full rail measurement parser self-test" in rail_parser.stdout,
        },
        "stages": stage_results,
        "checkonly_preserves_completed_evidence": {
            "returncode": protected_check["returncode"],
            "refused_before_commands": (
                protected_check["returncode"] != 0
                and "Refusing CheckOnly to overwrite completed or non-preflight stage evidence"
                in protected_text
                and "CHECK:" not in protected_text
                and "RUN:" not in protected_text
            ),
            "artifact_bytes_unchanged": protected_before == protected_after,
        },
        "execute_missing_replacement_display_fpc_negative": {
            "returncode": negative["returncode"],
            "refused_before_hardware": (
                negative["returncode"] != 0
                and "Missing replacement display-FPC evidence file." in negative_text
                and "RUN:" not in negative_text
            ),
        },
        "execute_with_lock_missing_replacement_display_fpc_negative": {
            "returncode": locked_missing_fpc["returncode"],
            "refused_before_hardware": (
                locked_missing_fpc["returncode"] != 0
                and "Missing replacement display-FPC evidence file." in locked_missing_fpc_text
                and "RUN:" not in locked_missing_fpc_text
            ),
        },
        "black_without_white_rail_negative": {
            "returncode": black_missing_white_rail["returncode"],
            "refused_before_hardware": (
                black_missing_white_rail["returncode"] != 0
                and "Missing post-White rail evidence file." in black_missing_white_rail_text
                and "RUN:" not in black_missing_white_rail_text
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
        "operator_rejection_selftest": {
            "returncode": operator_reject["returncode"],
            "stdout_has_recovery": "RECOVERY: flash_normal_restore_after_failure" in operator_reject_text,
            "report_status": operator_reject_report.get("status"),
            "normal_firmware_restored": operator_reject_report.get("normal_firmware_restored"),
            "diagnostic_left_installed": operator_reject_report.get("diagnostic_left_installed"),
            "operator_review": operator_reject_report.get("operator_review", {}),
            "operator_result_exists": (OPERATOR_REJECT_ROOT / "selftest" / "operator-prompt-observation.txt").is_file(),
            "result_ids": list(operator_reject_statuses),
            "result_statuses": operator_reject_statuses,
        },
        "operator_pass_selftest": {
            "returncode": operator_pass["returncode"],
            "report_status": operator_pass_report.get("status"),
            "normal_firmware_restored": operator_pass_report.get("normal_firmware_restored"),
            "diagnostic_left_installed": operator_pass_report.get("diagnostic_left_installed"),
            "operator_review": operator_pass_report.get("operator_review", {}),
            "operator_result_exists": (OPERATOR_PASS_ROOT / "selftest" / "operator-prompt-observation.txt").is_file(),
            "result_ids": list(operator_pass_statuses),
            "result_statuses": operator_pass_statuses,
        },
        "preparation_commands": list(PREPARATION_COMMANDS),
        "operator_sequence": [
            "Run White only after the versioned replacement-display-FPC evidence passes; the runner holds the Companion-WB55 firmware mutex across flash, capture, review and restore.",
            "Only after White rail evidence passes, run Black and record one focused visible-frame decision.",
            "Run RestoreNormal before any product interaction or runtime-resource acceptance.",
            "If either visible frame fails, measure PREVGH1/PREVGL1 during that verified refresh and stop software changes.",
        ],
        "wba_boundary": (
            "WBA55/WBA65 reuse the staged machine/operator evidence shape but must provide target-local "
            "flash, serial, panel-power, rail, and normal-restore commands."
        ),
        "validation_commands": [
            "python .\\tools\\verify_wb55_official_full_diagnostic_log.py --self-test",
            "python .\\tools\\verify_wb55_official_full_rail_measurement.py --self-test",
            "pwsh -NoProfile -File .\\tools\\test_companion_wb55_lock_host.ps1",
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
        "isolated_white_rail_probe_profile",
    ):
        if image_contract.get(key) is not True:
            errors.append(f"diagnostic image contract failed: {key}")
    prompt_contract = snapshot.get("operator_prompt_contract", {})
    for key in (
        "canonical_aiw_command_present",
        "review_style_present",
        "durable_output_path_present",
        "four_result_buttons_present",
        "prompt_after_machine_steps",
        "normal_restore_after_review_present",
        "nonempty_operator_observation_required",
        "operator_observation_template_present",
    ):
        if prompt_contract.get(key) is not True:
            errors.append(f"operator prompt contract failed: {key}")
    prerequisite_contract = snapshot.get("prerequisite_guard_contract", {})
    for key in (
        "replacement_display_fpc_schema_guard_present",
        "white_execute_requires_replacement_display_fpc",
        "black_execute_requires_white_rail",
        "white_rail_schema_guard_present",
        "vendor_source_audit_guard_present",
        "checkonly_preserves_completed_evidence",
    ):
        if prerequisite_contract.get(key) is not True:
            errors.append(f"prerequisite guard contract failed: {key}")
    hardware_lock = snapshot.get("hardware_lock_contract", {})
    for key in (
        "helper_exists",
        "runner_imports_helper",
        "runner_acquires_before_steps",
        "child_grant_is_recorded",
        "legacy_boolean_is_not_authority",
        "flash_child_imports_and_uses_helper",
        "serial_child_imports_and_uses_helper",
        "runner_does_not_forward_legacy_boolean_to_serial_child",
        "mutex_spans_step_sequence_and_restore",
        "host_mutex_test_passed",
    ):
        if hardware_lock.get(key) is not True:
            errors.append(f"hardware lock contract failed: {key}")
    if snapshot.get("source_audit_contract") != {
        "path": "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json",
        "schema_id": "companion.gdey0154d67_t03.vendor_1s_source_audit.v1",
        "machine_status": "PASS_AUDIT_COMPLETE",
        "promotion_status": "NO_GO_PANEL_IDENTITY_UNPROVEN",
        "production_lut_reference_absent": True,
        "runner_binds_parser_audit_argument": True,
        "runner_rehashes_audited_sources_before_execute": True,
    }:
        errors.append("source-audit binding contract drifted")
    if snapshot.get("parser_selftest", {}).get("passed") is not True:
        errors.append("official diagnostic parser self-test must pass")
    if snapshot.get("rail_measurement_parser_selftest", {}).get("passed") is not True:
        errors.append("official rail measurement parser self-test must pass")
    if snapshot.get("preparation_commands") != list(PREPARATION_COMMANDS):
        errors.append("diagnostic preparation command sequence drifted")
    expected_steps = {
        "white": ["flash_white", "capture_white", "parse_white"],
        "black": ["flash_black", "capture_black", "parse_black"],
        "restorenormal": ["flash_normal_restore"],
    }
    expected_images = {
        "white": ".cache/validation/wb55-display-fpc-recovery-preflight/images/white.hex",
        "black": ".cache/validation/wb55-display-fpc-recovery-preflight/images/black.hex",
        "restorenormal": ".cache/validation/wb55-display-fpc-recovery-preflight/images/normal.hex",
    }
    expected_operator_reviews = {
        "white": {
            "required": True,
            "invoked": False,
            "style": "aiw_operator_prompt_v1",
            "progress_text": "1/2（本次 1/1）",
            "output_path": ".cache/validation/wb55-display-fpc-recovery-preflight/white/operator-prompt-observation.txt",
        },
        "black": {
            "required": True,
            "invoked": False,
            "style": "aiw_operator_prompt_v1",
            "progress_text": "2/2（本次 1/1）",
            "output_path": ".cache/validation/wb55-display-fpc-recovery-preflight/black/operator-prompt-observation.txt",
        },
        "restorenormal": {
            "required": False,
            "invoked": False,
            "style": None,
            "progress_text": None,
            "output_path": None,
        },
    }
    expected_prerequisites = {
        "white": {
            "replacement_display_fpc_required": True,
            "replacement_display_fpc_path": "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json",
            "replacement_display_fpc_validated": False,
            "post_white_rail_required": False,
            "post_white_rail_path": None,
            "post_white_rail_validated": False,
            "vendor_source_audit_required": True,
            "vendor_source_audit_path": "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json",
            "vendor_source_audit_validated": False,
        },
        "black": {
            "replacement_display_fpc_required": False,
            "replacement_display_fpc_path": None,
            "replacement_display_fpc_validated": False,
            "post_white_rail_required": True,
            "post_white_rail_path": None,
            "post_white_rail_validated": False,
            "vendor_source_audit_required": True,
            "vendor_source_audit_path": "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json",
            "vendor_source_audit_validated": False,
        },
        "restorenormal": {
            "replacement_display_fpc_required": False,
            "replacement_display_fpc_path": None,
            "replacement_display_fpc_validated": False,
            "post_white_rail_required": False,
            "post_white_rail_path": None,
            "post_white_rail_validated": False,
            "vendor_source_audit_required": False,
            "vendor_source_audit_path": None,
            "vendor_source_audit_validated": False,
        },
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
        if result.get("prerequisites") != expected_prerequisites[stage]:
            errors.append(f"{stage} prerequisite declaration drifted")
        review = result.get("operator_review", {})
        for key, expected in expected_operator_reviews[stage].items():
            if review.get(key) != expected:
                errors.append(f"{stage} operator review {key} drifted")
        if stage in ("white", "black"):
            if not all(
                isinstance(review.get(key), str) and review.get(key)
                for key in ("title", "scope_text", "message", "expected_text")
            ):
                errors.append(f"{stage} operator review text is incomplete")
    negative = snapshot.get("execute_missing_replacement_display_fpc_negative", {})
    if negative.get("returncode") == 0 or negative.get("refused_before_hardware") is not True:
        errors.append("White Execute must refuse before hardware when replacement display-FPC evidence is absent")
    locked_missing_fpc = snapshot.get("execute_with_lock_missing_replacement_display_fpc_negative", {})
    if locked_missing_fpc.get("returncode") == 0 or locked_missing_fpc.get("refused_before_hardware") is not True:
        errors.append("White Execute must refuse before hardware when replacement display-FPC evidence is absent")
    black_missing_rail = snapshot.get("black_without_white_rail_negative", {})
    if black_missing_rail.get("returncode") == 0 or black_missing_rail.get("refused_before_hardware") is not True:
        errors.append("Black Execute must refuse before hardware when White rail evidence is absent")
    preserved = snapshot.get("checkonly_preserves_completed_evidence", {})
    if preserved.get("returncode") == 0 or preserved.get("refused_before_commands") is not True:
        errors.append("CheckOnly must refuse before command output when a completed stage report exists")
    if preserved.get("artifact_bytes_unchanged") is not True:
        errors.append("CheckOnly must preserve a completed stage report byte-for-byte")
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
    rejected = snapshot.get("operator_rejection_selftest", {})
    rejected_review = rejected.get("operator_review", {})
    if rejected.get("returncode") == 0 or rejected.get("stdout_has_recovery") is not True:
        errors.append("operator rejection self-test must fail and invoke normal restore")
    if rejected.get("report_status") != "FAIL" or rejected.get("normal_firmware_restored") is not True:
        errors.append("operator rejection must leave a FAIL report with normal firmware restored")
    if rejected.get("diagnostic_left_installed") is not False or rejected.get("operator_result_exists") is not True:
        errors.append("operator rejection must persist its result and leave no diagnostic installed")
    if rejected_review.get("invoked") is not True or rejected_review.get("selected") != "失败":
        errors.append("operator rejection report did not retain the selected button")
    if rejected.get("result_ids") != [
        "flash_white", "capture_white", "parse_white", "flash_normal_restore_after_failure"
    ]:
        errors.append("operator rejection self-test step order drifted")
    if rejected.get("result_statuses") != {
        "flash_white": "PASS",
        "capture_white": "PASS",
        "parse_white": "PASS",
        "flash_normal_restore_after_failure": "PASS",
    }:
        errors.append("operator rejection self-test result matrix drifted")
    passed = snapshot.get("operator_pass_selftest", {})
    passed_review = passed.get("operator_review", {})
    if passed.get("returncode") != 0:
        errors.append("operator PASS self-test must complete successfully")
    if passed.get("report_status") != "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS":
        errors.append("operator PASS status must retain the voltage-rail limitation")
    if passed.get("normal_firmware_restored") is not True or passed.get("diagnostic_left_installed") is not False:
        errors.append("operator PASS must restore normal firmware and leave no diagnostic installed")
    if passed.get("operator_result_exists") is not True:
        errors.append("operator PASS must persist the result beside its stage report")
    if passed_review.get("invoked") is not True or passed_review.get("selected") != "通过":
        errors.append("operator PASS report did not retain the selected button")
    if not isinstance(passed_review.get("note"), str) or not passed_review["note"].strip():
        errors.append("operator PASS report must retain a nonempty physical observation note")
    if passed.get("result_ids") != [
        "flash_white", "capture_white", "parse_white", "flash_normal_restore_after_review"
    ]:
        errors.append("operator PASS self-test step order drifted")
    if passed.get("result_statuses") != {
        "flash_white": "PASS",
        "capture_white": "PASS",
        "parse_white": "PASS",
        "flash_normal_restore_after_review": "PASS",
    }:
        errors.append("operator PASS self-test result matrix drifted")
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
        print("FAIL: WB55 replacement-display-FPC recovery runner preflight failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 staged replacement-display-FPC recovery runner verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
