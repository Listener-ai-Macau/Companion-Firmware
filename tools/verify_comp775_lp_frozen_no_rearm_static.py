#!/usr/bin/env python3
"""Fail closed unless frozen LP synchronizes RAM without a Mode-2 rearm."""

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
    checks = {
        "target_rebaselines_old_plane": (
            "ssd1681_write_plane_region(0x26u, mapped_sleepy, &window)" in body),
        "target_rebaselines_current_plane": (
            "ssd1681_write_plane_region(0x24u, mapped_sleepy, &window)" in body),
        "no_mode2_rearm_after_target": (
            "ssd1681_accepted_mode2_rearm" not in body),
        "frozen_handoff_requires_rebaseline": (
            "frozen_handoff_complete = rebaseline_complete;" in body),
        "receipt_exposes_no_rearm": (
            "m2=0 frozen=%u" in body),
        "returns_frozen_handoff": (
            "return frozen_handoff_complete;" in body),
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "companion.comp_req_775.lp_frozen_no_rearm_static.v1",
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
