#!/usr/bin/env python3
"""Render Companion pendant e-paper golden fixtures."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import (  # noqa: E402
    CARD_STATES,
    CARD_TYPES,
    DISPLAY_VARIANTS,
    EXPRESSION_KINDS,
    card_from_ble_write,
    default_fixture_cards,
    render_card,
    required_state_cards,
    sha256_hex,
)


DEFAULT_OUTPUT_DIR = pathlib.Path("docs/validation/epaper")
DEFAULT_MANIFEST = pathlib.Path("docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json")
SCHEMA_ID = "companion.pendant.epaper_fixtures.v1"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_fixture(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build_manifest(out_dir: pathlib.Path) -> dict[str, Any]:
    fixtures: list[dict[str, Any]] = []
    for card in default_fixture_cards():
        for variant in DISPLAY_VARIANTS.values():
            data = render_card(card, variant)
            path = out_dir / f"{card.card_id}_{variant.key.replace('.', '_')}.pbm"
            write_fixture(path, data)
            fixtures.append(
                {
                    "id": card.card_id,
                    "variant": variant.key,
                    "path": rel(path),
                    "width": variant.width,
                    "height": variant.height,
                    "sha256": sha256_hex(data),
                    "card": card.as_manifest(),
                }
            )

    ble_card = card_from_ble_write(
        {
            "request_id": 42,
            "card_slot": 2,
            "utf8_title_len": 5,
            "utf8_body_len": 18,
            "title": "Event card",
            "body": "BLE mapped payload",
            "display_flags": 0x02,
        }
    )
    state_cards = list(required_state_cards())
    return {
        "schema_id": SCHEMA_ID,
        "fixtures": fixtures,
        "display_variants": {
            key: {
                "width": variant.width,
                "height": variant.height,
                "label": variant.label,
                "format": "PBM P4 1-bit monochrome",
            }
            for key, variant in DISPLAY_VARIANTS.items()
        },
        "supported_card_types": sorted(CARD_TYPES),
        "supported_expressions": sorted(EXPRESSION_KINDS),
        "supported_states": sorted(CARD_STATES),
        "state_card_coverage": sorted({card.card_type for card in state_cards}),
        "state_coverage": sorted({card.state for card in state_cards}),
        "text_fallback": {
            "ascii_font": "built-in 5x7",
            "unsupported_unicode": "deterministic codepoint placeholder boxes",
        },
        "dithering": "deterministic 4x4 Bayer thresholding",
        "ble_card_write_mapping": ble_card.as_manifest(),
        "hardware_boundary": {
            "ai_testable_now": [
                "card model",
                "ExpressionV1 state model",
                "expression golden fixtures",
                "text fallback",
                "dithering",
                "framebuffer dimensions",
                "PBM bitmap export",
            ],
            "deferred_to_hardware_gates": [
                "real e-paper SPI timing",
                "busy-pin handling",
                "refresh waveform validation",
            ],
        },
    }


def run_self_test(manifest_path: pathlib.Path, out_dir: pathlib.Path) -> dict[str, Any]:
    manifest = build_manifest(out_dir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if len(manifest["fixtures"]) < 3:
        raise AssertionError("expected at least three golden fixtures")
    if {"2.13in", "1.54in"} - set(manifest["display_variants"]):
        raise AssertionError("missing required display variants")
    required_cards = {"boot_default", "recording", "sync_complete"}
    required_expression_cards = {f"expression_{expression}" for expression in EXPRESSION_KINDS}
    fixture_ids = {fixture["id"] for fixture in manifest["fixtures"]}
    if not required_cards <= fixture_ids:
        raise AssertionError(f"missing fixture cards: {sorted(required_cards - fixture_ids)}")
    if not required_expression_cards <= fixture_ids:
        raise AssertionError(f"missing expression fixture cards: {sorted(required_expression_cards - fixture_ids)}")

    required_types = {
        "expression",
        "mood",
        "name",
        "event",
        "reminder",
        "recording",
        "sync_complete",
        "low_battery",
        "error",
    }
    if not required_types <= set(manifest["state_card_coverage"]):
        raise AssertionError("card model coverage is incomplete")
    if not EXPRESSION_KINDS <= set(manifest["supported_expressions"]):
        raise AssertionError("expression model coverage is incomplete")
    if manifest["ble_card_write_mapping"]["card_type"] != "event":
        raise AssertionError("BLE CardWriteV1 fixture did not map to event card")

    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Render fixtures and validate coverage.")
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="Print the manifest JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.self_test:
        print("Use --self-test to generate the Companion e-paper golden fixtures.")
        return 0

    manifest = run_self_test(REPO_ROOT / args.manifest, REPO_ROOT / args.out_dir)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(
            "PASS: rendered Companion e-paper fixtures -> "
            f"{args.manifest.as_posix()} ({len(manifest['fixtures'])} PBM files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
