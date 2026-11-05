#!/usr/bin/env python3
"""Verify the bounded generic removed-black repair/current-union trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-removed-black-repair-current-union-static-20260720.json"
SUPPLIER_SHA256 = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_removed_black_repair_current_union_runtime.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--static", type=pathlib.Path, default=STATIC)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--expected-partials", type=int, default=48)
    args = parser.parse_args(argv)
    missing = [name for path, name in ((args.log, "runtime_log_missing"), (args.static, "static_gate_missing")) if not path.is_file()]
    if missing:
        report: dict[str, Any] = {"schema_id": SCHEMA_ID, "status": "NO_GO_RUNTIME_INPUT_MISSING", "failures": missing}
    else:
        static = json.loads(args.static.read_text(encoding="utf-8-sig"))
        log = args.log.read_text(encoding="utf-8", errors="replace")
        boot = log.rfind("[boot] Companion NUCLEO-WB55RG bringup")
        scoped = log[boot:] if boot >= 0 else ""
        end = scoped.find("[screen-assets] policy=")
        if end >= 0:
            scoped = scoped[:end]
        baseline = re.findall(r"^\[epaper\] refresh mode=full profile=default control=0xF7 .*?activation_command=0x20 activate=1 complete=1 elapsed_ms=(\d+)$", scoped, flags=re.MULTILINE)
        full_windows = re.findall(r"^\[epaper\] window x_byte=0\.\.24 y=0\.\.199 bytes=5000 changed=1$", scoped, flags=re.MULTILINE)
        traces = re.findall(r"^\[epaper\] vendor_partial_removed_black_repair_current_union source_sha256=([A-F0-9]{64}) repair_removed_black_window_bytes=(\d+) union_window_bytes=(\d+) repair_reset_low_high_ms=(\d+)/(\d+) repair_0x24_current=(\d) repair_control=0x([0-9A-F]{2}) repair_complete=(\d) union_reset_low_high_ms=(\d+)/(\d+) union_0x24_current=(\d) union_control=0x([0-9A-F]{2}) union_complete=(\d) no_old_or_current_union=(\d) no_full_write=(\d) no_c7=(\d)$", scoped, flags=re.MULTILINE)
        refreshes = re.findall(r"^\[epaper\] refresh mode=differential profile=good_display_vendor_partial_removed_black_repair_current_union control=0x([0-9A-F]{2}) .*?activation_command=0x20 activate=1 complete=(\d) elapsed_ms=(\d+)$", scoped, flags=re.MULTILINE)
        timings = re.findall(r"^\[epaper\] timing mode=differential .*?bytes=(\d+) data_planes=(\d+) ", scoped, flags=re.MULTILINE)
        cycles = re.findall(r"^\[epaper\] boot_diag pattern=4 official=0 cycle=(\d+) result=(\d) bytes=(\d+) busy=(\d) vendor_1s_lut=0 vendor_partial_source=1$", scoped, flags=re.MULTILINE)
        checks = {
            "static_gate_admits_hardware": static.get("status") == "PASS_STATIC_PRODUCTION_OFF_VENDOR_PARTIAL_REMOVED_BLACK_REPAIR_CURRENT_UNION" and static.get("machine_status") == "PASS_STATIC_HARDWARE_ADMITTED",
            "one_source_basemap": len(baseline) == 1 and len(full_windows) >= 1,
            "all_bounded_partial_frames_present": len(traces) == args.expected_partials and len(cycles) >= args.expected_partials + 1,
            "two_ordered_current_frame_source_passes": bool(traces) and all(
                source == SUPPLIER_SHA256 and 0 < int(repair_window) < 5000 and 0 < int(union_window) < 5000
                and repair_low == "10" and repair_high == "10" and repair_written == "1" and repair_control == "FF" and repair_complete == "1"
                and union_low == "10" and union_high == "10" and union_written == "1" and union_control == "FF" and union_complete == "1"
                and no_union == "1" and no_full == "1" and no_c7 == "1"
                for source, repair_window, union_window, repair_low, repair_high, repair_written, repair_control, repair_complete,
                    union_low, union_high, union_written, union_control, union_complete, no_union, no_full, no_c7 in traces),
            "exactly_two_busy_completed_0xff_activations_per_frame": len(refreshes) == args.expected_partials * 2 and all(control == "FF" and complete == "1" and int(elapsed) > 0 for control, complete, elapsed in refreshes),
            "local_transfer_reports_two_planes": len(timings) == args.expected_partials and all(0 < int(byte_count) < 5000 and int(planes) == 2 for byte_count, planes in timings),
            "no_c7_or_old_or_current_union_in_diagnostic_scope": "control=0xC7" not in scoped and "vendor_partial_draw_final" not in scoped,
            "all_boot_cycles_completed": len(cycles) >= args.expected_partials + 1 and all(result == "0" and busy == "0" for _, result, _, busy in cycles),
        }
        failures = [name for name, passed in checks.items() if not passed]
        report = {"schema_id": SCHEMA_ID, "status": "PASS_MACHINE_REMOVED_BLACK_REPAIR_CURRENT_UNION_TRACE" if not failures else "NO_GO_MACHINE_REMOVED_BLACK_REPAIR_CURRENT_UNION_TRACE", "claim_scope": "machine transport only; residual recurrence, leading-edge continuity and cleanliness require operator review", "checks": checks, "failures": failures, "source": {"runtime_log": {"path": relative(args.log), "sha256": digest(args.log)}, "static_gate": {"path": relative(args.static), "sha256": digest(args.static)}, "supplier_epaper_c_sha256": SUPPLIER_SHA256}, "observed": {"baseline_elapsed_ms": [int(value) for value in baseline], "partial_frame_count": len(traces), "partial_activation_count": len(refreshes), "partial_elapsed_ms": [int(value[2]) for value in refreshes], "repair_removed_black_window_bytes": [int(value[1]) for value in traces], "union_window_bytes": [int(value[2]) for value in traces]}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: removed-black repair/current-union runtime trace -> {relative(args.out)}")
    return 0 if report["status"] == "PASS_MACHINE_REMOVED_BLACK_REPAIR_CURRENT_UNION_TRACE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
