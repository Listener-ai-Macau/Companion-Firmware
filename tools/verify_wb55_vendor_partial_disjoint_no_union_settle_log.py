#!/usr/bin/env python3
"""Fail-closed trace verifier for the two-pass disjoint no-union diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_STATIC = ROOT / (
    "docs/validation/"
    "companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-static-20260721.json"
)
EXPECTED_STATIC = "PASS_STATIC_SOURCE_EXACT_DISJOINT_NO_UNION_SETTLE_DEFAULT_OFF"
EXPECTED_SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
EXPECTED_PROFILE = "good_display_vendor_partial_disjoint_no_union_settle"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_disjoint_no_union_settle_trace.v1"
CHANGED_FRAMES = 48
EXPECTED_COMPLETIONS = CHANGED_FRAMES * 2
MAX_PASS_MS = 700
MAX_FRAME_MS = 1400
P95_FRAME_MS = 1200


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def nearest_rank_p95(values: list[int]) -> int | None:
    if not values:
        return None
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def _matches(pattern: str, text: str) -> list[re.Match[str]]:
    return list(re.finditer(pattern, text))


def evaluate(log_path: pathlib.Path, static_path: pathlib.Path) -> dict[str, Any]:
    static = load_json(static_path)
    text = log_path.read_text(encoding="utf-8-sig", errors="replace")
    boot = _matches(r"boot_diag pattern=6 .*? cycle=(\d+) result=(\d+) bytes=(\d+)", text)
    probes = _matches(
        r"disjoint_component_probe phase=(\d+) segment=(\d+) fraction=(\d+) "
        r"center=(\d+),(\d+) radius=(\d+)",
        text,
    )
    erase_region = _matches(
        r"vendor_partial_disjoint_no_union_settle pass=erase "
        r"x_byte=(\d+)\.\.(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) "
        r"window=(\d+) current_0x24=(\d+) no_0x26=1",
        text,
    )
    erase_refresh = _matches(
        r"vendor_partial_disjoint_no_union_settle pass=erase refresh control=0xFF "
        r"activation_command=0x20 activate=(\d+) complete=(\d+)",
        text,
    )
    erase_source = _matches(
        r"vendor_partial_disjoint_no_union_settle pass=erase source_sha256=([0-9A-F]+) "
        r"staged_regions=1 staged_bytes=(\d+) one_control=0xFF one_activation=0x20 "
        r"no_0x26=1 no_c7=1 no_full_write=1",
        text,
    )
    draw_region = _matches(
        r"vendor_partial_disjoint_no_union_settle pass=draw index=(\d+) "
        r"x_byte=(\d+)\.\.(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) "
        r"window=(\d+) current_0x24=(\d+) no_0x26=1",
        text,
    )
    draw_refresh = _matches(
        r"vendor_partial_disjoint_no_union_settle pass=draw refresh control=0xFF "
        r"activation_command=0x20 activate=(\d+) complete=(\d+)",
        text,
    )
    draw_source = _matches(
        r"vendor_partial_disjoint_no_union_settle pass=draw source_sha256=([0-9A-F]+) "
        r"staged_regions=(\d+) staged_bytes=(\d+) one_control=0xFF one_activation=0x20 "
        r"no_0x26=1 no_c7=1 no_full_write=1",
        text,
    )
    refresh = _matches(
        rf"refresh mode=differential profile={EXPECTED_PROFILE} control=0xFF .*?"
        r"activation_command=0x20 activate=(\d+) complete=(\d+) elapsed_ms=(\d+)",
        text,
    )
    identical = _matches(r"differential_skip identical_frame", text)

    candidate_events: list[tuple[int, str, re.Match[str]]] = []
    for name, matches in (
        ("erase_region", erase_region),
        ("refresh", refresh),
        ("erase_refresh", erase_refresh),
        ("erase_source", erase_source),
        ("draw_region", draw_region),
        ("draw_refresh", draw_refresh),
        ("draw_source", draw_source),
    ):
        candidate_events.extend((match.start(), name, match) for match in matches)
    candidate_events.sort(key=lambda item: item[0])

    sequence_ok = True
    frame_regions: list[list[re.Match[str]]] = []
    cursor = 0
    for _ in range(CHANGED_FRAMES):
        expected_prefix = ("erase_region", "refresh", "erase_refresh", "erase_source")
        if tuple(item[1] for item in candidate_events[cursor : cursor + 4]) != expected_prefix:
            sequence_ok = False
            break
        cursor += 4
        regions: list[re.Match[str]] = []
        while cursor < len(candidate_events) and candidate_events[cursor][1] == "draw_region":
            regions.append(candidate_events[cursor][2])
            cursor += 1
        if not 1 <= len(regions) <= 5:
            sequence_ok = False
            break
        frame_regions.append(regions)
        expected_suffix = ("refresh", "draw_refresh", "draw_source")
        if tuple(item[1] for item in candidate_events[cursor : cursor + 3]) != expected_suffix:
            sequence_ok = False
            break
        cursor += 3
    sequence_ok = sequence_ok and cursor == len(candidate_events) and len(frame_regions) == CHANGED_FRAMES

    draw_regions_bounded = all(
        int(match.group(7)) == 1
        and int(match.group(8)) == 1
        and 0 <= int(match.group(1)) <= 4
        and 0 <= int(match.group(2)) <= int(match.group(3)) < 25
        and 0 <= int(match.group(4)) <= int(match.group(5)) < 200
        and int(match.group(6)) == (int(match.group(3)) - int(match.group(2)) + 1)
        * (int(match.group(5)) - int(match.group(4)) + 1)
        for match in draw_region
    )
    disjoint_ordered = all(
        all(int(regions[index].group(3)) < int(regions[index + 1].group(2))
            for index in range(len(regions) - 1))
        for regions in frame_regions
    )
    source_counts_match = len(frame_regions) == len(draw_source) and all(
        len(regions) == int(source.group(2))
        and sum(int(region.group(6)) for region in regions) == int(source.group(3))
        for regions, source in zip(frame_regions, draw_source)
    )
    refresh_ms = [int(match.group(3)) for match in refresh]
    pair_ms = [refresh_ms[index] + refresh_ms[index + 1]
               for index in range(0, len(refresh_ms) - 1, 2)]
    partial_text = text[boot[0].end() :] if boot else text

    checks = {
        "static_contract_passed": static.get("status") == EXPECTED_STATIC,
        "one_baseline_48_changed_one_identical": (
            len(boot) == 50
            and [int(match.group(1)) for match in boot] == list(range(1, 51))
            and all(int(match.group(2)) == 0 for match in boot)
            and boot[-1].group(3) == "0"
            and len(identical) == 1
        ),
        "five_anchor_12px_probe_is_complete": (
            len(probes) == 50
            and all(
                int(match.group(1)) == (index % 40 if index < 49 else 8)
                and int(match.group(2)) == (index % 40 if index < 49 else 8) // 8
                and int(match.group(3)) == (index % 40 if index < 49 else 8) % 8
                and int(match.group(6)) == 12
                and 0 <= int(match.group(4)) < 200
                and 0 <= int(match.group(5)) < 200
                for index, match in enumerate(probes)
            )
            and min(int(match.group(4)) for match in probes) == 58
            and max(int(match.group(4)) for match in probes) == 142
            and min(int(match.group(5)) for match in probes) == 58
            and max(int(match.group(5)) for match in probes) == 142
        ),
        "strict_erase_then_draw_event_order_for_every_changed_frame": sequence_ok,
        "exactly_96_source_completions_and_busy_returns": (
            len(refresh) == EXPECTED_COMPLETIONS
            and len(erase_refresh) == CHANGED_FRAMES
            and len(draw_refresh) == CHANGED_FRAMES
            and all(match.group(1) == "1" and match.group(2) == "1" for match in refresh)
            and all(match.group(1) == "1" and match.group(2) == "1" for match in erase_refresh + draw_refresh)
        ),
        "erase_pass_is_current_0x24_previous_black_bbox": (
            len(erase_region) == CHANGED_FRAMES
            and all(
                match.group(6) == "1"
                and match.group(7) == "1"
                and 0 <= int(match.group(1)) <= int(match.group(2)) < 25
                and 0 <= int(match.group(3)) <= int(match.group(4)) < 200
                and int(match.group(5)) == (int(match.group(2)) - int(match.group(1)) + 1)
                * (int(match.group(4)) - int(match.group(3)) + 1)
                for match in erase_region
            )
        ),
        "draw_pass_has_one_to_five_bounded_disjoint_current_regions": (
            len(frame_regions) == CHANGED_FRAMES
            and draw_regions_bounded
            and disjoint_ordered
            and source_counts_match
        ),
        "all_passes_bind_the_exact_supplier_source_hash": (
            len(erase_source) == CHANGED_FRAMES
            and len(draw_source) == CHANGED_FRAMES
            and all(match.group(1) == EXPECTED_SOURCE_SHA for match in erase_source + draw_source)
        ),
        "single_pass_and_two_pass_frame_timing_are_bounded": (
            len(refresh_ms) == EXPECTED_COMPLETIONS
            and len(pair_ms) == CHANGED_FRAMES
            and max(refresh_ms, default=MAX_PASS_MS + 1) <= MAX_PASS_MS
            and max(pair_ms, default=MAX_FRAME_MS + 1) <= MAX_FRAME_MS
            and (nearest_rank_p95(pair_ms) or P95_FRAME_MS + 1) <= P95_FRAME_MS
        ),
        "identical_frame_has_zero_payload_and_no_activation": (
            len(identical) == 1 and boot and boot[-1].group(3) == "0" and len(refresh) == EXPECTED_COMPLETIONS
        ),
        "forbidden_partial_transport_is_absent": (
            "ram_write command=0x26" not in partial_text
            and "control=0xC7" not in partial_text
            and "ram_write command=0x24 bytes=5000" not in partial_text
            and "profile=good_display_vendor_partial_disjoint_current_stage" not in partial_text
        ),
        "no_panel_or_transport_error": (
            "result=4" not in text
            and "TRANSPORT_ERROR" not in text
            and "complete=0" not in text
            and "activate=0" not in text
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_TRACE"
        if not failures
        else "NO_GO_INCOMPLETE_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_TRACE",
        "claim_scope": "bounded machine trace only; no visual, temperature, production, or OLED-like claim",
        "checks": checks,
        "failures": failures,
        "log": {"path": rel(log_path), "sha256": hashlib.sha256(log_path.read_bytes()).hexdigest().upper()},
        "static_contract": {"path": rel(static_path), "status": static.get("status")},
        "changed_frames": len(frame_regions),
        "controller_completions": len(refresh),
        "busy_completions": sum(match.group(2) == "1" for match in refresh),
        "panel_errors": text.count("result=4") + text.count("TRANSPORT_ERROR"),
        "regions_per_changed_frame": [len(regions) for regions in frame_regions],
        "refresh_elapsed_ms": refresh_ms,
        "per_frame_two_completion_elapsed_ms": pair_ms,
        "timing": {
            "single_completion_limit_ms": MAX_PASS_MS,
            "single_completion_max_ms": max(refresh_ms, default=None),
            "two_completion_p95_limit_ms": P95_FRAME_MS,
            "two_completion_p95_ms": nearest_rank_p95(pair_ms),
            "two_completion_max_limit_ms": MAX_FRAME_MS,
            "two_completion_max_ms": max(pair_ms, default=None),
        },
    }


def synthetic_fixture(*, third_refresh: bool = False, timeout: bool = False,
                      forbidden_0x26: bool = False, missing_completion: bool = False,
                      wrong_order: bool = False) -> str:
    lines: list[str] = []
    for cycle in range(1, 51):
        phase = (cycle - 1) % 40 if cycle < 50 else 8
        segment, fraction = divmod(phase, 8)
        anchors = ((100, 100), (100, 58), (142, 100), (100, 142), (58, 100))
        if phase in (0, 8, 16, 24, 32):
            x, y = anchors[segment]
        else:
            x, y = 100, 100
        lines.append(f"[epaper] disjoint_component_probe phase={phase} segment={segment} fraction={fraction} center={x},{y} radius=12")
        if cycle == 1:
            lines.append("[epaper] boot_diag pattern=6 official=0 cycle=1 result=0 bytes=10000")
            continue
        if cycle == 50:
            lines.append("[epaper] differential_skip identical_frame")
            lines.append("[epaper] boot_diag pattern=6 official=0 cycle=50 result=0 bytes=0")
            continue
        elapsed = 701 if timeout and cycle == 2 else 447
        erase = [
            "[epaper] vendor_partial_disjoint_no_union_settle pass=erase x_byte=10..12 y=80..120 bytes=123 window=1 current_0x24=1 no_0x26=1",
            f"[epaper] refresh mode=differential profile={EXPECTED_PROFILE} control=0xFF activation_command=0x20 activate=1 complete=1 elapsed_ms={elapsed}",
            "[epaper] vendor_partial_disjoint_no_union_settle pass=erase refresh control=0xFF activation_command=0x20 activate=1 complete=1",
            f"[epaper] vendor_partial_disjoint_no_union_settle pass=erase source_sha256={EXPECTED_SOURCE_SHA} staged_regions=1 staged_bytes=123 one_control=0xFF one_activation=0x20 no_0x26=1 no_c7=1 no_full_write=1",
        ]
        draw = [
            "[epaper] vendor_partial_disjoint_no_union_settle pass=draw index=0 x_byte=9..9 y=90..100 bytes=11 window=1 current_0x24=1 no_0x26=1",
            "[epaper] vendor_partial_disjoint_no_union_settle pass=draw index=1 x_byte=13..13 y=90..100 bytes=11 window=1 current_0x24=1 no_0x26=1",
            f"[epaper] refresh mode=differential profile={EXPECTED_PROFILE} control=0xFF activation_command=0x20 activate=1 complete=1 elapsed_ms=447",
            "[epaper] vendor_partial_disjoint_no_union_settle pass=draw refresh control=0xFF activation_command=0x20 activate=1 complete=1",
            f"[epaper] vendor_partial_disjoint_no_union_settle pass=draw source_sha256={EXPECTED_SOURCE_SHA} staged_regions=2 staged_bytes=22 one_control=0xFF one_activation=0x20 no_0x26=1 no_c7=1 no_full_write=1",
        ]
        if wrong_order and cycle == 2:
            lines.extend(draw + erase)
        else:
            lines.extend(erase + draw)
        if third_refresh and cycle == 2:
            lines.append(f"[epaper] refresh mode=differential profile={EXPECTED_PROFILE} control=0xFF activation_command=0x20 activate=1 complete=1 elapsed_ms=447")
        lines.append(f"[epaper] boot_diag pattern=6 official=0 cycle={cycle} result=0 bytes=22")
    if missing_completion:
        for index, line in enumerate(lines):
            if "pass=draw refresh" in line:
                del lines[index]
                break
    if forbidden_0x26:
        lines.insert(10, "[epaper] ram_write command=0x26 bytes=22")
    return "\n".join(lines) + "\n"


def self_test() -> int:
    cases = (
        ("positive", {}, True),
        ("missing_completion", {"missing_completion": True}, False),
        ("third_refresh", {"third_refresh": True}, False),
        ("forbidden_0x26", {"forbidden_0x26": True}, False),
        ("wrong_order", {"wrong_order": True}, False),
        ("timeout", {"timeout": True}, False),
    )
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        base = pathlib.Path(directory)
        static = base / "static.json"
        static.write_text(json.dumps({"status": EXPECTED_STATIC}), encoding="utf-8")
        for name, kwargs, expected_pass in cases:
            log = base / f"{name}.log"
            log.write_text(synthetic_fixture(**kwargs), encoding="utf-8")
            passed = evaluate(log, static)["status"].startswith("PASS_MACHINE")
            if passed != expected_pass:
                failures.append(name)
    if failures:
        print(f"FAIL: trace verifier self-test cases: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("PASS: trace verifier fail-closed self-tests (positive + 5 negative fixtures)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--static-contract", type=pathlib.Path, default=DEFAULT_STATIC)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.log is None or args.out is None:
        parser.error("--log and --out are required unless --self-test is used")
    try:
        report = evaluate(args.log.resolve(), args.static_contract.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: trace parsing failed: {error}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: {rel(args.out)}")
    return 0 if report["status"].startswith("PASS_MACHINE") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
