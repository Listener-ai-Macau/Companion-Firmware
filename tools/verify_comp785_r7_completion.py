#!/usr/bin/env python3
"""Assemble the COMP-REQ-785 r7 machine-closure receipt.

This gate intentionally stops at MACHINE_READY_FOR_OWNER.  Glass cleanliness
and perceived animation independence remain an explicit human boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_BIN_SHA = "86C1F5C2262B2DE6AB5D17C341E682DBEC5E2398569FA1B325188B68932A18FB"
EXPECTED_HEX_SHA = "9A68E8938A9CA63AD64416A19C3C51EAB4E673964F0E0A7EB74789A85576C9C8"
EXPECTED_ELF_SHA = "42CBBACFA33704BDE024A2C3F812BE54EF96495CE2AE6FF4AC8B4DE741F49F4F"
EXPECTED_MAP_SHA = "7C6E2E18F1B33DB8665387B37C29130F71467E8654D9733B8330E9C46981505C"
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
    status_pixels = load(package / "status-bar-pixel-replay" / "receipt.json")
    browser = load(package / "browser-settings.json")
    power = load(package / "power-settings.json")
    face = load(package / "recording-face-independence-r7b.json")
    race = load(package / "recording-lp-race-r7b.json")
    postflash_ble = load(package / "real-user-path-postflash-r7.json")
    recording_ble = load(package / "real-user-path-recording-r7b.json")
    journal = load(package.parent / "comp-req-778-recording-journal-host" / "result.json")
    gatt = load(package.parent / "comp-req-558-recording-host" / "result.json")
    l3 = load(args.l3.resolve())
    flash_text = (package / "flash-swd-ota-app-only-r7.log").read_text(
        encoding="utf-8", errors="replace")
    codec_text = (package / "codec3-product-r7.txt").read_text(
        encoding="utf-8", errors="replace").strip()

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
        "firmware_hashes_exact": hashes == {
            "bin": EXPECTED_BIN_SHA, "hex": EXPECTED_HEX_SHA,
            "elf": EXPECTED_ELF_SHA, "map": EXPECTED_MAP_SHA,
        },
        "ota_layout_safe": layout.get("status") == "MACHINE_READY"
            and all(layout.get("checks", {}).values())
            and headroom >= MIN_HEADROOM,
        "app_only_flash_verified": "Download verified successfully" in flash_text
            and "Loader region not targeted" in flash_text
            and "Address       : 0x08007000" in flash_text,
        "canonical_status_bar_pixels": status_pixels.get("status") == "MACHINE_READY"
            and all(status_pixels.get("checks", {}).get(name) is True
                    for name in pixel_required),
        "settings_persist_and_bind": browser.get("status") == "MACHINE_READY"
            and all(browser.get("checks", {}).values())
            and browser.get("ota", {}).get("headroom_bytes") == headroom,
        "power_settings_persist": power.get("status") == "MACHINE_READY"
            and power.get("host_test", {}).get("status") == "PASS",
        "postflash_serial_clean": serial_clean(package, "serial-postflash-r7"),
        "recording_serial_clean": serial_clean(package, "serial-recording-r7b"),
        "low_power_serial_clean": serial_clean(package, "serial-low-power-r7"),
        "postflash_ble_clock_disconnect": postflash_ble.get("status") == "PASS_REAL_RADIO"
            and op_pass(postflash_ble, "sync_utc_clock")
            and op_pass(postflash_ble, "disconnect"),
        "real_ble_recording_start_stop": recording_ble.get("status") == "PASS_REAL_RADIO"
            and op_pass(recording_ble, "recording_control_start_write")
            and op_pass(recording_ble, "recording_control_stop_write")
            and op_pass(recording_ble, "disconnect"),
        "recording_clocks_independent": face.get("status") == "MACHINE_READY"
            and all(face.get("checks", {}).values()),
        "recording_lp_race_closed": race.get("status") == "MACHINE_READY"
            and all(race.get("checks", {}).values())
            and race.get("same_binary_normal_idle", {}).get("status") == "MACHINE_READY",
        "recording_journal_contract": journal.get("status") == "PASS",
        "gatt_pull_contract": gatt.get("status") == "PASS"
            and gatt.get("pcm_matches_metadata") is True,
        "codec3_product_contract": codec_text.startswith("PASS live_mic_codec3_product"),
        "immutable_l3_chain_valid": sha256(args.l3.resolve()) == EXPECTED_L3_SHA
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
        "schema": "companion.comp785.r7.completion_audit.v1",
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
            "wave_p95_ms": race.get("timing", {}).get("pure_wave_gap_p95_ms"),
            "face_commits": face.get("counts", {}).get("phase_face"),
            "blink_commits": face.get("counts", {}).get("phase_blink"),
            "accessory_deadlines": race.get("counts", {}).get("accessory_deadlines"),
            "low_power_f7_count": race.get("same_binary_normal_idle", {})
                .get("counts", {}).get("f7_panel"),
            "panel_after_freeze": race.get("same_binary_normal_idle", {})
                .get("counts", {}).get("panel_after_freeze"),
            "l3_sha256": sha256(args.l3.resolve()),
        },
        "human_gate": {
            "status": "PENDING",
            "required": True,
            "scope": [
                "black status bar has no white leaks",
                "time is visible",
                "BT is visible when connected and BX when disconnected",
                "recording waveform is fastest while face/accessories feel independent",
                "low-power background is clean and no residual lines or hang appear",
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
