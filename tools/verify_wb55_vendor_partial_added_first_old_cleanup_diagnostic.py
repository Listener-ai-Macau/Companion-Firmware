#!/usr/bin/env python3
"""Verify the default-off pure-added-first/old-cleanup SSD1681 diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_vendor_partial_added_first_old_cleanup_diagnostic.ps1"
TRACE = ROOT / "tools/verify_wb55_vendor_partial_added_first_old_cleanup_log.py"
PREREQ = ROOT / "tools/verify_wb55_vendor_partial_added_first_old_cleanup_hardware_prerequisite.py"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
RESEARCH = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-research-source-hash-20260721.json"
PRIOR_OPERATOR = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-operator-r1-20260721.json"
PRIOR_AUDIT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-completion-audit-20260721.json"
SUPPLIER = pathlib.Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
BUILD_ROOT = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup"
DIAG_ELF = BUILD_ROOT / "build_vendor_partial_added_first_old_cleanup_diagnostic/Companion_Nucleo_WB55RG_VendorPartialAddedFirstOldCleanupDiagnostic.elf"
OBSERVER_ELF = BUILD_ROOT / "build_vendor_partial_added_first_old_cleanup_operator_loop_diagnostic/Companion_Nucleo_WB55RG_VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic.elf"
NORMAL_HEX = BUILD_ROOT / "build/Companion_Nucleo_WB55RG_Bringup.hex"
NORMAL_ELF = BUILD_ROOT / "build/Companion_Nucleo_WB55RG_Bringup.elf"
OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-partial-added-first-old-cleanup-static-20260721.json"

SOURCE_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
NORMAL_SHA = "E1997F29DCB8735899B4BC0B9012CF75025F3CA8D21250485BCC21E4C4691B46"
PRIOR_OPERATOR_SHA = "67E43FBBD7546EB99E4CE8B06EE84141D0B0F4419E77C7ED1AF7D9C38D7D9C00"
PRIOR_AUDIT_SHA = "42D611AB16D10403B820D9DE6E25B8B24A6D0BD4105AE12222BB1517BF46058F"
STATUS = "PASS_STATIC_SOURCE_EXACT_ADDED_FIRST_OLD_CLEANUP_DEFAULT_OFF"
PROFILE = b"good_display_vendor_partial_added_first_old_cleanup"
WIDTH = HEIGHT = 200
ROW_BYTES = 25
RADIUS = 12
STEPS = 8
ANCHORS = ((100, 100), (100, 58), (142, 100), (100, 142), (58, 100))


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} must be an object")
    return value


def center(phase: int) -> tuple[int, int]:
    segment, fraction = divmod(phase, STEPS)
    start = ANCHORS[segment]
    end = ANCHORS[(segment + 1) % len(ANCHORS)]
    # All deltas are non-negative for the half-open segments that use rounding.
    return (
        start[0] + int(((end[0] - start[0]) * fraction + STEPS // 2) / STEPS),
        start[1] + int(((end[1] - start[1]) * fraction + STEPS // 2) / STEPS),
    )


def draw(phase: int) -> bytearray:
    frame = bytearray([0xFF]) * (ROW_BYTES * HEIGHT)
    cx, cy = center(phase)
    for y in range(cy - RADIUS, cy + RADIUS + 1):
        for x in range(cx - RADIUS, cx + RADIUS + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= RADIUS ** 2:
                frame[y * ROW_BYTES + x // 8] &= ~(0x80 >> (x & 7))
    return frame


def phase(cycle: int) -> int:
    previous_phase = cycle - 2
    return (previous_phase if cycle == 50 else cycle - 1) % 40


def pure_added_runs(previous: bytearray, current: bytearray) -> tuple[list[tuple[int, int, int]], int, int]:
    runs: list[tuple[int, int, int]] = []
    eligible = mixed = 0
    for x_byte in range(ROW_BYTES):
        start: int | None = None
        for y in range(HEIGHT + 1):
            is_eligible = False
            if y < HEIGHT:
                old = previous[y * ROW_BYTES + x_byte]
                new = current[y * ROW_BYTES + x_byte]
                added = old & (~new & 0xFF)
                removed = (~old & 0xFF) & new
                is_eligible = added != 0 and removed == 0
                eligible += int(is_eligible)
                mixed += int(added != 0 and removed != 0)
            if is_eligible and start is None:
                start = y
            elif not is_eligible and start is not None:
                runs.append((x_byte, start, y - 1))
                start = None
    return runs, eligible, mixed


def synthetic() -> dict[str, Any]:
    frames = [draw(phase(cycle)) for cycle in range(1, 51)]
    rows: list[dict[str, Any]] = []
    for index in range(1, 49):
        runs, eligible, mixed = pure_added_runs(frames[index - 1], frames[index])
        assert all(x == x and start <= end for x, start, end in runs)
        rows.append({"cycle": index + 1, "regions": len(runs), "eligible_bytes": eligible, "mixed_bytes": mixed})
    identical_runs, identical_eligible, identical_mixed = pure_added_runs(frames[48], frames[49])
    return {
        "changed_frames": len(rows),
        "region_count_min": min(row["regions"] for row in rows),
        "region_count_max": max(row["regions"] for row in rows),
        "eligible_bytes_min": min(row["eligible_bytes"] for row in rows),
        "eligible_bytes_max": max(row["eligible_bytes"] for row in rows),
        "mixed_bytes_min": min(row["mixed_bytes"] for row in rows),
        "mixed_bytes_max": max(row["mixed_bytes"] for row in rows),
        "empty_changed_frames": sum(row["regions"] == 0 for row in rows),
        "over_limit_frames": sum(row["regions"] > 8 for row in rows),
        "identical": {"regions": len(identical_runs), "eligible_bytes": identical_eligible, "mixed_bytes": identical_mixed},
        "frames": rows,
    }


def evaluate() -> dict[str, Any]:
    required = (DRIVER, MAKEFILE, BUILD, RUNNER, TRACE, PREREQ, REGISTRY, RESEARCH,
                PRIOR_OPERATOR, PRIOR_AUDIT, SUPPLIER, DIAG_ELF, OBSERVER_ELF, NORMAL_HEX, NORMAL_ELF)
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {"schema_id": "companion.wb55.gdey0154d67_t03.vendor_partial_added_first_old_cleanup_static.v1",
                "status": "NO_GO_STATIC_INPUT_MISSING", "checks": {}, "failures": missing}

    driver = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    makefile = MAKEFILE.read_text(encoding="utf-8-sig", errors="replace")
    build = BUILD.read_text(encoding="utf-8-sig", errors="replace")
    runner = RUNNER.read_text(encoding="utf-8-sig", errors="replace")
    registry = REGISTRY.read_text(encoding="utf-8-sig", errors="replace")
    research = load(RESEARCH)
    prior_operator = load(PRIOR_OPERATOR)
    prior_audit = load(PRIOR_AUDIT)
    synth = synthetic()
    start = driver.find("if (vendor_partial_added_first_old_cleanup) {")
    end = driver.find("#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC", start)
    branch = driver[start:end] if start >= 0 and end > start else ""
    helper_start = driver.find("static uint8_t ssd1681_windows_from_pure_added_black")
    helper_end = driver.find("#endif", helper_start)
    helper = driver[helper_start:helper_end] if helper_start >= 0 else ""

    checks = {
        "registry_records_exact_comp_req_255_contract": all(token in registry for token in (
            "COMP-REQ-255", "vendor_partial_added_first_old_cleanup", "maximum of eight regions",
            "empty or over-limit region set fails closed", "no `0x21`, `0x37`, `0x2D` read")),
        "research_authorizes_only_this_candidate": research.get("status") == "PASS_RESEARCH_AUTHORIZES_ONE_ADDED_FIRST_OLD_CLEANUP_CANDIDATE"
            and research.get("owner_steering", {}).get("only_new_candidate") is True,
        "supplier_and_prior_evidence_hashes_are_exact": digest(SUPPLIER) == SOURCE_SHA
            and digest(PRIOR_OPERATOR) == PRIOR_OPERATOR_SHA and digest(PRIOR_AUDIT) == PRIOR_AUDIT_SHA
            and prior_operator.get("status") == "NO_GO_OPERATOR_LEADING_EDGE_CUTOFF_DISJOINT_NO_UNION_SETTLE"
            and prior_audit.get("status") == "NO_GO_OPERATOR_LEADING_EDGE_CUTOFF_NORMAL_RESTORED",
        "synthetic_48_changed_frames_match_research": synth["changed_frames"] == 48
            and synth["region_count_min"] == 2 and synth["region_count_max"] == 6
            and synth["eligible_bytes_min"] == 28 and synth["eligible_bytes_max"] == 49
            and synth["mixed_bytes_min"] == 0 and synth["mixed_bytes_max"] == 4
            and synth["empty_changed_frames"] == 0 and synth["over_limit_frames"] == 0
            and synth["identical"] == {"regions": 0, "eligible_bytes": 0, "mixed_bytes": 0},
        "macro_is_default_off_binary_guarded_and_isolated": all(token in driver for token in (
            "#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_DIAGNOSTIC 0",
            "diagnostic must be 0 or 1", "diagnostic requires the source partial operator loop",
            "diagnostic excludes every historical partial and LUT diagnostic",
            "diagnostic requires pattern 6")),
        "helper_implements_exact_predicate_and_eight_run_fail_closed_limit": "#define SSD1681_PURE_ADDED_REGION_MAX 8u" in driver and all(token in helper for token in (
            "previous & (uint8_t)~current",
            "(uint8_t)~previous & current", "added_black != 0u && removed_black == 0u",
            "if (region_count >= SSD1681_PURE_ADDED_REGION_MAX)", "*over_limit = true;", "return 0u;")),
        "branch_has_added_then_cleanup_and_exactly_two_completions": branch.count("ssd1681_reset();") == 2
            and branch.count("ssd1681_refresh_display(") == 2
            and branch.find("pass=added") < branch.find("pass=cleanup")
            and "plan_valid = old_window.changed && added_region_count != 0u" in branch
            and "!added_over_limit" in branch and "if (added_refreshed)" in branch,
        "pass1_rechecks_predicate_and_writes_only_current_0x24": all(token in branch for token in (
            "predicate_verified = predicate_verified && added_black != 0u &&",
            "removed_black == 0u", "&added_regions[index], index == 0u",
            "0x24u", "s_frame", "predicate_verified=%u", "mixed_transition=0")),
        "pass2_uses_previous_black_bbox_with_current_0x24": all(token in branch for token in (
            "ssd1681_window_from_previous_black_pixels()", "&old_window, true",
            "ssd1681_write_plane_region(0x24u", "s_frame", "&old_window")),
        "branch_explicitly_forbids_fallback_union_and_unapproved_commands": all(token in branch for token in (
            "no_fallback=1", "no_union=1", "no_0x21=1", "no_0x37=1",
            "no_0x26=1", "no_c7=1", "no_full_write=1"))
            and all(token not in branch for token in ("0x21u", "0x26u", "0x2Du", "0x37u", "0xC7u", "LUT_DATA")),
        "common_union_setup_and_third_activation_are_bypassed": "vendor_partial_added_first_old_cleanup && partial\n                                ? true" in driver
            and "!vendor_partial_added_first_old_cleanup)" in driver,
        "identical_frame_returns_before_gpio_or_payload": driver.find("if (partial && !window.changed) {") >= 0
            and driver.find("return COMP_EPAPER_PANEL_RESULT_OK;", driver.find("if (partial && !window.changed) {"))
                < driver.find("ssd1681_gpio_init();", driver.find("if (partial && !window.changed) {")),
        "make_and_build_have_isolated_50_and_360_images": all(token in makefile + build for token in (
            "EPAPER_SSD1681_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_DIAGNOSTIC",
            "EpaperSsd1681VendorPartialAddedFirstOldCleanupDiagnostic",
            "EpaperSsd1681VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic",
            "build_vendor_partial_added_first_old_cleanup_diagnostic",
            "build_vendor_partial_added_first_old_cleanup_operator_loop_diagnostic",
            "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=6")) and "if ($addedFirstObserver) { 360 } else { 50 }" in build,
        "runner_is_fail_closed_and_requires_machine_gate_before_prompt": all(token in runner for token in (
            "-ReusePassedMachineTrace is an execution-only optimization.",
            "Machine trace gate failed; operator review is forbidden.",
            "normal_firmware_restore_required = $true", "aiw_operator_prompt_v1", "-WorkflowLockHeld")),
        "diagnostic_and_observer_elves_contain_profile": PROFILE in DIAG_ELF.read_bytes() and PROFILE in OBSERVER_ELF.read_bytes(),
        "normal_restore_image_is_exact_and_profile_absent": digest(NORMAL_HEX) == NORMAL_SHA
            and PROFILE not in NORMAL_ELF.read_bytes(),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": "companion.wb55.gdey0154d67_t03.vendor_partial_added_first_old_cleanup_static.v1",
        "status": STATUS if not failures else "NO_GO_STATIC_ADDED_FIRST_OLD_CLEANUP_CONTRACT_INCOMPLETE",
        "claim_scope": "machine-only default-off production-off source contract; no physical success claim",
        "checks": checks,
        "failures": failures,
        "synthetic_probe": synth,
        "source_manifest": {rel(path): digest(path) for path in required},
        "forbidden": ["fallback", "union", "mixed pass-1 byte", "0x21", "0x2D", "0x37", "0x26 after baseline", "LUT/waveform mutation", "third activation"],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    report = evaluate()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"{report['status']}: {rel(output)}")
    return 0 if report["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
