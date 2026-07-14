#!/usr/bin/env python3
"""Verify one reset-bounded WB55 SSD1681 official full diagnostic log."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATTERN_IDS = {"white": 1, "black": 2}
SCHEMA_ID = "companion.wb55.ssd1681_official_full_log.v1"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def evaluate(text: str, pattern: str, log_path: str) -> dict[str, Any]:
    pattern_id = PATTERN_IDS[pattern]
    checks = {
        "single_boot": text.count("[boot] Companion NUCLEO-WB55RG bringup") == 1,
        "expected_pattern_marker": re.search(
            rf"\[epaper\] boot_diag pattern={pattern_id} official=1 cycle=1 result=0 bytes=5000 busy=0",
            text,
        )
        is not None,
        "official_current_plane_only": "[epaper] full_write_profile=good_display_official_0x24_only" in text,
        "soft_reset_busy_asserted": re.search(
            r"\[epaper\] controller_init=1 soft_reset mode=full busy=1 pre=1 command=1",
            text,
        )
        is not None,
        "full_window_5000_bytes": re.search(
            r"\[epaper\] window x_byte=0\.\.24 y=0\.\.199 bytes=5000 changed=1",
            text,
        )
        is not None,
        "refresh_completed": re.search(
            r"\[epaper\] refresh mode=full .*control=0xF7 .*complete=1 elapsed_ms=\d+",
            text,
        )
        is not None,
        "single_data_plane": re.search(
            r"\[epaper\] timing mode=full .*bytes=5000 data_planes=1 spi=software_vendor_edges",
            text,
        )
        is not None,
        "policy_committed": "[epaper] policy_commit mode=full ok=1" in text,
        "no_panel_error_marker": "[epaper] error=" not in text,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_DIGITAL_ONLY" if not failures else "NO_GO_INCOMPLETE_DIAGNOSTIC_LOG",
        "claim_scope": "serial_log_digital_path_only_no_visual_or_voltage_claim",
        "pattern": pattern,
        "pattern_id": pattern_id,
        "log": log_path,
        "checks": checks,
        "failures": failures,
        "operator_gate": (
            "Machine PASS proves the selected one-plane command/BUSY trace only. "
            "The operator must still confirm a deterministic visible frame after FTS02 replacement."
        ),
    }


def synthetic_log(pattern_id: int, busy: int = 1) -> str:
    return "\n".join(
        [
            "[boot] Companion NUCLEO-WB55RG bringup",
            "[epaper] full_write_profile=good_display_official_0x24_only",
            f"[epaper] controller_init=1 soft_reset mode=full busy={busy} pre=1 command=1",
            "[epaper] window x_byte=0..24 y=0..199 bytes=5000 changed=1",
            "[epaper] refresh mode=full profile=default control=0xF7 expected_visible_flicker=multiple activation_count=1 busy=0 update=1 activate=1 complete=1 elapsed_ms=1297",
            "[epaper] timing mode=full prepare_ms=7 setup_ms=46 transfer_before_waveform_ms=56 transfer_after_waveform_ms=0 bytes=5000 data_planes=1 spi=software_vendor_edges",
            "[epaper] policy_commit mode=full ok=1 partial_count=0 baseline=1",
            f"[epaper] boot_diag pattern={pattern_id} official=1 cycle=1 result=0 bytes=5000 busy=0",
        ]
    )


def run_self_test() -> list[str]:
    errors: list[str] = []
    if evaluate(synthetic_log(1), "white", "selftest-white")["status"] != "PASS_MACHINE_DIGITAL_ONLY":
        errors.append("white synthetic log must pass")
    if evaluate(synthetic_log(2), "black", "selftest-black")["status"] != "PASS_MACHINE_DIGITAL_ONLY":
        errors.append("black synthetic log must pass")
    if evaluate(synthetic_log(2), "white", "selftest-wrong-pattern")["status"] == "PASS_MACHINE_DIGITAL_ONLY":
        errors.append("wrong pattern must fail")
    if evaluate(synthetic_log(1, busy=0), "white", "selftest-missing-busy")["status"] == "PASS_MACHINE_DIGITAL_ONLY":
        errors.append("missing BUSY assertion must fail")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", choices=sorted(PATTERN_IDS))
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        errors = run_self_test()
        if errors:
            print("FAIL: official full diagnostic parser self-test failed:", file=sys.stderr)
            for error in errors:
                print(f" - {error}", file=sys.stderr)
            return 1
        print("PASS: official full diagnostic parser self-test")
        return 0

    if not args.pattern or args.log is None or args.out is None:
        parser.error("--pattern, --log, and --out are required outside --self-test")
    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    if not log_path.is_file():
        print(f"FAIL: missing diagnostic log {rel(log_path)}", file=sys.stderr)
        return 1

    raw = log_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    report = evaluate(text, args.pattern, rel(log_path))
    report["log_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if report["status"] != "PASS_MACHINE_DIGITAL_ONLY":
        print(f"FAIL: {args.pattern} official full diagnostic log incomplete -> {rel(out_path)}", file=sys.stderr)
        return 1
    print(f"PASS: {args.pattern} official full diagnostic digital trace -> {rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
