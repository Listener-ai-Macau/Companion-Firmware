#!/usr/bin/env python3
"""Verify the old/new RAM A/B trace without accepting a waveform change."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC_DEFAULT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-old-new-ram-static-20260720.json"
SCHEMA = "companion.wb55.gdey0154d67_t03.vendor_partial_old_new_ram_log.v1"
STATIC_SCHEMA = "companion.wb55.gdey0154d67_t03.vendor_partial_old_new_ram_static.v1"
STATIC_PASS = "PASS_STATIC_OWNER_AUTHORIZED_VENDOR_PARTIAL_OLD_NEW_RAM_AB"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_static(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    report = json.loads(raw.decode("utf-8-sig"))
    if report.get("schema_id") != STATIC_SCHEMA or report.get("status") != STATIC_PASS:
        raise ValueError("old/new RAM static contract is not passed")
    return {"path": rel(path), "sha256": hashlib.sha256(raw).hexdigest().upper(), "status": report["status"]}


def evaluate(text: str, log_path: str, static: dict[str, Any]) -> dict[str, Any]:
    end = r"\[epaper\] boot_diag pattern=4 official=0 cycle=6 result=0 bytes=\d+ busy=0 vendor_1s_lut=0 vendor_partial_source=1"
    match = re.search(r"\[epaper\] policy requested=1 selected=full reason=0 partial_count=0 limit=255 baseline=0(?P<body>.*?)" + end, text, re.DOTALL)
    scoped = match.group(0) if match else ""
    phases = [tuple(map(int, row)) for row in re.findall(r"ball_motion_slow phase=(\d+) segment=(\d+) fraction=(\d+)", scoped)]
    cycles = [tuple(map(int, row)) for row in re.findall(r"boot_diag pattern=4 official=0 cycle=(\d+) result=(\d+) bytes=(\d+) busy=(\d+) vendor_1s_lut=(\d+) vendor_partial_source=(\d+)", scoped)]
    batches = []
    for row in re.finditer(r"vendor_partial_source multi_region count=(\d+) total_bytes=(\d+)(?P<body>.*?)refresh mode=differential profile=good_display_vendor_partial_old_new_ram_ab control=0xFF ", scoped, re.DOTALL):
        indices = [tuple(map(int, item)) for item in re.findall(r"multi_region index=(\d+) x_byte=(\d+)\.\.(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) window=(\d+) write_0x24=(\d+) old_0x26_new_0x24=(\d+) write_0x26=(\d+)", row.group("body"))]
        batches.append((int(row.group(1)), int(row.group(2)), indices))
    refreshes = [int(value) for value in re.findall(r"refresh mode=differential profile=good_display_vendor_partial_old_new_ram_ab control=0xFF .*?activation_command=0x20 activate=1 complete=1 elapsed_ms=(\d+)", scoped)]
    transfers = [int(value) for value in re.findall(r"timing mode=differential .*? bytes=(\d+) data_planes=2 spi=software_vendor_edges", scoped)]
    checks = {
        "single_boot": text.count("[boot] Companion NUCLEO-WB55RG bringup") == 1,
        "static_contract_bound": static.get("status") == STATIC_PASS,
        "source_basemap_remains_two_5000_byte_planes": scoped.count("full_write_profile=good_display_vendor_partial_basemap_0x24_then_0x26") == 1 and scoped.count("bytes=5000 data_planes=2 spi=software_vendor_edges") == 1,
        "six_ordered_slow_positions": phases == [(0, 0, 0), (1, 0, 1), (2, 0, 2), (3, 0, 3), (4, 0, 4), (5, 0, 5)],
        "five_partial_updates_keep_source_control_busy_and_two_planes": len(refreshes) == 5 and all(value <= 5000 for value in refreshes) and len(transfers) == 5 and all(0 < value <= 567 for value in transfers),
        "each_partial_writes_previous_0x26_before_current_0x24": len(batches) == 5 and all(count in (1, 2) and total == sum(item[5] for item in indices) and all(item[6] == 1 and item[7] == 1 and item[8] == 1 and item[9] == 1 for item in indices) for count, total, indices in batches),
        "baseline_then_five_successful_two_plane_cycles": len(cycles) == 6 and cycles[0] == (1, 0, 10000, 0, 0, 1) and all(cycle == number and result == 0 and 0 < bytes_written <= 1134 and busy == 0 and lut == 0 and source == 1 for number, (cycle, result, bytes_written, busy, lut, source) in enumerate(cycles[1:], start=2)),
        "no_panel_error": "[epaper] error=" not in scoped,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {"schema_id": SCHEMA, "status": "PASS_MACHINE_VENDOR_PARTIAL_OLD_NEW_RAM_TRACE" if not failures else "NO_GO_INCOMPLETE_VENDOR_PARTIAL_OLD_NEW_RAM_TRACE", "claim_scope": "old/new RAM A/B trace only; no residue, temperature or production claim", "log": log_path, "checks": checks, "failures": failures, "slow_phases": phases, "cycles": cycles, "region_batches": batches, "region_refresh_elapsed_ms": refreshes, "region_transfer_bytes_per_plane": transfers, "diagnostic_scope_found": match is not None, "static_contract": static}


def synthetic_log() -> str:
    lines = ["[boot] Companion NUCLEO-WB55RG bringup", "[epaper] policy requested=1 selected=full reason=0 partial_count=0 limit=255 baseline=0", "[epaper] ball_motion_slow phase=0 segment=0 fraction=0 center=100,100 radius=10", "[epaper] full_write_profile=good_display_vendor_partial_basemap_0x24_then_0x26", "[epaper] timing mode=full prepare_ms=1 setup_ms=1 transfer_before_waveform_ms=1 transfer_after_waveform_ms=0 bytes=5000 data_planes=2 spi=software_vendor_edges", "[epaper] boot_diag pattern=4 official=0 cycle=1 result=0 bytes=10000 busy=0 vendor_1s_lut=0 vendor_partial_source=1"]
    for cycle in range(2, 7):
        phase = cycle - 1
        lines += [f"[epaper] ball_motion_slow phase={phase} segment=0 fraction={phase} center=100,100 radius=10", "[epaper] vendor_partial_source multi_region count=1 total_bytes=126", "[epaper] vendor_partial_source multi_region index=0 x_byte=10..12 y=90..131 bytes=126 window=1 write_0x24=1 old_0x26_new_0x24=1 write_0x26=1", f"[epaper] refresh mode=differential profile=good_display_vendor_partial_old_new_ram_ab control=0xFF expected_visible_flicker=none activation_count={cycle} busy=0 update=1 activation_command=0x20 activate=1 complete=1 elapsed_ms=401", "[epaper] timing mode=differential prepare_ms=1 setup_ms=1 transfer_before_waveform_ms=1 transfer_after_waveform_ms=0 bytes=126 data_planes=2 spi=software_vendor_edges", f"[epaper] boot_diag pattern=4 official=0 cycle={cycle} result=0 bytes=252 busy=0 vendor_1s_lut=0 vendor_partial_source=1"]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--static-contract", type=pathlib.Path, default=STATIC_DEFAULT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        result = evaluate(synthetic_log(), "self-test", {"status": STATIC_PASS})
        print("PASS: old/new RAM trace parser self-test" if result["status"] == "PASS_MACHINE_VENDOR_PARTIAL_OLD_NEW_RAM_TRACE" else "FAIL: old/new RAM trace parser self-test", file=sys.stderr if result["failures"] else sys.stdout)
        return 0 if not result["failures"] else 1
    if args.log is None or args.out is None:
        parser.error("--log and --out are required outside --self-test")
    try:
        static = load_static(args.static_contract if args.static_contract.is_absolute() else ROOT / args.static_contract)
        path = args.log if args.log.is_absolute() else ROOT / args.log
        raw = path.read_bytes()
        report = evaluate(raw.decode("utf-8", errors="replace"), rel(path), static)
        report["log_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: cannot parse old/new RAM trace: {error}", file=sys.stderr)
        return 1
    output = args.out if args.out.is_absolute() else ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: old/new RAM trace -> {rel(output)}")
    return 0 if report["status"] == "PASS_MACHINE_VENDOR_PARTIAL_OLD_NEW_RAM_TRACE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
