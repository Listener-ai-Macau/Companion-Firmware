#!/usr/bin/env python3
"""Verify the r38 inverse-F7/discharge/white-F7/target-C7 LP sequence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = args.source.read_text(encoding="utf-8")
    start = text.index("static bool ssd1681_lp_white_then_sleepy_f7(")
    end = text.index("\n/* Product LP boundary:", start)
    body = text[start:end]
    inverse = body.index("s_frame[index] = (uint8_t)~mapped_sleepy[index]")
    first_f7 = body.index("s_frame, &window, &total_busy_ms, 0xF7u")
    discharge = body.index("ssd1681_lp_sleep2s_reinit(&window, NULL)")
    white = body.index("memset(s_frame, 0xFFu, SSD1681_FRAME_BYTES)")
    second_f7 = body.index("s_frame, &window, &total_busy_ms, 0xF7u", first_f7 + 1)
    target_c7 = body.index("mapped_sleepy, &window, &total_busy_ms, 0xC7u")
    checks = {
        "ordered_inverse_discharge_white_target": (
            inverse < first_f7 < discharge < white < second_f7 < target_c7),
        "two_current_only_f7_stages": (
            body.count("0xF7u, false, false") == 2),
        "one_target_c7": body.count("0xC7u") == 1,
        "two_second_discharge_dwell": "d=2000" in body,
        "no_post_target_mode2_rearm": "ssd1681_accepted_mode2_rearm" not in body,
        "frozen_receipt": "c=F7F7C7" in body and "m2=0 frozen=%u" in body,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_inverse_white_target_static.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "checks": checks,
        "failed_checks": failed,
        "source": str(args.source.resolve()),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest().upper(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
