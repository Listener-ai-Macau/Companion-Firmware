#!/usr/bin/env python3
"""Parse the bounded trace for the vendor disjoint current-stage diagnostic."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_STATIC = ROOT / (
    "docs/validation/"
    "companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-static-20260720.json"
)
EXPECTED_STATIC = "PASS_STATIC_SOURCE_EXACT_DISJOINT_CURRENT_STAGE_DEFAULT_OFF"
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_disjoint_current_stage_trace.v1"
EXPECTED_PROBE_RADIUS_PX = 12


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


def evaluate(log_path: pathlib.Path, static_path: pathlib.Path) -> dict[str, Any]:
    static = load_json(static_path)
    text = log_path.read_text(encoding="utf-8-sig", errors="replace")
    stage_lines = list(
        re.finditer(
            r"vendor_partial_disjoint_current_stage count=(\d+) total_bytes=(\d+) multi_smaller_than_union=(\d+)",
            text,
        )
    )
    region_lines = list(
        re.finditer(
            r"vendor_partial_disjoint_current_stage index=(\d+) x_byte=(\d+)\.\.(\d+) y=(\d+)\.\.(\d+) bytes=(\d+) window=(\d+) current_0x24=(\d+) no_0x26=1",
            text,
        )
    )
    completion_lines = list(
        re.finditer(
            r"vendor_partial_disjoint_current_stage source_sha256=([0-9A-F]+) staged_regions=(\d+) staged_bytes=(\d+) multi_smaller_than_union=(\d+) one_control=0xFF one_activation=0x20 no_0x26=1 no_c7=1 no_full_write=1",
            text,
        )
    )
    refresh_lines = list(
        re.finditer(
            r"refresh mode=differential profile=good_display_vendor_partial_disjoint_current_stage control=0xFF .*?activation_command=0x20 activate=(\d+) complete=(\d+) elapsed_ms=(\d+)",
            text,
        )
    )
    boot_lines = list(re.finditer(r"boot_diag pattern=6 .*? cycle=(\d+) result=(\d+) bytes=(\d+)", text))
    probe_lines = list(
        re.finditer(
            r"disjoint_component_probe phase=(\d+) segment=(\d+) fraction=(\d+) center=(\d+),(\d+) radius=(\d+)",
            text,
        )
    )
    identical_skip_lines = list(re.finditer(r"differential_skip identical_frame", text))
    partial_stages = stage_lines
    checks = {
        "static_contract_passed": static.get("status") == EXPECTED_STATIC,
        "one_full_baseline_plus_48_partial_steps_and_one_identical_frame": len(boot_lines) == 50 and len(partial_stages) == 48,
        "all_50_frames_use_the_owner_authorized_five_anchor_12px_probe": len(probe_lines) == 50
        and all(
            int(match.group(6)) == EXPECTED_PROBE_RADIUS_PX
            and 0 <= int(match.group(4)) <= 199
            and 0 <= int(match.group(5)) <= 199
            and int(match.group(2)) == int(match.group(1)) // 8
            and int(match.group(3)) == int(match.group(1)) % 8
            for match in probe_lines
        ),
        "probe_traverses_the_42px_five_anchor_orbit": len(probe_lines) == 50
        and min(int(match.group(4)) for match in probe_lines) == 58
        and max(int(match.group(4)) for match in probe_lines) == 142
        and min(int(match.group(5)) for match in probe_lines) == 58
        and max(int(match.group(5)) for match in probe_lines) == 142,
        "each_partial_has_one_to_five_disjoint_current_regions": len(partial_stages) == 48
        and all(
            1 <= int(match.group(1)) <= 5
            and (match.group(3) != "1" or int(match.group(1)) > 1)
            for match in partial_stages
        ),
        "all_regions_are_current_0x24_only_and_bounded": len(region_lines)
        == sum(int(match.group(1)) for match in partial_stages)
        and all(
            match.group(7) == "1"
            and match.group(8) == "1"
            and 0 <= int(match.group(1)) <= 4
            and int(match.group(2)) <= int(match.group(3)) < 25
            and int(match.group(4)) <= int(match.group(5)) < 200
            for match in region_lines
        ),
        "each_partial_has_one_source_ff_20_busy_completion": len(completion_lines) == 48
        and len(refresh_lines) == 48
        and all(
            1 <= int(match.group(2)) <= 5
            and (match.group(4) != "1" or int(match.group(2)) > 1)
            for match in completion_lines
        )
        and all(match.group(1) == "1" and match.group(2) == "1" for match in refresh_lines),
        "identical_frame_has_zero_payload_and_zero_activation": len(identical_skip_lines) == 1
        and len(boot_lines) == 50
        and boot_lines[-1].group(1) == "50"
        and boot_lines[-1].group(2) == "0"
        and boot_lines[-1].group(3) == "0"
        and len(refresh_lines) == 48,
        "no_panel_error_marker": "result=4" not in text and "TRANSPORT_ERROR" not in text,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_MACHINE_VENDOR_PARTIAL_DISJOINT_CURRENT_STAGE_TRACE" if not failures else "NO_GO_INCOMPLETE_VENDOR_PARTIAL_DISJOINT_CURRENT_STAGE_TRACE",
        "claim_scope": "bounded machine command trace only; no visual-residue, temperature, or production claim",
        "checks": checks,
        "failures": failures,
        "log": rel(log_path),
        "static_contract": {"path": rel(static_path), "status": static.get("status")},
        "partial_steps": len(partial_stages),
        "identical_frame_steps": len(identical_skip_lines),
        "probe_radius_px": sorted({int(match.group(6)) for match in probe_lines}),
        "probe_centers": [[int(match.group(4)), int(match.group(5))] for match in probe_lines],
        "probe_orbit": {
            "min_center_x": min((int(match.group(4)) for match in probe_lines), default=None),
            "max_center_x": max((int(match.group(4)) for match in probe_lines), default=None),
            "min_center_y": min((int(match.group(5)) for match in probe_lines), default=None),
            "max_center_y": max((int(match.group(5)) for match in probe_lines), default=None),
        },
        "regions_per_step": [int(match.group(1)) for match in partial_stages],
        "staged_bytes_per_step": [int(match.group(2)) for match in partial_stages],
        "refresh_elapsed_ms": [int(match.group(3)) for match in refresh_lines],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--static-contract", type=pathlib.Path, default=DEFAULT_STATIC)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.log.resolve(), args.static_contract.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: trace parsing failed: {error}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: {rel(args.out)}")
    return 0 if report["status"] == "PASS_MACHINE_VENDOR_PARTIAL_DISJOINT_CURRENT_STAGE_TRACE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
