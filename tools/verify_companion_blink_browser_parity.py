"""Verify a WB55 serial window against the fixed browser blink clock."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / (
    ".cache/validation/comp775-r53-independent-track-composed-commit/"
    "hardware-recording-composed/nucleo-serial-raw.log"
)
DEFAULT_PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
DEFAULT_OUTPUT = ROOT / (
    ".cache/validation/comp775-r53-independent-track-composed-commit/"
    "BLINK_BROWSER_PARITY.json"
)
LIVING_SEED = 0x4D3C2B1A


def u32(value: int) -> int:
    return value & 0xFFFFFFFF


def imul(left: int, right: int) -> int:
    return u32(left * right)


def blink_hash(value: int, channel: int = 3) -> int:
    result = u32(
        LIVING_SEED
        ^ imul(value + 1, 2246822519)
        ^ imul(channel + 1, 3266489917)
    )
    for byte in b"blink":
        result = imul(result ^ byte, 16777619)
    result ^= result >> 15
    result = imul(result, 2246822519)
    result ^= result >> 13
    return u32(result)


def parse_browser_contract(page: str) -> tuple[int, int, list[int]]:
    cadence = int(re.search(r"const CADENCE_MS = (\d+);", page).group(1))
    first = int(re.search(r"const BLINK_FIRST_INTERVAL_COMMITS = (\d+);", page).group(1))
    values = [
        int(value)
        for value in re.search(
            r"const BLINK_INTERVAL_COMMITS = Object\.freeze\(\[([^]]+)\]\);",
            page,
        ).group(1).split(",")
    ]
    return cadence, first, values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    log = args.log.read_text(encoding="utf-8", errors="replace")
    page = args.page.read_text(encoding="utf-8")
    cadence, first_commits, intervals = parse_browser_contract(page)
    enabled_match = re.search(r"scheduler=enabled .*? at_ms=(\d+)", log)
    pair_matches = re.findall(
        r"\[screen-blink\] pair closed_request=(\d+) open_request=(\d+) "
        r"closed_enqueued_ms=(\d+) closed_visible_ms=(\d+) "
        r"open_enqueued_ms=(\d+) open_visible_ms=(\d+) queue_gap_ms=(\d+) "
        r"closed_to_open_ms=(\d+) closed_control=0x([0-9A-F]{2}) "
        r"open_control=0x([0-9A-F]{2}) closed_bytes=(\d+) open_bytes=(\d+) "
        r"closed_busy_ms=(\d+) open_busy_ms=(\d+) committed=(\d+) "
        r"next_due_in_ms=(\d+) epoch=(\d+) interval_index=(\d+)",
        log,
    )
    reports = [
        (int(request), control, int(partial_before))
        for request, control, partial_before in re.findall(
            r"accepted_product_driver request=(\d+).*?control=0x([0-9A-F]{2})"
            r".*?partial_before=(\d+)",
            log,
        )
    ]
    pairs: list[dict[str, object]] = []
    for index, match in enumerate(pair_matches):
        (
            closed_request,
            open_request,
            closed_enqueued_ms,
            closed_visible_ms,
            open_enqueued_ms,
            open_visible_ms,
            queue_gap_ms,
            closed_to_open_ms,
            closed_control,
            open_control,
            closed_bytes,
            open_bytes,
            closed_busy_ms,
            open_busy_ms,
            committed,
            next_due_in_ms,
            epoch,
            interval_index,
        ) = match
        numeric = [
            int(value)
            for value in (
                closed_request,
                open_request,
                closed_enqueued_ms,
                closed_visible_ms,
                open_enqueued_ms,
                open_visible_ms,
                queue_gap_ms,
                closed_to_open_ms,
                closed_bytes,
                open_bytes,
                closed_busy_ms,
                open_busy_ms,
                committed,
                next_due_in_ms,
                epoch,
                interval_index,
            )
        ]
        (
            closed_request_i,
            open_request_i,
            closed_enqueued_i,
            closed_visible_i,
            open_enqueued_i,
            open_visible_i,
            queue_gap_i,
            closed_to_open_i,
            closed_bytes_i,
            open_bytes_i,
            closed_busy_i,
            open_busy_i,
            committed_i,
            next_due_i,
            epoch_i,
            interval_index_i,
        ) = numeric
        expected_index = (
            blink_hash(epoch_i + interval_index_i) * len(intervals)
        ) >> 32
        expected_due = intervals[expected_index] * cadence
        next_close_delay = (
            int(pair_matches[index + 1][2]) - open_visible_i
            if index + 1 < len(pair_matches)
            else None
        )
        pairs.append(
            {
                "closed_request": closed_request_i,
                "open_request": open_request_i,
                "request_ids_adjacent": open_request_i == closed_request_i + 1,
                "closed_control": closed_control,
                "open_control": open_control,
                "closed_bytes": closed_bytes_i,
                "open_bytes": open_bytes_i,
                "closed_busy_ms": closed_busy_i,
                "open_busy_ms": open_busy_i,
                "handoff_matches": open_enqueued_i >= closed_visible_i,
                "queue_gap_ms": queue_gap_i,
                "closed_to_open_visible_ms": closed_to_open_i,
                "open_committed": committed_i == 1,
                "expected_next_due_ms": expected_due,
                "reported_next_due_ms": next_due_i,
                "next_closed_enqueue_ms": next_close_delay,
                "next_closed_within_one_physical_commit": (
                    next_close_delay is None
                    or expected_due <= next_close_delay <= expected_due + 600
                ),
            }
        )

    first_delay = (
        int(pair_matches[0][2]) - int(enabled_match.group(1))
        if pair_matches and enabled_match
        else None
    )
    # Cover every interval bucket when the browser uses a short sparse cycle,
    # while keeping the four-pair floor used by longer cadence tables.
    required_complete_pairs = min(4, max(3, len(intervals)))
    checks = {
        "fixed_browser_declares_exact_next_commit_open": (
            "exact_open_next_commit: true" in page and "closed_commits: 1" in page
        ),
        "enough_complete_blink_pairs_for_browser_contract": (
            len(pairs) >= required_complete_pairs
        ),
        "all_close_open_counts_match": len(pairs) == len(pair_matches),
        "first_blink_uses_browser_wall_clock": (
            first_delay is not None
            and first_commits * cadence <= first_delay <= (first_commits + 1) * cadence
        ),
        "every_close_open_pair_is_atomic_and_partial": all(
            row["request_ids_adjacent"]
            and row["handoff_matches"]
            and row["queue_gap_ms"] <= 20
            and row["closed_to_open_visible_ms"] <= cadence + 64
            and row["open_committed"]
            and row["closed_control"] == "CF"
            and row["open_control"] == "CF"
            for row in pairs
        ),
        "every_next_interval_is_anchored_at_visible_open": all(
            row["reported_next_due_ms"] == row["expected_next_due_ms"]
            and row["next_closed_within_one_physical_commit"]
            for row in pairs
        ),
        "life_continues_after_blink": len(re.findall(r"\[screen-life\] family=", log)) >= 8,
        "home_has_no_automatic_full_maintenance": (
            not re.search(
                r"accepted_product_driver .*?control=0xFF .*?reason=4",
                log,
            )
            and all(control in {"FF", "CF"} for _, control, _ in reports)
            and max((partial for _, control, partial in reports if control == "CF"), default=0) >= 30
        ),
        "blink_scheduler_not_restarted_by_boot_completion": (
            log.count("scheduler=enabled") == 1 and log.count("scheduler=preserved") >= 1
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.blink_browser_parity.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "browser_contract": {
            "cadence_ms": cadence,
            "first_interval_commits": first_commits,
            "interval_commits": intervals,
        },
        "observed": {
            "pairs": pairs,
            "required_complete_pairs": required_complete_pairs,
            "first_closed_enqueue_ms_from_scheduler_enable": first_delay,
            "life_frames": len(re.findall(r"\[screen-life\] family=", log)),
            "partial_reports": sum(control == "CF" for _, control, _ in reports),
            "full_reports": sum(control == "FF" for _, control, _ in reports),
            "max_partial_before": max(
                (partial for _, control, partial in reports if control == "CF"),
                default=0,
            ),
        },
        "log": str(args.log),
        "hardware_contact": 1,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
