#!/usr/bin/env python3
"""Build and audit the first production-off SSD1681 custom Mode2 candidate."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
SUPPLIER = Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
SSD1681_PDF = (
    ROOT
    / ".cache/validation/ssd1681-mechanism-lut-research-20260721/official-sources"
    / "SSD1681V0.13_Spec-200529.pdf"
)
PRIOR_RESEARCH = (
    ROOT
    / "docs/validation/companion-ssd1681-mechanism-lut-research-disposition-20260721.json"
)
OUT = (
    ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-transition-workbench-20260721.json"
)

EXPECTED_HASHES = {
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    SSD1681_PDF: "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B",
    PRIOR_RESEARCH: "478EECD541623713C665D2FCFCCF17743B9F3489A934097978033C1893E20F93",
}
EXPECTED_LUT_HEX = (
    "AA8055400000000000000000"
    "5410A8200000000000000000"
    "AA8055400000000000000000"
    "5410A8200000000000000000"
    "000000000000000000000000"
    "0505000505000003020000000000"
    "0505000505000003020000000000"
    + "00" * 56
    + "222222222222000000"
    + "221741A83258"
)
EXPECTED_DIFF_OFFSETS = [0, 1, 2, 3, 36, 37, 38, 39]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def parse_lut(source: str) -> list[int]:
    match = re.search(
        r"const\s+unsigned\s+char\s+LUT_DATA\[159\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        return []
    return [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1))]


def page_text(reader: PdfReader, page_number: int) -> str:
    return reader.pages[page_number - 1].extract_text() or ""


def main() -> int:
    errors: list[str] = []
    hashes: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            errors.append(f"missing locked input: {path}")
            continue
        actual = sha(path)
        hashes[str(path)] = actual
        if actual != expected:
            errors.append(f"hash mismatch: {path}")

    supplier_values = parse_lut(SUPPLIER.read_text(encoding="latin-1")) if SUPPLIER.is_file() else []
    expected_values = list(bytes.fromhex(EXPECTED_LUT_HEX))
    if supplier_values != expected_values:
        errors.append("supplier LUT_DATA is not the locked 159-byte source sequence")

    candidate = supplier_values.copy()
    for offset in EXPECTED_DIFF_OFFSETS:
        if offset < len(candidate):
            candidate[offset] = 0
    differences = [
        {"offset": index, "supplier_hex": f"{old:02X}", "candidate_hex": f"{new:02X}"}
        for index, (old, new) in enumerate(zip(supplier_values, candidate))
        if old != new
    ]
    if [item["offset"] for item in differences] != EXPECTED_DIFF_OFFSETS:
        errors.append("candidate changes bytes outside the two stationary voltage tables")
    if len(candidate) != 159:
        errors.append("candidate waveform is not 159 bytes")
    if candidate[12:36] != supplier_values[12:36]:
        errors.append("transition LUT1/LUT2 bytes changed")
    if candidate[40:159] != supplier_values[40:159]:
        errors.append("timing/frame/XON/tail bytes changed")
    if candidate[153:159] != [0x22, 0x17, 0x41, 0xA8, 0x32, 0x58]:
        errors.append("protected voltage tail changed")

    registry = REGISTRY.read_text(encoding="utf-8")
    if "COMP-REQ-285" not in registry or "22 17 41 A8 32 58" not in registry:
        errors.append("COMP-REQ-285 custom Mode2 authorization is missing")

    official_evidence: dict[str, object] = {}
    if SSD1681_PDF.is_file():
        reader = PdfReader(str(SSD1681_PDF))
        p13 = page_text(reader, 13)
        p15 = page_text(reader, 15)
        p26 = page_text(reader, 26)
        p30 = page_text(reader, 30)
        evidence_checks = {
            "page13_table_6_5_maps_ram_pairs_to_lut0_3": all(
                token in p13 for token in ("Table 6-5", "LUT 0", "LUT 1", "LUT 2", "LUT 3")
            ),
            "page15_defines_159_byte_waveform": "159 bytes" in p15 and "0~152" in p15,
            "page26_cf_displays_mode2_without_load": "CF" in p26 and "Display with DISPLAY Mode 2" in p26,
            "page26_ff_loads_temperature_then_displays_mode2": "FF" in p26 and "Load temperature value" in p26,
            "page30_pingpong_only_mode2": "PingPong for Display Mode 2" in p30
            and "not support" in p30
            and "Display Mode 1" in p30,
        }
        official_evidence = {"pdf_pages": [13, 15, 26, 30], "checks": evidence_checks}
        errors.extend(name for name, passed in evidence_checks.items() if not passed)

    transition_oracle = [
        {"old_0x26": 0, "new_0x24": 0, "class": "BB", "lut": 0, "candidate_drive": "suppressed"},
        {"old_0x26": 0, "new_0x24": 1, "class": "BW", "lut": 1, "candidate_drive": "supplier_exact"},
        {"old_0x26": 1, "new_0x24": 0, "class": "WB", "lut": 2, "candidate_drive": "supplier_exact"},
        {"old_0x26": 1, "new_0x24": 1, "class": "WW", "lut": 3, "candidate_drive": "suppressed"},
    ]

    report = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_transition_workbench.v1",
        "status": "PASS_WORKBENCH_ADMIT_STATIONARY_SUPPRESSION_MODE2_R1" if not errors else "NO_GO_WORKBENCH",
        "errors": errors,
        "hardware_contact": 0,
        "requirement": "COMP-REQ-285",
        "candidate": {
            "name": "custom_mode2_stationary_suppression_r1",
            "production_enabled": False,
            "single_mechanism_variable": "suppress stationary BB/WW voltage drive while retaining supplier BW/WB transition drive",
            "supplier_lut_hex": bytes(supplier_values).hex().upper(),
            "supplier_lut_sha256": sha_bytes(bytes(supplier_values)) if supplier_values else None,
            "candidate_lut_hex": bytes(candidate).hex().upper(),
            "candidate_lut_sha256": sha_bytes(bytes(candidate)) if candidate else None,
            "byte_differences": differences,
            "unchanged_ranges": [
                {"start": 4, "end_inclusive": 35, "meaning": "remaining LUT0 plus exact BW and WB transition LUTs"},
                {"start": 40, "end_inclusive": 152, "meaning": "LUT3 remainder, LUT4, timing, repeat, frame-rate and XON"},
                {"start": 153, "end_inclusive": 158, "meaning": "protected EOPT/VGH/VSH1/VSH2/VSL/VCOM tail"},
            ],
            "protected_tail_hex": bytes(candidate[153:159]).hex().upper(),
        },
        "transition_oracle": transition_oracle,
        "command_topology": {
            "load": "write bytes 0..152 under 0x32, then byte153 under 0x3F, byte154 under 0x03, bytes155..157 under 0x04, byte158 under 0x2C",
            "per_transition": "set local window; write explicit previous bytes under 0x26; reset pointer; write explicit current bytes under 0x24; 0x22=0xCF; 0x20; BUSY",
            "why_0xCF": "SSD1681 page 26 defines CF as Display Mode2 with no LUT/temperature reload, preserving the MCU-loaded custom LUT",
            "why_not_0xFF": "SSD1681 page 26 defines FF as temperature load plus Display Mode2; it can select OTP waveform state and is excluded from the loaded-LUT candidate",
            "hard_reset_after_load": False,
        },
        "official_evidence": official_evidence,
        "scope": {
            "physical_stage_max_local_activations": 16,
            "required_classes": ["WW", "WB", "BW", "BB"],
            "full_frame_activation_allowed": False,
            "voltage_or_temperature_tuning_allowed": False,
            "promotion_allowed": False,
        },
        "source_hashes": hashes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors, "artifact": str(OUT)}))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
