#!/usr/bin/env python3
"""Declare which portable pet scenes have a v9 candidate and which need art."""

from __future__ import annotations

import argparse
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200"
MANIFEST = ART_DIR / "v9-expression-cemp-manifest.json"
OUTPUT = ART_DIR / "v9-scene-resource-coverage.json"
SOURCE_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"


AVAILABLE = "CANDIDATE_AVAILABLE_NOT_ACTIVE"
PENDING = "PENDING_VISUAL_BASELINE"
PENDING_MENU = "PENDING_MENU_VISUAL_BASELINE"


# This table is intentionally exhaustive for the portable performance layer.
# A pending entry means no fallback image may be selected for that visible scene.
COVERAGE = (
    ("daily.idle", AVAILABLE, "idle", "v9 idle calm"),
    ("daily.tap", AVAILABLE, "touch", "v9 curious tap"),
    ("daily.stroke", AVAILABLE, "touch", "v9 curious tap is the only approved gentle-touch candidate"),
    ("daily.swipe_left", AVAILABLE, "swipe_left", "v9 left gesture"),
    ("daily.swipe_right", AVAILABLE, "swipe_right", "v9 right gesture"),
    ("daily.swipe_up", AVAILABLE, "swipe_up", "v9 up gesture"),
    ("daily.swipe_down", AVAILABLE, "swipe_down", "v9 down gesture"),
    ("voice.listening", AVAILABLE, "listening", "v9 sound-arc listening"),
    ("voice.speaking", PENDING, None, "requires a v9-derived speaking source"),
    ("menu.hold", AVAILABLE, "menu_hold", "v9 hold/decision"),
    ("menu.enter", AVAILABLE, "menu_hold", "v9 hold/decision supplies only the entry handoff"),
    ("menu.open", PENDING_MENU, None, "requires the separately approved four-root menu visual source"),
    ("menu.select", AVAILABLE, "menu_hold", "v9 decision supplies only the committed selection handoff"),
    ("menu.blocked", PENDING, None, "requires a v9-derived blocked-state source"),
    ("menu.exit", PENDING, None, "requires a v9-derived exit-state source"),
    ("recording.start", AVAILABLE, "recording", "v9 record-dot entry"),
    ("recording.active", AVAILABLE, "recording", "v9 record-dot active"),
    ("recording.saving", AVAILABLE, "saving", "v9 dot-trail saving"),
    ("recording.saved", AVAILABLE, "saved", "v9 sparkle saved"),
    ("recording.error", PENDING, None, "requires a v9-derived recording-error source"),
    ("power.sleep_entry", AVAILABLE, "sleep", "v9 moon and Z sleep"),
    ("power.deep_sleep", AVAILABLE, "sleep", "v9 static sleep keyframe"),
    ("power.wake", AVAILABLE, "wake", "v9 sleep-to-idle-to-curious handoff"),
    ("power.charge_detected", PENDING, None, "requires a v9-derived charge-detected source"),
    ("power.charging", PENDING, None, "requires a v9-derived charging source"),
    ("power.charged", PENDING, None, "requires a v9-derived charged source"),
    ("power.low_battery", PENDING, None, "requires a v9-derived low-battery source"),
    ("link.pairing", PENDING, None, "requires a v9-derived pairing source"),
    ("link.connected", PENDING, None, "requires a v9-derived connected source"),
    ("link.syncing", PENDING, None, "requires a v9-derived syncing source"),
    ("link.synced", PENDING, None, "requires a v9-derived synced source"),
    ("link.error", PENDING, None, "requires a v9-derived link-error source"),
    ("upgrade.offer", PENDING, None, "requires a v9-derived upgrade-offer source; OTA remains frozen"),
    ("upgrade.prepare", PENDING, None, "requires a v9-derived upgrade-prepare source; OTA remains frozen"),
    ("upgrade.transfer", PENDING, None, "requires a v9-derived upgrade-transfer source; OTA remains frozen"),
    ("upgrade.verify", PENDING, None, "requires a v9-derived upgrade-verify source; OTA remains frozen"),
    ("upgrade.restart", PENDING, None, "requires a v9-derived upgrade-restart source; OTA remains frozen"),
    ("upgrade.success", PENDING, None, "requires a v9-derived upgrade-success source; OTA remains frozen"),
    ("upgrade.error", PENDING, None, "requires a v9-derived upgrade-error source; OTA remains frozen"),
    ("system.error", PENDING, None, "requires a v9-derived system-error source"),
)


def build() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    clips = {clip["name"] for clip in manifest["clips"]}
    entries = []
    for family, status, clip, note in COVERAGE:
        if clip is not None and clip not in clips:
            raise ValueError(f"coverage references missing candidate clip {clip!r}")
        entries.append(
            {
                "resource_family": family,
                "status": status,
                "candidate_clip": clip,
                "source_sha256": SOURCE_SHA256 if clip is not None else None,
                "note": note,
            }
        )
    return {
        "schema": "companion.v9_scene_resource_coverage.v1",
        "status": "PASS_EXHAUSTIVE_NO_LEGACY_FALLBACK",
        "source_sha256": SOURCE_SHA256,
        "candidate_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "candidate_runtime_resource_activated": False,
        "policy": "A pending scene has no visual fallback. It must receive a separately recorded v9-derived source before it can render.",
        "available_candidate_count": sum(entry["candidate_clip"] is not None for entry in entries),
        "pending_visual_baseline_count": sum(entry["candidate_clip"] is None for entry in entries),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    coverage = build()
    if args.write:
        OUTPUT.write_text(json.dumps(coverage, indent=2) + "\n", encoding="ascii")
    print(
        "PASS: v9 scene coverage keeps "
        f"{coverage['available_candidate_count']} candidate mappings and "
        f"{coverage['pending_visual_baseline_count']} explicit no-fallback gaps."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
