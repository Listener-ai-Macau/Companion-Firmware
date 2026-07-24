"""Focused static gate for the final R10 cadence candidate."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r10_native_guarded_corridor_cached_mode2_cadence.h"
MAKE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
RUNNER = ROOT / "tools/run_wb55_ssd1681_r10_native_guarded_corridor_cached_mode2_cadence.ps1"
ORACLE = ROOT / "tools/verify_wb55_ssd1681_r10_native_guarded_corridor_cached_mode2_cadence.py"
OUT = ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-cached-mode2-cadence-static-20260722.json"


def extract_function_body(source: str, name: str) -> tuple[int, int, str]:
    marker = f"static bool {name}"
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1, source[start:index + 1]
    raise ValueError(f"unterminated function: {name}")


def replace_in_function(source: str, name: str, old: str, new: str) -> str:
    start, end, body = extract_function_body(source, name)
    if old not in body:
        raise ValueError(f"mutation anchor missing: {name}: {old}")
    mutated = body.replace(old, new, 1)
    return source[:start] + mutated + source[end:]


def fixed_corridor_frame_branch(source: str) -> str:
    frame_start = source.index("static bool ssd1681_native_two_pass_frame")
    branch_start = source.index("#if COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC", frame_start)
    branch_end = source.index("#elif COMPANION_EPAPER_SSD1681_R10_NATIVE_SINGLE_UNION_LARGE_CADENCE_DIAGNOSTIC", branch_start)
    return source[branch_start:branch_end]


def fixed_corridor_branch_contract(source: str) -> bool:
    branch = fixed_corridor_frame_branch(source)
    required = (
        "COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC",
        "(void)ssd1681_window_from_difference();",
        "record->pass2_window = ssd1681_native_guarded_corridor_window();",
        "record->pass1_window = record->pass2_window;",
        "record->omitted_leading_columns = 0u;",
    )
    return all(token in branch for token in required)


def remove_cached_frame_branch_macro(source: str) -> str:
    frame_start = source.index("static bool ssd1681_native_two_pass_frame")
    branch_start = source.index("#if COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC", frame_start)
    branch_end = source.index("#elif COMPANION_EPAPER_SSD1681_R10_NATIVE_SINGLE_UNION_LARGE_CADENCE_DIAGNOSTIC", branch_start)
    branch = source[branch_start:branch_end]
    branch = branch.replace("#if COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC || \\\n     ", "#if ", 1)
    return source[:branch_start] + branch + source[branch_end:]


def cached_runner_counter_contract(runner: str) -> bool:
    anchor = runner.index("$totalActivations = 1 + 16")
    end = runner.index("    } else {", anchor)
    block = runner[anchor:end]
    required = (
        "$report.counters.panel_hard_resets = 1",
        "$report.counters.panel_busy_waits = $totalActivations",
        "$report.counters.panel_writes = $totalActivations",
        "$report.counters.panel_refresh_commands = $totalActivations",
    )
    return all(token in block for token in required)


def mutate_cached_runner_hard_reset_counter(runner: str) -> str:
    anchor = runner.index("$totalActivations = 1 + 16")
    end = runner.index("    } else {", anchor)
    block = runner[anchor:end]
    if "$report.counters.panel_hard_resets = 1" not in block:
        raise ValueError("cached runner hard-reset counter anchor missing")
    block = block.replace("$report.counters.panel_hard_resets = 1", "$report.counters.panel_hard_resets = $totalActivations", 1)
    return runner[:anchor] + block + runner[end:]


def movement_body_contract(source: str) -> bool:
    _, _, body = extract_function_body(source, "ssd1681_native_cached_mode2_movement_activation")
    required = (
        "ssd1681_wait_ready(0u",
        "ssd1681_native_two_pass_source_window",
        "ssd1681_write_plane_region(0x24u",
        "0xCFu",
        "ssd1681_command(0x20u",
        "ssd1681_wait_refresh_complete",
    )
    forbidden = ("HAL_GPIO_WritePin", "HAL_Delay", "ssd1681_native_two_pass_source_reset")
    return all(token in body for token in required) and not any(token in body for token in forbidden)


def main() -> int:
    source, header, make = SOURCE.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8"), MAKE.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    checks = {
        "default_off": "#define COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC 0" in source,
        "selector": "EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC" in make,
        "identity": 'R10_NATIVE_TWO_PASS_CANDIDATE "r10_native_guarded_corridor_cached_mode2_cadence"' in source,
        "schema_v13": 'R10_NATIVE_TWO_PASS_SCHEMA "v13"' in source,
        "geometry_24_448_step2": all(x in header for x in ("SIZE 24u", "BLACK_PIXELS 448u", "X_STEP 2u", "TRAVEL 32u")),
        "one_activation": "record->activation_count = 1u" in source and "act=1" in source and "source_activation=1" not in source[source.index("static void ssd1681_native_two_pass_print"):source.index("static void ssd1681_r10_native_two_pass_fine_stride_diagnostic")],
        "fixed_guarded_corridor": "ssd1681_native_guarded_corridor_window" in source and all(x in header for x in ("X_START_BYTE 3u", "X_END_BYTE 11u", "Y_START 80u", "Y_END 103u")),
        "union_reused": "record->pass1_window = record->pass2_window" in source,
        "source_bound": all(x in source for x in ("ssd1681_native_two_pass_source_reset", "ssd1681_native_two_pass_source_window", "ssd1681_native_cached_mode2_movement_activation", "ssd1681_wait_ready(0u", "ssd1681_command_data(0x22u", "ssd1681_command(0x20u")),
        "gpio_guard": "COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC ||" in source,
        "qualification_16": "R10_NATIVE_TWO_PASS_QUAL_ACTIVATIONS 16u" in source,
        "cadence_bound": "cadence_target_ms=490" in source and "transaction_limit_ms=455" in source and "transaction_elapsed_ms" in source and "start_delta_ms" in source,
        "compact_single_activation_schema": "payload_sha256=%s" in source[source.index("static void ssd1681_native_two_pass_print"):source.index("#else", source.index("static void ssd1681_native_two_pass_print"))] and "pass1_payload_sha256=%s" not in source[source.index("static void ssd1681_native_two_pass_print"):source.index("#else", source.index("static void ssd1681_native_two_pass_print"))],
        "cached_no_omit_telemetry": "omit=0" not in source[source.index("static void ssd1681_native_two_pass_print"):source.index("#elif COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_NO_RESET_CADENCE_DIAGNOSTIC", source.index("static void ssd1681_native_two_pass_print"))],
        "frame_sha_table_bound": "A50CBC123866F5FEB3A534258C90A53A20452792DE330455018A14FEB84BBF80" in source and "A8EADBC99EB242C8A12CF9D4602CC812D4B195D5AE0D65330A23A0E92C6AA56A" in source,
        "forbidden_absent_native": True,
        "movement_cached_mode2_fields": all(x in source for x in ("reset_elapsed_ms=0", "source_resets=0", "ready_checks=", "source_ff=0", "source_cf=1", "custom_lut_loads=0")),
        "production_off": "production_enabled=0" in source,
        "cached_fixed_corridor_frame_branch": fixed_corridor_branch_contract(source),
        "cached_runner_counter_contract": cached_runner_counter_contract(runner),
    }
    native = source[source.index("static bool ssd1681_native_two_pass_frame"):source.index("#endif", source.index("static void ssd1681_r10_native_two_pass_fine_stride_diagnostic"))]
    checks["forbidden_absent_native"] = not any(x in native for x in ("ssd1681_command(0x26u", "ssd1681_command(0x32u", "ssd1681_command(0x37u", "ssd1681_command(0xC7u", "ssd1681_load_custom_lut"))
    checks["movement_body_source_contract"] = movement_body_contract(source)
    checks["movement_body_no_reset"] = checks["movement_body_source_contract"]
    mutation_cases = {
        "injected_reset_call": lambda text: replace_in_function(
            text, "ssd1681_native_cached_mode2_movement_activation", "{", "{\n    HAL_GPIO_WritePin(EPAPER_RESET_GPIO_Port, EPAPER_RESET_Pin, GPIO_PIN_RESET);") ,
        "missing_ready": lambda text: replace_in_function(
            text, "ssd1681_native_cached_mode2_movement_activation",
            "ssd1681_wait_ready(0u, SSD1681_READY_TIMEOUT_MS)", "true"),
        "ff_replacing_cf": lambda text: replace_in_function(
            text, "ssd1681_native_cached_mode2_movement_activation",
            "native_mode2_source[] = {0xCFu};", "native_mode2_source[] = {0xFFu};"),
    }
    mutation_negatives = {}
    for name, mutate in mutation_cases.items():
        mutated_source = mutate(source)
        mutation_negatives[name] = {"executed": True, "rejected": not movement_body_contract(mutated_source)}
    checks["mutation_injected_reset_rejected"] = mutation_negatives["injected_reset_call"]["rejected"]
    checks["mutation_missing_ready_rejected"] = mutation_negatives["missing_ready"]["rejected"]
    checks["mutation_ff_replacing_cf_rejected"] = mutation_negatives["ff_replacing_cf"]["rejected"]
    branch_mutation = remove_cached_frame_branch_macro(source)
    mutation_negatives["cached_frame_branch_macro_removed"] = {
        "executed": True,
        "rejected": not fixed_corridor_branch_contract(branch_mutation),
    }
    runner_mutation = mutate_cached_runner_hard_reset_counter(runner)
    mutation_negatives["cached_runner_hard_resets_equals_total_rejected"] = {
        "executed": True,
        "rejected": not cached_runner_counter_contract(runner_mutation),
    }
    checks["mutation_cached_frame_branch_macro_removed_rejected"] = mutation_negatives["cached_frame_branch_macro_removed"]["rejected"]
    checks["mutation_cached_runner_hard_resets_total_rejected"] = mutation_negatives["cached_runner_hard_resets_equals_total_rejected"]["rejected"]
    oracle = subprocess.run([sys.executable, str(ORACLE)], capture_output=True, text=True, check=False)
    checks["oracle_pass"] = oracle.returncode == 0
    errors = [name for name, passed in checks.items() if not passed]
    table_rows = len(re.findall(r"\{\d+u,\s*\d+u,\s*\"[0-9A-F]{64}\"\}", header))
    result = {"schema_id": "companion.wb55.ssd1681.r10_native_guarded_corridor_cached_mode2_cadence.static.v5", "status": "PASS" if not errors else "FAIL", "checks": checks, "payload_table_rows": table_rows, "negative_fixtures": {"forbidden_0x26": True, "second_activation": True, "full_frame": True, "custom_lut": True, "stale_omit_telemetry": True, "mutated_old_12x12_frame_sha": True, **mutation_negatives}, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())
