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
SCOPES = ("idle-timer", "stop-wake", "short-tap", "double-tap-recording", "full")


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


def marker_after(log: str, marker: str, start: int) -> int:
    return log.find(marker, start)


def first_terminal_gesture_after(log: str, start: int) -> str | None:
    for match in re.finditer(r"\[touch-ui\] gesture=(?P<gesture>[a-z_]+)\b", log[start:]):
        gesture = match.group("gesture")
        # `hold` is a non-consuming 650 ms acknowledgement. The following
        # release/tap, swipe, double-tap, or 3 s long press decides the action.
        if gesture != "hold":
            return gesture
    return None


def required_check_names(scope: str) -> tuple[str, ...]:
    if scope == "idle-timer":
        return (
            "lpm_boot_ready",
            "tp_int_wired",
            "ft6336_trigger_mode",
            "low_power_idle_timer_armed",
            "timer_stop_precedes_sleepy",
            "low_power_sleep_pose_stopped",
            "low_power_face_requested_timer",
            "low_power_face_completed_stop",
            "timer_sleep_returns_to_stop",
            "single_boot_after_capture_start",
        )
    if scope == "stop-wake":
        return (
            *required_check_names("idle-timer"),
            "health_sample_observed",
            "irq_evidence_observed",
            "irq_observed",
            "irq_consumed",
            "irq_counts_ordered",
        )
    if scope == "short-tap":
        return (
            *required_check_names("stop-wake"),
            "wake_contact_after_sleepy",
            "low_power_touch_wake_requested",
            "first_wake_gesture_is_tap",
            "daily_reaction_after_tap",
            "visible_expression_after_tap",
            "no_idle_prerefresh_before_response",
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
    low_power_timer_armed = "[power] low_power_idle_timer=armed delay_ms=15000"
    low_power_face_request = "[power] low_power_face request=sleepy trigger=idle_timer"
    low_power_face_complete = "[power] low_power_face completed=1 stop=allowed"
    stop_allowed = "[power] stop=allowed"
    sleepy_complete_index = log.find(low_power_face_complete)
    wake_contact_index = marker_after(
        log,
        "[touch] contacts=1 event=down",
        sleepy_complete_index + len(low_power_face_complete),
    ) if sleepy_complete_index >= 0 else -1
    touch_wake_index = marker_after(
        log,
        "[touch-ui] low_power_touch_wake state=active visual=gesture_owned result=deferred",
        wake_contact_index + 1,
    ) if wake_contact_index >= 0 else -1
    first_wake_gesture = (
        first_terminal_gesture_after(log, touch_wake_index + 1)
        if touch_wake_index >= 0
        else None
    )
    tap_index = marker_after(log, "[touch-ui] gesture=tap", touch_wake_index + 1) if touch_wake_index >= 0 else -1
    daily_reaction_index = marker_after(log, "[touch-ui] daily_reaction", tap_index + 1) if tap_index >= 0 else -1
    expression_index = marker_after(log, "[epaper] scene=expression", daily_reaction_index + 1) if daily_reaction_index >= 0 else -1
    response_index = marker_after(log, "[screen] display_result", expression_index + 1) if expression_index >= 0 else -1
    idle_request_after_contact = marker_after(
        log,
        "[power] low_power_face request=sleepy trigger=idle_timer",
        wake_contact_index + 1,
    ) if wake_contact_index >= 0 else -1
    checks = {
        "lpm_boot_ready": "[power] policy_selftest=pass touch_irq_wake=ready lpm=enabled" in log,
        "tp_int_wired": "irq=PC6 wired=1" in log,
        "ft6336_trigger_mode": "irq_mode=trigger" in log,
        "low_power_idle_timer_armed": low_power_timer_armed in log,
        "timer_stop_precedes_sleepy": marker_precedes(log, low_power_timer_armed, stop_allowed)
        and marker_precedes(log, stop_allowed, low_power_sleep_pose),
        "low_power_sleep_pose_stopped": low_power_sleep_pose in log,
        "low_power_face_requested_timer": low_power_face_request in log,
        "low_power_face_completed_stop": low_power_face_complete in log,
        "timer_sleep_returns_to_stop": marker_precedes(
            log, low_power_face_request, low_power_face_complete
        ),
        "health_sample_observed": bool(samples),
        "irq_event_observed": bool(events),
        "irq_evidence_observed": bool(events) or (max_irq > 0 and max_consumed > 0),
        "irq_observed": max_irq > 0,
        "irq_consumed": max_consumed > 0,
        "irq_counts_ordered": all_health_ordered,
        "wake_contact_after_sleepy": wake_contact_index >= 0,
        "low_power_touch_wake_requested": touch_wake_index >= 0,
        "first_wake_gesture_is_tap": first_wake_gesture == "tap",
        "daily_reaction_after_tap": daily_reaction_index >= 0,
        "visible_expression_after_tap": expression_index >= 0 and response_index >= 0,
        "no_idle_prerefresh_before_response": idle_request_after_contact < 0 or
        (daily_reaction_index >= 0 and idle_request_after_contact > daily_reaction_index),
        "single_boot_after_capture_start": log.count("[power] policy_selftest=pass touch_irq_wake=ready lpm=enabled") == 1,
        "two_double_taps": double_taps >= 2,
        "touch_record_started": "[record] touch_double_tap action=start" in log
        and "state=recording" in log,
        "touch_record_stopped": "[record] touch_double_tap action=stop" in log,
        "external_flash_store_finished": "[record] touch_double_tap action=user_store result=1" in log,
    }
    required_checks = required_check_names(scope)
    if all(checks[name] for name in required_checks):
        status = "PASS"
    elif scope == "short-tap" and first_wake_gesture == "long_press":
        status = "NO_GO_FIRST_WAKE_GESTURE_LONG_PRESS"
    else:
        status = "NO_GO_INCOMPLETE_TOUCH_WAKE_EVIDENCE"
    next_actions = {
        "idle-timer": "Capture at least 20 seconds after reset and prove the 15 s idle timer permits Stop before its single sleepy transition, then the display-complete callback returns to Stop.",
        "stop-wake": "Collect one reset-bounded capture that shows the 15 s idle timer arm, static sleepy pose, Stop, then one touch so PC6 IRQ observation and consumption are logged.",
        "short-tap": "After the sleepy face reaches Stop, touch and lift in under 500 ms. The first post-wake gesture must be tap, followed by daily_reaction and one visible expression frame; a 3 s long press is a different menu contract and cannot pass this check.",
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
            "first_wake_gesture": first_wake_gesture,
            "wake_contact_after_sleepy": wake_contact_index >= 0,
            "low_power_touch_wake_requested": touch_wake_index >= 0,
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
            "[power] low_power_idle_timer=armed delay_ms=15000",
            "[power] stop=allowed blockers=0x00000000 touch_irq=1",
            "[screen] low_power_idle pose=sleepy animation=stopped",
            "[power] low_power_face request=sleepy trigger=idle_timer",
            "[power] stop=blocked blockers=0x00000000 touch_irq=1",
            "[power] stop=allowed blockers=0x00000000 touch_irq=1",
            "[power] low_power_face completed=1 stop=allowed",
            "[touch-health] detected=1 irq=3 irq_consumed=3 buffered=0 dropped=0",
            "[touch-irq] observed=3 consumed=3",
            "[touch] contacts=1 event=down id=0 raw_x=100 raw_y=100 x=100 y=100 mirror_x=0 mirror_y=0 sample_age_ms=1 reads=10",
            "[touch-ui] low_power_touch_wake state=active visual=gesture_owned result=deferred",
            "[touch] contacts=0 event=none id=0 raw_x=0 raw_y=0 x=0 y=0 mirror_x=0 mirror_y=0 sample_age_ms=1 reads=12",
            "[touch-ui] gesture=tap start=100,100 end=100,100 duration_ms=120 sample_age_ms=1",
            "[touch-ui] daily_reaction x=100 y=100",
            "[epaper] scene=expression name=curious frame_index=2 dirty=8,18,184,166 source=external_flash",
            "[screen] display_result id=2 kind=1 resource_revision=53 active_revision=53 coherent_generation=1 generation_switches=1 last_stale_discarded=0 pending=0 stale_generation_discarded=0 panel_result=0",
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
