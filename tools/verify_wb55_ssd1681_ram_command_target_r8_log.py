#!/usr/bin/env python3
"""Fail-closed parser for the R8 post-activation RAM command-target probe."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FRAME_BYTES = 5000
READ_BYTES = 5001
TAG_INDICES = tuple(y * 25 + x for y in range(96, 104) for x in range(10, 12))
STAGES = (
    "before_swap",
    "before_swap_activation",
    "after_swap",
    "after_tag_24",
    "after_restore_24",
    "after_tag_26",
    "after_restore_26",
)
READ_RE = re.compile(
    r"\[epaper\] ram_command_target_r8 read stage=(\S+) selector=([01]) repeat=([12]) "
    r"len=(\d+) read_ok=([01]) repeat_ok=([01]) data=([0-9A-F]*) "
    r"gpio_restore=([01]) sda=0 sck=0 cs=1"
)
PROBE_RE = re.compile(
    r"\[epaper\] ram_command_target_r8 probe command=0x(24|26) "
    r"target_selector=([01]) changed0=([01]) changed1=([01]) restored=([01]) "
    r"activation_after_tag=0"
)
RESULT_RE = re.compile(
    r"\[epaper\] ram_command_target_r8 result=(ok|no_go) mapping=(\S+) "
    r"target24=(\d+) target26=(\d+) stages=(\d+) selector_reads=(\d+) "
    r"writes_24=(\d+) writes_26=(\d+) swap_activations=(\d+) "
    r"post_tag_activations=(\d+) controls_ff=(\d+) refresh_20=(\d+) "
    r"hard_resets=(\d+) retries=(\d+) gpio_restore=([01]) sda=0 sck=0 cs=1"
)


def tagged(value: int) -> bytes:
    frame = bytearray([0xFF] * FRAME_BYTES)
    for index in TAG_INDICES:
        frame[index] = value
    return bytes(frame)


WHITE = bytes([0xFF]) * FRAME_BYTES
SWAP = tagged(0xC3)
TAG24 = tagged(0x5A)
TAG26 = tagged(0xA5)


def changed_indices(left: bytes, right: bytes) -> list[int]:
    return [index for index, values in enumerate(zip(left, right)) if values[0] != values[1]]


def evaluate(text: str) -> dict:
    errors: list[str] = []
    start_index = text.find("[epaper] ram_command_target_r8 start ")
    result_matches = list(RESULT_RE.finditer(text, max(start_index, 0)))
    if start_index < 0:
        errors.append("start marker missing")
        scoped = text
    elif len(result_matches) != 1:
        errors.append(f"result marker count differs: {len(result_matches)}")
        scoped = text[start_index:]
    else:
        scoped = text[start_index:result_matches[0].end()]

    reads: dict[tuple[str, int, int], bytes] = {}
    expected_keys = {
        (stage, selector, repeat)
        for stage in STAGES
        for selector in range(2)
        for repeat in (1, 2)
    }
    for match in READ_RE.finditer(scoped):
        stage, selector_s, repeat_s, length_s, read_ok, repeat_ok, raw_hex, gpio = match.groups()
        key = (stage, int(selector_s), int(repeat_s))
        if key in reads:
            errors.append(f"duplicate read: {key}")
            continue
        if stage not in STAGES:
            errors.append(f"unexpected stage: {stage}")
            continue
        if int(length_s) != READ_BYTES or read_ok != "1" or repeat_ok != "1" or gpio != "1":
            errors.append(f"transport metadata failure: {key}")
            continue
        if len(raw_hex) != READ_BYTES * 2:
            errors.append(f"response length failure: {key} hex={len(raw_hex)}")
            continue
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError:
            errors.append(f"response is not hex: {key}")
            continue
        reads[key] = raw[1:]

    missing = sorted(expected_keys - set(reads))
    unexpected = sorted(set(reads) - expected_keys)
    if missing:
        errors.append(f"missing reads: {missing}")
    if unexpected:
        errors.append(f"unexpected reads: {unexpected}")
    for stage in STAGES:
        for selector in range(2):
            first = reads.get((stage, selector, 1))
            second = reads.get((stage, selector, 2))
            if first is not None and second is not None and first != second:
                errors.append(f"repeat mismatch: {stage}/selector{selector}")

    def payload(stage: str, selector: int) -> bytes | None:
        return reads.get((stage, selector, 1))

    fixed = {
        ("before_swap", 0): WHITE,
        ("before_swap", 1): WHITE,
        ("before_swap_activation", 0): SWAP,
        ("before_swap_activation", 1): WHITE,
        ("after_swap", 0): WHITE,
        ("after_swap", 1): SWAP,
        ("after_restore_24", 0): WHITE,
        ("after_restore_24", 1): SWAP,
        ("after_restore_26", 0): WHITE,
        ("after_restore_26", 1): SWAP,
    }
    for key, expected in fixed.items():
        actual = payload(*key)
        if actual is not None and actual != expected:
            differences = changed_indices(actual, expected)
            errors.append(f"state mismatch: {key} differences={len(differences)}")

    targets: dict[int, int | None] = {0x24: None, 0x26: None}
    for command, stage, expected_tag in (
        (0x24, "after_tag_24", TAG24),
        (0x26, "after_tag_26", TAG26),
    ):
        pair = (payload(stage, 0), payload(stage, 1))
        candidates = []
        if pair[0] is not None and pair[1] is not None:
            if pair == (expected_tag, SWAP):
                candidates.append(0)
            if pair == (WHITE, expected_tag):
                candidates.append(1)
        if len(candidates) != 1:
            errors.append(f"0x{command:02X} target is not unique: {candidates}")
        else:
            targets[command] = candidates[0]

    if TAG24 == TAG26 or SWAP in (TAG24, TAG26):
        errors.append("internal tag oracle is ambiguous")

    probes = {}
    for match in PROBE_RE.finditer(scoped):
        command_s, selector_s, changed0, changed1, restored = match.groups()
        command = int(command_s, 16)
        if command in probes:
            errors.append(f"duplicate probe marker: 0x{command:02X}")
        probes[command] = {
            "selector": int(selector_s),
            "changed": (int(changed0), int(changed1)),
            "restored": int(restored),
        }
    if set(probes) != {0x24, 0x26}:
        errors.append(f"probe marker set differs: {sorted(probes)}")
    for command, target in targets.items():
        marker = probes.get(command)
        expected_changed = None if target is None else ((1, 0) if target == 0 else (0, 1))
        if marker is not None and (
            marker["selector"] != target
            or marker["changed"] != expected_changed
            or marker["restored"] != 1
        ):
            errors.append(f"probe marker disagrees with readback: 0x{command:02X}")

    action = re.search(
        r"ram_command_target_r8 action=known_swap control=0xFF refresh=0x20 "
        r"busy_complete=1 elapsed_ms=(\d+) activation_count=1",
        scoped,
    )
    start_ok = re.search(
        r"ram_command_target_r8 start frame_bytes=5000 read_bytes=5001 dummy_bytes=1 "
        r"tag_bytes=16 tag_x=10-11 tag_y=96-103 selectors=2 repeats=2 "
        r"swap_activations=1 controls_ff=1 refresh_20=1 post_tag_activations=0 "
        r"writes_24=3 writes_26=2 hard_resets=1 retries=0",
        scoped,
    ) is not None
    if not start_ok:
        errors.append("start contract differs")
    if action is None:
        errors.append("single known-swap activation marker missing")
    elif int(action.group(1)) > 5000:
        errors.append("known-swap BUSY exceeds 5000 ms")
    if scoped.count("action=known_swap") != 1:
        errors.append("known-swap activation count differs")
    if scoped.count("control=0xFF") != 1 or scoped.count("refresh=0x20") != 1:
        errors.append("activation command markers are not singular")
    first_tag = scoped.find("read stage=after_tag_24")
    if first_tag < 0 or "control=" in scoped[first_tag:] or "refresh=" in scoped[first_tag:]:
        errors.append("activation marker appears after tag write")
    forbidden = ("0xF7", "0xC7", "0xCF", "0x32", "0x37", "ball_motion", "point_probe")
    if any(token in scoped for token in forbidden):
        errors.append("forbidden waveform/full/motion marker present")

    selected_mapping = None
    if targets == {0x24: 0, 0x26: 1}:
        selected_mapping = "fixed_bank"
    elif targets == {0x24: 1, 0x26: 0}:
        selected_mapping = "role_based_current_0x24_base_0x26"
    else:
        errors.append(f"command targets do not form a bijection: {targets}")

    result = result_matches[0] if len(result_matches) == 1 else None
    if result is None:
        errors.append("result marker missing or duplicated")
    else:
        (status, mapping, target24, target26, stages, selector_reads,
         writes24, writes26, activations, post_tag, controls, refreshes,
         hard_resets, retries, gpio) = result.groups()
        expected = (
            status == "ok"
            and mapping == selected_mapping
            and int(target24) == targets[0x24]
            and int(target26) == targets[0x26]
            and tuple(map(int, (stages, selector_reads, writes24, writes26,
                                activations, post_tag, controls, refreshes,
                                hard_resets, retries, gpio)))
            == (7, 28, 3, 2, 1, 0, 1, 1, 1, 0, 1)
        )
        if not expected:
            errors.append("result contract disagrees with readback")

    role_by_selector = {0: "base_role_after_swap", 1: "current_role_after_swap"}
    return {
        "schema_id": "companion.wb55.ssd1681_ram_command_target_r8_trace.v1",
        "status": "PASS_MACHINE_R8_COMMAND_TARGET_MAPPING" if not errors else "NO_GO_R8_COMMAND_TARGET_MAPPING",
        "errors": errors,
        "contract": {
            "frame_bytes": FRAME_BYTES,
            "response_bytes": READ_BYTES,
            "tag_indices": list(TAG_INDICES),
            "stages": list(STAGES),
            "selectors": [0, 1],
            "repeats_per_selector": 2,
            "swap_activations": 1,
            "post_tag_activations": 0,
        },
        "observed": {
            "read_count": len(reads),
            "target_selector": {"0x24": targets[0x24], "0x26": targets[0x26]},
            "target_role": {
                "0x24": role_by_selector.get(targets[0x24]),
                "0x26": role_by_selector.get(targets[0x26]),
            },
            "selected_mapping": selected_mapping,
            "known_swap_busy_elapsed_ms": int(action.group(1)) if action else None,
        },
        "claims_not_made": [
            "no optical or ghosting result",
            "no production admission",
            "no LUT, waveform, temperature, voltage, motion, Rig, CRIG, or expression claim",
        ],
    }


def fixture(target24: int = 0, target26: int = 1) -> str:
    stages = {
        "before_swap": (WHITE, WHITE),
        "before_swap_activation": (SWAP, WHITE),
        "after_swap": (WHITE, SWAP),
        "after_tag_24": (TAG24, SWAP) if target24 == 0 else (WHITE, TAG24),
        "after_restore_24": (WHITE, SWAP),
        "after_tag_26": (TAG26, SWAP) if target26 == 0 else (WHITE, TAG26),
        "after_restore_26": (WHITE, SWAP),
    }
    mapping = (
        "fixed_bank" if (target24, target26) == (0, 1)
        else "role_based_current_0x24_base_0x26"
    )
    lines = [
        "[epaper] ram_command_target_r8 start frame_bytes=5000 read_bytes=5001 dummy_bytes=1 tag_bytes=16 tag_x=10-11 tag_y=96-103 selectors=2 repeats=2 swap_activations=1 controls_ff=1 refresh_20=1 post_tag_activations=0 writes_24=3 writes_26=2 hard_resets=1 retries=0",
        "[epaper] ram_command_target_r8 action=known_swap control=0xFF refresh=0x20 busy_complete=1 elapsed_ms=447 activation_count=1",
    ]
    for stage, pair in stages.items():
        for selector, value in enumerate(pair):
            for repeat in (1, 2):
                raw = bytes([0]) + value
                lines.append(
                    f"[epaper] ram_command_target_r8 read stage={stage} selector={selector} "
                    f"repeat={repeat} len=5001 read_ok=1 repeat_ok=1 data={raw.hex().upper()} "
                    "gpio_restore=1 sda=0 sck=0 cs=1"
                )
    for command, target in ((0x24, target24), (0x26, target26)):
        changed = "1 changed1=0" if target == 0 else "0 changed1=1"
        lines.append(
            f"[epaper] ram_command_target_r8 probe command=0x{command:02X} "
            f"target_selector={target} changed0={changed} restored=1 activation_after_tag=0"
        )
    lines.append(
        f"[epaper] ram_command_target_r8 result=ok mapping={mapping} target24={target24} "
        f"target26={target26} stages=7 selector_reads=28 writes_24=3 writes_26=2 "
        "swap_activations=1 post_tag_activations=0 controls_ff=1 refresh_20=1 "
        "hard_resets=1 retries=0 gpio_restore=1 sda=0 sck=0 cs=1"
    )
    return "\n".join(lines)


def self_test() -> int:
    positive_fixed = evaluate(fixture())
    positive_role = evaluate(fixture(1, 0))
    missing = evaluate(fixture().replace(
        next(line for line in fixture().splitlines() if "stage=after_tag_24 selector=0 repeat=2" in line),
        "",
        1,
    ))
    repeat_bad = evaluate(fixture().replace("repeat=2 len=5001 read_ok=1 repeat_ok=1", "repeat=2 len=5001 read_ok=1 repeat_ok=0", 1))
    post_activation = evaluate(fixture().replace("post_tag_activations=0", "post_tag_activations=1", 1))
    outside = bytearray(TAG24)
    outside[0] = 0x00
    outside_bad = evaluate(fixture().replace(TAG24.hex().upper(), bytes(outside).hex().upper(), 1))
    restore_bad = evaluate(fixture().replace("after_restore_24", "after_tag_24", 1))
    ambiguous = evaluate(fixture(0, 0))
    equal_tags = evaluate(fixture().replace(TAG26.hex().upper(), TAG24.hex().upper()))
    cases = (
        positive_fixed["status"] == "PASS_MACHINE_R8_COMMAND_TARGET_MAPPING",
        positive_role["status"] == "PASS_MACHINE_R8_COMMAND_TARGET_MAPPING",
        missing["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
        repeat_bad["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
        post_activation["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
        outside_bad["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
        restore_bad["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
        ambiguous["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
        equal_tags["status"] == "NO_GO_R8_COMMAND_TARGET_MAPPING",
    )
    ok = all(cases)
    print("PASS: R8 parser fixed/role and negative fixture matrix" if ok else "FAIL: R8 parser fixture matrix")
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
    result = evaluate(args.log.read_text(encoding="utf-8", errors="replace"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "PASS_MACHINE_R8_COMMAND_TARGET_MAPPING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
