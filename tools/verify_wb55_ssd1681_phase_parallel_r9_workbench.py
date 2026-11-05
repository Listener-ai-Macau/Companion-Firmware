#!/usr/bin/env python3
"""Audit a source-derived, research-only SSD1681 phase-parallel R9 waveform."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/companion_product_requirements.md"
SUPPLIER = Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
PDF = (
    ROOT
    / ".cache/validation/ssd1681-mechanism-lut-research-20260721/official-sources"
    / "SSD1681V0.13_Spec-200529.pdf"
)
OWNER_ACCEPTANCE = (
    ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
)
R1 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-workbench-20260721.json"
R2 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r2-20260721.json"
R3 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r3-20260721.json"
R4 = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-timing-workbench-r4-20260721.json"
R4_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-custom-mode2-transition-safety-r4-disposition-20260721.json"
R6_DIAGNOSIS = ROOT / "docs/validation/companion-ssd1681-custom-mode2-observable-r6-failure-diagnosis-20260721.json"
R8_RUNTIME = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-runtime-20260721.json"
R8_DISPOSITION = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-disposition-20260721.json"
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-workbench-20260721.json"

EXPECTED_HASHES = {
    SUPPLIER: "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896",
    PDF: "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B",
    OWNER_ACCEPTANCE: "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
    R1: "8653B6ABD0E299E6C99B50C5A086EE840E38CED37F358F7AA326B37F7933CF05",
    R2: "266FC130BAEB68219A759A9A15E292D6E2BED97919FC5A9F0086BCC6733A5148",
    R3: "CCFB9EF0AE1CBF1038A7ED4E188D3A6DF8303CFF5E18C4391418A20310C16124",
    R4: "E7467B808CE7BD1BE317BC282B7990CF343922DE8C15B092588B9968DEAB444D",
    R4_DISPOSITION: "C4E52FF8B1E0A4A2E7D084E65166BACC5748E96B31A3822DC32C275FD4C259D0",
    R6_DIAGNOSIS: "CD58E1AFF90339A2A3528C9C86B22F641DD010A4D275AF75410E16F812552289",
    R8_RUNTIME: "BAD97BBABFD2E1B515A2E1D1A45EE3C4E68EF3FFC167D03468E1859659C07FF5",
    R8_DISPOSITION: "FE3EDA1AD48F7B626C7D099F526D063EA6EA125D9F34B4E9A963A1AE94527374",
}
EXPECTED_SUPPLIER_LUT_SHA = "F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15"
TRANSITIONS = (("BB", 0), ("BW", 1), ("WB", 2), ("WW", 3))
PHASE_NAMES = "ABCD"
VOLTAGE = {
    0: {"name": "VSS", "polarity": "zero", "volts": 0.0},
    1: {"name": "VSH1", "polarity": "positive", "volts": 15.0},
    2: {"name": "VSL", "polarity": "negative", "volts": -15.0},
    3: {"name": "VSH2", "polarity": "positive_low", "volts": 5.0},
}
BUSY_LIMIT_MS = 600


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def parse_supplier_lut(source: str) -> bytes:
    match = re.search(
        r"const\s+unsigned\s+char\s+LUT_DATA\[159\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        raise ValueError("supplier LUT_DATA[159] not found")
    values = bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1)))
    if len(values) != 159:
        raise ValueError(f"supplier LUT_DATA length is {len(values)}, expected 159")
    return values


def unpack_voltage_tables(values: bytes) -> list[list[int]]:
    if len(values) != 159:
        raise ValueError("waveform must contain 159 bytes")
    tables: list[list[int]] = []
    for lut in range(5):
        phases: list[int] = []
        for packed in values[lut * 12 : (lut + 1) * 12]:
            phases.extend(((packed >> 6) & 3, (packed >> 4) & 3, (packed >> 2) & 3, packed & 3))
        tables.append(phases)
    return tables


def pack_voltage_tables(tables: list[list[int]]) -> bytes:
    packed = bytearray()
    for table in tables:
        if len(table) != 48:
            raise ValueError("each voltage table must contain 48 complete VS fields")
        for index in range(0, 48, 4):
            a, b, c, d = table[index : index + 4]
            packed.append((a << 6) | (b << 4) | (c << 2) | d)
    return bytes(packed)


def unpack_timing(values: bytes) -> list[dict[str, Any]]:
    groups = []
    for group in range(12):
        base = 60 + group * 7
        groups.append(
            {
                "group": group,
                "tp": [values[base], values[base + 1], values[base + 3], values[base + 4]],
                "sr_ab": values[base + 2],
                "sr_cd": values[base + 5],
                "rp": values[base + 6],
            }
        )
    return groups


def pack_timing(groups: list[dict[str, Any]]) -> bytes:
    packed = bytearray()
    for item in groups:
        a, b, c, d = item["tp"]
        packed.extend((a, b, item["sr_ab"], c, d, item["sr_cd"], item["rp"]))
    return bytes(packed)


def build_r9(supplier: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    source_tables = unpack_voltage_tables(supplier)
    tables = [[0] * 48 for _ in range(5)]
    groups = [
        {"group": group, "tp": [0, 0, 0, 0], "sr_ab": 0, "sr_cd": 0, "rp": 0}
        for group in range(12)
    ]
    # VS and TP are independent complete fields in SSD1681. Move each exactly once.
    moves = (
        # destination, duration source, BW source, WB source
        ((0, "A"), (0, "A"), (0, "A"), (0, "A")),
        ((1, "A"), (1, "A"), (1, "B"), (1, "A")),
        ((2, "A"), (2, "A"), (2, "A"), (2, "A")),
        ((3, "A"), (3, "A"), (3, "B"), (3, "A")),
    )
    source_timing = unpack_timing(supplier)
    lineage: list[dict[str, Any]] = []
    for destination, duration_source, bw_source, wb_source in moves:
        dst_group, dst_name = destination
        dst_phase = PHASE_NAMES.index(dst_name)
        duration_group, duration_name = duration_source
        duration_phase = PHASE_NAMES.index(duration_name)
        duration = source_timing[duration_group]["tp"][duration_phase]
        groups[dst_group]["tp"][dst_phase] = duration
        item: dict[str, Any] = {
            "destination": f"{dst_group}{dst_name}",
            "duration": {
                "value": duration,
                "source_field": f"TP[{duration_group}{duration_name}]",
            },
        }
        for label, lut, source in (("BW", 1, bw_source), ("WB", 2, wb_source)):
            src_group, src_name = source
            src_phase = PHASE_NAMES.index(src_name)
            value = source_tables[lut][src_group * 4 + src_phase]
            tables[lut][dst_group * 4 + dst_phase] = value
            item[label] = {
                "code": value,
                "voltage": VOLTAGE[value]["name"],
                "source_field": f"VS[{src_group}{src_name}-LUT{lut}]",
            }
        lineage.append(item)
    candidate = bytearray(159)
    candidate[:60] = pack_voltage_tables(tables)
    candidate[60:144] = pack_timing(groups)
    candidate[144:159] = supplier[144:159]
    return bytes(candidate), lineage


def phase_rows(values: bytes) -> list[dict[str, Any]]:
    tables = unpack_voltage_tables(values)
    timing = unpack_timing(values)
    rows = []
    for group in range(12):
        for phase in range(4):
            duration = timing[group]["tp"][phase]
            row: dict[str, Any] = {
                "slot": f"{group}{PHASE_NAMES[phase]}",
                "duration_frames": duration,
            }
            for name, lut in TRANSITIONS:
                code = tables[lut][group * 4 + phase]
                row[name] = {
                    "code": code,
                    "voltage": VOLTAGE[code]["name"],
                    "polarity": VOLTAGE[code]["polarity"],
                }
            rows.append(row)
    return rows


def transition_summary(values: bytes, name: str) -> dict[str, Any]:
    tables = unpack_voltage_tables(values)
    timing = unpack_timing(values)
    shared_total = sum(sum(group["tp"]) for group in timing)
    transitions: dict[str, Any] = {}
    for transition, lut in TRANSITIONS:
        counts = Counter({"VSS": 0, "VSH1": 0, "VSL": 0, "VSH2": 0})
        sequence = []
        for group in range(12):
            for phase in range(4):
                duration = timing[group]["tp"][phase]
                if duration == 0:
                    continue
                code = tables[lut][group * 4 + phase]
                voltage = VOLTAGE[code]
                counts[voltage["name"]] += duration
                sequence.append(
                    {
                        "slot": f"{group}{PHASE_NAMES[phase]}",
                        "duration_frames": duration,
                        "code": code,
                        "voltage": voltage["name"],
                        "polarity": voltage["polarity"],
                    }
                )
        volt_frame = sum(counts[item["name"]] * item["volts"] for item in VOLTAGE.values())
        positive = counts["VSH1"] + counts["VSH2"]
        negative = counts["VSL"]
        transitions[transition] = {
            "lut": lut,
            "shared_timing_frames": shared_total,
            "effective_drive_frames": positive + negative,
            "zero_drive_frames": counts["VSS"],
            "positive_drive_frames": positive,
            "negative_drive_frames": negative,
            "normalized_signed_frames": positive - negative,
            "source_volt_frame_impulse": volt_frame,
            "voltage_frame_counts": dict(counts),
            "phase_order": sequence,
        }
    first_half = sum(sum(group["tp"]) for group in timing[:2])
    second_half = sum(sum(group["tp"]) for group in timing[2:4])
    return {
        "profile": name,
        "lut_sha256": sha_bytes(values),
        "shared_timing_frames": shared_total,
        "first_polarity_half_timing_frames": first_half,
        "second_polarity_half_timing_frames": second_half,
        "transitions": transitions,
        "phase_rows": phase_rows(values),
    }


def topology_signature(values: bytes) -> tuple[Any, ...]:
    tables = unpack_voltage_tables(values)
    timing = unpack_timing(values)
    records = []
    for group in range(12):
        for phase in range(4):
            duration = timing[group]["tp"][phase]
            if duration:
                records.append((duration, tables[1][group * 4 + phase], tables[2][group * 4 + phase]))
    return (
        tuple(tables[0]),
        tuple(tables[3]),
        tuple(records),
        values[144:159],
    )


def extract_luts_from_text(text: str) -> list[bytes]:
    found: list[bytes] = []
    for match in re.finditer(r"(?<![0-9A-Fa-f])([0-9A-Fa-f]{318})(?![0-9A-Fa-f])", text):
        found.append(bytes.fromhex(match.group(1)))
    for match in re.finditer(r"\{([^{}]{200,4000})\}", text, re.DOTALL):
        tokens = re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1))
        if len(tokens) == 159:
            found.append(bytes(int(item, 16) for item in tokens))
    return found


def history_scan(candidate: bytes) -> dict[str, Any]:
    candidate_hash = sha_bytes(candidate)
    signature = topology_signature(candidate)
    exact_hits: list[dict[str, Any]] = []
    equivalent_hits: list[dict[str, Any]] = []
    scanned_files = 0
    scanned_sequences = 0
    roots = (ROOT / "app", ROOT / "tools", ROOT / "docs/validation")
    extensions = {".c", ".h", ".py", ".ps1", ".json", ".md", ".txt"}
    admitted_implementation_outputs = {
        ROOT / "tools/invoke_wb55_ssd1681_phase_parallel_r9_final_visual_prompt.ps1",
        ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9.ps1",
        ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_diagnostic.py",
        ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_launcher.py",
        ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_log.py",
        ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_machine_ready.py",
        ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-persistent-launcher-static-20260721.json",
        ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-machine-ready-20260721.json",
        ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-static-20260721.json",
    }
    admitted_driver = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if (
                not path.is_file()
                or path.suffix.lower() not in extensions
                or path == OUT
                or path in admitted_implementation_outputs
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scanned_files += 1
            if path == admitted_driver:
                text = re.sub(
                    r"#if COMPANION_EPAPER_SSD1681_PHASE_PARALLEL_R9_DIAGNOSTIC\s+"
                    r"#define SSD1681_PHASE_PARALLEL_R9_LUT_SHA256.*?"
                    r"static const uint8_t ssd1681_phase_parallel_r9_lut\[159\].*?"
                    r"\n\};\s*#endif",
                    "",
                    text,
                    flags=re.DOTALL,
                )
            for index, values in enumerate(extract_luts_from_text(text)):
                scanned_sequences += 1
                record = {"path": str(path.relative_to(ROOT)), "sequence_index": index, "sha256": sha_bytes(values)}
                if record["sha256"] == candidate_hash:
                    exact_hits.append(record)
                if topology_signature(values) == signature:
                    equivalent_hits.append(record)
    git_queries = []
    for needle in (candidate.hex().upper(), "0x40, 0x40, 0x80, 0x80", "40408080"):
        proc = subprocess.run(
            ["git", "log", "--all", "--format=%H", "-S", needle, "--", "app", "tools", "docs/validation"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        commits = sorted(set(line for line in proc.stdout.splitlines() if line))
        git_queries.append({"needle": needle, "returncode": proc.returncode, "matching_commits": commits})
    return {
        "worktree_scanned_files": scanned_files,
        "worktree_159_byte_sequences": scanned_sequences,
        "exact_candidate_hits": exact_hits,
        "equivalent_topology_hits": equivalent_hits,
        "git_pickaxe_queries": git_queries,
        "duplicate_found": bool(exact_hits or equivalent_hits or any(item["matching_commits"] for item in git_queries)),
    }


def validate_candidate(candidate: bytes, supplier: bytes, lineage: list[dict[str, Any]], known_hashes: set[str]) -> list[str]:
    errors: list[str] = []
    if len(candidate) != 159:
        errors.append("candidate length is not 159")
        return errors
    tables = unpack_voltage_tables(candidate)
    timing = unpack_timing(candidate)
    source_tables = unpack_voltage_tables(supplier)
    source_timing = unpack_timing(supplier)
    if any(tables[lut] != [0] * 48 for lut in (0, 3)):
        errors.append("stationary BB/WW drive is not zero")
    if any(item["sr_ab"] or item["sr_cd"] or item["rp"] for item in timing):
        errors.append("SR/RP changed from source zero")
    if candidate[144:159] != supplier[144:159]:
        errors.append("FR/XON/tail bytes 144..158 are not supplier exact")
    if candidate[153:159] != bytes.fromhex("221741A83258"):
        errors.append("protected bytes 153..158 drifted")
    if not set(candidate).issubset(set(supplier)):
        errors.append("candidate contains a packed byte value absent from supplier")
    used_voltage: set[str] = set()
    used_duration: set[str] = set()
    destination_slots: set[int] = set()
    for item in lineage:
        destination_match = re.fullmatch(r"(\d+)([ABCD])", item["destination"])
        if not destination_match:
            errors.append(f"invalid destination {item['destination']}")
            continue
        destination_group = int(destination_match.group(1))
        destination_phase = PHASE_NAMES.index(destination_match.group(2))
        destination_index = destination_group * 4 + destination_phase
        if destination_index in destination_slots:
            errors.append(f"destination reused {item['destination']}")
        destination_slots.add(destination_index)
        duration_field = item["duration"]["source_field"]
        match = re.fullmatch(r"TP\[(\d+)([ABCD])\]", duration_field)
        if not match:
            errors.append(f"invalid duration lineage {duration_field}")
        else:
            group, phase_name = int(match.group(1)), match.group(2)
            actual = source_timing[group]["tp"][PHASE_NAMES.index(phase_name)]
            if actual != item["duration"]["value"] or actual == 0:
                errors.append(f"duration lineage mismatch {duration_field}")
            if timing[destination_group]["tp"][destination_phase] != item["duration"]["value"]:
                errors.append(f"destination duration differs from lineage {item['destination']}")
        if duration_field in used_duration:
            errors.append(f"duration source field reused {duration_field}")
        used_duration.add(duration_field)
        for label, lut in (("BW", 1), ("WB", 2)):
            field = item[label]["source_field"]
            match = re.fullmatch(r"VS\[(\d+)([ABCD])-LUT(\d)\]", field)
            if not match or int(match.group(3)) != lut:
                errors.append(f"invalid {label} voltage lineage {field}")
                continue
            group, phase_name = int(match.group(1)), match.group(2)
            actual = source_tables[lut][group * 4 + PHASE_NAMES.index(phase_name)]
            if actual != item[label]["code"] or actual not in (1, 2):
                errors.append(f"{label} voltage lineage mismatch {field}")
            if tables[lut][destination_index] != item[label]["code"]:
                errors.append(f"destination {label} code differs from lineage {item['destination']}")
            if field in used_voltage:
                errors.append(f"voltage source field reused {field}")
            used_voltage.add(field)
    active_slots = {
        group * 4 + phase
        for group, item in enumerate(timing)
        for phase, duration in enumerate(item["tp"])
        if duration
    }
    if active_slots != destination_slots:
        errors.append("active timing slots differ from the complete lineage destinations")
    for lut in (1, 2):
        nonzero_slots = {index for index, code in enumerate(tables[lut]) if code}
        if nonzero_slots != destination_slots:
            errors.append(f"LUT{lut} nonzero VS slots differ from the complete lineage destinations")
    summary = transition_summary(candidate, "R9")
    for transition in ("BW", "WB"):
        item = summary["transitions"][transition]
        if item["effective_drive_frames"] != 16:
            errors.append(f"{transition} effective drive is not 16 frames")
        if item["positive_drive_frames"] != 8 or item["negative_drive_frames"] != 8:
            errors.append(f"{transition} polarity split is not 8/8")
        if item["source_volt_frame_impulse"] != 0:
            errors.append(f"{transition} net source impulse is not zero")
    for row in summary["phase_rows"]:
        if row["duration_frames"] and {row["BW"]["code"], row["WB"]["code"]} != {1, 2}:
            errors.append(f"retained phase {row['slot']} is not opposite-polarity BW/WB")
    if summary["shared_timing_frames"] != 16:
        errors.append("shared R9 timing is not 16 frames")
    if sha_bytes(candidate) in known_hashes:
        errors.append("candidate exact hash duplicates a registered supplier/R1-R4 waveform")
    return errors


def run_negative_fixtures(candidate: bytes, supplier: bytes, lineage: list[dict[str, Any]], known_hashes: set[str]) -> list[dict[str, Any]]:
    fixtures: list[tuple[str, bytes, list[dict[str, Any]], set[str]]] = []
    mutated = bytearray(candidate)
    mutated[153] ^= 1
    fixtures.append(("tail_drift", bytes(mutated), lineage, known_hashes))
    mutated = bytearray(candidate)
    mutated[67] = 4
    fixtures.append(("invented_duration_four", bytes(mutated), lineage, known_hashes))
    mutated = bytearray(candidate)
    mutated[0] = 0x40
    fixtures.append(("stationary_drive_restored", bytes(mutated), lineage, known_hashes))
    mutated = bytearray(candidate)
    mutated[24] = 0x40
    fixtures.append(("same_polarity_parallel_phase", bytes(mutated), lineage, known_hashes))
    mutated = bytearray(candidate)
    mutated[12] = 0xC0
    fixtures.append(("invented_vsh2_transition_field", bytes(mutated), lineage, known_hashes))
    duplicate_lineage = json.loads(json.dumps(lineage))
    duplicate_lineage[1]["BW"]["source_field"] = duplicate_lineage[0]["BW"]["source_field"]
    fixtures.append(("reused_supplier_vs_field", candidate, duplicate_lineage, known_hashes))
    fixtures.append(("registered_exact_duplicate", candidate, lineage, known_hashes | {sha_bytes(candidate)}))
    results = []
    for name, values, fixture_lineage, hashes in fixtures:
        fixture_errors = validate_candidate(values, supplier, fixture_lineage, hashes)
        results.append({"name": name, "rejected": bool(fixture_errors), "errors": fixture_errors})
    return results


def load_profile(path: Path, keys: tuple[str, ...]) -> bytes:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    for key in keys:
        value = value[key]
    return bytes.fromhex(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="also require all fail-closed negative fixtures")
    args = parser.parse_args()
    errors: list[str] = []
    hashes: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            errors.append(f"missing locked input: {path}")
            continue
        actual = sha(path)
        hashes[str(path)] = actual
        if actual != expected:
            errors.append(f"locked input hash drifted: {path}")
    registry = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
    if "| COMP-REQ-308 |" not in registry or "ADMIT_ONE_VARIABLE_R9" not in registry:
        errors.append("COMP-REQ-308 research-only contract is missing")

    supplier = parse_supplier_lut(SUPPLIER.read_text(encoding="latin-1")) if SUPPLIER.is_file() else b""
    if supplier and sha_bytes(supplier) != EXPECTED_SUPPLIER_LUT_SHA:
        errors.append("supplier LUT_DATA hash differs")
    profiles = {
        "supplier": supplier,
        "R1": load_profile(R1, ("candidate", "candidate_lut_hex")),
        "R2": load_profile(R2, ("candidate", "r2_lut_hex")),
        "R3": load_profile(R3, ("candidate", "r3_lut_hex")),
        "R4": load_profile(R4, ("candidate", "r4_lut_hex")),
    }
    r9, lineage = build_r9(supplier)
    known_hashes = {sha_bytes(values) for values in profiles.values()}
    errors.extend(validate_candidate(r9, supplier, lineage, known_hashes))

    reader = PdfReader(str(PDF)) if PDF.is_file() else None
    pdf_pages = {number: (reader.pages[number - 1].extract_text() or "") for number in (13, 14, 15, 21, 29)} if reader else {}
    encoding_checks = {
        "page13_has_lut0_to_lut3_mapping": all(token in pdf_pages.get(13, "") for token in ("Table 6-5", "LUT 0", "LUT 1", "LUT 2", "LUT 3")),
        "page14_defines_48_phases_and_independent_vs_lutm": all(token in pdf_pages.get(14, "") for token in ("Totally, there are 48", "VS[nX-LUTm]", "m represents the LUT number from 0-4")),
        "page14_defines_voltage_codes": all(token in pdf_pages.get(14, "") for token in ("00 VSS", "01 VSH1", "10 VSL", "11 VSH2")),
        "page15_defines_159_bytes_and_register_split": all(token in pdf_pages.get(15, "") for token in ("159 bytes", "0~152", "byte 153", "154", "155~157", "158")),
        "page21_tail_decodes_plus15_minus15": all(token in pdf_pages.get(21, "") for token in ("41h", "VSH1 at 15V", "32h", "VSL at -15V")),
        "page29_0x32_accepts_153_bytes": "Write LUT register from MCU interface" in pdf_pages.get(29, "") and "[153 bytes]" in pdf_pages.get(29, ""),
    }
    errors.extend(name for name, passed in encoding_checks.items() if not passed)

    r4_disposition = json.loads(R4_DISPOSITION.read_text(encoding="utf-8"))
    r6_diagnosis = json.loads(R6_DIAGNOSIS.read_text(encoding="utf-8"))
    r8_disposition = json.loads(R8_DISPOSITION.read_text(encoding="utf-8"))
    busy_values = r4_disposition.get("machine_result", {}).get("busy_elapsed_ms", [])
    predicted_busy = max(busy_values) if busy_values else None
    if predicted_busy is None or predicted_busy > BUSY_LIMIT_MS:
        errors.append("R4 timing-equivalent measured BUSY does not prove <=600 ms")
    if r6_diagnosis.get("observed_failure", {}).get("canonical_selected") != "失败":
        errors.append("R6 TP16 retirement evidence missing")
    mapping = r8_disposition.get("machine_result", {})
    if mapping.get("command_0x24_target_selector") != 0 or mapping.get("command_0x26_target_selector") != 1:
        errors.append("R8 fixed-bank command mapping evidence missing")

    summaries = {name: transition_summary(values, name) for name, values in profiles.items()}
    summaries["R9"] = transition_summary(r9, "R9")
    expected_profile_oracle = {
        "supplier": {"shared": 50, "BB": (46, 23, 23, 4), "BW": (34, 17, 17, 16), "WB": (46, 23, 23, 4), "WW": (34, 17, 17, 16)},
        "R1": {"shared": 50, "BB": (0, 0, 0, 50), "BW": (34, 17, 17, 16), "WB": (46, 23, 23, 4), "WW": (0, 0, 0, 50)},
        "R2": {"shared": 20, "BB": (0, 0, 0, 20), "BW": (14, 7, 7, 6), "WB": (18, 9, 9, 2), "WW": (0, 0, 0, 20)},
        "R3": {"shared": 19, "BB": (0, 0, 0, 19), "BW": (13, 7, 6, 6), "WB": (17, 8, 9, 2), "WW": (0, 0, 0, 19)},
        "R4": {"shared": 16, "BB": (0, 0, 0, 16), "BW": (12, 6, 6, 4), "WB": (14, 7, 7, 2), "WW": (0, 0, 0, 16)},
        "R9": {"shared": 16, "BB": (0, 0, 0, 16), "BW": (16, 8, 8, 0), "WB": (16, 8, 8, 0), "WW": (0, 0, 0, 16)},
    }
    exact_profile_oracle: dict[str, Any] = {}
    for profile_name, expected in expected_profile_oracle.items():
        summary = summaries[profile_name]
        actual: dict[str, Any] = {"shared": summary["shared_timing_frames"]}
        for transition, _ in TRANSITIONS:
            transition_data = summary["transitions"][transition]
            actual[transition] = (
                transition_data["effective_drive_frames"],
                transition_data["positive_drive_frames"],
                transition_data["negative_drive_frames"],
                transition_data["zero_drive_frames"],
            )
        exact_profile_oracle[profile_name] = {
            "passed": actual == expected,
            "actual": actual,
            "expected": expected,
        }
        if actual != expected:
            errors.append(f"{profile_name} exact transition phase oracle differs")
    scan = history_scan(r9)
    if scan["duplicate_found"]:
        errors.append("an exact or equivalent R9 topology already exists in worktree/history")
    fixtures = run_negative_fixtures(r9, supplier, lineage, known_hashes)
    if args.self_test and not all(item["rejected"] for item in fixtures):
        errors.append("one or more negative fixtures were not rejected")

    r4_summary = summaries["R4"]
    r9_summary = summaries["R9"]
    comparison = {
        "correction_to_prior_shorthand": "R4 has eight shared timing frames in each polarity half; exact VS decoding yields 12 effective BW drive frames and 14 effective WB drive frames, not eight effective frames per transition.",
        "r4": {
            "shared_total_frames": r4_summary["shared_timing_frames"],
            "per_half_frames": [r4_summary["first_polarity_half_timing_frames"], r4_summary["second_polarity_half_timing_frames"]],
            "bw_effective_drive_frames": r4_summary["transitions"]["BW"]["effective_drive_frames"],
            "wb_effective_drive_frames": r4_summary["transitions"]["WB"]["effective_drive_frames"],
        },
        "r9": {
            "shared_total_frames": r9_summary["shared_timing_frames"],
            "per_half_frames": [r9_summary["first_polarity_half_timing_frames"], r9_summary["second_polarity_half_timing_frames"]],
            "bw_effective_drive_frames": r9_summary["transitions"]["BW"]["effective_drive_frames"],
            "wb_effective_drive_frames": r9_summary["transitions"]["WB"]["effective_drive_frames"],
            "bw_net_volt_frames": r9_summary["transitions"]["BW"]["source_volt_frame_impulse"],
            "wb_net_volt_frames": r9_summary["transitions"]["WB"]["source_volt_frame_impulse"],
        },
    }

    status = "ADMIT_ONE_VARIABLE_R9" if not errors else "NO_GO_R9"
    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_workbench.v1",
        "status": status,
        "errors": errors,
        "hardware_contact": 0,
        "build_or_hex_created": False,
        "popup_count": 0,
        "requirement": "COMP-REQ-308",
        "candidate": {
            "name": "source_field_reorder_phase_parallel_r9",
            "research_only": True,
            "production_enabled": False,
            "single_mechanism_variable": "retain four supplier TP fields and overlap independently source-derived opposite-polarity BW/WB VS fields in those shared phases",
            "lut_hex": r9.hex().upper(),
            "lut_sha256": sha_bytes(r9),
            "protected_tail_hex": r9[153:159].hex().upper(),
            "fr_xon_tail_supplier_exact": r9[144:159] == supplier[144:159],
            "field_lineage": lineage,
        },
        "encoding_proof": {
            "result": "REPRESENTABLE" if all(encoding_checks.values()) else "NOT_PROVED",
            "reason": "TP[nX] is shared phase timing, while VS[nX-LUTm] is independently encoded for every LUT m; LUT1 BW and LUT2 WB can therefore select VSH1 and VSL simultaneously in the same retained phase.",
            "bit_order": "each LUT byte packs A in D7:D6, B in D5:D4, C in D3:D2, D in D1:D0",
            "checks": encoding_checks,
            "official_pdf_pages": [13, 14, 15, 21, 29],
        },
        "profiles": summaries,
        "exact_profile_oracle": exact_profile_oracle,
        "r4_to_r9_comparison": comparison,
        "busy_prediction": {
            "predicted_max_ms": predicted_busy,
            "limit_ms": BUSY_LIMIT_MS,
            "basis": "R9 and R4 both use groups 0..3, zero SR/RP, supplier-exact FR/XON/tail and exactly 16 shared TP frames; R4 measured 598..599 ms. Voltage selection does not add gate frames.",
            "hardware_busy_remains_authoritative": True,
        },
        "history_nonduplication": scan,
        "negative_fixtures": fixtures,
        "prior_evidence": {
            "r6_tp16_retired": r6_diagnosis.get("observed_failure", {}).get("canonical_selected") == "失败",
            "r8_fixed_bank_mapping": {
                "0x24_selector": mapping.get("command_0x24_target_selector"),
                "0x26_selector": mapping.get("command_0x26_target_selector"),
                "post_tag_activations": mapping.get("post_tag_activations"),
            },
        },
        "boundaries": {
            "candidate_build_allowed": False,
            "flash_allowed": False,
            "hardware_contact_allowed": False,
            "production_change_allowed": False,
            "expression_art_change_allowed": False,
            "next_step": "root review only; a separate registry contract is required before any build or physical candidate",
        },
        "source_hashes": hashes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "errors": errors, "artifact": str(OUT), "lut_sha256": sha_bytes(r9)}))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
