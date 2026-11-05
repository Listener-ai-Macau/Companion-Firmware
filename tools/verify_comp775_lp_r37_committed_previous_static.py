#!/usr/bin/env python3
"""Fail closed on restoration of the Owner-accepted r37 LP landing."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
BASELINE = (
    ROOT
    / ".cache/validation/comp775-r51-exact-r37-inplace-coverage"
    / "accepted-physical-baseline/BASELINE_MANIFEST.json"
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def extract_function(source: str, name: str) -> str:
    match = re.search(
        rf"static bool {re.escape(name)}\(.*?\n\}}\r?\n(?=\r?\nstatic )",
        source,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError(f"missing function: {name}")
    return match.group(0)


def extract_lp_branch(source: str) -> str:
    marker = "if (strong_idle_enter_refresh) {"
    start = source.find(marker, source.find("phase_started_ms = HAL_GetTick();"))
    end = source.find("} else if (first_frame || visible_full_refresh", start)
    if start < 0 or end < 0:
        raise ValueError("missing product IDLE_ENTER_STRONG branch")
    return source[start:end]


def evaluate() -> dict[str, object]:
    source = DRIVER.read_text(encoding="utf-8")
    manifest = json.loads(BASELINE.read_text(encoding="utf-8-sig"))
    landing = extract_function(
        source, "ssd1681_lifecycle_mode2_fast_full_activation"
    )
    branch = extract_lp_branch(source)

    checks = {
        "accepted_manifest_is_human_pass": (
            manifest.get("schema")
            == "companion.comp_req_775.accepted_physical_baseline.v1"
            and manifest.get("status") == "HUMAN_ACCEPTED_PHYSICAL_BASELINE"
            and manifest.get("baseline") == "r51-exact-r37-inplace-coverage"
            and manifest.get("operator_selection") == "通过"
        ),
        "lp_branch_calls_r37_once": (
            branch.count("ssd1681_lifecycle_mode2_fast_full_activation(") == 1
        ),
        "lp_branch_does_not_call_rejected_supplier_or_gc": (
            "ssd1681_lifecycle_lp_supplier_1s_single_activation(" not in branch
            and "ssd1681_lifecycle_mode1_gc_full_activation_ex(" not in branch
        ),
        "committed_previous_is_old_plane": (
            "committed_previous_used = s_controller_initialized &&" in landing
            and "s_previous_frame_valid;" in landing
            and "memcpy(s_blink_closed_frame, s_previous_frame," in landing
        ),
        "reset_first_then_mode2_load": (
            landing.find("ssd1681_reset();")
            < landing.find("ssd1681_wait_ready(0u, SSD1681_READY_TIMEOUT_MS)")
            < landing.find("ssd1681_accepted_mode2_rearm(&mode2_load_elapsed_ms)")
        ),
        "one_visible_ff_activation": (
            "static const uint8_t fast_full_update[] = {0xFFu};" in landing
            and landing.count("ssd1681_command(0x20u)") == 1
            and "report->activation_count" not in landing
        ),
        "old_then_current_plane_order": (
            landing.find("0x26u, s_blink_closed_frame, &window")
            < landing.find("0x24u, s_frame, &window")
        ),
        "target_target_rebaseline_without_activation": (
            landing.count("ssd1681_write_plane_region(0x26u, s_frame, &window)") == 1
            and landing.count("ssd1681_write_plane_region(0x24u, s_frame, &window)") == 2
            and "rebaseline_activation=0" in landing
        ),
        "lp_deep_sleep_remains_after_matching_commit": (
            "companion_epaper_panel_stm32wb_ssd1681_enter_deep_sleep();"
            in (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c")
            .read_text(encoding="utf-8")
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_id": "companion.comp775.lp_r37_committed_previous.static.v1",
        "status": "PASS_STATIC_R37_LP_RESTORED" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "driver": {"path": DRIVER.relative_to(ROOT).as_posix(), "sha256": digest(DRIVER)},
        "accepted_baseline": {
            "path": BASELINE.relative_to(ROOT).as_posix(),
            "sha256": digest(BASELINE),
            "firmware_bin_sha256": manifest.get("firmware_bin_sha256"),
            "owner_scope": manifest.get("owner_scope"),
        },
        "claim_scope": (
            "static restoration of the accepted low-power physical primitive; "
            "current binary and glass retention still require machine and Owner evidence"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = evaluate()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if args.write:
        destination = args.write if args.write.is_absolute() else ROOT / args.write
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if result["status"] != "PASS_STATIC_R37_LP_RESTORED":
        print("FAIL: " + ", ".join(result["failures"]), file=sys.stderr)
        return 1
    print("PASS: r37 committed-previous LP landing restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
