#!/usr/bin/env python3
"""Machine oracle for the supplier-exact dual-plane all-White BaseMap clean."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
READ_RE = re.compile(
    r"\[epaper\] dual_plane_white_clean read selector=([01]) command_bank=(0x24|0x26) "
    r"repeat=([12]) len=5001 window_reprogrammed=1 counter_reprogrammed=1 read_ok=1 "
    r"data=([0-9A-F]{10002}) gpio_restore=1 sda=0 sck=0 cs=1"
)


def evaluate(text: str) -> dict[str, object]:
    errors: list[str] = []
    start = (
        "dual_plane_white_clean start "
        f"source_sha256={SOURCE_SHA} frame_bytes=5000 writes_24=1 writes_26=1 "
        "order=0x24_then_0x26 control=0xF7 refresh=0x20 selectors=2 repeats=2 "
        "read_bytes=5001 dummy_bytes=1 hard_resets=1 retries=0"
    )
    action_re = re.compile(
        r"dual_plane_white_clean action=basemap bytes_24=5000 bytes_26=5000 "
        r"order=0x24_then_0x26 control=0xF7 refresh=0x20 busy_complete=1 "
        r"busy_elapsed_ms=(\d+) source_exact=1"
    )
    result = (
        "dual_plane_white_clean result=ok writes_24=1 writes_26=1 bytes_each=5000 "
        "controls_f7=1 refresh_20=1 busy_completions=1 selector_reads=4 "
        "window_reprograms=4 counter_reprograms=4 retries=0 gpio_restore=1 sda=0 sck=0 cs=1"
    )
    if text.count(start) != 1:
        errors.append("single source-bound dual-plane start marker missing")
    actions = action_re.findall(text)
    if len(actions) != 1:
        errors.append("single 0x24/0x26/F7/20/BUSY action marker missing")
    elif not 0 < int(actions[0]) <= 5000:
        errors.append(f"BUSY elapsed is outside the 1..5000 ms bound: {actions[0]}")
    if text.count(result) != 1:
        errors.append("dual-plane final count/GPIO marker missing")

    reads: list[dict[str, object]] = []
    for match in READ_RE.finditer(text):
        selector = int(match.group(1))
        bank = match.group(2)
        repeat = int(match.group(3))
        response = bytes.fromhex(match.group(4))
        reads.append({
            "selector": selector,
            "bank": bank,
            "repeat": repeat,
            "dummy_hex": f"{response[0]:02X}",
            "response_sha256": hashlib.sha256(response).hexdigest().upper(),
            "payload_sha256": hashlib.sha256(response[1:]).hexdigest().upper(),
            "payload_all_white": response[1:] == bytes([0xFF]) * 5000,
        })
    expected_order = [(0, "0x24", 1), (0, "0x24", 2),
                      (1, "0x26", 1), (1, "0x26", 2)]
    observed_order = [(int(row["selector"]), str(row["bank"]), int(row["repeat"]))
                      for row in reads]
    if observed_order != expected_order:
        errors.append(f"selector/repeat order differs: {observed_order}")
    if len(reads) == 4:
        if not all(bool(row["payload_all_white"]) for row in reads):
            errors.append("one or more selector payloads are not 5000-byte all-white")
        if reads[0]["response_sha256"] != reads[1]["response_sha256"]:
            errors.append("selector 0 repeated response differs")
        if reads[2]["response_sha256"] != reads[3]["response_sha256"]:
            errors.append("selector 1 repeated response differs")
    else:
        errors.append(f"expected four reads, got {len(reads)}")

    status = (
        "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE"
        if not errors
        else "NO_GO_DUAL_PLANE_WHITE_CLEAN"
    )
    return {
        "schema_id": "companion.wb55.ssd1681_dual_plane_white_clean_trace.v1",
        "status": status,
        "errors": errors,
        "contract": {
            "source_sha256": SOURCE_SHA,
            "write_order": ["0x24", "0x26"],
            "bytes_per_plane": 5000,
            "control": "0xF7",
            "refresh": "0x20",
            "selectors": {"0": "0x24", "1": "0x26"},
            "repeats_per_selector": 2,
            "read_bytes": 5001,
            "payload_bytes": 5000,
            "window_and_counter_reprogrammed_before_every_read": True,
        },
        "observed": {
            "busy_elapsed_ms": int(actions[0]) if len(actions) == 1 else None,
            "reads": reads,
        },
        "hardware_contact": 1,
        "production_allowed": False,
    }


def fixture() -> str:
    response = "00" + "FF" * 5000
    lines = [
        f"[epaper] dual_plane_white_clean start source_sha256={SOURCE_SHA} frame_bytes=5000 writes_24=1 writes_26=1 order=0x24_then_0x26 control=0xF7 refresh=0x20 selectors=2 repeats=2 read_bytes=5001 dummy_bytes=1 hard_resets=1 retries=0",
        "[epaper] dual_plane_white_clean action=basemap bytes_24=5000 bytes_26=5000 order=0x24_then_0x26 control=0xF7 refresh=0x20 busy_complete=1 busy_elapsed_ms=1289 source_exact=1",
    ]
    for selector, bank in ((0, "0x24"), (1, "0x26")):
        for repeat in (1, 2):
            lines.append(
                f"[epaper] dual_plane_white_clean read selector={selector} command_bank={bank} repeat={repeat} len=5001 window_reprogrammed=1 counter_reprogrammed=1 read_ok=1 data={response} gpio_restore=1 sda=0 sck=0 cs=1"
            )
    lines.append(
        "[epaper] dual_plane_white_clean result=ok writes_24=1 writes_26=1 bytes_each=5000 controls_f7=1 refresh_20=1 busy_completions=1 selector_reads=4 window_reprograms=4 counter_reprograms=4 retries=0 gpio_restore=1 sda=0 sck=0 cs=1"
    )
    return "\n".join(lines)


def self_test() -> int:
    good = fixture()
    corrupt = good.replace("00" + "FF" * 5000, "00FE" + "FF" * 4999, 1)
    second_marker = "repeat=2 len=5001"
    inconsistent = good.replace(second_marker, "repeat=2 len=5001", 1)
    first = inconsistent.find(second_marker)
    data = inconsistent.find("data=", first)
    inconsistent = inconsistent[:data + 5] + "01" + inconsistent[data + 7:]
    cases = {
        "missing_0x26": good.replace("writes_26=1", "writes_26=0", 1),
        "missing_selector_repeat": good.replace("selector=1 command_bank=0x26 repeat=2", "selector=1 command_bank=0x26 other=2", 1),
        "nonwhite_payload": corrupt,
        "repeat_mismatch": inconsistent,
        "busy_timeout": good.replace("busy_elapsed_ms=1289", "busy_elapsed_ms=5001", 1),
        "missing_post_sequence_marker": good.replace("result=ok", "result=no_go", 1),
    }
    ok = evaluate(good)["status"].startswith("PASS_") and all(
        evaluate(value)["status"].startswith("NO_GO_") for value in cases.values()
    )
    print(
        "PASS: dual-plane White parser positive/missing-0x26/read/nonwhite/repeat fixtures"
        if ok else
        "FAIL: dual-plane White parser self-test"
    )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--pattern")
    parser.add_argument("--source-audit", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.log is None or args.out is None:
        parser.error("--log and --out are required unless --self-test is used")
    result = evaluate(args.log.read_text(encoding="utf-8", errors="ignore"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if str(result["status"]).startswith("PASS_") else 1


if __name__ == "__main__":
    sys.exit(main())
