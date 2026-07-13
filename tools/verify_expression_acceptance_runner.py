#!/usr/bin/env python3
"""Verify the Companion screen expression aggregate acceptance runner."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-acceptance-runner.json")
SCHEMA_ID = "companion.pendant.screen_acceptance_runner.v1"

RUNNER = REPO_ROOT / "tools" / "run_expression_acceptance.py"
REPORT_RENDERER = REPO_ROOT / "tools" / "render_expression_acceptance_report.py"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
ACCEPTANCE_REPORT = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-report.md"
PRE_ACCEPTANCE_HEALTH = REPO_ROOT / "docs" / "validation" / "companion-screen-pre-acceptance-health.json"
TOUCH_REVIEW_RECORD = REPO_ROOT / "docs" / "validation" / "companion-screen-wb55-touch-visual-review-record.json"
RUNTIME_RECHECK_LOGS = REPO_ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-recheck-logs.json"
RUNTIME_PROMOTION = REPO_ROOT / "docs" / "validation" / "companion-screen-wb55-runtime-promotion.json"
DRY_RUN_REPORT = REPO_ROOT / ".cache" / "validation" / "companion-screen-acceptance-dry-run.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
CANDIDATE = current_candidate()
RUNTIME_GATE_ID = f"wb55_rev{CANDIDATE.revision}_runtime_recheck"


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


def load_index(errors: list[str]) -> dict[str, Any]:
    text = read(ACCEPTANCE_INDEX, errors)
    if not text:
        return {}
    return json.loads(text)


def unique_commands(index: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    seen: set[str] = set()
    for item in index.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("status") not in {"PASS", "DEFERRED_HARDWARE", "PENDING_HUMAN"}:
            continue
        for command in item.get("validation_commands", []):
            command_text = str(command)
            if command_text not in seen:
                seen.add(command_text)
                commands.append(command_text)
    return commands


def run_report_renderer_check() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(REPORT_RENDERER)],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def run_acceptance_dry_run() -> dict[str, Any]:
    DRY_RUN_REPORT.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--dry-run",
            "--skip-build",
            "--output",
            str(DRY_RUN_REPORT),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    report = json.loads(DRY_RUN_REPORT.read_text(encoding="utf-8")) if DRY_RUN_REPORT.exists() else {}
    return {
        "command": "python .\\tools\\run_expression_acceptance.py --dry-run --skip-build --output .\\.cache\\validation\\companion-screen-acceptance-dry-run.json",
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "report": report,
    }


def build_fixture() -> dict[str, Any]:
    index = json.loads(ACCEPTANCE_INDEX.read_text(encoding="utf-8"))
    pre_acceptance = json.loads(PRE_ACCEPTANCE_HEALTH.read_text(encoding="utf-8"))
    review_record = json.loads(TOUCH_REVIEW_RECORD.read_text(encoding="utf-8"))
    runtime_logs = json.loads(RUNTIME_RECHECK_LOGS.read_text(encoding="utf-8"))
    promotion = json.loads(RUNTIME_PROMOTION.read_text(encoding="utf-8"))
    dry_run_check = run_acceptance_dry_run()
    dry_run = dry_run_check["report"]
    commands = unique_commands(index)
    report_check = run_report_renderer_check()
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "runner": rel(RUNNER),
            "report_renderer": rel(REPORT_RENDERER),
            "acceptance_index": rel(ACCEPTANCE_INDEX),
            "acceptance_report": rel(ACCEPTANCE_REPORT),
            "pre_acceptance_health": rel(PRE_ACCEPTANCE_HEALTH),
            "touch_review_record": rel(TOUCH_REVIEW_RECORD),
            "runtime_recheck_logs": rel(RUNTIME_RECHECK_LOGS),
            "runtime_promotion": rel(RUNTIME_PROMOTION),
            "dry_run_report": rel(DRY_RUN_REPORT),
            "screen_acceptance": rel(SCREEN_DOC),
            "bringup_steps": rel(BRINGUP_STEPS),
        },
        "runner_contract": {
            "input_index_schema": index.get("schema_id"),
            "default_statuses": ["DEFERRED_HARDWARE", "PASS", "PENDING_HUMAN"],
            "deduplicates_validation_commands": True,
            "supports_dry_run": True,
            "supports_pass_only": True,
            "supports_skip_build": True,
            "supports_continue_on_fail": True,
            "requires_empty_stdout_for_third_party_diff": True,
            "writes_json_report": True,
            "has_human_markdown_report": True,
        },
        "report_schema": {
            "schema_id": "companion.pendant.screen_acceptance_run.v1",
            "required_fields": [
                "status",
                "index_summary",
                "included_statuses",
                "unique_command_count",
                "executed_command_count",
                "command_status_by_item",
                "commands",
            ],
            "terminal_statuses": ["PASS", "FAIL", "DRY_RUN", "PARTIAL"],
        },
        "acceptance_index_snapshot": {
            "summary": index.get("summary", {}),
            "item_count": len(index.get("items", [])),
            "deferred_gate": index.get("summary", {}).get("next_hardware_gate"),
            "human_gate": index.get("summary", {}).get("next_human_gate"),
            "unique_validation_command_count": len(commands),
            "has_build_command": any("build_nucleo_bringup.ps1" in command for command in commands),
            "has_third_party_guard": any(
                command.replace("/", "\\").lower().startswith("git diff --name-only --")
                and "third_party\\stm32cube" in command.replace("/", "\\").lower()
                for command in commands
            ),
            "has_touch_review_record_verifier": any(
                "verify_wb55_touch_visual_review_record.py" in command for command in commands
            ),
            "has_runtime_recheck_log_verifier": any(
                "verify_wb55_screen_runtime_recheck_logs.py" in command for command in commands
            ),
        },
        "dry_run_snapshot": {
            "path": rel(DRY_RUN_REPORT),
            "command": dry_run_check["command"],
            "returncode": dry_run_check["returncode"],
            "stdout_tail": dry_run_check["stdout_tail"],
            "stderr_tail": dry_run_check["stderr_tail"],
            "schema_id": dry_run.get("schema_id"),
            "status": dry_run.get("status"),
            "dry_run": dry_run.get("dry_run"),
            "skip_build": dry_run.get("skip_build"),
            "included_statuses": dry_run.get("included_statuses", []),
            "index_summary": dry_run.get("index_summary", {}),
            "unique_command_count": dry_run.get("unique_command_count"),
            "executed_command_count": dry_run.get("executed_command_count"),
            "skip_count": dry_run.get("skip_count"),
            "runtime_recheck_status": dry_run.get("command_status_by_item", {}).get(RUNTIME_GATE_ID),
            "touch_visual_acceptance_status": dry_run.get("command_status_by_item", {}).get("wb55_touch_visual_acceptance"),
            "runtime_recheck_commands": [
                {
                    "command": command.get("command"),
                    "status": command.get("status"),
                    "item_ids": command.get("item_ids", []),
                }
                for command in dry_run.get("commands", [])
                if RUNTIME_GATE_ID in command.get("item_ids", [])
            ],
        },
        "touch_visual_gate_snapshot": {
            "gate_id": "wb55_touch_visual_acceptance",
            "pre_acceptance_status": pre_acceptance.get("status"),
            "review_record_status": review_record.get("status"),
            "review_record_publishable_pass_allowed": review_record.get("publishable_pass_allowed"),
            "review_record_open_item_count": len(review_record.get("open_items", [])),
            "runtime_recheck_status": runtime_logs.get("status"),
            "runtime_promotion_status": promotion.get("status"),
            "human_review_start_rule": (
                f"operator must explicitly say 开始验收 after rev{CANDIDATE.revision} machine preflight passes"
            ),
        },
        "acceptance_report_check": {
            "command": "python .\\tools\\render_expression_acceptance_report.py",
            "returncode": report_check["returncode"],
            "stdout": report_check["stdout"],
            "stderr": report_check["stderr"],
            "verified_current": report_check["returncode"] == 0,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_acceptance_runner.py",
            "python .\\tools\\render_expression_acceptance_report.py",
            "python .\\tools\\run_expression_acceptance.py --dry-run --skip-build --output .\\.cache\\validation\\companion-screen-acceptance-dry-run.json",
            "python .\\tools\\verify_expression_acceptance_index.py",
        ],
    }


def check_runner_code(errors: list[str]) -> None:
    text = read(RUNNER, errors)
    for token in [
        "DEFAULT_INDEX",
        "DEFAULT_STATUSES = {\"PASS\", \"DEFERRED_HARDWARE\", \"PENDING_HUMAN\"}",
        "def collect_commands",
        "commands.setdefault",
        "def requires_empty_stdout",
        "git diff --name-only --",
        "third_party\\\\stm32cube",
        "def command_status_by_item",
        "subprocess.run",
        "shell=True",
        "SKIPPED_DRY_RUN",
        "--dry-run",
        "--pass-only",
        "--skip-build",
        "--continue-on-fail",
        "schema_id\": \"companion.pendant.screen_acceptance_run.v1",
        "command_status_by_item",
        "FAIL_NONEMPTY_STDOUT",
    ]:
        require(token in text, f"acceptance runner missing code anchor {token}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected acceptance runner fixture schema", errors)
    require(data.get("status") == "PASS", "acceptance runner fixture must be PASS", errors)
    contract = data.get("runner_contract", {})
    for token in [
        "deduplicates_validation_commands",
        "supports_dry_run",
        "supports_pass_only",
        "supports_skip_build",
        "supports_continue_on_fail",
        "requires_empty_stdout_for_third_party_diff",
        "writes_json_report",
        "has_human_markdown_report",
    ]:
        require(contract.get(token) is True, f"runner contract missing {token}", errors)
    snapshot = data.get("acceptance_index_snapshot", {})
    require(snapshot.get("item_count", 0) >= 25, "runner fixture item snapshot unexpectedly small", errors)
    require(
        snapshot.get("deferred_gate") == RUNTIME_GATE_ID,
        "runner fixture must expose the current runtime hardware gate",
        errors,
    )
    require(snapshot.get("human_gate") == "wb55_touch_visual_acceptance", "runner fixture missing focused human gate", errors)
    require(snapshot.get("unique_validation_command_count", 0) >= 20, "runner fixture command snapshot unexpectedly small", errors)
    require(snapshot.get("has_build_command") is True, "runner fixture must see WB55 build command", errors)
    require(snapshot.get("has_third_party_guard") is True, "runner fixture must see third-party guard command", errors)
    require(
        snapshot.get("has_touch_review_record_verifier") is True,
        "runner fixture must see the touch visual review record verifier",
        errors,
    )
    require(
        snapshot.get("has_runtime_recheck_log_verifier") is True,
        "runner fixture must see the active runtime recheck log verifier",
        errors,
    )
    dry_run = data.get("dry_run_snapshot", {})
    require(dry_run.get("returncode") == 0, "dry-run command must return zero", errors)
    require("summary: status=DRY_RUN" in str(dry_run.get("stdout_tail", "")), "dry-run stdout must include DRY_RUN summary", errors)
    require(not str(dry_run.get("stderr_tail", "")).strip(), "dry-run stderr must be empty", errors)
    require(
        dry_run.get("schema_id") == "companion.pendant.screen_acceptance_run.v1",
        "dry-run snapshot schema drifted",
        errors,
    )
    require(dry_run.get("status") == "DRY_RUN", "dry-run snapshot must remain DRY_RUN", errors)
    require(dry_run.get("dry_run") is True, "dry-run snapshot must record dry_run=true", errors)
    require(dry_run.get("skip_build") is True, "dry-run snapshot must record skip_build=true", errors)
    require(dry_run.get("runtime_recheck_status") == "SKIPPED_DRY_RUN", "active runtime recheck must be skipped in dry-run", errors)
    require(dry_run.get("touch_visual_acceptance_status") == "SKIPPED_DRY_RUN", "touch visual acceptance must be skipped in dry-run", errors)
    require(dry_run.get("unique_command_count") == dry_run.get("executed_command_count"), "dry-run must enumerate every selected command", errors)
    require(dry_run.get("skip_count") == dry_run.get("executed_command_count"), "dry-run must skip every selected command", errors)
    runtime_commands = dry_run.get("runtime_recheck_commands", [])
    require(len(runtime_commands) >= 5, "dry-run must list active runtime recheck commands", errors)
    for command in runtime_commands:
        require(command.get("status") == "SKIPPED_DRY_RUN", f"dry-run executed runtime command {command.get('command')}", errors)
    for token in [
        "verify_wb55_screen_runtime_recheck_runner.py",
        "render_wb55_runtime_hardware_action_card.py",
        "verify_wb55_runtime_flash_preflight.py",
        "verify_wb55_runtime_serial_capture_preflight.py",
        "run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
        "verify_wb55_screen_runtime_recheck_logs.py",
        "promote_wb55_screen_runtime_recheck.py",
    ]:
        require(
            any(token in str(command.get("command", "")) for command in runtime_commands),
            f"dry-run runtime command list missing {token}",
            errors,
        )
    touch_gate = data.get("touch_visual_gate_snapshot", {})
    require(
        touch_gate.get("gate_id") == "wb55_touch_visual_acceptance",
        "runner fixture touch gate id drifted",
        errors,
    )
    require(
        touch_gate.get("pre_acceptance_status") == "NO_GO_RUNTIME_RECHECK_PENDING",
        "runner fixture must preserve active runtime pending pre-acceptance state",
        errors,
    )
    require(
        touch_gate.get("review_record_status") == "NO_GO_NOT_STARTED",
        "runner fixture must preserve not-started human review record state",
        errors,
    )
    require(
        touch_gate.get("review_record_publishable_pass_allowed") is False,
        "runner fixture must not allow publishable PASS before review",
        errors,
    )
    require(
        touch_gate.get("review_record_open_item_count") == 8,
        "runner fixture must keep all eight touch/visual steps open before review",
        errors,
    )
    require(
        touch_gate.get("runtime_recheck_status") == "NO_GO_MISSING_RUNTIME_LOGS",
        "runner fixture must preserve missing active runtime logs state",
        errors,
    )
    require(
        touch_gate.get("runtime_promotion_status") == "NO_GO_LOGS_NOT_PASS",
        "runner fixture must preserve runtime promotion NO_GO state",
        errors,
    )
    require(
        "开始验收" in str(touch_gate.get("human_review_start_rule", "")),
        "runner fixture must keep explicit human review start rule",
        errors,
    )
    report_check = data.get("acceptance_report_check", {})
    require(report_check.get("verified_current") is True, "acceptance report renderer must verify report is current", errors)
    require(report_check.get("returncode") == 0, "acceptance report renderer returned non-zero", errors)
    require(
        "Companion screen acceptance report verified" in str(report_check.get("stdout", "")),
        "acceptance report check missing PASS stdout",
        errors,
    )
    report = data.get("report_schema", {})
    for field in ["status", "index_summary", "command_status_by_item", "commands"]:
        require(field in report.get("required_fields", []), f"runner report schema missing {field}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    bringup = read(BRINGUP_STEPS, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "run_expression_acceptance.py",
        "verify_expression_acceptance_runner.py",
        "render_expression_acceptance_report.py",
        "companion-screen-acceptance-runner.json",
        "companion-screen-acceptance-report.md",
        "--dry-run",
        "--skip-build",
    ]:
        require(token in screen_doc, f"screen doc missing acceptance runner anchor {token}", errors)
    for token in [
        "run_expression_acceptance.py",
        "companion-screen-acceptance-dry-run.json",
    ]:
        require(token in bringup, f"bringup steps missing acceptance runner anchor {token}", errors)
    require(fixture_rel in index_text, "acceptance index must link acceptance runner fixture", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if item.get("id") == "screen_acceptance_runner"]
        require(len(items) == 1, "acceptance index must contain one screen_acceptance_runner item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "screen_acceptance_runner item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "screen_acceptance_runner item missing fixture", errors)
            require(
                rel(ACCEPTANCE_REPORT) in item.get("evidence_paths", []),
                "screen_acceptance_runner item missing human report",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_acceptance_runner.py" in item.get("validation_commands", []),
                "screen_acceptance_runner item missing verifier command",
                errors,
            )
            require(
                "python .\\tools\\render_expression_acceptance_report.py" in item.get("validation_commands", []),
                "screen_acceptance_runner item missing report render command",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing acceptance runner fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic acceptance runner JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    errors: list[str] = []

    if not ACCEPTANCE_INDEX.exists():
        errors.append(f"missing acceptance index {rel(ACCEPTANCE_INDEX)}")
        expected: dict[str, Any] = {}
    else:
        expected = build_fixture()
        check_fixture_data(expected, errors)

    check_runner_code(errors)
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen acceptance runner checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen acceptance runner verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
