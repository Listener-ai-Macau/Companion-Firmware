#!/usr/bin/env python3
"""Validate the six-request WB55 e-paper refresh-cadence diagnostic trace."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_ID = "companion.wb55.refresh_cadence_log.v1"
REQUEST_COUNT = 6
POLICY = re.compile(
    r"\[epaper\] policy requested=3 selected=(?P<selected>\w+) "
    r"reason=(?P<reason>\d+) partial_count=(?P<count>\d+) "
    r"limit=(?P<limit>\d+) baseline=(?P<baseline>\d+)"
)
def scoped_log(log: str) -> str:
    start = "[screen] refresh_cadence_diagnostic start requests=6"
    end = "[screen] refresh_cadence_diagnostic done interactive_requests=6 cleanup_expected=1"
    start_index = log.find(start)
    if start_index < 0:
        return ""
    end_index = log.find(end, start_index)
    if end_index < 0:
        return log[start_index:]
    return log[start_index : end_index + len(end)]


def evaluate(log: str, log_path: str) -> dict[str, Any]:
    scoped = scoped_log(log)
    policies = [
        {
            "selected": match.group("selected"),
            "reason": int(match.group("reason")),
            "partial_count": int(match.group("count")),
            "limit": int(match.group("limit")),
            "baseline": int(match.group("baseline")),
        }
        for match in POLICY.finditer(scoped)
    ]
    queued = [
        int(match.group("step"))
        for match in re.finditer(r"refresh_cadence_diagnostic queue step=(?P<step>\d+)", scoped)
    ]
    completed = [
        int(match.group("step"))
        for match in re.finditer(r"refresh_cadence_diagnostic complete step=(?P<step>\d+)", scoped)
    ]
    interactive = policies[1:] if policies and policies[0]["selected"] == "full" else []
    differential = [
        policy["partial_count"]
        for policy in interactive
        if policy["selected"] == "differential"
    ]
    maintenance = [
        policy
        for policy in interactive
        if policy["selected"] == "maintenance"
    ]
    checks = {
        "diagnostic_started": bool(scoped),
        "baseline_full": bool(policies)
        and policies[0]["selected"] == "full"
        and policies[0]["reason"] == 3,
        "six_steps_queued": queued == list(range(1, REQUEST_COUNT + 1)),
        "six_steps_completed": completed == list(range(1, REQUEST_COUNT + 1)),
        "five_differential_requests": differential == [0, 1, 2, 3, 4],
        "one_sixth_request_maintenance": len(maintenance) == 1
        and maintenance[0]["partial_count"] == 5
        and maintenance[0]["reason"] == 4
        and maintenance[0]["limit"] == 5,
        "differential_waveform": scoped.count("refresh mode=differential control=0xFC") >= 5,
        "mode1_waveform": "refresh mode=fast control=0xC7" in scoped,
        "diagnostic_completed": (
            "[screen] refresh_cadence_diagnostic done "
            "interactive_requests=6 cleanup_expected=1"
        ) in scoped,
        "no_obsolete_delayed_maintenance": "screen_maintenance" not in scoped
        and "quiet_ms=1200" not in scoped,
        "no_diagnostic_abort": "refresh_cadence_diagnostic abort" not in scoped,
    }
    status = "PASS" if all(checks.values()) else "NO_GO_INCOMPLETE_REFRESH_CADENCE"
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": "reset-bounded serial evidence for the diagnostic image only; no human visual or current claim",
        "log": log_path,
        "checks": checks,
        "observed": {
            "policy_records": policies,
            "queued_steps": queued,
            "completed_steps": completed,
        },
        "next_action": (
            "Run the focused ACPT-01 visual review; this trace does not prove residual-image quality or touch feel."
            if status == "PASS"
            else "Flash the dedicated refresh-cadence diagnostic image, capture through its done marker, and inspect the failed checks."
        ),
    }


def self_test() -> dict[str, Any]:
    lines = [
        "[screen] refresh_cadence_diagnostic start requests=6",
        "[epaper] policy requested=3 selected=full reason=3 partial_count=0 limit=5 baseline=0",
        "[epaper] refresh mode=full control=0xF7",
        "[screen] refresh_cadence_diagnostic baseline_complete=1",
    ]
    for step in range(1, 6):
        lines.extend(
            [
                f"[screen] refresh_cadence_diagnostic queue step={step} item={step - 1} refresh=interactive",
                f"[epaper] policy requested=3 selected=differential reason=1 partial_count={step - 1} limit=5 baseline=1",
                "[epaper] refresh mode=differential control=0xFC",
                f"[screen] refresh_cadence_diagnostic complete step={step}",
            ]
        )
    lines.extend(
        [
            "[screen] refresh_cadence_diagnostic queue step=6 item=5 refresh=interactive",
            "[epaper] policy requested=3 selected=maintenance reason=4 partial_count=5 limit=5 baseline=1",
            "[epaper] refresh mode=fast control=0xC7",
            "[screen] refresh_cadence_diagnostic complete step=6",
            "[screen] refresh_cadence_diagnostic done interactive_requests=6 cleanup_expected=1",
        ]
    )
    report = evaluate("\n".join(lines), "synthetic-self-test")
    report["status"] = "PASS_STATIC_PARSER" if report["status"] == "PASS" else "FAIL_STATIC_PARSER"
    report["claim_scope"] = "synthetic parser self-test; no hardware claim"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test()
    elif args.log is not None:
        if not args.log.is_file():
            parser.error(f"serial log not found: {args.log}")
        report = evaluate(args.log.read_text(encoding="utf-8", errors="replace"), str(args.log))
    else:
        parser.error("pass --log PATH or --self-test")

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["status"] in {"PASS", "PASS_STATIC_PARSER"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
