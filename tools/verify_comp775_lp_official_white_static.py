#!/usr/bin/env python3
"""Fail closed unless LP uses normal-full white F7 then fast Mode-1 target C7."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    white_f7 = body.index("s_frame, &window, &total_busy_ms, 0xF7u")
    target_c7 = body.index("mapped_sleepy, &window, &total_busy_ms, 0xC7u")
    profile_positions = [m.start() for m in re.finditer(
        r"ssd1681_prepare_vendor_fast_profile\(\)", body)]
    checks = {
        "one_white_f7": body.count("0xF7u") == 1,
        "one_target_c7": body.count("0xC7u") == 1,
        "white_f7_precedes_target_c7": white_f7 < target_c7,
        "white_f7_has_no_fast_profile_before_it": not any(
            position < white_f7 for position in profile_positions),
        "target_c7_has_exactly_one_fast_profile_before_it": (
            len(profile_positions) == 1 and white_f7 < profile_positions[0] < target_c7),
        "white_is_current_only": "0xF7u, false, false" in body,
        "target_uses_white_old_plane": (
            "ssd1681_write_plane_region(0x26u, s_frame, &window)" in body),
        "target_is_current_only_c7": "0xC7u, false, false" in body,
        "two_visible_activations_reported": (
            'printf("[e] lp2 n=1 ' in body),
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_official_white_static.v1",
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
