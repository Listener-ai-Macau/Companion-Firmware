#!/usr/bin/env python3
"""Bind an official White refresh trace to structured replacement-FPC rail evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_ID = "companion.wb55.official_full_rail_measurement.v1"
SOURCE_AUDIT_SCHEMA_ID = "companion.gdey0154d67_t03.vendor_1s_source_audit.v1"
BOOT_RE = re.compile(
    r"\[epaper\] boot_diag pattern=1 official=1 cycle=(?P<cycle>\d+) "
    r"result=0 bytes=5000 busy=0"
)
REFRESH_RE = re.compile(
    r"\[epaper\] refresh mode=full .*control=0xF7 .*activation_command=0x20 activate=1 .*complete=1 elapsed_ms=(?P<elapsed>\d+)"
)
TIMING_RE = re.compile(
    r"\[epaper\] timing mode=full .*bytes=5000 data_planes=1 "
    r"spi=software_vendor_edges"
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_source_audit(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        audit = json.loads(raw.decode("utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ValueError(f"source audit is not valid JSON: {error}") from error
    source_manifest = audit.get("source_manifest")
    critical = source_manifest.get("critical_sources", {}) if isinstance(source_manifest, dict) else {}
    command_evidence = audit.get("command_evidence", {})
    errors: list[str] = []
    if audit.get("schema_id") != SOURCE_AUDIT_SCHEMA_ID:
        errors.append("schema_id")
    if audit.get("machine_status") != "PASS_AUDIT_COMPLETE":
        errors.append("machine_status")
    if audit.get("promotion_status") != "NO_GO_PANEL_IDENTITY_UNPROVEN":
        errors.append("promotion_status")
    if command_evidence.get("production_lut_reference_absent") is not True:
        errors.append("production_lut_reference_absent")
    for key in ("epaper_c", "current_ssd1681_target"):
        entry = critical.get(key)
        if not isinstance(entry, dict) or not entry.get("sha256") or not entry.get("path"):
            errors.append(f"source_manifest.critical_sources.{key}")
            continue
        source_path = pathlib.Path(str(entry["path"]))
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        if not source_path.is_file() or hashlib.sha256(source_path.read_bytes()).hexdigest().upper() != entry["sha256"]:
            errors.append(f"source_manifest.critical_sources.{key}.sha256_drift")
    if errors:
        raise ValueError("source audit is not safe to bind: " + ", ".join(errors))
    return {
        "path": rel(path),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "vendor_epaper_c_sha256": critical["epaper_c"]["sha256"],
        "current_ssd1681_target_sha256": critical["current_ssd1681_target"]["sha256"],
        "machine_status": audit["machine_status"],
        "promotion_status": audit["promotion_status"],
        "production_lut_reference_absent": command_evidence["production_lut_reference_absent"],
    }


def evaluate(
    text: str,
    prevgl_min_v: float | None,
    prevgh_max_v: float | None,
    min_cycles: int,
    operator_selected: str,
    screen_observation: str,
    source_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cycles = [int(match["cycle"]) for match in BOOT_RE.finditer(text)]
    refresh_elapsed = [int(match["elapsed"]) for match in REFRESH_RE.finditer(text)]
    accepted_cycles = canonical_reset_bounded_cycle_run(cycles)
    measurement_available = prevgl_min_v is not None and prevgh_max_v is not None
    rails_established = bool(
        measurement_available and prevgl_min_v < 0.0 and prevgh_max_v > 3.3
    )
    checks = {
        "official_current_plane_profile": "[epaper] full_write_profile=good_display_official_0x24_only" in text,
        "official_current_plane_only": "[epaper] full_write_profile=good_display_official_0x24_only" in text,
        "required_white_cycles_completed": len(accepted_cycles) >= min_cycles,
        "every_observed_cycle_has_completed_f7_refresh": len(refresh_elapsed) >= min_cycles
        and all(elapsed <= 5000 for elapsed in refresh_elapsed),
        "refresh_within_5000_ms": len(refresh_elapsed) >= min_cycles
        and all(elapsed <= 5000 for elapsed in refresh_elapsed),
        "activation_0x20_sent": len(refresh_elapsed) >= min_cycles,
        "every_observed_cycle_transfers_one_5000_byte_plane": len(TIMING_RE.findall(text))
        >= min_cycles,
        "no_panel_error_marker": "[epaper] error=" not in text and "[epaper] fail " not in text,
        "operator_selected_pass": operator_selected == "通过",
        "screen_observation_declares_uniform_white": screen_observation == "uniform_white",
        "positive_and_negative_refresh_rails_established": rails_established,
        "rail_measurement_available": measurement_available,
        "source_audit_bound": source_audit is None or bool(source_audit),
    }
    failures = [name for name, passed in checks.items() if not passed]
    status = (
        "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE"
        if not failures
        else (
            "NO_GO_WHITE_RAIL_MEASUREMENT_UNAVAILABLE"
            if not measurement_available
            else (
                "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED"
                if not rails_established
                else "NO_GO_OFFICIAL_WHITE_RAIL_SESSION_INCOMPLETE"
            )
        )
    )
    return {
        "checks": checks,
        "failures": failures,
        "status": status,
        "observed_cycles": cycles,
        "accepted_reset_bounded_cycles": accepted_cycles,
        "refresh_elapsed_ms": refresh_elapsed,
        "measurement": {
            "available": measurement_available,
            "prevgl1_min_v": prevgl_min_v,
            "prevgh1_max_v": prevgh_max_v,
            "operator_selected": operator_selected,
            "screen_observation": screen_observation,
        },
        "source_audit": source_audit,
    }


def canonical_reset_bounded_cycle_run(cycles: list[int]) -> list[int]:
    """Return the longest intact 1..N run after a possible capture-startup record."""
    longest: list[int] = []
    for start, cycle in enumerate(cycles):
        if cycle != 1:
            continue
        candidate = [1]
        expected = 2
        for later in cycles[start + 1 :]:
            if later != expected:
                break
            candidate.append(later)
            expected += 1
        if len(candidate) > len(longest):
            longest = candidate
    return longest


def synthetic_log(cycles: int = 3, activation_command: str = "0x20") -> str:
    lines = ["[boot] Companion NUCLEO-WB55RG bringup"]
    for cycle in range(1, cycles + 1):
        lines.extend(
            [
                "[epaper] full_write_profile=good_display_official_0x24_only",
                "[epaper] refresh mode=full profile=default control=0xF7 "
                "expected_visible_flicker=multiple activation_count=1 busy=0 update=1 "
                f"activation_command={activation_command} activate=1 complete=1 elapsed_ms=1297",
                "[epaper] timing mode=full prepare_ms=7 setup_ms=46 transfer_before_waveform_ms=56 transfer_after_waveform_ms=0 bytes=5000 data_planes=1 spi=software_vendor_edges",
                f"[epaper] boot_diag pattern=1 official=1 cycle={cycle} result=0 bytes=5000 busy=0",
            ]
        )
    return "\n".join(lines)


def run_self_test() -> list[str]:
    errors: list[str] = []
    passing = evaluate(synthetic_log(), -7.1, 15.4, 3, "通过", "uniform_white")
    if passing["status"] != "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE":
        errors.append("established-rail synthetic session must pass")
    capture_startup_duplicate = evaluate(
        synthetic_log(1) + "\n" + synthetic_log(3),
        -7.1,
        15.4,
        3,
        "通过",
        "uniform_white",
    )
    if capture_startup_duplicate["status"] != "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE":
        errors.append("startup duplicate before reset-bounded 1..N run must pass")
    duplicate_mid_session = evaluate(
        synthetic_log(2) + "\n" + synthetic_log(2),
        -7.1,
        15.4,
        3,
        "通过",
        "uniform_white",
    )
    if duplicate_mid_session["status"] == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE":
        errors.append("duplicate inside a reset-bounded cycle run must not pass")
    low_rail = evaluate(synthetic_log(), 0.0042, 3.3, 3, "通过", "uniform_white")
    if low_rail["status"] != "NO_GO_REFRESH_VOLTAGE_NOT_ESTABLISHED":
        errors.append("non-negative PREVGL and 3.3 V PREVGH must be voltage NO_GO")
    short = evaluate(synthetic_log(2), -7.1, 15.4, 3, "通过", "uniform_white")
    if short["status"] == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE":
        errors.append("short measurement window must not pass")
    wrong_activation = evaluate(
        synthetic_log(activation_command="0x21"),
        -7.1,
        15.4,
        3,
        "通过",
        "uniform_white",
    )
    if wrong_activation["status"] == "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE":
        errors.append("non-0x20 activation command must not pass")
    unavailable = evaluate(synthetic_log(), None, None, 3, "跳过", "unknown_white")
    if unavailable["status"] != "NO_GO_WHITE_RAIL_MEASUREMENT_UNAVAILABLE":
        errors.append("missing rail measurement must remain a NO_GO artifact")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--log", type=pathlib.Path)
    parser.add_argument("--image", type=pathlib.Path)
    parser.add_argument("--prevgl-min-v", type=float)
    parser.add_argument("--prevgh-max-v", type=float)
    parser.add_argument("--measurement-unavailable", action="store_true")
    parser.add_argument("--operator-selected", choices=("通过", "失败", "跳过", "中止"))
    parser.add_argument(
        "--screen-observation",
        choices=("uniform_white", "not_uniform_white", "unknown_white"),
    )
    parser.add_argument("--operator-note", type=pathlib.Path)
    parser.add_argument("--source-audit", type=pathlib.Path)
    parser.add_argument("--min-cycles", type=int, default=3)
    parser.add_argument("--write", type=pathlib.Path)
    args = parser.parse_args(argv)

    if args.self_test:
        errors = run_self_test()
        if errors:
            print("FAIL: official full rail measurement parser self-test failed:", file=sys.stderr)
            for error in errors:
                print(f" - {error}", file=sys.stderr)
            return 1
        print("PASS: official full rail measurement parser self-test")
        return 0

    required = (
        args.log,
        args.image,
        args.operator_selected,
        args.screen_observation,
        args.operator_note,
        args.source_audit,
        args.write,
    )
    if any(value is None for value in required) or args.min_cycles < 1:
        parser.error("all session inputs and --write are required outside --self-test")
    if args.measurement_unavailable:
        if args.prevgl_min_v is not None or args.prevgh_max_v is not None:
            parser.error("--measurement-unavailable cannot be combined with rail values")
    elif args.prevgl_min_v is None or args.prevgh_max_v is None:
        parser.error("both rail values are required unless --measurement-unavailable is set")

    log_path = args.log if args.log.is_absolute() else ROOT / args.log
    image_path = args.image if args.image.is_absolute() else ROOT / args.image
    note_path = args.operator_note if args.operator_note.is_absolute() else ROOT / args.operator_note
    audit_path = args.source_audit if args.source_audit.is_absolute() else ROOT / args.source_audit
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    for path in (log_path, image_path, note_path, audit_path):
        if not path.is_file():
            parser.error(f"missing session input: {rel(path)}")
    try:
        source_audit = load_source_audit(audit_path)
    except ValueError as error:
        parser.error(str(error))
    result = evaluate(
        log_path.read_text(encoding="utf-8", errors="replace"),
        args.prevgl_min_v,
        args.prevgh_max_v,
        args.min_cycles,
        args.operator_selected,
        args.screen_observation,
        source_audit,
    )
    report = {
        "schema_id": SCHEMA_ID,
        "claim_scope": "official_white_digital_trace_plus_structured_operator_rail_measurement",
        "minimum_cycles": args.min_cycles,
        "log": {"path": rel(log_path), "sha256": digest(log_path)},
        "image": {"path": rel(image_path), "sha256": digest(image_path)},
        "operator_note": {"path": rel(note_path), "sha256": digest(note_path)},
        **result,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE":
        print(f"NO_GO: official White rail measurement -> {rel(destination)}", file=sys.stderr)
        return 1
    print(f"PASS: official White rail measurement -> {rel(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
