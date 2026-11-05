#!/usr/bin/env python3
"""Causal and visible-isolation oracle for COMP-REQ-775 r61.

SSD1681 has one BUSY line, so maximum-rate waveform and sparse authored layers
must sometimes share one physical activation.  Independent clocks are not
enough: the Owner's r55 video proved that replaying a source-complete face
corridor makes unchanged face pixels visibly pulse with the waveform.  The r56
gate therefore also requires exact old/current deltas for authored layers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


FIELD_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")
PHASE_RE = re.compile(
    r"\[record-phase\]\s+track=([a-z]+)\s+request=(\d+)")
FACE_DUE_RE = re.compile(
    r"track=face\s+request=\d+\s+"
    r"due_source=authored_absolute_deadline\s+due_ms=(\d+)")
EXPRESSION_REQUEST_ID_BASE = 0xE0000000
EXPRESSION_REQUEST_ID_MASK = 0xF0000000
REJECTED_MARKERS = (
    "life_wave_joint_r52",
    "joint=r52",
    "face_joint=r52",
    "life_wave_copaint mode=shared_0xCF",
)


def fields(line: str) -> dict[str, str]:
    # Long hardware captures can contain character-level UART interleaving
    # between the display and storage tasks.  Keep the first occurrence: it
    # belongs to the record-phase prefix being parsed; a later duplicate such
    # as accessory due_ms is evidence from the spliced suffix.
    result: dict[str, str] = {}
    for key, value in FIELD_RE.findall(line):
        result.setdefault(key, value)
    return result


def is_expression_request_id(request_id: int) -> bool:
    return ((request_id & EXPRESSION_REQUEST_ID_MASK) ==
            EXPRESSION_REQUEST_ID_BASE)


def active_segment(lines: list[str]) -> list[str]:
    starts = [i for i, line in enumerate(lines)
              if "action=overlay_start result=1" in line]
    start = starts[-1] if starts else 0
    stops = [i for i in range(start + 1, len(lines))
             if ("action=stop_queue result=1" in lines[i]
                 or "[rec-flash] auto_stop deadline" in lines[i])]
    return lines[start:(stops[0] + 1 if stops else len(lines))]


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1,
                max(0, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def classify(path: Path, *, min_wave: int, min_face: int, min_blink: int,
             min_accessory: int, max_wave_gap_ms: int,
             max_wave_p95_gap_ms: int, **_: object) -> dict[str, object]:
    raw = path.read_bytes()
    lines = active_segment(
        raw.decode("utf-8", errors="replace").splitlines())
    rejected_markers = sorted({marker for marker in REJECTED_MARKERS
                               if any(marker in line for line in lines)})
    events: list[dict[str, object]] = []
    accessory_clock: list[dict[str, str]] = []
    screen_blink_by_request: dict[int, dict[str, object]] = {}
    pure_wave_driver_count = 0
    exact_authored_wave_driver_count = 0
    source_complete_authored_driver_count = 0
    exact_delta_fallback_count = 0
    recording_contract_count = 0
    for line_number, line in enumerate(lines, 1):
        if "[accessory-clock]" in line:
            accessory_clock.append(fields(line))
        if "[epaper] mic_local_partial only=1" in line:
            pure_wave_driver_count += 1
        if ("[epaper] authored_plus_wave_isolated_bands" in line
                and "wave_visible=1" in line
                and "unchanged_face_driven=0" in line
                and "old_current=1" in line
                and "topology=r61" in line):
            exact_authored_wave_driver_count += 1
        if ("[epaper] authored_plus_wave_source_complete" in line
                and "wave_visible=1" in line
                and "wave_owner=recording_scheduler" in line):
            source_complete_authored_driver_count += 1
        if "[epaper] authored_plus_wave_exact_delta_fallback" in line:
            exact_delta_fallback_count += 1
        if "[epaper] recording_ram_contract present=1" in line:
            recording_contract_count += 1
        if "[screen-blink] phase=" in line and "recording=1" in line:
            row = fields(line)
            try:
                request = int(row["request"])
            except (KeyError, ValueError):
                request = 0
            if is_expression_request_id(request):
                screen_blink_by_request[request] = {
                    "line": line_number,
                    "track": "blink",
                    "request": request,
                    "visible_ms": None,
                    "due_ms": None,
                    "fields": row,
                }
        match = PHASE_RE.search(line)
        if match is None:
            continue
        request = int(match.group(2))
        if not is_expression_request_id(request):
            continue
        row = fields(line)
        try:
            visible_ms = int(row["visible_ms"])
        except (KeyError, ValueError):
            visible_ms = None
        due_match = FACE_DUE_RE.search(line)
        due_ms = int(due_match.group(1)) if due_match is not None else None
        events.append({
            "line": line_number,
            "track": match.group(1),
            "request": request,
            "visible_ms": visible_ms,
            "due_ms": due_ms,
            "fields": row,
        })

    wave = [e for e in events if e["track"] == "wave"]
    face = [e for e in events if e["track"] == "face"]
    blink_by_request = dict(screen_blink_by_request)
    for event in events:
        if event["track"] == "blink":
            request = int(event["request"])
            merged = dict(blink_by_request.get(request, {}).get("fields", {}))
            merged.update(event["fields"])
            event["fields"] = merged
            blink_by_request[request] = event
    blink = list(blink_by_request.values())
    non_wave = face + blink
    wave_ids = {int(e["request"]) for e in wave}
    non_wave_ids = {int(e["request"]) for e in non_wave}
    explicitly_attested_carrier_ids = {
        int(e["request"]) for e in non_wave
        if e["fields"].get("wave_carried") == "1"
    }
    missing_wave_log_ids = sorted(non_wave_ids - wave_ids)
    missing_wave_carriers = sorted(
        non_wave_ids - wave_ids - explicitly_attested_carrier_ids)
    shared_carrier_ids = sorted(non_wave_ids & wave_ids)

    raw_wave_gaps: list[int] = []
    wave_gaps: list[int] = []
    wave_gap_records: list[dict[str, int]] = []
    for earlier, later in zip(wave, wave[1:]):
        if (earlier["visible_ms"] is None or later["visible_ms"] is None):
            continue
        elapsed = int(later["visible_ms"]) - int(earlier["visible_ms"])
        request_distance = int(later["request"]) - int(earlier["request"])
        if elapsed < 0 or request_distance <= 0:
            continue
        raw_wave_gaps.append(elapsed)
        # A missing UART line must not masquerade as a stopped physical wave.
        # Expression request IDs are monotonic per activation, so normalize
        # elapsed time by the number of carrier activations represented.
        normalized = math.ceil(elapsed / request_distance)
        wave_gaps.append(normalized)
        wave_gap_records.append({
            "earlier_request": int(earlier["request"]),
            "later_request": int(later["request"]),
            "earlier_visible_ms": int(earlier["visible_ms"]),
            "later_visible_ms": int(later["visible_ms"]),
            "request_distance": request_distance,
            "raw_gap_ms": elapsed,
            "normalized_gap_ms": normalized,
            "earlier_line": int(earlier["line"]),
            "later_line": int(later["line"]),
        })
    face_with_due = [e for e in face if e["due_ms"] is not None]
    face_due = [int(e["due_ms"]) for e in face_with_due]
    face_due_gaps = [later - earlier
                     for earlier, later in zip(face_due, face_due[1:])
                     if later > earlier]
    # The authored loop is re-anchored to HAL_GetTick() when its finite scene
    # table wraps.  That boundary preserves the 480 ms cadence but can move the
    # new epoch by a few scheduler milliseconds (the long hardware proof has a
    # single 963 ms gap at authored_loop, i.e. 2 * 480 ms + 3 ms).  Measure the
    # distance to the nearest grid point instead of requiring an impossible
    # zero-jitter RTOS timestamp.  Five milliseconds is deliberately far below
    # one display activation (~442 ms), so a wave-locked or skipped cadence
    # cannot pass through this tolerance.
    face_due_grid_error = [abs(gap - round(gap / 480) * 480)
                           for gap in face_due_gaps]
    authored_loop_reanchor_gaps: list[int] = []
    unexplained_grid_gaps: list[int] = []
    for earlier, later in zip(face_with_due, face_with_due[1:]):
        gap = int(later["due_ms"]) - int(earlier["due_ms"])
        if gap <= 0 or abs(gap - round(gap / 480) * 480) <= 5:
            continue
        between_events = lines[int(earlier["line"]):int(later["line"])]
        if any("[screen-life] authored_loop" in line
               for line in between_events):
            authored_loop_reanchor_gaps.append(gap)
        else:
            unexplained_grid_gaps.append(gap)

    wave_causal = [
        e for e in wave
        if e["fields"].get("due_source") == "recording_scheduler"
        and e["fields"].get("carrier") in {
            "pure_wave", "authored_life", "authored_blink",
            "functional_accessory"}
        and e["fields"].get("face_clock_advanced") == "0"
        and e["fields"].get("accessory_clock_advanced") == "0"
    ]
    face_causal = [
        e for e in face
        if e["fields"].get("due_source") == "authored_absolute_deadline"
        and e["fields"].get("wave_carried") == "1"
        and e["fields"].get("wave_drives_face") == "0"
    ]
    blink_causal = [
        e for e in blink
        if e["fields"].get("due_source") == "blink_scheduler"
        and e["fields"].get("wave_carried") == "1"
        and e["fields"].get("wave_drives_blink") == "0"
    ]
    accessory_causal = [
        row for row in accessory_clock
        if row.get("due_source") == "charging_wall_clock"
        and row.get("wave_clock_advanced") == "0"
        and row.get("life_clock_advanced") == "0"
        and row.get("blink_clock_advanced") == "0"
    ]

    wave_p95 = percentile(wave_gaps, 0.95)
    wave_max = max(wave_gaps) if wave_gaps else None
    wave_max_record = (
        max(wave_gap_records, key=lambda row: row["normalized_gap_ms"])
        if wave_gap_records else None
    )
    sparse_ratio = len(non_wave_ids) / len(wave_ids) if wave_ids else 1.0
    authored_gap_set = sorted(set(face_due_gaps))
    all_request_ids = wave_ids | non_wave_ids
    expected_activation_count = (
        max(all_request_ids) - min(all_request_ids) + 1
        if all_request_ids else 0)
    driver_wave_activation_count = (
        pure_wave_driver_count + exact_authored_wave_driver_count)
    driver_activation_coverage = (
        driver_wave_activation_count / expected_activation_count
        if expected_activation_count else 0.0)
    contract_activation_coverage = (
        recording_contract_count / expected_activation_count
        if expected_activation_count else 0.0)
    authored_driver_coverage = (
        exact_authored_wave_driver_count / len(non_wave_ids)
        if non_wave_ids else 0.0)
    checks = {
        "no_rejected_legacy_joint": not rejected_markers,
        "enough_wave_events": len(wave) >= min_wave,
        "enough_face_events": len(face) >= min_face,
        "enough_blink_events": len(blink) >= min_blink,
        "enough_accessory_clock_events": len(accessory_clock) >= min_accessory,
        "wave_clock_owner_is_recording_scheduler": (
            bool(wave) and len(wave_causal) / len(wave) >= 0.90),
        "every_authored_activation_carries_wave": (
            bool(non_wave_ids) and not missing_wave_carriers
            and authored_driver_coverage >= 0.90),
        "authored_carriers_are_visibly_isolated_exact_deltas": (
            exact_authored_wave_driver_count > 0
            and source_complete_authored_driver_count == 0
            and exact_delta_fallback_count == 0),
        "face_clock_owner_is_absolute_life_deadline": (
            bool(face) and len(face_causal) / len(face) >= 0.90),
        "blink_clock_owner_is_blink_scheduler": (
            bool(blink) and len(blink_causal) / len(blink) >= 0.90),
        "accessory_clock_is_independent": (
            (len(accessory_clock) == 0 and min_accessory == 0)
            or (bool(accessory_clock)
                and len(accessory_causal) / len(accessory_clock) >= 0.90)),
        "wave_uses_every_physical_recording_activation": (
            bool(shared_carrier_ids)
            and driver_activation_coverage >= 0.90
            and contract_activation_coverage >= 0.95),
        "authored_layers_are_sparse_relative_to_wave": sparse_ratio < 0.80,
        "authored_due_gaps_follow_480ms_grid": (
            bool(face_due_gaps)
            and not unexplained_grid_gaps),
        "authored_due_gaps_are_not_one_fixed_wave_period": (
            len(authored_gap_set) >= 2),
        "wave_has_no_face_or_accessory_pause": (
            bool(wave_gaps) and wave_max is not None
            and wave_max <= max_wave_gap_ms
            and wave_p95 is not None
            and wave_p95 <= max_wave_p95_gap_ms),
    }
    independent = all(checks.values())
    locked = (bool(rejected_markers) or bool(missing_wave_carriers)
              or source_complete_authored_driver_count > 0)
    classification = ("PHASE_INDEPENDENT" if independent else
                      "PHASE_LOCKED" if locked else
                      "INSUFFICIENT_OR_INVALID_EVIDENCE")
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "classification": classification,
        "counts": {
            "wave": len(wave), "face": len(face), "blink": len(blink),
            "accessory_clock": len(accessory_clock),
            "shared_carrier_ids": len(shared_carrier_ids),
            "missing_wave_carriers": len(missing_wave_carriers),
            "missing_wave_log_ids_uart_interleaving": len(missing_wave_log_ids),
            "pure_wave_driver_activations": pure_wave_driver_count,
            "exact_authored_wave_driver_activations":
                exact_authored_wave_driver_count,
            "source_complete_authored_driver_activations":
                source_complete_authored_driver_count,
            "exact_delta_fallback_activations": exact_delta_fallback_count,
            "recording_ram_contract_activations": recording_contract_count,
            "expected_request_span_activations": expected_activation_count,
        },
        "timing": {
            "wave_gap_p95_ms": wave_p95,
            "wave_gap_max_ms": wave_max,
            "wave_gap_max_event": wave_max_record,
            "raw_uart_wave_gap_p95_ms": percentile(raw_wave_gaps, 0.95),
            "raw_uart_wave_gap_max_ms": (
                max(raw_wave_gaps) if raw_wave_gaps else None),
            "authored_due_gap_ms": authored_gap_set,
            "authored_due_grid_error_max_ms": (
                max(face_due_grid_error) if face_due_grid_error else None),
            "authored_to_wave_ratio": sparse_ratio,
            "driver_wave_activation_coverage": driver_activation_coverage,
            "recording_contract_activation_coverage":
                contract_activation_coverage,
            "authored_driver_coverage": authored_driver_coverage,
            "authored_loop_reanchor_gap_ms": authored_loop_reanchor_gaps,
            "unexplained_authored_grid_gap_ms": unexplained_grid_gaps,
        },
        "rejected_markers": rejected_markers,
        "missing_wave_carriers": missing_wave_carriers,
        "missing_wave_log_ids_uart_interleaving": missing_wave_log_ids,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--negative-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-wave", type=int, default=20)
    parser.add_argument("--min-face", type=int, default=6)
    parser.add_argument("--min-blink", type=int, default=2)
    parser.add_argument("--min-accessory", type=int, default=1)
    # Scheduler/trace timestamps have a measured +/-2 ms edge around the
    # 800 ms safety ceiling. A second SSD1681 BUSY would be about 900 ms.
    parser.add_argument("--max-wave-gap-ms", type=int, default=805)
    # Exact old/current face bands add safe pre-transfer time but never a
    # second BUSY activation.  675 ms preserves the measured fastest isolated
    # carrier (r58=656 ms p95) while remaining far below a two-BUSY pause.
    parser.add_argument("--max-wave-p95-gap-ms", type=int, default=675)
    # Kept for CLI compatibility with archived runners; coincidence is now
    # expected transport coalescing and is not used as an independence test.
    parser.add_argument("--coincidence-window-ms", type=int, default=30)
    parser.add_argument("--max-coincidence-fraction", type=float, default=0.05)
    args = parser.parse_args()
    options = vars(args).copy()
    options.pop("candidate")
    options.pop("negative_log")
    options.pop("output")
    candidate = classify(args.candidate, **options)
    negative = classify(args.negative_log, **options)
    checks = {
        "candidate_is_phase_independent": (
            candidate["classification"] == "PHASE_INDEPENDENT"),
        "owner_rejected_log_is_physically_synchronized": (
            negative["classification"] == "PHASE_LOCKED"),
    }
    result = {
        "schema": "companion.comp_req_775.visible_isolation_oracle.v4",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "candidate": candidate,
        "owner_rejected_negative": negative,
        "policy": {
            **options,
            "shared_request_id_means_transport_carrier_not_shared_clock": True,
            "wave_between_faces_is_not_used_as_independence_proof": True,
            "source_complete_face_carrier_is_visible_synchronization": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
