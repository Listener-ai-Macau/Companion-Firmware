#!/usr/bin/env python3
"""Create a source/hash audit for the official public GDEH0154D67 sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPPLIER_ROOT = pathlib.Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷")
SUPPLIER_EPAPER = SUPPLIER_ROOT / "EPD_W21/EPAPER.c"
SUPPLIER_MAIN = SUPPLIER_ROOT / "User/main.c"
ARCHIVE = ROOT / ".cache/reference/good-display-gdeh0154d67/S-GDEH0154D67.rar"
PUBLIC_ROOT = ROOT / ".cache/reference/good-display-gdeh0154d67/extracted/S-GDEH0154D67-20221011"
PUBLIC_EPAPER = PUBLIC_ROOT / "HARDWARE/EPD/Display_EPD_W21.c"
PUBLIC_MAIN = PUBLIC_ROOT / "USER/main.c"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DEFAULT_OUT = ROOT / "docs/validation/companion-gdeh0154d67-public-reference-audit-20260720.json"
SCHEMA_ID = "companion.gdeh0154d67.public_reference_audit.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def source_entry(path: pathlib.Path) -> dict[str, Any]:
    return {"path": rel(path), "sha256": digest(path), "bytes": path.stat().st_size}


def has_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def evaluate() -> tuple[dict[str, Any], bool]:
    inputs = (SUPPLIER_EPAPER, SUPPLIER_MAIN, ARCHIVE, PUBLIC_EPAPER, PUBLIC_MAIN, DRIVER)
    missing = [rel(path) for path in inputs if not path.is_file()]
    if missing:
        return ({"schema_id": SCHEMA_ID, "status": "FAIL_INPUT_MISSING", "failures": missing}, False)

    supplier = SUPPLIER_EPAPER.read_text(encoding="utf-8", errors="replace")
    public = PUBLIC_EPAPER.read_text(encoding="utf-8", errors="replace")
    supplier_main = SUPPLIER_MAIN.read_text(encoding="utf-8", errors="replace")
    public_main = PUBLIC_MAIN.read_text(encoding="utf-8", errors="replace")
    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    checks = {
        "panel_geometry_200x200_is_shared": has_all(supplier, ("0x18", "0xC7"))
        and has_all(public, ("0x18", "0xC7")),
        "shared_base_map_sequence": has_all(
            supplier, ("void EPD_SetRAMValue_BaseMap", "Epaper_Write_Command(0x24)", "Epaper_Write_Command(0x26)", "EPD_Update()")
        ) and has_all(
            public, ("void EPD_SetRAMValue_BaseMap", "Epaper_Write_Command(0x24)", "Epaper_Write_Command(0x26)", "EPD_Update()")
        ),
        "shared_local_ram_update_control": has_all(
            supplier, ("void EPD_Dis_Part(", "Epaper_Write_Command(0x24)", "Epaper_Write_Data(0xFF)", "Epaper_Write_Command(0x20)")
        ) and has_all(
            public, ("void EPD_Dis_Part(", "Epaper_Write_Command(0x24)", "Epaper_Write_Data(0xFF)", "Epaper_Write_Command(0x20)")
        ),
        "supplier_only_159_byte_one_second_lut": all(
            token in supplier for token in ("LUT_DATA[159]", "void EPD_HW_Init_LUT", "void EPD_Update_LUT", "Epaper_Write_Command(0x32)")
        ) and "LUT_DATA[159]" not in public,
        "supplier_partial_has_reset_and_border_lock": has_all(
            supplier, ("void EPD_Dis_Part(", "driver_delay_xms(10)", "Epaper_Write_Data(0x80)")),
        "public_reference_documents_no_flash_local_claim": "partial refresh is performed, the screen does not flash" in public_main,
        "public_reference_does_not_bind_physical_fpc": "0154BN-D67-D2" not in public
        and "0154BN-D67-D2" not in public_main,
        "target_has_a_compile_time_disabled_cleanup_draw_candidate": has_all(
            driver,
            (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC 0",
                "good_display_vendor_partial_cleanup_draw",
                "SSD1681_VENDOR_PARTIAL_SOURCE_SHA256",
            ),
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    audited = not failures
    report = {
        "schema_id": SCHEMA_ID,
        "status": "PASS_PUBLIC_REFERENCE_AUDITED_NO_OPERATIONAL_PROFILE_PROMOTION" if audited else "FAIL_REFERENCE_AUDIT_DRIFT",
        "machine_status": "PASS_AUDIT_NO_GO_FOR_PROFILE_PROMOTION" if audited else "FAIL_AUDIT_DRIFT",
        "claim_scope": "hash and source-command comparison only; public download is research input and not a new firmware LUT source",
        "source_manifest": {
            "supplier_epaper_c": source_entry(SUPPLIER_EPAPER),
            "supplier_main_c": source_entry(SUPPLIER_MAIN),
            "official_archive": source_entry(ARCHIVE),
            "official_public_epaper_c": source_entry(PUBLIC_EPAPER),
            "official_public_main_c": source_entry(PUBLIC_MAIN),
            "current_target_driver": source_entry(DRIVER),
        },
        "checks": checks,
        "failures": failures,
        "word_level_diff_summary": {
            "shared": [
                "200x200 RAM geometry via X end 0x18 and Y end 0x00C7",
                "base map writes 0x24 then 0x26 before normal 0xF7/0x20/BUSY activation",
                "local path writes 0x24 in a window then 0xFF/0x20/BUSY",
            ],
            "supplier_only": [
                "159-byte LUT_DATA and its 153-byte 0x32 load plus 0xC7 one-second full-frame route",
                "100 ms base initialization reset and 10 ms local EPD_Dis_Part reset with 0x3C=0x80 border lock",
            ],
            "public_only": [
                "EPD_HW_Init_GUI mirror variant",
                "source comment asserting partial refresh does not flash",
            ],
        },
        "matching_conclusion": {
            "source_sequence_correlated": True,
            "physical_fpc_controller_identity_proven": False,
            "no_black_flash_profile_proven_clean": False,
            "production_profile_allowed": False,
            "reason": "The public sample corroborates the supplier's local 0xFF command family, but it supplies neither a binding to 0154BN-D67-D2 nor evidence that the observed local residue is eliminated. It is therefore not promoted into firmware as a new operational waveform source.",
        },
    }
    return report, audited


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report, audited = evaluate()
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: public GDEH reference audit -> {rel(args.out)}")
    return 0 if audited else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
