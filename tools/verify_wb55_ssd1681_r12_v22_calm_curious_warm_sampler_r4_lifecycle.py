"""Fail-closed offline lifecycle evidence for the reviewed R12 r4 CheckOnly run."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_RUN = ROOT / ".cache/validation/wb55-r12-v22-calm-curious-warm-sampler-r4-checkonly-primary-review-20260722-r1"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r12_v22_calm_curious_warm_sampler"
CANDIDATE_HEX = BUILD / "Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex"
RUNNER = ROOT / "tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1"
MONITOR = ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1"
SUPERVISOR = ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt_r4.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r4.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r4-lifecycle-20260722.json"

EXPECTED_HEX_SHA256 = "4B7558F08BA5A188615D2B8B6A169F67BADA127215FF4DC2ABA93893B8323A42"
READY = "READY_NO_HARDWARE_CONTACT"
LAUNCH_ZERO_FIELDS = (
    "hardware_contact",
    "write_counter_sum",
    "programmer_calls",
    "serial_open_count",
    "reset_count",
    "refresh_count",
    "popup_count",
    "retry_count",
)
STAGE_ZERO_FIELDS = (
    "serial_capture_processes",
    "preclean_programmer_processes",
    "preclean_write_calls",
    "preclean_panel_writes",
    "preclean_panel_refresh_commands",
    "preclean_panel_busy_waits",
    "postclean_programmer_processes",
    "postclean_write_calls",
    "postclean_panel_writes",
    "postclean_panel_refresh_commands",
    "postclean_panel_busy_waits",
    "candidate_programmer_processes",
    "candidate_write_calls",
    "restore_programmer_processes",
    "restore_write_calls",
    "restore_verify_operations",
    "restore_upload_calls",
    "restore_reset_arguments",
    "panel_writes",
    "panel_refresh_commands",
    "panel_hard_resets",
    "panel_busy_waits",
    "automatic_retries",
)
TOOL_PATHS = {
    "runner": RUNNER,
    "monitor": MONITOR,
    "supervisor": SUPERVISOR,
    "launcher": LAUNCHER,
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def same_path(actual: Any, expected: Path) -> bool:
    if not isinstance(actual, (str, os.PathLike)) or not str(actual):
        return False
    return os.path.normcase(os.path.abspath(str(actual))) == os.path.normcase(str(expected.resolve()))


def argument_value(arguments: Any, name: str) -> Any:
    if not isinstance(arguments, list) or arguments.count(name) != 1:
        return None
    index = arguments.index(name)
    return arguments[index + 1] if index + 1 < len(arguments) else None


def validate_checkonly(
    launch: dict[str, Any],
    stage: dict[str, Any],
    current_hex_sha256: str,
) -> dict[str, bool]:
    arguments = launch.get("arguments")
    counters = stage.get("counters")
    candidate = stage.get("images", {}).get("candidate", {})
    checkonly = stage.get("checkonly", {})
    children = checkonly.get("children")
    children_by_name = {
        child.get("name"): child
        for child in children
        if isinstance(child, dict) and isinstance(child.get("name"), str)
    } if isinstance(children, list) else {}
    expected_child_status = {
        "monitor": "READY_NO_HARDWARE_CONTACT",
        "supervisor": "READY_NO_PROMPT",
    }
    child_contract = (
        isinstance(children, list)
        and len(children) == 2
        and set(children_by_name) == set(expected_child_status)
        and all(
            children_by_name[name].get("exit_code") == 0
            and children_by_name[name].get("observed_process_exit_code") == 0
            and children_by_name[name].get("child_exited") is True
            and children_by_name[name].get("evidence_status") == status
            and same_path(Path(children_by_name[name].get("stdout", "")).parent.parent, ROOT_RUN)
            and same_path(Path(children_by_name[name].get("stderr", "")).parent.parent, ROOT_RUN)
            for name, status in expected_child_status.items()
        )
    )
    return {
        "current_hex_matches_primary_review_sha256": current_hex_sha256 == EXPECTED_HEX_SHA256,
        "persistent_launcher_ready": launch.get("status") == READY,
        "persistent_launcher_mode_check_only": launch.get("mode") == "check_only",
        "persistent_launcher_exit_zero_and_exited": launch.get("exit_code") == 0 and launch.get("child_exited") is True,
        "persistent_launcher_stage_ready": launch.get("stage_status") == READY,
        "persistent_launcher_all_counters_zero": all(launch.get(key) == 0 for key in LAUNCH_ZERO_FIELDS),
        "persistent_launcher_no_authorization": launch.get("authorization_artifact") is None and launch.get("authorization_hashes") is None,
        "persistent_launcher_runner_path_current": same_path(launch.get("runner"), RUNNER),
        "persistent_launcher_output_root_current": same_path(launch.get("output_root"), ROOT_RUN),
        "persistent_launcher_arguments_current": (
            isinstance(arguments, list)
            and arguments.count("-CheckOnly") == 1
            and arguments.count("-R12Sampler") == 1
            and same_path(argument_value(arguments, "-File"), RUNNER)
            and same_path(argument_value(arguments, "-OutRoot"), ROOT_RUN)
        ),
        "stage_ready": stage.get("status") == READY,
        "stage_mode_check_only": stage.get("mode") == "check_only",
        "stage_hardware_contact_zero": stage.get("hardware_contact") == 0,
        "stage_errors_clear": stage.get("error") is None and stage.get("controller_error") is None and stage.get("restore_error") is None,
        "stage_authorization_none": stage.get("authorization") is None,
        "stage_programmer_calls_empty": stage.get("programmer_calls") == [],
        "stage_counter_set_complete": isinstance(counters, dict) and set(counters) == set(STAGE_ZERO_FIELDS),
        "stage_all_counters_zero": (
            isinstance(counters, dict)
            and set(counters) == set(STAGE_ZERO_FIELDS)
            and all(type(counters[key]) is int and counters[key] == 0 for key in STAGE_ZERO_FIELDS)
        ),
        "stage_candidate_path_current": same_path(candidate.get("path"), CANDIDATE_HEX),
        "stage_candidate_sha_matches_current_hex": candidate.get("sha256") == current_hex_sha256,
        "stage_candidate_required_sha_matches_current_hex": candidate.get("required_sha256") == current_hex_sha256,
        "stage_checkonly_children_complete": child_contract,
        "stage_fixed_ring": checkonly.get("telemetry_ring_bytes") == 65536 and checkonly.get("telemetry_ring_fixed") is True,
        "stage_popup_zero": checkonly.get("popup_count") == 0,
        "stage_retry_zero": checkonly.get("retry_count") == 0,
    }


def stale_candidate_hash_selftest(
    launch: dict[str, Any],
    stage: dict[str, Any],
    current_hex_sha256: str,
) -> dict[str, Any]:
    mutated = copy.deepcopy(stage)
    mutated["images"]["candidate"]["sha256"] = "0" * 64
    checks = validate_checkonly(launch, mutated, current_hex_sha256)
    rejected_invariant = checks["stage_candidate_sha_matches_current_hex"] is False
    no_go = rejected_invariant and not all(checks.values())
    return {
        "fixture": "stale_checkonly_candidate_sha256",
        "mutated_candidate_sha256": "0" * 64,
        "target_invariant": "stage_candidate_sha_matches_current_hex",
        "target_invariant_false": rejected_invariant,
        "resulting_status": "NO_GO_STALE_CHECKONLY_CANDIDATE_HASH" if no_go else "UNSAFE_PASS",
        "pass": no_go,
    }


def _hash_references(value: Any, tool: str, path: tuple[str, ...] = ()) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (str(key),)
            key_lower = str(key).lower()
            path_lower = tuple(part.lower() for part in child_path)
            explicit_key = key_lower in {f"{tool}_sha256", f"{tool}_hash", f"{tool}_hash_sha256"}
            scoped_sha = key_lower == "sha256" and tool in path_lower[:-1]
            if isinstance(child, str) and re.fullmatch(r"[0-9a-fA-F]{64}", child) and (explicit_key or scoped_sha):
                found.append({"json_path": ".".join(child_path), "sha256": child.upper()})
            found.extend(_hash_references(child, tool, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_hash_references(child, tool, path + (str(index),)))
    return found


def checkonly_tool_hash_bindings(
    launch: dict[str, Any],
    stage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, path in TOOL_PATHS.items():
        references = [
            {"artifact": artifact_name, **reference}
            for artifact_name, artifact in (("persistent-launch.json", launch), ("stage-run.json", stage))
            for reference in _hash_references(artifact, name)
        ]
        current = sha(path)
        result[name] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "current_sha256": current,
            "available_in_checkonly_artifacts": bool(references),
            "declared_references": references,
            "matches_current": all(reference["sha256"] == current for reference in references) if references else None,
        }
    return result


def main() -> int:
    launch = load(ROOT_RUN / "persistent-launch.json")
    stage = load(ROOT_RUN / "stage-run.json")
    current_hex_sha256 = sha(CANDIDATE_HEX)
    checks = validate_checkonly(launch, stage, current_hex_sha256)
    stale_selftest = stale_candidate_hash_selftest(launch, stage, current_hex_sha256)
    tool_bindings = checkonly_tool_hash_bindings(launch, stage)
    checks["stale_checkonly_candidate_hash_selftest_pass"] = stale_selftest["pass"] is True
    checks["declared_checkonly_tool_hashes_match_current"] = all(
        binding["matches_current"] is not False for binding in tool_bindings.values()
    )
    errors = [key for key, value in checks.items() if not value]
    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.r4.lifecycle.v3",
        "status": "PASS" if not errors else "NO_GO_R12_R4_LIFECYCLE",
        "requirement": "COMP-REQ-377",
        "future_physical_authorization_requirement_id": "COMP-REQ-378",
        "mode": "persistent_checkonly_only",
        "hardware_contact": 0,
        "write_counter_sum": 0,
        "popup_count": 0,
        "retry_count": 0,
        "current_hex_sha256": current_hex_sha256,
        "required_current_hex_sha256": EXPECTED_HEX_SHA256,
        "checks": checks,
        "stale_candidate_hash_selftest": stale_selftest,
        "checkonly_tool_hash_bindings": tool_bindings,
        "checkonly_root": str(ROOT_RUN.relative_to(ROOT)).replace("\\", "/"),
        "errors": errors,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
