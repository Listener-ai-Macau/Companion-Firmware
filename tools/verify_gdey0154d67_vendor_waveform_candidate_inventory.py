#!/usr/bin/env python3
"""Inventory only the literal waveform candidates in the supplied Good Display tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR_ROOT = pathlib.Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷")
EPAPER = VENDOR_ROOT / "EPD_W21" / "EPAPER.c"
MAIN = VENDOR_ROOT / "User" / "main.c"
README = VENDOR_ROOT / "read me.txt"
TARGET = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-waveform-candidate-inventory-20260720.json"
SCHEMA_ID = "companion.gdey0154d67_t03.vendor_waveform_candidate_inventory.v1"
ARRAY_RE = re.compile(
    r"const\s+unsigned\s+char\s+LUT_DATA\s*\[\s*159\s*\]\s*=\s*\{(?P<body>.*?)\}\s*;",
    re.DOTALL,
)
HEX_RE = re.compile(r"0x([0-9A-Fa-f]{2})\b")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def is_in_block_comment(source: str, position: int) -> bool:
    return source.rfind("/*", 0, position) > source.rfind("*/", 0, position)


def preceding_label(source: str, position: int) -> str:
    context = source[max(0, position - 96):position]
    if "//1.5s" in context:
        return "commented_1_5s"
    if "Refresh time about 1s." in source[:position]:
        return "active_about_1s"
    return "unlabelled_lut"


def array_candidates(source: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, match in enumerate(ARRAY_RE.finditer(source)):
        values = [int(value, 16) for value in HEX_RE.findall(match.group("body"))]
        line = source.count("\n", 0, match.start()) + 1
        candidates.append(
            {
                "id": preceding_label(source, match.start()),
                "ordinal": index + 1,
                "line": line,
                "compiled": not is_in_block_comment(source, match.start()),
                "declared_bytes": 159,
                "literal_bytes": len(values),
                "lut_sha256": hashlib.sha256(bytes(values)).hexdigest().upper(),
                "payload_0x32_bytes": len(values[:153]),
                "payload_0x32_sha256": hashlib.sha256(bytes(values[:153])).hexdigest().upper(),
                "voltage_tail": {
                    "0x3F_eopq": values[153] if len(values) > 153 else None,
                    "0x03_vgh": values[154] if len(values) > 154 else None,
                    "0x04_vsh1": values[155] if len(values) > 155 else None,
                    "0x04_vsh2": values[156] if len(values) > 156 else None,
                    "0x04_vsl": values[157] if len(values) > 157 else None,
                    "0x2C_vcom": values[158] if len(values) > 158 else None,
                },
                "_values": values,
            }
        )
    return candidates


def build_report() -> dict[str, Any]:
    required = (EPAPER, MAIN, README, TARGET)
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {
            "schema_id": SCHEMA_ID,
            "status": "NO_GO_VENDOR_WAVEFORM_SOURCE_MISSING",
            "failures": missing,
        }

    source = EPAPER.read_text(encoding="utf-8-sig", errors="replace")
    main = MAIN.read_text(encoding="utf-8-sig", errors="replace")
    readme = README.read_text(encoding="utf-8-sig", errors="replace")
    candidates = array_candidates(source)
    failures: list[str] = []
    if len(candidates) != 2:
        failures.append(f"expected exactly two literal LUT_DATA declarations, found {len(candidates)}")
    active = next((entry for entry in candidates if entry["compiled"]), None)
    commented = next((entry for entry in candidates if not entry["compiled"]), None)
    if active is None:
        failures.append("compiled about-1s LUT_DATA candidate missing")
    if commented is None:
        failures.append("commented 1.5s LUT_DATA candidate missing")
    for candidate in candidates:
        if candidate["literal_bytes"] != 159:
            failures.append(f"{candidate['id']} is not exactly 159 bytes")
        if candidate["payload_0x32_bytes"] != 153:
            failures.append(f"{candidate['id']} does not expose exactly 153 0x32 bytes")
        candidate.pop("_values", None)

    differences: list[dict[str, int]] = []
    if active is not None and commented is not None:
        active_values = [int(value, 16) for value in HEX_RE.findall(
            next(match.group("body") for match in ARRAY_RE.finditer(source)
                 if not is_in_block_comment(source, match.start()))
        )]
        commented_values = [int(value, 16) for value in HEX_RE.findall(
            next(match.group("body") for match in ARRAY_RE.finditer(source)
                 if is_in_block_comment(source, match.start()))
        )]
        differences = [
            {"index": index, "about_1s": current, "commented_1_5s": alternate}
            for index, (current, alternate) in enumerate(zip(active_values, commented_values))
            if current != alternate
        ]

    checks = {
        "active_candidate_is_compiled_and_exactly_159_bytes": (
            active is not None and active["literal_bytes"] == 159
        ),
        "commented_candidate_is_not_compiled_and_exactly_159_bytes": (
            commented is not None and commented["literal_bytes"] == 159
        ),
        "both_candidates_have_exactly_153_byte_0x32_payloads": all(
            candidate["payload_0x32_bytes"] == 153 for candidate in candidates
        ),
        "both_candidates_have_same_voltage_tail": (
            active is not None
            and commented is not None
            and active["voltage_tail"] == commented["voltage_tail"]
        ),
        "source_lut_initializer_loads_tail_then_0x32_payload": all(
            token in source
            for token in (
                "Epaper_Write_Command(0x3F)",
                "Epaper_Write_Command(0x03)",
                "Epaper_Write_Command(0x04)",
                "Epaper_Write_Command(0x2C)",
                "Epaper_Write_Command(0x32)",
                "for(count=0;count<153;count++)",
            )
        ),
        "source_lut_activation_is_full_frame_c7_not_partial_ff": all(
            token in source
            for token in (
                "void EPD_Update_LUT(void)",
                "Epaper_Write_Data(0xC7)",
                "void EPD_WhiteScreen_ALL_LUT",
                "for(i=0;i<5000;i++)",
            )
        ) and "EPD_Update_LUT" not in main[main.find("EPD_SetRAMValue_BaseMap"):],
        "source_partial_path_uses_ff_and_has_no_lut_initializer": all(
            token in source for token in ("void EPD_Part_Update(void)", "Epaper_Write_Data(0xFF)")
        ) and "EPD_HW_Init_LUT" not in main[main.find("Partial refresh time demo"):main.find("Clear:")],
        "readme_requires_hardware_reset_and_border_80_after_partial": all(
            token in readme for token in ("hardware reset", "0x05-->0x80")
        ),
        "temperature_bands_or_cwf1_are_not_supplied": re.search(
            r"\b(?:CWF\d|temperature\s+(?:table|band|range)|[-+]?\d+\s*(?:deg(?:ree)?s?\s*C|C))\b",
            source + main + readme,
            flags=re.IGNORECASE,
        ) is None,
        "commented_candidate_is_not_an_executable_profile_selection": (
            commented is not None
            and commented["compiled"] is False
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    failures.extend(failed_checks)
    status = (
        "NO_GO_VENDOR_WAVEFORM_CANDIDATES_UNBOUND_TO_PANEL_PARTIAL_RECOVERY"
        if not failures
        else "NO_GO_VENDOR_WAVEFORM_CANDIDATE_INVENTORY_INCOMPLETE"
    )
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": "read-only inventory and classification of literal supplier LUT candidates; no physical run or LUT mutation",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "checks": checks,
        "failures": failures,
        "candidates": candidates,
        "candidate_byte_differences": differences,
        "conclusion": {
            "what_the_package_supplies": [
                "One compiled about-1s 159-byte LUT_DATA array and one commented-out about-1.5s literal alternative.",
                "The same six-byte voltage tail for both arrays, then a 153-byte 0x32 LUT payload.",
                "A 0xC7 full-frame LUT activation path with 5000-byte 0x24 writes.",
                "A separate 0xFF local-update path with reset and border 0x80, but no selected LUT or content-preserving residue recovery.",
            ],
            "what_the_package_does_not_supply": [
                "A temperature-banded CWF1 table or a temperature-to-LUT selection rule.",
                "A panel/FPC/controller binding for the observed 0154BN-D67-D2 module.",
                "An executable selection mechanism for the commented 1.5s array.",
                "A supplier-defined repeated-local-refresh recovery that removes residue without a full white clear.",
            ],
            "disposition": {
                "active_about_1s": "production-off only after the existing identity and rail gates pass; not a partial-refresh cure.",
                "commented_1_5s": "NO_GO: source text exists, but it is commented out and unbound; do not enable or mutate it without explicit supplier confirmation and full gates.",
                "self_authored_waveform": "prohibited",
                "production_dynamic_expression": "NO_GO",
            },
        },
        "source": {
            "vendor_root": str(VENDOR_ROOT),
            "epaper_c": {"path": str(EPAPER), "sha256": digest(EPAPER)},
            "main_c": {"path": str(MAIN), "sha256": digest(MAIN)},
            "readme": {"path": str(README), "sha256": digest(README)},
            "target_driver": {"path": rel(TARGET), "sha256": digest(TARGET)},
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    try:
        report = build_report()
    except (OSError, UnicodeDecodeError, ValueError, StopIteration) as error:
        print(f"NO_GO: cannot inventory supplier waveform candidates: {error}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: supplier waveform candidate inventory -> {rel(output)}")
    return 0 if report["status"] == "NO_GO_VENDOR_WAVEFORM_CANDIDATES_UNBOUND_TO_PANEL_PARTIAL_RECOVERY" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
