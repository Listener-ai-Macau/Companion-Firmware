#!/usr/bin/env python3
"""Fail-closed SSD1681 mechanism and supplier LUT research audit."""

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
OFFICIAL_DIR = (
    ROOT
    / ".cache/validation/ssd1681-mechanism-lut-research-20260721/official-sources"
)
SSD1681_PDF = OFFICIAL_DIR / "SSD1681V0.13_Spec-200529.pdf"
T03_PDF = OFFICIAL_DIR / "GDEY0154D67-T03-20241021.pdf"
PUBLIC_T03_SOURCE = (
    ROOT
    / ".cache/incoming/S-GDEY0154D67-FP-Touch-official-20260720"
    / "S-GDEY0154D67-FP-Touch20230303/HARDWARE/EPD/Display_EPD_W21.c"
)
OUT = (
    ROOT
    / "docs/validation/companion-ssd1681-mechanism-lut-research-disposition-20260721.json"
)

INPUTS = {
    "accepted_two_stage": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json",
    "accepted_runtime": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-runtime-20260720.json",
    "single_stage_r6": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-operator-r6-20260721.json",
    "post_sync_r1": ROOT
    / "docs/validation/companion-ssd1681-fast-point-probe-round1-disposition-20260721.json",
    "post_sync_r2": ROOT
    / "docs/validation/companion-ssd1681-fast-point-probe-inverse-seed-round2-disposition-20260721.json",
    "added_first": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-completion-audit-20260721.json",
    "removed_first": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-partial-removed-black-repair-current-union-operator-20260720.json",
    "disjoint_two_stage": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-operator-r1-20260721.json",
    "ram_fingerprint": ROOT
    / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json",
    "old_new_residue": ROOT
    / "docs/validation/companion-gdey0154d67-t03-vendor-t03-fast-state-residue-triage-20260720.json",
    "official_t03_audit": ROOT
    / "docs/validation/companion-gdey0154d67-t03-official-stm32-source-audit-20260720.json",
}

EXPECTED_HASHES = {
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    PUBLIC_T03_SOURCE: "CD08AFD1D56E8F7E1D0AE5C935A4D060E65C658ABC30CE29ACF65166141ACEE2",
    SSD1681_PDF: "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B",
    T03_PDF: "CCDD48B7EF9F72288E5CE5596D01C962BFF890653135AE6FF2360417F86F6FA9",
    OFFICIAL_DIR / "good-display-ssd1681-download-page.html": "ACD8C915DC91964EFD60A07BC20CD316C728F975FEDBCF1A6BA965932C7EDF3D",
    OFFICIAL_DIR / "good-display-gdey0154d67-t03-product.html": "ED1618FD1CEF2FDEF3B5714502CC5BF5A8CB0C3C70366C803AB1168D348D73B8",
    OFFICIAL_DIR / "good-display-gdey0154d67-product.html": "B4DC17ED369F83B488A5190D58AEF0A2B1E88FB73DAD62E7E5EBD37EE8AB365F",
    INPUTS["accepted_two_stage"]: "DA2FE11DB4CB1AFC5D433B2798BADBB576FC9C82BB39C472236E084C48F1EC57",
    INPUTS["accepted_runtime"]: "AE50830D1DB091AD2E526A132D55A7D512EA55E09D534F66CA7E71DB81BFF814",
    INPUTS["single_stage_r6"]: "13CF51F221110829949075864973DF769AAF1C8222B73B482124BF14FD55D9C3",
    INPUTS["added_first"]: "0E3643391446640D0D9A2A9B2E050D41A14D4BBB0D32785D814B4E57D98D2CF4",
    INPUTS["removed_first"]: "2FEBAB3365FE8481760DB0DC6C4180EFD01C24B10D985F751B6CAD9F4E1A2932",
    INPUTS["disjoint_two_stage"]: "67E43FBBD7546EB99E4CE8B06EE84141D0B0F4419E77C7ED1AF7D9C38D7D9C00",
    INPUTS["ram_fingerprint"]: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
    INPUTS["old_new_residue"]: "2EC85A59C950AEC033D4D2D78853E2B457DF6B870618F62E458672FA6C0C4291",
    INPUTS["official_t03_audit"]: "2472F102E8C8CEFF2914E4AB73AC45180A7D868E587F4C90E844B32DB65A5294",
}

EXPECTED_STATUSES = {
    "accepted_two_stage": "PASS_OPERATOR_ACCEPTED_PRODUCTION_OFF_NO_UNION_SETTLE_BASELINE",
    "accepted_runtime": "PASS_MACHINE_NO_UNION_SETTLE_TRACE",
    "single_stage_r6": "PASS_OPERATOR_WITH_RESIDUE_STEERING_PRODUCTION_OFF",
    "post_sync_r1": "UNSEEN_NO_VISIBLE_CHANGE_RESTORED_CONTINUE_GOAL",
    "post_sync_r2": "FAIL_NO_VISIBLE_REACTION_RESTORED_CONTINUE_GOAL",
    "added_first": "NO_GO_OWNER_MORE_RESIDUE_AND_CUTOFF_PERSISTS_NORMAL_RESTORED",
    "removed_first": "NO_GO_OPERATOR_VISIBLE_ENLARGED_GAP",
    "disjoint_two_stage": "NO_GO_OPERATOR_LEADING_EDGE_CUTOFF_DISJOINT_NO_UNION_SETTLE",
    "ram_fingerprint": "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED",
    "old_new_residue": "NO_GO_SOURCE_BACKED_NO_FLASH_RESIDUE_FREE_LOCAL_MOTION_NOT_FOUND",
    "official_t03_audit": "PASS_AUDIT_EXACT_T03_PUBLIC_SAMPLE_PANEL_IDENTITY_REMAINS_UNPROVEN",
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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def function_body(source: str, name: str, next_name: str) -> str:
    start = source.index(name)
    end = source.index(next_name, start)
    return source[start:end]


def pdf_text(path: Path, page_number: int) -> str:
    return PdfReader(str(path)).pages[page_number - 1].extract_text() or ""


def parse_lut(source: str) -> list[int]:
    match = re.search(
        r"const\s+unsigned\s+char\s+LUT_DATA\[159\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        return []
    return [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1))]


def decode_lut(values: list[int]) -> dict[str, object]:
    levels = ["VSS/DCVCOM", "VSH1/VSH1+DCVCOM", "VSL/VSL+DCVCOM", "VSH2/N_A_VCOM"]
    voltage_tables = []
    for lut_index in range(5):
        groups = []
        for group in range(12):
            raw = values[lut_index * 12 + group]
            codes = [(raw >> shift) & 0x03 for shift in (6, 4, 2, 0)]
            groups.append(
                {
                    "group": group,
                    "raw_hex": f"{raw:02X}",
                    "phase_codes_abcd": codes,
                    "levels_abcd": [levels[code] for code in codes],
                }
            )
        voltage_tables.append({"lut": lut_index, "groups": groups})

    timing_groups = []
    timing_names = ("TP_A", "TP_B", "SR_AB", "TP_C", "TP_D", "SR_CD", "RP")
    for group in range(12):
        raw = values[60 + group * 7 : 67 + group * 7]
        timing_groups.append(
            {
                "group": group,
                "raw_hex": [f"{value:02X}" for value in raw],
                "fields": dict(zip(timing_names, raw)),
                "effective_repeat_counts": {
                    "SR_AB": raw[2] + 1,
                    "SR_CD": raw[5] + 1,
                    "RP": raw[6] + 1,
                },
            }
        )

    frame_rates = []
    for offset, raw in enumerate(values[144:150]):
        frame_rates.extend(
            [
                {"group": offset * 2, "code": (raw >> 4) & 0x07},
                {"group": offset * 2 + 1, "code": raw & 0x07},
            ]
        )

    xon = []
    for offset, raw in enumerate(values[150:153]):
        for bit in range(8):
            group = offset * 4 + bit // 2
            subgroup = "AB" if bit % 2 == 0 else "CD"
            xon.append(
                {
                    "group": group,
                    "subgroup": subgroup,
                    "enabled": bool(raw & (1 << (7 - bit))),
                }
            )

    return {
        "length": len(values),
        "register_0x32_bytes_0_152": {
            "voltage_tables_bytes_0_59": voltage_tables,
            "timing_bytes_60_143": timing_groups,
            "frame_rate_bytes_144_149": frame_rates,
            "all_gate_on_bytes_150_152": xon,
        },
        "tail_registers": {
            "0x3F_EOPT_byte_153": f"{values[153]:02X}",
            "0x03_VGH_byte_154": {"raw_hex": f"{values[154]:02X}", "volts": 20.0},
            "0x04_source_bytes_155_157": {
                "raw_hex": [f"{value:02X}" for value in values[155:158]],
                "VSH1_volts": 15.0,
                "VSH2_volts": 5.0,
                "VSL_volts": -15.0,
            },
            "0x2C_VCOM_byte_158": {"raw_hex": f"{values[158]:02X}", "volts": -2.2},
        },
    }


def main() -> int:
    errors: list[str] = []
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            errors.append(f"missing locked input: {path}")
        elif sha(path) != expected:
            errors.append(f"hash mismatch: {path}")

    registry = REGISTRY.read_text(encoding="utf-8")
    if "| COMP-REQ-281 |" not in registry or "不是说一定是用这个" not in registry:
        errors.append("COMP-REQ-281 owner correction is missing")

    evidence: dict[str, dict[str, object]] = {}
    for name, path in INPUTS.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        evidence[name] = data
        if data.get("status") != EXPECTED_STATUSES[name]:
            errors.append(f"status drift: {name}")

    supplier_source = SUPPLIER.read_text(encoding="utf-8", errors="replace")
    values = parse_lut(supplier_source)
    if len(values) != 159:
        errors.append(f"supplier LUT length is {len(values)}, expected 159")
    elif bytes(values).hex().upper() != EXPECTED_LUT_HEX:
        errors.append("supplier LUT bytes drifted")

    supplier_init = function_body(supplier_source, "void EPD_HW_Init_LUT", "void EPD_Update_LUT")
    supplier_update = function_body(supplier_source, "void EPD_Update_LUT", "void EPD_WhiteScreen_ALL_LUT")
    supplier_full = function_body(supplier_source, "void EPD_WhiteScreen_ALL_LUT", "void EPD_WhiteScreen_White_LUT")
    supplier_partial = function_body(supplier_source, "void EPD_Part_Update", "//////////////////////////////All screen update")
    if not all(token in supplier_init for token in ("LUT_DATA[153]", "LUT_DATA[154]", "LUT_DATA[155]", "LUT_DATA[156]", "LUT_DATA[157]", "LUT_DATA[158]", "EPD_select_LUT(LUT_DATA)")):
        errors.append("supplier LUT tail/register sequence drifted")
    if not all(token in supplier_update for token in ("0x22", "0xC7", "0x20", "Epaper_READBUSY")):
        errors.append("supplier loaded-LUT C7 activation drifted")
    if not all(token in supplier_full for token in ("0x24", "i<5000", "EPD_Update_LUT")):
        errors.append("supplier loaded-LUT path is not exact 5000-byte full frame")
    if not all(token in supplier_partial for token in ("0x22", "0xFF", "0x20", "Epaper_READBUSY")):
        errors.append("supplier OTP partial activation drifted")

    public_source = PUBLIC_T03_SOURCE.read_text(encoding="utf-8", errors="replace")
    if "Epaper_Write_Data(0xC7)" not in public_source or "Epaper_Write_Data(0xFF)" not in public_source:
        errors.append("official T03 sample controls drifted")
    if "Epaper_Write_Command(0x32)" in public_source:
        errors.append("official T03 public sample unexpectedly writes external LUT")

    ssd_p15 = pdf_text(SSD1681_PDF, 15)
    ssd_p26 = pdf_text(SSD1681_PDF, 26)
    ssd_p30 = pdf_text(SSD1681_PDF, 30)
    ssd_p31 = pdf_text(SSD1681_PDF, 31)
    t03_p6 = pdf_text(T03_PDF, 6)
    t03_p23 = pdf_text(T03_PDF, 23)
    required_pdf_facts = [
        (ssd_p15, "there are 159 bytes"),
        (ssd_p15, "WS byte 0~152"),
        (ssd_p15, "WS byte 155~157"),
        (ssd_p26, "DISPLAY with DISPLAY Mode 1"),
        (ssd_p26, "DISPLAY with DISPLAY Mode 2"),
        (ssd_p30, "RAM Ping-Pong function is not support"),
        (ssd_p31, "Border Waveform Control"),
        (t03_p6, "GDEY0154D67-T03"),
        (t03_p6, "200×200"),
        (t03_p23, "controller &"),
        (t03_p23, "recommended to add a full-screen refresh after 5 consecutive operations"),
    ]
    for text, fact in required_pdf_facts:
        if fact not in text:
            errors.append(f"official PDF fact missing: {fact}")

    accepted = evidence["accepted_two_stage"]
    accepted_runtime = evidence["accepted_runtime"]
    r6 = evidence["single_stage_r6"]
    r1 = evidence["post_sync_r1"]
    r2 = evidence["post_sync_r2"]
    fingerprint = evidence["ram_fingerprint"]
    old_new = evidence["old_new_residue"]
    if accepted_runtime.get("observed", {}).get("partial_activation_count") != 96:
        errors.append("accepted two-stage activation count drifted")
    if r6.get("machine_trace", {}).get("busy_completions") != 48:
        errors.append("r6 single-stage trace drifted")
    if r1.get("machine", {}).get("refresh_0x20") != 120 or r2.get("machine", {}).get("frames") != 120:
        errors.append("post-sync no-response round counts drifted")
    if fingerprint.get("fingerprint", {}).get("unique_mapping") != "activation_swapped_banks_selector0_base_selector1_current":
        errors.append("Mode2 RAM swap fingerprint drifted")
    if "old_new_ram_ab" not in old_new.get("comparison", {}):
        errors.append("old/new RAM physical negative control missing")

    lut_decode = decode_lut(values) if len(values) == 159 else {}
    status = (
        "RESEARCH_DISPOSITION_MISSING_PANEL_BOUND_LOCAL_MODE2_RULE_NO_R3"
        if not errors
        else "NO_GO_MECHANISM_RESEARCH_EVIDENCE_DRIFT"
    )
    result = {
        "schema_id": "companion.wb55.ssd1681_mechanism_lut_research_disposition.v1",
        "status": status,
        "errors": errors,
        "hardware_contact": 0,
        "requirement": "COMP-REQ-281",
        "owner_boundary": {
            "accepted_reference": "COMP-REQ-236/237 is a successful physical reference and quality floor, not mandatory architecture",
            "protected_quality_floor": [
                "visible movement",
                "no recurring old-position hatch",
                "no whole-screen black flash",
            ],
            "remaining_reference_defect": accepted.get("operator_review", {}).get("remaining_issue"),
        },
        "official_sources": [
            {
                "title": "Good Display GDEY0154D67-T03 product page",
                "url": "https://www.good-display.com/product/258.html",
                "archive": str((OFFICIAL_DIR / "good-display-gdey0154d67-t03-product.html").relative_to(ROOT)).replace("\\", "/"),
                "sha256": EXPECTED_HASHES[OFFICIAL_DIR / "good-display-gdey0154d67-t03-product.html"],
            },
            {
                "title": "Good Display GDEY0154D67-T03 specification 2024-10-21",
                "url": "https://v4.cecdn.yun300.cn/100001_1909185148/GDEY0154D67-T03.pdf",
                "archive": str(T03_PDF.relative_to(ROOT)).replace("\\", "/"),
                "sha256": EXPECTED_HASHES[T03_PDF],
            },
            {
                "title": "Good Display hosted SSD1681 Rev 0.13 specification",
                "url": "https://www.good-display.com/companyfile/85.html",
                "resolved_url": "https://v4.cecdn.yun300.cn/100001_1909185148/SSD1681V0.13_Spec.pdf",
                "archive": str(SSD1681_PDF.relative_to(ROOT)).replace("\\", "/"),
                "sha256": EXPECTED_HASHES[SSD1681_PDF],
            },
            {
                "title": "Good Display official T03 STM32 sample",
                "url": "https://www.good-display.com/companyfile/1029.html",
                "resolved_url": "https://v4.cecdn.yun300.cn/100001_1909185148/S-GDEY0154D67-FP-Touch.rar",
                "source_path": str(PUBLIC_T03_SOURCE.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": EXPECTED_HASHES[PUBLIC_T03_SOURCE],
            },
        ],
        "supplier_159_byte_lut": {
            "source_path": str(SUPPLIER),
            "source_sha256": EXPECTED_HASHES[SUPPLIER],
            "decode": lut_decode,
            "black_white_mapping": {
                "R0_BW0": "black through LUT0",
                "R0_BW1": "white through LUT1",
                "R1_BW0": "black through LUT2 equal to LUT0 in controller mapping",
                "R1_BW1": "white through LUT3 equal to LUT1 in controller mapping",
                "LUT4": "present in 0x32 mapping; no black/white RAM-color assignment is stated in SSD1681 Table 6-5; supplier bytes are all zero",
            },
            "supplier_usage": {
                "load": "0x3F/0x03/0x04/0x2C tail then 153 bytes under 0x32",
                "image": "one 0x24 plane, exactly 5000 bytes",
                "activation": "0x22=0xC7, 0x20, BUSY",
                "scope": "supplier demonstrates this loaded LUT only with a full 200x200 frame",
            },
        },
        "control_decode": {
            "0xC7": "enable clock + analog, display with Mode 1, disable analog and oscillator; it does not load a LUT",
            "0xF7": "enable clock + analog, load temperature, display with Mode 1, disable analog and oscillator",
            "0xFF": "enable clock + analog, load temperature, display with Mode 2, disable analog and oscillator",
            "mode_boundary": "SSD1681 register 0x37 states RAM Ping-Pong is supported for Mode 2 and not for Mode 1",
            "correction": "0xC7 is loaded-LUT Mode1 display in the supplied program; 0xFF is temperature-selected OTP Mode2 display, not a synonym for external LUT refresh",
        },
        "phase_reconstruction": [
            {
                "case": "accepted_two_stage_erase_then_draw",
                "ram_command_phase": [
                    "pass 1 writes current bytes over previous-black window through 0x24, then FF/20/BUSY",
                    "pass 2 writes current bytes over current/difference window through 0x24, then FF/20/BUSY",
                ],
                "representative_pixels": [
                    {"phase": "visible_previous", "old_only": "black", "new_only": "white"},
                    {"phase": "after_pass_1", "old_only": "white", "new_only": "white"},
                    {"phase": "after_pass_2", "old_only": "white", "new_only": "black"},
                ],
                "optical_result": "accepted: no recurring hatch and no whole-screen black flash; new-only leading edge is visibly absent between activations",
            },
            {
                "case": "single_stage_r6_current_only",
                "ram_command_phase": [
                    "stage disjoint current regions through 0x24",
                    "one FF/20/BUSY activation; no post-activation sync",
                ],
                "optical_result": "visible motion, but direct-motion residue remained",
            },
            {
                "case": "post_sync_rounds_r1_r2",
                "ram_command_phase": [
                    "extended reset/init/window sequence, current diff through 0x24, FF/20/BUSY",
                    "after activation reissue setup and write current through 0x24 without another 0x20",
                ],
                "controller_result": "120 activations completed in each round; R2 frame 1 encoded both W-to-B and B-to-W transitions",
                "optical_result": "no visible reaction; controller command completion is not optical-transition proof",
            },
            {
                "case": "added_or_draw_first_then_cleanup",
                "ram_command_phase": [
                    "draw eligible added-black bytes first through current 0x24 and FF/20/BUSY",
                    "clean previous-black area second through current 0x24 and FF/20/BUSY",
                ],
                "optical_result": "owner observed more residue while the disappearing/cutoff segment persisted",
            },
            {
                "case": "explicit_old_0x26_new_0x24_one_stage",
                "ram_command_phase": [
                    "write prior changed region to 0x26 and current changed region to 0x24",
                    "one supplier FF/20/BUSY activation",
                ],
                "controller_result": "Phase A separately proved Mode2 activation swaps the two RAM-bank selectors",
                "optical_result": "physical negative control retained black following residue",
            },
        ],
        "candidate_assessment": [
            {
                "candidate": "exact_159_byte_LUT_plus_local_window_plus_C7",
                "admitted": False,
                "reason": "The LUT bytes and C7 command are individually traceable, but their local-window composition is absent from both supplier programs. Mode1 cannot use RAM Ping-Pong, and Good Display demonstrates this LUT only as a 5000-byte full-frame fast refresh that visibly flashes once.",
            },
            {
                "candidate": "OTP_Mode2_current_only_or_old_new_one_activation",
                "admitted": False,
                "reason": "This is the documented no-flash local family, but both the current-only and explicit old/new RAM forms already have physical residue evidence. Repackaging either is not a materially new R3.",
            },
            {
                "candidate": "two_stage_order_or_region_rearrangement",
                "admitted": False,
                "reason": "It can preserve final cleanliness, but all evidenced erase-first forms expose an incomplete new edge and draw-first forms regress residue or content integrity. The accepted implementation remains a reference, not mandatory architecture.",
            },
        ],
        "disposition": {
            "machine_ready_candidate": False,
            "hardware_allowed": False,
            "production_allowed": False,
            "accepted_reference_preserved": True,
            "missing_fact": "Good Display must provide a manufacturer mapping from observed FPC 0154BN-D67-D2 to the exact panel/OTP, plus a panel-bound local Mode2 waveform/temperature/update rule materially different from the already-tested FF path; alternatively it must explicitly document local no-flash use of this exact 159-byte LUT with RAM-plane semantics.",
            "why_research_can_continue_but_R3_cannot": "The controller mechanism is now understood, but no source-backed command/LUT topology remains untested that can claim clean simultaneous W-to-B and B-to-W transitions without a visible incomplete intermediate state.",
            "forbidden": [
                "custom or guessed LUT bytes",
                "combining the full-frame Mode1 LUT with local windows by inference",
                "repeating an already failed OTP Mode2 topology under a new name",
                "hardware contact before a materially new source-bound machine gate",
            ],
            "goal_terminal": False,
        },
        "source_hashes": {str(path): expected for path, expected in EXPECTED_HASHES.items()},
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(status)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
