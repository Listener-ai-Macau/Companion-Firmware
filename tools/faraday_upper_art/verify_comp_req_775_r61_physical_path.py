#!/usr/bin/env python3
"""Fail-closed physical-path gate for the final COMP-REQ-775 topology.

The ordinary (no microphone) face/blink path keeps the accepted cumulative
source-complete, current-plane-only r51 contract.  Recording is the deliberate
exception: every physical activation contains the recording scheduler's exact
mic delta, while an independently due life/blink beat may add only exact
old/current delta bands outside mic/charger bounds.  A source-complete face
carrier is rejected because the Owner's r55 video showed it as visible lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FIELD_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")
WINDOW_RE = re.compile(r"^(\d+)-(\d+),(\d+)-(\d+)$")


def fields(line: str) -> dict[str, str]:
    return dict(FIELD_RE.findall(line))


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError(f"unterminated function {signature}")


def parse_window(value: str) -> tuple[int, int, int, int] | None:
    match = WINDOW_RE.fullmatch(value)
    return tuple(map(int, match.groups())) if match else None


def active_segment(lines: list[str]) -> list[str]:
    starts = [
        index for index, line in enumerate(lines)
        if "action=overlay_start result=1" in line
        and "tracks=wave_authored_life_independent" in line
    ]
    if not starts:
        return []
    start = starts[-1]
    stops = [
        index for index in range(start + 1, len(lines))
        if "action=stop_queue result=1" in lines[index]
    ]
    end = stops[0] + 1 if stops else len(lines)
    return lines[start:end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--ordinary-log", type=Path, required=True)
    parser.add_argument("--recording-log", type=Path, required=True)
    parser.add_argument("--negative-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-ordinary-life", type=int, default=60)
    parser.add_argument("--min-wave", type=int, default=250)
    parser.add_argument("--min-face", type=int, default=60)
    parser.add_argument("--min-blink", type=int, default=2)
    parser.add_argument("--min-duration-ms", type=int, default=180000)
    args = parser.parse_args()

    driver_path = (
        args.repo / "app/companion_pendant/epaper/"
        "panel_target_stm32wb_ssd1681.c"
    )
    driver = driver_path.read_text(encoding="utf-8")
    cached = function_body(driver, "static bool ssd1681_cached_mode2_diff_internal(")
    source_complete = function_body(
        driver, "static bool ssd1681_product_source_complete_window("
    )
    current_activation = function_body(
        driver, "static bool ssd1681_native_cached_mode2_movement_activation("
    )
    functional_activation = function_body(
        driver, "static bool ssd1681_native_cached_mode2_functional_activation("
    )

    ordinary_raw = args.ordinary_log.read_bytes()
    recording_raw = args.recording_log.read_bytes()
    negative_raw = args.negative_log.read_bytes()
    ordinary = ordinary_raw.decode("utf-8", errors="replace").splitlines()
    recording_all = recording_raw.decode("utf-8", errors="replace").splitlines()
    negative_all = negative_raw.decode("utf-8", errors="replace").splitlines()
    recording = active_segment(recording_all)
    negative = active_segment(negative_all)

    # Pair each no-mic authored tuple with the first following panel commit.
    ordinary_life_pairs: list[dict[str, str]] = []
    for index, line in enumerate(ordinary):
        if "[screen-life] family=" not in line or "dwell_commits=" not in line:
            continue
        for candidate in ordinary[index + 1:index + 16]:
            if "[screen-life] family=" in candidate:
                break
            if "[epaper] accepted_product_driver" in candidate:
                row = fields(candidate)
                if row.get("recording_overlay") == "0":
                    ordinary_life_pairs.append(row)
                break
    ordinary_partial = [
        row for row in ordinary_life_pairs
        if row.get("control") == "0xCF" and row.get("result") == "1"
        and row.get("ordinary_coverage_epoch") == "1"
    ]
    ordinary_face_windows = [
        window for row in ordinary_partial
        if (window := parse_window(row.get("window", ""))) is not None
    ]
    ordinary_blink_pairs = [
        fields(line) for line in ordinary
        if "[screen-blink] pair " in line and "committed=1" in line
    ]

    mic_rows = [
        fields(line) for line in recording
        if "[epaper] mic_local_partial only=1" in line
        and "emotion_refresh=0" in line
    ]
    mic_windows = [
        window for row in mic_rows
        if (window := parse_window(row.get("window", ""))) is not None
    ]
    isolated_rows = [
        fields(line) for line in recording
        if "[epaper] authored_plus_wave_isolated_bands" in line
        and "unchanged_face_driven=0" in line
        and "old_current=1" in line
        and "topology=r61" in line
    ]
    isolated_face_regions = [
        int(row["face_regions"])
        for row in isolated_rows
        if row.get("face_regions", "").isdigit()
    ]
    face_rows = [
        fields(line) for line in recording
        if "[record-phase] track=face " in line
        and "due_source=authored_absolute_deadline" in line
        and "wave_drives_face=0" in line
    ]
    blink_rows = [
        fields(line) for line in recording
        if "[record-phase] track=blink " in line
        and "due_source=blink_scheduler" in line
        and "wave_drives_blink=0" in line
    ]
    panel_rows = [
        fields(line) for line in recording
        if "[epaper] accepted_product_driver" in line
    ]
    ram_contract_rows = [
        fields(line) for line in recording
        if "[epaper] recording_ram_contract present=1" in line
    ]
    ram_contract_good = [
        row for row in ram_contract_rows
        if row.get("body_black_current") == "108"
        and row.get("expected") == "108"
        and row.get("body_black_previous") in {"0", "108"}
    ]
    ram_contract_parseable = [
        row for row in ram_contract_rows
        if row.get("body_black_current", "").isdigit()
        and row.get("expected", "").isdigit()
        and row.get("body_black_previous", "").isdigit()
    ]
    stored_rows = [
        fields(line) for line in recording_all if "[rec-flash] stored" in line
    ]
    stored = stored_rows[-1] if stored_rows else {}
    negative_source_complete = sum(
        "[epaper] authored_plus_wave_source_complete" in line
        for line in negative
    )

    forbidden_recording_tokens = (
        "blink_eye_window_only",
        "authored_life_union_above_mic",
        "life_wave_copaint",
        "life_face_source_complete_minus_mic",
        "authored_plus_wave_source_complete",
        "authored_plus_wave_exact_delta_fallback",
        "VISIBLE_FULL",
        "HardFault",
        "HARDFAULT",
        "previous_reset=iwdg",
        "panel result=failed",
        "watchdog_fault",
        "recording_face_prepare_fail",
        "recording_face_mic_invariant_fail",
    )
    forbidden_recording = sorted({
        token for token in forbidden_recording_tokens
        if any(token in line for line in recording)
    })
    forbidden_controls = [
        row.get("control") for row in panel_rows
        if row.get("control") in {"0xC7", "0xF7", "0xFF"}
    ]
    panel_failures = [row for row in panel_rows if row.get("result") != "1"]
    unhealthy = [
        line for line in recording
        if ("[watchdog]" in line and "healthy=1" not in line)
        or "stalled_mask=0x00" not in line and "[watchdog] healthy=" in line
    ]
    try:
        duration_ms = int(stored.get("duration_ms", "0"))
        drops = int(stored.get("drops", "-1"))
    except ValueError:
        duration_ms, drops = 0, -1

    checks = {
        "ordinary_source_complete_coverage_static": (
            "ssd1681_product_source_complete_window(" in cached
            and "comp_epaper_refresh_coverage_expand(" in source_complete
            and "s_ordinary_refresh_coverage = coverage_candidate;" in cached
            and "comp_epaper_refresh_coverage_reset(" in driver
        ),
        "ordinary_face_activation_is_single_current_plane": (
            "ssd1681_write_plane_region(0x24u, s_frame, window)"
            in current_activation
            and "ssd1681_write_plane_region(0x26u" not in current_activation
            and current_activation.count("ssd1681_command(0x20u)") == 1
        ),
        "natural_blink_reuses_ordinary_source_complete_path": (
            "Replay the owner-accepted r37 compositor" in driver
            and "if (!natural_blink_frame)" not in cached
            and "blink_eye_window_only" not in driver
        ),
        "recording_exact_delta_old_current_is_one_busy": (
            "ssd1681_product_exact_delta_bands_outside(" in cached
            and "recording_exact_face_carrier = true;" in cached
            and "unchanged_face_driven=0 old_current=1 eye_black=1" in cached
            and "recording_eye_black_reinforce = true;" in cached
            and "0x26u, s_blink_closed_frame" in functional_activation
            and "0x24u, s_frame" in functional_activation
            and functional_activation.count("ssd1681_command(0x20u)") == 1
        ),
        "ordinary_runtime_has_at_least_60_authored_current_plane_commits": (
            len(ordinary_partial) >= args.min_ordinary_life
            and len(ordinary_face_windows) >= args.min_ordinary_life
            and all(row.get("previous_plane_sync") in {"0", "1"}
                    for row in ordinary_partial)
            and all(int(row.get("post_sync_bytes", "0")) <= 224
                    for row in ordinary_partial)
        ),
        "ordinary_runtime_blink_is_source_complete_0xcf": (
            len(ordinary_blink_pairs) >= args.min_blink
            and all(row.get("closed_control") == "0xCF"
                    and row.get("open_control") == "0xCF"
                    for row in ordinary_blink_pairs)
            and all(int(row.get("closed_bytes", "0")) > 1000
                    and int(row.get("open_bytes", "0")) > 1000
                    for row in ordinary_blink_pairs)
        ),
        "recording_wave_is_only1_and_inside_mic_bounds": (
            len(mic_rows) >= max(20, args.min_wave // 3)
            and len(mic_rows) + len(isolated_rows) >= args.min_wave
            and len(mic_windows) == len(mic_rows)
            and all(0 <= x0 <= x1 <= 4 and 22 <= y0 <= y1 <= 41
                    for x0, x1, y0, y1 in mic_windows)
        ),
        "recording_life_uses_only_exact_isolated_bands": (
            len(isolated_rows) >= args.min_face
            and len(face_rows) >= args.min_face
            # RTOS writers can splice bytes into the diagnostic UART. Every
            # parseable count must be legal and at least 98% must parse.
            and len(isolated_face_regions) / len(isolated_rows) >= 0.98
            and all(1 <= count <= 30 for count in isolated_face_regions)
        ),
        "recording_blink_clock_is_independent": len(blink_rows) >= args.min_blink,
        "recording_has_no_legacy_path_or_full_refresh": (
            not forbidden_recording and not forbidden_controls
        ),
        "recording_panel_and_watchdog_are_clean": (
            len(ram_contract_rows) >= args.min_wave
            # Logger writes from the display and real-time encoder can splice
            # diagnostic bytes without changing the panel transaction. Keep
            # both a relative and absolute corruption cap, while requiring
            # every parseable RAM contract to remain exact.
            and len(ram_contract_parseable) / len(ram_contract_rows) >= 0.95
            and (len(ram_contract_rows) - len(ram_contract_parseable)) <= 16
            and len(ram_contract_good) == len(ram_contract_parseable)
            and not panel_failures and not unhealthy
            and any("[watchdog] healthy=1 stalled_mask=0x00" in line
                    for line in recording)
        ),
        "recording_is_real_180s_drop_free_and_stored": (
            duration_ms >= args.min_duration_ms and drops == 0
        ),
        "owner_r55_negative_is_rejected_for_source_complete_face_carrier": (
            negative_source_complete > 0
        ),
    }
    result = {
        "schema": "companion.comp_req_775.r61_physical_path.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, ok in checks.items() if not ok],
        "counts": {
            "ordinary_life_current_plane": len(ordinary_partial),
            "ordinary_blink_pairs": len(ordinary_blink_pairs),
            "recording_mic_only1": len(mic_rows),
            "recording_isolated_face": len(isolated_rows),
            "recording_face_clock": len(face_rows),
            "recording_blink_clock": len(blink_rows),
            "recording_panel": len(panel_rows),
            "recording_ram_contract": len(ram_contract_rows),
            "recording_ram_contract_good": len(ram_contract_good),
            "recording_ram_contract_parseable": len(ram_contract_parseable),
            "recording_ram_contract_uart_spliced": (
                len(ram_contract_rows) - len(ram_contract_parseable)),
            "recording_isolated_face_parseable": len(isolated_face_regions),
            "recording_isolated_face_uart_spliced": (
                len(isolated_rows) - len(isolated_face_regions)),
            "negative_source_complete_face_carrier": negative_source_complete,
        },
        "recording": {
            "duration_ms": duration_ms,
            "drops": drops,
            "forbidden_tokens": forbidden_recording,
            "forbidden_controls": forbidden_controls,
            "panel_failures": len(panel_failures),
            "unhealthy_watchdog_rows": len(unhealthy),
        },
        "source": {
            "driver": str(driver_path.resolve()),
            "driver_sha256": hashlib.sha256(driver_path.read_bytes()).hexdigest().upper(),
            "ordinary_log": str(args.ordinary_log.resolve()),
            "ordinary_log_sha256": hashlib.sha256(ordinary_raw).hexdigest().upper(),
            "recording_log": str(args.recording_log.resolve()),
            "recording_log_sha256": hashlib.sha256(recording_raw).hexdigest().upper(),
            "negative_log": str(args.negative_log.resolve()),
            "negative_log_sha256": hashlib.sha256(negative_raw).hexdigest().upper(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
