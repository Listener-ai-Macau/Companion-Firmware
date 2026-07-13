#!/usr/bin/env python3
"""Validate real WB55 TP_INT wake evidence from a bounded serial capture."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ID = "companion.wb55.touch_wake_log.v1"
SCOPES = ("stop-wake", "double-tap-recording", "full")


def health_samples(log: str) -> list[dict[str, int]]:
    samples: list[dict[str, int]] = []
    pattern = re.compile(
        r"\[touch-health\].*?\birq=(?P<irq>\d+)\b.*?\birq_consumed=(?P<consumed>\d+)\b"
    )
    for match in pattern.finditer(log):
        samples.append(
            {
                "irq": int(match.group("irq")),
                "irq_consumed": int(match.group("consumed")),
            }
        )
    return samples


def irq_events(log: str) -> list[dict[str, int]]:
    events: list[dict[str, int]] = []
    pattern = re.compile(r"\[touch-irq\].*?\bobserved=(?P<irq>\d+)\b.*?\bconsumed=(?P<consumed>\d+)\b")
    for match in pattern.finditer(log):
        events.append({"irq": int(match.group("irq")), "irq_consumed": int(match.group("consumed"))})
    return events


def marker_precedes(log: str, first: str, second: str) -> bool:
    first_index = log.find(first)
    if first_index < 0:
        return False
    return log.find(second, first_index + len(first)) >= 0


def required_check_names(scope: str) -> tuple[str, ...]:
    if scope == "stop-wake":
        return (
            "lpm_boot_ready",
            "tp_int_wired",
            "ft6336_trigger_mode",
            "low_power_sleep_pose_stopped",
            "low_power_face_requested_static",
            "low_power_pose_precedes_stop",
            "health_sample_observed",
            "irq_event_observed",
            "irq_observed",
            "irq_consumed",
            "irq_counts_ordered",
            "single_boot_after_capture_start",
        )
    if scope == "double-tap-recording":
        return (
            "two_double_taps",
            "touch_record_started",
            "touch_record_stopped",
            "external_flash_store_finished",
        )
    return (
        *required_check_names("stop-wake"),
        *required_check_names("double-tap-recording"),
    )


def evaluate(log: str, log_path: str, scope: str = "full") -> dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError(f"unsupported scope: {scope}")
    samples = health_samples(log)
    events = irq_events(log)
    irq_observations = [*samples, *events]
    max_irq = max((sample["irq"] for sample in irq_observations), default=0)
    max_consumed = max((sample["irq_consumed"] for sample in irq_observations), default=0)
    all_health_ordered = all(sample["irq_consumed"] <= sample["irq"] for sample in irq_observations)
    double_taps = log.count("[touch-ui] daily_double_tap_recording")
    low_power_sleep_pose = "[screen] low_power_idle pose=sleepy animation=stopped"
    low_power_face_request = "[power] low_power_face request=sleepy animation=static"
    stop_allowed = "[power] stop=allowed"
    checks = {
        "lpm_boot_ready": "[power] policy_selftest=pass touch_irq_wake=ready lpm=enabled" in log,
        "tp_int_wired": "irq=PC6 wired=1" in log,
        "ft6336_trigger_mode": "irq_mode=trigger" in log,
        "low_power_sleep_pose_stopped": low_power_sleep_pose in log,
        "low_power_face_requested_static": low_power_face_request in log,
        "low_power_pose_precedes_stop": marker_precedes(log, low_power_face_request, stop_allowed),
        "health_sample_observed": bool(samples),
        "irq_event_observed": bool(events),
        "irq_observed": max_irq > 0,
        "irq_consumed": max_consumed > 0,
        "irq_counts_ordered": all_health_ordered,
        "single_boot_after_capture_start": log.count("[power] policy_selftest=pass touch_irq_wake=ready lpm=enabled") == 1,
        "two_double_taps": double_taps >= 2,
        "touch_record_started": "[record] touch_double_tap action=start" in log
        and "state=recording" in log,
        "touch_record_stopped": "[record] touch_double_tap action=stop" in log,
        "external_flash_store_finished": "[record] touch_double_tap action=user_store result=1" in log,
    }
    required_checks = required_check_names(scope)
    status = "PASS" if all(checks[name] for name in required_checks) else "NO_GO_INCOMPLETE_TOUCH_WAKE_EVIDENCE"
    next_actions = {
        "stop-wake": "Collect one reset-bounded capture that shows the static sleepy pose before Stop, then touch once so PC6 IRQ observation and consumption are logged.",
        "double-tap-recording": "Collect one bounded capture containing two daily-page double taps, recording start/stop, and a successful external Flash store.",
        "full": "Collect a post-wiring serial capture with TP_INT wired, then perform one Stop wake and two daily-page double taps.",
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "scope": scope,
        "claim_scope": "serial-log evidence only for the selected touch acceptance scope; no current measurement claim",
        "log": log_path,
        "checks": checks,
        "required_checks": list(required_checks),
        "observed": {
            "health_samples": len(samples),
            "irq_events": len(events),
            "max_irq": max_irq,
            "max_irq_consumed": max_consumed,
            "daily_double_tap_events": double_taps,
        },
        "next_action": (
            next_actions[scope]
            if status != "PASS"
            else "Use the next focused acceptance item; this serial log does not prove the final <= 1 mA product-board current target."
        ),
    }


def self_test(scope: str = "full") -> dict[str, Any]:
    synthetic = "\n".join(
        [
            "[touch] ft6336 decoder=pass gesture=pass addr=0x38 probe=present probes=1 irq_mode=trigger irq_cfg_errors=0 tuning=applied threshold=0x16 period=12/24 tuning_errors=0 poll_ms=5/8 irq=PC6 wired=1 reset=PC10 wired=0 refresh_poll_ms=5",
            "[power] policy_selftest=pass touch_irq_wake=ready lpm=enabled",
            "[screen] low_power_idle pose=sleepy animation=stopped",
            "[power] low_power_face request=sleepy animation=static",
            "[power] stop=allowed blockers=0x00000000 touch_irq=1",
            "[touch-health] detected=1 irq=3 irq_consumed=3 buffered=0 dropped=0",
            "[touch-irq] observed=3 consumed=3",
            "[touch-ui] daily_double_tap_recording x=100 y=100 state=idle",
            "[record] touch_double_tap action=start source=4 result=0 state=recording",
            "[touch-ui] daily_double_tap_recording x=100 y=100 state=recording",
            "[record] touch_double_tap action=stop source=4 stop_result=0 finish_result=0 state=transfer_ready",
            "[record] touch_double_tap action=user_store result=1 state=idle",
        ]
    )
    report = evaluate(synthetic, "synthetic-self-test", scope)
    report["status"] = "PASS_STATIC_PARSER" if report["status"] == "PASS" else "FAIL_STATIC_PARSER"
    report["claim_scope"] = "synthetic parser self-test; no hardware claim"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--scope", choices=SCOPES, default="full")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test(args.scope)
    elif args.log is not None:
        if not args.log.is_file():
            parser.error(f"serial log not found: {args.log}")
        report = evaluate(args.log.read_text(encoding="utf-8", errors="replace"), str(args.log), args.scope)
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
