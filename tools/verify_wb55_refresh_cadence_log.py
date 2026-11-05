#!/usr/bin/env python3
"""Validate one or more bounded WB55 e-paper refresh-cadence groups."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_ID = "companion.wb55.refresh_cadence_log.v2"
REQUEST_COUNT = 6
PARTIAL_PROFILES = {
    "differential": {"control": "FC", "profile": "default", "data_planes": 2},
    "vendor_sample": {
        "control": "FF",
        "profile": "good_display_vendor_partial_ab",
        "data_planes": 1,
    },
}
TRANSPORT_PROFILES = {
    "vendor_edges": "software_vendor_edges",
    "direct_bsrr": "software_direct_bsrr_diagnostic",
}
POLICY = re.compile(
    r"\[epaper\] policy requested=3 selected=(?P<selected>\w+) "
    r"reason=(?P<reason>\d+) partial_count=(?P<count>\d+) "
    r"limit=(?P<limit>\d+) baseline=(?P<baseline>\d+)"
)
DIFFERENTIAL_TIMING = re.compile(
    r"\[epaper\] timing mode=differential .*"
    r"transfer_before_waveform_ms=(?P<before>\d+) "
    r"transfer_after_waveform_ms=(?P<after>\d+) "
    r"bytes=(?P<bytes>\d+) data_planes=(?P<planes>\d+) "
    r"spi=(?P<transport>\S+)"
)
PARTIAL_REFRESH = re.compile(
    r"\[epaper\] refresh mode=differential profile=(?P<profile>\S+) "
    r"control=0x(?P<control>[0-9A-F]+)"
)
MICRO_MOTION = re.compile(
    r"\[epaper\] cadence_micro_motion step=(?P<step>\d+) "
    r"origin=(?P<x>\d+),(?P<y>\d+) size=(?P<size>\d+) "
    r"delta_x=(?P<delta_x>\d+)"
)


def scoped_log(log: str) -> str:
    start = "[screen] refresh_cadence_diagnostic start requests=6"
    start_index = log.find(start)
    if start_index < 0:
        return ""
    end_match = re.search(
        r"\[screen\] refresh_cadence_diagnostic done interactive_requests=6 "
        r"cleanup_expected=1(?: groups=\d+)?",
        log[start_index:],
    )
    if end_match is None:
        return log[start_index:]
    return log[start_index : start_index + end_match.end()]


def evaluate(
    log: str,
    log_path: str,
    partial_profile: str = "differential",
    transport_profile: str = "vendor_edges",
    groups: int = 1,
    micro_motion: bool = False,
) -> dict[str, Any]:
    expected = PARTIAL_PROFILES[partial_profile]
    expected_transport = TRANSPORT_PROFILES[transport_profile]
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
    group_starts = [
        int(match.group("group"))
        for match in re.finditer(
            r"refresh_cadence_diagnostic group_start group=(?P<group>\d+)",
            scoped,
        )
    ]
    group_completions = [
        int(match.group("group"))
        for match in re.finditer(
            r"refresh_cadence_diagnostic group_complete group=(?P<group>\d+)",
            scoped,
        )
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
    differential_timings = [
        {
            "before_ms": int(match.group("before")),
            "after_ms": int(match.group("after")),
            "window_bytes": int(match.group("bytes")),
            "data_planes": int(match.group("planes")),
            "transport": match.group("transport"),
        }
        for match in DIFFERENTIAL_TIMING.finditer(scoped)
    ]
    partial_refreshes = [
        {"profile": match.group("profile"), "control": match.group("control")}
        for match in PARTIAL_REFRESH.finditer(scoped)
    ]
    maintenance_refreshes = re.findall(
        r"refresh mode=maintenance profile=good_display_mode1 control=0xC7",
        scoped,
    )
    expected_steps = list(range(1, REQUEST_COUNT + 1)) * groups
    expected_differential_counts = list(range(0, REQUEST_COUNT - 1)) * groups
    micro_motion_records = [
        {
            "step": int(match.group("step")),
            "x": int(match.group("x")),
            "y": int(match.group("y")),
            "size": int(match.group("size")),
            "delta_x": int(match.group("delta_x")),
        }
        for match in MICRO_MOTION.finditer(scoped)
    ]
    def micro_origin_x(step: int) -> int:
        phase = step % 8
        return 96 + (phase if phase <= 4 else 8 - phase)

    expected_micro_motion = [{"step": 0, "x": 96, "y": 98, "size": 4, "delta_x": 1}]
    expected_micro_motion.extend(
        {
            "step": step,
            "x": micro_origin_x(step),
            "y": 98,
            "size": 4,
            "delta_x": 1,
        }
        for step in range(1, groups * REQUEST_COUNT + 1)
    )
    checks = {
        "diagnostic_started": bool(scoped),
        "baseline_full": bool(policies)
        and policies[0]["selected"] == "full"
        and policies[0]["reason"] == 3,
        "expected_groups_started": group_starts == list(range(1, groups + 1)),
        "expected_groups_completed": group_completions == list(range(1, groups + 1)),
        "six_steps_queued": queued == expected_steps,
        "six_steps_completed": completed == expected_steps,
        "five_differential_requests": differential == expected_differential_counts,
        "one_sixth_request_maintenance": len(maintenance) == groups
        and all(
            policy["partial_count"] == 5
            and policy["reason"] == 4
            and policy["limit"] == 5
            for policy in maintenance
        ),
        "differential_waveform": len(partial_refreshes) == 5 * groups
        and all(
            refresh["control"] == expected["control"]
            and refresh["profile"] == expected["profile"]
            for refresh in partial_refreshes
        ),
        "correct_data_plane_count": len(differential_timings) == 5 * groups
        and all(
            timing["data_planes"] == expected["data_planes"]
            for timing in differential_timings
        ),
        "correct_transport_profile": len(differential_timings) == 5 * groups
        and all(
            timing["transport"] == expected_transport
            for timing in differential_timings
        ),
        "no_post_waveform_transfer": len(differential_timings) == 5 * groups
        and all(timing["after_ms"] == 0 for timing in differential_timings),
        "micro_motion_sequence": not micro_motion
        or micro_motion_records == expected_micro_motion,
        "micro_motion_local_window": not micro_motion
        or len(differential_timings) == 5 * groups
        and all(timing["window_bytes"] == 4 for timing in differential_timings),
        "mode1_waveform": (
            scoped.count("fast_profile=good_display_mode1") == groups
            and len(maintenance_refreshes) == groups
        ),
        "diagnostic_completed": (
            "[screen] refresh_cadence_diagnostic done "
            f"interactive_requests=6 cleanup_expected=1 groups={groups}"
        ) in scoped,
        "no_obsolete_delayed_maintenance": "screen_maintenance" not in scoped
        and "quiet_ms=1200" not in scoped,
        "no_diagnostic_abort": "refresh_cadence_diagnostic abort" not in scoped,
    }
    status = "PASS" if all(checks.values()) else "NO_GO_INCOMPLETE_REFRESH_CADENCE"
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "partial_profile": partial_profile,
        "transport_profile": transport_profile,
        "groups": groups,
        "micro_motion": micro_motion,
        "claim_scope": "reset-bounded serial evidence for the diagnostic image only; no human visual or current claim",
        "log": log_path,
        "checks": checks,
        "observed": {
            "policy_records": policies,
            "queued_steps": queued,
            "completed_steps": completed,
            "group_starts": group_starts,
            "group_completions": group_completions,
            "differential_timings": differential_timings,
            "partial_refreshes": partial_refreshes,
            "micro_motion_records": micro_motion_records,
        },
        "next_action": (
            "Run the focused ACPT-01 visual review; this trace does not prove residual-image quality or touch feel."
            if status == "PASS"
            else "Flash the dedicated refresh-cadence diagnostic image, capture through its done marker, and inspect the failed checks."
        ),
    }


def self_test(
    partial_profile: str,
    transport_profile: str,
    groups: int = 1,
    micro_motion: bool = False,
) -> dict[str, Any]:
    expected = PARTIAL_PROFILES[partial_profile]
    expected_transport = TRANSPORT_PROFILES[transport_profile]
    lines = [
        f"[screen] refresh_cadence_diagnostic start requests=6 groups={groups}",
        "[epaper] policy requested=3 selected=full reason=3 partial_count=0 limit=5 baseline=0",
        "[epaper] refresh mode=full control=0xF7",
        "[screen] refresh_cadence_diagnostic baseline_complete=1",
    ]
    if micro_motion:
        lines.append("[epaper] cadence_micro_motion step=0 origin=96,98 size=4 delta_x=1")
    for group in range(1, groups + 1):
        lines.append(f"[screen] refresh_cadence_diagnostic group_start group={group}")
        for step in range(1, 6):
            micro_step = (group - 1) * REQUEST_COUNT + step
            micro_phase = micro_step % 8
            micro_x = 96 + (micro_phase if micro_phase <= 4 else 8 - micro_phase)
            lines.extend(
                [
                    f"[screen] refresh_cadence_diagnostic queue step={step} item={step - 1} refresh=interactive",
                    f"[epaper] policy requested=3 selected=differential reason=1 partial_count={step - 1} limit=5 baseline=1",
                    "[epaper] refresh mode=differential "
                    f"profile={expected['profile']} control=0x{expected['control']}",
                    "[epaper] timing mode=differential prepare_ms=0 setup_ms=0 "
                    "transfer_before_waveform_ms=53 transfer_after_waveform_ms=0 "
                    f"bytes={4 if micro_motion else 2552} data_planes={expected['data_planes']} "
                    f"spi={expected_transport}",
                    f"[screen] refresh_cadence_diagnostic complete step={step}",
                ]
            )
            if micro_motion:
                lines.insert(
                    len(lines) - 1,
                    f"[epaper] cadence_micro_motion step={micro_step} origin={micro_x},98 size=4 delta_x=1",
                )
        micro_step = group * REQUEST_COUNT
        micro_phase = micro_step % 8
        micro_x = 96 + (micro_phase if micro_phase <= 4 else 8 - micro_phase)
        lines.extend(
            [
                "[screen] refresh_cadence_diagnostic queue step=6 item=5 refresh=interactive",
                "[epaper] policy requested=3 selected=maintenance reason=4 partial_count=5 limit=5 baseline=1",
                "[epaper] fast_profile=good_display_mode1 temp_sensor=1 temp_load=1 temp_reg=0x0064 lut_mode1=1",
                "[epaper] refresh mode=maintenance profile=good_display_mode1 control=0xC7",
                "[screen] refresh_cadence_diagnostic complete step=6",
                f"[screen] refresh_cadence_diagnostic group_complete group={group}",
            ]
        )
        if micro_motion:
            lines.insert(
                len(lines) - 2,
                f"[epaper] cadence_micro_motion step={micro_step} origin={micro_x},98 size=4 delta_x=1",
            )
    lines.append(
        f"[screen] refresh_cadence_diagnostic done interactive_requests=6 cleanup_expected=1 groups={groups}"
    )
    report = evaluate(
        "\n".join(lines),
        "synthetic-self-test",
        partial_profile,
        transport_profile,
        groups,
        micro_motion,
    )
    report["status"] = "PASS_STATIC_PARSER" if report["status"] == "PASS" else "FAIL_STATIC_PARSER"
    report["claim_scope"] = "synthetic parser self-test; no hardware claim"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--partial-profile", choices=PARTIAL_PROFILES, default="differential")
    parser.add_argument("--transport-profile", choices=TRANSPORT_PROFILES, default="vendor_edges")
    parser.add_argument("--groups", type=int, choices=range(1, 41), default=1)
    parser.add_argument("--micro-motion", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test(
            args.partial_profile,
            args.transport_profile,
            args.groups,
            args.micro_motion,
        )
    elif args.log is not None:
        if not args.log.is_file():
            parser.error(f"serial log not found: {args.log}")
        report = evaluate(
            args.log.read_text(encoding="utf-8", errors="replace"),
            str(args.log),
            args.partial_profile,
            args.transport_profile,
            args.groups,
            args.micro_motion,
        )
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
