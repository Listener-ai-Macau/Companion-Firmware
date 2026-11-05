#!/usr/bin/env python3
"""Gate the exact-T03 public-source fast-state comparator before hardware use."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_vendor_partial_slow_motion_diagnostic.ps1"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
T03_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-official-stm32-source-audit-20260720.json"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-t03-fast-state-static-20260720.json"
SCHEMA = "companion.wb55.gdey0154d67_t03.vendor_t03_fast_state_static.v1"
PASS = "PASS_STATIC_OWNER_AUTHORIZED_VENDOR_T03_FAST_STATE_AB"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} is not a JSON object")
    return value


def main() -> int:
    required = (DRIVER, MAKEFILE, BUILD, RUNNER, REGISTRY, T03_AUDIT, SOURCE_AUDIT, RECOVERY_GATE)
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        report: dict[str, Any] = {"schema_id": SCHEMA, "status": "NO_GO_INPUT_MISSING", "failures": missing}
    else:
        driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
        makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
        build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
        runner = RUNNER.read_text(encoding="utf-8-sig", errors="replace")
        registry = REGISTRY.read_text(encoding="utf-8-sig", errors="replace")
        t03 = load(T03_AUDIT)
        source = load(SOURCE_AUDIT)
        recovery = load(RECOVERY_GATE)
        checks = {
            "owner_authorizes_exact_t03_production_off_comparator": all(
                token in registry
                for token in (
                    "COMP-REQ-208",
                    "GDEY0154D67-T03 STM32 Sample Code",
                    "0x22=0xB1 -> 0x20 -> BUSY",
                    "0xC7` base-map state",
                )
            ),
            "official_t03_archive_and_command_audit_passes": t03.get("status")
            == "PASS_AUDIT_EXACT_T03_PUBLIC_SAMPLE_PANEL_IDENTITY_REMAINS_UNPROVEN"
            and t03.get("official_provenance", {}).get("archive_sha256")
            == "202ADAB27515FDBA790565F643C3C83C52C11FF36844E8C387F66676C3D82CD4"
            and t03.get("literal_source_sequence", {}).get("no_external_lut_load") is True,
            "source_audit_still_binds_current_driver": source.get("machine_status") == "PASS_AUDIT_COMPLETE"
            and source.get("source_manifest", {}).get("critical_sources", {}).get("current_ssd1681_target", {}).get("sha256")
            == digest(DRIVER),
            "white_black_recovery_gate_passes": recovery.get("status")
            == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
            "default_off_and_source_partial_dependency": all(
                token in driver
                for token in (
                    "#define COMPANION_EPAPER_SSD1681_VENDOR_T03_FAST_STATE_DIAGNOSTIC 0",
                    "SSD1681 vendor T03 fast-state diagnostic requires the source slow-motion diagnostic",
                )
            ),
            "exact_otp_temperature_state_is_used": all(
                token in driver
                for token in (
                    "ssd1681_prepare_vendor_fast_profile",
                    "static const uint8_t temperature_sensor[] = {0x80u};",
                    "static const uint8_t load_temperature_mode1[] = {0xB1u};",
                    "SSD1681_VENDOR_FAST_TEMPERATURE_LSB 0x64u",
                    "static const uint8_t load_lut_mode1[] = {0x91u};",
                    "ssd1681_command_data(0x1Au,",
                )
            ),
            "baseline_is_two_full_planes_then_c7": all(
                token in driver
                for token in (
                    "const bool vendor_t03_fast_basemap = vendor_t03_fast_state && !partial;",
                    "ssd1681_write_plane_region(0x24u, s_frame, &window) &&\n                            ssd1681_write_plane_region(0x26u, s_frame, &window);",
                    "good_display_t03_fast_state_basemap",
                    "? COMP_EPAPER_REFRESH_DECISION_FAST",
                    "control=0xC7",
                )
            ),
            "later_updates_keep_source_region_path": all(
                token in driver
                for token in (
                    "good_display_t03_partial_0x24_only",
                    "vendor_partial_source region_reset low_ms=10 high_ms=10",
                    "static const uint8_t border_lock[] = {0x80u};",
                    "? 0xFFu",
                    "ssd1681_write_plane_region(0x24u, s_frame, &source_regions[index])",
                )
            ),
            "isolated_build_and_runner_exist": all(
                token in build
                for token in (
                    "[switch]$EpaperSsd1681VendorT03FastStateDiagnostic",
                    "EPAPER_SSD1681_VENDOR_T03_FAST_STATE_DIAGNOSTIC=1",
                    "BUILD_DIR=build_vendor_t03_fast_state_diagnostic",
                    "TARGET=Companion_Nucleo_WB55RG_VendorT03FastStateDiagnostic",
                )
            )
            and "EPAPER_SSD1681_VENDOR_T03_FAST_STATE_DIAGNOSTIC" in makefile
            and "[switch] $T03FastState" in runner,
        }
        failures = [name for name, passed in checks.items() if not passed]
        report = {
            "schema_id": SCHEMA,
            "status": PASS if not failures else "NO_GO_STATIC_VENDOR_T03_FAST_STATE_INCOMPLETE",
            "claim_scope": "owner-authorized, current-room, exact-public-T03-sequence adaptation; production-off with no external LUT, residue-free, temperature-range or panel-identity claim",
            "target": "NUCLEO-WB55RG + ESP32-FTS02 + observed 0154BN-D67-D2 panel",
            "checks": checks,
            "failures": failures,
            "source": {
                "target_driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
                "official_t03_audit": {"path": rel(T03_AUDIT), "sha256": digest(T03_AUDIT)},
                "supplier_source_audit": {"path": rel(SOURCE_AUDIT), "sha256": digest(SOURCE_AUDIT)},
                "recovery_gate": {"path": rel(RECOVERY_GATE), "sha256": digest(RECOVERY_GATE)},
            },
            "controlled_behavior": {
                "baseline": "T03 built-in temperature/OTP setup: 0x18=80, 0x22=B1/0x20/BUSY, 0x1A=64 00, 0x22=91/0x20/BUSY; then 0x24 and 0x26 each 5000 bytes, 0xC7/0x20/BUSY",
                "partial": "source reset low/high 10 ms, 0x3C=80, one or two changed current-image 0x24 regions, 0xFF/0x20/BUSY",
                "maximum_region_bytes_per_plane": 567,
                "production_default": "disabled",
                "max_frames": 360,
                "external_lut": "forbidden",
                "temperature_claim": "none",
                "normal_restore_required": True,
            },
        }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: T03 fast-state static check -> {rel(OUT)}")
    return 0 if report["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
