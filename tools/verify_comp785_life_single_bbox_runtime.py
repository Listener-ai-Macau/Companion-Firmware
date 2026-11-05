"""Verify the r44 ordinary-life dual-plane single-bbox runtime contract."""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


DRIVER_RE = re.compile(
    r"accepted_product_driver .*changed=(\d+) control=0xCF "
    r"window=(\d+)-(\d+),(\d+)-(\d+) bytes=(\d+) regions=(\d+) "
    r".*recording_overlay=(\d+) recording_overlay_only=(\d+) "
    r".*previous_plane_sync=(\d+).*result=(\d+)"
)


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def safe_atomic_blink_deferral(lines: list[str], receipt_at: int,
                               partial_before: int) -> bool:
    if 64 <= partial_before <= 65:
        return True
    if partial_before != 66:
        return False
    prior_driver = next(
        (i for i in range(receipt_at - 1, max(-1, receipt_at - 40), -1)
         if "[epaper] accepted_product_driver" in lines[i]), -1)
    if prior_driver < 0:
        return False
    before_match = re.search(r"partial_before=(\d+)", lines[prior_driver])
    pair_at = next(
        (i for i in range(prior_driver + 1, receipt_at)
         if "[screen-blink] pair " in lines[i]
         and "committed=1" in lines[i]
         and "closed_control=0xCF" in lines[i]
         and "open_control=0xCF" in lines[i]), -1)
    return (before_match is not None
            and int(before_match.group(1)) == 63
            and pair_at > prior_driver
            and not any("[epaper] accepted_product_driver" in lines[i]
                        for i in range(prior_driver + 1, receipt_at)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-maintenance-control",
                        choices=("C7", "FF"), default="C7")
    args = parser.parse_args()

    raw = Path(args.log).read_text(encoding="utf-8", errors="replace")
    boot_at = raw.rfind("[stage] uart ok")
    # Capturing without reset preserves the exact glass history we need to
    # judge. Accept a healthy watchdog before the LP boundary as the runtime
    # liveness receipt instead of resetting solely to satisfy this parser.
    probe_at = raw.find("[watchdog-probe] pass=")
    healthy_at = raw.find("[watchdog] healthy=1 stalled_mask=0x00")
    runtime_receipt_at = next(
        (value for value in (boot_at, probe_at, healthy_at) if value >= 0), -1)
    text = raw[runtime_receipt_at:] if runtime_receipt_at >= 0 else raw
    boundary_at = text.find("[s]57=")
    history = text[:boundary_at] if boundary_at >= 0 else text
    # A status-bar update uses the same 0xCF control and surface flags as life,
    # but is not an expression paint.  Attribute only the first accepted driver
    # receipt after each explicit screen-life request to the ordinary-life set.
    ordinary = []
    life_pending = False
    for line in history.splitlines():
        if "[screen-life]" in line:
            life_pending = True
            continue
        match = DRIVER_RE.search(line)
        if not match:
            continue
        # The independently scheduled status bar can land between a
        # screen-life request and its expression receipt.  Its panel-space
        # window is wholly inside the mapped 16-row top strip (Y 184..199),
        # and it intentionally writes current RAM only.  Do not consume the
        # pending life attribution on that unrelated track.
        y_start = int(match.group(4))
        y_end = int(match.group(5))
        if y_start >= 184 and y_end <= 199:
            continue
        if life_pending:
            if (match.group(1) == "1" and match.group(8) == "0" and
                    match.group(9) == "0"):
                ordinary.append(match)
            life_pending = False
    carrier_sizes = [
        (int(match.group(3)) - int(match.group(2)) + 1) *
        (int(match.group(5)) - int(match.group(4)) + 1)
        for match in ordinary
    ]
    transferred_sizes = [int(match.group(6)) for match in ordinary]
    regions = [int(match.group(7)) for match in ordinary]
    previous_sync = [int(match.group(10)) for match in ordinary]
    results = [int(match.group(11)) for match in ordinary]
    blink_traces = [
        line for line in history.splitlines()
        if "[epaper] blink_coverage_trace" in line
    ]
    history_lines = history.splitlines()
    maintenance_rows = [
        (index, int(match.group(1)))
        for index, line in enumerate(history_lines)
        if (match := re.search(
            rf"accepted_product_driver .*control=0x{args.expected_maintenance_control} "
            r".*maintenance=1 .*partial_before=(\d+)", line)) is not None
    ]
    maintenance_partials = [value for _, value in maintenance_rows]

    checks = {
        "valid_healthy_runtime_before_lp_boundary": (
            runtime_receipt_at >= 0 and boundary_at >= 0
        ),
        "production_history_crosses_three_safe_64_partial_boundaries": (
            len(maintenance_partials) >= 3
            and all(safe_atomic_blink_deferral(history_lines, receipt_at, value)
                    for receipt_at, value in maintenance_rows)
        ),
        "ordinary_partial_sample_count": len(carrier_sizes) >= 200,
        "ordinary_one_rectangle": bool(regions) and all(value == 1 for value in regions),
        "ordinary_driver_success": bool(results) and all(value == 1 for value in results),
        "ordinary_explicit_old_current": bool(previous_sync) and
        all(value == 1 for value in previous_sync) and
        all(transferred == carrier * 3 for transferred, carrier in
            zip(transferred_sizes, carrier_sizes)),
        "median_carrier_at_most_1500": bool(carrier_sizes) and
        statistics.median(carrier_sizes) <= 1500,
        "p95_carrier_at_most_2000": bool(carrier_sizes) and
        percentile(carrier_sizes, 0.95) <= 2000,
        "no_r40_fragmented_delta_path": "[epaper] exact_delta_bands" not in history,
        "blink_pairs_keep_r39_single_rectangle": len(blink_traces) >= 5 and all(
            re.search(r"closed_window=.*?/1 open_before=.*?open_window=.*?/1$", line)
            for line in blink_traces
        ),
        "no_faults": not any(
            token in text
            for token in ("HardFault", "BUSY timeout", "panel failure", "result=0")
        ),
    }
    result = {
        "schema": "companion.comp_req_785.life_single_bbox_runtime.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "metrics": {
            "ordinary_partials": len(carrier_sizes),
            "median_carrier_bytes": int(statistics.median(carrier_sizes)) if carrier_sizes else 0,
            "p95_carrier_bytes": percentile(carrier_sizes, 0.95) if carrier_sizes else 0,
            "maximum_carrier_bytes": max(carrier_sizes) if carrier_sizes else 0,
            "median_transferred_bytes": int(statistics.median(transferred_sizes)) if transferred_sizes else 0,
            "regions_not_one": sum(value != 1 for value in regions),
            "previous_sync_not_one": sum(value != 1 for value in previous_sync),
            "blink_complete_traces": len(blink_traces),
            "expected_maintenance_control":
                f"0x{args.expected_maintenance_control}",
        },
        "hardware_contact": 1,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
