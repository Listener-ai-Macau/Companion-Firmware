#!/usr/bin/env python3
"""Verify the WB55 SSD1681 differential-to-maintenance hardware sequence."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / (
    ".cache/validation/screen-revision21-maintenance-runtime-ready-gated/"
    "nucleo-serial-raw.log"
)
DEFAULT_PRODUCTION_LOG = ROOT / (
    ".cache/validation/screen-revision21-normal-restored/"
    "nucleo-serial-raw.log"
)


def resolve_log(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def require_in_order(text: str, markers: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    cursor = 0
    for marker in markers:
        position = text.find(marker, cursor)
        if position < 0:
            errors.append(f"missing ordered marker: {marker}")
            continue
        cursor = position + len(marker)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--production-log", type=Path, default=DEFAULT_PRODUCTION_LOG)
    args = parser.parse_args()

    log_path = resolve_log(args.log)
    if not log_path.is_file():
        print(f"epaper differential maintenance runtime: FAIL\n  - missing log: {log_path}")
        return 1

    text = log_path.read_text(encoding="utf-8", errors="replace")
    start = text.rfind("[screen] maintenance_diagnostic start delay_ms=")
    if start < 0:
        print("epaper differential maintenance runtime: FAIL")
        print("  - missing maintenance diagnostic start marker")
        return 1
    run = text[start:]
    errors = require_in_order(
        run,
        (
            "[screen] maintenance_diagnostic start delay_ms=3500",
            "policy requested=3 selected=differential reason=1 partial_count=0",
            "refresh mode=differential control=0xFC",
            "policy_commit mode=differential ok=1 partial_count=1 baseline=1",
            "[screen] maintenance_diagnostic enqueue=1",
            "policy requested=4 selected=maintenance reason=5 partial_count=1",
            "refresh mode=maintenance control=0xCF",
            "policy_commit mode=maintenance ok=1 partial_count=0 baseline=1",
        ),
    )
    if not re.search(
        r"refresh mode=differential control=0xFC.*complete=1 elapsed_ms=[1-9][0-9]*",
        run,
    ):
        errors.append("differential refresh did not complete")
    if not re.search(
        r"refresh mode=maintenance control=0xCF.*complete=1 elapsed_ms=[1-9][0-9]*",
        run,
    ):
        errors.append("maintenance refresh did not complete")
    failures = re.findall(r"(?im)^.*(?:complete=0|ready=0|timeout|failed).*$", run)
    if failures:
        errors.append("failure marker(s): " + " | ".join(failures[:3]))

    production_path = resolve_log(args.production_log)
    if not production_path.is_file():
        errors.append(f"missing restored production log: {production_path}")
    else:
        production = production_path.read_text(encoding="utf-8", errors="replace")
        if "maintenance_diagnostic" in production:
            errors.append("restored production firmware still contains diagnostic output")
        for marker in (
            "[screen] core_selftest menu=pass gesture=pass presentation=pass",
            "refresh mode=full control=0xF7",
            "tuning=1 threshold=0x90 active_period=4 monitor_period=4",
        ):
            if marker not in production:
                errors.append(f"restored production log missing: {marker}")

    if errors:
        print("epaper differential maintenance runtime: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    differential_ms = re.search(
        r"refresh mode=differential control=0xFC.*elapsed_ms=(\d+)", run
    )
    maintenance_ms = re.search(
        r"refresh mode=maintenance control=0xCF.*elapsed_ms=(\d+)", run
    )
    print("epaper differential maintenance runtime: PASS")
    print(f"  evidence: {log_path}")
    print(f"  differential: 0xFC complete in {differential_ms.group(1)} ms")
    print(f"  cleanup: 0xCF complete in {maintenance_ms.group(1)} ms")
    print(f"  restored production evidence: {production_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
