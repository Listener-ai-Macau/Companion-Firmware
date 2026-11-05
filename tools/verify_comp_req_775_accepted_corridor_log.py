#!/usr/bin/env python3
"""Verify the source-derived stable-corridor behavior on a reset-bounded log."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


BOOT_MARKER = "[boot] Companion NUCLEO-WB55RG bringup"
DRIVER_MARKER = "[epaper] accepted_product_driver "
FIELD_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>[^ ]+)")
WINDOW_RE = re.compile(r"^(?P<x0>\d+)-(?P<x1>\d+),(?P<y0>\d+)-(?P<y1>\d+)$")


def parse_driver(line: str) -> dict[str, object]:
    fields: dict[str, object] = {"line": line}
    for match in FIELD_RE.finditer(line):
        key = match.group("key")
        value = match.group("value")
        fields[key] = int(value) if value.isdigit() else value
    window = WINDOW_RE.match(str(fields.get("window", "")))
    if window:
        fields["window_tuple"] = tuple(int(window.group(name)) for name in ("x0", "x1", "y0", "y1"))
    return fields


def contains_window(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    return outer[0] <= inner[0] and outer[1] >= inner[1] and outer[2] <= inner[2] and outer[3] >= inner[3]


def verify(log_path: Path) -> dict[str, object]:
    raw = log_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    boot_offset = text.find(BOOT_MARKER)
    errors: list[str] = []
    if boot_offset < 0:
        errors.append("missing reset-bounded boot marker")
        runtime = text
    else:
        runtime = text[boot_offset:]

    lines = runtime.splitlines()
    drivers = [parse_driver(line) for line in lines if DRIVER_MARKER in line]
    full = [item for item in drivers if item.get("control") == "0xC7"]
    partial = [item for item in drivers if item.get("control") == "0xCF"]

    if len(full) != 1:
        errors.append(f"expected exactly one startup 0xC7, found {len(full)}")
    elif not (
        full[0].get("window") == "0-24,0-199"
        and full[0].get("bytes") == 5000
        and full[0].get("result") == 1
    ):
        errors.append("startup 0xC7 is not a successful 200x200/5000-byte commit")

    if len(partial) < 20:
        errors.append(f"expected at least 20 ordinary 0xCF commits, found {len(partial)}")

    previous_window: tuple[int, int, int, int] | None = None
    growth: list[dict[str, object]] = []
    for item in partial:
        request = item.get("request")
        window = item.get("window_tuple")
        if not isinstance(window, tuple):
            errors.append(f"partial request {request} has an invalid window")
            continue
        if previous_window is not None and not contains_window(window, previous_window):
            errors.append(f"coverage shrank at request {request}: {previous_window} -> {window}")
        if window != previous_window:
            growth.append({"request": request, "window": item.get("window"), "bytes": item.get("bytes")})
        previous_window = window
        if item.get("previous_plane_sync") != 0:
            errors.append(f"partial request {request} wrote the previous plane")
        if item.get("post_sync_command") != "0x00" or item.get("post_sync_bytes") != 0:
            errors.append(f"partial request {request} performed a post-BUSY controller sync")
        if item.get("ordinary_coverage_epoch") != 1:
            errors.append(f"partial request {request} did not use the coverage epoch")
        if item.get("maintenance") != 0 or item.get("reason") == 4:
            errors.append(f"partial request {request} used automatic maintenance")
        if item.get("result") != 1 or item.get("has_busy") != 1:
            errors.append(f"partial request {request} lacks a successful real-BUSY commit")

    blink_events: list[dict[str, object]] = []
    pending_phase: str | None = None
    for line in lines:
        phase_match = re.search(r"\[screen-blink\] phase=(closed|open) ", line)
        if phase_match:
            pending_phase = phase_match.group(1)
            continue
        if pending_phase is not None and DRIVER_MARKER in line:
            item = parse_driver(line)
            blink_events.append(
                {
                    "phase": pending_phase,
                    "request": item.get("request"),
                    "control": item.get("control"),
                    "window": item.get("window"),
                    "bytes": item.get("bytes"),
                }
            )
            pending_phase = None

    blink_pairs: list[dict[str, object]] = []
    for index in range(len(blink_events) - 1):
        closed = blink_events[index]
        opened = blink_events[index + 1]
        if closed["phase"] != "closed" or opened["phase"] != "open":
            continue
        adjacent = (
            isinstance(closed.get("request"), int)
            and isinstance(opened.get("request"), int)
            and opened["request"] == closed["request"] + 1
        )
        pair = {"closed": closed, "open": opened, "adjacent_requests": adjacent}
        blink_pairs.append(pair)
    if not blink_pairs:
        errors.append("no closed/open blink pair was bound to panel commits")
    for pair in blink_pairs:
        if not pair["adjacent_requests"]:
            errors.append("blink close/open panel requests were not adjacent")
        for phase in (pair["closed"], pair["open"]):
            if phase.get("control") != "0xCF":
                errors.append(f"blink {phase.get('phase')} did not use ordinary 0xCF")

    life_frames = re.findall(r"\[screen-life\].*?frame_index=(\d+)", runtime)
    distinct_life_frames = sorted({int(value) for value in life_frames})
    watchdog_healthy = runtime.count("[watchdog] healthy=1")
    if watchdog_healthy < 2:
        errors.append(f"expected at least two healthy watchdog reports, found {watchdog_healthy}")
    if "reason=4" in runtime:
        errors.append("runtime contains forbidden reason=4 automatic maintenance")
    if re.search(r"fault_mask=0x(?!00)[0-9A-Fa-f]{2}", runtime):
        errors.append("runtime contains a nonzero watchdog fault mask")
    if "[touch-health]" in runtime and re.search(r"\[touch-health\].*?(?:errors|dropped)=[1-9]\d*", runtime):
        errors.append("runtime contains FT6336 errors or dropped samples")

    final_window = partial[-1].get("window") if partial else None
    final_window_repeats = sum(1 for item in partial if item.get("window") == final_window)
    if partial and final_window_repeats < 8:
        errors.append(f"final source-derived corridor was not stable for 8 commits: {final_window_repeats}")

    return {
        "schema": "companion.comp_req_775.accepted_corridor_log.v1",
        "status": "MACHINE_READY" if not errors else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_log": str(log_path.resolve()),
        "source_log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "boot_marker_offset": boot_offset,
        "checks": {
            "startup_fast_full_count": len(full),
            "ordinary_partial_count": len(partial),
            "ordinary_single_plane_no_post_sync": not any(
                item.get("previous_plane_sync") != 0
                or item.get("post_sync_command") != "0x00"
                or item.get("post_sync_bytes") != 0
                for item in partial
            ),
            "coverage_never_shrinks": not any("coverage shrank" in error for error in errors),
            "coverage_growth": growth,
            "final_corridor": final_window,
            "final_corridor_commit_count": final_window_repeats,
            "blink_pairs": blink_pairs,
            "distinct_life_frames": distinct_life_frames,
            "watchdog_healthy_reports": watchdog_healthy,
            "automatic_maintenance_count": runtime.count("reason=4"),
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.log)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
