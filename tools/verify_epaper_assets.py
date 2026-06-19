#!/usr/bin/env python3
"""Verify Companion pendant e-paper renderer fixtures and boundaries."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import (  # noqa: E402
    CARD_STATES,
    CARD_TYPES,
    DISPLAY_VARIANTS,
    CardModel,
    card_from_ble_write,
    render_card,
    required_state_cards,
    sha256_hex,
)


MANIFEST = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
SCAN_ROOT = REPO_ROOT / "app/companion_pendant/epaper"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_pbm_dimensions(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 3 and index < len(data):
        if data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] not in {b"\n", b"\r"}:
                index += 1
            continue
        if data[index:index + 1].isspace():
            index += 1
            continue
        start = index
        while index < len(data) and not data[index:index + 1].isspace():
            index += 1
        tokens.append(data[start:index])
    if len(tokens) != 3 or tokens[0] != b"P4":
        raise ValueError(f"{path}: expected PBM P4 header")
    return int(tokens[1]), int(tokens[2])


def load_manifest(errors: list[str]) -> dict[str, Any] | None:
    require(MANIFEST.exists(), f"missing manifest: {MANIFEST.relative_to(REPO_ROOT)}", errors)
    if not MANIFEST.exists():
        return None
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.epaper_fixtures.v1", "unexpected manifest schema_id", errors)
    return data


def check_manifest(data: dict[str, Any], errors: list[str]) -> None:
    fixtures = data.get("fixtures", [])
    require(len(fixtures) >= 3, "expected at least three e-paper fixtures", errors)
    required_ids = {"boot_default", "recording", "sync_complete"}
    fixture_ids = {fixture.get("id") for fixture in fixtures}
    require(required_ids <= fixture_ids, f"missing fixture ids: {sorted(required_ids - fixture_ids)}", errors)
    variants = {fixture.get("variant") for fixture in fixtures}
    require({"2.13in", "1.54in"} <= variants, "fixtures must cover 2.13in and 1.54in variants", errors)

    required_types = {"mood", "name", "event", "reminder", "recording", "sync_complete", "low_battery", "error"}
    require(required_types <= set(data.get("state_card_coverage", [])), "manifest card coverage incomplete", errors)
    require(required_types <= CARD_TYPES, "renderer CARD_TYPES missing required cards", errors)
    require({"recording", "sync_complete", "low_battery", "error"} <= CARD_STATES, "renderer states incomplete", errors)
    require("deterministic 4x4 Bayer" in data.get("dithering", ""), "manifest missing deterministic dithering", errors)
    require(
        "deterministic codepoint placeholder" in data.get("text_fallback", {}).get("unsupported_unicode", ""),
        "manifest missing multilingual fallback policy",
        errors,
    )

    ble_mapping = data.get("ble_card_write_mapping", {})
    require(ble_mapping.get("card_type") == "event", "BLE CardWriteV1 mapping did not preserve event card type", errors)
    require(ble_mapping.get("request_id") == 42, "BLE CardWriteV1 mapping lost request_id", errors)


def check_fixture_files(data: dict[str, Any], errors: list[str]) -> None:
    for fixture in data.get("fixtures", []):
        rel_path = pathlib.Path(str(fixture.get("path", "")))
        path = REPO_ROOT / rel_path
        require(path.exists(), f"missing fixture file: {rel_path.as_posix()}", errors)
        if not path.exists():
            continue
        variant_key = str(fixture.get("variant"))
        variant = DISPLAY_VARIANTS.get(variant_key)
        require(variant is not None, f"unknown fixture variant: {variant_key}", errors)
        if variant is None:
            continue

        width, height = parse_pbm_dimensions(path)
        require(width == variant.width and height == variant.height, f"{rel_path}: dimension mismatch", errors)
        file_hash = sha256_hex(path.read_bytes())
        require(file_hash == fixture.get("sha256"), f"{rel_path}: hash does not match manifest", errors)

        card_data = fixture.get("card", {})
        card = CardModel(**card_data)
        expected = render_card(card, variant)
        require(sha256_hex(expected) == file_hash, f"{rel_path}: renderer output is not deterministic", errors)


def check_ble_mapping(errors: list[str]) -> None:
    card = card_from_ble_write(
        {
            "request_id": 7,
            "card_slot": 1,
            "utf8_title_len": 8,
            "utf8_body_len": 12,
            "title": "Reminder",
            "body": "Hydrate soon",
            "display_flags": 0x01,
        }
    )
    require(card.card_type == "reminder", "BLE CardWriteV1 display_flags did not map to reminder", errors)
    require(card.title == "Reminder", "BLE CardWriteV1 title length mapping failed", errors)
    require(card.body == "Hydrate soon"[:12], "BLE CardWriteV1 body length mapping failed", errors)


def check_model_render_coverage(errors: list[str]) -> None:
    for card in required_state_cards():
        for variant in DISPLAY_VARIANTS.values():
            rendered = render_card(card, variant)
            require(rendered.startswith(b"P4\n"), f"{card.card_id}/{variant.key} did not render PBM", errors)


def check_hardware_boundary(errors: list[str]) -> None:
    require(README.exists(), "missing e-paper renderer README", errors)
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    for needle in [
        "AI-testable now",
        "Real e-paper SPI timing",
        "refresh waveform validation",
        "deferred to later hardware gates",
        "BLE `CardWriteV1`",
    ]:
        require(needle in text, f"README missing hardware boundary anchor: {needle}", errors)


def check_no_external_requirement(errors: list[str]) -> None:
    patterns = [
        re.compile(r"\bsmart\s+base\b", re.IGNORECASE),
        re.compile(r"\bwi[- ]?fi\b", re.IGNORECASE),
        re.compile(r"\bwireless[- ]charging\b", re.IGNORECASE),
    ]
    for path in sorted(SCAN_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            require(not pattern.search(text), f"{path.relative_to(REPO_ROOT)} introduces external requirement: {pattern.pattern}", errors)


def main() -> int:
    errors: list[str] = []
    data = load_manifest(errors)
    if data is not None:
        check_manifest(data, errors)
        check_fixture_files(data, errors)
    check_ble_mapping(errors)
    check_model_render_coverage(errors)
    check_hardware_boundary(errors)
    check_no_external_requirement(errors)

    if errors:
        print("FAIL: Companion e-paper asset checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion e-paper assets verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
