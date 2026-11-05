#!/usr/bin/env python3
"""Static checks for the Companion STM32 diagnostic log foundation."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADER = REPO_ROOT / "app/companion_pendant/diag_log/diag_log_events.h"
CORE_FILES = [
    REPO_ROOT / "app/companion_pendant/diag_log/diag_log.h",
    REPO_ROOT / "app/companion_pendant/diag_log/diag_log.c",
    REPO_ROOT / "app/companion_pendant/diag_log/diag_log_export.h",
    REPO_ROOT / "app/companion_pendant/diag_log/diag_log_export.c",
    HEADER,
]
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
FIXTURE_DECODED = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.4-diag-log-decoded.json"

REQUIRED_SOURCES = {
    "boot",
    "ble",
    "gatt",
    "e_paper",
    "recording_fsm",
    "microphone",
    "spi_flash_cache",
    "ota",
    "battery_charging",
    "power_lpm",
    "warnings",
    "errors",
}
FORBIDDEN_CORE_PATTERNS = {
    r"\besp_[A-Za-z0-9_]+": "ESP-IDF API",
    r"\bESP_[A-Z0-9_]+": "ESP-IDF macro",
    r"\besp_partition": "ESP partition API",
    r"\bnvs_flash": "ESP NVS API",
    r"\bESP_LOG": "ESP logging API",
    r"\bFreeRTOS\b": "FreeRTOS include/use",
    r"\bportMUX": "ESP FreeRTOS critical-section type",
    r"\bxTask": "FreeRTOS task API",
}


def load_decoder_module() -> Any:
    sys.dont_write_bytecode = True
    path = REPO_ROOT / "tools/decode_diag_log.py"
    spec = importlib.util.spec_from_file_location("companion_decode_diag_log", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_schema(errors: list[str]) -> None:
    decoder = load_decoder_module()
    schema = decoder.load_schema(HEADER)
    source_names = set(schema.sources_by_name)
    require(REQUIRED_SOURCES <= source_names, f"missing sources: {sorted(REQUIRED_SOURCES - source_names)}", errors)

    source_ids = [source.value for source in schema.sources_by_name.values()]
    duplicate_sources = sorted(value for value, count in Counter(source_ids).items() if count > 1)
    require(not duplicate_sources, f"duplicate source IDs: {duplicate_sources}", errors)

    event_keys = [
        (schema.sources_by_symbol[event.source_symbol].value, event.value)
        for event in schema.events_by_name.values()
    ]
    duplicate_events = sorted(key for key, count in Counter(event_keys).items() if count > 1)
    require(not duplicate_events, f"duplicate event IDs within source: {duplicate_events}", errors)

    sources_with_events = {
        schema.sources_by_symbol[event.source_symbol].name
        for event in schema.events_by_name.values()
    }
    require(
        REQUIRED_SOURCES <= sources_with_events,
        f"sources without event coverage: {sorted(REQUIRED_SOURCES - sources_with_events)}",
        errors,
    )

    for event in schema.events_by_name.values():
        source = schema.sources_by_symbol[event.source_symbol]
        decoded = decoder.decode_raw_event(
            {
                "sequence": 1,
                "t_ms": 1,
                "source": source.value,
                "event_id": event.value,
                "severity": 0,
            },
            0,
            schema,
        )
        require(decoded["event"]["name"] == event.name, f"decoder missed event {event.name}", errors)


def check_core_is_stm32_safe(errors: list[str]) -> None:
    for path in CORE_FILES:
        require(path.exists(), f"missing core file: {path.relative_to(REPO_ROOT)}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_CORE_PATTERNS.items():
            if re.search(pattern, text):
                errors.append(f"{path.relative_to(REPO_ROOT)} contains forbidden {label}: {pattern}")

    readme = REPO_ROOT / "app/companion_pendant/diag_log/README.md"
    require(readme.exists(), "missing retained-ring README", errors)
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        require("SPI flash ring" in text, "README missing future SPI flash retained ring", errors)
        require("must not copy Listener ESP partition table assumptions" in text, "README missing ESP partition warning", errors)

    export_header = (REPO_ROOT / "app/companion_pendant/diag_log/diag_log_export.h").read_text(encoding="utf-8")
    export_source = (REPO_ROOT / "app/companion_pendant/diag_log/diag_log_export.c").read_text(encoding="utf-8")
    ring_source = (REPO_ROOT / "app/companion_pendant/diag_log/diag_log.c").read_text(encoding="utf-8")
    for needle in [
        "comp_diag_log_export_packet_t",
        "COMP_DIAG_LOG_EXPORT_HEADER_BYTES 20u",
        "COMP_DIAG_LOG_EXPORT_MAX_EVENTS 8u",
    ]:
        require(needle in export_header, f"diagnostics exporter missing {needle}", errors)
    for needle in ["comp_diag_log_export_build", "comp_diag_log_export_crc32", "_Static_assert"]:
        require(needle in export_source, f"diagnostics exporter source missing {needle}", errors)
    require("comp_diag_log_read_page" in ring_source, "diagnostic ring missing cursor paging", errors)


def check_ble_contract(errors: list[str]) -> None:
    require(BLE_CONTRACT.exists(), "missing docs/ble_gatt_contract.md", errors)
    if not BLE_CONTRACT.exists():
        return
    text = BLE_CONTRACT.read_text(encoding="utf-8")
    for needle in [
        "diagnostics/log pull",
        "bounded log export",
        "default bounded tails",
        "not unbounded full dumps",
        "| service | characteristic | direction | payload | validation |",
    ]:
        require(needle in text, f"BLE contract missing {needle!r}", errors)


def check_fixture(errors: list[str]) -> None:
    require(FIXTURE_DECODED.exists(), "missing decoded fixture artifact", errors)
    if not FIXTURE_DECODED.exists():
        return
    data = json.loads(FIXTURE_DECODED.read_text(encoding="utf-8"))
    events = data.get("events", [])
    names = {event.get("event", {}).get("name") for event in events}
    require("gatt.log_export_request" in names, "fixture missing named log export event", errors)
    require("errors.assert" in names, "fixture missing named error event", errors)


def main() -> int:
    errors: list[str] = []
    check_schema(errors)
    check_core_is_stm32_safe(errors)
    check_ble_contract(errors)
    check_fixture(errors)
    if errors:
        print("FAIL: Companion diag log static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion diag log static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
