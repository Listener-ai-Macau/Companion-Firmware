#!/usr/bin/env python3
"""Fail-closed parser for the bounded added-first/old-cleanup serial trace."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-static-20260721.json"
OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-machine-gate-20260721.json"
EXPECTED_STATIC = "PASS_STATIC_SOURCE_EXACT_ADDED_FIRST_OLD_CLEANUP_DEFAULT_OFF"
EXPECTED_SOURCE = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
PROFILE = "good_display_vendor_partial_added_first_old_cleanup"
PASS_STATUS = "PASS_MACHINE_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_TRACE"

BOOT_RE = re.compile(r"boot_diag pattern=6 official=0 cycle=(\d+) result=(\d+) bytes=(\d+) busy=(\d+) vendor_1s_lut=0 vendor_partial_source=1")
PLAN_RE = re.compile(r"vendor_partial_added_first_old_cleanup plan added_regions=(\d+) eligible_bytes=(\d+) mixed_excluded_bytes=(\d+) old_bytes=(\d+) over_limit=(\d+) no_fallback=1 no_union=1")
ADDED_RE = re.compile(r"vendor_partial_added_first_old_cleanup pass=added index=(\d+) x_byte=(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) predicate_verified=(\d+) mixed_transition=0 window=(\d+) current_0x24=(\d+)")
ADDED_REFRESH_RE = re.compile(r"vendor_partial_added_first_old_cleanup pass=added refresh control=0xFF activation_command=0x20 activate=(\d+) complete=(\d+)")
ADDED_SOURCE_RE = re.compile(r"vendor_partial_added_first_old_cleanup pass=added source_sha256=([0-9A-F]+) staged_regions=(\d+) staged_bytes=(\d+) eligible_bytes=(\d+) mixed_excluded_bytes=(\d+) one_control=0xFF one_activation=0x20 no_fallback=1 no_union=1 no_0x21=1 no_0x37=1 no_0x26=1 no_c7=1 no_full_write=1")
CLEANUP_RE = re.compile(r"vendor_partial_added_first_old_cleanup pass=cleanup x_byte=(\d+)\.\.(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) window=(\d+) current_0x24=(\d+)")
CLEANUP_REFRESH_RE = re.compile(r"vendor_partial_added_first_old_cleanup pass=cleanup refresh control=0xFF activation_command=0x20 activate=(\d+) complete=(\d+)")
CLEANUP_SOURCE_RE = re.compile(r"vendor_partial_added_first_old_cleanup pass=cleanup source_sha256=([0-9A-F]+) staged_regions=1 staged_bytes=(\d+) one_control=0xFF one_activation=0x20 no_fallback=1 no_union=1 no_0x21=1 no_0x37=1 no_0x26=1 no_c7=1 no_full_write=1")
GENERIC_RE = re.compile(rf"refresh mode=differential profile={PROFILE} control=0xFF .*?activation_command=0x20 activate=(\d+) complete=(\d+) elapsed_ms=(\d+)")


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def percentile95(values: list[int]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = 0.95 * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def one(pattern: re.Pattern[str], block: str) -> re.Match[str] | None:
    matches = list(pattern.finditer(block))
    return matches[0] if len(matches) == 1 else None


def evaluate(log_path: pathlib.Path, static_path: pathlib.Path) -> dict[str, Any]:
    text = log_path.read_text(encoding="utf-8-sig", errors="replace")
    static = json.loads(static_path.read_text(encoding="utf-8-sig"))
    boots = list(BOOT_RE.finditer(text))
    blocks: dict[int, str] = {}
    previous_end = 0
    for boot in boots:
        cycle = int(boot.group(1))
        blocks[cycle] = text[previous_end:boot.end()]
        previous_end = boot.end()

    frame_rows: list[dict[str, Any]] = []
    structural_ok = True
    for cycle in range(2, 50):
        block = blocks.get(cycle, "")
        plan = one(PLAN_RE, block)
        added_refresh = one(ADDED_REFRESH_RE, block)
        added_source = one(ADDED_SOURCE_RE, block)
        cleanup = one(CLEANUP_RE, block)
        cleanup_refresh = one(CLEANUP_REFRESH_RE, block)
        cleanup_source = one(CLEANUP_SOURCE_RE, block)
        generics = list(GENERIC_RE.finditer(block))
        regions = list(ADDED_RE.finditer(block))
        boot = next((match for match in boots if int(match.group(1)) == cycle), None)
        complete = all(item is not None for item in (plan, added_refresh, added_source, cleanup,
                                                       cleanup_refresh, cleanup_source, boot)) and len(generics) == 2
        if not complete:
            structural_ok = False
            frame_rows.append({"cycle": cycle, "valid": False, "reason": "missing_or_duplicate_event"})
            continue
        assert plan and added_refresh and added_source and cleanup and cleanup_refresh and cleanup_source and boot
        expected_regions = int(plan.group(1))
        eligible = int(plan.group(2))
        mixed = int(plan.group(3))
        old_bytes = int(plan.group(4))
        region_bytes = sum(int(match.group(5)) for match in regions)
        region_indexes = [int(match.group(1)) for match in regions]
        region_shapes_ok = all(
            int(match.group(3)) <= int(match.group(4))
            and int(match.group(5)) == int(match.group(4)) - int(match.group(3)) + 1
            and match.group(6) == match.group(7) == match.group(8) == "1"
            for match in regions
        )
        order_tokens = (" plan ", " pass=added index=", " pass=added refresh ",
                        " pass=added source_", " pass=cleanup x_", " pass=cleanup refresh ",
                        " pass=cleanup source_")
        positions = [block.find(f"vendor_partial_added_first_old_cleanup{token}") for token in order_tokens]
        event_order_ok = all(position >= 0 for position in positions) and positions == sorted(positions)
        elapsed = [int(match.group(3)) for match in generics]
        valid = (
            2 <= expected_regions <= 8
            and len(regions) == expected_regions
            and region_indexes == list(range(expected_regions))
            and region_shapes_ok
            and region_bytes == eligible
            and added_source.group(1) == cleanup_source.group(1) == EXPECTED_SOURCE
            and int(added_source.group(2)) == expected_regions
            and int(added_source.group(3)) == eligible
            and int(added_source.group(4)) == eligible
            and int(added_source.group(5)) == mixed
            and plan.group(5) == "0"
            and cleanup.group(6) == cleanup.group(7) == "1"
            and int(cleanup.group(5)) == old_bytes == int(cleanup_source.group(2))
            and added_refresh.group(1) == added_refresh.group(2) == "1"
            and cleanup_refresh.group(1) == cleanup_refresh.group(2) == "1"
            and all(match.group(1) == match.group(2) == "1" for match in generics)
            and all(value <= 700 for value in elapsed)
            and int(boot.group(2)) == 0 and int(boot.group(3)) == eligible + old_bytes
            and event_order_ok
        )
        structural_ok &= valid
        frame_rows.append({"cycle": cycle, "valid": valid, "added_regions": expected_regions,
                           "eligible_bytes": eligible, "mixed_excluded_bytes": mixed,
                           "old_bytes": old_bytes, "completion_ms": elapsed,
                           "frame_completion_ms": sum(elapsed)})

    partial_text = "".join(blocks.get(cycle, "") for cycle in range(2, 51))
    refresh_matches = list(GENERIC_RE.finditer(partial_text))
    frame_times = [row["frame_completion_ms"] for row in frame_rows if row.get("valid")]
    completion_times = [value for row in frame_rows if row.get("valid") for value in row["completion_ms"]]
    final_block = blocks.get(50, "")
    final_boot = next((match for match in boots if int(match.group(1)) == 50), None)
    forbidden_tokens = (
        "ram_write command=0x26", "command=0x21", "command=0x2D", "command=0x37",
        "control=0xC7", "bytes=5000", "no_fallback=0", "no_union=0",
        "mixed_transition=1", "full_write_profile=", "vendor_1s_lut loaded",
    )
    checks = {
        "static_contract_passed": static.get("status") == EXPECTED_STATIC,
        "exactly_50_ordered_boot_results": [int(match.group(1)) for match in boots] == list(range(1, 51)),
        "all_boot_results_success": len(boots) == 50 and all(match.group(2) == "0" for match in boots),
        "exactly_48_valid_changed_frames": structural_ok and len(frame_rows) == 48 and all(row.get("valid") for row in frame_rows),
        "exactly_96_source_profile_completions": len(refresh_matches) == 96,
        "all_96_activations_and_busy_completions_pass": len(refresh_matches) == 96 and all(match.group(1) == match.group(2) == "1" for match in refresh_matches),
        "each_completion_at_most_700ms": len(completion_times) == 96 and max(completion_times, default=9999) <= 700,
        "two_completion_frame_p95_at_most_1200ms": len(frame_times) == 48 and percentile95(frame_times) <= 1200,
        "two_completion_frame_max_at_most_1400ms": len(frame_times) == 48 and max(frame_times, default=9999) <= 1400,
        "identical_final_frame_has_zero_payload_and_activation": final_boot is not None
            and final_boot.group(2) == "0" and final_boot.group(3) == "0"
            and "differential_skip identical_frame" in final_block
            and PROFILE not in final_block and "vendor_partial_added_first_old_cleanup plan" not in final_block,
        "no_forbidden_command_or_fallback_after_baseline": not any(token in partial_text for token in forbidden_tokens),
        "no_panel_error_trace": not re.search(r"(?:ready=0|complete=0|activate=0|result=[1-9]|ERROR|FAIL)", partial_text, re.IGNORECASE),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": "companion.wb55.gdey0154d67_t03.vendor_partial_added_first_old_cleanup_trace.v1",
        "status": PASS_STATUS if not failures else "NO_GO_INCOMPLETE_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_TRACE",
        "checks": checks,
        "failures": failures,
        "counts": {"requests": len(boots), "changed_frames": len(frame_rows),
                   "source_completions": len(refresh_matches), "busy_completions": sum(match.group(2) == "1" for match in refresh_matches)},
        "timing_ms": {"completion_max": max(completion_times, default=None),
                      "frame_p95": percentile95(frame_times) if frame_times else None,
                      "frame_max": max(frame_times, default=None)},
        "frames": frame_rows,
        "source": {"raw_log": rel(log_path), "static_contract": rel(static_path)},
    }


def fixture(**mutations: bool) -> str:
    lines = ["[epaper] boot_diag pattern=6 official=0 cycle=1 result=0 bytes=5000 busy=0 vendor_1s_lut=0 vendor_partial_source=1"]
    for cycle in range(2, 50):
        lines.extend([
            "[epaper] vendor_partial_added_first_old_cleanup plan added_regions=2 eligible_bytes=22 mixed_excluded_bytes=1 old_bytes=123 over_limit=0 no_fallback=1 no_union=1",
            "[epaper] vendor_partial_added_first_old_cleanup pass=added index=0 x_byte=9 y=90..100 bytes=11 predicate_verified=1 mixed_transition=0 window=1 current_0x24=1",
            "[epaper] vendor_partial_added_first_old_cleanup pass=added index=1 x_byte=13 y=90..100 bytes=11 predicate_verified=1 mixed_transition=0 window=1 current_0x24=1",
            f"[epaper] refresh mode=differential profile={PROFILE} control=0xFF expected_visible_flicker=none activation_count=1 busy=0 update=1 activation_command=0x20 activate=1 complete=1 elapsed_ms=447",
            "[epaper] vendor_partial_added_first_old_cleanup pass=added refresh control=0xFF activation_command=0x20 activate=1 complete=1",
            f"[epaper] vendor_partial_added_first_old_cleanup pass=added source_sha256={EXPECTED_SOURCE} staged_regions=2 staged_bytes=22 eligible_bytes=22 mixed_excluded_bytes=1 one_control=0xFF one_activation=0x20 no_fallback=1 no_union=1 no_0x21=1 no_0x37=1 no_0x26=1 no_c7=1 no_full_write=1",
            "[epaper] vendor_partial_added_first_old_cleanup pass=cleanup x_byte=10..12 y=80..120 bytes=123 window=1 current_0x24=1",
            f"[epaper] refresh mode=differential profile={PROFILE} control=0xFF expected_visible_flicker=none activation_count=2 busy=0 update=1 activation_command=0x20 activate=1 complete=1 elapsed_ms=447",
            "[epaper] vendor_partial_added_first_old_cleanup pass=cleanup refresh control=0xFF activation_command=0x20 activate=1 complete=1",
            f"[epaper] vendor_partial_added_first_old_cleanup pass=cleanup source_sha256={EXPECTED_SOURCE} staged_regions=1 staged_bytes=123 one_control=0xFF one_activation=0x20 no_fallback=1 no_union=1 no_0x21=1 no_0x37=1 no_0x26=1 no_c7=1 no_full_write=1",
            f"[epaper] boot_diag pattern=6 official=0 cycle={cycle} result=0 bytes=145 busy=0 vendor_1s_lut=0 vendor_partial_source=1",
        ])
    lines.extend(["[epaper] differential_skip identical_frame",
                  "[epaper] boot_diag pattern=6 official=0 cycle=50 result=0 bytes=0 busy=0 vendor_1s_lut=0 vendor_partial_source=1"])
    if mutations.get("missing_completion"):
        del lines[4]
    if mutations.get("third_refresh"):
        lines.insert(5, f"[epaper] refresh mode=differential profile={PROFILE} control=0xFF activation_command=0x20 activate=1 complete=1 elapsed_ms=100")
    if mutations.get("forbidden_0x26"):
        lines.insert(4, "[epaper] ram_write command=0x26 bytes=22")
    if mutations.get("forbidden_0x21"):
        lines.insert(4, "[epaper] command=0x21 data=0x00")
    if mutations.get("forbidden_0x37"):
        lines.insert(4, "[epaper] command=0x37 data=00")
    if mutations.get("mixed_region"):
        lines[2] = lines[2].replace("mixed_transition=0", "mixed_transition=1")
    if mutations.get("predicate_false"):
        lines[2] = lines[2].replace("predicate_verified=1", "predicate_verified=0")
    if mutations.get("fallback"):
        lines[1] = lines[1].replace("no_fallback=1", "no_fallback=0")
    if mutations.get("over_limit"):
        lines[1] = lines[1].replace("over_limit=0", "over_limit=1")
    if mutations.get("wrong_order"):
        lines[4], lines[7] = lines[7], lines[4]
    if mutations.get("timeout"):
        lines[4] = lines[4].replace("elapsed_ms=447", "elapsed_ms=701")
    return "\n".join(lines) + "\n"


def self_test() -> int:
    cases = [("positive", {}, True), ("missing_completion", {"missing_completion": True}, False),
             ("third_refresh", {"third_refresh": True}, False), ("forbidden_0x26", {"forbidden_0x26": True}, False),
             ("forbidden_0x21", {"forbidden_0x21": True}, False), ("forbidden_0x37", {"forbidden_0x37": True}, False),
             ("mixed_region", {"mixed_region": True}, False), ("predicate_false", {"predicate_false": True}, False),
             ("fallback", {"fallback": True}, False), ("over_limit", {"over_limit": True}, False),
             ("wrong_order", {"wrong_order": True}, False), ("timeout", {"timeout": True}, False)]
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        static = root / "static.json"
        static.write_text(json.dumps({"status": EXPECTED_STATIC}), encoding="utf-8")
        for name, mutations, expected in cases:
            log = root / f"{name}.log"
            log.write_text(fixture(**mutations), encoding="utf-8")
            passed = evaluate(log, static)["status"] == PASS_STATUS
            if passed != expected:
                print(f"SELF_TEST_FAIL: {name} expected={expected} actual={passed}", file=sys.stderr)
                return 1
    print("PASS: added-first old-cleanup trace parser self-test")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--static", type=pathlib.Path, default=STATIC)
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.log is None:
        parser.error("--log is required unless --self-test is used")
    try:
        report = evaluate(args.log, args.static)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: trace parsing failed: {error}", file=sys.stderr)
        return 1
    output = args.out if args.out.is_absolute() else ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: {rel(output)}")
    return 0 if report["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
