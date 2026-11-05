#!/usr/bin/env python3
"""Unified machine gate for the final COMP-REQ-775 SSD1681 screen path.

The SSD1681 has one BUSY line.  A face/accessory may therefore ride the next
safe physical activation, but its logical deadline must never be advanced by
the recording wave.  This verifier deliberately checks those two concepts
separately.
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
START_TOKEN = "[record] touch_double_tap action=start source=2 result=0 state=recording"
STOP_TOKEN = "[record] touch_double_tap action=stop source=2"
GATT_START_TOKEN = (
    "[record] gatt_live_mic_start action=start source=3 result=0 state=recording"
)
GATT_STOP_TOKEN = "[record] gatt_recording_stop action=stop source=3"
FAULT_TOKENS = (
    "HardFault",
    "HARDFAULT",
    "watchdog_fault",
    "previous_reset=iwdg",
    "previous_reset=system fatal=",
    "BUSY timeout",
    "busy_timeout",
    "panel result=failed",
    "result=panic",
    "assert_failed",
    "stack overflow",
)


def fields(line: str) -> dict[str, str]:
    return dict(FIELD_RE.findall(line))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def nearest_rank(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1,
                              math.ceil(len(ordered) * fraction) - 1))]


def _latest_recording_segment(lines: list[str]) -> tuple[int | None, int | None]:
    starts = [i for i, line in enumerate(lines)
              if START_TOKEN in line or GATT_START_TOKEN in line]
    if not starts:
        return None, None
    start = starts[-1]
    stop_token = (STOP_TOKEN if START_TOKEN in lines[start]
                  else GATT_STOP_TOKEN)
    stops = [i for i in range(start + 1, len(lines))
             if stop_token in lines[i] and "stop_result=0" in lines[i]]
    return start, stops[0] if stops else None


def _extract_function(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    return ""


def analyze_scheduler_probe(
    log_path: Path,
    *,
    min_recording_duration_ms: int,
    min_wave: int,
    min_face: int,
    wave_p95_limit_ms: int,
) -> dict[str, Any]:
    """Audit a long recording scheduler run without claiming touch closure."""
    raw = log_path.read_bytes()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    # The current async GATT/touch path makes the visual overlay visible before
    # microphone preparation reaches state=recording. Start the scheduler audit
    # at that authored overlay boundary so the bootstrap waves and life slots
    # are not discarded merely because capture startup is asynchronous.
    overlay_token = ("[record-visual] action=overlay_start result=1 "
                     "initial_dispatch=wave_bootstrap")
    overlay_starts = [i for i, line in enumerate(lines)
                      if overlay_token in line]
    if not overlay_starts:
        return {
            "status": "NO_GO",
            "checks": {"actual_recording_start_stop": False},
            "failed_checks": ["actual_recording_start_stop"],
            "log": str(log_path.resolve()),
            "log_sha256": sha256(raw),
        }
    start = overlay_starts[-1]
    trigger_rows = lines[start:min(len(lines), start + 160)]
    trigger = ("touch_double_tap"
               if any(START_TOKEN in line for line in trigger_rows)
               else "gatt_control"
               if any("[record] gatt_live_mic_start action=start source=3 "
                      "result=0 state=recording" in line
                      for line in trigger_rows)
               else "unknown")
    if trigger == "unknown":
        return {
            "status": "NO_GO",
            "checks": {"actual_recording_start_stop": False},
            "failed_checks": ["actual_recording_start_stop"],
            "log": str(log_path.resolve()),
            "log_sha256": sha256(raw),
        }
    stop_token = (STOP_TOKEN if trigger == "touch_double_tap"
                  else "[record] gatt_recording_stop action=stop source=3")
    stops = [i for i in range(start + 1, len(lines))
             if stop_token in lines[i] and "stop_result=0" in lines[i]]
    stop = stops[0] if stops else None
    segment = lines[start:stop + 1] if stop is not None else []

    wave_lines = [line for line in segment
                  if "[record-phase] track=wave" in line]
    wave_events: list[tuple[int, int]] = []
    wave_timing_events: list[tuple[int, int]] = []
    wave_good = 0
    explicit_violations: list[str] = []
    allowed_carriers = {"pure_wave", "authored_life"}
    for line in wave_lines:
        row = fields(line)
        if (row.get("face_clock_advanced") not in {None, "0"}
                or row.get("accessory_clock_advanced") not in {None, "0"}
                or row.get("due_source") in {
                    "authored_absolute_deadline", "blink_scheduler",
                    "charging_wall_clock"}
                or row.get("carrier") in {
                    "co_paint", "shared_face_wave", "pure_accessory"}):
            explicit_violations.append(line)
            continue
        try:
            wave_timing_events.append((int(row["request"]),
                                       int(row["visible_ms"])))
        except (KeyError, ValueError):
            pass
        carrier_contract = (
            (row.get("carrier") == "pure_wave" and row.get("only") == "1")
            or (row.get("carrier") == "authored_life"
                and row.get("only") == "0"))
        complete = (
            row.get("due_source") == "recording_scheduler"
            and row.get("face_clock_advanced") == "0"
            and row.get("accessory_clock_advanced") == "0"
            and row.get("carrier") in allowed_carriers
            and carrier_contract)
        if not complete:
            continue
        try:
            wave_events.append((int(row["request"]), int(row["visible_ms"])))
            wave_good += 1
        except (KeyError, ValueError):
            pass
    gaps = [later[1] - earlier[1]
            for earlier, later in zip(wave_timing_events,
                                      wave_timing_events[1:])
            if later[0] == earlier[0] + 1 and later[1] >= earlier[1]]
    wave_p95 = nearest_rank(gaps, 0.95)
    wave_max = max(gaps) if gaps else None
    visible_span = (wave_timing_events[-1][1] - wave_timing_events[0][1]
                    if len(wave_timing_events) >= 2 else 0)
    wave_parse_fraction = (len(wave_timing_events) / len(wave_lines)
                           if wave_lines else 0.0)
    wave_contract_parse_fraction = (wave_good / len(wave_lines)
                                    if wave_lines else 0.0)

    face_rows = [fields(line) for line in segment
                 if "[record-phase] track=face" in line]
    face_good = [row for row in face_rows
                 if row.get("due_source") == "authored_absolute_deadline"
                 and row.get("wave_drives_face") == "0"]
    face_explicit = [row for row in face_rows
                     if row.get("wave_drives_face") not in {None, "0"}
                     or row.get("due_source") in {
                         "recording_scheduler", "blink_scheduler",
                         "charging_wall_clock"}]
    face_parse_fraction = len(face_good) / len(face_rows) if face_rows else 0.0

    enqueue_rows = [fields(line) for line in segment
                    if "[record-visual] authored_life_enqueue" in line]
    enqueue_good = [row for row in enqueue_rows
                    if row.get("due_source") == "authored_absolute_deadline"
                    and row.get("wave_drives_life") == "0"
                    and row.get("life_drives_wave") == "0"
                    and row.get("ornaments_follow_authored_life") == "1"]
    accessory_rows = [fields(line) for line in segment
                      if "[accessory-clock]" in line]
    accessory_good = [row for row in accessory_rows if
        row.get("wave_clock_advanced") == "0"
        and row.get("life_clock_advanced") == "0"
        and row.get("blink_clock_advanced") == "0"]
    accessory_explicit = [row for row in accessory_rows if
                          row.get("wave_clock_advanced") not in {None, "0"}
                          or row.get("life_clock_advanced") not in {None, "0"}
                          or row.get("blink_clock_advanced") not in {None, "0"}]
    accessory_safe = (len(accessory_rows) >= 2
                      and len(accessory_good) / len(accessory_rows) >= 0.90
                      and not accessory_explicit)
    blink_rows = [fields(line) for line in segment
                  if "[record-phase] track=blink" in line]
    blink_safe = (not blink_rows or any(
        row.get("due_source") == "blink_scheduler"
        and row.get("wave_carried") == "0"
        and row.get("wave_drives_blink") == "0"
        for row in blink_rows))
    option2_rows = [fields(line) for line in lines
                    if "[record-visual] option2=1" in line]
    option2 = option2_rows[-1] if option2_rows else {}
    overlay_rows = [fields(line) for line in lines
                    if "[record-visual] action=overlay_start result=1" in line]
    overlay = overlay_rows[-1] if overlay_rows else {}
    live_hot_rows = [fields(line) for line in segment
                     if "[rec-flash] live_hot" in line]
    watchdog_rows = [fields(line) for line in segment
                     if "[watchdog]" in line and "healthy=" in line]
    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in segment)})
    forbidden_controls = [fields(line).get("control") for line in segment
                          if "[epaper] accepted_product_driver" in line
                          and fields(line).get("control") in
                          {"0xC7", "0xF7", "0xFF"}]

    checks = {
        "actual_recording_start_stop": stop is not None,
        "visible_scheduler_span_at_least_minimum": (
            visible_span >= min_recording_duration_ms),
        "wave_first_available_p95": (
            len(wave_lines) >= min_wave
            and wave_parse_fraction >= 0.90
            and wave_contract_parse_fraction >= 0.85
            and not explicit_violations
            and wave_p95 is not None and wave_p95 <= wave_p95_limit_ms),
        "authored_face_clock_independent": (
            len(face_rows) >= min_face and len(face_rows) < len(wave_lines)
            and face_parse_fraction >= 0.80 and not face_explicit
            and len(enqueue_good) >= min_face),
        "accessory_clock_independent": accessory_safe,
        "blink_clock_independent_if_due": blink_safe,
        "option2_contract_present": (
            option2.get("same_as_offline") == "1"
            and option2.get("cadence_ms") == "480"
            and option2.get("no_soft_advance") == "1"
            and option2.get("no_cross_track_advance") == "1"
            and overlay.get("post_commit_dwell_ms") == "0"
            and overlay.get("no_predeadline_wave_suppression") == "1"),
        "capture_and_watchdog_drop_free": (
            bool(live_hot_rows)
            and all(row.get("drops") == "0" for row in live_hot_rows)
            and all(row.get("healthy") == "1"
                    and row.get("stalled_mask") == "0x00"
                    for row in watchdog_rows)),
        "no_fault_or_recording_full_refresh": not faults and not forbidden_controls,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "status": "MACHINE_READY_SCHEDULER_ONLY" if not failed else "NO_GO",
        "trigger": trigger,
        "checks": checks,
        "failed_checks": failed,
        "wave_count": len(wave_lines),
        "wave_parse_fraction": wave_parse_fraction,
        "wave_contract_parse_fraction": wave_contract_parse_fraction,
        "wave_gap_p95_ms": wave_p95,
        "wave_gap_max_ms": wave_max,
        "wave_visible_span_ms": visible_span,
        "face_count": len(face_rows),
        "face_parse_fraction": face_parse_fraction,
        "accessory_count": len(accessory_rows),
        "blink_count": len(blink_rows),
        "uart_spliced_wave_rows": len(wave_lines) - len(wave_timing_events),
        "explicit_violation_count": len(explicit_violations) + len(face_explicit),
        "fault_tokens": faults,
        "forbidden_controls": forbidden_controls,
        "log": str(log_path.resolve()),
        "log_sha256": sha256(raw),
        "note": ("This proves current single-BUSY scheduler causality. An "
                 "authored-life deadline may share its physical activation "
                 "with a wave, but wave_drives_face/life and all cross-track "
                 "advance fields must remain zero. A GATT trigger does not "
                 "replace the final physical touch gesture."),
    }


def analyze(
    log_path: Path,
    driver_path: Path,
    bin_path: Path,
    expected_bin_sha256: str,
    ota_layout_path: Path,
    *,
    lifecycle_log_path: Path | None = None,
    scheduler_log_path: Path | None = None,
    min_recording_duration_ms: int = 10_000,
    min_wave: int = 12,
    min_face: int = 2,
    min_partial_before_lp: int = 140,
    wave_p95_limit_ms: int = 700,
) -> dict[str, Any]:
    log_raw = log_path.read_bytes()
    lines = log_raw.decode("utf-8", errors="replace").splitlines()
    lifecycle_raw = (lifecycle_log_path.read_bytes()
                     if lifecycle_log_path is not None else log_raw)
    lifecycle_lines = lifecycle_raw.decode(
        "utf-8", errors="replace").splitlines()
    driver_raw = driver_path.read_bytes()
    driver = driver_raw.decode("utf-8", errors="replace")
    bin_raw = bin_path.read_bytes()
    ota_layout = json.loads(ota_layout_path.read_text(encoding="utf-8-sig"))

    start, stop = _latest_recording_segment(lines)
    segment = lines[start:stop + 1] if start is not None and stop is not None else []
    before = lines[:start] if start is not None else lines
    after = lines[stop + 1:] if stop is not None else []

    wave_lines = [(line_number, line) for line_number, line in enumerate(segment)
                  if "[record-phase] track=wave" in line]
    face_lines = [line for line in segment
                  if "[record-phase] track=face" in line]
    wave_rows = [fields(line) for _, line in wave_lines]
    face_rows = [fields(line) for line in face_lines]
    life_enqueue_rows = [fields(line) for line in segment
                         if "[record-visual] authored_life_enqueue" in line]
    screen_life_recording = [fields(line) for line in segment
                             if "[screen-life] family=" in line]
    ordinary_source_lines = before + after
    if lifecycle_log_path is not None:
        ordinary_source_lines += lifecycle_lines
    screen_life_ordinary = [fields(line) for line in ordinary_source_lines
                            if "[screen-life] family=" in line]
    accessory_recording = [fields(line) for line in segment
                           if "[accessory-clock]" in line]
    blink_source_lines = (lines if lifecycle_log_path is None
                          else lines + lifecycle_lines)
    blink_rows = [fields(line) for line in blink_source_lines
                  if "[screen-blink] phase=" in line]
    health_source_lines = (lines if lifecycle_log_path is None
                           else lines + lifecycle_lines)
    # Boot/setup watchdog diagnostics are not health samples.  Only rows that
    # explicitly carry healthy= participate in the stall gate.
    watchdog_rows = [fields(line) for line in health_source_lines
                     if "[watchdog]" in line and "healthy=" in line]

    # START may be preceded by a long asynchronous flash erase while the
    # recording visual is already alive.  Select the latest exact contract
    # row before START instead of imposing a fragile UART-line distance.
    overlay_rows = [fields(line) for line in lines[:(start or 0) + 1]
                    if "[record-visual] action=overlay_start result=1" in line]
    option2_rows = [fields(line) for line in lines[:(start or 0) + 1]
                    if "[record-visual] option2=1" in line]
    trace_rows = [fields(line) for line in lines
                  if "[record-visual] action=overlay_trace" in line]

    stored_rows = [fields(line) for line in after
                   if "[rec-flash] stored" in line]
    stored = stored_rows[0] if stored_rows else {}
    try:
        stored_duration = int(stored.get("duration_ms", "0"))
        stored_bytes = int(stored.get("bytes", "0"))
    except ValueError:
        stored_duration = stored_bytes = 0

    wave_events: list[dict[str, Any]] = []
    wave_timing_events: list[dict[str, int]] = []
    wave_explicit_violations: list[dict[str, str]] = []
    # One SSD1681 BUSY line means an independently due authored-life frame may
    # share the next physical wave activation.  Independence is the clock
    # ownership below, not a prohibition on that safe carrier.
    allowed_carriers = {"pure_wave", "authored_life"}
    for (line_number, _), row in zip(wave_lines, wave_rows):
        try:
            request_number = int(row["request"])
            visible_number = int(row["visible_ms"])
        except (KeyError, ValueError):
            continue
        explicit_violation = (
            (row.get("due_source") in {
                "authored_absolute_deadline", "blink_scheduler",
                "charging_wall_clock"})
            or ("face_clock_advanced" in row and
                row["face_clock_advanced"] != "0")
            or ("accessory_clock_advanced" in row and
                row["accessory_clock_advanced"] != "0")
            or (row.get("carrier") in {
                "co_paint", "shared_face_wave", "pure_accessory"})
            or (row.get("carrier") == "pure_wave" and row.get("only") != "1")
            or (row.get("carrier") == "authored_life" and row.get("only") != "0")
            or row.get("carrier") == "authored_blink")
        if explicit_violation:
            wave_explicit_violations.append(row)
            continue
        try:
            wave_timing_events.append({
                "request": request_number,
                "visible_ms": visible_number,
            })
        except (KeyError, ValueError):
            pass
        complete = (
            row.get("due_source") == "recording_scheduler"
            and row.get("face_clock_advanced") == "0"
            and row.get("accessory_clock_advanced") == "0"
            and row.get("carrier") in allowed_carriers
            and ((row.get("carrier") == "pure_wave" and row.get("only") == "1")
                 or (row.get("carrier") == "authored_life"
                     and row.get("only") == "0")))
        if complete:
            wave_events.append({
                "line_number": line_number,
                "request": request_number,
                "visible_ms": visible_number,
                "row": row,
            })
    wave_gaps: list[int] = []
    for earlier, later in zip(wave_timing_events, wave_timing_events[1:]):
        # RTOS tasks share the UART.  If an intervening record-phase line was
        # spliced and lost visible_ms, request ids reveal that the physical
        # wave commit existed; never turn that diagnostic loss into a fake
        # multi-frame gap.  An actual missing wave remains visible as an
        # explicit non-wave request and is caught by the carrier/clock gates.
        if later["request"] != earlier["request"] + 1:
            continue
        gap = later["visible_ms"] - earlier["visible_ms"]
        if gap >= 0:
            wave_gaps.append(gap)
    wave_p95 = nearest_rank(wave_gaps, 0.95)
    wave_max = max(wave_gaps) if wave_gaps else None

    pure_wave_rows = [row for row in wave_rows
                      if row.get("carrier") == "pure_wave"]
    carried_wave_rows = [row for row in wave_rows
                         if row.get("carrier") == "authored_life"]
    wave_parse_fraction = (len(wave_timing_events) / len(wave_rows)
                           if wave_rows else 0.0)
    wave_contract_parse_fraction = (len(wave_events) / len(wave_rows)
                                    if wave_rows else 0.0)
    all_wave_clock_safe = (
        bool(wave_rows) and wave_parse_fraction >= 0.90
        and wave_contract_parse_fraction >= 0.85
        and not wave_explicit_violations)

    face_good = [row for row in face_rows
                 if row.get("due_source") == "authored_absolute_deadline"
                 and row.get("wave_drives_face") == "0"]
    face_explicit_violations = [row for row in face_rows if
                                (row.get("due_source") in {
                                    "recording_scheduler", "blink_scheduler",
                                    "charging_wall_clock"})
                                or ("wave_drives_face" in row and
                                    row["wave_drives_face"] != "0")]
    face_parse_fraction = (len(face_good) / len(face_rows)
                           if face_rows else 0.0)
    all_face_clock_safe = (bool(face_rows) and face_parse_fraction >= 0.80
                           and not face_explicit_violations)

    enqueue_good = [row for row in life_enqueue_rows
                    if row.get("due_source") == "authored_absolute_deadline"
                    and row.get("wave_drives_life") == "0"
                    and row.get("life_drives_wave") == "0"
                    and row.get("ornaments_follow_authored_life") == "1"]
    enqueue_explicit_violations = [row for row in life_enqueue_rows if
                                   (row.get("due_source") in {
                                       "recording_scheduler", "blink_scheduler",
                                       "charging_wall_clock"})
                                   or ("wave_drives_life" in row and
                                       row["wave_drives_life"] != "0")
                                   or ("life_drives_wave" in row and
                                       row["life_drives_wave"] != "0")]
    enqueue_parse_fraction = (len(enqueue_good) / len(life_enqueue_rows)
                              if life_enqueue_rows else 0.0)
    all_enqueue_safe = (bool(life_enqueue_rows)
                        and enqueue_parse_fraction >= 0.80
                        and not enqueue_explicit_violations)

    def dwell_values(rows: list[dict[str, str]]) -> list[int]:
        values: list[int] = []
        for row in rows:
            try:
                values.append(int(row["dwell_commits"]))
            except (KeyError, ValueError):
                pass
        return values

    recording_dwells = dwell_values(screen_life_recording)
    ordinary_dwells = dwell_values(screen_life_ordinary)
    recording_families = {row.get("family") for row in screen_life_recording
                          if row.get("family")}
    ordinary_families = {row.get("family") for row in screen_life_ordinary
                         if row.get("family")}

    option2 = option2_rows[-1] if option2_rows else {}
    overlay = overlay_rows[-1] if overlay_rows else {}
    overlay_contract = (
        option2.get("hold_face") == "0"
        and option2.get("face_clock") == "authored_daily_life"
        and option2.get("same_as_offline") == "1"
        and option2.get("blink_clock") == "independent"
        and option2.get("accessory_clock") == "independent"
        and option2.get("no_soft_advance") == "1"
        and option2.get("no_cross_track_advance") == "1"
        and option2.get("no_full_refresh") == "1"
        and option2.get("cadence_ms") == "480"
        and overlay.get("post_commit_dwell_ms") == "0"
        and overlay.get("no_predeadline_wave_suppression") == "1"
        and overlay.get("tracks") == "wave_authored_life_independent"
    )
    # `dropped` on overlay_trace is the bounded diagnostic ring's count of
    # samples that could not be retained until the host drained it.  It is not
    # a display-commit drop (those are proved by record-phase timing and the
    # rec-flash drops field), so a long recording can legitimately report a
    # non-zero value with the RAM-safe 12-entry trace ring.  UART writers also
    # share the port and may splice an otherwise valid trace line.  Require
    # multiple complete runtime samples, reject every explicit contract
    # violation, and leave diagnostic-ring loss visible in the report.
    trace_good = [row for row in trace_rows
                  if row.get("post_commit_dwell_ms") == "0"
                  and row.get("visible") == "1"
                  and row.get("control") == "0xCF"]
    trace_explicit = [row for row in trace_rows if
                      ("post_commit_dwell_ms" in row
                       and row["post_commit_dwell_ms"] != "0")
                      or ("visible" in row and row["visible"] != "1")
                      or ("control" in row and row["control"] != "0xCF")]
    trace_contract = len(trace_good) >= 2 and not trace_explicit

    accessory_good = [row for row in accessory_recording if
        row.get("due_source") == "charging_wall_clock"
        and row.get("wave_clock_advanced") == "0"
        and row.get("life_clock_advanced") == "0"
        and row.get("blink_clock_advanced") == "0"]
    accessory_explicit = [row for row in accessory_recording if
                          row.get("wave_clock_advanced") not in {None, "0"}
                          or row.get("life_clock_advanced") not in {None, "0"}
                          or row.get("blink_clock_advanced") not in {None, "0"}]
    # Treat incomplete rows as UART transport loss, not as a clock violation.
    # Two complete independent deadlines are sufficient for the primary touch
    # run; the longer scheduler probe supplies the higher-volume auxiliary
    # sample.  Any explicit non-zero advance remains an unconditional failure.
    accessory_safe = len(accessory_good) >= 2 and not accessory_explicit
    blink_safe = len(blink_rows) >= 2 and all(
        row.get("due_source") == "blink_scheduler"
        and row.get("wave_drives_blink") == "0"
        and row.get("blink_drives_wave") == "0"
        for row in blink_rows)

    boundary_indexes = [i for i, line in enumerate(lifecycle_lines)
                        if ("[screen] low_power_boundary=enter" in line
                            or "[screen] boundary_enqueue reason=low_power_idle"
                            in line)]
    boundary = boundary_indexes[-1] if boundary_indexes else None
    lp_tail = lifecycle_lines[boundary:] if boundary is not None else []
    lp_panel_rows = [fields(line) for line in lp_tail
                     if "[epaper] accepted_product_driver" in line]
    lp_c7_rows = [row for row in lp_panel_rows
                  if row.get("control") == "0xC7" and row.get("reason") == "7"]
    lp_c7 = lp_c7_rows[0] if lp_c7_rows else {}
    try:
        lp_partial_before = int(lp_c7.get("partial_before", "0"))
    except ValueError:
        lp_partial_before = 0
    freeze_indexes = [i for i, line in enumerate(lifecycle_lines)
                      if "[screen] low_power_idle freeze=committed" in line]
    freeze = freeze_indexes[-1] if freeze_indexes else None
    after_freeze = lifecycle_lines[freeze + 1:] if freeze is not None else []
    watchdog_after_freeze = [fields(line) for line in after_freeze
                             if "[watchdog]" in line]
    panel_after_freeze = [line for line in after_freeze
                          if "[epaper] accepted_product_driver" in line]
    boundary_line = lifecycle_lines[boundary] if boundary is not None else ""
    freeze_line = lifecycle_lines[freeze] if freeze is not None else ""

    gc_function = _extract_function(
        driver, "static bool ssd1681_lifecycle_mode1_gc_full_activation_ex(")
    product_function = _extract_function(
        driver, "static comp_epaper_panel_result_t ssd1681_accepted_cached_mode2_product_refresh(")
    lp_calls_inverse_old_cold_gc = (
        product_function.count(
            "ssd1681_lifecycle_mode1_gc_full_activation_ex(") >= 2
        and "s_frame, sizeof(s_frame), &report, true, false, true, false);"
        in product_function
        and "lp_enter_inverse_old_c7 control=0xC7" in product_function)
    cold_c7_contract = (
        "ssd1681_reset();" in gc_function
        and "const uint8_t full_update = 0xC7u;" in gc_function
        and "0x26u, s_blink_closed_frame, &window" in gc_function
        and "ssd1681_write_plane_region(0x24u, s_frame, &window)" in gc_function
        and "if (force_inverse_old_plane)" in gc_function
        and "s_blink_closed_frame[index] = (uint8_t)~s_frame[index];"
        in gc_function
        and "lp_skip_mode2_rearm control_0x99=0" in gc_function
        and "if (rebaseline_complete && force_inverse_old_plane)"
        in gc_function)
    lp_inverse_receipts = [fields(line) for line in lp_tail
                           if "[epaper] lp_enter_inverse_old_c7" in line]
    lp_rearm_skip_receipts = [fields(line) for line in lp_tail
                              if "[epaper] lp_skip_mode2_rearm" in line]
    lp_hidden_rearm_receipts = [line for line in lp_tail
                                if "[epaper] accepted_mode2_rearm" in line]
    lp_compose_clean = any(
        "[epaper] lp_enter_skip_functional_compose" in line
        and "recording=0" in line and "charger=0" in line
        and "blink=0" in line and "pure_sleepy=1" in line
        for line in lp_tail)
    pre_boundary_lines = (lifecycle_lines[:boundary]
                          if boundary is not None else lifecycle_lines)
    pre_lp_changed_cf = [fields(line) for line in pre_boundary_lines
                         if "[epaper] accepted_product_driver" in line
                         and fields(line).get("control") == "0xCF"
                         and fields(line).get("changed") == "1"]
    pre_lp_maintenance = [fields(line) for line in pre_boundary_lines
                          if "[epaper] accepted_product_driver" in line
                          and fields(line).get("control") == "0xC7"
                          and fields(line).get("reason") == "4"]

    ota_checks = ota_layout.get("checks", {})
    ota_safe = (ota_layout.get("status") == "MACHINE_READY"
                and bool(ota_checks)
                and all(value is True for value in ota_checks.values()))
    actual_bin_sha = sha256(bin_raw)
    expected_bin_sha = expected_bin_sha256.upper()

    faults = sorted({token for token in FAULT_TOKENS
                     if any(token in line for line in health_source_lines)})
    unhealthy_watchdog = [row for row in watchdog_rows
                          if row.get("healthy") != "1"
                          or row.get("stalled_mask") != "0x00"]
    forbidden_recording_controls = [fields(line).get("control") for line in segment
                                    if "[epaper] accepted_product_driver" in line
                                    and fields(line).get("control") in
                                    {"0xC7", "0xF7", "0xFF"}]

    checks = {
        "latest_real_recording_has_clean_stop": start is not None and stop is not None,
        "recording_is_at_least_minimum_and_drop_free": (
            stored_duration >= min_recording_duration_ms
            and stored_bytes > 0 and stored.get("drops") == "0"),
        "wave_uses_first_available_slots": (
            len(wave_rows) >= min_wave and all_wave_clock_safe
            and overlay_contract and trace_contract
            and wave_p95 is not None and wave_p95 <= wave_p95_limit_ms),
        "face_uses_authored_clock_not_wave_clock": (
            len(face_rows) >= min_face and len(face_rows) < len(wave_rows)
            and all_face_clock_safe and all_enqueue_safe
            and len(life_enqueue_rows) >= len(face_rows)),
        "recording_and_ordinary_share_authored_life_contract": (
            len(screen_life_recording) >= min_face
            and len(screen_life_ordinary) >= 6
            and recording_dwells and ordinary_dwells
            and all(1 <= value <= 4 for value in recording_dwells + ordinary_dwells)
            and bool(recording_families & ordinary_families)
            and option2.get("same_as_offline") == "1"
            and option2.get("cadence_ms") == "480"),
        "accessory_clock_is_independent_during_recording": accessory_safe,
        "blink_clock_is_independent": blink_safe,
        "recording_has_no_full_refresh": not forbidden_recording_controls,
        "lp_runtime_boundary_is_inverse_old_c7_after_maintained_history": (
            lp_compose_clean
            and len(lp_c7_rows) == 1
            and len(lp_inverse_receipts) == 1
            and lp_inverse_receipts[0].get("control") == "0xC7"
            and lp_inverse_receipts[0].get("activation_count") == "1"
            and lp_inverse_receipts[0].get("inverse_old") == "1"
            and len(lp_rearm_skip_receipts) == 1
            and lp_rearm_skip_receipts[0].get("initial_display_stage") == "0"
            and not lp_hidden_rearm_receipts
            and (lp_partial_before >= min_partial_before_lp
                 or (len(pre_lp_changed_cf) >= min_partial_before_lp
                     and len(pre_lp_maintenance) >= 2))),
        "lp_source_is_one_inverse_old_cold_c7": (
            bool(gc_function) and lp_calls_inverse_old_cold_gc
            and cold_c7_contract),
        "lp_freeze_stops_all_screen_tracks": (
            "quiet=1 life=0 blink=0 wave=0 accessory=0" in freeze_line
            and not panel_after_freeze
            and len(watchdog_after_freeze) >= 3
            and all(row.get("healthy") == "1"
                    and row.get("stalled_mask") == "0x00"
                    for row in watchdog_after_freeze)),
        "no_fault_or_watchdog_stall": not faults and not unhealthy_watchdog,
        "ota_layout_is_safe": ota_safe,
        "binary_identity_matches": actual_bin_sha == expected_bin_sha,
    }
    failed = [name for name, passed in checks.items() if not passed]
    scheduler_probe = (analyze_scheduler_probe(
        scheduler_log_path,
        min_recording_duration_ms=min_recording_duration_ms,
        min_wave=min_wave,
        min_face=min_face,
        wave_p95_limit_ms=wave_p95_limit_ms)
        if scheduler_log_path is not None else None)
    return {
        "schema": "companion.comp_req_775.screen_final.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "thresholds": {
            "min_recording_duration_ms": min_recording_duration_ms,
            "min_wave": min_wave,
            "min_face": min_face,
            "min_partial_before_lp": min_partial_before_lp,
            "wave_p95_limit_ms": wave_p95_limit_ms,
        },
        "recording": {
            "duration_ms": stored_duration,
            "bytes": stored_bytes,
            "drops": stored.get("drops"),
            "wave_count": len(wave_rows),
            "pure_wave_count": len(pure_wave_rows),
            "authored_life_carrier_count": len(carried_wave_rows),
            "face_count": len(face_rows),
            "authored_life_enqueue_count": len(life_enqueue_rows),
            "wave_gaps_ms": wave_gaps,
            "wave_gap_p95_ms": wave_p95,
            "wave_gap_max_ms": wave_max,
            "wave_parse_fraction": wave_parse_fraction,
            "wave_contract_parse_fraction": wave_contract_parse_fraction,
            "face_parse_fraction": face_parse_fraction,
            "authored_life_enqueue_parse_fraction": enqueue_parse_fraction,
            "wave_explicit_violation_count": len(wave_explicit_violations),
            "face_explicit_violation_count": len(face_explicit_violations),
            "overlay_trace_rows": len(trace_rows),
            "overlay_trace_complete_rows": len(trace_good),
            "overlay_trace_uart_spliced_rows": len(trace_rows) - len(trace_good),
            "overlay_trace_explicit_violation_count": len(trace_explicit),
            "overlay_trace_buffer_dropped_max": max(
                (int(row["dropped"]) for row in trace_rows
                 if row.get("dropped", "").isdigit()), default=0),
            "recording_dwells": recording_dwells,
            "recording_families": sorted(recording_families),
        },
        "independent_tracks": {
            "recording_accessory_rows": len(accessory_recording),
            "recording_accessory_complete_rows": len(accessory_good),
            "recording_accessory_uart_spliced_rows": (
                len(accessory_recording) - len(accessory_good)),
            "recording_accessory_explicit_violation_count": len(accessory_explicit),
            "blink_phase_rows": len(blink_rows),
            "ordinary_life_rows": len(screen_life_ordinary),
            "ordinary_dwells": ordinary_dwells,
            "ordinary_families": sorted(ordinary_families),
        },
        "low_power": {
            "partial_before": lp_partial_before,
            "changed_cf_before_lp": len(pre_lp_changed_cf),
            "maintenance_c7_before_lp": len(pre_lp_maintenance),
            "runtime_c7_request_rows": len(lp_c7_rows),
            "source_visible_activation_count": 1 if lp_calls_inverse_old_cold_gc else None,
            "inverse_old_activations": len(lp_inverse_receipts),
            "sleepy_paint_activations": 1 if cold_c7_contract else None,
            "watchdog_rows_after_freeze": len(watchdog_after_freeze),
            "panel_rows_after_freeze": len(panel_after_freeze),
        },
        "stability": {
            "watchdog_rows": len(watchdog_rows),
            "unhealthy_watchdog_rows": len(unhealthy_watchdog),
            "fault_tokens": faults,
            "forbidden_recording_controls": forbidden_recording_controls,
        },
        "identity": {
            "log": str(log_path.resolve()),
            "log_sha256": sha256(log_raw),
            "lifecycle_log": str((lifecycle_log_path or log_path).resolve()),
            "lifecycle_log_sha256": sha256(lifecycle_raw),
            "driver": str(driver_path.resolve()),
            "driver_sha256": sha256(driver_raw),
            "binary": str(bin_path.resolve()),
            "binary_sha256": actual_bin_sha,
            "expected_binary_sha256": expected_bin_sha,
            "ota_layout": str(ota_layout_path.resolve()),
        },
        "scheduler_auxiliary": scheduler_probe,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--bin", dest="bin_path", type=Path, required=True)
    parser.add_argument("--expected-bin-sha256", required=True)
    parser.add_argument("--ota-layout", type=Path, required=True)
    parser.add_argument("--lifecycle-log", type=Path,
                        help="Optional same-firmware long-history/LP capture")
    parser.add_argument("--scheduler-log", type=Path,
                        help="Optional long shared-scheduler capture; does not replace touch")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-recording-duration-ms", type=int, default=10_000)
    parser.add_argument("--min-wave", type=int, default=12)
    parser.add_argument("--min-face", type=int, default=2)
    parser.add_argument("--min-partial-before-lp", type=int, default=140)
    parser.add_argument("--wave-p95-limit-ms", type=int, default=700)
    args = parser.parse_args()
    result = analyze(
        args.log, args.driver, args.bin_path, args.expected_bin_sha256,
        args.ota_layout,
        lifecycle_log_path=args.lifecycle_log,
        scheduler_log_path=args.scheduler_log,
        min_recording_duration_ms=args.min_recording_duration_ms,
        min_wave=args.min_wave,
        min_face=args.min_face,
        min_partial_before_lp=args.min_partial_before_lp,
        wave_p95_limit_ms=args.wave_p95_limit_ms,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
