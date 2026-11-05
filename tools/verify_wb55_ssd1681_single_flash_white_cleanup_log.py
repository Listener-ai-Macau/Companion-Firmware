"""Offline parser and negative fixtures for COMP-REQ-409."""
from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED = {
    "window": "x0-199,y0-199",
    "frame_bytes": 5000,
    "writes_24": 1,
    "writes_26": 1,
    "control": "0xFF",
    "refresh": "0x20",
    "busy_waits": 1,
}


def parse(text: str) -> dict[str, object]:
    if "single_flash_white_cleanup start" not in text:
        raise ValueError("missing start")
    if "window=logical_x0-24,logical_y0-199 controller_y199-0" not in text or "frame_bytes=5000" not in text:
        raise ValueError("wrong full-screen window or frame size")
    if "reset_ms=10+10" not in text:
        raise ValueError("reset is not the frozen 10/10 reset")
    if text.count("writes_24=1") != 1 or text.count("writes_26=1") != 1:
        raise ValueError("write counts are not bound")
    if "bytes_24=5000" not in text or "bytes_26=5000" not in text or "white=1" not in text:
        raise ValueError("White payload size/fill mismatch")
    if "mode=otp_mode2" not in text or "control=0xFF" not in text:
        raise ValueError("not OTP Mode2")
    if not re.search(r"result=ok\s+activation=1", text):
        raise ValueError("cleanup did not report successful activation")
    if "refresh=0x20" not in text or "busy_waits=1" not in text:
        raise ValueError("activation telemetry mismatch")
    forbidden = ("0xF7", "0xC7", "0x32", "custom_lut", "second_activation", "retry=1", "retries=1", "maintenance=1")
    if any(token in text for token in forbidden):
        raise ValueError("forbidden activation marker")
    result = re.search(r"result=ok .*busy_elapsed_ms=(\d+)", text)
    if not result:
        raise ValueError("missing successful result")
    return {**EXPECTED, "busy_elapsed_ms": int(result.group(1)), "hardware_contact": 0}


def self_test() -> dict[str, object]:
    good = (
        "[epaper] single_flash_white_cleanup start window=logical_x0-24,logical_y0-199 controller_y199-0 frame_bytes=5000 "
        "mode=otp_mode2 reset_ms=10+10 writes_24=1 writes_26=1 retries=0 maintenance=0\n"
        "[epaper] single_flash_white_cleanup result=ok activation=1 control=0xFF refresh=0x20 "
        "busy_waits=1 reset_elapsed_ms=20 busy_elapsed_ms=443 bytes_24=5000 bytes_26=5000 white=1 forbidden=0 retries=0 maintenance=0\n"
    )
    parse(good)
    negatives = {
        "missing_24": good.replace("writes_24=1", "writes_24=0", 1),
        "wrong_bytes": good.replace("bytes_24=5000", "bytes_24=4999"),
        "non_white": good.replace("white=1", "white=0"),
        "wrong_window": good.replace("controller_y199-0", "controller_y127-22"),
        "wrong_reset": good.replace("reset_ms=10+10", "reset_ms=100+100"),
        "old_mode1": good.replace("control=0xFF", "control=0xF7"),
        "busy_failure": good.replace("result=ok activation=1", "result=no_go activation=0"),
        "incomplete_activation": good.replace("activation=1", "activation=0", 1),
        "incomplete_writes": good.replace("bytes_26=5000", "bytes_26=0"),
        "second_activation": good + " second_activation=1",
        "retry": good.replace("retries=0", "retries=1", 1),
        "maintenance": good.replace("maintenance=0", "maintenance=1", 1),
    }
    rejected = {}
    for name, fixture in negatives.items():
        try:
            parse(fixture)
        except ValueError:
            rejected[name] = True
        else:
            rejected[name] = False
    if not all(rejected.values()):
        raise AssertionError(rejected)
    return {"positive": True, "negative": rejected}


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(self_test())
    else:
        print(parse(Path(sys.argv[1]).read_text(encoding="utf-8")))
