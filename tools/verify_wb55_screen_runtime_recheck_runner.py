#!/usr/bin/env python3
"""Verify the current WB55 CEMP runtime recheck runner stays hardware-safe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_wb55_screen_runtime_recheck.ps1"
BUILD_MATRIX = ROOT / "docs" / "validation" / "companion-screen-wb55-build-matrix.json"
PROMOTION = ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-promotion.json"
ACTION_CARD = ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-hardware-action-card.json"
SERIAL_CAPTURE_PREFLIGHT = ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-serial-capture-preflight.json"
RUNTIME_LOGS = ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-recheck-logs.json"
DEFAULT_JSON = ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-recheck-runner.json"
EXPECTED_STEPS = ["flash_provision", "capture_provision", "flash_normal", "capture_normal"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_runner(*args: str, timeout: int = 60) -> dict[str, Any]:
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


def build_snapshot() -> dict[str, Any]:
    candidate = current_candidate()
    run_report_path = candidate.run_root / "runtime-recheck-run.json"
    dry_run_root = ROOT / ".cache" / "validation" / f"rev{candidate.revision}-runtime-runner-checkonly"
    dry_run_report_path = dry_run_root / "runtime-recheck-run.json"
    recovery_report_path = candidate.recovery_root / "runtime-recheck-run.json"
    runner_text = RUNNER.read_text(encoding="utf-8")
    build_matrix = load_json(BUILD_MATRIX)
    promotion = load_json(PROMOTION) if PROMOTION.exists() else {}
    action_card = load_json(ACTION_CARD) if ACTION_CARD.exists() else {}
    serial_preflight = load_json(SERIAL_CAPTURE_PREFLIGHT) if SERIAL_CAPTURE_PREFLIGHT.exists() else {}
    runtime_logs = load_json(RUNTIME_LOGS) if RUNTIME_LOGS.exists() else {}
    quiet_profile_recheck_required = (
        candidate.runtime_status == candidate.pass_status
        and runtime_logs.get("status") != "PASS"
    )

    dry = run_runner("-CheckOnly", "-OutRoot", str(dry_run_root))
    dry_text = dry["stdout"] + dry["stderr"]
    dry_report = load_json(dry_run_report_path) if dry_run_report_path.exists() else {}

    negative = run_runner("-Execute", timeout=30)
    negative_text = negative["stdout"] + negative["stderr"]

    recovery = run_runner(
        "-SelfTestRecovery",
        "-OutRoot",
        str(candidate.recovery_root),
    )
    recovery_report = load_json(recovery_report_path) if recovery_report_path.exists() else {}
    recovery_text = recovery["stdout"] + recovery["stderr"]

    expected_source_tokens = (
        "-CheckOnly",
        "-Execute",
        "-SelfTestRecovery",
        "-WorkflowLockHeld",
        "Companion-WB55",
        "ScreenAssetProvision",
        "capture_nucleo_serial.ps1",
        "flash_provision",
        "capture_provision",
        "flash_normal",
        "capture_normal",
        "$revision = [int]$resource.revision",
        "$clips = [int]$resource.clips",
        "$frames = [int]$resource.frames",
        "$quietInteractionProfileMarker = \"[build] interaction_profile=quiet",
        "$runtimeLogsPath = Join-Path $repoRoot \"docs\\validation\\companion-screen-wb55-runtime-recheck-logs.json\"",
        "$quietInteractionProfileRecheckRequired = (",
        "$defaultRunRoot = Join-Path $repoRoot \".cache\\validation\\rev$revision-runtime-current\"",
        "$checkOnlyRunRoot = Join-Path $repoRoot \".cache\\validation\\rev$revision-runtime-runner-checkonly\"",
        "elseif ($CheckOnly) { $checkOnlyRunRoot }",
        "revision=$revision",
        "clips=$clips frames=$frames",
        "queue_generation revision=$revision",
        "expected_provision_runtime_markers",
        "expected_normal_runtime_markers",
        "companion-screen-wb55-build-matrix.json",
        "build_logs_prove_all_variants",
        "queue_generation_compiles_in_all_variants",
        "screen_asset_provision_builds_current_external_assets",
    )
    result_statuses = {
        str(item.get("id")): str(item.get("status"))
        for item in recovery_report.get("results", [])
        if isinstance(item, dict)
    }
    result_codes = {
        str(item.get("id")): item.get("exit_code")
        for item in recovery_report.get("results", [])
        if isinstance(item, dict)
    }
    return {
        "schema_id": "companion.screen.wb55_runtime_recheck_runner.v1",
        "status": "PASS",
        "runner": rel(RUNNER),
        "candidate": {
            "revision": candidate.revision,
            "total_bytes": candidate.total_bytes,
            "pack_crc32": candidate.pack_crc32,
            "runtime_status": candidate.runtime_status,
            "clips": candidate.clips,
            "frames": candidate.frames,
            "quiet_interaction_profile_recheck_required": quiet_profile_recheck_required,
        },
        "safety_contract": {
            "check_only_is_non_hardware": all(token in runner_text for token in ("if ($CheckOnly)", "$checkOnlyRunRoot", "DRY-RUN", "exit 0")),
            "execute_requires_workflow_lock": (
                "if ($Execute -and -not $WorkflowLockHeld)" in runner_text
                and "aiw.ps1 with-lock -Resource Companion-WB55" in runner_text
            ),
            "provision_before_normal": runner_text.find("flash_provision") < runner_text.find("flash_normal"),
            "captures_both_boots": all(token in runner_text for token in ("capture_provision", "capture_normal")),
            "restores_normal_firmware_after_failure": all(
                token in runner_text
                for token in (
                    "$provisionFlashed = $false",
                    "$normalRestored = $false",
                    "flash_normal_after_failure",
                    "$provisionFlashed -and -not $normalRestored",
                    "$report.normal_firmware_restored = [bool]$normalRestored",
                )
            ),
            "runtime_resource_is_manifest_driven": all(
                token in runner_text
                for token in (
                    "$resource = $menuEvidence.resource_pack",
                    "$revision = [int]$resource.revision",
                    "$crc32 = [string]$resource.pack_crc32",
                    "$clips = [int]$resource.clips",
                    "$frames = [int]$resource.frames",
                    "$runtimeLogs = Get-Content -LiteralPath $runtimeLogsPath -Raw | ConvertFrom-Json",
                    "$quietInteractionProfileRecheckRequired = (",
                    "$pendingStatus = \"REVISION_${revision}_RUNTIME_RECHECK_PENDING\"",
                    "$passStatus = \"REVISION_${revision}_RUNTIME_PASS_HUMAN_VISUAL_PENDING\"",
                )
            ),
            "expected_runtime_markers_are_revision_driven": all(
                token in runner_text
                for token in (
                    "revision=$revision",
                    "clips=$clips frames=$frames",
                    "queue_generation revision=$revision",
                    "$quietInteractionProfileMarker",
                    "expected_provision_runtime_markers",
                    "expected_normal_runtime_markers",
                )
            ),
            "requires_wb55_build_matrix_pass": all(
                token in runner_text
                for token in (
                    "$buildMatrixPath",
                    "Expected WB55 build matrix PASS before runtime recheck.",
                    "dry_run_default",
                    "ssd1681_real_panel",
                    "screen_asset_provision",
                )
            ),
            "selftest_recovery_is_no_hardware": all(
                token in runner_text
                for token in (
                    "SelfTestRecovery uses stub commands only and must never be treated as hardware evidence.",
                    "SELFTEST: capture_provision failure",
                )
            ),
        },
        "source_tokens": {token: token in runner_text for token in expected_source_tokens},
        "dry_run": {
            "returncode": dry["returncode"],
            "current_sequence_banner": f"CHECK: rev{candidate.revision} WB55 runtime recheck sequence" in dry_text,
            "already_promoted_banner": f"CHECK: rev{candidate.revision} WB55 runtime evidence is already promoted" in dry_text,
            "current_resource_banner": (
                f"revision={candidate.revision} bytes={candidate.total_bytes} crc={candidate.pack_crc32}" in dry_text
            ),
            "run_report_path": rel(dry_run_report_path),
            "run_report_exists": dry_run_report_path.exists(),
            "run_report_schema": dry_report.get("schema"),
            "run_report_status": dry_report.get("status"),
            "run_report_resource": dry_report.get("resource", {}),
            "run_report_results_count": len(dry_report.get("results", [])),
            "run_report_steps": [
                str(item.get("id")) for item in dry_report.get("steps", []) if isinstance(item, dict)
            ],
            "run_report_build_matrix": dry_report.get("build_matrix", {}),
            "run_report_expected_runtime_markers": dry_report.get("expected_runtime_markers", []),
            "run_report_expected_provision_runtime_markers": dry_report.get("expected_provision_runtime_markers", []),
            "run_report_expected_normal_runtime_markers": dry_report.get("expected_normal_runtime_markers", []),
        },
        "execute_without_lock_negative": {
            "returncode": negative["returncode"],
            "refused_before_hardware": (
                negative["returncode"] != 0
                and "Refusing WB55 runtime recheck without workflow lock acknowledgement" in negative_text
                and "RUN:" not in negative_text
            ),
            "claim_scope": "negative_execute_lock_guard_no_hardware_claim",
        },
        "recovery_selftest": {
            "returncode": recovery["returncode"],
            "stdout_has_recovery": "RECOVERY: flash_normal_after_failure" in recovery_text,
            "report_path": rel(recovery_report_path),
            "report_exists": recovery_report_path.exists(),
            "report_status": recovery_report.get("status"),
            "normal_firmware_restored": recovery_report.get("normal_firmware_restored"),
            "result_ids": list(result_statuses),
            "result_statuses": result_statuses,
            "result_exit_codes": result_codes,
            "claim_scope": "stubbed_failure_recovery_no_hardware_claim",
        },
        "build_matrix": {
            "path": rel(BUILD_MATRIX),
            "status": build_matrix.get("status"),
            "variants": sorted(build_matrix.get("build_variants", {}).keys()),
            "screen_asset_provision_size": build_matrix.get("build_log_evidence", {})
            .get("screen_asset_provision", {})
            .get("size"),
        },
        "promotion_gate": {
            "path": rel(PROMOTION),
            "status": promotion.get("status"),
            "target_status": promotion.get("target_state", {}).get("status"),
        },
        "operator_action_card": {
            "path": rel(ACTION_CARD),
            "exists": ACTION_CARD.exists(),
            "status": action_card.get("status"),
        },
        "serial_capture_preflight": {
            "path": rel(SERIAL_CAPTURE_PREFLIGHT),
            "exists": SERIAL_CAPTURE_PREFLIGHT.exists(),
            "status": serial_preflight.get("status"),
        },
        "runtime_log_gate": {
            "path": rel(RUNTIME_LOGS),
            "status": runtime_logs.get("status"),
            "quiet_profile_recheck_required": quiet_profile_recheck_required,
        },
        "commands": [
            "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
            f"pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -SelfTestRecovery -OutRoot .\\.cache\\validation\\rev{candidate.revision}-runtime-recovery-selftest",
            f"pwsh -NoProfile -File C:\\Users\\Billy\\Desktop\\Denzic\\ai-collaboration-workflow\\scripts\\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose \"Companion WB55 rev{candidate.revision} screen runtime recheck\" -Run pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -Execute -WorkflowLockHeld",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py --apply",
        ],
    }


def verify(snapshot: dict[str, Any]) -> list[str]:
    candidate = current_candidate()
    errors: list[str] = []
    if snapshot.get("schema_id") != "companion.screen.wb55_runtime_recheck_runner.v1":
        errors.append("unexpected schema_id")
    active = snapshot.get("candidate", {})
    if active != {
        "revision": candidate.revision,
        "total_bytes": candidate.total_bytes,
        "pack_crc32": candidate.pack_crc32,
        "runtime_status": candidate.runtime_status,
        "clips": candidate.clips,
        "frames": candidate.frames,
        "quiet_interaction_profile_recheck_required": (
            candidate.runtime_status == candidate.pass_status
            and snapshot.get("runtime_log_gate", {}).get("status") != "PASS"
        ),
    }:
        errors.append("runner candidate must match the active CEMP manifest")
    for key, value in snapshot.get("safety_contract", {}).items():
        if value is not True:
            errors.append(f"safety_contract.{key} is not true")
    for token, present in snapshot.get("source_tokens", {}).items():
        if present is not True:
            errors.append(f"runner missing source token {token}")

    dry = snapshot.get("dry_run", {})
    if dry.get("returncode") != 0:
        errors.append("runner -CheckOnly failed")
    if (
        dry.get("current_sequence_banner") is not True
        and dry.get("already_promoted_banner") is not True
    ) or dry.get("current_resource_banner") is not True:
        errors.append("runner -CheckOnly did not report the active CEMP candidate")
    if dry.get("run_report_exists") is not True:
        errors.append("runner -CheckOnly must write a dry-run report")
    if dry.get("run_report_schema") != "companion.wb55_screen_runtime_recheck_run.v1":
        errors.append("dry-run report schema drifted")
    if dry.get("run_report_status") != "DRY-RUN":
        errors.append("dry-run report must not claim hardware execution")
    if dry.get("run_report_resource") != active:
        errors.append("dry-run report resource must match active CEMP")
    if dry.get("run_report_results_count") != 0:
        errors.append("dry-run report must have no executed steps")
    if dry.get("run_report_steps") != EXPECTED_STEPS:
        errors.append("dry-run report step order drifted")
    expected_provision_markers = list(candidate.common_markers) + [
        "external_store=ready",
        "preview_started name=idle",
    ]
    quiet_marker = (
        "[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 "
        "ft6336_threshold=0x70 touch_poll_active_ms=5 touch_poll_refresh_ms=5 "
        "refresh_policy=partial_x5_then_fast_cleanup"
    )
    expected_normal_markers = [
        "mount=ok",
        f"revision={candidate.revision}",
        f"clips={candidate.clips} frames={candidate.frames}",
        "expression_renderer=external_pack",
        "pet_behavior_selftest=pass failure_code=0",
        "touch-health] detected=1 identity=1 addr=0x38",
        f"queue_generation revision={candidate.revision}",
        "coherent_generation=1",
        "last_stale_discarded=",
        quiet_marker,
        "preview_started name=idle",
        "low_power_face completed=1 stop=allowed",
    ]
    if dry.get("run_report_expected_runtime_markers") != expected_provision_markers:
        errors.append("runtime provision markers must follow the active CEMP manifest")
    if dry.get("run_report_expected_provision_runtime_markers") != expected_provision_markers:
        errors.append("provision markers must include the current external-store runtime contract")
    if dry.get("run_report_expected_normal_runtime_markers") != expected_normal_markers:
        errors.append("normal markers must require only production-retained quiet interaction evidence")
    runtime_log_gate = snapshot.get("runtime_log_gate", {})
    if runtime_log_gate.get("path") != rel(RUNTIME_LOGS):
        errors.append("runner must record the current runtime-log gate")
    expected_quiet_profile_recheck = (
        candidate.runtime_status == candidate.pass_status
        and runtime_log_gate.get("status") != "PASS"
    )
    if runtime_log_gate.get("quiet_profile_recheck_required") != expected_quiet_profile_recheck:
        errors.append("runner quiet-profile recheck eligibility drifted from runtime-log status")

    build = snapshot.get("build_matrix", {})
    if build.get("path") != rel(BUILD_MATRIX) or build.get("status") != "PASS":
        errors.append("WB55 build matrix must pass before runtime recheck")
    if build.get("variants") != ["dry_run_default", "screen_asset_provision", "ssd1681_real_panel"]:
        errors.append("WB55 build matrix must retain all required variants")
    size = build.get("screen_asset_provision_size", {})
    if not isinstance(size, dict) or any(not isinstance(size.get(key), int) or size[key] < 0 for key in ("text", "data", "bss", "dec")):
        errors.append("ScreenAssetProvision build size must be present and non-negative")
    if size.get("text", 0) <= 0 or size.get("dec", 0) <= 0 or not isinstance(size.get("hex"), str):
        errors.append("ScreenAssetProvision build size must be valid")

    negative = snapshot.get("execute_without_lock_negative", {})
    if negative.get("returncode") == 0 or negative.get("refused_before_hardware") is not True:
        errors.append("runner -Execute must refuse before hardware without the workflow lock")
    recovery = snapshot.get("recovery_selftest", {})
    if recovery.get("returncode") == 0 or recovery.get("stdout_has_recovery") is not True:
        errors.append("recovery self-test must fail capture and restore normal firmware")
    if recovery.get("report_status") != "FAIL" or recovery.get("normal_firmware_restored") is not True:
        errors.append("recovery self-test report must prove normal firmware restoration")
    if recovery.get("result_ids") != ["flash_provision", "capture_provision", "flash_normal_after_failure"]:
        errors.append("recovery self-test step order drifted")
    if recovery.get("result_statuses") != {
        "flash_provision": "PASS",
        "capture_provision": "FAIL",
        "flash_normal_after_failure": "PASS",
    }:
        errors.append("recovery self-test step outcomes drifted")
    if recovery.get("result_exit_codes", {}).get("capture_provision") != 7:
        errors.append("recovery self-test capture failure exit code must remain 7")

    promotion = snapshot.get("promotion_gate", {})
    if promotion.get("target_status") != candidate.pass_status:
        errors.append("promotion target must follow the active CEMP revision")
    if candidate.runtime_status == candidate.pending_status and promotion.get("status") != "NO_GO_LOGS_NOT_PASS":
        errors.append("promotion must remain blocked until current runtime logs pass")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args()
    output = args.json if args.json.is_absolute() else ROOT / args.json
    snapshot = build_snapshot()
    errors = verify(snapshot)
    rendered = json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write and not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not output.exists():
            errors.append(f"missing {rel(output)}")
        elif output.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(output)}; rerun with --write")
    if errors:
        print("FAIL: WB55 runtime recheck runner verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 runtime recheck runner verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
