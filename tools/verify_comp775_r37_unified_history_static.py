#!/usr/bin/env python3
"""Verify current product restores the complete accepted r37 refresh history."""

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
    ROOT / ".cache/validation/comp775-r51-exact-r37-inplace-coverage"
    / "accepted-physical-baseline/BASELINE_MANIFEST.json"
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def extract(source: str, name: str) -> str:
    match = re.search(rf"static [^\n]+ {re.escape(name)}\(", source)
    if match is None:
        raise ValueError(f"missing function {name}")
    body = source.find("{", match.start())
    if body < 0:
        raise ValueError(f"missing body for {name}")
    depth = 0
    for index in range(body, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    raise ValueError(f"unterminated function {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = DRIVER.read_text(encoding="utf-8")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8-sig"))
    product = extract(source, "ssd1681_accepted_cached_mode2_product_refresh")
    landing = extract(source, "ssd1681_lifecycle_mode2_fast_full_activation")

    strong_start = product.index("if (strong_idle_enter_refresh) {")
    boundary_start = product.index(
        "} else if (first_frame || visible_full_refresh || maintenance_refresh)",
        strong_start,
    )
    settle_start = product.index(
        "} else if (s_need_mode2_settle_after_mode1_gc)", boundary_start
    )
    strong = product[strong_start:boundary_start]
    boundary = product[boundary_start:settle_start]

    checks = {
        "historical_baseline_is_owner_accepted": (
            baseline.get("status") == "HUMAN_ACCEPTED_PHYSICAL_BASELINE"
            and baseline.get("baseline") == "r51-exact-r37-inplace-coverage"
            and baseline.get("operator_selection") == "通过"
            and baseline.get("firmware_bin_sha256")
            == "3DA80011473D0EB92C9313B06BD21A9CA1AE3FFABA0BD7BCA21034BCC2136A18"
        ),
        "ordinary_life_never_auto_promotes_to_full": (
            "automatic_life_maintenance = false;" in product
            and "selection.reason == COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT"
            not in product
        ),
        "lp_uses_committed_previous_ff": (
            strong.count("ssd1681_lifecycle_mode2_fast_full_activation(") == 1
            and "ssd1681_lifecycle_mode1_gc_full_activation_ex(" not in strong
            and "ssd1681_lifecycle_lp_supplier_1s_single_activation(" not in strong
        ),
        "boot_menu_wake_maintenance_use_same_ff": (
            boundary.count("ssd1681_lifecycle_mode2_fast_full_activation(") == 1
            and "ssd1681_lifecycle_mode1_gc_full_activation_ex(" not in boundary
            and "control=0xFF unified_r37=1" in boundary
        ),
        "ordinary_frames_remain_single_cf": (
            "ssd1681_cached_mode2_diff_internal(" in product
            and "Ordinary product partial: single 0xCF path" in product
        ),
        "landing_uses_committed_previous_old_plane": (
            "committed_previous_used = s_controller_initialized &&" in landing
            and "s_previous_frame_valid;" in landing
            and "0x26u, s_blink_closed_frame, &window" in landing
            and "0x24u, s_frame, &window" in landing
        ),
        "landing_has_one_ff_activation": (
            "static const uint8_t fast_full_update[] = {0xFFu};" in landing
            and landing.count("ssd1681_command(0x20u)") == 1
            and "activation_count=%u complete=%u" in landing
        ),
        "landing_rebaselines_without_activation": (
            "rebaseline_commands=0x26,0x24" in landing
            and "rebaseline_bytes=10000 rebaseline_activation=0" in landing
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_id": "companion.comp775.r37_unified_history.static.v1",
        "status": "PASS_STATIC_R37_UNIFIED_HISTORY" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "driver": {"path": str(DRIVER), "sha256": digest(DRIVER)},
        "accepted_baseline": {"path": str(BASELINE), "sha256": digest(BASELINE)},
        "claim_scope": "complete refresh-history topology only; current binary and glass remain unproven",
    }
    destination = args.write if args.write.is_absolute() else ROOT / args.write
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if failures:
        print("FAIL: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: complete r37 refresh history restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
