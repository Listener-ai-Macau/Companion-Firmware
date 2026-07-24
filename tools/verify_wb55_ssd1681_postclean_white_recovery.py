#!/usr/bin/env python3
"""Fail-closed static gate for official White post-clean plus exact raw restore."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_postclean_white_recovery.ps1"
WHITE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_official_full_diagnostic_white/Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
WHITE_PARSER = ROOT / "tools/verify_wb55_official_full_diagnostic_log.py"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
BACKUP_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BACKUP_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-r2-20260721.json"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OUT = ROOT / "docs/validation/companion-ssd1681-postclean-white-recovery-static-20260721.json"
EXPECTED = {
    WHITE: "F7CB7EE8C497CF1A01ACFF4BC921B43E274B0A934CA8B658AC24C34480F32925",
    BACKUP_A: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    BACKUP_B: "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C",
    SOURCE_AUDIT: "5395705759D9F149B0CCE4FCC5C576B78D3A13A5FBD45FF0F0799495736EF645",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def evaluate(runner: str, launcher: str) -> list[str]:
    errors: list[str] = []
    runner_tokens = {
        "mode_switch": "[switch]$PostCleanWhiteRecoveryOnly",
        "promptless_recovery": '$report.pre_execute_prompt.required = $false',
        "candidate_prompt_preserved": "if ($CustomMode2TransitionSafety) {",
        "zero_candidate": "if (-not $PostCleanWhiteRecoveryOnly)",
        "official_write": 'Operation "preclean-white-write"',
        "white_parser": "--pattern white",
        "postclean_artifact": 'postclean-white.json',
        "postclean_status": "PASS_POST_CANDIDATE_WHITE_CLEAN_EXACT_RAW_RESTORED",
        "raw_restore": 'Operation "restore-write-verify-upload"',
        "restore_upload": '"-u", "0x08000000", "0x80000", $restoreVerify',
        "normal_resume": "Post-restore normal application resumption was not proven.",
        "future_custom_postclean": 'Operation "postclean-white-write"',
        "future_fail_closed": "NO_GO_CUSTOM_MODE2_POSTCLEAN_FAILED_RESTORED",
    }
    launcher_tokens = {
        "mode": '"-PostCleanWhiteRecoveryOnly"',
        "fresh_root": "Post-clean output directory already exists; reuse is forbidden",
        "stdout": "-RedirectStandardOutput $stdout",
        "stderr": "-RedirectStandardError $stderr",
        "detached": '"STARTED_DETACHED"',
    }
    for name, token in runner_tokens.items():
        if token not in runner:
            errors.append(f"runner:{name}")
    for name, token in launcher_tokens.items():
        if token not in launcher:
            errors.append(f"launcher:{name}")
    if "Invoke-PostCleanRecoveryPrompt" in runner or "Companion R4 残留纯白清理确认" in runner:
        errors.append("recovery_must_be_promptless")
    if runner.find('Operation "preclean-white-write"') > runner.find('Operation "restore-write-verify-upload"'):
        errors.append("white_restore_order")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in [RUNNER, LAUNCHER, WHITE_PARSER, RESTORE, NORMAL, REGISTRY, *EXPECTED]:
        if not path.is_file():
            errors.append(f"missing:{path}")
    if errors:
        print("NO_GO_POSTCLEAN_STATIC")
        return 1
    for path, expected in EXPECTED.items():
        if sha(path) != expected:
            errors.append(f"hash:{path}")
    registry = REGISTRY.read_text(encoding="utf-8")
    if (
        "| COMP-REQ-293 |" not in registry
        or "| COMP-REQ-294 |" not in registry
        or "Routine deterministic official White pre-clean" not in registry
        or "raw Flash restore alone" not in registry
    ):
        errors.append("registry_contract")
    runner = RUNNER.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    errors.extend(evaluate(runner, launcher))
    fixtures = {
        "missing_future_postclean": runner.replace('Operation "postclean-white-write"', 'Operation "candidate-write"'),
        "missing_fail_closed": runner.replace("NO_GO_CUSTOM_MODE2_POSTCLEAN_FAILED_RESTORED", "PASS_IGNORED_POSTCLEAN"),
        "allows_reuse": launcher.replace("Post-clean output directory already exists; reuse is forbidden", "reuse accepted"),
        "adds_cleanup_prompt": runner.replace(
            'Operation "preclean-white-write"',
            'Invoke-PostCleanRecoveryPrompt\n        Operation "preclean-white-write"',
            1,
        ),
    }
    for name, source in fixtures.items():
        fixture_runner = source if name != "allows_reuse" else runner
        fixture_launcher = source if name == "allows_reuse" else launcher
        if not evaluate(fixture_runner, fixture_launcher):
            errors.append(f"negative_fixture:{name}")
    for path in (RUNNER, LAUNCHER):
        proc = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{path}' -Raw)); 'PASS'"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if proc.returncode != 0 or "PASS" not in proc.stdout:
            errors.append(f"powershell_parse:{path.name}")
    tests = {}
    for name, command in {
        "white_parser": [sys.executable, str(WHITE_PARSER), "--self-test"],
        "restore": [sys.executable, str(RESTORE), "--self-test"],
        "normal": [sys.executable, str(NORMAL), "--self-test"],
    }.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        tests[name] = {"exit_code": proc.returncode, "stdout": proc.stdout.strip()}
        if proc.returncode != 0:
            errors.append(f"test:{name}")
    report = {
        "schema_id": "companion.wb55.ssd1681_postclean_white_recovery_static.v1",
        "status": "PASS_POSTCLEAN_WHITE_RECOVERY_STATIC" if not errors else "NO_GO_POSTCLEAN_STATIC",
        "errors": errors,
        "hardware_contact": 0,
        "contract": {
            "official_white_image_sha256": EXPECTED[WHITE],
            "frame_command": "0x24",
            "frame_bytes": 5000,
            "control": "0xF7",
            "refresh": "0x20",
            "candidate_writes": 0,
            "raw_restore_sha256": EXPECTED[BACKUP_A],
            "future_custom_postclean_fail_closed": True,
        },
        "negative_fixtures": list(fixtures),
        "host_tests": tests,
        "production_allowed": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    for error in errors:
        print(f"FAIL: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
