#!/usr/bin/env python3
"""Verify the production-off vendor partial cleanup/draw hardware trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC_DEFAULT = ROOT / (
    "docs/validation/companion-gdey0154d67-t03-vendor-partial-cleanup-draw-static-20260720.json"
)
SUPPLIER_SHA256 = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_cleanup_draw_runtime.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative(path)} is not a JSON object")
    return value


def after_last_boot(log: str) -> str:
    marker = "[boot] Companion NUCLEO-WB55RG bringup"
    index = log.rfind(marker)
    scoped = log[index:] if index >= 0 else ""
    # The diagnostic intentionally ends before the normal application takes
    # ownership. Its subsequent full render is outside the local-motion trace.
    terminator = "[screen-assets] policy="
    end = scoped.find(terminator)
    return scoped[:end] if end >= 0 else scoped


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=pathlib.Path)
    parser.add_argument("--static", type=pathlib.Path, default=STATIC_DEFAULT)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--expected-partials", type=int, default=48)
    args = parser.parse_args(argv)

    failures: list[str] = []
    if not args.log.is_file():
        failures.append("runtime_log_missing")
    if not args.static.is_file():
        failures.append("static_admission_artifact_missing")
    if failures:
        report: dict[str, Any] = {
            "schema_id": SCHEMA_ID,
            "status": "NO_GO_RUNTIME_INPUT_MISSING",
            "failures": failures,
        }
    else:
        static = load_json(args.static)
        log = args.log.read_text(encoding="utf-8", errors="replace")
        scoped = after_last_boot(log)
        baseline = re.findall(
            r"^\[epaper\] refresh mode=full profile=default control=0xF7 .*?"
            r"activation_command=0x20 activate=1 complete=1 elapsed_ms=(\d+)$",
            scoped,
            flags=re.MULTILINE,
        )
        full_writes = re.findall(
            r"^\[epaper\] window x_byte=0\.\.24 y=0\.\.199 bytes=5000 changed=1$",
            scoped,
            flags=re.MULTILINE,
        )
        full_timing = re.findall(
            r"^\[epaper\] timing mode=full .*?bytes=5000 data_planes=2 ",
            scoped,
            flags=re.MULTILINE,
        )
        cleanup_lines = re.findall(
            r"^\[epaper\] vendor_partial_cleanup_draw "
            r"source_sha256=([A-F0-9]{64}) window_bytes=(\d+) "
            r"cleanup_0x24_white=(\d) cleanup_control=0x([0-9A-F]{2}) cleanup_complete=(\d) "
            r"draw_reset_low_high_ms=(\d+)/(\d+) draw_0x24=(\d) "
            r"draw_control=0x([0-9A-F]{2}) draw_complete=(\d) "
            r"no_full_write=(\d) no_c7=(\d)$",
            scoped,
            flags=re.MULTILINE,
        )
        partial_refreshes = re.findall(
            r"^\[epaper\] refresh mode=differential "
            r"profile=good_display_vendor_partial_cleanup_draw control=0x([0-9A-F]{2}) "
            r".*?activation_command=0x20 activate=1 complete=(\d) elapsed_ms=(\d+)$",
            scoped,
            flags=re.MULTILINE,
        )
        timings = re.findall(
            r"^\[epaper\] timing mode=differential .*?bytes=(\d+) data_planes=(\d+) ",
            scoped,
            flags=re.MULTILINE,
        )
        boot_cycles = re.findall(
            r"^\[epaper\] boot_diag pattern=4 official=0 cycle=(\d+) result=(\d) bytes=(\d+) "
            r"busy=(\d) vendor_1s_lut=0 vendor_partial_source=1$",
            scoped,
            flags=re.MULTILINE,
        )

        checks = {
            "static_hardware_admission_passed": static.get("status")
            == "PASS_STATIC_PRODUCTION_OFF_VENDOR_PARTIAL_CLEANUP_DRAW"
            and static.get("machine_status") == "PASS_STATIC_HARDWARE_ADMITTED",
            "one_full_basemap_is_source_bound": len(baseline) == 1
            and len(full_writes) >= 1
            and len(full_timing) == 1,
            "all_expected_partial_frames_completed": len(cleanup_lines) == args.expected_partials
            and len(boot_cycles) >= args.expected_partials + 1,
            "all_cleanup_draw_lines_are_source_bound_local_and_complete": bool(cleanup_lines)
            and all(
                source == SUPPLIER_SHA256
                and 0 < int(window_bytes) < 5000
                and cleanup_written == "1"
                and cleanup_control == "FF"
                and cleanup_complete == "1"
                and reset_low == "10"
                and reset_high == "10"
                and draw_written == "1"
                and draw_control == "FF"
                and draw_complete == "1"
                and no_full_write == "1"
                and no_c7 == "1"
                for (
                    source,
                    window_bytes,
                    cleanup_written,
                    cleanup_control,
                    cleanup_complete,
                    reset_low,
                    reset_high,
                    draw_written,
                    draw_control,
                    draw_complete,
                    no_full_write,
                    no_c7,
                ) in cleanup_lines
            ),
            "exactly_two_busy_completed_0xff_activations_per_partial": len(partial_refreshes)
            == args.expected_partials * 2
            and all(control == "FF" and complete == "1" and int(elapsed) > 0
                    for control, complete, elapsed in partial_refreshes),
            "per_frame_local_transfer_reports_two_planes": len(timings) == args.expected_partials
            and all(0 < int(byte_count) < 5000 and int(plane_count) == 2
                    for byte_count, plane_count in timings),
            "diagnostic_scope_never_emits_c7": "control=0xC7" not in scoped,
            "machine_boot_cycles_report_success": len(boot_cycles) >= args.expected_partials + 1
            and all(result == "0" and busy == "0" for _, result, _, busy in boot_cycles),
        }
        failures = [name for name, passed in checks.items() if not passed]
        report = {
            "schema_id": SCHEMA_ID,
            "status": "PASS_MACHINE_CLEANUP_DRAW_TRACE"
            if not failures
            else "NO_GO_MACHINE_CLEANUP_DRAW_TRACE",
            "claim_scope": "machine transport evidence only; local optical residue requires operator review",
            "checks": checks,
            "failures": failures,
            "source": {
                "runtime_log": {"path": relative(args.log), "sha256": digest(args.log)},
                "static_admission": {"path": relative(args.static), "sha256": digest(args.static)},
                "supplier_epaper_c_sha256": SUPPLIER_SHA256,
            },
            "observed": {
                "expected_partial_frames": args.expected_partials,
                "full_basemap_count": len(baseline),
                "full_basemap_elapsed_ms": [int(value) for value in baseline],
                "cleanup_draw_frame_count": len(cleanup_lines),
                "partial_activation_count": len(partial_refreshes),
                "partial_elapsed_ms": [int(value[2]) for value in partial_refreshes],
                "local_window_bytes": [int(value[1]) for value in cleanup_lines],
                "local_timing_bytes": [int(value[0]) for value in timings],
                "boot_cycle_count": len(boot_cycles),
            },
            "required_next_boundary": "Flash the separately built operator loop and record optical result with canonical aiw operator-prompt; this trace cannot establish no-residue visually.",
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: cleanup/draw runtime trace -> {relative(args.out)}")
    return 0 if report["status"] == "PASS_MACHINE_CLEANUP_DRAW_TRACE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
