#!/usr/bin/env python3
"""Fail-closed final acceptance gate for COMP-REQ-775."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
ROOT = (
    REPO
    / ".cache/validation/comp-req-775-browser-device-single-source-final"
)
STATIC = ROOT / "64-life-trace-total-audit.json"
BROWSER = ROOT / "58-proactive-browser-pointer/MACHINE_READY.json"
LIFE_TRACE = ROOT / "64-life-trace-100-commits/MACHINE_READY.json"
BOOT = ROOT / "60-anywhere-exit-root-fix-boot-60s/BOOT_EVIDENCE.json"
RUNTIME = ROOT / "65-latest-app-active-awake-10min/TEN_MINUTE_MACHINE_READY.json"
BUILD = REPO / ".cache/validation/comp-req-775-incremental-sync/FIRMWARE_BUILD_READY.json"
PHYSICAL_DIR = ROOT / "62-canonical-combined-physical-after-anywhere-fix"
FINAL = ROOT / "MACHINE_READY.json"
PENDING = ROOT / "FINAL_PENDING.json"

PAGE_SHA256 = "D308CB63D287EFADC6DAC70F5E0DDE1BCA3AD13803B5A93E625BBB8505A7DAAE"
CONTRACT_SHA256 = "0A66B1F7ECED5A7C82EBD521D88AC4C8D813D2C5BB5C75CD5E66719C8F4C8CB9"
RESOURCE_ID = "28CF8B30A7AA3090647DBAA8F98030985CA0EE193BBFF20E5299E135E2107BF4"
GENERATION = 15

POINTER_RE = re.compile(
    r"\[touch-ui\]\s+browser_pointer\s+gesture=(?P<gesture>[a-z_]+)\s+"
    r"menu=(?P<menu>[01])\s+start=(?P<sx>\d+),(?P<sy>\d+)\s+"
    r"end=(?P<ex>\d+),(?P<ey>\d+)\s+duration_ms=(?P<duration>\d+)"
)
TOKEN_RE = re.compile(r"\b(?P<key>[a-z_]+)=(?P<value>\S+)")
REFRESH_PREFIX = "[epaper] accepted_product_driver "
PASS_SELECTIONS = {"通过", "pass", "accepted", "accept"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def indices(lines: list[str], needle: str) -> list[int]:
    return [index for index, line in enumerate(lines) if needle in line]


def first(lines: list[str], needle: str, start: int = 0) -> int:
    found = indices(lines[start:], needle)
    return start + found[0] if found else -1


def parse_refresh(index: int, line: str) -> dict[str, Any] | None:
    if REFRESH_PREFIX not in line:
        return None
    tokens = {m.group("key"): m.group("value") for m in TOKEN_RE.finditer(line)}
    parsed: dict[str, Any] = {"line": index + 1, "text": line}
    for key in (
        "request",
        "changed",
        "control",
        "bytes",
        "transaction_ms",
        "busy_ms",
        "maintenance",
        "reason",
        "result",
    ):
        if key not in tokens:
            continue
        try:
            parsed[key] = int(tokens[key], 0)
        except ValueError:
            pass
    return parsed


def refreshes(lines: list[str], start: int = 0, end: int | None = None) -> list[dict[str, Any]]:
    stop = len(lines) if end is None else end
    result = [parse_refresh(i, lines[i]) for i in range(start, stop)]
    return [item for item in result if item is not None]


def changed(entry: dict[str, Any]) -> bool:
    return entry.get("changed") == 1 and entry.get("result") == 1


def partial(entry: dict[str, Any]) -> bool:
    return (
        changed(entry)
        and entry.get("control") == 0xCF
        and 0 < entry.get("bytes", 0) <= 5000
        and entry.get("maintenance") == 0
    )


def boundary(entry: dict[str, Any]) -> bool:
    return (
        changed(entry)
        and entry.get("control") == 0xC7
        and entry.get("bytes") == 5000
        and entry.get("maintenance") == 1
    )


def next_changed_refresh(lines: list[str], anchor: int) -> dict[str, Any] | None:
    return next(
        (item for item in refreshes(lines, max(anchor + 1, 0)) if changed(item)),
        None,
    )


def pointer_records(lines: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = POINTER_RE.search(line)
        if match is None:
            continue
        records.append(
            {
                "line": index + 1,
                "gesture": match.group("gesture"),
                "menu": int(match.group("menu")),
                "start": [int(match.group("sx")), int(match.group("sy"))],
                "end": [int(match.group("ex")), int(match.group("ey"))],
                "duration_ms": int(match.group("duration")),
            }
        )
    return records


def physical_evidence(log: Path) -> dict[str, Any]:
    text = log.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    pointers = pointer_records(lines)
    gestures = [(item["gesture"], item["menu"]) for item in pointers]
    raw_nonzero = [
        i for i, line in enumerate(lines)
        if re.search(r"\[touch-raw\]\s+contacts=[1-9]", line)
    ]
    raw_down = indices(lines, "[touch-raw] contacts=1 event=down")
    raw_up = [
        i for i, line in enumerate(lines)
        if "[touch-raw]" in line
        and (" event=up " in line or "contacts=0" in line)
    ]
    latency_records: list[dict[str, Any]] = []
    for line in lines:
        if "[touch-raw]" not in line or "queue_class=" not in line:
            continue
        age = re.search(r"sample_age_ms=(\d+)", line)
        queue_class = re.search(r"queue_class=(\w+)", line)
        post_busy = re.search(r"post_busy_dispatch_ms=(\d+)", line)
        terminal = re.search(r"terminal=(\d+)", line)
        poll_count = re.search(r"input_poll_count=(\d+)", line)
        poll_over20 = re.search(r"input_poll_over20=(\d+)", line)
        poll_max = re.search(r"input_poll_max_ms=(\d+)", line)
        if not all((age, queue_class, post_busy, terminal,
                    poll_count, poll_over20, poll_max)):
            continue
        latency_records.append({
            "sample_age_ms": int(age.group(1)),
            "queue_class": queue_class.group(1),
            "post_busy_dispatch_ms": int(post_busy.group(1)),
            "terminal": int(terminal.group(1)),
            "input_poll_count": int(poll_count.group(1)),
            "input_poll_over20": int(poll_over20.group(1)),
            "input_poll_max_ms": int(poll_max.group(1)),
        })
    non_busy_ages = [
        item["sample_age_ms"] for item in latency_records
        if item["queue_class"] == "non_busy"
    ]
    busy_terminal_delays = [
        item["post_busy_dispatch_ms"] for item in latency_records
        if item["queue_class"] == "busy_buffer" and item["terminal"] == 1
    ]
    poll_count = max(
        (item["input_poll_count"] for item in latency_records), default=0
    )
    poll_over20 = max(
        (item["input_poll_over20"] for item in latency_records), default=0
    )
    poll_max_ms = max(
        (item["input_poll_max_ms"] for item in latency_records), default=0
    )
    non_busy_p95_ms = (
        sorted(non_busy_ages)[max(0, (len(non_busy_ages) * 95 + 99) // 100 - 1)]
        if non_busy_ages else None
    )

    record_start = first(lines, "[record] touch_double_tap action=start")
    if record_start < 0:
        record_start = first(lines, "[record] async_prepare complete result=ready")
    stop_queue = first(lines, "touch_double_tap action=stop_queued result=1", max(record_start, 0))
    restore_queue = first(lines, "[record-visual] action=stop_queue result=1", max(stop_queue, 0))
    stop_commit = first(lines, "[record-visual] action=stop_commit", max(restore_queue, 0))
    handoff = first(lines, "[record-stop] stage=visual_handoff", max(stop_commit, 0))
    finalize = first(lines, "[record-stop] stage=finalize_begin", max(handoff, 0))
    handoff_line = lines[handoff] if handoff >= 0 else ""
    wait_match = re.search(r"wait_ms=(\d+)", handoff_line)
    visual_wait_ms = int(wait_match.group(1)) if wait_match else None
    stop_commit_line = lines[stop_commit] if stop_commit >= 0 else ""
    gesture_visible_match = re.search(
        r"gesture_to_visible_ms=(\d+)", stop_commit_line
    )
    gesture_to_visible_ms = (
        int(gesture_visible_match.group(1)) if gesture_visible_match else None
    )
    request_match = (
        re.search(r"request=(\d+)", lines[stop_commit])
        if stop_commit >= 0
        else None
    )
    stop_request = int(request_match.group(1)) if request_match else None
    stop_refresh = next(
        (
            item
            for item in refreshes(lines, max(restore_queue, 0))
            if item.get("request") == stop_request
        ),
        None,
    )

    enter = first(lines, "[screen] menu_boundary=enter ")
    exit_event = first(lines, "[touch-ui] menu_right_swipe_exit ", max(enter, 0))
    exit_boundary = first(lines, "[screen] menu_boundary=exit ", max(exit_event, 0))
    sleep_request = first(lines, "[power] low_power_face request=sleepy trigger=idle_timer")
    sleep_complete = first(lines, "[power] low_power_face completed=1", max(sleep_request, 0))
    wake_boundary = first(lines, "[screen] low_power_boundary=wake ", max(sleep_complete, 0))
    wake_touch = first(lines, "[touch-ui] low_power_touch_wake state=active", max(wake_boundary, 0))

    enter_refresh = next_changed_refresh(lines, enter)
    exit_refresh = next_changed_refresh(lines, exit_boundary)
    sleep_refresh = next_changed_refresh(lines, sleep_request)
    wake_refresh = next_changed_refresh(lines, wake_touch)
    menu_region = refreshes(lines, enter, exit_boundary if exit_boundary >= 0 else None)
    menu_internal = [item for item in menu_region if changed(item) and not boundary(item)]
    exit_region_end = sleep_request if sleep_request >= 0 else len(lines)
    exit_tail = refreshes(lines, exit_boundary, exit_region_end)

    left_pointers = [
        item for item in pointers if item["gesture"] == "swipe_left" and item["menu"] == 1
    ]
    right_pointers = [
        item for item in pointers if item["gesture"] == "swipe_right" and item["menu"] == 1
    ]
    left_before_right = bool(left_pointers and right_pointers) and (
        left_pointers[-1]["line"] < right_pointers[-1]["line"]
    )
    no_exit_after_left = left_before_right and not any(
        "menu_boundary=exit" in line
        for line in lines[left_pointers[-1]["line"] : right_pointers[-1]["line"] - 1]
    )

    progress = [
        re.search(r"bucket=(\d+).*held_ms=(\d+).*state=(menu_hold_\d+ms)", line)
        for line in lines
        if "[emote-player] menu_hold_progress" in line
    ]
    progress = [match for match in progress if match is not None]
    progress_signature = [
        (int(match.group(1)), int(match.group(2)), match.group(3))
        for match in progress
    ]

    checks = {
        "real_ft6336_contact_observed": bool(raw_nonzero),
        "raw_pointer_lifecycles_have_down_and_release": (
            len(raw_down) >= len(pointers) > 0 and len(raw_up) >= len(pointers)
        ),
        "every_pointer_has_recent_raw_contact": bool(pointers) and all(
            any(max(0, item["line"] - 241) <= raw + 1 < item["line"] for raw in raw_nonzero)
            for item in pointers
        ),
        "touch_sampling_publish_p95_20_max_40_ms": (
            poll_count > 0
            and poll_max_ms <= 40
            and poll_over20 * 20 <= poll_count
        ),
        "touch_non_busy_dispatch_p95_60_ms": (
            non_busy_p95_ms is not None and non_busy_p95_ms <= 60
        ),
        "touch_busy_terminal_dispatch_max_20_ms": (
            bool(busy_terminal_delays) and max(busy_terminal_delays) <= 20
        ),
        "ordinary_tap_covered": ("tap", 0) in gestures,
        "recording_double_tap_entry_and_exit_covered": gestures.count(("double_tap", 0)) >= 2,
        "recording_stop_exact_return_queued": (
            0 <= record_start < stop_queue < restore_queue < stop_commit < handoff < finalize
            and all(
                token in lines[restore_queue]
                for token in ("restore_clip=", "restore_frame=", "restore_in_clip=")
            )
        ),
        "recording_stop_returns_home_with_fast_full": (
            gesture_to_visible_ms is not None
            and gesture_to_visible_ms <= 2600
            and "resolved=1" in handoff_line
            and "visible=1" in handoff_line
            and "timeout=0" in handoff_line
            and stop_refresh is not None
            and boundary(stop_refresh)
        ),
        "long_press_four_authored_milestones": (
            [item[0] for item in progress_signature] == [0, 1, 2, 3]
            and [item[2] for item in progress_signature]
            == [
                "menu_hold_1000ms",
                "menu_hold_1500ms",
                "menu_hold_2000ms",
                "menu_hold_2500ms",
            ]
            and gestures.count(("long_press", 0)) == 1
        ),
        "menu_entry_exactly_one_boundary_full": (
            enter >= 0
            and enter_refresh is not None
            and boundary(enter_refresh)
            and sum(boundary(item) for item in menu_region) == 1
        ),
        "menu_vertical_drag_is_partial_only": (
            any(gesture in gestures for gesture in (("swipe_up", 1), ("swipe_down", 1)))
            and bool(indices(lines, "browser_event=menu_vertical_drag"))
            and bool(menu_internal)
            and all(partial(item) for item in menu_internal)
        ),
        "menu_left_swipe_does_not_exit": no_exit_after_left,
        "menu_right_swipe_exits_once": (
            len(right_pointers) == 1
            and len(indices(lines, "[screen] menu_boundary=exit ")) == 1
            and 0 <= exit_event < exit_boundary
        ),
        "menu_exit_exactly_one_boundary_full": (
            exit_refresh is not None
            and boundary(exit_refresh)
            and sum(boundary(item) for item in exit_tail) == 1
        ),
        "home_choreography_resumes_partial": (
            any(partial(item) for item in exit_tail[1:])
            and first(lines, "[emote-player] life_frame", exit_boundary) >= 0
        ),
        "sleep_entry_exactly_one_boundary_full": (
            0 <= sleep_request < sleep_complete
            and any(
                token in lines[sleep_complete]
                for token in ("stop=allowed", "stop=blocked")
            )
            and sleep_refresh is not None
            and boundary(sleep_refresh)
        ),
        "sleep_wake_exactly_one_boundary_full": (
            0 <= wake_boundary < wake_touch
            and wake_refresh is not None
            and boundary(wake_refresh)
        ),
        "no_touch_or_runtime_fault": not any(
            token in text
            for token in (
                "terminal_fault=1",
                "watchdog] fault",
                "selftest=fail",
                "dropped=1",
                "mount=fail",
            )
        ),
    }
    return {
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "hardware_contact": 1 if raw_nonzero else 0,
        "log": str(log.resolve()),
        "log_sha256": sha256(log),
        "pointer_count": len(pointers),
        "raw_down_count": len(raw_down),
        "raw_release_count": len(raw_up),
        "touch_latency": {
            "non_busy_sample_count": len(non_busy_ages),
            "non_busy_dispatch_p95_ms": non_busy_p95_ms,
            "busy_terminal_count": len(busy_terminal_delays),
            "busy_terminal_dispatch_max_ms": (
                max(busy_terminal_delays) if busy_terminal_delays else None
            ),
            "input_active_poll_count": poll_count,
            "input_active_poll_over_20ms": poll_over20,
            "input_active_poll_max_ms": poll_max_ms,
        },
        "recording_visual_wait_ms": visual_wait_ms,
        "recording_gesture_to_visible_ms": gesture_to_visible_ms,
        "pointers": pointers,
        "menu_hold_progress": progress_signature,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", type=Path, default=STATIC)
    parser.add_argument("--browser", type=Path, default=BROWSER)
    parser.add_argument("--life-trace", type=Path, default=LIFE_TRACE)
    parser.add_argument("--boot", type=Path, default=BOOT)
    parser.add_argument("--runtime", type=Path, default=RUNTIME)
    parser.add_argument("--build", type=Path, default=BUILD)
    parser.add_argument("--physical-dir", type=Path, default=PHYSICAL_DIR)
    parser.add_argument("--final", type=Path, default=FINAL)
    parser.add_argument("--pending", type=Path, default=PENDING)
    args = parser.parse_args()
    for name in (
        "static", "browser", "life_trace", "boot", "runtime", "build",
        "physical_dir", "final", "pending"
    ):
        path = getattr(args, name)
        if not path.is_absolute():
            setattr(args, name, REPO / path)

    required = [
        args.static, args.browser, args.life_trace, args.boot, args.runtime,
        args.build,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    receipts = {
        "static": load(args.static) if args.static.is_file() else {},
        "browser": load(args.browser) if args.browser.is_file() else {},
        "life_trace": load(args.life_trace) if args.life_trace.is_file() else {},
        "boot": load(args.boot) if args.boot.is_file() else {},
        "runtime": load(args.runtime) if args.runtime.is_file() else {},
        "build": load(args.build) if args.build.is_file() else {},
    }
    log = args.physical_dir / "nucleo-serial-raw.log"
    operator_path = args.physical_dir / "operator-result.json"
    physical = physical_evidence(log) if log.is_file() else {
        "status": "NO_GO",
        "checks": {},
        "failed_checks": ["physical_log_missing"],
        "hardware_contact": 0,
    }
    operator = load(operator_path) if operator_path.is_file() else {}
    selected = str(operator.get("selected", "")).strip()
    operator_passed = selected.lower() in PASS_SELECTIONS

    checks = {
        "all_required_machine_receipts_exist": not missing,
        "latest_static_single_source_machine_ready": (
            receipts["static"].get("status") == "MACHINE_READY"
            and all(receipts["static"].get("checks", {}).values())
            and receipts["static"].get("page_sha256") == PAGE_SHA256
            and receipts["static"].get("contract_sha256") == CONTRACT_SHA256
            and receipts["static"].get("resource_id") == RESOURCE_ID
            and receipts["static"].get("generation") == GENERATION
        ),
        "fixed_page_complete_pointer_replay_machine_ready": (
            receipts["browser"].get("verdict") == "MACHINE_READY"
            and not receipts["browser"].get("browser_errors")
            and receipts["browser"].get("expected_page_sha256") == PAGE_SHA256
            and receipts["browser"].get("pointer_contract", {})
            .get("lower_left_double_tap", {})
            .get("exact_return_frame") is True
            and receipts["browser"].get("pointer_contract", {})
            .get("lower_left_double_tap", {})
            .get("second_pointer_cycle_to_synchronous_restore_ms", 701) <= 700
        ),
        "ten_families_first_100_commits_exact": (
            receipts["life_trace"].get("status") == "MACHINE_READY"
            and all(receipts["life_trace"].get("checks", {}).values())
            and receipts["life_trace"].get("source", {}).get("page_sha256")
            == PAGE_SHA256
        ),
        "latest_app_boot_machine_ready": (
            receipts["boot"].get("status") == "MACHINE_READY"
            and all(receipts["boot"].get("checks", {}).values())
        ),
        "accepted_active_choreography_stress_machine_ready": (
            receipts["runtime"].get("status") == "MACHINE_READY"
            and all(receipts["runtime"].get("checks", {}).values())
            and receipts["runtime"].get("identity", {}).get("generation")
            == GENERATION
            and receipts["runtime"].get("identity", {}).get("resource_prefix")
            == RESOURCE_ID[:8]
            and receipts["runtime"].get("identity", {}).get("hex_sha256")
            == receipts["build"].get("firmware", {}).get("hex_sha256")
        ),
        "formal_app_identity_and_address_guard": (
            receipts["build"].get("status") == "FIRMWARE_BUILD_READY"
            and all(receipts["build"].get("checks", {}).values())
            and receipts["build"].get("firmware", {}).get("hex_minimum_address")
            == "0x08007000"
            and int(receipts["build"].get("firmware", {}).get(
                "hex_maximum_address_exclusive", "0"
            ), 16) <= 0x08080000
        ),
        "real_physical_touch_suite_machine_ready": (
            physical.get("status") == "MACHINE_READY"
            and physical.get("hardware_contact", 0) > 0
            and all(physical.get("checks", {}).values())
        ),
        "canonical_operator_review_passed": operator_passed,
        "operator_result_bound_to_real_touch_log": (
            operator_passed
            and physical.get("hardware_contact", 0) > 0
            and operator_path.parent.resolve() == args.physical_dir.resolve()
        ),
    }
    ready = all(checks.values())
    result = {
        "schema": "companion.comp_req_775.final_acceptance.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "missing_files": missing,
        "machine_receipts": {
            str(path.relative_to(REPO)): {
                "sha256": sha256(path),
                "status": load(path).get("status", load(path).get("verdict")),
            }
            for path in required
            if path.is_file()
        },
        "physical": physical,
        "operator": {
            "path": str(operator_path.relative_to(REPO)),
            "selected": selected or None,
            "text": operator.get("text"),
            "hardware_contact": physical.get("hardware_contact", 0),
        },
        "hardware_contact": physical.get("hardware_contact", 0),
    }

    target = args.final if ready else args.pending
    target.parent.mkdir(parents=True, exist_ok=True)
    if not ready and args.final.exists():
        args.final.unlink()
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
