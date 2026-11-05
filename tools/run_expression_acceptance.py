#!/usr/bin/env python3
"""Run the Companion screen expression acceptance commands from the index."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_INDEX = pathlib.Path("docs/validation/companion-screen-acceptance-index.json")
DEFAULT_STATUSES = {"PASS", "DEFERRED_HARDWARE", "PENDING_HUMAN"}
STDIO_TAIL_CHARS = 4000


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def tail(text: str, limit: int = STDIO_TAIL_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def load_index(path: pathlib.Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    return json.loads(resolved.read_text(encoding="utf-8"))


def is_build_command(command: str) -> bool:
    return "build_nucleo_bringup.ps1" in command


def requires_empty_stdout(command: str) -> bool:
    normalized = command.replace("/", "\\").lower()
    return normalized.startswith("git diff --name-only --") and "third_party\\stm32cube" in normalized


def collect_commands(index: dict[str, Any], statuses: set[str], skip_build: bool) -> list[dict[str, Any]]:
    commands: dict[str, dict[str, Any]] = {}
    for item in index.get("items", []):
        if not isinstance(item, dict):
            continue
        item_status = str(item.get("status", ""))
        if item_status not in statuses:
            continue
        for command in item.get("validation_commands", []):
            command_text = str(command)
            if skip_build and is_build_command(command_text):
                continue
            entry = commands.setdefault(
                command_text,
                {
                    "command": command_text,
                    "item_ids": [],
                    "titles": [],
                    "requires_empty_stdout": requires_empty_stdout(command_text),
                },
            )
            entry["item_ids"].append(str(item.get("id", "")))
            entry["titles"].append(str(item.get("title", "")))
    return list(commands.values())


def command_status_by_item(commands: list[dict[str, Any]]) -> dict[str, str]:
    item_statuses: dict[str, str] = {}
    for command in commands:
        status = str(command.get("status", "UNKNOWN"))
        for item_id in command.get("item_ids", []):
            previous = item_statuses.get(str(item_id), "PASS")
            if status.startswith("SKIPPED"):
                if previous == "PASS":
                    item_statuses[str(item_id)] = status
            elif status != "PASS":
                item_statuses[str(item_id)] = status
            else:
                item_statuses.setdefault(str(item_id), "PASS")
    return item_statuses


def run_command(command: dict[str, Any], timeout_s: float, dry_run: bool) -> dict[str, Any]:
    command_text = str(command["command"])
    result = dict(command)
    if dry_run:
        result.update(
            {
                "status": "SKIPPED_DRY_RUN",
                "returncode": None,
                "duration_s": 0.0,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        )
        return result

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command_text,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "TIMEOUT",
                "returncode": None,
                "duration_s": round(time.monotonic() - started, 3),
                "stdout_tail": tail(exc.stdout or ""),
                "stderr_tail": tail(exc.stderr or ""),
            }
        )
        return result

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    status = "PASS" if completed.returncode == 0 else "FAIL"
    if status == "PASS" and result.get("requires_empty_stdout") and stdout.strip():
        status = "FAIL_NONEMPTY_STDOUT"
    result.update(
        {
            "status": status,
            "returncode": completed.returncode,
            "duration_s": round(time.monotonic() - started, 3),
            "stdout_tail": tail(stdout),
            "stderr_tail": tail(stderr),
        }
    )
    return result


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    index_path = args.index if args.index.is_absolute() else REPO_ROOT / args.index
    index = load_index(index_path)
    statuses = {"PASS"} if args.pass_only else set(DEFAULT_STATUSES)
    commands = collect_commands(index, statuses, args.skip_build)

    started = utc_now()
    monotonic_started = time.monotonic()
    results: list[dict[str, Any]] = []
    for command in commands:
        result = run_command(command, float(args.timeout), bool(args.dry_run))
        results.append(result)
        print(f"{result['status']}: {result['command']}")
        if result["status"] not in {"PASS", "SKIPPED_DRY_RUN"} and not args.continue_on_fail:
            break

    failed = [result for result in results if result["status"] not in {"PASS", "SKIPPED_DRY_RUN"}]
    skipped = [result for result in results if str(result["status"]).startswith("SKIPPED")]
    report_status = "PASS"
    if failed:
        report_status = "FAIL"
    elif skipped:
        report_status = "DRY_RUN" if args.dry_run else "PARTIAL"

    report = {
        "schema_id": "companion.pendant.screen_acceptance_run.v1",
        "status": report_status,
        "started_at": started,
        "ended_at": utc_now(),
        "duration_s": round(time.monotonic() - monotonic_started, 3),
        "index": rel(index_path),
        "index_summary": index.get("summary", {}),
        "included_statuses": sorted(statuses),
        "skip_build": bool(args.skip_build),
        "dry_run": bool(args.dry_run),
        "unique_command_count": len(commands),
        "executed_command_count": len(results),
        "pass_count": sum(1 for result in results if result["status"] == "PASS"),
        "fail_count": len(failed),
        "skip_count": len(skipped),
        "command_status_by_item": command_status_by_item(results),
        "commands": results,
    }
    return report


def write_report(path: pathlib.Path, report: dict[str, Any]) -> None:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=pathlib.Path, default=DEFAULT_INDEX, help="Acceptance index JSON to run.")
    parser.add_argument("--output", type=pathlib.Path, default=None, help="Optional JSON report path.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Per-command timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Emit the command plan without executing commands.")
    parser.add_argument("--pass-only", action="store_true", help="Run only PASS items, excluding deferred hardware gates.")
    parser.add_argument("--skip-build", action="store_true", help="Skip WB55 build commands from the index.")
    parser.add_argument("--continue-on-fail", action="store_true", help="Continue after a failing command.")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    report = build_report(args)
    if args.output is not None:
        write_report(args.output, report)
    if args.output is None or args.dry_run:
        print(
            "summary: "
            f"status={report['status']} unique={report['unique_command_count']} "
            f"executed={report['executed_command_count']} pass={report['pass_count']} "
            f"fail={report['fail_count']} skip={report['skip_count']}"
        )
    return 0 if report["status"] in {"PASS", "DRY_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
