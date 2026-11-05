#!/usr/bin/env python3
"""Verify the inactive v9 scene-to-CEMP metadata binding stays exhaustive."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
COVERAGE = REPO_ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-scene-resource-coverage.json"
MANIFEST = REPO_ROOT / "docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json"
BINDING_HEADER = REPO_ROOT / "app/companion_pendant/epaper/v9_candidate_resource_binding.h"
BINDING_SOURCE = REPO_ROOT / "app/companion_pendant/epaper/v9_candidate_resource_binding.c"
OUTPUT = REPO_ROOT / "docs/validation/companion-v9-candidate-resource-binding-20260717.json"

EXPECTED_AVAILABLE = {
    "daily.idle": "idle",
    "daily.tap": "touch",
    "daily.stroke": "touch",
    "daily.swipe_left": "swipe_left",
    "daily.swipe_right": "swipe_right",
    "daily.swipe_up": "swipe_up",
    "daily.swipe_down": "swipe_down",
    "voice.listening": "listening",
    "menu.hold": "menu_hold",
    "menu.enter": "menu_hold",
    "menu.select": "menu_hold",
    "recording.start": "recording",
    "recording.active": "recording",
    "recording.saving": "saving",
    "recording.saved": "saved",
    "power.sleep_entry": "sleep",
    "power.deep_sleep": "sleep",
    "power.wake": "wake",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_result() -> tuple[dict[str, object], list[str]]:
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    binding_header = BINDING_HEADER.read_text(encoding="utf-8")
    binding_source = BINDING_SOURCE.read_text(encoding="utf-8")
    errors: list[str] = []
    entries = coverage.get("entries", [])
    available = {
        entry.get("resource_family"): entry.get("candidate_clip")
        for entry in entries
        if entry.get("status") == "CANDIDATE_AVAILABLE_NOT_ACTIVE"
    }
    pending = [
        entry.get("resource_family")
        for entry in entries
        if entry.get("status") in {"PENDING_VISUAL_BASELINE", "PENDING_MENU_VISUAL_BASELINE"}
    ]

    check(coverage.get("status") == "PASS_EXHAUSTIVE_NO_LEGACY_FALLBACK",
          "coverage is not a no-fallback pass", errors)
    check(len(entries) == 40, "coverage must list all 40 pet-performance scene families", errors)
    check(available == EXPECTED_AVAILABLE, "candidate scene map differs from the locked v9 coverage", errors)
    check(len(pending) == 22, "pending scene count must remain 22", errors)
    check(manifest.get("revision") == 90, "v9 candidate pack revision must remain 90", errors)
    check(manifest.get("provenance", {}).get("runtime_resource_activated") is False,
          "v9 candidate manifest must remain inactive", errors)
    for token in (
        "comp_v9_candidate_resource_resolve",
        "COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE",
        "COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE",
        "COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE",
        "runtime_activation_allowed",
        "comp_v9_candidate_resource_pack_identity_matches",
    ):
        check(token in binding_header + binding_source,
              f"v9 portable binding is missing {token}", errors)
    for token in (
        "comp_emote_asset_pack_mount",
        "comp_asset_store_",
        "comp_epaper_display_queue_",
        "companion_epaper_panel_",
        "HAL_",
        "STM32",
        "GPIO",
        "SPI",
        "I2C",
    ):
        check(token not in binding_header + binding_source,
              f"v9 portable binding must not contain activation/platform token {token}", errors)

    result: dict[str, object] = {
        "schema": "companion.v9_candidate_resource_binding_validation.v1",
        "status": "PASS_MACHINE_ONLY_INACTIVE" if not errors else "FAIL",
        "candidate_pack": {
            "name": manifest.get("name"),
            "revision": manifest.get("revision"),
            "runtime_resource_activated": manifest.get("provenance", {}).get("runtime_resource_activated"),
            "manifest_sha256": sha256(MANIFEST),
        },
        "scene_coverage": {
            "total": len(entries),
            "available_not_active": len(available),
            "pending_visual_baseline": len(pending),
            "available_map": EXPECTED_AVAILABLE,
        },
        "portable_selector": {
            "header": BINDING_HEADER.relative_to(REPO_ROOT).as_posix(),
            "source": BINDING_SOURCE.relative_to(REPO_ROOT).as_posix(),
            "runtime_activation_allowed": False,
            "forbidden_fallbacks": ["legacy", "rescue", "procedural", "unrelated_art"],
        },
        "limits": [
            "This verifier does not mount or select a CEMP pack.",
            "This verifier does not read or write external Flash.",
            "This verifier does not queue, render, refresh, flash, or inspect a panel.",
            "The four-root menu visual source is still pending and menu.open has no fallback.",
        ],
        "errors": errors,
    }
    return result, errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the validation JSON.")
    args = parser.parse_args(argv)
    result, errors = build_result()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: v9 candidate resource binding is exhaustive, portable, and inactive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
