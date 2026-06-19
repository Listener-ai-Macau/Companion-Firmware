#!/usr/bin/env python3
"""Static checks for Companion OTA readiness and manifest discipline."""

from __future__ import annotations

import json
import pathlib
import re
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OTA_DOC = REPO_ROOT / "docs/ota_readiness.md"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
REUSE_MAP = REPO_ROOT / "docs/listener_reuse_map.md"
DIAG_EVENTS = REPO_ROOT / "app/companion_pendant/diag_log/diag_log_events.h"
FIXTURE_REPORT = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"

REQUIRED_BLOCKERS = {
    "recording_active",
    "transfer_active",
    "diag_export_active",
    "low_battery",
    "wrong_board_target",
    "invalid_hash",
    "interrupted_transfer",
}
REQUIRED_DIAG_EVENTS = {
    "ota.manifest",
    "ota.readiness",
    "ota.blocker",
    "ota.interrupted_transfer",
    "ota.post_update_self_check",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing {path.relative_to(REPO_ROOT)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def check_ota_doc(errors: list[str]) -> None:
    text = read_text(OTA_DOC, errors)
    for anchor in [
        "BLE_Ota",
        "BLE_p2pServer_ota",
        "low-battery",
        "rollback",
        "manifest",
        "Listener",
        "STM32_WPAN",
        "STM32CubeProgrammer",
        "must not be copied",
    ]:
        require(anchor in text, f"ota_readiness missing anchor: {anchor}", errors)
    for blocker in REQUIRED_BLOCKERS:
        require(blocker in text, f"ota_readiness missing blocker: {blocker}", errors)
    require("not a firmware swap implementation" in text, "ota_readiness must defer real firmware swap", errors)


def check_ble_contract(errors: list[str]) -> None:
    text = read_text(BLE_CONTRACT, errors)
    for anchor in [
        "OTA readiness",
        "OtaReadinessV1",
        "blocker_bitmap",
        "manifest_version",
        "image_sha256_prefix",
        "interrupted_transfer_resume_token",
        "must not accept\nOTA data writes",
    ]:
        require(anchor in text, f"BLE contract missing OTA anchor: {anchor}", errors)
    for blocker in REQUIRED_BLOCKERS:
        require(blocker in text, f"BLE contract missing blocker: {blocker}", errors)


def check_diag_events(errors: list[str]) -> None:
    text = read_text(DIAG_EVENTS, errors)
    require('"ota"' in text, "diag events missing ota source", errors)
    for event in REQUIRED_DIAG_EVENTS:
        require(f'"{event}"' in text, f"diag events missing {event}", errors)

    pairs = re.findall(r"X\(OTA,\s*([A-Z0-9_]+),\s*(0x[0-9A-Fa-f]+|\d+)u?", text)
    ids = [int(value, 0) for _, value in pairs]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    require(not duplicate_ids, f"duplicate OTA diag event ids: {duplicate_ids}", errors)


def check_fixture_report(errors: list[str]) -> None:
    require(FIXTURE_REPORT.exists(), f"missing fixture report: {FIXTURE_REPORT.relative_to(REPO_ROOT)}", errors)
    if not FIXTURE_REPORT.exists():
        return
    data = json.loads(FIXTURE_REPORT.read_text(encoding="utf-8"))
    require(data.get("status") == "PASS", "OTA manifest fixture report did not PASS", errors)
    cases = {case.get("case"): case for case in data.get("cases", [])}
    for case_name in ["good", "bad_invalid_hash", "bad_wrong_board", "bad_missing_blockers"]:
        require(case_name in cases, f"missing fixture case: {case_name}", errors)
        if case_name in cases:
            require(cases[case_name].get("status") == "PASS", f"fixture case did not PASS: {case_name}", errors)
    require(REQUIRED_BLOCKERS <= set(data.get("required_blockers", [])), "fixture report missing required blockers", errors)


def check_reuse_boundary(errors: list[str]) -> None:
    text = read_text(REUSE_MAP, errors)
    for anchor in [
        "components/firmware_ota",
        "ports/esp32/ble_firmware_ota",
        "manifest discipline",
        "ESP-IDF OTA slots",
        "NimBLE service code",
        "no reuse",
    ]:
        require(anchor in text, f"reuse map missing OTA boundary: {anchor}", errors)


def main() -> int:
    errors: list[str] = []
    check_ota_doc(errors)
    check_ble_contract(errors)
    check_diag_events(errors)
    check_fixture_report(errors)
    check_reuse_boundary(errors)

    if errors:
        print("FAIL: Companion OTA static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion OTA readiness contract static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
