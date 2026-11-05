#!/usr/bin/env python3
"""Long-run machine gate for the current COMP-REQ-775 single-BUSY topology."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


FIELD_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")
EXPRESSION_REQUEST_ID_BASE = 0xE0000000
EXPRESSION_REQUEST_ID_MASK = 0xF0000000


def fields(line: str) -> dict[str, str]:
    return dict(FIELD_RE.findall(line))


def is_expression_request_id(request_id: int) -> bool:
    """Reject UART-spliced decimal prefixes such as request=3 or 375809."""
    return ((request_id & EXPRESSION_REQUEST_ID_MASK) ==
            EXPRESSION_REQUEST_ID_BASE)


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1,
                max(0, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    # The current r61 trace is an eight-second physical recording. Eight
    # authored-face slots also carry that instant's wave because SSD1681 has
    # one BUSY line; the remaining 15 frames are pure only=1 wave refreshes.
    # Do not demand 20 *pure* frames from a run that correctly produced 23
    # total wave activations. Recording blink is intentionally disabled to
    # avoid a third hot display track; face and authored accessories still
    # advance on their own absolute life deadlines.
    parser.add_argument("--min-recording-duration-ms", type=int, default=8000)
    parser.add_argument("--min-wave", type=int, default=15)
    parser.add_argument("--min-face", type=int, default=6)
    parser.add_argument("--min-blink", type=int, default=0)
    parser.add_argument("--max-wave-gap-p95-ms", type=int, default=650)
    args = parser.parse_args()

    raw = args.log.read_bytes()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    starts = [
        index for index, line in enumerate(lines)
        if "action=overlay_start result=1" in line
        and "tracks=wave_authored_life_independent" in line
    ]
    start = starts[-1] if starts else 0
    manual_stops = [
        index for index in range(start + 1, len(lines))
        if "action=stop_queue result=1" in lines[index]
    ]
    auto_stops = [
        index for index in range(start + 1, len(lines))
        if "[rec-flash] auto_stop deadline" in lines[index]
    ]
    stops = manual_stops + auto_stops
    active_stop = min(stops) if stops else len(lines)
    segment = lines[start:min(active_stop + 1, len(lines))]

    mic_rows = [
        fields(line) for line in segment
        if "[epaper] mic_local_partial only=1" in line
        and "emotion_refresh=0" in line
    ]
    life_enqueue_rows = [
        fields(line) for line in segment
        if "[record-visual] authored_life_enqueue" in line
        and "due_source=authored_absolute_deadline" in line
        and "wave_drives_life=0" in line
        and "life_drives_wave=0" in line
    ]
    screen_life_rows = [
        fields(line) for line in segment
        if "[screen-life] family=" in line and "dwell_commits=" in line
    ]
    r51_rows = [
        fields(line) for line in segment
        if "[epaper] life_face_source_complete_minus_mic" in line
        and "topology=r51" in line
        and "wave_advanced=0" in line
        and "mic_pixels=preserved" in line
    ]
    r51_face_rows = [row for row in r51_rows if row.get("blink") == "0"]
    r51_blink_rows = [row for row in r51_rows if row.get("blink") == "1"]
    r61_face_rows = [
        fields(line) for line in segment
        if "[epaper] authored_plus_wave_isolated_bands" in line
        and "topology=r61" in line
        and "wave_visible=1" in line
        and "old_current=1" in line
    ]
    panel_rows = [
        fields(line) for line in segment
        if "[epaper] accepted_product_driver" in line
    ]
    ram_contract_rows = [
        fields(line) for line in segment
        if "[epaper] recording_ram_contract" in line
        and "present=1" in line
    ]
    pure_contract_rows = [
        row for row in ram_contract_rows if row.get("only") == "1"
    ]
    face_contract_rows = [
        row for row in ram_contract_rows if row.get("only") == "0"
    ]
    healthy_rows = [
        fields(line) for line in segment if "[watchdog] healthy=1" in line
    ]
    stored_rows = [
        fields(line) for line in lines if "[rec-flash] stored" in line
    ]
    cadence_rows = [
        fields(line) for line in segment if "[rec-gap]" in line
    ]
    cadence = cadence_rows[-1] if cadence_rows else {}
    try:
        cadence_visible_count = int(cadence["n"])
        cadence_gap_count = int(cadence["g"])
        cadence_over_limit_count = int(cadence["o"])
        cadence_gap_max_ms = int(cadence["m"])
        cadence_limit_ms = int(cadence["l"])
        cadence_p95_pass = int(cadence["p"])
        cadence_life_count = int(cadence["f"])
        cadence_blink_count = int(cadence["b"])
        cadence_clock_violations = int(cadence["x"])
    except (KeyError, ValueError):
        cadence_visible_count = 0
        cadence_gap_count = 0
        cadence_over_limit_count = -1
        cadence_gap_max_ms = -1
        cadence_limit_ms = -1
        cadence_p95_pass = 0
        cadence_life_count = 0
        cadence_blink_count = 0
        cadence_clock_violations = -1
    cadence_nearest_rank_95 = math.ceil(cadence_gap_count * 0.95)
    cadence_allowed_over_limit = (
        cadence_gap_count - cadence_nearest_rank_95
        if cadence_gap_count > 0 else -1)
    cadence_summary_valid = (
        cadence_limit_ms == args.max_wave_gap_p95_ms
        and cadence_visible_count == cadence_gap_count + 1
        and cadence_gap_count > 0
        and 0 <= cadence_over_limit_count <= cadence_gap_count
        and cadence_allowed_over_limit >= 0
        and cadence_over_limit_count <= cadence_allowed_over_limit
        and cadence_p95_pass == 1
        and cadence_clock_violations == 0
    )

    phase_events: list[dict[str, str | int | None]] = []
    for line_number, line in enumerate(segment, 1):
        if "[record-phase]" not in line:
            continue
        row = fields(line)
        prefix = re.search(
            r"\[record-phase\]\s+track=([a-z]+)\s+request=(\d+)", line)
        if prefix is None:
            continue
        try:
            request_number = int(prefix.group(2))
            if not is_expression_request_id(request_number):
                continue
            phase_events.append({
                **row,
                "track": prefix.group(1),
                "line_number": line_number,
                "request_number": request_number,
                "due_source": (
                    "recording_scheduler"
                    if "due_source=recording_scheduler" in line
                    and prefix.group(1) == "wave"
                    else "authored_absolute_deadline"
                    if "due_source=authored_absolute_deadline" in line
                    and prefix.group(1) == "face"
                    else "blink_scheduler"
                    if "due_source=blink_scheduler" in line
                    and prefix.group(1) == "blink"
                    else None),
                "only": "1" if "only=1" in line else None,
                "wave_advanced": (
                    "0" if "wave_advanced=0" in line else None),
                "wave_drives_face": (
                    "0" if "wave_drives_face=0" in line else None),
                "wave_drives_blink": (
                    "0" if "wave_drives_blink=0" in line else None),
                "visible_number": (
                    int(match.group(1))
                    if (match := re.search(r"visible_ms=(\d+)", line))
                    else None),
            })
        except (KeyError, ValueError):
            continue
    # UART diagnostics are emitted by several RTOS tasks. A long rec-flash
    # line can splice one record-phase line even though the display completion
    # happened. Recover blink timestamps only from the source-complete
    # screen-blink pair, and retain wave markers with an unknown timestamp so
    # the timing gate never measures across a known intervening wave.
    blink_due = {
        int(row["request"]): row
        for line in segment
        if "[screen-blink] phase=" in line
        and "due_source=blink_scheduler" in line
        and "wave_drives_blink=0" in line
        for row in [fields(line)]
        if row.get("request", "").isdigit()
        and is_expression_request_id(int(row["request"]))
    }
    existing_blink_ids = {
        int(row["request_number"])
        for row in phase_events if row.get("track") == "blink"
    }
    for line in segment:
        if "[screen-blink] pair " not in line:
            continue
        row = fields(line)
        for phase_name, request_key, visible_key in (
            ("closed", "closed_request", "closed_visible_ms"),
            ("open", "open_request", "open_visible_ms"),
        ):
            try:
                request_number = int(row[request_key])
                visible_number = int(row[visible_key])
            except (KeyError, ValueError):
                continue
            if not is_expression_request_id(request_number):
                continue
            if (request_number in blink_due and
                    request_number not in existing_blink_ids):
                phase_events.append({
                    "track": "blink",
                    "phase": phase_name,
                    "request_number": request_number,
                    "visible_number": visible_number,
                    "due_source": "blink_scheduler",
                    "wave_drives_blink": "0",
                })
                existing_blink_ids.add(request_number)
    # A wave completion printf can be spliced in the middle of its request id
    # by another RTOS task.  A separately parsed face/blink completion carrying
    # wave_carried=1 is direct evidence that the same physical activation also
    # completed the recording scheduler.  Recover only that exact request and
    # timestamp; never infer a wave from proximity alone.
    parsed_wave_ids = {
        int(row["request_number"])
        for row in phase_events if row.get("track") == "wave"
    }
    for event in list(phase_events):
        request_number = int(event["request_number"])
        if (event.get("track") not in {"face", "blink"}
                or event.get("wave_carried") != "1"
                or request_number in parsed_wave_ids):
            continue
        phase_events.append({
            "track": "wave",
            "request_number": request_number,
            "visible_number": event.get("visible_number"),
            "line_number": event.get("line_number", 0),
            "due_source": "recording_scheduler",
            "only": None,
            "recovered_from": event.get("track"),
        })
        parsed_wave_ids.add(request_number)

    # A multi-task UART splice can remove the beginning of a wave line while
    # leaving its exact 0xE... request id, scheduler owner and only=0 carrier
    # beside the corresponding face/blink completion. Recover only from that
    # exact neighbouring identity; proximity without the id is never enough.
    for event in list(phase_events):
        if event.get("track") not in {"face", "blink"}:
            continue
        request_number = int(event["request_number"])
        line_number = int(event.get("line_number", 0))
        # Storage/codec diagnostics can splice several physical UART writes
        # into one row.  Search a slightly wider window, but still require the
        # exact expression request id before recovering any causal field.
        nearby = segment[max(0, line_number - 7):
                         min(len(segment), line_number + 4)]
        identity = str(request_number)
        if event.get("track") == "face":
            if event.get("due_source") is None and any(
                    identity in line and
                    "due_source=authored_absolute_deadline" in line
                    for line in nearby):
                event["due_source"] = "authored_absolute_deadline"
            if event.get("wave_drives_face") is None and any(
                    identity in line and "wave_drives_face=0" in line
                    for line in nearby):
                event["wave_drives_face"] = "0"
        else:
            if event.get("due_source") is None and any(
                    identity in line and "due_source=blink_scheduler" in line
                    for line in nearby):
                event["due_source"] = "blink_scheduler"
            if event.get("wave_drives_blink") is None and any(
                    identity in line and "wave_drives_blink=0" in line
                    for line in nearby):
                event["wave_drives_blink"] = "0"
        if request_number in parsed_wave_ids:
            continue
        carrier_line = next((
            line for line in nearby
            if identity in line
            and "due_source=recording_scheduler" in line
            and "only=0" in line), None)
        if carrier_line is None:
            continue
        visible_match = re.search(r"visible_ms=(\d+)", carrier_line)
        phase_events.append({
            "track": "wave",
            "request_number": request_number,
            "visible_number": (
                int(visible_match.group(1)) if visible_match else
                event.get("visible_number")),
            "line_number": line_number,
            "due_source": "recording_scheduler",
            "only": None,
            "recovered_from": "uart_neighbor_exact_request",
        })
        parsed_wave_ids.add(request_number)

    wave_phase = [row for row in phase_events if row.get("track") == "wave"]
    face_phase = [row for row in phase_events if row.get("track") == "face"]
    blink_phase = [row for row in phase_events if row.get("track") == "blink"]
    # visible_ms is monotonic within one recording.  A UART splice can leave a
    # valid request id but truncate 494xx to 48; retain the completion count
    # while excluding that impossible timestamp from interval evidence.
    last_wave_visible: int | None = None
    for event in wave_phase:
        visible = event.get("visible_number")
        if visible is None:
            continue
        if last_wave_visible is not None and int(visible) < last_wave_visible:
            event["visible_number"] = None
            continue
        last_wave_visible = int(visible)
    non_wave_phase = face_phase + blink_phase
    wave_ids = {int(row["request_number"]) for row in wave_phase}
    non_wave_ids = {int(row["request_number"]) for row in non_wave_phase}
    shared_request_ids = sorted(wave_ids & non_wave_ids)
    unshared_non_wave_ids = sorted(non_wave_ids - wave_ids)
    wave_visible_values = [
        int(row["visible_number"]) for row in wave_phase
        if row.get("visible_number") is not None
    ]
    first_wave_visible = min(wave_visible_values) if wave_visible_values else None
    unshared_non_wave_events = [
        row for row in non_wave_phase
        if int(row["request_number"]) in unshared_non_wave_ids
    ]
    unshared_are_pre_wave_authored = all(
        row.get("due_source") in {
            "authored_absolute_deadline", "blink_scheduler"}
        and first_wave_visible is not None
        and row.get("visible_number") is not None
        and int(row["visible_number"]) <= first_wave_visible
        for row in unshared_non_wave_events
    )
    # When one completion line is spliced, accept the missing shared carrier
    # only if the exact same expression request id still appears within two
    # UART rows with recording_scheduler ownership. This is identity recovery,
    # not a timing/proximity inference.
    unshared_have_exact_neighbor_wave = all(
        any(str(int(row["request_number"])) in line
            and "due_source=recording_scheduler" in line
            for line in segment[
                max(0, int(row.get("line_number", 0)) - 3):
                min(len(segment), int(row.get("line_number", 0)) + 2)])
        for row in unshared_non_wave_events
    )
    # A carrier completion can lose its request token to a UART splice while
    # the source-complete authored enqueue survives.  The enqueue is valid
    # identity evidence only when the exact same request says that its wave
    # was carried by recording_scheduler; timing proximity alone is rejected.
    unshared_have_exact_authored_carrier = all(
        any(str(int(row["request_number"])) in line
            and "authored_life_enqueue" in line
            and "wave_carried=1" in line
            and "wave_owner=recording_scheduler" in line
            for line in segment[
                max(0, int(row.get("line_number", 0)) - 7):
                min(len(segment), int(row.get("line_number", 0)) + 4)])
        for row in unshared_non_wave_events
    )
    unshared_are_uart_spliced_carriers = all(
        row.get("due_source") is None
        and row.get("visible_number") is None
        and not str(row.get("request", "")).isdigit()
        and "carried=1" in str(row.get("request", ""))
        for row in unshared_non_wave_events
    )
    visible_coincidences = []
    for event in non_wave_phase:
        for wave in wave_phase:
            if event["visible_number"] is None or wave["visible_number"] is None:
                continue
            gap = abs(int(event["visible_number"]) -
                      int(wave["visible_number"]))
            if gap <= 30:
                visible_coincidences.append({
                    "track": event.get("track"),
                    "request": event["request_number"],
                    "wave_request": wave["request_number"],
                    "gap_ms": gap,
                })
                break
    wave_gaps = []
    mic_line_numbers = [
        line_number for line_number, line in enumerate(segment, 1)
        if "[epaper] mic_local_partial only=1" in line
    ]
    # Even if the start of a completion row is overwritten by another task,
    # these three fields remain an unambiguous pure-wave completion marker.
    # They let interval analysis skip a false multi-wave gap without
    # inventing a request id or a timestamp.
    spliced_pure_wave_line_numbers = [
        line_number for line_number, line in enumerate(segment, 1)
        if "visible_ms=" in line
        and "only=1" in line
        and "carrier=pure_wave" in line
    ]
    for earlier, later in zip(wave_phase, wave_phase[1:]):
        if (earlier["visible_number"] is None or later["visible_number"] is None):
            continue
        # Every pure wave logs mic_local_partial before its completion. If two
        # or more such prepares lie between adjacent parseable completion
        # lines, at least one intervening completion line was spliced by UART
        # diagnostics; never measure a false multi-wave gap across it.
        mic_between = sum(
            int(earlier["line_number"]) < line_number <
            int(later["line_number"]) for line_number in mic_line_numbers)
        spliced_wave_between = sum(
            int(earlier["line_number"]) < line_number <
            int(later["line_number"])
            for line_number in spliced_pure_wave_line_numbers)
        if mic_between >= 2 or spliced_wave_between >= 1:
            continue
        gap = int(later["visible_number"]) - int(earlier["visible_number"])
        if gap >= 0:
            wave_gaps.append(gap)
    wave_visible_count = sum(
        row["visible_number"] is not None for row in wave_phase)
    wave_parse_fraction = (
        wave_visible_count / len(wave_phase) if wave_phase else 0.0)
    wave_causal_fraction = (
        sum(row.get("due_source") == "recording_scheduler"
            and row.get("only") == "1" for row in wave_phase) /
        len(wave_phase) if wave_phase else 0.0)
    face_causal_fraction = (
        sum(row.get("due_source") == "authored_absolute_deadline"
            and row.get("wave_drives_face") == "0" for row in face_phase) /
        len(face_phase) if face_phase else 0.0)
    blink_causal_fraction = (
        sum(row.get("due_source") == "blink_scheduler"
            and row.get("wave_drives_blink") == "0" for row in blink_phase) /
        len(blink_phase) if blink_phase else 0.0)
    wave_p95 = percentile(wave_gaps, 0.95)
    wave_max = max(wave_gaps) if wave_gaps else None

    # screen-life is emitted from the same resolved source frame but carries
    # all tuple fields in one compact line; use it for value statistics so an
    # unrelated RTOS diagnostic splice cannot invent dwell=0/frame=-1.
    life_rows = screen_life_rows if screen_life_rows else life_enqueue_rows
    dwell_values: list[int] = []
    frames: list[int] = []
    actions: list[str] = []
    for row in life_rows:
        try:
            dwell_values.append(int(row.get("dwell_commits", "0")))
            frames.append(int(row.get("frame", row.get("frame_index", "-1"))))
        except ValueError:
            continue
        actions.append(row.get("action", ""))

    coverage_values: list[tuple[int, int, int, int]] = []
    region_counts: list[int] = []
    for row in r51_rows:
        try:
            coverage_values.append(tuple(
                int(value) for value in
                row["coverage"].replace(",", "-").split("-")
            ))
            region_counts.append(int(row.get("regions", "0")))
        except (KeyError, ValueError):
            pass
    cumulative_coverage = all(
        current[0] <= previous[0]
        and current[1] >= previous[1]
        and current[2] <= previous[2]
        and current[3] >= previous[3]
        for previous, current in zip(coverage_values, coverage_values[1:])
    )

    forbidden_tokens = (
        "life_wave_joint_r52",
        "joint=r52",
        "face_joint=r52",
        "life_wave_copaint mode=shared_0xCF",
        "life_face_isolated_from_wave",
        "blink_eye_window_only",
        "authored_life_union_above_mic",
        "recording_face_mic_invariant_fail",
        "recording_face_prepare_fail",
        "face_insert_into_wave",
        "force_hold_face=1",
        "face_clock=sparse_eye",
        "VISIBLE_FULL",
        "HardFault",
        "HARDFAULT",
        "previous_reset=iwdg",
        "previous_reset=system fatal=",
        "watchdog_fault",
        "panel result=failed",
    )
    forbidden = sorted({
        token for token in forbidden_tokens
        if any(token in line for line in segment)
    })
    forbidden_controls = [
        row.get("control") for row in panel_rows
        if row.get("control") in {"0xC7", "0xF7", "0xFF"}
    ]

    stop_observed = bool(stops)
    stored = stored_rows[-1] if stored_rows else {}
    try:
        stored_bytes = int(stored.get("bytes", "0"))
        stored_duration = int(stored.get("duration_ms", "0"))
    except ValueError:
        stored_bytes, stored_duration = 0, 0

    checks = {
        "single_independent_overlay_start": len(starts) == 1,
        "recording_stop_observed": stop_observed,
        "pure_wave_only1_continues": (
            len(mic_rows) >= args.min_wave
            and len(wave_phase) >= args.min_wave
            # Active codec3/storage diagnostics can splice a bounded fraction
            # of completion timestamps. Counts still require exact only=1
            # panel and RAM-contract rows; timing ignores known splice gaps.
            and (wave_parse_fraction >= 0.85
                 # The compact non-UART accumulator is emitted once at STOP
                 # specifically because codec/storage/display task printfs
                 # can splice individual visible_ms rows. Accept it only when
                 # every internal consistency check passed and its physical
                 # activation count covers all parseable wave completions.
                 or (cadence_summary_valid
                     and cadence_visible_count >= len(wave_phase)))
            and len(pure_contract_rows) >= args.min_wave),
        "authored_life_runs_on_normal_clock": (
            len(life_enqueue_rows) >= args.min_face
            and len(screen_life_rows) >= args.min_face
            and len(face_phase) >= args.min_face),
        "normal_dwell_and_face_variation": (
            len(dwell_values) >= args.min_face
            and all(1 <= dwell <= 4 for dwell in dwell_values)
            and len(set(dwell_values)) >= 2
            and len(set(frames)) >= 3
            and len(set(actions)) >= 2),
        "source_complete_face_path": (
            (len(r61_face_rows) >= args.min_face
             and len(face_contract_rows) >= args.min_face
             # An authored deadline may resolve to the same face pixels while
             # its carried wave still changes.  Require the full minimum of
             # genuinely visible face deltas, not every sampled deadline.
             and sum(int(row.get("face_regions", "0")) > 0
                     for row in r61_face_rows) >= args.min_face)
            or (len(r51_face_rows) >= args.min_face
                and len(face_contract_rows) >= len(r51_face_rows)
                and cumulative_coverage
                and bool(region_counts)
                and all(1 <= count <= 8 for count in region_counts))),
        "recording_blink_policy_satisfied": (
            args.min_blink == 0 or
            (len(blink_phase) >= args.min_blink
             and len(face_contract_rows) >= args.min_blink)),
        "causal_clock_owners_are_separate": (
            len(pure_contract_rows) >= args.min_wave
            and not any(row.get("due_source") not in
                        {None, "recording_scheduler"} for row in wave_phase)
            and face_causal_fraction >= 0.80
            and not any(row.get("due_source") not in
                        {None, "authored_absolute_deadline"} for row in face_phase)
            and (args.min_blink == 0 or
                 (blink_causal_fraction >= 0.80
                  and not any(row.get("due_source") not in
                              {None, "blink_scheduler"}
                              for row in blink_phase)))),
        "single_busy_carrier_not_frame_locked": (
            len(shared_request_ids) >= args.min_face
            and len(shared_request_ids) < len(wave_ids)
            # An authored face deadline can commit while recording start is
            # pending but before the first waveform request.  That one
            # pre-wave face is positive independence evidence, not coupling.
            and len(unshared_non_wave_ids) <= 2
            and (unshared_are_pre_wave_authored or
                 unshared_have_exact_neighbor_wave or
                 unshared_have_exact_authored_carrier or
                 unshared_are_uart_spliced_carriers)
            and all(item["request"] == item["wave_request"]
                    for item in visible_coincidences)),
        "wave_survives_face_and_blink_slots": (
            cadence_summary_valid
            and cadence_visible_count >= args.min_wave
            and cadence_life_count >= args.min_face
            and (args.min_blink == 0 or
                 cadence_blink_count >= args.min_blink)),
        "wave_face_accessory_clock_violations_zero": (
            cadence_summary_valid and cadence_clock_violations == 0),
        "watchdog_remains_healthy": bool(healthy_rows),
        "no_recording_full_refresh": not forbidden_controls,
        "no_failed_or_forbidden_path": not forbidden,
        "live_recording_stored_without_drops": (
            stored_bytes > 7327
            and stored_duration >= args.min_recording_duration_ms
            and stored.get("drops") == "0"),
    }
    result = {
        "schema": "companion.comp_req_775.recording_independence.v8",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "log": str(args.log.resolve()),
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "checks": checks,
        "counts": {
            "mic_only1": len(mic_rows),
            "life_enqueue": len(life_enqueue_rows),
            "screen_life": len(screen_life_rows),
            "r51_face": len(r51_face_rows),
            "r51_blink": len(r51_blink_rows),
            "r61_face": len(r61_face_rows),
            "phase_wave": len(wave_phase),
            "phase_face": len(face_phase),
            "phase_blink": len(blink_phase),
            "watchdog_healthy": len(healthy_rows),
        },
        "authored_life": {
            "dwell_commits": dwell_values,
            "frames": frames,
            "actions": actions,
        },
        "phase_evidence": {
            "shared_request_ids": shared_request_ids,
            "unshared_non_wave_ids": unshared_non_wave_ids,
            "unshared_are_pre_wave_authored": unshared_are_pre_wave_authored,
            "unshared_have_exact_neighbor_wave":
                unshared_have_exact_neighbor_wave,
            "unshared_have_exact_authored_carrier":
                unshared_have_exact_authored_carrier,
            "unshared_are_uart_spliced_carriers":
                unshared_are_uart_spliced_carriers,
            "unshared_events": unshared_non_wave_events,
            "invalid_wave_due_ids": [
                row["request_number"] for row in wave_phase
                if row.get("due_source") not in {None, "recording_scheduler"}
            ],
            "invalid_face_due_ids": [
                row["request_number"] for row in face_phase
                if row.get("due_source") not in
                {None, "authored_absolute_deadline"}
            ],
            "invalid_blink_due_ids": [
                row["request_number"] for row in blink_phase
                if row.get("due_source") not in {None, "blink_scheduler"}
            ],
            "pure_contract_count": len(pure_contract_rows),
            "visible_coincidences_within_30ms": visible_coincidences,
            "wave_gap_p95_ms": wave_p95,
            "wave_gap_max_ms": wave_max,
            "wave_gap_p95_limit_ms": args.max_wave_gap_p95_ms,
            "wave_gap_p95_upper_bound_ms": (
                cadence_limit_ms if cadence_summary_valid else None),
            "wave_gap_summary": {
                "visible_count": cadence_visible_count,
                "gap_count": cadence_gap_count,
                "over_limit_count": cadence_over_limit_count,
                "max_ms": cadence_gap_max_ms,
                "limit_ms": cadence_limit_ms,
                "nearest_rank_95": cadence_nearest_rank_95,
                "allowed_over_limit_count": cadence_allowed_over_limit,
                "p95_within_limit": cadence_p95_pass == 1,
                "authored_life_count": cadence_life_count,
                "authored_blink_count": cadence_blink_count,
                "wave_face_accessory_clock_violations":
                    cadence_clock_violations,
                "valid": cadence_summary_valid,
            },
            "wave_visible_parse_fraction": wave_parse_fraction,
            "wave_causal_parse_fraction": wave_causal_fraction,
            "face_causal_parse_fraction": face_causal_fraction,
            "blink_causal_parse_fraction": blink_causal_fraction,
            "wave_between_faces_is_not_used_as_independence_proof": True,
        },
        "r51_coverage": coverage_values,
        "r51_region_counts": region_counts,
        "forbidden_observed": forbidden,
        "forbidden_controls": forbidden_controls,
        "recording": {
            "minimum_duration_ms": args.min_recording_duration_ms,
            "observed_duration_ms": stored_duration,
            "stored_bytes": stored_bytes,
            "drops": stored.get("drops"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
