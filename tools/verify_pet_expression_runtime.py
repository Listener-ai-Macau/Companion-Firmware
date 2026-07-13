#!/usr/bin/env python3
"""Verify a WB55 serial capture for the quiet-idle procedural pet renderer."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"


def default_log() -> pathlib.Path:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    runtime = evidence.get("runtime_evidence", {})
    value = runtime.get("normal_raw_log")
    if not isinstance(value, str) or not value:
        raise ValueError("companion-screen-bilingual-menu-wb55.json is missing runtime_evidence.normal_raw_log")
    return pathlib.Path(value)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.log is None:
        args.log = default_log()
    path = ROOT / args.log
    if not path.is_file():
        print(f"pet expression runtime: FAIL\n  - missing log: {path}")
        return 1
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for marker in (
        "[screen] pet_behavior_selftest=pass",
        "[screen] pet_behavior_selftest=pass failure_code=0",
        "[pet-emotion] selftest=pass failure_code=0 moods=calm,curious,affectionate,delighted,restful,worried memory=pass",
        "[pet-emotion] boot mood=",
        "attachment=",
        "traits=",
        "strokes=pass",
    ):
        if marker not in raw_text:
            errors.append(f"missing startup marker: {marker}")
    text = raw_text
    boot_marker = "[stage] ble app init requested"
    boot_index = text.rfind(boot_marker)
    if boot_index < 0:
        errors.append(f"missing marker: {boot_marker}")
    else:
        text = text[boot_index:]
    for marker in (
        "[screen] pet_expression_selftest=pass",
        "[screen-assets] pack=emote-matrix-white-200x200-v1 revision=47 clips=33 frames=159",
        "[pet-renderer] clip=idle frame=0 in_clip=0",
        "source=external_flash",
        "[epaper] scene=expression name=idle frame_index=0",
        "dirty=8,18,184,166 source=external_flash",
        "[pet-renderer] idle_frame_suppressed frame=1 in_clip=1",
        "[pet-renderer] idle_frame_suppressed frame=2 in_clip=2",
        "[touch-health] detected=1",
        "buffered=0 dropped=0",
        "wait_buffer_selftest=1",
    ):
        if marker not in text:
            errors.append(f"missing marker: {marker}")
    if text.count("refresh mode=full control=0xF7") != 1:
        errors.append("quiet-idle capture must contain exactly one boot full refresh")
    if "refresh mode=differential control=0xFC" in text:
        errors.append("quiet-idle capture must not refresh old idle timeline frames")
    if errors:
        print("pet expression runtime: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("pet expression runtime: PASS")
    print("  one boot baseline, rev47 generated-image-baseline idle clip, two suppressed legacy idle ticks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
