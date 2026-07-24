"""Focused source and host-tool gate for the default-off R12 sampler."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_log as parser

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler.h"
ASSETS = ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler_assets.h"
MAKE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
ORACLE = ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.py"
PARSER = ROOT / "tools/verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_log.py"
GENERATOR = ROOT / "tools/generate_r12_v22_asset_header.py"
OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-static-20260722.json"
ORACLE_OUT = ROOT / "docs/validation/companion-ssd1681-r12-v22-calm-curious-warm-sampler-r3-oracle-20260722.json"
WORK_PACKAGE = ROOT / "docs/validation/companion-r12-v22-calm-curious-warm-sampler-r3-work-package-20260722.json"
PROTECTED = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


def r3_transport_checks(source: str) -> dict[str, bool]:
    setup = between(source, "static bool ssd1681_r12_setup_corridor_window", "static bool ssd1681_r12_reset_corridor_counters")
    counters = between(source, "static bool ssd1681_r12_reset_corridor_counters", "#endif\n\nstatic bool ssd1681_native_two_pass_activation")
    movement = between(source, "static bool ssd1681_native_cached_mode2_movement_activation", "static bool ssd1681_native_two_pass_frame")
    diagnostic_start = source.index("static void ssd1681_r10_native_two_pass_fine_stride_diagnostic")
    qualification_start = source.index("    for (uint8_t index = 0u;", diagnostic_start)
    setup_flow = source[diagnostic_start:qualification_start]
    order = (
        "ssd1681_wait_ready",
        "ssd1681_r12_reset_corridor_counters()",
        "ssd1681_write_r12_v22_corridor(s_frame, window)",
        "ssd1681_command_data(0x22u",
        "ssd1681_command(0x20u)",
        "ssd1681_wait_refresh_complete",
    )
    return {
        "r12_window_setup_exactly_once_after_baseline_before_qualification": (
            setup_flow.count("ok = ssd1681_r12_setup_corridor_window();") == 1 and
            source.count("ssd1681_r12_setup_corridor_window();") == 1 and
            setup_flow.index("if (!ok) { return; }") < setup_flow.index("ok = ssd1681_r12_setup_corridor_window();")
        ),
        "r12_window_setup_exact_44_45_once": (
            setup.count("ssd1681_command_data(0x44u") == 1 and
            setup.count("ssd1681_command_data(0x45u") == 1
        ),
        "r12_window_setup_fixed_corridor": all(token in setup for token in (
            "COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_X_START_BYTE",
            "COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_X_END_BYTE",
            "{0x7Fu, 0x00u, 0x16u, 0x00u}",
        )),
        "r12_window_setup_no_ram_write_or_refresh": not any(token in setup for token in (
            "ssd1681_command(0x24u)", "ssd1681_data(", "ssd1681_command_data(0x22u",
            "ssd1681_command(0x20u)", "ssd1681_wait_refresh_complete", "0x3Cu",
        )),
        "r12_window_setup_failure_terminal_activation": all(token in setup_flow for token in (
            "memset(&setup_fault_record, 0, sizeof(setup_fault_record));",
            "setup_fault_record.transaction_elapsed_ms = HAL_GetTick() - setup_start_ms;",
            'ssd1681_r12_print_fault("qualification", 1u, &setup_fault_record, 0u,',
            '"activation");', "return;",
        )),
        "r12_movement_counters_exactly_once": (
            counters.count("ssd1681_command_data(0x4Eu") == 1 and
            counters.count("ssd1681_command_data(0x4Fu") == 1 and
            movement.count("ssd1681_r12_reset_corridor_counters()") == 1
        ),
        "r12_movement_counter_helper_has_no_window_border_write_or_refresh": not any(
            token in counters for token in ("0x3Cu", "0x44u", "0x45u", "0x24u", "0x22u", "0x20u", "ssd1681_data(")
        ),
        "r12_movement_has_no_window_or_border_commands": not any(
            token in movement for token in ("0x3Cu", "0x44u", "0x45u")
        ),
        "r12_movement_command_order_unchanged": all(
            movement.index(left) < movement.index(right) for left, right in zip(order, order[1:])
        ),
    }


def validate_r3_transport_source(source: str) -> None:
    failed = [name for name, passed in r3_transport_checks(source).items() if not passed]
    if failed:
        raise ValueError("r3 transport contract: " + ", ".join(failed))


def expect_source_reject(name: str, source: str, results: dict[str, bool]) -> None:
    try:
        validate_r3_transport_source(source)
    except (ValueError, IndexError):
        results[name] = True
    else:
        results[name] = False


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    make = MAKE.read_text(encoding="utf-8")
    parser_text = PARSER.read_text(encoding="utf-8")
    baseline = between(source, "static bool ssd1681_native_two_pass_baseline", "static void ssd1681_native_two_pass_print")
    movement = between(source, "static bool ssd1681_native_cached_mode2_movement_activation", "static bool ssd1681_native_two_pass_frame")
    packed_writer = between(source, "static bool ssd1681_write_r12_v22_corridor", "#if COMPANION_EPAPER_SSD1681_R10_BALL_DIAGNOSTIC")
    qualification_start = source.index("    for (uint8_t index = 0u;")
    qualification_loop = source[qualification_start:source.index(
        '        ssd1681_r12_print_fault("qualification"', qualification_start)]
    qualification_transport_branch = qualification_loop[:qualification_loop.index(
        "        if (record.transaction_elapsed_ms > 460u")]
    qualification_threshold_branch = qualification_loop[qualification_loop.index(
        "        if (record.transaction_elapsed_ms > 460u"):]
    print_body = between(source, "static void ssd1681_native_two_pass_print", "static void ssd1681_r10_native_two_pass_fine_stride_diagnostic")
    metadata_start = source.index('printf(COMP_R_NATIVE_LOG_PREFIX " armed candidate=%s schema=v2')
    metadata_body = source[metadata_start:source.index("#else", metadata_start)]
    tools = {
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler.ps1",
    }
    host = {name: path.read_text(encoding="utf-8") for name, path in tools.items()}

    checks: dict[str, bool] = {
        "default_off": "#define COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC 0" in source,
        "production_off": "production_enabled=0" in metadata_body,
        "isolated_make_selector": "EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC" in make,
        "qualification_is_four_exact_cycles": "qualification[16u]" in header and header.count("44u, 56u, 44u, 32u") == 5,
        "observation_loop_is_one_exact_cycle": "LOOP_LENGTH 4u" in header and "loop[4u]" in header,
        "corridor_constants": all(token in header for token in ("X_START_BYTE 4u", "X_END_BYTE 21u",
                                                                  "Y_START 72u", "Y_END 177u", "BYTES 1908u")),
        "baseline_has_explicit_full_window": all(token in baseline for token in (
            "COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC",
            ".x_start_byte = 0u", ".x_end_byte = SSD1681_BYTES_PER_ROW - 1u",
            ".y_start = 0u", ".y_end = SSD1681_HEIGHT - 1u", ".changed = true")),
        "baseline_uses_reset_ff_activation": "ssd1681_native_two_pass_activation(&window" in baseline,
        "movement_is_corridor_current_only": "ssd1681_write_plane_region(0x24u, s_frame, window)" in movement,
        "r12_movement_uses_packed_corridor": "ssd1681_write_r12_v22_corridor(s_frame, window)" in movement,
        "r12_packed_payload_fixed_bss": "static uint8_t s_r12_v22_corridor_payload[COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_BYTES]" in source,
        "r12_packed_payload_one_data_call": (
            (packed_writer.count("ssd1681_data(") == 1 and
             packed_writer.count("ssd1681_r12_direct_bsrr_payload(") == 0) or
            (packed_writer.count("ssd1681_data(") == 0 and
             packed_writer.count("ssd1681_r12_direct_bsrr_payload(") == 1)
        ) and packed_writer.count("ssd1681_command(0x24u)") == 1 and
            "memcpy(&s_r12_v22_corridor_payload" in packed_writer,
        "r12_packed_payload_no_row_data_loop": "ssd1681_data(row" not in packed_writer,
        "r12_qualification_record_cleared_before_frame": qualification_loop.count("memset(&record, 0, sizeof(record));") == 1,
        "r12_transport_false_saves_fault_snapshot_before_break": all(token in qualification_transport_branch for token in (
            "qualification_fault_record = record;", "qualification_fault_index = (uint32_t)index + 1u",
            "qualification_fault_delta_ms = record.start_delta_ms;", "break;")) and
            qualification_transport_branch.index("qualification_fault_record = record;") < qualification_transport_branch.index("break;"),
        "r12_threshold_cadence_saves_fault_snapshot_before_break": all(token in qualification_threshold_branch for token in (
            "qualification_fault_record = record;", "qualification_fault_index = (uint32_t)index + 1u",
            "qualification_fault_delta_ms = record.start_delta_ms;", "ok = false;", "break;")) and
            qualification_threshold_branch.index("qualification_fault_record = record;") < qualification_threshold_branch.index("break;"),
        "movement_uses_cf_once": movement.count("0xCFu") == 1 and "0xFFu" not in movement,
        "movement_has_no_reset": "HAL_GPIO_WritePin" not in movement and "ssd1681_hardware_reset" not in movement,
        "movement_has_one_ready_and_activation": movement.count("ssd1681_wait_ready") == 1 and movement.count("ssd1681_command(0x20u)") == 1,
        "record_schema_v2_three_frame_ids": "s=v2" in print_body and "ssd1681_r12_frame_id(previous_x)" in print_body and
                                            "ssd1681_r12_frame_id(current_x)" in print_body,
        "record_true_corridor": "w=4-21,72-177" in print_body,
        "record_does_not_emit_internal_pairs": "p=%u,%u n=%u,%u w=4-21,72-177" not in print_body,
        "truthful_start_metadata": all(token in metadata_body for token in (
            "format=200x200_1bpp", "frames=calm,curious,warm", "path=0-1-2-1-0",
            "baseline_window=0-24,0-199", "baseline_bytes=5000", "corridor=4-21,72-177",
            "corridor_bytes=1908", "control=0xCF", "busy_ms=600", "transaction_ms=460",
            "cadence_ms=480", "ring=65536")),
        "r12_metadata_has_no_ball_contract": not any(token in metadata_body for token in (
            "24x24", "nodes=A0", "path=A0", "black_pixels", "nodes=", "3-19,64-135", "1224")),
        "baseline_metadata_truthful": "baseline frame=0 window=0-24,0-199 bytes=5000" in source,
        "firmware_metadata_matches_parser": (
            'armed candidate=%s schema=v2 ring=65536 popup_commands=0 production_enabled=0' in metadata_body and
            all(line.removeprefix("[r12] ").removesuffix("\r\n") in metadata_body
                for line in parser.metadata_lines()[1:10])),
        "parser_is_r12_v2": 'SCHEMA = "v2"' in parser_text and 'WINDOW = "4-21,72-177"' in parser_text,
        "parser_has_three_frames_and_four_transitions": "TRANSITIONS = ((0, 1), (1, 2), (2, 1), (1, 0))" in parser_text,
        "parser_has_no_ball_model": not any(token in parser_text for token in ("24x24", "A0..A8", "NODES =", "def frame(node")),
        "parser_old_window_only_negative_fixture": parser_text.count("3-19,64-135") == 1 and '"wrong_window"' in parser_text,
        "parser_structured_fault_terminal": 'FAULT_REASONS = {"activation", "transaction", "busy", "cadence"}' in parser_text and
                                             'NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_FAULT' in parser_text and
                                             'expected_reason = ("busy"' in parser_text,
        "protected_hash": PROTECTED.is_file() and sha(PROTECTED) == PROTECTED_SHA,
        "work_package_hash": WORK_PACKAGE.is_file(),
        "asset_header_three_full_frames": ASSETS.read_text(encoding="ascii").count("[COMP_R12_V22_FRAME_BYTES]") == 3,
    }
    checks.update(r3_transport_checks(source))
    for name, text in host.items():
        checks[f"{name}_execute_and_checkonly"] = "[switch]$Execute" in text and "[switch]$CheckOnly" in text
        checks[f"{name}_candidate"] = parser.CANDIDATE in text
    checks.update({
        "monitor_v2_frame_protocol": "[r12] s=v2" in host["monitor"] and "$positions=@(1,2,1,0)" in host["monitor"],
        "monitor_no_ball_protocol": not any(token in host["monitor"] for token in ("3-19,64-135", "24x24", "A0..A8")),
        "monitor_fixed_ring": all(token in host["monitor"] for token in ("65536", "cadence_over_480_ms", "transaction_over_460_ms", "busy_over_600_ms")),
        "monitor_fault_terminal_no_popup": "NO_GO_R12_SAFETY_FAULT" in host["monitor"] and "popup_count=0" in host["monitor"],
        "qualification_and_loop_fault_terminal_no_popup": (
            'ssd1681_r12_print_fault("qualification"' in source and
            'ssd1681_r12_print_fault("loop"' in source and
            'NO_GO_R12_SAFETY_FAULT' in host["monitor"] and
            'popup_count=0' in host["monitor"]),
        "runner_exact_future_authorization": '[string]$authorization.requirement_id -eq "COMP-REQ-376"' in host["runner"] and
                                              "requirement_id -match '^COMP-REQ-" not in host["runner"],
        "launcher_exact_future_authorization": "requirement_id -ne 'COMP-REQ-376'" in host["launcher"],
        "launcher_rejects_prior_r12_legacy_and_wildcard": all(token in host["launcher"] for token in (
            "'COMP-REQ-370'", "'COMP-REQ-371'", "'COMP-REQ-372'", "'COMP-REQ-373'",
            "'COMP-REQ-374'", "'COMP-REQ-375'", "'COMP-REQ-323'", "'COMP-REQ-999'")),
        "runner_true_sampler_scope": all(token in host["runner"] for token in (
            "full 5000-byte calm baseline", "calm-curious-warm-curious-calm", "full 1908-byte current rewrite",
            "x-bytes 4..21/y72..177")),
        "host_has_no_r11_ball_contract": not any(token in "\n".join(host.values()) for token in (
            "A0..A8..A0", "full 1224-byte", "x-bytes 3..19/y64..135", "24x24实心球")),
        "supervisor_canonical_chinese_prompt": '@("通过","失败")' in host["supervisor"] and "三表情验收" in host["supervisor"],
        "checkonly_zero_contract": all(token in host["launcher"] for token in (
            "write_counter_sum", "programmer_calls", "serial_open_count", "reset_count", "refresh_count",
            "popup_count", "retry_count", "READY_NO_HARDWARE_CONTACT")),
    })

    oracle_run = subprocess.run(["python", str(ORACLE)], cwd=ROOT, capture_output=True, text=True, check=False)
    parser_run = subprocess.run(["python", str(PARSER), "--self-test"], cwd=ROOT, capture_output=True, text=True, check=False)
    checks["oracle_pass"] = oracle_run.returncode == 0
    checks["parser_selftest_pass"] = parser_run.returncode == 0
    oracle_artifact = json.loads(ORACLE_OUT.read_text(encoding="utf-8")) if ORACLE_OUT.is_file() else {}
    parser_result = json.loads(parser_run.stdout) if parser_run.returncode == 0 else {}
    checks["oracle_proves_header_and_pixels"] = (
        oracle_artifact.get("status") == "PASS" and
        oracle_artifact.get("asset_header_generation", {}).get("two_independent_results_identical") is True and
        oracle_artifact.get("asset_header_generation", {}).get("current_header_matches_generated") is True and
        oracle_artifact.get("pixel_oracle", {}).get("source_to_logical_pixel_difference") == 0 and
        [item["changed_pixels"] for item in oracle_artifact.get("transitions", [])[:4]] == [765, 846, 846, 765]
    )
    checks["negative_fixtures_actually_rejected"] = (
        parser_result.get("negative_cases_rejected") is True and
        all(oracle_artifact.get("negative_fixtures", {}).values())
    )
    setup_body = between(source, "static bool ssd1681_r12_setup_corridor_window", "static bool ssd1681_r12_reset_corridor_counters")
    counter_body = between(source, "static bool ssd1681_r12_reset_corridor_counters", "#endif\n\nstatic bool ssd1681_native_two_pass_activation")
    r3_negative_fixtures: dict[str, bool] = {}
    expect_source_reject("missing_counter", source.replace(
        counter_body, counter_body.replace("ssd1681_command_data(0x4Fu, y_counter, sizeof(y_counter))", "true"), 1),
        r3_negative_fixtures)
    expect_source_reject("duplicate_setup", source.replace(
        "ok = ssd1681_r12_setup_corridor_window();",
        "ok = ssd1681_r12_setup_corridor_window();\n        ok = ssd1681_r12_setup_corridor_window();", 1),
        r3_negative_fixtures)
    expect_source_reject("movement_resends_window", source.replace(
        "ssd1681_r12_reset_corridor_counters() &&",
        "ssd1681_r12_reset_corridor_counters() && ssd1681_command_data(0x44u, NULL, 0u) &&", 1),
        r3_negative_fixtures)
    expect_source_reject("movement_resends_border", source.replace(
        "ssd1681_r12_reset_corridor_counters() &&",
        "ssd1681_r12_reset_corridor_counters() && ssd1681_command_data(0x3Cu, NULL, 0u) &&", 1),
        r3_negative_fixtures)
    expect_source_reject("setup_ram_write", source.replace(
        setup_body, setup_body.replace("return ssd1681_command_data(0x44u", "return ssd1681_command(0x24u) &&\n           ssd1681_command_data(0x44u"), 1),
        r3_negative_fixtures)
    expect_source_reject("setup_refresh", source.replace(
        setup_body, setup_body.replace("return ssd1681_command_data(0x44u", "return ssd1681_command(0x20u) &&\n           ssd1681_command_data(0x44u"), 1),
        r3_negative_fixtures)
    checks["r3_negative_fixtures_rejected"] = all(r3_negative_fixtures.values())
    errors = [name for name, passed in checks.items() if not passed]
    hash_paths = [SOURCE, HEADER, ASSETS, MAKE, GENERATOR, ORACLE, PARSER, *tools.values(), WORK_PACKAGE, PROTECTED]
    result = {
        "schema_id": "companion.wb55.ssd1681.r12_v22_calm_curious_warm_sampler.static.v4",
        "status": "PASS" if not errors else "FAIL", "candidate": parser.CANDIDATE,
        "cadence_gate": {"accepted_ms": 480, "rejected_ms": 481, "target_ms": 450},
        "baseline": {"window": "0-24,0-199", "bytes": 5000, "reset": 1, "control": "0xFF"},
        "movement": {"window": "4-21,72-177", "bytes": 1908, "reset": 0, "control": "0xCF"},
        "future_physical_authorization_requirement_id": "COMP-REQ-376",
        "r3_negative_fixtures": r3_negative_fixtures,
        "checks": checks, "artifact_sha256": {str(path.relative_to(ROOT)): sha(path) for path in hash_paths},
        "errors": errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
