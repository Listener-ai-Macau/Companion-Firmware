#!/usr/bin/env python3
"""Verify a reset-bounded six-frame Good Display one-second LUT diagnostic trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC_DEFAULT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-diagnostic-static-20260720.json"
EXPECTED_LUT_SHA256 = "F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_1s_lut_diagnostic_log.v1"


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
    if report.get("schema_id") != "companion.wb55.gdey0154d67_t03.vendor_1s_lut_diagnostic_static.v1":
        raise ValueError("static contract schema mismatch")
    if report.get("status") != "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_1S_LUT":
        raise ValueError("static contract is not passed")
    return {
        "path": rel(path),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "status": report["status"],
        "supplier_lut_sha256": report.get("source", {}).get("supplier_lut_sha256"),
    }


def evaluate(text: str, log_path: str, static: dict[str, Any]) -> dict[str, Any]:
    diagnostic_match = re.search(
        r"\[epaper\] policy requested=1 selected=full reason=0 partial_count=0 limit=5 baseline=0"
        r"(?P<trace>.*?)"
        r"\[epaper\] boot_diag pattern=4 official=0 cycle=6 result=0 bytes=5000 busy=0 vendor_1s_lut=1",
        text,
        flags=re.DOTALL,
    )
    scoped = diagnostic_match.group(0) if diagnostic_match is not None else ""
    refresh_elapsed = [
        int(value)
        for value in re.findall(
            r"\[epaper\] refresh mode=full profile=good_display_1s_lut control=0xC7 .*activation_command=0x20 activate=1 complete=1 elapsed_ms=(\d+)",
            scoped,
        )
    ]
    cycles = [
        (int(cycle), int(result), int(bytes_written), int(busy), int(vendor))
        for cycle, result, bytes_written, busy, vendor in re.findall(
            r"\[epaper\] boot_diag pattern=4 official=0 cycle=(\d+) result=(\d+) bytes=(\d+) busy=(\d+) vendor_1s_lut=(\d+)",
            scoped,
        )
    ]
    steps = [int(value) for value in re.findall(r"\[epaper\] ball_motion step=(\d+) pose=", scoped)]
    checks = {
        "single_boot": text.count("[boot] Companion NUCLEO-WB55RG bringup") == 1,
        "static_contract_bound": static.get("supplier_lut_sha256") == EXPECTED_LUT_SHA256,
        "vendor_reset_is_recorded": re.search(
            r"\[epaper\] vendor_1s_lut reset low_ms=100 high_ms=100 busy=\d+", text
        )
        is not None,
        "soft_reset_and_window_are_recorded": re.search(
            r"\[epaper\] controller_init=1 soft_reset mode=full busy=\d+ pre=1 command=1", text
        )
        is not None
        and "[epaper] window x_byte=0..24 y=0..199 bytes=5000 changed=1" in text,
        "source_hash_and_lut_load_are_recorded": re.search(
            rf"\[epaper\] vendor_1s_lut profile=good_display_1s_lut sha256={EXPECTED_LUT_SHA256} "
            r"payload_bytes=153 tails=0x22,0x17,0x41,0xA8,0x32,0x58 loaded=1",
            scoped,
        )
        is not None,
        "one_current_plane_per_frame": scoped.count(
            "[epaper] full_write_profile=good_display_vendor_1s_lut_0x24_only"
        )
        == 6,
        "all_six_refreshes_activate_c7_20_and_return_busy_ready": len(refresh_elapsed) == 6
        and all(value <= 5000 for value in refresh_elapsed)
        and scoped.count("profile=good_display_1s_lut control=0xC7") == 6,
        "all_six_refreshes_report_one_5000_byte_plane": scoped.count(
            "bytes=5000 data_planes=1 spi=software_vendor_edges"
        )
        == 6,
        "six_distinct_marker_steps_are_run": steps == [0, 1, 2, 3, 4, 5],
        "six_successful_vendor_boot_cycles": cycles
        == [(1, 0, 5000, 0, 1), (2, 0, 5000, 0, 1), (3, 0, 5000, 0, 1),
            (4, 0, 5000, 0, 1), (5, 0, 5000, 0, 1), (6, 0, 5000, 0, 1)],
        "no_panel_error_marker": "[epaper] error=" not in scoped,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_VENDOR_1S_LUT_SIX_FRAME_TRACE" if not failures else "NO_GO_INCOMPLETE_VENDOR_1S_LUT_TRACE",
        "claim_scope": "source-bound six-frame digital trace only; no temperature or production claim",
        "log": log_path,
        "checks": checks,
        "failures": failures,
        "refresh_elapsed_ms": refresh_elapsed,
        "cycles": cycles,
        "marker_steps": steps,
        "diagnostic_scope_found": diagnostic_match is not None,
        "static_contract": static,
    }


def synthetic_log() -> str:
    lines = ["[boot] Companion NUCLEO-WB55RG bringup"]
    for cycle in range(1, 7):
        step = cycle - 1
        if cycle == 1:
            lines.append("[epaper] policy requested=1 selected=full reason=0 partial_count=0 limit=5 baseline=0")
        lines.extend(
            [
                "[epaper] ball_motion step=%d pose=marker radius=8" % step,
                "[epaper] vendor_1s_lut reset low_ms=100 high_ms=100 busy=0",
                "[epaper] controller_init=1 soft_reset mode=full busy=0 pre=1 command=1",
                "[epaper] vendor_1s_lut profile=good_display_1s_lut sha256=%s payload_bytes=153 tails=0x22,0x17,0x41,0xA8,0x32,0x58 loaded=1" % EXPECTED_LUT_SHA256,
                "[epaper] window x_byte=0..24 y=0..199 bytes=5000 changed=1",
                "[epaper] full_write_profile=good_display_vendor_1s_lut_0x24_only",
                "[epaper] refresh mode=full profile=good_display_1s_lut control=0xC7 expected_visible_flicker=single activation_count=%d busy=0 update=1 activation_command=0x20 activate=1 complete=1 elapsed_ms=1012" % cycle,
                "[epaper] timing mode=full prepare_ms=5 setup_ms=220 transfer_before_waveform_ms=55 transfer_after_waveform_ms=0 bytes=5000 data_planes=1 spi=software_vendor_edges",
                "[epaper] boot_diag pattern=4 official=0 cycle=%d result=0 bytes=5000 busy=0 vendor_1s_lut=1" % cycle,
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
        static = {"supplier_lut_sha256": EXPECTED_LUT_SHA256}
        if evaluate(synthetic_log(), "self-test", static)["status"] != "PASS_MACHINE_VENDOR_1S_LUT_SIX_FRAME_TRACE":
            print("FAIL: vendor one-second trace parser self-test", file=sys.stderr)
            return 1
        if evaluate(synthetic_log().replace("control=0xC7", "control=0xF7", 1), "bad-control", static)["status"] == "PASS_MACHINE_VENDOR_1S_LUT_SIX_FRAME_TRACE":
            print("FAIL: wrong update control passed", file=sys.stderr)
            return 1
        print("PASS: vendor one-second trace parser self-test")
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
        print(f"NO_GO: cannot parse vendor one-second trace: {error}", file=sys.stderr)
        return 1
    report["log_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: vendor one-second trace -> {rel(output)}")
    return 0 if report["status"] == "PASS_MACHINE_VENDOR_1S_LUT_SIX_FRAME_TRACE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
