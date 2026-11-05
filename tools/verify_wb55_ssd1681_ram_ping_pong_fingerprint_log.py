#!/usr/bin/env python3
"""Fail-closed oracle for the production-off SSD1681 RAM fingerprint run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FRAME_BYTES = 5000
READ_BYTES = 5001
STAGES = (
    "after_basemap_activation",
    "after_dirty_staging_before_activation",
    "after_partial_activation",
)
READ_RE = re.compile(
    r"\[epaper\] ram_fingerprint stage=(\S+) selector=([01]) repeat=([12]) "
    r"len=(\d+) read_ok=([01]) data=([0-9A-F]*) "
    r"gpio_restore=([01]) sda=0 sck=0 cs=1"
)


def baseline() -> bytes:
    return bytes(0xA5 ^ ((index * 37) & 0xFF) ^ ((index >> 3) & 0xFF)
                 for index in range(FRAME_BYTES))


def current() -> bytes:
    data = bytearray(baseline())
    for y in range(96, 104):
        for x in range(10, 12):
            data[y * 25 + x] ^= 0x3C
    return bytes(data)


def changed_indices(left: bytes, right: bytes) -> list[int]:
    return [index for index, pair in enumerate(zip(left, right)) if pair[0] != pair[1]]


def evaluate(text: str) -> dict:
    errors: list[str] = []
    reads: dict[tuple[str, int, int], bytes] = {}
    dummy: dict[tuple[str, int, int], int] = {}
    expected_keys = {(stage, selector, repeat)
                     for stage in STAGES for selector in range(2) for repeat in range(1, 3)}

    for match in READ_RE.finditer(text):
        stage, selector_s, repeat_s, length_s, read_ok_s, hex_data, gpio_s = match.groups()
        key = (stage, int(selector_s), int(repeat_s))
        if key in reads:
            errors.append(f"duplicate read: {key}")
            continue
        if stage not in STAGES:
            errors.append(f"unexpected stage: {stage}")
            continue
        if int(length_s) != READ_BYTES or read_ok_s != "1" or gpio_s != "1":
            errors.append(f"invalid transport metadata: {key}")
            continue
        if len(hex_data) != READ_BYTES * 2:
            errors.append(f"invalid response length: {key} hex={len(hex_data)}")
            continue
        try:
            raw = bytes.fromhex(hex_data)
        except ValueError:
            errors.append(f"non-hex response: {key}")
            continue
        dummy[key] = raw[0]
        reads[key] = raw[1:]

    missing = sorted(expected_keys - set(reads))
    unexpected = sorted(set(reads) - expected_keys)
    if missing:
        errors.append(f"missing reads: {missing}")
    if unexpected:
        errors.append(f"unexpected reads: {unexpected}")

    for stage in STAGES:
        for selector in range(2):
            one = reads.get((stage, selector, 1))
            two = reads.get((stage, selector, 2))
            if one is not None and two is not None and one != two:
                errors.append(f"repeat mismatch: {stage}/selector{selector}")

    base = baseline()
    now = current()
    expected_dirty = changed_indices(base, now)
    if len(expected_dirty) != 16:
        errors.append("internal oracle dirty-byte count is not 16")

    def payload(stage: str, selector: int) -> bytes | None:
        return reads.get((stage, selector, 1))

    fixed_expectations = {
        ("after_basemap_activation", 0): base,
        ("after_basemap_activation", 1): base,
        ("after_dirty_staging_before_activation", 0): now,
        ("after_dirty_staging_before_activation", 1): base,
    }
    for key, expected in fixed_expectations.items():
        actual = payload(*key)
        if actual is not None and actual != expected:
            diffs = changed_indices(actual, expected)
            outside = [index for index in diffs if index not in expected_dirty]
            errors.append(
                f"fixed-stage mismatch: {key} differences={len(diffs)} outside_dirty={len(outside)}"
            )

    candidates = {
        "fixed_register_banks_selector0_current_selector1_base": (now, base),
        "activation_swapped_banks_selector0_base_selector1_current": (base, now),
        "activation_copied_current_to_both_banks": (now, now),
        "activation_reverted_both_banks_to_base": (base, base),
    }
    post0 = payload("after_partial_activation", 0)
    post1 = payload("after_partial_activation", 1)
    matches = [] if post0 is None or post1 is None else [
        name for name, pair in candidates.items() if pair == (post0, post1)
    ]
    if len(matches) != 1:
        errors.append(f"post-activation mapping is not unique: {matches}")

    all_payloads = list(reads.values())
    if any(data == bytes(FRAME_BYTES) or data == bytes([0xFF]) * FRAME_BYTES
           for data in all_payloads):
        errors.append("all-00 or all-FF payload rejected")

    start_ok = re.search(
        r"ram_fingerprint start .*frame_bytes=5000 .*read_bytes=5001 .*dummy_bytes=1 "
        r".*dirty_bytes=16 .*writes_24=2 writes_26=1 refresh_commands=2 "
        r"hard_resets=2 busy_waits=4 retries=0",
        text,
    ) is not None
    baseline_action = re.search(
        r"ram_fingerprint action=baseline control=0xF7 refresh=0x20 "
        r"busy_complete=1 elapsed_ms=(\d+)", text)
    dirty_action_ok = "ram_fingerprint action=dirty_stage command=0x24 bytes=16 activation=0 ok=1" in text
    partial_action = re.search(
        r"ram_fingerprint action=partial control=0xFF refresh=0x20 "
        r"busy_complete=1 elapsed_ms=(\d+)", text)
    result_ok = re.search(
        r"ram_fingerprint result=ok stages=3 selectors=2 repeats=2 read_bytes=5001 "
        r"writes_24=2 writes_26=1 refresh_commands=2 controls=F7,FF "
        r"hard_resets=2 retries=0 gpio_restore=1 sda=0 sck=0 cs=1",
        text,
    ) is not None
    if not start_ok:
        errors.append("start contract marker missing")
    if baseline_action is None:
        errors.append("baseline activation marker missing")
    if not dirty_action_ok:
        errors.append("dirty staging marker missing")
    if partial_action is None:
        errors.append("partial activation marker missing")
    if not result_ok:
        errors.append("result marker missing")

    timings = {
        "baseline_busy_elapsed_ms": int(baseline_action.group(1)) if baseline_action else None,
        "partial_busy_elapsed_ms": int(partial_action.group(1)) if partial_action else None,
    }
    for name, value in timings.items():
        if value is not None and value > 5000:
            errors.append(f"{name} exceeds 5000 ms")

    return {
        "schema_id": "companion.ssd1681.ram_ping_pong_fingerprint.v1",
        "status": "PASS_UNIQUE_RAM_MAPPING" if not errors else "NO_GO_RAM_MAPPING",
        "errors": errors,
        "contract": {
            "frame_bytes": FRAME_BYTES,
            "response_bytes": READ_BYTES,
            "dummy_bytes": 1,
            "stages": list(STAGES),
            "selectors": [0, 1],
            "repeats_per_selector": 2,
            "dirty_indices": expected_dirty,
            "data_entry": "0x01",
            "write_bank_registers": {"selector_0": "0x24", "selector_1": "0x26"},
        },
        "observed": {
            "read_count": len(reads),
            "dummy_bytes": {"/".join(map(str, key)): value for key, value in dummy.items()},
            "unique_mapping_matches": matches,
            "selected_mapping": matches[0] if len(matches) == 1 else None,
            "timings": timings,
        },
        "claims_not_made": [
            "selector banks are not called visual previous/current before this fingerprint",
            "no production admission",
            "no LUT, waveform, temperature, voltage, Rig, CRIG, or expression claim",
        ],
    }


def fixture(mapping: str = "fixed_register_banks_selector0_current_selector1_base") -> str:
    base = baseline()
    now = current()
    post = {
        "fixed_register_banks_selector0_current_selector1_base": (now, base),
        "activation_swapped_banks_selector0_base_selector1_current": (base, now),
    }[mapping]
    stage_values = {
        "after_basemap_activation": (base, base),
        "after_dirty_staging_before_activation": (now, base),
        "after_partial_activation": post,
    }
    lines = [
        "[epaper] ram_fingerprint start frame_bytes=5000 read_bytes=5001 dummy_bytes=1 data_entry=0x01 dirty_x=10-11 dirty_y=96-103 dirty_bytes=16 writes_24=2 writes_26=1 refresh_commands=2 hard_resets=2 busy_waits=4 retries=0",
        "[epaper] ram_fingerprint action=baseline control=0xF7 refresh=0x20 busy_complete=1 elapsed_ms=500",
        "[epaper] ram_fingerprint action=dirty_stage command=0x24 bytes=16 activation=0 ok=1",
        "[epaper] ram_fingerprint action=partial control=0xFF refresh=0x20 busy_complete=1 elapsed_ms=400",
    ]
    for stage, values in stage_values.items():
        for selector, value in enumerate(values):
            for repeat in (1, 2):
                raw = bytes([0x00]) + value
                lines.append(
                    f"[epaper] ram_fingerprint stage={stage} selector={selector} repeat={repeat} "
                    f"len=5001 read_ok=1 data={raw.hex().upper()} gpio_restore=1 sda=0 sck=0 cs=1"
                )
    lines.append("[epaper] ram_fingerprint result=ok stages=3 selectors=2 repeats=2 read_bytes=5001 writes_24=2 writes_26=1 refresh_commands=2 controls=F7,FF hard_resets=2 retries=0 gpio_restore=1 sda=0 sck=0 cs=1")
    return "\n".join(lines)


def self_test() -> int:
    positive = evaluate(fixture())
    swapped = evaluate(fixture("activation_swapped_banks_selector0_base_selector1_current"))
    corrupted_text = fixture().replace("data=00", "data=00FF", 1)
    corrupted = evaluate(corrupted_text)
    repeated = fixture().replace("repeat=2 len=5001 read_ok=1 data=00", "repeat=2 len=5001 read_ok=1 data=0000", 1)
    repeat_bad = evaluate(repeated)
    ok = (positive["status"] == "PASS_UNIQUE_RAM_MAPPING" and
          swapped["status"] == "PASS_UNIQUE_RAM_MAPPING" and
          corrupted["status"] == "NO_GO_RAM_MAPPING" and
          repeat_bad["status"] == "NO_GO_RAM_MAPPING")
    print("PASS: fingerprint parser positive/alternative/length/repeat fixtures" if ok
          else "FAIL: fingerprint parser self-test")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.log is None or args.out is None:
        parser.error("--log and --out are required unless --self-test is used")
    result = evaluate(args.log.read_text(encoding="utf-8", errors="ignore"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "PASS_UNIQUE_RAM_MAPPING" else 1


if __name__ == "__main__":
    sys.exit(main())
