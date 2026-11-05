"""Offline R12 r5 target-mapping, pixel, payload, scope, and edge oracle."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r5 as base

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler.h"
PDF = ROOT / ".cache/validation/ssd1681-read-only-research/ssd1681-rev013-2.pdf"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r5-oracle-20260723.json"
EXPECTED_PDF_SHA = "2989DB3DBBCE190F6E1F065A169479BF4FE911896FF8805894549F792FE9B53B"
HELPER = "ssd1681_r12_direct_bsrr_payload"
R12_GUARD = "#if COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC"
EXPECTED_EDGE_OPERATIONS = (
    "SCL_LOW_BSRR", "SDA_DATA_BSRR", "LOW_NOP", "LOW_NOP",
    "SCL_HIGH_BSRR", "HIGH_NOP", "HIGH_NOP", "SHIFT_LEFT",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def mapping_negative_fixtures() -> dict[str, dict[str, object]]:
    raw = base.source_data()
    _, _, raster = base.generator.parse_p4(raw["calm"], "calm")
    controller = bytes(value ^ 0xFF for value in raster)
    expected = base.normal_target_mapping(controller)
    missing = controller
    double = base.normal_target_mapping(expected)
    horizontal_only = b"".join(
        bytes(int(f"{value:08b}"[::-1], 2) for value in controller[row * 25:(row + 1) * 25])
        for row in range(200))
    rotation_only = base.normal_target_mapping(horizontal_only)
    return {
        "missing_transform": {"rejected": missing != expected},
        "double_transform": {"rejected": double != expected},
        "horizontal_only": {"rejected": horizontal_only != expected},
        "rotation_only": {"rejected": rotation_only != expected},
        "wrong_corridor": {"rejected": (4, 21, 72, 177) != base.WINDOW},
    }


def function_region(source: str, start_marker: str, end_marker: str) -> tuple[int, int, str]:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return start, end, source[start:end]


def helper_region(source: str) -> tuple[int, int, str]:
    return function_region(source, f"static bool {HELPER}", "static bool ssd1681_write_r12_v22_corridor")


def bit_loop_body(helper: str) -> str:
    loop = helper.index("for (uint8_t bit = 0u;")
    opening = helper.index("{", loop)
    depth = 0
    for index in range(opening, len(helper)):
        if helper[index] == "{":
            depth += 1
        elif helper[index] == "}":
            depth -= 1
            if depth == 0:
                return helper[opening + 1:index]
    raise ValueError("unterminated R12 bit loop")


def explicit_edge_operations(helper: str) -> list[str]:
    operations: list[str] = []
    high_seen = False
    for raw in bit_loop_body(helper).splitlines():
        line = raw.strip()
        if line == "GPIOA->BSRR = sck_low;":
            operations.append("SCL_LOW_BSRR")
        elif line.startswith("GPIOC->BSRR ="):
            operations.append("SDA_DATA_BSRR")
        elif line == "GPIOA->BSRR = sck_high;":
            operations.append("SCL_HIGH_BSRR")
            high_seen = True
        elif line == "__NOP();":
            operations.append("HIGH_NOP" if high_seen else "LOW_NOP")
        elif line == "value <<= 1u;":
            operations.append("SHIFT_LEFT")
        elif line == "value >>= 1u;":
            operations.append("SHIFT_RIGHT")
    return operations


def reference_facts(source: str) -> dict[str, object]:
    helper_start, _, _ = helper_region(source)
    definition_name = source.index(HELPER, helper_start)
    writer_start, writer_end, writer = function_region(
        source, "static bool ssd1681_write_r12_v22_corridor", "#endif")
    command_start, command_end, _ = function_region(
        source, "static bool ssd1681_command(uint8_t command)", "static bool ssd1681_data")
    baseline_start, baseline_end, _ = function_region(
        source, "static bool ssd1681_native_two_pass_baseline", "static void ssd1681_native_two_pass_print")
    guard_start = source.rfind(R12_GUARD, 0, helper_start)
    guard_end = source.index("#endif", writer_end - len("#endif")) + len("#endif")
    references = [match.start() for match in re.finditer(rf"\b{HELPER}\s*\(", source)]
    calls = [position for position in references if position != definition_name]
    exact_call = re.compile(
        rf"{HELPER}\s*\(\s*s_r12_v22_corridor_payload\s*,\s*"
        r"sizeof\(s_r12_v22_corridor_payload\)\s*\)", re.DOTALL)
    command_position = writer.find("ssd1681_command(0x24u)")
    call_position = writer.find(HELPER)
    return {
        "reference_count": len(references),
        "definition_position": definition_name,
        "call_positions": calls,
        "call_count": len(calls),
        "writer_start": writer_start,
        "writer_end": writer_end,
        "guard_start": guard_start,
        "guard_end": guard_end,
        "all_calls_in_writer": len(calls) == 1 and writer_start <= calls[0] < writer_end,
        "all_calls_in_r12_guard": guard_start >= 0 and all(guard_start <= position < guard_end for position in calls),
        "call_after_0x24": command_position >= 0 and call_position > command_position,
        "call_fixed_buffer_and_sizeof": len(exact_call.findall(writer)) == 1,
        "call_not_in_command": not any(command_start <= position < command_end for position in calls),
        "call_not_in_baseline": not any(baseline_start <= position < baseline_end for position in calls),
    }


def analyze_transport(source: str) -> tuple[dict[str, bool], dict[str, object]]:
    helper_start, _, helper = helper_region(source)
    writer_start, writer_end, writer = function_region(
        source, "static bool ssd1681_write_r12_v22_corridor", "#endif")
    operations = explicit_edge_operations(helper)
    refs = reference_facts(source)
    operation_count = len(operations)
    scl_upper_mhz = 32 / operation_count if operation_count else None
    shift_position = max(helper.find("value <<= 1u"), helper.find("value >>= 1u"))
    pdf_exists = PDF.is_file()
    pdf_sha = sha(PDF) if pdf_exists else None
    checks = {
        "ssd1681_rev013_pdf_hash_matches": pdf_exists and pdf_sha == EXPECTED_PDF_SHA,
        "r12_scoped_helper_definition": (
            source.count(f"static bool {HELPER}") == 1
            and source.rfind(R12_GUARD, 0, helper_start) > source.rfind("#endif", 0, helper_start)
        ),
        "helper_reference_count_definition_plus_one_call": refs["reference_count"] == 2 and refs["call_count"] == 1,
        "helper_call_only_in_r12_writer": bool(refs["all_calls_in_writer"]),
        "helper_call_within_r12_guard": bool(refs["all_calls_in_r12_guard"]),
        "helper_not_used_by_command": bool(refs["call_not_in_command"]),
        "helper_not_used_by_baseline": bool(refs["call_not_in_baseline"]),
        "helper_call_after_0x24": bool(refs["call_after_0x24"]),
        "helper_call_fixed_buffer_and_sizeof": bool(refs["call_fixed_buffer_and_sizeof"]),
        "helper_used_by_r12_payload_only": all(bool(refs[key]) for key in (
            "all_calls_in_writer", "all_calls_in_r12_guard", "call_not_in_command",
            "call_not_in_baseline", "call_after_0x24", "call_fixed_buffer_and_sizeof")),
        "commands_remain_software_vendor_edges": (
            "ssd1681_command(0x24u)" in writer and "ssd1681_data(" not in writer
            and "ssd1681_command_data(0x22u" not in writer
        ),
        "edge_order_low_data_nops_high_nops_shift": operations == list(EXPECTED_EDGE_OPERATIONS),
        "low_phase_has_two_nops": operations.count("LOW_NOP") == 2,
        "high_phase_has_two_nops": operations.count("HIGH_NOP") == 2,
        "msb_first": "value & 0x80u" in helper and "value <<= 1u" in helper and "value >>= 1u" not in helper,
        "exact_1908_length": (
            "length != COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_BYTES" in helper
            and "COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_BYTES 1908u" in HEADER.read_text(encoding="utf-8")
        ),
        "final_scl_low": shift_position >= 0 and helper.rfind("GPIOA->BSRR = sck_low") > shift_position,
        "payload_bytes_come_from_row_copy": "memcpy(&s_r12_v22_corridor_payload[offset], row, bytes_per_row);" in writer,
        "explicit_minimum_operation_count_is_8": operation_count == 8,
        "frequency_proof_32_div_8_is_4_below_20": (
            operations == list(EXPECTED_EDGE_OPERATIONS)
            and operation_count == 8 and scl_upper_mhz == 4 and scl_upper_mhz < 20
        ),
    }
    evidence = {
        "ssd1681_rev013_pdf_path": str(PDF.relative_to(ROOT)).replace("\\", "/"),
        "ssd1681_rev013_pdf_sha256": pdf_sha,
        "controller_write_limit_mhz": 20,
        "mcu_clock_mhz": 32,
        "explicit_operations_per_bit": operations,
        "explicit_minimum_instruction_cycles_per_bit": operation_count,
        "conservative_scl_upper_bound_mhz": scl_upper_mhz,
        "helper_references": refs,
        "writer_source_span": [writer_start, writer_end],
    }
    return checks, evidence


def validate_transport(source: str) -> dict[str, bool]:
    return analyze_transport(source)[0]


def replace_in_helper(source: str, old: str, new: str) -> str:
    _, _, helper = helper_region(source)
    if old not in helper:
        raise ValueError(f"helper mutation anchor absent: {old!r}")
    return source.replace(helper, helper.replace(old, new, 1), 1)


def negative_fixtures(source: str) -> dict[str, dict[str, object]]:
    _, _, writer = function_region(source, "static bool ssd1681_write_r12_v22_corridor", "#endif")
    guard_start = source.rfind(R12_GUARD, 0, source.index(f"static bool {HELPER}"))
    baseline_anchor = "    if (!ssd1681_native_two_pass_activation(&window, reset_elapsed_ms, transaction_elapsed_ms, busy_elapsed_ms)) return false;"
    mutations = {
        "fast_helper_used_by_command": source.replace(
            "    bool ok = ssd1681_spi_tx(&command, 1u);",
            f"    (void){HELPER}(s_r12_v22_corridor_payload, sizeof(s_r12_v22_corridor_payload));\n    bool ok = ssd1681_spi_tx(&command, 1u);", 1),
        "fast_helper_used_by_baseline": source.replace(
            baseline_anchor,
            f"    (void){HELPER}(s_r12_v22_corridor_payload, sizeof(s_r12_v22_corridor_payload));\n{baseline_anchor}", 1),
        "fast_helper_used_outside_r12": (
            source[:guard_start]
            + f"static bool r4_outside_scope_probe(void) {{ return {HELPER}(s_r12_v22_corridor_payload, sizeof(s_r12_v22_corridor_payload)); }}\n"
            + source[guard_start:]
        ),
        "missing_low_phase_nop": replace_in_helper(source,
            "GPIOC->BSRR = (value & 0x80u) != 0u ? mosi_high : mosi_low;\n            __NOP();",
            "GPIOC->BSRR = (value & 0x80u) != 0u ? mosi_high : mosi_low;"),
        "missing_high_phase_nop": replace_in_helper(source,
            "GPIOA->BSRR = sck_high;\n            __NOP();",
            "GPIOA->BSRR = sck_high;"),
        "wrong_edge_order": replace_in_helper(source,
            "GPIOA->BSRR = sck_low;\n            GPIOC->BSRR = (value & 0x80u) != 0u ? mosi_high : mosi_low;",
            "GPIOC->BSRR = (value & 0x80u) != 0u ? mosi_high : mosi_low;\n            GPIOA->BSRR = sck_low;"),
        "lsb_first": replace_in_helper(
            replace_in_helper(source, "value & 0x80u", "value & 0x01u"),
            "value <<= 1u", "value >>= 1u"),
        "payload_length_not_1908": replace_in_helper(source,
            "length != COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_BYTES", "length != 1907u"),
        "payload_bytes_changed": source.replace(
            "memcpy(&s_r12_v22_corridor_payload[offset], row, bytes_per_row);",
            "memset(&s_r12_v22_corridor_payload[offset], 0, bytes_per_row);", 1),
    }
    expected_false = {
        "fast_helper_used_by_command": ("helper_not_used_by_command", "helper_used_by_r12_payload_only"),
        "fast_helper_used_by_baseline": ("helper_not_used_by_baseline", "helper_used_by_r12_payload_only"),
        "fast_helper_used_outside_r12": ("helper_call_within_r12_guard", "helper_used_by_r12_payload_only"),
        "missing_low_phase_nop": ("low_phase_has_two_nops", "explicit_minimum_operation_count_is_8", "frequency_proof_32_div_8_is_4_below_20"),
        "missing_high_phase_nop": ("high_phase_has_two_nops", "explicit_minimum_operation_count_is_8", "frequency_proof_32_div_8_is_4_below_20"),
        "wrong_edge_order": ("edge_order_low_data_nops_high_nops_shift", "frequency_proof_32_div_8_is_4_below_20"),
        "lsb_first": ("msb_first", "edge_order_low_data_nops_high_nops_shift", "frequency_proof_32_div_8_is_4_below_20"),
        "payload_length_not_1908": ("exact_1908_length",),
        "payload_bytes_changed": ("payload_bytes_come_from_row_copy",),
    }
    base_checks = validate_transport(source)
    results: dict[str, dict[str, object]] = {}
    for name, mutated in mutations.items():
        mutated_checks = validate_transport(mutated)
        invariants = expected_false[name]
        base_true = all(base_checks[invariant] is True for invariant in invariants)
        mutated_false = all(mutated_checks[invariant] is False for invariant in invariants)
        results[name] = {
            "expected_false_invariants": list(invariants),
            "base_invariants_true": base_true,
            "mutated_invariants": {invariant: mutated_checks[invariant] for invariant in invariants},
            "rejected": base_true and mutated_false,
        }
    return results


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    base_main = base.main()
    base_result = json.loads(base.OUT.read_text(encoding="utf-8")) if base.OUT.is_file() else {}
    checks, evidence = analyze_transport(source)
    negatives = negative_fixtures(source)
    mapping_negatives = mapping_negative_fixtures()
    errors = [key for key, value in checks.items() if not value]
    errors.extend(name for name, value in negatives.items() if not value["rejected"])
    errors.extend(name for name, value in mapping_negatives.items() if not value["rejected"])
    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.oracle.v7",
        "status": "PASS" if base_main == 0 and not errors else "FAIL",
        "pixel_payload_oracle": "r5_target_mapping_and_preview_pass",
        "target_mapping": {
            "normal_rotation_degrees": 180,
            "normal_mirror_x": 1,
            "composed_transform": "vertical_flip",
            "applied_once_to_previous_and_current": "ssd1681_r12_apply_normal_target_mapping",
            "physical_to_browser_pixel_difference": base_result.get("pixel_oracle", {}).get("physical_to_browser_pixel_difference"),
        },
        "detail_artifact": base_result.get("detail_artifact"),
        "detail_artifact_sha256": sha(base.OUT) if base.OUT.is_file() else None,
        "controller_frame_sha256": base_result.get("controller_frame_sha256"),
        "corridor_payload_sha256": base_result.get("corridor_payload_sha256"),
        "pixel_oracle_detail": base_result.get("pixel_oracle"),
        "preview_evidence": base_result.get("pixel_oracle", {}).get("preview_evidence"),
        "transport_checks": checks,
        "transport_evidence": evidence,
        "negative_fixtures": negatives,
        "mapping_negative_fixtures": mapping_negatives,
        "driver_sha256": sha(SOURCE),
        "errors": errors,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
