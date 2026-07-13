#!/usr/bin/env python3
"""Keep Companion's focused acceptance inventory durable and complete."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "docs" / "companion_function_acceptance_coverage.md"
REQUIRED_ITEMS = tuple(f"ACPT-{number:02d}" for number in range(1, 14))
REQUIRED_SHARED_ANCHORS = (
    "exactly one Chinese popup at a time",
    "N/13",
    "normal",
    "Failure/recovery",
    "Machine evidence",
    "Popup:",
    "COMP-REQ-009",
    "COMP-REQ-007",
    "STM32WBA55/WBA65",
    "low_power_face request=sleepy animation=static",
    "periodic sleep-frame flicker",
)


def main() -> int:
    text = COVERAGE.read_text(encoding="utf-8") if COVERAGE.exists() else ""
    errors = [f"missing acceptance coverage anchor: {anchor}" for anchor in REQUIRED_SHARED_ANCHORS if anchor not in text]
    for item in REQUIRED_ITEMS:
        if text.count(f"### {item}:") != 1:
            errors.append(f"acceptance item {item} must have exactly one heading")
    if errors:
        print("FAIL: Companion function acceptance coverage")
        for error in errors:
            print(f" - {error}")
        return 1
    print("PASS: Companion function acceptance coverage contains 13 focused items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
