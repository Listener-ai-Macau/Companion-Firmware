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
RECORDING_TOUCH_HEALTH_MAX_GAP_MS = 750


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


def recording_touch_samples(log: str) -> list[dict[str, int | str]]:
    samples: list[dict[str, int | str]] = []
    pattern = re.compile(
        r"\[record-touch\]\s+t=(?P<tick>\d+)\s+service=(?P<service>\d+)\s+"
        r"ft_read=(?P<ft_read>\d+)\s+delta=(?P<read_delta>\d+)\s+"
        r"ft_error=(?P<ft_error>\d+)\s+irq_produced=(?P<irq_produced>\d+)\s+"
        r"irq_consumed=(?P<irq_consumed>\d+)\s+pc6=(?P<pc6>[01])\s+"
        r"next_poll_ms=(?P<next_poll_ms>-?\d+)\s+contact=(?P<contact>[01])\s+"
        r"gesture_active=(?P<gesture_active>[01])\s+consumed=(?P<consumed>[01])\s+"
        r"tap_pending=(?P<tap_pending>[01])\s+buffered=(?P<buffered>\d+)\s+"
        r"deferred=(?P<deferred>[a-z_]+)"
    )
    integer_fields = (
        "tick",
        "service",
        "ft_read",
        "read_delta",
        "ft_error",
        "irq_produced",
        "irq_consumed",
        "pc6",
        "next_poll_ms",
        "contact",
        "gesture_active",
        "consumed",
        "tap_pending",
        "buffered",
    )
    for match in pattern.finditer(log):
        sample: dict[str, int | str] = {
            field: int(match.group(field)) for field in integer_fields
        }
        sample["deferred"] = match.group("deferred")
        samples.append(sample)
    return samples


def summarize_recording_touch_health(
    samples: list[dict[str, int | str]],
    post_start_contacts: int,
    post_start_gestures: int,
    recording_started: bool,
    recording_stopped: bool,
) -> dict[str, Any]:
    if not recording_started:
        return {
            "diagnosis": "NOT_APPLICABLE_NO_RECORDING_START",
            "sample_count": 0,
            "next_action": "First prove that the initial double tap starts recording.",
        }
    if not samples:
        return {
            "diagnosis": "NO_RECORDING_TOUCH_HEALTH",
            "sample_count": 0,
            "next_action": "Reject this trace image or inspect recording-loop scheduling; no [record-touch] sample followed recording start.",
        }

    services = [int(sample["service"]) for sample in samples]
    read_counts = [int(sample["ft_read"]) for sample in samples]
    read_deltas = [int(sample["read_delta"]) for sample in samples]
    error_counts = [int(sample["ft_error"]) for sample in samples]
    irq_produced = [int(sample["irq_produced"]) for sample in samples]
    irq_consumed = [int(sample["irq_consumed"]) for sample in samples]
    ticks = [int(sample["tick"]) for sample in samples]
    tick_gaps = [
        (current - previous) & 0xFFFFFFFF
        for previous, current in zip(ticks, ticks[1:])
    ]
    service_progress = all(
        current > previous for previous, current in zip(services, services[1:])
    )
    read_progress = sum(read_deltas) > 0 or read_counts[-1] > read_counts[0]
    error_delta = max(error_counts) - min(error_counts)
    irq_produced_delta = irq_produced[-1] - irq_produced[0]
    irq_consumed_delta = irq_consumed[-1] - irq_consumed[0]
    max_gap_ms = max(tick_gaps, default=0)
    pc6_levels = sorted({int(sample["pc6"]) for sample in samples})
    contact_seen = post_start_contacts > 0 or any(
        int(sample["contact"]) != 0 for sample in samples
    )
    gesture_state_seen = post_start_gestures > 0 or any(
        int(sample["gesture_active"]) != 0
        or int(sample["consumed"]) != 0
        or int(sample["tap_pending"]) != 0
        for sample in samples
    )

    if recording_stopped:
        diagnosis = "COMPLETE"
        next_action = "Recording touch control completed; continue the remaining recording/store gates."
    elif len(samples) < 2:
        diagnosis = "INSUFFICIENT_RECORDING_TOUCH_HEALTH"
        next_action = "Capture at least one more 250 ms recording-touch health interval."
    elif not service_progress or max_gap_ms > RECORDING_TOUCH_HEALTH_MAX_GAP_MS:
        diagnosis = "RECORDING_TOUCH_SCHEDULER_STALLED"
        next_action = "Inspect the recording loop around the largest health gap before changing FT6336 tuning."
    elif error_delta > 0:
        diagnosis = "FT6336_I2C_READ_FAILURE"
        next_action = "Inspect I2C bus recovery, pull-ups and controller power; FT6336 errors increased during recording."
    elif not read_progress:
        diagnosis = "FT6336_POLL_STALLED"
        next_action = "Inspect next-poll scheduling; touch service ran but FT6336 read_count did not advance."
    elif irq_produced[-1] > irq_consumed[-1]:
        diagnosis = "FT6336_IRQ_NOT_CONSUMED"
        next_action = "Inspect EXTI consumption and pending sample draining before changing touch thresholds."
    elif pc6_levels == [0] and irq_produced_delta == 0:
        diagnosis = "FT6336_PC6_STUCK_LOW"
        next_action = "Inspect the active-low TP_INT line and EXTI edge state; PC6 remained low without a new IRQ."
    elif irq_produced_delta == 0 and not contact_seen:
        diagnosis = "FT6336_NO_TOUCH_DETECTION"
        next_action = "The scheduler and I2C polling are healthy, but FT6336 neither asserted a new IRQ nor reported contact; inspect touch-controller detection or wiring."
    elif irq_produced_delta > 0 and not contact_seen:
        diagnosis = "FT6336_IRQ_WITHOUT_CONTACT_REPORT"
        next_action = "A touch IRQ arrived but no contact report followed; inspect report reads and release timing."
    elif contact_seen and not gesture_state_seen:
        diagnosis = "TOUCH_CONTACT_WITHOUT_GESTURE"
        next_action = "FT6336 contact reached firmware; inspect gesture lifecycle boundaries and release samples."
    else:
        diagnosis = "TOUCH_GESTURE_NOT_COMPLETED"
        next_action = "Touch acquisition progressed; inspect the captured gesture states that prevented the second double tap."

    return {
        "diagnosis": diagnosis,
        "sample_count": len(samples),
        "first_tick_ms": ticks[0],
        "last_tick_ms": ticks[-1],
        "max_gap_ms": max_gap_ms,
        "service_first": services[0],
        "service_last": services[-1],
        "service_progress": service_progress,
        "ft_read_first": read_counts[0],
        "ft_read_last": read_counts[-1],
        "ft_read_delta_sum": sum(read_deltas),
        "ft_read_progress": read_progress,
        "ft_error_first": error_counts[0],
        "ft_error_last": error_counts[-1],
        "ft_error_delta": error_delta,
        "irq_produced_first": irq_produced[0],
        "irq_produced_last": irq_produced[-1],
        "irq_produced_delta": irq_produced_delta,
        "irq_consumed_first": irq_consumed[0],
        "irq_consumed_last": irq_consumed[-1],
        "irq_consumed_delta": irq_consumed_delta,
        "pc6_levels": pc6_levels,
        "contact_seen": contact_seen,
        "post_start_contacts": post_start_contacts,
        "gesture_state_seen": gesture_state_seen,
        "post_start_gestures": post_start_gestures,
        "max_buffered_samples": max(int(sample["buffered"]) for sample in samples),
        "deferred_actions": sorted({str(sample["deferred"]) for sample in samples}),
        "next_action": next_action,
    }


def microphone_blocks(log: str) -> list[dict[str, int | str]]:
    blocks: list[dict[str, int | str]] = []
    pattern = re.compile(
        r"\[mic-manual\]\s+block=(?P<block>\d+)\s+status=(?P<status>[a-z_]+).*?"
        r"\bpcm_min=(?P<pcm_min>-?\d+)\s+pcm_max=(?P<pcm_max>-?\d+).*?"
        r"\bpcm_crc=0x(?P<pcm_crc>[0-9A-Fa-f]+)\b"
    )
    for match in pattern.finditer(log):
        blocks.append(
            {
                "block": int(match.group("block")),
                "status": match.group("status"),
                "pcm_min": int(match.group("pcm_min")),
                "pcm_max": int(match.group("pcm_max")),
                "pcm_crc": int(match.group("pcm_crc"), 16),
            }
        )
    return blocks


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
            "recording_touch_health_observed",
            "microphone_clock_restored",
            "microphone_dma_started",
            "sustained_pcm_blocks",
            "pcm_crc_varies",
            "pcm_has_signal_span",
            "no_microphone_timeout",
            "touch_record_stopped",
            "microphone_dma_stopped",
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
    mic_blocks = microphone_blocks(log)
    valid_mic_blocks = [block for block in mic_blocks if block["status"] == "ok"]
    pcm_crcs = {int(block["pcm_crc"]) for block in valid_mic_blocks}
    irq_observations = [*samples, *events]
    max_irq = max((sample["irq"] for sample in irq_observations), default=0)
    max_consumed = max((sample["irq_consumed"] for sample in irq_observations), default=0)
    all_health_ordered = all(sample["irq_consumed"] <= sample["irq"] for sample in irq_observations)
    double_taps = log.count("[touch-ui] daily_double_tap_recording")
    recording_start_marker = "[record] touch_double_tap action=start"
    recording_start_index = log.find(recording_start_marker)
    recording_started = recording_start_index >= 0 and bool(
        re.search(
            r"\[record\]\s+touch_double_tap\s+action=start\b.*?\bstate=recording\b",
            log[recording_start_index:],
        )
    )
    recording_slice = log[recording_start_index:] if recording_start_index >= 0 else ""
    record_touch_samples = recording_touch_samples(recording_slice)
    post_start_contacts = recording_slice.count("[touch] contacts=1")
    post_start_gestures = len(
        re.findall(r"\[touch-ui\]\s+gesture=[a-z_]+\b", recording_slice)
    )
    recording_stopped = "[record] touch_double_tap action=stop" in recording_slice
    record_touch_health = summarize_recording_touch_health(
        record_touch_samples,
        post_start_contacts,
        post_start_gestures,
        recording_started,
        recording_stopped,
    )
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
    dma_start_index = log.find("[mic-dma] action=start status=ok")
    dma_stop_index = marker_after(
        log,
        "[mic-dma] action=stop status=ok",
        dma_start_index + 1,
    ) if dma_start_index >= 0 else -1
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
        "touch_record_started": recording_started,
        "recording_touch_health_observed": bool(record_touch_samples),
        "microphone_clock_restored": bool(
            re.search(
                r"\[mic-clock\]\s+action=restore\b.*?\bstatus=ok\b.*?\bnow_ready=1\b.*?\bsai1_enabled=1\b",
                log,
            )
        ),
        "microphone_dma_started": bool(
            re.search(r"\[mic-dma\]\s+action=start\s+status=ok\b", log)
        ),
        "sustained_pcm_blocks": len(valid_mic_blocks) >= 2,
        "pcm_crc_varies": len(pcm_crcs) >= 2,
        "pcm_has_signal_span": any(
            int(block["pcm_min"]) < int(block["pcm_max"]) for block in valid_mic_blocks
        ),
        "no_microphone_timeout": not bool(
            re.search(r"\[mic-manual\].*?\bstatus=timeout\b", log)
        ),
        "touch_record_stopped": recording_stopped,
        "microphone_dma_stopped": dma_stop_index > dma_start_index >= 0,
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
        "double-tap-recording": "Collect one bounded capture containing two daily-page double taps, restored SAI clock, successful DMA start, at least two changing PCM blocks without timeout, recording stop, successful DMA shutdown, and a successful external Flash store.",
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
            "recording_touch_health": record_touch_health,
            "valid_microphone_blocks": len(valid_mic_blocks),
            "distinct_pcm_crcs": len(pcm_crcs),
            "first_wake_gesture": first_wake_gesture,
            "wake_contact_after_sleepy": wake_contact_index >= 0,
            "low_power_touch_wake_requested": touch_wake_index >= 0,
        },
        "next_action": (
            "Use the next focused acceptance item; this serial log does not prove the final <= 1 mA product-board current target."
            if status == "PASS"
            else record_touch_health["next_action"]
            if scope in {"double-tap-recording", "full"} and recording_started
            else next_actions[scope]
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
            "[mic-clock] action=restore was_ready=0 status=ok now_ready=1 sai1_enabled=1",
            "[record] touch_double_tap action=start source=4 result=0 state=recording",
            "[mic-dma] action=start status=ok sai_state=34 dma_state=2 cndtr=960 cr1=0x01FB20E1",
            "[record-touch] t=20000 service=1 ft_read=20 delta=0 ft_error=0 irq_produced=3 irq_consumed=3 pc6=1 next_poll_ms=4 contact=0 gesture_active=0 consumed=0 tap_pending=0 buffered=0 deferred=none",
            "[mic-manual] block=0 status=ok quality=voice raw_min=0x10000000 raw_max=0xE0000000 raw_zero=0 raw_same=0 raw_crc=0x11111111 slot=0 slot0_mean=100 slot0_peak=900 slot1_mean=0 slot1_peak=0 gain=8x preclip=0 pcm_min=-1200 pcm_max=1800 pcm_mean=42 pcm_zero=0 pcm_clip=0 pcm_crc=0x12345678 feed=0",
            "[mic-manual] block=200 status=ok quality=voice raw_min=0x11000000 raw_max=0xE1000000 raw_zero=0 raw_same=0 raw_crc=0x22222222 slot=0 slot0_mean=120 slot0_peak=920 slot1_mean=0 slot1_peak=0 gain=8x preclip=0 pcm_min=-1400 pcm_max=2100 pcm_mean=38 pcm_zero=0 pcm_clip=0 pcm_crc=0x87654321 feed=0",
            "[record-touch] t=20250 service=301 ft_read=70 delta=50 ft_error=0 irq_produced=3 irq_consumed=3 pc6=1 next_poll_ms=3 contact=0 gesture_active=0 consumed=0 tap_pending=0 buffered=0 deferred=none",
            "[touch-ui] daily_double_tap_recording x=100 y=100 state=recording",
            "[mic-dma] action=stop status=ok sai_state=1 dma_state=1 cr1=0x01F820E1",
            "[record] touch_double_tap action=stop source=4 stop_result=0 finish_result=0 state=transfer_ready",
            "[record] touch_double_tap action=user_store result=1 state=idle",
        ]
    )
    report = evaluate(synthetic, "synthetic-self-test", scope)
    positive_passed = report["status"] == "PASS"
    missing_dma_stop_rejected = True
    missing_health_rejected = True
    no_touch_classified = True
    i2c_failure_classified = True
    if scope in {"double-tap-recording", "full"}:
        missing_dma_stop = synthetic.replace(
            "[mic-dma] action=stop status=ok sai_state=1 dma_state=1 cr1=0x01F820E1\n",
            "",
        )
        missing_dma_stop_rejected = (
            evaluate(missing_dma_stop, "synthetic-missing-dma-stop", scope)["status"]
            != "PASS"
        )
        missing_health = re.sub(r"^\[record-touch\].*?\n?", "", synthetic, flags=re.M)
        missing_health_report = evaluate(
            missing_health,
            "synthetic-missing-recording-touch-health",
            scope,
        )
        missing_health_rejected = (
            missing_health_report["status"] != "PASS"
            and missing_health_report["observed"]["recording_touch_health"]["diagnosis"]
            == "NO_RECORDING_TOUCH_HEALTH"
        )
        second_double_tap = "[touch-ui] daily_double_tap_recording x=100 y=100 state=recording"
        no_touch = synthetic.split(second_double_tap, 1)[0]
        no_touch_report = evaluate(no_touch, "synthetic-no-second-touch", scope)
        no_touch_classified = (
            no_touch_report["observed"]["recording_touch_health"]["diagnosis"]
            == "FT6336_NO_TOUCH_DETECTION"
        )
        i2c_failure = no_touch.replace(
            "t=20250 service=301 ft_read=70 delta=50 ft_error=0",
            "t=20250 service=301 ft_read=20 delta=0 ft_error=1",
        )
        i2c_failure_report = evaluate(
            i2c_failure,
            "synthetic-recording-touch-i2c-failure",
            scope,
        )
        i2c_failure_classified = (
            i2c_failure_report["observed"]["recording_touch_health"]["diagnosis"]
            == "FT6336_I2C_READ_FAILURE"
        )
    report["self_test_checks"] = {
        "positive_fixture_passed": positive_passed,
        "missing_dma_stop_rejected": missing_dma_stop_rejected,
        "missing_recording_touch_health_rejected": missing_health_rejected,
        "no_second_touch_classified": no_touch_classified,
        "i2c_failure_classified": i2c_failure_classified,
    }
    report["status"] = (
        "PASS_STATIC_PARSER"
        if positive_passed
        and missing_dma_stop_rejected
        and missing_health_rejected
        and no_touch_classified
        and i2c_failure_classified
        else "FAIL_STATIC_PARSER"
    )
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
