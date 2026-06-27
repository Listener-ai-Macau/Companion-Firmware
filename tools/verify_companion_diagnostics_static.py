#!/usr/bin/env python3
"""Static/fixture checks for the Companion diagnostics bundle collector."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
COLLECTOR = REPO_ROOT / "tools/collect_companion_diagnostics.ps1"
SUMMARY = REPO_ROOT / "docs/validation/companion-diagnostics-fixture/summary.json"
DECODED = REPO_ROOT / "docs/validation/companion-diagnostics-fixture/diag_tail_decoded.json"

REQUIRED_COLLECTOR_ANCHORS = (
    "Only fixture/no-hardware Companion diagnostics are implemented",
    "companion.pendant.diagnostics_bundle.v1",
    "private_audio_payload_exported",
    "raw_recording_payload_exported",
    "no_unbounded_full_dumps",
    "device_status",
    "scan_summary",
    "recording_cache",
    "last_transfer_result",
    "epaper",
    "ota",
    "battery",
    "diag_tail",
    "diagnostics/log pull cursor/source/severity model",
    "decode_diag_log.py",
)

REQUIRED_SUMMARY_KEYS = (
    "device_status",
    "ble",
    "recording",
    "recording_cache",
    "last_transfer_result",
    "epaper",
    "ota",
    "battery",
    "diag_tail",
)

REQUIRED_EVENT_NAMES = (
    "gatt.log_export_request",
    "recording_fsm.transition",
    "spi_flash_cache.write",
    "e_paper.update_result",
    "ota.manifest",
    "ota.readiness",
    "battery_charging.sample",
    "power_lpm.blocker",
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing JSON artifact: {path.relative_to(REPO_ROOT)}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def check_collector(errors: list[str]) -> None:
    require(COLLECTOR.exists(), "missing tools/collect_companion_diagnostics.ps1", errors)
    if not COLLECTOR.exists():
        return
    text = COLLECTOR.read_text(encoding="utf-8")
    for anchor in REQUIRED_COLLECTOR_ANCHORS:
        require(anchor in text, f"collector missing anchor: {anchor}", errors)
    require("-Fixture" in text, "collector missing -Fixture parameter", errors)
    require("throw \"Only fixture/no-hardware" in text, "collector must refuse non-fixture hardware access", errors)


def check_summary(errors: list[str]) -> None:
    summary = load_json(SUMMARY, errors)
    if not summary:
        return
    require(summary.get("schema_id") == "companion.pendant.diagnostics_bundle.v1", "wrong summary schema", errors)
    require(summary.get("mode") == "fixture", "summary must be fixture mode", errors)
    require(summary.get("bounded") is True, "summary must be bounded", errors)
    require(summary.get("hardware_action") is False, "fixture summary must not touch hardware", errors)

    for key in REQUIRED_SUMMARY_KEYS:
        require(key in summary, f"summary missing key: {key}", errors)

    privacy = summary.get("privacy", {})
    require(privacy.get("private_audio_payload_exported") is False, "private audio must not be exported", errors)
    require(privacy.get("raw_recording_payload_exported") is False, "raw recording payload must not be exported", errors)
    require(privacy.get("no_unbounded_full_dumps") is True, "summary must forbid unbounded full dumps", errors)

    diag_tail = summary.get("diag_tail", {})
    require(diag_tail.get("bounded") is True, "diag_tail must be bounded", errors)
    request = diag_tail.get("request", {})
    require(int(request.get("max_events", 0)) <= 64, "diag_tail max_events not bounded", errors)
    require(int(request.get("max_bytes", 0)) <= 4096, "diag_tail max_bytes not bounded", errors)
    require("cursor/source/severity" in str(diag_tail.get("contract", "")), "diag_tail missing cursor/source/severity model", errors)


def check_decoded_tail(errors: list[str]) -> None:
    decoded = load_json(DECODED, errors)
    if not decoded:
        return
    names = {
        str(event.get("event", {}).get("name"))
        for event in decoded.get("events", [])
    }
    for name in REQUIRED_EVENT_NAMES:
        require(name in names, f"decoded diag tail missing event: {name}", errors)


def main() -> int:
    errors: list[str] = []
    check_collector(errors)
    check_summary(errors)
    check_decoded_tail(errors)
    if errors:
        print("FAIL: Companion diagnostics static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion diagnostics collector fixture/static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
