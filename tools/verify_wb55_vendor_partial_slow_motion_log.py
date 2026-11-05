#!/usr/bin/env python3
"""Verify a slow-position source-partial baseline-plus-region trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC_DEFAULT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-slow-motion-static-20260720.json"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_slow_motion_log.v1"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_static(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    report = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(report, dict):
        raise ValueError("static contract is not a JSON object")
    if report.get("schema_id") != "companion.wb55.gdey0154d67_t03.vendor_partial_slow_motion_static.v1":
        raise ValueError("static contract schema mismatch")
    if report.get("status") != "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_SLOW_MOTION":
        raise ValueError("static contract is not passed")
    maximum = report.get("accepted_single_region_comparator", {}).get("maximum_accepted_region_bytes")
    if not isinstance(maximum, int) or maximum <= 0:
        raise ValueError("static contract has no accepted region-byte maximum")
    return {
        "path": rel(path),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "status": report["status"],
        "maximum_accepted_region_bytes": maximum,
    }


def evaluate(text: str, log_path: str, static: dict[str, Any]) -> dict[str, Any]:
    diagnostic_match = re.search(
        r"\[epaper\] policy requested=1 selected=full reason=0 partial_count=0 limit=255 baseline=0"
        r"(?P<trace>.*?)"
        r"\[epaper\] boot_diag pattern=4 official=0 cycle=6 result=0 bytes=\d+ busy=0 vendor_1s_lut=0 vendor_partial_source=1",
        text,
        flags=re.DOTALL,
    )
    scoped = diagnostic_match.group(0) if diagnostic_match is not None else ""
    phases = [
        tuple(int(value) for value in match)
        for match in re.findall(
            r"\[epaper\] ball_motion_slow phase=(\d+) segment=(\d+) fraction=(\d+) center=", scoped
        )
    ]
    cycles = [
        tuple(int(value) for value in match)
        for match in re.findall(
            r"\[epaper\] boot_diag pattern=4 official=0 cycle=(\d+) result=(\d+) bytes=(\d+) busy=(\d+) vendor_1s_lut=(\d+) vendor_partial_source=(\d+)",
            scoped,
        )
    ]
    region_timings = [
        int(value)
        for value in re.findall(
            r"\[epaper\] timing mode=differential .*? bytes=(\d+) data_planes=1 spi=software_vendor_edges",
            scoped,
        )
    ]
    region_elapsed = [
        int(value)
        for value in re.findall(
            r"\[epaper\] refresh mode=differential profile=good_display_vendor_partial_source control=0xFF "
            r".*?activation_command=0x20 activate=1 complete=1 elapsed_ms=(\d+)",
            scoped,
        )
    ]
    region_batches: list[dict[str, Any]] = []
    for match in re.finditer(
        r"\[epaper\] vendor_partial_source multi_region count=(\d+) total_bytes=(\d+)"
        r"(?P<body>.*?)"
        r"\[epaper\] refresh mode=differential profile=good_display_vendor_partial_source control=0xFF ",
        scoped,
        flags=re.DOTALL,
    ):
        index_rows = [
            tuple(int(value) for value in row)
            for row in re.findall(
                r"multi_region index=(\d+) x_byte=(\d+)\.\.(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) window=(\d+) write_0x24=(\d+)",
                match.group("body"),
            )
        ]
        region_batches.append(
            {
                "count": int(match.group(1)),
                "total_bytes": int(match.group(2)),
                "indices": index_rows,
            }
        )
    maximum = static["maximum_accepted_region_bytes"]
    checks = {
        "single_boot": text.count("[boot] Companion NUCLEO-WB55RG bringup") == 1,
        "static_contract_bound": static.get("status")
        == "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_SLOW_MOTION",
        "source_basemap_reset_and_two_5000_byte_planes_are_recorded": re.search(
            r"\[epaper\] vendor_partial_source basemap_reset low_ms=100 high_ms=100 busy=\d+", scoped
        )
        is not None
        and scoped.count("[epaper] full_write_profile=good_display_vendor_partial_basemap_0x24_then_0x26")
        == 1
        and scoped.count("refresh mode=full profile=default control=0xF7") == 1
        and scoped.count("bytes=5000 data_planes=2 spi=software_vendor_edges") == 1,
        "six_ordered_slow_intermediate_positions_are_run": phases == [
            (0, 0, 0),
            (1, 0, 1),
            (2, 0, 2),
            (3, 0, 3),
            (4, 0, 4),
            (5, 0, 5),
        ],
        "each_later_frame_uses_one_10ms_reset_one_ff_20_busy": scoped.count(
            "[epaper] vendor_partial_source region_reset low_ms=10 high_ms=10"
        )
        == 5
        and len(region_elapsed) == 5
        and all(value <= 5000 for value in region_elapsed)
        and scoped.count("profile=good_display_vendor_partial_source control=0xFF") == 5,
        "each_later_frame_has_one_or_two_successful_0x24_regions_below_accepted_limit": len(region_batches)
        == 5
        and all(
            1 <= batch["count"] <= 2
            and len(batch["indices"]) == batch["count"]
            and batch["total_bytes"] == sum(row[5] for row in batch["indices"])
            and 0 < batch["total_bytes"] <= maximum
            and all(row[6] == 1 and row[7] == 1 for row in batch["indices"])
            for batch in region_batches
        ),
        "all_five_partial_transfer_counts_are_below_accepted_single_region_maximum": len(region_timings)
        == 5
        and all(0 < value <= maximum for value in region_timings),
        "baseline_then_five_successful_slow_partial_cycles": len(cycles) == 6
        and cycles[0] == (1, 0, 10000, 0, 0, 1)
        and all(
            cycle == index
            and result == 0
            and 0 < bytes_written <= maximum
            and busy == 0
            and vendor_lut == 0
            and vendor_partial == 1
            for index, (cycle, result, bytes_written, busy, vendor_lut, vendor_partial) in enumerate(cycles[1:], start=2)
        ),
        "no_panel_error_marker": "[epaper] error=" not in scoped,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_VENDOR_PARTIAL_SLOW_MOTION_TRACE" if not failures else "NO_GO_INCOMPLETE_VENDOR_PARTIAL_SLOW_MOTION_TRACE",
        "claim_scope": "source-bound slow-position digital trace only; no ghosting, temperature or production claim",
        "log": log_path,
        "checks": checks,
        "failures": failures,
        "slow_phases": phases,
        "cycles": cycles,
        "region_batches": region_batches,
        "region_transfer_bytes": region_timings,
        "region_refresh_elapsed_ms": region_elapsed,
        "maximum_accepted_region_bytes": maximum,
        "diagnostic_scope_found": diagnostic_match is not None,
        "static_contract": static,
    }


def synthetic_log() -> str:
    lines = [
        "[boot] Companion NUCLEO-WB55RG bringup",
        "[epaper] policy requested=1 selected=full reason=0 partial_count=0 limit=255 baseline=0",
        "[epaper] ball_motion_slow phase=0 segment=0 fraction=0 center=100,100 radius=10",
        "[epaper] vendor_partial_source basemap_reset low_ms=100 high_ms=100 busy=0",
        "[epaper] full_write_profile=good_display_vendor_partial_basemap_0x24_then_0x26",
        "[epaper] refresh mode=full profile=default control=0xF7 expected_visible_flicker=multiple activation_count=1 busy=0 update=1 activation_command=0x20 activate=1 complete=1 elapsed_ms=1200",
        "[epaper] timing mode=full prepare_ms=5 setup_ms=220 transfer_before_waveform_ms=55 transfer_after_waveform_ms=0 bytes=5000 data_planes=2 spi=software_vendor_edges",
        "[epaper] boot_diag pattern=4 official=0 cycle=1 result=0 bytes=10000 busy=0 vendor_1s_lut=0 vendor_partial_source=1",
    ]
    for cycle in range(2, 7):
        phase = cycle - 1
        lines.extend(
            [
                "[epaper] policy requested=2 selected=differential reason=1 partial_count=%d limit=255 baseline=1" % (cycle - 2),
                "[epaper] ball_motion_slow phase=%d segment=0 fraction=%d center=100,100 radius=10" % (phase, phase),
                "[epaper] vendor_partial_source region_reset low_ms=10 high_ms=10 busy=0",
                "[epaper] vendor_partial_source multi_region count=1 total_bytes=126",
                "[epaper] vendor_partial_source multi_region index=0 x_byte=10..12 y=90..131 bytes=126 window=1 write_0x24=1",
                "[epaper] refresh mode=differential profile=good_display_vendor_partial_source control=0xFF expected_visible_flicker=none activation_count=%d busy=0 update=1 activation_command=0x20 activate=1 complete=1 elapsed_ms=401" % cycle,
                "[epaper] timing mode=differential prepare_ms=5 setup_ms=20 transfer_before_waveform_ms=7 transfer_after_waveform_ms=0 bytes=126 data_planes=1 spi=software_vendor_edges",
                "[epaper] boot_diag pattern=4 official=0 cycle=%d result=0 bytes=126 busy=0 vendor_1s_lut=0 vendor_partial_source=1" % cycle,
            ]
        )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--static-contract", type=pathlib.Path, default=STATIC_DEFAULT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        static = {
            "status": "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_SLOW_MOTION",
            "maximum_accepted_region_bytes": 567,
        }
        passed = evaluate(synthetic_log(), "self-test", static)
        if passed["status"] != "PASS_MACHINE_VENDOR_PARTIAL_SLOW_MOTION_TRACE":
            print("FAIL: vendor partial slow-motion trace parser self-test", file=sys.stderr)
            return 1
        failed = evaluate(synthetic_log().replace("total_bytes=126", "total_bytes=568", 1), "bad-limit", static)
        if failed["status"] == "PASS_MACHINE_VENDOR_PARTIAL_SLOW_MOTION_TRACE":
            print("FAIL: over-limit region passed", file=sys.stderr)
            return 1
        print("PASS: vendor partial slow-motion trace parser self-test")
        return 0
    if args.log is None or args.out is None:
        parser.error("--log and --out are required outside --self-test")
    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    output = args.out if args.out.is_absolute() else ROOT / args.out
    static_path = args.static_contract if args.static_contract.is_absolute() else ROOT / args.static_contract
    try:
        static = load_static(static_path)
        raw = log_path.read_bytes()
        report = evaluate(raw.decode("utf-8", errors="replace"), rel(log_path), static)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: cannot parse vendor partial slow-motion trace: {error}", file=sys.stderr)
        return 1
    report["log_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: vendor partial slow-motion trace -> {rel(output)}")
    return 0 if report["status"] == "PASS_MACHINE_VENDOR_PARTIAL_SLOW_MOTION_TRACE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
