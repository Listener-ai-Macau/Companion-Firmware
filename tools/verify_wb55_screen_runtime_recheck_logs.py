#!/usr/bin/env python3
"""Verify or scaffold current WB55 CEMP runtime recheck serial evidence."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER_REPORT = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-runner.json"
BILINGUAL_MENU = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
CANDIDATE = current_candidate()
DEFAULT_RUN_ROOT = CANDIDATE.run_root
RUN_REPORT_NAME = "runtime-recheck-run.json"
SCHEMA_ID = "companion.screen.wb55_runtime_recheck_logs.v1"
PENDING_STATUS = CANDIDATE.pending_status
PASS_STATUS = CANDIDATE.pass_status
QUIET_INTERACTION_PROFILE_MARKER = (
    "[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 "
    "ft6336_threshold=0x70 touch_poll_active_ms=5 touch_poll_refresh_ms=5 "
    "refresh_policy=partial_x5_then_fast_cleanup"
)


PROVISION_COMMON_MARKERS = CANDIDATE.common_markers

PROVISION_MARKERS = PROVISION_COMMON_MARKERS + (
    "external_store=ready",
    "preview_started name=idle",
)

QUIET_NORMAL_MARKERS = (
    "mount=ok",
    f"revision={CANDIDATE.revision}",
    f"clips={CANDIDATE.clips} frames={CANDIDATE.frames}",
    "expression_renderer=external_pack",
    "pet_behavior_selftest=pass failure_code=0",
    "touch-health] detected=1 identity=1 addr=0x38",
    f"queue_generation revision={CANDIDATE.revision}",
    "coherent_generation=1",
    "last_stale_discarded=",
    QUIET_INTERACTION_PROFILE_MARKER,
    "preview_started name=idle",
    "low_power_face completed=1 stop=allowed",
)

EXPECTED_RUN_STEPS = (
    "flash_provision",
    "capture_provision",
    "flash_normal",
    "capture_normal",
)


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: pathlib.Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def log_result(label: str, run_root: pathlib.Path, markers: tuple[str, ...]) -> dict[str, Any]:
    raw = run_root / label / "nucleo-serial-raw.log"
    summary = run_root / label / "nucleo-serial-summary.json"
    text = read_text(raw)
    summary_data: dict[str, Any] | None = None
    if summary.exists():
        try:
            summary_data = load_json(summary)
        except json.JSONDecodeError:
            summary_data = {"status": "INVALID_JSON"}
    marker_map = {marker: marker in text for marker in markers}
    return {
        "label": label,
        "raw_log": rel(raw),
        "summary_json": rel(summary),
        "raw_log_exists": raw.exists(),
        "summary_json_exists": summary.exists(),
        "summary_status": None if summary_data is None else summary_data.get("status"),
        "bytes_read": None if summary_data is None else summary_data.get("bytes_read"),
        "markers": marker_map,
        "status": "PASS" if raw.exists() and summary.exists() and all(marker_map.values()) else "MISSING_OR_INCOMPLETE",
    }


def run_report_result(run_root: pathlib.Path) -> dict[str, Any]:
    path = run_root / RUN_REPORT_NAME
    data: dict[str, Any] | None = None
    if path.exists():
        try:
            data = load_json(path)
        except json.JSONDecodeError:
            data = {"schema": "INVALID_JSON", "status": "INVALID_JSON"}
    steps = [] if data is None else data.get("steps", [])
    results = [] if data is None else data.get("results", [])
    result_statuses = {
        str(item.get("id")): str(item.get("status"))
        for item in results
        if isinstance(item, dict)
    }
    result_ids = [str(item.get("id")) for item in results if isinstance(item, dict)]
    results_have_timestamps = bool(results) and all(
        isinstance(item, dict)
        and isinstance(item.get("started_at"), str)
        and "T" in str(item.get("started_at"))
        and isinstance(item.get("ended_at"), str)
        and "T" in str(item.get("ended_at"))
        for item in results
    )
    return {
        "path": rel(path),
        "exists": path.exists(),
        "schema": None if data is None else data.get("schema"),
        "status": None if data is None else data.get("status"),
        "resource": None if data is None else data.get("resource"),
        "step_ids": [str(item.get("id")) for item in steps if isinstance(item, dict)],
        "result_ids": result_ids,
        "result_statuses": result_statuses,
        "expected_step_ids": list(EXPECTED_RUN_STEPS),
        "steps_match_expected_order": [str(item.get("id")) for item in steps if isinstance(item, dict)] == list(EXPECTED_RUN_STEPS),
        "results_match_expected_order": result_ids == list(EXPECTED_RUN_STEPS),
        "all_results_pass": all(result_statuses.get(step) == "PASS" for step in EXPECTED_RUN_STEPS),
        "results_have_timestamps": results_have_timestamps,
    }


def build_snapshot(run_root: pathlib.Path) -> dict[str, Any]:
    runner = load_json(RUNNER_REPORT)
    menu = load_json(BILINGUAL_MENU)
    resource = menu.get("resource_pack", {})
    runtime = menu.get("runtime_evidence", {})
    provision = log_result("provision", run_root, PROVISION_MARKERS)
    normal = log_result("normal", run_root, QUIET_NORMAL_MARKERS)
    run_report = run_report_result(run_root)
    logs_pass = provision["status"] == "PASS" and normal["status"] == "PASS"
    missing_logs = not (
        provision["raw_log_exists"]
        and provision["summary_json_exists"]
        and normal["raw_log_exists"]
        and normal["summary_json_exists"]
    )
    if logs_pass:
        status = "PASS"
    elif missing_logs:
        status = "NO_GO_MISSING_RUNTIME_LOGS"
    else:
        status = "NO_GO_INCOMPLETE_RUNTIME_MARKERS"
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "target": "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U",
        "candidate": {
            "revision": resource.get("revision"),
            "total_bytes": resource.get("total_bytes"),
            "pack_crc32": resource.get("pack_crc32"),
            "runtime_status": runtime.get("status"),
        },
        "runner": {
            "path": runner.get("runner"),
            "status": runner.get("status"),
            "dry_run_returncode": runner.get("dry_run", {}).get("returncode"),
            "safety_contract": runner.get("safety_contract", {}),
        },
        "run_root": rel(run_root),
        "run_report": run_report,
        "provision": provision,
        "normal": normal,
        "promotion_rule": (
            "Only after both logs pass may companion-screen-bilingual-menu-wb55.json "
            f"be promoted from {PENDING_STATUS} to a runtime-pass "
            "human-visual-pending state."
        ),
        "next_machine_action": (
            "Run tools/run_wb55_screen_runtime_recheck.ps1 under the Companion-WB55 "
            "workflow lock, then rerun this verifier."
        ) if status != "PASS" else (
            "Runtime evidence is already promoted; continue to pre-acceptance health."
            if runtime.get("status") == PASS_STATUS else
            "Run tools/promote_wb55_screen_runtime_recheck.py --apply, then rerun pre-acceptance health."
        ),
    }


def verify(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate = snapshot.get("candidate", {})
    if snapshot.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    if candidate.get("revision") != CANDIDATE.revision:
        errors.append(f"candidate revision must be {CANDIDATE.revision}")
    if candidate.get("total_bytes") != CANDIDATE.total_bytes:
        errors.append(f"candidate size must be {CANDIDATE.total_bytes}")
    if candidate.get("pack_crc32") != CANDIDATE.pack_crc32:
        errors.append(f"candidate CRC must be {CANDIDATE.pack_crc32}")
    if candidate.get("runtime_status") not in {PENDING_STATUS, PASS_STATUS}:
        errors.append("runtime status must be pending or promoted human-visual-pending")
    runner = snapshot.get("runner", {})
    if runner.get("status") != "PASS" or runner.get("dry_run_returncode") != 0:
        errors.append("runtime recheck runner dry-run must pass")
    for key, value in runner.get("safety_contract", {}).items():
        if value is not True:
            errors.append(f"runner safety_contract.{key} is not true")
    status = snapshot.get("status")
    if status not in {"PASS", "NO_GO_MISSING_RUNTIME_LOGS", "NO_GO_INCOMPLETE_RUNTIME_MARKERS"}:
        errors.append(f"unexpected status {status!r}")
    if status == "PASS":
        run_report = snapshot.get("run_report", {})
        if run_report.get("exists") is not True:
            errors.append("runtime recheck run report must exist when logs pass")
        if run_report.get("schema") != "companion.wb55_screen_runtime_recheck_run.v1":
            errors.append("runtime recheck run report schema is invalid")
        if run_report.get("status") != "PASS":
            errors.append("runtime recheck run report status must be PASS when logs pass")
        if run_report.get("steps_match_expected_order") is not True:
            errors.append("runtime recheck run report must preserve provision/capture/normal/capture order")
        if run_report.get("results_match_expected_order") is not True:
            errors.append("runtime recheck run report results must preserve provision/capture/normal/capture order")
        if run_report.get("all_results_pass") is not True:
            errors.append("runtime recheck run report must show all steps PASS")
        if run_report.get("results_have_timestamps") is not True:
            errors.append("runtime recheck run report must include started_at/ended_at for every step")
        resource = run_report.get("resource") or {}
        if (
            resource.get("revision") != CANDIDATE.revision
            or resource.get("total_bytes") != CANDIDATE.total_bytes
            or resource.get("pack_crc32") != CANDIDATE.pack_crc32
        ):
            errors.append("runtime recheck run report resource must match the active CEMP candidate")
        for label in ("provision", "normal"):
            section = snapshot.get(label, {})
            if section.get("status") != "PASS":
                errors.append(f"{label} log status must be PASS")
            missing = [marker for marker, present in section.get("markers", {}).items() if present is not True]
            if missing:
                errors.append(f"{label} log missing markers: {missing}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--run-root", type=pathlib.Path, default=DEFAULT_RUN_ROOT)
    args = parser.parse_args()

    output = args.json if args.json.is_absolute() else ROOT / args.json
    run_root = args.run_root if args.run_root.is_absolute() else ROOT / args.run_root
    snapshot = build_snapshot(run_root)
    errors = verify(snapshot)
    rendered = json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not output.exists():
        errors.append(f"missing {rel(output)}")
    elif output.read_text(encoding="utf-8") != rendered:
        errors.append(f"stale {rel(output)}")

    if errors:
        print("FAIL: WB55 screen runtime recheck log verification failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: WB55 screen runtime recheck logs verified -> {rel(output)} ({snapshot['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
