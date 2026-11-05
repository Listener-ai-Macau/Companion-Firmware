#!/usr/bin/env python3
"""Fail-closed release packager for the COMP-REQ-775 r62 board candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require(ok: bool, name: str) -> None:
    if not ok:
        raise AssertionError(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = (repo / args.evidence).resolve()
    output = (repo / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    static_path = evidence / "r61-static.json"
    paired_path = evidence / "paired-replay.json"
    phase_path = evidence / "phase-lock.json"
    physical_path = evidence / "physical-path.json"
    soak = evidence / "long-recording-180s-run2"
    ble_path = soak / "ble-recording-control.json"
    serial_path = soak / "nucleo-serial-summary.json"
    raw_path = soak / "nucleo-serial-raw.log"
    layout_path = repo / ".cache/validation/build-nucleo/ota-app-layout-Companion_Nucleo_WB55RG_FreeRTOS.json"
    build = repo / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_freertos"
    firmware = {
        ext: build / f"Companion_Nucleo_WB55RG_FreeRTOS.{ext}"
        for ext in ("bin", "hex", "elf")
    }
    flash_log = output / "flash-transcript.log"
    final_boot_summary = output / "final-boot/nucleo-serial-summary.json"

    static = load(static_path)
    paired = load(paired_path)
    phase = load(phase_path)
    physical = load(physical_path)
    ble = load(ble_path)
    serial = load(serial_path)
    layout = load(layout_path)
    boot = load(final_boot_summary)
    flash_text = flash_log.read_text(encoding="utf-8-sig", errors="replace")

    checks = {
        "static_driver_gate": static.get("status") == "MACHINE_READY",
        "independent_mode_enabled": static.get("independent_enabled") is True,
        "paired_60_exact": paired.get("status") == "MACHINE_READY"
        and paired.get("paired_count") == 60,
        "phase_independent": phase.get("status") == "MACHINE_READY"
        and phase["candidate"].get("classification") == "PHASE_INDEPENDENT",
        "r55_negative_rejected": phase["owner_rejected_negative"].get("classification")
        == "PHASE_LOCKED",
        "wave_fastest_gap_gate": phase["candidate"]["timing"].get("wave_gap_max_ms", 999999)
        <= phase["policy"].get("max_wave_gap_ms", 0)
        and phase["candidate"]["timing"].get("wave_gap_p95_ms", 999999)
        <= phase["policy"].get("max_wave_p95_gap_ms", 0),
        "physical_path": physical.get("status") == "MACHINE_READY",
        "real_recording_180s": physical["recording"].get("duration_ms", 0) >= 180000,
        "audio_drop_free": physical["recording"].get("drops") == 0,
        "no_forbidden_refresh": not physical["recording"].get("forbidden_tokens")
        and not physical["recording"].get("forbidden_controls"),
        "real_ble": ble.get("status") == "PASS_REAL_RADIO",
        "serial_capture": serial.get("status") == "PASS"
        and not serial.get("errors") and serial.get("seconds", 0) >= 260,
        "raw_log_identity": phase["candidate"].get("sha256") == sha(raw_path)
        and physical["source"].get("recording_log_sha256") == sha(raw_path),
        "ota_app_layout": layout.get("status") == "MACHINE_READY"
        and layout.get("minimum_address") == "0x08007000"
        and int(layout.get("maximum_address_exclusive", "0"), 16) <= 0x08080000,
        "app_only_flash_verified": "Download verified successfully" in flash_text
        and "Loader region not targeted" in flash_text,
        "final_post_flash_boot": boot.get("status") == "PASS"
        and not boot.get("errors"),
    }
    for name, ok in checks.items():
        require(ok, name)

    copied: dict[str, dict] = {}
    for ext, source in firmware.items():
        target = output / f"Companion_Nucleo_WB55RG_FreeRTOS.{ext}"
        shutil.copy2(source, target)
        copied[ext] = {"path": target.name, "bytes": target.stat().st_size, "sha256": sha(target)}
    evidence_out = output / "evidence"
    evidence_out.mkdir(exist_ok=True)
    for source in (static_path, paired_path, phase_path, physical_path, ble_path,
                   serial_path, raw_path, layout_path):
        shutil.copy2(source, evidence_out / source.name)

    manifest = {
        "schema": "companion.comp_req_775.r62_release.v1",
        "status": "MACHINE_READY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "identity": {
            "build": "FreeRTOS OTA App",
            "build_command": "tools/build_nucleo_bringup.ps1 -UseFreeRTOS -OtaApp",
            "flash_command": "tools/flash_swd_ota_app_only.ps1 -ImagePath <formal hex>",
            "firmware": copied,
            "ota_app_layout": {
                "minimum_address": layout["minimum_address"],
                "maximum_address_exclusive": layout["maximum_address_exclusive"],
                "reset_handler": layout["vector"]["reset_handler"],
                "ota_magic_pointer": layout["ota_magic"]["pointer"],
            },
        },
        "checks": checks,
        "metrics": {
            "paired_authored_tuples": paired["paired_count"],
            "wave": phase["candidate"]["counts"]["wave"],
            "face": phase["candidate"]["counts"]["face"],
            "blink": phase["candidate"]["counts"]["blink"],
            "accessory_clock": phase["candidate"]["counts"]["accessory_clock"],
            "wave_gap_max_ms": phase["candidate"]["timing"]["wave_gap_max_ms"],
            "wave_gap_p95_ms": phase["candidate"]["timing"]["wave_gap_p95_ms"],
            "recording_duration_ms": physical["recording"]["duration_ms"],
            "audio_drops": physical["recording"]["drops"],
            "panel_failures": physical["recording"]["panel_failures"],
            "unhealthy_watchdog_rows": physical["recording"]["unhealthy_watchdog_rows"],
        },
        "rollback": str((repo / ".cache/validation/comp775-r52-owner-fail-hold-rollback-20260810").resolve()),
        "pending_human": "Owner visual panel acceptance; timeout is not PASS",
    }
    manifest_path = output / "MACHINE_READY.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
