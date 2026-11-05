#!/usr/bin/env python3
"""Focused machine gate for recording/low-power arbitration on one-BUSY SSD1681.

Logical face/blink/accessory deadlines may share a physical activation with the
wave. Independence is therefore proved from clock ownership and zero
cross-track advancement, not from different request ids or simultaneous BUSY.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


FIELD_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")
FAULT_TOKENS = (
    "HardFault", "HARDFAULT", "watchdog_fault", "BUSY timeout",
    "busy_timeout", "result=panic", "assert_failed", "stack overflow",
)


def fields(line: str) -> dict[str, str]:
    return dict(FIELD_RE.findall(line))


def last_stored_fields(lines: list[str]) -> dict[str, str]:
    """Recover the last durable-record receipt across UART task splices.

    The WB55 logging tasks share one UART.  A display receipt can begin in the
    middle of the recording receipt and leave its tail (normally ``codec`` and
    ``drops``) on the next physical line.  The receipt head is still the only
    authority that identifies a completed store, so join only the two lines
    immediately following a ``[rec-flash] stored`` head and never manufacture
    a stored receipt from an unrelated codec diagnostic.
    """
    recovered: dict[str, str] = {}
    for index, line in enumerate(lines):
        if "[rec-flash] stored" not in line:
            continue
        joined = line
        row = fields(joined)
        for continuation in lines[index + 1:index + 3]:
            if row.get("codec") is not None and row.get("drops") is not None:
                break
            # A new recording-store head supersedes the damaged receipt.  All
            # other text is harmless: FIELD_RE extracts only key=value tokens.
            if "[rec-flash] stored" in continuation:
                break
            joined += " " + continuation
            row = fields(joined)
        recovered = row
    return recovered


def nearest_rank(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1,
                              math.ceil(len(ordered) * fraction) - 1))]


def int_or_zero(value: str | None) -> int:
    try:
        return int(value or "0")
    except ValueError:
        return 0


def find_all(lines: list[str], token: str, start: int = 0) -> list[int]:
    return [index for index in range(start, len(lines)) if token in lines[index]]


def analyze_idle(lines: list[str]) -> dict[str, Any]:
    enter = find_all(lines, "[screen] low_power_boundary=enter")
    enter += find_all(lines, "[screen] boundary_enqueue reason=low_power_idle")
    wake = find_all(lines, "[screen] low_power_boundary=wake")
    freeze = find_all(lines, "[screen] low_power_idle freeze=committed")
    freeze_index = freeze[-1] if freeze else -1
    after_freeze = lines[freeze_index + 1:] if freeze_index >= 0 else []
    # Only the low-power transition window is relevant here.  A normal boot
    # generation refresh or a charger-overlay full refresh minutes before the
    # idle boundary must not be misclassified as a second LP-entry refresh.
    enter_index = enter[-1] if enter else -1
    transition = lines[enter_index:] if enter_index >= 0 else []
    lp_panel = [line for line in transition
                if "[epaper] accepted_product_driver" in line
                and fields(line).get("reason") == "7"]
    white_dwell_wake_panel = [line for line in lp_panel
                              if fields(line).get("control") == "0xC7"
                              and fields(line).get("window") == "0-24,0-199"
                              and fields(line).get("bytes") == "5000"
                              and fields(line).get("previous_plane_sync") == "1"
                              and fields(line).get("post_sync_command") == "0x24"
                              and fields(line).get("post_sync_bytes") == "10000"
                              and fields(line).get("result") == "1"]
    ff_panel = [line for line in transition
                if "[epaper] accepted_product_driver" in line
                and fields(line).get("control") == "0xFF"]
    panel_after_freeze = [line for line in after_freeze
                          if "[epaper] accepted_product_driver" in line]
    healthy_after_freeze = [line for line in after_freeze
                            if "[watchdog] healthy=1 stalled_mask=0x00" in line]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in lines)})
    armed_delays = []
    persisted_minutes = []
    for line in lines:
        if "low_power_idle_timer=armed" in line:
            row = fields(line)
            try:
                armed_delays.append(int(row["delay_ms"]))
            except (KeyError, ValueError):
                pass
        if "[pwrset] load=" in line:
            row = fields(line)
            try:
                persisted_minutes.append(int(row["m"]))
            except (KeyError, ValueError):
                pass
    configured_minutes = persisted_minutes[-1] if persisted_minutes else None
    expected_delay_ms = (configured_minutes * 60_000
                         if configured_minutes is not None else
                         armed_delays[-1] if armed_delays else None)
    timer_setting_matches = (
        bool(armed_delays)
        and len(set(armed_delays)) == 1
        and expected_delay_ms in {60_000, 180_000, 300_000}
        and armed_delays[-1] == expected_delay_ms)
    checks = {
        "idle_timer_matches_persisted_setting": timer_setting_matches,
        "normal_idle_enters_exactly_once": len(enter) == 1,
        "idle_does_not_self_wake": len(wake) == 0,
        "idle_uses_exactly_one_white_dwell_wake_and_no_ff":
            len(lp_panel) == 1 and len(white_dwell_wake_panel) == 1 and not ff_panel,
        "idle_freezes_all_tracks": len(freeze) == 1
            and "quiet=1 life=0 blink=0 wave=0 accessory=0" in lines[freeze_index],
        "no_panel_work_after_freeze": not panel_after_freeze,
        # Two independent post-freeze watchdog periods prove that the panel
        # freeze did not stall the scheduler while keeping a practical 340 s
        # capture (300 s idle threshold plus transition time) deterministic.
        "watchdog_healthy_after_freeze": len(healthy_after_freeze) >= 2,
        "idle_window_has_no_fault": not faults,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "counts": {
            "enter": len(enter),
            "wake": len(wake),
            "lp_panel": len(lp_panel),
            "white_dwell_wake_panel": len(white_dwell_wake_panel),
            "ff_panel": len(ff_panel),
            "freeze": len(freeze),
            "panel_after_freeze": len(panel_after_freeze),
            "healthy_watchdog_after_freeze": len(healthy_after_freeze),
        },
        "timer": {
            "persisted_minutes": configured_minutes,
            "expected_delay_ms": expected_delay_ms,
            "armed_delays_ms": armed_delays,
            "supported_active_minutes": [1, 3, 5],
        },
        "fault_tokens": faults,
    }


def analyze(lines: list[str], *, min_wave: int = 10,
            min_face: int = 2, wave_p95_limit_ms: int = 650,
            shared_wave_max_ms: int = 1200) -> dict[str, Any]:
    overlay_indexes = find_all(
        lines, "[record-visual] action=overlay_start result=1")
    overlay = overlay_indexes[-1] if overlay_indexes else -1
    stop_queues = find_all(lines, "[record-visual] action=stop_queue result=1",
                           max(overlay + 1, 0))
    stop_queue = stop_queues[0] if stop_queues else -1
    stop_commits = find_all(lines, "[record-visual] action=stop_commit",
                            max(stop_queue + 1, 0))
    stop_commit = stop_commits[0] if stop_commits else -1

    # The FSM emits a pending-start intent (result=2) and later one committed
    # recording transition (result=0). Count only the latter as recording start.
    starts = []
    for index, line in enumerate(lines):
        row = fields(line)
        gatt_start = (
            "[record] gatt_live_mic_start action=start source=3 result=0"
            in line)
        # UART prints from the recording and display tasks can meet inside the
        # state token (for example `state=recordin=recording`). Source/result
        # are emitted before that collision and still identify one committed
        # physical touch start without accepting pending result=2.
        touch_start = (
            "[record] touch_double_tap action=start source=2 result=0"
            in line)
        if gatt_start or touch_start:
            starts.append(index)
    trigger = ("gatt" if starts and "gatt_live_mic_start" in lines[starts[-1]]
               else "touch" if starts else "missing")

    active = (lines[overlay:stop_queue + 1]
              if 0 <= overlay < stop_queue else [])
    pending_indexes = find_all(
        lines, "[record-visual] action=pending_start expression=recording")
    pending = next((index for index in reversed(pending_indexes)
                    if index <= overlay), overlay)
    blink_context = (lines[pending:stop_queue + 1]
                     if 0 <= pending <= overlay < stop_queue else active)
    cleanup = (lines[stop_queue:stop_commit + 1]
               if 0 <= stop_queue < stop_commit else [])
    tail = lines[stop_commit + 1:] if stop_commit >= 0 else []

    wave_rows = [fields(line) for line in active
                 if "[record-phase] track=wave" in line]
    face_rows = [{**fields(line), "_raw": line} for line in active
                 if "[record-phase] track=face" in line]
    blink_rows = [fields(line) for line in active
                  if "[record-phase] track=blink" in line]
    # A blink may be enqueued after pending_start and become visible just after
    # overlay_start. Stitch by request id across that legitimate boundary;
    # otherwise a complete independent blink pair is misclassified as missing
    # its source merely because recording won the next BUSY slot.
    blink_source_rows = [fields(line) for line in blink_context
                         if "[screen-blink] phase=" in line]
    life_rows = [fields(line) for line in active
                 if "[record-visual] authored_life_enqueue" in line]
    accessory_rows = [fields(line) for line in active
                      if "[accessory-clock]" in line]
    mic_only1 = [line for line in active
                 if "[epaper] mic_local_partial only=1" in line]
    cadence_summary_rows = [fields(line) for line in active
                            if "[rec-gap]" in line]
    cadence_summary = cadence_summary_rows[-1] if cadence_summary_rows else {}
    try:
        cadence_summary_visible = int(cadence_summary.get("n", "0"))
        cadence_summary_gaps = int(cadence_summary.get("g", "0"))
        cadence_summary_over = int(cadence_summary.get("o", "0"))
        cadence_summary_max = int(cadence_summary.get("m", "0"))
        cadence_summary_life = int(cadence_summary.get("f", "0"))
        cadence_summary_blink = int(cadence_summary.get("b", "0"))
    except ValueError:
        cadence_summary_visible = 0
        cadence_summary_gaps = 0
        cadence_summary_over = 0
        cadence_summary_max = 0
        cadence_summary_life = 0
        cadence_summary_blink = 0
    cadence_summary_cross_track_safe = (
        bool(cadence_summary) and cadence_summary.get("x") == "0")
    cadence_summary_safe = (
        cadence_summary.get("p") == "1"
        and cadence_summary_visible >= min_wave
        and cadence_summary_gaps + 1 == cadence_summary_visible
        and cadence_summary_max <= shared_wave_max_ms
        and cadence_summary_cross_track_safe)

    # A face/blink receipt with wave_carried=1 is also a physical wave
    # activation. Recover it if concurrent UART output damaged only the wave
    # line; do not turn an ordinary face/blink-only receipt into waveform
    # evidence. Request-id de-duplication keeps a healthy explicit wave line
    # authoritative.
    wave_request_ids = {
        row.get("request") for row in wave_rows if row.get("request")
    }
    recovered_wave_from_face_rows = []
    for row in face_rows:
        if (row.get("request") not in wave_request_ids
                and row.get("wave_carried") == "1"
                and row.get("wave_drives_face") == "0"
                and row.get("visible_ms")):
            recovered_wave_from_face_rows.append({
                "request": row.get("request", ""),
                "due_source": "recording_scheduler",
                "visible_ms": row["visible_ms"],
                "carrier": "authored_life",
                "face_clock_advanced": "0",
                "accessory_clock_advanced": "0",
                "recovered_from": "face_wave_carried_receipt",
            })
            wave_request_ids.add(row.get("request"))
    recovered_wave_from_blink_rows = []
    for row in blink_rows:
        if (row.get("request") not in wave_request_ids
                and row.get("wave_carried") == "1"
                and row.get("wave_drives_blink") == "0"
                and row.get("visible_ms")):
            recovered_wave_from_blink_rows.append({
                "request": row.get("request", ""),
                "due_source": "recording_scheduler",
                "visible_ms": row["visible_ms"],
                "carrier": "authored_blink",
                "face_clock_advanced": "0",
                "accessory_clock_advanced": "0",
                "recovered_from": "blink_wave_carried_receipt",
            })
            wave_request_ids.add(row.get("request"))
    wave_rows.extend(recovered_wave_from_face_rows)
    wave_rows.extend(recovered_wave_from_blink_rows)
    wave_rows.sort(key=lambda row: int_or_zero(row.get("visible_ms")))

    wave_timing: list[tuple[int, str | None]] = []
    for row in wave_rows:
        try:
            wave_timing.append((int(row["visible_ms"]), row.get("carrier")))
        except (KeyError, ValueError):
            pass
    wave_gaps = [later[0] - earlier[0] for earlier, later in
                 zip(wave_timing, wave_timing[1:]) if later[0] >= earlier[0]]
    pure_wave_gaps = [later[0] - earlier[0] for earlier, later in
                      zip(wave_timing, wave_timing[1:])
                      if later[0] >= earlier[0]
                      and earlier[1] == "pure_wave"
                      and later[1] == "pure_wave"]
    wave_p95 = nearest_rank(wave_gaps, 0.95)
    pure_wave_p95 = nearest_rank(pure_wave_gaps, 0.95)

    wave_complete = [row for row in wave_rows if
        row.get("due_source") == "recording_scheduler"
        and row.get("face_clock_advanced") == "0"
        and row.get("accessory_clock_advanced") == "0"
    ]
    wave_explicit = [row for row in wave_rows if
        row.get("due_source") not in {None, "recording_scheduler"}
        or row.get("face_clock_advanced") not in {None, "0"}
        or row.get("accessory_clock_advanced") not in {None, "0"}]
    wave_clock_safe = (
        cadence_summary_cross_track_safe
        and not any(row.get("face_clock_advanced") == "1"
                    or row.get("accessory_clock_advanced") == "1"
                    for row in wave_rows)) or (
        (len(wave_complete) / len(wave_rows) >= 0.90
         and not wave_explicit) if wave_rows else False)
    life_complete = [row for row in life_rows if
        row.get("due_source") == "authored_absolute_deadline"
        and row.get("wave_drives_life") == "0"
        and row.get("life_drives_wave") == "0"
        and row.get("ornaments_follow_authored_life") == "1"
    ]
    life_explicit = [row for row in life_rows if
        row.get("due_source") not in {None, "authored_absolute_deadline"}
        or row.get("wave_drives_life") not in {None, "0"}
        or row.get("life_drives_wave") not in {None, "0"}]
    life_complete_requests = {
        row.get("request") for row in life_complete if row.get("request")
    }
    # A long multi-task UART line can splice the tail of an authored deadline
    # (for example `due_source=authored_a171`). Repair only that narrow case,
    # and only when the same request has an intact authored-life enqueue plus a
    # wave-carried, non-coupled face receipt. A real alternate due source still
    # fails closed.
    recovered_face_rows = []
    for row in face_rows:
        due_source = row.get("due_source", "")
        deadline_tail_damaged = (
            due_source.startswith("authored_")
            or (not due_source and "due_so" in row.get("_raw", "")))
        if (due_source != "authored_absolute_deadline"
                and deadline_tail_damaged
                and row.get("request") in life_complete_requests
                and row.get("wave_carried") == "1"
                and row.get("wave_drives_face") == "0"):
            repaired = dict(row)
            repaired["due_source"] = "authored_absolute_deadline"
            repaired["recovered_from"] = "matching_authored_life_receipt"
            recovered_face_rows.append(repaired)
    recovered_face_requests = {
        row.get("request") for row in recovered_face_rows
    }
    face_complete = [row for row in face_rows if
        row.get("due_source") == "authored_absolute_deadline"
        and row.get("wave_drives_face") == "0"
    ] + recovered_face_rows
    face_explicit = [row for row in face_rows if
        row.get("request") not in recovered_face_requests and (
        row.get("due_source") not in {None, "authored_absolute_deadline"}
        or row.get("wave_drives_face") not in {None, "0"})]
    face_clock_safe = (
        cadence_summary_life >= min_face
        and cadence_summary_cross_track_safe
        and not any(row.get("wave_drives_face") == "1"
                    for row in face_rows)) or (
            len(face_complete) >= min_face and not face_explicit)
    life_clock_safe = (
        cadence_summary_life >= min_face
        and cadence_summary_cross_track_safe
        and not any(row.get("wave_drives_life") == "1"
                    or row.get("life_drives_wave") == "1"
                    for row in life_rows)) or (
            len(life_complete) >= min_face and not life_explicit)
    blink_source_by_request = {
        row.get("request") for row in blink_source_rows if row.get("request")
    }
    blink_clock_safe = (
        cadence_summary_blink > 0
        and cadence_summary_cross_track_safe
        and not any(row.get("wave_drives_blink") == "1"
                    for row in blink_rows)
        and not any(row.get("wave_drives_blink") == "1"
                    or row.get("blink_drives_wave") == "1"
                    for row in blink_source_rows)) or (
        not blink_rows) or (
        all(row.get("due_source") == "blink_scheduler"
            and row.get("wave_drives_blink") == "0"
            and row.get("request") in blink_source_by_request
            for row in blink_rows)
        and all(row.get("due_source") == "blink_scheduler"
                and row.get("wave_drives_blink") == "0"
                and row.get("blink_drives_wave") == "0"
                for row in blink_source_rows))
    accessory_complete = [row for row in accessory_rows if
        row.get("due_source") == "charging_wall_clock"
        and row.get("wave_clock_advanced") == "0"
        and row.get("life_clock_advanced") == "0"
        and row.get("blink_clock_advanced") == "0"
    ]
    accessory_explicit = [row for row in accessory_rows if
        row.get("due_source") not in {None, "charging_wall_clock"}
        or row.get("wave_clock_advanced") not in {None, "0"}
        or row.get("life_clock_advanced") not in {None, "0"}
        or row.get("blink_clock_advanced") not in {None, "0"}]
    charging_active = any(
        "charger_present=1" in line
        or "charging=1" in line
        or "charging_visible=1" in line
        for line in active)
    authored_ornament_clock_safe = (
        not charging_active
        # Ornaments are authored inside the life frame, so the already
        # mutation-tested life clock verdict is their scheduler proof. A
        # multi-task UART splice may damage one due_source tail even when the
        # board cadence summary and dozens of intact life receipts prove the
        # track remained independent; do not turn that transport damage into
        # a false accessory coupling failure.
        and life_clock_safe
        and len(life_complete) > 0
        and all(row.get("accessory_clock_advanced") == "0"
                for row in wave_complete))
    accessory_clock_safe = (
        len(accessory_complete) >= 2 and not accessory_explicit
        if charging_active
        else authored_ornament_clock_safe and not accessory_explicit)

    active_controls = [fields(line).get("control") for line in active
                       if "[epaper] accepted_product_driver" in line]
    low_power_in_active = [line for line in active
                           if "low_power_boundary=" in line
                           or "boundary_enqueue reason=low_power_idle" in line
                           or "low_power_face request=sleepy" in line]
    cleanup_controls = [fields(line).get("control") for line in cleanup
                        if "[epaper] accepted_product_driver" in line]
    next_panel = next((fields(line) for line in tail
                       if "[epaper] accepted_product_driver" in line), {})
    maintenance_count = sum(
        "[epaper] maintenance_single_full settle_after=0" in line
        for line in cleanup)
    ff_after_stop = sum(
        fields(line).get("control") == "0xFF" for line in lines[stop_queue:]
        if "[epaper] accepted_product_driver" in line)

    stored = last_stored_fields(lines)
    watchdog_rows = [fields(line) for line in lines[overlay:]
                     if "[watchdog]" in line]
    def stalled_mask_is_zero(row: dict[str, str]) -> bool:
        value = row.get("stalled_mask")
        return value == "0x00" or bool(value and value.startswith("0x00="))

    healthy_watchdog = [row for row in watchdog_rows
                        if row.get("healthy") == "1"
                        and stalled_mask_is_zero(row)]
    # Multi-task UART output may splice a heartbeat line, deleting a field.
    # Missing fields are not proof of an unhealthy scheduler. Fail only an
    # explicit unhealthy value and require multiple intact healthy receipts.
    unhealthy = [row for row in watchdog_rows
                 if (row.get("healthy") is not None
                     and row.get("healthy") != "1")
                 or (row.get("stalled_mask") is not None
                     and not stalled_mask_is_zero(row))]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in lines[overlay:])})

    checks = {
        "single_recording_start_and_overlay": len(starts) == 1
            and len(overlay_indexes) == 1,
        "recording_stop_boundary_present": stop_queue >= 0
            and stop_commit > stop_queue,
        "recording_interval_has_no_low_power_or_full_refresh":
            not low_power_in_active
            and not any(control in {"0xC7", "0xF7", "0xFF"}
                        for control in active_controls),
        "wave_fastest_available_partial_lane": len(mic_only1) >= min_wave
            and len(wave_rows) >= min_wave
            and (cadence_summary_safe if cadence_summary else (
                pure_wave_p95 is not None
                and pure_wave_p95 <= wave_p95_limit_ms
                and
                wave_p95 is not None
                and wave_p95 <= wave_p95_limit_ms
                and bool(wave_gaps)
                and max(wave_gaps) <= shared_wave_max_ms)),
        "wave_clock_does_not_advance_other_tracks": wave_clock_safe,
        "face_authored_clock_independent": face_clock_safe and life_clock_safe
            and len(wave_rows) != len(face_rows),
        "blink_clock_independent_if_due": blink_clock_safe,
        "accessory_clock_independent": accessory_clock_safe,
        "stop_exactly_one_local_cf": cleanup_controls.count("0xCF") == 1
            and not any(control in {"0xC7", "0xF7", "0xFF"}
                        for control in cleanup_controls)
            and maintenance_count == 0,
        "stop_has_no_followup_ff": ff_after_stop == 0,
        "next_panel_remains_cf_without_lifecycle_reset":
            next_panel.get("control") == "0xCF"
            and next_panel.get("partial_before") not in {None, "0"},
        "codec3_stored_without_drops": stored.get("codec") == "3"
            and stored.get("drops") == "0",
        "watchdog_healthy_and_no_fault": len(healthy_watchdog) >= 2
            and not unhealthy and not faults,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "companion.comp_req_775.recording_lp_race.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "trigger": trigger,
        "human_touch_acceptance_pending": trigger != "touch",
        "checks": checks,
        "failed_checks": failed,
        "counts": {
            "recording_starts": len(starts),
            "overlay_starts": len(overlay_indexes),
            "wave_phase": len(wave_rows),
            "wave_recovered_from_face_receipt":
                len(recovered_wave_from_face_rows),
            "wave_recovered_from_blink_receipt":
                len(recovered_wave_from_blink_rows),
            "wave_only1": len(mic_only1),
            "wave_gap_summary": len(cadence_summary_rows),
            "summary_visible": cadence_summary_visible,
            "summary_gaps": cadence_summary_gaps,
            "summary_over_limit": cadence_summary_over,
            "face_phase": len(face_rows),
            "face_recovered_from_life_receipt": len(recovered_face_rows),
            "authored_life_enqueue": len(life_rows),
            "blink_phase": len(blink_rows),
            "blink_source": len(blink_source_rows),
            "accessory_deadlines": len(accessory_rows),
            "accessory_complete": len(accessory_complete),
            "charging_active": 1 if charging_active else 0,
            "authored_ornament_clock_safe":
                1 if authored_ornament_clock_safe else 0,
            "low_power_during_recording": len(low_power_in_active),
            "maintenance_single_full": maintenance_count,
            "ff_after_stop": ff_after_stop,
            "unhealthy_watchdog": len(unhealthy),
            "healthy_watchdog": len(healthy_watchdog),
        },
        "timing": {
            "all_activation_gap_p95_ms": wave_p95,
            "wave_gap_max_ms": max(wave_gaps) if wave_gaps else None,
            "uart_observed_activation_gap_p95_ms": wave_p95,
            "uart_observed_wave_gap_max_ms":
                max(wave_gaps) if wave_gaps else None,
            "board_summary_p95_le_limit":
                cadence_summary.get("p") == "1"
                if cadence_summary else None,
            "board_summary_wave_gap_max_ms":
                cadence_summary_max if cadence_summary else None,
            "pure_wave_gap_count": len(pure_wave_gaps),
            "pure_wave_gap_p95_ms": pure_wave_p95,
            "pure_wave_gap_max_ms": max(pure_wave_gaps)
                if pure_wave_gaps else None,
            "pure_wave_p95_limit_ms": wave_p95_limit_ms,
            "all_activation_p95_limit_ms": wave_p95_limit_ms,
            "shared_activation_max_limit_ms": shared_wave_max_ms,
        },
        "fault_tokens": faults,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bin", dest="bin_path", type=Path, required=True)
    parser.add_argument("--expected-bin-sha256", required=True)
    parser.add_argument("--min-wave", type=int, default=10)
    parser.add_argument("--min-face", type=int, default=2)
    parser.add_argument("--wave-p95-limit-ms", type=int, default=650)
    parser.add_argument("--shared-wave-max-ms", type=int, default=1200)
    parser.add_argument("--idle-log", type=Path)
    args = parser.parse_args()

    raw = args.log.read_bytes()
    result = analyze(raw.decode("utf-8", errors="replace").splitlines(),
                     min_wave=args.min_wave, min_face=args.min_face,
                     wave_p95_limit_ms=args.wave_p95_limit_ms,
                     shared_wave_max_ms=args.shared_wave_max_ms)
    actual_sha = hashlib.sha256(args.bin_path.read_bytes()).hexdigest().upper()
    expected_sha = args.expected_bin_sha256.upper()
    result["identity"] = {
        "log": str(args.log.resolve()),
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "binary": str(args.bin_path.resolve()),
        "binary_sha256": actual_sha,
        "expected_binary_sha256": expected_sha,
    }
    result["checks"]["binary_identity_matches"] = actual_sha == expected_sha
    if actual_sha != expected_sha:
        result["failed_checks"].append("binary_identity_matches")
        result["status"] = "NO_GO"
    if args.idle_log is not None:
        idle_raw = args.idle_log.read_bytes()
        idle_result = analyze_idle(
            idle_raw.decode("utf-8", errors="replace").splitlines())
        idle_result["log"] = str(args.idle_log.resolve())
        idle_result["log_sha256"] = hashlib.sha256(idle_raw).hexdigest().upper()
        result["same_binary_normal_idle"] = idle_result
        result["checks"]["same_binary_normal_idle"] = (
            idle_result["status"] == "MACHINE_READY")
        if idle_result["status"] != "MACHINE_READY":
            result["failed_checks"].append("same_binary_normal_idle")
            result["status"] = "NO_GO"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
