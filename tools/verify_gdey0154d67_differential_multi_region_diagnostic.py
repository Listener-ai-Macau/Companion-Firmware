#!/usr/bin/env python3
"""Verify the default-off, source-bounded SSD1681 multi-region data diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR_EPAPER = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
BUILD_SCRIPT = ROOT / "tools/build_nucleo_bringup.ps1"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
DIAGNOSTIC_ELF = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_differential_multi_region_diagnostic/"
    "Companion_Nucleo_WB55RG_DifferentialMultiRegionDiagnostic.elf"
)
OUTPUT = (
    ROOT
    / "docs/validation/companion-gdey0154d67-t03-differential-multi-region-diagnostic-20260720.json"
)
SCHEMA_ID = "companion.gdey0154d67_t03.differential_multi_region_diagnostic.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def source_function(source: str) -> str:
    match = re.search(
        r"void EPD_Dis_Part_myself\(.*?(?=//Loading waveform)", source, flags=re.DOTALL
    )
    return "" if match is None else match.group(0)


def contains_all(source: str, tokens: tuple[str, ...]) -> bool:
    return all(token in source for token in tokens)


def build_report() -> dict[str, Any]:
    required = (VENDOR_EPAPER, TARGET, BUILD_SCRIPT, MAKEFILE, DIAGNOSTIC_ELF)
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {
            "schema_id": SCHEMA_ID,
            "status": "NO_GO_DIFFERENTIAL_MULTI_REGION_INPUT_MISSING",
            "checks": {},
            "failures": missing,
        }

    vendor = VENDOR_EPAPER.read_text(encoding="utf-8-sig", errors="replace")
    target = TARGET.read_text(encoding="utf-8-sig", errors="replace")
    build_script = BUILD_SCRIPT.read_text(encoding="utf-8-sig", errors="replace")
    makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    supplier_multi_region = source_function(vendor)
    checks = {
        "supplier_stages_exactly_five_regions_before_one_existing_partial_activation": (
            supplier_multi_region.count("Epaper_Write_Command(0x24)") == 5
            and supplier_multi_region.count("EPD_Part_Update();") == 1
        ),
        "target_macro_defaults_off_and_is_binary_guarded": contains_all(
            target,
            (
                "#define COMPANION_EPAPER_SSD1681_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC 0",
                "SSD1681 differential multi-region diagnostic must be 0 or 1",
            ),
        ),
        "target_never_exceeds_supplier_five_region_bound": (
            "#define SSD1681_DIFFERENTIAL_MULTI_REGION_MAX 5u" in target
            and "region_count >= SSD1681_DIFFERENTIAL_MULTI_REGION_MAX" in target
        ),
        "target_derives_regions_from_actual_previous_and_current_frame": contains_all(
            target,
            (
                "static uint8_t ssd1681_windows_from_difference",
                "if (s_frame[index] == s_previous_frame[index])",
                "regions[0] = ssd1681_window_from_difference();",
                "differential_region_bytes <",
            ),
        ),
        "target_writes_old_and_new_plane_for_every_selected_region": contains_all(
            target,
            (
                "ssd1681_set_differential_region_window",
                "ssd1681_write_plane_region(\n                                                    0x26u,",
                "ssd1681_write_plane_region(\n                                                    0x24u,",
                "differential_multi_region index=",
            ),
        ),
        "target_reuses_existing_single_partial_activation_without_lut_mutation": contains_all(
            target,
            (
                "ssd1681_refresh_display(selection.decision,",
                "? 0xFCu",
            ),
        ) and "ssd1681_vendor_1s_lut" not in target[target.find("ssd1681_windows_from_difference"):target.find("#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC")],
        "build_switch_is_isolated_and_forwards_the_c_macro": contains_all(
            build_script,
            (
                "[switch]$EpaperSsd1681DifferentialMultiRegionDiagnostic",
                "Differential multi-region is an isolated source-bound transport diagnostic.",
                "EPAPER_SSD1681_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC=1",
                "BUILD_DIR=build_differential_multi_region_diagnostic",
            ),
        ) and contains_all(
            makefile,
            (
                "ifeq ($(EPAPER_SSD1681_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC),1)",
                "-DCOMPANION_EPAPER_SSD1681_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC=1",
            ),
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    status = (
        "PASS_MACHINE_SOURCE_BOUND_DIAGNOSTIC_DEFAULT_OFF"
        if not failures
        else "NO_GO_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC_INCOMPLETE"
    )
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": (
            "machine-only verification of a default-off, source-bounded multi-window data "
            "diagnostic; it makes no physical, no-residue, LUT, temperature, or production claim"
        ),
        "checks": checks,
        "failures": failures,
        "source": {
            "vendor_epaper_c": {"path": str(VENDOR_EPAPER), "sha256": digest(VENDOR_EPAPER)},
            "target_driver": {"path": rel(TARGET), "sha256": digest(TARGET)},
            "build_script": {"path": rel(BUILD_SCRIPT), "sha256": digest(BUILD_SCRIPT)},
            "makefile": {"path": rel(MAKEFILE), "sha256": digest(MAKEFILE)},
            "diagnostic_elf": {"path": rel(DIAGNOSTIC_ELF), "sha256": digest(DIAGNOSTIC_ELF)},
        },
        "diagnostic_contract": {
            "default_compilation": "off",
            "maximum_disjoint_regions": 5,
            "region_selection": "actual previous/current framebuffer byte differences; use multiple regions only when their total payload is smaller than one bounding window",
            "per_region_ram_payload": "old 0x26 then new 0x24",
            "activation": "one existing differential 0xFC/0x20/BUSY sequence after all selected regions",
            "lut_policy": "no LUT byte was added, changed, or selected by this diagnostic",
            "physical_policy": "not flashed; panel identity and White-rail prerequisites remain controlling",
        },
        "disposition": {
            "production_dynamic_expression": "NO_GO",
            "observed_residue": "unresolved; smaller payload cannot replace a panel-bound residue-recovery waveform",
            "allowed_next_step": "only a gate-authorized physical diagnostic with canonical operator evidence after identity and White-rail prerequisites",
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    try:
        report = build_report()
    except (OSError, UnicodeDecodeError) as error:
        print(f"NO_GO: cannot verify differential multi-region diagnostic: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: differential multi-region diagnostic -> {rel(output)}")
    return 0 if report["status"] == "PASS_MACHINE_SOURCE_BOUND_DIAGNOSTIC_DEFAULT_OFF" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
