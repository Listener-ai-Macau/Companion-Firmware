#!/usr/bin/env python3
"""Gate the official-method old/new RAM diagnostic before it can flash hardware."""

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
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
OFFICIAL_RESEARCH = ROOT / "docs/validation/companion-gdey0154d67-t03-official-partial-refresh-research-20260720.json"
SOURCE_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
RECOVERY_GATE = ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
DEFAULT_OUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-old-new-ram-static-20260720.json"
SCHEMA = "companion.wb55.gdey0154d67_t03.vendor_partial_old_new_ram_static.v1"
PASS = "PASS_STATIC_OWNER_AUTHORIZED_VENDOR_PARTIAL_OLD_NEW_RAM_AB"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load(path: pathlib.Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(decoded, dict):
        raise ValueError(f"{path} is not a JSON object")
    return decoded


def main() -> int:
    required = (DRIVER, MAKEFILE, BUILD, RUNNER, REQUIREMENTS, OFFICIAL_RESEARCH, SOURCE_AUDIT, RECOVERY_GATE)
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        report: dict[str, Any] = {"schema_id": SCHEMA, "status": "NO_GO_INPUT_MISSING", "failures": missing}
    else:
        driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
        makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
        build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
        runner = RUNNER.read_text(encoding="utf-8-sig", errors="replace")
        requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
        official = load(OFFICIAL_RESEARCH)
        source = load(SOURCE_AUDIT)
        recovery = load(RECOVERY_GATE)
        old_plane = driver.find("ssd1681_write_plane_region(0x26u,\n                                                    s_previous_frame")
        new_plane = driver.find("ssd1681_write_plane_region(0x24u, s_frame")
        checks = {
            "owner_authorizes_official_method_ab": all(
                token in requirements
                for token in (
                    "COMP-REQ-206",
                    "old data, then new data, then update",
                    "0x26` write of the CPU-held prior region before the existing `0x24`",
                )
            ),
            "official_research_is_present_and_non_promotional": official.get("status")
            == "PASS_OFFICIAL_METHOD_IDENTIFIED_PANEL_IDENTITY_REMAINS_UNPROVEN"
            and official.get("allowed_single_variable_diagnostic", {}).get("partial", "").startswith("retain source reset")
            and official.get("identity_boundary", "").startswith("The official web source"),
            "source_audit_still_passes_and_binds_current_driver": source.get("machine_status") == "PASS_AUDIT_COMPLETE"
            and source.get("source_manifest", {}).get("critical_sources", {}).get("current_ssd1681_target", {}).get("sha256")
            == digest(DRIVER),
            "white_black_recovery_gate_still_passes": recovery.get("status")
            == "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST",
            "old_new_mode_is_default_off_and_requires_slow_source_path": all(
                token in driver
                for token in (
                    "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OLD_NEW_RAM_DIAGNOSTIC 0",
                    "SSD1681 vendor partial old/new RAM diagnostic requires the source slow-motion diagnostic",
                )
            ),
            "only_changed_region_ram_planes_differ": old_plane >= 0
            and new_plane >= 0
            and old_plane < new_plane
            and "good_display_vendor_partial_old_new_ram_ab" in driver
            and "? (partial ? (vendor_partial_old_new_ram ? 2u : 1u) : 2u)" in driver,
            "source_reset_border_control_and_busy_remain": all(
                token in driver
                for token in (
                    "ssd1681_reset_vendor_partial_basemap",
                    "vendor_partial_source region_reset low_ms=10 high_ms=10",
                    "static const uint8_t border_lock[] = {0x80u};",
                    "? 0xFFu",
                    "ssd1681_command(0x20u)",
                )
            ),
            "separate_build_and_runner_mode_exist": all(
                token in build
                for token in (
                    "[switch]$EpaperSsd1681VendorPartialOldNewRamDiagnostic",
                    "EPAPER_SSD1681_VENDOR_PARTIAL_OLD_NEW_RAM_DIAGNOSTIC=1",
                    "BUILD_DIR=build_vendor_partial_old_new_ram_diagnostic",
                    "TARGET=Companion_Nucleo_WB55RG_VendorPartialOldNewRamDiagnostic",
                )
            )
            and "EPAPER_SSD1681_VENDOR_PARTIAL_OLD_NEW_RAM_DIAGNOSTIC" in makefile
            and "[switch] $OldNewRam" in runner,
        }
        failures = [name for name, passed in checks.items() if not passed]
        report = {
            "schema_id": SCHEMA,
            "status": PASS if not failures else "NO_GO_STATIC_VENDOR_PARTIAL_OLD_NEW_RAM_AB_INCOMPLETE",
            "claim_scope": "owner-authorized current-room, default-disabled old/new RAM A/B; no LUT, temperature or production claim",
            "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
            "checks": checks,
            "failures": failures,
            "source": {
                "target_driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
                "official_research": {"path": rel(OFFICIAL_RESEARCH), "sha256": digest(OFFICIAL_RESEARCH)},
                "source_audit": {"path": rel(SOURCE_AUDIT), "sha256": digest(SOURCE_AUDIT)},
                "recovery_gate": {"path": rel(RECOVERY_GATE), "sha256": digest(RECOVERY_GATE)},
            },
            "controlled_behavior": {
                "baseline": "supplier 0x24 then 0x26, 5000 bytes each, 0xF7, 0x20, BUSY",
                "partial": "prior changed bytes 0x26, current changed bytes 0x24, supplier 0xFF, 0x20, BUSY",
                "single_variable": "second RAM-plane payload only",
                "maximum_region_bytes_per_plane": 567,
                "production_default": "disabled",
                "max_frames": 360,
                "temperature_claim": "none",
                "normal_restore_required": True,
            },
        }
    DEFAULT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: old/new RAM static check -> {rel(DEFAULT_OUT)}")
    return 0 if report["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
