#!/usr/bin/env python3
"""Fail-closed, no-hardware R5 audit of SSD1681 Mode2/LUT mapping evidence."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = (
    ROOT
    / ".cache/validation/ssd1681-mechanism-lut-research-20260721/official-sources"
    / "SSD1681V0.13_Spec-200529.pdf"
)
SUPPLIER = Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
OUT = (
    ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-mapping-r5-disposition-20260721.json"
)

INPUTS = {
    "controller_state": ROOT
    / "docs/validation/companion-ssd1681-reset-read-controller-state-machine-20260721.json",
    "ram_fingerprint": ROOT
    / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json",
    "mechanism_research": ROOT
    / "docs/validation/companion-ssd1681-mechanism-lut-research-disposition-20260721.json",
    "r1_workbench": ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-transition-workbench-20260721.json",
    "r2_workbench": ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r2-20260721.json",
    "r3_workbench": ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r3-20260721.json",
    "r4_workbench": ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r4-20260721.json",
    "r4_disposition": ROOT
    / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r4-disposition-20260721.json",
}

EXPECTED_HASHES = {
    PDF: "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B",
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    INPUTS["controller_state"]: "70D235CC0228C8326438B325A0A145D66AFF9D0D60BA5A38200DD6F3E4666E13",
    INPUTS["ram_fingerprint"]: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    INPUTS["mechanism_research"]: "478EECD541623713C665D2FCFCCF17743B9F3489A934097978033C1893E20F93",
    INPUTS["r1_workbench"]: "8653B6ABD0E299E6C99B50C5A086EE840E38CED37F358F7AA326B37F7933CF05",
    INPUTS["r2_workbench"]: "266FC130BAEB68219A759A9A15E292D6E2BED97919FC5A9F0086BCC6733A5148",
    INPUTS["r3_workbench"]: "CCFB9EF0AE1CBF1038A7ED4E188D3A6DF8303CFF5E18C4391418A20310C16124",
    INPUTS["r4_workbench"]: "E7467B808CE7BD1BE317BC282B7990CF343922DE8C15B092588B9968DEAB444D",
    INPUTS["r4_disposition"]: "C4E52FF8B1E0A4A2E7D084E65166BACC5748E96B31A3822DC32C275FD4C259D0",
}

EXPECTED_STATUSES = {
    "controller_state": "PASS_MACHINE_RESET_READ_CONTROLLER_STATE_RESTORED",
    "ram_fingerprint": "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED",
    "mechanism_research": "RESEARCH_DISPOSITION_MISSING_PANEL_BOUND_LOCAL_MODE2_RULE_NO_R3",
    "r1_workbench": "PASS_WORKBENCH_ADMIT_STATIONARY_SUPPRESSION_MODE2_R1",
    "r2_workbench": "PASS_WORKBENCH_ADMIT_TP_DURATION_SCALE_MODE2_R2",
    "r3_workbench": "PASS_WORKBENCH_ADMIT_MINIMUM_INTEGER_TP19_MODE2_R3",
    "r4_workbench": "PASS_WORKBENCH_ADMIT_UNIFORM_ACTIVE_TP16_MODE2_R4",
    "r4_disposition": "NO_GO_R4_MACHINE_PASS_OPERATOR_FAILED_SCREEN_DIRTY_EXACT_RAW_RESTORED",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def page_text(reader: PdfReader, page_number: int) -> str:
    return reader.pages[page_number - 1].extract_text() or ""


def parse_supplier_lut() -> list[int]:
    source = SUPPLIER.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"const\s+unsigned\s+char\s+LUT_DATA\[159\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        return []
    return [
        int(value, 16)
        for value in re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1))
    ]


def decode_mode2_slots(display_option_hex: str) -> tuple[list[int], bool]:
    raw = bytes.fromhex(display_option_hex)
    if len(raw) != 5:
        return [], False
    slots: list[int] = []
    for byte_index, value in enumerate(raw[:4]):
        for bit in range(8):
            if value & (1 << bit):
                slots.append(byte_index * 8 + bit)
    for bit in range(4):
        if raw[4] & (1 << bit):
            slots.append(32 + bit)
    return slots, bool(raw[4] & 0x40)


def candidate_lut(data: dict[str, object], key: str) -> list[int]:
    candidate = data.get("candidate", {})
    if not isinstance(candidate, dict):
        return []
    value = candidate.get(key, "")
    if not isinstance(value, str):
        return []
    try:
        return list(bytes.fromhex(value))
    except ValueError:
        return []


def offsets(data: dict[str, object], key: str) -> list[int]:
    candidate = data.get("candidate", {})
    if not isinstance(candidate, dict):
        return []
    rows = candidate.get(key, [])
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("offset"), int):
            result.append(row["offset"])
    return result


def main() -> int:
    errors: list[str] = []
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            errors.append(f"missing locked input: {path}")
        elif sha(path) != expected:
            errors.append(f"hash mismatch: {path}")

    evidence: dict[str, dict[str, object]] = {}
    for name, path in INPUTS.items():
        if not path.is_file():
            evidence[name] = {}
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        evidence[name] = data
        if data.get("status") != EXPECTED_STATUSES[name]:
            errors.append(f"status drift: {name}")

    reader = PdfReader(str(PDF))
    p13 = page_text(reader, 13)
    p15 = page_text(reader, 15)
    p26 = page_text(reader, 26)
    p27 = page_text(reader, 27)
    p30 = page_text(reader, 30)
    official_checks = {
        "page13_bw_ram_pairs_map_to_lut0_lut1_lut2_lut3": all(
            token in p13
            for token in (
                "Table 6-5",
                "0 0 Black LUT 0",
                "0 1 White LUT 1",
                "1 0 Black LUT 2 = LUT0",
                "1 1 White LUT 3 = LUT1",
            )
        ),
        "page15_waveform_setting_is_159_bytes": all(
            token in p15
            for token in ("159 bytes", "WS byte 0~152", "Register", "0x32")
        ),
        "page26_0x24_is_bw_ram_and_cf_is_mode2_without_lut_load": all(
            token in p26
            for token in ("Write RAM (Black White)", "Display with DISPLAY Mode 2", "CF")
        ),
        "page27_0x26_is_red_ram": all(
            token in p27 for token in ("Write RAM (RED)", "RAM 0x26")
        ),
        "page30_0x37_is_mode_selection_per_ws_slot": all(
            token in p30
            for token in (
                "Display Mode for WS[7:0]",
                "Display Mode for WS[15:8]",
                "Display Mode for WS[23:16]",
                "Display Mode for WS[31:24]",
                "Display Mode for WS[35:32]",
            )
        ),
        "page30_f6_enables_mode2_ram_pingpong": all(
            token in p30
            for token in ("PingPong for Display Mode 2", "RAM Ping-Pong enable")
        ),
    }
    for name, passed in official_checks.items():
        if not passed:
            errors.append(f"official PDF check failed: {name}")

    controller = evidence.get("controller_state", {})
    controller_capture = controller.get("controller_capture", {})
    decoded = controller_capture.get("decoded", {}) if isinstance(controller_capture, dict) else {}
    display_option_hex = (
        decoded.get("display_option_0x37_b_through_f_hex", "")
        if isinstance(decoded, dict)
        else ""
    )
    mode2_slots, pingpong = decode_mode2_slots(str(display_option_hex))
    if display_option_hex != "4020100040":
        errors.append("measured 0x37 B..F bytes drifted")
    if mode2_slots != [6, 13, 20]:
        errors.append(f"unexpected Mode2 WS slots: {mode2_slots}")
    if not pingpong:
        errors.append("measured 0x37 F6 does not enable Mode2 RAM ping-pong")

    ram_fingerprint = evidence.get("ram_fingerprint", {}).get("fingerprint", {})
    if not isinstance(ram_fingerprint, dict) or ram_fingerprint.get("unique_mapping") != (
        "activation_swapped_banks_selector0_base_selector1_current"
    ):
        errors.append("RAM ping-pong fingerprint drifted")

    supplier_lut = parse_supplier_lut()
    if len(supplier_lut) != 159:
        errors.append(f"supplier LUT length is {len(supplier_lut)}, expected 159")
    supplier_nonzero_lut0_lut3 = [
        offset
        for offset in list(range(0, 12)) + list(range(36, 48))
        if len(supplier_lut) == 159 and supplier_lut[offset] != 0
    ]
    if supplier_nonzero_lut0_lut3 != [0, 1, 2, 3, 36, 37, 38, 39]:
        errors.append("supplier LUT0/LUT3 nonzero offsets drifted")

    r1 = evidence.get("r1_workbench", {})
    r2 = evidence.get("r2_workbench", {})
    r3 = evidence.get("r3_workbench", {})
    r4 = evidence.get("r4_workbench", {})
    r1_lut = candidate_lut(r1, "candidate_lut_hex")
    r2_lut = candidate_lut(r2, "r2_lut_hex")
    r3_lut = candidate_lut(r3, "r3_lut_hex")
    r4_lut = candidate_lut(r4, "r4_lut_hex")
    r1_offsets = offsets(r1, "byte_differences")
    r2_offsets = offsets(r2, "byte_differences_from_r1")
    r3_offsets = offsets(r3, "byte_differences_from_r2")
    r4_offsets = offsets(r4, "byte_differences_from_r2")
    if r1_offsets != supplier_nonzero_lut0_lut3:
        errors.append("R1 did not clear exactly the supplier nonzero LUT0/LUT3 bytes")
    for name, values in (("R1", r1_lut), ("R2", r2_lut), ("R3", r3_lut), ("R4", r4_lut)):
        if len(values) != 159:
            errors.append(f"{name} candidate LUT is not 159 bytes")
        elif any(values[offset] != 0 for offset in list(range(0, 12)) + list(range(36, 48))):
            errors.append(f"{name} does not preserve zeroed LUT0/LUT3")
    expected_timing_differences = {
        "R2": [60, 61, 63, 64, 67, 68, 74, 75, 77, 78, 81, 82],
        "R3": [74],
        "R4": [61, 64, 75, 78],
    }
    for name, actual in (("R2", r2_offsets), ("R3", r3_offsets), ("R4", r4_offsets)):
        if actual != expected_timing_differences[name]:
            errors.append(f"{name} timing-only differences drifted")
        if any(offset < 60 or offset > 143 for offset in actual):
            errors.append(f"{name} changed a non-timing byte")

    r4_disposition = evidence.get("r4_disposition", {})
    operator_review = r4_disposition.get("operator_review", {})
    if not isinstance(operator_review, dict) or operator_review.get("note") != "不太行, 屏幕很杂":
        errors.append("R4 sealed physical failure note drifted")
    if r4_disposition.get("production_allowed") is not False:
        errors.append("R4 production boundary drifted")

    checks = {
        **official_checks,
        "measured_0x37_b_through_f_exact": display_option_hex == "4020100040",
        "measured_mode2_ws_slots_exact": mode2_slots == [6, 13, 20],
        "measured_mode2_pingpong_enabled": pingpong,
        "ram_fingerprint_unique_swap_proven": isinstance(ram_fingerprint, dict)
        and ram_fingerprint.get("unique_mapping")
        == "activation_swapped_banks_selector0_base_selector1_current",
        "supplier_lut_length_159": len(supplier_lut) == 159,
        "r1_cleared_exact_nonzero_lut0_lut3_bytes": r1_offsets
        == supplier_nonzero_lut0_lut3
        == [0, 1, 2, 3, 36, 37, 38, 39],
        "r2_r3_r4_preserve_zeroed_lut0_lut3": all(
            len(values) == 159
            and not any(
                values[offset] != 0
                for offset in list(range(0, 12)) + list(range(36, 48))
            )
            for values in (r2_lut, r3_lut, r4_lut)
        ),
        "r2_r3_r4_changes_are_timing_only": all(
            actual == expected_timing_differences[name]
            and all(60 <= offset <= 143 for offset in actual)
            for name, actual in (("R2", r2_offsets), ("R3", r3_offsets), ("R4", r4_offsets))
        ),
        "r4_physical_no_go_preserved": r4_disposition.get("status")
        == EXPECTED_STATUSES["r4_disposition"]
        and isinstance(operator_review, dict)
        and operator_review.get("note") == "不太行, 屏幕很杂",
    }

    status = (
        "PASS_R5_MAPPING_CONFIRMS_LUT0_LUT3_TARGETING_NO_NEW_HARDWARE_CANDIDATE"
        if not errors
        else "FAIL_R5_MAPPING_AUDIT"
    )
    artifact = {
        "schema_id": "companion.wb55.ssd1681_custom_mode2_mapping_r5_disposition.v1",
        "status": status,
        "errors": errors,
        "hardware_contact": 0,
        "requirements": ["COMP-REQ-296"],
        "official_mapping": {
            "black_white_transition_table": [
                {"old_r_ram": 0, "new_bw_ram": 0, "class": "BB", "lut": 0},
                {"old_r_ram": 0, "new_bw_ram": 1, "class": "BW", "lut": 1},
                {"old_r_ram": 1, "new_bw_ram": 0, "class": "WB", "lut": 2},
                {"old_r_ram": 1, "new_bw_ram": 1, "class": "WW", "lut": 3},
            ],
            "supplier_159_byte_layout": {
                "lut0": [0, 11],
                "lut1": [12, 23],
                "lut2": [24, 35],
                "lut3": [36, 47],
                "lut4": [48, 59],
                "timing": [60, 143],
                "frame_rate": [144, 149],
                "xon": [150, 152],
                "register_tail": [153, 158],
            },
            "register_0x37_boundary": (
                "B..F select Display Mode 1 or Mode 2 per waveform-setting slot WS0..WS35; "
                "they do not select LUT0..LUT4 and are not byte addresses into the 159-byte waveform"
            ),
        },
        "measured_controller_decode": {
            "display_option_0x37_b_through_f_hex": display_option_hex,
            "mode2_ws_slots": mode2_slots,
            "f6_mode2_ram_pingpong_enabled": pingpong,
            "slot_decode": [
                {"byte": "B", "value_hex": "40", "mode2_ws_slots": [6]},
                {"byte": "C", "value_hex": "20", "mode2_ws_slots": [13]},
                {"byte": "D", "value_hex": "10", "mode2_ws_slots": [20]},
                {"byte": "E", "value_hex": "00", "mode2_ws_slots": []},
                {"byte": "F", "value_hex": "40", "mode2_ws_slots": [], "f6_pingpong": True},
            ],
        },
        "r1_through_r4_audit": {
            "supplier_nonzero_lut0_lut3_offsets": supplier_nonzero_lut0_lut3,
            "r1_cleared_offsets": r1_offsets,
            "r2_timing_offsets_from_r1": r2_offsets,
            "r3_timing_offsets_from_r2": r3_offsets,
            "r4_timing_offsets_from_r2": r4_offsets,
            "conclusion": (
                "R1 targeted the correct stationary transition tables: LUT0 for BB and LUT3 for WW. "
                "R2, R3 and R4 preserved those tables and changed timing bytes only."
            ),
        },
        "checks": checks,
        "disposition": {
            "mapping_error_found": False,
            "hardware_candidate_admitted": False,
            "hardware_allowed": False,
            "production_allowed": False,
            "r1_r4_rerun_allowed": False,
            "r4_no_go_preserved": True,
            "reason": (
                "The measured 0x37 bytes do not reveal a LUT-table swap or byte-address remap. "
                "R4 dirtiness therefore cannot be corrected by swapping the stationary LUT targets; "
                "a materially new, machine-gated mechanism is required before any hardware contact."
            ),
        },
        "source_hashes": {
            str(path): expected for path, expected in EXPECTED_HASHES.items()
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(status)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
