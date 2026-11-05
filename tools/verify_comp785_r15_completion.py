#!/usr/bin/env python3
"""Assemble the COMP-REQ-785 r17 machine-closure receipt.

The receipt binds the exact app-only image to real-radio status-bar and
recording runs.  It deliberately leaves glass quality and perceived motion
independence behind a blocking Owner gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_HASHES = {
    "bin": "06E375A892A986BBCDCF770CBAC70E624798A35DE33D58342B7080C11AB274FD",
    "hex": "40F52B9A8F3C460A119E99B450A21485C3CD792253653FB1EF0D7630D3855029",
    "elf": "83EAE69DFDE4FCDC2A1FDD570B4F78B1CFD6974166036087D3485C8B2C80CD22",
    "map": "05F6F5A66E0AF89767C54EB451D3704E7AC9EE6353B1A744EFFE04403DAA3514",
}
EXPECTED_L3_SHA = "C8E7E26106D868034F3AA65BB654F1AB8F2D7119A4FFE5EA032E291FDF006E6E"
OTA_END_EXCLUSIVE = 0x08080000
MIN_HEADROOM = 1024
FAULT_TOKENS = (
    "HardFault", "BUSY timeout", "panel failure", "watchdog] healthy=0",
    "stalled_mask=0x01", "stalled_mask=0x02", "stalled_mask=0x04",
    "stalled_mask=0x08", "stalled_mask=0x10",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def op_pass(doc: dict[str, Any], name: str) -> bool:
    return any(row.get("operation") == name and row.get("status") == "PASS"
               for row in doc.get("operations", []))


def serial_clean(package: Path, folder: str) -> bool:
    summary = load(package / folder / "nucleo-serial-summary.json")
    raw = (package / folder / "nucleo-serial-raw.log").read_text(
        encoding="utf-8", errors="replace")
    return (summary.get("status") == "PASS" and summary.get("bytes_read", 0) > 0
            and not summary.get("errors")
            and not any(token in raw for token in FAULT_TOKENS))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--l3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = args.package.resolve()

    artifacts = {
        "bin": package / "Companion_Nucleo_WB55RG_FreeRTOS.bin",
        "hex": package / "Companion_Nucleo_WB55RG_FreeRTOS.hex",
        "elf": package / "Companion_Nucleo_WB55RG_FreeRTOS.elf",
        "map": package / "Companion_Nucleo_WB55RG_FreeRTOS.map",
    }
    hashes = {name: sha256(path) for name, path in artifacts.items()}
    layout = load(package / "ota-app-layout-Companion_Nucleo_WB55RG_FreeRTOS.json")
    maximum = int(layout["maximum_address_exclusive"], 16)
    headroom = OTA_END_EXCLUSIVE - maximum
    pixels = load(package / "status-bar-pixel-replay" / "receipt.json")
    browser = load(package / "browser-settings.json")
    status = load(package / "statusbar-runtime.json")
    face = load(package / "recording-face-independence.json")
    race = load(package / "recording-lp-race.json")
    status_ble = load(package / "real-user-path-status-r17.json")
    recording_ble = load(package / "real-user-path-recording-r17.json")
    journal = load(package.parent / "comp-req-778-recording-journal-host" / "result.json")
    gatt = load(package.parent / "comp-req-558-recording-host" / "result.json")
    l3_path = args.l3.resolve()
    l3 = load(l3_path)
    flash_text = (package / "flash-swd-app-only.log").read_text(
        encoding="utf-8", errors="replace")
    codec_text = (package / "codec3-product.log").read_text(
        encoding="utf-8", errors="replace")

    pixel_required = (
        "actual_c_renderer_executed",
        "pixels_below_y15_unchanged",
        "canonical_top_strip_is_source_independent",
        "connected_bluetooth_rune_visible",
        "disconnected_bluetooth_marker_visible",
        "connected_and_disconnected_are_distinct",
        "nucleo_runtime_neutral_battery_outline",
        "valid_clock_and_unknown_time_are_distinct",
        "bluetooth_region_ends_before_battery_x174",
        "non_glyph_bar_regions_are_solid_black",
        "invalid_clock_rejected_without_mutation",
    )
    l3_checks = l3.get("checks", {})
    checks = {
        "firmware_hashes_exact": hashes == EXPECTED_HASHES,
        "ota_layout_safe": layout.get("status") == "MACHINE_READY"
            and all(layout.get("checks", {}).values())
            and headroom >= MIN_HEADROOM,
        "app_only_flash_verified": "Download verified successfully" in flash_text
            and "Loader region not targeted" in flash_text
            and "Address       : 0x08007000" in flash_text,
        "canonical_status_bar_pixels": pixels.get("status") == "MACHINE_READY"
            and all(pixels.get("checks", {}).get(name) is True
                    for name in pixel_required),
        "settings_persist_and_bind": browser.get("status") == "MACHINE_READY"
            and all(browser.get("checks", {}).values())
            and browser.get("ota", {}).get("headroom_bytes") == headroom,
        "status_serial_clean": serial_clean(package, "serial-status-runtime-r17"),
        "recording_serial_clean": serial_clean(package, "serial-recording-runtime-r17"),
        "low_power_serial_clean": serial_clean(package, "serial-lp-runtime-r17"),
        "real_status_windows_are_top_only": status.get("status") == "MACHINE_READY"
            and all(status.get("checks", {}).values())
            and len(status.get("status_transactions", [])) == 3,
        "real_ble_clock_connect_disconnect": status_ble.get("status") == "PASS_REAL_RADIO"
            and op_pass(status_ble, "sync_utc_clock")
            and op_pass(status_ble, "disconnect"),
        "real_ble_recording_start_stop": recording_ble.get("status") == "PASS_REAL_RADIO"
            and op_pass(recording_ble, "recording_control_start_write")
            and op_pass(recording_ble, "recording_control_stop_write")
            and op_pass(recording_ble, "disconnect"),
        "recording_clocks_independent": face.get("status") == "MACHINE_READY"
            and all(face.get("checks", {}).values()),
        "recording_lp_race_closed": race.get("status") == "MACHINE_READY"
            and all(race.get("checks", {}).values())
            and race.get("same_binary_normal_idle", {}).get("status") == "MACHINE_READY"
            and all(race.get("same_binary_normal_idle", {}).get("checks", {}).values()),
        "recording_journal_contract": journal.get("status") == "PASS",
        "gatt_pull_contract": gatt.get("status") == "PASS"
            and gatt.get("pcm_matches_metadata") is True,
        "codec3_product_contract": "PASS live_mic_codec3_product" in codec_text,
        "immutable_l3_chain_valid": sha256(l3_path) == EXPECTED_L3_SHA
            and str(l3.get("result", "")).startswith("PASS")
            and l3.get("realBoardMic") is True and l3.get("codec") == 3
            and l3.get("seed") is False and l3.get("disconnectResume") is True
            and l3.get("dualMode") is True
            and l3.get("minutesAccuracy", {}).get("pass") is True
            and all(l3_checks.get(name) is True for name in
                    ("machineFullChain", "ownerPassed")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp785.r17.completion_audit.v1",
        "status": "MACHINE_READY_FOR_OWNER" if not failed else "NO_GO",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "package": str(package),
        "firmware": {
            "bin_sha256": hashes["bin"],
            "hex_sha256": hashes["hex"],
            "elf_sha256": hashes["elf"],
            "map_sha256": hashes["map"],
            "ota_start": layout["minimum_address"],
            "ota_end_exclusive": layout["maximum_address_exclusive"],
            "headroom_bytes": headroom,
            "minimum_headroom_bytes": MIN_HEADROOM,
        },
        "checks": checks,
        "failed_checks": failed,
        "machine_evidence": {
            "status_transactions": status.get("status_transactions"),
            "wave_p95_ms": race.get("timing", {}).get("pure_wave_gap_p95_ms"),
            "face_commits": face.get("counts", {}).get("phase_face"),
            "accessory_deadlines": race.get("counts", {}).get("accessory_deadlines"),
            "recording_drops": face.get("recording", {}).get("drops"),
            "recording_full_refreshes": race.get("counts", {}).get("maintenance_single_full"),
            "low_power_f7_count": race.get("same_binary_normal_idle", {})
                .get("counts", {}).get("f7_panel"),
            "panel_after_freeze": race.get("same_binary_normal_idle", {})
                .get("counts", {}).get("panel_after_freeze"),
            "l3_sha256": sha256(l3_path),
        },
        "human_gate": {
            "status": "PENDING",
            "required": True,
            "scope": [
                "top black strip is solid except intentional white glyphs",
                "HH:MM is visible after clock sync",
                "BT is visible when connected and B- when disconnected",
                "status changes do not disturb the face or accessories",
                "recording waveform is fastest while face/accessories feel independent",
                "low-power background is clean with no residual lines or hang",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
