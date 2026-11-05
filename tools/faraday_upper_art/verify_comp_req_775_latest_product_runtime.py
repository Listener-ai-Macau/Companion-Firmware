#!/usr/bin/env python3
"""Verify a reset-bounded COMP-REQ-775 boot plus continuation runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


TICK_RE = re.compile(r"\[tick\] t_ms=(\d+)")
PARTIAL_RE = re.compile(r"partial_before=(\d+)")
PRODUCT_PREFIX = "[epaper] accepted_product_driver "
TRUE_FULL_PREFIX = "[epaper] accepted_true_full "


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ticks(text: str) -> list[int]:
    return [int(value) for value in TICK_RE.findall(text)]


def product_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if PRODUCT_PREFIX in line]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot-log", type=Path, required=True)
    parser.add_argument("--continuation-log", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-generation", type=int, default=15)
    parser.add_argument("--expected-resource-prefix", default="28CF8B30")
    parser.add_argument("--expected-state-count", type=int, default=4995)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    boot = args.boot_log.read_text(encoding="utf-8", errors="replace")
    continuation = args.continuation_log.read_text(
        encoding="utf-8", errors="replace"
    )
    build = json.loads(args.build_receipt.read_text(encoding="utf-8"))
    boot_ticks = ticks(boot)
    continuation_ticks = ticks(continuation)
    boot_products = product_lines(boot)
    continuation_products = product_lines(continuation)
    all_products = [*boot_products, *continuation_products]
    partial_values = [
        int(match.group(1))
        for line in all_products
        if (match := PARTIAL_RE.search(line))
    ]
    sleep_products = [
        line
        for line in continuation_products
        if "control=0xC7" in line and "reason=5" in line
    ]
    sleep_line = sleep_products[0] if len(sleep_products) == 1 else ""
    sleep_index = continuation.find(sleep_line) if sleep_line else -1
    post_sleep = continuation[sleep_index + len(sleep_line) :] if sleep_line else ""
    source_path = Path(
        "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    )
    recorded_source_hash = build.get("source_sha256", {}).get(source_path.as_posix())
    firmware = build.get("firmware", {})
    checks = {
        "formal_latest_build_ready": build.get("status") == "FIRMWARE_BUILD_READY"
        and all(build.get("checks", {}).values()),
        "latest_app_source_hash_linked": recorded_source_hash == sha256(source_path),
        "ota_app_range_guarded": firmware.get("hex_minimum_address") == "0x08007000"
        and int(firmware.get("hex_maximum_address_exclusive", "0"), 16)
        <= 0x08080000,
        "single_reset_bounded_boot": boot.count("[boot] Companion NUCLEO-WB55RG bringup")
        == 1
        and (
            f"ui_generation=active generation={args.expected_generation} "
            f"resource_id={args.expected_resource_prefix} "
            f"entries={args.expected_state_count}"
        ) in boot,
        "same_session_ticks_monotonic": bool(boot_ticks and continuation_ticks)
        and boot_ticks == sorted(boot_ticks)
        and continuation_ticks == sorted(continuation_ticks)
        and continuation_ticks[0] > boot_ticks[-1]
        and continuation_ticks[0] - boot_ticks[-1] <= 120000,
        "runtime_exceeds_six_minutes": bool(continuation_ticks)
        and continuation_ticks[-1] >= 360000,
        "home_partial_crosses_legacy_limit": max(partial_values, default=0) >= 150,
        "no_automatic_home_full_refresh": not any(
            "reason=4" in line and "control=0xC7" in line
            for line in all_products
        ),
        "single_sleep_boundary_product_refresh": len(sleep_products) == 1,
        "single_sleep_true_full_waveform": continuation.count(TRUE_FULL_PREFIX) == 1
        and "control=0xC7" in continuation
        and "window=200x200" in continuation
        and "bytes_each=5000" in continuation
        and "data_planes=2" in continuation
        and "activation_count=1" in continuation,
        "no_display_commit_after_sleep": bool(sleep_line)
        and PRODUCT_PREFIX not in post_sleep
        and TRUE_FULL_PREFIX not in post_sleep,
        "watchdog_healthy_through_sleep": continuation.count(
            "[watchdog] healthy=1"
        )
        >= 10
        and "[watchdog] healthy=1" in post_sleep,
        "touch_health_healthy": "errors=0 recoveries=0" in continuation
        and "dropped=0" in continuation,
        "no_runtime_fault": not re.search(
            r"HardFault|MemManage|BusFault|UsageFault|\[fatal\]", boot + continuation
        ),
        "physical_contact_not_claimed": not re.search(
            r"\[touch-raw\][^\r\n]*contacts=[1-9]", continuation
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    receipt = {
        "schema": "companion.comp_req_775.latest_product_runtime.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "build": {
            "hex_sha256": firmware.get("hex_sha256"),
            "hex_minimum_address": firmware.get("hex_minimum_address"),
            "hex_maximum_address_exclusive": firmware.get(
                "hex_maximum_address_exclusive"
            ),
            "app_ble_sha256": recorded_source_hash,
        },
        "observed": {
            "boot_last_tick_ms": max(boot_ticks, default=0),
            "continuation_first_tick_ms": min(continuation_ticks, default=0),
            "continuation_last_tick_ms": max(continuation_ticks, default=0),
            "maximum_partial_before": max(partial_values, default=0),
            "boot_product_commits": len(boot_products),
            "continuation_product_commits": len(continuation_products),
            "sleep_boundary_product_commits": len(sleep_products),
            "watchdog_healthy_samples": continuation.count(
                "[watchdog] healthy=1"
            ),
            "hardware_contact": 0,
            "generation": args.expected_generation,
            "resource_prefix": args.expected_resource_prefix,
            "state_count": args.expected_state_count,
        },
        "evidence": {
            "boot_log": str(args.boot_log),
            "boot_log_sha256": sha256(args.boot_log),
            "continuation_log": str(args.continuation_log),
            "continuation_log_sha256": sha256(args.continuation_log),
            "build_receipt": str(args.build_receipt),
        },
        "claim_boundary": (
            "Latest App same-session runtime, home partial refresh, and one sleep "
            "boundary only; hardware_contact=0 does not prove touch interaction."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
