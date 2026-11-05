#!/usr/bin/env python3
"""One-shot machine closure for COMP-REQ-781/782 before Owner review."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / ".cache" / "validation" / "comp-req-781-power-settings-20260815"
BUILD = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "build_freertos"
OUT = PKG / "FINAL_MACHINE_READY.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def run(name: str, command: list[str]) -> dict:
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )
    return {
        "name": name,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:].strip(),
        "stderr_tail": completed.stderr[-1000:].strip(),
    }


def main() -> int:
    build_bin = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.bin"
    package_bin = PKG / build_bin.name
    build_hex = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.hex"
    save_log = (PKG / "set-5-capture" / "nucleo-serial-raw.log").read_text(
        encoding="utf-8-sig", errors="replace"
    )
    boot_log = (PKG / "r3-machine-boot" / "nucleo-serial-raw.log").read_text(
        encoding="utf-8-sig", errors="replace"
    )

    checks = [
        run("power_store_fault_injection", [sys.executable, str(ROOT / "tools" / "verify_comp_req_781_power_settings.py")]),
        run("menu_refresh_contract", [sys.executable, str(ROOT / "tools" / "verify_comp_req_782_menu_refresh_boundary.py")]),
        run("low_power_regression", [sys.executable, str(ROOT / "tools" / "verify_companion_low_power_requirements.py")]),
        run("touch_and_menu_host_replay", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools" / "test_touch_gesture_host.ps1")]),
        run("ota_app_layout", [sys.executable, str(ROOT / "tools" / "faraday_upper_art" / "verify_companion_ota_app_hex.py"), "--hex", str(build_hex), "--receipt", str(PKG / "OTA_APP_LAYOUT.json")]),
    ]
    identities = {
        "build_bin_sha256": sha256(build_bin),
        "package_bin_sha256": sha256(package_bin),
        "match": sha256(build_bin) == sha256(package_bin),
    }
    runtime = {
        "real_menu_save_5": "[pwrset] save=0 m=5 g=1 n=1" in save_log,
        "reset_load_5": "[pwrset] load=0 m=5 g=1 n=1" in boot_log,
        "reset_rtc_300000": "low_power_idle_timer=armed delay_ms=300000" in boot_log,
        "watchdog_boot_progress_healthy": "watchdog-probe] pass=8" in boot_log and "stalled=0x00" in boot_log,
        "touch_controller_healthy": "errors=0 recoveries=0 failure_streak=0" in boot_log,
    }
    all_pass = (
        all(check["status"] == "PASS" for check in checks)
        and identities["match"]
        and all(runtime.values())
    )
    result = {
        "schema": "companion.comp_req_781_782.final_machine.v1",
        "status": "MACHINE_READY" if all_pass else "NO_GO",
        "firmware": identities,
        "checks": checks,
        "runtime": runtime,
        "owner_boundary": "Only physical refresh appearance, residue, and interaction feel remain.",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
