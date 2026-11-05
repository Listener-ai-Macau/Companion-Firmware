#!/usr/bin/env python3
"""Generate the offline-only COMP-REQ-473 browser owner-review scope."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


VALIDATION_DIR = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
UPPER_RELATIVE = VALIDATION_DIR / "UPPER_MACHINE_READY.json"
RUNNER_RELATIVE = Path(
    "tools/faraday_upper_art/"
    "run_companion_browser_owner_review_comp_req_471.ps1"
)
SUPERVISOR_RELATIVE = Path(
    "tools/faraday_upper_art/"
    "supervise_companion_browser_owner_review_comp_req_471.ps1"
)
CHECKONLY_RELATIVE = VALIDATION_DIR / "owner-review-checkonly.json"
OWNER_RESULT_RELATIVE = VALIDATION_DIR / "owner-review.json"

EXPECTED_UPPER_SHA256 = (
    "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69"
)
EXPECTED_RUNNER_SHA256 = (
    "6739E7BDF6CEB8118CC8ED9E660D5FB193F110D36E5D84F3C152753D9A424C81"
)
EXPECTED_SUPERVISOR_SHA256 = (
    "E7E599F906886030B95B47A17B0ADA88F8648A232F2A45D0C86C901AD9096F87"
)
EXPECTED_CHECKONLY_SHA256 = (
    "21FCE148BBD11C68074F98EE10E8F1A75A0DD4D86FAC4F65EE7CB03CFFABDCC7"
)
EXPECTED_MACHINE_SHA256 = (
    "6A7EDAC4A9624842B154B717C090441E745AC6F65F8E73BC235E8E3C16D11EBD"
)
EXPECTED_PAGE_SHA256 = (
    "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
)
EXPECTED_FUTURE_COMMAND = (
    "pwsh -NoProfile -File "
    ".\\tools\\faraday_upper_art\\"
    "supervise_companion_browser_owner_review_comp_req_471.ps1 "
    "-Execute -OwnerStartAcknowledged"
)

VISIBLE_CHECKS = [
    {
        "id": "center_orientation_identity",
        "action": "Open the overall browser surface and inspect the centered rest face.",
        "pass_condition": (
            "The 200x200 screen is centered and oriented like the real display; "
            "the accepted V9 identity, pupils, and white highlights are intact."
        ),
    },
    {
        "id": "tap_drag_replacement",
        "action": (
            "Single-tap, then drag left/right/up/down and back to center."
        ),
        "pass_condition": (
            "Tap gives one deterministic expression/gaze response; drag "
            "continuously replaces the current gaze with no stale face, pupil, "
            "or highlight layer."
        ),
    },
    {
        "id": "double_tap_recording",
        "action": "Double-tap with mouse or touch.",
        "pass_condition": (
            "Recording preview is entered exactly once without microphone "
            "permission and exposes the accepted return path."
        ),
    },
    {
        "id": "hold_progress_menu",
        "action": (
            "Hold stationary through the ornament progress, then use the four "
            "root menu rows and Device > UI assets."
        ),
        "pass_condition": (
            "Progress remains compact and continuous; the completed hold enters "
            "the menu exactly once with the accepted menu assets."
        ),
    },
    {
        "id": "return_exclusivity",
        "action": "Return from both menu and recording to the expression face.",
        "pass_condition": (
            "Each return restores one centered face and at most one gaze/"
            "highlight; inactive menu and recording surfaces are absent."
        ),
    },
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.as_posix()} is not a JSON object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def owner_pass_allowed(
    *,
    result_file_exists: bool,
    result: dict[str, Any] | None,
    expected_prompt_contract: dict[str, Any],
) -> tuple[bool, str]:
    if not result_file_exists or result is None:
        return False, "matching owner-review.json is required"
    if (
        result.get("schema") != "companion.browser-owner-review.v1"
        or result.get("requirement") != "COMP-REQ-471"
    ):
        return False, "owner result schema or requirement mismatch"
    if (
        result.get("selected") != "\u901a\u8fc7"
        or result.get("status") != "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED"
    ):
        return False, "canonical owner selection is not pass"
    machine = result.get("machine_result")
    page = result.get("page")
    execution = result.get("execution")
    if (
        not isinstance(machine, dict)
        or machine.get("sha256") != EXPECTED_MACHINE_SHA256
        or machine.get("status_preserved") != "PASS"
        or not isinstance(page, dict)
        or page.get("sha256") != EXPECTED_PAGE_SHA256
        or not isinstance(execution, dict)
        or execution.get("canonical_prompt_count") != 1
        or execution.get("hardware_count") != 0
        or result.get("prompt_contract") != expected_prompt_contract
    ):
        return False, "owner result identity binding mismatch"
    return True, "hash-bound canonical owner pass"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )
    output_path = (
        args.output.resolve()
        if args.output and args.output.is_absolute()
        else repo_root
        / (
            args.output
            if args.output
            else VALIDATION_DIR / "owner-review-scope.json"
        )
    )

    upper_path = repo_root / UPPER_RELATIVE
    runner_path = repo_root / RUNNER_RELATIVE
    supervisor_path = repo_root / SUPERVISOR_RELATIVE
    checkonly_path = repo_root / CHECKONLY_RELATIVE
    owner_result_path = repo_root / OWNER_RESULT_RELATIVE

    identities = {
        "upper_machine_ready": {
            "path": UPPER_RELATIVE.as_posix(),
            "expected_sha256": EXPECTED_UPPER_SHA256,
            "observed_sha256": file_sha(upper_path),
        },
        "runner": {
            "path": RUNNER_RELATIVE.as_posix(),
            "expected_sha256": EXPECTED_RUNNER_SHA256,
            "observed_sha256": file_sha(runner_path),
        },
        "supervisor": {
            "path": SUPERVISOR_RELATIVE.as_posix(),
            "expected_sha256": EXPECTED_SUPERVISOR_SHA256,
            "observed_sha256": file_sha(supervisor_path),
        },
        "checkonly": {
            "path": CHECKONLY_RELATIVE.as_posix(),
            "expected_sha256": EXPECTED_CHECKONLY_SHA256,
            "observed_sha256": file_sha(checkonly_path),
        },
    }
    for value in identities.values():
        value["match"] = (
            value["observed_sha256"] == value["expected_sha256"]
        )

    upper = load_json(upper_path)
    checkonly = load_json(checkonly_path)
    generator_source = Path(__file__).resolve().read_text(encoding="utf-8")
    generator_tree = ast.parse(generator_source)
    imported_modules = {
        alias.name.split(".")[0]
        for node in ast.walk(generator_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (
            node.names
            if isinstance(node, ast.Import)
            else [ast.alias(name=node.module or "", asname=None)]
        )
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(generator_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden_modules = {
        "asyncio",
        "http",
        "os",
        "requests",
        "socket",
        "subprocess",
        "urllib",
        "webbrowser",
    }
    forbidden_calls = {
        "Popen",
        "run",
        "startfile",
        "system",
        "urlopen",
    }
    evidence_write_call_count = sum(
        1
        for node in ast.walk(generator_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "write_bytes"
    )
    offline_source_only = (
        not (imported_modules & forbidden_modules)
        and not (called_attributes & forbidden_calls)
        and evidence_write_call_count == 1
    )
    readiness = checkonly["readiness"]
    prompt_contract = readiness["prompt_contract"]
    owner_result_exists = owner_result_path.is_file()
    owner_result = load_json(owner_result_path) if owner_result_exists else None

    actual_owner_pass, actual_owner_reason = owner_pass_allowed(
        result_file_exists=owner_result_exists,
        result=owner_result,
        expected_prompt_contract=prompt_contract,
    )
    absent_pass, absent_reason = owner_pass_allowed(
        result_file_exists=False,
        result={
            "schema": "companion.browser-owner-review.v1",
            "requirement": "COMP-REQ-471",
            "status": "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED",
            "selected": "\u901a\u8fc7",
            "machine_result": {
                "sha256": EXPECTED_MACHINE_SHA256,
                "status_preserved": "PASS",
            },
            "page": {"sha256": EXPECTED_PAGE_SHA256},
            "prompt_contract": prompt_contract,
            "execution": {"canonical_prompt_count": 1, "hardware_count": 0},
        },
        expected_prompt_contract=prompt_contract,
    )
    drift_pass, drift_reason = owner_pass_allowed(
        result_file_exists=True,
        result={
            "schema": "companion.browser-owner-review.v1",
            "requirement": "COMP-REQ-471",
            "status": "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED",
            "selected": "\u901a\u8fc7",
            "machine_result": {
                "sha256": "0" * 64,
                "status_preserved": "PASS",
            },
            "page": {"sha256": EXPECTED_PAGE_SHA256},
            "prompt_contract": prompt_contract,
            "execution": {"canonical_prompt_count": 1, "hardware_count": 0},
        },
        expected_prompt_contract=prompt_contract,
    )
    fail_selection_pass, fail_selection_reason = owner_pass_allowed(
        result_file_exists=True,
        result={
            "schema": "companion.browser-owner-review.v1",
            "requirement": "COMP-REQ-471",
            "status": "FAIL_OWNER_BROWSER_EXPERIENCE_RETURN_TO_ITERATION",
            "selected": "\u5931\u8d25",
            "machine_result": {
                "sha256": EXPECTED_MACHINE_SHA256,
                "status_preserved": "PASS",
            },
            "page": {"sha256": EXPECTED_PAGE_SHA256},
            "prompt_contract": prompt_contract,
            "execution": {"canonical_prompt_count": 1, "hardware_count": 0},
        },
        expected_prompt_contract=prompt_contract,
    )

    prompt_exact = (
        prompt_contract["instance_count"] == 1
        and prompt_contract["buttons"] == ["\u901a\u8fc7", "\u5931\u8d25"]
        and prompt_contract["note_allowed"] is True
        and readiness["canonical_aiw"]["invoked"] is False
        and checkonly["exact_future_execute_command"]
        == EXPECTED_FUTURE_COMMAND
    )
    upper_offline_pass = (
        upper["status"] == "UPPER_MACHINE_READY"
        and upper["default_off"] is True
        and upper["integration_authorized"] is False
        and not upper["failed"]
        and all(value is True for value in upper["checks"].values())
        and upper["owner_boundary"]["owner_result_exists"] is False
        and upper["owner_boundary"]["execute_authorized"] is False
        and upper["owner_boundary"]["operator_prompt_invoked"] is False
        and upper["owner_boundary"]["server_or_browser_started"] is False
        and upper["side_effect_counters"]["execute"] == 0
        and upper["side_effect_counters"]["prompt"] == 0
        and upper["side_effect_counters"]["server"] == 0
        and upper["side_effect_counters"]["hardware"] == 0
    )
    checks = {
        "all_identities_match": all(
            item["match"] is True for item in identities.values()
        ),
        "upper_is_exact_offline_machine_pass": upper_offline_pass,
        "visible_scope_is_fixed_five_checks": (
            len(VISIBLE_CHECKS) == 5
            and len({item["id"] for item in VISIBLE_CHECKS}) == 5
        ),
        "canonical_single_chinese_prompt_contract": prompt_exact,
        "owner_result_absent": owner_result_exists is False,
        "owner_pass_not_claimed": actual_owner_pass is False,
        "owner_pass_requires_existing_result": absent_pass is False,
        "drifted_result_rejected": drift_pass is False,
        "failure_selection_rejected": fail_selection_pass is False,
        "no_execute_or_runtime_side_effect": offline_source_only,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = (
        "READY_FOR_SINGLE_OWNER_REVIEW_NOT_OWNER_PASS"
        if not failed
        else "NO_GO_OWNER_REVIEW_SCOPE"
    )
    artifact = {
        "schema": "companion.browser-owner-review-scope.v1",
        "requirement": "COMP-REQ-473",
        "status": status,
        "default_off": True,
        "owner_pass": False,
        "owner_acceptance_status": "NOT_RUN",
        "identities": identities,
        "human_visible_checks": VISIBLE_CHECKS,
        "canonical_single_prompt": {
            "supervised_future_command": EXPECTED_FUTURE_COMMAND,
            "command_executed": False,
            "aiw_subcommand": "operator-prompt",
            "title": prompt_contract["title"],
            "buttons": prompt_contract["buttons"],
            "note_allowed": prompt_contract["note_allowed"],
            "instance_count": prompt_contract["instance_count"],
            "message": prompt_contract["message"],
        },
        "owner_pass_gate": {
            "result_path": OWNER_RESULT_RELATIVE.as_posix(),
            "result_exists": owner_result_exists,
            "actual_owner_pass_allowed": actual_owner_pass,
            "actual_reason": actual_owner_reason,
            "required_selection": "\u901a\u8fc7",
            "required_scope_identities": {
                "upper_machine_ready_sha256": EXPECTED_UPPER_SHA256,
                "runner_sha256": EXPECTED_RUNNER_SHA256,
                "supervisor_sha256": EXPECTED_SUPERVISOR_SHA256,
            },
            "required_existing_runner_result_fields": {
                "schema": "companion.browser-owner-review.v1",
                "requirement": "COMP-REQ-471",
                "status": "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED",
                "machine_result_sha256": EXPECTED_MACHINE_SHA256,
                "page_sha256": EXPECTED_PAGE_SHA256,
                "canonical_prompt_count": 1,
                "hardware_count": 0,
            },
        },
        "fail_closed_probes": [
            {
                "id": "fabricated_pass_without_owner_result_file",
                "accepted": absent_pass,
                "reason": absent_reason,
                "pass": absent_pass is False,
            },
            {
                "id": "pass_with_drifted_upper_binding",
                "accepted": drift_pass,
                "reason": drift_reason,
                "pass": drift_pass is False,
            },
            {
                "id": "canonical_failure_selection",
                "accepted": fail_selection_pass,
                "reason": fail_selection_reason,
                "pass": fail_selection_pass is False,
            },
        ],
        "checks": checks,
        "failed": failed,
        "side_effect_counters": {
            "execute": 0,
            "process": 0,
            "server_probe": 0,
            "server_start": 0,
            "browser_start": 0,
            "popup": 0,
            "operator_prompt": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "evidence_artifact_write": 1,
        },
        "generator_static_boundary": {
            "offline_source_only": offline_source_only,
            "forbidden_imports_found": sorted(
                imported_modules & forbidden_modules
            ),
            "forbidden_calls_found": sorted(
                called_attributes & forbidden_calls
            ),
            "evidence_write_call_count": evidence_write_call_count,
        },
        "boundaries": [
            "This artifact is browser owner-review readiness, not owner PASS.",
            "Only a future existing hash-bound canonical owner-review.json may carry owner selection.",
            "No server, browser, popup, prompt, hardware, lower, Platform, production, or redraw action is authorized.",
        ],
        "generator": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "status": status,
                "checks": f"{len(checks) - len(failed)}/{len(checks)}",
                "artifact_sha256": file_sha(output_path),
                "owner_result_exists": owner_result_exists,
                "owner_pass": False,
            },
            sort_keys=True,
        )
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
