#!/usr/bin/env python3
"""Verify the default-off Good Display disjoint no-union settle partial diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_vendor_partial_disjoint_no_union_settle_diagnostic.ps1"
TRACE_VERIFIER = ROOT / "tools/verify_wb55_vendor_partial_disjoint_no_union_settle_log.py"
SERIAL_CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
HARDWARE_PREREQUISITE_VERIFIER = ROOT / (
    "tools/verify_wb55_vendor_partial_disjoint_no_union_settle_hardware_prerequisite.py"
)
HARDWARE_PREREQUISITE = ROOT / (
    "docs/validation/"
    "companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-r2-hardware-prerequisite-20260721.json"
)
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
STUDY = ROOT / "docs/validation/companion-gdey0154d67-t03-yesterday-method-study-20260721.json"
R6_OPERATOR = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-current-stage-operator-r6-20260721.json"
HISTORICAL_TRACE = ROOT / ".cache/validation/wb55-vendor-partial-slow-motion-current-room-20260720/capture/nucleo-serial-raw.log"
HISTORICAL_CANDIDATES = {
    "old_new_0x26": (
        ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-old-new-ram-static-20260720.json",
        "PASS_STATIC_OWNER_AUTHORIZED_VENDOR_PARTIAL_OLD_NEW_RAM_AB",
    ),
    "current_union_old_settle": (
        ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-current-union-old-settle-runtime-20260720.json",
        "PASS_MACHINE_CURRENT_UNION_OLD_SETTLE_TRACE",
    ),
    "removed_black_repair": (
        ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-removed-black-repair-current-union-operator-20260720.json",
        "NO_GO_OPERATOR_VISIBLE_ENLARGED_GAP",
    ),
    "draw_final": (
        ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-draw-final-operator-20260720.json",
        "NO_GO_OPERATOR_VISIBLE_RESIDUE_DRAW_FINAL",
    ),
    "slow_motion": (
        ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-slow-motion-residue-triage-20260720.json",
        "NO_GO_PHYSICAL_CONTINUOUS_PARTIAL_RESIDUE",
    ),
    "accepted_no_union_baseline": (
        ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-no-union-settle-operator-20260720.json",
        "PASS_OPERATOR_ACCEPTED_PRODUCTION_OFF_NO_UNION_SETTLE_BASELINE",
    ),
}
ELF = ROOT / (
    "cubeide/Companion_Nucleo_WB55RG_Bringup/"
    "build_vendor_partial_disjoint_no_union_settle_diagnostic/"
    "Companion_Nucleo_WB55RG_VendorPartialDisjointNoUnionSettleDiagnostic.elf"
)
OBSERVER_ELF = ROOT / (
    "cubeide/Companion_Nucleo_WB55RG_Bringup/"
    "build_vendor_partial_disjoint_no_union_settle_operator_loop_diagnostic/"
    "Companion_Nucleo_WB55RG_VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic.elf"
)
NORMAL_HEX = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.hex"
NORMAL_ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.elf"
DEFAULT_OUTPUT = ROOT / (
    "docs/validation/"
    "companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-static-20260721.json"
)
SCHEMA_ID = "companion.wb55.gdey0154d67_t03.vendor_partial_disjoint_no_union_settle_static.v1"
WIDTH = 200
HEIGHT = 200
BYTES_PER_ROW = WIDTH // 8
DISJOINT_PROBE_RADIUS = 12
STEPS_PER_SEGMENT = 8
POSITION_COUNT = 5 * STEPS_PER_SEGMENT
ANCHOR_X = (100, 100, 142, 100, 58)
ANCHOR_Y = (100, 58, 100, 142, 100)
VENDOR_SHA256 = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
NORMAL_HEX_SHA256 = "E1997F29DCB8735899B4BC0B9012CF75025F3CA8D21250485BCC21E4C4691B46"


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


def branch_after(source: str, marker: str, end_marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        return ""
    end = source.find(end_marker, start)
    return source[start:] if end < 0 else source[start:end]


def probe_center(phase: int) -> tuple[int, int]:
    """Mirror frame_disjoint_component_probe exactly (C integer division truncates toward zero)."""
    segment = phase // STEPS_PER_SEGMENT
    fraction = phase % STEPS_PER_SEGMENT
    next_segment = (segment + 1) % 5
    start_x, start_y = ANCHOR_X[segment], ANCHOR_Y[segment]
    end_x, end_y = ANCHOR_X[next_segment], ANCHOR_Y[next_segment]
    denominator = STEPS_PER_SEGMENT
    center_x = start_x + int(((end_x - start_x) * fraction + denominator // 2) / denominator)
    center_y = start_y + int(((end_y - start_y) * fraction + denominator // 2) / denominator)
    return center_x, center_y


def draw_probe(phase: int) -> bytearray:
    frame = bytearray([0xFF]) * (BYTES_PER_ROW * HEIGHT)
    center_x, center_y = probe_center(phase)
    for y in range(center_y - DISJOINT_PROBE_RADIUS, center_y + DISJOINT_PROBE_RADIUS + 1):
        for x in range(center_x - DISJOINT_PROBE_RADIUS, center_x + DISJOINT_PROBE_RADIUS + 1):
            if (x - center_x) ** 2 + (y - center_y) ** 2 <= DISJOINT_PROBE_RADIUS ** 2:
                index = y * BYTES_PER_ROW + x // 8
                frame[index] &= ~(0x80 >> (x & 7))
    return frame


def windows_from_difference(previous: bytearray, current: bytearray) -> list[tuple[int, int, int, int]]:
    regions: list[tuple[int, int, int, int]] = []
    previous_column_changed = False
    for x_byte in range(BYTES_PER_ROW):
        changed_rows = [
            y
            for y in range(HEIGHT)
            if previous[y * BYTES_PER_ROW + x_byte] != current[y * BYTES_PER_ROW + x_byte]
        ]
        if not changed_rows:
            previous_column_changed = False
            continue
        if not previous_column_changed:
            if len(regions) >= 5:
                changed = [
                    (x, y)
                    for x in range(BYTES_PER_ROW)
                    for y in range(HEIGHT)
                    if previous[y * BYTES_PER_ROW + x] != current[y * BYTES_PER_ROW + x]
                ]
                return [(min(x for x, _ in changed), max(x for x, _ in changed),
                         min(y for _, y in changed), max(y for _, y in changed))]
            regions.append((x_byte, x_byte, min(changed_rows), max(changed_rows)))
        else:
            start_x, _, start_y, end_y = regions[-1]
            regions[-1] = (start_x, x_byte, min(start_y, min(changed_rows)), max(end_y, max(changed_rows)))
        previous_column_changed = True
    return regions


def window_bytes(region: tuple[int, int, int, int]) -> int:
    start_x, end_x, start_y, end_y = region
    return (end_x - start_x + 1) * (end_y - start_y + 1)


def synthetic_probe_evidence() -> dict[str, Any]:
    previous = draw_probe(0)
    current = draw_probe(16)
    regions = windows_from_difference(previous, current)
    changed = [
        (x, y)
        for x in range(BYTES_PER_ROW)
        for y in range(HEIGHT)
        if previous[y * BYTES_PER_ROW + x] != current[y * BYTES_PER_ROW + x]
    ]
    union = (min(x for x, _ in changed), max(x for x, _ in changed),
             min(y for _, y in changed), max(y for _, y in changed))
    total = sum(window_bytes(region) for region in regions)
    return {
        "probe_radius_px": DISJOINT_PROBE_RADIUS,
        "previous_phase": 0,
        "current_phase": 16,
        "regions": [
            {"x_byte": [region[0], region[1]], "y": [region[2], region[3]], "bytes": window_bytes(region)}
            for region in regions
        ],
        "region_count": len(regions),
        "total_bytes": total,
        "union_bytes": window_bytes(union),
        "strictly_smaller_than_union": total < window_bytes(union),
    }


def synthetic_five_anchor_orbit_evidence() -> dict[str, Any]:
    centers = [probe_center(phase) for phase in range(POSITION_COUNT)]
    return {
        "probe_radius_px": DISJOINT_PROBE_RADIUS,
        "phase_count": POSITION_COUNT,
        "steps_per_segment": STEPS_PER_SEGMENT,
        "anchors": [[x, y] for x, y in zip(ANCHOR_X, ANCHOR_Y)],
        "centers": [[x, y] for x, y in centers],
        "min_center_x": min(x for x, _ in centers),
        "max_center_x": max(x for x, _ in centers),
        "min_center_y": min(y for _, y in centers),
        "max_center_y": max(y for _, y in centers),
        "all_centers_on_panel": all(0 <= x < WIDTH and 0 <= y < HEIGHT for x, y in centers),
    }


def synthetic_identical_frame_evidence() -> dict[str, Any]:
    previous = draw_probe(0)
    current = draw_probe(0)
    regions = windows_from_difference(previous, current)
    return {
        "previous_phase": 0,
        "current_phase": 0,
        "region_count": len(regions),
        "total_bytes": sum(window_bytes(region) for region in regions),
        "expected_controller_activations": 0,
    }


def evaluate() -> dict[str, Any]:
    required = (
        VENDOR,
        DRIVER,
        MAKEFILE,
        BUILD,
        RUNNER,
        TRACE_VERIFIER,
        SERIAL_CAPTURE,
        HARDWARE_PREREQUISITE_VERIFIER,
        HARDWARE_PREREQUISITE,
        REQUIREMENTS,
        STUDY,
        R6_OPERATOR,
        HISTORICAL_TRACE,
        *(path for path, _ in HISTORICAL_CANDIDATES.values()),
        ELF,
        OBSERVER_ELF,
        NORMAL_HEX,
        NORMAL_ELF,
    )
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {
            "schema_id": SCHEMA_ID,
            "status": "NO_GO_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_INPUT_MISSING",
            "checks": {},
            "failures": missing,
        }

    vendor = VENDOR.read_text(encoding="utf-8-sig", errors="replace")
    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
    runner = RUNNER.read_text(encoding="utf-8-sig", errors="replace")
    serial_capture = SERIAL_CAPTURE.read_text(encoding="utf-8-sig", errors="replace")
    requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    study = json.loads(STUDY.read_text(encoding="utf-8-sig"))
    r6_operator = json.loads(R6_OPERATOR.read_text(encoding="utf-8-sig"))
    historical = HISTORICAL_TRACE.read_text(encoding="utf-8-sig", errors="replace")
    historical_candidates = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, (path, _) in HISTORICAL_CANDIDATES.items()
    }
    supplier_multi = source_function(vendor)
    diagnostic_branch = branch_after(
        driver,
        "if (vendor_partial_disjoint_no_union_settle) {",
        "#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC",
    )
    synthetic = synthetic_probe_evidence()
    identical = synthetic_identical_frame_evidence()
    orbit = synthetic_five_anchor_orbit_evidence()
    historical_count_one = bool(re.search(r"vendor_partial_source multi_region count=1", historical))
    identical_skip_offset = driver.find("if (partial && !window.changed) {")
    first_controller_command_after_skip = driver.find("ssd1681_gpio_init();", identical_skip_offset)

    checks = {
        "owner_steering_records_comp_req_243_two_pass_candidate_only": all(
            token in requirements
            for token in (
                "COMP-REQ-243",
                "vendor_partial_disjoint_no_union_settle",
                "pass 1 keeps the accepted COMP-REQ-236 erase structure",
                "pass 2 replaces only the union window",
                "no LUT/waveform/controller-register/control",
            )
        ),
        "yesterday_study_and_r6_residue_steering_are_preserved": (
            study.get("status") == "STUDY_COMPLETE_TWO_PASS_ERASE_FIRST_IS_ACCEPTED_METHOD"
            and study.get("implication", {}).get("new_candidate")
            == "vendor_partial_disjoint_no_union_settle"
            and digest(STUDY) == "A88B022423E6ADFBA83B1362BAACB0C6CAC3A970DAEC93EB521E63EEB0030C2D"
            and r6_operator.get("status") == "PASS_OPERATOR_WITH_RESIDUE_STEERING_PRODUCTION_OFF"
            and "残影" in r6_operator.get("operator_review", {}).get("note", "")
            and digest(R6_OPERATOR) == "13CF51F221110829949075864973DF769AAF1C8222B73B482124BF14FD55D9C3"
        ),
        "supplier_source_hash_is_exact": digest(VENDOR) == VENDOR_SHA256,
        "supplier_function_is_five_current_0x24_stages_then_one_partial_activation": (
            supplier_multi.count("Epaper_Write_Command(0x24)") == 5
            and supplier_multi.count("EPD_Part_Update();") == 1
            and supplier_multi.count("Epaper_Write_Command(0x26)") == 0
        ),
        "historical_ball_trace_exercised_only_one_region": historical_count_one,
        "new_probe_proves_two_disjoint_regions_and_strict_payload_reduction": (
            synthetic["region_count"] == 2 and synthetic["strictly_smaller_than_union"]
        ),
        "new_probe_is_single_12px_ball_on_42px_five_anchor_orbit": (
            orbit["probe_radius_px"] == DISJOINT_PROBE_RADIUS
            and orbit["all_centers_on_panel"]
            and orbit["min_center_x"] == 58
            and orbit["max_center_x"] == 142
            and orbit["min_center_y"] == 58
            and orbit["max_center_y"] == 142
        ),
        "identical_frame_synthetic_probe_has_zero_regions_zero_payload_and_zero_activation": (
            identical["region_count"] == 0
            and identical["total_bytes"] == 0
            and identical["expected_controller_activations"] == 0
        ),
        "target_is_default_off_binary_guarded_and_pattern_isolated": all(
            token in driver
            for token in (
                "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC 0",
                "SSD1681 vendor partial disjoint no-union settle diagnostic must be 0 or 1",
                "SSD1681 vendor partial disjoint no-union settle diagnostic requires the source partial operator loop",
                "SSD1681 vendor partial disjoint no-union settle diagnostic excludes every historical partial and LUT diagnostic",
                "SSD1681 vendor partial disjoint no-union settle diagnostic requires pattern 6",
                "SSD1681 pattern 6 is reserved for the vendor partial disjoint current-stage diagnostic",
            )
        ),
        "target_compile_time_excludes_every_historical_partial_or_lut_candidate": all(
            token in driver
            for token in (
                "#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC != 0 &&",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_SLOW_MOTION_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_OLD_NEW_RAM_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DRAW_FINAL_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_NO_UNION_SETTLE_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_CURRENT_UNION_OLD_SETTLE_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_REMOVED_BLACK_REPAIR_CURRENT_UNION_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_T03_FAST_STATE_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_VENDOR_1S_LUT_OPERATOR_LOOP_DIAGNOSTIC != 0",
                "COMPANION_EPAPER_SSD1681_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC != 0",
                '#error "SSD1681 vendor partial disjoint no-union settle diagnostic excludes every historical partial and LUT diagnostic"',
            )
        ),
        "target_derives_generic_bounded_byte_aligned_difference_regions": all(
            token in driver
            for token in (
                "static uint8_t ssd1681_windows_from_difference",
                "#define SSD1681_DIFFERENTIAL_MULTI_REGION_MAX 5u",
                "if (s_frame[index] == s_previous_frame[index])",
                "region_count >= SSD1681_DIFFERENTIAL_MULTI_REGION_MAX",
                "settle_region_count = ssd1681_windows_from_difference(settle_regions);",
            )
        ),
        "target_uses_owner_authorized_12px_diagnostic_probe_only": all(
            token in driver
            for token in (
                "#define SSD1681_VENDOR_PARTIAL_DISJOINT_PROBE_RADIUS 12u",
                "static void frame_disjoint_component_probe(uint8_t phase)",
                "static const int32_t k_anchor_x[5] = {100, 100, 142, 100, 58};",
                "static const int32_t k_anchor_y[5] = {100, 58, 100, 142, 100};",
                "const int32_t radius = (int32_t)SSD1681_VENDOR_PARTIAL_DISJOINT_PROBE_RADIUS;",
            )
        ) and "expression_rig" not in diagnostic_branch
        and "comp_epaper_ball_motion_diagnostic_" not in diagnostic_branch,
        "target_uses_only_current_0x24_for_erase_and_each_draw_region": all(
            token in diagnostic_branch
            for token in (
                "ssd1681_window_from_previous_black_pixels()",
                "ssd1681_set_window_vendor_partial_source(&old_window, true)",
                "ssd1681_write_plane_region(0x24u, s_frame, &old_window)",
                "ssd1681_set_window_vendor_partial_source(&settle_regions[index]",
                "index == 0u",
                "&settle_regions[index]);",
                "no_0x26=1",
                "no_c7=1",
                "no_full_write=1",
            )
        ) and "0x26u" not in diagnostic_branch and "0xC7u" not in diagnostic_branch,
        "target_has_exactly_two_ordered_source_completions_and_no_common_third": (
            diagnostic_branch.count("ssd1681_reset();") == 2
            and diagnostic_branch.count("ssd1681_refresh_display(") == 2
            and diagnostic_branch.find("pass=erase") < diagnostic_branch.find("pass=draw")
            and all(token in driver
            for token in (
                "good_display_vendor_partial_disjoint_no_union_settle",
                "one_control=0xFF one_activation=0x20",
                "uint8_t update_control = vendor_1s_lut_diagnostic",
                "? 0xFFu",
                "ssd1681_command(0x20u)",
                "ssd1681_wait_refresh_complete",
                "!vendor_partial_disjoint_no_union_settle)",
            ))
        ),
        "candidate_bypasses_the_common_union_window_setup": (
            "vendor_partial_disjoint_no_union_settle && partial\n                                ? true" in driver
        ),
        "candidate_uses_the_full_50_frame_phase_sequence": (
            "COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC" in driver
            and ".menu_page = ssd1681_disjoint_component_probe_phase(cycle)," in driver
        ),
        "target_skips_identical_partial_frame_before_controller_commands": all(
            token in driver
            for token in (
                "if (partial && !window.changed) {",
                "differential_skip identical_frame",
                "out_report->transferred_bytes = 0u;",
                "return COMP_EPAPER_PANEL_RESULT_OK;",
            )
        ) and identical_skip_offset >= 0 and first_controller_command_after_skip > identical_skip_offset,
        "diagnostic_probe_is_not_product_expression_binding": all(
            token in driver
            for token in (
                "static void frame_disjoint_component_probe(uint8_t phase)",
                "frame_disjoint_component_probe(request == NULL ? 0u : request->menu_page);",
            )
        ) and "expression_rig" not in diagnostic_branch,
        "makefile_and_build_script_are_explicit_and_isolated": all(
            token in makefile
            for token in (
                "ifeq ($(EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC),1)",
                "-DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC=1",
            )
        ) and all(
            token in build
            for token in (
                "[switch]$EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic",
                "[switch]$EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic",
                "Vendor partial disjoint no-union settle diagnostic is a fixed isolated image",
                "EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC=1",
                "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=6",
                "$disjointNoUnionRepeats = if ($disjointNoUnionObserver) { 360 } else { 50 }",
                '"EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$disjointNoUnionRepeats"',
                '"BUILD_DIR=$disjointNoUnionBuildDir"',
                '"TARGET=$disjointNoUnionTarget"',
                "build_vendor_partial_disjoint_no_union_settle_diagnostic",
                "build_vendor_partial_disjoint_no_union_settle_operator_loop_diagnostic",
            )
        ),
        "runner_is_fail_closed_and_captures_all_48_partial_steps": all(
            token in runner
            for token in (
                "[switch]$CheckOnly",
                "[switch]$Execute",
                "[switch]$ReusePassedMachineTrace",
                "-ReusePassedMachineTrace is an execution-only optimization.",
                "Cannot reuse a machine trace because the captured raw log is missing.",
                "function Assert-NoForeignOperatorPrompt",
                "Another canonical operator review window is already open",
                "verify_wb55_vendor_partial_disjoint_no_union_settle_hardware_prerequisite.py",
                "PASS_R2_HARDWARE_PREREQUISITE_DISJOINT_NO_UNION_SETTLE_UNPROVEN",
                "[int]$CaptureSeconds = 90",
                "frame_count = 50; partial_steps = 48; identical_frame_steps = 1",
                "exactly_two_source_completions_per_changed_partial = $true",
                'completion_order = "erase_old_then_draw_disjoint_current"',
                "Machine trace gate failed; operator review is forbidden.",
                "Review observer flash failed.",
                "五锚点轨道连续移动",
                "领先边短暂缺口不比昨晚更大或更久",
                "-WorkflowLockHeld",
                "normal_firmware_restore_required = $true",
                "aiw_operator_prompt_v1",
            )
        ),
        "serial_capture_retries_only_transient_vcp_open_races_and_records_attempts": all(
            token in serial_capture
            for token in (
                "[switch] $SelfTestSerialOpenRetry",
                "[int] $SerialOpenRetrySeconds = 15",
                "function Open-SerialWithRetry",
                "catch [System.IO.IOException]",
                "catch [System.UnauthorizedAccessException]",
                "serial_open_attempts = $script:serialOpenAttempts",
                "Open-SerialWithRetry -PortName $resolved.port -RetrySeconds $SerialOpenRetrySeconds",
                "selftest-serial-open-retry",
            )
        ),
        "diagnostic_elf_exists": ELF.is_file(),
        "observer_elf_exists": OBSERVER_ELF.is_file(),
        "diagnostic_and_observer_images_contain_only_the_new_profile": (
            b"good_display_vendor_partial_disjoint_no_union_settle" in ELF.read_bytes()
            and b"good_display_vendor_partial_disjoint_no_union_settle" in OBSERVER_ELF.read_bytes()
        ),
        "normal_hex_is_the_accepted_restore_image": digest(NORMAL_HEX) == NORMAL_HEX_SHA256,
        "normal_firmware_omits_the_default_off_diagnostic_profile": (
            b"good_display_vendor_partial_disjoint_no_union_settle" not in NORMAL_ELF.read_bytes()
            and b"disjoint_component_probe" not in NORMAL_ELF.read_bytes()
        ),
        "historical_candidate_artifacts_are_explicitly_preserved_and_not_reclassified": all(
            historical_candidates[name].get("status") == expected_status
            for name, (_, expected_status) in HISTORICAL_CANDIDATES.items()
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_STATIC_SOURCE_EXACT_DISJOINT_NO_UNION_SETTLE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_DISJOINT_NO_UNION_SETTLE_CONTRACT_INCOMPLETE",
        "claim_scope": "machine-only, production-off source-topology diagnostic; no residue, temperature, production, or OLED-like continuity claim",
        "checks": checks,
        "failures": failures,
        "source": {
            "vendor_epaper_c": {"path": str(VENDOR), "sha256": digest(VENDOR)},
            "target_driver": {"path": rel(DRIVER), "sha256": digest(DRIVER)},
            "makefile": {"path": rel(MAKEFILE), "sha256": digest(MAKEFILE)},
            "build_script": {"path": rel(BUILD), "sha256": digest(BUILD)},
            "runner": {"path": rel(RUNNER), "sha256": digest(RUNNER)},
            "trace_verifier": {"path": rel(TRACE_VERIFIER), "sha256": digest(TRACE_VERIFIER)},
            "serial_capture": {"path": rel(SERIAL_CAPTURE), "sha256": digest(SERIAL_CAPTURE)},
            "hardware_prerequisite_verifier": {
                "path": rel(HARDWARE_PREREQUISITE_VERIFIER),
                "sha256": digest(HARDWARE_PREREQUISITE_VERIFIER),
            },
            "hardware_prerequisite": {
                "path": rel(HARDWARE_PREREQUISITE),
                "sha256": digest(HARDWARE_PREREQUISITE),
            },
            "yesterday_method_study": {
                "path": rel(STUDY),
                "sha256": digest(STUDY),
                "status": study.get("status"),
            },
            "r6_residue_steering": {
                "path": rel(R6_OPERATOR),
                "sha256": digest(R6_OPERATOR),
                "status": r6_operator.get("status"),
            },
            "diagnostic_elf": {"path": rel(ELF), "sha256": digest(ELF)},
            "observer_elf": {"path": rel(OBSERVER_ELF), "sha256": digest(OBSERVER_ELF)},
            "normal_hex": {"path": rel(NORMAL_HEX), "sha256": digest(NORMAL_HEX)},
            "normal_elf": {"path": rel(NORMAL_ELF), "sha256": digest(NORMAL_ELF)},
            "historical_single_region_trace": {"path": rel(HISTORICAL_TRACE), "sha256": digest(HISTORICAL_TRACE)},
            "historical_candidates": {
                name: {
                    "path": rel(path),
                    "sha256": digest(path),
                    "recorded_status": historical_candidates[name].get("status"),
                }
                for name, (path, _) in HISTORICAL_CANDIDATES.items()
            },
        },
        "source_diff": {
            "supplier": "EPD_Dis_Part_myself resets once, locks border once, writes five current 0x24 regions, then calls EPD_Part_Update once.",
            "historical_observation": "The prior slow-motion physical trace used the source multi-region path but recorded count=1 for every ball frame, so it did not observe disjoint staging.",
            "candidate": "The new default-off probe first erases the previous black bounding box with its own source completion, then stages generic previous/current differences across one to five disjoint current-0x24 regions and performs exactly one second source completion.",
            "physical_probe": "After the r5 human observation failed because the 1 px step / 4 px excursion probe was not visibly moving, the owner (COMP-REQ-242 addendum 2026-07-21) authorized reusing only the five-anchor geometry: a single fixed 12 px-radius diagnostic ball on the 42 px center/up/right/down/left orbit with eight interpolation steps per segment. This is probe geometry only, not a product-expression binding or a transport/waveform change.",
            "not_claimed": "The supplier function uses one fixed PART_COLUMN/PART_LINE size for all five calls; the target uses bounded actual difference rectangles for integration. This proves command/topology ancestry, not a panel-qualified residue waveform.",
        },
        "historical_exclusions": {
            "old_new_0x26": "Preserved as an A/B static artifact; the candidate has no 0x26 and is compile-time incompatible with that candidate.",
            "current_union_old_settle": "Preserved as machine evidence only; the candidate stages disjoint current regions instead of a union rectangle and is compile-time incompatible with it.",
            "removed_black_repair": "Operator NO_GO for enlarged gap; the candidate writes no synthetic black repair and is compile-time incompatible with it.",
            "draw_final": "Operator NO_GO for visible residue; the candidate does not use draw-final and is compile-time incompatible with it.",
            "slow_motion": "Physical NO_GO for continuous partial residue; it is retained as a negative result, not reused as candidate success evidence.",
            "accepted_no_union_baseline": "Accepted production-off regression baseline retained; the candidate does not replace or bind it to production expression rendering.",
        },
        "synthetic_disjoint_probe": synthetic,
        "synthetic_identical_frame_probe": identical,
        "synthetic_five_anchor_orbit": orbit,
        "physical_gate": {
            "permitted": False,
            "reason": "Static source-direction evidence only. A fail-closed runner, current-goal audit, prerequisite checks, machine trace and canonical Chinese operator review are still required before any flash.",
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    report = evaluate()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['status']}: {rel(output)}")
    return 0 if report["status"] == "PASS_STATIC_SOURCE_EXACT_DISJOINT_NO_UNION_SETTLE_DEFAULT_OFF" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
